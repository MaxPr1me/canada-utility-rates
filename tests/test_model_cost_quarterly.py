"""Offline regressions for the quarter-end model costs rebuilt from the model change history.

The Rate History tab charts only amounts the history saved (owner decisions 50, 55 and 57 of 2026-11-23 and 80 of
2026-11-24). Histories here are recorded through the module's own record_refresh from small synthetic exports.
"""
import codecs
import json
import os
from datetime import timedelta
from pathlib import Path

import pytest

from pipeline import model_monitoring as monitoring
from tests.test_model_monitoring import receipt

ON = "ON|electricity|residential|tou|-"
AB = "AB|electricity|commercial|demand|commercial_medium"
SMALL = "BC|electricity|commercial|demand|commercial_small"
GAS = "NB|gas|residential|flat|-"
NS = "NS|electricity|commercial|demand|commercial_small"
OLD = "PE|electricity|residential|flat|-"
NEW = "YT|electricity|residential|tiered|-"


def level(level_id, cost, *, role=None, benchmark=None, **usage):
    """A published level: a None cost is unavailable, benchmark=False an unavailable observed benchmark."""
    value = {"id": level_id, "role": role, **(usage or {"kwh": 1000}),
             "without_tax": {"median": cost, "n": 2},
             "with_tax": {"median": None if cost is None else cost + 10, "n": 2},
             "utilities": [] if cost is None else [{"utility": "A", "cost_without_tax": cost,
                                                    "cost_with_tax": cost + 10}]}
    if benchmark is not None:
        value["market_benchmark"] = (
            {"available": False, "reason": "incomplete market window"} if benchmark is False else
            {"available": True, "without_tax": {"median": benchmark}, "with_tax": {"median": benchmark + 20}})
    return value


def model(model_id, *levels, cost_basis="delivery_and_energy", method=None):
    value = {"id": model_id, "state": "modeled", "provenance": "modeled", "cost_basis": cost_basis,
             "levels": list(levels)}
    if method:
        value["method"] = method
    return value


def export(generated_at, *models, method="7T-1"):
    return {"version": 1, "method_version": method, "generated_at": generated_at,
            "as_of": monitoring.timestamp(generated_at).date().isoformat(), "models": list(models)}


def evidence(document, history, *, gap=False):
    """The receipt the workflow passes to --record; gap: the generation it replaced was never recorded."""
    previous = ({"status": "absent"} if history is None else
                {"status": "unverified", "detail": "an unrecorded generation"} if gap else
                {"status": "known", "generated_at": history["last_refresh"]["generated_at"],
                 "fingerprint": history["last_refresh"]["model_fingerprint"]})
    value = receipt(document, previous)
    # Recorded a few minutes after generation, so recorded_at never doubles as generated_at.
    value["checked_at"] = (monitoring.timestamp(document["generated_at"]) + timedelta(minutes=5)).isoformat()
    return value


def history_of(*documents, gaps=()):
    history = None
    for index, document in enumerate(documents):
        history = monitoring.record_refresh(history, document, evidence(document, history, gap=index in gaps))
    return history


def simple_documents():
    """Two refreshes in 2026 Q4 and one in 2027 Q1."""
    return [export("2026-11-17T20:00:00+00:00", model(ON, level("typical", 100))),
            export("2026-12-01T09:00:00+00:00", model(ON, level("typical", 110))),
            # 20:00 in Toronto on December 31 is already January 1 in UTC: a first-quarter refresh.
            export("2026-12-31T20:00:00-05:00", model(ON, level("typical", 120)))]


RICH = ("2026-11-17T20:00:00+00:00", "2026-12-01T09:00:00+00:00", "2026-12-31T20:00:00-05:00",
        "2027-02-01T09:00:00+00:00", "2027-04-02T09:00:00+00:00")


