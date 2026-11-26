"""Spark gap comparison (method SG-1; owner decisions 118 and 124-165, 2026-11-25 and 2026-11-26).

Offline: frozen live records (tests/fixtures/sg_records.json: BC Hydro's two home plans, an Ontario distributor's
home TOU/tiered/ULO tariffs, Enbridge's and EPCOR's home gas, Nova Scotia Power and Yukon Energy), the committed
reviewed inputs and an inline heating-oil document built from Statistics Canada's published prices.
"""
import copy
import json
from datetime import date
from pathlib import Path

import pytest

from pipeline import export_json, model_monitoring, representative_models as rm, spark_gap as sg

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "sg_records.json"
AS_OF = "2026-11-26"
OPTIONS = {"archetypes": None, "market_documents": {"ON": None, "AB": None}}
# Statistics Canada Table 18-10-0001-01, household heating fuel, cents per litre (published 2026-11-16).
OIL = {"NB": {"2026-09": 259.9, "2026-10": 268.7}, "NS": {"2026-09": 230.8, "2026-10": 248.1},
       "PE": {"2026-10": 210.9}, "NL": {"2026-10": 253.3}, "YT": {"2026-10": 255.0}, "NT": {"2026-10": 243.2}}


def _records() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["records"]


def _oil(prices=OIL) -> dict:
    return {"version": 1, "kind": "heating_oil_prices", "retrieved_at": None, "series": {
        region: {"vector": "v0", "geo": region, "months": {month: {"value": value, "status": None}
                                                           for month, value in months.items()}}
        for region, months in prices.items()}}


@pytest.fixture(scope="module")
def inputs():
    return {"crosswalk": rm.load_crosswalk(), "usage_levels": rm.load_usage_levels(), "taxes": rm.load_taxes(),
            "config": sg.load_config()}


@pytest.fixture(scope="module")
def result(inputs):
    return sg.build_spark_gap(_records(), inputs["crosswalk"], inputs["usage_levels"], inputs["taxes"],
                              inputs["config"], _oil(), as_of=AS_OF, **OPTIONS)


@pytest.fixture(scope="module")
def electricity_runs(inputs):
    def run(step):
        return rm.build_models(_records(), inputs["crosswalk"], sg.electricity_levels(inputs["usage_levels"],
                               inputs["config"], step), inputs["taxes"], provinces=sg.REGIONS, fuels=("electricity",),
                               as_of=AS_OF, exact_costs=True, **OPTIONS)
    return run(0.0), run(1.0)


def _row(result, customer, region):
    return next(row for c in result["customers"] if c["id"] == customer for row in c["rows"] if row["region"] == region)


def _gas_cost(record, quantity, inputs):
    return rm.record_monthly_cost(record, quantity, sector="residential", usage_levels=inputs["usage_levels"],
                                  as_of=AS_OF)["cost"]


def test_reviewed_choices_pick_one_price_per_utility(result):
    bc = _row(result, "residential", "BC")["electricity"]
    assert [(u["utility"], u["records"], u.get("choice")) for u in bc["utilities"]] == [
        ("BC Hydro", [1184], "bc-hydro-cheaper-plan")]  # the flat plan (Rate 1151) costs less at 2,000 kWh
    on = _row(result, "residential", "ON")["electricity"]
    assert [u["records"] for u in on["utilities"]] == [[5027]] and "tou models only" in on["notes"][0]
    gas = {u["utility"]: u for u in _row(result, "residential", "ON")["fuel_prices"]["utilities"]}
    assert gas["EPCOR Natural Gas (Ontario)"]["choice"] == "epcor-ontario-gas-median"
    assert [v["id"] for v in gas["EPCOR Natural Gas (Ontario)"]["heating_values"]] == ["cer_fallback",
                                                                                      "epcor-southern-bruce"]
    assert [v["mj_per_m3"] for v in gas["Enbridge Gas"]["heating_values"]] == [39.08]


