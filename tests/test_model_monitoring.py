"""Offline regressions for semantic model changes and reliable refresh evidence."""
import copy
import json
import os
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pipeline import model_monitoring as monitoring


@pytest.fixture
def document():
    return {
        "version": 1, "method_version": "test-method",
        "generated_at": "2026-11-01T08:15:00+00:00", "as_of": "2026-11-01",
        "assumptions": {"days_per_month": 30.4375, "synthetic_profiles": {"test": {"hours": 12}}},
        "input": {"latest_record_created_at": "2026-11-01"},
        "models": [{
            "id": "example", "key": {"province": "ON", "fuel": "electricity"},
            "state": "modeled", "provenance": "modeled", "cost_basis": "delivery_and_energy",
            "coverage": {"contributing_utilities": ["A", "B"]},
            "generated_from": {"as_of": "2026-11-01", "input": "rates.json"},
            "method": "A comparison. Generated 2026-11-01 from rates.json.",
            "levels": [{
                "id": "typical", "kwh": 1000, "kw": None,
                "without_tax": {"median": 100, "n": 2}, "with_tax": {"median": 100, "n": 2, "lines": []},
                "utilities": [{"utility": "A", "cost_with_tax": 99}, {"utility": "B", "cost_with_tax": 101}],
                "illustrative_all_in": {"with_tax": {"median": 900}},
            }],
            "illustrative": {"available": True},
        }],
    }


def receipt(document, previous=None, inputs=None):
    return monitoring.generation_receipt(document, previous=previous or {"status": "absent"}, inputs=inputs)


def next_generation(document, history):
    changed = copy.deepcopy(document)
    changed["generated_at"] = "2026-11-15T08:15:00+00:00"
    previous = {"status": "known", "generated_at": history["last_refresh"]["generated_at"],
                "fingerprint": history["last_refresh"]["model_fingerprint"]}
    return changed, previous


@pytest.mark.parametrize("old,new,material,percent", [
    (100, 104.99, False, 4.99), (100, 105, True, 5), (100, 105.01, True, 5.01),
    (100, 95, True, -5), (0.2, 0.21, True, 5), (-100, -105, True, -5),
    (-100, 100, True, 200),
])
def test_material_threshold_uses_decimal_after_tax_movement(document, old, new, material, percent):
    document["models"][0]["levels"][0]["with_tax"]["median"] = old
    after = copy.deepcopy(document)
    after["models"][0]["levels"][0]["with_tax"]["median"] = new
    changes = monitoring.compare_models(monitoring.semantic_models(document), monitoring.semantic_models(after))
    assert len(changes) == 1
    assert changes[0]["material"] is material
    assert changes[0]["after_tax_percent"] == pytest.approx(percent)


@pytest.mark.parametrize("old,new,comparison", [(0, 5, "from_zero"), (None, 5, "availability_changed"),
                                               (5, None, "availability_changed")])
def test_zero_and_missing_are_not_fabricated_percentages(document, old, new, comparison):
    document["models"][0]["levels"][0]["with_tax"]["median"] = old
    after = copy.deepcopy(document)
    after["models"][0]["levels"][0]["with_tax"]["median"] = new
    change = monitoring.compare_models(monitoring.semantic_models(document), monitoring.semantic_models(after))[0]
    assert change["comparison"] == comparison
    assert change["after_tax_percent"] is None and not change["material"]


def test_before_tax_only_changes_are_recorded_but_not_material(document):
    after = copy.deepcopy(document)
    after["models"][0]["levels"][0]["without_tax"]["median"] = 120
    change = monitoring.compare_models(monitoring.semantic_models(document), monitoring.semantic_models(after))[0]
    assert change["before"]["without_tax"]["median"] == 100
    assert change["after"]["without_tax"]["median"] == 120
    assert change["after_tax_percent"] == 0 and not change["material"]


def test_usage_and_tax_changes_are_not_lost(document):
    after = copy.deepcopy(document)
    level = after["models"][0]["levels"][0]
    level["kwh"] = 2000
    level["with_tax"] = {"median": 200, "lines": [{"name": "Rebate", "rate": 0.1}]}
    change = monitoring.compare_models(monitoring.semantic_models(document), monitoring.semantic_models(after))[0]
    assert change["comparison"] == "basis_changed"
    assert change["fields"] == ["kwh", "with_tax"]
    assert not change["material"]


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf"), True, "100"])
def test_invalid_costs_fail_explicitly(document, invalid):
    document["models"][0]["levels"][0]["with_tax"]["median"] = invalid
    with pytest.raises(ValueError, match="median"):
        monitoring.semantic_models(document)


def test_timestamps_order_and_synthetic_changes_do_not_change_semantics(document):
    after = copy.deepcopy(document)
    after["generated_at"] = "2026-11-15T10:00:00Z"
    after["as_of"] = "2026-11-15"
    after["models"][0]["generated_from"] = {"as_of": "2026-11-15", "input": "/another/machine/rates.json"}
    after["models"][0]["method"] = "A comparison. Generated 2026-11-15 from /another/machine/rates.json."
    after["models"][0]["levels"][0]["utilities"].reverse()
    after["models"][0]["coverage"]["contributing_utilities"].reverse()
    after["models"][0]["illustrative"] = {"available": False}
    after["models"][0]["levels"][0]["illustrative_all_in"]["with_tax"]["median"] = 5000
    after["assumptions"]["synthetic_profiles"]["test"]["hours"] = 18
    assert monitoring.semantic_models(document) == monitoring.semantic_models(after)


