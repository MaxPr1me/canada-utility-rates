"""
medicine_hat.py — Scraper for the City of Medicine Hat Electric Utility (Alberta).

Medicine Hat generates, distributes and sells electricity itself, so each record bundles the City's delivery
charges with its own default energy price (owner decision 2026-11-04: a bundled city utility counts as one).

Official sources:
- The City's "Energy Plans & Pricing" page
  (https://www.medicinehat.ca/home-property-utilities/utilities/energy-plans-pricing/): the monthly default
  electricity rate for residential, farm, small and medium commercial customers (the row for the current month
  must exist and equal the page's "Current Electricity Rate"), the fixed default rate for Large Commercial and
  Industrial customers with its term (2025-2026, until December 31, 2026), and the "Going Green" surcharge. The
  page also links the brochure as "Current Utility Rates".
- The 2026 Utility Rates brochure: delivery charges by rate class, read one page column at a time because the
  two printed columns interleave in plain text extraction.

Decisions:
- Large Commercial (4.1) and Industrial (5.1): the City publishes their fixed default rate, so they are complete
  records (delivery plus energy) and are kept out of the representative models (owner decisions 2026-11-19).
  After their rate's term ends they fail closed until the next term is published.
- Each record ends with its shortest-lived price: the month for 1.1, 3.1 and 3.3 (default rate and Going Green
  surcharge), the fixed rate's term for 4.1 and 5.1. Models and the coverage gate stop using a record after its end
  date until a newer one is stored. The scheduled run on the 1st usually comes before the City posts the month's
  row and fails closed; the owner then starts a Medicine Hat run once it is posted (owner decisions 2026-11-19).
- The Going Green surcharge is printed without a date ("calculated monthly"), so it is stored as a charge for
  the month it was read, with a note (owner decision 2026-11-19). It applies to residential, small and medium
  commercial customers only.
- The Municipal Consent & Access Fee (within city limits only) stays a note, as for Alberta's other municipal
  access fees. Demand charges are per kVA of the peak recorded in the monthly billing period.

Scope: 1.1 Residential, 3.1 Small Commercial, 3.3 Medium Commercial, 4.1 Large Commercial - Primary and
5.1 Industrial - Primary. Excluded: farm (2.1), temporary (3.2, 3.4) and irrigation (3.5, 3.6) services,
unmetered (6.1), rental and street lighting (7.0, 8.0). No seed fallback: a failed source returns no records;
when the page links no brochure, the last known brochure is read with a note.
"""

from __future__ import annotations

import calendar
import io
import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import urljoin

from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage, parse_html

UTILITY = "City of Medicine Hat Electric Utility"
ENERGY_PAGE_URL = "https://www.medicinehat.ca/home-property-utilities/utilities/energy-plans-pricing/"
LAST_KNOWN_BROCHURE_URL = ("https://media-002-ca.cdn.govstack.com/medicinehat-016-ca/media/vhua0uvl/"
                           "2026-utility-rate-brochure.pdf")

# code: (name, customer class, rate structure, required charge labels, uses the small-customer energy rate)
CLASSES = {
    "1.1": ("Residential", "residential", "tiered", ("Service Charge", "Administration Charge",
                                                    "Facilities Usage", "Capacity Charge"), True),
    "3.1": ("Small Commercial", "commercial", "flat", ("Service Charge", "Administration Charge",
                                                      "Facilities Usage", "Capacity Charge"), True),
    "3.3": ("Medium Commercial", "commercial", "demand", ("Service Charge", "Administration Charge",
                                                         "Demand Charge", "Capacity Charge"), True),
    "4.1": ("Large Commercial - Primary", "commercial", "demand", ("Service Charge", "Administration Charge",
                                                                  "Demand Charge", "Capacity Charge"), False),
    "5.1": ("Industrial - Primary", "industrial", "demand", ("Service Charge", "Administration Charge",
                                                            "Demand Charge", "Capacity Charge"), False),
}
COMPONENT_TYPES = {"Service Charge": "fixed", "Administration Charge": "fixed", "Facilities Usage": "delivery",
                   "Capacity Charge": "energy", "Demand Charge": "demand"}
NOTES = {
    "Facilities Usage": "Covers the electric distribution, transmission and substation infrastructure (brochure).",
    "Capacity Charge": "Contributes to the cost of generating power for the service area (brochure).",
    "Demand Charge": "Per kVA of the peak demand recorded in the monthly billing period (the City's distribution "
                     "charges page).",
}

