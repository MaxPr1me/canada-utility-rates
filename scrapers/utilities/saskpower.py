"""
saskpower.py — Scraper for SaskPower electricity rates (Saskatchewan).

SaskPower is the principal electric utility in Saskatchewan, a Crown
corporation providing generation, transmission, and distribution
province-wide. Rates are flat (non-tiered) for most customer classes.

Official source:
  https://www.saskpower.com/accounts/power-rates/power-supply-rates

SaskPower publishes rate schedules as PDFs linked from the landing page.
Supported schedules are rebuilt from their published charge tables. Classes
that cannot be parsed retain explicitly unverified fallback data.

Regulated by: Saskatchewan Rate Review Panel
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html, detect_js_rendered, find_pdf_links, extract_pdf_text,
    extract_effective_date, extract_pdf_pages, DocumentPage,
)

logger = logging.getLogger(__name__)

LANDING_URL = "https://www.saskpower.com/accounts/power-rates/power-supply-rates"

# Known rate values — used as seed/fallback data.
# Values reflect SaskPower's published rates; effective_date updated to
# the most recent known adjustment period.
SEED_RESIDENTIAL = {
    "effective_date": "2026-02-01",
    "source_url": LANDING_URL,
    "energy_rate": 0.15476,         # $/kWh — flat rate (15.476¢/kWh)
    "basic_charge_per_month": 31.16,  # $/month
}

SEED_SMALL_COMMERCIAL = {
    "effective_date": "2025-01-01",
    "source_url": LANDING_URL,
    "energy_rate": 0.1797,          # $/kWh
    "basic_charge_per_month": 40.24,  # $/month
}

SEED_DEMAND_COMMERCIAL = {
    "effective_date": "2025-01-01",
    "source_url": LANDING_URL,
    "energy_rate": 0.0928,          # $/kWh
    "demand_charge": 14.94,         # $/kW
    "basic_charge_per_month": 40.24,  # $/month
}


class SaskPowerScraper(BaseScraper):
    """Scrape SaskPower electricity rates."""

    def __init__(self):
        super().__init__(utility_name="SaskPower", province="SK")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live SaskPower rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d SaskPower tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for SaskPower")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Discover independent schedules and retain per-class fallback provenance."""
        try:
            html = self.fetch_page(LANDING_URL)
            if not html or detect_js_rendered(html):
                html = self.fetch_rendered_page(LANDING_URL)
            if not html:
                self.logger.warning("Could not fetch SaskPower rates page")
                return None

            pdf_links = find_pdf_links(
                parse_html(html),
                keywords=["residential", "rate", "schedule", "service"],
                base_url=LANDING_URL,
            )
        except Exception:
            self.logger.exception("Could not discover SaskPower schedules")
            return None

        live: list[TariffRecord] = []
        for pdf_url in dict.fromkeys(pdf_links):
            try:
                if "residential" in pdf_url.lower():
                    record = self._parse_residential_pdf(
                        extract_pdf_text(self.fetch_bytes(pdf_url)), pdf_url,
                    )
                    if record:
                        live.extend(self.mark_live_parsed([record], source_url=pdf_url))
                elif any(filename in pdf_url.lower() for filename in (
                    "saskpowersuppliedtransformation.pdf", "customerownedtransformation.pdf",
                )):
                    records = self._parse_transformation(
                        extract_pdf_pages(self.fetch_bytes(pdf_url)), pdf_url,
                    )
                    live.extend(self.mark_live_parsed(records, source_url=pdf_url))
            except Exception as exc:
                self.logger.warning("Could not parse SaskPower schedule %s: %s", pdf_url, exc)

        if not live:
            return None
        covered = {record.tariff_name for record in live}
        codes = {record.tariff_code for record in live}
        if {"E05", "E06"} <= codes:
            covered.add("Power Service (Demand)")
        if {"E75", "E76"} <= codes:
            covered.add("Small Commercial Service")
        fallback = [record for record in self._seed_data() if record.tariff_name not in covered]
        return live + self.mark_fallback(fallback) if fallback else live

    def _parse_residential_pdf(self, text: str, source_url: str) -> Optional[TariffRecord]:
        basic = re.search(r"Basic monthly charge\s*\$\s*([\d,]+(?:\.\d+)?)", text, re.IGNORECASE)
        energy = re.search(
            r"Energy charge\s*\([^\d\w\s/$+-]{1,2}/kWh\)\s*([\d.]+)\s*[^\d\w\s/$+-]{1,2}",
            text, re.IGNORECASE,
        )
        effective_date = extract_effective_date(text)
        if not basic or not energy or not effective_date or effective_date > self.now_iso()[:10]:
            return None
        return TariffRecord(
            utility_name="SaskPower", province="SK", utility_type="electricity",
            tariff_name="Residential Service", customer_class="residential",
            rate_structure="flat", effective_date=effective_date,
            source_url=source_url, source_page="Residential standard rate table", confidence="high",
            notes="SaskPower flat residential rate (Standard Rate E01/E03).",
            components=[
                RateComponent("fixed", "Basic Charge", float(basic.group(1).replace(",", "")), "$/month",
                              source_detail="Residential standard rate table"),
                RateComponent("energy", "Energy Charge", round(float(energy.group(1)) / 100.0, 6), "$/kWh",
                              source_detail="Residential standard rate table"),
            ],
        )

    @staticmethod
    def _column_values(text: str, label: str, value_pattern: str, count: int) -> list[float]:
        row = re.search(label + r"([^\n]*)", text, re.IGNORECASE)
        if row and re.search(r"(?:-\s*\$|\$\s*-|\(\s*\$)", row.group(1)):
            raise ValueError(f"Unexpected negative charge in rate row: {label}")
        values = re.findall(value_pattern, row.group(1)) if row else []
        if len(values) != count:
            raise ValueError(f"Incomplete or ambiguous rate row: {label}")
        return [float(value.replace(",", "")) for value in values]

    def _parse_transformation(
        self, pages: list[DocumentPage], source_url: str,
    ) -> list[TariffRecord]:
        records = self._parse_supplied_services(pages, source_url)
        money = r"\$\s*([\d,]+(?:\.\d+)?)"
        cents = r"(-?[\d,]+(?:\.\d+)?)\s*[^\d\w\s/$+-]{1,2}(?=\s|$)"
        schedules = {
            ("E05", "E06"): ("SaskPower-Supplied", "Standard Service", "tiered", "commercial"),
            ("E75", "E76"): ("SaskPower-Supplied", "Small Commercial Service", "tiered", "commercial"),
            ("E07", "E08", "E10", "E12"): ("Customer-Owned", "Standard Service", "flat", "commercial"),
            ("E77", "E78"): ("Customer-Owned", "Small Commercial Service", "tiered", "commercial"),
            ("E82", "E83", "E84"): ("Customer-Owned", "Power Time-of-Use", "tou", "industrial"),
            ("E22", "E23", "E24"): ("Customer-Owned", "Power Standard Service", "flat", "industrial"),
            ("N22", "N23", "N24"): ("Customer-Owned", "Capacity Reservation Service", "flat", "industrial"),
        }
        code_pattern = r"Rate Codes?\*?\s+([EN]\d{2}(?:\s+[EN]\d{2})*)\b"
        for page_index, page in enumerate(pages):
            code_match = re.search(code_pattern, page.text)
            if not code_match:
                continue
            codes = tuple(code_match.group(1).split())
            if codes not in schedules:
                if not set(codes) <= {"E37", "E15", "E16", "E17", "E18", "E35"}:
                    self.logger.warning("Unparsed SaskPower rate codes %s at %s", codes, source_url)
                continue
            owner, name, energy_mode, customer_class = schedules[codes]
            section_pages = [page]
            for continuation in pages[page_index + 1:]:
                if re.search(code_pattern, continuation.text):
                    break
                section_pages.append(continuation)
            text = "\n".join(section.text for section in section_pages)
            count = len(codes)
            try:
                if owner.upper() not in page.text or "MINIMUM BILL" not in text:
                    raise ValueError("Schedule owner or minimum-bill conditions missing")
                effective_header = re.search(r"\bEffective\b(.*?)(?:Supply voltage|Basic monthly charge)", page.text, re.S)
                dates = re.findall(r"\b[A-Z][a-z]+\s+\d{1,2},\s*\d{4}\b", effective_header.group(1)) if effective_header else []
                effective_date = extract_effective_date("Effective " + dates[0]) if len(dates) == 1 else None
                if not effective_date or effective_date > self.now_iso()[:10]:
                    raise ValueError("Missing, ambiguous or future effective date")
                basic = self._column_values(text, r"Basic monthly charge", money, count)
                voltage_row = re.search(r"Supply voltage([^\n]*)", page.text)
                voltages = re.findall(r"\d+\s*kV(?:\s*&\s*(?:less|above))?", voltage_row.group(1)) if voltage_row else []
                if voltage_row and len(voltages) != count:
                    raise ValueError("Incomplete voltage columns")
                if owner == "Customer-Owned" and not voltages:
                    raise ValueError("Missing voltage columns")
                areas = re.findall(r"\((Urban|Rural)\)", effective_header.group(1))
                if customer_class == "commercial" and areas != ["Urban", "Rural"]:
                    raise ValueError("Missing or reordered urban/rural columns")
                if energy_mode == "tiered":
                    free_match = re.search(r"Demand Charge First ([\d,]+) kVA/month", text)
                    if not free_match:
                        raise ValueError("Missing kVA free-demand block")
                    demand_threshold = float(free_match.group(1).replace(",", ""))
                    free_demand = self._column_values(text, r"Demand Charge First [\d,]+ kVA/month", money, count)
                    demand = self._column_values(text, r"Balance\s+\$/kVA", money, count)
                    thresholds = self._column_values(text, r"Energy Charge First block kWh/month",
                                                     r"([\d,]+)\s*kWh", count)
                    first = self._column_values(text, r"First block\s*\([^\d\w\s/$+-]{1,2}/kWh\)", cents, count)
                    balance = self._column_values(text, r"Balance\s*\([^\d\w\s/$+-]{1,2}/kWh\)", cents, count)
                    values = basic + demand + thresholds + first + balance + [demand_threshold]
                    if any(value != 0 for value in free_demand):
                        raise ValueError("Changed free-demand structure")
                else:
                    demand = self._column_values(text, r"Demand Charge Per kVA[^\n$]*", money, count)
                    if energy_mode == "tou":
                        first = self._column_values(text, r"On-peak energy charge", cents, count)
                        balance = self._column_values(text, r"Off-peak energy charge", cents, count)
                        hours = re.search(r"ON-PEAK ENERGY CONSUMPTION\s*(.*?)OFF-PEAK ENERGY CONSUMPTION\s*(.*?)(?:AVAILABILITY|$)", text, re.S)
                        if not hours or not re.search(r"[^\d\w\s/$+-]{1,2}/kWh", text):
                            raise ValueError("Missing time-of-use hours or energy unit")
                        tou_hours = [re.sub(r"\s+", " ", hours.group(index)).strip() for index in (1, 2)]
                        values = basic + demand + first + balance
                    else:
                        first = self._column_values(text, r"Energy Charge\s+[^\d\w\s/$+-]{1,2}/kWh", cents, count)
                        values = basic + demand + first
                if any(value <= 0 for value in values):
                    raise ValueError("Invalid charge values")
            except ValueError as exc:
                self.logger.warning("SaskPower %s: %s", codes, exc)
                continue
            for column, code in enumerate(codes):
                labels = ([areas[column]] if column < len(areas) else []) + ([voltages[column]] if voltages else [])
                label = ", ".join(labels)
                detail = f"PDF pages {page.page_number}-{section_pages[-1].page_number}; Rate {code} ({label})"
                components = [RateComponent("fixed", "Basic Charge", basic[column], "$/month")]
                if energy_mode == "tiered":
                    components.extend([
                        RateComponent("demand", f"Demand Charge - First {demand_threshold:g} kVA", free_demand[column], "$/kVA",
                                      tier_number=1, tier_threshold=demand_threshold, tier_unit="kVA", demand_unit="kVA"),
                        RateComponent("demand", "Demand Charge - Balance", demand[column], "$/kVA",
                                      tier_number=2, tier_threshold=demand_threshold, tier_unit="kVA", demand_unit="kVA"),
                        RateComponent("energy", "Energy Charge - First Block", round(first[column] / 100.0, 6), "$/kWh",
                                      tier_number=1, tier_threshold=thresholds[column], tier_unit="kWh"),
                        RateComponent("energy", "Energy Charge - Balance", round(balance[column] / 100.0, 6), "$/kWh",
                                      tier_number=2, tier_threshold=thresholds[column], tier_unit="kWh"),
                    ])
                else:
                    components.append(RateComponent("demand", "Demand Charge", demand[column], "$/kVA", demand_unit="kVA"))
                    if energy_mode == "tou":
                        components.extend([
                            RateComponent("energy", "On-Peak Energy Charge", round(first[column] / 100.0, 6), "$/kWh",
                                          tou_period="on-peak", tou_hours=tou_hours[0]),
                            RateComponent("energy", "Off-Peak Energy Charge", round(balance[column] / 100.0, 6), "$/kWh",
                                          tou_period="off-peak", tou_hours=tou_hours[1]),
                        ])
                    else:
                        components.append(RateComponent("energy", "Energy Charge", round(first[column] / 100.0, 6), "$/kWh"))
                for component in components:
                    component.source_detail = detail
                eligibility = re.sub(r"\s+", " ", page.text.split("Rate Codes", 1)[0]).strip() + f" {label}."
                if code in {"E10", "E12"}:
                    if "closed to new customers" not in re.sub(r"\s+", " ", text):
                        continue
                    eligibility += " Closed to new customers."
                records.append(TariffRecord(
                    utility_name="SaskPower", province="SK", utility_type="electricity",
                    tariff_name=f"{owner} {name} - {label} (Rate {code})",
                    tariff_code=code, customer_class=customer_class, sub_class=label.lower(),
                    rate_structure="mixed" if energy_mode != "flat" else "demand", effective_date=effective_date,
                    source_url=source_url, source_page=detail, confidence="high",
                    eligibility=eligibility,
                    notes="Published minimum bill and billing conditions: " +
                          re.sub(r"\s+", " ", text.split("MINIMUM BILL", 1)[1]).strip(),
                    components=components,
                ))
        return records

    def _parse_supplied_services(
        self, pages: list[DocumentPage], source_url: str,
    ) -> list[TariffRecord]:
        services = {
            "E37": ("NON-FARM IRRIGATION RATE", "Non-Farm Irrigation", "demand"),
            "E15": ("UNMETERED GENERAL SERVICE RATE", "Unmetered General Service", "flat"),
            "E16": ("UNMETERED GENERAL SERVICE RATE", "Unmetered CATV Power Supply", "flat"),
            "E17": ("UNMETERED CATV RECTIFIER RATE", "Unmetered CATV Rectifier", "flat"),
            "E18": ("UNMETERED X-RAY RATE", "Unmetered X-Ray", "flat"),
            "E35": ("GENERAL SERVICE DIESEL RATE", "General Service Diesel", "tiered"),
        }
        unmetered = {
            "E15": (r"Charge per 100 watt of connected load per month", "Connected Load Charge", "$/100 W/month"),
            "E16": (r"Charge per power supply unit per month", "Power Supply Unit Charge", "$/power supply unit/month"),
            "E17": (r"Charge per 10 watt of connected load per month", "Rectifier Connected Load Charge", "$/10 W/month"),
            "E18": (r"Charge/kVA of installed transformer capacity/month", "Installed Transformer Capacity Charge", "$/kVA/month"),
        }
        money = r"\$\s*([\d,]+(?:\.\d+)?)"
        cents = r"(-?[\d,]+(?:\.\d+)?)\s*[^\d\w\s/$+-]{1,2}(?=\s|$)"
        cent_unit = r"\([^\d\w\s/$+-]{1,2}/kWh\)"
        records: list[TariffRecord] = []
        for page in pages:
            if "SASKPOWER-SUPPLIED" not in page.text:
                continue
            headings = list(re.finditer(r"(?m)^([A-Z][A-Z -]* RATE)[ \t]*$", page.text))
            for section_index, heading in enumerate(headings):
                end = headings[section_index + 1].start() if section_index + 1 < len(headings) else len(page.text)
                section = page.text[heading.start():end]
                code_match = re.search(r"Rate Code\*?\s+(E\d{2})\b", section)
                if not code_match or code_match.group(1) not in services:
                    continue
                code = code_match.group(1)
                expected_header, name, structure = services[code]
                try:
                    if heading.group(1) != expected_header:
                        raise ValueError("Rate code does not match service heading")
                    dates = re.findall(r"\bEffective\s+[A-Z][a-z]+\s+\d{1,2},\s*\d{4}\b", section)
                    effective_date = extract_effective_date(dates[0]) if len(dates) == 1 else None
                    if not effective_date or effective_date > self.now_iso()[:10]:
                        raise ValueError("Missing, ambiguous or future effective date")
                    if code != "E18" and "MINIMUM BILL" not in section:
                        raise ValueError("Missing minimum-bill conditions")
                    if code == "E37":
                        if not re.search(r"annual pumping season between February 1 and Oct\. 31", section):
                            raise ValueError("Changed or missing pumping season")
                        basic = self._column_values(section, r"Basic seasonal charge", money, 1)[0]
                        demand = self._column_values(section, r"Demand Charge \$/HP/season", money, 1)[0]
                        energy = self._column_values(section, r"Energy Charge Energy charge\s*" + cent_unit, cents, 1)[0]
                        components = [
                            RateComponent("fixed", "Basic Seasonal Charge", basic, "$/season"),
                            RateComponent("demand", "Seasonal Horsepower Charge", demand, "$/HP/season", demand_unit="HP"),
                            RateComponent("energy", "Energy Charge", round(energy / 100.0, 6), "$/kWh"),
                        ]
                        for component in components:
                            component.season = "pumping"
                            component.season_months = "2,3,4,5,6,7,8,9,10"
                    elif code == "E35":
                        basic = self._column_values(section, r"Basic monthly charge", money, 1)[0]
                        first_row = re.search(r"Energy Charge First ([\d,]+) kWh/month", section)
                        if not first_row:
                            raise ValueError("Missing diesel energy block threshold")
                        threshold = float(first_row.group(1).replace(",", ""))
                        if threshold <= 0:
                            raise ValueError("Invalid diesel energy block threshold")
                        first = self._column_values(section, r"Energy Charge First [\d,]+ kWh/month\s*" + cent_unit, cents, 1)[0]
                        balance = self._column_values(section, r"Balance\s*" + cent_unit, cents, 1)[0]
                        components = [
                            RateComponent("fixed", "Basic Charge", basic, "$/month"),
                            RateComponent("energy", "Energy Charge - First Block", round(first / 100.0, 6), "$/kWh",
                                          tier_number=1, tier_threshold=threshold, tier_unit="kWh"),
                            RateComponent("energy", "Energy Charge - Balance", round(balance / 100.0, 6), "$/kWh",
                                          tier_number=2, tier_threshold=threshold, tier_unit="kWh"),
                        ]
                    else:
                        label, component_name, unit = unmetered[code]
                        value = self._column_values(section, label, money, 1)[0]
                        components = [RateComponent("other", component_name, value, unit)]
                    if any(component.charge_value is None or component.charge_value <= 0 for component in components):
                        raise ValueError("Invalid charge values")
                except ValueError as exc:
                    self.logger.warning("SaskPower %s: %s", code, exc)
                    continue
                detail = f"PDF page {page.page_number}; Rate {code}; {expected_header}"
                for component in components:
                    component.source_url = source_url
                    component.source_detail = detail
                conditions = section.split("MINIMUM BILL", 1)
                notes = "Minimum bill: " + re.sub(r"\s+", " ", conditions[1]).strip() if len(conditions) == 2 else "Charge applies to installed transformer capacity, not measured demand."
                records.append(TariffRecord(
                    utility_name="SaskPower", province="SK", utility_type="electricity",
                    tariff_name=f"SaskPower-Supplied {name} (Rate {code})", tariff_code=code,
                    customer_class="commercial", sub_class=name.lower(), rate_structure=structure,
                    effective_date=effective_date, source_url=source_url, source_page=detail,
                    eligibility=re.sub(r"\s+", " ", section.split("Rate Code", 1)[0]).strip(),
                    notes=notes, components=components,
                ))
        return records

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="SaskPower",
            province="SK",
            utility_type="electricity",
            tariff_name="Residential Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes="SaskPower flat residential electricity rate (PDF source)",
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

        # ── Small Commercial (Non-Demand) ────────────────────────
        records.append(TariffRecord(
            utility_name="SaskPower",
            province="SK",
            utility_type="electricity",
            tariff_name="Small Commercial Service",
            customer_class="commercial",
            sub_class="small commercial",
            rate_structure="flat",
            effective_date=SEED_SMALL_COMMERCIAL["effective_date"],
            source_url=SEED_SMALL_COMMERCIAL["source_url"],
            confidence="high",
            eligibility="Small commercial customers without demand metering",
            notes="SaskPower small commercial rate without demand charge (PDF source)",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_SMALL_COMMERCIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_SMALL_COMMERCIAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        # ── Demand Commercial ────────────────────────────────────
        records.append(TariffRecord(
            utility_name="SaskPower",
            province="SK",
            utility_type="electricity",
            tariff_name="Power Service (Demand)",
            customer_class="commercial",
            sub_class="demand commercial",
            rate_structure="demand",
            effective_date=SEED_DEMAND_COMMERCIAL["effective_date"],
            source_url=SEED_DEMAND_COMMERCIAL["source_url"],
            confidence="high",
            eligibility="Commercial customers with demand metering",
            notes="SaskPower demand-metered commercial rate (PDF source)",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_DEMAND_COMMERCIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_DEMAND_COMMERCIAL["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Applied to billing demand (kW)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_DEMAND_COMMERCIAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Energy charge per kWh consumed",
                ),
            ],
        ))

        return records
