"""Phase 7C representative models: every province with live data, Alberta wires + Rate of Last Resort pairs, plus the
7C-2 additions (two-month charges, reviewed block periods, required contributors, contributor nouns) and the Phase 7E
illustrative sidecar (synthetic load profile).

Frozen fixtures and inline market documents only (tests/fixtures/rm_records_b14.json plus the 7A/7B samples), so the
tests never depend on the live export or the live market file.
"""
import copy
import json
import logging
from pathlib import Path

import pytest

from pipeline import export_json, representative_models as rm
from pipeline.representative_models import (build_models, compose_pairs, coverage_report, latest_live_records,
                                            load_crosswalk, load_rates, load_taxes, load_usage_levels, match_record,
                                            record_covers_level, record_monthly_cost)
from scrapers.utils.market_pricing import ROLLING_METHOD, synthetic_profile_price

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FIXTURE = FIXTURES / "rm_records_b14.json"
ON_FIXTURE = FIXTURES / "rm_engine_sample.json"
AS_OF = "2026-10-16"
ON_AS_OF = "2026-10-09"
DPM = 365.25 / 12
PROVINCES = ("ON", "AB", "BC", "MB", "NB", "NL", "NS", "PE", "QC", "SK")
AB_RES = "AB|electricity|residential|flat|-"
AB_SMALL = "AB|electricity|commercial|demand|commercial_small"
AB_MEDIUM = "AB|electricity|commercial|demand|commercial_medium"
AB_LARGE = "AB|electricity|commercial|demand|commercial_large"
BC_RES_FLAT = "BC|electricity|residential|flat|-"
BC_RES_TIERED = "BC|electricity|residential|tiered|-"
NL_RES = "NL|electricity|residential|flat|-"
ON_MEDIUM = "ON|electricity|commercial|demand|commercial_medium"
ON_LARGE = "ON|electricity|commercial|demand|commercial_large"
ENMAX, ATCO = "ENMAX Power + ENMAX Energy Corporation", "ATCO Electric + Direct Energy Regulated Services"
EPCOR, FORTIS = "EPCOR Distribution + EPCOR Energy Alberta", "FortisAlberta + EPCOR Energy Alberta"
STATES = {"modeled", "single_source", "market_energy_pending", "not_computable"}
SYNTHETIC = "SYNTHETIC LOAD PROFILE - ILLUSTRATIVE ONLY"
BCH_1101 = {"id": "test-bc-hydro-1101", "utility": "BC Hydro", "match": {"tariff_code": "1101"},
            "threshold_period": "two_months", "quote": "Bi-monthly threshold shown; monthly threshold is 675 kWh.",
            "source_url": "https://example.org/bchydro-electric-tariff.pdf", "location": "Rate Schedule 1101",
            "reviewed": True}


def _records():
    return load_rates(FIXTURE)


def _by_id(record_id):
    return next(r for r in _records() if r["id"] == record_id)


def _build(records=None, provinces=PROVINCES, crosswalk=None, block_periods=None, market_document=None):
    return build_models(_records() if records is None else records, crosswalk or load_crosswalk(), load_usage_levels(),
                        load_taxes(), provinces=provinces, as_of=AS_OF, block_periods=block_periods,
                        market_document=market_document)


def _model(result, model_id):
    return next(m for m in result["models"] if m["id"] == model_id)


def _level(model, level_id):
    return next(lv for lv in model["levels"] if lv["id"] == level_id)


def _row(level, utility):
    return next(r for r in level["utilities"] if r["utility"] == utility)


def _cost(record, kwh, kw=None, sector="residential", structure="flat", block_periods=None):
    return record_monthly_cost(record, kwh, kw, sector=sector, structure=structure, usage_levels=load_usage_levels(),
                               as_of=AS_OF, block_periods=block_periods)


def _c(ctype, value, unit, name, **extra):
    comp = {"component_type": ctype, "component_name": name, "charge_value": value, "charge_unit": unit,
            "notes": "Provenance: live_parsed. "}
    comp.update(extra)
    return comp


def _rec(components, utility="Synthetic Power", code="X", province="BC", cls="commercial", rid=1, **extra):
    record = {"id": rid, "utility_name": utility, "province": province, "utility_type": "electricity",
              "name": f"{utility} {code}", "tariff_code": code, "customer_class": cls, "rate_structure": "demand",
              "effective_date": "2026-01-01", "provenance": "live", "components": components}
    record.update(extra)
    return record


def _variants(record_id):
    live = latest_live_records(_records())
    variants, _, _ = compose_pairs(live, load_crosswalk())
    record = next(r for r in live if r["id"] == record_id)
    return variants[id(record)]


def test_fixture_is_a_frozen_subset_of_latest_live_records():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    records = data["records"]
    assert data["count"] == len(records) == 27 and data["extracted_from"] == "site/data/rates.json"
    assert all(r["provenance"] == "live" and r["components"] for r in records)
    assert len(latest_live_records(records)) == len(records)
    assert {r["province"] for r in records} == {"AB", "BC", "NB", "NL", "NS", "QC", "SK"}


