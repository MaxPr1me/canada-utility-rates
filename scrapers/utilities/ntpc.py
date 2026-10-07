"""
ntpc.py — Scraper for Northwest Territories Power Corporation electricity rates (NT).

The Northwest Territories Power Corporation (NTPC) is a Crown
corporation that generates and distributes electricity across the
Northwest Territories.  NTPC operates in multiple rate zones that
reflect the dramatically different generation costs across this vast
territory:

  - **Hydro zones** (Yellowknife, Hay River, and surrounding areas)
    use hydroelectric generation from the Snare and Taltson river
    systems.  Rates here are lower but still well above southern
    Canadian averages.

  - **Thermal / diesel zones** (most smaller communities) rely on
    trucked-in diesel fuel for generation.  These communities have
    some of the highest electricity rates in Canada, with tail-block
    rates exceeding $1.00/kWh.

The NWT government operates a Territorial Power Support Program (TPSP)
that subsidises residential electricity costs in high-cost communities,
effectively equalising the first block of residential consumption
across zones.

Regulated by the Public Utilities Board of the Northwest Territories
(PUB NWT).

Official sources (live parser):
  - PUB-approved rate schedule PDF, linked as the current schedule from
    https://www.ntpc.com/node/796 (residential and general service,
    government and non-government, by zone/community).
  - Residential Electrical Rates page (TPSP first-block price, GNWT Cost of
    Living Subsidy and rider cross-check):
    https://www.ntpc.com/customer-service/residential-service/residential-electrical-rates
  - TPSP and rider-explanation pages for subsidy eligibility.
  - PUB-approved Terms and Conditions of Service (Schedule "D") for the
    conditional Taltson retail interruptible heating rate on schedule page 20.

NTPC does not retail power in Yellowknife (Naka Power does), so the legacy
"Yellowknife Zone" seeds have no live NTPC equivalent and are only emitted when
the whole live parse fails.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages

logger = logging.getLogger(__name__)

UTILITY_NAME = "Northwest Territories Power Corporation"
RESIDENTIAL_URL = "https://www.ntpc.com/customer-service/residential-service/residential-electrical-rates"
SCHEDULE_INDEX_URL = "https://www.ntpc.com/node/796"
TPSP_URL = "https://www.ntpc.com/customer-service/territorial-power-support-program-tpsp"
RIDER_URL = "https://www.ntpc.com/node/976"
TERMS_URL = ("https://www.ntpc.com/sites/default/files/2026-05/"
             "Terms%20and%20Conditions%20of%20Service%20-%20Approved%20-%20February%201%2C%202026.pdf")
DIESEL_RESIDENTIAL_NAME = "Residential Service — Diesel Zone"
INTERRUPTIBLE_NAME = "Interruptible Energy For Heating – Retail (Taltson: Fort Smith/Fort Resolution)"

# canonical key -> (rate-schedule label prefix, residential-page label prefix, display name, rider-page heading)
RIDERS = {
    "stabilization": ("nwt stabilization fund rate rider", "nwt stabilization", "NWT Stabilization Fund Rate Rider", None),
    "misc": ("misc. deferral transfers rider", "misc. deferral transfers", "Misc. Deferral Transfers Rider",
             "MISCELLANEOUS DEFERRAL ACCOUNT TRANSFERS RIDER"),
    "sunk": ("sunk cost deferral account rider", "sunk cost deferral account", "Sunk Cost Deferral Account Rider",
             "SUNK COST DEFERRAL ACCOUNT RIDER"),
    "gra": ("gra shortfall rider", "gra shortfall", "GRA Shortfall Rider", "GRA SHORTFALL RIDER"),
}
COL_HEADING = "GNWT COST OF LIVING SUBSIDY"
ZONES = {"Snare System": "Snare Zone", "Thermal": "Thermal Zone", "Norman Wells": "Norman Wells Zone",
         "Taltson System": "Taltson Zone"}
BLOCK_RE = re.compile(r"(Residential|General Service) (Government|Non-Government)\b")
EFFECTIVE_RE = re.compile(r"Effective Date:\s*([A-Z][a-z]+\s+\d{1,2},\s*\d{4})")
CENTS = r"(-?\d+(?:\.\d+)?)\s*¢/kWh"
VALUE_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*cents?\s*/\s*kWh", re.I)
RATCHET_RE = re.compile(
    r"Billing Demand shall be the greater of the current month.s maximum Demand or the maximum Demand"
    r"\s+experienced during the 12 month period ending with the current billing\s+month")
NO_STABILIZATION_RE = re.compile(r"NWT Stabilization rider does not apply to Hay River")
MISC_ONLY_RE = re.compile(r"Miscellaneous Deferral Account Transfers only applies to Hay River")
HAY_RIVER = "Hay River"
SEASON_MONTHS = {"September 1 to March 31": "9,10,11,12,1,2,3", "April 1 to August 31": "4,5,6,7,8"}
INTERRUPTIBLE_HEAD_RE = re.compile(r"Interruptible Energy For Heating\s*[-–—]\s*(Retail|Wholesale)")
TERMS_EFFECTIVE_RE = re.compile(r"TERMS & CONDITIONS OF SERVICE Effective Date:\s*([A-Z][a-z]+\s+\d{1,2},\s*\d{4})")
TERMS_APPROVED = "have been approved by the Public Utilities Board of the Northwest Territories"
SCHEDULE_D_RE = re.compile(r"SCHEDULE \"D\" INTERRUPTIBLE ENERGY FOR HEATING:\s*TALTSON RETAIL")
SCHEDULE_E_RE = re.compile(r"SCHEDULE \"E\" INTERRUPTIBLE ENERGY FOR HEATING")
# Schedule "D" sentences that define eligibility; any wording change omits the record.
SCHEDULE_D_QUOTES = {
    "available": "Interruptible energy is available to general service and industrial customers in Fort Smith and "
                 "Fort Resolution from time to time for heating.",
    "surplus": "The availability of interruptible energy is determined by the Northwest Territories Power "
               "Corporation (NTPC) based on the availability of surplus hydro capacity.",
    "new_loads": "The rate is only available to new interruptible loads in areas where there is sufficient surplus "
                 "distribution system capacity at the time of connection.",
    "separate": "The interruptible energy is provided on a separate service that is fully interruptible at the "
                "request of NTPC.",
    "incremental": "The customer must satisfy NTPC that the interruptible electricity use is in excess of the "
                   "customer's firm electricity consumption and represents incremental usage displacing an "
                   "alternative fuel source by an appliance installed primarily to provide heat.",
    "backup": "A viable alternative fuel source is available to the customer, capable of providing the same quantity "
              "of heating in the event of electricity interruptions of unlimited duration.",
    "notice": "Customers will not be permitted to have interruptible electricity loads shifted to firm electric "
              "service without providing NTPC 12 months notice, unless waived at NTPC's discretion.",
    "no_return": "Once any interruptible electricity load is switched to firm service, it will not be able to switch "
                 "back to interruptible electricity service in the future.",
    "rate": "The interruptible energy charge shall be the published rate filed and approved by the NWT Public "
            "Utilities Board from time to time.",
    "applied": "The interruptible energy charge for any rate period shall be applied to all interruptible energy "
               "kW.h consumed in each month during that rate period.",
    "interruptions": "There shall be no limits on the frequency or duration of interruptions in the supply of "
                     "electricity for heating purposes which NTPC may cause.",
    "install": "The customer will be responsible for any cost of installing the separate service, including all "
               "necessary equipment and upgrades, metering devices and any required remote interruption equipment.",
}


class _Reject(ValueError):
    """A source block is incomplete or ambiguous and must not become a live record."""


@dataclass
class _Block:
    zone: str
    klass: str
    owner: str
    page: int
    fixed: Optional[float] = None
    demand: Optional[float] = None
    minimum: Optional[float] = None
    standby: Optional[float] = None
    energy: dict[str, float] = field(default_factory=dict)
    riders: dict[str, float] = field(default_factory=dict)


@dataclass
class _Schedule:
    url: str
    effective: str
    blocks: list[_Block]
    ratchet: Optional[str]
    taltson_rules: bool


@dataclass
class _PageGroup:
    zone: str
    heading: str
    service_fee: Optional[float] = None
    first_block_kwh: Optional[int] = None
    tpsp_your: Optional[float] = None
    tpsp_actual: Optional[float] = None
    energy: Optional[float] = None
    riders: dict[str, float] = field(default_factory=dict)
    col: dict[str, float] = field(default_factory=dict)
    save: Optional[float] = None
    will_pay: Optional[float] = None


@dataclass
class _ResidentialPage:
    url: str
    effective: str
    groups: dict[str, _PageGroup]


@dataclass
class _Interruptible:
    url: str
    effective: str
    page: int
    cents: float


@dataclass
class _ScheduleD:
    url: str
    effective: str
    pages: list[int]
    quotes: dict[str, str]


def _flat(text: str) -> str:
    text = text.translate(str.maketrans({"“": '"', "”": '"', "’": "'", "‘": "'"}))
    return re.sub(r"\s+", " ", text).strip()


def _norm(name: str) -> str:
    text = name.replace("ı", "i").replace("ł", "l").replace("Ł", "L")
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return re.sub(r"[^a-z]", "", text.lower())


def _iso(text: str) -> str:
    return datetime.strptime(re.sub(r"\s+", " ", text.strip()), "%B %d, %Y").date().isoformat()


def _dollars_per_kwh(cents: float) -> float:
    return round(cents / 100, 6)


def _content(html: str) -> Tag:
    soup = BeautifulSoup(html or "", "html.parser")
    return soup.find(id="entryContent") or soup


def _rider_key(label: str, position: int) -> Optional[str]:
    label = label.lower().lstrip("- ").strip()
    return next((key for key, spec in RIDERS.items() if label.startswith(spec[position])), None)


# ── Official-source parsers (pure functions, fixture-testable) ─────

def parse_schedule_index(html: str, today: str) -> tuple[str, str]:
    """Return (current schedule PDF URL, effective ISO date) listed above "Past Rate Schedules"."""
    content = _content(html)
    current: list[tuple[str, str]] = []
    for element in content.find_all(["a", "h2", "h3"]):
        if element.name != "a":
            if "past rate schedules" in element.get_text(" ", strip=True).lower():
                break
            continue
        href = element.get("href") or ""
        if href.lower().split("?")[0].endswith(".pdf"):
            current.append((urljoin(SCHEDULE_INDEX_URL, href), element.get_text(" ", strip=True)))
    if len(current) != 1:
        raise _Reject(f"expected one current rate schedule link, found {len(current)}")
    url, label = current[0]
    match = re.fullmatch(r"([A-Z][a-z]+ \d{1,2}, \d{4}) Rate Schedule", re.sub(r"\s+", " ", label))
    if not match:
        raise _Reject(f"unrecognised current schedule label {label!r}")
    effective = _iso(match.group(1))
    if effective > today:
        raise _Reject(f"current schedule {effective} is in the future")
    return url, effective


def _parse_block(zone: str, klass: str, owner: str, body: str, page: int) -> _Block:
    block = _Block(zone, klass, owner, page)
    in_energy = False
    for line in (line.strip() for line in body.splitlines()):
        if not line:
            continue
        if match := re.fullmatch(r"Monthly Service Charge:?\s*\$(\d+\.\d{2})", line):
            block.fixed = float(match.group(1))
        elif match := re.fullmatch(r"Demand Charge:\s*\$(\d+\.\d{2})\s*/kW", line):
            block.demand = float(match.group(1))
        elif match := re.fullmatch(r"Energy Charge:\s*" + CENTS, line):
            block.energy[""] = float(match.group(1))
        elif match := re.fullmatch(r"Minimum Monthly Bill:\s*\$(\d+\.\d{2})", line):
            block.minimum, in_energy = float(match.group(1)), False
        elif match := re.fullmatch(r"Stand-by[- ]Charge:\s*\$(\d+\.\d{2})\s*/kW", line):
            block.standby = float(match.group(1))
        elif (match := re.fullmatch(r"(.+?):\s*" + CENTS, line)) and _rider_key(match.group(1), 0):
            key = _rider_key(match.group(1), 0)
            if key in block.riders:
                raise _Reject(f"duplicate {key} rider")
            block.riders[key] = float(match.group(2))
        elif (match := re.fullmatch(r"(?:Energy Charge\s+)?([^\d:$¢]+?)\s+" + CENTS, line)) and (
                line.startswith("Energy Charge ") or in_energy):
            community = re.sub(r"\s+", " ", match.group(1)).strip()
            if community in block.energy:
                raise _Reject(f"duplicate energy charge for {community}")
            block.energy[community], in_energy = float(match.group(2)), True
        elif "$" in line or "¢" in line:
            raise _Reject(f"unrecognised charge line {line!r}")
    if klass == "Residential" and (block.fixed is None or block.demand is not None):
        raise _Reject("residential block needs a monthly service charge and no demand charge")
    if klass == "General Service" and (block.demand is None or block.fixed is not None):
        raise _Reject("general service block needs a demand charge and no service charge")
    if block.minimum is None or not block.energy:
        raise _Reject("missing minimum monthly bill or energy charge")
    if (owner == "Non-Government") != (set(block.energy) == {""}):
        raise _Reject("energy charge layout does not match the government/non-government class")
    required = {"stabilization", "sunk", "gra"} | ({"misc"} if zone == "Taltson System" else set())
    if set(block.riders) != required:
        raise _Reject(f"rider set {sorted(block.riders)} != {sorted(required)}")
    return block


def parse_schedule(pages: list[DocumentPage], url: str, today: str) -> _Schedule:
    """Parse residential and general-service blocks of the PUB-approved rate schedule.

    Wholesale, Con Mine, streetlighting and interruptible-heating pages carry no
    residential/general-service header and are ignored. A malformed block is
    rejected on its own; date conflicts reject the whole document.
    """
    dates = {_iso(value) for page in pages for value in EFFECTIVE_RE.findall(page.text)}
    if len(dates) != 1:
        raise _Reject(f"expected one schedule effective date, found {sorted(dates)}")
    effective = dates.pop()
    if effective > today:
        raise _Reject(f"schedule effective {effective} is in the future")
    blocks: list[_Block] = []
    zone: Optional[str] = None
    for page in pages:
        if match := re.search(r"^Zone:\s*(.+)$", page.text, re.M):
            zone = match.group(1).strip()
        elif "Rate Schedule:" in page.text:
            zone = None
        heads = list(BLOCK_RE.finditer(page.text))
        for index, head in enumerate(heads):
            end = heads[index + 1].start() if index + 1 < len(heads) else len(page.text)
            try:
                if zone not in ZONES:
                    raise _Reject(f"unknown zone {zone!r}")
                blocks.append(_parse_block(zone, head.group(1), head.group(2), page.text[head.end():end],
                                           page.page_number))
            except _Reject as exc:
                logger.warning("NTPC %s %s block on page %d rejected: %s",
                               head.group(1), head.group(2), page.page_number, exc)
    text = "\n".join(page.text for page in pages)
    ratchet = RATCHET_RE.search(text)
    return _Schedule(
        url=url, effective=effective, blocks=blocks,
        ratchet=re.sub(r"\s+", " ", ratchet.group(0)) + "." if ratchet else None,
        taltson_rules=bool(NO_STABILIZATION_RE.search(text) and MISC_ONLY_RE.search(text)),
    )


def _page_zone(heading: str) -> Optional[str]:
    key = _norm(heading)
    for token, zone in (("thermal", "Thermal"), ("normanwells", "Norman Wells"),
                        ("behchoko", "Snare System"), ("hayriver", "Taltson System")):
        if token in key:
            return zone
    return None


def _values(cell: Tag) -> list[float]:
    return [float(value) for value in VALUE_RE.findall(cell.get_text(" ", strip=True))]


def _parse_group(zone: str, heading: str, table: Tag, prose: str) -> _PageGroup:
    group = _PageGroup(zone, heading)
    section = None
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 3:
            raise _Reject("residential table row without label/your-cost/actual-cost cells")
        label = re.sub(r"\s+", " ", cells[0].get_text(" ", strip=True)).lower().lstrip("- ").strip()
        yours, actual = _values(cells[1]), _values(cells[2])
        if label == "service fee":
            fees = [re.findall(r"\$\s*(\d+(?:\.\d+)?)", cell.get_text(" ")) for cell in cells[1:]]
            if fees[0] != fees[1] or len(fees[0]) != 1:
                raise _Reject("service fee columns disagree")
            group.service_fee = float(fees[0][0])
        elif match := re.fullmatch(r"up to ([\d,]+) kwh", label):
            section, group.first_block_kwh = "first", int(match.group(1).replace(",", ""))
        elif label.startswith("each additional"):
            section = "additional"
        elif label.startswith("energy charge"):
            if len(yours) != 1 or len(actual) != 1:
                raise _Reject("energy charge row needs one value per column")
            if section == "first":
                group.tpsp_your, group.tpsp_actual = yours[0], actual[0]
            elif yours != actual or group.energy is not None:
                raise _Reject("energy charge columns disagree or repeat")
            else:
                group.energy = actual[0]
        elif "cost of living subsidy" in label:
            names = [name.strip() for name in label.split("subsidy", 1)[1].split(" - ") if name.strip()] or [""]
            if yours != actual or len(actual) != len(names):
                raise _Reject("cost of living subsidy values do not align with their communities")
            group.col = dict(zip(names, actual))
        elif key := _rider_key(label, 1):
            if len(yours) != 1 or yours != actual or key in group.riders:
                raise _Reject(f"{key} rider columns disagree or repeat")
            group.riders[key] = actual[0]
        elif yours or actual:
            raise _Reject(f"unrecognised residential row {label!r}")
    if group.service_fee is None or group.energy is None:
        raise _Reject("missing service fee or energy charge")
    if (group.tpsp_your is None) != (group.first_block_kwh is None):
        raise _Reject("first-block section without a first-block energy price")
    if match := re.search(r"save \$\s*([\d,]+\.\d{2})", prose):
        group.save = float(match.group(1).replace(",", ""))
    if match := re.search(r"will pay (\d+(?:\.\d+)?) cents per kWh", prose):
        group.will_pay = float(match.group(1))
    return group


def parse_residential_page(html: str, today: str) -> _ResidentialPage:
    """Parse the residential page's per-zone "Your cost"/"Actual cost" tables."""
    content = _content(html)
    match = re.search(r"Effective ([A-Z][a-z]+ \d{1,2}, \d{4})", content.get_text(" ", strip=True))
    if not match:
        raise _Reject("residential page has no effective date")
    effective = _iso(match.group(1))
    if effective > today:
        raise _Reject(f"residential page effective {effective} is in the future")
    groups: dict[str, _PageGroup] = {}
    for heading in content.find_all("h3"):
        zone = _page_zone(heading.get_text(" ", strip=True))
        if not zone:
            continue
        table, prose = None, []
        for sibling in heading.next_siblings:
            if not isinstance(sibling, Tag):
                continue
            if sibling.name == "h3":
                break
            if table is None and (found := sibling if sibling.name == "table" else sibling.find("table")):
                table = found
            elif sibling.name != "table":
                prose.append(sibling.get_text(" ", strip=True))
        try:
            if table is None or zone in groups:
                raise _Reject("missing or duplicate zone table")
            groups[zone] = _parse_group(zone, heading.get_text(" ", strip=True), table,
                                        re.sub(r"\s+", " ", " ".join(prose)))
        except _Reject as exc:
            logger.warning("NTPC residential page group %r rejected: %s", heading.get_text(strip=True), exc)
    return _ResidentialPage(RESIDENTIAL_URL, effective, groups)


