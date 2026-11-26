"""Offline browser tests for the Building Archetypes tab (method AC-1, owner decisions 107-110).

The archetype cost file is built from the frozen records and synthetic runs of tests/test_archetype_costs.py; every
request is routed locally.
"""
import copy
from decimal import ROUND_HALF_UP, Decimal

import pytest
from playwright.sync_api import expect

from tests.test_across_canada import browser, model_template, open_site, payload  # noqa: F401
from tests.test_archetype_costs import _build, _records, _run

ARCH = "data/archetype_costs.json"


@pytest.fixture(scope="module")
def document():
    runs = [_run(kwh_per_hour=36.0, peaks=[120.0] * 12, name="office-electric"),
            _run(fuel="NaturalGas", kwh_per_hour=25.0, peaks=[90.0] * 12, gas_gj=[60.0] * 12, name="office-gas"),
            _run(building="LowriseApartment", kwh_per_hour=12.0, peaks=[30.0] * 12, name="apartment"),
            _run("Calgary", "Warehouse", fuel="NaturalGas", kwh_per_hour=10.0, peaks=[100.0] * 12,
                 gas_gj=[50.0] * 12, name="warehouse"),
            _run(building="Hospital", kwh_per_hour=2400.0, peaks=[6000.0] * 12, name="hospital")]
    return _build(runs, records=_records())


@pytest.fixture
def arch(document):
    return copy.deepcopy(document)


def _open(open_site, payload, arch, width=1280):  # noqa: F811
    page, _, errors = open_site(payload, markets={ARCH: arch}, width=width)
    requested = []
    page.on("request", lambda request: requested.append(request.url) if request.url.endswith(ARCH) else None)
    expect(page.locator('[data-view="archetypes"]')).to_contain_text("Simulated")
    assert requested == []  # loaded only when the tab opens
    page.locator('[data-view="archetypes"]').click()
    expect(page.locator("#arch-content table")).to_be_visible()
    return page, errors


def test_the_tab_loads_lazily_and_labels_every_result_simulated(open_site, payload, arch):  # noqa: F811
    page, errors = _open(open_site, payload, arch)
    expect(page.locator('#view-archetypes [role="note"]')).to_contain_text("not real buildings or bills")
    rows = page.locator("#arch-content tbody tr")
    expect(rows).to_have_count(5)
    for index in range(5):
        expect(rows.nth(index).locator(".arch-badge").first).to_have_text("Simulated")
    expect(page.locator('tr[data-run="office-electric"]')).to_contain_text("Estimated energy")
    expect(page.locator('tr[data-run="apartment"]')).to_contain_text("Bulk-metered building")
    expect(page.locator('tr[data-run="hospital"]')).to_contain_text("Not computable")
    expect(page.locator("#arch-asof")).to_contain_text("4 of 5 simulated buildings priced")
    expect(page.locator("#arch-notes")).to_contain_text("Not applied")
    assert errors == []


def test_sorting_filters_and_tax_switch_use_the_published_values(open_site, payload, arch):  # noqa: F811
    page, errors = _open(open_site, payload, arch)
    priced = sorted((run for run in arch["runs"] if run["total"]["status"] == "ok"),
                    key=lambda run: run["total"]["with_tax"], reverse=True)
    order = page.locator("#arch-content tbody tr").evaluate_all("rows => rows.map(r => r.dataset.run)")
    assert order[:4] == [run["id"] for run in priced] and order[4] == "hospital"  # not computable last
    page.locator('button[data-sort="total"]').click()
    order = page.locator("#arch-content tbody tr").evaluate_all("rows => rows.map(r => r.dataset.run)")
    assert order[:4] == [run["id"] for run in reversed(priced)]
    page.select_option("#arch-fuel", "NaturalGas")
    expect(page.locator("#arch-content tbody tr")).to_have_count(2)
    page.select_option("#arch-fuel", "")
    page.select_option("#arch-tax", "without_tax")
    office = next(run for run in arch["runs"] if run["id"] == "office-gas")
    shown = Decimal(str(office["total"]["without_tax"])).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    expect(page.locator('tr[data-run="office-gas"]')).to_contain_text(f"${shown:,}")
    expect(page.locator("#arch-content caption")).to_contain_text("before tax and rebates")
    assert errors == []


def test_the_detail_shows_class_charges_chart_pair_and_sources(open_site, payload, arch):  # noqa: F811
    page, errors = _open(open_site, payload, arch)
    page.locator('tr[data-run="office-gas"] .arch-open').click()
    detail = page.locator("#arch-detail")
    expect(detail).to_be_visible()
    expect(detail).to_contain_text("Medium office, Toronto: Natural gas heating")
    expect(detail).to_contain_text("monthly average peak demand is equal to or greater than 50 kW")
    expect(detail).to_contain_text("Rate 6 commercial sector")
    expect(detail).to_contain_text("Cost by charge group")
    expect(detail.locator("rect.arch-bar-electricity")).to_have_count(12)
    expect(detail.locator("rect.arch-bar-gas")).to_have_count(12)
    expect(detail).to_contain_text("Electric versus gas heating")
    expect(detail).to_contain_text("Electric heating")
    expect(detail.locator('a[href$="/timestep.csv"]')).to_have_count(1)
    assert detail.locator("canvas").count() == 0  # no load-shape heatmap (decision 108)
    page.locator('tr[data-run="apartment"] .arch-open').click()
    expect(detail).to_contain_text("17 dwelling units")
    expect(detail).to_contain_text("owner decision 167")
    page.locator('tr[data-run="hospital"] .arch-open').click()
    expect(detail).to_contain_text("Not computable")
    expect(detail).to_contain_text("fits 0 of the classes")
    assert errors == []


def test_a_missing_file_shows_a_notice_and_retries(open_site, payload, arch):  # noqa: F811
    page, _, errors = open_site(payload, markets={ARCH: arch})
    calls = []

    def flaky(route):
        calls.append(route.request.url)
        if len(calls) == 1:
            route.fulfill(status=503, body="Unavailable")
        else:
            route.fulfill(json=arch)
    page.route(f"**/{ARCH}", flaky)
    page.locator('[data-view="archetypes"]').click()
    expect(page.locator("#arch-notice")).to_contain_text("not available")
    page.locator('[data-view="models"]').click()
    page.locator('[data-view="archetypes"]').click()
    expect(page.locator("#arch-content table")).to_be_visible()
    expect(page.locator("#arch-notice")).to_be_hidden()
    assert len(calls) == 2 and errors == []


def test_published_text_is_never_html(open_site, payload, arch):  # noqa: F811
    run = next(item for item in arch["runs"] if item["id"] == "hospital")
    run["electricity"]["reasons"] = ['<img src=x onerror="window.__bad=1">']
    run["sources"]["timestep_csv"] = "javascript:window.__bad=1"
    page, errors = _open(open_site, payload, arch)
    page.locator('tr[data-run="hospital"] .arch-open').click()
    expect(page.locator("#arch-detail")).to_contain_text("<img src=x")
    assert page.locator("#view-archetypes img").count() == 0
    assert page.locator('#view-archetypes a[href^="javascript:"]').count() == 0
    assert page.evaluate("window.__bad === undefined") and errors == []


def test_phone_width_shows_stacked_cards_without_overflow(open_site, payload, arch):  # noqa: F811
    page, errors = _open(open_site, payload, arch, width=390)
    row = page.locator('tr[data-run="office-gas"]')
    expect(row).to_be_visible()
    assert row.evaluate("r => getComputedStyle(r).display") == "block"
    row.locator(".arch-open").click()
    expect(page.locator("#arch-detail")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert errors == []
