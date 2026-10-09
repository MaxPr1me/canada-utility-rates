"""
epcor_distribution.py -- EPCOR Distribution & Transmission Inc. (EDTI) wires rates, Edmonton (Alberta).

EDTI posts its AUC tariffs as dated PDFs on the Edmonton "Electricity tariffs and riders" page
(DISCOVERY_URL): the Distribution Access Service (DAS) tariff, the System Access Service (SAS,
transmission) tariff and standalone rider editions (G Balancing Pool, J SAS True-Up, K Transmission
Charge Deferral Account True-Up, DJ DAS True-up). Each run selects the newest edition of each that is
already in effect and builds one delivery record per building-scope class from the matching DAS and
SAS price schedules plus the riders those schedules list:

  DAS-R / SAS-R        residential (single household)
  DAS-SC / SAS-SC      commercial/industrial, normal maximum demand < 50 kVA
  DAS-MC / SAS-MC      commercial/industrial, 50 to < 150 kVA
  DAS-TOU / SAS-TOU    commercial/industrial, 150 to < 5,000 kVA, secondary voltage
  DAS-TOUP / SAS-TOUP  commercial/industrial, >= 150 kVA, primary voltage

Not modelled: DAS/SAS-CS and SAS-CST/CST21 (closed to new points of service, customer-specific
charges), DAS/SAS-DC (direct transmission-connected; its SAS charges are an AESO tariff
flow-through), DGEN generator interconnection and SL/TL/SEL/LL lighting. Energy supply is billed
separately by a retailer or the Rate of Last Resort provider.

Every schedule value must equal the tariff's own cell-reference table (Table 1 DAS / Table 3 SAS),
whose descriptions fix the units. Schedules printed "(YYYY INTERIM RATE)" give live records at medium
confidence. The SAS operating reserve charge is a printed percentage of the hourly AESO pool price,
so it is a value-less market component. A missing or inconsistent schedule, unit, date or rider row
rejects only the affected class; seeds are used only when nothing can be parsed.

Regulated by the Alberta Utilities Commission (AUC).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional, Union
from urllib.parse import urljoin, urlsplit

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

logger = logging.getLogger(__name__)

# Seed data for EPCOR Distribution rates.
SOURCE_URL = "https://www.epcor.com/products-services/power/rates-tariffs/Pages/default.aspx"
EFFECTIVE_DATE = "2024-04-01"

SEED_RESIDENTIAL = {
    "tariff_code": "D100",
    "basic_charge_per_day": 0.6458,   # $/day
    "distribution_rate": 0.0186,       # $/kWh
}

SEED_SMALL_COMMERCIAL = {
    "tariff_code": "D200",
    "basic_charge_per_day": 0.8754,   # $/day
    "distribution_rate": 0.0226,       # $/kWh
}

SEED_LARGE_COMMERCIAL = {
    "tariff_code": "D300",
    "basic_charge_per_day": 15.42,    # $/day
    "demand_charge": 5.1200,           # $/kW
    "distribution_rate": 0.0035,       # $/kWh
}

# ── Live sources ─────────────────────────────────────────────────

DISCOVERY_URL = (
    "https://www.epcor.com/ca/en/ab/edmonton/account/rates/special-fees-charges/electricity-tariffs.html"
)
AESO_POOL_PRICE_URL = "https://www.aeso.ca/market/market-and-system-reporting/"
_DOCUMENTS = "https://www.epcor.com/content/dam/epcor/documents/rates/"

# Accordion section title on DISCOVERY_URL -> document kind.
SECTION_KINDS = {
    "distribution access service": "DAS",
    "system access service": "SAS",
    "balancing pool rider": "G",
    "system access service true-up rider": "J",
    "transmission charge deferral account true-up (tcda) rider": "K",
    "distribution access true-up rider": "DJ",
}

# Known editions, used only if the discovery page cannot be read and only until the next
# expected editions (January 2027 tariffs, Rider G/J and quarterly Rider K).
FALLBACK_EDITIONS = {
    "DAS": (("January 2026", _DOCUMENTS + "distribution-access-service-tariffs/2026-01-distribution-access-service-tariff.pdf"),),
    "SAS": (("January 2026", _DOCUMENTS + "system-access-service-tariffs/2026-01-system-access-service-tariff.pdf"),),
    "G": (("January 2026", _DOCUMENTS + "riders/2026-01-rider-g.pdf"),),
    "J": (("January 2026", _DOCUMENTS + "riders/2026-01-rider-j.pdf"),),
    "K": (("October 2026", _DOCUMENTS + "riders/2026-10-rider-k.pdf"),),
    "DJ": (("January 2020", _DOCUMENTS + "riders/2020-01_rider-dj.pdf"),),
}
FALLBACK_VALID_UNTIL = date(2026, 12, 31)

# Riders published as standalone editions -> the tariff whose period they belong to.
STANDALONE_RIDERS = {"G": "SAS", "J": "SAS", "K": "SAS", "DJ": "DAS"}
# Riders each service may list; LAF and E are described in notes, DG is the DAS tariff's own table.
_ALLOWED_RIDERS = {"DAS": ("LAF", "E", "DG", "DJ"), "SAS": ("LAF", "G", "J", "K")}
_RIDER_TITLES = {
    "DG": "Temporary Adjustment",
    "DJ": "DAS True-up Rider",
    "G": "Balancing Pool Rider",
    "J": "SAS True-Up Rider",
    "K": "Transmission Charge Deferral Account True-Up Rider",
}
_RIDER_COLUMNS = {
    "SAS": (("energy", "Energy Charge"), ("demand", "Demand Charge per kW or kVA per Day"),
            ("oss", "OSS Charge"), ("operating_reserve", "Operating Reserve")),
    "DAS": (("customer", "Customer Charge per Day"), ("demand", "Demand Charge per kW or kVA per Day"),
            ("energy", "Per kWh of Total Energy"), ("on_peak", "Per kWh of On-Peak Energy"),
            ("off_peak", "Per kWh of Off-Peak Energy")),
}
_RIDER_HEADERS = {
    "SAS": ("energy", "demand", "osscharge", "operating", "reserve"),
    "DAS": ("customer", "demand", "totalenergy", "on-peak", "off-peak"),
}

_COVER_TITLES = {"DAS": "Distribution Access Service Tariff", "SAS": "Transmission Access Service Tariff"}
_TABLES = {
    "DAS": (r"Table 1: EDTI's (\d{4}) Distribution Tariff Schedules", "Table 2:", "Table 1"),
    "SAS": (r"Table 3: EDTI's (\d{4}) System Access Service Rate Schedules", "Table 4:", "Table 3"),
}

_DATE = r"([A-Z][a-z]+ \d{1,2}, \d{4})"
_SCHEDULE_VALUE = re.compile(r"\$\s?\(?\d[\d,]*\.\d+\)?|\b\d+\.\d+%")
_TABLE_ROW = re.compile(
    r"\b((?:DAS|SAS)-[A-Z]+\d+(?:-\d+)?)\s+(\$\s?\(?\d[\d,]*\.\d+\)?|\d+\.\d+%|\d+\.\d+|Flowthrough)\s+([^\n]*)"
)
_RIDER_TOKEN = r"(?:N/A|-|\$\s?\(?\d[\d,]*\.\d+\)?)"
_BD_PERCENT = re.compile(
    r"\(?b\)\s*(\d+)% of the highest metered demand in the (?:12|twelve)[- ]month period including and "
    r"ending with the billing period", re.I)
_BD_CLAUSE = re.compile(r"\(?d\)\s*the (contract demand|Contracted Minimum Demand)")
_BD_MINIMUM = re.compile(r"\(?e\)\s*(\d[\d,]*) (kVA|kilowatts)")
_ON_PEAK = re.compile(
    r"On-Peak is all energy consumption (between \d{1,2}:\d{2} [ap]\.m\. and \d{1,2}:\d{2} [ap]\.m\. "
    r"Monday to Friday, excluding statutory holidays)")
_PEAK_METERED = "The Peak Metered Demand is the highest metered demand in the billing period"
_LAF_TEXT = (
    "The Local Access Fee (LAF) is a surcharge imposed by the City of Edmonton",
    "The LAF applies to all sites within the City of Edmonton",
)
_RIDER_E_TEXT = (
    "SPECIAL FACILITIES CHARGE Rider E",
    "The facilities charge will be set out in a contract, negotiated between the customer and the Company",
)

# Table 1/3 cell descriptions (full match, case-insensitive) fix each cell's unit.
_D_SITE_DAY = r"per site per day"
_D_KWH = r"/kWh of Energy at the Meter"
_D_KVA_DAY = r"per kVA per Day"
_D_KW_DAY = r"per kW per Day"
_D_ON_PEAK = r"/kWh of On-Peak Energy at the Meter"
_D_OFF_PEAK = r"/kWh of Off-Peak Energy at the Meter"
_S_KWH = r"/ ?kWh of Energy Charge"
_S_KVA_CAPACITY = r"/kVA/day of Capacity Charge"
_S_KVA_DEMAND = r"/kVA/day of Demand Charge"
_S_KW_CAPACITY = r"/kW/day of Capacity Charge"
_S_KW_OSS = r"/kW/day of Other System Support Charge"
_S_KW_DEMAND = r"/kW/day of Demand Charge"
_S_RESERVE = r"Operating Reserve Charge \(Total Energy x OR%(?: x Pool Price\))?"

DELIVERY_NOTE = (
    "Delivery charges only: EPCOR Distribution & Transmission Inc. (EDTI) Distribution Access Service (DAS) "
    "and System Access Service (SAS, transmission) charges with the riders the price schedules list; "
    "electricity supply is billed separately by a retailer or the Rate of Last Resort provider."
)
LAF_NOTE = (
    "Local Access Fee (Rider LAF): a surcharge imposed by the City of Edmonton and approved by the AUC that "
    "applies to all sites within the City of Edmonton; municipal fee, not shown as a component."
)
RIDER_E_NOTE = (
    "Rider E (Special Facilities Charge) applies only to facilities EDTI builds on customer-owned or leased "
    "property at the customer's request; the charge is set in a negotiated contract and is not published."
)
MARKET_NOTE = (
    "The SAS operating reserve charge is a printed percentage of the hourly AESO pool price; it is shown as "
    "Variable, never as an estimated value."
)


def _interim_note(year: int) -> str:
    return (
        f"Interim: EDTI prints each {year} DAS and SAS price schedule as '({year} INTERIM RATE)'. These rates are "
        "approved by the Alberta Utilities Commission (AUC) on an interim basis and are subject to its final "
        "decision; true-ups are made through riders such as Rider DJ (DAS True-up Rider) and Rider J (SAS True-Up "
        "Rider), which apply 'when a charge or refund is approved by the AUC'."
    )


@dataclass(frozen=True)
class _Cell:
    """One priced cell of a DAS or SAS price schedule."""

    ref: str
    component_type: str
    name: str
    unit: str
    description: str
    role: str


@dataclass(frozen=True)
class _ClassSpec:
    """A building-scope class: its DAS and SAS cells and the eligibility it must print."""

    code: str
    tariff_name: str
    customer_class: str
    sub_class: str
    rate_structure: str
    demand_unit: Optional[str]
    bounds_pattern: Optional[str]
    bounds: tuple[int, ...]
    phrases: tuple[str, ...]
    eligibility: str
    das: tuple[_Cell, ...]
    sas: tuple[_Cell, ...]
    continued: bool = False


def _fixed(ref: str) -> _Cell:
    return _Cell(ref, "fixed", "Distribution Customer Charge", "$/day", _D_SITE_DAY, "fixed")


def _large_cells(code: str) -> tuple[tuple[_Cell, ...], tuple[_Cell, ...]]:
    das = (
        _fixed(f"DAS-{code}1"),
        _Cell(f"DAS-{code}2", "demand", "Distribution Demand Charge", "$/kW/day", _D_KW_DAY, "demand"),
        _Cell(f"DAS-{code}3", "distribution", "Distribution On-Peak Energy Charge", "$/kWh", _D_ON_PEAK, "on_peak"),
        _Cell(f"DAS-{code}4", "distribution", "Distribution Off-Peak Energy Charge", "$/kWh", _D_OFF_PEAK, "off_peak"),
    )
    sas = (
        _Cell(f"SAS-{code}1", "transmission", "Transmission Energy Charge", "$/kWh", _S_KWH, "energy"),
        _Cell(f"SAS-{code}2", "transmission", "Transmission Capacity Charge", "$/kW/day", _S_KW_CAPACITY, "capacity"),
        _Cell(f"SAS-{code}3", "transmission", "Transmission Other System Support (OSS) Charge", "$/kW/day",
              _S_KW_OSS, "oss"),
        _Cell(f"SAS-{code}4", "transmission", "Transmission Operating Reserve Charge", "%", _S_RESERVE, "market"),
        _Cell(f"SAS-{code}5", "transmission", "Transmission Demand Charge", "$/kW/day", _S_KW_DEMAND, "peak_demand"),
    )
    return das, sas


_TOU_DAS, _TOU_SAS = _large_cells("TOU")
_TOUP_DAS, _TOUP_SAS = _large_cells("TOUP")

CLASS_SPECS: tuple[_ClassSpec, ...] = (
    _ClassSpec(
        "R", "Residential Distribution and Transmission (DAS-R)", "residential", "single household", "flat", None,
        None, (),
        ("For single-phase service at secondary voltage through a single meter",
         "For normal use by a single and separate household",
         "Not applicable to any commercial or industrial use"),
        "Single-phase service at secondary voltage through a single meter for normal use by a single and "
        "separate household; not applicable to any commercial or industrial use.",
        (_fixed("DAS-R1"),
         _Cell("DAS-R2", "distribution", "Distribution Energy Charge", "$/kWh", _D_KWH, "energy")),
        (_Cell("SAS-R1", "transmission", "Transmission Energy Charge", "$/kWh", _S_KWH, "energy"),),
    ),
    _ClassSpec(
        "SC", "Commercial/Industrial <50 kVA Distribution and Transmission (DAS-SC)", "commercial",
        "small commercial/industrial (<50 kVA)", "flat", None,
        r"normal maximum demand of less than (\d[\d,]*) kVA", (50,),
        ("at secondary voltage", "This rate is also applicable to all sites for which no other rate is applicable"),
        "Points of service with a normal maximum demand of less than 50 kVA, single or three-phase at secondary "
        "voltage, energy-metered or estimated; also applies to all sites for which no other rate is applicable.",
        (_fixed("DAS-SC1"),
         _Cell("DAS-SC2", "distribution", "Distribution Energy Charge", "$/kWh", _D_KWH, "energy")),
        (_Cell("SAS-SC1", "transmission", "Transmission Energy Charge", "$/kWh", _S_KWH, "energy"),),
    ),
    _ClassSpec(
        "MC", "Commercial/Industrial 50 kVA to <150 kVA Distribution and Transmission (DAS-MC)", "commercial",
        "medium commercial/industrial (50 to <150 kVA)", "demand", "kVA",
        r"normal maximum demand of greater than or equal to (\d[\d,]*) kVA and less than (\d[\d,]*) kVA", (50, 150),
        ("at secondary voltage", "These services will have demand meters"),
        "Points of service with a normal maximum demand of at least 50 kVA and less than 150 kVA, single or "
        "three-phase at secondary voltage, with demand meters.",
        (_fixed("DAS-MC1"),
         _Cell("DAS-MC2", "demand", "Distribution Demand Charge", "$/kVA/day", _D_KVA_DAY, "demand"),
         _Cell("DAS-MC3", "distribution", "Distribution Energy Charge", "$/kWh", _D_KWH, "energy")),
        (_Cell("SAS-MC1", "transmission", "Transmission Capacity Charge", "$/kVA/day", _S_KVA_CAPACITY, "capacity"),
         _Cell("SAS-MC2", "transmission", "Transmission Energy Charge", "$/kWh", _S_KWH, "energy"),
         _Cell("SAS-MC3", "transmission", "Transmission Demand Charge", "$/kVA/day", _S_KVA_DEMAND, "peak_demand")),
    ),
    _ClassSpec(
        "TOU", "Commercial/Industrial 150 kVA to <5,000 kVA Secondary Distribution and Transmission (DAS-TOU)",
        "commercial",
        "large commercial/industrial, secondary voltage (150 to <5,000 kVA)", "demand", "kW",
        r"normal maximum demand of greater than or equal to (\d[\d,]*) kVA and less than (\d[\d,]*) kVA",
        (150, 5000),
        ("served at the secondary voltage of the transformer, normally with a delivery voltage of below 1,000 volts",
         "interval data metering"),
        "Distribution-connected points of service with a normal maximum demand of at least 150 kVA and less than "
        "5,000 kVA, served at the secondary voltage of the transformer (normally below 1,000 volts), with "
        "interval data metering.",
        _TOU_DAS, _TOU_SAS, continued=True,
    ),
    _ClassSpec(
        "TOUP", "Primary Commercial/Industrial >=150 kVA Distribution and Transmission (DAS-TOUP)", "commercial",
        "commercial/industrial, primary voltage (>=150 kVA)", "demand", "kW",
        r"normal maximum demand of greater than or equal to (\d[\d,]*) kVA for all", (150,),
        ("served at the primary voltage of the transformer, normally with a delivery voltage of over 1,000 volts",
         "interval data metering", "Electric Service Agreement"),
        "Distribution-connected points of service with a normal maximum demand of at least 150 kVA, served at the "
        "primary voltage of the transformer (normally over 1,000 volts), with interval data metering and an "
        "Electric Service Agreement with EDTI.",
        _TOUP_DAS, _TOUP_SAS, continued=True,
    ),
)


# ── Small helpers ────────────────────────────────────────────────

def _today() -> date:
    return datetime.now(timezone.utc).date()


def _flat(text: str) -> str:
    text = text.replace("\uf0b7", " ").replace("\u2019", "'").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(text: str) -> date:
    try:
        return datetime.strptime(text, "%B %d, %Y").date()
    except ValueError as exc:
        raise ValueError(f"unreadable date {text!r}") from exc


def _long(value: date) -> str:
    return f"{value:%B} {value.day}, {value.year}"


def _label_date(label: str) -> Optional[date]:
    try:
        return datetime.strptime(label.strip(), "%B %Y").date()
    except ValueError:
        return None


def _decimal(token: str) -> Decimal:
    raw = token.replace("$", "").replace(",", "").replace(" ", "").rstrip("%")
    negative = raw.startswith("-") or (raw.startswith("(") and raw.endswith(")"))
    try:
        value = Decimal(raw.strip("()-"))
    except InvalidOperation as exc:
        raise ValueError(f"unreadable value {token!r}") from exc
    return -value if negative else value


# ── Discovery ────────────────────────────────────────────────────

@dataclass(frozen=True)
class Edition:
    """One dated document listed on the discovery page."""

    kind: str
    label: str
    label_date: date
    url: str


def discover_editions(html: str, base_url: str = DISCOVERY_URL) -> dict[str, list[Edition]]:
    """Map each tariff/rider section on the discovery page to its dated PDFs, newest first.

    An entry is kept only when its month label (e.g. "January 2026") matches the YYYY-MM stamp in
    its file name, so a mislabelled document is never taken for the current edition.
    """
    soup = parse_html(html)
    found: dict[str, list[Edition]] = {}
    for item in soup.select("div.cmp-accordion__item"):
        heading = item.select_one(".cmp-accordion__title")
        kind = SECTION_KINDS.get(_flat(heading.get_text(" ")).casefold()) if heading else None
        if not kind:
            continue
        for entry in item.select("div.cmp-list__item"):
            link = entry.find("a", href=True)
            if link is None or not urlsplit(link["href"]).path.lower().endswith(".pdf"):
                continue
            title = entry.select_one(".cmp-list__item-title")
            label = _flat(title.get_text(" ")) if title else _flat(link.get("download") or "")
            label_date = _label_date(label)
            url = urljoin(base_url, link["href"])
            stamp = re.search(r"/(\d{4})-(\d{2})[-_][^/]*$", urlsplit(url).path)
            if label_date is None or stamp is None or (int(stamp.group(1)), int(stamp.group(2))) != (
                    label_date.year, label_date.month):
                logger.warning("EPCOR %s document %s labelled %r has no matching dated file name; ignored",
                               kind, url, label)
                continue
            editions = found.setdefault(kind, [])
            if all(existing.url != url for existing in editions):
                editions.append(Edition(kind, label, label_date, url))
    for editions in found.values():
        editions.sort(key=lambda edition: edition.label_date, reverse=True)
    return found


def tariff_effective_date(pages: list[DocumentPage], kind: str) -> Optional[date]:
    """The effective date printed on a DAS/SAS tariff cover, if readable."""
    pattern = re.escape(_COVER_TITLES[kind]) + r" Effective:? " + _DATE
    for page in pages[:2]:
        match = re.search(pattern, _flat(page.text))
        if match:
            try:
                return _parse_date(match.group(1))
            except ValueError:
                return None
    return None


def _rider_title(flat: str, letter: str) -> Optional[re.Match[str]]:
    return re.search(rf"\bRider {letter}(?: - (.+?))? Effective:?\s*{_DATE}", flat)


def rider_effective_date(pages: list[DocumentPage], letter: str) -> Optional[date]:
    """The effective date in a rider edition's title, if readable."""
    for page in pages:
        match = _rider_title(_flat(page.text), letter)
        if match:
            try:
                return _parse_date(match.group(2))
            except ValueError:
                return None
    return None


