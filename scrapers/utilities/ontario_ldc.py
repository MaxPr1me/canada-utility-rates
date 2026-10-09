"""
ontario_ldc.py — Data-driven scraper for ALL Ontario electricity LDCs.

Ontario electricity rates have a unique structure:
  - ENERGY prices are set province-wide by the OEB (Ontario Energy Board)
    and are the same for every LDC.  Available as TOU, Tiered, or ULO.
  - DELIVERY charges (monthly fixed + distribution volumetric) are
    different for each LDC, approved individually by the OEB.
  - TRANSMISSION and REGULATORY charges are effectively the same
    province-wide (passed through from IESO/OEB).

Because of this structure, ONE scraper class handles all 55+ LDCs.
The registry passes a registry_entry dict; the scraper reads the
utility name and looks up its delivery charges from ONTARIO_LDC_DATA.

Official sources:
  OEB RPP prices: https://www.oeb.ca/consumer-information-and-protection/electricity-rates
  Each distributor's OEB-approved Tariff of Rates and Charges (OEB_TARIFF_DOCUMENTS)
  OEB bill-calculator open data (name/zone mapping and cross-check only):
    https://www.oeb.ca/_html/calculator/data/BillData.xml and BillData_GS.xml

For LDCs with a configured approved tariff, every value comes from that tariff
(delivery, riders, transmission, regulatory) plus the OEB RPP page (commodity):
residential and GS < 50 kW get TOU/Tiered/ULO records per rate zone/class, and
demand classes come from oeb_tariff.build_demand_records. The default zone keeps
the legacy tariff names and codes; other zones append " [<zone>]" to the name and
"-<ZONE-SLUG>" to the code. Unconfigured or merged LDCs keep labelled seed
estimates. Street lighting is an excluded class and stays a seed estimate.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import date, datetime, timezone
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils import oeb_tariff

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# Province-wide OEB-regulated energy rates (same for ALL LDCs)
# Updated periodically — usually May 1 and Nov 1
# ═══════════════════════════════════════════════════════════════

OEB_EFFECTIVE_DATE = "2025-11-01"
OEB_SOURCE_URL = "https://www.oeb.ca/consumer-information-and-protection/electricity-rates"

# Time-of-Use (Nov 2025)
OEB_TOU = {
    "off_peak": 0.098,    # $/kWh
    "mid_peak": 0.157,    # $/kWh
    "on_peak": 0.203,     # $/kWh
}

# Tiered (Nov 2025)
OEB_TIERED = {
    "tier1_rate": 0.120,
    "tier2_rate": 0.142,
    "tier1_threshold_winter": 1000,  # kWh/month (Nov-Apr)
    "tier1_threshold_summer": 600,   # kWh/month (May-Oct)
}

# Ultra-Low Overnight (Nov 2025)
OEB_ULO = {
    "ultra_low_overnight": 0.039,  # 11pm-7am
    "weekend_off_peak": 0.098,     # weekends & holidays 7am-11pm
    "mid_peak": 0.157,             # weekdays 7am-4pm & 9pm-11pm
    "on_peak": 0.391,              # weekdays 4pm-9pm
}

# Residential / GS < 50 kW pass-through charges (volumetric, $/kWh)
OEB_TX_NETWORK_VOL = 0.0120       # $/kWh — transmission network
OEB_TX_CONNECTION_VOL = 0.0068    # $/kWh — transmission connection
OEB_REGULATORY_CHARGE = 0.0053    # $/kWh — regulatory charge (Jan 2026)


# ═══════════════════════════════════════════════════════════════
# OEB-regulated GS energy rates (same province-wide)
# GS < 50 kW uses TOU/Tiered like residential (same energy prices)
# GS >= 50 kW pays market-based energy: the IESO Ontario Electricity Market
# Price (OEMP; the HOEP was retired April 30, 2025) plus the Global Adjustment
# ═══════════════════════════════════════════════════════════════

# Street Lighting energy rate
OEB_STREET_LIGHTING_ENERGY = 0.0576  # $/kWh — effective 2025-11-01


# ═══════════════════════════════════════════════════════════════
# Per-LDC delivery charges
#
# Each entry is a dict with named keys for each customer class:
#
#   "res":  {"fixed": $/mo, "dist_vol": $/kWh}
#   "gs_s": {"fixed": $/mo, "dist_vol": $/kWh}
#   "gs_d1": {"fixed": $/mo, "dist_demand": $/kW, "tx_network": $/kW,
#             "tx_connection": $/kW, "low_voltage": $/kW,
#             "demand_min_kw": int, "demand_max_kw": int|None}
#   "gs_d2": same as gs_d1 (1,500-5,000 kW tier, optional)
#   "gs_d3": same as gs_d1 (5,000+ kW tier, optional)
#   "confidence": str
#
# Smaller LDCs may omit gs_d2 and/or gs_d3 if they don't serve
# those customer tiers.
#
# confidence:
#   "high"       = verified against OEB-approved rate order or utility site
#   "medium"     = from utility website but not cross-checked
#   "unverified" = estimated from OEB typical ranges
# ═══════════════════════════════════════════════════════════════

ONTARIO_LDC_DATA: dict[str, dict] = {
    # ── Major LDCs (verified rates) ─────────────────────────────
    "Toronto Hydro-Electric System Ltd.": {
        "confidence": "high",
        "res": {"fixed": 6.04, "dist_vol": 0.0254},
        "gs_s": {"fixed": 13.61, "dist_vol": 0.0254},
        "gs_d1": {
            "fixed": 268.40, "dist_demand": 4.7556,
            "tx_network": 4.4925, "tx_connection": 2.6068,
            "low_voltage": 0.01960,
            "demand_min_kw": 50, "demand_max_kw": 999,
        },
        "gs_d2": {
            "fixed": 2662.34, "dist_demand": 3.6875,
            "tx_network": 4.6512, "tx_connection": 2.7834,
            "low_voltage": 0.02100,
            "demand_min_kw": 1000, "demand_max_kw": 4999,
        },
        "gs_d3": {
            "fixed": 11408.60, "dist_demand": 3.0210,
            "tx_network": 5.1500, "tx_connection": 3.1200,
            "low_voltage": 0.02350,
            "demand_min_kw": 5000, "demand_max_kw": None,
        },
    },
    "Hydro One Networks Inc.": {
        "confidence": "high",
        "res": {"fixed": 30.77, "dist_vol": 0.0230},
        "gs_s": {"fixed": 31.58, "dist_vol": 0.0230},
        "gs_d1": {
            "fixed": 310.50, "dist_demand": 5.1200,
            "tx_network": 4.8500, "tx_connection": 2.8200,
            "low_voltage": 0.02100,
            "demand_min_kw": 50, "demand_max_kw": 999,
        },
        "gs_d2": {
            "fixed": 3250.00, "dist_demand": 4.2100,
            "tx_network": 5.0400, "tx_connection": 3.0100,
            "low_voltage": 0.02200,
            "demand_min_kw": 1000, "demand_max_kw": 4999,
        },
        "gs_d3": {
            "fixed": 12500.00, "dist_demand": 3.5600,
            "tx_network": 5.5800, "tx_connection": 3.3900,
            "low_voltage": 0.02480,
            "demand_min_kw": 5000, "demand_max_kw": None,
        },
    },
    "Hydro Ottawa Ltd.": {
        "confidence": "high",
        "res": {"fixed": 7.53, "dist_vol": 0.0305},
        "gs_s": {"fixed": 23.95, "dist_vol": 0.0305},
        "gs_d1": {
            "fixed": 200.00, "dist_demand": 6.5553,
            "tx_network": 4.8480, "tx_connection": 2.8187,
            "low_voltage": 0.02063,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
        "gs_d2": {
            "fixed": 4126.75, "dist_demand": 6.0796,
            "tx_network": 5.0337, "tx_connection": 3.0126,
            "low_voltage": 0.02204,
            "demand_min_kw": 1500, "demand_max_kw": 4999,
        },
        "gs_d3": {
            "fixed": 14946.93, "dist_demand": 6.0316,
            "tx_network": 5.5802, "tx_connection": 3.3924,
            "low_voltage": 0.02482,
            "demand_min_kw": 5000, "demand_max_kw": None,
        },
    },
    "Alectra Utilities": {
        "confidence": "high",
        "res": {"fixed": 5.40, "dist_vol": 0.0194},
        "gs_s": {"fixed": 14.54, "dist_vol": 0.0194},
        "gs_d1": {
            "fixed": 214.75, "dist_demand": 3.8640,
            "tx_network": 4.6000, "tx_connection": 2.6700,
            "low_voltage": 0.01900,
            "demand_min_kw": 50, "demand_max_kw": 999,
        },
        "gs_d2": {
            "fixed": 2450.00, "dist_demand": 3.2800,
            "tx_network": 4.7800, "tx_connection": 2.8600,
            "low_voltage": 0.02050,
            "demand_min_kw": 1000, "demand_max_kw": 4999,
        },
        "gs_d3": {
            "fixed": 10200.00, "dist_demand": 2.8500,
            "tx_network": 5.2900, "tx_connection": 3.2100,
            "low_voltage": 0.02300,
            "demand_min_kw": 5000, "demand_max_kw": None,
        },
    },
    "London Hydro Inc.": {
        "confidence": "high",
        "res": {"fixed": 8.07, "dist_vol": 0.0196},
        "gs_s": {"fixed": 13.75, "dist_vol": 0.0196},
        "gs_d1": {
            "fixed": 164.30, "dist_demand": 3.9700,
            "tx_network": 4.5500, "tx_connection": 2.6400,
            "low_voltage": 0.01880,
            "demand_min_kw": 50, "demand_max_kw": 999,
        },
        "gs_d2": {
            "fixed": 1850.00, "dist_demand": 3.4200,
            "tx_network": 4.7200, "tx_connection": 2.8200,
            "low_voltage": 0.02030,
            "demand_min_kw": 1000, "demand_max_kw": 4999,
        },
    },
    "Kitchener-Wilmot Hydro Inc.": {
        "confidence": "high",
        "res": {"fixed": 5.73, "dist_vol": 0.0180},
        "gs_s": {"fixed": 12.96, "dist_vol": 0.0180},
        "gs_d1": {
            "fixed": 155.80, "dist_demand": 3.7100,
            "tx_network": 4.5000, "tx_connection": 2.6100,
            "low_voltage": 0.01850,
            "demand_min_kw": 50, "demand_max_kw": 999,
        },
        "gs_d2": {
            "fixed": 1720.00, "dist_demand": 3.2000,
            "tx_network": 4.6800, "tx_connection": 2.8000,
            "low_voltage": 0.02000,
            "demand_min_kw": 1000, "demand_max_kw": 4999,
        },
    },

    # ── Medium-large LDCs ───────────────────────────────────────
    "Burlington Hydro Inc.": {
        "confidence": "medium",
        "res": {"fixed": 6.69, "dist_vol": 0.0180},
        "gs_s": {"fixed": 14.22, "dist_vol": 0.0180},
        "gs_d1": {
            "fixed": 178.50, "dist_demand": 3.8200,
            "tx_network": 4.6000, "tx_connection": 2.6700,
            "low_voltage": 0.01900,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Oakville Hydro Electricity Distribution Inc.": {
        "confidence": "medium",
        "res": {"fixed": 6.62, "dist_vol": 0.0188},
        "gs_s": {"fixed": 14.16, "dist_vol": 0.0188},
        "gs_d1": {
            "fixed": 185.20, "dist_demand": 3.9500,
            "tx_network": 4.6200, "tx_connection": 2.6800,
            "low_voltage": 0.01920,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Kingston Hydro Corporation": {
        "confidence": "medium",
        "res": {"fixed": 8.44, "dist_vol": 0.0174},
        "gs_s": {"fixed": 14.80, "dist_vol": 0.0174},
        "gs_d1": {
            "fixed": 170.40, "dist_demand": 3.6800,
            "tx_network": 4.5500, "tx_connection": 2.6400,
            "low_voltage": 0.01880,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Greater Sudbury Hydro Inc.": {
        "confidence": "medium",
        "res": {"fixed": 7.90, "dist_vol": 0.0205},
        "gs_s": {"fixed": 15.10, "dist_vol": 0.0205},
        "gs_d1": {
            "fixed": 195.60, "dist_demand": 4.1200,
            "tx_network": 4.7000, "tx_connection": 2.7300,
            "low_voltage": 0.01970,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Guelph Hydro Electric Systems Inc.": {
        "confidence": "medium",
        "res": {"fixed": 5.64, "dist_vol": 0.0207},
        "gs_s": {"fixed": 13.25, "dist_vol": 0.0207},
        "gs_d1": {
            "fixed": 175.30, "dist_demand": 4.1500,
            "tx_network": 4.6800, "tx_connection": 2.7200,
            "low_voltage": 0.01960,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Milton Hydro Distribution Inc.": {
        "confidence": "medium",
        "res": {"fixed": 5.26, "dist_vol": 0.0175},
        "gs_s": {"fixed": 12.50, "dist_vol": 0.0175},
        "gs_d1": {
            "fixed": 160.20, "dist_demand": 3.6500,
            "tx_network": 4.5200, "tx_connection": 2.6200,
            "low_voltage": 0.01850,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Elexicon Energy Inc.": {
        "confidence": "medium",
        "res": {"fixed": 6.92, "dist_vol": 0.0192},
        "gs_s": {"fixed": 14.40, "dist_vol": 0.0192},
        "gs_d1": {
            "fixed": 180.60, "dist_demand": 3.9200,
            "tx_network": 4.6100, "tx_connection": 2.6800,
            "low_voltage": 0.01910,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Enwin Utilities Ltd.": {
        "confidence": "medium",
        "res": {"fixed": 6.87, "dist_vol": 0.0234},
        "gs_s": {"fixed": 13.90, "dist_vol": 0.0234},
        "gs_d1": {
            "fixed": 192.50, "dist_demand": 4.5800,
            "tx_network": 4.7500, "tx_connection": 2.7600,
            "low_voltage": 0.01990,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Halton Hills Hydro Inc.": {
        "confidence": "medium",
        "res": {"fixed": 5.28, "dist_vol": 0.0186},
        "gs_s": {"fixed": 12.60, "dist_vol": 0.0186},
        "gs_d1": {
            "fixed": 165.40, "dist_demand": 3.8000,
            "tx_network": 4.5800, "tx_connection": 2.6600,
            "low_voltage": 0.01890,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Waterloo North Hydro Inc.": {
        "confidence": "medium",
        "res": {"fixed": 5.56, "dist_vol": 0.0189},
        "gs_s": {"fixed": 13.10, "dist_vol": 0.0189},
        "gs_d1": {
            "fixed": 168.50, "dist_demand": 3.8500,
            "tx_network": 4.5900, "tx_connection": 2.6600,
            "low_voltage": 0.01900,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Niagara Peninsula Energy Inc.": {
        "confidence": "medium",
        "res": {"fixed": 9.12, "dist_vol": 0.0179},
        "gs_s": {"fixed": 16.20, "dist_vol": 0.0179},
        "gs_d1": {
            "fixed": 198.40, "dist_demand": 3.7200,
            "tx_network": 4.5500, "tx_connection": 2.6400,
            "low_voltage": 0.01880,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Synergy North Corporation": {
        "confidence": "medium",
        "res": {"fixed": 7.92, "dist_vol": 0.0219},
        "gs_s": {"fixed": 15.40, "dist_vol": 0.0219},
        "gs_d1": {
            "fixed": 200.10, "dist_demand": 4.3600,
            "tx_network": 4.7200, "tx_connection": 2.7400,
            "low_voltage": 0.01980,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Brantford Power Inc.": {
        "confidence": "medium",
        "res": {"fixed": 6.77, "dist_vol": 0.0213},
        "gs_s": {"fixed": 14.00, "dist_vol": 0.0213},
        "gs_d1": {
            "fixed": 182.30, "dist_demand": 4.2200,
            "tx_network": 4.6800, "tx_connection": 2.7200,
            "low_voltage": 0.01960,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "North Bay Hydro Distribution Ltd.": {
        "confidence": "medium",
        "res": {"fixed": 7.94, "dist_vol": 0.0202},
        "gs_s": {"fixed": 14.90, "dist_vol": 0.0202},
        "gs_d1": {
            "fixed": 188.70, "dist_demand": 4.0800,
            "tx_network": 4.6500, "tx_connection": 2.7000,
            "low_voltage": 0.01940,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Festival Hydro Inc.": {
        "confidence": "medium",
        "res": {"fixed": 5.57, "dist_vol": 0.0193},
        "gs_s": {"fixed": 13.00, "dist_vol": 0.0193},
        "gs_d1": {
            "fixed": 166.80, "dist_demand": 3.9000,
            "tx_network": 4.6000, "tx_connection": 2.6700,
            "low_voltage": 0.01900,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Entegrus Powerlines Inc.": {
        "confidence": "medium",
        "res": {"fixed": 6.84, "dist_vol": 0.0217},
        "gs_s": {"fixed": 14.30, "dist_vol": 0.0217},
        "gs_d1": {
            "fixed": 186.40, "dist_demand": 4.3200,
            "tx_network": 4.7000, "tx_connection": 2.7300,
            "low_voltage": 0.01970,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Bluewater Power Distribution": {
        "confidence": "medium",
        "res": {"fixed": 6.43, "dist_vol": 0.0205},
        "gs_s": {"fixed": 13.60, "dist_vol": 0.0205},
        "gs_d1": {
            "fixed": 179.50, "dist_demand": 4.1000,
            "tx_network": 4.6500, "tx_connection": 2.7000,
            "low_voltage": 0.01940,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Essex Powerlines Corp.": {
        "confidence": "medium",
        "res": {"fixed": 6.54, "dist_vol": 0.0209},
        "gs_s": {"fixed": 13.80, "dist_vol": 0.0209},
        "gs_d1": {
            "fixed": 183.60, "dist_demand": 4.1800,
            "tx_network": 4.6600, "tx_connection": 2.7100,
            "low_voltage": 0.01950,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Newmarket-Tay Power Distribution Ltd.": {
        "confidence": "medium",
        "res": {"fixed": 5.85, "dist_vol": 0.0183},
        "gs_s": {"fixed": 13.20, "dist_vol": 0.0183},
        "gs_d1": {
            "fixed": 168.30, "dist_demand": 3.7500,
            "tx_network": 4.5600, "tx_connection": 2.6500,
            "low_voltage": 0.01880,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Oshawa PUC Networks Inc.": {
        "confidence": "medium",
        "res": {"fixed": 5.80, "dist_vol": 0.0196},
        "gs_s": {"fixed": 13.40, "dist_vol": 0.0196},
        "gs_d1": {
            "fixed": 174.20, "dist_demand": 3.9600,
            "tx_network": 4.6100, "tx_connection": 2.6800,
            "low_voltage": 0.01910,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Welland Hydro-Electric System Corp.": {
        "confidence": "medium",
        "res": {"fixed": 6.11, "dist_vol": 0.0222},
        "gs_s": {"fixed": 13.50, "dist_vol": 0.0222},
        "gs_d1": {
            "fixed": 185.80, "dist_demand": 4.4000,
            "tx_network": 4.7200, "tx_connection": 2.7400,
            "low_voltage": 0.01980,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "St. Thomas Energy Inc.": {
        "confidence": "medium",
        "res": {"fixed": 5.72, "dist_vol": 0.0211},
        "gs_s": {"fixed": 13.30, "dist_vol": 0.0211},
        "gs_d1": {
            "fixed": 176.40, "dist_demand": 4.2000,
            "tx_network": 4.6800, "tx_connection": 2.7200,
            "low_voltage": 0.01960,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "PUC Distribution Inc.": {
        "confidence": "medium",
        "res": {"fixed": 8.45, "dist_vol": 0.0210},
        "gs_s": {"fixed": 15.60, "dist_vol": 0.0210},
        "gs_d1": {
            "fixed": 196.80, "dist_demand": 4.2400,
            "tx_network": 4.6800, "tx_connection": 2.7200,
            "low_voltage": 0.01960,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Orangeville Hydro Limited": {
        "confidence": "medium",
        "res": {"fixed": 5.98, "dist_vol": 0.0197},
        "gs_s": {"fixed": 13.50, "dist_vol": 0.0197},
        "gs_d1": {
            "fixed": 172.60, "dist_demand": 3.9800,
            "tx_network": 4.6100, "tx_connection": 2.6800,
            "low_voltage": 0.01910,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },

    # ── Smaller LDCs (approximate values) ───────────────────────
    "Algoma Power Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 11.22, "dist_vol": 0.0334},
        "gs_s": {"fixed": 20.50, "dist_vol": 0.0334},
        "gs_d1": {
            "fixed": 280.60, "dist_demand": 6.2000,
            "tx_network": 4.9500, "tx_connection": 2.8800,
            "low_voltage": 0.02100,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Atikokan Hydro Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 8.25, "dist_vol": 0.0245},
        "gs_s": {"fixed": 15.80, "dist_vol": 0.0245},
        "gs_d1": {
            "fixed": 210.40, "dist_demand": 4.8500,
            "tx_network": 4.7800, "tx_connection": 2.7800,
            "low_voltage": 0.02000,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Canadian Niagara Power Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 9.10, "dist_vol": 0.0210},
        "gs_s": {"fixed": 16.40, "dist_vol": 0.0210},
        "gs_d1": {
            "fixed": 198.30, "dist_demand": 4.2500,
            "tx_network": 4.6800, "tx_connection": 2.7200,
            "low_voltage": 0.01960,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Centre Wellington Hydro Ltd.": {
        "confidence": "unverified",
        "res": {"fixed": 5.40, "dist_vol": 0.0198},
        "gs_s": {"fixed": 12.80, "dist_vol": 0.0198},
        "gs_d1": {
            "fixed": 170.50, "dist_demand": 3.9800,
            "tx_network": 4.6200, "tx_connection": 2.6800,
            "low_voltage": 0.01910,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Chapleau Public Utilities Corp.": {
        "confidence": "unverified",
        "res": {"fixed": 8.85, "dist_vol": 0.0292},
        "gs_s": {"fixed": 17.60, "dist_vol": 0.0292},
        "gs_d1": {
            "fixed": 245.80, "dist_demand": 5.7500,
            "tx_network": 4.9000, "tx_connection": 2.8500,
            "low_voltage": 0.02060,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Erie Thames Powerlines Corp.": {
        "confidence": "unverified",
        "res": {"fixed": 7.25, "dist_vol": 0.0218},
        "gs_s": {"fixed": 14.80, "dist_vol": 0.0218},
        "gs_d1": {
            "fixed": 185.40, "dist_demand": 4.3500,
            "tx_network": 4.7000, "tx_connection": 2.7300,
            "low_voltage": 0.01970,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Espanola Regional Hydro": {
        "confidence": "unverified",
        "res": {"fixed": 8.50, "dist_vol": 0.0265},
        "gs_s": {"fixed": 16.20, "dist_vol": 0.0265},
        "gs_d1": {
            "fixed": 230.40, "dist_demand": 5.2500,
            "tx_network": 4.8500, "tx_connection": 2.8200,
            "low_voltage": 0.02040,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Fort Frances Power Corp.": {
        "confidence": "unverified",
        "res": {"fixed": 8.40, "dist_vol": 0.0248},
        "gs_s": {"fixed": 16.00, "dist_vol": 0.0248},
        "gs_d1": {
            "fixed": 215.60, "dist_demand": 4.9200,
            "tx_network": 4.8000, "tx_connection": 2.7900,
            "low_voltage": 0.02010,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Grimsby Power Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 5.82, "dist_vol": 0.0198},
        "gs_s": {"fixed": 13.20, "dist_vol": 0.0198},
        "gs_d1": {
            "fixed": 172.40, "dist_demand": 3.9800,
            "tx_network": 4.6200, "tx_connection": 2.6800,
            "low_voltage": 0.01910,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Hearst Power Distribution Co. Ltd.": {
        "confidence": "unverified",
        "res": {"fixed": 9.10, "dist_vol": 0.0295},
        "gs_s": {"fixed": 17.80, "dist_vol": 0.0295},
        "gs_d1": {
            "fixed": 250.60, "dist_demand": 5.8200,
            "tx_network": 4.9200, "tx_connection": 2.8600,
            "low_voltage": 0.02070,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Hydro 2000 Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 7.60, "dist_vol": 0.0232},
        "gs_s": {"fixed": 15.00, "dist_vol": 0.0232},
        "gs_d1": {
            "fixed": 195.40, "dist_demand": 4.5800,
            "tx_network": 4.7500, "tx_connection": 2.7600,
            "low_voltage": 0.01990,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Hydro Hawkesbury Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 6.90, "dist_vol": 0.0224},
        "gs_s": {"fixed": 14.20, "dist_vol": 0.0224},
        "gs_d1": {
            "fixed": 188.60, "dist_demand": 4.4500,
            "tx_network": 4.7200, "tx_connection": 2.7400,
            "low_voltage": 0.01980,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Innpower Corporation": {
        "confidence": "unverified",
        "res": {"fixed": 6.15, "dist_vol": 0.0210},
        "gs_s": {"fixed": 13.40, "dist_vol": 0.0210},
        "gs_d1": {
            "fixed": 178.20, "dist_demand": 4.2000,
            "tx_network": 4.6800, "tx_connection": 2.7200,
            "low_voltage": 0.01960,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Lakefront Utilities Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 6.80, "dist_vol": 0.0211},
        "gs_s": {"fixed": 14.10, "dist_vol": 0.0211},
        "gs_d1": {
            "fixed": 180.40, "dist_demand": 4.2200,
            "tx_network": 4.6800, "tx_connection": 2.7200,
            "low_voltage": 0.01960,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Lakeland Power Distribution Ltd.": {
        "confidence": "unverified",
        "res": {"fixed": 10.98, "dist_vol": 0.0276},
        "gs_s": {"fixed": 19.80, "dist_vol": 0.0276},
        "gs_d1": {
            "fixed": 260.40, "dist_demand": 5.4500,
            "tx_network": 4.8800, "tx_connection": 2.8400,
            "low_voltage": 0.02050,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Midland Power Utility Corp.": {
        "confidence": "unverified",
        "res": {"fixed": 6.10, "dist_vol": 0.0215},
        "gs_s": {"fixed": 13.30, "dist_vol": 0.0215},
        "gs_d1": {
            "fixed": 180.20, "dist_demand": 4.3000,
            "tx_network": 4.7000, "tx_connection": 2.7300,
            "low_voltage": 0.01970,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Northern Ontario Wires Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 9.25, "dist_vol": 0.0285},
        "gs_s": {"fixed": 17.40, "dist_vol": 0.0285},
        "gs_d1": {
            "fixed": 245.20, "dist_demand": 5.6200,
            "tx_network": 4.9000, "tx_connection": 2.8500,
            "low_voltage": 0.02060,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Ottawa River Power Corporation": {
        "confidence": "unverified",
        "res": {"fixed": 7.85, "dist_vol": 0.0218},
        "gs_s": {"fixed": 14.90, "dist_vol": 0.0218},
        "gs_d1": {
            "fixed": 186.50, "dist_demand": 4.3500,
            "tx_network": 4.7000, "tx_connection": 2.7300,
            "low_voltage": 0.01970,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Rideau St. Lawrence Distribution Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 8.15, "dist_vol": 0.0240},
        "gs_s": {"fixed": 15.40, "dist_vol": 0.0240},
        "gs_d1": {
            "fixed": 205.60, "dist_demand": 4.7500,
            "tx_network": 4.7800, "tx_connection": 2.7800,
            "low_voltage": 0.02000,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Sioux Lookout Hydro Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 8.80, "dist_vol": 0.0260},
        "gs_s": {"fixed": 16.60, "dist_vol": 0.0260},
        "gs_d1": {
            "fixed": 225.40, "dist_demand": 5.1500,
            "tx_network": 4.8400, "tx_connection": 2.8100,
            "low_voltage": 0.02030,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Tillsonburg Hydro Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 5.95, "dist_vol": 0.0203},
        "gs_s": {"fixed": 13.20, "dist_vol": 0.0203},
        "gs_d1": {
            "fixed": 174.60, "dist_demand": 4.0600,
            "tx_network": 4.6500, "tx_connection": 2.7000,
            "low_voltage": 0.01940,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Wasaga Distribution Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 5.70, "dist_vol": 0.0195},
        "gs_s": {"fixed": 12.90, "dist_vol": 0.0195},
        "gs_d1": {
            "fixed": 168.40, "dist_demand": 3.9200,
            "tx_network": 4.6100, "tx_connection": 2.6800,
            "low_voltage": 0.01900,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
    "Westario Power Inc.": {
        "confidence": "unverified",
        "res": {"fixed": 6.50, "dist_vol": 0.0215},
        "gs_s": {"fixed": 13.80, "dist_vol": 0.0215},
        "gs_d1": {
            "fixed": 182.60, "dist_demand": 4.3000,
            "tx_network": 4.7000, "tx_connection": 2.7300,
            "low_voltage": 0.01970,
            "demand_min_kw": 50, "demand_max_kw": 1499,
        },
    },
}


# ═══════════════════════════════════════════════════════════════
# OEB bill-calculator open data — mapping and cross-check only
#
# The feed has one row per distributor rate zone and class. It names zones
# consistently, so it maps registry LDCs to OEB distributors/zones and is
# compared against the approved tariffs, but its values are never used in
# records (stale rows, merged alternative charges, aggregate riders and
# rate-year-only dates). RPP prices, periods, tier thresholds and the price
# effective date come from the OEB electricity-rates page.
# ═══════════════════════════════════════════════════════════════

OEB_BILLDATA_RES_URL = "https://www.oeb.ca/_html/calculator/data/BillData.xml"
OEB_BILLDATA_GS_URL = "https://www.oeb.ca/_html/calculator/data/BillData_GS.xml"
OEB_DATA_KEYS_URL = "https://www.oeb.ca/sites/default/files/data-keys-electricity-rates.xlsx"

# Exact element set of a <BillDataRow>; any addition or removal fails closed.
OEB_BILLDATA_FIELDS = frozenset({
    "Dist", "Class", "YEAR", "ET1", "RPP1", "RPP2", "SC", "DC", "GA_RR_NONRPP",
    "Net", "Conn", "WMSR", "RRRP", "SSS", "LF", "GST", "EOffP", "EMidP", "EOnP",
    "RPPOffP", "RPPMidP", "RPPOnP", "PBGA", "Rebate", "OFC", "VC", "OC", "DRP",
    "DRC", "DRP_Rate", "ULO_midp", "ULO_midp_period", "ULO_onp", "ULO_onp_period",
    "ULO_overnight", "ULO_overnight_period", "ULO_weekendoffp",
    "ULO_weekendoffp_period",
})

# OEB <Class> label -> zone qualifier ("" = the distributor's standard class).
OEB_RES_CLASS_QUALIFIERS = {
    "RESIDENTIAL": "",
    "RESIDENTIAL R1": "R1",
    "R1 RESIDENTIAL": "R1",
    "RESIDENTIAL R2": "R2",
    "R2 RESIDENTIAL": "R2",
    "AUR RESIDENTIAL": "AUR",
    "UR RESIDENTIAL": "UR",
    "AR RESIDENTIAL": "AR",
    "SEASONAL CUSTOMERS": "Seasonal",
    "SEASONAL RESIDENTIAL": "Seasonal",
    "COMPETITIVE SECTOR MULTI-UNIT RESIDENTIAL": "Competitive Sector Multi-Unit Residential",
}
OEB_GS_CLASS_QUALIFIERS = {
    "GENERAL SERVICE LESS THAN 50 KW": "",
    "URBAN GENERAL SERVICE ENERGY BILLED": "UGe",
    "URBAN GENERAL SERVICE ENERGY BILLED - UGE": "UGe",
    "GENERAL SERVICE ENERGY BILLED": "GSe",
}

# OEB distributor (the <Dist> text before any "-<zone>" suffix) -> registry name.
# Entries whose registry name equals the OEB name are successors or LDCs that
# are not yet registered; adding a registry entry with that name enables them.
OEB_DISTRIBUTOR_REGISTRY_NAMES: dict[str, str] = {
    "Alectra Utilities Corporation": "Alectra Utilities",
    "Algoma Power Inc.": "Algoma Power Inc.",
    "Atikokan Hydro Inc.": "Atikokan Hydro Inc.",
    "Bluewater Power Distribution Corporation": "Bluewater Power Distribution",
    "Burlington Hydro Inc.": "Burlington Hydro Inc.",
    "Canadian Niagara Power Inc.": "Canadian Niagara Power Inc.",
    "Centre Wellington Hydro Ltd.": "Centre Wellington Hydro Ltd.",
    "Cooperative Hydro Embrun Inc.": "Cooperative Hydro Embrun Inc.",
    "E.L.K. Energy Inc.": "E.L.K. Energy Inc.",
    "Elexicon Energy Inc.": "Elexicon Energy Inc.",
    "Enova Power Corp.": "Enova Power Corp.",
    "Entegrus Powerlines Inc.": "Entegrus Powerlines Inc.",
    "ENWIN Utilities Ltd.": "Enwin Utilities Ltd.",
    "EPCOR Electricity Distribution Ontario Inc.": "EPCOR Electricity Distribution Ontario Inc.",
    "ERTH Power Corporation": "Erie Thames Powerlines Corp.",
    "ESSEX POWERLINES CORPORATION": "Essex Powerlines Corp.",
    "Festival Hydro Inc.": "Festival Hydro Inc.",
    "Fort Frances Power Corporation": "Fort Frances Power Corp.",
    "GrandBridge Energy Inc.": "GrandBridge Energy Inc.",
    "Greater Sudbury Hydro Inc.": "Greater Sudbury Hydro Inc.",
    "Grimsby Power Incorporated": "Grimsby Power Inc.",
    "Halton Hills Hydro Inc.": "Halton Hills Hydro Inc.",
    "Hearst Power Distribution Co. Ltd.": "Hearst Power Distribution Co. Ltd.",
    "Hydro 2000 Inc.": "Hydro 2000 Inc.",
    "Hydro Hawkesbury Inc.": "Hydro Hawkesbury Inc.",
    "Hydro One Networks Inc.": "Hydro One Networks Inc.",
    "Hydro Ottawa Limited": "Hydro Ottawa Ltd.",
    "InnPower Corporation": "Innpower Corporation",
    "Kingston Hydro Corporation": "Kingston Hydro Corporation",
    "Lakefront Utilities Inc.": "Lakefront Utilities Inc.",
    "Lakeland Power Distribution Ltd.": "Lakeland Power Distribution Ltd.",
    "London Hydro Inc.": "London Hydro Inc.",
    "Milton Hydro Distribution Inc.": "Milton Hydro Distribution Inc.",
    "Newmarket-Tay Power Distribution Ltd.": "Newmarket-Tay Power Distribution Ltd.",
    "Niagara Peninsula Energy Inc.": "Niagara Peninsula Energy Inc.",
    "Niagara-on-the-Lake Hydro Inc.": "Niagara-on-the-Lake Hydro Inc.",
    "North Bay Hydro Distribution Limited": "North Bay Hydro Distribution Ltd.",
    "Northern Ontario Wires Inc.": "Northern Ontario Wires Inc.",
    "Oakville Hydro Electricity Distribution Inc.": "Oakville Hydro Electricity Distribution Inc.",
    "Orangeville Hydro Limited": "Orangeville Hydro Limited",
    "Oshawa PUC Networks Inc.": "Oshawa PUC Networks Inc.",
    "Ottawa River Power Corporation": "Ottawa River Power Corporation",
    "PUC Distribution Inc.": "PUC Distribution Inc.",
    "Renfrew Hydro Inc.": "Renfrew Hydro Inc.",
    "Rideau St. Lawrence Distribution Inc.": "Rideau St. Lawrence Distribution Inc.",
    "Sioux Lookout Hydro Inc.": "Sioux Lookout Hydro Inc.",
    "Synergy North Corporation": "Synergy North Corporation",
    "Tillsonburg Hydro Inc.": "Tillsonburg Hydro Inc.",
    "Toronto Hydro-Electric System Limited": "Toronto Hydro-Electric System Ltd.",
    "Wasaga Distribution Inc.": "Wasaga Distribution Inc.",
    "Welland Hydro-Electric System Corp.": "Welland Hydro-Electric System Corp.",
    "Wellington North Power Inc.": "Wellington North Power Inc.",
    "Westario Power Inc.": "Westario Power Inc.",
}
OEB_REGISTRY_TO_DISTRIBUTOR = {v: k for k, v in OEB_DISTRIBUTOR_REGISTRY_NAMES.items()}

# Registry LDCs with no distributor of their own in the OEB feed. Their rates
# are published as a successor's rate zone, so they never emit live records
# under the old name (that would duplicate the successor's zone records).
OEB_MERGED_REGISTRY_NAMES: dict[str, str] = {
    "Brantford Power Inc.": "GrandBridge Energy Inc. (Brantford Power Rate Zone)",
    "Kitchener-Wilmot Hydro Inc.": "Enova Power Corp. (Kitchener-Wilmot Hydro Rate Zone)",
    "Waterloo North Hydro Inc.": "Enova Power Corp. (Waterloo North Rate Zone)",
    "Guelph Hydro Electric Systems Inc.": "Alectra Utilities Corporation (Guelph Rate Zone)",
    "St. Thomas Energy Inc.": "Entegrus Powerlines Inc. (Former St. Thomas Energy Rate Zone)",
    "Midland Power Utility Corp.": "Newmarket-Tay Power Distribution Ltd. (Midland Rate Zone)",
    "Espanola Regional Hydro": "North Bay Hydro Distribution Limited (Espanola Rate Zone)",
    "Chapleau Public Utilities Corp.": "not published in the OEB feed",
}

# Zone that keeps the legacy (unsuffixed) tariff names and codes, per OEB
# distributor and class group. Single-zone distributors need no entry.
OEB_DEFAULT_ZONES: dict[str, dict[str, str]] = {
    "Hydro One Networks Inc.": {"residential": "R1", "gs": "GSe"},
    "Alectra Utilities Corporation": {"residential": "PowerStream", "gs": "PowerStream"},
    "Algoma Power Inc.": {"residential": "R1 (i)"},
    "Elexicon Energy Inc.": {"residential": "Veridian", "gs": "Veridian"},
    "Entegrus Powerlines Inc.": {"residential": "Entegrus-Main", "gs": "Entegrus-Main"},
    "ERTH Power Corporation": {"residential": "Main", "gs": "Main"},
    "Newmarket-Tay Power Distribution Ltd.": {"residential": "Newmarket-Tay", "gs": "Newmarket-Tay"},
    "North Bay Hydro Distribution Limited": {"residential": "North Bay", "gs": "North Bay"},
}

# ═══════════════════════════════════════════════════════════════
# OEB-approved Tariff of Rates and Charges — the value source
#
# Registry name -> documents. Adding an LDC is one entry:
#   url           official tariff PDF (OEB RDS record or distributor rate order)
#   case_number   expected EB number; a different number on the sheet fails closed
#   zones         None = every rate zone in the document, or a list of zone names
#   default_zone  zone/class label keeping the legacy names and codes: a string
#                 for all groups or {"residential": ..., "gs": ..., "demand": ...};
#                 "" = the distributor's plain standard class
#   extract       optional text-extraction options, e.g. {"y_tolerance": 6}
#   connection_rate optional "not_printed" (oeb_tariff.CONNECTION_RATE_NOT_PRINTED):
#                 the approved tariff prints no Retail Transmission Connection rate, so
#                 classes without any connection line are accepted (with a note);
#                 every other document requires one
# ═══════════════════════════════════════════════════════════════

_OEB_RDS_DOC = "https://www.rds.oeb.ca/CMWebDrawer/Record/{}/File/document"

OEB_TARIFF_DOCUMENTS: dict[str, list[dict]] = {
    "Toronto Hydro-Electric System Ltd.": [{
        "url": "https://www.rds.oeb.ca/CMWebDrawer/Record/925317/File/document",
        "case_number": "EB-2025-0006", "zones": None, "default_zone": "",
    }],
    "Hydro Ottawa Ltd.": [{
        "url": "https://www.rds.oeb.ca/CMWebDrawer/Record/943758/File/document",
        "case_number": "EB-2024-0115", "zones": None, "default_zone": "",
    }],
    "Alectra Utilities": [{
        "url": "https://www.rds.oeb.ca/CMWebDrawer/Record/927401/File/document",
        "case_number": "EB-2025-0055", "zones": None, "default_zone": "PowerStream",
    }],
    "Hydro One Networks Inc.": [{
        "url": "https://www.hydroone.com/abouthydroone/RegulatoryInformation/rateschedules/"
               "Documents/Distribution%20Rates/dec_rate_order_HydroOne_20251223.PDF",
        "case_number": "EB-2025-0030", "zones": None,
        "default_zone": {"residential": "R1", "gs": "GSe"},
    }],
    "Elexicon Energy Inc.": [{
        "url": _OEB_RDS_DOC.format(932087),
        "case_number": "EB-2025-0046", "zones": ["Whitby", "Veridian"], "default_zone": "Veridian",
    }],
    "Niagara Peninsula Energy Inc.": [{
        "url": _OEB_RDS_DOC.format(925214),
        "case_number": "EB-2025-0020", "zones": None, "default_zone": "",
    }],
    "Milton Hydro Distribution Inc.": [{
        "url": _OEB_RDS_DOC.format(925125),
        "case_number": "EB-2025-0022", "zones": None, "default_zone": "",
    }],
    "Bluewater Power Distribution": [{
        "url": _OEB_RDS_DOC.format(936449),
        "case_number": "EB-2025-0052", "zones": None, "default_zone": "",
    }],
    "Halton Hills Hydro Inc.": [{
        "url": _OEB_RDS_DOC.format(938337),
        "case_number": "EB-2025-0034", "zones": None, "default_zone": "",
    }],
    "Essex Powerlines Corp.": [{
        "url": _OEB_RDS_DOC.format(925198),
        "case_number": "EB-2025-0040", "zones": None, "default_zone": "",
    }],
    "Erie Thames Powerlines Corp.": [{
        "url": _OEB_RDS_DOC.format(936464),
        "case_number": "EB-2025-0041", "zones": ["Main", "Goderich"], "default_zone": "Main",
    }],
    "North Bay Hydro Distribution Ltd.": [{
        "url": _OEB_RDS_DOC.format(939335),
        "case_number": "EB-2025-0018", "zones": ["North Bay", "Espanola"], "default_zone": "North Bay",
    }],
    "Synergy North Corporation": [{
        "url": _OEB_RDS_DOC.format(936213),
        "case_number": "EB-2025-0008", "zones": None, "default_zone": "",
    }],
    "Enwin Utilities Ltd.": [{
        "url": _OEB_RDS_DOC.format(925336),
        "case_number": "EB-2025-0043", "zones": None, "default_zone": "",
    }],
    "London Hydro Inc.": [{
        "url": _OEB_RDS_DOC.format(936432),
        "case_number": "EB-2025-0023", "zones": None, "default_zone": "",
    }],
    "Kingston Hydro Corporation": [{
        "url": _OEB_RDS_DOC.format(925245),
        "case_number": "EB-2025-0026", "zones": None, "default_zone": "",
        # Wider line grouping keeps the GS 50-4,999 kW labels with their rates.
        "extract": {"y_tolerance": 6},
    }],
    "Greater Sudbury Hydro Inc.": [{
        "url": _OEB_RDS_DOC.format(936646),
        "case_number": "EB-2025-0036", "zones": None, "default_zone": "",
    }],
    "Oakville Hydro Electricity Distribution Inc.": [{
        "url": _OEB_RDS_DOC.format(925312),
        "case_number": "EB-2025-0016", "zones": None, "default_zone": "",
    }],
    "Burlington Hydro Inc.": [{
        "url": _OEB_RDS_DOC.format(925320),
        "case_number": "EB-2025-0051", "zones": None, "default_zone": "",
    }],
    # Revised rate order (2026-03-31); zones harmonized into one tariff from 2026-05-01.
    "Entegrus Powerlines Inc.": [{
        "url": _OEB_RDS_DOC.format(937681),
        "case_number": "EB-2025-0044", "zones": None, "default_zone": "",
    }],
    "Oshawa PUC Networks Inc.": [{
        "url": _OEB_RDS_DOC.format(947598),
        "case_number": "EB-2025-0014", "zones": None, "default_zone": "",
    }],
    "Canadian Niagara Power Inc.": [{
        "url": _OEB_RDS_DOC.format(927499),
        "case_number": "EB-2025-0050", "zones": None, "default_zone": "",
    }],
    "Grimsby Power Inc.": [{
        "url": _OEB_RDS_DOC.format(925220),
        "case_number": "EB-2025-0035", "zones": None, "default_zone": "",
        # GS 50-4,999 kW rates print a few points above their labels.
        "extract": {"y_tolerance": 4},
    }],
    "Welland Hydro-Electric System Corp.": [{
        "url": _OEB_RDS_DOC.format(936222),
        "case_number": "EB-2025-0004", "zones": None, "default_zone": "",
    }],
    # Revised rate order.
    "Centre Wellington Hydro Ltd.": [{
        "url": _OEB_RDS_DOC.format(926741),
        "case_number": "EB-2025-0049", "zones": None, "default_zone": "",
    }],
    "Festival Hydro Inc.": [{
        "url": _OEB_RDS_DOC.format(925779),
        "case_number": "EB-2025-0039", "zones": None, "default_zone": "",
    }],
    "Westario Power Inc.": [{
        "url": _OEB_RDS_DOC.format(924811),
        "case_number": "EB-2025-0002", "zones": None, "default_zone": "",
    }],
    "Tillsonburg Hydro Inc.": [{
        "url": _OEB_RDS_DOC.format(939423),
        "case_number": "EB-2025-0007", "zones": None, "default_zone": "",
    }],
    "Orangeville Hydro Limited": [{
        "url": _OEB_RDS_DOC.format(939232),
        "case_number": "EB-2025-0015", "zones": None, "default_zone": "",
    }],
    "Wasaga Distribution Inc.": [{
        "url": _OEB_RDS_DOC.format(936415),
        "case_number": "EB-2025-0005", "zones": None, "default_zone": "",
    }],
    "Innpower Corporation": [{
        "url": _OEB_RDS_DOC.format(926802),
        "case_number": "EB-2025-0027", "zones": None, "default_zone": "",
    }],
    "Lakefront Utilities Inc.": [{
        "url": _OEB_RDS_DOC.format(925193),
        "case_number": "EB-2025-0025", "zones": None, "default_zone": "",
    }],
    # Final rate order, effective 2026-09-01.
    "Lakeland Power Distribution Ltd.": [{
        "url": _OEB_RDS_DOC.format(954612),
        "case_number": "EB-2025-0024", "zones": None, "default_zone": "",
    }],
    "Hydro 2000 Inc.": [{
        "url": _OEB_RDS_DOC.format(936563),
        "case_number": "EB-2025-0032", "zones": None, "default_zone": "",
    }],
    # Final rate order.
    "Hydro Hawkesbury Inc.": [{
        "url": _OEB_RDS_DOC.format(937884),
        "case_number": "EB-2025-0031", "zones": None, "default_zone": "",
    }],
    "Ottawa River Power Corporation": [{
        "url": _OEB_RDS_DOC.format(936459),
        "case_number": "EB-2025-0013", "zones": None, "default_zone": "",
    }],
    "Rideau St. Lawrence Distribution Inc.": [{
        "url": _OEB_RDS_DOC.format(937200),
        "case_number": "EB-2025-0010", "zones": None, "default_zone": "",
    }],
    "Hearst Power Distribution Co. Ltd.": [{
        "url": _OEB_RDS_DOC.format(939278),
        "case_number": "EB-2025-0033", "zones": None, "default_zone": "",
    }],
    "Atikokan Hydro Inc.": [{
        "url": _OEB_RDS_DOC.format(936437),
        "case_number": "EB-2025-0053", "zones": None, "default_zone": "",
    }],
    "Fort Frances Power Corp.": [{
        "url": _OEB_RDS_DOC.format(936512),
        "case_number": "EB-2025-0038", "zones": None, "default_zone": "",
    }],
    "Sioux Lookout Hydro Inc.": [{
        "url": _OEB_RDS_DOC.format(936469),
        "case_number": "EB-2025-0009", "zones": None, "default_zone": "",
    }],
    "Northern Ontario Wires Inc.": [{
        "url": _OEB_RDS_DOC.format(936426),
        "case_number": "EB-2025-0017", "zones": None, "default_zone": "",
    }],
    # Prints only the Network Service Rate (no connection rate); configured per user decision 2026-10-09.
    "PUC Distribution Inc.": [{
        "url": _OEB_RDS_DOC.format(936444),
        "case_number": "EB-2025-0012", "zones": None, "default_zone": "",
        "connection_rate": oeb_tariff.CONNECTION_RATE_NOT_PRINTED,
    }],
    # R1 criteria (i) (year-round dwelling) keeps the legacy residential codes; no GS classes.
    "Algoma Power Inc.": [{
        "url": _OEB_RDS_DOC.format(926153),
        "case_number": "EB-2025-0054", "zones": None, "default_zone": {"residential": "R1 (i)"},
    }],
    # Revised Newmarket-Tay zone sheet supersedes that zone in the original order.
    "Newmarket-Tay Power Distribution Ltd.": [
        {
            "url": _OEB_RDS_DOC.format(935092),
            "case_number": "EB-2025-0021", "zones": ["Newmarket-Tay"], "default_zone": "Newmarket-Tay",
        },
        {
            "url": _OEB_RDS_DOC.format(924987),
            "case_number": "EB-2025-0021", "zones": ["Midland"], "default_zone": "Newmarket-Tay",
            # Tighter line grouping keeps Midland's wrapped rider conditions on their own lines.
            "extract": {"y_tolerance": 1},
        },
    ],
    # Successors with no seed data: live records only.
    "Enova Power Corp.": [{
        "url": _OEB_RDS_DOC.format(925278),
        "case_number": "EB-2025-0045", "zones": ["Kitchener-Wilmot Hydro", "Waterloo North"],
        "default_zone": "Kitchener-Wilmot Hydro",
    }],
    "GrandBridge Energy Inc.": [{
        "url": _OEB_RDS_DOC.format(925329),
        "case_number": "EB-2025-0037", "zones": ["Brantford Power", "Energy+"],
        "default_zone": "Energy+",
    }],
}

# Configured LDCs that are not (yet) registry entries; they emit live records only.
OEB_SUCCESSOR_REGISTRY_NAMES = frozenset({"Enova Power Corp.", "GrandBridge Energy Inc."})

# An approved tariff older than this (effective date) is treated as superseded.
_TARIFF_STALE_DAYS = 500

_ENERGY_EXCLUDED_RE = re.compile(
    r"LIGHTING|SENTINEL|UNMETERED|EMBEDDED|MICRO\s*FIT|\bFIT\b|STANDBY|GENERATION|DGEN|STORAGE|"
    r"DEMAND BILLED|ELECTRIC VEHICLE|\bEVC?\b|WHOLESALE|SUB[- ]?TRANSMISSION|LARGE USE",
    re.I,
)
_DENSITY_CODE_RE = re.compile(r"-\s*(AUGE|AGSE|UGE|GSE|AUR|AR|UR|R1|R2)\W*$", re.I)
_DENSITY_CODES = {
    "UR": "UR", "R1": "R1", "R2": "R2", "AUR": "AUR", "AR": "AR",
    "UGE": "UGe", "GSE": "GSe", "AUGE": "AUGe", "AGSE": "AGSe",
}
_RESIDENTIAL_DENSITY_CODES = frozenset({"UR", "R1", "R2", "AUR", "AR"})
_SME_RE = re.compile(r"^Smart Metering Entity Charge\b", re.I)
_WMS_RE = re.compile(r"Wholesale Market Service", re.I)
_CBR_RE = re.compile(r"^Capacity Based Recovery", re.I)
_RRRP_RE = re.compile(r"Rural or Remote", re.I)
_SSS_RE = re.compile(r"Standard Supply Service", re.I)
_NON_RPP_RE = re.compile(r"Global Adjustment|Non[- ]*RPP", re.I)
_RATE_RIDER_RE = re.compile(r"^Rate Rider\b", re.I)
_EXCLUDING_GA_RE = re.compile(r"excl\w*\.?\s+(?:the\s+)?Global Adj", re.I)
_SUBAREA_ONLY_RE = re.compile(r"(?<!not )applicable to former [^()]*? customers only", re.I)
_SEASONAL_RE = re.compile(r"\bseasonal\b", re.I)
_NOT_SEASONAL_RE = re.compile(r"not for Seasonal", re.I)
_ENERGY_UNITS = ("$/month", "$/30 days", "$/kWh")
_FIXED_UNITS = ("$/month", "$/30 days")
_CRITERIA_WORD_RE = re.compile(r"\bcriteri(?:a|on)\b", re.I)
_CRITERIA_TAG_RE = re.compile(r"\s*-\s*Applicable only to customers that meet criteria \((?P<c>[ivx]+)\) above\b", re.I)
_CRITERION_MARK_RE = re.compile(r"(?<![\w(])(?P<c>i{1,3}|iv)\)\s*")
_ROMAN = ("i", "ii", "iii", "iv")


def clean_zone(zone: Optional[str]) -> str:
    """Normalize a published rate-zone heading to the label used in names/codes."""
    text = " ".join((zone or "").split())
    text = re.sub(r"^For\s+", "", text)
    return re.sub(r"\s+(?:Rate Zone|Service Area)$", "", text)


def _norm_class_name(name: str) -> str:
    return " ".join(name.replace("–", "-").split()).rstrip("*").strip().upper()


def select_energy_classification(cls) -> Optional[tuple[str, str]]:
    """Return (group, qualifier) for a residential or GS < 50 kW energy-billed class.

    group is "residential" or "gs"; qualifier is "" for the distributor's plain
    standard class, a density code (UR/R1/R2/AUR/AR/UGe/GSe/AUGe/AGSe) or the
    title-cased class name. Prefers oeb_tariff.classify_classification when present.
    """
    name = _norm_class_name(cls.name)
    if _ENERGY_EXCLUDED_RE.search(name):
        return None
    local: Optional[str] = None
    qualifier = name.title()
    code = (getattr(cls, "code", None) or "").upper()
    if code in _DENSITY_CODES or (m := _DENSITY_CODE_RE.search(name)):
        qualifier = _DENSITY_CODES[code or m.group(1).upper()]
        local = "residential" if qualifier in _RESIDENTIAL_DENSITY_CODES else "gs"
    elif name == "RESIDENTIAL":
        local, qualifier = "residential", ""
    elif name == "GENERAL SERVICE LESS THAN 50 KW":
        local, qualifier = "gs", ""
    elif name.startswith("SEASONAL"):
        local, qualifier = "residential", "Seasonal"
    elif "RESIDENTIAL" in name and "GENERAL SERVICE" not in name:
        local = "residential"
    classify = getattr(oeb_tariff, "classify_classification", None)
    if classify is not None:
        group = {"residential": "residential", "gs_energy": "gs"}.get(classify(cls))
        if group is None:
            return None
        return group, (qualifier if local == group else name.title())
    return (local, qualifier) if local else None


def _split_seasonal(charges: list, qualifier: str) -> list[tuple[str, list, bool]]:
    """Split a class that prints a separate Seasonal service-charge line.

    Returns [(qualifier, charges, is_seasonal_split)]; other multi-service-charge
    layouts are returned unchanged and fail validation.
    """
    services = [c for c in charges if c.kind == "service"]
    seasonal = [c for c in services if _SEASONAL_RE.search(c.label)]
    if qualifier == "Seasonal" or len(services) != 2 or len(seasonal) != 1:
        return [(qualifier, charges, False)]
    base = [c for c in charges if c is not seasonal[0]]
    other = [
        replace(c, conditional=False, condition=None) if c is seasonal[0] else c
        for c in charges
        if not (c.kind == "service" and c is not seasonal[0])
        and not _NOT_SEASONAL_RE.search(c.condition or "")
    ]
    return [(qualifier, base, False), ("Seasonal", other, True)]


def _criteria_text(eligibility: str) -> dict[str, str]:
    """Numbered eligibility criteria "i) ... ii) ..." in sequence; the last ends at its sentence."""
    flat = " ".join(eligibility.split())
    marks = []
    for m in _CRITERION_MARK_RE.finditer(flat):
        if len(marks) < len(_ROMAN) and m.group("c") == _ROMAN[len(marks)]:
            marks.append(m)
    found = {}
    for i, m in enumerate(marks):
        text = flat[m.end():marks[i + 1].start()] if i + 1 < len(marks) else re.split(
            r"\.(?=\s+[A-Z]|$)", flat[m.end():], maxsplit=1)[0]
        found[m.group("c")] = re.sub(r"(?:[\s,]+and)?[\s,.]*$", "", text).strip()
    return found


def _split_criteria(charges: list, qualifier: str, eligibility: str):
    """Split a class whose lines are tagged "Applicable only to customers that meet criteria (i) above".

    Returns None (no criteria tags), a rejection reason, or [(label, charges, eligibility)] per
    criterion: tagged lines go to their criterion (tag stripped), untagged lines are shared.
    """
    worded = [c for c in charges if _CRITERIA_WORD_RE.search(c.label)]
    if not worded:
        return None
    tags: dict[int, str] = {}
    for c in worded:
        m = _CRITERIA_TAG_RE.search(c.label)
        if not m or _CRITERIA_WORD_RE.search(c.label[:m.start()] + c.label[m.end():]):
            return f"unrecognised criteria wording in '{c.label[:80]}'"
        tags[id(c)] = m.group("c").lower()
    criteria = _criteria_text(eligibility)
    used = set(tags.values())
    if not criteria or used != set(criteria):
        return f"criteria tags {sorted(used)} do not match the eligibility criteria {sorted(criteria)}"
    if any(c.kind == "service" and id(c) not in tags for c in charges):
        return "untagged Service Charge alongside criteria-specific Service Charges"
    base = re.sub(r"^Residential\s*", "", qualifier) or "Residential"
    out = []
    for numeral, text in criteria.items():
        mine = [replace(c, label=_CRITERIA_TAG_RE.sub("", c.label).strip()) if id(c) in tags else c
                for c in charges if tags.get(id(c), numeral) == numeral]
        if sum(c.kind == "service" for c in mine) != 1:
            return f"criteria ({numeral}) does not have exactly one Service Charge"
        reg = re.search(r"Ontario Regulation (\d+/\d+)", text)
        label = f"{base} ({numeral})" + (f" O. Reg. {reg.group(1)}" if reg else "")
        out.append((label, mine, f"Criteria ({numeral}) only: {text}. Classification text: {eligibility}"))
    return out


def validate_energy_charges(charges: list, group: str, unparsed: list[str],
                            connection_optional: bool = False) -> Optional[str]:
    """Return why an energy-billed class must fail closed, or None if complete.

    ``connection_optional`` (documents configured with connection_rate "not_printed")
    accepts a class that prints no Retail Transmission Connection line at all.
    """
    services = [c for c in charges if c.kind == "service"]
    if len(services) != 1:
        return f"expected exactly one Service Charge line, found {len(services)}"
    if services[0].unit not in _FIXED_UNITS or not 0 < services[0].value < 1000:
        return f"Service Charge {services[0].value} {services[0].unit} implausible"
    dist = [c for c in charges if c.kind == "distribution"]
    if len(dist) > 1 or (group == "gs" and len(dist) != 1):
        return f"unexpected Distribution Volumetric Rate count {len(dist)}"
    if dist and dist[0].unit != "$/kWh":
        return f"Distribution Volumetric Rate unit {dist[0].unit} is not $/kWh (demand-billed class?)"
    for kind, label in (("transmission_network", "Network"), ("transmission_connection", "Connection")):
        if kind == "transmission_connection" and connection_optional and not any(c.kind == kind for c in charges):
            continue
        std = [c for c in charges if c.kind == kind and not c.conditional]
        if len(std) != 1 or std[0].unit != "$/kWh":
            return f"expected one standard $/kWh Retail Transmission {label} rate, found {len(std)}"
    regulatory = [c for c in charges if c.kind == "regulatory"]
    for pattern, units, label in ((_WMS_RE, ("$/kWh",), "WMS"), (_RRRP_RE, ("$/kWh",), "RRRP"),
                                  (_SSS_RE, _FIXED_UNITS, "SSS")):
        found = [c for c in regulatory if pattern.search(c.label)]
        if len(found) != 1 or found[0].unit not in units:
            return f"expected one {label} regulatory charge, found {len(found)}"
    for c in charges:
        if c.unit not in _ENERGY_UNITS:
            return f"'{c.label}' has unit {c.unit}, not valid for an energy-billed class"
        if c.unit == "$/kWh" and abs(c.value) >= 0.5:
            return f"'{c.label}' value {c.value} $/kWh implausible"
        if c.kind == "other" and not _SME_RE.search(c.label) and not _is_conditional_credit(c):
            return f"unrecognised delivery charge '{c.label}'"
        if c.kind == "regulatory" and not any(p.search(c.label) for p in (_WMS_RE, _CBR_RE, _RRRP_RE, _SSS_RE)) \
                and not _is_regulatory_rider(c):
            return f"unrecognised regulatory charge '{c.label}'"
    bad = [text for text in unparsed if re.search(r"\$|\d\.\d", text)]
    if bad:
        return f"unparsed charge text: {bad[0][:120]}"
    return None


def _is_conditional_credit(charge) -> bool:
    return charge.conditional and charge.value < 0 and "credit" in charge.label.casefold()


def _is_regulatory_rider(charge) -> bool:
    """A rate rider printed in the Regulatory Component (PUC's Embedded Generation Adjustment).

    Non-RPP riders there stay unrecognised: the non-RPP omission only covers delivery riders.
    """
    return bool(_RATE_RIDER_RE.match(charge.label)) and not _NON_RPP_RE.search(charge.label)


def _energy_loss_factors(sheet, cls) -> list:
    by_class = getattr(oeb_tariff, "class_loss_factors", None)
    losses = by_class(sheet, cls) if by_class else sheet.loss_factors
    return [lf for lf in losses if "> 5,000" not in lf.label]


def _connection_optional(doc: dict) -> bool:
    return doc.get("connection_rate") == oeb_tariff.CONNECTION_RATE_NOT_PRINTED


def _zone_default(doc: dict, group: str, distributor: Optional[str]) -> str:
    default = doc.get("default_zone")
    if isinstance(default, dict):
        return default.get(group, "")
    if isinstance(default, str):
        return default
    return OEB_DEFAULT_ZONES.get(distributor or "", {}).get(group, "")

_DIST_SPLIT_RE = re.compile(r"^(.*?(?:Inc\.|Corporation|Corp\.|Ltd\.|Limited|Incorporated))-(.+)$")
_RPP_DATE_RE = re.compile(r"set by the OEB (?:for|effective)\s+([A-Z][a-z]+\s+\d{1,2},\s*\d{4})")
_RPP_STALE_DAYS = 400

_OEB_FETCH_CACHE: dict[str, bytes] = {}


class OEBDataError(ValueError):
    """Official OEB source content failed a structural or freshness check."""


def clear_oeb_cache() -> None:
    _OEB_FETCH_CACHE.clear()


def _today() -> date:
    return datetime.now(timezone.utc).date()


def split_oeb_distributor(dist: str) -> tuple[str, str]:
    """Split an OEB <Dist> value into (distributor, zone) with the zone cleaned."""
    dist = " ".join(dist.split())
    match = _DIST_SPLIT_RE.match(dist)
    if not match:
        return dist, ""
    return match.group(1).strip(), clean_zone(match.group(2))


def oeb_distributor_for_registry(registry_name: str) -> Optional[str]:
    """Return the OEB distributor for a registry name, or None if merged/unknown."""
    if registry_name in OEB_MERGED_REGISTRY_NAMES:
        return None
    return OEB_REGISTRY_TO_DISTRIBUTOR.get(registry_name)


def _parse_rpp_date(text: str) -> date:
    return datetime.strptime(" ".join(text.replace(",", ", ").split()), "%B %d, %Y").date()


def _cents(text: str) -> float:
    value = float(text.strip())
    if not 1.0 <= value <= 100.0:
        raise OEBDataError(f"RPP price {value} ¢/kWh outside plausible range")
    return round(value / 100.0, 6)


def _kwh_threshold(text: str, label: str) -> float:
    match = re.search(label + r"\s*[–-]\s*first\s+([\d,]+)\s*kWh/month", text)
    if not match:
        raise OEBDataError(f"RPP tier threshold for {label!r} not found")
    value = float(match.group(1).replace(",", ""))
    if value <= 0:
        raise OEBDataError(f"Non-positive tier threshold for {label!r}")
    return value


def parse_rpp_page(html: str, today: Optional[date] = None) -> dict:
    """Parse current OEB RPP prices, periods, thresholds and effective date.

    Raises OEBDataError when any table, period, price or the date is missing,
    or when the effective date is in the future or older than about 13 months.
    """
    from scrapers.utils.parsing import parse_html

    today = today or _today()
    soup = parse_html(html)
    text = " ".join(soup.get_text(" ", strip=True).split())
    date_match = _RPP_DATE_RE.search(text)
    if not date_match:
        raise OEBDataError("RPP effective date sentence not found")
    effective = _parse_rpp_date(date_match.group(1))
    if effective > today:
        raise OEBDataError(f"RPP effective date {effective} is in the future")
    if (today - effective).days > _RPP_STALE_DAYS:
        raise OEBDataError(f"RPP effective date {effective} is stale")

    tables: dict[str, list[list[str]]] = {}
    for table in soup.find_all("table"):
        rows = [
            [" ".join(c.get_text(" ", strip=True).split()) for c in tr.find_all(["th", "td"])]
            for tr in table.find_all("tr")
        ]
        if rows and rows[0]:
            tables[rows[0][0]] = rows

    def table(key: str, columns: int) -> list[list[str]]:
        rows = tables.get(key)
        if not rows:
            raise OEBDataError(f"RPP table {key!r} not found")
        if "¢/kWh" not in rows[0][-1]:
            raise OEBDataError(f"RPP table {key!r} price unit changed: {rows[0][-1]!r}")
        if any(len(r) != columns for r in rows):
            raise OEBDataError(f"RPP table {key!r} column layout changed")
        return rows

    def season(header: str, name: str) -> str:
        match = re.fullmatch(name + r"\s*\((.+)\)", header)
        if not match:
            raise OEBDataError(f"RPP season header changed: {header!r}")
        return match.group(1).strip()

    tou_rows = table("TOU Price Periods", 4)
    winter = season(tou_rows[0][1], "Winter")
    summer = season(tou_rows[0][2], "Summer")
    tou = {}
    for row in tou_rows[1:]:
        tou[row[0]] = {"winter_hours": row[1], "summer_hours": row[2], "price": _cents(row[3])}
    if set(tou) != {"Off-Peak", "Mid-Peak", "On-Peak"}:
        raise OEBDataError(f"RPP TOU periods changed: {sorted(tou)}")

    ulo_rows = table("ULO Price Periods", 3)
    if ulo_rows[0][1] != "All Year":
        raise OEBDataError(f"RPP ULO season header changed: {ulo_rows[0][1]!r}")
    ulo = {row[0]: {"hours": row[1], "price": _cents(row[2])} for row in ulo_rows[1:]}
    if set(ulo) != {"Ultra-Low Overnight", "Weekend Off-Peak", "Mid-Peak", "On-Peak"}:
        raise OEBDataError(f"RPP ULO periods changed: {sorted(ulo)}")

    tier_rows = table("Tier Thresholds", 4)
    if season(tier_rows[0][1], "Winter") != winter or season(tier_rows[0][2], "Summer") != summer:
        raise OEBDataError("RPP tier seasons differ from TOU seasons")
    tiers = {row[0]: row for row in tier_rows[1:]}
    if set(tiers) != {"Tier 1", "Tier 2"}:
        raise OEBDataError(f"RPP tiers changed: {sorted(tiers)}")
    tier1 = tiers["Tier 1"]
    thresholds = {
        "res_winter": _kwh_threshold(tier1[1], "Residential"),
        "res_summer": _kwh_threshold(tier1[2], "Residential"),
        "gs_winter": _kwh_threshold(tier1[1], "Non-residential"),
        "gs_summer": _kwh_threshold(tier1[2], "Non-residential"),
    }
    return {
        "effective_date": effective.isoformat(),
        "winter_months": winter,
        "summer_months": summer,
        "tou": tou,
        "ulo": ulo,
        "tier1_price": _cents(tier1[3]),
        "tier2_price": _cents(tiers["Tier 2"][3]),
        "thresholds": thresholds,
    }


def _num(row: dict, key: str) -> Optional[float]:
    raw = row.get(key)
    if raw is None or raw.strip() == "":
        return None
    try:
        return float(raw)
    except ValueError as exc:
        raise OEBDataError(f"{key}={raw!r} is not numeric") from exc


def _validate_billdata_row(row: dict, kind: str, rpp: dict, year: int) -> dict:
    """Return validated numeric values for one feed row or raise OEBDataError."""
    if int(row["YEAR"] or 0) != year:
        raise OEBDataError(f"rate year {row['YEAR']!r} is not {year}")
    values = {k: _num(row, k) for k in (
        "SC", "VC", "DC", "OC", "OFC", "Net", "Conn", "WMSR", "RRRP", "SSS", "LF",
        "ET1", "RPP1", "RPP2", "RPPOffP", "RPPMidP", "RPPOnP", "ULO_overnight",
        "ULO_weekendoffp", "ULO_midp", "ULO_onp", "DRP", "DRP_Rate",
    )}
    for key in ("SC", "Net", "Conn", "WMSR", "RRRP", "SSS", "LF", "OFC", "OC", "ET1", "DRP"):
        if values[key] is None:
            raise OEBDataError(f"required field {key} is empty")
    for key in ("SC", "Net", "Conn", "WMSR", "RRRP", "SSS"):
        if values[key] <= 0:
            raise OEBDataError(f"{key}={values[key]} must be positive")
    for key in ("Net", "Conn", "WMSR", "RRRP"):
        if values[key] >= 0.1:
            raise OEBDataError(f"{key}={values[key]} is not a plausible $/kWh rate (non-kWh billing?)")
    if not 1.0 <= values["LF"] < 1.25:
        raise OEBDataError(f"loss factor {values['LF']} outside 1.00-1.25")
    if values["VC"] is not None and values["VC"] <= 0:
        raise OEBDataError(f"VC={values['VC']} must be positive when present")
    if abs(values["OC"]) >= 0.1 or abs(values["OFC"]) >= 50:
        raise OEBDataError("other charges outside plausible range")
    if values["SC"] > 2000:
        raise OEBDataError(f"SC={values['SC']} implausible for this class")
    total_vol = (values["VC"] or 0.0) + values["OC"]
    if abs((values["DC"] or 0.0) - total_vol) > 1e-6:
        raise OEBDataError(f"DC={values['DC']} != VC+OC={total_vol}")
    if values["DRP"] not in (0.0, 1.0):
        raise OEBDataError(f"DRP flag {values['DRP']} not 0/1")
    expected = {
        "RPPOffP": rpp["tou"]["Off-Peak"]["price"],
        "RPPMidP": rpp["tou"]["Mid-Peak"]["price"],
        "RPPOnP": rpp["tou"]["On-Peak"]["price"],
        "ULO_overnight": rpp["ulo"]["Ultra-Low Overnight"]["price"],
        "ULO_weekendoffp": rpp["ulo"]["Weekend Off-Peak"]["price"],
        "ULO_midp": rpp["ulo"]["Mid-Peak"]["price"],
        "ULO_onp": rpp["ulo"]["On-Peak"]["price"],
        "RPP1": rpp["tier1_price"],
        "RPP2": rpp["tier2_price"],
    }
    for key, price in expected.items():
        if values[key] is None or abs(values[key] - price) > 1e-6:
            raise OEBDataError(f"{key}={values[key]} disagrees with the OEB RPP page ({price})")
    thresholds = rpp["thresholds"]
    allowed = (
        {thresholds["res_winter"], thresholds["res_summer"]} if kind == "residential"
        else {thresholds["gs_winter"], thresholds["gs_summer"]}
    )
    if values["ET1"] not in allowed:
        raise OEBDataError(f"ET1={values['ET1']} disagrees with RPP thresholds {sorted(allowed)}")
    return values


def parse_bill_data(
    xml_bytes: bytes,
    kind: str,
    rpp: dict,
    today: Optional[date] = None,
) -> tuple[dict[str, list[dict]], list[str]]:
    """Parse an OEB BillData XML into validated zone rows per OEB distributor.

    Returns ({distributor: [zone dicts]}, [rejection messages]). Structural
    changes raise OEBDataError for the whole file; bad rows reject only their
    own distributor zone.
    """
    if kind not in ("residential", "gs"):
        raise ValueError(kind)
    today = today or _today()
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise OEBDataError(f"BillData XML unreadable: {exc}") from exc
    if root.tag != "BillDataTable" or not len(root):
        raise OEBDataError(f"unexpected BillData root {root.tag!r}")
    qualifiers = OEB_RES_CLASS_QUALIFIERS if kind == "residential" else OEB_GS_CLASS_QUALIFIERS
    zones: dict[str, dict[str, dict]] = {}
    rejected: list[str] = []
    for element in root:
        if element.tag != "BillDataRow":
            raise OEBDataError(f"unexpected BillData element {element.tag!r}")
        tags = [child.tag for child in element]
        if set(tags) != OEB_BILLDATA_FIELDS or len(tags) != len(OEB_BILLDATA_FIELDS):
            raise OEBDataError(
                "BillData row fields changed: missing "
                f"{sorted(OEB_BILLDATA_FIELDS - set(tags))}, extra {sorted(set(tags) - OEB_BILLDATA_FIELDS)}"
            )
        row = {child.tag: (child.text or "") for child in element}
        dist_text = " ".join(row["Dist"].split())
        class_text = " ".join(row["Class"].split())
        distributor, zone = split_oeb_distributor(dist_text)
        where = f"{dist_text} / {class_text}"
        qualifier = qualifiers.get(class_text.upper())
        if qualifier is None:
            rejected.append(f"{where}: unknown class label")
            continue
        label = " / ".join(part for part in (zone, qualifier) if part)
        try:
            values = _validate_billdata_row(row, kind, rpp, today.year)
        except OEBDataError as exc:
            rejected.append(f"{where}: {exc}")
            continue
        entry = {
            "distributor": distributor,
            "zone": label,
            "dist": dist_text,
            "class": class_text,
            "year": int(row["YEAR"]),
            "values": values,
        }
        by_label = zones.setdefault(distributor, {})
        if label in by_label:
            existing = by_label[label]
            if existing is not None and existing["values"] != values:
                rejected.append(f"{where}: conflicting duplicate zone {label!r}")
                by_label[label] = None
            continue
        by_label[label] = entry
    result = {
        dist: [z for z in by_label.values() if z is not None]
        for dist, by_label in zones.items()
    }
    return {d: z for d, z in result.items() if z}, rejected


def _slug(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", text.upper()).strip("-")


# ═══════════════════════════════════════════════════════════════
# Ontario LDC Scraper class
# ═══════════════════════════════════════════════════════════════

class OntarioLDCScraper(BaseScraper):
    """
    Data-driven scraper for any Ontario electricity LDC.

    All Ontario LDCs share the same OEB-regulated RPP energy prices;
    only delivery charges differ. LDCs listed in OEB_TARIFF_DOCUMENTS are
    built live from their approved tariff; others use ONTARIO_LDC_DATA seeds.

    Produces tariffs for:
      - Residential: TOU, Tiered, ULO (per rate zone/class when live)
      - GS < 50 kW: TOU, Tiered, ULO (per rate zone/class when live)
      - GS >= 50 kW / Large Use: demand classes (live: delivery charges plus a
        value-less market energy component) or seed
      - Street Lighting (seed estimate; excluded class)
    """

    def __init__(self, registry_entry: dict | None = None):
        # Read utility name from registry entry
        if registry_entry:
            self._ldc_name = registry_entry["name"]
            self._source_urls = [s["url"] for s in registry_entry.get("sources", [])]
        else:
            self._ldc_name = "Unknown Ontario LDC"
            self._source_urls = [OEB_SOURCE_URL]

        super().__init__(utility_name=self._ldc_name, province="ON")

        self._oeb_distributor = oeb_distributor_for_registry(self._ldc_name)
        self._demand_records: Optional[list[TariffRecord]] = None
        self.tariff_rejections: dict[str, str] = {}
        self.xml_discrepancies: list[str] = []

        # Look up delivery charges
        self._ldc_data = ONTARIO_LDC_DATA.get(self._ldc_name)
        if not self._ldc_data and self._ldc_name not in OEB_TARIFF_DOCUMENTS:
            self.logger.error("No approved delivery data for %s; no estimated tariff will be emitted", self._ldc_name)

    # Plan key, legacy tariff name, legacy code, rate structure
    RES_PLANS = (
        ("tou", "Residential -- Time-of-Use (TOU)", "TOU-R", "tou"),
        ("tiered", "Residential -- Tiered Pricing", "TIER-R", "tiered"),
        ("ulo", "Residential -- Ultra-Low Overnight (ULO)", "ULO-R", "tou"),
    )
    GS_PLANS = (
        ("tou", "General Service < 50 kW -- TOU", "GS-TOU-S", "tou"),
        ("tiered", "General Service < 50 kW -- Tiered", "GS-TIER-S", "tiered"),
        ("ulo", "General Service < 50 kW -- ULO", "GS-ULO-S", "tou"),
    )
    DEMAND_CODES = frozenset({"GS-D1", "GS-D2", "GS-D3"})

    def set_demand_records(self, records: Optional[list[TariffRecord]]) -> None:
        """Supply externally built GS >= 50 kW records that replace the GS-D seeds.

        The records are emitted as given (their provenance is the caller's
        responsibility); seed GS-D1/D2/D3 are then omitted entirely.
        """
        self._demand_records = list(records) if records is not None else None

    def _external_demand_records(self) -> Optional[list[TariffRecord]]:
        return self._demand_records

    def scrape(self) -> list[TariffRecord]:
        seed = self._seed_data()
        res_codes = {p[2] for p in self.RES_PLANS}
        gs_codes = {p[2] for p in self.GS_PLANS}
        groups = {
            "residential": [r for r in seed if r.tariff_code in res_codes],
            "gs": [r for r in seed if r.tariff_code in gs_codes],
        }
        other = [r for r in seed if r.tariff_code not in res_codes | gs_codes]

        live = self._try_live_scrape() or {}
        external = self._external_demand_records()
        built_demand = live.get("demand") or []
        demand = external if external is not None else built_demand
        if external is not None or built_demand or self._class_rejected("demand"):
            other = [r for r in other if r.tariff_code not in self.DEMAND_CODES]

        ordered: list[TariffRecord] = []
        fallback: list[TariffRecord] = []
        for group in ("residential", "gs"):
            live_records = live.get(group) or []
            ordered.extend(live_records)
            has_default = any(r.tariff_code in res_codes | gs_codes for r in live_records)
            if not has_default and self._class_rejected(group):
                self.logger.info("%s %s class rejected in its approved tariff; no estimate emitted",
                                 self._ldc_name, group)
            elif not has_default:
                ordered.extend(groups[group])
                fallback.extend(groups[group])
        if not live:
            self.logger.info("Using seed data for %s residential/GS < 50 kW", self._ldc_name)
        if fallback:
            self.mark_fallback(fallback)
        for subset, reason in (
            ([r for r in other if r.tariff_code in self.DEMAND_CODES],
             "Approved-tariff demand classes not configured or not completely verified"),
            ([r for r in other if r.tariff_code not in self.DEMAND_CODES],
             "Excluded class with no live parser; seed estimate only"),
        ):
            if subset:
                self.mark_fallback(subset, reason)
        ordered.extend(other)
        if demand:
            ordered.extend(demand)
        return ordered

    def _class_rejected(self, group: str) -> bool:
        """A configured tariff rejected a class of this group (not a whole sheet)."""
        keys = self.tariff_rejections
        if self._ldc_name not in OEB_TARIFF_DOCUMENTS or any(k.startswith("sheet:") for k in keys):
            return False
        return any(k.startswith(f"{group}:") for k in keys)

    def _fetch_oeb(self, url: str) -> bytes:
        if url not in _OEB_FETCH_CACHE:
            _OEB_FETCH_CACHE[url] = self.fetch_bytes(url)
        return _OEB_FETCH_CACHE[url]

    def _try_live_scrape(self) -> Optional[dict[str, list[TariffRecord]]]:
        """Build live records from the LDC's approved tariff(s) and OEB RPP prices.

        Returns {"residential": [...], "gs": [...], "demand": [...]} with only the
        groups that produced records, or None. Each document, rate zone and class
        fails closed on its own; a missing default zone leaves that group's seed.
        """
        if self._ldc_name in OEB_MERGED_REGISTRY_NAMES:
            self.logger.info(
                "%s has no separate OEB distributor (%s); seed estimates only",
                self._ldc_name, OEB_MERGED_REGISTRY_NAMES[self._ldc_name],
            )
            return None
        documents = OEB_TARIFF_DOCUMENTS.get(self._ldc_name)
        if not documents:
            self.logger.info("No OEB-approved tariff configured for %s; seed estimates only", self._ldc_name)
            return None

        today = _today()
        sheets = [pair for doc in documents for pair in self._load_sheets(doc, today)]
        if not sheets:
            return None
        self._record_absent_classes(sheets)
        try:
            rpp: Optional[dict] = parse_rpp_page(
                self._fetch_oeb(OEB_SOURCE_URL).decode("utf-8", errors="replace"))
        except Exception as exc:
            self.logger.warning("OEB RPP page failed for %s: %s; no RPP tariffs built", self._ldc_name, exc)
            rpp = None

        out: dict[str, list[TariffRecord]] = {"residential": [], "gs": [], "demand": []}
        entries: list[dict] = []
        for doc, sheet in sheets:
            if rpp is not None:
                entries.extend(self._energy_entries(doc, sheet, today))
            out["demand"].extend(self._tariff_demand_records(doc, sheet, today))
        out["demand"] = self._drop_duplicate_demand(out["demand"])
        if rpp is not None:
            entries = self._drop_duplicate_labels(entries)
            for group in ("residential", "gs"):
                out[group] = self._build_rpp_records(group, [e for e in entries if e["group"] == group], rpp)
            self._xml_cross_check(entries, rpp)
        for records in out.values():
            if records:
                self.mark_live_parsed(records)
        return {k: v for k, v in out.items() if v} or None

    def _record_absent_classes(self, sheets: list) -> None:
        """An accepted approved tariff that publishes no class of a group counts as that group's rejection."""
        categories = {oeb_tariff.classify_classification(c) for _, sheet in sheets for c in sheet.classifications}
        for group, wanted, label in (
            ("gs", {"gs_energy"}, "General Service < 50 kW"),
            ("demand", {"gs_demand", "large_use", "sub_transmission"}, "General Service demand-billed"),
        ):
            if not categories & wanted:
                self.tariff_rejections[f"{group}:absent"] = (
                    f"approved tariff publishes no {label} classification; no estimate emitted")

    def _fetch_tariff_pages(self, url: str, **options) -> list:
        from scrapers.utils.parsing import extract_pdf_pages
        extract = getattr(oeb_tariff, "extract_tariff_pages", extract_pdf_pages)
        return extract(self._fetch_oeb(url), **options)

    def _load_sheets(self, doc: dict, today: date) -> list[tuple[dict, "oeb_tariff.TariffSheet"]]:
        """Fetch and parse one tariff document; return the accepted (doc, zone sheet) pairs."""
        url = doc["url"]
        try:
            pages = self._fetch_tariff_pages(url, **doc.get("extract", {}))
        except Exception as exc:
            self.logger.warning("OEB tariff fetch failed for %s (%s): %s", self._ldc_name, url, exc)
            return []
        if not pages:
            self.logger.warning("OEB tariff %s for %s has no extractable text", url, self._ldc_name)
            return []
        try:
            zones = oeb_tariff.parse_tariff_zones(pages, url, today)
        except Exception as exc:
            self.logger.warning("OEB tariff %s for %s could not be parsed: %s", url, self._ldc_name, exc)
            return []
        wanted = doc.get("zones")
        wanted_labels = None if wanted is None else {clean_zone(z).casefold() for z in wanted}
        accepted = []
        for raw_zone, sheet in zones.items():
            zone = clean_zone(raw_zone)
            if wanted_labels is not None and zone.casefold() not in wanted_labels:
                continue
            reason = self._sheet_problem(doc, sheet, today)
            if reason:
                self.tariff_rejections[f"sheet:{zone}"] = reason
                self.logger.warning("Rejected OEB tariff zone %r for %s: %s", zone or "standard", self._ldc_name, reason)
                continue
            accepted.append((doc, sheet))
        if not accepted:
            self.logger.warning("No usable rate zone in OEB tariff %s for %s", url, self._ldc_name)
        return accepted

    def _sheet_problem(self, doc: dict, sheet, today: date) -> Optional[str]:
        if sheet.errors:
            return "; ".join(sheet.errors)
        if not sheet.effective_date:
            return "effective date missing"
        expected = self._oeb_distributor
        if expected and " ".join((sheet.distributor or "").split()).casefold() != expected.casefold():
            return f"distributor {sheet.distributor!r} is not {expected!r}"
        if doc.get("case_number") and sheet.case_number != doc["case_number"]:
            return f"case number {sheet.case_number!r} is not the configured {doc['case_number']!r}"
        if (today - date.fromisoformat(sheet.effective_date)).days > _TARIFF_STALE_DAYS:
            return f"tariff effective {sheet.effective_date} is stale (likely superseded)"
        return None

    @staticmethod
    def _delivery_date(sheet) -> str:
        return max(d for d in (sheet.effective_date, sheet.implementation_date) if d)

    def _energy_entries(self, doc: dict, sheet, today: date) -> list[dict]:
        """Validated residential / GS < 50 kW classification entries for one zone sheet."""
        zone = clean_zone(sheet.rate_zone)
        as_of = today.isoformat()
        entries = []
        for cls in sheet.classifications:
            selected = select_energy_classification(cls)
            if selected is None:
                continue
            group, qualifier = selected
            if not cls.charges:
                self.logger.debug("%s %s has no charge lines (overview heading)", zone, cls.name)
                continue
            split = _split_criteria(list(cls.charges), qualifier, cls.eligibility)
            if isinstance(split, str):
                key = f"{group}:{' / '.join(p for p in (zone, qualifier) if p) or 'standard'}"
                self.tariff_rejections[key] = split
                self.logger.warning("Rejected OEB tariff %s for %s: %s", key, self._ldc_name, split)
                continue
            for crit_qual, crit_charges, eligibility in split or [(qualifier, list(cls.charges), None)]:
                for qual, charges, seasonal_split in _split_seasonal(crit_charges, crit_qual):
                    label = " / ".join(part for part in (zone, qual) if part)
                    key = f"{group}:{label or 'standard'}"
                    reason = validate_energy_charges(charges, group, cls.unparsed,
                                                     connection_optional=_connection_optional(doc))
                    if reason:
                        self.tariff_rejections[key] = reason
                        self.logger.warning("Rejected OEB tariff %s for %s: %s", key, self._ldc_name, reason)
                        continue
                    entries.append(self._energy_entry(
                        doc, sheet, cls, group, label, charges, seasonal_split, as_of, eligibility))
        return entries

    def _energy_entry(self, doc, sheet, cls, group, label, charges, seasonal_split, as_of,
                      eligibility: Optional[str] = None) -> dict:
        when = self._delivery_date(sheet)
        omitted: dict[str, list[str]] = {"non_rpp": [], "subarea": [], "expired": []}
        applied = []
        for c in charges:
            if c.kind == "rider" and _NON_RPP_RE.search(c.label) and not _EXCLUDING_GA_RE.search(c.label):
                omitted["non_rpp"].append(c.label)
            elif _SUBAREA_ONLY_RE.search(c.label):
                omitted["subarea"].append(c.label)
            elif c.end_date and c.end_date < as_of:
                omitted["expired"].append(c.label)
            else:
                applied.append(c)
        components = [self._tariff_component(c, sheet, cls.name, when) for c in applied]
        if group == "gs":
            for allowance in sheet.allowances:
                if (allowance.unit == "$/kWh" and "allowance" in allowance.label.casefold()
                        and re.search(r"less than 50 kW|Energy Billed", allowance.label, re.I)):
                    components.append(self._tariff_component(allowance, sheet, cls.name, when))
        class_notes = list(cls.notes)
        if _connection_optional(doc) and not any(c.kind == "transmission_connection" for c in charges):
            class_notes.append(oeb_tariff.connection_not_printed_note(self._ldc_name, sheet.case_number))
        return {
            "group": group,
            "label": label,
            "default": label == _zone_default(doc, group, self._oeb_distributor),
            "sheet": sheet,
            "class_name": cls.name,
            "class_notes": class_notes,
            "losses": _energy_loss_factors(sheet, cls),
            "eligibility": cls.eligibility if eligibility is None else eligibility,
            "pages": list(cls.pages),
            "charges": applied,
            "components": components,
            "omitted": omitted,
            "seasonal_split": seasonal_split,
            "when": when,
        }

    def _drop_duplicate_labels(self, entries: list[dict]) -> list[dict]:
        seen: dict[tuple[str, str], int] = {}
        for e in entries:
            seen[(e["group"], e["label"])] = seen.get((e["group"], e["label"]), 0) + 1
        for (group, label), count in seen.items():
            if count > 1:
                self.tariff_rejections[f"{group}:{label or 'standard'}"] = "conflicting duplicate classifications"
                self.logger.warning("Rejected %s %r for %s: %d classifications map to it",
                                    group, label, self._ldc_name, count)
        return [e for e in entries if seen[(e["group"], e["label"])] == 1]

    def _drop_duplicate_demand(self, records: list[TariffRecord]) -> list[TariffRecord]:
        counts: dict[str, int] = {}
        for r in records:
            counts[r.tariff_code] = counts.get(r.tariff_code, 0) + 1
        for code, count in counts.items():
            if count > 1:
                self.tariff_rejections[f"demand:{code}"] = "conflicting duplicate classifications"
                self.logger.warning("Rejected demand class %r for %s: %d classifications map to it",
                                    code, self._ldc_name, count)
        return [r for r in records if counts[r.tariff_code] == 1]

    def _tariff_component(self, charge, sheet, cls_name: str, when: str) -> RateComponent:
        ctype, sub = {
            "service": ("fixed", "service_charge"),
            "distribution": ("distribution", "distribution_volumetric"),
            "rider": ("rider", None),
            "other": ("fixed", "smart_metering_entity"),
            "transmission_network": ("transmission", "network_service"),
            "transmission_connection": ("transmission", "line_and_transformation_connection"),
            "low_voltage": ("delivery", "low_voltage_service"),
            "regulatory": ("regulatory", None),
        }[charge.kind]
        if charge.kind == "regulatory":
            sub = next((name for pattern, name in (
                (_WMS_RE, "wholesale_market_service"), (_CBR_RE, "capacity_based_recovery"),
                (_RRRP_RE, "rural_remote_rate_protection"), (_SSS_RE, "standard_supply_service"),
            ) if pattern.search(charge.label)), None)
        if charge.kind == "other" and _is_conditional_credit(charge):
            ctype, sub = "rebate", "conditional_credit"
        if charge.section == "allowances":
            ctype, sub = "rebate", "transformer_ownership_allowance"
        notes = []
        if charge.condition:
            notes.append(charge.condition if charge.condition.startswith("Conditional")
                         else f"Conditional: {charge.condition}")
        if charge.term:
            notes.append(charge.term)
        if re.search(r"interim basis", charge.label, re.I):
            notes.append("Approved on an interim basis")
        if charge.period == "30 days":
            notes.append("Published per 30 days")
        zone = f" {sheet.rate_zone}," if sheet.rate_zone else ""
        dates = f"effective {sheet.effective_date}"
        if sheet.implementation_date and sheet.implementation_date != sheet.effective_date:
            dates += f", implemented {sheet.implementation_date}"
        return RateComponent(
            component_type=ctype,
            component_name=charge.label,
            charge_value=charge.value,
            charge_unit=charge.unit,
            sub_component=sub,
            effective_date=when,
            end_date=charge.end_date,
            source_url=sheet.source_url,
            source_detail=(f"PDF page {charge.page_number} ({sheet.case_number or 'OEB tariff'},{zone} "
                           f"{cls_name} {charge.section}; tariff {dates})"),
            confidence="high",
            notes="; ".join(notes) or None,
        )

    def _build_rpp_records(self, group: str, entries: list[dict], rpp: dict) -> list[TariffRecord]:
        plans = self.RES_PLANS if group == "residential" else self.GS_PLANS
        records = []
        for entry in sorted(entries, key=lambda e: (not e["default"], e["label"])):
            sheet = entry["sheet"]
            pages = entry["pages"]
            page_text = f"PDF page {pages[0]}" if len(pages) == 1 else f"PDF pages {pages[0]}-{pages[-1]}"
            zone = f", {sheet.rate_zone}" if sheet.rate_zone else ""
            for plan, base_name, base_code, structure in plans:
                name = base_name if entry["default"] else f"{base_name} [{entry['label']}]"
                code = base_code if entry["default"] else f"{base_code}-{_slug(entry['label'])}"
                records.append(TariffRecord(
                    utility_name=self._ldc_name,
                    province="ON",
                    utility_type="electricity",
                    tariff_name=name,
                    tariff_code=code,
                    customer_class="residential" if group == "residential" else "commercial",
                    sub_class=None if group == "residential" else "GS < 50 kW",
                    description=(f"OEB-approved tariff: {sheet.distributor}{zone} / {entry['class_name']} "
                                 f"Service Classification, with OEB RPP {plan.upper()} commodity prices"),
                    eligibility=(entry["eligibility"][:1500] or None) if entry["eligibility"] else (
                        None if group == "residential"
                        else "Non-residential customers with monthly peak demand under 50 kW"),
                    demand_max_kw=None if group == "residential" else 50,
                    rate_structure=structure,
                    pricing_method="regulated",
                    effective_date=max(rpp["effective_date"], entry["when"]),
                    source_url=sheet.source_url,
                    source_page=f"{page_text} ({sheet.case_number}); RPP prices: OEB electricity-rates page",
                    confidence="high",
                    notes=self._rpp_tariff_notes(entry, rpp),
                    components=[*self._rpp_components(plan, group, rpp),
                                *self._copy_components(entry["components"])],
                ))
        return records

    @staticmethod
    def _copy_components(components: list[RateComponent]) -> list[RateComponent]:
        return [replace(c) for c in components]

    @staticmethod
    def _rpp_tariff_notes(entry: dict, rpp: dict) -> str:
        sheet = entry["sheet"]
        dates = f"effective {sheet.effective_date}"
        if sheet.implementation_date and sheet.implementation_date != sheet.effective_date:
            dates += f", implemented {sheet.implementation_date}"
        notes = [
            f"Delivery, transmission and regulatory charges from the OEB-approved Tariff of Rates and "
            f"Charges ({sheet.case_number}, {dates}); RPP commodity prices set by the OEB effective "
            f"{rpp['effective_date']}.",
            "Each charge is a separate component with its own source and date; no bill total is calculated.",
        ]
        if entry["when"] != sheet.effective_date:
            notes.append("Delivery components are dated from the implementation date, when the approved "
                         "rates began to be billed.")
        omitted = entry["omitted"]
        if omitted["non_rpp"]:
            notes.append("Omitted because they apply only to non-RPP customers: "
                         + "; ".join(omitted["non_rpp"]) + ".")
        if omitted["subarea"]:
            notes.append("Omitted sub-area rider sets (apply only to the named former service area): "
                         + "; ".join(omitted["subarea"]) + ".")
        if omitted["expired"]:
            notes.append("Expired riders omitted: " + "; ".join(omitted["expired"]) + ".")
        if entry["seasonal_split"]:
            notes.append(f"Seasonal service charge is printed as an alternative Service Charge line in the "
                         f"{entry['class_name']} classification; the classification's other charges are "
                         "listed once and are shown as published.")
        losses = entry["losses"]
        if losses:
            notes.append("Published total loss factors (multiply metered kWh for commodity and some charges; "
                         "not applied here): " + "; ".join(f"{lf.label} {lf.value}" for lf in losses) + ".")
        else:
            notes.append("No loss factor was parsed for this rate zone; the approved loss factor still "
                         "adjusts metered kWh.")
        notes.extend(entry["class_notes"])
        notes.append("The Ontario Electricity Rebate, HST and Distribution Rate Protection adjustments are "
                     "not part of these records.")
        return " ".join(notes)

    def _tariff_demand_records(self, doc: dict, sheet, today: date) -> list[TariffRecord]:
        """Delivery-only demand-class records from oeb_tariff, dated like the RPP records."""
        try:
            records = oeb_tariff.build_demand_records(sheet, self._ldc_name, today=today,
                                                      connection_rate=doc.get("connection_rate"))
        except Exception as exc:
            self.logger.warning("OEB demand classes failed for %s: %s", self._ldc_name, exc)
            return []
        zone = clean_zone(sheet.rate_zone)
        for cls_name, reason in sheet.rejections.items():
            self.tariff_rejections[f"demand:{zone or 'standard'}:{cls_name}"] = reason
        when = self._delivery_date(sheet)
        suffix = zone and zone != _zone_default(doc, "demand", self._oeb_distributor)
        for record in records:
            if suffix:
                record.tariff_code = f"{record.tariff_code}-{_slug(zone)}"
            if when != record.effective_date:
                record.effective_date = when
                for component in record.components:
                    if component.effective_date == sheet.effective_date:
                        component.effective_date = when
                record.notes = (record.notes or "") + (
                    " Components are dated from the implementation date, when the approved rates began "
                    "to be billed.")
        return records

    def _xml_cross_check(self, entries: list[dict], rpp: dict) -> None:
        """Compare tariff entries with the OEB bill-data feed; log differences, never alter records."""
        distributor = self._oeb_distributor
        if not distributor:
            return
        for group, url in (("residential", OEB_BILLDATA_RES_URL), ("gs", OEB_BILLDATA_GS_URL)):
            try:
                zones, _ = parse_bill_data(self._fetch_oeb(url), group, rpp)
            except Exception as exc:
                self.logger.info("OEB bill-data cross-check (%s) unavailable for %s: %s", group, self._ldc_name, exc)
                continue
            xml = {z["zone"]: z["values"] for z in zones.get(distributor, [])}
            mine = {e["label"]: e for e in entries if e["group"] == group}
            found: list[str] = []
            for label in sorted(set(xml) - set(mine)):
                found.append(f"{group} [{label or 'standard'}]: in OEB bill data, no parsed tariff class")
            for label in sorted(set(mine) - set(xml)):
                found.append(f"{group} [{label or 'standard'}]: parsed tariff class absent from OEB bill data")
            for label in sorted(set(xml) & set(mine)):
                for field, xml_value, tariff_value in self._xml_pairs(xml[label], mine[label]):
                    if xml_value is None and tariff_value is None:
                        continue
                    tolerance = 0.005 if field in ("SC", "SSS") else 0.00005
                    if (xml_value is None or tariff_value is None
                            or abs(xml_value - tariff_value) > tolerance):
                        found.append(f"{group} [{label or 'standard'}] {field}: "
                                     f"bill data {xml_value} vs tariff {tariff_value}")
            if found:
                self.xml_discrepancies.extend(found)
                self.logger.warning("OEB bill-data cross-check for %s (records unchanged): %s",
                                    self._ldc_name, " | ".join(found))

    @staticmethod
    def _xml_pairs(values: dict, entry: dict) -> list[tuple[str, Optional[float], Optional[float]]]:
        charges = entry["charges"]

        def one(kind: str, pattern=None) -> Optional[float]:
            found = [c.value for c in charges if c.kind == kind and not (
                kind.startswith("transmission") and c.conditional)
                and (pattern is None or pattern.search(c.label))]
            return found[0] if len(found) == 1 else None

        wms = one("regulatory", _WMS_RE)
        cbr = one("regulatory", _CBR_RE) or 0.0
        losses = [lf.value for lf in entry["losses"] if "Primary" not in lf.label]
        return [
            ("SC", values["SC"], one("service")),
            ("VC", values["VC"], one("distribution")),
            ("Net", values["Net"], one("transmission_network")),
            ("Conn", values["Conn"], one("transmission_connection")),
            ("WMSR", values["WMSR"], None if wms is None else round(wms + cbr, 6)),
            ("RRRP", values["RRRP"], one("regulatory", _RRRP_RE)),
            ("SSS", values["SSS"], one("regulatory", _SSS_RE)),
            ("LF", values["LF"], losses[0] if len(losses) == 1 else None),
        ]

    @staticmethod
    def _rpp_components(plan: str, kind: str, rpp: dict) -> list[RateComponent]:
        when = rpp["effective_date"]
        winter, summer = rpp["winter_months"], rpp["summer_months"]

        def energy(name: str, value: float, detail: str, **kw) -> RateComponent:
            return RateComponent(
                component_type="energy", component_name=name, charge_value=value,
                charge_unit="$/kWh", effective_date=when, source_url=OEB_SOURCE_URL,
                source_detail=f"OEB RPP prices set for {when}: {detail}", confidence="high", **kw,
            )

        if plan == "tou":
            out = []
            for label, period in (("Off-Peak", "off-peak"), ("Mid-Peak", "mid-peak"), ("On-Peak", "on-peak")):
                row = rpp["tou"][label]
                hours = f"Winter ({winter}): {row['winter_hours']}; Summer ({summer}): {row['summer_hours']}"
                out.append(energy(f"{label} Energy", row["price"], f"TOU table, {label}",
                                  tou_period=period, tou_hours=hours))
            return out
        if plan == "ulo":
            periods = (
                ("Ultra-Low Overnight", "ultra-low-overnight"),
                ("Weekend Off-Peak", "off-peak"),
                ("Mid-Peak", "mid-peak"),
                ("On-Peak", "on-peak"),
            )
            return [
                energy(f"{label} Energy", rpp["ulo"][label]["price"], f"ULO table, {label}",
                       tou_period=period, tou_hours=f"All year: {rpp['ulo'][label]['hours']}")
                for label, period in periods
            ]
        t = rpp["thresholds"]
        prefix = "res" if kind == "residential" else "gs"
        audience = "Residential" if kind == "residential" else "Non-residential"
        w, s = t[f"{prefix}_winter"], t[f"{prefix}_summer"]
        if w == s:
            return [
                energy("Tier 1 Energy", rpp["tier1_price"], f"Tiered table, Tier 1 ({audience})",
                       tier_number=1, tier_threshold=w, tier_unit="kWh/month",
                       notes=f"First {w:,.0f} kWh/month, all year"),
                energy("Tier 2 Energy", rpp["tier2_price"], f"Tiered table, Tier 2 ({audience})",
                       tier_number=2, tier_threshold=w, tier_unit="kWh/month",
                       notes=f"Use above {w:,.0f} kWh/month, all year"),
            ]
        out = []
        for season_name, months, threshold in (("winter", winter, w), ("summer", summer, s)):
            title = season_name.capitalize()
            out.append(energy(
                f"Tier 1 Energy ({title})", rpp["tier1_price"], f"Tiered table, Tier 1 ({audience}, {title})",
                tier_number=1, tier_threshold=threshold, tier_unit="kWh/month",
                season=season_name, season_months=months,
                notes=f"First {threshold:,.0f} kWh/month in {season_name}",
            ))
            out.append(energy(
                f"Tier 2 Energy ({title})", rpp["tier2_price"], f"Tiered table, Tier 2 ({audience}, {title})",
                tier_number=2, tier_threshold=threshold, tier_unit="kWh/month",
                season=season_name, season_months=months,
                notes=f"Use above {threshold:,.0f} kWh/month in {season_name}",
            ))
        return out

    def _seed_data(self) -> list[TariffRecord]:
        if not self._ldc_data:
            return []
        confidence = self._ldc_data["confidence"]
        res = self._ldc_data["res"]
        gs_s = self._ldc_data["gs_s"]
        records = []

        # ── Volumetric pass-through for residential and GS < 50 kW ──
        vol_passthrough = [
            RateComponent(
                component_type="transmission",
                component_name="Transmission -- Network",
                charge_value=OEB_TX_NETWORK_VOL,
                charge_unit="$/kWh",
                source_url=OEB_SOURCE_URL,
            ),
            RateComponent(
                component_type="transmission",
                component_name="Transmission -- Connection",
                charge_value=OEB_TX_CONNECTION_VOL,
                charge_unit="$/kWh",
                source_url=OEB_SOURCE_URL,
            ),
            RateComponent(
                component_type="regulatory",
                component_name="Regulatory Charge",
                charge_value=OEB_REGULATORY_CHARGE,
                charge_unit="$/kWh",
                source_url=OEB_SOURCE_URL,
            ),
        ]

        def make_vol_delivery(class_data: dict, conf: str) -> list[RateComponent]:
            """Delivery components for residential / GS < 50 kW (volumetric)."""
            return [
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Service Charge",
                    charge_value=class_data["fixed"],
                    charge_unit="$/month",
                    confidence=conf,
                ),
                RateComponent(
                    component_type="distribution",
                    component_name="Distribution Volumetric Rate",
                    charge_value=class_data["dist_vol"],
                    charge_unit="$/kWh",
                    confidence=conf,
                ),
            ]

        res_delivery = make_vol_delivery(res, confidence)
        gs_s_delivery = make_vol_delivery(gs_s, confidence)

        # ================================================================
        # RESIDENTIAL tariffs (TOU, Tiered, ULO)
        # ================================================================
        records.append(TariffRecord(
            utility_name=self._ldc_name,
            province="ON",
            utility_type="electricity",
            tariff_name="Residential -- Time-of-Use (TOU)",
            tariff_code="TOU-R",
            customer_class="residential",
            rate_structure="tou",
            effective_date=OEB_EFFECTIVE_DATE,
            source_url=OEB_SOURCE_URL,
            confidence=confidence,
            notes=(
                f"OEB-regulated TOU rate. Energy prices are province-wide. "
                f"Delivery charges are specific to {self._ldc_name}."
            ),
            components=[
                RateComponent(
                    component_type="energy", component_name="Off-Peak Energy",
                    charge_value=OEB_TOU["off_peak"], charge_unit="$/kWh",
                    tou_period="off-peak",
                    tou_hours="Weekdays 7pm-7am, all day weekends & holidays",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy", component_name="Mid-Peak Energy",
                    charge_value=OEB_TOU["mid_peak"], charge_unit="$/kWh",
                    tou_period="mid-peak",
                    tou_hours="Weekdays 11am-5pm",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy", component_name="On-Peak Energy",
                    charge_value=OEB_TOU["on_peak"], charge_unit="$/kWh",
                    tou_period="on-peak",
                    tou_hours="Weekdays 7am-11am & 5pm-7pm",
                    source_url=OEB_SOURCE_URL,
                ),
                *res_delivery, *vol_passthrough,
            ],
        ))

        records.append(TariffRecord(
            utility_name=self._ldc_name,
            province="ON",
            utility_type="electricity",
            tariff_name="Residential -- Tiered Pricing",
            tariff_code="TIER-R",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=OEB_EFFECTIVE_DATE,
            source_url=OEB_SOURCE_URL,
            confidence=confidence,
            notes=(
                "OEB-regulated tiered rate. Tier 1 threshold: "
                "1,000 kWh/month winter (Nov-Apr), 600 kWh/month summer (May-Oct)."
            ),
            components=[
                RateComponent(
                    component_type="energy", component_name="Tier 1 Energy",
                    charge_value=OEB_TIERED["tier1_rate"], charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=OEB_TIERED["tier1_threshold_winter"],
                    tier_unit="kWh", season="winter", season_months="Nov-Apr",
                    source_url=OEB_SOURCE_URL,
                    notes="1,000 kWh/month winter; 600 kWh/month summer",
                ),
                RateComponent(
                    component_type="energy", component_name="Tier 2 Energy",
                    charge_value=OEB_TIERED["tier2_rate"], charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=OEB_TIERED["tier1_threshold_winter"],
                    tier_unit="kWh",
                    source_url=OEB_SOURCE_URL,
                ),
                *res_delivery, *vol_passthrough,
            ],
        ))

        records.append(TariffRecord(
            utility_name=self._ldc_name,
            province="ON",
            utility_type="electricity",
            tariff_name="Residential -- Ultra-Low Overnight (ULO)",
            tariff_code="ULO-R",
            customer_class="residential",
            rate_structure="tou",
            effective_date=OEB_EFFECTIVE_DATE,
            source_url=OEB_SOURCE_URL,
            confidence=confidence,
            notes=(
                "OEB-regulated ULO rate -- opt-in for EV owners and "
                "customers who can shift usage overnight."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="Ultra-Low Overnight Energy",
                    charge_value=OEB_ULO["ultra_low_overnight"],
                    charge_unit="$/kWh", tou_period="ultra-low-overnight",
                    tou_hours="Daily 11pm-7am", source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Weekend Off-Peak Energy",
                    charge_value=OEB_ULO["weekend_off_peak"],
                    charge_unit="$/kWh", tou_period="off-peak",
                    tou_hours="Weekends & holidays 7am-11pm",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy", component_name="Mid-Peak Energy",
                    charge_value=OEB_ULO["mid_peak"], charge_unit="$/kWh",
                    tou_period="mid-peak",
                    tou_hours="Weekdays 7am-4pm & 9pm-11pm",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy", component_name="On-Peak Energy",
                    charge_value=OEB_ULO["on_peak"], charge_unit="$/kWh",
                    tou_period="on-peak",
                    tou_hours="Weekdays 4pm-9pm",
                    source_url=OEB_SOURCE_URL,
                ),
                *res_delivery, *vol_passthrough,
            ],
        ))

        # ================================================================
        # GS < 50 kW — TOU, Tiered, and ULO (same energy as residential)
        # ================================================================
        records.append(TariffRecord(
            utility_name=self._ldc_name,
            province="ON",
            utility_type="electricity",
            tariff_name="General Service < 50 kW -- TOU",
            tariff_code="GS-TOU-S",
            customer_class="commercial",
            sub_class="GS < 50 kW",
            rate_structure="tou",
            effective_date=OEB_EFFECTIVE_DATE,
            source_url=OEB_SOURCE_URL,
            confidence=confidence,
            eligibility="Non-residential customers with monthly peak demand under 50 kW",
            demand_max_kw=50,
            notes=(
                "OEB-regulated GS < 50 kW TOU rate. Same energy prices as residential; "
                f"delivery charges are specific to {self._ldc_name}."
            ),
            components=[
                RateComponent(
                    component_type="energy", component_name="Off-Peak Energy",
                    charge_value=OEB_TOU["off_peak"], charge_unit="$/kWh",
                    tou_period="off-peak",
                    tou_hours="Weekdays 7pm-7am, all day weekends & holidays",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy", component_name="Mid-Peak Energy",
                    charge_value=OEB_TOU["mid_peak"], charge_unit="$/kWh",
                    tou_period="mid-peak", tou_hours="Weekdays 11am-5pm",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy", component_name="On-Peak Energy",
                    charge_value=OEB_TOU["on_peak"], charge_unit="$/kWh",
                    tou_period="on-peak",
                    tou_hours="Weekdays 7am-11am & 5pm-7pm",
                    source_url=OEB_SOURCE_URL,
                ),
                *gs_s_delivery, *vol_passthrough,
            ],
        ))

        records.append(TariffRecord(
            utility_name=self._ldc_name,
            province="ON",
            utility_type="electricity",
            tariff_name="General Service < 50 kW -- Tiered",
            tariff_code="GS-TIER-S",
            customer_class="commercial",
            sub_class="GS < 50 kW",
            rate_structure="tiered",
            effective_date=OEB_EFFECTIVE_DATE,
            source_url=OEB_SOURCE_URL,
            confidence=confidence,
            eligibility="Non-residential customers with monthly peak demand under 50 kW",
            demand_max_kw=50,
            notes=(
                "OEB-regulated GS < 50 kW tiered rate. Tier 1 threshold: "
                "750 kWh/month."
            ),
            components=[
                RateComponent(
                    component_type="energy", component_name="Tier 1 Energy",
                    charge_value=OEB_TIERED["tier1_rate"], charge_unit="$/kWh",
                    tier_number=1, tier_threshold=750, tier_unit="kWh",
                    source_url=OEB_SOURCE_URL,
                    notes="GS < 50 kW: 750 kWh/month threshold",
                ),
                RateComponent(
                    component_type="energy", component_name="Tier 2 Energy",
                    charge_value=OEB_TIERED["tier2_rate"], charge_unit="$/kWh",
                    tier_number=2, tier_threshold=750, tier_unit="kWh",
                    source_url=OEB_SOURCE_URL,
                ),
                *gs_s_delivery, *vol_passthrough,
            ],
        ))

        records.append(TariffRecord(
            utility_name=self._ldc_name,
            province="ON",
            utility_type="electricity",
            tariff_name="General Service < 50 kW -- ULO",
            tariff_code="GS-ULO-S",
            customer_class="commercial",
            sub_class="GS < 50 kW",
            rate_structure="tou",
            effective_date=OEB_EFFECTIVE_DATE,
            source_url=OEB_SOURCE_URL,
            confidence=confidence,
            eligibility="Non-residential customers with monthly peak demand under 50 kW",
            demand_max_kw=50,
            notes=(
                "OEB-regulated GS < 50 kW Ultra-Low Overnight rate. "
                "Same energy prices as residential ULO; "
                f"delivery charges are specific to {self._ldc_name}."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="Ultra-Low Overnight Energy",
                    charge_value=OEB_ULO["ultra_low_overnight"],
                    charge_unit="$/kWh", tou_period="ultra-low-overnight",
                    tou_hours="Daily 11pm-7am", source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Weekend Off-Peak Energy",
                    charge_value=OEB_ULO["weekend_off_peak"],
                    charge_unit="$/kWh", tou_period="off-peak",
                    tou_hours="Weekends & holidays 7am-11pm",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy", component_name="Mid-Peak Energy",
                    charge_value=OEB_ULO["mid_peak"], charge_unit="$/kWh",
                    tou_period="mid-peak",
                    tou_hours="Weekdays 7am-4pm & 9pm-11pm",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy", component_name="On-Peak Energy",
                    charge_value=OEB_ULO["on_peak"], charge_unit="$/kWh",
                    tou_period="on-peak",
                    tou_hours="Weekdays 4pm-9pm",
                    source_url=OEB_SOURCE_URL,
                ),
                *gs_s_delivery, *vol_passthrough,
            ],
        ))

        # ================================================================
        # GS >= 50 kW — demand-based pricing (up to 3 tiers)
        #
        # Energy is market-based (IESO Ontario Electricity Market Price + GA;
        # the HOEP was retired April 30, 2025).
        # Transmission is demand-based ($/kW) — NOT volumetric.
        # Each tier has its own fixed, distribution demand, and
        # transmission demand charges from the LDC data dict.
        # ================================================================
        tier_defs = [
            ("gs_d1", "GS-D1", "GS 50-1,499 kW", "commercial"),
            ("gs_d2", "GS-D2", "GS 1,500-4,999 kW", "commercial"),
            ("gs_d3", "GS-D3", "GS 5,000+ kW", "industrial"),
        ]

        for tier_key, tariff_code, sub_class, cust_class in tier_defs:
            tier = self._ldc_data.get(tier_key)
            if tier is None:
                continue

            demand_min = tier["demand_min_kw"]
            demand_max = tier.get("demand_max_kw")
            max_label = f"{demand_max:,} kW" if demand_max else "unlimited"

            records.append(TariffRecord(
                utility_name=self._ldc_name,
                province="ON",
                utility_type="electricity",
                tariff_name=f"General Service — {sub_class} (Demand)",
                tariff_code=tariff_code,
                customer_class=cust_class,
                sub_class=sub_class,
                rate_structure="demand",
                effective_date=OEB_EFFECTIVE_DATE,
                source_url=OEB_SOURCE_URL,
                confidence=confidence,
                eligibility=(
                    f"Non-residential customers with monthly peak demand "
                    f"{demand_min:,} kW to {max_label}"
                ),
                demand_min_kw=float(demand_min),
                demand_max_kw=float(demand_max) if demand_max else None,
                pricing_method="market_based",
                market_reference=oeb_tariff.MARKET_REFERENCE,
                notes=(
                    f"{sub_class} energy cost is market-based: the IESO Ontario Electricity Market Price "
                    "(OEMP), which replaced the Hourly Ontario Energy Price (HOEP, retired April 30, 2025; "
                    f"{oeb_tariff.HOEP_RETIRED_URL}), plus the Global Adjustment. "
                    "Class B pays GA as volumetric per-kWh charge; "
                    "Class A (Industrial Conservation Initiative) pays GA by peak demand factor. "
                    f"Delivery charges are specific to {self._ldc_name}. "
                    "See market_pricing_ontario.json for hourly representative rates."
                ),
                components=[
                    RateComponent(
                        component_type="energy",
                        component_name="Energy (Market-Based)",
                        charge_value=None,
                        charge_unit="$/kWh",
                        market_reference=oeb_tariff.MARKET_REFERENCE,
                        market_source_url=oeb_tariff.MARKET_SOURCE_URL,
                        source_url=oeb_tariff.MARKET_SOURCE_URL,
                        confidence="medium",
                        notes=(
                            "Market-based: Ontario Electricity Market Price + Global Adjustment (the HOEP was "
                            "retired April 30, 2025). Actual cost varies by hour/month. "
                            "See market_pricing_ontario.json for representative rates."
                        ),
                    ),
                    RateComponent(
                        component_type="fixed",
                        component_name="Monthly Service Charge",
                        charge_value=tier["fixed"],
                        charge_unit="$/month",
                        confidence=confidence,
                    ),
                    RateComponent(
                        component_type="demand",
                        component_name="Distribution Demand Charge",
                        charge_value=tier["dist_demand"],
                        charge_unit="$/kW",
                        demand_unit="kW",
                        confidence=confidence,
                    ),
                    RateComponent(
                        component_type="transmission",
                        component_name="Transmission -- Network (Demand)",
                        charge_value=tier["tx_network"],
                        charge_unit="$/kW",
                        demand_unit="kW",
                        source_url=OEB_SOURCE_URL,
                    ),
                    RateComponent(
                        component_type="transmission",
                        component_name="Transmission -- Connection (Demand)",
                        charge_value=tier["tx_connection"],
                        charge_unit="$/kW",
                        demand_unit="kW",
                        source_url=OEB_SOURCE_URL,
                    ),
                    RateComponent(
                        component_type="distribution",
                        component_name="Low Voltage Service Charge",
                        charge_value=tier["low_voltage"],
                        charge_unit="$/kW",
                        demand_unit="kW",
                        confidence=confidence,
                    ),
                    RateComponent(
                        component_type="regulatory",
                        component_name="Regulatory Charge",
                        charge_value=OEB_REGULATORY_CHARGE,
                        charge_unit="$/kWh",
                        source_url=OEB_SOURCE_URL,
                    ),
                ],
            ))

        # ================================================================
        # Street Lighting
        # ================================================================
        records.append(TariffRecord(
            utility_name=self._ldc_name,
            province="ON",
            utility_type="electricity",
            tariff_name="Street Lighting",
            tariff_code="SL",
            customer_class="other",
            sub_class="street lighting",
            rate_structure="flat",
            effective_date=OEB_EFFECTIVE_DATE,
            source_url=OEB_SOURCE_URL,
            confidence=confidence,
            eligibility="Municipal and roadway lighting connections",
            notes="OEB-regulated street lighting rate.",
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=OEB_STREET_LIGHTING_ENERGY,
                    charge_unit="$/kWh",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Service Charge (per connection)",
                    charge_value=3.50,
                    charge_unit="$/month",
                    confidence=confidence,
                    notes="Per-connection monthly charge; varies by LDC",
                ),
                *vol_passthrough,
            ],
        ))

        return records
