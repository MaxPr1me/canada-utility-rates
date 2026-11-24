"""Deterministic tests for scripts/coverage_gate.py and its ledger (no network, no database)."""
import importlib.util
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 10, 30)


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gate = _load_script("coverage_gate")

AUDIT = {"date": "2026-10-07", "basis": "test audit", "source": "tests"}


def _registry(*entries):
    return {"utilities": [{"name": n, "status": s} for n, s in entries]}


def _live(name, effective="2026-01-01", end=None, provenance="live"):
    return {"utility_name": name, "provenance": provenance, "effective_date": effective, "end_date": end}


def _ledger(**entries):
    return {"schema_version": 1, "utilities": entries}


def _codes(result, name):
    return {f["code"] for f in result["utilities"][name]}


def test_is_live_on_requires_live_provenance_and_an_effective_window():
    assert gate.is_live_on(_live("A"), AS_OF)
    assert not gate.is_live_on(_live("A", provenance="seed"), AS_OF)
    assert not gate.is_live_on(_live("A", effective="2026-11-01"), AS_OF)
    assert not gate.is_live_on(_live("A", end="2026-10-29"), AS_OF)
    assert gate.is_live_on(_live("A", end="2026-10-30"), AS_OF)
    assert not gate.is_live_on(_live("A", effective="not a date"), AS_OF)


def test_clean_utility_passes_and_merged_or_retired_entries_are_skipped():
    registry = _registry(("A", "partial"), ("B", "merged"), ("C", "retired"))
    result = gate.evaluate(registry, [_live("A")], _ledger(A={"audit": AUDIT}), AS_OF)
    assert result["passed"] and result["active_utilities"] == 1 and result["passing_utilities"] == 1
    assert set(result["utilities"]) == {"A"}


def test_seed_only_utility_has_no_live_output():
    result = gate.evaluate(_registry(("A", "active")), [_live("A", provenance="seed")],
                           _ledger(A={"audit": AUDIT}), AS_OF)
    assert not result["passed"] and _codes(result, "A") == {"no_live_output"}
    assert result["live_utilities"] == 0


def test_missing_and_stale_audit_fail():
    registry = _registry(("A", "active"), ("B", "active"))
    ledger = _ledger(B={"audit": {**AUDIT, "date": "2026-01-01"}})
    result = gate.evaluate(registry, [_live("A"), _live("B")], ledger, AS_OF, max_age_days=120)
    assert _codes(result, "A") == {"no_audit"}
    assert _codes(result, "B") == {"stale_audit"}
    assert result["audited_utilities"] == 1


def test_deferred_items_fail_but_exclusions_and_blocked_items_do_not():
    entry = {"audit": AUDIT, "excluded": ["lighting"], "source_blocked": ["net metering"], "deferred": ["RS1892"]}
    result = gate.evaluate(_registry(("A", "active")), [_live("A")], _ledger(A=entry), AS_OF)
    assert _codes(result, "A") == {"deferred_open"}
    entry.pop("deferred")
    assert gate.evaluate(_registry(("A", "active")), [_live("A")], _ledger(A=entry), AS_OF)["passed"]


def test_monitor_items_warn_when_due_soon_and_fail_when_overdue():
    def result_for(review_by):
        entry = {"audit": AUDIT, "monitor": [{"item": "GRA decision", "review_by": review_by}]}
        return gate.evaluate(_registry(("A", "active")), [_live("A")], _ledger(A=entry), AS_OF)

    assert result_for("2027-03-01")["passed"] and not result_for("2027-03-01")["warnings"]
    soon = result_for("2026-11-15")
    assert soon["passed"] and soon["warnings"] == {"monitor_due_soon": 1}
    overdue = result_for("2026-10-29")
    assert not overdue["passed"] and overdue["errors"] == {"monitor_overdue": 1}


