"""
enmax_power.py -- Scraper for ENMAX Power distribution rates (Alberta).

ENMAX Power Corporation (EPC) is the regulated electricity distribution utility
serving the City of Calgary and surrounding area.

Official source: the "View current distribution tariff" PDF (EPC Distribution
Tariff Rate Schedule) linked from https://www.enmax.com/tariffs. Its asset URL is
opaque and changes with every quarterly edition, so it is discovered each run.

Alberta has a deregulated electricity market -- distribution companies
charge regulated tariffs for wires service, while energy supply is
purchased separately from competitive retailers or the Rate of Last Resort
provider. This scraper covers the wires tariff only: Distribution Access
Service (DAS) charges, System Access Service (SAS) transmission charges and
the current riders, each kept as a separate dated component.

Regulated by the Alberta Utilities Commission (AUC).
"""

from __future__ import annotations

import io
import logging
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, Optional
from urllib.parse import urljoin, urlsplit

import requests

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import DocumentPage, parse_html

logger = logging.getLogger(__name__)

TARIFFS_URL = "https://www.enmax.com/tariffs"

# Seed data for ENMAX Power distribution rates.
SOURCE_URL = "https://www.enmax.com/home/rates-and-billing/understand-your-bill"
EFFECTIVE_DATE = "2024-04-01"

SEED_RESIDENTIAL = {
    "tariff_code": "D110",
    "basic_charge_per_day": 0.7086,   # $/day
    "distribution_rate": 0.0192,       # $/kWh
}

SEED_SMALL_COMMERCIAL = {
    "tariff_code": "D210",
    "basic_charge_per_day": 0.9400,   # $/day
    "distribution_rate": 0.0238,       # $/kWh
}

SEED_LARGE_COMMERCIAL = {
    "tariff_code": "D310",
    "basic_charge_per_day": 16.80,    # $/day
    "demand_charge": 5.2400,           # $/kW
    "distribution_rate": 0.0031,       # $/kWh
}

# ── Live schedule parsing ─────────────────────────────────────────

_DATE = r"[A-Z][a-z]{2,8}\.?\s+\d{1,2},\s*\d{4}"
_DECISION = r"\d{5}-D\d{2}-\d{4}"
_MONEY_WORD = re.compile(r"\(?\$\d[\d,]*\.\d+\)?")
_NUMBER_WORD = re.compile(r"\d[\d,]*\.\d+\)?")
# Label-to-unit gaps are >= 11 pt; words inside one cell are <= ~7 pt apart. Amounts always split.
_CELL_GAP = 9.0
_TABLE_HEADER = "COMPONENT TYPE UNIT PRICE"
_SECTIONS = {
    "DISTRIBUTION CHARGE FOR DISTRIBUTION ACCESS SERVICE": "DAS",
    "TRANSMISSION CHARGE FOR SYSTEM ACCESS SERVICE": "SAS",
}
_HEADING_RE = re.compile(r"[A-Z][A-Z ]* CHARGE FOR [A-Z ]* SERVICE")
_FOOTER_RE = re.compile(r"^ENMAX Power Corporation Distribution Tariff Page (\d+) of (\d+)$", re.M)
_APPROVAL_RE = re.compile(
    rf"Distribution Access Service \(DAS\) rates approved in AUC Decision ({_DECISION}) effective ({_DATE}) and "
    rf"System Access Service \(SAS\) rates approved in AUC Decision ({_DECISION}) effective ({_DATE})"
)
_LABEL_RE = re.compile(
    r"\s*(Service and Facilities Charge|System Usage Charge|Service Charge|Non-Ratcheted Demand Charge|"
    r"Facilities Charge|Demand Charge|Variable Charge On Peak|Variable Charge Off Peak|Variable Charge)(?=\s|$)"
)
_UNIT_RE = re.compile(r"\s*(per day per kVA of (?:Billing|Metered) Demand|per day|per kWh)(?=\s|$)")
_ROW_UNITS = {
    "Service and Facilities Charge": "per day",
    "Service Charge": "per day",
    "System Usage Charge": "per kWh",
    "Facilities Charge": "per day per kVA of Billing Demand",
    "Non-Ratcheted Demand Charge": "per day per kVA of Metered Demand",
    "Demand Charge": "per day per kVA of Billing Demand",
    "Variable Charge": "per kWh",
    "Variable Charge On Peak": "per kWh",
    "Variable Charge Off Peak": "per kWh",
}
_UNIT_CODES = {
    "per day": "$/day",
    "per kWh": "$/kWh",
    "per day per kVA of Billing Demand": "$/kVA/day",
    "per day per kVA of Metered Demand": "$/kVA/day",
}
_LAF_TEXT = "The LAF is a surcharge imposed by the City of Calgary"
_APPLIES_TO_ALL = "Rider will apply to all energy delivered under the Distribution Tariff"
_BPA_TITLE = r"\d{4} Balancing Pool Allocation Rider\b"
_QUARTERLY_TITLE = r"QUARTERLY TRANSMISSION ACCESS CHARGE \(TAC\) ADJUSTMENT RIDER\b"
_DEFERRAL_TITLE = r"TRANSMISSION ACCESS CHARGE \(TAC\) DEFERRAL ACCOUNT RIDER ADJUSTMENT\b"
_EXCLUDED = {
    "D500": "streetlight (photo-cell controlled lighting) service",
    "D600": "large distributed generation (export capacity of 1,000 kVA or more)",
}


@dataclass(frozen=True)
class _ClassSpec:
    code: str
    title: str
    tariff_name: str
    customer_class: str
    structure: str
    das: tuple[str, ...]
    sas: tuple[str, ...]
    eligibility: str


