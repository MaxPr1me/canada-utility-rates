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

import copy
import logging
import re
from datetime import date
from typing import Optional
from urllib.parse import urljoin

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import (
    parse_html, detect_js_rendered, find_pdf_links, extract_pdf_pages,
    extract_effective_date, DocumentPage,
)

logger = logging.getLogger(__name__)

RATE_SCHEDULES_URL = "https://yukonenergy.ca/customer-service/rates/rate-schedules/"

# Cross-reference residential sections: (start, end lookahead, [(code, row label, title, sub_class)]).
# Codes sharing one section share one printed column; 1160 anchors the document.
RESIDENTIAL_SECTIONS = (
    (r"Residential Rate Schedules\s+1160 Hydro Non-Govt", r"\n1460 Old Crow Non-Govt", (
        ("1160", "Hydro Non-Govt", "Hydro", "hydro non-government"),
        ("1260", "Small Diesel Non-Govt", "Small Diesel", "small diesel non-government"),
        ("1360", "Large Diesel Non-Govt", "Large Diesel", "large diesel non-government"),
    )),
    (r"\n1460 Old Crow Non-Govt", r"\n1180 Hydro Govt", (
        ("1460", "Old Crow Non-Govt", "Old Crow Diesel", "old crow diesel non-government"),
    )),
    (r"\n1180 Hydro Govt", r"\n1480 Old Crow Govt", (
        ("1180", "Hydro Govt", "Hydro, Government", "hydro government"),
        ("1280", "Small Diesel Govt", "Small Diesel, Government", "small diesel government"),
        ("1380", "Large Diesel Govt", "Large Diesel, Government", "large diesel government"),
    )),
    (r"\n1480 Old Crow Govt", r"\nGeneral Service Rate Schedules|\Z", (
        ("1480", "Old Crow Govt", "Old Crow Diesel, Government", "old crow diesel government"),
    )),
)

# Joint YECL/YEC rate-schedule book (text PDF) published by ATCO Electric Yukon; it carries the
# minimum bills, availability and general-service terms that Yukon Energy's own PDFs show only as images.
JOINT_RATES_PAGE_URL = "https://www.atcoelectricyukon.com/en-ca/services-rates/understanding-rates.html"
JOINT_SCHEDULE_URL = (
    "https://www.atcoelectricyukon.com/content/dam/aey-website/en-ca/assets/services-rates/"
    "yecl-yec-rate-schedules-10-2026.pdf"
)

GENERAL_SERVICE_SCHEDULES = {
    "2160": ("Hydro, Non-Government", "hydro non-government"),
    "2260": ("Small Diesel, Non-Government", "small diesel non-government"),
    "2360": ("Large Diesel, Non-Government", "large diesel non-government"),
    "2460": ("Old Crow Diesel, Non-Government", "old crow diesel non-government"),
    "2170": ("Hydro, Municipal Government", "hydro municipal government"),
    "2270": ("Small Diesel, Municipal Government", "small diesel municipal government"),
    "2370": ("Large Diesel, Municipal Government", "large diesel municipal government"),
    "2470": ("Old Crow Diesel, Municipal Government", "old crow diesel municipal government"),
    "2180": ("Hydro, Federal & Territorial Government", "hydro federal/territorial government"),
    "2280": ("Small Diesel, Federal & Territorial Government", "small diesel federal/territorial government"),
    "2380": ("Large Diesel, Federal & Territorial Government", "large diesel federal/territorial government"),
    "2480": ("Old Crow Diesel, Federal & Territorial Government", "old crow diesel federal/territorial government"),
}

_KWH = r"\s?[^\d\s$]{1,2}/kW\.h"


