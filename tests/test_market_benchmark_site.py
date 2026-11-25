"""The market energy note (method 7S-2, owner decisions 119-123, 2026-11-25): estimated energy is labelled and stated,
a failed estimate falls back to delivery charges only, and the same-use-every-hour benchmark is a comparison only."""
import pytest
from playwright.sync_api import expect

from tests.test_across_canada import browser, model_template, open_site, payload  # noqa: F401


def add_benchmark(payload, available=True, province="ON"):
    model = next(m for m in payload["models"] if m["key"]["province"] == "ON"
                 and m["key"]["size_band"] == "commercial_medium")
    model["state"] = "market_energy_pending"
    model["cost_basis"] = "delivery_only_market_energy_pending"
    model["key"]["province"] = province
    if province == "AB":
        model["coverage"]["contributor_noun"] = {"singular": "service area", "plural": "service areas"}
    model["market_benchmark"] = {
        "available": available, "province": province, "reason": None if available else "Missing observed history",
        "window": {"start_month": "2021-10", "end_month": "2026-09", "months": 60},
        "method": "Equal-month historical average, not customer-weighted.",
        "exclusions": ["Retail fees and losses"], "sources": [
            {"url": "https://example.test/price", "name": "Official price"},
            {"url": "javascript:alert(1)", "name": "Bad link"}],
        "profile_backed": {"available": False, "reason": "No qualified commercial profile"},
    }
    for level in model["levels"]:
        level["market_benchmark"] = {
            "available": available, "reason": None if available else "Missing observed history",
            "market_energy_per_kwh": 0.1, "market_energy_cost": 2500,
            "without_tax": {"median": 6000, "n": 2}, "with_tax": {"median": 6780, "n": 2},
        }
    return model


def add_estimate(payload, province="ON", available=True):
    """An estimated model as the engine publishes it (state, cost basis, model and level fields)."""
    model = add_benchmark(payload, True, province)
    model["energy_estimate"] = {
        "available": available, "reason": None if available else "stale market history: the window ends 2026-05",
        "input_problem": not available, "profile_id": "BTAP_NECB2020_BAND_GENERAL_SHAPE", "price_per_kwh": 0.108,
        "flat_price_per_kwh": 0.1, "price_range": {"min": 0.105, "max": 0.114},
        "window": {"start_month": "2021-11", "end_month": "2026-10", "months": 60},
        "shape": {"buildings": 1, "cities": ["Toronto"]},
        "assumptions": ["Estimated, not live: assumption text.", "<b>Load shape</b> as text"],
        "buildings": [{"datapoint_id": "run-1", "building_type": "<img src=x onerror=alert(1)>MediumOffice",
                       "heating_fuel": "NaturalGas", "city": "Toronto", "average_monthly_peak_kw": 150.5,
                       "kwh_per_kw": 253.9, "quality_flag": True, "price_per_kwh": 0.108}]}
    if available:
        model["state"] = "market_energy_estimated"
        model["cost_basis"] = "delivery_and_estimated_market_energy"
        for level in model["levels"]:
            level["market_energy_estimate"] = {"price_per_kwh": 0.108, "cost": 2700}
            level["without_tax"]["median"] = 6200
            level["with_tax"]["median"] = 7006
    return model


def open_model(open_site, payload, province, width=1280):
    page, _, errors = open_site(payload, width=width)
    page.locator('[data-view="models"]').click()
    page.select_option("#models-province", province)
    page.select_option("#models-segment", "commercial|commercial_medium")
    return page, errors


