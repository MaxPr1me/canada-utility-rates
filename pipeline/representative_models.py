"""Representative models: crosswalk/coverage (Phase 7A) and the modeled-cost engine (Phase 7B)."""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Optional, Union

ROOT = Path(__file__).resolve().parents[1]
CROSSWALK_PATH = ROOT / "data" / "models" / "crosswalk.json"
USAGE_LEVELS_PATH = ROOT / "data" / "models" / "usage_levels.json"
TAXES_PATH = ROOT / "data" / "models" / "taxes.json"
RATES_PATH = ROOT / "site" / "data" / "rates.json"
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
        model = {
            "province": rule.get("province") or record.get("province"),
            "fuel": rule.get("fuel") or record.get("utility_type"),
            "sector": spec.get("sector"),
            "structure": spec.get("structure"),
            "size_band": resolve_size_band(spec.get("size_band"), record, crosswalk),
        }
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
    """Concrete (province, fuel, sector, structure, size_band) keys of a mapped outcome; [] otherwise."""
    model = outcome.get("model")
    if not model:
        return []
    return [(model["province"], model["fuel"], model["sector"], model["structure"], band)
            for band in (model.get("size_band") or [None])]


def key_label(key: tuple) -> str:
    """Printable model key, e.g. 'ON|electricity|commercial|demand|commercial_large'."""
    return "|".join("-" if part is None else str(part) for part in key)


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

METHOD_VERSION = "7B-2"
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
BASIS_UNITS = {"month": "$/month", "kwh": "$/kWh", "kw": "$/kW-month"}
TAX_BASES = ("pre_tax_subtotal", "pre_rebate_subtotal", "energy_charge_subtotal")
TAX_KINDS = ("sales_tax", "rebate")
PROVINCE_NAMES = {"AB": "Alberta", "BC": "British Columbia", "MB": "Manitoba", "NB": "New Brunswick",
                  "NL": "Newfoundland and Labrador", "NS": "Nova Scotia", "NT": "Northwest Territories",
                  "NU": "Nunavut", "ON": "Ontario", "PE": "Prince Edward Island", "QC": "Quebec",
                  "SK": "Saskatchewan", "YT": "Yukon"}
UTILITY_NOUNS = {("ON", "electricity"): "distributors"}
STRUCTURE_LABELS = {"flat": "flat-rate", "tiered": "tiered", "tou": "time-of-use (TOU)",
                    "tiered_tou": "tiered time-of-day", "ulo": "ultra-low overnight (ULO)",
                    "critical_peak": "critical-peak", "seasonal": "seasonal", "demand": "demand-billed",
                    "demand_tou": "demand time-of-use", "interruptible": "interruptible"}
NOT_APPLIED = {("ON", "electricity"): (
    "distribution loss factors (Ontario bills energy, transmission and regulatory charges on loss-adjusted kWh)",
    "Class A Global Adjustment")}
