"""
test_validation.py — Tests for scrapers/utils/validation.py

Covers: validate_tariff, validate_batch, ValidationResult.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from scrapers.base import TariffRecord, RateComponent
from scrapers.utils.validation import validate_tariff, validate_batch, ValidationResult


def _make_tariff(**overrides) -> TariffRecord:
    """Helper to build a well-formed TariffRecord with sensible defaults."""
    defaults = dict(
        utility_name="BC Hydro",
        province="BC",
        utility_type="electricity",
        tariff_name="Residential Service",
        customer_class="residential",
        rate_structure="tiered",
        components=[
            RateComponent(
                component_type="energy",
                component_name="Step 1",
                charge_value=0.0950,
                charge_unit="$/kWh",
            ),
        ],
    )
    defaults.update(overrides)
    return TariffRecord(**defaults)


# ─── Valid tariff ────────────────────────────────────────────────

class TestValidTariff:
    def test_valid_tariff_passes(self):
        record = _make_tariff()
        result = validate_tariff(record)
        assert result.is_valid is True
        assert result.errors == []

    def test_valid_tariff_result_type(self):
        result = validate_tariff(_make_tariff())
        assert isinstance(result, ValidationResult)


# ─── Missing required fields ────────────────────────────────────

class TestMissingFields:
    def test_missing_utility_name(self):
        record = _make_tariff(utility_name="")
        result = validate_tariff(record)
        assert result.is_valid is False
        assert any("utility_name" in e for e in result.errors)

    def test_missing_province(self):
        record = _make_tariff(province="")
        result = validate_tariff(record)
        assert result.is_valid is False
        assert any("province" in e for e in result.errors)

    def test_missing_tariff_name(self):
        record = _make_tariff(tariff_name="")
        result = validate_tariff(record)
        assert result.is_valid is False
        assert any("tariff_name" in e for e in result.errors)

    def test_invalid_utility_type(self):
        record = _make_tariff(utility_type="water")
        result = validate_tariff(record)
        assert result.is_valid is False
        assert any("utility_type" in e for e in result.errors)


# ─── No components ──────────────────────────────────────────────

class TestNoComponents:
    def test_no_components_fails(self):
        record = _make_tariff(components=[])
        result = validate_tariff(record)
        assert result.is_valid is False
        assert any("no rate components" in e.lower() for e in result.errors)


# ─── Absurd rate value ──────────────────────────────────────────

class TestAbsurdRate:
    def test_absurd_rate_value_fails(self):
        """$100/kWh exceeds ELECTRICITY_MAX (5.0) and should produce an error."""
        record = _make_tariff(
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="Absurd Energy Rate",
                    charge_value=100.0,
                    charge_unit="$/kWh",
                ),
            ]
        )
        result = validate_tariff(record)
        assert result.is_valid is False
        assert any("unreasonably high" in e.lower() for e in result.errors)


# ─── Negative rebate ────────────────────────────────────────────

class TestNegativeRebate:
    def test_negative_rebate_ok(self):
        """A negative charge_value with component_type='rebate' should NOT be
        an error.  It may produce a warning or no warning, but the record
        must remain valid."""
        record = _make_tariff(
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="Base Energy",
                    charge_value=0.10,
                    charge_unit="$/kWh",
                ),
                RateComponent(
                    component_type="rebate",
                    component_name="Clean Energy Rebate",
                    charge_value=-0.02,
                    charge_unit="$/kWh",
                ),
            ]
        )
        result = validate_tariff(record)
        assert result.is_valid is True
        # No error about negative value for the rebate component
        assert not any("negative" in e.lower() for e in result.errors)

    def test_negative_non_rebate_warns(self):
        """A negative value on a non-rebate component should produce a warning."""
        record = _make_tariff(
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="Oddly Negative Energy",
                    charge_value=-0.05,
                    charge_unit="$/kWh",
                ),
            ]
        )
        result = validate_tariff(record)
        # Still valid (warnings don't invalidate), but should warn
        assert result.is_valid is True
        assert any("negative" in w.lower() for w in result.warnings)


# ─── validate_batch ─────────────────────────────────────────────

class TestValidateBatch:
    def test_separates_valid_and_invalid(self):
        good = _make_tariff()
        bad = _make_tariff(utility_name="", tariff_name="Missing Name")

        valid, invalid = validate_batch([good, bad])
        assert len(valid) == 1
        assert len(invalid) == 1
        assert valid[0].utility_name == "BC Hydro"
        assert invalid[0].tariff_name == "Missing Name"

    def test_all_valid(self):
        records = [_make_tariff(), _make_tariff(tariff_name="Another Tariff")]
        valid, invalid = validate_batch(records)
        assert len(valid) == 2
        assert len(invalid) == 0

    def test_all_invalid(self):
        records = [_make_tariff(utility_name=""), _make_tariff(components=[])]
        valid, invalid = validate_batch(records)
        assert len(valid) == 0
        assert len(invalid) == 2

    def test_empty_batch(self):
        valid, invalid = validate_batch([])
        assert valid == []
        assert invalid == []
