"""City of Medicine Hat Electric Utility parser tests (2026 brochure columns and energy-page excerpt)."""

import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities import medicine_hat as mh
from scrapers.utils.parsing import DocumentPage

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "medicine_hat_rates_2026.json").read_text(encoding="utf-8"))
URL = FIXTURE["source_url"]
HTML = FIXTURE["energy_page_html"]
TODAY = date(2026, 11, 19)


def _pages(old: str = "", new: str = "") -> list[DocumentPage]:
    return [DocumentPage(p["page_number"], p["text"].replace(old, new, 1) if old else p["text"])
            for p in FIXTURE["pages"]]


def _parse(pages=None, html=HTML, today=TODAY):
    records, rejections = mh.parse_rates(pages or _pages(), mh.parse_energy_page(html, today), URL, today)
    return {r.tariff_code: r for r in records}, rejections


def _values(record):
    return {c.component_name: (c.charge_value, c.charge_unit) for c in record.components}


def test_bundled_records_read_each_brochure_column_separately():
    records, rejections = _parse()
    assert list(records) == ["1.1", "3.1", "3.3", "4.1", "5.1"] and not rejections
    assert _values(records["3.3"]) == {
        "Service Charge": (3.2586, "$/day"), "Administration Charge": (0.6724, "$/day"),
        "Demand Charge": (6.7, "$/kVA/month"), "Capacity Charge": (0.02859, "$/kWh"),
        "Default Energy Charge": (0.07, "$/kWh"), "Going Green Surcharge": (0.005, "$/kWh")}
    assert _values(records["4.1"])["Demand Charge"] == (6.26, "$/kVA/month")
    assert _values(records["5.1"])["Administration Charge"] == (61.4529, "$/day")
    assert "$0.52952/day and $1.08875/kVA" in records["3.3"].notes
    assert not any("MCAF" in c.component_name for r in records.values() for c in r.components)


def test_monthly_energy_and_going_green_are_dated_to_the_current_month():
    records, _ = _parse()
    residential = records["1.1"]
    monthly = [(c.component_name, c.effective_date, c.end_date) for c in residential.components if c.end_date]
    assert monthly == [("Default Energy Charge", "2026-11-01", "2026-11-30"),
                       ("Going Green Surcharge", "2026-11-01", "2026-11-30")]
    assert residential.effective_date == "2026-11-01"
    # The record ends with its month-dated prices, so models and the gate stop using it after November.
    assert residential.end_date == "2026-11-30" and records["3.3"].end_date == "2026-11-30"
    tiers = [(c.charge_value, c.tier_number, c.tier_threshold, c.tier_unit) for c in residential.components
             if c.component_name.startswith("Environmental Conservation")]
    assert tiers == [(0.0, 1, 950.0, "kWh/month"), (0.0074, 2, 950.0, "kWh/month")]
    with pytest.raises(ValueError, match="no single December 2026 default electricity rate"):
        mh.parse_energy_page(HTML, date(2026, 12, 1))


def test_large_customers_use_the_fixed_term_rate_and_fail_closed_after_it():
    records, _ = _parse()
    energy = [c for c in records["4.1"].components if c.component_name.startswith("Default Energy")]
    assert [(c.charge_value, c.effective_date, c.end_date) for c in energy] == [(0.12025, "2025-01-01", "2026-12-31")]
    assert records["4.1"].end_date == records["5.1"].end_date == "2026-12-31"
    assert "Going Green Surcharge" not in _values(records["5.1"])
    assert "Kept out of the representative models" in records["5.1"].notes
    energy = mh.parse_energy_page(HTML, TODAY)
    _, rejections = mh.parse_rates(_pages(), energy, URL, date(2027, 1, 2))
    assert rejections["4.1"] == "no Large Commercial/Industrial default energy rate in effect today"


def test_current_rate_must_equal_the_month_row():
    with pytest.raises(ValueError, match="does not equal"):
        mh.parse_energy_page(HTML.replace("$0.07000 / kWh", "$0.07500 / kWh", 1), TODAY)


def test_a_missing_charge_rejects_only_its_class():
    pages = _pages("Demand Charge $6.70 per kVA", "Demand Charge per kVA")
    records, rejections = _parse(pages)
    assert rejections == {"3.3": "missing Demand Charge"} and "3.1" in records


def test_brochure_link_discovery():
    assert mh.find_brochure_url(HTML) == URL
