"""Dated representative-model inputs: Ontario TOU/ULO share sets and the Ontario Electricity Rebate (OER).

Offline: synthetic usage_levels documents, the committed data/models/usage_levels.json and taxes.json and the frozen
tests/fixtures/rm_engine_sample.json records (no network, no export). The November 1, 2026 values come from the OEB
Regulated Price Plan Price Report, November 1, 2026 to October 31, 2027 (issued October 16, 2026) and O. Reg. 328/26,
which amends O. Reg. 363/16 s.2 (OER 23.5% -> 15.7% on November 1, 2026).
"""
import copy
import json
import math
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from pipeline.representative_models import (build_models, find_tou_shares, load_taxes, load_usage_levels,
                                            record_monthly_cost, tax_lines)

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "rm_engine_sample.json"
LAST_OLD_DAY, FIRST_NEW_DAY = date(2026, 10, 31), date(2026, 11, 1)
NEW_REPORT = "https://www.oeb.ca/sites/default/files/rpp-price-report-20261016.pdf"
OER = "Ontario Electricity Rebate (OER)"
SETS = (("tou", "ON_RPP_TOU", "ON_RPP_TOU_2026"), ("ulo", "ON_RPP_ULO", "ON_RPP_ULO_2026"))
TOU_SHARES = {"off-peak": 0.64, "mid-peak": 0.18, "on-peak": 0.18}
ULO_PRICES = {"ultra-low-overnight": 0.037, "off-peak": 0.091, "mid-peak": 0.146, "on-peak": 0.377}
RES_TOU, RES_ULO = "ON|electricity|residential|tou|-", "ON|electricity|residential|ulo|-"


def _entry(structure="tou", sectors=("residential",), shares=None, **window):
    entry = {"applies_to": {"province": "ON", "fuel": "electricity", "structure": structure, "sectors": list(sectors)},
             "shares": dict(shares or TOU_SHARES)}
    entry.update(window)
    return entry


def _levels(**entries):
    return {"tou_shares": {"basis": "synthetic test sets", **entries}}


def _found(levels, as_of, structure="tou", sector="residential"):
    return find_tou_shares(levels, "ON", "electricity", structure, sector, as_of)[0]


def _ulo_record():
    return {"id": "test-ulo", "utility_name": "Synthetic Hydro", "province": "ON", "utility_type": "electricity",
            "customer_class": "residential", "rate_structure": "ulo", "tariff_code": "ULO-R",
            "components": [{"component_type": "energy", "component_name": f"ULO {period}", "charge_value": price,
                            "charge_unit": "$/kWh", "tou_period": period, "notes": "Provenance: live_parsed. "}
                           for period, price in ULO_PRICES.items()]}


def _ulo_cost(levels, as_of):
    return record_monthly_cost(_ulo_record(), 1000, sector="residential", structure="ulo", usage_levels=levels,
                               as_of=as_of)


def _in_window(entry, day):
    start, end = entry.get("effective_date"), entry.get("end_date")
    return (start is None or date.fromisoformat(start) <= day) and (end is None or day < date.fromisoformat(end))


def _structures(entry):
    structure = entry["applies_to"]["structure"]
    return [structure] if isinstance(structure, str) else list(structure)


# ---------------------------------------------------------------- engine: find_tou_shares with dates


def test_undated_share_set_matches_every_date():
    levels = _levels(ONLY=_entry())
    for as_of in (date(2000, 1, 1), LAST_OLD_DAY, FIRST_NEW_DAY, "2099-12-31"):
        assert _found(levels, as_of) == "ONLY"
    # The five-argument call of earlier releases still works (as-of defaults to today).
    assert find_tou_shares(levels, "ON", "electricity", "tou", "residential") == ("ONLY", levels["tou_shares"]["ONLY"])


def test_dated_share_sets_apply_from_effective_date_until_before_end_date():
    levels = _levels(OLD=_entry(end_date="2026-11-01"), NEW=_entry(effective_date="2026-11-01"),
                     TERM=_entry(structure="ulo", effective_date="2026-11-01", end_date="2027-11-01"))
    assert [_found(levels, d) for d in (date(2020, 1, 1), LAST_OLD_DAY)] == ["OLD", "OLD"]
    assert [_found(levels, d) for d in (FIRST_NEW_DAY, "2026-11-01", date(2040, 1, 1))] == ["NEW", "NEW", "NEW"]
    assert _found(levels, LAST_OLD_DAY, "ulo") is None
    assert _found(levels, FIRST_NEW_DAY, "ulo") == "TERM"
    assert _found(levels, date(2027, 10, 31), "ulo") == "TERM"
    assert _found(levels, date(2027, 11, 1), "ulo") is None