def test_input_hashes_exclude_synthetic_edits_but_preserve_first_match_order():
    inputs = {"crosswalk": {"rules": [{"id": "first"}, {"id": "second"}]},
              "usage_levels": {"electricity": {"levels": [1000]}, "synthetic_profiles": {"hours": 12},
                               "updated": "before"}}
    hashes = monitoring.input_fingerprints(inputs)
    inputs["usage_levels"].update(synthetic_profiles={"hours": 20}, updated="after")
    assert monitoring.input_fingerprints(inputs) == hashes
    inputs["crosswalk"]["rules"].reverse()
    assert monitoring.input_fingerprints(inputs)["crosswalk"] != hashes["crosswalk"]


def test_observed_benchmarks_are_compared_separately(document):
    level = document["models"][0]["levels"][0]
    level["market_benchmark"] = {"available": True, "without_tax": {"median": 200},
                                 "with_tax": {"median": 200}}
    after = copy.deepcopy(document)
    after["models"][0]["levels"][0]["market_benchmark"]["with_tax"]["median"] = 220
    changes = monitoring.compare_models(monitoring.semantic_models(document), monitoring.semantic_models(after))
    assert len(changes) == 1 and changes[0]["kind"] == "benchmark" and changes[0]["material"]


def test_baseline_unchanged_refresh_and_rerun_are_not_historical_changes(document):
    history = monitoring.record_refresh(None, document, receipt(document))
    assert history["events"][0]["kind"] == "baseline" and history["events"][0]["changes"] == []
    assert history["last_changed"]["example"] is None
    after, previous = next_generation(document, history)
    next_receipt = receipt(after, previous)
    assert next_receipt["change_status"] == "unchanged"
    updated = monitoring.record_refresh(history, after, next_receipt)
    assert updated["events"] == history["events"]
    assert updated["last_refresh"]["generated_at"] == after["generated_at"]
    assert monitoring.record_refresh(updated, after, next_receipt) == updated


def test_failed_generation_cannot_be_mistaken_for_unchanged_success(document):
    history = monitoring.record_refresh(None, document, receipt(document))
    failed = monitoring.generation_receipt(None, previous={"status": "known"}, error="source failed")
    with pytest.raises(ValueError, match="receipt"):
        monitoring.record_refresh(history, document, failed)
    assert history["last_changed"]["example"] is None


def test_small_change_and_a_tracking_gap_are_both_recorded(document):
    history = monitoring.record_refresh(None, document, receipt(document))
    after, previous = next_generation(document, history)
    after["models"][0]["levels"][0]["with_tax"]["median"] = 101
    previous["generated_at"] = "2026-11-10T10:00:00+00:00"
    updated = monitoring.record_refresh(history, after, receipt(after, previous))
    assert updated["events"][:-1] == history["events"]
    event = updated["events"][-1]
    assert event["history_gap"] and event["changes"][0]["after_tax_percent"] == 1
    assert updated["last_changed"]["example"] == event["recorded_at"]


def test_history_corruption_and_output_failure_preserve_prior_data(document, tmp_path, monkeypatch):
    history = monitoring.record_refresh(None, document, receipt(document))
    history["events"][0]["history_gap"] = True
    with pytest.raises(ValueError, match="integrity"):
        monitoring.record_refresh(history, document, receipt(document))
    target = tmp_path / "history.json"
    target.write_text("previous", encoding="utf-8")

    def reject_replace(*args):
        raise OSError("disk full")

    monkeypatch.setattr(monitoring.os, "replace", reject_replace)
    with pytest.raises(OSError, match="disk full"):
        monitoring.write_json(target, {"new": "history"})
    assert target.read_text(encoding="utf-8") == "previous"
    assert not target.with_name("history.json.tmp").exists()


def test_receipt_failure_is_logged_not_a_primary_publication_failure(document, monkeypatch, caplog, tmp_path):
    def unavailable(*args):
        raise OSError("disk full")

    monkeypatch.setattr(monitoring, "write_json", unavailable)
    monitoring.save_generation_receipt(tmp_path / "receipt.json", document, previous={"status": "absent"})
    assert "monitoring cannot verify this refresh" in caplog.text


def workflow_context(document, *, full=True, publication="success", checked_at="2026-11-01T09:00:00Z", run_id=1):
    identity = {"id": str(run_id), "attempt": "1"}
    generation = receipt(document)
    generation.update(run=identity, checked_at=checked_at)
    source = {
        "version": 1, "kind": "source_check", "run": identity, "checked_at": checked_at,
        "scope": {"full": full}, "expected_utilities": ["A"],
        "summary": {"rows": [{"utility": "A", "live": 1, "seed": 0, "invalid": 0, "status": "live", "error": None}]},
    }
    run = {
        "id": run_id, "run_attempt": 1, "status": "completed", "conclusion": "success",
        "updated_at": checked_at, "created_at": checked_at, "html_url": f"https://github.com/test/runs/{run_id}",
        "evidence": {
            "model-generation.json": generation, "source-summary.json": source,
            "monitor-status.json": {
                "version": 1, "kind": "workflow_outcome", "run": identity, "checked_at": checked_at,
                "publication": publication, "sources": "success", "failure_reported": False,
                "history_step": "success", "history_recorded": True,
            },
        },
    }
    return {"workflows": {"scrape.yml": {"schedules": ["0 8 1 * *"], "runs": [run]}}}


