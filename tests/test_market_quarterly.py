"""Quarterly market history for the Rate History tab: scripts/market_quarterly.py and both market builders.

Owner decision 50 (2026-11-23): only complete calendar quarters are published, and each value is the hour-weighted
mean of its three monthly values. Ontario weighs each month's calendar hours in EST (the IESO convention); Alberta
weighs its observed local-time hours, which include the daylight-saving hour. Expected values were computed
independently from the formula with exact fractions, rounded half up to six decimals. The builder runs reuse the
offline worlds of tests/test_market_rolling.py and tests/test_alberta_market.py; nothing is downloaded.
"""
import copy
import csv
import json
from datetime import timedelta
from decimal import Decimal

import pytest

from tests import test_alberta_market as alberta
from tests import test_market_rolling as rolling
from tests.test_alberta_market import built  # noqa: F401 (the Alberta builder fixture, reused as is)

bom, bam = rolling.bom, alberta.bam
mq = bom.mq
MILLIONTH = Decimal("0.000001")
DOCUMENT_KEYS = ["version", "kind", "province", "derivation_method", "unit", "measures", "source", "weighting", "rule",
                 "first_quarter", "last_quarter", "quarters"]
ONTARIO_HEADER = ("month,era,energy_arithmetic,energy_weighted,ga_class_b,total_arithmetic,energy_source,ga_source,"
                  "observed_hours\n")
# Rows of data/market/ontario_market_monthly.csv: the IESO monthly-table months carry no observed hours (0) and the
# hourly Ontario Price archive starts on July 11, 2026 (504 hours).
ONTARIO_ROWS = (
    "2025-04,hoep,39.22,41.09,69.15,108.37,hoep_monthly_report,ga_workbook,0\n"
    "2025-05,oemp,22.46,24.67,134.93,157.39,oemp_monthly_table,ga_workbook,0\n"
    "2025-06,oemp,50.07,56.12,59.72,109.79,oemp_monthly_table,ga_workbook,0\n"
    "2026-07,oemp,72.86,80.32,39.83,112.69,oemp_monthly_table,ga_monthly_report,504\n"
    "2026-08,oemp,64.40,68.22,44.35,108.75,oemp_monthly_table,ga_monthly_report,744\n"
    "2026-09,oemp,51.03,53.47,64.77,115.80,oemp_monthly_table,ga_monthly_report,720\n"
)


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise RuntimeError("live network disabled in deterministic tests")

    monkeypatch.setattr(rolling.gmp.requests, "get", blocked)
    monkeypatch.setattr(rolling.gmp, "REQUEST_DELAY_SECONDS", 0)


def _ontario(rows=ONTARIO_ROWS):
    return bom.load_monthly((ONTARIO_HEADER + rows).encode("utf-8"), "monthly history").values()


def _alberta_row(month, energy, hours):
    return {"month": month, "energy_arithmetic": energy, "total_arithmetic": energy, "observed_hours": hours,
            "source_url": bam.summary_url(month)}


def _quarter(document, name):
    return next(entry for entry in document["quarters"] if entry["quarter"] == name)


def _ontario_options():
    return {"generated_at": rolling.GENERATED, "window_months": rolling.SIZE, "first_month": rolling.FIRST}


def test_hour_weighted_mean_of_a_31_28_31_day_quarter_is_the_mean_of_every_hour():
    values, hours = [Decimal("0.09"), Decimal("0.18"), Decimal("0.36")], [31 * 24, 28 * 24, 31 * 24]
    mean = mq.hour_weighted_mean(values, hours)
    assert mean == Decimal("0.211")  # (0.09 x 744 + 0.18 x 672 + 0.36 x 744) / 2160 = 455.76 / 2160
    every_hour = [value for value, count in zip(values, hours) for _ in range(count)]
    assert sum(every_hour) / len(every_hour) == mean
    assert sum(values) / 3 == Decimal("0.21")  # a plain mean would weigh February like a 31-day month
    assert mq.round_value(mean) == Decimal("0.211000")
    assert mq.round_value(Decimal("0.0123445")) == Decimal("0.012345")  # half up, not half even
    assert str(mq.round_value(Decimal("-0.0000004"))) == "0.000000"
    with pytest.raises(mq.QuarterlyError):
        mq.hour_weighted_mean(values, [744, 0, 744])


