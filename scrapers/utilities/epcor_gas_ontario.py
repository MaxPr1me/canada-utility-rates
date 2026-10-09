"""
epcor_gas_ontario.py — EPCOR Natural Gas (Ontario): Aylmer and Southern Bruce rate zones.

EPCOR Natural Gas Limited Partnership is an Ontario Energy Board (OEB) regulated gas
distributor with two rate zones: the Aylmer service area and the Southern Bruce
(Kincardine and area) service area.

Official sources, per zone:
  EPCOR rates page   https://www.epcor.com/ca/en/on/aylmer-area/account/rates/natural-gas-rates.html
                     https://www.epcor.com/ca/en/on/kincardine-area/account/rates/natural-gas-rates.html
  OEB QRAM notice    https://www.oeb.ca/sites/default/files/qram-epcor-{aylmer|sb}-YYYYMMDD-en.pdf
                     (gas commodity charge, effective date and case number)
  OEB Decision and Rate Order, Appendix A (approved rate schedules), found by the notice's
  case number in the OEB Regulatory Document Search (https://www.rds.oeb.ca/).
  CRA fuel charge rates (federal fuel charge set to zero from April 1, 2025):
                     https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/fcrates/fuel-charge-rates.html

EPCOR's page states that the OEB decision and order governs on any variance, so every
page value must also appear in the approved schedule. Where the page prints a unit or a
season split differently from the schedule, the schedule governs and the record says so.
"""

from __future__ import annotations

import html as html_lib
import io
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Optional

from bs4 import Comment

from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage, parse_html

logger = logging.getLogger(__name__)

UTILITY_NAME = "EPCOR Natural Gas (Ontario)"
CRA_URL = ("https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/fcrates/"
           "fuel-charge-rates.html")
NOTICE_URL = "https://www.oeb.ca/sites/default/files/qram-epcor-{slug}-{stamp}-en.pdf"
RDS_SEARCH_URL = ("https://www.rds.oeb.ca/CMWebDrawer/Record?q=casenumber%3A{case}"
                  "&sortBy=recRegisteredOn-&pageSize=400")
RDS_DOCUMENT_URL = "https://www.rds.oeb.ca/CMWebDrawer/Record/{record}/File/document"


@dataclass(frozen=True)
class Zone:
    key: str
    label: str
    page_url: str
    notice_slug: str
    order_name: str


ZONES = {
    "aylmer": Zone("aylmer", "Aylmer",
                   "https://www.epcor.com/ca/en/on/aylmer-area/account/rates/natural-gas-rates.html",
                   "aylmer", "AYLMER"),
    "sb": Zone("sb", "Southern Bruce",
               "https://www.epcor.com/ca/en/on/kincardine-area/account/rates/natural-gas-rates.html",
               "sb", "SOUTHERN BRUCE"),
}


@dataclass(frozen=True)
class ClassSpec:
    zone: str
    code: str
    heading: str                      # EPCOR page h3 text
    order_heading: str                # regex locating the approved schedule in Appendix A
    name: str
    customer_class: str
    rate_structure: str
    kinds: frozenset                  # exact set of identified page lines
    usage: Optional[tuple[str, str]] = None   # ("min"|"max", regex on the approved eligibility)
    note: str = ""


_RES_LINES = frozenset({"fixed", "delivery", "rider", "transportation"})
_TIER2 = frozenset({"fixed", "block_first", "block_over", "rider", "transportation"})
_TIER3 = frozenset({"fixed", "block_first", "block_next", "block_over", "rider", "transportation"})
_SB_TIERS = frozenset({"fixed", "block_first", "block_next", "block_over", "upstream_recovery",
                       "transport_storage", "rider", "gas_supply"})

