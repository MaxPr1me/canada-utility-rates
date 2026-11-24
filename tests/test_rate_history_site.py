"""Offline browser tests for the Rate History view (site/js/rate-history.js).

Owner decisions 44-57 (2026-11-23) and 80-83 (2026-11-24). Every request is routed: rates.json is the frozen live-record
fixture (tests/fixtures/rate_history_records.json) plus a few synthetic versions built here, the reviewed series and
event lists are the real site files, and the market, model-cost and revision files are synthetic documents in the
formats the data workflows write. The page clock is frozen at 2026-11-24 (America/Toronto).
"""
from __future__ import annotations

import copy
import csv
import io
import json
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

import pytest
from playwright.sync_api import expect, sync_playwright

from tests.test_site_models import _builds

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
NOW = datetime(2026, 11, 24, 17, 0, tzinfo=timezone.utc)
SERIES = json.loads((SITE / "data" / "rate_history_series.json").read_text(encoding="utf-8"))
EVENTS = json.loads((SITE / "data" / "rate_history_events.json").read_text(encoding="utf-8"))
FIXTURE = json.loads((ROOT / "tests" / "fixtures" / "rate_history_records.json").read_text(encoding="utf-8"))["records"]
OPTIONAL = ("data/rate_history_revisions.json", "data/market_quarterly_ontario.json", "data/market_quarterly_alberta.json",
            "data/model_cost_quarterly.json")
TORONTO = "Toronto Hydro-Electric System Ltd."
TOU = "Residential -- Time-of-Use (TOU)"
OEB_RELEASE = ("https://www.oeb.ca/newsroom/2026/"
               "ontario-energy-board-announces-changes-electricity-prices-households-small-businesses")


def _component(name, value, unit="$/kWh", ctype="energy", effective="2026-11-01", end=None, **extra):
    component = {"component_type": ctype, "component_name": name, "sub_component": None, "charge_value": value,
                 "charge_unit": unit, "tier_number": None, "tier_threshold": None, "tier_unit": None, "tou_period": None,
                 "season": None, "demand_threshold_kw": None, "demand_unit": None, "market_reference": None,
                 "effective_date": effective, "end_date": end, "source_url": "https://example.org/tariff.pdf",
                 "notes": None}
    component.update(extra)
    return component


def _record(rid, utility, name, province, fuel, effective, components, created, provenance="live", code="T"):
    return {"id": rid, "utility_name": utility, "name": name, "province": province, "utility_type": fuel,
            "tariff_code": code, "customer_class": "commercial", "rate_structure": "flat", "effective_date": effective,
            "end_date": None, "created_at": created, "scrape_run_id": 46, "provenance": provenance, "confidence": "high",
            "source_url": "https://example.org/tariff.pdf", "notes": None, "components": components}


def _fixture(utility, name, effective=None):
    return next(record for record in FIXTURE if record["utility_name"] == utility and record["name"] == name
                and (effective is None or record["effective_date"] == effective))


def _new_rpp_version(name, rid, utility=TORONTO, overrides=None):
    """The 2026-11-01 version of a Toronto Hydro RPP tariff: its energy prices from the fixture's November record."""
    old = _fixture(TORONTO, name)
    november = {c["component_name"]: c["charge_value"] for c in _fixture(
        TORONTO, f"{name} [Competitive Sector Multi-Unit Residential]")["components"] if c["component_type"] == "energy"}
    new = copy.deepcopy(old)
    new.update(id=rid, utility_name=utility, effective_date="2026-11-01", created_at="2026-11-01 14:50:04")
    for component in new["components"]:
        if component["component_type"] == "energy":
            component.update(effective_date="2026-11-01",
                             charge_value=(overrides or {}).get(component["component_name"], november[component["component_name"]]))
    return new


def _rates():
    rates = copy.deepcopy(FIXTURE)
    for rid, name in ((9101, TOU), (9102, "Residential -- Ultra-Low Overnight (ULO)"), (9103, "Residential -- Tiered Pricing")):
        rates.append(_new_rpp_version(name, rid))
    # A second distributor with the same RPP change, so the grouped list says "2 utilities".
    older = copy.deepcopy(_fixture(TORONTO, TOU))
    older.update(id=9104, utility_name="Hydro Ottawa Limited")
    rates += [older, _new_rpp_version(TOU, 9105, utility="Hydro Ottawa Limited")]
    # Eastward's December price is stored ahead of time: a future period (decision 81).
    december = copy.deepcopy(_fixture("Heritage Gas", "General Service", "2026-11-01"))
    december.update(id=9106, effective_date="2026-12-01", created_at="2026-11-20 10:00:00")
    for component in december["components"]:
        if component["component_name"] == "Gas Cost Recovery Rate":
            component.update(charge_value=10.1, effective_date="2026-12-01", end_date="2026-12-31")
    rates.append(december)
    # Two versions that differ only by float noise: neither a change nor a revision.
    rates += [
        _record(9201, "Float Noise Utility", "Small General Service", "BC", "electricity", "2026-10-01", [
            _component("Energy Charge", 0.1086, effective="2026-10-01"),
            _component("Customer Charge", 0.3, "$/day", "fixed", effective="2026-10-01")], "2026-10-02 10:00:00"),
        _record(9202, "Float Noise Utility", "Small General Service", "BC", "electricity", "2026-11-01", [
            _component("Energy Charge", 0.10859999999999999, effective="2026-11-01"),
            _component("Customer Charge", 0.30000000000000004, "$/day", "fixed", effective="2026-10-01")], "2026-11-01 10:00:00"),
    ]
    # Three prices sharing one description in one version, told apart only by their notes (BC Hydro, November 2026).
    def surcharges(values, effective):
        return [_component("Conditional Power Factor Surcharge", value, "fraction of Rate section charges", "adjustment",
                           effective=effective, sub_component="conditional", notes=f"power factor step {step}")
                for step, value in enumerate(values, 1)]
    rates += [
        _record(9301, "BC Hydro", "Large General Service (Rate 1600)", "BC", "electricity", "2026-10-01",
                [_component("Energy Charge", 0.0581, effective="2026-04-01")] + surcharges((0.01, 0.02, 0.03), "2026-04-01"),
                "2026-10-01 18:18:18", code="1600"),
        _record(9302, "BC Hydro", "Large General Service (Rate 1600)", "BC", "electricity", "2026-11-01",
                [_component("Energy Charge", 0.0581, effective="2026-04-01")] + surcharges((0.015, 0.025, 0.035), "2026-11-01"),
                "2026-11-01 18:18:18", code="1600"),
    ]
    # A market-following "Variable" price and a $0 price.
    rates.append(_record(9401, TORONTO, "General Service 50 to 999 kW", "ON", "electricity", "2026-01-01", [
        _component("Distribution Volumetric Rate", 4.5, "$/kW", "distribution", effective="2026-01-01"),
        _component("Low Voltage Service Rate", 0.0, "$/kW", "transmission", effective="2026-01-01"),
        _component("Market Energy (Ontario Electricity Market Price + Class B Global Adjustment)", None, "$/kWh",
                   effective="2026-01-01", market_reference="IESO Ontario Electricity Market Price + Class B Global Adjustment"),
    ], "2026-10-07 18:47:54", code="GS50"))
    return rates


