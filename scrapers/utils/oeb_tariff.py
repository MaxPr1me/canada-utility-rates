"""
oeb_tariff.py — Parser for Ontario distributors' OEB-approved Tariff of Rates and Charges.

The OEB rate generator prints every distributor's approved tariff in one common
layout: repeated page headers (distributor, optional rate zone, "TARIFF OF RATES
AND CHARGES Effective [and Implementation] Date ...", EB case number), then one
"<NAME> SERVICE CLASSIFICATION" block per rate class with eligibility text, an
APPLICATION boilerplate and "MONTHLY RATES AND CHARGES - Delivery/Regulatory
Component" charge lines of the form ``<label> <unit> <value>``, followed by
ALLOWANCES, SPECIFIC/RETAIL SERVICE CHARGES and LOSS FACTORS sections.

All functions are pure and network-free. ``parse_tariff_pages`` turns extracted
PDF pages into a :class:`TariffSheet`; ``build_demand_records`` converts the
GS >= 50 kW, Large Use and (Hydro One) Sub Transmission load classes into
delivery-only ``TariffRecord`` objects, failing closed per classification.
``classify_classification`` tells callers which classes are residential,
GS < 50 kW energy-billed, demand-billed or excluded. Callers are responsible for
provenance stamping (``BaseScraper.mark_live_parsed``).

Hydro One Networks Inc. prints the same OEB layout with extra deviations that are
handled here: coded density-zone headings ("URBAN DENSITY - UR", "GENERAL SERVICE
DEMAND BILLED - GSd", "SUB TRANSMISSION - ST", ...) under rate-free group pages
("... SERVICE CLASSIFICATIONS"); label / bare value / label-tail wrapping; a
former-Chapleau PUC rider set; R2 Seasonal and RRRP footnote alternatives;
ST facility/meter/transformation charges; one loss-factor table keyed by class
code; and three tariffs (main area, former Peterborough, former Orillia) in one
PDF, exposed as rate zones by ``parse_tariff_zones`` (main area key ``None``).

Other distributor layouts handled (fail closed otherwise): tariff copies under a
"Proposed/Draft Tariff of Rates and Charges" cover are ignored and remaining repeated
classes must publish identical values (else rejected); "... SERVICE" headings without
"CLASSIFICATION"; labels wrapped after their value ("... $/kW 0.1765" / "(2026) -
effective until ..."); interval-metered transmission rates split by demand size and
distribution rates split by meter type (conditional alternatives); separate Line and
Transformation Connection rates; open-ended GS classes ("GREATER THAN 50 KW"). Classes
with garbled text, orphan label tails or unrecognised delivery charges are rejected.

Text extraction: ``scrapers.utils.parsing.normalize_document_text`` drops lines
that repeat more than twice on a page, which deletes genuine rider tails such as
"customers) - effective until December 31, 2026" (Hydro One GSe/GSd pages).
Prefer ``extract_tariff_pages`` (same pdfplumber settings and row joining, no
repeated-line removal). Pages from ``extract_pdf_pages`` are still accepted: a
rider whose label was visibly truncated keeps ``end_date=None`` and its class gets
a note saying the end date was not found; nothing is inferred.
"""

from __future__ import annotations

import io
import logging
import re
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Iterable, Optional, Sequence, Union

from scrapers.base import RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage

logger = logging.getLogger(__name__)

CHARGE_KINDS = (
    "service", "distribution", "rider", "transmission_network",
    "transmission_connection", "regulatory", "low_voltage", "facility", "other",
)

# Selector token for residential classes billed on a demand basis (Algoma R2).
RESIDENTIAL_DEMAND_CLASS = "RESIDENTIAL DEMAND BILLED"

DEFAULT_DEMAND_CLASSES = (
    "GENERAL SERVICE 50 TO 4,999 KW", "LARGE USE", "SUB TRANSMISSION - ST", RESIDENTIAL_DEMAND_CLASS,
)

CLASS_CATEGORIES = (
    "residential", "residential_demand", "gs_energy", "gs_demand", "large_use", "sub_transmission",
    "excluded", "other",
)

ST_LOAD_NOTE = (
    "Only the Sub Transmission load path is represented: three-phase load over 500 kW supplied from "
    "Hydro One Distribution assets at 44 kV to 13.8 kV (primary side of the local transformer). The "
    "embedded-LDC supply path of the same class is excluded (embedded distributor/wholesale service). "
    "Meter, local transformation, facility and connection charges depend on ownership and connection "
    "type; they are conditional alternatives and are never summed."
)

COMMODITY_NOTE = (
    "Delivery and regulatory charges only, from the OEB-approved Tariff of Rates and Charges. "
    "The electricity commodity is not included: demand-billed (>= 50 kW) customers are non-RPP and "
    "pay the market-based Hourly Ontario Energy Price (HOEP) plus the Global Adjustment, which are "
    "deferred to the Ontario market-rate work. Each charge is a separate component; no bill total "
    "is calculated."
)

_DATE = r"[A-Z][a-z]+\.?\s+\d{1,2}\s*,?\s*\d{4}"
_TARIFF_LINE_RE = re.compile(r"^TARIFF OF RATES AND CHARGES\b(?P<rest>.*)$")
_EFF_IMPL_RE = re.compile(rf"Effective and Implementation Date\s+(?P<d>{_DATE})")
_EFF_RE = re.compile(rf"Effective Date\s+(?P<d>{_DATE})")
_IMPL_RE = re.compile(rf"Implementation Date\s+(?P<d>{_DATE})")
_CASE_RE = re.compile(r"\bEB-\d{4}-\d{4}\b")
_PAGE_NO_RE = re.compile(r"^(?:Page\s+)?\d+\s+of\s+\d+$", re.I)
_SUPERSEDES_RE = re.compile(r"^This schedule supersedes and replaces all previously$")
_APPROVED_RE = re.compile(r"^approved schedules of Rates, Charges and Loss Factors\s*(?P<rest>.*)$")
# Footers: "Issued - <date>", "Originally Issued - <date>", "Revised - <date>", "Revised: <date>", "Issued – <date>".
_ISSUED_RE = re.compile(rf"\s*(?:(?:Originally\s+)?Issued|Revised)\s*[-–:]?\s*(?P<d>{_DATE})\s*$")
# Bare footer date: a whole last line, or after a sentence end ("... the HST. March 19, 2026").
_BARE_DATE_RE = re.compile(rf"(?:^|(?<=\.)\s+)(?P<d>{_DATE})\s*$")
_FINAL_SCHEDULE_FOOTER_RE = re.compile(r"(?:^|\s+)\d+\.\s+Final Tariff Schedule Page \d+\s*$")
_PAGE_OF_RE = re.compile(r"^(?:Page\s+)?(\d+)\s+of\s+(\d+)$", re.I)
_PROPOSED_COVER_RE = re.compile(r"\b(?:Proposed|Draft)\s+Tariff of Rates and Charges\b", re.I)
_CLASS_RE = re.compile(r"^(?P<name>\S.{1,120}?) SERVICE CLASSIFICATION\b\s*(?P<rest>.*)$")
# Heading without "CLASSIFICATION" (London: "GENERAL SERVICE 1,000 TO 4,999 KW (CO-GENERATION) SERVICE").
_SERVICE_HEADING_RE = re.compile(r"^(?P<name>[A-Z][A-Z0-9 ,.()&/\-]{2,120}?) SERVICE$")
_SERVICE_HEADING_NAME_RE = re.compile(r"GENERAL SERVICE|LARGE USE|RESIDENTIAL|STANDBY|LIGHTING|GENERATION|LOAD")
_SECTION_RE = re.compile(
    r"^(?P<name>ALLOWANCES|SPECIFIC SERVICE CHARGES|RETAIL SERVICE CHARGES|LOSS FACTORS|"
    r"SUBMETERING SERVICE CHARGES|Dry Core Transformer Charges|GROSS LOAD BILLING NOTE|"
    r"NOTES(?=\s+1\.\s|$)|(?:NOTES|Notes)(?=\s+1\)\s))\b\s*(?P<rest>.*)$"
)
# Rate-free group pages (Hydro One): "RESIDENTIAL SERVICE CLASSIFICATIONS - ...", "ACQUIRED GENERAL SERVICE CLASSIFICATIONS".
_GROUP_RE = re.compile(r"^(?P<name>[A-Z][A-Z ]*? CLASSIFICATIONS)\b\s*(?P<rest>.*)$")
_CODED_CLASS_RE = re.compile(
    r"^(?P<name>(?:[A-Z]+ )*?(?:DENSITY|BILLED|TRANSMISSION|GENERATION)(?: [A-Z]+)*? - "
    r"(?P<code>[A-Z][A-Za-z0-9]{0,4}))\**(?:\s+(?P<rest>This classification\b.*))?$"
)
_CANONICAL_CODES = {
    "UR": "UR", "R1": "R1", "R2": "R2", "AUR": "AUR", "AR": "AR", "ST": "ST", "DGEN": "DGen",
    "UGE": "UGe", "GSE": "GSe", "AUGE": "AUGe", "AGSE": "AGSe",
    "UGD": "UGd", "GSD": "GSd", "AUGD": "AUGd", "AGSD": "AGSd",
}
_RESIDENTIAL_CODES = {"UR", "R1", "R2", "AUR", "AR"}
_GS_ENERGY_CODES = {"UGE", "GSE", "AUGE", "AGSE"}
_GS_DEMAND_CODES = {"UGD", "GSD", "AUGD", "AGSD"}
_LABEL_START_RE = re.compile(
    r"(?:Rate Rider|Service Charge|Distribution Volumetric Rate|Retail Transmission Rate|"
    r"Smart Metering Entity Charge|Low Voltage Service|Meter Charge|Local Transformation Charge|"
    r"Facility Charge)\b"
)
# Midland overprint: "<applicability tail of the previous rider> <next label> <unit> <value>" on one line.
_APPLICABLE_TAIL_RE = re.compile(
    r"^(?P<phrase>Applicable only for (?:Class B Customers|Non-RPP Customers|Non-Wholesale Market Participants))"
    rf"\s+(?={_LABEL_START_RE.pattern})"
)
_SUBHEADING_RE = re.compile(r"^Retail Transmission Service Rates\b")
_SEE_NOTE_RE = re.compile(r"\s*\(see Notes?\s[^)]*\)", re.I)
_FOOTNOTE_MARK_RE = re.compile(r"(?<=\w)\*+(?=\s+-\s)")
_ALLOWANCE_HEADING_RE = re.compile(r"^(?P<head>[A-Z][A-Z\-]*(?: [A-Z\-]+)* ALLOWANCE)\b\s*(?P<rest>.*)$")
_CLASS_LOSS_RE = re.compile(
    r"^(?P<label>(?:Residential|General Service|Acquired (?:Residential|General Service)|"
    r"Distributed Generation|Unmetered Scattered Load|Sentinel Lights|Street Lights)\b.*?)"
    r"\s+(?P<value>\d\.\d{3,5})$"
)
_LOSS_GROUP_RE = re.compile(r"^[A-Z][A-Za-z ]+ - [A-Z][A-Za-z0-9]{0,4}$")
_EMBEDDED_LOSS_RE = re.compile(
    r"^(?:(?P<kind>(?:Distribution|Total) Loss Factors)\s+)?(?P<label>Embedded Delivery Points.*?)"
    r"\s+(?P<value>\d\.\d{3,5})$"
)
_DRP_RE = re.compile(
    r"caps monthly\s+distribution charges at \$\s?(?P<v>\d+\.\d{2})\s+for eligible\s+(?P<who>[^.]+?)\s+customers",
    re.I,
)
_RRRP_CREDIT_RE = re.compile(r"RRRP credit, currently at\s*\$\s?(?P<v>\d+\.\d{2})")
# Decision text: the RRRP adjustment is applied to the base rates of named classes (Algoma R1/R2).
_RRRP_BASE_RATES_RE = re.compile(
    r"RRRP adjustment factor of [\d.]+%,?\s+which was applied to\s+[^.]{0,80}?base rates for\s+"
    r"(?P<classes>[A-Z]\d(?:\s*(?:,|and)\s*[A-Z]\d)*)\s+customer classes"
)
_RES_DEMAND_BASIS_RE = re.compile(r"billed on a demand basis", re.I)
_RES_DEMAND_FLOOR_RE = re.compile(r"greater than\b[^.\d]{0,90}?(\d[\d,]*)\s*(?:kW|kilowatts)\b", re.I)
_FOOTNOTE_SPLIT_RE = re.compile(r"(?:^|\s)(\d{1,2})\.\s+(?=[A-Z])")
_FOOTNOTE_PAREN_SPLIT_RE = re.compile(r"(?:^|\s)(\d{1,2})\)\s+(?=[A-Z])")
_CHAPLEAU_RE = re.compile(r"(?<!Not )applicable to former Chapleau", re.I)
_CHAPLEAU_CONDITION = ("Applies only to former Chapleau PUC customers: this rider set replaces the standard "
                       "riders of the same name for those customers")
