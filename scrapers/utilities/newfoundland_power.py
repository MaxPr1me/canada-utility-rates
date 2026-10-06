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
import re
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from datetime import datetime

from scrapers.utils.parsing import (
    DocumentPage, parse_html, find_pdf_links, extract_pdf_text, extract_pdf_pages,
    extract_effective_date,
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

# Core service classes published in the Newfoundland Power RateBook.
# (rate code, display name, customer_class, rate_structure). Seasonal
# (1.1S) and street/area-lighting (4.x) schedules are not modelled here.
_NF_RATES: list[tuple[str, str, str, str]] = [
    ("1.1", "Domestic Service", "residential", "flat"),
    ("2.1", "General Service 0-100 kW", "commercial", "demand"),
    ("2.3", "General Service 110 kVA - 1000 kVA", "commercial", "demand"),
    ("2.4", "General Service 1000 kVA and Over", "industrial", "demand"),
]


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
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Parse the core Domestic + General Service classes from the official RateBook PDF."""
        try:
            html = self.fetch_page(_SOURCE_URL)
        except Exception:
            self.logger.warning("Failed to fetch Newfoundland Power rates page")
            return None

        pdf_links = find_pdf_links(
            parse_html(html), keywords=["ratebook", "schedule", "rates", "regulation"],
            base_url=_SOURCE_URL,
        )
        for link in pdf_links[:6]:
            try:
                pdf_bytes = self.fetch_bytes(link)
                text = extract_pdf_text(pdf_bytes)
            except Exception:
                continue
            if "RATE #1.1" not in text:
                continue
            records = self._parse_ratebook(text, link)
            if records:
                try:
                    pages = extract_pdf_pages(pdf_bytes)
                except Exception:
                    pages = []
                if pages:
                    self._annotate_base(records, pages, link)
                    records.extend(self._parse_pages(pages, link, records))
                return self.mark_live_parsed(records)
        return None

    # ── Page-aware additions ───────────────────────────────────

    @staticmethod
    def _find_page(pages: list[DocumentPage], *needles: str) -> Optional[DocumentPage]:
        for page in pages:
            if all(re.search(n, page.text) for n in needles):
                return page
        return None

    @staticmethod
    def _page_date(page: DocumentPage) -> Optional[str]:
        m = re.search(r"Effective ([A-Z][a-z]+ \d{1,2}, \d{4})", page.text)
        if not m:
            return None
        try:
            return datetime.strptime(m.group(1), "%B %d, %Y").date().isoformat()
        except ValueError:
            return None

    def _annotate_base(
        self, records: list[TariffRecord], pages: list[DocumentPage], link: str
    ) -> None:
        """Attach page-level provenance to the already parsed core components."""
        for record in records:
            page = self._find_page(
                pages, rf"RATE #{re.escape(record.tariff_code)}\s*\n", "Basic Customer Charge"
            )
            if not page:
                continue
            date = self._page_date(page)
            for comp in record.components:
                comp.effective_date = date or record.effective_date
                comp.source_url = link
                comp.source_detail = f"PDF page {page.page_number}, Rate #{record.tariff_code}"

    def _parse_pages(
        self, pages: list[DocumentPage], link: str, base: list[TariffRecord]
    ) -> list[TariffRecord]:
        """Parse optional/seasonal, discount and fee records; each fails independently."""
        records: list[TariffRecord] = []
        for builder in (
            lambda: self._seasonal_domestic(pages, link, base),
            lambda: self._prompt_payment(pages, link),
            lambda: self._primary_voltage_discount(pages, link),
            lambda: self._service_fees(pages, link),
            lambda: self._curtailable(pages, link, base),
            lambda: self._net_metering_domestic(pages, link, base),
        ):
            try:
                record = builder()
            except Exception:
                self.logger.warning("Newfoundland Power page parser failed", exc_info=True)
                record = None
            if record:
                if isinstance(record, list):
                    records.extend(record)
                else:
                    records.append(record)
        return records

    def _curtailable(
        self, pages: list[DocumentPage], link: str, base: list[TariffRecord]
    ) -> list[TariffRecord]:
        rate = self._find_page(pages, r"CURTAILABLE SERVICE OPTION", r"Contracted Demand Reduction x \$\d+ per kVA")
        conditions = self._find_page(pages, r"CURTAILABLE SERVICE OPTION", r"Failure to Curtail:")
        if not rate or not conditions or self._page_date(rate) != self._page_date(conditions):
            return []
        date = self._page_date(rate)
        if not date or not re.search(
            r"Curtailment Credit = Contracted Demand Reduction x \$(\d+) per kVA", rate.text
        ) or not all(term in rate.text for term in ("300 kW (330 kVA)", "5000 kW (5500 kVA)", "during May billing")):
            return []
        if not all(term in conditions.text for term in ("25% for each", "12.5% for", "no Curtailment Credit")):
            return []
        amount = float(re.search(
            r"Curtailment Credit = Contracted Demand Reduction x \$(\d+) per kVA", rate.text
        ).group(1))
        detail = f"PDF pages {rate.page_number}-{conditions.page_number}, Curtailable Service Option"
        return [TariffRecord(
            utility_name="Newfoundland Power", province="NL", utility_type="electricity",
            tariff_name=f"Curtailable Service Option 1 (Rate {code})", tariff_code=f"{code}-CURT1",
            customer_class=base_rate.customer_class, rate_structure="demand", effective_date=date,
            source_url=link, source_page=detail, confidence="high",
            eligibility=("Rate 2.3 or 2.4 customers demonstrating 300-5000 kW "
                         "(330-5500 kVA) contracted winter demand reduction; enrollment required."),
            notes=("Conditional May billing credit for successful December-March curtailment, "
                   "not a standard demand-charge reduction. Failures reduce or eliminate the "
                   "credit. Option 2 uses a separate load-factor formula and is not represented here."),
            components=[RateComponent(
                component_type="rebate", component_name="Curtailment Credit - Option 1",
                charge_value=-amount, charge_unit="$/kVA", demand_unit="kVA",
                effective_date=date, source_url=link, source_detail=detail, confidence="high",
                notes="Per kVA of contracted demand reduction, credited in May only if conditions are met",
            )],
        ) for code in ("2.3", "2.4")
            if (base_rate := next((r for r in base if r.tariff_code == code and r.effective_date == date), None))]

    def _net_metering_domestic(
        self, pages: list[DocumentPage], link: str, base: list[TariffRecord]
    ) -> Optional[TariffRecord]:
        availability = self._find_page(pages, r"NET METERING SERVICE OPTION", r"Availability:")
        billing = self._find_page(pages, r"NET METERING SERVICE OPTION", r"Customer Generation Credit equals")
        conditions = self._find_page(pages, r"NET METERING SERVICE OPTION", r"nameplate capacity rating")
        domestic = next((r for r in base if r.tariff_code == "1.1"), None)
        if not all((availability, billing, conditions, domestic)):
            return None
        date = self._page_date(billing)
        if not date or any(self._page_date(page) != date for page in (availability, conditions)):
            return None
        if domestic.effective_date != date or not all(term in billing.text for term in (
            "rate applicable to the Customer’s class", "shall not exceed the energy supplied",
            "then-current 2nd block energy charge",
        )) or not all(term in conditions.text for term in (
            "not more than 100 kW", "annual energy requirements", "renewable energy source",
        )) or "not available for unmetered service accounts" not in availability.text:
            return None
        energy = [c for c in domestic.components if c.component_type == "energy" and c.charge_unit == "$/kWh"]
        if len(energy) != 1 or not energy[0].source_detail or energy[0].effective_date != date:
            return None
        detail = (f"{energy[0].source_detail}; PDF pages {availability.page_number}-"
                  f"{conditions.page_number}, Net Metering Service Option")
        return TariffRecord(
            utility_name="Newfoundland Power", province="NL", utility_type="electricity",
            tariff_name="Domestic Net Metering Service Option (Rate 1.1)", tariff_code="1.1-NM",
            customer_class="residential", rate_structure="flat", effective_date=date,
            source_url=link, source_page=detail, confidence="high",
            eligibility=("Metered Rate 1.1 customer with approved renewable generation up to 100 kW, "
                         "designed not to exceed annual premises energy needs; provincial cap applies."),
            notes=("Conditional generation credit against monthly purchases at the Rate 1.1 energy price; "
                   "limited to purchased kWh, with unused kWh banked. Annual bank settlement uses NL "
                   "Hydro's then-current second-block Utility Rate, not this retail price; no "
                   "annual cash settlement is priced here. Fixed charges and taxes remain applicable."),
            components=[RateComponent(
                component_type="rebate", component_name="Domestic Monthly Generation Credit",
                charge_value=-energy[0].charge_value, charge_unit="$/kWh", effective_date=date,
                source_url=link, source_detail=detail, confidence="high",
                notes="Per credited kWh, up to monthly energy purchased; surplus kWh banked",
            )],
        )

    def _seasonal_domestic(
        self, pages: list[DocumentPage], link: str, base: list[TariffRecord]
    ) -> Optional[TariffRecord]:
        page = self._find_page(pages, r"RATE #1\.1S\s*\n", "Winter Season Premium Adjustment")
        if not page:
            return None
        date = self._page_date(page)
        domestic = next((r for r in base if r.tariff_code == "1.1"), None)
        if not date or not domestic or domestic.effective_date != date:
            return None
        if not re.search(r"minimum of\s+12 months of uninterrupted billing", page.text):
            return None
        winter = re.search(
            r"Winter Season Premium Adjustment\s+\(Billing months of December through April\):"
            r"\s*All kilowatt-hours\s*\.{3,}\s*@\s*(\d+\.\d+)¢ per kWh", page.text)
        credit = re.search(
            r"Non-Winter Season Credit Adjustment\s+\(Billing Months of May through November\):"
            r"\s*All kilowatt-hours\s*\.{3,}\s*@\s*\((\d+\.\d+)\)¢ per kWh", page.text)
        if not winter or not credit:
            return None
        detail = f"PDF page {page.page_number}, Rate #1.1S"
        common = dict(charge_unit="$/kWh", effective_date=date, source_url=link,
                      source_detail=detail, confidence="high")
        return TariffRecord(
            utility_name="Newfoundland Power", province="NL", utility_type="electricity",
            tariff_name="Domestic Seasonal - Optional (Rate 1.1S)", tariff_code="1.1S",
            customer_class="residential", rate_structure="flat", effective_date=date,
            source_url=link, source_page=detail, confidence="high",
            eligibility=(
                "Existing Rate #1.1 customers with at least 12 months of uninterrupted "
                "billing history at the serviced premises; available on request."
            ),
            notes=(
                "Adjustments to the Rate #1.1 energy charge, not replacement prices. "
                "12-month binding term, auto-renewing; notice within 60 days after renewal "
                "or in advance to terminate. Includes Municipal Tax and Rate Stabilization "
                "Adjustments per the base rate."
            ),
            components=[
                RateComponent(
                    component_type="rider", component_name="Winter Season Premium Adjustment",
                    charge_value=round(float(winter.group(1)) / 100.0, 6),
                    season="winter", season_months="December-April",
                    notes="Added to Rate #1.1 energy charge, all kWh, billing months December-April",
                    **common),
                RateComponent(
                    component_type="rebate", component_name="Non-Winter Season Credit Adjustment",
                    charge_value=-round(float(credit.group(1)) / 100.0, 6),
                    season="non-winter", season_months="May-November",
                    notes="Deducted from Rate #1.1 energy charge, all kWh, billing months May-November",
                    **common),
            ],
        )

    def _prompt_payment(self, pages: list[DocumentPage], link: str) -> Optional[TariffRecord]:
        found: list[tuple[str, DocumentPage]] = []
        for code in ("1.1", "2.1", "2.3", "2.4"):
            page = self._find_page(pages, rf"RATE #{re.escape(code)}\s*\n", "Discount:")
            if not page or not re.search(
                r"A discount of 1\.5% of the amount of the current month[’']s bill will be "
                r"allowed if the bill is paid within 10\s+days after it is issued", page.text):
                return None
            found.append((code, page))
        dates = {self._page_date(p) for _, p in found}
        if len(dates) != 1 or None in dates:
            return None
        date = dates.pop()
        detail = "; ".join(f"PDF page {p.page_number} (Rate #{c})" for c, p in found)
        return TariffRecord(
            utility_name="Newfoundland Power", province="NL", utility_type="electricity",
            tariff_name="Prompt Payment Discount (Rates 1.1, 2.1, 2.3, 2.4)",
            tariff_code="PPD", customer_class="other", rate_structure="flat",
            effective_date=date, source_url=link, source_page=detail, confidence="high",
            notes=(
                "Condition-based discount on the current month's bill when paid within 10 days "
                "after issue; excludes HST. Not a calculated bill total."
            ),
            components=[RateComponent(
                component_type="rebate", component_name="Prompt Payment Discount",
                charge_value=-1.5, charge_unit="%", effective_date=date, source_url=link,
                source_detail=detail, confidence="high",
                notes="Percentage of the amount of the current month's bill",
            )],
        )

    def _primary_voltage_discount(
        self, pages: list[DocumentPage], link: str
    ) -> Optional[TariffRecord]:
        page = self._find_page(pages, r"for supply at 4 kV to 25 kV", r"primary distribution or\s+transmission voltage")
        if not page:
            return None
        date = self._page_date(page)
        flat = re.sub(r"\s+", " ", page.text)
        m = re.search(
            r"for supply at 4 kV to 25 kV \$(\d+\.\d\d) per kVA \(ii\) for supply at "
            r"33 kV to 138 kV \$(\d+\.\d\d) per kVA", flat)
        if not date or not m or "subject to the minimum monthly charge" not in flat:
            return None
        detail = f"PDF page {page.page_number}, Regulation 9(k)"
        comps = [
            RateComponent(
                component_type="rebate", component_name=name, charge_value=-float(val),
                charge_unit="$/kVA", demand_unit="kVA", effective_date=date, source_url=link,
                source_detail=detail, confidence="high",
                notes="Reduction of the monthly demand charge, subject to the minimum monthly charge",
            )
            for name, val in (
                ("Primary Voltage Demand Discount (4 kV to 25 kV)", m.group(1)),
                ("Primary Voltage Demand Discount (33 kV to 138 kV)", m.group(2)),
            )
        ]
        return TariffRecord(
            utility_name="Newfoundland Power", province="NL", utility_type="electricity",
            tariff_name="Primary Voltage Demand Discount (Regulation 9(k))", tariff_code="RULE-9K",
            customer_class="commercial", rate_structure="demand", effective_date=date,
            source_url=link, source_page=detail, confidence="high",
            eligibility=(
                "Service at primary distribution or transmission voltage where the customer "
                "provides its own transformation and all facilities beyond the point of supply."
            ),
            notes="Conditional credit per kVA of billing demand; not applied to every customer.",
            components=comps,
        )

    def _service_fees(self, pages: list[DocumentPage], link: str) -> Optional[TariffRecord]:
        comps: list[RateComponent] = []
        dates: list[str] = []

        def add(page: Optional[DocumentPage], pattern: str, items: list[tuple[str, str, int]],
                detail_label: str) -> None:
            if not page:
                return
            date = self._page_date(page)
            m = re.search(pattern, page.text)
            if not date or not m:
                return
            for name, unit, group in items:
                comps.append(RateComponent(
                    component_type="other", component_name=name,
                    charge_value=float(m.group(group)), charge_unit=unit, effective_date=date,
                    source_url=link, source_detail=f"PDF page {page.page_number}, {detail_label}",
                    confidence="high", notes="One-time fee per occurrence; excludes HST",
                ))
            dates.append(date)

        add(self._find_page(pages, r"reconnection fee shall be"),
            r"reconnection fee shall be \$(\d+\.\d\d) where the reconnection is done during "
            r"normal office\s+hours or \$(\d+\.\d\d) if it is done at other times",
            [("Reconnection Fee (normal office hours)", "$/reconnection", 1),
             ("Reconnection Fee (other times)", "$/reconnection", 2)],
            "Regulation 9(f)")
        add(self._find_page(pages, r"An application fee of"),
            r"application fee of \$(\d+\.\d\d) will be charged for all requests for Customer "
            r"name changes\s+and connection of new Serviced Premises",
            [("Application Fee (name change / new premises)", "$/application", 1)],
            "Regulation 9(n)")
        add(self._find_page(pages, r"is not honoured by their financial institution"),
            r"not honoured by their financial institution, a charge of \$(\d+\.\d\d) may be applied",
            [("Dishonoured Payment Charge", "$/payment", 1)],
            "Regulation 10(d)")
        if not comps:
            return None
        date = max(dates)
        return TariffRecord(
            utility_name="Newfoundland Power", province="NL", utility_type="electricity",
            tariff_name="Service Fees and Charges (Rules and Regulations)", tariff_code="FEES",
            customer_class="other", sub_class="service fees", rate_structure="flat",
            effective_date=date, source_url=link, confidence="high",
            notes=(
                "One-time fees from Regulations 9 and 10, not monthly charges. Interest on "
                "overdue balances of $50.00 or more is prime plus 5% (a condition, not a fixed charge)."
            ),
            components=comps,
        )

    def _parse_ratebook(self, text: str, link: str) -> list[TariffRecord]:
        """Build a TariffRecord for each core rate class found in the RateBook text."""
        effective = extract_effective_date(text) or SEED_RESIDENTIAL["effective_date"]
        records: list[TariffRecord] = []
        for code, name, customer_class, structure in _NF_RATES:
            section = self._rate_section(text, code)
            if not section:
                continue
            components = self._parse_components(section)
            if not components:
                continue
            records.append(TariffRecord(
                utility_name="Newfoundland Power", province="NL", utility_type="electricity",
                tariff_name=f"{name} (Rate {code})", tariff_code=code,
                customer_class=customer_class, rate_structure=structure,
                effective_date=effective, source_url=link, confidence="high",
                notes=(
                    "Parsed from the Newfoundland Power RateBook "
                    "(PUB-approved Schedule of Rates, Rules and Regulations)."
                ),
                components=components,
            ))
        return records

    @staticmethod
    def _rate_section(text: str, code: str) -> Optional[str]:
        """Return the charge-bearing detail section for a rate code, bounded to the next rate."""
        for m in re.finditer(rf"RATE #{re.escape(code)}\b", text):
            start = m.start()
            nxt = re.search(r"RATE #\d", text[start + 10:])
            end = start + 10 + nxt.start() if nxt else start + 1800
            section = text[start:end]
            if "Basic Customer Charge" in section:
                return section
        return None

    @staticmethod
    def _slice(text: str, start_label: str, end_labels: list[str]) -> str:
        """Return the text between *start_label* and the earliest of *end_labels*."""
        i = text.find(start_label)
        if i == -1:
            return ""
        i += len(start_label)
        end = len(text)
        for label in end_labels:
            j = text.find(label, i)
            if j != -1:
                end = min(end, j)
        return text[i:end]

    def _parse_components(self, section: str) -> list[RateComponent]:
        """Extract fixed, demand and energy components from one rate-detail section."""
        components: list[RateComponent] = []

        # ── Basic Customer Charge (may have metered/phase variants) ──
        basic = self._slice(
            section, "Basic Customer Charge",
            ["Demand Charge", "Energy Charge", "Minimum Monthly"],
        )
        basic = re.sub(r"\.{3,}", " ... ", basic)
        for label, value in re.findall(
            r"([^$\n]*?)\s*\.\.\.\s*\$?([\d.]+)\s*per month", basic
        ):
            label = label.strip(" :")
            name = (
                "Basic Customer Charge"
                if not label or label.lower().startswith("basic customer")
                else f"Basic Customer Charge ({label})"
            )
            components.append(RateComponent(
                component_type="fixed", component_name=name,
                charge_value=float(value), charge_unit="$/month",
            ))

        # ── Demand Charge (seasonal: winter vs. balance of year) ──
        demand = self._slice(
            section, "Demand Charge",
            ["Energy Charge", "Maximum Monthly", "Minimum Monthly"],
        )
        dm = re.search(
            r"\$([\d.]+)\s*per (kW|kVA).*?and\s*\$([\d.]+)\s*per (?:kW|kVA)",
            demand, re.DOTALL,
        )
        if dm:
            unit = dm.group(2)
            components.append(RateComponent(
                component_type="demand", component_name="Demand Charge (December-March)",
                charge_value=float(dm.group(1)), charge_unit=f"$/{unit}", demand_unit=unit,
                notes="Billing demand, winter months (December-March)",
            ))
            components.append(RateComponent(
                component_type="demand", component_name="Demand Charge (April-November)",
                charge_value=float(dm.group(3)), charge_unit=f"$/{unit}", demand_unit=unit,
                notes="Billing demand, balance of year (April-November)",
            ))

        # ── Energy Charge (flat or tiered, quoted in cents) ──
        energy = self._slice(
            section, "Energy Charge",
            ["Maximum Monthly", "Minimum Monthly", "Discount", "General:"],
        )
        energy = re.sub(r"\.{3,}", " ... ", energy)
        for label, value in re.findall(
            r"(First [\d,]+[^@]*?|All excess[^@]*?|All kilowatt-hours[^@]*?)@\s*([\d.]+)",
            energy,
        ):
            clean = re.sub(r"\s+", " ", label.replace("...", "")).strip(" ,")
            tier_number: Optional[int] = None
            threshold: Optional[float] = None
            low = clean.lower()
            if low.startswith("first"):
                tier_number = 1
                fm = re.search(r"First ([\d,]+) kilowatt-hours(?! per)", clean)
                if fm:
                    threshold = float(fm.group(1).replace(",", ""))
            elif "excess" in low:
                tier_number = 2
            components.append(RateComponent(
                component_type="energy",
                component_name=f"Energy Charge - {clean}"[:120],
                charge_value=round(float(value) / 100.0, 6), charge_unit="$/kWh",
                tier_number=tier_number, tier_threshold=threshold,
                tier_unit="kWh" if threshold else None,
            ))

        return components

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
