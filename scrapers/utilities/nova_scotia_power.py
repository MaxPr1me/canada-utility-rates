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


class NovaScotiaPowerScraper(BaseScraper):
    """Scrape Nova Scotia Power electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Nova Scotia Power", province="NS")
        self._book: Optional[tuple[list[DocumentPage], dict[str, str], str]] = None

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
        for record in live_records:
            record.source_page = record.source_page or f"Rate {record.tariff_code}: {record.tariff_name}"
            for component in record.components:
                component.source_detail = component.source_detail or record.source_page
        covered = {record.tariff_name for record in live_records}
        fallback = [record for record in self._seed_data() if record.tariff_name not in covered]
        return self.mark_live_parsed(live_records) + (self.mark_fallback(fallback) if fallback else [])

    def _try_live_residential(self) -> list[TariffRecord]:
        self._book = None
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
            pages = extract_pdf_pages(self.fetch_bytes(source_url))
        except Exception as exc:
            self.logger.warning("NSPower residential tariff unavailable: %s", exc)
            return []
        self._book = (pages, products, source_url)
        records: list[TariffRecord] = []
        for parse in (self._parse_residential_tariffs, self._parse_building_option_tariffs):
            try:
                records.extend(parse(pages, products, source_url))
            except Exception as exc:
                self.logger.warning("NSPower tariff group %s unavailable: %s", parse.__name__, exc)
        return records

    def _order_context(
        self, pages: list[DocumentPage], product_text: dict[str, str],
    ) -> Optional[tuple[int, str, str, str]]:
        """Return (book year, Board-order date, today, year end) when the dated book is current."""
        cover = next((page.text for page in pages if re.match(r"Tariffs\s+[A-Za-z]+\s+\d{4}", page.text)), "")
        publication = re.search(r"Tariffs\s+([A-Za-z]+)\s+(\d{4})", cover)
        if not publication or "Approved by" not in cover:
            return None
        year = int(publication.group(2))
        dates = set()
        for text in product_text.values():
            match = re.search(r"Rates updated as of ([A-Za-z]+ \d{1,2}, \d{4})", text)
            if match:
                effective = extract_effective_date("Effective " + match.group(1))
                if effective and datetime.strptime(effective, "%Y-%m-%d").strftime("%B %Y") == f"{publication.group(1)} {year}":
                    dates.add(effective)
        if len(dates) != 1:
            return None
        effective = next(iter(dates))
        today = self.now_iso()[:10]
        year_end = date(year, 12, 31).isoformat()
        if not effective <= today <= year_end:
            return None
        return year, effective, today, year_end

    def _parse_residential_tariffs(
        self, pages: list[DocumentPage], products: dict[str, str], source_url: str,
    ) -> list[TariffRecord]:
        """Parse the current approved book, separating tariff phases and rider totals."""
        product_text = {kind: parse_html(html).get_text(" ", strip=True) for kind, html in products.items()}
        context = self._order_context(pages, product_text)
        if not context:
            return []
        year, effective, today, year_end = context

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

    # ── Building options: MURB time-of-use and solar subscriptions ──

    @staticmethod
    def _continuous_pages(pages: list[DocumentPage], header_pattern: str, label: str) -> list[DocumentPage]:
        """Return one tariff's pages in order, rejecting any missing continuation page."""
        found: list[tuple[int, int, DocumentPage]] = []
        for page in pages:
            match = re.match(header_pattern, re.sub(r"\s+", " ", page.text))
            if match:
                found.append((int(match.group(1)), int(match.group(2)), page))
        found.sort(key=lambda item: item[0])
        if not found or {item[1] for item in found} != {len(found)} or [item[0] for item in found] != list(range(1, len(found) + 1)):
            raise ValueError(f"Incomplete {label} continuation")
        return [item[2] for item in found]

    @staticmethod
    def _footer_effective_date(pages: list[DocumentPage]) -> str:
        """Return the single 'Effective: <date>' footer shared by every page of a rider."""
        dates = set()
        for page in pages:
            match = re.search(r"Effective: ([A-Za-z]+ \d{1,2}, \d{4})", page.text)
            dates.add(extract_effective_date("Effective " + match.group(1)) if match else None)
        if len(dates) != 1 or None in dates:
            raise ValueError("Missing or inconsistent rider effective date")
        return next(iter(dates))

    def _murb_rider_components(
        self, pages: list[DocumentPage], year: int, effective: str, year_end: str, source_url: str,
    ) -> list[RateComponent]:
        """Read the shared General/MURB row of the FAM, DSM and storm riders (not Large General)."""
        def joined(heading: str) -> tuple[str, str]:
            selected = [page for page in pages if page.text.startswith(heading)]
            detail = heading + "; PDF pages " + ", ".join(str(page.page_number) for page in selected)
            return re.sub(r"\s+", " ", "\n".join(page.text for page in selected)), detail

        def number(token: str) -> float:
            return -float(token[1:-1]) if token.startswith("(") else float(token)

        text, fam_detail = joined("FUEL ADJUSTMENT MECHANISM (FAM) TARIFF")
        current = re.search(rf"\b{year}\b(.*?)(?:\b{year + 1}\b|$)", text)
        row = re.search(
            r"(?<!Small )General, General Time of Use, (\d+\.\d+) (\d+\.\d+) General Critical Peak, Multi-Unit "
            r".*?Residential Building \(MURB\) Time of Use Large General",
            current.group(1) if current else "",
        )
        if not row or "cents per kWh" not in text or row.group(1) != row.group(2):
            raise ValueError("Missing FAM row for General and MURB service")
        fam = number(row.group(2))

        text, dsm_detail = joined("DEMAND SIDE MANAGEMENT COST RECOVERY RIDER")
        row = re.search(
            r"General, General Time of Use, General Critical Peak (\d+\.\d+) (\(?\d+\.\d+\)?) (\d+\.\d+) "
            r"Pricing, Multi-unit Residential Building Time-of-Use Large General", text,
        )
        if not row or f"January 1, {year} to December 31, {year}" not in text or "cents per kWh" not in text:
            raise ValueError("Missing DSM row for General and MURB service")
        program, balance, dsm = number(row.group(1)), number(row.group(2)), number(row.group(3))
        if abs(program + balance - dsm) > 0.0011:
            raise ValueError("Changed MURB DSM breakdown")

        text, storm_detail = joined("STORM COST RECOVERY RIDER")
        row = re.search(
            r"General, General Time-of-Use, General Critical Peak Pricing, Multi-unit (\d+\.\d+) "
            r"Residential Building Time-of-Use Large General", text,
        )
        if not row or f"SCRR RATES FOR {year}" not in text or "cents per kWh" not in text:
            raise ValueError("Missing storm row for General and MURB service")
        storm = number(row.group(1))

        row_note = "Shared published row: General, General TOU, General Critical Peak and Multi-Unit Residential Building (MURB) TOU; Large General is a separate row."
        riders = [
            RateComponent("rider", "FAM Actual/Balance Adjustment (Combined)", round(fam / 100, 6), "$/kWh",
                          source_detail=fam_detail, effective_date=effective, end_date=year_end, notes=row_note),
            RateComponent("rider", "DSM Cost Recovery Rider", round(dsm / 100, 6), "$/kWh",
                          source_detail=dsm_detail, effective_date=date(year, 1, 1).isoformat(), end_date=year_end,
                          notes=f"Combined PCR {program} and BA {balance} cents/kWh; do not add the subcomponents again. {row_note}"),
            RateComponent("rider", "Storm Cost Recovery Rider", round(storm / 100, 6), "$/kWh",
                          source_detail=storm_detail, effective_date=effective, end_date=year_end, notes=row_note),
        ]
        for component in riders:
            component.source_url = source_url
        return riders

    def _parse_murb_tariff(
        self, pages: list[DocumentPage], context: tuple[int, str, str, str], source_url: str,
    ) -> TariffRecord:
        """Parse Rate 89 (optional MURB time-of-use) with its mandatory riders kept separate."""
        year, effective, _today, year_end = context
        selected = self._continuous_pages(
            pages, r"MULTI-UNIT RESIDENTIAL BUILDINGS TIME OF USE TARIFF Page (\d+) of (\d+) Rate Code 89", "MURB tariff",
        )
        text = re.sub(r"\s+", " ", "\n".join(page.text for page in selected))
        order = r"Board\S{1,2}s Order Effective January 1, " + str(year + 1)
        non_winter = re.search(
            r"cents per kilowatt-hour Non-winter Period Off-peak On-peak April 1 through October 31 9:00 PM to 7:00 AM to 7:00 AM 9:00 PM "
            r"Effective upon the date of the (\d+\.\d+) (\d+\.\d+) " + order, text,
        )
        winter = re.search(
            r"cents per kilowatt-hour On-peak On-peak Winter Period Mid-peak Off-peak \(morning\) \(evening\) November 1 through March 31 "
            r"7:00 AM to 11:00 AM to 5:00 PM to 9:00 PM to 11:00 AM 5:00 PM 9:00 PM 7:00 AM "
            r"Effective upon the date of the (\d+\.\d+) (\d+\.\d+) (\d+\.\d+) (\d+\.\d+) " + order, text,
        )
        if not non_winter or not winter:
            raise ValueError("Missing or changed MURB energy table")
        off_peak, on_peak = (float(value) for value in non_winter.groups())
        winter_prices = [float(value) for value in winter.groups()]
        if min(off_peak, on_peak, *winter_prices) <= 0:
            raise ValueError("Non-positive MURB base energy price")
        if winter_prices[0] != winter_prices[2]:
            raise ValueError("Changed MURB winter on-peak columns")
        weekend = re.search(r"Note 1: (.*?) FUEL ADJUSTMENT MECHANISM", text)
        if not weekend or "applicable peak price also applies to all hours on Saturdays, Sundays" not in weekend.group(1):
            raise ValueError("Missing MURB weekend and holiday rule")
        availability = re.search(r"AVAILABILITY CONDITIONS (.*?) SPECIAL CONDITIONS", text)
        required = ("minimum of 10 units", "house meter", "standard Smart Meter", "November 1st", "Regulation 3.3", "Regulation 3.6")
        if not availability or not all(phrase in availability.group(1) for phrase in required) \
                or "eligible for service under the General Tariff" not in text:
            raise ValueError("Missing MURB eligibility conditions")
        minimum = re.search(
            r"MINIMUM MONTHLY CHARGE The minimum monthly charge shall not be less than the rates in the table below\. "
            r"per month Effective upon the date of the \$(\d+\.\d{2}) " + order + r" \$", text,
        )
        metering = re.search(r"Meter readings shall then be reduced by (\d+\.\d+)%", text)
        if not minimum or not metering:
            raise ValueError("Missing MURB minimum charge or metering adjustment")
        riders = self._murb_rider_components(pages, year, effective, year_end, source_url)

        holiday_rule = " Source Note 1 applies the applicable peak price on Saturdays, Sundays and listed holidays."
        weekday = "Monday-Friday excluding listed holidays: "
        energy = [
            ("Base Non-Winter Off-Peak Energy", off_peak, "off-peak", weekday + "9:00 PM to 7:00 AM", "non-winter", "4,5,6,7,8,9,10"),
            ("Base Non-Winter On-Peak Energy", on_peak, "on-peak", "7:00 AM to 9:00 PM." + holiday_rule, "non-winter", "4,5,6,7,8,9,10"),
            ("Base Winter On-Peak (Morning) Energy", winter_prices[0], "on-peak", weekday + "7:00 AM to 11:00 AM." + holiday_rule, "winter", "11,12,1,2,3"),
            ("Base Winter Mid-Peak Energy", winter_prices[1], "mid-peak", weekday + "11:00 AM to 5:00 PM", "winter", "11,12,1,2,3"),
            ("Base Winter On-Peak (Evening) Energy", winter_prices[2], "on-peak", weekday + "5:00 PM to 9:00 PM." + holiday_rule, "winter", "11,12,1,2,3"),
            ("Base Winter Off-Peak Energy", winter_prices[3], "off-peak", weekday + "9:00 PM to 7:00 AM", "winter", "11,12,1,2,3"),
        ]
        detail = "Rate Code 89; PDF pages " + ", ".join(str(page.page_number) for page in selected)
        components = [
            RateComponent("energy", name, round(price / 100, 6), "$/kWh", tou_period=period, tou_hours=hours,
                          season=season, season_months=months, source_url=source_url, source_detail=detail,
                          effective_date=effective, end_date=year_end)
            for name, price, period, hours, season, months in energy
        ]
        return TariffRecord(
            utility_name="Nova Scotia Power", province="NS", utility_type="electricity",
            tariff_name="Multi-Unit Residential Buildings Time-of-Use (Rate 89)", tariff_code="89",
            customer_class="residential", sub_class="multi-unit residential building time-of-use (house meter)",
            rate_structure="tou", effective_date=effective, end_date=year_end,
            eligibility="Optional tariff for customers eligible under the General Tariff. " + availability.group(1).strip(),
            source_url=source_url, source_page=detail,
            notes=(
                f"No customer charge is published. The ${minimum.group(1)} monthly charge is a minimum-bill condition, not an additional fixed charge. "
                "Base energy and the mandatory FAM, DSM and storm riders are separate. "
                f"Primary metering readings are reduced by {metering.group(1)}%. Source Note 1: {weekend.group(1)} "
                "The source does not separate the equal winter on-peak prices beyond this rule. "
                "Effective date is the May 2026 Board-order date verified on the residential rate pages; no separate dated MURB product page is used."
            ),
            components=components + riders,
        )

    def _parse_solar_garden_rider(
        self, pages: list[DocumentPage], context: tuple[int, str, str, str], source_url: str,
    ) -> TariffRecord:
        """Parse the optional Amherst Solar Garden subscription as an adjustment to the subscriber's own tariff."""
        year, _effective, today, year_end = context
        selected = self._continuous_pages(pages, r"(?:SCHEDULE A )?SOLAR GARDEN RATE RIDER Page (\d+) of (\d+)", "Solar Garden rider")
        text = re.sub(r"\s+", " ", "\n".join(page.text for page in selected))
        effective = self._footer_effective_date(selected)
        if effective > today:
            raise ValueError("Solar Garden rider is not yet effective")
        exclusions = (
            "Customers on a seasonal rate", "Customers who take Net Metering Service under Regulation 3.6",
            "Section 3A or 3AA of the Electricity Act", "Subscribers to the Community Solar Energy Credit Rider",
        )
        availability = re.search(r"AVAILABILITY (.*?) APPLICABILITY", text)
        if not availability or not all(phrase in availability.group(1) for phrase in exclusions) \
                or "first-come, first-served" not in availability.group(1):
            raise ValueError("Missing Solar Garden subscriber eligibility")
        charge = re.search(
            r"Monthly Solar Capacity Charge \$(\d+\.\d+) per kW subscribed\. The same charge will apply regardless of the customer.s rate class", text,
        )
        table = re.search(r"Solar Energy Credit Year \(cents per kWh\)(.*?)The same credit will apply regardless of the customer.s rate class", text)
        if not charge or not table or "0.25 kW increments" not in text \
                or "will also be billed in accordance with the otherwise applicable Tariffs" not in text \
                or "does not change per distinct time-of-use, time-of-day, or critical peak period" not in text:
            raise ValueError("Missing Solar Garden charge, credit table or billing basis")
        credits = {int(row[0]): float(row[1]) for row in re.findall(r"\b(20\d{2}) (\d{1,2}\.\d{3})\b", table.group(1))}
        years = sorted(credits)
        if year not in credits or years != list(range(years[0], years[-1] + 1)):
            raise ValueError("Missing current Solar Garden credit year")
        if float(charge.group(1)) <= 0 or min(credits.values()) <= 0:
            raise ValueError("Non-positive Solar Garden charge or credit")
        if any(abs(credits[later] / credits[earlier] - 1.02) > 0.001 for earlier, later in zip(years, years[1:])):
            raise ValueError("Changed Solar Garden credit escalation")
        detail = "Solar Garden Rate Rider; PDF pages " + ", ".join(str(page.page_number) for page in selected)
        components = [
            RateComponent(
                "rider", "Solar Garden Monthly Capacity Charge", float(charge.group(1)), "$/kW-dc subscribed/month",
                sub_component="optional", effective_date=effective,
                notes="Published per subscribed kW-dc per month; subscriptions are purchased in 0.25 kW-dc increments. Applies for all days of the subscription month, even if generation is interrupted. Same rate for every customer class.",
            ),
            RateComponent(
                "rebate", f"Solar Garden Energy Credit ({year})", -round(credits[year] / 100, 6), "$/kWh of subscriber's attributable Solar Garden production",
                sub_component="optional", effective_date=date(year, 1, 1).isoformat(), end_date=year_end,
                notes="Credit, not an energy price: it is applied only to the subscriber's attributable share of measured net Solar Garden output and does not vary by time-of-use period. Source credits rise about 2% per year.",
            ),
        ]
        for component in components:
            component.source_url = source_url
            component.source_detail = detail
        return TariffRecord(
            utility_name="Nova Scotia Power", province="NS", utility_type="electricity",
            tariff_name="Solar Garden Rate Rider (Optional Subscriber Adjustment)", tariff_code="Solar Garden Rider",
            customer_class="other", sub_class="optional adjustment - Amherst Solar Garden subscribers only",
            rate_structure="flat", effective_date=max(component.effective_date for component in components), source_url=source_url, source_page=detail,
            eligibility=availability.group(1).strip(),
            notes=(
                "Applies on top of the subscriber's otherwise applicable tariff; it does not replace that tariff's energy, fixed, demand or rider charges. "
                "Subscribers receive credits only on their attributable share of Solar Garden net production; no bill total or offset is calculated. "
                "Renewable energy certificates are not offered."
            ),
            components=components,
        )

    def _parse_community_solar_rider(
        self, pages: list[DocumentPage], context: tuple[int, str, str, str], source_url: str,
    ) -> TariffRecord:
        """Parse the Community Solar credit rider for project-owner-approved subscribers."""
        _year, _effective, today, _year_end = context
        selected = self._continuous_pages(pages, r"(?:A )?COMMUNITY SOLAR ENERGY CREDIT RIDER Page (\d+) of ?(\d+)", "Community Solar rider")
        text = re.sub(r"\s+", " ", "\n".join(page.text for page in selected)).replace("\u2019", "'")
        effective = self._footer_effective_date(selected)
        if effective > today:
            raise ValueError("Community Solar rider is not yet effective")
        availability = re.search(r"AVAILABILITY (.*?) APPLICABILITY", text)
        required = ("criteria, as set solely by the Project Owner", "Regulation 3.6", "Solar Garden Pilot Rate Rider", "all metered NS Power customer classes")
        credit = re.search(r"Value of Solar Energy Credit is (\d+\.\d+) cents per kWh for the duration of the subscription", text)
        if not availability or not all(phrase in availability.group(1) for phrase in required) or not credit \
                or "The same credit will apply regardless of the customer's current applicable tariff" not in text \
                or "NO ADDITIONAL FEES" not in text \
                or "will also be billed in accordance with the otherwise applicable Tariffs" not in text:
            raise ValueError("Missing Community Solar eligibility, credit or billing basis")
        if float(credit.group(1)) <= 0:
            raise ValueError("Non-positive Community Solar credit")
        detail = "Community Solar Energy Credit Rider; PDF pages " + ", ".join(str(page.page_number) for page in selected)
        component = RateComponent(
            "rebate", "Community Solar Energy Credit", -round(float(credit.group(1)) / 100, 6),
            "$/kWh of subscriber's attributable Community Solar Garden production", sub_component="optional",
            effective_date=effective, source_url=source_url, source_detail=detail,
            notes="Fixed for the duration of the subscription unless amended under the Community Solar Program Regulations; credit only, applied to the attributable share of measured net garden production.",
        )
        return TariffRecord(
            utility_name="Nova Scotia Power", province="NS", utility_type="electricity",
            tariff_name="Community Solar Energy Credit Rider (Optional Subscriber Adjustment)", tariff_code="Community Solar Rider",
            customer_class="other", sub_class="optional adjustment - approved Community Solar Garden subscribers only",
            rate_structure="flat", effective_date=effective, source_url=source_url, source_page=detail,
            eligibility=availability.group(1).strip(),
            notes=(
                "Applies on top of the subscriber's otherwise applicable tariff. The source states no additional subscription fees; project-owner contracts are outside this tariff. "
                "Eligibility is set by each Project Owner and no bill total or offset is calculated."
            ),
            components=[component],
        )

    def _parse_building_option_tariffs(
        self, pages: list[DocumentPage], products: dict[str, str], source_url: str,
    ) -> list[TariffRecord]:
        """Parse MURB and solar options independently; a failed class is logged and omitted."""
        context = self._order_context(pages, {kind: parse_html(html).get_text(" ", strip=True) for kind, html in products.items()})
        if not context:
            return []
        records: list[TariffRecord] = []
        for label, parser in (
            ("MURB Rate 89", self._parse_murb_tariff),
            ("Solar Garden rider", self._parse_solar_garden_rider),
            ("Community Solar rider", self._parse_community_solar_rider),
        ):
            try:
                records.append(parser(pages, context, source_url))
            except (ValueError, IndexError) as exc:
                self.logger.warning("NSPower %s incomplete: %s", label, exc)
        return records

    # ── Business: Small General 10, General 11, Large General 12 ──

    def _try_live_commercial(self) -> Optional[list[TariffRecord]]:
        """Parse Rate 10/11/12 from the tariff book already fetched for residential service."""
        book = self._book
        if not book:
            return None
        pages, products, source_url = book
        records = self._parse_business_tariffs(pages, products, source_url)
        records.extend(self._parse_industrial_tariffs(pages, products, source_url))
        try:
            business_html = self.fetch_page(BUSINESS_URL)
        except Exception as exc:
            self.logger.warning("NSPower business product page unavailable; pilots skipped: %s", exc)
        else:
            records.extend(self._parse_business_pilot_tariffs(pages, products, source_url, business_html))
        return records or None

    @staticmethod
    def _joined_rider_text(pages: list[DocumentPage], heading: str) -> tuple[str, str]:
        selected = [page for page in pages if page.text.startswith(heading)]
        detail = heading + "; PDF pages " + ", ".join(str(page.page_number) for page in selected)
        return re.sub(r"\s+", " ", "\n".join(page.text for page in selected)), detail

    def _business_rider_components(
        self, pages: list[DocumentPage], key: str, year: int, effective: str, year_end: str, source_url: str,
    ) -> list[RateComponent]:
        """Read this class's own FAM, DSM and storm rows (key: small, general, large or an industrial key)."""
        def number(token: str) -> float:
            return -float(token[1:-1]) if token.startswith("(") else float(token)

        N = r"\(?\d+\.\d+\)?"
        C = rf"({N})"

        rows = {
            "small": {
                "label": "Small General, Small General TOU and Small General Critical Peak",
                "fam": r"Small General, Small General Time of Use, Small General Critical Peak (\d+\.\d+) (\d+\.\d+) Pricing",
                "dsm": r"Small General, Small General Time of Use, Small (\d+\.\d+) (\(?\d+\.\d+\)?) (\d+\.\d+) General Critical Peak Pricing",
                "storm": r"Small General, Small General Time-of-Use, Small General Critical Peak (\d+\.\d+) Pricing",
            },
            "general": {
                "label": "General, General TOU, General Critical Peak and Multi-Unit Residential Building (MURB) TOU",
                "fam": r"(?<!Small )General, General Time of Use, (\d+\.\d+) (\d+\.\d+) General Critical Peak, Multi-Unit "
                       r".*?Residential Building \(MURB\) Time of Use Large General",
                "dsm": r"General, General Time of Use, General Critical Peak (\d+\.\d+) (\(?\d+\.\d+\)?) (\d+\.\d+) "
                       r"Pricing, Multi-unit Residential Building Time-of-Use Large General",
                "storm": r"General, General Time-of-Use, General Critical Peak Pricing, Multi-unit (\d+\.\d+) "
                         r"Residential Building Time-of-Use Large General",
            },
            "large": {
                "label": "Large General",
                "fam": r"Residential Building \(MURB\) Time of Use Large General (\d+\.\d+) (\d+\.\d+) Small Industrial",
                "dsm": r"Time-of-Use Large General (\d+\.\d+) (\(?\d+\.\d+\)?) (\d+\.\d+) Small Industrial",
                "storm": r"Residential Building Time-of-Use Large General (\d+\.\d+) Small Industrial",
            },
            # Industrial row labels are unique within each current-year rider table; capture only this class's values.
            "small_industrial": {
                "label": "Small Industrial",
                "fam": rf"Small Industrial {C} {C} Medium Industrial",
                "dsm": rf"Small Industrial {C} {C} {C} Medium Industrial",
                "storm": rf"Small Industrial {C} Medium Industrial",
            },
            "medium_industrial": {
                "label": "Medium Industrial",
                "fam": rf"Medium Industrial {C} {C} Large Industrial Firm",
                "dsm": rf"Medium Industrial {C} {C} {C} Large Industrial including Interruptible Rider",
                "storm": rf"Medium Industrial {C} Large Industrial including Interruptible Rider",
            },
            "large_firm": {
                "label": "Large Industrial Firm (FAM); Large Industrial including Interruptible Rider (DSM, storm)",
                "fam": rf"Large Industrial Firm {C} {C} Large Industrial Interruptible",
                "dsm": rf"Large Industrial including Interruptible Rider {C} {C} {C} Municipal",
                "storm": rf"Large Industrial including Interruptible Rider {C} Municipal",
            },
            "large_interruptible": {
                "label": "Large Industrial Interruptible (FAM); Large Industrial including Interruptible Rider (DSM, storm)",
                "fam": rf"Large Industrial Interruptible {C} {C} Municipal",
                "dsm": rf"Large Industrial including Interruptible Rider {C} {C} {C} Municipal",
                "storm": rf"Large Industrial including Interruptible Rider {C} Municipal",
            },
        }[key]

        text, fam_detail = self._joined_rider_text(pages, "FUEL ADJUSTMENT MECHANISM (FAM) TARIFF")
        current = re.search(rf"\b{year}\b(.*?)(?:\b{year + 1}\b|$)", text)
        row = re.search(rows["fam"], current.group(1) if current else "")
        if not row or "cents per kWh" not in text or row.group(1) != row.group(2):
            raise ValueError(f"Missing FAM row for {rows['label']}")
        fam = number(row.group(2))

        text, dsm_detail = self._joined_rider_text(pages, "DEMAND SIDE MANAGEMENT COST RECOVERY RIDER")
        row = re.search(rows["dsm"], text)
        if not row or f"January 1, {year} to December 31, {year}" not in text or "cents per kWh" not in text:
            raise ValueError(f"Missing DSM row for {rows['label']}")
        program, balance, dsm = number(row.group(1)), number(row.group(2)), number(row.group(3))
        if abs(program + balance - dsm) > 0.0011:
            raise ValueError(f"Changed DSM breakdown for {rows['label']}")

        text, storm_detail = self._joined_rider_text(pages, "STORM COST RECOVERY RIDER")
        row = re.search(rows["storm"], text)
        if not row or f"SCRR RATES FOR {year}" not in text or "cents per kWh" not in text:
            raise ValueError(f"Missing storm row for {rows['label']}")
        storm = number(row.group(1))

        note = f"Published row: {rows['label']}. Mandatory rider, separate from base energy."
        riders = [
            RateComponent("rider", "FAM Actual/Balance Adjustment (Combined)", round(fam / 100, 6), "$/kWh",
                          source_detail=fam_detail, effective_date=effective, end_date=year_end, notes=note),
            RateComponent("rider", "DSM Cost Recovery Rider", round(dsm / 100, 6), "$/kWh",
                          source_detail=dsm_detail, effective_date=date(year, 1, 1).isoformat(), end_date=year_end,
                          notes=f"Combined PCR {program} and BA {balance} cents/kWh; do not add the subcomponents again. {note}"),
            RateComponent("rider", "Storm Cost Recovery Rider", round(storm / 100, 6), "$/kWh",
                          source_detail=storm_detail, effective_date=effective, end_date=year_end, notes=note),
        ]
        for component in riders:
            component.source_url = source_url
        return riders

    def _parse_business_tariff(
        self, pages: list[DocumentPage], code: str, context: tuple[int, str, str, str], source_url: str,
    ) -> TariffRecord:
        """Parse one of Rate 10/11/12 with base charges, riders and minimum bill kept separate."""
        year, effective, _today, year_end = context
        nxt = f"Effective January 1, {year + 1}"
        spec = {
            "10": (r"SMALL GENERAL TARIFF Page (\d+) of (\d+) Rate Code 10", "Small General tariff",
                   "Small Commercial", "small commercial", "tiered", "small"),
            "11": (r"GENERAL TARIFF Page (\d+) of (\d+) Rate Code 11", "General tariff",
                   "Commercial General Demand", "general demand", "demand", "general"),
            "12": (r"LARGE GENERAL TARIFF Page (\d+) of (\d+) \(2,000 kVA or 1,800 kW and over\) Rate Code 12",
                   "Large General tariff", "Large Commercial", "large commercial", "demand", "large"),
        }[code]
        selected = self._continuous_pages(pages, spec[0], spec[1])
        text = re.sub(r"\s+", " ", "\n".join(page.text for page in selected)).replace("\u2019", "'")
        detail = f"Rate Code {code}; PDF pages " + ", ".join(str(page.page_number) for page in selected)
        order = r"Effective upon the date of the \$(\d+\.\d+) Board's Order " + nxt + r" \$(\d+\.\d+)"
        plain = r"Effective upon the date of the (\d+\.\d+) Board's Order " + nxt + r" (\d+\.\d+)"
        components: list[RateComponent] = []

        def positive(*values: float) -> None:
            if min(values) <= 0:
                raise ValueError(f"Non-positive Rate {code} amount")

        if code == "10":
            fixed = re.search(r"CUSTOMER CHARGE per month \$(\d+\.\d{2}) " + nxt + r" \$(\d+\.\d{2}) ENERGY CHARGE", text)
            energy = re.search(
                r"ENERGY CHARGE cents per kilowatt-hour for the first 200 for all kilowatt-hours additional per month "
                r"kilowatt-hours (\d+\.\d+) (\d+\.\d+) " + nxt + r" (\d+\.\d+) (\d+\.\d+) FUEL ADJUSTMENT", text)
            minimum = re.search(
                r"MINIMUM MONTHLY CHARGE The minimum monthly charge shall be as follows: per month \$(\d+\.\d{2}) "
                r".*?per month " + nxt + r" \$(\d+\.\d{2}) AVAILABILITY", text)
            availability = re.search(r"AVAILABILITY (.*?) Effective:", text)
            required = ("less than 32,000 kWh per year", "less than 45,000 kWh per year", "written request", "minimum of six months")
            if not (fixed and energy and minimum and availability) or not all(p in availability.group(1) for p in required):
                raise ValueError("Missing or changed Small General charges or eligibility")
            positive(float(fixed.group(1)), float(minimum.group(1)), *(float(v) for v in energy.groups()[:2]))
            tiers = [("Energy Charge - First 200 kWh", float(energy.group(1)), 1, 200.0),
                     ("Energy Charge - Balance", float(energy.group(2)), 2, None)]
            components.append(RateComponent("fixed", "Customer Charge", float(fixed.group(1)), "$/month",
                                            notes="Monthly customer charge"))
            for name, price, tier, threshold in tiers:
                components.append(RateComponent(
                    "energy", name, round(price / 100, 6), "$/kWh", tier_number=tier, tier_threshold=threshold,
                    tier_unit="kWh/month" if threshold else None,
                    notes="First 200 kWh per month" if threshold else "All kWh beyond the first 200 kWh per month"))
            floor = minimum.group(1)
            conditions = (
                f"The ${floor} minimum monthly charge is a minimum-bill condition, not an additional fixed charge. "
                "General-tariff customers may elect this tariff on written request (two class switches per 24 months; six-month minimum stay)."
            )
        else:
            large = code == "12"
            unit, amount = ("kVA", "kilovolt ampere") if large else ("kW", "kilowatt")
            if large:
                demand = re.search(
                    r"DEMAND CHARGE As follows, per month per kilovolt ampere of maximum demand of the current month or the maximum "
                    r"actual demand of the previous December, January, or February occurring in the previous eleven \(11\) months\. "
                    r"per month " + order + r" (\d+) cents per kilovolt ampere reduction in demand charge where the transformer is owned by the customer\.", text)
                energy = re.search(r"ENERGY CHARGE cents per kilowatt-hour " + plain + r" FUEL ADJUSTMENT", text)
                minimum = re.search(
                    r"MINIMUM MONTHLY CHARGE The minimum monthly charge shall be as follows\. per month " + order + r" AVAILABILITY", text)
                availability = re.search(r"AVAILABILITY (.*?) SPECIAL CONDITIONS", text)
                required = ("any use except industrial", "2,000 kVA or 1,800 kW and over")
            else:
                demand = re.search(
                    r"DEMAND CHARGE per month per kilowatt of maximum demand " + order + r" (\d+) cents per kilowatt reduction in demand charge where "
                    r"the transformer was owned by the customer prior to February 1, 1974, or under Special Condition \(2\)", text)
                energy = re.search(
                    r"ENERGY CHARGE cents per kilowatt-hour for the first 200 kilowatt- for all additional hours per month per kilowatt "
                    r"kilowatt-hours of maximum demand Effective upon the date of the (\d+\.\d+) (\d+\.\d+) Board's Order " + nxt +
                    r" (\d+\.\d+) (\d+\.\d+) FUEL ADJUSTMENT", text)
                minimum = re.search(
                    r"MAXIMUM PER KWH CHARGE/MINIMUM BILL .*? per month " + order + r" AVAILABILITY", text)
                availability = re.search(r"AVAILABILITY (.*?) SPECIAL CONDITIONS", text)
                required = ("32,000 kWh, or greater", "written request", "minimum of six months")
            if not (demand and energy and minimum and availability) or not all(p in availability.group(1) for p in required):
                raise ValueError(f"Missing or changed Rate {code} charges or eligibility")
            if demand.group(3) != "32":
                raise ValueError("Changed transformer-ownership credit")
            positive(float(demand.group(1)), float(minimum.group(1)), *(float(v) for v in energy.groups()[:2]))
            components.append(RateComponent(
                "demand", "Demand Charge", float(demand.group(1)), f"$/{unit}/month", demand_unit=unit,
                notes=f"Per {amount} of maximum demand."))
            components.append(RateComponent(
                "rebate", "Customer-Owned Transformer Demand Reduction", -0.32, f"$/{unit}/month", demand_unit=unit,
                sub_component="conditional", notes=f"32 cents per {amount} reduction in the demand charge, only where the customer owns the transformer as the tariff states."))
            if large:
                positive(float(energy.group(1)))
                components.append(RateComponent("energy", "Energy Charge", round(float(energy.group(1)) / 100, 6), "$/kWh",
                                                notes="Flat rate for all kWh."))
            else:
                components.append(RateComponent(
                    "energy", "Energy Charge - First 200 kWh per kW", round(float(energy.group(1)) / 100, 6), "$/kWh",
                    tier_number=1, tier_threshold=200.0, tier_unit="kWh/kW of maximum demand/month",
                    notes="First 200 kWh per month per kW of maximum demand."))
                components.append(RateComponent(
                    "energy", "Energy Charge - Balance", round(float(energy.group(2)) / 100, 6), "$/kWh", tier_number=2,
                    notes="All kWh beyond the first 200 kWh per kW of maximum demand per month."))
            floor = minimum.group(1)
            if large:
                conditions = (
                    f"The ${floor} minimum monthly charge is a minimum-bill condition, not an additional fixed charge. "
                    "Demand is the higher of the current month or the previous December-February maximum within eleven months. "
                    "Primary metering reads reduce by 1.1% (69 kV or higher, metered high side) or increase by 1.1% (below 69 kV, metered low side). "
                    "Availability is withdrawn if billing demand is not consistently 2,000 kVA or 1,800 kW."
                )
            else:
                conditions = (
                    f"The ${floor} minimum monthly bill is a condition, not an additional fixed charge; the maximum charge per kWh is that for a 10% billing load factor. "
                    "Primary metering reads reduce by 1.9%. Customers eligible for Small General may elect that tariff on written request."
                )
        for component in components:
            component.source_url = source_url
            component.source_detail = detail
            component.effective_date = effective
            component.end_date = year_end
        riders = self._business_rider_components(pages, spec[5], year, effective, year_end, source_url)
        return TariffRecord(
            utility_name="Nova Scotia Power", province="NS", utility_type="electricity",
            tariff_name=spec[2], tariff_code=code, customer_class="commercial", sub_class=spec[3],
            rate_structure=spec[4], effective_date=effective, end_date=year_end, source_url=source_url, source_page=detail,
            eligibility=re.sub(r"\s+", " ", availability.group(1)).strip(),
            notes=(
                f"NS Power Rate {code}; first published column of the approved May 2026 book (Board-order date verified on the residential rate pages; "
                f"the {year + 1} column is not used). Base charges and the mandatory FAM, DSM and storm riders are separate; "
                "no bill total is calculated. " + conditions
            ),
            components=components + riders,
        )

    def _parse_business_tariffs(
        self, pages: list[DocumentPage], products: dict[str, str], source_url: str,
    ) -> list[TariffRecord]:
        """Parse Rate 10/11/12 independently; a failed class is logged and omitted."""
        context = self._order_context(pages, {kind: parse_html(html).get_text(" ", strip=True) for kind, html in products.items()})
        if not context:
            return []
        records: list[TariffRecord] = []
        for code in ("10", "11", "12"):
            try:
                records.append(self._parse_business_tariff(pages, code, context, source_url))
            except (ValueError, IndexError) as exc:
                self.logger.warning("NSPower Rate %s incomplete: %s", code, exc)
        return records

    # ── Industrial: Small 21, Medium 22, Large 23 firm and Interruptible Rider 25 ──

    def _parse_industrial_tariff(
        self, pages: list[DocumentPage], code: str, context: tuple[int, str, str, str], source_url: str,
    ) -> TariffRecord:
        """Parse one industrial size class; base charges, conditional credits, riders and minimum bill stay separate."""
        year, effective, _today, year_end = context
        nxt = f"Effective January 1, {year + 1}"
        order = r"Effective upon the date of the \$(\d+\.\d+) Board's Order " + nxt + r" \$(\d+\.\d+)"
        header, label = {
            "21": (r"SMALL INDUSTRIAL TARIFF Page (\d+) of (\d+) \(up to 249 kVA or 224 kW\) Rate Code 21", "Small Industrial tariff"),
            "22": (r"MEDIUM INDUSTRIAL TARIFF Page (\d+) of (\d+) \(250 kVA or 225 kW to 1,999 kVA or 1,799 kW\) Rate Code 22",
                   "Medium Industrial tariff"),
            "23": (r"LARGE INDUSTRIAL TARIFF Page (\d+) of (\d+) \(2,000 kVA or 1,800 kW and over\) Rate Code 23", "Large Industrial tariff"),
            "25": (r"LARGE INDUSTRIAL TARIFF Page (\d+) of (\d+) \(2,000 kVA or 1,800 kW and over\) Rate Code 23", "Large Industrial tariff"),
        }[code]
        selected = self._continuous_pages(pages, header, label)
        text = re.sub(r"\s+", " ", "\n".join(page.text for page in selected)).replace("\u2019", "'")
        detail = "Rate Code 23" + (" Interruptible Rider (Rate Code 25)" if code == "25" else "") if code in ("23", "25") else f"Rate Code {code}"
        detail += "; PDF pages " + ", ".join(str(page.page_number) for page in selected)
        availability = re.search(r"AVAILABILITY (.*?) SPECIAL CONDITIONS", text)

        def demand_component(value: str) -> RateComponent:
            return RateComponent("demand", "Demand Charge", float(value), "$/kVA/month", demand_unit="kVA",
                                 notes="Per kilovolt ampere of maximum demand.")

        def transformer_credit(cents: str, condition: str) -> RateComponent:
            if cents != "32":
                raise ValueError("Changed transformer-ownership credit")
            return RateComponent(
                "rebate", "Customer-Owned Transformer Demand Reduction", -0.32, "$/kVA/month", demand_unit="kVA",
                sub_component="conditional", notes=f"32 cents per kilovolt ampere reduction in the demand charge, only where {condition}.")

        components: list[RateComponent] = []
        if code == "21":
            demand = re.search(
                r"DEMAND CHARGE per month per kilovolt ampere of maximum demand " + order + r" (\d+) cents per kilovolt ampere "
                r"reduction in demand charge where the transformer was owned by the customer prior to February 1, 1974, or under "
                r"Special Condition \(2\)", text)
            energy = re.search(
                r"ENERGY CHARGE cents per kilowatt-hour for the first 200 kilowatt-hours for all additional per month per kilovolt ampere "
                r"kilowatt-hours of maximum demand Effective upon the date of the (\d+\.\d+) (\d+\.\d+) Board's Order " + nxt +
                r" (\d+\.\d+) (\d+\.\d+) FUEL ADJUSTMENT", text)
            minimum = re.search(r"MAXIMUM PER KWH CHARGE/MINIMUM BILL The maximum charge per kWh will be that for a billing load "
                                r"factor of 10% .*?per month " + order + r" AVAILABILITY", text)
            required = ("for industrial use", "regular billing demand is less than 250 kVA or 225 kW")
            if not (demand and energy and minimum and availability) or not all(p in availability.group(1) for p in required) \
                    or "Meter readings shall then be reduced by 1.9%" not in text:
                raise ValueError("Missing or changed Small Industrial charges or eligibility")
            first, balance = float(energy.group(1)), float(energy.group(2))
            if min(float(demand.group(1)), float(minimum.group(1)), first, balance) <= 0:
                raise ValueError("Non-positive Rate 21 amount")
            components += [
                demand_component(demand.group(1)),
                transformer_credit(demand.group(3), "the customer owned the transformer prior to February 1, 1974, or under Special Condition (2)"),
                RateComponent("energy", "Energy Charge - First 200 kWh per kVA", round(first / 100, 6), "$/kWh", tier_number=1,
                              tier_threshold=200.0, tier_unit="kWh/kVA of maximum demand/month",
                              notes="First 200 kWh per month per kVA of maximum demand."),
                RateComponent("energy", "Energy Charge - Balance", round(balance / 100, 6), "$/kWh", tier_number=2,
                              notes="All kWh beyond the first 200 kWh per kVA of maximum demand per month."),
            ]
            name, sub_class, rider_key = "Small Industrial", "small industrial", "small_industrial"
            conditions = (
                f"The ${minimum.group(1)} minimum monthly bill is a condition, not an additional fixed charge; the maximum charge per kWh is that for a "
                "10% billing load factor. High-voltage-side metering reads reduce by 1.9%."
            )
        elif code == "22":
            demand = re.search(
                r"DEMAND CHARGE per month per kilovolt ampere of maximum demand " + order + r" (\d+) cents per kilovolt ampere "
                r"reduction in demand charge where the transformer is owned by the customer\.", text)
            energy = re.search(r"ENERGY CHARGE cents per kilowatt- hour Effective upon the date of the (\d+\.\d+) Board's Order " + nxt +
                               r" (\d+\.\d+) FUEL ADJUSTMENT", text)
            minimum = re.search(r"MINIMUM MONTHLY CHARGE The minimum monthly charge shall be as follows\..*?per month " + order + r" AVAILABILITY", text)
            required = ("any industrial customer having a regular billing demand of 250 kVA (225 kW) and over",)
            if not (demand and energy and minimum and availability) or not all(p in availability.group(1) for p in required) \
                    or "Meter readings shall then be reduced by 1.1%" not in text:
                raise ValueError("Missing or changed Medium Industrial charges or eligibility")
            if min(float(demand.group(1)), float(minimum.group(1)), float(energy.group(1))) <= 0:
                raise ValueError("Non-positive Rate 22 amount")
            components += [
                demand_component(demand.group(1)),
                transformer_credit(demand.group(3), "the customer owns the transformer"),
                RateComponent("energy", "Energy Charge", round(float(energy.group(1)) / 100, 6), "$/kWh", notes="Flat rate for all kWh."),
            ]
            name, sub_class, rider_key = "Medium Industrial", "medium industrial", "medium_industrial"
            conditions = (
                f"The ${minimum.group(1)} minimum monthly charge is a minimum-bill condition, not an additional fixed charge. "
                "High-voltage-side metering reads reduce by 1.1%. NSPI may withdraw availability if billing demand of 250 kVA (225 kW) is not maintained."
            )
        else:
            demand = re.search(
                r"DEMAND CHARGE As follows, per kilovolt ampere of maximum demand of the current month or the maximum actual demand of the "
                r"previous December, January, or February occurring in the previous eleven \(11\) months\. per month \$(\d+\.\d+) " + nxt +
                r" \$(\d+\.\d+) DISTRIBUTION COST ADDER For customers connected at distribution level, the following charge also applies, "
                r"subject to the same provisions as the Demand Charge section above\. per month \$(\d+\.\d+) " + nxt + r" \$(\d+\.\d+) "
                r"(\d+) cents per kilovolt ampere reduction in demand charge where the transformer is owned by the customer\.", text)
            energy = re.search(r"ENERGY CHARGE cents per kilowatt-hour Firm Interruptible Customers Customers (\d+\.\d+) (\d+\.\d+) " + nxt +
                               r" (\d+\.\d+) (\d+\.\d+) FUEL ADJUSTMENT", text)
            minimum = re.search(r"MINIMUM MONTHLY CHARGE The minimum monthly charge shall be the greater of the demand charge or the amounts "
                                r"in the table below\. per month " + order + r" AVAILABILITY", text)
            required = ("three phase", "low voltage side of the bulk power transformer",
                        "any industrial customer having a regular billing demand of 2,000 kVA or 1,800 kW and over")
            if not (demand and energy and minimum and availability) or not all(p in availability.group(1) for p in required) \
                    or "Meter readings shall be increased by 1.1% for each transformation" not in text:
                raise ValueError("Missing or changed Large Industrial charges or eligibility")
            interruptible = code == "25"
            price = float(energy.group(2 if interruptible else 1))
            if min(float(demand.group(1)), float(demand.group(3)), float(minimum.group(1)), price) <= 0:
                raise ValueError(f"Non-positive Rate {code} amount")
            components += [
                demand_component(demand.group(1)),
                RateComponent("demand", "Distribution Cost Adder", float(demand.group(3)), "$/kVA/month", demand_unit="kVA",
                              sub_component="conditional",
                              notes="Applies only to customers connected at distribution level, on the same billing demand as the Demand Charge."),
                transformer_credit(demand.group(5), "the customer owns the transformer"),
                RateComponent("energy", "Energy Charge - " + ("Interruptible" if interruptible else "Firm") + " Customers",
                              round(price / 100, 6), "$/kWh",
                              notes="Published Large Industrial energy price for " + ("interruptible" if interruptible else "firm") + " customers."),
            ]
            conditions = (
                f"The minimum monthly charge is the greater of the demand charge or ${minimum.group(1)}; it is a condition, not an additional fixed charge. "
                "Billing demand is the higher of the current month or the previous December-February maximum within eleven months. "
                "Meter readings increase by 1.1% per transformation between meter and the bulk-supply transformer low-voltage side and are reduced "
                "for transmission-voltage metering. A written operating agreement and separate service agreement may be required."
            )
            if interruptible:
                rider = re.search(
                    r"INTERRUPTIBLE RIDER TO THE LARGE INDUSTRIAL TARIFF \(RATE CODE 25\) (.*?) reduction per kilovolt ampere reduction in "
                    r"demand charge " + order + r" AVAILABILITY (.*?) SPECIAL CONDITIONS", text)
                terms = ("interruptible billing demand at 90% Power Factor", "written notice", "within ten (10) minutes", "Performance Penalty", "five (5) year advance written notice",
                         "Interruption is limited to 16 hours per day and 5 days per week to a maximum of 30% of the hours per month and 15% of the hours in a year")
                if not rider or "billed interruptible demand" not in rider.group(1) or not all(t in rider.group(4) for t in terms) \
                        or float(rider.group(2)) <= 0:
                    raise ValueError("Missing or changed Interruptible Rider credit or terms")
                components.append(RateComponent(
                    "rebate", "Interruptible Demand Credit", -float(rider.group(2)), "$/kVA/month", demand_unit="kVA",
                    sub_component="conditional",
                    notes=("Reduction applies only to billed interruptible demand (total billing demand minus contracted firm demand; "
                           "none when billing demand is below contracted firm demand). Not a credit on all demand.")))
                name, sub_class, rider_key = "Large Industrial - Interruptible Rider", "large industrial interruptible", "large_interruptible"
                conditions += (
                    " Interruptible service requires an agreed interruptible billing demand at 90% power factor, written notice, a dedicated telephone "
                    "and load reduction within 10 minutes of NSPI notice; interruption is limited to 16 h/day, 5 days/week, 30% of monthly and 15% of "
                    "annual hours. Non-compliance incurs Threshold and Performance Penalties (not modelled); return to firm service needs five years' "
                    "notice. The Demand Charge applies to total billing demand and the credit reduces it only for billed interruptible demand."
                )
                eligibility = (availability.group(1).strip() + " Interruptible Rider (Rate Code 25): an agreed interruptible billing demand "
                               "at 90% power factor, on written notice identifying firm and interruptible load.")
            else:
                name, sub_class, rider_key = "Large Industrial - Firm", "large industrial firm", "large_firm"
                conditions += " NSPI may withdraw availability from firm-only customers not consistently maintaining 2,000 kVA or 1,800 kW."
        for component in components:
            component.source_url = source_url
            component.source_detail = detail
            component.effective_date = effective
            component.end_date = year_end
        riders = self._business_rider_components(pages, rider_key, year, effective, year_end, source_url)
        if code != "25":
            eligibility = re.sub(r"\s+", " ", availability.group(1)).strip()
        return TariffRecord(
            utility_name="Nova Scotia Power", province="NS", utility_type="electricity",
            tariff_name=name, tariff_code=code, customer_class="industrial", sub_class=sub_class,
            rate_structure="demand", effective_date=effective, end_date=year_end, source_url=source_url, source_page=detail,
            eligibility=eligibility,
            notes=(
                f"NS Power Rate {code}; first published column of the approved May 2026 book (Board-order date verified on the residential rate pages; "
                f"the {year + 1} column is not used). Base charges, conditional credits and the mandatory FAM, DSM and storm riders are separate; "
                "no bill total is calculated. " + conditions
            ),
            components=components + riders,
        )

    def _parse_industrial_tariffs(
        self, pages: list[DocumentPage], products: dict[str, str], source_url: str,
    ) -> list[TariffRecord]:
        """Parse Rate 21/22/23 and the Rate 25 Interruptible Rider independently; a failed class is logged and omitted."""
        context = self._order_context(pages, {kind: parse_html(html).get_text(" ", strip=True) for kind, html in products.items()})
        if not context:
            return []
        records: list[TariffRecord] = []
        for code in ("21", "22", "23", "25"):
            try:
                records.append(self._parse_industrial_tariff(pages, code, context, source_url))
            except (ValueError, IndexError) as exc:
                self.logger.warning("NSPower industrial Rate %s incomplete: %s", code, exc)
        return records

    # ── Business time-varying pilots 72/73/82/83 ──

    def _parse_business_pilot(
        self, pages: list[DocumentPage], code: str, context: tuple[int, str, str, str], source_url: str,
        business_text: str,
    ) -> TariffRecord:
        """Parse one closed-enrollment pilot: interim standard-price phase until its dated November start."""
        year, effective, today, year_end = context
        nxt = f"Effective January 1, {year + 1}"
        title, name, key, cpp, general = {
            "72": ("SMALL GENERAL CRITICAL PEAK PRICING", "Small General Critical Peak Pricing Pilot (Rate 72)", "small", True, False),
            "82": ("SMALL GENERAL TIME OF USE", "Small General Time-of-Use Pilot (Rate 82)", "small", False, False),
            "73": ("GENERAL CRITICAL PEAK PRICING", "General Critical Peak Pricing Pilot (Rate 73)", "general", True, True),
            "83": ("GENERAL TIME OF USE", "General Time-of-Use Pilot (Rate 83)", "general", False, True),
        }[code]
        if "Applications for the Time-of-Use Rate Pilot and Critical Peak Pricing Rate Pilot are now closed" not in business_text:
            raise ValueError("Pilot enrollment status not verified")
        selected = self._continuous_pages(pages, rf"{title} TARIFF Page (\d+) of (\d+) Rate Code {code}", f"Rate {code}")
        raw = "\n".join(page.text for page in selected).replace("\u2019", "'")
        text = re.sub(r"\s+", " ", raw)
        detail = f"Rate Code {code}; PDF pages " + ", ".join(str(page.page_number) for page in selected)
        scope = "General" if general else "Small General"
        required = ("standard Smart Meter", f"eligible for service under the {scope} Tariff", "close enrollment",
                    "commence service under this tariff on November 1st", "standard offer rates",
                    "FUEL ADJUSTMENT MECHANISM", "DSM COST RECOVERY RIDER", "STORM COST RECOVERY RIDER")
        if not all(label in text for label in required):
            raise ValueError("Missing pilot eligibility or rider context")
        transition = re.search(r"until October 31, (\d{4})\. Effective November 1, \1", text)
        if not transition or int(transition.group(1)) != year:
            raise ValueError("Missing or unsupported interim transition")
        transition_date = date(year, 11, 1).isoformat()

        order = r"Effective upon the date of the \$(\d+\.\d+) Board's Order " + nxt + r" \$(\d+\.\d+)"
        components: list[RateComponent] = []
        if general:
            demand = re.search(
                r"DEMAND CHARGE per month per kilowatt of maximum demand " + order + r" (\d+) cents per kilowatt reduction in demand charge "
                r"where the transformer was owned by the customer prior to February 1, 1974, or under Special Condition \(2\)", text)
            if not demand or demand.group(3) != "32" or float(demand.group(1)) <= 0:
                raise ValueError("Missing or changed pilot demand charge")
            components.append(RateComponent("demand", "Demand Charge", float(demand.group(1)), "$/kW/month", demand_unit="kW",
                                            notes="Per kilowatt of maximum demand."))
            components.append(RateComponent("rebate", "Customer-Owned Transformer Demand Reduction", -0.32, "$/kW/month", demand_unit="kW",
                                            sub_component="conditional", notes="32 cents per kilowatt reduction only where the customer owns the transformer as the tariff states."))
            minimum = re.search(r"MINIMUM BILL .*?per month " + order, text)
            floor_label = "minimum monthly bill"
        else:
            fixed = re.search(r"CUSTOMER CHARGE per month " + order.replace(r"\$(\d+\.\d+)", r"\$(\d+\.\d{2})"), text)
            if not fixed or float(fixed.group(1)) <= 0:
                raise ValueError("Missing or changed pilot customer charge")
            components.append(RateComponent("fixed", "Customer Charge", float(fixed.group(1)), "$/month", notes="Monthly customer charge"))
            minimum = re.search(r"MINIMUM MONTHLY CHARGE .*?per month " + order, text)
            floor_label = "minimum monthly charge"
        if not minimum or float(minimum.group(1)) <= 0:
            raise ValueError("Missing pilot minimum bill")
        floor = minimum.group(1)

        tier_unit = "kWh/kW of maximum demand/month" if general else "kWh/month"
        tier_note = ("First 200 kWh per month per kW of maximum demand" if general else "First 200 kWh per month")
        heading = re.search(r"(?<!INTERIM )ENERGY CHARGE cents per", text)
        if not heading or "INTERIM ENERGY CHARGE" not in text:
            raise ValueError("Missing energy sections")
        interim_text = text[text.index("INTERIM ENERGY CHARGE"):heading.start()]
        approved = text[heading.start():]
        if not re.search(r"cents per.{0,40}kilowatt-hour", approved[:200]) or (cpp and not re.search(r"(?i)first 200", approved)):
            raise ValueError("Missing approved energy units")

        def tiers(prefix: str, first: float, balance: float) -> list[RateComponent]:
            if min(first, balance) <= 0:
                raise ValueError("Invalid pilot energy value")
            return [
                RateComponent("energy", f"{prefix} - First 200 kWh", round(first / 100, 6), "$/kWh", tier_number=1,
                              tier_threshold=200.0, tier_unit=tier_unit, notes=tier_note),
                RateComponent("energy", f"{prefix} - Balance", round(balance / 100, 6), "$/kWh", tier_number=2,
                              notes="All kWh beyond the first 200 kWh" + (" per kW of maximum demand per month" if general else " per month")),
            ]

        start, end = effective, date(year, 10, 31).isoformat()
        structure = "demand" if general else "tiered"
        variant = "pilot - interim standard pricing"
        conditions = (
            f"The ${floor} {floor_label} is a minimum-bill condition, not an additional fixed charge. "
            "Pilot enrollment is closed to new applications; service must start November 1 unless NSPI grants a waiver; standard Smart Meter required; "
            "no seasonal or net-metering service as listed in the tariff. Base energy and mandatory FAM, DSM and storm riders are separate; no bill total is calculated."
        )
        if today < transition_date:
            match = re.search(r"Effective upon the date of the (?:n/a )?(\d+\.\d+) (\d+\.\d+) Board's Order", interim_text)
            if not match:
                raise ValueError("Missing published interim energy rate")
            restoration = re.search(r"If system functionality is restored after (.*?shall remain in effect until October 31, \d{4})", text)
            if not restoration:
                raise ValueError("Missing interim applicability condition")
            components.extend(tiers("Interim Energy Charge", float(match.group(1)), float(match.group(2))))
            conditions += (
                " Conditional interim variant: the tariff applies these standard-offer-equivalent rates while system functionality is unavailable "
                "(if restored after " + restoration.group(1) + "); the scraper has not verified restoration status. "
                "Scheduled time-varying prices begin " + transition_date + " and are not substituted for this phase."
                + (" No Critical Peak Events are scheduled while interim pricing is in force." if cpp else " Billed under Rate Code " + ("11" if general else "10") + " while interim.")
            )
            if cpp and "No Critical Peak Events will be scheduled" not in text:
                raise ValueError("Missing interim no-event condition")
        else:
            start, structure, variant = transition_date, "tou", "pilot - time-varying pricing"
            row = re.search(r"Effective November 1, " + str(year) + r" ((?:\d+\.\d+ ?)+)", approved)
            prices = [float(v) for v in re.findall(r"\d+\.\d+", row.group(1))] if row else []
            if cpp:
                if len(prices) != 3 or "four-hour duration" not in text or "6:00 AM and 11:00 PM" not in text:
                    raise ValueError("Missing CPP event rate or window")
                events = re.search(r"CRITICAL PEAK EVENT PROCEDURE (.*?)FUEL ADJUSTMENT MECHANISM", text)
                if not events or "No more than 18" not in events.group(1) or "day prior" not in events.group(1) or "holidays" not in events.group(1):
                    raise ValueError("Missing critical-peak event limits, holidays or notice")
                if min(prices) <= 0:
                    raise ValueError("Invalid pilot energy value")
                components.append(RateComponent(
                    "energy", "Critical Peak Event Energy", round(prices[0] / 100, 6), "$/kWh", tou_period="critical-peak",
                    tou_hours="Declared four-hour events between 06:00 and 23:00 in the Nov 1-Mar 31 winter period; listed holidays excluded",
                    season="winter", season_months="11,12,1,2,3"))
                components.extend(tiers("Non-Critical Energy", prices[1], prices[2]))
                conditions += " Published event conditions: " + events.group(1)
            else:
                if len(prices) != 4 or prices[0] != prices[2] or prices[1] != prices[3] or min(prices) <= 0:
                    raise ValueError("Incomplete current TOU energy columns")
                clocks = re.findall(r"\d{1,2}:\d{2} [AP]M", approved[:row.start()])
                holidays = re.search(r"Note 1: (.*?)FUEL ADJUSTMENT MECHANISM", approved)
                if len(clocks) != 8 or not holidays or "off-peak price also applies to all hours on Saturdays, Sundays" not in approved \
                        or "November 1 through March 31" not in approved:
                    raise ValueError("Missing TOU hours, weekend rule or season")
                windows = [f"{clocks[i]} to {clocks[i + 4]}" for i in range(4)]
                components.extend([
                    RateComponent("energy", "Winter On-Peak Energy", round(prices[0] / 100, 6), "$/kWh", tou_period="on-peak",
                                  tou_hours=f"Monday-Friday {windows[0]} and {windows[2]}, excluding listed holidays", season="winter", season_months="11,12,1,2,3"),
                    RateComponent("energy", "Winter Off-Peak Energy", round(prices[1] / 100, 6), "$/kWh", tou_period="off-peak",
                                  tou_hours=f"{windows[1]} and {windows[3]}; all weekends and listed/observed holidays", season="winter", season_months="11,12,1,2,3"),
                ])
                conditions += (" Published winter holiday rule: " + holidays.group(1)
                               + f" The non-winter (April-October) price is published only effective April 1, {year + 1} and is not used.")

        riders = self._business_rider_components(pages, key, year, effective, year_end, source_url)
        for component in components:
            component.source_url = source_url
            component.source_detail = detail
            component.effective_date = start
            component.end_date = end if start == effective else year_end
        availability = re.search(r"PURPOSE (.*?) (?:CUSTOMER CHARGE|DEMAND CHARGE)", text)
        availability_text = (availability.group(1) if availability else "") + " Pilot closed to new applications; " + (
            "conditional interim standard-price variant." if today < transition_date else "time-varying winter phase.")
        record_end = end if start == effective else year_end
        return TariffRecord(
            utility_name="Nova Scotia Power", province="NS", utility_type="electricity",
            tariff_name=name + " - Conditional Pilot", tariff_code=code, customer_class="commercial",
            sub_class=("general demand " if general else "small commercial ") + variant,
            rate_structure=structure, effective_date=start, end_date=record_end, source_url=source_url, source_page=detail,
            eligibility=availability_text.strip(), notes=conditions, components=components + riders,
        )

    def _parse_business_pilot_tariffs(
        self, pages: list[DocumentPage], products: dict[str, str], source_url: str, business_html: str,
    ) -> list[TariffRecord]:
        """Parse Rates 72/73/82/83 independently; a failed pilot is logged and omitted."""
        context = self._order_context(pages, {kind: parse_html(html).get_text(" ", strip=True) for kind, html in products.items()})
        if not context:
            return []
        business_text = parse_html(business_html).get_text(" ", strip=True)
        records: list[TariffRecord] = []
        for code in ("72", "73", "82", "83"):
            try:
                records.append(self._parse_business_pilot(pages, code, context, source_url, business_text))
            except (ValueError, IndexError) as exc:
                self.logger.warning("NSPower business pilot %s incomplete: %s", code, exc)
        return records

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
