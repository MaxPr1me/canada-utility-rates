"""City of Lethbridge Electric Utility parser tests (Bylaw 6364 consolidation, 2026 rate table, rates page)."""

import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities import lethbridge as lb
from scrapers.utils.parsing import DocumentPage

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "lethbridge_tariff_2026.json").read_text(encoding="utf-8"))
TODAY = date(2026, 11, 19)


def _bylaw(old: str = "", new: str = ""):
    return lb.parse_bylaw([DocumentPage(p["page_number"], p["text"].replace(old, new, 1) if old else p["text"])
                           for p in FIXTURE["bylaw_pages"]])


def _parse(bylaw=None, words=None, html=None, today=TODAY):
    records, rejections = lb.parse_tariff(
        bylaw or _bylaw(), lb.parse_rate_table(words or FIXTURE["rate_table_words"]),
        lb.parse_rates_page(html or FIXTURE["rates_page_html"], today), FIXTURE["bylaw_url"],
        FIXTURE["rate_table_url"], today)
    return {r.tariff_code: r for r in records}, rejections


def _values(record):
    return {c.component_name: (c.component_type, c.charge_value, c.charge_unit) for c in record.components}


def test_wires_records_keep_transmission_and_distribution_apart_with_dated_riders():
    records, rejections = _parse()
    assert list(records) == ["991", "992", "994", "995", "996", "997", "RoLR-Res", "RoLR-SB"] and not rejections
    assert _values(records["991"]) == {
        "Transmission System Usage Charge": ("transmission", 0.0338, "$/kWh"),
        "Transmission Service and Facilities Charge": ("transmission", 0.3509, "$/day"),
        "Distribution System Usage Charge": ("distribution", 0.0209, "$/kWh"),
        "Distribution Service and Facilities Charge": ("fixed", 0.9372, "$/day"),
        "Rider B - Balancing Pool Consumer Allocation Rider": ("rider", 0.00126, "$/kWh"),
        "Rider C - AESO DTS Rider": ("rebate", -0.012, "$/kWh")}
    assert records["991"].effective_date == "2026-11-01"
    assert "15.50% of the total distribution and transmission access charges" in records["994"].notes
    assert _values(records["995"])["Distribution Demand Charge"] == ("demand", 0.2176, "$/kVA/day")


def test_large_rates_price_transmission_usage_on_and_off_peak():
    records, _ = _parse()
    peak = [(c.charge_value, c.tou_period, c.tou_hours) for c in records["996"].components if c.tou_period]
    assert peak == [(0.0217, "on-peak", "07:00 to 23:00, every day of the week"),
                    (0.018, "off-peak", "All hours outside On-Peak")]


def test_rate_of_last_resort_runs_for_the_current_year_and_skips_the_undefined_rds_price():
    records, _ = _parse()
    rolr = records["RoLR-Res"]
    assert [(c.charge_value, c.effective_date, c.end_date) for c in rolr.components] == [
        (0.09975, "2026-01-01", "2026-12-31")]
    assert "'RDS' price (0.10388 $/kWh) without defining it" in rolr.notes
    _, rejections = _parse(today=date(2027, 1, 4))
    assert rejections["RoLR"].startswith("no 2027 Rate of Last Resort price")


def test_bylaw_and_rate_table_must_agree():
    words = [dict(word, text="0.0339") if word["text"] == "0.0338" else word for word in FIXTURE["rate_table_words"]]
    records, rejections = _parse(words=words)
    assert rejections == {"991": "bylaw and rate table disagree: transmission System Usage Charge 0.0338 vs rate "
                                 "table 0.0339"}
    assert "994" in records


def test_riders_must_match_the_rider_table():
    html = FIXTURE["rates_page_html"].replace("Rider B: $0.00126/kWh", "Rider B: $0.00200/kWh", 1)
    records, rejections = _parse(html=html)
    assert rejections["riders"].startswith("Riders A/B/C") and rejections["991"] == "City riders unavailable"
    assert set(records) == {"RoLR-Res", "RoLR-SB"}


def test_document_years_and_dates_fail_closed():
    with pytest.raises(ValueError, match="rate table year 2026 differs"):
        _parse(bylaw=_bylaw("2. The 2026 Electric Distribution Rates", "2. The 2027 Electric Distribution Rates"))
    with pytest.raises(ValueError, match="take effect 2026-01-01"):
        _parse(today=date(2025, 12, 31))


def test_document_links():
    url, text = lb.find_link(FIXTURE["electric_page_html"], r"Bylaw \d+ Electric Distribution Tariff",
                             FIXTURE["electric_page_url"])
    assert url == FIXTURE["bylaw_url"] and text == "Bylaw 6466 Electric Distribution Tariff"
    assert lb.find_link(FIXTURE["rates_page_html"], r"20\d\d Rate Table", FIXTURE["rates_page_url"])[0] == \
        FIXTURE["rate_table_url"]
