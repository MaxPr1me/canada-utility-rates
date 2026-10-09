"""
alberta_rolr.py -- Shared helpers for Alberta Rate of Last Resort (RoLR) scrapers.

On January 1, 2025 the Rate of Last Resort replaced the Regulated Rate Option
as Alberta's default electricity supply for customers without a competitive
retail contract. Each RoLR provider's energy price is fixed for a two-year
term approved by the Alberta Utilities Commission (AUC).

The Utilities Consumer Advocate (UCA, Government of Alberta) default-rates page
publishes every provider's approved price by distributor service area. Provider
scrapers use that table as a required cross-check of their own official
source: a missing or reshaped table, a unit other than cents/kWh, a missing
term, a term that does not cover today, or any provider/UCA price difference
fails closed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from scrapers.base import RateComponent, TariffRecord
from scrapers.utils.parsing import parse_html

UCA_DEFAULT_RATES_URL = (
    "https://ucahelps.alberta.ca/utility-choices/current-rates-and-pricing/default-rates/"
)

_MONTHS = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)
DATE_PATTERN = (
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}"
)
_CENTS_UNIT = re.compile(r"(?:¢|cents?)\s*(?:/|per)\s*kWh", re.I)

COMMON_NOTE = (
    "The Rate of Last Resort (RoLR) replaced the Regulated Rate Option on January 1, 2025 as "
    "Alberta's default electricity supply for eligible customers without a competitive retail "
    "contract; its energy price is fixed for a two-year term approved by the Alberta Utilities "
    "Commission. The Rate of Last Resort Regulation includes a 0.1 cents/kWh consumer-awareness "
    "surcharge in that price, so it is not a separate charge. Transmission and distribution "
    "(delivery) charges, distributor riders and local access fees are billed under the wires "
    "owner's own tariff and are not part of this record."
)


class RolrError(ValueError):
    """A required RoLR fact is missing, inconsistent or out of date."""


@dataclass(frozen=True)
class RolrPeriod:
    start: date
    end: date

    def covers(self, today: date) -> bool:
        return self.start <= today <= self.end

    def label(self) -> str:
        return f"{_long(self.start)} to {_long(self.end)}"


@dataclass(frozen=True)
class UcaRolrTable:
    period: RolrPeriod
    caption: str
    prices: dict[tuple[str, str], Decimal]  # (retailer, distributor) -> cents/kWh

    def entry(self, retailer: str, distributor: str) -> tuple[str, str, Decimal]:
        hits = [
            (name, area, cents) for (name, area), cents in self.prices.items()
            if retailer.casefold() in name.casefold() and distributor.casefold() in area.casefold()
        ]
        if len(hits) != 1:
            raise RolrError(f"UCA table has {len(hits)} entries for {retailer} / {distributor}")
        return hits[0]

    def price(self, retailer: str, distributor: str) -> Decimal:
        return self.entry(retailer, distributor)[2]


def _long(day: date) -> str:
    return f"{day:%B} {day.day}, {day.year}"


def normalize_text(text: str) -> str:
    """Normalize dashes, quotes and spacing so official wording can be matched."""
    for old, new in (
        ("\xa0", " "), ("\u200b", ""), ("\u2013", "-"), ("\u2014", "-"), ("\u2212", "-"),
        ("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u20b5", "¢"),
    ):
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


def html_text(html: str) -> str:
    """Visible page text (scripts and styles removed), normalized."""
    soup = parse_html(html)
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    return normalize_text(soup.get_text(" ", strip=True))


def parse_date(text: str) -> date:
    """Parse 'January 1, 2025', 'Jan. 1, 2025' or 'Dec. 31 2026'."""
    match = re.fullmatch(r"([A-Za-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})", normalize_text(text))
    if not match:
        raise RolrError(f"unreadable date {text!r}")
    word = match.group(1).casefold()
    months = [i for i, name in enumerate(_MONTHS, 1) if len(word) >= 3 and name.startswith(word)]
    if len(months) != 1:
        raise RolrError(f"unreadable month in {text!r}")
    try:
        return date(int(match.group(3)), months[0], int(match.group(2)))
    except ValueError as exc:
        raise RolrError(f"invalid date {text!r}") from exc


def make_period(start_text: str, end_text: str) -> RolrPeriod:
    period = RolrPeriod(parse_date(start_text), parse_date(end_text))
    if period.start >= period.end:
        raise RolrError(f"RoLR term {period.label()} is not a valid range")
    return period


def require_current(period: RolrPeriod, today: date) -> None:
    if today < period.start:
        raise RolrError(f"RoLR term {period.label()} has not started on {today.isoformat()}")
    if today > period.end:
        raise RolrError(f"RoLR term {period.label()} ended before {today.isoformat()}; no newer price published")


def parse_cents(value: str, unit: str) -> Decimal:
    """Validate a published cents/kWh price (any other unit fails closed)."""
    if not _CENTS_UNIT.fullmatch(normalize_text(unit)):
        raise RolrError(f"RoLR price unit {unit!r} is not cents/kWh")
    try:
        cents = Decimal(value)
    except InvalidOperation as exc:
        raise RolrError(f"unreadable RoLR price {value!r}") from exc
    if not Decimal("1") <= cents <= Decimal("100"):
        raise RolrError(f"RoLR price {cents} cents/kWh outside the plausible range")
    return cents


def cents_to_dollars(cents: Decimal) -> float:
    return float((cents / Decimal(100)).quantize(Decimal("0.000001")))


def fmt_cents(cents: Decimal) -> str:
    return format(cents.normalize(), "f")


def _table_grid(table) -> list[list[str]]:
    rows = []
    for tr in table.find_all("tr"):
        cells: list[str] = []
        for cell in tr.find_all(["td", "th"]):
            try:
                span = max(int(cell.get("colspan", 1)), 1)
            except ValueError:
                span = 1
            cells.extend([normalize_text(cell.get_text(" ", strip=True))] * span)
        if cells:
            rows.append(cells)
    return rows


def _parse_uca_grid(grid: list[list[str]]) -> UcaRolrTable:
    caption = grid[0][0]
    if not _CENTS_UNIT.search(caption):
        raise RolrError(f"UCA RoLR table unit is not cents/kWh: {caption!r}")
    term = re.search(rf"({DATE_PATTERN})\s*-\s*({DATE_PATTERN})", caption)
    if not term:
        raise RolrError(f"UCA RoLR table term missing: {caption!r}")
    period = make_period(term.group(1), term.group(2))
    rows = {row[0].casefold(): row for row in grid[1:]}
    retailers, distributors = rows.get("retailer"), rows.get("distributor")
    price_rows = [row for row in grid[1:] if row[0].casefold() not in ("retailer", "distributor")]
    if not retailers or not distributors or len(price_rows) != 1:
        raise RolrError("UCA RoLR table needs Retailer, Distributor and exactly one price row")
    price_row = price_rows[0]
    if not len(retailers) == len(distributors) == len(price_row) or len(price_row) < 2:
        raise RolrError("UCA RoLR table columns are misaligned")
    row_date = re.search(DATE_PATTERN, price_row[0])
    if row_date and parse_date(row_date.group(0)) != period.end:
        raise RolrError(f"UCA price-row label {price_row[0]!r} differs from the table term")
    prices: dict[tuple[str, str], Decimal] = {}
    for retailer, distributor, cell in zip(retailers[1:], distributors[1:], price_row[1:]):
        if not re.fullmatch(r"\d{1,3}\.\d{1,4}", cell):
            raise RolrError(f"UCA RoLR price {cell!r} unreadable")
        prices[(retailer, distributor)] = parse_cents(cell, "cents/kWh")
    return UcaRolrTable(period, caption, prices)


def parse_uca_table(html: str, today: date) -> UcaRolrTable:
    """Return the UCA RoLR table whose published term covers ``today``."""
    soup = parse_html(html)
    page_text = normalize_text(soup.get_text(" ", strip=True))
    grids = [g for g in (_table_grid(t) for t in soup.find_all("table"))
             if g and "rate of last resort" in g[0][0].casefold()]
    if not grids:
        raise RolrError("UCA RoLR table not found")
    tables = [_parse_uca_grid(grid) for grid in grids]
    for until in re.findall(rf"RoLR will be in place until ({DATE_PATTERN})", page_text):
        if parse_date(until) not in {table.period.end for table in tables}:
            raise RolrError(f"UCA text says the RoLR is in place until {until}, which no table term matches")
    current = [table for table in tables if table.period.covers(today)]
    if len(current) != 1:
        terms = ", ".join(table.period.label() for table in tables)
        raise RolrError(f"no single UCA RoLR term covers {today.isoformat()} (published: {terms})")
    return current[0]


def uca_detail(table: UcaRolrTable, retailer: str, distributor: str) -> str:
    name, area, cents = table.entry(retailer, distributor)
    return f"UCA default-rates table '{table.caption}': {name} / {area} {fmt_cents(cents)} cents/kWh"


def energy_component(
    cents: Decimal,
    period: RolrPeriod,
    *,
    source_url: str,
    source_detail: str,
    uca_check: str,
    notes: str = "",
) -> RateComponent:
    return RateComponent(
        component_type="energy",
        component_name="RoLR Energy Charge",
        charge_value=cents_to_dollars(cents),
        charge_unit="$/kWh",
        effective_date=period.start.isoformat(),
        end_date=period.end.isoformat(),
        source_url=source_url,
        source_detail=source_detail,
        confidence="high",
        notes=(
            f"Fixed RoLR energy price: {fmt_cents(cents)} cents/kWh for {period.label()}. "
            f"Cross-checked: {uca_check} ({UCA_DEFAULT_RATES_URL}). {notes}"
        ).strip(),
    )


def rolr_record(
    *,
    utility_name: str,
    tariff_name: str,
    tariff_code: str,
    customer_class: str,
    description: str,
    eligibility: str,
    period: RolrPeriod,
    components: list[RateComponent],
    source_url: str,
    source_page: str,
    notes: str,
    confidence: str = "high",
    usage_max: Optional[float] = None,
    usage_unit: Optional[str] = None,
) -> TariffRecord:
    """Assemble a flat regulated RoLR tariff dated by its latest required component."""
    effective = max(c.effective_date for c in components if c.effective_date)
    return TariffRecord(
        utility_name=utility_name,
        province="AB",
        utility_type="electricity",
        tariff_name=tariff_name,
        tariff_code=tariff_code,
        customer_class=customer_class,
        description=description,
        eligibility=eligibility,
        usage_max=usage_max,
        usage_unit=usage_unit,
        rate_structure="flat",
        pricing_method="regulated",
        effective_date=effective,
        end_date=period.end.isoformat(),
        source_url=source_url,
        source_page=source_page,
        confidence=confidence,
        notes=f"{notes} {COMMON_NOTE}".strip(),
        components=components,
    )
