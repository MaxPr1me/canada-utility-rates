"""Method 7T-1: the territorial representative models (owner decisions 64-79, 2026-11-24).

Frozen latest live territorial records (tests/fixtures/rm_records_t.json, the run-46 export) with the reviewed
data/models/percentage_riders.json and subsidies.json, never the live export. Costs are checked against hand arithmetic
on the published charges; each test names the decision it pins.
"""
import copy
import statistics
from pathlib import Path

import pytest

from pipeline.representative_models import (build_models, coverage_report, load_block_periods, load_crosswalk,
                                            load_percentage_riders, load_rates, load_subsidies, load_taxes,
                                            load_usage_levels, match_record, record_monthly_cost)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RECORDS = load_rates(FIXTURES / "rm_records_t.json")
AS_OF = "2026-11-24"
TERRITORIES = ("YT", "NT", "NU")
YUKON, YEC = "Yukon Energy", "Yukon Electrical Company"
NTPC, NAKA, QEC = "Northwest Territories Power Corporation", "Naka Power Utilities (NWT)", "Qulliq Energy Corporation"
DASH = "\u2014"
NTPC_THERMAL = f"Residential Service {DASH} Diesel Zone"
YT_RES, NT_RES, NU_RES = ("YT|electricity|residential|tiered|-", "NT|electricity|residential|flat|-",
                          "NU|electricity|residential|flat|-")
YUKON_RIDERS = (14.38 + 100.23 + 15.91) / 100  # Riders R, J and J1, each a percentage of the base charges


def _record(utility, code=None, name=None):
    (record,) = [r for r in RECORDS if r["utility_name"] == utility
                 and (code is None or r["tariff_code"] == code) and (name is None or r["name"] == name)]
    return record


def _cost(record, kwh, kw=None, sector="residential", level=None, as_of=AS_OF, riders=True):
    return record_monthly_cost(record, kwh, kw, sector=sector, usage_levels=load_usage_levels(), as_of=as_of,
                               level=level, block_periods=load_block_periods()["entries"],
                               percentage_riders=load_percentage_riders()["entries"] if riders else None,
                               subsidies=load_subsidies())


def _build(records=None, as_of=AS_OF, **kwargs):
    return build_models(RECORDS if records is None else records, load_crosswalk(), load_usage_levels(), load_taxes(),
                        provinces=TERRITORIES, as_of=as_of, market_documents={"ON": None, "AB": None}, **kwargs)


RESULT = _build()


def _model(model_id, result=RESULT):
    return next(m for m in result["models"] if m["id"] == model_id)


def _level(model, level_id):
    return next(lv for lv in model["levels"] if lv["id"] == level_id)


def _rows(level):
    return {row["utility"]: row for row in level["utilities"]}


def test_every_territorial_record_is_mapped_or_excluded():
    report = coverage_report(RECORDS, load_crosswalk())
    assert report["unmapped"] == [] and report["totals"]["records"] == 38
    assert {m["id"] for m in RESULT["models"]} == {
        YT_RES, NT_RES, NU_RES, "YT|electricity|commercial|demand|commercial_small",
        "NT|electricity|commercial|demand|commercial_small", "NU|electricity|commercial|demand|commercial_small"}


def test_yukon_percentage_riders_apply_to_the_base_charges_only():
    # Decision 64: Riders R (14.38%), J (100.23%) and J1 (15.91%) of the base fixed and energy charges, never of other
    # riders; Rider F (1 cent per kWh) is not a base charge. Rate 1160 at 1,000 kWh:
    result = _cost(_record(YUKON, "1160"), 1000)
    assert result["status"] == "ok"
    base = 14.65 + 1000 * 0.1214            # base customer charge + first block (first 1,000 kWh) = $136.05
    riders = YUKON_RIDERS * base            # 130.52% of $136.05 = $177.5725
    fuel = 1000 * 0.01                      # Rider F on every kWh = $10.00
    assert result["cost"] == pytest.approx(base + riders + fuel)
    assert round(result["cost"], 2) == 323.62
    amounts = {item["component"]: item.get("amount") for item in result["items"]}
    assert amounts["Rider R - Base Rate Adjustment"] == pytest.approx(0.1438 * base)
    assert amounts["Rider J - Base Rate Adjustment"] == pytest.approx(1.0023 * base)
    assert amounts["Rider J1 - Temporary True-Up"] == pytest.approx(0.1591 * base)
    reasons = {item["component"]: item.get("reason") for item in result["items"]}
    assert reasons["Rider R - Base Rate Adjustment"] == "percentage_rider:yt-rider-r"
    assert reasons["Affordability Rate Relief"] == "subsidy"  # left out of the cost before subsidies
    typical = _level(_model(YT_RES), "typical")
    assert typical["without_tax"]["median"] == 323.62 and typical["without_tax"]["n"] == 1


