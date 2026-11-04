"""
summerland.py — Scraper for the District of Summerland electrical utility (British Columbia).

Official source: Schedule 'A' (Electric Fees and Charges) of the District's consolidated Fees and
Charges Bylaw No. 98-001, linked from https://www.summerland.ca/your-city-hall/bylaws-policies/bylaws
(the utility-billing page names this bylaw as the electric rate source). The bylaw's amendment list
dates each Schedule A replacement ("Bylaw 2026-004 replaced Schedule A effective February 10, 2026");
the latest listed date is the schedule's effective date and must not be in the future.

Council sets these rates; the BCUC does not regulate them. Prices exclude GST and PST.

Scope (building service): residential E01-E08, general commercial E10 and primary-metered service with
customer-owned equipment E15, E17 and 19. E10 and E15 bill demand only above 40 kVA, stored as a
$0 first block like Maritime Electric's free 20 kW. Excluded: E12/E14 (E10 prices for GST- or
PST-exempt customers), E20 irrigation, E22 unmetered cable amplifiers, E25 municipal energy (District
accounts; batch 18 provisional decision, 2026-11-04), E26 flat-rate power, E31-E44 and E50 lighting,
distributed-generation credits and connection fees.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from urllib.parse import urljoin

from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

UTILITY = "District of Summerland"
BYLAWS_PAGE_URL = "https://www.summerland.ca/your-city-hall/bylaws-policies/bylaws"
LAST_KNOWN_BYLAW_URL = (
    "https://www.summerland.ca/docs/default-source/your-city-hall/bylaws---policies/district-bylaws/"
    "fees-and-charges-no-98-001-consolidated-to-feb-10-20269da7a85cf68d6e33909cff00007e7f94.pdf?sfvrsn=942ac6fb_2"
)
_DATE = r"([A-Z][a-z]+ \d{1,2}, \d{4})"
_MONEY = r"\$\s?(\d+(?:\.\d+)?)"


@dataclass(frozen=True)
class _Class:
    code: str
    heading: str
    name: str
    customer_class: str
    sub_class: str
    demand: bool


CLASSES = (
    _Class("E01-E08", r"RATE CODES E01 TO E08 . RESIDENTIAL", "Residential", "residential", "residential", False),
    _Class("E10", r"RATE CODE E10 . GENERAL COMMERCIAL\n", "General Commercial", "commercial",
           "general commercial", True),
    _Class("E15", r"RATE CODE E15 . PRIMARY POWER LESS THAN 500 KVA DEMAND", "Primary Power (under 500 kVA)",
           "commercial", "primary power, customer-owned equipment, under 500 kVA", True),
    _Class("E17", r"RATE CODE E17 . PRIMARY POWER OVER 500 KVA BUT LESS THAN 1,000 KVA DEMAND",
           "Primary Power (500 to 1,000 kVA)", "commercial",
           "primary power, customer-owned equipment, 500 to 1,000 kVA", True),
    _Class("E19", r"RATE CODE 19 . PRIMARY POWER OVER 1,000 KVA DEMAND", "Primary Power (over 1,000 kVA)",
           "commercial", "primary power, customer-owned equipment, over 1,000 kVA", True),
)


def _iso(text: str) -> str:
    return datetime.strptime(text, "%B %d, %Y").date().isoformat()


def find_bylaw_url(html: str, base_url: str = BYLAWS_PAGE_URL) -> Optional[str]:
    """The consolidated Fees and Charges Bylaw No. 98-001 link on the District bylaws page."""
    for anchor in parse_html(html or "").find_all("a", href=True):
        label = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))
        if re.match(r"Fees and Charges No\. 98-001 Consolidated", label, re.I) and ".pdf" in anchor["href"]:
            return urljoin(base_url, anchor["href"])
    return None


def schedule_a_effective(text: str) -> str:
    """Latest 'replaced/revised Schedule A effective <date>' in the bylaw's amendment list."""
    dates = [_iso(m.group(1)) for m in
             re.finditer(r"Bylaw \d{4}-\d{3} (?:replaced|revised) Schedule A effective " + _DATE, text)]
    if not dates:
        raise ValueError("Schedule A effective date not found")
    return max(dates)