_MONTHLY_RE = re.compile(
    r"^MONTHLY RATES AND CHARGES\s*[-–]\s*(?P<part>Delivery|Regulatory) Component\b\s*(?P<rest>.*)$"
)
_CHARGE_RE = re.compile(
    r"^(?:(?P<label>.*?\S)\s+)?(?P<unit>\$/kWh|\$/kW|\$/kVA|\$/km|\$/cust\.|\$|%)\s*"
    r"(?P<value>\(?\s*[-–]?\s*\d[\d\s,]*(?:\.\s?[\d\s]*\d)?\s*\)?)\s*"
    r"(?P<per>\(per 30 days\))?$"
)
_LOSS_RE = re.compile(
    r"(?P<label>(?:Total|Distribution|Supply Facility) Loss Factor\b.*?)\s+(?P<value>\d\.\d{3,5})\s*$"
)
_UNTIL_RE = re.compile(rf"(?:effective|in effect) until\s+(?P<d>{_DATE})", re.I)
_UNTIL_COS_RE = re.compile(r"until the\s+effective date of the next\s+cost of service", re.I)
_GS_RANGE_RE = re.compile(r"^GENERAL SERVICE ([\d,]+) TO ([\d,]+) KW$", re.I)
# Open-ended GS classes: "GREATER THAN 50 KW", "1,000 KW AND GREATER", "1,000 KW OR GREATER".
_GS_OPEN_RE = re.compile(
    r"^GENERAL SERVICE (?:(?:(?:EQUAL TO OR )?GREATER THAN|GREATER THAN OR EQUAL TO|OVER|ABOVE|MORE THAN) "
    r"(?P<a>[\d,]+) KW|"
    r"(?P<b>[\d,]+) KW (?:AND|OR) (?:GREATER|OVER|ABOVE|MORE))$", re.I)
_GS_BELOW_RE = re.compile(r"^GENERAL SERVICE (?:LESS THAN|UNDER|BELOW) ([\d,]+) KW$", re.I)
# Unbounded GS classes with a lower bound above this are built as large-use (industrial) classes.
_OPEN_GS_COMMERCIAL_MAX_FLOOR_KW = 1000
_DEDICATED_STATION_RE = re.compile(r"DEDICATED TRANSFORMER STATION", re.I)
_IN_SCOPE_NAME_RE = re.compile(r"GENERAL SERVICE|LARGE USE|INTERMEDIATE|RESIDENTIAL", re.I)
# Schedule A cover sheet before the approved tariff: "TARIFF OF RATES AND CHARGES EB-2025-0017" / "March 19, 2026".
_COVER_CASE_RE = re.compile(rf"^TARIFF OF RATES AND CHARGES\s+(?P<case>EB-\d{{4}}-\d{{4}})\s*$")
_COVER_DATE_RE = re.compile(rf"^(?P<d>{_DATE})$")
_EXCLUDED_CLASS_RE = re.compile(
    r"LIGHTING|SENTINEL|UNMETERED|EMBEDDED|MICRO\s*FIT|\bFIT\b|STANDBY|GENERATION|DGEN|"
    r"ENERGY RESOURCE|ENERGY FROM WASTE|STORAGE|ELECTRIC VEHICLE|\bEVC?\b|HCI|RESOP|"
    r"DEDICATED TRANSFORMER STATION",
    re.I,
)
# A non-charge line that continues the previous complete charge line (Oshawa wrapping).
_CONTINUATION_RE = re.compile(r"^(?:\(\d{4}\)\s*-|.{0,80}?\b(?:effective|in effect) until\b)", re.I)
# Delivery labels typed "other" that are known, legitimate charges.
_KNOWN_OTHER_RE = re.compile(
    r"^(?:Meter Charge|Local Transformation Charge|Smart Metering Entity Charge|"
    r"Rural or Remote Rate Protection \(RRRP\) credit)\b"
)
_ORPHAN_TAIL_RE = re.compile(r"^(?:effective until|in effect until|\(20\d\d\))", re.I)
_GARBLED_RE = re.compile(r"(?:\b[A-Za-z]\s){3,}")
_METER_ALT_RE = re.compile(r"^Distribution Volumetric Rate - (?P<meter>Thermal Demand Meter|Interval Meter)$")
_SIZE_RANGE_RE = re.compile(
    r"\((?P<range>less than\s*[\d,]+\s*kW|[\d,]+\s*to\s*[\d,]+\s*kW|[\d,]+\s*kW\s+(?:and|or)\s+(?:above|greater|over))\)",
    re.I,
)
_SIZE_CONDITION_PREFIX = "Alternative by demand size"
_NOTE7_CONDITION = ("Applied as determined by the customer's connection point under its connection agreement "
                    "(tariff Note 7)")
_CLASS_REF_RE = re.compile(
    r"General Service (?:less than 50 kW|[\d,]+ to [\d,]+ kW)|Large Use(?: with dedicated assets)?", re.I
)

_EV_RE = r"EV CHARGING|-\s*EV\b"
_CONDITIONS = (
    (re.compile(_EV_RE, re.I),
     "Optional Electric Vehicle Charging (EVC) Rate alternative: replaces the standard retail "
     "transmission rate only for eligible customers who elect it"),
    (re.compile(r"Interval Metered", re.I),
     "Alternative retail transmission rate that applies instead of the standard rate to "
     "interval-metered customers"),
    (re.compile(r"Non[- ]*RPP", re.I),
     "Applies only to non-RPP Class B customers (not wholesale market participants or customers "
     "that changed between Class A and Class B during the accumulation period)"),
    (re.compile(r"Non\s*-?\s*Wholesale Market Participants", re.I),
     "Applies only to customers that are not wholesale market participants"),
    (re.compile(r"Class B", re.I), "Applies only to Class B customers"),
    (re.compile(r"\(if applicable\)", re.I),
     "Applies only where the service is taken (e.g. standard supply service customers)"),
    (re.compile(r"\bnon-WMP\b", re.I),
     "Applies only to customers that are not wholesale market participants"),
    (re.compile(r"Global Adjustment Account", re.I),
     "Applies only to non-RPP Class B customers (not wholesale market participants or customers "
     "that changed between Class A and Class B during the accumulation period)"),
    (re.compile(r"applicable to Seasonal customers", re.I),
     "Alternative service charge for Seasonal (non-year-round) residential properties; replaces "
     "the year-round Service Charge"),
    (re.compile(r"^Meter Charge", re.I),
     "Applies per metering facility only at delivery points where Hydro One owns the metering "
     "(tariff Note 11)"),
    (re.compile(r"^Local Transformation Charge", re.I),
     "Applies per transformer only to ST customers who use Hydro One-owned local transformation "
     "facilities (tariff Note 15)"),
    (re.compile(r"^Facility Charge for connection to Common ST Lines", re.I),
     "Alternative by connection type: applies only to ST customers connected to common ST lines "
     "(44 kV to 13.8 kV); basis is the monthly maximum demand (tariff Notes 1, 8 and 14)"),
    (re.compile(r"^Facility Charge for connection to Specific ST Lines", re.I),
     "Alternative by connection type: per kilometre of line within a supplied LDC's service area "
     "supplying solely that LDC (tariff Note 2); an embedded-LDC supply charge listed for reference"),
    (re.compile(r"^Facility Charge\b.*Low Voltage Distribution Station", re.I),
     "Alternative by connection type: applies only where supplied through a Hydro One Low Voltage "
     "Distribution Station; basis is the non-coincident demand at each delivery point (tariff Notes 3 and 14)"),
    (re.compile(r"^Facility Charge\b.*High Voltage Distribution Station", re.I),
     "Alternative by connection type: applies only where supplied through a Hydro One High Voltage "
     "Distribution Station at the stated secondary voltage; basis is the monthly maximum demand "
     "(tariff Notes 1 and 14)"),
    (re.compile(r"^Facility Charge", re.I),
     "Alternative by connection type, as set by the customer's connection"),
    (re.compile(r"Retail Transmission Rate - (?:Line|Transformation) Connection Service Rate", re.I),
     _NOTE7_CONDITION),
)
_ALTERNATIVE_TRANSMISSION_RE = re.compile(rf"{_EV_RE}|Interval Metered", re.I)


