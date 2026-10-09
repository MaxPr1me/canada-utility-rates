"""
enbridge_gas.py — Scraper for Enbridge Gas Inc. rates (Ontario).

Enbridge Gas (formerly Union Gas + Enbridge Gas Distribution) serves three
legacy rate zones: EGD, Union North (with separate Union North West / North
East gas supply prices) and Union South. Every OEB-approved rate schedule and
rider is published in one Rate Handbook PDF, re-issued with each quarterly
rate order (QRAM).

Official sources:
  Rate Handbook (linked from each large-volume rate page):
    https://www.enbridgegas.com/-/media/Extranet-Pages/ontario/business-and-industrial/Commercial-and-Industrial/Large-Volume-Rates-and-Services/EGD-Rates/rate-handbook.pdf
  https://www.enbridgegas.com/ontario/business-industrial/commercial-industrial/large-volume-services-rates
  https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/fcrates/fuel-charge-rates.html

Each record is one rate class in one zone for a customer buying system gas
from Enbridge (sales service). Marketer supply prices and direct-purchase,
storage, transportation-only and wholesale services are not modelled.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import DocumentPage

logger = logging.getLogger(__name__)

HANDBOOK_URL = (
    "https://www.enbridgegas.com/-/media/Extranet-Pages/ontario/business-and-industrial/"
    "Commercial-and-Industrial/Large-Volume-Rates-and-Services/EGD-Rates/rate-handbook.pdf"
)
DISCOVERY_URLS = (
    "https://www.enbridgegas.com/ontario/business-industrial/commercial-industrial/large-volume-services-rates/"
    "leg-rate-zone-rates/rate-110",
    "https://www.enbridgegas.com/ontario/business-industrial/commercial-industrial/large-volume-services-rates/"
    "union-south/rate-m4",
)
CRA_URL = (
    "https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/fcrates/fuel-charge-rates.html"
)

DATE = r"([A-Z][a-z]+ \d{1,2}, \d{4})"
CENTS = r"(\d{1,3}(?:,\d{3})*\.\d{4,5})"
TOKEN = r"(\(\d+\.\d{4}\)|\d+\.\d{4}|-)"
EDITION_RE = re.compile(
    r"Effective " + DATE + r"\s+Implemented " + DATE + r"\s+OEB Order (EB-\d{4}-\d{4})\s+Supersedes "
    r"(EB-\d{4}-\d{4}) (?:Rate Schedule )?effective " + DATE)

# Seed data based on OEB-approved rates.
# Enbridge operates in two legacy rate zones.
SEED_RATE_1 = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.enbridgegas.com/residential/gas-charges",
    "customer_charge_monthly": 28.44,        # $/month
    "gas_supply_rate": 0.1039,               # $/m³ (commodity)
    "delivery_to_you_rate": 0.0993,          # $/m³
    "transportation_rate": 0.0409,           # $/m³
    "federal_carbon_charge": 0.1239,         # $/m³
    "cost_adjustment_rider": -0.0012,        # $/m³ (can be negative — a credit)
}


@dataclass(frozen=True)
class ClassSpec:
    zone: str
    rate: str
    title: str
    builder: str
    name: str
    customer_class: str
    sub_class: str
    applicability: str


CLASS_SPECS = (
    ClassSpec("EGD", "1", "RESIDENTIAL SERVICE", "general", "Rate 1 Residential Service", "residential",
              "residential building with up to six dwelling units",
              r"to a residential building served through one meter, the Point of Consumption, and containing no "
              r"more than six dwelling units\."),
    ClassSpec("EGD", "6", "GENERAL SERVICE", "general", "Rate 6 General Service", "commercial",
              "general service (non-residential)",
              r"to a single Point of Consumption for non-residential purposes\."),
    ClassSpec("EGD", "100", "FIRM CONTRACT SERVICE", "egd_contract", "Rate 100 Firm Contract Service",
              "industrial", "firm contract service",
              r"maximum daily volume of not less than [\d,]+ m³ and not more than [\d,]+ m³\."),
    ClassSpec("EGD", "110", "LARGE VOLUME LOAD FACTOR SERVICE", "egd_contract",
              "Rate 110 Large Volume Load Factor Service", "industrial", "large volume load factor firm contract service",
              r"annual supply of Gas of not less than \d+ times a specified maximum daily volume of not less than "
              r"[\d,]+ m³\."),
    ClassSpec("EGD", "115", "LARGE VOLUME LOAD FACTOR SERVICE", "egd_contract",
              "Rate 115 Large Volume Load Factor Service", "industrial", "large volume load factor firm contract service",
              r"annual supply of Gas of not less than \d+ times a specified maximum daily volume of not less than "
              r"[\d,]+ m³\."),
    ClassSpec("EGD", "145", "INTERRUPTIBLE SERVICE", "egd_contract", "Rate 145 Interruptible Service", "industrial",
              "interruptible contract service",
              r"must agree to transport a Minimum Annual Volume of (?P<min>[\d,]+) m³\."),
    ClassSpec("EGD", "170", "LARGE INTERRUPTIBLE SERVICE", "egd_contract", "Rate 170 Large Interruptible Service",
              "industrial", "large interruptible contract service",
              r"maximum daily volume of Gas of not less than [\d,]+ m³ and a Minimum Annual Volume of "
              r"(?P<min>[\d,]+) m³"),
    ClassSpec("Union North", "01", "SMALL VOLUME GENERAL FIRM SERVICE", "general",
              "Rate 01 Small Volume General Firm Service", "residential",
              "small volume general service (residential and other end-users)",
              r"whose total Gas requirements at that location are equal to or less than (?P<max>[\d,]+) m³ per year\."),
    ClassSpec("Union North", "10", "LARGE VOLUME GENERAL FIRM SERVICE", "general",
              "Rate 10 Large Volume General Firm Service", "commercial", "large volume general service",
              r"whose total Firm Gas requirements at one or more Company-owned meters at one location exceed "
              r"(?P<min>[\d,]+) m³ per year\."),
    ClassSpec("Union North", "20", "MEDIUM VOLUME FIRM SERVICE", "un_contract", "Rate 20 Medium Volume Firm Service",
              "industrial", "medium volume firm contract service",
              r"whose total maximum daily requirements for Firm or combined Firm and Interruptible Service is "
              r"[\d,]+ m³ or more\."),
    ClassSpec("Union North", "25", "LARGE VOLUME INTERRUPTIBLE SERVICE", "un_interruptible",
              "Rate 25 Large Volume Interruptible Service", "industrial", "large volume interruptible contract service",
              r"whose total maximum daily Interruptible requirement is [\d,]+ m³ or more"),
    ClassSpec("Union North", "100", "LARGE VOLUME HIGH LOAD FACTOR FIRM SERVICE", "un_contract",
              "Rate 100 Large Volume High Load Factor Firm Service", "industrial",
              "large volume high load factor firm contract service",
              r"whose Firm Contract Demand is [\d,]+ m³ or more, and whose annual requirement for Firm Service is "
              r"equal to or greater than its Firm Contract Demand multiplied by \d+\."),
    ClassSpec("Union South", "M1", "SMALL VOLUME GENERAL SERVICE", "general", "Rate M1 Small Volume General Service",
              "residential", "small volume general service (residential and other general service)",
              r"To general service Customers whose total Consumption is equal to or less than (?P<max>[\d,]+) m³ "
              r"per year\."),
    ClassSpec("Union South", "M2", "LARGE VOLUME GENERAL SERVICE", "general", "Rate M2 Large Volume General Service",
              "commercial", "large volume general service",
              r"To general service Customers whose total Consumption is greater than (?P<min>[\d,]+) m³ per year\."),
    ClassSpec("Union South", "M4", "FIRM INDUSTRIAL AND COMMERCIAL CONTRACT SERVICE", "m4",
              "Rate M4 Firm Industrial and Commercial Contract Service", "industrial", "firm contract service",
              r"specifies a Contract Demand between [\d,]+ m³ and [\d,]+ m³\."),
    ClassSpec("Union South", "M5", "INTERRUPTIBLE INDUSTRIAL AND COMMERCIAL CONTRACT SERVICE", "m5",
              "Rate M5 Interruptible Industrial and Commercial Contract Service", "industrial",
              "interruptible contract service",
              r"specifies an Interruptible Contract Demand between (?P<low>[\d,]+) m³ and (?P<high>[\d,]+) m³ "
              r"inclusive\."),
)

EXCLUDED_SCHEDULES = {
    ("EGD", "125"): "unbundled extra-large firm distribution for direct-purchase contracts",
    ("EGD", "135"): "seasonal firm service, outside the agreed class list",
    ("EGD", "200"): "wholesale service to other distributors",
    ("EGD", "300"): "unbundled firm or interruptible distribution for direct-purchase contracts",
    ("EGD", "315"): "gas storage service", ("EGD", "316"): "gas storage service at Dawn",
    ("EGD", "320"): "backstopping gas supply service", ("EGD", "401"): "RNG injection service for producers",
    ("Union South", "M7"): "special large-volume contract with negotiated interruptible and seasonal prices",
    ("Union South", "M9"): "wholesale service to distributors",
    ("Union South", "T1"): "storage and transportation for contract carriage customers",
    ("Union South", "T2"): "storage and transportation for contract carriage customers",
    ("Union South", "T3"): "storage and transportation for a distributor",
}


@dataclass(frozen=True)
class Edition:
    effective: date
    implemented: date
    order: str
    supersedes: str
    superseded_effective: date


@dataclass
class Schedule:
    kind: str
    code: str
    title: str
    pages: list[DocumentPage]
    zone: Optional[str] = None


@dataclass
class RiderC:
    start: date
    end: date
    rows: dict


@dataclass
class _Context:
    edition: Edition
    url: str
    today: date
    carbon: dict
    carbon_note: str
    rider_c: Optional[RiderC]
    rider_i: Optional[tuple]


def blank_overlap_indexes(chars: list[dict], max_gap: float = 0.5, line_tolerance: float = 2.0) -> set[int]:
    """Indexes of blank glyphs drawn inside a number.

    The handbook draws padding blanks over some leading digits, so a plain
    extraction reads 14.2691 as "1 4.2691". A blank whose neighbouring glyphs on
    the same line are less than ``max_gap`` points apart separates nothing.
    """
    lines: dict[int, list[dict]] = {}
    for char in chars:
        if not char["text"].isspace():
            lines.setdefault(round(char["top"]), []).append(char)
    drop: set[int] = set()
    for index, char in enumerate(chars):
        if not char["text"].isspace():
            continue
        key = round(char["top"])
        near = [solid for row in range(key - 2, key + 3) for solid in lines.get(row, ())
                if abs(solid["top"] - char["top"]) <= line_tolerance]
        left = [solid for solid in near if solid["x0"] <= char["x0"]]
        right = [solid for solid in near if solid["x0"] > char["x0"]]
        if left and right:
            before = max(left, key=lambda solid: solid["x0"])
            after = min(right, key=lambda solid: solid["x0"])
            if abs(after["x0"] - before["x1"]) < max_gap:
                drop.add(index)
    return drop


def extract_handbook_pages(pdf_bytes: bytes) -> list[DocumentPage]:
    """Line-preserving page texts with split digits rejoined; empty on failure."""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber not installed — run: pip install pdfplumber")
        return []
    pages: list[DocumentPage] = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for number, page in enumerate(pdf.pages, 1):
                chars = page.chars
                drop = {id(chars[index]) for index in blank_overlap_indexes(chars)}
                raw = page.filter(lambda obj: id(obj) not in drop).extract_text(x_tolerance=2, y_tolerance=3) or ""
                lines = (re.sub(r"\s+", " ", line).strip() for line in raw.splitlines())
                text = "\n".join(line for line in lines if line)
                if text:
                    pages.append(DocumentPage(number, text))
    except Exception as exc:
        logger.warning("Enbridge rate handbook extraction failed closed: %s", exc)
        return []
    return pages


def _dec(text: str) -> Decimal:
    text = text.replace(",", "")
    if text.startswith("(") and text.endswith(")"):
        return -Decimal(text[1:-1])
    return Decimal(text)


def _token(text: str) -> Optional[Decimal]:
    return None if text == "-" else _dec(text)


def _add(*values: Optional[Decimal]) -> Optional[Decimal]:
    present = [value for value in values if value is not None]
    return sum(present, Decimal(0)) if present else None


def _dollars(cents: Decimal) -> float:
    return float(cents / 100)


def _long_date(text: str) -> date:
    return datetime.strptime(text, "%B %d, %Y").date()


def _human(day: date) -> str:
    return f"{day.strftime('%B')} {day.day}, {day.year}"


def _flat(pages: list[DocumentPage]) -> str:
    return " ".join(" ".join(page.text.split()) for page in pages)


def _heading(page: DocumentPage) -> Optional[tuple[str, str, str]]:
    lines = page.text.split("\n")
    for kind in ("RATE", "RIDER"):
        if lines[0] == f"{kind}:" and len(lines) > 1:
            head = lines[1]
        elif lines[0].startswith(f"{kind}: "):
            head = lines[0][len(kind) + 2:]
        else:
            continue
        match = re.fullmatch(r"([0-9A-Z]{1,4}) ([A-Z][A-Z0-9 ,&/'()-]*)", head)
        return (kind, match.group(1), match.group(2)) if match else None
    return None


def group_schedules(pages: list[DocumentPage]) -> list[Schedule]:
    """Consecutive pages sharing one RATE:/RIDER: heading form one schedule."""
    groups: list[Schedule] = []
    for page in sorted(pages, key=lambda item: item.page_number):
        head = _heading(page)
        if head is None:
            continue
        last = groups[-1] if groups else None
        if (last and (last.kind, last.code, last.title) == head
                and page.page_number == last.pages[-1].page_number + 1
                and not re.search(r"^Page 1 of \d+$", page.text, re.M)):
            last.pages.append(page)
            continue
        zone = re.search(r"To Enbridge Gas Customers in the (EGD|Union North|Union South) Rate Zone\.", page.text)
        groups.append(Schedule(head[0], head[1], head[2], [page], zone.group(1) if zone else None))
    return groups


def check_complete(schedule: Schedule, edition: Edition) -> None:
    """Every 'Page n of m' page present and the closing footer matches the handbook edition."""
    numbers = []
    for page in schedule.pages:
        found = re.findall(r"^Page (\d+) of (\d+)$", page.text, re.M)
        if not found:
            raise ValueError(f"PDF page {page.page_number} has no page-of marker")
        numbers.append((int(found[-1][0]), int(found[-1][1])))
    total = numbers[0][1]
    if numbers != [(number, total) for number in range(1, total + 1)]:
        raise ValueError("schedule pages missing or out of order")
    footer = EDITION_RE.search(schedule.pages[-1].text)
    if not footer:
        raise ValueError("schedule effective-date footer missing")
    effective, implemented, order, supersedes, _ = footer.groups()
    if (_long_date(effective), _long_date(implemented), order, supersedes) != (
            edition.effective, edition.implemented, edition.order, edition.supersedes):
        raise ValueError(f"schedule footer ({order}, effective {effective}) differs from the handbook cover")


def cra_carbon_evidence(text: str, today: date) -> Optional[tuple[date, str]]:
    """CRA statement that all federal fuel charge rates are zero, naming Ontario's ended period."""
    text = re.sub(r"\s+", " ", text)
    zero = re.search(
        r"Fuel charge rates \S{1,2} Beginning " + DATE + r" On [A-Z][a-z]+ \d{1,2}, \d{4}, the Government of "
        r"Canada made regulations that cease the application of the federal fuel charge, by setting all fuel "
        r"charge rates to zero", text)
    ontario = re.search(r"The rates applied in [^.]*?\bOntario\b[^.]*? from April 1, 2019 to " + DATE, text)
    if not zero or not ontario:
        return None
    try:
        start, ended = _long_date(zero.group(1)), _long_date(ontario.group(1))
    except ValueError:
        return None
    if start > today or ended >= start:
        return None
    return start, (f"Canada Revenue Agency fuel charge rates: beginning {_human(start)} all federal fuel charge "
                   f"rates are zero; the Ontario rates applied until {_human(ended)}.")


