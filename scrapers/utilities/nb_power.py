"""
nb_power.py — Scraper for NB Power electricity rates (New Brunswick).

NB Power (New Brunswick Power Corporation) is the primary electric utility
in New Brunswick, a provincial Crown corporation. Residential rates use a
flat structure with a single energy charge for all kWh consumed.

Official sources:
  Residential: https://www.nbpower.com/en/products-services/residential/rates
  Business:    https://www.nbpower.com/en/products-services/business/rates

Regulated by: New Brunswick Energy and Utilities Board (EUB NB)
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    extract_tables,
    clean_currency,
    detect_js_rendered,
)
from scrapers.utils.change_detection import (
    compare_to_seed,
    log_change_alerts,
    has_critical_alerts,
)

logger = logging.getLogger(__name__)

# ── URLs ──────────────────────────────────────────────────────────
RESIDENTIAL_URL = "https://www.nbpower.com/en/products-services/residential/rates"
BUSINESS_URL = "https://www.nbpower.com/en/products-services/business/rates"

# ── Seed / fallback data ─────────────────────────────────────────
# Known rate values — used as seed/fallback data.

SEED_RESIDENTIAL = {
    "effective_date": "2026-04-14",
    "source_url": RESIDENTIAL_URL,
    "basic_charge_per_month": 30.87,   # $/month (urban)
    "energy_rate": 0.1584,             # $/kWh — single flat rate, all kWh
}

SEED_GS1 = {
    "effective_date": "2026-04-14",
    "source_url": BUSINESS_URL,
    "basic_charge_per_month": 30.87,   # $/month
    "demand_charge": 7.52,             # $/kW
    "tier1_threshold_kwh": 15000,      # first 15,000 kWh
    "tier1_rate": 0.1584,              # $/kWh
    "tier2_rate": 0.1050,              # $/kWh — balance
}

SEED_SMALL_INDUSTRIAL = {
    "effective_date": "2026-04-14",
    "source_url": BUSINESS_URL,
    "basic_charge_per_month": 22.84,   # $/month
    "demand_charge": 7.52,             # $/kW
    "energy_rate": 0.0772,             # $/kWh
}


def _extract_total_from_merged_cell(cell_text: str) -> Optional[float]:
    """
    Extract the 'Total Charge' value from a merged cell that contains
    Base Rate + Variance + Total concatenated as one string.

    Example input:
        '17.76¢ Base Rate+ 0.45¢ Variance Account Charge18.21¢ Total Charge'
    Returns: 0.1821

    Also handles simple values like '$30.87' or '$9.39 /kW'.
    """
    # First try: look for "Total Charge" preceded by a number
    match = re.search(r"(\d+\.?\d*)\s*[¢c]\s*Total", cell_text, re.IGNORECASE)
    if match:
        return float(match.group(1)) / 100.0

    # Second try: look for dollar amount with "Total"
    match = re.search(r"\$\s*(\d+\.?\d*)\s*(?:Total|/)", cell_text, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Third try: simple dollar amount (e.g. '$30.87', '$9.39 /kW')
    return clean_currency(cell_text)


class NBPowerScraper(BaseScraper):
    """Scrape NB Power electricity rates."""

    def __init__(self):
        super().__init__(utility_name="NB Power", province="NB")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live NB Power rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d NB Power tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for NB Power")
            records.extend(self._seed_data())

        return records

    # ── Live scraping ────────────────────────────────────────────

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live NB Power website."""
        try:
            res_html = self.fetch_page(RESIDENTIAL_URL)
            biz_html = self.fetch_page(BUSINESS_URL)

            if detect_js_rendered(res_html):
                self.logger.warning("Residential page appears JS-rendered — skipping live parse")
                return None

            if detect_js_rendered(biz_html):
                self.logger.warning("Business page appears JS-rendered — skipping live parse")
                return None

            residential = self._parse_residential(res_html)
            if residential is None:
                self.logger.warning("Could not parse residential rates from live page")
                return None

            gs1 = self._parse_gs1(biz_html)
            small_ind = self._parse_small_industrial(biz_html)

            live_records = [residential]
            if gs1:
                live_records.append(gs1)
            if small_ind:
                live_records.append(small_ind)

            # Validate live data against seed using change detection
            alerts = compare_to_seed(live_records, self._seed_data())
            log_change_alerts(alerts)

            if has_critical_alerts(alerts):
                self.logger.error(
                    "Critical deviation in live data vs seed — falling back to seed"
                )
                return None

            return live_records

        except Exception as e:
            self.logger.warning("Could not fetch NB Power pages: %s", e)
            return None

    # ── Residential parser ───────────────────────────────────────

    def _parse_residential(self, html: str) -> Optional[TariffRecord]:
        """
        Parse residential rate values from the NB Power residential rates page.

        The residential page has a rate table (Table 0) structured as:
          Row 0: ['Base Rate', 'Variance Account Charge', 'Total Charge']
          Row 1: ['Urban', '', '', '$30.87']
          Row 2: ['Rural/Seasonal', '', '', '$33.82']
          Row 3: ['Energy Charge all kWh: ¢/kWh', '15.39¢', '+ 0.45¢', '15.84¢']

        We extract the Urban service charge and the flat energy rate from
        the Total column (last cell).
        """
        tables = extract_tables(html)

        service_charge = None
        energy_rate = None

        # The rate table is the first table on the page with the
        # 3-column header (Base Rate / Variance / Total).
        for table in tables:
            if not table:
                continue

            for row in table:
                if len(row) < 2:
                    continue

                label = row[0].lower()
                total_cell = row[-1]

                # Service charge: the "Urban" row holds the standard
                # residential service charge in the last column.
                if "urban" in label and "rural" not in label and service_charge is None:
                    val = clean_currency(total_cell)
                    if val is not None and 1.0 < val < 200.0:
                        service_charge = val

                # Energy rate: look for "energy" and "kwh" in the label.
                # The value in the last column is the total (in ¢/kWh).
                if "energy" in label and "kwh" in label and energy_rate is None:
                    val = clean_currency(total_cell)
                    if val is not None and 0.01 < val < 1.0:
                        energy_rate = val

            # Stop after finding both values (avoid later tables like
            # "Other Services" which contain unrelated charges).
            if service_charge is not None and energy_rate is not None:
                break

        if service_charge is None or energy_rate is None:
            self.logger.warning(
                "Incomplete residential parse: service_charge=%s, energy_rate=%s",
                service_charge, energy_rate,
            )
            return None

        # Sanity check: rates should be in reasonable ranges
        if not (1.0 < service_charge < 200.0):
            self.logger.warning("Service charge out of range: %s", service_charge)
            return None
        if not (0.01 < energy_rate < 1.0):
            self.logger.warning("Energy rate out of range: %s", energy_rate)
            return None

        return TariffRecord(
            utility_name="NB Power",
            province="NB",
            utility_type="electricity",
            tariff_name="Residential Service (Rate D)",
            tariff_code="D",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=RESIDENTIAL_URL,
            confidence="high",
            notes="NB Power residential flat rate — live parsed",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=service_charge,
                    charge_unit="$/month",
                    notes="Monthly service charge (urban)",
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

    # ── Business parsers ─────────────────────────────────────────

    def _get_business_sections(
        self, html: str,
    ) -> dict[str, list[list[str]]]:
        """
        Parse the business rates page into named sections.

        NB Power's business page uses ONE large table with section headers
        as single-cell rows (e.g. ['General Service 1 (standard)']).
        Rate rows are 2-cell: [label, value].

        Returns a dict mapping section name (lowercased) to a list of
        [label, value] row pairs belonging to that section.
        """
        tables = extract_tables(html)
        if not tables:
            return {}

        # The rate data is in the first (largest) table.
        main_table = tables[0]

        sections: dict[str, list[list[str]]] = {}
        current_section = ""

        for row in main_table:
            if not row:
                continue

            # Section header: single non-empty cell, or first cell with
            # the rest empty, that looks like a heading (contains a known
            # rate class keyword).
            first_cell = row[0].strip()
            first_lower = first_cell.lower()

            # Detect section headers — they are single-cell rows or rows
            # where only the first cell is meaningful and it matches a
            # known section name.
            is_header = False
            if len(row) == 1 and first_cell:
                is_header = True
            elif len(row) == 2 and not row[1].strip():
                is_header = True

            if is_header:
                # Check if it matches a known rate class
                for keyword in (
                    "general service",
                    "recreational lighting",
                    "small industrial",
                    "large industrial",
                ):
                    if keyword in first_lower:
                        current_section = keyword
                        sections.setdefault(current_section, [])
                        break
                continue

            # Data row: append to current section
            if current_section and len(row) >= 2:
                sections.setdefault(current_section, [])
                sections[current_section].append(row)

        return sections

    def _parse_gs1(self, html: str) -> Optional[TariffRecord]:
        """
        Parse General Service 1 (GS1) rates from the business rates page.

        Expected rows in the GS1 section:
          ['Service Charge:', '$30.87']
          ['First 20 kilowatts of demand', 'No charge']
          ['Additional kilowatts of demand:', '$14.20/kW']
          ['First 5000 kilowatt hours', '17.76¢ Base Rate+ 0.45¢ ...18.21¢ Total Charge']
          ['Balance kilowatt-hours', '12.59¢ Base Rate+ 0.45¢ ...13.04¢ Total Charge']
        """
        sections = self._get_business_sections(html)
        gs1_rows = sections.get("general service", [])

        if not gs1_rows:
            self.logger.warning("No General Service section found on business page")
            return None

        service_charge = None
        demand_charge = None
        energy_tier1 = None
        energy_tier2 = None
        energy_tier1_threshold = None

        for row in gs1_rows:
            label = row[0].lower()
            value_cell = row[-1]

            # Service charge
            if "service" in label and "charge" in label:
                val = clean_currency(value_cell)
                if val is not None and 1.0 < val < 200.0:
                    service_charge = val

            # Demand charge — "additional kilowatts of demand"
            elif "additional" in label and "kilowatt" in label and "hour" not in label:
                val = _extract_total_from_merged_cell(value_cell)
                if val is not None and 0.5 < val < 100.0:
                    demand_charge = val

            # Energy tier 1 — "first NNNN kilowatt hours"
            elif "first" in label and ("kilowatt hour" in label or "kilowatt-hour" in label or "kwh" in label):
                val = _extract_total_from_merged_cell(value_cell)
                if val is not None and 0.01 < val < 1.0:
                    energy_tier1 = val
                    # Extract the threshold from the label
                    threshold_match = re.search(r"(\d[\d,]*)\s*(?:kilowatt|kwh)", label)
                    if threshold_match:
                        energy_tier1_threshold = float(
                            threshold_match.group(1).replace(",", "")
                        )

            # Energy tier 2 — "balance kilowatt-hours"
            elif ("balance" in label or "remaining" in label) and \
                    ("kilowatt" in label or "kwh" in label):
                val = _extract_total_from_merged_cell(value_cell)
                if val is not None and 0.01 < val < 1.0:
                    energy_tier2 = val

        if service_charge is None or energy_tier1 is None:
            self.logger.warning(
                "Incomplete GS1 parse: service=%s, demand=%s, tier1=%s, tier2=%s",
                service_charge, demand_charge, energy_tier1, energy_tier2,
            )
            return None

        components = [
            RateComponent(
                component_type="fixed",
                component_name="Basic Charge",
                charge_value=service_charge,
                charge_unit="$/month",
                notes="Monthly service charge",
            ),
        ]

        if demand_charge is not None:
            components.append(RateComponent(
                component_type="demand",
                component_name="Demand Charge",
                charge_value=demand_charge,
                charge_unit="$/kW",
                demand_unit="kW",
                notes="Applied to billing demand (kW); first 20 kW at no charge",
            ))

        components.append(RateComponent(
            component_type="energy",
            component_name="Tier 1 Energy Charge",
            charge_value=energy_tier1,
            charge_unit="$/kWh",
            tier_number=1,
            tier_threshold=energy_tier1_threshold,
            tier_unit="kWh",
            notes=f"Applies to first {int(energy_tier1_threshold or 0):,} kWh" if energy_tier1_threshold else "First block energy charge",
        ))

        if energy_tier2 is not None:
            components.append(RateComponent(
                component_type="energy",
                component_name="Tier 2 Energy Charge",
                charge_value=energy_tier2,
                charge_unit="$/kWh",
                tier_number=2,
                tier_threshold=energy_tier1_threshold,
                tier_unit="kWh",
                notes="Applies to all kWh above the Tier 1 threshold",
            ))

        return TariffRecord(
            utility_name="NB Power",
            province="NB",
            utility_type="electricity",
            tariff_name="General Service I",
            tariff_code="GS1",
            customer_class="commercial",
            sub_class="general service",
            rate_structure="tiered",
            effective_date=SEED_GS1["effective_date"],
            source_url=BUSINESS_URL,
            confidence="high",
            notes="NB Power General Service I rate — live parsed",
            components=components,
        )

    def _parse_small_industrial(self, html: str) -> Optional[TariffRecord]:
        """
        Parse Small Industrial rates from the business rates page.

        Expected rows in the Small Industrial section:
          ['Demand Charge', '$9.39 /kW']
          ['First 100 kWh per kilowatt', '18.19¢ Base Rate+ 0.44¢ ...18.63¢ Total Charge']
          ['Balance kilowatt-hours', '8.59¢ Base Rate+ 0.44¢ ...9.03¢ Total Charge']
        """
        sections = self._get_business_sections(html)
        si_rows = sections.get("small industrial", [])

        if not si_rows:
            self.logger.warning("No Small Industrial section found on business page")
            return None

        service_charge = None
        demand_charge = None
        energy_rate = None
        energy_tier1 = None
        energy_tier2 = None

        for row in si_rows:
            label = row[0].lower()
            value_cell = row[-1]

            # Service charge
            if "service" in label and "charge" in label:
                val = clean_currency(value_cell)
                if val is not None and 1.0 < val < 200.0:
                    service_charge = val

            # Demand charge
            elif "demand" in label and "charge" in label:
                val = _extract_total_from_merged_cell(value_cell)
                if val is not None and 0.5 < val < 100.0:
                    demand_charge = val

            # Energy — "first" block
            elif "first" in label and ("kwh" in label or "kilowatt" in label):
                val = _extract_total_from_merged_cell(value_cell)
                if val is not None and 0.01 < val < 1.0:
                    energy_tier1 = val

            # Energy — "balance" or single energy line
            elif ("balance" in label or "remaining" in label) and \
                    ("kilowatt" in label or "kwh" in label):
                val = _extract_total_from_merged_cell(value_cell)
                if val is not None and 0.01 < val < 1.0:
                    energy_tier2 = val

            # Single energy charge (non-tiered fallback)
            elif "energy" in label and ("kwh" in label or "charge" in label):
                val = _extract_total_from_merged_cell(value_cell)
                if val is not None and 0.01 < val < 1.0:
                    energy_rate = val

        if demand_charge is None:
            self.logger.warning("Incomplete Small Industrial parse: no demand charge found")
            return None

        # Build components
        components = []

        if service_charge is not None:
            components.append(RateComponent(
                component_type="fixed",
                component_name="Basic Charge",
                charge_value=service_charge,
                charge_unit="$/month",
                notes="Monthly service charge",
            ))

        components.append(RateComponent(
            component_type="demand",
            component_name="Demand Charge",
            charge_value=demand_charge,
            charge_unit="$/kW",
            demand_unit="kW",
            notes="Applied to billing demand (kW)",
        ))

        # Use tiered energy if found, otherwise single energy rate
        if energy_tier1 is not None:
            components.append(RateComponent(
                component_type="energy",
                component_name="Tier 1 Energy Charge",
                charge_value=energy_tier1,
                charge_unit="$/kWh",
                tier_number=1,
                notes="First block energy charge",
            ))
            if energy_tier2 is not None:
                components.append(RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge",
                    charge_value=energy_tier2,
                    charge_unit="$/kWh",
                    tier_number=2,
                    notes="Balance energy charge",
                ))
        elif energy_rate is not None:
            components.append(RateComponent(
                component_type="energy",
                component_name="Energy Charge",
                charge_value=energy_rate,
                charge_unit="$/kWh",
                notes="Energy charge per kWh consumed",
            ))

        return TariffRecord(
            utility_name="NB Power",
            province="NB",
            utility_type="electricity",
            tariff_name="Small Industrial Service",
            customer_class="commercial",
            sub_class="small industrial",
            rate_structure="demand",
            demand_max_kw=750,
            effective_date=SEED_SMALL_INDUSTRIAL["effective_date"],
            source_url=BUSINESS_URL,
            confidence="high",
            eligibility="Small industrial customers with loads up to 750 kW",
            notes="NB Power small industrial rate — live parsed",
            components=components,
        )

    # ── Seed / fallback data ─────────────────────────────────────

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        return [
            self._seed_data_residential(),
            self._seed_data_gs1(),
            self._seed_data_small_industrial(),
        ]

    def _seed_data_residential(self) -> TariffRecord:
        """Return seed data for the residential tariff."""
        return TariffRecord(
            utility_name="NB Power",
            province="NB",
            utility_type="electricity",
            tariff_name="Residential Service (Rate D)",
            tariff_code="D",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes="NB Power residential flat electricity rate",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                    notes="Monthly service charge (urban)",
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

    def _seed_data_gs1(self) -> TariffRecord:
        """Return seed data for the General Service I tariff."""
        return TariffRecord(
            utility_name="NB Power",
            province="NB",
            utility_type="electricity",
            tariff_name="General Service I",
            tariff_code="GS1",
            customer_class="commercial",
            sub_class="general service",
            rate_structure="tiered",
            effective_date=SEED_GS1["effective_date"],
            source_url=SEED_GS1["source_url"],
            confidence="high",
            notes=(
                "NB Power General Service I rate. "
                "Tiered energy with demand charge."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_GS1["basic_charge_per_month"],
                    charge_unit="$/month",
                    notes="Monthly service charge",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_GS1["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to billing demand (kW)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 1 Energy Charge",
                    charge_value=SEED_GS1["tier1_rate"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_GS1["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="Applies to first 15,000 kWh",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge",
                    charge_value=SEED_GS1["tier2_rate"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_GS1["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="Applies to all kWh above 15,000",
                ),
            ],
        )

    def _seed_data_small_industrial(self) -> TariffRecord:
        """Return seed data for the small industrial tariff."""
        return TariffRecord(
            utility_name="NB Power",
            province="NB",
            utility_type="electricity",
            tariff_name="Small Industrial Service",
            customer_class="commercial",
            sub_class="small industrial",
            rate_structure="demand",
            effective_date=SEED_SMALL_INDUSTRIAL["effective_date"],
            source_url=SEED_SMALL_INDUSTRIAL["source_url"],
            confidence="high",
            eligibility="Small industrial customers with demand metering",
            notes="NB Power small industrial rate with demand and energy charges",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_SMALL_INDUSTRIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_SMALL_INDUSTRIAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to billing demand (kW)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_SMALL_INDUSTRIAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Energy charge per kWh consumed",
                ),
            ],
        )
