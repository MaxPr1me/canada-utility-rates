"""
atco_electric.py -- Scraper for ATCO Electric distribution rates (Alberta).

ATCO Electric Ltd. is the AUC-regulated wires utility for rural and northern
Alberta. Alberta's market is unbundled: these price schedules carry the
transmission (System Access Service), distribution and service charges only;
energy is billed separately by a retailer or the Rate of Last Resort provider.

Official sources, discovered each run from the rates page's AEM model JSON:
  https://electric.atco.com/en-ca/understanding-rates/rates.html
  - "Current Distribution Tariffs": the price-schedules PDF (index, schedules,
    price options and bound copies of Riders A, B, G, J and S)
  - "Current Rate Riders": the separately published Rider B, G, S and J PDFs

Building scope parsed live: D11, D13, D21, D31 and the priced part of T31.
Other published schedules are recorded as exclusions, never priced.
"""

from __future__ import annotations

import calendar
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable, Iterator, Optional
from urllib.parse import urljoin, urlsplit

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

logger = logging.getLogger(__name__)

# Seed data for ATCO Electric distribution rates.
SOURCE_URL = "https://www.atco.com/en-ca/for-home/electricity/understand-your-bill.html"
EFFECTIVE_DATE = "2024-01-01"

SEED_RESIDENTIAL = {
    "tariff_code": "D11",
    "basic_charge_per_day": 0.8186,   # $/day
    "distribution_rate": 0.0204,       # $/kWh
}

SEED_SMALL_COMMERCIAL = {
    "tariff_code": "D21",
    "basic_charge_per_day": 0.9754,   # $/day
    "distribution_rate": 0.0260,       # $/kWh
}

SEED_LARGE_COMMERCIAL = {
    "tariff_code": "D31",
    "basic_charge_per_day": 17.58,    # $/day
    "demand_charge": 5.4720,           # $/kW
    "distribution_rate": 0.0032,       # $/kWh
}

SITE_URL = "https://electric.atco.com/"
RATES_PAGE_URL = "https://electric.atco.com/en-ca/understanding-rates/rates.html"
RATES_MODEL_URLS = (
    "https://electric.atco.com/en-ca/understanding-rates/rates.model.json",
    "https://electric.atco.com/content/atco-electric/en-ca/home/understanding-rates/rates.model.json",
)
_ASSETS = "https://electric.atco.com/content/dam/atco-electric-website/en-ca/assets/understanding-rates/"
# Last known links, used only when the rates page cannot be read; the dates printed in the PDFs still gate them.
FALLBACK_SCHEDULES_URL = _ASSETS + "2026-01-01-atco-electric-price-schedules.pdf"
FALLBACK_RIDER_URLS = {
    "B": _ASSETS + "2026-01-01-rider-b.pdf",
    "G": _ASSETS + "2026-01-01-rider-g.pdf",
    "S": _ASSETS + "2026-10-01-rider-s-q4-2026.pdf",
    "J": _ASSETS + "2025-09-01-rider-j.pdf",
}

# Building-scope schedules: (tariff name, printed title, customer class, sub-class, rate structure).
SCHEDULES = {
    "D11": ("Standard Residential Service (Price Schedule D11)", "Standard Residential Service",
            "residential", "standard residential", "flat"),
    "D13": ("Time of Use Residential Service (Price Schedule D13)", "Time of Use Residential Service",
            "residential", "time of use residential (by request, at the company's discretion)", "tou"),
    "D21": ("Standard Small General Service (Price Schedule D21)", "Standard Small General Service",
            "commercial", "small general service", "demand"),
    "D31": ("Large General Service - Distribution Connected (Price Schedule D31)",
            "Large General Service / Industrial Distribution Connected",
            "commercial", "large general service/industrial, distribution connected", "demand"),
    "T31": ("Large General Service - Transmission Connected (Price Schedule T31)",
            "Large General Service / Industrial Transmission Connected",
            "industrial", "large general service/industrial, transmission connected", "demand"),
}

# Published schedules outside building scope: reported, never priced.
EXCLUDED_SCHEDULES = {
    "D22": "Small Technology: customer-owned fixtures up to 1 kW, not building service",
    "D23": "Electric vehicle fast charging service (excluded process load)",
    "D24": "Small general service in isolated industrial areas (excluded by user decision)",
    "D25": "Irrigation pumping service (excluded process load)",
    "D26": "REA irrigation pumping service (excluded process load)",
    "D32": "Generator interconnection and standby power (excluded)",
    "D33": "Transmission Opportunity Rate, distribution connected: opportunity energy above a D31 base demand (excluded)",
    "T33": "Transmission Opportunity Rate, transmission connected: opportunity energy above a T31 base demand (excluded)",
    "D34": "Large general service in isolated industrial areas (excluded by user decision)",
    "D41": "Small oilfield and pumping power (excluded process load)",
    "D44": "Small oilfield and pumping power in isolated industrial areas (excluded process load)",
    "D51": "REA farm service (excluded)",
    "D52": "REA farm service excluding wires service provider functions (excluded)",
    "D56": "Farm service (excluded)",
    "D61": "Street lighting service (excluded)",
    "D63": "Private lighting service (excluded)",
}

