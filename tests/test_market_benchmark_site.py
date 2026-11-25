"""Historical benchmarks and the opt-in simulated estimate stay separate from base costs."""
import pytest
from playwright.sync_api import expect

from tests.test_across_canada import browser, model_template, open_site, payload  # noqa: F401


def add_benchmark(payload, available=True, province="ON"):
    model = next(m for m in payload["models"] if m["key"]["province"] == "ON"
                 and m["key"]["size_band"] == "commercial_medium")
    model["state"] = "market_energy_pending"
    model["cost_basis"] = "delivery_only_market_energy_pending"
    model["key"]["province"] = province
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
            "market_energy_per_kwh": 0.1, "market_energy_cost": 4000,
            "without_tax": {"median": 6000, "n": 2}, "with_tax": {"median": 6780, "n": 2},
        }
    return model


@pytest.mark.parametrize("available", [True, False])
@pytest.mark.parametrize("province", ["ON", "AB"])
def test_benchmark_display_and_unavailable_reason(open_site, payload, available, province):
    add_benchmark(payload, available, province)
    page, _, errors = open_site(payload)
    page.locator('[data-view="models"]').click()
    page.select_option("#models-province", province)
    page.select_option("#models-segment", "commercial|commercial_medium")
    block = page.locator(".rm-benchmark")
    expect(block).to_contain_text("not a bill")
    expect(block).to_contain_text("Real customer-profile cost unavailable")
    expect(block).to_contain_text("Retail fees and losses")
    if available:
        expect(block).to_contain_text("$6,780.00")
        expect(block).to_contain_text("mean of 60 months")
        if province == "AB":
            expect(block).to_contain_text("2 wires utilities")
        expect(block.locator('a[href="https://example.test/price"]')).to_have_count(1)
        expect(block.locator("details.rm-details summary")).to_have_text("Sources (1)")
    else:
        expect(block).to_contain_text("Missing observed history")
        assert "$6,780" not in block.inner_text()
    assert block.locator('a[href^="javascript:"]').count() == 0
    page.select_option("#models-province", "ON")
    page.select_option("#models-segment", "residential")
    expect(page.locator(".rm-benchmark")).to_have_count(0)
    assert not errors


def test_wrong_province_cannot_display_benchmark_amounts(open_site, payload):
    model = add_benchmark(payload)
    model["market_benchmark"]["province"] = "AB"
    page, _, errors = open_site(payload)
    page.locator('[data-view="models"]').click()
    page.select_option("#models-segment", "commercial|commercial_medium")
    expect(page.locator(".rm-benchmark")).to_contain_text("No valid benchmark")
    assert "$6,780" not in page.locator(".rm-benchmark").inner_text()
    assert not errors


def add_simulated(payload, province):
    """Method 7S-1: the opt-in market energy estimate priced with simulated building load shapes."""
    model = add_benchmark(payload, True, province)
    model["illustrative"] = {
        "available": True, "reason": None, "simulated": True, "caveat": "Simulated buildings, not metered customers.",
        "method": "Median of the simulated buildings' market energy prices.",
        "window": {"start_month": "2021-11", "end_month": "2026-10", "months": 60}, "price_per_kwh": 0.108,
        "buildings": [{"datapoint_id": "run-1", "building_type": "<img src=x onerror=alert(1)>MediumOffice",
                       "heating_fuel": "NaturalGas", "city": "Toronto", "average_monthly_peak_kw": 150.5,
                       "kwh_per_kw": 253.9, "quality_flag": True, "price_per_kwh": 0.108}]}
    for level in model["levels"]:
        level["illustrative_all_in"] = {
            "simulated_profile": True, "illustrative_only": True, "market_energy_per_kwh": 0.108,
            "market_energy_cost": 4320, "market_energy_range": {"min_per_kwh": 0.105, "max_per_kwh": 0.114,
                                                                "min_cost": 4200, "max_cost": 4560, "buildings": 1},
            "without_tax": {"median": 6200, "n": 2, "min": 6100, "max": 6300},
            "with_tax": {"median": 7006, "n": 2, "min": 6893, "max": 7119}}
    return model


@pytest.mark.parametrize("province,width", [("ON", 1280), ("AB", 390)])
def test_simulated_estimate_appears_only_while_ticked_and_lists_its_buildings_as_text(open_site, payload, province,
                                                                                      width):
    add_simulated(payload, province)
    page, _, errors = open_site(payload, width=width)
    page.locator('[data-view="models"]').click()
    page.select_option("#models-province", province)
    page.select_option("#models-segment", "commercial|commercial_medium")
    toggle = page.locator("#models-illustrative-toggle")
    expect(toggle).not_to_be_checked()
    expect(page.locator(".rm-illus")).to_have_count(0)
    assert "$7,006" not in page.locator("#models-notes").inner_text()
    toggle.check()
    block = page.locator(".rm-illus")
    expect(block.locator(".rm-illus-badge")).to_have_text("SIMULATED")
    expect(block).to_contain_text("SIMULATED LOAD SHAPES - MARKET ENERGY ESTIMATE, NOT A BILL")
    expect(block).to_contain_text("$7,006.00")
    expect(block).to_contain_text("1 building, 10.50 to 11.40 cents/kWh")
    buildings = block.locator("details.rm-illus-buildings")
    buildings.locator("summary").click()
    expect(buildings).to_contain_text("Simulated buildings used (1, Toronto)")
    expect(buildings).to_contain_text("Natural gas")
    expect(buildings).to_contain_text("More than 300 occupied hours")
    assert block.locator("img").count() == 0
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    toggle.uncheck()
    expect(page.locator(".rm-illus")).to_have_count(0)
    assert not errors