_LONG_DATE = r"[A-Z][a-z]+ \d{1,2}, \d{4}"
_HEADING = re.compile(r"^(\d\.\d) ([A-Z][A-Z &/-]*[A-Z])$")
_STOP = re.compile(r"^(?:\*MCAF|E Within|N Outside|WATER\b|SEWER\b|SOLID WASTE\b|NATURAL GAS\b)")
_PRICE = re.compile(r"^(?P<label>[A-Za-z][A-Za-z* ]*?)\s+\$(?P<value>\d+(?:\.\d+)?) per (?P<unit>day|kWh|kVA)$")
_ELECTRIC_DATE = re.compile(r"“E”\s*/\s*“N”\s*[–-]\s*Effective (" + _LONG_DATE + ")")


def _iso(text: str) -> str:
    return datetime.strptime(text, "%B %d, %Y").date().isoformat()


def _flat(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def extract_brochure_columns(pdf_bytes: bytes) -> list[DocumentPage]:
    """Each page's left half then right half: the brochure prints two independent columns per page."""
    import pdfplumber

    pages: list[DocumentPage] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            halves = [page.crop(box).extract_text(x_tolerance=2, y_tolerance=3) or ""
                      for box in ((0, 0, page.width / 2, page.height), (page.width / 2, 0, page.width, page.height))]
            text = "\n".join(halves).strip()
            if len(re.sub(r"\W", "", text)) >= 20:
                pages.append(DocumentPage(number, text))
    return pages


def find_brochure_url(html: str, base_url: str = ENERGY_PAGE_URL) -> Optional[str]:
    for anchor in parse_html(html or "").find_all("a", href=True):
        if _flat(anchor) == "Current Utility Rates" and anchor["href"].lower().split("?")[0].endswith(".pdf"):
            return urljoin(base_url, anchor["href"])
    return None


def _tables(html: str) -> list[list[list[str]]]:
    return [[[_flat(cell) for cell in row.find_all(["td", "th"])] for row in table.find_all("tr")]
            for table in parse_html(html or "").find_all("table")]


def parse_energy_page(html: str, today: date) -> dict:
    """Default energy prices and the Going Green surcharge; ValueError (fail closed) on a missing or odd value."""
    text = _flat(parse_html(html or ""))
    month = f"{calendar.month_name[today.month]} {today.year}"
    small = [table for table in _tables(html) if table and table[0][:1]
             and table[0][0].startswith("for Residential, Farm, Small and Medium Commercial")
             and "Electricity (per kWh)" in table[0]]
    if len(small) != 1:
        raise ValueError("default electricity rate table for residential and small/medium commercial not found")
    rows = [row for row in small[0][1:] if row and row[0] == month]
    column = small[0][0].index("Electricity (per kWh)")
    found = re.fullmatch(r"\$(\d+\.\d+)/kWh", rows[0][column]) if len(rows) == 1 and len(rows[0]) > column else None
    if not found:
        raise ValueError(f"no single {month} default electricity rate in $/kWh")
    current = re.search(r"Current Electricity Rate \$(\d+\.\d+) / kWh", text)
    if not current or current.group(1) != found.group(1):
        raise ValueError(f"the page's Current Electricity Rate does not equal the {month} table row")
    rate = float(found.group(1))
    if not 0 < rate < 1:
        raise ValueError(f"{month} default electricity rate {rate} $/kWh is implausible")
    start = today.replace(day=1)
    result = {"month": month, "start": start.isoformat(),
              "end": start.replace(day=calendar.monthrange(start.year, start.month)[1]).isoformat(),
              "small_rate": rate, "large": None, "going_green": None}
    large = [table for table in _tables(html) if table and table[0][:1]
             and table[0][0].startswith("for Large Commercial, Industrial and Street Lighting")
             and "Electricity (per kWh)" in table[0]]
    if len(large) == 1 and len(large[0]) == 2 and len(large[0][1]) == 2:
        period, price = large[0][1]
        years = re.match(r"(\d{4})-(\d{4})\b", period)
        until = re.search(r"until (" + _LONG_DATE + r")", period)
        value = re.fullmatch(r"\$(\d+\.\d+)/kWh", price)
        if years and until and value and _iso(until.group(1))[:4] == years.group(2):
            result["large"] = {"rate": float(value.group(1)), "start": f"{years.group(1)}-01-01",
                               "end": _iso(until.group(1)), "period": period}
    green = re.search(r"Going Green.{0,300}?for residential, farm, small and medium commercial customers\. "
                      r"The Going Green surcharge is \$(\d+\.\d+) per kilowatt hour", text)
    if green:
        result["going_green"] = float(green.group(1))
    return result


def _blocks(pages: list[DocumentPage]) -> tuple[dict[str, dict], set[str]]:
    """Electric rate-class blocks {code: {heading, page, lines}} and the brochure's electric effective dates."""
    blocks: dict[str, dict] = {}
    dates: set[str] = set()
    for page in pages:
        dates.update(_iso(found) for found in _ELECTRIC_DATE.findall(page.text))
        current = None
        for raw in page.text.splitlines():
            line = " ".join(raw.split())
            heading = _HEADING.match(line)
            if heading:
                if heading.group(1) in blocks:
                    raise ValueError(f"rate {heading.group(1)} printed twice")
                current = blocks[heading.group(1)] = {"heading": heading.group(2), "page": page.page_number,
                                                      "lines": []}
            elif current is not None and _STOP.match(line):
                current = None
            elif current is not None:
                current["lines"].append(line)
    return blocks, dates


def _prices(lines: list[str]) -> dict[str, tuple[float, str]]:
    prices: dict[str, tuple[float, str]] = {}
    for line in lines:
        found = _PRICE.match(line)
        if found:
            label = found.group("label").strip()
            if label in prices:
                raise ValueError(f"{label} printed twice")
            prices[label] = (float(found.group("value")), found.group("unit"))
    return prices


def parse_rates(pages: list[DocumentPage], energy: dict, source_url: str, today: date,
                energy_url: str = ENERGY_PAGE_URL, discovery_note: str = "") -> tuple[list[TariffRecord], dict]:
    """Build the in-scope bundled records; return (records, {code: rejection reason})."""
    blocks, dates = _blocks(pages)
    if len(dates) != 1:
        raise ValueError(f"brochure electric effective dates not found or inconsistent: {sorted(dates)}")
    effective = dates.pop()
    if date.fromisoformat(effective) > today:
        raise ValueError(f"brochure rates take effect {effective}, after {today.isoformat()}")
    records: list[TariffRecord] = []
    rejections: dict[str, str] = {}
    for code, (name, customer_class, structure, required, small) in CLASSES.items():
        block = blocks.get(code)
        if block is None:
            rejections[code] = "rate class not found in the brochure"
            continue
        try:
            prices = _prices(block["lines"])
        except ValueError as exc:
            rejections[code] = str(exc)
            continue
        missing = [label for label in required if label not in prices]
        if missing:
            rejections[code] = f"missing {', '.join(missing)}"
            continue
        if not small and (energy["large"] is None or not
                          energy["large"]["start"] <= today.isoformat() <= energy["large"]["end"]):
            rejections[code] = "no Large Commercial/Industrial default energy rate in effect today"
            continue
        detail = f"{effective[:4]} Utility Rates brochure, rate {code} ({block['heading']}), PDF page {block['page']}"
        components: list[RateComponent] = []
        for label in required:
            value, unit = prices[label]
            expected = {"Service Charge": "day", "Administration Charge": "day", "Facilities Usage": "kWh",
                        "Capacity Charge": "kWh", "Demand Charge": "kVA"}[label]
            if unit != expected:
                rejections[code] = f"{label} is per {unit}, not per {expected}"
                break
            components.append(RateComponent(
                component_type=COMPONENT_TYPES[label], component_name=label, charge_value=value,
                charge_unit={"day": "$/day", "kWh": "$/kWh", "kVA": "$/kVA/month"}[unit],
                demand_unit="kVA" if unit == "kVA" else None, effective_date=effective, source_url=source_url,
                source_detail=detail, notes=NOTES.get(label)))
        else:
            notes: list[str] = []
            joined = " ".join(block["lines"])
            conservation = re.search(r"Environmental Conservation Charge - additional charge for energy in "
                                     r"\$(\d+(?:\.\d+)?) per kWh excess of ([\d,]+) kWhs", joined)
            if code == "1.1":
                if not conservation:
                    rejections[code] = "Environmental Conservation Charge not found"
                    continue
                threshold = float(conservation.group(2).replace(",", ""))
                for tier, label, value in ((1, f"First {threshold:,.0f} kWh", 0.0),
                                           (2, f"Above {threshold:,.0f} kWh", float(conservation.group(1)))):
                    components.append(RateComponent(
                        component_type="rider", component_name=f"Environmental Conservation Charge — {label}",
                        charge_value=value, charge_unit="$/kWh", tier_number=tier, tier_threshold=threshold,
                        tier_unit="kWh/month", effective_date=effective, source_url=source_url,
                        source_detail=detail,
                        notes="Added for each kWh above the threshold per month; funds the City's HAT Smart "
                              "program (brochure)."))
            if small:
                components.append(RateComponent(
                    component_type="energy", component_name="Default Energy Charge", charge_value=energy["small_rate"],
                    charge_unit="$/kWh", effective_date=energy["start"], end_date=energy["end"],
                    source_url=energy_url,
                    source_detail=f"Energy Plans & Pricing page, default rates table, {energy['month']}",
                    notes=(f"{energy['month']} default electricity rate for residential, farm, small and medium "
                           "commercial customers (no contract required).")))
                if energy["going_green"] is None:
                    notes.append("Going Green surcharge not stored: the Energy Plans & Pricing page did not state "
                                 "it in the expected form.")
                else:
                    components.append(RateComponent(
                        component_type="rider", component_name="Going Green Surcharge",
                        charge_value=energy["going_green"], charge_unit="$/kWh", effective_date=energy["start"],
                        end_date=energy["end"], source_url=energy_url,
                        source_detail="Energy Plans & Pricing page, Going Green Charge",
                        notes=(f"Recovers the City's renewable energy purchases. The page gives no date ('calculated "
                               f"monthly'), so this is the value read for {energy['month']} (owner decision "
                               "2026-11-19).")))
            else:
                large = energy["large"]
                components.append(RateComponent(
                    component_type="energy", component_name="Default Energy Charge (Large Commercial and Industrial)",
                    charge_value=large["rate"], charge_unit="$/kWh", effective_date=large["start"],
                    end_date=large["end"], source_url=energy_url,
                    source_detail="Energy Plans & Pricing page, Large Commercial, Industrial and Street Lighting table",
                    notes=(f"Fixed default rate for {large['period']} The City bases it on the average of the "
                           "Alberta Rate of Last Resort prices.")))
                notes.append("Kept out of the representative models (owner decision 2026-11-19).")
            mcaf = {label: prices[label] for label in ("MCAF* fixed", "MCAF* variable") if label in prices}
            if mcaf:
                notes.append("Municipal Consent & Access Fee (customers within the City of Medicine Hat only, rate "
                             "code E; not included as a charge): "
                             + " and ".join(f"${value:g}/{unit}" for value, unit in mcaf.values()) + ".")
            notes.insert(0, f"City of Medicine Hat rate {code} ({block['heading'].title()}), brochure rates effective "
                            f"{effective}. The City generates, distributes and sells this electricity; the record "
                            "bundles its delivery charges and its default energy price.")
            if discovery_note:
                notes.append(discovery_note)
            # The record ends with its shortest-lived price (the month-dated default energy and Going Green surcharge,
            # or the large-customer fixed rate's term), so models and the coverage gate stop using it after that date
            # until a newer record is stored (owner decision 2026-11-19).
            ends = [c.end_date for c in components if c.end_date]
            records.append(TariffRecord(
                utility_name=UTILITY, province="AB", utility_type="electricity",
                tariff_name=f"{name} (Rate {code})", tariff_code=code, customer_class=customer_class,
                sub_class=block["heading"].lower(), rate_structure=structure, pricing_method="municipal",
                effective_date=max(c.effective_date for c in components), end_date=min(ends) if ends else None,
                source_url=source_url, source_page=detail, confidence="high", notes=" ".join(notes),
                components=components))
    return records, rejections


class MedicineHatScraper(BaseScraper):
    """Parse the City of Medicine Hat's bundled electricity rates."""

    def __init__(self) -> None:
        super().__init__(utility_name=UTILITY, province="AB")

    def scrape(self) -> list[TariffRecord]:
        # No seed fallback for batch 18 utilities (owner confirmed 2026-11-17).
        records = self._try_live_scrape()
        if not records:
            self.logger.warning("Medicine Hat: no live records (no seed fallback)")
        return records

    def _try_live_scrape(self) -> list[TariffRecord]:
        today = date.today()
        try:
            html = self.fetch_page(ENERGY_PAGE_URL)
            energy = parse_energy_page(html, today)
        except Exception as exc:
            self.logger.warning("Medicine Hat energy prices failed closed: %s", exc)
            return []
        url, note = find_brochure_url(html), ""
        if not url:
            url, note = LAST_KNOWN_BROCHURE_URL, ("The Energy Plans & Pricing page did not link the rates brochure, "
                                                  "so the last known brochure was read.")
        try:
            pages = extract_brochure_columns(self.fetch_bytes(url))
            records, rejections = parse_rates(pages, energy, url, today, discovery_note=note)
        except Exception as exc:
            self.logger.warning("Medicine Hat rates brochure failed closed: %s", exc)
            return []
        for code, reason in rejections.items():
            self.logger.warning("Medicine Hat rate %s rejected: %s", code, reason)
        return self.mark_live_parsed(records)
