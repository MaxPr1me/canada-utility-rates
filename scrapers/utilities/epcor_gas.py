"""
epcor_gas.py — Scraper for EPCOR Natural Gas rates (Alberta).

EPCOR provides natural gas distribution in parts of Alberta,
primarily serving smaller communities.

Official source:
  https://www.epcor.com/products-services/natural-gas/rates-and-billing/

Alberta has a deregulated gas market — EPCOR provides distribution
only, while gas supply is purchased from a competitive retailer or
the regulated default supply.

Regulated by the Alberta Utilities Commission (AUC).
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Seed data based on limited publicly available rate information.
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.epcor.com/products-services/natural-gas/rates-and-billing/",
    "customer_charge_monthly": 32.00,           # $/month
    "distribution_rate": 1.28,                  # $/GJ
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
    "rate_rider": 0.0350,                       # $/GJ — adjustment rider
}


class EPCORGasScraper(BaseScraper):
    """Scrape EPCOR Natural Gas distribution rates for Alberta."""

    def __init__(self):
        super().__init__(utility_name="EPCOR Natural Gas", province="AB")

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for EPCOR Natural Gas")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        try:
            html = self.fetch_page(SEED_RESIDENTIAL["source_url"])
            return None
        except Exception as e:
            self.logger.warning("Could not fetch EPCOR Natural Gas page: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="EPCOR Natural Gas",
            province="AB",
            utility_type="gas",
            tariff_name="Residential Distribution",
            tariff_code="D-Res",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="low",
            notes=(
                "EPCOR Natural Gas distribution charges for Alberta. "
                "Limited public rate data available — values are approximate. "
                "Alberta is deregulated — gas supply must be purchased "
                "separately from a retailer or default supply provider. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_RESIDENTIAL["customer_charge_monthly"],
                    charge_unit="$/month",
                    confidence="low",
                    notes="Fixed monthly distribution charge",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Distribution Charge",
                    charge_value=SEED_RESIDENTIAL["distribution_rate"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="Volume-based distribution charge for gas delivery",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_RESIDENTIAL["carbon_charge"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Rate Rider",
                    charge_value=SEED_RESIDENTIAL["rate_rider"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="AUC-approved rate adjustment rider",
                ),
            ],
        ))

        return records
