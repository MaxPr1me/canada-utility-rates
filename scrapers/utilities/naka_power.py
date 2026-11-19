"""
naka_power.py — Scraper for Naka Power Utilities (NWT) Ltd. (Northwest Territories).

Naka Power (formerly Northland Utilities (NWT) and Naka Power Utilities (Yellowknife), amalgamated on
January 1, 2026) serves Yellowknife (Snare Zone), Enterprise, K'atl'odeeche First Nation and Riverwoods
(Taltson Zone) and the diesel-served communities Fort Providence, Sambaa K'e, Wekweti and Dory Point/Kakisa
(Thermal Zone). Hay River moved to NTPC on March 1, 2025.

Official source: the NWT Public Utilities Board-approved Rate Schedule PDF linked from
https://www.nakapower.com/en-ca/customer-billing-rates/rates-regulations.html as "Rate Schedule (effective
<date>)", once per zone tab; both links must name the same document and date, and that date must equal the
newest date printed in the schedule. The schedule prints each class's base rates (dated 2012 or 2016) and the
riders as dated zone tables. Every component keeps its own date; a record takes its latest component's date.

- Base rows must add up to each printed Total, column by column. The Thermal Zone General Service schedule has
  printed a $14.00/kW demand charge with a $10.00/kW total since at least January 2026, so it fails closed.
- Riders: every rider a class lists is looked up in its zone's table. Cents-per-kWh riders are stored per kWh
  (credits as rebates, as for NL Hydro); percentage riders and the Snare Zone franchise tax are stored as
  percentages of the revenue the schedule names, never converted to per-unit prices. Riders printed at zero or
  without a rate are named in the notes only.
- Confidence: Naka's rate-update notice linked from the same page says whether the edition's rider changes
  are interim. The July 1, 2026 changes are "interim refundable rates" pending the 2026-2028 GRA, so records are
  medium confidence; when the notice is missing or names another date, they stay medium with a note.
- GNWT programs for non-government customers are conditional alternatives, never folded into the base price
  (as for NTPC): the Territorial Power Subsidy Program first-block price (Taltson and Thermal residential) and
  the GNWT Rate Equalization Program reference rates (Thermal Zone). The Cost of Living Subsidy publishes no
  value and is not stored.

Scope: residential and general service in each zone, plus Taltson Large General Service. Excluded: street and
sentinel lighting, Taltson interruptible service (priced case by case under contract) and the Hay River
transmission wheeling charge (a wholesale charge to NTPC). No seed fallback: a failed source returns no
records. No last-known copy either: riders change several times a year, so a stale copy would misstate prices.
Territories are not modelled yet.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import urljoin

from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

UTILITY = "Naka Power Utilities (NWT)"
RATES_PAGE_URL = "https://www.nakapower.com/en-ca/customer-billing-rates/rates-regulations.html"

ZONES = ("Snare", "Taltson", "Thermal")
ZONE_LABELS = {"Snare": "Snare Zone (Yellowknife)", "Taltson": "Taltson Zone", "Thermal": "Thermal Zone"}
# (zone, printed schedule heading): (code, name, customer class, rate structure)
CLASSES = {
    ("Snare", "RESIDENTIAL RATE SCHEDULE"): ("SNARE-RES", "Residential Service", "residential", "flat"),
    ("Snare", "GENERAL SERVICE (COMMERCIAL) RATE SCHEDULE"): ("SNARE-GS", "General Service (Commercial)",
                                                              "commercial", "demand"),
    ("Taltson", "RESIDENTIAL SERVICE RATE SCHEDULE"): ("TALTSON-RES", "Residential Service", "residential", "flat"),
    ("Taltson", "GENERAL SERVICE RATE SCHEDULE"): ("TALTSON-GS", "General Service", "commercial", "demand"),
    ("Taltson", "LARGE GENERAL SERVICE RATE SCHEDULE"): ("TALTSON-LGS", "Large General Service", "commercial",
                                                         "demand"),
    ("Thermal", "RESIDENTIAL SERVICE RATE SCHEDULE"): ("THERMAL-RES", "Residential Service", "residential", "flat"),
    ("Thermal", "GENERAL SERVICE RATE SCHEDULE"): ("THERMAL-GS", "General Service", "commercial", "demand"),
}
EXCLUDED_HEADINGS = ("LIGHT", "INTERRUPTIBLE")
RIDER_TITLES = {
    "A": "Fuel Cost Adjustment", "E": "Temporary Refund/Surcharge", "F": "Purchase Power Cost Adjustment",
    "G": "Global Adjustment Rate Rider", "H": "Cost Recovery/Refund", "J": "Transitional Rate Reduction/Surcharge",
    "K": "Interim Refundable Rate", "R": "Revenue Adjustment", "T": "25 kV Deferral Account",
    "FRANCHISE": "Franchise Tax",
}
# What each percentage rider adjusts, in the schedule's words.
PERCENT_BASIS = {
    "E": "the company's base rate revenue", "H": "the company's base rate revenue",
    "R": "base rates (excluding fuel and purchase power)", "T": "the company's base rate revenue",
    "FRANCHISE": "revenues billed under the Company's rate schedules",
}
SEASON_MONTHS = {"September 1 to March 31": "9,10,11,12,1,2,3", "April 1 to August 31": "4,5,6,7,8"}

_LONG_DATE = r"[A-Z][a-z]+ \d{1,2}, \d{4}"
_HEADER_DATE = re.compile(r"Effective Date:\s*(" + _LONG_DATE + ")")
_CLASS_HEAD = re.compile(r"^(SNARE|TALTSON|THERMAL) ZONE\s*\n\s*([A-Z][A-Z ()]*RATE SCHEDULE)\s*$", re.M)
_ROW = re.compile(r"(Customer Charge|Demand Charge|Energy Charge|Supply Charge|Fuel Charge|Total)\s+(?=\$|-|\d)")
_CELL = re.compile(r"\$\s?(?P<money>\d+(?:\.\d+)?)\s*/\s*(?P<unit>kV\.a\s*/\s*month|kW\s*/\s*month|kW|month)"
                   r"|(?P<cents>\d+(?:\.\d+)?)\s*¢\s*/\s*kW\.h|(?P<dash>(?<![\w.])-(?![\w.]))")
_RIDER_ROW = re.compile(r"\b(Snare|Taltson|Thermal) Zone\s+(?P<value>-?\d+(?:\.\d+)?\s*(?:%|¢\s*/\s*kW\.h)|-)\s+"
                        r"(?P<date>\d{4}-\d{2}-\d{2}|N/A)\s+(?P<decision>\d{2}-\d{4}|N/A)")
_SCHEDULE_LINK = re.compile(r"^Rate Schedule \(effective (" + _LONG_DATE + r")\)$")


def _iso(text: str) -> str:
    return datetime.strptime(text, "%B %d, %Y").date().isoformat()


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split())


def find_schedule(html: str, base_url: str = RATES_PAGE_URL) -> tuple[str, str]:
    """(PDF URL, ISO date) of the "Rate Schedule (effective <date>)" links; every zone tab must agree."""
    found = set()
    for anchor in parse_html(html or "").find_all("a", href=True):
        label = _SCHEDULE_LINK.match(_text(anchor))
        if label and anchor["href"].lower().split("?")[0].endswith(".pdf"):
            found.add((urljoin(base_url, anchor["href"]), _iso(label.group(1))))
    if not found:
        raise ValueError("rates page links no 'Rate Schedule (effective <date>)' PDF")
    if len(found) > 1:
        raise ValueError(f"rates page links different current schedules: {sorted(found)}")
    return found.pop()


def find_rate_update_url(html: str, base_url: str = RATES_PAGE_URL) -> Optional[str]:
    for anchor in parse_html(html or "").find_all("a", href=True):
        if re.fullmatch(r"\d{4} Rate Updates", _text(anchor)):
            return urljoin(base_url, anchor["href"])
    return None


def parse_rate_update(html: str) -> tuple[str, bool]:
    """(ISO effective date, whether it calls the changes interim) of Naka's rate-update notice."""
    text = _text(parse_html(html or ""))
    heading = re.search(r"Electricity Rate Updates\s*[–-]\s*Effective (" + _LONG_DATE + ")", text)
    if not heading:
        raise ValueError("rate-update notice has no 'Electricity Rate Updates – Effective <date>' heading")
    return _iso(heading.group(1)), bool(re.search(r"\binterim\b", text, re.I))


