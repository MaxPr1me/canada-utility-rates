"""
market_pricing.py -- Utility to load and query Ontario IESO market pricing data.

Ontario commercial customers >= 50 kW pay market-based energy rates:
  HOEP (Hourly Ontario Energy Price) + GA (Global Adjustment)

This module provides access to the representative historical pricing
surface built from 5 years of IESO data.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MARKET_DATA_PATH = PROJECT_ROOT / "site" / "data" / "market_pricing_ontario.json"


def load_ontario_market_pricing() -> dict:
    """Load the Ontario IESO market pricing surface."""
    with open(MARKET_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_representative_rate(month: int, day_type: str, hour: int) -> dict:
    """
    Get the representative HOEP + GA rate for a specific time slot.

    Args:
        month: 1-12
        day_type: "weekday" or "weekend"
        hour: 0-23

    Returns:
        dict with avg_hoep, avg_ga, combined_energy_component
    """
    data = load_ontario_market_pricing()
    for entry in data["hourly_surface"]:
        if entry["month"] == month and entry["day_type"] == day_type and entry["hour"] == hour:
            return entry
    raise ValueError(f"No data for month={month}, day_type={day_type}, hour={hour}")


def get_monthly_average(month: int) -> dict:
    """Get the weighted average rate for a given month across all hours."""
    data = load_ontario_market_pricing()
    entries = [e for e in data["hourly_surface"] if e["month"] == month]
    # Weight weekday 5/7, weekend 2/7
    weekday_entries = [e for e in entries if e["day_type"] == "weekday"]
    weekend_entries = [e for e in entries if e["day_type"] == "weekend"]

    def avg(lst, key):
        return sum(e[key] for e in lst) / len(lst) if lst else 0

    wd_weight = 5 / 7
    we_weight = 2 / 7

    return {
        "month": month,
        "avg_hoep": round(avg(weekday_entries, "avg_hoep") * wd_weight + avg(weekend_entries, "avg_hoep") * we_weight, 4),
        "avg_ga": round(avg(weekday_entries, "avg_ga") * wd_weight + avg(weekend_entries, "avg_ga") * we_weight, 4),
        "combined": round(avg(weekday_entries, "combined_energy_component") * wd_weight + avg(weekend_entries, "combined_energy_component") * we_weight, 4),
    }


def get_market_tariff_metadata() -> dict:
    """
    Return metadata dict for market-based Ontario tariffs.
    Use this when storing tariff records for market-priced customer classes.
    """
    return {
        "pricing_method": "market_based",
        "formula": "HOEP + GA",
        "market_reference": "IESO",
        "history_window_years": 5,
        "ga_allocation": "Class B uniform per-kWh",
        "notes": "Representative modeled hourly price based on 5 years of IESO historical data. Actual customer bills use real-time HOEP and monthly GA.",
    }