_SMALL_DAS = ("Service and Facilities Charge", "System Usage Charge")
_DEMAND_DAS = ("Service Charge", "Facilities Charge", "Non-Ratcheted Demand Charge")
_TOU_SAS = ("Demand Charge", "Variable Charge On Peak", "Variable Charge Off Peak")
_SPECS = (
    _ClassSpec("D100", "RESIDENTIAL", "Residential Distribution (Rate D100)", "residential", "flat",
               _SMALL_DAS, ("Variable Charge",),
               r"Sites which use Electricity Services for domestic purposes in separate and permanently metered "
               r"single family dwelling units"),
    _ClassSpec("D200", "SMALL COMMERCIAL", "Small Commercial Distribution (Rate D200)", "commercial", "flat",
               _SMALL_DAS, ("Variable Charge",),
               r"Commercial Sites where the Energy consumption is less than ([\d,]+) kWh per month"),
    _ClassSpec("D300", "MEDIUM COMMERCIAL", "Medium Commercial Distribution (Rate D300)", "commercial", "demand",
               _DEMAND_DAS, ("Demand Charge", "Variable Charge"),
               r"Energy consumption is equal to or greater than ([\d,]+) kWh per month for at least six of the last "
               r"12 invoice periods, provided a peak demand greater than ([\d,]+) kVA was not registered twice in the "
               r"previous 365 days"),
    _ClassSpec("D310", "LARGE COMMERCIAL - SECONDARY", "Large Commercial Secondary Distribution (Rate D310)",
               "commercial", "mixed", _DEMAND_DAS, _TOU_SAS,
               r"registered a monthly peak demand greater than ([\d,]+) kVA twice in the previous 365 days and "
               r"served at secondary voltage"),
    _ClassSpec("D410", "LARGE COMMERCIAL - PRIMARY", "Large Commercial Primary Distribution (Rate D410)",
               "commercial", "mixed", _DEMAND_DAS, _TOU_SAS,
               r"For Electricity Services that are served at primary voltage"),
)


class _Reject(Exception):
    """A class, rider or document cannot be proven complete from the source."""


@dataclass(frozen=True)
class _Rider:
    values: dict[str, float]
    start: date
    end: Optional[date]
    page: int
    decision: str
    label: str
    period: str


@dataclass(frozen=True)
class _Riders:
    """Each rider is either parsed or the reason it could not be proven."""

    bpa: _Rider | str
    bpa_ineligible: frozenset[str]
    quarterly: _Rider | str
    deferral: _Rider | str
    deferral_expired: bool


def _require(rider: _Rider | str) -> _Rider:
    if isinstance(rider, str):
        raise _Reject(rider)
    return rider


def _flat(text: str) -> str:
    text = (text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
            .replace("\u2013", "-").replace("\u2014", "-"))
    return re.sub(r"\s+", " ", text).strip()


def _date(raw: str) -> Optional[date]:
    text = re.sub(r",\s*", ", ", re.sub(r"\s+", " ", raw.replace(".", ""))).strip()
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _long(day: date) -> str:
    return f"{day:%B} {day.day}, {day.year}"


def _money(raw: str) -> Optional[float]:
    """Dollar amount as printed; parentheses mark a refund (negative)."""
    match = re.fullmatch(r"(\()?\$\s?(\d[\d,]*\.\d+)(\))?", raw.strip())
    if not match or bool(match.group(1)) != bool(match.group(3)):
        return None
    value = float(match.group(2).replace(",", ""))
    return -value if match.group(1) else value


def _page_ranges(numbers: set[int]) -> str:
    ordered, ranges = sorted(numbers), []
    for number in ordered:
        if ranges and number == ranges[-1][1] + 1:
            ranges[-1][1] = number
        else:
            ranges.append([number, number])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in ranges)


# ── PDF text extraction ───────────────────────────────────────────