def workflow_check(context, now):
    return next(check for check in monitoring.workflow_checks(context, monitoring.timestamp(now))
                if check["id"] == "workflow:scrape.yml")


@pytest.mark.parametrize("now,expected", [("2026-11-02T08:00:00Z", None), ("2026-11-02T08:00:01Z", False)])
@pytest.mark.parametrize("status", ["queued", "in_progress", "completed"])
def test_unverified_or_missing_refresh_is_overdue_only_after_the_grace(document, now, expected, status):
    context = workflow_context(document)
    run = context["workflows"]["scrape.yml"]["runs"][0]
    run.update(status=status, evidence={})
    assert workflow_check(context, now)["ok"] is expected


def test_full_receipt_not_workflow_badge_proves_refresh_scope(document):
    context = workflow_context(document, full=False)
    assert workflow_check(context, "2026-11-03T12:00:00Z")["ok"] is False
    context = workflow_context(document)
    assert workflow_check(context, "2026-11-03T12:00:00Z")["ok"] is True
    source = context["workflows"]["scrape.yml"]["runs"][0]["evidence"]["source-summary.json"]
    source["summary"]["rows"][0].update(live=0, seed=2, status="seed only")
    checks = monitoring.workflow_checks(context, monitoring.timestamp("2026-11-03T12:00:00Z"))
    assert next(check for check in checks if check["id"] == "source:A")["ok"] is False


def source_receipt(**row):
    base = {"utility": "LDC", "live": 9, "seed": 1, "invalid": 0, "status": "live + seed", "error": None}
    return {"version": 1, "kind": "source_check", "checked_at": "2026-11-18T10:00:00Z",
            "scope": {"full": True}, "expected_utilities": ["LDC"], "summary": {"rows": [{**base, **row}]}}


@pytest.mark.parametrize("row,healthy", [
    ({"excluded_seed": 1}, True),  # labelled street-lighting estimate only (owner decision 2026-11-18)
    ({"seed": 2, "excluded_seed": 1}, False),  # another estimate still fails the source
    ({}, False),  # older receipt without the field stays strict
    ({"live": 0, "excluded_seed": 1, "status": "seed only"}, False),
])
def test_only_labelled_excluded_class_estimates_are_ignored(row, healthy):
    assert monitoring.source_checks(source_receipt(**row))[0]["ok"] is healthy


def test_excluded_estimates_cannot_exceed_the_estimate_count():
    with pytest.raises(ValueError, match="invalid source receipt counts"):
        monitoring.source_checks(source_receipt(excluded_seed=2))


MANUAL_LEDGER = {"utilities": {
    "LDC": {"manual_update": {"reason": "blocked on GitHub", "decided": "2026-11-19", "review_by": "2027-09-01"}},
    "Broken": {"manual_update": {"reason": "missing review date", "decided": "2026-11-19"}},
}}


@pytest.mark.parametrize("checked_at,row,healthy", [
    ("2027-09-01T23:00:00Z", {"live": 0, "seed": 2, "status": "seed only"}, True),  # on the review date
    ("2027-09-02T10:00:00Z", {"live": 0, "seed": 2, "status": "seed only"}, False),  # the yearly reminder
    ("2026-11-20T10:00:00Z", {"live": 0, "seed": 2, "invalid": 1, "status": "seed only"}, False),
    ("2026-11-20T10:00:00Z", {"live": 0, "seed": 0, "status": "no valid records"}, False),
    ("2026-11-20T10:00:00Z", {"live": 0, "seed": 2, "error": "boom", "status": "failed"}, False),
    ("2026-11-20T10:00:00Z", {"live": 10, "seed": 0, "status": "live"}, True),  # a live source stays healthy
])
def test_manual_update_utility_estimates_are_accepted_only_until_review(checked_at, row, healthy):
    # Owner decision 2026-11-19 (Maritime Electric): ledger manual_update, yearly review reminder.
    receipt = {**source_receipt(**row), "checked_at": checked_at}
    (check,) = monitoring.source_checks(receipt, monitoring.manual_update_reviews(MANUAL_LEDGER))
    assert check["ok"] is healthy
    if checked_at.startswith("2027-09-02"):
        assert "manual update review was due by 2027-09-01" in check["details"][0]


def test_manual_update_exemption_needs_a_wellformed_ledger_decision():
    reviews = monitoring.manual_update_reviews(MANUAL_LEDGER)
    assert reviews == {"LDC": datetime(2027, 9, 1).date()}
    receipt = source_receipt(utility="Broken", live=0, seed=2, status="seed only")
    receipt["expected_utilities"] = ["Broken"]
    assert monitoring.source_checks(receipt, reviews)[0]["ok"] is False
    assert monitoring.manual_update_reviews({"utilities": []}) == {}


