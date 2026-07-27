"""
bc_hydro.py — Scraper for BC Hydro electricity rates (British Columbia).

BC Hydro is the primary electricity provider in British Columbia.
Their residential rates use a two-tier (step) pricing structure.

Official sources:
  Residential (tiered): https://app.bchydro.com/accounts-billing/rates-energy-use/electricity-rates/residential-rates/tiered.html
  Business rates:       https://app.bchydro.com/accounts-billing/rates-energy-use/electricity-rates/business-rates.html

Rate classes scraped:
  - Residential Service (Rate 1101) — tiered/step pricing, no demand charge
  - Small General Service (Rate 1300) — flat energy, no demand charge
  - Medium General Service (Rate 1500) — energy + demand charge
  - Large General Service (Rate 1600) — energy + demand charge (higher demand, lower energy)

The live parser fetches sub-pages (tiered.html for residential,
business-rates.html for SGS/MGS) and extracts rates from prose text
using patterns like "XX.XX cents per kWh" and "XX.XX cents per day".

NOTE: BC Hydro redirects www.bchydro.com to app.bchydro.com.
"""

from __future__ import annotations

import re
import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import parse_html, extract_rate_from_text, detect_js_rendered
from scrapers.utils.change_detection import compare_to_seed, log_change_alerts, has_critical_alerts

logger = logging.getLogger(__name__)

# ── Source URLs ───────────────────────────────────────────────────
RESIDENTIAL_URL = "https://app.bchydro.com/accounts-billing/rates-energy-use/electricity-rates/residential-rates/tiered.html"
BUSINESS_URL = "https://app.bchydro.com/accounts-billing/rates-energy-use/electricity-rates/business-rates.html"

# ── Seed / fallback data (updated 2026-04-01) ────────────────────
SEED_RESIDENTIAL = {
    "effective_date": "2026-04-01",
    "source_url": RESIDENTIAL_URL,
    "step1_threshold_kwh": 1350,     # per ~2-month billing period
    "step1_rate": 0.1187,            # $/kWh
    "step2_rate": 0.1408,            # $/kWh
    "basic_charge_per_day": 0.2344,  # $/day
    "rider": -0.015,                 # approximately -1.5% (credit)
}

SEED_SMALL_GENERAL = {
    "effective_date": "2026-04-01",
    "source_url": BUSINESS_URL,
    "energy_rate": 0.1406,           # $/kWh
    "basic_charge_per_day": 0.4089,  # $/day
}

SEED_MEDIUM_GENERAL = {
    "effective_date": "2026-04-01",
    "source_url": BUSINESS_URL,
    "demand_charge": 6.07,           # $/kW
    "energy_rate": 0.1086,           # $/kWh
    "basic_charge_per_day": 0.2999,  # $/day
}

SEED_LARGE_GENERAL = {
    "effective_date": "2026-04-01",
    "source_url": BUSINESS_URL,
    "demand_charge": 13.83,          # $/kW
    "energy_rate": 0.0679,           # $/kWh
    "basic_charge_per_day": 0.2999,  # $/day
}


