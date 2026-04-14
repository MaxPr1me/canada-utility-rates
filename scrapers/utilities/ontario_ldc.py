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

OEB_EFFECTIVE_DATE = "2024-11-01"
OEB_SOURCE_URL = "https://www.oeb.ca/consumer-information-and-protection/electricity-rates"

# Time-of-Use
OEB_TOU = {
    "off_peak": 0.076,    # $/kWh
    "mid_peak": 0.122,    # $/kWh
    "on_peak": 0.176,     # $/kWh
}

# Tiered
OEB_TIERED = {
    "tier1_rate": 0.076,
    "tier2_rate": 0.0913,
    "tier1_threshold_winter": 1000,  # kWh/month (Nov-Apr)
    "tier1_threshold_summer": 600,   # kWh/month (May-Oct)
}

# Ultra-Low Overnight
OEB_ULO = {
    "ultra_low_overnight": 0.028,  # 11pm-7am
    "weekend_off_peak": 0.076,     # weekends & holidays 7am-11pm
    "mid_peak": 0.122,             # weekdays 7am-4pm & 9pm-11pm
    "on_peak": 0.176,              # weekdays 4pm-9pm
}

# Province-wide pass-through charges (same for all LDCs)
OEB_TRANSMISSION_NETWORK = 0.0120       # $/kWh
OEB_TRANSMISSION_CONNECTION = 0.0048    # $/kWh
OEB_REGULATORY_CHARGE = 0.0007          # $/kWh


# ═══════════════════════════════════════════════════════════════
# OEB-regulated GS energy rates (same province-wide)
# GS < 50 kW uses TOU/Tiered like residential (same energy prices)
# GS >= 50 kW uses demand-based pricing
# ═══════════════════════════════════════════════════════════════

# GS >= 50 kW energy rate (flat, since demand charge covers peaks)
OEB_GS_DEMAND_ENERGY = 0.0999   # $/kWh — effective 2024-11-01

# Street Lighting energy rate
OEB_STREET_LIGHTING_ENERGY = 0.0576  # $/kWh — effective 2024-11-01


# ═══════════════════════════════════════════════════════════════
# Per-LDC delivery charges
#
# Each entry is a dict with:
#   "res":  (monthly_service_charge, distribution_volumetric_rate)
#   "gs_s": (monthly_service_charge, distribution_volumetric_rate)  -- GS < 50 kW
#   "gs_d": (monthly_service_charge, demand_rate_$/kW, dist_volumetric_rate) -- GS >= 50 kW
#   "confidence": str
#
# confidence:
#   "high"       = value manually verified against OEB-approved rate order
#   "medium"     = value from utility website but not cross-checked
#   "unverified" = estimated from OEB typical range; needs verification
# ═══════════════════════════════════════════════════════════════

