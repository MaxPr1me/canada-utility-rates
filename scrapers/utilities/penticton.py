"""
penticton.py — Scraper for the City of Penticton electric utility (British Columbia).

Official sources:
  - Fees and Charges Bylaw No. 2014-07 (consolidated package), Schedule A Appendix 7 "Electric": electric
    rates by rate code, printed in side-by-side year columns ("ELECTRIC 2025 2026"; the 2026 column was set
    by Bylaw No. 2025-22, adopted September 16, 2025). Found on the City's bylaw directory
    (https://www.penticton.ca/city-hall/bylaw-directory, paged).
  - Electric & Water Accounts page: "City Utility bills are mailed monthly", which makes the schedule's
    "per billing" prices monthly. The sentence must be present or the run fails closed.

The current year's column is used; a document without a column for the current year fails closed (no
stale column is carried into a new year). The bylaw prints only the year, so records are dated January 1
of that year with a note (batch 18 provisional decision, 2026-11-04). Council sets these rates; the BCUC
does not regulate them.

Scope: Rate Code 10 Residential and the general service codes 20 (secondary metered, City-owned
transformation), 25 (primary metered, City-owned), 30 (secondary, customer-owned) and 35 (primary,
customer-owned); each code prints its own discounted prices. Demand is billed per kVA in excess of 45 kVA,
stored as a $0 first block. Excluded: Rate Code 45 City accounts (batch 18 provisional decision,
2026-11-04), Rate Code 55 lighting and unmetered loads, net metering and service fees.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional
from urllib.parse import urljoin

from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

UTILITY = "City of Penticton"
DIRECTORY_URL = "https://www.penticton.ca/city-hall/bylaw-directory"
ACCOUNTS_URL = "https://www.penticton.ca/city-services/utility-electrical-services/electric-water-accounts"
LAST_KNOWN_BYLAW_URL = ("https://www.penticton.ca/sites/default/files/uploads/bylaws/2014-07%20Fees%20and%20Charges%20"
                        "Bylaw%20-%20CONSOLIDATED%20PACKAGE%20-%20October%202026_1.pdf")
MONTHLY_BILLS = re.compile(r"City Utility bills are mailed monthly")
_P = r"\$(\d+(?:\.\d+)?)"

CODES = {
    "10": ("Residential", "residential", "residential", r"Rate Code 10 - Residential"),
    "20": ("General – Secondary Metered, City-Owned Transformation", "commercial",
           "general service, secondary metered, City-owned transformation",
           r"Rate Code 20 - General - Secondary metered and City owned Transformation"),
    "25": ("General – Primary Metered, City-Owned Transformation", "commercial",
           "general service, primary metered, City-owned transformation",
           r"Rate Code 25 - General - Primary metered and City owned Transformation"),
    "30": ("General – Secondary Metered, Customer-Owned Transformation", "commercial",
           "general service, secondary metered, customer-owned transformation",
           r"Rate Code 30 - General - Secondary metered and customer owned Transformation"),
    "35": ("General – Primary Metered, Customer-Owned Transformation", "commercial",
           "general service, primary metered, customer-owned transformation",
           r"Rate Code 35 - General - Primary metered and customer owned Transformation"),
}


def find_bylaw_url(html: str, base_url: str = DIRECTORY_URL) -> Optional[str]:
    """The consolidated Fees and Charges Bylaw No. 2014-07 link on a bylaw directory page."""
    for anchor in parse_html(html or "").find_all("a", href=True):
        label = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))
        if label.startswith("Fees and Charges Bylaw No. 2014-07") and ".pdf" in anchor["href"].lower():
            return urljoin(base_url, anchor["href"])
    return None


def _pair(pattern: str, body: str, what: str) -> tuple[float, float]:
    match = re.search(pattern, body, re.S)
    if not match:
        raise ValueError(f"{what} not found")
    return float(match.group(1)), float(match.group(2))


def parse_appendix(pages: list[DocumentPage], source_url: str, accounts_text: str, today: Optional[date] = None,
                   discovery_note: str = "") -> list[TariffRecord]:
    """Build the in-scope Appendix 7 electric classes for the current year's column; raise ValueError (fail
    closed) when the monthly-billing evidence, the year column, a class or a price is missing."""
    today = today or date.today()
    if not MONTHLY_BILLS.search(re.sub(r"\s+", " ", accounts_text or "")):
        raise ValueError("monthly billing statement not found on the accounts page")
    electric = [p for p in pages if re.search(r"Appendix 7", p.text) and re.search(r"Rate Code \d", p.text)]
    if not electric:
        raise ValueError("Appendix 7 electric rates not found")
    years = re.search(r"ELECTRIC (\d{4}) (\d{4})", "\n".join(p.text for p in pages))
    if not years:
        raise ValueError("Appendix 7 year columns not found")
    columns = (int(years.group(1)), int(years.group(2)))
    if today.year not in columns:
        raise ValueError(f"no {today.year} column (columns {columns[0]} and {columns[1]})")
    column = columns.index(today.year)
    effective = f"{today.year}-01-01"
    text = re.sub(r"\s+", " ", "\n".join(p.text for p in electric))
    numbers = [p.page_number for p in electric]
    detail = (f"Fees and Charges Bylaw No. 2014-07 (consolidated), Schedule A Appendix 7 Electric, {today.year} column, "
              f"PDF pages {numbers[0]}-{numbers[-1]}")
    starts = sorted((m.start(), code) for code, (_, _, _, heading) in CODES.items()
                    for m in [re.search(heading, text)] if m)
    if len(starts) != len(CODES):
        found = {code for _, code in starts}
        raise ValueError(f"rate codes missing: {', '.join(sorted(set(CODES) - found))}")
    stops = [m.start() for m in re.finditer(r"Rate Code (?:- )?\d", text)]
    records = []
    for start, code in starts:
        end = min([s for s in stops if s > start] + [len(text)])
        body = text[start:end]
        name, customer_class, sub_class, _ = CODES[code]

        def comp(**fields) -> RateComponent:
            return RateComponent(effective_date=effective, source_url=source_url,
                                 source_detail=f"{detail}, Rate Code {code}", confidence="high", **fields)

        basic = _pair(_P + r" per billing plus " + _P + r" per billing plus", body, f"Rate Code {code} basic charge")
        components = [comp(component_type="fixed", component_name="Basic Charge", charge_value=basic[column],
                           charge_unit="$/month", notes="Per billing; City utility bills are monthly.")]
        if code == "10":
            energy = _pair(_P + r" per kWh for all " + _P + r" per kWh for all", body, "Rate Code 10 energy charge")
            components.append(comp(component_type="energy", component_name="Energy Charge",
                                   charge_value=energy[column], charge_unit="$/kWh",
                                   notes="All consumption during the billing period."))
            structure = "flat"
        else:
            first = _pair(r"First [\d,]+ kwh per billing " + _P + r" per kWh " + _P + r" per kWh", body,
                          f"Rate Code {code} first block")
            block1 = float(re.search(r"First ([\d,]+) kwh per billing", body).group(1).replace(",", ""))
            block2 = block1 + float(re.search(r"Next ([\d,]+) kwh per billing", body).group(1).replace(",", ""))
            second = _pair(r"Next [\d,]+ kwh per billing " + _P + r" per kWh " + _P + r" per kWh", body,
                           f"Rate Code {code} second block")
            third = _pair(r"Additional kwh per billing " + _P + r" per kWh " + _P + r" per kWh", body,
                          f"Rate Code {code} third block")
            demand = _pair(_P + r" per KVA of billing " + _P + r" per KVA of billing", body, f"Rate Code {code} demand")
            free = re.findall(r"in excess of (\d+) ?KVA", body, re.I)
            if not free or len(set(free)) != 1:
                raise ValueError(f"Rate Code {code} demand threshold missing or inconsistent")
            free_kva = float(free[0])
            components += [
                comp(component_type="energy", component_name=f"Energy Charge — First {block1:,.0f} kWh",
                     charge_value=first[column], charge_unit="$/kWh", tier_number=1, tier_threshold=block1,
                     tier_unit="kWh/month"),
                comp(component_type="energy", component_name=f"Energy Charge — Next {block2 - block1:,.0f} kWh",
                     charge_value=second[column], charge_unit="$/kWh", tier_number=2, tier_threshold=block2,
                     tier_unit="kWh/month"),
                comp(component_type="energy", component_name="Energy Charge — Additional kWh", charge_value=third[column],
                     charge_unit="$/kWh", tier_number=3, tier_threshold=block2, tier_unit="kWh/month"),
                comp(component_type="demand", component_name=f"Demand Charge — First {free_kva:g} kVA", charge_value=0.0,
                     charge_unit="$/kVA/month", demand_unit="kVA", tier_number=1, tier_threshold=free_kva,
                     tier_unit="kVA"),
                comp(component_type="demand", component_name=f"Demand Charge — Above {free_kva:g} kVA",
                     charge_value=demand[column], charge_unit="$/kVA/month", demand_unit="kVA", tier_number=2,
                     tier_threshold=free_kva, tier_unit="kVA",
                     notes=(f"Per kVA of billing demand: the greater of the maximum kVA demand in excess of {free_kva:g} "
                            f"kVA for the current billing, or 75% of the maximum kVA billable demand in excess of "
                            f"{free_kva:g} kVA recorded during the previous 364 days.")),
            ]
            structure = "demand"
        notes = (f"City of Penticton Rate Code {code}. Council-set rates. The bylaw column is headed only "
                 f"'{today.year}' (no day), so the rates are dated January 1, {today.year}.")
        if discovery_note:
            notes += " " + discovery_note
        records.append(TariffRecord(
            utility_name=UTILITY, province="BC", utility_type="electricity", tariff_name=name, tariff_code=code,
            customer_class=customer_class, sub_class=sub_class, rate_structure=structure, pricing_method="municipal",
            effective_date=effective, source_url=source_url, source_page=detail, confidence="high", notes=notes,
            components=components))
    return records


class PentictonScraper(BaseScraper):
    """Parse the City of Penticton electric rates (Fees and Charges Bylaw, Appendix 7)."""

    def __init__(self) -> None:
        super().__init__(utility_name=UTILITY, province="BC")

    def scrape(self) -> list[TariffRecord]:
        # No seed fallback for utilities added in batch 18 (provisional decision 2026-11-04).
        records = self._try_live_scrape()
        if not records:
            self.logger.warning("Penticton: no live records (no seed fallback)")
        return records

    def _discover(self) -> tuple[str, str]:
        for page in range(4):
            try:
                url = find_bylaw_url(self.fetch_page(f"{DIRECTORY_URL}?page={page}" if page else DIRECTORY_URL))
            except Exception as exc:
                self.logger.warning("Penticton bylaw directory page %d unavailable: %s", page, exc)
                continue
            if url:
                return url, ""
        return LAST_KNOWN_BYLAW_URL, ("The bylaw directory did not link the Fees and Charges Bylaw, so the last "
                                      "known consolidation was read (it may not be the current one).")

    def _try_live_scrape(self) -> list[TariffRecord]:
        url, note = self._discover()
        try:
            accounts = parse_html(self.fetch_page(ACCOUNTS_URL)).get_text(" ")
            pages = extract_pdf_pages(self.fetch_bytes(url), drop_repeated_lines=False)
            records = parse_appendix(pages, url, accounts, discovery_note=note)
        except Exception as exc:
            self.logger.warning("Penticton Appendix 7 failed closed: %s", exc)
            return []
        return self.mark_live_parsed(records)
