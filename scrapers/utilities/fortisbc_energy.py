"""
fortisbc_energy.py — Scraper for FortisBC Energy natural gas rates (BC).

FortisBC Energy Inc. is the primary natural gas distributor in British
Columbia, serving over one million customers.

Official sources:
  https://www.fortisbc.com/accounts/billing-rates/natural-gas-rates/residential-rates  (Rate 1)
  https://www.fortisbc.com/accounts/billing-rates/natural-gas-rates/business-rates     (Rates 2 and 3)
  https://www2.gov.bc.ca/gov/content/taxes/sales-taxes/motor-fuel-carbon-tax          (carbon tax status)

BC gas rates are regulated by the British Columbia Utilities Commission (BCUC).
FortisBC uses GJ as the primary billing unit; the basic charge is published per day.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

RATES_BASE_URL = "https://www.fortisbc.com/accounts/billing-rates/natural-gas-rates/"
PAGE_URLS = {
    "residential": RATES_BASE_URL + "residential-rates",
    "business": RATES_BASE_URL + "business-rates",
    "carbon": "https://www2.gov.bc.ca/gov/content/taxes/sales-taxes/motor-fuel-carbon-tax",
}

MAINLAND = r"Mainland and Vancouver Island \(including North and South Interior, Whistler(?: and Revelstoke)?\)"
FORT_NELSON = r"Fort Nelson"
OTHER_AREAS = r"Fort Nelson|Mainland and Vancouver Island \(|Revelstoke \("


@dataclass(frozen=True)
class AreaClassSpec:
    rate: str               # "1", "2" or "3"
    page: str               # PAGE_URLS key
    area_pattern: str
    area_label: str
    tariff_name: str
    customer_class: str


CLASSES = (
    AreaClassSpec("1", "residential", MAINLAND, "Mainland and Vancouver Island (including North and South Interior, Whistler)",
                  "Residential — Rate 1", "residential"),
    AreaClassSpec("1", "residential", FORT_NELSON, "Fort Nelson", "Residential — Rate 1 (Fort Nelson)", "residential"),
    AreaClassSpec("2", "business", MAINLAND, "Mainland and Vancouver Island (including North and South Interior, Whistler)",
                  "Commercial — Rate 2", "commercial"),
    AreaClassSpec("2", "business", FORT_NELSON, "Fort Nelson", "Commercial — Rate 2 (Fort Nelson)", "commercial"),
    AreaClassSpec("3", "business", MAINLAND, "Mainland and Vancouver Island (including North and South Interior, Whistler)",
                  "Commercial — Rate 3", "commercial"),
    AreaClassSpec("3", "business", FORT_NELSON, "Fort Nelson", "Commercial — Rate 3 (Fort Nelson)", "commercial"),
)

# Seed data based on BCUC-approved rates.
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.fortisbc.com/gas/gas-rates",
    "basic_charge_monthly": 14.48,              # $/month
    "delivery_rate": 6.7040,                    # $/GJ
    "cost_of_gas": 2.4430,                      # $/GJ
    "storage_and_transport": 1.6700,            # $/GJ
    "carbon_tax": 3.1050,                       # $/GJ — BC provincial carbon tax
    "rate_rider": -0.0980,                      # $/GJ — revenue surplus refund
}

SEED_COMMERCIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.fortisbc.com/gas/gas-rates",
    "basic_charge_monthly": 18.00,              # $/month
    "delivery_rate": 5.4550,                    # $/GJ
    "cost_of_gas": 2.4430,                      # $/GJ
    "storage_and_transport": 1.6700,            # $/GJ
    "carbon_tax": 3.1050,                       # $/GJ
    "rate_rider": -0.0750,                      # $/GJ
}


class FortisBCEnergyScraper(BaseScraper):
    """Scrape FortisBC Energy natural gas rates for British Columbia."""

    def __init__(self):
        super().__init__(utility_name="FortisBC Energy", province="BC")

    def scrape(self) -> list[TariffRecord]:
        records = list(self._try_live_scrape() or [])
        live_names = {record.tariff_name for record in records}
        missing = [seed for seed in self._seed_data() if seed.tariff_name not in live_names]
        if missing:
            self.logger.warning("Live parse unavailable for %s — using unverified seed",
                                ", ".join(seed.tariff_name for seed in missing))
            records.extend(self.mark_fallback(missing))
        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Fetch each official page independently and parse complete classes."""
        pages: dict[str, str] = {}
        for key, url in PAGE_URLS.items():
            try:
                html = self.fetch_page(url)
                if key == "carbon" and "Carbon tax was eliminated" not in html:
                    html = self.fetch_rendered_page(url) or html
                pages[key] = self._page_text(html)
            except Exception as exc:
                self.logger.warning("FortisBC Energy %s page unavailable: %s", key, exc)
        records = self.parse_pages(pages)
        return self.mark_live_parsed(records) if records else None

    @staticmethod
    def _page_text(html: str) -> str:
        from scrapers.utils.parsing import parse_html
        soup = parse_html(html)
        node = soup.find("main") or soup
        return node.get_text(" ", strip=True)

    # ── Parsing ──────────────────────────────────────────────

    @staticmethod
    def _norm(text: str) -> str:
        return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()

    @staticmethod
    def _long_date(value: str) -> Optional[date]:
        try:
            return datetime.strptime(value, "%B %d, %Y").date()
        except ValueError:
            return None

    def _carbon(self, text: str, today: date) -> Optional[tuple[date, str]]:
        """Effective date of the official BC carbon-tax elimination, if published and in force."""
        match = re.search(r"Carbon tax was eliminated effective ([A-Z][a-z]+ \d{1,2}, \d{4})\.", text)
        effective = self._long_date(match.group(1)) if match else None
        if not effective or effective > today:
            return None
        return effective, (f"Province of British Columbia: carbon tax was eliminated effective {match.group(1)}. "
                           "FortisBC's rate pages publish no carbon charge.")

    @staticmethod
    def _rate_section(text: str, rate: str) -> str:
        """Business-page text for one rate schedule, up to the next schedule's description."""
        start = re.search(rf"Rate {rate} You are ", text)
        if not start:
            raise ValueError(f"Rate {rate} description missing")
        end = re.search(rf"Rate {int(rate) + 1} You are ", text[start.end():])
        return text[start.start():start.end() + end.start()] if end else text[start.start():]

    def _area_values(self, text: str, spec: AreaClassSpec, today: date) -> tuple[date, dict[str, float]]:
        pattern = (
            rf"(?:^| ){spec.area_pattern} (?:(?!{OTHER_AREAS}|Basic charge).){{0,300}}?"
            r"\(Effective (?P<date>[A-Z][a-z]+ \d{1,2}, \d{4}) ?\) "
            r"Basic charge per day (?:\d )?\$(?P<basic>\d+\.\d+) "
            r"Delivery charge per (?:gigajoule \(GJ\)|GJ) \$(?P<delivery>\d+\.\d+) "
            r"Storage and transport (?:charge|cost) per GJ \$(?P<storage>\d+\.\d+) "
            r"Cost of gas per GJ \$(?P<gas>\d+\.\d+) "
        )
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            raise ValueError(f"expected one complete {spec.area_label} table, found {len(matches)}")
        match = matches[0]
        effective = self._long_date(match.group("date"))
        if not effective or effective > today:
            raise ValueError("missing or future effective date")
        values = {key: float(match.group(key)) for key in ("basic", "delivery", "storage", "gas")}
        if min(values.values()) <= 0:
            raise ValueError("non-positive charge")
        return effective, values

    def parse_pages(self, pages: dict[str, str], today: Optional[date] = None) -> list[TariffRecord]:
        """Build tariffs from page texts keyed residential/business/carbon.

        Missing carbon status rejects everything; each rate/area table is otherwise isolated.
        """
        today = today or datetime.now(timezone.utc).date()
        pages = {key: self._norm(text) for key, text in pages.items()}
        carbon = self._carbon(pages.get("carbon", ""), today)
        if carbon is None:
            self.logger.warning("FortisBC Energy: required current carbon-tax status could not be verified")
            return []
        records: list[TariffRecord] = []
        for spec in CLASSES:
            try:
                text = pages.get(spec.page, "")
                eligibility = None
                if spec.page == "business":
                    text = self._rate_section(text, spec.rate)
                    sentence = re.match(rf"Rate {spec.rate} You are (.+?\(e\.g\. [^)]+\)\.)", text)
                    volume = re.search(r"use (less|more) than ([\d,]+) gigajoules \(GJ\) annually", sentence.group(1)) if sentence else None
                    if not volume:
                        raise ValueError("annual-volume eligibility sentence missing")
                    eligibility = "You are " + sentence.group(1)
                    limit = float(volume.group(2).replace(",", ""))
                    usage = (None, limit) if volume.group(1) == "less" else (limit, None)
                else:
                    usage = (None, None)
                effective, values = self._area_values(text, spec, today)
                records.append(self._build(spec, effective, values, eligibility, usage, carbon))
            except ValueError as exc:
                self.logger.warning("FortisBC Energy %s not parsed live: %s", spec.tariff_name, exc)
        return records

    def _build(self, spec: AreaClassSpec, effective: date, values: dict[str, float], eligibility: Optional[str],
               usage: tuple[Optional[float], Optional[float]], carbon: tuple[date, str]) -> TariffRecord:
        eff = effective.isoformat()
        url = PAGE_URLS[spec.page]
        detail = f"Rate {spec.rate}, {spec.area_label} (Effective {effective.strftime('%B')} {effective.day}, {effective.year})"
        carbon_date, carbon_note = carbon
        comps = [
            RateComponent("fixed", "Basic Charge", values["basic"], "$/day", effective_date=eff, source_url=url,
                          source_detail=detail, notes="Published per day; billed for the days in the billing period"),
            RateComponent("delivery", "Delivery Charge", values["delivery"], "$/GJ", effective_date=eff,
                          source_url=url, source_detail=detail, notes="Reviewed annually by the BCUC"),
            RateComponent("transmission", "Storage and Transport Charge", values["storage"], "$/GJ",
                          effective_date=eff, source_url=url, source_detail=detail),
            RateComponent("commodity", "Cost of Gas", values["gas"], "$/GJ", effective_date=eff, source_url=url,
                          source_detail=detail, market_reference="FortisBC gas commodity portfolio",
                          notes="FortisBC default commodity, reviewed by the BCUC every three months. Customer Choice "
                                "gas-marketer prices are separate and not included."),
            RateComponent("carbon", "BC Carbon Tax", 0.0, "$/GJ", effective_date=carbon_date.isoformat(),
                          source_url=PAGE_URLS["carbon"], source_detail="Motor fuel tax and carbon tax",
                          notes=carbon_note),
        ]
        usage_min, usage_max = usage
        return TariffRecord(
            utility_name="FortisBC Energy", province="BC", utility_type="gas", tariff_name=spec.tariff_name,
            tariff_code=f"Rate {spec.rate}", customer_class=spec.customer_class, sub_class=spec.area_label,
            eligibility=eligibility, usage_min=usage_min, usage_max=usage_max,
            usage_unit="GJ/year" if (usage_min or usage_max) else None, rate_structure="flat",
            pricing_method="regulated", effective_date=max(effective, carbon_date).isoformat(), source_url=url,
            source_page=detail, confidence="high",
            notes=(f"Service area: {spec.area_label}. Regulated by the BCUC. Other applicable fees and taxes are not "
                   "published in these rate tables and are not included."),
            components=comps,
        )

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential — Rate 1 ─────────────────────────────────
        records.append(TariffRecord(
            utility_name="FortisBC Energy",
            province="BC",
            utility_type="gas",
            tariff_name="Residential — Rate 1",
            tariff_code="Rate 1",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes=(
                "FortisBC Energy residential gas rate. "
                "Cost of gas is a pass-through from commodity markets. "
                "BC carbon tax is provincial, not the federal backstop. "
                "Regulated by BCUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="high",
                    notes="Fixed monthly customer charge",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Delivery Charge",
                    charge_value=SEED_RESIDENTIAL["delivery_rate"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="FortisBC distribution charge for delivering gas",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Cost of Gas",
                    charge_value=SEED_RESIDENTIAL["cost_of_gas"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Pass-through commodity cost — adjusted quarterly by BCUC",
                    market_reference="FortisBC gas commodity portfolio",
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Storage and Transport",
                    charge_value=SEED_RESIDENTIAL["storage_and_transport"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Pipeline transportation and underground storage costs",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Carbon Tax",
                    charge_value=SEED_RESIDENTIAL["carbon_tax"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="BC provincial carbon tax on natural gas",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Rate Rider",
                    charge_value=SEED_RESIDENTIAL["rate_rider"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Revenue surplus/deficiency adjustment — can be negative (credit)",
                ),
            ],
        ))

        # ── Commercial — Rate 2 ──────────────────────────────────
        records.append(TariffRecord(
            utility_name="FortisBC Energy",
            province="BC",
            utility_type="gas",
            tariff_name="Commercial — Rate 2",
            tariff_code="Rate 2",
            customer_class="commercial",
            rate_structure="flat",
            effective_date=SEED_COMMERCIAL["effective_date"],
            source_url=SEED_COMMERCIAL["source_url"],
            confidence="high",
            notes=(
                "FortisBC Energy small commercial gas rate. "
                "Lower delivery rate than residential. "
                "Regulated by BCUC."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_COMMERCIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="high",
                    notes="Fixed monthly customer charge for commercial accounts",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Delivery Charge",
                    charge_value=SEED_COMMERCIAL["delivery_rate"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Distribution charge — lower rate for commercial class",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Cost of Gas",
                    charge_value=SEED_COMMERCIAL["cost_of_gas"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Pass-through commodity cost — same as residential",
                    market_reference="FortisBC gas commodity portfolio",
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Storage and Transport",
                    charge_value=SEED_COMMERCIAL["storage_and_transport"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Pipeline transportation and underground storage costs",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Carbon Tax",
                    charge_value=SEED_COMMERCIAL["carbon_tax"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="BC provincial carbon tax on natural gas",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Rate Rider",
                    charge_value=SEED_COMMERCIAL["rate_rider"],
                    charge_unit="$/GJ",
                    confidence="high",
                    notes="Revenue surplus/deficiency adjustment — can be negative (credit)",
                ),
            ],
        ))

        return records
