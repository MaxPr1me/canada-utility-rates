"""
saskenergy.py — Scraper for SaskEnergy natural gas rates (Saskatchewan).

SaskEnergy is Saskatchewan's Crown-owned natural gas distribution
utility, serving the entire province.

Official source:
  https://www.saskenergy.com/rates

Saskatchewan gas rates are regulated by the Saskatchewan Rate Review
Panel.  SaskEnergy uses m3 as the primary billing unit.
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Seed data based on Rate Review Panel-approved rates.
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.saskenergy.com/rates",
    "basic_charge_monthly": 23.50,              # $/month
    "commodity_rate": 0.2093,                   # $/m³ — gas commodity
    "delivery_rate": 0.0856,                    # $/m³ — delivery/distribution
    "carbon_charge": 0.1239,                    # $/m³ — federal carbon levy
    "rate_rider": 0.0035,                       # $/m³ — rate adjustment rider
}


class SaskEnergyScraper(BaseScraper):
    """Scrape SaskEnergy natural gas rates for Saskatchewan."""

    def __init__(self):
        super().__init__(utility_name="SaskEnergy", province="SK")

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for SaskEnergy")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Verify every modelled component against the current official schedule."""
        return self.verify_official_records(SEED_RESIDENTIAL["source_url"], self._seed_data())

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="SaskEnergy",
            province="SK",
            utility_type="gas",
            tariff_name="Residential",
            tariff_code="Res",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes=(
                "SaskEnergy residential natural gas rate. "
                "SaskEnergy is a Saskatchewan Crown corporation providing "
                "gas distribution across the entire province. "
                "Rates in $/m3. "
                "Regulated by the Saskatchewan Rate Review Panel."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="high",
                    notes="Fixed monthly customer charge",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Commodity Charge",
                    charge_value=SEED_RESIDENTIAL["commodity_rate"],
                    charge_unit="$/m³",
                    confidence="high",
                    notes="Natural gas commodity cost — largest volumetric component",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Delivery Charge",
                    charge_value=SEED_RESIDENTIAL["delivery_rate"],
                    charge_unit="$/m³",
                    confidence="high",
                    notes="SaskEnergy distribution charge for gas delivery",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_RESIDENTIAL["carbon_charge"],
                    charge_unit="$/m³",
                    confidence="high",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Rate Rider",
                    charge_value=SEED_RESIDENTIAL["rate_rider"],
                    charge_unit="$/m³",
                    confidence="high",
                    notes="Rate adjustment rider — periodic true-up",
                ),
            ],
        ))

        return records
