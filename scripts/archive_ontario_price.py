"""Keep a permanent hourly archive of the Ontario Price (Ontario Electricity Market Price, OEMP).

Since May 1, 2025 the Ontario Price is the Day-Ahead Ontario Zonal Price (DA-OZP) plus the Load Forecast Deviation
Adjustment (LFDA), hourly in $/MWh. The IESO keeps its daily DA-OZP reports online for only about 90 days, so each run
adds what is new to data/market/ontario_price_hourly.csv and never deletes rows:

* DA-OZP from the highest version of each daily Day-Ahead Hourly Ontario Zonal Price report (da_ozp_source "report");
  a higher report version replaces a lower one, and a report replaces site API rows;
* LFDA value and status as published in the IESO yearly hourly LFDA reports, updated whenever the report changes.
  A blank published LFDA stays blank, and so does that hour's Ontario Price: the IESO's published May 2025 monthly
  LFDA average (0.33) leaves those hours out, whereas counting them as zero gives 0.30;
* optionally (never in the scheduled workflow), the IESO website's chart API (da_ozp_source "site_api"; not a
  published report), only for delivery days without any report file, only after it equalled the reports to the cent
  on at least 14 overlap days in three months, and only for gap months whose averages then match the published table.

Hours are IESO hour-ending 1-24 in Eastern Standard Time. The run fails closed (exit status 1, nothing written) when a
day lacks any of hours 1-24, a value is not a number with at most two decimals or is beyond +/-2,000 $/MWh, a report
title or layout is unexpected, or a month that is complete in the archive differs from the IESO's published monthly
arithmetic average DA-OZP, LFDA or Ontario Price by more than 0.01 $/MWh. Incomplete months are not checked. A run
without new data leaves the file byte-identical.

    python scripts/archive_ontario_price.py [--output PATH] [--cache-dir DIR] [--api-cache-dir DIR] [--no-site-api]
                                            [--dry-run]
"""
import argparse
import csv
import importlib.util
import io
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from urllib.parse import urlencode, urlparse

import requests
from bs4 import BeautifulSoup


def _load_generator():
    """scripts/generate_market_pricing.py, loaded once and shared (MarketDataError, ReportSource, IESO helpers)."""
    if "generate_market_pricing" in sys.modules:
        return sys.modules["generate_market_pricing"]
    path = Path(__file__).resolve().parent / "generate_market_pricing.py"
    spec = importlib.util.spec_from_file_location("generate_market_pricing", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gmp = _load_generator()
MarketDataError = gmp.MarketDataError
ReportSource = gmp.ReportSource

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "market" / "ontario_price_hourly.csv"
OEMP_START = date(2025, 5, 1)

DA_DIR = gmp.REPORTS_BASE + "DAHourlyOntarioZonalPrice/"
DA_FILE_RE = re.compile(r"(PUB_DAHourlyOntarioZonalPrice_(\d{8})(?:_v(\d+))?\.xml)")
DA_DOC_ID = "DAHourlyOntarioZonalPrice"
DA_TITLE = "Day Ahead Hourly Ontario Zonal Energy Price Report"
LFDA_DIR = gmp.REPORTS_BASE + "HourlyLFDA/"
LFDA_FILE_RE = re.compile(r"(PUB_HourlyLFDA_(\d{4})(?:_v(\d+))?\.csv)")
LFDA_HEADER = ["Date", "Hour", "Status", "LFDA Rate ($/MWh)"]
PRICES_URL = gmp.ONTARIO_PRICE_URL
TABLE_HEADER = ["Date", "DA-OZP", "LFDA", "Ontario Price (OEMP)"]
TABLE_PANES = {"AA": "arithmetic", "WA": "weighted"}
SITE_API_URL = "https://www.ieso.ca/ieso/api/heatmapWebApi/getOntarioDayAheadAndPredispatchPrices"
SITE_API_HEADERS = {"User-Agent": gmp.USER_AGENT, "Accept": "application/json", "Referer": PRICES_URL}

FIELDS = ["date", "hour_ending", "da_ozp", "lfda", "oemp", "da_ozp_source", "da_ozp_version", "lfda_status"]
REPORT, SITE_API = "report", "site_api"
HOURS = list(range(1, 25))
MEASURES = ("da_ozp", "lfda", "oemp")
MEASURE_LABELS = {"da_ozp": "DA-OZP", "lfda": "LFDA", "oemp": "OEMP"}
PRICE_RE = re.compile(r"-?\d+(?:\.\d{1,2})?")
STATUS_RE = re.compile(r"[A-Za-z][A-Za-z ]*")
PRICE_LIMIT = Decimal(2000)
CENT = Decimal("0.01")
CHECK_TOLERANCE = Decimal("0.01")
MIN_OVERLAP_DAYS = 14
MIN_OVERLAP_MONTHS = 3


@dataclass(frozen=True)
class Row:
    da_ozp: Decimal
    source: str
    version: int | None
    lfda: Decimal | None = None
    lfda_status: str = ""

    @property
    def oemp(self) -> Decimal | None:
        return None if self.lfda is None else self.da_ozp + self.lfda


Archive = dict[tuple[date, int], Row]


@dataclass
class MonthStatus:
    month: str
    hours: int
    expected: int
    sources: dict[str, int]
    pending_lfda: int
    blank_lfda: int
    averages: dict[str, Decimal | None]
    published: dict[str, Decimal] | None
    results: dict[str, str]

    @property
    def failed(self) -> list[str]:
        return [measure for measure in MEASURES if self.results[measure] == "fail"]


@dataclass
class ApiResult:
    overlap_days: list[date] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)
    qualified: bool = False
    gap_days_served: int = 0
    filled: list[str] = field(default_factory=list)
    dropped: dict[str, str] = field(default_factory=dict)
    note: str = ""


