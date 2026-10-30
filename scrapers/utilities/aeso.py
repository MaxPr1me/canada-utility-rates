"""
aeso.py -- Scraper for Alberta Electric System Operator (AESO) pool price.

AESO is not a utility -- it is the independent system operator that runs Alberta's wholesale electricity market.
AESO publishes no customer tariff, so the record is a market reference: one value-less "Variable" energy component
(``charge_value=None`` plus a market reference and source URL), the same pattern as Ontario's market energy (Phase
6B). No pool price, average or estimate is stored in the live record; hourly observations belong to a market model,
never to a tariff.

The record counts as live only when both official AESO sources verify on the day of the run:

* the ETS Historical Pool Price report (CSV, no login) answers in the documented format and has recent posted
  hourly prices within the published $0.00-$999.99 range;
* the report's metadata PDF still defines the pool price (the time weighted average of the one-minute system marginal
  price, ISO rule 201.6) and carries a document date, which becomes the record's effective date.

Otherwise the labelled seed estimate is emitted instead (hidden by default on the site).

Sources (checked October 30, 2026; the old hourly-pool-price-report page on aeso.ca returns 404):
  http://ets.aeso.ca/ets_web/ip/Market/Reports/HistoricalPoolPriceReportServlet  (plain http only)
  http://ets.aeso.ca/Market/Reports/Manual/HelpText/historical-pool-price-metadata.pdf
"""

from __future__ import annotations

import csv
import io
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from scrapers.base import BaseScraper, RateComponent, TariffRecord

logger = logging.getLogger(__name__)

REPORT_URL = "http://ets.aeso.ca/ets_web/ip/Market/Reports/HistoricalPoolPriceReportServlet"
METADATA_URL = "http://ets.aeso.ca/Market/Reports/Manual/HelpText/historical-pool-price-metadata.pdf"
SOURCE_URL = METADATA_URL
MARKET_REFERENCE = "AESO pool price (Alberta wholesale market)"
CSV_HEADER = ["Date (HE)", "Price ($)", "30Ravg ($)", "AIL Demand (MW)"]
PRICE_FLOOR, PRICE_CAP = 0.0, 999.99
LOOKBACK_DAYS = 7
MAX_STALE_DAYS = 3
MIN_POSTED_HOURS = 24
METADATA_PHRASES = (
    "settlement price of one megawatt-hour of electric energy",
    "time weighted average of the one-minute system marginal price",
    "$ cad",
)

SEED_POOL_PRICE = {
    "effective_date": "2024-10-01",
    "source_url": SOURCE_URL,
    "average_pool_price": 0.0952,  # $/kWh -- recent average
}


class AESOVerificationError(ValueError):
    """An official AESO source is missing, changed shape or is out of date."""


def _today() -> date:
    return datetime.now(timezone.utc).date()


def report_csv_url(begin: date, end: date) -> str:
    """ETS report URL; the end date is exclusive."""
    return f"{REPORT_URL}?beginDate={begin:%m%d%Y}&endDate={end:%m%d%Y}&contentType=csv"


def parse_pool_price_csv(text: str) -> list[tuple[date, str, float]]:
    """Posted hourly prices as (date, hour-ending label, $/MWh).

    Hours not yet posted ("-") are skipped. A changed header, an unreadable row or a price outside the published
    range rejects the whole file.
    """
    rows = list(csv.reader(io.StringIO(text)))
    header_at = next((i for i, row in enumerate(rows) if [c.strip() for c in row] == CSV_HEADER), None)
    if header_at is None:
        raise AESOVerificationError("pool price CSV header not found")
    out: list[tuple[date, str, float]] = []
    for row in rows[header_at + 1:]:
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != len(CSV_HEADER):
            raise AESOVerificationError(f"unexpected pool price row: {row!r}")
        match = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4}) (0[1-9]|1\d|2[0-4])(\*?)", row[0].strip())
        if not match:
            raise AESOVerificationError(f"unreadable pool price hour label: {row[0]!r}")
        price_text = row[1].strip()
        if price_text == "-":
            continue
        try:
            price = float(price_text)
            hour_date = date(int(match.group(3)), int(match.group(1)), int(match.group(2)))
        except ValueError as exc:
            raise AESOVerificationError(f"unreadable pool price row: {row!r}") from exc
        if not PRICE_FLOOR <= price <= PRICE_CAP:
            raise AESOVerificationError(f"pool price {price} outside {PRICE_FLOOR}-{PRICE_CAP} $/MWh on {row[0]!r}")
        out.append((hour_date, match.group(4) + match.group(5), price))
    return out


def verify_recent_prices(prices: list[tuple[date, str, float]], today: date) -> date:
    """Require enough recent posted hours; returns the latest posted date."""
    if len(prices) < MIN_POSTED_HOURS:
        raise AESOVerificationError(f"only {len(prices)} posted hourly prices in the last {LOOKBACK_DAYS} days")
    latest = max(p[0] for p in prices)
    if latest > today:
        raise AESOVerificationError(f"pool price dated in the future: {latest}")
    if (today - latest).days > MAX_STALE_DAYS:
        raise AESOVerificationError(f"latest posted pool price is {latest}, more than {MAX_STALE_DAYS} days old")
    return latest


