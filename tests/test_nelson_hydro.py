"""Nelson Hydro (BC) parser tests on the Hydro Services Bylaw 2026/2027 schedules and the rates page
(year selection and December 31 end dates: owner decisions 2026-11-23)."""

import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities import nelson_hydro as nh
from scrapers.utils.parsing import DocumentPage

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "nelson_hydro_bylaw_3608_2026.json").read_text(encoding="utf-8"))
URL = FIXTURE["source_url"]
HTML = FIXTURE["rates_page_html"]
TODAY = date(2026, 11, 4)


def _pages(drop: tuple[int, ...] = ()) -> list[DocumentPage]:
    return [DocumentPage(p["page_number"], p["text"]) for p in FIXTURE["pages"] if p["page_number"] not in drop]


def _parse(html=HTML, pages=None, today=TODAY):
    return {r.tariff_code: r for r in nh.parse_rates(html, pages or _pages(), URL, today=today)}


def test_page_values_select_and_match_the_2026_bylaw_schedules():
    records = _parse()
    assert list(records) == ["A1", "A3", "B1", "B4"]
    assert {(r.effective_date, r.end_date, r.confidence) for r in records.values()} == {
        ("2026-01-01", "2026-12-31", "medium")}
    assert {c.end_date for r in records.values() for c in r.components} == {"2026-12-31"}
    assert [(c.charge_value, c.charge_unit) for c in records["B4"].components] == [
        (59.06, "$/two months"), (0.1902, "$/kWh")]
    assert "Schedule C B4 (2026), PDF page 61" in records["B4"].source_page
    assert "for 2026, 2027" in records["B4"].notes


def test_residential_demand_above_20_kw_is_conditional():
    demand = [c for c in _parse()["A3"].components if c.component_type == "demand"]
    assert [(c.charge_value, c.sub_component) for c in demand] == [(11.35, "conditional")]
    assert demand[0].notes.startswith("Conditional:")


def test_page_and_bylaw_disagreement_fails_closed():
    with pytest.raises(ValueError, match="differ from the rates page"):
        _parse(html=HTML.replace("$0.1379/kWh", "$0.1400/kWh"))


def test_unlabelled_older_rural_schedule_is_never_read():
    # Page 80 prints an older A3 ($21.56, $0.1397/kWh) without a year label; without the 2026 page the run fails.
    with pytest.raises(ValueError, match=r"A3 \(2026\) not found"):
        _parse(pages=_pages(drop=(59,)))


def test_new_year_reads_the_bylaw_schedules_while_the_page_still_shows_the_old_year():
    # Owner decision 2026-11-23: the bylaw's (2027) schedules apply from January 1 without the page comparison.
    records = _parse(today=date(2027, 1, 2))
    assert {(r.effective_date, r.end_date) for r in records.values()} == {("2027-01-01", "2027-12-31")}
    assert [(c.charge_value, c.end_date) for c in records["B4"].components] == [
        (61.28, "2027-12-31"), (0.1974, "2027-12-31")]
    assert [c.charge_value for c in records["A3"].components] == [25.95, 0.1681, 11.78]
    assert "Schedule C B4 (2027), PDF page 62; not compared" in records["B4"].source_page
    assert "rates effective 2026-01-01" in records["A1"].notes


def test_a_year_the_bylaw_does_not_print_fails_closed():
    with pytest.raises(ValueError, match=r"A1 \(2028\) not found"):
        _parse(today=date(2028, 1, 3))


def test_page_already_showing_next_year_is_not_compared_in_december():
    html = HTML.replace("Effective January 1, 2026", "Effective January 1, 2027").replace("$0.1379/kWh", "$0.1419/kWh")
    records = _parse(html=html, today=date(2026, 12, 10))
    assert {(r.effective_date, r.end_date) for r in records.values()} == {("2026-01-01", "2026-12-31")}
    assert records["A1"].components[1].charge_value == 0.1379


def test_large_commercial_and_other_classes_are_not_emitted():
    assert set(_parse()) == {"A1", "A3", "B1", "B4"}


def test_bylaw_document_id_comes_from_the_page_link():
    assert nh.parse_rates_page(HTML)[2] == "108411"