@dataclass
class Result:
    rows: Archive
    added: int
    updated: int
    downloaded: dict[date, int]
    unversioned: list[date]
    lfda_unlisted: list[int]
    months: list[MonthStatus]
    api: ApiResult | None


# -- small helpers ---------------------------------------------------------------------------------

def _price(text: str | None, label: str) -> Decimal:
    if text is None or not PRICE_RE.fullmatch(text):
        raise MarketDataError(f"{label}: expected a price with at most two decimals, found {text!r}")
    value = Decimal(text)
    if abs(value) > PRICE_LIMIT:
        raise MarketDataError(f"{label}: {text} is outside +/-{PRICE_LIMIT} $/MWh")
    return value


def _hour(text: str | None, label: str) -> int:
    if text is None or not re.fullmatch(r"\d{1,2}", text) or not 1 <= int(text) <= 24:
        raise MarketDataError(f"{label}: invalid hour {text!r}")
    return int(text)


def _check_hours(hours, label: str) -> None:
    if sorted(hours) != HOURS:
        missing = sorted(set(HOURS) - set(hours))
        raise MarketDataError(f"{label}: expected hours 1-24, found {len(hours)} (missing {missing})")


def _money(value: Decimal | None) -> str:
    if value is None:
        return ""
    return "0.00" if value == 0 else f"{value:.2f}"


def _month(day: date) -> str:
    return gmp.month_key(day.year, day.month)


def _month_days(key: str) -> list[date]:
    return gmp.month_dates(int(key[:4]), int(key[5:]))


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _months(first: date, last: date) -> list[str]:
    return sorted({_month(day) for day in _days(first.replace(day=1), last)})


def _by_month(days) -> dict[str, list[date]]:
    grouped: dict[str, list[date]] = defaultdict(list)
    for day in sorted(days):
        grouped[_month(day)].append(day)
    return grouped


def _mean(values: list[Decimal]) -> Decimal | None:
    return sum(values, Decimal(0)) / len(values) if values else None


def _rounded(value: Decimal | None) -> str:
    return "-" if value is None else str(value.quantize(CENT, rounding=ROUND_HALF_UP))


# -- archive file ----------------------------------------------------------------------------------

def _check_days(rows: Archive, label: str) -> None:
    hours: dict[date, list[int]] = defaultdict(list)
    origins: dict[date, set] = defaultdict(set)
    for (day, hour), row in rows.items():
        hours[day].append(hour)
        origins[day].add((row.source, row.version))
    for day in sorted(hours):
        if day < OEMP_START:
            raise MarketDataError(f"{label}: {day} is before the Ontario Price began on {OEMP_START}")
        _check_hours(hours[day], f"{label} {day}")
        if len(origins[day]) != 1:
            raise MarketDataError(f"{label} {day}: hours come from different DA-OZP sources or versions")


