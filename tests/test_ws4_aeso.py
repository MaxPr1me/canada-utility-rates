"""Deterministic tests for the AESO pool price market reference (no network)."""
import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities import aeso
from scrapers.utilities.aeso import AESOScraper, AESOVerificationError

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "aeso.json").read_text(encoding="utf-8"))
TODAY = date(2026, 10, 30)


def _csv(days=range(24, 31), *, header=None, extra_rows=(), unposted_from=(30, 10)):
    """A week of hourly rows; hours from unposted_from (day, hour) on show '-'."""
    lines = [header if header is not None else FIXTURE["csv_header"].rstrip("\n")]
    for day in days:
        for hour in range(1, 25):
            label = f"10/{day:02d}/2026 {hour:02d}"
            if (day, hour) >= unposted_from:
                lines.append(f'"{label}","-","-","-"')
            else:
                price = 29.80 + hour
                lines.append(f'"{label}","{price:.2f}","40.66","10052.0"')
    lines.extend(extra_rows)
    return "\n".join(lines) + "\n"


def _scraper(monkeypatch, csv_text=None, metadata_text=None, document_date=None, today=TODAY):
    scraper = AESOScraper()
    monkeypatch.setattr(aeso, "_today", lambda: today)
    csv_text = _csv() if csv_text is None else csv_text

    def fetch_bytes(url, delay=1.0):
        if url.startswith(aeso.REPORT_URL):
            return csv_text.encode("utf-8")
        assert url == aeso.METADATA_URL
        return b"%PDF"

    monkeypatch.setattr(scraper, "fetch_bytes", fetch_bytes)
    monkeypatch.setattr(aeso, "metadata_document", lambda _bytes: (
        FIXTURE["metadata_text"] if metadata_text is None else metadata_text,
        FIXTURE["metadata_document_date"] if document_date is None else document_date))
    return scraper


def test_fixture_urls_match_the_scraper_constants():
    assert FIXTURE["source_url"] == aeso.REPORT_URL
    assert FIXTURE["metadata_url"] == aeso.METADATA_URL
    assert aeso.report_csv_url(date(2026, 10, 23), date(2026, 10, 31)) == (
        aeso.REPORT_URL + "?beginDate=10232026&endDate=10312026&contentType=csv")


def test_live_record_is_a_value_less_market_reference_with_the_metadata_date(monkeypatch):
    (record,) = _scraper(monkeypatch).scrape()
    assert record.tariff_name == "AESO Pool Price Reference" and record.tariff_code == "POOL"
    assert record.rate_structure == "market" and record.pricing_method == "market_based"
    assert record.effective_date == "2025-05-28" and record.source_url == aeso.METADATA_URL
    assert record.notes.startswith("Provenance: live_parsed.")
    (component,) = record.components
    assert component.charge_value is None and component.charge_unit == "$/MWh"
    assert component.market_reference == aeso.MARKET_REFERENCE
    assert component.market_source_url == aeso.REPORT_URL
    assert component.notes.startswith("Provenance: live_parsed.")
    assert "seed_fallback" not in record.notes


def test_no_observed_number_is_stored_in_the_live_record(monkeypatch):
    (record,) = _scraper(monkeypatch).scrape()
    assert all(c.charge_value is None for c in record.components)
    assert "29.8" not in record.notes and "29.8" not in record.components[0].notes


def test_csv_parser_skips_unposted_hours_and_reads_the_fall_back_hour():
    rows = ['"11/02/2025 02","61.50","40.00","9000.0"', '"11/02/2025 02*","999.99","40.00","9000.0"',
            '"11/02/2025 03","-","-","-"']
    prices = aeso.parse_pool_price_csv(FIXTURE["csv_header"] + "\n".join(rows) + "\n")
    assert [(p[0], p[1], p[2]) for p in prices] == [
        (date(2025, 11, 2), "02", 61.5), (date(2025, 11, 2), "02*", 999.99)]
    fixture_rows = "\n".join(",".join(f'"{c}"' for c in r)
                             for r in FIXTURE["csv_rows_posted"] + FIXTURE["csv_rows_unposted"])
    parsed = aeso.parse_pool_price_csv(FIXTURE["csv_header"] + fixture_rows + "\n")
    assert [p[2] for p in parsed] == [29.8, 28.61]


