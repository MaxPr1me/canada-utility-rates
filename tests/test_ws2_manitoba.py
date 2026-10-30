"""Manitoba Hydro commercial energy blocks and phase-variant basic charges (workstream 2)."""
from __future__ import annotations

import html as _html
import json
import math
import os
from dataclasses import asdict

import pytest

from scrapers.utilities.manitoba_hydro import ManitobaHydroScraper
from pipeline.representative_models import _block_windows, _unmarked_fixed_variants, component_exclusion

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "manitoba_hydro.json")
with open(FIXTURE, encoding="utf-8") as fh:
    COMMERCIAL_LINES = json.load(fh)["pages"]["commercial"]["lines"]


def _html_of(lines):
    return "<html><body>" + "".join(f"<p>{_html.escape(ln)}</p>" for ln in lines) + "</body></html>"


def _parse(lines=None):
    return {r.tariff_name: r for r in ManitobaHydroScraper()._parse_commercial(_html_of(lines or COMMERCIAL_LINES))}


def _edited(old, new, occurrence=0):
    lines = list(COMMERCIAL_LINES)
    index = [i for i, ln in enumerate(lines) if ln == old][occurrence]
    lines[index] = new
    return lines


def _energy(record):
    return [c for c in record.components if c.component_type == "energy"]


def _tiers(record):
    return [(c.tier_number, c.tier_threshold) for c in _energy(record)]


def test_two_block_classes_are_numbered_one_and_two():
    com = _parse()
    assert _tiers(com["General Service Small (Non-Demand)"]) == [(1, 11000.0), (2, None)]
    assert _tiers(com["General Service Medium"]) == [(1, 19500.0), (2, None)]
    assert _tiers(com["General Service Seasonal (Single Phase)"]) == [(1, 66000.0), (2, None)]


def test_balance_row_is_never_tier_three_in_a_two_block_class():
    for name in ("General Service Small (Non-Demand)", "General Service Medium",
                 "General Service Seasonal (Single Phase)"):
        assert [c.tier_number for c in _energy(_parse()[name])] == [1, 2]


def test_next_block_stores_a_cumulative_upper_bound_not_its_width():
    demand = _parse()["General Service Small (Demand)"]
    first, nxt, balance = _energy(demand)
    assert [c.tier_number for c in (first, nxt, balance)] == [1, 2, 3]
    assert (first.component_name, first.tier_threshold) == ("First 11,000 kWh", 11000.0)
    assert (nxt.component_name, nxt.tier_threshold) == ("Next 8,500 kWh", 19500.0)
    assert (balance.component_name, balance.tier_threshold, balance.tier_unit) == ("Balance of kWh", None, None)
    assert [c.charge_value for c in (first, nxt, balance)] == pytest.approx([0.09864, 0.07568, 0.04858])
    assert {first.tier_unit, nxt.tier_unit} == {"kWh"}
    assert "cumulative upper bound (19,500 kWh)" in nxt.notes
    assert "above 19,500 kWh" in balance.notes
    assert "For accounts where demand has exceeded 50 kVA" in balance.notes


def test_stored_blocks_give_the_engine_contiguous_windows():
    demand = _parse()["General Service Small (Demand)"]
    rows = [({}, asdict(c)) for c in _energy(demand)]
    windows, problem = _block_windows(rows, 1.0)
    assert problem is None
    assert windows == {1: (0.0, 11000.0), 2: (11000.0, 19500.0), 3: (19500.0, math.inf)}
    two = _parse()["General Service Medium"]
    windows, problem = _block_windows([({}, asdict(c)) for c in _energy(two)], 1.0)
    assert problem is None
    assert windows == {1: (0.0, 19500.0), 2: (19500.0, math.inf)}


def test_single_energy_charge_classes_have_no_tiers():
    large = _parse()["General Service Large (>100 kV)"]
    assert all(c.tier_number is None and c.tier_threshold is None for c in large.components)


