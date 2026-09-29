"""
yukon_energy.py — Scraper for Yukon Energy Corporation electricity rates (Yukon).

Yukon Energy is a Crown corporation that owns and operates most of the
electricity generation and transmission infrastructure in Yukon.  It
supplies wholesale power to Yukon Electrical Company (ATCO) for
distribution, but also sets end-use rates for some customers.

Most of Yukon's grid electricity comes from hydroelectric generation
(Whitehorse Rapids, Aishihik Lake, Mayo).  However, several remote
communities rely on diesel generation at significantly higher cost;
these "diesel communities" receive rate subsidies so that customers
pay comparable rates to grid-connected areas.

Regulated by the Yukon Utilities Board.

Official source:
  https://yukonenergy.ca/energy-in-yukon/electricity-rates
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

RATE_SCHEDULES_URL = "https://yukonenergy.ca/customer-service/rates/rate-schedules/"

# ── Seed / fallback rate data ─────────────────────────────────────
# Values below are approximate published rates as of early 2025.
# Yukon Energy and Yukon Electrical share a common residential rate
# structure set through the Yukon Utilities Board.

SEED_RESIDENTIAL = {
    "effective_date": "2024-04-01",
    "source_url": "https://yukonenergy.ca/energy-in-yukon/electricity-rates",
    "tier1_threshold_kwh": 1000,   # per month
    "tier1_rate": 0.1326,          # $/kWh
    "tier2_rate": 0.1426,          # $/kWh (above 1000 kWh)
    "basic_charge_monthly": 17.50, # $/month
}

SEED_GENERAL_SERVICE = {
    "effective_date": "2024-04-01",
    "source_url": "https://yukonenergy.ca/energy-in-yukon/electricity-rates",
    "energy_rate": 0.1210,         # $/kWh
    "demand_charge": 15.40,        # $/kW
    "basic_charge_monthly": 25.00, # $/month
}

SEED_DIESEL_COMMUNITY = {
    "effective_date": "2024-04-01",
    "source_url": "https://yukonenergy.ca/energy-in-yukon/electricity-rates",
    "tier1_threshold_kwh": 1000,
    "tier1_rate": 0.1326,          # subsidised to match grid rate
    "tier2_rate": 0.1826,          # higher tail-block for diesel areas
    "basic_charge_monthly": 17.50,
}


class YukonEnergyScraper(BaseScraper):
    """Scrape Yukon Energy Corporation electricity rates."""

    def __init__(self) -> None:
        super().__init__(utility_name="Yukon Energy", province="YT")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Yukon Energy rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records: list[TariffRecord] = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Yukon Energy tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for Yukon Energy")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Parse the effective residential rate (base + Riders R & J) from the official
        Base Rates cross-reference schedule. Other classes stay as labelled seed."""
        try:
            html = self.fetch_page(RATE_SCHEDULES_URL)
            if not html or detect_js_rendered(html):
                html = self.fetch_rendered_page(RATE_SCHEDULES_URL)
            if not html:
                return None
            pdf_links = find_pdf_links(
                parse_html(html), keywords=["base", "rate", "cross", "reference"],
                base_url=RATE_SCHEDULES_URL,
            )
            residential = self._parse_residential_pdf(pdf_links)
            if not residential:
                return None

            live = self.mark_live_parsed([residential])
            seed_only = [r for r in self._seed_data() if r.tariff_name != "Residential Service"]
            if seed_only:
                live = live + self.mark_fallback(seed_only)
            return live
        except Exception:
            self.logger.exception("Error during Yukon Energy live scrape")
            return None

    def _parse_residential_pdf(self, pdf_links: list[str]) -> Optional[TariffRecord]:
        """Return the 1160 residential record (effective rate incl. Riders R & J)."""
        # The Base Rates cross-reference PDF holds the effective (base + rider) rates.
        candidates = [u for u in pdf_links if "cross-reference" in u.lower() or "base_rates" in u.lower()]
        for link in (candidates or pdf_links)[:6]:
            try:
                text = extract_pdf_text(self.fetch_bytes(link))
            except Exception:
                continue
            cust = re.search(r"Customer\s*\$\s*[\d.]+\s*\$\s*[\d.]+\s*\$\s*[\d.]+\s*\$\s*([\d.]+)", text)
            b1 = re.search(r"First 1000 kWh Energy Block 1\s*\u00a2/kWh\s*[\d.]+\s+[\d.]+\s+[\d.]+\s+([\d.]+)", text)
            b2 = re.search(r"1001-2500 kWh Energy Block 2\s*\u00a2/kWh\s*[\d.]+\s+[\d.]+\s+[\d.]+\s+([\d.]+)", text)
            b3 = re.search(r">2500 kWh Energy Block 3\s*\u00a2/kWh\s*[\d.]+\s+[\d.]+\s+[\d.]+\s+([\d.]+)", text)
            if not (cust and b1 and b2 and b3):
                continue
            return TariffRecord(
                utility_name="Yukon Energy", province="YT", utility_type="electricity",
                tariff_name="Residential Service Hydro (Rate 1160)", tariff_code="1160",
                customer_class="residential", rate_structure="tiered",
                effective_date=extract_effective_date(text) or SEED_RESIDENTIAL["effective_date"],
                source_url=link, confidence="high",
                notes=(
                    "Yukon Energy residential (grid hydro, non-government) effective rate "
                    "including Rider R and Rider J, from the official Base Rates cross-reference schedule."
                ),
                components=[
                    RateComponent(
                        component_type="fixed", component_name="Customer Charge",
                        charge_value=float(cust.group(1)), charge_unit="$/month",
                        notes="Monthly customer charge (base + Riders R & J)",
                    ),
                    RateComponent(
                        component_type="energy", component_name="Energy Block 1 (first 1,000 kWh)",
                        charge_value=float(b1.group(1)) / 100.0, charge_unit="$/kWh",
                        tier_number=1, tier_threshold=1000, tier_unit="kWh",
                    ),
                    RateComponent(
                        component_type="energy", component_name="Energy Block 2 (1,001-2,500 kWh)",
                        charge_value=float(b2.group(1)) / 100.0, charge_unit="$/kWh",
                        tier_number=2, tier_threshold=2500, tier_unit="kWh",
                    ),
                    RateComponent(
                        component_type="energy", component_name="Energy Block 3 (over 2,500 kWh)",
                        charge_value=float(b3.group(1)) / 100.0, charge_unit="$/kWh",
                        tier_number=3, tier_threshold=2500, tier_unit="kWh",
                    ),
                ],
            )
        return None

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records: list[TariffRecord] = []

        # ── Residential (Tiered) ─────────────────────────────────
        records.append(TariffRecord(
            utility_name="Yukon Energy",
            province="YT",
            utility_type="electricity",
            tariff_name="Residential Service",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "Yukon residential rate set jointly by Yukon Energy and "
                "Yukon Electrical through the Yukon Utilities Board. "
                "Tier 1 applies to the first 1,000 kWh per month; "
                "tier 2 applies to consumption above that threshold."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Monthly customer charge",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 1 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_RESIDENTIAL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes="First 1,000 kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_RESIDENTIAL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes="All kWh above 1,000 per month",
                ),
            ],
        ))

        # ── General Service ──────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Yukon Energy",
            province="YT",
            utility_type="electricity",
            tariff_name="General Service",
            customer_class="commercial",
            rate_structure="demand",
            effective_date=SEED_GENERAL_SERVICE["effective_date"],
            source_url=SEED_GENERAL_SERVICE["source_url"],
            confidence="medium",
            notes=(
                "General service rate for commercial and institutional "
                "customers. Includes energy charge and demand charge."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_GENERAL_SERVICE["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_GENERAL_SERVICE["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_GENERAL_SERVICE["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    confidence="medium",
                    notes="Billed on peak measured demand in the billing period",
                ),
            ],
        ))

        # ── Diesel Community Residential ─────────────────────────
        records.append(TariffRecord(
            utility_name="Yukon Energy",
            province="YT",
            utility_type="electricity",
            tariff_name="Residential Service — Diesel Communities",
            customer_class="residential",
            sub_class="diesel community",
            rate_structure="tiered",
            effective_date=SEED_DIESEL_COMMUNITY["effective_date"],
            source_url=SEED_DIESEL_COMMUNITY["source_url"],
            confidence="medium",
            notes=(
                "Several remote Yukon communities (e.g. Old Crow, Destruction Bay) "
                "are not connected to the main hydro grid and rely on diesel generation. "
                "The Yukon government subsidises diesel-community rates so that the "
                "first-tier price matches the hydro-grid rate; the second tier is "
                "somewhat higher to reflect the true cost of diesel generation."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_DIESEL_COMMUNITY["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 1 Energy Charge (Diesel Community)",
                    charge_value=SEED_DIESEL_COMMUNITY["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_DIESEL_COMMUNITY["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes="Subsidised to match hydro-grid rate for first 1,000 kWh/month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge (Diesel Community)",
                    charge_value=SEED_DIESEL_COMMUNITY["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_DIESEL_COMMUNITY["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    confidence="medium",
                    notes="Above 1,000 kWh/month — higher rate reflecting diesel costs",
                ),
            ],
        ))

        return records