def test_failed_publication_is_reported_immediately_not_given_a_grace(document):
    context = workflow_context(document, publication="failure")
    assert workflow_check(context, "2026-11-01T10:00:00Z")["ok"] is False


def test_newer_failed_refresh_is_not_hidden_by_an_older_success(document):
    context = workflow_context(document, publication="failure", checked_at="2026-11-02T10:00:00Z", run_id=2)
    context["workflows"]["scrape.yml"]["runs"] += workflow_context(document)["workflows"]["scrape.yml"]["runs"]
    assert workflow_check(context, "2026-11-03T12:00:00Z")["ok"] is False


def test_an_older_reported_failure_cannot_suppress_a_new_failure(document):
    context = workflow_context(document, publication="failure", checked_at="2026-11-02T10:00:00Z", run_id=2)
    older = workflow_context(document, publication="failure")["workflows"]["scrape.yml"]["runs"][0]
    older["evidence"]["monitor-status.json"]["failure_reported"] = True
    context["workflows"]["scrape.yml"]["runs"].append(older)
    check = workflow_check(context, "2026-11-03T12:00:00Z")
    assert check["ok"] is False and not check["reported_elsewhere"]


def test_latest_unverified_generation_is_not_hidden_by_an_older_success(document):
    context = workflow_context(document, checked_at="2026-11-02T10:00:00Z", run_id=2)
    context["workflows"]["scrape.yml"]["runs"][0]["evidence"] = {}
    context["workflows"]["scrape.yml"]["runs"] += workflow_context(document)["workflows"]["scrape.yml"]["runs"]
    assert workflow_check(context, "2026-11-03T12:00:00Z")["ok"] is False


def test_failed_targeted_publication_is_not_ignored(document):
    context = workflow_context(document, full=False, publication="failure",
                               checked_at="2026-11-02T10:00:00Z", run_id=2)
    context["workflows"]["scrape.yml"]["runs"] += workflow_context(document)["workflows"]["scrape.yml"]["runs"]
    assert workflow_check(context, "2026-11-03T12:00:00Z")["ok"] is False


# -- The monthly-price run on the 4th (owner decisions 2026-11-20 and 2026-11-23) --------------------

PRICE_GROUP = {"full": False, "utility": None, "province": None, "group": monitoring.MONTHLY_PRICE_GROUP}


def source_row(utility, ok=True):
    if ok:
        return {"utility": utility, "live": 3, "seed": 0, "invalid": 0, "status": "live", "error": None}
    return {"utility": utility, "live": 0, "seed": 0, "invalid": 0, "status": "failed", "error": "month not posted"}


def scrape_run(document, run_id, checked_at, scope=None, rows=None):
    run = workflow_context(document, checked_at=checked_at, run_id=run_id)["workflows"]["scrape.yml"]["runs"][0]
    source = run["evidence"]["source-summary.json"]
    if scope is not None:
        source["scope"] = scope
    if rows is not None:
        source["summary"]["rows"], source["expected_utilities"] = rows, [row["utility"] for row in rows]
    return run


def checks_by_id(runs, now, utilities=()):
    context = {"workflows": {"scrape.yml": {"schedules": ["0 8 1 * *", monitoring.MONTHLY_PRICE_CRON],
                                            "runs": runs}}}
    return {check["id"]: check
            for check in monitoring.workflow_checks(context, monitoring.timestamp(now), None, utilities)}


@pytest.mark.parametrize("cron,after,expected", [
    (monitoring.MONTHLY_PRICE_CRON, "2026-12-01T08:00:00Z", "2026-12-04T08:00:00Z"),
    (monitoring.MONTHLY_PRICE_CRON, "2026-12-04T08:00:00Z", "2027-01-04T08:00:00Z"),
    ("0 8 1 * *", "2026-12-31T23:00:00Z", "2027-01-01T08:00:00Z"),
])
def test_next_scheduled_occurrence_rolls_over_months_and_years(cron, after, expected):
    assert monitoring.next_scheduled(cron, monitoring.timestamp(after)) == monitoring.timestamp(expected)


def test_the_monthly_price_run_never_makes_the_full_refresh_look_overdue(document):
    runs = [scrape_run(document, 2, "2026-11-04T09:00:00Z", PRICE_GROUP),
            scrape_run(document, 1, "2026-11-01T09:00:00Z")]
    checks = checks_by_id(runs, "2026-11-06T12:00:00Z")
    assert checks["workflow:scrape.yml"]["ok"] is True
    assert checks["workflow:scrape.yml:monthly-price"]["ok"] is True


@pytest.mark.parametrize("later,now,expected", [
    (None, "2026-11-04T12:00:00Z", None),  # within the 24-hour grace
    (None, "2026-11-05T08:00:01Z", False),  # overdue
    ({"full": False, "utility": "A", "province": None, "group": None}, "2026-11-06T12:00:00Z", False),  # targeted
    ({"full": True}, "2026-11-06T12:00:00Z", True),  # a later full run also refreshes the monthly prices
])
def test_the_monthly_price_refresh_is_due_on_its_own_schedule(document, later, now, expected):
    runs = [scrape_run(document, 1, "2026-11-01T09:00:00Z")]
    if later is not None:
        runs.insert(0, scrape_run(document, 2, "2026-11-04T10:00:00Z", later))
    checks = checks_by_id(runs, now)
    assert checks["workflow:scrape.yml:monthly-price"]["ok"] is expected
    assert checks["workflow:scrape.yml"]["ok"] is True


