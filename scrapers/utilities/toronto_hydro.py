"""
toronto_hydro.py — Scraper for Toronto Hydro electricity rates (Ontario).

Toronto Hydro is the local distribution company (LDC) for the City of Toronto.
Unlike BC Hydro and Hydro-Québec, Ontario LDCs don't set energy prices —
the Ontario Energy Board (OEB) sets province-wide rates.

Ontario electricity bills have many components from multiple sources:
  - Electricity charges (OEB-regulated)
  - Delivery charges (utility-specific)
  - Regulatory charges (OEB)
  - Debt retirement charge (provincial, now ended for most)
  - HST

This scraper demonstrates combining multiple official sources.

Official sources:
  Toronto Hydro delivery charges:
    https://www.torontohydro.com/rates-billing
  OEB-regulated prices:
    https://www.oeb.ca/consumer-information-and-protection/electricity-rates

Rate structures available in Ontario:
  - Time-of-Use (TOU) — most residential
  - Tiered — opt-in alternative to TOU
  - Ultra-Low Overnight (ULO) — opt-in since 2023
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utilities.ontario_ldc import (
    OEB_EFFECTIVE_DATE,
    OEB_SOURCE_URL,
    OEB_TOU,
    OEB_TIERED,
    OEB_ULO,
    OEB_TX_NETWORK_VOL,
    OEB_TX_CONNECTION_VOL,
    OEB_REGULATORY_CHARGE,
)

logger = logging.getLogger(__name__)

# Re-export OEB constants in the format toronto_hydro _seed_data expects.
# These are now single-source-of-truth imports from ontario_ldc.py.
OEB_TOU_RATES = {
    "effective_date": OEB_EFFECTIVE_DATE,
    "source_url": OEB_SOURCE_URL,
    "off_peak": OEB_TOU["off_peak"],
    "mid_peak": OEB_TOU["mid_peak"],
    "on_peak": OEB_TOU["on_peak"],
}

OEB_TIERED_RATES = {
    "effective_date": OEB_EFFECTIVE_DATE,
    "source_url": OEB_SOURCE_URL,
    "tier1_threshold_kwh": OEB_TIERED["tier1_threshold_winter"],
    "tier1_rate": OEB_TIERED["tier1_rate"],
    "tier2_rate": OEB_TIERED["tier2_rate"],
}

OEB_ULO_RATES = {
    "effective_date": OEB_EFFECTIVE_DATE,
    "source_url": OEB_SOURCE_URL,
    "ultra_low_overnight": OEB_ULO["ultra_low_overnight"],
    "weekend_off_peak": OEB_ULO["weekend_off_peak"],
    "mid_peak": OEB_ULO["mid_peak"],
    "on_peak": OEB_ULO["on_peak"],
}

# Toronto Hydro delivery charges (utility-specific).
TORONTO_HYDRO_DELIVERY = {
    "effective_date": OEB_EFFECTIVE_DATE,
    "source_url": "https://www.torontohydro.com/rates-billing",
    "residential_fixed_monthly": 6.04,         # $/month
    "residential_distribution_volumetric": 0.0254,  # $/kWh
    "residential_transmission_network": OEB_TX_NETWORK_VOL,   # $/kWh
    "residential_transmission_connection": OEB_TX_CONNECTION_VOL,  # $/kWh
    "regulatory_charge": OEB_REGULATORY_CHARGE,               # $/kWh
}


class TorontoHydroScraper(BaseScraper):
    """Scrape Toronto Hydro electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Toronto Hydro", province="ON")

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for Toronto Hydro")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        try:
            html = self.fetch_page(TORONTO_HYDRO_DELIVERY["source_url"])
            # Toronto Hydro site structure parsing would go here
            return None
        except Exception as e:
            self.logger.warning("Could not fetch Toronto Hydro page: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential TOU ───────────────────────────────────
        records.append(TariffRecord(
            utility_name="Toronto Hydro",
            province="ON",
            utility_type="electricity",
            tariff_name="Residential — Time-of-Use (TOU)",
            tariff_code="TOU-R",
            customer_class="residential",
            rate_structure="tou",
            effective_date=OEB_TOU_RATES["effective_date"],
            source_url=TORONTO_HYDRO_DELIVERY["source_url"],
            confidence="high",
            notes=(
                "Ontario residential TOU rate. Energy prices set by OEB province-wide. "
                "Delivery charges are Toronto Hydro-specific. "
                "TOU periods: On-Peak 7am-11am & 5pm-7pm weekdays, "
                "Mid-Peak 11am-5pm weekdays, Off-Peak all other times."
            ),
            components=[
                # Energy charges (from OEB)
                RateComponent(
                    component_type="energy",
                    component_name="Off-Peak Energy",
                    charge_value=OEB_TOU_RATES["off_peak"],
                    charge_unit="$/kWh",
                    tou_period="off-peak",
                    tou_hours="Weekdays 7pm-7am, all day weekends & holidays",
                    source_url=OEB_TOU_RATES["source_url"],
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Mid-Peak Energy",
                    charge_value=OEB_TOU_RATES["mid_peak"],
                    charge_unit="$/kWh",
                    tou_period="mid-peak",
                    tou_hours="Weekdays 11am-5pm",
                    source_url=OEB_TOU_RATES["source_url"],
                ),
                RateComponent(
                    component_type="energy",
                    component_name="On-Peak Energy",
                    charge_value=OEB_TOU_RATES["on_peak"],
                    charge_unit="$/kWh",
                    tou_period="on-peak",
                    tou_hours="Weekdays 7am-11am & 5pm-7pm",
                    source_url=OEB_TOU_RATES["source_url"],
                ),
                # Delivery charges (from Toronto Hydro)
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Service Charge",
                    charge_value=TORONTO_HYDRO_DELIVERY["residential_fixed_monthly"],
                    charge_unit="$/month",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                ),
                RateComponent(
                    component_type="distribution",
                    component_name="Distribution Volumetric Rate",
                    charge_value=TORONTO_HYDRO_DELIVERY["residential_distribution_volumetric"],
                    charge_unit="$/kWh",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Transmission — Network",
                    charge_value=TORONTO_HYDRO_DELIVERY["residential_transmission_network"],
                    charge_unit="$/kWh",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Transmission — Connection",
                    charge_value=TORONTO_HYDRO_DELIVERY["residential_transmission_connection"],
                    charge_unit="$/kWh",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                ),
                RateComponent(
                    component_type="regulatory",
                    component_name="Regulatory Charge",
                    charge_value=TORONTO_HYDRO_DELIVERY["regulatory_charge"],
                    charge_unit="$/kWh",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                    notes="Covers OEB operating costs",
                ),
            ],
        ))

        # ── Residential Tiered ────────────────────────────────
        records.append(TariffRecord(
            utility_name="Toronto Hydro",
            province="ON",
            utility_type="electricity",
            tariff_name="Residential — Tiered Pricing",
            tariff_code="TIER-R",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=OEB_TIERED_RATES["effective_date"],
            source_url=TORONTO_HYDRO_DELIVERY["source_url"],
            confidence="high",
            notes=(
                "Ontario residential tiered rate (opt-in alternative to TOU). "
                "Tier 1 threshold is 1,000 kWh/month in winter (Nov-Apr), "
                "600 kWh/month in summer (May-Oct)."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="Tier 1 Energy",
                    charge_value=OEB_TIERED_RATES["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=OEB_TIERED_RATES["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    season="winter",
                    season_months="Nov-Apr",
                    source_url=OEB_TIERED_RATES["source_url"],
                    notes="1,000 kWh/month winter threshold; 600 kWh/month summer",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy",
                    charge_value=OEB_TIERED_RATES["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=OEB_TIERED_RATES["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    source_url=OEB_TIERED_RATES["source_url"],
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Service Charge",
                    charge_value=TORONTO_HYDRO_DELIVERY["residential_fixed_monthly"],
                    charge_unit="$/month",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                ),
                RateComponent(
                    component_type="distribution",
                    component_name="Distribution Volumetric Rate",
                    charge_value=TORONTO_HYDRO_DELIVERY["residential_distribution_volumetric"],
                    charge_unit="$/kWh",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Transmission — Network",
                    charge_value=TORONTO_HYDRO_DELIVERY["residential_transmission_network"],
                    charge_unit="$/kWh",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Transmission — Connection",
                    charge_value=TORONTO_HYDRO_DELIVERY["residential_transmission_connection"],
                    charge_unit="$/kWh",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                ),
                RateComponent(
                    component_type="regulatory",
                    component_name="Regulatory Charge",
                    charge_value=TORONTO_HYDRO_DELIVERY["regulatory_charge"],
                    charge_unit="$/kWh",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                ),
            ],
        ))

        # ── Residential ULO ───────────────────────────────────
        records.append(TariffRecord(
            utility_name="Toronto Hydro",
            province="ON",
            utility_type="electricity",
            tariff_name="Residential — Ultra-Low Overnight (ULO)",
            tariff_code="ULO-R",
            customer_class="residential",
            rate_structure="tou",
            effective_date=OEB_ULO_RATES["effective_date"],
            source_url=TORONTO_HYDRO_DELIVERY["source_url"],
            confidence="high",
            notes=(
                "Ontario ULO rate — opt-in for EV owners and overnight heavy users. "
                "Ultra-low period is 11pm-7am daily."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="Ultra-Low Overnight Energy",
                    charge_value=OEB_ULO_RATES["ultra_low_overnight"],
                    charge_unit="$/kWh",
                    tou_period="ultra-low-overnight",
                    tou_hours="Daily 11pm-7am",
                    source_url=OEB_ULO_RATES["source_url"],
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Weekend Off-Peak Energy",
                    charge_value=OEB_ULO_RATES["weekend_off_peak"],
                    charge_unit="$/kWh",
                    tou_period="off-peak",
                    tou_hours="Weekends & holidays 7am-11pm",
                    source_url=OEB_ULO_RATES["source_url"],
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Mid-Peak Energy",
                    charge_value=OEB_ULO_RATES["mid_peak"],
                    charge_unit="$/kWh",
                    tou_period="mid-peak",
                    tou_hours="Weekdays 7am-4pm & 9pm-11pm",
                    source_url=OEB_ULO_RATES["source_url"],
                ),
                RateComponent(
                    component_type="energy",
                    component_name="On-Peak Energy",
                    charge_value=OEB_ULO_RATES["on_peak"],
                    charge_unit="$/kWh",
                    tou_period="on-peak",
                    tou_hours="Weekdays 4pm-9pm",
                    source_url=OEB_ULO_RATES["source_url"],
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Service Charge",
                    charge_value=TORONTO_HYDRO_DELIVERY["residential_fixed_monthly"],
                    charge_unit="$/month",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                ),
                RateComponent(
                    component_type="distribution",
                    component_name="Distribution Volumetric Rate",
                    charge_value=TORONTO_HYDRO_DELIVERY["residential_distribution_volumetric"],
                    charge_unit="$/kWh",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                ),
                RateComponent(
                    component_type="regulatory",
                    component_name="Regulatory Charge",
                    charge_value=TORONTO_HYDRO_DELIVERY["regulatory_charge"],
                    charge_unit="$/kWh",
                    source_url=TORONTO_HYDRO_DELIVERY["source_url"],
                ),
            ],
        ))

        return records
