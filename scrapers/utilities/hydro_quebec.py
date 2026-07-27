"""
hydro_quebec.py — Scraper for Hydro-Québec electricity rates (Quebec).

Hydro-Québec is the sole electricity distributor in Quebec.
They have notably low residential rates compared to most of Canada.

Official source (PDF):
  https://www.hydroquebec.com/data/documents-donnees/pdf/electricity-rates.pdf

Hydro-Québec rates include:
  - Rate D: Domestic (residential)
  - Rate G: General / small commercial (< 65 kW)
  - Rate M: Medium-power (50–5,000 kW)
  - Rate L: Large industrial (> 5,000 kW, special contracts)

This scraper handles Rate D, Rate G, and Rate M.

The scraper downloads the official electricity-rates PDF and extracts
rate values using pdfplumber text extraction + regex. If the PDF fetch
or parse fails, it falls back to verified seed data.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import parse_html, detect_js_rendered, find_pdf_links, extract_pdf_text
from scrapers.utils.change_detection import compare_to_seed, log_change_alerts, has_critical_alerts

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────
PDF_URL = "https://www.hydroquebec.com/data/documents-donnees/pdf/electricity-rates.pdf"
RATE_D_URL = "https://www.hydroquebec.com/residential/customer-space/rates/rate-d.html"

# ── Seed data — verified from electricity-rates.pdf, effective 2026-04-01 ─
SEED_RATE_D = {
    "effective_date": "2026-04-01",
    "source_url": PDF_URL,
    "fixed_per_day": 0.46154,            # $/day (46.154 cents/day)
    "first_40kwh_per_day": 0.07065,      # $/kWh (7.065 cents/kWh)
    "remaining": 0.11142,                # $/kWh (11.142 cents/kWh)
    "tier_threshold_kwh_per_day": 40,
}

SEED_RATE_G = {
    "effective_date": "2026-04-01",
    "source_url": PDF_URL,
    "fixed_per_month": 15.426,           # $/month
    "demand_charge_above_50kw": 22.071,  # $/kW above 50 kW
    "demand_free_kw": 50,
    "first_15090kwh": 0.12388,           # $/kWh
    "remaining": 0.09534,               # $/kWh
    "tier_threshold_kwh": 15090,
    "eligibility": "Contract capacity under 65 kW",
}

SEED_RATE_M = {
    "effective_date": "2026-04-01",
    "source_url": PDF_URL,
    "demand_charge": 18.242,             # $/kW
    "first_210000kwh": 0.06292,          # $/kWh
    "remaining": 0.04666,               # $/kWh
    "tier_threshold_kwh": 210000,
    "eligibility": "Contract power 50 kW to 5,000 kW",
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
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    # ── Live PDF parser ───────────────────────────────────────

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Download the HQ electricity-rates PDF and extract rates."""
        try:
            # Try HTML page first to confirm JS-rendered status
            html = self.fetch_page(RATE_D_URL)
            if html and detect_js_rendered(html):
                self.logger.info(
                    "HQ rate page is JS-rendered, trying PDF fallback"
                )

            # Download and parse PDF
            pdf_bytes = self.fetch_bytes(PDF_URL)
            if not pdf_bytes:
                self.logger.warning("Empty response from HQ PDF download")
                return None

            pdf_text = extract_pdf_text(pdf_bytes)
            if not pdf_text:
                self.logger.warning("Could not extract text from HQ PDF")
                return None

            records = []

            rate_d = self._parse_rate_d(pdf_text)
            if rate_d:
                records.append(rate_d)

            rate_g = self._parse_rate_g(pdf_text)
            if rate_g:
                records.append(rate_g)

            rate_m = self._parse_rate_m(pdf_text)
            if rate_m:
                records.append(rate_m)

            if not records:
                self.logger.warning("No rates parsed from HQ PDF")
                return None

            # Compare live-parsed values against seed data
            alerts = compare_to_seed(records, self._seed_data())
            log_change_alerts(alerts)
            if has_critical_alerts(alerts):
                self.logger.error(
                    "Critical deviation detected in HQ live parse — "
                    "rejecting live data and falling back to seed"
                )
                return None

            self.logger.info(
                "Successfully parsed %d rate(s) from Hydro-Québec PDF",
                len(records),
            )
            return records

        except Exception as e:
            self.logger.warning("Could not fetch/parse Hydro-Québec PDF: %s", e)
            return None

    # ── Section extraction helpers ────────────────────────────

    @staticmethod
    def _extract_section(pdf_text: str, section_start: str, section_end: str) -> str:
        """Extract text between two section markers (case-insensitive)."""
        text_lower = pdf_text.lower()
        start = text_lower.find(section_start.lower())
        if start == -1:
            return ""
        end = text_lower.find(section_end.lower(), start + len(section_start))
        if end == -1:
            return pdf_text[start:]
        return pdf_text[start:end]

    # ── Rate D parser ─────────────────────────────────────────

    def _parse_rate_d(self, pdf_text: str) -> Optional[TariffRecord]:
        """Parse Rate D (Domestic/Residential) from PDF text."""
        # Extract the Rate D section — ends at Rate DM or Rate G
        section = self._extract_section(pdf_text, "Rate D", "Rate DM")
        if not section:
            section = self._extract_section(pdf_text, "Rate D", "Rate G")
        if not section:
            self.logger.warning("Could not find Rate D section in PDF")
            return None

        # Fixed charge: look for "XX.XXX¢ per day" or "XX.XXX cents per day"
        fixed_match = re.search(
            r'([\d.]+)\s*[¢c]\s*per\s*day', section, re.IGNORECASE
        )
        if not fixed_match:
            fixed_match = re.search(
                r'([\d.]+)\s*cents?\s*per\s*day', section, re.IGNORECASE
            )
        if not fixed_match:
            self.logger.warning("Could not find Rate D fixed charge in PDF")
            return None
        fixed_cents = float(fixed_match.group(1))
        fixed_dollars = fixed_cents / 100.0

        # Energy rates: look for "X.XXX¢ per kilowatthour"
        energy_matches = re.findall(
            r'([\d.]+)\s*[¢c]\s*per\s*kilowatthour', section, re.IGNORECASE
        )
        if not energy_matches:
            energy_matches = re.findall(
                r'([\d.]+)\s*cents?\s*per\s*kilowatthour', section, re.IGNORECASE
            )
        if len(energy_matches) < 2:
            self.logger.warning(
                "Could not find two energy tiers for Rate D (found %d)",
                len(energy_matches),
            )
            return None

        tier1_cents = float(energy_matches[0])
        tier2_cents = float(energy_matches[1])
        tier1_rate = tier1_cents / 100.0
        tier2_rate = tier2_cents / 100.0

        return TariffRecord(
            utility_name="Hydro-Québec",
            province="QC",
            utility_type="electricity",
            tariff_name="Rate D — Domestic",
            tariff_code="D",
            customer_class="residential",
            rate_structure="tiered",
            effective_date=SEED_RATE_D["effective_date"],
            source_url=PDF_URL,
            confidence="high",
            notes=(
                "Hydro-Québec residential rate. Tier threshold is 40 kWh/day "
                "(~1,200 kWh/month in a 30-day period). "
                "Parsed from official electricity-rates PDF."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Daily Fixed Charge",
                    charge_value=round(fixed_dollars, 5),
                    charge_unit="$/day",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="First 40 kWh/day",
                    charge_value=round(tier1_rate, 5),
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=40.0,
                    tier_unit="kWh/day",
                    notes="Applies to first 40 kWh per day of the billing period",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Remaining consumption",
                    charge_value=round(tier2_rate, 5),
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=40.0,
                    tier_unit="kWh/day",
                    notes="Applies to all kWh beyond 40/day",
                ),
            ],
        )

    # ── Rate G parser ─────────────────────────────────────────

    def _parse_rate_g(self, pdf_text: str) -> Optional[TariffRecord]:
        """Parse Rate G (General/Small Commercial) from PDF text."""
        section = self._extract_section(pdf_text, "Rate G", "Rate M")
        if not section:
            self.logger.warning("Could not find Rate G section in PDF")
            return None

        # Fixed charge: "$XX.XXX per month" or "XX.XXX $/month"
        fixed_match = re.search(
            r'\$([\d.]+)\s*per\s*month', section, re.IGNORECASE
        )
        if not fixed_match:
            fixed_match = re.search(
                r'([\d.]+)\s*\$/\s*month', section, re.IGNORECASE
            )
        fixed_per_month = float(fixed_match.group(1)) if fixed_match else None

        # Demand charge: "$XX.XXX per kilowatt"
        demand_match = re.search(
            r'\$([\d.]+)\s*per\s*kilowatt', section, re.IGNORECASE
        )
        demand_charge = float(demand_match.group(1)) if demand_match else None

        # Energy rates: "XX.XXX¢ per kilowatthour"
        energy_matches = re.findall(
            r'([\d.]+)\s*[¢c]\s*per\s*kilowatthour', section, re.IGNORECASE
        )
        if not energy_matches:
            energy_matches = re.findall(
                r'([\d.]+)\s*cents?\s*per\s*kilowatthour', section, re.IGNORECASE
            )
        if len(energy_matches) < 2:
            self.logger.warning(
                "Could not find two energy tiers for Rate G (found %d)",
                len(energy_matches),
            )
            return None

        tier1_rate = float(energy_matches[0]) / 100.0
        tier2_rate = float(energy_matches[1]) / 100.0

        components = []

        if fixed_per_month is not None:
            components.append(RateComponent(
                component_type="fixed",
                component_name="Monthly Fixed Charge",
                charge_value=round(fixed_per_month, 3),
                charge_unit="$/month",
            ))

        components.append(RateComponent(
            component_type="energy",
            component_name="First 15,090 kWh",
            charge_value=round(tier1_rate, 5),
            charge_unit="$/kWh",
            tier_number=1,
            tier_threshold=15090,
            tier_unit="kWh",
        ))

        components.append(RateComponent(
            component_type="energy",
            component_name="Remaining kWh",
            charge_value=round(tier2_rate, 5),
            charge_unit="$/kWh",
            tier_number=2,
            tier_threshold=15090,
            tier_unit="kWh",
        ))

        if demand_charge is not None:
            components.append(RateComponent(
                component_type="demand",
                component_name="Demand Charge (above 50 kW)",
                charge_value=round(demand_charge, 3),
                charge_unit="$/kW",
                demand_threshold_kw=50,
                demand_unit="kW",
                notes="No demand charge for first 50 kW",
            ))

        return TariffRecord(
            utility_name="Hydro-Québec",
            province="QC",
            utility_type="electricity",
            tariff_name="Rate G — General",
            tariff_code="G",
            customer_class="commercial",
            sub_class="small general",
            rate_structure="mixed",
            effective_date=SEED_RATE_G["effective_date"],
            source_url=PDF_URL,
            confidence="high",
            eligibility=SEED_RATE_G["eligibility"],
            demand_max_kw=65,
            notes=(
                "Hydro-Québec small commercial rate — energy charge is tiered, "
                "plus demand charge above 50 kW. "
                "Parsed from official electricity-rates PDF."
            ),
            components=components,
        )

    # ── Rate M parser ─────────────────────────────────────────

    def _parse_rate_m(self, pdf_text: str) -> Optional[TariffRecord]:
        """Parse Rate M (Medium Power, 50-5000 kW) from PDF text."""
        section = self._extract_section(pdf_text, "Rate M", "Rate L")
        if not section:
            # Rate M might be near the end; try without end marker
            section = self._extract_section(pdf_text, "Rate M", "Rate LG")
            if not section:
                section = self._extract_section(pdf_text, "Rate M", "SECTION")
        if not section:
            self.logger.warning("Could not find Rate M section in PDF")
            return None

        # Demand charge: "$XX.XXX per kilowatt"
        demand_match = re.search(
            r'\$([\d.]+)\s*per\s*kilowatt', section, re.IGNORECASE
        )
        demand_charge = float(demand_match.group(1)) if demand_match else None

        # Energy rates: "X.XXX¢ per kilowatthour"
        energy_matches = re.findall(
            r'([\d.]+)\s*[¢c]\s*per\s*kilowatthour', section, re.IGNORECASE
        )
        if not energy_matches:
            energy_matches = re.findall(
                r'([\d.]+)\s*cents?\s*per\s*kilowatthour', section, re.IGNORECASE
            )
        if len(energy_matches) < 2:
            self.logger.warning(
                "Could not find two energy tiers for Rate M (found %d)",
                len(energy_matches),
            )
            return None

        tier1_rate = float(energy_matches[0]) / 100.0
        tier2_rate = float(energy_matches[1]) / 100.0

        components = []

        if demand_charge is not None:
            components.append(RateComponent(
                component_type="demand",
                component_name="Demand Charge",
                charge_value=round(demand_charge, 3),
                charge_unit="$/kW",
                notes="Per kW of billing demand",
            ))

        components.append(RateComponent(
            component_type="energy",
            component_name="First 210,000 kWh",
            charge_value=round(tier1_rate, 5),
            charge_unit="$/kWh",
            tier_number=1,
            tier_threshold=210000,
            tier_unit="kWh",
        ))

        components.append(RateComponent(
            component_type="energy",
            component_name="Remaining kWh",
            charge_value=round(tier2_rate, 5),
            charge_unit="$/kWh",
            tier_number=2,
            tier_threshold=210000,
            tier_unit="kWh",
        ))

        return TariffRecord(
            utility_name="Hydro-Québec",
            province="QC",
            utility_type="electricity",
            tariff_name="Rate M — Medium Power",
            tariff_code="M",
            customer_class="commercial",
            sub_class="medium power",
            rate_structure="mixed",
            effective_date=SEED_RATE_M["effective_date"],
            source_url=PDF_URL,
            confidence="high",
            eligibility=SEED_RATE_M["eligibility"],
            demand_min_kw=50,
            demand_max_kw=5000,
            notes=(
                "Hydro-Québec medium-power rate for contract power 50–5,000 kW. "
                "Parsed from official electricity-rates PDF."
            ),
            components=components,
        )

    # ── Seed data (fallback) ──────────────────────────────────

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
            confidence="high",
            notes=(
                "Hydro-Québec residential rate. Tier threshold is 40 kWh/day "
                "(~1,200 kWh/month in a 30-day period). "
                "Verified from official electricity-rates PDF (2026-04-01)."
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
            confidence="high",
            eligibility=SEED_RATE_G["eligibility"],
            demand_max_kw=65,
            notes=(
                "Hydro-Québec small commercial rate — energy charge is tiered, "
                "plus demand charge above 50 kW. "
                "Verified from official electricity-rates PDF (2026-04-01)."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Fixed Charge",
                    charge_value=SEED_RATE_G["fixed_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="First 15,090 kWh",
                    charge_value=SEED_RATE_G["first_15090kwh"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=15090,
                    tier_unit="kWh",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Remaining kWh",
                    charge_value=SEED_RATE_G["remaining"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=15090,
                    tier_unit="kWh",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge (above 50 kW)",
                    charge_value=SEED_RATE_G["demand_charge_above_50kw"],
                    charge_unit="$/kW",
                    demand_threshold_kw=50,
                    demand_unit="kW",
                    notes="No demand charge for first 50 kW",
                ),
            ],
        ))

        # ── Rate M: Medium Power ──────────────────────────────
        records.append(TariffRecord(
            utility_name="Hydro-Québec",
            province="QC",
            utility_type="electricity",
            tariff_name="Rate M — Medium Power",
            tariff_code="M",
            customer_class="commercial",
            sub_class="medium power",
            rate_structure="mixed",
            effective_date=SEED_RATE_M["effective_date"],
            source_url=SEED_RATE_M["source_url"],
            confidence="high",
            eligibility=SEED_RATE_M["eligibility"],
            demand_min_kw=50,
            demand_max_kw=5000,
            notes=(
                "Hydro-Québec medium-power rate for contract power 50–5,000 kW. "
                "Verified from official electricity-rates PDF (2026-04-01)."
            ),
            components=[
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_RATE_M["demand_charge"],
                    charge_unit="$/kW",
                    notes="Per kW of billing demand",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="First 210,000 kWh",
                    charge_value=SEED_RATE_M["first_210000kwh"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=210000,
                    tier_unit="kWh",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Remaining kWh",
                    charge_value=SEED_RATE_M["remaining"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=210000,
                    tier_unit="kWh",
                ),
            ],
        ))

        return records