def test_a_quarter_with_a_missing_month_is_left_out_and_later_complete_quarters_are_published():
    # The Alberta history starts in November 2021, so 2021Q4 has two months; June 2022 is missing too.
    months = [("2021-11", 721), ("2021-12", 744), ("2022-01", 744), ("2022-02", 672), ("2022-03", 743),
              ("2022-04", 720), ("2022-05", 744), ("2022-07", 744), ("2022-08", 744), ("2022-09", 720)]
    document = bam.quarterly_document([_alberta_row(month, 0.05, hours) for month, hours in months])
    assert [entry["quarter"] for entry in document["quarters"]] == ["2022Q1", "2022Q3"]
    assert (document["first_quarter"], document["last_quarter"]) == ("2022Q1", "2022Q3")
    assert _quarter(document, "2022Q1")["hours"] == 744 + 672 + 743
    with pytest.raises(bam.MarketDataError, match="no complete quarter"):
        bam.quarterly_document([_alberta_row(month, 0.05, hours) for month, hours in months[:2]])


def test_ontario_weighs_est_calendar_hours_even_without_observed_hours_and_converts_to_dollars_per_kwh():
    document = bom.quarterly_document(_ontario())
    assert list(document) == DOCUMENT_KEYS
    assert (document["province"], document["unit"], document["measures"]) == ("ON", "$/kWh",
                                                                               ["energy", "ga_class_b", "total"])
    assert document["source"] == "data/market/ontario_market_monthly.csv"
    assert "Eastern Standard Time" in document["weighting"] and "owner decision 50" in document["rule"]
    q2 = _quarter(document, "2025Q2")
    assert list(q2) == ["quarter", "start", "end", "months", "hours", "energy", "ga_class_b", "total", "eras",
                        "energy_sources", "ga_sources"]
    assert (q2["start"], q2["end"], q2["months"]) == ("2025-04-01", "2025-06-30", ["2025-04", "2025-05", "2025-06"])
    assert q2["hours"] == 720 + 744 + 720  # every observed_hours is 0
    # (39.22 x 720 + 22.46 x 744 + 50.07 x 720) / 2184 = 37.0875 $/MWh; the plain mean would be 0.037250.
    assert (q2["energy"], q2["ga_class_b"], q2["total"]) == (Decimal("0.037087"), Decimal("0.088450"),
                                                             Decimal("0.125537"))
    assert (q2["eras"], q2["energy_sources"], q2["ga_sources"]) == (["hoep", "oemp"],
                                                                    ["hoep_monthly_report", "oemp_monthly_table"],
                                                                    ["ga_workbook"])
    q3 = _quarter(document, "2026Q3")
    assert q3["hours"] == 744 + 744 + 720  # July counts 744 hours, not its 504 observed ones
    assert (q3["energy"], q3["ga_class_b"], q3["total"]) == (Decimal("0.062891"), Decimal("0.049486"),
                                                             Decimal("0.112377"))
    assert (q3["eras"], q3["ga_sources"]) == (["oemp"], ["ga_monthly_report"])


def test_alberta_weighs_local_hours_with_the_daylight_saving_hour_and_has_no_global_adjustment():
    rows = [_alberta_row("2024-10", 0.0512345678, 744), _alberta_row("2024-11", 0.0798765432, 721),
            _alberta_row("2024-12", 0.1023456789, 744)]
    document = bam.quarterly_document(rows)
    assert list(document) == DOCUMENT_KEYS
    assert (document["province"], document["measures"]) == ("AB", ["energy"])
    assert document["source"] == "data/market/alberta_market_monthly.csv" and "local time" in document["weighting"]
    (q4,) = document["quarters"]
    assert list(q4) == ["quarter", "start", "end", "months", "hours", "energy", "source_urls"]
    assert q4["hours"] == 2209
    assert q4["energy"] == Decimal("0.077798")  # 0.077797 if November counted 720 hours
    assert q4["source_urls"] == [bam.summary_url(month) for month in ("2024-10", "2024-11", "2024-12")]
    rendered = mq.render(document, indent=None, ensure_ascii=True).decode("utf-8")
    for ontario_only in ("ga_class_b", "Global Adjustment", "Eastern Standard Time"):
        assert ontario_only not in rendered
    spring = bam.quarterly_document([_alberta_row("2024-01", 0.05, 744), _alberta_row("2024-02", 0.05, 696),
                                     _alberta_row("2024-03", 0.05, 743)])
    assert spring["quarters"][0]["hours"] == 2183
    for hours in (700, 723):
        rows[1]["observed_hours"] = hours
        with pytest.raises(bam.MarketDataError, match=f"2024-11: {hours} observed hours"):
            bam.quarterly_document(rows)


