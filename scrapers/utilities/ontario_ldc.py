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
  OEB rate schedules: https://www.oeb.ca/consumer-information-and-protection/electricity-rates
  OEB rate comparison tool: https://www.oeb.ca/consumer-information-and-protection/bill-calculator
  Individual LDC tariffs: each LDC's website (linked in registry.json)
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

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
# GS >= 50 kW pays market-based energy (IESO HOEP + GA)
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
# Ontario LDC Scraper class
# ═══════════════════════════════════════════════════════════════

class OntarioLDCScraper(BaseScraper):
    """
    Data-driven scraper for any Ontario electricity LDC.

    All Ontario LDCs share the same OEB-regulated energy prices;
    only delivery charges differ.  This class reads the utility
    name from the registry_entry and looks up delivery charges
    from ONTARIO_LDC_DATA.

    Produces tariffs for:
      - Residential: TOU, Tiered, ULO
      - GS < 50 kW: TOU, Tiered (energy-based, like residential)
      - GS >= 50 kW: Demand-based
      - Street Lighting
    """

    def __init__(self, registry_entry: dict | None = None):
        # Read utility name from registry entry
        if registry_entry:
            self._ldc_name = registry_entry["name"]
        else:
            self._ldc_name = "Unknown Ontario LDC"

        super().__init__(utility_name=self._ldc_name, province="ON")

        # Look up delivery charges
        self._ldc_data = ONTARIO_LDC_DATA.get(self._ldc_name)
        if not self._ldc_data:
            self.logger.warning(
                "No delivery charge data for %s -- will use Ontario median values",
                self._ldc_name,
            )
            # Ontario median fallback
            self._ldc_data = {
                "confidence": "unverified",
                "res": {"fixed": 7.50, "dist_vol": 0.0210},
                "gs_s": {"fixed": 14.00, "dist_vol": 0.0210},
                "gs_d1": {
                    "fixed": 185.00, "dist_demand": 4.10,
                    "tx_network": 4.65, "tx_connection": 2.70,
                    "low_voltage": 0.01950,
                    "demand_min_kw": 50, "demand_max_kw": 1499,
                },
            }

    def scrape(self) -> list[TariffRecord]:
        records = []
        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.info("Using seed data for %s", self._ldc_name)
            records.extend(self._seed_data())
        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        # Placeholder -- each LDC's website has different HTML.
        return None

    def _seed_data(self) -> list[TariffRecord]:
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
        # Energy is market-based (IESO HOEP + GA).
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
                market_reference="IESO HOEP + Global Adjustment",
                notes=(
                    f"{sub_class} energy cost is market-based (IESO HOEP + GA). "
                    "Class B pays GA as volumetric per-kWh charge; "
                    "Class A (> 1 MW) pays GA via coincident peak demand (ICI). "
                    f"Delivery charges are specific to {self._ldc_name}. "
                    "See market_pricing_ontario.json for hourly representative rates."
                ),
                components=[
                    RateComponent(
                        component_type="energy",
                        component_name="Energy (Market-Based)",
                        charge_value=None,
                        charge_unit="$/kWh",
                        market_reference="IESO HOEP + Global Adjustment",
                        source_url=OEB_SOURCE_URL,
                        confidence="medium",
                        notes=(
                            "Market-based: HOEP + GA. Actual cost varies by hour/month. "
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
