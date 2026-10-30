"""FortisBC Electric Rate Schedule 38 (Mid-C indexed interruptible pilot), Phase 6D."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from scrapers.base import TariffRecord
from scrapers.utilities.fortisbc_electric import (
    MID_C_MARKET_REFERENCE,
    TARIFF_URL,
    FortisBCElectricScraper,
)
from scrapers.utils.parsing import DocumentPage

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TODAY = date(2026, 10, 30)


def _pages(mutate=None, drop=()):
    base = json.loads((FIXTURES / "fortisbc_electric.json").read_text(encoding="utf-8"))
    rs38 = json.loads((FIXTURES / "fortisbc_electric_rs38.json").read_text(encoding="utf-8"))
    raw = [page for key in ("pages", "large_commercial_pages", "industrial_pages") for page in base[key]]
    raw += rs38["pages"]
    pages = []
    for page in raw:
        if page["page_number"] in drop:
            continue
        text = page["text"]
        if mutate:
            text = mutate(page["page_number"], text)
        pages.append(DocumentPage(page["page_number"], text))
    return pages


def _parse(pages) -> dict[str, TariffRecord]:
    with patch("scrapers.utilities.fortisbc_electric._today", return_value=TODAY):
        return {r.tariff_code: r for r in FortisBCElectricScraper().parse_schedule_pages(pages)}


@pytest.fixture
def rs38() -> TariffRecord:
    records = _parse(_pages())
    assert "38" in records
    return records["38"]


def test_existing_eleven_schedules_still_parse_and_rs38_is_added():
    records = _parse(_pages())
    assert set(records) == {"01", "2A", "20", "21", "22A", "23A", "30", "31", "32", "33", "38", "85"}


def test_record_identity_and_classification(rs38):
    assert rs38.tariff_name == "Large Commercial Service - Interruptible (Rate 38)"
    assert rs38.customer_class == "commercial"
    assert rs38.rate_structure == "market"
    assert rs38.pricing_method == "market_based"
    assert rs38.sub_class == "large commercial interruptible (pilot)"
    assert rs38.market_reference == MID_C_MARKET_REFERENCE
    assert rs38.end_date == "2028-07-31"
    assert "Rate Schedule 30" in rs38.eligibility and "Rate Schedule 31" in rs38.eligibility
    assert "July 31, 2028" in rs38.eligibility
    assert rs38.confidence == "medium" and "Interim" in rs38.notes


def test_market_energy_component_is_value_less_with_reference(rs38):
    market = [c for c in rs38.components if c.market_reference]
    assert len(market) == 1
    component = market[0]
    assert component.component_type == "energy"
    assert component.charge_value is None
    assert component.charge_unit == "$/kWh"
    assert component.market_reference == MID_C_MARKET_REFERENCE
    assert component.market_source_url == TARIFF_URL
    assert component.effective_date == "2023-08-01"
    assert "R-38.2" in component.source_detail
    assert "Mid-C" in component.notes and "Bank of Canada" in component.notes


def test_only_printed_numbers_are_stored(rs38):
    priced = {c.component_name: (c.charge_value, c.charge_unit, c.effective_date) for c in rs38.components
              if c.charge_value is not None}
    assert priced == {
        "Customer Charge (as Rate Schedule 30)": (1252.43, "$/month", "2026-01-01"),
        "Customer Charge (as Rate Schedule 31)": (4077.97, "$/month", "2026-01-01"),
        "Hourly Service Adder": (0.01, "$/kWh", "2023-08-01"),
    }
    assert rs38.effective_date == "2026-01-01"
    for component in rs38.components:
        assert component.source_url == TARIFF_URL


def test_customer_charges_are_alternatives(rs38):
    charges = [c for c in rs38.components if c.component_type == "fixed"]
    assert [c.sub_component for c in charges] == ["alternative", "alternative"]
    assert all("Zero ($0.00)" in c.notes for c in charges)


def test_scraper_marks_rs38_live_without_seed():
    with patch("scrapers.utilities.fortisbc_electric._today", return_value=TODAY), \
            patch.object(FortisBCElectricScraper, "_fetch_schedule_pages", return_value=_pages()):
        scraped = FortisBCElectricScraper().scrape()
    rs38 = next(r for r in scraped if r.tariff_code == "38")
    assert rs38.notes.startswith("Provenance: live_parsed.")
    assert not any("seed_fallback" in (r.notes or "") for r in scraped)


def test_missing_schedule_sheet_rejects_only_rs38():
    for dropped in (74, 75, 76):
        records = _parse(_pages(drop=(dropped,)))
        assert "38" not in records
        assert {"30", "31", "32", "33", "85"} <= set(records)


def test_missing_adopted_customer_charge_page_rejects_rs38():
    records = _parse(_pages(drop=(63,)))
    assert "30" not in records and "38" not in records
    records = _parse(_pages(drop=(65,)))
    assert "31" not in records and "38" not in records


@pytest.mark.parametrize("page_number, old, new", [
    (74, "Rate Schedule 30 at the time", "Rate Schedule 21 at the time"),
    (74, "non-firm", "firm"),
    (75, "Day Ahead Mid-Columbia Off-Peak Index", "Day Ahead Off-Peak Index"),
    (75, "(applicable Mid-C Price + 0.0100)", "(applicable Mid-C Price + 0.0200)"),
    (75, "Hourly Service Adder of $0.01000", "Hourly Service Fee of $0.01000"),
    (76, "the daily Bank of Canada", "the weekly Bank of Canada"),
])
def test_changed_required_context_fails_closed(page_number, old, new):
    def mutate(number, text):
        return text.replace(old, new) if number == page_number else text

    pages = _pages(mutate)
    assert any(old in p.text for p in _pages() if p.page_number == page_number)
    records = _parse(pages)
    assert "38" not in records
    assert {"30", "31"} <= set(records)


def test_future_dated_sheet_rejected():
    def mutate(number, text):
        return text.replace("Effective Date: August 1, 2023", "Effective Date: August 1, 2030") if number == 75 else text

    assert "38" not in _parse(_pages(mutate))


def test_expired_pilot_rejected():
    def mutate(number, text):
        return text.replace("July 31, 2028", "July 31, 2026") if number == 74 else text

    assert "38" not in _parse(_pages(mutate))


def test_permanent_orders_give_high_confidence():
    def mutate(number, text):
        return text.replace("(Interim)", "") if number in (74, 75, 76, 77, 78) else text

    record = _parse(_pages(mutate))["38"]
    assert record.confidence == "high"
    assert all(c.confidence == "high" for c in record.components)
