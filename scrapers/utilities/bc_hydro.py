"""
bc_hydro.py — Scraper for BC Hydro electricity rates (British Columbia).

BC Hydro is the primary electricity provider in British Columbia.
Residential service includes tiered, flat, optional time-of-day combinations
and a closed dual-fuel schedule. The approved tariff supplies rates and riders.

Official sources:
  Residential (tiered): https://app.bchydro.com/accounts-billing/rates-energy-use/electricity-rates/residential-rates/tiered.html
  Business rates:       https://app.bchydro.com/accounts-billing/rates-energy-use/electricity-rates/business-rates.html

Rate classes scraped:
    - Residential tiered (1101), flat (1151), each optionally with time-of-day (2101)
    - Closed residential dual-fuel heating service (1105)
  - Small General Service (Rate 1300) — flat energy, no demand charge
  - Medium General Service (Rate 1500) — energy + demand charge
  - Large General Service (Rate 1600) — energy + demand charge (higher demand, lower energy)

Residential prices, dates and riders come from the approved Electric Tariff PDF;
the tiered/flat/time-of-day sub-pages are product discovery references. Business
rates continue to use the existing prose parser for the three supported classes.

NOTE: BC Hydro redirects www.bchydro.com to app.bchydro.com.
"""

from __future__ import annotations

import re
import logging
from dataclasses import replace
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html, extract_rate_from_text, detect_js_rendered, extract_pdf_pages,
    extract_effective_date, DocumentPage,
)
from scrapers.utils.change_detection import compare_to_seed, log_change_alerts, has_critical_alerts

logger = logging.getLogger(__name__)

# ── Source URLs ───────────────────────────────────────────────────
RESIDENTIAL_URL = "https://app.bchydro.com/accounts-billing/rates-energy-use/electricity-rates/residential-rates/tiered.html"
FLAT_URL = "https://app.bchydro.com/accounts-billing/rates-energy-use/electricity-rates/residential-rates/flat.html"
TIME_OF_DAY_URL = "https://app.bchydro.com/accounts-billing/rates-energy-use/electricity-rates/residential-rates/time-of-day.html"
TARIFF_URL = "https://www.bchydro.com/content/dam/BCHydro/customer-portal/documents/corporate/tariff-filings/electric-tariff/bchydro-electric-tariff.pdf"
BUSINESS_URL = "https://app.bchydro.com/accounts-billing/rates-energy-use/electricity-rates/business-rates.html"

# ── Seed / fallback data (updated 2026-04-01) ────────────────────
SEED_RESIDENTIAL = {
    "effective_date": "2026-04-01",
    "source_url": RESIDENTIAL_URL,
    "step1_threshold_kwh": 1350,     # per ~2-month billing period
    "step1_rate": 0.1187,            # $/kWh
    "step2_rate": 0.1408,            # $/kWh
    "basic_charge_per_day": 0.2344,  # $/day
    "rider": -0.015,                 # approximately -1.5% (credit)
}

SEED_SMALL_GENERAL = {
    "effective_date": "2026-04-01",
    "source_url": BUSINESS_URL,
    "energy_rate": 0.1406,           # $/kWh
    "basic_charge_per_day": 0.4089,  # $/day
}

SEED_MEDIUM_GENERAL = {
    "effective_date": "2026-04-01",
    "source_url": BUSINESS_URL,
    "demand_charge": 6.07,           # $/kW
    "energy_rate": 0.1086,           # $/kWh
    "basic_charge_per_day": 0.2999,  # $/day
}

SEED_LARGE_GENERAL = {
    "effective_date": "2026-04-01",
    "source_url": BUSINESS_URL,
    "demand_charge": 13.83,          # $/kW
    "energy_rate": 0.0679,           # $/kWh
    "basic_charge_per_day": 0.2999,  # $/day
}


