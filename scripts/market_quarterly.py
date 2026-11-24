"""Complete calendar quarters of a permanent monthly market history, for the Rate History tab's Market sub-tab.

Owner decision 50 (2026-11-23): a quarter (Q1 = January-March, ...) is published only when all three of its months are
complete in the permanent monthly history, and each measure is the hour-weighted (time-weighted) mean of its three
monthly values, sum(value x hours) / sum(hours). Every monthly value is the arithmetic mean of that month's hourly
prices, so the weighted mean reproduces the arithmetic mean over every hour of the quarter, to the precision the
monthly history stores; a plain mean of three months would count a short February like a 31-day month. A quarter
with a missing month is left out, never filled.

Province-neutral on purpose: each builder passes its own hour weights (its market's hour convention), measures and
per-quarter keys, so Ontario's Global Adjustment and eras never reach the Alberta file (Ontario and Alberta histories
stay separate). Values are $/kWh rounded to six decimals, and the document carries no wall-clock time, so an
unchanged history renders to identical bytes.
"""
from __future__ import annotations

import json
import re
from calendar import monthrange
from collections.abc import Callable, Iterable, Mapping, Sequence
from decimal import ROUND_HALF_UP, Decimal, localcontext
from typing import TypeVar

VERSION = 1
KIND = "market_quarterly"
DERIVATION_METHOD = "observed_quarterly_time_weighted"
UNIT = "$/kWh"
PLACES = Decimal("0.000001")
RULE = ("A quarter is published only when all three of its calendar months are complete in the permanent monthly "
        "history, and each value is the hour-weighted mean of its three monthly values, sum(value x hours) / "
        "sum(hours) (owner decision 50, 2026-11-23).")
MONTH_RE = re.compile(r"(\d{4})-(0[1-9]|1[0-2])")
QUARTER_RE = re.compile(r"(\d{4})Q([1-4])")

Row = TypeVar("Row")


class QuarterlyError(ValueError):
    """A month cannot enter a quarter; the builder publishes nothing."""


def _month(text: str) -> tuple[int, int]:
    match = MONTH_RE.fullmatch(text) if isinstance(text, str) else None
    if match is None:
        raise QuarterlyError(f"invalid month {text!r}; expected YYYY-MM")
    return int(match.group(1)), int(match.group(2))


def quarter_of(month: str) -> str:
    """'2025-05' -> '2025Q2'."""
    year, number = _month(month)
    return f"{year:04d}Q{(number - 1) // 3 + 1}"


def quarter_months(quarter: str) -> list[str]:
    """'2025Q2' -> ['2025-04', '2025-05', '2025-06']."""
    match = QUARTER_RE.fullmatch(quarter) if isinstance(quarter, str) else None
    if match is None:
        raise QuarterlyError(f"invalid quarter {quarter!r}; expected YYYYQn")
    year, index = int(match.group(1)), int(match.group(2))
    return [f"{year:04d}-{number:02d}" for number in range(3 * index - 2, 3 * index + 1)]


def complete_quarters(months: Iterable[str]) -> list[str]:
    """The quarters whose three months are all present, in chronological order."""
    present = set(months)
    quarters = sorted({quarter_of(month) for month in present})
    return [quarter for quarter in quarters if all(month in present for month in quarter_months(quarter))]


def hour_weighted_mean(values: Sequence[Decimal], hours: Sequence[int]) -> Decimal:
    """sum(value x hours) / sum(hours), unrounded."""
    if not values or len(values) != len(hours):
        raise QuarterlyError("every value needs exactly one hour weight")
    if any(isinstance(weight, bool) or not isinstance(weight, int) or weight <= 0 for weight in hours):
        raise QuarterlyError(f"hour weights must be positive whole numbers, found {list(hours)}")
    if any(not isinstance(value, Decimal) or not value.is_finite() for value in values):
        raise QuarterlyError(f"values must be finite decimals, found {list(values)}")
    with localcontext() as context:
        # A fixed precision far beyond the six published decimals, whatever context the caller set.
        context.prec = 40
        return sum((value * weight for value, weight in zip(values, hours)), Decimal(0)) / sum(hours)


def round_value(value: Decimal) -> Decimal:
    """Six decimals of $/kWh, ROUND_HALF_UP, like the site's market files; a rounded zero is never '-0'."""
    rounded = value.quantize(PLACES, rounding=ROUND_HALF_UP)
    return rounded.copy_abs() if rounded.is_zero() else rounded


def build_document(rows: Mapping[str, Row], *, province: str, source: str, weighting: str,
                   measures: Mapping[str, Callable[[Row], Decimal]], hours: Callable[[str, Row], int],
                   details: Callable[[list[Row]], dict]) -> dict:
    """The quarterly document of one province's permanent monthly history.

    rows maps every complete month ('YYYY-MM') to the province's own record; measures maps each published measure, in
    order, to the record's monthly value in $/kWh; hours gives a month's weight in that market's hour convention;
    details gives the province's own keys for a quarter from its three records, in month order. A history without
    one complete quarter is refused rather than published empty.
    """
    quarters = []
    for quarter in complete_quarters(rows):
        months = quarter_months(quarter)
        records = [rows[month] for month in months]
        weights = [hours(month, record) for month, record in zip(months, records)]
        entry = {"quarter": quarter, "start": f"{months[0]}-01",
                 "end": f"{months[-1]}-{monthrange(*_month(months[-1]))[1]:02d}", "months": months,
                 "hours": sum(weights)}
        for name, value in measures.items():
            entry[name] = round_value(hour_weighted_mean([value(record) for record in records], weights))
        extra = details(records)
        if set(extra) & set(entry):
            raise QuarterlyError(f"{quarter}: province keys {sorted(set(extra) & set(entry))} repeat quarter keys")
        entry.update(extra)
        quarters.append(entry)
    if not quarters:
        raise QuarterlyError("the monthly history holds no complete quarter")
    return {
        "version": VERSION,
        "kind": KIND,
        "province": province,
        "derivation_method": DERIVATION_METHOD,
        "unit": UNIT,
        "measures": list(measures),
        "source": source,
        "weighting": weighting,
        "rule": RULE,
        "first_quarter": quarters[0]["quarter"],
        "last_quarter": quarters[-1]["quarter"],
        "quarters": quarters,
    }


def _number(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def render(document: dict, *, indent: int | None, ensure_ascii: bool) -> bytes:
    """UTF-8 JSON with LF line ends and a final newline, in the calling builder's own style (indent=None is compact).

    Decimal values become JSON numbers; rendering the same document always gives the same bytes."""
    separators = (",", ":") if indent is None else (",", ": ")
    text = json.dumps(document, indent=indent, separators=separators, ensure_ascii=ensure_ascii, allow_nan=False,
                      default=_number)
    return (text + "\n").encode("utf-8")
