"""
enmax_energy.py -- Scraper for ENMAX Energy Corporation RRO rates (Alberta).

ENMAX Energy Corporation is the Regulated Rate Option (RRO)
electricity provider for the ENMAX Power (Calgary) service area.

Official source:
  https://www.enmax.com/home/rates-and-billing/understand-your-bill/regulated-rate-option

Alberta has a deregulated electricity market. The RRO is a regulated
default supply rate for customers who have not chosen a competitive
retailer. The RRO energy rate changes monthly based on the AESO pool
price and a risk premium.

Regulated by the Alberta Utilities Commission (AUC).
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

AESO_MARKET_URL = (
    "https://www.aeso.ca/market/market-and-system-reporting/"
    "hourly-pool-price-report/"
)

SOURCE_URL = (
    "https://www.enmax.com/home/rates-and-billing/"
    "understand-your-bill/regulated-rate-option"
)

SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": SOURCE_URL,
    "energy_rate": 0.1684,       # $/kWh
    "admin_fee_monthly": 5.95,   # $/month
}

SEED_COMMERCIAL = {
    "effective_date": "2024-10-01",
    "source_url": SOURCE_URL,
    "energy_rate": 0.1684,       # $/kWh
    "admin_fee_monthly": 7.95,   # $/month
}


class ENMAXEnergyScraper(BaseScraper):
    """Scrape ENMAX Energy Corporation RRO rates for Calgary, Alberta."""

    def __init__(self):
        super().__init__(
            utility_name="ENMAX Energy Corporation",
            province="AB",
        )

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning(
                "Live scrape failed -- using seed data for ENMAX Energy"
            )
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        try:
            html = self.fetch_page(SOURCE_URL)
            # TODO: parse live RRO rate from ENMAX page
            return None
        except Exception as e:
            self.logger.warning(
                "Could not fetch ENMAX Energy page: %s", e
            )
            return None

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # -- Residential RRO -----------------------------------------------
        records.append(TariffRecord(
            utility_name="ENMAX Energy Corporation",
            province="AB",
            utility_type="electricity",
            tariff_name="Residential Regulated Rate Option",
            tariff_code="RRO-Res",
            customer_class="residential",
            rate_structure="market",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "ENMAX Energy provides the Regulated Rate Option (RRO) "
                "for the ENMAX Power (Calgary) service area. The energy "
                "rate changes monthly based on the AESO pool price plus "
                "a regulated risk premium. Distribution charges from "
                "ENMAX Power are separate. Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="RRO Energy Charge",
                    charge_value=SEED_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    market_reference="AESO pool price",
                    market_source_url=AESO_MARKET_URL,
                    notes=(
                        "Regulated Rate Option energy charge -- varies "
                        "monthly based on AESO pool price"
                    ),
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Administration Fee",
                    charge_value=SEED_RESIDENTIAL["admin_fee_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly administration fee",
                ),
            ],
        ))

        # -- Commercial RRO ------------------------------------------------
        records.append(TariffRecord(
            utility_name="ENMAX Energy Corporation",
            province="AB",
            utility_type="electricity",
            tariff_name="Commercial Regulated Rate Option",
            tariff_code="RRO-Com",
            customer_class="commercial",
            rate_structure="market",
            effective_date=SEED_COMMERCIAL["effective_date"],
            source_url=SEED_COMMERCIAL["source_url"],
            confidence="medium",
            notes=(
                "ENMAX Energy commercial RRO for the Calgary service "
                "area. Same energy rate structure as residential -- "
                "varies monthly with AESO pool price. Distribution "
                "charges from ENMAX Power are separate. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="RRO Energy Charge",
                    charge_value=SEED_COMMERCIAL["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    market_reference="AESO pool price",
                    market_source_url=AESO_MARKET_URL,
                    notes=(
                        "Regulated Rate Option energy charge -- varies "
                        "monthly based on AESO pool price"
                    ),
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Administration Fee",
                    charge_value=SEED_COMMERCIAL["admin_fee_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly administration fee",
                ),
            ],
        ))

        return records