@dataclass(frozen=True)
class TariffCharge:
    """One published ``<label> <unit> <value>`` line."""

    label: str
    value: float
    unit: str                        # $/month, $/30 days, $/kWh, $/kW, $/kVA, $/customer, %
    kind: str                        # one of CHARGE_KINDS
    section: str                     # "delivery" | "regulatory" | "allowances"
    page_number: int
    period: Optional[str] = None     # "month" or "30 days" for fixed and demand charges
    end_date: Optional[str] = None   # ISO date from "effective until <date>"
    conditional: bool = False
    condition: Optional[str] = None
    term: Optional[str] = None       # open-ended term such as "until the next cost-of-service order"


@dataclass(frozen=True)
class LossFactor:
    label: str
    value: float
    page_number: int


@dataclass
class Classification:
    name: str                        # heading without " SERVICE CLASSIFICATION"
    eligibility: str = ""
    demand_min_kw: Optional[float] = None
    demand_max_kw: Optional[float] = None
    demand_text: Optional[str] = None
    charges: list[TariffCharge] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)
    code: Optional[str] = None       # Hydro One class code, canonical case (UR, R1, UGe, GSd, ST, ...)
    group: Optional[str] = None      # rate-free group heading, e.g. "RESIDENTIAL SERVICE CLASSIFICATIONS"

    def find(self, kind: str, *, conditional: Optional[bool] = None) -> list[TariffCharge]:
        return [c for c in self.charges
                if c.kind == kind and (conditional is None or c.conditional == conditional)]


@dataclass
class TariffSheet:
    source_url: str
    today: str
    distributor: Optional[str] = None
    rate_zone: Optional[str] = None
    effective_date: Optional[str] = None
    implementation_date: Optional[str] = None
    case_number: Optional[str] = None
    issued_date: Optional[str] = None
    classifications: list[Classification] = field(default_factory=list)
    allowances: list[TariffCharge] = field(default_factory=list)
    loss_factors: list[LossFactor] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rejections: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)          # sheet-level notes (e.g. ST allowance text)
    footnotes: dict[str, str] = field(default_factory=dict)  # numbered NOTES section, keyed "1", "2", ...
    exclusions: dict[str, str] = field(default_factory=dict)  # excluded class name -> reason (build_demand_records)

    def classification(self, name: str) -> Optional[Classification]:
        wanted = _norm_name(name)
        return next((c for c in self.classifications if _norm_name(c.name) == wanted), None)


# ─── Small helpers ────────────────────────────────────────────────

def _iso(raw: str) -> Optional[str]:
    text = re.sub(r"\s+", " ", raw.replace(".", "")).strip()
    text = re.sub(r"\s*,\s*", ", ", text)
    if "," not in text:
        text = re.sub(r"^(\w+ \d{1,2}) (\d{4})$", r"\1, \2", text)
    try:
        return datetime.strptime(text, "%B %d, %Y").date().isoformat()
    except ValueError:
        return None


def _today_iso(today: Union[date, str, None]) -> str:
    if today is None:
        return date.today().isoformat()
    return today.isoformat() if isinstance(today, date) else str(today)[:10]


def _norm_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace("–", "-")).strip().upper()


def _parse_value(raw: str) -> Optional[float]:
    text = re.sub(r"[\s,]", "", raw).replace("–", "-")
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return None
    value = float(text)
    return -abs(value) if negative else value


def _kind(label: str, section: str) -> str:
    folded = label.casefold()
    if section == "regulatory":
        return "regulatory"
    if section == "allowances":
        return "other"
    if folded.startswith("rate rider"):
        return "rider"
    if folded.startswith("service charge"):
        return "service"
    if folded.startswith("distribution volumetric rate"):
        return "distribution"
    if "retail transmission rate" in folded and "network" in folded:
        return "transmission_network"
    if "retail transmission rate" in folded and "connection" in folded:
        return "transmission_connection"
    if folded.startswith("low voltage"):
        return "low_voltage"
    if folded.startswith("facility charge"):
        return "facility"
    return "other"


def _condition(label: str, section: str) -> Optional[str]:
    if section == "allowances":
        if re.search(r"transform(?:er|ation) allowance", label, re.I):
            return ("Conditional credit: applies only to customers who provide (own) their own "
                    "transformation facilities")
        return "Conditional: applies only to primary-metered customers, as published"
    texts = [_CHAPLEAU_CONDITION] if _CHAPLEAU_RE.search(label) else []
    if meter := _METER_ALT_RE.match(label):
        kind = meter.group("meter").lower()
        return (f"Alternative distribution rate by meter type: applies only to customers metered with "
                f"{'an' if kind[0] in 'aeiou' else 'a'} {kind}; the other meter-type rate applies instead otherwise")
    for pattern, text in _CONDITIONS:
        if pattern.search(label):
            texts.append(text)
            break
    return "; ".join(texts) or None


def _unit(token: str, per: Optional[str]) -> tuple[str, Optional[str]]:
    period = "30 days" if per else "month"
    if token == "$":
        return ("$/30 days" if per else "$/month"), period
    if token == "$/cust.":
        return "$/customer", "month"
    if token in ("$/kW", "$/kVA", "$/km"):
        return token, period
    return token, None


def _num(raw: str) -> float:
    return float(raw.replace(",", ""))


def _name_bounds(name: Optional[str]) -> tuple[Optional[float], Optional[float]]:
    """kW bounds printed in a class name; an inclusive "... to 4,999" upper bound becomes "< 5,000"."""
    norm = _norm_name(name or "")
    if m := _GS_RANGE_RE.match(norm):
        hi = _num(m.group(2))
        return _num(m.group(1)), hi + 1 if hi % 10 == 9 else hi
    if m := _GS_OPEN_RE.match(norm):
        return _num(m.group("a") or m.group("b")), None
    if m := _GS_BELOW_RE.match(norm):
        return None, _num(m.group(1))
    return None, None


def _demand_bounds(text: str, name: Optional[str] = None) -> tuple[Optional[float], Optional[float], Optional[str]]:
    flat = re.sub(r"\s+", " ", text)
    # "shall not qualify as a General Service Less Than 50 kW ..." names another class, not a bound.
    scrubbed = re.sub(r"General Service\s+Less\s+Than\s+[\d,]+\s*kW", " ", flat, flags=re.I)
    lo = re.search(r"greater than\b[^.\d]{0,90}?(\d[\d,]*(?:\.\d+)?)\s*kW\b", scrubbed, re.I)
    hi = re.search(r"less than\b[^.\d]{0,90}?(\d[\d,]*(?:\.\d+)?)\s*kW\b", scrubbed, re.I)
    if lo is None:
        lo = re.search(r"\b(?:equall?ed or )?exceed(?:s|ed)?\b[^.\d]{0,60}?(\d[\d,]*(?:\.\d+)?)\s*kW\b",
                       scrubbed, re.I)
    sentence = next((s.strip() for s in re.split(r"(?<=\.)\s+", flat)
                     if re.search(r"\d\s*(?:kW|kVA)\b", s)), None)
    low = _num(lo.group(1)) if lo else None
    high = _num(hi.group(1)) if hi else None
    if low is None and high is None and (
            rng := re.search(r"in the range of (\d[\d,]*) to (\d[\d,]*)\s*kW\b", scrubbed, re.I)):
        low, high = _num(rng.group(1)), _num(rng.group(2))
        high = high + 1 if high % 10 == 9 else high
    name_lo, name_hi = _name_bounds(name)
    return (low if low is not None else name_lo), (high if high is not None else name_hi), sentence


# ─── Parsing ──────────────────────────────────────────────────────

def _size_range(label: str) -> Optional[str]:
    m = _SIZE_RANGE_RE.search(label)
    return re.sub(r"\s+", " ", re.sub(r"(?<=than)(?=\d)", " ", m.group("range"))) if m else None


def _connection_part(label: str) -> Optional[str]:
    m = re.search(r"- (Line|Transformation) Connection Service Rate\b", label)
    return m.group(1) if m else None


def _separate_connection_pair(cls: Classification) -> None:
    """ENWIN Large Use: separate Line and Transformation Connection rates are both charged (not alternatives)."""
    pair = [c for c in cls.charges if c.kind == "transmission_connection" and c.condition == _NOTE7_CONDITION]
    if {_connection_part(c.label) for c in pair} == {"Line", "Transformation"} and len(pair) == 2:
        cls.charges = [replace(c, conditional=False, condition=None) if c in pair else c for c in cls.charges]


def _single_connection_standard(cls: Classification) -> None:
    """Note 7 alternatives come in Line + Transformation pairs; a lone Transformation line is the standard rate (Atikokan).

    A lone Line line stays conditional (half of a pair whose other part is missing; fails closed).
    """
    lines = [c for c in cls.charges if c.kind == "transmission_connection" and c.condition == _NOTE7_CONDITION]
    if len(lines) == 1 and _connection_part(lines[0].label) == "Transformation":
        cls.charges = [replace(c, conditional=False, condition=None) if c in lines else c for c in cls.charges]


def _deinterleave_heading(text: str) -> str:
    """Undo "CLASSIFICATION" overprinted on "This classification applies ..." (Tillsonburg p22)."""
    target, kept, i = "CLASSIFICATION", [], 0
    for position, char in enumerate(text[:90]):
        if i < len(target) and char == target[i]:
            i += 1
            continue
        kept.append(char)
        if i == len(target):
            repaired = "".join(kept) + text[position + 1:]
            return repaired if re.match(r"This classification (?:applies|refers) to\b", repaired) else text
    return text


