"""City of Penticton (BC) parser tests on the October 2026 Appendix 7 Electric excerpt."""

import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities import penticton as pt
from scrapers.utils.parsing import DocumentPage

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "penticton_fees_bylaw_2026.json").read_text(encoding="utf-8"))
URL = FIXTURE["source_url"]
ACCOUNTS = FIXTURE["accounts_text"]
TODAY = date(2026, 11, 4)


def _pages(old: str = "", new: str = "") -> list[DocumentPage]:
    return [DocumentPage(p["page_number"], p["text"].replace(old, new) if old else p["text"])
            for p in FIXTURE["pages"]]


def _parse(pages=None, accounts=ACCOUNTS, today=TODAY):
    return {r.tariff_code: r for r in pt.parse_appendix(pages or _pages(), URL, accounts, today=today)}


def test_uses_the_current_year_column_dated_january_first():
    records = _parse()
    assert list(records) == ["10", "20", "25", "30", "35"]
    assert {r.effective_date for r in records.values()} == {"2026-01-01"}
    assert [(c.charge_value, c.charge_unit) for c in records["10"].components] == [(24.94, "$/month"), (0.1438, "$/kWh")]
    assert "no day" in records["10"].notes


def test_general_service_blocks_and_demand_above_45_kva():
    record = _parse()["20"]
    energy = [(c.tier_number, c.tier_threshold, c.charge_value) for c in record.components if c.component_type == "energy"]
    assert energy == [(1, 10000.0, 0.1476), (2, 100000.0, 0.1163), (3, 100000.0, 0.0815)]
    demand = [(c.tier_number, c.tier_threshold, c.charge_value, c.charge_unit) for c in record.components
              if c.component_type == "demand"]
    assert demand == [(1, 45.0, 0.0, "$/kVA/month"), (2, 45.0, 13.45, "$/kVA/month")]
    assert [c.charge_value for c in _parse()["35"].components if c.component_type == "demand"] == [0.0, 12.04]


def test_previous_year_column_is_used_only_in_that_year():
    records = _parse(today=date(2025, 6, 1))
    assert records["10"].effective_date == "2025-01-01"
    assert records["10"].components[0].charge_value == 21.81


def test_year_without_a_column_fails_closed():
    with pytest.raises(ValueError, match="no 2027 column"):
        _parse(today=date(2027, 1, 2))


def test_monthly_billing_evidence_is_required():
    with pytest.raises(ValueError, match="monthly billing"):
        _parse(accounts="City Utility bills are mailed every two months.")


def test_city_accounts_and_lighting_are_excluded():
    assert not set(_parse()) & {"45", "55"}


def test_missing_class_fails_closed():
    pages = _pages("Rate Code 30 - General - Secondary metered and customer owned Transformation", "Rate Code 30")
    with pytest.raises(ValueError, match="30"):
        _parse(pages)


def test_directory_link_discovery():
    html = ('<a href="/sites/default/files/uploads/bylaws/2014-07%20Fees.pdf">Fees and Charges Bylaw No. 2014-07 '
            '(Consolidated Package October 2026)</a>')
    assert pt.find_bylaw_url(html) == "https://www.penticton.ca/sites/default/files/uploads/bylaws/2014-07%20Fees.pdf"
    assert pt.find_bylaw_url('<a href="/x.pdf">Electric Utility Services Bylaw No. 2017-44</a>') is None