EXCLUSION_TEXT = {
    "expired": "expired before the as-of date",
    "not_yet_effective": "not yet in effect at the as-of date",
    "alternative": "conditional alternative to another charge",
    "optional": "optional",
    "conditional": "conditional (applies only to some customers)",
    "market_pending": "market price with no stored value (pending Phase 6)",
    "no_value": "no published value",
    "percentage_base_not_computable": "percentage adjustment whose base is not computable",
    "unsupported_unit": "unit not supported by the engine",
}
COMPONENT_RULES = (
    "Included: unconditional components in effect at the as-of date (fixed, energy, distribution, demand, "
    "transmission, regulatory, riders, carbon, other) in $/month, $/30 days, $/day, $/year, $/kWh, $/MWh, $/kW, "
    "$/kVA (per month or per day).",
    "Included as reference-customer charges: conditional components that a reviewed usage_levels.json "
    "'reference_customer' entry lists for the province, fuel and sector (Ontario: Class B CBR, Standard Supply "
    "Service administration, non-wholesale-market-participant riders, and non-RPP Class B Global Adjustment riders "
    "at 50 kW and over), itemized with reason 'reference_customer:<id>'.",
    "Excluded and counted: other conditional components (sub_component 'conditional'/'conditional_credit' or "
    "notes starting 'Conditional'), alternatives, optional components, components expired (end_date before the "
    "as-of date) or not yet effective, value-less market components (model state market_energy_pending) and "
    "percentage adjustments (no computable base).",
    "Not computable (record left out at that level, reason listed): a charge published only as conditional "
    "alternatives, an unconditional component without value or in an unsupported unit, TOU periods without an "
    "official share, ambiguous tier thresholds, seasons that do not cover the year, demand charges at a level "
    "without kW.",
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
        return "market_pending" if component.get("market_reference") else "no_value"
    return None


def reference_customer_entries(usage_levels: Optional[dict], province: Any, fuel: Any, sector: Any) -> list[dict]:
    """usage_levels 'reference_customer' entries for a province, fuel (missing = any fuel) and sector."""
    return [entry for entry in (usage_levels or {}).get("reference_customer") or []
            if isinstance(entry, dict) and entry.get("id") and entry.get("province") == province
            and entry.get("fuel", fuel) == fuel and sector in (entry.get("sectors") or [])]


def reference_customer_match(component: dict, entries: Iterable[dict]) -> Optional[str]:
    """Id of the first entry whose notes_regex/name_regex all fully match the component (notes without the
    provenance prefix); None when none does. Entries with no or unknown criteria never match."""
    fields = {"notes_regex": _note_body(component), "name_regex": component.get("component_name") or ""}
    for entry in entries:
        match = entry.get("match")
        if isinstance(match, dict) and match and set(match) <= set(REFERENCE_MATCH_FIELDS) and all(
                _fullmatch(regex, fields[field]) for field, regex in match.items()):
            return entry["id"]
    return None


def price_basis(component: dict, days_per_month: float = DEFAULT_DAYS_PER_MONTH,
                power_factor: float = DEFAULT_POWER_FACTOR) -> Optional[tuple[str, float, list[str]]]:
    """(basis 'month'|'kwh'|'kw'|'percent', factor to $/month, $/kWh or $/kW-month, conversions); None if unknown."""
    unit = re.sub(r"\s+", " ", (component.get("charge_unit") or "").strip().lower())
    dpm = f"{days_per_month:g}"
    if unit.startswith("%") or unit.startswith("fraction"):
        return "percent", 1.0, []
    fixed = {"$/month": (1.0, []), "$/30 days": (days_per_month / 30, [f"$/30 days x {dpm}/30"]),
             "$/day": (days_per_month, [f"$/day x {dpm}"]), "$/year": (1 / 12, ["$/year / 12"])}
    if unit in fixed:
        return ("month",) + fixed[unit]
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


def find_tou_shares(usage_levels: Optional[dict], province: Any, fuel: Any, structure: Any,
                    sector: Any) -> tuple[Optional[str], Optional[dict]]:
    """(id, entry) of the usage_levels tou_shares set whose applies_to matches; (None, None) when none does."""
    for key, entry in ((usage_levels or {}).get("tou_shares") or {}).items():
        applies = entry.get("applies_to") if isinstance(entry, dict) else None
        if not isinstance(applies, dict):
            continue
        structures = applies.get("structure")
        structures = [structures] if isinstance(structures, str) else list(structures or [])
        if (applies.get("province") == province and applies.get("fuel", fuel) == fuel and structure in structures
                and sector in (applies.get("sectors") or [])):
            return key, entry
    return None, None


def bucket_of(component_type: Any, basis: str) -> str:
    """Bucket of a priced component; distribution/delivery charges split by unit basis."""
    if component_type in ("distribution", "delivery"):
        return {"kwh": "distribution_volumetric", "kw": "demand"}.get(basis, "fixed")
    return {"fixed": "fixed", "energy": "energy", "demand": "demand", "transmission": "transmission",
            "regulatory": "regulatory", "rider": "riders", "carbon": "carbon"}.get(component_type, "other")


def _context(province: Any, fuel: Any, structure: Any, sector: Any, usage_levels: Optional[dict],
             as_of: date) -> dict:
    usage_levels = usage_levels or {}
    shares_id, entry = find_tou_shares(usage_levels, province, fuel, structure, sector)
    return {"as_of": as_of, "province": province, "fuel": fuel, "sector": sector, "usage_levels": usage_levels,
            "days_per_month": float(usage_levels.get("days_per_month") or DEFAULT_DAYS_PER_MONTH),
            "power_factor": float(usage_levels.get("power_factor_for_kva") or DEFAULT_POWER_FACTOR),
            "shares_id": shares_id, "shares": (entry or {}).get("shares"), "shares_entry": entry,
            "reference": reference_customer_entries(usage_levels, province, fuel, sector)}


def _tier_windows(group: list[tuple[dict, dict]]) -> list[str]:
    """Set tier_lower/tier_upper (kWh/month) on one season's tier items; blockers when thresholds are ambiguous."""
    rows = sorted(group, key=lambda pair: pair[1].get("tier_number") or 0)
    numbers = [comp.get("tier_number") for _, comp in rows]
    names = ", ".join(item["component"] for item, _ in rows)
    if numbers != list(range(1, len(rows) + 1)):
        return [f"tier numbers {numbers} are not 1..n: {names}"]
    lower = 0.0
    for index, (item, comp) in enumerate(rows):
        threshold = comp.get("tier_threshold")
        if threshold is not None and (comp.get("tier_unit") or "").strip().lower() not in _TIER_UNITS:
            return [f"tier threshold unit {comp.get('tier_unit')!r} not supported (kWh/month only): {names}"]
        if index == len(rows) - 1:
            if threshold is not None and float(threshold) != lower:
                return [f"last tier threshold {threshold} differs from the previous upper bound {lower:g}: {names}"]
            upper = math.inf
        elif threshold is None or float(threshold) < lower:
            return [f"tier thresholds missing or decreasing: {names}"]
        else:
            upper = float(threshold)
        item["tier_lower"], item["tier_upper"] = lower, upper
        lower = upper
    return []


def _period_and_tier_checks(priced: list[tuple[dict, dict]], ctx: dict) -> list[str]:
    """Attach TOU shares and tier windows to priced items; blockers for anything not computable."""
    blockers: list[str] = []
    shares = ctx.get("shares")
    energy_periods: set[str] = set()
    tier_groups: dict[tuple, list[tuple[dict, dict]]] = defaultdict(list)
    seasons: dict[str, list[int]] = {}
    for item, comp in priced:
        period, tier = comp.get("tou_period"), comp.get("tier_number")
        if item["basis"] == "kw":
            if period:
                blockers.append(f"time-period demand charge not computable: {item['component']}")
            if comp.get("demand_threshold_kw") is not None:
                blockers.append(f"demand threshold not computable: {item['component']}")
            continue
        if item["basis"] != "kwh":
            continue
        if period:
            share = (shares or {}).get(period)
            if share is None:
                source = ctx.get("shares_id") or "no matching share set"
                blockers.append(f"no official kWh share for TOU period '{period}' ({source}): {item['component']}")
            else:
                item["share"] = float(share)
            if item["type"] == "energy":
                energy_periods.add(period)
        if tier is not None:
            if period:
                blockers.append(f"tiered time-of-use price not computable: {item['component']}")
            else:
                tier_groups[(item["type"], item.get("season"))].append((item, comp))
        if item["type"] == "energy" and item.get("months"):
            seasons.setdefault(str(item.get("season")), item["months"])
    if energy_periods and shares and energy_periods != set(shares):
        blockers.append(f"TOU periods {sorted(energy_periods)} do not match the official share set {sorted(shares)}")
    if seasons and sorted(m for months in seasons.values() for m in months) != list(range(1, 13)):
        blockers.append("seasonal energy prices do not cover each month exactly once: "
                        + json.dumps(seasons, sort_keys=True))
    for group in tier_groups.values():
        blockers.extend(_tier_windows(group))
    return blockers


def _prepare(record: dict, ctx: dict) -> dict:
    """Classify a record's components once (level-independent): items, priced items, blockers, energy status."""
    items: list[dict] = []
    priced: list[tuple[dict, dict]] = []
    blockers: list[str] = []
    alternatives: dict[tuple, list[str]] = defaultdict(list)
    priced_slots: set[tuple] = set()
    market: list[str] = []
    energy_seen = market_energy = False
    for comp in record.get("components") or []:
        name = comp.get("component_name") or ""
        ctype = comp.get("component_type")
        energy_seen = energy_seen or ctype == "energy"
        item = {"component": name, "type": ctype, "sub_component": comp.get("sub_component"),
                "value": comp.get("charge_value"), "unit": comp.get("charge_unit")}
        for field in ("tou_period", "season", "tier_number", "effective_date", "end_date"):
            if comp.get(field) is not None:
                item[field] = comp.get(field)
        reason = component_exclusion(comp, ctx["as_of"])
        reference = reference_customer_match(comp, ctx["reference"]) if reason == "conditional" else None
        if reference:
            reason = None
        basis = None
        if reason is None:
            basis = price_basis(comp, ctx["days_per_month"], ctx["power_factor"])
            reason = "unsupported_unit" if basis is None else "percentage_base_not_computable" if basis[0] == "percent" else None
        if reason in ("unsupported_unit", "no_value"):
            blockers.append(f"{EXCLUSION_TEXT[reason]}: {name} ({item['unit']})")
        elif reason == "market_pending":
            market.append(name)
            market_energy = market_energy or ctype == "energy"
        elif reason == "alternative":
            alternatives[(ctype, comp.get("sub_component"))].append(name)
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
        if reference:
            item["reason"] = REFERENCE_PREFIX + reference
        items.append(item)
        priced.append((item, comp))
        priced_slots.add((ctype, comp.get("sub_component")))
    for slot, names in sorted(alternatives.items(), key=str):
        if slot not in priced_slots:
            blockers.append("charge published only as conditional alternatives: " + "; ".join(names))
    blockers.extend(_period_and_tier_checks(priced, ctx))
    if market_energy:
        energy_status = "market_pending"
    elif any(item["type"] == "energy" for item, _ in priced):
        energy_status = "included"
    elif energy_seen:
        energy_status = "excluded"
        blockers.append("energy components exist but none is unconditional and in effect")
    else:
        energy_status = "absent"
    return {"items": items, "priced": priced, "blockers": blockers, "energy_status": energy_status,
            "market_pending": market}


def _price(prep: dict, kwh: float, kw: Optional[float]) -> dict:
    """Monthly cost of a prepared record at one usage level; amounts align with prep['priced']."""
    reasons = list(prep["blockers"])
    if kw is None and any(item["basis"] == "kw" for item, _ in prep["priced"]):
        reasons.append("demand charges present but the usage level has no kW")
    if reasons:
        return {"status": "not_computable", "cost": None, "energy_charge_subtotal": None, "reasons": reasons,
                "amounts": []}
    amounts: list[float] = []
    for item, _ in prep["priced"]:
        if item["basis"] == "month":
            quantity = 1.0
        elif item["basis"] == "kw":
            quantity = float(kw or 0.0)
        else:
            quantity = float(kwh)
            if "tier_lower" in item:
                quantity = max(0.0, min(quantity, item["tier_upper"]) - item["tier_lower"])
            quantity *= item.get("share", 1.0)
        weight = len(item["months"]) / 12 if item.get("months") else 1.0
        amounts.append(float(item["value"]) * item["factor"] * quantity * weight)
    per_kwh = sum(a for (item, _), a in zip(prep["priced"], amounts) if item["basis"] == "kwh")
    return {"status": "ok", "cost": sum(amounts), "energy_charge_subtotal": per_kwh, "reasons": [], "amounts": amounts}


def _clean(value: Any) -> Any:
    if isinstance(value, float):
        return None if math.isinf(value) or math.isnan(value) else value
    return value


def record_monthly_cost(record: dict, kwh: float, kw: Optional[float] = None, *, sector: Optional[str] = None,
                        structure: Optional[str] = None, usage_levels: Optional[dict] = None,
                        as_of: Union[date, str, None] = None) -> dict:
    """Modeled monthly cost of one record at (kWh/month, kW) with an itemized included/excluded component list.

    ``sector`` (residential or a commercial size band) also selects the usage_levels reference-customer entries."""
    if sector is None:
        sector = "residential" if record.get("customer_class") == "residential" else None
    ctx = _context(record.get("province"), record.get("utility_type"), structure or record.get("rate_structure"),
                   sector, usage_levels, _as_of(as_of))
    prep = _prepare(record, ctx)
    priced = _price(prep, kwh, kw)
    amounts = {id(item): amount for (item, _), amount in zip(prep["priced"], priced["amounts"])}
    items = []
    for item in prep["items"]:
        row = {k: _clean(v) for k, v in item.items()}
        if id(item) in amounts:
            row["amount"] = amounts[id(item)]
        items.append(row)
    return {"record_id": record.get("id"), "utility": record.get("utility_name"), "tariff_code": record.get("tariff_code"),
            "kwh": kwh, "kw": kw, "status": priced["status"], "cost": priced["cost"],
            "energy_charge_subtotal": priced["energy_charge_subtotal"], "energy_status": prep["energy_status"],
            "market_pending": prep["market_pending"], "reasons": priced["reasons"], "shares_id": ctx["shares_id"],
            "items": items}


def record_covers_level(record: dict, kwh: Optional[float], kw: Optional[float]) -> bool:
    """True when the record's published demand ([min, max) kW) and kWh usage bounds include the level."""
    if kw is not None:
        lo, hi = _kw(record.get("demand_min_kw"), 0.0), _kw(record.get("demand_max_kw"), math.inf)
        if not lo <= kw < hi:
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
    """(applied, not_applied) tax/rebate lines for a level: sector, dates and thresholds (EITHER test when both)."""
    as_of = _as_of(as_of)
    group = "residential" if sector == "residential" else "commercial"
    lines = ((((taxes or {}).get("jurisdictions") or {}).get(province) or {}).get(fuel) or {}).get(group) or []
    annual = None if kwh is None else float(kwh) * 12
    applied, skipped = [], []
    for line in sorted((l for l in lines if isinstance(l, dict)), key=lambda l: l.get("order") or 0):
        eligibility = line.get("eligibility") or {}
        start, end = _as_date(line.get("effective_date")), _as_date(line.get("end_date"))
        reason = None
        if line.get("kind") not in TAX_KINDS or line.get("base") not in TAX_BASES or line.get("rate") is None:
            reason = f"unsupported line (kind {line.get('kind')!r}, base {line.get('base')!r})"
        elif sector not in (eligibility.get("sectors") or []):
            reason = f"sector {sector} not eligible"
        elif start is not None and start > as_of:
            reason = f"not in effect until {start.isoformat()}"
        elif end is not None and as_of >= end:
            reason = f"ended {end.isoformat()}"
        else:
            reason = _threshold_problem(eligibility, kw, annual)
        brief = {"name": line.get("name"), "kind": line.get("kind"), "rate": line.get("rate"), "base": line.get("base"),
                 "order": line.get("order"), "source_url": line.get("source_url"), "confidence": line.get("confidence")}
        if reason is None:
            applied.append(brief)
        else:
            skipped.append({"name": line.get("name"), "kind": line.get("kind"), "rate": line.get("rate"), "reason": reason})
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
    return {"record_id": record.get("id"), "tariff_code": record.get("tariff_code"), "name": record.get("name"),
            "zone": zone, "rule_id": rule_id, "effective_date": record.get("effective_date"),
            "source_url": record.get("source_url"), "confidence": record.get("confidence")}


def _period_label(item: dict) -> Optional[str]:
    parts = [item.get("tou_period")]
    if item["type"] == "energy":
        parts.append(f"tier {item['tier_number']}" if item.get("tier_number") is not None else None)
        parts.append(item.get("season") if item.get("months") else None)
    return " / ".join(str(p) for p in parts if p) or None


def _record_buckets(prep: dict) -> dict[tuple, float]:
    """Normalized rates per (bucket, unit, period): $/month, $/kWh, $/kW-month; seasonal non-energy annualized."""
    out: dict[tuple, float] = defaultdict(float)
    for item, _ in prep["priced"]:
        period = _period_label(item)
        weight = len(item["months"]) / 12 if item.get("months") and not period else 1.0
        out[(item["bucket"], BASIS_UNITS[item["basis"]], period)] += float(item["value"]) * item["factor"] * weight
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
    bands = (crosswalk.get("vocabulary") or {}).get("size_bands") or {}
    sector_text = sector if sector != "commercial" else f"commercial {(bands.get(band) or {}).get('label') or band or ''}".strip()
    return f"{PROVINCE_NAMES.get(province, province)} {fuel} - {sector_text} - {STRUCTURE_LABELS.get(structure, structure)}"


def _fmt_money(value: Optional[float]) -> str:
    return "n/a" if value is None else f"${value:,.2f}"


def _method_text(model: dict, key: tuple, levels: list[dict], component_counts: Counter,
                 component_examples: dict, conversions: set[str], zone_policy: str) -> str:
    province, fuel, sector, structure, band = key
    noun = UTILITY_NOUNS.get((province, fuel), "utilities")
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
        parts.append(f"Single source: {contributors[0]} ({records}) is the only {prov} utility with a computable live "
                     f"{sector_text} {structure_text} record; no averaging.")
    elif n:
        what = "at each usage level" if levels else "(component buckets only)"
        parts.append(f"Median of {n} {prov} {noun}' {sector_text} {structure_text} tariffs {what}, each counted once "
                     f"(zone policy '{zone_policy}': {ZONE_POLICY_TEXT[zone_policy]}; "
                     f"{len(cov['multi_zone_utilities'])} with more than one zone record).")
    else:
        parts.append("No contributing utility: every mapped record was excluded (see exclusions).")
    tou, tiers = model.get("tou"), model.get("tiers")
    energy = model["energy"]["status"]
    if energy == "market_pending":
        parts.append("Energy: market-priced energy is pending (Phase 6/7E); costs are delivery and regulatory charges "
                     "only, never a guessed energy price.")
    elif energy == "absent":
        parts.append("Energy: the contributing records publish no energy component; costs are delivery and regulatory "
                     "charges only.")
    elif energy == "mixed":
        parts.append("Energy: contributing records differ (some without energy); compare with care.")
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
            f"{lv['id']} {lv['kwh']:,.0f} kWh" + ("" if lv.get("kw") is None else f" at {lv['kw']:g} kW") + "/month"
            for lv in levels) + ".")
    else:
        parts.append("No usage level is defined for this size band yet; only component buckets are reported.")
    if conversions:
        parts.append("Conversions: " + "; ".join(sorted(conversions)) + ".")
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
    parts.append(f"Coverage: {n} of {cov['utilities_in_province']} {prov} {fuel} utilities with live records"
                 + (f"; no mapped record: {', '.join(cov['missing_utilities'])}" if cov["missing_utilities"] else "")
                 + ". Contributing: " + (", ".join(contributors) or "none") + ".")
    parts.append(f"Generated {model['generated_from']['as_of']} from {model['generated_from']['input']}.")
    return re.sub(r"\.\.(?=\s|$)", ".", " ".join(parts))