def test_alberta_pairs_count_once_and_keep_each_components_source_and_dates():
    model = _model(_build(), AB_RES)
    assert model["state"] == "modeled" and model["provenance"] == "modeled"
    assert model["coverage"]["contributing_utilities"] == sorted([ATCO, ENMAX, EPCOR, FORTIS])
    assert model["coverage"]["utilities_in_province"] == 4
    typical = _level(model, "typical")
    assert typical["without_tax"]["n"] == 4
    enmax = _row(typical, ENMAX)
    assert enmax["records"] == ["3014+3036"]
    wires, retail = _by_id(3014), _by_id(3036)
    expected = sum(c["charge_value"] * (1000 if c["charge_unit"] == "$/kWh" else DPM)
                   for c in wires["components"] + retail["components"])
    assert enmax["cost_without_tax"] == round(expected, 2) == 213.43
    composite = _variants(3014)[0]
    assert composite["utility_name"] == ENMAX and composite["tariff_code"] == "D100+RoLR-Res"
    parts = {(c["pair_part"], c["component_name"]): c for c in composite["components"]}
    assert parts[("retail", "RoLR Energy Charge")]["source_url"] == retail["source_url"]
    assert parts[("retail", "RoLR Energy Charge")]["end_date"] == "2026-12-31"
    assert parts[("wires", "Transmission Variable Charge")]["source_url"] == wires["source_url"]
    assert composite["effective_date"] == max(wires["effective_date"], retail["effective_date"])
    assert {r["utility"] for r in typical["utilities"]} == {ATCO, ENMAX, EPCOR, FORTIS}


def test_rate_of_last_resort_applies_only_below_250000_kwh_a_year():
    retail, market = _variants(3021)
    assert retail["pair"]["variant"] == "retail" and market["pair"]["variant"] == "market"
    assert record_covers_level(retail, 20833.0, 25) and not record_covers_level(retail, 250000 / 12, 25)
    assert record_covers_level(market, 250000 / 12, 25) and not record_covers_level(market, 20833.0, 25)
    result = _build()
    s2 = _row(_level(_model(result, AB_SMALL), "s2"), ATCO)
    assert s2["records"] == ["3021+3035"]
    medium = _model(result, AB_MEDIUM)
    assert medium["state"] == "market_energy_pending" and medium["cost_basis"] == "delivery_only_market_energy_pending"
    m1 = _level(medium, "m1")
    assert _row(m1, ATCO)["records"] == [3021] and _row(m1, ENMAX)["records"] == [3016]
    assert {p["utility"] for p in medium["energy"]["market_pending"]} == {ATCO, ENMAX}
    assert "Alberta pool price" in medium["energy"]["market_pending"][0]["components"][0]


def test_atco_small_business_pair_matches_a_hand_calculation_with_per_kw_energy_blocks():
    s1 = _row(_level(_model(_build(), AB_SMALL), "s1"), ATCO)
    assert s1["cost_without_tax"] == 542.69
    res = _cost(_variants(3021)[0], 8000, 25, sector="commercial_small", structure="demand")
    items = {i["component"]: i for i in res["items"]}
    assert items["Distribution Energy Charge (first 200 kWh per kW of billing demand)"]["amount"] == pytest.approx(
        0.0426 * 200 * 25)
    assert items["Transmission Energy Charge (in excess of 200 kWh per kW of billing demand)"]["amount"] == pytest.approx(
        0.0058 * (8000 - 5000))
    assert items["RoLR Energy Charge"]["amount"] == pytest.approx(0.1202 * 8000)


def test_a_wires_class_without_a_retail_record_is_not_computable_at_rate_of_last_resort_levels():
    small = _model(_build(), AB_SMALL)
    reasons = " ".join(e["reason"] for e in small["exclusions"] if e["scope"] in ("record", "utility"))
    assert "no Rate of Last Resort record for D300 sites" in reasons
    assert ENMAX not in small["coverage"]["contributing_utilities"]


def test_only_market_priced_energy_makes_a_model_pending():
    large = _model(_build(), AB_LARGE)
    assert large["state"] == "market_energy_pending"
    other = large["energy"]["market_indexed_excluded"]
    assert other and other[0]["utility"] == EPCOR and "Transmission Operating Reserve Charge" in other[0]["components"][0]
    counted = {e["reason"]: e["count"] for e in large["exclusions"] if e["scope"] == "component"}
    assert counted["market_indexed_non_energy"] == 1
    assert "Excludes market-indexed charges with no stored value that are not the energy price" in large["method"]
    assert "pending Phase 6C" in large["method"]
    reserve = _c("transmission", None, "$/kWh", "Operating Reserve", market_reference="pool price x 8%")
    record = _rec([_c("fixed", 20.0, "$/month", "Basic"), _c("energy", 0.1, "$/kWh", "Energy"), reserve],
                  utility="BC Hydro", code="1300", structure="flat")
    res = _cost(record, 2000, 10, sector="commercial_small")
    assert res["status"] == "ok" and res["energy_status"] == "included" and res["cost"] == pytest.approx(220.0)
    assert res["market_pending"] == []
    model = _model(_build([record], provinces=("BC",)), "BC|electricity|commercial|flat|commercial_small")
    assert model["state"] == "single_source" and model["energy"]["market_pending"] == []
    assert "pending Phase 6;" in model["method"]
    assert rm.component_exclusion(_c("energy", None, "$/kWh", "Market", market_reference="IESO")) == "market_pending"
    assert rm.component_exclusion(reserve) == "market_indexed_non_energy"