def test_naka_percentage_riders_on_all_base_charges_reproduce_the_official_bill_impact():
    # Decision 64: Naka's Riders R, E and H apply to the customer, supply and fuel charges. Naka's July 1, 2026 notice:
    # a (government) Thermal residential customer using 600 kWh pays $99.26 more after the rider changes.
    record = _record(NAKA, "THERMAL-RES")
    before = copy.deepcopy(record)
    for comp in before["components"]:
        old = {"Revenue Adjustment (Rider R)": 14.8, "Temporary Refund/Surcharge (Rider E)": 0.8,
               "Fuel Cost Adjustment (Rider A)": -0.0779}.get(comp["component_name"])
        if old is not None:
            comp["charge_value"] = old
    increase = _cost(record, 600)["cost"] - _cost(before, 600)["cost"]
    # (26.7% + 2.1% - 14.8% - 0.8%) x ($18.00 + 600 x 84.15 cents) + 600 x (7.79 - 2.75) cents
    assert increase == pytest.approx(0.132 * (18 + 600 * 0.8415) + 600 * 0.0504)
    assert round(increase, 2) == 99.26


def test_an_unreviewed_percentage_rider_fails_closed_in_the_territories_only():
    record = copy.deepcopy(_record(YUKON, "1160"))
    record["components"].append({"component_type": "rider", "component_name": "Rider X - New Adjustment",
                                 "charge_value": 3.0, "charge_unit": "%", "notes": "Provenance: live_parsed. "})
    result = _cost(record, 1000)
    assert result["status"] == "not_computable"
    assert any("Rider X - New Adjustment" in reason and "percentage_riders.json" in reason
               for reason in result["reasons"])
    # Without the reviewed list, every territorial percentage rider fails closed instead of being dropped.
    assert _cost(_record(YUKON, "1160"), 1000, riders=False)["status"] == "not_computable"
    model = _model(YT_RES, _build([record if r is _record(YUKON, "1160") else r for r in RECORDS]))
    assert all(_rows(level).get(YUKON) is not None for level in model["levels"])  # the other zones still price
    assert any("Rider X" in e.get("reason", "") for e in model["exclusions"] if e["scope"] == "record")
    # Provinces keep disclosing percentage adjustments unapplied (no provincial entry; method unchanged).
    westminster = next(r for r in load_rates(FIXTURES / "rm_records_b18.json")
                       if r["utility_name"] == "City of New Westminster" and r["tariff_code"] == "101")
    provincial = _cost(westminster, 1000)
    assert provincial["status"] == "ok" and provincial["cost"] == pytest.approx(16.16 / 2 + 1000 * 0.1344)
    assert {i["reason"] for i in provincial["items"] if i["status"] == "excluded"} == {"percentage_base_not_computable"}


def test_missing_reviewed_lists_fail_closed():
    # No percentage list: Yukon and Naka records carry percentage riders, so they are not computable (never priced
    # without them); NTPC and Qulliq carry none and still price.
    without_riders = _build(percentage_riders=None)
    assert _model(YT_RES, without_riders)["state"] == "not_computable"
    assert set(_rows(_level(_model(NT_RES, without_riders), "typical"))) == {NTPC}
    # No subsidies list: the costs before subsidies are unchanged and no after-subsidy cost is published.
    without_subsidies = _model(NT_RES, _build(subsidies=None))
    assert _level(without_subsidies, "typical")["without_tax"] == _level(_model(NT_RES), "typical")["without_tax"]
    assert without_subsidies["subsidies"]["after_subsidy"] is False
    assert all(level["after_subsidy"]["available"] is False for level in without_subsidies["levels"])