def parse_joint_schedules(pages: list[DocumentPage], today: str) -> dict[str, dict]:
    """Return complete residential/general-service terms by code; incomplete schedules are omitted."""
    texts = {page.page_number: re.sub(r"\s+", " ", page.text.replace("\u2013", "-")) for page in pages}
    terms: dict[str, dict] = {}
    seen: set[str] = set()
    for number, text in texts.items():
        head = re.search(r"RATE SCHEDULE -? ?([12][1-4][678]0)\b", text)
        if not head:
            continue
        code = head.group(1)
        if code in seen:
            terms.pop(code, None)
            continue
        seen.add(code)
        header = re.search(r"Effective: (\d{4}) (\d{2}) (\d{2})", text)
        scope = re.search(r"AVAILABLE: (.*?) APPLICABLE: (.*?) RATE:", text)
        if not header or not scope:
            continue
        effective = date(*(int(part) for part in header.groups())).isoformat()
        if effective > today:
            continue
        entry: dict = {"page": number, "effective": effective,
                       "available": scope.group(1).strip(), "applicable": scope.group(2).strip()}
        if code[0] == "1":
            customer = re.search(r"\(a\) Customer Charge \$(\d+\.\d+)", text)
            blocks = [re.search(label + r" (\d+\.\d+)" + _KWH, text) for label in (
                r"For the first 1,000 kW\.h", r"Between 1,001 - 2,500 kW\.h", r"For energy in excess 2,500 kW\.h")]
            minimum = re.search(r"The minimum monthly charge is the customer charge of \$(\d+\.\d+)\.", text)
            if not customer or not all(blocks) or not minimum or minimum.group(1) != customer.group(1):
                continue
            entry.update(customer=float(customer.group(1)), minimum=float(minimum.group(1)),
                         blocks=[float(block.group(1)) for block in blocks])
        else:
            demand = re.search(r"Demand Charge All kW of billing demand \$(\d+\.\d+) / kW", text)
            blocks = [re.search(label + r" (\d+\.\d+)" + _KWH, text) for label in (
                r"For the first 2,000 kW\.h", r"Between 2,001 - 15,000 kW\.h",
                r"Between 15,001 - 20,000 kW\.h", r"For energy in excess of 20,000 kW\.h")]
            minimum = re.search(r"Shall be the Demand Charge but not less than \$(\d+\.\d+)\.", text)
            billing = all(rule in text.lower() for rule in (
                "billing demand may be estimated or measured", "excluding the months april through september",
                "(d) 5 kilowatts"))
            continuation = texts.get(number + 1, "")
            power_factor = (re.search(rf"Rate Schedule -? ?{code} \(Continued\)", continuation)
                            and "power factor of 90 percent" in continuation
                            and "one kV.A shall be taken as one kW" in continuation)
            if not demand or not all(blocks) or not minimum or not billing or not power_factor:
                continue
            entry.update(demand=float(demand.group(1)), minimum=float(minimum.group(1)),
                         blocks=[float(block.group(1)) for block in blocks])
        terms[code] = entry
    return terms


