"""Offline browser tests for the Across-Canada "Spark gap" sub-tab (method SG-1, owner decisions 124-165).

The spark gap file is built from the frozen records of tests/test_spark_gap.py; every request is routed locally.
"""
import copy

import pytest
from playwright.sync_api import expect

from tests.test_across_canada import browser, model_template, open_site, payload  # noqa: F401
from tests.test_spark_gap import inputs, result  # noqa: F401

SPARK = "data/spark_gap.json"


@pytest.fixture
def spark(result):  # noqa: F811
    return copy.deepcopy(result)


def _open_spark(open_site, payload, spark, width=1280):  # noqa: F811
    page, _, errors = open_site(payload, markets={SPARK: spark}, width=width)
    requested = []
    page.on("request", lambda request: requested.append(request.url) if request.url.endswith(SPARK) else None)
    page.locator('[data-view="across-canada"]').click()
    expect(page.locator("#across-content table")).to_be_visible()
    expect(page.locator('[data-across-tab="residential"]')).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#across-spark")).to_be_hidden()
    assert requested == []  # loaded only when its sub-tab opens
    page.locator('[data-across-tab="spark"]').click()
    expect(page.locator("#spark-content table")).to_be_visible()
    expect(page.locator("#across-residential")).to_be_hidden()
    return page, errors


def _view(spark, customer, region, view):
    row = next(r for c in spark["customers"] if c["id"] == customer for r in c["rows"] if r["region"] == region)
    return row["views"][view]


def test_subtab_loads_lazily_and_lists_every_region(open_site, payload, spark):  # noqa: F811
    page, errors = _open_spark(open_site, payload, spark)
    expect(page.locator("#spark-content tbody tr")).to_have_count(13)
    ns = page.locator('#spark-content tr[data-region="NS"]')
    expect(ns).to_contain_text("Heating oil")
    expect(ns).to_contain_text("Oil price: October 2026")
    expect(ns).to_contain_text("A heat pump costs less to run than a new oil furnace.")
    expect(page.locator('#spark-content tr[data-region="YT"]')).to_contain_text("After automatic subsidies, before tax")
    expect(page.locator("#spark-asof")).to_contain_text("heating oil October 2026")
    expect(page.locator("#spark-notes")).to_contain_text("Statistics Canada")
    page.locator('[data-across-tab="residential"]').click()
    expect(page.locator("#across-content table")).to_be_visible()
    expect(page.locator("#across-spark")).to_be_hidden()
    assert errors == []


@pytest.mark.parametrize("view", ["with_tax", "without_tax"])
def test_bars_and_cells_show_the_published_values(open_site, payload, spark, view):  # noqa: F811
    page, errors = _open_spark(open_site, payload, spark)
    page.select_option("#spark-tax", view)
    for region in ("ON", "NS", "YT"):
        expected = _view(spark, "residential", region, view)["spark_gap"]["average"]
        bar = page.locator(f'.spark-chart-row[data-region="{region}"] .spark-bar')
        assert float(bar.get_attribute("data-value")) == pytest.approx(expected)
        expect(page.locator(f'#spark-content tr[data-region="{region}"]')).to_contain_text(f"Average {expected:.2f}")
    assert errors == []


def test_unavailable_rows_have_no_bar_and_say_why(open_site, payload, spark):  # noqa: F811
    page, errors = _open_spark(open_site, payload, spark)
    for region in ("BC", "NU"):
        expect(page.locator(f'.spark-chart-row[data-region="{region}"] .spark-bar')).to_have_count(0)
        expect(page.locator(f'.spark-chart-row[data-region="{region}"]')).to_contain_text("Not available")
    expect(page.locator('#spark-content tr[data-region="NU"]')).to_contain_text("Nunavut")
    page.select_option("#spark-customer", "commercial_medium")
    expect(page.locator("#spark-content tbody tr")).to_have_count(8)
    expect(page.locator("#spark-content thead")).not_to_contain_text("Realistic heat pump COP")
    expect(page.locator("#spark-notes")).to_contain_text("input tax credits")
    expect(page.locator(".spark-bar")).to_have_count(0)
    assert errors == []


def test_failure_notice_retries_and_leaves_other_views_working(open_site, payload, spark):  # noqa: F811
    page, _, errors = open_site(payload, markets={SPARK: spark})
    calls = []

    def flaky(route):
        calls.append(route.request.url)
        if len(calls) == 1:
            route.fulfill(status=503, body="Unavailable")
        else:
            route.fulfill(json=spark)
    page.route(f"**/{SPARK}", flaky)
    page.locator('[data-view="across-canada"]').click()
    page.locator('[data-across-tab="spark"]').click()
    expect(page.locator("#spark-status")).to_contain_text("not available")
    page.locator('[data-across-tab="residential"]').click()
    expect(page.locator("#across-content table")).to_be_visible()
    page.locator('[data-across-tab="spark"]').click()
    expect(page.locator("#spark-content table")).to_be_visible()
    expect(page.locator("#spark-status")).to_have_text("")
    assert len(calls) == 2 and errors == []


def test_published_text_is_never_html(open_site, payload, spark):  # noqa: F811
    row = next(r for c in spark["customers"] if c["id"] == "residential" for r in c["rows"] if r["region"] == "ON")
    row["electricity"]["utilities"][0]["utility"] = '<img src=x onerror="window.__bad=1">'
    row["fuel_prices"]["notes"] = ["<script>window.__bad=1</script>"]
    spark["assumptions"]["gas_heating_values"]["entries"][0]["source"]["url"] = "javascript:window.__bad=1"
    page, errors = _open_spark(open_site, payload, spark)
    page.locator('#spark-content tr[data-region="ON"] summary').click()
    expect(page.locator('#spark-content tr[data-region="ON"]')).to_contain_text("<img src=x")
    assert page.locator("#across-spark img").count() == 0
    assert page.locator('#across-spark a[href^="javascript:"]').count() == 0
    assert page.evaluate("window.__bad === undefined") and errors == []


def test_phone_width_keeps_table_and_chart_usable(open_site, payload, spark):  # noqa: F811
    page, errors = _open_spark(open_site, payload, spark, width=390)
    expect(page.locator(".spark-chart-row")).to_have_count(13)
    expect(page.locator('#spark-content tr[data-region="ON"]')).to_be_visible()
    assert errors == []
