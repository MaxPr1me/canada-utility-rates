"""Offline tests for the joint YECL/YEC rate-book discovery from ATCO Electric Yukon's rates-page model JSON."""
import json
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from scrapers.utilities import yukon_energy
from scrapers.utilities.yukon_electrical import YukonElectricalScraper
from scrapers.utilities.yukon_energy import (
    JOINT_RATES_MODEL_URL, JOINT_RATES_PAGE_URL, JOINT_SCHEDULE_URL, RATE_SCHEDULES_URL, YukonEnergyScraper,
    joint_schedule_editions,
)
from scrapers.utils.parsing import DocumentPage

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ASSETS = "https://www.atcoelectricyukon.com/content/dam/aey-website/en-ca/assets/services-rates/"
BOOK = [DocumentPage(1, "YECL/YEC Joint Rate Schedules Approved in Board Order 2011-06")]
JS_SHELL = "<html><body><noscript>You need to enable JavaScript to run this app.</noscript></body></html>"


def _fixture() -> dict:
    return json.loads((FIXTURES / "yukon_rate_book_model.json").read_text(encoding="utf-8"))


def _book(edition: str) -> str:
    return f"{ASSETS}yecl-yec-rate-schedules-{edition}.pdf"


def _model(*hrefs: str) -> dict:
    rows = "".join(f'<tr><td><a href="{href}" target="_blank">YECL/YEC Rate Schedules</a></td></tr>' for href in hrefs)
    return {":items": {"root": {":items": {"richtext": {"text": f"<table><tbody>{rows}</tbody></table>"}}}}}


def _joint(served, model, page_html=JS_SHELL, now="2026-10-30T12:00:00+00:00"):
    """Run _joint_schedule() offline; `model` is a dict, raw text or an exception raised by the fetch."""
    scraper = YukonEnergyScraper()
    pages_fetched, bytes_fetched = [], []

    def fetch_page(url, *args, **kwargs):
        pages_fetched.append(url)
        if url == JOINT_RATES_MODEL_URL:
            if isinstance(model, Exception):
                raise model
            return model if isinstance(model, str) else json.dumps(model)
        if url == JOINT_RATES_PAGE_URL:
            return page_html
        raise OSError(f"unexpected fetch {url}")

    def fetch_bytes(url, *args, **kwargs):
        bytes_fetched.append(url)
        if url not in served:
            raise OSError(f"404 Not Found: {url}")
        return url.encode("utf-8")

    with patch.object(scraper, "fetch_page", side_effect=fetch_page),\
            patch.object(scraper, "fetch_bytes", side_effect=fetch_bytes),\
            patch.object(scraper, "now_iso", return_value=now),\
            patch.object(yukon_energy, "extract_pdf_pages", side_effect=lambda data: served[data.decode("utf-8")]):
        return scraper._joint_schedule(), pages_fetched, bytes_fetched


def test_fixture_is_trimmed_official_model_excerpt():
    document = _fixture()
    assert document["source_url"] == JOINT_RATES_MODEL_URL and document["landing_url"] == JOINT_RATES_PAGE_URL
    assert document["retrieved_on"] == "2026-10-30"
    table = document["model_excerpt"][":items"]["root"][":items"]["responsivegrid"][":items"]["section_tab_copy_cop"]
    assert table[":items"]["richtext_copy_414764424"]["text"].count(".pdf") == 5
    # The October 2026 link on the live page is the last known link kept in the scraper.
    assert joint_schedule_editions(document["model_excerpt"]) == {JOINT_SCHEDULE_URL: "2026-10"}


def test_editions_accept_relative_absolute_and_plain_path_strings():
    relative = "/content/dam/aey-website/en-ca/assets/services-rates/yecl-yec-rate-schedules-09-2026.pdf"
    model = _model(relative, _book("09-2026"), _book("10-2026"))
    model["fileReference"] = "/content/dam/aey-website/en-ca/assets/services-rates/YECL-YEC-Rate-Schedules-08-2026.pdf"
    assert joint_schedule_editions(model) == {
        _book("09-2026"): "2026-09", _book("10-2026"): "2026-10",
        ASSETS + "YECL-YEC-Rate-Schedules-08-2026.pdf": "2026-08"}


