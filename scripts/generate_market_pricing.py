"""Build the Ontario legacy market history surface from official IESO data (Phase 6A).

Writes 576 bins (month 1-12 x weekday/weekend x hour 0-23) of observed averages over full calendar years of
the legacy IESO market (default 2020-2024):

* Hourly Ontario Energy Price (HOEP), from the IESO yearly hourly HOEP report. The HOEP retired on April 30,
  2025 and was replaced with the Ontario Price on May 1, 2025, so these values are legacy-market history;
* Global Adjustment (GA) Class B actual monthly rate, from the IESO Data Directory GA workbook ($/MWh).

The run fails closed (exit status 1, nothing written) when a day, hour or month is missing, a report layout or
unit is unexpected, or a cross-check fails: computed monthly HOEP means against the IESO HOEP Monthly Averages
report, that report's weighted averages against the cents-per-kWh table on the IESO HOEP page, and the $/MWh
GA workbook against the cents-per-kWh GA workbook.

    python scripts/generate_market_pricing.py [--output PATH] [--start-year YYYY] [--end-year YYYY] [--cache-dir PATH]
"""
import argparse
import csv
import io
import json
import math
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import openpyxl
import requests
from bs4 import BeautifulSoup
from openpyxl.utils.exceptions import InvalidFileException

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "site" / "data" / "market_pricing_ontario.json"
DEFAULT_START_YEAR = 2020
DEFAULT_END_YEAR = 2024
# The HOEP began on May 1, 2002 and retired on April 30, 2025, so 2003-2024 are its only full years.
FIRST_FULL_HOEP_YEAR = 2003
LAST_FULL_HOEP_YEAR = 2024
HOEP_RETIRED_ON = date(2025, 4, 30)

REPORTS_BASE = "https://reports-public.ieso.ca/public/"
HOEP_DIR = REPORTS_BASE + "PriceHOEPPredispOR/"
HOEP_AVERAGE_DIR = REPORTS_BASE + "PriceHOEPAverage/"
DATA_DIRECTORY_URL = "https://www.ieso.ca/Power-Data/Data-Directory"
GA_MWH_URL = "https://www.ieso.ca/-/media/Files/IESO/Power-Data/data-directory/Global-Adjustment-Values-MWh.xlsx"
GA_KWH_URL = "https://www.ieso.ca/-/media/Files/IESO/Power-Data/data-directory/Global-Adjustment-kWh.xlsx"
HOEP_PAGE_URL = "https://www.ieso.ca/Sector-Participants/Market-Operations/Legacy-Market/Hourly-Ontario-Energy-Price"
ONTARIO_PRICE_URL = "https://www.ieso.ca/Power-Data/Price-Overview/Ontario-Market-Prices"

HOEP_FILE_RE = re.compile(r"(PUB_PriceHOEPPredispOR_(\d{4})(?:_v(\d+))?\.csv)")
HOEP_AVERAGE_FILE_RE = re.compile(r"(PUB_PriceHOEPAverage_(\d{4})(?:_v(\d+))?\.xml)")
HOEP_TITLE = "Yearly HOEP OR Predispatch Report"
HOEP_HEADER = [
    "Date", "Hour", "HOEP", "Hour 1 Predispatch", "Hour 2 Predispatch", "Hour 3 Predispatch",
    "OR 10 Min Sync", "OR 10 Min non-sync", "OR 30 Min",
]
HOEP_AVERAGE_TITLE = "HOEP Monthly Averages Report"
HOEP_RETIREMENT_STATEMENT = (
    "The Hourly Ontario Energy Price (HOEP) retired on April 30, 2025, and was replaced with the Ontario Price."
)
PAGE_TABLE_HEADING = "Average Weighted Hourly Price (\u00a2/kWh)"
GA_MWH_SHEET = "Global Adjustment $MWh"
GA_MWH_ACTUAL_LABEL = "Actual Rate ($/MWh)"
GA_KWH_SHEET = "Global Adjustment kWh"
GA_KWH_ACTUAL_LABEL = "Actual"
GA_DEFERRAL_SHEET = "2020 Deferral Information"
GA_DEFERRAL_MONTHS = ("2020-04", "2020-05", "2020-06")
GA_UNADJUSTED_LABEL = "Unadjusted Actual Rate ($/MWh)"
GA_RECOVERY_SHEET = "2021 Recovery Rates"
GA_RECOVERY_YEAR = 2021
GA_RECOVERY_LABEL = "Actual Recovery Rate - CBRR Actual ($/MWh)"

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
MONTH_LABELS = {name.lower(): number for number, name in enumerate(MONTH_NAMES, start=1)}
MONTH_LABELS.update({name[:3].lower(): number for number, name in enumerate(MONTH_NAMES, start=1)})
MONTH_LABELS["sept"] = 9
DAY_TYPES = ("weekday", "weekend")
NS = {"i": "http://www.ieso.ca/schema"}

# Legacy market clearing prices were bounded at +/-2,000 $/MWh, so the hourly HOEP was too.
HOEP_LIMIT_PER_MWH = 2000.0
GA_LIMIT_PER_MWH = 1000.0
# Published averages have two decimals: rounding alone explains differences up to 0.005.
HOEP_AVERAGE_TOLERANCE_PER_MWH = 0.01
HOEP_UNIT_TOLERANCE_CENTS = 0.006
# The cents-per-kWh workbook has two decimals, i.e. 0.1 $/MWh steps.
GA_UNIT_TOLERANCE_PER_MWH = 0.051

