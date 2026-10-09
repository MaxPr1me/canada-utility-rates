"""
enmax_energy.py -- Scraper for ENMAX Energy Corporation Rate of Last Resort (Alberta).

ENMAX Energy Corporation is the Rate of Last Resort (RoLR) provider for the
ENMAX Power Corporation service area (City of Calgary). On January 1, 2025 the
RoLR replaced the Regulated Rate Option (RRO); its energy price is fixed for a
two-year term approved by the Alberta Utilities Commission (AUC).

Official sources:
  - ENMAX RoLR page (static HTML; content sits in the embedded Next.js data):
    the term sentence "The Rate of Last Resort is a fixed rate beginning
    <start>, and is expected to remain unchanged until <end>." and the
    "View the rate schedule" link.
  - ENMAX Energy RoLR rate schedule PDF ("Regulated Rate Tariff" pages):
    energy and administration charges, applicability, decision/effective date
    and interim status for the Residential and Small Commercial schedules.
  - Utilities Consumer Advocate default-rates table (Government of Alberta):
    required cross-check for ENMAX / ENMAX Power Corporation.

A printed rider without dates, a schedule for another year, or any
provider/UCA disagreement fails closed for the affected class. Delivery
charges and the Calgary local access fee come from ENMAX Power's tariff.

The RRO seed constants below are retained only as the labelled fallback (and
as database history); they are never presented as live rates.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from decimal import Decimal
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.alberta_rolr import (
    DATE_PATTERN,
    UCA_DEFAULT_RATES_URL,
    RolrError,
    RolrPeriod,
    energy_component,
    html_text,
    make_period,
    normalize_text,
    parse_date,
    parse_uca_table,
    require_current,
    rolr_record,
    uca_detail,
)
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

logger = logging.getLogger(__name__)

AESO_MARKET_URL = (
    "https://www.aeso.ca/market/market-and-system-reporting/"
    "hourly-pool-price-report/"
)

SOURCE_URL = (
    "https://www.enmax.com/home/rates-and-billing/"
    "understand-your-bill/regulated-rate-option"
)

ROLR_URL = "https://www.enmax.com/rateoflastresort"
UCA_RETAILER = "ENMAX"
UCA_DISTRIBUTOR = "ENMAX Power"
SERVICE_AREA = "ENMAX Power Corporation service area (City of Calgary)"

# kind: (rate schedule name, tariff_name, tariff_code, customer_class, distribution rate)
SCHEDULES = {
    "residential": ("Residential", "Rate of Last Resort - Residential", "RoLR-Res", "residential", "D100"),
    "small_business": (
        "Small Commercial", "Rate of Last Resort - Small Business", "RoLR-SB", "commercial", "D200",
    ),
}

_TERM = re.compile(
    rf"fixed rate beginning ({DATE_PATTERN}),? and is expected to remain unchanged until ({DATE_PATTERN})"
)
_HEAD = re.compile(
    r"ENMAX Energy Corporation (INTERIM )?(\d{4}) REGULATED RATE TARIFF "
    r"(Residential|Small Commercial|Medium Commercial|Large Commercial)\b"
)

SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": SOURCE_URL,
    "energy_rate": 0.1684,       # $/kWh
    "admin_fee_monthly": 5.95,   # $/month
}

SEED_COMMERCIAL = {
    "effective_date": "2024-10-01",
    "source_url": SOURCE_URL,
    "energy_rate": 0.1684,       # $/kWh
    "admin_fee_monthly": 7.95,   # $/month
}


def _next_data_strings(html: str) -> list[str]:
    """All string values of the page's embedded Next.js data (where ENMAX keeps its content)."""
    match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        return []
    try:
        stack = [json.loads(match.group(1))]
    except ValueError:
        return []
    strings: list[str] = []
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, str):
            strings.append(node)
    return strings


