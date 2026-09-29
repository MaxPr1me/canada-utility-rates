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

import logging
import re
from datetime import datetime
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html, find_pdf_links, extract_pdf_text, extract_effective_date,
)

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


def _resolve_effective_date(text: str, link: str) -> str:
    """Resolve the schedule effective date from the text, then the URL, then seed."""
    iso = extract_effective_date(text)
    if iso:
        return iso
    bare = re.search(r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})", text)
    if bare:
        try:
            return datetime.strptime(
                f"{bare.group(1)} {bare.group(2)} {bare.group(3)}", "%B %d %Y"
            ).date().isoformat()
        except ValueError:
            pass
    fname = re.search(r"effective-([a-z]+)-(\d{1,2})-(\d{4})", link, re.I)
    if fname:
        try:
            return datetime.strptime(
                f"{fname.group(1)} {fname.group(2)} {fname.group(3)}", "%B %d %Y"
            ).date().isoformat()
        except ValueError:
            pass
    return SEED_RESIDENTIAL["effective_date"]


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
                    text = extract_pdf_text(self.fetch_bytes(link))
                except Exception:
                    continue
                if "Residential Urban" not in text:
                    continue
                records = self._parse_all_classes(text, link)
                if records:
                    return self.mark_live_parsed(records)
            return None
        except Exception:
            self.logger.exception("Error during Maritime Electric live scrape")
            return None

    def _parse_all_classes(self, text: str, link: str) -> list[TariffRecord]:
        """Parse all non-lighting service classes from the Schedule of Adjusted Rates."""
        start = text.find("110 Residential")
        if start == -1:
            return []
        end = text.find("Page 1 of 3")
        body = text[start:end] if end != -1 else text[start:]
        effective = _resolve_effective_date(text, link)

        codes = {code for code, _, _, _ in RATE_CLASSES}
        headers = [
            (m.group(1), m.start())
            for m in re.finditer(r"(?m)^\s*(\d{3})\s+\D.*$", body)
            if m.group(1) in codes
        ]
        records: list[TariffRecord] = []
        for i, (code, pos) in enumerate(headers):
            seg_end = headers[i + 1][1] if i + 1 < len(headers) else len(body)
            record = self._build_record(code, body[pos:seg_end], effective, link)
            if record:
                records.append(record)
        return records

    def _build_record(
        self, code: str, block: str, effective: str, link: str
    ) -> Optional[TariffRecord]:
        """Build one TariffRecord from a single rate-code block of the schedule."""
        meta = next((m for m in RATE_CLASSES if m[0] == code), None)
        if not meta:
            return None
        _, name, customer_class, structure = meta
        components: list[RateComponent] = []
        for line in block.splitlines()[1:]:
            component = self._parse_component_line(line.strip())
            if component:
                components.append(component)
        if not components:
            return None
        return TariffRecord(
            utility_name="Maritime Electric", province="PE", utility_type="electricity",
            tariff_name=f"{name} (Rate {code})", tariff_code=code,
            customer_class=customer_class, rate_structure=structure,
            effective_date=effective, source_url=link, confidence="high",
            notes=(
                "Parsed from the IRAC-approved Maritime Electric Schedule of "
                "Adjusted Rates (Section N-28)."
            ),
            components=components,
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
