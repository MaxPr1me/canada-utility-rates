"""
fortisalberta.py -- Scraper for FortisAlberta distribution rates (Alberta).

FortisAlberta Inc. is a regulated electricity distribution utility serving
central and southern Alberta. It is the largest electricity distribution
provider in the province by service area.

Official source:
  https://www.fortisalberta.com/customer-service/rates-and-tariffs

Alberta has a deregulated electricity market -- distribution companies
charge regulated tariffs for wires service, while energy supply is
purchased separately from competitive retailers or the regulated rate
option (RRO). This scraper covers distribution charges only.

Regulated by the Alberta Utilities Commission (AUC).
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Seed data for FortisAlberta distribution rates.
SOURCE_URL = "https://www.fortisalberta.com/customer-service/rates-and-tariffs"
EFFECTIVE_DATE = "2024-01-01"

SEED_RESIDENTIAL = {
    "tariff_code": "D10",
    "basic_charge_per_day": 0.7854,   # $/day
    "distribution_rate": 0.0177,       # $/kWh
}

SEED_SMALL_COMMERCIAL = {
    "tariff_code": "D20",
    "basic_charge_per_day": 1.0264,   # $/day
    "distribution_rate": 0.0215,       # $/kWh
}

SEED_LARGE_COMMERCIAL = {
    "tariff_code": "D30",
    "basic_charge_per_day": 18.95,    # $/day
    "demand_charge": 4.8900,           # $/kW
    "distribution_rate": 0.0028,       # $/kWh
}


class FortisAlbertaScraper(BaseScraper):
    """Scrape FortisAlberta electricity distribution rates."""

    def __init__(self):
        super().__init__(utility_name="FortisAlberta", province="AB")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live FortisAlberta distribution rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d FortisAlberta tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed -- using seed data for FortisAlberta")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Verify every modelled component against the current official schedule."""
        return self.verify_official_records(SOURCE_URL, self._seed_data())

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # -- Residential (Rate D10) -------------------------------------------
        records.append(TariffRecord(
            utility_name="FortisAlberta",
            province="AB",
            utility_type="electricity",
            tariff_name="Residential Distribution (Rate D10)",
            tariff_code=SEED_RESIDENTIAL["tariff_code"],
            customer_class="residential",
            rate_structure="flat",
            effective_date=EFFECTIVE_DATE,
            source_url=SOURCE_URL,
            confidence="high",
            notes=(
                "Distribution charges only; energy supply from retailer. "
                "FortisAlberta serves central and southern Alberta. "
                "Regulated by the Alberta Utilities Commission (AUC)."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_day"],
                    charge_unit="$/day",
                    confidence="high",
                    notes="Daily fixed distribution charge",
                ),
                RateComponent(
                    component_type="distribution",
                    component_name="Distribution Charge",
                    charge_value=SEED_RESIDENTIAL["distribution_rate"],
                    charge_unit="$/kWh",
                    confidence="high",
                    notes="Variable distribution charge per kWh consumed",
                ),
            ],
        ))

        # -- Small Commercial (Rate D20) --------------------------------------
        records.append(TariffRecord(
            utility_name="FortisAlberta",
            province="AB",
            utility_type="electricity",
            tariff_name="Small General Service Distribution (Rate D20)",
            tariff_code=SEED_SMALL_COMMERCIAL["tariff_code"],
            customer_class="commercial",
            sub_class="small general service",
            rate_structure="flat",
            effective_date=EFFECTIVE_DATE,
            source_url=SOURCE_URL,
            confidence="high",
            eligibility="General service customers with demand under 150 kVA",
            demand_max_kw=150,
            notes=(
                "Distribution charges only; energy supply from retailer. "
                "Applies to commercial customers with demand below 150 kVA. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_SMALL_COMMERCIAL["basic_charge_per_day"],
                    charge_unit="$/day",
                    confidence="high",
                    notes="Daily fixed distribution charge",
                ),
                RateComponent(
                    component_type="distribution",
                    component_name="Distribution Charge",
                    charge_value=SEED_SMALL_COMMERCIAL["distribution_rate"],
                    charge_unit="$/kWh",
                    confidence="high",
                    notes="Variable distribution charge per kWh consumed",
                ),
            ],
        ))

        # -- Large Commercial (Rate D30) --------------------------------------
        records.append(TariffRecord(
            utility_name="FortisAlberta",
            province="AB",
            utility_type="electricity",
            tariff_name="Large General Service Distribution (Rate D30)",
            tariff_code=SEED_LARGE_COMMERCIAL["tariff_code"],
            customer_class="commercial",
            sub_class="large general service",
            rate_structure="demand",
            effective_date=EFFECTIVE_DATE,
            source_url=SOURCE_URL,
            confidence="high",
            eligibility="General service customers with demand of 150 kVA or greater",
            demand_min_kw=150,
            notes=(
                "Distribution charges only; energy supply from retailer. "
                "Demand-based tariff for large commercial customers. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_LARGE_COMMERCIAL["basic_charge_per_day"],
                    charge_unit="$/day",
                    confidence="high",
                    notes="Daily fixed distribution charge",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_LARGE_COMMERCIAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    confidence="high",
                    notes="Applied to billing demand (kW)",
                ),
                RateComponent(
                    component_type="distribution",
                    component_name="Distribution Charge",
                    charge_value=SEED_LARGE_COMMERCIAL["distribution_rate"],
                    charge_unit="$/kWh",
                    confidence="high",
                    notes="Variable distribution charge per kWh consumed",
                ),
            ],
        ))

        return records