def test_ontario_total_stays_within_one_millionth_of_energy_plus_ga():
    # Q1 2024 values chosen so that rounding each measure on its own moves the total by exactly one millionth.
    rows = ("2024-01,hoep,30.89,31.00,72.33,103.22,hoep_hourly,ga_workbook,744\n"
            "2024-02,hoep,19.65,20.00,46.82,66.47,hoep_hourly,ga_workbook,696\n"
            "2024-03,hoep,50.58,51.00,48.68,99.26,hoep_hourly,ga_workbook,744\n") + ONTARIO_ROWS
    document = bom.quarterly_document(_ontario(rows))
    q1 = _quarter(document, "2024Q1")
    assert (q1["energy"], q1["ga_class_b"], q1["total"]) == (Decimal("0.034016"), Decimal("0.056144"),
                                                             Decimal("0.090159"))
    published = json.loads(mq.render(document, indent=2, ensure_ascii=False), parse_float=Decimal)
    for entry in published["quarters"]:
        assert abs(entry["total"] - (entry["energy"] + entry["ga_class_b"])) <= MILLIONTH
    assert abs(q1["total"] - (q1["energy"] + q1["ga_class_b"])) == MILLIONTH


def test_rendering_is_deterministic_and_carries_no_clock():
    months = list(_ontario())
    first = mq.render(bom.quarterly_document(months), indent=2, ensure_ascii=False)
    assert mq.render(bom.quarterly_document(reversed(months)), indent=2, ensure_ascii=False) == first
    assert first.endswith(b"}\n") and b"\r" not in first and b"generated" not in first and b"as_of" not in first
    assert json.loads(first)["quarters"][0]["energy"] == 0.037087
    rows = [_alberta_row(month, 0.05, hours) for month, hours in (("2024-10", 744), ("2024-11", 721),
                                                                  ("2024-12", 744))]
    compact = mq.render(bam.quarterly_document(rows), indent=None, ensure_ascii=True)
    assert compact == mq.render(bam.quarterly_document(copy.deepcopy(rows)), indent=None, ensure_ascii=True)
    assert compact.count(b"\n") == 1 and b'"energy":0.05,' in compact


def test_ontario_builder_writes_the_quarterly_file_with_its_outputs_but_not_in_a_dry_run(tmp_path, capsys):
    paths = rolling._paths(tmp_path)
    options = _ontario_options()
    assert bom.main(rolling._args(paths, "--refresh-hoep", "--dry-run"), fetch=rolling._fetcher(rolling._world()),
                    **options) == 0
    assert "Quarters: 6 complete, 2024Q1..2025Q2" in capsys.readouterr().out
    assert sorted(path.name for path in tmp_path.iterdir()) == ["archive.csv"]
    assert bom.main(rolling._args(paths, "--refresh-hoep"), fetch=rolling._fetcher(rolling._world()), **options) == 0
    written = paths["quarterly.json"].read_bytes()
    document = json.loads(written, parse_float=Decimal)
    assert [entry["quarter"] for entry in document["quarters"]] == ["2024Q1", "2024Q2", "2024Q3", "2024Q4", "2025Q1",
                                                                    "2025Q2"]
    assert _quarter(document, "2025Q2")["eras"] == ["hoep", "oemp"]  # September 2025 has no GA actual yet
    stored = bom.load_monthly(paths["monthly.csv"].read_bytes(), "monthly history")
    assert written == mq.render(bom.quarterly_document(stored.values()), indent=2, ensure_ascii=False)
    options["generated_at"] = rolling.GENERATED + timedelta(days=1)
    assert bom.main(rolling._args(paths), fetch=rolling._fetcher(rolling._world()), **options) == 0
    assert paths["quarterly.json"].read_bytes() == written  # the CI path, from the stored monthly history
    capsys.readouterr()
    options["generated_at"] = rolling.GENERATED + timedelta(days=2)
    assert bom.main(rolling._args(paths), fetch=rolling._fetcher(rolling._world()), **options) == 0
    assert "All outputs are unchanged." in capsys.readouterr().out
    assert paths["quarterly.json"].read_bytes() == written