def parse_tpsp(html: str) -> dict[str, int]:
    """Return {season: first-block kWh} from the TPSP page; both seasons are required."""
    text = re.sub(r"\s+", " ", _content(html).get_text(" ", strip=True))
    seasons = {}
    for season in SEASON_MONTHS:
        match = re.search(re.escape(season) + r".{0,200}?first ([\d,]+) kilowatt hours", text)
        if not match:
            raise _Reject(f"TPSP page lacks the {season} first-block threshold")
        seasons[season] = int(match.group(1).replace(",", ""))
    if "residential customers" not in text.lower():
        raise _Reject("TPSP page lacks its residential eligibility statement")
    return seasons


def parse_rider_page(html: str) -> dict[str, str]:
    """Return {upper-case heading: summary paragraphs} from the rider explanation page."""
    content = _content(html)
    sections: dict[str, str] = {}
    for heading in content.find_all("h2"):
        parts = []
        for sibling in heading.find_next_siblings():
            if sibling.name == "h2":
                break
            parts.append(sibling.get_text(" ", strip=True))
        sections[re.sub(r"\s+", " ", heading.get_text(" ", strip=True)).upper()] = re.sub(
            r"\s+", " ", " ".join(parts)).strip()
    return sections


def _schedule_component(schedule: _Schedule, block: _Block, ctype: str, name: str, value: float, unit: str,
                        **extra) -> RateComponent:
    return RateComponent(
        component_type=ctype, component_name=name, charge_value=value, charge_unit=unit,
        effective_date=schedule.effective, source_url=schedule.url,
        source_detail=f"PDF page {block.page}, Zone: {block.zone}, {block.klass} {block.owner}",
        confidence="high", **extra,
    )


