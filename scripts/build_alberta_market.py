"""Observed AESO pool history; no tariff values, customer load shapes or Ontario GA.

The hourly ETS report is checked against each official Pool Monthly Summary.
Only complete, fully observed months enter the rolling 60-month view. Historical
corrections require review: no unverified AESO revision deadline is assumed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
from calendar import monthrange
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from dateutil import tz

from scrapers.utilities.aeso import (
    AESOVerificationError, METADATA_URL, metadata_document, parse_metadata,
    parse_pool_price_csv, report_csv_url,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "site" / "data" / "market_pricing_alberta.json"
DEFAULT_HOURLY = ROOT / "data" / "market" / "alberta_pool_hourly.csv"
DEFAULT_MONTHLY = ROOT / "data" / "market" / "alberta_market_monthly.csv"
SUMMARY_BASE = "http://ets.aeso.ca/Market/Reports/Manual/PoolMonthlySummary/"
METHOD = "observed_rolling_60m_aeso_pool"
WINDOW_MONTHS = 60
TOLERANCE = 0.01  # Official monthly summaries publish cents per MWh.
FIELDS = ("date", "hour_ending", "pool_price")
MONTHLY_FIELDS = ("month", "energy_arithmetic", "total_arithmetic", "observed_hours", "source_url")
ZONE = tz.gettz("America/Edmonton")
TIME_BASIS = (
    "AESO published Alberta hour-ending labels (1-24), not UTC or Ontario EST. "
    "Spring omits HE02; autumn repeats HE02 as HE02*. Both autumn observations "
    "enter the HE02 bin. Bins store hour=HE-1 only as an index, not an hour-beginning timestamp."
)
REVISION_POLICY = (
    "All archived months are re-downloaded and cross-checked on each run. "
    "An already archived hourly price or monthly value that changes stops publication "
    "for review; no AESO correction deadline is assumed. History is never shortened."
)


class MarketDataError(ValueError):
    """Missing or inconsistent official evidence; retain the last good outputs."""


class SourceMissing(MarketDataError):
    """The official server returned HTTP 404, not a transient request failure."""


class Source:
    """Date-scoped, query-safe cache; each URL is fetched at most once per build."""

    def __init__(self, cache: Path | None = None):
        self.cache = cache
        self.day = datetime.now(timezone.utc).date().isoformat()

    def get(self, url: str) -> bytes:
        path = self.cache / self.day / hashlib.sha256(url.encode()).hexdigest() if self.cache else None
        if path is not None and path.is_file():
            return path.read_bytes()
        try:
            response = requests.get(url, timeout=(15, 120), headers={"User-Agent": "CanadaUtilityRates/1.0"})
            if response.status_code == 404:
                raise SourceMissing(f"official report not published (HTTP 404): {url}")
            response.raise_for_status()
        except requests.RequestException as exc:
            raise MarketDataError(f"could not download {url}: {exc}") from exc
        if not response.content:
            raise MarketDataError(f"official report is empty: {url}")
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(response.content)
        return response.content


def shift_month(key: str, offset: int) -> str:
    day = date.fromisoformat(key + "-01")
    index = day.year * 12 + day.month - 1 + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def month_keys(first: str, last: str) -> list[str]:
    result = []
    while first <= last:
        result.append(first)
        first = shift_month(first, 1)
    return result


def summary_url(month: str) -> str:
    day = date.fromisoformat(month + "-01")
    return f"{SUMMARY_BASE}PMS_{day:%m%d%Y}.html"


def load_summary(source: Source, month: str) -> float:
    url = summary_url(month)
    content = source.get(url)
    frames = BeautifulSoup(content, "html.parser").select('frame[name="frSheet"]')
    if frames:
        target = urljoin(url, frames[0].get("src", ""))
        if len(frames) != 1 or not re.fullmatch(re.escape(SUMMARY_BASE) + r"PMS_\d{8}_files/sheet001\.html", target):
            raise MarketDataError(f"{month}: unexpected monthly summary sheet link")
        # Older summaries are Excel HTML framesets; recent summaries have one page.
        content = source.get(target)
    return parse_summary(content, month)


def parse_summary(content: bytes, month: str) -> float:
    text = " ".join(BeautifulSoup(content, "html.parser").get_text(" ", strip=True).split())
    day = date.fromisoformat(month + "-01")
    label = day.strftime("%B %Y")
    if f"Pool Monthly Summary for {label}" not in text:
        raise MarketDataError(f"{month}: wrong monthly summary edition")
    pattern = (rf"The average pool price for the month of {day:%B} was "
               r"\$(-?[\d,]+\.\d{2})/MWh\.")
    matches = re.findall(pattern, text)
    if len(matches) != 1:
        raise MarketDataError(f"{month}: missing or ambiguous arithmetic pool-price statement ($/MWh)")
    return float(matches[0].replace(",", ""))


def expected_labels(day: date) -> list[str]:
    if ZONE is None:
        raise MarketDataError("America/Edmonton timezone data is unavailable")
    labels = []
    midnight = datetime.combine(day, datetime.min.time())
    for hour in range(1, 25):
        if tz.datetime_exists(midnight + timedelta(hours=hour), ZONE):
            labels.append(f"{hour:02d}")
        if tz.datetime_ambiguous(midnight + timedelta(hours=hour - 1), ZONE):
            labels.append(f"{hour:02d}*")
    return labels


def check_hours(rows: list[tuple[date, str, float]], first: date, last: date) -> dict[tuple[date, str], float]:
    result = {}
    for day, hour, price in rows:
        key = (day, hour)
        if not first <= day <= last or key in result or not math.isfinite(price) or round(price, 2) != price:
            raise MarketDataError(f"unexpected, duplicate or invalid hourly observation: {day} HE{hour}")
        result[key] = price
    expected = set()
    day = first
    while day <= last:
        expected.update((day, hour) for hour in expected_labels(day))
        day += timedelta(days=1)
    if set(result) != expected:
        missing, extra = expected - result.keys(), result.keys() - expected
        raise MarketDataError(f"hourly coverage {first}..{last}: {len(missing)} missing, {len(extra)} unexpected; "
                              f"first missing/extra: {next(iter(sorted(missing or extra)), None)}")
    return result


def read_archive(path: Path) -> dict[tuple[date, str], float]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise MarketDataError("unexpected Alberta hourly archive columns")
        try:
            rows = [(date.fromisoformat(row["date"]), row["hour_ending"], float(row["pool_price"]))
                    for row in reader]
        except (ValueError, KeyError, TypeError) as exc:
            raise MarketDataError("invalid Alberta hourly archive row") from exc
    if not rows:
        raise MarketDataError("existing Alberta hourly archive is empty")
    first, last = min(row[0] for row in rows), max(row[0] for row in rows)
    if first.day != 1 or last.day != monthrange(last.year, last.month)[1]:
        raise MarketDataError("existing archive must contain whole months")
    return check_hours(rows, first, last)


def build(source: Source, as_of: date, previous: dict[tuple[date, str], float]) -> tuple[dict, dict, list[dict]]:
    metadata_text, document_date = metadata_document(source.get(METADATA_URL))
    parse_metadata(metadata_text, document_date)
    if "366 days" not in metadata_text or "user-specified period" not in metadata_text:
        raise MarketDataError("AESO historical report availability contract changed")
    end = shift_month(as_of.strftime("%Y-%m"), -1)
    incomplete = []
    latest = None
    for lag in range(4):
        try:
            latest = load_summary(source, end)
            break
        except SourceMissing:
            incomplete.append({"month": end, "reason": "Official Pool Monthly Summary not published (HTTP 404)."})
            end = shift_month(end, -1)
    if latest is None:
        raise MarketDataError("no published monthly summary in the latest four complete months")
    start = shift_month(end, 1 - WINDOW_MONTHS)
    first = min(day for day, _ in previous).strftime("%Y-%m") if previous else start
    last_day = date.fromisoformat(end + f"-{monthrange(int(end[:4]), int(end[5:]))[1]}")
    if first > start or any(day > last_day for day, _ in previous):
        raise MarketDataError("new market history would shorten the existing archive or the 60-month window")
    months = month_keys(first, end)

    def get_summary(month: str) -> tuple[str, float]:
        return month, latest if month == end else load_summary(source, month)

    # A small fixed pool limits load on the official server; files have independent cache keys.
    with ThreadPoolExecutor(max_workers=3) as pool:
        summaries = dict(pool.map(get_summary, months))

    periods = []
    begin = date.fromisoformat(first + "-01")
    while begin <= last_day:
        finish = min(date(begin.year, 12, 31), last_day)
        periods.append((begin, finish))
        begin = finish + timedelta(days=1)

    def get_hours(period: tuple[date, date]) -> dict:
        begin, finish = period
        content = source.get(report_csv_url(begin, finish + timedelta(days=1)))
        rows = parse_pool_price_csv(content.decode("utf-8-sig"), price_bounds=None)
        return check_hours(rows, begin, finish)

    hours = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(get_hours, periods):
            hours.update(result)
    for key, price in previous.items():
        if hours.get(key) != price:
            raise MarketDataError(f"archived AESO observation changed at {key}; review the source correction")

    by_month: dict[str, list[float]] = defaultdict(list)
    for (day, _), price in hours.items():
        by_month[day.strftime("%Y-%m")].append(price)
    monthly, differences = [], []
    for month in months:
        prices = by_month[month]
        mean = math.fsum(prices) / len(prices)
        difference = abs(mean - summaries[month])
        if difference > TOLERANCE + 1e-10:
            raise MarketDataError(f"{month}: hourly mean {mean:.6f} != official monthly {summaries[month]:.2f} $/MWh")
        differences.append(difference)
        monthly.append({"month": month, "energy_arithmetic": round(mean / 1000, 10),
                        "total_arithmetic": round(mean / 1000, 10), "observed_hours": len(prices),
                        "source_url": summary_url(month)})
    selected = [row for row in monthly if row["month"] >= start]
    bins: dict[tuple[int, str, int], list[float]] = defaultdict(list)
    for (day, hour), price in hours.items():
        if day.strftime("%Y-%m") >= start:
            bins[(day.month, "weekend" if day.weekday() >= 5 else "weekday", int(hour.rstrip("*")) - 1)].append(price)
    surface = []
    for month in range(1, 13):
        for kind in ("weekday", "weekend"):
            for hour in range(24):
                values = bins[(month, kind, hour)]
                if not values:
                    raise MarketDataError(f"no observed hours for heatmap bin {month}/{kind}/{hour}")
                mean = round(math.fsum(values) / len(values) / 1000, 10)
                surface.append({"month": month, "day_type": kind, "hour": hour, "hours_count": len(values),
                                "avg_energy_price": mean, "combined": mean})
    observed = sum(row["observed_hours"] for row in selected)
    document = {"metadata": {
        "schema_version": 2, "province": "AB", "market_operator": "AESO", "derivation_method": METHOD,
        "unit": "$/kWh (CAD)", "as_of": as_of.isoformat(), "generated_at": datetime.now(timezone.utc).isoformat(),
        "window": {"start_month": start, "end_month": end, "months": WINDOW_MONTHS},
        "time_basis": TIME_BASIS,
        "method": "Arithmetic mean of every observed pool-price hour within each month; every month counts equally "
                  "in the headline and model benchmark. Pool energy only: no retail fees, losses, delivery, taxes "
                  "or Ontario Global Adjustment. Not a customer-weighted price, bill or forecast.",
        "day_type_rule": "Saturday/Sunday are weekends; statutory holidays retain their calendar weekday.",
        "coverage": {"observed_hours": observed, "calendar_hours": observed, "unobserved_hours": 0},
        "cross_check": {"months_checked": len(monthly), "tolerance_per_mwh": TOLERANCE,
                        "max_abs_difference_per_mwh": round(max(differences), 8)},
        "revisions": REVISION_POLICY, "incomplete_months": incomplete,
        "permission": "Owner-confirmed AESO permission covers public raw hourly archives and derived charts/benchmarks; "
                      "the project has not independently inspected the grant.",
        "source_codes": {"aeso_hourly": "AESO ETS Historical Pool Price CSV ($/MWh), exact requested dates.",
                         "aeso_monthly": "AESO Pool Monthly Summary arithmetic average ($/MWh)."},
        "sources": [{"name": "AESO historical pool-price report metadata", "url": METADATA_URL},
                    *[{"name": f"AESO hourly pool price {a} to {b}",
                       "url": report_csv_url(a, b + timedelta(days=1))} for a, b in periods],
                    *[{"name": f"AESO Pool Monthly Summary {m}", "url": summary_url(m)} for m in months]],
    }, "monthly": [dict(row, sources=["aeso_hourly", "aeso_monthly"]) for row in selected],
        "hourly_surface": surface}
    return document, hours, monthly


def csv_bytes(fields: tuple[str, ...], rows: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def output_bytes(document: dict, hours: dict, monthly: list[dict], output: Path, hourly: Path, month_csv: Path) -> dict:
    if month_csv.exists():
        with month_csv.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != list(MONTHLY_FIELDS):
                raise MarketDataError("unexpected Alberta monthly history columns")
            old = list(reader)
        current = {row["month"]: row for row in monthly}
        if not old or len({row["month"] for row in old}) != len(old):
            raise MarketDataError("empty or duplicate monthly history")
        for row in old:
            new = current.get(row["month"])
            if new is None or any(str(new[field]) != row[field] for field in MONTHLY_FIELDS):
                raise MarketDataError(f"archived month changed or disappeared: {row['month']}; review required")
    raw = [{"date": day.isoformat(), "hour_ending": hour, "pool_price": f"{hours[(day, hour)]:.2f}"}
           for day, hour in sorted(hours)]
    doc = json.loads(json.dumps(document, allow_nan=False))
    if output.exists():
        old = json.loads(output.read_text(encoding="utf-8"))
        comparable = json.loads(json.dumps(doc))
        for key in ("as_of", "generated_at"):
            comparable["metadata"][key] = old.get("metadata", {}).get(key)
        if old == comparable:
            doc = old
    return {hourly: csv_bytes(FIELDS, raw), month_csv: csv_bytes(MONTHLY_FIELDS, monthly),
            output: (json.dumps(doc, ensure_ascii=True, separators=(",", ":"), allow_nan=False) + "\n").encode()}


def write_outputs(outputs: dict[Path, bytes]) -> None:
    staged = {}
    try:
        for path, content in outputs.items():
            if path.exists() and path.read_bytes() == content:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                staged[path] = Path(stream.name)
                stream.write(content)
        for path, temporary in staged.items():
            os.replace(temporary, path)
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--hourly-csv", type=Path, default=DEFAULT_HOURLY)
    parser.add_argument("--monthly-csv", type=Path, default=DEFAULT_MONTHLY)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if len({p.resolve() for p in (args.output, args.hourly_csv, args.monthly_csv)}) != 3:
            raise MarketDataError("output paths must be different")
        doc, hours, monthly = build(Source(args.cache_dir), args.as_of, read_archive(args.hourly_csv))
        outputs = output_bytes(doc, hours, monthly, args.output, args.hourly_csv, args.monthly_csv)
        if not args.dry_run:
            write_outputs(outputs)
        meta = doc["metadata"]
        print(f"{'Dry run' if args.dry_run else 'Saved'}: {meta['window']}; {len(hours):,} archived hours; "
              f"{meta['coverage']['observed_hours']:,} window hours; {len(doc['hourly_surface'])} observed bins; "
              f"cross-check {meta['cross_check']}")
        for item in meta["incomplete_months"]:
            print(f"Not complete: {item['month']}: {item['reason']}")
        return 0
    except (MarketDataError, AESOVerificationError, OSError, ValueError) as exc:
        print(f"Alberta market history not published: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
