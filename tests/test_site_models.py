"""Phase 7F UI contract: the Representative Models view (site/js/models.js) and the engine output it reads.

Models are built from frozen fixtures with the engine, never from site/data/representative_models.json, so the
tests do not depend on the live export.
"""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from pipeline.representative_models import build_models, load_crosswalk, load_rates, load_taxes, load_usage_levels

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SITE = ROOT / "site"
AS_OF = "2026-10-09"
STATES = {"modeled", "single_source", "market_energy_pending", "not_computable"}
RES_TOU = "ON|electricity|residential|tou|-"
MEDIUM = "ON|electricity|commercial|demand|commercial_medium"
MARKET_NOTE = ("Provenance: live_parsed. The hourly Ontario Electricity Market Price replaced the HOEP on May 1, 2025. "
               "Conditional: Class A customers instead pay Global Adjustment by their peak demand factor.")

# Fields site/js/models.js reads (keep in sync with that file).
TOP_FIELDS = {"method_version": str, "as_of": str, "generated_at": str, "models": list}
MODEL_FIELDS = {"id": str, "key": dict, "label": str, "state": str, "cost_basis": str, "coverage": dict,
                "levels": list, "exclusions": list, "warnings": list, "method": str}
KEY_FIELDS = ("province", "fuel", "sector", "structure", "size_band")
COVERAGE_FIELDS = {"utilities_in_province": int, "utilities_mapped": int, "utilities_contributing": int,
                   "contributing_utilities": list, "missing_utilities": list, "records_mapped": int,
                   "records_used": int, "effective_dates": list}
LEVEL_FIELDS = ("id", "kwh", "kw", "without_tax", "with_tax", "closest_utility", "outliers", "utilities")
STAT_FIELDS = ("median", "n", "min", "p25", "p75", "max")
TAX_LINE_FIELDS = ("name", "kind", "rate", "base", "median_amount", "source_url")
NOT_APPLIED_FIELDS = ("name", "reason")
CLOSEST_FIELDS = ("utility", "deviation_pct")
OUTLIER_FIELDS = ("utility", "deviation_pct")
LEVEL_UTILITY_FIELDS = ("utility", "cost_without_tax", "cost_with_tax")
EXCLUSION_TEXT_FIELDS = {"component": ("reason", "text", "count", "examples"), "record": ("utility", "reason"),
                         "utility": ("utility", "reason")}


def _engine_fixture():
    return json.loads((FIXTURES / "rm_engine_sample.json").read_text(encoding="utf-8"))


def _component(ctype, value, unit, name, **extra):
    comp = {"component_type": ctype, "component_name": name, "charge_value": value, "charge_unit": unit,
            "notes": "Provenance: live_parsed. "}
    comp.update(extra)
    return comp


def _tou(off=0.098, mid=0.157, on=0.203):
    return [_component("energy", off, "$/kWh", "Off-Peak Energy", tou_period="off-peak"),
            _component("energy", mid, "$/kWh", "Mid-Peak Energy", tou_period="mid-peak"),
            _component("energy", on, "$/kWh", "On-Peak Energy", tou_period="on-peak")]


def _record(components, utility="Only Hydro", code="TOU-R", cls="residential", structure="tou", lo=None, hi=None,
            rid=1):
    return {"id": rid, "utility_name": utility, "province": "ON", "utility_type": "electricity",
            "name": f"{utility} {code}", "tariff_code": code, "customer_class": cls, "rate_structure": structure,
            "demand_min_kw": lo, "demand_max_kw": hi, "effective_date": "2026-01-01", "provenance": "live",
            "source_url": "https://example.org/tariff.pdf", "components": components}


def _demand(utility, rid, fixed):
    comps = [_component("fixed", fixed, "$/month", "fixed $/month"),
             _component("demand", 5.0, "$/kW", "demand $/kW", sub_component="distribution_volumetric"),
             _component("energy", None, "$/kWh", "Market Energy", market_reference="IESO OEMP + GA", notes=MARKET_NOTE)]
    return _record(comps, utility=utility, code="GS 50-4,999 kW", cls="commercial", structure="demand", lo=50, hi=5000,
                   rid=rid)


def _synthetic(records):
    fx = _engine_fixture()
    return build_models(records, fx["crosswalk"], fx["usage_levels"], fx["taxes"], as_of=AS_OF)


