"""
newfoundland_power.py — Scraper for Newfoundland Power electricity rates (Newfoundland and Labrador).

Newfoundland Power Inc. is the primary electricity distributor on the
island of Newfoundland, serving approximately 270,000 customers. It is
a subsidiary of Fortis Inc. Newfoundland Power distributes electricity
purchased mainly from NL Hydro.

Official source:
  https://www.newfoundlandpower.com/en/My-Account/Usage/Electricity-Rates

Rates are published in the "Schedule of Rates, Rules and Regulations" PDF
linked from the page above.

Regulated by: Board of Commissioners of Public Utilities (PUB NL)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html, find_pdf_links, extract_pdf_text, extract_effective_date,
)

logger = logging.getLogger(__name__)

_SOURCE_URL = "https://www.newfoundlandpower.com/en/My-Account/Usage/Electricity-Rates"

# Known rate values — used as seed/fallback data.
SEED_RESIDENTIAL = {
    "effective_date": "2025-07-01",
    "source_url": _SOURCE_URL,
    "energy_rate": 0.13263,         # $/kWh
    "basic_charge_per_month": 12.94,  # $/month
}

SEED_GENERAL_SERVICE = {
    "effective_date": "2025-07-01",
    "source_url": _SOURCE_URL,
    "energy_rate": 0.11690,         # $/kWh
    "demand_charge": 10.17,         # $/kW
    "basic_charge_per_month": 25.97,  # $/month
}

# Core service classes published in the Newfoundland Power RateBook.
# (rate code, display name, customer_class, rate_structure). Seasonal
# (1.1S) and street/area-lighting (4.x) schedules are not modelled here.
_NF_RATES: list[tuple[str, str, str, str]] = [
    ("1.1", "Domestic Service", "residential", "flat"),
    ("2.1", "General Service 0-100 kW", "commercial", "demand"),
    ("2.3", "General Service 110 kVA - 1000 kVA", "commercial", "demand"),
    ("2.4", "General Service 1000 kVA and Over", "industrial", "demand"),
]


class NewfoundlandPowerScraper(BaseScraper):
    """Scrape Newfoundland Power electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Newfoundland Power", province="NL")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Newfoundland Power rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Newfoundland Power tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for Newfoundland Power")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Parse the core Domestic + General Service classes from the official RateBook PDF."""
        try:
            html = self.fetch_page(_SOURCE_URL)
        except Exception:
            self.logger.warning("Failed to fetch Newfoundland Power rates page")
            return None

        pdf_links = find_pdf_links(
            parse_html(html), keywords=["ratebook", "schedule", "rates", "regulation"],
            base_url=_SOURCE_URL,
        )
        for link in pdf_links[:6]:
            try:
                text = extract_pdf_text(self.fetch_bytes(link))
            except Exception:
                continue
            if "RATE #1.1" not in text:
                continue
            records = self._parse_ratebook(text, link)
            if records:
                return self.mark_live_parsed(records)
        return None

    def _parse_ratebook(self, text: str, link: str) -> list[TariffRecord]:
        """Build a TariffRecord for each core rate class found in the RateBook text."""
        effective = extract_effective_date(text) or SEED_RESIDENTIAL["effective_date"]
        records: list[TariffRecord] = []
        for code, name, customer_class, structure in _NF_RATES:
            section = self._rate_section(text, code)
            if not section:
                continue
            components = self._parse_components(section)
            if not components:
                continue
            records.append(TariffRecord(
                utility_name="Newfoundland Power", province="NL", utility_type="electricity",
                tariff_name=f"{name} (Rate {code})", tariff_code=code,
                customer_class=customer_class, rate_structure=structure,
                effective_date=effective, source_url=link, confidence="high",
                notes=(
                    "Parsed from the Newfoundland Power RateBook "
                    "(PUB-approved Schedule of Rates, Rules and Regulations)."
                ),
                components=components,
            ))
        return records

    @staticmethod
    def _rate_section(text: str, code: str) -> Optional[str]:
        """Return the charge-bearing detail section for a rate code, bounded to the next rate."""
        for m in re.finditer(rf"RATE #{re.escape(code)}\b", text):
            start = m.start()
            nxt = re.search(r"RATE #\d", text[start + 10:])
            end = start + 10 + nxt.start() if nxt else start + 1800
            section = text[start:end]
            if "Basic Customer Charge" in section:
                return section
        return None

    @staticmethod
    def _slice(text: str, start_label: str, end_labels: list[str]) -> str:
        """Return the text between *start_label* and the earliest of *end_labels*."""
        i = text.find(start_label)
        if i == -1:
            return ""
        i += len(start_label)
        end = len(text)
        for label in end_labels:
            j = text.find(label, i)
            if j != -1:
                end = min(end, j)
        return text[i:end]

    def _parse_components(self, section: str) -> list[RateComponent]:
        """Extract fixed, demand and energy components from one rate-detail section."""
        components: list[RateComponent] = []

        # ── Basic Customer Charge (may have metered/phase variants) ──
        basic = self._slice(
            section, "Basic Customer Charge",
            ["Demand Charge", "Energy Charge", "Minimum Monthly"],
        )
        basic = re.sub(r"\.{3,}", " ... ", basic)
        for label, value in re.findall(
            r"([^$\n]*?)\s*\.\.\.\s*\$?([\d.]+)\s*per month", basic
        ):
            label = label.strip(" :")
            name = (
                "Basic Customer Charge"
                if not label or label.lower().startswith("basic customer")
                else f"Basic Customer Charge ({label})"
            )
            components.append(RateComponent(
                component_type="fixed", component_name=name,
                charge_value=float(value), charge_unit="$/month",
            ))

        # ── Demand Charge (seasonal: winter vs. balance of year) ──
        demand = self._slice(
            section, "Demand Charge",
            ["Energy Charge", "Maximum Monthly", "Minimum Monthly"],
        )
        dm = re.search(
            r"\$([\d.]+)\s*per (kW|kVA).*?and\s*\$([\d.]+)\s*per (?:kW|kVA)",
            demand, re.DOTALL,
        )
        if dm:
            unit = dm.group(2)
            components.append(RateComponent(
                component_type="demand", component_name="Demand Charge (December-March)",
                charge_value=float(dm.group(1)), charge_unit=f"$/{unit}", demand_unit=unit,
                notes="Billing demand, winter months (December-March)",
            ))
            components.append(RateComponent(
                component_type="demand", component_name="Demand Charge (April-November)",
                charge_value=float(dm.group(3)), charge_unit=f"$/{unit}", demand_unit=unit,
                notes="Billing demand, balance of year (April-November)",
            ))

        # ── Energy Charge (flat or tiered, quoted in cents) ──
        energy = self._slice(
            section, "Energy Charge",
            ["Maximum Monthly", "Minimum Monthly", "Discount", "General:"],
        )
        energy = re.sub(r"\.{3,}", " ... ", energy)
        for label, value in re.findall(
            r"(First [\d,]+[^@]*?|All excess[^@]*?|All kilowatt-hours[^@]*?)@\s*([\d.]+)",
            energy,
        ):
            clean = re.sub(r"\s+", " ", label.replace("...", "")).strip(" ,")
            tier_number: Optional[int] = None
            threshold: Optional[float] = None
            low = clean.lower()
            if low.startswith("first"):
                tier_number = 1
                fm = re.search(r"First ([\d,]+) kilowatt-hours(?! per)", clean)
                if fm:
                    threshold = float(fm.group(1).replace(",", ""))
            elif "excess" in low:
                tier_number = 2
            components.append(RateComponent(
                component_type="energy",
                component_name=f"Energy Charge - {clean}"[:120],
                charge_value=round(float(value) / 100.0, 6), charge_unit="$/kWh",
                tier_number=tier_number, tier_threshold=threshold,
                tier_unit="kWh" if threshold else None,
            ))

        return components

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Newfoundland Power",
            province="NL",
            utility_type="electricity",
            tariff_name="Domestic Service (Rate 1.1)",
            tariff_code="1.1",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes="Newfoundland Power (Fortis-owned) domestic residential flat rate",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                    notes="Monthly basic charge regardless of consumption",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        # ── General Service (Demand) ─────────────────────────────
        records.append(TariffRecord(
            utility_name="Newfoundland Power",
            province="NL",
            utility_type="electricity",
            tariff_name="General Service (Rate 2.1)",
            tariff_code="2.1",
            customer_class="commercial",
            sub_class="general service",
            rate_structure="demand",
            effective_date=SEED_GENERAL_SERVICE["effective_date"],
            source_url=SEED_GENERAL_SERVICE["source_url"],
            confidence="high",
            eligibility="Commercial customers with demand metering",
            notes="Newfoundland Power (Fortis-owned) general service rate with demand charge",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_GENERAL_SERVICE["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_GENERAL_SERVICE["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to billing demand (kW)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_GENERAL_SERVICE["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Energy charge per kWh consumed",
                ),
            ],
        ))

        return records
