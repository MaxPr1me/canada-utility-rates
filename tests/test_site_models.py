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


# Phase 7C contributor nouns and the Phase 7E illustrative sidecar (synthetic load profile).
MODELS_JS = SITE / "js" / "models.js"
MODELS_CSS = SITE / "css" / "models.css"
ILLUSTRATIVE_TOGGLE = "Show illustrative all-in estimate (synthetic load profile)"
ILLUSTRATIVE_LABEL = "SYNTHETIC LOAD PROFILE - ILLUSTRATIVE ONLY"
ILLUSTRATIVE_WARNING = ("Representative only: not a forecast, a quote or a bill. "
                        "Do not use it for decisions; it needs further analysis.")
NOUN_FIELDS = ("contributor_noun", "singular", "plural", "market_indexed_excluded", "components")
ILLUSTRATIVE_FIELDS = ("available", "reason", "caveat", "method", "window")
WINDOW_FIELDS = ("start_month", "end_month", "months")
ILLUSTRATIVE_LEVEL_FIELDS = ("synthetic_profile", "illustrative_only", "market_energy_per_kwh", "market_energy_cost",
                             "profile", "without_tax", "with_tax")
PROFILE_FIELDS = ("peak_kw", "base_kw", "business_hours_beginning", "days", "time_basis", "holidays",
                  "business_hours_per_month", "other_hours_per_month")
ILLUSTRATIVE_BANDS = {"commercial_medium", "commercial_large"}


def _js_functions(source):
    """Top-level function name -> source text up to the next top-level function of the models.js IIFE."""
    starts = [(m.group(1), m.start()) for m in re.finditer(r"^    function (\w+)\(", source, flags=re.M)]
    ends = [start for _, start in starts[1:]] + [len(source)]
    return {name: source[start:end] for (name, start), end in zip(starts, ends)}


def _js_string(source, name):
    match = re.search(rf'const {name} = ((?:"[^"]*"\s*\+?\s*)+);', source)
    assert match, f"models.js has no string constant {name}"
    return "".join(re.findall(r'"([^"]*)"', match.group(1)))


def test_rm7e_models_js_fixes_the_toggle_label_warning_and_badge_texts():
    source = MODELS_JS.read_text(encoding="utf-8")
    assert _js_string(source, "ILLUSTRATIVE_TOGGLE_TEXT") == ILLUSTRATIVE_TOGGLE
    assert _js_string(source, "ILLUSTRATIVE_LABEL") == ILLUSTRATIVE_LABEL
    assert _js_string(source, "ILLUSTRATIVE_WARNING") == ILLUSTRATIVE_WARNING
    block = _js_functions(source)["illustrativeBlock"]
    assert 'warning.setAttribute("role", "note")' in block
    assert '"SYNTHETIC"' in block and "ILLUSTRATIVE_LABEL" in block and "ILLUSTRATIVE_WARNING" in block
    # The warning comes first in the block, before any number.
    assert block.index("section.append(warning)") < block.index("illustrativeLevel(")


def test_rm7e_toggle_is_a_labelled_unticked_checkbox_and_builds_the_block_only_while_ticked():
    functions = _js_functions(MODELS_JS.read_text(encoding="utf-8"))
    controls = functions["illustrativeControls"]
    for needle in ('input.type = "checkbox"', "input.checked = false", "label.htmlFor = ILLUSTRATIVE_TOGGLE_ID",
                   "label.append(input, el(\"span\", null, ILLUSTRATIVE_TOGGLE_TEXT))"):
        assert needle in controls, needle
    assert re.search(r'addEventListener\("change", \(\) => \{\s*slot\.replaceChildren\(\.\.\.\(input\.checked \? '
                     r"\[illustrativeBlock\(", controls)
    callers = sorted(name for name, body in functions.items() if "illustrativeBlock(" in body)
    assert callers == ["illustrativeBlock", "illustrativeControls"]
    # Fail closed: the model must say available and every level must be flagged synthetic and illustrative.
    gate = functions["illustrativeLevels"]
    for needle in ("info.available !== true", "all.synthetic_profile === true", "all.illustrative_only === true"):
        assert needle in gate, needle
    # Rebuilt (unticked) on every model render, so switching models resets the toggle.
    assert "illustrativeControls(model)" in functions["renderNotes"]