@pytest.mark.parametrize("first, second, overlap", [
    ({}, {}, LAST_OLD_DAY),
    ({}, {"effective_date": "2026-11-01"}, FIRST_NEW_DAY),
    ({"end_date": "2026-11-02"}, {"effective_date": "2026-11-01"}, FIRST_NEW_DAY),
])
def test_share_sets_in_force_together_fail_closed(first, second, overlap):
    other = {"off-peak": 0.70, "mid-peak": 0.15, "on-peak": 0.15}
    for levels in (_levels(A=_entry(**first), B=_entry(shares=other, **second)),
                   _levels(B=_entry(shares=other, **second), A=_entry(**first))):
        assert find_tou_shares(levels, "ON", "electricity", "tou", "residential", overlap) == (None, None)


def test_only_the_overlapping_days_fail_closed():
    levels = _levels(A=_entry(end_date="2026-11-02"), B=_entry(effective_date="2026-11-01"))
    assert _found(levels, LAST_OLD_DAY) == "A"
    assert _found(levels, FIRST_NEW_DAY) is None
    assert _found(levels, date(2026, 11, 2)) == "B"


@pytest.mark.parametrize("window", [{"effective_date": "2026-13-01"}, {"end_date": "next year"},
                                    {"effective_date": ""}, {"end_date": 20261101}])
def test_malformed_share_dates_fail_closed_at_every_date(window):
    levels = _levels(OLD=_entry(end_date="2026-11-01"), BAD=_entry(**window))
    for as_of in (date(2020, 1, 1), LAST_OLD_DAY, FIRST_NEW_DAY):
        assert find_tou_shares(levels, "ON", "electricity", "tou", "residential", as_of) == (None, None)


def test_dates_and_conflicts_stay_within_their_own_key():
    levels = _levels(RES_OLD=_entry(end_date="2026-11-01"), RES_NEW=_entry(effective_date="2026-11-01"),
                     SMALL=_entry(sectors=("commercial_small",)), SMALL_COPY=_entry(sectors=("commercial_small",)))
    assert _found(levels, FIRST_NEW_DAY) == "RES_NEW"
    assert _found(levels, FIRST_NEW_DAY, sector="commercial_small") is None
    assert find_tou_shares(levels, "BC", "electricity", "tou", "residential", FIRST_NEW_DAY) == (None, None)
    assert find_tou_shares(levels, "ON", "gas", "tou", "residential", FIRST_NEW_DAY) == (None, None)


def test_record_cost_uses_the_share_set_in_force_on_the_as_of_date():
    levels = load_usage_levels()
    old, new = _ulo_cost(levels, LAST_OLD_DAY), _ulo_cost(levels, FIRST_NEW_DAY)
    assert (old["status"], old["shares_id"]) == ("ok", "ON_RPP_ULO")
    assert (new["status"], new["shares_id"]) == ("ok", "ON_RPP_ULO_2026")
    # 1,000 kWh x (3.7/9.1/14.6/37.7 cents at 40/20/27/13% and at 41/20/26/13%)
    assert old["cost"] == pytest.approx(121.43, abs=1e-9)
    assert new["cost"] == pytest.approx(120.34, abs=1e-9)


def test_record_cost_is_not_computable_while_two_share_sets_overlap():
    levels = copy.deepcopy(load_usage_levels())
    levels["tou_shares"]["ON_RPP_ULO"]["end_date"] = None
    assert _ulo_cost(levels, LAST_OLD_DAY)["shares_id"] == "ON_RPP_ULO"
    result = _ulo_cost(levels, FIRST_NEW_DAY)
    assert (result["status"], result["cost"], result["shares_id"]) == ("not_computable", None, None)
    assert any("(no matching share set)" in reason for reason in result["reasons"])


# ---------------------------------------------------------------- live data: data/models/usage_levels.json


