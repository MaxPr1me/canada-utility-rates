"""Offline browser regressions for shared models, assumptions and residential comparisons."""
import copy
import mimetypes
import re
from pathlib import Path
from urllib.parse import urlparse

import pytest
from playwright.sync_api import expect, sync_playwright

from pipeline.representative_models import load_rates
from tests.test_site_models import _builds

SITE = Path(__file__).resolve().parents[1] / "site"


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture(scope="module")
def model_template():
    data = _builds()["export_like"]
    # The crosswalk fixture omits component values; use explicit synthetic display totals.
    for model in data["models"]:
        if model["key"]["sector"] != "residential" or model["key"]["fuel"] != "electricity":
            continue
        model["state"] = "modeled"
        model["cost_basis"] = "delivery_and_energy"
        model["energy"] = {"status": "included", "market_pending": []}
        for level in model["levels"]:
            level["without_tax"]["median"] = 40 + level["kwh"] * 0.1
            level["with_tax"]["median"] = round(level["without_tax"]["median"] * 0.973, 2)
    return data


@pytest.fixture
def payload(model_template):
    return copy.deepcopy(model_template)


@pytest.fixture
def open_site(browser):
    contexts = []

    def open_page(payload, failures=(), width=1280, markets=None, chart_stub=None, history=None, rates=None):
        context = browser.new_context(viewport={"width": width, "height": 900})
        contexts.append(context)
        requests, errors = [], []
        failures = iter(failures)
        if rates is None:
            rates = load_rates(SITE.parent / "tests" / "fixtures" / "rm_records_sample.json")[:2]

        def route(request):
            path = urlparse(request.request.url).path.lstrip("/")
            if path == "data/representative_models.json":
                requests.append(path)
                failure = next(failures, None)
                if failure == "http":
                    request.fulfill(status=503, body="Unavailable")
                elif failure == "json":
                    request.fulfill(content_type="application/json", body="{broken")
                elif failure == "schema":
                    request.fulfill(json={"models": []})
                else:
                    request.fulfill(json=payload)
            elif path == "data/model_change_history.json":
                if history == "http":
                    request.fulfill(status=503, body="Unavailable")
                elif history == "json":
                    request.fulfill(content_type="application/json", body="{broken")
                else:
                    request.fulfill(json=history or {})
            elif path == "data/rates.json":
                request.fulfill(json=rates)
            elif markets is not None and path in markets:
                request.fulfill(json=markets[path])
            elif path.startswith("data/"):
                request.fulfill(json=[] if path in ("data/missing.json", "data/source_review_report.json") else {})
            elif urlparse(request.request.url).hostname != "utility.test":
                request.fulfill(content_type="application/javascript", body=chart_stub or "")
            else:
                file = SITE / (path or "index.html")
                if file.is_file():
                    request.fulfill(body=file.read_bytes(),
                                    content_type=mimetypes.guess_type(str(file))[0] or "text/plain")
                else:
                    request.fulfill(status=404, body="Not found")

        context.route("**/*", route)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://utility.test/")
        expect(page.locator(".compare-add")).to_have_count(2)
        return page, requests, errors

    yield open_page
    for context in contexts:
        context.close()


def test_model_history_records_material_changes_without_recalculating_prices(open_site, payload):
    from pipeline import model_monitoring as monitoring
    from datetime import timedelta

    model = next(m for m in payload["models"] if m["key"]["province"] == "ON"
                 and m["key"]["sector"] == "residential" and m["key"]["structure"] == "tou")
    level = next(level for level in model["levels"] if level["id"] == "typical")
    level["with_tax"]["median"] = 100
    receipt = monitoring.generation_receipt(payload, previous={"status": "absent"})
    history = monitoring.record_refresh(None, payload, receipt)
    level["with_tax"]["median"] = 105
    payload["generated_at"] = (monitoring.timestamp(payload["generated_at"]) + timedelta(seconds=1)).isoformat()
    receipt = monitoring.generation_receipt(payload, previous={
        "status": "known", "generated_at": history["last_refresh"]["generated_at"],
        "fingerprint": history["last_refresh"]["model_fingerprint"],
    })
    history = monitoring.record_refresh(history, payload, receipt)
    page, requests, errors = open_site(payload, history=history, width=390)
    page.locator('[data-view="models"]').click()
    expect(page.locator("#models-last-changed")).to_contain_text("Last changed:")
    page.locator("#models-history summary").click()
    expect(page.locator("#models-history-events")).to_contain_text("Material after-tax change")
    expect(page.locator("#models-history-events")).to_contain_text("$100.00 to $105.00")
    page.locator("#models-history-scope").select_option("all")
    page.locator("#models-structure").select_option("tiered")
    expect(page.locator("#models-history-events")).to_contain_text("Material after-tax change")
    expect(page.locator("#models-last-changed")).to_contain_text("not yet observed")
    page.locator("#models-history-scope").select_option("selected")
    expect(page.locator("#models-history-events")).not_to_contain_text("Material after-tax change")
    page.locator('[data-view="across-canada"]').click()
    expect(page.locator("#across-content table")).to_be_visible()
    assert requests == ["data/representative_models.json"] and errors == []