@pytest.mark.parametrize("name", ["General Service Small (Non-Demand)", "General Service Small (Demand)"])
def test_phase_basic_charges_are_labelled_alternatives(name):
    record = _parse()[name]
    basics = [c for c in record.components if c.component_type == "fixed"]
    assert [c.component_name for c in basics] == ["Basic Charge (single phase)", "Basic Charge (three phase)"]
    assert [c.charge_value for c in basics] == [21.57, 35.04]
    assert [c.sub_component for c in basics] == ["single phase", "three phase"]
    for c in basics:
        assert c.notes.startswith("Alternative: applies only to ")
        assert "never both added together" in c.notes
        assert component_exclusion(asdict(c), "2026-10-30") == "alternative"


def test_unlabelled_basic_charges_are_still_a_single_charge():
    medium = _parse()["General Service Medium"]
    basic = [c for c in medium.components if c.component_type == "fixed"]
    assert len(basic) == 1 and basic[0].notes is None and basic[0].sub_component is None
    assert component_exclusion(asdict(basic[0]), "2026-10-30") is None


def test_engine_never_prices_both_phase_variants():
    record = _parse()["General Service Small (Non-Demand)"]
    # Old behaviour: unlabelled variants were flagged only by the engine's name heuristic and no alternative marker
    # existed; the stored rows now declare themselves alternatives, so neither is priced.
    priced = [({"component": c.component_name, "type": c.component_type}, asdict(c))
              for c in record.components
              if c.component_type == "fixed" and component_exclusion(asdict(c), "2026-10-30") is None]
    assert priced == []
    assert _unmarked_fixed_variants(priced) == []


def test_next_block_without_a_printed_size_rejects_only_that_class():
    com = _parse(_edited("Next 8,500 kWh", "Next kWh"))
    assert "General Service Small (Demand)" not in com
    assert {"General Service Small (Non-Demand)", "General Service Medium"} <= set(com)


def test_blocks_out_of_order_reject_the_class():
    lines = list(COMMERCIAL_LINES)
    start = lines.index("Next 8,500 kWh")
    lines[start - 2:start + 2] = ["Next 8,500 kWh", "7.568\u00a2/kWh", "First 11,000 kWh", "9.864\u00a2/kWh"]
    com = _parse(lines)
    assert "General Service Small (Demand)" not in com
    assert "General Service Medium" in com


def test_dropped_first_block_rejects_the_class():
    lines = list(COMMERCIAL_LINES)
    index = [i for i, ln in enumerate(lines) if ln == "First 19,500 kWh"][0]
    del lines[index:index + 2]
    com = _parse(lines)
    assert "General Service Medium" not in com
    assert "General Service Small (Demand)" in com


def test_all_seven_general_service_classes_and_diesel_still_parse():
    com = _parse()
    assert len(com) == 9
    assert all(r.confidence == "high" for r in com.values())


@pytest.mark.parametrize("name", ["General Service Small (Demand)", "General Service Medium"])
def test_first_50_kva_no_charge_is_a_zero_priced_demand_block(name):
    free, balance = [c for c in _parse()[name].components if c.component_type == "demand"]
    assert (free.tier_number, free.charge_value, free.tier_threshold, free.tier_unit) == (1, 0.0, 50.0, "kVA")
    assert (balance.tier_number, balance.tier_threshold, balance.tier_unit) == (2, 50.0, "kVA")
    assert balance.charge_value == pytest.approx(12.82 if "Small" in name else 12.39)
    assert balance.charge_unit == free.charge_unit == "$/kVA"


def test_engine_bills_demand_only_above_the_free_50_kva():
    medium = _parse()["General Service Medium"]
    rows = [({}, asdict(c)) for c in medium.components if c.component_type == "demand"]
    windows, problem = _block_windows(rows, 0.9)
    assert problem is None
    assert windows == {1: (0.0, 45.0), 2: (45.0, math.inf)}


def test_large_classes_keep_a_single_untiered_demand_charge():
    for name in ("General Service Large (>750 V to 30 kV)", "General Service Large (>100 kV)"):
        demand = [c for c in _parse()[name].components if c.component_type == "demand"]
        assert len(demand) == 1 and demand[0].tier_number is None and demand[0].tier_threshold is None


def test_missing_no_charge_row_rejects_the_class():
    lines = list(COMMERCIAL_LINES)
    index = [i for i, ln in enumerate(lines) if ln == "First 50 kVA of monthly billing demand"][0]
    del lines[index:index + 2]
    com = _parse(lines)
    assert "General Service Medium" not in com
    assert "General Service Small (Demand)" in com