REQUEST_DELAY_SECONDS = 0.5
RETRY_DELAY_SECONDS = 5.0
HTTP_ATTEMPTS = 2
HTTP_TIMEOUT_SECONDS = 60
USER_AGENT = "canada-utility-costs/0.1 (Ontario legacy market history; python-requests)"

DERIVATION_METHOD_TEMPLATE = "observed_legacy_hoep_{start}_{end}_average"
PRICE_NAME = "Hourly Ontario Energy Price (HOEP, legacy)"
PRICE_BASIS = (
    "Hourly Ontario Energy Price (HOEP): the legacy real-time market price, which in the IESO legacy market was "
    "the average of the twelve market clearing prices set in each hour, published by the IESO in $/MWh. "
    "The HOEP retired on April 30, 2025 and was replaced with the Ontario Price on May 1, 2025. "
    "Each bin is the arithmetic mean of the observed hourly legacy HOEP values in that bin, converted to $/kWh."
)
GA_BASIS = (
    "Global Adjustment Class B actual monthly rate (\"Actual Rate ($/MWh)\" in the IESO Data Directory Global "
    "Adjustment workbook, cross-checked against the IESO cents-per-kWh workbook), converted to $/kWh and applied "
    "to every hour of its month; each bin averages the rates of the months it covers, weighted by observed hours. "
    "Class A customers pay Global Adjustment by their peak demand factor instead."
)
HOUR_CONVENTION = (
    "hour = IESO delivery hour minus 1. The legacy yearly HOEP report's hours 1-24 are hour-ending, so hour 0 "
    "covers 00:00-01:00. Times are Eastern Standard Time all year (IESO market time, no daylight-saving shift; "
    "every day has 24 hours); while daylight time is in effect, hour 0 is 01:00-02:00 on local clocks."
)
DAY_TYPE_RULE = (
    "weekday = Monday-Friday, weekend = Saturday-Sunday, by IESO delivery date. Statutory holidays are not "
    "separated: a holiday counts as the day of the week it falls on."
)
NOTES = (
    "Observed legacy-market history for comparison only: not a tariff, a bill or a forecast. "
    + HOEP_RETIREMENT_STATEMENT + " "
    "Since May 1, 2025, market-billed customers pay the Ontario Electricity Market Price (OEMP, the Ontario Price) "
    "plus Global Adjustment; this view does not show the Ontario Price. "
    "Class A customers pay Global Adjustment by their peak demand factor, not the Class B rate shown here. "
    "Delivery, regulatory, loss and retail contract charges are not included."
)
SOURCES = [
    {"name": "IESO Yearly Hourly HOEP OR Predispatch Report (legacy hourly HOEP, $/MWh)", "url": HOEP_DIR,
     "type": "hourly_price"},
    {"name": "IESO Global Adjustment rates in $/MWh, Class B actual (Data Directory workbook)", "url": GA_MWH_URL,
     "type": "monthly_rate"},
    {"name": "IESO HOEP Monthly Averages Report (legacy)", "url": HOEP_AVERAGE_DIR, "type": "cross_check"},
    {"name": "IESO Hourly Ontario Energy Price (HOEP) - Historic Prices (retirement notice, weighted averages)",
     "url": HOEP_PAGE_URL, "type": "cross_check"},
    {"name": "IESO Global Adjustment rates in cents per kWh (Data Directory workbook)", "url": GA_KWH_URL,
     "type": "cross_check"},
    {"name": "IESO Data Directory (legacy HOEP values are reported as $/MWh)", "url": DATA_DIRECTORY_URL,
     "type": "reference"},
    {"name": "IESO Ontario Market Prices (the Ontario Price since May 1, 2025)", "url": ONTARIO_PRICE_URL,
     "type": "reference"},
]
REQUIRED_METADATA = (
    "province", "market_operator", "unit", "price_name", "price_basis", "ga_basis", "derivation_method",
    "window_start", "window_end", "years", "generated_at", "hoep_retirement", "coverage", "months", "sources",
    "hour_convention", "day_type_rule", "cross_check", "notes",
)
BIN_FIELDS = ("month", "day_type", "hour", "hours_count", "avg_energy_price", "avg_ga_class_b", "combined")


class MarketDataError(Exception):
    """Inputs are missing, malformed or inconsistent; the run must not write output."""


# -- small helpers ---------------------------------------------------------------------------------

def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def month_dates(year: int, month: int) -> list[date]:
    return [date(year, month, day) for day in range(1, monthrange(year, month)[1] + 1)]


def window_months(start_year: int, end_year: int) -> list[tuple[int, int]]:
    return [(year, month) for year in range(start_year, end_year + 1) for month in range(1, 13)]


def day_type(day: date) -> str:
    return DAY_TYPES[1] if day.weekday() >= 5 else DAY_TYPES[0]


def _number(text: str | None, label: str) -> float:
    try:
        value = float(text)
    except (TypeError, ValueError):
        raise MarketDataError(f"{label}: expected a number, found {text!r}") from None
    if not math.isfinite(value):
        raise MarketDataError(f"{label}: expected a finite number, found {text!r}")
    return value


def _parse_date(text: str | None, label: str) -> date:
    try:
        return date.fromisoformat(text or "")
    except ValueError:
        raise MarketDataError(f"{label}: invalid date {text!r}") from None


def _text(content: bytes, label: str) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        raise MarketDataError(f"{label}: not UTF-8 text") from None


def _ranges(days) -> str:
    runs: list[list[date]] = []
    for day in sorted(days):
        if runs and (day - runs[-1][1]).days == 1:
            runs[-1][1] = day
        else:
            runs.append([day, day])
    return ", ".join(str(a) if a == b else f"{a}..{b}" for a, b in runs)