# ── Riders ───────────────────────────────────────────────────────

@dataclass
class RiderDocument:
    """A parsed rider table: one row of printed cells per price schedule."""

    letter: str
    title: str
    effective: date
    end: Optional[date]
    prefix: str
    rows: dict[str, Optional[tuple[str, ...]]]
    source_url: str
    where: str
    basis: Optional[str] = None
    exclusion: Optional[str] = None


@dataclass(frozen=True)
class _NotApplied:
    note: str


@dataclass(frozen=True)
class _Unreadable:
    reason: str


_RiderStatus = Union[RiderDocument, _NotApplied, _Unreadable]


def parse_rider_pages(
    pages: list[DocumentPage],
    letter: str,
    source_url: str,
    label_date: Optional[date] = None,
    *,
    embedded: bool = False,
) -> RiderDocument:
    """Parse a rider table (standalone edition, or the DAS tariff's own Rider DG table).

    Raises ValueError when the title, effective date, edition month, column order or rows are not
    as published.
    """
    prefix = "DAS" if letter in ("DG", "DJ") else "SAS"
    columns = _RIDER_COLUMNS[prefix]
    row_pattern = re.compile(
        rf"\b{prefix}[- ]([A-Z]+\d*(?:-\d+)?)\*?((?:\s+{_RIDER_TOKEN}){{{len(columns)}}})(?=\s|$)")
    for page in pages:
        flat = _flat(page.text)
        title = _rider_title(flat, letter)
        if title:
            break
    else:
        raise ValueError(f"Rider {letter} title with an effective date not found")
    effective = _parse_date(title.group(2))
    if label_date and (effective.year, effective.month) != (label_date.year, label_date.month):
        raise ValueError(f"Rider {letter} edition mismatch: listed as {label_date:%B %Y}, "
                         f"printed effective {_long(effective)}")
    end = None
    period = re.search(rf"[Ee]ffective {_DATE} to {_DATE}", flat)
    if period:
        start, end = _parse_date(period.group(1)), _parse_date(period.group(2))
        if start != effective or end < start:
            raise ValueError(f"Rider {letter} period {period.group(0)!r} contradicts its title date")
    first_row = row_pattern.search(flat, title.end())
    if first_row is None:
        raise ValueError(f"Rider {letter} rate table not found")
    header = re.sub(r"\s+", "", flat[title.end():first_row.start()]).casefold()
    position = 0
    for word in _RIDER_HEADERS[prefix]:
        position = header.find(word, position)
        if position < 0:
            raise ValueError(f"Rider {letter} column headings changed (missing {word!r})")
        position += len(word)
    rows: dict[str, Optional[tuple[str, ...]]] = {}
    for row in row_pattern.finditer(flat, title.end()):
        code = f"{prefix}-{row.group(1)}"
        tokens = tuple(row.group(2).split())
        rows[code] = tokens if rows.get(code, tokens) == tokens else None
    basis = re.search(r"Based on [^.]*?Proceeding \d+\)?", flat)
    exclusion = re.search(rf"Rider {letter} does not apply to [^.]+\.", flat)
    where = (f"DAS tariff PDF page {page.page_number}, Rider {letter} table" if embedded
             else f"Rider {letter} PDF page {page.page_number}")
    return RiderDocument(
        letter=letter, title=(title.group(1) or _RIDER_TITLES.get(letter, "")).strip(), effective=effective,
        end=end, prefix=prefix, rows=rows, source_url=source_url, where=where,
        basis=basis.group(0) if basis else None, exclusion=exclusion.group(0) if exclusion else None,
    )