def rich_generation(phase):
    """Phases 0-1 fall in 2026 Q4 and 2-3 in 2027 Q1 (UTC dates); phase 4 is an unchanged refresh in 2027 Q2."""
    late = phase >= 3
    return export(
        RICH[phase],
        model(ON, level("typical", {0: 150, 1: 155}.get(phase, 160), role="reference" if late else None),
              level("low", 90, kwh=500), method="Method 7T-2." if late else "Method 7T-1."),
        model(AB, level("m1", 6100 if late else 6000, kw=100, kwh=40000,
                        benchmark=6600 if late else 6500 if phase == 0 else False),
              cost_basis="delivery_and_energy" if late else "delivery_only_market_energy_pending"),
        model(SMALL, level("s2", 1500, kw=40, kwh=10000) if late else level("s2", 1200, kw=25, kwh=8000)),
        model(GAS, level("typical", 190 if late else 160, quantity=250 if late else 200, unit="m3")),
        model(NS, level("s1", 700 if late else None, kw=14, kwh=2000)),
        model(NEW, level("typical", 320)) if late else model(OLD, level("typical", 100)),
        method="7T-2" if late else "7T-1",
    )


def rich_history():
    return history_of(*(rich_generation(phase) for phase in range(len(RICH))))


def series_points(quarterly, model_id, level_id="typical", kind="base"):
    for series in quarterly["series"]:
        if (series["model_id"], series["kind"], series["level_id"]) == (model_id, kind, level_id):
            return {point["quarter"]: point for point in series["points"]}
    return {}


def test_rebuilt_states_reproduce_every_recorded_level_change():
    history = rich_history()
    states = monitoring.history_states(history)
    assert len(states) == len(history["events"]) == 4  # the phase-4 refresh changed nothing
    checked = 0
    for index, event in enumerate(history["events"]):
        for change in event["changes"]:
            if change["category"] != "level":
                continue
            key = (change["model_id"], change["kind"], change["level_id"])
            assert (states[index - 1] if index else {}).get(key) == change["before"]
            assert states[index].get(key) == change["after"]
            checked += 1
    assert checked == 11  # 2 in December, 1 on January 1 (UTC), 8 in February
    models = history["baseline"]["snapshot"]["models"]
    assert set(states[-1]) == {(model_id, kind, level_id) for model_id, value in models.items()
                               for kind in ("base", "benchmark") for level_id in value[kind]["levels"]}
    assert (OLD, "base", "typical") in states[0] and (NEW, "base", "typical") not in states[0]


def test_a_history_that_does_not_reproduce_its_own_changes_is_refused():
    history = history_of(*simple_documents())
    history["events"][1]["changes"][0]["after"]["with_tax"]["median"] += 1
    previous = history["events"][0]["id"]
    for event in history["events"][1:]:
        event["previous_event"] = previous
        event["id"] = previous = monitoring.fingerprint({key: value for key, value in event.items() if key != "id"})
    monitoring.validate_history(history)  # the hash chain is intact; only the recorded values disagree
    with pytest.raises(ValueError, match="does not rebuild consistently"):
        monitoring.model_cost_quarterly(history)


def test_each_quarter_shows_the_last_state_generated_by_its_utc_end():
    history = history_of(*simple_documents())
    events = history["events"]
    quarterly = monitoring.model_cost_quarterly(history)
    assert list(quarterly) == ["version", "kind", "tracking_started_at", "last_refresh", "last_event", "rule",
                               "current_quarter", "series"]
    assert (quarterly["version"], quarterly["kind"], quarterly["current_quarter"]) == (1, "model_cost_quarterly",
                                                                                         "2027Q1")
    assert quarterly["tracking_started_at"] == history["tracking_started_at"]
    assert quarterly["last_refresh"] == {"generated_at": "2026-12-31T20:00:00-05:00", "as_of": "2027-01-01",
                                         "method_version": "7T-1"}
    assert quarterly["last_event"] == events[-1]["id"]
    (series,) = quarterly["series"]
    assert list(series) == ["model_id", "kind", "level_id", "points"]
    assert (series["model_id"], series["kind"], series["level_id"]) == (ON, "base", "typical")
    usage = {"kwh": 1000, "kw": None, "quantity": None, "unit": None}
    assert series["points"] == [
        {"quarter": "2026Q4", "in_progress": False, "available": True, "without_tax": 110, "with_tax": 120,
         "usage": usage, "recorded_at": events[1]["recorded_at"], "recording_gap": False, "break_before": None},
        {"quarter": "2027Q1", "in_progress": True, "available": True, "without_tax": 120, "with_tax": 130,
         "usage": usage, "recorded_at": events[2]["recorded_at"], "recording_gap": False, "break_before": None},
    ]
    assert list(series["points"][0]) == ["quarter", "in_progress", "available", "without_tax", "with_tax", "usage",
                                         "recorded_at", "recording_gap", "break_before"]


