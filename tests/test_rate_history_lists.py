"""Reviewed Rate History lists: the regulated and default series and the event markers.

The website charts the series in site/data/rate_history_series.json from the live records it already loads and
marks the decisions in site/data/rate_history_events.json (owner decisions 53, 55 and 56 of 2026-11-23). These
tests keep both hand-maintained lists well formed and check every series against frozen live records copied from
the export (tests/fixtures/rate_history_records.json). After each data run, model monitoring applies the same
rules (pipeline/rate_history.py, mirrored by site/js/rate-history.js) to the current export, so a renamed price
line is reported rather than shown as an empty chart.
"""
from __future__ import annotations

import copy
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

import pytest

from pipeline.rate_history import line_components, record_selected, series_problems

ROOT = Path(__file__).resolve().parents[1]
SERIES = json.loads((ROOT / "site" / "data" / "rate_history_series.json").read_text(encoding="utf-8"))
EVENTS = json.loads((ROOT / "site" / "data" / "rate_history_events.json").read_text(encoding="utf-8"))
RECORDS = json.loads((ROOT / "tests" / "fixtures" / "rate_history_records.json").read_text(encoding="utf-8"))["records"]

PROVINCES = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
COMPONENT_KEYS = {"component_type", "tou_period", "name_regex"}
LINE_KEYS = {"id", "label", "component_type", "name_regex", "tariff_code_regex", "tou_period"}
MATCH_KEYS = {"province", "utility_type", "utility_name", "requires", "excludes"}
FAMILIES = {"tariff", "regulated", "market", "model"}


def _js_safe(pattern: str) -> None:
    re.compile(pattern)
    # The browser compiles the same text with RegExp: no Python-only groups, flags or lookbehind.
    assert not re.search(r"\(\?(?!:)", pattern), pattern
    assert pattern.startswith("^") and pattern.endswith("$"), pattern


def _iso(text: str) -> date:
    return date.fromisoformat(text)


def test_series_list_is_well_formed():
    assert SERIES["version"] == 1 and SERIES["kind"] == "rate_history_series"
    reviewed = _iso(SERIES["reviewed"])
    assert reviewed <= date.today()
    ids = [row["id"] for row in SERIES["series"]]
    assert len(ids) == len(set(ids))
    for row in SERIES["series"]:
        assert row["family"] == "regulated" and row["province"] in PROVINCES
        assert row["fuel"] in ("electricity", "gas") and row["label"] and row["group"] and row["note"]
        match = row["match"]
        assert set(match) <= MATCH_KEYS and match["province"] == row["province"]
        assert match["utility_type"] == row["fuel"]
        for selector in match.get("requires", []) + match.get("excludes", []):
            assert selector and set(selector) <= COMPONENT_KEYS, (row["id"], selector)
            if "name_regex" in selector:
                _js_safe(selector["name_regex"])
        line_ids = [line["id"] for line in row["lines"]]
        assert line_ids and len(line_ids) == len(set(line_ids))
        for line in row["lines"]:
            assert set(line) <= LINE_KEYS and line["label"], (row["id"], line)
            _js_safe(line["name_regex"])
            if "tariff_code_regex" in line:
                _js_safe(line["tariff_code_regex"])


def test_medicine_hat_is_not_a_regulated_series():
    # Decision 56: Medicine Hat's monthly bundled rate is not a regulated or default series.
    assert not any("Medicine Hat" in json.dumps(row) for row in SERIES["series"])


@pytest.mark.parametrize("row", SERIES["series"], ids=lambda row: row["id"])
def test_every_series_line_matches_stored_live_records(row):
    records = [record for record in RECORDS if record_selected(record, row["match"])]
    assert records, f"{row['id']}: no live record matches"
    for line in row["lines"]:
        found = [(record, component) for record in records for component in line_components(record, line)]
        assert found, f"{row['id']}/{line['id']}: no stored component matches"
        # A series is shown once: the records carrying a line agree on its value for each effective date; the
        # site splits a line whose values differ instead of picking one (decision 56).
        values = defaultdict(set)
        for record, component in found:
            values[component.get("effective_date") or record.get("effective_date")].add(component.get("charge_value"))
        assert all(len(found_values) == 1 for found_values in values.values()), (row["id"], line["id"], values)