def load_archive(content: bytes, label: str) -> Archive:
    """Rows of an existing archive file; any inconsistency fails closed instead of being rewritten."""
    lines = list(csv.reader(io.StringIO(gmp._text(content, label).replace("\r\n", "\n"))))
    if not lines or lines[0] != FIELDS:
        raise MarketDataError(f"{label}: unexpected header {lines[0] if lines else None!r}; expected {FIELDS!r}")
    rows: Archive = {}
    for number, cells in enumerate(lines[1:], start=2):
        where = f"{label} line {number}"
        if len(cells) != len(FIELDS):
            raise MarketDataError(f"{where}: expected {len(FIELDS)} columns, found {len(cells)}")
        day = gmp._parse_date(cells[0], where)
        hour = _hour(cells[1], where)
        source, version_text, status = cells[5], cells[6], cells[7]
        if source == REPORT and re.fullmatch(r"[1-9]\d*", version_text):
            version = int(version_text)
        elif source == SITE_API and not version_text:
            version = None
        else:
            raise MarketDataError(f"{where}: da_ozp_source {source!r} with da_ozp_version {version_text!r}")
        lfda = _price(cells[3], f"{where} lfda") if cells[3] else None
        if (status and not STATUS_RE.fullmatch(status)) or (lfda is not None and not status):
            raise MarketDataError(f"{where}: lfda_status {status!r} does not fit lfda {cells[3]!r}")
        row = Row(_price(cells[2], f"{where} da_ozp"), source, version, lfda, status)
        if cells[4] != _money(row.oemp):
            raise MarketDataError(f"{where}: oemp {cells[4]!r} is not da_ozp + lfda")
        if (day, hour) in rows:
            raise MarketDataError(f"{where}: duplicate {day} hour {hour}")
        rows[(day, hour)] = row
    _check_days(rows, label)
    return rows


def serialize(rows: Archive) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(FIELDS)
    for day, hour in sorted(rows):
        row = rows[(day, hour)]
        writer.writerow([day.isoformat(), hour, _money(row.da_ozp), _money(row.lfda), _money(row.oemp), row.source,
                         "" if row.version is None else row.version, row.lfda_status])
    return buffer.getvalue().encode("utf-8")


