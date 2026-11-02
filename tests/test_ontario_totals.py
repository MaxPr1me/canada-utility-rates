"""Combined Ontario totals retain actual hours, negative prices and explicit gaps."""
import copy
import csv
import importlib.util
import io
import json
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NAME = "export_ontario_totals"
spec = importlib.util.spec_from_file_location(NAME, ROOT / "scripts" / f"{NAME}.py")
t = importlib.util.module_from_spec(spec)
sys.modules[NAME] = t
spec.loader.exec_module(t)
m, arc, gmp = t.market, t.arc, t.gmp


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("total exports must not download")
    monkeypatch.setattr(gmp.requests, "get", blocked)


def _hours(first, last, value):
    return {(day, hour): Decimal(value) for day in arc._days(first, last) for hour in arc.HOURS}


def _months(first="2025-01", last="2025-12"):
    return {
        key: m.Month(key, m._era(key), Decimal("20"), Decimal("21"),
                     Decimal("-2.92") if key == "2025-12" else Decimal("100"),
                     m.HOEP_HOURLY if key < "2025-04" else m.HOEP_REPORT if key == "2025-04" else m.OEMP_TABLE,
                     m.GA_WORKBOOK, 0)
        for key in m._span(first, last)
    }


@pytest.fixture
def inputs():
    return {
        "hoep": _hours(date(2025, 1, 1), date(2025, 3, 31), "20"),
        "monthly": _months(),
        "archive": {(date(2025, 12, 1), hour): arc.Row(Decimal("19"), arc.REPORT, 1,
                                                            Decimal("1"), "Final") for hour in arc.HOURS},
        "april": _hours(date(2025, 4, 1), date(2025, 4, 30), "19.96"),
        "first": date(2025, 1, 1),
    }


def _rows(content):
    return list(csv.DictReader(io.StringIO(content.decode())))


def _row(files, day, hour=1):
    return next(row for row in _rows(files[t.HOURLY_NAME])
                if row["date"] == day and row["hour_ending"] == str(hour))


def _supplement():
    excerpt = json.loads((ROOT / "tests" / "fixtures" / "ieso_market_rolling.json").read_text(
        encoding="utf-8"))["hoep_hourly"]["csv_excerpt"]
    lines = excerpt.splitlines()[:4]
    for day in arc._days(date(2025, 1, 1), date(2025, 4, 30)):
        price = "19.96" if day.month == 4 else "20.00"
        lines += [",".join([str(day), str(hour), price] + ["0.00"] * 6) for hour in arc.HOURS]
    return ("\n".join(lines) + "\n").encode()


def test_exact_total_units_and_negative_ga(inputs):
    files, meta = t.build(**inputs)
    assert _row(files, "2025-01-01")["total_cents_per_kwh"] == "12.000"
    assert _row(files, "2025-12-01")["total_cents_per_kwh"] == "1.708"
    assert _row(files, "2025-12-01")["market"] == "oemp"
    assert meta["unit"] == "CAD cents/kWh"
    assert set(_row(files, "2025-01-01")) == set(t.HOURLY_FIELDS)


def test_april_disagreement_is_flagged_not_hidden_or_changed(inputs):
    before = copy.deepcopy(inputs)
    files, meta = t.build(**inputs)
    april = _row(files, "2025-04-30", 24)
    assert april["total_cents_per_kwh"] == "11.996"
    assert april["monthly_average_total_cents_per_kwh"] == "12.000"
    assert april["status"] == "observed_monthly_mismatch"
    assert meta["monthly_reconciliation_warnings"][0]["difference_per_mwh"] == "-0.04"
    assert inputs == before


def test_gaps_stay_blank_with_separate_monthly_reference(inputs):
    files, _ = t.build(**inputs)
    row = _row(files, "2025-05-01")
    assert row["total_cents_per_kwh"] == ""
    assert row["status"] == "missing_hourly_energy"
    assert row["monthly_average_total_cents_per_kwh"] == "12.000"
    monthly = next(row for row in _rows(files[t.MONTHLY_NAME]) if row["month"] == "2025-05")
    assert monthly["available_hourly_totals"] == "0"
    assert monthly["expected_hours"] == "744"


@pytest.mark.parametrize("ga,lfda,status", [
    (True, None, "pending_lfda"),
    (False, None, "pending_lfda_and_class_b_ga"),
    (False, Decimal("1"), "pending_class_b_ga"),
    (True, Decimal("0"), "observed"),
])
def test_missing_is_not_zero(inputs, ga, lfda, status):
    day = date(2025, 12, 1) if ga else date(2026, 1, 1)
    for hour in arc.HOURS:
        inputs["archive"][(day, hour)] = arc.Row(Decimal("0"), arc.REPORT, 1, lfda, "Final" if lfda else "")
    if lfda == 0:
        inputs["archive"][(day, 1)] = arc.Row(Decimal("0"), arc.REPORT, 1, lfda, "Final")
        inputs["monthly"]["2025-12"] = m.Month("2025-12", "oemp", Decimal(0), Decimal(0), Decimal(0),
                                             m.OEMP_TABLE, m.GA_WORKBOOK, 0)
    files, _ = t.build(**inputs)
    row = _row(files, str(day))
    assert row["status"] == status
    assert row["total_cents_per_kwh"] == ("0.000" if lfda == 0 else "")


def test_preliminary_adjustment_is_visible(inputs):
    inputs["archive"][(date(2025, 12, 1), 1)] = arc.Row(Decimal("19"), arc.REPORT, 1, Decimal("1"), "Preliminary")
    files, _ = t.build(**inputs)
    assert _row(files, "2025-12-01")["status"] == "observed_preliminary_lfda"