def _rider_applies(key: str, zone: str, communities: list[str]) -> bool:
    if zone != "Taltson System":
        return True
    if key == "stabilization":
        return HAY_RIVER not in communities
    if key == "misc":
        return communities == [HAY_RIVER]
    return True


def _base_components(schedule: _Schedule, block: _Block, energy: float, communities: list[str],
                     rider_notes: dict[str, str]) -> list[RateComponent]:
    components: list[RateComponent] = []
    if block.fixed is not None:
        components.append(_schedule_component(schedule, block, "fixed", "Monthly Service Charge", block.fixed,
                                              "$/month"))
    if block.demand is not None:
        components.append(_schedule_component(
            schedule, block, "demand", "Demand Charge", block.demand, "$/kW", demand_unit="kW",
            notes="Per kW of monthly Billing Demand. " + (schedule.ratchet or "")))
    components.append(_schedule_component(schedule, block, "energy", "Energy Charge", _dollars_per_kwh(energy),
                                          "$/kWh"))
    for key, (_, _, display, heading) in RIDERS.items():
        if key in block.riders and _rider_applies(key, block.zone, communities):
            components.append(_schedule_component(
                schedule, block, "rider", display, _dollars_per_kwh(block.riders[key]), "$/kWh",
                notes=rider_notes.get(heading or "") or None))
    return components


