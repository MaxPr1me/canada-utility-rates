"""
test_change_detection.py — Tests for scrapers/utils/change_detection.py

Covers: compare_to_seed, log_change_alerts, has_critical_alerts,
        severity classification, record pairing, component matching.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from scrapers.base import TariffRecord, RateComponent
from scrapers.utils.change_detection import (
    compare_to_seed,
    log_change_alerts,
    has_critical_alerts,
    ChangeAlert,
    _classify_severity,
    _match_key,
)


def _make_tariff(name="Residential Service", code="1101", cls="residential",
                 components=None, **overrides) -> TariffRecord:
    """Helper to build a TariffRecord for testing."""
    defaults = dict(
        utility_name="Test Utility",
        province="BC",
        utility_type="electricity",
        tariff_name=name,
        tariff_code=code,
        customer_class=cls,
        rate_structure="tiered",
        components=components or [],
    )
    defaults.update(overrides)
    return TariffRecord(**defaults)


def _make_comp(name="Energy Charge", ctype="energy", value=0.10, unit="$/kWh",
               **overrides) -> RateComponent:
    """Helper to build a RateComponent for testing."""
    defaults = dict(
        component_type=ctype,
        component_name=name,
        charge_value=value,
        charge_unit=unit,
    )
    defaults.update(overrides)
    return RateComponent(**defaults)


# ─── Severity classification ─────────────────────────────────────

class TestClassifySeverity:
    def test_small_pct_is_info(self):
        assert _classify_severity(3.0, 0.01) == "info"

    def test_medium_pct_is_warning(self):
        assert _classify_severity(15.0, 0.02) == "warning"

    def test_large_pct_is_critical(self):
        assert _classify_severity(50.0, 0.05) == "critical"

    def test_large_pct_but_tiny_abs_is_info(self):
        # 100% change but only $0.001 absolute — not worth flagging
        assert _classify_severity(100.0, 0.001) == "info"

    def test_boundary_at_5pct(self):
        assert _classify_severity(4.9, 0.01) == "info"
        assert _classify_severity(5.1, 0.01) == "warning"

    def test_boundary_at_30pct(self):
        assert _classify_severity(29.9, 0.02) == "warning"
        assert _classify_severity(30.1, 0.02) == "critical"


# ─── Record pairing ─────────────────────────────────────────────

class TestMatchKey:
    def test_uses_code_name_class(self):
        rec = _make_tariff(name="Res", code="1101", cls="residential")
        key = _match_key(rec)
        assert "1101" in key
        assert "res" in key
        assert "residential" in key

    def test_handles_none_code(self):
        rec = _make_tariff(name="Res", code=None, cls="residential")
        key = _match_key(rec)
        assert "res" in key


# ─── Identical records produce no meaningful alerts ──────────────

class TestIdenticalRecords:
    def test_identical_records_no_alerts(self):
        comp = _make_comp(value=0.0950)
        live = [_make_tariff(components=[comp])]
        seed = [_make_tariff(components=[comp])]
        alerts = compare_to_seed(live, seed)
        # Should be empty or all info with 0% change
        assert not has_critical_alerts(alerts)
        assert all(a.severity == "info" for a in alerts)

    def test_empty_records(self):
        alerts = compare_to_seed([], [])
        assert alerts == []

    def test_empty_live(self):
        seed = [_make_tariff(components=[_make_comp()])]
        alerts = compare_to_seed([], seed)
        assert alerts == []

    def test_empty_seed(self):
        live = [_make_tariff(components=[_make_comp()])]
        alerts = compare_to_seed(live, [])
        assert alerts == []


# ─── Small changes produce info ─────────────────────────────────

class TestSmallChanges:
    def test_2pct_change_is_info(self):
        seed_comp = _make_comp(value=0.1000)
        live_comp = _make_comp(value=0.1020)  # 2% increase
        seed = [_make_tariff(components=[seed_comp])]
        live = [_make_tariff(components=[live_comp])]
        alerts = compare_to_seed(live, seed)
        assert not has_critical_alerts(alerts)
        value_alerts = [a for a in alerts if a.pct_change is not None]
        assert all(a.severity == "info" for a in value_alerts)


# ─── Moderate changes produce warnings ──────────────────────────

class TestModerateChanges:
    def test_20pct_change_is_warning(self):
        seed_comp = _make_comp(value=0.1000)
        live_comp = _make_comp(value=0.1200)  # 20% increase
        seed = [_make_tariff(components=[seed_comp])]
        live = [_make_tariff(components=[live_comp])]
        alerts = compare_to_seed(live, seed)
        value_alerts = [a for a in alerts if a.pct_change is not None]
        assert any(a.severity == "warning" for a in value_alerts)
        assert not has_critical_alerts(alerts)


# ─── Large changes produce critical alerts ──────────────────────

class TestLargeChanges:
    def test_50pct_change_is_critical(self):
        seed_comp = _make_comp(value=0.1000)
        live_comp = _make_comp(value=0.1600)  # 60% increase
        seed = [_make_tariff(components=[seed_comp])]
        live = [_make_tariff(components=[live_comp])]
        alerts = compare_to_seed(live, seed)
        assert has_critical_alerts(alerts)

    def test_decrease_also_critical(self):
        seed_comp = _make_comp(value=0.1000)
        live_comp = _make_comp(value=0.0500)  # 50% decrease
        seed = [_make_tariff(components=[seed_comp])]
        live = [_make_tariff(components=[live_comp])]
        alerts = compare_to_seed(live, seed)
        assert has_critical_alerts(alerts)


# ─── Missing/extra components ────────────────────────────────────

class TestComponentMismatch:
    def test_extra_component_in_live(self):
        seed = [_make_tariff(components=[_make_comp(name="Basic")])]
        live = [_make_tariff(components=[
            _make_comp(name="Basic"),
            _make_comp(name="New Rider", ctype="rider"),
        ])]
        alerts = compare_to_seed(live, seed)
        new_alerts = [a for a in alerts if "New component" in a.message]
        assert len(new_alerts) == 1
        assert new_alerts[0].severity == "warning"

    def test_missing_component_in_live(self):
        seed = [_make_tariff(components=[
            _make_comp(name="Basic"),
            _make_comp(name="Rider", ctype="rider"),
        ])]
        live = [_make_tariff(components=[_make_comp(name="Basic")])]
        alerts = compare_to_seed(live, seed)
        missing = [a for a in alerts if "missing" in a.message.lower()]
        assert len(missing) == 1


# ─── Missing/extra tariffs ──────────────────────────────────────

class TestTariffMismatch:
    def test_tariff_in_seed_not_in_live(self):
        seed = [
            _make_tariff(name="Residential", code="R1"),
            _make_tariff(name="Commercial", code="C1", cls="commercial"),
        ]
        live = [_make_tariff(name="Residential", code="R1")]
        alerts = compare_to_seed(live, seed)
        missing = [a for a in alerts if "seed but not in live" in a.message]
        assert len(missing) == 1
        assert "Commercial" in missing[0].message

    def test_new_tariff_in_live(self):
        seed = [_make_tariff(name="Residential", code="R1")]
        live = [
            _make_tariff(name="Residential", code="R1"),
            _make_tariff(name="New Plan", code="N1"),
        ]
        alerts = compare_to_seed(live, seed)
        new = [a for a in alerts if "New tariff" in a.message]
        assert len(new) == 1
        assert new[0].severity == "info"


# ─── Market-based (null values) ─────────────────────────────────

class TestNullValues:
    def test_both_null_no_alert(self):
        seed_comp = _make_comp(name="Market Energy", value=None)
        live_comp = _make_comp(name="Market Energy", value=None)
        seed = [_make_tariff(components=[seed_comp])]
        live = [_make_tariff(components=[live_comp])]
        alerts = compare_to_seed(live, seed)
        value_alerts = [a for a in alerts if a.component_name == "Market Energy"]
        assert len(value_alerts) == 0

    def test_seed_null_live_has_value(self):
        seed_comp = _make_comp(name="Energy", value=None)
        live_comp = _make_comp(name="Energy", value=0.12)
        seed = [_make_tariff(components=[seed_comp])]
        live = [_make_tariff(components=[live_comp])]
        alerts = compare_to_seed(live, seed)
        mismatch = [a for a in alerts if "mismatch" in a.message.lower()]
        assert len(mismatch) == 1


# ─── has_critical_alerts helper ──────────────────────────────────

class TestHasCriticalAlerts:
    def test_no_alerts(self):
        assert not has_critical_alerts([])

    def test_only_info(self):
        alerts = [ChangeAlert("U", "T", "C", 0.1, 0.1, 0.0, "info", "ok")]
        assert not has_critical_alerts(alerts)

    def test_with_critical(self):
        alerts = [ChangeAlert("U", "T", "C", 0.1, 0.2, 100.0, "critical", "bad")]
        assert has_critical_alerts(alerts)


# ─── log_change_alerts smoke test ────────────────────────────────

class TestLogAlerts:
    def test_logs_without_error(self, caplog):
        alerts = [
            ChangeAlert("U", "T", "C", 0.1, 0.105, 5.0, "info", "small change"),
            ChangeAlert("U", "T", "C", 0.1, 0.12, 20.0, "warning", "moderate"),
            ChangeAlert("U", "T", "C", 0.1, 0.2, 100.0, "critical", "big change"),
        ]
        log_change_alerts(alerts)  # should not raise


# ─── Multi-component tariff ─────────────────────────────────────

class TestMultiComponent:
    def test_mixed_changes(self):
        seed = [_make_tariff(components=[
            _make_comp(name="Basic Charge", ctype="fixed", value=6.89, unit="$/month"),
            _make_comp(name="Step 1", ctype="energy", value=0.0950),
            _make_comp(name="Step 2", ctype="energy", value=0.1408),
        ])]
        live = [_make_tariff(components=[
            _make_comp(name="Basic Charge", ctype="fixed", value=7.05, unit="$/month"),  # ~2.3%
            _make_comp(name="Step 1", ctype="energy", value=0.0966),  # ~1.7%
            _make_comp(name="Step 2", ctype="energy", value=0.1430),  # ~1.6%
        ])]
        alerts = compare_to_seed(live, seed)
        assert not has_critical_alerts(alerts)
        # All changes are small — should be info level
        value_alerts = [a for a in alerts if a.pct_change is not None]
        assert all(a.severity == "info" for a in value_alerts)
