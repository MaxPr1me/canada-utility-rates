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

REVELSTOKE = r"Revelstoke"
REVELSTOKE_CLASSES = (
    AreaClassSpec("1", "residential", REVELSTOKE, "Revelstoke (propane)",
                  "Residential — Rate 1 (Revelstoke propane)", "residential"),
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
        business_html = ""
        for key, url in PAGE_URLS.items():
            try:
                html = self.fetch_page(url)
                if key == "carbon" and "Carbon tax was eliminated" not in html:
                    html = self.fetch_rendered_page(url) or html
                if key == "business":
                    business_html = html
                pages[key] = self._page_text(html)
            except Exception as exc:
                self.logger.warning("FortisBC Energy %s page unavailable: %s", key, exc)
        urls = self._discover_documents(business_html)
        if "business" in pages:
            pages["business_rate45"] = pages["business"]
        for key, url in urls.items():
            try:
                from scrapers.utils.parsing import extract_pdf_pages
                pages[key] = self._document_text(extract_pdf_pages(self.fetch_bytes(url)), key)
            except Exception as exc:
                self.logger.warning("FortisBC Energy %s tariff document unavailable: %s", key, exc)
        records = self.parse_pages(pages, document_urls=urls)
        return self.mark_live_parsed(records) if records else None

    @staticmethod
    def _discover_documents(html: str) -> dict[str, str]:
        """Rate 4 and Rate 5 (Mainland/Vancouver Island) tariff PDFs linked from the business page."""
        from urllib.parse import urljoin
        from scrapers.utils.parsing import parse_html
        found: dict[str, str] = {}
        for anchor in parse_html(html).find_all("a", href=True) if html else []:
            match = re.search(r"/rateschedule_([45])\.pdf(?:\?|$)", anchor["href"])
            if match:
                found.setdefault(f"rate{match.group(1)}", urljoin(PAGE_URLS["business"], anchor["href"]))
        return found

    def _document_text(self, pages, key: str) -> str:
        """Table-of-charges pages (plus the Rate 4 definition/extension pages) as one string."""
        start = next((i for i, page in enumerate(pages)
                      if "Delivery Margin Related Charges" in page.text and "Basic Charge per" in page.text), None)
        if start is None:
            raise ValueError("table of charges not found")
        chosen = {i: pages[i].text for i in range(start, min(start + 3, len(pages)))}
        if key == "rate4":
            for i, page in enumerate(pages):
                if "Off-Peak Period - means" in page.text or "4.3 Extension of Off-Peak Period FortisBC" in self._norm(page.text):
                    chosen[i] = page.text
        return "\n".join(chosen[i] for i in sorted(chosen))

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
            r"Storage and transport(?: (?:charge|cost))?(?: per GJ)? \$(?P<storage>\d+\.\d+) "
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

    def parse_pages(self, pages: dict[str, str], today: Optional[date] = None,
                    document_urls: Optional[dict[str, str]] = None) -> list[TariffRecord]:
        """Build tariffs from page texts keyed residential/business/carbon.

        Rate 4/5 tariff PDFs (keys rate4/rate5) are parsed only when document_urls supplies their source URL.

        Missing carbon status rejects everything; each rate/area table is otherwise isolated.
        """
        today = today or datetime.now(timezone.utc).date()
        pages = {key: self._norm(text) for key, text in pages.items()}
        carbon = self._carbon(pages.get("carbon", ""), today)
        if carbon is None:
            self.logger.warning("FortisBC Energy: required current carbon-tax status could not be verified")
            return []
        records: list[TariffRecord] = []
        for spec in CLASSES + REVELSTOKE_CLASSES:
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
        for key, parser in (("rate5", self._rate5), ("rate4", self._rate4)):
            if key not in pages or not (document_urls or {}).get(key):
                continue
            try:
                url = document_urls[key]
                description = pages.get("business_rate45", pages.get("business", ""))
                records.append(parser(pages[key], description, url, carbon, today))
            except ValueError as exc:
                self.logger.warning("FortisBC Energy Rate %s not parsed live: %s", key[-1], exc)
        return records

    # ── Rates 4 and 5 (tariff PDFs) ──────────────────────────

    @staticmethod
    def _money(match: re.Match, *names: str) -> dict[str, float]:
        return {name: float(match.group(name).replace(",", "")) for name in names}

    def _tariff_table(self, text: str, pattern: str, today: date) -> tuple[re.Match, date, str]:
        """The single Mainland/Vancouver Island table, its effective date and BCUC order number."""
        text = self._norm(text)
        matches = list(re.finditer(pattern, text))
        if len(matches) != 1:
            raise ValueError(f"expected one complete Mainland/Vancouver Island table, found {len(matches)}")
        tail = text[matches[0].end():]
        footer = re.search(r"Order No\.: (G-\d+-\d+) .*?Effective Date: ([A-Z][a-z]+ \d{1,2}, \d{4})", tail)
        effective = self._long_date(footer.group(2)) if footer else None
        if not effective or effective > today:
            raise ValueError("missing or future effective date")
        return matches[0], effective, footer.group(1)

    @staticmethod
    def _require(text: str, *phrases: str) -> None:
        text = FortisBCEnergyScraper._norm(text)
        for phrase in phrases:
            if phrase not in text:
                raise ValueError(f"required tariff text missing: {phrase[:60]}")

    def _eligibility(self, business: str, rate: str, authorization: str) -> tuple[str, Optional[float]]:
        section = self._rate_section(self._norm(business), rate)
        sentence = re.match(rf"Rate {rate} You are (.+?\(e\.g\. [^)]+\)|.+?annually)\. ", section)
        if not sentence or authorization not in section:
            raise ValueError("eligibility/authorization text missing")
        volume = re.search(r"about ([\d,]+) GJ or more annually", sentence.group(1))
        text = f"You are {sentence.group(1)}. {authorization}"
        if rate == "5":
            if not volume:
                raise ValueError("annual-volume eligibility missing")
            text += " specific terms and conditions may apply."
            return text, float(volume.group(1).replace(",", ""))
        seasonal = re.search(r"only in the warmer months between April 1 and November 1", sentence.group(1))
        if not seasonal:
            raise ValueError("seasonal-use eligibility missing")
        return text + " specific terms and conditions may apply.", None

    def _rate5(self, text: str, business: str, url: str, carbon: tuple[date, str], today: date) -> TariffRecord:
        money = r"\$ (?P<{}>[\d,]+\.\d+)"
        pattern = (
            r"Table of Charges Mainland and Vancouver Island Service Area Delivery Margin Related Charges "
            r"1\. Basic Charge per Month " + money.format("basic") + r" 2\. Rider 2 per Month " + money.format("r2")
            + r" Subtotal of per Month Delivery Margin Related Charges " + money.format("sub1")
            + r" 3\. Demand Charge per Month per Gigajoule of Daily Demand ?1 " + money.format("demand")
            + r" 4\. Delivery Charge per Gigajoule " + money.format("delivery")
            + r" Commodity Related Charges 5\. Cost of Gas \(Commodity Cost Recovery Charge\) per Gigajoule ?2 "
            + money.format("gas") + r" 6\. Storage and Transport Charge per Gigajoule " + money.format("st")
            + r" 7\. Rider 6 per Gigajoule " + money.format("r6") + r" 8\. Rider 8 per Gigajoule " + money.format("r8")
            + r"(?: A)? Subtotal of per Gigajoule Commodity Related Charges " + money.format("sub2")
        )
        match, effective, order = self._tariff_table(text, pattern, today)
        v = self._money(match, "basic", "r2", "sub1", "demand", "delivery", "gas", "st", "r6", "r8", "sub2")
        if abs(v["basic"] + v["r2"] - v["sub1"]) > 1e-6 or abs(v["gas"] + v["st"] + v["r6"] + v["r8"] - v["sub2"]) > 1e-6:
            raise ValueError("charges do not reconcile to the published subtotals")
        if min(v["basic"], v["demand"], v["delivery"], v["gas"], v["st"]) <= 0:
            raise ValueError("non-positive charge")
        self._require(
            text, "Rider 2 Clean Growth Innovation Fund Account", "Rider 6 Midstream Cost Reconciliation Account",
            "Rider 8 Storage and Transport Renewable Natural Gas (S&T RNG) Rider",
            "Daily Demand is equal to 1.10 multiplied by the greater of",
            "The minimum charge per Month will be the aggregate of the Basic Charge, Demand Charges and the "
            "Municipal Operating Fee charge")
        eligibility, usage_min = self._eligibility(business, "5", "Rate 5 is authorized by written contract only and")
        carbon_date, carbon_note = carbon
        eff = effective.isoformat()
        detail = f"Rate Schedule 5 Table of Charges, Mainland and Vancouver Island Service Area (Order {order}, effective {effective.strftime('%B')} {effective.day}, {effective.year})"

        def comp(kind: str, name: str, value: float, unit: str, **extra) -> RateComponent:
            return RateComponent(kind, name, value, unit, effective_date=eff, source_url=url, source_detail=detail, **extra)

        comps = [
            comp("fixed", "Basic Charge", v["basic"], "$/month",
                 notes="The tariff table prints this per month; the business rate page describes a daily basic charge."),
            comp("rider", "Rider 2 (Clean Growth Innovation Fund Account)", v["r2"], "$/month"),
            comp("demand", "Demand Charge", v["demand"], "$/GJ/month of daily demand", demand_unit="GJ/day",
                 notes="Daily Demand is 1.10 x the greater of the highest winter (Nov 1-Mar 31) monthly average daily "
                       "consumption or half the highest summer (Apr 1-Oct 31) monthly average, from the preceding "
                       "Contract Year. Not a calculated bill."),
            comp("delivery", "Delivery Charge", v["delivery"], "$/GJ"),
            comp("transmission", "Storage and Transport Charge", v["st"], "$/GJ"),
            comp("commodity", "Cost of Gas", v["gas"], "$/GJ", market_reference="FortisBC gas commodity portfolio",
                 notes="Commodity Cost Recovery Charge; reduced pro rata by any RNG Blend Service share. "
                       "Gas-marketer prices are separate and not included."),
            comp("rider", "Rider 6 (Midstream Cost Reconciliation Account)", v["r6"], "$/GJ"),
            comp("rider", "Rider 8 (Storage and Transport RNG)", v["r8"], "$/GJ"),
            RateComponent("carbon", "BC Carbon Tax", 0.0, "$/GJ", effective_date=carbon_date.isoformat(),
                          source_url=PAGE_URLS["carbon"], source_detail="Motor fuel tax and carbon tax", notes=carbon_note),
        ]
        return TariffRecord(
            utility_name="FortisBC Energy", province="BC", utility_type="gas", tariff_name="Commercial — Rate 5",
            tariff_code="Rate 5", customer_class="commercial", sub_class="Mainland and Vancouver Island Service Area",
            description="General Firm Service", eligibility=eligibility, usage_min=usage_min, usage_unit="GJ/year",
            rate_structure="demand", pricing_method="regulated",
            effective_date=max(effective, carbon_date).isoformat(), source_url=url, source_page=detail,
            confidence="high",
            notes=("Firm service under a written General Firm Service Agreement; the annual volume is the business "
                   "page's 'about' figure, not a tariff threshold. Minimum monthly charge is the Basic Charge, Demand "
                   "Charges and any Municipal Operating Fee (a condition, not an extra charge). A Municipal Operating "
                   "Fee applies where FortisBC must remit one and is not included. Fort Nelson Rate 5 prices are not "
                   "parsed. Regulated by the BCUC."),
            components=comps,
        )

    def _rate4(self, text: str, business: str, url: str, carbon: tuple[date, str], today: date) -> TariffRecord:
        money = r"\$ (?P<{}>[\d,]+\.\d+)"
        pattern = (
            r"Table of Charges Mainland and Vancouver Island Service Area Delivery Margin Related Charges "
            r"1\. Basic Charge per Day " + money.format("basic") + r" 2\. Rider 2 per Day " + money.format("r2")
            + r" Subtotal of per Day Delivery Margin Related Charges " + money.format("sub1")
            + r" 3\. Delivery Charge per Gigajoule \(a\) Off-Peak Period " + money.format("d_off")
            + r" \(b\) Extension Period " + money.format("d_ext")
            + r" Commodity Related Charges 4\. Cost of Gas \(Commodity Cost Recovery Charge\) per Gigajoule ?1 "
            r"\(a\) Off-Peak Period " + money.format("g_off") + r" \(b\) Extension Period " + money.format("g_ext")
            + r" 5\. Storage and Transport Charge per Gigajoule \(a\) Off-Peak Period " + money.format("s_off")
            + r" \(b\) Extension Period " + money.format("s_ext")
            + r" 6\. Rider 6 per Gigajoule " + money.format("r6") + r" 7\. Rider 8 per Gigajoule " + money.format("r8")
            + r"(?: A)? Subtotal of per Gigajoule Commodity Related Charges \(a\) Off-Peak Period "
            + money.format("t_off") + r"(?: A)? \(b\) Extension Period " + money.format("t_ext")
            + r"(?: A)? 8\. Unauthorized Gas Charge per Gigajoule The greater of during peak period "
            r"\$ ?20\.00/GJ or 1\.5 x the Sumas Daily Price ?2"
        )
        match, effective, order = self._tariff_table(text, pattern, today)
        names = ("basic", "r2", "sub1", "d_off", "d_ext", "g_off", "g_ext", "s_off", "s_ext", "r6", "r8", "t_off", "t_ext")
        v = self._money(match, *names)
        if abs(v["basic"] + v["r2"] - v["sub1"]) > 1e-6:
            raise ValueError("daily charges do not reconcile to the published subtotal")
        for season in ("off", "ext"):
            if abs(v[f"g_{season}"] + v[f"s_{season}"] + v["r6"] + v["r8"] - v[f"t_{season}"]) > 1e-6:
                raise ValueError("per-GJ charges do not reconcile to the published subtotal")
        if min(v["basic"], v["d_off"], v["d_ext"], v["g_off"], v["g_ext"], v["s_off"], v["s_ext"]) <= 0:
            raise ValueError("non-positive charge")
        self._require(
            text, "Off-Peak Period - means the period commencing 7:00 a.m. Pacific Standard Time April 1 to 7:00 a.m. "
            "Pacific Standard Time November 1.",
            "the Customer will be charged the Extension Period Charges set out in the Table of Charges",
            "Rider 2 Clean Growth Innovation Fund Account", "Rider 6 Midstream Cost Reconciliation Account",
            "Rider 8 Storage and Transport Renewable Natural Gas (S&T RNG) Rider",
            "The minimum charge per Month, applicable only to months in which Gas is consumed, will be the "
            "aggregate of the Basic Charge and the Municipal Operating Fee charge")
        eligibility, _ = self._eligibility(business, "4", "Rate 4 is authorized by written consent only and")
        carbon_date, carbon_note = carbon
        eff = effective.isoformat()
        detail = f"Rate Schedule 4 Table of Charges, Mainland and Vancouver Island Service Area (Order {order}, effective {effective.strftime('%B')} {effective.day}, {effective.year})"
        periods = (("off", "Off-Peak Period", "April 1 to November 1"),
                   ("ext", "Extension Period", None))

        def comp(kind: str, name: str, value: float, unit: str, **extra) -> RateComponent:
            return RateComponent(kind, name, value, unit, effective_date=eff, source_url=url, source_detail=detail, **extra)

        comps = [
            comp("fixed", "Basic Charge", v["basic"], "$/day",
                 notes="Applies only to billing periods in which gas is consumed."),
            comp("rider", "Rider 2 (Clean Growth Innovation Fund Account)", v["r2"], "$/day"),
        ]
        for code, label, months in periods:
            ext_note = ("Extension Period charges apply when FortisBC agrees to serve beyond the Off-Peak Period."
                        if code == "ext" else None)
            kw = {"season": label, "season_months": months, "notes": ext_note}
            comps += [
                comp("delivery", "Delivery Charge", v[f"d_{code}"], "$/GJ", **kw),
                comp("transmission", "Storage and Transport Charge", v[f"s_{code}"], "$/GJ", **kw),
                comp("commodity", "Cost of Gas", v[f"g_{code}"], "$/GJ", market_reference="FortisBC gas commodity portfolio",
                     season=label, season_months=months,
                     notes=" ".join(filter(None, (ext_note, "Commodity Cost Recovery Charge; reduced pro rata by any "
                                                            "RNG Blend Service share.")))),
            ]
        comps += [
            comp("rider", "Rider 6 (Midstream Cost Reconciliation Account)", v["r6"], "$/GJ"),
            comp("rider", "Rider 8 (Storage and Transport RNG)", v["r8"], "$/GJ"),
            RateComponent("carbon", "BC Carbon Tax", 0.0, "$/GJ", effective_date=carbon_date.isoformat(),
                          source_url=PAGE_URLS["carbon"], source_detail="Motor fuel tax and carbon tax", notes=carbon_note),
        ]
        return TariffRecord(
            utility_name="FortisBC Energy", province="BC", utility_type="gas", tariff_name="Commercial — Rate 4",
            tariff_code="Rate 4", customer_class="commercial", sub_class="Mainland and Vancouver Island Service Area",
            description="Seasonal Firm Gas Service", eligibility=eligibility, rate_structure="mixed",
            pricing_method="regulated", effective_date=max(effective, carbon_date).isoformat(), source_url=url,
            source_page=detail, confidence="high",
            notes=("Seasonal firm service under a written Seasonal Firm Gas Service Agreement. Gas taken in the peak "
                   "period without FortisBC's written consent is charged the Unauthorized Gas Charge: the greater of "
                   "$20.00/GJ or 1.5 x the Sumas Daily Price (a penalty condition, not a rate component). The minimum "
                   "monthly charge, for months with consumption, is the Basic Charge plus any Municipal Operating Fee. "
                   "Fort Nelson is not published for this schedule here. Regulated by the BCUC."),
            components=comps,
        )

    def _build(self, spec: AreaClassSpec, effective: date, values: dict[str, float], eligibility: Optional[str],
               usage: tuple[Optional[float], Optional[float]], carbon: tuple[date, str]) -> TariffRecord:
        eff = effective.isoformat()
        url = PAGE_URLS[spec.page]
        detail = f"Rate {spec.rate}, {spec.area_label} (Effective {effective.strftime('%B')} {effective.day}, {effective.year})"
        carbon_date, carbon_note = carbon
        propane = spec.area_pattern == REVELSTOKE
        if propane:
            carbon_note += (" The Province also states that motor fuel tax applies to propane for any use unless exempt; "
                            "FortisBC publishes no propane tax amount in these tables, so none is included.")
        comps = [
            RateComponent("fixed", "Basic Charge", values["basic"], "$/day", effective_date=eff, source_url=url,
                          source_detail=detail, notes="Published per day; billed for the days in the billing period"),
            RateComponent("delivery", "Delivery Charge", values["delivery"], "$/GJ", effective_date=eff,
                          source_url=url, source_detail=detail, notes="Reviewed annually by the BCUC"),
            RateComponent("transmission", "Storage and Transport Charge", values["storage"], "$/GJ",
                          effective_date=eff, source_url=url, source_detail=detail),
            RateComponent("commodity", "Cost of Propane" if propane else "Cost of Gas", values["gas"], "$/GJ",
                          effective_date=eff, source_url=url, source_detail=detail,
                          market_reference="FortisBC propane portfolio" if propane else "FortisBC gas commodity portfolio",
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