@pytest.mark.parametrize("failure", ["http", "json", "mismatched", "usage", "benchmark", "last_changed"])
def test_optional_history_failure_never_hides_usable_models(open_site, payload, failure):
    from pipeline import model_monitoring as monitoring

    history = failure
    if failure not in ("http", "json"):
        history = monitoring.record_refresh(None, payload,
                                            monitoring.generation_receipt(payload, previous={"status": "absent"}))
        if failure == "mismatched":
            history["last_refresh"]["generated_at"] = "2000-01-01T00:00:00Z"
        elif failure == "usage":
            payload["models"][0]["levels"][0]["kwh"] += 1
        elif failure == "benchmark":
            payload["models"][0]["levels"][0]["market_benchmark"] = {"available": False}
        else:
            history["last_changed"][payload["models"][0]["id"]] = "2000-01-01T00:00:00Z"
    page, requests, errors = open_site(payload, history=history)
    page.locator('[data-view="models"]').click()
    expect(page.locator("#models-table-wrap table")).to_be_visible()
    expect(page.locator("#models-last-changed")).to_contain_text("history unavailable")
    page.locator("#models-history summary").click()
    expect(page.locator("#models-history-notice")).to_contain_text("The model prices remain available")
    page.locator('[data-view="across-canada"]').click()
    expect(page.locator("#across-content table")).to_be_visible()
    assert requests == ["data/representative_models.json"] and errors == []


@pytest.mark.parametrize("first", ["models", "across-canada"])
def test_shared_load_and_separate_structures(open_site, payload, first):
    page, requests, errors = open_site(payload)
    assert requests == []
    page.locator(f'[data-view="{first}"]').click()
    page.locator('[data-view="across-canada"]').click()
    expect(page.locator("#across-content table")).to_be_visible()
    expect(page.locator("#across-usage")).to_have_value("1000")
    provinces = page.locator(".across-table tbody tr").evaluate_all(
        "rows => [...new Set(rows.map(row => row.dataset.province))]")
    assert len(provinces) == 13
    # Across-Canada compares residential electricity only; Phase 7D gas models never appear in it.
    on = [m for m in payload["models"] if m["key"]["province"] == "ON" and m["key"]["sector"] == "residential"
          and m["key"]["fuel"] == "electricity"]
    expect(page.locator('tr[data-province="ON"]')).to_have_count(len(on))
    for kwh in (500, 1000, 2000):
        page.select_option("#across-usage", str(kwh))
        for model in on:
            level = next(level for level in model["levels"] if level["kwh"] == kwh)
            label = page.evaluate("key => CanadaUtilityModels.structureLabels[key]", model["key"]["structure"])
            row = page.locator('tr[data-province="ON"]').filter(has=page.get_by_role("cell", name=label, exact=True))
            for index, field in ((1, "without_tax"), (2, "with_tax")):
                amount = page.evaluate("value => CanadaUtilityModels.money(value)", level[field]["median"])
                expect(row.locator("td").nth(index)).to_have_text(amount)
    for province in ("YT", "NT", "NU"):
        expect(page.locator(f'tr[data-province="{province}"]')).to_contain_text("Not modelled yet")
    page.locator('[data-view="models"]').click()
    expect(page.locator("#models-content")).to_be_visible()
    assert len(requests) == 1
    assert not errors


