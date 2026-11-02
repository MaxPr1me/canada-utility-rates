"""Observed AESO history; source-derived format tests and independent synthetic years."""
import copy
import csv
import importlib.util
import io
import json
import math
import sys
from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_alberta_market", ROOT / "scripts" / "build_alberta_market.py")
bam = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bam
spec.loader.exec_module(bam)
FX = json.loads((ROOT / "tests" / "fixtures" / "aeso_history.json").read_text())


def csv_source(rows):
    stream = io.StringIO()
    stream.write("Pool Price\n\n\"\"\n\nDate (HE),Price ($),30Ravg ($),AIL Demand (MW)\n")
    writer = csv.writer(stream)
    for day, hour, price in rows:
        writer.writerow([f"{day:%m/%d/%Y} {hour}", price, "-", "-"])
    return stream.getvalue().encode()


@pytest.mark.parametrize("kind,day,count", [("spring", date(2024, 3, 10), 23), ("autumn", date(2024, 11, 3), 25)])
def test_published_clock_change_observations(kind, day, count):
    raw = [(day, hour, value) for hour, value in FX[kind]]
    parsed = bam.parse_pool_price_csv(csv_source(raw).decode(), price_bounds=None)
    checked = bam.check_hours(parsed, day, day)
    assert len(checked) == count
    assert list(bam.expected_labels(day)) == [hour for hour, _ in FX[kind]]
    if kind == "spring":
        assert round(math.fsum(checked.values()) / count, 2) == 28.85
    else:
        assert checked[(day, "02")] == 37.35 and checked[(day, "02*")] == 21.47


def test_monthly_arithmetic_statement_is_not_rolling_or_weighted():
    content = FX["summary_excerpt"].encode()
    assert bam.parse_summary(content, "2024-03") == 63.13
    for corrupt in (content.replace(b"March 2024", b"March 2023"),
                    content.replace(b"average pool price", b"weighted average pool price"),
                    content.replace(b"/MWh", b"/kWh")):
        with pytest.raises(bam.MarketDataError):
            bam.parse_summary(corrupt, "2024-03")


@pytest.mark.parametrize("problem", ["duplicate", "missing", "extra", "pending", "nonfinite", "precision"])
def test_bad_hours_fail_closed(problem):
    day = date(2024, 3, 10)
    rows = [(day, hour, value) for hour, value in FX["spring"]]
    if problem == "duplicate":
        rows.append(rows[0])
    elif problem == "missing":
        rows.pop()
    elif problem == "extra":
        rows.append((day, "02", 1.0))
    elif problem == "pending":
        rows[-1] = (day, "24", "-")
    elif problem == "nonfinite":
        rows[-1] = (day, "24", float("nan"))
    else:
        rows[-1] = (day, "24", 1.234)
    with pytest.raises((bam.MarketDataError, bam.AESOVerificationError)):
        parsed = bam.parse_pool_price_csv(csv_source(rows).decode(), price_bounds=None)
        bam.check_hours(parsed, day, day)


def synthetic_hours(first, last, price=50):
    rows = []
    day = first
    while day <= last:
        spring = 8 + (6 - date(day.year, 3, 8).weekday()) % 7
        autumn = 1 + (6 - date(day.year, 11, 1).weekday()) % 7
        for hour in range(1, 25):
            if not (day.month == 3 and day.day == spring and hour == 2):
                rows.append((day, f"{hour:02d}", price))
            if day.month == 11 and day.day == autumn and hour == 2:
                rows.append((day, "02*", price))
        day += timedelta(days=1)
    return rows


class FakeSource:
    def __init__(self, price=50):
        self.price = price
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        if url == bam.METADATA_URL:
            return b"fixture PDF"
        if "HistoricalPoolPriceReportServlet?" in url:
            query = parse_qs(urlparse(url).query)
            first, last = (datetime.strptime(query[key][0], "%m%d%Y").date() for key in ("beginDate", "endDate"))
            last -= timedelta(days=1)
            assert 0 <= (last - first).days < 366
            return csv_source(synthetic_hours(first, last, self.price))
        day = datetime.strptime(url.rsplit("PMS_", 1)[1][:8], "%m%d%Y").date()
        if day >= date(2026, 10, 1):
            raise bam.SourceMissing("fixture not published")
        return (f"<h1>Pool Monthly Summary for {day:%B %Y}</h1>"
                f"The average pool price for the month of {day:%B} was ${self.price:.2f}/MWh.").encode()


@pytest.fixture
def metadata(monkeypatch):
    monkeypatch.setattr(bam, "metadata_document", lambda _: (
        "366 days; user-specified period; settlement price of one megawatt-hour of electric energy; "
        "time weighted average of the one-minute system marginal price; $ CAD", "D:20250528113723"))