def _promote_interval_transmission(cls: Classification) -> None:
    """An interval-metered transmission rate is the class rate when no plain rate is published.

    When several interval-metered rates split the class by demand size (Enova Waterloo North:
    "(less than 1,000 kW)" / "(1,000 to 4,999 kW)"), they stay conditional alternatives keyed
    by the printed size range instead.
    """
    for kind in ("transmission_network", "transmission_connection"):
        lines = [c for c in cls.charges if c.kind == kind]
        if any(not _ALTERNATIVE_TRANSMISSION_RE.search(c.label) for c in lines):
            continue
        interval = [c for c in lines if re.search("Interval Metered", c.label, re.I)
                    and not re.search(_EV_RE, c.label, re.I)]
        ranges = [_size_range(c.label) for c in interval]
        if len(interval) > 1 and all(ranges) and len(set(ranges)) == len(ranges):
            cls.charges = [
                replace(c, conditional=True,
                        condition=f"{_SIZE_CONDITION_PREFIX}: applies only to interval-metered customers with "
                                  f"demand {_size_range(c.label)}; the other size range's rate applies otherwise")
                if c in interval else c
                for c in cls.charges
            ]
            if re.search(r"non-interval", cls.eligibility, re.I):
                note = ("The eligibility text lists a non-interval-metered sub-classification, but the tariff "
                        "publishes retail transmission rates only for interval-metered customers by demand size; "
                        "no rate is inferred for non-interval-metered customers.")
                if note not in cls.notes:
                    cls.notes.append(note)
            continue
        cls.charges = [
            replace(c, conditional=False, condition=None)
            if c.kind == kind and re.search("Interval Metered", c.label, re.I)
            and not re.search(_EV_RE, c.label, re.I) else c
            for c in cls.charges
        ]

def _split_page(page: DocumentPage) -> Optional[dict]:
    """Strip the repeated OEB page header; return header facts and body lines."""
    lines = [line.strip() for line in page.text.splitlines() if line.strip()]
    index = next((i for i, line in enumerate(lines) if _TARIFF_LINE_RE.match(line)), None)
    if index is None:
        return None
    header_window = " ".join(lines[index:index + 4])
    if "supersedes" not in header_window:
        return None  # cover sheets such as "SCHEDULE A ... TARIFF OF RATES AND CHARGES EB-..."
    preamble = [line for line in lines[:index] if not _PAGE_NO_RE.match(line)]
    page_of = next((m for line in lines[:index] if (m := _PAGE_OF_RE.match(line))), None)
    info: dict = {
        "distributor": preamble[0] if preamble else None,
        "zone": " ".join(preamble[1:]) or None,
        "effective": None, "implementation": None, "case": None, "issued": None,
        "page_of": int(page_of.group(1)) if page_of else None,
    }
    if m := _EFF_IMPL_RE.search(header_window):
        info["effective"] = info["implementation"] = _iso(m.group("d"))
    else:
        if m := _EFF_RE.search(header_window):
            info["effective"] = _iso(m.group("d"))
        if m := _IMPL_RE.search(header_window):
            info["implementation"] = _iso(m.group("d"))
    body: list[str] = []
    in_header = True
    issued: list[str] = []
    remaining = lines[index + 1:]
    for position, line in enumerate(remaining):
        if in_header:
            if _IMPL_RE.match(line) or _SUPERSEDES_RE.match(line):
                continue
            if m := _APPROVED_RE.match(line):
                rest = m.group("rest")
                if case := _CASE_RE.match(rest):
                    info["case"] = case.group(0)
                    rest = rest[case.end():].strip()
                in_header = False
                if rest:
                    body.append(rest)
                continue
            in_header = False
        if m := _FINAL_SCHEDULE_FOOTER_RE.search(line):
            line = line[:m.start()].strip()
        while m := _ISSUED_RE.search(line):
            issued.append(_iso(m.group("d")) or "")
            line = line[:m.start()].strip()
        last = all(_FINAL_SCHEDULE_FOOTER_RE.fullmatch(" " + rest) or _ISSUED_RE.fullmatch(rest)
                   for rest in remaining[position + 1:])
        if (m := _BARE_DATE_RE.search(line)) and (m.start() > 0 or last):
            issued.append(_iso(m.group("d")) or "")
            line = line[:m.start()].strip()
        if not line:
            continue
        body.append(line)
    issued = [d for d in issued if d]
    info["issued"] = max(issued) if issued else None
    info["body"] = body
    return info


def _new_charge(label: str, m: re.Match, section: str, page: int) -> Optional[TariffCharge]:
    value = _parse_value(m.group("value"))
    if value is None or not label:
        return None
    unit, period = _unit(m.group("unit"), m.group("per"))
    label = _FOOTNOTE_MARK_RE.sub("", _SEE_NOTE_RE.sub("", re.sub(r"\s+", " ", label))).strip()
    label = re.sub(r"\s+\*+$", "", label)
    kind = _kind(label, section)
    end = None
    if until := _UNTIL_RE.search(label):
        end = _iso(until.group("d"))
    condition = _condition(label, section)
    term = ("In effect until the effective date of the next cost-of-service rate order"
            if _UNTIL_COS_RE.search(label) else None)
    return TariffCharge(
        label=re.sub(r"\s+", " ", label).strip(), value=value, unit=unit, kind=kind,
        section=section, page_number=page, period=period, end_date=end,
        conditional=condition is not None, condition=condition, term=term,
    )


def _tail_split(label: str) -> Optional[tuple[str, str]]:
    """Split "<previous label tail>) <new label>" glued together by row joining."""
    for m in _LABEL_START_RE.finditer(label):
        if m.start() == 0:
            return None
        prefix = label[:m.start()].rstrip()
        if prefix.endswith(")") or re.search(r"\d{4}$", prefix):
            return prefix, label[m.start():]
    return None


def _add_footnote_credits(cls: Classification) -> None:
    """Hydro One R2: the RRRP credit is printed only in a footnote; keep it as a conditional credit."""
    for note in cls.notes:
        if m := _RRRP_CREDIT_RE.search(note):
            page = next((c.page_number for c in cls.charges if c.kind == "service"), cls.pages[-1])
            cls.charges.append(TariffCharge(
                label="Rural or Remote Rate Protection (RRRP) credit - qualifying year-round principal residence",
                value=-float(m.group("v")), unit="$/month", kind="other", section="delivery",
                page_number=page, period="month", conditional=True,
                condition="Conditional credit: reduces the year-round Service Charge only for qualifying "
                          "year-round customers with a principal residence (RRRP); not for Seasonal customers",
            ))
            return


def _split_footnotes(text: str) -> dict[str, str]:
    """Split a numbered NOTES section ("1. ... 2. ..." or "1) ... 2) ...") into {"1": ..., "2": ...}, in sequence only."""
    found: dict[str, str] = {}
    expected, start, key = 1, None, None
    splitter = _FOOTNOTE_PAREN_SPLIT_RE if re.match(r"\s*1\)\s", text) else _FOOTNOTE_SPLIT_RE
    for m in splitter.finditer(text):
        if int(m.group(1)) != expected:
            continue
        if key is not None:
            found[key] = text[start:m.start()].strip()
        key, start, expected = m.group(1), m.end(), expected + 1
    if key is not None:
        found[key] = text[start:].strip()
    return found


def _approved_copies(sheet: TariffSheet, pages: Sequence[DocumentPage], infos: list) -> list:
    """Drop tariff copies printed under a "Proposed/Draft Tariff of Rates and Charges" cover.

    Rate orders can append the settlement's proposed tariff (Burlington Appendix B) or repeat
    the approved one (Entegrus "5. Final Tariff Schedule"). A copy starts after a page gap or
    a "Page 1 of N" restart. Remaining duplicates are reconciled by ``_dedupe_classifications``.
    """
    copies: list[list] = []
    previous = None
    for number, info in infos:
        if previous is None or number - previous > 1 or (info["page_of"] == 1 and copies[-1]):
            copies.append([])
        copies[-1].append((number, info))
        previous = number
    tariff_numbers = {p.page_number for p in pages if _split_page(p)}
    by_number = {p.page_number: p for p in pages}

    def proposed(copy: list) -> bool:
        start = copy[0][0]
        for number in (start - 1, start - 2):
            if number in tariff_numbers or number not in by_number:
                return False
            text = re.sub(r"\s+", " ", by_number[number].text)
            if len(text) < 600 and _PROPOSED_COVER_RE.search(text):
                return True
        return False

    flagged = [copy for copy in copies if proposed(copy)]
    if not flagged:
        return infos
    if len(flagged) == len(copies):
        sheet.errors.append("Only a proposed/draft Tariff of Rates and Charges was found (PDF pages "
                            + ", ".join(f"{c[0][0]}-{c[-1][0]}" for c in flagged) + ")")
        return []
    for copy in flagged:
        sheet.notes.append(f"Ignored the proposed/draft tariff copy on PDF pages {copy[0][0]}-{copy[-1][0]}; "
                           "only the approved tariff is parsed.")
    return [item for copy in copies if copy not in flagged for item in copy]


def _signature(cls: Classification) -> tuple:
    """Published values only: copies may word rider labels differently (Entegrus draft vs Schedule A)."""
    return (cls.code, cls.demand_min_kw, cls.demand_max_kw,
            tuple(sorted((c.kind, c.section, c.value, c.unit, c.period or "", c.end_date or "", c.conditional,
                          c.term is not None) for c in cls.charges)))