@pytest.mark.parametrize("on_the_4th,now,held_check", [
    (None, "2026-11-02T12:00:00Z", None),  # held until the monthly-price run
    (None, "2026-11-05T08:00:01Z", False),  # that run did not refresh it within 24 hours
    (True, "2026-11-04T12:00:00Z", True),  # the run on the 4th stored it
    (False, "2026-11-04T12:00:00Z", False),  # the run on the 4th failed too
])
def test_failures_of_monthly_price_utilities_on_the_1st_wait_for_their_run(document, on_the_4th, now, held_check):
    runs = [scrape_run(document, 1, "2026-11-01T09:00:00Z", rows=[source_row("MH", ok=False),
                                                                    source_row("Other", ok=False)])]
    if on_the_4th is not None:
        runs.insert(0, scrape_run(document, 2, "2026-11-04T09:00:00Z", PRICE_GROUP, [source_row("MH", on_the_4th)]))
    checks = checks_by_id(runs, now, {"MH"})
    assert checks["source:MH"]["ok"] is held_check
    assert checks["source:Other"]["ok"] is False  # not a monthly-price utility: reported at once
    if held_check is None:
        assert checks["source:MH"]["details"][0].startswith("Awaiting the monthly-price run due 2026-11-04T08:00")
    if on_the_4th is None and held_check is False:
        assert "did not refresh it within 24 hours" in checks["source:MH"]["details"][-1]


def test_monthly_price_failures_on_other_days_or_without_the_registry_are_reported_at_once(document):
    later = [scrape_run(document, 1, "2026-11-15T09:00:00Z", rows=[source_row("MH", ok=False)])]
    assert checks_by_id(later, "2026-11-15T12:00:00Z", {"MH"})["source:MH"]["ok"] is False
    first = [scrape_run(document, 1, "2026-11-01T09:00:00Z", rows=[source_row("MH", ok=False)])]
    assert checks_by_id(first, "2026-11-02T12:00:00Z")["source:MH"]["ok"] is False  # registry list unavailable


@pytest.mark.parametrize("inputs,expected", [("failure", True), (None, False)])
def test_a_run_stopped_by_its_input_check_is_neither_a_failure_nor_a_refresh(document, inputs, expected):
    stopped = scrape_run(document, 2, "2026-11-02T10:00:00Z")
    stopped["conclusion"] = "failure"
    outcome = stopped["evidence"]["monitor-status.json"]
    outcome.update(publication="skipped", sources="skipped")
    if inputs:
        outcome["inputs"] = inputs  # older receipts have no field: the run still counts as a failure
    stopped["evidence"] = {"monitor-status.json": outcome}
    runs = [stopped, scrape_run(document, 1, "2026-11-01T09:00:00Z")]
    assert checks_by_id(runs, "2026-11-02T12:00:00Z")["workflow:scrape.yml"]["ok"] is expected


def test_workflow_outcome_records_the_input_check(tmp_path):
    helper = Path(__file__).resolve().parents[1] / "scripts" / "model_monitoring_issue.js"
    script = r"""
const {writeOutcome} = require(process.argv[1]);
process.chdir(process.argv[2]);
writeOutcome({context: {runId: 7, workflow: 'Monthly Scrape'}, workflow: 'scrape.yml',
  steps: {inputs: {outcome: 'failure'}}});
"""
    environment = {**os.environ, "GITHUB_RUN_ATTEMPT": "1"}
    result = subprocess.run(["node", "-e", script, str(helper), str(tmp_path)],
                            capture_output=True, encoding="utf-8", check=False, env=environment)
    assert result.returncode == 0, result.stdout + result.stderr
    outcome = json.loads((tmp_path / "monitor-status.json").read_text(encoding="utf-8"))
    assert (outcome["inputs"], outcome["sources"], outcome["publication"]) == ("failure", "not_attempted",
                                                                               "not_attempted")


@pytest.mark.parametrize("name,field,value", [
    ("source-summary.json", "scope", {"full": "false"}),
    ("model-generation.json", "as_of", "invalid"),
    ("model-generation.json", "fingerprint", "short"),
    ("monitor-status.json", "history_recorded", None),
    ("monitor-status.json", "history_recorded", False),
    ("monitor-status.json", "version", 2),
])
def test_invalid_or_incomplete_receipts_do_not_prove_refresh_success(document, name, field, value):
    context = workflow_context(document)
    context["workflows"]["scrape.yml"]["runs"][0]["evidence"][name][field] = value
    assert workflow_check(context, "2026-11-03T12:00:00Z")["ok"] is False