def _rider_tables(pages: list[DocumentPage]) -> dict[str, dict[str, dict]]:
    """{rider: {zone: {value, unit, date, decision}}}; a table without exactly one row per zone is left out."""
    tables: dict[str, dict[str, dict]] = {}
    for page in pages:
        if "Zone Rate Effective Date" not in page.text:
            continue
        if re.search(r"^FRANCHISE TAX\s*$", page.text, re.M):
            rider = "FRANCHISE"
        else:
            head = re.search(r"^RIDER ([A-Z])\b", page.text, re.M)
            if not head:
                continue
            rider = head.group(1)
        rows: dict[str, list[dict]] = {}
        for row in _RIDER_ROW.finditer(page.text):
            raw = row.group("value")
            value = unit = None
            if raw != "-":
                number = float(re.match(r"-?\d+(?:\.\d+)?", raw).group(0))
                value, unit = (number, "%") if raw.endswith("%") else (number, "¢/kWh")
            rows.setdefault(row.group(1), []).append({
                "value": value, "unit": unit, "page": page.page_number,
                "date": None if row.group("date") == "N/A" else row.group("date"),
                "decision": None if row.group("decision") == "N/A" else row.group("decision")})
        if set(rows) == set(ZONES) and all(len(found) == 1 for found in rows.values()) and rider not in tables:
            tables[rider] = {zone: found[0] for zone, found in rows.items()}
    return tables


