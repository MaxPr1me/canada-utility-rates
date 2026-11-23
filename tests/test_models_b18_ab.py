"""Parser-to-model checks for batch 18 continued (frozen rm_records_b18_ab.json plus the 7C Alberta sample).

Owner decisions 2026-11-04 and 2026-11-19: Lethbridge and Red Deer publish their wires tariff and their area's Rate of
Last Resort, so each city is one pairs unit; Medicine Hat's bundled residential rate joins the Alberta residential
median as flat; its business classes stay out; Lethbridge is not computable at s1; Naka Power is territorial.
"""
from pathlib import Path

import pytest

from pipeline.representative_models import (build_models, coverage_report, crosswalk_rule_levels, load_crosswalk,
                                            load_rates, load_taxes, load_usage_levels, match_record)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITIES = load_rates(FIXTURES / "rm_records_b18_ab.json")
AS_OF = "2026-11-19"
DPM = 365.25 / 12
LETHBRIDGE, RED_DEER = "City of Lethbridge Electric Utility", "City of Red Deer Electric Light & Power"
MEDICINE_HAT = "City of Medicine Hat Electric Utility"


def _build(as_of=AS_OF):
    return build_models(CITIES + load_rates(FIXTURES / "rm_records_b14.json"), load_crosswalk(), load_usage_levels(),
                        load_taxes(), provinces=("AB",), as_of=as_of, market_documents={"ON": None, "AB": None})


def _model(result, model_id):
    return next(m for m in result["models"] if m["id"] == model_id)


def _costs(model, level_id):
    level = next(lv for lv in model["levels"] if lv["id"] == level_id)
    return {row["utility"]: row["cost_without_tax"] for row in level["utilities"]}


def test_every_record_is_mapped_or_excluded_with_the_owner_decisions():
    assert coverage_report(CITIES, load_crosswalk())["unmapped"] == []
    outcomes = {(r["utility_name"], r["tariff_code"]): match_record(r, load_crosswalk()) for r in CITIES}
    excluded = {key: o["exclude"] for key, o in outcomes.items() if o["exclude"]}
    assert {key for key, reason in excluded.items() if reason == "territory_planned_later"} == {
        (u, c) for u, c in outcomes if u == "Naka Power Utilities (NWT)"}
    assert excluded[(MEDICINE_HAT, "3.1")] == excluded[(MEDICINE_HAT, "3.3")] == "eligibility_unpublished"
    assert excluded[(LETHBRIDGE, "992")] == excluded[(LETHBRIDGE, "995")] == "no_reference_level"
    assert {key for key, reason in excluded.items() if reason == "paired_retail_component"} == {
        (LETHBRIDGE, "RoLR-Res"), (LETHBRIDGE, "RoLR-SB"),
        (RED_DEER, "RRT-61"), (RED_DEER, "RRT-63"), (RED_DEER, "RRT-64"), (RED_DEER, "RRT-78")}
    assert outcomes[(MEDICINE_HAT, "1.1")]["model"]["structure"] == "flat"


def test_city_units_join_the_alberta_residential_median_with_hand_checked_costs():
    model = _model(_build(), "AB|electricity|residential|flat|-")
    costs = _costs(model, "typical")
    assert len(costs) == 7 and model["coverage"]["utilities_in_province"] == 7
    for text in ("Median of 7 Alberta service areas' residential flat-rate tariffs",
                 "Coverage: 7 of 7 Alberta electricity service areas with live records",
                 "so each city is one service area"):
        assert text in model["method"], text
    # Lethbridge 991 wires + the City's Rate of Last Resort (Riders B and C, November 1, 2026).
    assert costs[LETHBRIDGE] == pytest.approx((0.3509 + 0.9372) * DPM + 1000 * (0.0338 + 0.0209 + 0.00126 - 0.012
                                                                                 + 0.09975), abs=0.01)
    # Red Deer 61 wires + Schedule D administration charge + 12.06 cents/kWh.
    assert costs[RED_DEER] == pytest.approx((0.6949 + 0.5228 + 0.3035) * DPM + 1000 * (0.0184 + 0.0182 + 0.00131
                                                                                        + 0.0024 + 0.1206), abs=0.01)
    # Medicine Hat bundled 1.1: the conservation surcharge applies to the 50 kWh above 950.
    assert costs[MEDICINE_HAT] == pytest.approx((0.5299 + 0.0952) * DPM + 1000 * (0.0274 + 0.02859 + 0.07 + 0.005)
                                                + 50 * 0.0074, abs=0.01)