def write_archive(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(content)
    os.replace(temporary, path)


def set_day(rows: Archive, day: date, prices: dict[int, Decimal], source: str, version: int | None) -> None:
    """Replace one day's DA-OZP, keeping the LFDA already archived for its hours."""
    for hour, price in prices.items():
        old = rows.get((day, hour))
        rows[(day, hour)] = Row(price, source, version, old.lfda if old else None, old.lfda_status if old else "")


# -- official reports ------------------------------------------------------------------------------

def parse_da_report(content: bytes, day: date, label: str) -> dict[int, Decimal]:
    """{hour ending 1-24: DA-OZP in $/MWh} from one daily Day-Ahead Hourly Ontario Zonal Price report."""
    root = gmp._parse_xml(content, DA_DOC_ID, label)
    title = gmp._find_text(root, "i:DocHeader/i:DocTitle")
    if title != DA_TITLE:
        raise MarketDataError(f"{label}: unexpected report title {title!r}")
    delivery = gmp._find_text(root, "i:DocBody/i:DeliveryDate")
    if delivery != day.isoformat():
        raise MarketDataError(f"{label}: delivery date {delivery!r} does not match the file name ({day})")
    prices: dict[int, Decimal] = {}
    for element in root.findall("i:DocBody/i:HourlyPriceComponents", gmp.NS):
        hour = _hour(gmp._find_text(element, "i:PricingHour"), f"{label} PricingHour")
        if hour in prices:
            raise MarketDataError(f"{label}: duplicate hour {hour}")
        prices[hour] = _price(gmp._find_text(element, "i:ZonalPrice"), f"{label} hour {hour} ZonalPrice")
    _check_hours(prices, label)
    return prices


def report_files(source: ReportSource) -> tuple[dict[date, tuple[int, str]], list[date]]:
    """Highest versioned report file per delivery day (listing and cache), and days listed only without a version."""
    listed = gmp.parse_listing(source.get(DA_DIR, immutable=False).decode("utf-8", "replace"), DA_FILE_RE)
    if not listed:
        raise MarketDataError(f"{DA_DIR}: no daily report files listed")
    files: dict[date, tuple[int, str]] = {}
    unversioned = []
    for key, (version, name) in gmp._best_versions(source.archived(DA_DIR, DA_FILE_RE), listed).items():
        try:
            day = datetime.strptime(key, "%Y%m%d").date()
        except ValueError:
            raise MarketDataError(f"{DA_DIR}: invalid delivery date in {name}") from None
        if day < OEMP_START:
            continue
        if version:
            files[day] = (version, name)
        else:
            unversioned.append(day)
    return files, sorted(unversioned)


def download_reports(source: ReportSource, files: dict[date, tuple[int, str]],
                     rows: Archive) -> dict[date, tuple[int, dict[int, Decimal]]]:
    """Only days that are new or have a higher version than the archive holds."""
    held = {day: row.version for (day, hour), row in rows.items() if hour == 1 and row.source == REPORT}
    reports = {}
    for day, (version, name) in sorted(files.items()):
        if held.get(day, 0) < version:
            reports[day] = (version, parse_da_report(source.get(DA_DIR + name, immutable=True), day, name))
    return reports


def parse_lfda_csv(text: str, year: int, label: str) -> dict[tuple[date, int], tuple[Decimal | None, str]]:
    """{(date, hour ending): (LFDA in $/MWh, or None when published blank; status)} from a yearly LFDA report."""
    lines = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    header = [cell.strip() for cell in lines[0]] if lines else []
    if header != LFDA_HEADER:
        raise MarketDataError(f"{label}: unexpected header {header!r}; expected {LFDA_HEADER!r}")
    values: dict[tuple[date, int], tuple[Decimal | None, str]] = {}
    hours: dict[date, list[int]] = defaultdict(list)
    for number, cells in enumerate(lines[1:], start=2):
        if not any(cell.strip() for cell in cells):
            continue
        where = f"{label} line {number}"
        if len(cells) != len(LFDA_HEADER):
            raise MarketDataError(f"{where}: expected {len(LFDA_HEADER)} columns, found {len(cells)}")
        day = gmp._parse_date(cells[0].strip(), where)
        if day.year != year:
            raise MarketDataError(f"{where}: date {day} is outside {year}")
        hour = _hour(cells[1].strip(), where)
        status, rate = cells[2].strip(), cells[3].strip()
        if not STATUS_RE.fullmatch(status):
            raise MarketDataError(f"{where}: unexpected status {status!r}")
        if (day, hour) in values:
            raise MarketDataError(f"{where}: duplicate {day} hour {hour}")
        values[(day, hour)] = (_price(rate, f"{where} LFDA") if rate else None, status)
        hours[day].append(hour)
    for day in sorted(hours):
        _check_hours(hours[day], f"{label} {day}")
    return values


def load_lfda(source: ReportSource, years: list[int]) -> tuple[dict, list[int]]:
    """LFDA of the given years, and the years without a yearly report in the listing (archived LFDA is kept)."""
    if not years:
        return {}, []
    listed = gmp.parse_listing(source.get(LFDA_DIR, immutable=False).decode("utf-8", "replace"), LFDA_FILE_RE)
    if not listed:
        raise MarketDataError(f"{LFDA_DIR}: no yearly LFDA reports listed")
    values: dict = {}
    unlisted = []
    for year in years:
        if str(year) not in listed:
            unlisted.append(year)
            continue
        name = listed[str(year)][1]
        # The IESO rewrites these files daily without a new version number, so they are never kept across runs.
        values.update(parse_lfda_csv(gmp._text(source.get(LFDA_DIR + name, immutable=False), name), year, name))
    return values, unlisted


def apply_lfda(rows: Archive, lfda: dict) -> None:
    for key, row in rows.items():
        if key in lfda and (row.lfda, row.lfda_status) != lfda[key]:
            rows[key] = replace(row, lfda=lfda[key][0], lfda_status=lfda[key][1])


def _table_month(text: str, label: str) -> str:
    match = re.fullmatch(r"([A-Za-z]+)\.? (\d{4})", text)
    month = gmp.MONTH_LABELS.get(match.group(1).lower()) if match else None
    if month is None:
        raise MarketDataError(f"{label}: unexpected month {text!r}")
    return gmp.month_key(int(match.group(2)), month)


def parse_market_table(html: str, label: str = "Ontario Market Prices page") -> dict[str, dict[str, dict]]:
    """{"arithmetic"|"weighted": {"YYYY-MM": {"da_ozp", "lfda", "oemp"}}} from the monthly tables (tabs AA, WA)."""
    soup = BeautifulSoup(html, "html.parser")
    tables = {}
    for pane_id, basis in TABLE_PANES.items():
        pane = soup.find(id=pane_id)
        table = pane.find("table") if pane else None
        if table is None:
            raise MarketDataError(f"{label}: monthly {basis} average table (tab {pane_id}) not found")
        header = [" ".join(th.get_text().split()) for th in table.find_all("th")]
        if header != TABLE_HEADER:
            raise MarketDataError(f"{label} {pane_id}: unexpected columns {header!r}; expected {TABLE_HEADER!r}")
        months: dict[str, dict] = {}
        for tr in table.find_all("tr"):
            cells = [" ".join(td.get_text().split()) for td in tr.find_all("td")]
            if not cells:
                continue
            if len(cells) != len(TABLE_HEADER):
                raise MarketDataError(f"{label} {pane_id}: unexpected row {cells!r}")
            key = _table_month(cells[0], f"{label} {pane_id}")
            if key in months:
                raise MarketDataError(f"{label} {pane_id}: duplicate month {key}")
            months[key] = {measure: _price(cell, f"{label} {pane_id} {key} {MEASURE_LABELS[measure]}")
                           for measure, cell in zip(MEASURES, cells[1:])}
        if not months:
            raise MarketDataError(f"{label} {pane_id}: no monthly rows")
        tables[basis] = months
    return tables


# -- monthly cross-check ---------------------------------------------------------------------------

def _verdict(average: Decimal, published: Decimal) -> str:
    return "pass" if abs(average.quantize(CENT, rounding=ROUND_HALF_UP) - published) <= CHECK_TOLERANCE else "fail"


def month_status(month: str, rows: Archive, published: dict[str, Decimal] | None) -> MonthStatus:
    """Arithmetic averages of one month against the IESO table; only complete months are checked."""
    keys = [(day, hour) for day in _month_days(month) for hour in HOURS]
    present = [rows[key] for key in keys if key in rows]
    pending = sum(not row.lfda_status for row in present)
    blank = sum(bool(row.lfda_status) and row.lfda is None for row in present)
    averages = {
        "da_ozp": _mean([row.da_ozp for row in present]),
        "lfda": _mean([row.lfda for row in present if row.lfda is not None]),
        "oemp": _mean([row.oemp for row in present if row.oemp is not None]),
    }
    if not present:
        results = dict.fromkeys(MEASURES, "not checked (no hourly DA-OZP in the archive)")
    elif len(present) < len(keys):
        results = dict.fromkeys(MEASURES, f"not checked (incomplete: {len(present)} of {len(keys)} hours)")
    elif published is None:
        results = dict.fromkeys(MEASURES, "not checked (month not in the published table)")
    else:
        results = {"da_ozp": _verdict(averages["da_ozp"], published["da_ozp"])}
        if pending:
            results["lfda"] = results["oemp"] = f"not checked (LFDA not yet published for {pending} hours)"
        else:
            results["lfda"] = ("not checked (no published LFDA value)" if averages["lfda"] is None
                               else _verdict(averages["lfda"], published["lfda"]))
            results["oemp"] = (f"not checked ({blank} hours with a blank published LFDA)" if blank
                               else _verdict(averages["oemp"], published["oemp"]))
    return MonthStatus(month, len(present), len(keys), dict(Counter(row.source for row in present)), pending, blank,
                       averages, published, results)


def month_statuses(rows: Archive, published: dict[str, dict]) -> list[MonthStatus]:
    ends = [day for day, _ in rows] + [date.fromisoformat(key + "-01") for key in published]
    return [month_status(key, rows, published.get(key)) for key in _months(OEMP_START, max(ends, default=OEMP_START))]


# -- IESO website chart API (optional gap fill) ----------------------------------------------------

class SiteApiSource(ReportSource):
    """ReportSource for the IESO website's chart API: one cached JSON body per request and run date."""

    def _cache_path(self, url: str, immutable: bool) -> Path | None:
        if self.cache_dir is None:
            return None
        query = re.sub(r"[^0-9A-Za-z-]+", "_", urlparse(url).query)
        return self.cache_dir / self.run_date.isoformat() / f"DayAheadAndPredispatch_{query}.json"


def api_get(url: str) -> bytes:
    """Like generate_market_pricing.http_get, but a 404 (no data for those dates) is an empty body."""
    error = "not attempted"
    for attempt in range(gmp.HTTP_ATTEMPTS):
        if attempt:
            time.sleep(gmp.RETRY_DELAY_SECONDS)
        try:
            response = requests.get(url, headers=SITE_API_HEADERS, timeout=gmp.HTTP_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            error = type(exc).__name__
            continue
        if response.status_code == 404:
            return b""
        if response.status_code == 200:
            return response.content
        error = f"HTTP {response.status_code}"
        if response.status_code < 500:
            break
    raise MarketDataError(f"could not download {url}: {error}")


def site_api_url(start: date, end: date) -> str:
    return f"{SITE_API_URL}?{urlencode({'startDate': start.isoformat(), 'endDate': end.isoformat()})}"


def parse_site_api(content: bytes, start: date, end: date, label: str) -> dict[date, dict[int, Decimal]]:
    """{delivery date: {hour ending: day-ahead Ontario zonal price}} for start..end; an empty body means none."""
    if not content.strip():
        return {}
    try:
        data = json.loads(content)
    except ValueError:
        raise MarketDataError(f"{label}: not JSON") from None
    entries = data.get("DayAhead") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise MarketDataError(f"{label}: no DayAhead list")
    days: dict[date, dict[int, Decimal]] = defaultdict(dict)
    for entry in entries:
        if not isinstance(entry, dict):
            raise MarketDataError(f"{label}: unexpected DayAhead entry {entry!r}")
        day = gmp._parse_date(str(entry.get("ReportForDate", ""))[:10], f"{label} ReportForDate")
        hour, price = entry.get("Hour"), entry.get("Price")
        if type(hour) is not int or not 1 <= hour <= 24:
            raise MarketDataError(f"{label}: invalid hour {hour!r} on {day}")
        if type(price) not in (int, float):
            raise MarketDataError(f"{label}: {day} hour {hour} price {price!r} is not a number")
        if start <= day <= end:
            if hour in days[day]:
                raise MarketDataError(f"{label}: duplicate {day} hour {hour}")
            days[day][hour] = _price(repr(float(price)), f"{label} {day} hour {hour}")
    return dict(days)


def fetch_site_api(api: ReportSource, days: list[date]) -> dict[date, dict[int, Decimal]]:
    """Day-ahead prices served for the given days, one request per calendar month (its first to last day asked)."""
    served: dict[date, dict[int, Decimal]] = {}
    for month_days in _by_month(days).values():
        url = site_api_url(month_days[0], month_days[-1])
        served.update(parse_site_api(api.get(url, immutable=False), month_days[0], month_days[-1], url))
    return served


def site_api_candidates(api: ReportSource, rows: Archive) -> tuple[ApiResult, dict[date, dict[int, Decimal]]]:
    """(a) The API must equal the reports to the cent on enough overlap days; then the complete days it serves for
    delivery days without any archived DA-OZP become candidates. Any doubt about the API leaves it unused."""
    result = ApiResult()
    reports = sorted({day for (day, hour), row in rows.items() if hour == 1 and row.source == REPORT})
    if not reports:
        result.note = "not used: no report days to compare with"
        return result, {}
    gaps = [day for day in _days(OEMP_START, reports[-1]) if (day, 1) not in rows]
    if not gaps:
        result.note = "not needed: every delivery day up to the latest report is archived"
        return result, {}
    try:
        served = fetch_site_api(api, reports)
        result.overlap_days = [day for day in reports if sorted(served.get(day, {})) == HOURS]
        result.mismatches = [f"{day} hour {hour}: site API {served[day][hour]} vs report {rows[(day, hour)].da_ozp}"
                             for day in result.overlap_days for hour in HOURS
                             if served[day][hour] != rows[(day, hour)].da_ozp]
        months = {_month(day) for day in result.overlap_days}
        result.qualified = (not result.mismatches and len(result.overlap_days) >= MIN_OVERLAP_DAYS
                            and len(months) >= MIN_OVERLAP_MONTHS)
        if not result.qualified:
            result.note = (f"not used: {len(result.overlap_days)} complete overlap days in {len(months)} month(s), "
                           f"{len(result.mismatches)} hours differing from the reports (needs at least "
                           f"{MIN_OVERLAP_DAYS} days in {MIN_OVERLAP_MONTHS} months, every hour equal to the cent)")
            return result, {}
        served = fetch_site_api(api, gaps)
    except MarketDataError as exc:
        result.qualified = False
        result.note = f"not used: {exc}"
        return result, {}
    candidates = {day: served[day] for day in gaps if sorted(served.get(day, {})) == HOURS}
    result.gap_days_served = len(candidates)
    result.note = f"qualified; served {len(candidates)} of {len(gaps)} days without a report"
    return result, candidates


def verify_gap_months(candidates: dict[date, dict[int, Decimal]], rows: Archive, lfda: dict,
                      published: dict[str, dict], result: ApiResult) -> dict[date, dict[int, Decimal]]:
    """(b) Keep a gap month's API days only when the month, with any report days, matches the published table."""
    accepted: dict[date, dict[int, Decimal]] = {}
    for key, days in _by_month(candidates).items():
        month_keys = {(day, hour) for day in _month_days(key) for hour in HOURS}
        trial = {item: row for item, row in rows.items() if item in month_keys}
        for day in days:
            set_day(trial, day, candidates[day], SITE_API, None)
        apply_lfda(trial, lfda)
        status = month_status(key, trial, published.get(key))
        if all(status.results[measure] == "pass" for measure in MEASURES):
            accepted.update({day: candidates[day] for day in days})
            result.filled.append(key)
        else:
            result.dropped[key] = "; ".join(f"{MEASURE_LABELS[m]} {status.results[m]}" for m in MEASURES)
    return accepted


# -- run -------------------------------------------------------------------------------------------

def update_archive(source: ReportSource, existing: Archive, api: ReportSource | None = None) -> Result:
    """Merge new report files, LFDA and (optionally) verified site API days; raise MarketDataError on any doubt."""
    rows = dict(existing)
    files, unversioned = report_files(source)
    reports = download_reports(source, files, rows)
    for day, (version, prices) in reports.items():
        set_day(rows, day, prices, REPORT, version)
    table = parse_market_table(gmp._text(source.get(PRICES_URL, immutable=False), "Ontario Market Prices page"))
    api_result, candidates = site_api_candidates(api, rows) if api is not None else (None, {})
    lfda, unlisted = load_lfda(source, sorted({day.year for day, _ in rows} | {day.year for day in candidates}))
    if candidates:
        for day, prices in verify_gap_months(candidates, rows, lfda, table["arithmetic"], api_result).items():
            set_day(rows, day, prices, SITE_API, None)
    apply_lfda(rows, lfda)
    _check_days(rows, "archive")
    months = month_statuses(rows, table["arithmetic"])
    failures = [f"{status.month} {MEASURE_LABELS[measure]} computed {status.averages[measure]:.4f} vs published "
                f"{status.published[measure]}" for status in months for measure in status.failed]
    if failures:
        raise MarketDataError(f"monthly check against {PRICES_URL} (arithmetic averages, tolerance {CHECK_TOLERANCE} "
                              "$/MWh) failed: " + "; ".join(failures))
    return Result(
        rows=rows,
        added=sum(key not in existing for key in rows),
        updated=sum(key in existing and existing[key] != row for key, row in rows.items()),
        downloaded={day: version for day, (version, _) in reports.items()},
        unversioned=unversioned,
        lfda_unlisted=unlisted,
        months=months,
        api=api_result,
    )


def describe_month(status: MonthStatus) -> str:
    sources = ", ".join(f"{name} {count}" for name, count in sorted(status.sources.items())) or "no rows"
    text = f"{status.month} {status.hours:>4}/{status.expected} h ({sources})"
    if len(set(status.results.values())) == 1 and status.results["da_ozp"].startswith("not checked"):
        return f"{text}: {status.results['da_ozp']}"
    published = status.published or {}
    return f"{text}: " + "; ".join(
        f"{MEASURE_LABELS[m]} {_rounded(status.averages[m])} vs {published.get(m, '-')} {status.results[m]}"
        for m in MEASURES)


def summary_lines(result: Result, downloads: int, api_downloads: int | None) -> list[str]:
    days = sorted({day for day, _ in result.rows})
    span = f" ({days[0]}..{days[-1]}, {len(days)} days)" if days else ""
    pending = sum(not row.lfda_status for row in result.rows.values())
    blank = sum(bool(row.lfda_status) and row.lfda is None for row in result.rows.values())
    lines = [
        f"Ontario Price archive: {len(result.rows)} rows{span}; {result.added} added, {result.updated} updated",
        f"Report files read: {len(result.downloaded)}"
        + (f" ({gmp._ranges(result.downloaded)})" if result.downloaded else "") + f"; {downloads} downloads",
        f"LFDA: {pending} hours not yet published; {blank} hours published blank (kept blank)",
    ]
    if result.unversioned:
        lines.append(f"Listed only without a version (skipped until versioned): {gmp._ranges(result.unversioned)}")
    if result.lfda_unlisted:
        lines.append(f"No yearly LFDA report listed for {result.lfda_unlisted}; archived LFDA kept")
    if result.api is None:
        lines.append("Site API: off")
    else:
        api = result.api
        overlap = f"{api.overlap_days[0]}..{api.overlap_days[-1]}" if api.overlap_days else "none"
        lines.append(f"Site API ({api_downloads} downloads): {api.note}; overlap {len(api.overlap_days)} days "
                     f"({overlap}), {len(api.mismatches)} differing hours")
        lines += [f"  filled {key}" for key in api.filled]
        lines += [f"  dropped {key}: {reason}" for key, reason in api.dropped.items()]
    empty = [status.month for status in result.months if not status.hours]
    if empty:
        lines.append(f"Months without hourly DA-OZP (not checked): {len(empty)} ({', '.join(empty)})")
    lines.append("Monthly arithmetic averages vs the IESO table ($/MWh):")
    lines += [f"  {describe_month(status)}" for status in result.months if status.hours]
    return lines


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Add new official IESO hourly Ontario Price data to the archive.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="archive CSV (default: data/market/ontario_price_hourly.csv)")
    parser.add_argument("--cache-dir", type=Path, default=None,
                        help="optional cache of IESO files (versioned reports are kept forever)")
    parser.add_argument("--api-cache-dir", type=Path, default=None,
                        help="optional cache of raw site API responses (one folder per run date)")
    parser.add_argument("--no-site-api", action="store_true",
                        help="never call the IESO website's chart API (official reports only)")
    parser.add_argument("--dry-run", action="store_true", help="check everything but write nothing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, *, fetch=None, api_fetch=None, run_date: date | None = None) -> int:
    args = parse_args(argv)
    today = run_date or datetime.now(timezone.utc).date()
    source = ReportSource(args.cache_dir, today, fetch=fetch or gmp.http_get)
    api = None if args.no_site_api else SiteApiSource(args.api_cache_dir, today, fetch=api_fetch or api_get)
    previous = args.output.read_bytes() if args.output.is_file() else None
    try:
        existing = load_archive(previous, str(args.output)) if previous is not None else {}
        result = update_archive(source, existing, api)
    except MarketDataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(f"Nothing written; {args.output} is unchanged ({source.downloads} downloads).", file=sys.stderr)
        return 1
    content = serialize(result.rows)
    unchanged = previous is not None and content == previous.replace(b"\r\n", b"\n")
    for line in summary_lines(result, source.downloads, None if api is None else api.downloads):
        print(line)
    if args.dry_run:
        print(f"Dry run: nothing written ({args.output} {'unchanged' if unchanged else 'would change'}).")
    elif unchanged:
        print(f"{args.output} is unchanged.")
    else:
        write_archive(args.output, content)
        print(f"Wrote {len(result.rows)} rows to {args.output}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