CLASS_SPECS = (
    ClassSpec("aylmer", "AYL-1-RES", "Rate 1: Residential rate", r"RATE 1 [-–] Residential Rate",
              "Rate 1 Residential", "residential", "flat", _RES_LINES),
    ClassSpec("aylmer", "AYL-1-GS", "Rate 1: General service rate", r"RATE 1 [-–] General Service Rate",
              "Rate 1 General Service", "commercial", "tiered", _TIER2),
    ClassSpec("aylmer", "AYL-2", "Rate 2: Seasonal service", r"RATE 2 [-–] Seasonal Service",
              "Rate 2 Seasonal Service", "commercial", "tiered", _TIER3,
              note="EPCOR's page describes Rate 2 as designed for seasonal tobacco/agricultural use; the approved "
                   "schedule makes it available to all customers."),
    ClassSpec("aylmer", "AYL-3", "Rate 3: Special large volume contract rate",
              r"RATE 3 [-–] Special Large Volume Contract Rate", "Rate 3 Special Large Volume Contract", "industrial",
              "demand", frozenset({"fixed_single", "fixed_combined", "demand", "firm_delivery", "negotiated", "rider",
                                   "transportation"}),
              usage=("min", r"annual volume of at least ([\d,]+)\s*m3")),
    ClassSpec("aylmer", "AYL-4", "Rate 4: General service peaking", r"RATE 4 [-–] General Service Peaking",
              "Rate 4 General Service Peaking", "commercial", "tiered", _TIER2,
              note="Interruptible: service may be interrupted and restored with 24 hours' notice. EPCOR's page "
                   "describes Rate 4 as designed for small grain dryers; the approved schedule makes it available to "
                   "all customers whose operations can accept that interruption."),
    ClassSpec("aylmer", "AYL-5", "Rate 5: Interruptible peaking contract rate",
              r"RATE 5 [-–] Interruptible Peaking Contract Rate", "Rate 5 Interruptible Peaking Contract",
              "industrial", "flat", frozenset({"fixed_single", "negotiated", "rider", "transportation"}),
              usage=("min", r"annual volume of at least ([\d,]+)\s*m3"),
              note="Interruptible contract service. EPCOR's page describes Rate 5 as designed for large commercial "
                   "grain dryer operations; the approved schedule's eligibility is by contract, demand and volume."),
    ClassSpec("sb", "SB-1", "Rate 1: Residential, Commercial and Small Agricultural (General firm service)",
              r"RATE 1 [-–] General Firm Service", "Rate 1 General Firm Service — Residential", "residential",
              "tiered", _SB_TIERS, usage=("max", r"equal to or less than ([\d,]+) m3 per year")),
    ClassSpec("sb", "SB-1", "Rate 1: Residential, Commercial and Small Agricultural (General firm service)",
              r"RATE 1 [-–] General Firm Service", "Rate 1 General Firm Service — Commercial", "commercial",
              "tiered", _SB_TIERS, usage=("max", r"equal to or less than ([\d,]+) m3 per year"),
              note="Rate 1 is one published class for residential, commercial and small agricultural customers; "
                   "this record lists it for commercial customers."),
    ClassSpec("sb", "SB-6", "Rate 6: Large Volume (Large volume general firm service)",
              r"RATE 6 [-–] Large Volume General Firm Service", "Rate 6 Large Volume General Firm Service",
              "commercial", "tiered", _SB_TIERS, usage=("min", r"greater than ([\d,]+) m3 per year")),
    ClassSpec("sb", "SB-11", "Rate 11: Large Volume Seasonal Service", r"RATE 11 [-–] Large Volume Seasonal Service",
              "Rate 11 Large Volume Seasonal Service", "commercial", "flat",
              frozenset({"fixed", "delivery", "overrun_authorized", "overrun_unauthorized", "upstream_recovery",
                         "transport_storage", "rider", "gas_supply"}),
              usage=("min", r"greater\s+than ([\d,]+) m3"),
              note="Seasonal firm service May 1 - December 15; gas taken December 16 - April 30 is overrun gas."),
)

# Published classes deliberately not modelled, with the reason reported each run.
EXCLUDED_HEADINGS = {
    "aylmer": ((r"Rate 6: .*ethanol production facility",
                "single named facility (ALCO Energy, formerly IGPC, ethanol production); not generally available"),),
    "sb": ((r"Rate 16: Special Contracted Customers",
            "direct-purchase-only contracted firm service; EPCOR's page prints its riders in ¢ per m³ while the "
            "approved schedule prints them per m³ of contract demand without a unit, so the lines are not "
            "identified"),),
}

_LINE_RULES = (
    ("fixed", r"monthly fixed charge(?: \(1\))?"),
    ("fixed_single", r"firm or interruptible service"),
    ("fixed_combined", r"combined \(firm and interruptible\) service"),
    ("delivery", r"all volumes per month|all volumes delivered may 1 - dec 15"),
    ("block_first", r"first ([\d,]+) ?m³ per month"),
    ("block_next", r"next ([\d,]+) ?m³ per month"),
    ("block_over", r"(?:all )?over ([\d,]+) ?m³ per month"),
    ("demand", r"monthly demand charge - for each cubic metre of daily contracted firm demand"),
    ("firm_delivery", r"firm delivery charge"),
    ("negotiated", r"interruptible delivery charge \(negotiated\)"),
    ("rider", r"rate rider for (.+?) recovery \(effective for (\d+) (months|years) ending ([a-z]+ \d{1,2}, \d{4})\)"),
    ("transportation", r"transportation charge"),
    ("upstream_recovery", r"upstream recovery charge"),
    ("transport_storage", r"transportation and storage charge"),
    ("gas_supply", r"gas supply charge"),
    ("overrun_authorized", r"authorized overrun dec 16 - apr 30"),
    ("overrun_unauthorized", r"unauth(?:orized|roized) overrun dec 16 - apr 30"),
)
_GROUP_ROWS = {"delivery charges", "upstream charges", "monthly fixed charge (1)", "monthly fixed charge"}
_VALUE_RE = re.compile(
    r"(?P<low>\d+\.\d+)\s*-\s*(?P<high>\d+\.\d+)\s*¢\s*(?:per|/)\s*m³"
    r"|(?P<cneg>\()?(?P<cents>\d+\.\d+)\)?\s*¢\s*(?:per|/)\s*(?P<cper>m³|month)"
    r"|(?P<dneg>\()?\$\s*(?P<dollars>\d[\d,]*\.\d{2})\)?(?:\s*per\s+(?P<dper>month))?"
)
_MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August", "September",
                "October", "November", "December")
_MONTH_NUMBERS = {name[:3].lower(): number for number, name in enumerate(_MONTH_NAMES, 1)}


@dataclass(frozen=True)
class _Value:
    kind: str                       # "cents", "dollars" or "range"
    amount: float = 0.0             # signed printed number (unused for ranges)
    per: Optional[str] = None       # "m³", "month" or None
    low: Optional[float] = None
    high: Optional[float] = None
    text: str = ""


@dataclass
class _Line:
    kind: str
    label: str
    values: list
    match: re.Match


@dataclass
class _PageClass:
    heading: str
    description: str
    rows: Optional[list] = None


@dataclass
class _ZoneContext:
    zone: Zone
    effective: date
    case: str
    notice_url: str
    notice_charge: float
    order_url: str
    order_text: str
    page_classes: dict
    supply: dict = field(default_factory=dict)


# ── Pure helpers (used by fetching and tests) ─────────────────