@pytest.mark.parametrize("csv_text, message", [
    ("Pool Price\n\nDate,Price\n", "header not found"),
    (_csv(extra_rows=['"10/29/2026 05","-1.00","40.66","10052.0"']), "outside"),
    (_csv(extra_rows=['"10/29/2026 05","1000.00","40.66","10052.0"']), "outside"),
    (_csv(extra_rows=['"bad label","10.00","40.66","10052.0"']), "unreadable pool price hour label"),
    (_csv(extra_rows=['"10/29/2026 05","abc","40.66","10052.0"']), "unreadable pool price row"),
    (_csv(extra_rows=['"10/29/2026 05","10.00"']), "unexpected pool price row"),
])
def test_csv_changes_fail_closed(monkeypatch, caplog, csv_text, message):
    records = _scraper(monkeypatch, csv_text=csv_text).scrape()
    (record,) = records
    assert "seed_fallback" in record.notes and record.components[0].charge_value == aeso.SEED_POOL_PRICE["average_pool_price"]
    assert message in caplog.text


def test_stale_future_or_thin_data_is_not_live(monkeypatch):
    stale = _csv(days=range(20, 24), unposted_from=(99, 1))
    for csv_text in (stale, _csv(days=range(30, 31), unposted_from=(30, 5))):
        (record,) = _scraper(monkeypatch, csv_text=csv_text).scrape()
        assert "seed_fallback" in record.notes
    prices = aeso.parse_pool_price_csv(_csv())
    assert aeso.verify_recent_prices(prices, TODAY) == date(2026, 10, 30)
    with pytest.raises(AESOVerificationError, match="future"):
        aeso.verify_recent_prices(prices, date(2026, 10, 29))
    with pytest.raises(AESOVerificationError, match="days old"):
        aeso.verify_recent_prices(prices, date(2026, 11, 5))


@pytest.mark.parametrize("kwargs, message", [
    ({"metadata_text": "Pool price is something else."}, "no longer says"),
    ({"metadata_text": FIXTURE["metadata_text"].replace("time weighted", "simple")}, "time weighted"),
    ({"document_date": ""}, "no document date"),
])
def test_metadata_changes_fail_closed(monkeypatch, caplog, kwargs, message):
    (record,) = _scraper(monkeypatch, **kwargs).scrape()
    assert "seed_fallback" in record.notes
    assert message in caplog.text


def test_any_fetch_failure_falls_back_to_the_labelled_seed(monkeypatch):
    scraper = AESOScraper()

    def boom(url, delay=1.0):
        raise RuntimeError("network down")

    monkeypatch.setattr(scraper, "fetch_bytes", boom)
    (record,) = scraper.scrape()
    assert record.confidence == "unverified" and "Provenance: seed_fallback" in record.notes
    assert record.components[0].confidence == "unverified"
    assert record.components[0].market_source_url == aeso.REPORT_URL


def test_live_and_seed_share_the_tariff_name_so_the_live_version_supersedes_the_seed(monkeypatch):
    (live,) = _scraper(monkeypatch).scrape()
    (seed,) = AESOScraper()._seed_data()
    assert live.tariff_name == seed.tariff_name
    assert live.effective_date > seed.effective_date


def test_registry_lists_the_official_ets_sources():
    registry = json.loads((Path(__file__).resolve().parents[1] / "data" / "sources" / "registry.json")
                          .read_text(encoding="utf-8"))
    (entry,) = [u for u in registry["utilities"] if u["name"] == "Alberta Electric System Operator"]
    urls = {s["url"] for s in entry["sources"]}
    assert aeso.METADATA_URL in urls and aeso.REPORT_URL in urls
    assert not any("hourly-pool-price-report" in u for u in urls)
