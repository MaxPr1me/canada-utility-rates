"""Method 7D-2 gas models (owner decisions of 2026-11-20): commercial general service for small and mid-size buildings,
Energir Rate D1 and Liberty Utility Gas, plus the reviewed class bounds they rely on.

Frozen latest live records from the run-46 export (tests/fixtures/rm_records_7d2_gas.json), so these tests never depend
on the live export. Expected costs are recomputed from the frozen components (hand calculations), not copied from the
engine.
"""
import copy
import json
import math
from pathlib import Path

import pytest

from pipeline import representative_models as rm

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "rm_records_7d2_gas.json"
AS_OF = "2026-11-23"
DPM = 365.25 / 12
LIBERTY, ENERGIR, CENTRA, ATCO = "Liberty Utilities Gas NB", "Energir", "Centra Gas Manitoba", "ATCO Gas"
BANDS = ["commercial_small", "commercial_medium"]


def _records() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["records"]


def _build(records=None, usage=None, crosswalk=None) -> dict:
    return rm.build_models(_records() if records is None else records, crosswalk or rm.load_crosswalk(),
                           usage or rm.load_usage_levels(), rm.load_taxes(), provinces=None, fuels=("gas",),
                           as_of=AS_OF, block_periods=[], market_document=None)


@pytest.fixture(scope="module")
def built() -> dict:
    return _build()


def _model(result: dict, model_id: str) -> dict:
    return next(m for m in result["models"] if m["id"] == model_id)


def _level(model: dict, level_id: str) -> dict:
    return next(lv for lv in model["levels"] if lv["id"] == level_id)


def _row(level: dict, utility: str) -> dict:
    return next(row for row in level["utilities"] if row["utility"] == utility)


def _values(utility: str, code: str, customer_class: str = None) -> dict:
    record = next(r for r in _records() if r["utility_name"] == utility and r["tariff_code"] == code
                  and customer_class in (None, r["customer_class"]))
    return {c["component_name"]: c["charge_value"] for c in record["components"]}


def _codes(row: dict) -> list[str]:
    by_id = {r["id"]: r["tariff_code"] for r in _records()}
    return sorted(by_id[record_id] for record_id in row["records"])


def test_commercial_levels_are_the_approved_sets_with_documented_backing():
    gas = rm.load_usage_levels()["gas"]
    expected = {"commercial_small": {"m3": [500, 1000, 2000], "GJ": [15, 30, 60]},
                "commercial_medium": {"m3": [2500, 5000, 10000], "GJ": [100, 200, 400]}}
    for band, units in expected.items():
        for unit, quantities in units.items():
            levels = [lv for lv in gas[band] if lv["unit"] == unit]
            assert [lv["quantity"] for lv in levels] == quantities
            # Decision 16: a reference level with x0.5 and x2 sensitivity levels.
            assert [lv["role"] for lv in levels] == ["sensitivity", "reference", "sensitivity"]
            assert all(lv["decided"].startswith("owner 2026-11-20") and lv["represents"] and lv["why"] for lv in levels)
            assert all(lv["sources"] and all(s["url"].startswith("https://") and s["date"] and s["figure"]
                                             for s in lv["sources"]) for lv in levels)
            assert all("sensitivity level" in lv["why"] for lv in levels if lv["role"] == "sensitivity")