def test_units_that_need_an_assumed_conversion_are_not_computable_with_the_reason():
    rural = _cost(_by_id(1305), 1000)
    assert rural["status"] == "not_computable"
    assert "Basic Charge ($/billing period)" in " ".join(rural["reasons"])
    rate_g = _cost(_by_id(20), 2000, 10, sector="commercial_small", structure="demand")
    assert "tier threshold unit 'kWh' has no stated period" in " ".join(rate_g["reasons"])
    model = _model(_build(), "QC|electricity|commercial|demand|commercial_small")
    assert model["state"] == "not_computable" and all(lv["without_tax"]["median"] is None for lv in model["levels"])


def test_unmarked_fixed_charge_variants_are_never_added_together():
    res = _cost(_by_id(50), 1000)
    assert res["status"] == "not_computable"
    assert "fixed charge published as variants without a selection rule" in " ".join(res["reasons"])


def test_published_thresholds_daily_blocks_and_reviewed_two_month_blocks():
    quebec = _cost(_by_id(19), 2000, structure="tiered")
    first = 40 * DPM
    assert quebec["cost"] == pytest.approx(first * 0.07065 + (2000 - first) * 0.11142 + 0.46154 * DPM)
    assert any("block threshold kWh/day x 30.4375" in (i.get("conversions") or []) for i in quebec["items"])
    bc_hydro = _cost(_by_id(13), 1000, structure="tiered", block_periods=[BCH_1101])
    assert bc_hydro["cost"] == pytest.approx(675 * 0.1187 + 325 * 0.1408 + 0.2344 * DPM)
    threshold = [_c("demand", 10.0, "$/kW", "Demand above 50 kW", demand_threshold_kw=50.0)]
    assert _cost(_rec(threshold), 2000, 25, sector="commercial_small")["cost"] == pytest.approx(0.0)
    assert _cost(_rec(threshold), 40000, 100, sector="commercial_medium")["cost"] == pytest.approx(500.0)
    blocks = [_c("demand", 0.0, "$/kVA", "Demand first 50 kVA", tier_number=1, tier_threshold=50.0, tier_unit="kVA"),
              _c("demand", 21.632, "$/kVA", "Demand balance", tier_number=2, tier_threshold=50.0, tier_unit="kVA")]
    assert _cost(_rec(blocks), 40000, 100, sector="commercial_medium")["cost"] == pytest.approx((100 / 0.9 - 50) * 21.632)
    no_bounds = [dict(c, tier_threshold=None) for c in blocks]
    assert "demand block thresholds missing" in " ".join(_cost(_rec(no_bounds), 40000, 100)["reasons"])


def test_reviewed_annual_use_bounds_route_levels_to_the_eligible_class():
    result = _build()
    small_tiered = _model(result, "NS|electricity|commercial|tiered|commercial_small")
    assert _level(small_tiered, "s1")["without_tax"]["n"] == 1 and _level(small_tiered, "s2")["without_tax"]["n"] == 0
    small_demand = _model(result, "NS|electricity|commercial|demand|commercial_small")
    assert _level(small_demand, "s1")["without_tax"]["n"] == 0 and _level(small_demand, "s2")["without_tax"]["n"] == 1


def test_optional_time_of_use_and_peak_event_products_stay_out_of_the_medians():
    crosswalk = load_crosswalk()
    for record_id in (1187, 1213, 3020):
        outcome = match_record(_by_id(record_id), crosswalk)
        assert (outcome["model"], outcome["exclude"]) == (None, "optional_product"), record_id
    ids = {m["id"] for m in _build()["models"]}
    assert not any(part in model_id for model_id in ids for part in ("|tou|", "|tiered_tou|", "|critical_peak|")
                   if not model_id.startswith("ON|"))


def test_province_labels_method_texts_and_states_are_generic():
    result = _build()
    assert result["method_version"] == rm.METHOD_VERSION == "7C-2"
    assert result["input"]["fuels"] == ["electricity"] and result["input"]["provinces"] == sorted(PROVINCES)
    for model in result["models"]:
        province = model["key"]["province"]
        assert model["state"] in STATES and model["key"]["fuel"] == "electricity"
        assert len(model["label"].split(" - ")) == 3 and model["label"].startswith(rm.PROVINCE_NAMES[province])
        assert ("loss factors" in model["method"]) == (province == "ON")
        assert ("Class A Global Adjustment" in model["method"]) == (province == "ON")
    alberta = _model(result, AB_RES)
    for text in ("Median of 4 Alberta wires + Rate of Last Resort pairs' residential flat-rate tariffs",
                 "Direct Energy Regulated Services' daily administration charge is not included",
                 "applies only below 250,000 kWh a year", "Coverage: 4 of 4 Alberta electricity wires + Rate of Last "
                 "Resort pairs with live records", "municipal franchise and local access fees"):
        assert text in alberta["method"], text
    assert result["assumptions"]["pairs"]["retail_below_annual_kwh"] == 250000
    quebec = _model(result, "QC|electricity|residential|tiered|-")
    assert quebec["state"] == "single_source" and "is the only Quebec utility" in quebec["method"]