def _resolve_rider(
    letter: str,
    pages: Optional[list[DocumentPage]],
    url: Optional[str],
    label: Optional[date],
    governing: date,
    today: date,
) -> _RiderStatus:
    """Decide whether a standalone rider edition applies today."""
    title = _RIDER_TITLES[letter]
    if pages is None:
        latest = f" (latest posted edition: {label:%B %Y})" if label else ""
        return _NotApplied(f"Rider {letter} ({title}): no edition posted for the current tariff period{latest}; "
                           "not applied.")
    try:
        document = parse_rider_pages(pages, letter, url or "", label)
    except ValueError as exc:
        return _Unreadable(str(exc))
    if document.effective > today:
        return _Unreadable(f"Rider {letter} edition is not yet in effect ({document.effective.isoformat()})")
    if document.effective < governing:
        return _NotApplied(f"Rider {letter} ({document.title}): latest edition ({_long(document.effective)}) "
                           "predates the current tariff; not applied.")
    if document.end and document.end < today:
        return _NotApplied(f"Rider {letter} ({document.title}): edition ended {_long(document.end)}; not applied.")
    return document


def _rider_components(
    document: RiderDocument, schedule: str, spec: _ClassSpec, confidence: str, tou_hours: Optional[str],
) -> tuple[list[RateComponent], Optional[str]]:
    row = document.rows.get(schedule)
    if row is None:
        raise ValueError(f"Rider {document.letter} has no single row for {schedule}")
    components: list[RateComponent] = []
    for (column, label), token in zip(_RIDER_COLUMNS[document.prefix], row):
        if token == "N/A":
            continue
        if token == "-":
            raise ValueError(f"Rider {document.letter} {schedule} {label}: no value printed")
        extra: dict[str, object] = {}
        if column == "energy":
            unit = "$/kWh"
        elif column == "customer":
            unit = "$/day"
        elif column == "demand" and spec.demand_unit:
            unit, extra = f"$/{spec.demand_unit}/day", {"demand_unit": spec.demand_unit}
        elif column == "oss" and spec.demand_unit == "kW":
            unit, extra = "$/kW/day", {"demand_unit": "kW"}
        elif column in ("on_peak", "off_peak") and tou_hours:
            unit = "$/kWh"
            extra = {"tou_period": column.replace("_", "-"),
                     "tou_hours": tou_hours if column == "on_peak" else "All energy consumption outside On-Peak"}
        else:
            raise ValueError(f"Rider {document.letter} {schedule} {label}: unit cannot be determined for this class")
        value = float(_decimal(token))
        period = f"effective {_long(document.effective)}" + (
            f" to {_long(document.end)}" if document.end else " (no end date printed)")
        notes = f"{document.title}, {period}; {label} column of the rider table for {schedule}."
        if document.basis:
            notes += f" {document.basis}."
        if document.exclusion:
            notes += f" {document.exclusion}"
        if value < 0:
            notes += " A negative value is a credit."
        components.append(RateComponent(
            component_type="rider",
            component_name=f"Rider {document.letter} - {document.title}" + ("" if column == "energy" else f" ({label})"),
            charge_value=value, charge_unit=unit,
            effective_date=document.effective.isoformat(),
            end_date=document.end.isoformat() if document.end else None,
            source_url=document.source_url,
            source_detail=f"{document.where} (row {schedule}, {label})",
            confidence=confidence, notes=notes, **extra,  # type: ignore[arg-type]
        ))
    note = None if components else f"Rider {document.letter} ({document.title}): N/A for {schedule}."
    return components, note