def test_manual_update_decision_is_validated_and_its_review_date_is_monitored():
    # Owner decision 2026-11-19 (Maritime Electric): the yearly manual-update review reuses the monitor codes.
    def result_for(review_by, **change):
        manual = {"reason": "blocked on GitHub", "decided": "2026-10-01", "review_by": review_by, **change}
        entry = {"audit": AUDIT, "manual_update": manual}
        return gate.evaluate(_registry(("A", "active")), [_live("A")], _ledger(A=entry), AS_OF)

    assert result_for("2027-09-01")["passed"] and not result_for("2027-09-01")["warnings"]
    assert result_for("2026-11-15")["warnings"] == {"monitor_due_soon": 1}
    overdue = result_for("2026-10-29")
    assert overdue["errors"] == {"monitor_overdue": 1}
    assert "manual source update" in overdue["utilities"]["A"][0]["message"]
    assert result_for("2026-09-01")["errors"] == {"ledger_invalid": 1}  # review before the decision
    assert "ledger_invalid" in result_for("2027-09-01", reason=" ")["errors"]
    assert "ledger_invalid" in result_for("2027-09-01", extra="x")["errors"]
    assert gate.evaluate(_registry(("A", "active")), [_live("A", provenance="seed")], _ledger(
        A={"audit": AUDIT, "manual_update": {"reason": "r", "decided": "2026-10-01", "review_by": "2027-09-01"}}),
        AS_OF)["errors"] == {"no_live_output": 1}


def test_live_records_that_all_end_soon_warn_and_after_the_end_fail():
    ledger = _ledger(A={"audit": AUDIT})
    registry = _registry(("A", "active"))
    soon = gate.evaluate(registry, [_live("A", end="2026-12-31")], ledger, date(2026, 12, 5))
    assert soon["passed"] and soon["warnings"] == {"live_expiring": 1}
    far = gate.evaluate(registry, [_live("A", end="2026-12-31")], ledger, AS_OF)
    assert far["passed"] and not far["warnings"]
    open_ended = gate.evaluate(registry, [_live("A", end="2026-12-31"), _live("A")], ledger, date(2026, 12, 5))
    assert not open_ended["warnings"]
    after = gate.evaluate(registry, [_live("A", end="2026-12-31")], ledger, date(2027, 1, 2))
    assert _codes(after, "A") == {"no_live_output"}


def test_stored_name_maps_a_registry_name_to_the_name_in_the_export():
    registry = _registry(("Liberty Utilities NB", "partial"))
    ledger = _ledger(**{"Liberty Utilities NB": {"audit": AUDIT, "stored_name": "Liberty Utilities Gas NB"}})
    assert gate.evaluate(registry, [_live("Liberty Utilities Gas NB")], ledger, AS_OF)["passed"]
    assert not gate.evaluate(registry, [_live("Liberty Utilities Gas NB")], _ledger(
        **{"Liberty Utilities NB": {"audit": AUDIT}}), AS_OF)["passed"]


def test_orphan_ledger_entries_and_invalid_ledgers_are_errors():
    registry = _registry(("A", "active"), ("M", "merged"))
    result = gate.evaluate(registry, [_live("A")], _ledger(A={"audit": AUDIT}, M={"audit": AUDIT}), AS_OF)
    assert result["errors"] == {"ledger_orphan": 1}
    bad = _ledger(A={"audit": {"date": "yesterday", "basis": "", "source": "x"}, "deferred": [""],
                     "monitor": [{"item": "x"}], "surprise": 1})
    problems = gate.validate_ledger(bad)
    assert any("audit.date" in p for p in problems) and any("audit.basis" in p for p in problems)
    assert any("'deferred'" in p for p in problems) and any("review_by" in p for p in problems)
    assert any("unknown key 'surprise'" in p for p in problems)
    assert gate.validate_ledger({"schema_version": 2, "utilities": {}}) == ["schema_version must be 1"]
    assert not gate.evaluate(registry, [_live("A")], bad, AS_OF)["passed"]


def test_summary_names_utilities_without_live_output_and_counts_codes():
    registry = _registry(("A", "active"), ("B", "active"))
    result = gate.evaluate(registry, [_live("B")], _ledger(B={"audit": AUDIT, "deferred": ["x"]}), AS_OF)
    summary = gate.format_summary(result)
    assert summary.startswith("NOT COMPLETE on 2026-10-30: 0 of 2 active utilities pass")
    assert "no_live_output 1 (A)" in summary and "no_audit 1" in summary and "deferred_open 1" in summary