def test_estimates_never_join_a_series():
    # Decision 55: estimates are never charted, even when their lines carry a series' names.
    row = next(item for item in SERIES["series"] if item["id"] == "on-rpp-tou")
    live = next(record for record in RECORDS if record_selected(record, row["match"]))
    assert not record_selected({**live, "provenance": "seed"}, row["match"])
    assert any(record.get("provenance") == "seed" for record in RECORDS), "the fixture keeps one estimate"
    assert not any(record_selected(record, item["match"])
                   for record in RECORDS if record.get("provenance") != "live" for item in SERIES["series"])


def test_ontario_plans_do_not_overlap():
    plans = {row["id"]: row for row in SERIES["series"] if row["id"].startswith("on-rpp-")}
    for record in RECORDS:
        if record.get("provenance") == "live" and record.get("province") == "ON" and record["utility_type"] == "electricity":
            assert sum(record_selected(record, row["match"]) for row in plans.values()) <= 1, record["name"]


def test_the_monitoring_check_passes_on_the_stored_records():
    assert series_problems(SERIES, RECORDS) == []


def test_a_renamed_line_in_the_newest_version_is_reported_even_when_older_versions_match():
    # A newer version of the same tariff that renames the supply line must be reported, though the older version
    # still carries the old name: the site would chart nothing current for that line until the list is updated.
    older = next(record for record in RECORDS if record["utility_name"] == "Energir" and record["provenance"] == "live"
                 and record["effective_date"] == "2026-10-01")
    newer = copy.deepcopy(older)
    newer.update(effective_date="2026-12-01", scrape_run_id=(older.get("scrape_run_id") or 0) + 1)
    for component in newer["components"]:
        if component["component_name"] == "Natural Gas Supply":
            component["component_name"] = "Natural Gas Supply Price"
    records = [record for record in RECORDS if record["utility_name"] != "Energir"] + [older, newer]
    problems = series_problems(SERIES, records)
    assert len(problems) == 1 and "qc-gas-energir, line supply" in problems[0]
    assert series_problems(SERIES, [record for record in records if record is not newer]) == []


def test_a_series_without_any_current_live_tariff_is_reported():
    records = [record for record in RECORDS if record["utility_name"] != "SaskEnergy"]
    assert series_problems(SERIES, records) == ["Rate History series sk-gas-saskenergy: no current live tariff matches it."]


@pytest.mark.parametrize("fault", ["kind", "regex", "selector"])
def test_an_unreadable_series_list_cannot_pass_the_check(fault):
    document = copy.deepcopy(SERIES)
    if fault == "kind":
        document["kind"] = "something_else"
    elif fault == "regex":
        document["series"][0]["lines"][0]["name_regex"] = "^Off-Peak ("
    else:
        document["series"][0]["match"]["requires"] = [{"component": "energy"}]
    with pytest.raises(ValueError):
        series_problems(document, RECORDS)


def test_event_list_is_well_formed_and_sourced():
    assert EVENTS["version"] == 1 and EVENTS["kind"] == "rate_history_events"
    reviewed = _iso(EVENTS["reviewed"])
    ids = [event["id"] for event in EVENTS["events"]]
    assert len(ids) == len(set(ids))
    dates = [_iso(event["date"]) for event in EVENTS["events"]]
    assert dates == sorted(dates)
    for event in EVENTS["events"]:
        assert event["label"] and event["detail"]
        scope = event["applies_to"]
        assert set(scope) == {"provinces", "fuels", "families"}
        assert scope["provinces"] and set(scope["provinces"]) <= PROVINCES
        assert scope["fuels"] and set(scope["fuels"]) <= {"electricity", "gas"}
        assert scope["families"] and set(scope["families"]) <= FAMILIES
        assert event["sources"]
        for source in event["sources"]:
            # Decision 53: every marker links an official source whose quoted sentence was checked.
            assert source["url"].startswith("https://") and source["label"] and source["quote"]
            assert _iso(source["verified"]) <= reviewed
