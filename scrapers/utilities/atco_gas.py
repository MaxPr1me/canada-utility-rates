"""
atco_gas.py — Scraper for ATCO Gas distribution rates (Alberta).

ATCO Gas is one of Alberta's major natural gas distributors, serving
the southern and northern regions of the province.

Official source:
  https://www.atco.com/en-ca/for-home/natural-gas/natural-gas-rates.html

Alberta has a deregulated gas market — ATCO provides distribution
only, while gas supply is purchased from a competitive retailer or
the regulated default supply.  This scraper covers distribution
charges for both the North and South service territories.

Regulated by the Alberta Utilities Commission (AUC).
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Seed data for ATCO Gas South distribution.
SEED_SOUTH = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.atco.com/en-ca/for-home/natural-gas/natural-gas-rates.html",
    "customer_charge_monthly": 34.14,           # $/month
    "variable_distribution": 1.3419,            # $/GJ
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
    "municipal_franchise_fee_pct": 0.0,         # varies by municipality — not included
    "rate_rider": 0.0480,                       # $/GJ — AUC-approved rider
}

# Seed data for ATCO Gas North distribution.
SEED_NORTH = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.atco.com/en-ca/for-home/natural-gas/natural-gas-rates.html",
    "customer_charge_monthly": 37.00,           # $/month
    "variable_distribution": 1.4589,            # $/GJ
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
    "rate_rider": 0.0520,                       # $/GJ — AUC-approved rider
}


class ATCOGasScraper(BaseScraper):
    """Scrape ATCO Gas distribution rates for Alberta (North and South)."""

    def __init__(self):
        super().__init__(utility_name="ATCO Gas", province="AB")

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for ATCO Gas")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Verify every modelled component against the current official schedule."""
        return self.verify_official_records(SEED_SOUTH["source_url"], self._seed_data())

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential — South service territory ────────────────
        records.append(TariffRecord(
            utility_name="ATCO Gas",
            province="AB",
            utility_type="gas",
            tariff_name="Residential Distribution — South",
            tariff_code="D-South",
            customer_class="residential",
            sub_class="South",
            rate_structure="flat",
            effective_date=SEED_SOUTH["effective_date"],
            source_url=SEED_SOUTH["source_url"],
            confidence="medium",
            notes=(
                "ATCO Gas distribution charges for southern Alberta. "
                "Alberta is deregulated — gas supply must be purchased separately "
                "from a retailer or default supply provider. "
                "Municipal franchise fees vary by city and are not included. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_SOUTH["customer_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly distribution charge",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Variable Distribution Charge",
                    charge_value=SEED_SOUTH["variable_distribution"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Volume-based distribution charge for gas delivery",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_SOUTH["carbon_charge"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="AUC Rate Rider",
                    charge_value=SEED_SOUTH["rate_rider"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="AUC-approved rate adjustment rider",
                ),
            ],
        ))

        # ── Residential — North service territory ────────────────
        records.append(TariffRecord(
            utility_name="ATCO Gas",
            province="AB",
            utility_type="gas",
            tariff_name="Residential Distribution — North",
            tariff_code="D-North",
            customer_class="residential",
            sub_class="North",
            rate_structure="flat",
            effective_date=SEED_NORTH["effective_date"],
            source_url=SEED_NORTH["source_url"],
            confidence="medium",
            notes=(
                "ATCO Gas distribution charges for northern Alberta. "
                "Higher costs than South territory due to longer distribution lines "
                "and lower customer density. "
                "Gas supply must be purchased separately from a retailer. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_NORTH["customer_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly distribution charge — higher than South",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Variable Distribution Charge",
                    charge_value=SEED_NORTH["variable_distribution"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Volume-based distribution charge — higher than South territory",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_NORTH["carbon_charge"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="AUC Rate Rider",
                    charge_value=SEED_NORTH["rate_rider"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="AUC-approved rate adjustment rider",
                ),
            ],
        ))

        return records