def test_crosswalk_maps_alberta_wires_classes_and_marks_retail_records_as_pair_parts():
    crosswalk = load_crosswalk()
    b12 = load_rates(FIXTURES / "rm_records_b12.json")
    seen = {}
    for record in b12:
        if record["province"] != "AB" or record["utility_type"] != "electricity":
            continue
        outcome = match_record(record, crosswalk)
        seen[(record["utility_name"], record["tariff_code"])] = outcome["exclude"] or outcome["model"]["structure"]
        assert outcome["rule_id"].startswith("ab-") and outcome["exclude"] != "province_not_modelled_yet_7c"
    assert len(seen) == 28
    assert {k for k, v in seen.items() if v == "paired_retail_component"} == {
        (u, c) for u, c in seen if u in ("Direct Energy Regulated Services", "ENMAX Energy Corporation",
                                         "EPCOR Energy Alberta")}
    assert {k for k, v in seen.items() if v == "supply_voltage_alternative"} == {
        ("ENMAX Power", "D410"), ("ATCO Electric", "T31"), ("EPCOR Distribution", "DAS-TOUP"), ("FortisAlberta", "65")}
    assert seen[("ATCO Electric", "D13")] == "optional_product"
    units = {u["wires"]: {c["wires_code"] for c in u["classes"]} for u in crosswalk["pairs"]["units"]}
    for (utility, code), value in seen.items():
        if value in ("flat", "demand"):
            assert code in units[utility], (utility, code)


def test_frozen_samples_together_leave_nothing_unmapped():
    records = load_rates(FIXTURES / "rm_records_sample.json") + load_rates(FIXTURES / "rm_records_b12.json") + _records()
    report = coverage_report(records, load_crosswalk())
    assert report["unmapped"] == [] and report["unused_rules"] == []
    assert "province_not_modelled_yet_7c" not in report["exclusions"]
    assert report["exclusions"]["paired_retail_component"] == 8
    assert report["model_keys"][AB_RES]["utilities"] == ["ATCO Electric", "ENMAX Power", "EPCOR Distribution",
                                                         "FortisAlberta"]


def test_gas_and_territories_are_not_modelled():
    records = load_rates(FIXTURES / "rm_records_sample.json") + load_rates(FIXTURES / "rm_records_b12.json")
    result = build_models(records, load_crosswalk(), load_usage_levels(), load_taxes(), provinces=None, as_of=AS_OF,
                          block_periods=None, market_document=None)
    assert {m["key"]["fuel"] for m in result["models"]} == {"electricity"}
    assert not {m["key"]["province"] for m in result["models"]} & {"YT", "NT", "NU"}
    assert "Phase 7D" in result["assumptions"]["fuels"]


def test_ontario_engine_fixture_keeps_its_7b_numbers():
    fx = json.loads((FIXTURES / "rm_engine_sample.json").read_text(encoding="utf-8"))
    result = build_models(fx, fx["crosswalk"], fx["usage_levels"], fx["taxes"], as_of="2026-10-09")
    assert result["version"] == 1 and result["method_version"] == "7C-2" and result["as_of"] == "2026-10-09"
    assert result["input"]["records_considered"] == 36 and result["input"]["rates_generated_at"] == "2026-10-08T15:23:54Z"
    assert all(m["state"] in STATES and m["provenance"] == "modeled" for m in result["models"])
    typical = _level(_model(result, "ON|electricity|residential|tou|-"), "typical")
    assert (typical["without_tax"]["median"], typical["with_tax"]["median"]) == (198.09, 177.29)
    assert _model(result, "ON|electricity|residential|tou|-")["cost_basis"] == "delivery_and_energy"
    medium = _model(result, "ON|electricity|commercial|demand|commercial_medium")
    assert _level(medium, "m1")["without_tax"]["median"] == 1908.08
    assert medium["cost_basis"] == "delivery_only_no_energy_component"
    assert [(o["utility"], o["deviation_pct"]) for o in _level(medium, "m1")["outliers"]] == [
        ("Hydro One Networks Inc.", 76.0), ("Ottawa River Power Corporation", -46.2)]
    xlarge = _model(result, "ON|electricity|commercial|demand|commercial_xlarge")
    assert xlarge["state"] == "single_source" and xlarge["levels"] == []


def test_export_model_provinces_cover_the_ten_provinces_in_a_stable_order():
    assert export_json.MODEL_PROVINCES == PROVINCES and len(set(PROVINCES)) == 10


def test_export_hook_writes_compact_all_province_models_and_keeps_the_previous_file(tmp_path, monkeypatch, caplog):
    out = tmp_path / "site" / "representative_models.json"
    result = export_json.export_representative_models(_records(), out)
    text = out.read_text(encoding="utf-8")
    written = json.loads(text)
    assert text == json.dumps(written, separators=(",", ":"), ensure_ascii=False) + "\n"
    assert written["input"]["provinces"] == sorted(PROVINCES) and written["input"]["fuels"] == ["electricity"]
    assert written["method_version"] == "7C-2" and AB_RES in {m["id"] for m in result["models"]}
    previous = out.read_bytes()

    def broken(*args, **kwargs):
        raise RuntimeError("model build failed")

    monkeypatch.setattr(rm, "build_models", broken)
    with caplog.at_level(logging.ERROR, logger="pipeline.export_json"):
        assert export_json.export_representative_models(_records(), out) is None
    assert out.read_bytes() == previous and not list(out.parent.glob("*.tmp"))


