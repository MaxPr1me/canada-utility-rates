"""Build the rolling 5-year Ontario market history for the Market Pricing page from official IESO data.

Energy is the legacy Hourly Ontario Energy Price (HOEP) until it retired on April 30, 2025, then the Ontario Price
(Ontario Electricity Market Price, OEMP = DA-OZP + LFDA) from May 1, 2025; the Global Adjustment (GA) is the actual
monthly Class B rate, so energy + GA is what a market-billed Class B customer paid per kWh for energy. Outputs:

* data/market/hoep_hourly.csv: legacy hourly HOEP from 2020-01-01 to April 30, 2025 ($/MWh as published, hour-ending
  1-24 EST), imported once with --refresh-hoep; every month's mean must match the IESO HOEP Monthly Averages report;
* data/market/ontario_market_monthly.csv: permanent monthly history since 2020-01, never trimmed; a month that changes
  is accepted (and reported) only if it ended within 6 months of the as-of date;
* site/data/market_pricing_ontario.json (schema 2): the latest 60 consecutive complete months and 576 heatmap bins
  built from observed hours only (legacy HOEP hours plus archived Ontario Price hours, never modelled hours).

A month is complete when it has ended, its energy value is validated and its Class B GA actual rate is published.
The run fails closed: on any missing, malformed or inconsistent input it prints the reason, writes nothing and exits
with status 1. A run without new data leaves every file byte-identical.

    python scripts/build_ontario_market.py [--output PATH] [--monthly-csv PATH] [--hoep-csv PATH] [--archive PATH]
                                           [--cache-dir DIR] [--as-of YYYY-MM-DD] [--dry-run] [--refresh-hoep]
"""
import argparse
import copy
import csv
import importlib.util
import io
import json
import os
import re
import sys
from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path


def _load(name: str):
    """A sibling script loaded once and shared, like archive_ontario_price.py loads the generator."""
    if name in sys.modules:
        return sys.modules[name]
    path = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


gmp = _load("generate_market_pricing")
arc = _load("archive_ontario_price")
MarketDataError = gmp.MarketDataError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "site" / "data" / "market_pricing_ontario.json"
DEFAULT_MONTHLY = PROJECT_ROOT / "data" / "market" / "ontario_market_monthly.csv"
DEFAULT_HOEP = PROJECT_ROOT / "data" / "market" / "hoep_hourly.csv"
DEFAULT_ARCHIVE = arc.DEFAULT_OUTPUT

WINDOW_MONTHS = 60
FIRST_MONTH = "2020-01"
HOEP_LAST_DAY = gmp.HOEP_RETIRED_ON
LAST_HOEP_MONTH = "2025-04"
FIRST_OEMP_MONTH = "2025-05"
CHANGE_DATE = arc.OEMP_START
REVISION_MONTHS = 6
SCHEMA_VERSION = 2
DERIVATION_METHOD = "observed_rolling_60m_hoep_oemp_ga"

GA_DIR = gmp.REPORTS_BASE + "GlobalAdjustment/"
GA_FILE_RE = re.compile(r"(PUB_GlobalAdjustment_(\d{6})(?:_v(\d+))?\.xml)")
GA_DOC_ID = "GlobalAdjustment"
GA_TITLE = "IESO Global Adjustment Class B Rates"
GA_RATE_FIELDS = ("FirstEstimateRate", "SecondEstimateRate", "ActualRate")

CENT = Decimal("0.01")
MICRO = Decimal("0.000001")
THOUSAND = Decimal(1000)
HOEP_TOLERANCE = Decimal(str(gmp.HOEP_AVERAGE_TOLERANCE_PER_MWH))
OEMP_TOLERANCE = arc.CHECK_TOLERANCE
TABLE_SUM_TOLERANCE = Decimal("0.01")
GA_OVERLAP_TOLERANCE = Decimal("0.005")
GA_LIMIT = Decimal(str(gmp.GA_LIMIT_PER_MWH))

HOEP_FIELDS = ["date", "hour_ending", "hoep"]
MONTHLY_FIELDS = ["month", "era", "energy_arithmetic", "energy_weighted", "ga_class_b", "total_arithmetic",
                  "energy_source", "ga_source", "observed_hours"]
BIN_FIELDS = (*gmp.BIN_FIELDS, "hours_hoep", "hours_oemp")
ERAS = ("hoep", "oemp")
HOEP_HOURLY, HOEP_REPORT, OEMP_TABLE = "hoep_hourly", "hoep_monthly_report", "oemp_monthly_table"
GA_WORKBOOK, GA_REPORT = "ga_workbook", "ga_monthly_report"
ENERGY_SOURCES = {"hoep": (HOEP_HOURLY, HOEP_REPORT), "oemp": (OEMP_TABLE,)}
GA_SOURCES = (GA_WORKBOOK, GA_REPORT)