def _norm(text: str) -> str:
    text = text.replace("\u200b", " ").replace("\ufeff", " ").replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _long_date(value: str) -> Optional[date]:
    value = value.replace(".", "")
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _cents_to_dollars(value: float) -> float:
    return round(value / 100, 6)


def _display(day: date) -> str:
    return f"{day.strftime('%B')} {day.day}, {day.year}"


def page_effective_date(page_html: str) -> Optional[date]:
    """'The rates below are effective <date>' from an EPCOR rates page."""
    match = re.search(r"The rates below are effective ([A-Z][a-z]+ \d{1,2}, \d{4})",
                      _norm(parse_html(page_html).get_text(" ")))
    return _long_date(match.group(1)) if match else None


def notice_url(zone: Zone, effective: date) -> str:
    return NOTICE_URL.format(slug=zone.notice_slug, stamp=effective.strftime("%Y%m%d"))


def notice_case(pages: list) -> Optional[str]:
    match = re.search(r"As approved through (EB-\d{4}-\d{4})", _norm(" ".join(page.text for page in pages)))
    return match.group(1) if match else None


def find_rate_order_url(search_html: str, case: str) -> Optional[str]:
    """Newest OEB RDS record for the case whose document type includes 'Rate Order'."""
    for row in search_html.split("<tr")[1:]:
        record = re.search(r"/CMWebDrawer/Record/(\d+)/File/document", row)
        if not record:
            continue
        cells = [_norm(html_lib.unescape(re.sub(r"<[^>]+>", " ", cell)))
                 for cell in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)]
        if any(cell == case for cell in cells) and any("Rate Order" in cell for cell in cells):
            return RDS_DOCUMENT_URL.format(record=record.group(1))
    return None


def _cell_values(cell: str) -> Optional[list]:
    """Every printed value in a cell; None when any text is not a recognised value and unit."""
    values, position = [], 0
    for match in _VALUE_RE.finditer(cell):
        if cell[position:match.start()].strip():
            return None
        position = match.end()
        if match.group("low"):
            values.append(_Value("range", low=float(match.group("low")), high=float(match.group("high")),
                                 per="m³", text=match.group(0)))
        elif match.group("cents"):
            sign = -1 if match.group("cneg") else 1
            values.append(_Value("cents", sign * float(match.group("cents")), match.group("cper"),
                                 text=match.group(0)))
        else:
            sign = -1 if match.group("dneg") else 1
            values.append(_Value("dollars", sign * float(match.group("dollars").replace(",", "")),
                                 match.group("dper"), text=match.group(0)))
    if cell[position:].strip():
        return None
    return values


def _page_classes(page_html: str) -> dict:
    """h3 heading -> _PageClass(description, table rows) from an EPCOR rates page."""
    soup = parse_html(page_html)
    classes: dict[str, _PageClass] = {}
    for heading in soup.find_all("h3"):
        title = _norm(heading.get_text(" "))
        table = heading.find_next("table")
        if table is None or table.find_previous("h3") is not heading:
            classes[title] = _PageClass(title, "")
            continue
        parts = []
        for text in heading.find_all_next(string=True):
            if text.find_parent("table") is table:
                break
            if heading not in text.parents and not isinstance(text, Comment):
                parts.append(str(text))
        rows = [[_norm(cell.get_text(" ")) for cell in tr.find_all(["td", "th"])] for tr in table.find_all("tr")]
        classes[title] = _PageClass(title, _norm(" ".join(parts)), rows)
    return classes


def _order_text(pages: list) -> str:
    return "\n".join(f"[[PDF page {page.page_number}]]\n{page.text}" for page in pages)


def _order_section(order_text: str, heading: str) -> Optional[tuple[str, int]]:
    """Approved schedule text from its heading to its 'Implementation:' line, plus its first PDF page."""
    match = re.search(heading, order_text)
    if not match:
        return None
    end = order_text.find("Implementation:", match.end())
    if end < 0:
        return None
    end_line = order_text.find("\n", end)
    pages = re.findall(r"\[\[PDF page (\d+)\]\]", order_text[:match.start()])
    return order_text[match.start(): end_line if end_line > 0 else len(order_text)], int(pages[-1]) if pages else 0


def _order_numbers(section: str) -> tuple[set, set]:
    cents = {round((-1 if neg or minus else 1) * float(value), 6)
             for neg, minus, value in re.findall(r"(\()?(-)?(\d+\.\d+)\)?\s*(?:cents|¢)", section)}
    dollars = {round((-1 if neg or inner else 1) * float(value.replace(",", "")), 6)
               for neg, inner, value in re.findall(r"(\()?\$\s*(\()?(\d[\d,]*\.\d{2})", section)}
    return cents, dollars


def _period(text: str) -> Optional[tuple[int, int, int, Optional[int]]]:
    """(start month, start day, end month, end day or None) from e.g. 'April 1 to October 31' or 'Nov 1 - Mar'."""
    match = re.fullmatch(r"([A-Za-z]+)\.? (\d{1,2}) (?:to|-) ([A-Za-z]+)\.?(?: (\d{1,2}))?", text.strip())
    if not match:
        return None
    start, end = _MONTH_NUMBERS.get(match.group(1)[:3].lower()), _MONTH_NUMBERS.get(match.group(3)[:3].lower())
    if not start or not end:
        return None
    return start, int(match.group(2)), end, int(match.group(4)) if match.group(4) else None


def _order_periods(section: str) -> Optional[list[str]]:
    match = re.search(r"For all gas consumed from:\s*([A-Z][a-z]+ \d{1,2} - [A-Z][a-z]+(?: \d{1,2})?)\s+"
                      r"([A-Z][a-z]+ \d{1,2} - [A-Z][a-z]+(?: \d{1,2})?)", section)
    return [match.group(1), match.group(2)] if match else None


