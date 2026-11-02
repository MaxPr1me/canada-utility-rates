"""User decisions of 2026-10-30 for the representative models: fixed charges published as phase or amperage variants
are priced for the reference customer of the level (usage_levels.json 'fixed_charge_variants'), and blocks printed
'per Billing Period' count per month where the utility's billing terms confirm monthly billing (block_periods.json).

Synthetic records and frozen fixtures only (rm_records_b14.json, rm_records_b12.json, rm_records_sample.json,
rm_engine_sample.json, manitoba_hydro.json), never the live export.
"""
import copy
import html
import json
import re
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlparse

import pytest

from pipeline import representative_models as rm
from pipeline.representative_models import (build_models, load_block_periods, load_crosswalk, load_rates, load_taxes,
                                            load_usage_levels, record_monthly_cost)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
BLOCK_PERIODS = Path(rm.BLOCK_PERIODS_PATH)
AS_OF = "2026-10-16"
PROVINCES = ("ON", "AB", "BC", "MB", "NB", "NL", "NS", "PE", "QC", "SK")
NL_RES = "NL|electricity|residential|flat|-"
NL_SMALL = "NL|electricity|commercial|demand|commercial_small"
HOME, SINGLE, THREE = "home-single-phase-200a", "small-business-single-phase-10kw", "small-business-three-phase-25kw"
NOT_EXCEEDING = "Basic Customer Charge (Not Exceeding 200 Amp Service)"


def _c(ctype, value, unit, name, **extra):
    comp = {"component_type": ctype, "component_name": name, "charge_value": value, "charge_unit": unit,
            "notes": "Provenance: live_parsed. "}
    comp.update(extra)
    return comp


def _alt(value, qualifier, stem="Basic Customer Charge"):
    """A fixed charge stored as a marked alternative (the NL Hydro and Manitoba Hydro shape)."""
    return _c("fixed", value, "$/month", f"{stem} ({qualifier})", sub_component=qualifier,
              notes=f"Provenance: live_parsed. Alternative: applies only to '{qualifier}' service. Mutually exclusive "
                    "with the other rows; one row is billed per service, not all rows together.")


def _rec(components, utility="Synthetic Power", code="X", province="NL", cls="commercial", rid=1, structure="demand"):
    return {"id": rid, "utility_name": utility, "province": province, "utility_type": "electricity",
            "name": f"{utility} {code}", "tariff_code": code, "customer_class": cls, "rate_structure": structure,
            "effective_date": "2026-01-01", "provenance": "live", "components": components}


ENERGY = _c("energy", 0.10, "$/kWh", "Energy Charge")
PHASES = [_c("fixed", 14.0, "$/month", "Basic Customer Charge (Unmetered)"),
          _c("fixed", 22.0, "$/month", "Basic Customer Charge (Single Phase)"),
          _c("fixed", 34.0, "$/month", "Basic Customer Charge (Three phase)")]
PHASE_ALTERNATIVES = [_alt(14.0, "Unmetered"), _alt(22.0, "Single Phase"), _alt(34.0, "Three Phase")]
AMPS = [_c("fixed", 17.0, "$/month", NOT_EXCEEDING),
        _c("fixed", 22.0, "$/month", "Basic Customer Charge (Exceeding 200 Amp Service)")]


def _cost(record, kwh, kw=None, sector="commercial_small", level=None, usage_levels=None, **kwargs):
    return record_monthly_cost(record, kwh, kw, sector=sector, usage_levels=usage_levels or load_usage_levels(),
                               as_of=AS_OF, level=level, **kwargs)


def _items(result):
    return {item["component"]: item for item in result["items"]}


def _build(records, provinces=("NL",), usage_levels=None, **kwargs):
    return build_models(records, load_crosswalk(), usage_levels or load_usage_levels(), load_taxes(),
                        provinces=provinces, as_of=AS_OF, market_document=None, **kwargs)


def _model(result, model_id):
    return next(m for m in result["models"] if m["id"] == model_id)


def _level(model, level_id):
    return next(lv for lv in model["levels"] if lv["id"] == level_id)


def _without_rules(usage_levels):
    bare = copy.deepcopy(usage_levels)
    bare.pop("fixed_charge_variants", None)
    bare.pop("fixed_charge_variants_basis", None)
    return bare