def test_total_can_be_negative(inputs):
    inputs["archive"][(date(2025, 12, 1), 1)] = arc.Row(Decimal("-19"), arc.REPORT, 1, Decimal("1"), "Final")
    files, _ = t.build(**inputs)
    assert _row(files, "2025-12-01")["total_cents_per_kwh"] == "-2.092"


def test_other_month_disagreement_fails_closed(inputs):
    inputs["hoep"][(date(2025, 1, 1), 1)] = Decimal("100")
    with pytest.raises(t.MarketDataError, match="2025-01: hourly energy mean"):
        t.build(**inputs)


def test_consecutive_monthly_history_required(inputs):
    del inputs["monthly"]["2025-06"]
    with pytest.raises(t.MarketDataError, match="consecutive"):
        t.build(**inputs)


def test_no_oemp_before_market_change(inputs):
    inputs["archive"][(date(2025, 4, 30), 1)] = arc.Row(Decimal(19), arc.REPORT, 1, Decimal(1), "Final")
    with pytest.raises(t.MarketDataError, match="pre-market"):
        t.build(**inputs)


def test_supplement_is_source_derived_and_overlap_checked(inputs):
    content = _supplement()
    april = t.load_supplement(content, inputs["hoep"])
    assert april == inputs["april"]
    inputs["hoep"][(date(2025, 2, 1), 1)] = Decimal("99")
    with pytest.raises(t.MarketDataError, match="disagrees with the HOEP archive"):
        t.load_supplement(content, inputs["hoep"])


@pytest.mark.parametrize("mutation", ["day", "hour", "duplicate"])
def test_incomplete_or_duplicate_supplement_rejected(inputs, mutation):
    lines = _supplement().decode().splitlines()
    if mutation == "day":
        lines = [line for line in lines if not line.startswith("2025-04-30,")]
    elif mutation == "hour":
        lines = [line for line in lines if not line.startswith("2025-04-30,24,")]
    else:
        lines.append(lines[-1])
    with pytest.raises(t.MarketDataError):
        t.load_supplement(("\n".join(lines) + "\n").encode(), inputs["hoep"])


def test_full_2020_2025_grid_and_leap_days(inputs):
    inputs["hoep"] = _hours(date(2020, 1, 1), date(2025, 3, 31), "20")
    inputs["monthly"] = _months("2020-01")
    inputs["first"] = t.FIRST_DAY
    files, meta = t.build(**inputs)
    rows = _rows(files[t.HISTORICAL_NAME])
    assert len(rows) == meta["historical_2020_2025_rows"] == 52608
    assert len({(row["date"], row["hour_ending"]) for row in rows}) == 52608
    assert rows[0]["date"] == "2020-01-01" and rows[0]["hour_ending"] == "1"
    assert rows[-1]["date"] == "2025-12-31" and rows[-1]["hour_ending"] == "24"
    for day in ("2020-02-29", "2024-02-29", "2025-03-09", "2025-11-02"):
        assert [int(row["hour_ending"]) for row in rows if row["date"] == day] == list(range(1, 25))


@pytest.mark.parametrize("remove", [True, False])
def test_existing_totals_cannot_be_erased(tmp_path, inputs, remove):
    files, _ = t.build(**inputs)
    target = tmp_path / t.HOURLY_NAME
    target.write_bytes(files[t.HOURLY_NAME])
    rows = _rows(files[t.HOURLY_NAME])
    if remove:
        rows.pop(0)
    else:
        rows[0]["total_cents_per_kwh"] = ""
    with pytest.raises(t.MarketDataError, match="lost historical|erase"):
        t.check_no_loss(target, t._csv(t.HOURLY_FIELDS, rows))


def test_cli_idempotence_dry_run_and_failure_preserve_files(tmp_path, capsys):
    hoep = _hours(date(2020, 1, 1), date(2025, 3, 31), "20")
    sources = {
        "--hoep-csv": m.serialize_hoep(hoep),
        "--monthly-csv": m.serialize_monthly(list(_months("2020-01").values())),
        "--archive": arc.serialize({}),
        "--hoep-2025-source": _supplement(),
    }
    args = ["--output-dir", str(tmp_path / "output")]
    for flag, content in sources.items():
        path = tmp_path / (flag[2:] + ".csv")
        path.write_bytes(content)
        args += [flag, str(path)]
    assert t.main(args + ["--dry-run"]) == 0
    assert not (tmp_path / "output").exists()
    assert t.main(args) == 0
    before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns) for path in (tmp_path / "output").iterdir()}
    assert len(before) == 4
    assert t.main(args) == 0
    assert before == {path.name: (path.read_bytes(), path.stat().st_mtime_ns)
                      for path in (tmp_path / "output").iterdir()}
    for flag in sources:
        if flag == "--hoep-2025-source":
            continue
        path = tmp_path / (flag[2:] + ".csv")
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert t.main(args) == 0
    assert before == {path.name: (path.read_bytes(), path.stat().st_mtime_ns)
                      for path in (tmp_path / "output").iterdir()}
    (tmp_path / "monthly-csv.csv").write_text("bad header\n", encoding="utf-8")
    assert t.main(args) == 1
    assert "unexpected header" in capsys.readouterr().err
    assert before == {path.name: (path.read_bytes(), path.stat().st_mtime_ns)
                      for path in (tmp_path / "output").iterdir()}