def _best_versions(*mappings: dict) -> dict:
    best: dict[str, tuple[int, str]] = {}
    for mapping in mappings:
        for key, entry in mapping.items():
            if key not in best or entry[0] > best[key][0]:
                best[key] = entry
    return best


def _join(values) -> str:
    texts = [f"{value:.2f}" for value in values]
    return texts[0] if len(texts) == 1 else ", ".join(texts[:-1]) + " and " + texts[-1]


# -- report parsers --------------------------------------------------------------------------------

def parse_listing(html: str, pattern: re.Pattern) -> dict[str, tuple[int, str]]:
    """Map each year key in an IESO directory listing to its highest (version, file name)."""
    found: dict[str, tuple[int, str]] = {}
    for href in re.findall(r'href="([^"]+)"', html):
        match = pattern.fullmatch(href)
        if match:
            found = _best_versions(found, {match.group(2): (int(match.group(3) or 0), match.group(1))})
    return found


def parse_hoep_csv(text: str, year: int, label: str = "HOEP report") -> dict[date, dict[int, float]]:
    """Return {delivery date: {IESO hour-ending 1-24: HOEP in $/MWh}} from a yearly hourly HOEP report."""
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    header_at = next((i for i, row in enumerate(rows) if row and row[0].strip() == HOEP_HEADER[0]), None)
    if header_at is None:
        raise MarketDataError(f"{label}: header row not found")
    # Preamble lines start with backslashes (two in the published files).
    preamble = [row[0].strip().lstrip("\\") for row in rows[:header_at] if row]
    if not preamble or preamble[0] != HOEP_TITLE or f"For {year}" not in preamble:
        raise MarketDataError(f"{label}: expected the yearly HOEP report for {year}, found preamble {preamble!r}")
    header = [cell.strip() for cell in rows[header_at]]
    if header != HOEP_HEADER:
        raise MarketDataError(f"{label}: unexpected header {header!r}; expected {HOEP_HEADER!r}")
    prices: dict[date, dict[int, float]] = {}
    for line, row in enumerate(rows[header_at + 1:], start=header_at + 2):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != len(HOEP_HEADER):
            raise MarketDataError(f"{label} line {line}: expected {len(HOEP_HEADER)} columns, found {len(row)}")
        day = _parse_date(row[0].strip(), f"{label} line {line}")
        if day.year != year:
            raise MarketDataError(f"{label} line {line}: date {day} is outside {year}")
        hour_text = row[1].strip()
        if not hour_text.isdigit() or not 1 <= int(hour_text) <= 24:
            raise MarketDataError(f"{label} line {line}: invalid hour {hour_text!r}")
        hours = prices.setdefault(day, {})
        if int(hour_text) in hours:
            raise MarketDataError(f"{label} line {line}: duplicate {day} hour {hour_text}")
        price = _number(row[2].strip(), f"{label} line {line} HOEP")
        if abs(price) > HOEP_LIMIT_PER_MWH:
            raise MarketDataError(f"{label} line {line}: HOEP {price} is outside +/-{HOEP_LIMIT_PER_MWH:g} $/MWh")
        hours[int(hour_text)] = price
    return prices


def _parse_xml(content: bytes, doc_id: str, label: str) -> ET.Element:
    if b"<!DOCTYPE" in content or b"<!ENTITY" in content:
        raise MarketDataError(f"{label}: unexpected DOCTYPE or ENTITY declaration")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise MarketDataError(f"{label}: malformed XML ({exc})") from None
    if root.tag != "{http://www.ieso.ca/schema}Document" or root.get("docID") != doc_id:
        raise MarketDataError(f"{label}: expected an IESO {doc_id} document, found docID={root.get('docID')!r}")
    return root


def _find_text(element: ET.Element, path: str) -> str | None:
    found = element.find(path, NS)
    return None if found is None or found.text is None else found.text.strip()


def parse_hoep_averages(content: bytes, year: int, label: str = "HOEP averages report") -> dict[str, dict]:
    """Return {"YYYY-MM": {"arithmetic", "weighted"}} in $/MWh from a yearly HOEP Monthly Averages report."""
    root = _parse_xml(content, "PriceHOEPAverage", label)
    title = _find_text(root, "i:DocHeader/i:DocTitle")
    if title != HOEP_AVERAGE_TITLE:
        raise MarketDataError(f"{label}: unexpected report title {title!r}")
    report_year = _find_text(root, "i:DocBody/i:ReportYear")
    if report_year != str(year):
        raise MarketDataError(f"{label}: expected ReportYear {year}, found {report_year!r}")
    averages: dict[str, dict] = {}
    for element in root.findall("i:DocBody/i:HOEP", NS):
        name = _find_text(element, "i:Month")
        if name not in MONTH_NAMES:
            raise MarketDataError(f"{label}: unexpected month {name!r}")
        key = month_key(year, MONTH_NAMES.index(name) + 1)
        if key in averages:
            raise MarketDataError(f"{label}: duplicate month {key}")
        averages[key] = {
            "arithmetic": _number(_find_text(element, "i:ArithmeticAve"), f"{label} {key} ArithmeticAve"),
            "weighted": _number(_find_text(element, "i:WeightedAve"), f"{label} {key} WeightedAve"),
        }
    if not averages:
        raise MarketDataError(f"{label}: no monthly averages found")
    return averages


