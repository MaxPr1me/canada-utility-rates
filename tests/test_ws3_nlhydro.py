"""Phase 6D: NL Hydro market-indexed non-firm energy (Rate 5.1L and Island non-thermal) as value-less components."""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities.nl_hydro import (
    NL_NONFIRM_URL,
    NONFIRM_MARKET_REFERENCE,
    NLHydroScraper,
)
from scrapers.utils.parsing import DocumentPage

FIXTURES = Path(__file__).resolve().parent / "fixtures"
TODAY = date(2026, 10, 30)
REGISTRY = Path(__file__).resolve().parents[1] / "data" / "sources" / "registry.json"


def _document() -> dict:
    document = json.loads((FIXTURES / "nl_hydro.json").read_text(encoding="utf-8"))
    document["nonfirm"] = json.loads((FIXTURES / "nl_hydro_nonfirm.json").read_text(encoding="utf-8"))
    return document


def _parse(document: dict, with_lab: bool = True):
    pages = document["pages"] + document["wp1_pages"] + document["b10_industrial_pages"]
    if with_lab:
        pages = pages + document["nonfirm"]["pages"]
    scraper = NLHydroScraper()
    records = scraper.parse_schedule_pages(
        [DocumentPage(**page) for page in pages], document["source_url"], today=TODAY)
    return scraper, {record.tariff_code: record for record in records}


def _mutate(document: dict, key: str, page_number: int, old: str, new: str) -> dict:
    page = next(p for p in (document[key] if key != "nonfirm" else document["nonfirm"]["pages"])
                if p["page_number"] == page_number)
    assert old in page["text"]
    page["text"] = page["text"].replace(old, new)
    return document


def test_fixture_is_the_official_july_2026_rate_5_1l_schedule():
    document = _document()
    pages = {p["page_number"]: p["text"] for p in document["nonfirm"]["pages"]}
    assert sorted(pages) == [59, 60, 61]
    assert pages[59].rstrip().endswith("LAB-9") and pages[61].rstrip().endswith("LAB-11")
    assert document["nonfirm"]["source_url"] == document["source_url"]
    assert document["nonfirm"]["market_source_url"] == NL_NONFIRM_URL


def test_total_is_the_21_prior_records_plus_two_non_firm_records():
    scraper, records = _parse(_document())
    assert len(records) == 23
    assert {"IND-NONFIRM", "5.1L"} <= set(records)
    assert len(_parse(_document(), with_lab=False)[1]) == 22
    assert "5.1L" not in scraper.unmodelled_published


def test_rate_5_1l_has_a_printed_basic_charge_and_value_less_market_energy():
    record = _parse(_document())[1]["5.1L"]
    assert (record.customer_class, record.rate_structure, record.sub_class) == (
        "industrial", "mixed", "labrador non-firm")
    assert record.pricing_method == "market_based" and record.market_reference == NONFIRM_MARKET_REFERENCE
    assert record.effective_date == "2026-07-01" and record.confidence == "high"
    assert record.demand_min_kw == 1500.0
    assert "Labrador Interconnected System" in record.eligibility and "1.5 MW" in record.eligibility
    assert "interruption/curtailment" in record.eligibility
    assert record.notes.startswith("Provenance: live_parsed.")
    fixed, on_peak, off_peak = record.components
    assert (fixed.component_type, fixed.charge_value, fixed.charge_unit) == ("fixed", 85.25, "$/month")
    assert fixed.market_reference is None and fixed.effective_date == "2026-07-01"
    for component, period in ((on_peak, "on-peak"), (off_peak, "off-peak")):
        assert component.component_type == "energy" and component.tou_period == period
        assert component.charge_value is None and component.charge_unit == "$/kWh"
        assert component.market_reference == NONFIRM_MARKET_REFERENCE
        assert component.market_source_url == NL_NONFIRM_URL
        assert component.source_url == _document()["source_url"]
        assert component.effective_date == "2026-07-01"
        assert "greater of that rate and the energy charge of Rate No. 2.4L" in component.notes
    assert "December-March" in on_peak.tou_hours and "April-November" in on_peak.tou_hours
    assert off_peak.tou_hours == "All other hours"


def test_island_non_thermal_non_firm_has_only_value_less_market_energy():
    record = _parse(_document())[1]["IND-NONFIRM"]
    assert (record.customer_class, record.rate_structure, record.sub_class) == (
        "industrial", "market", "industrial non-firm")
    assert record.pricing_method == "market_based" and record.effective_date == "2026-07-01"
    assert "66 kV or greater" in record.eligibility and "other than a retailer" in record.eligibility
    assert "firm power and energy" in record.eligibility
    assert [(c.tou_period, c.charge_value, c.market_source_url) for c in record.components] == [
        ("on-peak", None, NL_NONFIRM_URL), ("off-peak", None, NL_NONFIRM_URL)]
    assert "Thermal Generation Source charge is a fuel-cost formula" in record.notes
    assert not any("fuel" in (c.component_name or "").lower() for c in record.components)


