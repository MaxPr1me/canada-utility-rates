"""
qulliq.py — Scraper for Qulliq Energy Corporation electricity rates (Nunavut).

Qulliq Energy Corporation (QEC) is the sole electricity provider in
Nunavut.  Every single community in the territory relies on diesel
generation — there is no hydroelectric, natural gas, or grid
interconnection.  This makes Nunavut the most expensive jurisdiction
for electricity in all of Canada.

Fuel must be shipped by barge during the short summer sealift season
or flown in at extreme cost during winter.  Published tariff rates
are very high (residential tail-block above $0.50/kWh, commercial
above $0.70/kWh), but the Government of Nunavut provides substantial
subsidies through the Territorial Power Support Program to reduce the
effective cost for residential customers and some businesses.

Without the subsidy, many residents would face monthly electricity
bills exceeding $1,000 even for modest consumption.

Regulated by the Utility Rates Review Council (URRC) of Nunavut.

Official source:
  https://www.qec.nu.ca/customer-care/accounts-billing/rates
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# ── Seed / fallback rate data ─────────────────────────────────────
# Approximate published rates as of early 2025.
# QEC sets uniform rates across Nunavut — all communities are diesel.
# Actual effective rates are much lower for subsidised customers.

SEED_RESIDENTIAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.qec.nu.ca/customer-care/accounts-billing/rates",
    "tier1_threshold_kwh": 1000,    # per month
    "tier1_rate": 0.3600,           # $/kWh
    "tier2_rate": 0.5400,           # $/kWh (above 1000 kWh)
    "basic_charge_monthly": 10.00,  # $/month
    # Territorial Power Support Program subsidy — approximate reduction
    "subsidy_per_kwh": 0.20,        # approximate average rebate $/kWh
}

SEED_COMMERCIAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.qec.nu.ca/customer-care/accounts-billing/rates",
    "energy_rate": 0.7200,          # $/kWh — flat rate for commercial
    "basic_charge_monthly": 50.00,  # $/month
}


class QulliqScraper(BaseScraper):
    """Scrape Qulliq Energy Corporation electricity rates."""

    def __init__(self) -> None:
        super().__init__(utility_name="Qulliq Energy Corporation", province="NU")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Qulliq Energy rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records: list[TariffRecord] = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Qulliq Energy tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning(
                "Live scrape failed — using seed data for Qulliq Energy"
            )
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Verify every community/tier component against the official schedule."""
        return self.verify_official_records(SEED_RESIDENTIAL["source_url"], self._seed_data())

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records: list[TariffRecord] = []

        # ── Residential (Tiered, with subsidy component) ─────────
        records.append(TariffRecord(
            utility_name="Qulliq Energy Corporation",
            province="NU",
            utility_type="electricity",
            tariff_name="Residential Service",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="low",
            notes=(
                "All Nunavut electricity is diesel-generated — the most "
                "expensive in Canada. Published tariff rates are very high "
                "but the Government of Nunavut Territorial Power Support "
                "Program provides a substantial per-kWh rebate that "
                "significantly reduces the effective cost for residential "
                "customers. The subsidy amount varies by community and is "
                "subject to change; the rebate component below is an "
                "approximate average. Actual effective rates after subsidy "
                "are roughly comparable to NWT hydro-zone rates."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="low",
                    notes="Monthly customer charge — relatively low given overall rate levels",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 1 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_RESIDENTIAL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="low",
                    notes="First 1,000 kWh per month — before subsidy",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_RESIDENTIAL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="low",
                    notes="All kWh above 1,000 per month — before subsidy",
                ),
                RateComponent(
                    component_type="rebate",
                    component_name="Territorial Power Support Program Subsidy",
                    charge_value=-SEED_RESIDENTIAL["subsidy_per_kwh"],
                    charge_unit="$/kWh",
                    confidence="low",
                    notes=(
                        "Approximate per-kWh rebate from the Government of "
                        "Nunavut Territorial Power Support Program. The "
                        "actual subsidy varies by community, consumption "
                        "level, and government policy. This value is a rough "
                        "territory-wide average. The negative value indicates "
                        "a credit reducing the customer's bill."
                    ),
                ),
            ],
        ))

        # ── Commercial ───────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Qulliq Energy Corporation",
            province="NU",
            utility_type="electricity",
            tariff_name="Commercial Service",
            customer_class="commercial",
            rate_structure="flat",
            effective_date=SEED_COMMERCIAL["effective_date"],
            source_url=SEED_COMMERCIAL["source_url"],
            confidence="low",
            notes=(
                "Commercial rate for businesses in Nunavut. All communities "
                "use diesel generation. Commercial customers typically do "
                "not receive the same level of territorial subsidy as "
                "residential customers, resulting in very high effective "
                "electricity costs. Some government and institutional "
                "customers may have negotiated rates."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_COMMERCIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="low",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_COMMERCIAL["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="low",
                    notes=(
                        "Flat commercial energy rate — among the highest "
                        "in Canada, reflecting full diesel generation cost"
                    ),
                ),
            ],
        ))

        return records
