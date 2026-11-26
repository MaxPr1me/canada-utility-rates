"""Spark gap comparison by region (method SG-1; owner decisions 118 and 124-165, 2026-11-25 and 2026-11-26).

Step 1, the spark gap: the price of electricity divided by the price of the region's usual heating fuel for the same
amount of energy, before equipment efficiency (decision 128). Step 2, the break-even heat pump COP: the spark gap x the
efficiency of a new furnace (homes) or of commercial gas furnaces and boilers (businesses). For homes it is checked
against realistic seasonal heat pump COPs for the province's climate and stated in plain words (decisions 156-157).

Electricity and natural gas are priced from the live tariffs by the representative model engine at the spark gap's own
points (data/models/spark_gap.json): the average price is the whole monthly bill, fixed charges included, divided by
its energy (decision 140); the marginal price is the cost of the next kWh, m3 or GJ (decision 130). Gas billed in m3
converts to energy with its utility's published heating value, else the CER factor (decision 153). Heating oil is
Statistics Canada's latest monthly average retail price, as paid (data/fuel/heating_oil_prices.json, written by
scripts/fetch_heating_oil.py; decisions 149-152 and 165). Each fuel's price in a region is the median across its
utilities, each counted once (decision 131).

The result (site/data/spark_gap.json) is a labelled comparison aid: running cost only, never a bill, never in model
medians, the model change log, Rate History, change checks or coverage (decision 143; safeguard 8).
"""
from __future__ import annotations

import argparse
import copy
import json
import logging
import math
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from pipeline import representative_models as rm

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "models" / "spark_gap.json"
OIL_PRICES_PATH = ROOT / "data" / "fuel" / "heating_oil_prices.json"
OUTPUT_PATH = ROOT / "site" / "data" / "spark_gap.json"
METHOD = "SG-1"
CUSTOMERS = ("residential", "commercial_small", "commercial_medium")
REGIONS = ("BC", "AB", "SK", "MB", "ON", "QC", "NB", "NS", "PE", "NL", "YT", "NT", "NU")
TERRITORIES = ("YT", "NT", "NU")
FUELS = ("gas", "heating_oil")
VIEWS = ("without_tax", "with_tax", "after_subsidy")
VIEW_TEXT = {"without_tax": "Before tax and rebates", "with_tax": "With tax and rebates",
             "after_subsidy": "After automatic territorial subsidies, before tax (territories)"}
USABLE_STATES = ("modeled", "single_source", "market_energy_estimated")
CHOICE_KINDS = ("structure", "cheapest", "median")
FUEL_LABELS = {"gas": "Natural gas", "heating_oil": "Heating oil"}
FURNACE_WORDS = {"gas": "a new gas furnace", "heating_oil": "a new oil furnace"}
MJ_PER_KWH = 3.6
VERDICTS = ("heat_pump_cheaper", "depends_on_heat_pump", "furnace_cheaper")
_LEVEL_IDS = {"m3": ("sg_average_m3", "sg_marginal_m3", "sg_next_m3"),
              "GJ": ("sg_average_gj", "sg_marginal_gj", "sg_next_gj")}
_DATE_KEYS = ("reviewed", "checked")


# ---------------------------------------------------------------------------------------------------------------------
# Reviewed inputs
# ---------------------------------------------------------------------------------------------------------------------

def load_json(path: Union[str, Path]) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _date_ok(value: Any) -> bool:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    return True


def config_problems(config: Any) -> list[str]:
    """Problems that make the reviewed spark gap inputs unusable; an empty list means valid."""
    if not isinstance(config, dict) or config.get("version") != 1 or config.get("method") != METHOD:
        return [f"spark gap inputs must be version 1 of method {METHOD}"]
    problems = []
    if not _positive(config.get("kwh_per_gj")):
        problems.append("kwh_per_gj must be a positive number")
    points = config.get("points") or {}
    for customer in CUSTOMERS:
        point = points.get(customer)
        if not isinstance(point, dict):
            problems.append(f"points.{customer} is missing")
            continue
        electricity = point.get("electricity") or {}
        if not isinstance(electricity.get("level"), str) or not _positive(electricity.get("kwh")) or not (
                electricity.get("kw") is None or _positive(electricity.get("kw"))):
            problems.append(f"points.{customer}.electricity needs a level id, kWh and kW (or null)")
        if not _positive(point.get("average_energy_gj")):
            problems.append(f"points.{customer}.average_energy_gj must be positive")
        marginal = point.get("gas_marginal") or {}
        if not all(_positive(marginal.get(unit)) for unit in ("m3", "GJ")):
            problems.append(f"points.{customer}.gas_marginal needs positive m3 and GJ quantities")
    fuels = config.get("comparison_fuels") or {}
    for customer in CUSTOMERS:
        mapping = fuels.get(customer)
        if not isinstance(mapping, dict) or not mapping or any(
                region not in REGIONS or fuel not in FUELS for region, fuel in mapping.items()):
            problems.append(f"comparison_fuels.{customer} must map region codes to gas or heating_oil")
        elif customer != "residential" and any(fuel != "gas" for fuel in mapping.values()):
            problems.append(f"comparison_fuels.{customer}: businesses compare with gas only (decision 125)")
    values = config.get("gas_heating_values") or {}
    if not _positive((values.get("fallback") or {}).get("mj_per_m3")):
        problems.append("gas_heating_values.fallback.mj_per_m3 must be positive")
    for entry in values.get("entries") or []:
        regex = ((entry or {}).get("match") or {}).get("tariff_code_regex")
        if (not isinstance(entry, dict) or not entry.get("id") or not entry.get("utility")
                or not _positive(entry.get("mj_per_m3")) or not _date_ok(entry.get("reviewed"))
                or (regex is not None and not rm._regex_ok(regex))):
            problems.append(f"gas heating value entry {(entry or {}).get('id')!r} needs an id, utility, MJ/m3, "
                            "reviewed date and a valid optional tariff_code_regex")
    oil = config.get("heating_oil") or {}
    if (not _positive(oil.get("energy_mj_per_litre")) or not isinstance(oil.get("series"), dict)
            or not isinstance(oil.get("max_lag_months"), int) or not _date_ok(oil.get("reviewed"))):
        problems.append("heating_oil needs energy_mj_per_litre, a series map, max_lag_months and a reviewed date")
    efficiency = config.get("efficiency") or {}
    for fuel in FUELS:
        if not _fraction(((efficiency.get("residential") or {}).get(fuel) or {}).get("value")):
            problems.append(f"efficiency.residential.{fuel}.value must be in (0, 1]")
    commercial = (efficiency.get("commercial") or {}).get("gas")
    if not isinstance(commercial, list) or not commercial or any(
            not isinstance(item, dict) or not item.get("id") or not _fraction(item.get("value")) for item in commercial):
        problems.append("efficiency.commercial.gas must list equipment with an id and a value in (0, 1]")
    cop = config.get("realistic_cop") or {}
    cities = cop.get("cities") or {}
    if not cities or any(not isinstance(v, dict) or not _positive(v.get("standard")) or not _positive(
            v.get("cold_climate")) or v["standard"] > v["cold_climate"] for v in cities.values()):
        problems.append("realistic_cop.cities need standard <= cold_climate positive COPs")
    if any(city not in cities for city in (cop.get("provinces") or {}).values()):
        problems.append("realistic_cop.provinces names a city without COPs")
    for entry in (config.get("utility_choices") or {}).get("entries") or []:
        if (not isinstance(entry, dict) or entry.get("select") not in CHOICE_KINDS or entry.get("province") not in
                REGIONS or entry.get("fuel") not in ("electricity", "gas") or not isinstance(entry.get("sectors"), list)
                or (entry.get("select") == "structure" and not entry.get("structure"))
                or (entry.get("select") != "structure" and not entry.get("utility"))):
            problems.append(f"utility choice {(entry or {}).get('id')!r} is invalid")
    if not isinstance(config.get("reviews_max_age_days"), int):
        problems.append("reviews_max_age_days must be an integer")
    return problems


