"""City of Grand Forks (BC) parser tests on Schedule G (consolidation through A20) and Bylaw 1958-A19."""

import json
import re
from datetime import date
from pathlib import Path

import pytest
from requests import HTTPError

from scrapers.utilities import grand_forks as gf
from scrapers.utils.parsing import DocumentPage

FIXTURES = Path(__file__).parent / "fixtures"
CONSOLIDATION = json.loads((FIXTURES / "grand_forks_fees_consolidated_a20.json").read_text(encoding="utf-8"))
AMENDMENT = json.loads((FIXTURES / "grand_forks_bylaw_1958_a19.json").read_text(encoding="utf-8"))
LIBRARY = (FIXTURES / "grand_forks_document_library.html").read_text(encoding="utf-8")
TODAY = date(2026, 11, 4)


def _pages(fixture, old: str = "", new: str = "") -> list[DocumentPage]:
    return [DocumentPage(p["page_number"], p["text"].replace(old, new) if old else p["text"])
            for p in fixture["pages"]]


def _parse(consolidation=None, amendment=None, today=TODAY):
    records = gf.parse_schedule(consolidation or _pages(CONSOLIDATION), amendment or _pages(AMENDMENT),
                                CONSOLIDATION["source_url"], AMENDMENT["source_url"], today=today)
    return {r.tariff_code: r for r in records}


def test_schedule_g_classes_dated_by_the_amending_bylaw():
    records = _parse()
    assert list(records) == ["G-1", "G-2", "G-3"]
    assert {r.effective_date for r in records.values()} == {"2026-04-15"}
    assert [(c.charge_value, c.charge_unit) for c in records["G-1"].components] == [
        (24.84, "$/month"), (0.15516, "$/kWh")]
    assert "Bylaw 1958-A19" in records["G-1"].source_page


def test_commercial_block_is_per_two_month_billing_period():
    energy = [c for c in _parse()["G-2"].components if c.component_type == "energy"]
    assert [(c.tier_number, c.tier_threshold, c.tier_unit, c.charge_value) for c in energy] == [
        (1, 200000.0, "kWh", 0.15134), (2, 200000.0, "kWh", 0.11231)]
    assert all("two-month billing period" in c.notes for c in energy)


def test_amendment_with_different_prices_fails_closed():
    amendment = _pages(AMENDMENT, "$0.15516", "$0.15600")
    with pytest.raises(ValueError, match="prices differ"):
        _parse(amendment=amendment)


def test_amendment_not_yet_in_effect_fails_closed():
    with pytest.raises(ValueError, match="takes effect 2026-04-15"):
        _parse(today=date(2026, 4, 14))


def test_missing_effective_date_fails_closed():
    amendment = _pages(AMENDMENT, "The effective date of this amending bylaw shall be", "This bylaw applies from")
    with pytest.raises(ValueError, match="effective date not found"):
        _parse(amendment=amendment)


def test_media_search_picks_the_newest_matching_document():
    payload = json.dumps([
        {"date": "2026-01-22T10:00:00", "source_url": "https://www.grandforks.ca/wp-content/uploads/Bylaw1958Fees-Charges-Bylaw-CONSOLIDATED-through-A18-2026.pdf"},
        {"date": "2026-06-16T10:00:00", "source_url": CONSOLIDATION["source_url"]},
        {"date": "2026-06-01T10:00:00", "source_url": "https://www.grandforks.ca/wp-content/uploads/By1958-A20-Fees-and-Charges-Amendment-Development-Fees.pdf"},
    ])
    assert gf.newest_media_url(payload, gf._CONSOLIDATION) == CONSOLIDATION["source_url"]
    amendments = json.dumps([{"date": "2026-04-21T10:00:00", "source_url": AMENDMENT["source_url"]}])
    assert gf.newest_media_url(amendments, gf.amendment_pattern("1958-A19")) == AMENDMENT["source_url"]
    assert gf.newest_media_url(amendments, gf.amendment_pattern("1958-A20")) is None


