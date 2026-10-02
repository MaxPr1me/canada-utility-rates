"""
nova_scotia_power.py — Scraper for Nova Scotia Power electricity rates (Nova Scotia).

Nova Scotia Power Inc. (NSPI) is the primary electricity provider in
Nova Scotia, an investor-owned utility (Emera subsidiary). Residential
coverage includes standard, equipment-based TOD and conditional pilot phases.
Base energy and mandatory riders are parsed separately from the tariff book.

Official source (landing page — no rate values):
  https://www.nspower.ca/products-services/rate-information

Residential rates page (contains actual values):
  https://www.nspower.ca/your-home/residential-rates/standard-residential

Business rates page (commercial rate classes):
  https://www.nspower.ca/your-business/save-money-energy/business-rates

Regulated by: Nova Scotia Utility and Review Board (NSUARB)
"""

from __future__ import annotations

import logging
import re
from dataclasses import replace
from datetime import date, datetime
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html,
    find_text_near_label,
    extract_rate_from_text,
    extract_effective_date,
    extract_pdf_pages,
    find_pdf_links,
    DocumentPage,
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
BUSINESS_URL = (
    "https://www.nspower.ca/your-business/save-money-energy/business-rates"
)
RESIDENTIAL_PRODUCTS = {
    "standard": RESIDENTIAL_URL,
    "tod": RESIDENTIAL_URL.rsplit("/", 1)[0] + "/time-of-day",
    "tou": RESIDENTIAL_URL.rsplit("/", 1)[0] + "/time-of-use",
    "cpp": RESIDENTIAL_URL.rsplit("/", 1)[0] + "/critical-peak",
}
TARIFF_URL = "https://www.nspower.ca/docs/default-source/regulatory/tariff-book-2026.pdf"

# Known rate values — used as seed/fallback data.
SEED_RESIDENTIAL = {
    "effective_date": "2026-01-01",
    "source_url": RESIDENTIAL_URL,
    "energy_rate": 0.18187,           # $/kWh
    "basic_charge_per_month": 19.17,  # $/month
}

SEED_RATE10 = {
    "effective_date": "2026-01-01",
    "source_url": BUSINESS_URL,
    "base_charge": 22.00,             # $/month
    "energy_tier1": 0.19804,          # $/kWh — first 200 kWh/month
    "energy_tier2": 0.17997,          # $/kWh — balance
    "tier1_threshold_kwh": 200,
    "eligibility": "Under 45,000 kWh/year",
}

SEED_RATE11 = {
    "effective_date": "2026-01-01",
    "source_url": BUSINESS_URL,
    "demand_charge": 9.809,           # $/kW
    "energy_tier1": 0.15738,          # $/kWh — first 200 kWh per kW of max demand
    "energy_tier2": 0.12674,          # $/kWh — balance
    "tier1_threshold_desc": "First 200 kWh per kW of maximum demand",
    "eligibility": "Annual consumption ≥32,000 kWh; billing demand <2,000 kVA",
}

SEED_RATE12 = {
    "effective_date": "2026-01-01",
    "source_url": BUSINESS_URL,
    "demand_charge": 11.174,          # $/kVA
    "energy_rate": 0.11780,           # $/kWh — flat
    "minimum_charge": 22.00,          # $/month
    "eligibility": "Billing demand ≥2,000 kVA or 1,800 kW",
}

