"""Observed monthly benchmarks are separate from tariffs and synthetic load estimates."""
from decimal import Decimal

import pytest

from pipeline import representative_models as rm
from scrapers.utils.market_pricing import ALBERTA_METHOD, ROLLING_METHOD, historical_market_price
from tests.test_models_7c import AS_OF, _level, _model, _records, _on_fixture, ON_MEDIUM, AB_MEDIUM, AB_RES


def market_document(province):
    rows = []
    for index in range(2021 * 12 + 9, 2026 * 12 + 9):
        row = {"month": f"{index // 12:04d}-{index % 12 + 1:02d}", "energy_arithmetic": 0.04,
               "total_arithmetic": 0.1 if province == "ON" else 0.04}
        if province == "ON":
            row["ga_class_b"] = 0.06
        rows.append(row)
    return {"metadata": {"schema_version": 2, "province": province, "unit": "$/kWh (CAD)",
                         "derivation_method": ROLLING_METHOD if province == "ON" else ALBERTA_METHOD,
                         "as_of": AS_OF, "sources": [{"url": "https://example.test/observed", "name": "Fixture"}],
                         "window": {"start_month": "2021-10", "end_month": "2026-09", "months": 60}},
            "monthly": rows}


@pytest.mark.parametrize("province,expected", [("ON", 0.1), ("AB", 0.04)])
def test_observed_monthly_mean(province, expected):
    doc = market_document(province)
    result = historical_market_price(doc, province=province, as_of=AS_OF)
    assert result["price_per_kwh"] == pytest.approx(expected)
    doc["monthly"][0]["energy_arithmetic"] += 0.06
    doc["monthly"][0]["total_arithmetic"] += 0.06
    assert historical_market_price(doc, province=province, as_of=AS_OF)["price_per_kwh"] == pytest.approx(
        expected + 0.001)


@pytest.mark.parametrize("bad", ["province", "unit", "method", "schema", "asof", "window", "missing",
                                "duplicate", "nan", "bool", "ga", "total", "sources", "month", "lag"])
def test_invalid_benchmark_evidence_fails_closed(bad):
    doc = market_document("ON")
    meta = doc["metadata"]
    kwargs = {}
    if bad == "province":
        meta["province"] = "AB"
    elif bad == "unit":
        meta["unit"] = "$/MWh"
    elif bad == "method":
        meta["derivation_method"] = "synthetic"
    elif bad == "schema":
        meta["schema_version"] = 1
    elif bad == "asof":
        meta["as_of"] = "2027-01-01"
    elif bad == "window":
        meta["window"]["months"] = 59
    elif bad == "missing":
        doc["monthly"].pop()
    elif bad == "duplicate":
        doc["monthly"][1] = doc["monthly"][0]
    elif bad in ("nan", "bool"):
        doc["monthly"][0]["energy_arithmetic"] = float("nan") if bad == "nan" else True
    elif bad == "ga":
        del doc["monthly"][0]["ga_class_b"]
    elif bad == "total":
        doc["monthly"][0]["total_arithmetic"] = 1
    elif bad == "sources":
        meta["sources"] = []
    elif bad == "month":
        meta["window"]["start_month"] = "2021-13"
    elif bad == "lag":
        kwargs["max_lag_months"] = True
    with pytest.raises(ValueError):
        historical_market_price(doc, province="ON", as_of=AS_OF, **kwargs)


def test_alberta_has_no_global_adjustment_and_window_must_be_complete_and_recent():
    doc = market_document("AB")
    doc["monthly"][0]["ga_class_b"] = 0
    with pytest.raises(ValueError, match="Global Adjustment"):
        historical_market_price(doc, province="AB", as_of=AS_OF)
    del doc["monthly"][0]["ga_class_b"]
    with pytest.raises(ValueError, match="stale"):
        historical_market_price(doc, province="AB", as_of="2027-03-01")
    doc["metadata"]["as_of"] = "2026-09-01"
    with pytest.raises(ValueError, match="incomplete"):
        historical_market_price(doc, province="AB", as_of="2026-09-30")


def test_energy_is_added_per_zone_before_energy_tax_and_rebate():
    inputs = {"zone_rows": {"A": [(100, 10), (200, 20)], "B": [(300, 30)]},
              "applied": [{"name": "Energy tax", "base": "energy_charge_subtotal", "rate": 0.1, "kind": "sales_tax"},
                          {"name": "Rebate", "base": "pre_tax_subtotal", "rate": 0.05, "kind": "rebate"}],
              "not_applied": []}
    out = rm._market_energy_level({"kwh": 1000}, 0.1, inputs)
    assert out["market_energy_cost"] == 100
    assert out["utilities"] == [
        {"utility": "A", "cost_without_tax": 250, "cost_with_tax": 249},
        {"utility": "B", "cost_without_tax": 400, "cost_with_tax": 393}]
    assert out["without_tax"]["median"] == 325
    assert out["with_tax"]["median"] == 321
    assert out["without_tax"]["n"] == 2


def build(documents):
    return rm.build_models(_records() + _on_fixture()["records"],
                           rm.load_crosswalk(), rm.load_usage_levels(), rm.load_taxes(),
                           provinces=("ON", "AB"), as_of=AS_OF, market_document=None,
                           market_documents=documents)


def test_market_benchmarks_do_not_change_base_models_or_rolr():
    base = build({"ON": None, "AB": None})
    result = build({p: market_document(p) for p in ("ON", "AB")})
    for model_id, amount in ((ON_MEDIUM, 4000), (AB_MEDIUM, 1600)):
        model = _model(result, model_id)
        assert model["market_benchmark"]["available"]
        assert not model["market_benchmark"]["profile_backed"]["available"]
        assert model["state"] == "market_energy_pending"
        level = _level(model, "m1")
        benchmark = level["market_benchmark"]
        assert benchmark["available"] and benchmark["market_energy_cost"] == amount
        old = _level(_model(base, model_id), "m1")
        assert level["without_tax"] == old["without_tax"]
        assert level["with_tax"] == old["with_tax"]
        # Base output is rounded; benchmarks aggregate unrounded zone costs.
        difference = (Decimal(str(benchmark["without_tax"]["median"]))
                      - Decimal(str(level["without_tax"]["median"])) - Decimal(amount))
        assert abs(difference) <= Decimal("0.01")
    assert _model(result, AB_RES) == _model(base, AB_RES)
    for model in result["models"]:
        if model["cost_basis"] == "delivery_and_energy":
            assert "market_benchmark" not in model


def test_bad_province_data_only_disables_its_benchmark(caplog):
    bad = market_document("AB")
    bad["metadata"]["unit"] = "$/MWh"
    result = build({"ON": market_document("ON"), "AB": bad})
    assert _model(result, ON_MEDIUM)["market_benchmark"]["available"]
    assert not _model(result, AB_MEDIUM)["market_benchmark"]["available"]
    assert "unavailable" in caplog.text