def _b14(record_id):
    return next(r for r in load_rates(FIXTURES / "rm_records_b14.json") if r["id"] == record_id)


@pytest.mark.parametrize(("kwh", "kw", "level", "sector", "expected"), [
    (2000, 10, "s1", "commercial_small", 462.17),
    (2000, 20, "s1", "commercial_small", 462.17),
    (2000, 25, "s2", "commercial_small", 529.32),
    (8000, 25, "s2", "commercial_small", 1617.12),
    (40000, 100, "m1", "commercial_medium", 7225.97),
    (500000, 1000, "l1", "commercial_large", 85460.97),
])
def test_maritime_published_free_demand_block_prices_only_balance(kwh, kw, level, sector, expected):
    from scrapers.utilities.maritime_electric import MaritimeElectricScraper
    from scrapers.utils.parsing import DocumentPage

    fixture = json.loads((FIXTURES / "maritime_electric.json").read_text(encoding="utf-8"))
    pages = [DocumentPage(p["page_number"], p["text"]) for p in fixture["pages"]]
    records = MaritimeElectricScraper()._parse_pages(pages, fixture["url"])
    tariff = next(r for r in records if r.tariff_code == "232")
    record = _rec([asdict(c) for c in tariff.components], utility="Maritime Electric",
                  code="232", province="PE")
    result = _cost(record, kwh, kw, level=level, sector=sector, block_periods=load_block_periods())
    assert result["status"] == "ok"
    assert result["cost"] == pytest.approx(expected)


@pytest.mark.parametrize("fixed, unchosen", [(PHASES, "variant_not_selected"), (PHASE_ALTERNATIVES, "alternative")])
def test_small_business_levels_pick_single_phase_at_10_kw_and_three_phase_at_25_kw(fixed, unchosen):
    record = _rec(fixed + [ENERGY])
    for level, kwh, kw, value, rule, picked in (("s1", 2000, 10, 22.0, SINGLE, "Single Phase"),
                                                ("s2", 8000, 25, 34.0, THREE, "Three")):
        res = _cost(record, kwh, kw, level=level)
        assert res["status"] == "ok" and res["cost"] == pytest.approx(value + 0.10 * kwh), level
        fixed_items = {name: item for name, item in _items(res).items() if item["type"] == "fixed"}
        chosen = [item for name, item in fixed_items.items() if picked.lower() in name.lower()]
        assert len(chosen) == 1 and chosen[0]["status"] == "included" and chosen[0]["amount"] == pytest.approx(value)
        assert chosen[0]["reason"] == "fixed_charge_variant:" + rule
        others = [item for item in fixed_items.values() if item is not chosen[0]]
        assert len(others) == 2 and all(i["status"] == "excluded" and i["reason"] == unchosen and "amount" not in i
                                        for i in others)


def test_homes_price_the_variant_covering_a_200_amp_single_phase_service():
    unmarked = _rec(AMPS + [ENERGY], cls="residential", structure="flat")
    marked = _rec([_alt(17.0, "Not Exceeding 200 Amp Service"), _alt(22.0, "Exceeding 200 Amp Service"), ENERGY],
                  cls="residential", structure="flat")
    for record in (unmarked, marked):
        for level, kwh in (("low", 500), ("typical", 1000), ("high", 2000)):
            res = _cost(record, kwh, sector="residential", level=level)
            assert res["status"] == "ok" and res["cost"] == pytest.approx(17.0 + 0.10 * kwh)
            assert _items(res)[NOT_EXCEEDING]["reason"] == "fixed_charge_variant:" + HOME
            assert "amount" not in _items(res)["Basic Customer Charge (Exceeding 200 Amp Service)"]
    single = _rec([_c("fixed", 9.0, "$/month", "Basic Charge (single phase)"),
                   _c("fixed", 15.0, "$/month", "Basic Charge (three phase)"), ENERGY], cls="residential")
    assert _cost(single, 1000, sector="residential", level="typical")["cost"] == pytest.approx(109.0)


