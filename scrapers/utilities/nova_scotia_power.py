"""
nova_scotia_power.py — Scraper for Nova Scotia Power electricity rates (Nova Scotia).

Nova Scotia Power Inc. (NSPI) is the primary electricity provider in
Nova Scotia, an investor-owned utility (Emera subsidiary). Rates are
predominantly flat for residential and small general customers.

Official source (landing page — no rate values):
  https://www.nspower.ca/products-services/rate-information

Residential rates page (contains actual values):
  https://www.nspower.ca/your-home/residential-rates/standard-residential

Regulated by: Nova Scotia Utility and Review Board (NSUARB)
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html,
    find_text_near_label,
    extract_rate_from_text,
)
from scrapers.utils.change_detection import (
    compare_to_seed,
    log_change_alerts,
    has_critical_alerts,
)

logger = logging.getLogger(__name__)

# ── URLs ──────────────────────────────────────────────────────────
RESIDENTIAL_URL = (
    "https://www.nspower.ca/your-home/residential-rates/standard-residential"
)

# Known rate values — used as seed/fallback data.
SEED_RESIDENTIAL = {
    "effective_date": "2026-01-01",
    "source_url": RESIDENTIAL_URL,
    "energy_rate": 0.18187,           # $/kWh
    "basic_charge_per_month": 19.17,  # $/month
}

SEED_SMALL_GENERAL = {
    "effective_date": "2026-01-01",
    "source_url": "https://www.nspower.ca/products-services/rate-information",
    "energy_rate": 0.16996,           # $/kWh
    "basic_charge_per_month": 12.74,  # $/month
    "demand_charge": 4.09,            # $/kW — applies above 20 kW
    "demand_threshold_kw": 20,        # demand charge only above this
}


class NovaScotiaPowerScraper(BaseScraper):
    """Scrape Nova Scotia Power electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Nova Scotia Power", province="NS")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Nova Scotia Power rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Nova Scotia Power tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for Nova Scotia Power")
            records.extend(self._seed_data())

        return records

    # ── Live scraping ────────────────────────────────────────────

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live Nova Scotia Power website."""
        try:
            html = self.fetch_page(RESIDENTIAL_URL)
            soup = parse_html(html)

            residential = self._parse_residential(soup)
            if residential is None:
                self.logger.warning("Could not parse residential rates from live page")
                return None

            # Build the live record list: residential from live, commercial from seed
            live_records = [residential]

            # Validate live data against seed using change detection
            seed_residential = self._seed_data_residential()
            alerts = compare_to_seed([residential], [seed_residential])
            log_change_alerts(alerts)

            if has_critical_alerts(alerts):
                self.logger.error(
                    "Critical deviation in live data vs seed — falling back to seed"
                )
                return None

            # Append commercial from seed (no live URL confirmed)
            live_records.append(self._seed_data_small_general())

            return live_records

        except Exception as e:
            self.logger.warning("Could not fetch Nova Scotia Power page: %s", e)
            return None

    def _parse_residential(self, soup) -> Optional[TariffRecord]:
        """
        Parse residential rate values from the standard residential page.

        Expected HTML structure:
          <h4>Base Charge on Your Bill (Fixed Charge)</h4>
          <ul><li>... $19.17 per month ...</li></ul>
          <h4>Energy Charge (Variable Charge)</h4>
          <ul><li>... $0.18187 per kWh ...</li></ul>
        """
        basic_charge = self._extract_basic_charge(soup)
        energy_rate = self._extract_energy_rate(soup)

        if basic_charge is None or energy_rate is None:
            self.logger.warning(
                "Incomplete parse: basic_charge=%s, energy_rate=%s",
                basic_charge,
                energy_rate,
            )
            return None

        # Sanity check: rates should be positive and in reasonable ranges
        if not (1.0 < basic_charge < 100.0):
            self.logger.warning("Basic charge out of range: %s", basic_charge)
            return None
        if not (0.01 < energy_rate < 1.0):
            self.logger.warning("Energy rate out of range: %s", energy_rate)
            return None

        return TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Domestic Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=RESIDENTIAL_URL,
            confidence="high",
            notes="Nova Scotia Power domestic (residential) flat electricity rate — live parsed",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=basic_charge,
                    charge_unit="$/month",
                    notes="Monthly basic charge regardless of consumption",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=energy_rate,
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        )

    def _extract_basic_charge(self, soup) -> Optional[float]:
        """Extract the monthly base/fixed charge from the page."""
        # Approach A: find_text_near_label for "Base Charge" or "Fixed Charge"
        for label in ("Base Charge", "Fixed Charge"):
            text = find_text_near_label(soup, label)
            if text:
                rate = extract_rate_from_text(text)
                if rate is not None:
                    self.logger.debug("Found basic charge via label '%s': %s", label, rate)
                    return rate

        # Approach B: scan all <li> elements for "per month" pattern
        for li in soup.find_all("li"):
            li_text = li.get_text(strip=True)
            if "per month" in li_text.lower() and "$" in li_text:
                rate = extract_rate_from_text(li_text)
                if rate is not None:
                    self.logger.debug("Found basic charge via <li> scan: %s", rate)
                    return rate

        return None

    def _extract_energy_rate(self, soup) -> Optional[float]:
        """Extract the per-kWh energy charge from the page."""
        # Approach A: find_text_near_label for "Energy Charge" or "Variable Charge"
        for label in ("Energy Charge", "Variable Charge"):
            text = find_text_near_label(soup, label)
            if text:
                rate = extract_rate_from_text(text)
                if rate is not None:
                    self.logger.debug("Found energy rate via label '%s': %s", label, rate)
                    return rate

        # Approach B: scan all <li> elements for "per kWh" pattern
        for li in soup.find_all("li"):
            li_text = li.get_text(strip=True)
            if "per kwh" in li_text.lower() and "$" in li_text:
                rate = extract_rate_from_text(li_text)
                if rate is not None:
                    self.logger.debug("Found energy rate via <li> scan: %s", rate)
                    return rate

        return None

    # ── Seed / fallback data ─────────────────────────────────────

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        return [self._seed_data_residential(), self._seed_data_small_general()]

    def _seed_data_residential(self) -> TariffRecord:
        """Return seed data for the residential tariff."""
        return TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Domestic Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes="Nova Scotia Power domestic (residential) flat electricity rate",
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
        )

    def _seed_data_small_general(self) -> TariffRecord:
        """Return seed data for the small general service tariff."""
        return TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Small General Service",
            customer_class="commercial",
            sub_class="small general",
            rate_structure="demand",
            effective_date=SEED_SMALL_GENERAL["effective_date"],
            source_url=SEED_SMALL_GENERAL["source_url"],
            confidence="high",
            eligibility="Small commercial customers; demand charge applies above 20 kW",
            notes=(
                "Nova Scotia Power small general service rate. "
                "Demand charge applies only to billing demand exceeding 20 kW."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_SMALL_GENERAL["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_SMALL_GENERAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_SMALL_GENERAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    demand_threshold_kw=SEED_SMALL_GENERAL["demand_threshold_kw"],
                    notes="Applied to billing demand exceeding 20 kW",
                ),
            ],
        )