def _dedupe_classifications(sheet: TariffSheet) -> None:
    """Identical repeated classes collapse to the first; differing repeats are rejected (all copies)."""
    groups: dict[tuple, list[Classification]] = {}
    for cls in sheet.classifications:
        if _EXCLUDED_CLASS_RE.search(cls.name):
            continue  # e.g. several numbered EMBEDDED DISTRIBUTOR classes; never built
        groups.setdefault((_norm_name(cls.name), cls.code), []).append(cls)
    drop: list[Classification] = []
    cut: Optional[int] = None
    for copies in groups.values():
        if len(copies) < 2:
            continue
        cut = min(cut or copies[1].pages[0], copies[1].pages[0])
        pages = ", ".join(f"{c.pages[0]}-{c.pages[-1]}" for c in copies)
        if len({_signature(c) for c in copies}) == 1:
            copies[0].notes.append(f"The same classification is printed {len(copies)} times in this document "
                                   f"(PDF pages {pages}) with identical published values; the first copy is used.")
            drop.extend(copies[1:])
        else:
            sheet.rejections[copies[0].name] = (f"conflicting duplicate tariff copies (PDF pages {pages}) publish "
                                                "different eligibility or charges; class rejected")
            drop.extend(copies)
    if drop:
        sheet.classifications = [c for c in sheet.classifications if not any(c is d for d in drop)]
    if cut is None:
        return
    # Allowances and loss factors come from the first copy; a later copy must publish the same values.
    for attr in ("allowances", "loss_factors"):
        items = getattr(sheet, attr)
        first = [i for i in items if i.page_number < cut]
        later = [i for i in items if i.page_number >= cut]
        if later and sorted((i.value, getattr(i, "unit", "")) for i in first) != sorted(
                (i.value, getattr(i, "unit", "")) for i in later):
            sheet.errors.append(f"Repeated tariff copies publish different {attr.replace('_', ' ')}")
        setattr(sheet, attr, first)


def _cover_case_number(sheet: TariffSheet, pages: Sequence[DocumentPage], first_page: int) -> Optional[str]:
    """Case number from the Schedule A cover immediately before the tariff, only if dated as issued."""
    cover = next((p for p in pages if p.page_number == first_page - 1), None)
    if cover is None or sheet.issued_date is None or _split_page(cover):
        return None
    lines = [line.strip() for line in cover.text.splitlines() if line.strip()]
    if not lines or lines[0] != "SCHEDULE A" or len(" ".join(lines)) > 600:
        return None
    cases = [m.group("case") for line in lines if (m := _COVER_CASE_RE.match(line))]
    dates = [_iso(m.group("d")) for line in lines if (m := _COVER_DATE_RE.match(line))]
    if len(cases) != 1 or dates != [sheet.issued_date]:
        return None
    sheet.notes.append(f"OEB case number {cases[0]} taken from the Schedule A cover (PDF page {cover.page_number}), "
                       f"dated {sheet.issued_date} like the tariff; tariff page headers print no case number.")
    return cases[0]


def parse_tariff_pages(
    pages: Sequence[DocumentPage],
    source_url: str,
    today: Union[date, str, None] = None,
    rate_zone: Optional[str] = None,
) -> TariffSheet:
    """Parse OEB tariff pages for one distributor (and, if given, one rate zone).

    Non-tariff pages (decision text, cover sheets) are ignored. A document that
    carries several rate zones must be parsed one zone at a time; otherwise the
    sheet records an error and ``build_demand_records`` fails closed.
    """
    sheet = TariffSheet(source_url=source_url, today=_today_iso(today))
    infos = [(p.page_number, info) for p in pages if (info := _split_page(p))]
    zones = {info["zone"] for _, info in infos}
    if rate_zone is not None:
        infos = [(n, i) for n, i in infos if (i["zone"] or "").casefold() == rate_zone.casefold()]
    elif len(zones) > 1:
        sheet.errors.append(f"Multiple rate zones present ({sorted(z or '' for z in zones)}); "
                            "parse each zone separately")
    if not infos:
        sheet.errors.append("No OEB tariff pages found")
        return sheet
    infos = _approved_copies(sheet, pages, infos)
    if not infos:
        return sheet

    def single(key: str, label: str) -> Optional[str]:
        values = Counter(i[key] for _, i in infos if i[key])
        if len(values) > 1:
            sheet.errors.append(f"Inconsistent {label} across pages: {sorted(values)}")
        return values.most_common(1)[0][0] if values else None

    sheet.distributor = single("distributor", "distributor name")
    sheet.rate_zone = single("zone", "rate zone")
    sheet.effective_date = single("effective", "effective dates")
    sheet.implementation_date = single("implementation", "implementation dates")
    sheet.case_number = single("case", "case numbers")
    issued = sorted({i["issued"] for _, i in infos if i["issued"]})
    sheet.issued_date = issued[-1] if issued else None
    if sheet.case_number is None:
        sheet.case_number = _cover_case_number(sheet, pages, infos[0][0])
    if not sheet.effective_date:
        sheet.errors.append("Effective date not found")
    elif sheet.effective_date > sheet.today:
        sheet.errors.append(f"Effective date {sheet.effective_date} is in the future")
    if sheet.implementation_date and sheet.implementation_date > sheet.today:
        sheet.errors.append(f"Implementation date {sheet.implementation_date} is in the future")

    rrrp_codes: dict[str, int] = {}
    for page in pages:
        if rm := _RRRP_BASE_RATES_RE.search(page.text):
            rrrp_codes.update({code: page.page_number for code in re.findall(r"[A-Z]\d", rm.group("classes"))})
    drp_note = None
    for page in pages:
        if dm := _DRP_RE.search(page.text):
            who = re.sub(r"\s+", " ", dm.group("who"))
            drp_note = (f"Distribution Rate Protection (DRP): the OEB rate order (PDF page {page.page_number}) "
                        f"states the program currently caps monthly distribution charges at ${dm.group('v')} "
                        f"for eligible {who} customers. The tariff rates do not reflect DRP; the cap is a "
                        "note only and is not applied or computed.")
            break

    current: Optional[Classification] = None
    # none | description | boilerplate | charges | allowances | ignore | loss | group | group_boilerplate | notes
    mode = "none"
    section = "delivery"
    description: list[str] = []
    boilerplate: list[str] = []
    pending: list[str] = []
    footnote = False
    tail: Optional[dict] = None          # last charge built from a bare "<unit> <value>" line
    after: Optional[dict] = None         # last complete "<label> <unit> <value>" charge line
    billing_note: list[str] = []
    group_name: Optional[str] = None
    group_desc: list[str] = []
    class_group_desc = ""
    allowance_ctx: Optional[dict] = None
    loss_group: Optional[str] = None
    loss_kind: Optional[str] = None
    notes_text: list[str] = []

    def close_class() -> None:
        nonlocal current, pending, tail, after
        tail = after = None
        if current is None:
            return
        if mode == "description" or (description and not current.eligibility):
            current.eligibility = " ".join(description).strip()
        if not current.eligibility and current.code and class_group_desc:
            current.eligibility = class_group_desc
        if not current.eligibility.startswith("This classification"):
            current.eligibility = _deinterleave_heading(current.eligibility)
        if pending:
            current.unparsed.extend(pending)
        current.demand_min_kw, current.demand_max_kw, current.demand_text = _demand_bounds(
            current.eligibility, None if current.code else current.name)
        if current.code is None:
            _separate_connection_pair(current)
        _single_connection_standard(current)
        _promote_interval_transmission(current)
        _add_footnote_credits(current)
        for charge in current.charges:
            if (charge.kind == "rider" and charge.end_date is None and charge.term is None
                    and charge.label.count("(") > charge.label.count(")")):
                note = (f"End date of rider '{charge.label}' ({charge.unit}) was not found in the extracted "
                        "text (wrapped line missing); kept without an end date, not inferred.")
                if note not in current.notes:
                    current.notes.append(note)
        if drp_note and any("Distribution Rate Protection" in n for n in current.notes):
            current.notes.append(drp_note)
        pending = []
        current = None

    def flush_allowance() -> None:
        nonlocal allowance_ctx
        if allowance_ctx and not allowance_ctx["emitted"] and allowance_ctx["applies"]:
            sheet.notes.append(f"{allowance_ctx['head']}: {allowance_ctx['applies']}")
        allowance_ctx = None

    def add_loss(line: str, page: int) -> None:
        nonlocal loss_group, loss_kind
        if lm := _LOSS_RE.search(line):
            label = lm.group("label").replace("–", "-")
        elif lm := _CLASS_LOSS_RE.match(line):
            label = lm.group("label")
        elif _LOSS_GROUP_RE.match(line):
            loss_group, loss_kind = line, None
            return
        elif loss_group and (lm := _EMBEDDED_LOSS_RE.match(line)):
            loss_kind = lm.group("kind") or loss_kind
            label = " - ".join(p for p in (loss_group, loss_kind, lm.group("label")) if p)
        else:
            return
        sheet.loss_factors.append(LossFactor(re.sub(r"\s+", " ", label), float(lm.group("value")), page))

    def extend_tail(extra: str, ref: Optional[dict] = None) -> None:
        ref = ref or tail
        ref["label"] = f"{ref['label']} {extra}"
        charge = _new_charge(ref["label"], ref["match"], ref["section"], ref["page"])
        if charge is not None and current is not None:
            current.charges[ref["index"]] = charge

    def start_charges() -> None:
        nonlocal mode
        if current is not None and mode in ("description", "boilerplate"):
            current.eligibility = " ".join(description).strip()
            joined = " ".join(boilerplate)
            for note in re.findall(r"Note:\s*(.+?\.)(?=\s+[A-Z]|\s*$)", joined):
                current.notes.append(f"Note: {note}")
        mode = "charges"

    def add_line(text: str, page: int) -> None:
        nonlocal pending, footnote, tail, after, allowance_ctx
        target_allowance = mode == "allowances"
        if text.startswith("*") and not target_allowance:
            tail = after = None
            if current is not None:
                current.notes.append(text)
            footnote = True
            return
        m = _CHARGE_RE.match(text)
        if tail is not None and current is not None and not target_allowance:
            # Hydro One wraps as "<label part> / <unit> <value> / <label tail>".
            if not m and not _LABEL_START_RE.match(text) and not _SUBHEADING_RE.match(text):
                extend_tail(text)
                return
            if m and m.group("label") and (split := _tail_split(m.group("label"))):
                extend_tail(split[0])
                text = split[1] + text[m.end("label"):]
                m = _CHARGE_RE.match(text)
            tail = None
        if (m and after is not None and current is not None and not target_allowance and not pending
                and (am := _APPLICABLE_TAIL_RE.match(m.group("label") or ""))):
            previous = current.charges[after["index"]]
            if previous.kind == "rider" and "applicable" not in previous.label.casefold():
                extend_tail(am.group("phrase"), after)
                text = text[am.end():].lstrip()
                m = _CHARGE_RE.match(text)
        if not m:
            if (after is not None and current is not None and not target_allowance and not pending
                    and not footnote and not _LABEL_START_RE.match(text) and not _SUBHEADING_RE.match(text)
                    and (_CONTINUATION_RE.match(text) or after["label"].endswith("-"))):
                # Oshawa wraps as "<label> <unit> <value> / <label tail>" ("(2026) - effective until ...").
                extend_tail(text, after)
                return
            after = None
            if target_allowance and (hm := _ALLOWANCE_HEADING_RE.match(text)):
                flush_allowance()
                allowance_ctx = {"head": hm.group("head").title(), "applies": hm.group("rest").strip(),
                                 "emitted": False}
                pending = []
            elif target_allowance and allowance_ctx is not None:
                if allowance_ctx["emitted"]:
                    allowance_ctx["applies"], allowance_ctx["emitted"] = text, False
                else:
                    allowance_ctx["applies"] = f"{allowance_ctx['applies']} {text}".strip()
            elif _SUBHEADING_RE.match(text) and current is not None:
                current.notes.append(text)
            elif footnote and current is not None and current.notes:
                current.notes[-1] += " " + text
            else:
                pending.append(text)
            return
        footnote = False
        bare = m.group("label") is None
        label = " ".join(pending + [m.group("label") or ""]).strip()
        pending = []
        printed_condition = None
        if target_allowance and allowance_ctx is not None:
            applies = allowance_ctx["applies"]
            if ". " in label:
                head, label = label.rsplit(". ", 1)
                applies = f"{applies} {head}.".strip()
            allowance_ctx["applies"], allowance_ctx["emitted"] = applies, True
            label = f"{allowance_ctx['head']} - {label}"
            printed_condition = f"Conditional: {applies}" if applies else None
        elif target_allowance and sheet.allowances and re.match(r"(General Service|Large Use)", label, re.I):
            base = re.split(r"\s+(?=General Service|Large Use)", sheet.allowances[-1].label,
                            maxsplit=1, flags=re.I)[0]
            label = f"{base} {label}"
        charge = _new_charge(label, m, "allowances" if target_allowance else section, page)
        if charge is not None and printed_condition:
            charge = replace(charge, conditional=True, condition=printed_condition)
        after = None
        if charge is None:
            (current.unparsed if current is not None else sheet.unparsed).append(text)
        elif target_allowance:
            sheet.allowances.append(charge)
        elif current is not None:
            current.charges.append(charge)
            ref = {"index": len(current.charges) - 1, "label": label, "match": m,
                   "section": section, "page": page}
            if bare:
                tail = ref
            else:
                after = ref

    def start_class(cls: Classification, rest: Optional[str], page: int) -> None:
        nonlocal current, mode, section, footnote, description, boilerplate
        close_class()
        flush_allowance()
        current = cls
        sheet.classifications.append(cls)
        cls.pages.append(page)
        mode, section, footnote = "description", "delivery", False
        description, boilerplate = [], []
        if rest:
            description.append(rest)

    for page_number, info in infos:
        tail = after = None
        for line in info["body"]:
            if m := _GROUP_RE.match(line):
                close_class()
                flush_allowance()
                mode, group_name, group_desc = "group", _norm_name(m.group("name")), []
                pending, footnote = [], False
                continue
            if m := _CODED_CLASS_RE.match(line):
                close_class()
                code = m.group("code")
                class_group_desc = " ".join(group_desc).strip()
                start_class(Classification(name=re.sub(r"\s+", " ", m.group("name")).strip(),
                                           code=_CANONICAL_CODES.get(code.upper(), code), group=group_name),
                            m.group("rest"), page_number)
                continue
            if m := _CLASS_RE.match(line):
                name = m.group("name")
                if not re.search(r"[a-z]", re.sub(r"(?i:micro)|kW", "", name)):
                    start_class(Classification(name=re.sub(r"\s+", " ", name).strip()),
                                m.group("rest"), page_number)
                    continue
            if ((m := _SERVICE_HEADING_RE.match(line)) and "CLASSIFICATION" not in line
                    and _SERVICE_HEADING_NAME_RE.search(m.group("name"))):
                start_class(Classification(name=re.sub(r"\s+", " ", m.group("name")).strip()), None, page_number)
                continue
            if m := _SECTION_RE.match(line):
                close_class()
                flush_allowance()
                name = m.group("name").upper()
                mode = {"ALLOWANCES": "allowances", "LOSS FACTORS": "loss", "NOTES": "notes",
                        "GROSS LOAD BILLING NOTE": "billing_note"}.get(name, "ignore")
                pending, footnote = [], False
                if mode == "billing_note":
                    billing_note.append("")
                rest = m.group("rest")
                if rest and mode == "allowances":
                    add_line(rest, page_number)
                elif rest and mode == "loss":
                    add_loss(rest, page_number)
                elif rest and mode == "notes":
                    notes_text.append(rest)
                elif rest and mode == "billing_note":
                    billing_note[-1] = rest
                continue
            if current is not None and page_number not in current.pages:
                current.pages.append(page_number)
            if m := _MONTHLY_RE.match(line):
                if current is None:
                    continue
                start_charges()
                section = "delivery" if m.group("part") == "Delivery" else "regulatory"
                if pending:
                    current.unparsed.extend(pending)
                pending, footnote, tail, after = [], False, None, None
                if m.group("rest"):
                    add_line(m.group("rest"), page_number)
                continue
            if mode == "description":
                if line.startswith("APPLICATION"):
                    mode = "boilerplate"
                else:
                    description.append(line)
            elif mode == "boilerplate":
                boilerplate.append(line)
            elif mode in ("charges", "allowances"):
                add_line(line, page_number)
            elif mode == "loss":
                add_loss(line, page_number)
            elif mode == "group":
                if line.startswith("APPLICATION"):
                    mode = "group_boilerplate"
                elif not re.fullmatch(r"[A-Z][A-Z .,'-]*", line):
                    group_desc.append(line)
            elif mode == "notes":
                notes_text.append(line)
            elif mode == "billing_note":
                billing_note[-1] = f"{billing_note[-1]} {line}".strip()
    close_class()
    flush_allowance()
    for cls in sheet.classifications:
        code = _norm_name(cls.name).rsplit(" ", 1)[-1]
        if code in rrrp_codes and "RESIDENTIAL" in _norm_name(cls.name):
            cls.notes.append(
                f"Rural or Remote Electricity Rate Protection (RRRP): the OEB decision (PDF page {rrrp_codes[code]}) "
                f"applies the RRRP adjustment to the {code} base rates, so the approved rates already include the "
                "rate protection; no separate RRRP credit is listed or computed.")
    sheet.footnotes = _split_footnotes(" ".join(notes_text))
    for text in dict.fromkeys(t for t in billing_note if t):
        sheet.notes.append(f"Gross Load Billing Note: {text}")
    _dedupe_classifications(sheet)
    return sheet