@pytest.mark.parametrize("model_id, level_id, utility, codes", [
    ("ON|gas|commercial|tiered|commercial_small", "m3_small_low", "EPCOR Natural Gas (Ontario)", ["AYL-1-GS", "SB-1"]),
    ("ON|gas|commercial|tiered|commercial_small", "m3_small_reference", "EPCOR Natural Gas (Ontario)",
     ["AYL-1-GS", "SB-6"]),
    ("ON|gas|commercial|tiered|commercial_medium", "m3_medium_low", "Enbridge Gas",
     ["EGD-6", "UNE-01", "UNW-01", "US-M1"]),
    ("ON|gas|commercial|tiered|commercial_medium", "m3_medium_reference", "Enbridge Gas",
     ["EGD-6", "UNE-10", "UNW-10", "US-M2"]),
    ("AB|gas|commercial|flat|commercial_medium", "gj_medium_low", ATCO, ["N-LOW", "S-LOW"]),
    ("AB|gas|commercial|flat|commercial_medium", "gj_medium_reference", ATCO, ["N-MID", "S-MID"]),
    ("BC|gas|commercial|flat|commercial_medium", "gj_medium_low", "FortisBC Energy", ["Rate 2", "Rate 2"]),
    ("BC|gas|commercial|flat|commercial_medium", "gj_medium_reference", "FortisBC Energy", ["Rate 3", "Rate 3"]),
    ("SK|gas|commercial|flat|commercial_medium", "m3_medium_reference", "SaskEnergy", ["SC"]),
    ("SK|gas|commercial|flat|commercial_medium", "m3_medium_high", "SaskEnergy", ["LC"]),
])
def test_each_utility_is_priced_on_the_class_whose_published_limits_contain_the_level(built, model_id, level_id,
                                                                                    utility, codes):
    assert _codes(_row(_level(_model(built, model_id), level_id), utility)) == codes


def test_a_level_on_a_class_boundary_follows_the_reviewed_wording_and_fails_closed_without_it(built):
    # 100 GJ a month is 1,200 GJ a year: ATCO Low Use is "1,200 GJ per year or less" and Mid Use "more than 1,200".
    assert _codes(_row(_level(_model(built, "AB|gas|commercial|flat|commercial_medium"), "gj_medium_low"), ATCO)) == [
        "N-LOW", "S-LOW"]
    crosswalk = copy.deepcopy(rm.load_crosswalk())
    crosswalk["usage_bounds"] = [e for e in crosswalk["usage_bounds"] if not e["id"].startswith("ab-atco-gas-")]
    model = _model(_build(crosswalk=crosswalk), "AB|gas|commercial|flat|commercial_medium")
    assert _level(model, "gj_medium_low")["without_tax"]["n"] == 0
    reason = next(e["reason"] for e in model["exclusions"] if e.get("level") == "gj_medium_low")
    assert reason.count("on a stored class bound") == 4
    stale = copy.deepcopy(rm.load_crosswalk())
    next(e for e in stale["usage_bounds"] if e["id"] == "ab-atco-gas-mid-use")["max"] = 9000
    model = _model(_build(crosswalk=stale), "AB|gas|commercial|flat|commercial_medium")
    assert _level(model, "gj_medium_reference")["without_tax"]["n"] == 0
    assert "needs a new review" in next(e["reason"] for e in model["exclusions"] if e.get("level") == "gj_medium_reference")


def test_volume_bound_problem_tests_annual_and_peak_month_bounds():
    annual = {"utility_type": "gas", "usage_min": None, "usage_max": 50000, "usage_unit": "m³/year"}
    assert rm.volume_bound_problem(annual, 4000, "m3") is None
    assert "outside the stored eligibility" in rm.volume_bound_problem(annual, 5000, "m3")
    assert "on a stored class bound" in rm.volume_bound_problem(annual, 50000 / 12, "m3")
    assert "cannot be compared" in rm.volume_bound_problem(annual, 30, "GJ")
    peak = {"utility_type": "gas", "volume_bounds": {"id": "x", "unit": "GJ", "basis": "peak_month", "max": 250,
                                                       "max_inclusive": False, "quote": "less than 250 GJs per month"}}
    factor = {"id": "f", "factor": 1.85}
    assert rm.volume_bound_problem(peak, 100, "GJ", factor) is None
    assert "outside the class eligibility" in rm.volume_bound_problem(peak, 200, "GJ", factor)
    assert "no peak_month_factors entry" in rm.volume_bound_problem(peak, 100, "GJ")
    assert rm.volume_bound_problem({"utility_type": "gas"}, 10 ** 6, "m3") is None


