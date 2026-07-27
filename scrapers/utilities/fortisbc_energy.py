"""
fortisbc_energy.py — Scraper for FortisBC Energy natural gas rates (BC).

FortisBC Energy Inc. is the primary natural gas distributor in British
Columbia, serving over one million customers.

Official source:
  https://www.fortisbc.com/gas/gas-rates

BC gas rates are regulated by the British Columbia Utilities Commission (BCUC).
FortisBC uses GJ as the primary billing unit.
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Seed data based on BCUC-approved rates.
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.fortisbc.com/gas/gas-rates",
    "basic_charge_monthly": 14.48,              # $/month
    "delivery_rate": 6.7040,                    # $/GJ
    "cost_of_gas": 2.4430,                      # $/GJ
    "storage_and_transport": 1.6700,            # $/GJ
    "carbon_tax": 3.1050,                       # $/GJ — BC provincial carbon tax
    "rate_rider": -0.0980,                      # $/GJ — revenue surplus refund
}

SEED_COMMERCIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.fortisbc.com/gas/gas-rates",
    "basic_charge_monthly": 18.00,              # $/month
    "delivery_rate": 5.4550,                    # $/GJ
    "cost_of_gas": 2.4430,                      # $/GJ
    "storage_and_transport": 1.6700,            # $/GJ
    "carbon_tax": 3.1050,                       # $/GJ
    "rate_rider": -0.0750,                      # $/GJ
}


class FortisBCEnergyScraper(BaseScraper):
    """Scrape FortisBC Energy natural gas rates for British Columbia."""

    def __init__(self):
        super().__init__(utility_name="FortisBC Energy", province="BC")

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for FortisBC Energy")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Verify every modelled component against the current official schedule."""
        return self.verify_official_records(SEED_RESIDENTIAL["source_url"], self._seed_data())

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential — Rate 1 ─────────────────────────────────
        records.append(TariffRecord(
            utility_name="FortisBC Energy",
            province="BC",
            utility_type="gas",
            tariff_name="Residential — Rate 1",
            tariff_code="Rate 1",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes=(
                "FortisBC Energy residential gas rate. "
                "Cost of gas is a pass-through from commodity markets. "
                "BC carbon tax is provincial, not the federal backstop. "
                "Regulated by BCUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="high",
                    notes="Fixed monthly customer charge",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Delivery Charge",
                    charge_value=SEED_RESIDENTIAL["delivery_rate"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="FortisBC distribution charge for delivering gas",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Cost of Gas",
                    charge_value=SEED_RESIDENTIAL["cost_of_gas"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Pass-through commodity cost — adjusted quarterly by BCUC",
                    market_reference="FortisBC gas commodity portfolio",
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Storage and Transport",
                    charge_value=SEED_RESIDENTIAL["storage_and_transport"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Pipeline transportation and underground storage costs",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Carbon Tax",
                    charge_value=SEED_RESIDENTIAL["carbon_tax"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="BC provincial carbon tax on natural gas",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Rate Rider",
                    charge_value=SEED_RESIDENTIAL["rate_rider"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Revenue surplus/deficiency adjustment — can be negative (credit)",
                ),
            ],
        ))

        # ── Commercial — Rate 2 ──────────────────────────────────
        records.append(TariffRecord(
            utility_name="FortisBC Energy",
            province="BC",
            utility_type="gas",
            tariff_name="Commercial — Rate 2",
            tariff_code="Rate 2",
            customer_class="commercial",
            rate_structure="flat",
            effective_date=SEED_COMMERCIAL["effective_date"],
            source_url=SEED_COMMERCIAL["source_url"],
            confidence="high",
            notes=(
                "FortisBC Energy small commercial gas rate. "
                "Lower delivery rate than residential. "
                "Regulated by BCUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_COMMERCIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="high",
                    notes="Fixed monthly customer charge for commercial accounts",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Delivery Charge",
                    charge_value=SEED_COMMERCIAL["delivery_rate"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Distribution charge — lower rate for commercial class",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Cost of Gas",
                    charge_value=SEED_COMMERCIAL["cost_of_gas"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Pass-through commodity cost — same as residential",
                    market_reference="FortisBC gas commodity portfolio",
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Storage and Transport",
                    charge_value=SEED_COMMERCIAL["storage_and_transport"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Pipeline transportation and underground storage costs",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Carbon Tax",
                    charge_value=SEED_COMMERCIAL["carbon_tax"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="BC provincial carbon tax on natural gas",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Rate Rider",
                    charge_value=SEED_COMMERCIAL["rate_rider"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Revenue surplus/deficiency adjustment — can be negative (credit)",
                ),
            ],
        ))

        return records