RATES = _rates()

REVISIONS = {
    "version": 1, "kind": "rate_history_revisions", "rule": "synthetic",
    "latest_snapshot": {"scrape_run_id": 47, "snapshot_date": "2026-11-20"},
    "revisions": [
        {"utility_name": TORONTO, "province": "ON", "tariff_name": TOU, "tariff_effective_date": "2026-11-01",
         "component_type": "energy", "component_name": "On-Peak Energy", "charge_unit": "$/kWh", "tier_number": None,
         "tou_period": "on-peak", "season": None, "sub_component": None, "effective_date": "2026-11-01", "value": 0.189,
         "revised_on": "2026-11-04", "earlier": [{"value": 0.198, "first_stored": "2026-11-01", "last_stored": "2026-11-03"}]},
        # Its value no longer matches the stored price, so it must not attach.
        {"utility_name": TORONTO, "province": "ON", "tariff_name": TOU, "tariff_effective_date": "2026-11-01",
         "component_type": "energy", "component_name": "Off-Peak Energy", "charge_unit": "$/kWh", "tier_number": None,
         "tou_period": "off-peak", "season": None, "sub_component": None, "effective_date": "2026-11-01", "value": 0.0915,
         "revised_on": "2026-11-05", "earlier": [{"value": 0.09, "first_stored": "2026-11-01", "last_stored": "2026-11-04"}]},
    ],
}


def _quarter(quarter, start, end, months, hours, **measures):
    return {"quarter": quarter, "start": start, "end": end, "months": months, "hours": hours, **measures}


MARKET_ON = {
    "version": 1, "kind": "market_quarterly", "province": "ON", "derivation_method": "observed_quarterly_time_weighted",
    "unit": "$/kWh", "measures": ["energy", "ga_class_b", "total"], "source": "data/market/ontario_market_monthly.csv",
    "weighting": "Each month is weighted by its calendar hours in Eastern Standard Time.", "rule": "synthetic",
    "first_quarter": "2024Q3", "last_quarter": "2025Q3",
    "quarters": [
        _quarter("2024Q3", "2024-07-01", "2024-09-30", ["2024-07", "2024-08", "2024-09"], 2208, energy=0.031245,
                 ga_class_b=0.082, total=0.113245, eras=["hoep"], energy_sources=["hoep_hourly"], ga_sources=["ga_workbook"]),
        _quarter("2024Q4", "2024-10-01", "2024-12-31", ["2024-10", "2024-11", "2024-12"], 2208, energy=0.029,
                 ga_class_b=0.075, total=0.104, eras=["hoep"], energy_sources=["hoep_hourly"], ga_sources=["ga_workbook"]),
        _quarter("2025Q2", "2025-04-01", "2025-06-30", ["2025-04", "2025-05", "2025-06"], 2184, energy=0.052,
                 ga_class_b=0.051, total=0.103, eras=["hoep", "oemp"], energy_sources=["hoep_hourly", "oemp_monthly_table"],
                 ga_sources=["ga_workbook"]),
        _quarter("2025Q3", "2025-07-01", "2025-09-30", ["2025-07", "2025-08", "2025-09"], 2208, energy=0.061,
                 ga_class_b=0.044, total=0.105, eras=["oemp"], energy_sources=["oemp_monthly_table"], ga_sources=["ga_workbook"]),
    ],
}
MARKET_AB = {
    "version": 1, "kind": "market_quarterly", "province": "AB", "derivation_method": "observed_quarterly_time_weighted",
    "unit": "$/kWh", "measures": ["energy"], "source": "data/market/alberta_market_monthly.csv",
    "weighting": "Each month is weighted by its observed AESO pool-price hours.", "rule": "synthetic",
    "first_quarter": "2021Q4", "last_quarter": "2022Q1",
    "quarters": [
        _quarter("2021Q4", "2021-10-01", "2021-12-31", ["2021-10", "2021-11", "2021-12"], 2209, energy=0.0975,
                 source_urls=["http://ets.aeso.ca/oct.html", "http://ets.aeso.ca/nov.html", "http://ets.aeso.ca/dec.html"]),
        _quarter("2022Q1", "2022-01-01", "2022-03-31", ["2022-01", "2022-02", "2022-03"], 2159, energy=0.0902,
                 source_urls=["http://ets.aeso.ca/jan.html", "http://ets.aeso.ca/feb.html", "http://ets.aeso.ca/mar.html"]),
    ],
}