def _page_subsidies(schedule: _Schedule, block: _Block, communities: list[str], page: Optional[_ResidentialPage],
                    tpsp: Optional[dict[str, int]], rider_notes: dict[str, str]) -> tuple[list[RateComponent], list[str]]:
    """Return conditional GNWT credits for a non-government residential record, or notes explaining omissions."""
    group = page.groups.get(block.zone) if page else None
    if group is None:
        return [], ["GNWT subsidies not stored: the residential rates page for this zone was unavailable or rejected."]
    energy = block.energy[""]
    if (group.service_fee != block.fixed or group.energy != energy or group.riders != block.riders):
        return [], ["GNWT subsidies not stored: the residential rates page does not match the approved schedule."]
    col_key = next((key for key in group.col
                    if {_norm(part) for part in key.split("/")} == {_norm(c) for c in communities}), None)
    if col_key is None and set(group.col) == {""}:
        col_key = ""
    if group.will_pay is not None:
        applicable = sum(value for key, value in block.riders.items()
                         if _rider_applies(key, block.zone, communities))
        total = energy + applicable + (group.col[col_key] if col_key is not None else 0)
        if round(total, 2) != group.will_pay:
            return [], ["GNWT subsidies not stored: published per-kWh price above 1,000 kWh does not reconcile."]
    detail = f"Residential Electrical Rates page, {group.heading} table (Effective {page.effective})"
    components: list[RateComponent] = []
    notes: list[str] = []
    if col_key is not None and COL_HEADING in rider_notes:
        components.append(RateComponent(
            component_type="rebate", component_name="GNWT Cost of Living Subsidy",
            charge_value=_dollars_per_kwh(group.col[col_key]), charge_unit="$/kWh",
            effective_date=page.effective, source_url=page.url, source_detail=detail, confidence="high",
            notes=("Conditional GNWT-funded bill credit, not part of the approved base rate. "
                   f"Rider explanation page: {rider_notes[COL_HEADING]}"
                   + (" The residential page lists it under 'Each additional kWh' and does not state whether it "
                      "also applies within the TPSP first block." if group.tpsp_your is not None else "")),
        ))
    elif col_key is not None:
        notes.append("GNWT Cost of Living Subsidy not stored: its eligibility page was unavailable.")
    else:
        notes.append("No GNWT Cost of Living Subsidy is published for this zone on the residential rates page.")
    if group.tpsp_your is None:
        notes.append("No TPSP first-block price is published for this zone on the residential rates page.")
    elif (tpsp is None or group.tpsp_actual != energy or group.save is None
          or round((group.tpsp_actual - group.tpsp_your) * group.first_block_kwh / 100, 2) != group.save
          or tpsp.get("September 1 to March 31") != group.first_block_kwh):
        notes.append("TPSP first-block credit not stored: the published 'Your cost' price and stated monthly "
                     "saving do not reconcile, or the TPSP threshold page was unavailable.")
    else:
        for season, kwh in tpsp.items():
            components.append(RateComponent(
                component_type="energy",
                component_name=f"GNWT TPSP Subsidised First-Block Energy Price ({season})",
                charge_value=_dollars_per_kwh(group.tpsp_your), charge_unit="$/kWh", tier_number=1,
                tier_threshold=kwh, tier_unit="kWh", season=season, season_months=SEASON_MONTHS[season],
                effective_date=page.effective, source_url=page.url,
                source_detail=f"{detail}; TPSP page {TPSP_URL}", confidence="high",
                notes=(f"Conditional alternative, not an additional charge: for eligible residential household "
                       f"accounts (one TPSP account per customer) the first {kwh:,} kWh per month from {season} "
                       f"are billed at this published 'Your cost' price instead of the base energy charge of "
                       f"{group.tpsp_actual:.2f} cents/kWh. Cross-checked with NTPC's stated "
                       f"${group.save:,.2f} saving at 1,000 kWh. Riders are not stated to be reduced."),
            ))
    return components, notes