# ── Tariff documents ─────────────────────────────────────────────

@dataclass(frozen=True)
class _TableCell:
    value: Optional[Decimal]
    raw: str
    description: str
    page_number: int


@dataclass
class _Tariff:
    kind: str
    url: str
    pages: list[DocumentPage]
    effective: date
    table: dict[str, Optional[_TableCell]]


def _read_tariff(pages: list[DocumentPage], kind: str, url: str, label: Optional[date], today: date) -> _Tariff:
    effective = tariff_effective_date(pages, kind)
    if effective is None:
        raise ValueError(f"{kind} tariff cover effective date not found")
    if label and (effective.year, effective.month) != (label.year, label.month):
        raise ValueError(f"{kind} edition mismatch: listed as {label:%B %Y}, cover effective {_long(effective)}")
    if effective > today:
        raise ValueError(f"{kind} tariff not yet in effect ({effective.isoformat()})")
    start_pattern, end_marker, _ = _TABLES[kind]
    table: dict[str, Optional[_TableCell]] = {}
    active = False
    for page in pages:
        if not active:
            title = re.search(start_pattern, _flat(page.text))
            if not title:
                continue
            if int(title.group(1)) != effective.year:
                raise ValueError(f"{kind} rate table is for {title.group(1)}, tariff effective {effective.year}")
            active = True
        text = page.text
        stop = text.find(end_marker)
        for line in (text[:stop] if stop >= 0 else text).splitlines():
            for row in _TABLE_ROW.finditer(line):
                ref, raw = row.group(1), row.group(2)
                cell = _TableCell(None if raw == "Flowthrough" else _decimal(raw), raw,
                                  _flat(row.group(3)), page.page_number)
                if ref in table:
                    old = table[ref]
                    if old is None or (old.value, old.description) != (cell.value, cell.description):
                        table[ref] = None
                    continue
                table[ref] = cell
        if stop >= 0:
            break
    if not table:
        raise ValueError(f"{kind} rate table ({_TABLES[kind][2]}) not found")
    return _Tariff(kind, url, pages, effective, table)