def _sections(pages: list[DocumentPage]) -> list[dict]:
    """Class schedules in page order; each reads only its own text, up to the next heading or the riders."""
    sections: list[dict] = []
    current = None
    for page in pages:
        if "RIDERS AND SUBSIDIES" in page.text or "Zone Rate Effective Date" in page.text:
            current = None
            continue
        heads = list(_CLASS_HEAD.finditer(page.text))
        header = _HEADER_DATE.search(page.text)
        if not heads:
            if current is not None and header:
                current["text"] += "\n" + page.text
            continue
        for index, head in enumerate(heads):
            end = heads[index + 1].start() if index + 1 < len(heads) else len(page.text)
            current = {"zone": head.group(1).title(), "heading": " ".join(head.group(2).split()),
                       "page": page.page_number, "date": _iso(header.group(1)) if header else None,
                       "text": page.text[head.start():end]}
            sections.append(current)
    return sections


def _communities(pages: list[DocumentPage]) -> dict[str, list[str]]:
    """Communities by zone from the schedule's cover table (descriptive only)."""
    if not pages or "Zone Applicable Community/Communities" not in pages[0].text:
        return {}
    body = pages[0].text.split("Zone Applicable Community/Communities", 1)[1].split("Refer to the Index", 1)[0]
    found: dict[str, list[str]] = {}
    zone = None
    for line in (line.strip() for line in body.splitlines()):
        start = re.match(r"(Snare|Taltson|Thermal) Zone(?: \([^)]*\))?\s*(.*)", line)
        if start:
            zone, line = start.group(1), start.group(2)
        if zone and line:
            found.setdefault(zone, []).append(line)
    return found


def _table(text: str) -> dict[str, dict]:
    """Rows of a class's rate table: {label: {"money": [(value, unit)], "cents": [value]}}."""
    rows: dict[str, dict] = {}
    for match in _ROW.finditer(text):
        line = text[match.end():].split("\n", 1)[0]
        cells = {"money": [], "cents": []}
        for cell in _CELL.finditer(line):
            if cell.group("money"):
                cells["money"].append((float(cell.group("money")), " ".join(cell.group("unit").split())))
            elif cell.group("cents"):
                cells["cents"].append(float(cell.group("cents")))
        if match.group(1) in rows:
            raise ValueError(f"duplicate {match.group(1)} row")
        rows[match.group(1)] = cells
    return rows


