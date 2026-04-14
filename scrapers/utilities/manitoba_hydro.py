"""
manitoba_hydro.py — Scraper for Manitoba Hydro electricity rates (Manitoba).

Manitoba Hydro is the sole electricity and natural gas utility in Manitoba.
Manitoba benefits from abundant hydroelectric generation, resulting in some
of the lowest electricity rates in Canada.

Official source:
  https://www.hydro.mb.ca/accounts-and-billing/rates/

Regulated by: Public Utilities Board of Manitoba (PUB Manitoba)
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Known rate values — used as seed/fallback data.
SEED_RESIDENTIAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.hydro.mb.ca/accounts-and-billing/rates/",
    "energy_rate": 0.09940,        # $/kWh — flat rate
    "basic_charge_per_month": 8.81,  # $/month
}

SEED_GENERAL_SERVICE_SMALL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.hydro.mb.ca/accounts-and-billing/rates/",
    "energy_rate": 0.09032,        # $/kWh
    "basic_charge_per_month": 8.81,  # $/month
}

SEED_GENERAL_SERVICE_MEDIUM = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.hydro.mb.ca/accounts-and-billing/rates/",
    "energy_rate": 0.04526,        # $/kWh
    "demand_charge": 10.47,        # $/kW
    "basic_charge_per_month": 25.80,  # $/month
}


class ManitobaHydroScraper(BaseScraper):
    """Scrape Manitoba Hydro electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Manitoba Hydro", province="MB")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Manitoba Hydro rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Manitoba Hydro tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for Manitoba Hydro")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live Manitoba Hydro website."""
        # TODO: implement HTML parsing once page structure is verified
        return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Manitoba Hydro",
            province="MB",
            utility_type="electricity",
            tariff_name="Residential Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes=(
                "Manitoba Hydro flat residential rate. "
                "Among the lowest electricity rates in Canada due to abundant hydroelectric generation."
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
                    component_name="Energy Charge",
                    charge_value=SEED_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        # ── General Service Small (Non-Demand) ───────────────────
        records.append(TariffRecord(
            utility_name="Manitoba Hydro",
            province="MB",
            utility_type="electricity",
            tariff_name="General Service Small (Non-Demand)",
            customer_class="commercial",
            sub_class="general service small",
            rate_structure="flat",
            effective_date=SEED_GENERAL_SERVICE_SMALL["effective_date"],
            source_url=SEED_GENERAL_SERVICE_SMALL["source_url"],
            confidence="high",
            eligibility="Non-demand metered commercial customers",
            notes="Small commercial accounts without demand metering",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_GENERAL_SERVICE_SMALL["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_GENERAL_SERVICE_SMALL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        # ── General Service Medium (Demand) ──────────────────────
        records.append(TariffRecord(
            utility_name="Manitoba Hydro",
            province="MB",
            utility_type="electricity",
            tariff_name="General Service Medium (Demand)",
            customer_class="commercial",
            sub_class="general service medium",
            rate_structure="demand",
            effective_date=SEED_GENERAL_SERVICE_MEDIUM["effective_date"],
            source_url=SEED_GENERAL_SERVICE_MEDIUM["source_url"],
            confidence="high",
            eligibility="Demand-metered commercial customers",
            notes="Medium commercial accounts with demand metering",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_GENERAL_SERVICE_MEDIUM["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_GENERAL_SERVICE_MEDIUM["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to billing demand (kW)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_GENERAL_SERVICE_MEDIUM["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Energy charge per kWh consumed",
                ),
            ],
        ))

        return records