def _model(result, model_id):
    return next(m for m in result["models"] if m["id"] == model_id)


def _builds():
    records = load_rates(FIXTURES / "rm_records_sample.json") + load_rates(FIXTURES / "rm_records_b12.json")
    fx = _engine_fixture()
    return {
        "export_like": build_models(records, load_crosswalk(), load_usage_levels(), load_taxes(), as_of=AS_OF),
        "engine_fixture": build_models(fx["records"], fx["crosswalk"], fx["usage_levels"], fx["taxes"], as_of=AS_OF),
        "single_source": _synthetic([_record(_tou() + [_component("fixed", 30.0, "$/month", "Service Charge")])]),
        "not_computable": _synthetic([_record(_tou()[:2])]),
        "market_pending": _synthetic([_demand("A Hydro", 1, 100.0), _demand("B Hydro", 2, 300.0)]),
    }


BUILDS = _builds()


def _assert_fields(obj, fields, where):
    missing = [f for f in fields if f not in obj]
    assert not missing, f"{where}: missing {missing}"


def _assert_model_contract(model, where):
    for field, kind in MODEL_FIELDS.items():
        assert isinstance(model.get(field), kind), f"{where}: {field} should be {kind.__name__}"
    assert model["state"] in STATES, f"{where}: unknown state {model['state']!r} has no badge text"
    _assert_fields(model["key"], KEY_FIELDS, f"{where} key")
    assert all(isinstance(model["key"][f], str) and model["key"][f] for f in KEY_FIELDS[:4]), where
    assert model["key"]["size_band"] is None or isinstance(model["key"]["size_band"], str), where
    # models.js reads the sector and structure names from "<province fuel> - <sector> - <structure>".
    assert len(model["label"].split(" - ")) == 3, f"{where}: label {model['label']!r}"
    for field, kind in COVERAGE_FIELDS.items():
        assert isinstance(model["coverage"].get(field), kind), f"{where}: coverage.{field}"
    for exclusion in model["exclusions"]:
        _assert_fields(exclusion, ("scope",) + EXCLUSION_TEXT_FIELDS.get(exclusion["scope"], ("reason",)),
                       f"{where} exclusion")
    assert all(isinstance(w, str) for w in model["warnings"]), where
    for level in model["levels"]:
        _assert_level_contract(level, f"{where} level {level.get('id')}")


def _assert_level_contract(level, where):
    _assert_fields(level, LEVEL_FIELDS, where)
    assert isinstance(level["kwh"], (int, float)) and (level["kw"] is None or isinstance(level["kw"], (int, float)))
    for side in ("without_tax", "with_tax"):
        _assert_fields(level[side], STAT_FIELDS, f"{where} {side}")
    _assert_fields(level["with_tax"], ("lines", "not_applied"), f"{where} with_tax")
    for line in level["with_tax"]["lines"]:
        _assert_fields(line, TAX_LINE_FIELDS, f"{where} tax line")
        assert line["kind"] in ("sales_tax", "rebate"), where
    for line in level["with_tax"]["not_applied"]:
        _assert_fields(line, NOT_APPLIED_FIELDS, f"{where} not_applied")
    if level["closest_utility"] is not None:
        _assert_fields(level["closest_utility"], CLOSEST_FIELDS, f"{where} closest_utility")
    for outlier in level["outliers"]:
        _assert_fields(outlier, OUTLIER_FIELDS, f"{where} outlier")
    for row in level["utilities"]:
        _assert_fields(row, LEVEL_UTILITY_FIELDS, f"{where} utility row")


@pytest.mark.parametrize("name", sorted(BUILDS))
def test_rm7f_every_field_models_js_reads_exists(name):
    result = BUILDS[name]
    for field, kind in TOP_FIELDS.items():
        assert isinstance(result.get(field), kind), f"{name}: {field}"
    assert result["method_version"] and result["models"], name
    for model in result["models"]:
        _assert_model_contract(model, f"{name} {model['id']}")


def test_rm7f_fixture_builds_cover_every_state_and_an_empty_level_list():
    states = {model["state"] for result in BUILDS.values() for model in result["models"]}
    assert states == STATES
    assert any(not model["levels"] for result in BUILDS.values() for model in result["models"])
    assert _model(BUILDS["single_source"], RES_TOU)["state"] == "single_source"
    assert _model(BUILDS["market_pending"], MEDIUM)["state"] == "market_energy_pending"