@pytest.mark.parametrize("bad_receipt", [[], {"run": []}])
def test_malformed_artifact_shapes_are_reported_not_crashed(document, bad_receipt):
    context = workflow_context(document)
    context["workflows"]["scrape.yml"]["runs"][0]["evidence"]["monitor-status.json"] = bad_receipt
    assert workflow_check(context, "2026-11-03T12:00:00Z")["ok"] is False


def test_read_only_check_requires_the_exact_recorded_generation(document, tmp_path, monkeypatch):
    history = monitoring.record_refresh(None, document, receipt(document))
    paths = {name: tmp_path / f"{name}.json" for name in ("models", "history", "report")}
    monitoring.write_json(paths["history"], history)
    document["generated_at"] = "2026-11-15T08:15:00+00:00"
    monitoring.write_json(paths["models"], document)
    monkeypatch.setattr(monitoring, "input_checks", lambda *args: [])
    before = paths["history"].read_bytes()
    assert monitoring.main(["--models", str(paths["models"]), "--history", str(paths["history"]),
                            "--report", str(paths["report"]), "--dry-run"]) == 1
    checks = monitoring.read_json(paths["report"])["checks"]
    assert any(check["id"] == "model_history" and check["ok"] is False for check in checks)
    assert paths["history"].read_bytes() == before


@pytest.mark.parametrize("fault", [None, "taxes", "unmapped", "block_periods", "percentage_riders", "subsidies"])
def test_configuration_health_catches_missing_and_soft_failed_inputs(tmp_path, fault):
    from pipeline.representative_models import load_rates

    root = Path(__file__).resolve().parents[1]
    configs = tmp_path / "data" / "models"
    configs.mkdir(parents=True)
    for name in ("crosswalk", "usage_levels", "taxes", "block_periods", "percentage_riders", "subsidies"):
        if fault in ("taxes", "subsidies") and name == fault:
            continue
        config = monitoring.read_json(root / "data" / "models" / f"{name}.json")
        if fault == "unmapped" and name == "crosswalk":
            config["rules"] = [{"id": "no-match", "utility": "No Matching Utility", "exclude": "test"}]
        elif fault in ("block_periods", "percentage_riders") and name == fault:
            config["entries"].append({"id": "incomplete"})
        (configs / f"{name}.json").write_text(json.dumps(config), encoding="utf-8")
    rates = load_rates(root / "tests" / "fixtures" / "rm_records_sample.json")
    monitoring.write_json(tmp_path / "site" / "data" / "rates.json", rates)
    check = next(check for check in monitoring.input_checks(tmp_path, monitoring.timestamp("2026-11-17T12:00:00Z"))
                 if check["id"] == "model_configuration")
    assert check["ok"] is (fault is None)
    if fault == "unmapped":
        assert "unmapped" in " ".join(check["details"])


@pytest.mark.parametrize("where", ["model", "level"])
def test_synthetic_benchmark_flags_are_rejected_at_both_scopes(document, where):
    target = document["models"][0]
    if where == "level":
        target = target["levels"][0]
    target["market_benchmark"] = {"available": False, "synthetic_profile": True}
    with pytest.raises(ValueError, match="observed benchmark"):
        monitoring.semantic_models(document)


def test_rule_edits_method_and_contributor_changes_are_recorded(document):
    after = copy.deepcopy(document)
    after["method_version"] = "next-method"
    after["models"][0]["coverage"]["contributing_utilities"] = ["A"]
    changes = monitoring.compare_models(monitoring.semantic_models(document), monitoring.semantic_models(after))
    assert [change["category"] for change in changes] == ["inputs", "structure"]
    assert changes[0]["fields"] == ["method_version"]
    assert changes[1]["fields"] == ["coverage"]


def test_integer_and_float_spelling_has_the_same_fingerprint(document):
    after = copy.deepcopy(document)
    after["models"][0]["levels"][0]["with_tax"]["median"] = 100.0
    assert monitoring.fingerprint(monitoring.semantic_models(after)) == monitoring.fingerprint(monitoring.semantic_models(document))


def test_artifact_reader_never_extracts_paths(tmp_path):
    archive = tmp_path / "evidence.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("../../outside.json", '{"ignored":true}')
        output.writestr("monitor-status.json", '{"version":1}')
    assert monitoring.read_evidence_archive(archive) == {"monitor-status.json": {"version": 1}}
    assert not (tmp_path.parent / "outside.json").exists()


def test_actions_collection_uses_current_attempt_artifacts_and_surfaces_api_errors(document, tmp_path):
    helper = Path(__file__).resolve().parents[1] / "scripts" / "model_monitoring_issue.js"
    evidence = workflow_context(document)["workflows"]["scrape.yml"]["runs"][0]["evidence"]
    evidence["source-summary.json"]["expected_utilities"] = ["\u00c9nergir"]
    evidence["source-summary.json"]["summary"]["rows"][0]["utility"] = "\u00c9nergir"
    archive = tmp_path / "download.zip"
    with zipfile.ZipFile(archive, "w") as output:
        for name, value in evidence.items():
            value["run"]["attempt"] = "2"
            output.writestr(name, json.dumps(value))
    script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const {collectContext} = require(process.argv[1]);
const bytes = fs.readFileSync(process.argv[2]);
const actions = {listWorkflowRuns() {}, listWorkflowRunArtifacts() {},
  downloadArtifact: async args => {
    assert.equal(args.artifact_id, 2);
    return {data: bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength)};
  }};