def extract_schedule_pages(pdf_bytes: bytes) -> list[DocumentPage]:
    """Extract page text with column-preserving table rows; fails closed (empty list) on unreadable documents.

    The schedule centres multi-line table cells on some pages and top-aligns them on others,
    so plain text interleaves labels, units and prices. Rate-table rows are therefore rendered
    as tab-separated component/unit/price cells, and ruled tables (the rider tables) as their
    pdfplumber cells, keeping blank quarter columns in place.
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed — run: pip install pdfplumber")
        return []
    pages: list[DocumentPage] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for number, page in enumerate(pdf.pages, 1):
                tables = page.find_tables()
                boxes = [table.bbox for table in tables]
                words = [word for word in page.extract_words(x_tolerance=2, y_tolerance=3)
                         if not any(_within(word, box) for box in boxes)]
                blocks = [(table.bbox[1], ["\t".join(" ".join((cell or "").split()) for cell in row)
                                           for row in table.extract()]) for table in tables]
                text = render_page_words(words, blocks)
                if len(re.sub(r"\W", "", text)) >= 20:
                    pages.append(DocumentPage(number, text))
    except Exception as exc:
        logger.warning("ENMAX tariff PDF extraction failed closed: %s", exc)
        return []
    return pages


def _within(word: dict, box: tuple[float, float, float, float]) -> bool:
    x0, top, x1, bottom = box
    return (word["x0"] >= x0 - 1 and word["x1"] <= x1 + 1
            and word["top"] >= top - 1 and word["bottom"] <= bottom + 1)


def _cells(line: list[dict]) -> list[dict]:
    """Split one printed line into cells at wide gaps; dollar amounts are always their own cell."""
    cells: list[dict] = []
    for word in line:
        text = word["text"]
        last = cells[-1] if cells else None
        if last and last["texts"] in (["$"], ["($"]) and _NUMBER_WORD.fullmatch(text):
            last.update(x1=word["x1"], money=True)
            last["texts"].append(text)
            continue
        money = bool(_MONEY_WORD.fullmatch(text))
        if (last is None or money or last["money"] or text in ("$", "($") or last["texts"] in (["$"], ["($"])
                or word["x0"] - last["x1"] > _CELL_GAP):
            cells.append({"x0": word["x0"], "x1": word["x1"], "texts": [text], "money": money})
        else:
            last["x1"] = word["x1"]
            last["texts"].append(text)
    return cells


def render_page_words(words: list[dict], tables: Iterable[tuple[float, list[str]]] = ()) -> str:
    """Render pdfplumber words as lines; rows under a COMPONENT/UNIT/PRICE header become 3 tab cells.

    ``tables`` holds (top, tab-joined rows) of ruled tables whose words were removed from ``words``.
    """
    lines: list[list[dict]] = []
    for word in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and word["top"] - lines[-1][0]["top"] <= 3:
            lines[-1].append(word)
        else:
            lines.append([word])
    events: list[tuple[float, Optional[list[dict]], list[str]]] = [(line[0]["top"], line, []) for line in lines]
    events += [(top, None, rows) for top, rows in tables]
    output: list[str] = []
    anchors: Optional[tuple[float, float, float]] = None
    for _, line, rows in sorted(events, key=lambda event: event[0]):
        if line is None:
            anchors = None
            output.extend(rows)
            continue
        line.sort(key=lambda w: w["x0"])
        text = " ".join(w["text"] for w in line)
        if anchors is None:
            output.append(text)
            positions = {w["text"]: w["x0"] for w in line}
            if {"COMPONENT", "UNIT", "PRICE"} <= positions.keys():
                anchors = (positions["COMPONENT"], positions["UNIT"], positions["PRICE"])
            continue
        cells = _cells(line)
        columns_x = anchors
        if _HEADING_RE.fullmatch(text):
            output.append(text)
        elif line[0]["x0"] < columns_x[0] - 5 and not any(cell["money"] for cell in cells):
            anchors = None
            output.append(text)
        else:
            columns: list[list[str]] = [[], [], []]
            for cell in cells:
                x0 = cell["x0"]
                index = 2 if cell["money"] else min(range(3), key=lambda i: abs(x0 - columns_x[i]))
                columns[index].append(" ".join(cell["texts"]))
            output.append("\t".join(" ".join(column) for column in columns))
    return "\n".join(output)


# ── Discovery ─────────────────────────────────────────────────────

def current_tariff_link(html: str, base_url: str = TARIFFS_URL) -> Optional[str]:
    """Return the one ENMAX link labelled as the current distribution tariff, else None."""
    links: list[str] = []
    for anchor in parse_html(html).find_all("a", href=True):
        label = " ".join(anchor.get_text(" ").split())
        if not re.search(r"\bcurrent distribution tariff\b", label, re.I):
            continue
        url = urljoin(base_url, anchor["href"].strip())
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if parts.scheme == "https" and (host == "enmax.com" or host.endswith(".enmax.com")):
            links.append(url)
    links = list(dict.fromkeys(links))
    return links[0] if len(links) == 1 else None


# ── Schedule parsing ──────────────────────────────────────────────

def _tokens(stream: str, pattern: re.Pattern, what: str) -> list[str]:
    tokens, position, stream = [], 0, stream.strip()
    while position < len(stream):
        match = pattern.match(stream, position)
        if not match:
            raise _Reject(f"unrecognised {what}: {stream[position:]!r}")
        tokens.append(match.group(1))
        position = match.end()
    return tokens


def _table_rows(text: str) -> list[tuple[Optional[str], list[str]]]:
    """(section, [label, unit, price]) rows of the page's rate table, in printed order."""
    rows: list[tuple[Optional[str], list[str]]] = []
    section: Optional[str] = None
    seen: set[str] = set()
    started = False
    for line in text.splitlines():
        if not started:
            started = _flat(line) == _TABLE_HEADER
            continue
        if "\t" in line:
            cells = [cell.strip() for cell in line.split("\t")]
            if len(cells) != 3:
                raise _Reject("rate table row is not component/unit/price")
            rows.append((section, cells))
        elif line.strip() in _SECTIONS:
            section = _SECTIONS[line.strip()]
            if section in seen:
                raise _Reject(f"duplicate {section} section heading")
            seen.add(section)
        else:
            break
    return rows


def _section_charges(rows: list[list[str]], expected: tuple[str, ...], section: str) -> list[tuple[str, str, float]]:
    """Pair the section's label, unit and price columns in printed order and prove each row."""
    if not rows:
        raise _Reject(f"{section} rate rows missing")
    labels = _tokens(" ".join(row[0] for row in rows if row[0]), _LABEL_RE, f"{section} component labels")
    units = _tokens(re.sub(r"\bkVA off\b", "kVA of", " ".join(row[1] for row in rows if row[1])),
                    _UNIT_RE, f"{section} units")
    prices = [row[2] for row in rows if row[2]]
    if not len(labels) == len(units) == len(prices):
        raise _Reject(f"{section} has {len(labels)} labels, {len(units)} units and {len(prices)} prices")
    if Counter(labels) != Counter(expected):
        raise _Reject(f"{section} rows {labels} differ from the expected {list(expected)}")
    charges = []
    for label, unit, price in zip(labels, units, prices):
        if unit != _ROW_UNITS[label]:
            raise _Reject(f"{section} {label} unit {unit!r} is not {_ROW_UNITS[label]!r}")
        value = _money(price)
        if value is None or value <= 0:
            raise _Reject(f"{section} {label} price {price!r} is not a positive dollar amount")
        charges.append((label, unit, value))
    return charges


