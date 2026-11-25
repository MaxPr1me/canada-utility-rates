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
from tests.test_models_7c import ARCHETYPES, _market_doc

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SITE = ROOT / "site"
AS_OF = "2026-10-09"
STATES = {"modeled", "single_source", "market_energy_pending", "market_energy_estimated", "not_computable"}
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


SHAPES = load_usage_levels()["market_energy_shapes"]


def _builds():
    records = load_rates(FIXTURES / "rm_records_sample.json") + load_rates(FIXTURES / "rm_records_b12.json")
    fx = _engine_fixture()
    return {
        "export_like": build_models(records, load_crosswalk(), load_usage_levels(), load_taxes(), as_of=AS_OF),
        "engine_fixture": build_models(fx["records"], fx["crosswalk"], fx["usage_levels"], fx["taxes"], as_of=AS_OF),
        "single_source": _synthetic([_record(_tou() + [_component("fixed", 30.0, "$/month", "Service Charge")])]),
        "not_computable": _synthetic([_record(_tou()[:2])]),
        "market_pending": _synthetic([_demand("A Hydro", 1, 100.0), _demand("B Hydro", 2, 300.0)]),
        # Method 7S-2: estimated market energy (in-memory simulated runs and market history), and its fallback.
        "estimated": build_models([_demand("A Hydro", 1, 100.0), _demand("B Hydro", 2, 300.0)], fx["crosswalk"],
                                  {**fx["usage_levels"], "market_energy_shapes": SHAPES}, fx["taxes"], as_of=AS_OF,
                                  market_document=_market_doc(business=0.08), archetypes=ARCHETYPES),
        "estimate_unavailable": build_models([_demand("A Hydro", 1, 100.0), _demand("B Hydro", 2, 300.0)],
                                             fx["crosswalk"], {**fx["usage_levels"], "market_energy_shapes": SHAPES},
                                             fx["taxes"], as_of=AS_OF, market_document=_market_doc(business=0.08),
                                             archetypes=None),
        # Method 7T-1 (owner decisions 2026-11-24): the territorial models with their after-subsidy fields.
        "territorial": build_models(load_rates(FIXTURES / "rm_records_t.json"), load_crosswalk(), load_usage_levels(),
                                    load_taxes(), provinces=("YT", "NT", "NU"), as_of="2026-11-24",
                                    market_documents={"ON": None, "AB": None}),
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
    assert views == ["rates", "rate-history", "market", "models", "across-canada", "compare"]
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


# Phase 7C contributor nouns and the method 7S-2 market energy note (owner decisions 119-123, 2026-11-25; it replaced
# method 7S-1's opt-in simulated block and the separate benchmark block).
MODELS_JS = SITE / "js" / "models.js"
MODELS_CSS = SITE / "css" / "models.css"
NOUN_FIELDS = ("contributor_noun", "singular", "plural", "market_indexed_excluded", "components")
ESTIMATE_FIELDS = ("available", "reason", "input_problem", "profile_id", "price_per_kwh", "price_range", "window",
                   "shape", "buildings", "assumptions")
WINDOW_FIELDS = ("start_month", "end_month", "months")
ESTIMATE_LEVEL_FIELDS = ("price_per_kwh", "cost")
RANGE_FIELDS = ("min", "max")
BUILDING_FIELDS = ("building_type", "heating_fuel", "city", "average_monthly_peak_kw", "kwh_per_kw", "quality_flag",
                   "price_per_kwh")
BENCHMARK_LEVEL_FIELDS = ("available", "market_energy_per_kwh", "market_energy_cost", "without_tax", "with_tax")
ESTIMATE_BANDS = {"commercial_medium", "commercial_large"}


def _js_functions(source):
    """Top-level function name -> source text up to the next top-level function of the models.js IIFE."""
    starts = [(m.group(1), m.start()) for m in re.finditer(r"^    function (\w+)\(", source, flags=re.M)]
    ends = [start for _, start in starts[1:]] + [len(source)]
    return {name: source[start:end] for (name, start), end in zip(starts, ends)}


def test_s2_one_always_visible_note_replaces_the_opt_in_block_and_the_benchmark_block():
    source = MODELS_JS.read_text(encoding="utf-8")
    functions = _js_functions(source)
    assert "energyNote(model, level)" in functions["renderNotes"]
    for gone in ("illustrative", "benchmarkBlock", '"checkbox"', "rm-illus", "rm-benchmark", "SIMULATED"):
        assert gone not in source, gone
    # Fail closed: the estimate is described only when the model says it was applied and the level carries it.
    gate = functions["estimateUsable"]
    for needle in ('model.state === "market_energy_estimated"',
                   'model.cost_basis === "delivery_and_estimated_market_energy"', "info.available === true",
                   "isNum(info.price_per_kwh)", "isNum(costs.cost)"):
        assert needle in gate, needle
    bench = functions["benchmarkUsable"]
    for needle in ("info.available === true", "info.province === model.key.province", "costs.available === true"):
        assert needle in bench, needle
    note = functions["energyNote"]
    assert "estimateUsable(model, level)" in note and "benchmarkUsable(model, level)" in note
    assert "never a guessed energy price" in note


def test_s2_estimated_energy_is_labelled_in_the_badge_caption_row_and_cost_basis():
    source = MODELS_JS.read_text(encoding="utf-8")
    functions = _js_functions(source)
    assert 'case "market_energy_estimated"' in functions["stateText"]
    assert "with estimated market energy" in functions["stateText"]
    assert 'market_energy_estimated: "rm-badge rm-badge-caution"' in source
    assert 'delivery_and_estimated_market_energy: "Delivery charges plus estimated market energy (not live)"' in source
    assert "Includes estimated market energy, not live" in functions["renderTable"]
    row = functions["levelRow"]
    assert "level.market_energy_estimate" in row and '"Estimated energy"' in row


def test_rm7c_models_js_uses_the_contributor_noun_with_a_utility_fallback():
    source = MODELS_JS.read_text(encoding="utf-8")
    functions = _js_functions(source)
    assert 'const DEFAULT_NOUN = { singular: "utility", plural: "utilities" };' in source
    noun_of = functions["nounOf"]
    assert "contributor_noun" in noun_of and "DEFAULT_NOUN" in noun_of
    assert "ok(noun.singular) && ok(noun.plural)" in noun_of
    for name in ("stateText", "renderTable", "coverageText", "contributorsDetails"):
        assert "nounOf(model)" in functions[name], name
    for text in ("utilities`", "Utilities (n)", "Contributing utilities", "mapped utilities", '"Utility"',
                 "closest utility and", "Median across utilities"):
        assert text not in source, f"hard-coded model noun left in models.js: {text!r}"
    note = functions["marketIndexedNote"]
    assert "market_indexed_excluded" in note and "entry.components" in note and "entry.utility" in note


def test_s2_models_js_reads_the_estimate_contract_fields():
    source = MODELS_JS.read_text(encoding="utf-8")
    fields = (set(NOUN_FIELDS) | {"energy_estimate", "market_energy_estimate", "market_benchmark"}
              | set(ESTIMATE_FIELDS) | set(WINDOW_FIELDS) | set(ESTIMATE_LEVEL_FIELDS) | set(RANGE_FIELDS)
              | set(BUILDING_FIELDS) | set(BENCHMARK_LEVEL_FIELDS) | set(STAT_FIELDS))
    unread = sorted(f for f in fields if not re.search(rf"\b{re.escape(f)}\b", source))
    assert not unread, f"listed in the contract but not read by models.js: {unread}"


@pytest.mark.parametrize("name", sorted(BUILDS))
def test_s2_optional_engine_fields_have_the_shape_models_js_reads(name):
    for model in BUILDS[name]["models"]:
        where = f"{name} {model['id']}"
        noun = model["coverage"].get("contributor_noun")
        if noun is not None:
            assert all(isinstance(noun.get(f), str) and noun[f].strip() for f in ("singular", "plural")), where
        for entry in (model.get("energy") or {}).get("market_indexed_excluded") or []:
            assert isinstance(entry.get("utility"), str), where
            assert entry.get("components") and all(isinstance(c, str) and c for c in entry["components"]), where
        info = model.get("energy_estimate")
        levels = [level for level in model["levels"] if "market_energy_estimate" in level]
        if info is None or info["available"] is not True:
            assert not levels, f"{where}: market_energy_estimate without an available estimate"
            assert model["state"] != "market_energy_estimated", where
            if info is not None:
                _assert_fields(info, ("available", "reason", "input_problem"), f"{where} energy_estimate")
                assert isinstance(info["reason"], str) and info["reason"], where
            continue
        _assert_fields(info, ESTIMATE_FIELDS, f"{where} energy_estimate")
        assert model["key"]["province"] in ("ON", "AB") and model["key"]["size_band"] in ESTIMATE_BANDS, where
        assert model["state"] == "market_energy_estimated", where
        assert model["cost_basis"] == "delivery_and_estimated_market_energy", where
        assert info["buildings"] and info["assumptions"], where
        assert all(isinstance(text, str) and text for text in info["assumptions"]), where
        for building in info["buildings"]:
            _assert_fields(building, BUILDING_FIELDS, f"{where} energy_estimate building")
        _assert_fields(info["window"], WINDOW_FIELDS, f"{where} energy_estimate.window")
        _assert_fields(info["price_range"], RANGE_FIELDS, f"{where} energy_estimate.price_range")
        assert levels, where
        for level in levels:
            estimate = level["market_energy_estimate"]
            _assert_fields(estimate, ESTIMATE_LEVEL_FIELDS, f"{where} {level['id']} market_energy_estimate")
            assert estimate["price_per_kwh"] == info["price_per_kwh"], where
            assert estimate["cost"] == round(info["price_per_kwh"] * level["kwh"], 2), where
            benchmark = level.get("market_benchmark") or {}
            if benchmark.get("available"):
                _assert_fields(benchmark, BENCHMARK_LEVEL_FIELDS, f"{where} {level['id']} market_benchmark")


def test_rm7f_fixture_builds_include_a_fallback_and_an_estimate():
    assert _model(BUILDS["estimated"], MEDIUM)["state"] == "market_energy_estimated"
    fallback = _model(BUILDS["estimate_unavailable"], MEDIUM)
    assert fallback["state"] == "market_energy_pending"
    assert fallback["energy_estimate"]["input_problem"] is True


def test_s2_models_css_styles_every_energy_note_class_and_drops_the_old_blocks():
    css = MODELS_CSS.read_text(encoding="utf-8")
    source = MODELS_JS.read_text(encoding="utf-8")
    used = sorted(set(re.findall(r"\brm-(?:energy[\w-]*|tag-estimated)", source)))
    assert {"rm-energy", "rm-energy-badge", "rm-energy-buildings", "rm-tag-estimated"} <= set(used)
    unstyled = [name for name in used if not re.search(rf"\.{re.escape(name)}(?![\w-])[^{{]*\{{", css)]
    assert not unstyled, f"classes used by models.js without a models.css rule: {unstyled}"
    assert "rm-illus" not in css and "rm-benchmark" not in css and "!important" not in css


def test_rm7e_index_html_links_models_css_after_style_css():
    _, tags = _index()
    sheets = [attrs.get("href") for tag, attrs in tags if tag == "link" and attrs.get("rel") == "stylesheet"]
    assert "css/models.css" in sheets, "index.html must link css/models.css after css/style.css"
    assert sheets.index("css/models.css") > sheets.index("css/style.css")


# Method 7T-1 optional territorial fields (owner decisions 64-79, 2026-11-24). They are new and optional: provincial
# models never carry them; site/js/models.js and site/js/across-canada.js read them.
SUBSIDY_FIELDS = {"after_subsidy": bool, "tax_basis": str, "tax_note": str, "programs": list,
                  "percentage_subsidies": list, "not_applied": list}
PROGRAM_FIELDS = ("id", "name", "utility", "treatment", "status", "applied_at", "automatic", "quote", "source_url",
                  "decided")
AFTER_SUBSIDY_FIELDS = ("available", "reason", "tax_basis", "without_tax", "closest_utility", "not_computable",
                        "applied", "not_applied")
AFTER_RECORD_FIELDS = ("record_id", "zone", "cost_after_subsidy", "seasons", "applied", "not_applied", "reasons")
NOT_APPLIED_ROW_FIELDS = ("id", "name", "utility", "reason")
TERRITORIAL_MODEL_FIELDS = ("subsidies", "interim", "percentage_riders", "shared_rate_books")


@pytest.mark.parametrize("name", sorted(set(BUILDS) - {"territorial"}))
def test_rm7t_provincial_models_carry_no_territorial_fields(name):
    for model in BUILDS[name]["models"]:
        assert not set(TERRITORIAL_MODEL_FIELDS) & set(model), model["id"]
        for level in model["levels"]:
            assert "after_subsidy" not in level
            assert all("cost_after_subsidy" not in row and "interim" not in row for row in level["utilities"])


def test_rm7t_territorial_fields_have_the_shape_the_website_reads_next():
    models = BUILDS["territorial"]["models"]
    assert {m["key"]["province"] for m in models} == {"YT", "NT", "NU"}
    for model in models:
        where = model["id"]
        subsidies = model["subsidies"]
        for field, kind in SUBSIDY_FIELDS.items():
            assert isinstance(subsidies.get(field), kind), f"{where}: subsidies.{field}"
        assert subsidies["tax_basis"] == "before_tax_only"
        assert subsidies["after_subsidy"] or isinstance(subsidies.get("reason"), str), where
        for program in subsidies["programs"]:
            _assert_fields(program, PROGRAM_FIELDS, f"{where} program")
            assert program["status"] in ("applied", "not_applied", "disclosed"), where
        for row in subsidies["not_applied"]:
            _assert_fields(row, NOT_APPLIED_ROW_FIELDS + ("levels",), f"{where} not_applied")
        for entry in model.get("percentage_riders") or []:
            _assert_fields(entry, ("id", "utility", "component", "treatment", "rates_percent", "quote", "source_url"),
                           f"{where} percentage_riders")
            assert entry["treatment"] in ("apply", "exclude", "subsidy"), where
        for entry in model.get("interim") or []:
            _assert_fields(entry, ("utility", "entry", "records", "quote", "source", "decided"), f"{where} interim")
        for level in model["levels"]:
            after = level["after_subsidy"]
            _assert_fields(after, AFTER_SUBSIDY_FIELDS, f"{where} {level['id']} after_subsidy")
            _assert_fields(after["without_tax"], STAT_FIELDS, f"{where} {level['id']} after_subsidy.without_tax")
            assert "with_tax" not in after and after["tax_basis"] == "before_tax_only"
            assert (after["without_tax"]["median"] is not None) is after["available"], where
            for row in after["not_applied"]:
                _assert_fields(row, NOT_APPLIED_ROW_FIELDS + ("records",), f"{where} {level['id']} not_applied")
            for row in level["utilities"]:
                if not subsidies["after_subsidy"]:
                    assert "cost_after_subsidy" not in row, where
                    continue
                assert row["cost_after_subsidy"] is None or isinstance(row["cost_after_subsidy"], float), where
                for record in row["after_subsidy_records"]:
                    _assert_fields(record, AFTER_RECORD_FIELDS, f"{where} {level['id']} after_subsidy_records")
                    for season in record["seasons"] or []:
                        _assert_fields(season, ("season", "months", "cost_after_subsidy"), f"{where} season")
    nt = next(m for m in models if m["id"] == "NT|electricity|residential|flat|-")
    assert nt["levels"][1]["after_subsidy"]["available"] is True and nt["interim"]
    yt = next(m for m in models if m["id"] == "YT|electricity|residential|tiered|-")
    assert [book["counted_as"] for book in yt["shared_rate_books"]] == ["Yukon Energy"]


def test_rm7t_website_reads_the_territorial_fields_and_never_taxes_the_after_subsidy_cost():
    models_js = MODELS_JS.read_text(encoding="utf-8")
    across_js = (SITE / "js" / "across-canada.js").read_text(encoding="utf-8")
    read_by_models = (set(TERRITORIAL_MODEL_FIELDS) | {"after_subsidy", "cost_after_subsidy", "reason", "tax_note",
                                                       "programs", "percentage_subsidies", "not_applied", "applied_at",
                                                       "status", "rates_percent", "treatment", "counted_as"})
    unread = sorted(f for f in read_by_models if not re.search(rf"\b{re.escape(f)}\b", models_js))
    assert not unread, f"territorial fields not read by models.js: {unread}"
    assert all(re.search(rf"\b{field}\b", across_js) for field in ("subsidies", "after_subsidy", "reason"))
    # Decision 74: the after-subsidy cost is published before tax only; the browser never derives a taxed figure.
    for source in (models_js, across_js):
        assert not re.search(r"after_subsidy[^;\n]*with_tax", source)