class BCHydroScraper(BaseScraper):
    """Scrape BC Hydro electricity rates."""

    def __init__(self):
        super().__init__(utility_name="BC Hydro", province="BC")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live BC Hydro rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        # Try live scraping first
        live_records = self._try_live_scrape()
        if live_records:
            self.logger.info(
                "Successfully scraped %d BC Hydro tariffs from live site",
                len(live_records),
            )
            return live_records

        # Fall back to seed data
        self.logger.warning("Live scrape failed -- using seed data for BC Hydro")
        return self.mark_fallback(self._seed_data())

    # ── Live scraping ─────────────────────────────────────────

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live BC Hydro website."""
        try:
            records: list[TariffRecord] = []

            # --- Residential (tiered.html sub-page) ---
            res_record = self._parse_residential()
            if res_record:
                records.append(res_record)

            # --- Business rates (SGS + MGS + LGS) ---
            biz_records = self._parse_business()
            if biz_records:
                records.extend(biz_records)

            if not records:
                return None

            # Change detection: compare live vs seed
            seed = self._seed_data()
            alerts = compare_to_seed(records, seed)
            log_change_alerts(alerts)

            if has_critical_alerts(alerts):
                self.logger.error(
                    "Critical deviations detected in BC Hydro live parse -- "
                    "falling back to seed data"
                )
                return None

            return records

        except Exception as e:
            self.logger.warning("Could not fetch BC Hydro pages: %s", e)
            return None

    def _parse_residential(self) -> Optional[TariffRecord]:
        """Parse residential tiered rates from the tiered.html sub-page."""
        try:
            html = self.fetch_page(RESIDENTIAL_URL)
            if detect_js_rendered(html):
                self.logger.warning("Residential page appears JS-rendered")
                return None

            soup = parse_html(html)
            page_text = soup.get_text(" ", strip=True)

            # Basic charge: look for "XX.XX cents per day"
            basic = self._extract_cents_per(page_text, "cents per day")
            # Step 1: "XX.XX cents per kWh" near Step 1 / Tier 1 text
            step1 = self._extract_step_rate(page_text, step=1)
            # Step 2: "XX.XX cents per kWh" near Step 2 / Tier 2 text
            step2 = self._extract_step_rate(page_text, step=2)

            if basic is None or step1 is None or step2 is None:
                self.logger.warning(
                    "Could not extract all residential rates "
                    "(basic=%s, step1=%s, step2=%s)",
                    basic, step1, step2,
                )
                return None

            self.logger.info(
                "Parsed residential: basic=%.4f, step1=%.4f, step2=%.4f",
                basic, step1, step2,
            )

            return TariffRecord(
                utility_name="BC Hydro",
                province="BC",
                utility_type="electricity",
                tariff_name="Residential Service (Rate 1101)",
                tariff_code="1101",
                customer_class="residential",
                rate_structure="tiered",
                effective_date=SEED_RESIDENTIAL["effective_date"],
                source_url=RESIDENTIAL_URL,
                confidence="high",
                notes="BC Hydro two-step residential rate. Step 1 applies up to threshold per billing period.",
                components=[
                    RateComponent(
                        component_type="fixed",
                        component_name="Basic Charge",
                        charge_value=basic,
                        charge_unit="$/day",
                        notes="Daily basic charge regardless of consumption",
                    ),
                    RateComponent(
                        component_type="energy",
                        component_name="Step 1 Energy Charge",
                        charge_value=step1,
                        charge_unit="$/kWh",
                        tier_number=1,
                        tier_threshold=SEED_RESIDENTIAL["step1_threshold_kwh"],
                        tier_unit="kWh",
                        notes="Applies to first 1,350 kWh per ~2-month billing period",
                    ),
                    RateComponent(
                        component_type="energy",
                        component_name="Step 2 Energy Charge",
                        charge_value=step2,
                        charge_unit="$/kWh",
                        tier_number=2,
                        tier_threshold=SEED_RESIDENTIAL["step1_threshold_kwh"],
                        tier_unit="kWh",
                        notes="Applies to all kWh above the Step 1 threshold",
                    ),
                    RateComponent(
                        component_type="rider",
                        component_name="Rate Rider -- Deferral Account Rate Rider",
                        charge_value=SEED_RESIDENTIAL["rider"],
                        charge_unit="fraction",
                        confidence="medium",
                        notes="Approximately -1.5% credit; check BC Hydro tariff supplement for current value",
                    ),
                ],
            )

        except Exception as e:
            self.logger.warning("Error parsing residential page: %s", e)
            return None

    def _parse_business(self) -> Optional[list[TariffRecord]]:
        """Parse SGS (1300), MGS (1500), and LGS (1600) from business-rates.html."""
        try:
            html = self.fetch_page(BUSINESS_URL)
            if detect_js_rendered(html):
                self.logger.warning("Business rates page appears JS-rendered")
                return None

            soup = parse_html(html)
            page_text = soup.get_text(" ", strip=True)

            records: list[TariffRecord] = []

            # --- Small General Service (Rate 1300) ---
            sgs = self._parse_sgs(page_text)
            if sgs:
                records.append(sgs)

            # --- Medium General Service (Rate 1500) ---
            mgs = self._parse_mgs(page_text)
            if mgs:
                records.append(mgs)

            # --- Large General Service (Rate 1600) ---
            lgs = self._parse_lgs(page_text)
            if lgs:
                records.append(lgs)

            return records if records else None

        except Exception as e:
            self.logger.warning("Error parsing business rates page: %s", e)
            return None

    def _parse_sgs(self, page_text: str) -> Optional[TariffRecord]:
        """Extract Small General Service rates from page text."""
        # Isolate the SGS section: between "Small General Service" and
        # "Medium General Service" headers
        sgs_section = self._extract_section(
            page_text, "Small General Service", "Medium General Service"
        )
        if not sgs_section:
            self.logger.warning("Could not find SGS section in business page")
            return None

        basic = self._extract_cents_per(sgs_section, "cents per day")
        energy = self._extract_cents_per(sgs_section, "cents per kWh")

        if basic is None or energy is None:
            self.logger.warning(
                "Could not extract SGS rates (basic=%s, energy=%s)",
                basic, energy,
            )
            return None

        self.logger.info("Parsed SGS: basic=%.4f, energy=%.4f", basic, energy)

        return TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Small General Service (Rate 1300)",
            tariff_code="1300",
            customer_class="commercial",
            sub_class="small general service",
            rate_structure="flat",
            effective_date=SEED_SMALL_GENERAL["effective_date"],
            source_url=BUSINESS_URL,
            confidence="high",
            eligibility="Commercial customers with annual peak demand under 35 kW",
            demand_max_kw=35,
            notes="BC Hydro small commercial rate -- flat energy charge, no demand charge",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=basic,
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=energy,
                    charge_unit="$/kWh",
                ),
            ],
        )

    def _parse_mgs(self, page_text: str) -> Optional[TariffRecord]:
        """Extract Medium General Service rates from page text."""
        # Isolate the MGS section: after "Medium General Service"
        mgs_section = self._extract_section(
            page_text, "Medium General Service", "Large General Service"
        )
        if not mgs_section:
            # Try without end marker if LGS section doesn't appear
            mgs_section = self._extract_section(
                page_text, "Medium General Service", None
            )
        if not mgs_section:
            self.logger.warning("Could not find MGS section in business page")
            return None

        basic = self._extract_cents_per(mgs_section, "cents per day")
        energy = self._extract_cents_per(mgs_section, "cents per kWh")
        demand = self._extract_dollar_per(mgs_section, r"\$\s*([\d.]+)\s*per\s*kW\b")

        if basic is None or energy is None or demand is None:
            self.logger.warning(
                "Could not extract MGS rates (basic=%s, energy=%s, demand=%s)",
                basic, energy, demand,
            )
            return None

        self.logger.info(
            "Parsed MGS: basic=%.4f, energy=%.4f, demand=%.2f",
            basic, energy, demand,
        )

        return TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Medium General Service (Rate 1500)",
            tariff_code="1500",
            customer_class="commercial",
            sub_class="medium general service",
            rate_structure="demand",
            effective_date=SEED_MEDIUM_GENERAL["effective_date"],
            source_url=BUSINESS_URL,
            confidence="high",
            eligibility="Commercial customers with annual peak demand between 35 and 150 kW",
            demand_max_kw=150,
            notes="BC Hydro medium commercial rate with demand charge; served at secondary voltage",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=basic,
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=demand,
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to highest 15-minute demand average per billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=energy,
                    charge_unit="$/kWh",
                ),
            ],
        )

    def _parse_lgs(self, page_text: str) -> Optional[TariffRecord]:
        """Extract Large General Service rates from page text."""
        # Isolate the LGS section: after "Large General Service" until end or next section
        lgs_section = self._extract_section(
            page_text, "Large General Service", "Declaration of Eligibility"
        )
        if not lgs_section:
            lgs_section = self._extract_section(
                page_text, "Large General Service", None
            )
        if not lgs_section:
            self.logger.warning("Could not find LGS section in business page")
            return None

        basic = self._extract_cents_per(lgs_section, "cents per day")
        energy = self._extract_cents_per(lgs_section, "cents per kWh")
        demand = self._extract_dollar_per(lgs_section, r"\$\s*([\d.]+)\s*per\s*kW\b")

        if basic is None or energy is None or demand is None:
            self.logger.warning(
                "Could not extract LGS rates (basic=%s, energy=%s, demand=%s)",
                basic, energy, demand,
            )
            return None

        self.logger.info(
            "Parsed LGS: basic=%.4f, energy=%.4f, demand=%.2f",
            basic, energy, demand,
        )

        return TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Large General Service (Rate 1600)",
            tariff_code="1600",
            customer_class="commercial",
            sub_class="large general service",
            rate_structure="demand",
            effective_date=SEED_LARGE_GENERAL["effective_date"],
            source_url=BUSINESS_URL,
            confidence="high",
            eligibility="Commercial customers with annual peak demand of at least 150 kW, or using more than 550,000 kWh/year",
            demand_min_kw=150,
            notes="BC Hydro large commercial rate with demand charge; higher demand rate, lower energy rate than MGS",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=basic,
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=demand,
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to highest 15-minute demand average per billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=energy,
                    charge_unit="$/kWh",
                ),
            ],
        )

    # ── Text extraction helpers ───────────────────────────────

    @staticmethod
    def _extract_section(
        text: str,
        start_marker: str,
        end_marker: Optional[str],
    ) -> Optional[str]:
        """
        Extract a slice of text between start_marker and end_marker
        (case-insensitive). If end_marker is None, returns everything
        after start_marker.
        """
        lower = text.lower()
        start_idx = lower.find(start_marker.lower())
        if start_idx == -1:
            return None

        # Move past the marker itself
        start_idx += len(start_marker)

        if end_marker:
            end_idx = lower.find(end_marker.lower(), start_idx)
            if end_idx == -1:
                return text[start_idx:]
            return text[start_idx:end_idx]

        return text[start_idx:]

    @staticmethod
    def _extract_cents_per(text: str, unit_pattern: str) -> Optional[float]:
        """
        Find the first occurrence of "XX.XX <unit_pattern>" and return
        the value converted to dollars.

        Example: _extract_cents_per(text, "cents per day") finds
        "23.44 cents per day" and returns 0.2344.
        """
        pattern = rf"([\d]+\.?\d*)\s*{re.escape(unit_pattern)}"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1)) / 100.0
        return None

    @staticmethod
    def _extract_dollar_per(text: str, pattern: str) -> Optional[float]:
        """
        Find a dollar amount matching the given regex pattern.
        The pattern should have one capture group for the numeric value.

        Example: _extract_dollar_per(text, r"\\$\\s*([\\d.]+)\\s*per\\s*kW")
        finds "$6.07 per kW" and returns 6.07.
        """
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None

    @staticmethod
    def _extract_step_rate(page_text: str, step: int) -> Optional[float]:
        """
        Extract the energy rate for a given step/tier from residential page text.

        Looks for patterns like:
          "11.87 cents per kWh" near "Step 1" / "Tier 1"
        """
        # Split text into chunks around Step N / Tier N references
        labels = [f"step {step}", f"tier {step}"]
        lower = page_text.lower()

        for label in labels:
            idx = lower.find(label)
            if idx == -1:
                continue

            # Search in a window after the label for "XX.XX cents per kWh"
            window = page_text[max(0, idx - 50):idx + 300]
            match = re.search(
                r"([\d]+\.?\d*)\s*cents\s*per\s*kWh",
                window,
                re.IGNORECASE,
            )
            if match:
                return float(match.group(1)) / 100.0

        return None

    # ── Seed / fallback data ──────────────────────────────────

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # -- Residential (Step / Tiered) --
        records.append(TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Residential Service (Rate 1101)",
            tariff_code="1101",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes="BC Hydro two-step residential rate. Step 1 applies up to threshold per billing period.",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_day"],
                    charge_unit="$/day",
                    notes="Daily basic charge regardless of consumption",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Step 1 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["step1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_RESIDENTIAL["step1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="Applies to first 1,350 kWh per ~2-month billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Step 2 Energy Charge",
                    charge_value=SEED_RESIDENTIAL["step2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_RESIDENTIAL["step1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="Applies to all kWh above the Step 1 threshold",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Rate Rider -- Deferral Account Rate Rider",
                    charge_value=SEED_RESIDENTIAL["rider"],
                    charge_unit="fraction",
                    confidence="medium",
                    notes="Approximately -1.5% credit; check BC Hydro tariff supplement for current value",
                ),
            ],
        ))

        # -- Small General Service (Rate 1300) -- flat, NO demand charge --
        records.append(TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Small General Service (Rate 1300)",
            tariff_code="1300",
            customer_class="commercial",
            sub_class="small general service",
            rate_structure="flat",
            effective_date=SEED_SMALL_GENERAL["effective_date"],
            source_url=SEED_SMALL_GENERAL["source_url"],
            confidence="high",
            eligibility="Commercial customers with annual peak demand under 35 kW",
            demand_max_kw=35,
            notes="BC Hydro small commercial rate -- flat energy charge, no demand charge",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_SMALL_GENERAL["basic_charge_per_day"],
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_SMALL_GENERAL["energy_rate"],
                    charge_unit="$/kWh",
                ),
            ],
        ))

        # -- Medium General Service (Rate 1500) -- has demand charge --
        records.append(TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Medium General Service (Rate 1500)",
            tariff_code="1500",
            customer_class="commercial",
            sub_class="medium general service",
            rate_structure="demand",
            effective_date=SEED_MEDIUM_GENERAL["effective_date"],
            source_url=SEED_MEDIUM_GENERAL["source_url"],
            confidence="high",
            eligibility="Commercial customers with annual peak demand between 35 and 150 kW",
            demand_max_kw=150,
            notes="BC Hydro medium commercial rate with demand charge; served at secondary voltage",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_MEDIUM_GENERAL["basic_charge_per_day"],
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_MEDIUM_GENERAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to highest 15-minute demand average per billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_MEDIUM_GENERAL["energy_rate"],
                    charge_unit="$/kWh",
                ),
            ],
        ))

        # -- Large General Service (Rate 1600) -- higher demand, lower energy --
        records.append(TariffRecord(
            utility_name="BC Hydro",
            province="BC",
            utility_type="electricity",
            tariff_name="Large General Service (Rate 1600)",
            tariff_code="1600",
            customer_class="commercial",
            sub_class="large general service",
            rate_structure="demand",
            effective_date=SEED_LARGE_GENERAL["effective_date"],
            source_url=SEED_LARGE_GENERAL["source_url"],
            confidence="high",
            eligibility="Commercial customers with annual peak demand of at least 150 kW, or using more than 550,000 kWh/year",
            demand_min_kw=150,
            notes="BC Hydro large commercial rate with demand charge; higher demand rate, lower energy rate than MGS",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_LARGE_GENERAL["basic_charge_per_day"],
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_LARGE_GENERAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to highest 15-minute demand average per billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_LARGE_GENERAL["energy_rate"],
                    charge_unit="$/kWh",
                ),
            ],
        ))

        return records