RIDER_NAMES = {
    "B": "Balancing Pool Adjustment",
    "G": "Temporary Adjustment",
    "S": "SAS Deferral Adjustment",
    "J": "PBR Re-Opener Refund",
}
_RIDER_HEADINGS = {"B": r"Balancing Pool", "G": r"Temporary Adjustment", "S": r"SAS", "J": r"PBR Re-Opener|Interim Adjustment"}
_RIDER_ORDER = "ABGSJ"

_CENTS = "¢ȼ"
_CELL = re.compile(
    r"\s*(?:(?P<dash>-)(?=\s|$)"
    r"|(?P<dollar>\$)?\s?(?P<num>\d+(?:\.\d+)?)\s?"
    rf"(?P<unit>[{_CENTS}]/kV\.A/day|[{_CENTS}]/kW/day|[{_CENTS}]/kW\.h|[{_CENTS}]/day|/kW/day|kW/day|/kW\.h|/day))"
)
_CELL_UNITS = {"/kV.A/day": "$/kVA/day", "/kW/day": "$/kW/day", "kW/day": "$/kW/day", "/kW.h": "$/kWh", "/day": "$/day"}
_TOLERANCE_CENTS = 0.005 + 1e-9
_PRICE_LINE = re.compile(r"Price(?:$|\s+(?:The charge|Charges for))")
_TABLE_END = re.compile(r"(?:The billing demand|On Peak rates|Application)\b")


class _Reject(Exception):
    """A class or rider cannot be proven complete and current from the official documents."""


@dataclass(frozen=True)
class _Cell:
    dollars: float
    unit: str
    cents: float


@dataclass(frozen=True)
class _Column:
    kind: str  # "customer", "demand" or "energy"
    label: str
    unit: str
    tou_period: Optional[str] = None
    tou_hours: Optional[str] = None
    tier_number: Optional[int] = None
    tier_threshold: Optional[float] = None
    tier_unit: Optional[str] = None


@dataclass
class _RiderDoc:
    letter: str
    url: str
    page: int
    embedded: bool
    effective: str
    end: Optional[str]
    unit: str
    approval: str
    values: dict[str, float] = field(default_factory=dict)
    exclusions: Optional[str] = None
    quarter: Optional[str] = None
    quarter_end: Optional[str] = None
    basis: Optional[str] = None