SOURCE = "https://example.test/schedule"
OTHER = "https://example.test/other"


def _version(name, effective, *lines, tariff="T", end=None, source=SOURCE):
    """A live tariff version; each line is (component_type, charge_value[, extra component fields])."""
    components = [{"component_type": ctype, "component_name": f"{ctype} charge", "charge_value": value,
                   "charge_unit": "$/kWh", **(extra[0] if extra else {})} for ctype, value, *extra in lines]
    return {"utility_name": name, "name": tariff, "provenance": "live", "effective_date": effective,
            "end_date": end, "source_url": source, "components": components}


def test_redated_or_renamed_identical_values_are_not_a_price_change():
    # Owner decisions 2026-11-23 (re-dated identical values do not count) and 2026-11-24 (renames do not count).
    v1 = _version("A", "2025-01-01", ("energy", 0.1), ("fixed", 10.0))
    v2 = _version("A", "2026-01-01", ("energy", 0.1, {"component_name": "Energy (renamed)"}), ("fixed", 10))
    assert gate.document_update_dates([v2, v1], AS_OF) == {SOURCE: date(2025, 1, 1)}
    v3 = _version("A", "2026-07-01", ("energy", 0.11), ("fixed", 10.0))
    assert gate.document_update_dates([v1, v2, v3], AS_OF) == {SOURCE: date(2026, 7, 1)}


def test_threshold_changes_added_and_removed_lines_are_price_changes():
    tier = {"tier_number": 1, "tier_threshold": 1000}
    base = _version("A", "2025-01-01", ("energy", 0.1, tier), ("fixed", 10.0))

    def changed(*lines, effective="2026-03-01"):
        return gate.document_update_dates([base, _version("A", effective, *lines)], AS_OF)[SOURCE]

    assert changed(("energy", 0.1, {**tier, "tier_threshold": 1200}), ("fixed", 10.0)) == date(2026, 3, 1)
    assert changed(("energy", 0.1, tier)) == date(2026, 3, 1)
    assert changed(("energy", 0.1, tier), ("fixed", 10.0), ("rider", 0.002)) == date(2026, 3, 1)
    # A replaced value is dated by its replacement, not by the later version that first stored it.
    assert changed(("energy", 0.12, {**tier, "effective_date": "2026-01-01"}), ("fixed", 10.0)) == date(2026, 1, 1)


def test_zero_valueless_and_ended_prices_are_ignored():
    records = [
        _version("A", "2026-06-01", ("energy", 0.1), ("carbon", 0.0, {"source_url": OTHER}),
                 ("market", None, {"source_url": OTHER}),
                 ("rider", 0.01, {"source_url": OTHER, "effective_date": "2024-01-01", "end_date": "2026-09-30"})),
        _version("A", "2024-01-01", ("fixed", 5.0), tariff="Ended", end="2026-06-30", source=OTHER),
    ]
    assert gate.document_update_dates(records, AS_OF) == {SOURCE: date(2026, 6, 1)}
    assert gate.document_update_dates(records, date(2026, 9, 1))[OTHER] == date(2024, 1, 1)


def test_a_stale_document_behind_a_fresh_one_is_flagged_after_its_anniversary():
    # Owner decision 2026-11-24: each document is checked on its own, so a fresh monthly price cannot hide a
    # delivery schedule that has not changed for a year.
    records = [_version("A", "2026-10-01", ("commodity", 5.0),
                        ("fixed", 22.5, {"source_url": OTHER, "effective_date": "2025-10-30"}))]

    def result_on(as_of):
        return gate.evaluate(_registry(("A", "active")), records, _ledger(A={"audit": AUDIT}), as_of)

    on_due_date = result_on(date(2026, 10, 30))
    assert on_due_date["passed"] and not on_due_date["warnings"] and on_due_date["freshness"] == {}
    after = result_on(date(2026, 10, 31))
    assert after["passed"] and after["warnings"] == {"not_updated_in_a_year": 1}
    assert after["freshness"] == {"A": [{"document": OTHER, "last_change": "2025-10-30", "due": "2026-10-30"}]}
    assert "not_updated_in_a_year 1 (A)" in gate.format_summary(after)
    assert gate.one_year_after(date(2024, 2, 29)) == date(2025, 2, 28)