def _split_footer(page: DocumentPage) -> tuple[str, str]:
    matches = list(_FOOTER_RE.finditer(page.text))
    if len(matches) != 1 or int(matches[0].group(1)) != page.page_number:
        raise _Reject(f"PDF page {page.page_number} footer is missing or numbered differently")
    return page.text[:matches[0].start()], page.text[matches[0].end():]


def _schedule_start(page: DocumentPage) -> bool:
    first = next((line for line in page.text.splitlines() if line.strip()), "")
    return bool(re.search(r"\bRATE CODE D\d{3}\b", page.text)) or "RIDER" in first.upper()


def _class_pages(pages: list[DocumentPage], code: str) -> list[DocumentPage]:
    """The rate code's first page plus its consecutive continuation pages."""
    ordered = sorted(pages, key=lambda page: page.page_number)
    anchors = [index for index, page in enumerate(ordered) if re.search(rf"\bRATE CODE {code}\b", page.text)]
    if len(anchors) != 1:
        raise _Reject("schedule page missing or duplicated")
    section = [ordered[anchors[0]]]
    for page in ordered[anchors[0] + 1:]:
        if page.page_number != section[-1].page_number + 1 or _schedule_start(page):
            break
        section.append(page)
    return section


def _rider_page(pages: list[DocumentPage], title: str) -> DocumentPage:
    matches = [page for page in pages if re.match(title, _flat(page.text))]
    if len(matches) != 1:
        raise _Reject("rider page missing or duplicated")
    _split_footer(matches[0])
    return matches[0]


def _ruled_rows(text: str, width: int) -> list[list[str]]:
    return [cells for cells in ([cell.strip() for cell in line.split("\t")] for line in text.splitlines())
            if len(cells) == width]


def _class_values(rows: list[list[str]], column: int) -> dict[str, float]:
    """Rate code -> dollar value per kWh in ``column``; blank or unreadable cells are left out."""
    values: dict[str, float] = {}
    for row in rows:
        if not re.fullmatch(r"D\d{3}", row[1]) or row[2] != "per kWh":
            continue
        if row[1] in values:
            raise _Reject(f"rider row {row[1]} is duplicated")
        amount = _money(row[column])
        if amount is not None:
            values[row[1]] = amount
    return values


def _parse_bpa(pages: list[DocumentPage], in_effect: date) -> tuple[_Rider, frozenset[str]]:
    page = _rider_page(pages, _BPA_TITLE)
    flat = _flat(page.text)
    year = flat[:4]
    body = re.search(rf"The rider is effective ({_DATE})\.", flat)
    footer = re.search(rf"Balancing Pool Allocation(?: Refund)? Rider approved in AUC Decision ({_DECISION}),? "
                       rf"effective ({_DATE})", flat)
    rows = [row for _, row in _table_rows(page.text)]
    if _APPLIES_TO_ALL not in flat or not body or not footer:
        raise _Reject("applicability, effective date or approval missing")
    start = _date(body.group(1))
    if start is None or start != _date(footer.group(2)) or start > in_effect:
        raise _Reject("effective date missing, inconsistent or after the schedule's in-effect date")
    if len(rows) != 1 or rows[0][0] != "Balancing Pool Allocation" or rows[0][1] != "per kWh":
        raise _Reject("rate row missing or not per kWh")
    value = _money(rows[0][2])
    if not value:
        raise _Reject("rate is not a dollar amount")
    ineligible = re.search(r"((?:D\d{3}(?:,\s*|\s+and\s+)?)+) sites are ineligible for the Balancing Pool "
                           r"Allocation Rider", flat)
    excluded = frozenset(re.findall(r"D\d{3}", ineligible.group(1))) if ineligible else frozenset()
    return _Rider({"*": value}, start, None, page.page_number, footer.group(1), year,
                  f"effective {_long(start)}"), excluded


def _parse_quarterly(pages: list[DocumentPage], in_effect: date, today: date) -> _Rider:
    page = _rider_page(pages, _QUARTERLY_TITLE)
    flat = _flat(page.text)
    title = re.search(r"\b(\d{4}) Quarterly TAC Adjustment Rider\b", flat)
    body = re.search(rf"The rider is effective ({_DATE})\.", flat)
    footer = re.search(rf"adjustment approved in AUC Decision ({_DECISION}) effective ({_DATE})", flat)
    if _APPLIES_TO_ALL not in flat or not title or not body or not footer:
        raise _Reject("applicability, effective date or approval missing")
    year = int(title.group(1))
    rows = _ruled_rows(page.text, 7)
    header = [row[3:] for row in rows if all(re.fullmatch(rf"Q[1-4] {_DATE}", cell) for cell in row[3:])]
    if (not any(row[3] == "Quarterly TAC Adjustment Rider Charge / (Refund)" for row in rows) or len(header) != 1
            or [(cell[:2], _date(cell[3:])) for cell in header[0]]
            != [(f"Q{n}", date(year, 3 * n - 2, 1)) for n in (1, 2, 3, 4)]):
        raise _Reject("rate table header or calendar quarter columns missing")
    if in_effect.year != year:
        raise _Reject(f"{year} rider table does not cover the in-effect date {in_effect}")
    index = (in_effect.month - 1) // 3
    start = date(year, 1 + 3 * index, 1)
    end = (date(year + 1, 1, 1) if index == 3 else date(year, 4 + 3 * index, 1)) - timedelta(days=1)
    if _date(body.group(1)) != start or _date(footer.group(2)) != start:
        raise _Reject(f"rider effective date does not match the in-effect quarter starting {start}")
    if end < today:
        raise _Reject(f"Q{index + 1} {year} ended {end}; the current quarter's rider is not published")
    return _Rider(_class_values(rows, 3 + index), start, end, page.page_number, footer.group(1),
                  f"Q{index + 1} {year}", f"effective {_long(start)} to {_long(end)}")