def parse_enmax_page(html: str) -> tuple[RolrPeriod, str, bool]:
    """Return (term, rate schedule URL, municipal-areas notice present) from the RoLR page."""
    blocks = [s for s in _next_data_strings(html) if "Last Resort" in s or "View the rate schedule" in s]
    text = " \n ".join([html_text(html)] + [html_text(s) for s in blocks])
    terms = {make_period(start, end) for start, end in _TERM.findall(text)}
    if len(terms) != 1:
        raise RolrError(f"ENMAX RoLR term sentence missing or inconsistent ({len(terms)} terms)")
    links = set()
    for doc in [html] + blocks:
        for anchor in parse_html(doc).find_all("a", href=True):
            if normalize_text(anchor.get_text(" ", strip=True)).casefold() == "view the rate schedule":
                links.add(anchor["href"].strip())
    if len(links) != 1 or not next(iter(links)).startswith("https://"):
        raise RolrError(f"ENMAX rate schedule link missing or ambiguous: {sorted(links)}")
    municipal = bool(re.search(
        r"Rate of Last Resort in Red Deer, Cardston,? and Ponoka is set by the applicable municipal government",
        text,
    ))
    return terms.pop(), links.pop(), municipal


def parse_rate_schedule(pages: list[DocumentPage]) -> dict[str, dict]:
    """Split the ENMAX Power-area rate schedule PDF into its named schedules."""
    if not pages:
        raise RolrError("ENMAX rate schedule has no readable pages")
    cover = normalize_text(pages[0].text)
    if "provider of Rate of Last Resort for ENMAX Power Corporation" not in cover or "City of Calgary" not in cover:
        raise RolrError("PDF is not the ENMAX Power service-area RoLR rate schedule")
    schedules: dict[str, dict] = {}
    for page in pages:
        text = normalize_text(page.text)
        head = _HEAD.search(text)
        if not head:
            continue
        if head.group(3) in schedules:
            raise RolrError(f"duplicate {head.group(3)} schedule")
        schedules[head.group(3)] = {
            "page": page.page_number, "text": text,
            "interim": bool(head.group(1)), "year": int(head.group(2)),
        }
    return schedules


def parse_schedule_charges(entry: dict, today: date) -> dict:
    """Read one schedule's charges; any missing, odd-unit or undated item fails closed."""
    text = entry["text"]
    energy = re.search(r"Energy Charge \$(\d+\.\d+) per (\S+)", text)
    admin = re.search(r"Administration Charge \$(\d+\.\d+) per (\S+)", text)
    rider = re.search(r"\bRider (n/a|\S+(?: per \S+)?)", text)
    footer = re.search(rf"Decision (\d{{5}}-D\d{{2}}-\d{{4}}), effective ({DATE_PATTERN})", text)
    applicability = re.search(r"Applicability (.+?) (?:Rate )?Energy Charge", text)
    if not (energy and admin and rider and footer and applicability):
        raise RolrError("energy, administration, rider, applicability or decision wording missing")
    if energy.group(2) != "kWh" or admin.group(2) != "day":
        raise RolrError(f"unexpected units: energy per {energy.group(2)}, administration per {admin.group(2)}")
    if rider.group(1).casefold() != "n/a":
        raise RolrError(f"rider {rider.group(1)!r} is printed without dates")
    effective = parse_date(footer.group(2))
    if effective > today:
        raise RolrError(f"schedule effective {effective.isoformat()} is in the future")
    if entry["year"] != today.year:
        raise RolrError(f"rate schedule is for {entry['year']}, not {today.year}")
    return {
        "energy": Decimal(energy.group(1)), "admin": Decimal(admin.group(1)),
        "energy_text": energy.group(0), "admin_text": admin.group(0),
        "decision": footer.group(1), "effective": effective, "effective_text": footer.group(2),
        "applicability": applicability.group(1).strip(),
    }


