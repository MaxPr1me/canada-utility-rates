"""Saint John Energy (NB) parser tests on the September 1, 2026 rates-manual excerpt."""

import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities import saint_john_energy as sje
from scrapers.utils.parsing import DocumentPage

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "saint_john_energy_manual_2026-09-01.json")
                     .read_text(encoding="utf-8"))
URL = FIXTURE["source_url"]
TODAY = date(2026, 11, 4)


def _pages(replace: dict[int, tuple[str, str]] | None = None) -> list[DocumentPage]:
    pages = []
    for page in FIXTURE["pages"]:
        text = page["text"]
        if replace and page["page_number"] in replace:
            old, new = replace[page["page_number"]]
            assert old in text
            text = text.replace(old, new)
        pages.append(DocumentPage(page["page_number"], text))
    return pages


def _by_code():
    return {r.tariff_code: r for r in sje.parse_manual(_pages(), URL, today=TODAY)}


def _values(record):
    return {c.component_name: (c.charge_value, c.charge_unit) for c in record.components}


def test_parses_every_building_schedule_with_separate_rider():
    records = _by_code()
    assert list(records) == ["001", "006", "002", "202", "004", "008", "009", "010"]
    assert all(r.effective_date == "2026-04-14" and r.province == "NB" for r in records.values())
    assert _values(records["001"]) == {
        "Service Charge": (24.81, "$/month"),
        "Energy Charge (Base Rate)": (0.1392, "$/kWh"),
        "Rate Rider": (0.0039, "$/kWh"),
    }
    assert _values(records["004"])["Energy Charge (Base Rate)"] == (0.1842, "$/kWh")
    assert records["004"].usage_max == 5000.0 and records["004"].usage_unit == "kWh/month"
    assert _values(records["009"]) == {"Demand Charge": (19.33, "$/kW/month"),
                                       "Energy Charge (Base Rate)": (0.075, "$/kWh"),
                                       "Rate Rider": (0.0039, "$/kWh")}
    assert _values(records["010"])["Service Charge"] == (83.47, "$/month")
    assert "Closed" in records["202"].notes and "Closed" in records["009"].notes


def test_demand_schedules_keep_the_first_100_kwh_per_kw_block():
    gs = _by_code()["002"]
    blocks = [c for c in gs.components if c.component_type == "energy"]
    assert [(c.tier_number, c.tier_threshold, c.tier_unit, c.charge_value) for c in blocks] == [
        (1, 100.0, "kWh/kW of billing demand/month", 0.1568),
        (2, 100.0, "kWh/kW of billing demand/month", 0.1217),
    ]
    demand = next(c for c in gs.components if c.component_type == "demand")
    assert (demand.charge_value, demand.demand_unit) == (9.76, "kW")
    assert "50% of installed kVA capacity" in demand.notes


def test_municipal_related_and_rental_schedules_are_out_of_scope():
    codes = set(_by_code())
    assert not codes & {"101", "102", "104", "106", "112", "M", "W", "HP"}


def test_total_that_does_not_equal_base_plus_rider_fails_closed():
    pages = _pages({67: ("Total Charge 14.31", "Total Charge 14.41")})
    with pytest.raises(ValueError, match="does not equal total"):
        sje.parse_manual(pages, URL, today=TODAY)


def test_missing_schedule_fails_closed():
    pages = [p for p in _pages() if p.page_number != 75]
    with pytest.raises(ValueError, match="004"):
        sje.parse_manual(pages, URL, today=TODAY)


def test_schedule_not_yet_in_effect_fails_closed():
    with pytest.raises(ValueError, match="takes effect 2026-04-14"):
        sje.parse_manual(_pages(), URL, today=date(2026, 4, 13))


def test_manual_link_discovery_and_last_known_fallback(monkeypatch):
    html = f'<a class="btn" href="{URL}" target="_blank">PDF</a>'
    assert sje.find_manual_url(html) == URL
    scraper = sje.SaintJohnEnergyScraper()

    def tls_failure(*_args, **_kwargs):
        raise OSError("certificate verify failed")

    monkeypatch.setattr(scraper, "fetch_page", tls_failure)
    monkeypatch.setattr(scraper, "fetch_rendered_page", lambda *_a, **_k: html)
    assert scraper._discover_manual() == (URL, "")
    monkeypatch.setattr(scraper, "fetch_rendered_page", lambda *_a, **_k: None)
    url, note = scraper._discover_manual()
    assert url == sje.LAST_KNOWN_MANUAL_URL and "last known manual" in note


def test_no_seed_fallback_when_the_manual_cannot_be_read(monkeypatch):
    scraper = sje.SaintJohnEnergyScraper()
    monkeypatch.setattr(scraper, "_discover_manual", lambda: (URL, ""))

    def offline(*_args, **_kwargs):
        raise OSError("offline")

    monkeypatch.setattr(scraper, "fetch_bytes", offline)
    assert scraper.scrape() == []