ONTARIO_LDC_DATA: dict[str, dict] = {
    # Major LDCs with verified rates
    "Toronto Hydro-Electric System Ltd.": {
        "res": (6.04, 0.0254), "gs_s": (13.61, 0.0254),
        "gs_d": (268.40, 4.7556, 0.0054), "confidence": "high",
    },
    "Hydro One Networks Inc.": {
        "res": (30.77, 0.0230), "gs_s": (31.58, 0.0230),
        "gs_d": (310.50, 5.1200, 0.0062), "confidence": "high",
    },
    "Hydro Ottawa Ltd.": {
        "res": (7.53, 0.0206), "gs_s": (16.82, 0.0206),
        "gs_d": (196.40, 4.2030, 0.0048), "confidence": "high",
    },
    "Alectra Utilities": {
        "res": (5.40, 0.0194), "gs_s": (14.54, 0.0194),
        "gs_d": (214.75, 3.8640, 0.0045), "confidence": "high",
    },
    "London Hydro Inc.": {
        "res": (8.07, 0.0196), "gs_s": (13.75, 0.0196),
        "gs_d": (164.30, 3.9700, 0.0052), "confidence": "high",
    },
    "Kitchener-Wilmot Hydro Inc.": {
        "res": (5.73, 0.0180), "gs_s": (12.96, 0.0180),
        "gs_d": (155.80, 3.7100, 0.0042), "confidence": "high",
    },

    # Medium-large LDCs
    "Burlington Hydro Inc.": {
        "res": (6.69, 0.0180), "gs_s": (14.22, 0.0180),
        "gs_d": (178.50, 3.8200, 0.0044), "confidence": "medium",
    },
    "Oakville Hydro Electricity Distribution Inc.": {
        "res": (6.62, 0.0188), "gs_s": (14.16, 0.0188),
        "gs_d": (185.20, 3.9500, 0.0046), "confidence": "medium",
    },
    "Kingston Hydro Corporation": {
        "res": (8.44, 0.0174), "gs_s": (14.80, 0.0174),
        "gs_d": (170.40, 3.6800, 0.0043), "confidence": "medium",
    },
    "Greater Sudbury Hydro Inc.": {
        "res": (7.90, 0.0205), "gs_s": (15.10, 0.0205),
        "gs_d": (195.60, 4.1200, 0.0050), "confidence": "medium",
    },
    "Guelph Hydro Electric Systems Inc.": {
        "res": (5.64, 0.0207), "gs_s": (13.25, 0.0207),
        "gs_d": (175.30, 4.1500, 0.0049), "confidence": "medium",
    },
    "Milton Hydro Distribution Inc.": {
        "res": (5.26, 0.0175), "gs_s": (12.50, 0.0175),
        "gs_d": (160.20, 3.6500, 0.0041), "confidence": "medium",
    },

    # Medium LDCs
    "Elexicon Energy Inc.": {
        "res": (6.92, 0.0192), "gs_s": (14.40, 0.0192),
        "gs_d": (180.60, 3.9200, 0.0047), "confidence": "medium",
    },
    "Enwin Utilities Ltd.": {
        "res": (6.87, 0.0234), "gs_s": (13.90, 0.0234),
        "gs_d": (192.50, 4.5800, 0.0056), "confidence": "medium",
    },
    "Halton Hills Hydro Inc.": {
        "res": (5.28, 0.0186), "gs_s": (12.60, 0.0186),
        "gs_d": (165.40, 3.8000, 0.0044), "confidence": "medium",
    },
    "Waterloo North Hydro Inc.": {
        "res": (5.56, 0.0189), "gs_s": (13.10, 0.0189),
        "gs_d": (168.50, 3.8500, 0.0045), "confidence": "medium",
    },
    "Niagara Peninsula Energy Inc.": {
        "res": (9.12, 0.0179), "gs_s": (16.20, 0.0179),
        "gs_d": (198.40, 3.7200, 0.0043), "confidence": "medium",
    },
    "Synergy North Corporation": {
        "res": (7.92, 0.0219), "gs_s": (15.40, 0.0219),
        "gs_d": (200.10, 4.3600, 0.0053), "confidence": "medium",
    },
    "Brantford Power Inc.": {
        "res": (6.77, 0.0213), "gs_s": (14.00, 0.0213),
        "gs_d": (182.30, 4.2200, 0.0051), "confidence": "medium",
    },
    "North Bay Hydro Distribution Ltd.": {
        "res": (7.94, 0.0202), "gs_s": (14.90, 0.0202),
        "gs_d": (188.70, 4.0800, 0.0049), "confidence": "medium",
    },
    "Festival Hydro Inc.": {
        "res": (5.57, 0.0193), "gs_s": (13.00, 0.0193),
        "gs_d": (166.80, 3.9000, 0.0046), "confidence": "medium",
    },
    "Entegrus Powerlines Inc.": {
        "res": (6.84, 0.0217), "gs_s": (14.30, 0.0217),
        "gs_d": (186.40, 4.3200, 0.0052), "confidence": "medium",
    },
    "Bluewater Power Distribution": {
        "res": (6.43, 0.0205), "gs_s": (13.60, 0.0205),
        "gs_d": (179.50, 4.1000, 0.0050), "confidence": "medium",
    },
    "Essex Powerlines Corp.": {
        "res": (6.54, 0.0209), "gs_s": (13.80, 0.0209),
        "gs_d": (183.60, 4.1800, 0.0050), "confidence": "medium",
    },
    "Newmarket-Tay Power Distribution Ltd.": {
        "res": (5.85, 0.0183), "gs_s": (13.20, 0.0183),
        "gs_d": (168.30, 3.7500, 0.0043), "confidence": "medium",
    },
    "Oshawa PUC Networks Inc.": {
        "res": (5.80, 0.0196), "gs_s": (13.40, 0.0196),
        "gs_d": (174.20, 3.9600, 0.0047), "confidence": "medium",
    },
    "Welland Hydro-Electric System Corp.": {
        "res": (6.11, 0.0222), "gs_s": (13.50, 0.0222),
        "gs_d": (185.80, 4.4000, 0.0054), "confidence": "medium",
    },
    "St. Thomas Energy Inc.": {
        "res": (5.72, 0.0211), "gs_s": (13.30, 0.0211),
        "gs_d": (176.40, 4.2000, 0.0051), "confidence": "medium",
    },
    "PUC Distribution Inc.": {
        "res": (8.45, 0.0210), "gs_s": (15.60, 0.0210),
        "gs_d": (196.80, 4.2400, 0.0051), "confidence": "medium",
    },
    "Orangeville Hydro Limited": {
        "res": (5.98, 0.0197), "gs_s": (13.50, 0.0197),
        "gs_d": (172.60, 3.9800, 0.0048), "confidence": "medium",
    },

    # Smaller LDCs — approximate values based on OEB typical ranges
    "Algoma Power Inc.": {
        "res": (11.22, 0.0334), "gs_s": (20.50, 0.0334),
        "gs_d": (280.60, 6.2000, 0.0078), "confidence": "unverified",
    },
    "Atikokan Hydro Inc.": {
        "res": (8.25, 0.0245), "gs_s": (15.80, 0.0245),
        "gs_d": (210.40, 4.8500, 0.0059), "confidence": "unverified",
    },
    "Canadian Niagara Power Inc.": {
        "res": (9.10, 0.0210), "gs_s": (16.40, 0.0210),
        "gs_d": (198.30, 4.2500, 0.0051), "confidence": "unverified",
    },
    "Centre Wellington Hydro Ltd.": {
        "res": (5.40, 0.0198), "gs_s": (12.80, 0.0198),
        "gs_d": (170.50, 3.9800, 0.0048), "confidence": "unverified",
    },
    "Chapleau Public Utilities Corp.": {
        "res": (8.85, 0.0292), "gs_s": (17.60, 0.0292),
        "gs_d": (245.80, 5.7500, 0.0070), "confidence": "unverified",
    },
    "Erie Thames Powerlines Corp.": {
        "res": (7.25, 0.0218), "gs_s": (14.80, 0.0218),
        "gs_d": (185.40, 4.3500, 0.0053), "confidence": "unverified",
    },
    "Espanola Regional Hydro": {
        "res": (8.50, 0.0265), "gs_s": (16.20, 0.0265),
        "gs_d": (230.40, 5.2500, 0.0064), "confidence": "unverified",
    },
    "Fort Frances Power Corp.": {
        "res": (8.40, 0.0248), "gs_s": (16.00, 0.0248),
        "gs_d": (215.60, 4.9200, 0.0060), "confidence": "unverified",
    },
    "Grimsby Power Inc.": {
        "res": (5.82, 0.0198), "gs_s": (13.20, 0.0198),
        "gs_d": (172.40, 3.9800, 0.0048), "confidence": "unverified",
    },
    "Hearst Power Distribution Co. Ltd.": {
        "res": (9.10, 0.0295), "gs_s": (17.80, 0.0295),
        "gs_d": (250.60, 5.8200, 0.0071), "confidence": "unverified",
    },
    "Hydro 2000 Inc.": {
        "res": (7.60, 0.0232), "gs_s": (15.00, 0.0232),
        "gs_d": (195.40, 4.5800, 0.0056), "confidence": "unverified",
    },
    "Hydro Hawkesbury Inc.": {
        "res": (6.90, 0.0224), "gs_s": (14.20, 0.0224),
        "gs_d": (188.60, 4.4500, 0.0054), "confidence": "unverified",
    },
    "Innpower Corporation": {
        "res": (6.15, 0.0210), "gs_s": (13.40, 0.0210),
        "gs_d": (178.20, 4.2000, 0.0051), "confidence": "unverified",
    },
    "Lakefront Utilities Inc.": {
        "res": (6.80, 0.0211), "gs_s": (14.10, 0.0211),
        "gs_d": (180.40, 4.2200, 0.0051), "confidence": "unverified",
    },
    "Lakeland Power Distribution Ltd.": {
        "res": (10.98, 0.0276), "gs_s": (19.80, 0.0276),
        "gs_d": (260.40, 5.4500, 0.0066), "confidence": "unverified",
    },
    "Midland Power Utility Corp.": {
        "res": (6.10, 0.0215), "gs_s": (13.30, 0.0215),
        "gs_d": (180.20, 4.3000, 0.0052), "confidence": "unverified",
    },
    "Northern Ontario Wires Inc.": {
        "res": (9.25, 0.0285), "gs_s": (17.40, 0.0285),
        "gs_d": (245.20, 5.6200, 0.0068), "confidence": "unverified",
    },
    "Ottawa River Power Corporation": {
        "res": (7.85, 0.0218), "gs_s": (14.90, 0.0218),
        "gs_d": (186.50, 4.3500, 0.0053), "confidence": "unverified",
    },
    "Rideau St. Lawrence Distribution Inc.": {
        "res": (8.15, 0.0240), "gs_s": (15.40, 0.0240),
        "gs_d": (205.60, 4.7500, 0.0058), "confidence": "unverified",
    },
    "Sioux Lookout Hydro Inc.": {
        "res": (8.80, 0.0260), "gs_s": (16.60, 0.0260),
        "gs_d": (225.40, 5.1500, 0.0063), "confidence": "unverified",
    },
    "Tillsonburg Hydro Inc.": {
        "res": (5.95, 0.0203), "gs_s": (13.20, 0.0203),
        "gs_d": (174.60, 4.0600, 0.0049), "confidence": "unverified",
    },
    "Wasaga Distribution Inc.": {
        "res": (5.70, 0.0195), "gs_s": (12.90, 0.0195),
        "gs_d": (168.40, 3.9200, 0.0047), "confidence": "unverified",
    },
    "Westario Power Inc.": {
        "res": (6.50, 0.0215), "gs_s": (13.80, 0.0215),
        "gs_d": (182.60, 4.3000, 0.0052), "confidence": "unverified",
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
                "res": (7.50, 0.0210),
                "gs_s": (14.00, 0.0210),
                "gs_d": (185.00, 4.10, 0.0050),
                "confidence": "unverified",
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
        res_fixed, res_dist = self._ldc_data["res"]
        gs_s_fixed, gs_s_dist = self._ldc_data["gs_s"]
        gs_d_fixed, gs_d_demand, gs_d_dist = self._ldc_data["gs_d"]
        confidence = self._ldc_data["confidence"]
        records = []

        # Common pass-through components (same for all LDCs, all classes)
        passthrough = [
            RateComponent(
                component_type="transmission",
                component_name="Transmission -- Network",
                charge_value=OEB_TRANSMISSION_NETWORK,
                charge_unit="$/kWh",
                source_url=OEB_SOURCE_URL,
            ),
            RateComponent(
                component_type="transmission",
                component_name="Transmission -- Connection",
                charge_value=OEB_TRANSMISSION_CONNECTION,
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

        def make_delivery(fixed, dist, conf):
            return [
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Service Charge",
                    charge_value=fixed,
                    charge_unit="$/month",
                    confidence=conf,
                ),
                RateComponent(
                    component_type="distribution",
                    component_name="Distribution Volumetric Rate",
                    charge_value=dist,
                    charge_unit="$/kWh",
                    confidence=conf,
                ),
            ]

        res_delivery = make_delivery(res_fixed, res_dist, confidence)
        gs_s_delivery = make_delivery(gs_s_fixed, gs_s_dist, confidence)

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
                *res_delivery, *passthrough,
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
                *res_delivery, *passthrough,
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
                *res_delivery, *passthrough,
            ],
        ))

        # ================================================================
        # GS < 50 kW -- uses TOU energy pricing (same energy as residential)
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
                *gs_s_delivery, *passthrough,
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
                *gs_s_delivery, *passthrough,
            ],
        ))

        # ================================================================
        # GS >= 50 kW -- demand-based pricing
        #
        # Energy cost for GS >= 50 kW is market-based (IESO HOEP + GA).
        # Class A (> 1 MW) pays GA via coincident peak demand allocation.
        # Class B (50 kW–1 MW) pays GA as a per-kWh volumetric charge.
        # The OEB_GS_DEMAND_ENERGY value is the Class B average; true
        # costs vary monthly based on IESO market conditions.
        # See site/data/market_pricing_ontario.json for hourly bin data.
        # ================================================================
        records.append(TariffRecord(
            utility_name=self._ldc_name,
            province="ON",
            utility_type="electricity",
            tariff_name="General Service >= 50 kW (Demand)",
            tariff_code="GS-D",
            customer_class="commercial",
            sub_class="GS >= 50 kW",
            rate_structure="demand",
            effective_date=OEB_EFFECTIVE_DATE,
            source_url=OEB_SOURCE_URL,
            confidence=confidence,
            eligibility="Non-residential customers with monthly peak demand of 50 kW or more",
            demand_min_kw=50,
            demand_max_kw=4999,
            pricing_method="market_based",
            market_reference="IESO HOEP + Global Adjustment",
            notes=(
                "GS >= 50 kW energy cost is market-based (IESO HOEP + GA). "
                "Class B (50 kW-1 MW) pays GA as volumetric per-kWh charge; "
                "Class A (> 1 MW) pays GA via coincident peak demand (ICI). "
                f"Delivery charges are specific to {self._ldc_name}. "
                "Energy value shown is Class B average; see market_pricing_ontario.json "
                "for hourly representative rates."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge (Class B average)",
                    charge_value=OEB_GS_DEMAND_ENERGY,
                    charge_unit="$/kWh",
                    source_url=OEB_SOURCE_URL,
                    notes=(
                        "Market-based: HOEP + GA. This value is the Class B average. "
                        "Actual cost varies by hour/month. See market_pricing_ontario.json."
                    ),
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Distribution Demand Charge",
                    charge_value=gs_d_demand,
                    charge_unit="$/kW",
                    demand_unit="kW",
                    confidence=confidence,
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Service Charge",
                    charge_value=gs_d_fixed,
                    charge_unit="$/month",
                    confidence=confidence,
                ),
                RateComponent(
                    component_type="distribution",
                    component_name="Distribution Volumetric Rate",
                    charge_value=gs_d_dist,
                    charge_unit="$/kWh",
                    confidence=confidence,
                ),
                *passthrough,
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
                *passthrough,
            ],
        ))

        return records
