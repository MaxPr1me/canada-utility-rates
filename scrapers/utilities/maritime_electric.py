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
        """Parse the current Residential Urban rate from the official Schedule of Adjusted Rates PDF.

        General Service is kept as a labelled seed estimate until parsed.
        """
        try:
            html = self.fetch_page(SOURCE_URL)
            if not html:
                return None
            pdf_links = find_pdf_links(
                parse_html(html), keywords=["adjusted", "rate", "schedule", "section"],
                base_url=SOURCE_URL,
            )
            residential = self._parse_residential_pdf(pdf_links)
            if not residential:
                return None

            live = self.mark_live_parsed([residential])
            seed_only = [r for r in self._seed_data() if r.customer_class != "residential"]
            if seed_only:
                live = live + self.mark_fallback(seed_only)
            return live
        except Exception:
            self.logger.exception("Error during Maritime Electric live scrape")
            return None

    def _parse_residential_pdf(self, pdf_links: list[str]) -> Optional[TariffRecord]:
        """Return the Residential Urban (Rate 110) record from the Schedule of Adjusted Rates PDF."""
        for link in pdf_links[:6]:
            try:
                text = extract_pdf_text(self.fetch_bytes(link))
            except Exception:
                continue
            idx = text.find("Residential Urban")
            if idx == -1:
                continue
            section = text[idx:idx + 300]
            service = re.search(r"Service Charge\s*\$\s*([\d.]+)", section)
            tiers = re.findall(
                r"Energy Charge per kWh for (?:first 2,000 kWh|balance(?: of)? kWh)\s*\$\s*([\d.]+)",
                section,
            )
            if not service or len(tiers) < 2:
                continue
            return TariffRecord(
                utility_name="Maritime Electric", province="PE", utility_type="electricity",
                tariff_name="Residential Urban (Rate 110)", tariff_code="110",
                customer_class="residential", rate_structure="tiered",
                effective_date=extract_effective_date(text) or SEED_RESIDENTIAL["effective_date"],
                source_url=link, confidence="high",
                notes="Maritime Electric Residential Urban rate, parsed from the IRAC-approved Schedule of Adjusted Rates.",
                components=[
                    RateComponent(
                        component_type="fixed", component_name="Service Charge",
                        charge_value=float(service.group(1)), charge_unit="$/month",
                        notes="Monthly service charge",
                    ),
                    RateComponent(
                        component_type="energy", component_name="Energy Charge (first 2,000 kWh)",
                        charge_value=float(tiers[0]), charge_unit="$/kWh",
                        tier_number=1, tier_threshold=2000, tier_unit="kWh",
                    ),
                    RateComponent(
                        component_type="energy", component_name="Energy Charge (balance)",
                        charge_value=float(tiers[1]), charge_unit="$/kWh",
                        tier_number=2, tier_threshold=2000, tier_unit="kWh",
                    ),
                ],
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