def test_rm7e_illustrative_numbers_never_reach_the_main_table_badge_or_statistics():
    functions = _js_functions(MODELS_JS.read_text(encoding="utf-8"))
    readers = sorted(name for name, body in functions.items() if "illustrative_all_in" in body)
    assert readers == ["illustrativeLevel", "illustrativeLevels"]
    for name in ("renderModel", "renderBadge", "stateText", "renderTable", "levelRow", "rangeBar", "closestCell",
                 "outliersCell", "taxBlock", "factsGrid", "contributorsDetails"):
        assert "illustrative" not in functions[name].lower(), name


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


def test_rm7c_7e_models_js_reads_the_new_contract_fields():
    source = MODELS_JS.read_text(encoding="utf-8")
    fields = (set(NOUN_FIELDS) | {"illustrative", "illustrative_all_in"} | set(ILLUSTRATIVE_FIELDS)
              | set(WINDOW_FIELDS) | set(ILLUSTRATIVE_LEVEL_FIELDS) | set(PROFILE_FIELDS) | set(STAT_FIELDS))
    unread = sorted(f for f in fields if not re.search(rf"\b{re.escape(f)}\b", source))
    assert not unread, f"listed in the contract but not read by models.js: {unread}"


@pytest.mark.parametrize("name", sorted(BUILDS))
def test_rm7c_7e_optional_engine_fields_have_the_shape_models_js_reads(name):
    for model in BUILDS[name]["models"]:
        where = f"{name} {model['id']}"
        noun = model["coverage"].get("contributor_noun")
        if noun is not None:
            assert all(isinstance(noun.get(f), str) and noun[f].strip() for f in ("singular", "plural")), where
        for entry in (model.get("energy") or {}).get("market_indexed_excluded") or []:
            assert isinstance(entry.get("utility"), str), where
            assert entry.get("components") and all(isinstance(c, str) and c for c in entry["components"]), where
        info = model.get("illustrative")
        levels = [level for level in model["levels"] if level.get("illustrative_all_in") is not None]
        if info is None:
            assert not levels, f"{where}: illustrative_all_in without model.illustrative"
            continue
        _assert_fields(info, ("available", "reason"), f"{where} illustrative")
        if info["available"] is not True:
            assert not levels, f"{where}: illustrative_all_in on an unavailable model"
            continue
        _assert_fields(info, ILLUSTRATIVE_FIELDS, f"{where} illustrative")
        assert model["key"]["province"] == "ON" and model["key"]["size_band"] in ILLUSTRATIVE_BANDS, where
        assert model["state"] == "market_energy_pending", f"{where}: the state must stay market_energy_pending"
        _assert_fields(info["window"], WINDOW_FIELDS, f"{where} illustrative.window")
        assert levels, where
        for level in levels:
            all_in = level["illustrative_all_in"]
            _assert_fields(all_in, ILLUSTRATIVE_LEVEL_FIELDS, f"{where} {level['id']} illustrative_all_in")
            assert all_in["synthetic_profile"] is True and all_in["illustrative_only"] is True, where
            _assert_fields(all_in["profile"], PROFILE_FIELDS, f"{where} {level['id']} profile")
            for side in ("without_tax", "with_tax"):
                _assert_fields(all_in[side], STAT_FIELDS, f"{where} {level['id']} illustrative {side}")


def test_rm7e_models_css_styles_every_sidecar_class_and_marks_the_block_dashed():
    css = MODELS_CSS.read_text(encoding="utf-8")
    source = MODELS_JS.read_text(encoding="utf-8")
    used = sorted(set(re.findall(r"\brm-illus[\w-]*", source)))
    assert "rm-illus" in used and "rm-illus-badge" in used and "rm-illus-warning" in used
    unstyled = [name for name in used if not re.search(rf"\.{re.escape(name)}(?![\w-])[^{{]*\{{", css)]
    assert not unstyled, f"classes used by models.js without a models.css rule: {unstyled}"
    block = re.search(r"^\.rm-illus\s*\{([^}]*)\}", css, flags=re.M).group(1)
    assert re.search(r"border:\s*\d+px\s+dashed", block)
    assert "!important" not in css


def test_rm7e_index_html_links_models_css_after_style_css():
    _, tags = _index()
    sheets = [attrs.get("href") for tag, attrs in tags if tag == "link" and attrs.get("rel") == "stylesheet"]
    assert "css/models.css" in sheets, "index.html must link css/models.css after css/style.css"
    assert sheets.index("css/models.css") > sheets.index("css/style.css")
