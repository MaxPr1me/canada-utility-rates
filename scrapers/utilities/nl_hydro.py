"""
nl_hydro.py — Scraper for NL Hydro electricity rates (Newfoundland and Labrador).

Newfoundland and Labrador Hydro (NL Hydro) is the Crown corporation
responsible for electricity generation and transmission in the province.
NL Hydro also directly serves some rural and isolated communities,
as well as customers on the Labrador interconnected system.

Official source:
  https://nlhydro.com/electicity-rates/current-rates/

Regulated by: Board of Commissioners of Public Utilities (PUB NL)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable, Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    DocumentPage,
    parse_html,
    find_pdf_links,
    extract_pdf_pages,
)

logger = logging.getLogger(__name__)

NL_HYDRO_URL = "https://nlhydro.com/electicity-rates/current-rates/"

# Known rate values — used as seed/fallback data.
# NL Hydro serves rural areas directly; rates shown are for
# island-interconnected rural customers.
SEED_RURAL_RESIDENTIAL = {
    "effective_date": "2026-01-01",
    "source_url": NL_HYDRO_URL,
    "energy_rate": 0.15213,         # $/kWh
    "basic_charge_per_month": 12.94,  # $/month
}

SEED_LABRADOR_INTERCONNECTED = {
    "effective_date": "2026-01-01",
    "source_url": NL_HYDRO_URL,
    "energy_rate": 0.03154,         # $/kWh — Labrador interconnected rate
    "basic_charge_per_month": 12.94,  # $/month
}

SEED_GENERAL_SERVICE = {
    "effective_date": "2026-01-01",
    "source_url": NL_HYDRO_URL,
    "energy_rate": 0.14793,         # $/kWh (estimated proportional increase)
    "basic_charge_per_month": 19.42,  # $/month
    "demand_charge": 8.56,          # $/kW (for demand-metered)
}

# Seed identities that the live parser supersedes (sub_class -> published rate number).
_SEED_CODES = {"rural": "1.1", "labrador interconnected": "1.1L", "general service": "2.1"}

_LEADER = r"(?:\s*[.…]\s*){2,}"
_MONEY = r"\$\s*(\d[\d,]*\.\d{2})"
_CENTS = r"@\s*(\(?-?\d+\.\d+\)?)\s*(?:¢|cents?)\s*per\s*kWh"
_WINTER_MONTHS = "12,1,2,3"
_OTHER_MONTHS = "4,5,6,7,8,9,10,11"
_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


class _Reject(Exception):
    """A class cannot be proven complete from the published schedule."""


@dataclass(frozen=True)
class _Tier:
    pattern: str                 # fullmatch against the source row label; groups are block sizes
    tier: Optional[int] = None
    unit: Optional[str] = None


@dataclass(frozen=True)
class _Spec:
    code: str
    prefix: str                  # page-footer prefix, e.g. ISL for ISL-4
    heading: str                 # regex that must follow "RATE NO. <code>"
    name: str
    customer_class: str
    sub_class: str
    area: str
    availability: tuple[str, ...]
    basic: tuple[tuple[Optional[str], str], ...] = ()   # (source label, component label)
    demand: Optional[tuple[str, str]] = None            # ("seasonal"|"flat", "kW"|"kVA")
    energy: tuple[_Tier, ...] = ()
    kind: str = "standard"       # standard | diesel_domestic | option
    demand_min_kw: Optional[float] = None
    demand_max_kw: Optional[float] = None
    excess_kw: Optional[float] = None                   # billing demand counts only kW above this
    minimum: str = "none"        # none | rows (dollar floor per basic row) | demand (dollars per kW/kVA of 12-month peak)
    maximum: str = "none"        # none | plus_basic (cents/kWh plus basic charge) | flat_cents (cents/kWh)
    base_code: Optional[str] = None                     # option records apply together with this base rate


_ALL = (_Tier(r"All kilowatt-hours"),)
_EXCESS = _Tier(r"All excess kilowatt-hours", 2)
_ISL = "Island Interconnected System and L'Anse au Loup"
_ISL_AVAIL = r"Island Interconnected system and the L.Anse au Loup system"
_DSL = "Island and Labrador diesel systems"
_LAB = "Labrador Interconnected System"
_SINGLE = ((None, "Basic Customer Charge"),)
_PHASES = (("Unmetered", "Unmetered"), ("Single Phase", "Single Phase"), ("Three Phase", "Three Phase"))
_AMPS = (("Not Exceeding 200 Amp Service", "Not Exceeding 200 Amp Service"),
         ("Exceeding 200 Amp Service", "Exceeding 200 Amp Service"))

_SPECS: tuple[_Spec, ...] = (
    _Spec("1.1", "ISL", "DOMESTIC", "Rural Residential Service (Domestic)", "residential", "rural", _ISL,
          (r"Island Interconnected System and the L.Anse au Loup system", r"Domestic Unit"),
          basic=_AMPS, energy=_ALL, minimum="rows"),
    _Spec("1.1S", "ISL", r"DOMESTIC.{1,3}OPTIONAL", "Domestic Optional Seasonal Adjustment (Rate 1.1S)",
          "residential", "rural seasonal option", _ISL,
          (r"Island Interconnected System and the L.Anse au Loup system", r"Rate No\. 1\.1 Domestic",
           r"12 months of uninterrupted billing history"), kind="option", base_code="1.1"),
    _Spec("1.3", "ISL", "BURGEO SCHOOL AND LIBRARY", "Burgeo School and Library (Rate 1.3)", "commercial",
          "burgeo school and library", "Burgeo", (r"Burgeo School and Library",), energy=_ALL),
    _Spec("2.1", "ISL", r"GENERAL SERVICE 0.100 kW \(110 kVA\)", "General Service", "commercial",
          "general service", _ISL,
          (r"excluding Domestic Service", _ISL_AVAIL, r"less than 100 kilowatts \(110 kilovolt-amperes\)"),
          basic=_PHASES, demand=("seasonal", "kW"),
          energy=(_Tier(r"First ([\d,]+) kilowatt-hours", 1, "kWh"), _EXCESS),
          demand_max_kw=100.0, excess_kw=10.0, minimum="rows", maximum="plus_basic"),
    _Spec("2.3", "ISL", r"GENERAL SERVICE 110 kVA \(100 kW\).1,000 kVA",
          "General Service 110 kVA (100 kW)-1,000 kVA (Rate 2.3)", "commercial", "general service 110-1000 kVA",
          _ISL,
          (_ISL_AVAIL, r"110 kilovolt-amperes \(100 kilowatts\) or greater but less than 1,000 kilovolt-amperes"),
          basic=_SINGLE, demand=("seasonal", "kVA"),
          energy=(_Tier(r"First (\d+) kilowatt-hours per kVA of billing demand, up to a maximum of ([\d,]+) "
                        r"kilowatt-hours", 1, "kWh/kVA"), _EXCESS),
          demand_min_kw=100.0, maximum="plus_basic"),
    _Spec("2.4", "ISL", r"GENERAL SERVICE 1,000 kVA AND OVER", "General Service 1,000 kVA and Over (Rate 2.4)",
          "commercial", "general service 1000 kVA and over", _ISL,
          (_ISL_AVAIL, r"1,000 kilovolt-amperes or greater"),
          basic=_SINGLE, demand=("seasonal", "kVA"),
          energy=(_Tier(r"First ([\d,]+) kilowatt-hours", 1, "kWh"), _EXCESS), maximum="plus_basic"),
    _Spec("1.2D", "DSL-NG", "DOMESTIC DIESEL", "Domestic Diesel (Rate 1.2D)", "residential", "diesel", _DSL,
          (r"diesel service areas of Hydro \(excluding Government Departments\)", r"Domestic Unit",
           r"churches, schools, and community halls"),
          basic=((None, "Not Exceeding 200 Amp Service"), ("Exceeding 200 Amp Service",) * 2),
          kind="diesel_domestic", minimum="rows"),
    _Spec("1.2DS", "DSL-NG", r"DOMESTIC DIESEL \(NON-GOVERNMENT FIRST BLOCK\).{1,3}OPTIONAL",
          "Domestic Diesel First Block Optional Seasonal Adjustment (Rate 1.2DS)", "residential",
          "diesel seasonal option", _DSL,
          (r"excluding Government Departments", r"Rate 1\.2 Domestic Diesel",
           r"12 months of uninterrupted billing history"), kind="option", base_code="1.2D"),
    _Spec("2.1D", "DSL-NG", r"GENERAL SERVICE DIESEL 0.10 kW",
          "General Service Diesel 0-10 kW (Rate 2.1D)", "commercial", "diesel general service 0-10 kW", _DSL,
          (r"excluding Government Departments", r"less than 10 kilowatts"),
          basic=_PHASES, energy=_ALL, demand_max_kw=10.0, minimum="rows"),
    _Spec("2.2D", "DSL-NG", r"GENERAL SERVICE DIESEL OVER 10 kW",
          "General Service Diesel Over 10 kW (Rate 2.2D)", "commercial", "diesel general service over 10 kW",
          _DSL, (r"excluding Government Departments", r"10 kilowatts or greater"),
          basic=_PHASES, demand=("flat", "kW"), energy=_ALL, demand_min_kw=10.0, minimum="rows"),
    _Spec("1.2G", "DSL-G", r"DOMESTIC DIESEL GOVERNMENT DEPARTMENTS",
          "Domestic Diesel - Government Departments (Rate 1.2G)", "residential", "diesel government", _DSL,
          (r"Government Departments", r"Domestic Unit"), basic=_SINGLE, energy=_ALL, minimum="rows"),
    _Spec("2.1G", "DSL-G", r"GENERAL SERVICE DIESEL 0.10 kW GOVERNMENT DEPARTMENTS",
          "General Service Diesel 0-10 kW - Government Departments (Rate 2.1G)", "commercial",
          "diesel government general service 0-10 kW", _DSL,
          (r"Government Departments", r"less than 10 kilowatts"), basic=_SINGLE, energy=_ALL,
          demand_max_kw=10.0, minimum="rows"),
    _Spec("2.2G", "DSL-G", r"GENERAL SERVICE DIESEL OVER 10 kW GOVERNMENT DEPARTMENTS",
          "General Service Diesel Over 10 kW - Government Departments (Rate 2.2G)", "commercial",
          "diesel government general service over 10 kW", _DSL,
          (r"Government Departments", r"10 kilowatts or greater"),
          basic=_SINGLE, demand=("flat", "kW"), energy=_ALL, demand_min_kw=10.0),
    _Spec("1.1L", "LAB", "DOMESTIC", "Labrador Interconnected Residential Service", "residential",
          "labrador interconnected", _LAB, (r"Labrador Interconnected service area", r"Domestic Unit"),
          basic=_SINGLE, energy=_ALL, minimum="rows"),
    _Spec("2.1L", "LAB", r"GENERAL SERVICE 0.10 kW", "General Service 0-10 kW - Labrador (Rate 2.1L)",
          "commercial", "labrador general service 0-10 kW", _LAB,
          (r"excluding Domestic Service", r"Labrador Interconnected service area", r"less than 10 kilowatts"),
          basic=_PHASES, energy=_ALL, demand_max_kw=10.0, minimum="rows"),
    _Spec("2.2L", "LAB", r"GENERAL SERVICE 10.100 KW \(110 KVA\)",
          "General Service 10-100 kW - Labrador (Rate 2.2L)", "commercial", "labrador general service 10-100 kW",
          _LAB, (r"Labrador Interconnected service area",
                 r"10 kilowatts or greater but less than 100 kilowatts \(110 kilovolt-amperes\)"),
          basic=_PHASES, demand=("flat", "kW"), energy=_ALL, demand_min_kw=10.0, demand_max_kw=100.0,
          minimum="demand", maximum="flat_cents"),
    _Spec("2.3L", "LAB", r"GENERAL SERVICE 110 KVA \(100 KW\).1,000 KVA",
          "General Service 110 kVA (100 kW)-1,000 kVA - Labrador (Rate 2.3L)", "commercial",
          "labrador general service 110-1000 kVA", _LAB,
          (r"Labrador Interconnected service area",
           r"110 kilovolt-amperes \(100 kilowatts\) or greater but less than 1,?000 kilovolt-amperes"),
          demand=("flat", "kVA"), energy=_ALL, demand_min_kw=100.0, minimum="demand", maximum="flat_cents"),
    _Spec("2.4L", "LAB", r"GENERAL SERVICE 1,000 KVA AND OVER",
          "General Service 1,000 kVA and Over - Labrador (Rate 2.4L)", "commercial",
          "labrador general service 1000 kVA and over", _LAB,
          (r"Labrador Interconnected service area", r"1,?000 kilovolt-amperes or greater"),
          demand=("flat", "kVA"), energy=_ALL, minimum="demand", maximum="flat_cents"),
)

# Rate numbers that are published but deliberately outside the building-cost scope.
_EXCLUDED_CODES = {"4.1", "4.1D", "4.1G", "4.1L", "4.11L", "4.12L"}   # street and area lighting

# Published schedules that are real catalogue gaps, with the reason each is not a modelled building tariff.
_GAP_RATES = {
    "5.1L": "interruptible non-firm energy for 1.5 MW+ transmission customers; price is a NYISO/ISO-NE futures formula",
}
_GAP_SCHEDULES = {
    "UT": "Utility: wholesale supply to Newfoundland Power (a retailer)",
    "IND": "Island Industrial Firm/Non-Firm/Wheeling: 66 kV+ bulk-grid contract customers under Industrial Service Agreements",
    "LAB-IND": "Labrador Industrial: 66 kV+ contract customers with formula energy rates",
    "CP": "Commissioning Power non-firm rate",
    "NM": "Net Metering Service Option (billing option, not a tariff)",
}
_UNMODELLED_TERMS = re.compile(r"\b(?:subsid\w*|rider|surcharge|credit|rebate|curtail\w*)\b", re.I)


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"-\n(?=[a-z])", "-", text)).strip()


def _slice(flat: str, start: str, ends: Iterable[str]) -> str:
    begin = flat.find(start)
    if begin == -1:
        return ""
    begin += len(start)
    stop = min([pos for pos in (flat.find(end, begin) for end in ends) if pos != -1] or [len(flat)])
    return flat[begin:stop]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(_LEADER, " ", text)).strip(" :")


def _cents(raw: str) -> float:
    negative = raw.startswith("(") or raw.startswith("-")
    value = float(raw.strip("()-"))
    return round((-value if negative else value) / 100.0, 6)


def _num(raw: str) -> float:
    return float(raw.replace(",", ""))


def _months(numbers: list[int]) -> tuple[str, str]:
    return ",".join(str(number) for number in numbers), ", ".join(_MONTH_ABBR[number - 1] for number in numbers)


def _money_rows(section: str, per_month_required: bool = False) -> list[tuple[Optional[str], float]]:
    """(label, dollars) rows; the label is None when the source row is unlabelled."""
    unit = r"\s*per month" if per_month_required else r"(?:\s*per month)?"
    return [
        ((match.group(1) or "").strip(" :") or None, _num(match.group(2)))
        for match in re.finditer(
            rf"([A-Za-z0-9][A-Za-z0-9 ]*?)?[\s:]*{_LEADER}\s*{_MONEY}{unit}", section)
    ]


def _landing_rates(text: str) -> dict[str, float]:
    """Headline cents/kWh quoted on the current-rates page, keyed by rate number."""
    flat = _flat(text)
    rates: dict[str, float] = {}
    island = re.search(
        r"Island Interconnected System, L.Anse au Loup, and Isolated Diesel Systems \(first block\), "
        r"the current rate is (\d+\.\d+) cents per kWh", flat)
    labrador = re.search(
        r"Labrador Interconnected System, the current rate is (\d+\.\d+) cents per kWh", flat)
    if island:
        rates["1.1"] = rates["1.2D"] = round(float(island.group(1)) / 100.0, 6)
    if labrador:
        rates["1.1L"] = round(float(labrador.group(1)) / 100.0, 6)
    return rates


def _basic_components(flat: str, spec: _Spec) -> list[RateComponent]:
    start = flat.find("Basic Customer Charge")
    if not spec.basic:
        if start != -1:
            raise _Reject("unexpected Basic Customer Charge")
        return []
    if start == -1:
        raise _Reject("Basic Customer Charge missing")
    section = _slice(flat, "Basic Customer Charge", ("Billing Demand Charge", "Demand Charge", "Energy Charge"))
    rows = _money_rows(section, per_month_required=True)
    if [label for label, _ in rows] != [label for label, _ in spec.basic]:
        raise _Reject(f"Basic Customer Charge rows {[label for label, _ in rows]} do not match expected labels")
    alternatives = len(spec.basic) > 1
    components = []
    for (source_label, value), (_, label) in zip(rows, spec.basic):
        if value <= 0:
            raise _Reject("non-positive Basic Customer Charge")
        note = None
        if alternatives:
            note = (f"Alternative: applies only to '{label}' service. Mutually exclusive with the other "
                    "Basic Customer Charge rows; one row is billed per service, not all rows together")
            if source_label is None:
                note += " (the source row is unlabelled and precedes the 'Exceeding 200 Amp Service' row)"
        components.append(RateComponent(
            component_type="fixed",
            component_name="Basic Customer Charge" if label == "Basic Customer Charge"
            else f"Basic Customer Charge ({label})",
            charge_value=value, charge_unit="$/month",
            sub_component=None if label == "Basic Customer Charge" else label, notes=note,
        ))
    return components


def _demand_components(flat: str, spec: _Spec) -> list[RateComponent]:
    present = re.search(r"(?:Billing )?Demand Charge", flat) is not None
    if spec.demand is None:
        if present:
            raise _Reject("unexpected Demand Charge")
        return []
    kind, unit = spec.demand
    if not present:
        raise _Reject("Demand Charge missing")
    if kind == "flat":
        section = _slice(flat, "Demand Charge", ("Energy Charge",))
        match = re.search(rf"@\s*{_MONEY}\s*per\s*(kW|kVA)\b", section)
        if not match or match.group(2) != unit:
            raise _Reject(f"Demand Charge is not a $ per {unit} row")
        if _num(match.group(1)) <= 0:
            raise _Reject("non-positive Demand Charge")
        return [RateComponent(
            component_type="demand", component_name="Demand Charge", charge_value=_num(match.group(1)),
            charge_unit=f"$/{unit}", demand_unit=unit,
            notes=f"Maximum demand registered on the meter in the current month, billed per {unit}",
        )]
    match = re.search(
        rf"{_MONEY} per (kW|kVA) of billing demand in the months of December, January, February and March "
        rf"and {_MONEY} per (kW|kVA) in all other months", flat)
    if not match or match.group(2) != unit or match.group(4) != unit:
        raise _Reject(f"seasonal Demand Charge per {unit} not found")
    if _num(match.group(1)) <= 0 or _num(match.group(3)) <= 0:
        raise _Reject("non-positive seasonal Demand Charge")
    note = f"Billed per {unit} of billing demand (maximum demand registered in the current month)"
    threshold = None
    if spec.excess_kw is not None:
        if not re.search(rf"in excess of {spec.excess_kw:g} kW", flat):
            raise _Reject("billing-demand excess threshold missing")
        threshold = spec.excess_kw
        note += f"; only demand in excess of {spec.excess_kw:g} kW is billed"
    return [
        RateComponent(component_type="demand", component_name=f"Demand Charge ({label})",
                      charge_value=_num(match.group(group)), charge_unit=f"$/{unit}", demand_unit=unit,
                      season=season, season_months=months, demand_threshold_kw=threshold, notes=note)
        for label, group, season, months in (
            ("December-March", 1, "winter", _WINTER_MONTHS), ("April-November", 3, "other months", _OTHER_MONTHS))
    ]


def _energy_rows(flat: str) -> list[tuple[str, str]]:
    section = _slice(flat, "Energy Charge", ("Maximum Monthly Charge", "Minimum Monthly Charge", "Discount"))
    if re.search(r"\$\s*\d*\.?\d+\s*per\s*kWh", section):
        raise _Reject("energy charge quoted in dollars; cents per kWh expected")
    rows, position = [], 0
    for match in re.finditer(_CENTS, section):
        rows.append((_clean(section[position:match.start()]), match.group(1)))
        position = match.end()
    return rows


def _energy_components(flat: str, spec: _Spec) -> list[RateComponent]:
    rows = _energy_rows(flat)
    if spec.kind == "diesel_domestic":
        return _diesel_energy(flat, rows)
    if len(rows) != len(spec.energy):
        raise _Reject(f"expected {len(spec.energy)} energy rows, found {len(rows)}")
    components = []
    for (label, raw), tier in zip(rows, spec.energy):
        match = re.fullmatch(tier.pattern, label)
        if not match:
            raise _Reject(f"unexpected energy row label {label!r}")
        value = _cents(raw)
        if not 0 < value < 5:
            raise _Reject(f"implausible energy rate {raw}")
        groups = match.groups()
        if any(_num(group) <= 0 for group in groups):
            raise _Reject("non-positive energy block size")
        threshold = _num(groups[0]) if groups else None
        note = None
        if len(groups) > 1:
            note = f"First {groups[0]} kWh per kVA of billing demand, capped at {groups[1]} kWh per month"
        components.append(RateComponent(
            component_type="energy",
            component_name="Energy Charge" if tier.tier is None else f"Energy Charge - {label}",
            charge_value=value, charge_unit="$/kWh", tier_number=tier.tier, tier_threshold=threshold,
            tier_unit=tier.unit if threshold is not None else None, notes=note,
        ))
    return components


def _diesel_energy(flat: str, rows: list[tuple[str, str]]) -> list[RateComponent]:
    expected = (
        r"First Block \(See Table Below\) kilowatt-hours per month",
        r"Second Block \(See Table Below\) kilowatt-hours per month",
        r"All kWh over ([\d,]+) kilowatt-hours per month",
    )
    if len(rows) != 3 or not all(re.fullmatch(pattern, label) for (label, _), pattern in zip(rows, expected)):
        raise _Reject("diesel domestic block rows not found")
    values = [_cents(raw) for _, raw in rows]
    if not all(0 < value < 5 for value in values):
        raise _Reject("diesel block energy rates must all be positive and plausible")
    ceiling = _num(re.fullmatch(expected[2], rows[2][0]).group(1))
    if ceiling <= 0:
        raise _Reject("non-positive diesel block ceiling")
    table = re.search(
        r"Jan\.? Feb\.? Mar\.? Apr\.? May\.? Jun\.? Jul\.? Aug\.? Sept?\.? Oct\.? Nov\.? Dec\.? "
        r"First Block ((?:[\d,]+ ){11}[\d,]+) Second Block ((?:[\d,]+ ){11}[\d,]+)", flat)
    if not table:
        raise _Reject("monthly block-size table missing")
    first = [_num(size) for size in table.group(1).split()]
    second = [_num(size) for size in table.group(2).split()]
    if any(first_size <= 0 or second_size < 0 for first_size, second_size in zip(first, second)):
        raise _Reject("monthly first blocks must be positive and second blocks non-negative")
    if any(first_size + second_size != ceiling for first_size, second_size in zip(first, second)):
        raise _Reject("monthly block sizes do not sum to the published block ceiling")
    components = []
    for index, (tier, sizes, label) in enumerate(((1, first, "First Block"), (2, second, "Second Block"))):
        for size in sorted({size for size in sizes if size > 0}, reverse=True):
            numbers = [position + 1 for position, month_size in enumerate(sizes) if month_size == size]
            months, names = _months(numbers)
            components.append(RateComponent(
                component_type="energy", component_name=f"Energy Charge - {label} ({names})",
                charge_value=values[index], charge_unit="$/kWh", tier_number=tier, tier_threshold=size,
                tier_unit="kWh/month", season_months=months,
                notes=f"{label} is {size:g} kWh per month in these billing months (published table)",
            ))
    components.append(RateComponent(
        component_type="energy", component_name=f"Energy Charge - All kWh over {ceiling:g} kWh per month",
        charge_value=values[2], charge_unit="$/kWh", tier_number=3,
        notes=f"Applies to all kWh above {ceiling:g} kWh per month in every billing month",
    ))
    return components


def _option_components(flat: str, spec: _Spec) -> list[RateComponent]:
    first_only = "First Block Only" if spec.code == "1.2DS" else ""
    scope = f" {first_only}" if first_only else ""
    base_label = f"Rate {spec.base_code} energy charge" + (" (first block only)" if first_only else "")
    components = []
    for label, span, months in (
        ("Winter Season Premium Adjustment", "December through April", "12,1,2,3,4"),
        ("Non-Winter Season Premium Adjustment", "May through November", "5,6,7,8,9,10,11"),
    ):
        match = re.search(
            rf"{label} \(Billing Months of {span}\){scope}(?: All kilowatt-hours)?"
            rf"\s*(?:[.…]\s*)*{_CENTS}", flat)
        if not match:
            raise _Reject(f"{label} row not found")
        value = _cents(match.group(1))
        if value == 0 or abs(value) >= 0.5:
            raise _Reject(f"implausible seasonal adjustment {match.group(1)}")
        components.append(RateComponent(
            component_type="rebate" if value < 0 else "rider", component_name=label,
            charge_value=value, charge_unit="$/kWh adjustment", season_months=months,
            season="winter" if label.startswith("Winter") else "non-winter",
            sub_component=first_only or None,
            notes=(f"Apply together with the base schedule: adjusts the {base_label}; not a standalone energy "
                   "price. A negative value is a credit per kWh. Requires the signup, 12-month minimum "
                   "term and notice conditions listed on the tariff"),
        ))
    return components


def _option_conditions(flat: str) -> str:
    """Signup, minimum-term and termination conditions an option record must retain."""
    tail = flat[flat.find("Special Conditions"):] if "Special Conditions" in flat else ""
    first = re.search(
        r"1\. An application for Service under this rate option shall constitute a binding contract between "
        r"the Customer and the Company with an initial term of 12 months commencing the day after the first "
        r"meter reading date following the request by the customer, and renewing automatically on the "
        r"anniversary date thereof for successive 12-month terms\.", tail)
    second = re.search(
        r"2\. To terminate participation on this rate option on the renewal date, the Customer must notify the "
        r"Company either in advance of the renewal date or no later than 60 days after the anniversary/renewal "
        r"date\. When acceptable notice of termination is provided to the Company, the Customer.s billing may "
        r"require an adjustment to reverse any seasonal adjustments applied to charges for consumption after "
        r"the automatic renewal date\.", tail)
    if not first or not second:
        raise _Reject("option signup/minimum-term/termination special conditions missing or changed")
    if re.search(r"\s3\. ", tail):
        raise _Reject("option has an unmodelled additional special condition")
    return f"{first.group(0)} {second.group(0)}"


def _eligibility(flat: str) -> Optional[str]:
    match = re.search(
        r"Availability\d? (.*?)\sRate:?\s+(?=\(Including|Basic Customer|The Energy|Energy Charge|Demand Charge)",
        flat)
    if not match:
        return None
    text = match.group(1).replace("LÆAnse", "L'Anse")   # PDF extraction renders the apostrophe as Æ
    fish = re.search(r"This rate is also available to fish plants.*?of the rate\.", flat)
    return f"{text} {fish.group(0)}" if fish else text


def _billing_conditions(flat: str, spec: _Spec) -> list[str]:
    """Minimum/maximum bill rules the class requires; absent or unexpected rules reject the class."""
    discount_at = flat.find("Discount A discount")
    limit = discount_at if discount_at != -1 else len(flat)
    notes: list[str] = []
    has_maximum = "Maximum Monthly Charge The Maximum Monthly Charge" in flat[:limit]
    if spec.maximum == "none":
        if has_maximum:
            raise _Reject("unexpected Maximum Monthly Charge")
    else:
        match = re.search(
            r"Maximum Monthly Charge The Maximum Monthly Charge shall be (\d+(?:\.\d+)?)\s*(?:¢|cents?) per kWh"
            r"(?P<tail>(?: plus the [Bb]asic [Cc]ustomer [Cc]harge)?"
            r"(?:,? but not less than (?:the )?Minimum Monthly Charge)?)\. "
            r"The Maximum Monthly Charge shall not apply to Customers who avail of the Net Metering Service Option\.",
            flat)
        if not match or float(match.group(1)) <= 0:
            raise _Reject("Maximum Monthly Charge rule missing or changed")
        plus_basic = "plus the" in match.group("tail")
        floored = "not less than" in match.group("tail")
        if (spec.maximum == "plus_basic") != plus_basic or (spec.maximum == "flat_cents" and not floored):
            raise _Reject("Maximum Monthly Charge form does not match the class")
        notes.append(
            f"Maximum Monthly Charge: {match.group(1)} cents per kWh"
            + (" plus the Basic Customer Charge" if plus_basic else "")
            + (", but not less than the Minimum Monthly Charge" if floored else "")
            + "; does not apply with the Net Metering Service Option")
    header = flat.rfind("Minimum Monthly Charge", 0, limit)
    if spec.minimum == "none":
        if header != -1:
            raise _Reject("unexpected Minimum Monthly Charge")
    elif spec.minimum == "rows":
        rows = _money_rows(flat[header + len("Minimum Monthly Charge"):limit]) if header != -1 else []
        if [label for label, _ in rows] != [label for label, _ in spec.basic] or any(value <= 0 for _, value in rows):
            raise _Reject("Minimum Monthly Charge rows missing or do not match the basic charge rows")
        notes.append("Minimum Monthly Charge (a minimum bill, not an added charge): " + "; ".join(
            f"{label or 'standard'} ${value:.2f}" for (_, value), (_, label) in zip(rows, spec.basic)))
    else:
        unit = spec.demand[1] if spec.demand else ""
        match = re.search(
            r"Minimum Monthly Charge An amount equal to \$(\d+\.\d{2}) per (kW|kVA) of maximum demand occurring "
            r"in the 12 months ending with the current month(?:, but not less than \$(\d+\.\d{2}) for a "
            r"three-phase service)?\.", flat)
        if not match or match.group(2) != unit or float(match.group(1)) <= 0:
            raise _Reject("demand-based Minimum Monthly Charge missing or changed")
        floor = re.search(r"but not less than \$(\d+\.\d{2}) for a three-phase service", match.group(0))
        if bool(spec.basic) != bool(floor):
            raise _Reject("three-phase minimum floor does not match the class")
        notes.append(
            f"Minimum Monthly Charge (a minimum bill, not an added charge): ${match.group(1)} per {unit} of "
            "maximum demand in the 12 months ending with the current month"
            + (f", but not less than ${floor.group(1)} for a three-phase service" if floor else ""))
    return notes


def _page_date(flat: str, spec: _Spec, today: date) -> date:
    match = re.search(rf"Effective ([A-Z][a-z]+ \d{{1,2}}, \d{{4}}) {re.escape(spec.prefix)}-\d+", flat)
    if not match:
        raise _Reject("page effective date/footer missing")
    try:
        effective = datetime.strptime(match.group(1), "%B %d, %Y").date()
    except ValueError as exc:
        raise _Reject(f"unparseable effective date {match.group(1)!r}") from exc
    if effective > today:
        raise _Reject(f"effective date {effective} is in the future")
    return effective


class NLHydroScraper(BaseScraper):
    """Scrape NL Hydro electricity rates."""

    def __init__(self):
        super().__init__(utility_name="NL Hydro", province="NL")
        self.unmodelled_published: dict[str, str] = {}

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live NL Hydro rates.
        Classes the live schedule cannot prove complete fall back to labelled seeds.
        """
        records: list[TariffRecord] = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            covered = {record.tariff_code for record in live_records}
            missing = [seed for seed in self._seed_data() if _SEED_CODES[seed.sub_class] not in covered]
            if missing:
                records.extend(self.mark_fallback(
                    missing, "Live schedule did not yield a complete matching class"))
            self.logger.info(
                "Successfully scraped %d NL Hydro tariffs from live site", len(live_records))
        else:
            self.logger.warning("Live scrape failed — using seed data for NL Hydro")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def parse_schedule_pages(
        self,
        pages: list[DocumentPage],
        source_url: str,
        landing_text: Optional[str] = None,
        today: Optional[date] = None,
    ) -> list[TariffRecord]:
        """Build live tariffs from Schedule of Rates pages; each class succeeds or fails alone.

        Published schedules that are not modelled are left in `self.unmodelled_published`
        (rate number or schedule prefix -> reason) and logged as gaps.
        """
        today = today or date.today()
        landing = _landing_rates(landing_text) if landing_text else {}
        modelled = {spec.code for spec in _SPECS} | _EXCLUDED_CODES
        self.unmodelled_published = {}
        for page in pages:
            for code in re.findall(r"^RATE NO\. (\S+)\s*$", page.text, re.M):
                if code in _GAP_RATES:
                    self.unmodelled_published[code] = _GAP_RATES[code]
                elif code not in modelled:
                    self.unmodelled_published[code] = "published rate number not modelled"
            for prefix in re.findall(r"Effective [A-Z][a-z]+ \d{1,2}, \d{4} ([A-Z]+(?:-IND)?)-\d+", page.text):
                if prefix in _GAP_SCHEDULES:
                    self.unmodelled_published[prefix] = _GAP_SCHEDULES[prefix]
        for code, reason in self.unmodelled_published.items():
            self.logger.warning("NL Hydro: published schedule %s is not modelled (gap): %s", code, reason)
        records: list[TariffRecord] = []
        parsed: dict[str, TariffRecord] = {}
        for spec in _SPECS:
            try:
                record = self._parse_spec(spec, pages, source_url, landing, today)
                if spec.base_code is not None:
                    base = parsed.get(spec.base_code)
                    if base is None:
                        raise _Reject(f"base Rate {spec.base_code} is not live-verified")
                    if base.effective_date != record.effective_date:
                        raise _Reject(f"option date {record.effective_date} differs from base date {base.effective_date}")
                parsed[spec.code] = record
                records.append(record)
            except _Reject as exc:
                self.logger.warning("NL Hydro Rate %s not live-verified: %s", spec.code, exc)
        return records

    def _parse_spec(
        self, spec: _Spec, pages: list[DocumentPage], source_url: str, landing: dict[str, float], today: date,
    ) -> TariffRecord:
        anchored = [page for page in pages if re.search(rf"^RATE NO\. {re.escape(spec.code)}\s*$", page.text, re.M)]
        if len(anchored) != 1:
            raise _Reject(f"rate heading found on {len(anchored)} pages")
        page = anchored[0]
        flat = _flat(page.text)
        if not re.search(rf"RATE NO\. {re.escape(spec.code)} {spec.heading}", flat):
            raise _Reject("rate title does not match")
        effective = _page_date(flat, spec, today)
        eligibility = _eligibility(flat)
        if not eligibility or not all(re.search(pattern, flat) for pattern in spec.availability):
            raise _Reject("availability/eligibility text missing or changed")
        if spec.kind != "option" and _UNMODELLED_TERMS.search(flat):
            raise _Reject("page mentions a subsidy, credit, rider or surcharge that is not modelled")

        conditions: list[str] = []
        if spec.kind == "option":
            components = _option_components(flat, spec)
            conditions.append(_option_conditions(flat))
            structure = "mixed"
        else:
            components = _basic_components(flat, spec) + _demand_components(flat, spec) \
                + _energy_components(flat, spec)
            conditions.extend(_billing_conditions(flat, spec))
            has_demand = spec.demand is not None
            structure = "demand" if has_demand else "tiered" if len(
                [component for component in components if component.component_type == "energy"]) > 1 else "flat"
        expected = landing.get(spec.code)
        if expected is not None and spec.kind in ("standard", "diesel_domestic"):
            energy = [component for component in components if component.component_type == "energy"][0]
            if abs(energy.charge_value - expected) > 1e-9:
                raise _Reject("schedule energy rate disagrees with the current-rates page")

        notes = [f"{spec.area}. Source: NL Hydro Schedule of Rates, Rules and Regulations, rate {spec.code}."]
        if spec.kind == "option":
            notes.append(
                f"Optional seasonal adjustment: apply together with base Rate {spec.base_code}; it is not a "
                "standalone tariff and its negative value is a credit, not an energy price.")
        if len(spec.basic) > 1:
            notes.append(
                "Basic Customer Charge rows are mutually exclusive alternatives (service type or amperage); "
                "one row is billed per service, not all rows together.")
        if "Including Municipal Tax and Rate Stabilization Adjustments" in flat:
            notes.append("Rates include municipal tax and rate stabilization adjustments; HST excluded.")
        if conditions:
            label = "Special conditions" if spec.kind == "option" else "Billing conditions, not additive charges"
            notes.append(f"{label}: {'. '.join(condition.rstrip('.') for condition in conditions)}.")
        discount = re.search(
            r"discount of (\d+(?:\.\d+)?)% of the amount of the current month.s bill will be allowed "
            r"if the bill is paid within (\d+) days", flat)
        if discount:
            notes.append(f"{discount.group(1)}% prompt-payment discount if paid within {discount.group(2)} days.")
        for component in components:
            component.effective_date = effective.isoformat()
            component.confidence = "high"
        description = f"{spec.area} - Rate {spec.code}"
        if spec.kind == "option":
            description += f"; apply with base Rate {spec.base_code}"
        record = TariffRecord(
            utility_name=self.utility_name, province=self.province, utility_type="electricity",
            tariff_name=spec.name, tariff_code=spec.code, customer_class=spec.customer_class,
            sub_class=spec.sub_class, description=description, eligibility=eligibility,
            demand_min_kw=spec.demand_min_kw, demand_max_kw=spec.demand_max_kw,
            rate_structure=structure, pricing_method="regulated", effective_date=effective.isoformat(),
            confidence="high", notes=" ".join(notes), components=components,
        )
        return self.mark_live_parsed(
            [record], source_url=source_url, detail=f"PDF page {page.page_number}")[0]

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """
        Parse the official Schedule of Rates linked from the current-rates page.

        Returns only classes proven complete; None if nothing could be verified.
        """
        try:
            html = self.fetch_page(NL_HYDRO_URL)
            if not html:
                self.logger.warning("NL Hydro: empty response from %s", NL_HYDRO_URL)
                return None
            soup = parse_html(html)
            links = find_pdf_links(
                soup, keywords=["schedule-of-rates", "schedule of rates"], base_url=NL_HYDRO_URL)
            if not links:
                self.logger.warning("NL Hydro: no Schedule of Rates PDF link found on %s", NL_HYDRO_URL)
                return None
            landing_text = soup.get_text(" ", strip=True)
            for link in links:
                pages = extract_pdf_pages(self.fetch_bytes(link))
                if not pages:
                    self.logger.warning("NL Hydro: no usable text in %s", link)
                    continue
                records = self.parse_schedule_pages(pages, link, landing_text)
                if records:
                    return records
            return None
        except Exception as exc:
            self.logger.warning("NL Hydro: live scrape error — %s", exc)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Rural Residential (Island Interconnected) ────────────
        records.append(TariffRecord(
            utility_name="NL Hydro",
            province="NL",
            utility_type="electricity",
            tariff_name="Rural Residential Service (Domestic)",
            customer_class="residential",
            sub_class="rural",
            rate_structure="flat",
            effective_date=SEED_RURAL_RESIDENTIAL["effective_date"],
            source_url=SEED_RURAL_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "NL Hydro rural residential rate for island-interconnected customers. "
                "NL Hydro primarily handles generation and transmission but serves "
                "rural areas directly where Newfoundland Power does not operate."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RURAL_RESIDENTIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Monthly basic charge regardless of consumption",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_RURAL_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        # ── Labrador Interconnected Residential ──────────────────
        records.append(TariffRecord(
            utility_name="NL Hydro",
            province="NL",
            utility_type="electricity",
            tariff_name="Labrador Interconnected Residential Service",
            customer_class="residential",
            sub_class="labrador interconnected",
            rate_structure="flat",
            effective_date=SEED_LABRADOR_INTERCONNECTED["effective_date"],
            source_url=SEED_LABRADOR_INTERCONNECTED["source_url"],
            confidence="medium",
            notes=(
                "NL Hydro residential rate for Labrador interconnected system. "
                "Labrador rates are significantly lower than island rates due to "
                "proximity to Churchill Falls hydroelectric generation."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_LABRADOR_INTERCONNECTED["basic_charge_per_month"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_LABRADOR_INTERCONNECTED["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    notes=(
                        "Labrador interconnected rate — substantially lower than island "
                        "rates due to local hydroelectric generation"
                    ),
                ),
            ],
        ))

        # ── General Service (Commercial) ────────────────────────────
        records.append(TariffRecord(
            utility_name="NL Hydro",
            province="NL",
            utility_type="electricity",
            tariff_name="General Service",
            customer_class="commercial",
            sub_class="general service",
            rate_structure="demand",
            effective_date=SEED_GENERAL_SERVICE["effective_date"],
            source_url=SEED_GENERAL_SERVICE["source_url"],
            confidence="medium",
            notes=(
                "NL Hydro general service rate for commercial customers "
                "in rural areas served directly by NL Hydro."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_GENERAL_SERVICE["basic_charge_per_month"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_GENERAL_SERVICE["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    confidence="medium",
                    notes="Applied to billing demand (kW)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_GENERAL_SERVICE["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                ),
            ],
        ))

        return records
