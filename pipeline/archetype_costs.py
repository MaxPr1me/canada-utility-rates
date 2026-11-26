"""Simulated building archetype costs (method AC-1): price each BTAP run with the tariffs stored today.

Owner decisions 86-114 (2026-11-24) and 166-167 (2026-11-26). Each of the owner's 68 simulated NECB 2020 buildings
(``pipeline.archetype_profiles``) is priced month by month over its simulated year with the live tariffs stored for the
city named in its weather file (Toronto: Toronto Hydro and Enbridge Gas's EGD rate zone; Calgary: ENMAX Power with ENMAX
Energy's Rate of Last Resort or the pool price, and ATCO Gas South), in the rate class its own simulated load qualifies
for. The reviewed inputs are ``data/models/archetypes.json``; charges are classified with the representative models'
own rules (``representative_models._prepare``: conditional, ended and reference-customer charges), then priced with
each month's actual days, energy, time-of-use split, demand and ratchet.

The result, ``site/data/archetype_costs.json``, is a labelled SIMULATED comparison: never a bill, never live coverage,
and never mixed into the representative models, Across-Canada, Compare, Rate History or the model change history
(AGENTS.md safeguard 8, owner decisions 104-105).

Failure behaviour: invalid reviewed inputs or unreadable simulations raise ``ValueError`` (the export keeps the previous
file and model monitoring reports it); a fuel whose class, charges or market energy cannot be settled is "not
computable" with its reasons, and such a run has no total.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import logging
import math
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from pipeline import archetype_profiles as ap
from pipeline import representative_models as rm
from scrapers.utils.market_pricing import load_shape_price

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "models" / "archetypes.json"
SPARK_GAP_CONFIG_PATH = ROOT / "data" / "models" / "spark_gap.json"
OUTPUT_PATH = ROOT / "site" / "data" / "archetype_costs.json"
MODELS_PATH = ROOT / "site" / "data" / "representative_models.json"
MARKET_PATHS = {"ON": ROOT / "site" / "data" / "market_pricing_ontario.json",
                "AB": ROOT / "site" / "data" / "market_pricing_alberta.json"}
METHOD = "AC-1"
LABEL = "SIMULATED"
CITIES = {"Toronto": "ON", "Calgary": "AB"}
CLASS_KINDS = ("demand_range", "monthly_tests")
TESTS = ("kva_months_over", "kwh_months_at_least", "otherwise")
VOLUME_UNITS = ("m3", "GJ")
BANDS = ("commercial_small", "commercial_medium", "commercial_large", "commercial_xlarge")
DATE_KEYS = ("checked", "reviewed")
KWH_PER_GJ = ap.J_PER_GJ / ap.J_PER_KWH
REPO_BLOB = "https://github.com/MaxPr1me/canada-utility-rates/blob/main/"
# Charge groups as the tab names them: the models' buckets in words that fit electricity and gas alike.
GROUP_TEXT = {"fixed": "Fixed charges (service, administration)", "energy": "Energy (supply or commodity)",
              "distribution_volumetric": "Delivery charges per unit used", "demand": "Demand charges (per kW or kVA)",
              "transmission": "Transmission charges", "regulatory": "Regulatory charges", "riders": "Rate riders",
              "carbon": "Carbon charges", "other": "Other charges"}
SUPPLY_TEXT = {"rpp_tou": "Regulated Price Plan, time-of-use", "market": "Ontario market price plus Class B GA (estimated)",
               "rate_of_last_resort": "Rate of Last Resort", "pool": "Alberta pool price (estimated)",
               "utility": "Utility supply"}
_DASHES = re.compile(r"[\u2010-\u2015\u2212]")
_PathLike = Union[str, Path, None]


def load_json(path: Union[str, Path]) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _norm(text: Any) -> str:
    """Lower-case text with dashes as '-' and single spaces, for comparing reviewed quotes with stored wording."""
    return re.sub(r"\s+", " ", _DASHES.sub("-", str(text or ""))).strip().lower()


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _walk(value: Any, path: str = "") -> Iterable[tuple[str, dict]]:
    if isinstance(value, dict):
        yield path, value
        for key, item in value.items():
            yield from _walk(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")


def _hour_ranges_problem(ranges: Any) -> Optional[str]:
    if not isinstance(ranges, list) or not ranges:
        return "needs [start, end] hour ranges"
    taken: set[int] = set()
    for pair in ranges:
        if (not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(v, int) for v in pair)
                or not 0 <= pair[0] < pair[1] <= 24):
            return f"invalid hour range {pair!r}"
        hours = set(range(pair[0], pair[1]))
        if hours & taken:
            return f"overlapping hour range {pair!r}"
        taken |= hours
    return None


def config_problems(config: Any) -> list[str]:
    """Problems that make the reviewed archetype inputs unusable; an empty list means valid."""
    if not isinstance(config, dict):
        return ["archetypes.json is not a JSON object"]
    problems: list[str] = []
    if config.get("method") != METHOD or config.get("label") != LABEL:
        problems.append(f"method must be {METHOD} and label {LABEL}")
    if not isinstance(config.get("reviews_max_age_days"), int) or config["reviews_max_age_days"] <= 0:
        problems.append("reviews_max_age_days must be a positive integer")
    locations = config.get("locations") or {}
    if set(locations) != set(CITIES):
        problems.append(f"locations must be exactly {sorted(CITIES)}")
    classes = config.get("electricity_classes") or {}
    for city, province in CITIES.items():
        location = locations.get(city) or {}
        if location.get("province") != province:
            problems.append(f"{city}: province must be {province}")
        utility = (location.get("electricity") or {}).get("utility")
        rules = classes.get(utility) if isinstance(utility, str) else None
        if not isinstance(rules, dict) or rules.get("kind") not in CLASS_KINDS:
            problems.append(f"{city}: electricity utility {utility!r} has no class rules")
        elif rules["kind"] == "demand_range":
            codes = rules.get("tariff_codes")
            quotes = rules.get("quotes") or {}
            apartments = rules.get("apartments") or {}
            if not isinstance(codes, list) or not codes or set(quotes) != set(codes):
                problems.append(f"{utility}: tariff_codes and quotes must name the same classes")
            if not isinstance(apartments.get("tariff_codes"), list) or not apartments["tariff_codes"] \
                    or not set(apartments["tariff_codes"]) <= set(codes or []) or not apartments.get("quote"):
                problems.append(f"{utility}: apartments needs tariff_codes among the classes and a quote")
        else:
            tests = rules.get("tests")
            if not isinstance(tests, list) or not tests or (tests[-1] or {}).get("test") != "otherwise":
                problems.append(f"{utility}: tests must end with an 'otherwise' test")
            for test in tests or []:
                ok = isinstance(test, dict) and test.get("test") in TESTS and test.get("tariff_code") and test.get("quote")
                if ok and test["test"] != "otherwise":
                    limit = test.get("kva" if test["test"] == "kva_months_over" else "kwh")
                    ok = _number(limit) and limit > 0 and isinstance(test.get("months"), int) and 1 <= test["months"] <= 12
                if not ok:
                    problems.append(f"{utility}: invalid class test {test!r}")
        gas = location.get("gas") or {}
        if not isinstance(gas.get("utility"), str) or gas.get("volume_unit") not in VOLUME_UNITS:
            problems.append(f"{city}: gas needs a utility and a volume_unit in {VOLUME_UNITS}")
    for name, entry in ((config.get("apartments") or {}).get("building_types") or {}).items():
        units = (entry or {}).get("dwelling_units")
        if not isinstance(units, int) or units <= 6:
            problems.append(f"apartment {name}: dwelling_units must be an integer above 6 (the class wording used is "
                            "for buildings of more than six units)")
    rpp = ((config.get("supply") or {}).get("ON") or {}).get("rpp") or {}
    if not (_number(rpp.get("max_demand_kw")) and _number(rpp.get("max_annual_kwh"))
            and rpp.get("plan") == "tou" and isinstance(rpp.get("energy_record"), str)):
        problems.append("supply.ON.rpp needs max_demand_kw, max_annual_kwh, plan 'tou' and energy_record")
    holidays = config.get("holidays") or {}
    for key, entry in holidays.items():
        try:
            ap.holiday_dates((entry or {}).get("rules") or [], weekend_rule=(entry or {}).get("weekend_rule"))
        except (ValueError, TypeError) as exc:
            problems.append(f"holidays {key}: {exc}")
    for key, entry in (config.get("clock_periods") or {}).items():
        if key == "decided":
            continue
        seasons = (entry or {}).get("seasons") or {}
        months = sorted(month for values in seasons.values() for month in values or [])
        if months != list(range(1, 13)):
            problems.append(f"clock_periods {key}: seasons must cover each month exactly once")
        for season, periods in ((entry or {}).get("weekday_hours") or {}).items():
            if season not in seasons:
                problems.append(f"clock_periods {key}: unknown season {season!r}")
            taken: list[list[int]] = []
            for period, ranges in (periods or {}).items():
                problem = _hour_ranges_problem(ranges)
                if problem:
                    problems.append(f"clock_periods {key} {season} {period}: {problem}")
                taken.extend(ranges if isinstance(ranges, list) else [])
            if _hour_ranges_problem(taken) and taken:
                problems.append(f"clock_periods {key} {season}: periods overlap")
        if (entry or {}).get("holidays") not in holidays or not isinstance((entry or {}).get("other_hours"), str) \
                or not isinstance((entry or {}).get("utility"), str) or not (entry or {}).get("stored_tou_hours"):
            problems.append(f"clock_periods {key}: needs utility, other_hours, a known holidays set and stored_tou_hours")
    for ratchet in ((config.get("demand") or {}).get("ratchets") or []):
        try:
            re.compile((ratchet or {}).get("metered_component_regex") or "")
            ok = _number(ratchet.get("fraction")) and 0 < ratchet["fraction"] <= 1 and ratchet.get("tariff_codes")
            # The stored wording must restate the reviewed fraction, so a changed percentage cannot pass unnoticed.
            ok = ok and all(isinstance(ratchet.get(key), str) and ratchet[key].strip()
                            for key in ("stored_wording", "stored_metered_wording"))
            ok = ok and f"{round(ratchet['fraction'] * 100, 4):g}%" in ratchet["stored_wording"]
        except (re.error, TypeError, AttributeError):
            ok = False
        if not ok:
            problems.append(f"invalid demand ratchet {ratchet!r}")
    loss = ((config.get("loss_factors") or {}).get("ON") or {})
    if not isinstance(loss.get("label_regex"), str) or not set(loss.get("loss_adjusted_buckets") or ["?"]) <= set(rm.BUCKETS):
        problems.append("loss_factors.ON needs label_regex and loss_adjusted_buckets among the model buckets")
    heating = (((config.get("gas") or {}).get("Enbridge Gas") or {}).get("heating_value") or {})
    if not isinstance(heating.get("spark_gap_entry"), str) or not _number((heating.get("confirmed") or {}).get("mj_per_m3")):
        problems.append("gas.Enbridge Gas.heating_value needs spark_gap_entry and confirmed.mj_per_m3")
    for path, entry in _walk(config):
        for key in DATE_KEYS:
            if key in entry and rm._as_date(entry[key]) is None:
                problems.append(f"{path}.{key} is not an ISO date")
    return problems


def stale_reviews(config: dict, today: date) -> list[str]:
    """Reviewed values checked more than reviews_max_age_days before ``today`` (model monitoring reports them)."""
    limit = int(config.get("reviews_max_age_days") or 365)
    stale = []
    for path, entry in _walk(config):
        for key in DATE_KEYS:
            when = rm._as_date(entry.get(key))
            if when is not None and (today - when).days > limit:
                stale.append(f"{path} ({key} {when.isoformat()})")
    return stale


def load_config(path: _PathLike = None) -> dict:
    """The reviewed inputs; raises ValueError when they are unusable."""
    config = load_json(path or CONFIG_PATH)
    problems = config_problems(config)
    if problems:
        raise ValueError("data/models/archetypes.json is not usable: " + "; ".join(problems))
    return config


def enbridge_heating_value(config: dict, spark_config: dict) -> tuple[Optional[float], Optional[str]]:
    """(MJ per m3, problem) of the shared reviewed Enbridge entry; a value other than the one confirmed for the stored
    edition is a problem, so the two files never disagree silently (decision 101)."""
    heating = config["gas"]["Enbridge Gas"]["heating_value"]
    entries = (((spark_config or {}).get("gas_heating_values") or {}).get("entries") or [])
    entry = next((e for e in entries if isinstance(e, dict) and e.get("id") == heating["spark_gap_entry"]), None)
    if entry is None or not _number(entry.get("mj_per_m3")):
        return None, f"spark gap heating value entry {heating['spark_gap_entry']!r} not found"
    if abs(float(entry["mj_per_m3"]) - float(heating["confirmed"]["mj_per_m3"])) > 1e-9:
        return None, (f"spark gap entry {entry['id']} gives {entry['mj_per_m3']} MJ/m3 but the stored edition's QRAM "
                      f"confirms {heating['confirmed']['mj_per_m3']}; review both")
    return float(entry["mj_per_m3"]), None


def clock_labels(periods: dict, holidays: dict) -> list[str]:
    """The period of each standard-time hour of the simulated year under one reviewed clock-period set (decision 112:
    clock time; decision 95: the tariff's holiday rule on 2006)."""
    days = ap.holiday_dates(holidays["rules"], weekend_rule=holidays["weekend_rule"])
    season_of = {month: name for name, months in periods["seasons"].items() for month in months}
    labels = []
    for _, clock in ap.hour_calendar():
        label = periods["other_hours"]
        if clock.weekday() < 5 and clock.date() not in days:
            for period, ranges in (periods["weekday_hours"].get(season_of[clock.month]) or {}).items():
                if any(start <= clock.hour < end for start, end in ranges):
                    label = period
                    break
        labels.append(label)
    return labels


def _band(crosswalk: dict, kw: float) -> Optional[str]:
    for band in BANDS:
        limits = rm._band_limits(crosswalk, band)
        if limits and limits[0] <= kw and (limits[1] is None or kw < limits[1]):
            return band
    return None


def _days(month: int) -> int:
    return calendar.monthrange(ap.YEAR, month)[1]


def _loss_factor(record: dict, label_regex: str) -> Optional[float]:
    """The record's published total loss factor whose label matches (the scraper's note; decision 113: secondary)."""
    match = rm._LOSS_NOTE_RE.search(record.get("notes") or "")
    if not match:
        return None
    found = [float(m.group("value")) for m in (rm._LOSS_VALUE_RE.match(part.strip())
                                               for part in match.group("values").split(";"))
             if m and re.search(label_regex, m.group("label"))]
    return found[0] if len(found) == 1 else None


def _brief(record: dict) -> dict:
    return {"id": record.get("id"), "utility": record.get("utility_name"), "tariff_code": record.get("tariff_code"),
            "name": record.get("name"), "effective_date": record.get("effective_date"),
            "end_date": record.get("end_date"), "source_url": record.get("source_url")}


class _Fail(Exception):
    """A fuel that cannot be priced: its reasons are published."""

    def __init__(self, reasons: Union[str, list[str]]):
        super().__init__("; ".join([reasons] if isinstance(reasons, str) else reasons))
        self.reasons = [reasons] if isinstance(reasons, str) else list(reasons)


def _wording(record: dict, quote: str, what: str) -> None:
    if _norm(quote) not in _norm(record.get("eligibility")):
        raise _Fail(f"the stored {what} wording of {record.get('utility_name')} {record.get('tariff_code')} no longer "
                    f"contains the reviewed quote \"{quote}\" (data/models/archetypes.json needs a new review)")


def _check_demand_wording(prep: dict, ratchet: Optional[dict], utility: str, record: dict) -> None:
    """Fail closed when a priced demand charge's stored note no longer states the reviewed ratchet (or metered demand
    for the non-ratcheted charge), or mentions a ratchet that no reviewed rule covers: billing demand would otherwise
    be guessed."""
    code = record.get("tariff_code")
    for item, comp in prep["priced"]:
        if item["basis"] != "kw":
            continue
        notes = _norm(comp.get("notes"))
        if ratchet is None:
            if "ratchet" in notes:
                raise _Fail(f"{item['component']} of {utility} {code} mentions a demand ratchet that no reviewed rule "
                            "covers (data/models/archetypes.json needs a new review)")
            continue
        metered = re.search(ratchet["metered_component_regex"], item["component"])
        expected = ratchet["stored_metered_wording"] if metered else ratchet["stored_wording"]
        if _norm(expected) not in notes:
            raise _Fail(f"the stored note of {item['component']} of {utility} {code} no longer contains the reviewed "
                        f"demand wording \"{expected}\" (data/models/archetypes.json needs a new review)")


def toronto_class(run: ap.ArchetypeRun, rules: dict, records: dict, apartment: bool) -> tuple[dict, dict]:
    """(record, class info) of a Toronto Hydro run: the class whose stored demand range holds its average monthly
    peak; an apartment building of more than 6 units takes a 50 kW and over class (decision 167)."""
    kw = run.average_monthly_peak_kw
    codes = rules["apartments"]["tariff_codes"] if apartment else rules["tariff_codes"]
    missing = [code for code in codes if code not in records]
    if missing:
        raise _Fail(f"no live record for class {', '.join(missing)}")
    matches = [code for code in codes if rm.record_covers_level(records[code], None, kw)]
    floor = None
    if apartment and not matches:
        lowest = min(codes, key=lambda code: rm._kw(records[code].get("demand_min_kw"), 0.0))
        if kw < rm._kw(records[lowest].get("demand_min_kw"), 0.0):
            matches, floor = [lowest], lowest
    if len(matches) != 1:
        raise _Fail(f"average monthly peak {kw:,.1f} kW fits {len(matches)} of the classes {', '.join(codes)}")
    code = matches[0]
    record = records[code]
    _wording(record, rules["quotes"][code], "class")
    reason = f"Average monthly peak {kw:,.1f} kW: \"{rules['quotes'][code]}\"."
    if apartment:
        _wording(record, rules["apartments"]["quote"], "apartment class")
        reason = (f"Apartment building of more than 6 units: \"{rules['apartments']['quote']}\" Average monthly peak "
                  f"{kw:,.1f} kW" + (f", below 50 kW, so the lowest of those classes (owner decision 167)." if floor
                                    else "."))
    return record, {"code": code, "reason": reason}


def enmax_class(run: ap.ArchetypeRun, rules: dict, records: dict, power_factor: float) -> tuple[dict, dict]:
    """(record, class info) of a Calgary run by ENMAX Power's tests over its repeating simulated year (decision 100)."""
    kva = [peak / power_factor for peak in run.monthly_peak_kw]
    for test in rules["tests"]:
        if test["test"] == "kva_months_over":
            count = sum(1 for value in kva if value > test["kva"])
            chosen = count >= test["months"]
            reason = (f"Monthly peak above {test['kva']:g} kVA in {count} of 12 months (highest {max(kva):,.1f} kVA at "
                      f"power factor {power_factor:g}): \"{test['quote']}\".")
        elif test["test"] == "kwh_months_at_least":
            count = sum(1 for value in run.monthly_kwh if value >= test["kwh"])
            chosen = count >= test["months"]
            reason = f"{count} of 12 months use {test['kwh']:,.0f} kWh or more: \"{test['quote']}\"."
        else:
            chosen, reason = True, f"Neither larger class applies: \"{test['quote']}\"."
        if chosen:
            record = records.get(test["tariff_code"])
            if record is None:
                raise _Fail(f"no live record for class {test['tariff_code']}")
            _wording(record, test["quote"], "class")
            return record, {"code": test["tariff_code"], "reason": reason}
    raise _Fail("no ENMAX Power class test applies")


class Pricer:
    """Shared inputs of one build: reviewed config, live records, documents, clock labels and market documents."""

    def __init__(self, config: dict, rates: Union[list, dict], crosswalk: dict, usage_levels: dict, taxes: dict,
                 spark_config: dict, as_of: date, market_documents: dict, archetypes: ap.ArchetypeSet):
        self.config, self.crosswalk, self.usage_levels, self.taxes = config, crosswalk, usage_levels, taxes
        self.as_of = as_of
        self.archetypes = archetypes
        rows = rates.get("records", []) if isinstance(rates, dict) else list(rates)
        self.live = [rm.apply_usage_bounds(r, crosswalk) for r in rm.latest_live_records(rows)]
        self.by_utility: dict[str, dict[str, dict]] = {}
        for record in self.live:
            self.by_utility.setdefault(record.get("utility_name") or "", {})[record.get("tariff_code")] = record
        self.pairs, _, _ = rm.compose_pairs([r for r in self.live if r.get("province") == "AB"
                                             and r.get("utility_type") == "electricity"], crosswalk)
        self.pair_threshold = float(rm.pair_config(crosswalk).get("retail_below_annual_kwh") or 250000)
        self.power_factor = float(usage_levels.get("power_factor_for_kva") or rm.DEFAULT_POWER_FACTOR)
        self.block_periods = rm.load_block_periods()["entries"]
        self.percent_entries = rm.load_percentage_riders()["entries"]
        self.mj_per_m3, self.heating_problem = enbridge_heating_value(config, spark_config)
        holidays = config["holidays"]
        self.clock = {entry["utility"]: (key, entry, clock_labels(entry, holidays[entry["holidays"]]))
                      for key, entry in config["clock_periods"].items() if key != "decided"}
        self.market = market_documents
        self.records_used: dict[str, dict] = {}
        self.market_windows: dict[str, Any] = {}

    def _context(self, province: str, fuel: str, record: dict, sector: str, volume_unit: str,
                 periods: Iterable[str] = (), drop_reference: Iterable[str] = ()) -> dict:
        ctx = rm._context(province, fuel, record.get("rate_structure"), sector, self.usage_levels, self.as_of,
                          self.block_periods, volume_unit, self.percent_entries, None)
        # Time-of-use and on-peak kWh come from the simulated hours, so every period gets a placeholder share that
        # _prepare's share check accepts; the month pricer replaces it with the period's own kWh.
        ctx["shares"] = {period: 1.0 for period in periods} or None
        ctx["shares_id"] = "archetype clock hours" if periods else None
        ctx["reference"] = [entry for entry in ctx["reference"] if entry.get("id") not in set(drop_reference)]
        return ctx

    @staticmethod
    def _periods(record: dict) -> set[str]:
        return {c.get("tou_period") for c in record.get("components") or [] if c.get("tou_period")}

    def _check_periods(self, prep: dict, utility: str) -> tuple[Optional[str], Optional[list[str]]]:
        """(clock set id, hourly labels) for the record's time-period charges, checked against the reviewed hours."""
        timed = [(item, comp) for item, comp in prep["priced"] if comp.get("tou_period")]
        if not timed:
            return None, None
        if utility not in self.clock:
            raise _Fail(f"time-period charges but no reviewed clock periods for {utility}")
        key, entry, labels = self.clock[utility]
        for item, comp in timed:
            stored = entry["stored_tou_hours"].get(comp["tou_period"])
            if stored is None or _norm(stored) != _norm(comp.get("tou_hours")):
                raise _Fail(f"the stored hours of {item['component']} ({comp.get('tou_hours')!r}) differ from the "
                            f"reviewed {key} periods (data/models/archetypes.json needs a new review)")
        return key, labels

    def price_fuel(self, run: ap.ArchetypeRun, record: dict, *, province: str, fuel: str, sector: str,
                   tax_sector: str, volume_unit: str, monthly_volume: list[float], utility: str,
                   drop_reference: Iterable[str] = (), loss: Optional[float] = None,
                   market_province: Optional[str] = None) -> dict:
        """Price one fuel's record over the 12 simulated months; raises _Fail with the reasons."""
        ctx = self._context(province, fuel, record, sector, volume_unit, self._periods(record), drop_reference)
        prep = rm._prepare(record, ctx)
        if prep["blockers"]:
            raise _Fail(prep["blockers"])
        reasons = []
        if prep["market_other"]:
            reasons.append("market-indexed charges other than energy: " + "; ".join(prep["market_other"]))
        if prep["energy_status"] == "absent":
            reasons.append("the record has no energy price")
        if any(item["basis"] == "percent" for item, _ in prep["priced"]):
            reasons.append("percentage charges are not priced in the archetype costs")
        for item, comp in prep["priced"]:
            if "tier_lower" in item and "day" in str(comp.get("tier_unit") or "").lower():
                reasons.append(f"daily block threshold not priced month by month: {item['component']}")
        if reasons:
            raise _Fail(reasons)
        _, labels = self._check_periods(prep, utility)
        split = ap.period_kwh(run, labels) if labels else None
        estimate = None
        if prep["energy_status"] == "market_pending":
            document = self.market.get(market_province or province)
            estimate = load_shape_price(document or {}, province=market_province or province,
                                        bin_kw=run.market_bin_kw, month_kwh=run.market_month_kwh, as_of=self.as_of)
            if not estimate.get("ok"):
                raise _Fail(f"market energy not estimable: {estimate.get('reason')}")
            self.market_windows[market_province or province] = estimate.get("window")
        ratchet = next((r for r in self.config["demand"].get("ratchets") or [] if r.get("utility") == utility
                        and record.get("tariff_code", "").split("+")[0] in r["tariff_codes"]), None)
        _check_demand_wording(prep, ratchet, utility, record)
        peak = max(run.monthly_peak_kw)
        buckets = set(self.config["loss_factors"]["ON"]["loss_adjusted_buckets"]) if loss else set()
        months, totals = [], [0.0] * len(prep["priced"])
        for month in range(1, 13):
            days, volume, metered = _days(month), monthly_volume[month - 1], run.monthly_peak_kw[month - 1]
            billing = max(metered, float(ratchet["fraction"]) * peak) if ratchet else metered
            groups: dict[str, float] = {}
            subtotal_parts, energy_parts = [], []
            for index, (item, comp) in enumerate(prep["priced"]):
                if item.get("months") and month not in item["months"]:
                    continue
                basis = rm.price_basis(comp, days, self.power_factor, volume_unit)
                if basis is None or basis[0] != item["basis"]:
                    raise _Fail(f"unit of {item['component']} changed while pricing")
                factor = basis[1]
                if item["basis"] == "month":
                    quantity = 1.0
                elif item["basis"] == "kw":
                    use_metered = ratchet and re.search(ratchet["metered_component_regex"], item["component"])
                    quantity = metered if use_metered else billing
                    if "demand_lower" in item:
                        quantity = max(0.0, min(quantity, item["demand_upper"]) - item["demand_lower"])
                else:
                    period = comp.get("tou_period")
                    quantity = split[month].get(period, 0.0) if period else volume
                    if "tier_lower" in item:
                        scale = {"kw": billing, "kva": billing / self.power_factor}.get(item.get("tier_scale"), 1.0)
                        upper = item["tier_upper"] * scale if math.isfinite(item["tier_upper"]) else math.inf
                        quantity = max(0.0, min(quantity, upper) - item["tier_lower"] * scale)
                    if item["bucket"] in buckets:
                        quantity *= loss
                amount = float(item["value"]) * factor * quantity
                totals[index] += amount
                groups[item["bucket"]] = groups.get(item["bucket"], 0.0) + amount
                subtotal_parts.append(amount)
                if item["basis"] == "kwh":
                    energy_parts.append(amount)
            if estimate is not None:
                quantity = volume * (loss if "energy" in buckets else 1.0)
                amount = float(estimate["month_prices"][str(month)]) * quantity
                groups["energy"] = groups.get("energy", 0.0) + amount
                subtotal_parts.append(amount)
                energy_parts.append(amount)
            months.append({"month": month, "days": days, "volume": volume, "metered_kw": metered,
                           "billing_kw": billing, "subtotal": math.fsum(subtotal_parts),
                           "energy_subtotal": math.fsum(energy_parts), "groups": groups})
        annual_volume = math.fsum(monthly_volume)
        lines, skipped = rm.tax_lines(self.taxes, province, fuel, tax_sector,
                                      annual_volume / 12 if fuel == "electricity" else None,
                                      run.average_monthly_peak_kw if fuel == "electricity" else None, self.as_of)
        line_totals = [0.0] * len(lines)
        for entry in months:
            entry["with_tax"], amounts = rm.apply_tax_lines(entry["subtotal"], entry["energy_subtotal"], lines)
            line_totals = [a + b for a, b in zip(line_totals, amounts)]
        for record_part in self._parts(record):
            self.records_used[str(record_part.get("id"))] = _brief(record_part)
        charges = [{"component": item["component"], "bucket": item["bucket"], "value": item["value"],
                    "unit": item["unit"], "tou_period": comp.get("tou_period"), "annual": round(total, 2),
                    "reason": item.get("reason"), "source_url": comp.get("source_url") or record.get("source_url")}
                   for (item, comp), total in zip(prep["priced"], totals)]
        if estimate is not None:
            charges.append({"component": "Estimated market energy" + (" (Class B Global Adjustment included)"
                                                                      if province == "ON" else ""),
                            "bucket": "energy", "value": estimate["price_per_kwh"], "unit": "$/kWh", "tou_period": None,
                            "annual": round(math.fsum(float(estimate["month_prices"][str(m)]) * monthly_volume[m - 1]
                                                      * (loss if "energy" in buckets else 1.0) for m in range(1, 13)), 2),
                            "reason": "estimated", "source_url": None})
        excluded = [{"component": item["component"], "reason": item.get("reason")} for item in prep["items"]
                    if item.get("status") == "excluded"]
        return {"months": months, "lines": lines, "line_totals": line_totals, "skipped": skipped,
                "charges": charges, "excluded": excluded, "estimate": estimate, "annual_volume": annual_volume}

    def _parts(self, record: dict) -> list[dict]:
        ids = str(record.get("id") or "").split("+")
        found = [r for r in self.live if str(r.get("id")) in ids]
        return found or [record]


def _round_months(months: list[dict], electric: bool) -> list[dict]:
    out = []
    for m in months:
        entry = {"month": m["month"], "days": m["days"], "volume": round(m["volume"], 3)}
        if electric:
            entry.update(metered_kw=round(m["metered_kw"], 2), billing_kw=round(m["billing_kw"], 2))
        entry.update(groups={key: round(value, 2) for key, value in sorted(m["groups"].items())},
                     without_tax=round(m["subtotal"], 2), with_tax=round(m["with_tax"], 2))
        out.append(entry)
    return out


def _fuel_out(priced: dict, *, unit: str, utility: str, class_info: dict, supply: dict, records: list[dict],
              loss: Optional[float], extra: Optional[dict] = None) -> dict:
    months = priced["months"]
    without = math.fsum(m["subtotal"] for m in months)
    with_tax = math.fsum(m["with_tax"] for m in months)
    groups: dict[str, float] = {}
    for entry in months:
        for key, value in entry["groups"].items():
            groups[key] = groups.get(key, 0.0) + value
    out = {"status": "ok", "reasons": [], "utility": utility, "class": class_info, "supply": supply,
           "records": [_brief(r) for r in records], "unit": unit, "annual_volume": round(priced["annual_volume"], 3),
           "loss_factor": loss, "months": _round_months(months, unit == "kWh"),
           "annual": {"without_tax": round(without, 2), "with_tax": round(with_tax, 2),
                      "groups": {key: round(value, 2) for key, value in sorted(groups.items())},
                      "tax_lines": [{"name": line["name"], "kind": line["kind"], "rate": line["rate"],
                                     "amount": round(amount, 2)} for line, amount in zip(priced["lines"],
                                                                                         priced["line_totals"])]},
           "tax_not_applied": [{"name": s["name"], "reason": s["reason"]} for s in priced["skipped"]],
           "charges": priced["charges"], "excluded": priced["excluded"], "_without": without, "_with": with_tax}
    if priced["estimate"] is not None:
        estimate = priced["estimate"]
        out["estimated_energy"] = {"price_per_kwh": estimate["price_per_kwh"], "window": estimate["window"],
                                   "month_prices": estimate["month_prices"]}
    out.update(extra or {})
    return out


def _not_computable(reasons: list[str], **fields: Any) -> dict:
    return {"status": "not_computable", "reasons": reasons, **fields}


def price_electricity(pricer: Pricer, run: ap.ArchetypeRun, apartment: bool) -> dict:
    config, city = pricer.config, run.city
    location = config["locations"][city]
    utility = location["electricity"]["utility"]
    province = location["province"]
    rules = config["electricity_classes"][utility]
    records = pricer.by_utility.get(utility, {})
    kw, annual = run.average_monthly_peak_kw, run.annual_kwh
    sector = _band(pricer.crosswalk, kw) or "commercial_small"
    class_info: dict = {}
    try:
        if rules["kind"] == "demand_range":
            record, class_info = toronto_class(run, rules, records, apartment)
            rpp_cfg = config["supply"]["ON"]["rpp"]
            why = []
            if kw <= float(rpp_cfg["max_demand_kw"]):
                why.append(f"an average monthly peak of {kw:,.1f} kW ({rpp_cfg['max_demand_kw']:g} kW or less)")
            if apartment and rpp_cfg.get("residential_complex"):
                why.append("an apartment building (a residential complex)")
            if annual <= float(rpp_cfg["max_annual_kwh"]):
                why.append(f"{annual:,.0f} kWh a year ({rpp_cfg['max_annual_kwh']:,.0f} or less)")
            loss = _loss_factor(record, config["loss_factors"]["ON"]["label_regex"])
            if loss is None:
                raise _Fail(f"no published secondary-metered total loss factor in the {record.get('tariff_code')} record")
            drop: list[str] = []
            parts = [record]
            if why:
                supply = {"kind": "rpp_tou", "estimated": False, "reason": "Eligible: " + "; ".join(why) + "."}
                drop = list(rpp_cfg.get("drop_reference_entries") or [])
                if not any(c.get("component_type") in rm.ENERGY_TYPES and c.get("tou_period")
                           for c in record.get("components") or []):
                    energy = records.get(rpp_cfg["energy_record"])
                    if energy is None:
                        raise _Fail(f"no live {rpp_cfg['energy_record']} record for the RPP time-of-use prices")
                    lines = [{**c, "source_url": c.get("source_url") or energy.get("source_url")}
                             for c in energy.get("components") or []
                             if c.get("component_type") in rm.ENERGY_TYPES and c.get("tou_period")]
                    market = [c for c in record.get("components") or [] if c.get("component_type") in rm.ENERGY_TYPES
                              and c.get("charge_value") is None and c.get("market_reference")]
                    if not lines or len(market) != 1:
                        raise _Fail("the RPP time-of-use energy cannot replace the class's market energy line")
                    record = {**record, "id": f"{record.get('id')}+{energy.get('id')}", "rate_structure": "tou",
                              "components": [c for c in record["components"] if c is not market[0]] + lines}
                    parts = [records[class_info["code"]], energy]
            else:
                supply = {"kind": "market", "estimated": True,
                          "reason": (f"Not eligible for the Regulated Price Plan: an average monthly peak of {kw:,.1f} kW "
                                     f"(more than {rpp_cfg['max_demand_kw']:g} kW) and {annual:,.0f} kWh a year (more "
                                     f"than {rpp_cfg['max_annual_kwh']:,.0f})"
                                     + ("." if apartment else ", and not a residential complex."))}
            tax_sector = "residential" if apartment and config["taxes"].get("apartments_use_residential_lines") \
                else sector
            priced = pricer.price_fuel(run, record, province=province, fuel="electricity", sector=sector,
                                       tax_sector=tax_sector, volume_unit="kwh", monthly_volume=list(run.monthly_kwh),
                                       utility=utility, drop_reference=drop, loss=loss)
            return _fuel_out(priced, unit="kWh", utility=utility, class_info=class_info, supply=supply,
                             records=parts, loss=loss)
        wires, class_info = enmax_class(run, rules, records, pricer.power_factor)
        variants = pricer.pairs.get(id(wires))
        if not variants:
            raise _Fail(f"{utility} {class_info['code']} has no Rate of Last Resort pairing in crosswalk pairs")
        retail = annual < pricer.pair_threshold
        record = variants[0] if retail else variants[1]
        retail_code = (record.get("pair") or {}).get("retail_record_id")
        supply = ({"kind": "rate_of_last_resort", "estimated": False,
                   "reason": f"{annual:,.0f} kWh a year, below the Rate of Last Resort limit of "
                             f"{pricer.pair_threshold:,.0f} kWh: ENMAX Energy's Rate of Last Resort for "
                             f"{class_info['code']} sites."} if retail else
                  {"kind": "pool", "estimated": True,
                   "reason": f"{annual:,.0f} kWh a year, at or above the Rate of Last Resort limit of "
                             f"{pricer.pair_threshold:,.0f} kWh; no retailer charges or margins are included."})
        priced = pricer.price_fuel(run, record, province=province, fuel="electricity", sector=sector,
                                   tax_sector=sector, volume_unit="kwh", monthly_volume=list(run.monthly_kwh),
                                   utility=utility)
        parts = pricer._parts(record)
        out = _fuel_out(priced, unit="kWh", utility=utility, class_info=class_info, supply=supply, records=parts,
                        loss=None)
        out["retail_record_id"] = retail_code
        return out
    except _Fail as fail:
        return _not_computable(fail.reasons, utility=utility, **({"class": class_info} if class_info else {}))


def price_gas(pricer: Pricer, run: ap.ArchetypeRun) -> dict:
    config = pricer.config
    location = config["locations"][run.city]
    gas = location["gas"]
    utility, unit = gas["utility"], gas["volume_unit"]
    records = pricer.by_utility.get(utility, {})
    annual_gj = run.annual_gas_gj
    class_info: dict = {}
    try:
        if unit == "m3":
            if pricer.mj_per_m3 is None:
                raise _Fail(pricer.heating_problem or "no reviewed heating value")
            monthly = [gj * 1000 / pricer.mj_per_m3 for gj in run.monthly_gas_gj]
            record = records.get(gas["tariff_code"])
            if record is None:
                raise _Fail(f"no live {gas['tariff_code']} record")
            rules = config["gas"][utility]
            _wording(record, rules["class_quote"], "class")
            class_info = {"code": gas["tariff_code"],
                          "reason": f"\"{rules['class_quote']}\"; apartment buildings of more than six units are in "
                                    "the Rate 6 commercial sector (Enbridge, EB-2022-0200)."}
        else:
            monthly = list(run.monthly_gas_gj)
            fits = []
            for code in gas["tariff_codes"]:
                candidate = records.get(code)
                if candidate is None:
                    raise _Fail(f"no live {code} record")
                problem = rm.volume_bound_problem(candidate, annual_gj / 12, "GJ")
                if problem is None:
                    fits.append(candidate)
            if len(fits) != 1:
                raise _Fail(f"{annual_gj:,.1f} GJ a year fits {len(fits)} of {', '.join(gas['tariff_codes'])}")
            record = fits[0]
            class_info = {"code": record.get("tariff_code"),
                          "reason": f"{annual_gj:,.1f} GJ a year: \"{record.get('eligibility')}\""}
        priced = pricer.price_fuel(run, record, province=location["province"], fuel="gas", sector="commercial_medium",
                                   tax_sector="commercial_medium", volume_unit=unit, monthly_volume=monthly,
                                   utility=utility)
        extra = {"mj_per_m3": pricer.mj_per_m3} if unit == "m3" else {}
        supply_lines = sorted({c["component_name"] for c in record.get("components") or []
                               if c.get("component_type") in rm.ENERGY_TYPES and c.get("component_name")})
        supply = {"kind": "utility", "estimated": False,
                  "reason": (", ".join(supply_lines) + ": " if supply_lines else "")
                  + "the supply price for customers without a contract with a gas marketer or retailer."}
        return _fuel_out(priced, unit=unit, utility=utility, class_info=class_info, supply=supply,
                         records=pricer._parts(record), loss=None, extra=extra)
    except _Fail as fail:
        return _not_computable(fail.reasons, utility=utility, **({"class": class_info} if class_info else {}))


def _effective(fuel: dict, run: ap.ArchetypeRun) -> dict:
    if fuel.get("status") != "ok":
        return {}
    volume = fuel["annual_volume"]
    if fuel["unit"] == "kWh":
        return {"cents_per_kwh_without_tax": round(fuel["_without"] / volume * 100, 3),
                "cents_per_kwh_with_tax": round(fuel["_with"] / volume * 100, 3)}
    gj = run.annual_gas_gj
    out = {"dollars_per_gj_without_tax": round(fuel["_without"] / gj, 3),
           "dollars_per_gj_with_tax": round(fuel["_with"] / gj, 3)}
    if fuel["unit"] == "m3":
        out.update(cents_per_m3_without_tax=round(fuel["_without"] / volume * 100, 3),
                   cents_per_m3_with_tax=round(fuel["_with"] / volume * 100, 3))
    return out


def price_run(pricer: Pricer, run: ap.ArchetypeRun) -> dict:
    """One run's published entry: identity, load, each fuel's priced months and the total when every fuel prices."""
    config = pricer.config
    apartments = config["apartments"]["building_types"]
    apartment = run.building_type in apartments
    electricity = price_electricity(pricer, run, apartment)
    gas = price_gas(pricer, run) if run.heating_fuel == "NaturalGas" else None
    fuels = [electricity] + ([gas] if gas is not None else [])
    for fuel in fuels:
        fuel["effective"] = _effective(fuel, run)
    total: dict[str, Any] = {"status": "ok" if all(f["status"] == "ok" for f in fuels) else "not_computable"}
    if total["status"] == "ok":
        without = math.fsum(f["_without"] for f in fuels)
        with_tax = math.fsum(f["_with"] for f in fuels)
        total.update(without_tax=round(without, 2), with_tax=round(with_tax, 2),
                     per_m2_without_tax=round(without / run.floor_area_m2, 3),
                     per_m2_with_tax=round(with_tax / run.floor_area_m2, 3),
                     months=[{"month": m, "without_tax": round(math.fsum(f["months"][m - 1]["without_tax"]
                                                                          for f in fuels), 2),
                              "with_tax": round(math.fsum(f["months"][m - 1]["with_tax"] for f in fuels), 2)}
                             for m in range(1, 13)])
    for fuel in fuels:
        fuel.pop("_without", None)
        fuel.pop("_with", None)
    m3 = round(run.annual_gas_gj * 1000 / pricer.mj_per_m3, 1) \
        if gas is not None and gas.get("unit") == "m3" and pricer.mj_per_m3 else None
    energy_kwh = run.annual_kwh + run.annual_gas_gj * KWH_PER_GJ
    folder = "data/btap/NECB2020_Default/NECB2020_Default/"
    flag = float(config["simulations"]["quality_flag_unmet_occupied_hours"])
    return {
        "id": run.datapoint_id, "building_type": run.building_type,
        "label": config["building_labels"].get(run.building_type, run.building_type),
        "city": run.city, "province": run.province, "heating_fuel": run.heating_fuel,
        "pair": f"{run.city}|{run.building_type}", "climate_zone": run.climate_zone,
        "floor_area_m2": round(run.floor_area_m2, 1),
        "quality": {"unmet_occupied_hours": round(run.unmet_occupied_hours, 1),
                    "flagged": run.unmet_occupied_hours > flag},
        "apartment": ({"dwelling_units": apartments[run.building_type]["dwelling_units"],
                       "note": config["apartments"]["note"]} if apartment else None),
        "load": {"annual_kwh": round(run.annual_kwh, 1), "max_peak_kw": round(run.max_peak_kw, 2),
                 "average_monthly_peak_kw": round(run.average_monthly_peak_kw, 2),
                 "annual_gas_gj": round(run.annual_gas_gj, 3), "annual_gas_m3": m3,
                 "eui_ekwh_per_m2": round(energy_kwh / run.floor_area_m2, 1),
                 "monthly_kwh": [round(v, 1) for v in run.monthly_kwh],
                 "monthly_peak_kw": [round(v, 2) for v in run.monthly_peak_kw],
                 "monthly_gas_gj": [round(v, 3) for v in run.monthly_gas_gj]},
        "electricity": electricity, "gas": gas, "total": total,
        "sources": {"timestep_csv": f"{REPO_BLOB}{folder}parametric/runs/{run.datapoint_id}/timestep.csv",
                    "results_workbook": f"{REPO_BLOB}{folder}results/output.xlsx"},
    }


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def hourly_fingerprint(archetypes: ap.ArchetypeSet) -> str:
    """SHA-256 of every run's hourly kWh and monthly gas (rounded to six decimals), which the costs read beyond the
    values ``archetype_profiles.archetype_fingerprint`` covers."""
    return _digest([[run.datapoint_id, [round(v, 6) for v in run.hourly_kwh], [round(v, 6) for v in run.monthly_gas_gj]]
                    for run in sorted(archetypes.runs, key=lambda r: r.datapoint_id)])


def method_text(config: dict) -> list[str]:
    return [
        config["basis"],
        "Class: Toronto Hydro by the average of the 12 monthly highest 15-minute demands against each class's stored "
        "limits (apartment buildings of more than 6 units on a 50 kW and over class, decision 167); ENMAX Power by its "
        "own tests over the repeating simulated year (more than 150 kVA in two months: D310; 5,000 kWh in six months: "
        "D300; otherwise D200). Gas: Enbridge Rate 6 (apartments included, per Enbridge's own rate-class evidence); ATCO "
        "Gas Low or Mid Use by annual GJ.",
        "Supply: in Toronto, Regulated Price Plan time-of-use prices where O. Reg. 95/05 makes the account eligible, "
        "otherwise the market price plus the Class B Global Adjustment; in Calgary, ENMAX Energy's Rate of Last Resort "
        "below 250,000 kWh a year, otherwise pool energy. Market energy is estimated from each building's own load "
        "shape and the observed market history of the latest 60 complete months (labelled estimated).",
        "Ontario charges on energy, per-kWh transmission and per-kWh regulatory charges use loss-adjusted kWh (the "
        "record's published secondary-metered total loss factor), as the OEB bill calculator does; the representative "
        "models do not apply loss factors.",
        "Clock time: time-of-use and on-peak periods read local clock time (an hour later inside daylight saving) with "
        "each tariff's holidays on the 2006 calendar; bills follow the simulation's standard-time months.",
        "Taxes and rebates from data/models/taxes.json; the Ontario Electricity Rebate tests the average monthly peak "
        "(50 kW or less) or the annual use (250,000 kWh or less), and apartment buildings get it as residential "
        "complexes (decision 103).",
    ]


def load_market_documents() -> dict:
    """The observed market histories the estimates price with: Ontario through the models' IESO loader, Alberta as
    the models read it (load_shape_price checks each file's method); None when a file is missing or unreadable."""
    documents = {"ON": rm.load_market_document(MARKET_PATHS["ON"])[0]}
    try:
        documents["AB"] = load_json(MARKET_PATHS["AB"])
    except (OSError, ValueError) as exc:
        logger.warning("Alberta market history unavailable for the archetype costs: %s", exc)
        documents["AB"] = None
    return documents


def build_archetype_costs(rates: Union[list, dict], crosswalk: dict, usage_levels: dict, taxes: dict, config: dict,
                          spark_config: dict, as_of: Union[date, str, None] = None,
                          market_documents: Optional[dict] = None,
                          archetypes: Optional[ap.ArchetypeSet] = None) -> dict:
    """The archetype costs document (method AC-1); raises ValueError on unusable inputs (fail closed)."""
    problems = config_problems(config)
    if problems:
        raise ValueError("data/models/archetypes.json is not usable: " + "; ".join(problems))
    when = rm._as_of(as_of)
    archetypes = archetypes if archetypes is not None else ap.load_archetypes()
    if not archetypes.runs:
        raise ValueError("no validated simulated buildings: " + "; ".join(archetypes.problems[:3]))
    if market_documents is None:
        market_documents = load_market_documents()
    pricer = Pricer(config, rates, crosswalk, usage_levels, taxes, spark_config, when, market_documents, archetypes)
    runs = [price_run(pricer, run) for run in sorted(archetypes.runs, key=lambda r: (r.city, r.building_type,
                                                                                     r.heating_fuel))]
    computable = sum(1 for run in runs if run["total"]["status"] == "ok")
    return {
        "method_version": METHOD, "label": LABEL, "as_of": when.isoformat(),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "caveat": config["caveat"], "method": method_text(config), "not_applied": config["not_applied"],
        "simulation_problems": list(archetypes.problems),
        "summary": {"runs": len(runs), "computable": computable, "not_computable": len(runs) - computable,
                    "quality_flagged": sum(1 for run in runs if run["quality"]["flagged"])},
        "inputs": {
            "fingerprints": {"archetypes": ap.archetype_fingerprint(archetypes),
                             "hourly": hourly_fingerprint(archetypes), "config": _digest(config),
                             "taxes": _digest(taxes),
                             "records": _digest(sorted(pricer.records_used.values(), key=lambda r: str(r["id"])))},
            "market_windows": pricer.market_windows,
            "records": sorted(pricer.records_used.values(), key=lambda r: (str(r["utility"]), str(r["tariff_code"]))),
            "heating_value_mj_per_m3": pricer.mj_per_m3,
        },
        "buckets": {key: GROUP_TEXT.get(key, rm.BUCKET_TEXT.get(key, key)) for key in rm.BUCKETS},
        "runs": runs,
    }


def write_archetype_costs(path: _PathLike = None, **kwargs: Any) -> dict:
    """Build from the repository inputs (keyword arguments override them) and write the document atomically."""
    result = build_archetype_costs(
        kwargs.pop("rates", None) or rm.load_rates(), kwargs.pop("crosswalk", None) or rm.load_crosswalk(),
        kwargs.pop("usage_levels", None) or rm.load_usage_levels(), kwargs.pop("taxes", None) or rm.load_taxes(),
        kwargs.pop("config", None) or load_config(), kwargs.pop("spark_config", None) or load_json(SPARK_GAP_CONFIG_PATH),
        **kwargs)
    target = Path(path or OUTPUT_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(result, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n",
                   encoding="utf-8")
    os.replace(tmp, target)
    return result


def archetype_costs_problems(root: Path, today: date) -> list[str]:
    """Model monitoring's archetype_costs check (decision 105): the reviewed inputs are valid and recently checked, and
    the published file exists, is this method's and is no older than the representative models it was built with."""
    problems: list[str] = []
    try:
        config = load_json(root / "data" / "models" / "archetypes.json")
    except (OSError, ValueError) as exc:
        return [f"data/models/archetypes.json unreadable: {exc}"]
    problems.extend(f"Reviewed archetype input problem: {p}" for p in config_problems(config))
    if not problems:
        problems.extend(f"Reviewed archetype input checked more than {config['reviews_max_age_days']} days ago: {item}"
                        for item in stale_reviews(config, today))
    output = root / "site" / "data" / "archetype_costs.json"
    try:
        document = load_json(output)
    except (OSError, ValueError) as exc:
        return problems + [f"site/data/archetype_costs.json missing or unreadable ({type(exc).__name__}): the last "
                           "archetype build failed or never ran"]
    if not isinstance(document, dict) or document.get("method_version") != METHOD or not isinstance(
            document.get("runs"), list) or document.get("label") != LABEL:
        return problems + [f"site/data/archetype_costs.json is not a {METHOD} {LABEL} document"]
    try:
        models = load_json(root / "site" / "data" / "representative_models.json")
        if datetime.fromisoformat(str(document.get("generated_at"))) < datetime.fromisoformat(
                str(models["generated_at"])):
            problems.append("site/data/archetype_costs.json is older than the representative models: its last build "
                            "failed (see 'Refresh archetype costs' or the export log)")
    except (OSError, ValueError, KeyError, TypeError):
        problems.append("site/data/archetype_costs.json or the representative models have no readable generated_at")
    return problems


def format_summary(result: dict) -> str:
    lines = [f"Archetype costs {result['method_version']} as of {result['as_of']}: {result['summary']['computable']} of "
             f"{result['summary']['runs']} runs priced"]
    for run in result["runs"]:
        total = run["total"]
        cost = f"${total['with_tax']:>13,.2f} with tax" if total["status"] == "ok" else "not computable"
        electricity = run["electricity"]
        detail = (electricity.get("class") or {}).get("code") or "-"
        reasons = "; ".join(electricity.get("reasons") or (run.get("gas") or {}).get("reasons") or [])
        lines.append(f"  {run['city']:<8} {run['building_type']:<23} {run['heating_fuel']:<11} {detail:<18} {cost}"
                     + (f"  [{reasons[:120]}]" if reasons else ""))
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build the simulated archetype costs (method AC-1).")
    parser.add_argument("--build", action="store_true", help="build and write site/data/archetype_costs.json")
    parser.add_argument("--dry-run", action="store_true", help="build and print a summary; write nothing")
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    parser.add_argument("--as-of", default=None)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        if args.dry_run or not args.build:
            result = build_archetype_costs(rm.load_rates(), rm.load_crosswalk(), rm.load_usage_levels(),
                                           rm.load_taxes(), load_config(), load_json(SPARK_GAP_CONFIG_PATH),
                                           as_of=args.as_of)
        else:
            result = write_archetype_costs(args.output, as_of=args.as_of)
    except (OSError, ValueError, ap.ArchetypeDataError) as exc:
        logger.error("Archetype costs not built: %s", exc)
        return 1
    print(format_summary(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
