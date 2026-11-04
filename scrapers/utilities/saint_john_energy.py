"""
saint_john_energy.py — Scraper for Saint John Energy electricity rates (New Brunswick).

Official source: the Customer Policy and Rates Manual (Section 9, Rate Schedules), linked from
https://sjenergy.ca/about/our-rates and published on the utility's S3 document store.

Each in-scope schedule prints a CLASS / RATE CODE heading, its own EFFECTIVE DATE, a
service charge, an optional demand charge and an ENERGY RATE table of Base Rate + Rate Rider =
Total Charge. The rider (the pass-through of NB Power's rate rider, manual definition "Rate
Rider") is kept as its own component; the printed total must equal base + rider or the class
fails closed. Demand schedules price the first block as "First 100 kWh/kW of billed demand".

sjenergy.ca serves an incomplete certificate chain (leaf only, checked 2026-11-04), so Python
cannot verify it. The manual link is discovered with a plain request first, then headless
Chromium (which completes the chain itself); if both fail the last known manual is read and
the records say so. TLS verification is never disabled (batch 18 provisional decision,
2026-11-04).

Scope (building service): Residential 001 and 006, General Service 002, 202 (closed) and 004,
Industrial 008, 009 (closed) and 010. Excluded: water-heater and heat-pump rentals, lighting,
pole attachments, EV charging, miscellaneous fees and the City of Saint John "Municipal
Related" rates (101/102/104/106/112/M, restricted to municipal operations; batch 18
provisional decision, 2026-11-04). Rates exclude HST.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages

UTILITY = "Saint John Energy"
RATES_PAGE_URL = "https://sjenergy.ca/about/our-rates"
LAST_KNOWN_MANUAL_URL = (
    "https://sje-cms.s3.ca-central-1.amazonaws.com/"
    "Customer_Policy_and_Rates_Manual_as_of_September_1_2026_ddbf7bea17.pdf"
)
_MANUAL_LINK = re.compile(r"https://sje-cms\.s3\.[a-z0-9-]+\.amazonaws\.com/Customer_Policy_and_Rates_Manual[^\"'\s<>]*\.pdf")


@dataclass(frozen=True)
class _Class:
    code: str
    name: str
    customer_class: str
    sub_class: str
    demand: bool


CLASSES = {
    "001": _Class("001", "Residential Service", "residential", "residential", False),
    "006": _Class("006", "Residential Service – Central Electric Heating", "residential",
                  "central electric heating (apartment buildings and condominiums)", False),
    "002": _Class("002", "General Service", "commercial", "general service", True),
    "202": _Class("202", "General Service – Customer-Owned Transformation (Closed)", "commercial",
                  "general service, customer-owned transformer, primary metered", True),
    "004": _Class("004", "General Service: Non-Demand Metered", "commercial",
                  "general service, non-demand metered (up to 5,000 kWh/month)", False),
    "008": _Class("008", "Industrial Service", "industrial", "industrial (manufacturing, 5 kW minimum)", True),
    "009": _Class("009", "Industrial Service (Closed)", "industrial",
                  "industrial (manufacturing, 750 kW minimum, closed)", True),
    "010": _Class("010", "Industrial Service (Non-Interruptible)", "industrial",
                  "industrial and data centres (750 kW minimum)", True),
}

_DATE = r"([A-Z][a-z]+\s+\d{1,2},\s*\d{4})"
_NUM = r"(\d+(?:\.\d+)?)"


def _iso(text: str) -> str:
    return datetime.strptime(re.sub(r"\s+", " ", text.replace(",", ", ")).replace(" ,", ",").strip(),
                             "%B %d, %Y").date().isoformat()


def _cents(text: str) -> float:
    return round(float(text) / 100, 6)


def find_manual_url(html: str) -> Optional[str]:
    """The rates page's current manual link (the first S3 manual PDF it names)."""
    match = _MANUAL_LINK.search(html or "")
    return match.group(0) if match else None


def manual_revision(pages: list[DocumentPage]) -> str:
    """ISO date of the manual's 'Document revised as of <date>' cover line."""
    for page in pages[:3]:
        match = re.search(r"Document revised as of\s+" + _DATE, page.text)
        if match:
            return _iso(match.group(1))
    raise ValueError("manual revision date not found")


