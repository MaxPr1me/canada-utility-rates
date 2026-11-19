"""
red_deer.py — Scraper for the City of Red Deer Electric Light & Power (Alberta).

Red Deer owns its distribution system and sets the Regulated Rate Tariff (the Rate of Last Resort in its area,
provided by ENMAX Energy under contract with the City), so one scraper emits both: distribution tariff (wires)
records per rate class and the City's Rate of Last Resort records. The representative models pair them as one unit
(owner decision 2026-11-04: municipal wires with the city-published default energy rate).

Official sources (Electric Utility Bylaw 3273/2000):
- Schedule A, Distribution Tariff (Appendix_A.pdf): System Access (transmission) and Distribution Access charges
  per rate class, the Balancing Pool Allocation and the Local Access Fee. Every value must equal the City's
  "Delivery Rates and Charges" page, whose date label may lag the schedule; that page also publishes the quarterly
  Transmission Rider, stored for the current quarter.
- Schedule D, Regulated Rate Tariff (Appendix_D.pdf): the daily Administration Charge per class. The City's Rate of
  Last Resort page still shows $0.2498/day from January 2026, so Schedule D's $0.3035/day (effective March 1,
  2026) is stored with a note (owner decision 2026-11-19).
- The Rate of Last Resort page: the energy price for the current term (12.06 cents/kWh, January 1, 2025 to
  December 31, 2026). The page prints it under "Residential" and "-" under "Commercial", but says one Rate of
  Last Resort replaced the two RRO rates, and Schedule D gives every class the same energy charge, so it applies
  to rates 61, 63, 64 and 78 alike (owner decision 2026-11-19). After the term the records fail closed.

The Local Access Fee (15% of the System and Distribution Access charges) stays a note, as for Alberta's other
municipal access fees. Scope: rates 61, 63, 64 and 78. Excluded: street and traffic lights (81, 82) and
distribution generation (83). No seed fallback: a failed source returns no records. The schedules keep fixed
addresses; pages are fetched over plain HTTP, with headless Chromium only when the expected content is missing.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

UTILITY = "City of Red Deer Electric Light & Power"
BASE = "https://www.reddeer.ca"
SCHEDULE_A_URL = f"{BASE}/media/reddeerca/city-services/electric-light-and-power/Appendix_A.pdf"
SCHEDULE_D_URL = f"{BASE}/media/reddeerca/city-services/electric-light-and-power/Appendix_D.pdf"
DELIVERY_PAGE_URL = (f"{BASE}/city-services/electric-light-and-power/understanding-your-electricity-bill-and-meter/"
                     "delivery-rates-and-charges/")
ROLR_PAGE_URL = f"{BASE}/city-services/electric-light-and-power/getting-electricity/rate-of-last-resort/"

# rate class: (name, customer class)
CLASSES = {"61": ("Residential", "residential"), "63": ("General Service", "commercial"),
           "64": ("General Service (50 kVA or greater)", "commercial"),
           "78": ("Large General Service/Industrial", "commercial")}
QUARTERS = {1: ("01-01", "03-31"), 2: ("04-01", "06-30"), 3: ("07-01", "09-30"), 4: ("10-01", "12-31")}

_LONG_DATE = r"[A-Z][a-z]+ \d{1,2}, \d{4}"
_NUMBER = r"(-?\d+\.\d+)"


def _iso(text: str) -> str:
    return datetime.strptime(text, "%B %d, %Y").date().isoformat()


def _flat(value) -> str:
    text = value.get_text(" ", strip=True) if hasattr(value, "get_text") else value
    return " ".join(text.split())


def _sections(pages: list[DocumentPage], heading: str) -> dict[str, dict]:
    """{rate class: {page, text}} for pages whose heading matches ``heading`` (one class per page)."""
    found: dict[str, dict] = {}
    for page in pages:
        head = re.search(heading, page.text)
        if head:
            if head.group(1) in found:
                raise ValueError(f"rate {head.group(1)} printed twice")
            found[head.group(1)] = {"page": page.page_number, "text": _flat(page.text[head.end():])}
    return found


def parse_schedule_a(pages: list[DocumentPage]) -> dict:
    """Effective date and, per class, the System/Distribution Access charges, Balancing Pool and Local Access Fee."""
    effective = re.search(r"This Tariff is effective on (" + _LONG_DATE + ")", _flat(pages[0].text) if pages else "")
    if not effective:
        raise ValueError("Schedule A effective date not found")
    classes: dict[str, dict] = {}
    for code, section in _sections(pages, r"- RATE (\d{2})\b").items():
        text = section["text"]
        basic = re.search(r"Basic Charge \$ per day " + _NUMBER + " " + _NUMBER, text)
        demand = re.search(r"Demand Charge \$/kVA of Billing Demand " + _NUMBER + " " + _NUMBER + r" per day", text)
        variable = re.search(r"Variable Charge \$/kWh of all energy " + _NUMBER + " " + _NUMBER, text)
        pool = re.search(r"Balancing A charge of \$" + _NUMBER + r"/kWh of all energy effective from (" + _LONG_DATE
                         + ")", text)
        access = re.search(r"Assessed as (\d+\.\d+)% of each and every component", text)
        application = re.search(r"^Application (.+?) Distribution Unit", text)
        classes[code] = {"page": section["page"], "basic": basic and (float(basic.group(1)), float(basic.group(2))),
                         "demand": demand and (float(demand.group(1)), float(demand.group(2))),
                         "variable": variable and (float(variable.group(1)), float(variable.group(2))),
                         "pool": pool and (float(pool.group(1)), _iso(pool.group(2))),
                         "access_fee": access and float(access.group(1)),
                         "application": application.group(1) if application else None}
    return {"effective": _iso(effective.group(1)), "classes": classes}


def parse_schedule_d(pages: list[DocumentPage]) -> dict:
    """Effective date and the Administration Charge and application text per Regulated Rate Tariff class."""
    effective = re.search(r"This Tariff is effective on (" + _LONG_DATE + ")", _flat(pages[0].text) if pages else "")
    if not effective:
        raise ValueError("Schedule D effective date not found")
    classes: dict[str, dict] = {}
    for code, section in _sections(pages, r"REGULATED RATE RATE (\d{2})").items():
        admin = re.search(r"Administration Charge: \$(\d+\.\d+) per day", section["text"])
        energy = "Energy Charge as per Regulated Rate Tariff Energy Price Setting Plan" in section["text"]
        application = re.search(r"Application:? \d* ?(.+?) \d+ (?:Rate|Services are)", section["text"])
        classes[code] = {"page": section["page"], "admin": float(admin.group(1)) if admin and energy else None,
                         "application": application.group(1) if application else None}
    return {"effective": _iso(effective.group(1)), "classes": classes}


def parse_delivery_page(html: str) -> dict:
    """The delivery page's charges by rate class, Local Access Fee, Balancing Pool and quarterly Transmission Rider."""
    tables = [[[_flat(cell) for cell in row.find_all(["td", "th"])] for row in table.find_all("tr")]
              for table in parse_html(html or "").find_all("table")]
    table = next((t for t in tables if t and t[0][:1] == ["Rate Class"]), None)
    if table is None:
        raise ValueError("delivery rates table not found")
    codes = table[0][1:]
    values: dict[tuple[str, str, str], float] = {}
    riders: dict[int, list[float]] = {}
    block = None
    pool = access = None
    for row in table[1:]:
        label = row[0] if row else ""
        if label in ("System Access (SA)", "Distribution Access (DA)"):
            block = label[-3:-1]
            continue
        if label.startswith(("Basic Charge", "Variable Charge")) and block:
            for code, cell in zip(codes, row[1:]):
                if cell:
                    values[(block, label, code)] = float(cell)
        elif label.startswith("Local Access Fee") and row[-1].endswith("%"):
            access = float(row[-1][:-1])
        elif label.startswith("Balancing Pool Allocation"):
            pool = float(row[-1])
        elif label.startswith("Transmission Rider") or re.fullmatch(r"20\d\d", label):
            year_cell = row[1] if label.startswith("Transmission Rider") else label
            quarters = row[-2].split()
            amounts = [float(value) for value in row[-1].split()]
            if re.fullmatch(r"20\d\d", year_cell) and quarters == ["Q1", "Q2", "Q3", "Q4"] and len(amounts) == 4:
                riders[int(year_cell)] = amounts
    return {"values": values, "access_fee": access, "pool": pool, "riders": riders}


