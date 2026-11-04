"""District of Summerland (BC) parser tests on the February 10, 2026 Schedule A excerpt."""

import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities import summerland
from scrapers.utils.parsing import DocumentPage

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "summerland_fees_bylaw_2026-02-10.json")
                     .read_text(encoding="utf-8"))
URL = FIXTURE["source_url"]
TODAY = date(2026, 11, 4)


def _pages(old: str = "", new: str = "") -> list[DocumentPage]:
    pages = []
    for page in FIXTURE["pages"]:
        text = page["text"]
        if old and old in text:
            text = text.replace(old, new, 1)
        pages.append(DocumentPage(page["page_number"], text))
    return pages


def _parse(pages=None, today=TODAY):
    return {r.tariff_code: r for r in summerland.parse_bylaw(pages or _pages(), URL, today=today)}


def test_parses_building_classes_dated_by_the_latest_schedule_a_replacement():
    records = _parse()
    assert list(records) == ["E01-E08", "E10", "E15", "E17", "E19"]
    assert {r.effective_date for r in records.values()} == {"2026-02-10"}
    residential = records["E01-E08"]
    assert [(c.component_name, c.charge_value, c.charge_unit) for c in residential.components] == [
        ("Basic Charge", 22.54, "$/month"), ("Energy Charge", 0.1582, "$/kWh")]
    assert "PDF pages 3-6" in residential.source_page


def test_general_commercial_bills_demand_only_above_40_kva():
    demand = [c for c in _parse()["E10"].components if c.component_type == "demand"]
    assert [(c.tier_number, c.tier_threshold, c.tier_unit, c.charge_value, c.charge_unit) for c in demand] == [
        (1, 40.0, "kVA", 0.0, "$/kVA/month"), (2, 40.0, "kVA", 17.69, "$/kVA/month")]


def test_large_primary_classes_bill_every_kva():
    for code in ("E17", "E19"):
        demand = [c for c in _parse()[code].components if c.component_type == "demand"]
        assert [(c.charge_value, c.tier_number) for c in demand] == [(17.69, None)]


def test_excluded_codes_are_not_emitted():
    assert not set(_parse()) & {"E12", "E14", "E20", "E22", "E25", "E26", "E50"}


def test_repeated_price_lines_survive_extraction():
    # Page 4 prints "All electrical energy used $ 0.1514 per kWh" three times (E10, E15, E17); the default
    # header/footer heuristic would drop them, so the parser reads pages with drop_repeated_lines=False.
    page4 = next(p for p in FIXTURE["pages"] if p["page_number"] == 4)["text"]
    assert page4.count("All electrical energy used $ 0.1514 per kWh") == 3


def test_future_schedule_fails_closed():
    with pytest.raises(ValueError, match="takes effect 2026-02-10"):
        _parse(today=date(2026, 2, 9))


def test_missing_energy_price_fails_closed():
    pages = _pages("All electrical energy used $ 0.1582 per kWh", "All electrical energy used per kWh")
    with pytest.raises(ValueError, match="E01-E08"):
        _parse(pages)


def test_bylaw_link_discovery_and_fallback(monkeypatch):
    html = ('<a href="/docs/default-source/your-city-hall/bylaws---policies/district-bylaws/'
            'fees-and-charges-no-98-001-consolidated-to-feb-10-2026.pdf?sfvrsn=1">Fees and Charges No. 98-001 '
            'Consolidated to Feb 10, 2026</a>')
    assert summerland.find_bylaw_url(html).startswith("https://www.summerland.ca/docs/default-source/")
    scraper = summerland.SummerlandScraper()
    monkeypatch.setattr(scraper, "fetch_page", lambda *_a, **_k: "<html></html>")
    url, note = scraper._discover()
    assert url == summerland.LAST_KNOWN_BYLAW_URL and "last known" in note
