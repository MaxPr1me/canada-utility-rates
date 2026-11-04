"""
new_westminster.py — Scraper for the City of New Westminster Electrical Utility (British Columbia).

Official source: Schedule "A" (Schedule of Rates) of the consolidated Electrical Utility Bylaw No. 6502,
1998, linked as "Bylaw No. 6502, 1998" from the City's bylaw index
(https://www.newwestcity.ca/city_hall/bylaws/main/131/site_bylaws.php?sw=e). The schedule prints one
date ("SCHEDULE OF RATES – Effective January 1, 2026"). Council sets the rates; the BCUC does not
regulate them. Residential and small general service are billed per two-month period, large general
service per month (the electrical utility page: "Residential accounts: Billed every two months").

Every class adds "a rate rider equal to 2.5% of the billed amount" and "a climate action levy equal to
3.5% of the billed amount". Both are stored as percentage riders; the representative models disclose
but do not apply percentage riders (engine rule kept, batch 18 provisional decision 2026-11-04).

Scope: residential 101, 102 (strata common areas) and 103 (multiple occupancy, per dwelling unit),
multi-residential 131 (with the 133 transformer-ownership discount) and 134 (100% rental buildings, with
the 135 discount), general service under 35 kW 201 and 202 (common areas), and general service 35 kW
and over 210, 211 and 212, whose 220/230/240 variants are 210 with the conditional primary-metering
(1.5%) and customer-transformation ($0.25/kW) discounts. Excluded: temporary service 203/213, the
Rate 241 MURB thermal pilot, lighting (302 onward), net metering (Rate 500) and standard charges.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import urljoin

from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

UTILITY = "City of New Westminster"
BYLAW_INDEX_URL = "https://www.newwestcity.ca/city_hall/bylaws/main/131/site_bylaws.php?sw=e"
LAST_KNOWN_BYLAW_URL = ("https://www.newwestcity.ca/database/files/library/"
                        "Consolidated_Bylaw_6502__1998_Electrical_Utility__2025_12_15_consolidation_.pdf")
_NUM = r"\$?\s?(\d*\.\d+|\d+)"


def _iso(text: str) -> str:
    return datetime.strptime(text, "%B %d, %Y").date().isoformat()


def find_bylaw_url(html: str, base_url: str = BYLAW_INDEX_URL) -> Optional[str]:
    """The consolidated Electrical Utility Bylaw No. 6502 link on the bylaw index page."""
    for anchor in parse_html(html or "").find_all("a", href=True):
        label = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))
        if re.fullmatch(r"Bylaw No\. 6502, 1998", label) and anchor["href"].lower().endswith(".pdf"):
            return urljoin(base_url, anchor["href"])
    return None


def _body(text: str, start: str, ends: list[str]) -> str:
    match = re.search(start, text)
    if not match:
        raise ValueError(f"{start!r} not found in Schedule A")
    stops = [m.start() for end in ends for m in [re.search(end, text[match.end():])] if m]
    return text[match.start():match.end() + min(stops)] if stops else text[match.start():]


def _one(pattern: str, body: str, what: str) -> float:
    match = re.search(pattern, body, re.S)
    if not match:
        raise ValueError(f"{what} not found")
    return float(match.group(1))


def _riders(body: str, what: str) -> tuple[float, float]:
    rider = _one(r"A rate rider equal to (\d+(?:\.\d+)?)% of the billed amount shall apply", body, f"{what} rate rider")
    levy = _one(r"A climate action levy equal to (\d+(?:\.\d+)?)% of the billed amount shall apply", body,
                f"{what} climate action levy")
    return rider, levy


def parse_schedule(pages: list[DocumentPage], source_url: str, today: Optional[date] = None,
                   discovery_note: str = "") -> list[TariffRecord]:
    """Build the in-scope Schedule A classes; raise ValueError (fail closed) on a missing date, class, price or
    rider, or a schedule not yet in effect."""
    today = today or date.today()
    full = re.sub(r"\s+", " ", "\n".join(page.text for page in pages))
    dated = re.search(r"SCHEDULE OF RATES . Effective ([A-Z][a-z]+ \d{1,2}, \d{4})", full)
    if not dated:
        raise ValueError("Schedule A effective date not found")
    effective = _iso(dated.group(1))
    if date.fromisoformat(effective) > today:
        raise ValueError(f"Schedule A takes effect {effective}, after {today.isoformat()}")
    schedule = full[dated.start():]
    end = re.search(r"RATE 302\b", schedule)
    schedule = schedule[:end.start()] if end else schedule
    page_numbers, inside = [], False
    for page in pages:
        inside = inside or "SCHEDULE OF RATES" in page.text
        if inside:
            page_numbers.append(page.page_number)
            if re.search(r"RATE 302\b", page.text):
                break
    detail = (f"Electrical Utility Bylaw No. 6502 (consolidated), Schedule A Schedule of Rates effective {effective}, "
              f"PDF pages {page_numbers[0]}-{page_numbers[-1]}")

    def comp(**fields) -> RateComponent:
        return RateComponent(effective_date=effective, source_url=source_url, source_detail=detail,
                             confidence="high", **fields)

    def rider_components(body: str, what: str) -> list[RateComponent]:
        rider, levy = _riders(body, what)
        return [comp(component_type="rider", component_name="Rate Rider", charge_value=rider, charge_unit="%",
                     notes=f"{rider:g}% of the billed amount."),
                comp(component_type="rider", component_name="Climate Action Levy", charge_value=levy, charge_unit="%",
                     notes=f"{levy:g}% of the billed amount.")]

    records: list[TariffRecord] = []

    def add(code: str, name: str, customer_class: str, sub_class: str, structure: str,
            components: list[RateComponent], extra: str = "") -> None:
        notes = f"City of New Westminster Rate {code}. Council-set rates. {extra}".strip()
        if discovery_note:
            notes += " " + discovery_note
        records.append(TariffRecord(
            utility_name=UTILITY, province="BC", utility_type="electricity", tariff_name=name, tariff_code=code,
            customer_class=customer_class, sub_class=sub_class, rate_structure=structure, pricing_method="municipal",
            effective_date=effective, source_url=source_url, source_page=detail, confidence="high", notes=notes,
            components=components))

    residential = _body(schedule, r"RATES 101, 102 and 103", [r"RATES 131 and 133"])
    for code, name, sub_class, basic_label in (
            ("101", "Residential Service, Single Family Dwelling", "single family dwelling", r"Basic Charge per period"),
            ("102", "Residential Service – Common Use Areas", "common use areas of strata corporations and owner "
             "occupied multiple residential premises", r"Basic Charge per period"),
            ("103", "Residential Service, Multiple Occupancy in Single Family Dwelling",
             "multiple occupancy in a single family dwelling (per dwelling unit)",
             r"Basic Charge per single family dwelling unit per period")):
        body = _body(residential, rf"Rate {code}\b", [rf"Rate {int(code) + 1}\b", r"Special Condition"])
        if not re.search(r"for a period of two months", body):
            raise ValueError(f"Rate {code} billing period not printed")
        basic = _one(basic_label + r" " + _NUM, body, f"Rate {code} basic charge")
        energy = _one(r"All kW\.h per (?:single family dwelling unit per )?period " + _NUM + r" per kW\.h", body,
                      f"Rate {code} energy charge")
        per_unit = " per dwelling unit" if code == "103" else ""
        add(code, name, "residential", sub_class, "flat", [
            comp(component_type="fixed", component_name="Basic Charge", charge_value=basic, charge_unit="$/two months",
                 notes=f"Per two-month billing period{per_unit}; also the minimum charge."),
            comp(component_type="energy", component_name="Energy Charge", charge_value=energy, charge_unit="$/kWh",
                 notes=f"All kWh per two-month period{per_unit}."),
            *rider_components(body, f"Rate {code}")])

    multi = _body(schedule, r"RATES 131 and 133", [r"RATES 134 and 135"])
    first = re.search(r"First (\d+) kW\.h per single family dwelling per period " + _NUM + r" per kW\.h\s*Next (\d+) kW\.h"
                      r" per single family dwelling per period " + _NUM + r" per kW\.h\s*All additional kW\.h per period "
                      + _NUM + r" per kW\.h", multi)
    if not first:
        raise ValueError("Rate 131 energy blocks not found")
    one, two = float(first.group(1)), float(first.group(1)) + float(first.group(3))
    unit = "kWh per dwelling per two months"
    add("131", "All Purpose Multi-Residential Service", "residential", "multi-residential, one meter", "tiered", [
        comp(component_type="fixed", component_name="Basic Charge",
             charge_value=_one(r"Basic Charge per single family dwelling per period " + _NUM, multi, "Rate 131 basic"),
             charge_unit="$/two months", notes="Per single family dwelling per two-month period (vacancies count)."),
        comp(component_type="energy", component_name=f"Energy Charge — First {one:g} kWh per dwelling",
             charge_value=float(first.group(2)), charge_unit="$/kWh", tier_number=1, tier_threshold=one, tier_unit=unit),
        comp(component_type="energy", component_name=f"Energy Charge — Next {two - one:g} kWh per dwelling",
             charge_value=float(first.group(4)), charge_unit="$/kWh", tier_number=2, tier_threshold=two, tier_unit=unit),
        comp(component_type="energy", component_name="Energy Charge — Additional kWh",
             charge_value=float(first.group(5)), charge_unit="$/kWh", tier_number=3, tier_threshold=two, tier_unit=unit),
        comp(component_type="rebate", component_name="Rate 133 Transformer Ownership Discount",
             charge_value=-_one(r"discount of \$(\.\d+|\d+\.\d+) per kW of maximum demand", multi, "Rate 133 discount"),
             charge_unit="$/kW/month", demand_unit="kW", sub_component="conditional_credit",
             notes="Conditional: per kW of maximum demand when the customer supplies the transformation (Rate 133)."),
        *rider_components(multi, "Rate 131")], "Rate 133 is Rate 131 with the transformer-ownership discount.")

    rental = _body(schedule, r"RATES 134 and 135", [r"RATES 201, 202, and 203"])
    add("134", "All Purpose Multi-Residential Service (100% Rental Buildings)", "residential",
        "multi-residential rental building, one meter with unit sub-metering", "flat", [
            comp(component_type="fixed", component_name="Basic Charge",
                 charge_value=_one(r"Basic Charge per period/per meter " + _NUM, rental, "Rate 134 basic"),
                 charge_unit="$/two months", notes="Per two-month period per meter."),
            comp(component_type="energy", component_name="Energy Charge",
                 charge_value=_one(r"All kWH per period " + _NUM + r" per kW\.h", rental, "Rate 134 energy"),
                 charge_unit="$/kWh"),
            comp(component_type="rebate", component_name="Rate 135 Transformer Ownership Discount",
                 charge_value=-_one(r"discount of \$(\.\d+|\d+\.\d+) per kW of maximum demand", rental, "Rate 135 discount"),
                 charge_unit="$/kW/month", demand_unit="kW", sub_component="conditional_credit",
                 notes="Conditional: per kW of maximum demand when the customer supplies the transformation (Rate 135)."),
            *rider_components(rental, "Rate 134")], "Rate 135 is Rate 134 with the transformer-ownership discount.")

    small = _body(schedule, r"RATES 201, 202, and 203", [r"RATES 210, 211"])
    if not re.search(r"For a period of two months:\s*Basic Charge per period", small):
        raise ValueError("Rates 201-203 billing period not printed")
    small_basic = _one(r"Basic Charge per period " + _NUM, small, "Rates 201-203 basic")
    small_energy = _one(r"All kW\.h per period " + _NUM + r" per kW\.h", small, "Rates 201-203 energy")
    for code, name, sub_class in (("201", "General Service (Under 35 kW)", "general commercial under 35 kW"),
                                  ("202", "General Service (Under 35 kW) – Common Use Areas",
                                   "common use areas of rental apartment and strata mixed-use buildings under 35 kW")):
        add(code, name, "commercial", sub_class, "flat", [
            comp(component_type="fixed", component_name="Basic Charge", charge_value=small_basic,
                 charge_unit="$/two months", notes="Per two-month period; also the minimum charge."),
            comp(component_type="energy", component_name="Energy Charge", charge_value=small_energy, charge_unit="$/kWh"),
            *rider_components(small, "Rates 201-203")], "No demand meter: estimated demand under 35 kW.")
    large = _body(schedule, r"RATES 210, 211, 212, 213, 220, 230 and 240", [r"RATE 241"])
    rate = re.search(r"Basic Charge " + _NUM + r" per month\s*Demand Charge First (\d+) kW of billing demand per month "
                     r"NIL\s*Next (\d+) kW of billing demand per month " + _NUM + r" per kW\s*All\s*additional kW of "
                     r"billing demand per month " + _NUM + r" per kW.*?Energy Charge First ([\d,]+) kW\.h per month "
                     + _NUM + r" per kW\.h\s*All additional kW\.h per month " + _NUM + r" per kW\.h", large, re.S)
    if not rate:
        raise ValueError("Rates 210-240 prices not found")
    free, step = float(rate.group(2)), float(rate.group(2)) + float(rate.group(3))
    block = float(rate.group(6).replace(",", ""))
    primary = re.search(r"A discount of 1(?:½|\ufffd|\.5) ?% shall be applied to the above Rates if a customer.s\s*"
                        r"supply of electricity is metered at a primary potential", large)
    transformer = _one(r"A discount of \$(\.\d+|\d+\.\d+) per kW of billing demand shall be applied", large,
                       "Rates 230/240 discount")
    if not primary:
        raise ValueError("Rates 220/240 primary-metering discount not found")
    for code, name, sub_class in (("210", "General Service (35 kW and Over)", "general commercial 35 kW and over"),
                                  ("211", "General Service (35 kW and Over) – Rental Apartment Common Areas",
                                   "common use areas of rental apartment buildings, 35 kW and over"),
                                  ("212", "General Service (35 kW and Over) – Strata Mixed-Use Common Areas",
                                   "common use areas of strata mixed-use buildings, 35 kW and over")):
        add(code, name, "commercial", sub_class, "demand", [
            comp(component_type="fixed", component_name="Basic Charge", charge_value=float(rate.group(1)),
                 charge_unit="$/month"),
            comp(component_type="demand", component_name=f"Demand Charge — First {free:g} kW", charge_value=0.0,
                 charge_unit="$/kW/month", demand_unit="kW", tier_number=1, tier_threshold=free, tier_unit="kW"),
            comp(component_type="demand", component_name=f"Demand Charge — Next {step - free:g} kW",
                 charge_value=float(rate.group(4)), charge_unit="$/kW/month", demand_unit="kW", tier_number=2,
                 tier_threshold=step, tier_unit="kW"),
            comp(component_type="demand", component_name="Demand Charge — Additional kW",
                 charge_value=float(rate.group(5)), charge_unit="$/kW/month", demand_unit="kW", tier_number=3,
                 tier_threshold=step, tier_unit="kW"),
            comp(component_type="energy", component_name=f"Energy Charge — First {block:,.0f} kWh",
                 charge_value=float(rate.group(7)), charge_unit="$/kWh", tier_number=1, tier_threshold=block,
                 tier_unit="kWh/month"),
            comp(component_type="energy", component_name="Energy Charge — Additional kWh",
                 charge_value=float(rate.group(8)), charge_unit="$/kWh", tier_number=2, tier_threshold=block,
                 tier_unit="kWh/month"),
            comp(component_type="rebate", component_name="Primary Metering Discount", charge_value=-1.5,
                 charge_unit="%", sub_component="conditional_credit",
                 notes="Conditional: 1.5% discount when the supply is metered at a primary potential (Rates 220/240)."),
            comp(component_type="rebate", component_name="Customer Transformation Discount",
                 charge_value=-transformer, charge_unit="$/kW/month", demand_unit="kW",
                 sub_component="conditional_credit",
                 notes="Conditional: per kW of billing demand when the customer supplies the transformation "
                       "(Rates 230/240; the primary-metering discount applies first)."),
            *rider_components(large, "Rates 210-240")], "Rates 220, 230 and 240 are this rate with the conditional "
                                                         "discounts. Billing demand is estimated when no demand meter is installed.")
    return records


class NewWestminsterScraper(BaseScraper):
    """Parse the City of New Westminster Electrical Utility Schedule of Rates (Bylaw No. 6502, Schedule A)."""

    def __init__(self) -> None:
        super().__init__(utility_name=UTILITY, province="BC")

    def scrape(self) -> list[TariffRecord]:
        # No seed fallback for utilities added in batch 18 (provisional decision 2026-11-04).
        records = self._try_live_scrape()
        if not records:
            self.logger.warning("New Westminster: no live records (no seed fallback)")
        return records

    def _discover(self) -> tuple[str, str]:
        try:
            url = find_bylaw_url(self.fetch_page(BYLAW_INDEX_URL))
        except Exception as exc:
            self.logger.warning("New Westminster bylaw index unavailable: %s", exc)
            url = None
        if url:
            return url, ""
        return LAST_KNOWN_BYLAW_URL, ("The bylaw index did not link Bylaw No. 6502, so the last known consolidation "
                                      "was read (it may not be the current one).")

    def _try_live_scrape(self) -> list[TariffRecord]:
        url, note = self._discover()
        try:
            pages = extract_pdf_pages(self.fetch_bytes(url), drop_repeated_lines=False)
            records = parse_schedule(pages, url, discovery_note=note)
        except Exception as exc:
            self.logger.warning("New Westminster Schedule A failed closed: %s", exc)
            return []
        return self.mark_live_parsed(records)
