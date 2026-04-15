"""
hydro_quebec.py — Scraper for Hydro-Québec electricity rates (Quebec).

Hydro-Québec is the sole electricity distributor in Quebec.
They have notably low residential rates compared to most of Canada.

Official source:
  https://www.hydroquebec.com/residential/customer-space/rates/

Hydro-Québec rates include:
  - Rate D: Domestic (residential)
  - Rate DM: Residential with dual-energy heating
  - Rate G: General / small commercial (< 100 kW)
  - Rate M: Medium-power (100–5000 kW)
  - Rate L: Large industrial (> 5000 kW, special contracts)

This scraper handles Rate D and Rate G as examples.

Note: Hydro-Québec's rate pages are JS-rendered (populate-data.js injects
values client-side), so BeautifulSoup cannot extract rate values directly.
The scraper detects this and falls back to seed data until a headless
browser or PDF-based approach is implemented.
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import parse_html, detect_js_rendered, find_pdf_links

logger = logging.getLogger(__name__)

# Seed data based on published rates (updated periodically).
# Hydro-Québec adjusts rates annually, typically April 1.
#
# Note: Rate values below are carried forward from the 2024 schedule.
# The HQ rates page is JS-rendered (populate-data.js), so exact 2026
# values cannot be confirmed without a headless browser. Confidence
# is set to "medium" accordingly.
SEED_RATE_D = {
    "effective_date": "2026-04-01",
    "source_url": "https://www.hydroquebec.com/residential/customer-space/rates/rate-d.html",
    "first_40kwh_per_day": 0.06509,   # $/kWh for first 40 kWh/day
    "remaining": 0.10041,             # $/kWh for remaining consumption
    "fixed_per_day": 0.4064,          # $/day
}

SEED_RATE_G = {
    "effective_date": "2026-04-01",
    "source_url": "https://www.hydroquebec.com/business/customer-space/rates/rate-g-general-rate.html",
    "first_15000kwh": 0.06509,
    "remaining": 0.04336,
    "demand_charge_first_50kw": 0.00,
    "demand_charge_above_50kw": 18.89,
    "fixed_per_day": 1.3820,
}


class HydroQuebecScraper(BaseScraper):
    """Scrape Hydro-Québec electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Hydro-Québec", province="QC")

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data for Hydro-Québec")
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt live scraping of Hydro-Québec rates.

        Hydro-Québec's rate pages use client-side JS (populate-data.js)
        to inject rate values, so standard HTML fetching returns an empty
        shell. This method detects that condition and looks for PDF
        fallback links before giving up.
        """
        try:
            html = self.fetch_page(SEED_RATE_D["source_url"])
            if not html:
                self.logger.warning("Empty response from Hydro-Québec rate page")
                return None

            # Check if the page relies on JS to render rate data
            if detect_js_rendered(html):
                self.logger.warning(
                    "Hydro-Québec rate page is JS-rendered (populate-data.js); "
                    "cannot extract rates with static HTML parsing"
                )

                # Look for PDF links as a potential alternative source
                soup = parse_html(html)
                pdf_links = find_pdf_links(
                    soup, keywords=["rates", "electricity", "tarif"]
                )
                if pdf_links:
                    self.logger.info(
                        "Found %d PDF link(s) on Hydro-Québec page for future "
                        "implementation: %s",
                        len(pdf_links),
                        pdf_links,
                    )
                else:
                    self.logger.info(
                        "No relevant PDF links found on Hydro-Québec rate page"
                    )

                return None

            # If the page is not JS-rendered (unlikely for HQ, but handle it),
            # full HTML parsing would go here in the future.
            self.logger.info(
                "Hydro-Québec page did not appear JS-rendered, but no "
                "HTML parser is implemented yet — falling back to seed data"
            )
            return None

        except Exception as e:
            self.logger.warning("Could not fetch Hydro-Québec page: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Rate D: Domestic (Residential) ────────────────────
        records.append(TariffRecord(
            utility_name="Hydro-Québec",
            province="QC",
            utility_type="electricity",
            tariff_name="Rate D — Domestic",
            tariff_code="D",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=SEED_RATE_D["effective_date"],
            source_url=SEED_RATE_D["source_url"],
            confidence="medium",
            notes=(
                "Hydro-Québec residential rate. Tier threshold is 40 kWh/day "
                "(~1,200 kWh/month in a 30-day period). "
                "Rate values carried forward from 2024 — source page is "
                "JS-rendered and cannot be verified without a headless browser."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Daily Fixed Charge",
                    charge_value=SEED_RATE_D["fixed_per_day"],
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="First 40 kWh/day",
                    charge_value=SEED_RATE_D["first_40kwh_per_day"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=40.0,
                    tier_unit="kWh/day",
                    notes="Applies to first 40 kWh per day of the billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Remaining consumption",
                    charge_value=SEED_RATE_D["remaining"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=40.0,
                    tier_unit="kWh/day",
                    notes="Applies to all kWh beyond 40/day",
                ),
            ],
        ))

        # ── Rate G: General (Small Commercial) ────────────────
        records.append(TariffRecord(
            utility_name="Hydro-Québec",
            province="QC",
            utility_type="electricity",
            tariff_name="Rate G — General",
            tariff_code="G",
            customer_class="commercial",
            sub_class="small general",
            rate_structure="mixed",
            effective_date=SEED_RATE_G["effective_date"],
            source_url=SEED_RATE_G["source_url"],
            confidence="medium",
            eligibility="Contract capacity under 100 kW",
            demand_max_kw=100,
            notes=(
                "Hydro-Québec small commercial rate — energy charge is tiered, "
                "plus demand charge above 50 kW. "
                "Rate values carried forward from 2024 — source page is "
                "JS-rendered and cannot be verified without a headless browser."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Daily Fixed Charge",
                    charge_value=SEED_RATE_G["fixed_per_day"],
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="First 15,000 kWh",
                    charge_value=SEED_RATE_G["first_15000kwh"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=15000,
                    tier_unit="kWh",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Remaining kWh",
                    charge_value=SEED_RATE_G["remaining"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=15000,
                    tier_unit="kWh",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge (above 50 kW)",
                    charge_value=SEED_RATE_G["demand_charge_above_50kw"],
                    charge_unit="$/kW",
                    demand_threshold_kw=50,
                    demand_unit="kW",
                    notes="No demand charge for first 50 kW; $18.89/kW above 50 kW",
                ),
            ],
        ))

        return records
