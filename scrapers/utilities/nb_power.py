"""
nb_power.py — Scraper for NB Power electricity rates (New Brunswick).

NB Power (New Brunswick Power Corporation) is the primary electric utility
in New Brunswick, a provincial Crown corporation. Residential rates use a
two-tier structure based on monthly consumption.

Official source:
  https://www.nbpower.com/en/products-services/residential/rates

Regulated by: New Brunswick Energy and Utilities Board (EUB NB)
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Known rate values — used as seed/fallback data.
SEED_RESIDENTIAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.nbpower.com/en/products-services/residential/rates",
    "tier1_threshold_kwh": 1400,   # first 1,400 kWh per month
    "tier1_rate": 0.1193,          # $/kWh
    "tier2_rate": 0.1634,          # $/kWh — remaining kWh
    "basic_charge_per_month": 22.84,  # $/month
}

SEED_SMALL_INDUSTRIAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.nbpower.com/en/products-services/business/rates",
    "energy_rate": 0.0772,         # $/kWh
    "demand_charge": 7.52,         # $/kW
    "basic_charge_per_month": 22.84,  # $/month
}


class NBPowerScraper(BaseScraper):
    """Scrape NB Power electricity rates."""

    def __init__(self):
        super().__init__(utility_name="NB Power", province="NB")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live NB Power rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d NB Power tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for NB Power")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live NB Power website."""
        # TODO: implement HTML parsing once page structure is verified
        return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Residential (Two-Tier) ───────────────────────────────
        records.append(TariffRecord(
            utility_name="NB Power",
            province="NB",
            utility_type="electricity",
            tariff_name="Residential Service (Rate D)",
            tariff_code="D",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes=(
                "NB Power two-tier residential rate. "
                "Tier 1 applies to the first 1,400 kWh per month."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                    notes="Monthly basic charge regardless of consumption",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 1 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_RESIDENTIAL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="Applies to first 1,400 kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_RESIDENTIAL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="Applies to all kWh above the Tier 1 threshold",
                ),
            ],
        ))

        # ── Small Industrial ─────────────────────────────────────
        records.append(TariffRecord(
            utility_name="NB Power",
            province="NB",
            utility_type="electricity",
            tariff_name="Small Industrial Service",
            customer_class="commercial",
            sub_class="small industrial",
            rate_structure="demand",
            effective_date=SEED_SMALL_INDUSTRIAL["effective_date"],
            source_url=SEED_SMALL_INDUSTRIAL["source_url"],
            confidence="high",
            eligibility="Small industrial customers with demand metering",
            notes="NB Power small industrial rate with demand and energy charges",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_SMALL_INDUSTRIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_SMALL_INDUSTRIAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to billing demand (kW)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_SMALL_INDUSTRIAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Energy charge per kWh consumed",
                ),
            ],
        ))

        return records
