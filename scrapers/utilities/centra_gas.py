"""
centra_gas.py — Scraper for Centra Gas Manitoba rates.

Centra Gas Manitoba is a subsidiary of Manitoba Hydro and is the
primary natural gas distributor in Manitoba.

Official sources (the old /accounts-and-billing/rates/natural-gas-rates/ URL is dead):
  https://www.hydro.mb.ca/account/rates/residential/       (residential gas table)
  https://www.hydro.mb.ca/account/rates/commercial/        (commercial gas tables)
  https://www.hydro.mb.ca/account/rates/natural-gas/       (default quarterly commodity rate, marketers)
  https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/fcrates/fuel-charge-rates.html

Manitoba gas rates are regulated by the Public Utilities Board of
Manitoba (PUB Manitoba).  Charges are published in cents per m3 and stored
as $/m3 (a plain /100 conversion; no heat-content conversion is performed).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

HYDRO_BASE_URL = "https://www.hydro.mb.ca/account/rates/"
PAGE_URLS = {
    "residential": HYDRO_BASE_URL + "residential/",
    "commercial": HYDRO_BASE_URL + "commercial/",
    "supply": HYDRO_BASE_URL + "natural-gas/",
    "schedule": "https://www.hydro.mb.ca/docs/billing/schedule-of-sales-and-transportation-services-and-rates-v0826.pdf",
    "carbon": (
        "https://www.canada.ca/en/revenue-agency/services/forms-publications/"
        "publications/fcrates/fuel-charge-rates.html"
    ),
}

SEED_RESIDENTIAL_NAME = "Residential — Small General Service"
MARKETER_SUFFIX = " (Marketer Supply, Delivery Only)"

# Published cents per m3; the cent glyph is matched loosely, a dollar sign never matches.

def _cents(group_name: str) -> str:
    return rf"(?P<{group_name}>\d+\.\d+)[^\d\s/$]{{1,2}}/m3"


@dataclass(frozen=True)
class GasClassSpec:
    """One published Centra table on the commercial page."""
    option_label: str       # label in the 'Commercial rate options' list
    table_heading: str      # heading repeated three times before each table
    tariff_name: str
    tariff_code: str
    sub_class: str
    sales_service: bool     # True: Centra supplies commodity; False: T-service
    has_demand: bool
    has_alternate_supply: bool = False
    marketer_variant: bool = False  # delivery-only copy for customers buying from a marketer


COMMERCIAL_CLASSES = (
    GasClassSpec("Small general service", "Small general service", "Commercial — Small General Service",
                 "COM-SGS", "small general service", True, False, marketer_variant=True),
    GasClassSpec("Large general service", "Large general service", "Commercial — Large General Service",
                 "COM-LGS", "large general service", True, False, marketer_variant=True),
    GasClassSpec("High volume firm service", "High volume firm service (Sales service)",
                 "Commercial — High Volume Firm Service (Sales)", "COM-HVF-S", "high volume firm", True, True),
    GasClassSpec("High volume firm service", "High volume firm service (T-service)",
                 "Commercial — High Volume Firm Service (T-Service)", "COM-HVF-T", "high volume firm", False, True),
    GasClassSpec("Mainline firm service", "Mainline firm service (Sales service)",
                 "Commercial — Mainline Firm Service (Sales)", "COM-MFS-S", "mainline firm", True, True),
    GasClassSpec("Mainline firm service", "Mainline firm service (T-service)",
                 "Commercial — Mainline Firm Service (T-Service)", "COM-MFS-T", "mainline firm", False, True),
    GasClassSpec("Interruptible service", "Interruptible service (Sales service)",
                 "Commercial — Interruptible Service (Sales)", "COM-IS-S", "interruptible", True, True, True),
    GasClassSpec("Interruptible service", "Interruptible service (T-service)",
                 "Commercial — Interruptible Service (T-Service)", "COM-IS-T", "interruptible", False, True, True),
)

MONTHS = {name: number for number, name in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}

# Seed data based on PUB-approved rates (2024; unverified fallback only).
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": PAGE_URLS["residential"],
    "basic_charge_monthly": 14.00,              # $/month
    "primary_gas_rate": 0.1195,                 # $/m³ — primary gas supply
    "supplemental_gas_rate": 0.0320,            # $/m³ — supplemental gas/peaking
    "distribution_rate": 0.0775,                # $/m³ — distribution to customer
    "transportation_rate": 0.0292,              # $/m³ — upstream pipeline transport
    "cost_adjustment_rider": -0.0045,           # $/m³ — periodic adjustment
}


class CentraGasScraper(BaseScraper):
    """Scrape Centra Gas Manitoba natural gas rates."""

    def __init__(self):
        super().__init__(utility_name="Centra Gas Manitoba", province="MB")

    def scrape(self) -> list[TariffRecord]:
        records = list(self._try_live_scrape() or [])

        if not any(record.tariff_name == SEED_RESIDENTIAL_NAME for record in records):
            self.logger.warning("Residential live parse unavailable — using unverified seed for Centra Gas Manitoba")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Fetch each official page independently and parse complete classes."""
        pages: dict[str, str] = {}
        for key, url in PAGE_URLS.items():
            try:
                if key == "schedule":
                    import io
                    import pdfplumber
                    import requests
                    response = requests.get(url, timeout=(10, 45))
                    response.raise_for_status()
                    with pdfplumber.open(io.BytesIO(response.content)) as document:
                        pages[key] = " ".join(
                            "PDF page " + str(number) + " " + re.sub(
                                r"(?m)^\d{1,2} ", "", document.pages[number - 1].extract_text() or "")
                            for number in (14, 17, 18, 19, 34, 44, 51))
                    continue
                html = self.fetch_page(url)
                if "Request Rejected" in html[:600]:
                    html = self.fetch_rendered_page(url) or html
                pages[key] = self._page_text(html)
            except Exception as exc:
                self.logger.warning("Centra Gas %s page unavailable: %s", key, exc)
        records = self.parse_pages(pages)
        if not records:
            return None
        return self.mark_live_parsed(records)

    @staticmethod
    def _page_text(html: str) -> str:
        from scrapers.utils.parsing import parse_html
        soup = parse_html(html)
        node = soup.find("main") or soup
        return node.get_text(" ", strip=True)

    # ── Parsing ──────────────────────────────────────────────

    @staticmethod
    def _norm(text: str) -> str:
        text = text.replace("\xa0", " ")
        text = re.sub(r"\bm\s?[³3]", "m3", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _dollars(cents: str) -> float:
        return round(float(cents) / 100, 6)

    @staticmethod
    def _long_date(value: str) -> Optional[date]:
        try:
            return datetime.strptime(value, "%B %d, %Y").date()
        except ValueError:
            return None

    def _carbon(self, text: str, today: date) -> Optional[tuple[date, str]]:
        """Return (effective date, note) only for an explicit zero fuel charge that names Manitoba."""
        zero = re.search(
            r"Fuel charge rates \S{1,2} Beginning ([A-Z][a-z]+ \d{1,2}, \d{4}) On [A-Z][a-z]+ \d{1,2}, \d{4}, "
            r"the Government of Canada made regulations that cease the application of the federal fuel charge, "
            r"by setting all fuel charge rates to zero", text)
        manitoba_ended = re.search(
            r"The rates applied in Alberta, Manitoba, Ontario, and Saskatchewan from April 1, 2019 to March 31, 2025", text)
        effective = self._long_date(zero.group(1)) if zero else None
        if not effective or not manitoba_ended or effective > today:
            return None
        return effective, (
            f"Canada Revenue Agency fuel charge rates, beginning {zero.group(1)}: all federal fuel charge rates "
            "set to zero; Manitoba is a listed province whose charge ended March 31, 2025. "
            "Centra Gas's own pages publish no carbon row.")

    def _quarterly_rate(self, text: str, today: date) -> Optional[tuple[date, float]]:
        """Latest in-force default quarterly commodity rate ($/m3) from the gas supply page."""
        if not re.search(r"Quarterly rate service \(adjusted four times per year\) This is the default natural gas service option", text):
            return None
        found: list[tuple[date, float]] = []
        for amount, month, day, year in re.findall(
                r"\$\s*(\d\.\d{4}) \(([A-Z][a-z]{2,4})\.? (\d{1,2})[.,] (\d{4})\)", text):
            number = MONTHS.get(month[:3].lower())
            if number:
                found.append((date(int(year), number, int(day)), float(amount)))
        in_force = [row for row in found if row[0] <= today]
        return max(in_force) if in_force else None

    def _commodity_headline(self, text: str, today: date) -> Optional[tuple[date, float]]:
        """Effective date and $/m3 commodity from the headline of a gas section."""
        match = re.search(
            rf"Rates effective ([A-Z][a-z]+ \d{{1,2}}, \d{{4}}) Effective \1, the Gas Commodity rate is {_cents('cents')}", text)
        effective = self._long_date(match.group(1)) if match else None
        if not match or not effective or effective > today:
            return None
        return effective, self._dollars(match.group("cents"))

    def _table_values(self, section: str, spec_sales: bool, has_demand: bool, alternate: bool) -> dict[str, float]:
        """Strictly parse one gas table and its two explanatory sentences; raises ValueError."""
        split = re.search(r"Delivery is the total of:|Delivery only includes", section)
        if not section.startswith("Charge Cost ") or not split:
            raise ValueError("table header or delivery explanation missing")
        rows_text = section[len("Charge Cost "):split.start()].strip()
        note_text = section[split.start():].strip()
        rows = rf"Basic monthly charge \$\s*(?P<basic>\d[\d,]*\.\d{{2}})"
        if spec_sales:
            rows += rf" Gas Commodity {_cents('commodity')}"
        rows += rf" Delivery {_cents('delivery')}"
        if has_demand:
            rows += rf" Demand {_cents('demand')} ?/month"
        if alternate:
            rows += rf" Alternate supply service {_cents('alternate')}"
        row_match = re.fullmatch(rows, rows_text)
        if not row_match:
            raise ValueError("unexpected, missing or wrongly-united charge row")
        notes = (rf"Delivery is the total of: Transportation to Centra charges at {_cents('transport')} plus "
                 rf"Distribution to customer charges at {_cents('distribution')}\s?\."
                 if spec_sales else r"Delivery only includes Distribution to customer charges\.")
        if has_demand:
            notes += (rf" Demand is the total of: Demand transportation charges at {_cents('demand_transport')} ?/month "
                      rf"plus Demand distribution charges at {_cents('demand_distribution')} ?/month\s?\."
                      if spec_sales else r" Demand only includes Demand distribution charges\.")
        note_match = re.fullmatch(notes, note_text)
        if not note_match:
            raise ValueError("delivery/demand composition sentence missing or changed")
        values = {key: float(value.replace(",", "")) for key, value in {**row_match.groupdict(), **note_match.groupdict()}.items()}
        if min(values.values()) <= 0:
            raise ValueError("non-positive charge")
        if spec_sales:
            if abs(values["transport"] + values["distribution"] - values["delivery"]) > 0.005:
                raise ValueError("delivery total does not equal its published components")
            if has_demand and abs(values["demand_transport"] + values["demand_distribution"] - values["demand"]) > 0.005:
                raise ValueError("demand total does not equal its published components")
        return values

    @staticmethod
    def _section(text: str, heading: str, others: list[str], end_marker: str) -> str:
        """Text from one repeated-heading table up to the next table or the end marker."""
        marker = f"{heading} {heading} {heading} "
        start = text.find(marker)
        if start < 0:
            raise ValueError("table heading missing")
        start += len(marker)
        ends = [text.find(f"{other} {other} {other} ", start) for other in others]
        ends += [text.find(end_marker, start)]
        ends = [position for position in ends if position >= 0]
        return text[start:min(ends)].strip() if ends else text[start:].strip()

    def parse_pages(self, pages: dict[str, str], today: Optional[date] = None) -> list[TariffRecord]:
        """Build tariffs from page texts keyed residential/commercial/supply/carbon.

        Missing carbon applicability rejects everything. Otherwise each class
        and each variant is isolated: one malformed table never discards another.
        """
        today = today or datetime.now(timezone.utc).date()
        pages = {key: self._norm(text) for key, text in pages.items()}
        schedule = pages.get("winter", "") + " " + pages.get("schedule", "")
        carbon = self._carbon(pages.get("carbon", ""), today)
        if carbon is None:
            self.logger.warning("Centra Gas: required current carbon applicability could not be verified")
            return []
        supply = pages.get("supply", "")
        quarterly = self._quarterly_rate(supply, today)
        marketer_ok = bool(re.search(
            r"If you sign an agreement with a natural gas marketer for your gas commodity supply, we will continue "
            r"to provide all other components of your natural gas supply and service", supply))
        fixed_terms = bool(re.search(
            r"Fixed rate service for natural gas supply is available during designated enrollment periods "
            r"throughout the year\. It provides you the option to choose a fixed rate for your natural gas "
            r"for a one, three or five-year term through Manitoba Hydro", supply))

        records: list[TariffRecord] = []

        def build(**kwargs) -> None:
            records.append(self._build(carbon=carbon, fixed_terms=fixed_terms, **kwargs))

        def headline_for(page_key: str) -> tuple[date, float]:
            headline = self._commodity_headline(pages.get(page_key, ""), today)
            if headline is None:
                raise ValueError("missing or future 'Rates effective' headline")
            return headline

        def sales_commodity(headline: tuple[date, float], table_commodity: float) -> float:
            if quarterly is None or quarterly != headline:
                raise ValueError("headline commodity rate not confirmed by the quarterly rate table")
            if abs(round(table_commodity / 100, 6) - headline[1]) > 1e-9:
                raise ValueError("table commodity differs from the published headline rate")
            return headline[1]

        # Residential
        try:
            headline = headline_for("residential")
            text = pages["residential"]
            start = text.find("Residential natural gas rates ")
            if start < 0:
                raise ValueError("residential table missing")
            end = text.find("Natural gas is a commodity that is traded", start)
            section = text[start + len("Residential natural gas rates "):end if end > 0 else len(text)].strip()
            values = self._table_values(section, True, False, False)
            values["commodity"] = sales_commodity(headline, values["commodity"])
            condition, usage_min, usage_max, schedule_detail = self._schedule_conditions(
                schedule, "SGS")
            build(name=SEED_RESIDENTIAL_NAME, code="SGS", customer_class="residential", sub_class=None,
                  eligibility=condition, usage_min=usage_min, usage_max=usage_max, values=values, sales=True,
                  effective=headline[0], url=PAGE_URLS["residential"], has_demand=False, alternate=False,
                  schedule_detail=schedule_detail)
            if marketer_ok:
                build(name=SEED_RESIDENTIAL_NAME + MARKETER_SUFFIX, code="SGS-MKT", customer_class="residential",
                      sub_class=None, eligibility=condition, usage_min=usage_min, usage_max=usage_max, values=values,
                      sales=False, effective=headline[0], url=PAGE_URLS["residential"], has_demand=False,
                      alternate=False, marketer=True, schedule_detail=schedule_detail)
        except ValueError as exc:
            self.logger.warning("Centra Gas residential not parsed live: %s", exc)

        # Commercial
        commercial = pages.get("commercial", "")
        headings = [spec.table_heading for spec in COMMERCIAL_CLASSES]
        for spec in COMMERCIAL_CLASSES:
            try:
                headline = headline_for("commercial")
                eligibility, usage_min, usage_max = self._eligibility(commercial, spec.option_label)
                condition, usage_min, usage_max, schedule_detail = self._schedule_conditions(
                    schedule, spec.tariff_code)
                if usage_min is not None:
                    eligibility = re.sub(r"^More than [\d,]+ m³", f"At least {usage_min:,.0f} m³", eligibility)
                else:
                    eligibility = re.sub(r"^Less than [\d,]+ m³", f"Less than {usage_max:,.0f} m³", eligibility)
                eligibility += " " + condition
                section = self._section(
                    commercial, spec.table_heading, [h for h in headings if h != spec.table_heading],
                    "Contact your Energy Service Advisor for information about natural gas rates")
                values = self._table_values(section, spec.sales_service, spec.has_demand, spec.has_alternate_supply)
                if spec.sales_service:
                    values["commodity"] = sales_commodity(headline, values["commodity"])
                common = dict(customer_class="commercial", sub_class=spec.sub_class, eligibility=eligibility,
                              usage_min=usage_min, usage_max=usage_max, values=values,
                              effective=headline[0], url=PAGE_URLS["commercial"], has_demand=spec.has_demand,
                              alternate=spec.has_alternate_supply, schedule_detail=schedule_detail)
                build(name=spec.tariff_name, code=spec.tariff_code, sales=spec.sales_service, **common)
                if spec.marketer_variant and marketer_ok:
                    build(name=spec.tariff_name + MARKETER_SUFFIX, code=spec.tariff_code + "-MKT", sales=False,
                          marketer=True, **common)
            except ValueError as exc:
                self.logger.warning("Centra Gas %s not parsed live: %s", spec.tariff_name, exc)
        return records

    def _eligibility(self, text: str, option_label: str) -> tuple[str, Optional[float], Optional[float]]:
        """Published eligibility sentence and its annual-volume bound for one commercial option."""
        start = text.find("Commercial rate options ")
        first_table = re.search(r"Small general service Small general service Small general service Charge Cost", text)
        if start < 0 or not first_table:
            raise ValueError("commercial rate option list missing")
        segment = text[start + len("Commercial rate options "):first_table.start()]
        labels = list(dict.fromkeys(spec.option_label for spec in COMMERCIAL_CLASSES))
        hits = {}
        for label in labels:
            match = re.search(rf"(?:^| ){re.escape(label)} \S{{1,2}} ", segment)
            if not match:
                if label == option_label:
                    raise ValueError(f"option '{label}' missing")
                continue
            hits[label] = match
        mine = hits[option_label]
        later = [hit.start() for hit in hits.values() if hit.start() > mine.start()]
        eligibility = segment[mine.end():min(later) if later else len(segment)].strip().replace("m3", "m³")
        volume = re.match(r"(Less|More) than ([\d,]+) m³ of natural gas used annually", eligibility)
        if not volume:
            raise ValueError("annual-volume eligibility unrecognised")
        limit = float(volume.group(2).replace(",", ""))
        if limit <= 0:
            raise ValueError("non-positive annual-volume limit")
        return eligibility, (limit if volume.group(1) == "More" else None), (limit if volume.group(1) == "Less" else None)

    def _schedule_conditions(self, text: str, code: str) -> tuple[str, Optional[float], Optional[float], str]:
        pages = {}
        for number in (14, 17, 18, 19, 34, 44, 51):
            match = re.search(rf"PDF page {number} (.*?)(?=PDF page \d+ |$)", text)
            pages[number] = match.group(1) if match else ""
        required = ({17, 18} if code.startswith("COM-LGS") else
                    {17} if "SGS" in code else
                    {18, 34} if "HVF" in code else {19, 34})
        if code.endswith("-T"):
            required.add(44)
        if code.startswith("COM-IS"):
            required.add(51)
        if any(class_code in code for class_code in ("HVF", "MFS", "-IS")):
            required.add(14)
        if not all("November 1, 2025" in pages[number] and "Order 138/25" in pages[number]
                   for number in required):
            raise ValueError("approved Centra schedule context missing")
        if code in ("SGS", "SGS-MKT", "COM-SGS", "COM-SGS-MKT", "COM-LGS", "COM-LGS-MKT"):
            section = pages[17]
            heading = "Small General Class" if "SGS" in code else "Large General Class"
            match = re.search(rf"{heading}.*?annual consumption of less than ([\d,]+) m3", section)
            if not match:
                raise ValueError("SGC/LGC annual eligibility missing")
            limit = float(match.group(1).replace(",", ""))
            if limit <= 0:
                raise ValueError("invalid schedule annual boundary")
            condition = f"PUB schedule page 16: annual consumption less than {limit:,.0f} m³; T-service is not available."
            if code.startswith("COM-"):
                if not re.search(r"each election must remain effective for a minimum of one year", pages[17] + " " + pages[18]):
                    raise ValueError("SGC/LGC election term missing")
                condition += " SGC/LGC class elections last at least one year."
            return condition, None, limit, "PDF page 17 (schedule page 16)"

        number = 18 if "HVF" in code else 19
        section = pages[number]
        class_heading = ("High Volume Firm" if number == 18 else
                 "Mainline Class" if "MFS" in code else "Interruptible Service is available to Customers")
        match = re.search(rf"{class_heading}.*?(?:equals or exceeds|equal or exceed) ([\d,]+)\s*(?:m3|3 m)", section)
        if not match:
            raise ValueError("approved high-volume boundary missing")
        limit = float(match.group(1).replace(",", ""))
        if limit <= 0:
            raise ValueError("invalid schedule annual boundary")
        condition = f"PUB schedule page {number - 1}: annual consumption at least {limit:,.0f} m³ through one meter."
        if "MFS" in code:
            if not re.search(r"pressures in excess of medium pressure.*?minimum of one year", section):
                raise ValueError("Mainline pressure/contract condition missing")
            condition += " Direct transmission or dedicated distribution above medium pressure; one-year contract."
        elif "HVF" in code:
            if not re.search(r"binding agreement.*?minimum term of one year", section):
                raise ValueError("HVF contract condition missing")
            condition += " Firm service with a binding agreement for at least one year."
        else:
            if not re.search(r"minimum of one year, or to Customers that have received Interruptible Service continuously since December 31, 1996", section):
                raise ValueError("interruptible enrollment context missing")
            condition += " Interruptible by notice; one-year contract or continuous service since December 31, 1996."
        demand = pages[34]
        if not re.search(r"Winter Month.*?months of November, December, January, February, and March", pages[14]):
            raise ValueError("winter month definition missing")
        if not re.search(r"Monthly Billing Demand will be the highest daily consumption.*?any Winter Month of the preceding eleven months.*?may be estimated or otherwise specified by the Company", demand):
            raise ValueError("monthly billing demand definition missing")
        if not re.search(r"During the months of November and March.*?without invoking a higher Monthly Billing Demand", demand):
            raise ValueError("winter demand exception missing")
        condition += (" Winter months are November through March. Monthly billing demand: highest daily m³ "
                  "consumed in a winter month or a winter month "
                  "of the preceding eleven months, subject to schedule exceptions; Centra may estimate it without "
                      "12 months of data and may allow November/March use without increasing it.")
        if code.endswith("-T"):
            if not re.search(r"minimum term of one year.*?daily nomination equals or exceeds 200 GJ", pages[44]):
                raise ValueError("T-service agreement/nomination missing")
            condition += " T-service requires a one-year agreement and normally at least 200 GJ/day nomination."
        if code.startswith("COM-IS"):
            if not re.search(r"pass-through cost of acquiring additional gas commodity and transportation to Manitoba.*?Alternate Supply Service Delivery Rate", pages[51]):
                raise ValueError("alternate supply pass-through context missing")
            condition += (" Alternate supply during curtailment has a pass-through commodity/transport price plus "
                          "the published alternate delivery rate; it is not the default commodity price.")
        return condition, limit, None, (f"PDF page {number} (schedule page {number - 1}); "
                        "PDF page 14 (schedule page 13); PDF page 34 (schedule page 33)")

    def _build(
        self, *, name: str, code: str, customer_class: str, sub_class: Optional[str],
        eligibility: Optional[str], usage_min: Optional[float], usage_max: Optional[float],
        values: dict[str, float], sales: bool, effective: date, url: str, has_demand: bool,
        alternate: bool, carbon: tuple[date, str], marketer: bool = False, fixed_terms: bool = False,
        schedule_detail: str = "",
    ) -> TariffRecord:
        eff = effective.isoformat()
        detail = f"Rates effective {effective.strftime('%B')} {effective.day}, {effective.year}"
        dollars = self._dollars
        unit = "$/m³"
        comps = [RateComponent(
            "fixed", "Basic Monthly Charge", values["basic"], "$/month", effective_date=eff, source_url=url,
            source_detail=detail, notes="Published monthly basic charge")]
        if sales:
            comps.append(RateComponent(
                "commodity", "Gas Commodity", values["commodity"], unit, effective_date=eff, source_url=url,
                source_detail=detail + "; confirmed by the quarterly rate table on the gas supply page",
                notes="Manitoba Hydro default quarterly rate service, passed through without mark-up; changes "
                      "quarterly. Fixed-rate contract and marketer prices are separate and not included."))
        composed = "transport" in values
        if composed:
            comps.append(RateComponent(
                "transmission", "Transportation to Centra", dollars(str(values["transport"])), unit,
                effective_date=eff, source_url=url, source_detail=detail,
                notes=f"Published delivery total {values['delivery']:.2f}¢/m³ is this plus the distribution "
                      "charge; the total is not a separate additive component."))
        comps.append(RateComponent(
            "delivery", "Distribution Charge",
            dollars(str(values["distribution"] if composed else values["delivery"])), unit,
            effective_date=eff, source_url=url, source_detail=detail,
            notes="Distribution to customer" + ("" if composed else "; T-service delivery includes distribution only")))
        if has_demand:
            if composed:
                comps.append(RateComponent(
                    "demand", "Demand Transportation Charge", dollars(str(values["demand_transport"])),
                    "$/m³/month", effective_date=eff, source_url=url,
                    source_detail=detail + "; demand definition: " + PAGE_URLS["schedule"] + " " + schedule_detail,
                    sub_component="transportation",
                    notes=f"Published demand total {values['demand']:.2f}¢/m³/month is this plus the demand "
                          "distribution charge; not additive."))
            comps.append(RateComponent(
                "demand", "Demand Distribution Charge",
                dollars(str(values["demand_distribution"] if composed else values["demand"])),
                "$/m³/month", effective_date=eff, source_url=url,
                source_detail=detail + "; demand definition: " + PAGE_URLS["schedule"] + " " + schedule_detail,
                sub_component="distribution",
                notes="Published native unit is cents per m³ per month"))
        if alternate:
            comps.append(RateComponent(
                "other", "Alternate Supply Service", dollars(str(values["alternate"])), unit,
                effective_date=eff, source_url=url, source_detail=detail,
                    notes="Conditional delivery charge during interruptible curtailment; acquired gas and transport "
                        "are pass-through costs, not the default commodity rate (approved schedule page 50)."))
        carbon_date, carbon_note = carbon
        comps.append(RateComponent(
            "carbon", "Federal Carbon Charge", 0.0, unit, effective_date=carbon_date.isoformat(),
            source_url=PAGE_URLS["carbon"], source_detail="CRA fuel charge rates", notes=carbon_note))
        if marketer:
            supply_note = ("Customer buys gas commodity from an independent marketer: the marketer's contract price is "
                           "negotiated, unpublished and not included; Centra supplies and bills all other components.")
        elif sales:
            supply_note = "Centra Gas supplies the gas commodity under the default quarterly rate service."
            if fixed_terms:
                supply_note += (" A separate fixed-rate commodity contract is offered during designated enrollment "
                                "periods for one, three or five years; it does not fix delivery or the total bill "
                                f"(Manitoba Hydro gas supply: {PAGE_URLS['supply']}).")
        else:
            supply_note = "T-service: no Gas Commodity row is published; commodity is not included."
        return TariffRecord(
            utility_name="Centra Gas Manitoba", province="MB", utility_type="gas", tariff_name=name,
            tariff_code=code, customer_class=customer_class, sub_class=sub_class, eligibility=eligibility,
            usage_min=usage_min, usage_max=usage_max, usage_unit="m³/year" if (usage_min or usage_max) else None,
            rate_structure="demand" if has_demand else "flat", pricing_method="regulated",
            effective_date=max(effective, carbon_date).isoformat(), source_url=url, source_page=detail,
            confidence="high",
                 notes=(supply_note + f" Approved schedule {schedule_detail} (November 1, 2025, PUB Order 138/25): "
                     f"{PAGE_URLS['schedule']}. Published in cents per m³ and stored as $/m³. Regulated by the Public Utilities "
                   "Board of Manitoba. Taxes are not published on these pages and are not included."),
            components=comps,
        )

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Centra Gas Manitoba",
            province="MB",
            utility_type="gas",
            tariff_name="Residential — Small General Service",
            tariff_code="SGS",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "Centra Gas Manitoba residential rate (Small General Service). "
                "Centra Gas is a subsidiary of Manitoba Hydro. "
                "Primary gas rate is the main commodity cost; supplemental gas "
                "covers peaking supply. Rates in $/m3. "
                "Regulated by PUB Manitoba."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly customer charge",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Primary Gas Rate",
                    charge_value=SEED_RESIDENTIAL["primary_gas_rate"],
                    charge_unit="$/m³",
                    confidence="medium",
                    notes="Primary gas supply cost — largest commodity component",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Supplemental Gas Rate",
                    charge_value=SEED_RESIDENTIAL["supplemental_gas_rate"],
                    charge_unit="$/m³",
                    confidence="medium",
                    sub_component="supplemental",
                    notes="Supplemental gas for peaking supply and storage",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Distribution Charge",
                    charge_value=SEED_RESIDENTIAL["distribution_rate"],
                    charge_unit="$/m³",
                    confidence="medium",
                    notes="Centra Gas distribution charge for delivering gas to customer",
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Transportation to Centra",
                    charge_value=SEED_RESIDENTIAL["transportation_rate"],
                    charge_unit="$/m³",
                    confidence="medium",
                    notes="Upstream pipeline transportation to Centra Gas system",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Cost Adjustment Rider",
                    charge_value=SEED_RESIDENTIAL["cost_adjustment_rider"],
                    charge_unit="$/m³",
                    confidence="medium",
                    notes="Periodic gas cost adjustment — can be positive or negative",
                ),
            ],
        ))

        return records