def test_liberty_uses_the_monthly_peak_for_its_class_and_customer_charge(built):
    mgs, lgs, factor = _values(LIBERTY, "MGS"), _values(LIBERTY, "LGS"), 1.85
    supply = mgs["Liberty Utility Gas"]
    assert lgs["Liberty Utility Gas"] == supply
    block = "Monthly Distribution Delivery Charge \u2014 Block"
    winter, summer = lgs[block + " 2 (Sep-Apr)"], lgs[block + " 2 (May-Aug)"]
    # MGS: block 1 is the first 100 GJ; the customer charge is $22.50 up to a 60 GJ peak month, $52.50 above it.
    # LGS: block 1 (all year) is the first 250 GJ; block 2 is seasonal; $295 up to a 650 GJ peak month, $395 above.
    expected = {
        ("commercial_small", "gj_small_reference", 30): ("MGS", "nb-liberty-mgs-customer-charge",
                                                         22.5 + mgs[block + " 1"] * 30 + supply * 30),
        ("commercial_small", "gj_small_high", 60): ("MGS", "nb-liberty-mgs-customer-charge-higher",
                                                    52.5 + mgs[block + " 1"] * 60 + supply * 60),
        ("commercial_medium", "gj_medium_low", 100): ("MGS", "nb-liberty-mgs-customer-charge-higher",
                                                      52.5 + mgs[block + " 1"] * 100 + supply * 100),
        ("commercial_medium", "gj_medium_reference", 200): ("LGS", "nb-liberty-lgs-customer-charge",
                                                            295 + lgs[block + " 1"] * 200 + supply * 200),
        ("commercial_medium", "gj_medium_high", 400): ("LGS", "nb-liberty-lgs-customer-charge-higher",
                                                       395 + lgs[block + " 1"] * 250 + supply * 400
                                                       + (winter * 8 / 12 + summer * 4 / 12) * 150),
    }
    for (band, level_id, quantity), (code, rule, cost) in expected.items():
        model = _model(built, f"NB|gas|commercial|tiered|{band}")
        row = _row(_level(model, level_id), LIBERTY)
        assert _codes(row) == [code], level_id
        assert [v["rule"] for v in row["fixed_charge_variants"]] == [rule], level_id
        assert row["cost_without_tax"] == round(cost, 2), level_id
        assert (quantity * factor < 250) == (code == "MGS")
    model = _model(built, "NB|gas|commercial|tiered|commercial_medium")
    assert model["peak_month_factor"]["factor"] == factor and "1.85 x the level" in model["method"]


def test_energir_d1_prices_one_meter_its_basic_fee_band_daily_blocks_and_load_balancing(built):
    d1 = _values(ENERGIR, "D1", "commercial")
    per_m3 = math.fsum(d1[name] for name in ("Cap-and-Trade Emission Allowances (CTEAS)", "Natural Gas Supply",
                                             "Load Balancing", "Renewable Gas Socialization Cost",
                                             "Renewable Gas Socialization Rider", "Transportation"))
    block1, block2 = d1["Distribution \u2014 Block 1"], d1["Distribution \u2014 Block 2"]
    band = {n: d1[f"Basic Fee \u2014 Band {n}"] for n in (1, 2, 3)}
    first = 30 * DPM
    small = _model(built, "QC|gas|commercial|tiered|commercial_small")
    # 1,000 m3 a month: 12,000 m3 a year is basic-fee band 2 (10,950-36,500); 30 m3 a day is 913.125 m3 a month.
    row = _row(_level(small, "m3_small_reference"), ENERGIR)
    assert row["cost_without_tax"] == round(band[2] * DPM + block1 * first + block2 * (1000 - first) + per_m3 * 1000, 2)
    assert [v["component"] for v in row["fixed_charge_variants"]] == ["Basic Fee \u2014 Band 2"]
    assert _row(_level(small, "m3_small_low"), ENERGIR)["fixed_charge_variants"][0]["component"].endswith("Band 1")
    medium = _model(built, "QC|gas|commercial|tiered|commercial_medium")
    assert _row(_level(medium, "m3_medium_reference"), ENERGIR)["fixed_charge_variants"][0]["component"].endswith("Band 3")
    # 10,000 m3 a month is 120,000 m3 a year: load balancing follows a formula at 75,000 m3 a year or more.
    assert _level(medium, "m3_medium_high")["without_tax"]["n"] == 0
    reason = next(e["reason"] for e in medium["exclusions"] if e.get("level") == "m3_medium_high")
    assert "less than 75,000 m³ a year (qc-energir-load-balancing)" in reason
    assert {e["id"] for e in small["reference_customer"]} == {"qc-energir-load-balancing",
                                                              "qc-energir-renewable-gas-socialization"}
    home = _values(ENERGIR, "D1", "residential")
    residential = _row(_level(_model(built, "QC|gas|residential|tiered|-"), "m3_reference"), ENERGIR)
    assert home["Basic Fee \u2014 Band 1"] == band[1]
    assert residential["cost_without_tax"] == round(band[1] * DPM + block1 * 200 + per_m3 * 200, 2)