def test_tax_rebate_clarification_is_next_to_prices_without_changing_totals(open_site, payload):
    model = next(m for m in payload["models"] if m["id"] == "ON|electricity|residential|tou|-")
    payload["models"] = [model]
    page, _, errors = open_site(payload)
    page.locator('[data-view="models"]').click()
    table = page.locator("#models-table-wrap")
    expect(table.get_by_role("columnheader", name="Median before tax and rebates", exact=True)).to_be_visible()
    expect(table.get_by_role("columnheader", name="Median with tax and rebates", exact=True)).to_be_visible()
    note = table.locator(".rm-rebate-note")
    expect(note).to_have_count(1)
    expect(note).to_contain_text("Ontario Electricity Rebate")
    expect(note).to_contain_text("exceed sales taxes")
    for level in model["levels"]:
        row = table.get_by_role("row").filter(has=page.get_by_role(
            "rowheader", name=re.compile(f"{level['kwh']:,.0f} kWh")))
        for column, field in (("without", "without_tax"), ("with", "with_tax")):
            amount = page.evaluate("n => CanadaUtilityModels.money(n)", level[field]["median"])
            expect(row.locator(f'[data-col="{column}"]')).to_have_text(amount)

    page.locator('[data-view="across-canada"]').click()
    expect(page.locator("#across-tax option:checked")).to_have_text("With tax and rebates")
    expect(page.locator("#across-chart-title")).to_contain_text("after tax and rebates")
    expect(page.locator("#across-content").get_by_role(
        "columnheader", name="With tax and rebates", exact=True)).to_be_visible()
    expect(page.locator("#across-chart .rm-rebate-note")).to_contain_text("Ontario Electricity Rebate")
    typical = next(level for level in model["levels"] if level["id"] == "typical")
    bar = page.locator(".across-bar")
    expect(bar).to_have_attribute("data-value", str(typical["with_tax"]["median"]))
    page.select_option("#across-tax", "without_tax")
    expect(page.locator("#across-chart-title")).to_contain_text("before tax and rebates")
    assert float(bar.get_attribute("data-value")) == typical["without_tax"]["median"]
    assert not errors


@pytest.mark.parametrize("case", ["not_applied", "higher_total", "missing_total"])
def test_rebate_explanation_requires_applied_rebate_and_lower_published_total(open_site, payload, case):
    model = next(m for m in payload["models"] if m["id"] == "ON|electricity|residential|tou|-")
    payload["models"] = [model]
    for level in model["levels"]:
        if case == "not_applied":
            level["with_tax"]["not_applied"] = level["with_tax"]["lines"]
            level["with_tax"]["lines"] = []
        else:
            level["with_tax"]["median"] = (
                level["without_tax"]["median"] + 1 if case == "higher_total" else None)
    page, _, errors = open_site(payload)
    page.locator('[data-view="models"]').click()
    expect(page.locator("#models-content")).to_be_visible()
    expect(page.locator("#models-table-wrap .rm-rebate-note")).to_have_count(0)
    page.locator('[data-view="across-canada"]').click()
    expect(page.locator("#across-content table")).to_be_visible()
    expect(page.locator("#across-chart .rm-rebate-note")).to_have_count(0)
    assert not errors


@pytest.mark.parametrize("state", ["market_energy_pending", "market_energy_estimated", "not_computable", "withheld",
                                   "missing_level", "delivery_only"])
def test_incomplete_costs_and_synthetic_values_are_never_compared(open_site, payload, state):
    model = next(m for m in payload["models"] if m["key"]["sector"] == "residential")
    model["key"]["province"] = "NU"
    model["levels"] = [{"id": "typical", "kwh": 1000, "without_tax": {"median": 98765.43, "n": 2},
                        "with_tax": {"median": 98765.43, "n": 2},
                        "illustrative_all_in": {"median": 98765.43}}]
    if state == "withheld":
        model["levels"][0]["withheld"] = {"reason": "Required contributor missing"}
    elif state == "missing_level":
        model["levels"] = []
    elif state == "delivery_only":
        model["cost_basis"] = "delivery_only_no_energy_component"
    else:
        model["state"] = state
    page, _, errors = open_site(payload)
    page.locator('[data-view="across-canada"]').click()
    row = page.locator('tr[data-province="NU"]')
    expect(row).to_contain_text("not a full cost")
    expect(row.locator("td").nth(1)).to_have_text("\u2014")
    expect(row.locator("td").nth(2)).to_have_text("\u2014")
    assert "98,765" not in page.locator("#across-content").inner_text()
    assert not errors


def test_sources_and_model_text_are_not_html(open_site, payload):
    model = next(m for m in payload["models"] if m["key"]["sector"] == "residential")
    model["method"] = "<img src=x onerror=alert(1)>"
    model["utilities"] = [{"utility": "Example", "records": [
        {"source_url": "javascript:alert(1)"}, {"source_url": "https://example.org/official.pdf"}]}]
    page, _, errors = open_site(payload)
    page.locator('[data-view="across-canada"]').click()
    expect(page.locator("#across-content table")).to_be_visible()
    assert page.locator("#across-content img").count() == 0
    assert page.locator('#across-content a[href^="javascript:"]').count() == 0
    expect(page.locator('#across-content a[href="https://example.org/official.pdf"]')).to_have_count(1)
    assert not errors


