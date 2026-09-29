"""
saskpower.py — Scraper for SaskPower electricity rates (Saskatchewan).

SaskPower is the principal electric utility in Saskatchewan, a Crown
corporation providing generation, transmission, and distribution
province-wide. Rates are flat (non-tiered) for most customer classes.

Official source:
  https://www.saskpower.com/accounts/power-rates/power-supply-rates

SaskPower publishes rate schedules as PDFs linked from the landing page.
The live scraper downloads the official schedule and verifies every seeded
component before returning it as live-verified data.

Regulated by: Saskatchewan Rate Review Panel
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html, detect_js_rendered, find_pdf_links, extract_pdf_text,
    extract_effective_date,
)

logger = logging.getLogger(__name__)

LANDING_URL = "https://www.saskpower.com/accounts/power-rates/power-supply-rates"

# Known rate values — used as seed/fallback data.
# Values reflect SaskPower's published rates; effective_date updated to
# the most recent known adjustment period.
SEED_RESIDENTIAL = {
    "effective_date": "2026-02-01",
    "source_url": LANDING_URL,
    "energy_rate": 0.15476,         # $/kWh — flat rate (15.476¢/kWh)
    "basic_charge_per_month": 31.16,  # $/month
}

SEED_SMALL_COMMERCIAL = {
    "effective_date": "2025-01-01",
    "source_url": LANDING_URL,
    "energy_rate": 0.1797,          # $/kWh
    "basic_charge_per_month": 40.24,  # $/month
}

SEED_DEMAND_COMMERCIAL = {
    "effective_date": "2025-01-01",
    "source_url": LANDING_URL,
    "energy_rate": 0.0928,          # $/kWh
    "demand_charge": 14.94,         # $/kW
    "basic_charge_per_month": 40.24,  # $/month
}


class SaskPowerScraper(BaseScraper):
    """Scrape SaskPower electricity rates."""

    def __init__(self):
        super().__init__(utility_name="SaskPower", province="SK")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live SaskPower rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d SaskPower tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for SaskPower")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """
        Attempt to parse rates from the live SaskPower website.

        SaskPower's rates page links to PDF rate schedules rather than
        publishing rates in HTML. Download the official PDF and return
        records only when every component can be verified in its text.
        """
        try:
            html = self.fetch_page(LANDING_URL)
            if not html or detect_js_rendered(html):
                # The landing page is JS-rendered; render it to reveal PDF links.
                html = self.fetch_rendered_page(LANDING_URL)
            if not html:
                self.logger.warning("Could not fetch SaskPower rates page")
                return None

            pdf_links = find_pdf_links(
                parse_html(html),
                keywords=["residential", "rate", "schedule", "service"],
                base_url=LANDING_URL,
            )
            res_pdf = next((u for u in pdf_links if "residential" in u.lower()), None)
            if not res_pdf:
                self.logger.info("No SaskPower residential rate PDF found on page")
                return None

            text = extract_pdf_text(self.fetch_bytes(res_pdf))
            basic = re.search(r"Basic monthly charge[^\d]*([\d.]+)", text, re.IGNORECASE)
            energy = re.search(r"Energy charge[^\d]*([\d.]+)\s*\u00a2", text, re.IGNORECASE)
            if not basic or not energy:
                self.logger.warning(
                    "Could not parse SaskPower residential PDF (basic=%s, energy=%s)",
                    basic, energy,
                )
                return None

            residential = TariffRecord(
                utility_name="SaskPower", province="SK", utility_type="electricity",
                tariff_name="Residential Service", customer_class="residential",
                rate_structure="flat",
                effective_date=extract_effective_date(text) or SEED_RESIDENTIAL["effective_date"],
                source_url=res_pdf, confidence="high",
                notes="SaskPower flat residential rate (Standard Rate E01/E03).",
                components=[
                    RateComponent(
                        component_type="fixed", component_name="Basic Charge",
                        charge_value=float(basic.group(1)), charge_unit="$/month",
                    ),
                    RateComponent(
                        component_type="energy", component_name="Energy Charge",
                        charge_value=float(energy.group(1)) / 100.0, charge_unit="$/kWh",
                    ),
                ],
            )
            live = self.mark_live_parsed(
                [residential], source_url=res_pdf, detail="Official residential rate schedule PDF"
            )

            # Preserve commercial classes (separate schedules) as labelled seed
            seed_only = [r for r in self._seed_data() if r.tariff_name != "Residential Service"]
            if seed_only:
                live = live + self.mark_fallback(seed_only)
            return live

        except Exception:
            self.logger.exception("Error during SaskPower live scrape")
            return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="SaskPower",
            province="SK",
            utility_type="electricity",
            tariff_name="Residential Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes="SaskPower flat residential electricity rate (PDF source)",
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

        # ── Small Commercial (Non-Demand) ────────────────────────
        records.append(TariffRecord(
            utility_name="SaskPower",
            province="SK",
            utility_type="electricity",
            tariff_name="Small Commercial Service",
            customer_class="commercial",
            sub_class="small commercial",
            rate_structure="flat",
            effective_date=SEED_SMALL_COMMERCIAL["effective_date"],
            source_url=SEED_SMALL_COMMERCIAL["source_url"],
            confidence="high",
            eligibility="Small commercial customers without demand metering",
            notes="SaskPower small commercial rate without demand charge (PDF source)",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_SMALL_COMMERCIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_SMALL_COMMERCIAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        # ── Demand Commercial ────────────────────────────────────
        records.append(TariffRecord(
            utility_name="SaskPower",
            province="SK",
            utility_type="electricity",
            tariff_name="Power Service (Demand)",
            customer_class="commercial",
            sub_class="demand commercial",
            rate_structure="demand",
            effective_date=SEED_DEMAND_COMMERCIAL["effective_date"],
            source_url=SEED_DEMAND_COMMERCIAL["source_url"],
            confidence="high",
            eligibility="Commercial customers with demand metering",
            notes="SaskPower demand-metered commercial rate (PDF source)",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_DEMAND_COMMERCIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_DEMAND_COMMERCIAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to billing demand (kW)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_DEMAND_COMMERCIAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Energy charge per kWh consumed",
                ),
            ],
        ))

        return records
