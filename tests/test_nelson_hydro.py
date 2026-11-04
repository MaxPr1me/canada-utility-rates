"""Nelson Hydro (BC) parser tests on the Hydro Services Bylaw 2026/2027 schedules and the rates page."""

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
    assert {(r.effective_date, r.confidence) for r in records.values()} == {("2026-01-01", "medium")}
    assert [(c.charge_value, c.charge_unit) for c in records["B4"].components] == [
        (59.06, "$/two months"), (0.1902, "$/kWh")]
    assert "Schedule C B4 (2026), PDF page 61" in records["B4"].source_page


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


def test_stale_page_year_fails_closed_in_a_new_year():
    with pytest.raises(ValueError, match="not current"):
        _parse(today=date(2027, 1, 5))


def test_large_commercial_and_other_classes_are_not_emitted():
    assert set(_parse()) == {"A1", "A3", "B1", "B4"}


def test_bylaw_document_id_comes_from_the_page_link():
    assert nh.parse_rates_page(HTML)[2] == "108411"
