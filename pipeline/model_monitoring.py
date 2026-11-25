"""Model change history, explicit refresh receipts and read-only health checks.

Owner decision 2026-11-17: material means >=5% movement in an after-tax median.
Synthetic estimates never enter these comparisons. Monitoring is not a publication gate.
"""
from __future__ import annotations

import argparse
import calendar
import copy
import hashlib
import json
import logging
import math
import os
import re
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
HISTORY_PATH = ROOT / "site" / "data" / "model_change_history.json"
MODELS_PATH = ROOT / "site" / "data" / "representative_models.json"
QUARTERLY_PATH = ROOT / "site" / "data" / "model_cost_quarterly.json"
SCHEMA_VERSION = 1
MATERIAL_PERCENT = 5
OVERDUE_GRACE = timedelta(hours=24)
# The Monthly Scrape's monthly-price schedule (owner decisions 2026-11-20 and 2026-11-23). It scrapes only the
# registry's monthly_price_refresh utilities, so it never counts as the full refresh and gets its own cadence
# check. scrape.yml uses the same string in its schedule and in "Run scrapers".
MONTHLY_PRICE_CRON = "0 8 4 * *"
MONTHLY_PRICE_GROUP = "monthly_price_refresh"  # scrapers.registry.MONTHLY_PRICE_FLAG, the receipt's scope group

MODEL_FIELDS = (
    "id", "key", "label", "state", "provenance", "cost_basis", "energy", "coverage", "buckets",
    "tou", "tiers", "utilities", "reference_customer", "exclusions", "warnings", "block_periods",
    "fixed_charge_variants", "required_contributors",
    # Method 7T-1 territorial fields (owner decisions 2026-11-24).
    "subsidies", "interim", "percentage_riders", "shared_rate_books",
)
USAGE_FIELDS = ("id", "kwh", "kw", "quantity", "unit", "role")
LEVEL_FIELDS = USAGE_FIELDS + (
    "without_tax", "with_tax", "closest_utility", "outliers", "utilities", "withheld", "reason", "after_subsidy",
)
ASSUMPTION_FIELDS = (
    "usage_levels", "days_per_month", "power_factor_for_kva", "tou_shares", "seasons", "zone_policy",
    "statistics", "closest_utility", "outliers", "component_rules", "reference_customer",
    "fixed_charge_variants", "buckets", "pairs", "block_periods", "required_contributors",
    "usage_bounds", "taxes",
    # Method 7D-2 selection inputs (owner decisions 2026-11-20).
    "peak_month_factors", "elective_classes", "demand_bounds",
    # Method 7T-1 inputs (owner decisions 2026-11-24).
    "percentage_riders", "subsidies", "interim_rates", "shared_rate_books",
)
INPUT_FIELDS = {
    "crosswalk": ("vocabulary", "pairs", "required_contributors", "usage_bounds", "rules", "elective_classes",
                  "demand_bounds", "interim_rates", "shared_rate_books"),
    "usage_levels": (
        "days_per_month", "power_factor_for_kva", "market_benchmarks", "electricity", "gas",
        "tou_shares", "seasons", "reference_customer", "fixed_charge_variants", "peak_month_factors",
    ),
    "taxes": ("sectors", "jurisdictions"),
    "block_periods": ("entries",),
    # Reviewed percentage riders and territorial subsidies (method 7T-1): taken, like block_periods, from the loaded
    # configuration recorded in the build's assumptions, so an edit to a reviewed list is an input change.
    "percentage_riders": ("entries",),
    "subsidies": ("jurisdictions", "programs"),
}
# Inputs read from the build's assumptions (the configuration actually loaded) rather than passed by the caller.
RESULT_INPUTS = ("block_periods", "percentage_riders", "subsidies")
VOLATILE_FIELDS = {
    "generated_at", "created_at", "updated", "as_of", "generated_from", "rates_generated_at",
    "latest_record_created_at", "file", "input",
}
ORDERED_FIELDS = {"rules", "entries", "reference_customer", "fixed_charge_variants"}
# Opt-in estimates and their inputs never enter fingerprints or the change history (safeguard 8): the Phase 7E synthetic
# fields stay listed so that histories recorded before method 7S-1 still compare.
SYNTHETIC_FIELDS = {"illustrative", "illustrative_all_in", "synthetic_profiles", "simulated_profiles"}