def parse_rolr_page(html: str, today: date) -> Optional[dict]:
    """The current term's Rate of Last Resort energy price and the page's administration charge, or None."""
    soup = parse_html(html or "")
    text = _flat(soup)
    term = re.search(r"effective (January 1, \d{4}) - (December 31, \d{4})", text)
    if not term or not _iso(term.group(1)) <= today.isoformat() <= _iso(term.group(2)):
        return None
    for table in soup.find_all("table"):
        rows = [[_flat(cell) for cell in row.find_all(["td", "th"])] for row in table.find_all("tr")]
        if not rows or rows[0][:2] != ["Month", "Energy Price ($/kWh) Residential"]:
            continue
        dated = []
        for row in rows[1:]:
            try:
                when = datetime.strptime(row[0], "%B %Y").date()
            except (ValueError, IndexError):
                continue
            price = re.fullmatch(r"\*?(\d+\.\d+)", row[1]) if len(row) > 3 else None
            if price and when <= today:
                dated.append((when, float(price.group(1)), row[3]))
        if dated:
            when, price, admin = max(dated)
            return {"price": price, "row": when.strftime("%B %Y"), "start": when.isoformat(),
                    "end": _iso(term.group(2)), "page_admin": admin}
    return None


def _quarter(today: date) -> tuple[int, str, str]:
    quarter = (today.month - 1) // 3 + 1
    start, end = QUARTERS[quarter]
    return quarter, f"{today.year}-{start}", f"{today.year}-{end}"


