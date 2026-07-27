"""
maritime_electric.py — Scraper for Maritime Electric electricity rates (Prince Edward Island).

Maritime Electric Company, Limited is the sole electricity provider in
Prince Edward Island. It is a subsidiary of Fortis Inc. PEI imports a
significant share of its electricity from New Brunswick.

Official source:
  https://www.maritimeelectric.com/my-account/understanding-my-bill/understanding-rates/

Regulated by: Island Regulatory and Appeals Commission (IRAC)
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Known rate values — used as seed/fallback data.
# Rates are approximate; IRAC publishes exact approved schedules.
SEED_RESIDENTIAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.maritimeelectric.com/my-account/understanding-my-bill/understanding-rates/",
    "energy_rate": 0.1740,          # $/kWh
    "basic_charge_per_month": 19.28,  # $/month
}

SEED_GENERAL_SERVICE = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.maritimeelectric.com/my-account/understanding-my-bill/understanding-rates/",
    "energy_rate": 0.1740,          # $/kWh
    "basic_charge_per_month": 30.00,  # $/month
}


class MaritimeElectricScraper(BaseScraper):
    """Scrape Maritime Electric electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Maritime Electric", province="PE")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Maritime Electric rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Maritime Electric tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for Maritime Electric")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Verify every community/tier component against the official schedule."""
        return self.verify_official_records(SEED_RESIDENTIAL["source_url"], self._seed_data())

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Maritime Electric",
            province="PE",
            utility_type="electricity",
            tariff_name="Residential Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "Maritime Electric (Fortis-owned) residential rate. "
                "Rates are approximate; check IRAC-approved rate schedule for exact values."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Monthly basic charge regardless of consumption",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        # ── General Service ──────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Maritime Electric",
            province="PE",
            utility_type="electricity",
            tariff_name="General Service",
            customer_class="commercial",
            sub_class="general service",
            rate_structure="flat",
            effective_date=SEED_GENERAL_SERVICE["effective_date"],
            source_url=SEED_GENERAL_SERVICE["source_url"],
            confidence="medium",
            eligibility="Small commercial customers",
            notes=(
                "Maritime Electric (Fortis-owned) general service rate. "
                "Rates are approximate; check IRAC-approved rate schedule for exact values."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_GENERAL_SERVICE["basic_charge_per_month"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_GENERAL_SERVICE["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        return records