def test_unavailable_added_and_removed_levels_publish_only_what_existed_at_each_quarter_end():
    history = rich_history()
    quarterly = monitoring.model_cost_quarterly(history)
    assert quarterly["current_quarter"] == "2027Q2"
    unavailable = series_points(quarterly, NS, "s1")
    assert [(point["available"], point["without_tax"], point["with_tax"]) for point in unavailable.values()] == [
        (False, None, None), (True, 700, 710), (True, 700, 710)]
    assert unavailable["2026Q4"]["usage"] == {"kwh": 2000, "kw": 14, "quantity": None, "unit": None}
    benchmark = series_points(quarterly, AB, "m1", "benchmark")
    assert [(point["available"], point["without_tax"], point["with_tax"]) for point in benchmark.values()] == [
        (False, None, None), (True, 6600, 6620), (True, 6600, 6620)]
    assert list(series_points(quarterly, NEW)) == ["2027Q1", "2027Q2"]  # added in 2027 Q1: no earlier point
    assert list(series_points(quarterly, OLD)) == ["2026Q4"]  # removed in 2027 Q1: its earlier point stays
    # 2027 Q2 has only an unchanged refresh: it shows the state recorded in Q1, in progress.
    quiet = series_points(quarterly, ON)["2027Q2"]
    assert (quiet["in_progress"], quiet["with_tax"], quiet["recorded_at"]) == (True, 170,
                                                                                history["events"][3]["recorded_at"])
    keys = [(series["model_id"], series["kind"], series["level_id"]) for series in quarterly["series"]]
    assert keys == sorted(keys) and len(keys) == 9


@pytest.mark.parametrize("gaps,expected", [
    ((1,), True),  # the first refresh recorded after 2026 Q4 followed an unrecorded generation
    ((), False),
    ((2,), False),  # a later gap cannot have changed the value in effect at the end of 2026 Q4
])
def test_recording_gap_comes_from_the_first_refresh_recorded_after_the_quarter(gaps, expected):
    documents = [export("2026-11-17T20:00:00+00:00", model(ON, level("typical", 100))),
                 export("2027-01-10T09:00:00+00:00", model(ON, level("typical", 110))),
                 export("2027-02-10T09:00:00+00:00", model(ON, level("typical", 110)))]
    history = history_of(*documents, gaps=gaps)
    assert [index for index, event in enumerate(history["events"]) if event["history_gap"]] == list(gaps)
    fourth, first = series_points(monitoring.model_cost_quarterly(history), ON).values()
    assert fourth["recording_gap"] is expected
    assert first["in_progress"] and first["recording_gap"] is False


