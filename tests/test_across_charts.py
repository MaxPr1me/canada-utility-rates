"""Grouped comparison bars use the same eligible values as the detailed table."""
import pytest
from playwright.sync_api import expect

from tests.test_across_canada import browser, model_template, open_site, payload  # noqa: F401


@pytest.mark.parametrize("basis", ["with_tax", "without_tax"])
def test_chart_costs_colors_and_scale(open_site, payload, basis):
    page, _, errors = open_site(payload)
    page.locator('[data-view="across-canada"]').click()
    expect(page.locator("#across-tax")).to_have_value("with_tax")
    page.select_option("#across-tax", basis)
    expect(page.locator(".across-group")).to_have_count(13)
    colors = {}
    # Across-Canada charts residential electricity only; Phase 7D gas models are never charted there.
    models = [m for m in payload["models"] if m["key"]["sector"] == "residential" and m["key"]["fuel"] == "electricity"]
    for kwh in (500, 1000, 2000):
        page.select_option("#across-usage", str(kwh))
        widths = []
        for model in models:
            province, structure = model["key"]["province"], model["key"]["structure"]
            level = next(lv for lv in model["levels"] if lv["kwh"] == kwh)
            chart = page.locator(f'.across-group[data-province="{province}"] '
                                 f'.across-chart-row[data-structure="{structure}"]')
            amount = level[basis]["median"]
            assert float(chart.locator(".across-bar").get_attribute("data-value")) == pytest.approx(amount)
            formatted = page.evaluate("n => CanadaUtilityModels.money(n)", amount)
            expect(chart.locator(".across-chart-value")).to_have_text(formatted)
            bar = chart.locator(".across-bar")
            color = bar.evaluate("bar => bar.style.backgroundColor")
            key = province, structure
            assert colors.setdefault(key, color) == color
            if amount:
                widths.append(bar.evaluate("bar => parseFloat(bar.style.width)") / amount)
        assert max(widths) == pytest.approx(min(widths))
    for province in {p for p, _ in colors}:
        shades = [color for (p, _), color in colors.items() if p == province]
        assert len(set(shades)) == len(shades)
    assert not errors


def test_missing_cost_is_not_zero_and_real_zero_is_visible(open_site, payload):
    model = next(m for m in payload["models"] if m["key"]["sector"] == "residential" and m["key"]["fuel"] == "electricity")
    province, structure = model["key"]["province"], model["key"]["structure"]
    level = next(lv for lv in model["levels"] if lv["kwh"] == 1000)
    level["with_tax"]["median"] = 0
    page, _, errors = open_site(payload)
    page.locator('[data-view="across-canada"]').click()
    bar = page.locator(f'.across-group[data-province="{province}"] '
                       f'.across-chart-row[data-structure="{structure}"] .across-bar')
    expect(bar).to_have_attribute("data-value", "0")
    assert bar.evaluate("bar => parseFloat(bar.style.width)") == 0
    expect(page.locator('.across-group[data-province="NU"] .across-bar')).to_have_count(0)
    expect(page.locator('.across-group[data-province="NU"]')).to_contain_text("Not modelled yet")
    assert not errors


@pytest.mark.parametrize("width", [390, 1280])
def test_chart_mobile_and_keyboard_controls(open_site, payload, width):
    page, _, errors = open_site(payload, width=width)
    page.locator('[data-view="across-canada"]').click()
    expect(page.locator("#across-chart-title")).to_contain_text("after tax")
    page.locator("#across-tax").focus()
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    expect(page.locator("#across-chart-title")).to_contain_text("before tax")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert not errors