SOURCE_CODES = {
    HOEP_HOURLY: "Arithmetic: mean of every hourly legacy HOEP value (data/market/hoep_hourly.csv, imported from the "
                 "IESO yearly hourly HOEP reports), checked against the IESO HOEP Monthly Averages report; weighted: "
                 "that report's demand-weighted average.",
    HOEP_REPORT: "Arithmetic and demand-weighted averages from the IESO HOEP Monthly Averages report (legacy market; "
                 "no hourly values archived for the month).",
    OEMP_TABLE: "IESO Ontario Market Prices monthly table: Ontario Price (OEMP) arithmetic (tab AA) and weighted (tab WA) "
                "averages.",
    GA_WORKBOOK: "IESO Data Directory Global Adjustment workbook, Class B 'Actual Rate ($/MWh)'.",
    GA_REPORT: "IESO Global Adjustment monthly report (PUB_GlobalAdjustment_YYYYMM), Class B ActualRate ($/MWh).",
}
PRICE_NAME = "Ontario market energy price: legacy HOEP to April 2025, then the Ontario Price (OEMP)"
PRICE_BASIS = (
    "Energy is the legacy Hourly Ontario Energy Price (HOEP) until it retired on April 30, 2025, and the Ontario "
    "Electricity Market Price (OEMP, the Ontario Price = Day-Ahead Ontario Zonal Price + Load Forecast Deviation "
    "Adjustment) from May 1, 2025, published by the IESO in $/MWh and shown here in $/kWh. "
    "Monthly values: legacy HOEP months use the arithmetic mean of every hourly HOEP value (checked against the IESO "
    "HOEP Monthly Averages report) and that report's demand-weighted average; Ontario Price months use the IESO "
    "monthly Ontario Price table (arithmetic and weighted averages), checked against the project's hourly archive "
    "when the archive covers the whole month."
)
GA_BASIS = (
    "Global Adjustment Class B actual monthly rate: \"Actual Rate ($/MWh)\" in the IESO Data Directory Global "
    "Adjustment workbook (cross-checked against the IESO cents-per-kWh workbook) or, for months the workbook does not "
    "list yet, ActualRate in the IESO Global Adjustment monthly report; where both list a month they must agree within "
    "0.005 $/MWh. The rate applies to every hour of its month, so energy + GA is what a market-billed Class B customer "
    "paid per kWh for energy. Class A customers pay Global Adjustment by their peak demand factor instead."
)
HOUR_CONVENTION = (
    "hour = IESO hour ending minus 1 (hour beginning). The legacy HOEP reports and the Ontario Price reports both use "
    "hours ending 1-24 in Eastern Standard Time all year (IESO market time, no daylight-saving shift; every day has 24 "
    "hours), so hour 0 covers 00:00-01:00 EST; while daylight time is in effect, hour 0 is 01:00-02:00 on local clocks."
)
UNOBSERVED_HOEP_REASON = (
    "No validated hourly legacy HOEP values: the IESO yearly hourly HOEP report for the final, partial year does not "
    "reproduce the HOEP Monthly Averages report for this month (or no hourly report exists), so the month's hours are "
    "left out of the heatmap and its monthly values come from the HOEP Monthly Averages report."
)
COMPLETE_RULE = (
    "A month is complete when it has ended, its energy value is validated (legacy HOEP months: the hourly mean matches "
    "the IESO HOEP Monthly Averages report within 0.01 $/MWh; Ontario Price months: listed in the IESO monthly table, "
    "and within 0.01 $/MWh of the hourly archive when the archive covers the whole month) and its Class B Global "
    "Adjustment actual rate is published. The window is the latest 60 consecutive complete months."
)
SOURCES = [
    {"name": "Project archive of the legacy hourly HOEP (data/market/hoep_hourly.csv), imported from the IESO Yearly "
             "Hourly HOEP OR Predispatch Reports", "url": gmp.HOEP_DIR, "type": "hourly_price"},
    {"name": "IESO HOEP Monthly Averages Report (legacy)", "url": gmp.HOEP_AVERAGE_DIR, "type": "monthly_price"},
    {"name": "Project archive of the hourly Ontario Price (data/market/ontario_price_hourly.csv), from the IESO "
             "Day-Ahead Hourly Ontario Zonal Price and hourly LFDA reports", "url": arc.DA_DIR, "type": "hourly_price"},
    {"name": "IESO Ontario Market Prices: monthly Ontario Price table (arithmetic and weighted averages)",
     "url": gmp.ONTARIO_PRICE_URL, "type": "monthly_price"},
    {"name": "IESO Global Adjustment rates in $/MWh, Class B actual (Data Directory workbook)", "url": gmp.GA_MWH_URL,
     "type": "monthly_rate"},
    {"name": "IESO Global Adjustment monthly reports (Class B rates)", "url": GA_DIR, "type": "monthly_rate"},
    {"name": "IESO Global Adjustment rates in cents per kWh (Data Directory workbook)", "url": gmp.GA_KWH_URL,
     "type": "cross_check"},
    {"name": "IESO Hourly Ontario Energy Price (HOEP) - Historic Prices (legacy market; retirement notice)",
     "url": gmp.HOEP_PAGE_URL, "type": "reference"},
]


@dataclass(frozen=True)
class Month:
    month: str
    era: str
    energy_arithmetic: Decimal
    energy_weighted: Decimal
    ga_class_b: Decimal
    energy_source: str
    ga_source: str
    observed_hours: int

    @property
    def total_arithmetic(self) -> Decimal:
        return self.energy_arithmetic + self.ga_class_b


@dataclass
class Build:
    document: dict
    months: list[Month]
    window: list[str]
    hoep: dict | None
    revisions: list[dict] = field(default_factory=list)
    incomplete: dict[str, str] = field(default_factory=dict)


# -- small helpers ---------------------------------------------------------------------------------

def _ym(key: str) -> tuple[int, int]:
    return int(key[:4]), int(key[5:7])


