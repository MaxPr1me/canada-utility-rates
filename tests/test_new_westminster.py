"""City of New Westminster (BC) parser tests on the January 1, 2026 Schedule of Rates excerpt."""

import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities import new_westminster as nw
from scrapers.utils.parsing import DocumentPage

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "new_westminster_bylaw_6502_2026-01-01.json")
                     .read_text(encoding="utf-8"))
URL = FIXTURE["source_url"]
TODAY = date(2026, 11, 4)


def _pages(old: str = "", new: str = "") -> list[DocumentPage]:
    return [DocumentPage(p["page_number"], p["text"].replace(old, new) if old else p["text"])
            for p in FIXTURE["pages"]]


def _parse(pages=None, today=TODAY):
    return {r.tariff_code: r for r in nw.parse_schedule(pages or _pages(), URL, today=today)}


def _values(record):
    return [(c.component_name, c.charge_value, c.charge_unit) for c in record.components]


def test_parses_building_classes_with_one_schedule_date():
    records = _parse()
    assert list(records) == ["101", "102", "103", "131", "134", "201", "202", "210", "211", "212"]
    assert {r.effective_date for r in records.values()} == {"2026-01-01"}
    assert all("PDF pages 26-33" in r.source_page for r in records.values())
    assert _values(records["101"]) == [("Basic Charge", 16.16, "$/two months"), ("Energy Charge", 0.1344, "$/kWh"),
                                       ("Rate Rider", 2.5, "%"), ("Climate Action Levy", 3.5, "%")]
    assert _values(records["201"])[:2] == [("Basic Charge", 19.32, "$/two months"), ("Energy Charge", 0.151, "$/kWh")]


def test_large_general_service_keeps_demand_and_energy_blocks():
    record = _parse()["210"]
    demand = [(c.tier_number, c.tier_threshold, c.charge_value) for c in record.components
              if c.component_type == "demand" and c.tier_number]
    assert demand == [(1, 35.0, 0.0), (2, 150.0, 7.75), (3, 150.0, 14.87)]
    energy = [(c.tier_number, c.tier_threshold, c.tier_unit, c.charge_value) for c in record.components
              if c.component_type == "energy"]
    assert energy == [(1, 14800.0, "kWh/month", 0.151), (2, 14800.0, "kWh/month", 0.0728)]
    discounts = {c.component_name: (c.charge_value, c.sub_component) for c in record.components
                 if c.sub_component == "conditional_credit"}
    assert discounts == {"Primary Metering Discount": (-1.5, "conditional_credit"),
                         "Customer Transformation Discount": (-0.25, "conditional_credit")}


def test_multi_residential_blocks_are_per_dwelling():
    energy = [(c.tier_number, c.tier_threshold, c.tier_unit, c.charge_value) for c in _parse()["131"].components
              if c.component_type == "energy"]
    assert energy == [(1, 400.0, "kWh per dwelling per two months", 0.1344),
                      (2, 600.0, "kWh per dwelling per two months", 0.151),
                      (3, 600.0, "kWh per dwelling per two months", 0.1344)]


def test_temporary_pilot_and_lighting_rates_are_excluded():
    assert not set(_parse()) & {"203", "213", "220", "230", "240", "241", "302", "500"}


def test_missing_levy_fails_closed():
    pages = _pages("A climate action levy equal to 3.5% of the billed amount shall apply", "")
    with pytest.raises(ValueError, match="climate action levy"):
        _parse(pages)


def test_schedule_not_yet_in_effect_fails_closed():
    with pytest.raises(ValueError, match="takes effect 2026-01-01"):
        _parse(today=date(2025, 12, 31))


def test_bylaw_link_discovery_and_fallback(monkeypatch):
    html = ('<a href="https://www.newwestcity.ca/database/files/library/Consolidated_Bylaw_6502__1998_Electrical_'
            'Utility__2026_01_15_consolidation_.pdf">Bylaw No. 6502, 1998</a>')
    assert nw.find_bylaw_url(html).endswith("2026_01_15_consolidation_.pdf")
    scraper = nw.NewWestminsterScraper()
    monkeypatch.setattr(scraper, "fetch_page", lambda *_a, **_k: "<a href='x.pdf'>Bylaw No. 6503, 1998</a>")
    url, note = scraper._discover()
    assert url == nw.LAST_KNOWN_BYLAW_URL and "last known" in note