def parse_sources(sources: dict, today: date) -> tuple[list[TariffRecord], list[str]]:
    """Build live RoLR records; ``sources`` holds 'uca', 'page' (HTML) and 'schedule_pages'."""
    try:
        uca = parse_uca_table(sources.get("uca") or "", today)
        uca_cents = uca.price(UCA_RETAILER, UCA_DISTRIBUTOR)
        period, schedule_url, municipal = parse_enmax_page(sources.get("page") or "")
        if period != uca.period:
            raise RolrError(f"ENMAX term {period.label()} differs from UCA term {uca.period.label()}")
        require_current(period, today)
        schedules = parse_rate_schedule(sources.get("schedule_pages") or [])
    except RolrError as exc:
        return [], [f"all classes: {exc}"]
    check = uca_detail(uca, UCA_RETAILER, UCA_DISTRIBUTOR)

    records: list[TariffRecord] = []
    rejections: list[str] = []
    for kind, (schedule, name, code, customer_class, rate_code) in SCHEDULES.items():
        try:
            if schedule not in schedules:
                raise RolrError(f"{schedule} schedule missing from the rate schedule PDF")
            entry = schedules[schedule]
            charges = parse_schedule_charges(entry, today)
            if charges["energy"] * 100 != uca_cents:
                raise RolrError(f"rate schedule {charges['energy_text']} differs from UCA {uca_cents} cents/kWh")
            if f"{rate_code} service" not in charges["applicability"]:
                raise RolrError(f"applicability no longer names {rate_code} service")
            limit = re.search(r"less than (\d[\d,]*) MWh", charges["applicability"])
            if kind == "small_business" and not limit:
                raise RolrError("small commercial consumption limit missing")
        except RolrError as exc:
            rejections.append(f"{name}: {exc}")
            continue

        interim = entry["interim"]
        status = f"{'INTERIM ' if interim else ''}{entry['year']} Regulated Rate Tariff"
        pdf_detail = f"ENMAX Energy RoLR rate schedule ({status}), PDF page {entry['page']} ({schedule})"
        components = [
            energy_component(
                charges["energy"] * 100, period, source_url=schedule_url,
                source_detail=f"{pdf_detail}: '{charges['energy_text']}'; term from the ENMAX RoLR page ({ROLR_URL})",
                uca_check=check,
            ),
            RateComponent(
                component_type="fixed",
                component_name="RoLR Administration Charge",
                charge_value=float(charges["admin"]),
                charge_unit="$/day",
                effective_date=charges["effective"].isoformat(),
                source_url=schedule_url,
                source_detail=(
                    f"{pdf_detail}: '{charges['admin_text']}'; 'Decision {charges['decision']}, "
                    f"effective {charges['effective_text']}'"
                ),
                confidence="medium" if interim else "high",
                notes=(
                    f"Printed in ENMAX Energy's {status}; no end date is printed."
                    + (" Interim pending a final AUC decision." if interim else "")
                ),
            ),
        ]
        notes = [f"Rates from ENMAX Energy's {status} (rider: n/a)."]
        if kind == "small_business" and {"Medium Commercial", "Large Commercial"} & set(schedules):
            notes.append(
                "The rate schedule also has Medium Commercial (D300) and Large Commercial (D310/D410) "
                "RoLR schedules for sites under the same consumption limit; they are not modelled separately."
            )
        if municipal:
            notes.append(
                "ENMAX Energy also provides the RoLR in Red Deer, Cardston and Ponoka, where the "
                "municipality sets it; those areas are not covered here."
            )
        records.append(rolr_record(
            utility_name="ENMAX Energy Corporation",
            tariff_name=name,
            tariff_code=code,
            customer_class=customer_class,
            description=f"Rate of Last Resort default electricity supply ({schedule} schedule) in the City of Calgary.",
            eligibility=f"{charges['applicability']} Service area: {SERVICE_AREA}.",
            period=period,
            components=components,
            source_url=schedule_url,
            source_page=pdf_detail,
            notes=" ".join(notes),
            confidence="medium" if interim else "high",
            usage_max=float(limit.group(1).replace(",", "")) if limit else None,
            usage_unit="MWh/year" if limit else None,
        ))
    return records, rejections


