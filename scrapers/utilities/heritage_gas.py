"""
heritage_gas.py — Scraper for Heritage Gas rates (Nova Scotia).

Heritage Gas Limited provides natural gas distribution to parts of
Nova Scotia, including the Halifax Regional Municipality, Amherst,
and other communities.

Official source:
  https://www.heritagegas.com/rates/

Nova Scotia gas rates are regulated by the Nova Scotia Utility and
Review Board (NSUARB).  Heritage Gas uses GJ as the primary billing unit.
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Seed data — limited public rate information available.
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.heritagegas.com/rates/",
    "basic_charge_monthly": 20.00,              # $/month
    "delivery_rate": 10.50,                     # $/GJ — delivery/distribution
    "commodity_rate": 8.00,                     # $/GJ — gas supply (varies with market)
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
}


class HeritageGasScraper(BaseScraper):
    """Scrape Heritage Gas natural gas rates for Nova Scotia."""

    def __init__(self):
        super().__init__(utility_name="Heritage Gas", province="NS")

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for Heritage Gas")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        try:
            html = self.fetch_page(SEED_RESIDENTIAL["source_url"])
            return None
        except Exception as e:
            self.logger.warning("Could not fetch Heritage Gas page: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Heritage Gas",
            province="NS",
            utility_type="gas",
            tariff_name="Residential — Small General Service",
            tariff_code="SGS",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="low",
            notes=(
                "Heritage Gas residential rate for Nova Scotia. "
                "Limited public rate data — values are approximate. "
                "Heritage Gas serves a small service area including Halifax "
                "and Amherst. Commodity rate varies with market conditions. "
                "Regulated by the NSUARB."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="low",
                    notes="Fixed monthly customer charge",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Delivery Charge",
                    charge_value=SEED_RESIDENTIAL["delivery_rate"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="Heritage Gas distribution charge for gas delivery",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Gas Supply Charge",
                    charge_value=SEED_RESIDENTIAL["commodity_rate"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="Gas commodity cost — varies with market conditions",
                    market_reference="Nova Scotia gas supply portfolio",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_RESIDENTIAL["carbon_charge"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
            ],
        ))

        return records