def test_ontario_builder_fails_closed_when_the_quarterly_file_cannot_be_built(tmp_path, monkeypatch, capsys):
    paths = rolling._paths(tmp_path)

    def malformed(*args, **kwargs):
        raise mq.QuarterlyError("invalid month '2025-13'; expected YYYY-MM")

    with monkeypatch.context() as patch:
        patch.setattr(mq, "build_document", malformed)
        assert bom.main(rolling._args(paths, "--refresh-hoep"), fetch=rolling._fetcher(rolling._world()),
                        **_ontario_options()) == 1
    assert "quarterly history: invalid month" in capsys.readouterr().err
    assert sorted(path.name for path in tmp_path.iterdir()) == ["archive.csv"]
    clash = rolling._args(paths, "--refresh-hoep", "--quarterly-output", str(paths["monthly.csv"]))
    assert bom.main(clash, fetch=rolling._fetcher(rolling._world()), **_ontario_options()) == 1
    assert "must differ" in capsys.readouterr().err
    assert sorted(path.name for path in tmp_path.iterdir()) == ["archive.csv"]


def test_alberta_builder_writes_the_quarterly_file_with_its_outputs_but_not_in_a_dry_run(built, tmp_path,  # noqa: F811
                                                                                          monkeypatch, capsys):
    def arguments(folder):
        return ["--output", str(folder / "market.json"), "--hourly-csv", str(folder / "hourly.csv"), "--monthly-csv",
                str(folder / "monthly.csv"), "--quarterly-output", str(folder / "quarterly.json")]

    quarterly = tmp_path / "quarterly.json"
    monkeypatch.setattr(bam, "build", lambda *args: built[:3])
    assert bam.main(arguments(tmp_path) + ["--dry-run"]) == 0
    assert "20 complete quarters 2021Q4..2026Q3" in capsys.readouterr().out
    assert not list(tmp_path.iterdir())
    assert bam.main(arguments(tmp_path)) == 0
    written = quarterly.read_bytes()
    document = json.loads(written, parse_float=Decimal)
    assert (document["first_quarter"], document["last_quarter"], len(document["quarters"])) == ("2021Q4", "2026Q3", 20)
    assert [entry["hours"] for entry in document["quarters"][:2]] == [744 + 721 + 744, 744 + 672 + 743]
    assert {entry["energy"] for entry in document["quarters"]} == {Decimal("0.05")}
    with (tmp_path / "monthly.csv").open(encoding="utf-8", newline="") as stream:
        assert written == mq.render(bam.quarterly_document(list(csv.DictReader(stream))), indent=None,
                                    ensure_ascii=True)
    stamp = quarterly.stat().st_mtime_ns
    assert bam.main(arguments(tmp_path)) == 0
    assert quarterly.read_bytes() == written and quarterly.stat().st_mtime_ns == stamp
    malformed = copy.deepcopy(built[2])
    malformed[1]["observed_hours"] = 700  # November 2021 has 721 local hours
    monkeypatch.setattr(bam, "build", lambda *args: (built[0], built[1], malformed))
    fresh = tmp_path / "fresh"
    assert bam.main(arguments(fresh)) == 1
    assert "2021-11: 700 observed hours" in capsys.readouterr().err
    assert not fresh.exists()