def test_cli_build_defaults_to_the_export_provinces_and_writes_compact_json(tmp_path, capsys):
    output = tmp_path / "models.json"
    assert rm.main(["--build", "--rates", str(FIXTURE), "--output", str(output), "--as-of", AS_OF]) == 0
    text = output.read_text(encoding="utf-8")
    written = json.loads(text)
    assert text == json.dumps(written, separators=(",", ":"), ensure_ascii=False) + "\n"
    assert written["input"]["provinces"] == sorted(PROVINCES) and written["as_of"] == AS_OF
    assert AB_RES in capsys.readouterr().out


# 7C-2 (user decisions October 16, 2026)

def test_two_month_charges_are_halved_exactly():
    fortis = _by_id(1242)
    basic = next(c for c in fortis["components"] if c["charge_unit"] == "$/two months")
    res = _cost(fortis, 1000)
    assert res["status"] == "ok"
    item = next(i for i in res["items"] if i["component"] == basic["component_name"])
    assert item["amount"] == pytest.approx(basic["charge_value"] / 2) and item["conversions"] == ["$/two months / 2"]
    model = _model(_build(), BC_RES_FLAT)
    assert model["state"] == "single_source" and "$/two months / 2" in model["method"]
    assert _row(_level(model, "typical"), "FortisBC Electric")["cost_without_tax"] == round(res["cost"], 2)
    # replaces test_rm7b_valueless_non_market_components_and_unsupported_units_are_not_computable
    bimonthly = _cost(_rec([_c("fixed", 10.0, "$/two months", "Bimonthly")], cls="residential"), 1000)
    assert bimonthly["status"] == "ok" and bimonthly["cost"] == pytest.approx(5.0)
    no_value = _cost(_rec([_c("fixed", 10.0, "$/month", "Basic"), _c("rider", None, "$/month", "Unpriced")]), 1000)
    assert no_value["status"] == "not_computable" and "no published value: Unpriced" in " ".join(no_value["reasons"])
    odd = _cost(_rec([_c("fixed", 10.0, "$/billing period", "Per bill")]), 1000)
    assert "unit not supported by the engine: Per bill ($/billing period)" in " ".join(odd["reasons"])


BLOCKS = [_c("energy", 0.10, "$/kWh", "First block", tier_number=1, tier_threshold=1000.0, tier_unit="kWh"),
          _c("energy", 0.20, "$/kWh", "Balance", tier_number=2, tier_threshold=1000.0, tier_unit="kWh")]


def _period(period, entry_id="p", utility="Synthetic Power", match=None, **extra):
    entry = {"id": entry_id, "utility": utility, "match": match or {"tariff_code": "X"}, "threshold_period": period,
             "quote": "First 1,000 kWh", "source_url": "https://example.org/tariff.pdf", "location": "p. 1",
             "reviewed": True}
    entry.update(extra)
    return entry


def test_block_periods_set_the_period_of_bare_kwh_thresholds():
    record = _rec(BLOCKS, cls="residential")

    def cost(entries, kwh=1000, rec=record):
        return _cost(rec, kwh, structure="tiered", block_periods={"version": 1, "status": "test", "entries": entries})

    assert cost([_period("month")])["cost"] == pytest.approx(100.0)
    assert cost([_period("two_months")])["cost"] == pytest.approx(500 * 0.10 + 500 * 0.20)
    day = cost([_period("day")], kwh=40000)
    assert day["cost"] == pytest.approx(1000 * DPM * 0.10 + (40000 - 1000 * DPM) * 0.20)
    assert {i.get("block_period") for i in day["items"]} == {"p"}
    assert "block threshold kWh per day x 30.4375 (p)" in day["items"][0]["conversions"]
    for entries, text in (([], "(no reviewed data/models/block_periods.json entry)"),
                          ([_period(None)], "entry p: no period stated"),
                          ([_period("week")], "entry p: unsupported threshold_period 'week'"),
                          ([_period(None, "first"), _period("month", "second")], "entry first: no period stated"),
                          ([_period("month", reviewed=False)], "(no reviewed data/models/block_periods.json entry)"),
                          ([_period("month", utility="Other Power")], "(no reviewed"),
                          ([_period("month", match={"tariff_code": "Y"})], "(no reviewed"),
                          ([_period("month", component_name_regex="^Other$")], "(no reviewed")):
        reasons = " ".join(cost(entries)["reasons"])
        assert "tier threshold unit 'kWh' has no stated period" in reasons and text in reasons, entries
    assert cost([_period("two_months", component_name_regex="^Balance$")])["cost"] == pytest.approx(150.0)
    assert cost([_period("two_months", match={"tariff_code_regex": "^X$"})])["cost"] == pytest.approx(150.0)
    codeless = dict(record, tariff_code=None, name="General Service Small")
    assert cost([_period("two_months", match={"name_regex": "^General Service Small$"})], rec=codeless)[
        "cost"] == pytest.approx(150.0)
    assert _cost(record, 1000, structure="tiered", block_periods=[_period("two_months")])["cost"] == pytest.approx(150.0)
    assert _cost(record, 1000, structure="tiered")["status"] == "not_computable"


