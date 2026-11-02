"""Centra quarterly PDF authority, signed transport and fail-closed source evidence."""
import json
import logging
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities import centra_gas
from scrapers.utilities.centra_gas import MLI_CODE, MLI_ROW, PAGE_URLS, CentraGasScraper

FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures" / "centra_gas.json").read_text(encoding="utf-8"))
V1126 = FIXTURE["appendix_a_v1126"]
AUGUST_TODAY = date(2026, 10, 30)
NOVEMBER_TODAY = date(2026, 11, 2)
TEXT_CLASSES = {"SGS", "SGS-MKT", "COM-SGS", "COM-SGS-MKT", "COM-LGS", "COM-LGS-MKT",
                "COM-HVF-S", "COM-HVF-T", "COM-MFS-S", "COM-MFS-T", "COM-IS-S", "COM-IS-T"}
FIRM_CLASSES = TEXT_CLASSES - {"COM-IS-S", "COM-IS-T"}

# Synthetic: Centra's November 1, 2026 rate pages are not published yet (checked 2026-10-30). The three tables the
# Mainline Interruptible record is cross-checked against are restated with v1126 page 4 of 4 values in cents.
NOVEMBER_TABLES = (
    ("Basic monthly charge $1,306.98 Delivery 0.21¢/m 3 Demand 22.71¢/m 3 /month Delivery only",
     "Basic monthly charge $1,374.87 Delivery 0.29¢/m 3 Demand 23.83¢/m 3 /month Delivery only"),
    ("Basic monthly charge $1,409.45 Gas Commodity 6.60¢/m 3 Delivery 3.13¢/m 3 Demand 36.97¢/m 3 /month "
     "Alternate supply service 1.29¢/m 3 Delivery is the total of: Transportation to Centra charges at 0.31¢/m 3 plus "
     "Distribution to customer charges at 2.82¢/m 3 . Demand is the total of: Demand transportation charges at "
     "13.98¢/m 3 /month plus Demand distribution charges at 22.99¢/m 3 /month.",
     "Basic monthly charge $1,490.40 Gas Commodity 5.88¢/m 3 Delivery 2.34¢/m 3 Demand 32.34¢/m 3 /month "
     "Alternate supply service 1.41¢/m 3 Delivery is the total of: Transportation to Centra charges at 0.14¢/m 3 plus "
     "Distribution to customer charges at 2.20¢/m 3 . Demand is the total of: Demand transportation charges at "
     "6.94¢/m 3 /month plus Demand distribution charges at 25.39¢/m 3 /month."),
    ("Basic monthly charge $1,409.45 Delivery 0.86¢/m 3 Demand 22.99¢/m 3 /month Alternate supply service 1.29¢/m 3",
     "Basic monthly charge $1,490.40 Delivery 1.09¢/m 3 Demand 25.39¢/m 3 /month Alternate supply service 1.41¢/m 3"),
)


def evidence_parts():
    evidence = FIXTURE["appendix_a_transcription"]["evidence"]
    return ["PDF page 19 " + evidence["19"], "PDF page 50 " + evidence["50"]]


def text_appendix():
    return " ".join(evidence_parts() + ["PDF page " + number + " " + page["text"]
                                        for number, page in V1126["pages"].items()])


def transcription_appendix():
    pages = FIXTURE["appendix_a_transcription"]["pages"]
    return " ".join(evidence_parts() + ["PDF page " + number + " image-sha256 " + page["image_sha256"] + " " +
                                        page["header_text"] for number, page in pages.items()])


def august_pages(appendix):
    pages = {key: page["text"] for key, page in FIXTURE["pages"].items()}
    pages["appendix_a"] = appendix
    return pages