def _parse_deferral(pages: list[DocumentPage], in_effect: date) -> _Rider:
    page = _rider_page(pages, _DEFERRAL_TITLE)
    flat = _flat(page.text)
    title = re.search(r"\b(\d{4}) TAC Deferral Account Rider Adjustment\b", flat)
    period = re.search(rf"The adjustment is effective ({_DATE}) to ({_DATE})\.", flat)
    footer = re.search(rf"deferral account rider adjustment approved in AUC Decision ({_DECISION}) effective ({_DATE})",
                       flat, re.I)
    rows = _ruled_rows(page.text, 4)
    if _APPLIES_TO_ALL not in flat or not title or not period or not footer:
        raise _Reject("applicability, effective period or approval missing")
    if not any(row[3] == f"{title.group(1)} TAC Deferral Account Rider Adjustment Charge / (Refund)" for row in rows):
        raise _Reject("rate table header missing")
    start, end = _date(period.group(1)), _date(period.group(2))
    if start is None or end is None or start != _date(footer.group(2)) or end < start or start > in_effect:
        raise _Reject("effective period missing, inconsistent or after the schedule's in-effect date")
    return _Rider(_class_values(rows, 3), start, end, page.page_number, footer.group(1), title.group(1),
                  f"effective {_long(start)} to {_long(end)}")


def _unmodelled_riders(pages: list[DocumentPage], today: date) -> list[str]:
    """Rider pages other than the three modelled riders that are not shown to have ended."""
    unmodelled = []
    for page in pages:
        first = next((line.strip() for line in page.text.splitlines() if line.strip()), "")
        flat = _flat(page.text)
        if "RIDER" not in first.upper() or any(re.match(title, flat) for title in (
                _BPA_TITLE, _QUARTERLY_TITLE, _DEFERRAL_TITLE)):
            continue
        period = re.search(rf"effective ({_DATE}) to ({_DATE})", flat)
        end = _date(period.group(2)) if period else None
        if end is not None and end < today:
            logger.info("ENMAX Power rider %r (PDF page %d) ended %s; ignored", first, page.page_number, end)
            continue
        unmodelled.append(f"{first} (PDF page {page.page_number})")
    return unmodelled


def _parse_riders(pages: list[DocumentPage], in_effect: date, today: date) -> _Riders:
    bpa: _Rider | str
    quarterly: _Rider | str
    deferral: _Rider | str
    ineligible: frozenset[str] = frozenset()
    try:
        bpa, ineligible = _parse_bpa(pages, in_effect)
    except _Reject as exc:
        bpa = f"Balancing Pool Allocation Rider: {exc}"
    try:
        quarterly = _parse_quarterly(pages, in_effect, today)
    except _Reject as exc:
        quarterly = f"Quarterly TAC Adjustment Rider: {exc}"
    try:
        deferral = _parse_deferral(pages, in_effect)
    except _Reject as exc:
        deferral = f"TAC Deferral Account Rider Adjustment: {exc}"
    expired = isinstance(deferral, _Rider) and deferral.end is not None and deferral.end < today
    if expired:
        logger.info("ENMAX Power TAC Deferral Account Rider Adjustment has ended; excluded")
    for rider in (bpa, quarterly, deferral):
        if isinstance(rider, str):
            logger.warning("ENMAX Power rider not live-verified: %s", rider)
    return _Riders(bpa, ineligible, quarterly, deferral, expired)


def _log_exclusions(pages: list[DocumentPage]) -> None:
    for code, reason in _EXCLUDED.items():
        if any(re.search(rf"\bRATE CODE {code}\b", page.text) for page in pages):
            logger.info("ENMAX Power Rate %s excluded from building scope: %s", code, reason)
    d700 = [page for page in pages if re.search(r"\bRATE CODE D700\b", page.text)]
    if d700 and "ISO Costs $ Flow through" in _flat(d700[0].text):
        logger.info("ENMAX Power Rate D700 (transmission connected) excluded: its System Access Service charge is "
                    "a flow-through of AESO ISO costs, not a printed price (source-blocked)")
    elif d700:
        logger.warning("ENMAX Power Rate D700 no longer prints an AESO flow-through transmission charge; "
                       "review whether it is now fully priced (not modelled)")