def test_block_periods_are_disclosed_and_a_missing_file_never_fails_the_build(tmp_path, monkeypatch):
    result = _build(block_periods={"version": 1, "status": "test", "entries": [BCH_1101]})
    model = _model(result, BC_RES_TIERED)
    assert model["state"] == "single_source"
    assert model["block_periods"] == [{k: BCH_1101[k] for k in ("id", "utility", "threshold_period", "quote",
                                                                "source_url", "location")}]
    assert "test-bc-hydro-1101 (BC Hydro, per two months, halved)" in model["method"]
    assert "block threshold kWh per two months / 2 (test-bc-hydro-1101)" in model["method"]
    expected = 675 * 0.1187 + 325 * 0.1408 + 0.2344 * DPM
    assert _row(_level(model, "typical"), "BC Hydro")["cost_without_tax"] == round(expected, 2)
    assert [e["id"] for e in result["assumptions"]["block_periods"]["entries"]] == ["test-bc-hydro-1101"]
    without = _model(_build(), BC_RES_TIERED)
    assert without["state"] == "not_computable" and "block_periods" not in without
    monkeypatch.setattr(rm, "BLOCK_PERIODS_PATH", tmp_path / "block_periods.json")
    missing = rm.load_block_periods()
    assert missing["entries"] == [] and missing["problem"] == "block_periods.json not found"
    default = build_models(_records(), load_crosswalk(), load_usage_levels(), load_taxes(), provinces=("BC",),
                           as_of=AS_OF, market_document=None)
    assert default["assumptions"]["block_periods"]["problem"] == "block_periods.json not found"
    assert _model(default, BC_RES_TIERED)["state"] == "not_computable"
    (tmp_path / "block_periods.json").write_text(json.dumps(
        {"version": 1, "status": "test", "entries": [BCH_1101, {"id": "bad"}, dict(BCH_1101, id="u", reviewed=False)]}),
        encoding="utf-8")
    loaded = rm.load_block_periods()
    assert [e["id"] for e in loaded["entries"]] == ["test-bc-hydro-1101"] and loaded["status"] == "test"
    assert loaded["skipped"] == [{"id": "bad", "reason": "id and utility are required"},
                                 {"id": "u", "reason": "not reviewed"}]
    assert _model(build_models(_records(), load_crosswalk(), load_usage_levels(), load_taxes(), provinces=("BC",),
                               as_of=AS_OF, market_document=None), BC_RES_TIERED)["state"] == "single_source"
    (tmp_path / "block_periods.json").write_text("{", encoding="utf-8")
    assert rm.load_block_periods()["entries"] == [] and "unreadable" in rm.load_block_periods()["problem"]


def _nl_hydro(rid=9001, code="1.1L"):
    return _rec([_c("fixed", 20.0, "$/month", "Basic Customer Charge"), _c("energy", 0.10, "$/kWh", "Energy Charge")],
                utility="NL Hydro", code=code, province="NL", cls="residential", rid=rid)


def test_nl_residential_is_withheld_while_newfoundland_power_is_not_computable():
    nf_power = _by_id(50)
    assert _cost(nf_power, 1000)["status"] == "not_computable"
    model = _model(_build([nf_power, _nl_hydro()], provinces=("NL",)), NL_RES)
    assert model["state"] == "not_computable" and model["coverage"]["contributing_utilities"] == []
    for level in model["levels"]:
        assert level["without_tax"]["n"] == 0 and level["without_tax"]["median"] is None
        assert level["with_tax"]["median"] is None and level["utilities"] == [] and level["outliers"] == []
        assert level["closest_utility"] is None
        assert level["withheld"]["missing_required"] == ["Newfoundland Power"]
        assert level["withheld"]["computed_utilities"] == ["NL Hydro"]
        assert level["withheld"]["rules"] == ["nl-residential-newfoundland-power"]
    required = model["required_contributors"]
    assert [(r["id"], r["utilities"], r["decided"], r["withheld_at"]) for r in required] == [
        ("nl-residential-newfoundland-power", ["Newfoundland Power"], "user 2026-10-16", ["low", "typical", "high"])]
    assert "Labrador zone alone" in required[0]["reason"]
    assert "Withheld at low, typical, high: required utility Newfoundland Power is not computable there" in model[
        "method"]
    levels = [e["reason"] for e in model["exclusions"] if e["scope"] == "level"]
    assert len(levels) == 3 and all(r.startswith("required contributor not computable: Newfoundland Power") for r in levels)
    records = {e["record_id"]: e["reason"] for e in model["exclusions"] if e["scope"] == "record"}
    assert "withheld" in records[9001] and "fixed charge published as variants" in records[50]
    assert not model["warnings"]
    computable = _rec([_c("fixed", 15.0, "$/month", "Basic"), _c("energy", 0.14, "$/kWh", "Energy")],
                      utility="Newfoundland Power", code="1.1", province="NL", cls="residential", rid=9002)
    both = _model(_build([computable, _nl_hydro()], provinces=("NL",)), NL_RES)
    assert both["state"] == "modeled" and _level(both, "typical")["without_tax"]["n"] == 2
    assert "withheld" not in _level(both, "typical") and both["required_contributors"][0]["withheld_at"] == []
    crosswalk = load_crosswalk()
    crosswalk.pop("required_contributors")
    alone = _model(_build([nf_power, _nl_hydro()], provinces=("NL",), crosswalk=crosswalk), NL_RES)
    assert alone["state"] == "single_source" and "required_contributors" not in alone