def build_records(schedule: _Schedule, page: Optional[_ResidentialPage] = None,
                  tpsp: Optional[dict[str, int]] = None, rider_notes: Optional[dict[str, str]] = None) -> list[TariffRecord]:
    """Build one record per published zone/community group and class from the parsed sources."""
    rider_notes = rider_notes or {}
    keyed: dict[tuple[str, str, str], list[_Block]] = {}
    for block in schedule.blocks:
        keyed.setdefault((block.zone, block.klass, block.owner), []).append(block)
    zone_communities: dict[str, list[str]] = {}
    for (zone, _, owner), blocks in keyed.items():
        if owner == "Government" and len(blocks) == 1:
            zone_communities.setdefault(zone, list(blocks[0].energy))
    records: list[TariffRecord] = []
    for (zone, klass, owner), blocks in keyed.items():
        if len(blocks) != 1:
            logger.warning("NTPC duplicate %s %s block for %s rejected", klass, owner, zone)
            continue
        block = blocks[0]
        if klass == "General Service" and not schedule.ratchet:
            logger.warning("NTPC general service billing-demand definition missing; %s rejected", zone)
            continue
        if zone == "Taltson System" and not schedule.taltson_rules:
            logger.warning("NTPC Taltson Hay River rider applicability notes missing; %s %s rejected", klass, owner)
            continue
        if owner == "Government":
            groups = [([community], block.energy[community]) for community in block.energy]
        else:
            communities = zone_communities.get(zone)
            if not communities:
                logger.warning("NTPC %s communities unknown; %s non-government rejected", zone, klass)
                continue
            if zone == "Taltson System":
                if HAY_RIVER not in communities:
                    logger.warning("NTPC Taltson Hay River not listed; %s non-government rejected", klass)
                    continue
                others = [community for community in communities if community != HAY_RIVER]
                groups = [([HAY_RIVER], block.energy[""]), (others, block.energy[""])]
            else:
                groups = [(communities, block.energy[""])]
        for communities, energy in groups:
            records.append(_record(schedule, block, communities, energy, page, tpsp, rider_notes))
    return records


