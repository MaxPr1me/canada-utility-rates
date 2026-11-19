"""City of Red Deer Electric Light & Power parser tests (Schedules A and D of Bylaw 3273/2000 and the City's pages)."""

import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities import red_deer as rd
from scrapers.utils.parsing import DocumentPage

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "red_deer_tariff_2026-03-01.json")
                     .read_text(encoding="utf-8"))
TODAY = date(2026, 11, 19)


def _pages(key: str, old: str = "", new: str = "") -> list[DocumentPage]:
    return [DocumentPage(p["page_number"], p["text"].replace(old, new, 1) if old else p["text"])
            for p in FIXTURE[key]]


def _build(schedule_a=None, delivery=None, rolr=None, today=TODAY):
    records, rejections = rd.build_records(
        rd.parse_schedule_a(schedule_a or _pages("schedule_a_pages")), rd.parse_schedule_d(_pages("schedule_d_pages")),
        rd.parse_delivery_page(delivery or FIXTURE["delivery_page_html"]),
        rd.parse_rolr_page(rolr or FIXTURE["rolr_page_html"], today), today)
    return {r.tariff_code: r for r in records}, rejections


def _values(record):
    return {c.component_name: (c.component_type, c.charge_value, c.charge_unit) for c in record.components}


def test_wires_records_keep_system_and_distribution_access_apart():
    records, rejections = _build()
    assert list(records) == ["61", "63", "64", "78", "RRT-61", "RRT-63", "RRT-64", "RRT-78"] and not rejections
    assert _values(records["64"]) == {
        "System Access Demand Charge": ("transmission", 0.2533, "$/kVA/day"),
        "Distribution Access Demand Charge": ("demand", 0.1847, "$/kVA/day"),
        "System Access Variable Charge": ("transmission", 0.0143, "$/kWh"),
        "Distribution Access Variable Charge": ("distribution", 0.0143, "$/kWh"),
        "Balancing Pool Allocation": ("rider", 0.00131, "$/kWh"),
        "Transmission Rider (2026 Q4)": ("rider", 0.0024, "$/kWh")}
    rider = records["61"].components[-1]
    assert (rider.effective_date, rider.end_date) == ("2026-10-01", "2026-12-31")
    assert "Local Access Fee: 15.00%" in records["63"].notes


def test_quarterly_transmission_rider_follows_the_date():
    records, _ = _build(today=date(2026, 5, 2))
    rider = records["61"].components[-1]
    assert (rider.component_name, rider.charge_value, rider.effective_date) == (
        "Transmission Rider (2026 Q2)", 0.0024, "2026-04-01")
    _, rejections = _build(today=date(2027, 1, 4))
    assert rejections["61"] == "no 2027 Q1 Transmission Rider on the delivery page"


def test_schedule_a_must_match_the_delivery_page():
    records, rejections = _build(delivery=FIXTURE["delivery_page_html"].replace("0.6949", "0.6950", 1))
    assert rejections == {"61": "SA Basic Charge ($/day): Schedule A 0.6949 vs delivery page 0.695"}
    assert "63" in records


def test_rate_of_last_resort_uses_schedule_d_administration_and_one_energy_price():
    records, _ = _build()
    residential, commercial = records["RRT-61"], records["RRT-78"]
    assert _values(residential) == {"RoLR Energy Charge": ("energy", 0.1206, "$/kWh"),
                                    "RoLR Administration Charge": ("fixed", 0.3035, "$/day")}
    assert "still shows $0.2498/day from January 2026" in residential.components[1].notes
    assert "'-' under Commercial" in commercial.components[0].notes
    assert residential.end_date == "2026-12-31"
    _, rejections = _build(today=date(2027, 1, 4))
    assert rejections["RRT-61"] == "no Rate of Last Resort energy price in effect on the City's page"


def test_future_schedule_fails_closed():
    pages = _pages("schedule_a_pages", "effective on March 1, 2026", "effective on December 1, 2026")
    with pytest.raises(ValueError, match="Schedule A takes effect 2026-12-01"):
        _build(schedule_a=pages)