def test_only_a_cost_basis_or_example_customer_change_breaks_a_series():
    history = rich_history()
    changes = history["events"][3]["changes"]
    # The role label, the method text and the method version change in the same refresh as the breaks.
    assert any(change["category"] == "level" and change["model_id"] == ON and change["fields"] == ["role"]
               for change in changes)
    assert any(change["category"] == "structure" and change["model_id"] == ON and change["fields"] == ["method"]
               for change in changes)
    assert any(change["category"] == "inputs" and change["fields"] == ["method_version"] for change in changes)
    breaks = {(series["model_id"], series["kind"], series["level_id"]): [point["break_before"]
                                                                          for point in series["points"]]
              for series in monitoring.model_cost_quarterly(history)["series"]}
    basis = {"reasons": ["cost basis changed: delivery_only_market_energy_pending -> delivery_and_energy"]}
    assert breaks[(AB, "base", "m1")] == breaks[(AB, "benchmark", "m1")] == [None, basis, None]
    assert breaks[(SMALL, "base", "s2")] == [None, {"reasons": [
        "example customer changed: 25 kW and 8,000 kWh -> 40 kW and 10,000 kWh"]}, None]
    assert breaks[(GAS, "base", "typical")] == [None, {"reasons": [
        "example customer changed: 200 m\u00b3 -> 250 m\u00b3"]}, None]
    assert breaks[(ON, "base", "typical")] == breaks[(ON, "base", "low")] == [None, None, None]
    assert breaks[(NS, "base", "s1")] == [None, None, None]


@pytest.mark.parametrize("readded_at,quarter", [
    ("2027-02-10T09:00:00+00:00", "2027Q1"),  # removed and re-added within 2027 Q1
    ("2027-04-10T09:00:00+00:00", "2027Q2"),  # absent at the end of 2027 Q1, re-added in Q2
])
@pytest.mark.parametrize("kwh,expected", [
    (1200, {"reasons": ["example customer changed: 1,000 kWh -> 1,200 kWh"]}),
    (1000, None),  # the same example customer: a cost change alone never breaks the series
])
def test_a_level_readded_with_another_example_customer_breaks_its_series(readded_at, quarter, kwh, expected):
    history = history_of(
        export("2026-11-17T20:00:00+00:00", model(ON, level("typical", 100), level("low", 60, kwh=500))),
        export("2027-01-10T09:00:00+00:00", model(ON, level("low", 60, kwh=500))),
        export(readded_at, model(ON, level("typical", 120, kwh=kwh), level("low", 60, kwh=500))),
    )
    # No recorded change shows the level on both sides: decision 80 compares the two points a chart joins.
    assert [(change["before"] is None, change["after"] is None) for event in history["events"]
            for change in event["changes"] if change["category"] == "level"] == [(False, True), (True, False)]
    quarterly = monitoring.model_cost_quarterly(history)
    typical = series_points(quarterly, ON)
    assert list(typical) == ["2026Q4", quarter]
    assert typical[quarter]["break_before"] == expected
    assert all(point["break_before"] is None for point in series_points(quarterly, ON, "low").values())


@pytest.mark.parametrize("readded_at,quarter", [
    ("2027-02-10T09:00:00+00:00", "2027Q1"),  # removed and added again within 2027 Q1
    ("2027-04-10T09:00:00+00:00", "2027Q2"),  # absent at the end of 2027 Q1, added again in Q2
])
def test_a_model_removed_and_added_again_breaks_every_series_of_that_model(readded_at, quarter):
    def commercial():
        return model(AB, level("m1", 6000, kw=100, kwh=40000, benchmark=6500))

    history = history_of(
        export("2026-11-17T20:00:00+00:00", model(ON, level("typical", 100)), commercial()),
        export("2027-01-10T09:00:00+00:00", model(ON, level("typical", 100))),
        export(readded_at, model(ON, level("typical", 100)), commercial()),
    )
    assert [change["category"] for event in history["events"] for change in event["changes"]
            if change["category"].startswith("model_")] == ["model_removed", "model_added"]
    quarterly = monitoring.model_cost_quarterly(history)
    # Decision 84: the same example customer and cost basis, but the earlier cost basis was never recorded.
    readded = {"reasons": ["the model was removed and added again; its earlier cost basis was not recorded"]}
    for kind in ("base", "benchmark"):
        points = series_points(quarterly, AB, "m1", kind)
        assert list(points) == ["2026Q4", quarter]
        assert points[quarter]["break_before"] == readded
    assert all(point["break_before"] is None for point in series_points(quarterly, ON).values())


