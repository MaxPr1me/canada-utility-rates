"""
fortisalberta.py -- Scraper for FortisAlberta wires (transmission and distribution) rates.

FortisAlberta Inc. is the AUC-regulated distribution utility for central and
southern Alberta. Its "Rates, Options and Riders Schedules" PDF is reissued
whenever a rider changes (normally each quarter); the newest edition already in
effect is read from:

  https://www.fortisalberta.com/customer-service/rates-and-billing/rates-options-and-riders

Building classes parsed, each with its printed transmission and distribution
charges and its current riders as separate dated components:

  Rate 11 Residential, Rate 41 Small General Service (<75 kW),
  Rate 61 General Service (<=2,000 kW), Rate 63 Large General Service (>2,000 kW),
  Rate 65 Transmission Connected Service (distribution service charge; the AESO
  ISO tariff transmission charges are flowed through and shown without a value).

Option A (primary service credit) and Option I (interval metering) are
conditional components. Rider A-1 and the Municipal Franchise Fee Riders are
municipality-specific percentages, recorded as conditions without a value.

Excluded: farm (21, 22), grain drying (23), irrigation (26), street and yard
lighting (31, 33, 38), oil and gas (44, 45), EV fast charging (62), opportunity
transmission (66), distributed generation (Option M), customer-specific
facilities (Rider E) and REA wire-owner charges and riders.

Energy is bought separately from a retailer or the Rate of Last Resort provider.
Regulated by the Alberta Utilities Commission (AUC).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from urllib.parse import unquote, urljoin, urlsplit

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.fortisalberta.com/customer-service/rates-and-billing/rates-options-and-riders"
AESO_TARIFF_URL = "https://www.aeso.ca/rules-standards-and-tariff/tariff/"

# Seed data for FortisAlberta distribution rates (fallback only).
EFFECTIVE_DATE = "2024-01-01"

SEED_RESIDENTIAL = {
    "tariff_code": "D10",
    "basic_charge_per_day": 0.7854,   # $/day
    "distribution_rate": 0.0177,       # $/kWh
}

SEED_SMALL_COMMERCIAL = {
    "tariff_code": "D20",
    "basic_charge_per_day": 1.0264,   # $/day
    "distribution_rate": 0.0215,       # $/kWh
}

SEED_LARGE_COMMERCIAL = {
    "tariff_code": "D30",
    "basic_charge_per_day": 18.95,    # $/day
    "demand_charge": 4.8900,           # $/kW
    "distribution_rate": 0.0028,       # $/kWh
}

# Newest linked editions inspected (page order is newest first).
_MAX_EDITIONS = 4

_DATE = r"[A-Z][a-z]+\.? \d{1,2}, \d{4}"
_MONEY = r"\$(\d+\.\d+)"
_MONTHS = {
    name: number
    for number, full in enumerate(
        ("january", "february", "march", "april", "may", "june", "july",
         "august", "september", "october", "november", "december"), 1)
    for name in (full, full[:3])
}
_PUNCTUATION = str.maketrans({"\u2019": "'", "\u2018": "'", "\u2013": "-", "\u2014": "-", "\u00a0": " "})
_PAGE_HEADER = re.compile(r"^FortisAlberta Inc\. Rates, Options and Riders Schedules ?")
_PAGE_FOOTER = re.compile(r" ?\bPage (\d+)$")
# Schedule headings are upper case; mixed-case mentions in the text are references, not headings.
_HEADING = re.compile(
    r"TABLE OF|RATE ?\d{2}:|OPTION ?[A-Z]:|RIDER [A-Z](?:-\d)?\b|BASE TRANSMISSION ADJUSTMENT RIDER|"
    r"QUARTERLY ?TRANSMISSION ADJUSTMENT RIDER|BALANCING POOL ALLOCATION RIDER|"
    r"MUNICIPAL FRANCHISE FEE RIDERS|REA ?WIRE OWNER"
)
_EFFECTIVE = re.compile(rf"Effective Date: ({_DATE})")
_DECISION = re.compile(r"Approved in AUC Decision: (?:Decision )?(\d{5}-D\d{2}-\d{4})")
_BASE_HEADING = re.compile(r"BASE TRANSMISSION ADJUSTMENT RIDER(?! FOR REA)")
_QTAR_HEADING = re.compile(r"QUARTERLY ?TRANSMISSION ADJUSTMENT RIDER(?! FOR REA)")
_BPAR_HEADING = re.compile(r"BALANCING POOL ALLOCATION RIDER(?! FOR REA)")
_OPTION_A_HEADING = re.compile(r"OPTION ?A: ?PRIMARY SERVICE OPTION")
_OPTION_I_HEADING = re.compile(r"OPTION ?I: ?INTERVAL METERING OPTION")
_LINK_DATE = re.compile(r"Effective ([A-Za-z]+)\.? ?(\d{1,2}),? (\d{4})", re.I)
_URL_DATE = re.compile(r"effective-([a-z]+)-?(\d{1,2})-(\d{4})")

_APPLICABLE = {
    "Rider A-1 Municipal Assessment Rider": "a1",
    "Municipal Franchise Fee Riders": "mff",
    "Base Transmission Adjustment Rider": "base",
    "Quarterly Transmission Adjustment Rider": "qtar",
    "Balancing Pool Allocation Rider": "bpar",
    "Option A - Primary Service Option": "option_a",
    "Option C - Idle Service Option": "option_c",
    "Option D - Flat Rate Option": "option_d",
    "Option I - Interval Metering Option": "option_i",
}

_KVA_ALTERNATIVE = (
    "Conditional: kVA-basis alternative to the kW-basis charge; the amount billed is the greater of the two, "
    "so never add both."
)
_KW_BASIS = "Billed as the greater of this kW-basis charge and its kVA-basis alternative."


@dataclass(frozen=True)
class _ClassSpec:
    code: str
    heading: str
    tariff_name: str
    customer_class: str
    sub_class: Optional[str]
    rate_structure: str
    shape: str
    row: str  # the class's rate-code cell as printed in the rider tables


_CLASSES = (
    _ClassSpec("11", "RESIDENTIAL SERVICE", "Residential Distribution (Rate 11)", "residential", None,
               "flat", "flat", r"11"),
    _ClassSpec("41", "SMALL GENERAL SERVICE", "Small General Service Distribution (Rate 41)", "commercial",
               "small general service", "demand", "demand", r"41"),
    _ClassSpec("61", "GENERAL SERVICE", "General Service Distribution (Rate 61)", "commercial",
               "general service", "demand", "demand", r"61 ?(?:&|and) ?62"),
    _ClassSpec("63", "LARGE GENERAL SERVICE", "Large General Service Distribution (Rate 63)", "commercial",
               "large general service", "demand", "large", r"63"),
    _ClassSpec("65", "TRANSMISSION CONNECTED SERVICE", "Transmission Connected Service Distribution (Rate 65)",
               "industrial", "transmission connected service", "mixed", "transmission_connected", r"65"),
)


def _today() -> date:
    return datetime.now(timezone.utc).date()


def _date(text: str) -> date:
    match = re.fullmatch(r"([A-Za-z]+)\.? ?(\d{1,2}),? (\d{4})", text.strip())
    month = _MONTHS.get(match.group(1).lower()) if match else None
    if not match or not month:
        raise ValueError(f"unparseable date {text!r}")
    return date(int(match.group(3)), month, int(match.group(2)))


def _long_date(value: date) -> str:
    return f"{value:%B} {value.day}, {value.year}"


# ─── Document model ────────────────────────────────────────────

@dataclass(frozen=True)
class _Document:
    """Flattened schedule text that keeps page boundaries for attribution."""

    text: str
    pages: tuple[tuple[int, int, Optional[str]], ...]  # (offset, PDF page, printed page)
    source_url: str

    def detail(self, offset: int) -> str:
        _, number, printed = [entry for entry in self.pages if entry[0] <= offset][-1]
        return f"PDF page {number}" + (f" (schedule page {printed})" if printed else "")

    def page_numbers(self, start: int, end: int) -> list[int]:
        bounds = [entry[0] for entry in self.pages[1:]] + [len(self.text) + 1]
        return [number for (offset, number, _), stop in zip(self.pages, bounds) if offset < end and stop > start]


@dataclass(frozen=True)
class _Section:
    doc: _Document
    start: int
    text: str

    def one(self, pattern: str | re.Pattern[str], what: str, lo: int = 0, hi: Optional[int] = None) -> re.Match[str]:
        """Exactly one match, so a duplicated or missing row fails closed."""
        regex = re.compile(pattern) if isinstance(pattern, str) else pattern
        matches = list(regex.finditer(self.text, lo, len(self.text) if hi is None else hi))
        if len(matches) != 1:
            raise ValueError(f"{'missing' if not matches else 'ambiguous'} {what}")
        return matches[0]

    def block(self, opening: str, closing: str) -> tuple[int, int]:
        lo = self.one(re.escape(opening), f"'{opening}' heading").end()
        hi = self.one(re.escape(closing), f"'{closing}' heading").start()
        if hi <= lo:
            raise ValueError(f"'{opening}' and '{closing}' are out of order")
        return lo, hi

    def detail(self, match: re.Match[str]) -> str:
        return self.doc.detail(self.start + match.start())

    def pages(self) -> list[int]:
        return self.doc.page_numbers(self.start, self.start + len(self.text))


def _document(pages: list[DocumentPage], source_url: str) -> _Document:
    parts: list[str] = []
    index: list[tuple[int, int, Optional[str]]] = []
    offset = 0
    for page in sorted(pages, key=lambda p: p.page_number):
        flat = _PAGE_HEADER.sub("", re.sub(r"\s+", " ", page.text.translate(_PUNCTUATION)).strip())
        footer = _PAGE_FOOTER.search(flat)
        flat = _PAGE_FOOTER.sub("", flat)
        index.append((offset, page.page_number, footer.group(1) if footer else None))
        parts.append(flat)
        offset += len(flat) + 1
    return _Document(" ".join(parts), tuple(index), source_url)


def _schedule(doc: _Document, heading: re.Pattern[str], labels: tuple[str, ...], what: str) -> _Section:
    """The one heading occurrence followed by its charge labels; table-of-contents entries never qualify."""
    found = []
    for match in heading.finditer(doc.text):
        following = _HEADING.search(doc.text, match.end())
        section = _Section(doc, match.start(), doc.text[match.start():following.start() if following else None])
        if "Approved in AUC Decision" in section.text and all(label in section.text for label in labels):
            found.append(section)
    if len(found) != 1:
        raise ValueError(f"{what} schedule {'not found' if not found else 'printed more than once'}")
    return found[0]


def _stamp(section: _Section, what: str) -> tuple[str, date]:
    decision = section.one(_DECISION, f"{what} AUC decision").group(1)
    return decision, _date(section.one(_EFFECTIVE, f"{what} effective date").group(1))


def document_edition_date(pages: list[DocumentPage]) -> date:
    """The newest effective date printed anywhere in a Rates, Options and Riders edition."""
    dates = [_date(text) for text in _EFFECTIVE.findall(_document(pages, "").text)]
    if not dates:
        raise ValueError("no effective dates printed in the schedule")
    return max(dates)


def schedule_links(html: str, base_url: str = SOURCE_URL) -> list[tuple[str, Optional[date]]]:
    """Rates, Options and Riders PDF links in page order, with the edition date stated by label or file name."""
    links: list[tuple[str, Optional[date]]] = []
    for anchor in parse_html(html).find_all("a", href=True):
        url = urljoin(base_url, anchor["href"])
        path = unquote(urlsplit(url).path).lower()
        label = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))
        if not path.endswith(".pdf") or any(url == known for known, _ in links):
            continue
        if not re.search(r"rates?,? options,? and riders?", f"{label} {path.replace('-', ' ')}", re.I):
            continue
        links.append((url, _link_date(_LINK_DATE.search(label)) or _link_date(_URL_DATE.search(path))))
    return links


def _link_date(match: Optional[re.Match[str]]) -> Optional[date]:
    if not match:
        return None
    try:
        return _date(f"{match.group(1)} {match.group(2)}, {match.group(3)}")
    except ValueError:
        return None


# ─── Components ────────────────────────────────────────────────

def _charge(
    section: _Section,
    match: re.Match[str],
    group: int,
    kind: str,
    name: str,
    unit: str,
    effective: date,
    where: str,
    *,
    sign: int = 1,
    allow_zero: bool = False,
    **fields: object,
) -> RateComponent:
    value = float(match.group(group))
    if value == 0 and not allow_zero:
        raise ValueError(f"zero {name}")
    return RateComponent(
        component_type=kind,
        component_name=name,
        charge_value=sign * value if value else 0.0,
        charge_unit=unit,
        demand_unit={"$/kW/day": "kW", "$/kVA/day": "kVA"}.get(unit),
        effective_date=effective.isoformat(),
        source_url=section.doc.source_url,
        source_detail=f"{section.detail(match)}; {where}",
        confidence="high",
        **fields,  # type: ignore[arg-type]
    )


def _kw_kva_pair(
    section: _Section,
    match: re.Match[str],
    kind: str,
    name: str,
    effective: date,
    where: str,
    basis: str,
) -> list[RateComponent]:
    """A printed kW rate and its kVA alternative (the greater of the two is billed)."""
    return [
        _charge(section, match, 1, kind, f"{name} (kW)", "$/kW/day", effective, f"{where}, kW Rate",
                notes=f"Per kW of {basis} per day. {_KW_BASIS}"),
        _charge(section, match, 2, kind, f"{name} (kVA)", "$/kVA/day", effective, f"{where}, kVA Rate",
                sub_component="alternative", notes=f"{_KVA_ALTERNATIVE} Per kVA of {basis} per day."),
    ]


def _rider_row(section: _Section, spec: _ClassSpec, value: str, what: str) -> re.Match[str]:
    return section.one(rf"(?<![\d$.,]){spec.row} {value}", f"{what} row for Rate {spec.code}")


def _base_rider(doc: _Document, spec: _ClassSpec, today: date) -> tuple[Optional[RateComponent], Optional[str]]:
    what = "Base Transmission Adjustment Rider"
    section = _schedule(doc, _BASE_HEADING, ("Rate Class Description",), what)
    decision, effective = _stamp(section, what)
    period = section.one(rf"from ({_DATE}) to ({_DATE})", f"{what} period")
    start, end = _date(period.group(1)), _date(period.group(2))
    if start != effective or end < start:
        raise ValueError(f"{what} period does not match its effective date")
    section.one(r"applies as a percentage \(%\) of the Customer's base Transmission Charges", f"{what} basis")
    row = _rider_row(section, spec, rf"(?:(-?\d+\.\d+)%|\((\d+\.\d+)%\)|{_MONEY} ?/day)", what)
    if effective > today:
        return None, f"The {what} starts {_long_date(effective)}; not included."
    if end < today:
        return None, f"The {what} period ended {_long_date(end)}; not included."
    period_text = f"Applies from {_long_date(start)} to {_long_date(end)} (AUC Decision {decision})."
    where = f"{what}, Rate {spec.code} row"
    if row.group(3):
        return _charge(section, row, 3, "rider", what, "$/day", effective, where, end_date=end.isoformat(),
                       notes=f"Printed as a daily charge for Rate {spec.code} rather than a percentage. {period_text}"), None
    percent = float(row.group(1)) if row.group(1) else -float(row.group(2))
    return RateComponent(
        component_type="rider",
        component_name=what,
        charge_value=percent if percent else 0.0,
        charge_unit="%",
        effective_date=effective.isoformat(),
        end_date=end.isoformat(),
        source_url=doc.source_url,
        source_detail=f"{section.detail(row)}; {where}",
        confidence="high",
        notes="Percentage of the customer's base Transmission Charges (the transmission components of this "
              "rate); a negative value is a credit. " + period_text,
    ), None


def _quarterly_rider(doc: _Document, spec: _ClassSpec, today: date) -> tuple[Optional[RateComponent], Optional[str]]:
    what = "Quarterly Transmission Adjustment Rider"
    section = _schedule(doc, _QTAR_HEADING, ("Rate Class Description",), what)
    stamps = {
        int(quarter): (decision, _date(text))
        for quarter, decision, text in re.findall(
            rf"Q([1-4]): Approved in AUC Decision: (?:Decision )?(\d{{5}}-D\d{{2}}-\d{{4}}) Effective Date: ({_DATE})",
            section.text)
    }
    header = section.one(rf"Rate Code ((?:Q[1-4] ?)+) ((?:{_DATE} ?)+)", f"{what} column header")
    quarters = [int(token[1]) for token in header.group(1).split()]
    columns = [_date(text) for text in re.findall(_DATE, header.group(2))]
    if not stamps or quarters != list(range(1, len(quarters) + 1)) or len(columns) != len(quarters) \
            or columns != sorted(set(columns)):
        raise ValueError(f"{what} quarter columns are incomplete or out of order")
    if any(quarter > len(columns) or columns[quarter - 1] != stamped for quarter, (_, stamped) in stamps.items()):
        raise ValueError(f"{what} approval dates differ from the quarter column dates")
    period_end = _date(section.one(rf"from {_DATE} to ({_DATE})", f"{what} period").group(1))
    row = _rider_row(section, spec, rf"((?:\(?{_MONEY}\)? ?/kWh ?)+)", what)
    cells = list(re.finditer(rf"(\(?){_MONEY}(\)?) ?/kWh", row.group(1)))
    if len(cells) > len(columns):
        raise ValueError(f"{what} has more values than quarters for Rate {spec.code}")
    current = [quarter for quarter, (_, stamped) in stamps.items() if stamped <= today]
    if not current:
        return None, f"No {what} quarter is in effect yet; not included."
    quarter = max(current)
    decision, effective = stamps[quarter]
    end = columns[quarter] - timedelta(days=1) if quarter < len(columns) else period_end
    if end < today:
        return None, (f"The {what} for Q{quarter} ended {_long_date(end)} and no later quarter is approved "
                      "in this edition; not included.")
    if len(cells) < quarter:
        raise ValueError(f"{what} Q{quarter} value missing for Rate {spec.code}")
    cell = cells[quarter - 1]
    if bool(cell.group(1)) != bool(cell.group(3)):
        raise ValueError(f"{what} Q{quarter} value for Rate {spec.code} has unbalanced credit parentheses")
    value = float(cell.group(2))
    return RateComponent(
        component_type="rider",
        component_name=what,
        charge_value=-value if cell.group(1) and value else value,
        charge_unit="$/kWh",
        effective_date=effective.isoformat(),
        end_date=end.isoformat(),
        source_url=doc.source_url,
        source_detail=f"{section.detail(row)}; {what}, Rate {spec.code} row, Q{quarter} column",
        confidence="high",
        notes=(f"Q{quarter} rate (AUC Decision {decision}) per kWh, applied to the Distribution Tariff; "
               "a negative value is a credit. Replaced each quarter."),
    ), None


def _balancing_pool_rider(doc: _Document, spec: _ClassSpec, today: date) -> tuple[Optional[RateComponent], Optional[str]]:
    what = "Balancing Pool Allocation Rider"
    section = _schedule(doc, _BPAR_HEADING, ("Rate Class Description",), what)
    decision, effective = _stamp(section, what)
    row = _rider_row(section, spec, rf"(\(?){_MONEY}(\)?) ?/kWh", what)
    if bool(row.group(1)) != bool(row.group(3)):
        raise ValueError(f"{what} value for Rate {spec.code} has unbalanced credit parentheses")
    if effective > today:
        return None, f"The {what} starts {_long_date(effective)}; not included."
    return _charge(section, row, 2, "rider", what, "$/kWh", effective, f"{what}, Rate {spec.code} row",
                   sign=-1 if row.group(1) else 1, allow_zero=True,
                   notes=f"Per kWh (AUC Decision {decision}); a negative value is a credit."), None


def _option_a(doc: _Document, spec: _ClassSpec, today: date) -> tuple[list[RateComponent], Optional[str]]:
    what = "Option A Primary Service Option"
    section = _schedule(doc, _OPTION_A_HEADING, ("Local Facilities Credit",), what)
    decision, effective = _stamp(section, what)
    availability = section.one(r"Availability (.+?) Distribution Charges", f"{what} availability").group(1)
    if f"Rate {spec.code}" not in availability:
        raise ValueError(f"{what} availability does not name Rate {spec.code}")
    credit = section.one(
        rf"Local Facilities Credit ?1? kW \[or kVA\] of Capacity \({_MONEY}\) ?/kW-day \({_MONEY}\) ?/kVA-day",
        f"{what} credit")
    rule = section.one(r"The Local Facilities Credit is the lesser of the kW of Capacity Credit or the kVA of "
                       r"Capacity Credit\.", f"{what} lesser-of rule").group(0)
    if effective > today:
        return [], f"{what} starts {_long_date(effective)}; not included."
    condition = f"Conditional: {what} (AUC Decision {decision}) only. {availability} {rule}"
    where = f"{what}, Local Facilities Credit"
    return [
        _charge(section, credit, 1, "rebate", "Option A Local Facilities Credit (kW)", "$/kW/day", effective,
                f"{where}, kW Rate", sign=-1, sub_component="conditional",
                notes=f"{condition} Per kW of Capacity per day."),
        _charge(section, credit, 2, "rebate", "Option A Local Facilities Credit (kVA)", "$/kVA/day", effective,
                f"{where}, kVA Rate", sign=-1, sub_component="alternative",
                notes=f"{condition} kVA-basis alternative to the kW-basis credit; never add both."),
    ], None


def _option_i(doc: _Document, spec: _ClassSpec, today: date) -> tuple[list[RateComponent], Optional[str]]:
    what = "Option I Interval Metering Option"
    section = _schedule(doc, _OPTION_I_HEADING, ("Service Charge",), what)
    decision, effective = _stamp(section, what)
    availability = section.one(r"Availability (.+?) Distribution Charges", f"{what} availability").group(1)
    charge = section.one(rf"Service Charge Daily {_MONEY} ?/day", f"{what} service charge")
    if effective > today:
        return [], f"{what} starts {_long_date(effective)}; not included."
    return [
        _charge(section, charge, 1, "fixed", "Option I Interval Metering Service Charge", "$/day", effective,
                f"{what}, Service Charge", sub_component="conditional",
                notes=f"Conditional: {what} (AUC Decision {decision}) only. {availability}"),
    ], None


# ─── Classes ───────────────────────────────────────────────────

def _applicable(section: _Section) -> set[str]:
    listed = section.one(r"Applicable Options and Riders (.+)$", "applicable options and riders").group(1)
    items = [item.strip() for item in listed.split("\u2022") if item.strip()]
    unknown = [item for item in items if item not in _APPLICABLE]
    if not items or unknown:
        raise ValueError(f"unrecognised applicable options or riders: {unknown or listed!r}")
    return {_APPLICABLE[item] for item in items}


def _demand_rules(section: _Section, spec: _ClassSpec) -> str:
    prefix = "Transmission " if spec.shape == "large" else ""
    usage = section.one(
        rf"The {prefix}System Usage Charge is the greater of the Peak Metered kW (?:Demand )?charge or the Peak "
        r"Metered kVA (?:Demand )?charge\.", "kW/kVA system usage rule").group(0)
    peak = section.one(r"The Peak Metered Demand \(in kVA or kW\) is the highest metered kVA or kW demand in the "
                       r"billing period\.", "peak metered demand definition").group(0)
    capacity = section.one(r"(The Transmission Capacity Charge and the Distribution Local Facilities Charge are the "
                           r"greater of: .+?) Minimum Charges", "kW/kVA of Capacity rule").group(1)
    return f"Billing demand: {usage} {peak} {capacity}"


def _size_limits(availability: str) -> tuple[Optional[float], Optional[float]]:
    size = re.search(r"Expected Peak Capacity (less than|of|greater than) ([\d,]+) kW( or less)?", availability)
    if not size:
        raise ValueError("missing Expected Peak Capacity limit")
    limit = float(size.group(2).replace(",", ""))
    if size.group(1) == "greater than" and not size.group(3):
        return limit, None
    if size.group(1) == "less than" and not size.group(3) or size.group(1) == "of" and size.group(3):
        return None, limit
    raise ValueError(f"unrecognised Expected Peak Capacity wording {size.group(0)!r}")


def _parse_class(doc: _Document, spec: _ClassSpec, today: date) -> TariffRecord:
    title = spec.heading.title()
    heading = re.compile(rf"RATE ?{spec.code}: ?{' ?'.join(spec.heading.split())}\b")
    section = _schedule(doc, heading, ("Distribution Charges", "Applicable Options and Riders"), f"Rate {spec.code}")
    decision, effective = _stamp(section, f"Rate {spec.code}")
    if effective > today:
        raise ValueError(f"Rate {spec.code} is not in effect until {effective.isoformat()}")
    availability = section.one(r"Availability (.+?) Transmission Charges", "availability").group(1)
    t_lo, t_hi = section.block("Transmission Charges", "Distribution Charges")
    d_lo, d_hi = section.block("Distribution Charges", "Minimum Charges")
    minimum = section.one(r"Minimum Charges (.+?) Terms and Conditions", "minimum charges").group(1)
    applicable = _applicable(section)
    transmission = f"Rate {spec.code} Transmission Charges"
    distribution = f"Rate {spec.code} Distribution Charges"
    notes = [f"FortisAlberta Rate {spec.code} {title} (AUC Decision {decision}). Wires service only: transmission "
             "and distribution charges plus the current riders; energy is bought separately from a retailer or "
             "the Rate of Last Resort provider. Regulated by the Alberta Utilities Commission (AUC)."]
    demand_min = demand_max = None
    components: list[RateComponent] = []

    if spec.shape == "flat":
        variable = section.one(rf"Variable Charge kWh {_MONEY} ?/kWh", "transmission variable charge", t_lo, t_hi)
        usage = section.one(rf"System Usage Charge kWh {_MONEY} ?/kWh", "system usage charge", d_lo, d_hi)
        facilities = section.one(rf"Facilities and Service Charge \(for each unit\) Daily {_MONEY} ?/day",
                                 "facilities and service charge", d_lo, d_hi)
        components += [
            _charge(section, variable, 1, "transmission", "Transmission Variable Charge", "$/kWh", effective,
                    f"{transmission}, Variable Charge", notes="Transmission charge per kWh."),
            _charge(section, usage, 1, "distribution", "System Usage Charge", "$/kWh", effective,
                    f"{distribution}, System Usage Charge", notes="Distribution charge per kWh."),
            _charge(section, facilities, 1, "fixed", "Facilities and Service Charge", "$/day", effective,
                    f"{distribution}, Facilities and Service Charge",
                    notes="Daily distribution charge for each unit."),
        ]
    elif spec.shape in ("demand", "large"):
        demand_min, demand_max = _size_limits(availability)
        usage = section.one(rf"System Usage Charge ?1? {_MONEY} ?/kW-day {_MONEY} ?/kVA-day",
                            "transmission system usage charge", t_lo, t_hi)
        capacity = section.one(rf"Capacity Charge ?2? kW \[or kVA\] of Capacity {_MONEY} ?/kW-day {_MONEY} ?/kVA-day",
                               "transmission capacity charge", t_lo, t_hi)
        variable = section.one(rf"Variable Charge kWh {_MONEY} ?/kWh", "transmission variable charge", t_lo, t_hi)
        facilities = section.one(
            rf"Local Facilities Charge ?2? kW \[or kVA\] of Capacity {_MONEY} ?/kW-day {_MONEY} ?/kVA-day",
            "local facilities charge", d_lo, d_hi)
        service = section.one(rf"Service Charge Daily {_MONEY} ?/day", "service charge", d_lo, d_hi)
        components += _kw_kva_pair(section, usage, "transmission", "Transmission System Usage Charge", effective,
                                   f"{transmission}, System Usage Charge", "Peak Metered Demand")
        components += _kw_kva_pair(section, capacity, "transmission", "Transmission Capacity Charge", effective,
                                   f"{transmission}, Capacity Charge", "Capacity")
        components.append(_charge(section, variable, 1, "transmission", "Transmission Variable Charge", "$/kWh",
                                  effective, f"{transmission}, Variable Charge", notes="Transmission charge per kWh."))
        if spec.shape == "demand":
            system = section.one(rf"System Usage Charge ?1? {_MONEY} ?/kW-day {_MONEY} ?/kVA-day",
                                 "distribution system usage charge", d_lo, d_hi)
            components += _kw_kva_pair(section, system, "demand", "Distribution System Usage Charge", effective,
                                       f"{distribution}, System Usage Charge", "Peak Metered Demand")
        else:
            route = section.one(rf"System Usage Charge Contract km {_MONEY} ?/km-day",
                                "distribution system usage charge per contract km", d_lo, d_hi)
            components.append(_charge(section, route, 1, "distribution", "Distribution System Usage Charge",
                                      "$/km/day", effective, f"{distribution}, System Usage Charge",
                                      notes="Per contract km per day (billing unit printed as 'Contract km')."))
        components += _kw_kva_pair(section, facilities, "demand", "Local Facilities Charge", effective,
                                   f"{distribution}, Local Facilities Charge", "Capacity")
        components.append(_charge(section, service, 1, "fixed", "Service Charge", "$/day", effective,
                                  f"{distribution}, Service Charge", notes="Daily distribution service charge."))
        notes.append(_demand_rules(section, spec))
    else:
        flow = section.one(
            r"The Transmission Charge is the current Independent System Operator \(ISO\) tariff charges as billed by "
            r"the Alberta Electric System Operator ?\(AESO\) flowed through directly to the Customer\.",
            "ISO tariff flow-through statement", t_lo, t_hi)
        service = section.one(rf"Service Charge {_MONEY} ?/day", "service charge", d_lo, d_hi)
        flow_notes = ("Not priced in the FortisAlberta schedule: " + flow.group(0) +
                      " The AESO ISO tariff for the customer's Point of Delivery sets the amount.")
        try:
            bpar = _schedule(doc, _BPAR_HEADING, ("Rate Class Description",), "Balancing Pool Allocation Rider")
            rider_f = _rider_row(bpar, spec, r"ISO tariff Rider F flowed through to Customer", "Balancing Pool")
            flow_notes += (f" Per the Balancing Pool Allocation Rider table, {bpar.detail(rider_f)}, ISO tariff "
                           "Rider F is also flowed through.")
        except ValueError:
            pass
        notes.append("Transmission charges are the AESO ISO tariff charges for the Point of Delivery, flowed "
                     "through at cost; FortisAlberta prints no transmission price for this rate.")
        components += [
            RateComponent(
                component_type="transmission", component_name="Transmission Charge (AESO ISO tariff flow-through)",
                market_reference="AESO ISO tariff charges for the customer's Point of Delivery, flowed through at cost",
                market_source_url=AESO_TARIFF_URL, effective_date=effective.isoformat(),
                source_url=doc.source_url, source_detail=f"{section.detail(flow)}; {transmission}",
                confidence="high", notes=flow_notes),
            _charge(section, service, 1, "fixed", "Service Charge", "$/day", effective,
                    f"{distribution}, Service Charge", notes="Daily distribution service charge."),
        ]

    notes.append(f"Minimum charges: {minimum}")
    if spec.shape == "flat":
        exclusions = re.search(r"Exclusions (.+?) Applicable Options and Riders", section.text)
        if exclusions:
            notes.append(f"Exclusions: {exclusions.group(1)}")

    used_pages = set(section.pages())
    for key, parser in (("base", _base_rider), ("qtar", _quarterly_rider), ("bpar", _balancing_pool_rider)):
        if key in applicable:
            rider, skipped = parser(doc, spec, today)
            if rider:
                components.append(rider)
            if skipped:
                notes.append(skipped)
    for key, parser in (("option_a", _option_a), ("option_i", _option_i)):
        if key in applicable:
            extra, skipped = parser(doc, spec, today)
            components += extra
            if skipped:
                notes.append(skipped)
    for component in components:
        page = re.match(r"PDF page (\d+)", component.source_detail or "")
        if page:
            used_pages.add(int(page.group(1)))

    municipal = [name for key, name in (("a1", "Rider A-1 Municipal Assessment Rider"),
                                         ("mff", "Municipal Franchise Fee Riders")) if key in applicable]
    if municipal:
        notes.append("Conditional (not included): " + " and ".join(municipal) + " add a municipality-specific "
                     "percentage to the total transmission and distribution charges, excluding riders.")
    if "option_c" in applicable:
        notes.append("Option C (Idle Service): while a service is de-energized, the rate's minimum charges apply.")
    if "option_d" in applicable:
        notes.append("Option D (Flat Rate): unmetered services may be billed on an estimated kW of Capacity, "
                     "Peak Metered Demand and kWh.")

    standard = [c for c in components if c.sub_component not in ("conditional", "alternative") and c.effective_date]
    return TariffRecord(
        utility_name="FortisAlberta",
        province="AB",
        utility_type="electricity",
        tariff_name=spec.tariff_name,
        tariff_code=spec.code,
        customer_class=spec.customer_class,
        sub_class=spec.sub_class,
        eligibility=availability,
        demand_min_kw=demand_min,
        demand_max_kw=demand_max,
        rate_structure=spec.rate_structure,
        pricing_method="regulated",
        effective_date=max(c.effective_date for c in standard),
        source_url=doc.source_url,
        source_page="PDF pages " + ", ".join(str(number) for number in sorted(used_pages)),
        confidence="high",
        notes=" ".join(notes),
        components=components,
    )


def parse_schedule_pages(
    pages: list[DocumentPage],
    source_url: str,
    today: Optional[date] = None,
    rejected: Optional[dict[str, str]] = None,
) -> list[TariffRecord]:
    """Parse each in-scope class independently; a failing class is skipped and its reason kept in ``rejected``."""
    today = today or _today()
    doc = _document(pages, source_url)
    records: list[TariffRecord] = []
    for spec in _CLASSES:
        try:
            records.append(_parse_class(doc, spec, today))
        except ValueError as exc:
            logger.warning("FortisAlberta Rate %s rejected: %s", spec.code, exc)
            if rejected is not None:
                rejected[spec.code] = str(exc)
    return records


class FortisAlbertaScraper(BaseScraper):
    """Scrape FortisAlberta building rate classes from the current Rates, Options and Riders Schedules."""

    def __init__(self):
        super().__init__(utility_name="FortisAlberta", province="AB")

    def scrape(self) -> list[TariffRecord]:
        """Only a total fetch/parse failure falls back to the labelled seed estimates."""
        today = _today()
        rejected: dict[str, str] = {}
        try:
            source_url, pages = self._current_schedule(today)
            records = parse_schedule_pages(pages, source_url, today, rejected)
        except Exception as exc:
            self.logger.warning("FortisAlberta schedule could not be read: %s", exc)
            return self.mark_fallback(self._seed_data())
        if not records:
            self.logger.warning("No FortisAlberta class parsed (%s) -- using seed data", rejected)
            return self.mark_fallback(self._seed_data())
        if rejected:
            self.logger.warning("FortisAlberta classes rejected; no estimate emitted for them: %s", rejected)
        return self.mark_live_parsed(records)

    def _current_schedule(self, today: date) -> tuple[str, list[DocumentPage]]:
        """The newest edition already in effect; an older edition is never used in its place."""
        links = schedule_links(self.fetch_page(SOURCE_URL))
        if not links:
            rendered = self.fetch_rendered_page(SOURCE_URL)
            links = schedule_links(rendered) if rendered else []
        if not links:
            raise ValueError("no Rates, Options and Riders schedule PDF is linked")
        for url, stated in links[:_MAX_EDITIONS]:
            if stated and stated > today:
                continue
            pages = self._read_pdf(url)
            edition = document_edition_date(pages)
            if edition > today:
                continue
            if stated and edition != stated:
                raise ValueError(f"{url} is labelled {stated} but its newest effective date is {edition}")
            newer = sorted(other for _, other in links if other and edition < other <= today)
            if newer:
                raise ValueError(f"a newer in-effect edition ({newer[-1]}) is linked below {url}")
            return url, pages
        raise ValueError("no Rates, Options and Riders edition in effect was found")

    def _read_pdf(self, url: str) -> list[DocumentPage]:
        return extract_pdf_pages(self.fetch_bytes(url))

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # -- Residential (Rate D10) -------------------------------------------
        records.append(TariffRecord(
            utility_name="FortisAlberta",
            province="AB",
            utility_type="electricity",
            tariff_name="Residential Distribution (Rate D10)",
            tariff_code=SEED_RESIDENTIAL["tariff_code"],
            customer_class="residential",
            rate_structure="flat",
            effective_date=EFFECTIVE_DATE,
            source_url=SOURCE_URL,
            confidence="high",
            notes=(
                "Distribution charges only; energy supply from retailer. "
                "FortisAlberta serves central and southern Alberta. "
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

        # -- Small Commercial (Rate D20) --------------------------------------
        records.append(TariffRecord(
            utility_name="FortisAlberta",
            province="AB",
            utility_type="electricity",
            tariff_name="Small General Service Distribution (Rate D20)",
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

        # -- Large Commercial (Rate D30) --------------------------------------
        records.append(TariffRecord(
            utility_name="FortisAlberta",
            province="AB",
            utility_type="electricity",
            tariff_name="Large General Service Distribution (Rate D30)",
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