def november_pages(appendix=None):
    pages = august_pages(text_appendix() if appendix is None else appendix)
    for old, new in NOVEMBER_TABLES:
        assert pages["commercial"].count(old) == 1
        pages["commercial"] = pages["commercial"].replace(old, new)
    for key in ("residential", "commercial"):
        assert "Rates effective August 1, 2026 Effective August 1, 2026" in pages[key]
        pages[key] = pages[key].replace("August 1, 2026", "November 1, 2026").replace("6.60¢", "5.88¢")
    pages["supply"] = pages["supply"].replace("$0.0660 (Aug. 1, 2026)", "$0.0588 (Nov. 1, 2026) $0.0660 (Aug. 1, 2026)")
    return pages


def parse(pages, today=NOVEMBER_TODAY):
    scraper = CentraGasScraper()
    records = scraper.parse_pages(pages, today)
    return scraper, {record.tariff_code: record for record in records}


def components(record):
    return {component.component_name: component for component in record.components}


def test_fixture_excerpt_matches_the_edition_table():
    edition = centra_gas.SCHEDULE_EDITIONS[date(2026, 11, 1)]
    assert edition["appendix"] == "text"
    assert (V1126["source_url"], V1126["board_order"]) == (edition["url"], edition["board_order"])
    assert {int(number) for number in V1126["pages"]} == set(edition["pages"])
    for number, page in V1126["pages"].items():
        label, title = edition["pages"][int(number)]
        assert page["label"] == label and label in page["text"] and title in page["text"]
        assert "Approved by Board Order: 150/26" in page["text"] and "Effective from: November 1, 2026" in page["text"]
    assert centra_gas.SCHEDULE_EDITIONS[date(2026, 8, 1)] == {"url": PAGE_URLS["schedule"], "appendix": "transcription"}


def test_edition_follows_the_current_supported_quarter_not_stale_html():
    scraper = CentraGasScraper()
    assert scraper._edition(AUGUST_TODAY)["url"] == PAGE_URLS["schedule"]
    assert scraper._edition(NOVEMBER_TODAY)["url"] == V1126["source_url"]
    assert scraper._edition(date(2027, 1, 31))["url"] == V1126["source_url"]
    assert scraper._edition(date(2027, 2, 1)) is None


def test_november_pages_read_the_v1126_text_at_high_confidence():
    scraper, records = parse(november_pages())
    assert set(records) == TEXT_CLASSES | {MLI_CODE}
    assert scraper.unmodelled_classes == []
    record = records[MLI_CODE]
    assert record.effective_date == "2026-11-01" and record.confidence == "high"
    assert record.source_url == V1126["source_url"]
    assert record.source_page == ("Appendix A page 4 of 4 (PDF page 82), base rates plus riders, Board Order 150/26, "
                                  "effective November 1, 2026")
    parts = components(record)
    assert {name: (part.charge_value, part.charge_unit) for name, part in parts.items()} == {
        "Basic Monthly Charge": (1374.87, "$/month"),
        "Gas Commodity": (0.0588, "$/m³"),
        "Transportation to Centra": (-0.0017, "$/m³"),
        "Distribution Charge": (0.014, "$/m³"),
        "Demand Transportation Charge": (0.1117, "$/m³/month"),
        "Demand Distribution Charge": (0.2383, "$/m³/month"),
        "Alternate Supply Service": (0.0036, "$/m³"),
        "Federal Carbon Charge": (0.0, "$/m³"),
    }
    assert all(part.confidence == "high" for part in record.components)
    for name, part in parts.items():
        if name == "Federal Carbon Charge":
            assert part.effective_date == "2025-04-01" and "revenue-agency" in part.source_url
            continue
        assert part.effective_date == "2026-11-01" and part.source_url == V1126["source_url"]
        assert part.source_detail.startswith("Appendix A page 4 of 4 (PDF page 82)")
        assert part.notes.startswith("Read from the text layer of official Appendix A page 4 of 4")
    assert "Transcribed" not in record.notes and "Cross-checked against the text-published" in record.notes
    assert V1126["source_url"] in records["COM-HVF-T"].notes