def _point(quarter, without, with_tax, kwh, *, kw=None, in_progress=False, gap=False, reasons=None, available=True):
    return {"quarter": quarter, "in_progress": in_progress, "available": available,
            "without_tax": without if available else None, "with_tax": with_tax if available else None,
            "usage": {"kwh": kwh, "kw": kw, "quantity": None, "unit": None}, "recorded_at": "2026-11-24T16:36:57+00:00",
            "recording_gap": gap, "break_before": None if reasons is None else {"reasons": reasons}}


MODEL_COSTS = {
    "version": 1, "kind": "model_cost_quarterly", "tracking_started_at": "2026-11-17T20:34:27+00:00",
    "last_refresh": {"generated_at": "2026-11-24T16:36:57+00:00", "as_of": "2026-11-24", "method_version": "7T-1"},
    "last_event": "synthetic", "rule": "synthetic", "current_quarter": "2026Q4",
    "series": [
        {"model_id": "ON|electricity|residential|tou|-", "kind": "base", "level_id": "typical", "points": [
            _point("2026Q2", 120.5, 110.25, 1000), _point("2026Q3", 125.0, 114.5, 1000, gap=True),
            _point("2026Q4", 140.0, 128.75, 1200, in_progress=True,
                   reasons=["example customer changed: 1,000 kWh -> 1,200 kWh"])]},
        {"model_id": "ON|electricity|residential|tou|-", "kind": "base", "level_id": "low", "points": [
            _point("2026Q3", 70.0, 66.0, 500), _point("2026Q4", None, None, 500, in_progress=True, available=False)]},
        {"model_id": "ON|electricity|commercial|demand|commercial_medium", "kind": "base", "level_id": "m1", "points": [
            _point("2026Q4", 9100.0, 10283.0, 40000, kw=100, in_progress=True)]},
        {"model_id": "ON|electricity|commercial|demand|commercial_medium", "kind": "benchmark", "level_id": "m1", "points": [
            _point("2026Q4", 14800.0, 16724.0, 40000, kw=100, in_progress=True)]},
    ],
}
ALL_FILES = {"data/rate_history_revisions.json": REVISIONS, "data/market_quarterly_ontario.json": MARKET_ON,
             "data/market_quarterly_alberta.json": MARKET_AB, "data/model_cost_quarterly.json": MODEL_COSTS}


def tariff_hash(province, utility, name, query=""):
    return "#rate-history/tariff/" + "/".join(quote(part, safe="") for part in (province, utility, name)) + query


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture(scope="module")
def models_payload():
    return _builds()["export_like"]


def make_route(documents, missing):
    """Every request answered locally; optional files not supplied answer HTTP 404 (not published yet)."""
    def route(request):
        url = urlparse(request.request.url)
        path = url.path.lstrip("/")
        if url.hostname != "utility.test":
            request.fulfill(content_type="application/javascript", body="")
        elif path in documents and path not in missing:
            request.fulfill(json=documents[path])
        elif path in OPTIONAL or path in missing:
            request.fulfill(status=404, body="Not found")
        elif path.startswith("data/"):
            request.fulfill(json=[] if path in ("data/missing.json", "data/source_review_report.json") else {})
        else:
            file = SITE / (path or "index.html")
            if file.is_file():
                request.fulfill(body=file.read_bytes(), content_type=mimetypes.guess_type(str(file))[0] or "text/plain")
            else:
                request.fulfill(status=404, body="Not found")
    return route