def rider_a_terms(pages: list[DocumentPage]) -> Optional[str]:
    """Return the Rider A multiple-residence rule only when its full text is present."""
    text = re.sub(r"\s+", " ", " ".join(page.text for page in pages))
    if ("RIDER A MULTIPLE RESIDENCE SERVICE" in text and "Not applicable to apartments of multiple dwelling facilities" in text
            and "multiplied by the number of dwelling units" in text and "billed at the appropriate general service rate" in text):
        return ("Rider A: single detached dwellings serving more than one household are normally billed at general service; "
                "existing multiple residences on one meter may stay on the residential schedule with the minimum charge and "
                "each block's kWh multiplied by the number of dwelling units. Not applicable to apartments.")
    return None

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
        """Parse live residential/general-service schedules; unparsed seed classes stay labelled estimates."""
        live = self.live_records()
        if not live:
            return None
        replaced = {"Residential Service"}
        if any(record.sub_class and "diesel non-government" in record.sub_class
               for record in live if record.customer_class == "residential"):
            replaced.add("Residential Service — Diesel Communities")
        if any(record.customer_class == "commercial" for record in live):
            replaced.add("General Service")
        seed_only = [r for r in self._seed_data() if r.tariff_name not in replaced]
        return live + (self.mark_fallback(seed_only) if seed_only else [])

    def live_records(self) -> Optional[list[TariffRecord]]:
        """Return only live-parsed records (no seeds), or None when 1160 cannot be proven."""
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
            records = self._parse_residential_pdfs(pdf_links)
            return self.mark_live_parsed(records) if records else None
        except Exception:
            self.logger.exception("Error during Yukon Energy live scrape")
            return None

    def _joint_schedule(self) -> Optional[tuple[str, list[DocumentPage]]]:
        """Fetch the joint YECL/YEC rate-schedule book; None if unavailable or not the expected document."""
        url = JOINT_SCHEDULE_URL
        try:
            # The ATCO page is a JS shell that never settles for the shared networkidle renderer; static links only.
            html = self.fetch_page(JOINT_RATES_PAGE_URL)
            links = {urljoin(JOINT_RATES_PAGE_URL, a["href"]) for a in parse_html(html or "").find_all("a", href=True)
                     if re.search(r"rate-schedules[^/]*\.pdf$", a["href"], re.I)}
            if len(links) == 1:
                url = links.pop()
        except Exception as exc:
            self.logger.info("Joint rate page link discovery failed (%s); using %s", exc, url)
        try:
            pages = extract_pdf_pages(self.fetch_bytes(url))
        except Exception as exc:
            self.logger.warning("Joint YECL/YEC rate schedules unavailable: %s", exc)
            return None
        text = " ".join(page.text for page in pages or [])
        if "YECL/YEC Joint" not in text or "Approved in Board Order 2011-06" not in text:
            self.logger.warning("Joint YECL/YEC rate schedule document not recognised at %s", url)
            return None
        return url, pages

    def _parse_residential_pdfs(self, pdf_links: list[str]) -> Optional[list[TariffRecord]]:
        """Return residential schedules only when 1160, percentage riders, fuel and relief are proven."""
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
        percentages: dict[str, float] = {}
        rate_riders: list[RateComponent] = []
        for code, label in (("R", "AEY Rider R"), ("J", "YEC Rider J")):
            match = re.search(label + r":\s*([A-Z][a-z]+\s+\d{1,2},\s*\d{4})\s+(\d+(?:\.\d+)?)%", base_text)
            if not match:
                return None
            effective = extract_effective_date("Effective " + match.group(1))
            if not effective or effective > self.now_iso()[:10]:
                return None
            percentages[code] = float(match.group(2))
            rate_riders.append(RateComponent("rider", f"Rider {code} - Base Rate Adjustment", float(match.group(2)), "%",
                                             effective_date=effective, source_url=base_url,
                                             source_detail=f"PDF page {self._page_of(base_pages, label)}; Rider R/J effective-date header",
                                             notes="Applies to base fixed and energy charges, not to other riders."))
        shared: dict[str, RateComponent] = {}

        for kind, title in (("j1", "RIDER J1"), ("fuel", "FUEL ADJUSTMENT RIDER"), ("relief", "AFFORDABILITY RATE RELIEF REBATE")):
            source_url, pages = documents[kind]
            text = re.sub(r"\s+", " ", "\n".join(page.text for page in pages))
            header = re.search(r"\bEffective:\s*(\d{4})[ /-](\d{2})[ /-](\d{2})\b", text)
            if title not in text or not header:
                return None
            effective = date(*(int(part) for part in header.groups())).isoformat()
            if effective > self.now_iso()[:10]:
                return None
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
            shared[kind] = component

        base_effective = max(component.effective_date for component in rate_riders)
        book = self._joint_schedule()
        book_terms = parse_joint_schedules(book[1], self.now_iso()[:10]) if book else {}
        rider_a = rider_a_terms(book[1]) if book else None
        records: list[TariffRecord] = []
        for start, end, schedules in RESIDENTIAL_SECTIONS:
            match = re.search(start + r"(.*?)(?=" + end + r")", base_text, re.S)
            base_values = self._residential_base_values(match.group(1), percentages) if match else None
            if not base_values:
                if schedules[0][0] == "1160":
                    return None
                self.logger.warning("Yukon cross-reference section %s is incomplete; not published live", schedules[0][0])
                continue
            for position, (code, label, title, sub_class) in enumerate(schedules):
                if position and f"{code} {label}" not in match.group(1):
                    self.logger.warning("Yukon cross-reference no longer lists Rate %s in its column", code)
                    continue
                terms = book_terms.get(code)
                if terms and [terms["customer"], *terms["blocks"]] != base_values:
                    self.logger.warning("Rate %s joint schedule disagrees with the cross-reference", code)
                    if code == "1160":
                        return None
                    continue
                if not terms and code != "1160":
                    self.logger.warning("Rate %s minimum bill/availability not available as text; not published live", code)
                    continue
                page = self._page_of(base_pages, f"{schedules[0][0]} {schedules[0][1]}")
                government = not sub_class.endswith("non-government")
                components = [RateComponent("fixed", "Base Customer Charge", base_values[0], "$/month")]
                for index, (tier_label, threshold) in enumerate((
                    ("Energy Block 1 (first 1,000 kWh)", 1000),
                    ("Energy Block 2 (1,001-2,500 kWh)", 2500),
                    ("Energy Block 3 (over 2,500 kWh)", 2500),
                ), start=1):
                    components.append(RateComponent("energy", "Base " + tier_label, round(base_values[index] / 100.0, 6), "$/kWh",
                                                    tier_number=index, tier_threshold=threshold, tier_unit="kWh"))
                for component in components:
                    component.effective_date = base_effective
                    component.source_url = base_url
                    component.source_detail = f"PDF page {page}; Rate {code} base-rate column" + (
                        f"; matches joint schedule page {terms['page']}" if terms else "")
                    component.notes = "Published base rate before the separately listed percentage riders."
                extras = rate_riders + [shared["j1"], shared["fuel"]] + ([] if government else [shared["relief"]])
                components.extend(copy.deepcopy(component) for component in extras)
                name = "Residential Service Hydro (Rate 1160)" if code == "1160" else f"Residential Service {title} (Rate {code})"
                if terms:
                    eligibility = f"Rate {code}. Available in {terms['available']} Applicable {terms['applicable']}"
                    conditions = (f" Minimum monthly bill: the customer charge of ${terms['minimum']:.2f} (a condition, not an "
                                  f"extra charge); base schedule effective {terms['effective']}, joint rate schedules page "
                                  f"{terms['page']}. " + (rider_a or "Multiple-residence Rider A is not included."))
                else:
                    eligibility = "Single-phase secondary-voltage hydro service through one meter for one non-government household (Rate 1160)."
                    conditions = " Multiple-residence Rider A is not included."
                records.append(TariffRecord(
                    utility_name="Yukon Energy", province="YT", utility_type="electricity",
                    tariff_name=name, tariff_code=code,
                    customer_class="residential", sub_class=sub_class, rate_structure="tiered",
                    effective_date=max(component.effective_date for component in components),
                    source_url=base_url,
                    source_page=f"PDF page {page}; Rate {code}" + (f"; {book[0]} page {terms['page']}" if terms else ""),
                    eligibility=eligibility,
                    notes=("Base rates, Riders R/J/J1 and current Rider F are separate components"
                           + ("; the non-government affordability relief does not apply" if government
                              else ", with dated non-government residential relief")
                           + "; no bill total is calculated. Joint YEC/ATCO Electric Yukon schedule; the serving utility "
                           "depends on location." + conditions),
                    components=components,
                ))
        if book:
            records.extend(self._general_service_records(
                base_text, base_url, base_pages, percentages, book[0], book_terms, rate_riders, shared))
        return records

    def _general_service_records(
        self, base_text: str, base_url: str, base_pages: list[DocumentPage], percentages: dict[str, float],
        book_url: str, book_terms: dict[str, dict], rate_riders: list[RateComponent], shared: dict[str, RateComponent],
    ) -> list[TariffRecord]:
        """Build GS schedules from the joint book; block 4 must match a reconciled cross-reference row."""
        r_share, j_share = percentages["R"] / 100.0, percentages["J"] / 100.0
        block4: set[float] = set()
        for row in re.finditer(r">20000 kWh Energy Block 4\s*[^\d\w\s/$+-]{1,2}/kWh (\d+\.\d+) (\d+\.\d+) (\d+\.\d+) (\d+\.\d+)", base_text):
            base, rider_r, rider_j, total = (float(value) for value in row.groups())
            if (abs(base * r_share - rider_r) <= 0.006 and abs(base * j_share - rider_j) <= 0.006
                    and abs(base * (1 + r_share + j_share) - total) <= 0.006):
                block4.add(base)
        xref_page = self._page_of(base_pages, "General Service Rate Schedules")
        records: list[TariffRecord] = []
        for code, (title, sub_class) in GENERAL_SERVICE_SCHEDULES.items():
            terms = book_terms.get(code)
            if not terms or code not in base_text or terms["blocks"][3] not in block4:
                self.logger.warning("Rate %s general service is incomplete or not cross-checked; not published live", code)
                continue
            components = [RateComponent(
                "demand", "Base Demand Charge", terms["demand"], "$/kW", demand_unit="kW",
                notes=("Published base rate before the separately listed percentage riders. Billing demand is the greatest "
                       "of the period's highest metered demand, the highest metered demand in the 12 months ending with the "
                       "billing month excluding April-September, the estimated demand, or 5 kW; below 90% power factor "
                       "kVA is billed as kW."),
            )]
            for index, (tier_label, threshold) in enumerate((
                ("first 2,000 kWh", 2000), ("2,001-15,000 kWh", 15000),
                ("15,001-20,000 kWh", 20000), ("over 20,000 kWh", 20000),
            ), start=1):
                components.append(RateComponent(
                    "energy", f"Base Energy Block {index} ({tier_label})", round(terms["blocks"][index - 1] / 100.0, 6),
                    "$/kWh", tier_number=index, tier_threshold=threshold, tier_unit="kWh",
                    notes="Published base rate before the separately listed percentage riders."))
            for component in components:
                component.effective_date = terms["effective"]
                component.source_url = book_url
                component.source_detail = f"PDF page {terms['page']}; Rate {code}" + (
                    f"; block 4 matches cross-reference page {xref_page}" if component.tier_number == 4 else "")
            for rider in rate_riders + [shared["j1"], shared["fuel"]]:
                rider = copy.deepcopy(rider)
                rider.notes = (rider.notes or "").replace("base fixed and energy", "base demand and energy")
                components.append(rider)
            records.append(TariffRecord(
                utility_name="Yukon Energy", province="YT", utility_type="electricity",
                tariff_name=f"General Service {title} (Rate {code})", tariff_code=code,
                customer_class="commercial", sub_class=sub_class, rate_structure="demand",
                effective_date=max(component.effective_date for component in components),
                source_url=book_url, source_page=f"PDF pages {terms['page']}-{terms['page'] + 1}; Rate {code}",
                eligibility=f"Rate {code}. Available in {terms['available']} Applicable {terms['applicable']}",
                notes=(f"Minimum monthly bill: the demand charge but not less than ${terms['minimum']:.2f} (a condition, not an "
                       f"extra charge). Base schedule effective {terms['effective']} (Board Order 2011-06); Riders R/J/J1 apply "
                       "to base demand and energy charges and Rider F to all kWh; the residential affordability relief does not "
                       "apply. Unmetered Rider B is not modelled; no bill total is calculated. Joint YEC/ATCO Electric Yukon "
                       "schedule; the serving utility depends on location."),
                components=components,
            ))
        return records

    @staticmethod
    def _page_of(pages: list[DocumentPage], text: str) -> int:
        return next((page.page_number for page in pages if text in page.text), pages[0].page_number)

    @staticmethod
    def _residential_base_values(section: str, percentages: dict[str, float]) -> Optional[list[float]]:
        """Return base customer and block values; R/J and total columns must reconcile to the header percentages."""
        base_values: list[float] = []
        labels = [
            r"Customer", r"First 1000 kWh Energy Block 1", r"1001-2500 kWh Energy Block 2",
            r">2500 kWh Energy Block 3",
        ]
        r_share, j_share = percentages["R"] / 100.0, percentages["J"] / 100.0
        for index, label in enumerate(labels):
            unit = r"" if index == 0 else r"\s*[^\d\w\s/$+-]{1,2}/kWh"
            row = re.search(label + unit + r"([^\n]*)", section)
            if not row or re.search(r"[-()]", row.group(1)) or (index > 0 and "$" in row.group(1)):
                return None
            values = [float(value) for value in re.findall(
                r"\$\s*(\d+(?:\.\d+)?)" if index == 0 else r"\d+(?:\.\d+)?", row.group(1))]
            if len(values) != 4 or any(value <= 0 for value in values):
                return None
            base, rider_r, rider_j, total = values
            if (abs(base * r_share - rider_r) > 0.006 or abs(base * j_share - rider_j) > 0.006
                    or abs(base * (1 + r_share + j_share) - total) > 0.006):
                return None
            base_values.append(base)
        return base_values

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