def test_text_record_keeps_the_transcription_structure():
    _, november = parse(november_pages())
    _, august = parse(august_pages(transcription_appendix()), AUGUST_TODAY)
    new, old = november[MLI_CODE], august[MLI_CODE]
    assert (old.confidence, old.source_url, old.effective_date) == ("medium", PAGE_URLS["schedule"], "2026-08-01")
    assert old.notes.startswith("Transcribed from scanned official Appendix A")
    shape = [(part.component_type, part.component_name, part.charge_unit, part.sub_component) for part in new.components]
    assert shape == [(part.component_type, part.component_name, part.charge_unit, part.sub_component)
                     for part in old.components]
    for field in ("tariff_name", "customer_class", "sub_class", "rate_structure", "usage_min", "usage_unit", "eligibility"):
        assert getattr(new, field) == getattr(old, field)


def test_august_pages_never_read_the_text_appendix():
    scraper, records = parse(august_pages(text_appendix()), AUGUST_TODAY)
    assert set(records) == TEXT_CLASSES and scraper.unmodelled_classes == [MLI_ROW]


def test_november_pages_never_use_the_transcription():
    scraper, records = parse(november_pages(transcription_appendix()))
    assert not records and scraper.unmodelled_classes == [MLI_ROW]


@pytest.mark.parametrize(("old", "new", "expected"), [
    ("Approved by Board Order: 150/26", "Approved by Board Order: 151/26", set()),
    ("Approved by Board Order: 150/26", "Approved by Board Order: 150/260", set()),
    ("Effective from: November 1, 2026", "Effective from: February 1, 2027", set()),
    ("Page 4 of 4", "Page 4 of 5", FIRM_CLASSES),
    ("(BASE RATES ONLY - NO RIDERS)", "(BASE RATES)", FIRM_CLASSES),
])
def test_header_mismatch_rejects_the_affected_pdf_tables(old, new, expected, caplog):
    appendix = text_appendix()
    assert old in appendix
    with caplog.at_level(logging.WARNING):
        scraper, records = parse(november_pages(appendix.replace(old, new)))
    assert set(records) == expected and scraper.unmodelled_classes == [MLI_ROW]
    assert "header lacks" in caplog.text


def test_unknown_quarter_never_reuses_old_prices_or_html(monkeypatch, caplog):
    monkeypatch.setattr(centra_gas, "SCHEDULE_EDITIONS", {
        date(2026, 8, 1): centra_gas.SCHEDULE_EDITIONS[date(2026, 8, 1)]})
    with caplog.at_level(logging.WARNING):
        scraper, records = parse(november_pages())
    assert not records
    assert "no supported approved schedule for the current quarterly period" in caplog.text


@pytest.mark.parametrize(("old", "new"), [
    ("Mainline Interruptible (with firm delivery) $0.0588 -$0.0017 $0.0140 $0.0123 $0.0029 ", ""),
    ("Delivery - Mainline Interruptible Class $0.0036 ¹", "¹"),
    ("$0.0588 -$0.0017", "$0.0588 –$0.0017"),
])
def test_missing_or_unreadable_row_fails_closed(old, new):
    appendix = text_appendix()
    assert old in appendix
    scraper, records = parse(november_pages(appendix.replace(old, new)))
    assert set(records) == FIRM_CLASSES and scraper.unmodelled_classes == [MLI_ROW]


def test_repeated_table_fails_closed():
    page = V1126["pages"]["82"]["text"]
    start = page.index("Basic Monthly Charge: ($/month)")
    end = page.index("Delivery - Mainline Interruptible Class $0.0036") + len("Delivery - Mainline Interruptible Class $0.0036")
    table = page[start:end]
    _, records = parse(november_pages(text_appendix().replace(table, table + " " + table)))
    assert set(records) == FIRM_CLASSES