def _on_fixture(inject=True, profiles=True):
    fx = json.loads(ON_FIXTURE.read_text(encoding="utf-8"))
    if inject:
        for record in fx["records"]:
            if record["rate_structure"] == "demand":
                record["components"].append(_c("energy", None, "$/kWh", "Market Energy (OEMP + Class B GA)",
                                               market_reference="IESO OEMP + GA (Class B)"))
    if profiles:
        fx["usage_levels"]["synthetic_profiles"] = load_usage_levels()["synthetic_profiles"]
    return fx


def _on_build(fx, **kwargs):
    kwargs.setdefault("block_periods", None)
    kwargs.setdefault("market_document", None)
    return build_models(fx, fx["crosswalk"], fx["usage_levels"], fx["taxes"], as_of=ON_AS_OF, **kwargs)


def _month_key(index):
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _market_doc(end="2026-08", energy=0.05, ga=0.06, method=ROLLING_METHOD, business=None):
    last = int(end[:4]) * 12 + int(end[5:]) - 1
    months = [_month_key(i) for i in range(last - 59, last + 1)]
    monthly = [{"month": m, "era": "hoep" if m < "2025-05" else "oemp", "energy_arithmetic": energy,
                "ga_class_b": ga, "total_arithmetic": round(energy + ga, 6)} for m in months]
    surface = [{"month": month, "day_type": kind, "hour": hour, "hours_count": 20 if kind == "weekday" else 8,
                "avg_energy_price": business if business and kind == "weekday" and 7 <= hour <= 18 else energy}
               for month in range(1, 13) for kind in ("weekday", "weekend") for hour in range(24)]
    return {"metadata": {"derivation_method": method, "schema_version": 2, "generated_at": "2026-10-16T00:00:00Z",
                         "window": {"start_month": months[0], "end_month": months[-1], "months": 60}},
            "monthly": monthly, "hourly_surface": surface}


def _without_sidecar(models):
    out = copy.deepcopy(models)
    for model in out:
        model.pop("illustrative", None)
        for level in model["levels"]:
            level.pop("illustrative_all_in", None)
    return out


def test_contributor_nouns_name_what_each_model_counts_once():
    result = _build()
    assert _model(result, AB_RES)["coverage"]["contributor_noun"] == {
        "singular": "wires + Rate of Last Resort pair", "plural": "wires + Rate of Last Resort pairs"}
    assert _model(result, BC_RES_FLAT)["coverage"]["contributor_noun"] == {"singular": "utility", "plural": "utilities"}
    ontario = _on_build(_on_fixture(inject=False, profiles=False))["models"]
    assert ontario and all(m["coverage"]["contributor_noun"] == {"singular": "distributor", "plural": "distributors"}
                           for m in ontario)


def test_usage_levels_hold_the_user_approved_synthetic_profile():
    profile = load_usage_levels()["synthetic_profiles"]["ON_SYNTHETIC_BUSINESS_HOURS"]
    assert profile["applies_to"] == {"province": "ON", "fuel": "electricity",
                                     "sectors": ["commercial_medium", "commercial_large"]}
    assert profile["status"].startswith("SYNTHETIC: user-approved 2026-10-16") and profile["label"] == SYNTHETIC
    assert profile["business_hours_beginning"] == list(range(7, 19)) and profile["max_window_lag_months"] == 4
    assert (profile["days"], profile["time_basis"]) == ("Monday-Friday", "EST (IESO market time)")
    assert profile["holidays"] == "counted as the weekday they fall on" and "base_load" in profile
    assert "not a forecast, a quote or a bill" in profile["caveat"] and profile["caveat"].endswith(
        "Needs further analysis.")


