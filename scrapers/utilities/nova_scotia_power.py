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
    find_text_near_label,
    extract_rate_from_text,
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
    "base_charge": 22.00,             # $/month
    "energy_tier1": 0.19804,          # $/kWh — first 200 kWh/month
    "energy_tier2": 0.17997,          # $/kWh — balance
    "tier1_threshold_kwh": 200,
    "eligibility": "Under 45,000 kWh/year",
}

SEED_RATE11 = {
    "effective_date": "2026-01-01",
    "source_url": BUSINESS_URL,
    "demand_charge": 9.809,           # $/kW
    "energy_tier1": 0.15738,          # $/kWh — first 200 kWh per kW of max demand
    "energy_tier2": 0.12674,          # $/kWh — balance
    "tier1_threshold_desc": "First 200 kWh per kW of maximum demand",
    "eligibility": "Annual consumption ≥32,000 kWh; billing demand <2,000 kVA",
}

SEED_RATE12 = {
    "effective_date": "2026-01-01",
    "source_url": BUSINESS_URL,
    "demand_charge": 11.174,          # $/kVA
    "energy_rate": 0.11780,           # $/kWh — flat
    "minimum_charge": 22.00,          # $/month
    "eligibility": "Billing demand ≥2,000 kVA or 1,800 kW",
}

# Commercial rate classes published on the business rates page.
# (code, tariff_name, sub_class, rate_structure, page section header)
_COMMERCIAL_RATES: list[tuple[str, str, str, str, str]] = [
    ("10", "Small Commercial", "small commercial", "tiered",
     "Small Commercial (Small General Tariff): Rate 10"),
    ("11", "Commercial General Demand", "general demand", "demand",
     "Commercial General Demand: Rate 11"),
    ("12", "Large Commercial", "large commercial", "demand",
     "Large Commercial (Large General Tariff): Rate 12"),
]


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
            records.extend(self.mark_fallback(self._seed_data()))

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
                return self.mark_live_parsed(live_records)

            # Live residential succeeded but commercial did not: mark each honestly
            self.logger.info("Using seed data for commercial rate classes")
            seed_commercial = self.mark_fallback([
                self._seed_data_rate10(),
                self._seed_data_rate11(),
                self._seed_data_rate12(),
            ])
            return self.mark_live_parsed(live_records) + seed_commercial

        except Exception as e:
            self.logger.warning("Could not fetch Nova Scotia Power page: %s", e)
            return None

    def _try_live_commercial(self) -> Optional[list[TariffRecord]]:
        """Parse Rate 10/11/12 from the NSUARB-approved business rate schedule page."""
        try:
            html = self.fetch_page(BUSINESS_URL)
        except Exception as e:
            self.logger.warning("Could not fetch business rates page: %s", e)
            return None

        text = parse_html(html).get_text("\n", strip=True)
        headers = [row[4] for row in _COMMERCIAL_RATES] + ["Large Industrial"]
        eligibility = {
            "10": SEED_RATE10["eligibility"],
            "11": SEED_RATE11["eligibility"],
            "12": SEED_RATE12["eligibility"],
        }
        records: list[TariffRecord] = []
        for idx, (code, name, sub, structure, header) in enumerate(_COMMERCIAL_RATES):
            section = self._commercial_section(text, header, headers[idx + 1:])
            if not section:
                continue
            components = self._parse_commercial_components(section)
            if not components:
                continue
            records.append(TariffRecord(
                utility_name="Nova Scotia Power", province="NS", utility_type="electricity",
                tariff_name=name, tariff_code=code, customer_class="commercial",
                sub_class=sub, rate_structure=structure,
                effective_date=SEED_RATE10["effective_date"], source_url=BUSINESS_URL,
                confidence="high", eligibility=eligibility[code],
                notes=(
                    f"NS Power Rate {code} — {name} — live parsed from the "
                    "NSUARB-approved business rate schedule."
                ),
                components=components,
            ))

        if not records:
            self.logger.warning("Could not parse any commercial rates from business page")
            return None

        seed_commercial = [
            self._seed_data_rate10(), self._seed_data_rate11(), self._seed_data_rate12(),
        ]
        alerts = compare_to_seed(records, seed_commercial)
        log_change_alerts(alerts)
        if has_critical_alerts(alerts):
            self.logger.error(
                "Critical deviation in live commercial data vs seed — falling back to seed"
            )
            return None
        self.logger.info("Parsed %d commercial rate classes from business page", len(records))
        return records

    @staticmethod
    def _commercial_section(text: str, start_header: str, end_headers: list[str]) -> str:
        """Return the primary-charge slice for a rate, cut before samples/minimum-charge notes."""
        i = text.find(start_header)
        if i == -1:
            return ""
        i += len(start_header)
        end = len(text)
        stops = list(end_headers) + [
            "The minimum monthly", "The maximum charge", "minimum monthly bill", "Sample ",
        ]
        for marker in stops:
            j = text.find(marker, i)
            if j != -1:
                end = min(end, j)
        return text[i:end]

    def _parse_commercial_components(self, section: str) -> list[RateComponent]:
        """Extract base, demand and (flat/tiered) energy charges from one rate section."""
        components: list[RateComponent] = []

        base = re.search(r"\$\s*([\d.]+)\s*per month(?!\s*per\s*kilo)", section, re.I)
        if base:
            components.append(RateComponent(
                component_type="fixed", component_name="Base Charge",
                charge_value=float(base.group(1)), charge_unit="$/month",
                notes="Monthly base charge",
            ))

        demand = re.search(
            r"\$\s*([\d.]+)\s*per month per (kilowatt|kilovolt ampere)", section, re.I
        )
        if demand:
            unit = "kW" if "kilowatt" in demand.group(2).lower() else "kVA"
            components.append(RateComponent(
                component_type="demand", component_name="Demand Charge",
                charge_value=float(demand.group(1)), charge_unit=f"$/{unit}", demand_unit=unit,
                notes="Per unit of billing (maximum) demand",
            ))

        for em in re.finditer(
            r"([\d.]+)\s*[^\d\s]{0,3}\s*per kilowatt hour([^\n.]*)", section, re.I
        ):
            qualifier = re.sub(r"\s+", " ", em.group(2)).strip()
            tier_number: Optional[int] = None
            threshold: Optional[float] = None
            first = re.search(r"first ([\d,]+)", qualifier, re.I)
            if first:
                tier_number = 1
                threshold = float(first.group(1).replace(",", ""))
            elif "additional" in qualifier.lower():
                tier_number = 2
            label = ("Energy Charge " + qualifier).strip()[:110] if qualifier else "Energy Charge"
            components.append(RateComponent(
                component_type="energy", component_name=label,
                charge_value=round(float(em.group(1)) / 100.0, 6), charge_unit="$/kWh",
                tier_number=tier_number, tier_threshold=threshold,
                tier_unit="kWh" if threshold else None,
            ))

        return components

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