def test_the_yellowknife_franchise_tax_stays_disclosed_and_unapplied():
    result = _cost(_record(NAKA, "SNARE-RES"), 1000)
    base = 18.00 + 1000 * 0.2372                       # customer + energy charges = $255.20
    assert result["cost"] == pytest.approx(base * 1.08199 + 1000 * 0.1084)  # Rider R 8.199% + Rider F = $384.52
    excluded = {i["component"]: i["reason"] for i in result["items"] if i["status"] == "excluded"}
    assert excluded == {"Franchise Tax": "percentage_excluded"}
    model = _model(NT_RES)
    riders = {r["id"]: r for r in model["percentage_riders"]}
    assert riders["nt-naka-franchise-tax"]["treatment"] == "exclude"
    assert "Franchise Tax 2.464% (nt-naka-franchise-tax)" in model["method"]


def test_the_joint_yukon_rate_book_counts_once_with_its_zones():
    crosswalk = load_crosswalk()
    assert {match_record(r, crosswalk)["exclude"] for r in RECORDS if r["utility_name"] == YEC} == {"duplicate_variant"}
    for model in (m for m in RESULT["models"] if m["key"]["province"] == "YT"):
        coverage = model["coverage"]
        assert coverage["contributing_utilities"] == [YUKON] and coverage["utilities_in_province"] == 1
        assert coverage["missing_utilities"] == [] and model["state"] == "single_source"
        assert [book["id"] for book in model["shared_rate_books"]] == ["yt-joint-yub-rate-book"]
        assert "they count once, as Yukon Energy" in model["method"]
    # Hydro, small diesel, large diesel and Old Crow are zones of one contributor (decision 66); below 2,500 kWh their
    # charges are equal, so the median of zones is the hydro cost.
    row = _rows(_level(_model(YT_RES), "typical"))[YUKON]
    assert [z["tariff_code"] for z in row["zone_costs"]] == ["1160", "1260", "1360", "1460"]
    assert {z["cost_without_tax"] for z in row["zone_costs"]} == {323.62}


def test_nwt_counts_ntpc_and_naka_once_each_as_the_median_of_their_zones():
    level = _level(_model(NT_RES), "typical")
    rows = _rows(level)
    assert set(rows) == {NTPC, NAKA} and level["without_tax"]["n"] == 2
    # NTPC at 1,000 kWh: $18 service charge + 1,000 kWh x (energy charge + riders), by zone (decision 65).
    ntpc = [18 + 1000 * (0.8896 + 0.0101 + 0.0042 + 0.0772),   # Thermal $999.10
            18 + 1000 * (0.3968 + 0.0112 + 0.0042 - 0.0033),   # Snare $426.90
            18 + 1000 * (0.7130 + 0.0101 + 0.0042 + 0.0772),   # Norman Wells $822.50
            18 + 1000 * (0.3242 + 0.0018 + 0.0042 + 0.1040),   # Taltson (Hay River) $452.20
            18 + 1000 * (0.3242 + 0.0110 + 0.0042 + 0.1040)]   # Taltson (Fort Smith/Fort Resolution) $461.40
    # Naka: base charges x (1 + Riders R, E and H) + Riders A and F per kWh, by zone.
    naka = [(18 + 1000 * 0.2372) * 1.08199 + 1000 * 0.1084,                        # Snare $384.52
            (18 + 1000 * 0.3242) * (1 + 0.419 + 0.08 + 0.05) + 1000 * (0.1871 - 0.0931),  # Taltson $624.07
            (18 + 1000 * 0.8415) * (1 + 0.267 + 0.021) - 1000 * 0.0275]              # Thermal $1,079.54
    assert [z["cost_without_tax"] for z in rows[NTPC]["zone_costs"]] == [round(c, 2) for c in ntpc]
    assert rows[NTPC]["cost_without_tax"] == round(statistics.median(ntpc), 2) == 461.40
    assert rows[NAKA]["cost_without_tax"] == round(statistics.median(naka), 2) == 624.07
    assert level["without_tax"]["median"] == round(statistics.median([statistics.median(ntpc),
                                                                     statistics.median(naka)]), 2) == 542.73
    assert _model(NT_RES)["coverage"]["multi_zone_utilities"] == [NAKA, NTPC]


