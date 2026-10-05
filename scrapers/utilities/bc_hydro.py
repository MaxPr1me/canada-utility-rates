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
  - Standard service charges (Terms and Conditions Section 11), as a separate record

Residential and General Service prices, dates and riders come from the approved
Electric Tariff PDF; the product/business web pages are discovery references.

NOTE: BC Hydro redirects www.bchydro.com to app.bchydro.com.
"""

from __future__ import annotations

import re
import logging
from dataclasses import replace
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    extract_pdf_pages, extract_effective_date, DocumentPage,
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
        self._tariff_pages: Optional[list[DocumentPage]] = None

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
            return self._parse_residential_tariff(self._tariff_document())
        except Exception as exc:
            self.logger.warning("Could not parse BC Hydro residential tariff: %s", exc)
            return []

    def _tariff_document(self) -> list[DocumentPage]:
        if self._tariff_pages is None:
            self._tariff_pages = extract_pdf_pages(self.fetch_bytes(TARIFF_URL))
        return self._tariff_pages

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
        """Parse non-industrial General Service schedules and standard charges from the approved tariff."""
        try:
            records = self._parse_business_tariff(self._tariff_document())
        except Exception as exc:
            self.logger.warning("Could not parse BC Hydro business tariff: %s", exc)
            return None
        return records or None

    def _parse_business_tariff(self, pages: list[DocumentPage]) -> list[TariffRecord]:
        sections: dict[str, list[DocumentPage]] = {}
        for page in pages:
            header = re.match(
                r"BC Hydro Rate Schedules? (1300|1500|1600|1901|1904)\b(?:, \d{4}, \d{4}, \d{4})? \u2013", page.text,
            )
            if header:
                sections.setdefault(header.group(1), []).append(page)

        today = self.now_iso()[:10]

        def schedule(code: str) -> tuple[str, str, str]:
            selected = sections.get(code, [])
            if not selected:
                raise ValueError(f"Missing RS {code}")
            dates = {extract_effective_date(page.text.split("Section", 1)[0]) for page in selected}
            if len(dates) != 1 or None in dates or next(iter(dates)) > today:
                raise ValueError(f"Missing, ambiguous or future RS {code} date")
            detail = f"Electric Tariff RS {code}; PDF pages " + ", ".join(str(page.page_number) for page in selected)
            return re.sub(r"\s+", " ", "\n".join(page.text for page in selected)), next(iter(dates)), detail

        riders: Optional[list[RateComponent]] = []
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
                    notes="Applies to all charges under the General Service schedules, before taxes and levies.",
                ))
        except ValueError as exc:
            self.logger.warning("Incomplete BC Hydro business riders: %s", exc)
            riders = None

        cent = r"[\u00a2\u023c\ufffd]"
        power_factor_pages = [page for page in pages if re.match(r"BC Hydro Terms and Conditions, Section 7\b", page.text)
                      and re.search(r"Page 7-[12]\b", page.text.split("7. LOAD CHANGES", 1)[0])]
        power_factor: Optional[list[RateComponent]] = None
        if len(power_factor_pages) == 2 and {page.page_number for page in power_factor_pages} == {53, 54}:
            section = re.sub(r"\s+", " ", " ".join(page.text for page in sorted(power_factor_pages, key=lambda page: page.page_number)))
            dates = {extract_effective_date(page.text.split("Page 7-", 1)[0]) for page in power_factor_pages}
            bands = re.findall(r"Less than (\d+)% (?:but (\d+)% or more )?(\d+)(?=\s|$)", section)
            if (len(dates) == 1 and None not in dates and next(iter(dates)) <= today
                    and "Each Customer must maintain an average Power Factor between 90% lagging and 100%" in section
                    and "to the sum of all charges specified in the Rate section of a Rate Schedule" in section
                    and "No surcharge or credit will apply to any leading Power Factor" in section
                    and re.search(r"90% or more Nil", section)
                    and [(int(upper), int(lower) if lower else None) for upper, lower, _ in bands]
                    == [(90, 88), (88, 85), (85, 80), (80, 75), (75, 70),
                        (70, 65), (65, 60), (60, 55), (55, 50), (50, None)]
                    and all(0 < int(percent) <= 100 for _, _, percent in bands)):
                effective = next(iter(dates))
                power_factor = [RateComponent(
                    "adjustment", "Conditional Power Factor Surcharge", int(percent) / 100, "fraction of Rate section charges",
                    sub_component="conditional", effective_date=effective, source_url=TARIFF_URL,
                    source_detail="Electric Tariff Terms and Conditions section 7.2; PDF pages 53-54",
                    notes=(f"Lagging Power Factor less than {upper}%" + (f" but {lower}% or more" if lower else "")
                           + "; BC Hydro may apply after notification and failure to correct. Not a billing-demand adjustment."),
                ) for upper, lower, percent in bands]
        records: list[TariffRecord] = []
        for code, name, sub_class, structure in (
            ("1300", "Small General Service (Rate 1300)", "small general service", "flat"),
            ("1500", "Medium General Service (Rate 1500)", "medium general service", "demand"),
            ("1600", "Large General Service (Rate 1600)", "large general service", "demand"),
        ):
            if riders is None:
                break
            try:
                if power_factor is None:
                    raise ValueError("Missing or malformed Terms and Conditions section 7.2 power-factor surcharge")
                text, effective, detail = schedule(code)
                family = {"1300": ("1300", "1301", "1310", "1311"),
                          "1500": ("1500", "1501", "1510", "1511"),
                          "1600": ("1600", "1601", "1610", "1611")}[code]
                if any(not re.search(rf"Rate Schedule {member}:", text) for member in family):
                    raise ValueError("Missing voltage/transformation schedule variants")
                if "Rate Schedule 1901" not in text or "Rate Schedule 1904" not in text or "before taxes and levies" not in text:
                    raise ValueError("Missing rider continuation")
                rate_block = re.search(r"Rate Basic Charge:(.*?) Discounts ", text)
                if not rate_block:
                    raise ValueError("Missing rate block")
                rate_text = "Basic Charge:" + rate_block.group(1)

                def amount(pattern: str, label: str) -> float:
                    match = re.search(pattern, rate_text)
                    if not match or float(match.group(1)) <= 0:
                        raise ValueError(f"Missing {label}")
                    return float(match.group(1))

                basic = round(amount(rf"Basic Charge:\s*(\d+(?:\.\d+)?)\s*{cent}\s*per day", "basic charge") / 100.0, 6)
                energy = round(amount(rf"Energy Charge:\s*(\d+(?:\.\d+)?)\s*{cent}\s*per kWh", "energy charge") / 100.0, 6)
                demand = None
                if structure == "demand":
                    demand = amount(r"Demand Charge:\s*\$\s*(\d+(?:\.\d+)?) per kW of Billing Demand", "demand charge")
                elif "Demand Charge" in rate_text:
                    raise ValueError("Unexpected demand charge in small general service")

                primary = re.search(r"A discount of (\d+)(\u00bd)?\s*% will be applied to the above charges if [^.]*?metered at a Primary Voltage", text)
                transformer = re.search(
                    rf"A discount of (\d+(?:\.\d+)?)\s*{cent}\s*per (month|Billing Period) per kW of (?:Billing )?Demand will be applied (?:to the above charges )?if a Customer supplies\s+Transformation",
                    text,
                )
                if not primary or not transformer or "primary voltage will be applied first" not in text.replace("Primary Voltage", "primary voltage"):
                    raise ValueError("Missing discounts")
                primary_fraction = round((int(primary.group(1)) + (0.5 if primary.group(2) else 0.0)) / 100.0, 6)
                transformer_unit = "$/kW/month" if transformer.group(2) == "month" else "$/kW/billing period"

                eligibility = None
                demand_min = demand_max = usage_max = None
                if code == "1300":
                    limit = re.search(r"Demand, metered or estimated by BC Hydro, as applicable, is less than (\d+) kW", text)
                    if not limit:
                        raise ValueError("Missing availability")
                    demand_max = float(limit.group(1))
                    eligibility = f"General Service customers whose Demand, metered or estimated by BC Hydro, is less than {limit.group(1)} kW."
                elif code == "1500":
                    limit = re.search(r"Billing Demand is equal to or greater than (\d+) kW but less than (\d+) kW, and whose Energy consumption in any 12-month period is equal to or less than ([\d,]+) kWh", text)
                    if not limit:
                        raise ValueError("Missing availability")
                    demand_min, demand_max = float(limit.group(1)), float(limit.group(2))
                    usage_max = float(limit.group(3).replace(",", ""))
                    eligibility = (f"General Service customers with Billing Demand of {limit.group(1)} kW or more but less than "
                                   f"{limit.group(2)} kW and Energy consumption in any 12-month period of {limit.group(3)} kWh or less.")
                else:
                    limit = re.search(r"Billing Demand is equal to or greater than (\d+) kW, or whose Energy consumption in any 12 month period is greater than ([\d,]+) kWh", text)
                    if not limit:
                        raise ValueError("Missing availability")
                    demand_min = float(limit.group(1))
                    eligibility = (f"General Service customers with Billing Demand of {limit.group(1)} kW or more, "
                                   f"or Energy consumption in any 12-month period above {limit.group(2)} kWh.")

                minimum = "Minimum Charge: The Basic Charge."
                if structure == "demand":
                    wrapped = r"(?: Minimum| Charge)*"  # side-heading words interleave with the body text
                    if not re.search(rf"50% of the highest Demand Charge billed in any Billing Period wholly{wrapped} within an on-peak period during the immediately preceding{wrapped} 11 Billing{wrapped} Periods", text) \
                            or "November 1" not in text or "March 31" not in text:
                        raise ValueError("Missing minimum charge")
                    minimum = ("Monthly minimum charge is 50% of the highest Demand Charge billed in any Billing Period wholly within an "
                               "on-peak period (November 1 to March 31) during the preceding 11 Billing Periods; a condition, not an added charge.")
                elif not re.search(r"Minimum Charge: The Basic Charge", text):
                    raise ValueError("Missing minimum charge")

                components = [RateComponent("fixed", "Basic Charge", basic, "$/day")]
                if demand is not None:
                    components.append(RateComponent(
                        "demand", "Demand Charge", demand, "$/kW", demand_unit="kW",
                        notes="Per kW of Billing Demand, the highest kW Demand in the Billing Period.",
                    ))
                components.append(RateComponent("energy", "Energy Charge", energy, "$/kWh"))
                components.append(RateComponent(
                    "rebate", "Conditional Primary Voltage Discount", -primary_fraction, "fraction", sub_component="conditional",
                    notes="Applies to the above charges only where supply is metered at Primary Voltage (RS %s01/%s11); applied before the transformation discount." % (code[:2], code[:2]),
                ))
                components.append(RateComponent(
                    "rebate", "Conditional Transformer Ownership Discount", -round(float(transformer.group(1)) / 100.0, 6), transformer_unit,
                    sub_component="conditional", demand_unit="kW",
                    notes="Only where the Customer supplies Transformation (RS %s10/%s11)." % (code[:2], code[:2]),
                ))
                for component in components:
                    component.source_url = TARIFF_URL
                    component.source_detail = detail
                    component.effective_date = effective
                records.append(TariffRecord(
                    utility_name="BC Hydro", province="BC", utility_type="electricity", tariff_name=name,
                    tariff_code=code, customer_class="commercial", sub_class=sub_class, rate_structure=structure,
                    effective_date=max([effective] + [rider.effective_date for rider in riders]),
                    source_url=TARIFF_URL, source_page=detail, eligibility=eligibility,
                    demand_min_kw=demand_min, demand_max_kw=demand_max,
                    usage_max=usage_max, usage_unit="kWh/12 months" if usage_max else None,
                    notes=(f"Covers Rate Schedules {', '.join(family)} (voltage and transformation variants share these prices). "
                           f"{minimum} Rate Riders are shown separately; taxes and levies excluded."),
                    components=components + [replace(rider) for rider in riders] + [replace(component) for component in power_factor],
                ))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete BC Hydro RS %s: %s", code, exc)

        fees = self._parse_standard_charges(pages)
        if fees:
            records.append(fees)
        return records

    def _parse_standard_charges(self, pages: list[DocumentPage]) -> Optional[TariffRecord]:
        today = self.now_iso()[:10]
        components: list[RateComponent] = []
        dates: list[str] = []

        def add(marker: str, specs: list[tuple[str, str, str, str, float]], note: str) -> None:
            for page in pages:
                if not re.match(r"BC Hydro Terms and Conditions, Section 11\b", page.text) or marker not in page.text:
                    continue
                effective = extract_effective_date(page.text.split("Page 11-", 1)[0])
                if not effective or effective > today:
                    return
                text = re.sub(r"\s+", " ", page.text)
                for name, pattern, unit, kind, scale in specs:
                    match = re.search(pattern, text)
                    if not match:
                        continue
                    value = round(float(match.group(1).replace(",", "")) * scale, 6)
                    if value <= 0:
                        continue
                    components.append(RateComponent(
                        kind, name, value, unit, effective_date=effective, source_url=TARIFF_URL,
                        source_detail=f"Terms and Conditions {marker}; PDF page {page.page_number}", notes=note,
                    ))
                    dates.append(effective)
                return

        money = r"\$\s*([\d,]+\.\d\d)"
        add("11.1 Minimum Connection Charges", [
            ("Service Connection Call-Back Charge", rf"Service Connection Call-Back Charge {money}", "$/call-back", "other", 1.0),
        ], "One-time charge per occurrence; excludes taxes.")
        add("11.2 Metering Charges", [
            ("Metering Work - One Meter", rf"One meter Note \d {money}", "$/meter", "other", 1.0),
            ("Metering Work - Concurrent with Service Connection", rf"First and each additional meter Note \d {money}", "$/meter", "other", 1.0),
            ("Instrument Metering (CT and PT)", rf"Instrument metering[^$]*{money}", "$/installation", "other", 1.0),
        ], "One-time metering work charge; applies to services larger than 200 A for instrument metering.")
        add("11.3 Minimum Reconnection Charges", [
            ("Default Reconnection Charge", rf"Default Reconnection Charge: {money} per account", "$/account", "other", 1.0),
            ("Overtime Reconnection Charge", rf"Overtime Reconnection Charge: {money} per account", "$/account", "other", 1.0),
            ("Refused Access Reconnection Charge", rf"Refused Access Reconnection Charge: {money} per Service Connection", "$/service connection", "other", 1.0),
        ], "One-time minimum reconnection charge; excludes taxes.")
        add("11.4 Miscellaneous Standard Charges", [
            ("Account Charge", rf"Account Charge Note \d {money}", "$/account", "other", 1.0),
            ("Late Payment Charge", r"Late Payment Charge Note \d (\d+(?:\.\d+)?)% per month", "fraction/month", "other", 0.01),
            ("Radio-off Meter Charge", rf"Radio-off Meter Charge Note \d {money} per month", "$/month", "other", 1.0),
            ("Radio-off Meter Move Charge", rf"Radio-off Meter Move Charge Note \d {money}", "$/move", "other", 1.0),
        ], "Standard charge; the late payment charge applies to an overdue balance of $30.00 or more.")
        if not components:
            return None
        return TariffRecord(
            utility_name="BC Hydro", province="BC", utility_type="electricity",
            tariff_name="Standard Service Charges (Terms and Conditions Section 11)", tariff_code="T&C-11",
            customer_class="other", sub_class="service fees", rate_structure="flat",
            effective_date=max(dates), source_url=TARIFF_URL,
            source_page="Terms and Conditions Section 11 - Schedule of Standard Charges",
            notes="Standard charges that apply across rate classes under the Terms and Conditions; not recurring energy rates. Connection charges, transformer rental and net metering fees are not modelled.",
            components=components,
        )

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
