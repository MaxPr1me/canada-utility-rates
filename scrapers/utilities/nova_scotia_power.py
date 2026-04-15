"""
nova_scotia_power.py — Scraper for Nova Scotia Power electricity rates (Nova Scotia).

Nova Scotia Power Inc. (NSPI) is the primary electricity provider in
Nova Scotia, an investor-owned utility (Emera subsidiary). Rates are
predominantly flat for residential and small general customers.

Official source (landing page — no rate values):
  https://www.nspower.ca/products-services/rate-information

Residential rates page (contains actual values):
  https://www.nspower.ca/your-home/residential-rates/standard-residential

Business rates page (commercial rate classes):
  https://www.nspower.ca/your-business/save-money-energy/business-rates

Regulated by: Nova Scotia Utility and Review Board (NSUARB)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html,
    extract_tables,
    find_text_near_label,
    extract_rate_from_text,
    clean_currency,
)
from scrapers.utils.change_detection import (
    compare_to_seed,
    log_change_alerts,
    has_critical_alerts,
)

logger = logging.getLogger(__name__)

# ── URLs ──────────────────────────────────────────────────────────
RESIDENTIAL_URL = (
    "https://www.nspower.ca/your-home/residential-rates/standard-residential"
)
BUSINESS_URL = (
    "https://www.nspower.ca/your-business/save-money-energy/business-rates"
)

# Known rate values — used as seed/fallback data.
SEED_RESIDENTIAL = {
    "effective_date": "2026-01-01",
    "source_url": RESIDENTIAL_URL,
    "energy_rate": 0.18187,           # $/kWh
    "basic_charge_per_month": 19.17,  # $/month
}

SEED_RATE10 = {
    "effective_date": "2026-01-01",
    "source_url": BUSINESS_URL,
    "base_charge": 21.28,             # $/month
    "energy_tier1": 0.18872,          # $/kWh — first 200 kWh/month
    "energy_tier2": 0.17146,          # $/kWh — balance
    "tier1_threshold_kwh": 200,
    "eligibility": "Under 45,000 kWh/year",
}

SEED_RATE11 = {
    "effective_date": "2026-01-01",
    "source_url": BUSINESS_URL,
    "demand_charge": 10.554,          # $/kW
    "energy_tier1": 0.15532,          # $/kWh — first 200 kWh per kW of max demand
    "energy_tier2": 0.12235,          # $/kWh — balance
    "tier1_threshold_desc": "First 200 kWh per kW of maximum demand",
    "eligibility": "Annual consumption ≥32,000 kWh; billing demand <2,000 kVA",
}

SEED_RATE12 = {
    "effective_date": "2026-01-01",
    "source_url": BUSINESS_URL,
    "demand_charge": 13.845,          # $/kVA
    "energy_rate": 0.12256,           # $/kWh — flat
    "minimum_charge": 21.28,          # $/month
    "eligibility": "Billing demand ≥2,000 kVA or 1,800 kW",
}


class NovaScotiaPowerScraper(BaseScraper):
    """Scrape Nova Scotia Power electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Nova Scotia Power", province="NS")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Nova Scotia Power rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Nova Scotia Power tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for Nova Scotia Power")
            records.extend(self._seed_data())

        return records

    # ── Live scraping ────────────────────────────────────────────

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live Nova Scotia Power website."""
        try:
            html = self.fetch_page(RESIDENTIAL_URL)
            soup = parse_html(html)

            residential = self._parse_residential(soup)
            if residential is None:
                self.logger.warning("Could not parse residential rates from live page")
                return None

            # Build the live record list
            live_records = [residential]

            # Validate live residential data against seed using change detection
            seed_residential = self._seed_data_residential()
            alerts = compare_to_seed([residential], [seed_residential])
            log_change_alerts(alerts)

            if has_critical_alerts(alerts):
                self.logger.error(
                    "Critical deviation in live residential data vs seed — falling back to seed"
                )
                return None

            # Attempt to parse commercial rates from business page
            commercial_records = self._try_live_commercial()
            if commercial_records:
                live_records.extend(commercial_records)
            else:
                # Fall back to commercial seed data
                self.logger.info("Using seed data for commercial rate classes")
                live_records.append(self._seed_data_rate10())
                live_records.append(self._seed_data_rate11())
                live_records.append(self._seed_data_rate12())

            return live_records

        except Exception as e:
            self.logger.warning("Could not fetch Nova Scotia Power page: %s", e)
            return None

    def _try_live_commercial(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse commercial rates from the business rates page."""
        try:
            html = self.fetch_page(BUSINESS_URL)
            soup = parse_html(html)
            page_text = soup.get_text()

            records = []

            rate10 = self._parse_rate10(soup, page_text)
            rate11 = self._parse_rate11(soup, page_text)
            rate12 = self._parse_rate12(soup, page_text)

            for record in [rate10, rate11, rate12]:
                if record is not None:
                    records.append(record)

            if not records:
                self.logger.warning("Could not parse any commercial rates from business page")
                return None

            # Validate live commercial data against seeds
            seed_commercial = [
                self._seed_data_rate10(),
                self._seed_data_rate11(),
                self._seed_data_rate12(),
            ]
            alerts = compare_to_seed(records, seed_commercial)
            log_change_alerts(alerts)

            if has_critical_alerts(alerts):
                self.logger.error(
                    "Critical deviation in live commercial data vs seed — falling back to seed"
                )
                return None

            self.logger.info(
                "Parsed %d commercial rate classes from business page", len(records)
            )
            return records

        except Exception as e:
            self.logger.warning("Could not fetch business rates page: %s", e)
            return None

    def _parse_rate10(self, soup, page_text: str) -> Optional[TariffRecord]:
        """Parse Rate 10 — Small Commercial from the business page."""
        # Look for base charge near "Small Commercial" or "Rate 10"
        base_charge = self._find_commercial_value(soup, page_text, [
            "Base Charge", "Basic Charge",
        ], section_hint="Small Commercial")
        energy_tier1 = self._find_commercial_value(soup, page_text, [
            "first 200", "First 200 kWh",
        ], section_hint="Small Commercial")
        energy_tier2 = self._find_commercial_value(soup, page_text, [
            "balance", "Balance",
        ], section_hint="Small Commercial")

        if base_charge is not None and energy_tier1 is not None:
            # Sanity checks
            if not (5.0 < base_charge < 100.0):
                self.logger.warning("Rate 10 base charge out of range: %s", base_charge)
                return None
            if not (0.05 < energy_tier1 < 1.0):
                self.logger.warning("Rate 10 energy tier1 out of range: %s", energy_tier1)
                return None

            components = [
                RateComponent(
                    component_type="fixed",
                    component_name="Base Charge",
                    charge_value=base_charge,
                    charge_unit="$/month",
                    notes="Monthly base charge",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — First 200 kWh",
                    charge_value=energy_tier1,
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=200.0,
                    tier_unit="kWh/month",
                    notes="First 200 kWh per month",
                ),
            ]
            if energy_tier2 is not None and 0.05 < energy_tier2 < 1.0:
                components.append(RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — Balance",
                    charge_value=energy_tier2,
                    charge_unit="$/kWh",
                    tier_number=2,
                    notes="All additional kWh beyond 200 kWh/month",
                ))

            return TariffRecord(
                utility_name="Nova Scotia Power",
                province="NS",
                utility_type="electricity",
                tariff_name="Small Commercial",
                tariff_code="10",
                customer_class="commercial",
                sub_class="small commercial",
                rate_structure="tiered",
                effective_date=SEED_RATE10["effective_date"],
                source_url=BUSINESS_URL,
                confidence="high",
                eligibility=SEED_RATE10["eligibility"],
                notes="NS Power Rate 10 — Small Commercial — live parsed",
                components=components,
            )

        self.logger.debug("Could not parse Rate 10 from business page")
        return None

    def _parse_rate11(self, soup, page_text: str) -> Optional[TariffRecord]:
        """Parse Rate 11 — Commercial General Demand from the business page."""
        demand_charge = self._find_commercial_value(soup, page_text, [
            "Demand Charge",
        ], section_hint="General Demand")
        energy_tier1 = self._find_commercial_value(soup, page_text, [
            "first 200 kWh per kW", "First 200 kWh",
        ], section_hint="General Demand")
        energy_tier2 = self._find_commercial_value(soup, page_text, [
            "balance", "Balance",
        ], section_hint="General Demand")

        if demand_charge is not None and energy_tier1 is not None:
            if not (1.0 < demand_charge < 100.0):
                self.logger.warning("Rate 11 demand charge out of range: %s", demand_charge)
                return None
            if not (0.05 < energy_tier1 < 1.0):
                self.logger.warning("Rate 11 energy tier1 out of range: %s", energy_tier1)
                return None

            components = [
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=demand_charge,
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Billing demand charge",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — First 200 kWh/kW",
                    charge_value=energy_tier1,
                    charge_unit="$/kWh",
                    tier_number=1,
                    notes="First 200 kWh per kW of maximum demand",
                ),
            ]
            if energy_tier2 is not None and 0.05 < energy_tier2 < 1.0:
                components.append(RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — Balance",
                    charge_value=energy_tier2,
                    charge_unit="$/kWh",
                    tier_number=2,
                    notes="All additional kWh beyond first block",
                ))

            return TariffRecord(
                utility_name="Nova Scotia Power",
                province="NS",
                utility_type="electricity",
                tariff_name="Commercial General Demand",
                tariff_code="11",
                customer_class="commercial",
                sub_class="general demand",
                rate_structure="demand",
                effective_date=SEED_RATE11["effective_date"],
                source_url=BUSINESS_URL,
                confidence="high",
                eligibility=SEED_RATE11["eligibility"],
                notes="NS Power Rate 11 — Commercial General Demand — live parsed",
                components=components,
            )

        self.logger.debug("Could not parse Rate 11 from business page")
        return None

    def _parse_rate12(self, soup, page_text: str) -> Optional[TariffRecord]:
        """Parse Rate 12 — Large Commercial from the business page."""
        demand_charge = self._find_commercial_value(soup, page_text, [
            "Demand Charge",
        ], section_hint="Large Commercial")
        energy_rate = self._find_commercial_value(soup, page_text, [
            "Energy Charge",
        ], section_hint="Large Commercial")

        if demand_charge is not None and energy_rate is not None:
            if not (1.0 < demand_charge < 100.0):
                self.logger.warning("Rate 12 demand charge out of range: %s", demand_charge)
                return None
            if not (0.05 < energy_rate < 1.0):
                self.logger.warning("Rate 12 energy rate out of range: %s", energy_rate)
                return None

            return TariffRecord(
                utility_name="Nova Scotia Power",
                province="NS",
                utility_type="electricity",
                tariff_name="Large Commercial",
                tariff_code="12",
                customer_class="commercial",
                sub_class="large commercial",
                rate_structure="demand",
                effective_date=SEED_RATE12["effective_date"],
                source_url=BUSINESS_URL,
                confidence="high",
                eligibility=SEED_RATE12["eligibility"],
                notes="NS Power Rate 12 — Large Commercial — live parsed",
                components=[
                    RateComponent(
                        component_type="demand",
                        component_name="Demand Charge",
                        charge_value=demand_charge,
                        charge_unit="$/kVA",
                        demand_unit="kVA",
                        notes="Billing demand charge",
                    ),
                    RateComponent(
                        component_type="energy",
                        component_name="Energy Charge",
                        charge_value=energy_rate,
                        charge_unit="$/kWh",
                        notes="Flat energy rate for all kWh consumed",
                    ),
                    RateComponent(
                        component_type="fixed",
                        component_name="Minimum Charge",
                        charge_value=SEED_RATE12["minimum_charge"],
                        charge_unit="$/month",
                        notes="Minimum monthly charge",
                    ),
                ],
            )

        self.logger.debug("Could not parse Rate 12 from business page")
        return None

    def _find_commercial_value(
        self,
        soup,
        page_text: str,
        labels: list[str],
        section_hint: Optional[str] = None,
    ) -> Optional[float]:
        """
        Search for a rate value near the given labels on the business page.

        Uses multiple strategies:
          1. Table extraction — look for values in table cells adjacent to labels.
          2. find_text_near_label — HTML structural search.
          3. Regex scan of page text for patterns like "$21.280" or "18.872¢".

        If section_hint is given, prefer matches within text blocks
        containing the hint (e.g. "Small Commercial").
        """
        # Strategy 1: Table-based extraction
        tables = extract_tables(str(soup))
        for table in tables:
            for row in table:
                row_text = " ".join(row).lower()
                # Check if this row is in the right section
                if section_hint and section_hint.lower() not in row_text:
                    # Check the whole table for section context
                    table_text = " ".join(" ".join(r) for r in table).lower()
                    if section_hint.lower() not in table_text:
                        continue
                for label in labels:
                    if label.lower() in row_text:
                        # Try to extract a value from cells in this row
                        for cell in row:
                            value = clean_currency(cell)
                            if value is not None and value > 0:
                                self.logger.debug(
                                    "Found value %s for label '%s' in table", value, label
                                )
                                return value

        # Strategy 2: find_text_near_label in HTML structure
        for label in labels:
            text = find_text_near_label(soup, label)
            if text:
                value = clean_currency(text)
                if value is not None and value > 0:
                    self.logger.debug(
                        "Found value %s for label '%s' via find_text_near_label", value, label
                    )
                    return value

        # Strategy 3: Regex scan of page text for section-specific values
        if section_hint:
            # Find the section in the page text
            hint_lower = section_hint.lower()
            text_lower = page_text.lower()
            section_start = text_lower.find(hint_lower)
            if section_start >= 0:
                # Search within a reasonable window after the section header
                section_text = page_text[section_start:section_start + 2000]
                for label in labels:
                    label_pos = section_text.lower().find(label.lower())
                    if label_pos >= 0:
                        nearby = section_text[label_pos:label_pos + 200]
                        # Try $/value pattern
                        match = re.search(r"\$\s*(\d+\.?\d*)", nearby)
                        if match:
                            value = float(match.group(1))
                            self.logger.debug(
                                "Found value %s for label '%s' via regex ($)", value, label
                            )
                            return value
                        # Try cents pattern (e.g. "18.872¢")
                        match = re.search(r"(\d+\.?\d*)\s*[¢]", nearby)
                        if match:
                            value = float(match.group(1)) / 100.0
                            self.logger.debug(
                                "Found value %s for label '%s' via regex (¢)", value, label
                            )
                            return value

        return None

    def _parse_residential(self, soup) -> Optional[TariffRecord]:
        """
        Parse residential rate values from the standard residential page.

        Expected HTML structure:
          <h4>Base Charge on Your Bill (Fixed Charge)</h4>
          <ul><li>... $19.17 per month ...</li></ul>
          <h4>Energy Charge (Variable Charge)</h4>
          <ul><li>... $0.18187 per kWh ...</li></ul>
        """
        basic_charge = self._extract_basic_charge(soup)
        energy_rate = self._extract_energy_rate(soup)

        if basic_charge is None or energy_rate is None:
            self.logger.warning(
                "Incomplete parse: basic_charge=%s, energy_rate=%s",
                basic_charge,
                energy_rate,
            )
            return None

        # Sanity check: rates should be positive and in reasonable ranges
        if not (1.0 < basic_charge < 100.0):
            self.logger.warning("Basic charge out of range: %s", basic_charge)
            return None
        if not (0.01 < energy_rate < 1.0):
            self.logger.warning("Energy rate out of range: %s", energy_rate)
            return None

        return TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Domestic Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=RESIDENTIAL_URL,
            confidence="high",
            notes="Nova Scotia Power domestic (residential) flat electricity rate — live parsed",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=basic_charge,
                    charge_unit="$/month",
                    notes="Monthly basic charge regardless of consumption",
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

    def _extract_basic_charge(self, soup) -> Optional[float]:
        """Extract the monthly base/fixed charge from the page."""
        # Approach A: find_text_near_label for "Base Charge" or "Fixed Charge"
        for label in ("Base Charge", "Fixed Charge"):
            text = find_text_near_label(soup, label)
            if text:
                rate = extract_rate_from_text(text)
                if rate is not None:
                    self.logger.debug("Found basic charge via label '%s': %s", label, rate)
                    return rate

        # Approach B: scan all <li> elements for "per month" pattern
        for li in soup.find_all("li"):
            li_text = li.get_text(strip=True)
            if "per month" in li_text.lower() and "$" in li_text:
                rate = extract_rate_from_text(li_text)
                if rate is not None:
                    self.logger.debug("Found basic charge via <li> scan: %s", rate)
                    return rate

        return None

    def _extract_energy_rate(self, soup) -> Optional[float]:
        """Extract the per-kWh energy charge from the page."""
        # Approach A: find_text_near_label for "Energy Charge" or "Variable Charge"
        for label in ("Energy Charge", "Variable Charge"):
            text = find_text_near_label(soup, label)
            if text:
                rate = extract_rate_from_text(text)
                if rate is not None:
                    self.logger.debug("Found energy rate via label '%s': %s", label, rate)
                    return rate

        # Approach B: scan all <li> elements for "per kWh" pattern
        for li in soup.find_all("li"):
            li_text = li.get_text(strip=True)
            if "per kwh" in li_text.lower() and "$" in li_text:
                rate = extract_rate_from_text(li_text)
                if rate is not None:
                    self.logger.debug("Found energy rate via <li> scan: %s", rate)
                    return rate

        return None

    # ── Seed / fallback data ─────────────────────────────────────

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        return [
            self._seed_data_residential(),
            self._seed_data_rate10(),
            self._seed_data_rate11(),
            self._seed_data_rate12(),
        ]

    def _seed_data_residential(self) -> TariffRecord:
        """Return seed data for the residential tariff."""
        return TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Domestic Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes="Nova Scotia Power domestic (residential) flat electricity rate",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                    notes="Monthly basic charge regardless of consumption",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        )

    def _seed_data_rate10(self) -> TariffRecord:
        """Return seed data for Rate 10 — Small Commercial."""
        return TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Small Commercial",
            tariff_code="10",
            customer_class="commercial",
            sub_class="small commercial",
            rate_structure="tiered",
            effective_date=SEED_RATE10["effective_date"],
            source_url=SEED_RATE10["source_url"],
            confidence="high",
            eligibility=SEED_RATE10["eligibility"],
            notes="NS Power Rate 10 — Small Commercial tiered energy rate",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Base Charge",
                    charge_value=SEED_RATE10["base_charge"],
                    charge_unit="$/month",
                    notes="Monthly base charge",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — First 200 kWh",
                    charge_value=SEED_RATE10["energy_tier1"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=float(SEED_RATE10["tier1_threshold_kwh"]),
                    tier_unit="kWh/month",
                    notes="First 200 kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — Balance",
                    charge_value=SEED_RATE10["energy_tier2"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    notes="All additional kWh beyond 200 kWh/month",
                ),
            ],
        )

    def _seed_data_rate11(self) -> TariffRecord:
        """Return seed data for Rate 11 — Commercial General Demand."""
        return TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Commercial General Demand",
            tariff_code="11",
            customer_class="commercial",
            sub_class="general demand",
            rate_structure="demand",
            effective_date=SEED_RATE11["effective_date"],
            source_url=SEED_RATE11["source_url"],
            confidence="high",
            eligibility=SEED_RATE11["eligibility"],
            notes="NS Power Rate 11 — Commercial General Demand",
            components=[
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_RATE11["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Billing demand charge",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — First 200 kWh/kW",
                    charge_value=SEED_RATE11["energy_tier1"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    notes="First 200 kWh per kW of maximum demand",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — Balance",
                    charge_value=SEED_RATE11["energy_tier2"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    notes="All additional kWh beyond first block",
                ),
            ],
        )

    def _seed_data_rate12(self) -> TariffRecord:
        """Return seed data for Rate 12 — Large Commercial."""
        return TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Large Commercial",
            tariff_code="12",
            customer_class="commercial",
            sub_class="large commercial",
            rate_structure="demand",
            effective_date=SEED_RATE12["effective_date"],
            source_url=SEED_RATE12["source_url"],
            confidence="high",
            eligibility=SEED_RATE12["eligibility"],
            notes="NS Power Rate 12 — Large Commercial",
            components=[
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_RATE12["demand_charge"],
                    charge_unit="$/kVA",
                    demand_unit="kVA",
                    notes="Billing demand charge",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_RATE12["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat energy rate for all kWh consumed",
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="Minimum Charge",
                    charge_value=SEED_RATE12["minimum_charge"],
                    charge_unit="$/month",
                    notes="Minimum monthly charge",
                ),
            ],
        )
