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
        """Parse the current Domestic (Rate 1.1) schedule from the official RateBook PDF.

        The rates page links a RateBook PDF; General Service is kept as a labelled
        seed estimate until parsed.
        """
        try:
            html = self.fetch_page(_SOURCE_URL)
        except Exception:
            self.logger.warning("Failed to fetch Newfoundland Power rates page")
            return None

        pdf_links = find_pdf_links(
            parse_html(html), keywords=["ratebook", "schedule", "rates", "regulation"],
            base_url=_SOURCE_URL,
        )
        residential = self._parse_domestic_pdf(pdf_links)
        if not residential:
            return None

        live = self.mark_live_parsed([residential])
        seed_only = [r for r in self._seed_data() if r.customer_class != "residential"]
        if seed_only:
            live = live + self.mark_fallback(seed_only)
        return live

    def _parse_domestic_pdf(self, pdf_links: list[str]) -> Optional[TariffRecord]:
        """Return the Domestic Rate 1.1 record from the official RateBook PDF."""
        for link in pdf_links[:6]:
            try:
                text = extract_pdf_text(self.fetch_bytes(link))
            except Exception:
                continue
            # Pick the rate-detail occurrence, not a table-of-contents entry.
            section = None
            for match in re.finditer(r"RATE #1\.1", text):
                window = text[match.start():match.start() + 900]
                if "Basic Customer Charge" in window and "Energy Charge" in window:
                    section = window
                    break
            if not section:
                continue
            basic = re.search(r"Basic Customer Charge:.*?\$([\d.]+)\s*per month", section, re.IGNORECASE | re.DOTALL)
            energy = re.search(r"Energy Charge:.*?@?([\d.]+)\s*\u00a2\s*per\s*kWh", section, re.IGNORECASE | re.DOTALL)
            if not basic or not energy:
                continue
            return TariffRecord(
                utility_name="Newfoundland Power", province="NL", utility_type="electricity",
                tariff_name="Domestic Service (Rate 1.1)", tariff_code="1.1",
                customer_class="residential", rate_structure="flat",
                effective_date=extract_effective_date(text) or SEED_RESIDENTIAL["effective_date"],
                source_url=link, confidence="high",
                notes="Newfoundland Power domestic residential flat rate (Rate 1.1), parsed from the official RateBook.",
                components=[
                    RateComponent(
                        component_type="fixed", component_name="Basic Charge",
                        charge_value=float(basic.group(1)), charge_unit="$/month",
                        notes="Monthly basic charge (not exceeding 200 Amp service)",
                    ),
                    RateComponent(
                        component_type="energy", component_name="Energy Charge",
                        charge_value=float(energy.group(1)) / 100.0, charge_unit="$/kWh",
                        notes="Flat rate applied to all kWh",
                    ),
                ],
            )
        return None

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