def test_zero_or_two_matching_variants_and_levels_without_a_rule_stay_not_computable():
    polyphase = _rec([PHASES[0], _c("fixed", 30.0, "$/month", "Basic Customer Charge (Polyphase)"), ENERGY])
    res = _cost(polyphase, 2000, 10, level="s1")
    assert res["status"] == "not_computable" and res["reasons"] == [
        "fixed charge published as variants without a selection rule: Basic Customer Charge (Unmetered); "
        "Basic Customer Charge (Polyphase)"]
    twice = _rec([_c("fixed", 22.0, "$/month", "Basic Charge (single phase)"),
                  _c("fixed", 23.0, "$/month", "Basic Charge (Single-Phase)"), ENERGY])
    assert _cost(twice, 2000, 10, level="s1")["status"] == "not_computable"
    unpriced = _rec([_alt(None, "Single Phase"), _alt(34.0, "Three Phase"), ENERGY])
    assert _cost(unpriced, 2000, 10, level="s1")["status"] == "not_computable"
    assert _cost(unpriced, 8000, 25, level="s2")["status"] == "ok"
    record = _rec(PHASES + [ENERGY])
    baseline = _cost(record, 2000, 10)
    assert baseline["status"] == "not_computable" and len(baseline["reasons"]) == 1
    for kwargs in ({"level": "m1", "sector": "commercial_medium"}, {"level": "l1", "sector": "commercial_large"},
                   {"level": "typical"}, {"level": "s1", "sector": "residential"}):
        assert _cost(record, 2000, 10, **kwargs)["reasons"] == baseline["reasons"], kwargs
    alternatives = _cost(_rec(PHASE_ALTERNATIVES + [ENERGY]), 40000, 100, sector="commercial_medium", level="m1")
    assert [r.split(":")[0] for r in alternatives["reasons"]] == ["charge published only as conditional alternatives"] * 3
    meter = _rec([_c("demand", 6.0, "$/kW", "Distribution Rate (Interval Meter)", sub_component="a",
                     notes="Provenance: live_parsed. Alternative: interval meter"),
                  _c("demand", 5.0, "$/kW", "Distribution Rate (Thermal Meter)", sub_component="b",
                     notes="Provenance: live_parsed. Alternative: thermal meter"), ENERGY])
    assert _cost(meter, 2000, 10, level="s1")["status"] == "not_computable"


def test_records_without_variants_are_unchanged_by_the_rules():
    usage, bare = load_usage_levels(), _without_rules(load_usage_levels())
    plain = _rec([_c("fixed", 20.0, "$/month", "Basic Charge"), _c("fixed", 3.0, "$/month", "Meter Charge (single phase)"),
                  ENERGY])
    for level in (None, "s1", "s2"):
        assert _cost(plain, 2000, 10, level=level) == _cost(plain, 2000, 10, usage_levels=bare)
    for name, expected in ((("rm_records_sample.json", "rm_records_b12.json"), set()), (("rm_records_b14.json",), {NL_RES})):
        records = [record for part in name for record in load_rates(FIXTURES / part)]
        with_rules = _build(records, provinces=PROVINCES, usage_levels=usage)
        without = _build(records, provinces=PROVINCES, usage_levels=bare)
        assert [m["id"] for m in with_rules["models"]] == [m["id"] for m in without["models"]]
        assert {m["id"] for m, n in zip(with_rules["models"], without["models"]) if m != n} == expected, name
    fx = json.loads((FIXTURES / "rm_engine_sample.json").read_text(encoding="utf-8"))
    rules = {k: usage[k] for k in ("fixed_charge_variants", "fixed_charge_variants_basis")}
    ontario = build_models(fx, fx["crosswalk"], {**fx["usage_levels"], **rules}, fx["taxes"], as_of="2026-10-09")
    reference = build_models(fx, fx["crosswalk"], fx["usage_levels"], fx["taxes"], as_of="2026-10-09")
    assert ontario["models"] == reference["models"]
    typical = _level(_model(ontario, "ON|electricity|residential|tou|-"), "typical")
    assert (typical["without_tax"]["median"], typical["with_tax"]["median"]) == (198.09, 177.29)


