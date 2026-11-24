"""Coverage gate: is live-rate coverage complete for the active registered utilities?

    python scripts/coverage_gate.py [--as-of YYYY-MM-DD] [--json FILE] [--report-only] [--verbose]

Reads data/sources/registry.json, the exported site/data/rates.json and the audit ledger
data/sources/coverage_ledger.json, and checks every active registered utility (status "active" or "partial";
merged and retired entries are skipped) against these gates:

* G1 ``no_live_output``: at least one live record (provenance "live") in effect on the as-of date. Seed
  estimates never count, and a record whose end date has passed (for example an Alberta Rate of Last Resort price
  after its term) does not count.
* G2 ``no_audit`` / ``stale_audit``: a ledger entry with a dated class-level audit not older than --max-age-days.
* G3 ``deferred_open``: no item left in the ledger's "deferred" list (market-indexed products still to be added);
  excluded and source-blocked items are allowed because each one is written down with its reason.
  ``monitor_overdue``: a monitored item, or a ``manual_update`` decision, whose review_by date has passed.

A ``manual_update`` entry {reason, decided, review_by} records a utility whose official source cannot be read from
GitHub, so its labelled estimates are refreshed by hand (Maritime Electric, owner decision 2026-11-19). It never
counts as live output; pipeline/model_monitoring.py accepts that utility's estimates until review_by.

Warnings (never fail the gate): ``monitor_due_soon``, ``live_expiring`` (every live record ends within
--warn-days) and ``not_updated_in_a_year``. ``ledger_orphan`` (a ledger entry for a utility that is not active) and
``ledger_invalid`` are errors.

``not_updated_in_a_year`` (owner decisions 2026-11-23 and 2026-11-24): data not updated in a year is the key
freshness concern, while a lag of a few months is acceptable. Each official document behind a utility's current live
prices is dated by its last real price change (see ``document_update_dates``) and flagged once the as-of date is
past that date's anniversary, so a stale tariff sheet cannot hide behind a fresh monthly price. A ledger
``freshness_exempt`` {reason, decided} exempts a utility (AESO, Maritime Electric); a dated ``freshness_review``
{reviewed, finding, basis[, review_by]} clears the flags that already existed on its date, for one year or until
review_by.

The gate exits 1 when there are errors, unless --report-only is given. On GitHub Actions the result is one public
``::notice`` annotation. Standard library only; nothing is written except the optional --json file.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "data" / "sources" / "registry.json"
RATES_PATH = ROOT / "site" / "data" / "rates.json"
LEDGER_PATH = ROOT / "data" / "sources" / "coverage_ledger.json"

ACTIVE_STATUSES = ("active", "partial")
NOTICE_TITLE = "Coverage gate"
SCHEMA_VERSION = 1
DEFAULT_MAX_AGE_DAYS = 120
DEFAULT_WARN_DAYS = 30
LIST_KEYS = ("excluded", "source_blocked", "deferred")
ENTRY_KEYS = {"audit", "monitor", "manual_update", "freshness_exempt", "freshness_review", "notes", "stored_name",
              "group", *LIST_KEYS}
FRESHNESS_CODE = "not_updated_in_a_year"
FRESHNESS_FINDINGS = ("legitimate", "parser_fixed", "moved_on")
GROUP_KEYS = {"audit", "monitor", "notes", *LIST_KEYS}
ERROR_ORDER = ("no_live_output", "no_audit", "stale_audit", "deferred_open", "monitor_overdue",
               "ledger_orphan", "ledger_invalid")


class GateInputError(Exception):
    """An input file cannot be read."""


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GateInputError(f"cannot read {path}: {exc}") from exc


def _parse_date(value, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{label} is not an ISO date: {value!r}") from exc


def active_utilities(registry: dict) -> list[dict]:
    return [u for u in registry["utilities"] if u.get("status") in ACTIVE_STATUSES]


def manual_update_review_by(value) -> date:
    """The review date of a ledger ``manual_update`` decision; ValueError when the decision is malformed."""
    if not isinstance(value, dict) or set(value) != {"reason", "decided", "review_by"}:
        raise ValueError("'manual_update' needs exactly reason, decided and review_by")
    if not isinstance(value["reason"], str) or not value["reason"].strip():
        raise ValueError("manual_update.reason must be a non-empty string")
    decided = _parse_date(value["decided"], "manual_update.decided")
    review_by = _parse_date(value["review_by"], "manual_update.review_by")
    if review_by < decided:
        raise ValueError("manual_update.review_by is before its decision date")
    return review_by


def one_year_after(day: date) -> date:
    """The same calendar day a year later; a change on 29 February falls due on 28 February (decision 2026-11-24)."""
    try:
        return day.replace(year=day.year + 1)
    except ValueError:
        return day.replace(year=day.year + 1, day=28)


def freshness_exemption(value) -> date:
    """The decision date of a ledger ``freshness_exempt``; ValueError when it is malformed (no exemption then)."""
    if not isinstance(value, dict) or set(value) != {"reason", "decided"}:
        raise ValueError("'freshness_exempt' needs exactly reason and decided")
    if not isinstance(value["reason"], str) or not value["reason"].strip():
        raise ValueError("freshness_exempt.reason must be a non-empty string")
    return _parse_date(value["decided"], "freshness_exempt.decided")


def freshness_review_window(value) -> tuple[date, date]:
    """(reviewed, review_by) of a ledger ``freshness_review``; ValueError when it is malformed (it clears nothing then).

    review_by is optional: the note lasts one year, or until an earlier date it names (owner decision 2026-11-23).
    """
    if not isinstance(value, dict) or not {"reviewed", "finding", "basis"} <= set(value) <= {
            "reviewed", "finding", "basis", "review_by"}:
        raise ValueError("'freshness_review' needs reviewed, finding and basis, and optionally review_by")
    if value["finding"] not in FRESHNESS_FINDINGS:
        raise ValueError(f"freshness_review.finding must be one of {', '.join(FRESHNESS_FINDINGS)}")
    if not isinstance(value["basis"], str) or not value["basis"].strip():
        raise ValueError("freshness_review.basis must be a non-empty string")
    reviewed = _parse_date(value["reviewed"], "freshness_review.reviewed")
    longest = one_year_after(reviewed)
    review_by = _parse_date(value["review_by"], "freshness_review.review_by") if "review_by" in value else longest
    if not reviewed < review_by <= longest:
        raise ValueError("freshness_review.review_by must fall after reviewed and at most one year later")
    return reviewed, review_by


def _day(value) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _priced(component: dict) -> bool:
    """A line with a non-zero price: value-less market references ("Variable") and $0 lines cannot go stale."""
    value = component.get("charge_value")
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value != 0


def _line_key(component: dict) -> tuple:
    """A priced line without its name, so a line renamed with the same value is not a change (decision 2026-11-24)."""
    return (component.get("component_type"), component.get("charge_unit"), component.get("tier_number"),
            component.get("tou_period"), component.get("season"), component.get("sub_component"),
            float(component["charge_value"]), component.get("tier_threshold"), component.get("demand_threshold_kw"))


def document_update_dates(versions: list[dict], as_of: date) -> dict[str, date]:
    """When each official document behind a utility's current live prices last changed (decisions 2026-11-23/24).

    ``versions`` are one utility's live tariff versions, every stored effective date. Each tariff's versions are
    walked in effective-date order. A line identical to an unmatched line of the previous version (same type, unit,
    tier, TOU period, season, sub-component, value and thresholds; the name is ignored) keeps that line's date, so a
    version that only re-dates identical values changes nothing. Any other line took effect on its own effective date,
    else its version's. A line of the previous version left unmatched while its document gained no new line (a line
    removed outright) is a change of that document on the new version's effective date; a replaced value is dated by
    its replacement instead.

    The current lines are those of each tariff's newest version, including a future-dated one (a newer price is
    already stored). A tariff or line whose end date has passed is skipped: an ended price with nothing newer is a
    coverage question (``live_expiring``, ``no_live_output``), not stale data. A line's document is its own source URL,
    else its tariff's, and a document's date is the newest among its current lines and removals.
    """
    by_tariff: dict[object, list[dict]] = {}
    for record in versions:
        if _day(record.get("effective_date")) is not None:
            by_tariff.setdefault(record.get("name"), []).append(record)
    current: dict[str, date] = {}
    removed: dict[str, date] = {}
    for records in by_tariff.values():
        records.sort(key=lambda r: _day(r["effective_date"]))
        pool: dict[tuple, list[tuple[date, str]]] = {}
        changes: dict[str, date] = {}
        lines: list[tuple[dict, date, str]] = []
        for record in records:
            effective = _day(record["effective_date"])
            lines, fresh = [], set()
            for component in record.get("components") or []:
                if not _priced(component):
                    continue
                key = _line_key(component)
                document = component.get("source_url") or record.get("source_url") or "(no source URL)"
                matched = pool.get(key)
                if matched:
                    changed = matched.pop(0)[0]
                else:
                    changed = _day(component.get("effective_date")) or effective
                    fresh.add(document)
                lines.append((component, changed, document))
            for leftovers in pool.values():
                for _, document in leftovers:
                    if document not in fresh:
                        changes[document] = max(changes.get(document, effective), effective)
            pool = {}
            for component, changed, document in lines:
                pool.setdefault(_line_key(component), []).append((changed, document))
        newest_end = _day(records[-1].get("end_date"))
        if newest_end is not None and newest_end < as_of:
            continue
        for component, changed, document in lines:
            end = _day(component.get("end_date"))
            if end is None or end >= as_of:
                current[document] = max(current.get(document, changed), changed)
        for document, changed in changes.items():
            removed[document] = max(removed.get(document, changed), changed)
    return {document: max(changed, removed.get(document, changed)) for document, changed in current.items()}


def stale_documents(versions: list[dict], entry, as_of: date) -> list[dict]:
    """The documents past their one-year due date, after the ledger's exemption or review note.

    A well-formed ``freshness_exempt`` exempts the utility. A well-formed ``freshness_review`` that has not expired
    clears the documents whose flag already existed on its date (owner decision 2026-11-24); a document that turns a
    year old later is still flagged, and a real price change clears its flag by itself. Malformed entries grant
    nothing (they are reported once as ``ledger_invalid``).
    """
    entry = entry if isinstance(entry, dict) else {}
    if "freshness_exempt" in entry:
        try:
            freshness_exemption(entry["freshness_exempt"])
            return []
        except ValueError:
            pass
    window = None
    if "freshness_review" in entry:
        try:
            window = freshness_review_window(entry["freshness_review"])
        except ValueError:
            window = None
    stale = []
    for document, changed in sorted(document_update_dates(versions, as_of).items()):
        due = one_year_after(changed)
        if as_of <= due:
            continue
        if window is not None and window[0] <= as_of <= window[1] and due < window[0]:
            continue
        stale.append({"document": document, "last_change": changed.isoformat(), "due": due.isoformat()})
    return stale


def is_live_on(record: dict, as_of: date) -> bool:
    """A live record that is in effect on the as-of date (an undated end means open-ended)."""
    if record.get("provenance") != "live":
        return False
    effective, end = record.get("effective_date"), record.get("end_date")
    try:
        if effective and date.fromisoformat(effective[:10]) > as_of:
            return False
        if end and date.fromisoformat(end[:10]) < as_of:
            return False
    except ValueError:
        return False
    return True


def validate_ledger(ledger: dict) -> list[str]:
    """Return problems with the ledger's shape (empty when it is well formed)."""
    problems: list[str] = []
    if ledger.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version must be {SCHEMA_VERSION}")
    groups = ledger.get("groups", {})
    if not isinstance(groups, dict):
        problems.append("'groups' must be an object")
        groups = {}
    for gname, group in groups.items():
        _validate_block(problems, f"group {gname}:", group, GROUP_KEYS, require_audit=False)
    utilities = ledger.get("utilities")
    if not isinstance(utilities, dict):
        return problems + ["'utilities' must be an object keyed by registry name"]
    for name, entry in utilities.items():
        where = f"{name}:"
        if isinstance(entry, dict) and "group" in entry and entry["group"] not in groups:
            problems.append(f"{where} unknown group {entry['group']!r}")
        own_audit = isinstance(entry, dict) and "audit" in entry
        group_audit = isinstance(entry, dict) and "audit" in groups.get(entry.get("group"), {})
        _validate_block(problems, where, entry, ENTRY_KEYS, require_audit=own_audit or not group_audit)
    return problems


