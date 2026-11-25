"""Representative models: crosswalk/coverage (Phase 7A), the modeled-cost engine (Phase 7B), all provinces with
Alberta wires + Rate of Last Resort pairs (Phase 7C), the territories with reviewed percentage riders and before/after-
subsidy costs (method 7T-1, owner decisions 2026-11-24), and method 7S-1: the opt-in simulated-shape sidecar (Ontario
and Alberta market energy priced with simulated BTAP archetype load shapes, replacing Phase 7E's made-up profile) and
province-specific 50-499 kW and 500-4,999 kW example customers."""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional, Union

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
CROSSWALK_PATH = ROOT / "data" / "models" / "crosswalk.json"
USAGE_LEVELS_PATH = ROOT / "data" / "models" / "usage_levels.json"
TAXES_PATH = ROOT / "data" / "models" / "taxes.json"
RATES_PATH = ROOT / "site" / "data" / "rates.json"
BLOCK_PERIODS_PATH = ROOT / "data" / "models" / "block_periods.json"
PERCENTAGE_RIDERS_PATH = ROOT / "data" / "models" / "percentage_riders.json"
SUBSIDIES_PATH = ROOT / "data" / "models" / "subsidies.json"
MARKET_PATH = ROOT / "site" / "data" / "market_pricing_ontario.json"
DEMAND_BOUNDS = "@demand_bounds"
MATCH_FIELDS = ("tariff_code", "tariff_code_regex", "name_regex", "customer_class", "rate_structure")
UNMAPPED = {"rule_id": None, "model": None, "exclude": None, "zone": None}

PathLike = Union[str, Path, None]


