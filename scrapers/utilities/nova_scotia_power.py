"""
nova_scotia_power.py — Scraper for Nova Scotia Power electricity rates (Nova Scotia).

Nova Scotia Power Inc. (NSPI) is the primary electricity provider in
Nova Scotia, an investor-owned utility (Emera subsidiary). Rates are
predominantly flat for residential and small general customers.

Official source:
  https://www.nspower.ca/products-services/rate-information

Regulated by: Nova Scotia Utility and Review Board (NSUARB)
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Known rate values — used as seed/fallback data.
SEED_RESIDENTIAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.nspower.ca/products-services/rate-information",
    "energy_rate": 0.16996,         # $/kWh
    "basic_charge_per_month": 11.97,  # $/month
}

SEED_SMALL_GENERAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.nspower.ca/products-services/rate-information",
    "energy_rate": 0.16996,         # $/kWh
    "basic_charge_per_month": 12.74,  # $/month
    "demand_charge": 4.09,          # $/kW — applies above 20 kW
    "demand_threshold_kw": 20,      # demand charge only above this
}


class NovaScotiaPowerScraper(BaseScraper):
    """Scrape Nova Scotia Power electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Nova Scotia Power", province="NS")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Nova Scotia Power rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Nova Scotia Power tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for Nova Scotia Power")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live Nova Scotia Power website."""
        # TODO: implement HTML parsing once page structure is verified
        return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Domestic Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes="Nova Scotia Power domestic (residential) flat electricity rate",
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
                    component_name="Energy Charge",
                    charge_value=SEED_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        # ── Small General ────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Small General Service",
            customer_class="commercial",
            sub_class="small general",
            rate_structure="demand",
            effective_date=SEED_SMALL_GENERAL["effective_date"],
            source_url=SEED_SMALL_GENERAL["source_url"],
            confidence="high",
            eligibility="Small commercial customers; demand charge applies above 20 kW",
            notes=(
                "Nova Scotia Power small general service rate. "
                "Demand charge applies only to billing demand exceeding 20 kW."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_SMALL_GENERAL["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_SMALL_GENERAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_SMALL_GENERAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    demand_threshold_kw=SEED_SMALL_GENERAL["demand_threshold_kw"],
                    notes="Applied to billing demand exceeding 20 kW",
                ),
            ],
        ))

        return records