_DAS_COMPONENTS = {
    "Service and Facilities Charge": "fixed",
    "Service Charge": "fixed",
    "System Usage Charge": "distribution",
    "Facilities Charge": "demand",
    "Non-Ratcheted Demand Charge": "demand",
}
_SAS_NAMES = {
    "Variable Charge": "Transmission Variable Charge",
    "Variable Charge On Peak": "Transmission Variable Charge - On Peak",
    "Variable Charge Off Peak": "Transmission Variable Charge - Off Peak",
    "Demand Charge": "Transmission Demand Charge",
}
_BILLING_DEMAND_RE = re.compile(
    r'kVA of "Billing Demand" is defined as the greater of "Metered", "Ratchet" or "Contract" Demand: '
    r'\(a\) "Metered Demand" is the actual metered demand in the Tariff bill period[;,] '
    r'\(b\) "Ratchet Demand" is (\d+)% of the highest kVA demand in the last (\d+) days ending with the last day of '
    r'the Tariff bill period[;,] (?:and )?\(c\) "Contract Demand" is the kVA contracted for by the Customer'
)
_TOU_RE = re.compile(
    r'"On Peak" is all Energy consumption from (\d{1,2} a\.m\.) to (\d{1,2} p\.m\.) Monday to Friday inclusive, '
    r'excluding statutory holidays \(as according to the ISO Rules definition\)[,.] '
    r'"Off Peak" is all Energy consumption not consumed in On Peak hours'
)
_D300_CREDIT_RE = re.compile(
    rf"there will be a transformation credit of \$(\d+\.\d+) per day applied to the Service Charge, and a "
    rf"transformation credit of \$(\d+\.\d+) per day per kVA of Billing Demand applied to the Facilities Charge\. "
    rf"b\. The transformation credit is applicable only to D300 sites receiving primary voltage service prior to "
    rf"({_DATE})\."
)
_REQUIRED_NOTES = {
    "D100": ("No more than one additional unit of living quarters within a single family dwelling",
             "D100 allows at most one additional self-contained living unit (such as a basement suite) on the "
             "dwelling's meter; more units take a commercial rate unless each unit is metered separately."),
    "D300": ("Bulk Metering is the metering of multiple-unit residential occupancies under one corporate identity",
             "D300 also covers non-standard residential bulk metering (multiple residential units under one "
             "corporate identity, e.g. town housing, apartments, mobile home parks; no resale of electricity)."),
    "D410": ("The Customer is responsible for supplying all transformers",
             "D410 customers supply all transformers; metering is at EPC's primary distribution voltage."),
}


def _component(
    kind: str, name: str, value: float, unit: str, start: date, end: Optional[date], source_url: str,
    detail: str, notes: str, **extra,
) -> RateComponent:
    return RateComponent(
        component_type=kind, component_name=name, charge_value=value, charge_unit=unit,
        effective_date=start.isoformat(), end_date=end.isoformat() if end else None, source_url=source_url,
        source_detail=detail, confidence="high", notes=notes, **extra,
    )


def _page_with(section: list[DocumentPage], bodies: tuple[str, ...], phrase: str) -> int:
    number = next((page.page_number for page, body in zip(section, bodies) if phrase in _flat(body)), None)
    if number is None:
        raise _Reject(f"{phrase!r} is split across pages")
    return number


