"""
maritime_electric.py — Scraper for Maritime Electric electricity rates (Prince Edward Island).

Maritime Electric Company, Limited is the sole electricity provider in
Prince Edward Island. It is a subsidiary of Fortis Inc. PEI imports a
significant share of its electricity from New Brunswick.

Official source:
  https://www.maritimeelectric.com/my-account/understanding-my-bill/understanding-rates/

Regulated by: Island Regulatory and Appeals Commission (IRAC)
"""

from __future__ import annotations

import io
import logging
import re
from datetime import datetime
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import parse_html, find_pdf_links, DocumentPage

logger = logging.getLogger(__name__)

SOURCE_URL = "https://www.maritimeelectric.com/about-us/regulatory/rates-and-general-rules-and-regulations/"

# Known rate values — used as seed/fallback data.
# Rates are approximate; IRAC publishes exact approved schedules.
SEED_RESIDENTIAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.maritimeelectric.com/my-account/understanding-my-bill/understanding-rates/",
    "energy_rate": 0.1740,          # $/kWh
    "basic_charge_per_month": 19.28,  # $/month
}

SEED_GENERAL_SERVICE = {
    "effective_date": "2024-04-01",
    "source_url": "https://www.maritimeelectric.com/my-account/understanding-my-bill/understanding-rates/",
    "energy_rate": 0.1740,          # $/kWh
    "basic_charge_per_month": 30.00,  # $/month
}

# Non-lighting service classes published in the IRAC-approved Schedule of
# Adjusted Rates (Section N-28). (rate code, display name, customer_class,
# rate_structure). Street-lighting fixture rentals are intentionally excluded.
RATE_CLASSES: list[tuple[str, str, str, str]] = [
    ("110", "Residential Urban", "residential", "tiered"),
    ("130", "Residential Rural", "residential", "tiered"),
    ("131", "Residential Seasonal", "residential", "tiered"),
    ("133", "Residential Seasonal Option", "residential", "tiered"),
    ("232", "General Service", "commercial", "demand"),
    ("233", "General Service - Seasonal Operators Option", "commercial", "demand"),
    ("320", "Small Industrial", "industrial", "demand"),
    ("310", "Large Industrial", "industrial", "demand"),
    ("340", "Long Term Contract", "industrial", "demand"),
    ("330", "Short Term Contract", "industrial", "demand"),
]


def _tier_from_label(label: str, unit: str) -> tuple[Optional[int], Optional[float]]:
    """Infer (tier_number, tier_threshold) from a 'first N unit' / 'balance' label."""
    match = re.search(rf"first\s+([\d,]+)\s*{unit}", label)
    if match:
        return 1, float(match.group(1).replace(",", ""))
    if "balance" in label:
        return 2, None
    return None, None


def _parse_date(raw: str) -> Optional[str]:
    try:
        return datetime.strptime(re.sub(r"\s+", " ", raw).replace(",", ""), "%B %d %Y").date().isoformat()
    except ValueError:
        return None


def _schedule_date(text: str, link: str) -> Optional[str]:
    """Rate-column header date; must agree with the date in the document URL when present."""
    header = re.search(r"Rate\s+Code\s+([A-Z][a-z]+\s+\d{1,2},\s*\d{4})", text)
    effective = _parse_date(header.group(1)) if header else None
    if not effective:
        return None
    fname = re.search(r"effective-([a-z]+)-(\d{1,2})-(\d{4})", link, re.I)
    if fname and _parse_date(f"{fname.group(1).title()} {fname.group(2)} {fname.group(3)}") != effective:
        return None
    return effective


def _extract_pages(pdf_bytes: bytes) -> list[DocumentPage]:
    """Raw per-page text; the shared normalizer drops repeated rows, which this schedule relies on."""
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return [DocumentPage(n, p.extract_text() or "") for n, p in enumerate(pdf.pages, 1)]


# Expected (component_type, tier_number, tier_threshold) per rate code.
_RES = [("fixed", None, None), ("energy", 1, 2000.0), ("energy", 2, None)]
_GS = [("fixed", None, None), ("demand", 2, None),
       ("energy", 1, 5000.0), ("energy", 2, None)]