def _validate_block(problems: list[str], where: str, block, allowed: set, require_audit: bool) -> None:
    """Validate one ledger entry or group; an entry without its own audit must inherit one from its group."""
    if not isinstance(block, dict):
        problems.append(f"{where} entry must be an object")
        return
    for key in sorted(set(block) - allowed):
        problems.append(f"{where} unknown key {key!r}")
    audit = block.get("audit")
    if audit is None and not require_audit:
        pass
    elif not isinstance(audit, dict):
        problems.append(f"{where} 'audit' object is required")
    else:
        for key in ("date", "basis", "source"):
            if not isinstance(audit.get(key), str) or not audit[key].strip():
                problems.append(f"{where} audit.{key} must be a non-empty string")
        if isinstance(audit.get("date"), str):
            try:
                _parse_date(audit["date"], f"{where} audit.date")
            except ValueError as exc:
                problems.append(str(exc))
    for key in LIST_KEYS:
        items = block.get(key, [])
        if not isinstance(items, list) or not all(isinstance(i, str) and i.strip() for i in items):
            problems.append(f"{where} '{key}' must be a list of non-empty strings")
    if "stored_name" in block and (not isinstance(block["stored_name"], str) or not block["stored_name"].strip()):
        problems.append(f"{where} 'stored_name' must be a non-empty string")
    if "manual_update" in block:
        try:
            manual_update_review_by(block["manual_update"])
        except ValueError as exc:
            problems.append(f"{where} {exc}")
    if "freshness_exempt" in block:
        try:
            freshness_exemption(block["freshness_exempt"])
        except ValueError as exc:
            problems.append(f"{where} {exc}")
    if "freshness_review" in block:
        try:
            freshness_review_window(block["freshness_review"])
        except ValueError as exc:
            problems.append(f"{where} {exc}")
        if "freshness_exempt" in block:
            problems.append(f"{where} an exempt utility needs no freshness_review")
    monitor = block.get("monitor", [])
    if not isinstance(monitor, list):
        problems.append(f"{where} 'monitor' must be a list")
        return
    for item in monitor:
        if not isinstance(item, dict) or not isinstance(item.get("item"), str) or not item["item"].strip():
            problems.append(f"{where} each monitor entry needs an 'item' string")
            continue
        try:
            _parse_date(item.get("review_by"), f"{where} monitor review_by")
        except ValueError as exc:
            problems.append(str(exc))