def test_tpsp_first_block_is_all_in_and_month_weighted_in_the_after_subsidy_cost():
    # Decision 68: 1,000 kWh at 36.50 cents from September to March (7 months), 600 kWh from April to August (5),
    # cost = (7 x winter + 5 x summer) / 12. Decision 76: the first-block price is all-in: it replaces NTPC's energy
    # charge, its per-kWh riders (9.15 cents) and the Cost of Living credit; the kWh above the block pay 84.68 cents
    # (88.96 + 1.01 + 7.72 + 0.42 - 13.43) and the $18 service charge stays.
    winter = 18 + 1000 * 0.365                    # $383.00
    summer = 18 + 600 * 0.365 + 400 * 0.8468      # $575.72
    after = _cost(_record(NTPC, name=NTPC_THERMAL), 1000)["after_subsidy"]
    assert after["status"] == "ok" and after["applied"] == ["nt-ntpc-cost-of-living", "nt-tpsp-ntpc"]
    assert after["not_applied"] == []
    assert [(s["months"], s["cost_after_subsidy"]) for s in after["seasons"]] == [
        ([1, 2, 3, 9, 10, 11, 12], round(winter, 2)), ([4, 5, 6, 7, 8], round(summer, 2))]
    assert [round(winter, 2), round(summer, 2)] == [383.00, 575.72]
    assert after["cost"] == pytest.approx((7 * winter + 5 * summer) / 12) and round(after["cost"], 2) == 463.30
    # Norman Wells: the same all-in block; above it 68.10 cents (71.30 + 9.15 - 12.35).
    norman = _cost(_record(NTPC, name=f"Residential Service {DASH} Norman Wells Zone"), 1000)["after_subsidy"]
    assert [s["cost_after_subsidy"] for s in norman["seasons"]] == [383.00, round(18 + 600 * 0.365 + 400 * 0.6810, 2)]
    # Taltson (Hay River): NTPC publishes no TPSP price there, so the credit applies to every kWh.
    hay_river = _cost(_record(NTPC, name=f"Residential Service {DASH} Taltson Zone (Hay River)"), 1000)
    assert hay_river["after_subsidy"]["seasons"] is None
    assert round(hay_river["after_subsidy"]["cost"], 2) == round(hay_river["cost"] - 1000 * 0.1353, 2) == 316.90
    # Naka Taltson: the first block replaces the whole energy price (supply, fuel, Riders A and F and the percentage
    # riders' share), as Naka's July 2026 notice reconciles; the customer charge and its riders stay.
    energy = 0.3242 * 1.549 + 0.1871 - 0.0931
    customer = 18 * 1.549
    naka = _cost(_record(NAKA, "TALTSON-RES"), 1000)["after_subsidy"]
    assert naka["applied"] == ["nt-tpsp-naka"]
    assert naka["cost"] == pytest.approx((7 * (customer + 1000 * 0.365) + 5 * (customer + 600 * 0.365 + 400 * energy))
                                         / 12)
    after_level = _level(_model(NT_RES), "typical")["after_subsidy"]
    assert after_level["available"] and after_level["without_tax"]["n"] == 2
    rows = _rows(_level(_model(NT_RES), "typical"))
    assert rows[NAKA]["cost_after_subsidy"] == round(naka["cost"], 2)
    # NTPC low: Hay River 167.45, Fort Smith 173.80, Thermal and Norman Wells 200.50, Snare 222.45; Naka low: Thermal
    # 200.50, Snare 202.00, Taltson 210.38. Typical and high medians are NTPC Snare and Naka Taltson.
    medians = {lv["id"]: lv["after_subsidy"]["without_tax"]["median"] for lv in _model(NT_RES)["levels"]}
    assert medians == {"low": round((200.50 + 202.00) / 2, 2), "typical": 429.16, "high": 931.70}
    program = next(p for p in _model(NT_RES)["subsidies"]["programs"] if p["id"] == "nt-tpsp-ntpc")
    assert program["seasons"]["id"] == "NT_TPSP" and program["automatic"]["quote"].startswith(
        "Residential customers are automatically enrolled")
    assert "decision 76" in program["replaces"] and "riders and credits included" in _model(NT_RES)["method"]