def _schedule_page(tariff: _Tariff, schedule: str, continued: bool = False) -> DocumentPage:
    label = rf"Price Schedule {re.escape(schedule)}" + (r" \(Continued\)" if continued else "")
    pattern = re.compile(label + rf"\s+Effective:?\s*{_DATE}")
    hits = [(page, match) for page in tariff.pages for match in [pattern.search(_flat(page.text))] if match]
    what = f"{schedule}{' continuation' if continued else ''} page"
    if len(hits) != 1:
        raise ValueError(f"{what} with an effective date {'not found' if not hits else 'is duplicated'}")
    page, match = hits[0]
    if _parse_date(match.group(1)) != tariff.effective:
        raise ValueError(f"{what} effective {match.group(1)} differs from the tariff ({_long(tariff.effective)})")
    return page


def _check_eligibility(spec: _ClassSpec, flat: str, schedule: str) -> None:
    for phrase in spec.phrases:
        if phrase not in flat:
            raise ValueError(f"{schedule} eligibility text changed (missing {phrase!r})")
    if spec.bounds_pattern:
        match = re.search(spec.bounds_pattern, flat)
        bounds = tuple(int(group.replace(",", "")) for group in match.groups()) if match else None
        if bounds != spec.bounds:
            raise ValueError(f"{schedule} demand limits {bounds} differ from {spec.bounds}")