def _fraction(value: Any) -> bool:
    return _positive(value) and value <= 1


def load_config(path: Union[str, Path, None] = None) -> dict:
    config = load_json(path or CONFIG_PATH)
    problems = config_problems(config)
    if problems:
        raise ValueError("invalid spark gap inputs: " + "; ".join(problems))
    return config


def stale_reviews(config: dict, today: date) -> list[str]:
    """Reviewed values whose review or check date is more than reviews_max_age_days old (the owner's one-year
    freshness alarm, 2026-11-23): each heating value, efficiency, oil energy and source check."""
    limit = int(config.get("reviews_max_age_days") or 365)
    stale = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key in _DATE_KEYS:
                if key in value and _date_ok(value[key]) and (today - date.fromisoformat(value[key])).days > limit:
                    stale.append(f"{path or 'spark gap inputs'}: {key} {value[key]}")
            for key, item in value.items():
                walk(item, f"{path}.{key}" if path else key)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(item, f"{path}.{(item or {}).get('id', index) if isinstance(item, dict) else index}")

    walk(config, "")
    return stale


def heating_value(record: dict, config: dict) -> tuple[float, str]:
    """(MJ per m3, entry id) for a gas record billed in m3: its utility's first matching reviewed entry, else the CER
    fallback (decision 153)."""
    for entry in config["gas_heating_values"].get("entries") or []:
        if entry.get("utility") != record.get("utility_name"):
            continue
        regex = (entry.get("match") or {}).get("tariff_code_regex")
        if regex and not rm._fullmatch(regex, record.get("tariff_code") or ""):
            continue
        return float(entry["mj_per_m3"]), entry["id"]
    return float(config["gas_heating_values"]["fallback"]["mj_per_m3"]), "cer_fallback"


# ---------------------------------------------------------------------------------------------------------------------
# Heating-oil prices (Statistics Canada 18-10-0001-01; scripts/fetch_heating_oil.py)
# ---------------------------------------------------------------------------------------------------------------------

def oil_price_problems(document: Any) -> list[str]:
    if not isinstance(document, dict) or document.get("version") != 1 or document.get("kind") != "heating_oil_prices":
        return ["the heating-oil price file is not version 1 of kind heating_oil_prices"]
    series = document.get("series")
    if not isinstance(series, dict) or not series:
        return ["the heating-oil price file has no series"]
    problems = []
    for region, item in series.items():
        months = (item or {}).get("months") if isinstance(item, dict) else None
        if not isinstance(months, dict) or any(not re.fullmatch(r"\d{4}-\d{2}", month) for month in months):
            problems.append(f"heating-oil series {region} has invalid months")
    return problems


def latest_oil_month(document: dict, region: str) -> Optional[tuple[str, dict]]:
    """(YYYY-MM, entry) of a region's latest month with a usable price, or None."""
    months = ((document.get("series") or {}).get(region) or {}).get("months") or {}
    usable = [(month, entry) for month, entry in months.items()
              if isinstance(entry, dict) and _positive(entry.get("value"))]
    return max(usable, key=lambda item: item[0]) if usable else None


def months_between(month: str, today: date) -> int:
    year, number = (int(part) for part in month.split("-"))
    return (today.year * 12 + today.month) - (year * 12 + number)


def _oil_tax_factor(taxes: dict, region: str, as_of: date) -> tuple[Optional[float], list[dict], Optional[str]]:
    """1 + sales taxes - rebates of the reviewed heating-oil lines in force (decision 151), or None when the region has
    no reviewed sales-tax line (before tax then stays not available: fail closed)."""
    applied, _ = rm.tax_lines(taxes, region, "heating_oil", "residential", None, None, as_of)
    if not any(line["kind"] == "sales_tax" for line in applied):
        return None, applied, f"no reviewed heating-oil tax line for {region} in data/models/taxes.json"
    factor = 1 + math.fsum(float(line["rate"]) * (1 if line["kind"] == "sales_tax" else -1) for line in applied)
    return factor, applied, None