def parse_tariff_zones(
    pages: Sequence[DocumentPage],
    source_url: str,
    today: Union[date, str, None] = None,
) -> dict[Optional[str], TariffSheet]:
    """Parse every rate zone in a (possibly multi-zone) tariff document."""
    zones: list[Optional[str]] = []
    for page in pages:
        info = _split_page(page)
        if info and info["zone"] not in zones:
            zones.append(info["zone"])
    return {zone: parse_tariff_pages(pages, source_url, today, rate_zone=zone or "") for zone in zones}


def normalize_tariff_text(text: str) -> str:
    """``normalize_document_text`` without dropping lines that repeat on a page.

    OEB tariffs repeat genuine wrapped rider tails (e.g. Hydro One's
    "customers) - effective until December 31, 2026") three or more times per page.
    """
    output: list[str] = []
    for line in (re.sub(r"\s+", " ", raw).strip() for raw in text.splitlines()):
        if not line:
            continue
        if output and not re.search(r"\d", output[-1]) and re.search(r"\d", line):
            output[-1] = f"{output[-1]} {line}"
        else:
            output.append(line)
    return "\n".join(output)


def extract_tariff_pages(pdf_bytes: bytes, minimum_characters: int = 20, y_tolerance: float = 3) -> list[DocumentPage]:
    """Extract tariff PDF pages like ``extract_pdf_pages`` but keep repeated lines; fails closed.

    ``y_tolerance`` is a per-document override for layouts whose values print offset from their labels.
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
                text = normalize_tariff_text(page.extract_text(x_tolerance=2, y_tolerance=y_tolerance) or "")
                if len(re.sub(r"\W", "", text)) >= minimum_characters:
                    pages.append(DocumentPage(number, text))
    except Exception as exc:
        logger.warning("OEB tariff PDF extraction failed closed: %s", exc)
        return []
    return pages


def residential_demand_floor(cls: Classification) -> Optional[float]:
    """kW floor of a residential class billed on a demand basis; ``None`` unless every check holds."""
    name = _norm_name(cls.name)
    if "RESIDENTIAL" not in name or "SEASONAL" in name:
        return None
    dist = [c for c in cls.charges if c.kind == "distribution"]
    if not dist or any(c.unit != "$/kW" for c in dist) or not _RES_DEMAND_BASIS_RE.search(cls.eligibility):
        return None
    m = _RES_DEMAND_FLOOR_RE.search(re.sub(r"\s+", " ", cls.eligibility))
    floor = _num(m.group(1)) if m else None
    return floor if floor is not None and floor >= 50 else None


def classify_classification(cls: Classification) -> str:
    """Categorise a classification for record builders; one of ``CLASS_CATEGORIES``.

    "residential": RESIDENTIAL / SEASONAL classes and Hydro One UR, R1, R2, AUR, AR.
    "residential_demand": a RESIDENTIAL-named class with $/kW distribution rates whose eligibility says it is
    billed on a demand basis at or above a stated kW floor (Algoma R2); built as a delivery-only demand record.
    "gs_energy": GS less than 50 kW and Hydro One UGe, GSe, AUGe, AGSe (energy-billed).
    "gs_demand": GS ranges within 50-4,999 kW and Hydro One UGd, GSd, AUGd, AGSd; open-ended GS classes
    ("GREATER THAN 50 KW", "1,000 KW AND GREATER") whose eligibility caps them below 5,000 kW or whose
    lower bound is at most 1,000 kW.
    "large_use": LARGE USE variants, and open-ended GS classes with no upper bound starting above
    1,000 kW (North Bay "GREATER THAN 3,000 KW"; they can exceed 5,000 kW). "sub_transmission": Hydro One ST.
    "excluded": lighting, unmetered, standby, generation/microFIT, embedded, storage, EV, and
    customer-specific dedicated transformer station service.
    "other": anything not recognised (callers should not build it).
    """
    name = _norm_name(cls.name)
    code = (cls.code or "").upper()
    if _EXCLUDED_CLASS_RE.search(cls.name):
        return "excluded"
    if code in _RESIDENTIAL_CODES or "RESIDENTIAL" in name or "SEASONAL" in name:
        return "residential_demand" if residential_demand_floor(cls) is not None else "residential"
    if code in _GS_ENERGY_CODES or re.match(r"GENERAL SERVICE (?:LESS THAN|UNDER|BELOW) 50 KW\b", name):
        return "gs_energy"
    if code in _GS_DEMAND_CODES:
        return "gs_demand"
    if m := _GS_RANGE_RE.match(name):
        lo, hi = (int(x.replace(",", "")) for x in m.groups())
        if lo >= 50 and hi <= 4999:
            return "gs_demand"
    if m := _GS_OPEN_RE.match(name):
        lo = _num(m.group("a") or m.group("b"))
        hi = cls.demand_max_kw
        if lo >= 50 and hi is not None and hi <= 5000:
            return "gs_demand"
        if lo >= 50 and hi is None:
            return "gs_demand" if lo <= _OPEN_GS_COMMERCIAL_MAX_FLOOR_KW else "large_use"
        return "other"
    if name.startswith("LARGE USE"):
        return "large_use"
    if name.startswith("INTERMEDIATE"):
        lo, hi = cls.demand_min_kw, cls.demand_max_kw
        return "gs_demand" if lo is not None and hi is not None and 50 <= lo < hi <= 5000 else "other"
    if code == "ST":
        return "sub_transmission"
    return "other"


def class_loss_factors(sheet: TariffSheet, cls: Classification) -> list[LossFactor]:
    """Loss factors that belong to ``cls``.

    Code-keyed tables (Hydro One "General Service - UGd 1.050", "Sub Transmission - ST ...")
    match on the class code; otherwise the OEB "< 5,000 kW" / "> 5,000 kW" split is used.
    """
    if cls.code:
        pattern = re.compile(rf"(?:^|-\s){re.escape(cls.code)}\b", re.I)
        return [lf for lf in sheet.loss_factors if pattern.search(lf.label)]
    if any(re.search(r" - [A-Z][A-Za-z0-9]{0,4}\b", lf.label) and "Loss Factor" not in lf.label
           for lf in sheet.loss_factors):
        first = _norm_name(cls.name).split(" ")[0]
        return [lf for lf in sheet.loss_factors if _norm_name(lf.label).split(" ")[0] == first]
    large_use = _norm_name(cls.name).startswith("LARGE USE")
    return [lf for lf in sheet.loss_factors
            if ("> 5,000" in lf.label) == large_use or "5,000" not in lf.label]


# ─── Record building ──────────────────────────────────────────────

def exclusion_reason(cls: Classification) -> Optional[str]:
    """Why an "excluded" class is never built (``None`` for other categories)."""
    if classify_classification(cls) != "excluded":
        return None
    if _DEDICATED_STATION_RE.search(cls.name):
        return ("Dedicated Transformer Station service: eligibility is a customer-dedicated supply station, "
                "not general facility service defined by demand size or voltage")
    if re.search(r"GENERATION|DGEN|MICRO\s*FIT|\bFIT\b|HCI|RESOP|ENERGY RESOURCE|ENERGY FROM WASTE|STORAGE",
                 cls.name, re.I):
        return "Generation, co-generation, load-displacement or storage service (out of scope)"
    return ("Lighting, unmetered, standby, embedded-distributor or EV service class "
            "(out of building-tariff scope)")


def _selected(cls: Classification, classes: Iterable[str]) -> bool:
    category = classify_classification(cls)
    if category == "excluded":
        return False
    norm = _norm_name(cls.name)
    wanted = {_norm_name(c) for c in classes}
    if norm in wanted or (cls.code and cls.code.upper() in wanted):
        return True
    if "GENERAL SERVICE 50 TO 4,999 KW" in wanted and category == "gs_demand":
        return True
    if category == "residential_demand":
        return RESIDENTIAL_DEMAND_CLASS in wanted
    return "LARGE USE" in wanted and category == "large_use"


def _st_load_path(eligibility: str) -> Optional[str]:
    """The ST "Load which: ..." eligibility path, without the embedded-LDC supply path."""
    flat = re.sub(r"\s+", " ", eligibility.replace("\u25cb", " ").replace("\u2022", " "))
    m = re.search(r"\bLoad which:\s*(?P<load>.+?\b500 kW\b.*?\)\.)\s*(?P<rest>.*)$", flat)
    if not m or not re.search(r"three-phase", m.group("load")) or not re.search(r"44 kV and 13\.8 kV", m.group("load")):
        return None
    return f"Sub Transmission (ST) load path - Load which: {m.group('load')} {m.group('rest')}".strip()


def _validate_st(cls: Classification) -> Optional[str]:
    delivery = [c for c in cls.charges if c.section == "delivery"]
    service = [c for c in delivery if c.kind == "service" and not c.conditional]
    if len(service) != 1 or service[0].unit != "$/month":
        return f"expected exactly one standard monthly ST Service Charge, found {len(service)}"
    if not [c for c in delivery if c.kind == "facility" and c.unit == "$/kW"]:
        return "no ST facility charge in $/kW"
    if [c for c in delivery if c.kind == "distribution"]:
        return "unexpected Distribution Volumetric Rate line in ST"
    network = [c for c in delivery if c.kind == "transmission_network" and not c.conditional]
    if len(network) != 1 or network[0].unit != "$/kW":
        return f"expected exactly one standard ST network service rate in $/kW, found {len(network)}"
    connection = {c.label for c in delivery if c.kind == "transmission_connection"}
    for wanted in ("Line Connection Service Rate", "Transformation Connection Service Rate"):
        if not any(label.endswith(wanted) for label in connection):
            return f"ST '{wanted}' line missing"
    if not _st_load_path(cls.eligibility):
        return "ST load-path eligibility (three-phase, 44-13.8 kV, > 500 kW) not found"
    return None


def _validate(cls: Classification) -> Optional[str]:
    if cls.code == "ST":
        reason = _validate_st(cls)
        if reason:
            return reason
        return _validate_common(cls)
    delivery = [c for c in cls.charges if c.section == "delivery"]
    checks = (
        ("service", ("$/month", "$/30 days"), "Service Charge"),
        ("distribution", ("$/kW", "$/kVA"), "Distribution Volumetric Rate"),
        ("transmission_network", ("$/kW", "$/kVA"), "Retail Transmission Rate - Network Service Rate"),
        ("transmission_connection", ("$/kW", "$/kVA"),
         "Retail Transmission Rate - Line and Transformation Connection Service Rate"),
    )
    for kind, units, label in checks:
        found = [c for c in delivery if c.kind == kind
                 and not (kind.startswith("transmission") and c.conditional)
                 and not _METER_ALT_RE.match(c.label)]
        if not found:
            found = _alternatives(delivery, kind)
            if not found:
                return f"expected exactly one standard '{label}' line, found 0"
        elif len(found) != 1 and not (kind == "transmission_connection" and _connection_pair(found)):
            return f"expected exactly one standard '{label}' line, found {len(found)}"
        bad_unit = next((c for c in found if c.unit not in units), None)
        if bad_unit is not None:
            return f"'{label}' has unit {bad_unit.unit}; expected one of {', '.join(units)}"
    return _validate_common(cls)


def _alternatives(delivery: list[TariffCharge], kind: str) -> list[TariffCharge]:
    """Published alternatives that together replace one standard line (meter type or demand size)."""
    if kind == "distribution":
        found = [c for c in delivery if c.kind == kind and _METER_ALT_RE.match(c.label)]
        keys = {_METER_ALT_RE.match(c.label).group("meter") for c in found}
    elif kind.startswith("transmission"):
        found = [c for c in delivery if c.kind == kind and (c.condition or "").startswith(_SIZE_CONDITION_PREFIX)]
        keys = {_size_range(c.label) for c in found}
    else:
        return []
    return found if len(found) >= 2 and len(keys) == len(found) else []


def _connection_pair(found: list[TariffCharge]) -> bool:
    """A separate Line + Transformation Connection pair (both charged) in place of one combined rate."""
    parts = sorted(_connection_part(c.label) or "" for c in found)
    return parts == ["Line", "Transformation"]


def _validate_common(cls: Classification) -> Optional[str]:
    for charge in cls.charges:
        if charge.kind == "rider" and charge.unit not in ("$/month", "$/30 days", "$/kW", "$/kVA", "$/kWh"):
            return f"rider '{charge.label}' has unsupported unit {charge.unit}"
        if _GARBLED_RE.search(charge.label):
            return f"garbled (overlapping) text in charge label '{charge.label[:80]}'"
        if charge.section == "delivery" and _ORPHAN_TAIL_RE.match(charge.label):
            return f"charge label starts with a wrapped tail '{charge.label[:80]}' (label reassembly failed)"
        if charge.section == "delivery" and charge.kind == "other" and not _KNOWN_OTHER_RE.match(charge.label):
            return f"unrecognised delivery charge '{charge.label[:80]}'"
    bad = [text for text in cls.unparsed if re.search(r"\$|\d\.\d", text)]
    if bad:
        return f"unparsed charge text: {bad[0][:120]}"
    return None


def _component(charge: TariffCharge, sheet: TariffSheet, cls_name: str) -> RateComponent:
    ctype, sub = {
        "service": ("fixed", "service_charge"),
        "distribution": ("demand", "distribution_volumetric"),
        "rider": ("rider", None),
        "transmission_network": ("transmission", "network_service"),
        "transmission_connection": ("transmission", "line_and_transformation_connection"),
        "regulatory": ("regulatory", None),
        "low_voltage": ("delivery", "low_voltage_service"),
        "facility": ("demand", "facility_charge") if charge.unit == "$/kW" else ("other", "facility_charge"),
        "other": ("other", None),
    }[charge.kind]
    if charge.section == "allowances" and charge.unit in ("$/kW", "$/kVA", "$/kWh") and charge.value < 0:
        ctype, sub = "rebate", "transformer_ownership_allowance"
    elif charge.kind == "other" and charge.label.startswith("Meter Charge"):
        ctype, sub = "fixed", "meter_charge"
    elif charge.kind == "other" and charge.label.startswith("Local Transformation Charge"):
        ctype, sub = "fixed", "local_transformation_charge"
    elif charge.kind == "other" and charge.label.startswith("Rural or Remote Rate Protection (RRRP) credit"):
        ctype, sub = "rebate", "rrrp_credit"
    elif charge.kind == "transmission_connection" and not charge.conditional and _connection_part(charge.label):
        sub = f"{_connection_part(charge.label).lower()}_connection"
    notes = []
    if charge.condition:
        notes.append(charge.condition if charge.condition.startswith("Conditional")
                     else f"Conditional: {charge.condition}")
    if charge.term:
        notes.append(charge.term)
    if charge.period == "30 days":
        notes.append("Published per 30 days")
    if charge.unit == "%":
        notes.append("Percentage adjustment to measured demand and energy; not a dollar charge")
    if charge.unit == "$/km":
        notes.append("Per kilometre of line per month")
    if charge.label.startswith("Local Transformation Charge"):
        notes.append("Per transformer per month")
    zone = f" {sheet.rate_zone}," if sheet.rate_zone else ""
    case = f"{sheet.case_number}," if sheet.case_number else "OEB tariff,"
    return RateComponent(
        component_type=ctype,
        component_name=charge.label,
        charge_value=charge.value,
        charge_unit=charge.unit,
        demand_unit=charge.unit.split("/")[-1] if charge.unit in ("$/kW", "$/kVA") else None,
        sub_component=sub,
        effective_date=sheet.effective_date,
        end_date=charge.end_date,
        source_url=sheet.source_url,
        source_detail=f"PDF page {charge.page_number} ({case}{zone} "
                      f"{cls_name} {charge.section})",
        confidence="high",
        notes="; ".join(notes) or None,
    )


def _allowance_applies(charge: TariffCharge, cls: Classification) -> bool:
    if re.search(r"\bEnergy Billed\b", charge.label):
        return False  # demand records only
    if cls.code == "ST" and re.search(r"\bnon-ST\b", charge.condition or ""):
        return False
    refs = _CLASS_REF_RE.findall(charge.label)
    if not refs:
        return True
    target = _norm_name(cls.name)
    for ref in refs:
        ref_norm = _norm_name(ref)
        if ref_norm == target or (ref_norm == "LARGE USE" and target.startswith("LARGE USE")
                                  and "DEDICATED" not in target):
            return True
    return False


def _class_title(name: str) -> str:
    words = []
    for word in name.split():
        upper = word.upper()
        words.append("kW" if upper == "KW" else "to" if upper == "TO" else word.capitalize())
    return " ".join(words)


def _cls_title(cls: Classification) -> str:
    if cls.code:
        return f"{_class_title(cls.name.rsplit(' - ', 1)[0])} ({cls.code})"
    return _class_title(cls.name)


def _tariff_code(name: str, code: Optional[str] = None,
                 bounds: tuple[Optional[float], Optional[float]] = (None, None)) -> str:
    if code:
        return code
    norm = _norm_name(name)
    if norm.startswith("INTERMEDIATE") and None not in bounds:
        lo, hi = bounds
        return f"GS {lo:,.0f}-{hi - 1 if hi % 10 == 0 else hi:,.0f} kW"
    if m := _GS_RANGE_RE.match(norm):
        return f"GS {m.group(1)}-{m.group(2)} kW"
    if m := _GS_OPEN_RE.match(norm):
        return f"GS {m.group('a') or m.group('b')}+ kW"
    return "LU" if norm == "LARGE USE" else re.sub(r"[^A-Z0-9]+", "-", norm).strip("-")


def build_demand_records(
    sheet: TariffSheet,
    utility_name: str,
    province: str = "ON",
    classes: Sequence[str] = DEFAULT_DEMAND_CLASSES,
    today: Union[date, str, None] = None,
) -> list[TariffRecord]:
    """Build delivery-only demand-billed records, failing closed per classification.

    Selected classes are GS 50-4,999 kW (plus any published GS sub-ranges between
    50 and 4,999 kW, and Hydro One UGd/GSd/AUGd/AGSd), Large Use variants and the
    Hydro One Sub Transmission (ST) load path. ``classes`` may also name class codes
    (e.g. ``("UGd",)``). Excluded service classes are never built, even if requested.
    Reasons for rejected classes are stored in ``sheet.rejections``.
    """
    as_of = _today_iso(today) if today is not None else sheet.today
    if sheet.errors:
        for cls in sheet.classifications:
            if _selected(cls, classes):
                sheet.rejections[cls.name] = "sheet error: " + "; ".join(sheet.errors)
        logger.warning("OEB tariff %s rejected: %s", sheet.source_url, "; ".join(sheet.errors))
        return []
    if not sheet.effective_date or sheet.effective_date > as_of:
        sheet.rejections["*"] = f"effective date {sheet.effective_date} missing or after {as_of}"
        return []
    if sheet.implementation_date and sheet.implementation_date > as_of:
        sheet.rejections["*"] = f"implementation date {sheet.implementation_date} after {as_of}"
        return []

    records: list[TariffRecord] = []
    for cls in sheet.classifications:
        if reason := exclusion_reason(cls):
            sheet.exclusions[cls.name] = reason
        if (cls.charges and classify_classification(cls) == "other" and _IN_SCOPE_NAME_RE.search(cls.name)
                and cls.name not in sheet.rejections):
            sheet.rejections[cls.name] = ("unrecognised in-scope classification (name/demand range not mapped to a "
                                          "supported class); not built")
            logger.warning("OEB tariff %s %s not recognised; rejected", sheet.distributor, cls.name)
            continue
        if not _selected(cls, classes):
            continue
        reason = _validate(cls)
        if reason:
            sheet.rejections[cls.name] = reason
            logger.warning("OEB tariff %s %s rejected: %s", sheet.distributor, cls.name, reason)
            continue
        sub_transmission = cls.code == "ST"
        eligibility = _st_load_path(cls.eligibility) if sub_transmission else cls.eligibility
        demand_min, demand_max = cls.demand_min_kw, cls.demand_max_kw
        if sub_transmission:
            demand_min, demand_max, _ = _demand_bounds(eligibility)
        category = classify_classification(cls)
        residential_demand = category == "residential_demand"
        if residential_demand:
            demand_min, demand_max = residential_demand_floor(cls), None
        expired = [c for c in cls.charges if c.end_date and c.end_date < as_of]
        live = [c for c in cls.charges if c not in expired]
        components = [_component(c, sheet, cls.name) for c in live]
        components += [_component(a, sheet, cls.name) for a in sheet.allowances
                       if _allowance_applies(a, cls)]
        large_use = category in ("large_use", "sub_transmission")
        notes = [COMMODITY_NOTE]
        if sub_transmission:
            notes.append(ST_LOAD_NOTE)
        if residential_demand:
            notes.append(f"Residential service billed on a demand basis ({demand_min:,.0f} kW and above), "
                         "published as a residential classification; RPP commodity prices are not applied.")
        if sheet.case_number:
            notes.append(f"OEB case {sheet.case_number}.")
        if sheet.implementation_date and sheet.implementation_date != sheet.effective_date:
            notes.append(f"Rates effective {sheet.effective_date}, implemented {sheet.implementation_date}.")
        notes.append("Regulatory-component charges do not apply to embedded wholesale market participants.")
        notes.extend(cls.notes)
        if _GS_OPEN_RE.match(_norm_name(cls.name)) and demand_max is None:
            notes.append("The tariff publishes no upper demand bound for this class; it also covers loads of "
                         "5,000 kW and above.")
        notes.extend(f"Tariff note {key}: {text}" for key, text in sheet.footnotes.items()
                     if not cls.code and "Billing Demand" in text)
        notes.extend(n for n in sheet.notes if n.startswith("Gross Load Billing Note:"))
        if sub_transmission:
            notes.extend(n for n in sheet.notes if re.search(r"\bST customers\b", n))
        losses = class_loss_factors(sheet, cls)
        if sub_transmission:
            notes.append("Published ST loss factors are for embedded delivery points (LDC supply path) and "
                         "are not listed here; loss factors and connection rates for a load customer follow "
                         "its connection agreement (tariff Note 7).")
        elif losses:
            notes.append("Published total loss factors (multiply metered energy for commodity and "
                         "some charges; not applied here): "
                         + "; ".join(f"{lf.label} {lf.value}" for lf in losses) + ".")
        if expired:
            notes.append("Expired riders omitted: " + "; ".join(c.label for c in expired) + ".")
        notes.append("Standby, embedded-distributor, generation, unmetered and lighting classes excluded.")
        zone = f"{sheet.rate_zone} - " if sheet.rate_zone else ""
        if residential_demand:
            short = re.sub(r"^RESIDENTIAL\s*-?\s*", "", _norm_name(cls.name)) or "RES"
            code = f"{short} {demand_min:,.0f}+ kW"
        else:
            code = _tariff_code(cls.name, cls.code, (demand_min, demand_max))
        records.append(TariffRecord(
            utility_name=utility_name,
            province=province,
            utility_type="electricity",
            tariff_name=f"{zone}{_cls_title(cls)} (delivery only)",
            tariff_code=code,
            customer_class="residential" if residential_demand else "industrial" if large_use else "commercial",
            sub_class=sheet.rate_zone,
            description=f"OEB-approved {_cls_title(cls)} Service Classification delivery and regulatory "
                        f"charges ({sheet.distributor}).",
            eligibility=eligibility[:1500] or None,
            demand_min_kw=demand_min,
            demand_max_kw=demand_max,
            rate_structure="demand",
            pricing_method="regulated",
            effective_date=sheet.effective_date,
            source_url=sheet.source_url,
            source_page=f"PDF pages {cls.pages[0]}-{cls.pages[-1]}" if len(cls.pages) > 1
            else f"PDF page {cls.pages[0]}",
            confidence="high",
            notes=" ".join(notes),
            components=components,
        ))
    return records