def _billing_demand(flat: str, unit: str, schedule: str) -> str:
    percent, clause, minimum = _BD_PERCENT.search(flat), _BD_CLAUSE.search(flat), _BD_MINIMUM.search(flat)
    if not (percent and clause and minimum):
        raise ValueError(f"{schedule} billing demand rules not found")
    if (minimum.group(2) == "kVA") != (unit == "kVA"):
        raise ValueError(f"{schedule} billing demand minimum is in {minimum.group(2)}, charges are per {unit}")
    return (f"Billing demand is the greater of the highest metered demand in the billing period, "
            f"{percent.group(1)}% of the highest metered demand in the 12-month period including and ending with "
            f"the billing period, the estimated demand, the {clause.group(1)}, or {minimum.group(1)} "
            f"{minimum.group(2)}.")


def _service_components(
    spec: _ClassSpec, tariff: _Tariff, page: DocumentPage, cells: tuple[_Cell, ...], confidence: str,
    notes: dict[str, str], tou_hours: Optional[str], interim_year: Optional[int],
) -> list[RateComponent]:
    flat = _flat(page.text)
    schedule = f"{tariff.kind}-{spec.code}"
    refs = list(re.finditer(rf"\b{re.escape(schedule)}(\d+)\*", flat))
    found = [f"{schedule}{ref.group(1)}" for ref in refs]
    if found != [cell.ref for cell in cells]:
        raise ValueError(f"{schedule} price cells {found} differ from {[cell.ref for cell in cells]}")
    tokens = _SCHEDULE_VALUE.findall(flat[refs[-1].end():refs[-1].end() + 240])[:len(cells)]
    if len(tokens) != len(cells):
        raise ValueError(f"{schedule} price values incomplete: {tokens}")
    table_name = _TABLES[tariff.kind][2]
    prefix = f"{interim_year} interim rate. " if interim_year else ""
    components: list[RateComponent] = []
    for cell, token in zip(cells, tokens):
        entry = tariff.table.get(cell.ref)
        if entry is None or entry.value is None:
            raise ValueError(f"{cell.ref} missing or ambiguous in {table_name}")
        value = _decimal(token)
        if value != entry.value or token.endswith("%") != entry.raw.endswith("%"):
            raise ValueError(f"{cell.ref}: schedule value {token} differs from {table_name} value {entry.raw}")
        if not re.fullmatch(cell.description, entry.description, re.I):
            raise ValueError(f"{cell.ref}: {table_name} description changed to {entry.description!r}")
        if token.endswith("%") != (cell.role == "market") or (cell.role == "market" and not 0 < value < 100):
            raise ValueError(f"{cell.ref}: unexpected value form {token!r}")
        common = dict(
            effective_date=tariff.effective.isoformat(), source_url=tariff.url, confidence=confidence,
            source_detail=(f"{tariff.kind} tariff PDF page {page.page_number} (Price Schedule {schedule}, cell "
                           f"{cell.ref}) and page {entry.page_number} ({table_name})"),
        )
        if cell.role == "market":
            percent = format(value, "f")
            components.append(RateComponent(
                component_type=cell.component_type, component_name=cell.name, charge_value=None,
                charge_unit="$/kWh", market_reference=f"AESO pool price x {percent}% (operating reserve)",
                market_source_url=AESO_POOL_PRICE_URL,
                notes=(f"{prefix}Market-indexed: kWh delivered in each hour x {percent}% x the AESO pool price for "
                       f"that hour ({cell.ref}); it varies hourly, so no value is shown."),
                **common,  # type: ignore[arg-type]
            ))
            continue
        extra: dict[str, object] = {}
        if cell.role in ("demand", "capacity", "peak_demand"):
            extra["demand_unit"] = spec.demand_unit
        elif cell.role == "oss":
            extra["demand_unit"] = "kW"
        elif cell.role == "on_peak":
            extra.update(tou_period="on-peak", tou_hours=tou_hours)
        elif cell.role == "off_peak":
            extra.update(tou_period="off-peak", tou_hours="All energy consumption outside On-Peak")
        components.append(RateComponent(
            component_type=cell.component_type, component_name=cell.name, charge_value=float(value),
            charge_unit=cell.unit, notes=(prefix + notes.get(cell.role, "")).strip() or None,
            **common, **extra,  # type: ignore[arg-type]
        ))
    return components


def _listed_riders(page: DocumentPage, schedule: str) -> list[str]:
    flat = _flat(page.text)
    match = re.search(r"Price Adjustments\b(.*?)Note:", flat)
    letters = re.findall(r"\(Rider ([A-Z]{1,4})\)", match.group(1)) if match else []
    if not letters:
        raise ValueError(f"{schedule} price adjustment (rider) list not found")
    if "LAF" in letters and not all(text in flat for text in _LAF_TEXT):
        raise ValueError(f"{schedule} Local Access Fee note changed")
    return list(dict.fromkeys(letters))


