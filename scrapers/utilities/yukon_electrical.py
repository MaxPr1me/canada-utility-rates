"""
yukon_electrical.py — Scraper for Yukon Electrical Company electricity rates (Yukon).

Yukon Electrical Company Limited (YECL) is the primary electricity
distribution company in Yukon, owned by ATCO Ltd.  It purchases bulk
power from Yukon Energy Corporation and distributes it to residential,
commercial, and industrial customers throughout the territory.

YECL serves most populated areas of Yukon including Whitehorse,
Dawson City, Watson Lake, and other communities connected to the
main hydro grid as well as several diesel-served communities.

Rates are regulated by the Yukon Utilities Board and are closely
aligned with Yukon Energy's published rates, though distribution
charges differ slightly.

Official source:
  https://www.yukonelectrical.com/customer-service/rates
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# ── Seed / fallback rate data ─────────────────────────────────────
# Approximate published rates as of early 2025.

SEED_RESIDENTIAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.yukonelectrical.com/customer-service/rates",
    "tier1_threshold_kwh": 1000,   # per month
    "tier1_rate": 0.1326,          # $/kWh
    "tier2_rate": 0.1481,          # $/kWh (above 1000 kWh)
    "basic_charge_monthly": 20.34, # $/month
}

SEED_GENERAL_SERVICE = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.yukonelectrical.com/customer-service/rates",
    "energy_rate": 0.1326,         # $/kWh
    "demand_charge": 12.72,        # $/kW
    "basic_charge_monthly": 28.33, # $/month
}


class YukonElectricalScraper(BaseScraper):
    """Scrape Yukon Electrical Company electricity rates."""

    def __init__(self) -> None:
        super().__init__(utility_name="Yukon Electrical Company", province="YT")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Yukon Electrical rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records: list[TariffRecord] = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Yukon Electrical tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning(
                "Live scrape failed — using seed data for Yukon Electrical"
            )
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """
        Attempt to parse rates from the live Yukon Electrical website.

        Returns None until live parsing logic is implemented and verified.
        YECL (ATCO) publishes rates on their customer-service pages; the
        exact HTML structure needs manual verification before reliable
        automated parsing.
        """
        try:
            html = self.fetch_page(SEED_RESIDENTIAL["source_url"])
            if "rate" in html.lower():
                self.logger.info(
                    "Reached Yukon Electrical rate page — live parsing not yet implemented"
                )
            return None  # TODO: implement HTML parsing once structure is verified
        except Exception as e:
            self.logger.warning("Could not fetch Yukon Electrical page: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records: list[TariffRecord] = []

        # ── Residential (Tiered) ─────────────────────────────────
        records.append(TariffRecord(
            utility_name="Yukon Electrical Company",
            province="YT",
            utility_type="electricity",
            tariff_name="Residential Service",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "ATCO-owned distribution company serving most of Yukon. "
                "Residential rates use a two-tier structure: the first "
                "1,000 kWh per month at a lower rate, with consumption "
                "above that threshold billed at a higher rate. The basic "
                "monthly charge is slightly higher than Yukon Energy's "
                "direct rate, reflecting distribution costs."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Monthly customer charge — includes distribution costs",
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
            utility_name="Yukon Electrical Company",
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
                "customers served by Yukon Electrical. Includes energy "
                "charge and demand charge. Demand charge is somewhat "
                "lower than Yukon Energy's direct general service rate."
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

        return records