def test_review_note_clears_only_existing_flags_until_it_expires():
    records = [_version("A", "2025-01-01", ("fixed", 10.0)),
               _version("A", "2025-12-01", ("energy", 0.1), tariff="U", source=OTHER)]
    review = {"reviewed": "2026-06-01", "finding": "legitimate", "basis": "prices fixed by order"}

    def stale(as_of, **change):
        return [item["document"] for item in
                gate.stale_documents(records, {"freshness_review": {**review, **change}}, as_of)]

    assert stale(date(2026, 5, 31)) == [SOURCE]
    assert stale(date(2026, 6, 1)) == []
    assert stale(date(2026, 12, 2)) == [OTHER]  # turned a year old after the review
    assert stale(date(2027, 6, 1)) == [OTHER]
    assert stale(date(2027, 6, 2)) == [OTHER, SOURCE]  # the note lasts one year
    assert stale(date(2026, 9, 2), review_by="2026-09-01") == [SOURCE]  # or until an earlier date it names


def test_freshness_exemption_and_review_note_are_validated():
    exempt = {"reason": "publishes no price", "decided": "2026-11-23"}
    records = [_version("A", "2020-01-01", ("fixed", 10.0))]
    assert gate.stale_documents(records, {"freshness_exempt": exempt}, AS_OF) == []
    assert gate.stale_documents(records, {"freshness_exempt": {**exempt, "reason": " "}}, AS_OF)  # grants nothing

    def problems(**entry):
        return gate.validate_ledger(_ledger(A={"audit": AUDIT, **entry}))

    review = {"reviewed": "2026-11-24", "finding": "legitimate", "basis": "rates fixed until 2027"}
    assert problems(freshness_exempt=exempt) == problems(freshness_review=review) == []
    assert problems(freshness_review={**review, "review_by": "2027-06-30"}) == []
    assert problems(freshness_exempt={**exempt, "until": "2027-01-01"})  # no end date (owner decision 2026-11-24)
    for bad in ({**review, "review_by": "2027-11-25"}, {**review, "review_by": "2026-11-24"},
                {**review, "finding": "fine"}, {"reviewed": "2026-11-24", "finding": "legitimate"}):
        assert problems(freshness_review=bad), bad
    assert problems(freshness_exempt=exempt, freshness_review=review)
    result = gate.evaluate(_registry(("A", "active")), records,
                           _ledger(A={"audit": AUDIT, "freshness_review": {**review, "finding": "fine"}}), AS_OF)
    assert result["errors"] == {"ledger_invalid": 1} and result["warnings"] == {"not_updated_in_a_year": 1}


def _write(tmp_path, registry, rates, ledger):
    paths = {}
    for key, value in (("registry", registry), ("rates", rates), ("ledger", ledger)):
        paths[key] = tmp_path / f"{key}.json"
        paths[key].write_text(json.dumps(value), encoding="utf-8")
    return ["--registry", str(paths["registry"]), "--rates", str(paths["rates"]), "--ledger", str(paths["ledger"]),
            "--as-of", "2026-10-30"]