def _shift(key: str, months: int) -> str:
    year, month = _ym(key)
    index = year * 12 + month - 1 + months
    return gmp.month_key(index // 12, index % 12 + 1)


def _span(first: str, last: str) -> list[str]:
    keys = []
    while first <= last:
        keys.append(first)
        first = _shift(first, 1)
    return keys


def _month_of(day: date) -> str:
    return gmp.month_key(day.year, day.month)


def _month_end(key: str) -> date:
    year, month = _ym(key)
    return date(year, month, monthrange(year, month)[1])


def _era(key: str) -> str:
    return ERAS[0] if key < FIRST_OEMP_MONTH else ERAS[1]


def _cents(value, label: str) -> Decimal:
    """A published number as an exact two-decimal Decimal; more decimals are refused, not rounded."""
    number = Decimal(repr(float(value))) if isinstance(value, (int, float)) else Decimal(str(value))
    if number != number.quantize(CENT):
        raise MarketDataError(f"{label}: {value!r} has more than two decimals")
    return number.quantize(CENT)


def _per_kwh(value: Decimal) -> float:
    return float((value / THOUSAND).quantize(MICRO, rounding=ROUND_HALF_UP))


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / len(values)


def _months_before(day: date, months: int) -> date:
    index = day.year * 12 + day.month - 1 - months
    year, month = index // 12, index % 12 + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def _revisable(key: str, as_of: date) -> bool:
    return _month_end(key) >= _months_before(as_of, REVISION_MONTHS)


def _limits(values: list[int]) -> dict:
    return {"min": min(values), "max": max(values)} if values else {"min": 0, "max": 0}


# -- legacy hourly HOEP ----------------------------------------------------------------------------

def _check_hoep_days(rows: dict, label: str, first_month: str) -> None:
    hours: dict[date, list[int]] = defaultdict(list)
    for day, hour in rows:
        hours[day].append(hour)
    if not hours:
        raise MarketDataError(f"{label}: no hourly legacy HOEP values")
    days = sorted(hours)
    for day in days:
        arc._check_hours(hours[day], f"{label} {day}")
    first = date.fromisoformat(first_month + "-01")
    if days[0] != first:
        raise MarketDataError(f"{label}: starts on {days[0]}, expected {first}")
    if days[-1] > HOEP_LAST_DAY:
        raise MarketDataError(f"{label}: {days[-1]} is after the HOEP retired on {HOEP_LAST_DAY}")
    if days[-1] != _month_end(_month_of(days[-1])):
        raise MarketDataError(f"{label}: ends on {days[-1]}, part way through a month")
    missing = sorted(set(arc._days(days[0], days[-1])) - set(days))
    if missing:
        raise MarketDataError(f"{label}: missing {len(missing)} day(s): {gmp._ranges(missing)}")


def load_hoep_csv(content: bytes, label: str, first_month: str) -> dict[tuple[date, int], Decimal]:
    """{(date, hour ending): legacy HOEP in $/MWh} from data/market/hoep_hourly.csv; any doubt fails closed."""
    lines = list(csv.reader(io.StringIO(gmp._text(content, label).replace("\r\n", "\n"))))
    if not lines or lines[0] != HOEP_FIELDS:
        raise MarketDataError(f"{label}: unexpected header {lines[0] if lines else None!r}; expected {HOEP_FIELDS!r}")
    rows: dict[tuple[date, int], Decimal] = {}
    for number, cells in enumerate(lines[1:], start=2):
        where = f"{label} line {number}"
        if len(cells) != len(HOEP_FIELDS):
            raise MarketDataError(f"{where}: expected {len(HOEP_FIELDS)} columns, found {len(cells)}")
        key = (gmp._parse_date(cells[0], where), arc._hour(cells[1], where))
        if key in rows:
            raise MarketDataError(f"{where}: duplicate {key[0]} hour {key[1]}")
        rows[key] = arc._price(cells[2], f"{where} hoep")
    _check_hoep_days(rows, label, first_month)
    return rows


def serialize_hoep(rows: dict) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(HOEP_FIELDS)
    for day, hour in sorted(rows):
        writer.writerow([day.isoformat(), hour, arc._money(rows[(day, hour)])])
    return buffer.getvalue().encode("utf-8")


def import_hoep(source, first_month: str) -> tuple[dict, dict, dict[int, str]]:
    """Legacy hourly HOEP and HOEP Monthly Averages from the IESO (one-time import; 2025 is a partial year)."""
    years = list(range(int(first_month[:4]), HOEP_LAST_DAY.year + 1))
    listed = gmp.parse_listing(source.get(gmp.HOEP_DIR, immutable=False).decode("utf-8", "replace"), gmp.HOEP_FILE_RE)
    files = gmp._best_versions(source.archived(gmp.HOEP_DIR, gmp.HOEP_FILE_RE), listed)
    missing = [str(year) for year in years if year < HOEP_LAST_DAY.year and str(year) not in files]
    if missing:
        raise MarketDataError(f"yearly HOEP report not available for {', '.join(missing)} at {gmp.HOEP_DIR}")
    first = date.fromisoformat(first_month + "-01")
    rows: dict[tuple[date, int], Decimal] = {}
    used: dict[int, str] = {}
    for year in years:
        if str(year) not in files:
            continue
        version, name = files[str(year)]
        prices = gmp.parse_hoep_csv(gmp._text(source.get(gmp.HOEP_DIR + name, immutable=version > 0), name), year, name)
        for day, hours in prices.items():
            if day > HOEP_LAST_DAY:
                raise MarketDataError(f"{name}: {day} is after the HOEP retired on {HOEP_LAST_DAY}")
            if day < first:
                continue
            for hour, value in hours.items():
                rows[(day, hour)] = _cents(value, f"{name} {day} hour {hour}")
        used[year] = name
    _check_hoep_days(rows, "legacy HOEP reports", first_month)
    averages: dict[str, dict] = {}
    reports = gmp._yearly_files(source, gmp.HOEP_AVERAGE_DIR, gmp.HOEP_AVERAGE_FILE_RE, years,
                                "HOEP Monthly Averages report")
    for year, (version, name) in reports.items():
        content = source.get(gmp.HOEP_AVERAGE_DIR + name, immutable=version > 0)
        averages.update(gmp.parse_hoep_averages(content, year, name))
    return rows, averages, used


def hoep_energy(rows: dict, first_month: str, averages: dict | None, stored: dict[str, Month]):
    """{month: (arithmetic, weighted, source)} for the legacy months, the check record, failures and dropped months.

    With the IESO averages (import), each hourly mean must match the report, except in the partial final year: there a
    month that does not match, and every later month, keeps the report's averages and its hours are dropped (left
    unobserved), as when no yearly file exists. Otherwise the weighted average and any report-only month come from the
    monthly history and the hourly mean is recomputed."""
    by_month: dict[str, list[Decimal]] = defaultdict(list)
    for (day, _hour), price in rows.items():
        by_month[_month_of(day)].append(price)
    energies, failures, entries, dropped, worst = {}, [], [], [], Decimal(0)
    final_year = f"{HOEP_LAST_DAY.year}-01"
    for key in _span(first_month, LAST_HOEP_MONTH):
        covered = len(by_month.get(key, ())) == _month_end(key).day * 24
        if averages is not None:
            if key not in averages:
                failures.append(f"{key} is not in the HOEP Monthly Averages report")
                continue
            published = _cents(averages[key]["arithmetic"], f"HOEP Monthly Averages {key} ArithmeticAve")
            weighted = _cents(averages[key]["weighted"], f"HOEP Monthly Averages {key} WeightedAve")
            reference = published
        else:
            previous = stored.get(key)
            if previous is None:
                failures.append(f"the monthly history lacks legacy HOEP month {key}; run once with --refresh-hoep")
                continue
            if not covered and previous.energy_source != HOEP_REPORT:
                failures.append(f"the hourly legacy HOEP archive lacks {key}")
                continue
            weighted, reference = previous.energy_weighted, previous.energy_arithmetic
        if not covered:
            energies[key] = (reference, weighted, HOEP_REPORT)
            continue
        mean = _mean(by_month[key])
        difference = mean - reference
        mismatch = averages is not None and abs(difference) > HOEP_TOLERANCE
        used = not (averages is not None and key >= final_year and (dropped or mismatch))
        entries.append({"month": key, "computed": float(round(mean, 4)), "reference": float(reference),
                        "difference": float(round(difference, 4)), "hours_used": used})
        if not used:
            dropped.append(key)
            energies[key] = (reference, weighted, HOEP_REPORT)
            continue
        worst = max(worst, abs(difference))
        if mismatch:
            failures.append(f"{key} hourly mean {mean:.4f} vs published {reference}")
        energies[key] = (mean.quantize(CENT, rounding=ROUND_HALF_UP), weighted, HOEP_HOURLY)
    check = {
        "source_url": gmp.HOEP_AVERAGE_DIR,
        "basis": ("arithmetic mean of every hourly legacy HOEP value in the month vs the IESO HOEP Monthly Averages "
                  "report's ArithmeticAve" if averages is not None else
                  "arithmetic mean of every hourly legacy HOEP value in the month vs the monthly history, which was "
                  "checked against the IESO HOEP Monthly Averages report when the legacy hours were imported"),
        "unit": "$/MWh",
        "tolerance": float(HOEP_TOLERANCE),
        "months_checked": sum(entry["hours_used"] for entry in entries),
        "max_abs_difference": float(round(worst, 4)),
        "months": entries,
    }
    return energies, check, failures, dropped


# -- Ontario Price ---------------------------------------------------------------------------------

def oemp_energy(table: dict, archive: dict):
    """{month: (arithmetic, weighted, source)} from the IESO monthly table, its checks, failures and gaps."""
    arithmetic, weighted = table["arithmetic"], table["weighted"]
    failures, incomplete, energies = [], {}, {}
    early = sorted(key for key in set(arithmetic) | set(weighted) if key < FIRST_OEMP_MONTH)
    if early:
        failures.append(f"the Ontario Price table lists months before {FIRST_OEMP_MONTH}: {', '.join(early)}")
    worst_sum = Decimal(0)
    for basis, months in table.items():
        for key, values in months.items():
            difference = values["da_ozp"] + values["lfda"] - values["oemp"]
            worst_sum = max(worst_sum, abs(difference))
            if abs(difference) > TABLE_SUM_TOLERANCE:
                failures.append(f"table {basis} {key}: DA-OZP {values['da_ozp']} + LFDA {values['lfda']} != OEMP "
                                f"{values['oemp']}")
    entries, worst = [], Decimal(0)
    for key in sorted(set(arithmetic) | set(weighted)):
        if key not in arithmetic or key not in weighted:
            incomplete[key] = "listed in only one of the IESO arithmetic and weighted tables"
            continue
        status = arc.month_status(key, archive, arithmetic[key])
        if status.results["oemp"] in ("pass", "fail"):
            difference = status.averages["oemp"] - arithmetic[key]["oemp"]
            worst = max(worst, abs(difference))
            entries.append({"month": key, "hours": status.hours, "computed": float(round(status.averages["oemp"], 4)),
                            "published": float(arithmetic[key]["oemp"]), "difference": float(round(difference, 4)),
                            "da_ozp": status.results["da_ozp"], "lfda": status.results["lfda"]})
            if status.results["oemp"] == "fail":
                failures.append(f"{key} archive OEMP {status.averages['oemp']:.4f} vs table {arithmetic[key]['oemp']}")
                continue
        energies[key] = (arithmetic[key]["oemp"], weighted[key]["oemp"], OEMP_TABLE)
    checks = {
        "oemp_archive_vs_table": {
            "source_url": gmp.ONTARIO_PRICE_URL,
            "basis": "arithmetic mean of the archived hourly Ontario Price vs the IESO monthly table (tab AA), for "
                     "months whose every hour has a published Ontario Price in the archive",
            "unit": "$/MWh",
            "tolerance": float(OEMP_TOLERANCE),
            "months_checked": len(entries),
            "max_abs_difference": float(round(worst, 4)),
            "months": entries,
        },
        "ontario_price_table_sum": {
            "source_url": gmp.ONTARIO_PRICE_URL,
            "basis": "DA-OZP + LFDA vs the Ontario Price (OEMP) in every row of both IESO monthly tables",
            "unit": "$/MWh",
            "tolerance": float(TABLE_SUM_TOLERANCE),
            "months_checked": len(arithmetic) + len(weighted),
            "max_abs_difference": float(worst_sum),
        },
    }
    return energies, checks, failures, incomplete


# -- Global Adjustment -----------------------------------------------------------------------------

def parse_ga_report(content: bytes, month: str, label: str) -> dict:
    """{"FirstEstimateRate", "SecondEstimateRate", "ActualRate"} in $/MWh (None when not yet published)."""
    root = gmp._parse_xml(content, GA_DOC_ID, label)
    title = gmp._find_text(root, "i:DocHeader/i:DocTitle")
    if title != GA_TITLE:
        raise MarketDataError(f"{label}: unexpected report title {title!r}")
    trade_month = gmp._find_text(root, "i:DocBody/i:TradeMonth")
    if trade_month != month:
        raise MarketDataError(f"{label}: TradeMonth {trade_month!r} does not match the file name ({month})")
    values = root.find("i:DocBody/i:GAValues", gmp.NS)
    if values is None:
        raise MarketDataError(f"{label}: GAValues not found")
    rates = {}
    for name in GA_RATE_FIELDS:
        text = gmp._find_text(values, f"i:{name}")
        rate = arc._price(text, f"{label} {name}") if text else None
        if rate is not None and abs(rate) > GA_LIMIT:
            raise MarketDataError(f"{label}: {name} {rate} is outside +/-{GA_LIMIT} $/MWh")
        rates[name] = rate
    return rates


def load_ga_reports(source) -> dict[str, dict]:
    """Every Global Adjustment monthly report listed (or kept in the cache), highest version per month."""
    listed = gmp.parse_listing(source.get(GA_DIR, immutable=False).decode("utf-8", "replace"), GA_FILE_RE)
    if not listed:
        raise MarketDataError(f"{GA_DIR}: no Global Adjustment monthly reports listed")
    reports = {}
    for key, (version, name) in sorted(gmp._best_versions(source.archived(GA_DIR, GA_FILE_RE), listed).items()):
        month = f"{key[:4]}-{key[4:]}"
        rates = parse_ga_report(source.get(GA_DIR + name, immutable=version > 0), month, name)
        reports[month] = dict(rates, file=name)
    return reports


def load_ga(source, first_month: str):
    """{month: (Class B actual $/MWh, source)}, the workbook sheets, the checks and failures."""
    sheets = gmp.read_workbook(source.get(gmp.GA_MWH_URL, immutable=False), "GA $/MWh workbook")
    workbook_floats = gmp.parse_ga_mwh(sheets)
    kwh = gmp.parse_ga_kwh(gmp.read_workbook(source.get(gmp.GA_KWH_URL, immutable=False), "GA cents/kWh workbook"))
    listed_months = sorted(key for key in workbook_floats if key >= first_month)
    units = gmp.check_ga_units([_ym(key) for key in listed_months], workbook_floats, kwh)
    workbook = {key: _cents(workbook_floats[key], f"GA $/MWh workbook {key}") for key in listed_months}
    reports = load_ga_reports(source)
    rates, failures, overlap, worst = {}, [], [], Decimal(0)
    for key in sorted(set(workbook) | {month for month in reports if month >= first_month}):
        actual = (reports.get(key) or {}).get("ActualRate")
        if key in workbook and actual is not None:
            difference = actual - workbook[key]
            worst = max(worst, abs(difference))
            overlap.append({"month": key, "workbook": float(workbook[key]), "monthly_report": float(actual),
                            "difference": float(difference), "file": reports[key]["file"]})
            if abs(difference) > GA_OVERLAP_TOLERANCE:
                failures.append(f"GA {key}: workbook {workbook[key]} vs monthly report {actual} "
                                f"({reports[key]['file']})")
        if key in workbook:
            rates[key] = (workbook[key], GA_WORKBOOK)
        elif actual is not None:
            rates[key] = (actual, GA_REPORT)
    estimates = {key: next((name for name in ("SecondEstimateRate", "FirstEstimateRate") if entry.get(name) is not None),
                           None) for key, entry in reports.items() if entry.get("ActualRate") is None}
    checks = {
        "ga_class_b_units": units,
        "ga_workbook_vs_monthly_reports": {
            "source_url": GA_DIR,
            "basis": "Class B actual rate in the IESO Data Directory workbook vs ActualRate in the IESO Global "
                     "Adjustment monthly report, for months listed in both",
            "unit": "$/MWh",
            "tolerance": float(GA_OVERLAP_TOLERANCE),
            "months_checked": len(overlap),
            "max_abs_difference": float(worst),
            "months": overlap,
            "reports": {key: entry["file"] for key, entry in reports.items()},
        },
    }
    return rates, sheets, workbook_floats, estimates, checks, failures


# -- monthly history -------------------------------------------------------------------------------

def load_monthly(content: bytes, label: str) -> dict[str, Month]:
    lines = list(csv.reader(io.StringIO(gmp._text(content, label).replace("\r\n", "\n"))))
    if not lines or lines[0] != MONTHLY_FIELDS:
        raise MarketDataError(f"{label}: unexpected header {lines[0] if lines else None!r}; expected {MONTHLY_FIELDS!r}")
    months: dict[str, Month] = {}
    for number, cells in enumerate(lines[1:], start=2):
        where = f"{label} line {number}"
        if len(cells) != len(MONTHLY_FIELDS):
            raise MarketDataError(f"{where}: expected {len(MONTHLY_FIELDS)} columns, found {len(cells)}")
        key, era = cells[0], cells[1]
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", key) or era != _era(key):
            raise MarketDataError(f"{where}: month {key!r} with era {era!r}")
        if key in months:
            raise MarketDataError(f"{where}: duplicate month {key}")
        values = [arc._price(cells[index], f"{where} {MONTHLY_FIELDS[index]}") for index in range(2, 6)]
        if cells[6] not in ENERGY_SOURCES[era] or cells[7] not in GA_SOURCES or not cells[8].isdigit():
            raise MarketDataError(f"{where}: unexpected sources or observed_hours {cells[6:]!r}")
        month = Month(key, era, values[0], values[1], values[2], cells[6], cells[7], int(cells[8]))
        if values[3] != month.total_arithmetic:
            raise MarketDataError(f"{where}: total_arithmetic {values[3]} is not energy_arithmetic + ga_class_b")
        months[key] = month
    return months


def serialize_monthly(months: list[Month]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(MONTHLY_FIELDS)
    for month in sorted(months, key=lambda item: item.month):
        writer.writerow([month.month, month.era, arc._money(month.energy_arithmetic), arc._money(month.energy_weighted),
                         arc._money(month.ga_class_b), arc._money(month.total_arithmetic), month.energy_source,
                         month.ga_source, month.observed_hours])
    return buffer.getvalue().encode("utf-8")


def assemble(first_month: str, last_ended: str, energies: dict, rates: dict, stored: dict[str, Month],
             observed: dict[str, int], as_of: date, estimates: dict[str, str | None]):
    """Every complete month (recomputed where the sources allow, else as stored), revisions, failures and gaps."""
    rows, revisions, failures, incomplete = {}, [], [], {}
    for key in _span(first_month, last_ended):
        previous = stored.get(key)
        energy = energies.get(key) or (previous and (previous.energy_arithmetic, previous.energy_weighted,
                                                     previous.energy_source))
        rate = rates.get(key) or (previous and (previous.ga_class_b, previous.ga_source))
        if not energy or not rate:
            reasons = []
            if not energy:
                reasons.append("energy not validated" + (" (not in the IESO monthly table)" if key >= FIRST_OEMP_MONTH
                                                         else ""))
            if not rate:
                estimate = estimates.get(key)
                reasons.append("no Class B GA actual rate published"
                               + (f" (latest: {estimate})" if estimate else ""))
            incomplete[key] = "; ".join(reasons)
            continue
        month = Month(key, _era(key), energy[0], energy[1], rate[0], energy[2], rate[1], observed.get(key, 0))
        if previous is not None:
            for name in ("energy_arithmetic", "energy_weighted", "ga_class_b"):
                old, new = getattr(previous, name), getattr(month, name)
                if old == new:
                    continue
                if _revisable(key, as_of):
                    revisions.append({"month": key, "field": name, "previous_per_mwh": float(old),
                                      "new_per_mwh": float(new)})
                else:
                    failures.append(f"{key} {name} changed from {old} to {new}, but the month ended more than "
                                    f"{REVISION_MONTHS} months before {as_of}")
        rows[key] = month
    for key, previous in stored.items():
        if key not in rows and key not in incomplete:
            rows[key] = previous
    return rows, revisions, failures, incomplete


def choose_window(rows: dict[str, Month], last_ended: str, size: int) -> list[str]:
    complete = {key for key in rows if key <= last_ended}
    for end in sorted(complete, reverse=True):
        months = _span(_shift(end, 1 - size), end)
        if all(key in complete for key in months):
            return months
    raise MarketDataError(f"no {size} consecutive complete months up to {last_ended} "
                          f"({len(complete)} complete months)")


# -- heatmap bins ----------------------------------------------------------------------------------

def build_bins(window: list[str], rows: dict[str, Month], hoep: dict, archive: dict) -> list[dict]:
    """576 bins of observed hours only: legacy HOEP hours and archived Ontario Price hours inside the window."""
    inside = set(window)
    totals: dict[tuple, list] = defaultdict(lambda: [0, 0, Decimal(0), Decimal(0)])

    def add(day: date, hour: int, price: Decimal, era: int) -> None:
        entry = totals[(day.month, gmp.day_type(day), hour - 1)]
        entry[era] += 1
        entry[2] += price
        entry[3] += rows[_month_of(day)].ga_class_b

    for (day, hour), price in hoep.items():
        if _month_of(day) in inside:
            add(day, hour, price, 0)
    for (day, hour), row in archive.items():
        if row.oemp is not None and _month_of(day) in inside:
            add(day, hour, row.oemp, 1)
    surface = []
    for month in range(1, 13):
        for kind in gmp.DAY_TYPES:
            for hour in range(24):
                hours_hoep, hours_oemp, energy, rate = totals.get((month, kind, hour), (0, 0, Decimal(0), Decimal(0)))
                count = hours_hoep + hours_oemp
                if not count:
                    raise MarketDataError(f"no observed hours for month {month} {kind} hour {hour} in the window "
                                          f"{window[0]}..{window[-1]}")
                price, adjustment = energy / count / THOUSAND, rate / count / THOUSAND
                surface.append({
                    "month": month,
                    "day_type": kind,
                    "hour": hour,
                    "hours_count": count,
                    "avg_energy_price": float(price.quantize(MICRO, rounding=ROUND_HALF_UP)),
                    "avg_ga_class_b": float(adjustment.quantize(MICRO, rounding=ROUND_HALF_UP)),
                    "combined": float((price + adjustment).quantize(MICRO, rounding=ROUND_HALF_UP)),
                    "hours_hoep": hours_hoep,
                    "hours_oemp": hours_oemp,
                })
    return surface


# -- document --------------------------------------------------------------------------------------

def _gap(archive: dict, window: list[str]) -> dict:
    first = min((day for day, _ in archive), default=None)
    if first == CHANGE_DATE:
        raise MarketDataError(f"the Ontario Price archive starts on {CHANGE_DATE}; the gap description needs review")
    end = arc._days(CHANGE_DATE, first)[-2] if first else _month_end(window[-1])
    start_text = first.isoformat() if first else "no date yet"
    return {
        "from": CHANGE_DATE.isoformat(),
        "to": end.isoformat(),
        "reason": (
            "The IESO keeps its daily Day-Ahead Ontario Zonal Price reports online for only about 90 days and the "
            f"project's hourly Ontario Price archive starts on {start_text}, so the hourly Ontario Price before then "
            "cannot be recovered. Monthly values for those months come from the IESO monthly table; the heatmap uses "
            "only observed hours and is never filled with modelled hours."
        ),
    }


def _notes(gap: dict) -> str:
    return (
        "Observed market history for comparison only: not a tariff, a bill or a forecast. "
        + gmp.HOEP_RETIREMENT_STATEMENT + " "
        "Energy is the legacy HOEP to April 2025 and the Ontario Price (OEMP = DA-OZP + LFDA) from May 2025; Global "
        "Adjustment is the Class B actual monthly rate, so energy + GA is what a market-billed Class B customer paid "
        "per kWh for energy. "
        "Class A customers pay Global Adjustment by their peak demand factor, not the Class B rate shown here. "
        "Delivery, regulatory, loss and retail contract charges are not included. "
        f"The hourly Ontario Price from {gap['from']} to {gap['to']} is not available (the IESO keeps its daily "
        "reports for about 90 days and the project's archive starts after that period), so those hours are left out "
        "of the heatmap and never modelled; monthly values for those months come from the IESO monthly table."
    )


def _heatmap_basis(gap: dict, unobserved: list[str]) -> str:
    legacy = (f" The legacy HOEP hours of {', '.join(unobserved)} are left out too, because they could not be validated "
              "against the IESO HOEP Monthly Averages report.") if unobserved else ""
    return (
        "Each bin averages the observed hourly energy prices that fall in it inside the window months: legacy HOEP "
        "hours (until the HOEP retired on April 30, 2025) and archived Ontario Price hours. Hours without an observed "
        f"price are left out, never modelled: the Ontario Price from {gap['from']} to {gap['to']} and hours whose LFDA "
        "is not yet published or was published blank." + legacy + " Global Adjustment is each hour's monthly Class B "
        "actual rate, so a bin's Global Adjustment is hour-weighted. hours_hoep and hours_oemp count the hours of each "
        "era in a bin."
    )


def describe_months(window: list[str], rows: dict[str, Month]) -> list[dict]:
    described = []
    for key in window:
        days = gmp.month_dates(*_ym(key))
        weekend = sum(gmp.day_type(day) == gmp.DAY_TYPES[1] for day in days)
        described.append({"month": key, "days": len(days), "weekday_days": len(days) - weekend,
                          "weekend_days": weekend, "hours": len(days) * 24, "observed_hours": rows[key].observed_hours})
    return described


def coverage(described: list[dict], surface: list[dict]) -> dict:
    counts = {kind: [b["hours_count"] for b in surface if b["day_type"] == kind] for kind in gmp.DAY_TYPES}
    hours = sum(b["hours_count"] for b in surface)
    calendar_hours = sum(m["hours"] for m in described)
    return {
        "days": sum(m["days"] for m in described),
        "hours": hours,
        "months": len(described),
        "weekday_days": sum(m["weekday_days"] for m in described),
        "weekend_days": sum(m["weekend_days"] for m in described),
        "calendar_hours": calendar_hours,
        "hours_hoep": sum(b["hours_hoep"] for b in surface),
        "hours_oemp": sum(b["hours_oemp"] for b in surface),
        "unobserved_hours": calendar_hours - hours,
        "hours_per_bin": {kind: _limits(values) for kind, values in counts.items()},
        "hours_hoep_per_bin": _limits([b["hours_hoep"] for b in surface]),
        "hours_oemp_per_bin": _limits([b["hours_oemp"] for b in surface]),
    }


def monthly_record(month: Month) -> dict:
    return {
        "month": month.month,
        "era": month.era,
        "energy_arithmetic": _per_kwh(month.energy_arithmetic),
        "energy_weighted": _per_kwh(month.energy_weighted),
        "ga_class_b": _per_kwh(month.ga_class_b),
        "total_arithmetic": _per_kwh(month.total_arithmetic),
        "energy_source": month.energy_source,
        "ga_source": month.ga_source,
        "observed_hours": month.observed_hours,
    }


def validate_document(document: dict, size: int) -> None:
    metadata = document.get("metadata") or {}
    required = (*gmp.REQUIRED_METADATA, "schema_version", "window", "change_date", "eras", "gap", "heatmap_basis")
    missing = [key for key in required if not metadata.get(key)]
    if missing:
        raise MarketDataError(f"output metadata missing {missing}")
    window = metadata["window"]
    monthly = document.get("monthly") or []
    keys = [entry.get("month") for entry in monthly]
    if len(monthly) != size or window["months"] != size or keys != _span(window["start_month"], window["end_month"]):
        raise MarketDataError(f"output must hold the {size} consecutive window months")
    surface = document.get("hourly_surface") or []
    expected = {(month, kind, hour) for month in range(1, 13) for kind in gmp.DAY_TYPES for hour in range(24)}
    if len(surface) != len(expected) or {(b["month"], b["day_type"], b["hour"]) for b in surface} != expected:
        raise MarketDataError("output must contain exactly one bin per month, day type and hour (576)")
    for entry in surface:
        if (set(entry) != set(BIN_FIELDS) or entry["hours_count"] < 1
                or entry["hours_count"] != entry["hours_hoep"] + entry["hours_oemp"]):
            raise MarketDataError(f"invalid bin {entry!r}")
    if sum(entry["hours_count"] for entry in surface) != metadata["coverage"]["hours"]:
        raise MarketDataError("bin hours do not add up to the window's observed hours")


def build(source, *, hoep_content: bytes | None, monthly_content: bytes | None, archive_content: bytes, as_of: date,
          refresh_hoep: bool = False, generated_at: datetime | None = None, window_months: int = WINDOW_MONTHS,
          first_month: str = FIRST_MONTH) -> Build:
    """Validate every input and assemble all outputs in memory; raise MarketDataError instead of partial data."""
    stored = load_monthly(monthly_content, "monthly history") if monthly_content is not None else {}
    archive = arc.load_archive(archive_content, "Ontario Price archive")
    if refresh_hoep:
        hoep, averages, _files = import_hoep(source, first_month)
    else:
        if hoep_content is None:
            raise MarketDataError("the hourly legacy HOEP archive is missing; run once with --refresh-hoep")
        hoep, averages = load_hoep_csv(hoep_content, "hourly legacy HOEP archive", first_month), None
    failures: list[str] = []
    energies, hoep_check, problems, dropped = hoep_energy(hoep, first_month, averages, stored)
    failures += problems
    hoep = {key: price for key, price in hoep.items() if _month_of(key[0]) not in dropped}
    table = arc.parse_market_table(gmp._text(source.get(gmp.ONTARIO_PRICE_URL, immutable=False),
                                             "Ontario Market Prices page"))
    oemp, oemp_checks, problems, incomplete_energy = oemp_energy(table, archive)
    failures += problems
    energies.update(oemp)
    rates, sheets, workbook_floats, estimates, ga_checks, problems = load_ga(source, first_month)
    failures += problems
    observed: dict[str, int] = defaultdict(int)
    for day, _hour in hoep:
        observed[_month_of(day)] += 1
    for (day, _hour), row in archive.items():
        if row.oemp is not None:
            observed[_month_of(day)] += 1
    last_ended = _shift(_month_of(as_of), -1)
    rows, revisions, problems, incomplete = assemble(first_month, last_ended, energies, rates, stored, observed, as_of,
                                                     estimates)
    failures += problems
    for key, reason in incomplete_energy.items():
        if key in incomplete:
            incomplete[key] = reason
    if failures:
        raise MarketDataError("; ".join(failures))
    window = choose_window(rows, last_ended, window_months)
    surface = build_bins(window, rows, hoep, archive)
    described = describe_months(window, rows)
    gap = _gap(archive, window)
    unobserved = [key for key in window if rows[key].energy_source == HOEP_REPORT]
    adjustments = gmp.ga_adjustments([_ym(key) for key in window],
                                     {key: workbook_floats.get(key, float(rows[key].ga_class_b)) for key in window},
                                     sheets)
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    eras = []
    if window[0] <= LAST_HOEP_MONTH:
        eras.append({"id": "hoep", "name": "Hourly Ontario Energy Price (HOEP, legacy)", "from": window[0],
                     "to": min(LAST_HOEP_MONTH, window[-1])})
    if window[-1] >= FIRST_OEMP_MONTH:
        eras.append({"id": "oemp", "name": "Ontario Electricity Market Price (Ontario Price, OEMP)",
                     "from": max(FIRST_OEMP_MONTH, window[0]), "to": window[-1]})
    method = DERIVATION_METHOD if window_months == WINDOW_MONTHS else f"observed_rolling_{window_months}m_hoep_oemp_ga"
    document = {
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "province": "ON",
            "market_operator": "IESO",
            "unit": "$/kWh (CAD)",
            "price_name": PRICE_NAME,
            "price_basis": PRICE_BASIS,
            "ga_basis": GA_BASIS,
            "derivation_method": method,
            "window_start": date.fromisoformat(window[0] + "-01").isoformat(),
            "window_end": _month_end(window[-1]).isoformat(),
            "window": {"start_month": window[0], "end_month": window[-1], "months": len(window),
                       "complete_rule": COMPLETE_RULE},
            "years": sorted({int(key[:4]) for key in window}),
            "generated_at": generated.isoformat().replace("+00:00", "Z"),
            "as_of": as_of.isoformat(),
            "change_date": CHANGE_DATE.isoformat(),
            "eras": eras,
            "gap": gap,
            "heatmap_basis": _heatmap_basis(gap, unobserved),
            "hoep_retirement": {"retired_on": HOEP_LAST_DAY.isoformat(), "statement": gmp.HOEP_RETIREMENT_STATEMENT,
                                "source_url": gmp.HOEP_PAGE_URL},
            "coverage": coverage(described, surface),
            "months": described,
            "unobserved_hoep_months": [{"month": key, "reason": UNOBSERVED_HOEP_REASON} for key in unobserved],
            "incomplete_months": [{"month": key, "reason": reason} for key, reason in sorted(incomplete.items())],
            "revisions": revisions,
            "ga_adjustments": adjustments,
            "source_codes": SOURCE_CODES,
            "sources": SOURCES,
            "hour_convention": HOUR_CONVENTION,
            "day_type_rule": gmp.DAY_TYPE_RULE,
            "cross_check": {"hoep_monthly_arithmetic": hoep_check, **oemp_checks, **ga_checks},
            "notes": _notes(gap),
        },
        "monthly": [monthly_record(rows[key]) for key in window],
        "hourly_surface": surface,
    }
    validate_document(document, window_months)
    return Build(document, [rows[key] for key in sorted(rows)], window, hoep if refresh_hoep else None, revisions,
                 incomplete)


# -- run -------------------------------------------------------------------------------------------

def render_document(document: dict, path: Path) -> bytes | None:
    """The JSON bytes to write, or None when only generated_at would change."""
    if path.is_file():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previous = None
        stamp = ((previous or {}).get("metadata") or {}).get("generated_at") if isinstance(previous, dict) else None
        if stamp:
            candidate = copy.deepcopy(document)
            candidate["metadata"]["generated_at"] = stamp
            if candidate == previous:
                return None
    return (json.dumps(document, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def write_outputs(outputs: list[tuple[Path, bytes]]) -> None:
    """Write every file to a temporary sibling first, then move them all into place."""
    staged: list[tuple[Path, Path]] = []
    try:
        for path, content in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(path.name + ".tmp")
            temporary.write_bytes(content)
            staged.append((temporary, path))
    except OSError:
        for temporary, _path in staged:
            temporary.unlink(missing_ok=True)
        raise
    for temporary, path in staged:
        os.replace(temporary, path)


def summary_lines(result: Build, downloads: int) -> list[str]:
    inside = set(result.window)
    window = [month for month in result.months if month.month in inside]
    metadata = result.document["metadata"]
    covered = metadata["coverage"]
    eras = {era: [m for m in window if m.era == era] for era in ERAS}
    mean = {name: _mean([getattr(m, name) for m in window]) for name in ("energy_arithmetic", "ga_class_b",
                                                                          "total_arithmetic")}
    lines = [
        f"Monthly history: {len(result.months)} months {result.months[0].month}..{result.months[-1].month}",
        f"Window: {result.window[0]}..{result.window[-1]} ({len(result.window)} months: {len(eras['hoep'])} legacy HOEP, "
        f"{len(eras['oemp'])} Ontario Price)",
        f"Window means ($/MWh, arithmetic): energy {mean['energy_arithmetic']:.2f} + GA {mean['ga_class_b']:.2f} = "
        f"total {mean['total_arithmetic']:.2f}",
        f"Bins: {len(result.document['hourly_surface'])}; observed hours {covered['hours']} of {covered['calendar_hours']}"
        f" (legacy HOEP {covered['hours_hoep']}, Ontario Price {covered['hours_oemp']}); hours per bin weekday "
        f"{covered['hours_per_bin']['weekday']['min']}-{covered['hours_per_bin']['weekday']['max']}, weekend "
        f"{covered['hours_per_bin']['weekend']['min']}-{covered['hours_per_bin']['weekend']['max']}; legacy HOEP "
        f"{covered['hours_hoep_per_bin']['min']}-{covered['hours_hoep_per_bin']['max']}, Ontario Price "
        f"{covered['hours_oemp_per_bin']['min']}-{covered['hours_oemp_per_bin']['max']}",
        f"Gap (hourly Ontario Price not observed): {metadata['gap']['from']}..{metadata['gap']['to']}",
    ]
    checks = metadata["cross_check"]
    lines.append("Checks (max |diff| $/MWh): " + "; ".join(
        f"{name} {checks[name]['months_checked']} months {checks[name]['max_abs_difference']}" for name in checks))
    lines += [f"Revision accepted: {r['month']} {r['field']} {r['previous_per_mwh']} -> {r['new_per_mwh']}"
              for r in result.revisions] or ["Revisions: none"]
    lines += [f"Incomplete: {key} ({reason})" for key, reason in sorted(result.incomplete.items())]
    lines.append(f"Downloads: {downloads}")
    return lines


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the rolling 5-year Ontario market history (legacy HOEP, "
                                                 "Ontario Price and Class B Global Adjustment).")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Market Pricing JSON (default: site/data/market_pricing_ontario.json)")
    parser.add_argument("--monthly-csv", type=Path, default=DEFAULT_MONTHLY,
                        help="permanent monthly history (default: data/market/ontario_market_monthly.csv)")
    parser.add_argument("--hoep-csv", type=Path, default=DEFAULT_HOEP,
                        help="hourly legacy HOEP archive (default: data/market/hoep_hourly.csv)")
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE,
                        help="hourly Ontario Price archive (default: data/market/ontario_price_hourly.csv)")
    parser.add_argument("--cache-dir", type=Path, default=None, help="optional cache of downloaded IESO files")
    parser.add_argument("--as-of", type=date.fromisoformat, default=None,
                        help="date the months must have ended before (default: today, UTC)")
    parser.add_argument("--dry-run", action="store_true", help="check everything but write nothing")
    parser.add_argument("--refresh-hoep", action="store_true",
                        help="(re)import the legacy hourly HOEP and HOEP Monthly Averages reports from the IESO")
    return parser.parse_args(argv)


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes() if path.is_file() else None
    except OSError as exc:
        raise MarketDataError(f"cannot read {path}: {exc}") from None


def main(argv: list[str] | None = None, *, fetch=None, generated_at: datetime | None = None,
         window_months: int = WINDOW_MONTHS, first_month: str = FIRST_MONTH) -> int:
    args = parse_args(argv)
    today = datetime.now(timezone.utc).date()
    as_of = args.as_of or today
    source = gmp.ReportSource(args.cache_dir, today, fetch=fetch or gmp.http_get)
    try:
        archive = _read(args.archive)
        if archive is None:
            raise MarketDataError(f"the hourly Ontario Price archive {args.archive} is missing")
        result = build(source, hoep_content=None if args.refresh_hoep else _read(args.hoep_csv),
                       monthly_content=_read(args.monthly_csv), archive_content=archive, as_of=as_of,
                       refresh_hoep=args.refresh_hoep, generated_at=generated_at, window_months=window_months,
                       first_month=first_month)
    except MarketDataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(f"Nothing written ({source.downloads} downloads).", file=sys.stderr)
        return 1
    for line in summary_lines(result, source.downloads):
        print(line)
    planned = [(args.monthly_csv, serialize_monthly(result.months))]
    if result.hoep is not None:
        planned.append((args.hoep_csv, serialize_hoep(result.hoep)))
    outputs = [(path, content) for path, content in planned
               if (_read(path) or b"").replace(b"\r\n", b"\n") != content]
    document = render_document(result.document, args.output)
    if document is not None:
        outputs.append((args.output, document))
    names = ", ".join(str(path) for path, _ in outputs) or "none"
    if args.dry_run:
        print(f"Dry run: nothing written (would change: {names}).")
    elif not outputs:
        print("All outputs are unchanged.")
    else:
        write_outputs(outputs)
        print(f"Wrote {names}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