def test_no_number_is_stored_for_any_market_indexed_part():
    for code in ("IND-NONFIRM", "5.1L"):
        record = _parse(_document())[1][code]
        energy = [c for c in record.components if c.component_type == "energy"]
        assert len(energy) == 2
        assert all(c.charge_value is None and c.market_reference and c.market_source_url for c in energy)
        # a printed floor or monthly price must never appear as a stored number
        assert [c.charge_value for c in record.components if c.component_type != "energy"] == (
            [85.25] if code == "5.1L" else [])


def test_island_thermal_non_firm_stays_source_blocked():
    scraper, records = _parse(_document())
    assert scraper.unmodelled_published["IND-NONFIRM-THERMAL"].startswith("source-blocked")
    assert "IND-NONFIRM" not in scraper.unmodelled_published
    assert not any("fuel" in (c.component_name or "").lower() or "thermal" in (c.component_name or "").lower()
                   for code in ("IND-NONFIRM", "5.1L") for c in records[code].components)


def test_existing_classes_are_unchanged_by_the_new_records():
    document = _document()
    _, with_new = _parse(document)
    _, without = _parse(document, with_lab=False)
    for code, record in without.items():
        if code == "IND-NONFIRM":
            continue
        assert [(c.component_name, c.charge_value, c.charge_unit) for c in record.components] == \
            [(c.component_name, c.charge_value, c.charge_unit) for c in with_new[code].components]


@pytest.mark.parametrize(("page", "old", "new"), [
    (59, "$85.25 per month", "$0.00 per month"),
    (59, "NYISO Zone A Day-Ahead Peak", "Another Market Peak"),
    (59, "minimum of 1.5 MW load", "minimum of 5 MW load"),
    (59, "Effective July 1, 2026 LAB-9", "Effective July 1, 2027 LAB-9"),
    (59, "Rate No. 2.4L", "Rate No. 2.3L"),
    (60, "ISO New England Mass Hub Day-Ahead Off-Peak Calendar-Month 5 MW\nFutures", "Hub price"),
    (60, "7 am to 10 pm", "6 am to 10 pm"),
    (61, "first business day following\nthe 21st day", "last business day following\nthe 20th day"),
    (60, "The off-peak period will include all other hours.", "Off-peak is billed at 4.5¢ per kWh."),
])
def test_5_1l_fails_closed_on_missing_or_changed_terms(page, old, new):
    scraper, records = _parse(_mutate(_document(), "nonfirm", page, old, new))
    assert "5.1L" not in records
    assert scraper.unmodelled_published["5.1L"].startswith("published but not live-verified")
    assert len(records) == 22 and "IND-NONFIRM" in records and "LAB-IND" in records


def test_5_1l_missing_basic_charge_or_continuation_page_is_rejected():
    document = _document()
    document["nonfirm"]["pages"] = [p for p in document["nonfirm"]["pages"] if p["page_number"] != 60]
    scraper, records = _parse(document)
    assert "5.1L" not in records and "5.1L" in scraper.unmodelled_published
    document = _mutate(_document(), "nonfirm", 59, "Basic Customer Charge", "Customer Charge")
    assert "5.1L" not in _parse(document)[1]


def test_a_printed_non_firm_price_rejects_the_record_instead_of_being_stored():
    for key, page, old in (("nonfirm", 60, "The off-peak period"), ("b10_industrial_pages", 11, "The following formula")):
        document = _mutate(_document(), key, page, old, "Non-firm energy is 5.824¢ per kWh. " + old)
        scraper, records = _parse(document)
        rejected = "5.1L" if key == "nonfirm" else "IND-NONFIRM"
        assert rejected not in records
        assert "printed" in scraper.unmodelled_published[rejected]


def test_non_firm_failures_are_isolated_from_each_other():
    document = _mutate(_document(), "b10_industrial_pages", 11, "NYISO Zone A", "another market")
    _, records = _parse(document)
    assert "IND-NONFIRM" not in records and "5.1L" in records and "IND-FIRM" in records


def test_island_non_firm_missing_page_or_future_date_is_rejected():
    document = _document()
    document["b10_industrial_pages"] = [p for p in document["b10_industrial_pages"] if p["page_number"] != 12]
    _, records = _parse(document)
    assert "IND-NONFIRM" not in records and "5.1L" in records
    document = _document()
    for page in document["b10_industrial_pages"]:
        page["text"] = page["text"].replace("Effective July 1, 2026", "Effective July 1, 2027")
    _, records = _parse(document)
    assert "IND-NONFIRM" not in records


def test_rejected_non_firm_class_is_logged(caplog):
    caplog.set_level(logging.WARNING)
    _parse(_mutate(_document(), "nonfirm", 59, "NYISO Zone A Day-Ahead Peak", "Another Market Peak"))
    assert any("5.1L not live-verified" in message for message in caplog.messages)


def test_registry_lists_the_non_firm_price_page_and_scraper_constant_matches():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entry = next(e for e in registry["utilities"] if e["name"] == "NL Hydro")
    assert NL_NONFIRM_URL in {source["url"] for source in entry["sources"]}
    assert "Thermal Generation Source" in entry["notes"]