const github = {rest: {actions}, paginate: async (method, args) => {
  if (method === actions.listWorkflowRuns) {
    assert.equal(args.branch, 'main');
    if (args.workflow_id === 'source-health.yml') throw new Error('API unavailable');
    return args.workflow_id === 'scrape.yml' ? [{
      id: 1, run_attempt: 2, status: 'completed', conclusion: 'success',
      created_at: '2026-11-01T09:00:00Z', updated_at: '2026-11-01T09:00:00Z',
      head_branch: 'main', head_repository: {full_name: 'test/example'},
      html_url: 'https://github.com/test/example/actions/runs/1',
    }] : [];
  }
  assert.equal(method, actions.listWorkflowRunArtifacts);
  return [1, 2].map(attempt => ({id: attempt, name: `model-monitoring-evidence-1-${attempt}`,
    expired: false, size_in_bytes: bytes.length}));
}};
collectContext({github, context: {repo: {owner: 'test', repo: 'example'}}, core: {warning() {}}})
  .then(result => console.log(JSON.stringify(result)))
  .catch(error => {console.error(error); process.exitCode = 1;});
"""
    environment = {**os.environ, "RUNNER_TEMP": str(tmp_path), "PYTHONIOENCODING": "cp1252",
                   "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"]}
    result = subprocess.run(["node", "-e", script, str(helper), str(archive)],
                            capture_output=True, encoding="utf-8", check=False, env=environment)
    assert result.returncode == 0, result.stdout + result.stderr
    workflows = json.loads(result.stdout)["workflows"]
    assert workflows["scrape.yml"]["runs"][0]["evidence"]["model-generation.json"]["run"]["attempt"] == "2"
    assert workflows["scrape.yml"]["runs"][0]["evidence"]["source-summary.json"]["expected_utilities"] == ["\u00c9nergir"]
    assert workflows["source-health.yml"]["error"] == "API unavailable"
    assert not (tmp_path / "model-evidence-1-2.zip").exists()


def test_issue_deduplication_scoped_recovery_and_unrelated_issues_are_preserved():
    helper = Path(__file__).resolve().parents[1] / "scripts" / "model_monitoring_issue.js"
    script = r"""
