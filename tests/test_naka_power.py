"""Naka Power Utilities (NWT) parser tests on the July 1, 2026 rate schedule (source-derived fixture)."""

import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities import naka_power as nk
from scrapers.utils.parsing import DocumentPage

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "naka_power_schedule_2026-07-01.json")
                     .read_text(encoding="utf-8"))
URL = FIXTURE["source_url"]
TODAY = date(2026, 11, 19)
INTERIM = ("2026-07-01", True)


def _pages(old: str = "", new: str = "", page: int = 0) -> list[DocumentPage]:
    return [DocumentPage(p["page_number"], p["text"].replace(old, new, 1)
                         if old and (not page or p["page_number"] == page) else p["text"])
            for p in FIXTURE["pages"]]


def _parse(pages=None, today=TODAY, label_date="2026-07-01", update=INTERIM):
    records, rejections = nk.parse_schedule(pages or _pages(), URL, today=today, label_date=label_date,
                                            update=update)
    return {r.tariff_code: r for r in records}, rejections


def _values(record):
    return {c.component_name: (c.charge_value, c.charge_unit) for c in record.components}


def test_parses_each_zone_with_base_rates_and_dated_riders():
    records, rejections = _parse()
    assert list(records) == ["SNARE-RES", "SNARE-GS", "TALTSON-RES", "TALTSON-GS", "TALTSON-LGS", "THERMAL-RES"]
    assert {r.effective_date for r in records.values()} == {"2026-07-01"}
    snare = records["SNARE-RES"]
    assert _values(snare) == {
        "Customer Charge": (18.0, "$/month"), "Energy Charge": (0.2372, "$/kWh"),
        "Purchase Power Cost Adjustment (Rider F)": (0.1084, "$/kWh"),
        "Revenue Adjustment (Rider R)": (8.199, "%"), "Franchise Tax": (2.464, "%")}
    assert [c.effective_date for c in snare.components] == ["2012-01-01", "2012-01-01", "2026-07-01",
                                                            "2026-07-01", "2026-01-01"]
    assert "Rider G): 0 cents/kWh (since 2026-06-01)" in snare.notes
    assert _values(records["SNARE-GS"])["Demand Charge"] == (14.68, "$/kVA/month")
    taltson = _values(records["TALTSON-RES"])
    assert taltson["Supply Charge"] == (0.2094, "$/kWh") and taltson["Fuel Charge"] == (0.1148, "$/kWh")
    assert taltson["Temporary Refund/Surcharge (Rider E)"] == (8.0, "%")
    credit = next(c for c in records["TALTSON-RES"].components if c.component_name.endswith("(Rider A)"))
    assert (credit.component_type, credit.charge_value) == ("rebate", -0.0931)
    assert "Franchise Tax" not in taltson


def test_general_service_energy_blocks_are_per_kw_of_billing_demand():
    records, _ = _parse()
    tiers = [(c.component_name, c.charge_value, c.tier_number, c.tier_threshold, c.tier_unit)
             for c in records["TALTSON-LGS"].components if c.component_type == "energy"]
    assert tiers == [
        ("Supply Charge — First 200 kWh/kW", 0.0912, 1, 200.0, "kWh/kW of billing demand/month"),
        ("Supply Charge — Balance", 0.0138, 2, 200.0, "kWh/kW of billing demand/month"),
        ("Fuel Charge — First 200 kWh/kW", 0.1148, 1, 200.0, "kWh/kW of billing demand/month"),
        ("Fuel Charge — Balance", 0.1148, 2, 200.0, "kWh/kW of billing demand/month")]
    assert "loads over 200 kW" in records["TALTSON-LGS"].notes
    assert "(h) 20 kW" in records["TALTSON-LGS"].components[0].notes


def test_thermal_general_service_fails_closed_on_its_printed_total():
    records, rejections = _parse()
    assert "THERMAL-GS" not in records
    assert rejections == {"THERMAL-GS": "Demand Charge $14.00 / kW does not equal the printed total $10.00 / kW"}