@pytest.mark.parametrize("failure", ["http", "json", "schema"])
def test_unavailable_models_retry_without_breaking_other_views(open_site, payload, failure):
    page, requests, errors = open_site(payload, failures=[failure])
    page.locator('[data-view="across-canada"]').click()
    expect(page.locator("#across-status")).to_contain_text("not available")
    page.locator('[data-view="rates"]').click()
    expect(page.locator(".compare-add").first).to_be_visible()
    page.locator('[data-view="across-canada"]').click()
    expect(page.locator("#across-content table")).to_be_visible()
    assert len(requests) == 2
    assert not errors


def test_assumptions_both_levels_and_safe_text(open_site, payload):
    model = next(m for m in payload["models"] if m["key"]["province"] == "ON"
                 and m["key"]["size_band"] == "commercial_small" and m["key"]["structure"] == "tou")
    model["fixed_charge_variants"] = [
        {"reference": "Single-phase 10 kW", "levels": ["s1"], "utilities": ["Example"],
         "components": ["Chosen single-phase"], "decided": "user 2026-10-30"},
        {"reference": "<img src=x onerror=alert(1)>Three-phase 25 kW", "levels": ["s2"],
         "utilities": ["Example"], "components": ["Chosen three-phase"], "decided": "user 2026-10-30"},
    ]
    for level in model["levels"]:
        for row in level["utilities"]:
            row["fixed_charge_variants"] = [{"component": "Chosen " + level["id"]}]
    page, _, errors = open_site(payload)
    page.locator('[data-view="models"]').click()
    page.select_option("#models-segment", "commercial|commercial_small")
    expect(page.locator(".rm-fixed-assumptions")).to_contain_text("Single-phase 10 kW")
    expect(page.locator(".rm-fixed-assumptions")).to_contain_text("Three-phase 25 kW")
    expect(page.locator(".rm-fixed-assumptions")).to_contain_text("user 2026-10-30")
    assert page.locator(".rm-fixed-assumptions img").count() == 0
    assert "Chosen " in page.locator("#models-notes").inner_text()
    assert not errors


def test_residential_levels_show_reference_and_sensitivity_tags(open_site, payload):
    # Owner decision 29 (2026-11-20): 1,000 kWh is the reference level, 500 and 2,000 kWh are sensitivity levels.
    page, _, errors = open_site(payload)
    page.locator('[data-view="models"]').click()
    rows = page.locator("#models-table-wrap tbody tr th")
    expect(rows.nth(0)).to_contain_text("500 kWh")
    expect(rows.nth(0)).to_contain_text("Sensitivity")
    expect(rows.nth(1)).to_contain_text("Reference")
    expect(rows.nth(2)).to_contain_text("Sensitivity")
    assert "Typical" not in page.locator("#models-table-wrap").inner_text()
    assert not errors


def test_commercial_gas_models_name_the_class_used_at_each_level(open_site, payload):
    from tests.test_models_7d2_gas import _build as build_gas

    gas = build_gas()
    payload["models"] += [m for m in gas["models"] if m["id"] in (
        "MB|gas|commercial|flat|commercial_small", "NB|gas|commercial|tiered|commercial_medium")]
    page, _, errors = open_site(payload)
    page.locator('[data-view="models"]').click()
    page.select_option("#models-province", "MB")
    page.select_option("#models-fuel", "gas")
    page.select_option("#models-segment", "commercial|commercial_small")
    expect(page.locator("#models-title")).to_have_text("Manitoba gas - commercial small building - flat-rate")
    table = page.locator("#models-table-wrap")
    expect(table).to_contain_text("1,000 m³")
    expect(table.locator("tbody tr").nth(1)).to_contain_text("Reference")
    notes = page.locator("#models-notes")
    expect(notes.locator(".rm-class-selection")).to_contain_text(
        "Centra Gas Manitoba: customers may elect COM-SGS or COM-LGS; the cheaper is used at each level")
    contributors = notes.locator(".rm-details").first
    contributors.locator("summary").click()
    expect(contributors).to_contain_text("Class used")
    expect(contributors).to_contain_text("COM-SGS; cheaper of COM-SGS $230.65 and COM-LGS $248.70")
    page.select_option("#models-province", "NB")
    page.select_option("#models-segment", "commercial|commercial_medium")
    expect(notes.locator(".rm-class-selection")).to_contain_text("Peak month: 1.85 x the level")
    expect(notes.locator(".rm-fixed-assumptions")).to_contain_text("peak month = 1.85 x the level")
    assert not errors