def test_link_found_in_model_json(caplog):
    caplog.set_level(logging.INFO, logger="scraper.yukon_energy")
    (url, pages), pages_fetched, bytes_fetched = _joint({JOINT_SCHEDULE_URL: BOOK}, _fixture()["model_excerpt"])
    assert (url, pages) == (JOINT_SCHEDULE_URL, BOOK)
    assert pages_fetched == [JOINT_RATES_MODEL_URL] and bytes_fetched == [JOINT_SCHEDULE_URL]
    assert f"Joint YECL/YEC rate schedules (rates page model): {JOINT_SCHEDULE_URL}" in caplog.text


@pytest.mark.parametrize(("now", "editions", "expected"), [
    ("2026-10-30T12:00:00+00:00", ("08-2026", "10-2026", "09-2026"), "10-2026"),
    ("2026-11-01T00:00:00+00:00", ("10-2026", "11-2026"), "11-2026"),
    ("2027-01-05T00:00:00+00:00", ("12-2026", "01-2027", "11-2026"), "01-2027"),
])
def test_newest_edition_not_later_than_current_month_wins(now, editions, expected):
    served = {_book(edition): BOOK for edition in editions}
    (url, _), pages_fetched, bytes_fetched = _joint(served, _model(*map(_book, editions)), now=now)
    assert url == _book(expected) and bytes_fetched == [_book(expected)]
    assert JOINT_RATES_PAGE_URL not in pages_fetched


def test_foreign_host_wrong_path_and_future_editions_ignored(caplog):
    caplog.set_level(logging.INFO, logger="scraper.yukon_energy")
    name = "yecl-yec-rate-schedules-10-2026.pdf"
    model = _model(
        "https://example.com/content/dam/aey-website/en-ca/assets/services-rates/" + name,
        "https://atcoelectricyukon.com/content/dam/aey-website/en-ca/assets/services-rates/" + name,
        "//example.com/content/dam/aey-website/en-ca/assets/services-rates/" + name,
        "http://www.atcoelectricyukon.com/content/dam/aey-website/en-ca/assets/services-rates/" + name,
        "/content/dam/other-website/en-ca/assets/services-rates/" + name,
        "/en-ca/services-rates/" + name,
        "/content/dam/aey-website/en-ca/assets/services-rates/aey-yec-rider-s-rate-schedule.pdf",
        "/content/dam/aey-website/en-ca/assets/services-rates/yecl-yec-rate-schedules-13-2026.pdf",
        "/content/dam/aey-website/en-ca/assets/services-rates/yecl-yec-rate-schedules-11-2026.pdf",
        "/content/dam/aey-website/en-ca/assets/services-rates/yecl-yec-rate-schedules-09-2026.pdf",
    )
    assert joint_schedule_editions(model) == {_book("11-2026"): "2026-11", _book("09-2026"): "2026-09"}
    (url, _), _, bytes_fetched = _joint({_book("09-2026"): BOOK, _book("11-2026"): BOOK}, model)
    assert url == _book("09-2026") and bytes_fetched == [_book("09-2026")]
    assert f"Joint YECL/YEC rate schedules {_book('11-2026')} are a future edition; ignored" in caplog.text


def test_two_links_for_the_newest_edition_are_not_guessed(caplog):
    archive = "/content/dam/aey-website/en-ca/assets/archive/yecl-yec-rate-schedules-11-2026.pdf"
    served = {JOINT_SCHEDULE_URL: BOOK, _book("11-2026"): BOOK}
    (url, _), pages_fetched, _ = _joint(served, _model(_book("11-2026"), archive), now="2026-11-02T00:00:00+00:00")
    assert url == JOINT_SCHEDULE_URL and pages_fetched == [JOINT_RATES_MODEL_URL, JOINT_RATES_PAGE_URL]
    assert "No single current joint YECL/YEC rate schedules link in the rates page model (2 found)" in caplog.text