def test_a_record_past_its_own_end_date_is_left_out_instead_of_priced_without_its_energy():
    # Medicine Hat's November record ends with its month-dated default energy price; its undated Capacity Charge
    # must not keep it in the median at a delivery-only cost (owner decision 2026-11-19).
    model_id = "AB|electricity|residential|flat|-"
    assert MEDICINE_HAT in _costs(_model(_build("2026-11-30"), model_id), "typical")
    model = _model(_build("2026-12-01"), model_id)
    costs = _costs(model, "typical")
    assert MEDICINE_HAT not in costs and len(costs) == 6
    reasons = [e["reason"] for e in model["exclusions"] if e.get("utility") == MEDICINE_HAT]
    assert reasons and all("record ended on 2026-11-30; no newer record is stored" in r for r in reasons)


def test_a_market_reference_operator_is_not_counted_as_a_missing_service_area():
    # AESO's only live record is a value-less pool-price reference, so it never counts toward Alberta's coverage
    # (owner decision 2026-11-20); before, the text read "7 of 8 ...; no mapped record: Alberta Electric System
    # Operator".
    aeso = [r for r in load_rates(FIXTURES / "rm_records_ws_6d.json")
            if r["utility_name"] == "Alberta Electric System Operator"]
    assert len(aeso) == 1
    result = build_models(CITIES + load_rates(FIXTURES / "rm_records_b14.json") + aeso, load_crosswalk(),
                          load_usage_levels(), load_taxes(), provinces=("AB",), as_of=AS_OF,
                          market_documents={"ON": None, "AB": None})
    for model in result["models"]:
        if model["key"]["fuel"] == "electricity":
            assert model["coverage"]["utilities_in_province"] == 7, model["id"]
            assert "Alberta Electric System Operator" not in model["method"], model["id"]
    residential = _model(result, "AB|electricity|residential|flat|-")
    assert residential["coverage"]["missing_utilities"] == []
    assert "Coverage: 7 of 7 Alberta electricity service areas with live records" in residential["method"]


def test_lethbridge_three_phase_rate_skips_the_single_phase_level():
    assert crosswalk_rule_levels(load_crosswalk())["ab-lethbridge-994"] == ["s2", "m1"]
    model = _model(_build(), "AB|electricity|commercial|demand|commercial_small")
    assert LETHBRIDGE not in _costs(model, "s1") and LETHBRIDGE in _costs(model, "s2")
    reasons = [e["reason"] for e in model["exclusions"] if e.get("utility") == LETHBRIDGE and e.get("level") == "s1"]
    assert reasons and "covers only levels s2, m1" in reasons[0]


def test_city_rate_of_last_resort_applies_only_below_250000_kwh():
    result = _build()
    small = _costs(_model(result, "AB|electricity|commercial|flat|commercial_small"), "s2")
    medium = _model(result, "AB|electricity|commercial|demand|commercial_medium")
    # s2 is 10,000 kWh at 40 kW since 7D-2 (owner decision 2026-11-20).
    assert small[RED_DEER] == pytest.approx((1.0151 + 1.6269 + 0.3035) * DPM + 10000 * (0.0361 + 0.0155 + 0.00131
                                                                                         + 0.0024 + 0.1206), abs=0.01)
    assert medium["state"] == "market_energy_pending"
    kva_days = 100 / 0.9 * DPM
    assert _costs(medium, "m1")[RED_DEER] == pytest.approx(kva_days * (0.2533 + 0.1847) + 40000 * (
        0.0143 + 0.0143 + 0.00131 + 0.0024), abs=0.01)
