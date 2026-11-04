"""Phase 7D residential gas models (method 7D-1, owner decision 2026-11-04).

Residential default utility supply only, priced in each utility's native billing unit: m3 utilities at
100/200/400 m3 a month and GJ utilities at 4/8/16 GJ a month, never converted or merged. Commercial, contract
and interruptible gas models are withheld until their scenarios are approved. The inputs are frozen latest live
records from the 2026-11-01 export (tests/fixtures/rm_records_7d_gas.json), so these tests never depend on the
live export.
"""
import copy
import json
import re
from pathlib import Path

import pytest

from pipeline import representative_models as rm

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "rm_records_7d_gas.json"
AS_OF = "2026-11-04"
M3_LEVELS = {"m3_low": 100.0, "m3_reference": 200.0, "m3_high": 400.0}
GJ_LEVELS = {"gj_low": 4.0, "gj_reference": 8.0, "gj_high": 16.0}


def _records() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["records"]


def _build(records=None) -> dict:
    return rm.build_models(records if records is not None else _records(), rm.load_crosswalk(),
                           rm.load_usage_levels(), rm.load_taxes(), provinces=None, fuels=("gas",), as_of=AS_OF,
                           block_periods=[], market_document=None)


@pytest.fixture(scope="module")
def built() -> dict:
    return _build()


def _model(result: dict, model_id: str) -> dict:
    return next(m for m in result["models"] if m["id"] == model_id)


def test_gas_levels_are_the_approved_native_unit_sets():
    levels = rm.load_usage_levels()["gas"]["residential"]
    by_unit = {unit: {lv["id"]: lv["quantity"] for lv in levels if lv["unit"] == unit} for unit in ("m3", "GJ")}
    assert by_unit == {"m3": M3_LEVELS, "GJ": GJ_LEVELS}
    assert all("kwh" not in lv and "kw" not in lv for lv in levels)
    references = [lv for lv in levels if lv["role"] == "reference"]
    assert {lv["id"] for lv in references} == {"m3_reference", "gj_reference"}
    assert all(lv["source_url"].startswith("https://") and lv["basis"] for lv in references)
    assert {lv["role"] for lv in levels if lv["id"] not in ("m3_reference", "gj_reference")} == {"sensitivity"}


@pytest.mark.parametrize("unit, volume, expected", [
    ("$/m³", "m3", ("kwh", 1.0, [])),
    ("$/m3", "m3", ("kwh", 1.0, [])),
    ("$/GJ", "GJ", ("kwh", 1.0, [])),
    ("$/GJ", "m3", None),
    ("$/m³", "GJ", None),
    ("$/kWh", "m3", None),
    ("$/m³/month", "m3", None),
    ("$/metering device/day", "m3", None),
])
def test_price_basis_accepts_only_the_models_own_volume_unit(unit, volume, expected):
    assert rm.price_basis({"charge_unit": unit}, volume_unit=volume) == expected


def test_fixed_charges_and_electricity_units_are_unchanged():
    assert rm.price_basis({"charge_unit": "$/day"}, volume_unit="GJ")[0:2] == ("month", rm.DEFAULT_DAYS_PER_MONTH)
    assert rm.price_basis({"charge_unit": "$/month"}, volume_unit="m3") == ("month", 1.0, [])
    assert rm.price_basis({"charge_unit": "$/kWh"}) == ("kwh", 1.0, [])
    assert rm.price_basis({"charge_unit": "$/m³"}) is None


def test_gas_volume_unit_requires_one_native_unit():
    m3 = {"components": [{"charge_unit": "$/m³"}, {"charge_unit": "$/month"}]}
    gj = {"components": [{"charge_unit": "$/GJ"}, {"charge_unit": "$/day"}]}
    assert rm.gas_volume_unit([m3]) == "m3"
    assert rm.gas_volume_unit([gj]) == "GJ"
    assert rm.gas_volume_unit([m3, gj]) is None
    assert rm.gas_volume_unit([{"components": [{"charge_unit": "$/month"}]}]) is None


