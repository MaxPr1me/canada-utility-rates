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

This scraper handles D, DP, grandfathered DM, northern off-grid DN, G and M.
Other domestic options remain gaps; multiplier and demand rules are not bill totals.

The scraper downloads the official electricity-rates PDF and extracts
rate values using pdfplumber text extraction + regex. If the PDF fetch
or parse fails, known classes fall back to explicitly unverified seed estimates.
"""

from __future__ import annotations

import logging
import re
from calendar import month_name, monthrange
from datetime import datetime
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html, detect_js_rendered, find_pdf_links, extract_pdf_text,
    extract_pdf_pages, extract_effective_date, DocumentPage,
)
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
            try:
                html = self.fetch_page(RATE_D_URL)
            except Exception as exc:
                self.logger.warning("HQ residential landing page unavailable; checking official PDF: %s", exc)
                html = ""
            if html and detect_js_rendered(html):
                self.logger.info(
                    "HQ rate page is JS-rendered, trying PDF fallback"
                )

            # Download and parse PDF
            pdf_bytes = self.fetch_bytes(PDF_URL)
            if not pdf_bytes:
                self.logger.warning("Empty response from HQ PDF download")
                return None

            pages = extract_pdf_pages(pdf_bytes)
            pdf_text = "\n".join(page.text for page in pages)
            if not pdf_text:
                self.logger.warning("Could not extract text from HQ PDF")
                return None

            effective_date = extract_effective_date("\n".join(page.text for page in pages if page.page_number <= 2))
            if not effective_date or effective_date > self.now_iso()[:10]:
                self.logger.warning("Missing or future Hydro-Quebec publication date")
                return None
            records = self._parse_domestic_rates(pages, effective_date)
            records.extend(self._parse_optional_domestic_rates(pages, effective_date))
            records.extend(self._parse_building_extras(pages, effective_date))

            rate_d = self._parse_rate_d(pdf_text)
            if rate_d:
                rate_d.effective_date = effective_date
                records.append(rate_d)

            rate_g = self._parse_rate_g(pdf_text)
            if rate_g:
                rate_g.effective_date = effective_date
                records.append(rate_g)

            rate_m = self._parse_rate_m(pdf_text)
            if rate_m:
                rate_m.effective_date = effective_date
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
            for record in records:
                record.source_page = record.source_page or "Official electricity-rates PDF"
                for component in record.components:
                    component.source_detail = component.source_detail or record.source_page
                    component.source_url = component.source_url or record.source_url or PDF_URL
                    component.effective_date = component.effective_date or record.effective_date
            live = self.mark_live_parsed(records, source_url=PDF_URL)

            # Preserve any rates we couldn't parse live as labelled seed estimates
            live_names = {r.tariff_name for r in live}
            seed_only = [r for r in self._seed_data() if r.tariff_name not in live_names]
            if seed_only:
                live = live + self.mark_fallback(seed_only)
            return live

        except Exception as e:
            self.logger.warning("Could not fetch/parse Hydro-Québec PDF: %s", e)
            return None

    def _parse_domestic_rates(
        self, pages: list[DocumentPage], effective_date: str,
    ) -> list[TariffRecord]:
        """Rebuild DP, grandfathered DM and off-grid DN from their own sections."""
        sections: dict[str, list[DocumentPage]] = {}
        for page in pages:
            heading = re.match(r"Section\s+\d+\s+\W?\s*Rate\s+(DP|DM)\b", page.text)
            if heading:
                sections.setdefault(heading.group(1), []).append(page)
            page_text = re.sub(r"\s+", " ", page.text)
            if re.search(r"Application of Rate D\s*N\s+9\.1\b", page_text) or (
                re.match(r"Section\s+1\b.*Conditions of Application of Domestic Rates.*Off[-\u2010-\u2015]Grid", page_text, re.I)
                and re.search(r"Billing demand\s+9\.4\b", page_text)
            ):
                sections.setdefault("DN", []).append(page)
        records: list[TariffRecord] = []
        cent_amount = r"(-?\d+(?:\.\d+)?)\s*(?:\u00a2|\u023c|\ufffd|cents?)"
        definitions = re.sub(r"\s+", " ", "\n".join(page.text for page in pages if page.text.startswith("Interpretative Provisions")))
        billing = next((re.sub(r"\s+", " ", page.text) for page in pages if "Adjustment of rates to consumption periods" in page.text), "")
        if "monthly: Relating to a period of 30 consecutive days" not in definitions or "consumption period is 30 consecutive days" not in billing:
            self.logger.warning("Missing Hydro-Quebec domestic billing-period definitions")
            return []
        season_months: dict[str, str] = {}
        season_rules: dict[str, str] = {}
        for season in ("summer", "winter"):
            match = re.search(rf"{season} period: (The period from ([A-Za-z]+) 1(?: of one year)? through ([A-Za-z]+) (\d+)(?: of the next year)?, inclusive\.)", definitions)
            if not match:
                return []
            try:
                first_month = list(month_name).index(match.group(2))
                last_month = list(month_name).index(match.group(3))
            except ValueError:
                return []
            if not first_month or not last_month or int(match.group(4)) != monthrange(int(effective_date[:4]), last_month)[1]:
                return []
            months = list(range(first_month, last_month + 1)) if first_month <= last_month else list(range(first_month, 13)) + list(range(1, last_month + 1))
            season_months[season] = ",".join(str(month) for month in months)
            season_rules[season] = match.group(1)
        adjustment_pages = [page for page in pages if "Credit for supply at medium or high voltage" in page.text and "12.2" in page.text]
        adjustment_text = re.sub(r"\s+", " ", "\n".join(page.text for page in adjustment_pages))
        adjustment_detail = "Conditional credits, Articles 12.2-12.4; PDF pages " + ", ".join(str(page.page_number) for page in adjustment_pages)
        for code in ("DP", "DM", "DN"):
            selected = sections.get(code, [])
            if not selected:
                continue
            text = re.sub(r"\s+", " ", "\n".join(page.text for page in selected))
            text = re.sub(r"\bD\s+([PMN])\b", r"D\1", text)
            if code == "DN":
                text = re.sub(r"\bD\s+T\b", "DT", text)
            try:
                following_heading = "Multiplier" if code == "DN" else "Billing demand"
                structure_match = re.search(rf"Structure of Rate {code}\b\s*\d+\.\d+(.*?){following_heading}\s+\d+\.\d+", text)
                application = re.search(rf"Application(?: of Rate {code})?\s+\d+\.\d+(.*?)Structure of Rate", text)
                minimum = re.search(r"Minimum billing demand\s+\d+\.\d+\s+(.*?)(?=\d{4} Electricity Rates|$)", text)
                if not structure_match or not application or not minimum:
                    raise ValueError("Missing charge, eligibility or minimum-demand section")
                structure = structure_match.group(1)
                if re.search(r"-\s*\$|\$\s*-|\(\s*\$", structure):
                    raise ValueError("Unexpected negative domestic charge")
                energy = re.findall(cent_amount + r"\s+per\s+kilowatthour\b", structure, re.I)
                if len(energy) != 2 or min(float(value) for value in energy) <= 0:
                    raise ValueError("Missing positive energy tiers in cents/kWh")
                components: list[RateComponent] = []
                eligibility = application.group(1).strip()
                notes = "Published billing conditions: " + text[structure_match.end():]
                if code == "DP":
                    if not re.search(r"Installation of maximum[-\u2010-\u2015]demand meter\s+2\.20", text):
                        raise ValueError("Missing DP application continuation")
                    threshold_match = re.search(r"up to ([\d,]+) kilowatthours per monthly period", structure)
                    qualifying = re.search(r"maximum power demand was at least ([\d,]+) kilowatts", eligibility)
                    demand_rows = re.findall(
                        r"\$\s*(\d+(?:\.\d+)?)\s+p\s*er kilowatt of billing demand in excess of ([\d,]+) kilowatts during the (summer|winter) period",
                        structure,
                    )
                    minimum_bill = re.search(r"minimum monthly bill is (.*?)(?=If applicable|$)", structure)
                    if not threshold_match or not qualifying or len(demand_rows) != 2 or {row[2] for row in demand_rows} != {"summer", "winter"} or not minimum_bill:
                        raise ValueError("Missing DP thresholds, seasonal charges or minimum bill")
                    threshold = float(threshold_match.group(1).replace(",", ""))
                    minimum_kw = float(qualifying.group(1).replace(",", ""))
                    tier_unit = "kWh/month"
                    tier_notes = "Per monthly period as defined by the tariff; do not reuse Rate D's daily allowance."
                    for value, allowance, season in demand_rows:
                        if float(value) <= 0 or float(allowance.replace(",", "")) <= 0:
                            raise ValueError("Invalid DP demand values")
                        components.append(RateComponent(
                            "demand", f"{season.title()} Demand Charge", float(value), "$/kW/month",
                            demand_threshold_kw=float(allowance.replace(",", "")), demand_unit="kW", season=season,
                            season_months=season_months[season],
                            notes=season_rules[season] + " Applies above the demand allowance; crossing periods are prorated by days. Monthly means 30 days; other billing durations are prorated under Article 12.11.",
                        ))
                    voltage_credit = re.search(r"Credit for supply at medium or high voltage\s+12\.2(.*?)Credit for supply applicable to domestic rates\s+12\.3", adjustment_text)
                    losses = re.search(r"Adjustment for transformation losses\s+12\.4(.*?)Power factor improvement\s+12\.5", adjustment_text)
                    if not voltage_credit or not losses or "monthly credit in dollars per kilowatt" not in voltage_credit.group(1):
                        raise ValueError("Missing DP conditional adjustment sources")
                    voltage_rows = re.findall(r"(\d+)\s+k\s*V(?:, but less than (\d+)\s+k\s*V)?\s+(\d+\.\d+)", voltage_credit.group(1))
                    if len(voltage_rows) != 5 or "less than 30 days" not in voltage_credit.group(1):
                        raise ValueError("Incomplete supply-voltage credit table or contract restriction")
                    for lower, upper, credit in voltage_rows:
                        voltage_range = f"{lower} to under {upper} kV" if upper else f"{lower} kV or more"
                        components.append(RateComponent(
                            "rebate", f"Conditional Supply Voltage Credit ({voltage_range})", -float(credit), "$/kW/month",
                            sub_component="conditional", demand_unit="kW", source_detail=adjustment_detail,
                            notes="Only the applicable voltage band is used, not all listed credits. Customer must use the supplied voltage or transform at no cost to Hydro-Quebec. No credit for short-term contracts under 30 days. See Article 12.2; not a universal residential discount.",
                        ))
                    notes += " Conditional transformation-loss rule (not assumed to apply): " + losses.group(1).strip()
                    notes = "Minimum bill (not an additional charge): " + minimum_bill.group(1).strip() + " " + notes
                    name, sub_class = "Rate DP - Domestic Demand", "domestic demand"
                else:
                    fixed = re.search(cent_amount + r"\s+system access charge for each day in the consumption period, times the multiplier", structure, re.I)
                    threshold_match = re.search(r"up to the product of ([\d,]+) kilowatthours, the number of days in the consumption period and the multiplier", structure)
                    demand = re.search(r"monthly charge of \$\s*(\d+(?:\.\d+)?)\s+per kilowatt of billing demand in excess of the base billing demand", structure)
                    base_end = r"Rate DT\s+9\.7" if code == "DN" else r"Multiplier\s+\d+\.\d+"
                    multiplier_end = r"Billing demand\s+9\.4" if code == "DN" else r"Mixed use\s+\d+\.\d+"
                    base_demand = re.search(rf"Base billing demand\s+\d+\.\d+\s+(.*?){base_end}", text)
                    multiplier = re.search(rf"Multiplier\s+\d+\.\d+\s+(.*?){multiplier_end}", text)
                    if not all((fixed, threshold_match, demand, base_demand, multiplier)):
                        raise ValueError(f"Missing {code} multiplier or demand conditions")
                    if code == "DM" and ("May 31, 2009" not in eligibility or "bulk metering" not in eligibility):
                        raise ValueError("Missing DM grandfathering or bulk-metering eligibility")
                    if code == "DN" and not all((
                        "from an off-grid system located north of the 53rd parallel" in eligibility,
                        "except the Schefferville system" in eligibility,
                        "multiplier is 1, unless the contract was eligible for Rate DM on May 31, 2009" in multiplier.group(1),
                        "1 for the first 9 rooms" in multiplier.group(1),
                        "1 for each additional room" in multiplier.group(1),
                        "Rate DT described in Chapter 2 does not apply to a contract for electricity supplied by an off-grid system" in text,
                        "credit for supply, as described in Article 12.3, applies" in structure,
                    )):
                        raise ValueError("Missing DN territory, multiplier continuation, DT exclusion or supply-credit reference")
                    if code == "DN":
                        ratchet = re.search(r"equal to (\d+(?:\.\d+)?)% of the maximum power demand.*?falls wholly within the winter period.*?12 consecutive monthly periods", minimum.group(1))
                        allowance = re.search(r"higher of the following values: a\) (\d+(?:\.\d+)?) kilowatts,? or b\) (\d+(?:\.\d+)?) kilowatts times the multiplier", base_demand.group(1))
                        if not ratchet or not 0 < float(ratchet.group(1)) <= 100 or not allowance or min(float(value) for value in allowance.groups()) <= 0:
                            raise ValueError("Incomplete DN winter minimum-demand or kW allowance rule")
                    if float(fixed.group(1)) <= 0 or float(demand.group(1)) <= 0:
                        raise ValueError(f"Invalid {code} charges")
                    components.extend([
                        RateComponent("fixed", "Daily System Access per Multiplier", round(float(fixed.group(1)) / 100, 6), "$/multiplier/day",
                                      notes="Multiply by billing days and the approved tariff multiplier; not a flat per-account daily charge."),
                        RateComponent("demand", "Demand Charge above Base Billing Demand", float(demand.group(1)), "$/kW/month", demand_unit="kW",
                                      notes=base_demand.group(1).strip() + " Apply to billing demand above this computed allowance, not a fixed 50-kW threshold."),
                    ])
                    threshold = float(threshold_match.group(1).replace(",", ""))
                    minimum_kw = None
                    tier_unit = "kWh/day/multiplier"
                    tier_notes = "Multiply allowance by the number of billing days and the approved tariff multiplier. "
                    tier_notes += "Eligibility is grandfathered." if code == "DM" else "DN defaults to multiplier 1 unless the exception in Article 9.3 applies."
                    notes += " Multiplier: " + multiplier.group(1).strip()
                    notes += " Use the applicable occupancy branch only; dwelling and room terms within that branch are additive."
                    if code == "DM":
                        notes += " The mixed-use increment is conditional; no multiplier is assumed."
                    else:
                        notes += " DN defaults to multiplier 1; the alternate occupancy branches apply only to contracts eligible for DM on May 31, 2009."
                    credit_section = re.search(r"Credit for supply applicable to domestic rates\s+12\.3(.*?)Adjustment for transformation losses\s+12\.4", adjustment_text)
                    credit = re.search(r"credit of " + cent_amount + r"\s+per kilowatthour", credit_section.group(1)) if credit_section else None
                    if not credit or float(credit.group(1)) < 0 or not re.search(r"Rate D\s*M\b", credit_section.group(1)):
                        raise ValueError("Missing domestic conditional supply credit")
                    components.append(RateComponent(
                        "rebate", "Conditional Domestic Supply Voltage Credit", -round(float(credit.group(1)) / 100, 6), "$/kWh",
                        sub_component="conditional", source_detail=adjustment_detail,
                        notes=("DN incorporates this conditional credit through Articles 9.2 and 12.3. " if code == "DN" else "") + credit_section.group(1).strip() + " Only when these voltage and ownership conditions are met; not an automatic credit.",
                    ))
                    if code == "DM":
                        name, sub_class = "Rate DM - Grandfathered Bulk Domestic", "grandfathered bulk metered"
                    else:
                        name, sub_class = "Rate DN - Northern Off-Grid Domestic", "northern off-grid domestic"
                if threshold <= 0:
                    raise ValueError("Invalid domestic energy threshold")
                components.extend([
                    RateComponent("energy", "First-Tier Energy", round(float(energy[0]) / 100, 6), "$/kWh",
                                  tier_number=1, tier_threshold=threshold, tier_unit=tier_unit, notes=tier_notes),
                    RateComponent("energy", "Remaining Energy", round(float(energy[1]) / 100, 6), "$/kWh",
                                  tier_number=2, tier_threshold=threshold, tier_unit=tier_unit, notes=tier_notes),
                ])
                conditions = re.search(r"If applicable,(.*?)(?=$)", structure)
                if conditions:
                    notes += " Conditional adjustments: If applicable," + conditions.group(1)
                detail = f"Electricity Rates {code}; PDF pages " + ", ".join(str(page.page_number) for page in selected)
                for component in components:
                    component.source_url = PDF_URL
                    component.source_detail = component.source_detail or detail
                    component.effective_date = effective_date
                records.append(TariffRecord(
                    utility_name=self.utility_name, province="QC", utility_type="electricity",
                    tariff_name=name, tariff_code=code, customer_class="residential", sub_class=sub_class,
                    rate_structure="mixed", effective_date=effective_date, demand_min_kw=minimum_kw,
                    source_url=PDF_URL, source_page=detail, eligibility=eligibility,
                    notes=notes + " Monthly rates and allowances are prorated under Article 12.11 for billing periods other than 30 days. No bill total is calculated.",
                    components=components,
                ))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec domestic %s: %s", code, exc)
        return records

    @staticmethod
    def _option_section(pages: list[DocumentPage], heading: str) -> tuple[list[DocumentPage], str]:
        selected = sorted((page for page in pages if re.match(heading, page.text)), key=lambda page: page.page_number)
        text = " ".join(page.text.split("\n", 1)[1] if "\n" in page.text else "" for page in selected)
        text = text.replace("\u2011", "-").replace("\u2212", "-")
        text = re.sub(r"(?:\b\d+\s+\u2013\s+)?\b20\d\d Electricity Rates(?:\s+\u2013\s+\d+)?", " ", text)
        text = re.sub(r"\bD\s+T\b", "DT", text)
        return selected, re.sub(r"\s+", " ", text)

    def _parse_optional_domestic_rates(
        self, pages: list[DocumentPage], effective_date: str,
    ) -> list[TariffRecord]:
        """Rebuild DT, Flex D and the closed Winter Credit option from their own sections."""
        cent = r"(?<![\d.$])(-?\d+(?:\.\d+)?)\s*(?:\u00a2|\u023c|\ufffd|cents?)"
        all_text = re.sub(r"\bD\s+([TM])\b", r"D\1", re.sub(r"\s+", " ", "\n".join(page.text for page in pages)).replace("\u2011", "-"))
        definitions = re.sub(r"\s+", " ", "\n".join(page.text for page in pages if page.text.startswith("Interpretative Provisions")))
        billing = next((re.sub(r"\s+", " ", page.text) for page in pages if "Adjustment of rates to consumption periods" in page.text), "")
        winter = re.search(r"winter period: The period from ([A-Za-z]+) 1(?: of one year)? through ([A-Za-z]+) (\d+)(?: of the next year)?, inclusive\.", definitions)
        summer = re.search(r"summer period: The period from ([A-Za-z]+) 1 through ([A-Za-z]+) (\d+), inclusive\.", definitions)
        if "monthly: Relating to a period of 30 consecutive days" not in definitions or "consumption period is 30 consecutive days" not in billing or not winter or not summer:
            self.logger.warning("Missing Hydro-Quebec billing-period or season definitions for optional domestic products")
            return []
        season_months: dict[str, str] = {}
        try:
            for season, match in (("winter", winter), ("summer", summer)):
                first, last = list(month_name).index(match.group(1)), list(month_name).index(match.group(2))
                if not first or not last or int(match.group(3)) != monthrange(int(effective_date[:4]), last)[1]:
                    raise ValueError
                months = range(first, last + 1) if first <= last else [*range(first, 13), *range(1, last + 1)]
                season_months[season] = ",".join(str(month) for month in months)
        except ValueError:
            self.logger.warning("Invalid Hydro-Quebec season definitions for optional domestic products")
            return []
        if sorted((season_months["winter"] + "," + season_months["summer"]).split(","), key=int) != [str(month) for month in range(1, 13)]:
            return []
        credit_pages = [page for page in pages if "Credit for supply applicable to domestic rates" in page.text]
        credit_text = re.sub(r"\bD\s+([TM])\b", r"D\1", re.sub(r"\s+", " ", "\n".join(page.text for page in credit_pages)))
        credit_match = re.search(r"Credit for supply applicable to domestic rates\s+12\.3(.*?)Adjustment for transformation losses\s+12\.4(.*?)Power factor improvement", credit_text)
        credit_detail = "Conditional credit, Article 12.3; PDF pages " + ", ".join(str(page.page_number) for page in credit_pages)

        def supply_credit(rate_name: str) -> RateComponent:
            credit = re.search(r"credit of " + cent + r"\s+per kilowatthour on the price of all energy billed", credit_match.group(1)) if credit_match else None
            if not credit or float(credit.group(1)) <= 0 or rate_name not in credit_match.group(1):
                raise ValueError("Missing domestic conditional supply credit for " + rate_name)
            return RateComponent(
                "rebate", "Conditional Domestic Supply Voltage Credit", -round(float(credit.group(1)) / 100, 6), "$/kWh",
                sub_component="conditional", source_detail=credit_detail,
                notes=credit_match.group(1).strip() + " Only when these voltage and ownership conditions are met; not an automatic credit.",
            )

        def finish(selected: list[DocumentPage], label: str, components: list[RateComponent], **fields) -> TariffRecord:
            detail = f"Electricity Rates {label}; PDF pages " + ", ".join(str(page.page_number) for page in selected)
            for component in components:
                component.source_url = PDF_URL
                component.source_detail = component.source_detail or detail
                component.effective_date = effective_date
            notes = fields.pop("notes") + " Monthly rates are prorated under Article 12.11 for billing periods other than 30 days. No bill total is calculated."
            return TariffRecord(
                utility_name=self.utility_name, province="QC", utility_type="electricity", customer_class="residential",
                rate_structure="mixed", effective_date=effective_date, source_url=PDF_URL, source_page=detail,
                notes=notes, components=components, **fields,
            )

        def need(text: str, headings: tuple[str, ...]) -> None:
            for heading in headings:
                if not re.search(re.escape(heading) + r"\s+\d+\.\d+", text):
                    raise ValueError("Missing section: " + heading)

        def clause(text: str, pattern: str, what: str) -> str:
            match = re.search(pattern, text)
            if not match:
                raise ValueError("Missing " + what)
            return match.group(1).strip()

        records: list[TariffRecord] = []

        selected, text = self._option_section(pages, r"Section\s+\d+\s+\W?\s*Rate\s+DT\b")
        if selected:
            try:
                need(text, ("Application", "Characteristics of the dual-energy system", "Sign up for Rate DT", "Structure of Rate DT", "Multiplier",
                            "Billing demand", "Minimum billing demand", "Base billing demand", "Mixed use", "Farms", "Duration of rate application",
                            "Non-compliance with conditions", "Fraud"))
                application = clause(text, r"Application\s+\d+\.\d+\s+(Rate DT applies to a contract eligible for one of the domestic rates.*?)Definition\s+\d+\.\d+", "DT application")
                equipment = clause(text, r"Characteristics of the dual-energy system\s+\d+\.\d+\s+(.*?)Sign up for Rate DT", "DT equipment conditions")
                signup = clause(text, r"Sign up for Rate DT\s+\d+\.\d+\s+(.*?)Recovery after a power failure", "DT sign-up")
                structure = clause(text, r"Structure of Rate DT\s+\d+\.\d+\s+(.*?)Multiplier\s+\d+\.\d+", "DT structure")
                multiplier = clause(text, r"Multiplier\s+\d+\.\d+\s+(.*?)Billing demand\s+\d+\.\d+", "DT multiplier")
                minimum = clause(text, r"Minimum billing demand\s+\d+\.\d+\s+(.*?)Base billing demand\s+\d+\.\d+", "DT minimum demand")
                base = clause(text, r"Base billing demand\s+\d+\.\d+\s+(.*?)Apartment building", "DT base demand")
                apartment = clause(text, r"Apartment building, community residence or rooming house with a dual-energy system\s+\d+\.\d+\s+(.*?)Mixed use\s+\d+\.\d+", "DT apartment rules")
                mixed = clause(text, r"Mixed use\s+\d+\.\d+\s+(.*?)Farms\s+\d+\.\d+", "DT mixed use")
                farms = clause(text, r"Farms\s+\d+\.\d+\s+(.*?)Duration of rate application\s+\d+\.\d+", "DT farm rules")
                duration = clause(text, r"Duration of rate application\s+\d+\.\d+\s+(.*?)Non-compliance with conditions\s+\d+\.\d+", "DT duration")
                noncompliance = clause(text, r"Non-compliance with conditions\s+\d+\.\d+\s+(.*?)Fraud\s+\d+\.\d+", "DT non-compliance")
                fraud = clause(text, r"Fraud\s+\d+\.\d+\s+(.*)$", "DT fraud rule")
                fixed = re.search(cent + r"\s+system access charge for each day in the consumption period, times the multiplier", structure)
                energy = re.search(
                    cent + r" per kilowatthour for energy consumed when the temperature is equal to or higher than -(\d+)\u00b0C or -(\d+)\u00b0C, depending on the climate zones defined by Hydro-Qu\S+bec, and "
                    + cent + r" per kilowatthour for energy consumed when the temperature is below -(\d+)\u00b0C or -(\d+)\u00b0C", structure)
                demand = re.search(r"monthly charge of \$\s*(\d+(?:\.\d+)?)\s+per kilowatt of billing demand in excess of the base billing demand", structure)
                ratchet = re.search(r"equal to (\d+(?:\.\d+)?)% of the maximum power demand during a consumption period that falls wholly within the winter period included in the 12 consecutive monthly periods", minimum)
                allowance = re.search(r"higher of the following values: a\) (\d+(?:\.\d+)?) kilowatts or b\) (\d+(?:\.\d+)?) kilowatts times the multiplier", base)
                if not (fixed and energy and demand and ratchet and allowance):
                    raise ValueError("Missing DT charges, temperature zones, ratchet or base-demand allowance")
                zones = (energy.group(2), energy.group(3))
                if zones != (energy.group(5), energy.group(6)) or len(set(zones)) != 2 or min(int(zone) for zone in zones) <= 0:
                    raise ValueError("Inconsistent DT temperature zones")
                if min(float(fixed.group(1)), float(energy.group(1)), float(energy.group(4)), float(demand.group(1))) <= 0 or not 0 < float(ratchet.group(1)) <= 100 or min(float(value) for value in allowance.groups()) <= 0:
                    raise ValueError("Invalid DT values")
                if not all((
                    "credit for supply, as described in Article 12.3, applies" in structure,
                    "the multiplier is 1 except when there is bulk metering" in multiplier and "May 31, 2009" in multiplier,
                    "automatic switch" in equipment and "temperature gauge" in equipment and "supplied and installed by Hydro-Qu" in equipment,
                    "Certificate of Eligibility" in signup,
                    re.search(r"does not exceed 10 kilowatts", mixed) and re.search(r"no less than 50% of the installed capacity", farms),
                    "minimum of 12 consecutive monthly periods" in duration and "10 business days" in noncompliance and "365 days" in fraud,
                    "Rate DT described in Chapter 2 does not apply to a contract for electricity supplied by an off-grid system" in all_text,
                )):
                    raise ValueError("Missing DT eligibility, multiplier, off-grid exclusion or continuation conditions")
                zone_label = f"-{zones[0]} C or -{zones[1]} C depending on Hydro-Quebec climate zone"
                components = [
                    RateComponent("fixed", "Daily System Access per Multiplier", round(float(fixed.group(1)) / 100, 6), "$/multiplier/day",
                                  notes="Multiply by billing days and the approved tariff multiplier (1 unless the bulk-metering exception applies)."),
                    RateComponent("energy", "Electric Mode Energy (at or above switching temperature)", round(float(energy.group(1)) / 100, 6), "$/kWh",
                                  tou_period="outdoor temperature at or above " + zone_label,
                                  notes="Switching temperature depends on the customer's Hydro-Quebec climate zone; the zone is not assumed. Temperature-based, not clock-based."),
                    RateComponent("energy", "Fuel Mode Energy (below switching temperature)", round(float(energy.group(4)) / 100, 6), "$/kWh",
                                  tou_period="outdoor temperature below " + zone_label,
                                  notes="Applies to energy consumed when the outdoor temperature is below the zone threshold, while the dual-energy system is expected to use its fuel source."),
                    RateComponent("demand", "Demand Charge above Base Billing Demand", float(demand.group(1)), "$/kW/month", demand_unit="kW",
                                  notes=base + " Apply to billing demand above this computed allowance, not a fixed 50-kW threshold."),
                    supply_credit("Rate DT"),
                ]
                notes = (
                    "Dual-energy equipment: " + equipment + " Sign-up: " + signup + " Multiplier: " + multiplier + " Minimum billing demand: " + minimum
                    + " Apartment building, community residence or rooming house: " + apartment + " Mixed use: " + mixed + " Farms: " + farms
                    + " Duration: " + duration + " Non-compliance: " + noncompliance + " Fraud: " + fraud
                    + " Not available for contracts supplied by an off-grid system (Rate DN Article 9.7)."
                    + " Conditional transformation-loss rule (not assumed to apply): " + (credit_match.group(2).strip() if credit_match else "")
                )
                records.append(finish(
                    selected, "DT", components, tariff_name="Rate DT - Domestic Dual-Energy", tariff_code="DT",
                    sub_class="dual-energy heating", eligibility=application + " " + equipment, notes=notes,
                ))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec domestic DT: %s", exc)

        selected, text = self._option_section(pages, r"Section\s+\d+\s+\W?\s*Rate\s+Flex D\b")
        if selected:
            try:
                need(text, ("Application", "Definitions", "Sign-up procedure", "Eligibility", "Conditions applicable to peak demand events",
                            "Peak demand event notifications", "Structure of Rate Flex D", "Termination"))
                application = clause(text, r"Application\s+\d+\.\d+\s+(Rate Flex D applies.*?)Definitions\s+\d+\.\d+", "Flex D application")
                hours = re.search(r"peak hours: All hours from (\d\d:\d\d) to (\d\d:\d\d) and from (\d\d:\d\d) to (\d\d:\d\d) during the winter period, excluding (.*?) when the latter fall within the winter period", text)
                signup = clause(text, r"Sign-up procedure\s+\d+\.\d+\s+(.*?)Eligibility\s+\d+\.\d+", "Flex D sign-up")
                eligibility = clause(text, r"Eligibility\s+\d+\.\d+\s+(For the contract to be eligible.*?)Conditions applicable to peak demand events", "Flex D eligibility")
                events = re.search(r"Maximum number of events per day: (\d+) Minimum interval between 2 events \(hours\): (\d+) Duration of each event \(hours\): (\d+) Maximum duration of events per winter period \(hours\): (\d+)", text)
                notice = re.search(r"before (\d\d:\d\d) on the day prior to each peak demand event", text)
                structure = clause(text, r"Structure of Rate Flex D\s+\d+\.\d+\s+(.*?)Termination\s+\d+\.\d+", "Flex D structure")
                termination = clause(text, r"Termination\s+\d+\.\d+\s+(.*)$", "Flex D termination")
                fixed = re.search(cent + r" system access charge for each day in the consumption period plus a\)", structure)
                winter_rates = re.search(
                    r"a\) During the winter period: " + cent + r" per kilowatthour for energy consumed outside peak demand events, up to the product of (\d+) kilowatthours and the number of days in the consumption period, and "
                    + cent + r" per kilowatthour for the remaining energy consumed outside peak demand events, and " + cent + r" per kilowatthour for energy consumed during peak demand events; or b\)", structure)
                summer_rates = re.search(
                    r"b\) During the summer period: " + cent + r" per kilowatthour for energy consumed, up to the product of (\d+) kilowatthours and the number of days in the consumption period, and "
                    + cent + r" per kilowatthour for the remaining consumption", structure)
                if not (hours and events and notice and fixed and winter_rates and summer_rates):
                    raise ValueError("Missing Flex D charges, peak hours, event limits or notice rule")
                values = [float(winter_rates.group(i)) for i in (1, 3, 4)] + [float(summer_rates.group(i)) for i in (1, 3)] + [float(fixed.group(1))]
                if min(values) <= 0 or float(winter_rates.group(2)) <= 0 or float(summer_rates.group(2)) <= 0 or min(int(value) for value in events.groups()) <= 0:
                    raise ValueError("Invalid Flex D values")
                if "times the multiplier" in structure or not all((
                    "credit for supply, as described in Article 12.3, applies" in structure,
                    "single communicating meter" in eligibility and "Customer Space" in eligibility,
                    "must not be supplied by an off-grid system" in eligibility,
                    "Winter Credit Option" in eligibility and "Net Metering Option" in eligibility,
                    "cannot sign up again during that same winter or the following winter period" in eligibility,
                    "within 5 business days" in signup and re.search(r"applies as of the day following Hydro-Qu.bec.s acceptance", signup),
                )):
                    raise ValueError("Missing Flex D eligibility, enrollment or multiplier-free structure")
                peak_hours = f"{hours.group(1)}-{hours.group(2)},{hours.group(3)}-{hours.group(4)}"
                rate_text = (
                    "Applies only after Hydro-Quebec accepts the request, from the following day. Winter rates apply only in the winter period; "
                    "the event price applies only to peak demand events notified before " + notice.group(1) + " on the preceding day."
                )
                threshold_unit = "kWh/day"
                components = [
                    RateComponent("fixed", "Daily System Access", round(float(fixed.group(1)) / 100, 6), "$/day", notes="No multiplier applies to Rate Flex D."),
                    RateComponent("energy", "Winter First-Tier Energy Outside Peak Demand Events", round(float(winter_rates.group(1)) / 100, 6), "$/kWh",
                                  tier_number=1, tier_threshold=float(winter_rates.group(2)), tier_unit=threshold_unit, season="winter",
                                  season_months=season_months["winter"], tou_period="outside peak demand events", notes=rate_text),
                    RateComponent("energy", "Winter Remaining Energy Outside Peak Demand Events", round(float(winter_rates.group(3)) / 100, 6), "$/kWh",
                                  tier_number=2, tier_threshold=float(winter_rates.group(2)), tier_unit=threshold_unit, season="winter",
                                  season_months=season_months["winter"], tou_period="outside peak demand events", notes=rate_text),
                    RateComponent("energy", "Winter Peak Demand Event Energy", round(float(winter_rates.group(4)) / 100, 6), "$/kWh",
                                  season="winter", season_months=season_months["winter"], tou_period="peak demand event", tou_hours=peak_hours,
                                  notes=f"Events may occur only in peak hours {peak_hours}, excluding {hours.group(5)}; at most {events.group(1)} per day, {events.group(2)} h apart, {events.group(3)} h each and {events.group(4)} h per winter. " + rate_text),
                    RateComponent("energy", "Summer First-Tier Energy", round(float(summer_rates.group(1)) / 100, 6), "$/kWh",
                                  tier_number=1, tier_threshold=float(summer_rates.group(2)), tier_unit=threshold_unit, season="summer", season_months=season_months["summer"]),
                    RateComponent("energy", "Summer Remaining Energy", round(float(summer_rates.group(3)) / 100, 6), "$/kWh",
                                  tier_number=2, tier_threshold=float(summer_rates.group(2)), tier_unit=threshold_unit, season="summer", season_months=season_months["summer"]),
                    supply_credit("Rate Flex D"),
                ]
                notes = "Optional product for a Rate D-eligible contract; enrollment, eligibility and event rules: Sign-up: " + signup + " Eligibility: " + eligibility + " Termination: " + termination
                records.append(finish(
                    selected, "Flex D", components, tariff_name="Rate Flex D - Domestic Peak Events", tariff_code="FLEX_D",
                    sub_class="optional peak demand event rate", eligibility=application + " " + eligibility, notes=notes,
                ))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec domestic Flex D: %s", exc)

        selected, text = self._option_section(pages, r"Section\s+\d+\s+\W?\s*Winter Credit Option for Rate D Customers")
        if selected:
            try:
                need(text, ("Application", "Definitions", "Sign-up procedure", "Eligibility", "Conditions applicable to peak demand events",
                            "Peak demand event notifications", "Credit", "Termination"))
                application = clause(text, r"Application\s+\d+\.\d+\s+(The Winter Credit Option.*?)Definitions\s+\d+\.\d+", "Winter Credit application")
                calculation_rules = clause(text, r"Definitions\s+\d+\.\d+\s+(.*?)Sign-up procedure\s+\d+\.\d+", "Winter Credit reference-energy definitions")
                notification_rules = clause(text, r"Peak demand event notifications\s+\d+\.\d+\s+(.*?)Credit\s+2\.64", "Winter Credit notifications")
                signup_rules = clause(text, r"Sign-up procedure\s+\d+\.\d+\s+(.*?)Eligibility\s+\d+\.\d+", "Winter Credit sign-up")
                termination_rules = clause(text, r"Termination\s+\d+\.\d+\s+(.*)$", "Winter Credit termination")
                cutoff = re.search(r"reserved for the Rate D contract to which it applied up to ([A-Za-z]+ \d{1,2}, \d{4})", application)
                hours = re.search(r"peak hours: All hours from (\d\d:\d\d) to (\d\d:\d\d) and from (\d\d:\d\d) to (\d\d:\d\d) during the winter period, excluding (.*?) when the latter fall within the winter period", text)
                eligibility = clause(text, r"Eligibility\s+\d+\.\d+\s+(To be eligible for this option.*?)Conditions applicable to peak demand events", "Winter Credit eligibility")
                events = re.search(r"Maximum number of events per day: (\d+) Minimum interval between 2 events \(hours\): (\d+) Duration of each event \(hours\): (\d+) Maximum duration of events per winter period \(hours\): (\d+)", text)
                credit = re.search(r"entitled to the following credit: " + cent + r" per kilowatthour of energy curtailed\. (No credit is given for a peak demand event .*?)Termination\s+\d+\.\d+", text)
                if not (cutoff and hours and events and credit):
                    raise ValueError("Missing Winter Credit closed-enrollment date, peak hours, event limits or credit")
                closed_on = datetime.strptime(cutoff.group(1), "%B %d, %Y").date().isoformat()
                if closed_on > self.now_iso()[:10] or float(credit.group(1)) <= 0 or min(int(value) for value in events.groups()) <= 0:
                    raise ValueError("Invalid Winter Credit values")
                if not all((
                    "single communicating meter" in eligibility, "must not be supplied by an off-grid system" in eligibility,
                    "must not be signed up for a Net Metering Option" in eligibility,
                    "reference energy:" in calculation_rules and "reference period:" in calculation_rules,
                    "temperature adjustment:" in calculation_rules and "This value cannot be negative" in calculation_rules,
                    "excluding the minimum and maximum values for each hour" in calculation_rules,
                    "5 weekdays or 5 weekend days" in calculation_rules,
                    "before 15:00 on the day prior" in notification_rules,
                    "notification may be sent after 15:00" in notification_rules,
                    "within 5 business days" in signup_rules,
                )):
                    raise ValueError("Missing Winter Credit eligibility conditions")
                peak_hours = f"{hours.group(1)}-{hours.group(2)},{hours.group(3)}-{hours.group(4)}"
                components = [RateComponent(
                    "rebate", "Winter Credit per kWh Curtailed", -round(float(credit.group(1)) / 100, 6), "$/kWh curtailed",
                    sub_component="conditional", season="winter", season_months=season_months["winter"], tou_period="peak demand event", tou_hours=peak_hours,
                    notes=f"Credit applies only to energy curtailed during notified peak demand events (peak hours {peak_hours}, excluding {hours.group(5)}). " + credit.group(2).strip(),
                )]
                notes = (
                    f"Closed to new enrollment: {application} Eligibility: {eligibility} Peak demand events: at most {events.group(1)} per day, "
                    f"{events.group(2)} h apart, {events.group(3)} h each and {events.group(4)} h per winter. Credit is conditional on enrollment, curtailment and notified events; "
                    f"Rate D charges remain separate. Closed-enrollment cutoff in source: {closed_on}."
                    + " Source calculation rules (not calculated here): " + calculation_rules
                    + " Notification rules: " + notification_rules + " Sign-up: " + signup_rules
                    + " Termination: " + termination_rules
                )
                records.append(finish(
                    selected, "Winter Credit Option (Rate D)", components, tariff_name="Winter Credit Option - Rate D", tariff_code="WINTER_CREDIT_D",
                    sub_class="closed to new enrollment", eligibility=application + " " + eligibility, notes=notes,
                ))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec Winter Credit Option: %s", exc)
        return records

    # ── Building extras: Inukjuak, G9, Flex G/M/G9, dual-energy, options ──

    @staticmethod
    def _run_section(pages: list[DocumentPage], heading: str, article: str) -> tuple[list[DocumentPage], str]:
        """Consecutive pages of one section, starting at the page that carries its opening article."""
        by_number = {page.page_number: page for page in pages}
        first = next((page for page in sorted(pages, key=lambda p: p.page_number)
                      if re.match(heading, page.text) and re.search(article, page.text)), None)
        if first is None:
            return [], ""
        selected = [first]
        number = first.page_number + 1
        while number in by_number and re.match(heading, by_number[number].text):
            selected.append(by_number[number])
            number += 1
        text = " ".join(page.text.split("\n", 1)[1] if "\n" in page.text else "" for page in selected)
        text = text.replace("\u2011", "-").replace("\u2212", "-")
        text = re.sub(r"(?:\b\d+\s+\u2013\s+)?\b20\d\d Electricity Rates(?:\s+\u2013\s+\d+)?", " ", text)
        text = re.sub(r"\bG\s+9\b", "G9", text)
        text = re.sub(r"\bD\s+([TMNP])\b", r"D\1", text)
        return selected, re.sub(r"\s+", " ", text)

    @staticmethod
    def _period_months(text: str, name: str, year: int) -> str:
        match = re.search(
            rf"(?<![-\w]){name}: The period from ([A-Za-z]+) 1(?: of one year)? through ([A-Za-z]+) (\d+)(?: of the next year)?, inclusive", text)
        if not match:
            raise ValueError("Missing definition of " + name)
        first, last = list(month_name).index(match.group(1)), list(month_name).index(match.group(2))
        if not first or not last or int(match.group(3)) != monthrange(year, last)[1]:
            raise ValueError("Invalid definition of " + name)
        months = range(first, last + 1) if first <= last else [*range(first, 13), *range(1, last + 1)]
        return ",".join(str(month) for month in months)

    def _parse_building_extras(
        self, pages: list[DocumentPage], effective_date: str,
    ) -> list[TariffRecord]:
        """Inukjuak dual-energy, G9, Flex G/M/G9, dual-energy heating rates, Winter Credit G and net metering."""
        cent = r"(?<![\d.$])(-?\d+(?:\.\d+)?)\s*(?:\u00a2|\u023c|\ufffd|cents?)"
        definitions = re.sub(r"\s+", " ", "\n".join(page.text for page in pages if page.text.startswith("Interpretative Provisions")))
        billing = next((re.sub(r"\s+", " ", page.text) for page in pages if "Adjustment of rates to consumption periods" in page.text), "")
        if "monthly: Relating to a period of 30 consecutive days" not in definitions or "consumption period is 30 consecutive days" not in billing:
            self.logger.warning("Missing Hydro-Quebec billing-period definitions for building rates")
            return []
        year = int(effective_date[:4])
        try:
            winter_months = self._period_months(definitions, "winter period", year)
            summer_months = self._period_months(definitions, "summer period", year)
            if sorted((winter_months + "," + summer_months).split(","), key=int) != [str(month) for month in range(1, 13)]:
                raise ValueError("Seasons do not cover the year")
        except ValueError as exc:
            self.logger.warning("Invalid Hydro-Quebec season definitions for building rates: %s", exc)
            return []
        credit_pages = [page for page in pages if "Credit for supply at medium or high voltage" in page.text and "12.2" in page.text]
        credit_text = re.sub(r"\bG\s+9\b", "G9", re.sub(r"\s+", " ", "\n".join(page.text for page in credit_pages)))
        credit_detail = "Conditional credits, Articles 12.2-12.4; PDF pages " + ", ".join(str(page.page_number) for page in credit_pages)
        domestic_credit = re.search(r"Credit for supply applicable to domestic rates\s+12\.3(.*?)Adjustment for transformation losses\s+12\.4(.*?)Power factor improvement", credit_text)
        credit_clause = "credit for supply at medium or high voltage and the adjustment for transformation losses, as described in articles 12.2 and 12.4, apply"

        def voltage_credits() -> tuple[list[RateComponent], str]:
            voltage = re.search(r"Credit for supply at medium or high voltage\s+12\.2(.*?)Credit for supply applicable to domestic rates\s+12\.3", credit_text)
            if not voltage or not domestic_credit or "monthly credit in dollars per kilowatt" not in voltage.group(1) or "less than 30 days" not in voltage.group(1):
                raise ValueError("Missing supply-voltage credit table or contract restriction")
            rows = re.findall(r"(\d+)\s+k\s*V(?:, but less than (\d+)\s+k\s*V)?\s+(\d+\.\d+)", voltage.group(1))
            if len(rows) != 5 or min(float(row[2]) for row in rows) <= 0:
                raise ValueError("Incomplete supply-voltage credit table")
            components = []
            for lower, upper, credit in rows:
                band = f"{lower} to under {upper} kV" if upper else f"{lower} kV or more"
                components.append(RateComponent(
                    "rebate", f"Conditional Supply Voltage Credit ({band})", -float(credit), "$/kW/month",
                    sub_component="conditional", demand_unit="kW", source_detail=credit_detail,
                    notes="Only the applicable voltage band is used, not all listed credits. Customer must use the supplied voltage or transform it at no cost to Hydro-Quebec. No credit for short-term contracts under 30 days or on the minimum monthly amount. See Article 12.2.",
                ))
            return components, " Conditional transformation-loss rule (not assumed to apply): " + domestic_credit.group(2).strip()

        def domestic_supply_credit() -> RateComponent:
            credit = re.search(r"credit of " + cent + r"\s+per kilowatthour on the price of all energy billed", domestic_credit.group(1)) if domestic_credit else None
            if not credit or float(credit.group(1)) <= 0:
                raise ValueError("Missing domestic conditional supply credit")
            return RateComponent(
                "rebate", "Conditional Domestic Supply Voltage Credit", -round(float(credit.group(1)) / 100, 6), "$/kWh",
                sub_component="conditional", source_detail=credit_detail,
                notes=domestic_credit.group(1).strip() + " Only when these voltage and ownership conditions are met; not an automatic credit.",
            )

        def finish(selected: list[DocumentPage], label: str, components: list[RateComponent], customer_class: str, **fields) -> TariffRecord:
            detail = f"Electricity Rates {label}; PDF pages " + ", ".join(str(page.page_number) for page in selected)
            for component in components:
                component.source_url = PDF_URL
                component.source_detail = component.source_detail or detail
                component.effective_date = effective_date
            notes = fields.pop("notes") + " Monthly rates are prorated under Article 12.11 for billing periods other than 30 days. No bill total is calculated."
            return TariffRecord(
                utility_name=self.utility_name, province="QC", utility_type="electricity", customer_class=customer_class,
                rate_structure="mixed", effective_date=effective_date, source_url=PDF_URL, source_page=detail,
                notes=notes, components=components, **fields,
            )

        def need(text: str, headings: tuple[str, ...]) -> None:
            for heading in headings:
                if not re.search(re.escape(heading) + r"\s+\d+\.\d+", text):
                    raise ValueError("Missing section: " + heading)

        def clause(text: str, pattern: str, what: str) -> str:
            match = re.search(pattern, text)
            if not match:
                raise ValueError("Missing " + what)
            return match.group(1).strip()

        def positive(*values: str) -> None:
            if min(float(value.replace(",", "")) for value in values) <= 0:
                raise ValueError("Non-positive published value")

        def peak_rules(text: str, structure_text: str) -> tuple[re.Match, re.Match, re.Match]:
            hours = re.search(r"peak hours: All hours from (\d\d:\d\d) to (\d\d:\d\d) and from (\d\d:\d\d) to (\d\d:\d\d) during the winter period, excluding:? (.*?) when the latter fall within the winter period", text)
            events = re.search(r"Maximum number of events per day: (\d+) Minimum interval between 2 events \(hours\): (\d+) Duration of each event \(hours\): (\d+(?: or \d+)?) Maximum duration of events per winter period \(hours\): (\d+)", text)
            notice = re.search(r"before (\d\d:\d\d) on the day prior to each peak demand event", text)
            if not (hours and events and notice):
                raise ValueError("Missing peak hours, event limits or notice rule")
            if min(int(value) for value in re.findall(r"\d+", events.group(0).split("per day:", 1)[1])) <= 0:
                raise ValueError("Invalid event limits")
            return hours, events, notice

        def flex_components(text: str, structure_text: str, hours, events, notice, winter_match, fixed_component: list[RateComponent]) -> list[RateComponent]:
            peak_hours = f"{hours.group(1)}-{hours.group(2)},{hours.group(3)}-{hours.group(4)}"
            rule = ("Applies only after enrolment is accepted. Winter rates apply only in the winter period; the event price applies only to peak demand events notified before "
                    + notice.group(1) + " on the preceding day.")
            return [
                *fixed_component,
                RateComponent("energy", "Winter Energy Outside Peak Demand Events", round(float(winter_match.group(1)) / 100, 6), "$/kWh",
                              season="winter", season_months=winter_months, tou_period="outside peak demand events", notes=rule),
                RateComponent("energy", "Winter Peak Demand Event Energy", round(float(winter_match.group(2)) / 100, 6), "$/kWh",
                              season="winter", season_months=winter_months, tou_period="peak demand event", tou_hours=peak_hours,
                              notes=f"Events may occur only in peak hours {peak_hours}, excluding {hours.group(5)}; at most {events.group(1)} per day, {events.group(2)} h apart, {events.group(3)} h each and {events.group(4)} h per winter. " + rule),
            ]

        def phase_minimum(structure_text: str) -> str:
            minimum = re.search(r"minimum monthly bill is \$(\d+\.\d+) when single-phase electricity is delivered or \$(\d+\.\d+) when three-phase electricity is delivered", structure_text)
            if not minimum or float(minimum.group(1)) <= 0 or float(minimum.group(2)) <= 0:
                raise ValueError("Missing minimum monthly bill")
            return f"Minimum monthly bill (not an additional charge): ${minimum.group(1)} single-phase, ${minimum.group(2)} three-phase."

        winter_re = (r"a\) During the winter period: " + cent + r" per kilowatthour for energy consumed outside peak demand events, and "
                     + cent + r" per kilowatthour for energy consumed during peak demand events;? or b\) During the summer period: ")
        flex_checks = ("single communicating meter", "must not be supplied by an off-grid system", "Customer Space")
        records: list[TariffRecord] = []

        # Inukjuak dual-energy domestic
        selected, text = self._run_section(pages, r"Section\s+6\s+\W?\s*Dual\W?Energy Domestic Rate\s*\W\s*Inukjuak System", r"Application\s+9\.40\b")
        if selected:
            try:
                need(text, ("Application", "Definition", "Eligibility", "Sign-up procedure", "Multiplier", "Billing demand", "Minimum billing demand",
                            "Base billing demand", "Non-compliance with conditions"))
                application = clause(text, r"Application\s+9\.40\s+(This rate applies.*?)Definition\s+9\.41", "Inukjuak application")
                eligibility = clause(text, r"Eligibility\s+9\.42\s+(.*?)Sign-up procedure\s+9\.43", "Inukjuak eligibility")
                signup = clause(text, r"Sign-up procedure\s+9\.43\s+(.*?)Structure of the Dual-Energy Domestic Rate \W Inukjuak System\s+9\.44", "Inukjuak sign-up")
                structure = clause(text, r"Structure of the Dual-Energy Domestic Rate \W Inukjuak System\s+9\.44\s+(.*?)Multiplier\s+9\.45", "Inukjuak structure")
                multiplier = clause(text, r"Multiplier\s+9\.45\s+(.*?)Determination of prices under the Dual-Energy Domestic Rate \W Inukjuak System\s+9\.46", "Inukjuak multiplier")
                pricing = clause(text, r"Determination of prices under the Dual-Energy Domestic Rate \W Inukjuak System\s+9\.46\s+(.*?)Billing demand\s+9\.47", "Inukjuak price determination")
                minimum = clause(text, r"Minimum billing demand\s+9\.48\s+(.*?)Base billing demand\s+9\.49", "Inukjuak minimum demand")
                base = clause(text, r"Base billing demand\s+9\.49\s+(.*?)Non-compliance with conditions\s+9\.50", "Inukjuak base demand")
                noncompliance = clause(text, r"Non-compliance with conditions\s+9\.50\s+(.*?)Provision applicable to customers benefiting from the Efficient Energy Use Program\s+9\.51", "Inukjuak non-compliance")
                efficiency = clause(text, r"Efficient Energy Use Program\s+9\.51\s+(.*)$", "Inukjuak efficiency-program rebate")
                fixed = re.search(cent + r"\s+system access charge for each day in the consumption period, times the multiplier", structure)
                energy = re.search(
                    cent + r" per kilowatthour for energy consumed, up to the product of ([\d,]+) kilowatthours, the number of days in the consumption period and the multiplier, and "
                    + cent + r" per kilowatthour for the remaining consumption", structure)
                demand = re.search(r"monthly charge of \$\s*(\d+(?:\.\d+)?)\s+per kilowatt of billing demand in excess of the base billing demand", structure)
                ratchet = re.search(r"equal to (\d+(?:\.\d+)?)% of the maximum power demand during a consumption period that falls wholly within the winter period included in the 12 consecutive monthly periods", minimum)
                allowance = re.search(r"higher of the following values: a\) (\d+(?:\.\d+)?) kilowatts, or b\) (\d+(?:\.\d+)?) kilowatts times the multiplier", base)
                if not (fixed and energy and demand and ratchet and allowance):
                    raise ValueError("Missing Inukjuak charges, ratchet or base-demand allowance")
                positive(fixed.group(1), energy.group(1), energy.group(2), energy.group(3), demand.group(1), allowance.group(1), allowance.group(2))
                if not 0 < float(ratchet.group(1)) <= 100:
                    raise ValueError("Invalid Inukjuak ratchet")
                if not all((
                    "Inukjuak off-grid system" in application and "Rate DN" in application,
                    "switch remotely controlled by Hydro-Qu" in eligibility and "must not be used simultaneously" in eligibility,
                    "Prices are set on an annual basis as specified in Article 9.46" in structure,
                    "credit for supply, as described in Article 12.3, applies" in structure,
                    "the multiplier is 1, unless the contract was eligible for Rate DM on May 31, 2009" in multiplier,
                    "second-tier energy price is determined as follows" in pricing and "reference index" in pricing,
                    "billed at" in noncompliance and "second-tier energy price at Rate DN" in noncompliance,
                    "until March 31, 2029" in efficiency,
                )):
                    raise ValueError("Missing Inukjuak eligibility, multiplier, price-determination or conditional rules")
                threshold = float(energy.group(2).replace(",", ""))
                tier_note = "Multiply the allowance by billing days and the approved multiplier (1 unless the Rate DM exception applies)."
                components = [
                    RateComponent("fixed", "Daily System Access per Multiplier", round(float(fixed.group(1)) / 100, 6), "$/multiplier/day",
                                  notes="Equal to Rate DN's charge (Article 9.46). Multiply by billing days and the multiplier."),
                    RateComponent("energy", "First-Tier Energy", round(float(energy.group(1)) / 100, 6), "$/kWh",
                                  tier_number=1, tier_threshold=threshold, tier_unit="kWh/day/multiplier", notes=tier_note + " Equal to Rate DN's first-tier price."),
                    RateComponent("energy", "Remaining Energy (indexed fuel-mode price)", round(float(energy.group(3)) / 100, 6), "$/kWh",
                                  tier_number=2, tier_threshold=threshold, tier_unit="kWh/day/multiplier",
                                  notes=tier_note + " Second-tier price set from an oil-price formula and annual CPI index (Article 9.46); published value used. " + pricing),
                    RateComponent("demand", "Demand Charge above Base Billing Demand", float(demand.group(1)), "$/kW/month", demand_unit="kW",
                                  notes=base + " Apply to billing demand above this computed allowance, not a fixed 50-kW threshold."),
                    domestic_supply_credit(),
                ]
                notes = ("Dual-energy off-grid domestic rate for Rate DN-eligible contracts at the Inukjuak system. Eligibility: " + eligibility + " Sign-up: " + signup
                         + " Multiplier: " + multiplier + " Minimum billing demand: " + minimum + " Non-compliance: " + noncompliance
                         + " Efficient Energy Use Program rebate on the second-tier price (conditional, not applied): " + efficiency)
                records.append(finish(selected, "DN Inukjuak dual-energy", components, "residential", tariff_name="Rate DN Dual-Energy - Inukjuak System",
                                      tariff_code="DN_INUKJUAK", sub_class="dual-energy off-grid (Inukjuak)", eligibility=application + " " + eligibility, notes=notes))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec Inukjuak dual-energy domestic rate: %s", exc)

        # Rate G9 and Rate Flex G9 share the same demand/energy base
        def g9_common(text: str, structure: str, minimum_text: str) -> tuple[list[RateComponent], str, float]:
            demand = re.search(r"\$\s*(\d+\.\d+) per kilowatt of billing demand plus ", structure)
            excess = re.search(r"exceeds the real power during a consumption period, the excess is subject to a monthly charge of \$\s*(\d+\.\d+) per kilowatt", structure)
            ratchet = re.search(r"equal to (\d+(?:\.\d+)?)% of the maximum power demand during a consumption period that falls wholly within the winter period", minimum_text)
            if not (demand and excess and ratchet) or credit_clause not in structure:
                raise ValueError("Missing G9 demand charge, apparent-power excess, ratchet or credit reference")
            positive(demand.group(1), excess.group(1))
            if not 0 < float(ratchet.group(1)) <= 100:
                raise ValueError("Invalid minimum-demand ratchet")
            credits, losses = voltage_credits()
            components = [
                RateComponent("demand", "Demand Charge", float(demand.group(1)), "$/kW/month", demand_unit="kW",
                              notes="Per kilowatt of billing demand; billing demand is never less than the minimum billing demand (" + ratchet.group(1) + "% winter ratchet)."),
                RateComponent("demand", "Excess of Maximum Power Demand over Real Power", float(excess.group(1)), "$/kW/month", demand_unit="kW", sub_component="conditional",
                              notes="Applies only when the maximum power demand exceeds the real power during a consumption period; charged on the excess."),
                *credits,
            ]
            return components, losses, float(ratchet.group(1))

        selected, text = self._run_section(pages, r"Section\s+2\s+\W?\s*Rate G9\b", r"Application\s+4\.9\b")
        if selected:
            try:
                need(text, ("Application", "Structure of Rate G9", "Billing demand", "Minimum billing demand", "Short-term contract", "Installation of maximum-demand meter"))
                application = clause(text, r"Application\s+4\.9\s+(General Rate G9 applies.*?)Structure of Rate G9\s+4\.10", "G9 application")
                structure = clause(text, r"Structure of Rate G9\s+4\.10\s+(.*?)Billing demand\s+4\.11", "G9 structure")
                minimum = clause(text, r"Minimum billing demand\s+4\.12\s+(.*?)Short-term contract\s+4\.13", "G9 minimum demand")
                short = clause(text, r"Short-term contract\s+4\.13\s+(.*?)Installation of maximum-demand meter\s+4\.14", "G9 short-term terms")
                qualifying = re.search(r"maximum power demand has been at least ([\d,]+) kilowatts during one of the 12 consecutive monthly periods", application)
                energy = re.search(r"per kilowatt of billing demand plus " + cent + r" per kilowatthour\.", structure)
                surcharge = re.search(r"minimum monthly bill is increased by \$(\d+\.\d+)\. In the winter period, the monthly demand charge is increased by \$(\d+\.\d+)\.", short)
                if not (qualifying and energy and surcharge) or "not offered to independent producers" not in application:
                    raise ValueError("Missing G9 eligibility, energy price or short-term surcharge")
                positive(qualifying.group(1), energy.group(1), surcharge.group(1), surcharge.group(2))
                components, losses, _ = g9_common(text, structure, minimum)
                components.insert(1, RateComponent(
                    "energy", "Energy", round(float(energy.group(1)) / 100, 6), "$/kWh", notes="Single-price energy charge."))
                components.append(RateComponent(
                    "demand", "Short-Term Contract Winter Demand Surcharge", float(surcharge.group(2)), "$/kW/month", demand_unit="kW", sub_component="conditional",
                    season="winter", season_months=winter_months,
                    notes="Increase to the monthly demand charge in the winter period for a short-term contract (term under 12 monthly periods, at least 1 monthly period); prorated when a period overlaps the season boundary. " + short))
                notes = ("Medium-power general rate for limited use of billing demand. " + phase_minimum(structure) + " Minimum billing demand: " + minimum
                         + " Short-term contract minimum bill increase: $" + surcharge.group(1) + "." + losses)
                records.append(finish(selected, "G9", components, "commercial", tariff_name="Rate G9 - General Limited Demand Use", tariff_code="G9",
                                      sub_class="medium power, limited use of billing demand", demand_min_kw=float(qualifying.group(1).replace(",", "")),
                                      eligibility=application, notes=notes))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec Rate G9: %s", exc)

        # Flex G
        selected, text = self._run_section(pages, r"Section\s+4\s+\W?\s*Rate Flex G\b", r"Application\s+3\.17\b")
        if selected:
            try:
                need(text, ("Application", "Definitions", "Sign-up procedure", "Eligibility", "Conditions applicable to peak demand events",
                            "Peak demand event notifications", "Structure of Rate Flex G", "Termination"))
                application = clause(text, r"Application\s+3\.17\s+(Rate Flex G applies.*?)Definitions\s+3\.18", "Flex G application")
                signup = clause(text, r"Sign-up procedure\s+3\.19\s+(.*?)Eligibility\s+3\.20", "Flex G sign-up")
                eligibility = clause(text, r"Eligibility\s+3\.20\s+(For the contract to be eligible.*?)Conditions applicable to peak demand events\s+3\.21", "Flex G eligibility")
                structure = clause(text, r"Structure of Rate Flex G\s+3\.23\s+(.*?)Termination\s+3\.24", "Flex G structure")
                termination = clause(text, r"Termination\s+3\.24\s+(.*?)Installation of maximum-demand meter\s+3\.25", "Flex G termination")
                limit = re.search(r"maximum power demand for the contract is less than (\d+) kilowatts", application)
                hours, events, notice = peak_rules(text, structure)
                fixed = re.search(r"\$\s*(\d+\.\d+) system access charge plus ", structure)
                winter = re.search(winter_re, structure + "")
                summer = re.search(r"b\) During the summer period: " + cent + r" per kilowatthour\.", structure)
                if not (limit and fixed and winter and summer):
                    raise ValueError("Missing Flex G eligibility or charges")
                positive(limit.group(1), fixed.group(1), winter.group(1), winter.group(2), summer.group(1))
                if not all(item in eligibility for item in flex_checks) or "Winter Credit Option" not in eligibility or "Net Metering Option" not in eligibility \
                        or "cannot sign up again during that same winter or the following winter period" not in eligibility or "within 5 business days" not in signup:
                    raise ValueError("Missing Flex G eligibility or enrolment conditions")
                components = flex_components(text, structure, hours, events, notice, winter, [
                    RateComponent("fixed", "Monthly System Access", float(fixed.group(1)), "$/month", notes="Monthly system access charge; no multiplier applies.")])
                components.append(RateComponent(
                    "energy", "Summer Energy", round(float(summer.group(1)) / 100, 6), "$/kWh", season="summer", season_months=summer_months))
                notes = ("Optional peak-event rate for a Rate G-eligible contract. " + phase_minimum(structure) + " Sign-up: " + signup + " Eligibility: " + eligibility + " Termination: " + termination)
                records.append(finish(selected, "Flex G", components, "commercial", tariff_name="Rate Flex G - Small Power Peak Events", tariff_code="FLEX_G",
                                      sub_class="optional peak demand event rate", demand_max_kw=float(limit.group(1)), eligibility=application + " " + eligibility, notes=notes))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec Rate Flex G: %s", exc)

        # Flex M
        selected, text = self._run_section(pages, r"Section\s+7\s+\W?\s*Rate Flex M\b", r"Application\s+4\.29\b")
        if selected:
            try:
                need(text, ("Application", "Definitions", "Sign-up procedure", "Eligibility", "Conditions applicable to peak demand events",
                            "Peak demand event notifications", "Structure of Rate Flex M", "Billing demand", "Minimum billing demand", "Termination"))
                application = clause(text, r"Application\s+4\.29\s+(Rate Flex M is an experimental peak rate.*?)Definitions\s+4\.30", "Flex M application")
                signup = clause(text, r"Sign-up procedure\s+4\.31\s+(.*?)Eligibility\s+4\.32", "Flex M sign-up")
                eligibility = clause(text, r"Eligibility\s+4\.32\s+(For the contract to be eligible.*?)Conditions applicable to peak demand events\s+4\.33", "Flex M eligibility")
                structure = clause(text, r"Structure of Rate Flex M\s+4\.35\s+(.*?)Billing demand\s+4\.36", "Flex M structure")
                minimum = clause(text, r"Minimum billing demand\s+4\.37\s+(.*?)Limitation\s+4\.38", "Flex M minimum demand")
                termination = clause(text, r"Termination\s+4\.39\s+(.*?)Installation of maximum-demand meter\s+4\.40", "Flex M termination")
                hours, events, notice = peak_rules(text, structure)
                demand = re.search(r"\$\s*(\d+\.\d+) per kilowatt of billing demand plus ", structure)
                winter = re.search(winter_re, structure)
                summer = re.search(r"b\) During the summer period: " + cent + r" per kilowatthour for the first ([\d,]+) kilowatthours, and " + cent + r" per kilowatthour for the remaining consumption", structure)
                ratchet = re.search(r"equal to (\d+(?:\.\d+)?)% of the maximum power demand during a consumption period that falls wholly within the winter period", minimum)
                ceiling = re.search(r"minimum billing demand reaches or exceeds ([\d,]+) kilowatts, the contract ceases to be eligible", minimum)
                if not (demand and winter and summer and ratchet and ceiling) or credit_clause not in structure:
                    raise ValueError("Missing Flex M charges, ratchet, ceiling or credit reference")
                positive(demand.group(1), winter.group(1), winter.group(2), summer.group(1), summer.group(2), summer.group(3), ceiling.group(1))
                if not 0 < float(ratchet.group(1)) <= 100:
                    raise ValueError("Invalid Flex M ratchet")
                if not all(item in eligibility for item in flex_checks) or "Net Metering Option" not in eligibility or "by November 20" not in signup:
                    raise ValueError("Missing Flex M eligibility or enrolment conditions")
                credits, losses = voltage_credits()
                threshold = float(summer.group(2).replace(",", ""))
                components = [
                    RateComponent("demand", "Demand Charge", float(demand.group(1)), "$/kW/month", demand_unit="kW",
                                  notes=f"Per kilowatt of billing demand; never less than the minimum billing demand ({ratchet.group(1)}% winter ratchet)."),
                ]
                components.extend(flex_components(text, structure, hours, events, notice, winter, []))
                components.extend([
                    RateComponent("energy", "Summer First-Tier Energy", round(float(summer.group(1)) / 100, 6), "$/kWh",
                                  tier_number=1, tier_threshold=threshold, tier_unit="kWh/month", season="summer", season_months=summer_months),
                    RateComponent("energy", "Summer Remaining Energy", round(float(summer.group(3)) / 100, 6), "$/kWh",
                                  tier_number=2, tier_threshold=threshold, tier_unit="kWh/month", season="summer", season_months=summer_months),
                    *credits,
                ])
                notes = ("Experimental optional peak rate for a medium-power contract. " + phase_minimum(structure) + " Sign-up: " + signup + " Eligibility: " + eligibility
                         + " Minimum billing demand: " + minimum + " Termination: " + termination + losses)
                records.append(finish(selected, "Flex M", components, "commercial", tariff_name="Rate Flex M - Medium Power Peak Events", tariff_code="FLEX_M",
                                      sub_class="experimental optional peak demand event rate", demand_max_kw=float(ceiling.group(1).replace(",", "")),
                                      eligibility=application + " " + eligibility, notes=notes))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec Rate Flex M: %s", exc)

        # Flex G9
        selected, text = self._run_section(pages, r"Section\s+8\s+\W?\s*Rate Flex G9\b", r"Application\s+4\.41\b")
        if selected:
            try:
                need(text, ("Application", "Definitions", "Sign-up procedure", "Eligibility", "Conditions applicable to peak demand events",
                            "Peak demand event notifications", "Structure of Rate Flex G9", "Billing demand", "Minimum billing demand", "Termination"))
                application = clause(text, r"Application\s+4\.41\s+(Rate Flex G9 is an experimental peak rate.*?)Definitions\s+4\.42", "Flex G9 application")
                signup = clause(text, r"Sign-up procedure\s+4\.43\s+(.*?)Eligibility\s+4\.44", "Flex G9 sign-up")
                eligibility = clause(text, r"Eligibility\s+4\.44\s+(For the contract to be eligible.*?)Conditions applicable to peak demand events\s+4\.45", "Flex G9 eligibility")
                structure = clause(text, r"Structure of Rate Flex G9\s+4\.47\s+(.*?)Billing demand\s+4\.48", "Flex G9 structure")
                minimum = clause(text, r"Minimum billing demand\s+4\.49\s+(.*?)Limitation\s+4\.50", "Flex G9 minimum demand")
                termination = clause(text, r"Termination\s+4\.51\s+(.*?)Installation of a maximum-demand meter\s+4\.52", "Flex G9 termination")
                hours, events, notice = peak_rules(text, structure)
                winter = re.search(winter_re, structure)
                summer = re.search(r"b\) During the summer period: " + cent + r" per kilowatthour\.", structure)
                if not (winter and summer) or "by November 20" not in signup or not all(item in eligibility for item in flex_checks):
                    raise ValueError("Missing Flex G9 charges or eligibility")
                positive(winter.group(1), winter.group(2), summer.group(1))
                components, losses, _ = g9_common(text, structure, minimum)
                components[2:2] = flex_components(text, structure, hours, events, notice, winter, [])
                components.insert(4, RateComponent(
                    "energy", "Summer Energy", round(float(summer.group(1)) / 100, 6), "$/kWh", season="summer", season_months=summer_months))
                notes = ("Experimental optional peak rate for a medium-power contract with limited use of billing demand. " + phase_minimum(structure) + " Sign-up: " + signup
                         + " Eligibility: " + eligibility + " Minimum billing demand: " + minimum + " Termination: " + termination + losses)
                records.append(finish(selected, "Flex G9", components, "commercial", tariff_name="Rate Flex G9 - Limited Demand Peak Events", tariff_code="FLEX_G9",
                                      sub_class="experimental optional peak demand event rate", eligibility=application + " " + eligibility, notes=notes))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec Rate Flex G9: %s", exc)

        # Small- and medium-power dual-energy heating rates
        selected, text = self._run_section(
            pages, r"(?:CHAPTER 8\b|Section\s+1\s+\W?\s*Small\W?\s*and Medium\W?\s*Power Dual\W?Energy Rate)", r"Application\s+8\.1\b")
        if selected:
            try:
                need(text, ("Application", "Definitions", "Eligibility", "Characteristics of the dual-energy system", "Sign-up procedure", "Non-compliance", "Fraud"))
                application = clause(text, r"Application\s+8\.1\s+(The Small- and Medium-Power Dual-Energy Rate.*?)Definitions\s+8\.2", "dual-energy application")
                heating = self._period_months(text, "heating season", year)
                non_heating = self._period_months(text, "non-heating season", year)
                if sorted((heating + "," + non_heating).split(","), key=int) != [str(month) for month in range(1, 13)]:
                    raise ValueError("Dual-energy seasons do not cover the year")
                eligibility = clause(text, r"Eligibility\s+8\.3\s+(For the contract to be eligible.*?)Characteristics of the dual-energy system\s+8\.4", "dual-energy eligibility")
                equipment = clause(text, r"Characteristics of the dual-energy system\s+8\.4\s+(.*?)Recovery after a power failure\s+8\.5", "dual-energy equipment")
                signup = clause(text, r"Sign-up procedure\s+8\.6\s+(.*?)Non-compliance\s+8\.7", "dual-energy sign-up")
                noncompliance = clause(text, r"Non-compliance\s+8\.7\s+(.*?)Fraud\s+8\.8", "dual-energy non-compliance")
                fraud = clause(text, r"Fraud\s+8\.8\s+(.*?)(?:Structure of the Small-Power Dual-Energy Rate\s+8\.9|$)", "dual-energy fraud rule")
                if not all((
                    "metered separately" in eligibility, "must not benefit" in eligibility,
                    "must not be supplied by an off-grid system" in eligibility,
                    "automatic switch" in equipment and "temperature gauge" in equipment and "supplied and installed by Hydro-Qu" in equipment,
                    "Certificate of Eligibility" in signup, "10 business days" in noncompliance, "365 days" in fraud,
                    "only applies to the electricity consumed by the dual-energy system for space heating" in application,
                )):
                    raise ValueError("Missing dual-energy eligibility or equipment conditions")
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec dual-energy conditions: %s", exc)
            else:
                heat_re = (r"a\) During the heating season: " + cent + r" per kilowatthour when the temperature is equal to or higher than -(\d+)\u00b0C or -(\d+)\u00b0C, "
                           r"depending on the climate zones defined by Hydro-Qu\S+bec, and " + cent + r" per kilowatthour when the temperature is below -(\d+)\u00b0C or -(\d+)\u00b0C, as applicable\.? or b\) During the non-heating season: ")
                shared = ("Applies only to electricity used by the dual-energy system for space heating; other consumption is billed under a separate Rate G, M or G9 contract. Eligibility: "
                          + eligibility + " Equipment: " + equipment + " Sign-up: " + signup + " Non-compliance: " + noncompliance + " Fraud: " + fraud)
                variants = (
                    ("small", r"Structure of the Small-Power Dual-Energy Rate\s+8\.9\s+(.*?)Structure of the Medium-Power Dual-Energy Rate\s+8\.10",
                     "Small-Power Dual-Energy Rate (Space Heating)", "DUAL_ENERGY_SMALL", "small power"),
                    ("medium", r"Structure of the Medium-Power Dual-Energy Rate\s+8\.10\s+(.*?)(?:Structure of the Medium-Power Dual-Energy Rate for contracts with low load factors\s+8\.11|$)",
                     "Medium-Power Dual-Energy Rate (Space Heating)", "DUAL_ENERGY_MEDIUM", "medium power"),
                    ("low", r"Structure of the Medium-Power Dual-Energy Rate for contracts with low load factors\s+8\.11\s+(.*?)Billing demand\s+8\.12",
                     "Medium-Power Dual-Energy Rate - Low Load Factor (Space Heating)", "DUAL_ENERGY_MEDIUM_LLF", "medium power, limited use of billing demand"),
                )
                for kind, pattern, name, code, sub_class in variants:
                    try:
                        structure = clause(text, pattern, f"dual-energy {kind} structure")
                        heat = re.search(heat_re, structure)
                        if not heat:
                            raise ValueError("Missing heating-season temperature prices")
                        zones = (heat.group(2), heat.group(3))
                        if zones != (heat.group(5), heat.group(6)) or len(set(zones)) != 2 or min(int(zone) for zone in zones) <= 0:
                            raise ValueError("Inconsistent temperature zones")
                        positive(heat.group(1), heat.group(4))
                        zone_label = f"-{zones[0]} C or -{zones[1]} C depending on Hydro-Quebec climate zone"
                        components = [
                            RateComponent("energy", "Heating Season Electric Mode Energy (at or above switching temperature)", round(float(heat.group(1)) / 100, 6), "$/kWh",
                                          season="heating", season_months=heating, tou_period="outdoor temperature at or above " + zone_label,
                                          notes="Climate zone is not assumed. Temperature-based, not clock-based."),
                            RateComponent("energy", "Heating Season Fuel Mode Energy (below switching temperature)", round(float(heat.group(4)) / 100, 6), "$/kWh",
                                          season="heating", season_months=heating, tou_period="outdoor temperature below " + zone_label,
                                          notes="Energy consumed when the outdoor temperature is below the zone threshold."),
                        ]
                        extra_notes, demand_min, demand_max = "", None, None
                        if kind == "low":
                            non = re.search(r"b\) During the non-heating season: \$\s*(\d+\.\d+) per kilowatt of billing demand, plus " + cent + r" per kilowatthour\.", structure)
                            excess = re.search(r"in kilovoltamperes exceeds the highest real power demand during a consumption period included in whole or in part during a non-heating season, the excess is subject to a monthly charge of \$\s*(\d+\.\d+) per kilowatt", structure)
                            qualifying = re.search(r"maximum power demand has been at least (\d+) kilowatts during the non-heating season", structure)
                            billing_rule = clause(text, r"Billing demand\s+8\.12\s+(.*?)Division of consumption period\s+8\.13", "dual-energy billing demand")
                            division = clause(text, r"Division of consumption period\s+8\.13\s+(.*?)Termination\s+8\.14", "dual-energy period division")
                            if not (non and excess and qualifying) or "During the heating season, no billing demand applies" not in billing_rule:
                                raise ValueError("Missing low-load-factor non-heating charges or billing-demand rule")
                            positive(non.group(1), non.group(2), excess.group(1), qualifying.group(1))
                            components.extend([
                                RateComponent("demand", "Non-Heating Season Demand Charge", float(non.group(1)), "$/kW/month", demand_unit="kW",
                                              season="non-heating", season_months=non_heating, notes=billing_rule),
                                RateComponent("energy", "Non-Heating Season Energy", round(float(non.group(2)) / 100, 6), "$/kWh", season="non-heating", season_months=non_heating),
                                RateComponent("demand", "Excess of Apparent over Real Power Demand (non-heating)", float(excess.group(1)), "$/kW/month", demand_unit="kW",
                                              sub_component="conditional", season="non-heating", season_months=non_heating,
                                              notes="Applies only when the kVA demand exceeds the highest real power demand in a period touching the non-heating season."),
                            ])
                            demand_min = float(qualifying.group(1))
                            extra_notes = " Billing demand: " + billing_rule + " Division: " + division
                        else:
                            if kind == "small":
                                non = re.search(r"b\) During the non-heating season: \$\s*(\d+\.\d+) per kilowatt of billing demand in excess of (\d+) kilowatts plus " + cent + r" per kilowatthour for the first ([\d,]+) kilowatthours, and " + cent + r" per kilowatthour for the remaining energy consumption", structure)
                                limit = re.search(r"maximum power demand was less than (\d+) kilowatts during the non-heating season", structure)
                                if not (non and limit):
                                    raise ValueError("Missing small-power non-heating charges")
                                positive(non.group(1), non.group(2), non.group(3), non.group(4), non.group(5), limit.group(1))
                                free_kw, threshold, tier1, tier2 = float(non.group(2)), non.group(4), non.group(3), non.group(5)
                                demand_max = float(limit.group(1))
                                demand_value = non.group(1)
                            else:
                                non = re.search(r"b\) During the non-heating season: \$\s*(\d+\.\d+) per kilowatt of billing demand plus " + cent + r" per kilowatthour for the first ([\d,]+) kilowatthours, and " + cent + r" per kilowatthour for the remaining energy consumption", structure)
                                limit = re.search(r"maximum power demand was at least (\d+) kilowatts during the non-heating season", structure)
                                if not (non and limit):
                                    raise ValueError("Missing medium-power non-heating charges")
                                positive(non.group(1), non.group(2), non.group(3), non.group(4), limit.group(1))
                                free_kw, threshold, tier1, tier2 = None, non.group(3), non.group(2), non.group(4)
                                demand_min = float(limit.group(1))
                                demand_value = non.group(1)
                            if credit_clause not in structure:
                                raise ValueError("Missing supply-voltage credit reference")
                            components.extend([
                                RateComponent("demand", "Non-Heating Season Demand Charge", float(demand_value), "$/kW/month", demand_unit="kW",
                                              demand_threshold_kw=free_kw, season="non-heating", season_months=non_heating,
                                              notes="Per kilowatt of billing demand" + (f" in excess of {int(free_kw)} kW." if free_kw else ".")),
                                RateComponent("energy", "Non-Heating Season First-Tier Energy", round(float(tier1) / 100, 6), "$/kWh", tier_number=1,
                                              tier_threshold=float(threshold.replace(",", "")), tier_unit="kWh/month", season="non-heating", season_months=non_heating),
                                RateComponent("energy", "Non-Heating Season Remaining Energy", round(float(tier2) / 100, 6), "$/kWh", tier_number=2,
                                              tier_threshold=float(threshold.replace(",", "")), tier_unit="kWh/month", season="non-heating", season_months=non_heating),
                            ])
                        if kind == "low" and credit_clause not in structure:
                            raise ValueError("Missing supply-voltage credit reference")
                        credits, losses = voltage_credits()
                        components.extend(credits)
                        notes = f"Dual-energy heating rate, {sub_class} contract. Heating season Oct-Apr and non-heating season May-Sep as defined by the tariff. " + shared + extra_notes + losses
                        records.append(finish(selected, f"Dual-Energy {kind}", components, "commercial", tariff_name=name, tariff_code=code, sub_class="dual-energy heating, " + sub_class,
                                              demand_min_kw=demand_min, demand_max_kw=demand_max, eligibility=application + " " + eligibility, notes=notes))
                    except (ValueError, IndexError) as exc:
                        self.logger.warning("Incomplete Hydro-Quebec dual-energy %s-power rate: %s", kind, exc)

        # Closed Winter Credit Option for Rate G
        selected, text = self._run_section(pages, r"Section\s+3\s+\W?\s*Winter Credit Option for Rate G Customers", r"Application\s+3\.9\b")
        if selected:
            try:
                need(text, ("Application", "Definitions", "Sign-up procedure", "Eligibility", "Conditions applicable to peak demand events",
                            "Peak demand event notifications", "Credit", "Termination"))
                application = clause(text, r"Application\s+3\.9\s+(The Winter Credit Option.*?)Definitions\s+3\.10", "Winter Credit G application")
                rules = clause(text, r"Definitions\s+3\.10\s+(.*?)Sign-up procedure\s+3\.11", "Winter Credit G definitions")
                signup = clause(text, r"Sign-up procedure\s+3\.11\s+(.*?)Eligibility\s+3\.12", "Winter Credit G sign-up")
                eligibility = clause(text, r"Eligibility\s+3\.12\s+(To be eligible for this option.*?)Conditions applicable to peak demand events\s+3\.13", "Winter Credit G eligibility")
                notifications = clause(text, r"Peak demand event notifications\s+3\.14\s+(.*?)Credit\s+3\.15", "Winter Credit G notifications")
                termination = clause(text, r"Termination\s+3\.16\s+(.*)$", "Winter Credit G termination")
                cutoff = re.search(r"reserved for the Rate G contract to which it applied up to ([A-Za-z]+ \d{1,2}, \d{4})", application)
                limit = re.search(r"maximum power demand under the contract is less than (\d+) kilowatts", application)
                hours, events, _ = peak_rules(text, "")
                credit = re.search(r"entitled to the following credit: " + cent + r" per kilowatthour of energy curtailed\. (No credit is given for a peak demand event .*?)Termination\s+3\.16", text)
                if not (cutoff and limit and credit):
                    raise ValueError("Missing Winter Credit G closed-enrolment date, demand limit or credit")
                closed_on = datetime.strptime(cutoff.group(1), "%B %d, %Y").date().isoformat()
                if closed_on > self.now_iso()[:10]:
                    raise ValueError("Winter Credit G cutoff is in the future")
                positive(credit.group(1), limit.group(1))
                if not all((
                    "single communicating meter" in eligibility, "must not be supplied by an off-grid system" in eligibility,
                    "must not be signed up for a Net Metering Option" in eligibility,
                    "reference energy:" in rules and "reference period:" in rules, "temperature adjustment:" in rules and "This value cannot be negative" in rules,
                    "excluding the minimum and maximum values for each hour" in rules, "5 weekdays or 5 weekend days" in rules,
                    "before 15:00 on the day prior" in notifications, "notification may be sent after 15:00" in notifications, "within 5 business days" in signup,
                )):
                    raise ValueError("Missing Winter Credit G eligibility conditions")
                peak_hours = f"{hours.group(1)}-{hours.group(2)},{hours.group(3)}-{hours.group(4)}"
                components = [RateComponent(
                    "rebate", "Winter Credit per kWh Curtailed", -round(float(credit.group(1)) / 100, 6), "$/kWh curtailed",
                    sub_component="conditional", season="winter", season_months=winter_months, tou_period="peak demand event", tou_hours=peak_hours,
                    notes=f"Credit applies only to energy curtailed during notified peak demand events (peak hours {peak_hours}, excluding {hours.group(5)}). " + credit.group(2).strip(),
                )]
                notes = (f"Closed to new enrolment: {application} Eligibility: {eligibility} Peak demand events: at most {events.group(1)} per day, {events.group(2)} h apart, "
                         f"{events.group(3)} h each and {events.group(4)} h per winter. Credit is conditional on enrolment, curtailment and notified events; Rate G charges remain separate. "
                         f"Closed-enrolment cutoff in source: {closed_on}. Source calculation rules (not calculated here): " + rules + " Notifications: " + notifications
                         + " Sign-up: " + signup + " Termination: " + termination)
                records.append(finish(selected, "Winter Credit Option (Rate G)", components, "commercial", tariff_name="Winter Credit Option - Rate G", tariff_code="WINTER_CREDIT_G",
                                      sub_class="closed to new enrollment", demand_max_kw=float(limit.group(1)), eligibility=application + " " + eligibility, notes=notes))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec Winter Credit Option for Rate G: %s", exc)

        # Net metering Option I (grid-connected)
        selected, text = self._run_section(pages, r"Section\s+6\s+\W?\s*Net Metering for Customer\W?Generators\s*\W?\s*Option I(?!I)", r"Application\s+2\.45\b")
        if selected:
            try:
                need(text, ("Application", "Definitions", "Eligibility", "Billing", "Surplus bank restrictions", "Restrictions", "Termination"))
                application = clause(text, r"Application\s+2\.45\s+(The Net Metering Option.*?)Definitions\s+2\.46", "net metering application")
                eligibility = clause(text, r"Eligibility\s+2\.48\s+(To be eligible.*?)Sign-up date\s+2\.49", "net metering eligibility")
                billing_rule = clause(text, r"Billing\s+2\.50\s+(.*?)Surplus bank restrictions\s+2\.51", "net metering billing")
                bank = clause(text, r"Surplus bank restrictions\s+2\.51\s+(.*?)Restrictions\s+2\.52", "net metering surplus-bank rules")
                price = re.search(r"credited the balance at the price of the average cost of electricity supply, i\.e\., " + cent + r" per kilowatthour", bank)
                g_selected, g_text = self._run_section(pages, r"Section\s+2\s+\W?\s*Net Metering for Customer\W?Generators\s*\W?\s*Option I(?!I)", r"Application\s+3\.8\b")
                if not price or "Rate D, Rate DM or Rate DP" not in application or "1,000 kilowatts" not in application \
                        or "The amount billed cannot be negative" not in billing_rule or not re.search(r"applies to the Rate G contract of a customer whose maximum self-generation capacity does not exceed 1,000 kilowatts", g_text):
                    raise ValueError("Missing net metering price, applicability or billing rule")
                positive(price.group(1))
                components = [RateComponent(
                    "rebate", "Surplus Bank Reset Credit (average cost of supply)", -round(float(price.group(1)) / 100, 6), "$/kWh of surplus-bank balance",
                    sub_component="conditional", notes="Credited only when the surplus bank is reset to zero or the option ends. " + bank)]
                notes = ("Billing option for customer-generators; the system access charge and the amount for electricity delivered follow the applicable rate, minus the surplus-bank balance. "
                         + "Billing: " + billing_rule + " Eligibility: " + eligibility + " Rate G application (Chapter 3 Section 2): " + g_text)
                records.append(finish(selected + g_selected, "Net Metering Option I", components, "residential", tariff_name="Net Metering Option I - Customer-Generators",
                                      tariff_code="NET_METERING_I", sub_class="net metering option (also Rate G)", eligibility=application + " " + eligibility, notes=notes))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec Net Metering Option I: %s", exc)

        m_selected, m_text = self._run_section(pages, r"Section\s+6\s+\W?\s*Net Metering for Customer\W?Generators\s*\W?\s*Option I(?!I)", r"Application\s+4\.28\b")
        if m_selected:
            try:
                common_selected, common_text = self._run_section(pages, r"Section\s+6\s+\W?\s*Net Metering for Customer\W?Generators\s*\W?\s*Option I(?!I)", r"Application\s+2\.45\b")
                need(common_text, ("Application", "Definitions", "Eligibility", "Billing", "Surplus bank restrictions", "Restrictions", "Termination"))
                application = clause(common_text, r"Application\s+2\.45\s+(The Net Metering Option.*?)Definitions\s+2\.46", "Option I application")
                eligibility = clause(common_text, r"Eligibility\s+2\.48\s+(To be eligible.*?)Sign-up date\s+2\.49", "Option I eligibility")
                billing_rule = clause(common_text, r"Billing\s+2\.50\s+(.*?)Surplus bank restrictions\s+2\.51", "Option I billing")
                bank = clause(common_text, r"Surplus bank restrictions\s+2\.51\s+(.*?)Restrictions\s+2\.52", "Option I surplus bank")
                price = re.search(r"credited the balance at the price of the average cost of electricity supply, i\.e\., " + cent + r" per kilowatthour", bank)
                m_application = re.search(r"Application\s+4\.28\s+(Net Metering Option I, described in Section 6 of Chapter 2, applies to the Rate M contract of a customer whose maximum self-generation capacity does not exceed 1,000 kilowatts\.)", m_text)
                if not common_selected or not price or not m_application or "1,000 kilowatts" not in application \
                        or "The amount billed cannot be negative" not in billing_rule:
                    raise ValueError("Missing Rate M net metering applicability, credit or billing rule")
                positive(price.group(1))
                components = [RateComponent(
                    "rebate", "Surplus Bank Reset Credit (average cost of supply)", -round(float(price.group(1)) / 100, 6), "$/kWh of surplus-bank balance",
                    sub_component="conditional", notes="Credited only when the surplus bank is reset to zero or the option ends. " + bank)]
                notes = ("Rate M charges remain separate; the applicable rate governs electricity delivered minus the surplus-bank balance. "
                         + "Billing: " + billing_rule + " Eligibility: " + eligibility + " Rate M application: " + m_application.group(1))
                records.append(finish(common_selected + m_selected, "Net Metering Option I (Rate M)", components, "commercial",
                                      tariff_name="Net Metering Option I - Rate M Customer-Generators", tariff_code="NET_METERING_I_M",
                                      sub_class="Rate M net metering option", eligibility=m_application.group(1) + " " + eligibility, notes=notes))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec Net Metering Option I for Rate M: %s", exc)

        # Net metering Option III (off-grid)
        selected, text = self._run_section(pages, r"Section\s+3\s+\W?\s*Net Metering for Customer\W?Generators\s*\W?\s*Option I\s?I\s?I", r"Application\s+9\.12\b")
        if selected:
            try:
                need(text, ("Application", "Definitions", "Eligibility", "Surplus bank", "Billing", "Termination"))
                application = clause(text, r"Application\s+9\.12\s+(The Net Metering Option.*?)Definitions\s+9\.13", "Option III application")
                eligibility = clause(text, r"Eligibility\s+9\.15\s+(To be eligible.*?)Sign-up date\s+9\.16", "Option III eligibility")
                bank = clause(text, r"Surplus bank\s+9\.17\s+(.*?)Billing\s+9\.18", "Option III surplus bank")
                billing_rule = clause(text, r"Billing\s+9\.18\s+(.*?)Surplus bank restrictions\s+9\.19", "Option III billing")
                rules = clause(text, r"Surplus bank restrictions\s+9\.19\s+(.*?)Termination\s+9\.20", "Option III bank resets")
                prices = re.search(
                    r"multiplied by: " + cent + r" per kilowatthour when the electricity is produced by a heavy diesel power plant, or " + cent
                    + r" per kilowatthour when the electricity is produced by a light diesel power plant, or " + cent
                    + r" per kilowatthour when the electricity is produced by an arctic diesel power plant", bank)
                if not prices or "Rate D, Rate DM, Rate DN or Rate G" not in application or "off-grid system" not in application:
                    raise ValueError("Missing off-grid net metering prices or applicability")
                positive(*prices.groups())
                names = ("heavy diesel", "light diesel", "arctic diesel")
                components = [
                    RateComponent("rebate", f"Injected Energy Credit ({label} plant)", -round(float(value) / 100, 6), "$/kWh injected", sub_component="conditional",
                                  notes="Credited to the surplus bank per kWh injected; the rate depends on the type of power plant producing the off-grid electricity. " + rules)
                    for label, value in zip(names, prices.groups())
                ]
                notes = "Off-grid net metering for customer-generators. Eligibility: " + eligibility + " Billing: " + billing_rule + " Surplus bank resets: " + rules
                records.append(finish(selected, "Net Metering Option III", components, "residential", tariff_name="Net Metering Option III - Off-Grid Customer-Generators",
                                      tariff_code="NET_METERING_III", sub_class="off-grid net metering option (also Rate G)", eligibility=application + " " + eligibility, notes=notes))
            except (ValueError, IndexError) as exc:
                self.logger.warning("Incomplete Hydro-Quebec Net Metering Option III: %s", exc)
        return records

    # ── Rate D parser ─────────────────────────────────────────

    def _parse_rate_d(self, pdf_text: str) -> Optional[TariffRecord]:
        """Parse Rate D (Domestic/Residential) from PDF text."""
        # The "Structure of Rate D" section carries the actual charges; the
        # plain "Rate D" heading also appears in the table of contents.
        heading = re.search(r"Structure of Rate D\s+2\.5\b", pdf_text)
        if not heading:
            self.logger.warning("Could not find Rate D section in PDF")
            return None
        section = pdf_text[heading.start():heading.start() + 1200]

        # Fixed charge is worded "XX.XXX¢ system access charge for each day".
        fixed_match = re.search(
            r'([\d.]+)\s*[¢c]\s*system access charge', section, re.IGNORECASE
        )
        if not fixed_match:
            fixed_match = re.search(
                r'([\d.]+)\s*[¢c][^.]{0,40}(?:per day|for each day|a day)', section, re.IGNORECASE
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
        idx = pdf_text.find("Structure of Rate G")
        if idx == -1:
            self.logger.warning("Could not find Rate G section in PDF")
            return None
        section = pdf_text[idx:idx + 900]

        # Fixed charge is worded "$XX.XXX system access charge".
        fixed_match = re.search(
            r'\$([\d.]+)\s*system access charge', section, re.IGNORECASE
        )
        fixed_per_month = float(fixed_match.group(1)) if fixed_match else None

        # Demand charge: "$XX.XXX per kilowatt of billing demand in excess of 50 kilowatts"
        demand_match = re.search(
            r'\$([\d.]+)\s*per\s*kilowatt', section, re.IGNORECASE
        )
        demand_charge = float(demand_match.group(1)) if demand_match else None

        # Energy rates: "XX.XXX¢ per kilowatthour" (the cent glyph varies by PDF encoding)
        energy_matches = re.findall(
            r'([\d.]+)\s*[^\d\s]{0,2}\s*per\s*kilowatthour', section, re.IGNORECASE
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
        idx = pdf_text.find("Structure of Rate M")
        if idx == -1:
            self.logger.warning("Could not find Rate M section in PDF")
            return None
        section = pdf_text[idx:idx + 900]

        # Demand charge: "$XX.XXX per kilowatt of billing demand"
        demand_match = re.search(
            r'\$([\d.]+)\s*per\s*kilowatt', section, re.IGNORECASE
        )
        demand_charge = float(demand_match.group(1)) if demand_match else None

        # Energy rates: "X.XXX¢ per kilowatthour" (the cent glyph varies by PDF encoding)
        energy_matches = re.findall(
            r'([\d.]+)\s*[^\d\s]{0,2}\s*per\s*kilowatthour', section, re.IGNORECASE
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