def _build_record(
    spec: _ClassSpec, pages: list[DocumentPage], riders: _Riders, in_effect: date, source_url: str,
) -> TariffRecord:
    section = _class_pages(pages, spec.code)
    anchor = section[0]
    bodies, footers = zip(*(_split_footer(page) for page in section))
    approvals = [_APPROVAL_RE.search(_flat(footer)) for footer in footers]
    if not approvals[0] or any(not match or match.groups() != approvals[0].groups() for match in approvals):
        raise _Reject("DAS/SAS approval footer missing or inconsistent across the schedule's pages")
    das_decision, das_raw, sas_decision, sas_raw = approvals[0].groups()
    das_date, sas_date = _date(das_raw), _date(sas_raw)
    if das_date is None or sas_date is None or max(das_date, sas_date) > in_effect:
        raise _Reject("DAS/SAS effective date missing or after the schedule's in-effect date")

    head = _flat(bodies[0])
    if not re.search(rf"\bDISTRIBUTION TARIFF {re.escape(spec.title)} RATE CODE {spec.code}\b", head):
        raise _Reject("schedule title does not match the rate code")
    printed = re.search(rf"\bELIGIBILITY (.+?) RATE {_TABLE_HEADER}\b", head)
    if not printed:
        raise _Reject("eligibility section missing")
    criteria = re.search(spec.eligibility, printed.group(1))
    if not criteria:
        raise _Reject("eligibility criteria missing or changed")
    body = _flat(" ".join(bodies))
    if _LAF_TEXT not in body:
        raise _Reject("continuation page (Local Access Fee text) missing")

    rows = _table_rows(anchor.text)
    das = _section_charges([row for name, row in rows if name == "DAS"], spec.das, "DAS")
    sas = _section_charges([row for name, row in rows if name == "SAS"], spec.sas, "SAS")

    notes: list[str] = []
    billing_note = on_peak_hours = ""
    if spec.structure != "flat":
        billing = _BILLING_DEMAND_RE.search(body)
        if not billing:
            raise _Reject("Billing Demand definition missing or changed")
        billing_note = (
            f"Billing Demand is the greatest of Metered Demand (actual metered kVA in the bill period), Ratchet "
            f"Demand ({billing.group(1)}% of the highest kVA demand in the last {billing.group(2)} days ending with "
            f"the last day of the bill period) and Contract Demand (kVA contracted by the customer)."
        )
    if "Variable Charge On Peak" in spec.sas:
        tou = _TOU_RE.search(body)
        if not tou:
            raise _Reject("On Peak/Off Peak definition missing or changed")
        on_peak_hours = (f"{tou.group(1)} to {tou.group(2)} Monday to Friday inclusive, excluding statutory "
                         f"holidays (ISO Rules definition)")
    if spec.code in _REQUIRED_NOTES:
        phrase, note = _REQUIRED_NOTES[spec.code]
        if phrase not in body:
            raise _Reject("continuation-page conditions missing or changed")
        notes.append(note)

    components: list[RateComponent] = []
    das_detail = f"PDF page {anchor.page_number}; Rate Code {spec.code}, Distribution Charge for Distribution Access Service"
    for label, unit, value in das:
        kind = _DAS_COMPONENTS[label]
        text = f"Distribution Access Service (DAS) charge {unit}."
        if label == "Facilities Charge":
            text = f"{text} {billing_note}"
        elif label == "Non-Ratcheted Demand Charge":
            text = f"{text[:-1]} (the actual metered demand in the bill period; not ratcheted)."
        components.append(_component(
            kind, label, value, _UNIT_CODES[unit], das_date, None, source_url, das_detail, text,
            demand_unit="kVA" if "kVA" in unit else None,
        ))
    sas_detail = f"PDF page {anchor.page_number}; Rate Code {spec.code}, Transmission Charge for System Access Service"
    for label, unit, value in sas:
        text = f"System Access Service (SAS) transmission charge {unit}."
        extra: dict = {"demand_unit": "kVA"} if "kVA" in unit else {}
        if label == "Demand Charge":
            text = f"{text} {billing_note}"
        elif label == "Variable Charge On Peak":
            text = f"{text[:-1]} consumed On Peak ({on_peak_hours})."
            extra = {"tou_period": "on-peak", "tou_hours": on_peak_hours}
        elif label == "Variable Charge Off Peak":
            text = f"{text[:-1]} consumed Off Peak (all energy not consumed in On Peak hours)."
            extra = {"tou_period": "off-peak", "tou_hours": "All hours outside On Peak"}
        components.append(_component(
            "transmission", _SAS_NAMES[label], value, _UNIT_CODES[unit], sas_date, None, source_url, sas_detail,
            text, **extra,
        ))

    if spec.code == "D300":
        credit = _D300_CREDIT_RE.search(body)
        credit_date = _date(credit.group(3)) if credit else None
        if not credit or credit_date is None:
            raise _Reject("primary voltage transformation credit missing or changed")
        page = _page_with(section, bodies, "transformation credit of $")
        detail = f"PDF page {page}; Rate Code D300, Other item 5 (primary voltage transformation credit)"
        condition = f"Conditional: only D300 sites that received primary voltage service before {_long(credit_date)}"
        components.append(_component(
            "rebate", "Primary Voltage Transformation Credit - Service Charge", -float(credit.group(1)), "$/day",
            das_date, None, source_url, detail, f"{condition}; credit per day applied to the Service Charge.",
            sub_component="conditional",
        ))
        components.append(_component(
            "rebate", "Primary Voltage Transformation Credit - Facilities Charge", -float(credit.group(2)),
            "$/kVA/day", das_date, None, source_url, detail,
            f"{condition}; credit per day per kVA of Billing Demand applied to the Facilities Charge.",
            demand_unit="kVA", sub_component="conditional",
        ))

    bpa, quarterly, deferral = _require(riders.bpa), _require(riders.quarterly), _require(riders.deferral)
    used = {page.page_number for page in section}
    if spec.code not in riders.bpa_ineligible:
        used.add(bpa.page)
        components.append(_component(
            "rider", "Balancing Pool Allocation Rider", bpa.values["*"], "$/kWh", bpa.start, None, source_url,
            f"PDF page {bpa.page}; {bpa.label} Balancing Pool Allocation Rider",
            f"{bpa.label} Balancing Pool Allocation Rider ({bpa.period}): flow-through of the AESO Consumer "
            f"Allocation Rider (Rider F), per kWh of all energy delivered under the Distribution Tariff (D600 sites "
            f"are ineligible). Approved in AUC Decision {bpa.decision}.",
        ))
    if spec.code not in quarterly.values:
        raise _Reject("Quarterly TAC Adjustment Rider has no row for this rate code")
    used.add(quarterly.page)
    components.append(_component(
        "rider", "Quarterly TAC Adjustment Rider", quarterly.values[spec.code], "$/kWh", quarterly.start,
        quarterly.end, source_url,
        f"PDF page {quarterly.page}; Quarterly TAC Adjustment Rider, Rate Code {spec.code}, {quarterly.label} column",
        f"{quarterly.label} column of the Quarterly Transmission Access Charge (TAC) Adjustment Rider, "
        f"{quarterly.period} (end of the published quarter): charge (positive) or refund (negative) per kWh of all "
        f"energy delivered. Approved in AUC Decision {quarterly.decision}; changes every quarter.",
    ))
    if riders.deferral_expired:
        notes.append(f"The {deferral.label} TAC Deferral Account Rider Adjustment ({deferral.period}) has ended "
                     f"and is not included.")
    else:
        if spec.code not in deferral.values:
            raise _Reject("TAC Deferral Account Rider Adjustment has no row for this rate code")
        used.add(deferral.page)
        components.append(_component(
            "rider", "TAC Deferral Account Rider Adjustment", deferral.values[spec.code], "$/kWh", deferral.start,
            deferral.end, source_url,
            f"PDF page {deferral.page}; {deferral.label} TAC Deferral Account Rider Adjustment, Rate Code {spec.code}",
            f"{deferral.label} Transmission Access Charge (TAC) Deferral Account Rider Adjustment, {deferral.period}: "
            f"charge (positive) or refund (negative) per kWh of all energy delivered. Approved in AUC Decision "
            f"{deferral.decision}.",
        ))

    if re.search(r"If a Site (?:that )?qualifies as a Micro-Generator, rate charges will only apply to energy "
                 r"inflow into the Site", body):
        notes.append("Micro-generators pay these charges on energy inflow only (no outflow charges).")
    notes.append(
        "Conditional: the City of Calgary Local Access Fee (LAF) applies to sites within the City's municipal "
        "boundaries; it is a City surcharge approved by the AUC and collected by EPC, and its rate is not printed "
        "in this schedule, so no value is shown."
    )
    usage_min = usage_max = None
    sub_class = {"D100": "residential", "D310": "large commercial secondary voltage",
                 "D410": "large commercial primary voltage"}.get(spec.code)
    if spec.code == "D200":
        usage_max = float(criteria.group(1).replace(",", ""))
        sub_class = f"small commercial (< {usage_max:,.0f} kWh/month)"
    elif spec.code == "D300":
        usage_min = float(criteria.group(1).replace(",", ""))
        sub_class = f"medium commercial (>= {usage_min:,.0f} kWh/month)"
    title = spec.title.title()
    return TariffRecord(
        utility_name="ENMAX Power", province="AB", utility_type="electricity",
        tariff_name=spec.tariff_name, tariff_code=spec.code, customer_class=spec.customer_class,
        sub_class=sub_class,
        description=f"EPC Distribution Tariff Rate Schedule, Rate Code {spec.code} (Distribution Tariff {title})",
        eligibility=printed.group(1), usage_min=usage_min, usage_max=usage_max,
        usage_unit="kWh/month" if usage_min or usage_max else None,
        rate_structure=spec.structure, pricing_method="regulated",
        effective_date=max(component.effective_date or "" for component in components),
        source_url=source_url, source_page=f"PDF pages {_page_ranges(used)}", confidence="high",
        notes=" ".join([
            "ENMAX Power Corporation (EPC) wires tariff for the Calgary service area; energy is billed separately "
            "by a retailer or the Rate of Last Resort provider.",
            f"Distribution Access Service (DAS) rates approved in AUC Decision {das_decision} effective "
            f"{_long(das_date)}; System Access Service (SAS) transmission charges approved in AUC Decision "
            f"{sas_decision} effective {_long(sas_date)}; rate schedule in effect as of {_long(in_effect)}.",
            "Riders are separate dated components.",
            *notes,
        ]),
        components=components,
    )