@pytest.mark.parametrize("province,width", [("ON", 1280), ("AB", 390)])
def test_estimated_energy_is_labelled_in_the_table_and_explained_in_an_always_visible_note(open_site, payload,
                                                                                         province, width):
    add_estimate(payload, province)
    page, errors = open_model(open_site, payload, province, width)
    expect(page.locator("#models-badge")).to_contain_text("with estimated market energy")
    expect(page.locator("#models-table-wrap caption")).to_contain_text("Includes estimated market energy, not live")
    expect(page.locator("#models-table-wrap tbody tr").first.locator(".rm-tag-estimated")).to_have_text(
        "Estimated energy")
    expect(page.locator("#models-table-wrap")).to_contain_text("$7,006.00")
    note = page.locator(".rm-energy")
    expect(note.locator(".rm-energy-badge")).to_have_text("Estimated")
    expect(note).to_contain_text("10.80 cents/kWh: the general load shape of 1 simulated buildings")
    expect(note).to_contain_text("November 2021 to October 2026")
    expect(note).to_contain_text("$2,700.00 a month")
    expect(note).to_contain_text("10.00 cents/kWh, $2,500.00 a month: median $6,000.00 before tax and rebates, "
                                 "$6,780.00 with tax and rebates")
    expect(note).to_contain_text("10.50 to 11.40 cents/kWh")
    expect(note).to_contain_text("<b>Load shape</b> as text")
    assert note.locator("b").count() == 0 and note.locator("img").count() == 0
    buildings = note.locator("details.rm-energy-buildings")
    buildings.locator("summary").click()
    expect(buildings).to_contain_text("Simulated buildings used (1, Toronto)")
    expect(buildings).to_contain_text("Natural gas")
    expect(buildings).to_contain_text("More than 300 occupied hours")
    expect(note.locator('a[href="https://example.test/price"]')).to_have_count(1)
    assert note.locator('a[href^="javascript:"]').count() == 0
    expect(page.locator("#models-illustrative-toggle")).to_have_count(0)
    expect(page.locator(".rm-benchmark")).to_have_count(0)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    page.select_option("#models-province", "ON")
    page.select_option("#models-segment", "residential")
    expect(page.locator(".rm-energy")).to_have_count(0)
    assert not errors


@pytest.mark.parametrize("benchmark", [True, False])
def test_a_failed_estimate_says_why_and_shows_delivery_charges_only(open_site, payload, benchmark):
    model = add_estimate(payload, "ON", available=False)
    if not benchmark:
        model["market_benchmark"]["available"] = False
    page, errors = open_model(open_site, payload, "ON")
    expect(page.locator("#models-badge")).to_have_text("Delivery charges only: market energy pending")
    note = page.locator(".rm-energy")
    expect(note).to_contain_text("Estimated market energy unavailable: stale market history: the window ends "
                                 "2026-05. The table shows delivery charges only (market energy pending), never a "
                                 "guessed energy price.")
    expect(note.locator(".rm-energy-badge")).to_have_count(0)
    text = note.inner_text()
    assert "10.80" not in text and "Simulated buildings" not in text and "Estimated, not live" not in text
    assert ("$6,780.00" in text) is benchmark
    expect(page.locator("#models-table-wrap .rm-tag-estimated")).to_have_count(0)
    assert not errors


def test_a_pending_model_without_an_estimate_shows_only_a_usable_benchmark(open_site, payload):
    add_benchmark(payload, True, "AB")
    page, errors = open_model(open_site, payload, "AB")
    note = page.locator(".rm-energy")
    expect(note).to_contain_text("The table shows delivery charges only (market energy pending)")
    expect(note).to_contain_text("historical market benchmark across 2 service areas")
    expect(note.locator("details.rm-details summary")).to_have_text("Sources (1)")
    assert not errors


def test_wrong_province_or_unflagged_values_never_display_amounts(open_site, payload):
    model = add_estimate(payload, "ON")
    model["market_benchmark"]["province"] = "AB"
    for level in model["levels"]:
        level.pop("market_energy_estimate")
    page, errors = open_model(open_site, payload, "ON")
    note = page.locator(".rm-energy")
    expect(note).to_contain_text("The details of this model's estimated market energy are not available.")
    text = note.inner_text()
    assert "$6,780" not in text and "10.80" not in text and "$2,700" not in text
    assert not errors
