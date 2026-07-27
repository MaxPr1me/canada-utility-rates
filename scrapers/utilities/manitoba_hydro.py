"""
manitoba_hydro.py — Scraper for Manitoba Hydro electricity rates (Manitoba).

Manitoba Hydro is the sole electricity and natural gas utility in Manitoba.
Manitoba benefits from abundant hydroelectric generation, resulting in some
of the lowest electricity rates in Canada.

Official sources:
  Residential: https://www.hydro.mb.ca/accounts_and_services/rates/residential_rates/
  Commercial:  https://www.hydro.mb.ca/accounts_and_services/rates/commercial_rates/

Regulated by: Public Utilities Board of Manitoba (PUB Manitoba)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import extract_tables, clean_currency, detect_js_rendered
from scrapers.utils.change_detection import compare_to_seed, log_change_alerts, has_critical_alerts

logger = logging.getLogger(__name__)

# ── URLs ──────────────────────────────────────────────────────────
RESIDENTIAL_URL = "https://www.hydro.mb.ca/accounts_and_services/rates/residential_rates/"
COMMERCIAL_URL = "https://www.hydro.mb.ca/accounts_and_services/rates/commercial_rates/"

# ── Seed / fallback data (updated to January 1, 2026 published rates) ──

SEED_RESIDENTIAL = {
    "effective_date": "2026-01-01",
    "source_url": RESIDENTIAL_URL,
    "energy_rate": 0.09970,          # $/kWh — flat rate (9.970¢/kWh)
    "basic_charge_per_month": 9.84,  # $/month (≤200 Amp service)
}

SEED_GENERAL_SERVICE_SMALL = {
    "effective_date": "2026-01-01",
    "source_url": COMMERCIAL_URL,
    "energy_rate_tier1": 0.09864,      # $/kWh — first 11,000 kWh (9.864¢/kWh)
    "energy_rate_tier2": 0.07568,      # $/kWh — balance (7.568¢/kWh)
    "tier1_threshold_kwh": 11000,      # kWh
    "basic_charge_per_month": 21.57,   # $/month (single-phase)
}

SEED_GENERAL_SERVICE_MEDIUM = {
    "effective_date": "2026-01-01",
    "source_url": COMMERCIAL_URL,
    "energy_rate_tier1": 0.09120,      # $/kWh — first 19,500 kWh (9.120¢/kWh)
    "energy_rate_tier2": 0.04728,      # $/kWh — balance (4.728¢/kWh)
    "tier1_threshold_kwh": 19500,      # kWh
    "demand_charge": 12.39,            # $/kVA (first 50 kVA no charge, balance)
    "demand_free_kva": 50,             # first 50 kVA at no charge
    "basic_charge_per_month": 35.81,   # $/month
}


class ManitobaHydroScraper(BaseScraper):
    """Scrape Manitoba Hydro electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Manitoba Hydro", province="MB")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Manitoba Hydro rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Manitoba Hydro tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for Manitoba Hydro")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    # ── Live scraping ────────────────────────────────────────────

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live Manitoba Hydro website."""
        try:
            # Fetch both rate pages
            residential_html = self.fetch_page(RESIDENTIAL_URL)
            commercial_html = self.fetch_page(COMMERCIAL_URL)

            # Check if pages are JS-rendered (would need a headless browser)
            if detect_js_rendered(residential_html):
                self.logger.warning("Residential page appears JS-rendered — cannot parse")
                return None
            if detect_js_rendered(commercial_html):
                self.logger.warning("Commercial page appears JS-rendered — cannot parse")
                return None

            # Parse each page
            residential_records = self._parse_residential(residential_html)
            commercial_records = self._parse_commercial(commercial_html)

            if not residential_records and not commercial_records:
                self.logger.warning("Could not parse any tariffs from live pages")
                return None

            live_records = residential_records + commercial_records

            # Compare to seed data for sanity checking
            seed_records = self._seed_data()
            alerts = compare_to_seed(live_records, seed_records)
            log_change_alerts(alerts)

            if has_critical_alerts(alerts):
                self.logger.error(
                    "Critical deviations from seed data — likely a parsing error. "
                    "Falling back to seed data."
                )
                return None

            return live_records

        except Exception as e:
            self.logger.warning("Live scrape failed for Manitoba Hydro: %s", e)
            return None

    def _parse_residential(self, html: str) -> list[TariffRecord]:
        """Parse residential rates from the Manitoba Hydro residential rates page."""
        tables = extract_tables(html)
        if not tables:
            self.logger.warning("No tables found on residential page")
            return []

        basic_charge: Optional[float] = None
        energy_rate: Optional[float] = None

        for table in tables:
            for row in table:
                if len(row) < 2:
                    continue
                charge_text = row[0].lower()
                cost_text = row[-1]

                # Basic monthly charge (≤200 Amp standard service)
                if "basic monthly" in charge_text and "200" in charge_text and ">" not in charge_text:
                    val = clean_currency(cost_text)
                    if val is not None:
                        basic_charge = val

                # Energy charge — look for "energy" or "kwh" in charge column
                if ("energy" in charge_text or "kwh" in charge_text) and "demand" not in charge_text:
                    val = clean_currency(cost_text)
                    if val is not None:
                        energy_rate = val

        if basic_charge is None or energy_rate is None:
            self.logger.warning(
                "Could not extract all residential values (basic=%s, energy=%s)",
                basic_charge, energy_rate,
            )
            return []

        record = TariffRecord(
            utility_name="Manitoba Hydro",
            province="MB",
            utility_type="electricity",
            tariff_name="Residential Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=RESIDENTIAL_URL,
            confidence="high",
            notes=(
                "Manitoba Hydro flat residential rate. "
                "Among the lowest electricity rates in Canada due to abundant hydroelectric generation."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=basic_charge,
                    charge_unit="$/month",
                    notes="Monthly basic charge regardless of consumption (≤200 Amp service)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=energy_rate,
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        )
        return [record]

    def _parse_commercial(self, html: str) -> list[TariffRecord]:
        """Parse commercial rates from the Manitoba Hydro commercial rates page."""
        tables = extract_tables(html)
        if not tables:
            self.logger.warning("No tables found on commercial page")
            return []

        records = []

        # ── GS Small Non-Demand ──────────────────────────────────
        gs_small = self._parse_gs_small(tables)
        if gs_small:
            records.append(gs_small)

        # ── GS Medium (Demand) ───────────────────────────────────
        gs_medium = self._parse_gs_medium(tables)
        if gs_medium:
            records.append(gs_medium)

        return records

    def _parse_gs_small(self, tables: list[list[list[str]]]) -> Optional[TariffRecord]:
        """Parse GS Small Non-Demand rates from commercial page tables."""
        basic_charge: Optional[float] = None
        energy_tier1: Optional[float] = None
        energy_tier2: Optional[float] = None
        tier1_threshold: Optional[float] = None

        # Search tables for GS Small Non-Demand data
        # The page has separate sections/tables for each rate class
        in_gs_small_section = False

        for table in tables:
            for row in table:
                if not row:
                    continue
                row_text = " ".join(row).lower()

                # Detect section headers — GS Small Non-Demand
                if "non-demand" in row_text or ("small" in row_text and "non" in row_text):
                    in_gs_small_section = True
                # If we hit a different section header, stop
                elif in_gs_small_section and (
                    ("medium" in row_text and "general" in row_text)
                    or ("large" in row_text and "general" in row_text)
                    or "demand" in row_text and "non" not in row_text and "small" not in row_text
                ):
                    # Check if this looks like a section header (not a data row with "demand" in it)
                    if len(row) <= 2 or not any(
                        "¢" in cell or "$" in cell for cell in row
                    ):
                        in_gs_small_section = False

                if not in_gs_small_section:
                    continue

                if len(row) < 2:
                    continue

                charge_text = row[0].lower()
                cost_text = row[-1]

                # Basic charge (single-phase)
                if "basic" in charge_text and "single" in charge_text:
                    val = clean_currency(cost_text)
                    if val is not None:
                        basic_charge = val

                # Energy tiers
                if "first" in charge_text and "kwh" in charge_text:
                    val = clean_currency(cost_text)
                    if val is not None:
                        energy_tier1 = val
                        # Extract threshold (e.g. "First 11,000 kWh")
                        threshold_match = re.search(r"(\d[\d,]*)\s*kwh", charge_text)
                        if threshold_match:
                            tier1_threshold = float(threshold_match.group(1).replace(",", ""))

                if "balance" in charge_text and "kwh" in charge_text:
                    val = clean_currency(cost_text)
                    if val is not None:
                        energy_tier2 = val

        if basic_charge is None or energy_tier1 is None or energy_tier2 is None:
            self.logger.warning(
                "Could not extract all GS Small values (basic=%s, tier1=%s, tier2=%s)",
                basic_charge, energy_tier1, energy_tier2,
            )
            return None

        return TariffRecord(
            utility_name="Manitoba Hydro",
            province="MB",
            utility_type="electricity",
            tariff_name="General Service Small (Non-Demand)",
            customer_class="commercial",
            sub_class="general service small",
            rate_structure="tiered",
            effective_date=SEED_GENERAL_SERVICE_SMALL["effective_date"],
            source_url=COMMERCIAL_URL,
            confidence="high",
            eligibility="Non-demand metered commercial customers (≤50 kVA)",
            notes="Small commercial accounts without demand metering",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=basic_charge,
                    charge_unit="$/month",
                    notes="Monthly basic charge (single-phase service)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — First Block",
                    charge_value=energy_tier1,
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=tier1_threshold or SEED_GENERAL_SERVICE_SMALL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes=f"First {int(tier1_threshold or SEED_GENERAL_SERVICE_SMALL['tier1_threshold_kwh']):,} kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — Balance",
                    charge_value=energy_tier2,
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=tier1_threshold or SEED_GENERAL_SERVICE_SMALL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="All additional kWh beyond the first block",
                ),
            ],
        )

    def _parse_gs_medium(self, tables: list[list[list[str]]]) -> Optional[TariffRecord]:
        """Parse GS Medium (Demand) rates from commercial page tables."""
        basic_charge: Optional[float] = None
        energy_tier1: Optional[float] = None
        energy_tier2: Optional[float] = None
        tier1_threshold: Optional[float] = None
        demand_charge: Optional[float] = None

        in_gs_medium_section = False

        for table in tables:
            for row in table:
                if not row:
                    continue
                row_text = " ".join(row).lower()

                # Detect GS Medium section
                if "medium" in row_text and ("general" in row_text or ">200" in row_text or "200 kva" in row_text):
                    in_gs_medium_section = True
                # If we hit the next section (e.g. Large), stop
                elif in_gs_medium_section and "large" in row_text and "general" in row_text:
                    if len(row) <= 2 or not any(
                        "¢" in cell or "$" in cell for cell in row
                    ):
                        in_gs_medium_section = False

                if not in_gs_medium_section:
                    continue

                if len(row) < 2:
                    continue

                charge_text = row[0].lower()
                cost_text = row[-1]

                # Basic charge
                if "basic" in charge_text and ("monthly" in charge_text or "month" in charge_text or "charge" in charge_text):
                    val = clean_currency(cost_text)
                    if val is not None:
                        basic_charge = val

                # Energy tiers
                if "first" in charge_text and "kwh" in charge_text:
                    val = clean_currency(cost_text)
                    if val is not None:
                        energy_tier1 = val
                        threshold_match = re.search(r"(\d[\d,]*)\s*kwh", charge_text)
                        if threshold_match:
                            tier1_threshold = float(threshold_match.group(1).replace(",", ""))

                if "balance" in charge_text and "kwh" in charge_text:
                    val = clean_currency(cost_text)
                    if val is not None:
                        energy_tier2 = val

                # Demand charge — look for "balance" with "kVA" or just "kVA" charge
                if "balance" in charge_text and "kva" in charge_text:
                    val = clean_currency(cost_text)
                    if val is not None:
                        demand_charge = val
                elif "kva" in charge_text and "demand" in charge_text:
                    val = clean_currency(cost_text)
                    if val is not None:
                        demand_charge = val

        if basic_charge is None or energy_tier1 is None or energy_tier2 is None or demand_charge is None:
            self.logger.warning(
                "Could not extract all GS Medium values (basic=%s, tier1=%s, tier2=%s, demand=%s)",
                basic_charge, energy_tier1, energy_tier2, demand_charge,
            )
            return None

        return TariffRecord(
            utility_name="Manitoba Hydro",
            province="MB",
            utility_type="electricity",
            tariff_name="General Service Medium (Demand)",
            customer_class="commercial",
            sub_class="general service medium",
            rate_structure="demand",
            effective_date=SEED_GENERAL_SERVICE_MEDIUM["effective_date"],
            source_url=COMMERCIAL_URL,
            confidence="high",
            eligibility="Demand-metered commercial customers (>200 kVA)",
            notes="Medium commercial accounts with demand metering",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=basic_charge,
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=demand_charge,
                    charge_unit="$/kVA",
                    demand_unit="kVA",
                    notes="First 50 kVA at no charge; applied to billing demand above 50 kVA",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — First Block",
                    charge_value=energy_tier1,
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=tier1_threshold or SEED_GENERAL_SERVICE_MEDIUM["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes=f"First {int(tier1_threshold or SEED_GENERAL_SERVICE_MEDIUM['tier1_threshold_kwh']):,} kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — Balance",
                    charge_value=energy_tier2,
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=tier1_threshold or SEED_GENERAL_SERVICE_MEDIUM["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="All additional kWh beyond the first block",
                ),
            ],
        )

    # ── Seed / fallback data ─────────────────────────────────────

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Manitoba Hydro",
            province="MB",
            utility_type="electricity",
            tariff_name="Residential Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes=(
                "Manitoba Hydro flat residential rate. "
                "Among the lowest electricity rates in Canada due to abundant hydroelectric generation."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                    notes="Monthly basic charge regardless of consumption (≤200 Amp service)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        # ── General Service Small (Non-Demand) ───────────────────
        records.append(TariffRecord(
            utility_name="Manitoba Hydro",
            province="MB",
            utility_type="electricity",
            tariff_name="General Service Small (Non-Demand)",
            customer_class="commercial",
            sub_class="general service small",
            rate_structure="tiered",
            effective_date=SEED_GENERAL_SERVICE_SMALL["effective_date"],
            source_url=SEED_GENERAL_SERVICE_SMALL["source_url"],
            confidence="high",
            eligibility="Non-demand metered commercial customers (≤50 kVA)",
            notes="Small commercial accounts without demand metering",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_GENERAL_SERVICE_SMALL["basic_charge_per_month"],
                    charge_unit="$/month",
                    notes="Monthly basic charge (single-phase service)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — First Block",
                    charge_value=SEED_GENERAL_SERVICE_SMALL["energy_rate_tier1"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_GENERAL_SERVICE_SMALL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="First 11,000 kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — Balance",
                    charge_value=SEED_GENERAL_SERVICE_SMALL["energy_rate_tier2"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_GENERAL_SERVICE_SMALL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="All additional kWh beyond the first block",
                ),
            ],
        ))

        # ── General Service Medium (Demand) ──────────────────────
        records.append(TariffRecord(
            utility_name="Manitoba Hydro",
            province="MB",
            utility_type="electricity",
            tariff_name="General Service Medium (Demand)",
            customer_class="commercial",
            sub_class="general service medium",
            rate_structure="demand",
            effective_date=SEED_GENERAL_SERVICE_MEDIUM["effective_date"],
            source_url=SEED_GENERAL_SERVICE_MEDIUM["source_url"],
            confidence="high",
            eligibility="Demand-metered commercial customers (>200 kVA)",
            notes="Medium commercial accounts with demand metering",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_GENERAL_SERVICE_MEDIUM["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_GENERAL_SERVICE_MEDIUM["demand_charge"],
                    charge_unit="$/kVA",
                    demand_unit="kVA",
                    notes="First 50 kVA at no charge; applied to billing demand above 50 kVA",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — First Block",
                    charge_value=SEED_GENERAL_SERVICE_MEDIUM["energy_rate_tier1"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_GENERAL_SERVICE_MEDIUM["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="First 19,500 kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — Balance",
                    charge_value=SEED_GENERAL_SERVICE_MEDIUM["energy_rate_tier2"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_GENERAL_SERVICE_MEDIUM["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="All additional kWh beyond the first block",
                ),
            ],
        ))

        return records