def test_gas_prices_convert_each_system_with_its_own_heating_value(result, inputs):
    records = {r["id"]: r for r in _records()}
    systems = [(records[3607], 37.3), (records[3613], 39.02)]  # Aylmer: CER factor; Southern Bruce: EPCOR's value
    average = [_gas_cost(record, 7200 / value, inputs) / 7.2 * 100 / 277.7778 for record, value in systems]
    marginal = [(_gas_cost(record, 401, inputs) - _gas_cost(record, 400, inputs)) / (value / 1000) * 100 / 277.7778
                for record, value in systems]
    epcor = next(u for u in _row(result, "residential", "ON")["fuel_prices"]["utilities"]
                 if u["utility"] == "EPCOR Natural Gas (Ontario)")
    assert epcor["average"]["without_tax"]["cents_per_kwh"] == pytest.approx(sum(average) / 2, abs=1e-4)
    assert epcor["marginal"]["without_tax"]["cents_per_kwh"] == pytest.approx(sum(marginal) / 2, abs=1e-4)


def test_spark_gap_and_break_even_follow_the_published_prices(result):
    row = _row(result, "residential", "ON")
    assert row["status"] == "ok" and row["realistic_cop"]["city"] == "Toronto"
    for view in ("without_tax", "with_tax"):
        parts = row["views"][view]
        for part in ("average", "marginal"):
            gap = parts["electricity"][part]["cents_per_kwh"] / parts["fuel"][part]["cents_per_kwh"]
            assert parts["spark_gap"][part] == pytest.approx(gap, abs=1e-3)
            assert parts["break_even_cop"][part]["gas"] == pytest.approx(gap * 0.95, abs=0.01)
        assert parts["verdict"]["code"] in sg.VERDICTS
    assert "after_subsidy" not in row["views"]


def test_oil_prices_remove_reviewed_taxes_and_fail_closed(result, inputs):
    row = _row(result, "residential", "NS")
    oil = row["fuel_prices"]
    assert (oil["month"], oil["cents_per_litre"], oil["tax_factor"]) == ("2026-10", 248.1, pytest.approx(1.05))
    with_tax = 248.1 / (38.8 / 3.6)
    assert row["views"]["with_tax"]["fuel"]["average"]["cents_per_kwh"] == pytest.approx(with_tax, abs=1e-4)
    assert row["views"]["without_tax"]["fuel"]["average"]["cents_per_kwh"] == pytest.approx(with_tax / 1.05, abs=1e-4)
    assert row["views"]["with_tax"]["fuel"]["marginal"] == row["views"]["with_tax"]["fuel"]["average"]
    assert row["efficiency"][0]["value"] == 0.83 and row["realistic_cop"]["city"] == "Halifax"
    nunavut = _row(result, "residential", "NU")
    assert nunavut["status"] == "not_available" and "Nunavut" in nunavut["reasons"][-1]
    untaxed = copy.deepcopy(inputs["taxes"])
    del untaxed["jurisdictions"]["NS"]["heating_oil"]
    missing = sg.oil_region("NS", inputs["config"], _oil(), None, untaxed, date(2026, 11, 26))
    assert missing["average"]["without_tax"] is None and missing["average"]["with_tax"] == pytest.approx(with_tax)
    assert "no reviewed heating-oil tax line" in missing["reasons"][0]
    unusable = _oil()
    unusable["series"]["NS"]["months"]["2026-10"] = {"value": None, "status": ".."}
    assert sg.oil_region("NS", inputs["config"], unusable, None, inputs["taxes"], date(2026, 11, 26))["month"] == "2026-09"


def test_territories_show_the_cost_after_automatic_subsidies_before_tax(result):
    row = _row(result, "residential", "YT")
    assert row["status"] == "ok" and "before_subsidies" in row["labels"] and row["realistic_cop"] is None
    after, before = row["views"]["after_subsidy"], row["views"]["without_tax"]
    assert after["fuel"] == before["fuel"]  # oil before tax
    assert after["electricity"]["average"]["cents_per_kwh"] < before["electricity"]["average"]["cents_per_kwh"]
    assert "verdict" not in after and "verdict" not in row["views"]["with_tax"]