class BCHydroScraper(BaseScraper):
    """Scrape BC Hydro electricity rates."""

    def __init__(self):
        super().__init__(utility_name="BC Hydro", province="BC")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live BC Hydro rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        # Try live scraping first
        live_records = self._try_live_scrape()
        if live_records:
            self.logger.info(
                "Successfully scraped %d BC Hydro tariffs from live site",
                len(live_records),
            )
            return live_records

        # Fall back to seed data
        self.logger.warning("Live scrape failed -- using seed data for BC Hydro")
        return self.mark_fallback(self._seed_data())

    # ── Live scraping ─────────────────────────────────────────

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live BC Hydro website."""
        try:
            records: list[TariffRecord] = []

            # --- Residential (tiered.html sub-page) ---
            records.extend(self._parse_residential_options())

            # --- Business rates (SGS + MGS + LGS) ---
            biz_records = self._parse_business()
            if biz_records:
                records.extend(biz_records)

            if not records:
                return None

            # Change detection: compare live vs seed
            seed = self._seed_data()
            alerts = compare_to_seed(records, seed)
            log_change_alerts(alerts)

            if has_critical_alerts(alerts):
                self.logger.error(
                    "Critical deviations detected in BC Hydro live parse -- "
                    "falling back to seed data"
                )
                return None

            live = self.mark_live_parsed(records)
            covered = {record.tariff_name for record in records}
            fallback = [record for record in seed if record.tariff_name not in covered]
            return live + self.mark_fallback(fallback) if fallback else live

        except Exception as e:
            self.logger.warning("Could not fetch BC Hydro pages: %s", e)
            return None

    def _parse_residential(self) -> Optional[TariffRecord]:
        """Return the standard tiered option for callers needing a single record."""
        return next((record for record in self._parse_residential_options() if record.tariff_code == "1101"), None)

    def _parse_residential_options(self) -> list[TariffRecord]:
        for url in (RESIDENTIAL_URL, FLAT_URL, TIME_OF_DAY_URL):
            try:
                self.fetch_page(url)
            except Exception as exc:
                self.logger.warning("BC Hydro product page unavailable %s: %s", url, exc)
        try:
            return self._parse_residential_tariff(extract_pdf_pages(self.fetch_bytes(TARIFF_URL)))
        except Exception as exc:
            self.logger.warning("Could not parse BC Hydro residential tariff: %s", exc)
            return []

    def _parse_residential_tariff(self, pages: list[DocumentPage]) -> list[TariffRecord]:
        sections: dict[str, list[DocumentPage]] = {}
        for page in pages:
            header = re.match(r"BC Hydro Rate Schedule\s+(1101|1105|1151|2101|1901|1904)\b", page.text)
            if header:
                sections.setdefault(header.group(1), []).append(page)

        def schedule(code: str) -> tuple[str, str, str]:
            selected = sections.get(code, [])
            if not selected:
                raise ValueError(f"Missing RS {code}")
            dates = {extract_effective_date(page.text.split("Section", 1)[0]) for page in selected}
            if len(dates) != 1 or None in dates:
                raise ValueError(f"Missing or ambiguous RS {code} date")
            effective = next(iter(dates))
            if effective > self.now_iso()[:10]:
                raise ValueError(f"Future RS {code}")
            detail = f"Electric Tariff RS {code}; PDF pages " + ", ".join(str(page.page_number) for page in selected)
            return re.sub(r"\s+", " ", "\n".join(page.text for page in selected)), effective, detail

        cents = r"([\d]+(?:\.\d+)?)\s*(?:[\u00a2\u023c\ufffd]|cents?)"

        def value(text: str, label: str, unit: str) -> float:
            match = re.search(label + r"\s*" + cents + r"\s+per\s+" + unit + r"\b", text, re.I)
            if not match or float(match.group(1)) <= 0:
                raise ValueError(f"Missing {label} in {unit}")
            return round(float(match.group(1)) / 100.0, 6)

        riders: list[RateComponent] = []
        try:
            for code, title in (("1901", "Deferral Account Rate Rider"), ("1904", "Trade Income Rate Rider")):
                text, effective, detail = schedule(code)
                amount = re.search(r"charge equal to\s+(\(?-?\d+(?:\.\d+)?\)?)%", text)
                if not amount or "except for Rate Schedules 2101" not in text:
                    raise ValueError(f"Missing RS {code} rate or exclusions")
                raw = amount.group(1)
                percent = -float(raw[1:-1]) if raw.startswith("(") and raw.endswith(")") else float(raw)
                riders.append(RateComponent(
                    "rider", f"Rate Rider -- {title}", round(percent / 100.0, 6), "fraction",
                    effective_date=effective, source_url=TARIFF_URL, source_detail=detail,
                    notes="Applies to base schedule charges before taxes/levies, not to RS 2101 time-of-day adjustments.",
                ))
        except ValueError as exc:
            self.logger.warning("Incomplete BC Hydro residential riders: %s", exc)
            return []

        records: list[TariffRecord] = []
        for code, name, structure in (
            ("1101", "Residential Service (Rate 1101)", "tiered"),
            ("1151", "Residential Flat Rate (Rate 1151)", "flat"),
            ("1105", "Residential Dual Fuel (Rate 1105, Closed)", "flat"),
        ):
            try:
                text, effective, detail = schedule(code)
                if "Rate Schedule 1901" not in text or "Rate Schedule 1904" not in text:
                    raise ValueError("Missing rider continuation")
                components: list[RateComponent] = []
                if code != "1105":
                    basic = value(text, r"Basic Charge:", "day")
                    components.append(RateComponent("fixed", "Basic Charge", basic, "$/day"))
                if structure == "tiered":
                    first = re.search(r"Step 1: First\s+([\d,]+)\s+kWh per two months\s*@", text)
                    monthly = re.search(r"Step 1: First\s+([\d,]+)\s+kWh per month\s*@", text)
                    if not first or not monthly or "Step 1 is pro-rated on a daily basis" not in text:
                        raise ValueError("Missing residential threshold/billing-period rules")
                    threshold = float(first.group(1).replace(",", ""))
                    first_rate = value(text, r"Step 1: First [\d,]+ kWh per two months\s*@", "kWh")
                    second_rate = value(text, r"Step 2: Additional kWh per two months\s*@", "kWh")
                    if first_rate != value(text, r"Step 1: First [\d,]+ kWh per month\s*@", "kWh") or second_rate != value(text, r"Step 2: Additional kWh per month\s*@", "kWh"):
                        raise ValueError("Monthly and bi-monthly tier prices differ")
                    for number, rate in ((1, first_rate), (2, second_rate)):
                        components.append(RateComponent("energy", f"Step {number} Energy Charge", rate, "$/kWh",
                                                        tier_number=number, tier_threshold=threshold, tier_unit="kWh",
                                                        notes=f"Bi-monthly threshold shown; monthly threshold is {monthly.group(1)} kWh. Step 1 is pro-rated daily for the actual billing period."))
                else:
                    components.append(RateComponent("energy", "Energy Charge", value(text, r"Energy Charge:", "kWh"), "$/kWh"))
                eligibility = text.split("Availability", 1)[1].split("Rate Energy" if code == "1105" else "Rate Basic", 1)[0].strip()
                if code == "1105" and ("DUAL FUEL (CLOSED)" not in text or "no change in Customer since" not in text):
                    raise ValueError("Missing closed dual-fuel eligibility")
                if code != "1105":
                    discount = value(text, r"discount of", "month per kW")
                    if "more than three units" not in text:
                        raise ValueError("Missing transformer-ownership condition")
                    components.append(RateComponent(
                        "rebate", "Conditional Transformer Ownership Discount", -discount, "$/kW/month",
                        sub_component="conditional", demand_unit="kW",
                        notes="Only where the customer supplies transformation and the premises contains more than three units; based on Maximum Demand. Not an automatic household discount.",
                    ))
                for component in components:
                    component.source_url = TARIFF_URL
                    component.source_detail = detail
                    component.effective_date = effective
                records.append(TariffRecord(
                    utility_name="BC Hydro", province="BC", utility_type="electricity", tariff_name=name,
                    tariff_code=code, customer_class="residential", sub_class="closed dual fuel" if code == "1105" else structure,
                    rate_structure=structure, effective_date=max([effective] + [rider.effective_date for rider in riders]),
                    source_url=TARIFF_URL, source_page=detail, eligibility=eligibility,
                    notes="Published base tariff plus separate applicable riders; taxes and levies excluded. Transformer discount is conditional, not universal." if code != "1105" else "Closed legacy heating service; no new or additional load permitted. Applicable riders shown separately.",
                    components=components + [replace(rider) for rider in riders],
                ))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete BC Hydro RS %s: %s", code, exc)

        try:
            text, effective, detail = schedule("2101")
            if not all(phrase in text for phrase in (
                "concurrently receiving Service", "Rate Schedule 1101 or 1151",
                "not available for use in separately metered common property", "will not apply to this Rate Schedule",
            )):
                raise ValueError("Missing time-of-day applicability or rider exclusion")
            periods = {}
            for title in ("Off-Peak", "On-Peak", "Overnight"):
                match = re.search(rf"\d\. {title} Period (.*?)(?= \d\. | Special )", text)
                if not match or not re.search(r"\d{2}:\d{2}", match.group(1)):
                    raise ValueError(f"Missing {title} hours")
                periods[title] = match.group(1)
            overnight = re.search(r"Energy Credit: Overnight Period:\s*\(([\d.]+)\)\s*[\u00a2\u023c\ufffd]\s+per kWh", text)
            on_peak = re.search(r"Energy Charge: On-Peak Period:\s*([\d.]+)\s*[\u00a2\u023c\ufffd]\s+per kWh", text)
            off_peak = re.findall(r"Off-Peak Period:\s*([\d.]+)\s*[\u00a2\u023c\ufffd]\s+per kWh", text)
            if not overnight or not on_peak or len(off_peak) != 2 or any(float(amount) != 0 for amount in off_peak):
                raise ValueError("Missing or changed time-of-day adjustments")
            for base in list(records):
                if base.tariff_code not in {"1101", "1151"}:
                    continue
                adjustments = [
                    RateComponent("rebate", "Time-of-Day Overnight Credit", -round(float(overnight.group(1)) / 100.0, 6), "$/kWh", tou_period="overnight", tou_hours=periods["Overnight"]),
                    RateComponent("rider", "Time-of-Day On-Peak Surcharge", round(float(on_peak.group(1)) / 100.0, 6), "$/kWh", tou_period="on-peak", tou_hours=periods["On-Peak"]),
                    RateComponent("rider", "Time-of-Day Off-Peak Adjustment", 0.0, "$/kWh", tou_period="off-peak", tou_hours=periods["Off-Peak"]),
                ]
                for component in adjustments:
                    component.source_url = TARIFF_URL
                    component.source_detail = detail
                    component.effective_date = effective
                    component.notes = "Adjustment to the base energy price, not a replacement price. RS 1901/1904 riders do not apply to this adjustment."
                records.append(replace(
                    base, tariff_name=f"Residential {'Tiered' if base.tariff_code == '1101' else 'Flat'} with Time-of-Day (Rates {base.tariff_code} + 2101)",
                    tariff_code=base.tariff_code + "+2101", sub_class=base.sub_class + " with time-of-day",
                    rate_structure="mixed" if base.rate_structure == "tiered" else "tou",
                    effective_date=max(base.effective_date, effective), source_page=base.source_page + "; " + detail,
                    eligibility=base.eligibility + " Optional RS 2101; unavailable for separately metered common property. Applies daily, including weekends.",
                    components=[replace(component) for component in base.components] + adjustments,
                ))
        except ValueError as exc:
            self.logger.warning("BC Hydro time-of-day options unavailable: %s", exc)
        return records

    def _parse_business(self) -> Optional[list[TariffRecord]]:
        """Parse SGS (1300), MGS (1500), and LGS (1600) from business-rates.html."""
        try:
            html = self.fetch_page(BUSINESS_URL)
            if detect_js_rendered(html):
                self.logger.warning("Business rates page appears JS-rendered")
                return None

            soup = parse_html(html)
            page_text = soup.get_text(" ", strip=True)

            records: list[TariffRecord] = []

            # --- Small General Service (Rate 1300) ---
            sgs = self._parse_sgs(page_text)
            if sgs:
                records.append(sgs)

            # --- Medium General Service (Rate 1500) ---
            mgs = self._parse_mgs(page_text)
            if mgs:
                records.append(mgs)

            # --- Large General Service (Rate 1600) ---
            lgs = self._parse_lgs(page_text)
            if lgs:
                records.append(lgs)

            return records if records else None

        except Exception as e:
            self.logger.warning("Error parsing business rates page: %s", e)
            return None

    def _parse_sgs(self, page_text: str) -> Optional[TariffRecord]:
        """Extract Small General Service rates from page text."""
        # Isolate the SGS section: between "Small General Service" and
        # "Medium General Service" headers
        sgs_section = self._extract_section(
            page_text, "Small General Service", "Medium General Service"
        )
        if not sgs_section:
            self.logger.warning("Could not find SGS section in business page")
            return None

        basic = self._extract_cents_per(sgs_section, "cents per day")
        energy = self._extract_cents_per(sgs_section, "cents per kWh")

        if basic is None or energy is None:
            self.logger.warning(
                "Could not extract SGS rates (basic=%s, energy=%s)",
                basic, energy,
            )
            return None

        self.logger.info("Parsed SGS: basic=%.4f, energy=%.4f", basic, energy)

        return TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Small General Service (Rate 1300)",
            tariff_code="1300",
            customer_class="commercial",
            sub_class="small general service",
            rate_structure="flat",
            effective_date=SEED_SMALL_GENERAL["effective_date"],
            source_url=BUSINESS_URL,
            confidence="high",
            eligibility="Commercial customers with annual peak demand under 35 kW",
            demand_max_kw=35,
            notes="BC Hydro small commercial rate -- flat energy charge, no demand charge",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=basic,
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=energy,
                    charge_unit="$/kWh",
                ),
            ],
        )

    def _parse_mgs(self, page_text: str) -> Optional[TariffRecord]:
        """Extract Medium General Service rates from page text."""
        # Isolate the MGS section: after "Medium General Service"
        mgs_section = self._extract_section(
            page_text, "Medium General Service", "Large General Service"
        )
        if not mgs_section:
            # Try without end marker if LGS section doesn't appear
            mgs_section = self._extract_section(
                page_text, "Medium General Service", None
            )
        if not mgs_section:
            self.logger.warning("Could not find MGS section in business page")
            return None

        basic = self._extract_cents_per(mgs_section, "cents per day")
        energy = self._extract_cents_per(mgs_section, "cents per kWh")
        demand = self._extract_dollar_per(mgs_section, r"\$\s*([\d.]+)\s*per\s*kW\b")

        if basic is None or energy is None or demand is None:
            self.logger.warning(
                "Could not extract MGS rates (basic=%s, energy=%s, demand=%s)",
                basic, energy, demand,
            )
            return None

        self.logger.info(
            "Parsed MGS: basic=%.4f, energy=%.4f, demand=%.2f",
            basic, energy, demand,
        )

        return TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Medium General Service (Rate 1500)",
            tariff_code="1500",
            customer_class="commercial",
            sub_class="medium general service",
            rate_structure="demand",
            effective_date=SEED_MEDIUM_GENERAL["effective_date"],
            source_url=BUSINESS_URL,
            confidence="high",
            eligibility="Commercial customers with annual peak demand between 35 and 150 kW",
            demand_max_kw=150,
            notes="BC Hydro medium commercial rate with demand charge; served at secondary voltage",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=basic,
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=demand,
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to highest 15-minute demand average per billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=energy,
                    charge_unit="$/kWh",
                ),
            ],
        )

    def _parse_lgs(self, page_text: str) -> Optional[TariffRecord]:
        """Extract Large General Service rates from page text."""
        # Isolate the LGS section: after "Large General Service" until end or next section
        lgs_section = self._extract_section(
            page_text, "Large General Service", "Declaration of Eligibility"
        )
        if not lgs_section:
            lgs_section = self._extract_section(
                page_text, "Large General Service", None
            )
        if not lgs_section:
            self.logger.warning("Could not find LGS section in business page")
            return None

        basic = self._extract_cents_per(lgs_section, "cents per day")
        energy = self._extract_cents_per(lgs_section, "cents per kWh")
        demand = self._extract_dollar_per(lgs_section, r"\$\s*([\d.]+)\s*per\s*kW\b")

        if basic is None or energy is None or demand is None:
            self.logger.warning(
                "Could not extract LGS rates (basic=%s, energy=%s, demand=%s)",
                basic, energy, demand,
            )
            return None

        self.logger.info(
            "Parsed LGS: basic=%.4f, energy=%.4f, demand=%.2f",
            basic, energy, demand,
        )

        return TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Large General Service (Rate 1600)",
            tariff_code="1600",
            customer_class="commercial",
            sub_class="large general service",
            rate_structure="demand",
            effective_date=SEED_LARGE_GENERAL["effective_date"],
            source_url=BUSINESS_URL,
            confidence="high",
            eligibility="Commercial customers with annual peak demand of at least 150 kW, or using more than 550,000 kWh/year",
            demand_min_kw=150,
            notes="BC Hydro large commercial rate with demand charge; higher demand rate, lower energy rate than MGS",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=basic,
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=demand,
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to highest 15-minute demand average per billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=energy,
                    charge_unit="$/kWh",
                ),
            ],
        )

    # ── Text extraction helpers ───────────────────────────────

    @staticmethod
    def _extract_section(
        text: str,
        start_marker: str,
        end_marker: Optional[str],
    ) -> Optional[str]:
        """
        Extract the rate-bearing slice between start_marker and end_marker
        (case-insensitive). The page repeats these service headers in a
        summary/navigation list, so pick the occurrence whose following text
        actually introduces a rate block ("cents per" / "per kW"), not the first.
        """
        lower = text.lower()
        marker = start_marker.lower()

        start_idx = -1
        pos = 0
        while True:
            idx = lower.find(marker, pos)
            if idx == -1:
                break
            window = lower[idx:idx + 600]
            if "cents per" in window or "per kw" in window:
                start_idx = idx
                break
            pos = idx + len(marker)

        if start_idx == -1:
            start_idx = lower.find(marker)
            if start_idx == -1:
                return None

        content_start = start_idx + len(start_marker)
        if end_marker:
            end_idx = lower.find(end_marker.lower(), content_start)
            if end_idx != -1:
                return text[content_start:end_idx]
        return text[content_start:]

    @staticmethod
    def _extract_cents_per(text: str, unit_pattern: str) -> Optional[float]:
        """
        Find the first occurrence of "XX.XX <unit_pattern>" and return
        the value converted to dollars.

        Example: _extract_cents_per(text, "cents per day") finds
        "23.44 cents per day" and returns 0.2344.
        """
        pattern = rf"([\d]+\.?\d*)\s*{re.escape(unit_pattern)}"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1)) / 100.0
        return None

    @staticmethod
    def _extract_dollar_per(text: str, pattern: str) -> Optional[float]:
        """
        Find a dollar amount matching the given regex pattern.
        The pattern should have one capture group for the numeric value.

        Example: _extract_dollar_per(text, r"\\$\\s*([\\d.]+)\\s*per\\s*kW")
        finds "$6.07 per kW" and returns 6.07.
        """
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    @staticmethod
    def _extract_step_rate(page_text: str, step: int) -> Optional[float]:
        """
        Extract the energy rate for a given step/tier from residential page text.

        Matches the current "Tier N XX.XX cents per kWh" wording as well as the
        older "Step N" phrasing.
        """
        pattern = rf"(?:step|tier)\s*{step}\s+([\d]+\.?\d*)\s*cents\s*(?:per|/)\s*kWh"
        match = re.search(pattern, page_text, re.IGNORECASE)
        if match:
            return float(match.group(1)) / 100.0
        return None

    # ── Seed / fallback data ──────────────────────────────────

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # -- Residential (Step / Tiered) --
        records.append(TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Residential Service (Rate 1101)",
            tariff_code="1101",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes="BC Hydro two-step residential rate. Step 1 applies up to threshold per billing period.",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_day"],
                    charge_unit="$/day",
                    notes="Daily basic charge regardless of consumption",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Step 1 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["step1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_RESIDENTIAL["step1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="Applies to first 1,350 kWh per ~2-month billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Step 2 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["step2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_RESIDENTIAL["step1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="Applies to all kWh above the Step 1 threshold",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Rate Rider -- Deferral Account Rate Rider",
                    charge_value=SEED_RESIDENTIAL["rider"],
                    charge_unit="fraction",
                    confidence="medium",
                    notes="Approximately -1.5% credit; check BC Hydro tariff supplement for current value",
                ),
            ],
        ))

        # -- Small General Service (Rate 1300) -- flat, NO demand charge --
        records.append(TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Small General Service (Rate 1300)",
            tariff_code="1300",
            customer_class="commercial",
            sub_class="small general service",
            rate_structure="flat",
            effective_date=SEED_SMALL_GENERAL["effective_date"],
            source_url=SEED_SMALL_GENERAL["source_url"],
            confidence="high",
            eligibility="Commercial customers with annual peak demand under 35 kW",
            demand_max_kw=35,
            notes="BC Hydro small commercial rate -- flat energy charge, no demand charge",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_SMALL_GENERAL["basic_charge_per_day"],
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_SMALL_GENERAL["energy_rate"],
                    charge_unit="$/kWh",
                ),
            ],
        ))

        # -- Medium General Service (Rate 1500) -- has demand charge --
        records.append(TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Medium General Service (Rate 1500)",
            tariff_code="1500",
            customer_class="commercial",
            sub_class="medium general service",
            rate_structure="demand",
            effective_date=SEED_MEDIUM_GENERAL["effective_date"],
            source_url=SEED_MEDIUM_GENERAL["source_url"],
            confidence="high",
            eligibility="Commercial customers with annual peak demand between 35 and 150 kW",
            demand_max_kw=150,
            notes="BC Hydro medium commercial rate with demand charge; served at secondary voltage",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_MEDIUM_GENERAL["basic_charge_per_day"],
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_MEDIUM_GENERAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to highest 15-minute demand average per billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_MEDIUM_GENERAL["energy_rate"],
                    charge_unit="$/kWh",
                ),
            ],
        ))

        # -- Large General Service (Rate 1600) -- higher demand, lower energy --
        records.append(TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Large General Service (Rate 1600)",
            tariff_code="1600",
            customer_class="commercial",
            sub_class="large general service",
            rate_structure="demand",
            effective_date=SEED_LARGE_GENERAL["effective_date"],
            source_url=SEED_LARGE_GENERAL["source_url"],
            confidence="high",
            eligibility="Commercial customers with annual peak demand of at least 150 kW, or using more than 550,000 kWh/year",
            demand_min_kw=150,
            notes="BC Hydro large commercial rate with demand charge; higher demand rate, lower energy rate than MGS",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_LARGE_GENERAL["basic_charge_per_day"],
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_LARGE_GENERAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to highest 15-minute demand average per billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_LARGE_GENERAL["energy_rate"],
                    charge_unit="$/kWh",
                ),
            ],
        ))

        return records
