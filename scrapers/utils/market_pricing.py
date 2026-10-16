"""
market_pricing.py -- Load and query the Ontario market history surface.

Since May 1, 2025, Ontario customers on market prices pay the hourly Ontario Electricity Market Price
(OEMP, the "Ontario Price" = Day-Ahead Ontario Zonal Price + Load Forecast Deviation Adjustment) plus the
Global Adjustment (Class B: monthly rate per kWh; Class A: by peak demand factor).

site/data/market_pricing_ontario.json holds observed IESO history in $/kWh, never a tariff or a forecast:

* schema 2 (scripts/build_ontario_market.py, derivation_method "observed_rolling_60m_hoep_oemp_ga"): the latest
  60 complete months (energy = legacy Hourly Ontario Energy Price (HOEP) until it retired on April 30, 2025, then
  the Ontario Price; plus the Class B Global Adjustment actual rate) and 576 bins (month x weekday/weekend x hour)
  built from observed hours only;
* the earlier legacy surface (scripts/generate_market_pricing.py, "observed_legacy_hoep_YYYY_YYYY_average"): 576
  bins of legacy HOEP and Class B Global Adjustment over full calendar years.
"""
from __future__ import annotations

import json
import logging
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MARKET_DATA_PATH = PROJECT_ROOT / "site" / "data" / "market_pricing_ontario.json"
ROLLING_METHOD = "observed_rolling_60m_hoep_oemp_ga"
OBSERVED_METHOD_RE = re.compile(r"^(?:observed_legacy_hoep_\d{4}_\d{4}_average|observed_rolling_60m_hoep_oemp_ga)$")
PRICE_FIELDS = ("avg_energy_price", "avg_ga_class_b", "combined")
DAY_TYPES = ("weekday", "weekend")
WINDOW_MONTHS = 60
HOURS_PER_MONTH = 730.5
WEEKDAYS_PER_MONTH = 365.25 * 5 / 7 / 12
MIN_TIME_WEIGHTED_ENERGY = 0.001
SYNTHETIC_LABEL = "SYNTHETIC LOAD PROFILE - ILLUSTRATIVE ONLY"


def load_ontario_market_pricing(path: Path = MARKET_DATA_PATH) -> dict:
    """Load the observed surface; reject files that are not built from IESO observations."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    method = (data.get("metadata") or {}).get("derivation_method")
    if not OBSERVED_METHOD_RE.fullmatch(method or ""):
        raise ValueError(f"{path} is not an observed IESO market surface (derivation_method={method!r})")
    return data


def get_observed_bin(month: int, day_type: str, hour: int, path: Path = MARKET_DATA_PATH) -> dict:
    """
    Get the observed average for one bin.

    Args:
        month: 1-12
        day_type: "weekday" or "weekend"
        hour: 0-23 (hour beginning, Eastern Standard Time)

    Returns:
        dict with hours_count and avg_energy_price, avg_ga_class_b, combined ($/kWh); rolling files add
        hours_hoep and hours_oemp
    """
    data = load_ontario_market_pricing(path)
    for entry in data["hourly_surface"]:
        if entry["month"] == month and entry["day_type"] == day_type and entry["hour"] == hour:
            return entry
    raise ValueError(f"No data for month={month}, day_type={day_type}, hour={hour}")


def get_monthly_average(month: int, path: Path = MARKET_DATA_PATH) -> dict:
    """Average of all observed hours in a month (each bin weighted by its hours_count), $/kWh."""
    data = load_ontario_market_pricing(path)
    entries = [e for e in data["hourly_surface"] if e["month"] == month]
    hours = sum(e["hours_count"] for e in entries)
    if not hours:
        raise ValueError(f"No observations for month={month}")
    result = {"month": month, "hours": hours}
    for field in PRICE_FIELDS:
        result[field] = round(sum(e[field] * e["hours_count"] for e in entries) / hours, 6)
    return result


def get_monthly_series(path: Path = MARKET_DATA_PATH) -> list[dict]:
    """The window's monthly records (energy, Class B GA and total in $/kWh) of a rolling (schema 2) file."""
    data = load_ontario_market_pricing(path)
    monthly = data.get("monthly")
    if not isinstance(monthly, list) or not monthly:
        raise ValueError(f"{path} has no monthly series (derivation_method="
                         f"{data['metadata'].get('derivation_method')!r})")
    return [dict(entry) for entry in monthly]