const assert = require('node:assert/strict');
const {syncIssue} = require(process.argv[1]);
const issues = [{number: 1, body: 'Unrelated failure', user: {login: 'github-actions[bot]'}, state: 'open'}];
const comments = [];
let created = 0;
const github = {
  paginate: async () => issues.filter(i => i.state === 'open'),
  rest: {issues: {
    listForRepo() {},
    create: async fields => {
      created++;
      issues.push({...fields, number: 2, user: {login: 'github-actions[bot]'}, state: 'open'});
    },
    update: async fields => Object.assign(issues.find(i => i.number === fields.issue_number), fields),
    createComment: async fields => comments.push(fields),
  }}
};
const context = {repo: {owner: 'test', repo: 'example'}, serverUrl: 'https://github.com', runId: 4};
const check = (id, ok, extra={}) => ({id, ok, details: ok ? [] : ['Missing input'], ...extra});
const report = checks => ({version: 1, checked_at: '2026-11-17T12:00:00Z', checks});
(async () => {
  await syncIssue({github, context, report: report([check('source:A', false), check('source:B', false)])});
  await syncIssue({github, context, report: report([check('source:A', false)])});
  assert.equal(created, 1);
  issues[1].body += '\nMaintainer note: preserve this.';
  await syncIssue({github, context, report: report([check('source:A', true), check('source:B', null)])});
  assert.equal(issues[1].state, 'open');
  assert.match(issues[1].body, /Maintainer note/);
  await syncIssue({github, context, report: report([check('source:B', true, {checked_at: '2026-11-16T12:00:00Z'})])});
  assert.equal(issues[1].state, 'open', 'older success cannot close newer failure');
  await syncIssue({github, context, report: report([check('source:B', true)])});
  assert.equal(issues[1].state, 'closed');
  assert.equal(issues[0].body, 'Unrelated failure');
  assert.equal(issues[0].state, 'open');
  assert.equal(comments.length, 1);
  await syncIssue({github, context, report: report([check('workflow:x', false, {reported_elsewhere: true})])});
  assert.equal(created, 1, 'do not duplicate the existing workflow failure ticket');
  github.rest.issues.create = async () => { throw new Error('API unavailable'); };
  await assert.rejects(syncIssue({github, context, report: report([check('new', false)])}), /API unavailable/);
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    result = subprocess.run(["node", "-e", script, str(helper)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_only_a_full_successful_monthly_scrape_in_a_quarters_first_month_is_the_freshness_report_run(document):
    # Owner decisions 2026-11-23: the quarterly report follows the first successful full Monthly Scrape of January,
    # April, July and October; the monthly-price run, targeted runs and other workflows only refresh an open issue.
    flagged = {"A": [{"document": "https://example.test/a", "last_change": "2025-01-01", "due": "2026-01-01"}]}

    def report(context, now="2027-01-01T12:00:00Z", run_id="1"):
        return monitoring.freshness_report(flagged, context, monitoring.timestamp(now), run_id)

    first = report(workflow_context(document))
    assert first["report_run"] is True and first["quarter"] == "2027-Q1" and first["utilities"] == flagged
    assert report(workflow_context(document), now="2027-02-01T12:00:00Z")["report_run"] is False
    assert report(workflow_context(document, full=False))["report_run"] is False
    assert report(workflow_context(document, publication="failure"))["report_run"] is False
    assert report(workflow_context(document), run_id="2")["report_run"] is False  # another workflow's monitor job
    assert report(None, run_id=None)["report_run"] is False
    broken = workflow_context(document)
    del broken["workflows"]["scrape.yml"]["runs"][0]["evidence"]["model-generation.json"]
    assert report(broken)["report_run"] is False
    assert monitoring.freshness_report(None, workflow_context(document), monitoring.timestamp(
        "2027-01-01T12:00:00Z"), "1") is None  # unreadable gate inputs: nothing to report or close


def test_freshness_issue_is_quarterly_refreshed_superseded_and_never_reopened():
    helper = Path(__file__).resolve().parents[1] / "scripts" / "model_monitoring_issue.js"
    script = r"""
const assert = require('node:assert/strict');
const {syncFreshnessIssue} = require(process.argv[1]);
const monitoringBody = '<!-- model-monitoring:v1 -->\nstate\n<!-- /model-monitoring -->';
const issues = [{number: 1, body: 'Unrelated failure', user: {login: 'github-actions[bot]'}, state: 'open'},
                {number: 2, body: monitoringBody, user: {login: 'github-actions[bot]'}, state: 'open'}];
const comments = [];
let next = 10;
const github = {
  paginate: async (method, params) => issues.filter(i => params.state === 'all' || i.state === params.state),
  rest: {issues: {
    listForRepo() {},
    create: async fields => {
      const issue = {...fields, number: next++, user: {login: 'github-actions[bot]'}, state: 'open'};
      issues.push(issue);
      return {data: issue};
    },
    update: async fields => Object.assign(issues.find(i => i.number === fields.issue_number), fields),
    createComment: async fields => comments.push(fields),
  }}
};
const context = {repo: {owner: 'test', repo: 'example'}, serverUrl: 'https://github.com', runId: 7};
const doc = name => ({document: `https://example.test/${name}`, last_change: '2025-01-01', due: '2026-01-01'});
const report = (quarter, report_run, utilities) => ({freshness: {version: 1, quarter, report_run, reason: 'test', utilities}});
const owned = () => issues.filter(i => (i.body || '').includes('<!-- rates-not-updated:v1 -->'));
const sync = (...args) => syncFreshnessIssue({github, context, report: report(...args)});
(async () => {
  await sync('2027-Q1', false, {A: [doc('a')]});
  await syncFreshnessIssue({github, context, report: {freshness: null}});
  assert.equal(owned().length, 0, 'only the report run creates an issue');
  await sync('2027-Q1', true, {A: [doc('a')], B: [doc('b')]});
  await sync('2027-Q1', true, {A: [doc('a')], B: [doc('b')]});
  assert.equal(owned().length, 1, 'one issue per quarter');
  const q1 = owned()[0];
  assert.equal(q1.title, 'Rates not updated in a year: 2027 Q1');
  assert.match(q1.body, /### A\n- https:\/\/example\.test\/a: last price change 2025-01-01/);
  q1.body += '\nMaintainer note: keep.';
  await sync('2027-Q1', false, {A: [doc('a')], C: [doc('c')]});
  assert.doesNotMatch(q1.body, /### B/);
  assert.match(q1.body, /### C/);
  assert.match(q1.body, /Maintainer note: keep\./);
  await sync('2027-Q1', false, {});
  assert.equal(q1.state, 'closed', 'closes when the list is empty');
  await sync('2027-Q1', true, {D: [doc('d')]});
  assert.equal(owned().length, 1, 'a closed report is neither reopened nor recreated in its quarter');
  assert.equal(q1.state, 'closed');
  await sync('2027-Q2', true, {D: [doc('d')]});
  const q2 = owned().find(i => i.title.endsWith('2027 Q2'));
  await sync('2027-Q3', true, {D: [doc('d')]});
  const q3 = owned().find(i => i.title.endsWith('2027 Q3'));
  assert.equal(q2.state, 'closed');
  assert.equal(q3.state, 'open');
  assert.ok(comments.some(c => c.issue_number === q2.number && c.body.includes(`#${q3.number}`)), 'superseded');
  await sync('2027-Q4', true, {});
  assert.equal(q3.state, 'closed', 'a report with nothing flagged closes the open earlier report');
  assert.equal(owned().length, 3);
  assert.deepEqual(issues.slice(0, 2).map(i => [i.body, i.state]),
                   [['Unrelated failure', 'open'], [monitoringBody, 'open']]);
  await assert.rejects(sync('2027-Q4', true, {E: [{document: 1}]}), /Invalid freshness entry/);
  q2.state = 'open';
  q3.state = 'open';
  await assert.rejects(sync('2027-Q4', false, {}), /Multiple open/);
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
    result = subprocess.run(["node", "-e", script, str(helper)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
