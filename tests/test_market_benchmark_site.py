"""Historical benchmarks stay separate from base and synthetic costs."""
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