@pytest.mark.parametrize("sector", ("residential", "commercial_small"))
@pytest.mark.parametrize("structure, old_id, new_id", SETS)
def test_live_ontario_share_sets_switch_on_november_1_2026(structure, old_id, new_id, sector):
    levels = load_usage_levels()
    for as_of in ("2026-10-09", "2026-10-16", LAST_OLD_DAY):
        assert find_tou_shares(levels, "ON", "electricity", structure, sector, as_of)[0] == old_id
    for as_of in (FIRST_NEW_DAY, date(2027, 10, 31), date(2028, 1, 1)):
        assert find_tou_shares(levels, "ON", "electricity", structure, sector, as_of)[0] == new_id


def test_live_ontario_share_values_sources_and_windows():
    shares = load_usage_levels()["tou_shares"]
    assert shares["ON_RPP_TOU"]["shares"] == shares["ON_RPP_TOU_2026"]["shares"] == TOU_SHARES
    assert shares["ON_RPP_ULO"]["shares"] == {"ultra-low-overnight": 0.40, "off-peak": 0.20, "mid-peak": 0.27,
                                              "on-peak": 0.13}
    assert shares["ON_RPP_ULO_2026"]["shares"] == {"ultra-low-overnight": 0.41, "off-peak": 0.20, "mid-peak": 0.26,
                                                   "on-peak": 0.13}
    for _, old_id, new_id in SETS:
        old, new = shares[old_id], shares[new_id]
        assert (old.get("effective_date"), old["end_date"]) == (None, "2026-11-01")
        assert (new["effective_date"], new.get("end_date")) == ("2026-11-01", None)
        assert new["applies_to"] == old["applies_to"]
        assert new["period"] == "November 1, 2026 to October 31, 2027"
        assert new["source"]["url"] == NEW_REPORT and new["source"]["retrieved"] == "2026-10-30"
        assert "issued October 16, 2026" in new["source"]["title"]
        for entry in (old, new):
            assert math.isclose(math.fsum(entry["shares"].values()), 1.0, abs_tol=1e-12)
            # The quoted percentages, in order, are the share values.
            quoted = [int(pct) / 100 for pct in re.findall(r"(\d+)%", entry["source"]["quote"])]
            assert quoted == list(entry["shares"].values())


def test_live_share_sets_never_overlap_at_any_boundary():
    tou_shares = load_usage_levels()["tou_shares"]
    entries = {k: v for k, v in tou_shares.items() if isinstance(v, dict) and "applies_to" in v}
    days = {date(2000, 1, 1)}
    for entry in entries.values():
        for field in ("effective_date", "end_date"):
            if entry.get(field) is not None:
                day = date.fromisoformat(entry[field])
                days |= {day - timedelta(days=1), day}
    keys = {(e["applies_to"]["province"], e["applies_to"]["fuel"], structure, sector) for e in entries.values()
            for structure in _structures(e) for sector in e["applies_to"]["sectors"]}
    for province, fuel, structure, sector in sorted(keys):
        for day in sorted(days):
            in_force = [k for k, e in entries.items() if (e["applies_to"]["province"], e["applies_to"]["fuel"]) == (
                province, fuel) and structure in _structures(e) and sector in e["applies_to"]["sectors"]
                and _in_window(e, day)]
            assert len(in_force) <= 1, (province, structure, sector, day, in_force)
            found = find_tou_shares({"tou_shares": entries}, province, fuel, structure, sector, day)[0]
            assert found == (in_force[0] if in_force else None)


def test_live_ontario_seasons_cite_the_2026_report_and_keep_the_thresholds():
    season = load_usage_levels()["seasons"]["ON_RPP"]
    assert (season["winter"]["residential_tier_threshold_kwh"], season["summer"]["residential_tier_threshold_kwh"],
            season["winter"]["non_residential_tier_threshold_kwh"],
            season["summer"]["non_residential_tier_threshold_kwh"]) == (1000, 600, 750, 750)
    assert season["source"]["url"] == NEW_REPORT
    assert "rpp-price-report-20251017.pdf" in season["source"]["note"]
    assert (season["tiered_profile_reference"]["tier_1"], season["tiered_profile_reference"]["tier_2"]) == (0.65, 0.35)


# ---------------------------------------------------------------- live data: Ontario Electricity Rebate


@pytest.mark.parametrize("sector, kwh, kw", [("residential", 500, None), ("residential", 2000, None),
                                             ("commercial_small", 2000, 10), ("commercial_small", 8000, 25)])