def test_cli_exit_codes_report_only_and_json_output(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    args = _write(tmp_path, _registry(("A", "active")), [_live("A", provenance="seed")], _ledger(A={"audit": AUDIT}))
    out = tmp_path / "result.json"
    assert gate.main(args + ["--json", str(out)]) == 1
    assert json.loads(out.read_text(encoding="utf-8"))["errors"] == {"no_live_output": 1}
    assert "no_live_output" in capsys.readouterr().out
    assert gate.main(args + ["--report-only"]) == 0
    good = _write(tmp_path, _registry(("A", "active")), [_live("A")], _ledger(A={"audit": AUDIT}))
    assert gate.main(good) == 0


def test_cli_unreadable_input_fails_even_with_report_only(tmp_path, capsys):
    args = _write(tmp_path, _registry(("A", "active")), [], _ledger())
    (tmp_path / "rates.json").write_text("not json", encoding="utf-8")
    assert gate.main(args + ["--report-only"]) == 1
    assert "could not run" in capsys.readouterr().err


def test_github_annotation_is_a_single_escaped_line(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    args = _write(tmp_path, _registry(("A", "active")), [], _ledger(A={"audit": AUDIT}))
    gate.main(args + ["--report-only"])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.startswith("::")]
    assert len(lines) == 1 and lines[0].startswith("::warning title=Coverage gate::NOT COMPLETE")
    assert "\n" not in lines[0]
    assert gate._escape("a%b\nc") == "a%25b%0Ac"


def test_the_committed_ledger_is_well_formed_and_only_names_active_registry_utilities():
    ledger = json.loads((ROOT / "data" / "sources" / "coverage_ledger.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "data" / "sources" / "registry.json").read_text(encoding="utf-8"))
    assert gate.validate_ledger(ledger) == []
    active = {u["name"] for u in gate.active_utilities(registry)}
    assert set(ledger["utilities"]) <= active
    today = datetime.now(timezone.utc).date()
    for name in ledger["utilities"]:
        assert date.fromisoformat(gate.resolve_entry(ledger, name)["audit"]["date"]) <= today, name


def test_committed_ledger_covers_every_active_utility_with_a_dated_audit():
    ledger = json.loads((ROOT / "data" / "sources" / "coverage_ledger.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "data" / "sources" / "registry.json").read_text(encoding="utf-8"))
    for utility in gate.active_utilities(registry):
        entry = gate.resolve_entry(ledger, utility["name"])
        assert entry is not None and isinstance(entry.get("audit"), dict), utility["name"]


def test_groups_give_entries_an_audit_and_standard_exclusions():
    ledger = {"schema_version": 1,
              "groups": {"g": {"audit": AUDIT, "excluded": ["lighting"], "deferred": ["group item"]}},
              "utilities": {"A": {"group": "g", "excluded": ["standby"], "deferred": ["own item"]},
                            "B": {"group": "g", "audit": {**AUDIT, "date": "2026-10-20"}}}}
    assert gate.validate_ledger(ledger) == []
    a = gate.resolve_entry(ledger, "A")
    assert a["audit"] == AUDIT and a["excluded"] == ["lighting", "standby"]
    assert a["deferred"] == ["group item", "own item"]
    assert gate.resolve_entry(ledger, "B")["audit"]["date"] == "2026-10-20"
    assert gate.resolve_entry(ledger, "missing") is None
    result = gate.evaluate(_registry(("A", "active"), ("B", "active")), [_live("A"), _live("B")], ledger, AS_OF)
    assert result["audited_utilities"] == 2 and result["errors"] == {"deferred_open": 3}


def test_group_problems_are_reported():
    bad = {"schema_version": 1, "groups": {"g": {"excluded": [""], "stored_name": "x"}},
           "utilities": {"A": {"group": "nope"}, "B": {"group": "g"}, "C": {}}}
    problems = gate.validate_ledger(bad)
    assert any("group g:" in p and "'excluded'" in p for p in problems)
    assert any("group g:" in p and "unknown key 'stored_name'" in p for p in problems)
    assert any(p.startswith("A:") and "unknown group 'nope'" in p for p in problems)
    assert any(p.startswith("B:") and "'audit' object is required" in p for p in problems)
    assert any(p.startswith("C:") and "'audit' object is required" in p for p in problems)
    assert gate.validate_ledger({"schema_version": 1, "groups": [], "utilities": {}}) == ["'groups' must be an object"]


def test_scrape_workflow_runs_the_gate_in_report_only_mode_without_blocking_the_save():
    yaml = pytest.importorskip("yaml")
    scrape = yaml.safe_load((ROOT / ".github" / "workflows" / "scrape.yml").read_text(encoding="utf-8"))
    names = [step["name"] for step in scrape["jobs"]["scrape"]["steps"]]
    step = scrape["jobs"]["scrape"]["steps"][names.index("Report live-rate coverage gate")]
    assert step["continue-on-error"] is True and "--report-only" in step["run"]
    assert names.index("Export JSON for site") < names.index("Report live-rate coverage gate") \
        < names.index("Check database history before upload")
