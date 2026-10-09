"""
direct_energy_regulated.py -- Scraper for Direct Energy Regulated Services (Alberta).

Direct Energy Regulated Services (DERS) is the Rate of Last Resort (RoLR)
provider for the ATCO Electric service area. On January 1, 2025 the RoLR
replaced the Regulated Rate Option (RRO); its energy price is fixed for a
two-year term approved by the Alberta Utilities Commission (AUC).

Official sources (static HTML):
  - DERS residential and commercial regulated electricity pages, each stating
    "The Rate of Last Resort for Direct Energy Regulated Services' customers is
    <price> cents/kWh from <start>, to <end>." and naming the rate class.
  - Utilities Consumer Advocate default-rates table (Government of Alberta):
    required cross-check of price, unit and term for DERS / ATCO Electric.

DERS's daily administration charge is shown on its pages without an effective
date (and differs from its last dated rate schedule), so it is not emitted.
Delivery charges come from ATCO Electric's own tariff.

The RRO seed constants below are retained only as the labelled fallback (and
as database history); they are never presented as live rates.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.alberta_rolr import (
    DATE_PATTERN,
    UCA_DEFAULT_RATES_URL,
    RolrError,
    energy_component,
    html_text,
    make_period,
    parse_cents,
    parse_uca_table,
    require_current,
    rolr_record,
    uca_detail,
)

logger = logging.getLogger(__name__)

AESO_MARKET_URL = (
    "https://www.aeso.ca/market/market-and-system-reporting/"
    "hourly-pool-price-report/"
)

RESIDENTIAL_URL = "https://www.directenergy.ca/en/regulated/residential-electricity-rates"
COMMERCIAL_URL = "https://www.directenergy.ca/en/regulated/commercial-electricity-rates"
PAGE_URLS = {"residential": RESIDENTIAL_URL, "small_business": COMMERCIAL_URL}

UCA_RETAILER = "Direct Energy Regulated Services"
UCA_DISTRIBUTOR = "ATCO Electric"

# kind: (tariff_name, tariff_code, customer_class, DERS class label, eligibility)
CLASSES = {
    "residential": (
        "Rate of Last Resort - Residential", "RoLR-Res", "residential", "Residential Services",
        "Residential sites in the ATCO Electric service area that have not chosen a competitive "
        "retailer (DERS Residential Services class).",
    ),
    "small_business": (
        "Rate of Last Resort - Small Business", "RoLR-SB", "commercial", "Small General Service",
        "Small business sites in the ATCO Electric service area that have not chosen a competitive "
        "retailer (DERS Small General Service class). DERS's rate page does not print the "
        "consumption limit for RoLR eligibility.",
    ),
}

_SENTENCE = re.compile(
    r"The Rate of Last Resort for Direct Energy Regulated Services'? customers is "
    rf"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>\S+(?: per kWh)?) from (?P<start>{DATE_PATTERN}),? "
    rf"to (?P<end>{DATE_PATTERN})"
)

SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.directenergyregulatedservices.com/",
    "energy_rate": 0.1762,       # $/kWh -- typical monthly RRO rate
    "admin_fee_monthly": 5.95,   # $/month
}

SEED_COMMERCIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.directenergyregulatedservices.com/",
    "energy_rate": 0.1762,       # $/kWh -- same energy rate as residential
    "admin_fee_monthly": 7.95,   # $/month
}


def parse_ders_page(html: str, kind: str):
    """Return (cents, term, quoted sentence) from a DERS regulated electricity page."""
    text = html_text(html)
    label = CLASSES[kind][3]
    if label.casefold() not in text.casefold():
        raise RolrError(f"DERS page lacks the {label} class")
    hits = list(_SENTENCE.finditer(text))
    if not hits:
        raise RolrError("DERS RoLR price sentence missing")
    offers = {(parse_cents(h["value"], h["unit"]), make_period(h["start"], h["end"])) for h in hits}
    if len(offers) != 1:
        raise RolrError("DERS page states conflicting RoLR prices or terms")
    cents, period = offers.pop()
    return cents, period, hits[0].group(0)


def parse_sources(sources: dict[str, str], today: date) -> tuple[list[TariffRecord], list[str]]:
    """Build live RoLR records from fetched HTML; return (records, rejection reasons)."""
    try:
        uca = parse_uca_table(sources.get("uca") or "", today)
        uca_cents = uca.price(UCA_RETAILER, UCA_DISTRIBUTOR)
    except RolrError as exc:
        return [], [f"UCA cross-check failed: {exc}"]
    check = uca_detail(uca, UCA_RETAILER, UCA_DISTRIBUTOR)

    records: list[TariffRecord] = []
    rejections: list[str] = []
    for kind, url in PAGE_URLS.items():
        name, code, customer_class, label, eligibility = CLASSES[kind]
        try:
            if not sources.get(kind):
                raise RolrError("DERS page unavailable")
            cents, period, sentence = parse_ders_page(sources[kind], kind)
            if period != uca.period:
                raise RolrError(f"DERS term {period.label()} differs from UCA term {uca.period.label()}")
            require_current(period, today)
            if cents != uca_cents:
                raise RolrError(f"DERS {cents} cents/kWh differs from UCA {uca_cents} cents/kWh")
        except RolrError as exc:
            rejections.append(f"{name}: {exc}")
            continue
        detail = f"DERS {label} rate page: '{sentence}'"
        records.append(rolr_record(
            utility_name="Direct Energy Regulated Services",
            tariff_name=name,
            tariff_code=code,
            customer_class=customer_class,
            description=f"Rate of Last Resort default electricity supply ({label}) in the ATCO Electric service area.",
            eligibility=f"{eligibility} Service area: ATCO Electric (UCA default-rates table).",
            period=period,
            components=[energy_component(
                cents, period, source_url=url, source_detail=detail, uca_check=check,
            )],
            source_url=url,
            source_page=detail,
            notes=(
                "DERS also bills a daily administration charge; its current value is shown without "
                "an effective date, so it is not included."
            ),
        ))
    return records, rejections


class DirectEnergyRegulatedScraper(BaseScraper):
    """Scrape Direct Energy Regulated Services RoLR rates for Alberta."""

    def __init__(self):
        super().__init__(
            utility_name="Direct Energy Regulated Services",
            province="AB",
        )

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning(
                "Live scrape failed -- using seed data for "
                "Direct Energy Regulated Services"
            )
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Parse the DERS RoLR pages; the UCA table is a required cross-check."""
        try:
            sources = {"uca": self.fetch_page(UCA_DEFAULT_RATES_URL)}
        except Exception as exc:
            self.logger.warning("UCA default-rates page unavailable: %s", exc)
            return None
        for kind, url in PAGE_URLS.items():
            try:
                sources[kind] = self.fetch_page(url)
            except Exception as exc:
                self.logger.warning("DERS %s page unavailable: %s", kind, exc)
        try:
            records, rejections = parse_sources(sources, self._today())
        except Exception:
            self.logger.exception("DERS RoLR parse failed")
            return None
        for reason in rejections:
            self.logger.warning("DERS RoLR rejected -- %s", reason)
        if not records:
            return None
        return self.mark_live_parsed(records)

    @staticmethod
    def _today() -> date:
        return date.today()

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # -- Residential RRO -----------------------------------------------
        records.append(TariffRecord(
            utility_name="Direct Energy Regulated Services",
            province="AB",
            utility_type="electricity",
            tariff_name="Residential Regulated Rate Option",
            tariff_code="RRO-Res",
            customer_class="residential",
            rate_structure="market",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "Direct Energy Regulated Services provides the Regulated "
                "Rate Option (RRO) for the ATCO Electric service area. "
                "The energy rate changes monthly based on the AESO pool "
                "price plus a regulated risk premium. This seed value is "
                "a typical monthly rate -- actual rate varies each month. "
                "Distribution charges from ATCO Electric are separate. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="RRO Energy Charge",
                    charge_value=SEED_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    market_reference="AESO pool price",
                    market_source_url=AESO_MARKET_URL,
                    notes=(
                        "Regulated Rate Option energy charge -- varies "
                        "monthly based on AESO pool price"
                    ),
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Administration Fee",
                    charge_value=SEED_RESIDENTIAL["admin_fee_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly administration fee",
                ),
            ],
        ))

        # -- Commercial RRO ------------------------------------------------
        records.append(TariffRecord(
            utility_name="Direct Energy Regulated Services",
            province="AB",
            utility_type="electricity",
            tariff_name="Commercial Regulated Rate Option",
            tariff_code="RRO-Com",
            customer_class="commercial",
            rate_structure="market",
            effective_date=SEED_COMMERCIAL["effective_date"],
            source_url=SEED_COMMERCIAL["source_url"],
            confidence="medium",
            notes=(
                "Direct Energy Regulated Services commercial RRO for the "
                "ATCO Electric service area. Same energy rate structure as "
                "residential -- varies monthly with AESO pool price. "
                "Distribution charges from ATCO Electric are separate. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="RRO Energy Charge",
                    charge_value=SEED_COMMERCIAL["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    market_reference="AESO pool price",
                    market_source_url=AESO_MARKET_URL,
                    notes=(
                        "Regulated Rate Option energy charge -- varies "
                        "monthly based on AESO pool price"
                    ),
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Administration Fee",
                    charge_value=SEED_COMMERCIAL["admin_fee_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly administration fee",
                ),
            ],
        ))

        return records
