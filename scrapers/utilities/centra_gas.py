"""
centra_gas.py — Scraper for Centra Gas Manitoba rates.

Centra Gas Manitoba is a subsidiary of Manitoba Hydro and is the
primary natural gas distributor in Manitoba.

Official source:
  https://www.hydro.mb.ca/accounts-and-billing/rates/natural-gas-rates/

Manitoba gas rates are regulated by the Public Utilities Board of
Manitoba (PUB Manitoba).  Centra Gas uses m3 as the primary billing unit.
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Seed data based on PUB-approved rates.
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.hydro.mb.ca/accounts-and-billing/rates/natural-gas-rates/",
    "basic_charge_monthly": 14.00,              # $/month
    "primary_gas_rate": 0.1195,                 # $/m³ — primary gas supply
    "supplemental_gas_rate": 0.0320,            # $/m³ — supplemental gas/peaking
    "distribution_rate": 0.0775,                # $/m³ — distribution to customer
    "transportation_rate": 0.0292,              # $/m³ — upstream pipeline transport
    "cost_adjustment_rider": -0.0045,           # $/m³ — periodic adjustment
}


class CentraGasScraper(BaseScraper):
    """Scrape Centra Gas Manitoba natural gas rates."""

    def __init__(self):
        super().__init__(utility_name="Centra Gas Manitoba", province="MB")

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for Centra Gas Manitoba")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Verify every modelled component against the current official schedule."""
        return self.verify_official_records(SEED_RESIDENTIAL["source_url"], self._seed_data())

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Centra Gas Manitoba",
            province="MB",
            utility_type="gas",
            tariff_name="Residential — Small General Service",
            tariff_code="SGS",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "Centra Gas Manitoba residential rate (Small General Service). "
                "Centra Gas is a subsidiary of Manitoba Hydro. "
                "Primary gas rate is the main commodity cost; supplemental gas "
                "covers peaking supply. Rates in $/m3. "
                "Regulated by PUB Manitoba."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly customer charge",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Primary Gas Rate",
                    charge_value=SEED_RESIDENTIAL["primary_gas_rate"],
                    charge_unit="$/m³",
                    confidence="medium",
                    notes="Primary gas supply cost — largest commodity component",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Supplemental Gas Rate",
                    charge_value=SEED_RESIDENTIAL["supplemental_gas_rate"],
                    charge_unit="$/m³",
                    confidence="medium",
                    sub_component="supplemental",
                    notes="Supplemental gas for peaking supply and storage",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Distribution Charge",
                    charge_value=SEED_RESIDENTIAL["distribution_rate"],
                    charge_unit="$/m³",
                    confidence="medium",
                    notes="Centra Gas distribution charge for delivering gas to customer",
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Transportation to Centra",
                    charge_value=SEED_RESIDENTIAL["transportation_rate"],
                    charge_unit="$/m³",
                    confidence="medium",
                    notes="Upstream pipeline transportation to Centra Gas system",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Cost Adjustment Rider",
                    charge_value=SEED_RESIDENTIAL["cost_adjustment_rider"],
                    charge_unit="$/m³",
                    confidence="medium",
                    notes="Periodic gas cost adjustment — can be positive or negative",
                ),
            ],
        ))

        return records