def parse_hoep_page(html: str, label: str = "HOEP page") -> dict[str, float]:
    """Require the retirement statement; return {"YYYY-MM": weighted HOEP in cents/kWh} from the page table."""
    soup = BeautifulSoup(html, "html.parser")
    if HOEP_RETIREMENT_STATEMENT not in " ".join(soup.get_text(" ").split()):
        raise MarketDataError(f"{label}: retirement statement {HOEP_RETIREMENT_STATEMENT!r} not found")
    heading = next((tag for tag in soup.find_all(["h2", "h3", "h4", "h5"])
                    if " ".join(tag.get_text().split()) == PAGE_TABLE_HEADING), None)
    table = heading.find_next("table") if heading else None
    if table is None:
        raise MarketDataError(f"{label}: table {PAGE_TABLE_HEADING!r} not found")
    header = [" ".join(th.get_text().split()) for th in table.find_all("th")]
    expected = ["Year"] + [name[:3] for name in MONTH_NAMES]
    if header != expected:
        raise MarketDataError(f"{label}: unexpected columns {header!r}; expected {expected!r}")
    weighted: dict[str, float] = {}
    for row in table.find_all("tr"):
        cells = [" ".join(td.get_text().split()) for td in row.find_all("td")]
        if not cells:
            continue
        if len(cells) != 13 or not re.fullmatch(r"\d{4}", cells[0]):
            raise MarketDataError(f"{label}: unexpected row {cells!r}")
        for month, cell in enumerate(cells[1:], start=1):
            if not cell:
                continue
            key = month_key(int(cells[0]), month)
            if key in weighted:
                raise MarketDataError(f"{label}: duplicate month {key}")
            weighted[key] = _number(cell, f"{label} {key}")
    if not weighted:
        raise MarketDataError(f"{label}: no monthly values found")
    return weighted


def read_workbook(content: bytes, label: str) -> dict[str, list[list]]:
    """Every sheet of an .xlsx workbook as rows of cell values."""
    try:
        workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    except (InvalidFileException, zipfile.BadZipFile, KeyError, ValueError, OSError) as exc:
        raise MarketDataError(f"{label}: not a readable .xlsx workbook ({type(exc).__name__})") from None
    return {sheet.title: [list(row) for row in sheet.iter_rows(values_only=True)] for sheet in workbook.worksheets}


def _clean(value):
    """Workbook text without zero-width or non-breaking spaces (the IESO sheets contain both)."""
    if isinstance(value, str):
        return " ".join(value.replace("\u200b", "").replace("\xa0", " ").split())
    return value


def _cell(row: list, index: int):
    return _clean(row[index]) if index < len(row) else None


def _cell_number(value, label: str) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise MarketDataError(f"{label}: expected a finite number, found {value!r}")
        return float(value)
    if isinstance(value, str) and value:
        return _number(value, label)
    raise MarketDataError(f"{label}: expected a number, found {value!r}")


