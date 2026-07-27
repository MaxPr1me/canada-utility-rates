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
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html, detect_js_rendered, find_pdf_links, extract_pdf_text,
    verify_tariff_values,
)

logger = logging.getLogger(__name__)

LANDING_URL = "https://www.saskpower.com/accounts/power-rates/power-supply-rates"

# Known rate values — used as seed/fallback data.
# Values reflect SaskPower's published rates; effective_date updated to
# the most recent known adjustment period.
SEED_RESIDENTIAL = {
    "effective_date": "2025-01-01",
    "source_url": LANDING_URL,
    "energy_rate": 0.1797,          # $/kWh — flat rate
    "basic_charge_per_month": 24.05,  # $/month
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
            if html is None:
                self.logger.warning("Could not fetch SaskPower landing page")
                return None

            # Check whether the page requires JavaScript rendering
            if detect_js_rendered(html):
                self.logger.info(
                    "SaskPower landing page appears JS-rendered; "
                    "cannot parse without a headless browser"
                )
                return None

            soup = parse_html(html)

            # Look for PDF links related to rate schedules
            pdf_links = find_pdf_links(
                soup, keywords=["residential", "rate", "schedule"], base_url=LANDING_URL
            )

            if pdf_links:
                records = self._seed_data()
                for link in pdf_links:
                    text = extract_pdf_text(self.fetch_bytes(link))
                    missing = verify_tariff_values(text, records)
                    if not missing:
                        for record in records:
                            record.source_url = link
                            record.notes = f"{record.notes}; live-verified against official PDF"
                        return records
                    self.logger.warning("Official SaskPower PDF %s is missing: %s", link, ", ".join(missing))
            else:
                self.logger.info(
                    "No PDF links detected on SaskPower rates page; "
                    "page structure may have changed"
                )

            return None

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