def parse_schedule_pages(
    pages: list[DocumentPage], source_url: str, today: Optional[date] = None,
) -> list[TariffRecord]:
    """Build live D100-D410 records from the Distribution Tariff Rate Schedule; each class stands alone.

    Returns [] when the cover's "RATES IN EFFECT AS OF" date is missing or later than ``today``.
    """
    today = today or date.today()
    cover = next((page for page in pages if page.page_number == 1), None)
    match = re.search(rf"\bRATES IN EFFECT AS OF ({_DATE})", _flat(cover.text)) if cover else None
    in_effect = _date(match.group(1)) if match else None
    if in_effect is None or in_effect > today:
        logger.warning("ENMAX Power schedule rejected: in-effect date %s is missing or after %s", in_effect, today)
        return []
    unmodelled = _unmodelled_riders(pages, today)
    if unmodelled:
        logger.warning("ENMAX Power schedule rejected: current rider(s) not modelled: %s", "; ".join(unmodelled))
        return []
    riders = _parse_riders(pages, in_effect, today)
    _log_exclusions(pages)
    records: list[TariffRecord] = []
    for spec in _SPECS:
        try:
            records.append(_build_record(spec, pages, riders, in_effect, source_url))
        except _Reject as exc:
            logger.warning("ENMAX Power Rate %s not live-verified: %s", spec.code, exc)
    return records


class ENMAXPowerScraper(BaseScraper):
    """Scrape ENMAX Power electricity distribution rates for Calgary."""

    def __init__(self):
        super().__init__(utility_name="ENMAX Power", province="AB")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live ENMAX Power distribution rates.
        Classes the live schedule cannot prove are dropped (no new seed for them);
        seed data is used only when no class can be parsed from the official source.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d ENMAX Power tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed -- using seed data for ENMAX Power")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Parse the current Distribution Tariff Rate Schedule; None if no class can be proven."""
        try:
            pdf_url = self._discover_schedule_url()
            if not pdf_url:
                self.logger.warning("ENMAX Power: no single current distribution tariff link on %s", TARIFFS_URL)
                return None
            pages = extract_schedule_pages(self.fetch_bytes(pdf_url))
            if not pages:
                self.logger.warning("ENMAX Power: no usable text in %s", pdf_url)
                return None
            today = date.fromisoformat(self.now_iso()[:10])
            records = parse_schedule_pages(pages, pdf_url, today)
            return self.mark_live_parsed(records) if records else None
        except Exception as exc:
            self.logger.warning("ENMAX Power: live scrape error -- %s", exc)
            return None

    def _discover_schedule_url(self) -> Optional[str]:
        """Static tariffs page first; the rendered page only if the link is absent or the fetch failed."""
        html = None
        try:
            html = self.fetch_page(TARIFFS_URL)
        except requests.RequestException as exc:
            self.logger.warning("ENMAX Power: static fetch of %s failed (%s); trying rendered page", TARIFFS_URL, exc)
        link = current_tariff_link(html) if html else None
        if link is None:
            rendered = self.fetch_rendered_page(TARIFFS_URL)
            link = current_tariff_link(rendered) if rendered else None
        return link

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # -- Residential (Rate D110) ------------------------------------------
        records.append(TariffRecord(
            utility_name="ENMAX Power",
            province="AB",
            utility_type="electricity",
            tariff_name="Residential Distribution (Rate D110)",
            tariff_code=SEED_RESIDENTIAL["tariff_code"],
            customer_class="residential",
            rate_structure="flat",
            effective_date=EFFECTIVE_DATE,
            source_url=SOURCE_URL,
            confidence="high",
            notes=(
                "Distribution charges only; energy supply from retailer. "
                "ENMAX Power serves the City of Calgary. "
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

        # -- Small Commercial (Rate D210) -------------------------------------
        records.append(TariffRecord(
            utility_name="ENMAX Power",
            province="AB",
            utility_type="electricity",
            tariff_name="Small General Service Distribution (Rate D210)",
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

        # -- Large Commercial (Rate D310) -------------------------------------
        records.append(TariffRecord(
            utility_name="ENMAX Power",
            province="AB",
            utility_type="electricity",
            tariff_name="Large General Service Distribution (Rate D310)",
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