def _year_cell(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and re.fullmatch(r"\d{4}", value):
        return int(value)
    return None


def _month_columns(row: list, first: int, label: str) -> list[int]:
    """Columns first..first+11, which must be headed January to December in order."""
    labels = [_cell(row, index) for index in range(first, first + 12)]
    if [MONTH_LABELS.get(str(text or "").lower()) for text in labels] != list(range(1, 13)):
        raise MarketDataError(f"{label}: unexpected month headings {labels!r}")
    return list(range(first, first + 12))


def _sheet(sheets: dict, title: str, label: str) -> list[list]:
    if title not in sheets:
        raise MarketDataError(f"{label}: sheet {title!r} not found (found {sorted(sheets)!r})")
    return sheets[title]


def _actual_rates(rows: list[list], actual_label: str, limit: float, label: str) -> dict[str, float]:
    """{"YYYY-MM": value} from the rows labelled actual_label under each year block (year in column A)."""
    header = next((row for row in rows if _cell(row, 0) == "Year"), None)
    if header is None:
        raise MarketDataError(f"{label}: 'Year' heading row not found")
    columns = _month_columns(header, 2, label)
    rates: dict[str, float] = {}
    year = None
    for row in rows:
        year = _year_cell(_cell(row, 0)) or year
        text = str(_cell(row, 1) or "")
        if not text.lower().startswith("actual"):
            continue
        if text != actual_label:
            raise MarketDataError(f"{label}: unexpected row label {text!r}; expected {actual_label!r}")
        if year is None or any(key.startswith(f"{year:04d}-") for key in rates):
            raise MarketDataError(f"{label}: {text!r} row without a new year (after {year})")
        for month, column in enumerate(columns, start=1):
            value = _cell(row, column)
            if value is None or value == "":
                continue
            key = month_key(year, month)
            rates[key] = _cell_number(value, f"{label} {key}")
            if abs(rates[key]) > limit:
                raise MarketDataError(f"{label}: {key} rate {rates[key]} is outside +/-{limit:g}")
    if not rates:
        raise MarketDataError(f"{label}: no {actual_label!r} rows found")
    return rates


def parse_ga_mwh(sheets: dict, label: str = "GA $/MWh workbook") -> dict[str, float]:
    """Class B actual rates {"YYYY-MM": $/MWh} from the "Actual Rate ($/MWh)" rows."""
    return _actual_rates(_sheet(sheets, GA_MWH_SHEET, label), GA_MWH_ACTUAL_LABEL, GA_LIMIT_PER_MWH, label)


def parse_ga_kwh(sheets: dict, label: str = "GA cents/kWh workbook") -> dict[str, float]:
    """Class B actual rates {"YYYY-MM": cents/kWh} from the "Actual" rows."""
    return _actual_rates(_sheet(sheets, GA_KWH_SHEET, label), GA_KWH_ACTUAL_LABEL, GA_LIMIT_PER_MWH / 10, label)


def parse_ga_deferral(sheets: dict, label: str = "GA $/MWh workbook") -> tuple[float, dict[str, float]]:
    """(Class B cap in $/MWh, {"2020-MM": unadjusted actual rate}) from the 2020 deferral sheet."""
    rows = _sheet(sheets, GA_DEFERRAL_SHEET, label)
    text = " ".join(str(_cell(row, 0) or "") for row in rows)
    match = re.search(r"Class B rate will not exceed \$(\d+(?:\.\d+)?)/MWh", text)
    if not match:
        raise MarketDataError(f"{label}: Class B deferral cap statement not found in {GA_DEFERRAL_SHEET!r}")
    header = next((row for row in rows if _year_cell(_cell(row, 0)) == 2020), None)
    unadjusted = next((row for row in rows if _cell(row, 0) == GA_UNADJUSTED_LABEL), None)
    if header is None or unadjusted is None:
        raise MarketDataError(f"{label}: {GA_UNADJUSTED_LABEL!r} row for 2020 not found")
    months = [MONTH_LABELS.get(str(_cell(header, column) or "").lower()) for column in (1, 2, 3)]
    if [month_key(2020, month or 0) for month in months] != list(GA_DEFERRAL_MONTHS):
        raise MarketDataError(f"{label}: unexpected deferral months {[_cell(header, c) for c in (1, 2, 3)]!r}")
    rates = {key: _cell_number(_cell(unadjusted, column), f"{label} unadjusted {key}")
             for column, key in zip((1, 2, 3), GA_DEFERRAL_MONTHS)}
    return float(match.group(1)), rates


def parse_ga_recovery(sheets: dict, label: str = "GA $/MWh workbook") -> dict[str, float]:
    """{"2021-MM": actual Class B recovery rate in $/MWh} from the 2021 recovery sheet."""
    rows = _sheet(sheets, GA_RECOVERY_SHEET, label)
    header = next((row for row in rows if _year_cell(_cell(row, 0)) == GA_RECOVERY_YEAR), None)
    actual = next((row for row in rows if _cell(row, 0) == GA_RECOVERY_LABEL), None)
    if header is None or actual is None:
        raise MarketDataError(f"{label}: {GA_RECOVERY_LABEL!r} row for {GA_RECOVERY_YEAR} not found")
    columns = _month_columns(header, 1, label)
    return {month_key(GA_RECOVERY_YEAR, month): _cell_number(_cell(actual, column), f"{label} recovery {month}")
            for month, column in enumerate(columns, start=1)}


# -- downloading -----------------------------------------------------------------------------------

def http_get(url: str) -> bytes:
    error = "not attempted"
    for attempt in range(HTTP_ATTEMPTS):
        if attempt:
            time.sleep(RETRY_DELAY_SECONDS)
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            error = type(exc).__name__
            continue
        if response.status_code == 200:
            return response.content
        error = f"HTTP {response.status_code}"
        if response.status_code < 500:
            break
    raise MarketDataError(f"could not download {url}: {error}")


def _cache_folder(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path if url.endswith("/") else parsed.path.rsplit("/", 1)[0]
    return (parsed.netloc + path).strip("/").replace("/", "_")


class ReportSource:
    """Downloads IESO files politely. With a cache directory, versioned report files are kept forever
    (an archive of files the IESO may later remove) and other pages are reused only on the same day."""

    def __init__(self, cache_dir: Path | None, run_date: date, fetch=http_get, delay: float | None = None):
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.run_date = run_date
        self.fetch = fetch
        self.delay = REQUEST_DELAY_SECONDS if delay is None else delay
        self.downloads = 0
        self._last_request: float | None = None

    def get(self, url: str, immutable: bool) -> bytes:
        path = self._cache_path(url, immutable)
        if path is not None and path.is_file():
            return path.read_bytes()
        if self._last_request is not None:
            wait = self.delay - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
        content = self.fetch(url)
        self._last_request = time.monotonic()
        self.downloads += 1
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return content

    def archived(self, directory_url: str, pattern: re.Pattern) -> dict[str, tuple[int, str]]:
        """Versioned files of one report directory already kept in the cache."""
        folder = self.cache_dir / _cache_folder(directory_url) if self.cache_dir else None
        found: dict[str, tuple[int, str]] = {}
        if folder is not None and folder.is_dir():
            for path in folder.iterdir():
                match = pattern.fullmatch(path.name)
                if match and match.group(3):
                    found = _best_versions(found, {match.group(2): (int(match.group(3)), match.group(1))})
        return found

    def _cache_path(self, url: str, immutable: bool) -> Path | None:
        if self.cache_dir is None:
            return None
        folder = self.cache_dir / _cache_folder(url)
        name = "_listing.html" if url.endswith("/") else url.rsplit("/", 1)[-1]
        return folder / name if immutable else folder / self.run_date.isoformat() / name


# -- loading ---------------------------------------------------------------------------------------

def _yearly_files(source: ReportSource, directory: str, pattern: re.Pattern, years: list[int],
                  what: str) -> dict[int, tuple[int, str]]:
    listed = parse_listing(source.get(directory, immutable=False).decode("utf-8", "replace"), pattern)
    files = _best_versions(source.archived(directory, pattern), listed)
    missing = [str(year) for year in years if str(year) not in files]
    if missing:
        raise MarketDataError(f"{what} not available for {', '.join(missing)} at {directory}")
    return {year: files[str(year)] for year in years}


def load_hoep(source: ReportSource, years: list[int]) -> dict[date, dict[int, float]]:
    prices: dict[date, dict[int, float]] = {}
    for year, (version, name) in _yearly_files(source, HOEP_DIR, HOEP_FILE_RE, years, "yearly HOEP report").items():
        prices.update(parse_hoep_csv(_text(source.get(HOEP_DIR + name, immutable=version > 0), name), year, name))
    return prices


def load_hoep_averages(source: ReportSource, years: list[int]) -> dict[str, dict]:
    averages: dict[str, dict] = {}
    files = _yearly_files(source, HOEP_AVERAGE_DIR, HOEP_AVERAGE_FILE_RE, years, "HOEP Monthly Averages report")
    for year, (version, name) in files.items():
        averages.update(parse_hoep_averages(source.get(HOEP_AVERAGE_DIR + name, immutable=version > 0), year, name))
    return averages


# -- window, checks and bins -----------------------------------------------------------------------

def check_years(start_year: int, end_year: int) -> list[int]:
    if start_year > end_year:
        raise MarketDataError(f"start year {start_year} is after end year {end_year}")
    if start_year < FIRST_FULL_HOEP_YEAR or end_year > LAST_FULL_HOEP_YEAR:
        raise MarketDataError(
            f"years {start_year}-{end_year} are outside {FIRST_FULL_HOEP_YEAR}-{LAST_FULL_HOEP_YEAR}, the full "
            f"calendar years of the HOEP (May 1, 2002 to its retirement on {HOEP_RETIRED_ON})"
        )
    return list(range(start_year, end_year + 1))


def check_complete(months: list[tuple[int, int]], hoep: dict, ga: dict) -> None:
    days = [day for year, month in months for day in month_dates(year, month)]
    problems = []
    missing_days = [day for day in days if day not in hoep]
    if missing_days:
        problems.append(f"HOEP missing for {len(missing_days)} day(s): {_ranges(missing_days)}")
    partial = [day for day in days if day in hoep and sorted(hoep[day]) != list(range(1, 25))]
    if partial:
        problems.append(f"HOEP hours missing for {len(partial)} day(s): " + "; ".join(
            f"{day} hour(s) {sorted(set(range(1, 25)) - set(hoep[day]))}" for day in partial[:5]))
    missing_ga = [month_key(*ym) for ym in months if month_key(*ym) not in ga]
    if missing_ga:
        problems.append("GA Class B actual rate missing for " + ", ".join(missing_ga))
    if problems:
        raise MarketDataError(
            f"window {month_key(*months[0])}..{month_key(*months[-1])} is incomplete: " + "; ".join(problems)
        )


def monthly_hoep_mean(year: int, month: int, hoep: dict) -> float:
    """Arithmetic mean over every hour of a month, $/MWh (the basis of the report's ArithmeticAve)."""
    values = [hoep[day][hour] for day in month_dates(year, month) for hour in range(1, 25)]
    return math.fsum(values) / len(values)


def cross_check_hoep(months: list[tuple[int, int]], hoep: dict, averages: dict) -> dict:
    entries, failures, worst = [], [], 0.0
    for year, month in months:
        key = month_key(year, month)
        if key not in averages:
            failures.append(f"{key} is not in the published report")
            continue
        computed = monthly_hoep_mean(year, month, hoep)
        published = averages[key]["arithmetic"]
        difference = computed - published
        worst = max(worst, abs(difference))
        if abs(difference) > HOEP_AVERAGE_TOLERANCE_PER_MWH:
            failures.append(f"{key} computed {computed:.4f} vs published {published}")
        entries.append({"month": key, "computed": round(computed, 4), "published": published,
                        "difference": round(difference, 4)})
    if failures:
        raise MarketDataError(
            f"HOEP cross-check against {HOEP_AVERAGE_DIR} failed (tolerance {HOEP_AVERAGE_TOLERANCE_PER_MWH} "
            "$/MWh): " + "; ".join(failures)
        )
    return {
        "source_url": HOEP_AVERAGE_DIR,
        "basis": "computed arithmetic mean of every hourly legacy HOEP value in the month vs the IESO HOEP "
                 "Monthly Averages report's ArithmeticAve; the report's demand-weighted average is not "
                 "comparable with these unweighted averages",
        "unit": "$/MWh",
        "tolerance": HOEP_AVERAGE_TOLERANCE_PER_MWH,
        "months_checked": len(entries),
        "max_abs_difference": round(worst, 4),
        "months": entries,
    }


def check_hoep_unit(months: list[tuple[int, int]], averages: dict, page_cents: dict) -> dict:
    failures, worst, checked = [], 0.0, 0
    for year, month in months:
        key = month_key(year, month)
        if key not in averages or key not in page_cents:
            failures.append(f"{key} is missing from the report or the page")
            continue
        difference = averages[key]["weighted"] / 10 - page_cents[key]
        worst, checked = max(worst, abs(difference)), checked + 1
        if abs(difference) > HOEP_UNIT_TOLERANCE_CENTS:
            failures.append(f"{key} report WeightedAve {averages[key]['weighted']} $/MWh vs page "
                            f"{page_cents[key]} cents/kWh")
    if failures:
        raise MarketDataError(
            f"HOEP unit check against {HOEP_PAGE_URL} failed (tolerance {HOEP_UNIT_TOLERANCE_CENTS} cents/kWh): "
            + "; ".join(failures)
        )
    return {
        "source_url": HOEP_PAGE_URL,
        "basis": "legacy HOEP Monthly Averages report WeightedAve ($/MWh) divided by 10 vs the page's 'Average "
                 "Weighted Hourly Price (\u00a2/kWh)' table, confirming that the legacy HOEP reports are in $/MWh",
        "unit": "\u00a2/kWh",
        "tolerance": HOEP_UNIT_TOLERANCE_CENTS,
        "months_checked": checked,
        "max_abs_difference": round(worst, 4),
    }


def check_ga_units(months: list[tuple[int, int]], ga_mwh: dict, ga_kwh_cents: dict) -> dict:
    failures, worst, checked = [], 0.0, 0
    for year, month in months:
        key = month_key(year, month)
        if key not in ga_kwh_cents:
            failures.append(f"{key} is not in the cents-per-kWh workbook")
            continue
        difference = ga_mwh[key] - ga_kwh_cents[key] * 10
        worst, checked = max(worst, abs(difference)), checked + 1
        if abs(difference) > GA_UNIT_TOLERANCE_PER_MWH:
            failures.append(f"{key} {ga_mwh[key]} $/MWh vs {ga_kwh_cents[key]} cents/kWh")
    if failures:
        raise MarketDataError(
            f"GA unit check against {GA_KWH_URL} failed (tolerance {GA_UNIT_TOLERANCE_PER_MWH} $/MWh): "
            + "; ".join(failures)
        )
    return {
        "source_url": GA_KWH_URL,
        "basis": "Class B 'Actual Rate ($/MWh)' vs 10 x the 'Actual' rate in the IESO cents-per-kWh workbook",
        "unit": "$/MWh",
        "tolerance": GA_UNIT_TOLERANCE_PER_MWH,
        "months_checked": checked,
        "max_abs_difference": round(worst, 4),
    }


def ga_adjustments(months: list[tuple[int, int]], ga: dict, sheets: dict) -> list[dict]:
    """What the published actual rates include for the 2020 deferral and the 2021 recovery months."""
    keys = {month_key(*ym) for ym in months}
    notes = []
    if keys & set(GA_DEFERRAL_MONTHS):
        cap, unadjusted = parse_ga_deferral(sheets)
        published = {key: ga[key] for key in GA_DEFERRAL_MONTHS}
        if any(rate > cap for rate in published.values()):
            raise MarketDataError(f"GA actual rates {published} exceed the ${cap:g}/MWh deferral cap")
        notes.append({
            "type": "deferral_cap",
            "months": list(GA_DEFERRAL_MONTHS),
            "description": (
                f"Provincial Global Adjustment deferral, April-June 2020: the Class B rate did not exceed "
                f"${cap:g}/MWh. The published actual rates used here ({_join(published.values())} $/MWh) are the "
                f"capped rates; the IESO's unadjusted actual rates were {_join(unadjusted.values())} $/MWh."
            ),
            "published_actual_per_mwh": published,
            "unadjusted_actual_per_mwh": unadjusted,
            "source_url": GA_MWH_URL,
        })
    recovery_keys = sorted(key for key in keys if key.startswith(f"{GA_RECOVERY_YEAR}-"))
    if recovery_keys:
        recovery = parse_ga_recovery(sheets)
        notes.append({
            "type": "deferral_recovery_not_included",
            "months": recovery_keys,
            "description": (
                f"During {GA_RECOVERY_YEAR} the deferred 2020 amount was recovered from non-RPP Class B customers "
                f"through separate monthly Class B recovery rates (actual {min(recovery.values()):.2f}-"
                f"{max(recovery.values()):.2f} $/MWh). The IESO's published {GA_RECOVERY_YEAR} actual rates, "
                "used here, do not include them."
            ),
            "recovery_actual_per_mwh": recovery,
            "source_url": GA_MWH_URL,
        })
    return notes


def build_surface(months: list[tuple[int, int]], hoep: dict, ga: dict) -> list[dict]:
    energy: dict[tuple, list[float]] = defaultdict(list)
    adjustment: dict[tuple, list[float]] = defaultdict(list)
    for year, month in months:
        rate = ga[month_key(year, month)]
        for day in month_dates(year, month):
            kind = day_type(day)
            for hour in range(1, 25):
                energy[(month, kind, hour - 1)].append(hoep[day][hour])
                adjustment[(month, kind, hour - 1)].append(rate)
    surface = []
    for month in range(1, 13):
        for kind in DAY_TYPES:
            for hour in range(24):
                values = energy.get((month, kind, hour))
                if not values:
                    raise MarketDataError(f"no observations for month {month} {kind} hour {hour}")
                price = math.fsum(values) / len(values) / 1000
                rate = math.fsum(adjustment[(month, kind, hour)]) / len(values) / 1000
                surface.append({
                    "month": month,
                    "day_type": kind,
                    "hour": hour,
                    "hours_count": len(values),
                    "avg_energy_price": round(price, 6),
                    "avg_ga_class_b": round(rate, 6),
                    "combined": round(price + rate, 6),
                })
    return surface


def describe_months(months: list[tuple[int, int]], ga: dict) -> list[dict]:
    described = []
    for year, month in months:
        days = month_dates(year, month)
        weekend_days = sum(day_type(day) == DAY_TYPES[1] for day in days)
        described.append({"month": month_key(year, month), "days": len(days), "weekday_days": len(days) - weekend_days,
                          "weekend_days": weekend_days, "hours": len(days) * 24,
                          "ga_class_b_actual_per_mwh": ga[month_key(year, month)]})
    return described


def coverage(months: list[dict], surface: list[dict]) -> dict:
    counts = {kind: [b["hours_count"] for b in surface if b["day_type"] == kind] for kind in DAY_TYPES}
    return {
        "days": sum(m["days"] for m in months),
        "hours": sum(m["hours"] for m in months),
        "months": len(months),
        "weekday_days": sum(m["weekday_days"] for m in months),
        "weekend_days": sum(m["weekend_days"] for m in months),
        "hours_per_bin": {kind: {"min": min(values), "max": max(values)} for kind, values in counts.items()},
    }


def validate_document(document: dict) -> None:
    metadata = document.get("metadata") or {}
    missing = [key for key in REQUIRED_METADATA if not metadata.get(key)]
    if missing:
        raise MarketDataError(f"output metadata missing {missing}")
    surface = document.get("hourly_surface") or []
    expected = {(month, kind, hour) for month in range(1, 13) for kind in DAY_TYPES for hour in range(24)}
    if len(surface) != len(expected) or {(b["month"], b["day_type"], b["hour"]) for b in surface} != expected:
        raise MarketDataError("output must contain exactly one bin per month, day type and hour (576)")
    for entry in surface:
        values = [entry.get(field) for field in BIN_FIELDS[4:]]
        if set(entry) != set(BIN_FIELDS) or entry["hours_count"] < 1 or not all(
            isinstance(value, (int, float)) and math.isfinite(value) for value in values
        ):
            raise MarketDataError(f"invalid bin {entry!r}")
    if sum(entry["hours_count"] for entry in surface) != metadata["coverage"]["hours"]:
        raise MarketDataError("bin hours do not add up to the window's hours")


def build_document(source: ReportSource, start_year: int = DEFAULT_START_YEAR, end_year: int = DEFAULT_END_YEAR,
                   generated_at: datetime | None = None) -> dict:
    """Download, validate and aggregate the inputs; raise MarketDataError instead of returning partial data."""
    years = check_years(start_year, end_year)
    months = window_months(start_year, end_year)
    hoep = load_hoep(source, years)
    ga_sheets = read_workbook(source.get(GA_MWH_URL, immutable=False), "GA $/MWh workbook")
    ga = parse_ga_mwh(ga_sheets)
    check_complete(months, hoep, ga)
    averages = load_hoep_averages(source, years)
    page_cents = parse_hoep_page(_text(source.get(HOEP_PAGE_URL, immutable=False), "HOEP page"))
    ga_kwh_cents = parse_ga_kwh(read_workbook(source.get(GA_KWH_URL, immutable=False), "GA cents/kWh workbook"))
    checks = {
        "hoep_monthly_arithmetic": cross_check_hoep(months, hoep, averages),
        "hoep_unit": check_hoep_unit(months, averages, page_cents),
        "ga_class_b_units": check_ga_units(months, ga, ga_kwh_cents),
    }
    adjustments = ga_adjustments(months, ga, ga_sheets)
    surface = build_surface(months, hoep, ga)
    described = describe_months(months, ga)
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc).replace(microsecond=0)
    document = {
        "metadata": {
            "province": "ON",
            "market_operator": "IESO",
            "unit": "$/kWh (CAD)",
            "price_name": PRICE_NAME,
            "price_basis": PRICE_BASIS,
            "ga_basis": GA_BASIS,
            "derivation_method": DERIVATION_METHOD_TEMPLATE.format(start=start_year, end=end_year),
            "window_start": date(start_year, 1, 1).isoformat(),
            "window_end": date(end_year, 12, 31).isoformat(),
            "years": years,
            "generated_at": generated.isoformat().replace("+00:00", "Z"),
            "hoep_retirement": {
                "retired_on": HOEP_RETIRED_ON.isoformat(),
                "statement": HOEP_RETIREMENT_STATEMENT,
                "source_url": HOEP_PAGE_URL,
            },
            "coverage": coverage(described, surface),
            "months": described,
            "ga_adjustments": adjustments,
            "sources": SOURCES,
            "hour_convention": HOUR_CONVENTION,
            "day_type_rule": DAY_TYPE_RULE,
            "cross_check": checks,
            "notes": NOTES,
        },
        "hourly_surface": surface,
    }
    validate_document(document)
    return document


def write_document(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Ontario legacy HOEP + Class B GA history surface.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="output JSON path (default: site/data/market_pricing_ontario.json)")
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR,
                        help=f"first full calendar year (default {DEFAULT_START_YEAR})")
    parser.add_argument("--end-year", type=int, default=DEFAULT_END_YEAR,
                        help=f"last full calendar year (default {DEFAULT_END_YEAR}; the HOEP retired April 30, 2025)")
    parser.add_argument("--cache-dir", type=Path, default=None,
                        help="optional cache and archive of downloaded files (default: no cache)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source = ReportSource(args.cache_dir, datetime.now(timezone.utc).date(), fetch=http_get)
    try:
        document = build_document(source, args.start_year, args.end_year)
    except MarketDataError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(f"Nothing written; {args.output} is unchanged ({source.downloads} downloads).", file=sys.stderr)
        return 1
    write_document(args.output, document)
    metadata = document["metadata"]
    covered, checks = metadata["coverage"], metadata["cross_check"]
    bins = covered["hours_per_bin"]
    print(f"Wrote {len(document['hourly_surface'])} bins to {args.output} ({source.downloads} downloads)")
    print(f"Window {metadata['window_start']}..{metadata['window_end']}: {covered['days']} days, {covered['hours']} "
          f"hours; hours per bin weekday {bins['weekday']['min']}-{bins['weekday']['max']}, weekend "
          f"{bins['weekend']['min']}-{bins['weekend']['max']}")
    print(f"Cross-checks: HOEP monthly arithmetic max |diff| {checks['hoep_monthly_arithmetic']['max_abs_difference']}"
          f" $/MWh; HOEP unit max |diff| {checks['hoep_unit']['max_abs_difference']} cents/kWh; GA units max |diff| "
          f"{checks['ga_class_b_units']['max_abs_difference']} $/MWh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