def _build_record(
    spec: _ClassSpec, das: _Tariff, sas: _Tariff, riders: dict[str, _RiderStatus], rider_e: bool,
) -> TariffRecord:
    pages = {}
    for tariff in (das, sas):
        schedule = f"{tariff.kind}-{spec.code}"
        main = _schedule_page(tariff, schedule)
        pages[tariff.kind] = (main, _schedule_page(tariff, schedule, continued=True) if spec.continued else main)
        _check_eligibility(spec, _flat(main.text), schedule)
    das_flat, sas_flat = _flat(pages["DAS"][0].text), _flat(pages["SAS"][0].text)
    interim = {
        kind: tariff.effective.year
        for kind, tariff, flat in (("DAS", das, das_flat), ("SAS", sas, sas_flat))
        if f"({tariff.effective.year} INTERIM RATE)" in flat
    }
    confidence = "medium" if interim else "high"

    das_notes = {"fixed": "Per site per day.", "energy": "Per kWh of energy at the meter.",
                 "on_peak": "Per kWh of On-Peak energy at the meter.",
                 "off_peak": "Per kWh of Off-Peak energy at the meter (all energy outside the On-Peak hours)."}
    sas_notes = {"energy": "Per kWh of energy."}
    tou_hours = None
    if spec.demand_unit:
        das_notes["demand"] = (f"Per {spec.demand_unit} of billing demand per day. "
                               + _billing_demand(das_flat, spec.demand_unit, f"DAS-{spec.code}"))
        sas_notes["capacity"] = (f"Per {spec.demand_unit} of billing demand per day. "
                                 + _billing_demand(sas_flat, spec.demand_unit, f"SAS-{spec.code}"))
        if _PEAK_METERED not in sas_flat:
            raise ValueError(f"SAS-{spec.code} Peak Metered Demand definition not found")
        sas_notes["peak_demand"] = (f"Per {spec.demand_unit} of Peak Metered Demand per day; the Peak Metered Demand "
                                    "is the highest metered demand in the billing period.")
        sas_notes["oss"] = "Other System Support charge, per kW per day as printed."
    if any(cell.role == "on_peak" for cell in spec.das):
        on_peak = _ON_PEAK.search(das_flat)
        if not on_peak:
            raise ValueError(f"DAS-{spec.code} On-Peak hours not found")
        tou_hours = on_peak.group(1)

    components = _service_components(spec, das, pages["DAS"][0], spec.das, confidence, das_notes, tou_hours,
                                     interim.get("DAS"))
    components += _service_components(spec, sas, pages["SAS"][0], spec.sas, confidence, sas_notes, tou_hours,
                                      interim.get("SAS"))

    notes = [DELIVERY_NOTE]
    if interim:
        notes.append(_interim_note(max(interim.values())))
    for kind, flat in (("DAS", das_flat), ("SAS", sas_flat)):
        minimum = re.search(r"The minimum daily charge is [^.]+\.", flat)
        if minimum:
            notes.append(f"{kind}-{spec.code}: {minimum.group(0)}")
    for kind in ("DAS", "SAS"):
        schedule = f"{kind}-{spec.code}"
        for letter in _listed_riders(pages[kind][1], schedule):
            if letter not in _ALLOWED_RIDERS[kind]:
                raise ValueError(f"{schedule} lists Rider {letter}, which this parser does not model")
            if letter == "LAF":
                if LAF_NOTE not in notes:
                    notes.append(LAF_NOTE)
                continue
            if letter == "E":
                if not rider_e:
                    raise ValueError("Rider E (Special Facilities Charge) terms changed or missing")
                notes.append(RIDER_E_NOTE)
                continue
            status = riders.get(letter, _Unreadable(f"Rider {letter} document not supplied"))
            if isinstance(status, _Unreadable):
                raise ValueError(status.reason)
            if isinstance(status, _NotApplied):
                notes.append(status.note)
                continue
            rider_parts, rider_note = _rider_components(status, schedule, spec, confidence, tou_hours)
            components += rider_parts
            if rider_note:
                notes.append(rider_note)
    if any(component.market_reference for component in components):
        notes.append(MARKET_NOTE)

    page_list = "; ".join(
        f"{kind} tariff PDF page{'s' if main is not app else ''} {main.page_number}"
        + (f", {app.page_number}" if main is not app else "")
        for kind, (main, app) in pages.items())
    return TariffRecord(
        utility_name="EPCOR Distribution", province="AB", utility_type="electricity",
        tariff_name=spec.tariff_name, tariff_code=f"DAS-{spec.code}", customer_class=spec.customer_class,
        sub_class=spec.sub_class, eligibility=spec.eligibility, rate_structure=spec.rate_structure,
        pricing_method="regulated",
        effective_date=max(component.effective_date for component in components if component.effective_date),
        source_url=das.url, source_page=page_list, confidence=confidence, notes=" ".join(notes),
        components=components,
    )


def parse_tariff_pages(
    das_pages: list[DocumentPage],
    sas_pages: list[DocumentPage],
    rider_pages: dict[str, Optional[list[DocumentPage]]],
    source_urls: dict[str, str],
    today: Optional[date] = None,
    labels: Optional[dict[str, date]] = None,
) -> list[TariffRecord]:
    """Build the in-scope class records from the DAS and SAS tariffs and standalone rider editions.

    ``rider_pages`` maps G/J/K/DJ to the pages of the edition chosen for today, or to None when no
    edition is posted for the current tariff period; an absent key or empty page list is a missing
    required document. ``labels`` holds each document's listed edition month for mismatch checks.
    A class that fails any check is skipped and logged; the others are returned.
    """
    today = today or _today()
    labels = labels or {}
    try:
        das = _read_tariff(das_pages, "DAS", source_urls["DAS"], labels.get("DAS"), today)
        sas = _read_tariff(sas_pages, "SAS", source_urls["SAS"], labels.get("SAS"), today)
    except (KeyError, ValueError) as exc:
        logger.warning("EPCOR Distribution tariffs rejected: %s", exc)
        return []

    riders: dict[str, _RiderStatus] = {}
    for letter, kind in STANDALONE_RIDERS.items():
        if letter not in rider_pages:
            riders[letter] = _Unreadable(f"Rider {letter} document not supplied")
            continue
        governing = das.effective if kind == "DAS" else sas.effective
        riders[letter] = _resolve_rider(letter, rider_pages[letter], source_urls.get(letter), labels.get(letter),
                                        governing, today)
    try:
        dg = parse_rider_pages(das.pages, "DG", das.url, embedded=True)
        if dg.effective != das.effective:
            raise ValueError(f"Rider DG table effective {_long(dg.effective)} differs from the DAS tariff")
        riders["DG"] = dg
    except ValueError as exc:
        riders["DG"] = _Unreadable(str(exc))
    flat_das = " ".join(_flat(page.text) for page in das.pages)
    rider_e = all(text in flat_das for text in _RIDER_E_TEXT)

    records: list[TariffRecord] = []
    for spec in CLASS_SPECS:
        try:
            records.append(_build_record(spec, das, sas, riders, rider_e))
        except ValueError as exc:
            logger.warning("EPCOR Distribution DAS-%s rejected: %s", spec.code, exc)
    return records


