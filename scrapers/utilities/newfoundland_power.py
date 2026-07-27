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
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html, detect_js_rendered, find_pdf_links, extract_pdf_text,
    verify_tariff_values,
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
            records.extend(self._seed_data())

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live Newfoundland Power website.

        Fetch the rates page and its official Schedule of Rates PDF. Records
        are returned only when every component is present in extracted text.
        """
        try:
            html = self.fetch_page(_SOURCE_URL)
        except Exception:
            self.logger.warning("Failed to fetch Newfoundland Power rates page")
            return None

        if detect_js_rendered(html):
            self.logger.info(
                "Newfoundland Power rates page appears JS-rendered; "
                "content may be incomplete"
            )

        soup = parse_html(html)
        pdf_links = find_pdf_links(
            soup, keywords=["schedule", "rates", "regulation"], base_url=_SOURCE_URL
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
                self.logger.warning(
                    "Official Newfoundland Power PDF %s is missing: %s",
                    link, ", ".join(missing),
                )
        else:
            self.logger.info(
                "No matching PDF links found on Newfoundland Power rates page"
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