EXPECTED_SHAPES: dict[str, list[tuple]] = {
    "110": _RES, "130": _RES, "131": _RES, "133": _RES,
    "232": _GS, "233": _GS,
    "320": [("demand", None, None), ("energy", 1, 100.0), ("energy", 2, None)],
    "310": [("demand", None, None), ("energy", None, None)],
    "340": [("demand", None, None), ("energy", None, None)],
    "330": [("demand", None, None), ("energy", None, None), ("energy", 2, None)],
}
# General Service's first 20 kW of demand is published as "$ -" (no charge).
_ZERO_DEMAND_CODES = {"232", "233"}
_ZERO_DEMAND_LINE = re.compile(r"^demand charge.*first\s+20\s*kW\s*\$\s*-\s*$", re.I)

# Section N schedules on the rates page carry the eligibility, billing-demand and
# conditional terms that the N-28 price summary omits.
_RATES_PAGE_DATE = re.compile(
    r"Unless otherwise indicated, this Rate Schedule and the General Rules and "
    r"Regulations are effective ([A-Z][a-z]+ \d{1,2}, \d{4})"
)
_ECAM_INCLUSIVE = (
    "This rate is inclusive of the Energy Cost Adjustment Mechanism and other rates "
    "and tolls approved by the Commission"
)
_SI_BILLING_DEMAND = (
    "The greatest of: The monthly maximum kW demand; 90% of the monthly maximum kVA "
    "demand; or 5 kW."
)
_LI_BILLING_DEMAND = (
    "The greatest of: The monthly maximum kW demand; 90% of the maximum kVA demand; "
    "90% of the firm amount reserved in the contract for non-curtailable customers or "
    "100% of the total contracted amount for curtailable customers; 90% of the maximum "
    "demand recorded during the current calendar year excluding April through November; "
    "or 90% of the lesser of the average demand recorded during the previous calendar "
    "year, or the previous calendar year excluding April through November."
)
_OPT_DOWN = (
    "Customers whose demand is above 750 kW and less than 3000 kW may choose to be "
    "billed at the Small Industrial Rate but must meet certain conditions of the Large "
    "Industrial Rate; specifically, they must be metered at a primary voltage of 69 kV "
    "and own the step-down transformation from the primary service voltage or pay an "
    "equivalent rental charge."
)
_SIC_GROUPS = (
    "Industrial Rates apply to the following S.I.C. groups: Division C Major group: "
    "04 Logging Industry Division D Major groups: 06 Mining Industries"
)
_LOSSES_PRIMARY = (
    "Losses Charge - 69 kV to primary distribution voltage At the discretion of Maritime "
    "Electric, electricity may be supplied at a primary distribution voltage between 4 kV "
    "and 25 kV. In such cases, the monthly demand and energy consumption will be "
    "increased by 1 1/2% to compensate for transformation losses."
)
_LOSSES_UTILIZATION = (
    "- Primary distribution voltage to Customer's utilization voltage At the discretion "
    "of Maritime Electric, electricity may be supplied at the Customer's utilization "
    "voltage. In such cases, the monthly demand and energy consumption will be increased "
    "by 1 1/2% to compensate for transformation losses. This charge will be in addition "
    "to the losses charge for transformation from 69 kV to the primary distribution voltage."
)
_TRANSFORMATION = (
    "Transformation Charge - 69 kV to primary distribution voltage When a Customer is "
    "provided service at a primary distribution voltage between 4 kV and 25 kV, the "
    "customer will also be charged an \"equivalent kVA rental\" charge equal to 1 5/6% "
    "per month of the costs of the equivalent substation kVA utilized by the Customer's "
    "electrical load. The equivalent kVA charge is the Customer's kVA demand multiplied "
    "by $1.25 per kVA per month."
)
_RENTAL = "The charge for such rental equipment is 1 5/6% per month of the installed costs."
_LI_CONTRACT = (
    "for an initial term of five (5) years, in the case of a Customer considered by "
    "Maritime Electric to be a new Customer, and for an initial term of one year"
)
_LI_METERING = "The metering point shall be at or near the transmission line terminals (69 kV)."


def _schedule_sections(html: str) -> tuple[Optional[str], dict[str, Optional[str]]]:
    """Rates-page effective date and whitespace-normalized <details> sections by title."""
    soup = parse_html(html)
    match = _RATES_PAGE_DATE.search(" ".join(soup.get_text(" ").split()))
    effective = _parse_date(match.group(1)) if match else None
    sections: dict[str, Optional[str]] = {}
    for details in soup.find_all("details"):
        summary = details.find("summary")
        if summary is None:
            continue
        title = " ".join(summary.get_text(" ").split())
        # A repeated title is ambiguous, so it is treated as missing.
        sections[title] = None if title in sections else " ".join(details.get_text(" ").split())
    return effective, sections