def test_rate_browser_shows_component_periods_and_tags_ended_prices(open_site, payload):
    # Owner decision 34 (2026-11-23): dated components show their period; ended ones are tagged, never hidden.
    import json

    fixture = SITE.parent / "tests" / "fixtures" / "rm_records_7d2_gas.json"
    rates = [r for r in json.loads(fixture.read_text(encoding="utf-8"))["records"]
             if r["utility_name"] == "SaskEnergy"]
    ended, current = rates[0]["components"][0], rates[0]["components"][1]
    ended.update(effective_date="2000-01-01", end_date="2000-01-31")
    current.update(effective_date="2000-01-01", end_date="2999-12-31")
    for component in rates[0]["components"][2:] + rates[1]["components"]:
        component["end_date"] = None
    page, _, errors = open_site(payload, rates=rates)
    card = page.locator(".rate-card").filter(has_text=rates[0]["name"]).first
    expect(card.locator(".ended-badge")).to_have_count(1)
    card.locator(".card-title").click()
    modal = page.locator("#modal-content")
    expect(modal).to_contain_text("Jan 1-31, 2000")
    expect(modal).to_contain_text("Jan 1, 2000 - Dec 31, 2999")
    expect(modal.locator(".ended-badge")).to_have_count(1)
    assert not errors


def test_mobile_all_views_preserve_existing_tariff_comparison(open_site, payload):
    page, _, errors = open_site(payload, width=390)
    page.locator(".compare-add").first.click()
    page.locator('[data-view="rates"]').click()
    page.locator(".compare-add").nth(1).click()
    expect(page.locator("#compare-count")).to_have_text("2/2")
    for view in ("market", "models", "across-canada", "compare"):
        page.locator(f'[data-view="{view}"]').click()
        expect(page.locator("#view-" + view)).to_be_visible()
    expect(page.locator("#comparison-container")).to_contain_text("no calculated total")
    page.locator(".compare-remove").first.click()
    expect(page.locator("#compare-count")).to_have_text("1/2")
    page.locator('[data-view="across-canada"]').click()
    expect(page.locator(".across-table")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert not errors


@pytest.mark.parametrize("width", [1280, 390])
def test_territorial_models_show_costs_before_and_after_subsidies(open_site, payload, width):
    # Method 7T-1 (owner decisions 67, 69, 72 and 74, 2026-11-24): territorial totals are before subsidies, the
    # after-subsidy median is published before tax only, interim rates are labelled and Nunavut says why it has
    # no after-subsidy cost. Every amount comes from the engine's own territorial build, never from the browser.
    territorial = copy.deepcopy(_builds()["territorial"]["models"])
    payload["models"] += territorial
    nt = next(m for m in territorial if m["key"]["province"] == "NT" and m["key"]["sector"] == "residential")
    level = next(item for item in nt["levels"] if item["kwh"] == 1000)
    page, _, errors = open_site(payload, width=width)

    def money(value):
        return page.evaluate("value => CanadaUtilityModels.money(value)", value)

    after = level["after_subsidy"]["without_tax"]["median"]
    page.locator('[data-view="models"]').click()
    page.locator("#models-province").select_option("NT")
    expect(page.locator("#models-interim")).to_contain_text("Interim rates: Naka Power Utilities (NWT)")
    expect(page.locator("#models-table-wrap > table")).to_contain_text(money(level["without_tax"]["median"]))
    expect(page.locator(".rm-subsidies table")).to_contain_text(money(after))
    expect(page.locator(".rm-subsidies")).to_contain_text("before tax only")
    page.locator("#models-province").select_option("NU")
    expect(page.locator(".rm-subsidies")).to_contain_text("No cost after subsidies is shown")
    expect(page.locator(".rm-subsidies table")).to_have_count(0)
    page.locator("#models-province").select_option("ON")
    expect(page.locator(".rm-subsidies")).to_have_count(0)
    expect(page.locator("#models-interim")).to_be_hidden()
    page.locator('[data-view="across-canada"]').click()
    row = page.locator('tr[data-province="NT"]')
    expect(row).to_contain_text("before subsidies")
    expect(row).to_contain_text(f"After automatic subsidies: {money(after)} before tax")
    expect(page.locator('tr[data-province="NU"]')).to_contain_text("Before subsidies only")
    expect(page.locator('tr[data-province="YT"]')).not_to_contain_text("Not modelled yet")
    expect(page.locator("#across-chart")).to_contain_text("(before subsidies)")
    expect(page.locator(".across-subsidy-note")).to_be_visible()
    if width == 390:
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert not errors
