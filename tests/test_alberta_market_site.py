"""Province switching, native hour labels and failure isolation without a network."""
import copy

import pytest
from playwright.sync_api import expect

from tests.test_across_canada import browser, model_template, open_site, payload  # noqa: F401
from tests.test_alberta_market import built  # noqa: F401
from tests.test_market_rolling import _base, _month_keys


@pytest.fixture
def markets(built):
    ontario = copy.deepcopy(_base().document)
    keys = _month_keys("2025-08")
    rows = ontario["monthly"]
    ontario["monthly"] = [
        dict(rows[index % len(rows)], month=key, era="hoep" if key < "2025-05" else "oemp")
        for index, key in enumerate(keys)]
    ontario["metadata"]["derivation_method"] = "observed_rolling_60m_hoep_oemp_ga"
    ontario["metadata"]["window"].update(start_month=keys[0], end_month=keys[-1], months=60)
    return {"data/market_pricing_alberta.json": copy.deepcopy(built[0]),
            "data/market_pricing_ontario.json": ontario}


@pytest.mark.parametrize("width", [390, 1280])
def test_region_switching_with_cdn_failure(open_site, payload, markets, width):
    page, _, errors = open_site(payload, markets=markets, width=width)
    page.locator('[data-view="market"]').click()
    expect(page.locator("#market-headline-title")).to_contain_text("Class B GA")
    page.select_option("#market-region", "alberta")
    expect(page.locator("#market-headline-title")).to_have_text("Average Wholesale Pool Energy")
    expect(page.locator(".market-headline-value")).to_have_text("5.00")
    expect(page.locator("#market-table-container tbody tr")).to_have_count(60)
    expect(page.locator("#market-table-container")).not_to_contain_text("Class B GA")
    expect(page.locator("#market-note-ontario")).to_be_hidden()
    expect(page.locator("#market-note-alberta")).to_be_visible()
    expect(page.locator('.heatmap-hour-label').first).to_have_text("1")
    expect(page.locator('.heatmap-hour-label').last).to_have_text("24")
    assert "HE1" in page.locator(".heatmap-cell").first.get_attribute("title")
    assert "EST" not in page.locator("#market-heatmap-description").inner_text()
    assert page.locator('#market-display option[value="avg_ga_class_b"]').is_disabled()
    page.select_option("#market-day-type", "weekend")
    expect(page.locator(".heatmap-cell")).to_have_count(288)
    expect(page.locator(".market-chart-notice")).to_have_count(1)
    page.select_option("#market-region", "ontario")
    expect(page.locator("#market-note-ontario")).to_be_visible()
    expect(page.locator("#market-note-alberta")).to_be_hidden()
    expect(page.locator("#market-headline-title")).to_contain_text("Class B GA")
    expect(page.locator("#market-table-container")).to_contain_text("Class B GA")
    assert not errors


@pytest.mark.parametrize("bad", ["missing", "province", "method", "ga", "duplicate_month", "duplicate_bin",
                                 "counts", "check", "source", "price"])
def test_invalid_alberta_is_isolated_and_region_control_stays_available(open_site, payload, markets, bad):
    doc = markets["data/market_pricing_alberta.json"]
    if bad == "missing":
        markets["data/market_pricing_alberta.json"] = {}
    elif bad in ("province", "method"):
        doc["metadata"]["province" if bad == "province" else "derivation_method"] = "ON"
    elif bad == "ga":
        doc["monthly"][0]["ga_class_b"] = 0
    elif bad == "duplicate_month":
        doc["monthly"][1] = doc["monthly"][0]
    elif bad == "duplicate_bin":
        doc["hourly_surface"][1] = doc["hourly_surface"][0]
    elif bad == "counts":
        doc["metadata"]["coverage"]["observed_hours"] += 1
    elif bad == "check":
        doc["metadata"]["cross_check"]["max_abs_difference_per_mwh"] = 1
    elif bad == "source":
        doc["monthly"][0]["source_url"] = "javascript:alert(1)"
    else:
        doc["monthly"][0]["energy_arithmetic"] = "not a price"
    page, _, errors = open_site(payload, markets=markets)
    page.locator('[data-view="market"]').click()
    page.select_option("#market-region", "alberta")
    expect(page.locator("#market-notice")).to_contain_text("not available")
    expect(page.locator("#market-content")).to_be_hidden()
    expect(page.locator("#market-region")).to_be_visible()
    page.select_option("#market-region", "ontario")
    expect(page.locator("#market-content")).to_be_visible()
    expect(page.locator("#market-table-container")).to_contain_text("Class B GA")
    assert not errors


def test_chart_instance_and_province_series_are_replaced(open_site, payload, markets):
    stub = """window.charts=[]; window.destroyed=0;
        window.Chart=class {constructor(canvas, config) {window.charts.push(config);}
        destroy(){window.destroyed++;}};"""
    page, _, errors = open_site(payload, markets=markets, chart_stub=stub)
    page.locator('[data-view="market"]').click()
    page.select_option("#market-region", "alberta")
    assert page.evaluate("charts.at(-1).data.datasets.map(d=>d.label)") == ["Alberta pool energy"]
    assert page.evaluate("destroyed") == 1
    page.select_option("#market-region", "ontario")
    assert len(page.evaluate("charts.at(-1).data.datasets")) == 3
    assert page.evaluate("destroyed") == 2
    assert not errors