def test_missing_fuel_or_market_energy_is_not_available_never_zero(result):
    bc = _row(result, "residential", "BC")
    assert bc["status"] == "not_available" and bc["views"] == {}
    assert any(reason.startswith("Natural gas:") for reason in bc["reasons"])
    assert all(row["status"] == "not_available" for row in
               next(c for c in result["customers"] if c["id"] == "commercial_medium")["rows"])


def test_unreviewed_overlap_fails_closed(electricity_runs, inputs):
    config = copy.deepcopy(inputs["config"])
    config["utility_choices"]["entries"] = [e for e in config["utility_choices"]["entries"]
                                            if e["id"] != "bc-hydro-cheaper-plan"]
    prices = sg.electricity_region("BC", "residential", *electricity_runs, config)
    assert not prices["available"] and "BC Hydro is priced more than once" in prices["reasons"][0]


def test_points_keep_level_ids_and_load_factor(inputs):
    levels = sg.electricity_levels(inputs["usage_levels"], inputs["config"], 1.0)["electricity"]
    assert [(lv["id"], lv["kwh"], lv["kw"]) for lv in levels["residential"]] == [("high", 2001.0, None)]
    assert [(lv["id"], lv["kwh"], round(lv["kw"], 6)) for lv in levels["commercial_small"]] == [("s2", 10001.0, 40.004)]
    assert [(lv["id"], lv["kwh"], round(lv["kw"], 6)) for lv in levels["commercial_medium"]] == [("m1", 25001.0, 100.004)]
    changed = copy.deepcopy(inputs["usage_levels"])
    next(lv for lv in changed["electricity"]["residential"] if lv["id"] == "high")["kwh"] = 2500
    with pytest.raises(ValueError, match="no longer matches"):
        sg.electricity_levels(changed, inputs["config"])


def test_exact_costs_only_on_request_and_match_published_rounding(inputs):
    args = (_records(), inputs["crosswalk"], inputs["usage_levels"], inputs["taxes"])
    plain = rm.build_models(*args, provinces=("BC",), fuels=("electricity",), as_of=AS_OF, **OPTIONS)
    exact = rm.build_models(*args, provinces=("BC",), fuels=("electricity",), as_of=AS_OF, exact_costs=True, **OPTIONS)
    rows = [row for model in plain["models"] for level in model["levels"] for row in level["utilities"]]
    assert rows and not any("exact" in row for row in rows)
    for model in exact["models"]:
        for level in model["levels"]:
            for row in level["utilities"]:
                assert round(row["exact"]["without_tax"], 2) == row["cost_without_tax"]
                assert round(row["exact"]["with_tax"], 2) == row["cost_with_tax"]
                assert [r["record_id"] for r in row["exact"]["records"]] == row["records"]


def test_verdicts_and_the_marginal_note(inputs):
    cop = {"standard": 3.1, "cold_climate": 3.3}
    assert [sg.verdict(value, cop) for value in (3.0, 3.2, 3.3, None)] == [
        "heat_pump_cheaper", "depends_on_heat_pump", "furnace_cheaper", None]
    assert sg.verdict(2.0, None) is None

    def prices(average, marginal):
        return {"available": True, "average": {"without_tax": average, "with_tax": average, "after_subsidy": None},
                "marginal": {"without_tax": marginal, "with_tax": marginal, "after_subsidy": None}}
    row = sg.compare("BC", "residential", "gas", prices(16.0, 16.0), prices(5.0, 4.4), inputs["config"])
    verdict = row["views"]["with_tax"]["verdict"]
    assert verdict["code"] == "heat_pump_cheaper"  # break-even 3.2 x 0.95 = 3.04 < Vancouver's standard 3.1
    assert verdict["marginal_code"] == "furnace_cheaper" and verdict["marginal_note"].startswith("At the marginal")


