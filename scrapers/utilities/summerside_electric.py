"""
summerside_electric.py — Scraper for Summerside Electric, the City of Summerside's utility (Prince Edward Island).

Official source: the City's "Electric Rates, Schedule & Policy Manual" (Section N, Rates, Schedules and
Application Guidelines), linked from https://www.summerside.ca/my_services/my_utilities. The revision table
on page 2 dates the current rates ("Rate adjustment in accordance with Maritime Electric and IRAC order for
Fiona Cost Recovery ... August 1, 2026"); the most recent date there is the records' effective date.

Prices are printed "per Billing Period". The manual says the billing period "cannot be exacted to a 30 or 31
day month" and its Heat For Less Now pages print the same service charge as "$24.57/month", so service
charges are stored per month. Energy blocks keep the printed plain-kWh threshold; data/models/block_periods.json
records their monthly period (owner decision 2026-10-30, as for Maritime Electric), and leaves the seasonal
schedules' period open. The Energy Cost Adjustment Mechanism (ECAM) adds a bill adjustment
whose current value is not printed in the manual, so no ECAM component is shown.

Scope: Residential Urban, Rural, Seasonal and Seasonal Option, General Service I and General Service I -
Seasonal (first 20 kW of demand free), and Small and Large Industrial. Excluded: General Service II
(closed March 1, 2016), the Heat For Less Now equipment rate schedules, unmetered and short-term unmetered
service, miscellaneous, lighting and rental facilities, and electric-vehicle charging. Summerside also buys
wholesale power from Maritime Electric (Maritime rates 330/340), which stays a separate reference record.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import urljoin

from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

UTILITY = "Summerside Electric"
UTILITIES_PAGE_URL = "https://www.summerside.ca/my_services/my_utilities"
LAST_KNOWN_MANUAL_URL = ("https://summersideca.hosted.civiclive.com/UserFiles/Servers/Server_19514871/File/"
                         "2026%20-%20Electric%20Rates%20Schedule%20and%20Policy%20Manual%20August%201%202026%20v2.pdf")
_C = r"(\d+(?:\.\d+)?)\S?"
_RES = (r"Service Charge: \$\s?(\d+(?:\.\d+)?) per Billing Period\s*(?:[A-Za-z ]{1,40}?\s)?Energy Charge: " + _C
        + r" per kWh for first (\d+) kWh per Billing Period\s*" + _C + r" per kWh for balance kWh per Billing Period")
_GS = (r"Service Charge: \$\s?(\d+(?:\.\d+)?) per Billing Period\s*Demand Charge: No charge for first (\d+) kW or less "
       r"per Billing Period\s*\$(\d+(?:\.\d+)?) per kW for balance kW per Billing Period\s*Energy Charge: " + _C
       + r" per kWh for first (\d+) kWh per Billing Period\s*" + _C + r" per kWh for balance kWh per Billing Period")
MONTHLY_NOTE = ("Printed per Billing Period, about one month (the manual: the billing period 'cannot be exacted to a "
                "30 or 31 day month'; its Heat For Less Now schedules print the service charge per month).")

# code: (name, customer_class, sub_class, anchor text that precedes the class's prices, price pattern)
CLASSES = {
    "RES-URBAN": ("Residential Urban Rate", "residential", "residential, urban (population over 2,000)",
                  r"villages with population over 2000 served by the City\.", _RES),
    "RES-RURAL": ("Residential Rural Rate", "residential", "residential, rural",
                  r"Residential Urban category served by the City\.", _RES),
    "RES-SEASONAL": ("Residential Seasonal Rate", "residential", "residential seasonal (not a principal residence)",
                     r"Principal Residence \(e\.g\., summer cottages\)\.", _RES),
    "RES-SEASONAL-OPTION": ("Residential Seasonal Option", "residential",
                            "residential seasonal option (connected year round, billed May to October)",
                            r"Residential Seasonal customers whose", _RES),
    "GS1": ("General Service I", "commercial", "general service", r"General Service I\s*Service Rate Schedules", _GS),
    "GS1-SEASONAL": ("General Service I - Seasonal", "commercial", "general service seasonal",
                     r"General Service Seasonal customers whose", _GS),
}


def _iso(text: str) -> str:
    return datetime.strptime(text, "%B %d, %Y").date().isoformat()


def find_manual_url(html: str, base_url: str = UTILITIES_PAGE_URL) -> Optional[str]:
    for anchor in parse_html(html or "").find_all("a", href=True):
        if re.sub(r"\s+", " ", anchor.get_text(" ", strip=True)) == "Electric Rates, Schedule & Policy Manual" \
                and anchor["href"].lower().endswith(".pdf"):
            return urljoin(base_url, anchor["href"])
    return None


def manual_effective(pages: list[DocumentPage]) -> str:
    """Most recent date of the page-2 revision table (rate adjustments only)."""
    for page in pages[:4]:
        if "Description: Effective Date:" in page.text:
            dates = [_iso(m) for m in re.findall(r"([A-Z][a-z]+ \d{1,2}, \d{4})", page.text.split("Description:", 1)[1])]
            if dates:
                return max(dates)
    raise ValueError("revision table with effective dates not found")


def parse_manual(pages: list[DocumentPage], source_url: str, today: Optional[date] = None,
                 discovery_note: str = "") -> list[TariffRecord]:
    """Build the in-scope Section N schedules; raise ValueError (fail closed) on a missing date, class or price."""
    today = today or date.today()
    effective = manual_effective(pages)
    if date.fromisoformat(effective) > today:
        raise ValueError(f"manual rates take effect {effective}, after {today.isoformat()}")
    section = [p for p in pages if "Rates, Schedules and Application Guidelines" in p.text]
    text = "\n".join(p.text for p in section)

    def where(position: int) -> int:
        offset = 0
        for page in section:
            offset += len(page.text) + 1
            if position < offset:
                return page.page_number
        return section[-1].page_number

    records = []

    def record(code: str, name: str, customer_class: str, sub_class: str, structure: str, page: int,
               components: list[RateComponent], extra: str = "", demand_min: Optional[float] = None) -> None:
        detail = f"Electric Rates, Schedule & Policy Manual (rates effective {effective}), Section N, PDF page {page}"
        for component in components:
            component.effective_date, component.source_url, component.source_detail = effective, source_url, detail
        notes = (f"Summerside Electric {name}. Subject to the Energy Cost Adjustment Mechanism, whose current "
                 f"adjustment is not printed in the manual (not shown). {extra}").strip()
        if discovery_note:
            notes += " " + discovery_note
        records.append(TariffRecord(
            utility_name=UTILITY, province="PE", utility_type="electricity", tariff_name=name, tariff_code=code,
            customer_class=customer_class, sub_class=sub_class, rate_structure=structure, pricing_method="municipal",
            demand_min_kw=demand_min, effective_date=effective, source_url=source_url, source_page=detail,
            confidence="high", notes=notes, components=components))

    anchors = []
    for code, (_, _, _, anchor, _) in CLASSES.items():
        found = re.search(anchor, text)
        if not found:
            raise ValueError(f"{CLASSES[code][0]} section not found")
        anchors.append((code, found))
    industrial = re.search(r"chiefly for manufacturing or processing of goods", text)
    limits = [found.start() for _, found in anchors[1:]] + [industrial.start() if industrial else len(text)]
    if any(later <= found.end() for (_, found), later in zip(anchors, limits)):
        raise ValueError("rate schedule sections out of order")
    for (code, found), limit in zip(anchors, limits):
        name, customer_class, sub_class, _, pattern = CLASSES[code]
        # Each class reads only its own section, so a missing block never borrows the next class's prices.
        prices = re.compile(pattern).search(text, found.end(), limit)
        if not prices:
            raise ValueError(f"{name} prices not found")
        page = where(prices.start())
        fixed = RateComponent(component_type="fixed", component_name="Service Charge",
                              charge_value=float(prices.group(1)), charge_unit="$/month", notes=MONTHLY_NOTE)
        if pattern is _RES:
            block = float(prices.group(3))
            components = [fixed,
                          RateComponent(component_type="energy", component_name=f"Energy Charge — First {block:,.0f} kWh",
                                        charge_value=round(float(prices.group(2)) / 100, 6), charge_unit="$/kWh",
                                        tier_number=1, tier_threshold=block, tier_unit="kWh"),
                          RateComponent(component_type="energy", component_name="Energy Charge — Balance",
                                        charge_value=round(float(prices.group(4)) / 100, 6), charge_unit="$/kWh",
                                        tier_number=2, tier_threshold=block, tier_unit="kWh")]
            record(code, name, customer_class, sub_class, "tiered", page, components)
        else:
            free, block = float(prices.group(2)), float(prices.group(5))
            components = [fixed,
                          RateComponent(component_type="demand", component_name=f"Demand Charge — First {free:g} kW",
                                        charge_value=0.0, charge_unit="$/kW/month", demand_unit="kW", tier_number=1,
                                        tier_threshold=free, tier_unit="kW",
                                        notes=f"No charge for the first {free:g} kW or less per billing period."),
                          RateComponent(component_type="demand", component_name="Demand Charge — Balance",
                                        charge_value=float(prices.group(3)), charge_unit="$/kW/month", demand_unit="kW",
                                        tier_number=2, tier_threshold=free, tier_unit="kW",
                                        notes="Billing demand: the greater of the maximum kW demand or 90% of the "
                                              "maximum kVA demand in the billing period."),
                          RateComponent(component_type="energy", component_name=f"Energy Charge — First {block:,.0f} kWh",
                                        charge_value=round(float(prices.group(4)) / 100, 6), charge_unit="$/kWh",
                                        tier_number=1, tier_threshold=block, tier_unit="kWh"),
                          RateComponent(component_type="energy", component_name="Energy Charge — Balance",
                                        charge_value=round(float(prices.group(6)) / 100, 6), charge_unit="$/kWh",
                                        tier_number=2, tier_threshold=block, tier_unit="kWh")]
            record(code, name, customer_class, sub_class, "demand", page, components)

    small = re.search(r"Demand Charge: \$(\d+(?:\.\d+)?) per kW of billing demand per month\s*Energy Charge: " + _C
                      + r" per kWh for first 100 kWh per kW of billing demand per month\s*" + _C
                      + r" kWh for balance of kWh per month", text)
    large = re.search(r"Demand Charge: \$(\d+(?:\.\d+)?) per kW of the billing demand per month\s*Energy Charge: " + _C
                      + r" per kWh for all kWh per month", text)
    if not small or not large:
        raise ValueError("industrial rate schedules not found")
    record("SI", "Small Industrial Rate", "industrial", "small industrial (manufacturing/processing, 5 kW minimum)",
           "demand", where(small.start()), [
               RateComponent(component_type="demand", component_name="Demand Charge", charge_value=float(small.group(1)),
                             charge_unit="$/kW/month", demand_unit="kW",
                             notes="Billing demand: the greatest of the monthly maximum kW, 90% of the maximum kVA, or 5 kW."),
               RateComponent(component_type="energy", component_name="Energy Charge — First 100 kWh/kW",
                             charge_value=round(float(small.group(2)) / 100, 6), charge_unit="$/kWh", tier_number=1,
                             tier_threshold=100.0, tier_unit="kWh/kW of billing demand/month"),
               RateComponent(component_type="energy", component_name="Energy Charge — Balance",
                             charge_value=round(float(small.group(3)) / 100, 6), charge_unit="$/kWh", tier_number=2,
                             tier_threshold=100.0, tier_unit="kWh/kW of billing demand/month")],
           "No service charge is printed.", demand_min=5.0)
    record("LI", "Large Industrial Rate", "industrial", "large industrial (manufacturing/processing, 750 kW minimum)",
           "demand", where(large.start()), [
               RateComponent(component_type="demand", component_name="Demand Charge", charge_value=float(large.group(1)),
                             charge_unit="$/kW/month", demand_unit="kW",
                             notes="Billing demand includes winter-peak ratchets (90% tests); these set billing demand only."),
               RateComponent(component_type="energy", component_name="Energy Charge", charge_value=round(
                   float(large.group(2)) / 100, 6), charge_unit="$/kWh", notes="All kWh per month.")],
           "No service charge is printed; rental of City substation equipment is a separate charge.", demand_min=750.0)
    return records


class SummersideElectricScraper(BaseScraper):
    """Parse Summerside Electric's building-service rate schedules."""

    def __init__(self) -> None:
        super().__init__(utility_name=UTILITY, province="PE")

    def scrape(self) -> list[TariffRecord]:
        # No seed fallback for utilities added in batch 18 (provisional decision 2026-11-04).
        records = self._try_live_scrape()
        if not records:
            self.logger.warning("Summerside Electric: no live records (no seed fallback)")
        return records

    def _discover(self) -> tuple[str, str]:
        try:
            url = find_manual_url(self.fetch_page(UTILITIES_PAGE_URL))
        except Exception as exc:
            self.logger.warning("Summerside utilities page unavailable: %s", exc)
            url = None
        if url:
            return url, ""
        return LAST_KNOWN_MANUAL_URL, ("The utilities page did not link the rates manual, so the last known manual "
                                       "was read (it may not be the current edition).")

    def _try_live_scrape(self) -> list[TariffRecord]:
        url, note = self._discover()
        try:
            pages = extract_pdf_pages(self.fetch_bytes(url), drop_repeated_lines=False)
            records = parse_manual(pages, url, discovery_note=note)
        except Exception as exc:
            self.logger.warning("Summerside Electric manual failed closed: %s", exc)
            return []
        return self.mark_live_parsed(records)
