"""Parser-to-model checks for the batch 18 municipal utilities (frozen rm_records_b18.json, never the live export).

Owner decision 2026-11-04: they join their province's medians like any registered utility. These tests pin the
structures the engine must read correctly: bi-monthly charges, a two-month energy block, a monthly 'per Billing
Period' block, free demand blocks, kWh-per-kW blocks and disclosed (not applied) percentage riders.
"""
from pathlib import Path

import pytest

from pipeline.representative_models import (build_models, coverage_report, load_block_periods, load_crosswalk,
                                            load_rates, load_taxes, load_usage_levels, record_monthly_cost)

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RECORDS = load_rates(FIXTURES / "rm_records_b18.json")
AS_OF = "2026-11-04"


def _record(utility, code):
    (record,) = [r for r in RECORDS if r["utility_name"] == utility and r["tariff_code"] == code]
    return record


def _cost(record, kwh, kw=None, sector="residential", level=None):
    return record_monthly_cost(record, kwh, kw, sector=sector, usage_levels=load_usage_levels(), as_of=AS_OF,
                               level=level, block_periods=load_block_periods()["entries"])


def test_every_batch18_record_is_mapped_or_excluded():
    report = coverage_report(RECORDS, load_crosswalk())
    assert report["unmapped"] == []
    assert len(RECORDS) == 43


def test_bimonthly_basic_charge_is_halved_and_the_conditional_demand_left_out():
    result = _cost(_record("Nelson Hydro", "A1"), 1000)
    assert result["status"] == "ok"
    assert result["cost"] == pytest.approx(21.29 / 2 + 1000 * 0.1379)
    excluded = {i["component"]: i["reason"] for i in result["items"] if i.get("status") == "excluded"}
    assert excluded == {"Demand Charge — Above 20 kW": "conditional"}


def test_percentage_riders_are_disclosed_not_applied():
    result = _cost(_record("City of New Westminster", "101"), 1000)
    assert result["cost"] == pytest.approx(16.16 / 2 + 1000 * 0.1344)
    reasons = {i["component"]: i["reason"] for i in result["items"] if i.get("status") == "excluded"}
    assert reasons == {"Rate Rider": "percentage_base_not_computable",
                       "Climate Action Levy": "percentage_base_not_computable"}


def test_grand_forks_two_month_block_is_halved():
    result = _cost(_record("City of Grand Forks", "G-2"), 500000, 1000, sector="commercial_large", level="l1")
    assert result["status"] == "ok"
    # 200,000 kWh per two months -> 100,000 kWh a month at the first-block price.
    assert result["cost"] == pytest.approx(29.80 + 100000 * 0.15134 + 400000 * 0.11231)


def test_summerside_blocks_and_free_demand():
    residential = _cost(_record("Summerside Electric", "RES-URBAN"), 2000)
    assert residential["cost"] == pytest.approx(24.57 + 2000 * 0.1784)
    business = _cost(_record("Summerside Electric", "GS1"), 8000, 25, sector="commercial_small", level="s2")
    assert business["cost"] == pytest.approx(24.57 + 5 * 13.43 + 5000 * 0.2188 + 3000 * 0.1438)


def test_saint_john_first_block_is_per_kw_of_billing_demand():
    result = _cost(_record("Saint John Energy", "002"), 40000, 100, sector="commercial_medium", level="m1")
    assert result["cost"] == pytest.approx(25.30 + 100 * 9.76 + 10000 * 0.1568 + 30000 * 0.1217 + 40000 * 0.0039)


def test_new_utilities_join_their_province_medians():
    result = build_models(RECORDS, load_crosswalk(), load_usage_levels(), load_taxes(), provinces=("BC", "NB", "PE"),
                          as_of=AS_OF, market_document=None)
    models = {m["id"]: m for m in result["models"]}
    bc = models["BC|electricity|residential|flat|-"]
    names = {u["utility"] if isinstance(u, dict) else u for level in bc["levels"] for u in level["utilities"]}
    assert {"Nelson Hydro", "City of New Westminster", "City of Penticton", "City of Grand Forks",
            "District of Summerland"} <= names
    assert "NB|electricity|commercial|demand|commercial_medium" in models
