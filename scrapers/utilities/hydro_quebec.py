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
