"""BC Hydro Rate Schedule 1892 (Transmission Service - Freshet Energy): value-less Mid-C indexed energy."""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from pipeline.export_json import derive_provenance
from scrapers.base import RateComponent
from scrapers.utilities.bc_hydro import BCHydroScraper, TARIFF_URL
from scrapers.utils.parsing import DocumentPage
from scrapers.utils.validation import validate_batch

FIXTURES = Path(__file__).resolve().parent / "fixtures"
FRESHET_PAGES = set(range(150, 161))


def _pages():
    document = json.loads((FIXTURES / "bc_hydro_freshet.json").read_text(encoding="utf-8"))
    return [DocumentPage(**page) for page in document["pages"]]


def _mutate(pages, numbers, old, new):
    changed = []
    for page in pages:
        if page.page_number in numbers:
            assert old in page.text, (page.page_number, old)
            page = replace(page, text=page.text.replace(old, new))
        changed.append(page)
    return changed


def _parse(pages):
    return BCHydroScraper()._parse_freshet_energy(pages)


def test_rs1892_parses_one_record_with_a_value_less_market_energy_component():
    records = _parse(_pages())
    assert len(records) == 1
    record = records[0]
    assert (record.tariff_code, record.customer_class, record.rate_structure) == ("1892", "industrial", "market")
    assert record.pricing_method == "market_based"
    assert record.effective_date == "2026-04-01"
    assert record.source_url == TARIFF_URL and record.source_page == "Electric Tariff RS 1892; PDF pages 150-160"
    energy, *riders = record.components
    assert (energy.component_type, energy.charge_value, energy.charge_unit) == ("energy", None, "$/kWh")
    assert energy.market_source_url == TARIFF_URL and energy.market_reference == record.market_reference
    assert "Mid-Columbia (Mid-C)" in energy.market_reference and "$3/MWh adder" in energy.market_reference
    assert "$0/kWh" in energy.market_reference and "Bank of Canada" in energy.market_reference
    assert (energy.season, energy.season_months) == ("freshet", "May 1 to July 31 inclusive")
    assert "06:00-22:00 Monday-Saturday" in energy.tou_hours
    assert (energy.effective_date, energy.source_detail) == ("2026-04-01", "Electric Tariff RS 1892; PDF pages 150-160")


def test_rs1892_has_no_invented_number_only_the_two_source_riders_carry_values():
    record = _parse(_pages())[0]
    values = [(part.component_name, part.charge_value, part.charge_unit) for part in record.components]
    assert values == [
        ("Freshet Energy Charge (Mid-C index + adder)", None, "$/kWh"),
        ("Rate Rider -- Deferral Account Rate Rider", -0.015, "fraction"),
        ("Rate Rider -- Trade Income Rate Rider", 0.0, "fraction"),
    ]
    assert all(part.market_reference is None for part in record.components[1:])
    assert not [part for part in record.components if part.component_type != "energy" and part.charge_unit != "fraction"]
    assert all(part.effective_date and part.source_url == TARIFF_URL and part.source_detail for part in record.components)


def test_rs1892_eligibility_and_conditions_come_from_the_schedule():
    record = _parse(_pages())[0]
    for phrase in ("RS 1830, 1828, 2801, 2802, 2821 or 2822", "increase their Electricity usage during the Freshet Period",
                   "May 1 to July 31", "Kingsgate-Yahk and Lardeau-Shutty Bench", "March 1", "energy and capacity"):
        assert phrase in record.eligibility
    for phrase in ("baselines", "Net to Gross Ratio", "add-on", "RS 1880", "before July 31", "taxes excluded"):
        assert phrase in record.notes
    assert "not a separate charge" in record.components[0].notes and "No average" in record.components[0].notes


def test_rs1892_passes_validation_and_exports_as_live_when_marked_live_parsed():
    scraper = BCHydroScraper()
    records = scraper.mark_live_parsed(_parse(_pages()))
    valid, invalid = validate_batch(records)
    assert len(valid) == 1 and not invalid
    assert derive_provenance(valid[0].confidence, valid[0].notes) == "live"


def test_rs1892_missing_continuation_page_fails_closed():
    assert _parse([page for page in _pages() if page.page_number != 155]) == []
    assert _parse([page for page in _pages() if page.page_number != 160]) == []


def test_rs1892_missing_or_ambiguous_date_fails_closed():
    assert _parse(_mutate(_pages(), {150}, "April 1, 2026", "April 1, 2027")) == []
    assert _parse(_mutate(_pages(), {152}, "April 1, 2026", "April 1, 2025")) == []