def test_ntpc_snare_keeps_tpsp_omitted_and_disclosed():
    # Decision 77: NTPC's Snare zone (Behchoko, Dettah) stores no first-block price (NTPC's 'Your cost' price and stated
    # saving do not reconcile); TPSP is not applied there and the reviewed reason is disclosed.
    snare = _cost(_record(NTPC, name=f"Residential Service {DASH} Snare Zone"), 1000)
    after = snare["after_subsidy"]
    assert after["cost"] == pytest.approx(snare["cost"]) and after["applied"] == []
    skips = {skip["id"]: skip["reason"] for skip in after["not_applied"]}
    assert "owner decision 77" in skips["nt-tpsp-ntpc"]
    disclosed = [row for row in _model(NT_RES)["subsidies"]["not_applied"]
                 if row["id"] == "nt-tpsp-ntpc" and "owner decision 77" in row["reason"]]
    assert len(disclosed) == 1 and disclosed[0]["levels"] == ["low", "typical", "high"]


def test_naka_grep_reference_rates_replace_the_thermal_tariff_after_subsidies():
    # Decision 78: in Naka's Thermal zone the GREP reference rates ($18.00 a month, 83.94 cents/kWh, all-in) replace
    # Naka's own customer, supply and fuel charges and every rider (Rider A, Riders R and E); the TPSP first block at
    # 36.50 cents then replaces the reference energy price on the first-block kWh. The cost before subsidies stays
    # Naka's own tariff.
    record = _record(NAKA, "THERMAL-RES")
    typical = _cost(record, 1000)
    assert round(typical["cost"], 2) == round((18 + 1000 * 0.8415) * 1.288 - 1000 * 0.0275, 2) == 1079.54
    after = typical["after_subsidy"]
    assert after["applied"] == ["nt-naka-grep", "nt-tpsp-naka"] and after["not_applied"] == []
    winter, summer = 18 + 1000 * 0.365, 18 + 600 * 0.365 + 400 * 0.8394
    assert [s["cost_after_subsidy"] for s in after["seasons"]] == [round(winter, 2), round(summer, 2)] == [383.00, 572.76]
    assert after["cost"] == pytest.approx((7 * winter + 5 * summer) / 12)
    high = _cost(record, 2000)["after_subsidy"]
    assert high["seasons"][0]["cost_after_subsidy"] == round(18 + 1000 * 0.365 + 1000 * 0.8394, 2) == 1222.40
    # Thermal zone only: Taltson keeps Naka's own rates with the first block, and GREP is not named there.
    taltson = _cost(_record(NAKA, "TALTSON-RES"), 1000)["after_subsidy"]
    assert taltson["applied"] == ["nt-tpsp-naka"]
    assert "nt-naka-grep" not in {skip["id"] for skip in taltson["not_applied"]}
    program = next(p for p in _model(NT_RES)["subsidies"]["programs"] if p["id"] == "nt-naka-grep")
    assert program["treatment"] == "reference_rates" and program["status"] == "applied"
    assert program["applied_at"] == ["low", "typical", "high"] and "Thermal" in program["applies_to"]
    assert "Thermal Rate Zone" in program["automatic"]["quote"]
    # Without one of its reference rates the Thermal record is not computable after subsidies (fail closed).
    broken = copy.deepcopy(record)
    broken["components"] = [c for c in broken["components"] if c["component_name"] != "GNWT GREP Reference Energy Price"]
    result = _cost(broken, 1000)
    assert result["status"] == "ok" and result["after_subsidy"]["status"] == "not_computable"
    assert "GNWT GREP Reference Energy Price" in " ".join(result["after_subsidy"]["reasons"])


def test_an_unusable_subsidy_program_withholds_its_territory_after_subsidy_figure():
    # Fail closed: a malformed program (GREP without its reviewed reference components) is never applied, and the NWT
    # residential after-subsidy figure is withheld rather than computed without it; other territories are unaffected.
    config = copy.deepcopy(load_subsidies())
    del next(p for p in config["programs"] if p["id"] == "nt-naka-grep")["required_components"]
    result = _build(subsidies=config)
    nt = _model(NT_RES, result)
    assert nt["subsidies"]["after_subsidy"] is False and "program nt-naka-grep is not usable" in nt["subsidies"]["reason"]
    assert all(level["after_subsidy"]["available"] is False for level in nt["levels"])
    assert _model(YT_RES, result)["subsidies"]["after_subsidy"] is True


