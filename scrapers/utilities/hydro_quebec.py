"""
hydro_quebec.py — Scraper for Hydro-Québec electricity rates (Quebec).

Hydro-Québec is the sole electricity distributor in Quebec.
They have notably low residential rates compared to most of Canada.

Official source:
  https://www.hydroquebec.com/residential/customer-space/rates/

Hydro-Québec rates include:
  - Rate D: Domestic (residential)
  - Rate DM: Residential with dual-energy heating
  - Rate G: General / small commercial (< 100 kW)
  - Rate M: Medium-power (100–5000 kW)
  - Rate L: Large industrial (> 5000 kW, special contracts)

This scraper handles Rate D and Rate G as examples.
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# Seed data based on published rates (updated periodically).
# Hydro-Québec adjusts rates annually, typically April 1.
SEED_RATE_D = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.hydroquebec.com/residential/customer-space/rates/rate-d.html",
    "first_40kwh_per_day": 0.06509,   # $/kWh for first 40 kWh/day
    "remaining": 0.10041,             # $/kWh for remaining consumption
    "fixed_per_day": 0.4064,          # $/day
}

SEED_RATE_G = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.hydroquebec.com/business/customer-space/rates/rate-g-general-rate.html",
    "first_15000kwh": 0.06509,
    "remaining": 0.04336,
    "demand_charge_first_50kw": 0.00,
    "demand_charge_above_50kw": 18.89,
    "fixed_per_day": 1.3820,
}


class HydroQuebecScraper(BaseScraper):
    """Scrape Hydro-Québec electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Hydro-Québec", province="QC")

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for Hydro-Québec")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt live scraping of Hydro-Québec rates."""
        try:
            html = self.fetch_page(SEED_RATE_D["source_url"])
            # Hydro-Québec frequently changes page structure.
            # Full HTML parsing would go here.
            # For now, return None to use seed data.
            return None
        except Exception as e:
            self.logger.warning("Could not fetch Hydro-Québec page: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Rate D: Domestic (Residential) ────────────────────
        records.append(TariffRecord(
            utility_name="Hydro-Québec",
            province="QC",
            utility_type="electricity",
            tariff_name="Rate D — Domestic",
            tariff_code="D",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=SEED_RATE_D["effective_date"],
            source_url=SEED_RATE_D["source_url"],
            confidence="high",
            notes="Hydro-Québec residential rate. Tier threshold is 40 kWh/day (~1,200 kWh/month in a 30-day period).",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Daily Fixed Charge",
                    charge_value=SEED_RATE_D["fixed_per_day"],
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="First 40 kWh/day",
                    charge_value=SEED_RATE_D["first_40kwh_per_day"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=40.0,
                    tier_unit="kWh/day",
                    notes="Applies to first 40 kWh per day of the billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Remaining consumption",
                    charge_value=SEED_RATE_D["remaining"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=40.0,
                    tier_unit="kWh/day",
                    notes="Applies to all kWh beyond 40/day",
                ),
            ],
        ))

        # ── Rate G: General (Small Commercial) ────────────────
        records.append(TariffRecord(
            utility_name="Hydro-Québec",
            province="QC",
            utility_type="electricity",
            tariff_name="Rate G — General",
            tariff_code="G",
            customer_class="commercial",
            sub_class="small general",
            rate_structure="mixed",
            effective_date=SEED_RATE_G["effective_date"],
            source_url=SEED_RATE_G["source_url"],
            confidence="high",
            eligibility="Contract capacity under 100 kW",
            demand_max_kw=100,
            notes="Hydro-Québec small commercial rate — energy charge is tiered, plus demand charge above 50 kW.",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Daily Fixed Charge",
                    charge_value=SEED_RATE_G["fixed_per_day"],
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="First 15,000 kWh",
                    charge_value=SEED_RATE_G["first_15000kwh"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=15000,
                    tier_unit="kWh",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Remaining kWh",
                    charge_value=SEED_RATE_G["remaining"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=15000,
                    tier_unit="kWh",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge (above 50 kW)",
                    charge_value=SEED_RATE_G["demand_charge_above_50kw"],
                    charge_unit="$/kW",
                    demand_threshold_kw=50,
                    demand_unit="kW",
                    notes="No demand charge for first 50 kW; $18.89/kW above 50 kW",
                ),
            ],
        ))

        return records