def _build_model(key: tuple, entries: list[tuple[dict, str, Optional[str]]], *, crosswalk: dict, usage_levels: dict,
                 taxes: dict, as_of: date, zone_policy: str, province_utilities: set[str], input_label: str) -> dict:
    """One model: per-utility costs at each usage level, statistics, buckets, energy blocks and method text."""
    province, fuel, sector, structure, band = key
    level_sector = band if sector == "commercial" and band else sector
    raw_levels = (usage_levels.get(fuel) or {}).get(level_sector) if isinstance(usage_levels.get(fuel), dict) else None
    levels = [lv for lv in raw_levels if isinstance(lv, dict)] if isinstance(raw_levels, list) else []
    ctx = _context(province, fuel, structure, level_sector, usage_levels, as_of)
    by_utility: dict[str, list[tuple[dict, str, Optional[str]]]] = defaultdict(list)
    for record, zone, rule_id in entries:
        by_utility[record.get("utility_name") or ""].append((record, zone, rule_id))
    exclusions: list[dict] = []
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
    used_ids: set = set()
    contributing: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
    level_out = []
    for level in levels:
        kwh = float(level.get("kwh") or 0.0)
        kw = None if level.get("kw") is None else float(level["kw"])
        applied, not_applied = tax_lines(taxes, province, fuel, level_sector, kwh, kw, as_of)
        costs, taxed, line_amounts, rows_out = {}, {}, defaultdict(list), []
        for utility, rows in chosen.items():
            zone_rows, reasons = [], []
            for record, zone, rule_id in rows:
                if not record_covers_level(record, kwh, kw):
                    reasons.append(f"{record.get('tariff_code')}: eligibility does not cover the level")
                    continue
                prep = preps[id(record)]
                priced = _price(prep, kwh, kw)
                if priced["status"] != "ok":
                    reasons.append(f"{record.get('tariff_code')}: " + "; ".join(priced["reasons"]))
                    continue
                with_tax, amounts = apply_tax_lines(priced["cost"], priced["energy_charge_subtotal"], applied)
                zone_rows.append((record, zone, priced["cost"], with_tax, amounts))
            if not zone_rows:
                exclusions.append({"scope": "utility", "utility": utility, "level": level.get("id"),
                                   "reason": " | ".join(reasons) or "no record"})
                continue
            costs[utility] = statistics.median([row[2] for row in zone_rows])
            taxed[utility] = statistics.median([row[3] for row in zone_rows])
            for index in range(len(applied)):
                line_amounts[index].append(statistics.median([row[4][index] for row in zone_rows]))
            for record, zone, *_ in zone_rows:
                if id(record) not in used_ids:
                    contributing[utility].append((preps[id(record)], record))
                used_ids.add(id(record))
            rows_out.append({"utility": utility, "cost_without_tax": round(costs[utility], 2),
                             "cost_with_tax": round(taxed[utility], 2),
                             "records": [row[0].get("id") for row in zone_rows],
                             "zone_costs": [{"record_id": row[0].get("id"), "tariff_code": row[0].get("tariff_code"),
                                             "zone": row[1], "cost_without_tax": round(row[2], 2)}
                                            for row in zone_rows] if len(zone_rows) > 1 else None})
        stats = summary_stats(costs.values())
        closest = closest_to_median(costs, stats["median"])
        closest_rows = [row for row in rows_out if row["utility"] == closest]
        level_out.append({
            "id": level.get("id"), "kwh": kwh, "kw": kw,
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
    if not levels:
        for utility, rows in chosen.items():
            for record, _, _ in rows:
                if not preps[id(record)]["blockers"]:
                    contributing[utility].append((preps[id(record)], record))
                    used_ids.add(id(record))
    for utility, rows in chosen.items():
        for record, zone, _ in rows:
            prep = preps[id(record)]
            if id(record) in used_ids:
                continue
            if prep["blockers"]:
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
    statuses: Counter = Counter()
    pending: list[dict] = []
    for utility, pairs in sorted(contributing.items()):
        for prep, record in pairs:
            statuses[prep["energy_status"]] += 1
            if prep["market_pending"]:
                pending.append({"utility": utility, "record_id": record.get("id"), "components": prep["market_pending"]})
            for item in prep["items"]:
                if item["status"] == "excluded":
                    counts, examples, slot = component_counts, component_examples, item["reason"]
                else:
                    conversions.update(item.get("conversions") or [])
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
    if pending:
        state = "market_energy_pending"
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
    cost_basis = {"included": "delivery_and_energy", "market_pending": "delivery_only_market_energy_pending",
                  "absent": "delivery_only_no_energy_component"}.get(energy, energy)
    bucket_rows = {utility: [_record_buckets(prep) for prep, _ in pairs] for utility, pairs in contributing.items()}
    warnings = []
    entry = ctx.get("shares_entry") or {}
    period_end = _PERIOD_END_RE.search(entry.get("period") or "")
    if period_end:
        month = _MONTHS.get(period_end.group(1).lower()[:3])
        if month and as_of > date(int(period_end.group(3)), month, int(period_end.group(2))):
            warnings.append(f"TOU shares {ctx.get('shares_id')} cover {entry.get('period')}; the as-of date is later")
    if energy == "mixed":
        warnings.append("contributing records differ in energy basis: " + json.dumps(dict(statuses), sort_keys=True))
    model = {
        "id": key_label(key),
        "key": {"province": province, "fuel": fuel, "sector": sector, "structure": structure, "size_band": band},
        "label": _model_label(key, crosswalk),
        "state": state,
        "provenance": "modeled",
        "cost_basis": cost_basis,
        "energy": {"status": energy, "records_by_status": dict(sorted(statuses.items())), "market_pending": pending},
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
    model["method"] = _method_text(model, key, levels, component_counts, component_examples, conversions, zone_policy)
    return model


def _model_order(key: tuple, crosswalk: dict) -> tuple:
    bands = list(((crosswalk.get("vocabulary") or {}).get("size_bands") or {}).keys())
    structures = list(((crosswalk.get("vocabulary") or {}).get("structures") or {}).keys())
    province, fuel, sector, structure, band = key
    return (province or "", fuel or "", sector != "residential", bands.index(band) if band in bands else -1,
            structures.index(structure) if structure in structures else len(structures), str(structure))


def build_models(rates: Union[list[dict], dict], crosswalk: dict, usage_levels: dict, taxes: dict,
                 provinces: Optional[Iterable[str]] = ("ON",), as_of: Union[date, str, None] = None,
                 zone_policy: str = "median_of_zones", input_label: str = "site/data/rates.json") -> dict:
    """Representative models for every crosswalk model key of the given provinces (Phase 7B)."""
    if zone_policy not in ZONE_POLICIES:
        raise ValueError(f"zone_policy must be one of {ZONE_POLICIES}")
    as_of_date = _as_of(as_of)
    rows = rates.get("records", []) if isinstance(rates, dict) else list(rates)
    wanted = None if provinces is None else {str(p).upper() for p in provinces}
    live = [r for r in latest_live_records(rows) if wanted is None or r.get("province") in wanted]
    groups: dict[tuple, list] = defaultdict(list)
    province_utilities: dict[tuple, set[str]] = defaultdict(set)
    for record in live:
        province_utilities[(record.get("province"), record.get("utility_type"))].add(record.get("utility_name") or "")
        outcome = match_record(record, crosswalk)
        for key in model_keys(outcome):
            groups[key].append((record, outcome.get("zone") or "default", outcome.get("rule_id")))
    models = [_build_model(key, groups[key], crosswalk=crosswalk, usage_levels=usage_levels, taxes=taxes,
                           as_of=as_of_date, zone_policy=zone_policy,
                           province_utilities=province_utilities[(key[0], key[1])], input_label=input_label)
              for key in sorted(groups, key=lambda k: _model_order(k, crosswalk))]
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
                  "rates_generated_at": rates.get("generated_at") if isinstance(rates, dict) else None,
                  "latest_record_created_at": max(created) if created else None},
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
            "reference_customer": [{k: entry.get(k) for k in ("id", "province", "fuel", "sectors", "match", "reason",
                                                              "source")}
                                   for entry in usage_levels.get("reference_customer") or []
                                   if isinstance(entry, dict) and (wanted is None or entry.get("province") in wanted)],
            "buckets": dict(BUCKET_TEXT),
            "taxes": {"as_of": taxes.get("as_of"), "rule": "Lines from data/models/taxes.json for province, fuel and "
                      "sector, in effect at the as-of date; eligibility thresholds use the level's kW and kWh x 12 "
                      "(either test when both are set); amount = rate x base; never compounded; rebates subtracted."},
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
    target.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
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
    parser.add_argument("--province", action="append", help="province code, repeatable (default ON)")
    parser.add_argument("--as-of", default=None, help="YYYY-MM-DD (default: today, UTC)")
    args = parser.parse_args(argv)
    if not (args.coverage or args.build):
        parser.print_help()
        return 0
    rates, crosswalk = load_rates(args.rates), load_crosswalk(args.crosswalk)
    if args.coverage:
        print(format_coverage(coverage_report(rates, crosswalk)))
    if args.build:
        kwargs = {"rates": rates, "crosswalk": crosswalk, "usage_levels": load_usage_levels(args.usage_levels),
                  "taxes": load_taxes(args.taxes), "provinces": tuple(args.province or ("ON",)),
                  "as_of": args.as_of, "zone_policy": args.zone_policy,
                  "input_label": Path(args.rates).as_posix()}
        result = write_models(args.output, **kwargs) if args.output else build_models(**kwargs)
        print(format_models(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