def test_a_first_block_that_differs_from_the_reviewed_convention_fails_closed():
    record = copy.deepcopy(_record(NTPC, name=NTPC_THERMAL))
    for comp in record["components"]:
        if comp["component_name"].endswith("(September 1 to March 31)"):
            comp["tier_threshold"] = 900.0
    result = _cost(record, 1000)
    assert result["status"] == "ok" and result["after_subsidy"]["status"] == "not_computable"
    assert "needs a new review" in " ".join(result["after_subsidy"]["reasons"])
    level = _level(_model(NT_RES, _build([record if r is _record(NTPC, name=NTPC_THERMAL) else r
                                          for r in RECORDS])), "typical")
    assert level["without_tax"]["n"] == 2 and level["after_subsidy"]["available"] is False
    assert level["after_subsidy"]["without_tax"]["median"] is None
    assert [row["utility"] for row in level["after_subsidy"]["not_computable"]] == [NTPC]
    assert _rows(level)[NTPC]["cost_after_subsidy"] is None


def test_nunavut_is_before_subsidy_only():
    model = _model(NU_RES)
    assert model["subsidies"]["after_subsidy"] is False and "decision 69" in model["subsidies"]["reason"]
    nesp = next(p for p in model["subsidies"]["programs"] if p["id"] == "nu-qulliq-nesp")
    assert nesp["status"] == "disclosed" and "700 kWh" in nesp["quote"] and "1000 kWh" in nesp["quote"]
    assert [row["id"] for row in model["subsidies"]["not_applied"]] == ["nu-qulliq-nesp"]
    for level in model["levels"]:
        after = level["after_subsidy"]
        assert after["available"] is False and after["without_tax"]["median"] is None
        assert all("cost_after_subsidy" not in row for row in level["utilities"])
    # The cost before subsidy keeps the $36 interim service charge and the full 74.94-cent energy rate.
    typical = _level(model, "typical")
    assert typical["without_tax"]["median"] == 36 + 1000 * 0.7494 == 785.40
    assert _cost(_record(QEC, "NG-RES"), 1000)["after_subsidy"]["status"] == "not_published"


def test_yukon_affordability_rate_relief_applies_only_inside_its_dates():
    # Decision 70: -25% of the base energy charges and Riders R, J and J1 on them for the first 1,500 kWh, from
    # October 1, 2026 to March 31, 2027 (the stored component dates); Rider F and the customer charge are excluded.
    record = _record(YUKON, "1160")
    inside = _cost(record, 1000, as_of="2026-11-24")
    eligible = 1000 * 0.1214 * (1 + YUKON_RIDERS)
    assert inside["after_subsidy"]["cost"] == pytest.approx(inside["cost"] - 0.25 * eligible)
    assert round(inside["after_subsidy"]["cost"], 2) == 253.66
    high = _cost(record, 2000)
    assert high["after_subsidy"]["cost"] == pytest.approx(
        high["cost"] - 0.25 * (1000 * 0.1214 + 500 * 0.1282) * (1 + YUKON_RIDERS))
    ended = _cost(record, 1000, as_of="2027-04-01")
    assert ended["cost"] == pytest.approx(inside["cost"]) and ended["after_subsidy"]["cost"] == pytest.approx(ended["cost"])
    assert ended["after_subsidy"]["applied"] == [] and ended["after_subsidy"]["not_applied"] == [
        {"id": "yt-affordability-rate-relief", "name": "Yukon Affordability Rate Relief",
         "reason": "expired before the as-of date (2026-10-01 to 2027-03-31)"}]
    for as_of, applied in (("2026-11-24", True), ("2027-04-01", False)):
        model = _model(YT_RES, _build(as_of=as_of))
        level = _level(model, "typical")
        assert level["after_subsidy"]["available"]
        assert (level["after_subsidy"]["without_tax"]["median"] < level["without_tax"]["median"]) is applied
        relief = model["subsidies"]["percentage_subsidies"][0]
        assert relief["in_force"] is applied and bool(relief["applied_at"]) is applied


def test_government_classes_stay_out_of_the_medians():
    crosswalk = load_crosswalk()
    government = [r for r in RECORDS if f" Government {DASH} " in r["name"]
                  or r["tariff_code"] in ("1180", "2170", "2180", "G-RES", "G-COM", "MT-COM")]
    assert len(government) == 8
    assert {match_record(r, crosswalk)["exclude"] for r in government} == {"government_rate"}
    assert match_record(_record(QEC, "MT-RES"), crosswalk)["exclude"] == "duplicate_variant"
    used = {record_id for m in RESULT["models"] for level in m["levels"] for row in level["utilities"]
            for record_id in row["records"]}
    assert used and not used & {r["id"] for r in government}