def test_reviewed_inputs_are_valid_and_reviews_expire(inputs):
    assert sg.config_problems(inputs["config"]) == []
    assert sg.stale_reviews(inputs["config"], date(2026, 11, 26)) == []
    assert sg.stale_reviews(inputs["config"], date(2028, 1, 1))
    broken = copy.deepcopy(inputs["config"])
    broken["comparison_fuels"]["commercial_small"]["NS"] = "heating_oil"
    broken["realistic_cop"]["cities"]["Halifax"]["standard"] = 3.0
    problems = sg.config_problems(broken)
    assert any("businesses compare with gas only" in p for p in problems)
    assert any("standard <= cold_climate" in p for p in problems)
    records = {r["id"]: r for r in _records()}
    assert sg.heating_value(records[3613], inputs["config"]) == (39.02, "epcor-southern-bruce")
    assert sg.heating_value(records[3607], inputs["config"]) == (37.3, "cer_fallback")
    assert sg.heating_value(records[3577], inputs["config"]) == (39.08, "enbridge-qram-2026-07")


def test_heating_oil_tax_lines_never_change_model_fingerprints(inputs):
    without = copy.deepcopy(inputs["taxes"])
    for fuels in without["jurisdictions"].values():
        fuels.pop("heating_oil", None)
    assert model_monitoring.input_fingerprints({"taxes": without}) == model_monitoring.input_fingerprints(
        {"taxes": inputs["taxes"]})


def _monitored_root(tmp_path, *, spark_at, models_at, months):
    (tmp_path / "data" / "models").mkdir(parents=True)
    (tmp_path / "data" / "fuel").mkdir(parents=True)
    (tmp_path / "site" / "data").mkdir(parents=True)
    (tmp_path / "data" / "models" / "spark_gap.json").write_text(sg.CONFIG_PATH.read_text(encoding="utf-8"),
                                                                 encoding="utf-8")
    (tmp_path / "site" / "data" / "spark_gap.json").write_text(json.dumps(
        {"version": 1, "kind": "spark_gap", "generated_at": spark_at, "customers": []}), encoding="utf-8")
    (tmp_path / "site" / "data" / "representative_models.json").write_text(json.dumps(
        {"generated_at": models_at}), encoding="utf-8")
    (tmp_path / "data" / "fuel" / "heating_oil_prices.json").write_text(json.dumps(
        _oil({region: {month: 200.0} for region in OIL for month in months})), encoding="utf-8")
    return tmp_path


def test_monitoring_reports_stale_file_and_old_oil_prices(tmp_path):
    root = _monitored_root(tmp_path, spark_at="2026-11-26T10:00:00+00:00", models_at="2026-11-26T11:00:00+00:00",
                           months=("2026-06", "2026-07"))
    problems = sg.spark_gap_problems(root, date(2026, 11, 26))
    assert any("older than the representative models" in p for p in problems)
    assert sum("more than 3 months old" in p for p in problems) == len(OIL)
    fresh = _monitored_root(tmp_path / "fresh", spark_at="2026-11-26T12:00:00+00:00",
                            models_at="2026-11-26T11:00:00+00:00", months=("2026-10",))
    assert sg.spark_gap_problems(fresh, date(2026, 11, 26)) == []
    checks = model_monitoring.input_checks(fresh, model_monitoring.timestamp("2026-11-26T12:00:00+00:00"))
    assert next(check for check in checks if check["id"] == "spark_gap")["ok"] is True


def test_failed_export_keeps_the_previous_file(tmp_path, monkeypatch):
    target = tmp_path / "spark_gap.json"
    target.write_text('{"kept": true}\n', encoding="utf-8")

    def broken(*args, **kwargs):
        raise ValueError("bad input")
    monkeypatch.setattr(sg, "write_spark_gap", broken)
    assert export_json.export_spark_gap([], target) is None
    assert target.read_text(encoding="utf-8") == '{"kept": true}\n'