def _section(sections: dict[str, Optional[str]], title: str) -> str:
    body = sections.get(title)
    if not body:
        raise ValueError(f"missing or duplicated section {title!r}")
    return body


def _require(text: str, *phrases: str) -> None:
    for phrase in phrases:
        if phrase not in text:
            raise ValueError(f"missing published term {phrase[:60]!r}")


def _amounts(text: str) -> list[tuple[str, float]]:
    """Every dollar and cent amount in published order."""
    return [
        ("$", float(d.replace(",", ""))) if d else ("¢", float(c))
        for d, c in re.findall(r"\$\s?([\d,]+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s?¢", text)
    ]


def _expect_amounts(text: str, expected: list[tuple[str, float]]) -> None:
    found = [(kind, round(value, 4)) for kind, value in _amounts(text)]
    if found != [(kind, round(value, 4)) for kind, value in expected]:
        raise ValueError(f"published amounts {found} do not match the N-28 schedule {expected}")


class MaritimeElectricScraper(BaseScraper):
    """Scrape Maritime Electric electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Maritime Electric", province="PE")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Maritime Electric rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Maritime Electric tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for Maritime Electric")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Parse every non-lighting service class from the official Schedule of Adjusted Rates PDF."""
        try:
            html = self.fetch_page(SOURCE_URL)
            if not html:
                return None
            pdf_links = find_pdf_links(
                parse_html(html), keywords=["adjusted", "rate", "schedule", "section"],
                base_url=SOURCE_URL,
            )
            for link in pdf_links[:6]:
                try:
                    pages = _extract_pages(self.fetch_bytes(link))
                except Exception:
                    continue
                records = self._apply_schedules(self._parse_pages(pages, link), html)
                if records:
                    return self.mark_live_parsed(records)
            return None
        except Exception:
            self.logger.exception("Error during Maritime Electric live scrape")
            return None

    def _parse_pages(self, pages: list[DocumentPage], link: str) -> list[TariffRecord]:
        """Parse non-lighting service classes from the rate page; each class fails alone."""
        page = next(
            (p for p in pages
             if "Schedule of Rates" in p.text and "110 Residential Urban" in p.text),
            None,
        )
        if page is None:
            return []
        effective = _schedule_date(page.text, link)
        if not effective:
            return []
        start = page.text.find("110 Residential Urban")
        end = page.text.find("Page 1 of")
        body = page.text[start:end] if end > start else page.text[start:]

        codes = {code for code, _, _, _ in RATE_CLASSES}
        headers = [
            (m.group(1), m.start())
            for m in re.finditer(r"(?m)^\s*(\d{3})\s+\D.*$", body)
            if m.group(1) in codes
        ]
        seen = [code for code, _ in headers]
        records: list[TariffRecord] = []
        for i, (code, pos) in enumerate(headers):
            if seen.count(code) > 1:
                continue
            seg_end = headers[i + 1][1] if i + 1 < len(headers) else len(body)
            record = self._build_record(
                code, body[pos:seg_end], effective, link, page.source_detail
            )
            if record:
                records.append(record)
        return records

    def _build_record(
        self, code: str, block: str, effective: str, link: str, page_detail: str
    ) -> Optional[TariffRecord]:
        """Build one record; None unless the class has exactly its expected components."""
        meta = next((m for m in RATE_CLASSES if m[0] == code), None)
        if not meta:
            return None
        _, name, customer_class, structure = meta
        components: list[RateComponent] = []
        zero_demand_seen = False
        for raw in block.splitlines()[1:]:
            line = raw.strip()
            if _ZERO_DEMAND_LINE.search(line):
                zero_demand_seen = True
                continue
            component = self._parse_component_line(line)
            if component:
                components.append(component)
            elif re.search(r"charge.*\$", line, re.I):
                return None
        if (code in _ZERO_DEMAND_CODES) != zero_demand_seen:
            return None
        no_customers = "(Currently no customers in this rate category)" in block.splitlines()[0]
        shape = sorted(
            ((c.component_type, c.tier_number, c.tier_threshold) for c in components), key=repr
        )
        if shape != sorted(EXPECTED_SHAPES[code], key=repr):
            return None
        for c in components:
            c.effective_date = effective
            c.source_url = link
            c.source_detail = f"{page_detail}, Rate {code} {name}"
            if code == "320" and c.tier_unit:
                c.tier_unit = "kWh per kW billing demand"
        return TariffRecord(
            utility_name="Maritime Electric", province="PE", utility_type="electricity",
            tariff_name=f"{name} (Rate {code})", tariff_code=code,
            customer_class=customer_class, rate_structure=structure,
            effective_date=effective, source_url=link, source_page=page_detail,
            confidence="high",
            notes=(
                "Parsed from the IRAC-approved Maritime Electric Schedule of "
                "Adjusted Rates (Section N-28)."
                + (" N-28 states: currently no customers in this rate category." if no_customers else "")
            ),
            components=components,
        )

    def _apply_schedules(self, records: list[TariffRecord], html: str) -> list[TariffRecord]:
        """Cross-check industrial/wholesale classes against their Section N schedules; each fails alone."""
        appliers = {
            "320": self._apply_small_industrial, "310": self._apply_large_industrial,
            "340": self._apply_wholesale, "330": self._apply_wholesale,
        }
        if not any(r.tariff_code in appliers for r in records):
            return records
        effective, sections = _schedule_sections(html or "")
        kept: list[TariffRecord] = []
        for record in records:
            apply = appliers.get(record.tariff_code)
            if apply is None:
                kept.append(record)
                continue
            try:
                if effective != record.effective_date:
                    raise ValueError(f"rates page date {effective} differs from N-28 {record.effective_date}")
                apply(record, sections)
                kept.append(record)
            except ValueError as exc:
                self.logger.warning("Maritime Electric Rate %s rejected: %s", record.tariff_code, exc)
        return kept

    @staticmethod
    def _pdf_parts(record: TariffRecord) -> tuple[RateComponent, list[RateComponent]]:
        demand = [c for c in record.components if c.component_type == "demand"]
        energy = sorted(
            (c for c in record.components if c.component_type == "energy"),
            key=lambda c: c.tier_number or 0,
        )
        if len(demand) != 1 or not energy:
            raise ValueError("unexpected N-28 component shape")
        return demand[0], energy

    @staticmethod
    def _cross_checked(record: TariffRecord, section_title: str) -> None:
        for c in record.components:
            c.source_detail += f"; terms cross-checked against Section N {section_title} ({SOURCE_URL})"

    @staticmethod
    def _page_component(
        record: TariffRecord, section_title: str, part: str, **fields
    ) -> RateComponent:
        return RateComponent(
            effective_date=record.effective_date, source_url=SOURCE_URL,
            source_detail=f"Rates and General Rules and Regulations, Section N {section_title}, {part}",
            sub_component="conditional", **fields,
        )

    def _apply_small_industrial(self, record: TariffRecord, sections: dict) -> None:
        title = "Small Industrial Rate Schedule"
        body = _section(sections, title)
        guide = _section(sections, "Small Industrial Rate Application Guidelines")
        _require(
            body, "Rate (Code 320):", "minimum contracted demand of five (5) kilowatts",
            _SI_BILLING_DEMAND, "per kW of billing demand per month",
            "per kWh for first 100 kWh per kW of billing demand per month",
            "per kWh for balance of kWh per month",
            "customers must sign the Contract for Electrical Service", _ECAM_INCLUSIVE,
        )
        _require(guide, _SIC_GROUPS, "Division E Manufacturing Industries.", _OPT_DOWN)
        demand, energy = self._pdf_parts(record)
        if [e.tier_number for e in energy] != [1, 2]:
            raise ValueError("unexpected N-28 energy blocks")
        _expect_amounts(body, [("$", demand.charge_value)] + [("¢", e.charge_value * 100) for e in energy])
        self._cross_checked(record, title)
        record.sub_class = "small industrial"
        record.demand_min_kw = 5.0
        record.eligibility = (
            "Customers using electricity chiefly for manufacturing or processing of goods or for "
            "the extraction of raw materials (S.I.C. Division C 04, Division D 06-09 and Division E; "
            "fish hatcheries and qualifying mixed operations) with a minimum contracted demand of "
            "5 kW and a signed Contract for Electrical Service. " + _OPT_DOWN
        )
        demand.notes = (
            "Per kW of billing demand per month. Billing demand is the greatest of the monthly "
            "maximum kW demand, 90% of the monthly maximum kVA demand, or 5 kW; installed metering "
            "may make the kW/kVA tests inapplicable. The kVA test sets billing demand only; it is "
            "not a separate charge."
        )
        energy[0].notes = "First 100 kWh per kW of billing demand per month."
        energy[1].notes = "Balance of kWh per month."
        record.notes += " Section N Small Industrial schedule: rate is inclusive of the ECAM; no service charge is published."

    def _apply_large_industrial(self, record: TariffRecord, sections: dict) -> None:
        title = "Large Industrial Rate Schedule"
        body = _section(sections, title)
        guide = _section(sections, "Large Industrial Rate Application Guidelines")
        _require(
            body, "Rates (Code 310):", "minimum contracted demand of 750 kW", _LI_BILLING_DEMAND,
            "per kW of the billing demand per month", "per kWh for all kWh per month",
            _RENTAL, _LOSSES_PRIMARY, _LOSSES_UTILIZATION, _TRANSFORMATION, _LI_CONTRACT,
            "giving at least twelve month's notice in writing", _LI_METERING, _ECAM_INCLUSIVE,
        )
        _require(guide, _SIC_GROUPS, "Division E Manufacturing Industries.", _OPT_DOWN)
        demand, energy = self._pdf_parts(record)
        if len(energy) != 1:
            raise ValueError("unexpected N-28 energy blocks")
        _expect_amounts(body, [("$", demand.charge_value), ("¢", energy[0].charge_value * 100), ("$", 1.25)])
        self._cross_checked(record, title)
        record.sub_class = "large industrial"
        record.demand_min_kw = 750.0
        record.eligibility = (
            "Customers using electricity chiefly for manufacturing or processing of goods or for "
            "the extraction of raw materials (S.I.C. Division C 04, Division D 06-09 and Division E; "
            "qualifying mixed operations) with a minimum contracted demand of 750 kW. Firm contract: "
            "initial term 5 years (new customer) or 1 year (existing), then 12 months' written notice. "
            "Metering point at or near the 69 kV transmission line terminals. " + _OPT_DOWN
        )
        demand.notes = (
            "Per kW of billing demand per month. Billing demand is the greatest of: monthly maximum "
            "kW demand; 90% of maximum kVA demand; 90% of the contract firm amount (non-curtailable) "
            "or 100% of the total contracted amount (curtailable); 90% of the current calendar "
            "year's maximum demand excluding April-November; or 90% of the lesser of the previous "
            "calendar year's average demand or that average excluding April-November. These are "
            "ratchet conditions, not separate charges; no curtailable credit is published."
        )
        energy[0].notes = "All kWh per month."
        record.components.extend([
            self._page_component(
                record, title, "Losses Charge (69 kV to primary distribution voltage)",
                component_type="adjustment",
                component_name="Conditional Losses Adjustment - 69 kV to Primary Distribution Voltage",
                charge_value=1.5, charge_unit="% added to monthly demand and energy",
                notes=("Conditional: only when Maritime Electric, at its discretion, supplies at a primary "
                       "distribution voltage between 4 kV and 25 kV. Increases billed demand and energy "
                       "by 1 1/2%; not a separate price."),
            ),
            self._page_component(
                record, title, "Losses Charge (primary distribution to utilization voltage)",
                component_type="adjustment",
                component_name="Conditional Losses Adjustment - Primary to Utilization Voltage",
                charge_value=1.5, charge_unit="% added to monthly demand and energy",
                notes=("Conditional: only when Maritime Electric, at its discretion, supplies at the "
                       "customer's utilization voltage. Applies in addition to the 69 kV-to-primary "
                       "losses adjustment."),
            ),
            self._page_component(
                record, title, "Transformation Charge (69 kV to primary distribution voltage)",
                component_type="demand",
                component_name="Conditional Transformation Charge (equivalent kVA rental)",
                charge_value=1.25, charge_unit="$/kVA", demand_unit="kVA",
                notes=("Conditional: only when served at a primary distribution voltage between 4 kV and "
                       "25 kV. Per kVA of the customer's kVA demand per month (published as an equivalent "
                       "kVA rental of 1 5/6% per month of equivalent substation cost)."),
            ),
        ])
        record.notes += (
            " Section N Large Industrial schedule: rate is inclusive of the ECAM. Optional substation "
            "equipment rental at the customer's request is 1 5/6% per month of installed cost; no "
            "dollar price is published, so it is not a component."
        )

    def _apply_wholesale(self, record: TariffRecord, sections: dict) -> None:
        title = "Wholesale Rate Schedule"
        body = _section(sections, title)
        _require(body, "Application The City of Summerside Electric Department.", _ECAM_INCLUSIVE)
        long_start, short_start = body.find("Long Term Contract:"), body.find("Short Term Contract:")
        block_end = body.find("First Energy Block Determination")
        if not 0 <= long_start < short_start < block_end:
            raise ValueError("wholesale contract blocks missing or out of order")
        demand, energy = self._pdf_parts(record)
        if record.tariff_code == "340":
            part = body[long_start:short_start]
            _require(part, "Rate (Code 340):", "for a period not less than 10 years",
                     "per kW per month", "per kWh for all kWh per month")
            term = "not less than 10 years"
        else:
            part = body[short_start:]
            _require(part, "Rate (Code 330):", "for a period not less than 1 year",
                     "per kW per month", "per kWh for all kWh in the first block per month",
                     "per kWh for balance of kWh in the month",
                     "Set each year on 1 April based on the minimum monthly energy purchases")
            term = "not less than 1 year"
            if [e.tier_number for e in energy] != [None, 2]:
                raise ValueError("unexpected N-28 energy blocks")
            energy[0].tier_number = 1
            energy[0].notes = ("First energy block, set each 1 April from the minimum monthly energy "
                               "purchases for the previous 1 April-31 March with normalized customer "
                               "generation; no fixed kWh size is published.")
        _expect_amounts(part, [("$", demand.charge_value)] + [("¢", e.charge_value * 100) for e in energy])
        self._cross_checked(record, title)
        record.customer_class = "other"
        record.sub_class = "wholesale (reference only)"
        record.eligibility = f"The City of Summerside Electric Department only; contract {term}."
        record.notes += (
            " Section N Wholesale Rate Schedule for a reselling utility: excluded from building scope "
            "and retained as reference only."
        )

    @staticmethod
    def _parse_component_line(line: str) -> Optional[RateComponent]:
        """Turn one '... Charge ... $ value' schedule line into a RateComponent."""
        match = re.match(r"^(.*?charge.*?)\s*\$\s*(-|[\d,]+\.?\d*)\s*$", line, re.I)
        if not match:
            return None
        label = re.sub(r"\s+", " ", match.group(1)).strip()
        raw = match.group(2)
        if raw == "-":
            return None
        value = float(raw.replace(",", ""))
        low = label.lower()
        if low.startswith("service charge"):
            return RateComponent(
                component_type="fixed", component_name="Service Charge",
                charge_value=value, charge_unit="$/month",
            )
        if low.startswith("demand charge"):
            tier_number, threshold = _tier_from_label(low, "kw")
            return RateComponent(
                component_type="demand", component_name=label,
                charge_value=value, charge_unit="$/kW", demand_unit="kW",
                tier_number=tier_number, tier_threshold=threshold,
                tier_unit="kW" if threshold else None,
            )
        if low.startswith("energy charge"):
            tier_number, threshold = _tier_from_label(low, "kwh")
            return RateComponent(
                component_type="energy", component_name=label,
                charge_value=value, charge_unit="$/kWh",
                tier_number=tier_number, tier_threshold=threshold,
                tier_unit="kWh" if threshold else None,
            )
        return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Maritime Electric",
            province="PE",
            utility_type="electricity",
            tariff_name="Residential Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "Maritime Electric (Fortis-owned) residential rate. "
                "Rates are approximate; check IRAC-approved rate schedule for exact values."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Monthly basic charge regardless of consumption",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        # ── General Service ──────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Maritime Electric",
            province="PE",
            utility_type="electricity",
            tariff_name="General Service",
            customer_class="commercial",
            sub_class="general service",
            rate_structure="flat",
            effective_date=SEED_GENERAL_SERVICE["effective_date"],
            source_url=SEED_GENERAL_SERVICE["source_url"],
            confidence="medium",
            eligibility="Small commercial customers",
            notes=(
                "Maritime Electric (Fortis-owned) general service rate. "
                "Rates are approximate; check IRAC-approved rate schedule for exact values."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_GENERAL_SERVICE["basic_charge_per_month"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_GENERAL_SERVICE["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        return records