def test_rm7f_not_computable_levels_have_null_statistics_and_listed_reasons():
    model = _model(BUILDS["not_computable"], RES_TOU)
    assert model["state"] == "not_computable" and model["levels"]
    for level in model["levels"]:
        assert level["without_tax"]["median"] is None and level["closest_utility"] is None
    assert [e["reason"] for e in model["exclusions"] if e["scope"] in ("record", "utility")]


@pytest.mark.parametrize("name", ["export_like", "engine_fixture"])
def test_rm7f_default_selection_exists_with_a_typical_level(name):
    model = _model(BUILDS[name], RES_TOU)
    assert model["key"] == {"province": "ON", "fuel": "electricity", "sector": "residential", "structure": "tou",
                            "size_band": None}
    typical = next(level for level in model["levels"] if level["id"] == "typical")
    assert typical["kwh"] == 1000 and typical["kw"] is None


def test_rm7f_typical_level_explains_a_with_tax_median_below_the_without_tax_median():
    # The engine fixture carries full components; the 7A coverage fixtures do not, so their costs are zero.
    typical = next(level for level in _model(BUILDS["engine_fixture"], RES_TOU)["levels"] if level["id"] == "typical")
    assert typical["with_tax"]["median"] < typical["without_tax"]["median"]
    assert any(line["kind"] == "rebate" for line in typical["with_tax"]["lines"])


class _Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def _index():
    text = (SITE / "index.html").read_text(encoding="utf-8")
    parser = _Tags()
    parser.feed(text)
    return text, parser.tags


def test_rm7f_index_html_wires_the_tab_panel_and_script():
    text, tags = _index()
    views = [attrs["data-view"] for tag, attrs in tags if "nav-tab" in attrs.get("class", "").split()]
    assert views == ["rates", "market", "models", "compare"]
    panel = next(attrs for tag, attrs in tags if attrs.get("id") == "view-models")
    assert set(panel["class"].split()) == {"view-panel", "hidden"}
    ids = {attrs.get("id"): (tag, attrs) for tag, attrs in tags if attrs.get("id")}
    for field in ("province", "fuel", "segment", "structure"):
        assert ids[f"models-{field}"][0] == "select"
        assert any(tag == "label" and attrs.get("for") == f"models-{field}" for tag, attrs in tags)
    assert ids["models-notice"][1].get("role") == "status" and "estimated-banner" in ids["models-notice"][1]["class"]
    for required in ("models-asof", "models-loading", "models-content", "models-title", "models-badge",
                     "models-reasons", "models-table-wrap", "models-notes"):
        assert required in ids, required
    assert "They are not a rate anyone is billed." in text
    scripts = [attrs["src"] for tag, attrs in tags if tag == "script" and attrs.get("src")]
    assert scripts.index("js/models.js") == scripts.index("js/app.js") + 1


def test_rm7f_models_js_reads_the_contract_fields_and_never_writes_html():
    source = (SITE / "js" / "models.js").read_text(encoding="utf-8")
    assert '"data/representative_models.json"' in source
    assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write", source)
    fields = (set(TOP_FIELDS) | set(MODEL_FIELDS) | set(KEY_FIELDS) | set(COVERAGE_FIELDS) | set(LEVEL_FIELDS)
              | set(STAT_FIELDS) | set(TAX_LINE_FIELDS) | set(NOT_APPLIED_FIELDS) | set(CLOSEST_FIELDS)
              | set(LEVEL_UTILITY_FIELDS) | {"scope"} | {f for group in EXCLUSION_TEXT_FIELDS.values() for f in group})
    unread = sorted(f for f in fields if not re.search(rf"\b{re.escape(f)}\b", source))
    assert not unread, f"listed in the contract but not read by models.js: {unread}"


def test_rm7f_css_block_is_appended_once():
    css = (SITE / "css" / "style.css").read_text(encoding="utf-8")
    assert css.count("/* Representative models (Phase 7F) */") == 1
    block = css.split("/* Representative models (Phase 7F) */", 1)[1]
    assert re.search(r"\.rm-table-wrap\s*\{[^}]*overflow-x:\s*auto", block)
    assert "#view-models .hidden" in block
