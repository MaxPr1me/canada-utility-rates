"""
nelson_hydro.py — Scraper for Nelson Hydro, the City of Nelson's electric utility (British Columbia).

Official sources:
  - Electrical Rates page (https://www.nelson.ca/231/Electrical-Rates): "Electric Rates Effective January 1,
    2026" with the A1, A3, B1 and B4 basic and energy charges, and a link to the Hydro Services Bylaw ("View
    the full set of the interim approved 2026 and 2027 electrical rates in Schedules B and C").
  - Hydro Services Bylaw No. 3608 (consolidated, City CivicWeb document store): Schedule B (urban) and C
    (rural) print each class once per year, headed for example "A1: Residential Rate Urban (2026)". The
    bylaw also carries an older, unlabelled rural schedule, which is never read.

The bylaw schedules labelled with the current year apply from January 1 of that year (owner decision 2026-11-23).
The rates page is compared only when it shows the current year: its effective date is then the records' date
and its four values must equal the bylaw's, or the run fails closed. While the page still shows another year
(for example 2026 in early January 2027), the bylaw's current-year schedules are read without the comparison
and dated January 1. Each year's prices end on December 31 of that year (owner decision 2026-11-23: a price
whose source labels it with a year ends with it), so a year the bylaw does not print fails closed and the
previous year's prices stop counting. The rates are interim (BCUC-regulated for rural customers), so records
carry medium confidence.

Scope: A1/A3 residential and B1/B4 small commercial (loads up to 25 kVA without a demand meter), urban and
rural, billed every two months. The residential demand charge for demand above 20 kW per period is stored
as a conditional component. Excluded: C1/C4 large commercial until Nelson Hydro confirms whether ">25 kVA:
$10.33 per kVA" bills only the kVA above 25 (owner confirmed 2026-11-17), E1 City of Nelson
accounts, EV1 charging, F1/F2 flat commercial service under 400 kWh per period, G-3 lighting and M1/M2
manual meter reading.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

UTILITY = "Nelson Hydro"
RATES_PAGE_URL = "https://www.nelson.ca/231/Electrical-Rates"
DOCUMENT_URL = "https://nelson.civicweb.net/document/{doc_id}"
LAST_KNOWN_DOC_ID = "108411"

CLASSES = {
    "A1": ("Residential Rate Urban", "residential", "residential, urban", "Residential Rate Urban"),
    "A3": ("Residential Rate Rural", "residential", "residential, rural", "Residential Rate Rural"),
    "B1": ("Small Commercial Rate Urban", "commercial", "small commercial, urban (up to 25 kVA, no demand meter)",
           "Small Commercial Rate Urban"),
    "B4": ("Small Commercial Rate Rural", "commercial", "small commercial, rural (up to 25 kVA, no demand meter)",
           "Small Commercial Services Rate Rural"),
}
_P = r"\$\s?(\d+(?:\.\d+)?)"


def _iso(text: str) -> str:
    return datetime.strptime(text, "%B %d, %Y").date().isoformat()


def parse_rates_page(html: str) -> tuple[str, dict[str, tuple[float, float]], Optional[str]]:
    """(effective date, {code: (basic per period, energy $/kWh)}, bylaw CivicWeb document id) from the page."""
    soup = parse_html(html or "")
    text = re.sub(r"\s+", " ", soup.get_text(" ")).replace("\u00a0", " ")
    dated = re.search(r"Electric Rates Effective ([A-Z][a-z]+ \d{1,2}, \d{4})", text)
    if not dated:
        raise ValueError("rates page effective date not found")
    values = {}
    for code in CLASSES:
        match = re.search(rf"{code}: [A-Za-z ]+? Period: Bi-Monthly Basic Charge: ?{_P} per period Energy Charge: "
                          rf"{_P}/kWh", text)
        if not match:
            raise ValueError(f"rates page {code} values not found")
        values[code] = (float(match.group(1)), float(match.group(2)))
    doc_id = None
    for anchor in soup.find_all("a", href=True):
        found = re.search(r"civicweb\.net/(?:filepro/documents/\?.*?preview=|document/)(\d+)", anchor["href"])
        if found and "Hydro Services Bylaw" in anchor.get_text(" ", strip=True):
            doc_id = found.group(1)
            break
    return _iso(dated.group(1)), values, doc_id


def _schedule(pages: list[DocumentPage], code: str, year: int) -> tuple[str, int]:
    heading = re.compile(rf"{code}: {re.escape(CLASSES[code][3])} \({year}\)")
    for page in pages:
        match = heading.search(page.text)
        if match:
            return page.text[match.start():], page.page_number
    raise ValueError(f"bylaw schedule {code} ({year}) not found")


def _schedule_years(pages: list[DocumentPage], code: str) -> list[int]:
    """The years for which the bylaw prints a schedule of this class."""
    heading = re.compile(rf"{code}: {re.escape(CLASSES[code][3])} \((\d{{4}})\)")
    return sorted({int(found) for page in pages for found in heading.findall(page.text)})


def parse_rates(page_html: str, pages: list[DocumentPage], bylaw_url: str, today: Optional[date] = None,
                discovery_note: str = "") -> list[TariffRecord]:
    """Build A1/A3/B1/B4 from the bylaw schedules labelled with the current year, ending December 31; raise
    ValueError (fail closed) when a schedule is missing or changed, or when the page shows the current year and
    disagrees with the bylaw (owner decisions 2026-11-23, see the module docstring)."""
    today = today or date.today()
    page_effective, page_values, _ = parse_rates_page(page_html)
    year = today.year
    page_is_current = int(page_effective[:4]) == year
    if page_is_current:
        if date.fromisoformat(page_effective) > today:
            raise ValueError(f"rates page effective {page_effective} is after {today.isoformat()}")
        effective = page_effective
        check = f"cross-checked against the Electrical Rates page (effective {page_effective})"
    else:
        effective = date(year, 1, 1).isoformat()
        check = (f"not compared with the Electrical Rates page, which shows the rates effective {page_effective} "
                 f"rather than {year}'s")
    end = date(year, 12, 31).isoformat()
    records = []
    for code, (name, customer_class, sub_class, _) in CLASSES.items():
        text, page_number = _schedule(pages, code, year)
        body = re.sub(r"\s+", " ", text.split("Order No.")[0])
        if "Billing Period: Bi-Monthly" not in body:
            raise ValueError(f"{code} ({year}) is not billed bi-monthly")
        basic = re.search(r"Basic Charge: " + _P + r" per Period", body)
        energy = re.search(r"All kWh per Period: " + _P + r" per kWh", body)
        if not basic or not energy:
            raise ValueError(f"{code} ({year}) basic or energy charge missing")
        values = (float(basic.group(1)), float(energy.group(1)))
        if page_is_current and values != page_values[code]:
            raise ValueError(f"{code} bylaw values {values} differ from the rates page {page_values[code]}")
        detail = (f"Hydro Services Bylaw No. 3608 (consolidated), Schedule {'B' if code in ('A1', 'B1') else 'C'} "
                  f"{code} ({year}), PDF page {page_number}; {check}")

        def comp(**fields) -> RateComponent:
            return RateComponent(effective_date=effective, end_date=end, source_url=bylaw_url, source_detail=detail,
                                 confidence="medium", **fields)

        components = [
            comp(component_type="fixed", component_name="Basic Charge", charge_value=values[0],
                 charge_unit="$/two months", notes="Per bi-monthly billing period; also the minimum charge."),
            comp(component_type="energy", component_name="Energy Charge", charge_value=values[1], charge_unit="$/kWh",
                 notes="All kWh per bi-monthly period."),
        ]
        if customer_class == "residential":
            demand = re.search(r"First (\d+) kW: nil Each additional kW greater than \1 kW per Period is " + _P
                               + r" per kW", body)
            if not demand:
                raise ValueError(f"{code} ({year}) demand charge wording changed")
            components.append(comp(
                component_type="demand", component_name=f"Demand Charge — Above {demand.group(1)} kW",
                charge_value=float(demand.group(2)), charge_unit="$/kW/two months", demand_unit="kW",
                sub_component="conditional",
                notes=(f"Conditional: per kW of demand greater than {demand.group(1)} kW in a bi-monthly billing "
                       f"period; the first {demand.group(1)} kW are not charged.")))
        elif "Surcharge percentages may apply as per Section 4.9" in body:
            components[-1].notes += " A power factor surcharge may apply (bylaw Section 4.9)."
        printed = ", ".join(str(y) for y in _schedule_years(pages, code))
        notes = (f"Nelson Hydro {code}. Interim approved {year} rates, in force January 1 to December 31, {year} "
                 f"(the bylaw prints this class for {printed}); billed every two months.")
        if not page_is_current:
            notes += (f" The rates page shows the rates effective {page_effective}; the bylaw's {year} schedule "
                      f"applies from January 1, {year} (owner decision 2026-11-23).")
        if discovery_note:
            notes += " " + discovery_note
        records.append(TariffRecord(
            utility_name=UTILITY, province="BC", utility_type="electricity", tariff_name=name, tariff_code=code,
            customer_class=customer_class, sub_class=sub_class, demand_max_kw=None, rate_structure="flat",
            pricing_method="regulated", effective_date=effective, end_date=end, source_url=bylaw_url,
            source_page=detail, confidence="medium", notes=notes, components=components))
    return records


class NelsonHydroScraper(BaseScraper):
    """Parse Nelson Hydro's residential and small commercial rates (Hydro Services Bylaw schedules)."""

    def __init__(self) -> None:
        super().__init__(utility_name=UTILITY, province="BC")

    def scrape(self) -> list[TariffRecord]:
        # No seed fallback for batch 18 utilities (owner confirmed 2026-11-17).
        records = self._try_live_scrape()
        if not records:
            self.logger.warning("Nelson Hydro: no live records (no seed fallback)")
        return records

    def _try_live_scrape(self) -> list[TariffRecord]:
        try:
            html = self.fetch_page(RATES_PAGE_URL)
            _, _, doc_id = parse_rates_page(html)
            note = ""
            if not doc_id:
                doc_id, note = LAST_KNOWN_DOC_ID, ("The rates page did not link the Hydro Services Bylaw, so the last "
                                                   "known CivicWeb document was read.")
            url = DOCUMENT_URL.format(doc_id=doc_id)
            pages = extract_pdf_pages(self.fetch_bytes(url), drop_repeated_lines=False)
            records = parse_rates(html, pages, url, discovery_note=note)
        except Exception as exc:
            self.logger.warning("Nelson Hydro failed closed: %s", exc)
            return []
        return self.mark_live_parsed(records)