def test_gnwt_programs_are_conditional_alternatives_for_non_government_customers():
    records, _ = _parse()
    assert not any("TPSP" in c.component_name for c in records["SNARE-RES"].components)
    for code in ("TALTSON-RES", "THERMAL-RES"):
        tpsp = [(c.charge_value, c.tier_threshold, c.season) for c in records[code].components
                if "TPSP" in c.component_name]
        assert tpsp == [(0.365, 1000.0, "September 1 to March 31"), (0.365, 600.0, "April 1 to August 31")]
    grep = [c for c in records["THERMAL-RES"].components if "GREP" in c.component_name]
    assert [(c.charge_value, c.charge_unit) for c in grep] == [(18.0, "$/month"), (0.8394, "$/kWh")]
    assert all(c.notes.startswith("Conditional alternative") for c in grep)


def test_interim_status_comes_from_the_matching_rate_update_notice():
    records, _ = _parse()
    assert records["SNARE-RES"].confidence == "medium" and "interim refundable" in records["SNARE-RES"].notes
    unknown, _ = _parse(update=("2026-06-01", True))
    assert unknown["SNARE-RES"].confidence == "medium" and "not confirmed" in unknown["SNARE-RES"].notes
    final, _ = _parse(update=("2026-07-01", False))
    assert final["SNARE-RES"].confidence == "high"
    assert nk.parse_rate_update(FIXTURE["rate_update_html"]) == ("2026-07-01", True)


def test_schedule_date_and_link_must_agree_and_be_in_effect():
    with pytest.raises(ValueError, match="newest date is 2026-07-01"):
        _parse(label_date="2026-06-01")
    with pytest.raises(ValueError, match="takes effect 2026-07-01"):
        _parse(today=date(2026, 6, 30))


def test_a_listed_rider_without_its_table_rejects_the_class():
    pages = _pages("RIDER T 25 kV DEFERRAL ACCOUNT", "DEFERRAL ACCOUNT", page=29)
    records, rejections = _parse(pages)
    assert rejections["SNARE-RES"] == "25 kV Deferral Account (Rider T) is listed but its zone table was not found"
    assert "SNARE-RES" not in records and "TALTSON-RES" in records


def test_discovery_requires_one_current_schedule_link():
    url, when = nk.find_schedule(FIXTURE["rates_page_html"], FIXTURE["rates_page_url"])
    assert (url, when) == (URL, "2026-07-01")
    assert nk.find_rate_update_url(FIXTURE["rates_page_html"], FIXTURE["rates_page_url"]) == FIXTURE["rate_update_url"]
    conflicting = FIXTURE["rates_page_html"] + '<a href="/other.pdf">Rate Schedule (effective August 1, 2026)</a>'
    with pytest.raises(ValueError, match="different current schedules"):
        nk.find_schedule(conflicting)


def test_scraper_marks_live_records_and_returns_nothing_when_the_page_fails(monkeypatch):
    scraper = nk.NakaPowerScraper()
    pages = {FIXTURE["rates_page_url"]: FIXTURE["rates_page_html"], FIXTURE["rate_update_url"]: FIXTURE["rate_update_html"]}
    monkeypatch.setattr(scraper, "fetch_page", lambda url, delay=1.0: pages[url])
    monkeypatch.setattr(scraper, "fetch_bytes", lambda url, delay=1.0: b"%PDF" if url == URL else None)
    monkeypatch.setattr(nk, "extract_pdf_pages", lambda data, **options: _pages())
    monkeypatch.setattr(nk, "date", type("D", (date,), {"today": staticmethod(lambda: TODAY)}))
    records = scraper.scrape()
    assert len(records) == 6 and all(r.notes.startswith("Provenance: live_parsed") for r in records)

    def refused(url, delay=1.0):
        raise RuntimeError("HTTP 403")

    monkeypatch.setattr(scraper, "fetch_page", refused)
    assert scraper.scrape() == []
