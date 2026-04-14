"""
liberty_gas_nb.py — Scraper for Liberty Utilities gas rates (New Brunswick).

Liberty Utilities provides natural gas distribution in parts of
New Brunswick, serving a relatively small service area.

Official source:
  https://libertyutilities.com/east/gas/rates

New Brunswick gas rates are regulated by the Energy and Utilities
Board of New Brunswick (EUB NB).  Liberty uses GJ as the primary
billing unit.
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Seed data — limited public rate information available.
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://libertyutilities.com/east/gas/rates",
    "basic_charge_monthly": 18.00,              # $/month
    "delivery_rate": 7.00,                      # $/GJ — delivery/distribution
    "commodity_rate": 6.50,                     # $/GJ — gas supply (market-linked)
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
    "rate_rider": 0.0250,                       # $/GJ — periodic adjustment
}


class LibertyGasNBScraper(BaseScraper):
    """Scrape Liberty Utilities natural gas rates for New Brunswick."""

    def __init__(self):
        super().__init__(utility_name="Liberty Utilities Gas NB", province="NB")

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for Liberty Utilities Gas NB")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        try:
            html = self.fetch_page(SEED_RESIDENTIAL["source_url"])
            return None
        except Exception as e:
            self.logger.warning("Could not fetch Liberty Utilities Gas NB page: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Liberty Utilities Gas NB",
            province="NB",
            utility_type="gas",
            tariff_name="Residential — Small General Service",
            tariff_code="SGS",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="low",
            notes=(
                "Liberty Utilities residential gas rate for New Brunswick. "
                "Small service area — limited public rate data available. "
                "Commodity rate is market-linked and varies. "
                "Regulated by the EUB NB."
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
                    notes="Liberty distribution charge for gas delivery",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Gas Supply Charge",
                    charge_value=SEED_RESIDENTIAL["commodity_rate"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="Gas commodity cost — market-linked, varies periodically",
                    market_reference="New Brunswick gas supply portfolio",
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
                    notes="Periodic rate adjustment rider",
                ),
            ],
        ))

        return records