class EnbridgeGasScraper(BaseScraper):
    """Scrape Enbridge Gas rates for Ontario from the OEB-approved rate handbook."""

    def __init__(self):
        super().__init__(utility_name="Enbridge Gas", province="ON")
        self.unmodelled_classes: list[str] = []
        self.rejected_classes: list[str] = []

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for Enbridge Gas")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Parse the current handbook (discovered from the rate pages) plus CRA carbon evidence."""
        from scrapers.utils.parsing import parse_html

        handbook_url = self._discover_handbook()
        try:
            pages = extract_handbook_pages(self.fetch_bytes(handbook_url))
        except Exception as exc:
            self.logger.warning("Enbridge Gas rate handbook unavailable: %s", exc)
            return None
        try:
            soup = parse_html(self.fetch_page(CRA_URL))
            cra_text = (soup.find("main") or soup).get_text(" ", strip=True)
        except Exception as exc:
            self.logger.warning("CRA fuel charge page unavailable: %s", exc)
            cra_text = ""
        records = self.parse_documents(pages, cra_text, source_url=handbook_url)
        return self.mark_live_parsed(records) if records else None

    def _discover_handbook(self) -> str:
        from scrapers.utils.parsing import find_pdf_links, parse_html

        for url in DISCOVERY_URLS:
            try:
                links = find_pdf_links(parse_html(self.fetch_page(url)), ["rate-handbook"], url)
            except Exception as exc:
                self.logger.warning("Enbridge Gas discovery page unavailable (%s): %s", url, exc)
                continue
            for link in links:
                parts = urlsplit(link)
                official = parts.netloc == "enbridgegas.com" or parts.netloc.endswith(".enbridgegas.com")
                if official and parts.scheme == "https" and parts.path.lower().endswith("/rate-handbook.pdf"):
                    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        self.logger.warning("Enbridge Gas handbook link not discovered; using the known handbook URL")
        return HANDBOOK_URL

    # ── Parsing ──────────────────────────────────────────────

    def parse_documents(self, pages: list[DocumentPage], cra_text: str, today: Optional[date] = None,
                        source_url: str = HANDBOOK_URL) -> list[TariffRecord]:
        """Build every modelled class from handbook pages; each class fails closed on its own."""
        today = today or datetime.now(timezone.utc).date()
        self.unmodelled_classes, self.rejected_classes = [], []
        try:
            edition = self._edition(pages, today)
        except ValueError as exc:
            self.logger.warning("Enbridge Gas handbook edition rejected: %s", exc)
            return []
        evidence = cra_carbon_evidence(cra_text, today)
        if evidence is None:
            self.logger.warning("Enbridge Gas: CRA zero federal fuel charge evidence missing; nothing published live")
            return []
        schedules = group_schedules(pages)
        try:
            carbon = self._rider_j(schedules, edition)
            self._riders_without_amounts(schedules, edition)
        except ValueError as exc:
            self.logger.warning("Enbridge Gas riders rejected: %s", exc)
            return []
        try:
            rider_c = self._rider_c(schedules, edition)
        except ValueError as exc:
            self.logger.warning("Enbridge Gas Rider C unusable: %s", exc)
            rider_c = None
        try:
            rider_i = self._rider_i(schedules, edition)
        except ValueError as exc:
            self.logger.warning("Enbridge Gas Rider I unusable: %s", exc)
            rider_i = None
        note = (f"Rider J prints a 0.0000 ¢/m³ federal carbon charge ('if applicable'). {evidence[1]}")
        ctx = _Context(edition, source_url, today, carbon, note, rider_c, rider_i)

        found: dict[tuple[str, str], list[Schedule]] = {}
        for schedule in schedules:
            if schedule.kind == "RATE" and schedule.zone:
                found.setdefault((schedule.zone, schedule.code), []).append(schedule)
        modelled = {(spec.zone, spec.rate) for spec in CLASS_SPECS}
        for key, matches in found.items():
            if key not in modelled:
                reason = EXCLUDED_SCHEDULES.get(key, "outside the agreed building-service scope")
                self.unmodelled_classes.append(f"{key[0]} Rate {key[1]} {matches[0].title}: {reason}")

        records: list[TariffRecord] = []
        for spec in CLASS_SPECS:
            matches = found.get((spec.zone, spec.rate), [])
            try:
                if len(matches) != 1:
                    raise ValueError("schedule missing" if not matches else "schedule printed more than once")
                schedule = matches[0]
                if schedule.title != spec.title:
                    raise ValueError(f"schedule retitled {schedule.title!r}")
                check_complete(schedule, edition)
                records.extend(getattr(self, f"_build_{spec.builder}")(spec, schedule, ctx))
            except ValueError as exc:
                self.rejected_classes.append(f"{spec.zone} Rate {spec.rate}: {exc}")
                self.logger.warning("Enbridge Gas %s Rate %s not parsed live: %s", spec.zone, spec.rate, exc)
        return records

    @staticmethod
    def _edition(pages: list[DocumentPage], today: date) -> Edition:
        cover = next((page for page in pages if "ENBRIDGE GAS INC." in page.text and "RATE HANDBOOK" in page.text
                      and "INDEX" in page.text), None)
        match = EDITION_RE.search(cover.text) if cover else None
        if not match:
            raise ValueError("handbook cover edition (effective date / OEB order) missing")
        effective, implemented, order, supersedes, superseded = match.groups()
        edition = Edition(_long_date(effective), _long_date(implemented), order, supersedes, _long_date(superseded))
        if edition.effective > today or edition.implemented > today:
            raise ValueError(f"handbook effective {effective} is in the future")
        if edition.superseded_effective >= edition.effective:
            raise ValueError("superseded edition is not older than the current edition")
        return edition

    @staticmethod
    def _rider(schedules: list[Schedule], letter: str, title: str, edition: Edition) -> list[DocumentPage]:
        matches = [item for item in schedules if item.kind == "RIDER" and item.code == letter]
        if len(matches) != 1 or matches[0].title != title:
            raise ValueError(f"Rider {letter} ({title}) missing, duplicated or retitled")
        check_complete(matches[0], edition)
        return matches[0].pages

    def _rider_j(self, schedules: list[Schedule], edition: Edition) -> dict:
        pages = self._rider(schedules, "J", "CARBON CHARGES", edition)
        if "This rider is applicable to all Gas delivered or transported." not in pages[0].text:
            raise ValueError("Rider J applicability changed")
        rows: dict[tuple[str, str], tuple[Decimal, Decimal, int]] = {}
        for page in pages:
            if not re.search(r"Federal Facility\nCarbon Carbon\nCharge Charge\n\(if applicable\)\n¢/m³ ¢/m³",
                             page.text):
                raise ValueError(f"Rider J column headings or ¢/m³ units changed on PDF page {page.page_number}")
            zone = None
            for line in page.text.split("\n"):
                if line == "EGD Rate Zone":
                    zone = "EGD"
                elif line in ("Union North Rate Class", "Union South Rate Class"):
                    zone = line[:-len(" Rate Class")]
                elif line.startswith("$/GJ"):
                    zone = None
                match = re.fullmatch(r"Rate ([0-9A-Z]+) (\d+\.\d{4}) (\d+\.\d{4})", line)
                if match and zone:
                    rows[(zone, match.group(1))] = (_dec(match.group(2)), _dec(match.group(3)), page.page_number)
        if not rows:
            raise ValueError("Rider J rate rows missing")
        return rows

    def _riders_without_amounts(self, schedules: list[Schedule], edition: Edition) -> None:
        """Riders D and E currently print no amounts; any amount would be an unmodelled charge."""
        for letter, title in (("D", "DEFERRAL AND VARIANCE ACCOUNT CLEARANCE"), ("E", "REVENUE ADJUSTMENT")):
            for page in self._rider(schedules, letter, title, edition):
                body = page.text.split("\nEffective ")[0]
                if re.search(r"\d\.\d{2,}", body):
                    raise ValueError(f"Rider {letter} now prints amounts on PDF page {page.page_number}")

    def _rider_c(self, schedules: list[Schedule], edition: Edition) -> RiderC:
        pages = self._rider(schedules, "C", "GAS COST ADJUSTMENT", edition)
        if len(pages) != 3:
            raise ValueError("Rider C is not the expected three-page schedule")
        first, egd_page, union_page = pages
        period = re.search(r"This rider is applicable to all gas sold or delivered during the period of " + DATE
                           + r" to " + DATE + r"\.", first.text)
        headings = ("Western Ontario Dawn\nSales Transportation Transportation Transportation\n"
                    "Service Service Service Service\n( ¢/m³ ) ( ¢/m³ ) ( ¢/m³ ) ( ¢/m³ )",
                    "Union North West Union North East\nBundled Bundled\nSales Transportation Sales Transportation",
                    "Union South Rate Class")
        if not period or not all(heading in first.text for heading in headings):
            raise ValueError("Rider C period or column headings missing")
        totals: dict[tuple[str, str], list[Optional[Decimal]]] = {}
        zone = None
        for line in first.text.split("\n"):
            if line == "EGD Rate Zone":
                zone = "EGD"
            elif line in ("Union North Rate Class", "Union South Rate Class"):
                zone = line[:-len(" Rate Class")]
            match = re.fullmatch(r"Rate ([0-9A-Z]+)((?: (?:\(\d+\.\d{4}\)|\d+\.\d{4}|-))+)", line)
            if match and zone:
                totals[(zone, match.group(1))] = [_token(value) for value in match.group(2).split()]

        rows: dict[tuple[str, str], dict] = {}
        egd = re.compile(r"^Rate (\d+) Gas Supply Commodity Charge " + TOKEN + r"\nGas Supply Transportation Charge "
                         + TOKEN + " " + TOKEN + r"\nGas Supply Load Balancing Charge " + " ".join([TOKEN] * 4)
                         + r"\nTotal " + " ".join([TOKEN] * 4) + "$", re.M)
        for match in egd.finditer(egd_page.text):
            code, *values = match.groups()
            commodity, transport, western_transport, *rest = [_token(value) for value in values]
            balancing, total = rest[:4], rest[4:]
            consistent = (totals.get(("EGD", code)) == total
                          and _add(commodity, transport, balancing[0]) == total[0]
                          and _add(western_transport, balancing[1]) == total[1]
                          and balancing[2:] == total[2:])
            if not consistent:
                self.logger.warning("Rider C EGD Rate %s breakdown does not reconcile", code)
                continue
            rows[("EGD", code)] = {
                "total": total[0], "page": egd_page.page_number, "pages": f"{first.page_number}-{egd_page.page_number}",
                "note": (f"Sales-service total {total[0]} ¢/m³ = gas supply commodity {commodity} + transportation "
                         f"{transport} + load balancing {balancing[0]} ¢/m³. Direct-purchase customers pay the "
                         f"Western ({total[1]}), Ontario ({total[2]}) or Dawn ({total[3]}) transportation-service "
                         "amount instead.")}
        union = re.compile(r"^Rate (\d+) Gas Supply Commodity Charge " + TOKEN + "(?: " + TOKEN + r")?\n"
                           r"Gas Supply Transportation Charge " + " ".join([TOKEN] * 4) + r"\nTotal "
                           + " ".join([TOKEN] * 4) + "$", re.M)
        for match in union.finditer(union_page.text):
            code, *values = match.groups()
            west_supply, east_supply = _token(values[0]), _token(values[1]) if values[1] else None
            transport = [_token(value) for value in values[2:6]]
            total = [_token(value) for value in values[6:10]]
            consistent = (totals.get(("Union North", code)) == total
                          and _add(west_supply, transport[0]) == total[0] and transport[1] == total[1]
                          and _add(east_supply, transport[2]) == total[2] and transport[3] == total[3])
            if not consistent:
                self.logger.warning("Rider C Union North Rate %s breakdown does not reconcile", code)
                continue
            for zone_name, supply, part, sales, bundled in (
                    ("Union North West", west_supply, transport[0], total[0], total[1]),
                    ("Union North East", east_supply, transport[2], total[2], total[3])):
                rows[(zone_name, code)] = {
                    "total": sales, "page": union_page.page_number,
                    "pages": f"{first.page_number} and {union_page.page_number}",
                    "note": (f"Sales-service total {sales} ¢/m³ = gas supply commodity {supply} + transportation "
                             f"{part} ¢/m³. Bundled-transportation (marketer) customers pay {bundled} ¢/m³ instead.")}
        for code, value in re.findall(r"^Rate (M\d+) Gas Supply Commodity Charge " + TOKEN + "$",
                                      union_page.text, re.M):
            total = _token(value)
            if totals.get(("Union South", code)) != [total]:
                self.logger.warning("Rider C Union South Rate %s breakdown does not reconcile", code)
                continue
            rows[("Union South", code)] = {
                "total": total, "page": union_page.page_number,
                "pages": f"{first.page_number} and {union_page.page_number}",
                "note": f"Sales-service gas supply commodity adjustment {total} ¢/m³; not charged with marketer supply."}
        return RiderC(_long_date(period.group(1)), _long_date(period.group(2)), rows)

    def _rider_i(self, schedules: list[Schedule], edition: Edition) -> tuple[Decimal, Decimal, int]:
        pages = self._rider(schedules, "I", "SYSTEM EXPANSION AND TEMPORARY CONNECTION SURCHARGES", edition)
        text = pages[0].text
        ses = re.search(r"^System Expansion Surcharge \(SES\) " + CENTS + r" ¢/m³$", text, re.M)
        tcs = re.search(r"^Temporary Connection Surcharge \(TCS\) " + CENTS + r" ¢/m³$", text, re.M)
        flat = _flat(pages[:1])
        if not ses or not tcs or "must be no more than 50,000 m³" not in flat or "term of up to 40 years" not in flat:
            raise ValueError("Rider I surcharges or applicability terms missing")
        return _dec(ses.group(1)), _dec(tcs.group(1)), pages[0].page_number

    # ── Row helpers ──────────────────────────────────────────

    @staticmethod
    def _rates_section(schedule: Schedule) -> tuple[int, str]:
        page = schedule.pages[0]
        start = page.text.find("MONTHLY RATES AND CHARGES\n")
        end = page.text.find("\nRate Riders\n", start)
        if start < 0 or end < 0:
            raise ValueError("monthly rates section missing")
        return page.page_number, page.text[start:end]

    @staticmethod
    def _value(section: str, label: str) -> Decimal:
        match = re.search("^" + re.escape(label) + " " + CENTS + " ¢/m³$", section, re.M)
        if not match:
            raise ValueError(f"'{label}' row missing, garbled or not in ¢/m³")
        return _dec(match.group(1))

    @staticmethod
    def _pair(section: str, label: str) -> tuple[Decimal, Decimal]:
        if "Union Union\nNorth West North East" not in section:
            raise ValueError("Union North West / North East column headings missing")
        match = re.search("^" + re.escape(label) + " " + CENTS + "(?: ¢/m³)? " + CENTS + " ¢/m³$", section, re.M)
        if not match:
            raise ValueError(f"'{label}' zone row missing, garbled or not in ¢/m³")
        return _dec(match.group(1)), _dec(match.group(2))

    @staticmethod
    def _blocks(section: str, heading: str) -> list[tuple[str, Decimal, Optional[Decimal]]]:
        """Monthly volume blocks under a heading: first, next…, all over (cumulative bound must reconcile)."""
        lines = section.split("\n")
        if heading not in lines:
            raise ValueError(f"'{heading}' heading missing")
        blocks: list[tuple[str, Decimal, Optional[Decimal]]] = []
        bound = Decimal(0)
        for line in lines[lines.index(heading) + 1:]:
            match = re.fullmatch(r"For (the first|the next|all over) ([\d,]+) m³ per month " + CENTS + " ¢/m³", line)
            if not match:
                break
            kind, size, value = match.group(1), _dec(match.group(2)), _dec(match.group(3))
            if kind == "all over":
                if not blocks or size != bound:
                    raise ValueError(f"'{heading}' final block does not start at the cumulative bound")
                blocks.append((f"Over {size:,} m³", value, None))
                break
            if (kind == "the first") != (not blocks):
                raise ValueError(f"'{heading}' block order changed")
            bound += size
            blocks.append((f"{kind[4:].capitalize()} {size:,} m³", value, bound))
        if len(blocks) < 2 or blocks[-1][2] is not None:
            raise ValueError(f"'{heading}' blocks incomplete, garbled or not in ¢/m³")
        return blocks

    @staticmethod
    def _customer_charge(schedule: Schedule, section: str) -> tuple[Decimal, Optional[str]]:
        match = re.search(r"^Monthly Customer Charge( \(1\))? \$([\d,]+\.\d{2})$", section, re.M)
        if not match:
            raise ValueError("Monthly Customer Charge row missing or changed")
        if not match.group(1):
            return _dec(match.group(2)), None
        if ("(1) Aggregated within the Monthly Customer Charge is the amount of one dollar per month in accordance "
                "with Rider K") not in _flat(schedule.pages):
            raise ValueError("Rider K customer-charge footnote missing")
        return _dec(match.group(2)), ("Includes the one dollar per month Rider K amount (Bill 32 and Ontario "
                                      "Regulation 24/19), as printed; not a separate charge.")

    @staticmethod
    def _riders_listed(schedule: Schedule) -> set[str]:
        return set(re.findall(r"^Rider ([A-Z]) - ", schedule.pages[0].text, re.M))

    def _maker(self, ctx: _Context, spec: ClassSpec):
        def make(kind: str, name: str, value: Optional[float], unit: str, page: int, **extra) -> RateComponent:
            extra.setdefault("effective_date", ctx.edition.effective.isoformat())
            extra.setdefault("source_detail", f"Rate Handbook PDF page {page}; {spec.name}")
            return RateComponent(kind, name, value, unit, source_url=ctx.url, **extra)
        return make

    @staticmethod
    def _tiers(make, blocks, kind: str, name: str, unit: str, page: int, tier_unit: str, notes: str) -> list:
        return [make(kind, f"{name} — {label}", _dollars(value), unit, page, tier_number=number,
                     tier_threshold=float(bound) if bound is not None else None,
                     tier_unit=tier_unit if bound is not None else None, notes=notes)
                for number, (label, value, bound) in enumerate(blocks, 1)]

    def _supply(self, make, page: int, zone: str, values: dict) -> list[RateComponent]:
        comps = []
        if "transport" in values:
            comps.append(make("transmission", "Gas Supply Transportation Charge", _dollars(values["transport"]),
                              "$/m³", page, notes="Printed '(if applicable)': transportation of gas supply to "
                                                  "Enbridge's system, billed with Enbridge system gas."))
        if "dawn" in values:
            comps.append(make("transmission", "Gas Supply Transportation Dawn Charge", _dollars(values["dawn"]),
                              "$/m³", page, sub_component="conditional",
                              notes="Conditional: printed '(if applicable)'; billed only where Enbridge transports a "
                                    "direct-purchase (marketer) customer's gas from the Dawn hub, instead of the Gas "
                                    "Supply Transportation Charge. Not part of system-gas service."))
        if "storage" in values:
            comps.append(make("other", "Gas Supply Storage Charge" if zone != "Union South" else "Storage Charge",
                              _dollars(values["storage"]), "$/m³", page,
                              notes="Printed '(if applicable)': billed with Enbridge system gas."))
        comps.append(make("commodity", "Gas Supply Commodity Charge", _dollars(values["commodity"]), "$/m³", page,
                          notes="Enbridge system-gas (sales service) price for the quarter; printed '(if applicable)' "
                                "and charged only to customers buying gas from Enbridge. Marketer contract prices are "
                                "not included."))
        return comps

    def _rider_components(self, spec: ClassSpec, schedule: Schedule, ctx: _Context, make,
                          rider_zone: str) -> tuple[list[RateComponent], list[str]]:
        letters = self._riders_listed(schedule)
        if not {"C", "J"} <= letters:
            raise ValueError("Rider C or J no longer listed for this rate")
        comps: list[RateComponent] = []
        notes: list[str] = []
        rider_c = ctx.rider_c
        if rider_c is None:
            raise ValueError("Rider C (Gas Cost Adjustment) could not be parsed")
        row = rider_c.rows.get((rider_zone, spec.rate))
        if row is None:
            raise ValueError("Rider C row missing or does not reconcile")
        if row["total"] is None:
            notes.append("Rider C prints no gas cost adjustment ('-') for this rate.")
        elif rider_c.start <= ctx.today <= rider_c.end:
            comps.append(make("rider", "Gas Cost Adjustment (Rider C)", _dollars(row["total"]), "$/m³", row["page"],
                              effective_date=rider_c.start.isoformat(), end_date=rider_c.end.isoformat(),
                              source_detail=f"Rate Handbook PDF pages {row['pages']}; Rider C Gas Cost Adjustment",
                              notes=row["note"]))
        else:
            notes.append(f"Rider C applies only from {_human(rider_c.start)} to {_human(rider_c.end)}; no current "
                         "gas cost adjustment is included.")
        if "I" in letters:
            if ctx.rider_i is None:
                raise ValueError("Rider I (system expansion surcharges) could not be parsed")
            ses, tcs, page = ctx.rider_i
            detail = f"Rate Handbook PDF page {page}; Rider I System Expansion and Temporary Connection Surcharges"
            comps += [
                make("rider", "System Expansion Surcharge (Rider I)", _dollars(ses), "$/m³", page,
                     sub_component="conditional", source_detail=detail,
                     notes="Conditional: only at Points of Consumption in the Community Expansion Projects listed in "
                           "Rider I, for the project term (up to 40 years). SES and TCS are alternatives."),
                make("rider", "Temporary Connection Surcharge (Rider I)", _dollars(tcs), "$/m³", page,
                     sub_component="conditional", source_detail=detail,
                     notes="Conditional: only in Temporary Connection Surcharge project areas published by Enbridge "
                           "(term up to 40 years, or a contribution in aid of construction instead). SES and TCS "
                           "are alternatives."),
            ]
        carbon = ctx.carbon.get((spec.zone, spec.rate))
        if carbon is None:
            raise ValueError("Rider J carbon row missing")
        federal, facility, page = carbon
        if federal != 0:
            raise ValueError("Rider J federal carbon charge is no longer zero")
        detail = f"Rate Handbook PDF page {page}; Rider J Carbon Charges"
        comps += [
            make("carbon", "Federal Carbon Charge", 0.0, "$/m³", page, source_detail=detail, notes=ctx.carbon_note),
            make("carbon", "Facility Carbon Charge", _dollars(facility), "$/m³", page, source_detail=detail,
                 notes="Rider J facility carbon charge on all gas delivered or transported; separate from the "
                       "delivery charges."),
        ]
        optional = {"L": "Optional Rider L (voluntary RNG program, opt-in monthly charge) is not included.",
                    "M": "Rider M (credit only in the Markham hydrogen-blending pilot area) is not included.",
                    "O": "Rider O adjustments to negotiated interruptible rates are not included."}
        notes += [text for letter, text in optional.items() if letter in letters]
        return comps, notes

    def _record(self, spec: ClassSpec, schedule: Schedule, ctx: _Context, zone_label: str, code: str,
                comps: list[RateComponent], structure: str, notes: list[str]) -> TariffRecord:
        text = schedule.pages[0].text
        found = re.search(r"\nAPPLICABILITY\s+(.*?)\s+(?:CHARACTER OF SERVICE|MONTHLY RATES AND CHARGES)\n", text, re.S)
        applicability = " ".join(found.group(1).split()) if found else ""
        match = re.search(spec.applicability, applicability)
        if not match:
            raise ValueError("applicability text missing or changed")
        groups = match.groupdict()
        usage_min = float(_dec(groups["min"])) if groups.get("min") else None
        usage_max = float(_dec(groups["max"])) if groups.get("max") else None
        edition = ctx.edition
        header = (f"Enbridge Gas Rate Handbook approved by OEB Order {edition.order}, effective "
                  f"{_human(edition.effective)} (supersedes {edition.supersedes} of "
                  f"{_human(edition.superseded_effective)}). Prices printed in ¢/m³ are stored in $/m³.")
        footer = ("Gas supply components are Enbridge system-gas (sales service) charges; customers buying gas from "
                  "a marketer pay the marketer's price instead. Riders D and E print no current amounts. HST is not "
                  "included. Regulated by the Ontario Energy Board.")
        first, last = schedule.pages[0].page_number, schedule.pages[-1].page_number
        pages = f"page {first}" if first == last else f"pages {first}-{last}"
        return TariffRecord(
            utility_name="Enbridge Gas", province="ON", utility_type="gas",
            tariff_name=f"{spec.name} ({zone_label})", tariff_code=code, customer_class=spec.customer_class,
            sub_class=spec.sub_class, eligibility=f"{zone_label}: {applicability}",
            usage_min=usage_min, usage_max=usage_max,
            usage_unit="m³/year" if usage_min is not None or usage_max is not None else None,
            rate_structure=structure, pricing_method="regulated",
            effective_date=max(component.effective_date or "" for component in comps), source_url=ctx.url,
            source_page=f"Rate Handbook PDF {pages}; {spec.name}", confidence="high",
            notes=" ".join([header, *notes, footer]), components=comps,
        )

    # ── Class builders ───────────────────────────────────────

    def _build_general(self, spec: ClassSpec, schedule: Schedule, ctx: _Context) -> list[TariffRecord]:
        make = self._maker(ctx, spec)
        page, rates = self._rates_section(schedule)
        fixed, fixed_note = self._customer_charge(schedule, rates)
        blocks = self._blocks(rates, "Delivery Charge")
        if spec.zone == "EGD":
            variants = [("EGD Rate Zone", f"EGD-{spec.rate}", "EGD", {
                "transport": self._value(rates, "Gas Supply Transportation Charge (if applicable)"),
                "dawn": self._value(rates, "Gas Supply Transportation Dawn Charge (if applicable)"),
                "commodity": self._value(rates, "Gas Supply Commodity Charge (if applicable)")})]
        elif spec.zone == "Union North":
            storage = self._pair(rates, "Gas Supply Storage Charge (if applicable)")
            transport = self._pair(rates, "Gas Supply Transportation Charge (if applicable)")
            commodity = self._pair(rates, "Gas Supply Commodity Charge (if applicable)")
            variants = [(zone, f"{prefix}-{spec.rate}", zone, {
                "storage": storage[index], "transport": transport[index], "commodity": commodity[index]})
                for index, (zone, prefix) in enumerate((("Union North West", "UNW"), ("Union North East", "UNE")))]
        else:
            variants = [("Union South", f"US-{spec.rate}", "Union South", {
                "storage": self._value(rates, "Storage Charge (if applicable)"),
                "commodity": self._value(rates, "Gas Supply Commodity Charge (if applicable)")})]
        records = []
        for zone_label, code, rider_zone, supply in variants:
            comps = [make("fixed", "Monthly Customer Charge", float(fixed), "$/month", page, notes=fixed_note)]
            comps += self._tiers(make, blocks, "delivery", "Delivery Charge", "$/m³", page, "m³/month",
                                 "Monthly volume block; the threshold is the cumulative upper bound in m³ per month.")
            comps += self._supply(make, page, spec.zone, supply)
            riders, notes = self._rider_components(spec, schedule, ctx, make, rider_zone)
            records.append(self._record(spec, schedule, ctx, zone_label, code, comps + riders, "tiered", notes))
        return records

    def _contract_notes(self, schedule: Schedule) -> list[str]:
        flat = _flat(schedule.pages)
        notes = ["Requires a Service Contract with Enbridge."]
        if "represent maximum prices for service" in flat:
            notes.append("The printed rates (excluding gas supply charges) are maximum prices; multi-year prices may "
                         "be negotiated.")
        notice = re.search(r"upon the Company issuing a notice not less than (\d+) hours prior to the time at which "
                           r"such interruption", flat)
        if notice and "INTERRUPTIBLE" in schedule.title:
            notes.append(f"Service may be interrupted on at least {notice.group(1)} hours' notice.")
        minimum = re.search(r"Per cubic metre of Annual Volume Deficiency \(See Terms and Conditions of Service\) "
                            + CENTS + " ¢/m³", flat)
        if minimum:
            notes.append(f"Minimum bill: {minimum.group(1)} ¢/m³ of annual volume deficiency (conditional, not a "
                         "component).")
        if "The Monthly Minimum Bill shall be the Monthly Customer Charge plus the monthly Contract Demand" in flat:
            notes.append("Monthly minimum bill: customer charge plus the monthly contract demand charge.")
        credit = re.search(r"Per cubic metre of Daily Contracted Quantity from December to March for (\d+) hours of "
                           r"notice \$(\d+\.\d{2}) /m³", flat)
        if credit:
            notes.append(f"Curtailment credit: ${credit.group(2)} per m³ of Daily Contracted Quantity, December to "
                         f"March, for {credit.group(1)} hours of notice (conditional, not a component).")
        if "The Company may negotiate rates for Interruptible service where the Customer is located in an area of " \
                "constraint" in flat:
            notes.append("Interruptible rates may be negotiated (OEB-approved) where the customer is in a "
                         "constrained area for an integrated resource planning alternative.")
        return notes

    def _build_egd_contract(self, spec: ClassSpec, schedule: Schedule, ctx: _Context) -> list[TariffRecord]:
        make = self._maker(ctx, spec)
        page, rates = self._rates_section(schedule)
        fixed, fixed_note = self._customer_charge(schedule, rates)
        demand = self._value(rates, "Per cubic metre of Contract Demand")
        single = re.search(r"^Per cubic metre of Gas delivered " + CENTS + " ¢/m³$", rates, re.M)
        balancing = self._value(rates, "Gas Supply Load Balancing Charge")
        supply = {"transport": self._value(rates, "Gas Supply Transportation Charge (if applicable)"),
                  "dawn": self._value(rates, "Gas Supply Transportation Dawn Charge (if applicable)"),
                  "commodity": self._value(rates, "Gas Supply Commodity Charge (if applicable)")}
        comps = [
            make("fixed", "Monthly Customer Charge", float(fixed), "$/month", page, notes=fixed_note),
            make("demand", "Delivery Charge — Contract Demand", _dollars(demand), "$/m³/month", page,
                 demand_unit="m³/day Contract Demand",
                 notes="Monthly charge per m³ of Contract Demand (the contracted maximum daily volume)."),
        ]
        if single:
            comps.append(make("delivery", "Delivery Charge — Gas delivered", _dollars(_dec(single.group(1))), "$/m³",
                              page))
        else:
            comps += self._tiers(make, self._blocks(rates, "Per cubic metre of Gas delivered"), "delivery",
                                 "Delivery Charge — Gas delivered", "$/m³", page, "m³/month",
                                 "Monthly volume block; the threshold is the cumulative upper bound in m³ per month.")
        comps.append(make("delivery", "Gas Supply Load Balancing Charge", _dollars(balancing), "$/m³", page,
                          notes="Applies to all gas delivered under this rate."))
        comps += self._supply(make, page, spec.zone, supply)
        riders, notes = self._rider_components(spec, schedule, ctx, make, "EGD")
        return [self._record(spec, schedule, ctx, "EGD Rate Zone", f"EGD-{spec.rate}", comps + riders, "demand",
                             self._contract_notes(schedule) + notes)]

    def _build_un_contract(self, spec: ClassSpec, schedule: Schedule, ctx: _Context) -> list[TariffRecord]:
        make = self._maker(ctx, spec)
        page, rates = self._rates_section(schedule)
        fixed, fixed_note = self._customer_charge(schedule, rates)
        if spec.rate == "20":
            demand = self._blocks(rates, "Per cubic metre of Contract Demand")
            delivered = self._blocks(rates, "Per cubic metre of Gas delivered")
        else:
            demand = [("All Contract Demand", self._value(rates, "Per cubic metre of Contract Demand"), None)]
            delivered = [("All gas delivered", self._value(rates, "Per cubic metre of all Gas delivered"), None)]
        transport_demand = self._pair(rates, "Gas Supply Transportation Demand Charge (if applicable)")
        charge_one = self._pair(rates, "Charge 1")
        limit = re.search(r"Charge 1 applies for all gas volumes delivered in the billing month up to the volume "
                          r"represented by the Contract Demand multiplied by the number of days in the billing month "
                          r"multiplied by (\d\.\d+)\.", " ".join(rates.split()))
        if not re.search(r"^Charge 2 - ¢/m³ - ¢/m³$", rates, re.M) or not limit:
            raise ValueError("transportation Charge 1/Charge 2 rule changed")
        commodity = self._pair(rates, "Gas Supply Commodity Charge (if applicable)")
        records = []
        for index, (zone, prefix) in enumerate((("Union North West", "UNW"), ("Union North East", "UNE"))):
            comps = [make("fixed", "Monthly Customer Charge", float(fixed), "$/month", page, notes=fixed_note)]
            if len(demand) == 1:
                comps.append(make("demand", "Delivery Charge — Contract Demand", _dollars(demand[0][1]),
                                  "$/m³/month", page, demand_unit="m³/day Contract Demand",
                                  notes="Monthly charge per m³ of Contract Demand."))
                comps.append(make("delivery", "Delivery Charge — Gas delivered", _dollars(delivered[0][1]), "$/m³",
                                  page))
            else:
                comps += self._tiers(make, demand, "demand", "Delivery Charge — Contract Demand", "$/m³/month", page,
                                     "m³/day Contract Demand",
                                     "Monthly charge per m³ of Contract Demand; the threshold is the cumulative upper "
                                     "bound of contract demand.")
                comps += self._tiers(make, delivered, "delivery", "Delivery Charge — Gas delivered", "$/m³", page,
                                     "m³/month", "Monthly volume block; the threshold is the cumulative upper bound "
                                                 "in m³ per month.")
            comps += [
                make("transmission", "Gas Supply Transportation Demand Charge", _dollars(transport_demand[index]),
                     "$/m³/month", page, demand_unit="m³/day Contract Demand",
                     notes="Printed '(if applicable)': monthly charge per m³ of Contract Demand, billed with Enbridge "
                           "system gas."),
                make("transmission", "Gas Supply Transportation Charge (Charge 1)", _dollars(charge_one[index]),
                     "$/m³", page,
                     notes=f"Printed '(if applicable)'. Applies to monthly volumes up to Contract Demand × days in the "
                           f"billing month × {limit.group(1)}; Charge 2 for additional volumes prints '-'."),
                make("commodity", "Gas Supply Commodity Charge", _dollars(commodity[index]), "$/m³", page,
                     notes="Enbridge system-gas (sales service) price for the quarter; printed '(if applicable)'. "
                           "Adjusted for heat content above or below 37.89 MJ/m³ as printed. Marketer prices are not "
                           "included."),
            ]
            riders, notes = self._rider_components(spec, schedule, ctx, make, zone)
            records.append(self._record(spec, schedule, ctx, zone, f"{prefix}-{spec.rate}", comps + riders, "demand",
                                        self._contract_notes(schedule) + notes))
        return records

    def _build_un_interruptible(self, spec: ClassSpec, schedule: Schedule, ctx: _Context) -> list[TariffRecord]:
        make = self._maker(ctx, spec)
        page, rates = self._rates_section(schedule)
        fixed, fixed_note = self._customer_charge(schedule, rates)
        flat = " ".join(rates.split())
        cap = re.search(r"A Delivery Price for all volumes delivered to the Customer to be negotiated between the "
                        r"Company and the Customer and the average price during the period in which these rates "
                        r"remain in effect shall not exceed: " + CENTS + " ¢/m³", flat)
        supply = re.search(r"Gas Supply Charge \(All Union North rate zones\) Per cubic metre of Interruptible Gas "
                           r"delivered Minimum \(if applicable\) " + CENTS + r" ¢/m³ Maximum \(if applicable\) "
                           + CENTS + " ¢/m³", flat)
        if not cap or not supply:
            raise ValueError("negotiated delivery cap or gas supply range missing")
        comps = [
            make("fixed", "Monthly Customer Charge", float(fixed), "$/month", page, notes=fixed_note),
            make("delivery", "Delivery Charge (negotiated)", None, "$/m³", page, sub_component="conditional",
                 notes=f"Conditional: negotiated per contract; the average price over the period these rates are in "
                       f"effect may not exceed {cap.group(1)} ¢/m³. No single price is published."),
            make("commodity", "Gas Supply Charge (negotiated)", None, "$/m³", page, sub_component="conditional",
                 notes=f"Conditional: negotiated interruptible gas supply price between {supply.group(1)} and "
                       f"{supply.group(2)} ¢/m³ (all Union North zones). No single price is published."),
        ]
        riders, notes = self._rider_components(spec, schedule, ctx, make, "Union North West")
        east = ctx.rider_c.rows.get(("Union North East", spec.rate)) if ctx.rider_c else None
        if east is None or east["total"] is not None or any(c.component_type == "rider" for c in riders):
            raise ValueError("Rider C unexpectedly prices Rate 25")
        return [self._record(spec, schedule, ctx, "Union North", f"UN-{spec.rate}", comps + riders, "flat",
                             self._contract_notes(schedule) + notes)]

    def _build_m4(self, spec: ClassSpec, schedule: Schedule, ctx: _Context) -> list[TariffRecord]:
        make = self._maker(ctx, spec)
        page, rates = self._rates_section(schedule)
        if not re.search(r"^Monthly Customer Charge \(1\) -$", rates, re.M):
            raise ValueError("firm customer charge row changed")
        flat = _flat(schedule.pages)
        if ("Rate M4 Customers will be charged a one-time adjustment annually set at the equivalent of one dollar per "
                "month in accordance with Rider K") not in flat:
            raise ValueError("Rider K annual adjustment footnote missing")
        demand = self._blocks(rates, "Per cubic metre of Contract Demand per month")
        delivered = re.search(
            r"^Per cubic metre of Gas delivered\nFor the first ([\d,]+) m³ per month " + CENTS + r" ¢/m³\n"
            r"Next Gas delivered equal to (\d+) days use of Contract Demand " + CENTS + r" ¢/m³\n"
            r"For remainder of Gas delivered in the month " + CENTS + " ¢/m³$", rates, re.M)
        if not delivered:
            raise ValueError("delivered-gas blocks missing or changed")
        first_size, first, days, second, rest = delivered.groups()
        commodity = self._value(rates, "Gas Supply Commodity Charge (if applicable)")
        comps = self._tiers(make, demand, "demand", "Delivery Charge — Contract Demand", "$/m³/month", page,
                            "m³/day Contract Demand", "Monthly charge per m³ of Contract Demand; the threshold is the "
                                                      "cumulative upper bound of contract demand.")
        comps += [
            make("delivery", f"Delivery Charge — First {first_size} m³", _dollars(_dec(first)), "$/m³", page,
                 tier_number=1, tier_threshold=float(_dec(first_size)), tier_unit="m³/month"),
            make("delivery", f"Delivery Charge — Next {days} days use of Contract Demand", _dollars(_dec(second)),
                 "$/m³", page, tier_number=2,
                 notes=f"Block size equals {days} days' use of the Contract Demand (depends on the contract)."),
            make("delivery", "Delivery Charge — Remainder of gas delivered", _dollars(_dec(rest)), "$/m³", page,
                 tier_number=3),
            make("commodity", "Gas Supply Commodity Charge", _dollars(commodity), "$/m³", page,
                 notes="Enbridge system-gas (sales service) price for the quarter; printed '(if applicable)'. "
                       "Marketer prices are not included."),
        ]
        riders, notes = self._rider_components(spec, schedule, ctx, make, "Union South")
        extra = ["No monthly customer charge for firm service; Rider K is billed as a one-time annual adjustment "
                 "equal to one dollar per month."]
        minimum = re.search(r"equivalent to (\d+) days use of the Firm Contract Demand.*?Firm Minimum Annual Delivery "
                            r"Charge " + CENTS + " ¢/m³", flat)
        if minimum:
            extra.append(f"Firm minimum annual charge: {minimum.group(2)} ¢/m³ on any shortfall below "
                         f"{minimum.group(1)} days' use of the Contract Demand (conditional, not a component).")
        if "INTERRUPTIBLE SERVICE The price for all Interruptible Gas delivered" in flat:
            extra.append("Interruptible volumes under a combined M4 contract are priced like Rate M5 (see that record).")
        return [self._record(spec, schedule, ctx, "Union South", f"US-{spec.rate}", comps + riders, "demand",
                             self._contract_notes(schedule) + extra + notes)]

    def _build_m5(self, spec: ClassSpec, schedule: Schedule, ctx: _Context) -> list[TariffRecord]:
        make = self._maker(ctx, spec)
        page, rates = self._rates_section(schedule)
        fixed, fixed_note = self._customer_charge(schedule, rates)
        bands = re.findall(r"^([\d,]+) m³ and (less than|equal to or less than) ([\d,]+) m³ " + CENTS + " ¢/m³$",
                           rates, re.M)
        applicability = re.search(spec.applicability, _flat(schedule.pages[:1]))
        if not applicability or len(bands) < 2:
            raise ValueError("contract-demand delivery bands missing")
        lows = [_dec(band[0]) for band in bands]
        highs = [_dec(band[2]) for band in bands]
        if (lows[0] != _dec(applicability.group("low")) or highs[-1] != _dec(applicability.group("high"))
                or lows[1:] != highs[:-1] or bands[-1][1] != "equal to or less than"
                or any(band[1] != "less than" for band in bands[:-1])):
            raise ValueError("contract-demand delivery bands do not cover the eligible range")
        flat_rates = " ".join(rates.split())
        discount = re.search(r"For (\d+) days use of Contract Demand " + CENTS + r" ¢/m³ For each additional days use "
                             r"of Contract Demand up to a maximum of (\d+) days, an additional discount of " + CENTS
                             + " ¢/m³", flat_rates)
        flat = _flat(schedule.pages)
        firm = re.search(r"FIRM SERVICE The price for all Firm Gas delivered by the Company shall be determined on the "
                         r"basis of the following: Delivery Charge Per cubic metre of Contract Demand " + CENTS
                         + " ¢/m³", flat)
        if not discount or not firm:
            raise ValueError("days-use discount or firm-service demand charge missing")
        commodity = self._value(rates, "Gas Supply Commodity Charge (if applicable)")
        comps = [make("fixed", "Monthly Customer Charge", float(fixed), "$/month", page, notes=fixed_note)]
        for number, (low, kind, high, value) in enumerate(bands, 1):
            comps.append(make(
                "delivery", f"Delivery Charge — Contract Demand {low} to {high} m³", _dollars(_dec(value)), "$/m³",
                page, sub_component="conditional", tier_number=number, tier_threshold=float(_dec(high)),
                tier_unit="m³/day Contract Demand",
                notes=f"Conditional: alternative band — applies to all gas delivered when the Interruptible Contract "
                      f"Demand is at least {low} m³ and {kind} {high} m³. One band applies; bands are not added."))
        days, first, maximum, each = discount.groups()
        comps += [
            make("rebate", f"Days-Use Discount — {days} days use of Contract Demand", -_dollars(_dec(first)), "$/m³",
                 page, sub_component="conditional",
                 notes=f"Conditional: reduces the delivery charge when gas taken equals {days} days' use of the "
                       "Interruptible Contract Demand."),
            make("rebate", "Days-Use Discount — each additional day", -_dollars(_dec(each)), "$/m³", page,
                 sub_component="conditional",
                 notes=f"Conditional: further reduction per m³ for each additional day's use of Contract Demand "
                       f"beyond {days}, up to {maximum} days."),
            make("demand", "Firm Service Delivery Charge — Contract Demand", _dollars(_dec(firm.group(1))),
                 "$/m³/month", schedule.pages[-1].page_number, sub_component="conditional",
                 demand_unit="m³/day Firm Contract Demand",
                 notes="Conditional: only when firm service is combined with this interruptible contract; monthly "
                       "charge per m³ of Firm Contract Demand."),
            make("commodity", "Gas Supply Commodity Charge", _dollars(commodity), "$/m³", page,
                 notes="Enbridge system-gas (sales service) price for the quarter; printed '(if applicable)'. "
                       "Marketer prices are not included."),
        ]
        riders, notes = self._rider_components(spec, schedule, ctx, make, "Union South")
        extra = []
        minimum = re.search(r"will not be less than ([\d,]+) m³ per annum.*?Interruptible Minimum Annual Delivery "
                            r"Charge " + CENTS + " ¢/m³", flat)
        if minimum:
            extra.append(f"Interruptible minimum annual charge: {minimum.group(2)} ¢/m³ on any shortfall below the "
                         f"contracted minimum volume (at least {minimum.group(1)} m³ per year; conditional, not a "
                         "component).")
        return [self._record(spec, schedule, ctx, "Union South", f"US-{spec.rate}", comps + riders, "flat",
                             self._contract_notes(schedule) + extra + notes)]

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential — Rate 1 (Union South legacy area) ───
        records.append(TariffRecord(
            utility_name="Enbridge Gas",
            province="ON",
            utility_type="gas",
            tariff_name="Residential — Rate 1 (Union South)",
            tariff_code="Rate 1",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RATE_1["effective_date"],
            source_url=SEED_RATE_1["source_url"],
            confidence="high",
            notes=(
                "Enbridge Gas residential rate for Union South legacy service area. "
                "Gas supply (commodity) rate includes a mix of fixed and variable components. "
                "Total cost per m³ is the sum of all volumetric components."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_RATE_1["customer_charge_monthly"],
                    charge_unit="$/month",
                    notes="Fixed monthly charge regardless of gas usage",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Gas Supply Charge",
                    charge_value=SEED_RATE_1["gas_supply_rate"],
                    charge_unit="$/m³",
                    notes="Cost of the natural gas commodity — set by OEB quarterly",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Delivery to You",
                    charge_value=SEED_RATE_1["delivery_to_you_rate"],
                    charge_unit="$/m³",
                    notes="Enbridge distribution charge for delivering gas to your home",
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Transportation to Enbridge",
                    charge_value=SEED_RATE_1["transportation_rate"],
                    charge_unit="$/m³",
                    notes="Cost of transporting gas through upstream pipelines to Enbridge's system",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_RATE_1["federal_carbon_charge"],
                    charge_unit="$/m³",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Cost Adjustment Rider",
                    charge_value=SEED_RATE_1["cost_adjustment_rider"],
                    charge_unit="$/m³",
                    notes="Quarterly adjustment — can be positive or negative",
                ),
            ],
        ))

        return records