def _record(schedule: _Schedule, block: _Block, communities: list[str], energy: float,
            page: Optional[_ResidentialPage], tpsp: Optional[dict[str, int]],
            rider_notes: dict[str, str]) -> TariffRecord:
    zone_label = ZONES[block.zone]
    residential = block.klass == "Residential"
    government = block.owner == "Government"
    place = "/".join(communities)
    if government:
        name = f"{'Residential Service' if residential else 'General Service'} Government — {place} ({zone_label})"
    elif residential and block.zone == "Thermal":
        name = DIESEL_RESIDENTIAL_NAME
    else:
        name = f"{'Residential Service' if residential else 'General Service'} — {zone_label}"
        if block.zone == "Taltson System":
            name += f" ({place})"
    components = _base_components(schedule, block, energy, communities, rider_notes)
    notes = [f"PUB-approved NTPC rate schedule effective {schedule.effective}, {block.zone} zone "
             f"({block.klass} {block.owner}); communities: {', '.join(communities)}.",
             f"Minimum Monthly Bill: ${block.minimum:.2f} (a floor, not an additional charge)."]
    if block.zone == "Thermal" and residential and not government:
        notes.append("Thermal (diesel-generated) communities; name retained from earlier Diesel Zone records.")
    if block.zone == "Taltson System":
        notes.append("Per the schedule, the NWT Stabilization rider does not apply to Hay River and the "
                     "Misc. Deferral Transfers rider applies only to Hay River.")
    if block.standby is not None:
        notes.append(f"Stand-by Charge (${block.standby:.2f}/kW) excluded: stand-by eligibility is negotiated "
                     "per customer.")
    if residential and not government:
        credits, credit_notes = _page_subsidies(schedule, block, communities, page, tpsp, rider_notes)
        components.extend(credits)
        notes.extend(credit_notes)
    elif government:
        notes.append("Government accounts use this separate schedule; NTPC publishes no GNWT TPSP or "
                     "Cost of Living Subsidy value for them, so none is stored.")
    else:
        notes.append("NTPC publishes no Cost of Living Subsidy value for general service; none is stored.")
    return TariffRecord(
        utility_name=UTILITY_NAME, province="NT", utility_type="electricity", tariff_name=name,
        customer_class="residential" if residential else "commercial",
        sub_class=f"{zone_label.lower()} {block.owner.lower()}" + (f" {place.lower()}" if government or
                                                                    block.zone == "Taltson System" else ""),
        eligibility=f"{block.klass} {block.owner} customers in {', '.join(communities)}",
        rate_structure="flat" if residential else "demand", pricing_method="regulated",
        effective_date=max(component.effective_date for component in components),
        source_url=schedule.url, source_page=f"PDF page {block.page}", confidence="high",
        notes=" ".join(notes), components=components,
    )


def parse_interruptible_retail(pages: list[DocumentPage], url: str, today: str) -> _Interruptible:
    """Parse the Taltson "Interruptible Energy For Heating - Retail" block; the wholesale block is ignored."""
    found: list[_Interruptible] = []
    for page in pages:
        heads = list(INTERRUPTIBLE_HEAD_RE.finditer(page.text))
        for index, head in enumerate(heads):
            if head.group(1) != "Retail":
                continue
            if not re.search(r"^Zone:\s*Taltson System\s*$", page.text, re.M):
                raise _Reject("retail interruptible heating block is not under Zone: Taltson System")
            dates = {_iso(value) for value in EFFECTIVE_RE.findall(page.text)}
            if len(dates) != 1:
                raise _Reject(f"interruptible heating page dates {sorted(dates)}")
            end = heads[index + 1].start() if index + 1 < len(heads) else len(page.text)
            lines = [line.strip() for line in page.text[head.end():end].splitlines() if line.strip()]
            lines = [line for line in lines if not re.fullmatch(r"Page \d+", line)]
            energy = [m for line in lines if (m := re.fullmatch(r"Energy Charge:\s*Interruptible Energy\s+" + CENTS,
                                                                 line))]
            expected = {"Monthly Service Charge: N/A", "Demand Charge: N/A"}
            others = [line for line in lines if line not in expected and not re.fullmatch(
                r"Energy Charge:\s*Interruptible Energy\s+" + CENTS, line)]
            if len(energy) != 1 or not expected <= set(lines) or others:
                raise _Reject(f"unexpected retail interruptible heating block {lines!r}")
            found.append(_Interruptible(url, dates.pop(), page.page_number, float(energy[0].group(1))))
    if len(found) != 1:
        raise _Reject(f"expected one retail interruptible heating block, found {len(found)}")
    if found[0].effective > today:
        raise _Reject(f"interruptible heating rate effective {found[0].effective} is in the future")
    return found[0]


def parse_terms_schedule_d(pages: list[DocumentPage], url: str, today: str) -> _ScheduleD:
    """Return the dated, PUB-approved Schedule "D" eligibility wording; every required sentence must be present."""
    text = _flat("\n".join(page.text for page in pages))
    dates = {_iso(value) for value in TERMS_EFFECTIVE_RE.findall(text)}
    if len(dates) != 1:
        raise _Reject(f"terms and conditions effective dates {sorted(dates)}")
    effective = dates.pop()
    if effective > today:
        raise _Reject(f"terms and conditions effective {effective} is in the future")
    if TERMS_APPROVED not in text:
        raise _Reject("terms and conditions lack the PUB approval statement")
    starts = [page.page_number for page in pages if SCHEDULE_D_RE.search(_flat(page.text))]
    if len(starts) != 1:
        raise _Reject(f"expected one Schedule D heading, found {len(starts)}")
    section: list[DocumentPage] = []
    for page in pages:
        if page.page_number < starts[0]:
            continue
        flat = _flat(page.text)
        if section and SCHEDULE_E_RE.search(flat):
            break
        section.append(page)
    body = _flat("\n".join(page.text for page in section))
    body = body[SCHEDULE_D_RE.search(body).end():]
    if match := SCHEDULE_E_RE.search(body):
        body = body[:match.start()]
    missing = [key for key, quote in SCHEDULE_D_QUOTES.items() if quote not in body]
    if missing:
        raise _Reject(f"Schedule D wording changed or missing: {missing}")
    return _ScheduleD(url, effective, [page.page_number for page in section], dict(SCHEDULE_D_QUOTES))