def _class_blocks(pages: list[DocumentPage]) -> dict[str, tuple[str, list[int]]]:
    """Text of each in-scope schedule (its first page plus a '... continued' page), by rate code."""
    blocks: dict[str, tuple[str, list[int]]] = {}
    for index, page in enumerate(pages):
        for match in re.finditer(r"CLASS:\s*(.*?)\s*RATE CODE:\s*(\S+)", page.text):
            code = match.group(2)
            if code not in CLASSES:
                continue
            if code in blocks:
                raise ValueError(f"rate code {code} printed twice")
            text, numbers = page.text[match.start():], [page.page_number]
            if index + 1 < len(pages) and re.search(rf"Code {int(code)}\b.*?continued", pages[index + 1].text,
                                                    re.I | re.S):
                text += "\n" + pages[index + 1].text
                numbers.append(pages[index + 1].page_number)
            blocks[code] = (text, numbers)
    return blocks


def _energy_rows(text: str) -> list[tuple[float, float, float]]:
    """(base, rider, total) in $/kWh for each printed energy block, in order."""
    section = re.search(r"ENERGY (?:RATE|CHARGE):(.*?)(?:SERVICE CHARGE|Service charge)", text, re.S)
    if not section:
        raise ValueError("energy rate table missing")
    body = section.group(1)
    bases = re.findall(r"Base Rate\s+" + _NUM, body)
    riders = re.findall(r"Rate Rider\s+" + _NUM, body)
    totals = re.findall(r"Total Charge\s+" + _NUM, body)
    if not bases or not (len(bases) == len(riders) == len(totals)):
        raise ValueError("energy rate table rows incomplete")
    rows = []
    for base, rider, total in zip(bases, riders, totals):
        if abs(float(base) + float(rider) - float(total)) > 0.0051:
            raise ValueError(f"base {base} + rider {rider} does not equal total {total}")
        rows.append((_cents(base), _cents(rider), _cents(total)))
    if len(rows) == 2 and not re.search(r"First 100\s+.*?kWh/kW of.*?billed.*?demand.*?Balance of", body, re.S):
        raise ValueError("two energy blocks without the 'First 100 kWh/kW of billed demand' wording")
    if len(rows) not in (1, 2):
        raise ValueError(f"unexpected {len(rows)} energy blocks")
    return rows


