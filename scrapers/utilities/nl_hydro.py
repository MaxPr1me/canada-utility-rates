"""
nl_hydro.py — Scraper for NL Hydro electricity rates (Newfoundland and Labrador).

Newfoundland and Labrador Hydro (NL Hydro) is the Crown corporation
responsible for electricity generation and transmission in the province.
NL Hydro also directly serves some rural and isolated communities,
as well as customers on the Labrador interconnected system.

Official source:
  https://nlhydro.com/electicity-rates/current-rates/

Regulated by: Board of Commissioners of Public Utilities (PUB NL)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html,
    detect_js_rendered,
    find_pdf_links,
    extract_rate_from_text,
    extract_pdf_text,
    verify_tariff_values,
)

logger = logging.getLogger(__name__)

NL_HYDRO_URL = "https://nlhydro.com/electicity-rates/current-rates/"

# Known rate values — used as seed/fallback data.
# NL Hydro serves rural areas directly; rates shown are for
# island-interconnected rural customers.
SEED_RURAL_RESIDENTIAL = {
    "effective_date": "2026-01-01",
    "source_url": NL_HYDRO_URL,
    "energy_rate": 0.15213,         # $/kWh
    "basic_charge_per_month": 12.94,  # $/month
}

SEED_LABRADOR_INTERCONNECTED = {
    "effective_date": "2026-01-01",
    "source_url": NL_HYDRO_URL,
    "energy_rate": 0.03154,         # $/kWh — Labrador interconnected rate
    "basic_charge_per_month": 12.94,  # $/month
}

SEED_GENERAL_SERVICE = {
    "effective_date": "2026-01-01",
    "source_url": NL_HYDRO_URL,
    "energy_rate": 0.14793,         # $/kWh (estimated proportional increase)
    "basic_charge_per_month": 19.42,  # $/month
    "demand_charge": 8.56,          # $/kW (for demand-metered)
}


class NLHydroScraper(BaseScraper):
    """Scrape NL Hydro electricity rates."""

    def __init__(self):
        super().__init__(utility_name="NL Hydro", province="NL")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live NL Hydro rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d NL Hydro tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for NL Hydro")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """
        Attempt to parse rates from the live NL Hydro website.

        Inspect inline rates, then download the linked official schedule.
        Records are returned only when every component is present in the PDF.
        """
        try:
            html = self.fetch_page(NL_HYDRO_URL)
            if not html:
                self.logger.warning("NL Hydro: empty response from %s", NL_HYDRO_URL)
                return None

            # Check if the page requires JavaScript rendering
            if detect_js_rendered(html):
                self.logger.warning(
                    "NL Hydro: page appears to be JS-rendered, cannot parse static HTML"
                )
                return None

            soup = parse_html(html)
            page_text = soup.get_text(separator=" ")

            # Try to extract inline cent-per-kWh values for quick validation
            # The page shows values like "15.213¢/kWh" and "3.154¢/kWh"
            cent_pattern = re.compile(r"(\d+\.\d+)\s*[¢cents]+\s*/\s*kWh", re.IGNORECASE)
            matches = cent_pattern.findall(page_text)
            if matches:
                self.logger.info(
                    "NL Hydro: found inline energy rates on page: %s ¢/kWh",
                    ", ".join(matches),
                )
            else:
                self.logger.info("NL Hydro: no inline ¢/kWh rates detected on page")

            # Look for PDF links to rate schedules
            pdf_links = find_pdf_links(
                soup, keywords=["schedule", "rates", "regulation"], base_url=NL_HYDRO_URL
            )
            if pdf_links:
                self.logger.info(
                    "NL Hydro: found %d rate PDF link(s) for future implementation:",
                    len(pdf_links),
                )
                records = self._seed_data()
                for link in pdf_links:
                    text = extract_pdf_text(self.fetch_bytes(link))
                    missing = verify_tariff_values(text, records)
                    if not missing:
                        for record in records:
                            record.source_url = link
                            record.confidence = "high"
                            record.notes = f"{record.notes} Live-verified against official PDF."
                            for component in record.components:
                                component.confidence = "high"
                        return records
                    self.logger.warning("Official NL Hydro PDF %s is missing: %s", link, ", ".join(missing))
            else:
                self.logger.info("NL Hydro: no rate PDF links found on page")

            return None

        except Exception as exc:
            self.logger.warning("NL Hydro: live scrape error — %s", exc)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Rural Residential (Island Interconnected) ────────────
        records.append(TariffRecord(
            utility_name="NL Hydro",
            province="NL",
            utility_type="electricity",
            tariff_name="Rural Residential Service (Domestic)",
            customer_class="residential",
            sub_class="rural",
            rate_structure="flat",
            effective_date=SEED_RURAL_RESIDENTIAL["effective_date"],
            source_url=SEED_RURAL_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "NL Hydro rural residential rate for island-interconnected customers. "
                "NL Hydro primarily handles generation and transmission but serves "
                "rural areas directly where Newfoundland Power does not operate."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RURAL_RESIDENTIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Monthly basic charge regardless of consumption",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_RURAL_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        # ── Labrador Interconnected Residential ──────────────────
        records.append(TariffRecord(
            utility_name="NL Hydro",
            province="NL",
            utility_type="electricity",
            tariff_name="Labrador Interconnected Residential Service",
            customer_class="residential",
            sub_class="labrador interconnected",
            rate_structure="flat",
            effective_date=SEED_LABRADOR_INTERCONNECTED["effective_date"],
            source_url=SEED_LABRADOR_INTERCONNECTED["source_url"],
            confidence="medium",
            notes=(
                "NL Hydro residential rate for Labrador interconnected system. "
                "Labrador rates are significantly lower than island rates due to "
                "proximity to Churchill Falls hydroelectric generation."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_LABRADOR_INTERCONNECTED["basic_charge_per_month"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_LABRADOR_INTERCONNECTED["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    notes=(
                        "Labrador interconnected rate — substantially lower than island "
                        "rates due to local hydroelectric generation"
                    ),
                ),
            ],
        ))

        # ── General Service (Commercial) ────────────────────────────
        records.append(TariffRecord(
            utility_name="NL Hydro",
            province="NL",
            utility_type="electricity",
            tariff_name="General Service",
            customer_class="commercial",
            sub_class="general service",
            rate_structure="demand",
            effective_date=SEED_GENERAL_SERVICE["effective_date"],
            source_url=SEED_GENERAL_SERVICE["source_url"],
            confidence="medium",
            notes=(
                "NL Hydro general service rate for commercial customers "
                "in rural areas served directly by NL Hydro."
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
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_GENERAL_SERVICE["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    confidence="medium",
                    notes="Applied to billing demand (kW)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_GENERAL_SERVICE["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                ),
            ],
        ))

        return records
