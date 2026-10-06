"""
fortisbc_electric.py — Scraper for FortisBC Electric rates (British Columbia).

FortisBC Electric serves the southern interior of BC. Its BCUC-accepted Electric
Tariff is the system of record; the PDF is parsed page by page for the building
related schedules:

  RS 1 residential, RS 2A residential time-of-use (closed),
  RS 20 small commercial, RS 21 commercial,
  RS 22A secondary time-of-use, RS 23A primary time-of-use.

Official sources:
  https://fbcdotcomprod.blob.core.windows.net/libraries/docs/default-source/about-us-documents/regulatory-affairs-documents/electric-utility/fortisbcelectrictariff.pdf
  https://www.fortisbc.com/accounts-billing/billing-rates/electricity-rates/residential-rates

Also parsed: RS 30 / RS 32 large commercial primary (500 kVA+), RS 31 / RS 33
industrial transmission (5,000 kVA+) and the RS 85 Green Power rider. Not covered:
RS 37 stand-by (RS 31 only), RS 38 interruptible pilot, net metering (RS 95), EV charging
(RS 96), financing (RS 91) and the residential landing page (no static rate text).

Regulated by: British Columbia Utilities Commission (BCUC)
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Callable, Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import DocumentPage, normalize_document_text

logger = logging.getLogger(__name__)

TARIFF_URL = (
    "https://fbcdotcomprod.blob.core.windows.net/libraries/docs/default-source/"
    "about-us-documents/regulatory-affairs-documents/electric-utility/fortisbcelectrictariff.pdf"
)
RESIDENTIAL_RATES_URL = "https://www.fortisbc.com/accounts-billing/billing-rates/electricity-rates/residential-rates"

_CENT_GLYPHS = "¢ȼ"
_TARIFF_PAGE_FOOTER = re.compile(r"(?:Revision of|Original) Page (R-\d+[A-Z]?\.\d+)")
_TARIFF_PAGE_FILTER = re.compile(r"(?:Revision of|Original) Page R-(?:1|2A|20|21|22A|23A|30|31|32|33|85)\.\d+\b")
_EFFECTIVE_DATE = re.compile(r"Effective Date:\s*([A-Z][a-z]+ \d{1,2}, \d{4})")
_CUSTOMER_CHARGE = re.compile(
    r"CUSTOMER\s+(?:A\s+)?CHARGE:\s*\$(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?) per (two Month period|Month)\b"
)
_PRIMARY_DISCOUNT = re.compile(
    r"discount of (\d+(?:\.\d+)?)% will be applied to the above rate if the electric "
    r"service is metered at a primary distribution voltage"
)

# Published schedule values, used only when the official PDF cannot be read.
SEED_RESIDENTIAL = {
    "effective_date": "2026-01-01",
    "source_url": TARIFF_URL,
    "energy_cents_per_kwh": "15.503",
    "customer_charge_per_two_months": 49.58,
}

SEED_SMALL_GENERAL = {
    "effective_date": "2026-01-01",
    "source_url": TARIFF_URL,
    "energy_cents_per_kwh": "12.934",
    "customer_charge_per_two_months": 59.51,
    "primary_voltage_discount_percent": 1.5,
}


@dataclass(frozen=True)
class _PageSource:
    """Attribution of one tariff page."""

    effective_date: str
    detail: Optional[str]


@dataclass(frozen=True)
class _TouSeason:
    """One published pricing season and the ordered source text proving its hours."""

    name: str
    months: tuple[int, ...]
    marker: str
    on_peak_hours: tuple[str, ...]
    off_peak_hours: tuple[str, ...]


_SUMMER_JULY_AUGUST = (7, 8)
_ALL_MONTHS = tuple(range(1, 13))
_OTHER_THAN_SUMMER = tuple(month for month in _ALL_MONTHS if month not in _SUMMER_JULY_AUGUST)

_SECONDARY_TOU_SEASONS = (
    _TouSeason(
        "Summer", _SUMMER_JULY_AUGUST, "(July, August)",
        ("9:00 am - 11:00 am Monday-Friday", "3:00 pm – 11:00 pm Monday-Friday"),
        ("11:00 pm - 9:00 am Monday-Friday", "11:00 am – 3:00pm Monday-Friday",
         "All hours on Saturday and Sunday"),
    ),
    _TouSeason(
        "All other months", _OTHER_THAN_SUMMER, "All other months",
        ("8:00 am - 1:00 pm Monday-Friday", "5:00 pm - 10:00 pm Monday-Friday"),
        ("10:00 pm to 8:00 am Monday-Friday", "1:00 pm - 5:00 pm Monday-Friday",
         "All hours on Saturday and Sunday"),
    ),
)

_WINTER_MONTHS = (11, 12, 1, 2)
_SHOULDER_MONTHS = tuple(month for month in _ALL_MONTHS if month not in _SUMMER_JULY_AUGUST + _WINTER_MONTHS)
_PRIMARY_TOU_SEASONS = (
    _TouSeason(
        "Winter", _WINTER_MONTHS, "(Nov. - Feb.)",
        ("7:00 am - 12:00 pm business days", "4:00 pm - 10:00 pm business days"),
        ("10:00 pm to 7:00 am business days", "12:00 pm - 4:00 pm business days",
         "All hours on weekends and statutory holidays"),
    ),
    _TouSeason(
        "Summer", _SUMMER_JULY_AUGUST, "(July, August)",
        ("10:00 am - 9:00 pm business days",),
        ("9:00 pm - 10:00 am", "All hours on weekends and statutory holidays"),
    ),
    _TouSeason(
        "Shoulder", _SHOULDER_MONTHS, "(all other months)",
        ("6:00 am - 10:00 pm, Monday to Saturday",),
        ("10:00 pm to 6:00 am - Monday to Saturday, All day Sunday",),
    ),
)

_TOU_ELIGIBILITY_TEXT = (
    "available for a minimum of 12 consecutive Months and will continue, at the election of "
    "the Customer, to be available for a minimum of 36 consecutive Months"
)


# ─── Text helpers ──────────────────────────────────────────────

def _flatten(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("ȼ", "¢")).strip()


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text.replace("ȼ", "¢").replace("–", "-").replace("—", "-")).casefold()


def _cents_to_dollars(raw_cents: str) -> float:
    return round(float(raw_cents) / 100.0, 6)


def _require(match: Optional[re.Match[str]], description: str) -> re.Match[str]:
    if match is None:
        raise ValueError(f"missing {description}")
    return match


def _require_ordered_text(page_text: str, ordered_phrases: list[str], description: str) -> None:
    """Every phrase must occur, in the published order, in the page text."""
    squashed = _squash(page_text)
    position = 0
    for phrase in ordered_phrases:
        found = squashed.find(_squash(phrase), position)
        if found == -1:
            raise ValueError(f"missing or reordered {description}: {phrase!r}")
        position = found + len(_squash(phrase))


def _today() -> date:
    return datetime.now(timezone.utc).date()


# ─── Page selection ────────────────────────────────────────────

def _schedule_page(pages: list[DocumentPage], code: str, sheet_number: int = 1) -> DocumentPage:
    """Find a schedule sheet by heading and printed footer (R-<code>.<sheet>)."""
    code_pattern = re.escape(code[:-1]) + r"\s?" + code[-1] if code.endswith("A") else re.escape(code)
    heading = re.compile(rf"(?:RATE )?SCHEDULE {code_pattern}\s+-\s")
    footer = f"R-{code}.{sheet_number}"
    for page in pages:
        flat = _flatten(page.text)
        footer_match = _TARIFF_PAGE_FOOTER.search(flat)
        if footer_match and footer_match.group(1) == footer and heading.search(flat):
            if re.search(r"is cancelled|no longer in effect", flat, re.I):
                raise ValueError(f"Rate Schedule {code} is cancelled")
            return page
    raise ValueError(f"Rate Schedule {code} sheet {footer} not found")


def _page_source(page: DocumentPage, code: str, sheet_number: int = 1) -> _PageSource:
    flat = _flatten(page.text)
    match = _require(_EFFECTIVE_DATE.search(flat), f"effective date on page {page.page_number}")
    try:
        effective = datetime.strptime(match.group(1), "%B %d, %Y").date()
    except ValueError as exc:
        raise ValueError(f"unparseable effective date {match.group(1)!r}") from exc
    if effective > _today():
        raise ValueError(f"page {page.page_number} is not yet in effect ({effective.isoformat()})")
    return _PageSource(
        effective.isoformat(),
        f"Electric Tariff PDF page {page.page_number}, Rate Schedule {code} sheet R-{code}.{sheet_number}",
    )


# ─── Record building blocks ────────────────────────────────────

def _component(
    source: _PageSource,
    component_type: str,
    name: str,
    value: float,
    unit: str,
    **fields: object,
) -> RateComponent:
    if component_type != "rebate" and value <= 0:
        raise ValueError(f"non-positive {name}")
    return RateComponent(
        component_type=component_type,
        component_name=name,
        charge_value=value,
        charge_unit=unit,
        effective_date=source.effective_date,
        source_url=TARIFF_URL,
        source_detail=source.detail,
        **fields,  # type: ignore[arg-type]
    )


def _customer_charge_component(source: _PageSource, flat: str) -> RateComponent:
    match = _require(_CUSTOMER_CHARGE.search(flat), "customer charge")
    unit = "$/two months" if match.group(2).startswith("two") else "$/month"
    note = (
        "Published per two-month period; prorated on a monthly basis for monthly billing."
        if unit == "$/two months" else
        "Published per month; FortisBC may bill bimonthly, in which case the charge is doubled."
    )
    return _component(source, "fixed", "Customer Charge", float(match.group(1).replace(",", "")), unit, notes=note)


def _tariff(
    code: str,
    name: str,
    customer_class: str,
    rate_structure: str,
    sources: list[_PageSource],
    components: list[RateComponent],
    **fields: object,
) -> TariffRecord:
    return TariffRecord(
        utility_name="FortisBC Electric",
        province="BC",
        utility_type="electricity",
        tariff_name=name,
        tariff_code=code,
        customer_class=customer_class,
        rate_structure=rate_structure,
        pricing_method="regulated",
        effective_date=max(source.effective_date for source in sources),
        source_url=TARIFF_URL,
        source_page="; ".join(dict.fromkeys(source.detail for source in sources if source.detail)) or None,
        confidence="high",
        components=components,
        **fields,  # type: ignore[arg-type]
    )


def _residential_record(energy_cents: str, customer_charge: float, source: _PageSource) -> TariffRecord:
    return _tariff(
        "01", "Residential Service (Rate 01)", "residential", "flat", [source],
        [
            _component(source, "fixed", "Basic Charge", customer_charge, "$/two months",
                       notes="Published per two-month period; prorated on a monthly basis for monthly billing."),
            _component(source, "energy", "Energy Charge", _cents_to_dollars(energy_cents), "$/kWh",
                       notes="Single flat rate on all kWh; the earlier two-step structure is no longer published."),
        ],
        eligibility="Residential use including service to incidental motors of 5 HP or less",
        notes="FortisBC Electric Rate Schedule 1, permanent rates under BCUC Order G-293-25.",
    )


def _primary_voltage_discount(source: _PageSource, percent: float) -> RateComponent:
    if not 0 < percent < 100:
        raise ValueError("invalid primary-voltage discount")
    return _component(
        source, "rebate", "Primary Metering Voltage Discount", -percent, "%", sub_component="conditional",
        notes="Conditional: applies only if service is metered at a primary distribution voltage; "
              "the rates shown are for standard secondary voltage.",
    )


def _small_commercial_record(
    energy_cents: str, customer_charge: float, discount_percent: float, source: _PageSource
) -> TariffRecord:
    return _tariff(
        "20", "Small General Service (Rate 20)", "commercial", "flat", [source],
        [
            _component(source, "fixed", "Basic Charge", customer_charge, "$/two months",
                       notes="Published per two-month period; prorated on a monthly basis for monthly billing."),
            _component(source, "energy", "Energy Charge", _cents_to_dollars(energy_cents), "$/kWh",
                       notes="Applies to all kWh at standard secondary voltage."),
            _primary_voltage_discount(source, discount_percent),
        ],
        sub_class="small general service",
        eligibility="Commercial customers whose demand is generally not more than 40 kW, supplied through one meter",
        demand_max_kw=40,
        notes="FortisBC Electric Rate Schedule 20; there is no demand charge. Permanent rates under BCUC Order G-293-25.",
    )


# ─── Flat-rate schedule parsers ────────────────────────────────

def _parse_residential(pages: list[DocumentPage]) -> TariffRecord:
    page = _schedule_page(pages, "1")
    source = _page_source(page, "1")
    flat = _flatten(page.text)
    energy = _require(
        re.search(rf"All kW\.h @ (\d+(?:\.\d+)?)\s*[{_CENT_GLYPHS}]\s*per kW\.h", flat), "energy charge in cents"
    )
    customer = _require(_CUSTOMER_CHARGE.search(flat), "customer charge")
    if not customer.group(2).startswith("two"):
        raise ValueError("unexpected residential customer charge period")
    return _residential_record(energy.group(1), float(customer.group(1)), source)


def _parse_small_commercial(pages: list[DocumentPage]) -> TariffRecord:
    page = _schedule_page(pages, "20")
    source = _page_source(page, "20")
    flat = _flatten(page.text)
    _require(re.search(r"generally not more than 40 kW", flat), "Rate 20 40 kW eligibility")
    energy = _require(
        re.search(rf"All kW\.h @ (\d+(?:\.\d+)?)\s*[{_CENT_GLYPHS}]\s*per kW\.h", flat), "energy charge in cents"
    )
    customer = _require(_CUSTOMER_CHARGE.search(flat), "customer charge")
    if not customer.group(2).startswith("two"):
        raise ValueError("unexpected Rate 20 customer charge period")
    discount = _require(_PRIMARY_DISCOUNT.search(flat), "primary metering voltage discount")
    return _small_commercial_record(energy.group(1), float(customer.group(1)), float(discount.group(1)), source)


def _parse_commercial(pages: list[DocumentPage]) -> TariffRecord:
    first_page = _schedule_page(pages, "21")
    second_page = _schedule_page(pages, "21", 2)
    first_source = _page_source(first_page, "21")
    second_source = _page_source(second_page, "21", 2)
    flat = _flatten(first_page.text)
    continuation = _flatten(second_page.text)
    squashed = _squash(first_page.text)

    limits = _require(
        re.search(r"generally greater than (\d+) kW but less than (\d+) kW", flat), "Rate 21 kW eligibility"
    )
    demand = _require(
        re.search(r'\$(\d+(?:\.\d+)?) per kW of ["“”]?Billing Demand["“”]? above (\d+) kW', flat),
        "demand charge",
    )
    if demand.group(2) != limits.group(1):
        raise ValueError("demand charge threshold differs from the eligibility lower bound")
    energy = _require(
        re.search(rf"An Energy Charge of: (\d+(?:\.\d+)?)\s*[{_CENT_GLYPHS}] per kW\.h", flat), "energy charge in cents"
    )
    customer = _customer_charge_component(first_source, flat)
    if customer.charge_unit != "$/month":
        raise ValueError("unexpected Rate 21 customer charge period")
    primary = _require(_PRIMARY_DISCOUNT.search(flat), "primary metering voltage discount")
    for phrase in ("twenty-five per cent (25%) of the Contract Demand",
                   "the maximum Demand in kW for the current billing Month",
                   "seventy-five per cent (75%) of the maximum Demand in kW registered during the previous eleven Month period"):
        if _squash(phrase) not in squashed:
            raise ValueError(f"missing Billing Demand rule: {phrase!r}")

    transformation = _require(
        re.search(
            rf"discount of (\d+(?:\.\d+)?)\s*[{_CENT_GLYPHS}] per kW of Billing Demand will be applied to the above "
            r"rate if the Customer supplies the transformation from the primary to the secondary voltage",
            continuation,
        ),
        "customer-supplied transformation discount",
    )
    kva_threshold = _require(re.search(r"\b(\d+) kW will become (\d+) kVA", continuation), "kVA threshold")
    kva_discount = _require(
        re.search(
            rf"(\d+(?:\.\d+)?)\s*[{_CENT_GLYPHS}] per kW will become (\d+(?:\.\d+)?)\s*[{_CENT_GLYPHS}] per kVA",
            continuation,
        ),
        "kVA transformation discount",
    )
    kva_demand = _require(
        re.search(r"\$(\d+(?:\.\d+)?) per kW will become \$(\d+(?:\.\d+)?) per kVA", continuation), "kVA demand charge"
    )
    if kva_threshold.group(1) != demand.group(2):
        raise ValueError("kVA conversion does not refer to the demand threshold")
    if kva_discount.group(1) != transformation.group(1) or kva_demand.group(1) != demand.group(1):
        raise ValueError("kVA conversions do not refer to the published kW charges")

    billing_demand_note = (
        "Billing Demand is the greatest of 25% of Contract Demand, the maximum demand in kW for the "
        "current billing month, or 75% of the maximum demand registered in the previous eleven months."
    )
    kva_note = (
        f"Alternate to the kW charge, used only if FortisBC measures demand in kVA; the threshold becomes "
        f"{kva_threshold.group(2)} kVA."
    )
    components = [
        customer,
        _component(first_source, "demand", "Demand Charge", float(demand.group(1)), "$/kW",
                   demand_threshold_kw=float(demand.group(2)), demand_unit="kW",
                   notes=f"Per kW of Billing Demand above {demand.group(2)} kW. {billing_demand_note}"),
        _component(first_source, "energy", "Energy Charge", _cents_to_dollars(energy.group(1)), "$/kWh"),
        _primary_voltage_discount(first_source, float(primary.group(1))),
        _component(second_source, "rebate", "Customer-Supplied Transformation Discount",
               -_cents_to_dollars(transformation.group(1)), "$/kW", sub_component="conditional",
                   notes="Conditional: per kW of Billing Demand when the customer supplies the primary-to-secondary "
                         "transformation. If also entitled to the primary metering discount, that is applied first."),
        _component(second_source, "demand", "Demand Charge (kVA basis)", float(kva_demand.group(2)), "$/kVA",
                   demand_unit="kVA", sub_component="alternative", notes=kva_note),
        _component(second_source, "rebate", "Customer-Supplied Transformation Discount (kVA basis)",
                   -_cents_to_dollars(kva_discount.group(2)), "$/kVA", sub_component="conditional alternative", notes=kva_note),
    ]
    return _tariff(
        "21", "Commercial Service (Rate 21)", "commercial", "demand", [first_source, second_source], components,
        sub_class="commercial service",
        eligibility="Commercial customers whose demand is generally greater than 40 kW but less than 500 kW, supplied through one meter",
        demand_min_kw=float(limits.group(1)),
        demand_max_kw=float(limits.group(2)),
        notes="FortisBC Electric Rate Schedule 21. Billing codes A-D on the bill only describe measurement and metering.",
    )


# ─── Time-of-use schedule parsers ──────────────────────────────

def _tou_rates(page: DocumentPage, seasons: tuple[_TouSeason, ...]) -> list[tuple[float, float]]:
    """Return (on-peak, off-peak) dollars per kWh for each season in published order."""
    flat = _flatten(page.text)
    start = _require(re.search(r"RATES BY PRICING PERIOD:", flat), "pricing period table")
    stop = _require(re.search(r"CUSTOMER\s+(?:A\s+)?CHARGE:", flat[start.end():]), "customer charge after rates")
    region = flat[start.end():start.end() + stop.start()]
    if f"{_CENT_GLYPHS[0]}/kW.h" not in region:
        raise ValueError("rate table is not labelled in cents per kWh")
    values = re.findall(r"(?<![\d.:])(-?\d+\.\d{3})(?![\d:])", region)
    if len(values) != 2 * len(seasons):
        raise ValueError(f"expected {2 * len(seasons)} period rates, found {len(values)}")
    pairs = [(_cents_to_dollars(values[2 * index]), _cents_to_dollars(values[2 * index + 1]))
             for index in range(len(seasons))]
    if any(on_peak <= off_peak or off_peak <= 0 for on_peak, off_peak in pairs):
        raise ValueError("on-peak rate is not above off-peak rate; column order is uncertain")
    ordered: list[str] = []
    for season in seasons:
        ordered.extend([season.marker, *season.on_peak_hours, *season.off_peak_hours])
    _require_ordered_text(region, ordered, "pricing period hours")
    return pairs


def _tou_components(
    source: _PageSource, page: DocumentPage, seasons: tuple[_TouSeason, ...]
) -> list[RateComponent]:
    components = [_customer_charge_component(source, _flatten(page.text))]
    for season, (on_peak, off_peak) in zip(seasons, _tou_rates(page, seasons)):
        months = ",".join(str(month) for month in season.months)
        for period, value, hours in (
            ("on-peak", on_peak, season.on_peak_hours), ("off-peak", off_peak, season.off_peak_hours)
        ):
            components.append(_component(
                source, "energy", f"{season.name} {period.title()} Energy Charge", value, "$/kWh",
                tou_period=period, tou_hours="; ".join(hours), season=season.name.lower(),
                season_months=months,
            ))
    return components


def _require_tou_availability(page: DocumentPage) -> None:
    if _squash(_TOU_ELIGIBILITY_TEXT) not in _squash(page.text):
        raise ValueError("missing time-of-use minimum-term eligibility")


def _parse_residential_tou(pages: list[DocumentPage]) -> TariffRecord:
    page = _schedule_page(pages, "2A")
    source = _page_source(page, "2A")
    if not re.search(r"TIME OF USE\s*-\s*CLOSED\b", _flatten(page.text)):
        raise ValueError("missing Rate 2A closed-enrollment notice")
    _require_tou_availability(page)
    components = _tou_components(source, page, _SECONDARY_TOU_SEASONS)
    return _tariff(
        "2A", "Residential Time of Use - Closed (Rate 2A)", "residential", "tou", [source], components,
        sub_class="time of use (closed)",
        eligibility=(
            "Closed schedule. Residential use including incidental motors of 5 HP or less; customers with "
            "satisfactory load factors as determined by FortisBC; minimum 12 consecutive months, then at the "
            "customer's election a minimum of 36 consecutive months."
        ),
        notes="FortisBC Electric Rate Schedule 2A. The published on/off-peak rates are identical in both seasons.",
    )


def _parse_secondary_tou(pages: list[DocumentPage]) -> TariffRecord:
    page = _schedule_page(pages, "22A")
    source = _page_source(page, "22A")
    flat = _flatten(page.text)
    limits = _require(
        re.search(r"Demand is less than (\d+) kW and is supplied at a secondary distribution voltage", flat),
        "Rate 22A eligibility",
    )
    _require_tou_availability(page)
    return _tariff(
        "22A", "Commercial Service - Secondary - Time of Use (Rate 22A)", "commercial", "tou", [source],
        _tou_components(source, page, _SECONDARY_TOU_SEASONS),
        sub_class="secondary time of use",
        eligibility=(
            f"Commercial customers with demand less than {limits.group(1)} kW at a secondary distribution voltage "
            "through one meter; satisfactory load factors; minimum 12 consecutive months, then at the customer's "
            "election a minimum of 36 consecutive months."
        ),
        demand_max_kw=float(limits.group(1)),
        notes="FortisBC Electric Rate Schedule 22A. There is no demand charge; the same rates apply in both seasons.",
    )


def _parse_primary_tou(pages: list[DocumentPage]) -> TariffRecord:
    page = _schedule_page(pages, "23A")
    source = _page_source(page, "23A")
    flat = _flatten(page.text)
    limits = _require(
        re.search(r"Demand is less than (\d+) kW and is supplied at a primary distribution voltage", flat),
        "Rate 23A eligibility",
    )
    _require_tou_availability(page)
    return _tariff(
        "23A", "Commercial Service - Primary - Time of Use (Rate 23A)", "commercial", "tou", [source],
        _tou_components(source, page, _PRIMARY_TOU_SEASONS),
        sub_class="primary time of use",
        eligibility=(
            f"Commercial customers with demand less than {limits.group(1)} kW at a primary distribution voltage "
            "through one meter; satisfactory load factors; minimum 12 consecutive months, then at the customer's "
            "election a minimum of 36 consecutive months."
        ),
        demand_max_kw=float(limits.group(1)),
        notes="FortisBC Electric Rate Schedule 23A. There is no demand charge.",
    )


# ─── Large commercial and optional schedules ───────────────────

def _parse_large_commercial_primary(pages: list[DocumentPage]) -> TariffRecord:
    first_page = _schedule_page(pages, "30")
    second_page = _schedule_page(pages, "30", 2)
    first_source = _page_source(first_page, "30")
    second_source = _page_source(second_page, "30", 2)
    flat = _flatten(first_page.text)
    continuation = _flatten(second_page.text)

    _require(
        re.search(r"APPLICABLE: To power service to Customers for a contract Demand of 500 kVA or more, "
                  r"subject to written agreement", flat),
        "Rate 30 500 kVA contract-demand eligibility",
    )
    demand = _require(
        re.search(r"Demand Charge of: \$(\d+(?:\.\d+)?) per kVA of Billing Demand", flat), "demand charge per kVA"
    )
    energy = _require(
        re.search(rf"All kW\.h @ (\d+(?:\.\d+)?)\s*[{_CENT_GLYPHS}]\s*per kW\.h", flat), "energy charge in cents"
    )
    customer = _customer_charge_component(first_source, flat)
    if customer.charge_unit != "$/month":
        raise ValueError("unexpected Rate 30 customer charge period")
    squashed = _squash(first_page.text)
    for phrase in ("twenty-five percent (25%) of the Contract Demand",
                   "the maximum Demand in kVA for the current billing Month",
                   "seventy-five percent (75%) of the maximum Demand in kVA registered during the previous eleven Month period"):
        if _squash(phrase) not in squashed:
            raise ValueError(f"missing Billing Demand rule: {phrase!r}")

    _require(
        re.search(r"rate applies to power service when taken at FortisBC.s standard primary distribution voltage", continuation),
        "primary-voltage basis of the rate",
    )
    metering = _require(
        re.search(r"A discount of (\d+(?:\.\d+)?)% will be applied to the above rate if the electric service is "
                  r"metered at a transmission line voltage", continuation),
        "transmission metering discount",
    )
    transformation = _require(
        re.search(r"A discount of \$(\d+(?:\.\d+)?) per kVA of billing Demand will be applied to(?: [A-Z])? the above "
                  r"rate if the Customer supplies the transformation from the transmission line voltage to the "
                  r"primary distribution voltage", continuation),
        "customer-supplied transformation discount",
    )
    _require(
        re.search(r"discount applicable to the metering at a transmission line voltage is to be applied first", continuation),
        "discount ordering rule",
    )
    percent = float(metering.group(1))
    if not 0 < percent < 100:
        raise ValueError("invalid transmission metering discount")

    billing_demand_note = (
        "Billing Demand is the greatest of 25% of Contract Demand, the maximum demand in kVA for the "
        "current billing month, or 75% of the maximum demand registered in the previous eleven months."
    )
    components = [
        customer,
        _component(first_source, "demand", "Demand Charge", float(demand.group(1)), "$/kVA", demand_unit="kVA",
                   notes=f"Per kVA of Billing Demand. {billing_demand_note}"),
        _component(first_source, "energy", "Energy Charge", _cents_to_dollars(energy.group(1)), "$/kWh"),
        _component(second_source, "rebate", "Transmission Metering Voltage Discount", -percent, "%",
                   sub_component="conditional",
                   notes="Conditional: applies only if service is metered at a transmission line voltage; rates "
                         "shown are for the standard primary distribution voltage. Applied before the transformation discount."),
        _component(second_source, "rebate", "Customer-Supplied Transformation Discount",
                   -float(transformation.group(1)), "$/kVA", demand_unit="kVA", sub_component="conditional",
                   notes="Conditional: per kVA of Billing Demand when the customer supplies the transformation from "
                         "the transmission line voltage to the primary distribution voltage."),
    ]
    return _tariff(
        "30", "Large Commercial Service - Primary (Rate 30)", "commercial", "demand",
        [first_source, second_source], components,
        sub_class="large commercial primary",
        eligibility="Contract Demand of 500 kVA or more, subject to written agreement; standard primary distribution voltage",
        notes="FortisBC Electric Rate Schedule 30. Not restricted to industrial customers in the schedule text. "
              "Permanent rates under BCUC Order G-293-25.",
    )


def _parse_large_commercial_primary_tou(pages: list[DocumentPage]) -> TariffRecord:
    page = _schedule_page(pages, "32")
    source = _page_source(page, "32")
    flat = _flatten(page.text)
    limits = _require(
        re.search(r"contract Demand of (\d+) kVA or more, taking service at a standard primary distribution "
                  r"voltage, subject to written agreement", flat),
        "Rate 32 eligibility",
    )
    _require_tou_availability(page)
    return _tariff(
        "32", "Large Commercial Service - Primary - Time of Use (Rate 32)", "commercial", "tou", [source],
        _tou_components(source, page, _PRIMARY_TOU_SEASONS),
        sub_class="large commercial primary time of use",
        eligibility=(
            f"Contract Demand of {limits.group(1)} kVA or more at a standard primary distribution voltage, "
            "subject to written agreement; satisfactory load factors; minimum 12 consecutive months, then at the "
            "customer's election a minimum of 36 consecutive months."
        ),
        notes="FortisBC Electric Rate Schedule 32. No demand charge is published on this sheet; the schedule "
              "text does not restrict it to industrial customers.",
    )


def _parse_industrial_transmission(pages: list[DocumentPage]) -> TariffRecord:
    page = _schedule_page(pages, "31")
    source = _page_source(page, "31")
    flat = _flatten(page.text)
    _require(re.search(r"AVAILABLE: In all areas served by FortisBC for supply at 60 hertz, three phase with a "
                       r"nominal potential of 60,000 volts or higher as available", flat), "Rate 31 voltage")
    _require(re.search(r"Applicable to industrial Customers with loads of 5,000 kVA or more, subject to "
                       r"written agreement", flat), "Rate 31 eligibility")
    wires = _require(re.search(r"Wires Charge of: \$(\d+(?:\.\d+)?) per kVA of Billing Demand", flat), "wires charge")
    supply = _require(re.search(r"Power Supply Charge of: \$(\d+(?:\.\d+)?) per kVA of maximum Demand in "
                                r"current billing Month", flat), "power supply demand charge")
    energy = _require(re.search(rf"All kW\.h @ (\d+(?:\.\d+)?)\s*[{_CENT_GLYPHS}]\s*per kW\.h", flat),
                      "energy charge")
    customer = _customer_charge_component(source, flat)
    if customer.charge_unit != "$/month":
        raise ValueError("unexpected Rate 31 customer charge period")
    for phrase in ("eighty percent (80%) of the Contract Demand",
                   "maximum Demand in kVA for the current billing Month",
                   "eighty percent (80%) of the maximum Demand in kVA recorded during the previous eleven Month period",
                   "Stand-by Billing Demand under Rate Schedule 37",
                   "except when Rate Schedule 37, Special Provision 7 applies"):
        if _squash(phrase) not in _squash(flat):
            raise ValueError(f"missing Rate 31 Billing Demand condition: {phrase}")
    return _tariff(
        "31", "Large Commercial Service - Transmission (Rate 31)", "industrial", "demand", [source],
        [customer,
         _component(source, "demand", "Wires Charge", float(wires.group(1)), "$/kVA", demand_unit="kVA",
                    notes="Per kVA of Billing Demand: greatest of 80% of contract demand, current-month maximum, "
                          "or 80% of the prior eleven-month maximum; applicable Rate 37 stand-by billing demand "
                          "is added except under its Special Provision 7."),
         _component(source, "demand", "Power Supply Charge", float(supply.group(1)), "$/kVA", demand_unit="kVA",
                    notes="Per kVA of maximum demand in the current billing month, not Billing Demand."),
         _component(source, "energy", "Energy Charge", _cents_to_dollars(energy.group(1)), "$/kWh")],
        sub_class="industrial transmission", eligibility="Industrial load of 5,000 kVA or more; three-phase "
        "60 Hz supply at 60,000 volts or higher where available, subject to written agreement",
        notes="FortisBC Electric Rate Schedule 31, BCUC Order G-293-25. No voltage or transformation credit "
              "is published on this schedule.",
    )


def _parse_industrial_transmission_tou(pages: list[DocumentPage]) -> TariffRecord:
    page = _schedule_page(pages, "33")
    source = _page_source(page, "33")
    flat = _flatten(page.text)
    _require(re.search(r"nominal potential of 60,000 volts or higher as available", flat), "Rate 33 voltage")
    _require(re.search(r"Applicable to industrial Customers with loads of 5,000 kVA or more, subject to "
                       r"written agreement", flat), "Rate 33 eligibility")
    _require_tou_availability(page)
    return _tariff(
        "33", "Large Commercial Service - Transmission - Time of Use (Rate 33)", "industrial", "tou",
        [source], _tou_components(source, page, _PRIMARY_TOU_SEASONS),
        sub_class="industrial transmission time of use",
        eligibility="Industrial load of 5,000 kVA or more; three-phase 60 Hz supply at 60,000 volts or higher "
                    "where available, written agreement and satisfactory load factor; minimum 12 consecutive "
                    "months, then at the customer's election a minimum of 36 consecutive months.",
        notes="FortisBC Electric Rate Schedule 33. No demand charge or transmission voltage credit is published.",
    )


def _parse_green_power(pages: list[DocumentPage]) -> TariffRecord:
    page = _schedule_page(pages, "85")
    source = _page_source(page, "85")
    flat = _flatten(page.text)
    _require(re.search(r"APPLICABLE: To any current rate Schedules", flat), "Rate 85 applicability")
    option_a = _require(
        re.search(rf"OPTION A - In addition to all charges on the applicable rate Schedule, an additional charge, "
                  rf"of all discounts, of (\d+(?:\.\d+)?)\s*[{_CENT_GLYPHS}]\s*per kW\.h is levied against all kW\.h sold",
                  flat),
        "Option A premium in cents per kWh",
    )
    option_b = _require(
        re.search(r"OPTION B - .*?in no case will the amount be less than \$(\d+(?:\.\d+)?) per Month", flat),
        "Option B monthly minimum",
    )
    return _tariff(
        "85", "Green Power Rider (Rate 85)", "other", "flat", [source],
        [_component(source, "rider", "Green Power Premium (Option A)", _cents_to_dollars(option_a.group(1)), "$/kWh",
                    sub_component="optional",
                    notes="Optional adder to all kWh sold under the customer's applicable rate schedule; Option B "
                          f"instead adds a customer-chosen dollar amount of at least ${option_b.group(1)} per month.")],
        sub_class="green power rider (optional)",
        eligibility="Any current rate schedule, on the same terms as that schedule, for purchase of electricity "
                    "from environmentally desirable technologies",
        notes="FortisBC Electric Rate Schedule 85. Voluntary add-on to another tariff, not a replacement energy price.",
    )


_SCHEDULE_PARSERS: tuple[tuple[str, Callable[[list[DocumentPage]], TariffRecord]], ...] = (
    ("1", _parse_residential),
    ("2A", _parse_residential_tou),
    ("20", _parse_small_commercial),
    ("21", _parse_commercial),
    ("22A", _parse_secondary_tou),
    ("23A", _parse_primary_tou),
    ("30", _parse_large_commercial_primary),
    ("31", _parse_industrial_transmission),
    ("32", _parse_large_commercial_primary_tou),
    ("33", _parse_industrial_transmission_tou),
    ("85", _parse_green_power),
)


def extract_schedule_pages(pdf_bytes: bytes) -> list[DocumentPage]:
    """Extract only the supported schedule sheets from the full Electric Tariff PDF.

    Whole-document pdfplumber extraction stalls on the tariff's table of contents, so
    pdfminer first locates sheets by their printed footer.
    """
    import pdfplumber
    from pdfminer.converter import TextConverter
    from pdfminer.layout import LAParams
    from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
    from pdfminer.pdfpage import PDFPage

    footer_pages: list[int] = []
    resource_manager = PDFResourceManager()
    for index, pdf_page in enumerate(PDFPage.get_pages(io.BytesIO(pdf_bytes))):
        buffer = io.StringIO()
        interpreter = PDFPageInterpreter(resource_manager, TextConverter(resource_manager, buffer, laparams=LAParams()))
        interpreter.process_page(pdf_page)
        if _TARIFF_PAGE_FILTER.search(buffer.getvalue()):
            footer_pages.append(index)

    pages: list[DocumentPage] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for index in footer_pages:
            text = pdf.pages[index].extract_text(x_tolerance=2, y_tolerance=3) or ""
            pages.append(DocumentPage(index + 1, normalize_document_text(text)))
    return pages


class FortisBCElectricScraper(BaseScraper):
    """Scrape FortisBC Electric building rate schedules from the official Electric Tariff."""

    def __init__(self):
        super().__init__(utility_name="FortisBC Electric", province="BC")

    def scrape(self) -> list[TariffRecord]:
        """Parse each schedule independently; label seed fallbacks for failed seeded classes."""
        try:
            pages = self._fetch_schedule_pages()
        except Exception as exc:
            self.logger.warning("FortisBC Electric tariff could not be read: %s", exc)
            pages = []

        live_records = self.parse_schedule_pages(pages)
        live_codes = {record.tariff_code for record in live_records}
        records = self.mark_live_parsed(live_records, source_url=TARIFF_URL) if live_records else []

        fallback = [record for record in self._seed_data() if record.tariff_code not in live_codes]
        if fallback:
            self.logger.warning("Live scrape incomplete — seed fallback for %s",
                                ", ".join(str(record.tariff_code) for record in fallback))
            records.extend(self.mark_fallback(fallback))
        return records

    def _fetch_schedule_pages(self) -> list[DocumentPage]:
        return extract_schedule_pages(self.fetch_bytes(TARIFF_URL))

    def parse_schedule_pages(self, pages: list[DocumentPage]) -> list[TariffRecord]:
        """Return the schedules that parse completely; a failing schedule is skipped and logged."""
        records: list[TariffRecord] = []
        for code, parser in _SCHEDULE_PARSERS:
            try:
                records.append(parser(pages))
            except ValueError as exc:
                self.logger.warning("FortisBC Electric Rate Schedule %s rejected: %s", code, exc)
        return records

    def _seed_data(self) -> list[TariffRecord]:
        """Fallback copies of the published RS 1 and RS 20 values; never presented as live."""
        residential_source = _PageSource(SEED_RESIDENTIAL["effective_date"], None)
        commercial_source = _PageSource(SEED_SMALL_GENERAL["effective_date"], None)
        return [
            _residential_record(
                SEED_RESIDENTIAL["energy_cents_per_kwh"],
                SEED_RESIDENTIAL["customer_charge_per_two_months"],
                residential_source,
            ),
            _small_commercial_record(
                SEED_SMALL_GENERAL["energy_cents_per_kwh"],
                SEED_SMALL_GENERAL["customer_charge_per_two_months"],
                SEED_SMALL_GENERAL["primary_voltage_discount_percent"],
                commercial_source,
            ),
        ]
