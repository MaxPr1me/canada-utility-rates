"""
enbridge_gas.py — Scraper for Enbridge Gas rates (Ontario).

Enbridge Gas (formerly Union Gas + Enbridge Gas Distribution) is the
primary natural gas distributor in Ontario.

Official source:
  https://www.enbridgegas.com/residential/gas-charges

Ontario gas customers see charges from multiple sources:
  - Gas supply (commodity) — set by OEB or market
  - Delivery — Enbridge's distribution charge
  - Transportation — pipeline costs
  - Customer charge (fixed monthly)
  - Carbon charges — federal carbon levy
  - Various riders and adjustments

This scraper demonstrates a natural gas utility with many components.
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Seed data based on OEB-approved rates.
# Enbridge operates in two legacy rate zones.
SEED_RATE_1 = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.enbridgegas.com/residential/gas-charges",
    "customer_charge_monthly": 28.44,        # $/month
    "gas_supply_rate": 0.1039,               # $/m³ (commodity)
    "delivery_to_you_rate": 0.0993,          # $/m³
    "transportation_rate": 0.0409,           # $/m³
    "federal_carbon_charge": 0.1239,         # $/m³
    "cost_adjustment_rider": -0.0012,        # $/m³ (can be negative — a credit)
}


class EnbridgeGasScraper(BaseScraper):
    """Scrape Enbridge Gas rates for Ontario."""

    def __init__(self):
        super().__init__(utility_name="Enbridge Gas", province="ON")

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for Enbridge Gas")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        try:
            html = self.fetch_page(SEED_RATE_1["source_url"])
            return None
        except Exception as e:
            self.logger.warning("Could not fetch Enbridge Gas page: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential — Rate 1 (Union South legacy area) ───
        records.append(TariffRecord(
            utility_name="Enbridge Gas",
            province="ON",
            utility_type="gas",
            tariff_name="Residential — Rate 1 (Union South)",
            tariff_code="Rate 1",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RATE_1["effective_date"],
            source_url=SEED_RATE_1["source_url"],
            confidence="high",
            notes=(
                "Enbridge Gas residential rate for Union South legacy service area. "
                "Gas supply (commodity) rate includes a mix of fixed and variable components. "
                "Total cost per m³ is the sum of all volumetric components."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_RATE_1["customer_charge_monthly"],
                    charge_unit="$/month",
                    notes="Fixed monthly charge regardless of gas usage",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Gas Supply Charge",
                    charge_value=SEED_RATE_1["gas_supply_rate"],
                    charge_unit="$/m³",
                    notes="Cost of the natural gas commodity — set by OEB quarterly",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Delivery to You",
                    charge_value=SEED_RATE_1["delivery_to_you_rate"],
                    charge_unit="$/m³",
                    notes="Enbridge distribution charge for delivering gas to your home",
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Transportation to Enbridge",
                    charge_value=SEED_RATE_1["transportation_rate"],
                    charge_unit="$/m³",
                    notes="Cost of transporting gas through upstream pipelines to Enbridge's system",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_RATE_1["federal_carbon_charge"],
                    charge_unit="$/m³",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Cost Adjustment Rider",
                    charge_value=SEED_RATE_1["cost_adjustment_rider"],
                    charge_unit="$/m³",
                    notes="Quarterly adjustment — can be positive or negative",
                ),
            ],
        ))

        return records