def build_interruptible_record(rate: _Interruptible, terms: _ScheduleD) -> TariffRecord:
    """Build the conditional retail interruptible heating record; riders are not stated for this rate."""
    pages = f"{terms.pages[0]}-{terms.pages[-1]}" if len(terms.pages) > 1 else str(terms.pages[0])
    terms_detail = (f"Terms and Conditions of Service (PUB-approved, effective {terms.effective}), "
                    f"Schedule \"D\" Interruptible Energy for Heating: Taltson Retail, PDF pages {pages}")
    q = terms.quotes
    eligibility = ("General service and industrial customers in Fort Smith and Fort Resolution (Taltson System), "
                   "for new, separately serviced, fully interruptible heating load only, subject to Schedule \"D\": "
                   + " ".join(q[key] for key in ("available", "new_loads", "separate", "incremental", "backup",
                                                  "notice", "no_return")))
    component = RateComponent(
        component_type="energy", component_name="Interruptible Energy Charge",
        charge_value=_dollars_per_kwh(rate.cents), charge_unit="$/kWh",
        effective_date=rate.effective, source_url=rate.url,
        source_detail=(f"PDF page {rate.page}, Zone: Taltson System, Interruptible Energy For Heating - Retail; "
                       f"conditions: {terms_detail} ({terms.url})"),
        confidence="high",
        notes=("Conditional: applies only to eligible interruptible heating energy on a separate service, not to "
               "firm consumption. " + q["applied"] + " " + q["surplus"] + " " + q["interruptions"]
               + " The schedule page lists no service or demand charge and states no riders for this rate."),
    )
    notes = [
        f"PUB-approved NTPC rate schedule effective {rate.effective}, Taltson System, Interruptible Energy For "
        "Heating - Retail. Wholesale interruptible heating (Schedule \"E\", for NUL-NWT) is excluded.",
        f"Eligibility and service terms: {terms_detail}. {q['rate']}",
        "Riders not stated: the schedule page for this rate lists only the interruptible energy charge, so no "
        "Taltson rider components are stored.",
        q["install"],
        "Availability is at NTPC's discretion; this is not a general firm commercial rate.",
    ]
    return TariffRecord(
        utility_name=UTILITY_NAME, province="NT", utility_type="electricity", tariff_name=INTERRUPTIBLE_NAME,
        customer_class="commercial", sub_class="interruptible heating", eligibility=eligibility,
        rate_structure="flat", pricing_method="regulated", effective_date=rate.effective,
        source_url=rate.url, source_page=f"PDF page {rate.page}", confidence="high",
        notes=" ".join(notes), components=[component],
    )

# ── Seed / fallback rate data ─────────────────────────────────────
# Approximate published rates as of early 2025.
# NTPC has many rate zones; we capture Yellowknife (hydro) and a
# representative diesel community zone here.

SEED_RESIDENTIAL_YELLOWKNIFE = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.ntpc.com/customer-service/residential-service/current-rates",
    "tier1_threshold_kwh": 1000,   # per month
    "tier1_rate": 0.3244,          # $/kWh
    "tier2_rate": 0.5967,          # $/kWh
    "basic_charge_monthly": 16.28, # $/month
}

SEED_RESIDENTIAL_DIESEL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.ntpc.com/customer-service/residential-service/current-rates",
    "tier1_threshold_kwh": 600,    # lower threshold in diesel zones
    "tier1_rate": 0.3022,          # $/kWh (subsidised first block)
    "tier2_rate": 1.0181,          # $/kWh — true diesel cost
    "basic_charge_monthly": 16.28, # $/month
}

SEED_GENERAL_SERVICE_YELLOWKNIFE = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.ntpc.com/customer-service/residential-service/current-rates",
    "energy_rate": 0.3244,         # $/kWh
    "demand_charge": 5.30,         # $/kW
    "basic_charge_monthly": 28.00, # $/month
}


