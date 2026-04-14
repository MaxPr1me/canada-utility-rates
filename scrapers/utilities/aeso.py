"""
aeso.py -- Scraper for Alberta Electric System Operator (AESO) pool price.

AESO is not a utility -- it is the independent system operator that
manages Alberta's wholesale electricity market. This scraper produces
a single reference tariff record representing the AESO pool price,
which is the basis for all Regulated Rate Option (RRO) pricing in
the province.

Official source:
  https://www.aeso.ca/market/market-and-system-reporting/hourly-pool-price-report/

The pool price varies hourly. The seed value here is a recent average
and should be treated as a reference point, not a retail rate.
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

SOURCE_URL = (
    "https://www.aeso.ca/market/market-and-system-reporting/"
    "hourly-pool-price-report/"
)

SEED_POOL_PRICE = {
    "effective_date": "2024-10-01",
    "source_url": SOURCE_URL,
    "average_pool_price": 0.0952,  # $/kWh -- recent average
}


class AESOScraper(BaseScraper):
    """Scrape AESO pool price reference data for Alberta."""

    def __init__(self):
        super().__init__(
            utility_name="Alberta Electric System Operator",
            province="AB",
        )

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning(
                "Live scrape failed -- using seed data for AESO"
            )
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        try:
            html = self.fetch_page(SOURCE_URL)
            # TODO: parse live AESO pool price from report page
            return None
        except Exception as e:
            self.logger.warning(
                "Could not fetch AESO pool price report: %s", e
            )
            return None

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        records.append(TariffRecord(
            utility_name="Alberta Electric System Operator",
            province="AB",
            utility_type="electricity",
            tariff_name="AESO Pool Price Reference",
            customer_class="other",
            sub_class="market reference",
            rate_structure="market",
            effective_date=SEED_POOL_PRICE["effective_date"],
            source_url=SEED_POOL_PRICE["source_url"],
            confidence="medium",
            notes=(
                "Average AESO pool price. Real-time price varies hourly. "
                "This is a reference, not a retail rate."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="AESO Pool Price (Average)",
                    charge_value=SEED_POOL_PRICE["average_pool_price"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    market_reference="AESO pool price",
                    market_source_url=SOURCE_URL,
                    notes=(
                        "Average AESO pool price. The actual pool price "
                        "varies hourly based on supply and demand in "
                        "Alberta's wholesale electricity market. This "
                        "value is a recent average used as a reference."
                    ),
                ),
            ],
        ))

        return records