@pytest.mark.parametrize(("old", "new"), [
    ("$0.0140 $0.0123 $0.0029", "$0.0140 $0.0125 $0.0029"),
    ("$0.1117 $0.2383 $0.3500", "$0.1117 $0.2383 $0.3502"),
    ("$0.0785 $0.2536 $0.3321", "$0.0785 $0.2536 $0.3323"),
    ("N/A N/A $1,374.87 N/A $1,374.87", "N/A N/A $1,374.87 N/A $1,375.87"),
])
def test_inconsistent_appendix_arithmetic_fails_closed(old, new):
    appendix = text_appendix()
    assert old in appendix
    scraper, records = parse(november_pages(appendix.replace(old, new, 1)))
    assert set(records) == FIRM_CLASSES and scraper.unmodelled_classes == [MLI_ROW]


@pytest.mark.parametrize(("old", "new", "code"), [
    ("Basic monthly charge $1,374.87 Delivery 0.29", "Basic monthly charge $1,375.87 Delivery 0.29", "COM-MFS-T"),
    ("Delivery 1.09¢/m 3", "Delivery 1.19¢/m 3", "COM-IS-T"),
    ("Alternate supply service 1.41¢/m 3 Delivery is", "Alternate supply service 1.43¢/m 3 Delivery is", "COM-IS-S"),
])
def test_commercial_counterpart_mismatch_is_reported_without_overriding_pdf(old, new, code, caplog):
    pages = november_pages()
    assert pages["commercial"].count(old) == 1
    pages["commercial"] = pages["commercial"].replace(old, new)
    _, records = parse(pages)
    assert set(records) == TEXT_CLASSES | {MLI_CODE}
    assert code + " HTML prices differ" in caplog.text
    assert "Source discrepancies:" in records[code].notes


def test_pdf_totals_allow_one_rounding_unit_only():
    _, records = parse(november_pages())
    parts = components(records["COM-IS-S"])
    assert (parts["Demand Transportation Charge"].charge_value, parts["Demand Distribution Charge"].charge_value) == (
        0.0694, 0.2539)
    pages = november_pages()
    pages["appendix_a"] = pages["appendix_a"].replace("$0.0694 $0.2539 $0.3234", "$0.0694 $0.2539 $0.3235")
    _, records = parse(pages)
    assert "COM-IS-S" not in records and MLI_CODE not in records


class _Page:
    def __init__(self, text):
        self.text, self.images = text, []

    def extract_text(self):
        return self.text


def test_appendix_text_reads_text_pages_without_line_numbers():
    texts = {19: "1 Mainline election", 50: "2 VI. Terms", 80: "11 Basic Monthly Charge: ($/month)\n14\n15 Monthly", 82: "x"}
    document = type("Document", (), {"pages": [_Page(texts.get(number, "")) for number in range(1, 85)]})()
    text = CentraGasScraper._appendix_text(document, centra_gas.SCHEDULE_EDITIONS[date(2026, 11, 1)])
    assert CentraGasScraper._norm(text) == (
        "PDF page 19 Mainline election PDF page 50 VI. Terms PDF page 80 Basic Monthly Charge: ($/month) Monthly "
        "PDF page 81 PDF page 82 x")


def test_stale_august_html_cannot_date_november_prices_august(caplog):
    _, records = parse(august_pages(text_appendix()))
    assert set(records) == TEXT_CLASSES | {MLI_CODE}
    assert {record.effective_date for record in records.values()} == {"2026-11-01"}
    for record in records.values():
        assert record.source_url == V1126["source_url"]
        assert record.confidence == "high"
        for component in record.components:
            if component.component_type != "carbon":
                assert component.source_url == V1126["source_url"]
                assert component.effective_date == "2026-11-01"
                assert "quarterly rate table" not in component.source_detail
    assert "commercial HTML headline missing or differs" in caplog.text
    assert "gas supply HTML quarterly table missing or differs" in caplog.text
    parts = components(records["COM-HVF-S"])
    assert parts["Transportation to Centra"].charge_value == -0.0018
    assert parts["Gas Commodity"].charge_value == 0.0588
    assert parts["Distribution Charge"].charge_value == 0.023
    assert parts["Demand Transportation Charge"].charge_value == 0.2916
    assert parts["Demand Distribution Charge"].charge_value == 0.2985
    assert components(records["COM-HVF-T"])["Distribution Charge"].charge_value == 0.0119
    assert components(records["SGS"])["Distribution Charge"].charge_value == 0.1249
    assert components(records["COM-LGS"])["Distribution Charge"].charge_value == 0.0759
    assert not any("-MKT" in record.tariff_code and any(c.component_type == "commodity" for c in record.components)
                   for record in records.values())