class ENMAXEnergyScraper(BaseScraper):
    """Scrape ENMAX Energy Corporation RoLR rates for Calgary, Alberta."""

    def __init__(self):
        super().__init__(
            utility_name="ENMAX Energy Corporation",
            province="AB",
        )

    def scrape(self) -> list[TariffRecord]:
        records = []

        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning(
                "Live scrape failed -- using seed data for ENMAX Energy"
            )
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Parse the ENMAX RoLR page and rate schedule; the UCA table is a required cross-check."""
        try:
            sources = {
                "uca": self.fetch_page(UCA_DEFAULT_RATES_URL),
                "page": self.fetch_page(ROLR_URL),
            }
            _, schedule_url, _ = parse_enmax_page(sources["page"])
            sources["schedule_pages"] = self._pdf_pages(self.fetch_bytes(schedule_url))
        except Exception as exc:
            self.logger.warning("ENMAX RoLR sources unavailable: %s", exc)
            return None
        try:
            records, rejections = parse_sources(sources, self._today())
        except Exception:
            self.logger.exception("ENMAX RoLR parse failed")
            return None
        for reason in rejections:
            self.logger.warning("ENMAX RoLR rejected -- %s", reason)
        if not records:
            return None
        return self.mark_live_parsed(records)

    @staticmethod
    def _pdf_pages(data: bytes) -> list[DocumentPage]:
        return extract_pdf_pages(data)

    @staticmethod
    def _today() -> date:
        return date.today()

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # -- Residential RRO -----------------------------------------------
        records.append(TariffRecord(
            utility_name="ENMAX Energy Corporation",
            province="AB",
            utility_type="electricity",
            tariff_name="Residential Regulated Rate Option",
            tariff_code="RRO-Res",
            customer_class="residential",
            rate_structure="market",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "ENMAX Energy provides the Regulated Rate Option (RRO) "
                "for the ENMAX Power (Calgary) service area. The energy "
                "rate changes monthly based on the AESO pool price plus "
                "a regulated risk premium. Distribution charges from "
                "ENMAX Power are separate. Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="RRO Energy Charge",
                    charge_value=SEED_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    market_reference="AESO pool price",
                    market_source_url=AESO_MARKET_URL,
                    notes=(
                        "Regulated Rate Option energy charge -- varies "
                        "monthly based on AESO pool price"
                    ),
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Administration Fee",
                    charge_value=SEED_RESIDENTIAL["admin_fee_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly administration fee",
                ),
            ],
        ))

        # -- Commercial RRO ------------------------------------------------
        records.append(TariffRecord(
            utility_name="ENMAX Energy Corporation",
            province="AB",
            utility_type="electricity",
            tariff_name="Commercial Regulated Rate Option",
            tariff_code="RRO-Com",
            customer_class="commercial",
            rate_structure="market",
            effective_date=SEED_COMMERCIAL["effective_date"],
            source_url=SEED_COMMERCIAL["source_url"],
            confidence="medium",
            notes=(
                "ENMAX Energy commercial RRO for the Calgary service "
                "area. Same energy rate structure as residential -- "
                "varies monthly with AESO pool price. Distribution "
                "charges from ENMAX Power are separate. "
                "Regulated by the AUC."
            ),
            components=[
                RateComponent(
                    component_type="energy",
                    component_name="RRO Energy Charge",
                    charge_value=SEED_COMMERCIAL["energy_rate"],
                    charge_unit="$/kWh",
                    confidence="medium",
                    market_reference="AESO pool price",
                    market_source_url=AESO_MARKET_URL,
                    notes=(
                        "Regulated Rate Option energy charge -- varies "
                        "monthly based on AESO pool price"
                    ),
                ),
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Administration Fee",
                    charge_value=SEED_COMMERCIAL["admin_fee_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly administration fee",
                ),
            ],
        ))

        return records