def oil_region(region: str, config: dict, document: Optional[dict], document_problem: Optional[str], taxes: dict,
               as_of: date) -> dict:
    """Heating-oil price of one region in cents per kWh of oil energy, with and before tax."""
    oil = config["heating_oil"]
    if region in (oil.get("not_available") or {}):
        return {"available": False, "reasons": [oil["not_available"][region]]}
    series_id = (oil.get("series") or {}).get(region)
    if series_id is None:
        return {"available": False, "reasons": [f"no heating-oil price series is configured for {region}"]}
    if document is None:
        return {"available": False, "reasons": [document_problem or "the heating-oil price file is unavailable"]}
    latest = latest_oil_month(document, series_id)
    if latest is None:
        return {"available": False, "reasons": [f"the heating-oil price file has no usable month for {region}"]}
    month, entry = latest
    kwh_per_litre = float(oil["energy_mj_per_litre"]) / MJ_PER_KWH
    paid = float(entry["value"])
    factor, lines, problem = _oil_tax_factor(taxes, region, as_of)
    series = document["series"][series_id]
    with_tax = paid / kwh_per_litre
    out = {
        "available": True, "month": month, "cents_per_litre": paid, "geo": series.get("geo"),
        "vector": series.get("vector"), "status": entry.get("status"), "release_time": entry.get("release_time"),
        "kwh_per_litre": kwh_per_litre, "age_months": months_between(month, as_of),
        "tax_lines": [{key: line.get(key) for key in ("name", "kind", "rate", "source_url")} for line in lines],
        "tax_factor": factor,
        "average": {"with_tax": with_tax, "without_tax": None if factor is None else with_tax / factor},
        "reasons": [problem] if problem else [],
    }
    out["marginal"] = dict(out["average"])  # a price per litre has no fixed charge: the next kWh costs the same
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Evaluation levels for the model engine
# ---------------------------------------------------------------------------------------------------------------------

def _same_number(a: Any, b: Any) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(float(a), float(b), rel_tol=0, abs_tol=1e-9)


def electricity_levels(usage_levels: dict, config: dict, step_kwh: float = 0.0) -> dict:
    """A usage_levels copy whose electricity levels are only the spark gap points, moved by ``step_kwh`` at the same
    load factor (decision 137). The level ids stay the model's, so reviewed rules tied to them still apply (homes
    single-phase 200 A, the small-business phase rules, Lethbridge 994)."""
    levels = copy.deepcopy(usage_levels)
    electricity = levels.get("electricity") or {}
    replaced = {sector: [] for sector, value in electricity.items() if isinstance(value, list)}
    for customer in CUSTOMERS:
        point = config["points"][customer]["electricity"]
        source = next((lv for lv in electricity.get(customer) or []
                       if isinstance(lv, dict) and lv.get("id") == point["level"]), None)
        if source is None or not _same_number(source.get("kwh"), point["kwh"]) or not _same_number(
                source.get("kw"), point["kw"]):
            raise ValueError(f"spark gap point {customer} ({point['level']}: {point['kwh']} kWh, {point['kw']} kW) no "
                             "longer matches the model's usage level; review data/models/spark_gap.json")
        kwh = float(point["kwh"]) + step_kwh
        kw = None if point["kw"] is None else float(point["kw"]) * kwh / float(point["kwh"])
        replaced[customer] = [{**source, "kwh": kwh, "kw": kw}]
    levels["electricity"] = {**electricity, **replaced}
    return levels


def gas_levels(usage_levels: dict, config: dict, mj_per_m3: float) -> dict:
    """A usage_levels copy whose gas levels are the spark gap points in both native units: the average energy (m3 at
    ``mj_per_m3``), the marginal point and the next unit above it (decisions 139-142)."""
    levels = copy.deepcopy(usage_levels)
    gas = levels.get("gas") or {}
    replaced = {sector: [] for sector, value in gas.items() if isinstance(value, list)}
    for customer in CUSTOMERS:
        point = config["points"][customer]
        energy, marginal = float(point["average_energy_gj"]), point["gas_marginal"]
        replaced[customer] = [
            {"id": _LEVEL_IDS["m3"][0], "quantity": energy * 1000 / mj_per_m3, "unit": "m3", "role": "spark_gap"},
            {"id": _LEVEL_IDS["GJ"][0], "quantity": energy, "unit": "GJ", "role": "spark_gap"},
            {"id": _LEVEL_IDS["m3"][1], "quantity": float(marginal["m3"]), "unit": "m3", "role": "spark_gap"},
            {"id": _LEVEL_IDS["GJ"][1], "quantity": float(marginal["GJ"]), "unit": "GJ", "role": "spark_gap"},
            {"id": _LEVEL_IDS["m3"][2], "quantity": float(marginal["m3"]) + 1, "unit": "m3", "role": "spark_gap"},
            {"id": _LEVEL_IDS["GJ"][2], "quantity": float(marginal["GJ"]) + 1, "unit": "GJ", "role": "spark_gap"},
        ]
    levels["gas"] = {**gas, **replaced}
    return levels


# ---------------------------------------------------------------------------------------------------------------------
# Per-utility prices
# ---------------------------------------------------------------------------------------------------------------------

def _band(model: dict) -> str:
    key = model.get("key") or {}
    return key.get("size_band") or key.get("sector")


def _models(result: dict, region: str, fuel: str, customer: str) -> list[dict]:
    return [model for model in result.get("models") or [] if (model.get("key") or {}).get("province") == region
            and (model.get("key") or {}).get("fuel") == fuel and _band(model) == customer]


def _level(model: Optional[dict], level_id: str) -> Optional[dict]:
    return next((level for level in (model or {}).get("levels") or [] if level.get("id") == level_id), None)


def _rows(level: Optional[dict]) -> dict[str, dict]:
    return {row["utility"]: row for row in (level or {}).get("utilities") or [] if row.get("utility")}