def timestamp(value: str) -> datetime:
    """Reject ambiguous clocks instead of treating a local time as UTC."""
    if not isinstance(value, str):
        raise ValueError("monitoring timestamps must be ISO-8601 strings")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("monitoring timestamps must include a time zone")
    return parsed.astimezone(timezone.utc)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    def reject_constant(value: str) -> None:
        raise ValueError(f"{path}: non-finite JSON value {value}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject_constant)


def write_json(path: Path, value: Any) -> None:
    """Replace only a complete JSON document; retain earlier history on failure."""
    _replace_text(path, _json(value) + "\n")


def _replace_text(path: Path, text: str, newline: str | None = None) -> None:
    """Replace only a complete file; retain the earlier file on failure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_text(text, encoding="utf-8", newline=newline)
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            logger.exception("Could not remove monitoring temporary file %s", temporary)


def _pick(value: dict, keys: tuple[str, ...]) -> dict:
    return {key: value[key] for key in keys if key in value}


def _normalize(value: Any, field: str = "") -> Any:
    if isinstance(value, dict):
        return {key: _normalize(item, key) for key, item in sorted(value.items())
                if key not in VOLATILE_FIELDS | SYNTHETIC_FIELDS}
    if isinstance(value, list):
        items = [_normalize(item) for item in value]
        return items if field in ORDERED_FIELDS else sorted(items, key=_json)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite model value")
        return int(value) if value.is_integer() else value
    return value


def input_fingerprints(inputs: dict[str, dict]) -> dict[str, str]:
    """Fingerprint calculation inputs, preserving first-match rules but not synthetic settings."""
    unknown = set(inputs) - set(INPUT_FIELDS)
    if unknown:
        raise ValueError(f"unsupported model input roles: {sorted(unknown)}")
    return {name: fingerprint(_normalize(_pick(value, INPUT_FIELDS[name])))
            for name, value in sorted(inputs.items())}


def _median(summary: Any) -> float | int | None:
    if not isinstance(summary, dict) or "median" not in summary:
        raise ValueError("model cost summary has no median")
    value = summary["median"]
    if value is not None and (isinstance(value, bool) or not isinstance(value, (float, int))
                              or not math.isfinite(value)):
        raise ValueError("model median must be a finite number or null")
    return value


def _check_benchmark(value: Any) -> None:
    if value is not None and (not isinstance(value, dict) or type(value.get("available")) is not bool
                              or value.get("synthetic_profile") or value.get("simulated_profile")
                              or value.get("illustrative_only")):
        raise ValueError("invalid observed benchmark")


def semantic_models(document: dict) -> dict:
    """Project the supported export, not its timestamps, machine paths or illustrative estimates."""
    if (not isinstance(document, dict) or document.get("version") != 1
            or not isinstance(document.get("method_version"), str) or not document["method_version"]
            or not isinstance(document.get("models"), list) or not document["models"]):
        raise ValueError("unsupported or empty representative model export")
    timestamp(document["generated_at"])
    datetime.strptime(document["as_of"], "%Y-%m-%d")
    models = {}
    for model in document["models"]:
        if not isinstance(model, dict):
            raise ValueError("invalid representative model")
        model_id = model.get("id")
        if (not isinstance(model_id, str) or not model_id or model_id in models
                or model.get("provenance") != "modeled"
                or model.get("state") not in ("modeled", "single_source", "market_energy_pending", "not_computable")
                or not isinstance(model.get("levels"), list)):
            raise ValueError("invalid or duplicate representative model")
        base = _pick(model, MODEL_FIELDS)
        method = model.get("method")
        if isinstance(method, str):
            generated = model.get("generated_from") or {}
            footer = f" Generated {generated.get('as_of')} from {generated.get('input')}."
            base["method"] = method.removesuffix(footer)
        levels, benchmarks = {}, {}
        _check_benchmark(model.get("market_benchmark"))
        for level in model["levels"]:
            if not isinstance(level, dict):
                raise ValueError(f"{model_id}: invalid usage level")
            level_id = level.get("id")
            if not isinstance(level_id, str) or not level_id or level_id in levels:
                raise ValueError(f"{model_id}: invalid or duplicate usage level")
            _median(level.get("without_tax"))
            _median(level.get("with_tax"))
            levels[level_id] = _pick(level, LEVEL_FIELDS)
            benchmark = level.get("market_benchmark")
            _check_benchmark(benchmark)
            if benchmark is not None:
                if benchmark.get("available"):
                    _median(benchmark.get("without_tax"))
                    _median(benchmark.get("with_tax"))
                benchmarks[level_id] = {**_pick(level, USAGE_FIELDS), **benchmark}
        base["levels"] = levels
        models[model_id] = _normalize({
            "base": base,
            "benchmark": {"metadata": model.get("market_benchmark"), "levels": benchmarks},
        })
    return _normalize({
        "method_version": document["method_version"], "models": models,
        "assumptions": _pick(document.get("assumptions") or {}, ASSUMPTION_FIELDS),
        "coverage": document.get("coverage_report"),
        "scope": _pick(document.get("input") or {}, ("provinces", "fuels", "withheld_gas_models")),
    })


def observe_previous(path: Path) -> dict:
    """Capture the replaced generation so a missed monitoring run can be disclosed later."""
    if not path.exists():
        return {"status": "absent"}
    try:
        document = read_json(path)
        return {"status": "known", "generated_at": document["generated_at"],
                "fingerprint": fingerprint(semantic_models(document))}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        logger.warning("Previous model generation cannot be verified: %s", exc)
        return {"status": "unverified", "detail": str(exc)}


def run_identity() -> dict:
    run_id = os.environ.get("GITHUB_RUN_ID")
    repository = os.environ.get("GITHUB_REPOSITORY")
    return {
        "workflow": os.environ.get("GITHUB_WORKFLOW", "manual"),
        "id": run_id, "attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "url": f"https://github.com/{repository}/actions/runs/{run_id}" if repository and run_id else None,
    }


def generation_receipt(result: dict | None, *, previous: dict, inputs: dict[str, dict] | None = None,
                       error: str | None = None) -> dict:
    """Success comes from the producer, never from an unchanged output file."""
    if result is None and not error:
        raise ValueError("a failed generation requires an explicit error")
    receipt = {"version": SCHEMA_VERSION, "kind": "model_generation", "checked_at": utc_now(),
               "run": run_identity(), "status": "failed" if result is None else "success",
               "previous": previous, "error": error}
    if result is not None:
        model_hash = fingerprint(semantic_models(result))
        receipt.update(
            generated_at=result["generated_at"], as_of=result["as_of"], method_version=result["method_version"],
            fingerprint=model_hash,
            input_fingerprints=input_fingerprints(inputs or {}),
            change_status=("unchanged" if previous.get("fingerprint") == model_hash else
                           "initial" if previous["status"] == "absent" else "changed"),
        )
    return receipt


def save_generation_receipt(path: Path | None, result: dict | None, *, previous: dict,
                            inputs: dict[str, dict] | None = None, error: str | None = None) -> None:
    """A monitoring defect must not break the primary exporter; missing receipts stay unverified."""
    if path is None:
        return
    try:
        if result is not None and inputs is not None:
            assumptions = result["assumptions"]
            inputs = {**inputs, **{name: assumptions[name] for name in RESULT_INPUTS if name in assumptions}}
        write_json(path, generation_receipt(result, previous=previous, inputs=inputs, error=error))
    except Exception:
        logger.exception("Model generation receipt failed; monitoring cannot verify this refresh")


def _successful_generation(receipt: dict) -> None:
    """Validate producer evidence before either history recording or freshness can rely on it."""
    if (not isinstance(receipt, dict) or receipt.get("version") != SCHEMA_VERSION
            or receipt.get("kind") != "model_generation" or receipt.get("status") != "success"
            or not isinstance(receipt.get("method_version"), str) or not receipt["method_version"]
            or not isinstance(receipt.get("fingerprint"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", receipt["fingerprint"])
            or not isinstance(receipt.get("input_fingerprints"), dict) or not isinstance(receipt.get("run"), dict)):
        raise ValueError("missing, failed or invalid model generation receipt")
    timestamp(receipt["checked_at"])
    timestamp(receipt["generated_at"])
    datetime.strptime(receipt["as_of"], "%Y-%m-%d")
    for name, value in receipt["input_fingerprints"].items():
        if name not in INPUT_FIELDS or not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
            raise ValueError("invalid model input fingerprint in generation receipt")


def _cost_change(before: dict | None, after: dict | None, comparable: bool) -> dict:
    old = (before or {}).get("with_tax", {}).get("median")
    new = (after or {}).get("with_tax", {}).get("median")
    comparison, percent, material = "comparable", None, False
    if before is None or after is None or old is None or new is None:
        comparison = "availability_changed"
    elif not comparable:
        comparison = "basis_changed"
    elif old == 0:
        comparison = "from_zero" if new != 0 else "unchanged_zero"
    else:
        delta = Decimal(str(new)) - Decimal(str(old))
        fraction = delta / abs(Decimal(str(old)))
        percent = float(fraction * 100)
        if not math.isfinite(percent):
            raise ValueError("after-tax percentage is outside the finite numeric range")
        material = abs(delta) >= abs(Decimal(str(old))) * Decimal("0.05")
    return {"comparison": comparison, "after_tax_percent": percent, "material": material}


def _level_summary(level: dict | None) -> dict | None:
    if level is None:
        return None
    return {
        **_pick(level, USAGE_FIELDS + ("available", "reason", "without_tax", "with_tax")),
        "contributors": [
            _pick(row, ("utility", "cost_without_tax", "cost_with_tax"))
            for row in level.get("utilities", [])
        ],
    }


def compare_models(before: dict, after: dict) -> list[dict]:
    """Diff canonical snapshots using model ID, level ID and base/benchmark as separate identities."""
    changes = []
    context_fields = [key for key in ("method_version", "assumptions", "coverage", "scope", "input_fingerprints")
                      if before.get(key) != after.get(key)]
    if context_fields:
        changes.append({"category": "inputs", "model_id": None, "fields": context_fields,
                        "before": {key: before.get(key) for key in context_fields},
                        "after": {key: after.get(key) for key in context_fields}, "material": False})
    for model_id in sorted(before["models"].keys() | after["models"].keys()):
        old_model, new_model = before["models"].get(model_id), after["models"].get(model_id)
        if old_model is None or new_model is None:
            changes.append({"category": "model_added" if old_model is None else "model_removed",
                            "model_id": model_id, "material": False,
                            "before": (old_model or {}).get("base", {}).get("state"),
                            "after": (new_model or {}).get("base", {}).get("state")})
        for kind in ("base", "benchmark"):
            old, new = (old_model or {}).get(kind, {}), (new_model or {}).get(kind, {})
            metadata_fields = sorted(key for key in old.keys() | new.keys()
                                     if key != "levels" and old.get(key) != new.get(key))
            if metadata_fields and old_model is not None and new_model is not None:
                changes.append({"category": "structure", "model_id": model_id, "kind": kind,
                                "fields": metadata_fields, "material": False,
                                "before": {key: old.get(key) for key in metadata_fields},
                                "after": {key: new.get(key) for key in metadata_fields}})
            old_levels, new_levels = old.get("levels", {}), new.get("levels", {})
            for level_id in sorted(old_levels.keys() | new_levels.keys()):
                old_level, new_level = old_levels.get(level_id), new_levels.get(level_id)
                if old_level == new_level:
                    continue
                fields = sorted(key for key in (old_level or {}).keys() | (new_level or {}).keys()
                                if (old_level or {}).get(key) != (new_level or {}).get(key))
                comparable = (
                    old_model is not None and new_model is not None
                    and old_model["base"].get("cost_basis") == new_model["base"].get("cost_basis")
                    and _pick(old_level or {}, USAGE_FIELDS) == _pick(new_level or {}, USAGE_FIELDS)
                )
                changes.append({
                    "category": "level", "model_id": model_id, "kind": kind, "level_id": level_id,
                    "fields": fields, "before": _level_summary(old_level), "after": _level_summary(new_level),
                    **_cost_change(old_level, new_level, comparable),
                })
    return changes


def validate_history(history: dict) -> None:
    """Corrupt or incompatible history cannot be silently reset or extended."""
    if not isinstance(history, dict) or history.get("version") != SCHEMA_VERSION:
        raise ValueError("unsupported model change history")
    if history.get("policy") != {"material_after_tax_percent": MATERIAL_PERCENT, "synthetic_excluded": True}:
        raise ValueError("unsupported model history policy")
    baseline = history.get("baseline")
    if (not isinstance(baseline, dict) or not isinstance(baseline.get("snapshot"), dict)
            or baseline.get("fingerprint") != fingerprint(baseline["snapshot"])
            or not isinstance(history.get("events"), list) or not history["events"]
            or not isinstance(history.get("last_changed"), dict)):
        raise ValueError("invalid model history baseline")
    previous, ids = None, set()
    for event in history["events"]:
        event_id = event.get("id")
        if (event_id in ids or event.get("previous_event") != previous
                or event_id != fingerprint({key: value for key, value in event.items() if key != "id"})):
            raise ValueError("model change history integrity check failed")
        timestamp(event["recorded_at"])
        ids.add(event_id)
        previous = event_id
    timestamp(history["last_refresh"]["generated_at"])
    expected_changed = {key: None for key in baseline["snapshot"]["models"]}
    for event in history["events"]:
        for change in event["changes"]:
            if change["model_id"] is not None:
                expected_changed[change["model_id"]] = event["recorded_at"]
    if history["last_changed"] != expected_changed:
        raise ValueError("last-change dates do not match recorded history")
    model_snapshot = {key: value for key, value in baseline["snapshot"].items() if key != "input_fingerprints"}
    if history["last_refresh"]["model_fingerprint"] != fingerprint(model_snapshot):
        raise ValueError("last refresh does not match the recorded baseline")


def record_refresh(history: dict | None, document: dict, receipt: dict) -> dict:
    """Advance the last-reported baseline only after an explicitly successful, matching generation."""
    snapshot = semantic_models(document)
    _successful_generation(receipt)
    if (receipt["generated_at"] != document["generated_at"] or receipt["as_of"] != document["as_of"]
            or receipt["method_version"] != document["method_version"]
            or receipt["fingerprint"] != fingerprint(snapshot)):
        raise ValueError("missing, failed or mismatched model generation receipt")
    snapshot["input_fingerprints"] = receipt["input_fingerprints"]
    now = receipt["checked_at"]
    timestamp(now)
    if history is not None:
        validate_history(history)
        if timestamp(receipt["generated_at"]) < timestamp(history["last_refresh"]["generated_at"]):
            raise ValueError("refusing a model generation older than the recorded history")
        result = copy.deepcopy(history)
        changes = compare_models(history["baseline"]["snapshot"], snapshot)
        previous = receipt.get("previous") or {}
        gap = (receipt["generated_at"] != history["last_refresh"]["generated_at"]
               and (previous.get("status") != "known"
                    or previous.get("generated_at") != history["last_refresh"]["generated_at"]
                    or previous.get("fingerprint") != history["last_refresh"]["model_fingerprint"]))
    else:
        result = {"version": SCHEMA_VERSION, "tracking_started_at": now,
                  "policy": {"material_after_tax_percent": MATERIAL_PERCENT, "synthetic_excluded": True},
                  "events": [], "last_changed": {}}
        changes, gap = [], False
    if history is None or changes or gap:
        event = {"recorded_at": now, "generated_at": document["generated_at"], "run": receipt["run"],
                 "kind": "baseline" if history is None else "refresh", "changes": changes,
                 "history_gap": gap, "previous_event": result["events"][-1]["id"] if result["events"] else None}
        event["id"] = fingerprint(event)
        result["events"].append(event)
        for change in changes:
            if change["model_id"] is not None:
                result["last_changed"][change["model_id"]] = now
    for model_id in snapshot["models"]:
        result["last_changed"].setdefault(model_id, None)
    result["baseline"] = {"snapshot": snapshot, "fingerprint": fingerprint(snapshot)}
    result["last_refresh"] = {
        "generated_at": document["generated_at"], "as_of": document["as_of"],
        "method_version": document["method_version"], "checked_at": now, "run": receipt["run"],
        "model_fingerprint": receipt["fingerprint"],
        "change_status": "initial" if history is None else "changed" if changes else "unchanged",
    }
    return result


# Quarter-end model costs for the Rate History tab (owner decisions 50, 55 and 57 of 2026-11-23, 80 and 84 of
# 2026-11-24).
QUARTERLY_RULE = (
    "Each quarter shows the published medians before and with tax and rebates in effect at its end: the state after "
    "the last recorded refresh generated (UTC date) on or before the quarter's last day, the current quarter showing "
    "the latest recorded state as in progress; an unavailable level has no cost (a gap, never zero), and "
    "recording_gap marks a completed quarter whose next recorded refresh followed an unrecorded one (owner decisions "
    "50, 55 and 57, 2026-11-23). break_before marks a change of the model's cost basis or of the level's example "
    "customer between two points, never a label-only or method-version-only change (owner decision 80, 2026-11-24), "
    "and a model removed and added again between them, whose earlier cost basis was not recorded (owner decision 84, "
    "2026-11-24)."
)
# Decision 80: these define a level's example customer; its id and Reference/Sensitivity role are only labels.
EXAMPLE_CUSTOMER_FIELDS = ("kwh", "kw", "quantity", "unit")
UNIT_LABELS = {"m3": "m\u00b3"}


def _example_customer(summary: dict) -> dict:
    return {field: summary.get(field) for field in EXAMPLE_CUSTOMER_FIELDS}


def _quarter_values(summary: dict | None) -> dict | None:
    """A level's published availability, medians and example customer, copied from a recorded summary.

    Base levels carry no ``available`` flag, so a missing median makes them unavailable; an unavailable level never
    carries a cost (decision 55: the chart shows a gap, never zero).
    """
    if summary is None:
        return None
    medians = {field: None if summary.get(field) is None else _median(summary[field])
               for field in ("without_tax", "with_tax")}
    available = summary.get("available") is not False and None not in medians.values()
    return {"available": available, **{field: value if available else None for field, value in medians.items()},
            "usage": _example_customer(summary)}


def history_states(history: dict) -> list[dict[tuple[str, str, str], dict]]:
    """Level summaries of a validated history after each recorded event, oldest first.

    Keys are (model_id, kind, level_id), kind being "base" or "benchmark". The history keeps only its latest snapshot,
    so earlier states are rebuilt backwards by undoing each later event with its recorded ``before`` summaries. A
    chain whose events do not reproduce their own recorded ``after`` values is refused rather than published.
    """
    state = {(model_id, kind, level_id): _level_summary(level)
             for model_id, model in history["baseline"]["snapshot"]["models"].items()
             for kind in ("base", "benchmark") for level_id, level in model[kind]["levels"].items()}
    states = []
    for event in reversed(history["events"]):
        states.append(state)
        state = dict(state)
        for change in event["changes"]:
            if change["category"] != "level":
                continue
            key = (change["model_id"], change["kind"], change["level_id"])
            if _quarter_values(state.get(key)) != _quarter_values(change["after"]):
                raise ValueError(f"model change history does not rebuild consistently: {' '.join(key)} after event "
                                 f"{event['id']}")
            if change["before"] is None:
                state.pop(key, None)
            else:
                state[key] = change["before"]
    states.reverse()
    return states


def _quarter(day: date) -> tuple[int, int]:
    return day.year, (day.month - 1) // 3 + 1


def _quarter_end(quarter: tuple[int, int]) -> date:
    year, number = quarter
    return date(year, 3 * number, calendar.monthrange(year, 3 * number)[1])


def _usage_text(summary: dict) -> str:
    """The example customer as a reader sees it, e.g. "40 kW and 10,000 kWh" or "200 m\u00b3"."""
    parts = [f"{summary[field]:,} {unit}" for field, unit in (("kw", "kW"), ("kwh", "kWh"))
             if summary.get(field) is not None]
    if summary.get("quantity") is not None:
        unit = summary.get("unit")
        parts.append(f"{summary['quantity']:,} {UNIT_LABELS.get(unit, unit)}" if unit else f"{summary['quantity']:,}")
    return " and ".join(parts) or "no example usage"


def _break_reasons(events: list[dict], key: tuple[str, str, str], before: dict, after: dict) -> list[str]:
    """Why a series breaks between two points (owner decisions 80 and 84, 2026-11-24).

    Decision 80: only a changed cost basis or example customer breaks a series, never a label or method version.
    ``events`` are those recorded between the points; ``before`` and ``after`` are the example customers of the two
    points a chart joins. Comparing those directly also catches a level removed and re-added with another example
    customer, which no single recorded change shows on both sides. Decision 84: a model removed and added again keeps
    no record of its earlier cost basis, so that breaks every series of the model, base and benchmark.
    """
    reasons, removed = [], False
    for event in events:
        for change in event["changes"]:
            if change["model_id"] != key[0]:
                continue
            if change["category"] == "model_removed":
                removed = True
            elif change["category"] == "model_added" and removed:
                reasons.append("the model was removed and added again; its earlier cost basis was not recorded")
            elif (change["category"] == "structure" and change.get("kind") == "base"
                  and "cost_basis" in change["fields"]):
                old, new = (change[side].get("cost_basis") for side in ("before", "after"))
                reasons.append("cost basis changed: " + (old if isinstance(old, str) else _json(old)) + " -> "
                               + (new if isinstance(new, str) else _json(new)))
            elif (change["category"] == "level" and (change["kind"], change["level_id"]) == key[1:]
                  and change["before"] is not None and change["after"] is not None
                  and _example_customer(change["before"]) != _example_customer(change["after"])):
                reasons.append(f"example customer changed: {_usage_text(change['before'])} -> "
                               f"{_usage_text(change['after'])}")
    if before != after:
        reasons.append(f"example customer changed: {_usage_text(before)} -> {_usage_text(after)}")
    return list(dict.fromkeys(reasons))


def model_cost_quarterly(history: dict) -> dict:
    """Quarter-end costs of every recorded model level, rebuilt only from the recorded change history.

    Owner decisions 50, 55 and 57 (2026-11-23) and 80 and 84 (2026-11-24), stated in QUARTERLY_RULE: the website shows
    only amounts the history saved. Quarters run from the first event's quarter to the quarter of the last refresh;
    the wall clock is never read, so a given history always gives the same document. Base levels and observed market
    benchmarks are separate series; synthetic estimates never enter the history.
    """
    validate_history(history)
    events = history["events"]
    generated = [timestamp(event["generated_at"]) for event in events]
    last_generated = timestamp(history["last_refresh"]["generated_at"])
    if any(later < earlier for earlier, later in zip(generated, generated[1:])) or generated[-1] > last_generated:
        raise ValueError("model change history events are not in generation order")
    states = history_states(history)
    days = [value.date() for value in generated]
    current = _quarter(last_generated.date())
    quarter, index, points = _quarter(days[0]), 0, {}
    while quarter <= current:
        end = _quarter_end(quarter)
        while index + 1 < len(events) and days[index + 1] <= end:
            index += 1
        in_progress = quarter == current
        # An unrecorded generation before the next recorded refresh may have changed a value before the quarter ended.
        gap = not in_progress and index + 1 < len(events) and events[index + 1]["history_gap"] is True
        for key, summary in states[index].items():
            points.setdefault(key, []).append((index, {
                "quarter": f"{quarter[0]}Q{quarter[1]}", "in_progress": in_progress, **_quarter_values(summary),
                "recorded_at": events[index]["recorded_at"], "recording_gap": gap, "break_before": None,
            }))
        quarter = (quarter[0] + quarter[1] // 4, quarter[1] % 4 + 1)
    series = []
    for key in sorted(points):
        for (earlier, previous), (later, point) in zip(points[key], points[key][1:]):
            reasons = _break_reasons(events[earlier + 1:later + 1], key, previous["usage"], point["usage"])
            if reasons:
                point["break_before"] = {"reasons": reasons}
        series.append({"model_id": key[0], "kind": key[1], "level_id": key[2],
                       "points": [point for _, point in points[key]]})
    return {
        "version": 1, "kind": "model_cost_quarterly", "tracking_started_at": history["tracking_started_at"],
        "last_refresh": {key: history["last_refresh"][key] for key in ("generated_at", "as_of", "method_version")},
        "last_event": events[-1]["id"], "rule": QUARTERLY_RULE, "current_quarter": f"{current[0]}Q{current[1]}",
        "series": series,
    }


def save_cost_quarterly(path: Path, history: dict) -> bool:
    """Rewrite the quarter-end model costs from a recorded history; True when the file was replaced.

    The file is derived from the history, so a failure is logged and keeps the previous file without undoing or
    blocking the recorded history: reporting failures cannot block valid publication.
    """
    try:
        document = model_cost_quarterly(history)
        # The listed key order (not write_json's sorted keys) and LF line endings on every platform.
        text = json.dumps(document, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
        _replace_text(path, text, newline="\n")
    except Exception:
        logger.exception("Quarterly model costs were not updated; the change history was recorded and the previous "
                         "%s is kept", path)
        return False
    return True


def input_checks(root: Path, now: datetime) -> list[dict]:
    """Reuse coverage and observed-market validity rules; a documented missing model is not corrupt data."""
    from scripts.coverage_gate import evaluate
    from scrapers.utils.market_pricing import historical_market_price
    from pipeline.representative_models import (coverage_report, load_block_periods, load_percentage_riders,
                                                 load_subsidies)

    checks = []
    try:
        coverage = evaluate(read_json(root / "data" / "sources" / "registry.json"),
                            read_json(root / "site" / "data" / "rates.json"),
                            read_json(root / "data" / "sources" / "coverage_ledger.json"), now.date())
        problems = [f"{name}: {finding['code']}: {finding['message']}"
                    for name, findings in coverage["utilities"].items() for finding in findings
                    if finding["level"] == "error"]
        problems.extend(f"{finding['code']}: {finding['message']}" for finding in coverage["global"]
                        if finding["level"] == "error")
        checks.append({"id": "coverage", "ok": coverage["passed"], "details": problems,
                       "warnings": coverage["warnings"], "freshness": coverage["freshness"]})
    except (OSError, ValueError, KeyError, TypeError) as exc:
        checks.append({"id": "coverage", "ok": False, "details": [f"Coverage inputs cannot be checked: {exc}"]})
    try:
        configs = {}
        required = {
            "crosswalk": {"rules": list, "vocabulary": dict},
            "usage_levels": {"electricity": dict, "gas": dict, "tou_shares": dict},
            "taxes": {"jurisdictions": dict},
        }
        for name, fields in required.items():
            config = read_json(root / "data" / "models" / f"{name}.json")
            if (not isinstance(config, dict) or config.get("version") != 1
                    or any(not isinstance(config.get(key), kind) or not config[key] for key, kind in fields.items())):
                raise ValueError(f"invalid {name} configuration")
            configs[name] = config
        unmapped = coverage_report(read_json(root / "site" / "data" / "rates.json"),
                                   configs["crosswalk"])["totals"]["unmapped"]
        periods = load_block_periods(root / "data" / "models" / "block_periods.json")
        problems = [f"{unmapped} live tariffs are unmapped."] if unmapped else []
        if periods.get("problem") or periods.get("skipped"):
            problems.append(f"Reviewed block periods are invalid: {periods.get('problem') or periods['skipped']}")
        # Method 7T-1 reviewed lists: a missing or invalid list leaves territorial costs not computable.
        for name, loaded in (("percentage riders", load_percentage_riders(root / "data" / "models" /
                                                                          "percentage_riders.json")),
                             ("subsidies", load_subsidies(root / "data" / "models" / "subsidies.json"))):
            if loaded.get("problem") or loaded.get("skipped"):
                problems.append(f"Reviewed {name} are invalid: {loaded.get('problem') or loaded['skipped']}")
        checks.append({"id": "model_configuration", "ok": not problems, "details": problems})
    except (OSError, ValueError, KeyError, TypeError) as exc:
        checks.append({"id": "model_configuration", "ok": False,
                       "details": [f"Model configuration cannot be checked: {exc}"]})
    for province, name in (("ON", "ontario"), ("AB", "alberta")):
        try:
            config = read_json(root / "data" / "models" / "usage_levels.json")["market_benchmarks"][province]
            document = read_json(root / "site" / "data" / f"market_pricing_{name}.json")
            historical_market_price(document, province=province, as_of=now.date(),
                                    max_lag_months=config["max_window_lag_months"])
            checks.append({"id": f"market:{province}", "ok": True, "details": []})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            checks.append({"id": f"market:{province}", "ok": False,
                           "details": [f"Observed {province} market history cannot be used: {exc}"]})
    try:
        # Rate History (owner decisions 55 and 56, 2026-11-23): the reviewed series match stored component names, so a
        # scraper that renames or drops a matched line is reported here instead of leaving its chart empty.
        from pipeline.rate_history import series_problems

        problems = series_problems(read_json(root / "site" / "data" / "rate_history_series.json"),
                                   read_json(root / "site" / "data" / "rates.json"))
        checks.append({"id": "rate_history_series", "ok": not problems, "details": problems})
    except (OSError, ValueError, KeyError, TypeError) as exc:
        checks.append({"id": "rate_history_series", "ok": False,
                       "details": [f"Rate History series cannot be checked: {exc}"]})
    return checks


def _monthly_occurrences(cron: str, year: int, month: int) -> list[datetime]:
    """Occurrences in one month of the repository's fixed UTC day-of-month schedules, rejecting other cron forms."""
    minute, hour, days, month_field, weekday = cron.split()
    if month_field != "*" or weekday != "*" or not minute.isdigit() or not hour.isdigit():
        raise ValueError(f"unsupported monitoring schedule: {cron}")
    day_numbers = [int(day) for day in days.split(",")]
    if not day_numbers or any(day < 1 or day > 31 for day in day_numbers):
        raise ValueError(f"invalid monitoring schedule: {cron}")
    return [datetime(year, month, day, int(hour), int(minute), tzinfo=timezone.utc)
            for day in day_numbers if day <= calendar.monthrange(year, month)[1]]


def scheduled_due(cron: str, now: datetime) -> datetime:
    """The latest occurrence at or before ``now`` of a fixed UTC day-of-month schedule."""
    for offset in range(3):
        index = now.year * 12 + now.month - 1 - offset
        candidates = [value for value in _monthly_occurrences(cron, index // 12, index % 12 + 1) if value <= now]
        if candidates:
            return max(candidates)
    raise ValueError(f"no occurrence found for {cron}")


def next_scheduled(cron: str, after: datetime) -> datetime:
    """The first occurrence strictly after ``after`` of a fixed UTC day-of-month schedule."""
    for offset in range(3):
        index = after.year * 12 + after.month - 1 + offset
        candidates = [value for value in _monthly_occurrences(cron, index // 12, index % 12 + 1) if value > after]
        if candidates:
            return min(candidates)
    raise ValueError(f"no occurrence found for {cron}")


def manual_update_reviews(ledger: dict) -> dict[str, date]:
    """Review dates of the ledger's manual-update utilities; malformed decisions are left out (fail closed)."""
    from scripts.coverage_gate import manual_update_review_by

    reviews = {}
    utilities = ledger.get("utilities") if isinstance(ledger, dict) else None
    for name, entry in (utilities.items() if isinstance(utilities, dict) else ()):
        if isinstance(entry, dict) and "manual_update" in entry:
            try:
                reviews[name] = manual_update_review_by(entry["manual_update"])
            except ValueError:
                continue
    return reviews


def source_checks(receipt: dict, manual_updates: dict[str, date] | None = None) -> list[dict]:
    if receipt.get("version") != 1 or receipt.get("kind") != "source_check":
        raise ValueError("missing or unsupported source-check receipt")
    checked_at = receipt["checked_at"]
    checked_on = timestamp(checked_at).date()
    rows = receipt["summary"]["rows"]
    expected = receipt["expected_utilities"]
    if (not isinstance(receipt.get("scope"), dict) or type(receipt["scope"].get("full")) is not bool
            or not rows or not isinstance(expected, list) or not expected
            or len(rows) != len(expected) or len(set(expected)) != len(expected)
            or sorted(row["utility"] for row in rows) != sorted(expected)):
        raise ValueError("source receipt is incomplete or has duplicate utilities")
    checks = []
    for row in rows:
        if any(type(row.get(key)) is not int or row[key] < 0 for key in ("live", "seed", "invalid")):
            raise ValueError("invalid source receipt counts")
        # Older receipts have no excluded_seed field: every estimate then counts as a problem.
        excluded = row.get("excluded_seed", 0)
        if type(excluded) is not int or not 0 <= excluded <= row["seed"]:
            raise ValueError("invalid source receipt counts")
        # Labelled excluded-class estimates (Ontario street lighting) are expected output, not a
        # source failure (owner decision 2026-11-18); any other estimate still fails the source.
        healthy = (row["live"] > 0 and row["seed"] == excluded and row["invalid"] == 0
                   and row.get("error") is None)
        detail = (f"{row['utility']}: {row['live']} live, {row['seed']} estimated "
                  f"({excluded} excluded-class), {row['invalid']} invalid; {row.get('error') or row['status']}")
        review_by = (manual_updates or {}).get(row["utility"])
        if (review_by is not None and row["live"] == 0 and row["seed"] > 0 and row["invalid"] == 0
                and row.get("error") is None):
            # A ledger manual-update utility (Maritime Electric, owner decision 2026-11-19): its labelled
            # estimates are expected until review_by; a later check fails as the yearly reminder.
            healthy = checked_on <= review_by
            if not healthy:
                detail += (f"; manual update review was due by {review_by.isoformat()}: re-check the official "
                           "schedule locally, update the estimates and move manual_update.review_by in "
                           "data/sources/coverage_ledger.json")
        checks.append({"id": f"source:{row['utility']}", "ok": healthy, "checked_at": checked_at,
                       "details": [] if healthy else [detail]})
    return checks


def _evidence(run: dict, name: str) -> dict:
    value = run.get("evidence", {}).get(name)
    identity = value.get("run") if isinstance(value, dict) else None
    if (not isinstance(identity, dict) or str(identity.get("id")) != str(run["id"])
            or str(identity.get("attempt")) != str(run["run_attempt"])):
        raise ValueError(f"missing or mismatched {name} for run {run['id']}")
    return value


def _monthly_price_check(key: str, due: datetime, successes: list[datetime], unverified: bool,
                         now: datetime) -> dict:
    """The monthly-price schedule's own cadence: met by a successful full or monthly-price run after its due time."""
    price_key = f"{key}:monthly-price"
    if successes and not unverified:
        return {"id": price_key, "ok": True, "details": [], "checked_at": now.isoformat(),
                "refresh_completed_at": max(successes).isoformat()}
    if now - due > OVERDUE_GRACE:
        return {"id": price_key, "ok": False, "details": [
            f"scrape.yml: the monthly-price refresh due {due.isoformat()} is over 24 hours overdue; no successful "
            "monthly-price or full refresh since then could be verified."]}
    return {"id": price_key, "ok": None, "details": [
        f"scrape.yml: monthly-price refresh due {due.isoformat()}; awaiting complete evidence within the 24-hour "
        "grace."]}


def _held_until_monthly_price(check: dict, utilities: set[str], full_due: datetime, now: datetime) -> dict:
    """Hold a monthly-price utility's failure seen between the full run and the next monthly-price run.

    Owner decision 2026-11-23: these utilities usually fail on the 1st because their new month is posted later, so
    the failure waits for the monthly-price run on the 4th. It is a problem when that run's own check fails, or when
    no newer check arrives more than 24 hours after its due time. Other utilities and other days are reported as
    soon as they are seen (the 2026-11-17 rule).
    """
    utility = check["id"].removeprefix("source:")
    if check["ok"] is not False or utility not in utilities:
        return check
    price_due = next_scheduled(MONTHLY_PRICE_CRON, full_due)
    if not full_due <= timestamp(check["checked_at"]) < price_due:
        return check
    if now - price_due > OVERDUE_GRACE:
        return {**check, "details": [*check["details"], f"The monthly-price run due {price_due.isoformat()} did not "
                                                        "refresh it within 24 hours."]}
    return {**check, "ok": None, "details": [f"Awaiting the monthly-price run due {price_due.isoformat()} (owner "
                                             "decision 2026-11-23): " + "; ".join(check["details"])]}


def workflow_checks(context: dict, now: datetime, manual_updates: dict[str, date] | None = None,
                    monthly_price_utilities: Iterable[str] = ()) -> list[dict]:
    """Use completed-step evidence, including source provenance; a green badge alone is insufficient.

    The Monthly Scrape's monthly-price schedule (MONTHLY_PRICE_CRON) is checked on its own and never stands in for
    the full refresh; ``monthly_price_utilities`` (registry names) are the utilities whose failures it holds.
    """
    checks, latest_sources = [], {}
    full_due = None
    workflows = context["workflows"]
    parents = [run for name in ("scrape.yml", "ontario-price-archive.yml")
               for run in workflows.get(name, {}).get("runs", [])
               if run["status"] == "completed" and (name == "ontario-price-archive.yml"
                                                   or run.get("conclusion") == "success")]
    for name in ("scrape.yml", "source-health.yml", "ontario-price-archive.yml", "market-benchmarks.yml"):
        key = f"workflow:{name}"
        try:
            entry = workflows[name]
            if entry.get("error"):
                raise ValueError(entry["error"])
            schedules, price_due = list(entry["schedules"]), None
            if name == "scrape.yml" and MONTHLY_PRICE_CRON in schedules:
                schedules = [cron for cron in schedules if cron != MONTHLY_PRICE_CRON]
                if not schedules:
                    raise ValueError("scrape.yml has no full-refresh schedule besides the monthly-price run")
                price_due = scheduled_due(MONTHLY_PRICE_CRON, now)
            due = (max(scheduled_due(cron, now) for cron in schedules) if schedules else
                   max((timestamp(run["updated_at"]) for run in parents), default=None))
            if name == "scrape.yml":
                full_due = due
            if due is None:
                checks.append({"id": key, "ok": None, "details": ["No qualifying parent refresh was observed."]})
                continue
            successes, failures, price_successes = [], [], []
            latest_success, latest_unverified = None, None
            for run in entry["runs"]:
                observed_at = timestamp(run["updated_at"])
                if run.get("evidence_error"):
                    failures.append((observed_at, False, run["evidence_error"]))
                    continue
                if not run.get("evidence"):
                    if run["status"] == "completed" and run.get("conclusion") not in ("success", "skipped"):
                        failures.append((observed_at, False,
                                         f"{run.get('html_url', run['id'])}: workflow failed without complete receipts"))
                    elif run["status"] == "completed":
                        latest_unverified = max(latest_unverified or observed_at, observed_at)
                    continue
                reported_elsewhere, full_refresh, price_refresh = False, True, True
                try:
                    outcome = _evidence(run, "monitor-status.json")
                    if (outcome.get("version") != 1 or outcome.get("kind") != "workflow_outcome"
                            or type(outcome.get("failure_reported")) is not bool):
                        raise ValueError("invalid workflow outcome")
                    if outcome.get("inputs") == "failure":
                        # Owner decision 2026-11-23: a manual run stopped by its input check scraped and saved
                        # nothing, and its own error says what to type: neither a failed nor a successful refresh.
                        continue
                    observed_at = timestamp(outcome["checked_at"])
                    reported_elsewhere = outcome["failure_reported"]
                    if name in ("scrape.yml", "source-health.yml"):
                        sources = _evidence(run, "source-summary.json")
                        for check in source_checks(sources, manual_updates):
                            prior = latest_sources.get(check["id"])
                            if prior is None or timestamp(check["checked_at"]) > timestamp(prior["checked_at"]):
                                latest_sources[check["id"]] = {
                                    **check, "reported_elsewhere": outcome.get("failure_reported", False),
                                }
                        full_refresh = sources["scope"]["full"]
                        price_refresh = full_refresh or sources["scope"].get("group") == MONTHLY_PRICE_GROUP
                        if outcome["sources"] != "success":
                            raise ValueError("source-check step did not complete")
                        finished = timestamp(sources["checked_at"])
                    if name != "source-health.yml":
                        generated = _evidence(run, "model-generation.json")
                        _successful_generation(generated)
                        if outcome["publication"] != "success":
                            raise ValueError("model publication failed or was not attempted")
                        finished = timestamp(generated["checked_at"])
                        if (outcome.get("history_step") not in ("success", "failure")
                                or outcome.get("history_recorded") is not True):
                            raise ValueError("change history recording was not verified; data publication stayed separate")
                    if name == "ontario-price-archive.yml" and not outcome["archive_complete"]:
                        raise ValueError("raw preservation or validated archive update failed")
                    latest_success = max(latest_success or observed_at, observed_at)
                    if full_refresh and finished >= due:
                        successes.append(finished)
                    if price_due is not None and price_refresh and finished >= price_due:
                        price_successes.append(finished)
                except (ValueError, KeyError, TypeError) as exc:
                    failures.append((observed_at, reported_elsewhere, f"{run.get('html_url', run['id'])}: {exc}"))
            failure = max(failures, key=lambda item: item[0]) if failures else None
            unverified = (latest_unverified is not None
                          and (latest_success is None or latest_unverified > latest_success))
            if failure is not None and (latest_success is None or failure[0] >= latest_success):
                checks.append({"id": key, "ok": False, "reported_elsewhere": failure[1],
                               "details": [f"{name}: latest attempted refresh failed or could not be verified.", failure[2]],
                               "checked_at": now.isoformat()})
            elif successes and not unverified:
                checks.append({"id": key, "ok": True, "details": [],
                               "checked_at": now.isoformat(), "refresh_completed_at": max(successes).isoformat()})
            elif now - due > OVERDUE_GRACE:
                checks.append({"id": key, "ok": False,
                               "details": [f"{name}: expected refresh {due.isoformat()} is over 24 hours overdue; "
                                           "the latest full refresh could not be verified."]})
            else:
                checks.append({"id": key, "ok": None, "details": [
                    f"{name}: refresh due {due.isoformat()}; awaiting complete evidence within the 24-hour grace."]})
            if price_due is not None:
                checks.append(_monthly_price_check(key, price_due, price_successes, unverified, now))
        except (ValueError, KeyError, TypeError) as exc:
            checks.append({"id": key, "ok": False, "details": [f"Cannot verify workflow freshness: {exc}"]})
    sources = list(latest_sources.values())
    if full_due is not None:
        held = set(monthly_price_utilities)
        sources = [_held_until_monthly_price(check, held, full_due, now) for check in sources]
    return checks + sources


# Owner decisions 2026-11-23: the "Rates not updated in a year" issue is reported once a quarter, after the first
# successful full Monthly Scrape of January, April, July and October.
FRESHNESS_REPORT_MONTHS = (1, 4, 7, 10)


def _report_run(context: dict | None, now: datetime, run_id: str | None) -> tuple[bool, str]:
    """Whether this monitoring job belongs to a successful full Monthly Scrape in a quarter's first month.

    Proven by the calling run's own receipts (run and attempt bound): the full source scope, a completed source-check
    step, a successful model generation and a successful data publication. The monthly-price run on the 4th, targeted
    runs, Source Health and the other workflows never qualify; neither does a run whose receipts are not visible.
    """
    if now.month not in FRESHNESS_REPORT_MONTHS:
        return False, "not the first month of a quarter"
    if not run_id or context is None:
        return False, "no GitHub Actions run context"
    runs = context.get("workflows", {}).get("scrape.yml", {}).get("runs", [])
    run = next((item for item in runs if str(item.get("id")) == str(run_id)), None)
    if run is None:
        return False, "this run is not a Monthly Scrape, or its receipts were not visible"
    try:
        outcome = _evidence(run, "monitor-status.json")
        sources = _evidence(run, "source-summary.json")
        _successful_generation(_evidence(run, "model-generation.json"))
        if sources["scope"]["full"] is not True:
            return False, "a targeted or monthly-price Monthly Scrape, not a full one"
        if outcome["sources"] != "success" or outcome["publication"] != "success":
            return False, "the Monthly Scrape did not complete its scrape and publication"
    except (ValueError, KeyError, TypeError) as exc:
        return False, f"the run's receipts could not be verified: {exc}"
    return True, "a successful full Monthly Scrape in the first month of the quarter"


def freshness_report(utilities: dict | None, context: dict | None, now: datetime, run_id: str | None) -> dict | None:
    """The data for the quarterly "Rates not updated in a year" issue (owner decisions 2026-11-23 and 2026-11-24).

    ``utilities`` is the coverage gate's ``freshness`` result: the utilities with a document whose prices have not
    changed for more than a year, after the ledger's exemptions and review notes. None when the gate inputs could
    not be read: nothing is then reported, so the issue is neither created nor closed on missing data. Only a report
    run creates a quarter's issue; every other run only refreshes an open one (scripts/model_monitoring_issue.js).
    """
    if not isinstance(utilities, dict):
        return None
    report_run, reason = _report_run(context, now, run_id)
    return {"version": 1, "checked_at": now.isoformat(), "quarter": f"{now.year}-Q{(now.month - 1) // 3 + 1}",
            "report_run": report_run, "reason": reason, "utilities": utilities}


def read_evidence_archive(path: Path) -> dict:
    """Read only named JSON receipts from a small Actions artifact; never extract paths from a ZIP."""
    names = {"model-generation.json", "source-summary.json", "monitor-status.json"}
    result = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.filename not in names:
                continue
            if info.file_size > 2_000_000 or info.filename in result:
                raise ValueError("oversized or duplicate monitoring receipt")
            result[info.filename] = json.loads(archive.read(info).decode("utf-8"))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, default=MODELS_PATH)
    parser.add_argument("--history", type=Path, default=HISTORY_PATH)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--record", action="store_true", help="explicitly write history from a generation receipt")
    parser.add_argument("--quarterly", type=Path,
                        help="with --record: the quarter-end model costs to rewrite (default: "
                             f"{QUARTERLY_PATH.name} next to --history)")
    parser.add_argument("--dry-run", action="store_true", help="check only; never write history")
    parser.add_argument("--report", type=Path, help="explicitly write a diagnostic report")
    parser.add_argument("--github-context", type=Path, help="verified Actions run metadata and receipts")
    parser.add_argument("--artifact", type=Path, help="read named receipts from an Actions ZIP (no extraction)")
    args = parser.parse_args(argv)
    if args.artifact:
        print(_json(read_evidence_archive(args.artifact)))
        return 0
    if args.record and (args.dry_run or args.receipt is None):
        parser.error("--record requires --receipt and cannot be combined with --dry-run")
    if args.quarterly is not None and not args.record:
        parser.error("--quarterly requires --record")
    now = datetime.now(timezone.utc)
    report = {"version": SCHEMA_VERSION, "checked_at": now.isoformat(), "run": run_identity(),
              "checks": input_checks(ROOT, now)}
    coverage = next((check for check in report["checks"] if check["id"] == "coverage"), {})
    freshness = coverage.pop("freshness", None)
    context = None
    if args.github_context:
        context = read_json(args.github_context)
        try:
            manual_updates = manual_update_reviews(read_json(ROOT / "data" / "sources" / "coverage_ledger.json"))
        except (OSError, ValueError):
            manual_updates = {}  # no exemption; the coverage check reports the unreadable ledger
        try:
            from scrapers.registry import load_registry, monthly_price_utilities

            price_utilities = {entry["name"] for entry in
                               monthly_price_utilities(load_registry(ROOT / "data" / "sources" / "registry.json"))}
        except (OSError, ValueError, KeyError, TypeError):
            price_utilities = set()  # no hold: their failures are reported as soon as they are seen
        report["checks"].extend(workflow_checks(context, now, manual_updates, price_utilities))
    else:
        report["scope_note"] = "Local file checks only; GitHub workflow cadence was not checked."
    report["freshness"] = freshness_report(freshness, context, now, report["run"]["id"])
    quarterly = None
    try:
        document = read_json(args.models)
        semantic_models(document)
        if document.get("coverage_report") is not None:
            unmapped = document["coverage_report"]["totals"]["unmapped"]
            block_periods = document.get("assumptions", {}).get("block_periods", {})
            problems = ([f"{unmapped} live tariffs are unmapped."] if unmapped else [])
            if block_periods.get("problem") or block_periods.get("skipped"):
                problems.append("Reviewed block-period inputs are missing or invalid.")
            for name in ("percentage_riders", "subsidies"):
                reviewed = document.get("assumptions", {}).get(name) or {}
                if reviewed.get("problem") or reviewed.get("skipped"):
                    problems.append(f"Reviewed {name.replace('_', ' ')} inputs are missing or invalid.")
            report["checks"].append({"id": "model_inputs", "ok": not problems, "details": problems})
        history = read_json(args.history) if args.history.exists() else None
        if args.receipt:
            history = record_refresh(history, document, read_json(args.receipt))
        elif history is None:
            raise ValueError("model change tracking has not been initialized")
        else:
            validate_history(history)
            if (history["last_refresh"]["model_fingerprint"] != fingerprint(semantic_models(document))
                    or any(history["last_refresh"][key] != document[key]
                           for key in ("generated_at", "as_of", "method_version"))):
                raise ValueError("published models do not match the last recorded generation")
        if args.record:
            write_json(args.history, history)
            # Only after the history was written; a failure is logged and changes neither the history nor the checks.
            quarterly = save_cost_quarterly(args.quarterly or args.history.with_name(QUARTERLY_PATH.name), history)
        report["checks"].append({"id": "model_history", "ok": True, "details": []})
        report["refresh"] = history["last_refresh"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        logger.error("Model monitoring could not record/verify the refresh: %s", exc)
        report["checks"].append({"id": "model_history", "ok": False, "details": [str(exc)]})
    if args.report:
        write_json(args.report, report)
    failed = [check for check in report["checks"] if check["ok"] is False]
    print(f"Model monitoring: {len(failed)} problem check(s); "
          f"{'history write requested' if args.record else 'read-only check'}.")
    if quarterly is not None:
        print("Quarterly model costs: " + ("rewritten." if quarterly else
                                           "NOT updated (error logged above); the change history was recorded."))
    for check in failed:
        print(f"{check['id']}: " + "; ".join(check["details"]))
    if report["freshness"] is not None:
        flagged = report["freshness"]["utilities"]
        print(f"Rates not updated in a year: {len(flagged)} utilities"
              + (f" ({', '.join(flagged)})" if flagged else "")
              + f"; quarterly report run: {'yes' if report['freshness']['report_run'] else 'no'}"
              f" ({report['freshness']['reason']}).")
    if report.get("scope_note"):
        print(report["scope_note"])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