def parse_manual(pages: list[DocumentPage], source_url: str, today: Optional[date] = None,
                 discovery_note: str = "") -> list[TariffRecord]:
    """Build every in-scope schedule from the manual's Section 9 pages; raise ValueError when any is
    missing, duplicated, undated, not yet in effect or internally inconsistent (fail closed)."""
    today = today or date.today()
    revision = manual_revision(pages)
    blocks = _class_blocks(pages)
    missing = sorted(set(CLASSES) - set(blocks))
    if missing:
        raise ValueError(f"rate codes missing from the manual: {', '.join(missing)}")
    records = []
    for code, spec in CLASSES.items():
        text, page_numbers = blocks[code]
        dated = re.search(r"EFFECTIVE DATE:\s*" + _DATE, text)
        if not dated:
            raise ValueError(f"rate code {code} has no effective date")
        effective = _iso(dated.group(1))
        if date.fromisoformat(effective) > today:
            raise ValueError(f"rate code {code} takes effect {effective}, after {today.isoformat()}")
        detail = (f"Customer Policy and Rates Manual (revised as of {revision}), Section 9, "
                  f"Rate Code {code}, PDF page{'s' if len(page_numbers) > 1 else ''} "
                  f"{', '.join(map(str, page_numbers))}")
        rows = _energy_rows(text)
        riders = {rider for _, rider, _ in rows}
        if len(riders) != 1:
            raise ValueError(f"rate code {code} prints different riders per block")
        components: list[RateComponent] = []

        def add(**fields) -> None:
            components.append(RateComponent(effective_date=effective, source_url=source_url,
                                            source_detail=detail, confidence="high", **fields))

        service = re.search(r"\$" + _NUM + r"\s+service charge per month", text) or \
            re.search(r"Service charge\s+\$" + _NUM + r"\s+per month", text)
        if service:
            add(component_type="fixed", component_name="Service Charge", charge_value=float(service.group(1)),
                charge_unit="$/month")
        elif not re.search(r"Service charge is not applicable", text):
            raise ValueError(f"rate code {code} service charge missing")
        demand = re.search(r"MONTHLY DEMAND CHARGE:\s*\$" + _NUM + r"\s+per kW of monthly maximum billing demand",
                           text)
        if spec.demand != bool(demand):
            raise ValueError(f"rate code {code} demand charge {'missing' if spec.demand else 'unexpected'}")
        if demand:
            minimum = re.search(r"MINIMUM BILLING DEMAND:\s*(.*?)\n", text)
            billing = re.search(r"BILLING DEMAND:\s*(.*?)(?:MINIMUM BILLING DEMAND|MONTHLY DEMAND)", text, re.S)
            add(component_type="demand", component_name="Demand Charge", charge_value=float(demand.group(1)),
                charge_unit="$/kW/month", demand_unit="kW",
                notes=("Per kW of monthly maximum billing demand. Billing demand: "
                       + re.sub(r"\s+", " ", billing.group(1)).strip() if billing else "Per kW of billing demand.")
                + (" Minimum billing demand: " + minimum.group(1).strip() if minimum else ""))
        if len(rows) == 1:
            add(component_type="energy", component_name="Energy Charge (Base Rate)", charge_value=rows[0][0],
                charge_unit="$/kWh", notes="All kWh.")
        else:
            add(component_type="energy", component_name="Energy Charge (Base Rate) — First 100 kWh/kW",
                charge_value=rows[0][0], charge_unit="$/kWh", tier_number=1, tier_threshold=100.0,
                tier_unit="kWh/kW of billing demand/month",
                notes="First 100 kWh per kW of billed demand per month.")
            add(component_type="energy", component_name="Energy Charge (Base Rate) — Balance",
                charge_value=rows[1][0], charge_unit="$/kWh", tier_number=2, tier_threshold=100.0,
                tier_unit="kWh/kW of billing demand/month", notes="Balance of kWh per month.")
        add(component_type="rider", component_name="Rate Rider", charge_value=riders.pop(), charge_unit="$/kWh",
            notes="All kWh. Pass-through of NB Power's rate rider (manual definition 'Rate Rider'); the printed "
                  "Total Charge equals Base Rate + Rate Rider.")
        notes = (f"Saint John Energy Rate Code {code}. Rates exclude HST. Late payment, connection, change of "
                 "occupancy and after-hours fees are one-time or conditional charges, not shown as components.")
        if code in ("202", "009"):
            notes += " Closed: no longer available for new customers."
        if discovery_note:
            notes += " " + discovery_note
        records.append(TariffRecord(
            utility_name=UTILITY, province="NB", utility_type="electricity", tariff_name=spec.name,
            tariff_code=code, customer_class=spec.customer_class, sub_class=spec.sub_class,
            eligibility=_applicability(text), rate_structure=("demand" if spec.demand else "flat"),
            demand_min_kw=_minimum_kw(code), usage_max=(5000.0 if code == "004" else None),
            usage_unit=("kWh/month" if code == "004" else None), pricing_method="regulated",
            effective_date=effective, source_url=source_url, source_page=detail, confidence="high",
            notes=notes, components=components,
        ))
    return records


def _applicability(text: str) -> Optional[str]:
    match = re.search(r"APPLICABILITY:\s*(.*?)(?:BILLING DEMAND|ENERGY RATE|ENERGY CHARGE)", text, re.S)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else None


def _minimum_kw(code: str) -> Optional[float]:
    return {"008": 5.0, "009": 750.0, "010": 750.0}.get(code)


class SaintJohnEnergyScraper(BaseScraper):
    """Parse Saint John Energy's building-service rate schedules from its rates manual."""

    def __init__(self) -> None:
        super().__init__(utility_name=UTILITY, province="NB")

    def scrape(self) -> list[TariffRecord]:
        # No seed fallback for utilities added in batch 18 (provisional decision 2026-11-04):
        # a source failure returns no records and shows up as a failed utility.
        records = self._try_live_scrape()
        if not records:
            self.logger.warning("Saint John Energy: no live records (no seed fallback)")
        return records

    def _discover_manual(self) -> tuple[str, str]:
        for label, fetch in (("page", self.fetch_page), ("rendered page", self.fetch_rendered_page)):
            try:
                url = find_manual_url(fetch(RATES_PAGE_URL) or "")
            except Exception as exc:
                self.logger.warning("Saint John Energy rates %s unavailable: %s", label, exc)
                continue
            if url:
                return url, ""
        return LAST_KNOWN_MANUAL_URL, ("The rates page could not be read, so the last known manual was read "
                                       "(it may not be the current edition).")

    def _try_live_scrape(self) -> list[TariffRecord]:
        url, note = self._discover_manual()
        try:
            pages = extract_pdf_pages(self.fetch_bytes(url), drop_repeated_lines=False)
            records = parse_manual(pages, url, discovery_note=note)
        except Exception as exc:
            self.logger.warning("Saint John Energy manual failed closed: %s", exc)
            return []
        return self.mark_live_parsed(records)