class EPCORDistributionScraper(BaseScraper):
    """Scrape EPCOR Distribution & Transmission (Edmonton) DAS + SAS delivery rates."""

    def __init__(self, today: Optional[date] = None):
        super().__init__(utility_name="EPCOR Distribution", province="AB")
        self.today = today

    def scrape(self) -> list[TariffRecord]:
        """Live records for every class that parses; labelled seed only if none can be read."""
        try:
            records = self._try_live_scrape()
        except Exception as exc:  # any fetch/parse failure leaves the labelled seed fallback
            self.logger.warning("EPCOR Distribution live scrape failed: %s", exc)
            records = None
        if records:
            return records
        self.logger.warning("Live scrape failed -- using seed data for EPCOR Distribution")
        return self.mark_fallback(self._seed_data())

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        today = self.today or _today()
        editions = self._discover(today)
        if editions is None:
            return None
        das = self._load_tariff(editions["DAS"], "DAS", today)
        sas = self._load_tariff(editions["SAS"], "SAS", today)
        if das is None or sas is None:
            return None
        labels = {"DAS": das[0].label_date, "SAS": sas[0].label_date}
        urls = {"DAS": das[0].url, "SAS": sas[0].url}
        governing = {"DAS": das[2], "SAS": sas[2]}
        rider_pages: dict[str, Optional[list[DocumentPage]]] = {}
        for letter, kind in STANDALONE_RIDERS.items():
            if letter not in editions:
                self.logger.warning("EPCOR Rider %s section not found on the discovery page", letter)
                continue
            current = [edition for edition in editions[letter] if edition.label_date <= today]
            if not current or current[0].label_date < governing[kind].replace(day=1):
                rider_pages[letter] = None
                if current:
                    labels[letter] = current[0].label_date
                continue
            chosen, pages = self._load_rider(current, letter, today)
            rider_pages[letter], labels[letter], urls[letter] = pages, chosen.label_date, chosen.url
        records = parse_tariff_pages(das[1], sas[1], rider_pages, urls, today=today, labels=labels)
        return self.mark_live_parsed(records) if records else None

    def _discover(self, today: date) -> Optional[dict[str, list[Edition]]]:
        try:
            editions = discover_editions(self.fetch_page(DISCOVERY_URL))
        except Exception as exc:
            self.logger.warning("EPCOR tariff page unavailable: %s", exc)
            editions = {}
        if editions.get("DAS") and editions.get("SAS"):
            return editions
        if today <= FALLBACK_VALID_UNTIL:
            self.logger.warning("EPCOR tariff page unusable; trying the known editions (valid until %s)",
                                FALLBACK_VALID_UNTIL.isoformat())
            return {kind: [Edition(kind, label, _label_date(label), url)  # type: ignore[arg-type]
                           for label, url in entries] for kind, entries in FALLBACK_EDITIONS.items()}
        return None

    def _load_tariff(
        self, editions: list[Edition], kind: str, today: date,
    ) -> Optional[tuple[Edition, list[DocumentPage], date]]:
        for edition in [edition for edition in editions if edition.label_date <= today][:2]:
            pages = self._fetch_pdf_pages(edition.url)
            effective = tariff_effective_date(pages, kind)
            if effective is None:
                self.logger.warning("EPCOR %s tariff %s unreadable", kind, edition.url)
                return None
            if effective <= today:
                return edition, pages, effective
            self.logger.info("EPCOR %s %s is not yet in effect; trying the previous edition", kind, edition.label)
        return None

    def _load_rider(self, editions: list[Edition], letter: str, today: date) -> tuple[Edition, list[DocumentPage]]:
        for edition in editions[:2]:
            try:
                pages = self._fetch_pdf_pages(edition.url)
            except Exception as exc:
                self.logger.warning("EPCOR Rider %s %s unavailable: %s", letter, edition.label, exc)
                return edition, []
            effective = rider_effective_date(pages, letter)
            if effective is None or effective <= today:
                return edition, pages
        return editions[0], []

    def _fetch_pdf_pages(self, url: str) -> list[DocumentPage]:
        return extract_pdf_pages(self.fetch_bytes(url))

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # -- Residential (Rate D100) ------------------------------------------
        records.append(TariffRecord(
            utility_name="EPCOR Distribution",
            province="AB",
            utility_type="electricity",
            tariff_name="Residential Distribution (Rate D100)",
            tariff_code=SEED_RESIDENTIAL["tariff_code"],
            customer_class="residential",
            rate_structure="flat",
            effective_date=EFFECTIVE_DATE,
            source_url=SOURCE_URL,
            confidence="high",
            notes=(
                "Distribution charges only; energy supply from retailer. "
                "EPCOR Distribution serves the City of Edmonton. "
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

        # -- Small Commercial (Rate D200) -------------------------------------
        records.append(TariffRecord(
            utility_name="EPCOR Distribution",
            province="AB",
            utility_type="electricity",
            tariff_name="Small General Service Distribution (Rate D200)",
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

        # -- Large Commercial (Rate D300) -------------------------------------
        records.append(TariffRecord(
            utility_name="EPCOR Distribution",
            province="AB",
            utility_type="electricity",
            tariff_name="Large General Service Distribution (Rate D300)",
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
