"""
atco_electric.py -- Scraper for ATCO Electric distribution rates (Alberta).

ATCO Electric Ltd. is a regulated electricity distribution utility serving
rural and northern Alberta. It operates under the Alberta Utilities
Commission (AUC).

Official source:
  https://www.atco.com/en-ca/for-home/electricity/understand-your-bill.html

Alberta has a deregulated electricity market -- distribution companies
charge regulated tariffs for wires service, while energy supply is
purchased separately from competitive retailers or the regulated rate
option (RRO). This scraper covers distribution charges only.
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Seed data for ATCO Electric distribution rates.
SOURCE_URL = "https://www.atco.com/en-ca/for-home/electricity/understand-your-bill.html"
EFFECTIVE_DATE = "2024-01-01"

SEED_RESIDENTIAL = {
    "tariff_code": "D11",
    "basic_charge_per_day": 0.8186,   # $/day
    "distribution_rate": 0.0204,       # $/kWh
}

SEED_SMALL_COMMERCIAL = {
    "tariff_code": "D21",
    "basic_charge_per_day": 0.9754,   # $/day
    "distribution_rate": 0.0260,       # $/kWh
}

SEED_LARGE_COMMERCIAL = {
    "tariff_code": "D31",
    "basic_charge_per_day": 17.58,    # $/day
    "demand_charge": 5.4720,           # $/kW
    "distribution_rate": 0.0032,       # $/kWh
}


class ATCOElectricScraper(BaseScraper):
    """Scrape ATCO Electric distribution rates for Alberta."""

    def __init__(self):
        super().__init__(utility_name="ATCO Electric", province="AB")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live ATCO Electric distribution rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d ATCO Electric tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed -- using seed data for ATCO Electric")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live ATCO Electric website."""
        try:
            html = self.fetch_page(SOURCE_URL)
            # TODO: implement HTML parsing once page structure is verified
            return None
        except Exception as e:
            self.logger.warning("Could not fetch ATCO Electric page: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # -- Residential (Rate D11) -------------------------------------------
        records.append(TariffRecord(
            utility_name="ATCO Electric",
            province="AB",
            utility_type="electricity",
            tariff_name="Residential Distribution (Rate D11)",
            tariff_code=SEED_RESIDENTIAL["tariff_code"],
            customer_class="residential",
            rate_structure="flat",
            effective_date=EFFECTIVE_DATE,
            source_url=SOURCE_URL,
            confidence="high",
            notes=(
                "Distribution charges only; energy supply from retailer. "
                "ATCO Electric serves rural and northern Alberta. "
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

        # -- Small Commercial (Rate D21) --------------------------------------
        records.append(TariffRecord(
            utility_name="ATCO Electric",
            province="AB",
            utility_type="electricity",
            tariff_name="Small General Service Distribution (Rate D21)",
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

        # -- Large Commercial (Rate D31) --------------------------------------
        records.append(TariffRecord(
            utility_name="ATCO Electric",
            province="AB",
            utility_type="electricity",
            tariff_name="Large General Service Distribution (Rate D31)",
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