def test_illustrative_sidecar_adds_synthetic_market_energy_and_never_changes_the_model():
    fx = _on_fixture()
    result = _on_build(fx, market_document=_market_doc())
    baseline = _on_build(_on_fixture(profiles=False), market_document=_market_doc())
    assert _without_sidecar(result["models"]) == baseline["models"]
    assert _level(_model(result, ON_MEDIUM), "m1")["without_tax"]["median"] == 1908.08
    for model_id in (ON_MEDIUM, ON_LARGE):
        model = _model(result, model_id)
        assert model["state"] == "market_energy_pending"
        assert model["cost_basis"] == "delivery_only_market_energy_pending"
        info = model["illustrative"]
        assert info["available"] is True and info["reason"] is None and info["profile_id"] == "ON_SYNTHETIC_BUSINESS_HOURS"
        assert info["label"] == SYNTHETIC and info["caveat"].endswith("Needs further analysis.")
        assert info["window"] == {"start_month": "2021-09", "end_month": "2026-08", "months": 60}
        assert info["market_file"] == {"derivation_method": ROLLING_METHOD, "generated_at": "2026-10-16T00:00:00Z"}
        assert info["method"].startswith(SYNTHETIC + ":")
        for text in ("2021-09 to 2026-08", "44 legacy HOEP months, 16 Ontario Price months", "shape factor",
                     "Class B Global Adjustment only", "loss factors not modelled", "needs further analysis",
                     "not a forecast, a quote or a bill", "hours beginning 7-18 EST (IESO market time)",
                     "mean of the 60 monthly totals", "state stays market_energy_pending"):
            assert text in info["method"], text
        level = model["levels"][0]
        sidecar = level["illustrative_all_in"]
        assert sidecar["synthetic_profile"] is True and sidecar["illustrative_only"] is True
        assert sidecar["label"] == SYNTHETIC and sidecar["market_energy_per_kwh"] == pytest.approx(0.11)
        assert sidecar["market_energy_cost"] == pytest.approx(0.11 * level["kwh"])
        assert sidecar["profile"]["peak_kw"] == level["kw"] and sidecar["profile"]["business_hours_beginning"] == list(
            range(7, 19))
        assert set(sidecar["without_tax"]) == set(level["without_tax"])
        assert set(sidecar["with_tax"]) == set(level["with_tax"])
        assert sidecar["without_tax"]["n"] == level["without_tax"]["n"]
        for stat in ("median", "min", "max"):
            assert sidecar["without_tax"][stat] == pytest.approx(level["without_tax"][stat] + 0.11 * level["kwh"],
                                                                 abs=0.011)
        rate = sum(line["rate"] for line in level["with_tax"]["lines"] if line["kind"] == "sales_tax")
        assert rate > 0 and sidecar["with_tax"]["median"] == pytest.approx(
            sidecar["without_tax"]["median"] * (1 + rate), abs=0.02)
        assert [line["name"] for line in sidecar["with_tax"]["lines"]] == [line["name"] for line in
                                                                          level["with_tax"]["lines"]]
        assert sidecar["with_tax"]["not_applied"] == level["with_tax"]["not_applied"]


def test_illustrative_price_is_the_market_helpers_synthetic_profile_price():
    document = _market_doc(business=0.08)
    level = _level(_model(_on_build(_on_fixture(), market_document=document), ON_MEDIUM), "m1")
    expected = synthetic_profile_price(document, kwh=40000.0, kw=100.0, business_hours=list(range(7, 19)),
                                       as_of=ON_AS_OF, max_lag_months=4)
    assert expected["ok"] and expected["price_per_kwh"] > 0.11
    sidecar = level["illustrative_all_in"]
    assert sidecar["market_energy_per_kwh"] == expected["price_per_kwh"]
    assert sidecar["months"] == expected["months"] and sidecar["shape_factors"] == expected["shape_factors"]
    assert sidecar["market_energy_cost"] == round(expected["price_per_kwh"] * 40000, 2)


def test_illustrative_sidecar_is_unavailable_when_the_market_file_is_missing_wrong_or_stale(tmp_path, monkeypatch):
    fx = _on_fixture()
    monkeypatch.setattr(rm, "MARKET_PATH", tmp_path / "missing.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    cases = [("market history file missing.json not found", _on_build(fx, market_document=rm._DEFAULT)),
             ("no market history document was supplied", _on_build(fx)),
             ("not the rolling observed history",
              _on_build(fx, market_document=_market_doc(method="observed_legacy_hoep_2020_2024_average"))),
             ("stale market history: the window ends 2026-05, 5 months before 2026-10-09",
              _on_build(fx, market_document=_market_doc(end="2026-05")))]
    monkeypatch.setattr(rm, "MARKET_PATH", bad)
    cases.append(("market history file bad.json not usable", _on_build(fx, market_document=rm._DEFAULT)))
    for text, result in cases:
        for model_id in (ON_MEDIUM, ON_LARGE):
            model = _model(result, model_id)
            info = model["illustrative"]
            assert info["available"] is False and text in info["reason"], (text, info["reason"])
            assert model["state"] == "market_energy_pending" and info["method"] is None
            assert not any("illustrative_all_in" in level for level in model["levels"])
    stale = _model(cases[3][1], ON_MEDIUM)["illustrative"]
    assert stale["window"] == {"start_month": "2021-06", "end_month": "2026-05", "months": 60}


def test_illustrative_sidecar_only_for_market_pending_models_in_the_profile_scope():
    result = _on_build(_on_fixture(), market_document=_market_doc())
    assert {m["id"] for m in result["models"] if "illustrative" in m} == {ON_MEDIUM, ON_LARGE}
    delivery = _model(_on_build(_on_fixture(inject=False), market_document=_market_doc()), ON_MEDIUM)
    assert delivery["state"] != "market_energy_pending"
    assert delivery["illustrative"]["available"] is False
    assert delivery["illustrative"]["reason"].startswith(f"model state is {delivery['state']}")
    alberta = _build(market_document=_market_doc())
    assert _model(alberta, AB_MEDIUM)["state"] == "market_energy_pending"
    assert not any("illustrative" in m for m in alberta["models"])
    assert alberta["assumptions"]["market_file"] is None