def parse_metadata(text: str, document_date: Optional[str]) -> str:
    """Check the metadata text still defines the pool price and return the document date (ISO)."""
    flat = " ".join(text.lower().split())
    missing = [phrase for phrase in METADATA_PHRASES if phrase not in flat]
    if missing:
        raise AESOVerificationError(f"pool price metadata no longer says: {missing[0]!r}")
    match = re.match(r"D:(\d{4})(\d{2})(\d{2})", document_date or "")
    if not match:
        raise AESOVerificationError("pool price metadata PDF carries no document date")
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def metadata_document(pdf_bytes: bytes) -> tuple[str, Optional[str]]:
    """(text, PDF modification date such as "D:20250528113723-06'00'")."""
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        info = pdf.metadata or {}
    return text, info.get("ModDate") or info.get("CreationDate")


class AESOScraper(BaseScraper):
    """AESO pool price market reference for Alberta (value-less; no customer tariff exists)."""

    def __init__(self):
        super().__init__(
            utility_name="Alberta Electric System Operator",
            province="AB",
        )

    def scrape(self) -> list[TariffRecord]:
        live = self._try_live_scrape()
        if live:
            return live
        self.logger.warning("Live verification failed -- using seed data for AESO")
        return self.mark_fallback(self._seed_data())

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        today = _today()
        try:
            csv_url = report_csv_url(today - timedelta(days=LOOKBACK_DAYS), today + timedelta(days=1))
            csv_text = self.fetch_bytes(csv_url).decode("utf-8", errors="replace")
            verify_recent_prices(parse_pool_price_csv(csv_text), today)
            text, document_date = metadata_document(self.fetch_bytes(METADATA_URL))
            effective = parse_metadata(text, document_date)
        except AESOVerificationError as exc:
            self.logger.warning("AESO pool price not verified: %s", exc)
            return None
        except Exception as exc:  # noqa: BLE001 - any fetch or PDF failure falls back to the labelled seed
            self.logger.warning("AESO pool price sources failed: %s", exc)
            return None
        return self.mark_live_parsed(self._market_reference(effective))

    def _market_reference(self, effective_date: str) -> list[TariffRecord]:
        return [TariffRecord(
            utility_name="Alberta Electric System Operator",
            province="AB",
            utility_type="electricity",
            tariff_name="AESO Pool Price Reference",
            tariff_code="POOL",
            customer_class="other",
            sub_class="market reference",
            rate_structure="market",
            pricing_method="market_based",
            market_reference=MARKET_REFERENCE,
            effective_date=effective_date,
            source_url=SOURCE_URL,
            source_page="Pool Price Metadata (ETS Historical Pool Price report)",
            confidence="high",
            notes=(
                "AESO publishes no customer tariff. Pool price is the hourly wholesale energy price, the time "
                "weighted average of the one-minute system marginal price (ISO rule 201.6), in $ CAD per MWh. It "
                "changes every hour, so no number is stored here (shown as Variable); observed prices belong to a "
                "market model, never to a tariff. It is an energy-only wholesale reference, not a retail rate: "
                "wires, retail energy (Rate of Last Resort or a contract), riders and fees are separate records. "
                "The effective date is the date of AESO's pool price metadata document. "
                "The record is live only while the ETS Historical Pool Price report posts current hourly prices."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="AESO Pool Price (Variable)",
                    charge_value=None,
                    charge_unit="$/MWh",
                    confidence="high",
                    market_reference=MARKET_REFERENCE,
                    market_source_url=REPORT_URL,
                    effective_date=effective_date,
                    source_url=SOURCE_URL,
                    source_detail="AESO ETS Historical Pool Price report and its metadata",
                    notes=(
                        "Hourly pool price, $0.00-$999.99 per MWh, set by the ISO for each settlement hour; "
                        "hour-ending, Alberta local time. No average or estimate is stored."
                    ),
                ),
            ],
        )]

    def _seed_data(self) -> list[TariffRecord]:
        return [TariffRecord(
            utility_name="Alberta Electric System Operator",
            province="AB",
            utility_type="electricity",
            tariff_name="AESO Pool Price Reference",
            customer_class="other",
            sub_class="market reference",
            rate_structure="market",
            effective_date=SEED_POOL_PRICE["effective_date"],
            source_url=SEED_POOL_PRICE["source_url"],
            confidence="medium",
            notes=(
                "Average AESO pool price. Real-time price varies hourly. "
                "This is a reference, not a retail rate."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="AESO Pool Price (Average)",
                    charge_value=SEED_POOL_PRICE["average_pool_price"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    market_reference="AESO pool price",
                    market_source_url=REPORT_URL,
                    notes=(
                        "Average AESO pool price. The actual pool price "
                        "varies hourly based on supply and demand in "
                        "Alberta's wholesale electricity market. This "
                        "value is a recent average used as a reference."
                    ),
                ),
            ],
        )]