# Commercial rate classes published on the business rates page.
# (code, tariff_name, sub_class, rate_structure, page section header)
_COMMERCIAL_RATES: list[tuple[str, str, str, str, str]] = [
    ("10", "Small Commercial", "small commercial", "tiered",
     "Small Commercial (Small General Tariff): Rate 10"),
    ("11", "Commercial General Demand", "general demand", "demand",
     "Commercial General Demand: Rate 11"),
    ("12", "Large Commercial", "large commercial", "demand",
     "Large Commercial (Large General Tariff): Rate 12"),
]


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
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    # ── Live scraping ────────────────────────────────────────────

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Keep independent residential and business results with per-class fallbacks."""
        live_records = self._try_live_residential()
        try:
            live_records.extend(self._try_live_commercial() or [])
        except (ValueError, TypeError, IndexError) as exc:
            self.logger.warning("NSPower business parse failed; retaining residential results: %s", exc)
        if not live_records:
            return None
        covered = {record.tariff_name for record in live_records}
        fallback = [record for record in self._seed_data() if record.tariff_name not in covered]
        return self.mark_live_parsed(live_records) + (self.mark_fallback(fallback) if fallback else [])

    def _try_live_residential(self) -> list[TariffRecord]:
        products = {}
        for kind, url in RESIDENTIAL_PRODUCTS.items():
            try:
                products[kind] = self.fetch_page(url)
            except Exception as exc:
                self.logger.warning("NSPower residential product unavailable %s: %s", kind, exc)
        try:
            links = find_pdf_links(parse_html(products.get("standard", "")), base_url=RESIDENTIAL_URL)
            candidates = [url for url in dict.fromkeys(links) if "tariff-book" in url.lower()]
            if len(candidates) > 1:
                raise ValueError("Ambiguous current tariff books")
            source_url = candidates[0] if candidates else TARIFF_URL
            return self._parse_residential_tariffs(extract_pdf_pages(self.fetch_bytes(source_url)), products, source_url)
        except Exception as exc:
            self.logger.warning("NSPower residential tariff unavailable: %s", exc)
            return []

    def _parse_residential_tariffs(
        self, pages: list[DocumentPage], products: dict[str, str], source_url: str,
    ) -> list[TariffRecord]:
        """Parse the current approved book, separating tariff phases and rider totals."""
        product_text = {kind: parse_html(html).get_text(" ", strip=True) for kind, html in products.items()}
        cover = next((page.text for page in pages if re.match(r"Tariffs\s+[A-Za-z]+\s+\d{4}", page.text)), "")
        publication = re.search(r"Tariffs\s+([A-Za-z]+)\s+(\d{4})", cover)
        if not publication or "Approved by" not in cover:
            return []
        year = int(publication.group(2))
        dates = set()
        for text in product_text.values():
            match = re.search(r"Rates updated as of ([A-Za-z]+ \d{1,2}, \d{4})", text)
            if match:
                effective = extract_effective_date("Effective " + match.group(1))
                if effective and datetime.strptime(effective, "%Y-%m-%d").strftime("%B %Y") == f"{publication.group(1)} {year}":
                    dates.add(effective)
        if len(dates) != 1:
            return []
        effective = next(iter(dates))
        today = self.now_iso()[:10]
        year_end = date(year, 12, 31).isoformat()
        if not effective <= today <= year_end:
            return []

        titles = {
            "DOMESTIC SERVICE": ("standard", "02, 03, 04"),
            "DOMESTIC SERVICE TIME-OF-DAY": ("tod", "05, 06"),
            "DOMESTIC SERVICE TIME OF USE": ("tou", "80"),
            "DOMESTIC SERVICE CRITICAL PEAK PRICING": ("cpp", "70"),
        }
        sections: dict[str, list[tuple[int, int, DocumentPage]]] = {}
        for page in pages:
            text = re.sub(r"\s+", " ", page.text)
            header = re.match(r"(?:SCHEDULE A )?(DOMESTIC SERVICE.*?) TARIFF(?: \(OPTIONAL\))? Page (\d+) of (\d+)", text)
            if header and header.group(1) in titles:
                kind, codes = titles[header.group(1)]
                if re.search(r"Rate Codes? " + re.escape(codes) + r"\b", text):
                    sections.setdefault(kind, []).append((int(header.group(2)), int(header.group(3)), page))

        def amounts(row: str) -> list[float]:
            values = re.findall(r"(?<![\w.])(\(?-?\d+\.\d+\)?)(?![\w.])", row)
            return [-float(value[1:-1]) if value.startswith("(") and value.endswith(")") else float(value) for value in values]

        def rider_row(heading: str, count: int) -> tuple[list[float], str]:
            selected = [page for page in pages if page.text.startswith(heading)]
            text = re.sub(r"\s+", " ", "\n".join(page.text for page in selected))
            current = re.search(rf"\b{year}\b(.*?)(?:\b{year + 1}\b|$)", text)
            row = re.search(r"Domestic Service,(.*?)Small General", current.group(1)) if current else None
            if not row or not re.search(r"cents per\s+(?:kWh|kilowatt)", text, re.I):
                raise ValueError(f"Missing domestic rider row: {heading}")
            values = amounts(row.group(1))
            if len(values) != count:
                raise ValueError(f"Incomplete rider columns: {heading}")
            for label in ("Time-of-Day", "Time of Use", "Critical Peak"):
                normalized = re.sub(r"\s+", " ", re.sub(r"\d+\.\d+", "", row.group(1))).replace("Time-of-Use", "Time of Use")
                if label not in normalized:
                    raise ValueError(f"Missing rider class applicability: {heading}")
            detail = heading + "; PDF pages " + ", ".join(str(page.page_number) for page in selected)
            return values, detail

        try:
            fam, fam_detail = rider_row("FUEL ADJUSTMENT MECHANISM (FAM) TARIFF", 2)
            dsm, dsm_detail = rider_row("DEMAND SIDE MANAGEMENT COST RECOVERY RIDER", 3)
            storm, storm_detail = rider_row("STORM COST RECOVERY RIDER", 1)
            if abs(sum(dsm[:2]) - dsm[2]) > 0.001 or fam[0] != fam[1]:
                raise ValueError("Changed domestic rider breakdown")
        except ValueError as exc:
            self.logger.warning("NSPower residential riders: %s", exc)
            return []
        riders = [
            RateComponent("rider", "FAM Actual/Balance Adjustment (Combined)", round(fam[-1] / 100, 6), "$/kWh",
                          source_detail=fam_detail, effective_date=effective),
            RateComponent("rider", "DSM Cost Recovery Rider", round(dsm[-1] / 100, 6), "$/kWh",
                          source_detail=dsm_detail, effective_date=date(year, 1, 1).isoformat(),
                          notes=f"Combined PCR {dsm[0]} and BA {dsm[1]} cents/kWh; do not add the subcomponents again."),
            RateComponent("rider", "Storm Cost Recovery Rider", round(storm[0] / 100, 6), "$/kWh",
                          source_detail=storm_detail, effective_date=effective),
        ]
        for component in riders:
            component.source_url = source_url
            component.end_date = year_end

        def numeric_line(text: str, count: int) -> tuple[list[float], str]:
            for match in re.finditer(r"(?m)^\s*(\d+\.\d+(?:[ \t]+\d+\.\d+)*)[ \t]*$", text):
                values = amounts(match.group(1))
                if len(values) == count:
                    return values, text[:match.start()]
            raise ValueError("Missing complete energy rate row")

        def current_charge(text: str, heading: str) -> float:
            section = text.split(heading, 1)[1].split(f"Effective January 1, {year + 1}", 1)[0]
            matches = re.findall(r"\$(\d+(?:\.\d+)?)", section)
            if "per month" not in section or re.search(r"-\s*\$|\$\s*-|\(\s*\$", section) or len(matches) != 1 or float(matches[0]) <= 0:
                raise ValueError("Missing current monthly charge")
            return float(matches[0])

        records: list[TariffRecord] = []
        for kind, name, code in (
            ("standard", "Domestic Service", "02/03/04"),
            ("tod", "Domestic Service Time-of-Day (Rates 05/06)", "05/06"),
            ("tou", "Domestic Service Time-of-Use Pilot (Rate 80)", "80"),
            ("cpp", "Domestic Service Critical Peak Pricing Pilot (Rate 70)", "70"),
        ):
            selected = sorted(sections.get(kind, []), key=lambda item: item[0])
            try:
                if not selected or {item[1] for item in selected} != {len(selected)} or [item[0] for item in selected] != list(range(1, len(selected) + 1)):
                    raise ValueError("Incomplete tariff continuation")
                raw = "\n".join(item[2].text for item in selected)
                text = re.sub(r"\s+", " ", raw)
                if not all(label in text for label in ("FUEL ADJUSTMENT MECHANISM", "DSM COST RECOVERY RIDER", "STORM COST RECOVERY RIDER", "AVAILABILITY")):
                    raise ValueError("Missing rider or eligibility context")
                fixed = current_charge(text, "CUSTOMER CHARGE")
                if fixed != current_charge(text, "MINIMUM MONTHLY CHARGE"):
                    raise ValueError("Changed minimum-bill structure")
                components = [RateComponent("fixed", "Basic Charge", fixed, "$/month")]
                structure, variant, start, end = "flat", "standard", effective, year_end
                conditions = "Minimum bill is the monthly customer charge. Base energy and mandatory riders are separate."
                if kind == "standard":
                    energy_section = raw.split("ENERGY CHARGE", 1)[1].split("FUEL ADJUSTMENT", 1)[0]
                    match = re.search(r"cents per\s+kilowatt-hour\s+(\d+\.\d+)", energy_section)
                    if not match:
                        raise ValueError("Missing domestic base energy")
                    components.append(RateComponent("energy", "Base Energy Charge", round(float(match.group(1)) / 100, 6), "$/kWh"))
                elif kind == "tod":
                    if "Electric Thermal Storage (ETS)" not in text or "timing and controls approved" not in text:
                        raise ValueError("Missing storage-heating eligibility")
                    energy_section = raw.split("ENERGY CHARGE", 1)[1].split("FUEL ADJUSTMENT", 1)[0]
                    if not re.search(r"cents per\s+kilowatt-hour", energy_section):
                        raise ValueError("Invalid TOD energy unit")
                    winter, winter_header = numeric_line(energy_section, 4)
                    shoulder_section = energy_section.split("Applicable from March to", 1)[1]
                    shoulder, shoulder_header = numeric_line(shoulder_section, 2)
                    if not all(month in winter_header for month in ("December", "January", "February")) or "November" not in shoulder_header:
                        raise ValueError("Changed TOD seasons")
                    if "For Saturdays, Sundays, and statutory holidays" not in energy_section or winter[-1] != shoulder[-1]:
                        raise ValueError("Missing weekend/holiday pricing")
                    for season, months, values, header, count in (
                        ("winter", "12,1,2", winter, winter_header, 4),
                        ("non-winter", "3,4,5,6,7,8,9,10,11", shoulder, shoulder_header, 2),
                    ):
                        clocks = re.findall(r"\d{1,2}:\d{2} [AP]M", header)
                        if len(clocks) != count * 2:
                            raise ValueError("Missing TOD clock windows")
                        for index, price in enumerate(values):
                            period = ("on-peak", "mid-peak", "on-peak", "off-peak")[index] if count == 4 else ("mid-peak", "off-peak")[index]
                            hours = f"Monday-Friday excluding statutory holidays: {clocks[index]} to {clocks[index + count]}"
                            if period == "off-peak":
                                hours += "; all hours on Saturdays, Sundays and statutory holidays"
                            components.append(RateComponent("energy", f"Base {season.title()} {period.title()} Energy ({index + 1})",
                                                            round(price / 100, 6), "$/kWh", tou_period=period, tou_hours=hours,
                                                            season=season, season_months=months))
                    structure, variant = "tou", "thermal storage time-of-day"
                else:
                    product = product_text.get(kind, "")
                    if "Applications for the Time-of-Use Rate Pilot and Critical Peak Pricing Rate Pilot are now closed" not in product:
                        raise ValueError("Pilot enrollment status not verified")
                    transition = re.search(r"until October 31, (\d{4})\. Effective November\s+1, \1", text)
                    if not transition or "standard offer rates" not in text or "standard Smart Meter" not in text:
                        raise ValueError("Missing interim transition or pilot eligibility")
                    transition_date = date(int(transition.group(1)), 11, 1).isoformat()
                    if today < transition_date:
                        interim = text.split("INTERIM ENERGY CHARGE", 1)[1]
                        match = re.search(r"Effective upon the date of the (?:n/a )?(\d+\.\d+) Board", interim)
                        if not match or not re.search(r"cents per\s+(?:winter Period\)\s+)?kilowatt-hour", selected[0][2].text):
                            raise ValueError("Missing published interim energy rate")
                        end = date(int(transition.group(1)), 10, 31).isoformat()
                        components.append(RateComponent("energy", "Interim Base Energy Charge (All Hours)", round(float(match.group(1)) / 100, 6), "$/kWh"))
                        variant = "pilot - interim standard pricing"
                        conditions += " This is the published interim standard-price variant, subject to the tariff's system-restoration provisions; no critical-peak events apply while interim pricing is in force. Scheduled winter rates begin " + transition_date + ". Product pages advertise the time-varying prices; they are not substituted for this dated tariff phase."
                    else:
                        start, structure, variant = transition_date, "tou", "pilot - time-varying pricing"
                        energy_heading = re.search(r"(?m)^ENERGY CHARGE\s*$", raw)
                        approved = re.sub(r"\s+", " ", raw[energy_heading.end():]) if energy_heading else ""
                        if not re.search(r"cents per\s+kilowatt-hour", approved):
                            raise ValueError("Missing approved pilot energy units")
                        row = re.search(r"Effective November 1, " + str(year) + r" ((?:\d+\.\d+ ?)+)", approved)
                        prices = amounts(row.group(1)) if row else []
                        if kind == "tou":
                            if len(prices) != 4 or prices[0] != prices[2] or prices[1] != prices[3]:
                                raise ValueError("Incomplete current TOU energy columns")
                            clocks = re.findall(r"\d{1,2}:\d{2} [AP]M", approved[:row.start()])
                            if len(clocks) != 8 or "off-peak price also applies to all hours on Saturdays, Sundays" not in approved:
                                raise ValueError("Missing TOU hours or weekend rule")
                            windows = [f"{clocks[index]} to {clocks[index + 4]}" for index in range(4)]
                            holidays = re.search(r"Note 1: (.*?)FUEL ADJUSTMENT MECHANISM", approved)
                            if not holidays or "November 1 through March 31" not in approved:
                                raise ValueError("Missing TOU seasonal or holiday conditions")
                            conditions += " Published winter holiday rule: " + holidays.group(1)
                            components.extend([
                                RateComponent("energy", "Base Winter On-Peak Energy", round(prices[0] / 100, 6), "$/kWh",
                                              tou_period="on-peak", tou_hours=f"Monday-Friday {windows[0]} and {windows[2]}, excluding listed holidays", season="winter", season_months="11,12,1,2,3"),
                                RateComponent("energy", "Base Winter Off-Peak Energy", round(prices[1] / 100, 6), "$/kWh",
                                              tou_period="off-peak", tou_hours=f"{windows[1]} and {windows[3]}; all weekends and listed/observed holidays", season="winter", season_months="11,12,1,2,3"),
                            ])
                        else:
                            if len(prices) != 2 or "four-hour duration" not in text or "6:00 AM and 11:00 PM" not in text:
                                raise ValueError("Missing CPP event rate or window")
                            components.extend([
                                RateComponent("energy", "Base Critical Peak Event Energy", round(prices[0] / 100, 6), "$/kWh",
                                              tou_period="critical-peak", tou_hours="Declared four-hour events between 06:00 and 23:00; listed holidays excluded", season="winter", season_months="11,12,1,2,3"),
                                RateComponent("energy", "Base Non-Critical Energy", round(prices[1] / 100, 6), "$/kWh", tou_period="non-critical", tou_hours="All hours outside declared critical-peak events"),
                            ])
                            events = re.search(r"CRITICAL PEAK EVENT PROCEDURE (.*?)FUEL ADJUSTMENT MECHANISM", approved)
                            if not events or "No more than" not in events.group(1) or "day prior" not in events.group(1):
                                raise ValueError("Missing critical-peak event limits or notice conditions")
                            conditions += " Published event conditions: " + events.group(1)
                    conditions += " Pilot enrollment is closed to new applications. No seasonal or net-metering service; start November 1 unless NSPI grants a waiver."
                if any(component.charge_value is None or component.charge_value <= 0 for component in components):
                    raise ValueError("Invalid residential charge values")
                if "Optional Green Power Rider" in text:
                    block = re.search(r"provide (\d+) kWh per month.*?cost of \$(\d+(?:\.\d+)?) per month", text)
                    if not block:
                        raise ValueError("Incomplete optional green-power rider")
                    components.append(RateComponent("rider", "Optional Green Power Block", float(block.group(2)), "$/block/month",
                                                    sub_component="optional", notes=f"Opt-in only: each purchased block supplies {block.group(1)} kWh/month from green sources. Additional to normal service charges."))
                detail = f"Domestic tariff {code}; PDF pages " + ", ".join(str(item[2].page_number) for item in selected)
                for component in components:
                    component.source_url = source_url
                    component.source_detail = detail
                    component.effective_date = start
                    component.end_date = end
                availability = text.split("AVAILABILITY", 1)[1].split("Optional Green Power Rider", 1)[0]
                if kind in {"tou", "cpp"}:
                    availability += " Pilot closed to new applications; " + ("interim standard-price variant where interim provisions apply." if today < transition_date else "time-varying winter phase.")
                    if today < transition_date:
                        restoration = re.search(r"If system functionality is restored after (.*?shall remain in effect until October 31, \d{4})", text)
                        if not restoration:
                            raise ValueError("Missing interim applicability condition")
                        availability = "Conditional interim variant only. If system functionality is restored after " + restoration.group(1) + ". " + availability
                        conditions += " The scraper has not verified the participant's system-restoration status; this is not a claim that all pilot customers currently pay the interim price."
                record_name = name + " - Conditional Pilot" if kind in {"tou", "cpp"} else name
                records.append(TariffRecord(
                    utility_name="Nova Scotia Power", province="NS", utility_type="electricity",
                    tariff_name=record_name, tariff_code=code, customer_class="residential", sub_class=variant,
                    rate_structure=structure, effective_date=start, end_date=end,
                    eligibility=availability.strip(), source_url=source_url, source_page=detail,
                    notes=conditions, components=components + [replace(component) for component in riders],
                ))
            except (ValueError, IndexError) as exc:
                self.logger.warning("NSPower residential %s incomplete: %s", code, exc)
        return records

    def _try_live_commercial(self) -> Optional[list[TariffRecord]]:
        """Parse Rate 10/11/12 from the NSUARB-approved business rate schedule page."""
        try:
            html = self.fetch_page(BUSINESS_URL)
        except Exception as e:
            self.logger.warning("Could not fetch business rates page: %s", e)
            return None

        text = parse_html(html).get_text("\n", strip=True)
        headers = [row[4] for row in _COMMERCIAL_RATES] + ["Large Industrial"]
        eligibility = {
            "10": SEED_RATE10["eligibility"],
            "11": SEED_RATE11["eligibility"],
            "12": SEED_RATE12["eligibility"],
        }
        records: list[TariffRecord] = []
        for idx, (code, name, sub, structure, header) in enumerate(_COMMERCIAL_RATES):
            section = self._commercial_section(text, header, headers[idx + 1:])
            if not section:
                continue
            components = self._parse_commercial_components(section)
            if not components:
                continue
            records.append(TariffRecord(
                utility_name="Nova Scotia Power", province="NS", utility_type="electricity",
                tariff_name=name, tariff_code=code, customer_class="commercial",
                sub_class=sub, rate_structure=structure,
                effective_date=SEED_RATE10["effective_date"], source_url=BUSINESS_URL,
                confidence="high", eligibility=eligibility[code],
                notes=(
                    f"NS Power Rate {code} — {name} — live parsed from the "
                    "NSUARB-approved business rate schedule."
                ),
                components=components,
            ))

        if not records:
            self.logger.warning("Could not parse any commercial rates from business page")
            return None

        seed_commercial = [
            self._seed_data_rate10(), self._seed_data_rate11(), self._seed_data_rate12(),
        ]
        alerts = compare_to_seed(records, seed_commercial)
        log_change_alerts(alerts)
        if has_critical_alerts(alerts):
            self.logger.error(
                "Critical deviation in live commercial data vs seed — falling back to seed"
            )
            return None
        self.logger.info("Parsed %d commercial rate classes from business page", len(records))
        return records

    @staticmethod
    def _commercial_section(text: str, start_header: str, end_headers: list[str]) -> str:
        """Return the primary-charge slice for a rate, cut before samples/minimum-charge notes."""
        i = text.find(start_header)
        if i == -1:
            return ""
        i += len(start_header)
        end = len(text)
        stops = list(end_headers) + [
            "The minimum monthly", "The maximum charge", "minimum monthly bill", "Sample ",
        ]
        for marker in stops:
            j = text.find(marker, i)
            if j != -1:
                end = min(end, j)
        return text[i:end]

    def _parse_commercial_components(self, section: str) -> list[RateComponent]:
        """Extract base, demand and (flat/tiered) energy charges from one rate section."""
        components: list[RateComponent] = []

        base = re.search(r"\$\s*([\d.]+)\s*per month(?!\s*per\s*kilo)", section, re.I)
        if base:
            components.append(RateComponent(
                component_type="fixed", component_name="Base Charge",
                charge_value=float(base.group(1)), charge_unit="$/month",
                notes="Monthly base charge",
            ))

        demand = re.search(
            r"\$\s*([\d.]+)\s*per month per (kilowatt|kilovolt ampere)", section, re.I
        )
        if demand:
            unit = "kW" if "kilowatt" in demand.group(2).lower() else "kVA"
            components.append(RateComponent(
                component_type="demand", component_name="Demand Charge",
                charge_value=float(demand.group(1)), charge_unit=f"$/{unit}", demand_unit=unit,
                notes="Per unit of billing (maximum) demand",
            ))

        for em in re.finditer(
            r"([\d.]+)\s*[^\d\s]{0,3}\s*per kilowatt hour([^\n.]*)", section, re.I
        ):
            qualifier = re.sub(r"\s+", " ", em.group(2)).strip()
            tier_number: Optional[int] = None
            threshold: Optional[float] = None
            first = re.search(r"first ([\d,]+)", qualifier, re.I)
            if first:
                tier_number = 1
                threshold = float(first.group(1).replace(",", ""))
            elif "additional" in qualifier.lower():
                tier_number = 2
            label = ("Energy Charge " + qualifier).strip()[:110] if qualifier else "Energy Charge"
            components.append(RateComponent(
                component_type="energy", component_name=label,
                charge_value=round(float(em.group(1)) / 100.0, 6), charge_unit="$/kWh",
                tier_number=tier_number, tier_threshold=threshold,
                tier_unit="kWh" if threshold else None,
            ))

        return components

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
        return [
            self._seed_data_residential(),
            self._seed_data_rate10(),
            self._seed_data_rate11(),
            self._seed_data_rate12(),
        ]

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

    def _seed_data_rate10(self) -> TariffRecord:
        """Return seed data for Rate 10 — Small Commercial."""
        return TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Small Commercial",
            tariff_code="10",
            customer_class="commercial",
            sub_class="small commercial",
            rate_structure="tiered",
            effective_date=SEED_RATE10["effective_date"],
            source_url=SEED_RATE10["source_url"],
            confidence="high",
            eligibility=SEED_RATE10["eligibility"],
            notes="NS Power Rate 10 — Small Commercial tiered energy rate",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Base Charge",
                    charge_value=SEED_RATE10["base_charge"],
                    charge_unit="$/month",
                    notes="Monthly base charge",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — First 200 kWh",
                    charge_value=SEED_RATE10["energy_tier1"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=float(SEED_RATE10["tier1_threshold_kwh"]),
                    tier_unit="kWh/month",
                    notes="First 200 kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — Balance",
                    charge_value=SEED_RATE10["energy_tier2"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    notes="All additional kWh beyond 200 kWh/month",
                ),
            ],
        )

    def _seed_data_rate11(self) -> TariffRecord:
        """Return seed data for Rate 11 — Commercial General Demand."""
        return TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Commercial General Demand",
            tariff_code="11",
            customer_class="commercial",
            sub_class="general demand",
            rate_structure="demand",
            effective_date=SEED_RATE11["effective_date"],
            source_url=SEED_RATE11["source_url"],
            confidence="high",
            eligibility=SEED_RATE11["eligibility"],
            notes="NS Power Rate 11 — Commercial General Demand",
            components=[
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_RATE11["demand_charge"],
                    charge_unit="$/kW",
                    demand_unit="kW",
                    notes="Billing demand charge",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — First 200 kWh/kW",
                    charge_value=SEED_RATE11["energy_tier1"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    notes="First 200 kWh per kW of maximum demand",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — Balance",
                    charge_value=SEED_RATE11["energy_tier2"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    notes="All additional kWh beyond first block",
                ),
            ],
        )

    def _seed_data_rate12(self) -> TariffRecord:
        """Return seed data for Rate 12 — Large Commercial."""
        return TariffRecord(
            utility_name="Nova Scotia Power",
            province="NS",
            utility_type="electricity",
            tariff_name="Large Commercial",
            tariff_code="12",
            customer_class="commercial",
            sub_class="large commercial",
            rate_structure="demand",
            effective_date=SEED_RATE12["effective_date"],
            source_url=SEED_RATE12["source_url"],
            confidence="high",
            eligibility=SEED_RATE12["eligibility"],
            notes="NS Power Rate 12 — Large Commercial",
            components=[
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_RATE12["demand_charge"],
                    charge_unit="$/kVA",
                    demand_unit="kVA",
                    notes="Billing demand charge",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_RATE12["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat energy rate for all kWh consumed",
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="Minimum Charge",
                    charge_value=SEED_RATE12["minimum_charge"],
                    charge_unit="$/month",
                    notes="Minimum monthly charge",
                ),
            ],
        )