def test_a_model_that_is_only_added_breaks_no_series():
    history = history_of(
        export("2026-11-17T20:00:00+00:00", model(ON, level("typical", 100))),
        export("2027-01-10T09:00:00+00:00", model(ON, level("typical", 100)), model(NEW, level("typical", 300))),
        export("2027-04-10T09:00:00+00:00", model(ON, level("typical", 110)), model(NEW, level("typical", 310))),
    )
    assert [change["category"] for event in history["events"] for change in event["changes"]
            if change["category"].startswith("model_")] == ["model_added"]
    quarterly = monitoring.model_cost_quarterly(history)
    assert list(series_points(quarterly, ON)) == ["2026Q4", "2027Q1", "2027Q2"]
    assert list(series_points(quarterly, NEW)) == ["2027Q1", "2027Q2"]
    assert all(point["break_before"] is None for series in quarterly["series"] for point in series["points"])


@pytest.fixture
def record(tmp_path, monkeypatch):
    """Run ``--record`` like the data workflows, with temporary files and no repository input checks."""
    monkeypatch.setattr(monitoring, "input_checks", lambda *args: [])
    history_path = tmp_path / "site" / "model_change_history.json"

    def run(document, *extra):
        history = monitoring.read_json(history_path) if history_path.exists() else None
        monitoring.write_json(tmp_path / "models.json", document)
        monitoring.write_json(tmp_path / "receipt.json", evidence(document, history))
        return monitoring.main(["--models", str(tmp_path / "models.json"), "--history", str(history_path),
                                "--receipt", str(tmp_path / "receipt.json"), "--record", *extra])

    run.history = history_path
    return run


def test_record_writes_the_history_then_its_quarterly_costs_deterministically(record, capsys):
    first, second, _ = simple_documents()
    assert record(first) == 0 and record(second) == 0
    history = monitoring.read_json(record.history)
    assert len(history["events"]) == 2
    quarterly = record.history.with_name("model_cost_quarterly.json")  # the default: next to --history
    written = quarterly.read_bytes()
    assert json.loads(written) == monitoring.model_cost_quarterly(history)
    assert written.endswith(b"}\n") and b"\r" not in written and not written.startswith(codecs.BOM_UTF8)
    assert record(second) == 0  # the same generation again: no new event
    assert monitoring.read_json(record.history)["events"] == history["events"]
    assert quarterly.read_bytes() == written
    assert "Quarterly model costs: rewritten." in capsys.readouterr().out


@pytest.mark.parametrize("failure", ["build", "write"])
def test_a_quarterly_failure_is_logged_and_never_blocks_the_recorded_history(record, tmp_path, monkeypatch, caplog,
                                                                            capsys, failure):
    quarterly = tmp_path / "quarterly" / "model_cost_quarterly.json"
    quarterly.parent.mkdir()
    quarterly.write_bytes(b"previous\n")
    if failure == "build":
        def broken(history):
            raise RuntimeError("cannot rebuild")

        monkeypatch.setattr(monitoring, "model_cost_quarterly", broken)
    else:
        replace = os.replace

        def refuse_quarterly(source, target):
            if Path(target) == quarterly:
                raise OSError("disk full")
            replace(source, target)

        monkeypatch.setattr(monitoring.os, "replace", refuse_quarterly)
    report = tmp_path / "report.json"
    assert record(simple_documents()[0], "--quarterly", str(quarterly), "--report", str(report)) == 0
    monitoring.validate_history(monitoring.read_json(record.history))
    assert {"id": "model_history", "ok": True, "details": []} in monitoring.read_json(report)["checks"]
    assert quarterly.read_bytes() == b"previous\n"
    assert not quarterly.with_name(quarterly.name + ".tmp").exists()
    assert "Quarterly model costs were not updated; the change history was recorded" in caplog.text
    assert "Quarterly model costs: NOT updated" in capsys.readouterr().out


def test_quarterly_output_is_only_written_by_a_record_run(tmp_path):
    with pytest.raises(SystemExit):
        monitoring.main(["--dry-run", "--quarterly", str(tmp_path / "model_cost_quarterly.json")])
    assert not (tmp_path / "model_cost_quarterly.json").exists()