def load_crosswalk(path: PathLike = None) -> dict:
    """Read the crosswalk JSON (default data/models/crosswalk.json)."""
    with open(path or CROSSWALK_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def load_usage_levels(path: PathLike = None) -> dict:
    """Read the usage-level definitions (default data/models/usage_levels.json)."""
    with open(path or USAGE_LEVELS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def load_rates(path: PathLike = None) -> list[dict]:
    """Read an export (list of records) or a fixture ({"records": [...]})."""
    with open(path or RATES_PATH, encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("records", []) if isinstance(data, dict) else data


def latest_live_records(rates: Iterable[dict]) -> list[dict]:
    """Latest effective_date per (utility_name, name, customer_class), as the site dedupes, then provenance 'live'."""
    latest: dict[tuple[str, str, str], dict] = {}
    for record in rates:
        if not isinstance(record, dict):
            continue
        key = (record.get("utility_name") or "", record.get("name") or "", record.get("customer_class") or "")
        current = latest.get(key)
        if current is None or (record.get("effective_date") or "") > (current.get("effective_date") or ""):
            latest[key] = record
    return [r for r in latest.values() if r.get("provenance") == "live"]


@lru_cache(maxsize=2048)
def _compiled(regex: str) -> Optional[re.Pattern]:
    try:
        return re.compile(regex)
    except re.error:
        return None


def _fullmatch(regex: Any, value: Any) -> bool:
    pattern = _compiled(regex) if isinstance(regex, str) else None
    return bool(pattern and pattern.fullmatch(value if isinstance(value, str) else ""))


def rule_matches(rule: dict, record: dict) -> bool:
    """True when every criterion of ``rule`` holds for ``record`` (regexes use re.fullmatch)."""
    utility = rule.get("utility", "*")
    if utility not in ("*", None) and utility != record.get("utility_name"):
        return False
    if rule.get("province") and rule["province"] != record.get("province"):
        return False
    if rule.get("fuel") and rule["fuel"] != record.get("utility_type"):
        return False
    match = rule.get("match") or {}
    if not isinstance(match, dict):
        return False
    for field, expected in match.items():
        if field == "tariff_code":
            ok = record.get("tariff_code") == expected
        elif field == "tariff_code_regex":
            ok = _fullmatch(expected, record.get("tariff_code"))
        elif field == "name_regex":
            ok = _fullmatch(expected, record.get("name"))
        elif field in ("customer_class", "rate_structure"):
            ok = record.get(field) == expected
        else:
            ok = False
        if not ok:
            return False
    return True


def _kw(value: Any, default: float) -> float:
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def bands_for_demand(demand_min_kw: Any, demand_max_kw: Any, crosswalk: dict) -> list[str]:
    """Bands whose reference kW the [min, max) demand range covers; else bands containing it; else overlapping."""
    bands = (crosswalk.get("vocabulary") or {}).get("size_bands") or {}
    lo, hi = _kw(demand_min_kw, 0.0), _kw(demand_max_kw, math.inf)
    covered = [b for b, d in bands.items() if any(lo <= ref < hi for ref in d.get("reference_kw") or [])]
    if covered:
        return covered
    edges = {b: (_kw(d.get("min_kw"), 0.0), _kw(d.get("max_kw"), math.inf)) for b, d in bands.items()}
    contained = [b for b, (b_lo, b_hi) in edges.items() if b_lo <= lo and hi <= b_hi]
    return contained or [b for b, (b_lo, b_hi) in edges.items() if lo < b_hi and hi > b_lo]


def resolve_size_band(size_band: Any, record: dict, crosswalk: dict) -> Optional[list[str]]:
    """Normalise a rule size_band (None, id, list or '@demand_bounds') to a list of band ids or None."""
    if size_band is None:
        return None
    if size_band == DEMAND_BOUNDS:
        return bands_for_demand(record.get("demand_min_kw"), record.get("demand_max_kw"), crosswalk)
    if isinstance(size_band, str):
        return [size_band]
    return [str(band) for band in size_band]


def _outcome(rule: dict, record: dict, crosswalk: dict) -> dict:
    spec = rule.get("model")
    if isinstance(spec, dict):
        def resolve(target: dict) -> dict:
            return {"province": rule.get("province") or record.get("province"),
                    "fuel": rule.get("fuel") or record.get("utility_type"),
                    "sector": target.get("sector"), "structure": target.get("structure"),
                    "size_band": resolve_size_band(target.get("size_band"), record, crosswalk)}
        model = resolve(spec)
        # A record that also serves another model, e.g. Union Rate 01/M1 and ATCO Low Use (stored as residential)
        # in the commercial gas models (owner decision 18, 2026-11-20).
        also = [resolve(target) for target in spec.get("also") or [] if isinstance(target, dict)]
        if also:
            model["also"] = also
        return {"rule_id": rule.get("id"), "model": model, "exclude": None, "zone": rule.get("zone") or "default"}
    return {"rule_id": rule.get("id"), "model": None, "exclude": rule.get("exclude"), "zone": rule.get("zone")}


def matching_outcomes(record: dict, crosswalk: dict) -> list[dict]:
    """Outcomes of every rule that matches ``record``, in rule order."""
    try:
        return [_outcome(rule, record, crosswalk) for rule in crosswalk.get("rules") or []
                if isinstance(rule, dict) and rule_matches(rule, record)]
    except (AttributeError, TypeError, ValueError):
        return []


def match_record(record: dict, crosswalk: dict) -> dict:
    """First matching rule's outcome {'rule_id', 'model', 'exclude', 'zone'}; all None when unmapped."""
    try:
        for rule in crosswalk.get("rules") or []:
            if isinstance(rule, dict) and rule_matches(rule, record):
                return _outcome(rule, record, crosswalk)
    except (AttributeError, TypeError, ValueError):
        pass
    return dict(UNMAPPED)


def model_keys(outcome: dict) -> list[tuple]:
    """Concrete (province, fuel, sector, structure, size_band) keys of a mapped outcome, including the models it
    'also' serves; [] otherwise."""
    model = outcome.get("model")
    if not model:
        return []
    return [(target["province"], target["fuel"], target["sector"], target["structure"], band)
            for target in [model] + list(model.get("also") or []) for band in (target.get("size_band") or [None])]


def crosswalk_rule_levels(crosswalk: dict) -> dict[str, list[str]]:
    """Rule id -> the usage-level ids its optional model 'levels' list allows (rules without the list: absent).

    Used when a class's printed eligibility (for example three-phase service only) rules out a reference level that
    its size band would otherwise include (owner decision 2026-11-19, Lethbridge rate 994)."""
    found = {}
    for rule in (crosswalk or {}).get("rules") or []:
        model = rule.get("model") if isinstance(rule, dict) else None
        if isinstance(model, dict) and isinstance(model.get("levels"), list):
            found[rule.get("id")] = [str(level) for level in model["levels"]]
    return found


def key_label(key: tuple) -> str:
    """Printable model key, e.g. 'ON|electricity|commercial|demand|commercial_large'."""
    return "|".join("-" if part is None else str(part) for part in key)


def elective_class_groups(crosswalk: dict) -> dict[str, list[dict]]:
    """Crosswalk 'elective_classes' entries by utility: classes open to the same customers, between which the customer
    chooses (Centra Gas Manitoba Small and Large General Service, owner decision 19, 2026-11-20). Entries need an id,
    a utility and at least two tariff codes."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for entry in (crosswalk or {}).get("elective_classes") or []:
        if (isinstance(entry, dict) and entry.get("id") and entry.get("utility")
                and len(entry.get("tariff_codes") or []) > 1):
            groups[entry["utility"]].append(entry)
    return groups


def cheapest_elective_rows(rows: list[tuple], groups: list[dict]) -> tuple[list[tuple], list[dict]]:
    """Level rows (record, zone, cost without tax, ...) with each elective group reduced to its cheapest computable
    record per zone (ties: the group's tariff-code order), and notes naming the class used and both costs."""
    notes = []
    for group in groups:
        codes = list(group["tariff_codes"])
        for zone in sorted({row[1] for row in rows}, key=str):
            members = [row for row in rows if row[1] == zone and row[0].get("tariff_code") in codes]
            if len(members) < 2:
                continue
            best = min(members, key=lambda row: (round(row[2], 9), codes.index(row[0].get("tariff_code"))))
            rows = [row for row in rows if row is best or not any(row is member for member in members)]
            ordered = sorted(members, key=lambda row: codes.index(row[0].get("tariff_code")))
            notes.append({"group": group["id"], "zone": zone, "chosen": best[0].get("tariff_code"),
                          "costs": [{"record_id": row[0].get("id"), "tariff_code": row[0].get("tariff_code"),
                                     "cost_without_tax": round(row[2], 2)} for row in ordered]})
    return rows, notes


def _signature(outcome: dict) -> str:
    return json.dumps([outcome.get("model"), outcome.get("exclude"), outcome.get("zone")], sort_keys=True)


def _brief(record: dict) -> dict:
    return {field: record.get(field) for field in ("utility_name", "province", "tariff_code", "name", "customer_class")}


def coverage_report(rates: Iterable[dict], crosswalk: dict) -> dict:
    """Mapped/excluded/unmapped counts per utility and province, unmapped records, conflicts and model keys."""
    records = latest_live_records(rates)
    utilities: dict[str, dict] = {}
    provinces: dict[str, Counter] = defaultdict(Counter)
    exclusions: Counter = Counter()
    rule_hits: Counter = Counter()
    keys: dict[str, dict] = {}
    unmapped, conflicts = [], []
    for record in records:
        outcome = match_record(record, crosswalk)
        status = "mapped" if outcome["model"] else "excluded" if outcome["exclude"] else "unmapped"
        name = record.get("utility_name") or ""
        entry = utilities.setdefault(name, {"province": record.get("province"), "fuel": record.get("utility_type"),
                                            "records": 0, "mapped": 0, "excluded": 0, "unmapped": 0})
        entry["records"] += 1
        entry[status] += 1
        provinces[record.get("province") or ""][status] += 1
        if outcome["rule_id"]:
            rule_hits[outcome["rule_id"]] += 1
        if status == "unmapped":
            unmapped.append(_brief(record))
        elif status == "excluded":
            exclusions[outcome["exclude"]] += 1
        for key in model_keys(outcome):
            slot = keys.setdefault(key_label(key), {"utilities": set(), "default_zone_utilities": set(), "records": 0})
            slot["utilities"].add(name)
            slot["records"] += 1
            if outcome["zone"] == "default":
                slot["default_zone_utilities"].add(name)
        outcomes = matching_outcomes(record, crosswalk)
        if len({_signature(o) for o in outcomes}) > 1:
            conflicts.append({**_brief(record), "winning_rule": outcome["rule_id"], "rules": outcomes})
    rule_ids = [r.get("id") for r in crosswalk.get("rules") or [] if isinstance(r, dict)]
    return {
        "totals": {"records": len(records), "mapped": sum(u["mapped"] for u in utilities.values()),
                   "excluded": sum(u["excluded"] for u in utilities.values()),
                   "unmapped": len(unmapped), "utilities": len(utilities), "rules": len(rule_ids)},
        "by_province": {p: dict(c) for p, c in sorted(provinces.items())},
        "by_utility": dict(sorted(utilities.items())),
        "exclusions": dict(exclusions.most_common()),
        "model_keys": {k: {"utilities": sorted(v["utilities"]), "default_zone_utilities": sorted(v["default_zone_utilities"]),
                           "records": v["records"]} for k, v in sorted(keys.items())},
        "unmapped": unmapped,
        "conflicts": conflicts,
        "rule_hits": dict(rule_hits),
        "unused_rules": [rid for rid in rule_ids if not rule_hits.get(rid)],
    }


def format_coverage(report: dict, limit: int = 25) -> str:
    """Short plain-text summary of a coverage report."""
    t = report["totals"]
    lines = [f"Latest live records: {t['records']} across {t['utilities']} utilities; rules: {t['rules']}",
             f"Mapped {t['mapped']} | excluded {t['excluded']} | unmapped {t['unmapped']} | "
             f"conflicting multi-rule matches {len(report['conflicts'])}", "", "By province (mapped/excluded/unmapped):"]
    for prov, counts in report["by_province"].items():
        lines.append(f"  {prov}: {counts.get('mapped', 0)}/{counts.get('excluded', 0)}/{counts.get('unmapped', 0)}")
    lines.append("Exclusions: " + ", ".join(f"{k} {v}" for k, v in report["exclusions"].items()))
    lines.append("")
    lines.append(f"Model keys ({len(report['model_keys'])}; utilities / default-zone utilities / records):")
    for label, slot in report["model_keys"].items():
        lines.append(f"  {label}: {len(slot['utilities'])} / {len(slot['default_zone_utilities'])} / {slot['records']}")
    for title, rows in (("Unmapped", report["unmapped"]), ("Conflicts (first rule wins)", report["conflicts"])):
        lines.append("")
        lines.append(f"{title}: {len(rows)}")
        for row in rows[:limit]:
            extra = f" -> {row['winning_rule']} over {[o['rule_id'] for o in row['rules'][1:]]}" if "rules" in row else ""
            lines.append(f"  {row['utility_name']} [{row['tariff_code']}] {row['name']}{extra}")
    if report["unused_rules"]:
        lines.append("")
        lines.append("Rules that matched no record: " + ", ".join(report["unused_rules"]))
    return "\n".join(lines)


# Phase 7B engine: per-record modeled monthly cost, per-utility aggregation, taxes and statistics.

# 7C-3 (user decision 2026-10-30): phase/amperage fixed-charge variants priced for the reference customer.
# 7D-1 (owner decision 2026-11-04): residential default-supply gas in each utility's native volume unit.
# 7D-2 (owner decisions 2026-11-20): commercial general-service gas for small and mid-size buildings (class chosen by
# reviewed volume bounds), Energir Rate D1, Liberty Utility Gas as New Brunswick's reference supply, and the small
# business electricity levels s1 = 2,000 kWh at 14 kW and s2 = 10,000 kWh at 40 kW.
# 7T-1 (owner decisions 64-75, 2026-11-24): territorial residential and small-commercial models, reviewed percentage
# riders (data/models/percentage_riders.json), costs before and after automatic subsidies (data/models/subsidies.json,
# before tax only), government classes out of the medians and interim rates labelled.
# 7S-1 (requested 2026-11-25): an opt-in Ontario and Alberta sidecar priced market energy with the simulated BTAP
# archetypes' load shapes, replacing the Phase 7E made-up profile, and the 50-499 kW and 500-4,999 kW example customers
# differed by province.
# 7S-2 (owner decisions 119-123, 2026-11-25): the Ontario and Alberta 50-499 kW and 500-4,999 kW models price their
# market energy in the main table from the general load shape of the province's simulated buildings in the size band
# (usage_levels market_energy_shapes), labelled estimated and falling back to market_energy_pending when an input fails;
# every province uses m1 = 25,000 kWh at 100 kW and l1 = 250,000 kWh at 1,000 kW (a level's optional "provinces" list
# is kept but unused).
METHOD_VERSION = "7S-2"
# Every percentage component of a record in these jurisdictions needs a reviewed percentage_riders.json entry; one without
# makes the record not computable. Provinces keep disclosing percentage adjustments unapplied (owner decision 64).
TERRITORIES = ("YT", "NT", "NU")
PERCENT_TREATMENTS = ("apply", "exclude", "subsidy")
PERCENT_PREFIX = "percentage_rider:"
SUBSIDY_TREATMENTS = ("reference_rates", "first_block_price", "per_kwh_credit", "disclose")
BEFORE_TAX_ONLY = "before_tax_only"
MODEL_FUELS = ("electricity", "gas")
# Gas is priced in its native billing unit and never converted between m3 and GJ (owner decision 2026-11-04;
# a future cross-unit comparison converts toward m3, with its heating-value source chosen then).
GAS_VOLUME_PRICES = {"m3": ("$/m³", "$/m3"), "GJ": ("$/gj",)}
GAS_BLOCK_UNITS = {"m3": ("m³/month", "m3/month"), "GJ": ("gj/month",)}
# Daily gas blocks (Energir D1 "m³ per day ... multiplied by the number of days") scale by the average month (decision 8).
GAS_DAILY_BLOCK_UNITS = {"m3": ("m³/day", "m3/day"), "GJ": ("gj/day",)}
# Annual-volume units: class eligibility and fixed-charge bands selected by 12 x the level's monthly volume.
GAS_ANNUAL_UNITS = {"m3": ("m³/year", "m3/year"), "GJ": ("gj/year",)}
VOLUME_LABELS = {"kwh": "kWh", "m3": "m³", "GJ": "GJ"}
# Gas commodity/supply components play the role electricity energy components play.
ENERGY_TYPES = ("energy", "commodity")
# Residential (7D-1) and commercial general service (7D-2). Contract-demand, interruptible, seasonal and peaking gas
# classes are crosswalk exclusions until their own decision (owner decision 4, 2026-11-20); any other gas key outside
# these sectors would still be withheld.
GAS_MODEL_SECTORS = ("residential", "commercial")
ZONE_POLICIES = ("median_of_zones", "default_only")
ZONE_POLICY_TEXT = {
    "median_of_zones": "the median of each utility's standard rate-zone records covering the level",
    "default_only": "each utility's default-zone record(s) only (median if several)",
}
DEFAULT_DAYS_PER_MONTH = 365.25 / 12
DEFAULT_POWER_FACTOR = 0.9
OUTLIER_PCT = 0.30
OUTLIER_IQR_FACTOR = 1.5
OUTLIER_MIN_N = 3
BUCKETS = ("fixed", "energy", "distribution_volumetric", "demand", "transmission", "regulatory", "riders", "carbon",
           "other")
BUCKET_TEXT = {
    "fixed": "fixed charges per month (service, metering)",
    "energy": "energy/commodity per kWh, by time-of-use period, tier or season",
    "distribution_volumetric": "distribution and delivery charges per kWh (incl. low-voltage service)",
    "demand": "distribution and delivery charges per kW-month (kVA at the power factor)",
    "transmission": "retail transmission charges",
    "regulatory": "regulatory charges (e.g. wholesale market service, rural rate protection)",
    "riders": "mandatory rate riders",
    "carbon": "carbon charges",
    "other": "other mandatory charges",
}
BASIS_UNITS = {"month": "$/month", "kwh": "$/kWh", "kw": "$/kW-month", "percent": "% of base charges"}
TAX_BASES = ("pre_tax_subtotal", "pre_rebate_subtotal", "energy_charge_subtotal")
TAX_KINDS = ("sales_tax", "rebate")
PROVINCE_NAMES = {"AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick",
                  "NL": "Newfoundland and Labrador", "NS": "Nova Scotia", "NT": "Northwest Territories",
                  "NU": "Nunavut", "ON": "Ontario", "PE": "Prince Edward Island", "QC": "Quebec",
                  "SK": "Saskatchewan", "YT": "Yukon"}
# Alberta counts service areas (owner decision 2026-11-19): a wires + Rate of Last Resort pair, a city that publishes
# both halves (Lethbridge, Red Deer) or Medicine Hat's bundled city rate.
UTILITY_NOUNS = {("ON", "electricity"): ("distributor", "distributors"),
                 ("AB", "electricity"): ("service area", "service areas")}
DEFAULT_NOUNS = ("utility", "utilities")
STRUCTURE_LABELS = {"flat": "flat-rate", "tiered": "tiered", "tou": "time-of-use (TOU)",
                    "tiered_tou": "tiered time-of-day", "ulo": "ultra-low overnight (ULO)",
                    "critical_peak": "critical-peak", "seasonal": "seasonal", "demand": "demand-billed",
                    "demand_tou": "demand time-of-use", "interruptible": "interruptible"}
NOT_APPLIED = {("ON", "electricity"): (
    "distribution loss factors (Ontario bills energy, transmission and regulatory charges on loss-adjusted kWh)",
    "Class A Global Adjustment"),
    ("AB", "electricity"): (
    "municipal franchise and local access fees",
    "competitive retail energy contracts (only the Rate of Last Resort is priced)"),
    # Owner decision 23 (2026-11-20): named in the method, no line while the price is below the trigger.
    ("AB", "gas"): (
    "the Alberta Natural Gas Rebate Program (an automatic per-GJ rebate for customers using under 2,500 GJ a year, "
    "paid only when the Alberta gas price exceeds $6.50/GJ; nothing is credited while the price is below that trigger)",
    "municipal franchise fees")}
EXCLUSION_TEXT = {
    "expired": "expired before the as-of date",
    "not_yet_effective": "not yet in effect at the as-of date",
    "alternative": "conditional alternative to another charge",
    "optional": "optional",
    "conditional": "conditional (applies only to some customers)",
    "market_pending": "market energy price with no stored value (estimated only where the model's energy basis says so)",
    "market_indexed_non_energy": "market-indexed non-energy charge with no stored value (left out until market prices "
                                 "are modelled)",
    "no_value": "no published value",
    "percentage_base_not_computable": "percentage adjustment whose base is not computable",
    "percentage_excluded": "percentage of the whole bill or of revenues billed (reviewed: disclosed, not applied)",
    "percentage_unreviewed": "percentage rider without a reviewed data/models/percentage_riders.json entry",
    "subsidy": "automatic subsidy: left out of the cost before subsidies, applied only in the after-subsidy cost",
    "unsupported_unit": "unit not supported by the engine",
    "variant_not_selected": "fixed-charge variant for another reference customer",
}
COMPONENT_RULES = (
    "Included: unconditional components in effect at the as-of date (fixed, energy, distribution, demand, "
    "transmission, regulatory, riders, carbon, other) in $/month, $/30 days, $/day, $/year, $/two months (/ 2), "
    "$/metering device/day (one metering device), $/kWh, $/MWh, $/kW, $/kVA (per month or per day), and gas in the "
    "model's own unit ($/m³ or $/GJ).",
    "Included as reference-customer charges: conditional or optional components that a reviewed usage_levels.json "
    "'reference_customer' entry lists for the province, fuel and sector (Ontario: Class B CBR, Standard Supply "
    "Service administration, non-wholesale-market-participant riders, and non-RPP Class B Global Adjustment riders "
    "at 50 kW and over; Quebec gas: Energir's renewable-gas socialization charges and its load balancing below "
    "75,000 m³ a year; New Brunswick gas: Liberty Utility Gas supply), itemized with reason "
    "'reference_customer:<id>'. An entry with an annual-volume limit makes the record not computable at levels "
    "outside it (Energir's load-factor formula price at 75,000 m³ a year or more).",
    "Included as reference-customer fixed-charge variants: a fixed charge published as variants of one charge "
    "(unconditional variants or alternatives) is priced with the one variant that a usage_levels.json "
    "'fixed_charge_variants' rule selects: by level (user decision 2026-10-30: homes single-phase 200 A service; "
    "small business single phase at s1 and three phase at s2, 14 and 40 kW since 7D-2), by the monthly peak of a "
    "peak_month_factors entry (Liberty's customer charges) or by the band containing 12 x the level's volume "
    "(annual-volume bands such as Energir's basic fee); itemized with reason 'fixed_charge_variant:<id>'.",
    "Excluded and counted: other conditional components (sub_component 'conditional'/'conditional_credit' or "
    "notes starting 'Conditional'), alternatives, optional components, components expired (end_date before the "
    "as-of date) or not yet effective, value-less market energy (model state market_energy_pending), value-less "
    "market-indexed non-energy charges (named in the method; the state does not change) and percentage "
    "adjustments (no computable base) other than the reviewed ones below.",
    "Percentage riders (owner decision 64, 2026-11-24): a percentage component with a reviewed "
    "data/models/percentage_riders.json entry is priced as its percentage of the base charges the entry names (never "
    "of other riders), itemized with reason 'percentage_rider:<id>'; reviewed percentages of the whole bill or of "
    "revenues billed are disclosed, not applied; reviewed percentage subsidies apply only in the after-subsidy cost. "
    "In the territories a percentage component without a reviewed entry makes its record not computable.",
    "Territorial subsidies (owner decisions 67-70, 74 and 76-78, 2026-11-24): the cost before subsidies leaves subsidy "
    "prices and credits out; the after-subsidy cost (before tax only) applies only the automatic subsidies of "
    "data/models/subsidies.json and the reviewed percentage subsidies in force at the as-of date. Reference rates "
    "(GREP) and first-block prices (TPSP) are all-in: they replace the zone's whole tariff, or the whole per-kWh price "
    "of the first-block kWh; seasonal first blocks are priced per season and month-weighted.",
    "Thresholds as published: demand charges with a demand threshold bill only the kW above it; demand and energy "
    "blocks use their published bounds (kVA bounds at the power factor; per-kW and per-kVA energy blocks scale "
    "with the level's demand; per-day blocks x days per month; a block published in bare 'kWh' only with the "
    "first matching reviewed entry of data/models/block_periods.json: month as published, two months / 2, day x "
    "days per month; a null period or no entry is not computable); an unseasoned first block applies in every "
    "season of the seasonal blocks that follow it.",
    "Class selection: a record serves a level only when its published eligibility covers it: kW and kWh bounds for "
    "electricity; for gas, the reviewed crosswalk usage_bounds (12 x the level's monthly volume, or its monthly "
    "peak), else stored annual bounds (a level exactly on a stored bound is not computable without a reviewed "
    "entry). Elective classes of one utility (crosswalk elective_classes) count once, as the cheapest.",
    "Not computable (record left out at that level, reason listed): a charge published only as conditional "
    "alternatives, fixed charges published as variants of one charge (e.g. by amperage or phase) when no "
    "usage_levels.json 'fixed_charge_variants' rule of the level selects exactly one variant, an unconditional "
    "component without value or in an unsupported unit (e.g. per billing period), TOU periods without an official "
    "share, ambiguous tier thresholds, seasons that do not cover the year, demand charges at a level without kW.",
)
_PROVENANCE_PREFIX = re.compile(r"^\s*Provenance:\s*[\w-]+\.\s*")
_PER_30_DAYS = re.compile(r"\bper 30 days\b", re.IGNORECASE)
_STARTS_CONDITIONAL = re.compile(r"Conditional\b")
_STARTS_OPTIONAL = re.compile(r"Optional\b")
_STARTS_ALTERNATIVE = re.compile(r"Alternative\b")
_WORD_ALTERNATIVE = re.compile(r"\balternative\b", re.IGNORECASE)
_MONTH_RE = re.compile(r"\b(january|february|march|april|may|june|july|august|september|october|november|december|"
                       r"jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec)\b\.?\s*(\d{1,2})?", re.IGNORECASE)
_MONTHS = {name: i for i, name in enumerate(
    ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"), 1)}
_PERIOD_END_RE = re.compile(r"\bto\s+([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})")
_TIER_UNITS = ("kwh/month", "kwh per month")
REFERENCE_PREFIX = "reference_customer:"
REFERENCE_MATCH_FIELDS = ("notes_regex", "name_regex")
VARIANT_PREFIX = "fixed_charge_variant:"
BLOCK_PERIOD_MATCH_FIELDS = ("tariff_code", "tariff_code_regex", "name_regex")
BLOCK_PERIOD_WORDS = {"month": "per month", "two_months": "per two months, halved",
                      "day": "per day, x days per month"}
ESTIMATE_LABEL = "Estimated market energy"
_DEFAULT: Any = object()


def load_taxes(path: PathLike = None) -> dict:
    """Read the tax and rebate table (default data/models/taxes.json)."""
    with open(path or TAXES_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and len(value) >= 10:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _as_of(value: Union[date, str, None]) -> date:
    return _as_date(value) or datetime.now(timezone.utc).date()


def _note_body(component: dict) -> str:
    return _PROVENANCE_PREFIX.sub("", component.get("notes") or "", count=1).strip()


def component_exclusion(component: dict, as_of: Union[date, str, None] = None) -> Optional[str]:
    """Reason a component is left out of a modeled cost (see EXCLUSION_TEXT), or None when it is priced."""
    as_of = _as_of(as_of)
    end = _as_date(component.get("end_date"))
    if end is not None and end < as_of:
        return "expired"
    start = _as_date(component.get("effective_date"))
    if start is not None and start > as_of:
        return "not_yet_effective"
    body = _note_body(component)
    sub = (component.get("sub_component") or "").strip().lower()
    conditional = sub in ("conditional", "conditional_credit", "conditional alternative") or bool(
        _STARTS_CONDITIONAL.match(body))
    if sub in ("alternative", "conditional alternative") or _STARTS_ALTERNATIVE.match(body) or (
            conditional and _WORD_ALTERNATIVE.search(body)):
        return "alternative"
    if sub == "optional" or _STARTS_OPTIONAL.match(body):
        return "optional"
    if conditional:
        return "conditional"
    if component.get("charge_value") is None:
        if not component.get("market_reference"):
            return "no_value"
        return "market_pending" if component.get("component_type") == "energy" else "market_indexed_non_energy"
    return None


def reference_customer_entries(usage_levels: Optional[dict], province: Any, fuel: Any, sector: Any) -> list[dict]:
    """usage_levels 'reference_customer' entries for a province, fuel (missing = any fuel) and sector."""
    return [entry for entry in (usage_levels or {}).get("reference_customer") or []
            if isinstance(entry, dict) and entry.get("id") and entry.get("province") == province
            and entry.get("fuel", fuel) == fuel and sector in (entry.get("sectors") or [])]


def reference_customer_match(component: dict, entries: Iterable[dict], reason: str = "conditional") -> Optional[str]:
    """Id of the first entry whose notes_regex/name_regex all fully match the component (notes without the
    provenance prefix); None when none does. An entry unlocks only components excluded for its 'exclusion' reason
    ('conditional' by default; 'optional' for a reviewed default supply such as Liberty Utility Gas, owner decision 7,
    2026-11-20). Entries with no or unknown criteria never match."""
    fields = {"notes_regex": _note_body(component), "name_regex": component.get("component_name") or ""}
    for entry in entries:
        match = entry.get("match")
        if entry.get("exclusion", "conditional") != reason:
            continue
        if isinstance(match, dict) and match and set(match) <= set(REFERENCE_MATCH_FIELDS) and all(
                _fullmatch(regex, fields[field]) for field, regex in match.items()):
            return entry["id"]
    return None


def _within(value: float, bounds: dict) -> bool:
    """True when value lies inside {'min', 'min_inclusive', 'max', 'max_inclusive'} (a missing bound is open)."""
    lo, hi = bounds.get("min"), bounds.get("max")
    if lo is not None and (value < float(lo) or (value == float(lo) and not bounds.get("min_inclusive", True))):
        return False
    if hi is not None and (value > float(hi) or (value == float(hi) and not bounds.get("max_inclusive", True))):
        return False
    return True


def _bounds_text(bounds: dict, unit: str) -> str:
    parts = []
    if bounds.get("min") is not None:
        parts.append(f"{'at least' if bounds.get('min_inclusive', True) else 'more than'} {float(bounds['min']):,.0f}")
    if bounds.get("max") is not None:
        parts.append(f"{'at most' if bounds.get('max_inclusive', True) else 'less than'} {float(bounds['max']):,.0f}")
    return " and ".join(parts) + f" {VOLUME_LABELS.get(unit, unit)}" if parts else "any volume"


def _variant_rule_kind(rule: dict) -> Optional[str]:
    """'levels' (selected by usage-level id), 'peak_month' (by the level's monthly peak), 'annual_volume_band' (by 12 x
    the level's volume) or None for a malformed rule, which never applies."""
    match = rule.get("match")
    if not isinstance(match, dict) or "name_regex" not in match:
        return None
    if rule.get("select") == "annual_volume_band":
        return "annual_volume_band" if set(match) == {"name_regex"} else None
    if isinstance(rule.get("peak_month"), dict):
        return "peak_month" if set(match) <= {"name_regex", "tariff_code"} else None
    if isinstance(rule.get("levels"), list):
        return "levels" if set(match) == {"name_regex"} else None
    return None


def fixed_charge_variant_rules(usage_levels: Optional[dict], fuel: Any, sector: Any,
                               province: Any = None) -> list[dict]:
    """usage_levels 'fixed_charge_variants' rules for a fuel (missing = any fuel), sector and province (missing = any
    province); a rule without an id or a valid kind (_variant_rule_kind) never applies."""
    return [rule for rule in (usage_levels or {}).get("fixed_charge_variants") or []
            if isinstance(rule, dict) and rule.get("id") and rule.get("fuel", fuel) == fuel
            and sector in (rule.get("sectors") or []) and rule.get("province", province) == province
            and _variant_rule_kind(rule) is not None]


def peak_month_factor(usage_levels: Optional[dict], province: Any, fuel: Any, sector: Any) -> Optional[dict]:
    """The usage_levels 'peak_month_factors' entry (ratio of the peak month to the average month) for a province, fuel
    and sector, or None. Used where a class or charge follows the monthly peak rather than the average month (Liberty
    Gas NB, owner decision 17, 2026-11-20)."""
    for entry in (usage_levels or {}).get("peak_month_factors") or []:
        if (isinstance(entry, dict) and entry.get("id") and entry.get("province") == province
                and entry.get("fuel", fuel) == fuel and sector in (entry.get("sectors") or [])
                and isinstance(entry.get("factor"), (int, float)) and entry["factor"] > 0):
            return entry
    return None


def price_basis(component: dict, days_per_month: float = DEFAULT_DAYS_PER_MONTH,
                power_factor: float = DEFAULT_POWER_FACTOR, volume_unit: str = "kwh"
                ) -> Optional[tuple[str, float, list[str]]]:
    """(basis 'month'|'kwh'|'kw'|'percent', factor to $/month, $/kWh or $/kW-month, conversions); None if unknown.

    Basis 'kwh' means "per unit of the level's monthly volume": kWh for electricity, or the gas model's native
    ``volume_unit`` ('m3' or 'GJ'); a gas model accepts only its own unit, so a $/GJ charge in an m3 model (or any
    $/kWh charge) is unsupported and fails closed."""
    unit = re.sub(r"\s+", " ", (component.get("charge_unit") or "").strip().lower())
    dpm = f"{days_per_month:g}"
    if unit.startswith("%") or unit.startswith("fraction"):
        return "percent", 1.0, []
    fixed = {"$/month": (1.0, []), "$/30 days": (days_per_month / 30, [f"$/30 days x {dpm}/30"]),
             "$/day": (days_per_month, [f"$/day x {dpm}"]), "$/year": (1 / 12, ["$/year / 12"]),
             "$/two months": (0.5, ["$/two months / 2"]),
             # One metering device (owner decision 8, 2026-11-20: Energir D1 basic fee).
             "$/metering device/day": (days_per_month, [f"$/metering device/day x {dpm} (one metering device)"])}
    if unit in fixed:
        return ("month",) + fixed[unit]
    if volume_unit != "kwh":
        return ("kwh", 1.0, []) if unit in GAS_VOLUME_PRICES.get(volume_unit, ()) else None
    if unit == "$/kwh":
        return "kwh", 1.0, []
    if unit == "$/mwh":
        return "kwh", 0.001, ["$/MWh / 1,000"]
    match = re.fullmatch(r"\$/(kw|kva)(?:[/-](month|day))?", unit)
    if not match:
        return None
    factor, conversions = 1.0, []
    if match.group(2) == "day":
        factor *= days_per_month
        conversions.append(f"$/{match.group(1)}/day x {dpm}".replace("kva", "kVA").replace("kw", "kW"))
    elif _PER_30_DAYS.search(component.get("notes") or ""):
        factor *= days_per_month / 30
        conversions.append(f"demand charge published per 30 days x {dpm}/30")
    if match.group(1) == "kva":
        factor /= power_factor
        conversions.append(f"kVA = kW / {power_factor:g}")
    return "kw", factor, conversions


def months_from_text(text: Any) -> Optional[list[int]]:
    """Months named by a season text ('12,1,2', 'Sep-Apr', 'November 1 - April 30'); None when unparseable."""
    if not isinstance(text, str) or not text.strip():
        return None
    text = text.strip()
    if re.fullmatch(r"\d{1,2}(?:\s*,\s*\d{1,2})*", text):
        months = [int(part) for part in text.split(",")]
        return months if all(1 <= m <= 12 for m in months) and len(set(months)) == len(months) else None
    found = [(_MONTHS[m.group(1).lower()[:3]], m.group(2)) for m in _MONTH_RE.finditer(text)]
    if len(found) != 2 or not re.search(r"[-\u2013]|\bto\b|\bthrough\b", text):
        return None
    (start, _), (end, end_day) = found
    if end_day == "1" and end != start:
        end = 12 if end == 1 else end - 1
    months = [start]
    while months[-1] != end:
        months.append(months[-1] % 12 + 1)
    return months


def season_months(component: dict, province: Optional[str],
                  usage_levels: Optional[dict]) -> tuple[Optional[list[int]], Optional[str]]:
    """Months a seasonal component applies in (None = all year) and a problem text when unresolvable."""
    label, text = component.get("season"), component.get("season_months")
    if not label and not text:
        return None, None
    parsed = months_from_text(text)
    configured = None
    for key, entry in ((usage_levels or {}).get("seasons") or {}).items():
        if province and key.startswith(f"{province}_") and isinstance(entry, dict) and isinstance(entry.get(label), dict):
            configured = entry[label].get("months")
            break
    if configured and parsed and sorted(configured) != sorted(parsed):
        return None, f"season '{label}' ({text}) differs from usage_levels months {configured}"
    months = configured or parsed
    if not months:
        return None, f"season '{label}' months not resolvable from {text!r}"
    return sorted({int(m) for m in months}), None


def _tou_share_in_force(entry: dict, as_of: date) -> Optional[bool]:
    """Whether a tou_shares entry is in force on ``as_of``: effective_date <= as_of < end_date, both optional ISO
    dates where a missing or null bound is open (the window rule of tax_lines()). None when a bound is given but is
    not an ISO date, so a typo can never widen the window."""
    bounds: list[Optional[date]] = []
    for field in ("effective_date", "end_date"):
        raw = entry.get(field)
        parsed = _as_date(raw)
        if raw is not None and parsed is None:
            return None
        bounds.append(parsed)
    start, end = bounds
    return (start is None or start <= as_of) and (end is None or as_of < end)


def find_tou_shares(usage_levels: Optional[dict], province: Any, fuel: Any, structure: Any, sector: Any,
                    as_of: Union[date, str, None] = None) -> tuple[Optional[str], Optional[dict]]:
    """(id, entry) of the usage_levels 'tou_shares' set in force for a model key; (None, None) when there is none.

    Inputs: the usage_levels document, the model's province, fuel, rate structure and sector (residential or a
    commercial size band) and the as-of date (date or ISO string; None = today, UTC). An entry matches when its
    'applies_to' holds (province; fuel, missing = any; structure, one name or a list; sectors) and the as-of date is
    inside its optional effective_date/end_date window (see _tou_share_in_force); undated entries match every date.
    An entry's 'shares' are fractions of monthly kWh keyed by component tou_period label.

    Fails closed with (None, None), which leaves the model's TOU energy not computable ("no matching share set"),
    when more than one entry is in force for the key or a matching entry has a malformed date.
    """
    when = _as_of(as_of)
    in_force: list[tuple[str, dict]] = []
    for key, entry in ((usage_levels or {}).get("tou_shares") or {}).items():
        applies = entry.get("applies_to") if isinstance(entry, dict) else None
        if not isinstance(applies, dict):
            continue
        structures = applies.get("structure")
        structures = [structures] if isinstance(structures, str) else list(structures or [])
        if not (applies.get("province") == province and applies.get("fuel", fuel) == fuel and structure in structures
                and sector in (applies.get("sectors") or [])):
            continue
        window = _tou_share_in_force(entry, when)
        if window is None:
            return None, None
        if window:
            in_force.append((key, entry))
    # Two share sets in force at once is a data error, never settled by file order (fail-closed rule, 2026-10-30 plan).
    return in_force[0] if len(in_force) == 1 else (None, None)


def bucket_of(component_type: Any, basis: str) -> str:
    """Bucket of a priced component; distribution/delivery charges split by unit basis."""
    if component_type in ("distribution", "delivery"):
        return {"kwh": "distribution_volumetric", "kw": "demand"}.get(basis, "fixed")
    return {"fixed": "fixed", "energy": "energy", "commodity": "energy", "demand": "demand",
            "transmission": "transmission", "regulatory": "regulatory", "rider": "riders",
            "carbon": "carbon"}.get(component_type, "other")


def gas_volume_unit(records: Iterable[dict]) -> Optional[str]:
    """The single native volume unit ('m3' or 'GJ') that a gas model's records price; None if mixed or absent."""
    found: set[str] = set()
    for record in records:
        for comp in record.get("components") or []:
            unit = re.sub(r"\s+", " ", (comp.get("charge_unit") or "").strip().lower())
            found.update(track for track, units in GAS_VOLUME_PRICES.items() if unit in units)
    return found.pop() if len(found) == 1 else None


def _context(province: Any, fuel: Any, structure: Any, sector: Any, usage_levels: Optional[dict],
             as_of: date, block_periods: Optional[list] = None, volume_unit: str = "kwh",
             percentage_riders: Optional[list] = None, subsidies: Optional[dict] = None) -> dict:
    """Pricing inputs shared by every record of one model key at the as-of date.

    Inputs: the model's province, fuel, rate structure and sector (residential or a commercial size band), the
    usage_levels document, the as-of date, the usable block_periods entries, the usable percentage_riders entries and the
    subsidies configuration (subsidies_config). Returns days per month and the kVA power factor (module defaults when
    the document has none), the TOU share set in force on the as-of date (find_tou_shares; shares_id None unless
    exactly one validly dated set is in force, so TOU energy is then not computable), the reference-customer entries,
    the fixed-charge variant rules, the block periods, the percentage-rider entries (with 'percent_review' true in the
    territories, where an unreviewed percentage component is not computable) and the subsidies configuration.
    """
    usage_levels = usage_levels or {}
    shares_id, entry = find_tou_shares(usage_levels, province, fuel, structure, sector, as_of)
    return {"as_of": as_of, "province": province, "fuel": fuel, "sector": sector, "usage_levels": usage_levels,
            "days_per_month": float(usage_levels.get("days_per_month") or DEFAULT_DAYS_PER_MONTH),
            "power_factor": float(usage_levels.get("power_factor_for_kva") or DEFAULT_POWER_FACTOR),
            "shares_id": shares_id, "shares": (entry or {}).get("shares"), "shares_entry": entry,
            "reference": reference_customer_entries(usage_levels, province, fuel, sector),
            "variant_rules": fixed_charge_variant_rules(usage_levels, fuel, sector, province),
            "peak_factor": peak_month_factor(usage_levels, province, fuel, sector),
            "block_periods": [e for e in block_periods or [] if isinstance(e, dict)], "volume_unit": volume_unit,
            "percent_entries": [e for e in percentage_riders or [] if isinstance(e, dict)],
            "percent_review": province in TERRITORIES, "subsidies": subsidies}


def _block_period_problem(entry: Any) -> Optional[str]:
    if not isinstance(entry, dict) or not entry.get("id") or not entry.get("utility"):
        return "id and utility are required"
    match = entry.get("match")
    if not isinstance(match, dict) or not match or not set(match) <= set(BLOCK_PERIOD_MATCH_FIELDS):
        return "match must use tariff_code, tariff_code_regex or name_regex"
    if "threshold_period" not in entry:
        return "threshold_period missing"
    if not entry.get("reviewed"):
        return "not reviewed"
    return None


def block_periods_config(data: Any) -> dict:
    """Usable entries of a block_periods document ({'entries': [...]}) or entry list; unreviewed or malformed entries
    are skipped with a reason, so they never apply."""
    doc = data if isinstance(data, dict) else {"entries": data if isinstance(data, list) else []}
    entries, skipped = [], []
    for entry in doc.get("entries") or []:
        problem = _block_period_problem(entry)
        if problem:
            skipped.append({"id": entry.get("id") if isinstance(entry, dict) else None, "reason": problem})
        else:
            entries.append(entry)
    return {"version": doc.get("version"), "status": doc.get("status"), "problem": doc.get("problem"),
            "entries": entries, "skipped": skipped}


def load_block_periods(path: PathLike = None) -> dict:
    """Reviewed periods of bare-'kWh' block thresholds (default data/models/block_periods.json). A missing or unreadable
    file gives no entries (those blocks stay not computable) and states the problem; it never fails a build."""
    target = Path(path or BLOCK_PERIODS_PATH)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {**block_periods_config(None), "problem": f"{target.name} not found"}
    except (OSError, ValueError) as exc:
        return {**block_periods_config(None), "problem": f"{target.name} unreadable ({exc})"}
    if not isinstance(data, dict):
        return {**block_periods_config(None), "problem": f"{target.name} is not a JSON object"}
    return block_periods_config(data)


def block_period_entry(record: dict, components: Iterable[dict], entries: Iterable[dict]) -> Optional[dict]:
    """First block_periods entry for the record: same utility, every match criterion holds (tariff_code exact,
    tariff_code_regex/name_regex full match) and, when given, component_name_regex fully matches the name of at least
    one block component."""
    names = [comp.get("component_name") or "" for comp in components]
    for entry in entries:
        match = entry.get("match") or {}
        if entry.get("utility") != record.get("utility_name") or not match:
            continue
        if "tariff_code" in match and record.get("tariff_code") != match["tariff_code"]:
            continue
        if "tariff_code_regex" in match and not _fullmatch(match["tariff_code_regex"], record.get("tariff_code")):
            continue
        if "name_regex" in match and not _fullmatch(match["name_regex"], record.get("name")):
            continue
        regex = entry.get("component_name_regex")
        if regex is not None and not any(_fullmatch(regex, name) for name in names):
            continue
        return entry
    return None


def _regex_ok(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and _compiled(value) is not None


def _read_config(path: PathLike, default: Path) -> tuple[Optional[dict], Optional[str]]:
    """(document, problem) of a reviewed JSON configuration; a missing, unreadable or non-object file gives a problem,
    never an exception, so the build continues with the affected figures not computable."""
    target = Path(path or default)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, f"{target.name} not found"
    except (OSError, ValueError) as exc:
        return None, f"{target.name} unreadable ({exc})"
    if not isinstance(data, dict):
        return None, f"{target.name} is not a JSON object"
    return data, None


def _percentage_entry_problem(entry: Any) -> Optional[str]:
    if not isinstance(entry, dict) or not entry.get("id") or not entry.get("utility"):
        return "id and utility are required"
    match = entry.get("match")
    if (not isinstance(match, dict) or not _regex_ok(match.get("component_name_regex"))
            or not set(match) <= {"component_name_regex", "tariff_code_regex"}
            or not all(_regex_ok(value) for value in match.values())):
        return "match needs a valid component_name_regex (and optionally tariff_code_regex)"
    treatment = entry.get("treatment")
    if treatment not in PERCENT_TREATMENTS:
        return f"treatment must be one of {', '.join(PERCENT_TREATMENTS)}"
    if treatment != "exclude" and not _regex_ok((entry.get("base") or {}).get("component_name_regex")):
        return "base.component_name_regex is required"
    if treatment == "subsidy":
        limit = entry.get("limit")
        if limit is not None and (not isinstance(limit, dict) or limit.get("period") != "month"
                                  or isinstance(limit.get("kwh"), bool) or not isinstance(limit.get("kwh"), (int, float))
                                  or limit["kwh"] <= 0):
            return "limit needs kwh above 0 and period 'month'"
        if not isinstance(entry.get("with_riders", []), list):
            return "with_riders must be a list of entry ids"
    if not (entry.get("quote") and entry.get("source_url") and entry.get("decided")):
        return "quote, source_url and decided are required"
    if not entry.get("reviewed"):
        return "not reviewed"
    return None


def percentage_riders_config(data: Any) -> dict:
    """Usable entries of a percentage_riders document ({'entries': [...]}) or entry list; unreviewed or malformed
    entries are skipped with a reason, so they never apply (a territorial component they would match stays
    unreviewed and its record not computable)."""
    doc = data if isinstance(data, dict) else {"entries": data if isinstance(data, list) else []}
    entries, skipped = [], []
    for entry in doc.get("entries") or []:
        problem = _percentage_entry_problem(entry)
        if problem:
            skipped.append({"id": entry.get("id") if isinstance(entry, dict) else None, "reason": problem})
        else:
            entries.append(entry)
    return {"version": doc.get("version"), "status": doc.get("status"), "rule": doc.get("rule"),
            "problem": doc.get("problem"), "entries": entries, "skipped": skipped}


def load_percentage_riders(path: PathLike = None) -> dict:
    """Reviewed percentage riders (default data/models/percentage_riders.json, owner decision 64). A missing or
    unreadable file gives no entries (territorial percentage components are then not computable) and states the
    problem; it never fails a build."""
    data, problem = _read_config(path, PERCENTAGE_RIDERS_PATH)
    return percentage_riders_config(data) if problem is None else {**percentage_riders_config(None), "problem": problem}


def percentage_entries_for(record: dict, component: dict, entries: Iterable[dict]) -> list[dict]:
    """Reviewed percentage_riders entries of the record's utility whose match criteria fully match the component."""
    found = []
    for entry in entries:
        match = entry.get("match") or {}
        if (entry.get("utility") == record.get("utility_name")
                and _fullmatch(match.get("component_name_regex"), component.get("component_name"))
                and ("tariff_code_regex" not in match or _fullmatch(match["tariff_code_regex"], record.get("tariff_code")))):
            found.append(entry)
    return found


def _program_problem(program: Any) -> Optional[str]:
    if not isinstance(program, dict) or not program.get("id") or not program.get("province") or not program.get("name"):
        return "id, province and name are required"
    treatment = program.get("treatment")
    if treatment not in SUBSIDY_TREATMENTS:
        return f"treatment must be one of {', '.join(SUBSIDY_TREATMENTS)}"
    if not _regex_ok(program.get("component_name_regex")):
        return "component_name_regex is required"
    if not isinstance(program.get("sectors"), list) or not program["sectors"]:
        return "sectors are required"
    if treatment == "disclose":
        if not program.get("reason"):
            return "a disclosed program needs a reason"
    else:
        automatic = program.get("automatic")
        if not program.get("utility"):
            return "utility is required"
        if not isinstance(automatic, dict) or not automatic.get("quote") or not automatic.get("source_url"):
            # Owner decision 67 (2026-11-24): a subsidy counts as automatic only where an official source says so.
            return "an applied subsidy needs the official text saying it is automatic (automatic.quote and source_url)"
    if treatment == "first_block_price":
        # Owner decisions 76 and 78 (2026-11-24): the first-block price is all-in for the first-block kWh.
        if not isinstance(program.get("replaces"), dict) or program["replaces"].get("all_energy") is not True:
            return "replaces must state all_energy true (the first-block price replaces the whole per-kWh price)"
        if not isinstance(program.get("seasons"), str) or not program["seasons"]:
            return "seasons (a usage_levels.json seasons entry) is required"
    if treatment == "reference_rates":
        # Owner decision 78: reference rates replace the zone's whole tariff, charges and riders.
        if not isinstance(program.get("replaces"), dict) or program["replaces"].get("all_charges") is not True:
            return "replaces must state all_charges true (reference rates replace the whole tariff)"
        required = program.get("required_components")
        if not isinstance(required, list) or not required or not all(_regex_ok(regex) for regex in required):
            return "required_components (component-name regexes) are required"
    if treatment == "per_kwh_credit" and not isinstance(program.get("within_first_block"), bool):
        return "within_first_block (true or false) is required"
    absent = program.get("absent", [])
    if not isinstance(absent, list) or not all(isinstance(row, dict) and row.get("reason") and _selector_ok(row, "reason")
                                               for row in absent):
        return "absent entries need a tariff_code_regex or name_regex and a reason"
    if "applies_to" in program and not (isinstance(program["applies_to"], dict)
                                        and _selector_ok(program["applies_to"], "text")):
        return "applies_to needs a tariff_code_regex or name_regex"
    if not (program.get("quote") and program.get("source_url") and program.get("decided")):
        return "quote, source_url and decided are required"
    if not program.get("reviewed"):
        return "not reviewed"
    return None


def _selector_ok(selector: dict, *extra: str) -> bool:
    """A record selector names tariff_code_regex and/or name_regex (valid regexes) and nothing else but ``extra``."""
    keys = set(selector) - set(extra)
    return bool(keys) and keys <= {"tariff_code_regex", "name_regex"} and all(_regex_ok(selector[k]) for k in keys)


def _record_selected(record: dict, selector: Any) -> bool:
    """True when every regex of a record selector ({tariff_code_regex, name_regex}) fully matches the record."""
    if not isinstance(selector, dict) or not ({"tariff_code_regex", "name_regex"} & set(selector)):
        return False
    return (("tariff_code_regex" not in selector or _fullmatch(selector["tariff_code_regex"], record.get("tariff_code")))
            and ("name_regex" not in selector or _fullmatch(selector["name_regex"], record.get("name"))))


def subsidies_config(data: Any) -> dict:
    """Usable programs and the jurisdiction policy of a subsidies document (or of an already loaded configuration,
    whose skipped programs are kept); unreviewed or malformed programs are skipped with a reason, so they are never
    applied, and subsidy_policy then publishes no after-subsidy cost for their territory and sector."""
    doc = data if isinstance(data, dict) else {}
    programs = []
    skipped = [row for row in doc.get("skipped") or [] if isinstance(row, dict)]
    for program in doc.get("programs") or []:
        problem = _program_problem(program)
        if problem:
            row = program if isinstance(program, dict) else {}
            skipped.append({"id": row.get("id"), "province": row.get("province"), "sectors": row.get("sectors"),
                            "reason": problem})
        else:
            programs.append(program)
    jurisdictions = doc.get("jurisdictions") if isinstance(doc.get("jurisdictions"), dict) else {}
    return {"version": doc.get("version"), "status": doc.get("status"), "rule": doc.get("rule"),
            "tax_note": doc.get("tax_note"), "problem": doc.get("problem"), "jurisdictions": jurisdictions,
            "programs": programs, "skipped": skipped}


def load_subsidies(path: PathLike = None) -> dict:
    """Reviewed territorial subsidies (default data/models/subsidies.json, owner decisions 67-70, 74 and 76-78). A
    missing or unreadable file publishes no after-subsidy figure and states the problem; it never fails a build."""
    data, problem = _read_config(path, SUBSIDIES_PATH)
    return subsidies_config(data) if problem is None else {**subsidies_config(None), "problem": problem}


def _sector_group(sector: Any) -> str:
    return "residential" if sector == "residential" else "commercial"


def subsidy_policy(config: Optional[dict], province: Any, fuel: Any, sector: Any) -> Optional[dict]:
    """{'after_subsidy': bool, 'reason': text or None} for a territorial electricity model, else None (provinces carry
    no subsidy figures). Without a usable configuration or jurisdiction entry, or while a program that could apply to
    the territory and sector is not usable (skipped), no after-subsidy cost is published."""
    if province not in TERRITORIES or fuel != "electricity":
        return None
    if config is None:
        return {"after_subsidy": False, "reason": "no subsidies configuration was supplied"}
    if config.get("problem"):
        return {"after_subsidy": False, "reason": f"data/models/subsidies.json: {config['problem']}"}
    entry = ((config.get("jurisdictions") or {}).get(province) or {}).get(_sector_group(sector))
    if not isinstance(entry, dict) or not isinstance(entry.get("after_subsidy"), bool):
        return {"after_subsidy": False,
                "reason": f"no reviewed subsidies.json entry for {province} {_sector_group(sector)} models"}
    if not entry["after_subsidy"]:
        return {"after_subsidy": False, "reason": entry.get("reason") or "no after-subsidy cost is published",
                "decided": entry.get("decided")}
    group = _sector_group(sector)
    # Fail closed: a program that could apply here but is not usable would otherwise silently drop out of the figure.
    broken = [row for row in config.get("skipped") or [] if row.get("province") in (province, None)
              and (not isinstance(row.get("sectors"), list) or group in row["sectors"])]
    if broken:
        return {"after_subsidy": False, "decided": entry.get("decided"),
                "reason": "data/models/subsidies.json: " + "; ".join(
                    f"program {row.get('id')} is not usable ({row.get('reason')})" for row in broken)
                          + "; no after-subsidy cost is published until it is reviewed"}
    return {"after_subsidy": True, "reason": None, "decided": entry.get("decided")}


def subsidy_programs(config: Optional[dict], province: Any, sector: Any,
                     utilities: Optional[Iterable[str]] = None) -> list[dict]:
    """The configuration's usable programs for a province, sector group and (when given) set of utilities."""
    names = None if utilities is None else set(utilities)
    return [program for program in (config or {}).get("programs") or []
            if program.get("province") == province and _sector_group(sector) in (program.get("sectors") or [])
            and (names is None or program.get("utility") is None or program["utility"] in names)]


def interim_entry(record: dict, entries: Iterable[dict]) -> Optional[dict]:
    """The crosswalk interim_rates entry that labels a record interim (owner decision 72, 2026-11-24): same utility and
    the record's own notes still say so (notes_search, case-insensitive), so final rates drop the label."""
    for entry in entries:
        pattern = entry.get("notes_search") if isinstance(entry, dict) else None
        if not isinstance(pattern, str) or entry.get("utility") != record.get("utility_name"):
            continue
        try:
            if re.search(pattern, record.get("notes") or "", re.IGNORECASE):
                return entry
        except re.error:
            continue
    return None


def shared_rate_book_units(crosswalk: Optional[dict]) -> dict[str, str]:
    """Utility name -> the utility a crosswalk shared_rate_books entry counts it as (owner decision 66: the joint Yukon
    rate book is one contributor)."""
    units = {}
    for book in (crosswalk or {}).get("shared_rate_books") or []:
        if isinstance(book, dict) and book.get("counted_as") and isinstance(book.get("utilities"), list):
            for name in book["utilities"]:
                units[name] = book["counted_as"]
    return units


def _energy_tier_scale(unit: Any, record: dict, ctx: dict, components: list[dict]
                       ) -> tuple[Optional[str], float, list[str], Optional[str], Optional[str]]:
    """(scale 'month'|'kw'|'kva', factor to the scale, conversions, problem, block_periods entry id) of an energy block
    threshold unit; a bare 'kWh' threshold needs a reviewed data/models/block_periods.json entry."""
    text = re.sub(r"\s+", " ", (unit or "").strip().lower())
    dpm = ctx["days_per_month"]
    volume = ctx.get("volume_unit", "kwh")
    if volume != "kwh":
        # Gas blocks: monthly volume thresholds in the model's own unit, or daily ones x days per month (Energir D1,
        # owner decision 8, 2026-11-20); annual thresholds are not blocks.
        if text in GAS_BLOCK_UNITS.get(volume, ()):
            return "month", 1.0, [], None, None
        if text in GAS_DAILY_BLOCK_UNITS.get(volume, ()):
            return "month", dpm, [f"block threshold {VOLUME_LABELS[volume]}/day x {dpm:g}"], None, None
        return None, 1.0, [], (f"tier threshold unit {unit!r} not supported for {VOLUME_LABELS.get(volume, volume)} "
                               "gas blocks"), None
    if text in _TIER_UNITS:
        return "month", 1.0, [], None, None
    if text in ("kwh/day", "kwh per day"):
        return "month", dpm, [f"block threshold kWh/day x {dpm:g}"], None, None
    if re.fullmatch(r"kwh ?(?:/|per) ?(?:kw|kilowatt)(?: of (?:billing|maximum) demand)?(?:/month| per month)?", text):
        return "kw", 1.0, ["block threshold per kW x the level's kW"], None, None
    if re.fullmatch(r"kwh ?(?:/|per) ?kva(?: of (?:billing|maximum) demand)?(?:/month| per month)?", text):
        return "kva", 1.0, [f"block threshold per kVA x the level's kVA (kW / {ctx['power_factor']:g})"], None, None
    if text != "kwh":
        return None, 1.0, [], f"tier threshold unit {unit!r} not supported", None
    entry = block_period_entry(record, components, ctx.get("block_periods") or [])
    if entry is None:
        return None, 1.0, [], (f"tier threshold unit {unit!r} has no stated period (no reviewed "
                               "data/models/block_periods.json entry)"), None
    period, entry_id = entry.get("threshold_period"), entry.get("id")
    factors = {"month": (1.0, f"block threshold kWh per month ({entry_id})"),
               "two_months": (0.5, f"block threshold kWh per two months / 2 ({entry_id})"),
               "day": (dpm, f"block threshold kWh per day x {dpm:g} ({entry_id})")}
    if period not in factors:
        state = "no period stated" if period is None else f"unsupported threshold_period {period!r}"
        return None, 1.0, [], (f"tier threshold unit {unit!r} has no stated period (data/models/block_periods.json "
                               f"entry {entry_id}: {state})"), None
    factor, conversion = factors[period]
    return "month", factor, [conversion], None, entry_id


def _demand_tier_factor(unit: Any, power_factor: float) -> Optional[float]:
    """kW per threshold unit for demand blocks (kVA bounds at the power factor); None when unsupported."""
    text = re.sub(r"\s+", " ", (unit or "").strip().lower())
    match = re.fullmatch(r"(kw|kva)(?: of (?:billing|maximum|peak metered) demand)?", text)
    if not match:
        return None
    return power_factor if match.group(1) == "kva" else 1.0


def _block_windows(rows: list[tuple[dict, dict]], factor: float) -> tuple[Optional[dict], Optional[str]]:
    """Windows per tier number: two-block schedules share one boundary (an item may cover one block only);
    longer schedules need one item per tier 1..n with increasing cumulative bounds."""
    numbers = [comp.get("tier_number") for _, comp in rows]
    if set(numbers) <= {1, 2}:
        bounds = {float(comp["tier_threshold"]) for _, comp in rows if comp.get("tier_threshold") is not None}
        if len(bounds) != 1:
            return None, "tier thresholds missing or inconsistent"
        boundary = bounds.pop() * factor
        return {1: (0.0, boundary), 2: (boundary, math.inf)}, None
    if numbers != list(range(1, len(rows) + 1)):
        return None, f"tier numbers {numbers} are not 1..n"
    windows, lower = {}, 0.0
    for index, (_, comp) in enumerate(rows):
        threshold = comp.get("tier_threshold")
        if index == len(rows) - 1:
            if threshold is not None and float(threshold) * factor != lower:
                return None, f"last tier threshold {threshold} differs from the previous upper bound {lower:g}"
            upper = math.inf
        elif threshold is None or float(threshold) * factor < lower:
            return None, "tier thresholds missing or decreasing"
        else:
            upper = float(threshold) * factor
        windows[comp.get("tier_number")] = (lower, upper)
        lower = upper
    return windows, None


def _tier_windows(group: list[tuple[dict, dict]], ctx: dict, record: dict) -> list[str]:
    """Set tier_lower/tier_upper (kWh/month, or kWh per kW/kVA) on one season's energy block items."""
    rows = sorted(group, key=lambda pair: pair[1].get("tier_number") or 0)
    names = ", ".join(item["component"] for item, _ in rows)
    units = {comp.get("tier_unit") for _, comp in rows if comp.get("tier_threshold") is not None}
    if len(units) > 1:
        return [f"tier threshold units differ {sorted(map(str, units))}: {names}"]
    scale, factor, conversions, problem, entry_id = _energy_tier_scale(
        next(iter(units), "kWh/month" if ctx.get("volume_unit", "kwh") == "kwh"
             else GAS_BLOCK_UNITS.get(ctx["volume_unit"], ("",))[0]),
        record, ctx, [comp for _, comp in rows if comp.get("tier_threshold") is not None])
    if problem:
        return [f"{problem}: {names}"]
    if scale in ("kw", "kva") and any(_CAP_RE.search((comp.get("component_name") or "") + " " + _note_body(comp))
                                      for _, comp in rows):
        return [f"block threshold with a published cap that is not structured: {names}"]
    windows, problem = _block_windows(rows, factor)
    if problem:
        return [f"{problem}: {names}"]
    for item, comp in rows:
        item["tier_lower"], item["tier_upper"] = windows[comp.get("tier_number")]
        item["tier_scale"] = scale
        item["conversions"] = list(dict.fromkeys(list(item.get("conversions") or []) + conversions))
        if entry_id:
            item["block_period"] = entry_id
    return []


def _demand_windows(group: list[tuple[dict, dict]], ctx: dict) -> list[str]:
    """Set demand_lower/demand_upper (kW) on one season's demand block items."""
    rows = sorted(group, key=lambda pair: pair[1].get("tier_number") or 0)
    names = ", ".join(item["component"] for item, _ in rows)
    units = {comp.get("tier_unit") for _, comp in rows if comp.get("tier_threshold") is not None}
    if not units:
        return [f"demand block thresholds missing: {names}"]
    factors = {_demand_tier_factor(unit, ctx["power_factor"]) for unit in units}
    if len(factors) != 1 or None in factors:
        return [f"demand block threshold unit {sorted(map(str, units))} not supported: {names}"]
    windows, problem = _block_windows(rows, factors.pop())
    if problem:
        return [f"demand {problem}: {names}"]
    for item, comp in rows:
        item["demand_lower"], item["demand_upper"] = windows[comp.get("tier_number")]
    return []


def _period_and_tier_checks(priced: list[tuple[dict, dict]], ctx: dict, record: Optional[dict] = None) -> list[str]:
    """Attach TOU shares, block windows and demand thresholds to priced items; blockers for anything not computable."""
    blockers: list[str] = []
    shares = ctx.get("shares")
    energy_periods: set[str] = set()
    tier_groups: dict[tuple, list[tuple[dict, dict]]] = defaultdict(list)
    demand_groups: dict[tuple, list[tuple[dict, dict]]] = defaultdict(list)
    seasons: dict[str, list[int]] = {}
    for item, comp in priced:
        period, tier = comp.get("tou_period"), comp.get("tier_number")
        if item["basis"] == "kw":
            threshold = comp.get("demand_threshold_kw")
            if period:
                blockers.append(f"time-period demand charge not computable: {item['component']}")
            elif tier is not None and threshold is not None:
                blockers.append(f"demand block and demand threshold both set: {item['component']}")
            elif tier is not None:
                demand_groups[(item["type"], item.get("season"))].append((item, comp))
            elif threshold is not None:
                if "kva" in (item.get("unit") or "").lower():
                    blockers.append(f"kW demand threshold on a kVA charge not computable: {item['component']}")
                else:
                    item["demand_lower"], item["demand_upper"] = float(threshold), math.inf
            continue
        if item["basis"] != "kwh":
            continue
        if period:
            share = (shares or {}).get(period)
            if share is None and float(item["value"]) == 0.0:
                item["share"] = 0.0
            elif share is None:
                source = ctx.get("shares_id") or "no matching share set"
                blockers.append(f"no official kWh share for TOU period '{period}' ({source}): {item['component']}")
            else:
                item["share"] = float(share)
            if item["type"] in ENERGY_TYPES:
                energy_periods.add(period)
        if tier is not None:
            if period:
                blockers.append(f"tiered time-of-use price not computable: {item['component']}")
            else:
                tier_groups[(item["type"], item.get("season"))].append((item, comp))
        if item["type"] in ENERGY_TYPES and item.get("months"):
            seasons.setdefault(str(item.get("season")), item["months"])
    if energy_periods and shares and energy_periods != set(shares):
        blockers.append(f"TOU periods {sorted(energy_periods)} do not match the official share set {sorted(shares)}")
    if seasons and sorted(m for months in seasons.values() for m in months) != list(range(1, 13)):
        blockers.append("seasonal energy prices do not cover each month exactly once: "
                        + json.dumps(seasons, sort_keys=True))
    # An unseasoned first block followed by seasonal blocks (Liberty Gas NB LGS: block 1 all year, block 2 Sep-Apr and
    # May-Aug) applies in every season, so each season's blocks are bounded together with it.
    for ctype in sorted({key[0] for key in tier_groups}, key=str):
        plain = tier_groups.get((ctype, None))
        seasonal = [key for key in tier_groups if key[0] == ctype and key[1] is not None]
        numbers = {comp.get("tier_number") for _, comp in plain or []}
        if plain and seasonal and not any(numbers & {comp.get("tier_number") for _, comp in tier_groups[key]}
                                          for key in seasonal):
            for key in seasonal:
                tier_groups[key] = plain + tier_groups[key]
            del tier_groups[(ctype, None)]
    shared: dict[int, set] = defaultdict(set)
    for key, group in tier_groups.items():
        blockers.extend(_tier_windows(group, ctx, record or {}))
        for item, comp in group:
            if key[1] is not None and comp.get("season") is None and "tier_lower" in item:
                shared[id(item)].add((item["tier_lower"], item["tier_upper"]))
    if any(len(windows) > 1 for windows in shared.values()):
        blockers.append("an unseasoned block has different bounds in different seasons")
    for group in demand_groups.values():
        blockers.extend(_demand_windows(group, ctx))
    return blockers


_VARIANT_NAME = re.compile(r"^(.*\S)\s*\(([^()]*)\)\s*$")
_VARIANTS_BLOCKER = "fixed charge published as variants without a selection rule: "
_CAP_RE = re.compile(r"\bup to a maximum of\b|\bcapped at\b|\bmaximum of [\d,.]+\s*(?:kilowatt-hours|kwh)", re.IGNORECASE)


def _stem(name: str) -> str:
    match = _VARIANT_NAME.match(name or "")
    return (match.group(1) if match else name or "").strip().lower()


def _fixed_variant_groups(rows: list[tuple[dict, dict]]) -> dict[str, list[tuple[dict, dict]]]:
    """Fixed-charge items named as variants of one charge ('Stem (qualifier)'), by stem; groups of two or more."""
    groups: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    for item, comp in rows:
        match = _VARIANT_NAME.match(item["component"]) if item["type"] == "fixed" else None
        if match:
            groups[match.group(1).lower()].append((item, comp))
    return {stem: members for stem, members in groups.items() if len(members) > 1}


def _unmarked_fixed_variants(priced: list[tuple[dict, dict]]) -> list[str]:
    """Unconditional fixed charges printed as variants of one charge, e.g. 'Basic Charge (single phase)' and
    'Basic Charge (three phase)': never added together; a fixed_charge_variants rule may select one per level."""
    return [_VARIANTS_BLOCKER + "; ".join(item["component"] for item, _ in members)
            for members in _fixed_variant_groups(priced).values()]


_BANDS_BLOCKER = "fixed charge published as annual-volume bands without a selection rule: "


def _annual_band_groups(priced: list[tuple[dict, dict]], ctx: dict) -> dict[Any, list[tuple[dict, dict]]]:
    """Fixed charges published as bands of annual volume (tier numbers with a per-year gas threshold, e.g. Energir D1's
    basic fee per metering device: "One band applies, selected by annual volume withdrawn"), by component type; groups
    of two or more, sorted by tier. Only one band applies, so a group is never summed: a fixed_charge_variants rule
    with select 'annual_volume_band' picks the band containing 12 x the level's volume."""
    units = GAS_ANNUAL_UNITS.get(ctx.get("volume_unit", "kwh"), ())
    groups: dict[Any, list[tuple[dict, dict]]] = defaultdict(list)
    for item, comp in priced:
        if item["basis"] == "month" and comp.get("tier_number") is not None:
            groups[item["type"]].append((item, comp))

    def annual(comp: dict) -> bool:
        return re.sub(r"\s+", " ", (comp.get("tier_unit") or "").strip().lower()) in units

    # The open-ended last band has no threshold (and so no unit); every bounded band must be in an annual unit.
    return {key: sorted(rows, key=lambda row: row[1].get("tier_number") or 0) for key, rows in groups.items()
            if len(rows) > 1 and any(annual(comp) for _, comp in rows)
            and all(annual(comp) or comp.get("tier_threshold") is None for _, comp in rows)}


def _is_percentage(component: dict) -> bool:
    """True for a component priced as a percentage or fraction (price_basis 'percent')."""
    unit = re.sub(r"\s+", " ", (component.get("charge_unit") or "").strip().lower())
    return unit.startswith("%") or unit.startswith("fraction")


def _prepare(record: dict, ctx: dict) -> dict:
    """Classify a record's components once (level-independent): items, priced items, blockers, energy status."""
    items: list[dict] = []
    priced: list[tuple[dict, dict]] = []
    blockers: list[str] = []
    alternatives: dict[tuple, list[str]] = defaultdict(list)
    alternative_rows: dict[tuple, list[tuple[dict, dict]]] = defaultdict(list)
    priced_slots: set[tuple] = set()
    covered_stems: set[tuple] = set()
    market: list[str] = []
    market_other: list[str] = []
    energy_seen = market_energy = False
    for comp in record.get("components") or []:
        name = comp.get("component_name") or ""
        ctype = comp.get("component_type")
        energy_seen = energy_seen or ctype in ENERGY_TYPES
        item = {"component": name, "type": ctype, "sub_component": comp.get("sub_component"),
                "value": comp.get("charge_value"), "unit": comp.get("charge_unit")}
        for field in ("tou_period", "season", "tier_number", "effective_date", "end_date"):
            if comp.get(field) is not None:
                item[field] = comp.get(field)
        if comp.get("pair_part"):
            item["pair_part"] = comp["pair_part"]
        # Percentage components: the reviewed entry (owner decision 64, 2026-11-24) is looked up whatever the dates, so an
        # expired or future percentage subsidy is still named in the after-subsidy disclosure.
        pct_entries = percentage_entries_for(record, comp, ctx.get("percent_entries") or []) \
            if _is_percentage(comp) else []
        pct_entry = pct_entries[0] if len(pct_entries) == 1 else None
        if pct_entry is not None:
            item["percentage_entry"] = pct_entry["id"]
            if pct_entry.get("treatment") == "subsidy":
                item["limit_kwh"], item["limit_unit"] = comp.get("tier_threshold"), comp.get("tier_unit")
        reason = component_exclusion(comp, ctx["as_of"])
        reference = reference_customer_match(comp, ctx["reference"], reason) \
            if reason in ("conditional", "optional") else None
        if reference:
            reason = None
        basis = None
        if reason is None:
            basis = price_basis(comp, ctx["days_per_month"], ctx["power_factor"], ctx.get("volume_unit", "kwh"))
            if basis is None:
                reason = "unsupported_unit"
            elif basis[0] == "percent":
                if pct_entry is not None:
                    reason = {"apply": None, "exclude": "percentage_excluded", "subsidy": "subsidy"}[pct_entry["treatment"]]
                elif len(pct_entries) > 1 or ctx.get("percent_review"):
                    reason = "percentage_unreviewed"
                    blockers.append(f"{EXCLUSION_TEXT[reason]} (owner decision 64): {name} ({item['value']} "
                                    f"{item['unit']})" + (" matches more than one entry" if pct_entries else ""))
                else:
                    reason = "percentage_base_not_computable"
        if reason in ("unsupported_unit", "no_value"):
            blockers.append(f"{EXCLUSION_TEXT[reason]}: {name} ({item['unit']})")
        elif reason == "market_pending":
            market.append(name)
            market_energy = True
        elif reason == "market_indexed_non_energy":
            market_other.append(f"{name} ({comp.get('market_reference')})")
        elif reason == "alternative":
            alternatives[(ctype, comp.get("sub_component"))].append(name)
            alternative_rows[(ctype, comp.get("sub_component"))].append((item, comp))
        elif reason in ("conditional", "optional"):
            covered_stems.add((ctype, _stem(name)))
        if reason:
            item.update(status="excluded", reason=reason)
            items.append(item)
            continue
        months, problem = season_months(comp, ctx["province"], ctx["usage_levels"])
        if problem:
            blockers.append(f"{problem}: {name}")
        assert basis is not None
        kind, factor, conversions = basis
        item.update(status="included", basis=kind, factor=factor, bucket=bucket_of(ctype, kind), months=months,
                    conversions=conversions)
        if kind == "percent" and pct_entry is not None:
            item["reason"] = PERCENT_PREFIX + pct_entry["id"]
            item["percent_base"] = pct_entry["base"]["component_name_regex"]
        if reference:
            item["reason"] = REFERENCE_PREFIX + reference
            entry = next((e for e in ctx["reference"] if e.get("id") == reference), {})
            if isinstance(entry.get("annual_volume"), dict):
                item["annual_limit"] = {**entry["annual_volume"], "entry": reference}
        items.append(item)
        priced.append((item, comp))
        priced_slots.add((ctype, comp.get("sub_component")))
        covered_stems.add((ctype, _stem(name)))
    for item, _ in priced:
        # A reviewed rider whose base names no priced charge would be priced at zero: fail closed instead.
        if item["basis"] == "percent" and not any(
                other["basis"] != "percent" and _fullmatch(item["percent_base"], other["component"]) for other, _ in priced):
            blockers.append(f"percentage rider {item['component']}: its reviewed base "
                            f"({item['reason'][len(PERCENT_PREFIX):]}) names no priced charge")
    variant_slots: dict[str, list[tuple[int, list[tuple[dict, dict]]]]] = defaultdict(list)
    for slot, names in sorted(alternatives.items(), key=str):
        if slot not in priced_slots and not all(
                (slot[0], _stem(name)) in covered_stems for name in names):
            stems = {_stem(name) for name in names}
            # One stem with at least one qualifier: 'Charge' and 'Charge (higher consumption)' (Liberty Gas NB) are
            # variants of one charge as much as 'Charge (single phase)' and 'Charge (three phase)'.
            if slot[0] == "fixed" and len(stems) == 1 and any(_VARIANT_NAME.match(name) for name in names):
                variant_slots[stems.pop()].append((len(blockers), alternative_rows[slot]))
            blockers.append("charge published only as conditional alternatives: " + "; ".join(names))
    # Each group keeps the indexes of its blockers: a fixed_charge_variants rule may resolve them per usage level.
    variant_groups = [{"members": [row for _, rows in slots for row in rows], "blockers": [i for i, _ in slots]}
                      for slots in variant_slots.values() if sum(len(rows) for _, rows in slots) > 1]
    for members in _fixed_variant_groups(priced).values():
        variant_groups.append({"members": members, "blockers": [len(blockers)]})
        blockers.append(_VARIANTS_BLOCKER + "; ".join(item["component"] for item, _ in members))
    for members in _annual_band_groups(priced, ctx).values():
        windows, problem = _block_windows(members, 1.0)
        names = "; ".join(item["component"] for item, _ in members)
        if problem:
            blockers.append(f"annual-volume bands: {problem}: {names}")
            continue
        variant_groups.append({"members": members, "blockers": [len(blockers)], "kind": "annual_volume_band",
                               "windows": {id(item): windows[comp.get("tier_number")] for item, comp in members}})
        blockers.append(_BANDS_BLOCKER + names)
    grouped = {id(item) for group in variant_groups for item, _ in group["members"]}
    priced = [pair for pair in priced if id(pair[0]) not in grouped]
    if (record.get("pair") or {}).get("blocker"):
        blockers.append(record["pair"]["blocker"])
    blockers.extend(_period_and_tier_checks(priced, ctx, record))
    if market_energy:
        energy_status = "market_pending"
    elif any(item["type"] in ENERGY_TYPES for item, _ in priced):
        energy_status = "included"
    elif energy_seen:
        energy_status = "excluded"
        blockers.append("energy components exist but none is unconditional and in effect")
    else:
        energy_status = "absent"
    ended = _as_date(record.get("end_date"))
    if ended is not None and ended < _as_of(ctx["as_of"]):
        # A record past its own end date is not in effect, as in the coverage gate (owner decision 2026-11-19): its
        # remaining charges are never priced without the expired ones (Medicine Hat's month-dated default energy).
        blockers.append(f"record ended on {ended.isoformat()}; no newer record is stored")
    return {"items": items, "priced": priced, "blockers": blockers, "energy_status": energy_status,
            "market_pending": market, "market_other": market_other, "power_factor": ctx["power_factor"],
            "variant_groups": variant_groups, "volume_unit": ctx.get("volume_unit", "kwh"),
            "utility": record.get("utility_name"), "tariff_code": record.get("tariff_code")}


def _variant_rule_applies(rule: dict, prep: dict, level_id: Any, peak: Optional[float]) -> bool:
    """Whether a fixed_charge_variants rule applies to a prepared record at one level: its utility and tariff code
    (when given) and its kind's test (level id, the level's monthly peak within peak_month, or any level for bands)."""
    if rule.get("utility") not in (None, prep.get("utility")):
        return False
    if "tariff_code" in rule["match"] and rule["match"]["tariff_code"] != prep.get("tariff_code"):
        return False
    kind = _variant_rule_kind(rule)
    if kind == "levels":
        return level_id in rule["levels"]
    if kind == "peak_month":
        return peak is not None and _within(peak, rule["peak_month"])
    return kind == "annual_volume_band"


def _select_variants(prep: dict, ctx: dict, level_id: Any,
                     quantity: Optional[float] = None) -> tuple[list[dict], set[int]]:
    """(chosen variants, indexes of the blockers they resolve) at one usage level.

    A variant group is priced with its one member whose name fully matches a fixed_charge_variants rule that applies
    at the level and that has a value in a per-month unit; an annual-volume band group with the one band whose window
    strictly contains 12 x ``quantity`` (a level on a band boundary is ambiguous and stays not computable). No match,
    several matches or an unpriceable member keep the group's blockers."""
    peak = None
    if quantity is not None and ctx.get("peak_factor"):
        peak = float(quantity) * float(ctx["peak_factor"]["factor"])
    rules = [rule for rule in ctx.get("variant_rules") or [] if _variant_rule_applies(rule, prep, level_id, peak)]
    choices: list[dict] = []
    resolved: set[int] = set()
    for group in prep.get("variant_groups") or [] if rules else []:
        hits = []
        if group.get("kind") == "annual_volume_band":
            rule = next((r for r in rules if _variant_rule_kind(r) == "annual_volume_band" and all(
                _fullmatch(r["match"]["name_regex"], item["component"]) for item, _ in group["members"])), None)
            if rule is not None and quantity is not None:
                annual = float(quantity) * 12
                hits = [(item, comp, rule) for item, comp in group["members"]
                        if group["windows"][id(item)][0] < annual < group["windows"][id(item)][1]]
        else:
            for item, comp in group["members"]:
                rule = next((r for r in rules if _variant_rule_kind(r) != "annual_volume_band"
                             and _fullmatch(r["match"]["name_regex"], item["component"])), None)
                if rule is not None:
                    hits.append((item, comp, rule))
        if len(hits) != 1 or hits[0][1].get("charge_value") is None:
            continue
        item, comp, rule = hits[0]
        basis = price_basis(comp, ctx["days_per_month"], ctx["power_factor"])
        months, problem = season_months(comp, ctx["province"], ctx["usage_levels"])
        if basis is None or basis[0] != "month" or problem:
            continue
        kind, factor, conversions = basis
        chosen = {**item, "status": "included", "basis": kind, "factor": factor, "bucket": bucket_of(item["type"], kind),
                  "months": months, "conversions": conversions, "reason": VARIANT_PREFIX + rule["id"]}
        choices.append({"item": chosen, "source": item, "rule": rule["id"],
                        "members": [id(member) for member, _ in group["members"]]})
        resolved.update(group["blockers"])
    return choices, resolved


def _price(prep: dict, kwh: float, kw: Optional[float],
           selection: Optional[tuple[list[dict], set[int]]] = None) -> dict:
    """Monthly cost of a prepared record at one usage level; amounts align with prep['priced'] and the fixed-charge
    variants chosen by ``selection`` (from _select_variants) are priced in 'variants'. For gas ``kwh`` is the level's
    monthly volume in the model's unit."""
    choices, resolved = selection or ([], set())
    reasons = [blocker for index, blocker in enumerate(prep["blockers"]) if index not in resolved]
    if kw is None and any(item["basis"] == "kw" for item, _ in prep["priced"]):
        reasons.append("demand charges present but the usage level has no kW")
    if kw is None:
        reasons.extend(f"tier threshold unit per {item['tier_scale']} not supported at a level without kW: "
                       f"{item['component']}" for item, _ in prep["priced"] if item.get("tier_scale") in ("kw", "kva"))
    for item, _ in prep["priced"]:
        limit = item.get("annual_limit")
        if limit and not _within(float(kwh) * 12, limit):
            # e.g. Energir load balancing: below 75,000 m3 a year only; above it a load-factor formula price applies.
            reasons.append(f"{item['component']} is priced for the reference customer only at "
                           f"{_bounds_text(limit, limit.get('unit', ''))} a year ({limit.get('entry')}); "
                           f"{limit.get('otherwise') or 'another price applies'}")
    if reasons:
        return {"status": "not_computable", "cost": None, "energy_charge_subtotal": None, "reasons": reasons,
                "amounts": [], "variants": []}
    amounts: list[float] = []
    for item, _ in prep["priced"]:
        if item["basis"] == "percent":
            amounts.append(0.0)  # priced below, from the charges of its base at this level
            continue
        if item["basis"] == "month":
            quantity = 1.0
        elif item["basis"] == "kw":
            quantity = float(kw or 0.0)
            if "demand_lower" in item:
                quantity = max(0.0, min(quantity, item["demand_upper"]) - item["demand_lower"])
        else:
            quantity = float(kwh)
            if "tier_lower" in item:
                scale = {"kw": float(kw or 0.0), "kva": float(kw or 0.0) / prep["power_factor"]}.get(
                    item.get("tier_scale"), 1.0)
                upper = item["tier_upper"] * scale if math.isfinite(item["tier_upper"]) else math.inf
                quantity = max(0.0, min(quantity, upper) - item["tier_lower"] * scale)
            quantity *= item.get("share", 1.0)
        weight = len(item["months"]) / 12 if item.get("months") else 1.0
        amounts.append(float(item["value"]) * item["factor"] * quantity * weight)
    variants = []
    for choice in choices:
        item = choice["item"]
        weight = len(item["months"]) / 12 if item.get("months") else 1.0
        variants.append({**choice, "amount": float(item["value"]) * item["factor"] * weight})
    # Reviewed percentage riders (owner decision 64, 2026-11-24): the percentage of the base charges their entry names,
    # priced at this level; riders never apply to each other.
    for index, (item, _) in enumerate(prep["priced"]):
        if item["basis"] == "percent":
            base = math.fsum([amount for (other, _), amount in zip(prep["priced"], amounts)
                              if other["basis"] != "percent" and _fullmatch(item["percent_base"], other["component"])]
                             + [v["amount"] for v in variants if _fullmatch(item["percent_base"], v["item"]["component"])])
            amounts[index] = float(item["value"]) / 100 * base
    # math.fsum: built-in sum() of floats differs between Python 3.11 and 3.12, flipping cents
    per_kwh = math.fsum(a for (item, _), a in zip(prep["priced"], amounts) if item["basis"] == "kwh")
    return {"status": "ok", "cost": math.fsum(amounts + [v["amount"] for v in variants]),
            "energy_charge_subtotal": per_kwh, "reasons": [], "amounts": amounts, "variants": variants}


def _clean(value: Any) -> Any:
    if isinstance(value, float):
        return None if math.isinf(value) or math.isnan(value) else value
    return value


def record_monthly_cost(record: dict, kwh: float, kw: Optional[float] = None, *, sector: Optional[str] = None,
                        structure: Optional[str] = None, usage_levels: Optional[dict] = None,
                        as_of: Union[date, str, None] = None, block_periods: Any = None,
                        level: Optional[str] = None, percentage_riders: Any = None, subsidies: Any = None) -> dict:
    """Modeled monthly cost of one record at (kWh/month, kW) with an itemized included/excluded component list.

    ``sector`` (residential or a commercial size band) also selects the usage_levels reference-customer entries;
    ``block_periods`` is a block_periods document or entry list (default: none); ``level`` (a usage level id such as
    's1') applies that level's fixed_charge_variants rules (default: none, so fixed-charge variants stay not
    computable); ``percentage_riders`` is a percentage_riders document or entry list (default: none, so a territorial
    percentage component is not computable); ``subsidies`` is a subsidies document: when its policy covers the
    record's territory and sector, the result carries 'after_subsidy' (the cost after automatic subsidies, before
    tax)."""
    if sector is None:
        sector = "residential" if record.get("customer_class") == "residential" else None
    volume = (gas_volume_unit([record]) or "none") if record.get("utility_type") == "gas" else "kwh"
    subsidy_cfg = None if subsidies is None else subsidies_config(subsidies)
    ctx = _context(record.get("province"), record.get("utility_type"), structure or record.get("rate_structure"),
                   sector, usage_levels, _as_of(as_of), block_periods_config(block_periods)["entries"], volume,
                   percentage_riders_config(percentage_riders)["entries"], subsidy_cfg)
    prep = _prepare(record, ctx)
    selection = None if level is None else _select_variants(prep, ctx, level, kwh)
    priced = _price(prep, kwh, kw, selection)
    amounts = {id(item): amount for (item, _), amount in zip(prep["priced"], priced["amounts"])}
    chosen = {id(choice["source"]): choice for choice in priced["variants"]}
    others = {member for choice in priced["variants"] for member in choice["members"]} - set(chosen)
    items = []
    for item in prep["items"]:
        choice = chosen.get(id(item))
        row = {k: _clean(v) for k, v in (choice["item"] if choice else item).items()}
        if choice:
            row["amount"] = choice["amount"]
        elif id(item) in amounts:
            row["amount"] = amounts[id(item)]
        elif id(item) in others and row.get("status") == "included":
            row.update(status="excluded", reason="variant_not_selected")
        items.append(row)
    result = {"record_id": record.get("id"), "utility": record.get("utility_name"),
              "tariff_code": record.get("tariff_code"), "kwh": kwh, "kw": kw, "status": priced["status"],
              "cost": priced["cost"], "energy_charge_subtotal": priced["energy_charge_subtotal"],
              "energy_status": prep["energy_status"], "market_pending": prep["market_pending"],
              "reasons": priced["reasons"], "shares_id": ctx["shares_id"], "items": items}
    policy = None if subsidy_cfg is None else subsidy_policy(subsidy_cfg, record.get("province"),
                                                              record.get("utility_type"), sector)
    if policy is not None:
        if not policy["after_subsidy"]:
            result["after_subsidy"] = {"status": "not_published", "reason": policy["reason"]}
        elif priced["status"] != "ok":
            result["after_subsidy"] = {"status": "not_computable", "reasons": priced["reasons"]}
        else:
            result["after_subsidy"] = _after_subsidy_record(prep, record, ctx, kwh, kw, selection, priced["cost"])
    return result


def _note_sentences(record: dict, keyword: Any) -> Optional[str]:
    """The sentences of a record's notes that mention a subsidy keyword (why no price is stored for it)."""
    if not isinstance(keyword, str) or not keyword:
        return None
    text = _PROVENANCE_PREFIX.sub("", record.get("notes") or "", count=1)
    hits = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", text) if keyword in sentence]
    return " ".join(hits) or None


def _dates_text(component: dict) -> str:
    return f"{component.get('effective_date') or 'open'} to {component.get('end_date') or 'open'}"


def _after_subsidy_record(prep: dict, record: dict, ctx: dict, kwh: float, kw: Optional[float],
                          selection: Optional[tuple], before: float) -> dict:
    """One zone record's cost after the reviewed automatic subsidies at one usage level, before tax (owner decisions
    67-70, 74 and 76-78, 2026-11-24).

    Starts from the record's cost before subsidies at the level (``before``) or, where a reference-rate program applies
    to the zone record (GREP, decision 78), from its cost at the reference rates, which replace the zone's whole tariff
    (every charge and rider: the reference is all-in). A first-block price (TPSP) is all-in too (decisions 76 and 78):
    for each season's first-block kWh it replaces the whole per-kWh price of the tariff in force (the cost at the
    block's kWh less the cost at zero kWh, so the per-kWh and percentage riders' shares of energy go with it); the
    seasons and blocks come from the reviewed usage_levels.json seasons entry and are month-weighted. A per-kWh credit
    applies to every kWh or, when its program says it is not billed within a first block (within_first_block false),
    only to the kWh above it. A percentage subsidy in force at the as-of date applies to its base charges of the first
    limit kWh, plus the named riders' share. A subsidy that the sources do not establish (no stored price, a disclosed
    program, out of its dates) is not applied and is listed in 'not_applied'; a stored value that differs from its
    reviewed convention, a missing reference rate or a combination of subsidies that no review covers makes the record
    not computable. Returns {'status', 'cost', 'seasons', 'applied', 'not_applied', 'reasons'}."""
    as_of = _as_of(ctx["as_of"])
    applied: list[str] = []
    not_applied: list[dict] = []
    reasons: list[str] = []
    first_blocks: list[tuple[dict, list[dict]]] = []
    references: list[tuple[dict, list[dict]]] = []
    credits: list[tuple[dict, dict]] = []

    def skip(subsidy_id: str, name: str, reason: str) -> None:
        row = {"id": subsidy_id, "name": name, "reason": reason}
        if row not in not_applied:
            not_applied.append(row)

    def failed() -> dict:
        return {"status": "not_computable", "cost": None, "seasons": None, "applied": [], "not_applied": not_applied,
                "reasons": reasons}

    for program in subsidy_programs(ctx.get("subsidies"), ctx["province"], ctx["sector"], [record.get("utility_name")]):
        if "applies_to" in program and not _record_selected(record, program["applies_to"]):
            continue
        comps = [comp for comp in record.get("components") or []
                 if _fullmatch(program["component_name_regex"], comp.get("component_name"))]
        if program["treatment"] == "disclose":
            if comps:
                skip(program["id"], program["name"], program["reason"])
            continue
        live = []
        for comp in comps:
            state = component_exclusion(comp, as_of)
            if state in ("expired", "not_yet_effective"):
                skip(program["id"], program["name"],
                     f"{comp.get('component_name')}: {EXCLUSION_TEXT[state]} ({_dates_text(comp)})")
            elif state is None:
                reasons.append(f"{program['name']}: {comp.get('component_name')} is already priced in the cost before "
                               "subsidies")
            else:
                live.append(comp)
        if program["treatment"] == "reference_rates":
            # Decision 78: the program applies to this zone record (applies_to), so without its reference rates in
            # force the cost after subsidies is not computable rather than priced without it.
            if not live:
                reasons.append(f"{program['name']}: no reference rate in force is stored for this zone record")
                continue
            for regex in program["required_components"]:
                hits = [comp for comp in live if _fullmatch(regex, comp.get("component_name"))]
                if len(hits) != 1 or hits[0].get("charge_value") is None:
                    reasons.append(f"{program['name']}: expected one reference rate in force with a value matching "
                                   f"{regex}; found {len(hits)}")
            unknown = [comp.get("component_name") for comp in live
                       if not any(_fullmatch(regex, comp.get("component_name")) for regex in program["required_components"])]
            if unknown:
                reasons.append(f"{program['name']}: reference rate(s) not covered by its review: {', '.join(unknown)}")
            references.append((program, live))
            continue
        if not live:
            if not comps:
                # A reviewed reason (owner decision 77 for NTPC's Snare zone) comes before the record's own notes.
                note = next((row["reason"] for row in program.get("absent") or [] if _record_selected(record, row)),
                            None) or _note_sentences(record, program.get("keyword"))
                skip(program["id"], program["name"],
                     "no price is stored for this zone record" + (f" ({note.rstrip('.')})" if note else ""))
            continue
        if program["treatment"] == "first_block_price":
            first_blocks.append((program, live))
        elif (len(live) != 1 or live[0].get("charge_value") is None
              or re.sub(r"\s+", "", (live[0].get("charge_unit") or "").lower()) != "$/kwh"):
            reasons.append(f"{program['name']}: expected one per-kWh credit with a value")
        else:
            credits.append((program, live[0]))
    entries = {entry["id"]: entry for entry in ctx.get("percent_entries") or []}
    percentage_subsidies = []
    for item in prep["items"]:
        entry = entries.get(item.get("percentage_entry"))
        if entry is None or entry.get("treatment") != "subsidy":
            continue
        name = entry.get("name") or item["component"]
        if item.get("reason") == "subsidy":
            percentage_subsidies.append((item, entry))
        elif item.get("reason") in ("expired", "not_yet_effective"):
            # Owner decision 70: a dated subsidy applies only while its stored dates include the as-of date.
            skip(entry["id"], name, f"{EXCLUSION_TEXT[item['reason']]} ({_dates_text(item)})")
        else:
            skip(entry["id"], name, EXCLUSION_TEXT.get(item.get("reason"), str(item.get("reason"))))
    if len(first_blocks) > 1:
        reasons.append("more than one first-block subsidy applies: " + ", ".join(p["id"] for p, _ in first_blocks))
    if len(references) > 1:
        reasons.append("more than one reference-rate subsidy applies: " + ", ".join(p["id"] for p, _ in references))
    if references and (credits or percentage_subsidies):
        # Reference rates replace every charge and rider; no review says how another credit combines with them.
        reasons.append(f"{references[0][0]['name']}: combining its reference rates with "
                       + ", ".join([p["id"] for p, _ in credits] + [e["id"] for _, e in percentage_subsidies])
                       + " is not reviewed")
    program = first_blocks[0][0] if len(first_blocks) == 1 else None
    seasons: list[dict] = []
    if program is not None:
        convention = (ctx["usage_levels"].get("seasons") or {}).get(program["seasons"]) or {}
        for comp in first_blocks[0][1]:
            label = comp.get("season")
            months, problem = season_months(comp, ctx["province"], ctx["usage_levels"])
            reviewed = convention.get(label) if isinstance(convention.get(label), dict) else {}
            limit = reviewed.get("first_block_kwh_per_month")
            threshold = comp.get("tier_threshold")
            where = f"{program['name']} ({comp.get('component_name')})"
            if problem or not months:
                reasons.append(f"{where}: {problem or 'no season months'}")
            elif isinstance(limit, bool) or not isinstance(limit, (int, float)):
                reasons.append(f"{where}: season {label!r} has no reviewed first block in usage_levels.json seasons "
                               f"{program['seasons']}")
            elif threshold is None or float(threshold) != float(limit):
                reasons.append(f"{where}: the stored first block ({threshold} kWh) differs from the reviewed {limit:g} "
                               f"kWh a month (usage_levels.json seasons {program['seasons']}); it needs a new review")
            elif comp.get("charge_value") is None:
                reasons.append(f"{where}: no first-block price is stored")
            else:
                seasons.append({"season": label, "months": months, "block": float(limit),
                                "price": float(comp["charge_value"])})
        if seasons and sorted(m for season in seasons for m in season["months"]) != list(range(1, 13)):
            reasons.append(f"{program['name']}: its seasons do not cover each month exactly once")
    if reasons:
        return failed()
    base_prep, base_selection, start = prep, selection, float(before)
    if references:
        reference_program, reference_comps = references[0]
        # The reference rates priced as a tariff of their own (they are stored as conditional alternatives of the zone
        # record): only these components, unconditional, with their stored values, units and dates.
        reference = {**record, "components": [{**comp, "sub_component": None, "notes": "Provenance: live_parsed."}
                                              for comp in reference_comps]}
        base_prep, base_selection = _prepare(reference, ctx), None
        at = _price(base_prep, kwh, kw, None)
        if at["status"] != "ok":
            reasons.extend(f"{reference_program['name']}: {reason}" for reason in at["reasons"])
            return failed()
        if at["cost"] > float(before):
            reasons.append(f"{reference_program['name']}: its reference rates cost more than the zone's own tariff at "
                           "this level; no review covers that")
            return failed()
        start = at["cost"]
        applied.append(reference_program["id"])
    rows, zero = [], None
    for season in seasons or [{"season": None, "months": None, "block": None, "price": None}]:
        cost, block = start, 0.0
        if season["block"] is not None:
            block = min(float(kwh), season["block"])
            # Decisions 76 and 78: the first-block price is all-in, so it replaces the whole per-kWh price of the
            # tariff in force (the reference rates where they apply) on the first-block kWh.
            at_block = _price(base_prep, block, kw, base_selection)
            zero = zero or _price(base_prep, 0.0, kw, base_selection)
            if at_block["status"] != "ok" or zero["status"] != "ok":
                reasons.extend(at_block["reasons"] + zero["reasons"])
                return failed()
            saving = at_block["cost"] - zero["cost"] - block * season["price"]
            if saving < 0:
                reasons.append(f"{program['name']}: the first-block price exceeds the per-kWh price it replaces")
                return failed()
            cost -= saving
            if block > 0:
                applied.append(program["id"])
        for credit, comp in credits:
            # A credit not billed within the first block (its price is all-in, decision 76) applies above it.
            eligible = float(kwh) - (block if not credit["within_first_block"] else 0.0)
            if eligible > 0:
                cost += float(comp["charge_value"]) * eligible
                applied.append(credit["id"])
        for item, entry in percentage_subsidies:
            limit, stored = entry.get("limit"), item.get("limit_kwh")
            unit = re.sub(r"\s+", " ", (item.get("limit_unit") or "").strip().lower())
            if limit is not None and (stored is None or float(stored) != float(limit["kwh"])
                                      or unit not in ("kwh", "kwh/month", "kwh per month")):
                reasons.append(f"{entry['id']}: the stored limit ({stored} {item.get('limit_unit')}) differs from the "
                               f"reviewed {float(limit['kwh']):g} kWh a month; the entry needs a new review")
                return failed()
            if limit is None and stored is not None:
                reasons.append(f"{entry['id']}: the record limits it to {stored} kWh but the entry states no reviewed "
                               "limit")
                return failed()
            at = _price(prep, min(float(kwh), float(limit["kwh"])) if limit else float(kwh), kw, selection)
            if at["status"] != "ok":
                reasons.extend(at["reasons"])
                return failed()
            base = math.fsum(amount for (other, _), amount in zip(prep["priced"], at["amounts"])
                             if other["basis"] != "percent"
                             and _fullmatch(entry["base"]["component_name_regex"], other["component"]))
            riders = {PERCENT_PREFIX + rider for rider in entry.get("with_riders") or []}
            share = math.fsum(float(other["value"]) for other, _ in prep["priced"]
                              if other["basis"] == "percent" and other.get("reason") in riders)
            amount = float(item["value"]) / 100 * base * (1 + share / 100)
            cost += amount
            if amount:
                applied.append(entry["id"])
        rows.append({"season": season["season"], "months": season["months"], "cost": cost})
    seasonal = rows[0]["season"] is not None
    total = math.fsum(row["cost"] * len(row["months"]) / 12 for row in rows) if seasonal else rows[0]["cost"]
    return {"status": "ok", "cost": total,
            "seasons": [{"season": row["season"], "months": row["months"], "cost_after_subsidy": round(row["cost"], 2)}
                        for row in rows] if seasonal else None,
            "applied": sorted(set(applied)), "not_applied": not_applied, "reasons": []}


def record_covers_level(record: dict, kwh: Optional[float], kw: Optional[float]) -> bool:
    """True when the record's published demand ([min, max) kW, or the inclusivity of a reviewed crosswalk
    demand_bounds entry) and kWh usage bounds include the level; a pair variant also needs its Rate of Last Resort
    annual-use bound (with retail energy below it, wires alone at or above)."""
    pair = record.get("pair") or {}
    if pair and kwh is not None:
        annual = float(kwh) * 12
        if pair.get("below_annual_kwh") is not None and not annual < float(pair["below_annual_kwh"]):
            return False
        if pair.get("from_annual_kwh") is not None and annual < float(pair["from_annual_kwh"]):
            return False
    if kw is not None:
        if record.get("demand_bounds_problem"):
            return False
        lo, hi = _kw(record.get("demand_min_kw"), 0.0), _kw(record.get("demand_max_kw"), math.inf)
        lo_in, hi_in = record.get("demand_inclusive") or (True, False)
        if not ((lo < kw or (lo_in and kw == lo)) and (kw < hi or (hi_in and kw == hi))):
            return False
    unit = (record.get("usage_unit") or "").strip().lower()
    lo, hi = record.get("usage_min"), record.get("usage_max")
    if kwh is None or (lo is None and hi is None) or not unit.startswith("kwh"):
        return True
    if re.search(r"year|yr|12 months|annual", unit):
        quantity = kwh * 12
    elif "month" in unit:
        quantity = kwh
    else:
        return True
    return (lo is None or quantity >= float(lo)) and (hi is None or quantity <= float(hi))


def _threshold_problem(eligibility: dict, kw: Optional[float], annual_kwh: Optional[float]) -> Optional[str]:
    max_kw, max_kwh = eligibility.get("max_demand_kw"), eligibility.get("max_annual_kwh")
    tests, texts = [], []
    if max_kw is not None:
        tests.append(kw is not None and kw <= float(max_kw))
        texts.append(f"demand {'n/a' if kw is None else f'{kw:g}'} kW vs max {float(max_kw):g} kW")
    if max_kwh is not None:
        tests.append(annual_kwh is not None and annual_kwh <= float(max_kwh))
        texts.append(f"annual use {'n/a' if annual_kwh is None else f'{annual_kwh:,.0f}'} kWh vs max {float(max_kwh):,.0f} kWh")
    if tests and not any(tests):
        return "threshold not met (" + "; ".join(texts) + ("; either test suffices)" if len(tests) > 1 else ")")
    return None


def tax_lines(taxes: Optional[dict], province: Any, fuel: Any, sector: Any, kwh: Optional[float], kw: Optional[float],
              as_of: Union[date, str, None] = None) -> tuple[list[dict], list[dict]]:
    """(applied, not_applied) tax/rebate lines for a level: sector, dates and thresholds (EITHER test when both).

    A line left out only by its date window is not reported as "not applied" when another line of the same name is in
    its window on the as-of date: that is the same tax or rebate at another rate period, not a separate exclusion.
    """
    as_of = _as_of(as_of)
    group = "residential" if sector == "residential" else "commercial"
    lines = ((((taxes or {}).get("jurisdictions") or {}).get(province) or {}).get(fuel) or {}).get(group) or []
    annual = None if kwh is None else float(kwh) * 12
    applied, skipped, dated_out, in_window = [], [], [], set()
    for line in sorted((l for l in lines if isinstance(l, dict)), key=lambda l: l.get("order") or 0):
        eligibility = line.get("eligibility") or {}
        start, end = _as_date(line.get("effective_date")), _as_date(line.get("end_date"))
        if (start is None or start <= as_of) and (end is None or as_of < end):
            in_window.add(line.get("name"))
        reason = None
        outside_window = False
        if line.get("kind") not in TAX_KINDS or line.get("base") not in TAX_BASES or line.get("rate") is None:
            reason = f"unsupported line (kind {line.get('kind')!r}, base {line.get('base')!r})"
        elif sector not in (eligibility.get("sectors") or []):
            reason = f"sector {sector} not eligible"
        elif start is not None and start > as_of:
            reason, outside_window = f"not in effect until {start.isoformat()}", True
        elif end is not None and as_of >= end:
            reason, outside_window = f"ended {end.isoformat()}", True
        else:
            reason = _threshold_problem(eligibility, kw, annual)
        brief = {"name": line.get("name"), "kind": line.get("kind"), "rate": line.get("rate"), "base": line.get("base"),
                 "order": line.get("order"), "source_url": line.get("source_url"), "confidence": line.get("confidence")}
        if reason is None:
            applied.append(brief)
        else:
            skipped.append({"name": line.get("name"), "kind": line.get("kind"), "rate": line.get("rate"), "reason": reason})
            dated_out.append(outside_window)
    # e.g. the Ontario Electricity Rebate: 23.5% until 2026-11-01, then 15.7% (O. Reg. 328/26).
    skipped = [item for item, dated in zip(skipped, dated_out) if not (dated and item["name"] in in_window)]
    return applied, skipped


def apply_tax_lines(subtotal: float, energy_subtotal: float, lines: list[dict]) -> tuple[float, list[float]]:
    """Cost with tax and each line's amount: rate x base, never compounding; rebates are subtracted."""
    total, amounts = subtotal, []
    for line in lines:
        base = energy_subtotal if line["base"] == "energy_charge_subtotal" else subtotal
        amount = float(line["rate"]) * base
        amounts.append(amount)
        total += -amount if line["kind"] == "rebate" else amount
    return total, amounts


def summary_stats(values: Iterable[float]) -> dict:
    """median, n, min, p25, p75, max (statistics.quantiles 'inclusive'); None values when empty."""
    vals = sorted(float(v) for v in values)
    if not vals:
        return {"median": None, "n": 0, "min": None, "p25": None, "p75": None, "max": None}
    q1, q3 = (vals[0], vals[0]) if len(vals) == 1 else statistics.quantiles(vals, n=4, method="inclusive")[0::2]
    return {"median": statistics.median(vals), "n": len(vals), "min": vals[0], "p25": q1, "p75": q3, "max": vals[-1]}


def find_outliers(costs: dict[str, float], stats: Optional[dict] = None) -> list[dict]:
    """Utilities > 30% from the median or outside 1.5 x IQR, with signed deviation % (needs n >= 3)."""
    stats = stats or summary_stats(costs.values())
    if stats["n"] < OUTLIER_MIN_N:
        return []
    median, q1, q3 = stats["median"], stats["p25"], stats["p75"]
    low, high = q1 - OUTLIER_IQR_FACTOR * (q3 - q1), q3 + OUTLIER_IQR_FACTOR * (q3 - q1)
    found = []
    for utility, cost in costs.items():
        deviation = (cost - median) / median if median else None
        rules = []
        if deviation is not None and abs(deviation) > OUTLIER_PCT:
            rules.append("more_than_30pct_from_median")
        if cost < low or cost > high:
            rules.append("outside_1.5_iqr")
        if rules:
            found.append({"utility": utility, "cost": cost,
                          "deviation_pct": None if deviation is None else round(deviation * 100, 1), "rules": rules})
    return sorted(found, key=lambda o: (-abs(o["deviation_pct"] or 0.0), o["utility"]))


def closest_to_median(costs: dict[str, float], median: Optional[float]) -> Optional[str]:
    """Utility whose cost is nearest the median; ties resolved alphabetically."""
    if not costs or median is None:
        return None
    return min(sorted(costs), key=lambda u: (round(abs(costs[u] - median), 9), u))


def _money(stats: dict) -> dict:
    return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in stats.items()}


def _rate(stats: dict) -> dict:
    return {k: (round(v, 6) if isinstance(v, float) else v) for k, v in stats.items()}


def _record_brief(record: dict, zone: str, rule_id: Optional[str]) -> dict:
    brief = {"record_id": record.get("id"), "tariff_code": record.get("tariff_code"), "name": record.get("name"),
             "zone": zone, "rule_id": rule_id, "effective_date": record.get("effective_date"),
             "source_url": record.get("source_url"), "confidence": record.get("confidence")}
    if record.get("pair"):
        brief["pair"] = {k: record["pair"].get(k) for k in ("unit", "variant", "wires_record_id", "retail_record_id")}
        brief["retail_source_url"] = record.get("retail_source_url")
    if record.get("interim"):
        brief["interim"] = True  # owner decision 72 (2026-11-24): interim rates are included and labelled
    return brief


def _period_label(item: dict) -> Optional[str]:
    parts = [item.get("tou_period")]
    if item["type"] == "energy":
        parts.append(f"tier {item['tier_number']}" if item.get("tier_number") is not None else None)
        parts.append(item.get("season") if item.get("months") else None)
    return " / ".join(str(p) for p in parts if p) or None


def _record_buckets(prep: dict, extra: Optional[list[dict]] = None) -> dict[tuple, float]:
    """Normalized rates per (bucket, unit, period): $/month, $/kWh, $/kW-month; seasonal non-energy annualized.
    ``extra``: chosen fixed-charge variant items (only when the same variant applies at every level)."""
    out: dict[tuple, float] = defaultdict(float)
    volume = prep.get("volume_unit", "kwh")
    units = BASIS_UNITS if volume == "kwh" else {**BASIS_UNITS, "kwh": f"$/{VOLUME_LABELS.get(volume, volume)}"}
    for item in [item for item, _ in prep["priced"]] + list(extra or []):
        period = _period_label(item)
        weight = len(item["months"]) / 12 if item.get("months") and not period else 1.0
        out[(item["bucket"], units[item["basis"]], period)] += float(item["value"]) * item["factor"] * weight
    return out


def _bucket_stats(per_utility: dict[str, list[dict[tuple, float]]]) -> list[dict]:
    keys = sorted({k for rows in per_utility.values() for row in rows for k in row},
                  key=lambda k: (BUCKETS.index(k[0]) if k[0] in BUCKETS else len(BUCKETS), k[1], k[2] or ""))
    out = []
    for bucket, unit, period in keys:
        values = [statistics.median([row.get((bucket, unit, period), 0.0) for row in rows])
                  for rows in per_utility.values() if rows]
        out.append({"bucket": bucket, "unit": unit, "period": period, **_rate(summary_stats(values))})
    return out


def _energy_block(contributors: dict[str, list[tuple[dict, dict]]], ctx: dict, kind: str) -> Optional[dict]:
    """TOU or tier summary of the contributing records' energy prices; None when the model has none."""
    per_utility: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    signatures, dates, hours, windows = set(), set(), defaultdict(set), set()
    for utility, preps in contributors.items():
        for prep, record in preps:
            signature = []
            for item, comp in prep["priced"]:
                if item["type"] != "energy" or (kind == "tou") != bool(item.get("tou_period")) or (
                        kind == "tiers" and item.get("tier_number") is None):
                    continue
                label = _period_label(item) or "all"
                per_utility[utility][label].append(float(item["value"]) * item["factor"])
                signature.append((label, item["value"], item["unit"]))
                dates.add(comp.get("effective_date"))
                if comp.get("tou_hours"):
                    hours[label].add(comp.get("tou_hours"))
                if "tier_lower" in item:
                    windows.add((item.get("season") or "all year", tuple(item.get("months") or range(1, 13)),
                                 item["tier_number"], item["tier_lower"], _clean(item["tier_upper"])))
            if signature:
                signatures.add(tuple(sorted(signature, key=str)))
    if not signatures:
        return None
    labels = sorted({label for periods in per_utility.values() for label in periods})
    prices = {label: _rate(summary_stats([statistics.median(periods[label]) for periods in per_utility.values()
                                          if label in periods])) for label in labels}
    block = {"prices": prices, "identical_in_all_records": len(signatures) == 1,
             "effective_dates": sorted(d for d in dates if d)}
    if kind == "tou":
        entry = ctx.get("shares_entry") or {}
        source = entry.get("source") or {}
        block.update({"shares_id": ctx.get("shares_id"), "shares": ctx.get("shares"), "period": entry.get("period"),
                      "source": {k: source.get(k) for k in ("title", "url", "location")} if source else None,
                      "hours": {label: sorted(texts)[0] if len(texts) == 1 else sorted(texts)
                                for label, texts in sorted(hours.items())}})
    else:
        block["windows"] = [{"season": season, "months": list(months), "tier": tier, "from_kwh": lo, "to_kwh": hi}
                            for season, months, tier, lo, hi in sorted(windows, key=str)]
    return block


def _model_label(key: tuple, crosswalk: dict) -> str:
    province, fuel, sector, structure, band = key
    vocabulary = (crosswalk.get("vocabulary") or {})
    # Gas commercial bands are building sizes in native volume units (method 7D-2), not the electricity kW bands.
    bands = (vocabulary.get("gas_size_bands") if fuel == "gas" else None) or vocabulary.get("size_bands") or {}
    sector_text = sector if sector != "commercial" else f"commercial {(bands.get(band) or {}).get('label') or band or ''}".strip()
    return f"{PROVINCE_NAMES.get(province, province)} {fuel} - {sector_text} - {STRUCTURE_LABELS.get(structure, structure)}"


def _fmt_money(value: Optional[float]) -> str:
    return "n/a" if value is None else f"${value:,.2f}"


def _rates_text(values: Iterable[Any]) -> str:
    return "/".join(f"{float(value):g}%" for value in values)


def _territorial_method_parts(model: dict) -> list[str]:
    """Method sentences for the joint rate book, reviewed percentage riders, subsidies and interim rates (method 7T-1,
    owner decisions 2026-11-24). Provincial models carry none of these fields, so their text is unchanged."""
    parts = []
    for book in model.get("shared_rate_books") or []:
        parts.append(f"{' and '.join(book['utilities'])} bill the same rate schedules; they count once, as "
                     f"{book['counted_as']} ({book['id']}, decided {book.get('decided')}).")
    riders = model.get("percentage_riders") or []
    applied = [rider for rider in riders if rider["treatment"] == "apply"]
    if applied:
        parts.append("Percentage riders applied to the base charges named by their reviewed entry "
                     "(data/models/percentage_riders.json; never to other riders): " + "; ".join(
                         f"{rider['component']} {_rates_text(rider['rates_percent'])} of {rider['base']} ({rider['id']})"
                         for rider in applied) + ".")
    excluded = [rider for rider in riders if rider["treatment"] == "exclude"]
    if excluded:
        parts.append("Disclosed, not applied (a percentage of the whole bill): " + "; ".join(
            f"{rider['component']} {_rates_text(rider['rates_percent'])} ({rider['id']})" for rider in excluded) + ".")
    subsidies = model.get("subsidies")
    if subsidies:
        if subsidies["after_subsidy"]:
            used = [f"{entry['name']} ({entry['utility']}) at {', '.join(entry['applied_at'])}"
                    for entry in subsidies["programs"] + subsidies["percentage_subsidies"] if entry.get("applied_at")]
            text = ("Costs are before subsidies: subsidy prices and credits stay out of them. The cost after automatic "
                    "subsidies applies " + ("; ".join(used) if used else "no subsidy at any level") + ".")
            treatments = {entry["treatment"] for entry in subsidies["programs"] if entry.get("applied_at")}
            if "reference_rates" in treatments:
                text += (" Reference rates are all-in: where they apply they replace the zone's whole tariff, every "
                         "charge and rider (owner decision 78).")
            if "first_block_price" in treatments:
                text += (" First-block prices are all-in: they replace the whole per-kWh price of the first-block kWh, "
                         "riders and credits included (owner decisions 76 and 78); credits not billed within the block "
                         "apply to the kWh above it.")
            if any(entry.get("seasons") for entry in subsidies["programs"] if entry.get("applied_at")):
                text += (" Seasonal first blocks are priced once per season and month-weighted by the season's months "
                         "(usage_levels.json seasons).")
            text += " " + (subsidies.get("tax_note") or "After-subsidy costs are shown before tax only.")
        else:
            text = f"Costs are before subsidies; no after-subsidy cost is shown: {subsidies.get('reason')}"
        skipped = sorted({f"{row['name']} ({row['utility']}): {row['reason'].rstrip('.')}"
                          for row in subsidies["not_applied"]})
        if skipped:
            text += " Not applied: " + "; ".join(skipped) + "."
        parts.append(text)
    for entry in model.get("interim") or []:
        parts.append(f"Interim rates, included and labelled: {entry['utility']} ({len(entry['records'])} record(s); "
                     f"{entry['entry']}, decided {entry.get('decided')}).")
    return parts


def _method_text(model: dict, key: tuple, levels: list[dict], component_counts: Counter,
                 component_examples: dict, conversions: set[str], zone_policy: str, pair_text: Optional[str] = None) -> str:
    province, fuel, sector, structure, band = key
    singular, noun = UTILITY_NOUNS.get((province, fuel), DEFAULT_NOUNS)
    prov = PROVINCE_NAMES.get(province, province)
    cov = model["coverage"]
    contributors = cov["contributing_utilities"]
    n = len(contributors)
    sector_text = model["label"].split(" - ", 1)[1].rsplit(" - ", 1)[0]
    structure_text = STRUCTURE_LABELS.get(structure, structure)
    parts = ["Modeled comparison indicator, not a tariff anyone is billed."]
    if n == 1:
        only = next(u for u in model["utilities"] if u["utility"] == contributors[0])
        records = ", ".join(f"{r['name']} [{r['tariff_code']}]" for r in only["records"])
        parts.append(f"Single source: {contributors[0]} ({records}) is the only {prov} {singular} with a computable "
                     f"live {sector_text} {structure_text} record; no averaging.")
    elif n:
        what = "at each usage level" if levels else "(component buckets only)"
        parts.append(f"Median of {n} {prov} {noun}' {sector_text} {structure_text} tariffs {what}, each counted once "
                     f"(zone policy '{zone_policy}': {ZONE_POLICY_TEXT[zone_policy]}; "
                     f"{len(cov['multi_zone_utilities'])} with more than one zone record).")
    else:
        parts.append("No contributing utility: every mapped record was excluded (see exclusions).")
    for entry in model.get("required_contributors") or []:
        if entry["withheld_at"]:
            parts.append(f"Withheld at {', '.join(entry['withheld_at'])}: required {singular} "
                         f"{' and '.join(entry['utilities'])} is not computable there, so the other {noun} are not "
                         f"shown alone ({(entry.get('reason') or '').rstrip('.')}; decided {entry.get('decided')}).")
    if pair_text:
        parts.append(pair_text)
    tou, tiers = model.get("tou"), model.get("tiers")
    energy = model["energy"]["status"]
    if energy == "market_estimated":
        parts.append(_estimate_method_text(model))
    elif energy == "market_pending":
        estimate = model.get("energy_estimate") or {}
        parts.append("Energy: market-priced energy is pending (no stored price); costs are delivery and regulatory "
                     "charges only, never a guessed energy price."
                     + (f" The estimate from simulated load shapes is unavailable: {estimate['reason'].rstrip('.')}."
                        if estimate.get("reason") and estimate.get("input_problem") else ""))
    elif energy == "absent":
        parts.append("Energy: the contributing records publish no energy component; costs are delivery and regulatory "
                     "charges only.")
    elif energy == "mixed":
        parts.append("Energy: contributing records differ (some without energy); compare with care.")
    other = sorted({name for entry in model["energy"].get("market_indexed_excluded") or [] for name in entry["components"]})
    if other:
        parts.append("Excludes market-indexed charges with no stored value that are not the energy price ("
                     + "; ".join(other[:3]) + f"), pending Phase {'6C' if province == 'AB' else '6'}; the model "
                     "state does not change.")
    if tou:
        scope = "province-wide prices identical in every contributing record" if tou["identical_in_all_records"] \
            else "prices that differ between records (median per period shown)"
        order = list(tou.get("shares") or {})
        labels = sorted(tou["prices"], key=lambda label: (order.index(label) if label in order else len(order), label))
        prices = ", ".join(f"{label} ${tou['prices'][label]['median']:.4f}/kWh" for label in labels)
        shares = " / ".join(f"{share * 100:g}% {label}" for label, share in (tou.get("shares") or {}).items())
        title = ((tou.get("source") or {}).get("title")) or tou.get("shares_id")
        parts.append(f"TOU energy: {scope} ({prices}; effective {', '.join(tou['effective_dates'])}), weighted "
                     f"{shares} of monthly kWh per {title}.")
    if tiers:
        scope = "identical in every contributing record" if tiers["identical_in_all_records"] else "differing between records"
        windows = "; ".join(f"{w['season']} tier {w['tier']} " + (f"above {w['from_kwh']:,.0f}" if w["to_kwh"] is None
                                                                  else f"{w['from_kwh']:,.0f}-{w['to_kwh']:,.0f}")
                            + " kWh" for w in tiers["windows"])
        parts.append(f"Tiered energy ({scope}; effective {', '.join(tiers['effective_dates'])}): thresholds as "
                     f"published ({windows}); each month uses its season's tiers and the year is month-weighted.")
    if levels:
        parts.append("Usage levels: " + "; ".join(
            (f"{lv['id']} {float(lv['quantity']):,.0f} {VOLUME_LABELS.get(lv.get('unit'), lv.get('unit'))}"
             if "quantity" in lv else
             f"{lv['id']} {lv['kwh']:,.0f} kWh" + ("" if lv.get("kw") is None else f" at {lv['kw']:g} kW")) + "/month"
            for lv in levels) + ".")
    else:
        parts.append("No usage level is defined for this size band yet; only component buckets are reported.")
    if conversions:
        parts.append("Conversions: " + "; ".join(sorted(conversions)) + ".")
    if model.get("block_periods"):
        parts.append("Block thresholds published in kWh without a period use reviewed data/models/block_periods.json "
                     "entries: " + "; ".join(f"{e['id']} ({e['utility']}, "
                                             f"{BLOCK_PERIOD_WORDS.get(e['threshold_period'], e['threshold_period'])})"
                                             for e in model["block_periods"]) + ".")
    lines = {}
    for level in model["levels"]:
        for line in level["with_tax"].get("lines") or []:
            lines.setdefault(line["name"], f"{line['name']} {line['rate'] * 100:g}% of the {line['base'].replace('_', ' ')}"
                             + (" (subtracted)" if line["kind"] == "rebate" else ""))
    if lines:
        skipped = sorted({f"{s['name']} at {lv['id']} ({s['reason']})" for lv in model["levels"]
                          for s in lv["with_tax"].get("not_applied") or []})
        parts.append("With tax: " + "; ".join(lines.values()) + "; lines never compound."
                     + (" Not applied: " + "; ".join(skipped) + "." if skipped else ""))
    outliers = [f"{lv['id']}: " + ", ".join(f"{o['utility']} {o['deviation_pct']:+.1f}%" for o in lv["outliers"])
                for lv in model["levels"] if lv["outliers"]]
    if outliers:
        parts.append("Outliers versus the median (cost without tax): " + "; ".join(outliers) + ".")
    if model.get("reference_customer"):
        parts.append("Conditional charges included because the reference customer pays them (usage_levels.json "
                     "reference_customer): " + "; ".join(
                         f"{entry['id']} {entry['components']} (e.g. {', '.join(entry['examples'])})"
                         for entry in model["reference_customer"]) + ".")
    if model.get("fixed_charge_variants"):
        parts.append("Fixed charges published as variants of one charge (by phase, amperage, monthly peak or "
                     "annual-volume band) are priced for the reference customer (usage_levels.json "
                     "fixed_charge_variants): " + "; ".join(
                         f"{entry['id']} ({entry['reference']}; decided {entry['decided']}) at "
                         f"{', '.join(entry['levels'])}: {', '.join(entry['components'])} "
                         f"({', '.join(entry['utilities'])})" for entry in model["fixed_charge_variants"])
                     + "; component buckets include a variant only when the same one applies at every level.")
    if model.get("peak_month_factor"):
        peak = model["peak_month_factor"]
        parts.append(f"Classes and charges that follow the monthly peak use {float(peak['factor']):g} x the level "
                     f"({peak['id']}, decided {peak.get('decided')}).")
    for entry in model.get("elective_classes") or []:
        used = defaultdict(list)
        for level_id, code in entry["chosen"].items():
            used[code].append(level_id)
        parts.append(f"{entry['utility']} customers may elect {' or '.join(entry['tariff_codes'])}; the cheaper is "
                     f"priced at each level ({entry['id']}, decided {entry.get('decided')}): "
                     + "; ".join(f"{code} at {', '.join(ids)}" for code, ids in sorted(used.items())) + ".")
    parts.extend(_territorial_method_parts(model))
    if component_counts:
        parts.append("Excluded components: " + "; ".join(
            f"{reason.replace('_', ' ')} {count} (e.g. {', '.join(component_examples[reason])})"
            for reason, count in component_counts.most_common()) + ".")
    left_out = sorted({e["utility"] for e in model["exclusions"] if e["scope"] in ("record", "utility")
                       and e["utility"] not in contributors})
    if left_out:
        parts.append("Mapped but not contributing: " + ", ".join(left_out) + " (see exclusions).")
    not_applied = NOT_APPLIED.get((province, fuel))
    if not_applied:
        parts.append("Not modeled: " + "; ".join(not_applied) + ".")
    parts.append(f"Coverage: {n} of {cov['utilities_in_province']} {prov} {fuel} {noun} with live records"
                 + (f"; no mapped record: {', '.join(cov['missing_utilities'])}" if cov["missing_utilities"] else "")
                 + ". Contributing: " + (", ".join(contributors) or "none") + ".")
    parts.append(f"Generated {model['generated_from']['as_of']} from {model['generated_from']['input']}.")
    return re.sub(r"\.\.(?=\s|$)", ".", " ".join(parts))


def required_contributors(crosswalk: dict, key: tuple) -> list[dict]:
    """Crosswalk 'required_contributors' entries for a model key (province, fuel and, when set, sector, structure and
    size_band): a level where a listed utility is not computable is withheld instead of showing the others alone."""
    province, fuel, sector, structure, band = key
    return [entry for entry in (crosswalk or {}).get("required_contributors") or []
            if isinstance(entry, dict) and entry.get("utilities") and entry.get("province") == province
            and entry.get("fuel", fuel) == fuel and entry.get("sector", sector) == sector
            and entry.get("structure", structure) == structure and entry.get("size_band", band) == band]


def find_market_energy_shape(usage_levels: Optional[dict], province: Any, fuel: Any, sector: Any,
                             level_sector: Any) -> tuple[Optional[str], Optional[dict]]:
    """(id, entry) of the usage_levels market_energy_shapes entry whose applies_to matches a model; (None, None) else."""
    for key, entry in ((usage_levels or {}).get("market_energy_shapes") or {}).items():
        applies = entry.get("applies_to") if isinstance(entry, dict) else None
        if not isinstance(applies, dict):
            continue
        sectors = applies.get("sectors") or []
        if (province in (applies.get("provinces") or []) and applies.get("fuel", fuel) == fuel
                and (level_sector in sectors or sector in sectors)):
            return key, entry
    return None, None


def level_applies(level: dict, province: Any) -> bool:
    """True when a usage level applies to a province: levels without a 'provinces' list apply everywhere. Method 7S-1
    used the list to give Ontario and Alberta their own 50-499 kW and 500-4,999 kW customers; since method 7S-2 (owner
    decision 120) no level has one, and the feature stays for a future province-specific level."""
    provinces = level.get("provinces")
    if provinces is None:
        return True
    if not isinstance(provinces, list) or not all(isinstance(code, str) for code in provinces):
        raise ValueError(f"usage level {level.get('id')!r}: 'provinces' must be a list of province codes")
    return province in provinces


def load_market_document(path: PathLike = None) -> tuple[Optional[dict], Optional[str]]:
    """The observed Ontario market history (default site/data/market_pricing_ontario.json) read with
    scrapers.utils.market_pricing; (None, reason) when it is missing or not an observed IESO file."""
    target = Path(path or MARKET_PATH)
    if not target.is_file():
        return None, f"market history file {target.name} not found"
    try:
        from scrapers.utils.market_pricing import load_ontario_market_pricing

        return load_ontario_market_pricing(target), None
    except Exception as exc:  # a bad market file only makes the benchmark and the estimated energy unavailable
        return None, f"market history file {target.name} not usable ({exc})"


def _market_context(document: Any) -> dict:
    if document is _DEFAULT:
        document, problem = load_market_document()
    elif not isinstance(document, dict):
        document, problem = None, "no market history document was supplied"
    else:
        problem = None
    meta = (document or {}).get("metadata")
    info = {"derivation_method": meta.get("derivation_method"), "generated_at": meta.get("generated_at")} \
        if isinstance(meta, dict) else None
    return {"document": document, "problem": problem, "file": info}


def _market_energy_level(level: dict, price: float, inputs: dict) -> dict:
    """Add market energy before taxes and zone/utility aggregation, never to a rounded median."""
    energy_cost = price * level["kwh"]
    applied = inputs["applied"]
    without, taxed, line_amounts = {}, {}, defaultdict(list)
    for utility, rows in inputs["zone_rows"].items():
        totals = [apply_tax_lines(cost + energy_cost, energy + energy_cost, applied) for cost, energy in rows]
        without[utility] = statistics.median([cost + energy_cost for cost, _ in rows])
        taxed[utility] = statistics.median([total for total, _ in totals])
        for index in range(len(applied)):
            line_amounts[index].append(statistics.median([amounts[index] for _, amounts in totals]))
    stats = summary_stats(without.values())
    return {"market_energy_per_kwh": price, "market_energy_cost": round(energy_cost, 2),
            "without_tax": _money(stats),
            "closest_utility": closest_to_median(without, stats["median"]),
            "outliers": [{**row, "cost": round(row["cost"], 2)} for row in find_outliers(without, stats)],
            "utilities": [{"utility": name, "cost_without_tax": round(cost, 2),
                           "cost_with_tax": round(taxed[name], 2)} for name, cost in without.items()],
            "with_tax": {**_money(summary_stats(taxed.values())),
                         "lines": [{**line, "median_amount": round(statistics.median(line_amounts[i]), 2)
                                    if line_amounts[i] else None} for i, line in enumerate(applied)],
                         "not_applied": inputs["not_applied"]}}


def _benchmark(model: dict, market: dict, level_inputs: dict, config: dict, as_of: date) -> dict:
    from scrapers.utils.market_pricing import BENCHMARK_LABEL, historical_market_price

    info = {"available": False, "reason": None, "label": BENCHMARK_LABEL,
            "profile_backed": {"available": False, "reason": "No suitable observed customer-class load profile "
                               "has been verified; geographic and assigned settlement profiles are not substitutes."},
            "exclusions": ["Customer-specific distribution losses and retail procurement/administration fees.",
                           ("Class A Global Adjustment and conditional or unpriced tariff components."
                            if model["key"]["province"] == "ON" else "Conditional or unpriced tariff components."),
                           "Market-indexed non-energy charges remain excluded, including operating reserve."]}
    try:
        if not isinstance(config, dict):
            raise ValueError("benchmark configuration is invalid")
        if market.get("document") is None:
            raise ValueError(market.get("problem") or "market history is unavailable")
        priced = historical_market_price(market["document"], province=model["key"]["province"],
                                         as_of=as_of, max_lag_months=config.get("max_window_lag_months"))
    except ValueError as exc:
        info["reason"] = str(exc)
        logger.warning("Market benchmark %s unavailable: %s", model["id"], exc)
    else:
        info.update(priced)
        for level in model["levels"]:
            inputs = level_inputs[level["id"]]
            if level.get("withheld") or not inputs.get("zone_rows") or not inputs.get("market_eligible"):
                continue
            level["market_benchmark"] = {
                "available": True, "reason": None,
                **_market_energy_level(level, priced["price_per_kwh"], inputs)}
            info["available"] = True
        if not info["available"]:
            info["reason"] = "No eligible market-only usage level with complete required delivery contributors."
    for level in model["levels"]:
        if "market_benchmark" not in level:
            level["market_benchmark"] = {"available": False, "reason": info["reason"] or
                                         "Level withheld, not computable, or already includes priced energy."}
    return info


# Method 7S-2 (owner decisions 119-123, 2026-11-25): the Ontario and Alberta 50-499 kW and 500-4,999 kW models price the
# market energy that has no stored value from the general load shape of the province's simulated buildings in the size
# band (usage_levels market_energy_shapes) and the observed market heatmap, in the main table, labelled estimated.
_MARKET_CLOCK_TEXT = {
    "ON": "Eastern Standard Time all year (IESO market time), so the simulated steps are not shifted",
    "AB": "Alberta prevailing local time (AESO market time), so steps inside daylight saving move one hour later",
}
_BAND_TEXT = {"commercial_medium": "50 to 499 kW", "commercial_large": "500 to 4,999 kW"}
_HEATING_TEXT = {"Electricity": "electric", "NaturalGas": "natural gas"}
_ESTIMATE_NOT_MODELED = {
    "ON": "Not modeled: Class A Global Adjustment (paid by peak demand factor; a customer of 1,000 kW or less is Class "
          "B), retail contracts, and the distributors' loss factors (next item).",
    "AB": "Not modeled: retailer energy charges and margins, and distribution loss factors. A site using 250,000 kWh a "
          "year or more cannot take the Rate of Last Resort, so its energy follows the pool price through a retailer.",
}
# The note the Ontario scraper writes on every record (scrapers/utilities/ontario_ldc.py): "Published total loss factors
# (...): <label> <value>; <label> <value>."
_LOSS_NOTE_RE = re.compile(r"Published total loss factors \([^)]*\): (?P<values>.+?)\.(?:\s|$)")
_LOSS_VALUE_RE = re.compile(r"^(?P<label>.*?)\s+(?P<value>\d\.\d{2,5})$")


def _archetype_context(value: Any) -> dict:
    """Simulated archetypes for the estimate: _DEFAULT loads the repository's BTAP runs on first use, None disables."""
    return {"set": None if value is _DEFAULT else value, "pending": value is _DEFAULT,
            "problem": "no simulated archetypes were supplied" if value is None else None}


def _archetype_set(context: dict) -> Any:
    if context.get("pending"):
        context["pending"] = False
        try:
            from pipeline.archetype_profiles import load_archetypes

            context["set"] = load_archetypes()
        except Exception as exc:  # unreadable BTAP data only makes the estimate unavailable (market energy pending)
            context["problem"] = f"simulated archetypes unavailable ({type(exc).__name__}: {exc})"
            logger.warning("Simulated archetypes unavailable: %s", exc)
    return context.get("set")


def _archetype_summary(context: dict) -> Optional[dict]:
    """What the build read from the archetypes: counts and a fingerprint of the values used (run problems can name
    machine paths, so they are counted, not listed)."""
    data = context.get("set")
    if data is None:
        return {"available": False, "problem": context.get("problem")} if not context.get("pending") else None
    from pipeline.archetype_profiles import archetype_fingerprint

    root = Path(data.root)
    try:
        root = root.resolve().relative_to(ROOT)
    except ValueError:
        pass
    return {"available": True, "source": root.as_posix() if not root.is_absolute() else root.name,
            "workbook_rows": data.workbook_rows, "runs": len(data.runs), "runs_left_out": len(data.problems),
            "cities": {province: sorted({run.city for run in data.runs if run.province == province})
                       for province in sorted({run.province for run in data.runs})},
            "fingerprint": archetype_fingerprint(data)}


def _band_limits(crosswalk: dict, band: Any) -> Optional[tuple[float, Optional[float]]]:
    def number(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    entry = ((crosswalk.get("vocabulary") or {}).get("size_bands") or {}).get(band)
    low = entry.get("min_kw") if isinstance(entry, dict) else None
    high = entry.get("max_kw") if isinstance(entry, dict) else None
    if not number(low) or (high is not None and not number(high)):
        return None
    return float(low), None if high is None else float(high)


def _estimate_info(shape_id: str, shape: dict, market: dict) -> dict:
    return {"available": False, "reason": None, "input_problem": True, "profile_id": shape_id,
            "label": shape.get("label") or ESTIMATE_LABEL, "status": shape.get("status"), "price_per_kwh": None,
            "flat_price_per_kwh": None, "price_range": None, "window": None, "market_file": market.get("file"),
            "shape": None, "buildings": [], "assumptions": []}


def _energy_estimate(key: tuple, shape_id: str, shape: dict, market: dict, as_of: date, archetypes: dict,
                     limits: Optional[tuple[float, Optional[float]]]) -> dict:
    """Estimated market energy price ($/kWh) of a model (method 7S-2, owner decisions 119-123, 2026-11-25).

    The general load shape of every simulated building of the province whose average monthly peak is in the model's
    size band (both heating fuels; each building scaled to the same yearly use and counted once, averaged bin by bin,
    decision 121) is priced with the observed market heatmap (scrapers.utils.market_pricing.load_shape_price, owner
    decision 12). Each building is also priced alone for the published list and range, and a flat load gives the
    same-use-every-hour comparison. Any doubtful input leaves the estimate unavailable with its reason and
    ``input_problem`` set (fail closed): the model then stays market_energy_pending (decision 119)."""
    province, band = key[0], key[4]
    info = _estimate_info(shape_id, shape, market)

    def unavailable(reason: str) -> dict:
        info["reason"] = reason
        return info

    lag = shape.get("max_window_lag_months")
    if not isinstance(lag, int) or isinstance(lag, bool) or lag < 1:
        return unavailable(f"market energy shape {shape_id} lacks a positive max_window_lag_months")
    if limits is None:
        return unavailable(f"size band {band} has no kW limits in the crosswalk")
    document = market.get("document")
    if document is None:
        return unavailable(market.get("problem") or "no market history document")
    from pipeline.archetype_profiles import DAY_TYPES, runs_in_band
    from scrapers.utils.market_pricing import load_shape_price

    keys = [(month, kind, hour) for month in range(1, 13) for kind in DAY_TYPES for hour in range(24)]
    try:
        # A flat load checks the market history first, so a stale or wrong file never costs reading the simulated
        # runs; its price (the same use in every hour, months equally weighted) equals the historical benchmark's.
        probe = load_shape_price(document, province=province, as_of=as_of, max_lag_months=lag,
                                 bin_kw=dict.fromkeys(keys, 1.0), month_kwh=dict.fromkeys(range(1, 13), 1.0))
        info["window"] = probe.get("window")
        if not probe.get("ok"):
            return unavailable(probe.get("reason") or "the market history is not usable")
        data = _archetype_set(archetypes)
        if data is None:
            return unavailable(archetypes.get("problem") or "no simulated archetypes")
        runs = sorted(runs_in_band(data, province, *limits), key=lambda run: run.datapoint_id)
        if not runs:
            return unavailable(f"no simulated building in {province} has an average monthly peak in this size band")
        scaled = []
        for run in runs:
            total = math.fsum(run.market_month_kwh.values()) if isinstance(run.market_month_kwh, dict) else 0.0
            if set(run.market_bin_kw) != set(keys) or set(run.market_month_kwh) != set(range(1, 13)) or not total > 0:
                return unavailable(f"{run.building_type} ({run.datapoint_id}): no complete load on the {province} "
                                   "market clock")
            scaled.append((run, total))
        # Decision 121: each building divided by its own yearly kWh (the same yearly use), then the plain mean.
        general_bins = {k: math.fsum(run.market_bin_kw[k] / total for run, total in scaled) / len(scaled) for k in keys}
        general_months = {month: math.fsum(run.market_month_kwh[month] / total for run, total in scaled) / len(scaled)
                          for month in range(1, 13)}
        priced = load_shape_price(document, province=province, bin_kw=general_bins, month_kwh=general_months,
                                  as_of=as_of, max_lag_months=lag)
        if not priced.get("ok"):
            return unavailable(f"general load shape: {priced.get('reason') or 'not computable'}")
        buildings = []
        for run, _ in scaled:
            own = load_shape_price(document, province=province, bin_kw=run.market_bin_kw,
                                   month_kwh=run.market_month_kwh, as_of=as_of, max_lag_months=lag)
            if not own.get("ok"):
                return unavailable(f"{run.building_type} ({run.datapoint_id}): {own.get('reason') or 'not computable'}")
            buildings.append({"datapoint_id": run.datapoint_id, "building_type": run.building_type,
                              "heating_fuel": run.heating_fuel, "city": run.city,
                              "floor_area_m2": round(run.floor_area_m2, 1),
                              "average_monthly_kwh": round(run.average_monthly_kwh),
                              "average_monthly_peak_kw": round(run.average_monthly_peak_kw, 1),
                              "kwh_per_kw": round(run.kwh_per_kw, 1), "quality_flag": run.quality_flag,
                              "price_per_kwh": own["price_per_kwh"]})
    except Exception as exc:  # a defect in the estimate leaves the model market_energy_pending, never breaks the build
        logger.exception("Estimated market energy %s unavailable", key_label(key))
        return unavailable(f"estimate calculation failed ({type(exc).__name__}: {exc})")
    buildings.sort(key=lambda b: (b["price_per_kwh"], b["building_type"], b["heating_fuel"]))
    prices = [b["price_per_kwh"] for b in buildings]
    info.update(available=True, input_problem=False, price_per_kwh=priced["price_per_kwh"],
                flat_price_per_kwh=probe["price_per_kwh"], price_range={"min": min(prices), "max": max(prices)},
                buildings=buildings,
                shape={"buildings": len(buildings), "cities": sorted({b["city"] for b in buildings}),
                       "heating_fuels": dict(sorted(Counter(b["heating_fuel"] for b in buildings).items())),
                       "quality_flagged": sum(1 for b in buildings if b["quality_flag"]),
                       "month_weights": {str(month): round(weight, 6) for month, weight in general_months.items()},
                       "shape_factors": priced.get("shape_factors")})
    return info


def _no_estimate(shape_id: str, shape: dict, market: dict, reason: str) -> dict:
    """A model the shape covers whose records all have a stored energy price: nothing to estimate, no input problem."""
    return {**_estimate_info(shape_id, shape, market), "reason": reason, "input_problem": False}


def _loss_factor_summary(contributing: dict[str, list[tuple[dict, dict]]]) -> dict:
    """The contributing Ontario records' published total loss factors for a secondary-metered customer (a record's only
    value when it publishes one), read from the note the scraper writes; decision 122: stated, never applied."""
    values = []
    for pairs in contributing.values():
        for _, record in pairs:
            match = _LOSS_NOTE_RE.search(record.get("notes") or "")
            if not match:
                continue
            found = [(m.group("label"), float(m.group("value"))) for m in
                     (_LOSS_VALUE_RE.match(part.strip()) for part in match.group("values").split(";")) if m]
            secondary = [value for label, value in found if "secondary" in label.lower()]
            if len(secondary) == 1:
                values.append(secondary[0])
            elif len(found) == 1:
                values.append(found[0][1])
    if not values:
        return {"records": 0, "min": None, "median": None, "max": None}
    return {"records": len(values), "min": min(values), "median": round(statistics.median(values), 4),
            "max": max(values)}


def _estimate_assumptions(key: tuple, info: dict, document: Optional[dict], singular: str) -> list[str]:
    """The plain-language assumptions of an available estimate (decision 119: the energy states its assumptions)."""
    province, band = key[0], key[4]
    shape, window = info["shape"], info["window"] or {}
    fuels = " and ".join(f"{count} {_HEATING_TEXT.get(fuel, fuel)}-heated" for fuel, count in
                         shape["heating_fuels"].items())
    span = f"the {window.get('months')} complete months {window.get('start_month')} to {window.get('end_month')}"
    eras = Counter(entry.get("era") for entry in (document or {}).get("monthly") or [] if isinstance(entry, dict))
    if province == "ON":
        history = (f"the observed IESO history of {span}" + (f" ({eras['hoep']} months of the legacy HOEP, then "
                   f"{eras['oemp']} of the Ontario Price)" if eras.get("hoep") and eras.get("oemp") else ""))
        price_text = "published energy price"
        adder = ", plus that month's actual Class B Global Adjustment"
    else:
        history, price_text, adder = f"the observed AESO pool price history of {span}", "published pool price", ""
    flat, price = info["flat_price_per_kwh"], info["price_per_kwh"]
    low, high = info["price_range"]["min"], info["price_range"]["max"]
    items = [
        "Estimated, not live: these customers' market energy has no published price, so the table adds this modeled "
        "amount (method 7S-2, owner decisions 119 to 123, November 25, 2026). It never counts as live coverage.",
        f"Load shape: the general shape of the {shape['buildings']} simulated buildings in "
        f"{' and '.join(shape['cities'])} whose average monthly peak (the mean of the 12 monthly highest 15-minute "
        f"demands) is {_BAND_TEXT.get(band, band)}: {fuels}. Each building is scaled to the same yearly use and counted "
        "once, then the shapes are averaged hour by hour in the heatmap's 576 bins (calendar month x weekday or "
        "weekend x hour). The buildings are NECB 2020 archetypes simulated with NRCan's BTAP on CWEC 2020 typical "
        f"weather, not metered customers; {shape['quality_flagged']} of them exceed 300 occupied unmet hours (a "
        "simulation quality flag) and are kept.",
        "Example customer unchanged: the shape sets only when the energy is used, so its price per kWh; each usage "
        "level keeps its own kWh and kW, and its energy amount is that kWh x the price.",
        f"Prices: {history}. Each month's {price_text} is multiplied by that calendar month's shape factor (the "
        "shape's load-weighted mean price over the month's time-weighted mean, 1 for a flat load)" + adder + "; a "
        "calendar month's price is the mean of its window months, and the months are weighted by the shape's own use.",
        f"Market clock: {_MARKET_CLOCK_TEXT.get(province, 'the market operator time')}; holidays count as the weekday "
        "they fall on.",
        f"Taxes: the model's tax lines apply to each {singular}'s delivery charges plus this energy, as for any energy "
        "charge.",
    ]
    if province in _ESTIMATE_NOT_MODELED:
        items.append(_ESTIMATE_NOT_MODELED[province])
    losses = info.get("loss_factors")
    if losses and losses["records"]:
        items.append(
            f"Loss factors not applied, as in every model (owner decision 122): {losses['records']} contributing "
            f"records publish total loss factors of {losses['min']:.4f} to {losses['max']:.4f} (median "
            f"{losses['median']:.4f}) for a secondary-metered customer. Ontario bills market energy and the Global "
            "Adjustment on metered kWh x that factor, so the energy amount would be about "
            f"{(losses['min'] - 1) * 100:.1f}% to {(losses['max'] - 1) * 100:.1f}% higher.")
    elif losses:
        items.append("Loss factors not applied, as in every model (owner decision 122); no published value was found "
                     "in the contributing records.")
    items.append(f"For comparison, the same use in every hour of the window costs ${flat:.4f}/kWh (the historical "
                 f"market benchmark); the general shape's ${price:.4f}/kWh is {(price / flat - 1) * 100:+.1f}% from "
                 f"it, and the buildings' own prices range from ${low:.4f} to ${high:.4f}/kWh.")
    items.append("If an input fails (the market history is missing, stale or invalid, or the simulated buildings cannot "
                 "be read), the model shows delivery charges only, labelled market energy pending, never a guessed "
                 "price.")
    return items


def _estimate_method_text(model: dict) -> Optional[str]:
    """The method sentence of an estimated model (decision 122: Ontario states its published loss factors)."""
    info = model.get("energy_estimate") or {}
    if not info.get("available"):
        return None
    province, band = model["key"]["province"], model["key"].get("size_band")
    shape, window = info["shape"], info["window"] or {}
    singular = model["coverage"]["contributor_noun"]["singular"]
    text = (f"Energy (estimated, method 7S-2, owner decisions 119 to 123 of 2026-11-25): the market energy, which has "
            f"no stored price, is priced at ${info['price_per_kwh']:.6f}/kWh, the {window.get('start_month')} to "
            f"{window.get('end_month')} observed "
            + ("IESO energy price plus actual Class B Global Adjustment" if province == "ON" else "AESO pool price")
            + f" of the general load shape of {shape['buildings']} simulated {' and '.join(shape['cities'])} buildings "
            f"with an average monthly peak of {_BAND_TEXT.get(band, band)} (same use every hour: "
            f"${info['flat_price_per_kwh']:.6f}/kWh), x each level's kWh, added to each {singular}'s delivery cost "
            "before tax. Estimated, not live coverage; if an input fails the model falls back to delivery charges only "
            "(see the estimate's assumptions).")
    losses = info.get("loss_factors")
    if losses and losses["records"]:
        text += (f" Published total loss factors (secondary metered) of {losses['records']} contributing records: "
                 f"{losses['min']:.4f} to {losses['max']:.4f}, median {losses['median']:.4f}; not applied, as in every "
                 "model (decision 122).")
    return text


def _group_skips(skips: Iterable[dict], scope: str = "records") -> list[dict]:
    """Not-applied subsidies grouped by subsidy, utility and reason, listing the records (or levels) concerned."""
    grouped: dict[tuple, dict] = {}
    for skip in skips:
        key = (skip["id"], skip.get("utility") or "", skip["reason"])
        row = grouped.setdefault(key, {"id": skip["id"], "name": skip.get("name"), "utility": skip.get("utility"),
                                       "reason": skip["reason"], scope: []})
        for value in (skip.get("records") or [skip.get("record_id")]) if scope == "records" else [skip.get("level")]:
            if value is not None and value not in row[scope]:
                row[scope].append(value)
    return [grouped[key] for key in sorted(grouped, key=str)]


def _after_subsidy_level(policy: dict, costs: dict, after_costs: dict, problems: dict, withheld: Optional[dict],
                         applied: set, skipped: list) -> dict:
    """A level's cost after automatic subsidies, before tax only (owner decision 74, 2026-11-24): statistics over the
    same utilities as the cost before subsidies, so the two compare, and unavailable when any of them is not computable
    after subsidies (reason listed)."""
    block = {"available": False, "reason": None, "tax_basis": BEFORE_TAX_ONLY,
             "without_tax": _money(summary_stats([])), "closest_utility": None,
             "not_computable": [{"utility": utility, "reason": reason} for utility, reason in sorted(problems.items())],
             "applied": sorted(applied), "not_applied": _group_skips(skipped)}
    if not policy["after_subsidy"]:
        block["reason"] = policy["reason"]
    elif withheld:
        block["reason"] = "the level is withheld (see withheld)"
    elif not costs:
        block["reason"] = "no utility is computable at this level"
    elif problems or set(after_costs) != set(costs):
        block["reason"] = ("the cost after subsidies is not computable for "
                           + ", ".join(sorted(set(problems) | (set(costs) - set(after_costs)))))
    else:
        stats = summary_stats(after_costs.values())
        closest = closest_to_median(after_costs, stats["median"])
        block.update(available=True, without_tax=_money(stats), closest_utility={
            "utility": closest, "cost_without_tax": round(after_costs[closest], 2),
            "deviation_pct": round((after_costs[closest] - stats["median"]) / stats["median"] * 100, 2)
            if stats["median"] else None})
    return block


def _territorial_fields(model: dict, chosen: dict, preps: dict, crosswalk: dict, ctx: dict, policy: Optional[dict],
                        level_out: list[dict]) -> None:
    """Add the method 7T-1 fields (owner decisions 64-75, 2026-11-24) that apply to a model: the joint rate book, the
    reviewed percentage riders its records carry, interim labels (and warnings) and, for a territory, the subsidies
    block. Each field is added only when it applies, so provincial models stay unchanged."""
    records = [(utility, record) for utility, rows in chosen.items() for record, _, _ in rows]
    books = [book for book in (crosswalk or {}).get("shared_rate_books") or []
             if isinstance(book, dict) and book.get("counted_as") in chosen]
    if books:
        model["shared_rate_books"] = [{k: book.get(k) for k in ("id", "utilities", "counted_as", "quote", "source",
                                                                 "decided", "note")} for book in books]
    entries = {entry["id"]: entry for entry in ctx.get("percent_entries") or []}
    used: dict[str, dict] = {}
    for utility, record in records:
        for item in preps[id(record)]["items"]:
            entry = entries.get(item.get("percentage_entry"))
            if entry is None:
                continue
            row = used.setdefault(entry["id"], {"id": entry["id"], "utility": utility, "component": item["component"],
                                                "treatment": entry["treatment"], "rates_percent": [], "items": []})
            row["items"].append(item)
            if item.get("value") is not None and float(item["value"]) not in row["rates_percent"]:
                row["rates_percent"].append(float(item["value"]))
    if used:
        model["percentage_riders"] = [
            {**{k: row[k] for k in ("id", "utility", "component", "treatment")},
             "rates_percent": sorted(row["rates_percent"]), "base": (entries[eid].get("base") or {}).get("text"),
             **{k: entries[eid].get(k) for k in ("quote", "source_url", "location", "decided")}}
            for eid, row in sorted(used.items())]
    labels = {entry.get("id"): entry for entry in (crosswalk or {}).get("interim_rates") or [] if isinstance(entry, dict)}
    interim: dict[tuple, list] = defaultdict(list)
    for utility, record in records:
        if record.get("interim"):
            interim[(utility, record["interim"])].append(record.get("id"))
    if interim:
        model["interim"] = [{"utility": utility, "entry": entry_id, "records": ids,
                             **{k: (labels.get(entry_id) or {}).get(k) for k in ("quote", "source", "decided")}}
                            for (utility, entry_id), ids in sorted(interim.items())]
        for row in model["interim"]:
            model["warnings"].append(f"Interim rates included: {row['utility']} ({len(row['records'])} record(s); "
                                     f"{row['entry']}, owner decision 72): \"{row['quote']}\"")
    if policy is None:
        return
    config = ctx.get("subsidies") or {}
    applied_at: dict[str, list[str]] = defaultdict(list)
    skipped = []
    for level in level_out:
        block = level.get("after_subsidy") or {}
        for subsidy_id in block.get("applied") or []:
            applied_at[subsidy_id].append(str(level["id"]))
        skipped.extend({**row, "level": str(level["id"])} for row in block.get("not_applied") or [])
    programs = []
    for program in subsidy_programs(config, model["key"]["province"], ctx["sector"], chosen):
        present = [record for _, record in records if any(
            _fullmatch(program["component_name_regex"], comp.get("component_name"))
            for comp in record.get("components") or [])]
        if program["treatment"] == "disclose" and not present:
            continue
        seasons = None
        if program["treatment"] == "first_block_price":
            convention = (ctx["usage_levels"].get("seasons") or {}).get(program["seasons"]) or {}
            seasons = {"id": program["seasons"], "decided": convention.get("decided"),
                       "method": convention.get("method"),
                       "seasons": [{"label": label, "months": value.get("months"),
                                    "first_block_kwh_per_month": value.get("first_block_kwh_per_month")}
                                   for label, value in convention.items() if isinstance(value, dict) and "months" in value]}
        programs.append({"id": program["id"], "name": program["name"], "utility": program.get("utility"),
                         "treatment": program["treatment"],
                         "status": ("applied" if applied_at.get(program["id"]) else
                                    "disclosed" if program["treatment"] == "disclose" else "not_applied"),
                         "applied_at": applied_at.get(program["id"], []),
                         "replaces": (program.get("replaces") or {}).get("text"),
                         "applies_to": (program.get("applies_to") or {}).get("text"),
                         "within_first_block": program.get("within_first_block"), "seasons": seasons,
                         "automatic": program.get("automatic"),
                         **{k: program.get(k) for k in ("quote", "source_url", "location", "evidence", "note", "reason",
                                                        "decided")}})
        if program["treatment"] == "disclose" and not policy["after_subsidy"]:
            skipped.extend({"id": program["id"], "name": program["name"], "utility": program.get("utility"),
                            "reason": program["reason"], "level": None} for _ in present[:1])
    percentage = []
    for entry_id, row in sorted(used.items()):
        entry = entries[entry_id]
        if entry["treatment"] != "subsidy":
            continue
        starts = sorted({item.get("effective_date") for item in row["items"] if item.get("effective_date")})
        ends = sorted({item.get("end_date") for item in row["items"] if item.get("end_date")})
        percentage.append({"id": entry_id, "name": entry.get("name") or row["component"], "utility": row["utility"],
                           "component": row["component"], "rates_percent": sorted(row["rates_percent"]),
                           "effective_date": starts[0] if len(starts) == 1 else starts or None,
                           "end_date": ends[0] if len(ends) == 1 else ends or None,
                           "in_force": any(item.get("reason") == "subsidy" for item in row["items"]),
                           "applied_at": applied_at.get(entry_id, []), "base": (entry.get("base") or {}).get("text"),
                           "limit": entry.get("limit"),
                           **{k: entry.get(k) for k in ("quote", "applicable", "source_url", "location", "note",
                                                        "decided")}})
    model["subsidies"] = {"after_subsidy": policy["after_subsidy"], "reason": policy["reason"],
                          "decided": policy.get("decided"), "tax_basis": BEFORE_TAX_ONLY,
                          "tax_note": config.get("tax_note"), "rule": config.get("rule"),
                          "programs": programs, "percentage_subsidies": percentage,
                          "not_applied": _group_skips(skipped, scope="levels"),
                          "problem": config.get("problem"), "skipped": config.get("skipped") or []}


def _build_model(key: tuple, entries: list[tuple[dict, str, Optional[str]]], *, crosswalk: dict, usage_levels: dict,
                 taxes: dict, as_of: date, zone_policy: str, province_utilities: set[str], input_label: str,
                 block_periods: Optional[list] = None, archetypes: Optional[dict] = None,
                 benchmark_market: Optional[dict] = None, percentage_riders: Optional[list] = None,
                 subsidies: Optional[dict] = None) -> dict:
    """One model: per-utility costs at each usage level, statistics, buckets, energy blocks and method text; for a
    territory also the cost after automatic subsidies (subsidy_policy) and the reviewed percentage riders it applies."""
    province, fuel, sector, structure, band = key
    level_sector = band if sector == "commercial" and band else sector
    raw_levels = (usage_levels.get(fuel) or {}).get(level_sector) if isinstance(usage_levels.get(fuel), dict) else None
    levels = [lv for lv in raw_levels if isinstance(lv, dict) and level_applies(lv, province)] \
        if isinstance(raw_levels, list) else []
    repeated = sorted({str(lv.get("id")) for lv in levels if sum(other.get("id") == lv.get("id") for other in levels) > 1})
    if repeated:
        raise ValueError(f"usage levels {fuel}/{level_sector}: more than one entry {repeated} applies to {province}")
    volume = "kwh"
    if fuel == "gas":
        # Each gas model is evaluated only at the levels of its records' native volume unit (m3 or GJ).
        volume = gas_volume_unit(record for record, _, _ in entries) or "none"
        levels = [lv for lv in levels if lv.get("unit") == volume]
    ctx = _context(province, fuel, structure, level_sector, usage_levels, as_of, block_periods, volume,
                   percentage_riders, subsidies)
    policy = subsidy_policy(subsidies, province, fuel, level_sector)
    required = required_contributors(crosswalk, key)
    required_names = sorted({name for entry in required for name in entry.get("utilities") or []})
    by_utility: dict[str, list[tuple[dict, str, Optional[str]]]] = defaultdict(list)
    for record, zone, rule_id in entries:
        by_utility[record.get("utility_name") or ""].append((record, zone, rule_id))
    exclusions: list[dict] = []
    if volume == "none":
        exclusions.append({"scope": "model", "reason": "gas records do not price one native volume unit (m3 or GJ); "
                                                      "no usage level is evaluated"})
    chosen: dict[str, list[tuple[dict, str, Optional[str]]]] = {}
    for utility, rows in sorted(by_utility.items()):
        rows.sort(key=lambda row: (row[1] != "default", row[0].get("tariff_code") or "", str(row[0].get("id"))))
        keep = rows if zone_policy == "median_of_zones" else [row for row in rows if row[1] == "default"]
        for record, zone, rule_id in rows:
            if (record, zone, rule_id) not in keep:
                exclusions.append({"scope": "record", "utility": utility, "record_id": record.get("id"),
                                   "tariff_code": record.get("tariff_code"), "zone": zone,
                                   "reason": "zone policy default_only: not a default-zone record"})
        if keep:
            chosen[utility] = keep
    preps = {id(record): _prepare(record, ctx) for rows in chosen.values() for record, _, _ in rows}
    # Method 7S-2 (owner decisions 119-123, 2026-11-25): where a market_energy_shapes entry covers the model, the market
    # energy without a stored price is estimated once, before the levels, and added to those records' costs below.
    shape_id, shape = find_market_energy_shape(usage_levels, province, fuel, sector, level_sector)
    estimate = None
    if shape is not None:
        if any(prep["energy_status"] == "market_pending" for prep in preps.values()):
            estimate = _energy_estimate(key, shape_id, shape, benchmark_market or {}, as_of,
                                        archetypes if archetypes is not None else _archetype_context(None),
                                        _band_limits(crosswalk, band))
        else:
            estimate = _no_estimate(shape_id, shape, benchmark_market or {},
                                    "no record of this model has a market energy price without a stored value")
    estimate_price = estimate["price_per_kwh"] if estimate is not None and estimate["available"] else None
    rule_levels = crosswalk_rule_levels(crosswalk)
    electives = elective_class_groups(crosswalk)
    used_ids: set = set()
    estimated_ids: set = set()
    withheld_ids: set = set()
    withheld_missing: dict[Any, list[str]] = {}
    contributing: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    zone_fallbacks: dict[str, list] = defaultdict(list)
    level_inputs: dict[Any, dict] = {}
    variant_uses: list[tuple[Any, str, dict, dict]] = []
    elective_uses: list[tuple[Any, str, dict]] = []
    level_out = []
    for level in levels:
        if fuel == "gas":
            kwh, kw = float(level.get("quantity") or 0.0), None
            usage = {"kwh": None, "kw": None, "quantity": kwh, "unit": volume, "role": level.get("role")}
        else:
            kwh = float(level.get("kwh") or 0.0)
            kw = None if level.get("kw") is None else float(level["kw"])
            usage = {"kwh": kwh, "kw": kw, "role": level.get("role")}
        # Tax eligibility thresholds are in kWh; gas volumes never satisfy or fail a kWh test.
        applied, not_applied = tax_lines(taxes, province, fuel, level_sector, None if fuel == "gas" else kwh, kw, as_of)
        costs, taxed, line_amounts, rows_out = {}, {}, defaultdict(list), []
        level_used, level_fallbacks, zone_inputs, level_variants, level_electives = [], [], {}, [], []
        level_estimated: set = set()
        after_costs, after_problems, after_applied, after_skipped = {}, {}, set(), []
        for utility, rows in chosen.items():
            zone_rows, reasons = [], []
            for record, zone, rule_id in rows:
                limits = rule_levels.get(rule_id)
                if limits is not None and level.get("id") not in limits:
                    reasons.append(f"{record.get('tariff_code')}: crosswalk rule {rule_id} covers only levels "
                                   f"{', '.join(limits)}")
                    continue
                if fuel == "gas":
                    problem = volume_bound_problem(record, kwh, volume, ctx.get("peak_factor"))
                    if problem:
                        reasons.append(f"{record.get('tariff_code')}: {problem}")
                        continue
                elif not record_covers_level(record, kwh, kw):
                    reasons.append(f"{record.get('tariff_code')}: "
                                   f"{record.get('demand_bounds_problem') or 'eligibility does not cover the level'}")
                    continue
                prep = preps[id(record)]
                selection = _select_variants(prep, ctx, level.get("id"), kwh)
                priced = _price(prep, kwh, kw, selection)
                if priced["status"] != "ok":
                    reasons.append(f"{record.get('tariff_code')}: " + "; ".join(priced["reasons"]))
                    continue
                cost, energy_subtotal = priced["cost"], priced["energy_charge_subtotal"]
                estimated = estimate_price is not None and prep["energy_status"] == "market_pending"
                if estimated:
                    # Decision 119: the estimated market energy is part of the cost and of the energy subtotal before
                    # tax, like any energy charge; the delivery-only values stay for the flat benchmark below.
                    cost += estimate_price * kwh
                    energy_subtotal += estimate_price * kwh
                with_tax, amounts = apply_tax_lines(cost, energy_subtotal, applied)
                # The after-subsidy cost uses the same record and level as the cost before subsidies (decision 67).
                after = (_after_subsidy_record(prep, record, ctx, kwh, kw, selection, priced["cost"])
                         if policy and policy["after_subsidy"] else None)
                zone_rows.append((record, zone, cost, with_tax, amounts, energy_subtotal, priced["variants"], after,
                                  priced["cost"], priced["energy_charge_subtotal"], estimated))
            zone_rows, elective_notes = cheapest_elective_rows(zone_rows, electives.get(utility) or [])
            if not zone_rows:
                exclusions.append({"scope": "utility", "utility": utility, "level": level.get("id"),
                                   "reason": " | ".join(reasons) or "no record"})
                continue
            if all(row[1] != "default" for row in zone_rows) and any(zone == "default" for _, zone, _ in rows):
                level_fallbacks.append(utility)
            costs[utility] = statistics.median([row[2] for row in zone_rows])
            taxed[utility] = statistics.median([row[3] for row in zone_rows])
            for index in range(len(applied)):
                line_amounts[index].append(statistics.median([row[4][index] for row in zone_rows]))
            level_used.extend((utility, row[0]) for row in zone_rows)
            zone_inputs[utility] = [(row[8], row[9]) for row in zone_rows]
            level_estimated.update(id(row[0]) for row in zone_rows if row[10])
            row_out = {"utility": utility, "cost_without_tax": round(costs[utility], 2),
                       "cost_with_tax": round(taxed[utility], 2),
                       "records": [row[0].get("id") for row in zone_rows],
                       "zone_costs": [{"record_id": row[0].get("id"), "tariff_code": row[0].get("tariff_code"),
                                       "zone": row[1], "cost_without_tax": round(row[2], 2)}
                                      for row in zone_rows] if len(zone_rows) > 1 else None}
            if any(row[10] for row in zone_rows):
                row_out["estimated_market_energy"] = True
            picks = [(row[0], choice) for row in zone_rows for choice in row[6]]
            if picks:
                row_out["fixed_charge_variants"] = [{"record_id": record.get("id"), "rule": choice["rule"],
                                                     "component": choice["item"]["component"]}
                                                    for record, choice in picks]
                level_variants.extend((utility, record, choice) for record, choice in picks)
            if elective_notes:
                row_out["elective_classes"] = elective_notes
                level_electives.extend((level.get("id"), utility, note) for note in elective_notes)
            if any(row[0].get("interim") for row in zone_rows):
                row_out["interim"] = True  # owner decision 72 (2026-11-24)
            if policy is not None and policy["after_subsidy"]:
                afters = [row[7] for row in zone_rows]
                if all(after["status"] == "ok" for after in afters):
                    after_costs[utility] = statistics.median([after["cost"] for after in afters])
                else:
                    after_problems[utility] = " | ".join(
                        f"{row[0].get('tariff_code') or row[0].get('name')}: " + "; ".join(row[7]["reasons"])
                        for row in zone_rows if row[7]["status"] != "ok")
                row_out["cost_after_subsidy"] = round(after_costs[utility], 2) if utility in after_costs else None
                row_out["after_subsidy_records"] = [
                    {"record_id": row[0].get("id"), "tariff_code": row[0].get("tariff_code"), "zone": row[1],
                     "cost_after_subsidy": None if row[7]["cost"] is None else round(row[7]["cost"], 2),
                     "seasons": row[7]["seasons"], "applied": row[7]["applied"],
                     "not_applied": sorted({skip["id"] for skip in row[7]["not_applied"]}),
                     "reasons": row[7]["reasons"]} for row in zone_rows]
                for row in zone_rows:
                    after_applied.update(row[7]["applied"])
                    after_skipped.extend({**skip, "utility": utility, "record_id": row[0].get("id")}
                                         for skip in row[7]["not_applied"])
            rows_out.append(row_out)
        missing = [name for name in required_names if name not in costs]
        withheld = None
        if missing and costs:
            rules = [e for e in required if set(e.get("utilities") or []) & set(missing)]
            withheld = {"missing_required": missing, "computed_utilities": sorted(costs),
                        "rules": [e.get("id") for e in rules], "reason": " ".join(e.get("reason") or "" for e in rules)}
            withheld_missing[level.get("id")] = missing
            withheld_ids.update(id(record) for _, record in level_used)
            exclusions.append({"scope": "level", "level": level.get("id"),
                               "reason": f"required contributor not computable: {', '.join(missing)}; computed "
                                         f"{', '.join(sorted(costs))} withheld ({withheld['reason']})"})
            costs, taxed, line_amounts, rows_out, zone_inputs = {}, {}, defaultdict(list), [], {}
            after_costs, after_problems = {}, {}
            level_estimated = set()
        else:
            for utility in level_fallbacks:
                zone_fallbacks[utility].append(level.get("id"))
            for utility, record in level_used:
                if id(record) not in used_ids:
                    contributing[utility].append((preps[id(record)], record))
                used_ids.add(id(record))
            estimated_ids.update(level_estimated)
            variant_uses.extend((level.get("id"), utility, record, choice) for utility, record, choice in level_variants)
            elective_uses.extend(level_electives)
        level_inputs[level.get("id")] = {
            "zone_rows": zone_inputs, "applied": applied, "not_applied": not_applied,
            "market_eligible": bool(zone_inputs) and all(
                preps[id(record)]["energy_status"] == "market_pending" for _, record in level_used)}
        stats = summary_stats(costs.values())
        closest = closest_to_median(costs, stats["median"])
        closest_rows = [row for row in rows_out if row["utility"] == closest]
        level_out.append({
            "id": level.get("id"), **usage,
            "without_tax": _money(stats),
            "with_tax": {**_money(summary_stats(taxed.values())),
                         "lines": [{**line, "median_amount": round(statistics.median(line_amounts[i]), 2)
                                    if line_amounts[i] else None} for i, line in enumerate(applied)],
                         "not_applied": not_applied},
            "closest_utility": None if not closest else {
                "utility": closest, "cost_without_tax": round(costs[closest], 2),
                "cost_with_tax": round(taxed[closest], 2),
                "deviation_pct": round((costs[closest] - stats["median"]) / stats["median"] * 100, 2)
                if stats["median"] else None,
                "records": [_record_brief(record, zone, rule_id) for record, zone, rule_id in chosen[closest]
                            if record.get("id") in closest_rows[0]["records"]]},
            "outliers": [{**o, "cost": round(o["cost"], 2)} for o in find_outliers(costs, stats)],
            "utilities": rows_out,
        })
        if withheld:
            level_out[-1]["withheld"] = withheld
        if level_estimated:
            level_out[-1]["market_energy_estimate"] = {"price_per_kwh": estimate_price,
                                                       "cost": round(estimate_price * kwh, 2)}
        if policy is not None:
            level_out[-1]["after_subsidy"] = _after_subsidy_level(policy, costs, after_costs, after_problems,
                                                                  withheld, after_applied, after_skipped)
    if not levels:
        for utility, rows in chosen.items():
            for record, _, _ in rows:
                if (record.get("pair") or {}).get("variant") == "retail":
                    continue
                if not preps[id(record)]["blockers"]:
                    contributing[utility].append((preps[id(record)], record))
                    used_ids.add(id(record))
        missing = [name for name in required_names if name not in contributing]
        if missing and contributing:
            withheld_missing["component buckets"] = missing
            withheld_ids.update(used_ids)
            exclusions.append({"scope": "model", "reason": f"required contributor not computable: {', '.join(missing)}; "
                                                          f"{', '.join(sorted(contributing))} withheld"})
            contributing.clear()
            used_ids.clear()
    for utility, rows in chosen.items():
        for record, zone, _ in rows:
            prep = preps[id(record)]
            if id(record) in used_ids:
                continue
            if record.get("pair") and (not levels or not any(record_covers_level(record, lv.get("kwh"), lv.get("kw"))
                                                             for lv in levels)):
                continue
            if id(record) in withheld_ids:
                reason = ("computable, but withheld: required contributor(s) " + ", ".join(required_names)
                          + " not computable (see level exclusions)")
            elif fuel == "gas" and levels and all(
                    volume_bound_problem(record, float(lv.get("quantity") or 0.0), volume, ctx.get("peak_factor"))
                    for lv in levels):
                reason = "published volume eligibility covers no usage level of this model"
            elif prep["blockers"]:
                reason = "; ".join(prep["blockers"])
            elif levels and not any(record_covers_level(record, lv.get("kwh"), lv.get("kw")) for lv in levels):
                reason = (f"eligibility ({record.get('demand_min_kw')}-{record.get('demand_max_kw')} kW) covers no usage "
                          "level of this model")
            else:
                reason = "not used at any level (see utility exclusions)"
            exclusions.append({"scope": "record", "utility": utility, "record_id": record.get("id"),
                               "tariff_code": record.get("tariff_code"), "zone": zone, "reason": reason})
    component_counts: Counter = Counter()
    component_examples: dict[str, list[str]] = defaultdict(list)
    reference_counts: Counter = Counter()
    reference_examples: dict[str, list[str]] = defaultdict(list)
    conversions: set[str] = set()
    block_ids: set[str] = set()
    statuses: Counter = Counter()
    pending: list[dict] = []
    unestimated = 0
    market_other: list[dict] = []
    chosen_sources = {id(choice["source"]) for _, _, _, choice in variant_uses}
    for _, _, _, choice in variant_uses:
        conversions.update(choice["item"].get("conversions") or [])
    for utility, pairs in sorted(contributing.items()):
        for prep, record in pairs:
            statuses[prep["energy_status"]] += 1
            if prep["market_pending"]:
                pending.append({"utility": utility, "record_id": record.get("id"), "components": prep["market_pending"]})
                unestimated += id(record) not in estimated_ids
            if prep["market_other"]:
                market_other.append({"utility": utility, "record_id": record.get("id"),
                                     "components": prep["market_other"]})
            members = {id(item) for group in prep["variant_groups"] for item, _ in group["members"]}
            for item in prep["items"]:
                if id(item) in chosen_sources:
                    continue
                if item["status"] == "excluded" or id(item) in members:
                    counts, examples = component_counts, component_examples
                    slot = item["reason"] if item["status"] == "excluded" else "variant_not_selected"
                else:
                    conversions.update(item.get("conversions") or [])
                    if item.get("block_period"):
                        block_ids.add(item["block_period"])
                    slot = (item.get("reason") or "").partition(REFERENCE_PREFIX)[2]
                    if not slot:
                        continue
                    counts, examples = reference_counts, reference_examples
                counts[slot] += 1
                short = re.sub(r"\s+-\s+effective until.*$", "", item["component"])[:70]
                if short not in examples[slot] and len(examples[slot]) < 3:
                    examples[slot].append(short)
    for reason, count in component_counts.most_common():
        exclusions.append({"scope": "component", "reason": reason, "text": EXCLUSION_TEXT.get(reason, reason),
                           "count": count, "examples": component_examples[reason]})
    # Decision 119: market energy priced by the estimate for every record without a stored price makes the model
    # market_energy_estimated; any record left unpriced (no estimate, or an input failed) keeps it pending.
    estimated = bool(pending) and not unestimated
    if pending:
        state = "market_energy_estimated" if estimated else "market_energy_pending"
    elif len(contributing) >= 2:
        state = "modeled"
    elif len(contributing) == 1:
        state = "single_source"
    else:
        state = "not_computable"
    if not statuses:
        energy = "none"
    elif len(statuses) == 1:
        energy = next(iter(statuses))
    else:
        energy = "market_pending" if statuses.get("market_pending") else "mixed"
    if energy == "market_pending" and estimated:
        energy = "market_estimated"
    cost_basis = {"included": "delivery_and_energy", "market_pending": "delivery_only_market_energy_pending",
                  "market_estimated": "delivery_and_estimated_market_energy",
                  "absent": "delivery_only_no_energy_component"}.get(energy, energy)
    picks_by_record: dict[int, dict[Any, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for level_id, _, record, choice in variant_uses:
        picks_by_record[id(record)][level_id].append(choice)
    stable_variants = {key: [choice["item"] for choice in next(iter(by_level.values()))]
                       for key, by_level in picks_by_record.items()
                       if len({tuple(sorted(id(c["source"]) for c in picks)) for picks in by_level.values()}) == 1}
    bucket_rows = {utility: [_record_buckets(prep, stable_variants.get(id(record))) for prep, record in pairs]
                   for utility, pairs in contributing.items()}
    warnings = []
    entry = ctx.get("shares_entry") or {}
    period_end = _PERIOD_END_RE.search(entry.get("period") or "")
    if period_end:
        month = _MONTHS.get(period_end.group(1).lower()[:3])
        if month and as_of > date(int(period_end.group(3)), month, int(period_end.group(2))):
            warnings.append(f"TOU shares {ctx.get('shares_id')} cover {entry.get('period')}; the as-of date is later")
    if energy == "mixed":
        warnings.append("contributing records differ in energy basis: " + json.dumps(dict(statuses), sort_keys=True))
    for utility, level_ids in sorted(zone_fallbacks.items()):
        warnings.append(f"{utility}: the default-zone record is not computable at {', '.join(map(str, level_ids))}; "
                        "only other-zone records contribute (see exclusions)")
    singular, plural = UTILITY_NOUNS.get((province, fuel), DEFAULT_NOUNS)
    model = {
        "id": key_label(key),
        "key": {"province": province, "fuel": fuel, "sector": sector, "structure": structure, "size_band": band},
        "label": _model_label(key, crosswalk),
        "state": state,
        "provenance": "modeled",
        "cost_basis": cost_basis,
        "energy": {"status": energy, "records_by_status": dict(sorted(statuses.items())), "market_pending": pending,
                   "market_indexed_excluded": market_other},
        "coverage": {
            "utilities_in_province": len(province_utilities),
            "utilities_mapped": len(by_utility),
            "utilities_contributing": len(contributing),
            "contributing_utilities": sorted(contributing),
            "missing_utilities": sorted(province_utilities - set(by_utility)),
            "multi_zone_utilities": sorted(u for u, rows in chosen.items() if len(rows) > 1),
            "records_mapped": len(entries),
            "records_used": len(used_ids),
            "zone_policy": zone_policy,
            "effective_dates": sorted({r.get("effective_date") for pairs in contributing.values()
                                       for _, r in pairs if r.get("effective_date")}),
            "contributor_noun": {"singular": singular, "plural": plural},
        },
        "buckets": _bucket_stats(bucket_rows),
        "levels": level_out,
        "tou": _energy_block(contributing, ctx, "tou"),
        "tiers": _energy_block(contributing, ctx, "tiers"),
        "utilities": [{"utility": utility, "records": [_record_brief(r, z, rid) for r, z, rid in chosen[utility]]}
                      for utility in sorted(chosen)],
        "reference_customer": [{"id": rid, "components": count, "examples": reference_examples[rid]}
                               for rid, count in sorted(reference_counts.items())],
        "exclusions": exclusions,
        "warnings": warnings,
        "generated_from": {"as_of": as_of.isoformat(), "input": input_label},
    }
    if block_ids:
        model["block_periods"] = [{k: e.get(k) for k in ("id", "utility", "threshold_period", "quote", "source_url",
                                                         "location")}
                                  for e in ctx["block_periods"] if e.get("id") in block_ids]
    if variant_uses:
        rules = {rule["id"]: rule for rule in ctx["variant_rules"]}
        summary: dict[str, dict] = {}
        for level_id, utility, record, choice in variant_uses:
            rule = rules.get(choice["rule"]) or {}
            row = summary.setdefault(choice["rule"], {"id": choice["rule"], "reference": rule.get("reference"),
                                                      "decided": rule.get("decided"), "levels": [], "components": [],
                                                      "utilities": []})
            for field, value in (("levels", str(level_id)), ("components", choice["item"]["component"]),
                                 ("utilities", utility)):
                if value not in row[field]:
                    row[field].append(value)
        model["fixed_charge_variants"] = [summary[rule_id] for rule_id in sorted(summary)]
    if elective_uses:
        configs = {group.get("id"): group for groups in electives.values() for group in groups}
        chosen_by_group: dict[str, dict] = {}
        for level_id, utility, note in elective_uses:
            group = configs.get(note["group"]) or {}
            entry = chosen_by_group.setdefault(note["group"], {
                "id": note["group"], "utility": utility, "tariff_codes": list(group.get("tariff_codes") or []),
                "rule": group.get("rule"), "decided": group.get("decided"), "chosen": {}})
            entry["chosen"][str(level_id)] = note["chosen"]
        model["elective_classes"] = [chosen_by_group[key] for key in sorted(chosen_by_group)]
    if ctx.get("peak_factor") and levels:
        model["peak_month_factor"] = {k: ctx["peak_factor"].get(k) for k in ("id", "factor", "decided", "basis")}
    if required:
        model["required_contributors"] = [
            {"id": e.get("id"), "utilities": list(e.get("utilities") or []), "reason": e.get("reason"),
             "decided": e.get("decided"),
             "withheld_at": [str(level_id) for level_id, names in withheld_missing.items()
                             if set(names) & set(e.get("utilities") or [])]} for e in required]
    _territorial_fields(model, chosen, preps, crosswalk, ctx, policy, level_out)
    if estimate is not None:
        if estimate["available"]:
            if province == "ON":
                estimate["loss_factors"] = _loss_factor_summary(contributing)
            estimate["assumptions"] = _estimate_assumptions(key, estimate, (benchmark_market or {}).get("document"),
                                                            singular)
        model["energy_estimate"] = estimate
    has_pairs = any(record.get("pair") for rows in chosen.values() for record, _, _ in rows)
    model["method"] = _method_text(model, key, levels, component_counts, component_examples, conversions, zone_policy,
                                   pair_config(crosswalk).get("method_note") if has_pairs else None)
    configs = usage_levels.get("market_benchmarks") or {}
    # Decision 123: the flat (same use every hour) benchmark stays for the estimate's note and Rate History's line.
    if (province in ("ON", "AB") and fuel == "electricity" and sector == "commercial"
            and model["state"] in ("market_energy_pending", "market_energy_estimated") and province in configs):
        model["market_benchmark"] = _benchmark(model, benchmark_market or {}, level_inputs, configs[province], as_of)
    return model


def _model_order(key: tuple, crosswalk: dict) -> tuple:
    bands = list(((crosswalk.get("vocabulary") or {}).get("size_bands") or {}).keys())
    structures = list(((crosswalk.get("vocabulary") or {}).get("structures") or {}).keys())
    province, fuel, sector, structure, band = key
    return (province or "", fuel or "", sector != "residential", bands.index(band) if band in bands else -1,
            structures.index(structure) if structure in structures else len(structures), str(structure))


_CONFIDENCE_ORDER = ("high", "medium", "low", "unverified")


def pair_config(crosswalk: dict) -> dict:
    """The crosswalk 'pairs' section (wires + retail units), or {}."""
    pairs = (crosswalk or {}).get("pairs")
    return pairs if isinstance(pairs, dict) else {}


def _pair_composite(unit: dict, wires: dict, retail: Optional[dict], variant: str, cfg: dict,
                    blocker: Optional[str] = None) -> dict:
    """One wires + retail (variant 'retail') or wires-only (variant 'market') record counted as the unit."""
    parts = [("wires", wires)] + ([("retail", retail)] if retail is not None and variant == "retail" else [])
    components = [{**comp, "pair_part": part, "source_url": comp.get("source_url") or rec.get("source_url")}
                  for part, rec in parts for comp in rec.get("components") or []]
    threshold = cfg.get("retail_below_annual_kwh")
    pair = {"unit": unit.get("id"), "label": unit.get("label"), "variant": variant, "wires_record_id": wires.get("id"),
            "retail_record_id": retail.get("id") if retail is not None and variant == "retail" else None}
    if variant == "retail":
        pair["below_annual_kwh"] = threshold
        name = f"{wires.get('name')} + {retail.get('name')}" if retail is not None else wires.get("name")
        record_id = f"{wires.get('id')}+{retail.get('id')}" if retail is not None else f"{wires.get('id')}+none"
        code = f"{wires.get('tariff_code')}+{retail.get('tariff_code')}" if retail is not None else wires.get("tariff_code")
    else:
        pair["from_annual_kwh"] = threshold
        market = cfg.get("market_energy") or {}
        components.append({"component_type": "energy", "component_name": market.get("component_name"),
                           "charge_value": None, "charge_unit": "$/kWh", "market_reference": market.get("market_reference"),
                           "market_source_url": market.get("market_source_url"), "pair_part": "market",
                           "notes": "Provenance: modeled. " + (market.get("note") or "")})
        name, record_id, code = wires.get("name"), wires.get("id"), wires.get("tariff_code")
    if blocker:
        pair["blocker"] = blocker
    records = [rec for _, rec in parts]
    ranks = [_CONFIDENCE_ORDER.index(r.get("confidence")) for r in records if r.get("confidence") in _CONFIDENCE_ORDER]
    return {**wires, "id": record_id, "utility_name": unit.get("label"), "name": name, "tariff_code": code,
            "effective_date": max((r.get("effective_date") or "") for r in records) or None,
            "confidence": _CONFIDENCE_ORDER[max(ranks)] if ranks else wires.get("confidence"),
            "retail_source_url": retail.get("source_url") if retail is not None and variant == "retail" else None,
            "components": components, "pair": pair}


def compose_pairs(live: Iterable[dict], crosswalk: dict) -> tuple[dict[int, list[dict]], dict[str, str], set[str]]:
    """Pair variants per paired wires record (keyed by id(record)), wires utility -> unit label and retail utilities.

    A configured wires class gets a retail variant (wires + Rate of Last Resort record) used below the annual-use
    threshold and a market variant (wires + value-less market energy) used at or above it. A wires record without a
    configured class, or whose retail record is missing, gets variants that carry the reason as a blocker."""
    cfg = pair_config(crosswalk)
    live = list(live)
    by_code = {(r.get("utility_name"), r.get("tariff_code")): r for r in live}
    variants: dict[int, list[dict]] = {}
    wires_units: dict[str, str] = {}
    retail_utilities: set[str] = set()
    for unit in cfg.get("units") or []:
        if not isinstance(unit, dict) or not unit.get("wires") or not unit.get("label"):
            continue
        wires_units[unit["wires"]] = unit["label"]
        retail_utilities.add(unit.get("retail"))
        classes = {cls.get("wires_code"): cls for cls in unit.get("classes") or [] if isinstance(cls, dict)}
        for record in live:
            if record.get("utility_name") != unit["wires"]:
                continue
            cls = classes.get(record.get("tariff_code"))
            if cls is None:
                blocker = f"wires class {record.get('tariff_code')} has no retail pairing in crosswalk pairs"
                retail = None
            elif not cls.get("retail_code"):
                blocker, retail = f"no Rate of Last Resort record for {record.get('tariff_code')} sites: " \
                                  f"{cls.get('retail_missing') or 'not configured'}", None
            else:
                retail = by_code.get((unit.get("retail"), cls["retail_code"]))
                blocker = None if retail is not None else \
                    f"Rate of Last Resort record {unit.get('retail')} {cls['retail_code']} is not live"
            market_blocker = f"wires class {record.get('tariff_code')} has no retail pairing in crosswalk pairs" \
                if cls is None else None
            variants[id(record)] = [_pair_composite(unit, record, retail, "retail", cfg, blocker),
                                    _pair_composite(unit, record, None, "market", cfg, market_blocker)]
    return variants, wires_units, retail_utilities


def apply_usage_bounds(record: dict, crosswalk: dict) -> dict:
    """Copy of a record with reviewed eligibility bounds from crosswalk usage_bounds; the record itself when no entry
    matches.

    Electricity: annual-use kWh bounds when the record publishes them only in its eligibility text (a record with
    usage bounds is returned unchanged). Gas (entries with a 'unit', method 7D-2): the first entry for the utility,
    tariff code and (when given) customer class becomes the record's 'volume_bounds', quoting the published wording
    that decides whether a bound itself is included (stored bounds carry no inclusivity)."""
    entries = [entry for entry in (crosswalk or {}).get("usage_bounds") or [] if isinstance(entry, dict)
               and entry.get("utility") == record.get("utility_name")
               and _fullmatch(entry.get("tariff_code_regex"), record.get("tariff_code"))]
    if record.get("utility_type") == "gas":
        for entry in entries:
            if entry.get("unit") in GAS_VOLUME_PRICES and entry.get("customer_class", record.get("customer_class")) \
                    == record.get("customer_class"):
                return {**record, "volume_bounds": {k: entry.get(k) for k in (
                    "id", "unit", "basis", "min", "min_inclusive", "max", "max_inclusive", "quote")}}
        return record
    demand = next((entry for entry in (crosswalk or {}).get("demand_bounds") or [] if isinstance(entry, dict)
                   and entry.get("utility") == record.get("utility_name")
                   and _fullmatch(entry.get("tariff_code_regex"), record.get("tariff_code"))), None)
    if demand is not None:
        # Reviewed published inclusivity of a kW bound (FortisBC Electric Rate 20 is "not more than 40 kW"); the
        # engine's default is [min, max). Different numbers mean the class limits changed since the review.
        stored = (_kw(record.get("demand_min_kw"), 0.0), _kw(record.get("demand_max_kw"), math.inf))
        wanted = (_kw(demand.get("min_kw"), 0.0), _kw(demand.get("max_kw"), math.inf))
        record = {**record, "demand_bounds_entry": demand.get("id")}
        if stored != wanted:
            record["demand_bounds_problem"] = (f"reviewed demand_bounds {demand.get('id')} ({wanted[0]:g}-{wanted[1]:g} "
                                               f"kW) differs from the stored eligibility ({stored[0]:g}-{stored[1]:g} "
                                               "kW); the entry needs a new review")
        else:
            record["demand_inclusive"] = [bool(demand.get("min_inclusive", True)),
                                          bool(demand.get("max_inclusive", False))]
    if record.get("usage_min") is not None or record.get("usage_max") is not None:
        return record
    for entry in entries:
        if "unit" not in entry:
            return {**record, "usage_min": entry.get("min_annual_kwh"), "usage_max": entry.get("max_annual_kwh"),
                    "usage_unit": "kWh/year", "usage_bounds_entry": entry.get("id")}
    return record


def _stored_volume_bounds(record: dict) -> tuple[Optional[str], Optional[float], Optional[float]]:
    """(volume unit, min, max) of a gas record's stored annual bounds; unit None when it stores none, '?' when its
    bounds are in a unit other than m3 or GJ per year."""
    lo, hi = record.get("usage_min"), record.get("usage_max")
    if lo is None and hi is None:
        return None, None, None
    text = re.sub(r"\s+", " ", (record.get("usage_unit") or "").strip().lower())
    unit = next((track for track, units in GAS_ANNUAL_UNITS.items() if text in units), "?")
    return unit, None if lo is None else float(lo), None if hi is None else float(hi)


def volume_bound_problem(record: dict, quantity: float, unit: str,
                         peak_factor: Optional[dict] = None) -> Optional[str]:
    """Why a gas record's published volume eligibility excludes a level of ``quantity`` (monthly, in the model's
    ``unit``); None when the class serves it (method 7D-2, owner decision 16: each utility is priced on the class whose
    published limits contain 12 x the level).

    A reviewed crosswalk usage_bounds entry decides ('volume_bounds' from apply_usage_bounds): annual bounds test 12 x
    the level; 'peak_month' bounds test the level x the peak_month_factors entry (Liberty, decision 17). An annual
    entry whose numbers differ from the stored bounds fails closed (the class limits changed since the review).
    Without an entry, stored annual bounds apply, and a level exactly on one of them is not computable because the
    stored record does not say whether the bound is included. A record without bounds serves any volume."""
    label = VOLUME_LABELS.get(unit, unit)
    stored_unit, lo, hi = _stored_volume_bounds(record)
    bounds = record.get("volume_bounds")
    if bounds:
        if bounds.get("unit") != unit:
            return f"reviewed usage_bounds {bounds.get('id')} is in {bounds.get('unit')}, not the model's {label}"
        if bounds.get("basis") == "peak_month":
            if not peak_factor:
                return f"the class follows the monthly peak ({bounds.get('id')}) but no peak_month_factors entry applies"
            volume = float(quantity) * float(peak_factor["factor"])
            what = f"peak month {volume:,.2f} {label} ({float(peak_factor['factor']):g} x the level, {peak_factor['id']})"
        else:
            wanted = (None if bounds.get("min") is None else float(bounds["min"]),
                      None if bounds.get("max") is None else float(bounds["max"]))
            if stored_unit is not None and (stored_unit, lo, hi) != (unit, *wanted):
                return (f"reviewed usage_bounds {bounds.get('id')} ({_bounds_text(bounds, unit)}) differs from the stored "
                        f"eligibility ({lo}-{hi} {record.get('usage_unit')}); the entry needs a new review")
            volume = float(quantity) * 12
            what = f"annual volume {volume:,.0f} {label}"
        if not _within(volume, bounds):
            return f"{what} is outside the class eligibility ({_bounds_text(bounds, unit)}: \"{bounds.get('quote')}\")"
        return None
    if stored_unit is None:
        return None
    if stored_unit != unit:
        return f"stored eligibility in {record.get('usage_unit')!r} cannot be compared with {label} levels"
    annual = float(quantity) * 12
    if annual in (lo, hi):
        return (f"annual volume {annual:,.0f} {label} is on a stored class bound, and no reviewed usage_bounds entry "
                "says whether the bound is included")
    if (lo is not None and annual < lo) or (hi is not None and annual > hi):
        return f"annual volume {annual:,.0f} {label} is outside the stored eligibility ({lo}-{hi} {record.get('usage_unit')})"
    return None


def label_interim(record: dict, crosswalk: dict) -> dict:
    """Copy of a record labelled with the id of the crosswalk interim_rates entry that applies to it (owner decision 72,
    2026-11-24); the record itself when none does."""
    entry = interim_entry(record, [e for e in (crosswalk or {}).get("interim_rates") or [] if isinstance(e, dict)])
    return {**record, "interim": entry["id"]} if entry is not None and entry.get("id") else record


def build_models(rates: Union[list[dict], dict], crosswalk: dict, usage_levels: dict, taxes: dict,
                 provinces: Optional[Iterable[str]] = ("ON",), as_of: Union[date, str, None] = None,
                 zone_policy: str = "median_of_zones", input_label: str = "site/data/rates.json",
                 fuels: Optional[Iterable[str]] = MODEL_FUELS, block_periods: Any = _DEFAULT,
                 market_document: Any = _DEFAULT, market_documents: Any = _DEFAULT,
                 percentage_riders: Any = _DEFAULT, subsidies: Any = _DEFAULT, archetypes: Any = _DEFAULT) -> dict:
    """Representative models for every crosswalk model key of the given provinces and fuels (Phases 7B/7C, 7T).

    ``block_periods``: a block_periods document or entry list (default data/models/block_periods.json; a missing file
    means no entries). ``market_document``: observed Ontario market history for the Ontario benchmark and estimated
    market energy (default site/data/market_pricing_ontario.json; None or an unusable document makes them unavailable,
    never the build). ``market_documents`` optionally supplies province-keyed observed histories (ON, AB) instead; with
    only ``market_document`` given, Alberta has none. Explicit None values disable that province's history without
    reading a live file. ``archetypes``: the simulated BTAP runs whose general load shape prices the estimated market
    energy (method 7S-2; pipeline.archetype_profiles; default the repository's runs, read only when a market-pending
    model needs them; None disables the estimate, so those models stay market_energy_pending).
    ``percentage_riders`` and ``subsidies``: the reviewed percentage_riders and subsidies documents (defaults
    data/models/percentage_riders.json and data/models/subsidies.json; a missing file leaves territorial percentage
    riders not computable and publishes no after-subsidy cost)."""
    if zone_policy not in ZONE_POLICIES:
        raise ValueError(f"zone_policy must be one of {ZONE_POLICIES}")
    as_of_date = _as_of(as_of)
    periods = load_block_periods() if block_periods is _DEFAULT else block_periods_config(block_periods)
    riders = load_percentage_riders() if percentage_riders is _DEFAULT else percentage_riders_config(percentage_riders)
    subsidy_cfg = load_subsidies() if subsidies is _DEFAULT else subsidies_config(subsidies)
    rows = rates.get("records", []) if isinstance(rates, dict) else list(rates)
    wanted = None if provinces is None else {str(p).upper() for p in provinces}
    wanted_fuels = None if fuels is None else {str(f) for f in fuels}
    live = [label_interim(apply_usage_bounds(r, crosswalk), crosswalk) for r in latest_live_records(rows)
            if (wanted is None or r.get("province") in wanted)
            and (wanted_fuels is None or r.get("utility_type") in wanted_fuels)]
    variants, wires_units, retail_utilities = compose_pairs(live, crosswalk)
    shared = shared_rate_book_units(crosswalk)
    groups: dict[tuple, list] = defaultdict(list)
    withheld_gas: set[tuple] = set()
    province_utilities: dict[tuple, set[str]] = defaultdict(set)
    counted: list[tuple[tuple, str, str]] = []
    market_reference_only: dict[str, bool] = {}
    for record in live:
        name = record.get("utility_name") or ""
        outcome = match_record(record, crosswalk)
        market_reference_only[name] = (market_reference_only.get(name, True)
                                       and outcome.get("exclude") == "market_reference_only")
        # A city that publishes both its wires tariff and its Rate of Last Resort is one unit, not a retail part; the
        # utilities of a shared rate book count once (owner decision 66: the joint Yukon rate book).
        if name not in retail_utilities or name in wires_units:
            counted.append(((record.get("province"), record.get("utility_type")), name,
                            wires_units.get(name) or shared.get(name, name)))
        for key in model_keys(outcome):
            if key[1] == "gas" and key[2] not in GAS_MODEL_SECTORS:
                withheld_gas.add(key)
                continue
            for row in variants.get(id(record), [record]):
                groups[key].append((row, outcome.get("zone") or "default", outcome.get("rule_id")))
    # A market operator whose only records are value-less wholesale price references (AESO) sells nothing to the
    # model's customers, so it is not counted as a missing contributor (owner decision 2026-11-20).
    for province_fuel, name, unit in counted:
        if not market_reference_only.get(name):
            province_utilities[province_fuel].add(unit)
    if market_documents is not _DEFAULT and not isinstance(market_documents, dict):
        raise ValueError("market_documents must map province codes to market documents or None")
    archetype_ctx = _archetype_context(archetypes)
    benchmarks = {}
    for province in ("ON", "AB"):
        if wanted is not None and province not in wanted:
            continue
        if market_documents is not _DEFAULT:
            benchmarks[province] = _market_context(market_documents.get(province))
        elif province == "ON":
            benchmarks[province] = _market_context(market_document)
        elif market_document is not _DEFAULT:
            benchmarks[province] = _market_context(None)
        else:
            path = MARKET_PATH.with_name("market_pricing_alberta.json")
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                logger.warning("Alberta benchmark history unavailable: %s", exc)
                benchmarks[province] = {"document": None, "problem":
                                       f"Alberta market history file is missing or unreadable ({type(exc).__name__})."}
            else:
                benchmarks[province] = _market_context(document)
    models = [_build_model(key, groups[key], crosswalk=crosswalk, usage_levels=usage_levels, taxes=taxes,
                           as_of=as_of_date, zone_policy=zone_policy,
                           province_utilities=province_utilities[(key[0], key[1])], input_label=input_label,
                           block_periods=periods["entries"], archetypes=archetype_ctx,
                           benchmark_market=benchmarks.get(key[0]),
                           percentage_riders=riders["entries"], subsidies=subsidy_cfg)
              for key in sorted(groups, key=lambda k: _model_order(k, crosswalk))]
    shapes_used = {k: v for k, v in (usage_levels.get("market_energy_shapes") or {}).items()
                   if isinstance(v, dict) and (wanted is None or wanted & set(
                       (v.get("applies_to") or {}).get("provinces") or []))}
    created = [str(r["created_at"]) for r in live if r.get("created_at")]
    shares = {k: {"applies_to": v.get("applies_to"), "shares": v.get("shares"), "period": v.get("period"),
                  "source_url": (v.get("source") or {}).get("url")}
              for k, v in (usage_levels.get("tou_shares") or {}).items() if isinstance(v, dict) and "applies_to" in v}
    return {
        "version": 1,
        "method_version": METHOD_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of": as_of_date.isoformat(),
        "input": {"source": input_label, "records_considered": len(live),
                  "provinces": sorted(wanted) if wanted is not None else None,
                  "fuels": sorted(wanted_fuels) if wanted_fuels is not None else None,
                  "rates_generated_at": rates.get("generated_at") if isinstance(rates, dict) else None,
                  "latest_record_created_at": max(created) if created else None,
                  "withheld_gas_models": {
                      "models": sorted(key_label(k) for k in withheld_gas),
                      "reason": "Gas models cover residential and commercial general service (owner decisions "
                                "2026-11-04 and 2026-11-20); any other gas sector is withheld. Contract-demand, "
                                "interruptible, seasonal and peaking classes are crosswalk exclusions "
                                "(gas_models_phase_7d) until their own decision."}},
        "assumptions": {
            "usage_levels": {fuel: usage_levels.get(fuel) for fuel in ("electricity", "gas") if fuel in usage_levels},
            "usage_levels_basis": usage_levels.get("basis"),
            "days_per_month": float(usage_levels.get("days_per_month") or DEFAULT_DAYS_PER_MONTH),
            "power_factor_for_kva": float(usage_levels.get("power_factor_for_kva") or DEFAULT_POWER_FACTOR),
            "tou_shares": shares,
            "seasons": usage_levels.get("seasons"),
            "zone_policy": zone_policy,
            "zone_policy_text": ZONE_POLICY_TEXT[zone_policy],
            "statistics": "Per-utility cost at each level, then median, p25/p75 (statistics.quantiles, method "
                          "'inclusive'), min and max across utilities; buckets are per-utility normalized rates.",
            "closest_utility": "Utility whose cost without tax is nearest the median; ties alphabetical.",
            "outliers": {"pct_from_median": OUTLIER_PCT, "iqr_factor": OUTLIER_IQR_FACTOR,
                         "min_utilities": OUTLIER_MIN_N, "basis": "cost without tax"},
            "component_rules": list(COMPONENT_RULES),
            "reference_customer_basis": usage_levels.get("reference_customer_basis"),
            "reference_customer": [{k: entry.get(k) for k in ("id", "province", "fuel", "sectors", "exclusion", "match",
                                                              "annual_volume", "reason", "source")}
                                   for entry in usage_levels.get("reference_customer") or []
                                   if isinstance(entry, dict) and (wanted is None or entry.get("province") in wanted)],
            "fixed_charge_variants_basis": usage_levels.get("fixed_charge_variants_basis"),
            "fixed_charge_variants": [{k: entry.get(k) for k in ("id", "fuel", "province", "utility", "sectors", "levels",
                                                                 "peak_month", "select", "reference", "match", "decided")}
                                      for entry in usage_levels.get("fixed_charge_variants") or []
                                      if isinstance(entry, dict)],
            "peak_month_factors": [{k: entry.get(k) for k in ("id", "province", "fuel", "sectors", "factor", "decided",
                                                              "basis", "sources")}
                                   for entry in usage_levels.get("peak_month_factors") or []
                                   if isinstance(entry, dict) and (wanted is None or entry.get("province") in wanted)],
            "elective_classes": [e for e in crosswalk.get("elective_classes") or [] if isinstance(e, dict)],
            "buckets": dict(BUCKET_TEXT),
            "fuels": ("Electricity and natural gas. Gas (Phase 7D, owner decisions 2026-11-04 and 2026-11-20) is default "
                      "utility supply priced in each utility's native unit (m3 or GJ, never converted): residential, "
                      "and commercial general service for small and mid-size buildings, each utility on the class "
                      "whose published limits contain the level. Contract-demand, interruptible, seasonal and peaking "
                      "gas classes are left out until their own decision.")
            if wanted_fuels is None or "gas" in wanted_fuels else
            "Electricity only in this build; gas models are Phase 7D.",
            "pairs": {k: pair_config(crosswalk).get(k) for k in ("basis", "province", "fuel", "retail_below_annual_kwh",
                                                                 "retail_rule", "market_energy", "units")}
            if pair_config(crosswalk) and (wanted is None or pair_config(crosswalk).get("province") in wanted) else None,
            "block_periods": {
                "source": "data/models/block_periods.json" if block_periods is _DEFAULT else "argument",
                "version": periods.get("version"), "status": periods.get("status"), "problem": periods.get("problem"),
                "rule": "A block threshold published in bare kWh (no period) uses the first matching reviewed entry "
                        "(utility; tariff_code, tariff_code_regex or name_regex; optional component_name_regex on a "
                        "block component): month as published, two_months / 2, day x days per month; a null period "
                        "or no entry is not computable.",
                "entries": [{k: e.get(k) for k in ("id", "utility", "match", "component_name_regex", "threshold_period",
                                                   "quote", "source_url", "location")} for e in periods["entries"]],
                "skipped": periods.get("skipped")},
            "required_contributors": [e for e in crosswalk.get("required_contributors") or [] if isinstance(e, dict)
                                      and (wanted is None or e.get("province") in wanted)],
            # Method 7S-2 inputs (owner decisions 119-123): the shape settings, what was read from the simulated
            # buildings (with a fingerprint of their values) and the market files; model monitoring fingerprints them.
            "market_energy_shapes": {
                "profiles": shapes_used,
                "archetypes": _archetype_summary(archetype_ctx),
                "market_files": {province: context.get("file") for province, context in sorted(benchmarks.items())}},
            "usage_bounds": [e for e in crosswalk.get("usage_bounds") or [] if isinstance(e, dict)],
            "demand_bounds": [e for e in crosswalk.get("demand_bounds") or [] if isinstance(e, dict)],
            "taxes": {"as_of": taxes.get("as_of"), "rule": "Lines from data/models/taxes.json for province, fuel and "
                      "sector, in effect at the as-of date; eligibility thresholds use the level's kW and kWh x 12 "
                      "(either test when both are set); amount = rate x base; never compounded; rebates subtracted. "
                      "Territorial costs after subsidies are before tax only (owner decision 74, 2026-11-24)."},
            # Method 7T-1 inputs (owner decisions 64-75, 2026-11-24).
            "percentage_riders": {
                "source": "data/models/percentage_riders.json" if percentage_riders is _DEFAULT else "argument",
                "version": riders.get("version"), "status": riders.get("status"), "problem": riders.get("problem"),
                "rule": riders.get("rule"), "review_scope": list(TERRITORIES),
                "entries": riders["entries"], "skipped": riders.get("skipped")},
            "subsidies": {
                "source": "data/models/subsidies.json" if subsidies is _DEFAULT else "argument",
                "version": subsidy_cfg.get("version"), "status": subsidy_cfg.get("status"),
                "problem": subsidy_cfg.get("problem"), "rule": subsidy_cfg.get("rule"),
                "tax_note": subsidy_cfg.get("tax_note"), "jurisdictions": subsidy_cfg.get("jurisdictions"),
                "programs": subsidy_cfg.get("programs"), "skipped": subsidy_cfg.get("skipped")},
            "interim_rates": [e for e in crosswalk.get("interim_rates") or [] if isinstance(e, dict)],
            "shared_rate_books": [e for e in crosswalk.get("shared_rate_books") or [] if isinstance(e, dict)],
        },
        "models": models,
        "coverage_report": coverage_report(rows, crosswalk),
    }


def write_models(path: PathLike, **kwargs: Any) -> dict:
    """Build the models (missing inputs load from their default paths) and write them as JSON."""
    rates = kwargs.pop("rates", None)
    crosswalk = kwargs.pop("crosswalk", None)
    usage_levels = kwargs.pop("usage_levels", None)
    taxes = kwargs.pop("taxes", None)
    result = build_models(load_rates() if rates is None else rates, crosswalk or load_crosswalk(),
                          usage_levels or load_usage_levels(), taxes or load_taxes(), **kwargs)
    target = Path(path or ROOT / "site" / "data" / "representative_models.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(result, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n",
                   encoding="utf-8")
    os.replace(tmp, target)
    return result


def format_models(result: dict) -> str:
    """Short plain-text summary of built models: per level n, medians without/with tax, range, closest, outliers."""
    lines = [f"Representative models {result['method_version']} as of {result['as_of']} "
             f"(zone policy {result['assumptions']['zone_policy']}; {result['input']['records_considered']} records)"]
    for model in result["models"]:
        cov = model["coverage"]
        lines.append(f"{model['id']} [{model['state']}; {model['cost_basis']}] "
                     f"{cov['utilities_contributing']}/{cov['utilities_mapped']} utilities")
        for level in model["levels"]:
            wo, wt, closest = level["without_tax"], level["with_tax"], level["closest_utility"] or {}
            outliers = ", ".join(f"{o['utility']} {o['deviation_pct']:+.1f}%" for o in level["outliers"])
            lines.append(f"  {level['id']:8} n={wo['n']:<3} median {_fmt_money(wo['median'])} / with tax "
                         f"{_fmt_money(wt['median'])}  range {_fmt_money(wo['min'])}-{_fmt_money(wo['max'])}  "
                         f"closest {closest.get('utility')}" + (f"  outliers: {outliers}" if outliers else ""))
            estimate = level.get("market_energy_estimate")
            if estimate:
                lines.append(f"           includes estimated market energy ${estimate['price_per_kwh']:.6f}/kWh "
                             f"(${estimate['cost']:,.2f}/month; method 7S-2)")
            after = level.get("after_subsidy")
            if after and after.get("available"):
                lines.append(f"           after automatic subsidies (before tax only): median "
                             f"{_fmt_money(after['without_tax']['median'])} (n={after['without_tax']['n']}); "
                             f"applied {', '.join(after['applied']) or 'none'}")
            elif after:
                lines.append(f"           after subsidies: not shown ({after.get('reason')})")
        info = model.get("energy_estimate")
        if info and not info["available"] and info.get("input_problem"):
            lines.append(f"  estimated market energy unavailable (market energy pending): {info['reason']}")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    """CLI: --coverage (Phase 7A) and/or --build [--output PATH] [--zone-policy ...] (Phase 7B)."""
    parser = argparse.ArgumentParser(description="Representative models: crosswalk coverage (7A) and build (7B).")
    parser.add_argument("--coverage", action="store_true", help="print crosswalk coverage of the latest live records")
    parser.add_argument("--build", action="store_true", help="build the representative models and print a summary")
    parser.add_argument("--rates", default=str(RATES_PATH), help="export (list) or fixture ({'records': [...]}) JSON")
    parser.add_argument("--crosswalk", default=str(CROSSWALK_PATH))
    parser.add_argument("--usage-levels", default=str(USAGE_LEVELS_PATH))
    parser.add_argument("--taxes", default=str(TAXES_PATH))
    parser.add_argument("--output", default=None, help="write the models JSON to this path (default: summary only)")
    parser.add_argument("--zone-policy", choices=ZONE_POLICIES, default="median_of_zones")
    parser.add_argument("--province", action="append",
                        help="province code, repeatable (default: the export's MODEL_PROVINCES)")
    parser.add_argument("--as-of", default=None, help="YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--generation-receipt", type=Path, help="write an explicit model refresh outcome for CI")
    args = parser.parse_args(argv)
    if args.generation_receipt and not (args.build and args.output):
        parser.error("--generation-receipt requires --build and --output")
    if not (args.coverage or args.build):
        parser.print_help()
        return 0
    monitor, previous = None, {}
    if args.generation_receipt:
        from pipeline.export_json import start_model_receipt
        monitor, previous = start_model_receipt(args.generation_receipt, Path(args.output))
    inputs = {}
    try:
        rates, crosswalk = load_rates(args.rates), load_crosswalk(args.crosswalk)
        if args.coverage:
            print(format_coverage(coverage_report(rates, crosswalk)))
        if args.build:
            from pipeline.export_json import MODEL_PROVINCES  # the export owns the default scope
            inputs = {"crosswalk": crosswalk, "usage_levels": load_usage_levels(args.usage_levels),
                      "taxes": load_taxes(args.taxes)}
            kwargs = {"rates": rates, **inputs, "provinces": tuple(args.province or MODEL_PROVINCES),
                      "as_of": args.as_of, "zone_policy": args.zone_policy,
                      "input_label": Path(args.rates).as_posix()}
            result = write_models(args.output, **kwargs) if args.output else build_models(**kwargs)
            if monitor is not None:
                monitor.save_generation_receipt(args.generation_receipt, result, previous=previous, inputs=inputs)
            print(format_models(result))
    except Exception as exc:
        if monitor is not None:
            monitor.save_generation_receipt(args.generation_receipt, None, previous=previous,
                                            error=f"{type(exc).__name__}: {exc}")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