def resolve_entry(ledger: dict, name: str):
    """The ledger entry for a utility with its group's audit and lists folded in (None when absent).

    The entry's own audit wins over the group's; excluded, source_blocked, deferred and monitor lists are the
    group's followed by the entry's.
    """
    entry = ledger.get("utilities", {}).get(name)
    if not isinstance(entry, dict):
        return None
    group = ledger.get("groups", {}).get(entry.get("group"))
    if not isinstance(group, dict):
        return entry
    merged = dict(entry)
    if "audit" not in merged and "audit" in group:
        merged["audit"] = group["audit"]
    for key in (*LIST_KEYS, "monitor"):
        combined = [*group.get(key, []), *entry.get(key, [])] if all(
            isinstance(x, list) for x in (group.get(key, []), entry.get(key, []))) else entry.get(key, [])
        if combined:
            merged[key] = combined
    return merged


def evaluate(registry: dict, rates: list[dict], ledger: dict, as_of: date,
             max_age_days: int = DEFAULT_MAX_AGE_DAYS, warn_days: int = DEFAULT_WARN_DAYS) -> dict:
    """Check every active utility and return findings per utility plus global findings."""
    findings: dict[str, list[dict]] = {}
    global_findings: list[dict] = []

    def add(name: str, level: str, code: str, message: str) -> None:
        findings.setdefault(name, []).append({"level": level, "code": code, "message": message})

    problems = validate_ledger(ledger)
    for problem in problems:
        global_findings.append({"level": "error", "code": "ledger_invalid", "message": problem})
    raw_entries = ledger.get("utilities", {}) if isinstance(ledger.get("utilities"), dict) else {}
    entries = {n: resolve_entry(ledger, n) for n in raw_entries if isinstance(raw_entries[n], dict)}
    entries = {n: e for n, e in entries.items() if e is not None}

    active = active_utilities(registry)
    active_names = {u["name"] for u in active}
    for name in sorted(set(raw_entries) - active_names):
        global_findings.append({"level": "error", "code": "ledger_orphan",
                                "message": f"{name}: ledger entry for a utility that is not an active registry entry"})

    live_by_utility: dict[str, list[dict]] = {}
    versions_by_utility: dict[str, list[dict]] = {}
    for record in rates:
        if record.get("provenance") == "live":
            versions_by_utility.setdefault(record.get("utility_name"), []).append(record)
        if is_live_on(record, as_of):
            live_by_utility.setdefault(record.get("utility_name"), []).append(record)

    freshness: dict[str, list[dict]] = {}
    warn_cutoff = as_of + timedelta(days=warn_days)
    for utility in active:
        name = utility["name"]
        findings.setdefault(name, [])
        entry = entries.get(name)
        stored_name = entry.get("stored_name", name) if isinstance(entry, dict) else name
        live = live_by_utility.get(stored_name, [])
        if not live:
            add(name, "error", "no_live_output", "no live record in effect on the as-of date")
        elif all(r.get("end_date") for r in live):
            last_end = max(date.fromisoformat(r["end_date"][:10]) for r in live)
            if last_end <= warn_cutoff:
                add(name, "warning", "live_expiring",
                    f"every live record ends by {last_end.isoformat()}; the next term or edition must be stored")
        stale = stale_documents(versions_by_utility.get(stored_name, []), entry, as_of)
        if stale:
            freshness[name] = stale
            add(name, "warning", FRESHNESS_CODE, "no price change stored for more than a year in "
                + "; ".join(f"{item['document']} (last change {item['last_change']}, due {item['due']})"
                            for item in stale))
        entry = entries.get(name)
        if not isinstance(entry, dict) or not isinstance(entry.get("audit"), dict):
            add(name, "error", "no_audit", "no ledger audit entry")
            continue
        try:
            audited = _parse_date(entry["audit"].get("date"), "audit.date")
        except ValueError:
            continue
        if (as_of - audited).days > max_age_days:
            add(name, "error", "stale_audit",
                f"last audited {audited.isoformat()}, more than {max_age_days} days before {as_of.isoformat()}")
        for item in entry.get("deferred", []) if isinstance(entry.get("deferred", []), list) else []:
            add(name, "error", "deferred_open", f"deferred item still open: {item}")
        reviews = []
        for item in entry.get("monitor", []) if isinstance(entry.get("monitor", []), list) else []:
            if not isinstance(item, dict):
                continue
            try:
                reviews.append((item.get("item"), _parse_date(item.get("review_by"), "review_by")))
            except ValueError:
                continue
        if "manual_update" in entry:
            try:
                reviews.append(("manual source update of its estimates",
                                manual_update_review_by(entry["manual_update"])))
            except ValueError:
                pass  # reported once as ledger_invalid
        for item, review_by in reviews:
            label = f"{item} (review by {review_by.isoformat()})"
            if review_by < as_of:
                add(name, "error", "monitor_overdue", f"monitor review overdue: {label}")
            elif review_by <= warn_cutoff:
                add(name, "warning", "monitor_due_soon", f"monitor review due soon: {label}")

    errors = Counter()
    warnings = Counter()
    passing = 0
    for name in active_names:
        levels = {f["level"] for f in findings.get(name, [])}
        passing += "error" not in levels
        for f in findings.get(name, []):
            (errors if f["level"] == "error" else warnings)[f["code"]] += 1
    for f in global_findings:
        errors[f["code"]] += 1
    return {
        "as_of": as_of.isoformat(),
        "active_utilities": len(active),
        "passing_utilities": passing,
        "live_utilities": sum(1 for u in active if live_by_utility.get(
            entries[u["name"]].get("stored_name", u["name"]) if isinstance(entries.get(u["name"]), dict)
            else u["name"])),
        "audited_utilities": sum(1 for u in active if isinstance((entries.get(u["name"]) or {}).get("audit"), dict)),
        "errors": dict(errors),
        "warnings": dict(warnings),
        "passed": not errors,
        "global": global_findings,
        "utilities": {n: findings[n] for n in sorted(findings)},
        "freshness": {n: freshness[n] for n in sorted(freshness)},
    }