@pytest.fixture(scope="module")
def built():
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(bam, "metadata_document", lambda _: (
            "366 days; user-specified period; settlement price of one megawatt-hour of electric energy; "
            "time weighted average of the one-minute system marginal price; $ CAD", "D:20250528113723"))
        source = FakeSource()
        doc, hours, months = bam.build(source, date(2026, 11, 2), {})
        return doc, hours, months, source


def test_exact_sixty_month_contract_and_no_ga(built):
    doc, hours, monthly, source = built
    assert doc["metadata"]["window"] == {"start_month": "2021-10", "end_month": "2026-09", "months": 60}
    assert len(doc["monthly"]) == 60 and len(doc["hourly_surface"]) == 576
    assert all(row["total_arithmetic"] == 0.05 for row in monthly)
    assert "ga_class_b" not in json.dumps(doc)
    assert sum(row["hours_count"] for row in doc["hourly_surface"]) == len(hours)
    assert doc["metadata"]["coverage"]["observed_hours"] == len(hours)
    assert doc["metadata"]["incomplete_months"][0]["month"] == "2026-10"
    assert len([url for url in source.urls if "HistoricalPoolPriceReportServlet?" in url]) == 6
    from scrapers.utils.market_pricing import historical_market_price
    assert historical_market_price(doc, province="AB", as_of="2026-11-02")["price_per_kwh"] == 0.05


def test_archive_round_trip_and_byte_identical_noop(built, tmp_path):
    doc, hours, monthly, _ = built
    output, hourly, month_csv = (tmp_path / name for name in ("market.json", "hourly.csv", "monthly.csv"))
    first = bam.output_bytes(doc, hours, monthly, output, hourly, month_csv)
    bam.write_outputs(first)
    assert bam.read_archive(hourly) == hours
    later = copy.deepcopy(doc)
    later["metadata"]["generated_at"] = "2026-11-03T00:00:00+00:00"
    later["metadata"]["as_of"] = "2026-11-03"
    assert bam.output_bytes(later, hours, monthly, output, hourly, month_csv) == first
    assert not list(tmp_path.glob("tmp*"))
    monthly_changed = copy.deepcopy(monthly)
    monthly_changed[0]["energy_arithmetic"] += 0.01
    with pytest.raises(bam.MarketDataError, match="archived month changed"):
        bam.output_bytes(doc, hours, monthly_changed, output, hourly, month_csv)
    assert {path: path.read_bytes() for path in first} == first


def test_revised_hour_and_ignored_date_parameters_fail_closed(metadata):
    previous = {(date(2021, 10, 1), "01"): 51.0}
    with pytest.raises(bam.MarketDataError, match="observation changed"):
        bam.build(FakeSource(), date(2026, 11, 2), previous)
    wrong_range = synthetic_hours(date(2026, 9, 1), date(2026, 9, 1))
    with pytest.raises(bam.MarketDataError, match="unexpected"):
        bam.check_hours(wrong_range, date(2024, 1, 1), date(2024, 12, 31))


def test_independent_monthly_mismatch(metadata):
    class WrongAverage(FakeSource):
        def get(self, url):
            result = super().get(url)
            return result.replace(b"$50.00/MWh", b"$51.00/MWh") if "PMS_" in url else result
    with pytest.raises(bam.MarketDataError, match="hourly mean"):
        bam.build(WrongAverage(), date(2026, 11, 2), {})


def test_current_caps_are_not_silently_applied_to_history():
    text = csv_source([(date(2024, 1, 1), "01", 1001.0)]).decode()
    with pytest.raises(bam.AESOVerificationError):
        bam.parse_pool_price_csv(text)
    assert bam.parse_pool_price_csv(text, price_bounds=None)[0][2] == 1001.0


def test_older_workbook_link_uses_published_content_edition():
    class Workbook:
        def get(self, url):
            if url == bam.summary_url("2023-02"):
                return FX["february_2023_wrapper"].encode()
            assert url.endswith("PMS_01022023_files/sheet001.html")
            return b"Pool Monthly Summary for February 2023. The average pool price for the month of February was $75.00/MWh."
    assert bam.load_summary(Workbook(), "2023-02") == 75


def test_cli_dry_run_and_failure_preserve_outputs(built, tmp_path, monkeypatch, capsys):
    output, hourly, monthly = (tmp_path / name for name in ("market.json", "hourly.csv", "monthly.csv"))
    args = ["--output", str(output), "--hourly-csv", str(hourly), "--monthly-csv", str(monthly)]
    monkeypatch.setattr(bam, "build", lambda *args: built[:3])
    assert bam.main(args + ["--dry-run"]) == 0
    assert not list(tmp_path.iterdir())
    assert bam.main(args) == 0
    before = {path: path.read_bytes() for path in (output, hourly, monthly)}

    def failed(*args):
        raise bam.MarketDataError("independent average mismatch")
    monkeypatch.setattr(bam, "build", failed)
    assert bam.main(args) == 1
    assert "not published: independent average mismatch" in capsys.readouterr().err
    assert {path: path.read_bytes() for path in before} == before