def _between(text: str, start: str, ends: tuple[str, ...]) -> str:
    if start not in text:
        return ""
    tail = text.split(start, 1)[1]
    cut = min([tail.index(end) for end in ends if end in tail] or [len(tail)])
    return " ".join(tail[:cut].replace("•", " ").split())


def _base_components(section: dict) -> tuple[list[RateComponent], list[str]]:
    """Base components of one class, reconciled with its printed Total row; ValueError fails the class."""
    rows = _table(section["text"])
    total = rows.get("Total")
    fixed_label = "Customer Charge" if "Customer Charge" in rows else "Demand Charge"
    energy_labels = [label for label in ("Energy Charge", "Supply Charge", "Fuel Charge") if label in rows]
    if total is None or fixed_label not in rows or not energy_labels:
        raise ValueError("rate table rows not found")
    fixed = rows[fixed_label]
    columns = len(total["cents"])
    if (len(fixed["money"]) != 1 or fixed["cents"] or len(total["money"]) != 1 or columns not in (1, 2)
            or any(rows[label]["money"] or len(rows[label]["cents"]) != columns for label in energy_labels)):
        raise ValueError("rate table columns do not line up")
    (value, unit), (total_value, total_unit) = fixed["money"][0], total["money"][0]
    if unit != total_unit or abs(value - total_value) > 0.005:
        raise ValueError(f"{fixed_label} ${value:.2f} / {unit} does not equal the printed total "
                         f"${total_value:.2f} / {total_unit}")
    for column in range(columns):
        added = sum(rows[label]["cents"][column] for label in energy_labels)
        if abs(added - total["cents"][column]) > 0.005:
            raise ValueError(f"energy rows add to {added:.2f} cents/kWh, not the printed total "
                             f"{total['cents'][column]:.2f}")
    notes: list[str] = []
    when = section["date"]
    components: list[RateComponent] = []
    if fixed_label == "Customer Charge":
        if unit != "month":
            raise ValueError(f"customer charge unit {unit!r} is not per month")
        components.append(RateComponent(component_type="fixed", component_name="Customer Charge",
                                        charge_value=value, charge_unit="$/month", effective_date=when))
    else:
        kva = unit.startswith("kV.a")
        billing = _between(section["text"], "Billing Demand", ("Deficient Power Factor", "Options and Riders",
                                                                "Special arrangements"))
        components.append(RateComponent(
            component_type="demand", component_name="Demand Charge", charge_value=value,
            charge_unit="$/kVA/month" if kva else "$/kW/month", demand_unit="kVA" if kva else "kW",
            effective_date=when, notes=f"Billing Demand {billing}".strip() if billing else None))
    if columns == 1:
        for label in energy_labels:
            components.append(RateComponent(component_type="energy", component_name=label,
                                            charge_value=round(rows[label]["cents"][0] / 100, 6),
                                            charge_unit="$/kWh", effective_date=when))
        return components, notes
    blocks = re.search(r"For the first (\d+) kWh In excess of (\d+) kWh\s*per kW of billing", section["text"])
    if not blocks or blocks.group(1) != blocks.group(2):
        raise ValueError("energy block threshold per kW of billing demand not found")
    threshold = float(blocks.group(1))
    for label in energy_labels:
        for tier, part in ((1, f"First {threshold:g} kWh/kW"), (2, "Balance")):
            components.append(RateComponent(
                component_type="energy", component_name=f"{label} — {part}",
                charge_value=round(rows[label]["cents"][tier - 1] / 100, 6), charge_unit="$/kWh",
                tier_number=tier, tier_threshold=threshold, tier_unit="kWh/kW of billing demand/month",
                effective_date=when))
    notes.append(f"Energy blocks: the first {threshold:g} kWh per kW of billing demand per month, then the balance.")
    return components, notes