def test_nl_residential_is_modeled_once_newfoundland_power_prices_its_200_amp_charge():
    nf_power = _b14(50)
    assert _cost(nf_power, 1000, sector="residential")["status"] == "not_computable"
    res = _cost(nf_power, 1000, sector="residential", level="typical")
    assert res["status"] == "ok" and _items(res)[NOT_EXCEEDING]["amount"] == pytest.approx(17.36)
    assert _items(res)["Basic Customer Charge (Exceeding 200 Amp Service)"]["reason"] == "variant_not_selected"
    stripped = {**nf_power, "components": [c for c in nf_power["components"]
                                           if not c["component_name"].startswith("Basic Customer Charge (")]}
    assert res["cost"] == pytest.approx(_cost(stripped, 1000, sector="residential")["cost"] + 17.36)
    nl_hydro = _rec([_c("fixed", 20.0, "$/month", "Basic Customer Charge"), _c("energy", 0.10, "$/kWh", "Energy")],
                    utility="NL Hydro", code="1.1L", cls="residential", rid=9001, structure="flat")
    model = _model(_build([nf_power, nl_hydro]), NL_RES)
    assert model["state"] == "modeled" and model["coverage"]["contributing_utilities"] == ["NL Hydro", "Newfoundland Power"]
    assert model["required_contributors"][0]["withheld_at"] == []
    for level in model["levels"]:
        assert "withheld" not in level and level["without_tax"]["n"] == 2
    row = next(r for r in _level(model, "typical")["utilities"] if r["utility"] == "Newfoundland Power")
    assert row["cost_without_tax"] == round(res["cost"], 2)
    assert row["fixed_charge_variants"] == [{"record_id": 50, "rule": HOME, "component": NOT_EXCEEDING}]
    assert model["fixed_charge_variants"] == [{
        "id": HOME, "reference": "single-phase service of 200 A", "decided": "user 2026-10-30",
        "levels": ["low", "typical", "high"], "components": [NOT_EXCEEDING], "utilities": ["Newfoundland Power"]}]
    assert ("home-single-phase-200a (single-phase service of 200 A; decided user 2026-10-30) at low, typical, high: "
            + NOT_EXCEEDING + " (Newfoundland Power)") in model["method"]
    counted = {e["reason"]: e for e in model["exclusions"] if e["scope"] == "component"}
    assert counted["variant_not_selected"]["examples"] == ["Basic Customer Charge (Exceeding 200 Amp Service)"]
    only_200a = {**nf_power, "components": [c for c in nf_power["components"]
                                            if c["component_name"] != "Basic Customer Charge (Exceeding 200 Amp Service)"]}
    alone, plain = _model(_build([nf_power]), NL_RES), _model(_build([only_200a]), NL_RES)
    assert alone["state"] == plain["state"] == "single_source" and alone["buckets"] == plain["buckets"]
    assert [lv["without_tax"] for lv in alone["levels"]] == [lv["without_tax"] for lv in plain["levels"]]


def test_variants_that_differ_by_level_stay_out_of_the_component_buckets():
    record = _rec(PHASES + [ENERGY], utility="Newfoundland Power", code="2.1", rid=51)
    model = _model(_build([record]), NL_SMALL)
    assert model["state"] == "single_source"
    assert [(lv["id"], lv["without_tax"]["median"]) for lv in model["levels"]] == [("s1", 222.0), ("s2", 834.0)]
    assert [e["id"] for e in model["fixed_charge_variants"]] == [SINGLE, THREE]
    assert not [b for b in model["buckets"] if b["bucket"] == "fixed"]
    assert "component buckets include a variant only when the same one applies at every level" in model["method"]


def test_manitoba_general_service_small_phase_alternatives_from_the_frozen_page():
    from scrapers.utilities.manitoba_hydro import ManitobaHydroScraper

    lines = json.loads((FIXTURES / "manitoba_hydro.json").read_text(encoding="utf-8"))["pages"]["commercial"]["lines"]
    page = "<html><body>" + "".join(f"<p>{html.escape(line)}</p>" for line in lines) + "</body></html>"
    parsed = {r.tariff_name: r for r in ManitobaHydroScraper()._parse_commercial(page)}
    small = parsed["General Service Small (Non-Demand)"]
    record = _rec([asdict(c) for c in small.components], utility="Manitoba Hydro", code=None, province="MB",
                  structure="tiered")
    record["name"] = small.tariff_name
    periods = load_block_periods()
    for level, kwh, kw, value, rule in (("s1", 2000, 10, 21.57, SINGLE), ("s2", 8000, 25, 35.04, THREE)):
        res = _cost(record, kwh, kw, level=level, block_periods=periods)
        assert res["status"] == "ok", res["reasons"]
        chosen = [i for i in res["items"] if (i.get("reason") or "").startswith("fixed_charge_variant:")]
        assert [(i["value"], i["reason"]) for i in chosen] == [(value, "fixed_charge_variant:" + rule)]
        assert res["cost"] == pytest.approx(sum(i["amount"] for i in res["items"] if "amount" in i))
    assert _cost(record, 40000, 100, sector="commercial_medium", level="m1", block_periods=periods)["status"] == \
        "not_computable"


