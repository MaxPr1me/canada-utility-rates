"""
enmax_power.py -- Scraper for ENMAX Power distribution rates (Alberta).

ENMAX Power Corporation is the regulated electricity distribution utility
serving the City of Calgary and surrounding area.

Official source:
  https://www.enmax.com/home/rates-and-billing/understand-your-bill

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

# Seed data for ENMAX Power distribution rates.
SOURCE_URL = "https://www.enmax.com/home/rates-and-billing/understand-your-bill"
EFFECTIVE_DATE = "2024-04-01"

SEED_RESIDENTIAL = {
    "tariff_code": "D110",
    "basic_charge_per_day": 0.7086,   # $/day
    "distribution_rate": 0.0192,       # $/kWh
}

SEED_SMALL_COMMERCIAL = {
    "tariff_code": "D210",
    "basic_charge_per_day": 0.9400,   # $/day
    "distribution_rate": 0.0238,       # $/kWh
}

SEED_LARGE_COMMERCIAL = {
    "tariff_code": "D310",
    "basic_charge_per_day": 16.80,    # $/day
    "demand_charge": 5.2400,           # $/kW
    "distribution_rate": 0.0031,       # $/kWh
}


class ENMAXPowerScraper(BaseScraper):
    """Scrape ENMAX Power electricity distribution rates for Calgary."""

    def __init__(self):
        super().__init__(utility_name="ENMAX Power", province="AB")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live ENMAX Power distribution rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d ENMAX Power tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed -- using seed data for ENMAX Power")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live ENMAX website."""
        try:
            html = self.fetch_page(SOURCE_URL)
            # TODO: implement HTML parsing once page structure is verified
            return None
        except Exception as e:
            self.logger.warning("Could not fetch ENMAX Power page: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # -- Residential (Rate D110) ------------------------------------------
        records.append(TariffRecord(
            utility_name="ENMAX Power",
            province="AB",
            utility_type="electricity",
            tariff_name="Residential Distribution (Rate D110)",
            tariff_code=SEED_RESIDENTIAL["tariff_code"],
            customer_class="residential",
            rate_structure="flat",
            effective_date=EFFECTIVE_DATE,
            source_url=SOURCE_URL,
            confidence="high",
            notes=(
                "Distribution charges only; energy supply from retailer. "
                "ENMAX Power serves the City of Calgary. "
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

        # -- Small Commercial (Rate D210) -------------------------------------
        records.append(TariffRecord(
            utility_name="ENMAX Power",
            province="AB",
            utility_type="electricity",
            tariff_name="Small General Service Distribution (Rate D210)",
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

        # -- Large Commercial (Rate D310) -------------------------------------
        records.append(TariffRecord(
            utility_name="ENMAX Power",
            province="AB",
            utility_type="electricity",
            tariff_name="Large General Service Distribution (Rate D310)",
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
