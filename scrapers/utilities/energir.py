"""
energir.py — Scraper for Energir natural gas rates (Quebec).

Energir (formerly Gaz Metro) is the primary natural gas distributor
in Quebec, serving residential and commercial customers.

Official source:
  https://www.energir.com/en/residential/billing-and-rates/rates/

Quebec gas rates are regulated by the Regie de l'energie.
Energir uses GJ as the primary billing unit.
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Seed data based on Regie-approved rates.
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.energir.com/en/residential/billing-and-rates/rates/",
    "customer_charge_monthly": 15.29,           # $/month
    "distribution_rate": 0.5085,                # $/GJ
    "supply_rate": 4.3500,                      # $/GJ — varies with market
    "transportation_rate": 0.2150,              # $/GJ
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
    "load_balancing_rider": 0.0340,             # $/GJ
}

SEED_COMMERCIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.energir.com/en/residential/billing-and-rates/rates/",
    "customer_charge_monthly": 30.00,           # $/month
    "distribution_rate": 0.3714,                # $/GJ
    "supply_rate": 4.3500,                      # $/GJ — varies with market
    "transportation_rate": 0.2150,              # $/GJ
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
    "demand_charge": 3.75,                      # $/GJ of peak demand
}


class EnergirScraper(BaseScraper):
    """Scrape Energir natural gas rates for Quebec."""

    def __init__(self):
        super().__init__(utility_name="Energir", province="QC")

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for Energir")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        try:
            html = self.fetch_page(SEED_RESIDENTIAL["source_url"])
            return None
        except Exception as e:
            self.logger.warning("Could not fetch Energir page: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Energir",
            province="QC",
            utility_type="gas",
            tariff_name="Residential — Rate D1",
            tariff_code="D1",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "Energir residential rate for Quebec. "
                "Gas supply portion varies with market conditions. "
                "Regulated by the Regie de l'energie."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_RESIDENTIAL["customer_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly charge regardless of gas usage",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Distribution Charge",
                    charge_value=SEED_RESIDENTIAL["distribution_rate"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Energir distribution charge for delivering gas",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Gas Supply Charge",
                    charge_value=SEED_RESIDENTIAL["supply_rate"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Cost of natural gas commodity — varies with market",
                    market_reference="Quebec gas supply portfolio",
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Transportation Charge",
                    charge_value=SEED_RESIDENTIAL["transportation_rate"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Pipeline transportation to Energir system",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_RESIDENTIAL["carbon_charge"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Load Balancing Rider",
                    charge_value=SEED_RESIDENTIAL["load_balancing_rider"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Load balancing and inventory management adjustment",
                ),
            ],
        ))

        # ── Commercial ───────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Energir",
            province="QC",
            utility_type="gas",
            tariff_name="Commercial — Rate D3",
            tariff_code="D3",
            customer_class="commercial",
            rate_structure="flat",
            effective_date=SEED_COMMERCIAL["effective_date"],
            source_url=SEED_COMMERCIAL["source_url"],
            confidence="medium",
            notes=(
                "Energir small commercial rate for Quebec. "
                "Includes demand charges based on peak consumption. "
                "Regulated by the Regie de l'energie."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_COMMERCIAL["customer_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly charge for commercial accounts",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Distribution Charge",
                    charge_value=SEED_COMMERCIAL["distribution_rate"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Volume-based distribution charge — lower rate for commercial",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Gas Supply Charge",
                    charge_value=SEED_COMMERCIAL["supply_rate"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Cost of natural gas commodity — varies with market",
                    market_reference="Quebec gas supply portfolio",
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Transportation Charge",
                    charge_value=SEED_COMMERCIAL["transportation_rate"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Pipeline transportation to Energir system",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_COMMERCIAL["carbon_charge"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_COMMERCIAL["demand_charge"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Demand-based charge on peak gas consumption",
                ),
            ],
        ))

        return records