def test_rs1892_changed_index_formula_fails_closed():
    pages = _pages()
    assert _parse(_mutate(pages, {150}, "A $3/MWh adder", "A 3% adder")) == []
    assert _parse(_mutate(pages, {150}, "Mid-C Off-Peak weighted", "Mid-C Off-Peak simple")) == []
    assert _parse(_mutate(pages, {150}, "and $0/kWh, plus", "and $5/kWh, plus")) == []
    assert _parse(_mutate(pages, {150}, "Mid-Columbia (Mid-C)", "Palo Verde")) == []


def test_rs1892_changed_adder_value_is_carried_not_assumed():
    record = _parse(_mutate(_pages(), {150}, "A $3/MWh adder", "A $4.50/MWh adder"))[0]
    assert "$4.50/MWh adder" in record.market_reference and record.components[0].charge_value is None


def test_rs1892_changed_availability_period_or_conversion_fails_closed():
    pages = _pages()
    assert _parse(_mutate(pages, {150}, "that increase their", "that decrease their")) == []
    assert _parse(_mutate(pages, {151}, "May 1 to July 31 inclusive", "April 1 to August 31 inclusive")) == []
    assert _parse(_mutate(pages, {159}, "Bank of Canada daily exchange rate", "fixed exchange rate")) == []


def test_rs1892_missing_rider_clause_or_rider_page_fails_closed():
    pages = _pages()
    assert _parse([page for page in pages if page.page_number != 232]) == []
    assert _parse(_mutate(pages, {160}, "The Trade Income Rate Rider as set out in Rate Schedule 1904 applies",
                          "The Trade Income Rate Rider as set out in Rate Schedule 1904 may apply")) == []


def test_rs1892_page_without_the_schedule_returns_nothing():
    business = json.loads((FIXTURES / "bc_hydro_business.json").read_text(encoding="utf-8"))
    assert _parse([DocumentPage(**page) for page in business["pages"]]) == []


def test_rs1892_rejection_does_not_affect_other_transmission_parsers():
    scraper = BCHydroScraper()
    pilot_document = json.loads((FIXTURES / "bc_hydro_b10.json").read_text(encoding="utf-8"))
    pilot_pages = [DocumentPage(**page) for page in pilot_document["pages"]]
    assert scraper._parse_freshet_energy(pilot_pages) == []
    assert len(scraper._parse_transmission_pilots(pilot_pages)) == 4


def test_rs1892_full_scrape_adds_the_record_and_keeps_the_existing_seventeen_live():
    scraper = BCHydroScraper()
    pages = {}
    for name in ("bc_hydro_residential", "bc_hydro_business", "bc_hydro_b10", "bc_hydro_freshet"):
        document = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
        pages.update({page["page_number"]: DocumentPage(**page) for page in document["pages"]})
    document = [DocumentPage(1, "BC Hydro Electric Tariff, Title Page\nEffective: April 1, 2025")] + [pages[n] for n in sorted(pages)]
    with patch.object(scraper, "fetch_page", return_value=""), \
         patch.object(scraper, "fetch_bytes", return_value=b"pdf"), \
         patch("scrapers.utilities.bc_hydro.extract_pdf_pages", return_value=document):
        records = scraper.scrape()
    valid, invalid = validate_batch(records)
    assert not invalid and len(valid) == 18
    assert all(derive_provenance(record.confidence, record.notes) == "live" for record in valid)
    freshet = next(record for record in valid if record.tariff_code == "1892")
    assert freshet.components[0].charge_value is None and freshet.components[0].market_reference
    assert isinstance(freshet.components[0], RateComponent)


def test_rs1892_full_scrape_without_freshet_pages_keeps_seventeen_and_no_1892():
    scraper = BCHydroScraper()
    pages = {}
    for name in ("bc_hydro_residential", "bc_hydro_business", "bc_hydro_b10"):
        document = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
        pages.update({page["page_number"]: DocumentPage(**page) for page in document["pages"]})
    document = [DocumentPage(1, "BC Hydro Electric Tariff, Title Page\nEffective: April 1, 2025")] + [pages[n] for n in sorted(pages)]
    with patch.object(scraper, "fetch_page", return_value=""), \
         patch.object(scraper, "fetch_bytes", return_value=b"pdf"), \
         patch("scrapers.utilities.bc_hydro.extract_pdf_pages", return_value=document):
        records = scraper.scrape()
    assert len(records) == 17 and "1892" not in {record.tariff_code for record in records}