def new_page(browser, models_payload, *, width=1280, rates=None, files=None, missing=(), hash_=""):
    context = browser.new_context(viewport={"width": width, "height": 900}, timezone_id="America/Toronto",
                                  accept_downloads=True)
    context.clock.set_fixed_time(NOW)
    documents = {"data/rates.json": RATES if rates is None else rates, "data/rate_history_series.json": SERIES,
                 "data/rate_history_events.json": EVENTS, "data/representative_models.json": models_payload,
                 "data/model_change_history.json": {}}
    documents.update(ALL_FILES if files is None else files)
    context.route("**/*", make_route(documents, set(missing)))
    page = context.new_page()
    errors = []
    # A deliberately missing optional file is a 404 that Chromium reports as a resource error; anything else fails.
    page.on("console", lambda message: errors.append(message.text) if message.type == "error"
            and not message.text.startswith("Failed to load resource") else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://utility.test/" + hash_)
    expect(page.locator(".rate-card")).not_to_have_count(0)
    return context, page, errors


@pytest.fixture
def open_site(browser, models_payload):
    contexts = []

    def open_page(**options):
        context, page, errors = new_page(browser, models_payload, **options)
        contexts.append(context)
        return page, errors

    yield open_page
    for context in contexts:
        context.close()


def open_tab(page):
    page.locator('[data-view="rate-history"]').click()
    expect(page.locator("#view-rate-history")).to_be_visible()


def no_page_overflow(page):
    return page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def legend_key(page, label):
    button = page.locator("#rh-chart .rh-legend-btn").filter(has_text=re.compile(f"^{re.escape(label)}$"))
    expect(button).to_have_count(1)
    return button.get_attribute("data-line")


def bars(page, key):
    return page.evaluate("""key => [...document.querySelectorAll('#rh-chart .rh-bar')]
        .filter(bar => bar.dataset.line === key).map(bar => [bar.dataset.start || bar.dataset.quarter, Number(bar.dataset.value)])""",
                         key)


def table_row(page, line, period_start):
    return page.locator("#rh-chart .rh-table tbody tr").filter(
        has=page.locator("th", has_text=re.compile(f"^{re.escape(line)}$"))).filter(has_text=period_start)


@pytest.mark.parametrize("width", [1280, 390])
def test_landing_lists_grouped_recent_changes_and_charts_the_newest(open_site, width):
    page, errors = open_site(width=width)
    open_tab(page)
    subtabs = page.locator(".rh-subtab")
    expect(subtabs).to_have_count(4)
    expect(subtabs).to_have_text(["Tariff prices", "Regulated & default", "Market", "Model costs"])
    for index in range(4):
        expect(subtabs.nth(index)).to_have_attribute("aria-pressed", "false")
    items = page.locator(".rh-recent-item")
    expect(items.first).to_contain_text("Nov 1, 2026")
    # Decision 47: the RPP change at every distributor is one line, with old -> new and where.
    off_peak = items.filter(has_text="Ontario Regulated Price Plan: Time-of-Use, Off-peak")
    expect(off_peak).to_have_count(1)
    expect(off_peak).to_contain_text("9.8 \u2192 9.1 \u00a2/kWh (-7.1%)")
    expect(off_peak).to_contain_text("2 utilities")
    expect(items.filter(has_text="Ontario Regulated Price Plan: Mid-peak")).to_have_count(1)
    expect(items.filter(has_text="Tiered, Tier 1")).to_have_count(1)
    expect(items.filter(has_text="Eastward")).to_contain_text("$8.10/GJ \u2192 $9.65/GJ (+19.1%)")
    text = page.locator("#rh-recent").inner_text()
    # Decision 81: a future price joins the list only on its date; noise and repeated descriptions never do.
    assert "Dec 1, 2026" not in text and "10.10" not in text
    assert "Float Noise" not in text and "Conditional Power Factor" not in text and "Customer Charge" not in text
    # Corrections and estimates are never listed.
    assert "ATCO Electric" not in text
    expect(page.locator("#rh-chart .rh-lead")).to_contain_text("Price behind the newest change")
    expect(page.locator("#rh-chart svg.rh-svg").first).to_be_visible()
    assert page.evaluate("location.hash") == "#rate-history"
    if width == 390:
        assert no_page_overflow(page)
    assert not errors


def test_float_noise_is_neither_a_change_nor_a_revision(open_site):
    page, errors = open_site(hash_=tariff_hash("BC", "Float Noise Utility", "Small General Service"))
    expect(page.locator("#rh-chart-title")).to_have_text("Float Noise Utility: Small General Service")
    energy = legend_key(page, "Energy Charge")
    assert [start for start, _ in bars(page, energy)] == ["2026-10-01", "2026-11-01"]
    expect(table_row(page, "Energy Charge", "Nov 1, 2026")).to_contain_text("no change")
    table = page.locator("#rh-chart .rh-table").inner_text()
    assert "revised" not in table
    expect(page.locator("#rh-chart .rh-revised")).to_have_count(0)
    assert not errors


def test_repeated_descriptions_in_one_version_are_never_charted(open_site):
    page, errors = open_site(hash_=tariff_hash("BC", "BC Hydro", "Large General Service (Rate 1600)"))
    expect(page.locator("#rh-chart-title")).to_have_text("BC Hydro: Large General Service (Rate 1600)")
    expect(page.locator("#rh-chart .rh-repeated")).to_contain_text(
        "Not charted: 3 prices share this description in the same tariff version; see the tariff details in the Rate Browser")
    expect(page.locator("#rh-chart .rh-legend-btn")).to_have_text(["Energy Charge"])
    assert "Conditional Power Factor" not in page.locator("#rh-lines").inner_text()
    assert "Conditional Power Factor" not in page.locator("#rh-chart .rh-table").inner_text()
    assert not errors


@pytest.mark.parametrize("width", [1280, 390])
def test_tariff_chooser_search_and_cascade(open_site, width):
    page, errors = open_site(width=width)
    open_tab(page)
    page.locator('.rh-subtab[data-rh-family="tariff"]').click()
    expect(page.locator('.rh-subtab[data-rh-family="tariff"]')).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#rh-recent")).to_be_hidden()
    search = page.locator("#rh-search")
    # Decision 48: utility names only, ignoring accents and capital letters.
    search.fill("\u00c9NERGIR")
    result = page.locator(".rh-search-result")
    expect(result).to_have_text(["Energir (Quebec)"])
    search.fill("energir")
    expect(result).to_have_text(["Energir (Quebec)"])
    result.click()
    expect(page.locator("#rh-province")).to_have_value("QC")
    expect(page.locator("#rh-utility")).to_have_value("Energir")
    expect(page.locator("#rh-chart-title")).to_contain_text("Energir:")
    # An estimate-only utility is never offered (decision 55).
    search.fill("atco electric")
    expect(page.locator("#rh-search-results")).to_contain_text("No utility with live tariff history matches.")
    page.locator("#rh-province").select_option("BC")
    page.locator("#rh-utility").select_option("BC Hydro")
    page.locator("#rh-tariff").select_option(label="Residential Service (Rate 1101)")
    expect(page.locator("#rh-chart-title")).to_have_text("BC Hydro: Residential Service (Rate 1101)")
    expect(page.locator("#rh-lines option").first).to_contain_text("All price lines")
    page.locator("#rh-lines").select_option(label="Step 1 Energy Charge (\u00a2/kWh)")
    expect(page.locator("#rh-chart .rh-legend-btn")).to_have_text(["Step 1 Energy Charge"])
    # Decision 48: a single bar reads "unchanged since we started collecting".
    expect(page.locator("#rh-chart svg .rh-chart-label")).to_have_text("unchanged since we started collecting")
    assert "/tariff/BC/BC%20Hydro/" in page.evaluate("location.hash")
    if width == 390:
        assert no_page_overflow(page)
    assert not errors


@pytest.mark.parametrize("width", [1280, 390])
def test_tariff_chart_periods_legend_percent_and_ranges(open_site, width):
    page, errors = open_site(width=width, hash_=tariff_hash("ON", TORONTO, TOU))
    expect(page.locator("#rh-chart-title")).to_have_text(f"{TORONTO}: {TOU}")
    on_peak = legend_key(page, "On-Peak Energy")
    # Decision 49: one bar per published period, starting at its effective date (the first clipped at the view).
    assert bars(page, on_peak) == [["2025-11-01", 20.3], ["2026-11-01", 18.9]]
    expect(page.locator("#rh-chart .rh-clip-label").first).to_contain_text("Nov 1, 2025")
    expect(table_row(page, "On-Peak Energy", "Nov 1, 2025")).to_contain_text("first collected Oct 7, 2026")
    expect(table_row(page, "On-Peak Energy", "Nov 1, 2026 \u2013 current")).to_contain_text("first collected Nov 1, 2026")
    # Decision 53: the OEB decision of November 1, 2026 is marked, with its official source.
    expect(page.locator('#rh-chart .rh-event[data-event="on-rpp-2026-11-01"]').first).to_be_attached()
    expect(page.locator(f'#rh-chart .rh-events a[href="{OEB_RELEASE}"]')).to_have_count(1)
    # Decision 52: history before September 29, 2026 offers 1Y / 5Y / All.
    ranges = page.locator("#rh-chart .rh-range-btn")
    expect(ranges).to_have_text(["Since Sep 29, 2026", "1Y", "5Y", "All"])
    expect(ranges.first).to_have_attribute("aria-pressed", "true")
    ranges.filter(has_text="All").click()
    expect(page.locator('#rh-chart .rh-range-btn[data-range="all"]')).to_have_attribute("aria-pressed", "true")
    assert "range=all" in page.evaluate("location.hash")
    # Legend switches (decision 49).
    off_peak = legend_key(page, "Off-Peak Energy")
    assert bars(page, off_peak)
    page.locator("#rh-chart .rh-legend-btn").filter(has_text=re.compile("^Off-Peak Energy$")).click()
    expect(page.locator("#rh-chart .rh-legend-btn").filter(has_text=re.compile("^Off-Peak Energy$"))).to_have_attribute(
        "aria-pressed", "false")
    assert bars(page, off_peak) == []
    # Decision 51: % change since the first period shown.
    page.locator("#rh-pct").check()
    expect(page.locator("#rh-chart .rh-table thead")).to_contain_text("% since the first period shown")
    expect(table_row(page, "On-Peak Energy", "Nov 1, 2026 \u2013 current")).to_contain_text("-6.9%")
    assert bars(page, on_peak)[0][1] == 0
    assert "pct=1" in page.evaluate("location.hash")
    if width == 390:
        assert no_page_overflow(page)
    assert not errors


def test_ended_monthly_gas_price_leaves_a_gap_and_future_prices_follow_today(open_site):
    page, errors = open_site(hash_=tariff_hash("AB", "ATCO Gas", "Low Use Delivery Service (North)"))
    rider = legend_key(page, "Default Supply Gas Charge (DERS Rider F)")
    assert bars(page, rider) == [["2026-10-01", 1.458]]
    # Decision 55: the October price ended on October 31 and no newer price is stored: a labelled gap, never extended.
    gap = page.locator("#rh-chart .rh-gap").filter(has=page.locator("title", has_text="No current price stored"))
    expect(gap).not_to_have_count(0)
    expect(page.locator("#rh-chart .rh-gaps")).to_contain_text("no current price stored since Nov 1, 2026")
    expect(table_row(page, "Default Supply Gas Charge (DERS Rider F)", "Nov 1, 2026")).to_contain_text("No current price stored")
    # Other lines of this tariff began before September 29, 2026; the rider alone did not (decision 52).
    expect(page.locator("#rh-chart .rh-range")).to_have_count(1)
    page.locator("#rh-lines").select_option(label="Default Supply Gas Charge (DERS Rider F) ($/GJ)")
    expect(page.locator("#rh-chart .rh-range")).to_have_count(0)
    expect(page.locator("#rh-chart svg .rh-gap-label")).to_have_text(["No current price stored"])

    # Decision 81: a future price is drawn after the "today" marker, labelled "from <date>".
    page.goto("http://utility.test/" + tariff_hash("NS", "Heritage Gas", "General Service"))
    expect(page.locator("#rh-chart-title")).to_have_text("Heritage Gas: General Service")
    page.locator("#rh-lines").select_option(label="Gas Cost Recovery Rate ($/GJ)")
    recovery = legend_key(page, "Gas Cost Recovery Rate")
    assert bars(page, recovery) == [["2026-10-01", 8.1], ["2026-11-01", 9.65], ["2026-12-01", 10.1]]
    expect(page.locator("#rh-chart .rh-today")).to_have_count(1)
    expect(page.locator("#rh-chart svg .rh-bar-label")).to_have_text(["from Dec 1, 2026"])
    expect(table_row(page, "Gas Cost Recovery Rate", "Dec 1, 2026")).to_contain_text("future price")
    assert not errors


def test_a_tariff_version_end_date_ends_its_undated_components(open_site):
    # Decision 55 (correction of 2026-11-24): a component without its own end date ends with its tariff version and is
    # never extended; a version that ends in the future still draws as current.
    ended = _record(9601, "Short Term Electric Co.", "Temporary Rate", "SK", "electricity", "2026-11-01",
                    [_component("Energy Charge", 0.1)], "2026-11-02 10:00:00")
    ended["end_date"] = "2026-11-15"
    running = _record(9602, "Short Term Electric Co.", "Fixed Term Rate", "SK", "electricity", "2026-10-01",
                      [_component("Energy Charge", 0.12, effective="2026-10-01")], "2026-10-02 10:00:00")
    running["end_date"] = "2026-12-31"
    page, errors = open_site(rates=RATES + [ended, running],
                             hash_=tariff_hash("SK", "Short Term Electric Co.", "Temporary Rate"))
    energy = legend_key(page, "Energy Charge")
    assert bars(page, energy) == [["2026-11-01", 10]]
    expect(table_row(page, "Energy Charge", "Nov 1\u201315, 2026")).to_contain_text(
        "ended Nov 15, 2026 (the end date of its tariff version)")
    expect(table_row(page, "Energy Charge", "Nov 16, 2026 \u2013 today")).to_contain_text("No current price stored")
    expect(page.locator("#rh-chart svg .rh-gap-label")).to_have_text(["No current price stored"])
    expect(page.locator("#rh-chart .rh-gaps")).to_contain_text("ended Nov 15, 2026 with its tariff version")
    # The bar stops where the labelled gap begins (November 16).
    bar_end, gap_start = page.evaluate("""() => {
        const bar = document.querySelector('#rh-chart .rh-bar');
        const gap = document.querySelector('#rh-chart .rh-gap');
        return [Number(bar.getAttribute('x')) + Number(bar.getAttribute('width')), Number(gap.getAttribute('x'))];
    }""")
    assert gap_start - 3 < bar_end <= gap_start + 0.01
    page.locator("#rh-tariff").select_option(label="Fixed Term Rate")
    expect(page.locator("#rh-chart-title")).to_have_text("Short Term Electric Co.: Fixed Term Rate")
    expect(page.locator("#rh-chart .rh-gap")).to_have_count(0)
    expect(page.locator("#rh-chart svg .rh-chart-label")).to_have_text("unchanged since we started collecting")
    expect(table_row(page, "Energy Charge", "Oct 1, 2026")).to_contain_text(
        "until Dec 31, 2026 (the end date of its tariff version)")
    assert not errors


def test_variable_prices_are_listed_not_drawn_and_zero_is_a_marker(open_site):
    page, errors = open_site(hash_=tariff_hash("ON", TORONTO, "General Service 50 to 999 kW"))
    variable = page.locator("#rh-chart .rh-variable")
    expect(variable).to_contain_text("Market Energy (Ontario Electricity Market Price + Class B Global Adjustment)")
    expect(page.locator("#rh-chart .rh-legend-btn")).to_have_text(["Distribution Volumetric Rate", "Low Voltage Service Rate"])
    zero = legend_key(page, "Low Voltage Service Rate")
    assert bars(page, zero) == [["2026-01-01", 0]]
    expect(page.locator("#rh-chart .rh-bar-zero")).to_have_count(1)
    variable.get_by_role("button").click()
    expect(page.locator('.rh-subtab[data-rh-family="market"]')).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#rh-market-region")).to_have_value("ON")
    assert not errors


def test_estimates_are_never_charted_and_stale_links_fall_back(open_site):
    page, errors = open_site(hash_=tariff_hash("AB", "ATCO Electric", "Large General Service Distribution (Rate D31)"))
    expect(page.locator("#rh-notice")).to_contain_text("not available")
    expect(page.locator(".rh-recent-item").first).to_be_visible()
    for index in range(4):
        expect(page.locator(".rh-subtab").nth(index)).to_have_attribute("aria-pressed", "false")
    assert page.evaluate("location.hash") == "#rate-history"
    page.goto("http://utility.test/#rate-history/nothing-here")
    expect(page.locator("#rh-notice")).to_contain_text("This link points to a chart that is not available. Showing")
    expect(page.locator("#rh-notice")).not_to_contain_text("ATCO Electric")
    assert not errors


@pytest.mark.parametrize("width", [1280, 390])
def test_regulated_series_chart_with_event_marker_and_source(open_site, width):
    page, errors = open_site(width=width)
    open_tab(page)
    page.locator('.rh-subtab[data-rh-family="regulated"]').click()
    page.locator("#rh-series").select_option("on-rpp-tou")
    expect(page.locator("#rh-chart-title")).to_have_text("Ontario Regulated Price Plan: Time-of-Use")
    expect(page.locator("#rh-chart .rh-legend-btn")).to_have_text(["Off-peak", "Mid-peak", "On-peak"])
    assert bars(page, legend_key(page, "On-peak")) == [["2025-11-01", 20.3], ["2026-11-01", 18.9]]
    expect(page.locator('#rh-chart .rh-event[data-event="on-rpp-2026-11-01"]')).to_have_count(1)
    event = page.locator('#rh-chart .rh-events li[data-event="on-rpp-2026-11-01"]')
    expect(event).to_contain_text("OEB Regulated Price Plan prices change")
    expect(event.locator(f'a[href="{OEB_RELEASE}"]')).to_have_count(1)
    # The 2025 decision is outside the default range and appears with All.
    expect(page.locator('#rh-chart .rh-event[data-event="on-rpp-2025-11-01"]')).to_have_count(0)
    page.locator('#rh-chart .rh-range-btn[data-range="all"]').click()
    expect(page.locator('#rh-chart .rh-event[data-event="on-rpp-2025-11-01"]')).to_have_count(1)
    assert page.evaluate("location.hash") == "#rate-history/regulated/on-rpp-tou?range=all"
    if width == 390:
        assert no_page_overflow(page)
    assert not errors


def test_series_shows_every_differing_value_and_compare_lines(open_site):
    rates = RATES + [_new_rpp_version(TOU, 9501, utility="Split Hydro Inc.", overrides={"On-Peak Energy": 0.19})]
    page, errors = open_site(rates=rates, hash_="#rate-history/regulated/on-rpp-tou")
    expect(page.locator("#rh-chart-title")).to_have_text("Ontario Regulated Price Plan: Time-of-Use")
    values = bars(page, legend_key(page, "On-peak"))
    # Decision 56: values that differ between tariffs are each shown with their count; none is picked.
    assert sorted(value for start, value in values if start == "2026-11-01") == [18.9, 19.0]
    expect(page.locator("#rh-chart .rh-splits")).to_contain_text("18.9 \u00a2/kWh at 3 tariffs; 19.0 \u00a2/kWh at 1 tariff")
    # Decision 49: compare lines in the same unit only, removable.
    page.locator("#rh-chart .rh-compare summary").click()
    page.locator("#rh-cmp-province").select_option("AB")
    page.locator("#rh-cmp-utility").select_option("ENMAX Energy Corporation")
    page.locator("#rh-cmp-tariff").select_option(label="Rate of Last Resort - Residential")
    expect(page.locator("#rh-cmp-line")).to_have_value(re.compile("RoLR Energy Charge"))
    page.locator("#rh-chart .rh-cmp-add").click()
    expect(page.locator("#rh-chart .rh-chip")).to_have_count(1)
    expect(page.locator("#rh-chart .rh-legend-btn").last).to_have_text("ENMAX Energy Corporation: RoLR Energy Charge")
    assert "cmp=AB,ENMAX" in page.evaluate("location.hash")
    page.locator("#rh-cmp-province").select_option("NS")
    page.locator("#rh-cmp-utility").select_option("Heritage Gas")
    expect(page.locator("#rh-cmp-line")).to_contain_text("No price line in the same unit")
    page.locator("#rh-chart .rh-chip-remove").click()
    expect(page.locator("#rh-chart .rh-chip")).to_have_count(0)
    assert not errors


def test_the_compare_panel_stays_open_when_a_redraw_beats_its_toggle_event(open_site):
    # The panel's "toggle" event is asynchronous: a redraw before it runs (here a picker change in the same task, as
    # can happen on a busy machine) must not rebuild the panel closed and hide the pickers.
    page, errors = open_site(hash_="#rate-history/regulated/on-rpp-tou")
    expect(page.locator("#rh-chart-title")).to_have_text("Ontario Regulated Price Plan: Time-of-Use")
    page.evaluate("""() => {
    document.querySelector('#rh-chart .rh-compare summary').click();
    const select = document.querySelector('#rh-cmp-province');
    select.value = 'AB';
    select.dispatchEvent(new Event('change'));
    }""")
    expect(page.locator("#rh-chart .rh-compare")).to_have_attribute("open", "")
    expect(page.locator("#rh-cmp-utility")).to_be_visible()
    expect(page.locator("#rh-cmp-province")).to_have_value("AB")
    assert not errors


@pytest.mark.parametrize("width", [1280, 390])
def test_market_quarters_for_ontario_and_alberta(open_site, width):
    page, errors = open_site(width=width)
    open_tab(page)
    page.locator('.rh-subtab[data-rh-family="market"]').click()
    expect(page.locator("#rh-chart-title")).to_contain_text("Ontario electricity market")
    expect(page.locator("#rh-chart .rh-legend-btn")).to_have_text(["Energy", "Class B GA", "Total (energy + Class B GA)"])
    expect(page.locator("#rh-chart .rh-bar")).to_have_count(12)
    assert bars(page, "energy")[0] == ["2024Q3", 3.1245]
    assert bars(page, "total")[0] == ["2024Q3", 11.3245]
    swatches = page.locator("#rh-chart .rh-legend-btn .rh-swatch").evaluate_all(
        "nodes => nodes.map(node => getComputedStyle(node).backgroundColor)")
    assert swatches == ["rgb(31, 119, 180)", "rgb(44, 160, 44)", "rgb(214, 39, 40)"]
    # A quarter with an incomplete month is a labelled gap, never filled; the market renewal is marked.
    expect(page.locator("#rh-chart .rh-note").filter(has_text="Not available: Q1 2025")).to_have_count(1)
    expect(page.locator('#rh-chart .rh-event[data-event="on-market-renewal"]')).to_have_count(1)
    expect(page.locator("#rh-chart .rh-range")).to_have_count(0)
    expect(page.locator("#rh-chart .rh-table tbody tr").filter(has_text="Q2 2025")).to_contain_text("legacy HOEP and Ontario Price")
    page.locator("#rh-market-region").select_option("AB")
    expect(page.locator("#rh-chart-title")).to_contain_text("Alberta electricity market")
    expect(page.locator("#rh-chart .rh-legend-btn")).to_have_text(["Pool energy"])
    expect(page.locator("#rh-chart .rh-bar")).to_have_count(2)
    expect(page.locator('#rh-chart .rh-table a[href="http://ets.aeso.ca/oct.html"]')).to_have_count(1)
    assert page.evaluate("location.hash") == "#rate-history/market/AB"
    if width == 390:
        assert no_page_overflow(page)
    assert not errors


def test_missing_market_and_model_files_show_a_notice_only_there(open_site):
    page, errors = open_site(files={})
    open_tab(page)
    expect(page.locator(".rh-recent-item").first).to_be_visible()
    expect(page.locator("#rh-chart .rh-revisions-note")).to_have_text("Revision notes are not available yet.")
    page.locator('.rh-subtab[data-rh-family="market"]').click()
    expect(page.locator("#rh-chart")).to_contain_text("Quarterly market history for Ontario is not available yet")
    page.locator('.rh-subtab[data-rh-family="model"]').click()
    expect(page.locator("#rh-chooser")).to_contain_text("Quarterly model costs are not available yet")
    page.locator('.rh-subtab[data-rh-family="regulated"]').click()
    expect(page.locator("#rh-chart svg.rh-svg").first).to_be_visible()
    page.locator('[data-view="rates"]').click()
    expect(page.locator(".rate-card").first).to_be_visible()
    assert not errors


@pytest.mark.parametrize("width", [1280, 390])
def test_model_costs_tax_toggle_progress_and_method_change(open_site, width):
    page, errors = open_site(width=width)
    open_tab(page)
    page.locator('.rh-subtab[data-rh-family="model"]').click()
    expect(page.locator("#rh-model-province")).to_have_value("ON")
    expect(page.locator("#rh-model-structure")).to_have_value("tou")
    expect(page.locator("#rh-model-level")).to_have_value("typical")
    expect(page.locator("#rh-model-tax")).to_have_value("with")
    expect(page.locator("#rh-chart .rh-legend-btn")).to_have_text(["Model cost (median)"])
    # The default range starts at collection (2026Q3); the older 2026Q2 point adds the range buttons.
    assert bars(page, "base") == [["2026Q3", 114.5], ["2026Q4", 128.75]]
    page.locator("#rh-model-tax").select_option("before")
    assert bars(page, "base") == [["2026Q3", 125], ["2026Q4", 140]]
    assert page.evaluate("location.hash") == "#rate-history/model/ON%7Celectricity%7Cresidential%7Ctou%7C-/typical/before"
    # Decision 80: break_before draws a "method changed" gap saying what changed; decision 50: quarter in progress.
    expect(page.locator('#rh-chart .rh-break[data-quarter="2026Q4"]')).to_have_count(1)
    expect(page.locator("#rh-chart .rh-breaks")).to_contain_text("example customer changed: 1,000 kWh -> 1,200 kWh")
    expect(page.locator("#rh-chart")).to_contain_text("quarter in progress")
    expect(page.locator("#rh-chart")).to_contain_text("Recording gap in Q3 2026")
    page.locator('#rh-chart .rh-range-btn[data-range="all"]').click()
    assert bars(page, "base")[0] == ["2026Q2", 120.5]
    # An unavailable level is a labelled gap, never zero.
    page.locator("#rh-model-level").select_option("low")
    expect(page.locator("#rh-chart .rh-note").filter(has_text="Not available (a gap, never zero)")).to_have_count(1)
    assert bars(page, "base") == [["2026Q3", 70]]
    # Market benchmarks are their own series.
    page.locator("#rh-model-segment").select_option("commercial|commercial_medium")
    expect(page.locator("#rh-chart .rh-legend-btn")).to_have_text(["Model cost (median)", "Market benchmark"])
    if width == 390:
        assert no_page_overflow(page)
    assert not errors


def test_revision_note_and_csv_download(open_site):
    page, errors = open_site(hash_=tariff_hash("ON", TORONTO, TOU))
    row = table_row(page, "On-Peak Energy", "Nov 1, 2026 \u2013 current")
    expect(row).to_contain_text("revised on Nov 4, 2026")
    expect(row).to_contain_text("earlier: 19.8 \u00a2/kWh stored Nov 1, 2026 to Nov 3, 2026")
    # A revision whose value no longer matches the stored price never attaches.
    assert "Nov 5, 2026" not in page.locator("#rh-chart .rh-table").inner_text()
    with page.expect_download() as info:
        page.locator("#rh-chart .rh-csv").click()
    download = info.value
    assert download.suggested_filename.endswith(".csv")
    text = Path(download.path()).read_text(encoding="utf-8-sig")
    rows = list(csv.reader(io.StringIO(text)))
    assert rows[0][:8] == ["Chart", "Price line", "Unit as published", "Unit shown", "Period start", "Period end (last day)",
                           "Value as published", "Value shown"]
    on_peak = [row for row in rows if row[1] == "On-Peak Energy"]
    assert [row[4:8] for row in on_peak] == [["2025-11-01", "2026-10-31", "0.203", "20.3"],
                                             ["2026-11-01", "current", "0.189", "18.9"]]
    assert "revised on Nov 4, 2026" in on_peak[1][12]
    assert on_peak[0][11] == "2026-10-07"
    assert not errors


def test_shareable_link_restores_the_chart_on_reload(open_site):
    page, errors = open_site(hash_="#rate-history/regulated/on-rpp-tou?range=all&pct=1")
    expect(page.locator("#view-rate-history")).to_be_visible()
    expect(page.locator("#rh-chart-title")).to_have_text("Ontario Regulated Price Plan: Time-of-Use")
    expect(page.locator("#rh-pct")).to_be_checked()
    expect(page.locator('#rh-chart .rh-range-btn[data-range="all"]')).to_have_attribute("aria-pressed", "true")
    page.locator('.rh-subtab[data-rh-family="tariff"]').click()
    page.locator("#rh-search").fill("heritage")
    page.locator(".rh-search-result").click()
    expect(page.locator("#rh-chart-title")).to_have_text("Heritage Gas: General Service")
    page.reload()
    expect(page.locator("#rh-chart-title")).to_have_text("Heritage Gas: General Service")
    expect(page.locator('.rh-subtab[data-rh-family="tariff"]')).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#rh-pct")).to_be_checked()
    page.locator('[data-view="rates"]').click()
    page.wait_for_function("location.hash === ''")
    assert not errors


def test_history_button_in_the_rate_browser_opens_the_tariff(open_site):
    page, errors = open_site()
    card = page.locator(".rate-card").filter(has=page.locator(".card-title", has_text=re.compile(f"^{re.escape(TOU)}$"))).filter(
        has_text=TORONTO)
    card.locator(".card-title").click()
    page.locator("#modal-content .btn-rate-history").click()
    expect(page.locator("#modal-overlay")).to_be_hidden()
    expect(page.locator("#view-rate-history")).to_be_visible()
    expect(page.locator('.rh-subtab[data-rh-family="tariff"]')).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#rh-chart-title")).to_have_text(f"{TORONTO}: {TOU}")
    expect(page.locator("#rh-lines")).to_have_value("")
    lines = len([c for c in _fixture(TORONTO, TOU)["components"]])
    expect(page.locator("#rh-chart .rh-legend-btn")).to_have_count(lines)
    # Estimates have no History button.
    page.locator('[data-view="rates"]').click()
    page.locator("#toggle-estimated").check()
    page.locator(".rate-card").filter(has_text="ATCO Electric").locator(".card-title").click()
    expect(page.locator("#modal-content")).to_contain_text("Large General Service Distribution")
    expect(page.locator("#modal-content .btn-rate-history")).to_have_count(0)
    assert not errors


def test_the_other_views_still_load(open_site):
    page, errors = open_site(width=390)
    expect(page.locator(".rate-card").first).to_be_visible()
    expect(page.locator(".nav-tab")).to_have_text(["Rate Browser", "Rate History", "Market Pricing", "Representative Models",
                                                   "Across-Canada", re.compile("^Compare")])
    for view in ("rate-history", "market", "models", "across-canada", "compare", "rates"):
        page.locator(f'[data-view="{view}"]').click()
        expect(page.locator(f"#view-{view}")).to_be_visible()
        if view == "across-canada":
            expect(page.locator("#across-content table")).to_be_visible()
        assert no_page_overflow(page), view
    expect(page.locator(".rate-card").first).to_be_visible()
    assert not errors
