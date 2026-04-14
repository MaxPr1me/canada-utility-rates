"""
ntpc.py — Scraper for Northwest Territories Power Corporation electricity rates (NT).

The Northwest Territories Power Corporation (NTPC) is a Crown
corporation that generates and distributes electricity across the
Northwest Territories.  NTPC operates in multiple rate zones that
reflect the dramatically different generation costs across this vast
territory:

  - **Hydro zones** (Yellowknife, Hay River, and surrounding areas)
    use hydroelectric generation from the Snare and Taltson river
    systems.  Rates here are lower but still well above southern
    Canadian averages.

  - **Thermal / diesel zones** (most smaller communities) rely on
    trucked-in diesel fuel for generation.  These communities have
    some of the highest electricity rates in Canada, with tail-block
    rates exceeding $1.00/kWh.

The NWT government operates a Territorial Power Support Program (TPSP)
that subsidises residential electricity costs in high-cost communities,
effectively equalising the first block of residential consumption
across zones.

Regulated by the Public Utilities Board of the Northwest Territories
(PUB NWT).

Official source:
  https://www.ntpc.com/customer-service/residential-service/current-rates
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

# ── Seed / fallback rate data ─────────────────────────────────────
# Approximate published rates as of early 2025.
# NTPC has many rate zones; we capture Yellowknife (hydro) and a
# representative diesel community zone here.

SEED_RESIDENTIAL_YELLOWKNIFE = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.ntpc.com/customer-service/residential-service/current-rates",
    "tier1_threshold_kwh": 1000,   # per month
    "tier1_rate": 0.3244,          # $/kWh
    "tier2_rate": 0.5967,          # $/kWh
    "basic_charge_monthly": 16.28, # $/month
}

SEED_RESIDENTIAL_DIESEL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.ntpc.com/customer-service/residential-service/current-rates",
    "tier1_threshold_kwh": 600,    # lower threshold in diesel zones
    "tier1_rate": 0.3022,          # $/kWh (subsidised first block)
    "tier2_rate": 1.0181,          # $/kWh — true diesel cost
    "basic_charge_monthly": 16.28, # $/month
}

SEED_GENERAL_SERVICE_YELLOWKNIFE = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.ntpc.com/customer-service/residential-service/current-rates",
    "energy_rate": 0.3244,         # $/kWh
    "demand_charge": 5.30,         # $/kW
    "basic_charge_monthly": 28.00, # $/month
}


class NTPCScraper(BaseScraper):
    """Scrape Northwest Territories Power Corporation electricity rates."""

    def __init__(self) -> None:
        super().__init__(
            utility_name="Northwest Territories Power Corporation",
            province="NT",
        )

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live NTPC rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records: list[TariffRecord] = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d NTPC tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for NTPC")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """
        Attempt to parse rates from the live NTPC website.

        Returns None until live parsing logic is implemented and verified.
        NTPC publishes rates in a tabular format on their website, but
        the multi-zone structure makes automated parsing complex and
        requires manual verification of the HTML structure.
        """
        try:
            html = self.fetch_page(SEED_RESIDENTIAL_YELLOWKNIFE["source_url"])
            if "rate" in html.lower():
                self.logger.info(
                    "Reached NTPC rate page — live parsing not yet implemented"
                )
            return None  # TODO: implement HTML parsing once structure is verified
        except Exception as e:
            self.logger.warning("Could not fetch NTPC page: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records: list[TariffRecord] = []

        # ── Residential — Yellowknife Zone (Hydro) ───────────────
        records.append(TariffRecord(
            utility_name="Northwest Territories Power Corporation",
            province="NT",
            utility_type="electricity",
            tariff_name="Residential Service — Yellowknife Zone",
            customer_class="residential",
            sub_class="yellowknife zone",
            rate_structure="tiered",
            effective_date=SEED_RESIDENTIAL_YELLOWKNIFE["effective_date"],
            source_url=SEED_RESIDENTIAL_YELLOWKNIFE["source_url"],
            confidence="medium",
            notes=(
                "Yellowknife zone is served primarily by hydro generation "
                "(Snare River system). Rates are the lowest in the NWT but "
                "still significantly higher than southern Canada — roughly "
                "3x the national average. Tier 1 covers the first 1,000 kWh "
                "per month; tier 2 applies above that threshold."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_RESIDENTIAL_YELLOWKNIFE["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Monthly customer charge",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 1 Energy Charge",
                    charge_value=SEED_RESIDENTIAL_YELLOWKNIFE["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_RESIDENTIAL_YELLOWKNIFE["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes="First 1,000 kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge",
                    charge_value=SEED_RESIDENTIAL_YELLOWKNIFE["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_RESIDENTIAL_YELLOWKNIFE["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes="All kWh above 1,000 per month",
                ),
            ],
        ))

        # ── Residential — Diesel Zone ────────────────────────────
        records.append(TariffRecord(
            utility_name="Northwest Territories Power Corporation",
            province="NT",
            utility_type="electricity",
            tariff_name="Residential Service — Diesel Zone",
            customer_class="residential",
            sub_class="diesel zone",
            rate_structure="tiered",
            effective_date=SEED_RESIDENTIAL_DIESEL["effective_date"],
            source_url=SEED_RESIDENTIAL_DIESEL["source_url"],
            confidence="medium",
            notes=(
                "Diesel zone communities (e.g. Tuktoyaktuk, Sachs Harbour, "
                "Paulatuk) rely entirely on trucked-in diesel for electricity "
                "generation. The tail-block rate exceeds $1.00/kWh, making "
                "this among the most expensive electricity in Canada. The "
                "NWT Territorial Power Support Program subsidises the first "
                "block for residential customers to bring it closer to the "
                "Yellowknife hydro rate. Tier 1 threshold is lower at 600 kWh."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_RESIDENTIAL_DIESEL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 1 Energy Charge (Diesel Zone)",
                    charge_value=SEED_RESIDENTIAL_DIESEL["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_RESIDENTIAL_DIESEL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes=(
                        "First 600 kWh per month — subsidised through "
                        "Territorial Power Support Program"
                    ),
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge (Diesel Zone)",
                    charge_value=SEED_RESIDENTIAL_DIESEL["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_RESIDENTIAL_DIESEL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes=(
                        "Above 600 kWh/month — reflects true cost of "
                        "diesel generation in remote communities"
                    ),
                ),
            ],
        ))

        # ── General Service — Yellowknife Zone ───────────────────
        records.append(TariffRecord(
            utility_name="Northwest Territories Power Corporation",
            province="NT",
            utility_type="electricity",
            tariff_name="General Service — Yellowknife Zone",
            customer_class="commercial",
            sub_class="yellowknife zone",
            rate_structure="demand",
            effective_date=SEED_GENERAL_SERVICE_YELLOWKNIFE["effective_date"],
            source_url=SEED_GENERAL_SERVICE_YELLOWKNIFE["source_url"],
            confidence="medium",
            notes=(
                "Commercial general service rate for the Yellowknife hydro "
                "zone. Includes energy and demand components. Commercial "
                "rates in diesel communities are significantly higher."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_GENERAL_SERVICE_YELLOWKNIFE["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_GENERAL_SERVICE_YELLOWKNIFE["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_GENERAL_SERVICE_YELLOWKNIFE["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    confidence="medium",
                    notes="Billed on peak measured demand in the billing period",
                ),
            ],
        ))

        return records