def _model_problem(model: dict, level: Optional[dict]) -> Optional[str]:
    label = model.get("label") or model.get("id")
    if model.get("state") == "market_energy_pending":
        reason = (model.get("energy_estimate") or {}).get("reason")
        return f"{label}: market energy pending" + (f" ({reason})" if reason else "")
    if level is not None and level.get("withheld"):
        return f"{label}: withheld ({(level['withheld'] or {}).get('reason') or 'a required utility is missing'})"
    return None


def _cents_per_kwh(dollars: Optional[float], kwh: float) -> Optional[float]:
    return None if dollars is None else dollars / kwh * 100


def _choices(config: dict, region: str, fuel: str, customer: str) -> list[dict]:
    return [entry for entry in (config.get("utility_choices") or {}).get("entries") or []
            if entry.get("province") == region and entry.get("fuel") == fuel and customer in entry.get("sectors", [])]


def _record_note(model: dict) -> dict:
    key = model.get("key") or {}
    return {"model": model.get("id"), "label": model.get("label"), "structure": key.get("structure")}


def _resolve(candidates: dict[str, list[dict]], choices: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    """One entry per utility (decision 131): reviewed choices settle a utility found in several models; any other
    overlap fails closed. Returns (utilities, problems, notes)."""
    chosen, problems, notes = [], [], []
    for utility, entries in sorted(candidates.items()):
        if len(entries) == 1:
            chosen.append(entries[0])
            continue
        choice = next((c for c in choices if c.get("utility") == utility and c["select"] in ("cheapest", "median")),
                      None)
        structures = ", ".join(sorted({str(e["model"]["structure"]) for e in entries}))
        if choice is None:
            problems.append(f"{utility} is priced more than once ({structures} models or heating values) with no "
                            "reviewed choice in data/models/spark_gap.json")
        elif choice["select"] == "cheapest":
            pick = min(entries, key=lambda e: e["sort_cost"])
            chosen.append({**pick, "choice": choice["id"]})
            notes.append(f"{utility}: {pick['model']['structure']} plan, the cheaper of {structures} at the average "
                         f"point ({choice['id']})")
        else:
            merged = {**entries[0], "choice": choice["id"], "models": [e["model"] for e in entries],
                      "records": sorted({r for e in entries for r in e["records"]}, key=str)}
            for part in ("average", "marginal"):
                merged[part] = {}
                for view in VIEWS:
                    values = [e[part].get(view) for e in entries]
                    merged[part][view] = statistics.median(values) if all(v is not None for v in values) else None
            merged["marginal_reason"] = next((e["marginal_reason"] for e in entries if e.get("marginal_reason")), None)
            merged["estimated_energy"] = any(e.get("estimated_energy") for e in entries)
            merged["interim"] = any(e.get("interim") for e in entries)
            merged["heating_values"] = [hv for e in entries for hv in e.get("heating_values") or []]
            chosen.append(merged)
            notes.append(f"{utility}: median of its {len(entries)} systems ({structures}; {choice['id']})")
    return chosen, problems, notes


def electricity_region(region: str, customer: str, base: dict, nxt: dict, config: dict) -> dict:
    """Electricity average and marginal prices (cents per kWh) of one region and customer type."""
    point = config["points"][customer]["electricity"]
    kwh, level_id = float(point["kwh"]), point["level"]
    choices = _choices(config, region, "electricity", customer)
    structure = next((c["structure"] for c in choices if c["select"] == "structure"), None)
    next_models = {model.get("id"): model for model in _models(nxt, region, "electricity", customer)}
    candidates: dict[str, list[dict]] = defaultdict(list)
    problems, skipped = [], []
    for model in _models(base, region, "electricity", customer):
        if structure is not None and (model.get("key") or {}).get("structure") != structure:
            continue
        level = _level(model, level_id)
        problem = _model_problem(model, level)
        if problem:
            problems.append(problem)
            continue
        if model.get("state") not in USABLE_STATES or level is None:
            skipped.append(f"{model.get('label')}: no utility is computable at this point")
            continue
        following = _rows(_level(next_models.get(model.get("id")), level_id))
        for row in level.get("utilities") or []:
            exact = row.get("exact") or {}
            entry = {"utility": row["utility"], "model": _record_note(model), "records": list(row.get("records") or []),
                     "sort_cost": exact.get("without_tax"),
                     "average": {view: _cents_per_kwh(exact.get(view), kwh) for view in VIEWS},
                     "marginal": {view: None for view in VIEWS}, "marginal_reason": None,
                     "estimated_energy": bool(row.get("estimated_market_energy")), "interim": bool(row.get("interim"))}
            nrow = following.get(row["utility"])
            if nrow is None:
                entry["marginal_reason"] = "not computable at the next kWh"
            elif sorted(map(str, nrow.get("records") or [])) != sorted(map(str, entry["records"])):
                entry["marginal_reason"] = "the next kWh moves the customer to another tariff"
            else:
                after = nrow.get("exact") or {}
                entry["marginal"] = {view: None if exact.get(view) is None or after.get(view) is None
                                     else (after[view] - exact[view]) * 100 for view in VIEWS}
            candidates[row["utility"]].append(entry)
    utilities, overlap, notes = _resolve(candidates, choices)
    problems.extend(overlap)
    if structure is not None:
        choice_id = next(c["id"] for c in choices if c["select"] == "structure")
        notes.insert(0, f"{rm.PROVINCE_NAMES.get(region, region)}: {structure} models only ({choice_id})")
    return _region_prices(utilities, problems, notes, skipped)


def gas_region(region: str, customer: str, context: dict, config: dict) -> dict:
    """Natural gas average and marginal prices (cents per kWh of gas energy) of one region and customer type.

    ``context`` (from gas_runs) holds the gas builds, one per heating value (m3 levels at that value) plus one for
    GJ-billed utilities; a row is taken from the run whose heating value is its records' value (decision 153)."""
    point = config["points"][customer]
    energy_gj, kwh_per_gj = float(point["average_energy_gj"]), float(config["kwh_per_gj"])
    record_values, utility_values = context["record_values"], context["utility_values"]
    choices = _choices(config, region, "gas", customer)
    candidates: dict[str, list[dict]] = defaultdict(list)
    problems, skipped = [], []
    for run in context["runs"]:
        for model in _models(run["result"], region, "gas", customer):
            unit = "m3" if _level(model, _LEVEL_IDS["m3"][0]) is not None else "GJ" if _level(
                model, _LEVEL_IDS["GJ"][0]) is not None else None
            if unit is None or (unit == "GJ") != (run["mj_per_m3"] is None):
                continue
            average, marginal, following = (_level(model, level_id) for level_id in _LEVEL_IDS[unit])
            withheld = (average or {}).get("withheld")
            if withheld:
                # A withheld level has no rows; it concerns this run when one of its utilities uses this run's value.
                names = set(withheld.get("missing_required") or []) | set(withheld.get("computed_utilities") or [])
                if unit == "GJ" or any(run["mj_per_m3"] in utility_values.get((region, name), ()) for name in names):
                    problems.append(_model_problem(model, average))
                continue
            mj = run["mj_per_m3"]

            def own(row: Optional[dict]) -> tuple[list, Optional[dict]]:
                """This run's records of a row (every record for GJ) and the median of their exact costs per view,
                as the models take a utility's zones."""
                records = [item for item in ((row or {}).get("exact") or {}).get("records") or []
                           if unit == "GJ" or record_values.get(item["record_id"], (None,))[0] == mj]
                if not records:
                    return [], None
                return sorted((item["record_id"] for item in records), key=str), {
                    view: (statistics.median([item[view] for item in records])
                           if all(item.get(view) is not None for item in records) else None) for view in VIEWS}

            selected = [(row, *own(row)) for row in (average or {}).get("utilities") or []]
            selected = [(row, ids, costs) for row, ids, costs in selected if ids]
            if not selected:
                continue  # an m3 model's utilities are priced in the run of their own heating value
            if model.get("state") not in USABLE_STATES:
                skipped.append(f"{model.get('label')}: no utility is computable at this point")
                continue
            low, high = _rows(marginal), _rows(following)
            gj_per_unit = 1.0 if unit == "GJ" else mj / 1000
            for row, ids, costs in selected:
                values = sorted({record_values[r] for r in ids if r in record_values})
                entry = {"utility": row["utility"], "model": _record_note(model), "records": ids,
                         "sort_cost": costs["without_tax"], "unit": unit,
                         "heating_values": [{"mj_per_m3": value, "id": value_id} for value, value_id in values],
                         "average": {view: None if costs[view] is None else costs[view] / energy_gj * 100 / kwh_per_gj
                                     for view in VIEWS},
                         "marginal": {view: None for view in VIEWS}, "marginal_reason": None,
                         "estimated_energy": False, "interim": bool(row.get("interim"))}
                (low_ids, low_costs), (high_ids, high_costs) = own(low.get(row["utility"])), own(
                    high.get(row["utility"]))
                if not low_ids or not high_ids:
                    entry["marginal_reason"] = "not computable at the marginal point"
                elif low_ids != high_ids:
                    entry["marginal_reason"] = "the next unit moves the customer to another tariff"
                else:
                    entry["marginal"] = {view: None if low_costs[view] is None or high_costs[view] is None
                                         else (high_costs[view] - low_costs[view]) / gj_per_unit * 100 / kwh_per_gj
                                         for view in VIEWS}
                candidates[row["utility"]].append(entry)
    utilities, overlap, notes = _resolve(candidates, choices)
    problems.extend(overlap)
    return _region_prices(utilities, problems, notes, skipped)


def _median_or_none(values: Iterable[Optional[float]]) -> Optional[float]:
    present = [value for value in values if value is not None]
    return statistics.median(present) if present else None


def _region_prices(utilities: list[dict], problems: list[str], notes: list[str], skipped: list[str]) -> dict:
    """Median across utilities, each counted once, for each view (a utility whose marginal is not computable is left
    out of the marginal median and named, as the models leave out a utility not computable at a level)."""
    if problems or not utilities:
        return {"available": False, "utilities": utilities, "notes": notes,
                "reasons": problems or skipped or ["no utility is computable at this point"]}
    average = {view: (statistics.median([u["average"][view] for u in utilities])
                      if all(u["average"].get(view) is not None for u in utilities) else None) for view in VIEWS}
    marginal = {view: _median_or_none(u["marginal"].get(view) for u in utilities) for view in VIEWS}
    left_out = [f"{u['utility']}: {u['marginal_reason']}" for u in utilities if u.get("marginal_reason")]
    return {"available": True, "utilities": utilities, "notes": notes, "reasons": [],
            "average": average, "marginal": marginal, "marginal_left_out": left_out,
            "estimated_energy": any(u.get("estimated_energy") for u in utilities),
            "interim": any(u.get("interim") for u in utilities)}


# ---------------------------------------------------------------------------------------------------------------------
# Spark gap, break-even COP and the plain-words result
# ---------------------------------------------------------------------------------------------------------------------

def _ratio(top: Optional[float], bottom: Optional[float]) -> Optional[float]:
    return None if top is None or bottom is None or bottom <= 0 else top / bottom


def verdict(break_even: Optional[float], cop: Optional[dict]) -> Optional[str]:
    """heat_pump_cheaper when both heat pump types' seasonal COP is above the break-even COP, depends_on_heat_pump when
    only the cold-climate type's is, furnace_cheaper when neither is (decision 157)."""
    if break_even is None or not cop:
        return None
    if cop["standard"] > break_even:
        return "heat_pump_cheaper"
    if cop["cold_climate"] > break_even:
        return "depends_on_heat_pump"
    return "furnace_cheaper"


def verdict_text(code: Optional[str], fuel: str) -> Optional[str]:
    furnace = FURNACE_WORDS[fuel]
    return {"heat_pump_cheaper": f"A heat pump costs less to run than {furnace}.",
            "depends_on_heat_pump": f"Depends on the heat pump: a cold-climate heat pump costs less to run than "
                                    f"{furnace}; a standard one does not.",
            "furnace_cheaper": f"{furnace[0].upper()}{furnace[1:]} costs less to run than either heat pump."}.get(code)


def _efficiencies(config: dict, customer: str, fuel: str) -> list[dict]:
    if customer == "residential":
        item = config["efficiency"]["residential"][fuel]
        return [{"id": fuel, "value": float(item["value"]), "measure": item.get("measure"), "label": item.get("label")}]
    return [{"id": item["id"], "value": float(item["value"]), "measure": item.get("measure"),
             "label": item.get("label")} for item in config["efficiency"]["commercial"]["gas"]]


def _round(value: Optional[float], digits: int) -> Optional[float]:
    return None if value is None else round(value, digits)


def _price(cents: Optional[float], kwh_per_gj: float) -> Optional[dict]:
    if cents is None:
        return None
    return {"cents_per_kwh": round(cents, 4), "dollars_per_gj": round(cents * kwh_per_gj / 100, 4)}


def compare(region: str, customer: str, fuel: str, electricity: dict, fuel_prices: dict, config: dict) -> dict:
    """One table row: both prices, the spark gap, the break-even COP and, for homes, the realistic COP and result."""
    kwh_per_gj = float(config["kwh_per_gj"])
    efficiencies = _efficiencies(config, customer, fuel)
    city = (config["realistic_cop"].get("provinces") or {}).get(region) if customer in (
        config["realistic_cop"].get("applies_to") or []) else None
    cop = ({"city": city, **config["realistic_cop"]["cities"][city]} if city else None)
    row = {"region": region, "region_name": rm.PROVINCE_NAMES.get(region, region), "fuel": fuel,
           "fuel_label": FUEL_LABELS[fuel], "efficiency": efficiencies, "realistic_cop": cop,
           "reasons": [], "labels": []}
    if not electricity["available"]:
        row["reasons"].extend(f"Electricity: {reason}" for reason in electricity["reasons"])
    if not fuel_prices["available"]:
        row["reasons"].extend(f"{FUEL_LABELS[fuel]}: {reason}" for reason in fuel_prices["reasons"])
    row["status"] = "ok" if electricity["available"] and fuel_prices["available"] else "not_available"
    if electricity.get("estimated_energy"):
        row["labels"].append("estimated_energy")
    if electricity.get("interim") or fuel_prices.get("interim"):
        row["labels"].append("interim_rates")
    if region in TERRITORIES:
        row["labels"].append("before_subsidies")
    row["views"] = {}
    if row["status"] != "ok":
        return row
    if fuel == "heating_oil" and fuel_prices.get("status") == "E":
        row["labels"].append("oil_use_with_caution")
    for view in VIEWS:
        if view == "after_subsidy" and region not in TERRITORIES:
            continue
        fuel_view = "without_tax" if view == "after_subsidy" else view
        parts: dict[str, Any] = {"missing": []}
        for part in ("average", "marginal"):
            power, other = electricity[part].get(view), fuel_prices[part].get(fuel_view)
            gap = _ratio(power, other)
            parts.setdefault("electricity", {})[part] = _price(power, kwh_per_gj)
            parts.setdefault("fuel", {})[part] = _price(other, kwh_per_gj)
            parts.setdefault("spark_gap", {})[part] = _round(gap, 3)
            parts.setdefault("break_even_cop", {})[part] = (
                None if gap is None else {item["id"]: round(gap * item["value"], 2) for item in efficiencies})
            if power is None:
                parts["missing"].append(f"electricity {part} price {VIEW_TEXT[view].lower()}")
            if other is None:
                parts["missing"].append(f"{FUEL_LABELS[fuel].lower()} {part} price {VIEW_TEXT[fuel_view].lower()}")
        if cop and parts["spark_gap"]["average"] is not None:
            # Decision 161: the result uses the average price; a note says when the marginal price points elsewhere.
            efficiency = efficiencies[0]["value"]
            code = verdict(parts["spark_gap"]["average"] * efficiency, cop)
            marginal_gap = parts["spark_gap"]["marginal"]
            marginal_code = None if marginal_gap is None else verdict(marginal_gap * efficiency, cop)
            parts["verdict"] = {"code": code, "text": verdict_text(code, fuel), "marginal_code": marginal_code,
                                "marginal_note": None if marginal_code in (None, code) else
                                "At the marginal prices (the next unit of heat) the result would be: "
                                + verdict_text(marginal_code, fuel)}
        row["views"][view] = parts
    return row


# ---------------------------------------------------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------------------------------------------------

def _brief_utility(entry: dict, kwh_per_gj: float) -> dict:
    out = {"utility": entry["utility"], "records": entry["records"],
           "models": [m["label"] for m in entry.get("models") or [entry["model"]]],
           "average": {view: _price(value, kwh_per_gj) for view, value in entry["average"].items() if value is not None},
           "marginal": {view: _price(value, kwh_per_gj) for view, value in entry["marginal"].items()
                        if value is not None}}
    for key in ("choice", "marginal_reason", "heating_values"):
        if entry.get(key):
            out[key] = entry[key]
    if entry.get("estimated_energy"):
        out["estimated_energy"] = True
    if entry.get("interim"):
        out["interim"] = True
    return out


def _prices_out(prices: dict, kwh_per_gj: float) -> dict:
    out = {"available": prices["available"], "reasons": prices.get("reasons") or [],
           "notes": prices.get("notes") or [],
           "utilities": [_brief_utility(u, kwh_per_gj) for u in prices.get("utilities") or []]}
    if prices.get("marginal_left_out"):
        out["marginal_left_out"] = prices["marginal_left_out"]
    return out


def _oil_out(oil: dict) -> dict:
    keys = ("available", "reasons", "month", "cents_per_litre", "geo", "vector", "status", "release_time",
            "kwh_per_litre", "age_months", "tax_lines", "tax_factor")
    return {key: oil[key] for key in keys if key in oil}


def gas_runs(rates: Union[list, dict], crosswalk: dict, usage_levels: dict, taxes: dict, config: dict, as_of: date,
             regions: Iterable[str], **model_options: Any) -> dict:
    """The gas builds: one per published heating value among the live m3 records, one for GJ-billed utilities, with
    each m3 record's (value, entry id) and each (province, utility)'s values."""
    rows = rates.get("records", []) if isinstance(rates, dict) else list(rates)
    wanted = set(regions)
    live = [r for r in rm.latest_live_records(rows) if r.get("utility_type") == "gas" and r.get("province") in wanted]
    record_values = {r.get("id"): heating_value(r, config) for r in live if rm.gas_volume_unit([r]) == "m3"}
    utility_values: dict[tuple, set[float]] = defaultdict(set)
    by_value: dict[float, set[str]] = defaultdict(set)
    for record in live:
        if record.get("id") in record_values:
            value = record_values[record["id"]][0]
            by_value[value].add(record["province"])
            utility_values[(record["province"], record.get("utility_name"))].add(value)
    gj_regions = {r["province"] for r in live if rm.gas_volume_unit([r]) == "GJ"}
    runs = []
    for value, provinces in sorted(by_value.items()):
        runs.append({"mj_per_m3": value, "result": rm.build_models(
            rates, crosswalk, gas_levels(usage_levels, config, value), taxes, provinces=sorted(provinces),
            fuels=("gas",), as_of=as_of, exact_costs=True, **model_options)})
    if gj_regions:
        fallback = float(config["gas_heating_values"]["fallback"]["mj_per_m3"])
        runs.append({"mj_per_m3": None, "result": rm.build_models(
            rates, crosswalk, gas_levels(usage_levels, config, fallback), taxes, provinces=sorted(gj_regions),
            fuels=("gas",), as_of=as_of, exact_costs=True, **model_options)})
    return {"runs": runs, "record_values": record_values, "utility_values": dict(utility_values)}


def build_spark_gap(rates: Union[list, dict], crosswalk: dict, usage_levels: dict, taxes: dict, config: dict,
                    oil_prices: Optional[dict], *, oil_problem: Optional[str] = None,
                    as_of: Union[date, str, None] = None, input_label: str = "site/data/rates.json",
                    **model_options: Any) -> dict:
    """The spark gap document for every region and customer type (method SG-1).

    ``model_options`` pass through to representative_models.build_models (for example archetypes, market_documents,
    block_periods, percentage_riders, subsidies); ``oil_prices`` is the heating-oil price document or None (then
    ``oil_problem`` says why)."""
    problems = config_problems(config)
    if problems:
        raise ValueError("invalid spark gap inputs: " + "; ".join(problems))
    if oil_prices is not None and oil_price_problems(oil_prices):
        oil_problem = "; ".join(oil_price_problems(oil_prices))
        oil_prices = None
    as_of_date = rm._as_of(as_of)
    kwh_per_gj = float(config["kwh_per_gj"])
    base = rm.build_models(rates, crosswalk, electricity_levels(usage_levels, config), taxes, provinces=REGIONS,
                           fuels=("electricity",), as_of=as_of_date, exact_costs=True, input_label=input_label,
                           **model_options)
    following = rm.build_models(rates, crosswalk, electricity_levels(usage_levels, config, 1.0), taxes,
                                provinces=REGIONS, fuels=("electricity",), as_of=as_of_date, exact_costs=True,
                                input_label=input_label, **model_options)
    gas_regions = {region for customer in CUSTOMERS for region, fuel in config["comparison_fuels"][customer].items()
                   if fuel == "gas"}
    gas_context = gas_runs(rates, crosswalk, usage_levels, taxes, config, as_of_date, gas_regions, **model_options)
    customers = []
    for customer in CUSTOMERS:
        point = config["points"][customer]
        rows = []
        for region in REGIONS:
            fuel = config["comparison_fuels"][customer].get(region)
            if fuel is None:
                continue
            power = electricity_region(region, customer, base, following, config)
            if fuel == "gas":
                other = gas_region(region, customer, gas_context, config)
                fuel_out = _prices_out(other, kwh_per_gj)
            else:
                other = oil_region(region, config, oil_prices, oil_problem, taxes, as_of_date)
                fuel_out = _oil_out(other)
            row = compare(region, customer, fuel, power, other, config)
            row["electricity"] = _prices_out(power, kwh_per_gj)
            row["fuel_prices"] = fuel_out
            rows.append(row)
        customers.append({"id": customer, "label": point.get("label"), "point": {
            "electricity_kwh": point["electricity"]["kwh"], "electricity_kw": point["electricity"]["kw"],
            "electricity_level": point["electricity"]["level"], "average_energy_gj": point["average_energy_gj"],
            "gas_marginal": point["gas_marginal"]}, "rows": rows})
    oil_months = sorted({row["fuel_prices"].get("month") for c in customers for row in c["rows"]
                         if row["fuel"] == "heating_oil" and row["fuel_prices"].get("month")})
    return {
        "version": 1,
        "kind": "spark_gap",
        "method": METHOD,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "as_of": as_of_date.isoformat(),
        "input": {"source": input_label, "config": "data/models/spark_gap.json",
                  "rates_generated_at": base["input"].get("rates_generated_at"),
                  "latest_record_created_at": base["input"].get("latest_record_created_at"),
                  "model_method_version": base.get("method_version"),
                  "oil_prices": {"file": "data/fuel/heating_oil_prices.json",
                                 "retrieved_at": (oil_prices or {}).get("retrieved_at"), "months": oil_months,
                                 "problem": oil_problem}},
        "views": dict(VIEW_TEXT),
        "units": {"headline": "cents per kWh", "alongside": "$ per GJ", "kwh_per_gj": kwh_per_gj},
        "assumptions": {key: config.get(key) for key in (
            "decided", "basis", "kwh_per_gj_source", "points", "comparison_fuels", "gas_heating_values",
            "heating_oil", "efficiency", "realistic_cop", "utility_choices", "verdicts")},
        "customers": customers,
    }


def write_spark_gap(path: Union[str, Path, None] = None, *, rates: Any = None, crosswalk: Optional[dict] = None,
                    usage_levels: Optional[dict] = None, taxes: Optional[dict] = None, config: Optional[dict] = None,
                    oil_path: Union[str, Path, None] = None, **kwargs: Any) -> dict:
    """Build from the repository inputs (any argument overrides) and write the document atomically."""
    oil_prices, oil_problem = None, None
    try:
        oil_prices = load_json(oil_path or OIL_PRICES_PATH)
    except (OSError, ValueError) as exc:
        oil_problem = f"heating-oil price file unavailable ({type(exc).__name__})"
        logger.warning("Spark gap: %s", oil_problem)
    result = build_spark_gap(rm.load_rates() if rates is None else rates, crosswalk or rm.load_crosswalk(),
                             usage_levels or rm.load_usage_levels(), taxes or rm.load_taxes(),
                             config or load_config(), oil_prices, oil_problem=oil_problem, **kwargs)
    target = Path(path or OUTPUT_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    try:
        tmp.write_text(json.dumps(result, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n",
                       encoding="utf-8", newline="\n")
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    return result


def spark_gap_problems(root: Path, today: date) -> list[str]:
    """Model monitoring's spark_gap check (decisions 143 and 152): the reviewed inputs are valid and were checked
    within a year, the published file is valid and not older than the models (a failed build keeps the previous file),
    and every heating-oil price is at most max_lag_months old."""
    config = load_json(root / "data" / "models" / "spark_gap.json")
    problems = [f"Reviewed spark gap inputs are invalid: {problem}" for problem in config_problems(config)]
    if problems:
        return problems
    problems.extend(f"Reviewed spark gap input checked more than {config['reviews_max_age_days']} days ago: {item}"
                    for item in stale_reviews(config, today))
    path = root / "site" / "data" / "spark_gap.json"
    if not path.exists():
        problems.append("site/data/spark_gap.json is missing: the spark gap has not been built")
    else:
        document = load_json(path)
        if (not isinstance(document, dict) or document.get("version") != 1 or document.get("kind") != "spark_gap"
                or not isinstance(document.get("customers"), list) or not document.get("generated_at")):
            problems.append("site/data/spark_gap.json is not a valid spark gap file")
        else:
            models = load_json(root / "site" / "data" / "representative_models.json")
            if datetime.fromisoformat(document["generated_at"]) < datetime.fromisoformat(models["generated_at"]):
                problems.append("site/data/spark_gap.json is older than the representative models: its last build "
                                "failed (see 'Refresh spark gap comparison' or the export log)")
    lag = int(config["heating_oil"]["max_lag_months"])
    oil_path = root / "data" / "fuel" / "heating_oil_prices.json"
    if not oil_path.exists():
        return problems + ["data/fuel/heating_oil_prices.json is missing: run scripts/fetch_heating_oil.py"]
    oil = load_json(oil_path)
    issues = oil_price_problems(oil)
    if issues:
        return problems + [f"Heating-oil price file: {issue}" for issue in issues]
    for region, series_id in sorted(config["heating_oil"]["series"].items()):
        latest = latest_oil_month(oil, series_id)
        if latest is None:
            problems.append(f"No usable heating-oil price for {region}")
        elif months_between(latest[0], today) > lag:
            problems.append(f"The {region} heating-oil price is from {latest[0]}, more than {lag} months old: check "
                            "'Refresh heating-oil prices' in the Monthly Scrape log")
    return problems


def format_summary(result: dict) -> str:
    lines = [f"Spark gap {result['method']} as of {result['as_of']} (average with tax; break-even COP)"]
    for customer in result["customers"]:
        lines.append(f"  {customer['label']}:")
        for row in customer["rows"]:
            if row["status"] != "ok":
                lines.append(f"    {row['region']} {row['fuel']}: not available - {'; '.join(row['reasons'])[:160]}")
                continue
            view = row["views"].get("with_tax") or {}
            gap = (view.get("spark_gap") or {}).get("average")
            cop = (view.get("break_even_cop") or {}).get("average")
            result_code = (view.get("verdict") or {}).get("code") or "-"
            power = ((view.get("electricity") or {}).get("average") or {}).get("cents_per_kwh")
            other = ((view.get("fuel") or {}).get("average") or {}).get("cents_per_kwh")
            lines.append(f"    {row['region']} {row['fuel']}: {power} vs {other} c/kWh, gap {gap}, break-even {cop}, "
                         f"{result_code}{' [' + ', '.join(row['labels']) + ']' if row['labels'] else ''}")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Spark gap comparison by region (method SG-1).")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true", help="build and write the spark gap file")
    action.add_argument("--dry-run", action="store_true", help="build and print a summary; write nothing")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--as-of", default=None, help="evaluation date (default today, UTC)")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        if args.build:
            result = write_spark_gap(args.output, as_of=args.as_of)
        else:
            oil_prices, oil_problem = None, None
            try:
                oil_prices = load_json(OIL_PRICES_PATH)
            except (OSError, ValueError) as exc:
                oil_problem = f"heating-oil price file unavailable ({type(exc).__name__})"
            result = build_spark_gap(rm.load_rates(), rm.load_crosswalk(), rm.load_usage_levels(), rm.load_taxes(),
                                     load_config(), oil_prices, oil_problem=oil_problem, as_of=args.as_of)
    except Exception as exc:  # the previous file stays in place (atomic write)
        logger.exception("Spark gap build failed; %s left unchanged", args.output)
        print(f"Spark gap build FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(format_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
