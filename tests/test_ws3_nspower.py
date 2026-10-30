"""Phase 6D: NS Power One-Part Real Time Pricing (Schedules B and C) with a value-less market energy line."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper
from scrapers.utils.parsing import DocumentPage

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RTP = json.loads((FIXTURES / "nova_scotia_rtp.json").read_text(encoding="utf-8"))
RESIDENTIAL = json.loads((FIXTURES / "nova_scotia_residential.json").read_text(encoding="utf-8"))
INDUSTRIAL = json.loads((FIXTURES / "nova_scotia_industrial.json").read_text(encoding="utf-8"))
TODAY = "2026-10-30"
SOURCE = RTP["source_url"]


@pytest.fixture
def rtp():
    return copy.deepcopy(RTP)


def _pages(rtp, drop=()):
    merged = {page["page_number"]: page for page in RESIDENTIAL["pages"]}
    for group in RESIDENTIAL["building_pages"].values():
        merged.update({page["page_number"]: page for page in group})
    merged.update({page["page_number"]: page for page in INDUSTRIAL["pages"]})
    merged.update({page["page_number"]: page for page in rtp["pages"]})
    return [DocumentPage(**page) for number, page in sorted(merged.items()) if number not in drop]


def _products():
    return {kind: product["html"] for kind, product in RESIDENTIAL["products"].items()}


def _parse(rtp, today=TODAY, drop=()):
    scraper = NovaScotiaPowerScraper()
    with patch.object(scraper, "now_iso", return_value=today + "T00:00:00+00:00"):
        records = scraper._parse_rtp_tariffs(_pages(rtp, drop), _products(), SOURCE)
    return {record.tariff_code: record for record in records}


def _edit(rtp, page_number, old, new):
    page = next(page for page in rtp["pages"] if page["page_number"] == page_number)
    assert old in page["text"]
    page["text"] = page["text"].replace(old, new)


def _edit_shared(rtp, source, page_number, old, new):
    """Move a shared rider page into the RTP fixture so a test can edit it without touching other fixtures."""
    page = next(p for p in source["pages"] if p["page_number"] == page_number)
    assert old in page["text"]
    rtp["pages"].append({"page_number": page_number, "text": page["text"].replace(old, new)})


def _by_name(record):
    return {c.component_name: c for c in record.components}


def test_both_schedules_parse_as_market_based_industrial_records(rtp):
    records = _parse(rtp)
    assert set(records) == {"RTP-T", "RTP-D"}
    for record in records.values():
        assert record.customer_class == "industrial" and record.rate_structure == "market"
        assert record.pricing_method == "market_based" and record.market_reference
        assert record.effective_date == "2026-05-01" and record.end_date == "2026-12-31"
        assert record.demand_min_kw == 1800.0 and "no bill total is calculated" in record.notes
        assert "2,000 KVA or 1,800 kW, and over" in record.eligibility
        assert "written request" in record.eligibility
    assert records["RTP-T"].tariff_name == "One-Part Transmission Real Time Pricing"
    assert records["RTP-T"].sub_class == "large real time pricing transmission voltage"
    assert "transmission voltage of 69 kV or higher" in records["RTP-T"].eligibility
    assert records["RTP-D"].tariff_name == "One-Part Distribution Voltage Real Time Pricing"
    assert records["RTP-D"].sub_class == "large real time pricing distribution voltage"
    assert "voltage less than 69 kV" in records["RTP-D"].eligibility


def test_energy_line_is_value_less_market_component_and_nothing_is_averaged(rtp):
    for record in _parse(rtp).values():
        energy = [c for c in record.components if c.component_type == "energy"]
        assert len(energy) == 1
        market = energy[0]
        assert market.charge_value is None and market.charge_unit == "$/kWh"
        assert market.market_reference and "hourly marginal energy cost" in market.market_reference
        assert market.market_source_url == SOURCE and market.source_url == SOURCE
        assert "no average or estimated price is stored" in market.notes
        assert not [c for c in record.components if c.component_type == "demand"]
        assert "Demand charge: nil" in record.notes


@pytest.mark.parametrize("code,on_peak,off_peak", [("RTP-T", 0.05274, 0.00713), ("RTP-D", 0.09925, 0.03516)])
def test_fixed_cost_adders_and_credit_use_printed_values_and_units(rtp, code, on_peak, off_peak):
    c = _by_name(_parse(rtp)[code])
    on, off = c["Fixed Cost Adder - On-Peak"], c["Fixed Cost Adder - Off-Peak"]
    assert (on.charge_value, on.charge_unit, on.tou_period) == (on_peak, "$/kWh", "on-peak")
    assert (off.charge_value, off.charge_unit, off.tou_period) == (off_peak, "$/kWh", "off-peak")
    assert "weekends and holidays" in off.tou_hours and "non-holiday weekdays" in on.tou_hours
    assert on.effective_date == off.effective_date == "2026-04-01" and on.confidence == off.confidence == "medium"
    credit = c["Customer-Owned Transformer Credit"]
    assert (credit.charge_value, credit.charge_unit, credit.sub_component) == (-0.32, "$/kVA/month", "conditional")


def test_dsm_and_storm_riders_are_dated_separately_and_fam_is_not_assumed(rtp):
    for record in _parse(rtp).values():
        c = _by_name(record)
        dsm, storm = c["DSM Cost Recovery Rider"], c["Storm Cost Recovery Rider"]
        assert (dsm.charge_value, dsm.charge_unit, dsm.effective_date, dsm.end_date) == (0.0001, "$/kWh", "2026-01-01", "2026-12-31")
        assert (storm.charge_value, storm.effective_date, storm.end_date) == (0.0, "2026-05-01", "2026-12-31")
        assert "PCR 0.0 and BA 0.01" in dsm.notes
        assert not [x for x in record.components if "FAM" in x.component_name]
        assert "No FAM rate is shown" in record.notes
        assert {x.component_name for x in record.components} == {
            "Energy Charge - NSPI actual hourly marginal energy cost", "Fixed Cost Adder - On-Peak", "Fixed Cost Adder - Off-Peak",
            "Customer-Owned Transformer Credit", "DSM Cost Recovery Rider", "Storm Cost Recovery Rider"}


def test_old_web_page_adders_are_never_used(rtp):
    values = {c.charge_value for record in _parse(rtp).values() for c in record.components}
    assert not values & {0.05071, 0.00475, 0.06813, 0.00828, 0.08991, 0.02582}


def test_scanned_page_unit_misread_and_page_number_misread_are_tolerated(rtp):
    text = " ".join(p["text"] for p in rtp["pages"] if p["page_number"] in (89, 92))
    assert "0.713 e/kWh" in text and "Page l of 3" in text
    assert len(_parse(rtp)) == 2


def test_adders_follow_source(rtp):
    _edit(rtp, 89, "5.274 c/kWh", "5.300 c/kWh")
    _edit(rtp, 92, "3.516 c/kWh", "3.600 c/kWh")
    records = _parse(rtp)
    assert _by_name(records["RTP-T"])["Fixed Cost Adder - On-Peak"].charge_value == 0.053
    assert _by_name(records["RTP-D"])["Fixed Cost Adder - Off-Peak"].charge_value == 0.036


def test_rejects_implausible_or_reversed_adders_per_tariff(rtp):
    _edit(rtp, 89, "0.713 e/kWh", "6.000 e/kWh")
    assert set(_parse(rtp)) == {"RTP-D"}


def test_rejects_changed_credit_or_eligibility(rtp):
    _edit(rtp, 92, "A credit equal to 32 cents", "A credit equal to 35 cents")
    _edit(rtp, 89, "transmission voltage of 69 kV or higher", "transmission voltage of 138 kV or higher")
    assert _parse(rtp) == {}


def test_missing_continuation_page_omits_only_that_tariff(rtp):
    rtp["pages"] = [p for p in rtp["pages"] if p["page_number"] != 91]
    assert set(_parse(rtp)) == {"RTP-D"}


def test_missing_hourly_price_terms_or_conditions_fail_closed(rtp):
    _edit(rtp, 89, "final twenty minutes prior to the commencement", "final shortly before the commencement")
    _edit(rtp, 93, "minimum of twelve months", "minimum of six months")
    assert _parse(rtp) == {}


def test_effective_dates_outside_supported_year_fail_closed(rtp):
    for page_number in (89, 90, 91):
        _edit(rtp, page_number, "Effective: April 1, 2026", "Effective: April 1, 2027")
    assert set(_parse(rtp)) == {"RTP-D"}
    assert _parse(copy.deepcopy(RTP), today="2027-01-02") == {}
    assert _parse(copy.deepcopy(RTP), today="2026-03-01") == {}


def test_inconsistent_page_footers_fail_closed(rtp):
    _edit(rtp, 94, "Effective: April 1, 2026", "Effective: May 1, 2026")
    assert set(_parse(rtp)) == {"RTP-T"}


def test_a_printed_fam_row_fails_closed_until_the_parser_is_reviewed(rtp):
    _edit_shared(rtp, INDUSTRIAL, 66, "FUEL ADJUSTMENT MECHANISM (FAM) TARIFF Page 2 of 4",
                 "FUEL ADJUSTMENT MECHANISM (FAM) TARIFF Page 2 of 4\nOne Part Real Time Pricing 0.100 0.100")
    assert _parse(rtp) == {}


def test_changed_dsm_breakdown_or_missing_rider_row_fails_closed(rtp):
    _edit_shared(rtp, INDUSTRIAL, 76, "One Part Real Time Pricing 0.000 0.010 0.010", "One Part Real Time Pricing 0.000 0.010 0.020")
    assert _parse(rtp) == {}
    other = copy.deepcopy(RTP)
    _edit_shared(other, INDUSTRIAL, 79, "One-Part Real Time Pricing 0.000", "One-Part Real Time Pricing")
    assert _parse(other) == {}


def test_unsupported_book_context_returns_nothing(rtp):
    assert _parse(rtp, drop=(1,)) == {}


def test_live_commercial_pipeline_adds_both_records_without_seed_fallback(rtp):
    scraper = NovaScotiaPowerScraper()
    scraper._book = (_pages(rtp), _products(), SOURCE)
    business_html = RESIDENTIAL["business_pilot"]["business_html"]
    with patch.object(scraper, "now_iso", return_value=TODAY + "T00:00:00+00:00"), \
            patch.object(scraper, "fetch_page", return_value=business_html):
        records = scraper._try_live_commercial()
    codes = {record.tariff_code for record in records}
    assert {"RTP-T", "RTP-D", "21", "22", "23", "25"} <= codes
    marked = scraper.mark_live_parsed([r for r in records if r.tariff_code.startswith("RTP")])
    assert all("Provenance: live_parsed" in record.notes for record in marked)