def test_each_province_uses_its_native_unit_levels(built):
    expected_units = {"ON": "m3", "MB": "m3", "SK": "m3", "QC": "m3", "BC": "GJ", "AB": "GJ", "NS": "GJ", "NB": "GJ"}
    gas = [m for m in built["models"] if m["key"]["fuel"] == "gas"]
    assert {m["key"]["province"] for m in gas} == set(expected_units)
    for model in gas:
        unit = expected_units[model["key"]["province"]]
        ids = M3_LEVELS if unit == "m3" else GJ_LEVELS
        assert {lv["id"]: lv["quantity"] for lv in model["levels"]} == ids
        assert all(lv["unit"] == unit and lv["kwh"] is None and lv["kw"] is None for lv in model["levels"])
        first = "m3_low 100 m³/month" if unit == "m3" else "gj_low 4 GJ/month"
        assert first in str(model["method"]) and " kWh/month" not in str(model["method"])


def test_saskenergy_cost_is_the_sum_of_its_published_components(built):
    model = _model(built, "SK|gas|residential|flat|-")
    assert model["state"] == "single_source" and model["cost_basis"] == "delivery_and_energy"
    # Basic Monthly Charge $26.50 + (commodity 0.1264 + delivery 0.1113 + carbon 0.0) $/m3, as published.
    for level in model["levels"]:
        expected = 26.5 + (0.1264 + 0.1113 + 0.0) * level["quantity"]
        assert level["without_tax"]["median"] == pytest.approx(round(expected, 2), abs=0.005)
        assert level["with_tax"]["median"] > level["without_tax"]["median"]


def test_ontario_models_follow_the_offered_structures(built):
    tiered = _model(built, "ON|gas|residential|tiered|-")
    flat = _model(built, "ON|gas|residential|flat|-")
    assert tiered["coverage"]["contributing_utilities"] == ["EPCOR Natural Gas (Ontario)", "Enbridge Gas"]
    assert tiered["state"] == "modeled" and "Enbridge Gas" in tiered["coverage"]["multi_zone_utilities"]
    assert flat["coverage"]["contributing_utilities"] == ["EPCOR Natural Gas (Ontario)"]
    assert flat["state"] == "single_source"
    for model in (tiered, flat):
        assert model["cost_basis"] == "delivery_and_energy"
        costs = [lv["without_tax"]["median"] for lv in model["levels"]]
        assert costs == sorted(costs) and all(cost > 0 for cost in costs)


def test_unsupported_or_optional_supply_fails_closed(built):
    quebec = _model(built, "QC|gas|residential|tiered|-")
    assert quebec["state"] == "not_computable"
    assert any("$/metering device/day" in str(e.get("reason")) for e in quebec["exclusions"])
    new_brunswick = _model(built, "NB|gas|residential|flat|-")
    assert new_brunswick["state"] == "not_computable"
    assert any("none is unconditional" in str(e.get("reason")) for e in new_brunswick["exclusions"])
    assert all(lv["without_tax"]["median"] is None for model in (quebec, new_brunswick) for lv in model["levels"])


def test_excluded_products_never_contribute(built):
    used = {record_id for model in built["models"] for lv in model["levels"] for row in lv["utilities"]
            for record_id in row["records"]}
    names = {r["id"]: r["name"] for r in _records()}
    assert not [names[i] for i in used if re.search(r"propane|RNG|Customer Choice|Marketer|Delivery Service$|"
                                                   r"Alternative Technology", names[i])]


def test_commercial_gas_models_are_withheld(built):
    assert not [m for m in built["models"] if m["key"]["fuel"] == "gas" and m["key"]["sector"] != "residential"]
    withheld = built["input"]["withheld_gas_models"]
    assert any(label.startswith("BC|gas|commercial") for label in withheld["models"])
    assert "2026-11-04" in withheld["reason"]


def test_mixed_volume_units_make_the_model_not_computable():
    records = copy.deepcopy(_records())
    sk = next(r for r in records if r["utility_name"] == "SaskEnergy" and r["tariff_code"] == "Res")
    sk["components"].append({**sk["components"][0], "component_name": "Injected GJ charge", "charge_unit": "$/GJ",
                             "charge_value": 1.0})
    model = _model(_build(records), "SK|gas|residential|flat|-")
    assert model["levels"] == [] and model["state"] == "not_computable"
    assert any("one native volume unit" in str(e.get("reason")) for e in model["exclusions"])


def test_across_canada_view_stays_residential_electricity():
    script = (ROOT / "site" / "js" / "across-canada.js").read_text(encoding="utf-8")
    assert 'model.key.fuel === "electricity"' in script