def test_centra_prices_the_cheaper_elective_class_and_names_it(built):
    def cost(code, volume):
        v = _values(CENTRA, code)
        return v["Basic Monthly Charge"] + (v["Gas Commodity"] + v["Distribution Charge"]
                                            + v["Transportation to Centra"] + v["Federal Carbon Charge"]) * volume
    small = _model(built, "MB|gas|commercial|flat|commercial_small")
    for level_id, volume in (("m3_small_low", 500), ("m3_small_reference", 1000), ("m3_small_high", 2000)):
        row = _row(_level(small, level_id), CENTRA)
        sgs, lgs = cost("COM-SGS", volume), cost("COM-LGS", volume)
        cheaper = "COM-SGS" if sgs <= lgs else "COM-LGS"
        assert row["cost_without_tax"] == round(min(sgs, lgs), 2) and _codes(row) == [cheaper]
        note = row["elective_classes"][0]
        assert note["group"] == "mb-centra-sgs-lgs" and note["chosen"] == cheaper
        assert {c["tariff_code"]: c["cost_without_tax"] for c in note["costs"]} == {"COM-SGS": round(sgs, 2),
                                                                                     "COM-LGS": round(lgs, 2)}
    assert small["elective_classes"][0]["chosen"] == {"m3_small_low": "COM-SGS", "m3_small_reference": "COM-SGS",
                                                       "m3_small_high": "COM-LGS"}
    assert "the cheaper is priced at each level" in small["method"]


def test_union_and_atco_low_use_records_also_serve_the_commercial_models_with_commercial_taxes(built):
    crosswalk = rm.load_crosswalk()
    union = next(r for r in _records() if r["tariff_code"] == "UNE-01")
    keys = rm.model_keys(rm.match_record(union, crosswalk))
    assert keys == [("ON", "gas", "residential", "tiered", None), ("ON", "gas", "commercial", "tiered", BANDS[0]),
                    ("ON", "gas", "commercial", "tiered", BANDS[1])]
    level = _level(_model(built, "ON|gas|commercial|tiered|commercial_small"), "m3_small_reference")
    assert union["id"] in _row(level, "Enbridge Gas")["records"]
    assert [line["name"] for line in level["with_tax"]["lines"]] == ["HST"]
    atco = _row(_level(_model(built, "AB|gas|commercial|flat|commercial_small"), "gj_small_reference"), ATCO)
    assert _codes(atco) == ["N-LOW", "S-LOW"]


def test_new_brunswick_homes_use_liberty_utility_gas_as_the_reference_supply(built):
    sgs = _values(LIBERTY, "SGS")
    row = _row(_level(_model(built, "NB|gas|residential|flat|-"), "gj_reference"), LIBERTY)
    assert row["cost_without_tax"] == round(sgs["Monthly Distribution Customer Charge"] + 8 * (
        sgs["Monthly Distribution Delivery Charge"] + sgs["Liberty Utility Gas"]), 2)
    entry = next(e for e in rm.load_usage_levels()["reference_customer"] if e["id"] == "nb-liberty-utility-gas")
    assert entry["exclusion"] == "optional" and "marketer" in entry["reason"]


