"""Summerside Electric (PE) parser tests on the August 1, 2026 rates-manual excerpt."""

import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities import summerside_electric as se
from scrapers.utils.parsing import DocumentPage

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "summerside_electric_manual_2026-08-01.json")
                     .read_text(encoding="utf-8"))
URL = FIXTURE["source_url"]
TODAY = date(2026, 11, 4)


def _pages(old: str = "", new: str = "") -> list[DocumentPage]:
    return [DocumentPage(p["page_number"], p["text"].replace(old, new, 1) if old else p["text"])
            for p in FIXTURE["pages"]]


def _parse(pages=None, today=TODAY):
    return {r.tariff_code: r for r in se.parse_manual(pages or _pages(), URL, today=today)}


def test_parses_building_schedules_dated_by_the_revision_table():
    records = _parse()
    assert list(records) == ["RES-URBAN", "RES-RURAL", "RES-SEASONAL", "RES-SEASONAL-OPTION", "GS1",
                             "GS1-SEASONAL", "SI", "LI"]
    assert {r.effective_date for r in records.values()} == {"2026-08-01"}
    assert [(c.charge_value, c.charge_unit, c.tier_threshold) for c in records["RES-URBAN"].components] == [
        (24.57, "$/month", None), (0.1784, "$/kWh", 2000.0), (0.1423, "$/kWh", 2000.0)]
    assert records["RES-SEASONAL-OPTION"].components[0].charge_value == 37.5


def test_general_service_keeps_the_free_first_20_kw():
    demand = [(c.tier_number, c.tier_threshold, c.charge_value) for c in _parse()["GS1"].components
              if c.component_type == "demand"]
    assert demand == [(1, 20.0, 0.0), (2, 20.0, 13.43)]


def test_industrial_schedules():
    records = _parse()
    small = [(c.charge_value, c.tier_unit) for c in records["SI"].components]
    assert small == [(7.46, None), (0.2142, "kWh/kW of billing demand/month"), (0.109, "kWh/kW of billing demand/month")]
    assert [(c.charge_value, c.charge_unit) for c in records["LI"].components] == [(14.5, "$/kW/month"), (0.092, "$/kWh")]


def test_unprinted_ecam_is_disclosed_not_invented():
    record = _parse()["GS1"]
    assert "Energy Cost Adjustment Mechanism" in record.notes
    assert not any("ECAM" in c.component_name for c in record.components)


def test_missing_price_fails_closed():
    pages = _pages("$13.43 per kW for balance kW per Billing Period", "per kW for balance kW per Billing Period")
    with pytest.raises(ValueError, match="General Service I prices"):
        _parse(pages)


def test_future_rates_fail_closed():
    with pytest.raises(ValueError, match="take effect 2026-08-01"):
        _parse(today=date(2026, 7, 31))


def test_manual_link_discovery():
    html = ('<a href="https://summersideca.hosted.civiclive.com/UserFiles/x/2027%20Manual.pdf">Electric Rates, '
            'Schedule &amp; Policy Manual</a>')
    assert se.find_manual_url(html).endswith("2027%20Manual.pdf")