def _rider_components(section: dict, riders: dict, today: date) -> tuple[list[RateComponent], list[str]]:
    """Components for every rider the class lists; ValueError fails the class."""
    listed = sorted(set(re.findall(r"\(Rider ([A-Z])\)", section["text"])))
    if "Franchise Tax" in section["text"]:
        listed.append("FRANCHISE")
    components: list[RateComponent] = []
    inactive: list[str] = []
    for rider in listed:
        title = RIDER_TITLES.get(rider, f"Rider {rider}")
        label = title if rider == "FRANCHISE" else f"{title} (Rider {rider})"
        row = riders.get(rider, {}).get(section["zone"])
        if row is None:
            raise ValueError(f"{label} is listed but its zone table was not found")
        if not row["value"]:
            shown = "no rate" if row["value"] is None else (
                f"{row['value']:g}%" if row["unit"] == "%" else f"{row['value']:g} cents/kWh")
            inactive.append(f"{label}: {shown}" + (f" (since {row['date']})" if row["date"] else ""))
            continue
        if row["date"] is None:
            raise ValueError(f"{label} has a rate but no effective date")
        if date.fromisoformat(row["date"]) > today:
            raise ValueError(f"{label} takes effect {row['date']}, after {today.isoformat()}")
        decision = f"PUB Decision {row['decision']}. " if row["decision"] else ""
        kind = "rebate" if row["value"] < 0 else "rider"
        if row["unit"] == "%":
            components.append(RateComponent(
                component_type=kind, component_name=label, charge_value=row["value"], charge_unit="%",
                effective_date=row["date"],
                notes=f"{decision}Percentage adjustment of {PERCENT_BASIS.get(rider, 'base rate revenue')}; "
                      "not a per-unit price."))
        else:
            components.append(RateComponent(
                component_type=kind, component_name=label, charge_value=round(row["value"] / 100, 6),
                charge_unit="$/kWh", effective_date=row["date"], notes=f"{decision}Applies to all energy."))
    notes = ["Riders listed for this schedule but not in effect: " + "; ".join(inactive) + "."] if inactive else []
    return components, notes


def _program(pages: list[DocumentPage], title: str) -> Optional[DocumentPage]:
    """The page whose own heading line is the program title (the contents pages list it with dot leaders)."""
    heading = re.compile(r"^" + re.escape(title) + r"\s*$", re.M)
    return next((page for page in pages if heading.search(page.text)), None)


def _subsidies(code: str, pages: list[DocumentPage]) -> tuple[list[RateComponent], list[str]]:
    """Conditional GNWT alternatives for non-government customers (TPSP and GREP), or notes when not stored."""
    components: list[RateComponent] = []
    notes: list[str] = []
    residential = code.endswith("-RES")
    if residential and not code.startswith("SNARE"):
        page = _program(pages, "TERRITORIAL POWER SUBSIDY PROGRAM (TPSP)")
        header = page and _HEADER_DATE.search(page.text)
        text = " ".join(page.text.split()) if page else ""
        blocks = re.search(r"limited to ([\d,]+) kW\.h per month during September to March and ([\d,]+) kW\.h per "
                           r"month during April to August", text)
        rate = re.search(r"reference rate of (\d+(?:\.\d+)?)\s*¢\s*/\s*kW\.h", text)
        if not (header and blocks and rate and "excluding Snare Zone" in text
                and "non-government Residential Service customers" in text):
            notes.append("GNWT Territorial Power Subsidy Program price not stored: its schedule page was not "
                         "found in the expected form.")
        else:
            for season, kwh in (("September 1 to March 31", blocks.group(1)), ("April 1 to August 31", blocks.group(2))):
                kwh_value = float(kwh.replace(",", ""))
                components.append(RateComponent(
                    component_type="energy", component_name=f"GNWT TPSP First-Block Energy Price ({season})",
                    charge_value=round(float(rate.group(1)) / 100, 6), charge_unit="$/kWh", tier_number=1,
                    tier_threshold=kwh_value, tier_unit="kWh", season=season, season_months=SEASON_MONTHS[season],
                    effective_date=_iso(header.group(1)), source_detail=f"Rate Schedule PDF page {page.page_number}",
                    notes=(f"Conditional alternative, not an additional charge: for non-government residential "
                           f"customers the first {kwh_value:,.0f} kWh per month ({season}, pro-rated on a 30-day "
                           f"charge period) get the Territorial Support rate, based on the Snare Zone (Yellowknife) "
                           f"reference rate of {rate.group(1)} cents/kWh.")))
    if code.startswith("THERMAL"):
        page = _program(pages, "GNWT RATE EQUALIZATION PROGRAM (GREP)")
        header = page and _HEADER_DATE.search(page.text)
        text = " ".join(page.text.split()) if page else ""
        fixed = re.search(r"Customer / Demand \$(\d+(?:\.\d+)?) / month \$(\d+(?:\.\d+)?) / kW / month", text)
        energy = re.search(r"Energy (\d+(?:\.\d+)?) ¢ / kWh (\d+(?:\.\d+)?) ¢ / kWh", text)
        if not (header and fixed and energy and "non-government residential and general service customers in the "
                                                "Thermal Rate Zone" in text):
            notes.append("GNWT Rate Equalization Program reference rates not stored: their schedule page was not "
                         "found in the expected form.")
        else:
            column = 1 if residential else 2
            detail = f"Rate Schedule PDF page {page.page_number}"
            note = ("Conditional alternative, not an additional charge: GNWT Rate Equalization Program reference "
                    "rate for non-government customers in the Thermal Zone (the sum of NTPC Thermal Zone "
                    "non-government rates and riders); the program aligns their charges with these rates.")
            components.append(RateComponent(
                component_type="fixed" if residential else "demand",
                component_name="GNWT GREP Reference Customer Charge" if residential else
                "GNWT GREP Reference Demand Charge",
                charge_value=float(fixed.group(column)), charge_unit="$/month" if residential else "$/kW/month",
                demand_unit=None if residential else "kW", effective_date=_iso(header.group(1)),
                source_detail=detail, notes=note))
            components.append(RateComponent(
                component_type="energy", component_name="GNWT GREP Reference Energy Price",
                charge_value=round(float(energy.group(column)) / 100, 6), charge_unit="$/kWh",
                effective_date=_iso(header.group(1)), source_detail=detail, notes=note))
    return components, notes


