"""
grand_forks.py — Scraper for the City of Grand Forks electrical utility (British Columbia).

Official sources (City document library, https://www.grandforks.ca/document-library/):
  - Fees & Charges Bylaw No. 1958, consolidated for convenience: Schedule "G" Electrical Utility Fees
    and Charges names the amending bylaw that set it (for example "SCHEDULE "G" (Bylaw 1958-A19)").
  - That amending bylaw: "The effective date of this amending bylaw shall be April 15, 2026", with the
    same replacement Schedule G. Its prices must equal the consolidation's or the run fails closed.
Both documents are found through the dated fees-and-charges library, with public media search
(wp-json/wp/v2/media) as a fallback. The media API can reject a request even when the library works.
The consolidation prints no effective date of its own, so a missing amending bylaw also fails closed.

Council sets these rates; the BCUC does not regulate them. Scope: 1. Residential Service,
2. Commercial/Industrial/Institutional Service (its first block is "the first 200,000 kWh used in a
two-month billing period"; data/models/block_periods.json records that period) and 3. Seasonal Loads
(minimum three months of service). Excluded: 4. Unmetered Service (priced by agreement), service and
meter charges.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import urljoin

from requests.exceptions import RequestException

from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

UTILITY = "City of Grand Forks"
DOCUMENT_LIBRARY_URL = "https://www.grandforks.ca/document-library/?document_type=fees-and-charges"
MEDIA_SEARCH_URL = "https://www.grandforks.ca/wp-json/wp/v2/media?search={query}&per_page=100"
LAST_KNOWN_CONSOLIDATION_URL = "https://www.grandforks.ca/wp-content/uploads/By1958Fees-and-Charges-CONSOLIDATED-through-A20.pdf"
_CONSOLIDATION = re.compile(r"/(?:By|Bylaw)1958[^/]*Fees[^/]*CONSOLIDATED[^/]*\.pdf$", re.I)
_DATE = r"([A-Z][a-z]+ \d{1,2}, \d{4})"
_MONEY = r"\$(\d+(?:\.\d+)?)"


def _iso(text: str) -> str:
    return datetime.strptime(text, "%B %d, %Y").date().isoformat()


def newest_media_url(payload: str, pattern: re.Pattern) -> Optional[str]:
    """source_url of the most recent media item whose URL matches ``pattern`` (wp/v2/media JSON)."""
    items = [item for item in json.loads(payload or "[]")
             if isinstance(item, dict) and pattern.search(item.get("source_url") or "")]
    items.sort(key=lambda item: item.get("date") or "", reverse=True)
    return items[0]["source_url"] if items else None


def newest_document_url(html: str, pattern: re.Pattern) -> Optional[str]:
    """Choose a matching library document by publication date, never by its position on the page."""
    documents: list[tuple[str, str]] = []
    for heading in parse_html(html or "").find_all("h3"):
        anchor = heading.find("a", href=True)
        if anchor is None:
            continue
        url = urljoin(DOCUMENT_LIBRARY_URL, anchor["href"])
        if not pattern.search(url):
            continue
        published = heading.find("small")
        if published is None:
            raise ValueError(f"document library publication date missing for {url}")
        documents.append((_iso(published.get_text(" ", strip=True)), url))
    documents.sort(key=lambda document: document[0], reverse=True)
    return documents[0][1] if documents else None


def amendment_pattern(amendment: str) -> re.Pattern:
    """Media URL pattern of an amending bylaw such as '1958-A19' (consolidations excluded)."""
    number = re.escape(amendment)
    return re.compile(rf"/(?:By|Bylaw){number}[^/]*Amendment[^/]*\.pdf$", re.I)


def schedule_g(pages: list[DocumentPage]) -> tuple[str, str, list[int]]:
    """(text, amending bylaw number, PDF pages) of Schedule G, Electrical Utility Fees and Charges."""
    full, numbers = "", []
    for page in pages:
        if re.search(r"SCHEDULE .G.(?: \(Bylaw [\d-]+A\d+\))?\s*\n?ELECTRICAL UTILITY FEES AND CHARGES", page.text) \
                or (numbers and "Meter Checking" in page.text):
            full += "\n" + page.text
            numbers.append(page.page_number)
    match = re.search(r"SCHEDULE .G. \(Bylaw (1958-A\d+)\)\s*\n?ELECTRICAL UTILITY FEES AND CHARGES(.*)", full, re.S)
    if not match:
        raise ValueError("Schedule G Electrical Utility Fees and Charges not found")
    return match.group(2), match.group(1), numbers


def _prices(text: str) -> dict[str, float]:
    """The six published prices of Schedule G items 1-3."""
    flat = re.compile(r"Basic minimum service charge, per month " + _MONEY + r".*?Electrical usage charge, per kWh "
                      + _MONEY, re.S)
    sections = {key: re.search(rf"{label}(.*?)(?:\n\d\. |\Z)", text, re.S)
                for key, label in (("res", r"1\. Residential Service"),
                                   ("com", r"2\. Commercial/Industrial/Institutional Service"),
                                   ("sea", r"3\. Seasonal Loads"))}
    if not all(sections.values()):
        raise ValueError("Schedule G items 1-3 not all found")
    res = flat.search(sections["res"].group(1))
    sea = flat.search(sections["sea"].group(1))
    com = re.search(r"Basic minimum service charge, per month " + _MONEY + r".*?first ([\d,]+) KWh used in a\s*"
                    r"two-month billing period, per kWh " + _MONEY + r".*?in excess of ([\d,]+) kWh in a "
                    r"two-month billing\s*period, per kWh " + _MONEY, sections["com"].group(1), re.S | re.I)
    if not (res and sea and com):
        raise ValueError("Schedule G prices incomplete")
    if com.group(2) != com.group(4):
        raise ValueError("commercial block bounds disagree")
    return {"res_basic": float(res.group(1)), "res_energy": float(res.group(2)),
            "com_basic": float(com.group(1)), "com_block": float(com.group(2).replace(",", "")),
            "com_first": float(com.group(3)), "com_balance": float(com.group(5)),
            "sea_basic": float(sea.group(1)), "sea_energy": float(sea.group(2))}


def amendment_effective(pages: list[DocumentPage]) -> str:
    text = "\n".join(page.text for page in pages)
    match = re.search(r"The effective date of this amending bylaw shall be " + _DATE, text)
    if not match:
        raise ValueError("amending bylaw effective date not found")
    return _iso(match.group(1))


def parse_schedule(consolidation: list[DocumentPage], amendment: list[DocumentPage], consolidation_url: str,
                   amendment_url: str, today: Optional[date] = None, discovery_note: str = "") -> list[TariffRecord]:
    """Build Schedule G records; fail closed when the schedule, its amending bylaw's date or matching prices
    are missing, or the amendment is not yet in effect."""
    today = today or date.today()
    text, number, pages = schedule_g(consolidation)
    prices = _prices(text)
    amended = "\n".join(page.text for page in amendment)
    if not re.search(rf"BYLAW NO\. {re.escape(number)}\b", amended, re.I):
        raise ValueError(f"amending bylaw does not identify itself as Bylaw No. {number}")
    if _prices(amended[amended.find("ELECTRICAL UTILITY FEES AND CHARGES"):]) != prices:
        raise ValueError(f"amending bylaw {number} prices differ from the consolidation")
    effective = amendment_effective(amendment)
    if date.fromisoformat(effective) > today:
        raise ValueError(f"Schedule G (Bylaw {number}) takes effect {effective}, after {today.isoformat()}")
    detail = (f"Fees & Charges Bylaw No. 1958 (consolidated), Schedule G (Bylaw {number}, effective {effective}), "
              f"PDF page{'s' if len(pages) > 1 else ''} {', '.join(map(str, pages))}")

    def comp(**fields) -> RateComponent:
        return RateComponent(effective_date=effective, source_url=consolidation_url, source_detail=detail,
                             confidence="high", **fields)

    block = prices["com_block"]
    specs = [
        ("1", "Residential Service", "residential", "residential", "flat",
         [comp(component_type="fixed", component_name="Basic Minimum Service Charge", charge_value=prices["res_basic"],
               charge_unit="$/month"),
          comp(component_type="energy", component_name="Electrical Usage Charge", charge_value=prices["res_energy"],
               charge_unit="$/kWh")]),
        ("2", "Commercial/Industrial/Institutional Service", "commercial", "commercial, industrial and institutional",
         "tiered",
         [comp(component_type="fixed", component_name="Basic Minimum Service Charge", charge_value=prices["com_basic"],
               charge_unit="$/month"),
          comp(component_type="energy", component_name=f"Electrical Usage Charge — First {block:,.0f} kWh",
               charge_value=prices["com_first"], charge_unit="$/kWh", tier_number=1, tier_threshold=block,
               tier_unit="kWh", notes=f"First {block:,.0f} kWh used in a two-month billing period."),
          comp(component_type="energy", component_name=f"Electrical Usage Charge — Above {block:,.0f} kWh",
               charge_value=prices["com_balance"], charge_unit="$/kWh", tier_number=2, tier_threshold=block,
               tier_unit="kWh", notes=f"Usage in excess of {block:,.0f} kWh in a two-month billing period.")]),
        ("3", "Seasonal Loads", "commercial", "seasonal loads (minimum three months of service)", "flat",
         [comp(component_type="fixed", component_name="Basic Minimum Service Charge", charge_value=prices["sea_basic"],
               charge_unit="$/month"),
          comp(component_type="energy", component_name="Electrical Usage Charge", charge_value=prices["sea_energy"],
               charge_unit="$/kWh")]),
    ]
    records = []
    for code, name, customer_class, sub_class, structure, components in specs:
        notes = (f"City of Grand Forks Schedule G item {code}. Council-set rates; the effective date comes from "
                 f"amending Bylaw {number} ({amendment_url}).")
        if discovery_note:
            notes += " " + discovery_note
        records.append(TariffRecord(
            utility_name=UTILITY, province="BC", utility_type="electricity", tariff_name=name,
            tariff_code=f"G-{code}", customer_class=customer_class, sub_class=sub_class, rate_structure=structure,
            pricing_method="municipal", effective_date=effective, source_url=consolidation_url, source_page=detail,
            confidence="high", notes=notes, components=components,
        ))
    return records


class GrandForksScraper(BaseScraper):
    """Parse the City of Grand Forks electrical utility rates (Fees & Charges Bylaw Schedule G)."""

    def __init__(self) -> None:
        super().__init__(utility_name=UTILITY, province="BC")

    def scrape(self) -> list[TariffRecord]:
        # No seed fallback for batch 18 utilities (owner confirmed 2026-11-17).
        records = self._try_live_scrape()
        if not records:
            self.logger.warning("Grand Forks: no live records (no seed fallback)")
        return records

    def _media(self, query: str, pattern: re.Pattern) -> Optional[str]:
        try:
            return newest_media_url(self.fetch_page(MEDIA_SEARCH_URL.format(query=query)), pattern)
        except Exception as exc:
            self.logger.warning("Grand Forks media search '%s' failed: %s", query, exc)
            return None

    def _try_live_scrape(self) -> list[TariffRecord]:
        note = ""
        try:
            try:
                library = self.fetch_page(DOCUMENT_LIBRARY_URL)
            except RequestException as exc:
                self.logger.warning("Grand Forks document library unavailable: %s", exc)
                library = ""
            consolidation_url = newest_document_url(library, _CONSOLIDATION) or self._media(
                "CONSOLIDATED", _CONSOLIDATION)
            if not consolidation_url:
                consolidation_url = LAST_KNOWN_CONSOLIDATION_URL
                note = ("Neither the document library nor media search found a consolidation, so the last known "
                        "one was read (it may not be current).")
            consolidation = extract_pdf_pages(self.fetch_bytes(consolidation_url), drop_repeated_lines=False)
            _, number, _ = schedule_g(consolidation)
            pattern = amendment_pattern(number)
            amendment_url = newest_document_url(library, pattern) or self._media(number, pattern)
            if not amendment_url:
                raise ValueError(f"amending bylaw {number} not found in the document library or media search")
            amendment = extract_pdf_pages(self.fetch_bytes(amendment_url), drop_repeated_lines=False)
            records = parse_schedule(consolidation, amendment, consolidation_url, amendment_url, discovery_note=note)
        except Exception as exc:
            self.logger.warning("Grand Forks Schedule G failed closed: %s", exc)
            return []
        return self.mark_live_parsed(records)