def parse_bylaw(pages: list[DocumentPage], source_url: str, today: Optional[date] = None,
                discovery_note: str = "") -> list[TariffRecord]:
    """Build the in-scope Schedule A classes; raise ValueError (fail closed) when the schedule, a class or
    a price is missing, or the schedule is not yet in effect."""
    today = today or date.today()
    full = "\n".join(page.text for page in pages)
    effective = schedule_a_effective(full)
    if date.fromisoformat(effective) > today:
        raise ValueError(f"Schedule A takes effect {effective}, after {today.isoformat()}")
    start = re.search(r"SCHEDULE .A., BYLAW 98-001", full)
    end = re.search(r"OTHER RATES AND CHARGES", full)
    if not start or not end or end.start() < start.start():
        raise ValueError("Schedule A electric rates section not found")
    section = full[start.start():end.start()]
    page_numbers, inside = [], False
    for page in pages:
        inside = inside or bool(re.search(r"SCHEDULE .A., BYLAW 98-001", page.text))
        if inside:
            page_numbers.append(page.page_number)
            if "OTHER RATES AND CHARGES" in page.text:
                break
    detail = (f"Fees and Charges Bylaw No. 98-001 (consolidated), Schedule A Electric Fees and Charges, "
              f"effective {effective}, PDF pages {page_numbers[0]}-{page_numbers[-1]}")
    headings = list(re.finditer(r"RATE CODES? E?\d{2}", section))
    records = []
    for spec in CLASSES:
        match = re.search(spec.heading, section)
        if not match:
            raise ValueError(f"rate code {spec.code} not found")
        following = [h.start() for h in headings if h.start() > match.start()]
        body = section[match.start():following[0] if following else len(section)]
        basic = re.search(r"Basic [Cc]harge: " + _MONEY + r" per month", body)
        energy = re.search(r"All electrical energy used " + _MONEY + r" per kWh", body)
        if not basic or not energy:
            raise ValueError(f"rate code {spec.code} basic or energy charge missing")
        demand = re.search(r"Per kVA of .Billing Demand. (exceeding )?(?:per month )?" + _MONEY
                           + r"(?:\s*\n\s*(\d+) kVA)?", body)
        if spec.demand != bool(demand):
            raise ValueError(f"rate code {spec.code} demand charge {'missing' if spec.demand else 'unexpected'}")
        components = [
            RateComponent(component_type="fixed", component_name="Basic Charge", charge_value=float(basic.group(1)),
                          charge_unit="$/month"),
            RateComponent(component_type="energy", component_name="Energy Charge", charge_value=float(energy.group(1)),
                          charge_unit="$/kWh", notes="All electrical energy used."),
        ]
        if demand:
            price = float(demand.group(2))
            if demand.group(1):
                if not demand.group(3):
                    raise ValueError(f"rate code {spec.code} demand threshold missing")
                free = float(demand.group(3))
                components += [
                    RateComponent(component_type="demand", component_name=f"Demand Charge — First {free:g} kVA",
                                  charge_value=0.0, charge_unit="$/kVA/month", demand_unit="kVA", tier_number=1,
                                  tier_threshold=free, tier_unit="kVA",
                                  notes=f"No charge for the first {free:g} kVA of billing demand."),
                    RateComponent(component_type="demand", component_name=f"Demand Charge — Above {free:g} kVA",
                                  charge_value=price, charge_unit="$/kVA/month", demand_unit="kVA", tier_number=2,
                                  tier_threshold=free, tier_unit="kVA",
                                  notes=f"Per kVA of billing demand exceeding {free:g} kVA, per month."),
                ]
            else:
                components.append(RateComponent(
                    component_type="demand", component_name="Demand Charge", charge_value=price,
                    charge_unit="$/kVA/month", demand_unit="kVA", notes="Per kVA of billing demand, per month."))
        for component in components:
            component.effective_date = effective
            component.source_url = source_url
            component.source_detail = f"{detail}, Rate Code {spec.code}"
        notes = f"District of Summerland Rate Code {spec.code}. Council-set rates; prices exclude GST and PST."
        if spec.code in ("E15", "E17", "E19"):
            notes += " Applies where the customer owns and maintains all equipment past the load side of the metering unit."
        if discovery_note:
            notes += " " + discovery_note
        records.append(TariffRecord(
            utility_name=UTILITY, province="BC", utility_type="electricity", tariff_name=spec.name,
            tariff_code=spec.code, customer_class=spec.customer_class, sub_class=spec.sub_class,
            rate_structure="demand" if spec.demand else "flat", pricing_method="municipal",
            effective_date=effective, source_url=source_url, source_page=detail, confidence="high",
            notes=notes, components=components,
        ))
    return records


class SummerlandScraper(BaseScraper):
    """Parse the District of Summerland's electric rates (Fees and Charges Bylaw, Schedule A)."""

    def __init__(self) -> None:
        super().__init__(utility_name=UTILITY, province="BC")

    def scrape(self) -> list[TariffRecord]:
        # No seed fallback for utilities added in batch 18 (provisional decision 2026-11-04).
        records = self._try_live_scrape()
        if not records:
            self.logger.warning("Summerland: no live records (no seed fallback)")
        return records

    def _discover(self) -> tuple[str, str]:
        try:
            url = find_bylaw_url(self.fetch_page(BYLAWS_PAGE_URL))
        except Exception as exc:
            self.logger.warning("Summerland bylaws page unavailable: %s", exc)
            url = None
        if url:
            return url, ""
        return LAST_KNOWN_BYLAW_URL, ("The bylaws page did not link a consolidated Fees and Charges Bylaw, so the "
                                      "last known consolidation was read (it may not be the current one).")

    def _try_live_scrape(self) -> list[TariffRecord]:
        url, note = self._discover()
        try:
            pages = extract_pdf_pages(self.fetch_bytes(url), drop_repeated_lines=False)
            records = parse_bylaw(pages, url, discovery_note=note)
        except Exception as exc:
            self.logger.warning("Summerland Schedule A failed closed: %s", exc)
            return []
        return self.mark_live_parsed(records)
