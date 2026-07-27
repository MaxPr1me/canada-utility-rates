"""
yukon_energy.py — Scraper for Yukon Energy Corporation electricity rates (Yukon).

Yukon Energy is a Crown corporation that owns and operates most of the
electricity generation and transmission infrastructure in Yukon.  It
supplies wholesale power to Yukon Electrical Company (ATCO) for
distribution, but also sets end-use rates for some customers.

Most of Yukon's grid electricity comes from hydroelectric generation
(Whitehorse Rapids, Aishihik Lake, Mayo).  However, several remote
communities rely on diesel generation at significantly higher cost;
these "diesel communities" receive rate subsidies so that customers
pay comparable rates to grid-connected areas.

Regulated by the Yukon Utilities Board.

Official source:
  https://yukonenergy.ca/energy-in-yukon/electricity-rates
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# ── Seed / fallback rate data ─────────────────────────────────────
# Values below are approximate published rates as of early 2025.
# Yukon Energy and Yukon Electrical share a common residential rate
# structure set through the Yukon Utilities Board.

SEED_RESIDENTIAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://yukonenergy.ca/energy-in-yukon/electricity-rates",
    "tier1_threshold_kwh": 1000,   # per month
    "tier1_rate": 0.1326,          # $/kWh
    "tier2_rate": 0.1426,          # $/kWh (above 1000 kWh)
    "basic_charge_monthly": 17.50, # $/month
}

SEED_GENERAL_SERVICE = {
    "effective_date": "2024-04-01",
    "source_url": "https://yukonenergy.ca/energy-in-yukon/electricity-rates",
    "energy_rate": 0.1210,         # $/kWh
    "demand_charge": 15.40,        # $/kW
    "basic_charge_monthly": 25.00, # $/month
}

SEED_DIESEL_COMMUNITY = {
    "effective_date": "2024-04-01",
    "source_url": "https://yukonenergy.ca/energy-in-yukon/electricity-rates",
    "tier1_threshold_kwh": 1000,
    "tier1_rate": 0.1326,          # subsidised to match grid rate
    "tier2_rate": 0.1826,          # higher tail-block for diesel areas
    "basic_charge_monthly": 17.50,
}


class YukonEnergyScraper(BaseScraper):
    """Scrape Yukon Energy Corporation electricity rates."""

    def __init__(self) -> None:
        super().__init__(utility_name="Yukon Energy", province="YT")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Yukon Energy rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records: list[TariffRecord] = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Yukon Energy tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for Yukon Energy")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Verify every community/tier component against the official schedule."""
        return self.verify_official_records(SEED_RESIDENTIAL["source_url"], self._seed_data())

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records: list[TariffRecord] = []

        # ── Residential (Tiered) ─────────────────────────────────
        records.append(TariffRecord(
            utility_name="Yukon Energy",
            province="YT",
            utility_type="electricity",
            tariff_name="Residential Service",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "Yukon residential rate set jointly by Yukon Energy and "
                "Yukon Electrical through the Yukon Utilities Board. "
                "Tier 1 applies to the first 1,000 kWh per month; "
                "tier 2 applies to consumption above that threshold."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Monthly customer charge",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 1 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_RESIDENTIAL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes="First 1,000 kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_RESIDENTIAL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes="All kWh above 1,000 per month",
                ),
            ],
        ))

        # ── General Service ──────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Yukon Energy",
            province="YT",
            utility_type="electricity",
            tariff_name="General Service",
            customer_class="commercial",
            rate_structure="demand",
            effective_date=SEED_GENERAL_SERVICE["effective_date"],
            source_url=SEED_GENERAL_SERVICE["source_url"],
            confidence="medium",
            notes=(
                "General service rate for commercial and institutional "
                "customers. Includes energy charge and demand charge."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_GENERAL_SERVICE["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_GENERAL_SERVICE["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_GENERAL_SERVICE["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    confidence="medium",
                    notes="Billed on peak measured demand in the billing period",
                ),
            ],
        ))

        # ── Diesel Community Residential ─────────────────────────
        records.append(TariffRecord(
            utility_name="Yukon Energy",
            province="YT",
            utility_type="electricity",
            tariff_name="Residential Service — Diesel Communities",
            customer_class="residential",
            sub_class="diesel community",
            rate_structure="tiered",
            effective_date=SEED_DIESEL_COMMUNITY["effective_date"],
            source_url=SEED_DIESEL_COMMUNITY["source_url"],
            confidence="medium",
            notes=(
                "Several remote Yukon communities (e.g. Old Crow, Destruction Bay) "
                "are not connected to the main hydro grid and rely on diesel generation. "
                "The Yukon government subsidises diesel-community rates so that the "
                "first-tier price matches the hydro-grid rate; the second tier is "
                "somewhat higher to reflect the true cost of diesel generation."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_DIESEL_COMMUNITY["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 1 Energy Charge (Diesel Community)",
                    charge_value=SEED_DIESEL_COMMUNITY["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_DIESEL_COMMUNITY["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes="Subsidised to match hydro-grid rate for first 1,000 kWh/month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge (Diesel Community)",
                    charge_value=SEED_DIESEL_COMMUNITY["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_DIESEL_COMMUNITY["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes="Above 1,000 kWh/month — higher rate reflecting diesel costs",
                ),
            ],
        ))

        return records