def build_records(schedule_a: dict, schedule_d: dict, delivery: dict, rolr: Optional[dict], today: date,
                  ) -> tuple[list[TariffRecord], dict[str, str]]:
    """Wires and Rate of Last Resort records; (records, {code: rejection reason})."""
    for label, when in (("Schedule A", schedule_a["effective"]), ("Schedule D", schedule_d["effective"])):
        if when > today.isoformat():
            raise ValueError(f"{label} takes effect {when}, after {today.isoformat()}")
    records: list[TariffRecord] = []
    rejections: dict[str, str] = {}
    quarter, q_start, q_end = _quarter(today)
    rider = (delivery["riders"].get(today.year) or [None] * 4)[quarter - 1]
    for code, (name, customer_class) in CLASSES.items():
        section = schedule_a["classes"].get(code)
        if section is None:
            rejections[code] = "rate class not found in Schedule A"
            continue
        pairs = [("SA", "Basic Charge ($/day)", "basic"), ("DA", "Basic Charge ($/day)", "basic"),
                 ("SA", "Basic Charge ($/kVA/day)", "demand"), ("DA", "Basic Charge ($/kVA/day)", "demand"),
                 ("SA", "Variable Charge ($/kWh)", "variable"), ("DA", "Variable Charge ($/kWh)", "variable")]
        problems = []
        for block, label, key in pairs:
            printed = section[key][0 if block == "SA" else 1] if section[key] else None
            listed = delivery["values"].get((block, label, code))
            if printed != listed:
                problems.append(f"{block} {label}: Schedule A {printed} vs delivery page {listed}")
        if not section["variable"] or not (section["basic"] or section["demand"]):
            problems.append("Schedule A charges not found")
        if section["pool"] is None or section["pool"][0] != delivery["pool"]:
            problems.append("Balancing Pool Allocation missing or differs from the delivery page")
        if section["access_fee"] is None or section["access_fee"] != delivery["access_fee"]:
            problems.append("Local Access Fee missing or differs from the delivery page")
        if rider is None:
            problems.append(f"no {today.year} Q{quarter} Transmission Rider on the delivery page")
        if problems:
            rejections[code] = "; ".join(problems)
            continue
        detail = f"Electric Utility Bylaw 3273/2000 Schedule A, Rate {code}, PDF page {section['page']}"
        effective = schedule_a["effective"]
        components: list[RateComponent] = []
        if section["basic"]:
            components += [
                RateComponent(component_type="transmission", component_name="System Access Basic Charge",
                              charge_value=section["basic"][0], charge_unit="$/day"),
                RateComponent(component_type="fixed", component_name="Distribution Access Basic Charge",
                              charge_value=section["basic"][1], charge_unit="$/day")]
        if section["demand"]:
            ratchet = ("Per kVA of billing demand: the greater of the highest metered kVA in the monthly billing "
                       "period and in the 12 months ending with it (Schedule A).")
            components += [
                RateComponent(component_type="transmission", component_name="System Access Demand Charge",
                              charge_value=section["demand"][0], charge_unit="$/kVA/day", demand_unit="kVA",
                              notes=ratchet),
                RateComponent(component_type="demand", component_name="Distribution Access Demand Charge",
                              charge_value=section["demand"][1], charge_unit="$/kVA/day", demand_unit="kVA",
                              notes=ratchet)]
        components += [
            RateComponent(component_type="transmission", component_name="System Access Variable Charge",
                          charge_value=section["variable"][0], charge_unit="$/kWh"),
            RateComponent(component_type="distribution", component_name="Distribution Access Variable Charge",
                          charge_value=section["variable"][1], charge_unit="$/kWh")]
        for component in components:
            component.effective_date, component.source_url = effective, SCHEDULE_A_URL
            component.source_detail = detail + "; matches the Delivery Rates and Charges page"
        components.append(RateComponent(
            component_type="rider", component_name="Balancing Pool Allocation", charge_value=section["pool"][0],
            charge_unit="$/kWh", effective_date=section["pool"][1], source_url=SCHEDULE_A_URL, source_detail=detail))
        components.append(RateComponent(
            component_type="rebate" if rider < 0 else "rider", component_name=f"Transmission Rider ({today.year} Q{quarter})",
            charge_value=rider, charge_unit="$/kWh", effective_date=q_start, end_date=q_end,
            source_url=DELIVERY_PAGE_URL, source_detail="Delivery Rates and Charges page, Fees and Riders",
            notes="Quarterly charge or credit for AESO transmission cost variances (Schedule A, Transmission Rate "
                  "Rider)."))
        notes = (f"City of Red Deer Distribution Tariff (Electric Utility Bylaw 3273/2000 Schedule A, effective "
                 f"{effective}), Rate {code}. Wires charges only: System Access (transmission) and Distribution "
                 f"Access; energy is billed separately. Local Access Fee: {section['access_fee']:.2f}% of each System "
                 "and Distribution Access component (not included as a charge). The minimum monthly charge is the "
                 "total basic or demand charge plus any Local Access Fee (a floor, not an additional charge).")
        records.append(TariffRecord(
            utility_name=UTILITY, province="AB", utility_type="electricity", tariff_name=f"{name} (Rate {code})",
            tariff_code=code, customer_class=customer_class, sub_class=name.lower(),
            eligibility=section["application"], rate_structure="demand" if section["demand"] else "flat",
            pricing_method="municipal", effective_date=max(c.effective_date for c in components),
            source_url=SCHEDULE_A_URL, source_page=detail, confidence="high", notes=notes, components=components))
    for code, (name, customer_class) in CLASSES.items():
        section = schedule_d["classes"].get(code)
        key = f"RRT-{code}"
        if rolr is None:
            rejections[key] = "no Rate of Last Resort energy price in effect on the City's page"
            continue
        if section is None or section["admin"] is None:
            rejections[key] = "Schedule D class, Administration Charge or energy reference not found"
            continue
        detail = f"Electric Utility Bylaw 3273/2000 Schedule D, Rate {code}, PDF page {section['page']}"
        admin_note = "Administration Charge from Schedule D"
        if rolr["page_admin"] != f"{section['admin']:.4f}":
            admin_note += (f"; the City's Rate of Last Resort page still shows ${rolr['page_admin']}/day from "
                           f"{rolr['row']} (owner decision 2026-11-19: Schedule D is stored).")
        energy_note = "Rate of Last Resort energy price for the current term (the City's page)."
        if customer_class != "residential":
            energy_note += (" The page prints it under Residential and '-' under Commercial; it says one Rate of Last "
                            "Resort replaced the two RRO rates, and Schedule D gives this class the same energy charge "
                            "(owner decision 2026-11-19).")
        components = [
            RateComponent(component_type="energy", component_name="RoLR Energy Charge", charge_value=rolr["price"],
                          charge_unit="$/kWh", effective_date=rolr["start"], end_date=rolr["end"],
                          source_url=ROLR_PAGE_URL, source_detail=f"Rate of Last Resort page, {rolr['row']} row",
                          notes=energy_note),
            RateComponent(component_type="fixed", component_name="RoLR Administration Charge",
                          charge_value=section["admin"], charge_unit="$/day", effective_date=schedule_d["effective"],
                          source_url=SCHEDULE_D_URL, source_detail=detail, notes=admin_note + ".")]
        records.append(TariffRecord(
            utility_name=UTILITY, province="AB", utility_type="electricity",
            tariff_name=f"Rate of Last Resort — {name} (Rate {code})", tariff_code=key,
            customer_class=customer_class, sub_class=f"regulated rate tariff {name.lower()}",
            eligibility=section["application"], rate_structure="flat", pricing_method="regulated",
            effective_date=max(c.effective_date for c in components), end_date=rolr["end"], source_url=SCHEDULE_D_URL,
            source_page=detail, confidence="high",
            notes=("City of Red Deer Regulated Rate Tariff (Rate of Last Resort, Schedule D), provided by ENMAX Energy "
                   "under contract with the City, for sites using less than 250,000 kWh a year (residential: up to "
                   "two dwelling units). Wires charges are billed separately under the Distribution Tariff."),
            components=components))
    return records, rejections


