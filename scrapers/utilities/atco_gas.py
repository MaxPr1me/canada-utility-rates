"""
atco_gas.py — Scraper for ATCO Gas distribution rates (Alberta).

ATCO Gas distributes natural gas in Alberta's North and South service
territories. Its AUC-approved rate schedules are republished in place as one
PDF per territory. Gas supply is bought separately: customers without a
retailer contract are served by the default supply provider, Direct Energy
Regulated Services (DERS), at its monthly default rate tariff (DSP Rider F).

Official sources:
  https://gas.atco.com/content/dam/atco-gas-website/en-ca/assets/understanding-rates/documents/north-rate-schedule.pdf
  https://gas.atco.com/content/dam/atco-gas-website/en-ca/assets/understanding-rates/documents/south-rate-schedule.pdf
      (linked from https://gas.atco.com/en-ca/understanding-rates/how-rates-are-set.html, a JS-rendered page)
  https://www.directenergy.ca/en/regulated/residential-natural-gas-rates   (DERS monthly default rate)
  https://www.directenergy.ca/en/regulated/commercial-natural-gas-rates
  https://ucahelps.alberta.ca/utility-choices/current-rates-and-pricing/default-rates/  (required cross-check)
  https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/fcrates/fuel-charge-rates.html

Each class fails closed on its own: a missing page, unit, date or rider value
drops only that class. Irrigation, producer receipt and unmetered gas light
service are outside the building scope and are never emitted.

Regulated by the Alberta Utilities Commission (AUC).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional, Union

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

logger = logging.getLogger(__name__)

ATCO_DOCUMENTS = "https://gas.atco.com/content/dam/atco-gas-website/en-ca/assets/understanding-rates/documents/"
LANDING_URL = "https://gas.atco.com/en-ca/understanding-rates/how-rates-are-set.html"
# The approved PDFs are authoritative; the rendered web summary has disagreed with them
# (South Ultra High Use fixed charge 8.475 on the web vs 8.457 in the PDF, October 2026).
SCHEDULE_URLS = {
    "North": ATCO_DOCUMENTS + "north-rate-schedule.pdf",
    "South": ATCO_DOCUMENTS + "south-rate-schedule.pdf",
}
PAGE_URLS = {
    "ders_residential": "https://www.directenergy.ca/en/regulated/residential-natural-gas-rates",
    "ders_commercial": "https://www.directenergy.ca/en/regulated/commercial-natural-gas-rates",
    "uca": "https://ucahelps.alberta.ca/utility-choices/current-rates-and-pricing/default-rates/",
    "carbon": (
        "https://www.canada.ca/en/revenue-agency/services/forms-publications/"
        "publications/fcrates/fuel-charge-rates.html"
    ),
}

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
DATE = r"[A-Z][a-z]+ \d{1,2}, \d{4}"
GCFR_SENTENCE = ("our regulated rate for natural gas is called the Gas Cost Flow-Through Rate (GCFR) and "
                 "fluctuates each month")
DRT_RETAILER, DRT_DISTRIBUTOR = "Direct Energy Regulated Services", "ATCO Gas"
DRT_NAME = "Default Supply Gas Charge (DERS Rider F)"

RIDER_NAMES = {
    "L": "Load Balancing Deferral Account Rider",
    "T": "Transmission Service Charge",
    "W": "Weather Deferral Account Rider",
}
RIDER_HEADINGS = {
    "L": r'RIDER "L" TO ALL RATES FOR CREDITING OR DEBITING LOAD BALANCING DEFERRAL ACCOUNT \(LBDA\) BALANCES',
    "T": r'RIDER "T" TRANSMISSION SERVICE CHARGE',
    "W": r'RIDER "W" WEATHER DEFERRAL ACCOUNT RIDER',
}
RIDER_E_HEADING = r'RIDER "E" TO DELIVERY SERVICE RATES FOR THE DETERMINATION OF THE "DEEMED VALUE OF NATURAL GAS"'
FOOTER = r"The Company.s Terms and Conditions apply"
HEADER = re.compile(rf"ATCO Gas Effective (?P<date>{DATE})"
                    r"(?: by (?P<ref>(?:AUC )?(?:Decision|Disposition) \d+-D\d+-\d{4}))?")
APPLIES = re.compile(rf"To be applied to (?P<who>.+?) customers unless otherwise specified by specific contracts or "
                     rf"(?:the )?AUC, effective (?P<start>{DATE})(?: to (?P<end>{DATE}))?\.")
L_LABEL = re.compile(r"(?<![\w-])(ATA|Low|Mid|High|Ultra(?:[- ]High)?|Irrigation) Use Delivery Rate")
L_ROW = re.compile(rf"- (?P<start>{DATE}) to (?P<end>{DATE}) \$ ?(?P<value>\(?\d+\.\d+\)?) per (?P<unit>\S+) "
                   r"(?P<sign>Debit|Credit)")
TW_LABEL = re.compile(r"(?<![\w-])(Low Use|Mid Use|High Use|Ultra[- ]High Use|Alternative Technology and Appliance)"
                      r" Delivery (?:Rate|Service)")
TW_ROW = re.compile(r"\$ ?(?P<value>\(?\d+\.\d+\)?) (?P<unit>per .+)")
TW_UNITS = {
    "per GJ": "$/GJ",
    "per GJ per Day of 24 Hr. Billing Demand": "$/GJ/day",
    "per Day per GJ of 24 Hr. Billing Demand": "$/GJ/day",
}
# Class names inside rider applicability sentences.
WHO = {
    "LOW": r"\bLow Use\b",
    "MID": r"\bMid Use\b",
    "HIGH": r"(?<![\w-])(?<!Ultra )High Use\b",
    "UHU": r"\bUltra[- ]High Use\b",
    "ATA": r"\bAlternative Technology and Appliance\b|\(ATA\)",
}
BILLING_DEMAND = re.compile(
    r"The Billing Demand for each billing period shall be the greater of: 1\. Any applicable contract demand, or "
    r"2\. The greatest amount of gas in GJ delivered in any Gas Day \(i\.e\. 8:00 am to 8:00 am\) during the "
    r"current and preceding eleven billing periods provided that the greatest amount of gas delivered in any Gas "
    r"Day in the summer period shall be divided by 2\. 3\. (?P<min>[\d,]+) GJ/day", re.I)
SUMMER_ONLY = ("Provided that for a Customer who elects to take service only during the summer period, the Billing "
               "Demand for each billing period shall be the greatest amount of gas in GJ in any Gas Day in that "
               "billing period.")


@dataclass(frozen=True)
class ClassSpec:
    """One in-scope delivery service published in both territory schedules."""
    key: str
    title: str
    heading: str            # upper-case heading on the class page (case-sensitive)
    customer_class: str
    eligibility: str        # availability sentence, named groups min/max (GJ per year)
    demand: bool = False
    ders_page: Optional[str] = None   # DERS page carrying the default rate; None: DRT does not name the class


_RANGE = (r"Available to all customers using more than (?P<min>[\d,]+) GJ per year but no more than "
          r"(?P<max>[\d,]+) GJ annually\.")
# DERS's DRT schedules (Decision 30807-D01-2026) apply Rider F to Low, Mid and High Use delivery service only.
CLASSES = (
    ClassSpec("LOW", "Low Use Delivery Service", r"LOW USE DELIVERY SERVICE", "residential",
              r"Available to all customers using (?P<max>[\d,]+) GJ per year or less\.", ders_page="residential"),
    ClassSpec("MID", "Mid Use Delivery Service", r"MID USE DELIVERY SERVICE", "commercial", _RANGE,
              ders_page="commercial"),
    ClassSpec("HIGH", "High Use Delivery Service", r"(?<!ULTRA )HIGH USE DELIVERY SERVICE", "commercial", _RANGE,
              demand=True, ders_page="commercial"),
    ClassSpec("UHU", "Ultra High Use Delivery Service", r"ULTRA HIGH USE DELIVERY SERVICE", "industrial",
              r"Available to all customers using more than (?P<min>[\d,]+) GJ (?:per )?year\.", demand=True),
    ClassSpec("ATA", "Alternative Technology and Appliance Delivery Service",
              r"ALTERNATIVE TECHNOLOGY AND APPLIANCE DELIVERY SERVICE", "residential",
              r"Available by request only and at the discretion of the company for use to all customers: "
              r"(?:\S{1,2} )?Using less than (?P<max>[\d,]+) GJ per year, and (?:\S{1,2} )?Have one of the following "
              r"use types: (?:\S{1,2} )?Uses alternative technologies that reduce natural gas space heating load "
              r"including solar thermal, geoexchange, and net zero/near net zero emission homes; or (?:\S{1,2} )?"
              r"Uses natural gas solely for non-space heating purposes\."),
)


class Reject(ValueError):
    """A required fact is missing, inconsistent or out of date; the affected class is not emitted."""


@dataclass(frozen=True)
class _Page:
    number: int
    text: str


@dataclass(frozen=True)
class RiderRow:
    value: float
    unit: str
    start: date
    end: Optional[date]
    page: int
    label: str
    sign: Optional[str] = None


@dataclass
class RiderTable:
    letter: str
    page: Optional[int] = None
    reference: Optional[str] = None
    error: Optional[str] = None
    applies_to: set[str] = field(default_factory=set)
    rows: dict[str, list[RiderRow]] = field(default_factory=dict)
    row_errors: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class DeemedValue:
    """South Rider E: deemed gas value used only to compute the City of Calgary franchise fee."""
    value: float
    effective: date
    page: int
    applies_to: frozenset[str]


@dataclass
class Schedule:
    territory: str
    url: str
    edition: date
    pages: list[_Page]
    index: str
    riders: dict[str, RiderTable]
    rider_e: Optional[DeemedValue]


@dataclass(frozen=True)
class Commodity:
    value: Decimal
    page_key: str
    label: str
    start: date
    end: date


def _flat(text: str) -> str:
    for old, new in (("\u201c", '"'), ("\u201d", '"'), ("\u2018", "'"), ("\u2019", "'"), ("\u2013", "-"),
                     ("\u2014", "-"), ("\u2212", "-"), ("\xa0", " "), ("\u200b", "")):
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


def _date(text: str) -> date:
    try:
        return datetime.strptime(text, "%B %d, %Y").date()
    except ValueError as exc:
        raise Reject(f"unreadable date {text!r}") from exc


def _long(day: date) -> str:
    return f"{MONTHS[day.month - 1]} {day.day}, {day.year}"


def _month_end(day: date) -> date:
    return (day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)


def _amount(text: str) -> float:
    """Dollar amount as printed; parentheses mark a credit."""
    negative = text.startswith("(") and text.endswith(")")
    value = float(text.strip("()"))
    return round(-value if negative else value, 6)


def _int(text: Optional[str]) -> Optional[float]:
    return float(text.replace(",", "")) if text else None


def _class_key(label: str) -> str:
    word = label.split()[0].split("-")[0].casefold()
    return {"ata": "ATA", "alternative": "ATA", "low": "LOW", "mid": "MID", "high": "HIGH", "ultra": "UHU",
            "irrigation": "IRR"}[word]


def _soup_text(soup) -> str:
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    return _flat(soup.get_text(" ", strip=True))


def _grid(table) -> list[list[str]]:
    rows = []
    for tr in table.find_all("tr"):
        cells: list[str] = []
        for cell in tr.find_all(["td", "th"]):
            try:
                span = max(int(cell.get("colspan", 1)), 1)
            except ValueError:
                span = 1
            cells.extend([_flat(cell.get_text(" ", strip=True))] * span)
        if cells:
            rows.append(cells)
    return rows

# Seed data for ATCO Gas South distribution.
SEED_SOUTH = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.atco.com/en-ca/for-home/natural-gas/natural-gas-rates.html",
    "customer_charge_monthly": 34.14,           # $/month
    "variable_distribution": 1.3419,            # $/GJ
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
    "municipal_franchise_fee_pct": 0.0,         # varies by municipality — not included
    "rate_rider": 0.0480,                       # $/GJ — AUC-approved rider
}

# Seed data for ATCO Gas North distribution.
SEED_NORTH = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.atco.com/en-ca/for-home/natural-gas/natural-gas-rates.html",
    "customer_charge_monthly": 37.00,           # $/month
    "variable_distribution": 1.4589,            # $/GJ
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
    "rate_rider": 0.0520,                       # $/GJ — AUC-approved rider
}


class ATCOGasScraper(BaseScraper):
    """Scrape ATCO Gas distribution rates for Alberta (North and South)."""

    def __init__(self):
        super().__init__(utility_name="ATCO Gas", province="AB")
        self.rejections: list[str] = []

    def scrape(self) -> list[TariffRecord]:
        live = self._try_live_scrape()
        if live:
            return live
        self.logger.warning("Live scrape failed — using seed data for ATCO Gas")
        return self.mark_fallback(self._seed_data())

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Fetch both approved schedules and the supply/carbon pages; parse each class independently."""
        documents: dict[str, list[DocumentPage]] = {}
        for territory, url in SCHEDULE_URLS.items():
            try:
                documents[territory] = self._pdf_pages(url)
            except Exception as exc:
                self.logger.warning("ATCO Gas %s rate schedule unavailable: %s", territory, exc)
        if not documents:
            return None
        pages: dict[str, str] = {}
        for key, url in PAGE_URLS.items():
            try:
                pages[key] = self.fetch_page(url)
            except Exception as exc:
                self.logger.warning("ATCO Gas %s page unavailable: %s", key, exc)
        try:
            records = self.parse_sources(documents, pages, self._today())
        except Exception as exc:
            self.logger.warning("ATCO Gas sources could not be parsed: %s", exc)
            return None
        return self.mark_live_parsed(records) if records else None

    def _pdf_pages(self, url: str) -> list[DocumentPage]:
        pages = extract_pdf_pages(self.fetch_bytes(url))
        if not pages:
            raise ValueError("no extractable text")
        return pages

    @staticmethod
    def _today() -> date:
        return datetime.now(timezone.utc).date()

    # ── Parsing ──────────────────────────────────────────────

    def parse_sources(self, documents: dict[str, list[DocumentPage]], pages: dict[str, str],
                      today: Optional[date] = None) -> list[TariffRecord]:
        """Build in-scope classes from schedule pages keyed North/South and pages keyed as PAGE_URLS.

        Missing carbon evidence rejects everything; otherwise each territory and class is isolated.
        Rejection reasons are kept in ``self.rejections``.
        """
        today = today or self._today()
        self.rejections = []
        try:
            carbon = self._carbon(pages.get("carbon", ""), today)
        except Reject as exc:
            self._reject("all classes", exc)
            return []
        supply: dict[str, Union[Commodity, Reject]] = {}
        for page_key in ("residential", "commercial"):
            try:
                supply[page_key] = self._commodity(pages.get(f"ders_{page_key}", ""), pages.get("uca", ""),
                                                   page_key, today)
            except Reject as exc:
                supply[page_key] = exc
        records: list[TariffRecord] = []
        for territory, url in SCHEDULE_URLS.items():
            try:
                schedule = self._schedule(territory, url, documents.get(territory) or [], today)
            except Reject as exc:
                for spec in CLASSES:
                    self._reject(f"{territory[0]}-{spec.key}", exc)
                continue
            for spec in CLASSES:
                try:
                    records.append(self._build(schedule, spec, supply, carbon, today))
                except Reject as exc:
                    self._reject(f"{territory[0]}-{spec.key}", exc)
        return records

    def _reject(self, code: str, exc: Exception) -> None:
        self.rejections.append(f"{code}: {exc}")
        self.logger.warning("ATCO Gas %s not parsed live: %s", code, exc)

    @staticmethod
    def _carbon(html: str, today: date) -> tuple[date, str]:
        """Explicit zero federal fuel charge whose ended-charge sentence names Alberta."""
        text = _soup_text(parse_html(html)) if html else ""
        zero = re.search(
            rf"Fuel charge rates - Beginning (?P<date>{DATE}) On {DATE}, the Government of Canada made regulations "
            r"that cease the application of the federal fuel charge, by setting all fuel charge rates to zero", text)
        listed = re.search(r"The rates applied in (?P<where>[A-Z][A-Za-z ,]+?) from April 1, 2019 to March 31, 2025",
                           text)
        if not zero or not listed or "Alberta" not in listed.group("where"):
            raise Reject("CRA evidence of a zero federal fuel charge in Alberta is missing")
        effective = _date(zero.group("date"))
        if effective > today:
            raise Reject(f"CRA zero fuel charge starts {effective}, after {today}")
        return effective, (f"Canada Revenue Agency fuel charge rates, beginning {zero.group('date')}: all federal "
                           "fuel charge rates set to zero; Alberta's charge applied until March 31, 2025. ATCO Gas's "
                           "rate schedules publish no carbon row.")

    def _commodity(self, ders_html: str, uca_html: str, page_key: str, today: date) -> Commodity:
        """Current month's DERS default rate ($/GJ) from its rate chart, matched to the UCA default-rates table."""
        if not ders_html:
            raise Reject(f"DERS {page_key} natural gas rates page unavailable")
        soup = parse_html(ders_html)
        controls = soup.find_all(attrs={"data-rate-heading-label-text": True})
        charts = [tag for tag in soup.find_all(attrs={"data-chart-data": True})
                  if tag.get("data-data-type") == "natural-gas"]
        if GCFR_SENTENCE not in _soup_text(soup):
            raise Reject("DERS page no longer identifies its regulated gas rate as the Gas Cost Flow-Through Rate")
        if (len(controls) != 1 or _flat(controls[0]["data-rate-heading-label-text"]) != "Current Regulated Rate"
                or _flat(controls[0].get("data-rate-heading-measure-label-text", "")) != "/GJ"):
            raise Reject("DERS 'Current Regulated Rate' label or its /GJ unit is missing")
        if not charts:
            raise Reject("DERS natural gas rate chart is missing")
        label = f"{today.year % 100:02d}-{MONTHS[today.month - 1][:3]}"
        values: set[Decimal] = set()
        for chart in charts:
            if _flat(chart.get("data-label-y", "")) != "$/GJ":
                raise Reject("DERS rate chart unit is not $/GJ")
            try:
                rows = json.loads(chart["data-chart-data"], parse_float=Decimal)
            except ValueError as exc:
                raise Reject("DERS rate chart data is unreadable") from exc
            hits = [row for row in rows if isinstance(row, dict) and row.get("Billing Period") == label] \
                if isinstance(rows, list) else []
            if len(hits) != 1 or "$ per GJ" not in hits[0]:
                raise Reject(f"DERS has no single '{label}' rate in $ per GJ (current month not published)")
            try:
                values.add(Decimal(str(hits[0]["$ per GJ"])))
            except InvalidOperation as exc:
                raise Reject(f"DERS {label} rate is unreadable") from exc
        if len(values) != 1:
            raise Reject(f"DERS rate charts disagree for {label}")
        value = values.pop()
        if not Decimal("0") < value < Decimal("50"):
            raise Reject(f"DERS {label} rate {value} $/GJ is implausible")
        uca = self._uca_rate(uca_html, today)
        if uca != value:
            raise Reject(f"DERS {label} rate {value} $/GJ differs from the UCA default-rates table ({uca} $/GJ)")
        start = today.replace(day=1)
        return Commodity(value, page_key, label, start, _month_end(start))

    @staticmethod
    def _uca_rate(html: str, today: date) -> Decimal:
        """Direct Energy Regulated Services / ATCO Gas price for the current month from the UCA table."""
        if not html:
            raise Reject("UCA default-rates page unavailable")
        caption = f"{today.year} Natural Gas Regulated Rates in $/GJ"
        grids = [grid for grid in (_grid(table) for table in parse_html(html).find_all("table"))
                 if grid and grid[0][0] == caption]
        if len(grids) != 1:
            raise Reject(f"UCA table '{caption}' is missing")
        rows = {row[0].casefold(): row for row in grids[0][1:]}
        retailers, distributors = rows.get("retailer"), rows.get("distributor")
        if not retailers or not distributors or len(retailers) != len(distributors):
            raise Reject("UCA natural gas table lacks aligned Retailer and Distributor rows")
        columns = [index for index in range(1, len(retailers))
                   if retailers[index] == DRT_RETAILER and distributors[index] == DRT_DISTRIBUTOR]
        if len(columns) != 1:
            raise Reject(f"UCA natural gas table has no single {DRT_RETAILER} / {DRT_DISTRIBUTOR} column")
        month = MONTHS[today.month - 1]
        row = rows.get(month.casefold())
        if row is None:
            raise Reject(f"UCA table has no {month} {today.year} default rate yet")
        if len(row) != len(retailers) or not re.fullmatch(r"\d+\.\d+", row[columns[0]]):
            raise Reject(f"UCA {month} {today.year} default rate is unreadable")
        return Decimal(row[columns[0]])

    def _schedule(self, territory: str, url: str, document: list[DocumentPage], today: date) -> Schedule:
        """Edition checks plus rider tables for one territory's rate schedule PDF."""
        if not document:
            raise Reject(f"{territory} rate schedule PDF unavailable")
        pages = [_Page(page.page_number, _flat(page.text)) for page in document]
        upper = territory.upper()
        covers = [match for page in pages
                  for match in [re.search(rf"ATCO GAS (NORTH|SOUTH) RATE SCHEDULES ({DATE})", page.text)] if match]
        if len(covers) != 1 or covers[0].group(1) != upper:
            raise Reject(f"{territory} rate schedule cover (territory and edition date) is missing")
        edition = _date(covers[0].group(2))
        index = [page for page in pages
                 if re.search(rf"ATCO GAS AND PIPELINES LTD\. - {upper} RATE SCHEDULES INDEX", page.text)]
        header = HEADER.search(index[0].text) if len(index) == 1 else None
        if not header or _date(header.group("date")) != edition:
            raise Reject(f"{territory} rate schedule index is missing or its edition date differs from the cover")
        if edition > today:
            raise Reject(f"{territory} rate schedule edition {edition} is not yet in effect")
        riders = {letter: self._rider_table(letter, pages) for letter, heading in RIDER_HEADINGS.items()
                  if any(re.search(heading, page.text) for page in pages)}
        return Schedule(territory, url, edition, pages, index[0].text, riders, self._rider_e(pages))

    def _rider_table(self, letter: str, pages: list[_Page]) -> RiderTable:
        table = RiderTable(letter)
        hits = [page for page in pages if re.search(RIDER_HEADINGS[letter], page.text)]
        if len(hits) != 1:
            table.error = f'Rider "{letter}" schedule appears on {len(hits)} pages'
            return table
        page = hits[0]
        table.page = page.number
        header = HEADER.search(page.text)
        if not header:
            table.error = f'Rider "{letter}" effective-date header is missing'
            return table
        table.reference = header.group("ref")
        body = page.text[re.search(RIDER_HEADINGS[letter], page.text).end():]
        body = re.split(FOOTER, body)[0]
        try:
            header_date = _date(header.group("date"))
            if letter == "L":
                self._rows_l(table, body, page.number)
            else:
                self._rows_tw(table, body, page.number, header_date)
        except Reject as exc:
            table.error = f'Rider "{letter}": {exc}'
        return table

    @staticmethod
    def _rows_l(table: RiderTable, body: str, page: int) -> None:
        """Rider L: one dated debit/credit row per class."""
        labels = list(L_LABEL.finditer(body))
        if not labels:
            raise Reject("no class rows")
        for position, match in enumerate(labels):
            key = _class_key(match.group(1))
            stop = labels[position + 1].start() if position + 1 < len(labels) else len(body)
            table.applies_to.add(key)
            row = L_ROW.fullmatch(body[match.end():stop].strip())
            if not row:
                table.row_errors[key] = f'Rider "L" {match.group(0)} row is unreadable'
                continue
            if row.group("unit") != "GJ":
                table.row_errors[key] = f'Rider "L" {match.group(0)} unit is per {row.group("unit")}, not per GJ'
                continue
            value = _amount(row.group("value"))
            if value < 0:
                table.row_errors[key] = f'Rider "L" {match.group(0)} sign is ambiguous'
                continue
            try:
                start, end = _date(row.group("start")), _date(row.group("end"))
            except Reject as exc:
                table.row_errors[key] = f'Rider "L" {match.group(0)}: {exc}'
                continue
            if end < start:
                table.row_errors[key] = f'Rider "L" {match.group(0)} period ends before it starts'
                continue
            table.rows.setdefault(key, []).append(RiderRow(
                -value if row.group("sign") == "Credit" else value, "$/GJ", start, end, page, match.group(0),
                row.group("sign")))

    @staticmethod
    def _rows_tw(table: RiderTable, body: str, page: int, header_date: date) -> None:
        """Riders T and W: an applicability sentence with dates, then one row per class."""
        applies = APPLIES.search(body)
        if not applies:
            raise Reject("applicability sentence is missing or changed")
        start = _date(applies.group("start"))
        end = _date(applies.group("end")) if applies.group("end") else None
        if start != header_date:
            raise Reject("effective date in the text differs from the page header")
        if end and end < start:
            raise Reject("period ends before it starts")
        table.applies_to = {key for key, pattern in WHO.items() if re.search(pattern, applies.group("who"))}
        rows_text = body[applies.end():]
        labels = list(TW_LABEL.finditer(rows_text))
        seen: set[str] = set()
        for position, match in enumerate(labels):
            key = _class_key(match.group(1))
            stop = labels[position + 1].start() if position + 1 < len(labels) else len(rows_text)
            if key in seen:
                table.row_errors[key] = f'Rider "{table.letter}" {match.group(0)} row is repeated'
            seen.add(key)
            row = TW_ROW.fullmatch(rows_text[match.end():stop].strip())
            unit = TW_UNITS.get(row.group("unit")) if row else None
            if not row or not unit:
                table.row_errors[key] = f'Rider "{table.letter}" {match.group(0)} row or unit is unreadable'
                continue
            table.rows[key] = [RiderRow(_amount(row.group("value")), unit, start, end, page, match.group(0))]
        for key in table.applies_to ^ seen:
            table.row_errors[key] = f'Rider "{table.letter}" applicability sentence and rows disagree for this class'
        table.applies_to |= seen

    @staticmethod
    def _rider_e(pages: list[_Page]) -> Optional[DeemedValue]:
        page = next((page for page in pages if re.search(RIDER_E_HEADING, page.text)), None)
        if page is None:
            return None
        value = re.search(r'"Deemed Value" of Natural Gas Rate \$ ?(\d+\.\d+) per GJ', page.text)
        applies = re.search(rf"To be applied to (?P<who>.+?) customers in the City of Calgary, effective "
                            rf"(?P<date>{DATE})\.", page.text)
        if not value or not applies:
            return None
        try:
            effective = _date(applies.group("date"))
        except Reject:
            return None
        who = frozenset(key for key, pattern in WHO.items() if re.search(pattern, applies.group("who")))
        return DeemedValue(float(value.group(1)), effective, page.number, who)

    def _build(self, schedule: Schedule, spec: ClassSpec, supply: dict[str, Union[Commodity, Reject]],
               carbon: tuple[date, str], today: date) -> TariffRecord:
        territory, url = schedule.territory, schedule.url
        hits = [page for page in schedule.pages if re.search(spec.heading, page.text)]
        if len(hits) != 1:
            raise Reject(f"{spec.title} page is {'missing' if not hits else 'repeated'}")
        page = hits[0]
        text = page.text
        header = HEADER.search(text)
        if not header:
            raise Reject("effective-date header is missing")
        effective = _date(header.group("date"))
        if effective > today:
            raise Reject(f"rates effective {effective} are not yet in force")
        reference = header.group("ref")
        approved = (f"Approved in {reference if reference.startswith('AUC') else 'AUC ' + reference}."
                    if reference else "Approved by the AUC.")
        if not re.search(rf"ATCO GAS AND PIPELINES LTD\. - {territory.upper()} {spec.heading}", text):
            raise Reject(f"{territory} page header is missing")
        eligibility = re.search(spec.eligibility, text, re.I)
        if not eligibility:
            raise Reject("availability sentence is missing or changed")

        start = text.find("CHARGES:")
        if start < 0:
            raise Reject("CHARGES section is missing")
        stop = re.search(rf"RATE SWITCHING|DETERMINATION OF BILLING DEMAND|{FOOTER}", text[start:])
        block = text[start:start + stop.start()] if stop else text[start:]
        fixed = re.search(r"Fixed Charge: \$ ?(\d+\.\d+) per (\S+)", block)
        variable = re.search(r"Variable Charge: \$ ?(\d+\.\d+) per (\S+)", block)
        demand = re.search(r"Demand Charge: \$ ?(\d+\.\d+) per (.+?)(?= Load Balancing| Transmission Service|"
                           r" Weather Deferral|$)", block)
        if not fixed or not variable:
            raise Reject("fixed or variable charge is missing")
        if fixed.group(2) != "Day" or variable.group(2) != "GJ":
            raise Reject(f"unexpected units: fixed per {fixed.group(2)}, variable per {variable.group(2)}")
        if spec.demand != bool(demand):
            raise Reject("demand charge is missing" if spec.demand else "unexpected demand charge")
        if demand and demand.group(2) != "GJ per Day of 24 Hr. Billing Demand":
            raise Reject(f"unexpected demand charge unit 'per {demand.group(2)}'")
        if block.count("$") != 2 + bool(demand):
            raise Reject("unexpected additional charge in the CHARGES section")
        listed = re.findall(r'Rider "([A-Z])"', block)
        if len(set(listed)) != len(listed):
            raise Reject("a rider is listed twice")
        for letter in listed:
            if letter not in RIDER_NAMES or f'{RIDER_NAMES[letter]}: Rider "{letter}"' not in block:
                raise Reject(f'Rider "{letter}" is listed but not modelled')
        for letter, table in schedule.riders.items():
            if table.error is None and (spec.key in table.applies_to) != (letter in listed):
                raise Reject(f'Rider "{letter}" schedule and the class page disagree on whether it applies')

        eff = effective.isoformat()
        detail = f"{territory} rate schedule PDF page {page.number}; {spec.title}"

        def comp(kind: str, name: str, value: float, unit: str, source_detail: str, **extra) -> RateComponent:
            extra.setdefault("effective_date", eff)
            return RateComponent(kind, name, value, unit, source_url=url, source_detail=source_detail, **extra)

        components = [
            comp("fixed", "Fixed Charge", _amount(fixed.group(1)), "$/day", detail + ", Fixed Charge", notes=approved),
            comp("delivery", "Variable Charge", _amount(variable.group(1)), "$/GJ", detail + ", Variable Charge",
                 notes=approved),
        ]
        notes = [f"ATCO Gas {territory} {spec.title} from the AUC-approved {territory} rate schedules "
                 f"({_long(schedule.edition)} edition); base charges effective {_long(effective)}."]
        if spec.key == "LOW":
            notes.append(f"Low Use is open to every customer using {eligibility.group('max')} GJ per year or less, "
                         "homes and small businesses alike; it is classed residential here because it is the "
                         "delivery service for homes.")
        if spec.key == "ATA":
            notes.append("Conditional eligibility: available by request only, at ATCO Gas's discretion.")
        if demand:
            rule = BILLING_DEMAND.search(text)
            if not rule:
                raise Reject("billing demand determination is missing or changed")
            demand_note = (f"Per GJ of 24-hour Billing Demand per day. Billing Demand is the greatest of any "
                           "contract demand, the greatest Gas Day delivery in the current and preceding eleven "
                           "billing periods (summer-period deliveries divided by 2) and "
                           f"{rule.group('min')} GJ/day.")
            if SUMMER_ONLY in text:
                demand_note += (" For customers taking service only in the summer period, it is the greatest Gas "
                                "Day in the billing period.")
            components.append(comp("demand", "Demand Charge", _amount(demand.group(1)), "$/GJ/day",
                                   detail + ", Demand Charge", demand_unit="GJ/day", notes=demand_note + " " + approved))

        for letter in ("L", "T", "W"):
            if letter not in listed:
                continue
            table = schedule.riders.get(letter)
            if table is None:
                raise Reject(f'Rider "{letter}" schedule page is missing')
            if table.error:
                raise Reject(table.error)
            if spec.key in table.row_errors:
                raise Reject(table.row_errors[spec.key])
            rows = table.rows.get(spec.key) or []
            current = [row for row in rows if row.start <= today and (row.end is None or today <= row.end)]
            if len(current) > 1:
                raise Reject(f'Rider "{letter}" has several rows in force')
            if not current:
                if not rows or any(row.start > today for row in rows):
                    raise Reject(f'Rider "{letter}" has no value in force on {today}')
                last = max(rows, key=lambda row: row.end)
                notes.append(f'Rider "{letter}" ({RIDER_NAMES[letter]}) applied from {_long(last.start)} to '
                             f"{_long(last.end)} and has ended; it is not included.")
                continue
            row = current[0]
            if row.unit != ("$/GJ/day" if letter == "T" and spec.demand else "$/GJ"):
                raise Reject(f'Rider "{letter}" unit {row.unit} does not fit {spec.title}')
            ref = table.reference or ""
            ref = f" ({ref if ref.startswith('AUC') else 'AUC ' + ref})" if ref else ""
            period = (f"{_long(row.start)} to {_long(row.end)}" if row.end else f"effective {_long(row.start)}")
            if letter == "L":
                kind, name = "rider", "Rider L — Load Balancing Deferral Account"
                note = (f"{row.sign} ({'a charge' if row.sign == 'Debit' else 'a refund'}) on energy delivered, "
                        f"{period}{ref}.")
            elif letter == "T":
                kind, name = "transmission", "Rider T — Transmission Service Charge"
                note = (("Per GJ of 24-hour Billing Demand per day; " if row.unit == "$/GJ/day" else "")
                        + f"recovers transmission service costs, {period}{ref}.")
            else:
                kind, name = "rider", "Rider W — Weather Deferral Account"
                note = f"Weather deferral account rider, {period}{ref}."
            components.append(comp(
                kind, name, row.value, row.unit,
                f"{territory} rate schedule PDF page {row.page}; Rider {letter}, {row.label}",
                effective_date=row.start.isoformat(), end_date=row.end.isoformat() if row.end else None,
                demand_unit="GJ/day" if row.unit == "$/GJ/day" else None, notes=note))

        if spec.ders_page:
            gas = supply.get(spec.ders_page)
            if not isinstance(gas, Commodity):
                raise Reject(f"default supply gas price unavailable: {gas}")
            month = MONTHS[gas.start.month - 1]
            components.append(RateComponent(
                "commodity", DRT_NAME, float(gas.value), "$/GJ", effective_date=gas.start.isoformat(),
                end_date=gas.end.isoformat(), source_url=PAGE_URLS[f"ders_{gas.page_key}"],
                source_detail=(f"DERS regulated natural gas rates ({gas.page_key} page), chart Billing Period "
                               f"{gas.label}, $ per GJ; matches UCA {gas.start.year} Natural Gas Regulated Rates in "
                               f"$/GJ, {DRT_RETAILER} / {DRT_DISTRIBUTOR}, {month}"),
                market_reference="Direct Energy Regulated Services default rate tariff (DSP Rider F)",
                notes=(f"{month} {gas.start.year} default supply price for the ATCO Gas service area; it changes "
                       "monthly. Applies only to customers served by the default supply provider (no retailer "
                       "contract); retailer contract prices are excluded.")))
            notes.append("Gas supply shown is Direct Energy Regulated Services' default rate tariff for the current "
                         "month (customers without a retailer contract); DERS's daily default-supply "
                         "administration charge is not included.")
        else:
            notes.append("Gas supply is not included: Direct Energy Regulated Services' default rate tariff "
                         "(DSP Rider F) names Low, Mid and High Use delivery service only, and retailer contract "
                         "prices are excluded.")

        carbon_date, carbon_note = carbon
        components.append(RateComponent(
            "carbon", "Federal Carbon Charge", 0.0, "$/GJ", effective_date=carbon_date.isoformat(),
            source_url=PAGE_URLS["carbon"], source_detail="CRA fuel charge rates, Beginning April 1, 2025",
            notes=carbon_note))

        municipal = [name for letter, name in (("A", "Rider A (municipal franchise fee)"),
                                               ("B", "Rider B (municipal property tax and specific costs)"))
                     if f'Rider "{letter}"' in schedule.index]
        if municipal:
            notes.append(f"Conditional: {' and '.join(municipal)} add a percentage that varies by municipality to "
                         "all charges for customers in the listed municipalities; not included.")
        deemed = schedule.rider_e
        if deemed and spec.key in deemed.applies_to:
            notes.append(f"Conditional: in the City of Calgary (a Rider A Method C municipality) the franchise fee "
                         f"percentage also applies to Rider E, a deemed value of natural gas of ${deemed.value:.3f} "
                         f"per GJ (effective {_long(deemed.effective)}); Rider E is not a charge by itself and is "
                         "not included.")
        notes.append("GST is not included.")

        usage = eligibility.groupdict()
        source = f"ATCO Gas {territory} Rate Schedules, {_long(schedule.edition)} edition"
        return TariffRecord(
            utility_name="ATCO Gas", province="AB", utility_type="gas",
            tariff_name=f"{spec.title} ({territory})", tariff_code=f"{territory[0]}-{spec.key}",
            customer_class=spec.customer_class, sub_class=territory,
            eligibility=re.sub(r" (?:•|o) (?=[A-Z])", " ", eligibility.group(0)),
            usage_min=_int(usage.get("min")), usage_max=_int(usage.get("max")), usage_unit="GJ/year",
            rate_structure="demand" if spec.demand else "flat", pricing_method="regulated",
            effective_date=max(component.effective_date for component in components),
            source_url=url, source_page=f"{source}, PDF page {page.number}", confidence="high",
            notes=" ".join(notes), components=components,
        )

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential — South service territory ────────────────
        records.append(TariffRecord(
            utility_name="ATCO Gas",
            province="AB",
            utility_type="gas",
            tariff_name="Residential Distribution — South",
            tariff_code="D-South",
            customer_class="residential",
            sub_class="South",
            rate_structure="flat",
            effective_date=SEED_SOUTH["effective_date"],
            source_url=SEED_SOUTH["source_url"],
            confidence="medium",
            notes=(
                "ATCO Gas distribution charges for southern Alberta. "
                "Alberta is deregulated — gas supply must be purchased separately "
                "from a retailer or default supply provider. "
                "Municipal franchise fees vary by city and are not included. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_SOUTH["customer_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly distribution charge",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Variable Distribution Charge",
                    charge_value=SEED_SOUTH["variable_distribution"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Volume-based distribution charge for gas delivery",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_SOUTH["carbon_charge"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="AUC Rate Rider",
                    charge_value=SEED_SOUTH["rate_rider"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="AUC-approved rate adjustment rider",
                ),
            ],
        ))

        # ── Residential — North service territory ────────────────
        records.append(TariffRecord(
            utility_name="ATCO Gas",
            province="AB",
            utility_type="gas",
            tariff_name="Residential Distribution — North",
            tariff_code="D-North",
            customer_class="residential",
            sub_class="North",
            rate_structure="flat",
            effective_date=SEED_NORTH["effective_date"],
            source_url=SEED_NORTH["source_url"],
            confidence="medium",
            notes=(
                "ATCO Gas distribution charges for northern Alberta. "
                "Higher costs than South territory due to longer distribution lines "
                "and lower customer density. "
                "Gas supply must be purchased separately from a retailer. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_NORTH["customer_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly distribution charge — higher than South",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Variable Distribution Charge",
                    charge_value=SEED_NORTH["variable_distribution"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Volume-based distribution charge — higher than South territory",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_NORTH["carbon_charge"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="AUC Rate Rider",
                    charge_value=SEED_NORTH["rate_rider"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="AUC-approved rate adjustment rider",
                ),
            ],
        ))

        return records
