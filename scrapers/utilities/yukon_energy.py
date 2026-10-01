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
    https://yukonenergy.ca/customer-service/rates/rate-schedules/
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html, detect_js_rendered, find_pdf_links, extract_pdf_pages,
    extract_effective_date, DocumentPage,
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
        """Parse residential base rates and current riders; other classes stay estimates."""
        try:
            html = self.fetch_page(RATE_SCHEDULES_URL)
            if not html or detect_js_rendered(html):
                html = self.fetch_rendered_page(RATE_SCHEDULES_URL)
            if not html:
                return None
            pdf_links = find_pdf_links(
                parse_html(html), keywords=["base", "rate", "cross", "reference", "rider", "rebate"],
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
        """Return 1160 only when base, percentage riders, fuel and relief are proven."""
        tokens = {
            "base": "cross-reference", "j1": "rider_j1.pdf",
            "fuel": "rider_f_rate_schedule.pdf", "relief": "affordability_rate_relief.pdf",
        }
        documents: dict[str, tuple[str, list[DocumentPage]]] = {}
        for kind, token in tokens.items():
            matches = [url for url in dict.fromkeys(pdf_links) if token in url.lower()]
            if len(matches) != 1:
                self.logger.warning("Missing or ambiguous Yukon %s document", kind)
                return None
            pages = extract_pdf_pages(self.fetch_bytes(matches[0]))
            if not pages:
                self.logger.warning("Unreadable Yukon %s document", kind)
                return None
            documents[kind] = (matches[0], pages)

        base_url, base_pages = documents["base"]
        base_text = "\n".join(page.text for page in base_pages)
        section_match = re.search(
            r"Residential Rate Schedules\s+1160 Hydro Non-Govt(.*?)\n1460 Old Crow Non-Govt",
            base_text, re.S,
        )
        if not section_match:
            return None
        section = section_match.group(1)
        base_values: list[float] = []
        labels = [
            r"Customer", r"First 1000 kWh Energy Block 1", r"1001-2500 kWh Energy Block 2",
            r">2500 kWh Energy Block 3",
        ]
        for index, label in enumerate(labels):
            unit = r"" if index == 0 else r"\s*[^\d\w\s/$+-]{1,2}/kWh"
            row = re.search(label + unit + r"([^\n]*)", section)
            if row and (re.search(r"[-()]", row.group(1)) or (index > 0 and "$" in row.group(1))):
                return None
            values = re.findall(r"\$\s*(\d+(?:\.\d+)?)" if index == 0 else r"\d+(?:\.\d+)?", row.group(1)) if row else []
            if len(values) != 4 or any(float(value) <= 0 for value in values):
                return None
            base_values.append(float(values[0]))

        components = [RateComponent("fixed", "Base Customer Charge", base_values[0], "$/month")]
        for index, (label, threshold) in enumerate((
            ("Energy Block 1 (first 1,000 kWh)", 1000),
            ("Energy Block 2 (1,001-2,500 kWh)", 2500),
            ("Energy Block 3 (over 2,500 kWh)", 2500),
        ), start=1):
            components.append(RateComponent("energy", "Base " + label, round(base_values[index] / 100.0, 6), "$/kWh",
                                            tier_number=index, tier_threshold=threshold, tier_unit="kWh"))
        effective_dates: list[str] = []
        for code, label in (("R", "AEY Rider R"), ("J", "YEC Rider J")):
            match = re.search(label + r":\s*([A-Z][a-z]+\s+\d{1,2},\s*\d{4})\s+(\d+(?:\.\d+)?)%", base_text)
            if not match:
                return None
            effective = extract_effective_date("Effective " + match.group(1))
            if not effective or effective > self.now_iso()[:10]:
                return None
            effective_dates.append(effective)
            components.append(RateComponent("rider", f"Rider {code} - Base Rate Adjustment", float(match.group(2)), "%",
                                            effective_date=effective, notes="Applies to base fixed and energy charges, not to other riders."))
        for component in components:
            component.source_url = base_url
            component.source_detail = "PDF page 1; Rate 1160 base-rate column and Rider R/J headers"

        for kind, title in (("j1", "RIDER J1"), ("fuel", "FUEL ADJUSTMENT RIDER"), ("relief", "AFFORDABILITY RATE RELIEF REBATE")):
            source_url, pages = documents[kind]
            text = re.sub(r"\s+", " ", "\n".join(page.text for page in pages))
            header = re.search(r"\bEffective:\s*(\d{4})[ /-](\d{2})[ /-](\d{2})\b", text)
            if title not in text or not header:
                return None
            effective = date(*(int(part) for part in header.groups())).isoformat()
            if effective > self.now_iso()[:10]:
                return None
            effective_dates.append(effective)
            if kind == "j1":
                match = re.search(r"Rider J1 at (\d+(?:\.\d+)?)% applicable to the base rates", text)
                if not match or "To all electric service retail rates except Rate Schedule 32, Rate Schedule 42 and Rate Schedule 43" not in text:
                    return None
                component = RateComponent("rider", "Rider J1 - Temporary True-Up", float(match.group(1)), "%",
                                          notes="Applies to base fixed and energy charges, not the base-plus-R/J total.")
            elif kind == "fuel":
                match = re.search(r"surcharge rider of (\d+(?:\.\d+)?)\s*[^\d\w\s/$+-]{1,2} per kWh", text)
                if not match or "all kWh consumed" not in text or "APPLICABLE: To all classes of service." not in text:
                    return None
                component = RateComponent("rider", "Rider F - Fuel Adjustment", round(float(match.group(1)) / 100.0, 6), "$/kWh",
                                          notes="Applies to all kWh; excluded from the affordability rebate.")
            else:
                period = re.search(r"rebate effective ([A-Z][a-z]+ \d{1,2}, \d{4}) to ([A-Z][a-z]+ \d{1,2}, \d{4})", text)
                amount = re.search(r"rebate is (-\d+(?:\.\d+)?)% off energy charges", text)
                threshold = re.search(r"first ([\d,]+) kWh", text)
                if not period or not amount or not threshold or not all(value in text for value in (
                    "Non Government", "Not applicable to any commercial", "rebate does not apply to Rider F",
                    "includes base rates and Rider J, J1, R and R1 only",
                )):
                    return None
                start = extract_effective_date("Effective " + period.group(1))
                end = extract_effective_date("Effective " + period.group(2))
                threshold_kwh = float(threshold.group(1).replace(",", ""))
                if start != effective or not end or not effective <= self.now_iso()[:10] <= end or threshold_kwh <= 0:
                    return None
                component = RateComponent("rebate", "Affordability Rate Relief", float(amount.group(1)), "%",
                                          tier_threshold=threshold_kwh, tier_unit="kWh", end_date=end,
                                          notes="Non-government residential only. Applies to eligible energy charges (base, J, J1, R and R1 where applicable) for the first published kWh block; excludes fixed charges and Rider F. Subject to territorial funding.")
            component.effective_date = effective
            component.source_url = source_url
            component.source_detail = "PDF page 1; " + title
            components.append(component)

        base_effective = max(component.effective_date for component in components[:6] if component.effective_date)
        for component in components[:4]:
            component.effective_date = base_effective
            component.notes = "Published base rate before the separately listed percentage riders."
        return TariffRecord(
            utility_name="Yukon Energy", province="YT", utility_type="electricity",
            tariff_name="Residential Service Hydro (Rate 1160)", tariff_code="1160",
            customer_class="residential", sub_class="hydro non-government", rate_structure="tiered",
            effective_date=max(effective_dates), source_url=base_url, source_page="PDF page 1; Rate 1160",
            eligibility="Single-phase secondary-voltage hydro service through one meter for one non-government household (Rate 1160).",
            notes="Base rates, Riders R/J/J1, current Rider F and dated residential relief are separate components; no bill total is calculated. Multiple-residence Rider A and other classes are not included in this record.",
            components=components,
        )

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