def parse_schedule(pages: list[DocumentPage], source_url: str, today: Optional[date] = None,
                   label_date: Optional[str] = None,
                   update: Optional[tuple[str, bool]] = None) -> tuple[list[TariffRecord], dict[str, str]]:
    """Build the in-scope records; return (records, {code: rejection reason}).

    ValueError (the whole schedule fails closed): the link's date differs from the schedule's newest date, or
    the schedule takes effect after today. A class whose table, totals or riders do not check out is rejected
    on its own and reported in the returned reasons.
    """
    today = today or date.today()
    dates = [_iso(found) for page in pages for found in _HEADER_DATE.findall(page.text)]
    riders = _rider_tables(pages)
    dates += [row["date"] for table in riders.values() for row in table.values() if row["date"]]
    if not dates or not riders:
        raise ValueError("schedule dates or rider tables not found")
    edition = max(dates)
    if label_date and label_date != edition:
        raise ValueError(f"the rates page says effective {label_date}, but the schedule's newest date is {edition}")
    if date.fromisoformat(edition) > today:
        raise ValueError(f"schedule takes effect {edition}, after {today.isoformat()}")
    if update and update[0] == edition:
        interim: Optional[bool] = update[1]
    else:
        interim = None
    confidence = "high" if interim is False else "medium"
    if interim:
        status = (f"Interim: Naka's rate-update notice for {edition} calls these rider changes interim refundable "
                  "rates approved by the Public Utilities Board pending its final decision (medium confidence).")
    elif interim is None:
        status = ("Medium confidence: Naka's rate-update notice for this edition was not found, so whether its "
                  "rider changes are interim was not confirmed.")
    else:
        status = ""
    communities = _communities(pages)
    rejections: dict[str, str] = {}
    records: list[TariffRecord] = []
    seen = set()
    for section in _sections(pages):
        key = (section["zone"], section["heading"])
        if key not in CLASSES:
            if not any(word in section["heading"] for word in EXCLUDED_HEADINGS):
                rejections[f"{section['zone'].upper()}:{section['heading']}"] = "unrecognised class (not stored)"
            continue
        code, name, customer_class, structure = CLASSES[key]
        if code in seen:
            rejections[code] = "duplicate schedule section"
            records = [record for record in records if record.tariff_code != code]
            continue
        seen.add(code)
        try:
            if not section["date"]:
                raise ValueError("schedule page has no effective date")
            base, base_notes = _base_components(section)
            rider_parts, rider_notes = _rider_components(section, riders, today)
        except ValueError as exc:
            rejections[code] = str(exc)
            continue
        subsidies, subsidy_notes = _subsidies(code, pages)
        detail = f"Rate Schedule (edition effective {edition}), PDF page {section['page']}"
        for component in base + rider_parts:
            component.source_detail = component.source_detail or detail
        for component in rider_parts:
            component.confidence = confidence
        components = base + rider_parts + subsidies
        zone = section["zone"]
        places = communities.get(zone, [])
        application = _between(section["text"], "Application", ("\nRates",))
        notes = [f"NWT Public Utilities Board-approved Naka Power Utilities (NWT) rate schedule (edition effective "
                 f"{edition}), {ZONE_LABELS[zone]}" + (f": {', '.join(places)}." if places else "."),
                 f"Base rates effective {section['date']}; each rider keeps its own date.", status, *base_notes,
                 *rider_notes]
        if "minimum monthly charge is the Customer Charge" in " ".join(section["text"].split()):
            notes.append("The minimum monthly charge is the Customer Charge (a floor, not an additional charge).")
        special = re.search(r"Special arrangements must be made for supply to loads over [\d,]+ kW in this area\.",
                            " ".join(section["text"].split()))
        if special:
            notes.append(special.group(0))
        if any("%" == (c.charge_unit or "") for c in rider_parts):
            notes.append("Percentage riders adjust the revenue the schedule names; they are stored as percentages.")
        if subsidies:
            notes.append("Government accounts pay the same base rates and riders; the GNWT program prices are "
                         "conditional alternatives for non-government customers only.")
        notes.extend(subsidy_notes)
        records.append(TariffRecord(
            utility_name=UTILITY, province="NT", utility_type="electricity",
            tariff_name=f"{name} — {ZONE_LABELS[zone]}", tariff_code=code, customer_class=customer_class,
            sub_class=f"{zone.lower()} zone", eligibility=application or None, rate_structure=structure,
            pricing_method="regulated", effective_date=max(c.effective_date for c in components),
            source_url=source_url, source_page=detail, confidence=confidence,
            notes=" ".join(note for note in notes if note), components=components))
    for key, (code, *_rest) in CLASSES.items():
        if code not in seen:
            rejections[code] = f"{key[0]} Zone {key[1].title()} section not found"
    return records, rejections


