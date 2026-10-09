"""
epcor_energy_alberta.py -- Scraper for EPCOR Energy Alberta Rate of Last Resort.

EPCOR Energy Alberta GP Inc. (EEA) is the Rate of Last Resort (RoLR) provider
for the EPCOR Distribution & Transmission Inc. (City of Edmonton) and
FortisAlberta Inc. service areas. On January 1, 2025 the RoLR replaced the
Regulated Rate Option (RRO); its energy price is fixed for a two-year term
approved by the Alberta Utilities Commission (AUC).

Official sources, per service area (static HTML and text PDFs):
  - EPCOR residential RoLR page: term and price ("Provided by EPCOR").
  - EPCOR regulated business page: the "Small commercial" RoLR card (term and
    price) and the small-business consumption limit.
  - EEA Regulated Rate Tariff price schedule PDF, discovered from the area's
    electricity tariffs page: Residential and Commercial Service energy and
    administration charges, applicability and effective date.
  - Utilities Consumer Advocate default-rates table (Government of Alberta):
    required cross-check for EPCOR / EPCOR Distribution and EPCOR /
    FortisAlberta Inc.

Administration charges differ by area, so each area has its own records.
Any provider/UCA disagreement, unit change, credit-valued administration
charge or out-of-term date fails closed for the affected area or class.
Delivery charges come from the wires owner's own tariff.

The RRO seed constants below are retained only as the labelled fallback (and
as database history); they are never presented as live rates.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from decimal import Decimal
from typing import Optional
from urllib.parse import urljoin

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.alberta_rolr import (
    DATE_PATTERN,
    UCA_DEFAULT_RATES_URL,
    RolrError,
    energy_component,
    html_text,
    make_period,
    normalize_text,
    parse_cents,
    parse_date,
    parse_uca_table,
    require_current,
    rolr_record,
    uca_detail,
)
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

logger = logging.getLogger(__name__)

AESO_MARKET_URL = (
    "https://www.aeso.ca/market/market-and-system-reporting/"
    "hourly-pool-price-report/"
)

SOURCE_URL = (
    "https://www.epcor.com/products-services/power/rates-tariffs/"
    "Pages/regulated-rate-option.aspx"
)

_EPCOR = "https://www.epcor.com/ca/en/ab"
UCA_RETAILER = "EPCOR"
AREAS = {
    "edti": {
        "label": "EPCOR Distribution area",
        "code": "EDTI",
        "uca_distributor": "EPCOR Distribution",
        "service_area": "EPCOR Distribution & Transmission Inc. service area (City of Edmonton)",
        "home_url": f"{_EPCOR}/edmonton/start-services/home/rate-of-last-resort.html",
        "business_url": f"{_EPCOR}/edmonton/start-services/business/regulated.html",
        "tariffs_url": f"{_EPCOR}/edmonton/account/rates/special-fees-charges/electricity-tariffs.html",
        "file_key": "edmonton",
        "footer": "EEA Regulated Rate Tariff (EPCOR Distribution & Transmission Inc.)",
    },
    "fortis": {
        "label": "FortisAlberta area",
        "code": "FAI",
        "uca_distributor": "FortisAlberta",
        "service_area": "FortisAlberta Inc. service area (outside the City of Edmonton)",
        "home_url": f"{_EPCOR}/other/start-services/home/rate-of-last-resort.html",
        "business_url": f"{_EPCOR}/other/start-services/business/regulated.html",
        "tariffs_url": f"{_EPCOR}/other/account/rates/special-fees-charges/electricity-tariffs.html",
        "file_key": "fortis",
        "footer": "EEA Regulated Rate Tariff (FortisAlberta Inc.)",
    },
}

PAGE_LABELS = {"home": "EPCOR RoLR page", "business": "EPCOR regulated business page"}

# kind: (price schedule section, tariff_name, tariff_code, customer_class, provider page key)
CLASSES = {
    "residential": ("Residential Service", "Rate of Last Resort - Residential", "RoLR-Res", "residential", "home"),
    "small_business": (
        "Commercial Service", "Rate of Last Resort - Small Business", "RoLR-SB", "commercial", "business",
    ),
}

_HOME_TERM = re.compile(
    rf"fixed rate (?:for a two year period )?from ({DATE_PATTERN})\s*(?:to|-)\s*({DATE_PATTERN})"
)
_HOME_PRICE = re.compile(r"Rate of Last Resort Provided by EPCOR (\d+(?:\.\d+)?)\s*(\S+ per kWh)")
_BUSINESS_CARD = re.compile(
    rf"Rate of Last Resort Small commercial Current rate period: (?P<start>{DATE_PATTERN})\s*-\s*"
    rf"(?P<end>{DATE_PATTERN}) (?P<value>\d+(?:\.\d+)?)\s*(?P<unit>\S+ per kWh)",
    re.I,
)
_SMALL_BUSINESS_LIMIT = re.compile(
    r"Small businesses\s*:?\s*use less than (\d[\d,]*) kWh of electricity per year"
)
_SECTION = re.compile(
    r"Price Schedule (?P<name>[A-Z][A-Za-z ]*? Service) Applicable: (?P<applicable>.+?) "
    r"Price: (?P<price>.+?) Regulations:"
)

SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": SOURCE_URL,
    "energy_rate": 0.1738,       # $/kWh
    "admin_fee_monthly": 5.95,   # $/month
}

SEED_COMMERCIAL = {
    "effective_date": "2024-10-01",
    "source_url": SOURCE_URL,
    "energy_rate": 0.1738,       # $/kWh
    "admin_fee_monthly": 7.95,   # $/month
}


def parse_home_page(html: str):
    """Return (cents, term, quote) from an EPCOR residential RoLR page."""
    text = html_text(html)
    term_hits = list(_HOME_TERM.finditer(text))
    price_hits = list(_HOME_PRICE.finditer(text))
    terms = {make_period(m.group(1), m.group(2)) for m in term_hits}
    prices = {parse_cents(m.group(1), m.group(2)) for m in price_hits}
    if len(terms) != 1 or len(prices) != 1:
        raise RolrError(f"EPCOR RoLR page term/price missing or inconsistent ({len(terms)} terms, {len(prices)} prices)")
    quote = f"'{term_hits[0].group(0)}'; '{price_hits[0].group(0)}'"
    return prices.pop(), terms.pop(), quote


def parse_business_page(html: str):
    """Return (cents, term, quote, small-business kWh/year limit or None) from an EPCOR business page."""
    text = html_text(html)
    hits = list(_BUSINESS_CARD.finditer(text))
    cards = {(parse_cents(m["value"], m["unit"]), make_period(m["start"], m["end"])) for m in hits}
    if len(cards) != 1:
        raise RolrError(f"EPCOR Small commercial RoLR card missing or inconsistent ({len(cards)} variants)")
    cents, period = cards.pop()
    limit = _SMALL_BUSINESS_LIMIT.search(text)
    return cents, period, f"'{hits[0].group(0)}'", int(limit.group(1).replace(",", "")) if limit else None


def schedule_candidates(html: str, area_key: str, today: date) -> list[str]:
    """Area price-schedule PDF links dated (by file name) on or before today, newest first."""
    area = AREAS[area_key]
    dated: dict[str, date] = {}
    for anchor in parse_html(html).find_all("a", href=True):
        href = anchor["href"].strip()
        match = re.search(r"/regulated-rate-tariffs/((\d{4})-(\d{2})[-_][^/]*\.pdf)$", href)
        if not match or area["file_key"] not in match.group(1).casefold():
            continue
        try:
            month = date(int(match.group(2)), int(match.group(3)), 1)
        except ValueError:
            continue
        if month <= today:
            dated[urljoin(area["tariffs_url"], href)] = month
    return sorted(dated, key=lambda url: dated[url], reverse=True)


def parse_price_schedule(pages: list[DocumentPage], area_key: str, today: date) -> dict:
    """Validate a complete, current EEA price schedule for the area and split its sections."""
    area = AREAS[area_key]
    if not pages:
        raise RolrError("price schedule has no readable pages")
    footer = re.compile(re.escape(area["footer"]) + rf" Page (\d+) of (\d+) Effective Date: ({DATE_PATTERN})")
    numbers: list[int] = []
    totals: set[int] = set()
    dates: set[date] = set()
    sections: dict[str, dict] = {}
    for page in pages:
        text = normalize_text(page.text)
        hit = footer.search(text)
        if not hit:
            raise RolrError(f"PDF page {page.page_number} is not part of the {area['footer']} price schedule")
        numbers.append(int(hit.group(1)))
        totals.add(int(hit.group(2)))
        dates.add(parse_date(hit.group(3)))
        for section in _SECTION.finditer(text):
            if section["name"] in sections:
                raise RolrError(f"duplicate {section['name']} section")
            sections[section["name"]] = {
                "page": page.page_number, "applicable": section["applicable"], "price": section["price"],
            }
    if len(totals) != 1 or sorted(numbers) != list(range(1, max(totals) + 1)):
        raise RolrError("price schedule pages are incomplete")
    if len(dates) != 1:
        raise RolrError("price schedule pages carry different effective dates")
    effective = dates.pop()
    if effective > today:
        raise RolrError(f"price schedule effective {effective.isoformat()} is in the future")
    return {"effective": effective, "sections": sections}


def parse_section_charges(section: dict) -> dict:
    """Energy (cents/kWh) and administration ($/Day/Site) charges of one price-schedule section."""
    energy = re.search(r"Energy Charge (\S+) \(([^)]*)\)", section["price"])
    admin = re.search(r"Administration Charge (\(?\$?[\d.]+\)?) \(([^)]*)\)", section["price"])
    if not energy or not admin:
        raise RolrError("energy or administration charge missing")
    cents = parse_cents(energy.group(1), energy.group(2))
    if admin.group(2) != "$/Day/Site":
        raise RolrError(f"administration charge unit {admin.group(2)!r} is not $/Day/Site")
    if admin.group(1).startswith("("):
        raise RolrError(f"administration charge {admin.group(1)} is printed as a credit")
    if not re.fullmatch(r"\$\d+\.\d+", admin.group(1)):
        raise RolrError(f"administration charge {admin.group(1)!r} unreadable")
    applicable = re.sub(r"^\d+\.\s*", "", section["applicable"]).strip()
    return {
        "cents": cents, "admin": Decimal(admin.group(1)[1:]),
        "energy_text": energy.group(0), "admin_text": admin.group(0),
        # Rejoin words hyphenated across PDF line breaks ("single- phase").
        "applicable": re.sub(r"(?<=[a-z])- (?=[a-z])", "-", applicable),
    }


def parse_sources(sources: dict, today: date) -> tuple[list[TariffRecord], list[str]]:
    """Build live RoLR records per service area.

    ``sources`` holds 'uca' plus, per area key, '<area>_home' and '<area>_business'
    HTML and '<area>_schedule' = (pdf_url, pages).
    """
    try:
        uca = parse_uca_table(sources.get("uca") or "", today)
    except RolrError as exc:
        return [], [f"UCA cross-check failed: {exc}"]

    records: list[TariffRecord] = []
    rejections: list[str] = []
    for area_key, area in AREAS.items():
        try:
            uca_cents = uca.price(UCA_RETAILER, area["uca_distributor"])
            check = uca_detail(uca, UCA_RETAILER, area["uca_distributor"])
            schedule_url, pages = sources.get(f"{area_key}_schedule") or (None, None)
            if not pages:
                raise RolrError("price schedule unavailable")
            schedule = parse_price_schedule(pages, area_key, today)
        except RolrError as exc:
            rejections.append(f"{area['label']}: {exc}")
            continue
        effective = schedule["effective"]
        for kind, (section_name, name, code, customer_class, page_key) in CLASSES.items():
            tariff_name = f"{name} ({area['label']})"
            try:
                html = sources.get(f"{area_key}_{page_key}")
                if not html:
                    raise RolrError(f"EPCOR {page_key} page unavailable")
                if page_key == "home":
                    cents, period, quote = parse_home_page(html)
                    limit = None
                else:
                    cents, period, quote, limit = parse_business_page(html)
                if period != uca.period:
                    raise RolrError(f"EPCOR term {period.label()} differs from UCA term {uca.period.label()}")
                require_current(period, today)
                section = schedule["sections"].get(section_name)
                if not section:
                    raise RolrError(f"{section_name} missing from the price schedule")
                charges = parse_section_charges(section)
                if not cents == charges["cents"] == uca_cents:
                    raise RolrError(
                        f"EPCOR page {cents}, price schedule {charges['cents']} and UCA {uca_cents} cents/kWh disagree"
                    )
            except RolrError as exc:
                rejections.append(f"{tariff_name}: {exc}")
                continue

            page_url = area[f"{page_key}_url"]
            pdf_detail = (
                f"EEA price schedule ({area['footer']}), effective {effective:%B} {effective.day}, "
                f"{effective.year}, PDF page {section['page']} ({section_name})"
            )
            components = [
                energy_component(
                    cents, period, source_url=page_url,
                    source_detail=f"{PAGE_LABELS[page_key]}: {quote}; {pdf_detail}: '{charges['energy_text']}'",
                    uca_check=check,
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="RoLR Administration Charge",
                    charge_value=float(charges["admin"]),
                    charge_unit="$/day",
                    effective_date=effective.isoformat(),
                    source_url=schedule_url,
                    source_detail=f"{pdf_detail}: '{charges['admin_text']}'",
                    confidence="high",
                    notes="Printed as $/Day/Site (per site, per day); no end date is printed.",
                ),
            ]
            records.append(rolr_record(
                utility_name="EPCOR Energy Alberta",
                tariff_name=tariff_name,
                tariff_code=f"{code}-{area['code']}",
                customer_class=customer_class,
                description=(
                    f"Rate of Last Resort default electricity supply ({section_name}) in the "
                    f"{area['service_area']}."
                ),
                eligibility=f"{charges['applicable']} Service area: {area['service_area']}.",
                period=period,
                components=components,
                source_url=page_url,
                source_page=f"{PAGE_LABELS[page_key]}: {quote}; {pdf_detail}",
                notes=(
                    "EPCOR publishes separate price schedules for the EPCOR Distribution and FortisAlberta "
                    "service areas; their administration charges differ, so each area has its own record."
                ),
                usage_max=float(limit) if limit else None,
                usage_unit="kWh/year" if limit else None,
            ))
    return records, rejections


class EPCOREnergyAlbertaScraper(BaseScraper):
    """Scrape EPCOR Energy Alberta RoLR rates (EPCOR Distribution and FortisAlberta areas)."""

    def __init__(self):
        super().__init__(
            utility_name="EPCOR Energy Alberta",
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
                "EPCOR Energy Alberta"
            )
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Parse both service areas; the UCA table is a required cross-check."""
        try:
            sources: dict = {"uca": self.fetch_page(UCA_DEFAULT_RATES_URL)}
        except Exception as exc:
            self.logger.warning("UCA default-rates page unavailable: %s", exc)
            return None
        today = self._today()
        for area_key, area in AREAS.items():
            for page_key in ("home", "business"):
                try:
                    sources[f"{area_key}_{page_key}"] = self.fetch_page(area[f"{page_key}_url"])
                except Exception as exc:
                    self.logger.warning("EPCOR %s %s page unavailable: %s", area_key, page_key, exc)
            try:
                candidates = schedule_candidates(self.fetch_page(area["tariffs_url"]), area_key, today)
            except Exception as exc:
                self.logger.warning("EPCOR %s tariffs page unavailable: %s", area_key, exc)
                continue
            for url in candidates[:3]:
                try:
                    pages = self._pdf_pages(self.fetch_bytes(url))
                    parse_price_schedule(pages, area_key, today)
                except Exception as exc:
                    self.logger.warning("EPCOR %s price schedule %s skipped: %s", area_key, url, exc)
                    continue
                sources[f"{area_key}_schedule"] = (url, pages)
                break
        try:
            records, rejections = parse_sources(sources, today)
        except Exception:
            self.logger.exception("EPCOR RoLR parse failed")
            return None
        for reason in rejections:
            self.logger.warning("EPCOR RoLR rejected -- %s", reason)
        if not records:
            return None
        return self.mark_live_parsed(records)

    @staticmethod
    def _pdf_pages(data: bytes) -> list[DocumentPage]:
        return extract_pdf_pages(data)

    @staticmethod
    def _today() -> date:
        return date.today()

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # -- Residential RRO -----------------------------------------------
        records.append(TariffRecord(
            utility_name="EPCOR Energy Alberta",
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
                "EPCOR Energy Alberta provides the Regulated Rate Option "
                "(RRO) for the EPCOR Distribution (Edmonton) service area. "
                "The energy rate changes monthly based on the AESO pool "
                "price plus a regulated risk premium. Distribution charges "
                "from EPCOR Distribution are separate. "
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
            utility_name="EPCOR Energy Alberta",
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
                "EPCOR Energy Alberta commercial RRO for the Edmonton "
                "service area. Same energy rate structure as residential "
                "-- varies monthly with AESO pool price. Distribution "
                "charges from EPCOR Distribution are separate. "
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