# ── Scraper ───────────────────────────────────────────────────

class EPCOROntarioGasScraper(BaseScraper):
    """EPCOR Natural Gas Limited Partnership rates for the Aylmer and Southern Bruce zones."""

    def __init__(self, registry_entry: Optional[dict] = None):
        super().__init__(utility_name=UTILITY_NAME, province="ON")
        self.registry_entry = registry_entry
        self.today: Optional[date] = None
        self.rejections: list[str] = []
        self.exclusions: list[str] = []
        self.unmodelled: list[str] = []

    def scrape(self) -> list[TariffRecord]:
        sources = {"cra": self._fetch_text(CRA_URL), "zones": {key: self._fetch_zone(zone)
                                                                for key, zone in ZONES.items()}}
        records = self.parse_sources(sources, self.today)
        if not records:
            self.logger.warning("EPCOR Ontario gas: no class parsed live; returning no records (no seed data)")
            return []
        return self.mark_live_parsed(records)

    # ── Fetching ─────────────────────────────────────────────

    def _fetch_text(self, url: str) -> Optional[str]:
        try:
            soup = parse_html(self.fetch_page(url))
            return _norm((soup.find("main") or soup).get_text(" ", strip=True))
        except Exception as exc:
            self.logger.warning("EPCOR Ontario gas: %s unavailable: %s", url, exc)
            return None

    def _fetch_pdf_pages(self, url: str) -> list[DocumentPage]:
        """Raw per-page text; repeated lines (rider periods) are kept, unlike normalize_document_text."""
        import pdfplumber

        data = self.fetch_bytes(url)
        if not data.startswith(b"%PDF"):
            raise ValueError(f"not a PDF: {url}")
        with pdfplumber.open(io.BytesIO(data)) as document:
            return [DocumentPage(number, page.extract_text(x_tolerance=2, y_tolerance=3) or "")
                    for number, page in enumerate(document.pages, 1)]

    def _fetch_zone(self, zone: Zone) -> dict:
        data: dict = {"page_url": zone.page_url}
        try:
            data["page_html"] = self.fetch_page(zone.page_url)
            effective = page_effective_date(data["page_html"])
            if effective is None:
                return data
            data["notice_url"] = notice_url(zone, effective)
            data["notice_pages"] = self._fetch_pdf_pages(data["notice_url"])
            case = notice_case(data["notice_pages"])
            if case is None:
                return data
            order_url = find_rate_order_url(self.fetch_page(RDS_SEARCH_URL.format(case=case)), case)
            if order_url:
                data["order_url"] = order_url
                data["order_pages"] = self._fetch_pdf_pages(order_url)
        except Exception as exc:
            self.logger.warning("EPCOR Ontario gas %s source unavailable: %s", zone.label, exc)
        return data

    # ── Parsing ──────────────────────────────────────────────

    def parse_sources(self, sources: dict, today: Optional[date] = None) -> list[TariffRecord]:
        """Build records from fetched sources.

        sources = {"cra": text, "zones": {zone_key: {"page_html", "notice_url", "notice_pages",
        "order_url", "order_pages"}}}; pages are DocumentPage lists. Missing carbon evidence
        rejects everything; a zone fails as a whole on date/commodity/order problems, and
        otherwise each class fails independently.
        """
        today = today or datetime.now(timezone.utc).date()
        self.rejections, self.exclusions, self.unmodelled = [], [], []
        carbon = self._carbon(sources.get("cra") or "", today)
        if carbon is None:
            self._reject("all", "federal fuel charge evidence (CRA, Ontario, zero from April 1, 2025) missing")
            return []
        records: list[TariffRecord] = []
        for key, zone in ZONES.items():
            try:
                context = self._zone_context(zone, sources.get("zones", {}).get(key) or {}, today)
            except ValueError as exc:
                self._reject(zone.label, str(exc))
                continue
            for spec in CLASS_SPECS:
                if spec.zone != key:
                    continue
                try:
                    records.append(self._build(spec, context, carbon, today))
                except ValueError as exc:
                    self._reject(f"{zone.label} {spec.code} ({spec.customer_class})", str(exc))
        return records

    def _reject(self, scope: str, reason: str) -> None:
        self.rejections.append(f"{scope}: {reason}")
        self.logger.warning("EPCOR Ontario gas %s not parsed live: %s", scope, reason)

    def _carbon(self, text: str, today: date) -> Optional[tuple[date, str]]:
        """Explicit zero federal fuel charge, with Ontario listed among the provinces whose charge ended."""
        text = _norm(text)
        zero = re.search(
            r"Fuel charge rates \S{1,2} Beginning ([A-Z][a-z]+ \d{1,2}, \d{4}) On [A-Z][a-z]+ \d{1,2}, \d{4}, "
            r"the Government of Canada made regulations that cease the application of the federal fuel charge, "
            r"by setting all fuel charge rates to zero", text)
        ontario = re.search(
            r"The rates applied in Alberta, Manitoba, Ontario, and Saskatchewan from April 1, 2019 to March 31, 2025",
            text)
        if not zero or not ontario:
            return None
        effective = _long_date(zero.group(1))
        if not effective or effective > today:
            return None
        return effective, (f"Canada Revenue Agency fuel charge rates, beginning {zero.group(1)}: all federal fuel "
                           "charge rates set to zero; Ontario's charge applied until March 31, 2025.")

    def _zone_context(self, zone: Zone, data: dict, today: date) -> _ZoneContext:
        page_html = data.get("page_html")
        if not page_html:
            raise ValueError("rates page unavailable")
        effective = page_effective_date(page_html)
        if effective is None:
            raise ValueError("rates page effective date missing")
        if effective > today:
            raise ValueError(f"rates page effective date {effective} is in the future")
        notice_text = _norm(" ".join(page.text for page in data.get("notice_pages") or []))
        if not notice_text:
            raise ValueError("OEB QRAM notice unavailable")
        if zone.label not in notice_text:
            raise ValueError("OEB QRAM notice is for another rate zone")
        notice_date = re.search(r"The OEB approved the following commodity rates effective "
                                r"([A-Z][a-z]{2,8}\.? \d{1,2}, \d{4})", notice_text)
        if not notice_date or _long_date(notice_date.group(1)) != effective:
            raise ValueError("OEB QRAM notice effective date differs from the rates page")
        charge = re.search(r"Gas Commodity Charge\s*1?\s*\(including quarterly adjustment\)\s*=\s*(\d+\.\d{4})\s*¢\s*/"
                           r"\s*m[3³]", notice_text)
        case = notice_case(data.get("notice_pages") or [])
        if not charge or not case:
            raise ValueError("OEB QRAM notice commodity charge or case number missing")
        carbon_lines = re.findall(r"Carbon Charge(?: and Facilities)?(?: \(¢/m[3³]\))?\s+(\d+\.\d+)\s*¢", notice_text)
        if any(float(value) != 0 for value in carbon_lines):
            raise ValueError("OEB QRAM notice prints a non-zero carbon charge; the rates page prints none")
        order_pages = data.get("order_pages") or []
        if not order_pages:
            raise ValueError(f"OEB Decision and Rate Order for {case} unavailable")
        cover = _norm(" ".join(page.text for page in order_pages[:2])).upper()
        if f"DECISION AND RATE ORDER {case}" not in cover or zone.order_name not in cover:
            raise ValueError(f"OEB Decision and Rate Order is not {case} for {zone.label}")
        context = _ZoneContext(zone, effective, case, data.get("notice_url") or notice_url(zone, effective),
                               float(charge.group(1)), data.get("order_url") or "", _order_text(order_pages),
                               _page_classes(page_html))
        for title in context.page_classes:
            known = any(spec.zone == zone.key and spec.heading.lower() == title.lower() for spec in CLASS_SPECS)
            excluded = next((reason for pattern, reason in EXCLUDED_HEADINGS.get(zone.key, ())
                             if re.match(pattern, title)), None)
            if excluded:
                self.exclusions.append(f"{zone.label} {title}: {excluded}")
            elif not known and re.match(r"Rate \d+", title):
                self.unmodelled.append(f"{zone.label} {title}")
                self.logger.warning("EPCOR Ontario gas %s: unmodelled published class %r", zone.label, title)
        if zone.key == "aylmer":
            context.supply = self._aylmer_supply(context)
        return context

    def _aylmer_supply(self, context: _ZoneContext) -> dict:
        """Aylmer 'Gas supply charges' table, reconciled and confirmed by Schedule A and the OEB notice."""
        table = context.page_classes.get("Gas supply charges")
        if table is None or not table.rows:
            raise ValueError("gas supply charges table missing")
        values: dict[str, float] = {}
        for row in table.rows:
            if not row or row[0] == "Charges":
                continue
            parsed = _cell_values(" ".join(row[1:]))
            if not parsed or len(parsed) != 1 or parsed[0].kind != "cents" or parsed[0].per != "m³":
                raise ValueError(f"gas supply line {row[0]!r} has no single ¢/m³ value")
            values[row[0]] = parsed[0].amount
        names = ("PGCVA Reference Price", "GPRA Recovery Rate", "Total Gas Supply Charge")
        if set(values) != set(names):
            raise ValueError(f"gas supply lines changed: {sorted(values)}")
        reference, recovery, total = (values[name] for name in names)
        if abs(reference + recovery - total) > 0.00005:
            raise ValueError("gas supply parts do not add to the printed total")
        if total != context.notice_charge:
            raise ValueError("gas supply total differs from the OEB QRAM notice")
        section = _order_section(context.order_text, r"SCHEDULE A [-–] Gas Supply Charges")
        if section is None:
            raise ValueError("approved Schedule A (gas supply) missing")
        cents, _ = _order_numbers(section[0])
        if not {round(value, 6) for value in values.values()} <= cents:
            raise ValueError("gas supply values differ from approved Schedule A")
        self._require_effective(section[0], context.effective)
        return {"reference": reference, "recovery": recovery, "total": total, "page": section[1]}

    @staticmethod
    def _require_effective(section: str, effective: date) -> None:
        match = re.search(r"Effective:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", section)
        if not match or _long_date(match.group(1)) != effective:
            raise ValueError("approved schedule effective date differs from the rates page")

    def _lines(self, page_class: _PageClass) -> tuple[list[_Line], list[str]]:
        """Identified lines and the season headers (two for seasonal tables, else one empty)."""
        rows = page_class.rows or []
        periods = [""]
        lines: list[_Line] = []
        for row in rows:
            if not row or not any(row):
                continue
            label, cells = row[0], row[1:]
            if row == ["Charges", "Rates"]:
                continue
            if label.lower().startswith("for all gas consumed from"):
                periods = cells
                if len(periods) != 2 or not all(_period(period) for period in periods):
                    raise ValueError("season header not identified")
                continue
            values: list[_Value] = []
            for cell in cells:
                parsed = _cell_values(cell)
                if parsed is None:
                    raise ValueError(f"value not identified in line {label!r}")
                values.extend(parsed)
            if not values:
                if label.lower() not in _GROUP_ROWS:
                    raise ValueError(f"line {label!r} has no value")
                continue
            if len(values) != len(periods):
                raise ValueError(f"line {label!r} does not have one value per season column")
            for kind, pattern in _LINE_RULES:
                match = re.fullmatch(pattern, label, re.I)
                if match:
                    lines.append(_Line(kind, label, values, match))
                    break
            else:
                raise ValueError(f"line {label!r} not identified")
        return lines, periods

    def _build(self, spec: ClassSpec, context: _ZoneContext, carbon: tuple[date, str], today: date) -> TariffRecord:
        zone = context.zone
        page_class = next((value for title, value in context.page_classes.items()
                           if title.lower() == spec.heading.lower()), None)
        if page_class is None or not page_class.rows:
            raise ValueError("class heading or table missing from the rates page")
        lines, periods = self._lines(page_class)
        kinds = {line.kind for line in lines}
        if kinds != spec.kinds:
            raise ValueError(f"lines changed: missing {sorted(spec.kinds - kinds)}, unexpected {sorted(kinds - spec.kinds)}")
        found = _order_section(context.order_text, spec.order_heading)
        if found is None:
            raise ValueError("approved schedule missing from the Decision and Rate Order")
        section, order_page = found
        self._require_effective(section, context.effective)
        eligibility = re.search(r"(?:Eligibility|Applicability)\s*\n(.*?)\n\s*Rate\b", section, re.S)
        if not eligibility:
            raise ValueError("approved eligibility missing")
        eligibility_text = _norm(eligibility.group(1))
        usage_min = usage_max = None
        if spec.usage:
            limit = re.search(spec.usage[1], eligibility_text)
            if not limit:
                raise ValueError("approved volume eligibility changed")
            if spec.usage[0] == "min":
                usage_min = float(limit.group(1).replace(",", ""))
            else:
                usage_max = float(limit.group(1).replace(",", ""))
        seasonal = self._seasons(periods, section) if len(periods) == 2 else []
        seasons: list = seasonal or [None]
        cents, dollars = _order_numbers(section)
        bill32 = ("Includes $1 per month aggregated under Bill 32 and Ontario Regulation 24/19 (approved schedule "
                  "footnote 1)." if "one dollar per month in accordance with Bill 32" in _norm(section) else None)
        eff = context.effective.isoformat()
        page_detail = (f"{zone.label} rates page, '{page_class.heading}' table (rates effective "
                       f"{_display(context.effective)}); confirmed in {context.case} Appendix A, PDF page {order_page}")
        notes: list[str] = []
        if seasonal and seasonal[0]["differs"]:
            notes.append(f"Season periods follow the approved schedule ({seasonal[0]['label']}; "
                         f"{seasonal[1]['label']}); EPCOR's rates page prints {seasonal[0]['page']} and "
                         f"{seasonal[1]['page']}.")

        def comp(kind: str, name: str, value: Optional[float], unit: str, **extra) -> RateComponent:
            extra.setdefault("source_url", zone.page_url)
            extra.setdefault("source_detail", page_detail)
            return RateComponent(kind, name, value, unit, effective_date=eff, **extra)

        comps: list[RateComponent] = []
        tier = 0
        threshold = 0.0
        for line in lines:
            if line.kind == "rider":
                comps.extend(self._rider(line, seasons, cents, dollars, context, order_page, today, comp, notes))
                continue
            if line.kind == "negotiated":
                value = line.values[0]
                if value.kind != "range" or not all(re.search(re.escape(f"{bound:.4f}"), section)
                                                    for bound in (value.low, value.high)) \
                        or "negotiated" not in section:
                    raise ValueError("negotiated range not confirmed by the approved schedule")
                comps.append(comp(
                    "delivery", "Monthly Interruptible Delivery Charge (negotiated)", None, "$/m³",
                    sub_component="conditional",
                    notes=(f"Conditional: negotiated between EPCOR and the customer for all interruptible volumes, "
                           f"within the published range of {value.low:.4f}-{value.high:.4f}¢/m³; no single price "
                           "is published.")))
                continue
            for column, value in self._columns(line, seasons):
                season = seasons[column] if column is not None else None
                if line.kind.startswith("fixed"):
                    if value.kind != "dollars" or value.per or round(value.amount, 6) not in dollars:
                        raise ValueError(f"fixed charge {value.text!r} not confirmed in $ by the approved schedule")
                    amount, unit = value.amount, "$/month"
                else:
                    if value.kind != "cents" or value.per != "m³" or round(value.amount, 6) not in cents:
                        raise ValueError(f"{line.label!r} value {value.text!r} not confirmed in ¢/m³ by the "
                                         "approved schedule")
                    amount, unit = _cents_to_dollars(value.amount), "$/m³"
                extra = self._season_fields(season)
                suffix = f" ({season['label']})" if season else ""
                if line.kind == "fixed" or (line.kind == "fixed_single" and "fixed_combined" not in spec.kinds):
                    comps.append(comp("fixed", "Monthly Fixed Charge" + suffix, amount, unit, notes=bill32, **extra))
                elif line.kind == "fixed_single":
                    comps.append(comp("fixed", "Monthly Customer Charge — firm or interruptible service", amount,
                                      unit, sub_component="conditional",
                                      notes="Conditional: customers taking only firm or only interruptible service; "
                                            "combined service pays the alternative customer charge."))
                elif line.kind == "fixed_combined":
                    comps.append(comp("fixed", "Monthly Customer Charge — combined firm and interruptible service",
                                      amount, unit, sub_component="conditional",
                                      notes="Conditional: customers taking combined firm and interruptible service "
                                            "instead of the firm-or-interruptible customer charge."))
                elif line.kind == "delivery":
                    note = ("All volumes delivered May 1 - December 15." if "may 1" in line.label.lower()
                            else "All volumes per month.")
                    comps.append(comp("delivery", "Delivery Charge" + suffix, amount, unit, notes=note, **extra))
                elif line.kind.startswith("block_"):
                    size = float(line.match.group(1).replace(",", ""))
                    if line.kind == "block_first":
                        tier, threshold = 1, size
                        bound, text = size, f"first {size:,.0f} m³ per month"
                    elif line.kind == "block_next":
                        if column in (None, 0):
                            tier, threshold = tier + 1, threshold + size
                        bound, text = threshold, f"next {size:,.0f} m³ per month"
                    else:
                        if size != threshold:
                            raise ValueError("delivery blocks do not join up")
                        if column in (None, 0):
                            tier += 1
                        bound, text = None, f"over {size:,.0f} m³ per month"
                    comps.append(comp("delivery", f"Delivery Charge — {text}{suffix}", amount, unit,
                                      tier_number=tier, tier_threshold=bound, tier_unit="m³/month" if bound else None,
                                      notes=("Monthly volume block; threshold is the block's upper bound" if bound
                                             else "Monthly volume above the previous block"), **extra))
                elif line.kind == "demand":
                    phrase = r"\s+".join(["Monthly Demand Charge of", re.escape(f"{value.amount:.4f}"), *(
                        "cents per m3 for each m3 of daily contracted firm demand".split())])
                    if not re.search(phrase, section):
                        raise ValueError("demand charge basis not confirmed by the approved schedule")
                    comps.append(comp("demand", "Monthly Demand Charge", amount, "$/m³/month",
                                      demand_unit="m³/day of daily contracted firm demand",
                                      notes="Per m³ of daily contracted firm demand, per month."))
                elif line.kind == "firm_delivery":
                    comps.append(comp("delivery", "Monthly Firm Delivery Charge", amount, unit,
                                      notes="All firm volumes."))
                elif line.kind == "transportation":
                    comps.append(comp("delivery", "Transportation Charge" + suffix, amount, unit,
                                      notes="Printed for system gas and direct purchase customers.", **extra))
                elif line.kind == "upstream_recovery":
                    comps.append(comp("delivery", "Upstream Recovery Charge", amount, unit,
                                      notes="Upstream charge."))
                elif line.kind == "transport_storage":
                    comps.append(comp("delivery", "Transportation and Storage Charge", amount, unit,
                                      notes="Upstream charge; for direct purchase (T-service) customers it may vary "
                                            "with the Ontario Delivery Point."))
                elif line.kind == "gas_supply":
                    if value.amount != context.notice_charge:
                        raise ValueError("gas supply charge differs from the OEB QRAM notice")
                    comps.append(comp("commodity", "Gas Supply Charge", amount, unit,
                                      market_reference="EPCOR system gas supply (OEB quarterly rate adjustment)",
                                      source_detail=page_detail + f"; OEB QRAM notice {context.notice_url}",
                                      notes=self._supply_note(context)))
                elif line.kind == "overrun_authorized":
                    comps.append(comp("delivery", "Authorized Overrun Charge (December 16 - April 30)", amount, unit,
                                      sub_component="conditional",
                                      notes="Conditional: gas taken December 16 - April 30 with EPCOR's prior "
                                            "authorization (interruptible at EPCOR's discretion), plus upstream and "
                                            "gas supply charges."))
                elif line.kind == "overrun_unauthorized":
                    comps.append(comp("delivery", "Unauthorized Overrun Charge (December 16 - April 30)", amount,
                                      unit, sub_component="conditional",
                                      notes="Conditional: gas taken December 16 - April 30 without EPCOR's prior "
                                            "authorization, plus upstream and gas supply charges."))
        if zone.key == "aylmer":
            supply = context.supply
            detail = (f"{zone.label} rates page, 'Gas supply charges' table; approved {context.case} Schedule A, "
                      f"PDF page {supply['page']}; OEB QRAM notice {context.notice_url}")
            comps += [
                comp("commodity", "Gas Supply Charge — PGCVA Reference Price",
                     _cents_to_dollars(supply["reference"]), "$/m³", source_detail=detail,
                     market_reference="EPCOR system gas supply (OEB quarterly rate adjustment)",
                     notes=self._supply_note(context)),
                comp("commodity", "Gas Supply Charge — GPRA Recovery Rate", _cents_to_dollars(supply["recovery"]),
                     "$/m³", source_detail=detail,
                     notes=f"Gas Purchase Rebalancing Account recovery; with the PGCVA reference price it makes up "
                           f"the {supply['total']:.4f}¢/m³ total gas supply charge."),
            ]
        carbon_date, carbon_note = carbon
        comps.append(RateComponent(
            "carbon", "Federal Carbon Charge", 0.0, "$/m³", effective_date=carbon_date.isoformat(),
            source_url=CRA_URL, source_detail="CRA fuel charge rates",
            notes=carbon_note + " EPCOR's rates page and approved schedules print no carbon row; the OEB QRAM notice "
                                "prints the federal and facility carbon charges as 0.00¢/m³."))
        record_notes = [
            f"EPCOR Natural Gas Limited Partnership, {zone.label} service area (OEB-regulated).",
            f"Values from EPCOR's rates page (effective {_display(context.effective)}), each confirmed in the OEB "
            f"Decision and Rate Order {context.case} Appendix A ({context.order_url}); EPCOR states the decision "
            "and order governs on any variance.",
            *notes,
            *([spec.note] if spec.note else []),
            *self._conditions(spec),
            "Published in cents per m³ and stored as $/m³. Taxes are not included.",
        ]
        return TariffRecord(
            utility_name=UTILITY_NAME, province="ON", utility_type="gas",
            tariff_name=f"{spec.name} ({zone.label})", tariff_code=spec.code, customer_class=spec.customer_class,
            sub_class=f"{zone.label} service area", description=page_class.description or None,
            eligibility=eligibility_text, usage_min=usage_min, usage_max=usage_max,
            usage_unit="m³/year" if (usage_min or usage_max) else None, rate_structure=spec.rate_structure,
            pricing_method="regulated", effective_date=max(context.effective, carbon_date).isoformat(),
            source_url=zone.page_url, source_page=f"{page_class.heading}; {context.case} Appendix A PDF page "
                                                  f"{order_page}",
            confidence="high", notes=" ".join(record_notes), components=comps,
        )

    @staticmethod
    def _columns(line: _Line, seasons: list) -> list[tuple[Optional[int], _Value]]:
        """One unseasoned value when every season prints the same value, else one per season."""
        if len(line.values) == 1 or len({(value.kind, value.amount, value.per) for value in line.values}) == 1:
            return [(None, line.values[0])]
        return list(enumerate(line.values))

    @staticmethod
    def _season_fields(season: Optional[dict]) -> dict:
        return {"season": season["label"], "season_months": season["months"]} if season else {}

    def _seasons(self, periods: list[str], section: str) -> list[dict]:
        """Season columns; the approved schedule's periods govern when the page prints different months."""
        printed = _order_periods(section)
        if printed is None:
            raise ValueError("approved season periods missing")
        page = [_period(text) for text in periods]
        order = [_period(text) for text in printed]
        seasons = []
        for page_period, order_period, page_text in zip(page, order, periods):
            if page_period is None or order_period is None:
                raise ValueError("season periods not identified")
            start, first, end, last = order_period
            differs = (page_period[0], page_period[2]) != (start, end)
            if last is None and not differs:
                last = page_period[3]
            label = f"{_MONTH_NAMES[start - 1]} {first} - {_MONTH_NAMES[end - 1]}" + (f" {last}" if last else "")
            seasons.append({"label": label, "months": f"{_MONTH_NAMES[start - 1][:3]}-{_MONTH_NAMES[end - 1][:3]}",
                            "page": page_text, "differs": differs})
        if any(season["differs"] for season in seasons):
            for season in seasons:
                season["differs"] = True
        return seasons

    def _rider(self, line: _Line, seasons: list, cents: set, dollars: set, context: _ZoneContext, order_page: int,
               today: date, comp, notes: list) -> list[RateComponent]:
        subject, count, span, ending = line.match.groups()
        end = _long_date(ending.title())
        if end is None or end < context.effective or end < today:
            raise ValueError(f"rider {subject!r} period ended or unreadable")
        subject = subject if subject != subject.lower() else " ".join(
            word if word in ("in", "of", "for", "and") else word.capitalize() for word in subject.split())
        name = f"Rate Rider for {subject} Recovery"
        period = f"Rider period: effective for {count} {span} ending {_display(end)} (as printed)."
        output = []
        for column, value in self._columns(line, seasons):
            extra = self._season_fields(seasons[column] if column is not None else None)
            suffix = f" ({seasons[column]['label']})" if column is not None else ""
            key = round(value.amount, 6)
            if value.kind == "cents" and value.per == "m³" and key in cents:
                output.append(comp("rider", name + suffix, _cents_to_dollars(value.amount), "$/m³",
                                   end_date=end.isoformat(), notes=period, **extra))
            elif value.kind == "dollars" and value.per == "month" and key in dollars:
                output.append(comp("rider", name + suffix, value.amount, "$/month", end_date=end.isoformat(),
                                   notes=period, **extra))
            elif value.kind == "cents" and value.per == "month" and key in dollars:
                printed = f"${value.amount:.2f} per month"
                output.append(comp(
                    "rider", name + suffix, value.amount, "$/month", end_date=end.isoformat(),
                    source_url=context.order_url or context.zone.page_url,
                    source_detail=(f"{context.case} Appendix A, PDF page {order_page}: '{printed}'; EPCOR's rates "
                                   f"page prints '{value.text}'"),
                    notes=period + f" The approved schedule prints {printed}, which governs over the page's "
                                   f"'{value.text}'.", **extra))
                message = (f"{name}: EPCOR's rates page prints '{value.text}'; the approved schedule prints "
                           f"{printed}, which is used.")
                if message not in notes:
                    notes.append(message)
            else:
                raise ValueError(f"rider {line.label!r} value {value.text!r} not confirmed by the approved schedule")
        return output

    @staticmethod
    def _supply_note(context: _ZoneContext) -> str:
        return (f"System gas (sales) customers: OEB-approved quarterly gas supply charge, passed through without "
                f"mark-up; the OEB QRAM notice ({context.case}) prints {context.notice_charge:.4f}¢/m³ effective "
                f"{_display(context.effective)}. Direct purchase customers buy gas from a marketer instead; that "
                "price is not included.")

    @staticmethod
    def _conditions(spec: ClassSpec) -> list[str]:
        if spec.code == "AYL-3":
            return ["Approved schedule conditions (not components): minimum annual volume shortfall, unauthorized "
                    "overrun and transition-period commodity charges apply only in those cases."]
        if spec.code == "AYL-5":
            return ["Approved schedule conditions (not components): 50,000 m³ minimum annual volume with a shortfall "
                    "charge; unauthorized overrun is billed at the Rate 1 delivery charge plus gas supply."]
        return []