class NTPCScraper(BaseScraper):
    """Scrape Northwest Territories Power Corporation electricity rates."""

    def __init__(self) -> None:
        super().__init__(
            utility_name="Northwest Territories Power Corporation",
            province="NT",
        )

    def scrape(self) -> list[TariffRecord]:
        """Parse the current PUB-approved schedule; label any unreplaced seed as an estimate."""
        live_records = self._try_live_scrape()
        if not live_records:
            self.logger.warning("Live scrape failed — using seed data for NTPC")
            return self.mark_fallback(self._seed_data())
        records = self.mark_live_parsed(live_records)
        if not any(record.tariff_name == DIESEL_RESIDENTIAL_NAME for record in records):
            seed = [r for r in self._seed_data() if r.tariff_name == DIESEL_RESIDENTIAL_NAME]
            records.extend(self.mark_fallback(seed, "Thermal residential schedule could not be parsed"))
        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Build records from the schedule PDF; residential-page subsidies are optional, cross-checked extras."""
        today = self.now_iso()[:10]
        try:
            pdf_url, listed = parse_schedule_index(self.fetch_page(SCHEDULE_INDEX_URL), today)
            pages = extract_pdf_pages(self.fetch_bytes(pdf_url))
            if not pages:
                return None
            schedule = parse_schedule(pages, pdf_url, today)
            if schedule.effective != listed:
                self.logger.warning("NTPC schedule date %s differs from index label %s", schedule.effective, listed)
                return None
        except Exception:
            self.logger.exception("Error parsing the NTPC rate schedule")
            return None
        page = self._optional("residential page", lambda: parse_residential_page(self.fetch_page(RESIDENTIAL_URL), today))
        tpsp = self._optional("TPSP page", lambda: parse_tpsp(self.fetch_page(TPSP_URL)))
        rider_notes = self._optional("rider page", lambda: parse_rider_page(self.fetch_page(RIDER_URL))) or {}
        records = build_records(schedule, page, tpsp, rider_notes)
        interruptible = self._interruptible(pages, pdf_url, schedule.effective, today)
        if records and interruptible:
            records.append(interruptible)
        return records or None

    def _interruptible(self, pages: list[DocumentPage], pdf_url: str, effective: str,
                       today: str) -> Optional[TariffRecord]:
        """Return the conditional retail interruptible heating record, or None if either source fails closed."""
        try:
            rate = parse_interruptible_retail(pages, pdf_url, today)
            if rate.effective != effective:
                raise _Reject(f"interruptible heating date {rate.effective} differs from schedule {effective}")
            terms = parse_terms_schedule_d(extract_pdf_pages(self.fetch_bytes(TERMS_URL)), TERMS_URL, today)
            return build_interruptible_record(rate, terms)
        except Exception as exc:
            self.logger.warning("NTPC interruptible heating record omitted: %s", exc)
            return None

    def _optional(self, label: str, action):
        try:
            return action()
        except Exception as exc:
            self.logger.warning("NTPC %s unavailable; dependent subsidies omitted: %s", label, exc)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records: list[TariffRecord] = []

        # ── Residential — Yellowknife Zone (Hydro) ───────────────
        records.append(TariffRecord(
            utility_name="Northwest Territories Power Corporation",
            province="NT",
            utility_type="electricity",
            tariff_name="Residential Service — Yellowknife Zone",
            customer_class="residential",
            sub_class="yellowknife zone",
            rate_structure="tiered",
            effective_date=SEED_RESIDENTIAL_YELLOWKNIFE["effective_date"],
            source_url=SEED_RESIDENTIAL_YELLOWKNIFE["source_url"],
            confidence="medium",
            notes=(
                "Yellowknife zone is served primarily by hydro generation "
                "(Snare River system). Rates are the lowest in the NWT but "
                "still significantly higher than southern Canada — roughly "
                "3x the national average. Tier 1 covers the first 1,000 kWh "
                "per month; tier 2 applies above that threshold."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_RESIDENTIAL_YELLOWKNIFE["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Monthly customer charge",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 1 Energy Charge",
                    charge_value=SEED_RESIDENTIAL_YELLOWKNIFE["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_RESIDENTIAL_YELLOWKNIFE["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes="First 1,000 kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge",
                    charge_value=SEED_RESIDENTIAL_YELLOWKNIFE["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_RESIDENTIAL_YELLOWKNIFE["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes="All kWh above 1,000 per month",
                ),
            ],
        ))

        # ── Residential — Diesel Zone ────────────────────────────
        records.append(TariffRecord(
            utility_name="Northwest Territories Power Corporation",
            province="NT",
            utility_type="electricity",
            tariff_name="Residential Service — Diesel Zone",
            customer_class="residential",
            sub_class="diesel zone",
            rate_structure="tiered",
            effective_date=SEED_RESIDENTIAL_DIESEL["effective_date"],
            source_url=SEED_RESIDENTIAL_DIESEL["source_url"],
            confidence="medium",
            notes=(
                "Diesel zone communities (e.g. Tuktoyaktuk, Sachs Harbour, "
                "Paulatuk) rely entirely on trucked-in diesel for electricity "
                "generation. The tail-block rate exceeds $1.00/kWh, making "
                "this among the most expensive electricity in Canada. The "
                "NWT Territorial Power Support Program subsidises the first "
                "block for residential customers to bring it closer to the "
                "Yellowknife hydro rate. Tier 1 threshold is lower at 600 kWh."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_RESIDENTIAL_DIESEL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 1 Energy Charge (Diesel Zone)",
                    charge_value=SEED_RESIDENTIAL_DIESEL["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_RESIDENTIAL_DIESEL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes=(
                        "First 600 kWh per month — subsidised through "
                        "Territorial Power Support Program"
                    ),
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge (Diesel Zone)",
                    charge_value=SEED_RESIDENTIAL_DIESEL["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_RESIDENTIAL_DIESEL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes=(
                        "Above 600 kWh/month — reflects true cost of "
                        "diesel generation in remote communities"
                    ),
                ),
            ],
        ))

        # ── General Service — Yellowknife Zone ───────────────────
        records.append(TariffRecord(
            utility_name="Northwest Territories Power Corporation",
            province="NT",
            utility_type="electricity",
            tariff_name="General Service — Yellowknife Zone",
            customer_class="commercial",
            sub_class="yellowknife zone",
            rate_structure="demand",
            effective_date=SEED_GENERAL_SERVICE_YELLOWKNIFE["effective_date"],
            source_url=SEED_GENERAL_SERVICE_YELLOWKNIFE["source_url"],
            confidence="medium",
            notes=(
                "Commercial general service rate for the Yellowknife hydro "
                "zone. Includes energy and demand components. Commercial "
                "rates in diesel communities are significantly higher."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_GENERAL_SERVICE_YELLOWKNIFE["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_GENERAL_SERVICE_YELLOWKNIFE["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_GENERAL_SERVICE_YELLOWKNIFE["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    confidence="medium",
                    notes="Billed on peak measured demand in the billing period",
                ),
            ],
        ))

        return records