def _escape(message: str) -> str:
    return message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def format_summary(result: dict) -> str:
    """One line for the public notice and the console."""
    head = (f"{'PASSED' if result['passed'] else 'NOT COMPLETE'} on {result['as_of']}: "
            f"{result['passing_utilities']} of {result['active_utilities']} active utilities pass "
            f"(live output {result['live_utilities']}, audited {result['audited_utilities']})")
    parts = []
    for code in ERROR_ORDER:
        if code in result["errors"]:
            names = sorted(n for n, fs in result["utilities"].items() if any(f["code"] == code for f in fs))
            detail = f" ({', '.join(names)})" if code == "no_live_output" and names else ""
            parts.append(f"{code} {result['errors'][code]}{detail}")
    if result["warnings"]:
        # The run-page notice names the utilities not updated in a year (owner decision 2026-11-23).
        parts.append("warnings: " + ", ".join(
            f"{c} {n}" + (f" ({', '.join(result.get('freshness', {}))})" if c == FRESHNESS_CODE else "")
            for c, n in sorted(result["warnings"].items())))
    return head + ("; " + "; ".join(parts) if parts else "")


def format_report(result: dict, verbose: bool) -> str:
    lines = [format_summary(result), ""]
    for finding in result["global"]:
        lines.append(f"[{finding['level']}] {finding['code']}: {finding['message']}")
    for name, items in result["utilities"].items():
        if not items:
            continue
        shown = items if verbose else [f for f in items if f["code"] != "no_audit"]
        if not verbose and len(shown) < len(items):
            shown = shown + [{"level": "error", "code": "no_audit", "message": "no ledger audit entry"}]
        for finding in shown:
            lines.append(f"[{finding['level']}] {name}: {finding['code']}: {finding['message']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--rates", type=Path, default=RATES_PATH)
    parser.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    parser.add_argument("--as-of", help="ISO date to evaluate (default: today, UTC)")
    parser.add_argument("--max-age-days", type=int, default=DEFAULT_MAX_AGE_DAYS)
    parser.add_argument("--warn-days", type=int, default=DEFAULT_WARN_DAYS)
    parser.add_argument("--json", type=Path, help="write the full result to this file")
    parser.add_argument("--report-only", action="store_true", help="always exit 0 when the inputs could be read")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    try:
        as_of = date.fromisoformat(args.as_of) if args.as_of else datetime.now(timezone.utc).date()
        result = evaluate(_read_json(args.registry), _read_json(args.rates), _read_json(args.ledger), as_of,
                          args.max_age_days, args.warn_days)
    except (GateInputError, ValueError) as exc:
        print(f"Coverage gate could not run: {exc}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print(f"::error title={NOTICE_TITLE}::{_escape(str(exc))}")
        return 1

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(format_report(result, args.verbose))
    if args.json:
        args.json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        level = "notice" if result["passed"] else "warning"
        print(f"::{level} title={NOTICE_TITLE}::{_escape(format_summary(result))}")
    return 0 if result["passed"] or args.report_only else 1


if __name__ == "__main__":
    sys.exit(main())