def test_live_ontario_electricity_rebate_is_15_7_percent_from_november_1_2026(sector, kwh, kw):
    taxes, rates = load_taxes(), {}
    for as_of in (LAST_OLD_DAY, FIRST_NEW_DAY):
        applied, skipped = tax_lines(taxes, "ON", "electricity", sector, kwh, kw, as_of)
        assert [line["name"] for line in applied] == ["HST", OER]
        rates[as_of] = applied[1]["rate"]
        # The other rate period of the same rebate is not a separate "not applied" line.
        assert [s for s in skipped if s["name"] == OER] == []
    assert rates == {LAST_OLD_DAY: 0.235, FIRST_NEW_DAY: 0.157}


def test_a_dated_line_without_a_replacement_in_force_is_still_reported():
    line = {"name": "Future rebate", "kind": "rebate", "rate": 0.1, "base": "pre_tax_subtotal", "order": 1,
            "eligibility": {"sectors": ["residential"]}, "effective_date": "2026-11-01", "end_date": "2027-11-01"}
    taxes = {"jurisdictions": {"ON": {"electricity": {"residential": [line]}}}}
    for as_of, reason in ((LAST_OLD_DAY, "not in effect until 2026-11-01"), ("2027-11-01", "ended 2027-11-01")):
        applied, skipped = tax_lines(taxes, "ON", "electricity", "residential", 1000, None, as_of)
        assert applied == [] and [s["reason"] for s in skipped] == [reason]


def test_live_ontario_rebate_thresholds_still_exclude_larger_business():
    for as_of, rate in ((LAST_OLD_DAY, 0.235), (FIRST_NEW_DAY, 0.157)):
        applied, skipped = tax_lines(load_taxes(), "ON", "electricity", "commercial_medium", 40000, 100, as_of)
        assert [line["name"] for line in applied] == ["HST"]
        # One entry for the rate period in force; the other period is not listed again.
        rebate = [s for s in skipped if s["name"] == OER]
        assert [(s["rate"], s["reason"].split(" (")[0]) for s in rebate] == [(rate, "threshold not met")]


def test_live_ontario_rebate_lines_differ_only_in_rate_dates_and_source():
    electricity = load_taxes()["jurisdictions"]["ON"]["electricity"]
    for group in ("residential", "commercial"):
        old, new = [line for line in electricity[group] if line["name"] == OER]
        assert (old["rate"], old["effective_date"], old["end_date"]) == (0.235, "2025-11-01", "2026-11-01")
        assert (new["rate"], new["effective_date"], new["end_date"]) == (0.157, "2026-11-01", None)
        same = ("kind", "base", "order", "eligibility", "confidence")
        assert {k: old[k] for k in same} == {k: new[k] for k in same}
        assert new["source_url"] == "https://www.ontario.ca/laws/regulation/R26328"
        assert '"15.7 per cent"' in new["source_note"] and "O. Reg. 328/26" in old["source_note"]


# ---------------------------------------------------------------- models built either side of November 1, 2026


def test_models_switch_share_sets_and_rebate_on_november_1_2026():
    fx = json.loads(FIXTURE.read_text(encoding="utf-8"))
    usage_levels, taxes = load_usage_levels(), load_taxes()
    expected = {"2026-10-31": ("ON_RPP_TOU", "ON_RPP_ULO", 0.235),
                "2026-11-01": ("ON_RPP_TOU_2026", "ON_RPP_ULO_2026", 0.157)}
    for as_of, (tou_id, ulo_id, oer) in expected.items():
        models = {m["id"]: m for m in build_models(fx["records"], fx["crosswalk"], usage_levels, taxes,
                                                   as_of=as_of)["models"]}
        for model_id, shares_id in ((RES_TOU, tou_id), (RES_ULO, ulo_id)):
            model = models[model_id]
            assert model["tou"]["shares_id"] == shares_id
            assert not [w for w in model["warnings"] if w.startswith("TOU shares")]
            typical = next(level for level in model["levels"] if level["id"] == "typical")
            assert {line["name"]: line["rate"] for line in typical["with_tax"]["lines"]} == {"HST": 0.13, OER: oer}
    later = {m["id"]: m for m in build_models(fx["records"], fx["crosswalk"], usage_levels, taxes,
                                              as_of="2027-11-01")["models"]}
    assert ("TOU shares ON_RPP_TOU_2026 cover November 1, 2026 to October 31, 2027; the as-of date is later"
            in later[RES_TOU]["warnings"])