def test_billing_period_entries_cite_monthly_billing_terms():
    entries = {e["id"]: e for e in json.loads(BLOCK_PERIODS.read_text(encoding="utf-8"))["entries"]}
    confirmed = {"nb-power-gs1": "www.nbpower.com", "maritime-electric-residential": "www.maritimeelectric.com",
                 "maritime-electric-general-service": "www.maritimeelectric.com"}
    for entry_id, host in confirmed.items():
        entry = entries[entry_id]
        assert entry["threshold_period"] == "month" and entry["reviewed"] == "2026-10-30", entry_id
        assert urlparse(entry["source_url"]).scheme == "https" and urlparse(entry["source_url"]).netloc == host
        assert re.search(r"28 to 33 days|30 days", entry["quote"]) and "User decision 2026-10-30" in entry["note"]
        assert "per Billing Period" in entry["location"]
    seasonal = entries["maritime-electric-seasonal-options"]
    assert seasonal["threshold_period"] is None and seasonal["match"] == {"tariff_code_regex": "^(?:133|233)$"}
    assert entries["mb-gs-seasonal"]["threshold_period"] is None
    usable = {e["id"] for e in load_block_periods()["entries"]}
    assert set(confirmed) | {"maritime-electric-seasonal-options"} <= usable
    blocks = [_c("energy", 0.18, "$/kWh", "First block", tier_number=1, tier_threshold=5000.0, tier_unit="kWh"),
              _c("energy", 0.13, "$/kWh", "Balance", tier_number=2, tier_threshold=5000.0, tier_unit="kWh")]
    periods = load_block_periods()
    for utility, code, ok in (("NB Power", "GS1", True), ("Maritime Electric", "232", True),
                              ("Maritime Electric", "233", False)):
        res = _cost(_rec(blocks, utility=utility, code=code), 8000, 25, level="s2", block_periods=periods)
        assert (res["status"] == "ok") is ok, (utility, code)
        if ok:
            assert res["cost"] == pytest.approx(5000 * 0.18 + 3000 * 0.13)


def test_rules_and_method_text_are_disclosed():
    result = _build([_b14(50)])
    assumptions = result["assumptions"]
    assert [r["id"] for r in assumptions["fixed_charge_variants"]] == [HOME, SINGLE, THREE]
    assert all(r["decided"] == "user 2026-10-30" for r in assumptions["fixed_charge_variants"])
    assert "single-phase service of 200 A" in assumptions["fixed_charge_variants_basis"]
    rules = " ".join(assumptions["component_rules"])
    assert "'fixed_charge_variants' rule" in rules and "fixed_charge_variant:<id>" in rules
    assert "without a selection rule" not in rules
    usage = load_usage_levels()
    assert [(r["sectors"], r["levels"]) for r in usage["fixed_charge_variants"]] == [
        (["residential"], ["low", "typical", "high"]), (["commercial_small"], ["s1"]), (["commercial_small"], ["s2"])]
    levels = {sector: [lv["id"] for lv in usage["electricity"][sector]] for sector in ("residential", "commercial_small")}
    assert levels == {"residential": ["low", "typical", "high"], "commercial_small": ["s1", "s2"]}
    assert [(lv["kwh"], lv["kw"]) for lv in usage["electricity"]["commercial_small"]] == [(2000, 10), (8000, 25)]
    assert rm.fixed_charge_variant_rules(usage, "gas", "residential") == []
    assert rm.fixed_charge_variant_rules({"fixed_charge_variants": [{"id": "x", "sectors": ["residential"],
                                                                      "levels": ["low"], "match": {"notes_regex": "."}}]},
                                         "electricity", "residential") == []
