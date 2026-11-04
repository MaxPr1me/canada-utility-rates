"""Edition rollover checks from the January 2027 readiness audit (2026-11-04).

Most scrapers discover their documents and reject an edition whose effective date is later than
the scrape date, so an edition posted before it takes effect fails closed until that day (the
November 1, 2026 OEB RPP prices showed the pattern). These tests pin two calendar rules that the
audit found untested, using saved official sources:

- The OEB Bill Calculator feed (BillData.xml) must carry the current calendar year. On 2026-11-04
  all 141 rows of the live residential and GS<50 feeds said YEAR=2026 (last modified 2026-10-30), so
  unless the OEB relabels the feed before the January 1 Monthly Scrape, that run rejects every
  Ontario residential and GS<50 row: those records are not refreshed and the stored versions stay
  the latest. Accepting the previous year's rows in January would be a methodology change that
  needs an owner decision; this test documents today's fail-closed rule.
- An Enbridge Gas Rate Handbook (one PDF re-issued with each quarterly rate adjustment) is never
  used before its effective and implementation dates: a January 1 handbook posted in December
  makes the whole utility fail closed until January 1, rather than mixing editions.
"""
import json
from datetime import date
from pathlib import Path

from scrapers.utilities.enbridge_gas import EnbridgeGasScraper
from scrapers.utilities.ontario_ldc import parse_bill_data, parse_rpp_page
from scrapers.utils.parsing import DocumentPage

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_ontario_bill_data_rows_must_match_the_calendar_year():
    billdata = _load("oeb_billdata.json")  # saved 2026-10-07; every row says YEAR=2026
    rpp = parse_rpp_page(billdata["rpp_html"], today=date(2026, 10, 7))
    for kind, key in (("residential", "residential_xml"), ("gs", "gs_xml")):
        xml = billdata[key].encode()
        december, _ = parse_bill_data(xml, kind, rpp, date(2026, 12, 31))
        assert december, kind
        january, rejected = parse_bill_data(xml, kind, rpp, date(2027, 1, 1))
        assert january == {}
        assert rejected and all("rate year '2026' is not 2027" in reason for reason in rejected)


def _enbridge_records(today: date) -> list:
    document = _load("enbridge_gas.json")
    pages = [DocumentPage(page["page_number"], page["text"]) for page in document["pages"]]
    return EnbridgeGasScraper().parse_documents(pages, document["cra_text"], today=today,
                                                source_url=document["source_url"])


def test_enbridge_handbook_is_not_used_before_its_effective_date():
    # The saved handbook is "Effective October 1, 2026 Implemented October 1, 2026" (EB-2026-0221).
    assert _enbridge_records(date(2026, 9, 30)) == []
    assert _enbridge_records(date(2026, 10, 1))
