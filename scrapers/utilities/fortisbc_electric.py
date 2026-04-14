"""
fortisbc_electric.py — Scraper for FortisBC Electric rates (British Columbia).

FortisBC Electric serves customers in the southern interior of BC,
including the Okanagan, Kootenay, and South Similkameen regions.
Residential rates use a two-tier (step) pricing structure similar to BC Hydro.

Official source:
  https://www.fortisbc.com/electricity/electricity-rates

Regulated by: British Columbia Utilities Commission (BCUC)
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Known rate values — used as seed/fallback data.
SEED_RESIDENTIAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.fortisbc.com/electricity/electricity-rates",
    "step1_threshold_kwh": 1600,   # per 2-month billing period
    "step1_rate": 0.0945,          # $/kWh
    "step2_rate": 0.1408,          # $/kWh
    "basic_charge_per_day": 0.2070,  # $/day
}

SEED_SMALL_GENERAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.fortisbc.com/electricity/electricity-rates",
    "demand_charge": 6.18,         # $/kW
    "energy_rate": 0.0689,         # $/kWh
    "basic_charge_per_day": 0.4384,  # $/day
}


class FortisBCElectricScraper(BaseScraper):
    """Scrape FortisBC Electric electricity rates."""

    def __init__(self):
        super().__init__(utility_name="FortisBC Electric", province="BC")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live FortisBC Electric rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d FortisBC Electric tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for FortisBC Electric")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live FortisBC website."""
        # TODO: implement HTML parsing once page structure is verified
        return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Residential (Two-Tier / Step) ────────────────────────
        records.append(TariffRecord(
            utility_name="FortisBC Electric",
            province="BC",
            utility_type="electricity",
            tariff_name="Residential Service (Rate 01)",
            tariff_code="01",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes=(
                "FortisBC Electric two-step residential rate. "
                "Step 1 applies to the first 1,600 kWh per 2-month billing period."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_day"],
                    charge_unit="$/day",
                    notes="Daily basic charge regardless of consumption",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Step 1 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["step1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_RESIDENTIAL["step1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="Applies to first 1,600 kWh per 2-month billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Step 2 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["step2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_RESIDENTIAL["step1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="Applies to all kWh above the Step 1 threshold",
                ),
            ],
        ))

        # ── Small General Service (Rate 20) ──────────────────────
        records.append(TariffRecord(
            utility_name="FortisBC Electric",
            province="BC",
            utility_type="electricity",
            tariff_name="Small General Service (Rate 20)",
            tariff_code="20",
            customer_class="commercial",
            sub_class="small general service",
            rate_structure="demand",
            effective_date=SEED_SMALL_GENERAL["effective_date"],
            source_url=SEED_SMALL_GENERAL["source_url"],
            confidence="high",
            eligibility="Commercial customers under 150 kW demand",
            demand_max_kw=150,
            notes="FortisBC Electric small commercial rate with demand and energy charges",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_SMALL_GENERAL["basic_charge_per_day"],
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_SMALL_GENERAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to billing demand (kW)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_SMALL_GENERAL["energy_rate"],
                    charge_unit="$/kWh",
                ),
            ],
        ))

        return records