def test_with_tax_is_computed_on_the_cost_before_subsidies_only():
    for model in (m for m in RESULT["models"]):
        for level in model["levels"]:
            assert [line["name"] for line in level["with_tax"]["lines"]] == ["GST"]
            assert level["with_tax"]["median"] == pytest.approx(level["without_tax"]["median"] * 1.05, abs=0.01)
            after = level["after_subsidy"]
            assert after["tax_basis"] == "before_tax_only" and "with_tax" not in after
            assert all("cost_after_subsidy_with_tax" not in row for row in level["utilities"])
        assert "before tax only" in model["subsidies"]["tax_note"]


def test_interim_rates_of_qulliq_and_naka_are_labelled():
    for model_id, utility in ((NU_RES, QEC), (NT_RES, NAKA), ("NT|electricity|commercial|demand|commercial_small", NAKA)):
        model = _model(model_id)
        assert [entry["utility"] for entry in model["interim"]] == [utility]
        assert any(w.startswith(f"Interim rates included: {utility}") for w in model["warnings"])
        for level in model["levels"]:
            assert {u for u, row in _rows(level).items() if row.get("interim")} == {utility}
        briefs = next(u for u in model["utilities"] if u["utility"] == utility)["records"]
        assert all(brief["interim"] is True for brief in briefs)
    assert all("interim" not in m for m in RESULT["models"] if m["key"]["province"] == "YT")
    # The label follows the record's own notes: final rates drop it without a configuration edit.
    final = copy.deepcopy(_record(QEC, "NG-RES"))
    final["notes"] = "Provenance: live_parsed. Final rates approved by the Minister."
    model = _model(NU_RES, _build([final if r is _record(QEC, "NG-RES") else r for r in RECORDS]))
    assert "interim" not in model


def test_small_commercial_maps_non_government_general_service_at_s1_and_s2():
    expected = {"YT": {YUKON}, "NT": {NTPC, NAKA}, "NU": {QEC}}
    reasons = {}
    for province, utilities in expected.items():
        model = _model(f"{province}|electricity|commercial|demand|commercial_small")
        assert [level["id"] for level in model["levels"]] == ["s1", "s2"]
        assert model["subsidies"]["after_subsidy"] is False and model["subsidies"]["decided"] is None
        reasons[province] = model["subsidies"]["reason"]
        assert reasons[province] in model["method"]
        for level in model["levels"]:
            assert set(_rows(level)) == utilities
            assert level["after_subsidy"]["reason"] == reasons[province]
    # Sourced facts, not an owner decision: no automatic subsidy with a published general-service value.
    assert "'Residential - Non Government customer class only." in reasons["YT"]
    assert "automatically applies to all eligible residential and commercial customers" in reasons["NT"]
    assert "publishes no credit value for general service" in reasons["NT"] and "Thermal zone" in reasons["NT"]
    assert "non-government residential customers" in reasons["NU"]
    assert not any("decision 67" in reason for reason in reasons.values())
    nu = _model("NU|electricity|commercial|demand|commercial_small")
    # Qulliq NG-COM: $16 per kW of demand + 62.08 cents per kWh.
    assert [_level(nu, lv)["without_tax"]["median"] for lv in ("s1", "s2")] == [
        round(14 * 16 + 2000 * 0.6208, 2), round(40 * 16 + 10000 * 0.6208, 2)]
    yt = _model("YT|electricity|commercial|demand|commercial_small")
    # Rate 2160: (14 kW x $7.39 + 2,000 kWh x 10 cents) x (1 + Riders R, J, J1) + 2,000 kWh x 1 cent (Rider F).
    assert _level(yt, "s1")["without_tax"]["median"] == round((14 * 7.39 + 2000 * 0.10) * (1 + YUKON_RIDERS) + 20, 2)
    crosswalk = load_crosswalk()
    assert match_record(_record(NAKA, "TALTSON-LGS"), crosswalk)["exclude"] == "territory_planned_later"
    heating = next(r for r in RECORDS if r["name"].startswith("Interruptible Energy For Heating"))
    assert match_record(heating, crosswalk)["exclude"] == "conditional_only"
    assert not any(m["key"]["size_band"] in ("commercial_medium", "commercial_large", "commercial_xlarge")
                   for m in RESULT["models"])