MODEL_FAILURES = [
    pytest.param(OSError("503 Server Error"), id="fetch-error"),
    pytest.param("<html><body>Not JSON</body></html>", id="not-json"),
    pytest.param({":items": {}}, id="no-links"),
    pytest.param(_model(_book("11-2026")), id="future-only"),
]


@pytest.mark.parametrize("model", MODEL_FAILURES)
def test_model_failure_falls_back_to_page_link(model):
    page = f'<body><a href="{_book("09-2026")}">YECL/YEC Rate Schedules</a></body>'
    (url, _), pages_fetched, _ = _joint({_book("09-2026"): BOOK}, model, page_html=page)
    assert url == _book("09-2026") and pages_fetched == [JOINT_RATES_MODEL_URL, JOINT_RATES_PAGE_URL]


@pytest.mark.parametrize("model", MODEL_FAILURES)
def test_model_and_page_failure_fall_back_to_last_known_link(model, caplog):
    caplog.set_level(logging.INFO, logger="scraper.yukon_energy")
    (url, _), _, bytes_fetched = _joint({JOINT_SCHEDULE_URL: BOOK}, model)
    assert url == JOINT_SCHEDULE_URL and bytes_fetched == [JOINT_SCHEDULE_URL]
    assert f"Joint YECL/YEC rate schedules (last known link): {JOINT_SCHEDULE_URL}" in caplog.text


@pytest.mark.parametrize("served", [
    pytest.param({JOINT_SCHEDULE_URL: [DocumentPage(1, "Draft rate schedules")]}, id="unrecognised"),
    pytest.param({}, id="download-fails"),
])
def test_discovered_book_that_fails_returns_none(served):
    result, _, bytes_fetched = _joint(served, _fixture()["model_excerpt"])
    assert result is None and bytes_fetched == [JOINT_SCHEDULE_URL]


def _live_documents(book_url: str) -> dict[str, list[DocumentPage]]:
    """Batch 10 Yukon fixtures, with the joint book served at `book_url`."""
    documents = json.loads((FIXTURES / "yukon_energy_building_rates.json").read_text(encoding="utf-8"))["documents"]
    b10 = json.loads((FIXTURES / "yukon_b10.json").read_text(encoding="utf-8"))
    documents["cross_reference"]["pages"] += b10["cross_reference_other_pages"]["pages"]
    served = {document["source_url"]: [DocumentPage(**page) for page in document["pages"]] for document in documents.values()}
    served[book_url] = [DocumentPage(**page) for page in b10["joint_schedule"]["pages"]]
    return served


@pytest.mark.parametrize("scraper_class", [YukonEnergyScraper, YukonElectricalScraper])
def test_new_monthly_edition_keeps_all_records_live_with_unchanged_dates(scraper_class):
    book_url = _book("11-2026")
    served = _live_documents(book_url)
    rates_html = "<body>" + "".join(f'<a href="{url}">Rate schedule</a>' for url in served if url != book_url) + "</body>"
    pages = {RATE_SCHEDULES_URL: rates_html, JOINT_RATES_MODEL_URL: json.dumps(_model(_book("10-2026"), book_url))}
    scraper = scraper_class()
    with patch.object(scraper, "fetch_page", side_effect=lambda url, *a, **k: pages[url]),\
            patch.object(scraper, "fetch_rendered_page", return_value=None),\
            patch.object(scraper, "fetch_bytes", side_effect=lambda url, *a, **k: url.encode("utf-8")),\
            patch.object(scraper, "now_iso", return_value="2026-11-02T00:00:00+00:00"),\
            patch.object(yukon_energy, "extract_pdf_pages", side_effect=lambda data: served[data.decode("utf-8")]):
        records = scraper.scrape()
    assert len(records) == 20 and all("live_parsed" in record.notes for record in records)
    general = [record for record in records if record.customer_class == "commercial"]
    assert len(general) == 12 and {record.source_url for record in general} == {book_url}
    assert all(book_url in record.source_page for record in records if record.customer_class == "residential")
    # The edition month is only in the link; printed schedule and rider dates still set the effective dates.
    assert {record.effective_date for record in records} == {"2026-10-01"}
