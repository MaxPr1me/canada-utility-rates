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
# Per-LDC delivery charges
#
# Each entry:  (monthly_service_charge, distribution_volumetric_rate, confidence)
#
# confidence:
#   "high"       = value manually verified against OEB-approved rate order
#   "medium"     = value from utility website but not cross-checked
#   "unverified" = estimated from OEB typical range; needs verification
# ═══════════════════════════════════════════════════════════════

ONTARIO_LDC_DATA: dict[str, tuple[float, float, str]] = {
    # (monthly_fixed_$, distribution_$/kWh, confidence)

    # Major LDCs with verified rates
    "Toronto Hydro-Electric System Ltd.":       (6.04,  0.0254, "high"),
    "Hydro One Networks Inc.":                  (30.77, 0.0230, "high"),
    "Hydro Ottawa Ltd.":                        (7.53,  0.0206, "high"),
    "Alectra Utilities":                        (5.40,  0.0194, "high"),
    "London Hydro Inc.":                        (8.07,  0.0196, "high"),
    "Kitchener-Wilmot Hydro Inc.":              (5.73,  0.0180, "high"),
    "Burlington Hydro Inc.":                    (6.69,  0.0180, "medium"),
    "Oakville Hydro Electricity Distribution Inc.": (6.62, 0.0188, "medium"),
    "Kingston Hydro Corporation":               (8.44,  0.0174, "medium"),
    "Greater Sudbury Hydro Inc.":               (7.90,  0.0205, "medium"),
    "Guelph Hydro Electric Systems Inc.":       (5.64,  0.0207, "medium"),
    "Milton Hydro Distribution Inc.":           (5.26,  0.0175, "medium"),

    # Medium LDCs — rates from utility websites / OEB schedules
    "Elexicon Energy Inc.":                     (6.92,  0.0192, "medium"),
    "Enwin Utilities Ltd.":                     (6.87,  0.0234, "medium"),
    "Halton Hills Hydro Inc.":                  (5.28,  0.0186, "medium"),
    "Waterloo North Hydro Inc.":                (5.56,  0.0189, "medium"),
    "Niagara Peninsula Energy Inc.":            (9.12,  0.0179, "medium"),
    "Synergy North Corporation":                (7.92,  0.0219, "medium"),
    "Brantford Power Inc.":                     (6.77,  0.0213, "medium"),
    "North Bay Hydro Distribution Ltd.":        (7.94,  0.0202, "medium"),
    "Festival Hydro Inc.":                      (5.57,  0.0193, "medium"),
    "Entegrus Powerlines Inc.":                 (6.84,  0.0217, "medium"),
    "Bluewater Power Distribution":             (6.43,  0.0205, "medium"),
    "Essex Powerlines Corp.":                   (6.54,  0.0209, "medium"),
    "Newmarket-Tay Power Distribution Ltd.":    (5.85,  0.0183, "medium"),
    "Oshawa PUC Networks Inc.":                 (5.80,  0.0196, "medium"),
    "Welland Hydro-Electric System Corp.":      (6.11,  0.0222, "medium"),
    "St. Thomas Energy Inc.":                   (5.72,  0.0211, "medium"),
    "PUC Distribution Inc.":                    (8.45,  0.0210, "medium"),
    "Orangeville Hydro Limited":                (5.98,  0.0197, "medium"),

    # Smaller LDCs — approximate values based on OEB typical ranges
    "Algoma Power Inc.":                        (11.22, 0.0334, "unverified"),
    "Atikokan Hydro Inc.":                      (8.25,  0.0245, "unverified"),
    "Canadian Niagara Power Inc.":              (9.10,  0.0210, "unverified"),
    "Centre Wellington Hydro Ltd.":             (5.40,  0.0198, "unverified"),
    "Chapleau Public Utilities Corp.":          (8.85,  0.0292, "unverified"),
    "Erie Thames Powerlines Corp.":             (7.25,  0.0218, "unverified"),
    "Espanola Regional Hydro":                  (8.50,  0.0265, "unverified"),
    "Fort Frances Power Corp.":                 (8.40,  0.0248, "unverified"),
    "Grimsby Power Inc.":                       (5.82,  0.0198, "unverified"),
    "Hearst Power Distribution Co. Ltd.":       (9.10,  0.0295, "unverified"),
    "Hydro 2000 Inc.":                          (7.60,  0.0232, "unverified"),
    "Hydro Hawkesbury Inc.":                    (6.90,  0.0224, "unverified"),
    "Innpower Corporation":                     (6.15,  0.0210, "unverified"),
    "Lakefront Utilities Inc.":                 (6.80,  0.0211, "unverified"),
    "Lakeland Power Distribution Ltd.":         (10.98, 0.0276, "unverified"),
    "Midland Power Utility Corp.":              (6.10,  0.0215, "unverified"),
    "Northern Ontario Wires Inc.":              (9.25,  0.0285, "unverified"),
    "Ottawa River Power Corporation":           (7.85,  0.0218, "unverified"),
    "Rideau St. Lawrence Distribution Inc.":    (8.15,  0.0240, "unverified"),
    "Sioux Lookout Hydro Inc.":                 (8.80,  0.0260, "unverified"),
    "Tillsonburg Hydro Inc.":                   (5.95,  0.0203, "unverified"),
    "Wasaga Distribution Inc.":                 (5.70,  0.0195, "unverified"),
    "Westario Power Inc.":                      (6.50,  0.0215, "unverified"),
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
                "No delivery charge data for %s — will use Ontario median values",
                self._ldc_name,
            )
            # Ontario median: ~$7.50/month, ~$0.021/kWh
            self._ldc_data = (7.50, 0.0210, "unverified")

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
        # Placeholder — each LDC's website has different HTML.
        # Live parsing can be added per-LDC as needed.
        return None

    def _seed_data(self) -> list[TariffRecord]:
        monthly_fixed, dist_rate, confidence = self._ldc_data
        records = []

        # Common delivery components shared by all 3 rate plans
        delivery_components = [
            RateComponent(
                component_type="fixed",
                component_name="Monthly Service Charge",
                charge_value=monthly_fixed,
                charge_unit="$/month",
                confidence=confidence,
            ),
            RateComponent(
                component_type="distribution",
                component_name="Distribution Volumetric Rate",
                charge_value=dist_rate,
                charge_unit="$/kWh",
                confidence=confidence,
            ),
            RateComponent(
                component_type="transmission",
                component_name="Transmission — Network",
                charge_value=OEB_TRANSMISSION_NETWORK,
                charge_unit="$/kWh",
                source_url=OEB_SOURCE_URL,
            ),
            RateComponent(
                component_type="transmission",
                component_name="Transmission — Connection",
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

        # ── TOU ───────────────────────────────────────────────
        records.append(TariffRecord(
            utility_name=self._ldc_name,
            province="ON",
            utility_type="electricity",
            tariff_name="Residential — Time-of-Use (TOU)",
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
                    component_type="energy",
                    component_name="Off-Peak Energy",
                    charge_value=OEB_TOU["off_peak"],
                    charge_unit="$/kWh",
                    tou_period="off-peak",
                    tou_hours="Weekdays 7pm-7am, all day weekends & holidays",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Mid-Peak Energy",
                    charge_value=OEB_TOU["mid_peak"],
                    charge_unit="$/kWh",
                    tou_period="mid-peak",
                    tou_hours="Weekdays 11am-5pm",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy",
                    component_name="On-Peak Energy",
                    charge_value=OEB_TOU["on_peak"],
                    charge_unit="$/kWh",
                    tou_period="on-peak",
                    tou_hours="Weekdays 7am-11am & 5pm-7pm",
                    source_url=OEB_SOURCE_URL,
                ),
                *delivery_components,
            ],
        ))

        # ── Tiered ────────────────────────────────────────────
        records.append(TariffRecord(
            utility_name=self._ldc_name,
            province="ON",
            utility_type="electricity",
            tariff_name="Residential — Tiered Pricing",
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
                    component_type="energy",
                    component_name="Tier 1 Energy",
                    charge_value=OEB_TIERED["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=OEB_TIERED["tier1_threshold_winter"],
                    tier_unit="kWh",
                    season="winter",
                    season_months="Nov-Apr",
                    source_url=OEB_SOURCE_URL,
                    notes="1,000 kWh/month winter; 600 kWh/month summer",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy",
                    charge_value=OEB_TIERED["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=OEB_TIERED["tier1_threshold_winter"],
                    tier_unit="kWh",
                    source_url=OEB_SOURCE_URL,
                ),
                *delivery_components,
            ],
        ))

        # ── ULO ───────────────────────────────────────────────
        records.append(TariffRecord(
            utility_name=self._ldc_name,
            province="ON",
            utility_type="electricity",
            tariff_name="Residential — Ultra-Low Overnight (ULO)",
            tariff_code="ULO-R",
            customer_class="residential",
            rate_structure="tou",
            effective_date=OEB_EFFECTIVE_DATE,
            source_url=OEB_SOURCE_URL,
            confidence=confidence,
            notes=(
                "OEB-regulated ULO rate — opt-in for EV owners and "
                "customers who can shift usage overnight."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="Ultra-Low Overnight Energy",
                    charge_value=OEB_ULO["ultra_low_overnight"],
                    charge_unit="$/kWh",
                    tou_period="ultra-low-overnight",
                    tou_hours="Daily 11pm-7am",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Weekend Off-Peak Energy",
                    charge_value=OEB_ULO["weekend_off_peak"],
                    charge_unit="$/kWh",
                    tou_period="off-peak",
                    tou_hours="Weekends & holidays 7am-11pm",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Mid-Peak Energy",
                    charge_value=OEB_ULO["mid_peak"],
                    charge_unit="$/kWh",
                    tou_period="mid-peak",
                    tou_hours="Weekdays 7am-4pm & 9pm-11pm",
                    source_url=OEB_SOURCE_URL,
                ),
                RateComponent(
                    component_type="energy",
                    component_name="On-Peak Energy",
                    charge_value=OEB_ULO["on_peak"],
                    charge_unit="$/kWh",
                    tou_period="on-peak",
                    tou_hours="Weekdays 4pm-9pm",
                    source_url=OEB_SOURCE_URL,
                ),
                *delivery_components,
            ],
        ))

        return records
