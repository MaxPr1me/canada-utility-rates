"""Alberta Rate of Last Resort (RoLR) next-term rollover checks (added 2026-11-04).

The current RoLR term ends on 2026-12-31. On 2026-11-04 neither the Utilities Consumer Advocate
(UCA) default-rates table nor the three providers published a next term; the UCA's RoLR page says
the Alberta Utilities Commission re-evaluates the rate every two years. These tests pin the
fail-closed behaviour around the switch with the saved UCA page in tests/fixtures/alberta_rolr.json,
mutated the same way as ``test_rolr_uca_next_term_table_selected_by_date`` in
tests/test_live_parsers.py: the exact boundary days of a two-term page, a page that already lists
only the next term (never used before it starts) and two tables that cover the same day.
"""
import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utils import alberta_rolr as rolr

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "alberta_rolr.json"
CURRENT_TERM = "January 1, 2025 – December 31, 2026"
NEXT_TERM = "January 1, 2027 – December 31, 2028"
CURRENT_UNTIL = "will be in place until December 31, 2026"
DERS_ATCO = ("Direct Energy", "ATCO")


def _uca_html() -> str:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["sources"]["uca"]["html"]


def _table_bounds(html: str) -> tuple[int, int]:
    start = html.index("<table")
    return start, html.index("</table>", start) + len("</table>")


def _replace(text: str, old: str, new: str) -> str:
    assert old in text, old
    return text.replace(old, new)


def _next_term_table(html: str, cents: str = "12.50") -> str:
    """The current UCA table relabelled as a hypothetical 2027-2028 term with a new DERS price."""
    start, end = _table_bounds(html)
    table = _replace(html[start:end], CURRENT_TERM, NEXT_TERM)
    table = _replace(table, "Until Dec. 31", "Until Dec. 31 2028 ")
    table = _replace(table, "<p>2026</p>", "")
    return _replace(table, "12.02", cents)


def _cents(value: str):
    return rolr.parse_cents(value, "¢/kWh")


@pytest.mark.parametrize("day, cents", [(date(2026, 12, 31), "12.02"), (date(2027, 1, 1), "12.50")])
def test_two_term_page_switches_exactly_on_january_1(day, cents):
    html = _uca_html()
    _, end = _table_bounds(html)
    two_terms = html[:end] + _next_term_table(html) + html[end:]
    assert rolr.parse_uca_table(two_terms, day).price(*DERS_ATCO) == _cents(cents)


def test_next_term_alone_is_never_used_before_it_starts():
    html = _uca_html()
    start, end = _table_bounds(html)
    only_next = html[:start] + _next_term_table(html) + html[end:]
    # The page text still promises the current term until December 31, 2026, but no table says so.
    with pytest.raises(rolr.RolrError, match="no table term matches"):
        rolr.parse_uca_table(only_next, date(2026, 12, 15))
    # Even with consistent text, a December scrape must not adopt the 2027 price early.
    consistent = _replace(only_next, CURRENT_UNTIL, "will be in place until December 31, 2028")
    with pytest.raises(rolr.RolrError, match="no single UCA RoLR term covers 2026-12-15"):
        rolr.parse_uca_table(consistent, date(2026, 12, 15))
    assert rolr.parse_uca_table(consistent, date(2027, 1, 1)).price(*DERS_ATCO) == _cents("12.50")


def test_two_tables_covering_the_same_day_fail_closed():
    html = _uca_html()
    start, end = _table_bounds(html)
    duplicate = _replace(html[start:end], "12.02", "12.03")
    with pytest.raises(rolr.RolrError, match="no single UCA RoLR term covers 2026-11-04"):
        rolr.parse_uca_table(html[:end] + duplicate + html[end:], date(2026, 11, 4))
