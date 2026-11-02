"""Offline browser regressions for shared models, assumptions and residential comparisons."""
import copy
import mimetypes
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
        if model["key"]["sector"] != "residential":
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

    def open_page(payload, failures=(), width=1280, markets=None, chart_stub=None):
        context = browser.new_context(viewport={"width": width, "height": 900})
        contexts.append(context)
        requests, errors = [], []
        failures = iter(failures)
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
    on = [m for m in payload["models"] if m["key"]["province"] == "ON" and m["key"]["sector"] == "residential"]
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


@pytest.mark.parametrize("state", ["market_energy_pending", "not_computable", "withheld", "missing_level", "delivery_only"])
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