def _iso(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    try:
        return datetime.strptime(" ".join(text.replace(",", ", ").split()), "%B %d, %Y").date().isoformat()
    except ValueError:
        return None


def _footer_date(flat: str) -> Optional[str]:
    match = re.search(r"Effective:\s*(\d{4}) (\d{2}) (\d{2})\b", flat)
    if not match:
        return None
    try:
        return date(*(int(part) for part in match.groups())).isoformat()
    except ValueError:
        return None


def _flat(text: str) -> str:
    return " ".join(text.split())


# ── Discovery ────────────────────────────────────────────────────────

def _html_fragments(node: Any) -> Iterator[str]:
    if isinstance(node, dict):
        for value in node.values():
            yield from _html_fragments(value)
    elif isinstance(node, list):
        for value in node:
            yield from _html_fragments(value)
    elif isinstance(node, str) and "<a" in node and ".pdf" in node:
        yield node


def discover_documents(model: Any, base_url: str = SITE_URL) -> dict:
    """Return current document links from the rates page's AEM model JSON.

    Only the "Current Distribution Tariffs" and "Current Rate Riders" cards are read; archived
    links are ignored. Result: {"schedules": {url: link date}, "riders": {letter: {url: link date}}
    or None when the current riders card is absent}.
    """
    schedules: dict[str, Optional[str]] = {}
    riders: dict[str, dict[str, Optional[str]]] = {}
    riders_card = False
    for fragment in _html_fragments(model):
        soup = parse_html(fragment)
        heading = " ".join(tag.get_text(" ", strip=True) for tag in soup.find_all(re.compile(r"^h[1-6]$")))
        if re.search(r"\bCurrent Distribution Tariffs\b", heading, re.I):
            section = "schedules"
        elif re.search(r"\bCurrent Rate Riders\b", heading, re.I):
            section = "riders"
            riders_card = True
        else:
            continue
        for anchor in soup.find_all("a", href=True):
            if not urlsplit(anchor["href"]).path.lower().endswith(".pdf"):
                continue
            label = _flat(anchor.get_text(" ", strip=True))
            block = anchor.find_parent(["p", "li", "td"]) or anchor
            dated = re.search(r"Effective\s+([A-Z][a-z]+\s+\d{1,2},\s*\d{4})", _flat(block.get_text(" ", strip=True)))
            url = urljoin(base_url, anchor["href"])
            when = _iso(dated.group(1)) if dated else None
            rider = re.match(r"Rider ([A-Z])\b", label)
            if section == "schedules" and re.search(r"\bDistribution Tariffs\b", label, re.I):
                schedules[url] = when
            elif section == "riders" and rider:
                riders.setdefault(rider.group(1), {})[url] = when
    return {"schedules": schedules, "riders": riders if riders_card else None}


# ── Price-table parsing ──────────────────────────────────────────────

def _parse_cells(text: str) -> Optional[list[Optional[_Cell]]]:
    """Parse a whole row remainder into cells ("-" = no charge); None if anything else is present."""
    cells: list[Optional[_Cell]] = []
    position, text = 0, text.rstrip()
    while position < len(text):
        match = _CELL.match(text, position)
        if not match:
            return None
        position = match.end()
        if match.group("dash"):
            cells.append(None)
            continue
        unit_token = match.group("unit")
        in_cents = unit_token[0] in _CENTS
        if in_cents == bool(match.group("dollar")):
            return None
        number = float(match.group("num"))
        cents = number if in_cents else round(number * 100.0, 6)
        cells.append(_Cell(round(cents / 100.0, 6), _CELL_UNITS[unit_token.lstrip(_CENTS)], cents))
    return cells or None


def _row(lines: list[str], label: str) -> list[Optional[_Cell]]:
    hits = []
    for line in lines:
        for match in re.finditer(rf"(?:^|\s){label}\s", line):
            cells = _parse_cells(line[match.end():])
            if cells is not None:
                hits.append(cells)
                break
    if len(hits) != 1:
        raise _Reject(f"{label} row {'missing from' if not hits else 'repeated in'} the price table")
    return hits[0]


def _price_region(lines: list[str]) -> list[str]:
    start = next((index for index, line in enumerate(lines) if _PRICE_LINE.match(line)), None)
    if start is None:
        raise _Reject("Price section missing")
    end = next((index for index in range(start + 1, len(lines)) if _TABLE_END.match(lines[index])), None)
    if end is None:
        raise _Reject("end of the price table not found")
    return lines[start + 1:end]


def _reconcile(columns: list[_Column], rows: dict[str, list[Optional[_Cell]]], total: list[Optional[_Cell]]) -> None:
    """Each column's printed parts must carry the column unit and sum to its TOTAL PRICE cell."""
    for index, column in enumerate(columns):
        parts = [cells[index] for cells in rows.values() if cells[index] is not None]
        printed = total[index]
        if any(part.unit != column.unit for part in parts) or (printed is not None and printed.unit != column.unit):
            raise _Reject(f"{column.label} column is not priced in {column.unit}")
        if printed is None:
            if parts:
                raise _Reject(f"{column.label} column has charges but no TOTAL PRICE")
            continue
        if abs(sum(part.cents for part in parts) - printed.cents) > _TOLERANCE_CENTS:
            raise _Reject(f"{column.label} components do not sum to the printed TOTAL PRICE")


def _tou_hours(flat: str) -> tuple[str, str]:
    match = re.search(
        r"On Peak rates will be applied between the hours of (\d{1,2}) ?([ap])\.m\. to (\d{1,2}) ?([ap])\.m\.\s*"
        r"Off Peak rates will be applied before (\d{1,2}) ?([ap])\.m\. and after (\d{1,2}) ?([ap])\.m\.", flat)
    if not match:
        raise _Reject("On Peak/Off Peak hours missing")
    start, start_ampm, end, end_ampm, before, before_ampm, after, after_ampm = match.groups()
    if (start, start_ampm) != (before, before_ampm) or (end, end_ampm) != (after, after_ampm):
        raise _Reject("Off Peak hours do not complement the On Peak hours")
    return (f"{start} {start_ampm}.m. to {end} {end_ampm}.m.",
            f"Before {start} {start_ampm}.m. and after {end} {end_ampm}.m.")


def _billing_demand_rules(flat: str) -> list[str]:
    return [_flat(rule) for rule in re.findall(
        r"(The billing demand for the [^:]+? shall be the higher of: .*?)"
        r"(?= Sheet \d+ of \d+| Application\b| The billing demand for| If energy is also taken| For non-demand metered|$)",
        flat)]


# ── Riders ───────────────────────────────────────────────────────────

def _parse_rider_page(page: DocumentPage, url: str, embedded: bool) -> Optional[_RiderDoc]:
    """Parse one rider page (separate PDF or bound copy); None when the page is not a modelled rider."""
    head = "\n".join(page.text.splitlines()[:3])
    match = re.search(r"^Rider ([A-Z])\b(.*)$", head, re.M)
    if not match or match.group(1) not in RIDER_NAMES:
        return None
    letter, heading = match.group(1), match.group(2)
    if not re.search(_RIDER_HEADINGS[letter], heading):
        raise _Reject(f"Rider {letter} heading {heading.strip()!r} not recognised")
    flat = _flat(page.text)
    effective = _footer_date(flat)
    period = re.search(r"energy consumption effective (?:from )?([A-Z][a-z]+ \d{1,2}, \d{4})"
                       r"(?: to ([A-Z][a-z]+ \d{1,2}, \d{4}))?", flat)
    unit = re.search(rf"Price Schedule Charge \(([{_CENTS}]/\.?kW\.h|%)\)", flat)
    approval = re.search(r"Approved in ((?:Decision|Disposition) [\w-]+)", flat)
    if not effective or not period or not unit or not approval:
        raise _Reject(f"Rider {letter} effective date, consumption period, unit or approval missing")
    end = _iso(period.group(2)) if period.group(2) else None
    if _iso(period.group(1)) != effective or (period.group(2) and (not end or end < effective)):
        raise _Reject(f"Rider {letter} consumption period does not match its effective date {effective}")
    percent = unit.group(1) == "%"
    doc = _RiderDoc(letter, url, page.page_number, embedded, effective, end, "%" if percent else "$/kWh", approval.group(1))
    for line in page.text.splitlines():
        row = re.search(r"(?:^|\s)([DT]\d{2}) \S.*? (-?\d+\.\d+)(%?)$", line)
        if not row:
            continue
        code, number, sign = row.groups()
        if code in doc.values or bool(sign) != percent:
            raise _Reject(f"Rider {letter} row {code} is repeated or not in the table unit")
        doc.values[code] = float(number) if percent else round(float(number) / 100.0, 6)
    if not doc.values:
        raise _Reject(f"Rider {letter} rate table missing")
    note = re.search(rf"Note: Rider {letter} does not apply to (Rider [A-Z](?:, Rider [A-Z])*,? and Rider [A-Z])", flat)
    doc.exclusions = note.group(1) if note else None
    if letter == "S":
        quarter = re.search(r"\bQ([1-4])-(\d{4})\b", flat)
        if not quarter:
            raise _Reject("Rider S quarter label missing")
        number, year = int(quarter.group(1)), int(quarter.group(2))
        if date(year, 3 * number - 2, 1).isoformat() != effective:
            raise _Reject("Rider S quarter label does not match its effective date")
        doc.quarter = f"Q{number}-{year}"
        doc.quarter_end = date(year, 3 * number, calendar.monthrange(year, 3 * number)[1]).isoformat()
    if percent:
        basis = re.search(r"applies as a percentage \(%\) of (total base .+?) by rate class", flat)
        if not basis:
            raise _Reject(f"Rider {letter} percentage base not stated")
        doc.basis = basis.group(1)
    return doc


def _select_rider(letter: str, code: str, candidates: list[_RiderDoc], today: str) -> tuple[_RiderDoc, list[_RiderDoc]]:
    """Latest rider copy in effect by start date; same-dated copies must agree for the class."""
    current = [doc for doc in candidates if doc.effective <= today]
    if not current:
        raise _Reject(f"no Rider {letter} document in effect")
    latest = max(doc.effective for doc in current)
    tied = [doc for doc in current if doc.effective == latest]
    if any(code not in doc.values for doc in tied):
        raise _Reject(f"Rider {letter} ({latest}) has no {code} row")
    if len({(doc.values[code], doc.unit, doc.end) for doc in tied}) != 1:
        raise _Reject(f"Rider {letter} copies dated {latest} disagree for {code}")
    return next((doc for doc in tied if not doc.embedded), tied[0]), tied


def _rider_component(chosen: _RiderDoc, tied: list[_RiderDoc], code: str) -> RateComponent:
    detail = f"PDF page {chosen.page}; Rider {chosen.letter} table, row {code}"
    others = [doc for doc in tied if doc is not chosen]
    if others:
        detail += "; same value in " + ", ".join(
            f"{'price-schedules PDF' if doc.embedded else doc.url} page {doc.page}" for doc in others)
    period = f"from {chosen.effective}" + (f" to {chosen.end}" if chosen.end else "")
    if chosen.unit == "%":
        notes = f"Percentage of {chosen.basis}, {period}."
    elif chosen.letter == "S":
        notes = (f"{chosen.quarter} quarterly System Access Service (SAS) deferral rider per kWh of energy consumption "
                 f"from {chosen.effective}; no end date is printed (replaced quarterly).")
    elif chosen.letter == "B":
        notes = f"Flows through the AESO Balancing Pool amount per kWh of energy consumption {period}."
    else:
        notes = f"{RIDER_NAMES[chosen.letter]} per kWh of energy consumption {period}."
    notes += (f" Positive = charge, negative = refund. Approved in {chosen.approval}."
              + (f" Does not apply to {chosen.exclusions}." if chosen.exclusions else ""))
    return RateComponent(
        "rider", f"Rider {chosen.letter} - {RIDER_NAMES[chosen.letter]}", chosen.values[code], chosen.unit,
        effective_date=chosen.effective, end_date=chosen.end, source_url=chosen.url, source_detail=detail, notes=notes)


def _schedule_pages(pages: list[DocumentPage]) -> dict[str, list[DocumentPage]]:
    grouped: dict[str, list[DocumentPage]] = {}
    for page in pages:
        head = "\n".join(page.text.splitlines()[:2])
        match = re.search(r"^(?:ATCO Electric Distribution\s+)?Price Schedule ([DT]\d{2})\s*$", head, re.M)
        if match:
            grouped.setdefault(match.group(1), []).append(page)
    return grouped


class ATCOElectricScraper(BaseScraper):
    """Scrape ATCO Electric distribution rates for Alberta."""

    def __init__(self):
        super().__init__(utility_name="ATCO Electric", province="AB")
        self.today: Optional[date] = None
        self.rejected: dict[str, str] = {}
        self.excluded_published: dict[str, str] = {}
        self.unmodelled_published: dict[str, str] = {}

    def scrape(self) -> list[TariffRecord]:
        """
        Parse the current official price schedules and riders.
        Falls back to labelled seed data only when nothing can be proven live.
        """
        live_records = self._try_live_scrape()
        if live_records:
            self.logger.info("Successfully scraped %d ATCO Electric tariffs from live site", len(live_records))
            return live_records
        self.logger.warning("Live scrape failed -- using seed data for ATCO Electric")
        return self.mark_fallback(self._seed_data())

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Return live-parsed classes only; classes that fail are dropped, never replaced by seeds."""
        schedules_url, edition, rider_links = self._discover()
        try:
            pages = extract_pdf_pages(self.fetch_bytes(schedules_url))
        except Exception as exc:
            self.logger.warning("ATCO Electric price schedules unavailable (%s): %s", schedules_url, exc)
            return None
        if not pages:
            self.logger.warning("ATCO Electric price schedules unreadable: %s", schedules_url)
            return None
        rider_documents = []
        for letter, links in rider_links.items():
            for url, link_date in links.items():
                try:
                    rider_pages = extract_pdf_pages(self.fetch_bytes(url))
                except Exception as exc:
                    self.logger.warning("ATCO Electric Rider %s unavailable (%s): %s", letter, url, exc)
                    continue
                if rider_pages:
                    rider_documents.append((url, rider_pages, link_date))
        records = self.parse_schedule_pages(
            pages, schedules_url, rider_documents, today=self.today or date.today(), edition_date=edition)
        return self.mark_live_parsed(records) if records else None

    def _discover(self) -> tuple[str, Optional[str], dict[str, dict[str, Optional[str]]]]:
        """Current price-schedules link (and its printed edition date) plus current rider links."""
        fallback_riders = {letter: {url: None} for letter, url in FALLBACK_RIDER_URLS.items()}
        for model_url in RATES_MODEL_URLS:
            try:
                found = discover_documents(json.loads(self.fetch_page(model_url)))
            except Exception as exc:
                self.logger.warning("ATCO Electric rates page model unavailable (%s): %s", model_url, exc)
                continue
            if len(found["schedules"]) != 1:
                self.logger.warning("ATCO Electric rates page lists %d current distribution tariffs", len(found["schedules"]))
                continue
            (url, edition), = found["schedules"].items()
            riders = found["riders"]
            if riders is None:
                self.logger.warning("ATCO Electric current rate riders not listed; using last known rider links")
                riders = fallback_riders
            return url, edition, {letter: links for letter, links in riders.items() if letter in RIDER_NAMES}
        self.logger.warning("ATCO Electric document discovery failed; using last known document links")
        return FALLBACK_SCHEDULES_URL, None, fallback_riders

    def parse_schedule_pages(
        self,
        pages: list[DocumentPage],
        source_url: str,
        rider_documents: Iterable[tuple] = (),
        today: Optional[date] = None,
        edition_date: Optional[str] = None,
    ) -> list[TariffRecord]:
        """Build live tariffs from price-schedule pages and rider documents; each class succeeds or fails alone.

        `rider_documents` holds (url, pages[, link date]) for separately published rider PDFs; the rider
        copies bound into the price-schedules PDF are candidates too. Results of the audit are left in
        `self.rejected`, `self.excluded_published` and `self.unmodelled_published`.
        """
        today_iso = (today or date.today()).isoformat()
        self.rejected, self.excluded_published, self.unmodelled_published = {}, {}, {}
        listed: set[str] = set()
        for page in pages:
            if "PRICE SCHEDULE INDEX" in page.text:
                listed.update(re.findall(r"Price Schedule ([DT]\d{2})\b", page.text))
        for code in sorted(listed - set(SCHEDULES)):
            if code in EXCLUDED_SCHEDULES:
                self.excluded_published[code] = EXCLUDED_SCHEDULES[code]
                self.logger.info("ATCO Electric Price Schedule %s excluded: %s", code, EXCLUDED_SCHEDULES[code])
            else:
                self.unmodelled_published[code] = "published price schedule not modelled"
                self.logger.warning("ATCO Electric Price Schedule %s is published but not modelled (gap)", code)

        candidates: dict[str, list[_RiderDoc]] = {}
        sources = [(source_url, pages, None, True)] + [
            (document[0], document[1], document[2] if len(document) > 2 else None, False) for document in rider_documents]
        for url, document_pages, link_date, embedded in sources:
            for page in document_pages:
                try:
                    rider = _parse_rider_page(page, url, embedded)
                except _Reject as exc:
                    self.logger.warning("ATCO Electric rider page ignored (%s page %d): %s", url, page.page_number, exc)
                    continue
                if rider is None:
                    continue
                if link_date and rider.effective != link_date:
                    self.logger.warning("ATCO Electric Rider %s at %s is dated %s but linked as effective %s",
                                        rider.letter, url, rider.effective, link_date)
                    continue
                candidates.setdefault(rider.letter, []).append(rider)

        grouped = _schedule_pages(pages)
        records: list[TariffRecord] = []
        for code in SCHEDULES:
            try:
                records.append(self._schedule_record(code, grouped.get(code, []), source_url, candidates, today_iso, edition_date))
            except _Reject as exc:
                self.rejected[code] = str(exc)
                self.logger.warning("ATCO Electric Price Schedule %s not live-verified: %s", code, exc)
        return records

    def _schedule_record(
        self,
        code: str,
        pages: list[DocumentPage],
        source_url: str,
        candidates: dict[str, list[_RiderDoc]],
        today: str,
        edition_date: Optional[str],
    ) -> TariffRecord:
        name, title, customer_class, sub_class, structure = SCHEDULES[code]
        if not pages:
            raise _Reject("price schedule pages missing")
        sheets: dict[int, DocumentPage] = {}
        counts: set[int] = set()
        for page in pages:
            sheet = re.search(r"Sheet (\d+) of (\d+)", page.text)
            if not sheet or int(sheet.group(1)) in sheets:
                raise _Reject(f"sheet number missing or repeated on PDF page {page.page_number}")
            sheets[int(sheet.group(1))] = page
            counts.add(int(sheet.group(2)))
        if len(counts) != 1 or sorted(sheets) != list(range(1, counts.pop() + 1)):
            raise _Reject("continuation sheets incomplete")
        ordered = [sheets[number] for number in sorted(sheets)]
        dates = {_footer_date(_flat(page.text)) for page in ordered}
        if len(dates) != 1 or None in dates:
            raise _Reject("sheet effective dates missing or inconsistent")
        effective = dates.pop()
        if effective > today:
            raise _Reject(f"effective date {effective} is in the future")
        if edition_date and effective != edition_date:
            raise _Reject(f"sheets dated {effective} but the current link says effective {edition_date}")
        flat = " ".join(_flat(page.text) for page in ordered)
        first = _flat(ordered[0].text)
        approval = re.search(r"Approved in (Decision [\w-]+)(?: \(Dated:? ([A-Z][a-z]+ \d{1,2}, \d{4})\))?", flat)
        availability = re.search(r"\bAvailability (.+?) Price (?:The charge|Charges for)", first)
        if title not in first or not approval or not availability:
            raise _Reject("title, availability or approving decision missing")
        supersedes = re.search(r"Supersedes:\s*(\d{4}) (\d{2}) (\d{2})", flat)
        region = _price_region(ordered[0].text.splitlines())
        table = _flat(" ".join(region))

        customer = _Column("customer", "Customer Charge", "$/day")
        demand_max = None
        extra_notes: list[str] = []
        if code in ("D11", "D13"):
            if "Customer Charge Energy Charge" not in table:
                raise _Reject("Customer Charge / Energy Charge header missing")
            if code == "D11":
                columns = [customer, _Column("energy", "Energy Charge", "$/kWh")]
            else:
                if "On Peak Off Peak" not in table:
                    raise _Reject("On Peak / Off Peak header missing")
                on_hours, off_hours = _tou_hours(flat)
                columns = [customer,
                           _Column("energy", "Energy Charge (On Peak)", "$/kWh", tou_period="on-peak", tou_hours=on_hours),
                           _Column("energy", "Energy Charge (Off Peak)", "$/kWh", tou_period="off-peak", tou_hours=off_hours)]
                extra_notes.append(f"On Peak: {on_hours}; Off Peak: {off_hours[0].lower() + off_hours[1:]}; "
                                   "the schedule prints no weekday, weekend or holiday distinction.")
        elif code == "D21":
            blocks = re.findall(r"(\d+) kW\.h per kW\b", table)
            limit = re.search(r"Not applicable for any service in excess of (\d+) kW\b", first)
            if ("Customer Charge Demand Charge Energy Charge" not in table or "For energy in excess" not in table
                    or "For the first" not in table or len(blocks) != 2 or len(set(blocks)) != 1 or not limit):
                raise _Reject("energy block header or availability limit missing")
            block, tier_unit = float(blocks[0]), "kWh per kW of billing demand"
            demand_max = float(limit.group(1))
            columns = [customer, _Column("demand", "Demand Charge", "$/kW/day"),
                       _Column("energy", f"Energy Charge (first {block:g} {tier_unit})", "$/kWh",
                               tier_number=1, tier_threshold=block, tier_unit=tier_unit),
                       _Column("energy", f"Energy Charge (in excess of {block:g} {tier_unit})", "$/kWh",
                               tier_number=2, tier_threshold=block, tier_unit=tier_unit)]
        else:
            lead = "Customer Charge Demand Charge Energy Charge" if code == "D31" else "Demand Charge Energy Charge"
            first_block = re.search(r"For the first (\d+) kW of\b", table)
            over = re.search(r"billing demand over (?:demand )?(\d+) kW\b", table)
            if lead not in table or not first_block or not over or first_block.group(1) != over.group(1):
                raise _Reject("demand block header missing or inconsistent")
            block, tier_unit = float(first_block.group(1)), "kW of billing demand"
            columns = ([customer] if code == "D31" else []) + [
                _Column("demand", f"Demand Charge (first {block:g} kW of billing demand)", "$/kW/day",
                        tier_number=1, tier_threshold=block, tier_unit=tier_unit),
                _Column("demand", f"Demand Charge (billing demand over {block:g} kW)", "$/kW/day",
                        tier_number=2, tier_threshold=block, tier_unit=tier_unit),
                _Column("energy", "Energy Charge", "$/kWh")]

        rows = {"Transmission": [None] * len(columns) if code == "T31" else _row(region, "Transmission"),
                "Distribution": _row(region, "Distribution"), "Service": _row(region, "Service")}
        for label, cells in rows.items():
            if len(cells) != len(columns):
                raise _Reject(f"{label} row has {len(cells)} cells, expected {len(columns)}")
        if code == "T31":
            priced = re.search(rf"(\d+(?:\.\d+)?) [{_CENTS}]/kW/day \+ Current\b", table)
            if not priced or not all(phrase in table for phrase in (
                    "Transmission", "Current AESO DTS Rate Schedule", "under frequency load shedding", "Charges per current")):
                raise _Reject("AESO DTS flow-through wording or priced TOTAL PRICE changed")
            total = [_Cell(round(float(priced.group(1)) / 100.0, 6), "$/kW/day", float(priced.group(1))), None, None]
        else:
            total = _row(region, "TOTAL PRICE")
            if len(total) != len(columns):
                raise _Reject(f"TOTAL PRICE row has {len(total)} cells, expected {len(columns)}")
        _reconcile(columns, rows, total)

        page_label = (f"PDF page {ordered[0].page_number}" if len(ordered) == 1
                      else f"PDF pages {ordered[0].page_number}-{ordered[-1].page_number}")
        components: list[RateComponent] = []
        for index, column in enumerate(columns):
            for label, cells in rows.items():
                cell = cells[index]
                if cell is None:
                    continue
                kind = "transmission" if label == "Transmission" else {
                    "customer": "fixed", "demand": "demand", "energy": "distribution"}[column.kind]
                components.append(RateComponent(
                    kind, f"{label} {column.label}", cell.dollars, column.unit,
                    tier_number=column.tier_number, tier_threshold=column.tier_threshold, tier_unit=column.tier_unit,
                    tou_period=column.tou_period, tou_hours=column.tou_hours,
                    demand_unit="kW" if column.kind == "demand" else None,
                    effective_date=effective, source_url=source_url,
                    source_detail=f"PDF page {ordered[0].page_number}; Price Schedule {code}, {label} row, {column.label} column",
                    notes=("Transmission (System Access Service) charge as printed in this schedule."
                           if label == "Transmission" else None),
                ))

        if code == "D31":
            charge = re.search(rf"Charge for Deficient Power Factor (\d+\.\d+) [{_CENTS}]/kV\.A/day", flat)
            rule = re.search(
                rf"power factor which is less than (\d+)%, an additional charge for deficient power factor of (\d+\.\d+) "
                rf"[{_CENTS}]/kV\.A/day will be applied to the difference between the highest metered kV\.A demand and "
                r"(\d+)% of the highest metered kW demand", flat)
            if not charge or not rule or charge.group(1) != rule.group(2):
                raise _Reject("deficient power factor charge missing or inconsistent")
            pf_page = next(page.page_number for page in ordered if charge.group(0) in _flat(page.text))
            components.append(RateComponent(
                "demand", "Charge for Deficient Power Factor", round(float(charge.group(1)) / 100.0, 6), "$/kVA/day",
                demand_unit="kVA", sub_component="conditional", effective_date=effective, source_url=source_url,
                source_detail=f"PDF page {pf_page}; Price Schedule D31, Charge for Deficient Power Factor",
                notes=(f"Conditional: applies only when the customer's power factor is below {rule.group(1)}%; charged per "
                       f"kVA per day on the difference between the highest metered kVA demand and {rule.group(3)}% of the "
                       "highest metered kW demand in the billing period."),
            ))

        rules = _billing_demand_rules(flat)
        if code in ("D21", "D31", "T31"):
            wanted = [rule for rule in rules if code != "T31" or "Distribution and Service" in rule]
            if not wanted:
                raise _Reject("billing demand rule missing")
            extra_notes.append("Billing demand: " + " ".join(wanted))

        rider_notes: list[str] = []
        listed = list(dict.fromkeys(re.findall(r"\(Rider ([A-Z])\)", flat)))
        for letter in sorted(listed, key=lambda value: _RIDER_ORDER.find(value) if value in _RIDER_ORDER else 99):
            if letter == "A":
                rider_notes.append("Conditional: Rider A (Municipal Assessment: municipal tax and franchise fee) is a "
                                   "percentage that varies by municipality; it is not included.")
                continue
            if letter not in RIDER_NAMES:
                raise _Reject(f"Rider {letter} is listed but not modelled")
            chosen, tied = _select_rider(letter, code, candidates.get(letter, []), today)
            if chosen.end and chosen.end < today:
                rider_notes.append(f"Rider {letter} ({RIDER_NAMES[letter]}) applied from {chosen.effective} to "
                                   f"{chosen.end} and has ended; it is not included.")
                continue
            if chosen.quarter_end and chosen.quarter_end < today:
                raise _Reject(f"Rider {letter} {chosen.quarter} ended {chosen.quarter_end} and no later rider was found")
            components.append(_rider_component(chosen, tied, code))

        options = re.findall(r"([A-Z][A-Za-z -]*?[a-z]) \(Option ([A-Z])\)", flat)
        approved = approval.group(1) + (f" (dated {approval.group(2)})" if approval.group(2) else "")
        notes = [f"Wires charges from ATCO Electric Price Schedule {code}, approved in {approved}, effective {effective}"
                 + (f" (supersedes {'-'.join(supersedes.groups())})" if supersedes else "") + "."]
        if code == "T31":
            notes.append(
                "Transmission charges are the current AESO DTS Rate Schedule charges less the under frequency load "
                "shedding credit, plus energy charges per that schedule; they flow through from the AESO tariff, are not "
                f"priced in this schedule and are not included. Only the printed Distribution and Service demand charges "
                f"for the first {columns[0].tier_threshold:g} kW of billing demand are included (they reconcile to the "
                f"printed {total[0].cents:g} ¢/kW/day); billing demand over {columns[0].tier_threshold:g} kW and energy "
                "carry no printed distribution or service charge. Deficient power factor charges follow the AESO DTS "
                "Rate Schedule.")
        else:
            notes.append("Transmission, distribution and service rows are separate components that reconcile to the "
                         "printed TOTAL PRICE.")
        notes.append("Energy supply is billed separately by a retailer or the Rate of Last Resort provider and is not included.")
        notes.extend(extra_notes + rider_notes)
        if options:
            notes.append("Conditional price options are not included: "
                         + "; ".join(f"{option} (Option {letter})" for option, letter in dict.fromkeys(options)) + ".")
        notes.append("No bill total is calculated.")
        return TariffRecord(
            utility_name="ATCO Electric", province="AB", utility_type="electricity",
            tariff_name=name, tariff_code=code, customer_class=customer_class, sub_class=sub_class,
            eligibility=availability.group(1).replace("• ", "").strip(),
            demand_max_kw=demand_max, rate_structure=structure, pricing_method="regulated",
            effective_date=max(component.effective_date for component in components),
            source_url=source_url, source_page=f"{page_label}; Price Schedule {code}",
            confidence="high", notes=" ".join(notes), components=components,
        )

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # -- Residential (Rate D11) -------------------------------------------
        records.append(TariffRecord(
            utility_name="ATCO Electric",
            province="AB",
            utility_type="electricity",
            tariff_name="Residential Distribution (Rate D11)",
            tariff_code=SEED_RESIDENTIAL["tariff_code"],
            customer_class="residential",
            rate_structure="flat",
            effective_date=EFFECTIVE_DATE,
            source_url=SOURCE_URL,
            confidence="high",
            notes=(
                "Distribution charges only; energy supply from retailer. "
                "ATCO Electric serves rural and northern Alberta. "
                "Regulated by the Alberta Utilities Commission (AUC)."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_day"],
                    charge_unit="$/day",
                    confidence="high",
                    notes="Daily fixed distribution charge",
                ),
                RateComponent(
                    component_type="distribution",
                    component_name="Distribution Charge",
                    charge_value=SEED_RESIDENTIAL["distribution_rate"],
                    charge_unit="$/kWh",
                    confidence="high",
                    notes="Variable distribution charge per kWh consumed",
                ),
            ],
        ))

        # -- Small Commercial (Rate D21) --------------------------------------
        records.append(TariffRecord(
            utility_name="ATCO Electric",
            province="AB",
            utility_type="electricity",
            tariff_name="Small General Service Distribution (Rate D21)",
            tariff_code=SEED_SMALL_COMMERCIAL["tariff_code"],
            customer_class="commercial",
            sub_class="small general service",
            rate_structure="flat",
            effective_date=EFFECTIVE_DATE,
            source_url=SOURCE_URL,
            confidence="high",
            eligibility="General service customers with demand under 150 kVA",
            demand_max_kw=150,
            notes=(
                "Distribution charges only; energy supply from retailer. "
                "Applies to commercial customers with demand below 150 kVA. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_SMALL_COMMERCIAL["basic_charge_per_day"],
                    charge_unit="$/day",
                    confidence="high",
                    notes="Daily fixed distribution charge",
                ),
                RateComponent(
                    component_type="distribution",
                    component_name="Distribution Charge",
                    charge_value=SEED_SMALL_COMMERCIAL["distribution_rate"],
                    charge_unit="$/kWh",
                    confidence="high",
                    notes="Variable distribution charge per kWh consumed",
                ),
            ],
        ))

        # -- Large Commercial (Rate D31) --------------------------------------
        records.append(TariffRecord(
            utility_name="ATCO Electric",
            province="AB",
            utility_type="electricity",
            tariff_name="Large General Service Distribution (Rate D31)",
            tariff_code=SEED_LARGE_COMMERCIAL["tariff_code"],
            customer_class="commercial",
            sub_class="large general service",
            rate_structure="demand",
            effective_date=EFFECTIVE_DATE,
            source_url=SOURCE_URL,
            confidence="high",
            eligibility="General service customers with demand of 150 kVA or greater",
            demand_min_kw=150,
            notes=(
                "Distribution charges only; energy supply from retailer. "
                "Demand-based tariff for large commercial customers. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_LARGE_COMMERCIAL["basic_charge_per_day"],
                    charge_unit="$/day",
                    confidence="high",
                    notes="Daily fixed distribution charge",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_LARGE_COMMERCIAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    confidence="high",
                    notes="Applied to billing demand (kW)",
                ),
                RateComponent(
                    component_type="distribution",
                    component_name="Distribution Charge",
                    charge_value=SEED_LARGE_COMMERCIAL["distribution_rate"],
                    charge_unit="$/kWh",
                    confidence="high",
                    notes="Variable distribution charge per kWh consumed",
                ),
            ],
        ))

        return records