class NakaPowerScraper(BaseScraper):
    """Parse Naka Power Utilities (NWT)'s PUB-approved rate schedule."""

    def __init__(self) -> None:
        super().__init__(utility_name=UTILITY, province="NT")

    def scrape(self) -> list[TariffRecord]:
        # No seed fallback for batch 18 utilities (owner confirmed 2026-11-17).
        records = self._try_live_scrape()
        if not records:
            self.logger.warning("Naka Power: no live records (no seed fallback)")
        return records

    def _try_live_scrape(self) -> list[TariffRecord]:
        try:
            html = self.fetch_page(RATES_PAGE_URL)
            url, label_date = find_schedule(html)
        except Exception as exc:
            self.logger.warning("Naka Power rates page gave no usable schedule link: %s", exc)
            return []
        update = None
        update_url = find_rate_update_url(html)
        if update_url:
            try:
                update = parse_rate_update(self.fetch_page(update_url))
            except Exception as exc:
                self.logger.warning("Naka Power rate-update notice unreadable (%s): %s", update_url, exc)
        try:
            pages = extract_pdf_pages(self.fetch_bytes(url), drop_repeated_lines=False)
            records, rejections = parse_schedule(pages, url, label_date=label_date, update=update)
        except Exception as exc:
            self.logger.warning("Naka Power rate schedule failed closed: %s", exc)
            return []
        for code, reason in rejections.items():
            self.logger.warning("Naka Power %s rejected: %s", code, reason)
        return self.mark_live_parsed(records)