def get_market_tariff_metadata() -> dict:
    """
    Return metadata dict for market-based Ontario tariffs.
    Use this when storing tariff records for market-priced customer classes.
    """
    return {
        "pricing_method": "market_based",
        "formula": "Ontario Electricity Market Price (DA-OZP + LFDA) + Global Adjustment",
        "market_reference": "IESO",
        "ga_allocation": "Class B: monthly rate per kWh; Class A: peak demand factor",
        "notes": (
            "Energy is billed at the hourly Ontario Price plus Global Adjustment. The Market Pricing view shows the "
            "latest five years of observed history (legacy HOEP until it retired April 30, 2025, then the Ontario "
            "Price) with Class B Global Adjustment for context only; it is not a tariff value."
        ),
    }


# -- Phase 7E illustrative estimate (synthetic load profile) -----------------------------------------

def _number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _month_index(key: str) -> int:
    return int(key[:4]) * 12 + int(key[5:7]) - 1


def _month_key(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def _as_date(value) -> date:
    if value is None:
        return datetime.now(timezone.utc).date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def synthetic_profile_price(document: dict, *, kwh: float, kw: float, business_hours=range(7, 19), as_of=None,
                            max_lag_months: int = 4) -> dict:
    """Illustrative all-in market energy price ($/kWh) of a SYNTHETIC load profile; never a tariff or a bill.

    Profile: `kw` during Monday-Friday hours beginning in `business_hours` (EST, IESO market time; holidays count as
    the weekday they fall on) and a constant base load at all other hours, sized so the month's energy is `kwh`.
    For each window month, the published monthly energy level is scaled by its calendar month's shape factor
    (profile-weighted / time-weighted mean energy of the month's 48 heatmap bins), then that month's Class B Global
    Adjustment is added; the price is the mean of the window months' totals.
    """
    hours = sorted(set(business_hours))
    business = len(hours) * WEEKDAYS_PER_MONTH
    other = HOURS_PER_MONTH - business
    result = {
        "ok": False,
        "reason": None,
        "price_per_kwh": None,
        "profile": {
            "peak_kw": kw,
            "base_kw": None,
            "business_hours_beginning": hours,
            "days": "Monday-Friday",
            "time_basis": "EST (IESO market time)",
            "holidays": "counted as the weekday they fall on",
            "business_hours_per_month": round(business, 6),
            "other_hours_per_month": round(other, 6),
        },
        "window": None,
        "shape_factors": {},
        "months": [],
        "label": SYNTHETIC_LABEL,
    }

    def fail(reason: str) -> dict:
        result["reason"] = reason
        return result

    if not (_number(kwh) and _number(kw) and kwh > 0 and kw > 0):
        return fail("kwh and kw must be positive numbers")
    if not hours or any(not isinstance(hour, int) or not 0 <= hour <= 23 for hour in hours) or other <= 0:
        return fail("business_hours must be hours beginning 0-23 that leave other hours in the week")
    base_kw = (kwh - kw * business) / other
    result["profile"]["base_kw"] = round(base_kw, 6)
    if base_kw < 0:
        return fail(f"base load would be negative ({base_kw:.3f} kW): {kwh} kWh is less than {kw} kW for "
                    f"{business:.3f} business hours")
    if base_kw > kw:
        return fail(f"base load {base_kw:.3f} kW would exceed the business-hours load {kw} kW")
    metadata = document.get("metadata") if isinstance(document, dict) else None
    method = (metadata or {}).get("derivation_method")
    if method != ROLLING_METHOD:
        return fail(f"the market file is not the rolling observed history (derivation_method={method!r})")
    window = metadata.get("window") or {}
    monthly = document.get("monthly")
    surface = document.get("hourly_surface")
    try:
        start, end = _month_index(window["start_month"]), _month_index(window["end_month"])
    except (KeyError, TypeError, ValueError):
        return fail("bins or monthly records missing/invalid: no valid window")
    result["window"] = {"start_month": window["start_month"], "end_month": window["end_month"],
                        "months": window.get("months")}
    try:
        today = _as_date(as_of)
    except ValueError:
        return fail(f"invalid as_of {as_of!r}")
    lag = today.year * 12 + today.month - 1 - end
    if lag > max_lag_months:
        return fail(f"stale market history: the window ends {window['end_month']}, {lag} months before "
                    f"{today.isoformat()} (limit {max_lag_months})")
    expected = [_month_key(index) for index in range(start, end + 1)]
    if (len(expected) != WINDOW_MONTHS or window.get("months") != WINDOW_MONTHS or not isinstance(monthly, list)
            or [entry.get("month") if isinstance(entry, dict) else None for entry in monthly] != expected
            or not all(_number(entry.get("energy_arithmetic")) and _number(entry.get("ga_class_b"))
                       for entry in monthly)):
        return fail(f"bins or monthly records missing/invalid: expected {WINDOW_MONTHS} monthly records "
                    f"{window['start_month']}..{window['end_month']} with numeric energy and GA")
    bins: dict[tuple, dict] = {}
    for entry in surface if isinstance(surface, list) else []:
        if not isinstance(entry, dict):
            return fail("bins or monthly records missing/invalid: a bin is not an object")
        key = (entry.get("month"), entry.get("day_type"), entry.get("hour"))
        count, energy = entry.get("hours_count"), entry.get("avg_energy_price")
        if key in bins or not (isinstance(count, int) and count > 0 and _number(energy)):
            return fail(f"bins or monthly records missing/invalid: bin {key!r}")
        bins[key] = entry
    wanted = {(month, kind, hour) for month in range(1, 13) for kind in DAY_TYPES for hour in range(24)}
    if set(bins) != wanted:
        return fail(f"bins or monthly records missing/invalid: {len(bins)} valid bins, expected {len(wanted)}")
    factors = {}
    for month in range(1, 13):
        time_sum = time_hours = profile_sum = profile_weight = 0.0
        for kind in DAY_TYPES:
            for hour in range(24):
                entry = bins[(month, kind, hour)]
                load = kw if kind == "weekday" and hour in hours else base_kw
                count, energy = entry["hours_count"], entry["avg_energy_price"]
                time_sum += count * energy
                time_hours += count
                profile_sum += load * count * energy
                profile_weight += load * count
        time_weighted = time_sum / time_hours
        if time_weighted < MIN_TIME_WEIGHTED_ENERGY:
            return fail(f"calendar month {month}: time-weighted mean energy {time_weighted:.6f} $/kWh is below "
                        f"{MIN_TIME_WEIGHTED_ENERGY} $/kWh, so its shape factor is not meaningful")
        factors[month] = (profile_sum / profile_weight) / time_weighted
    totals = []
    for entry in monthly:
        factor = factors[int(entry["month"][5:7])]
        shaped = entry["energy_arithmetic"] * factor
        total = shaped + entry["ga_class_b"]
        totals.append(total)
        result["months"].append({"month": entry["month"], "energy_level": entry["energy_arithmetic"],
                                 "shape_factor": round(factor, 6), "shaped_energy": round(shaped, 6),
                                 "ga_class_b": entry["ga_class_b"], "total": round(total, 6)})
    result["shape_factors"] = {str(month): round(factor, 6) for month, factor in factors.items()}
    result["price_per_kwh"] = round(sum(totals) / len(totals), 6)
    result["ok"] = True
    return result