def test_no_records_without_the_amending_bylaw(monkeypatch):
    scraper = gf.GrandForksScraper()
    monkeypatch.setattr(gf, "LAST_KNOWN_AMENDMENT_URLS", {})
    monkeypatch.setattr(scraper, "fetch_page", lambda *_a, **_k: "")
    monkeypatch.setattr(scraper, "_media", lambda query, pattern: CONSOLIDATION["source_url"]
                        if pattern is gf._CONSOLIDATION else None)
    monkeypatch.setattr(gf, "extract_pdf_pages", lambda *_a, **_k: _pages(CONSOLIDATION))
    monkeypatch.setattr(scraper, "fetch_bytes", lambda *_a, **_k: b"%PDF")
    assert scraper.scrape() == []
    assert re.search(r"1958-A19", gf.schedule_g(_pages(CONSOLIDATION))[1])


def test_document_library_selects_the_latest_consolidation_and_matching_amendment():
    older = LIBRARY.replace("through-A20.pdf", "through-A18.pdf").replace("June 16, 2026", "January 22, 2026")
    assert gf.newest_document_url(older + LIBRARY, gf._CONSOLIDATION) == CONSOLIDATION["source_url"]
    assert gf.newest_document_url(LIBRARY, gf.amendment_pattern("1958-A19")) == AMENDMENT["source_url"]
    assert gf.newest_document_url(LIBRARY, gf.amendment_pattern("1958-A21")) is None
    with pytest.raises(ValueError, match="publication date"):
        gf.newest_document_url(LIBRARY.replace('<small style="opacity:.65">June 16, 2026 </small>', ""),
                               gf._CONSOLIDATION)


@pytest.mark.parametrize("library_available", [True, False])
def test_discovery_uses_the_library_with_media_search_as_fallback(monkeypatch, library_available):
    scraper = gf.GrandForksScraper()
    documents = {CONSOLIDATION["source_url"]: CONSOLIDATION, AMENDMENT["source_url"]: AMENDMENT}

    def fetch_page(url):
        if "/document-library/" in url:
            if library_available:
                return LIBRARY
            raise HTTPError("document library unavailable")
        if library_available:
            raise HTTPError("403 Forbidden: media search unavailable")
        fixture = CONSOLIDATION if "search=CONSOLIDATED" in url else AMENDMENT
        return json.dumps([{"date": "2026-11-04T00:00:00", "source_url": fixture["source_url"]}])

    monkeypatch.setattr(scraper, "fetch_page", fetch_page)
    monkeypatch.setattr(scraper, "fetch_bytes", lambda url: url.encode("utf-8"))
    monkeypatch.setattr(gf, "extract_pdf_pages", lambda content, **_k: _pages(documents[content.decode("utf-8")]))
    records = scraper.scrape()
    assert [r.tariff_code for r in records] == ["G-1", "G-2", "G-3"]
    assert {r.effective_date for r in records} == {"2026-04-15"}
    assert all("Provenance: live_parsed" in r.notes for r in records)


def test_blocked_discovery_reads_the_last_known_documents_and_says_so(monkeypatch):
    """Cloudflare 403s GitHub's runners for the library and media API but not wp-content/uploads."""
    scraper = gf.GrandForksScraper()
    documents = {gf.LAST_KNOWN_CONSOLIDATION_URL: CONSOLIDATION, gf.LAST_KNOWN_AMENDMENT_URLS["1958-A19"]: AMENDMENT}
    fetched = []

    def blocked(url):
        raise HTTPError(f"403 Client Error: Forbidden for url: {url}")

    def fetch_bytes(url):
        fetched.append(url)
        return url.encode("utf-8")

    monkeypatch.setattr(scraper, "fetch_page", blocked)
    monkeypatch.setattr(scraper, "fetch_bytes", fetch_bytes)
    monkeypatch.setattr(gf, "extract_pdf_pages", lambda content, **_k: _pages(documents[content.decode("utf-8")]))
    records = scraper.scrape()
    assert fetched == list(documents)
    assert gf.amendment_pattern("1958-A19").search(gf.LAST_KNOWN_AMENDMENT_URLS["1958-A19"])
    assert [r.tariff_code for r in records] == ["G-1", "G-2", "G-3"]
    for record in records:
        assert "Provenance: live_parsed" in record.notes
        assert "last known one was read (it may not be current)" in record.notes
        assert "found amending Bylaw 1958-A19, so its last known copy was read" in record.notes