@pytest.mark.parametrize(("old", "new", "missing"), [
    ("High Volume Firm (HVF) $0.0588 -$0.0018 $0.0230 $0.0212 $0.0119", "", {"COM-HVF-S", "COM-HVF-T"}),
    ("$0.0588 -$0.0018 $0.0230 $0.0212", "$0.0588 -$0.0018 $0.0230 $0.0214", {"COM-HVF-S", "COM-HVF-T"}),
    ("$0.2916 $0.2985 $0.5901", "$0.2916 $0.2985 $0.5903", {"COM-HVF-S", "COM-HVF-T"}),
    ("$0.0588 $0.0322 $0.1249", "$0.0588 $0.0322 -$0.1249", {"SGS", "SGS-MKT", "COM-SGS", "COM-SGS-MKT"}),
    ("N/A N/A $85.00 N/A N/A", "N/A N/A $85.00 N/A $85.00", {"COM-LGS", "COM-LGS-MKT"}),
])
def test_firm_row_errors_reject_only_affected_classes(old, new, missing):
    pages = november_pages()
    assert old in pages["appendix_a"]
    pages["appendix_a"] = pages["appendix_a"].replace(old, new)
    _, records = parse(pages)
    assert set(records) == (TEXT_CLASSES | {MLI_CODE}) - missing


def test_missing_carbon_still_rejects_all_current_pdf_prices():
    pages = november_pages()
    pages["carbon"] = ""
    assert parse(pages)[1] == {}


def test_missing_marketer_evidence_omits_only_marketer_variants():
    pages = november_pages()
    pages["supply"] = ""
    _, records = parse(pages)
    assert set(records) == (TEXT_CLASSES | {MLI_CODE}) - {"SGS-MKT", "COM-SGS-MKT", "COM-LGS-MKT"}


def test_missing_eligibility_rejects_hvf_but_keeps_other_classes():
    pages = november_pages()
    pages["schedule"] = pages["schedule"].replace("binding agreement", "agreement")
    _, records = parse(pages)
    assert set(records) == (TEXT_CLASSES | {MLI_CODE}) - {"COM-HVF-S", "COM-HVF-T"}


def test_missing_or_duplicate_firm_page_never_uses_html_prices():
    pages = november_pages()
    page = "PDF page 81 " + V1126["pages"]["81"]["text"]
    for appendix in (pages["appendix_a"].replace(page, ""), pages["appendix_a"] + " " + page):
        _, records = parse(november_pages(appendix))
        assert set(records) == {"COM-IS-S", "COM-IS-T"}


def test_future_text_prices_are_never_used_early():
    _, records = parse(november_pages(), AUGUST_TODAY)
    assert records == {}


@pytest.mark.parametrize(("old", "new"), [
    ("Commodity Volumetric Charge: ($/m3)", "Commodity Volumetric Charge: (cents/m3)"),
    ("Gas Commodity Centra to Customer Delivery", "Gas Commodity Customer to Centra Delivery"),
])
def test_firm_units_and_column_identity_are_required(old, new):
    pages = november_pages()
    page = V1126["pages"]["81"]["text"]
    assert old in page
    pages["appendix_a"] = pages["appendix_a"].replace(page, page.replace(old, new))
    _, records = parse(pages)
    assert set(records) == {"COM-IS-S", "COM-IS-T"}
