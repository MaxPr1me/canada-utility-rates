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
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

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
    "demand_charge": 14.20,            # $/kW (first 20 kW no charge)
    "tier1_threshold_kwh": 5000,       # first 5,000 kWh
    "tier1_rate": 0.1821,              # $/kWh — 18.21¢ total (base + variance)
    "tier2_rate": 0.1304,              # $/kWh — balance, 13.04¢ total
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


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _money(text: str) -> Optional[float]:
    m = re.search(r"\$\s*(\d+(?:,\d{3})*(?:\.\d+)?)", text)
    return float(m.group(1).replace(",", "")) if m else None


def _cents_total(text: str) -> Optional[float]:
    """Total ¢/kWh as $/kWh, only if base + variance reconciles to the printed total."""
    base = re.search(r"(\d+(?:\.\d+)?)\s*¢\s*Base Rate", text)
    var = re.search(r"\+\s*(\d+(?:\.\d+)?)\s*¢\s*Variance", text)
    total = re.search(r"(\d+(?:\.\d+)?)\s*¢\s*Total", text)
    if not (base and var and total):
        return None
    if abs(float(base.group(1)) + float(var.group(1)) - float(total.group(1))) > 0.005:
        return None
    return round(float(total.group(1)) / 100.0, 6)


def _cents_triplet(base: str, var: str, total: str) -> Optional[float]:
    vals = []
    for cell in (base, var, total):
        m = re.search(r"(\d+(?:\.\d+)?)\s*¢", cell)
        if not m:
            return None
        vals.append(float(m.group(1)))
    if abs(vals[0] + vals[1] - vals[2]) > 0.005:
        return None
    return round(vals[2] / 100.0, 6)


def _component(ctype, name, value, unit, eff, url, detail, **kw) -> RateComponent:
    return RateComponent(
        component_type=ctype, component_name=name, charge_value=value, charge_unit=unit,
        effective_date=eff, source_url=url, source_detail=detail, **kw,
    )


def _page_effective_date(soup, heading: str) -> Optional[str]:
    for h in soup.find_all(["h1", "h2"]):
        m = re.search(
            heading + r"\s*\(effective\s+([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\)",
            _clean(h.get_text(" ")),
        )
        if m:
            try:
                return datetime.strptime(" ".join(m.groups()), "%B %d %Y").date().isoformat()
            except ValueError:
                return None
    return None


def _table_after(soup, heading: str):
    """Table immediately following a bold '<heading>:' paragraph."""
    for strong in soup.find_all("strong"):
        if _clean(strong.get_text(" ")).rstrip(":").strip().lower() == heading.lower():
            para = strong.find_parent("p")
            nxt = para.find_next_sibling() if para else None
            return nxt if nxt is not None and nxt.name == "table" else None
    return None


