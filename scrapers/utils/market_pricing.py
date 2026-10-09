"""
market_pricing.py -- Load and query the Ontario legacy market history surface.

Since May 1, 2025, Ontario customers on market prices pay the hourly Ontario Electricity Market Price
(OEMP, the "Ontario Price" = Day-Ahead Ontario Zonal Price + Load Forecast Deviation Adjustment) plus the
Global Adjustment (Class B: monthly rate per kWh; Class A: by peak demand factor).

site/data/market_pricing_ontario.json is built by scripts/generate_market_pricing.py from official IESO
history: 576 bins (month x weekday/weekend x hour) of observed averages of the legacy Hourly Ontario Energy
Price (HOEP, retired April 30, 2025) and the Class B Global Adjustment actual monthly rates over full calendar
years (2020-2024 by default), in $/kWh. They are legacy-market context only, not a tariff or a forecast.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MARKET_DATA_PATH = PROJECT_ROOT / "site" / "data" / "market_pricing_ontario.json"
OBSERVED_METHOD_RE = re.compile(r"^observed_legacy_hoep_\d{4}_\d{4}_average$")
PRICE_FIELDS = ("avg_energy_price", "avg_ga_class_b", "combined")


def load_ontario_market_pricing(path: Path = MARKET_DATA_PATH) -> dict:
    """Load the observed legacy surface; reject files that are not built from IESO observations."""
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
        dict with hours_count and avg_energy_price (legacy HOEP), avg_ga_class_b, combined ($/kWh)
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
            "Energy is billed at the hourly Ontario Price plus Global Adjustment. The Market Pricing view "
            "shows legacy HOEP history (2020-2024; the HOEP retired April 30, 2025) with Class B Global "
            "Adjustment for context only; it is not a tariff value."
        ),
    }
