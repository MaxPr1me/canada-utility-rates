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

            if any(page.page_number == 1 and page.text.startswith("BC Hydro Electric Tariff, Title Page")
                   for page in self._tariff_document()):
                try:
                    records.extend(self._parse_transmission_tariff(self._tariff_document()))
                except Exception as exc:
                    self.logger.warning("Could not parse BC Hydro transmission tariff: %s", exc)
                try:
                    records.extend(self._parse_net_metering_tariff(self._tariff_document()))
                except Exception as exc:
                    self.logger.warning("Could not parse BC Hydro net metering tariff: %s", exc)
                try:
                    records.extend(self._parse_transmission_pilots(self._tariff_document()))
                except Exception as exc:
                    self.logger.warning("Could not parse BC Hydro transmission pilots: %s", exc)
                try:
                    records.extend(self._parse_self_generation_tariff(self._tariff_document()))
                except Exception as exc:
                    self.logger.warning("Could not parse BC Hydro self-generation tariff: %s", exc)
                try:
                    records.extend(self._parse_community_generation_tariff(self._tariff_document()))
                except Exception as exc:
                    self.logger.warning("Could not parse BC Hydro community generation tariff: %s", exc)

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

    def _parse_transmission_tariff(self, pages: list[DocumentPage]) -> list[TariffRecord]:
        sections: dict[str, list[DocumentPage]] = {}
        for page in pages:
            match = re.match(r"BC Hydro Rate Schedule (1830|1901|1904)\b", page.text)
            if match:
                sections.setdefault(match.group(1), []).append(page)

        def section(code: str, count: int) -> tuple[str, str, str]:
            selected = sections.get(code, [])
            if len(selected) != count or (code == "1830" and
                    {page.page_number for page in selected} != {138, 139, 140}):
                raise ValueError(f"Missing RS {code} continuation")
            dates = {extract_effective_date(page.text.split("Section", 1)[0]) for page in selected}
            if len(dates) != 1 or None in dates or next(iter(dates)) > self.now_iso()[:10]:
                raise ValueError(f"Missing, ambiguous or future RS {code} date")
            detail = f"Electric Tariff RS {code}; PDF pages " + ", ".join(str(page.page_number) for page in selected)
            return re.sub(r"\s+", " ", "\n".join(page.text for page in selected)), next(iter(dates)), detail

        try:
            text, effective, detail = section("1830", 3)
            if not all(phrase in text for phrase in (
                "Availability For all purposes", "Supply is at 60 kV or higher",
                "50% of the Contract Demand", "75% of the highest Billing Demand",
                "initial two Billing Periods", "06:00 to 22:00 Monday to Saturday",
                "Monthly Minimum Charge", "Rate Schedule 1901", "Rate Schedule 1904",
            )):
                raise ValueError("Incomplete RS 1830 availability or billing conditions")
            demand = re.search(r"Demand Charge:\s*\$([\d.]+) per kVA of Billing Demand per Billing Period", text)
            energy = re.search(r"Energy Charge:\s*([\d.]+)\s*[\u00a2\u023c\ufffd] per kWh for all kWh per Billing Period", text)
            minimum = re.search(r"Monthly Minimum Charge:\s*\$([\d.]+) per kVA of Billing Demand", text)
            if not demand or not energy or not minimum or demand.group(1) != minimum.group(1):
                raise ValueError("Incomplete RS 1830 rates or minimum")
            components = [
                RateComponent("demand", "Billing Demand Charge", float(demand.group(1)), "$/kVA/billing period", demand_unit="kVA"),
                RateComponent("energy", "Energy Charge", round(float(energy.group(1)) / 100, 6), "$/kWh"),
            ]
            for component in components:
                component.effective_date = effective
                component.source_url = TARIFF_URL
                component.source_detail = detail
            for code, title in (("1901", "Deferral Account Rate Rider"), ("1904", "Trade Income Rate Rider")):
                rider_text, rider_date, rider_detail = section(code, 1)
                amount = re.search(r"charge equal to\s+(\(?-?\d+(?:\.\d+)?\)?)%", rider_text)
                if not amount or "except for Rate Schedules 2101 and 3817" not in rider_text:
                    raise ValueError(f"Incomplete RS {code} rider")
                raw = amount.group(1)
                percent = -float(raw[1:-1]) if raw.startswith("(") and raw.endswith(")") else float(raw)
                components.append(RateComponent(
                    "rider", f"Rate Rider -- {title}", round(percent / 100, 6), "fraction",
                    effective_date=rider_date, source_url=TARIFF_URL, source_detail=rider_detail,
                    notes="Applies to RS 1830 charges before taxes and levies.",
                ))
            return [TariffRecord(
                utility_name="BC Hydro", province="BC", utility_type="electricity",
                tariff_name="Transmission Service (Rate 1830)", tariff_code="1830",
                customer_class="industrial", sub_class="general transmission service", rate_structure="demand",
                effective_date=max(component.effective_date for component in components),
                source_url=TARIFF_URL, source_page=detail,
                eligibility="All customers supplied at 60 kV or higher in the applicable Integrated Service Area; former RS 1823 customers move at the billing year starting nearest April 1, 2026.",
                notes="Billing Demand is the greatest of HLH kVA, 75% of the preceding November-February plant maximum, or 50% of contract demand; new customers use the daily-highest average for the first two billing periods. HLH is 06:00-22:00 Monday-Saturday except statutory holidays. Monthly minimum is the demand charge, not an additional charge. Transmission supply terms are in Electric Tariff Supplements 5/6 or 87/88.",
                components=components,
            )]
        except ValueError as exc:
            self.logger.warning("Incomplete BC Hydro RS 1830: %s", exc)
            return []

    def _parse_net_metering_tariff(self, pages: list[DocumentPage]) -> list[TariffRecord]:
        selected = [page for page in pages if re.match(r"BC Hydro Rate Schedule 1289\b", page.text)]
        if len(selected) != 9 or {page.page_number for page in selected} != set(range(223, 232)):
            return []
        dates = {extract_effective_date(page.text.split("Section", 1)[0]) for page in selected}
        if len(dates) != 1 or None in dates or next(iter(dates)) > self.now_iso()[:10]:
            return []
        text = re.sub(r"\s+", " ", "\n".join(page.text for page in sorted(selected, key=lambda page: page.page_number)))
        if not all(phrase in text for phrase in (
            "NET METERING SERVICE (CLOSED)", "as of June 30, 2026", "Rate Schedule 2289",
            "Charges for the Customer’s Net Consumption will be in accordance with the Rate Schedule",
            "daily average Mid-Columbia prices for the previous", "average annual exchange rate",
            "not more than 100 kilowatts", "apply any credits in the Generation Account Balance to the Net Consumption",
            "credit the Customer’s Generation Account with the Net Generation",
            "Basic Charge and Demand Charge (if applicable)", "At the Anniversary Date",
            "monthly or bi-monthly under BC Hydro’s regular billing plan",
            "Rate Rider as set out in Rate Schedule 1901", "Rate Rider as set out in Rate Schedule 1904",
        )):
            return []
        effective = next(iter(dates))
        detail = "Electric Tariff RS 1289; PDF pages 223-231"
        return [TariffRecord(
            utility_name="BC Hydro", province="BC", utility_type="electricity",
            tariff_name="Net Metering Generation Credit (Rate 1289, Closed)", tariff_code="1289",
            customer_class="other", sub_class="conditional net metering adjustment", rate_structure="other",
            effective_date=effective, source_url=TARIFF_URL, source_page=detail,
            eligibility="Only customers continuously on RS 1289 since June 30, 2026, with an eligible generating facility no larger than 100 kW and an active base service on the regular monthly or bi-monthly billing plan; customers transition to RS 2289 upon termination.",
            notes="Each billing period net generation is credited in kWh to the generation account and applied against later net consumption; the underlying rate schedule's basic and applicable demand charges remain payable. At the anniversary date or termination, remaining generation is purchased at a customer-independent annual formula based on prior-year daily average Mid-Columbia prices and Bank of Canada annual exchange rate; no published fixed cash price is implied here. Not a replacement retail energy price or an automatic cash rebate.",
            components=[RateComponent(
                "rebate", "Conditional Net Generation Account Credit", -1.0,
                "kWh credit/kWh net generation", sub_component="conditional",
                effective_date=effective, source_url=TARIFF_URL, source_detail=detail,
                notes="One kWh of net generation adds one kWh to the generation account; later net consumption draws down this balance. Cash settlement has a separate variable annual price, not this component.",
            )],
        )]

    def _numbered_section(self, pages: list[DocumentPage], code: str, section: int, count: int) -> tuple[str, str, str]:
        """Return one schedule's text only when every numbered continuation page is present and dated."""
        selected = sorted((page for page in pages if re.match(rf"BC Hydro Rate Schedule {code}\b", page.text)),
                          key=lambda page: page.page_number)
        labels = [re.search(rf"Section {section}-{code} [\u2013-] Page (\d+)\b", page.text[:200]) for page in selected]
        if (len(selected) != count or any(label is None for label in labels)
                or [int(label.group(1)) for label in labels] != list(range(1, count + 1))
                or [page.page_number for page in selected] != list(range(selected[0].page_number, selected[0].page_number + count))):
            raise ValueError(f"Missing RS {code} continuation")
        dates = {extract_effective_date(page.text.split("Section", 1)[0]) for page in selected}
        if len(dates) != 1 or None in dates or next(iter(dates)) > self.now_iso()[:10]:
            raise ValueError(f"Missing, ambiguous or future RS {code} date")
        first, last = selected[0].page_number, selected[-1].page_number
        detail = f"Electric Tariff RS {code}; PDF page{'s' if count > 1 else ''} {first}" + (f"-{last}" if count > 1 else "")
        return re.sub(r"\s+", " ", "\n".join(page.text for page in selected)), next(iter(dates)), detail

    def _parse_transmission_pilots(self, pages: list[DocumentPage]) -> list[TariffRecord]:
        """Optional RS 2801/2802/2821/2822 pilots offered in place of RS 1830; each fails closed independently."""
        cent = r"\s*[\u00a2\u023c\ufffd]\s*per kWh"
        riders: list[RateComponent] = []
        try:
            for code, title in (("1901", "Deferral Account Rate Rider"), ("1904", "Trade Income Rate Rider")):
                text, effective, detail = self._numbered_section(pages, code, 6, 1)
                amount = re.search(r"charge equal to\s+(\(?-?\d+(?:\.\d+)?\)?)%", text)
                if not amount or "except for Rate Schedules 2101 and 3817" not in text:
                    raise ValueError(f"Incomplete RS {code} rider")
                raw = amount.group(1)
                percent = -float(raw[1:-1]) if raw.startswith("(") and raw.endswith(")") else float(raw)
                riders.append(RateComponent(
                    "rider", f"Rate Rider -- {title}", round(percent / 100, 6), "fraction",
                    effective_date=effective, source_url=TARIFF_URL, source_detail=detail,
                    notes="Applies to all charges payable under the pilot schedule, before taxes and levies.",
                ))
        except ValueError as exc:
            self.logger.warning("BC Hydro transmission pilot riders unavailable: %s", exc)
            return []

        winter = "Four billing periods from the one commencing nearest November 1"
        on_peak_hours = "16:00-20:00 Winter Period weekdays, excluding statutory holidays"
        periods = {
            "Winter On-Peak Period": ("Winter On-Peak Energy Charge", "winter on-peak", on_peak_hours, "winter", winter),
            "Winter Off-Peak Period": ("Winter Off-Peak Energy Charge", "winter off-peak", "All other Winter Period hours", "winter", winter),
            "Spring Period": ("Spring Energy Charge", None, None, "spring", "Three billing periods from the one commencing nearest May 1"),
            "Remaining Period": ("Remaining Period Energy Charge", None, None, "remaining", "All billing periods outside the Winter and Spring Periods"),
            "All other kWh": ("All Other Energy Charge", None, None, None, None),
        }
        tou = ["Winter On-Peak Period", "Winter Off-Peak Period", "Spring Period", "Remaining Period"]
        specs = (
            ("2801", 7, "\u2013 TIME-OF-USE", "Transmission Time-of-Use Pilot (Rate 2801)", tou),
            ("2802", 8, "\u2013 TIME-OF-USE WITH MODIFIED WINTER DEMAND",
             "Transmission Time-of-Use with Modified Winter Demand Pilot (Rate 2802)", tou),
            ("2821", 7, "CRITICAL PEAK PRICING", "Transmission Critical Peak Pricing Pilot (Rate 2821)",
             ["Critical Peak Pricing Period", "All other kWh"]),
            ("2822", 8, "\u2013 CRITICAL PEAK PRICING WITH TIME-OF-USE",
             "Transmission Critical Peak Pricing with Time-of-Use Pilot (Rate 2822)", ["Critical Peak Pricing Period"] + tou),
        )
        records: list[TariffRecord] = []
        for code, count, title, name, labels in specs:
            try:
                text, effective, detail = self._numbered_section(pages, code, 5, count)
                required = [
                    "Rate Schedule 1830 or are eligible to take Service under Rate Schedule 1830",
                    "is a pilot effective until March 31, 2030", "Supply is at 60 kV or higher",
                    "This Rate Schedule will terminate effective March 31, 2030",
                    "The Pilot Period is April 1, 2026, to March 31, 2030", "completed enrollment form by March 19",
                    "BC Hydro will provide a bill guarantee",
                    f"may not participate in the Industrial Load Curtailment (ILC) Program while taking service under Rate Schedule {code}",
                    "50% of the Contract Demand", "06:00 to 22:00 Monday to Saturday",
                    "four Billing Periods starting with the first day of the Billing Period that commences nearest to November 1",
                ]
                if "Spring Period" in labels:
                    required.append("three Billing Periods starting with the first day of the Billing Period that commences nearest to May 1")
                if "Winter On-Peak Period" in labels and not re.search(r"hours from 16:00 to 20:00 during (?:the )?Winter Period weekdays", text):
                    raise ValueError("Missing Winter On-Peak hours")
                if "Critical Peak Pricing Period" in labels:
                    required += ["up to 15 Critical Peak Pricing events over the Winter Period and each event is from 16:00 to 20:00 on Winter Period weekdays",
                                 "day ahead notification"]
                if code == "2802":
                    required.append("hours from 6:00 to 16:00 and 20:00 to 22:00 during the Winter Period weekdays")
                missing = [phrase for phrase in required if phrase not in text]
                if (missing or not re.search(rf"RATE SCHEDULE {code} \u2013 TRANSMISSION SERVICE {title} Availability", text)
                        or any(not re.search(rf"Rate Schedule {rider} applies to all charges payable under this Rate Schedule, before taxes and levies", text)
                               for rider in ("1901", "1904"))):
                    raise ValueError(f"Incomplete availability, definitions or riders: {missing}")
                block = re.search(r" (Rate (?:Winter )?Demand Charges?:.*?) Definitions 1\. Billing Year", text)
                if not block:
                    raise ValueError("Missing rate block")
                rate = block.group(1)

                components: list[RateComponent] = []
                if code == "2802":
                    demand = re.search(
                        r"Rate Winter Demand Charges: \$([\d.]+) per kVA of Winter On-Peak Billing Demand per Billing Period "
                        r"plus \$([\d.]+) per kVA of Winter Non-Peak Billing Demand per Billing Period "
                        r"or Non-Winter Demand Charge: \$([\d.]+) per kVA of Non-Winter Billing Demand per Billing Period", rate)
                    if not demand:
                        raise ValueError("Missing seasonal demand charges")
                    components += [
                        RateComponent("demand", "Winter On-Peak Billing Demand Charge", float(demand.group(1)), "$/kVA/billing period",
                                      demand_unit="kVA", season="winter", season_months=winter, tou_period="winter on-peak", tou_hours=on_peak_hours,
                                      notes="Winter Period only, together with the Winter Non-Peak demand charge; highest kVA in Winter On-Peak hours."),
                        RateComponent("demand", "Winter Non-Peak Billing Demand Charge", float(demand.group(2)), "$/kVA/billing period",
                                      demand_unit="kVA", season="winter", season_months=winter, tou_period="winter non-peak",
                                      tou_hours="06:00-16:00 and 20:00-22:00 Winter Period weekdays, excluding statutory holidays",
                                      notes="Winter Period only; greatest of the period's highest kVA, 75% of prior November-February Winter Non-Peak billing demand, or 50% of contract demand."),
                        RateComponent("demand", "Non-Winter Billing Demand Charge", float(demand.group(3)), "$/kVA/billing period",
                                      demand_unit="kVA", season="non-winter", season_months="All billing periods outside the Winter Period",
                                      notes="Alternative to the two Winter demand charges, applying only outside the Winter Period; HLH kVA with the RS 1830-style ratchet."),
                    ]
                else:
                    demand = re.search(r"Rate Demand Charge: \$([\d.]+) per kVA of Billing Demand per Billing Period", rate)
                    if not demand:
                        raise ValueError("Missing demand charge")
                    components.append(RateComponent("demand", "Billing Demand Charge", float(demand.group(1)), "$/kVA/billing period", demand_unit="kVA"))
                minimum = re.search(r"Monthly Minimum Charge: \$([\d.]+) per kVA of Billing Demand", rate)
                if (code == "2821") != bool(minimum) or (minimum and minimum.group(1) != demand.group(1)):
                    raise ValueError("Unexpected or inconsistent monthly minimum")

                energy = re.findall(rf"(\d)\. ([A-Z][A-Za-z -]*?) (\d+\.\d+){cent}", rate)
                if [label for _, label, _ in energy] != labels or [int(number) for number, _, _ in energy] != list(range(1, len(labels) + 1)):
                    raise ValueError("Missing or changed energy periods")
                for _, label, amount in energy:
                    value = round(float(amount) / 100, 6)
                    if label == "Critical Peak Pricing Period":
                        components.append(RateComponent(
                            "energy", "Critical Peak Pricing Energy Charge", value, "$/kWh", sub_component="conditional",
                            tou_period="critical peak", season="winter", season_months=winter,
                            tou_hours="16:00-20:00 on BC Hydro-called Winter Period weekdays (up to 15 events; day-ahead email notice)",
                            notes="Applies only to kWh in called events. Published as its own energy-period price, not as a surcharge on another period price.",
                        ))
                        continue
                    component_name, period, hours, season, months = periods[label]
                    components.append(RateComponent("energy", component_name, value, "$/kWh", tou_period=period, tou_hours=hours,
                                                    season=season, season_months=months))
                if any(component.charge_value <= 0 for component in components):
                    raise ValueError("Non-positive pilot charge")
                for component in components:
                    component.effective_date = effective
                    component.source_url = TARIFF_URL
                    component.source_detail = detail
                minimum_note = " Monthly minimum equals the demand charge on Billing Demand; it is a floor, not an added charge." if code == "2821" else ""
                records.append(TariffRecord(
                    utility_name="BC Hydro", province="BC", utility_type="electricity", tariff_name=name, tariff_code=code,
                    customer_class="industrial", sub_class="optional transmission pilot (conditional enrollment)", rate_structure="mixed",
                    effective_date=max([effective] + [rider.effective_date for rider in riders]), end_date="2030-03-31",
                    source_url=TARIFF_URL, source_page=detail,
                    eligibility=("Optional pilot (April 1, 2026 to March 31, 2030) for customers taking, or eligible for, RS 1830 Transmission Service at 60 kV or higher "
                                 "in the Integrated Service Area excluding Kingsgate-Yahk and Lardeau-Shutty Bench; not available with RS 1828, 1894 or 1895. "
                                 "Requires an enrollment form (March 19 for 2026, March 1 later), starts at the Billing Year for a multi-year term, and excludes ILC participation."),
                    notes=("Pilot alternative to RS 1830, not an adjustment to it. Billing demand uses HLH kVA (06:00-22:00 Monday-Saturday except statutory holidays) "
                           "with 75%/50% ratchets. A one-time first-year bill guarantee refunds any excess over RS 1830 billing; it is conditional and not modelled. "
                           "Self-generators face RS 1880 restrictions in peak periods. Riders shown separately; taxes excluded." + minimum_note),
                    components=components + [replace(rider) for rider in riders],
                ))
            except ValueError as exc:
                self.logger.warning("Incomplete BC Hydro RS %s: %s", code, exc)
        return records

    def _parse_self_generation_tariff(self, pages: list[DocumentPage]) -> list[TariffRecord]:
        try:
            text, effective, detail = self._numbered_section(pages, "2289", 6, 4)
        except ValueError as exc:
            self.logger.warning("Incomplete BC Hydro RS 2289: %s", exc)
            return []
        price = re.search(r"Energy Price: BC Hydro will pay an Energy Price of (\d+(?:\.\d+)?)\s*[\u00a2\u023c\ufffd] per kWh for all Net Generation", text)
        if not price or float(price.group(1)) <= 0 or not all(phrase in text for phrase in (
            "RATE SCHEDULE 2289 \u2013 SELF-GENERATION SERVICE", "For Customers taking Service at distribution voltage who",
            "accepted by BC Hydro in writing and have received Interconnection Approval",
            "not available to Customer Premises taking Service under Rate Schedules 1253, 1268, 1289 or 2290",
            "aggregated nameplate rating of not more than 100 kW",
            "Net Generation Credit is the Net Generation during each billing period multiplied by the Energy Price",
            "BC Hydro will credit the Customer\u2019s bill by the Net Generation Credit",
            "responsible for paying any balance owing", "credit balance on April 30 each year",
        )):
            self.logger.warning("Incomplete BC Hydro RS 2289 price or credit rules")
            return []
        return [TariffRecord(
            utility_name="BC Hydro", province="BC", utility_type="electricity",
            tariff_name="Self-Generation Net Generation Credit (Rate 2289)", tariff_code="2289",
            customer_class="other", sub_class="conditional self-generation credit", rate_structure="other",
            effective_date=effective, source_url=TARIFF_URL, source_page=detail,
            eligibility=("Distribution-voltage customers with an accepted application and Interconnection Approval for an on-site or adjacent clean or renewable "
                         "Generating Facility of no more than 100 kW nameplate (or 100 kW per phase net injection limit); not for premises on RS 1253, 1268, 1289 or 2290."),
            notes=("Credit for electricity delivered to BC Hydro in each billing period, applied to the customer's bill; consumption stays billed under the "
                   "customer's own rate schedule. Not a replacement retail energy price or a savings estimate. Credit balances may be carried forward, "
                   "transferred, or paid out (on request above $50; any balance on April 30). No rate riders are attached to this payment."),
            components=[RateComponent(
                "rebate", "Conditional Net Generation Credit", -round(float(price.group(1)) / 100, 6), "$/kWh net generation",
                sub_component="conditional", effective_date=effective, source_url=TARIFF_URL, source_detail=detail,
                notes="Per kWh of net generation delivered to BC Hydro, not per kWh consumed.",
            )],
        )]

    def _parse_community_generation_tariff(self, pages: list[DocumentPage]) -> list[TariffRecord]:
        try:
            text, effective, detail = self._numbered_section(pages, "2290", 6, 11)
        except ValueError as exc:
            self.logger.warning("Incomplete BC Hydro RS 2290: %s", exc)
            return []
        price = re.search(r"Community Energy Price: BC Hydro will pay a Community Energy Price of (\d+(?:\.\d+)?)\s*[\u00a2\u023c\ufffd] per kWh for all Net Generation", text)
        if not price or float(price.group(1)) <= 0 or not all(phrase in text for phrase in (
            "RATE SCHEDULE 2290 \u2013 COMMUNITY GENERATION SERVICE", "For Customers taking Service at distribution voltage who",
            "new Shared Generating Facility to generate Electricity on or after July 1, 2026",
            "accepted by BC Hydro in writing and received Interconnection Approval",
            "not available to any Premises where Service is already provided under Rate Schedule 1253, 1268, 1289 or 2289",
            "Who holds an account for Residential Service or General Service",
            "Community Generation Credit is the Net Generation during each billing period multiplied by the Energy Price",
            "(a) 50% if the Shared Generating Facility has four or fewer", "(c) 10% if the Shared Generating Facility has 10 or more",
            "multiplied by 24 kW", "multiplied by 100 kW", "(b) A 2 MW injection limit at the Point of Delivery",
            "BC Hydro may charge a fee for the Community Generation Credit Billing Service",
            "not entitled to any credit or payments for Electricity delivered to BC Hydro in excess of its Shared Generating Facility\u2019s Maximum Injection Limit",
        )):
            self.logger.warning("Incomplete BC Hydro RS 2290 price, allocation or injection rules")
            return []
        return [TariffRecord(
            utility_name="BC Hydro", province="BC", utility_type="electricity",
            tariff_name="Community Generation Credit (Rate 2290)", tariff_code="2290",
            customer_class="other", sub_class="conditional community generation credit", rate_structure="other",
            effective_date=effective, source_url=TARIFF_URL, source_page=detail,
            eligibility=("Distribution-voltage Community Generator Customers with an accepted application and Interconnection Approval for a new "
                         "clean or renewable Shared Generating Facility in service on or after July 1, 2026; injection limited to the lesser of 24 kW per "
                         "benefitting Residential account plus 100 kW per benefitting General Service account, or 2 MW. Not for premises on RS 1253, 1268, "
                         "1289 or 2289; benefitting accounts must be Residential or General Service and not on RS 1289/2289."),
            notes=("Credit for net generation delivered to BC Hydro, recorded in a Community Generation Account and applied to the generator's bill "
                   "or, under the optional Credit Billing Service, allocated to benefitting accounts (maximum 50%/25%/10% per account for 1-4/5-9/10+ accounts). "
                   "Benefitting customers' consumption stays billed under their own rate schedules; this is not a replacement retail energy price or a "
                   "savings estimate. The optional Credit Billing Service fee and any generator-authorized deductions are unpublished and not modelled. "
                   "No credit above the Maximum Injection Limit. No rate riders are attached to this payment."),
            components=[RateComponent(
                "rebate", "Conditional Community Generation Credit", -round(float(price.group(1)) / 100, 6), "$/kWh net generation",
                sub_component="conditional", effective_date=effective, source_url=TARIFF_URL, source_detail=detail,
                notes="Per kWh of net generation delivered to BC Hydro within the Maximum Injection Limit, not per kWh consumed.",
            )],
        )]

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