class RedDeerScraper(BaseScraper):
    """Parse the City of Red Deer's distribution tariff and Regulated Rate Tariff."""

    def __init__(self) -> None:
        super().__init__(utility_name=UTILITY, province="AB")

    def scrape(self) -> list[TariffRecord]:
        # No seed fallback for batch 18 utilities (owner confirmed 2026-11-17).
        records = self._try_live_scrape()
        if not records:
            self.logger.warning("Red Deer: no live records (no seed fallback)")
        return records

    def _html(self, url: str, marker: str) -> str:
        """The page over plain HTTP, or rendered by headless Chromium when the expected content is missing."""
        try:
            html = self.fetch_page(url)
            if marker in html:
                return html
        except Exception as exc:
            self.logger.warning("Red Deer page %s unavailable over HTTP: %s", url, exc)
        return self.fetch_rendered_page(url) or ""

    def _try_live_scrape(self) -> list[TariffRecord]:
        today = date.today()
        try:
            delivery = parse_delivery_page(self._html(DELIVERY_PAGE_URL, "Rate Class"))
            rolr = parse_rolr_page(self._html(ROLR_PAGE_URL, "Energy Price"), today)
            schedule_a = parse_schedule_a(extract_pdf_pages(self.fetch_bytes(SCHEDULE_A_URL),
                                                            drop_repeated_lines=False))
            schedule_d = parse_schedule_d(extract_pdf_pages(self.fetch_bytes(SCHEDULE_D_URL),
                                                            drop_repeated_lines=False))
            records, rejections = build_records(schedule_a, schedule_d, delivery, rolr, today)
        except Exception as exc:
            self.logger.warning("Red Deer tariff failed closed: %s", exc)
            return []
        for code, reason in rejections.items():
            self.logger.warning("Red Deer %s rejected: %s", code, reason)
        return self.mark_live_parsed(records)