def test_contract_interruptible_and_seasonal_gas_classes_are_left_out(built):
    crosswalk = rm.load_crosswalk()
    left_out = {"UNE-20", "US-M5", "AYL-2", "N-HIGH", "Rate 5", "Rate 7", "COM-HVF-S", "COM-IS-S", "D5", "RC3"}
    for record in _records():
        if record["tariff_code"] in left_out:
            assert rm.match_record(record, crosswalk)["exclude"] == "gas_models_phase_7d", record["name"]
    assert built["input"]["withheld_gas_models"]["models"] == []
    used = {i for m in built["models"] for lv in m["levels"] for row in lv["utilities"] for i in row["records"]}
    assert not {r["id"] for r in _records() if r["tariff_code"] in left_out} & used


def test_crosswalk_gas_rules_use_building_bands_and_bounds_quote_their_wording():
    crosswalk = rm.load_crosswalk()
    for rule in crosswalk["rules"]:
        targets = [rule["model"]] + list(rule["model"].get("also") or []) if rule.get("model") else []
        for target in targets:
            if rule["fuel"] == "gas" and target["sector"] == "commercial":
                assert target["size_band"] == BANDS, rule["id"]
    gas = [e for e in crosswalk["usage_bounds"] if "unit" in e]
    assert gas and len({e["id"] for e in gas}) == len(gas)
    for entry in gas:
        assert entry["unit"] in ("m3", "GJ") and entry["basis"] in ("annual", "peak_month"), entry["id"]
        assert entry["quote"] and entry["source"], entry["id"]
        for side in ("min", "max"):
            assert (entry[side] is None) == (entry[f"{side}_inclusive"] is None), entry["id"]
    assert {e["id"] for e in crosswalk["elective_classes"]} == {"mb-centra-sgs-lgs"}
    assert set(crosswalk["vocabulary"]["gas_size_bands"]) == set(BANDS)


def test_saskatchewan_commercial_gas_shows_pst_at_zero_with_medium_confidence(built):
    level = _level(_model(built, "SK|gas|commercial|flat|commercial_small"), "m3_small_reference")
    lines = {line["name"]: line for line in level["with_tax"]["lines"]}
    assert (lines["GST"]["rate"], lines["PST"]["rate"], lines["PST"]["confidence"]) == (0.05, 0.0, "medium")
    assert level["with_tax"]["median"] == round(level["without_tax"]["median"] * 1.05, 2)


def test_alberta_gas_methods_name_the_natural_gas_rebate_program(built):
    for model in built["models"]:
        if model["key"]["province"] == "AB":
            assert "Alberta Natural Gas Rebate Program" in model["method"], model["id"]


def test_fortisbc_electric_40_kw_follows_the_published_inclusive_bound():
    crosswalk = rm.load_crosswalk()

    def record(code, lo, hi):
        return rm.apply_usage_bounds({"utility_name": "FortisBC Electric", "utility_type": "electricity",
                                      "tariff_code": code, "demand_min_kw": lo, "demand_max_kw": hi}, crosswalk)
    rate20, rate21 = record("20", None, 40.0), record("21", 40.0, 500.0)
    # Rate 20: "not more than 40 kW"; Rate 21: "greater than 40 kW" (the engine default would be [min, max)).
    assert rm.record_covers_level(rate20, 10000, 40) and not rm.record_covers_level(rate21, 10000, 40)
    assert rm.record_covers_level(rate21, 40000, 100) and not rm.record_covers_level(rate20, 40000, 100)
    changed = record("20", None, 50.0)
    assert "needs a new review" in changed["demand_bounds_problem"] and not rm.record_covers_level(changed, 2000, 14)