def _section_rows(soup, heading: str) -> list[tuple[str, str]]:
    """[label, value] rows following a section header row until the next header/blank row."""
    for cell in soup.find_all(["td", "th"]):
        if _clean(cell.get_text(" ")) != heading:
            continue
        rows = []
        for tr in cell.find_parent("tr").find_next_siblings("tr"):
            cells = [_clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
            if len(cells) != 2 or not all(cells):
                break
            rows.append((cells[0], cells[1]))
        return rows
    return []


class NBPowerScraper(BaseScraper):
    """Scrape NB Power electricity rates."""

    def __init__(self):
        super().__init__(utility_name="NB Power", province="NB")
        self._extra_live: list[TariffRecord] = []

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
            records.extend(self.mark_fallback(self._seed_data()))

        # Additional classes are parsed independently; failures are omitted, never seeded
        records.extend(self._extra_live)
        return records

    # ── Live scraping ────────────────────────────────────────────

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live NB Power website."""
        try:
            self._extra_live = []
            res_html = self.fetch_page(RESIDENTIAL_URL)
            biz_html = self.fetch_page(BUSINESS_URL)
            self._extra_live = self._parse_additional(res_html, biz_html)

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

            res_soup = BeautifulSoup(res_html, "html.parser")
            biz_soup = BeautifulSoup(biz_html, "html.parser")
            self._stamp_sources(
                residential, _page_effective_date(res_soup, "Residential Rates"),
                RESIDENTIAL_URL, "Residential Rates table",
                {"Basic Charge": "Urban row, Total Charge column",
                 "Energy Charge": "Energy Charge all kWh row, Total Charge column"},
            )
            live_records = [residential]
            biz_date = _page_effective_date(biz_soup, "Business Rates")
            if gs1 and biz_date:
                self._stamp_sources(
                    gs1, biz_date, BUSINESS_URL, "General Service 1 (standard) section",
                    {"Basic Charge": "Service Charge row",
                     "Demand Charge": "Additional kilowatts of demand row",
                     "Tier 1 Energy Charge": "First kilowatt hours row, Total Charge",
                     "Tier 2 Energy Charge": "Balance kilowatt-hours row, Total Charge"},
                )
                live_records.append(gs1)
            if small_ind and biz_date:
                self._stamp_sources(
                    small_ind, biz_date, BUSINESS_URL, "Small Industrial section",
                    {"Basic Charge": "Service Charge row",
                     "Demand Charge": "Demand Charge row",
                     "Tier 1 Energy Charge": "First kWh per kilowatt row, Total Charge",
                     "Tier 2 Energy Charge": "Balance kilowatt-hours row, Total Charge",
                     "Energy Charge": "Energy charge row"},
                )
                live_records.append(small_ind)
            large_ind = self._parse_large_industrial(biz_soup, biz_date)
            if large_ind:
                live_records.append(large_ind)

            # Validate live data against seed using change detection
            alerts = compare_to_seed(live_records, self._seed_data())
            log_change_alerts(alerts)

            if has_critical_alerts(alerts):
                self.logger.error(
                    "Critical deviation in live data vs seed — falling back to seed"
                )
                return None

            live_records = self.mark_live_parsed(live_records)

            # Preserve any classes we couldn't parse live as labelled seed estimates
            live_names = {r.tariff_name for r in live_records}
            seed_only = [r for r in self._seed_data() if r.tariff_name not in live_names]
            if seed_only:
                live_records = live_records + self.mark_fallback(seed_only)

            return live_records

        except Exception as e:
            self.logger.warning("Could not fetch NB Power pages: %s", e)
            return None

    @staticmethod
    def _stamp_sources(rec: TariffRecord, eff: Optional[str], url: str, table: str,
                       details: dict[str, str]) -> None:
        if eff:
            rec.effective_date = eff
        rec.source_url = url
        for c in rec.components:
            c.effective_date = eff or rec.effective_date
            c.source_url = url
            c.source_detail = f"{table}: {details.get(c.component_name, c.component_name)}"

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
        threshold = None
        soup = BeautifulSoup(html, "html.parser")
        heading = next((cell for cell in soup.find_all("th")
                        if _clean(cell.get_text(" ")) == "Small Industrial Service"), None)
        eligibility = (heading is not None and
                       _clean(heading.find_parent("tr").find_next_sibling("tr").get_text(" "))
                       == "(loads up to 750kilowatts)")

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
                match = re.fullmatch(r"\$(\d+\.\d{2})\s*/kW", value_cell)
                if match:
                    demand_charge = float(match.group(1))

            # Energy — "first" block
            elif "first" in label and ("kwh" in label or "kilowatt" in label):
                threshold = re.fullmatch(r"first\s+(\d+)\s+kwh per kilowatt", label)
                val = _cents_total(value_cell)
                if val is not None and 0.01 < val < 1.0:
                    energy_tier1 = val

            # Energy — "balance" or single energy line
            elif ("balance" in label or "remaining" in label) and \
                    ("kilowatt" in label or "kwh" in label):
                val = _cents_total(value_cell)
                if val is not None and 0.01 < val < 1.0:
                    energy_tier2 = val

            # Single energy charge (non-tiered fallback)
            elif "energy" in label and ("kwh" in label or "charge" in label):
                val = _extract_total_from_merged_cell(value_cell)
                if val is not None and 0.01 < val < 1.0:
                    energy_rate = val

        if (demand_charge is None or energy_tier1 is None or energy_tier2 is None
            or threshold is None or not eligibility):
            self.logger.warning("Incomplete Small Industrial parse: missing demand or energy tier")
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
                tier_threshold=float(threshold.group(1)),
                tier_unit="kWh per kilowatt",
                notes="First 100 kWh per kilowatt",
            ))
            if energy_tier2 is not None:
                components.append(RateComponent(
                    component_type="energy",
                    component_name="Tier 2 Energy Charge",
                    charge_value=energy_tier2,
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=float(threshold.group(1)),
                    tier_unit="kWh per kilowatt",
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

    def _parse_large_industrial(self, soup, eff: Optional[str]) -> Optional[TariffRecord]:
        if not eff:
            return None
        heading = next((cell for cell in soup.find_all("th")
                        if _clean(cell.get_text(" ")) == "Large Industrial Service"), None)
        if heading is None:
            return None
        rows = []
        for row in heading.find_parent("tr").find_next_siblings("tr"):
            if row.find("th"):
                break
            rows.append(row)
        if len(rows) != 5:
            return None
        eligibility = _clean(rows[0].get_text(" "))
        billing = rows[1]
        clauses = [_clean(item.get_text(" ")) for item in billing.find_all("li")]
        if (eligibility != "(minimum contracted demand of 750 kilowatts)"
                or not _clean(billing.get_text(" ")).startswith("Billing Demand The greatest of:")
                or len(clauses) != 5
                or not all(term in clause for term, clause in zip(
                    ("monthly maximum kW", "90% of the maximum kVA",
                     "non-curtailable", "current calendar year excluding April through November",
                     "previous calendar year excluding April through November"), clauses))):
            return None
        demand_cells = [_clean(cell.get_text(" ")) for cell in rows[2].find_all("td")]
        energy_cells = [_clean(cell.get_text(" ")) for cell in rows[3].find_all("td")]
        discount = _clean(rows[4].get_text(" "))
        if (len(demand_cells) != 2 or demand_cells[0] != "Demand Charge"
                or len(energy_cells) != 2 or energy_cells[0] != "Energy Charge"
                or not discount.startswith("Declining Discount Firm Rate New facilities")
                or "additional firm load" not in discount):
            return None
        match = re.fullmatch(r"\$(\d+\.\d{2}) per kW of the billing demand per month", demand_cells[1])
        energy = _cents_total(energy_cells[1])
        if match is None or energy is None:
            return None
        detail = "Business Rates page, Large Industrial Service section (Billing Demand and charge rows)"
        return TariffRecord(
            utility_name="NB Power", province="NB", utility_type="electricity",
            tariff_name="Large Industrial Service",
            customer_class="industrial", sub_class="large industrial",
            rate_structure="demand", demand_min_kw=750,
            effective_date=eff, source_url=BUSINESS_URL, source_page=detail,
            confidence="high", eligibility="Minimum contracted demand of 750 kW",
            notes=("Billing demand is the greatest of: " + "; ".join(clauses)
                   + ". Declining Discount Firm Rate applies only to eligible additional firm load; no universal discount price."),
            components=[
                _component("demand", "Demand Charge", float(match.group(1)),
                           "$/kW/month", eff, BUSINESS_URL, detail, demand_unit="kW"),
                _component("energy", "Energy Charge", energy, "$/kWh", eff,
                           BUSINESS_URL, detail),
            ],
        )

    # ── Additional building classes and recurring fees ──────────

    def _parse_additional(self, res_html: str, biz_html: str) -> list[TariffRecord]:
        """Parse each extra class independently; a failed class is omitted."""
        res = BeautifulSoup(res_html, "html.parser")
        biz = BeautifulSoup(biz_html, "html.parser")
        res_date = _page_effective_date(res, "Residential Rates")
        biz_date = _page_effective_date(biz, "Business Rates")

        jobs = [
            ("residential rural/seasonal", self._parse_rural_residential, (res, res_date)),
            ("residential water heater", self._parse_water_heater,
             (res, res_date, RESIDENTIAL_URL, "Residential", "residential")),
            ("residential SureConnect", self._parse_sureconnect, (res, res_date)),
            ("business water heater", self._parse_water_heater,
             (biz, biz_date, BUSINESS_URL, "Business", "commercial")),
            ("recreational lighting", self._parse_recreational_lighting, (biz, biz_date)),
            ("public fast charging", self._parse_fast_charging, (biz, biz_date)),
        ]
        records: list[TariffRecord] = []
        for label, fn, args in jobs:
            try:
                rec = fn(*args)
            except Exception as exc:  # fail closed per class
                self.logger.warning("NB Power %s parse failed: %s", label, exc)
                rec = None
            if rec is None:
                self.logger.warning("NB Power %s not parsed; omitted", label)
                continue
            records.append(rec)
        return self.mark_live_parsed(records) if records else []

    def _parse_rural_residential(self, soup, eff: Optional[str]) -> Optional[TariffRecord]:
        if not eff or "per billing period" not in soup.get_text(" ").lower():
            return None
        rural = energy = None
        for tr in soup.find_all("tr"):
            cells = [_clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
            if len(cells) < 4:
                continue
            if cells[0] == "Rural/Seasonal" and rural is None:
                rural = _money(cells[-1])
            elif cells[0].startswith("Energy Charge all kWh") and energy is None:
                energy = _cents_triplet(cells[1], cells[2], cells[3])
        if rural is None or energy is None:
            return None
        detail = "Residential Rates page, Service Charge table (Rural/Seasonal) and Energy Charge row"
        return TariffRecord(
            utility_name="NB Power", province="NB", utility_type="electricity",
            tariff_name="Residential Service (Rate D) - Rural/Seasonal",
            tariff_code="D-RURAL", customer_class="residential", sub_class="rural/seasonal",
            rate_structure="flat", effective_date=eff, source_url=RESIDENTIAL_URL,
            source_page=detail, confidence="high",
            notes="Rate D rural/seasonal service charge; same flat energy charge as urban",
            components=[
                _component("fixed", "Basic Charge", rural, "$/billing period", eff,
                           RESIDENTIAL_URL, detail, notes="Rural/Seasonal service charge per billing period"),
                _component("energy", "Energy Charge", energy, "$/kWh", eff,
                           RESIDENTIAL_URL, detail, notes="Flat rate for all kWh per billing period"),
            ],
        )

    def _parse_water_heater(
        self, soup, eff: Optional[str], url: str, audience: str, customer_class: str,
    ) -> Optional[TariffRecord]:
        table = _table_after(soup, "Water Heater Rental")
        if table is None or not eff or "$/month" not in _clean(table.get_text(" ")):
            return None
        components = []
        detail = f"{audience} Rates page, Water Heater Rental table"
        for tr in table.find_all("tr"):
            cells = [_clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
            if len(cells) == 1:
                continue  # header row
            m = re.fullmatch(r"(\d+)\s*Gallons?\s*/\s*(\d+)\s*litres?(?:\s*\((.+)\))?", cells[0], re.I)
            price = _money(cells[-1]) if len(cells) == 2 else None
            if not m or price is None:
                return None
            name = f"Water Heater Rental {m.group(1)} gal/{m.group(2)} L"
            if m.group(3):
                name += f" ({m.group(3)})"
            components.append(_component("fixed", name, price, "$/month", eff, url, detail,
                                         notes="Monthly equipment rental"))
        if not components:
            return None
        return TariffRecord(
            utility_name="NB Power", province="NB", utility_type="electricity",
            tariff_name=f"Water Heater Rental ({audience})",
            tariff_code="WH-" + audience[:3].upper(), customer_class=customer_class,
            sub_class="water heater rental", rate_structure="flat", effective_date=eff,
            source_url=url, source_page=detail, confidence="high",
            notes="Optional recurring equipment rental, priced by tank size; not an electricity tariff",
            components=components,
        )

    def _parse_sureconnect(self, soup, eff: Optional[str]) -> Optional[TariffRecord]:
        table = _table_after(soup, "SureConnect Service")
        if table is None or not eff or "$/month" not in _clean(table.get_text(" ")):
            return None
        detail = "Residential Rates page, SureConnect Service table"
        components = []
        for tr in table.find_all("tr"):
            cells = [_clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
            if len(cells) == 1:
                continue
            m = re.fullmatch(r"(\d+)\s*AMP", cells[0], re.I)
            price = _money(cells[-1]) if len(cells) == 2 else None
            if not m or price is None:
                return None
            components.append(_component("fixed", f"SureConnect Service {m.group(1)} A", price,
                                         "$/month", eff, RESIDENTIAL_URL, detail,
                                         notes="Monthly generator-connection service"))
        if not components:
            return None
        return TariffRecord(
            utility_name="NB Power", province="NB", utility_type="electricity",
            tariff_name="SureConnect Service (Residential)", tariff_code="SURECONNECT",
            customer_class="residential", sub_class="sureconnect", rate_structure="flat",
            effective_date=eff, source_url=RESIDENTIAL_URL, source_page=detail,
            confidence="high",
            notes="Optional recurring SureConnect service charge; not an electricity tariff",
            components=components,
        )

    def _parse_recreational_lighting(self, soup, eff: Optional[str]) -> Optional[TariffRecord]:
        if not eff:
            return None
        rows = _section_rows(soup, "Recreational Lighting")
        service = tier1 = tier2 = threshold = None
        for label, value in rows:
            low = label.lower()
            if low.startswith("service charge") and "per billing period" in low:
                service = _money(value)
            elif low.startswith("first") and "per billing period" in low:
                m = re.match(r"first\s+([\d,]+)\s*kwh", low)
                threshold = float(m.group(1).replace(",", "")) if m else None
                tier1 = _cents_total(value)
            elif low.startswith("balance") and "per billing period" in low:
                tier2 = _cents_total(value)
        if None in (service, tier1, tier2, threshold):
            return None
        detail = "Business Rates page, Recreational Lighting section"
        return TariffRecord(
            utility_name="NB Power", province="NB", utility_type="electricity",
            tariff_name="Recreational Lighting", tariff_code="RL", customer_class="commercial",
            sub_class="recreational lighting", rate_structure="tiered", effective_date=eff,
            source_url=BUSINESS_URL, source_page=detail, confidence="high",
            notes="Energy blocks apply per billing period",
            components=[
                _component("fixed", "Basic Charge", service, "$/billing period", eff,
                           BUSINESS_URL, detail),
                _component("energy", "Tier 1 Energy Charge", tier1, "$/kWh", eff, BUSINESS_URL,
                           detail, tier_number=1, tier_threshold=threshold, tier_unit="kWh/billing period"),
                _component("energy", "Tier 2 Energy Charge", tier2, "$/kWh", eff, BUSINESS_URL,
                           detail, tier_number=2, tier_threshold=threshold, tier_unit="kWh/billing period"),
            ],
        )

    def _parse_fast_charging(self, soup, eff: Optional[str]) -> Optional[TariffRecord]:
        table = _table_after(soup, "Public Fast Charging Rate")
        if table is None or not eff:
            return None
        detail = "Business Rates page, Public Fast Charging Rate table"
        service_values: set[float] = set()
        components: list[RateComponent] = []
        hours = {"on-peak": None, "off-peak": None}
        fallback_rule = False
        for tr in table.find_all("tr"):
            cells = [_clean(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
            if len(cells) != 3 or tr.find("th"):
                continue
            service = re.fullmatch(r"\$(\d+(?:\.\d+)?) per Billing Period", cells[0])
            if not service:
                return None
            service_values.add(float(service.group(1)))
            band = re.match(r"LF:\s*(\d+)%\s*<\s*LF\s*[≤<]=?\s*(\d+)%\s*Demand:\s*\$(\d+(?:\.\d+)?) per kW per Billing Period$", cells[1])
            if not band:
                if re.match(r"LF:\s*>\s*20%$", cells[1]) and "General Service Rates apply" in cells[2]:
                    fallback_rule = True
                    continue
                return None
            lo, hi, demand = band.group(1), band.group(2), float(band.group(3))
            on_m = re.match(r"On.Peak\s*(?:\(([^)]*)\))?\s*(.*?)\s*Off.Peak\s*(?:\(([^)]*)\))?\s*(.*)$", cells[2])
            if not on_m:
                return None
            for key, hrs in (("on-peak", on_m.group(1)), ("off-peak", on_m.group(3))):
                if hrs:
                    hours[key] = hrs.replace("\u2011", "-").replace("\u2013", "-")
            on_total = _cents_total(on_m.group(2))
            off_total = _cents_total(on_m.group(4))
            if on_total is None or off_total is None:
                return None
            lf = f"LF {lo}% < LF <= {hi}%"
            components.append(_component(
                "demand", f"Demand Charge ({lf})", demand, "$/kW/billing period", eff,
                BUSINESS_URL, detail, demand_unit="kW", sub_component=lf,
                notes="Per kW of demand per billing period, by load-factor band"))
            for key, total in (("on-peak", on_total), ("off-peak", off_total)):
                label = "On-Peak" if key == "on-peak" else "Off-Peak"
                components.append(_component(
                    "energy", f"{label} Energy Charge ({lf})", total, "$/kWh", eff,
                    BUSINESS_URL, detail, sub_component=lf, tou_period=key,
                    tou_hours=hours[key]))
        if len(service_values) != 1 or not fallback_rule or None in hours.values():
            return None
        if sum(1 for c in components if c.component_type == "demand") != 4:
            return None
        components.insert(0, _component(
            "fixed", "Basic Charge", service_values.pop(), "$/billing period", eff,
            BUSINESS_URL, detail))
        return TariffRecord(
            utility_name="NB Power", province="NB", utility_type="electricity",
            tariff_name="Public Fast Charging Rate", tariff_code="PFC", customer_class="commercial",
            sub_class="public fast charging", rate_structure="tou", effective_date=eff,
            source_url=BUSINESS_URL, source_page=detail, confidence="high",
            eligibility="Load factor above 20%: General Service rates apply (Section N-3)",
            notes="Demand and TOU energy depend on the load-factor (LF) band",
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
