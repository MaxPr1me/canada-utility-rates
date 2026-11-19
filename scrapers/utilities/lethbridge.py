"""
lethbridge.py — Scraper for the City of Lethbridge Electric Utility (Alberta).

Lethbridge owns its distribution system (a wire services provider under the Electric Utilities Act) and publishes
the Rate of Last Resort price for its area itself, so one scraper emits both: distribution tariff (wires) records
per rate code and the City's Rate of Last Resort records. The representative models pair them as one unit
(owner decision 2026-11-04: municipal wires with the city-published default energy rate).

Official sources:
- Electric Distribution Tariff Bylaw 6364 (the City's consolidation, linked from
  https://www.lethbridge.ca/utilities/electric/ as "Bylaw <n> Electric Distribution Tariff"): per rate code, the
  transmission and distribution access charges, eligibility, the on-peak hours and the ratchet rule.
- The 2026 Rate Table (linked from https://www.lethbridge.ca/utilities/utility-rates/ as "<year> Rate Table"):
  every bylaw value must equal the table's value for its rate code and row, read by column position. The two
  documents must name the same rate year.
- The Utility Rates page: the current year's Rate of Last Resort price and the dated City riders. Rider A (the
  15.50% Local Access Fee) stays a note, as for Alberta's other municipal access fees; Riders B (Balancing Pool)
  and C (AESO DTS) are dated per-kWh charges and must match the page's rider table. The page also lists an
  undefined "RDS" price, which is not stored.

Scope: rate codes 991, 992, 994, 995, 996 and 997. Excluded: public lighting (998), unmetered service (999) and
distributed generation (1000). No seed fallback: a failed source returns no records; when a page links no
document, the last known copy is read with a note.
"""

from __future__ import annotations

import io
import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import urljoin

from scrapers.base import BaseScraper, RateComponent, TariffRecord
from scrapers.utils.parsing import DocumentPage, extract_pdf_pages, parse_html

UTILITY = "City of Lethbridge Electric Utility"
RATES_PAGE_URL = "https://www.lethbridge.ca/utilities/utility-rates/"
ELECTRIC_PAGE_URL = "https://www.lethbridge.ca/utilities/electric/"
LAST_KNOWN_BYLAW_URL = ("https://media-001-ca.cdn.govstack.com/lethbridge-001-ca/media/pckj4114/"
                        "bylaw-6364-2025-12-08-consolidated.pdf")
LAST_KNOWN_RATE_TABLE_URL = ("https://media-001-ca.cdn.govstack.com/lethbridge-001-ca/media/f5fhdlhv/"
                             "2026-rate-table-final.pdf")

# rate code: (customer class, rate structure)
CODES = {"991": ("residential", "flat"), "992": ("commercial", "demand"), "994": ("commercial", "demand"),
         "995": ("commercial", "demand"), "996": ("commercial", "demand"), "997": ("commercial", "demand")}
# (access, bylaw charge) -> rate table row
TABLE_ROWS = {
    ("transmission", "System Usage Charge"): "TRAN Sys Usage",
    ("transmission", "Off-Peak System Usage Charge"): "TRAN Sys Usage",
    ("transmission", "On-Peak System Usage Charge"): "TRAN On Peak Sys Usage",
    ("transmission", "Service and Facilities Charge"): "TRAN Facilities Chg",
    ("transmission", "Demand Charge"): "TRAN Dmd Chrgs",
    ("distribution", "System Usage Charge"): "DIST Sys Usage Chrgs",
    ("distribution", "Service and Facilities Charge"): "DIST Facilities Chrgs",
    ("distribution", "Demand Charge"): "DIST Dmd Chrgs",
}
UNITS = {"kWh": "$/kWh", "day": "$/day", "kVA per day": "$/kVA/day"}

_LONG_DATE = r"[A-Z][a-z]+ \d{1,2}, \d{4}"
_SECTION = re.compile(r"^Rate Code (\d{3,4}): ([^.\n]+?)\s*$", re.M)
_CHARGE = re.compile(r"(?:^|\s)[a-c]\)\s*(On-Peak System Usage Charge|Off-Peak System Usage Charge|System Usage Charge|"
                     r"Service and Facilities Charge|Demand Charge)\s+(\d+\.\d+)\s+\$\s+per\s+(kWh|day|kVA per day)"
                     r"(?=\s|$)")


def _iso(text: str) -> str:
    return datetime.strptime(text, "%B %d, %Y").date().isoformat()


def _flat(node) -> str:
    return " ".join(node.get_text(" ", strip=True).replace("\u200b", "").split())


def find_link(html: str, pattern: str, base_url: str) -> Optional[tuple[str, str]]:
    """(URL, link text) of the first PDF link whose text fully matches ``pattern``."""
    for anchor in parse_html(html or "").find_all("a", href=True):
        text = _flat(anchor)
        if re.fullmatch(pattern, text) and anchor["href"].lower().split("?")[0].endswith(".pdf"):
            return urljoin(base_url, anchor["href"]), text
    return None


def rate_table_words(pdf_bytes: bytes) -> list[dict]:
    """Words of the rate table's first page with their positions (text, x0, x1, top)."""
    import pdfplumber

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return [{key: word[key] for key in ("text", "x0", "x1", "top")}
                for word in pdf.pages[0].extract_words(x_tolerance=2, y_tolerance=3)]


def parse_rate_table(words: list[dict]) -> tuple[int, dict[tuple[str, str], float]]:
    """(rate year, {(row label, rate code): value}) from positioned words; ValueError when the layout changed."""
    centre = lambda word: (word["x0"] + word["x1"]) / 2  # noqa: E731
    title = sorted((w for w in words if w["top"] < 60), key=lambda w: w["x0"])
    year = next((int(w["text"]) for w in title if re.fullmatch(r"20\d\d", w["text"])), None)
    headers = [(w["text"], centre(w)) for w in title if re.fullmatch(r"\d{3,4}", w["text"]) and w["x0"] > 200]
    if year is None or [code for code, _ in headers][:6] != list(CODES):
        raise ValueError("rate table header (year and rate codes 991-997) not found")
    lines: dict[float, list[dict]] = {}
    for word in sorted((w for w in words if w["x0"] < 200 and w["top"] >= 60), key=lambda w: (w["top"], w["x0"])):
        top = next((key for key in lines if abs(key - word["top"]) <= 3), word["top"])
        lines.setdefault(top, []).append(word)
    labels = {top: re.sub(r"\s*\(\$/[^)]*\)$", "", " ".join(w["text"] for w in line)) for top, line in lines.items()}
    values: dict[tuple[str, str], float] = {}
    for word in words:
        if word["x0"] < 200 or not re.fullmatch(r"\d+\.\d{4}", word["text"]):
            continue
        top = min(labels, key=lambda key: abs(key - word["top"]), default=None)
        code, x = min(headers, key=lambda header: abs(header[1] - centre(word)))
        if top is None or abs(top - word["top"]) > 8 or abs(x - centre(word)) > 25:
            raise ValueError(f"rate table value {word['text']} is not under a row label and rate code")
        key = (labels[top], code)
        if key in values:
            raise ValueError(f"two values for {key}")
        values[key] = float(word["text"])
    return year, values


def parse_bylaw(pages: list[DocumentPage]) -> dict:
    """Rate year, effective date, on-peak hours and the in-scope rate code sections of the consolidated bylaw."""
    text = "\n".join(page.text for page in pages)
    flat = " ".join(text.split())
    effective = re.search(r"Effective Date: (" + _LONG_DATE + ")", flat)
    year = re.search(r"\b2\. The (20\d\d) Electric Distribution Rates are contained", flat)
    peak = re.search(r"On-Peak Usage Means System Usage between the (\d{2}:\d{2}) hours and (\d{2}:\d{2}) hours, "
                     r"every day of the week", flat)
    ratchet = re.search(r"\bRatchet Means the highest demand in the last 12 months", flat)
    if not (effective and year and peak and ratchet):
        raise ValueError("bylaw effective date, rate year, on-peak hours or ratchet definition not found")
    heads = list(_SECTION.finditer(text))
    codes: dict[str, dict] = {}
    for index, head in enumerate(heads):
        code = head.group(1)
        if code not in CODES:
            continue
        if code in codes:
            raise ValueError(f"rate code {code} printed twice")
        body = text[head.end():heads[index + 1].start() if index + 1 < len(heads) else len(text)]
        page = next((p.page_number for p in pages if head.group(0) in p.text), None)
        if "Distribution Access Rate" not in body or "Transmission Access Rate" not in body:
            codes[code] = {"error": "transmission or distribution access rate block not found"}
            continue
        service, rest = body.split("Transmission Access Rate", 1)
        transmission, distribution = rest.split("Distribution Access Rate", 1)
        charges: dict[tuple[str, str], tuple[float, str]] = {}
        for access, block in (("transmission", transmission), ("distribution", distribution)):
            for found in _CHARGE.finditer(block):
                key = (access, found.group(1))
                if key in charges:
                    codes[code] = {"error": f"{access} {found.group(1)} printed twice"}
                    break
                charges[key] = (float(found.group(2)), found.group(3))
        if "error" in codes.get(code, {}):
            continue
        eligibility = " ".join(line.strip() for line in service.splitlines()
                               if line.strip() and line.strip() != "Service" and not line.strip().startswith("Bylaw "))
        # The bylaw prints its bullets as a lone "o" that text extraction scatters between words.
        notes = re.sub(r"(?m)^o\s*$|^o\s+", "", distribution)
        codes[code] = {"name": head.group(2).strip(), "page": page, "charges": charges, "eligibility": eligibility,
                       "notes": " ".join(notes.split())}
    return {"year": int(year.group(1)), "effective": _iso(effective.group(1)), "codes": codes,
            "on_peak": f"{peak.group(1)} to {peak.group(2)}, every day of the week"}


def parse_rates_page(html: str, today: date) -> dict:
    """The current year's Rate of Last Resort price and the dated City riders (either may be None)."""
    soup = parse_html(html or "")
    tables = [[[_flat(cell) for cell in row.find_all(["td", "th"])] for row in table.find_all("tr")]
              for table in soup.find_all("table")]
    result: dict = {"rolr": None, "riders": None, "rds": None}
    current = [table for table in tables if table and len(table[0]) >= 2 and table[0][0] == str(today.year)
               and re.fullmatch(r"(?i)rolr \(\$/kwh\)", table[0][1])]
    if len(current) == 1:
        header = current[0][0]
        rows = [row for row in current[0][1:] if row and row[0] == "January-December"]
        value = re.fullmatch(r"\d+\.\d{4,5}", rows[0][1]) if len(rows) == 1 and len(rows[0]) > 1 else None
        if value:
            result["rolr"] = {"rate": float(value.group(0)), "start": f"{today.year}-01-01",
                              "end": f"{today.year}-12-31"}
            if len(header) > 2 and header[2].upper().startswith("RDS") and len(rows[0]) > 2:
                result["rds"] = rows[0][2]
    text = _flat(soup)
    sentence = re.search(r"Effective (" + _LONG_DATE + r") the following City of Lethbridge Riders are as follows: "
                         r"Rider A: (\d+\.\d+) % of DT charges Rider B: \$(-?\d+\.\d+)/kWh Rider C: \$(-?\d+\.\d+)/kWh",
                         text)
    rider_rows = next((table for table in tables if table and table[0][:1] == ["Rider A"]), None)
    if sentence and rider_rows:
        by_name = {row[0]: row for row in rider_rows if row and row[0] in ("Rider A", "Rider B")}
        dated = [(_iso(found.group(1)), row[1]) for row in rider_rows
                 if row and (found := re.fullmatch(r"Effective (" + _LONG_DATE + ")", row[0])) and len(row) > 1]
        in_effect = [value for when, value in sorted(dated) if when <= today.isoformat()]
        a, b, c = sentence.group(2), sentence.group(3), sentence.group(4)
        if (by_name.get("Rider A", [""] * 3)[2].startswith(f"{a}%") and by_name.get("Rider B", [""] * 3)[2]
                .startswith(f"${b} ") and in_effect and in_effect[-1].startswith(f"${c} ")):
            result["riders"] = {"date": _iso(sentence.group(1)), "A": float(a), "B": float(b), "C": float(c)}
    return result


def _component(access: str, charge: str, value: float, unit: str, code: str, on_peak: str) -> RateComponent:
    unit_text = UNITS[unit]
    kind = {"day": "fixed", "kVA per day": "demand", "kWh": "distribution"}[unit]
    if access == "transmission":
        kind = "transmission"
    name = f"{access.title()} {charge}"
    component = RateComponent(component_type=kind, component_name=name, charge_value=value, charge_unit=unit_text)
    if unit == "kVA per day":
        component.demand_unit = "kVA"
        component.notes = ("Billed on the greater of the metered demand and the ratchet demand (the highest demand in "
                           "the last 12 months).")
    if charge.startswith("On-Peak"):
        component.tou_period, component.tou_hours = "on-peak", on_peak
    elif charge.startswith("Off-Peak"):
        component.tou_period, component.tou_hours = "off-peak", "All hours outside On-Peak"
    return component


def parse_tariff(bylaw: dict, table: tuple[int, dict], page: dict, bylaw_url: str, table_url: str,
                 today: date, discovery_note: str = "") -> tuple[list[TariffRecord], dict[str, str]]:
    """Wires records for each in-scope rate code plus the Rate of Last Resort records; (records, rejections)."""
    table_year, table_values = table
    if table_year != bylaw["year"]:
        raise ValueError(f"rate table year {table_year} differs from the bylaw's {bylaw['year']} rates")
    if bylaw["effective"] > today.isoformat():
        raise ValueError(f"bylaw rates take effect {bylaw['effective']}, after {today.isoformat()}")
    rejections: dict[str, str] = {}
    records: list[TariffRecord] = []
    riders = page["riders"]
    if riders is None:
        rejections["riders"] = "Riders A/B/C sentence and rider table not found or do not agree"
    elif riders["date"] > today.isoformat():
        rejections["riders"] = f"riders take effect {riders['date']}, after {today.isoformat()}"
        riders = None
    for code, (customer_class, structure) in CODES.items():
        section = bylaw["codes"].get(code)
        if section is None or "error" in section:
            rejections[code] = (section or {}).get("error", "rate code section not found in the bylaw")
            continue
        if riders is None:
            rejections[code] = "City riders unavailable"
            continue
        mismatch = []
        expected = set()
        for key, row in TABLE_ROWS.items():
            if key in section["charges"]:
                value = section["charges"][key][0]
                listed = table_values.get((row, code))
                if value:
                    expected.add(row)
                if (listed is None and value != 0) or (listed is not None and abs(listed - value) > 1e-9):
                    mismatch.append(f"{key[0]} {key[1]} {value} vs rate table {listed}")
        extra = sorted(row for row, column in table_values if column == code and row not in expected)
        if extra:
            mismatch.append("rate table rows without a bylaw charge: " + ", ".join(extra))
        if mismatch:
            rejections[code] = "bylaw and rate table disagree: " + "; ".join(mismatch)
            continue
        detail = f"Electric Distribution Tariff Bylaw 6364 (consolidation), Rate Code {code}, PDF page {section['page']}"
        components, zero = [], []
        for (access, charge), (value, unit) in section["charges"].items():
            if value == 0:
                zero.append(f"{access} {charge.lower()}")
                continue
            component = _component(access, charge, value, unit, code, bylaw["on_peak"])
            component.effective_date, component.source_url = bylaw["effective"], bylaw_url
            component.source_detail = detail + "; matches the rate table"
            components.append(component)
        for letter, name, value, note in (
                ("B", "Rider B - Balancing Pool Consumer Allocation Rider", riders["B"],
                 "Balancing Pool amounts passed through by the AESO; applies to all distribution tariff rates."),
                ("C", "Rider C - AESO DTS Rider", riders["C"],
                 "Flows through the AESO DTS transmission charges not matched by the transmission access rates; "
                 "reviewed monthly.")):
            components.append(RateComponent(
                component_type="rebate" if value < 0 else "rider", component_name=name, charge_value=value,
                charge_unit="$/kWh", effective_date=riders["date"], source_url=RATES_PAGE_URL,
                source_detail="Utility Rates page, Electric rates, City of Lethbridge riders", notes=note))
        notes = [f"City of Lethbridge Electric Distribution Tariff, Rate Code {code} ({section['name']}): "
                 f"{bylaw['year']} rates effective {bylaw['effective']}. Wires charges only; energy is billed "
                 "separately (Rate of Last Resort or a retailer).",
                 f"Rider A Local Access Fee: {riders['A']:.2f}% of the total distribution and transmission access "
                 "charges (not included as a charge).",
                 "The billing period is monthly."]
        if zero:
            notes.append("Printed at $0.0000: " + ", ".join(zero) + ".")
        minimum = re.search(r"The minimum daily charge is (.+?)(?:\.|\s+The billing period|\s+Demand charge|$)",
                            section["notes"])
        if minimum:
            notes.append(f"The minimum daily charge is {minimum.group(1)} (a floor, not an additional charge).")
        if any(c.tou_period for c in components):
            notes.append(f"Transmission system usage is priced on-peak ({bylaw['on_peak']}) and off-peak.")
        if discovery_note:
            notes.append(discovery_note)
        records.append(TariffRecord(
            utility_name=UTILITY, province="AB", utility_type="electricity",
            tariff_name=f"{section['name']} (Rate {code})", tariff_code=code, customer_class=customer_class,
            sub_class=section["name"].lower(), eligibility=section["eligibility"] or None,
            rate_structure=structure, pricing_method="municipal",
            effective_date=max(c.effective_date for c in components),
            source_url=bylaw_url, source_page=detail, confidence="high", notes=" ".join(notes),
            components=components))
    rolr = page["rolr"]
    if rolr is None:
        rejections["RoLR"] = f"no {today.year} Rate of Last Resort price for January-December on the rates page"
    else:
        for code, customer_class, label in (("RoLR-Res", "residential", "residential"),
                                            ("RoLR-SB", "commercial", "small business")):
            notes = (f"City of Lethbridge Rate of Last Resort for {label} sites using less than 250,000 kWh a year: "
                     "the City publishes one price for all eligible customers. It includes energy-related charges and "
                     "the 0.1 cents/kWh consumer awareness surcharge (the City's page). Fixed for the two-year term "
                     "(2025-2026); wires charges are billed separately.")
            if page["rds"]:
                notes += (f" The page also lists an 'RDS' price ({page['rds']} $/kWh) without defining it; it is not "
                          "stored.")
            records.append(TariffRecord(
                utility_name=UTILITY, province="AB", utility_type="electricity",
                tariff_name=f"Rate of Last Resort — {label.title()}", tariff_code=code, customer_class=customer_class,
                sub_class=f"rate of last resort {label}", rate_structure="flat", pricing_method="regulated",
                effective_date=rolr["start"], end_date=rolr["end"],
                source_url=RATES_PAGE_URL, source_page="Utility Rates page, Electric rates, Current rates table",
                confidence="high", notes=notes, components=[RateComponent(
                    component_type="energy", component_name="RoLR Energy Charge", charge_value=rolr["rate"],
                    charge_unit="$/kWh", effective_date=rolr["start"], end_date=rolr["end"], source_url=RATES_PAGE_URL,
                    source_detail=f"Utility Rates page, {today.year} RoLR ($/kWh), January-December")]))
    return records, rejections


class LethbridgeScraper(BaseScraper):
    """Parse the City of Lethbridge's distribution tariff and Rate of Last Resort price."""

    def __init__(self) -> None:
        super().__init__(utility_name=UTILITY, province="AB")

    def scrape(self) -> list[TariffRecord]:
        # No seed fallback for batch 18 utilities (owner confirmed 2026-11-17).
        records = self._try_live_scrape()
        if not records:
            self.logger.warning("Lethbridge: no live records (no seed fallback)")
        return records

    def _discover(self, page_url: str, pattern: str, last_known: str, label: str) -> tuple[str, str, str]:
        try:
            html = self.fetch_page(page_url)
        except Exception as exc:
            self.logger.warning("Lethbridge page %s unavailable: %s", page_url, exc)
            html = ""
        found = find_link(html, pattern, page_url)
        if found:
            return html, found[0], ""
        return html, last_known, f"The City's page did not link the {label}, so the last known copy was read."

    def _try_live_scrape(self) -> list[TariffRecord]:
        today = date.today()
        rates_html, table_url, table_note = self._discover(RATES_PAGE_URL, r"20\d\d Rate Table",
                                                           LAST_KNOWN_RATE_TABLE_URL, "rate table")
        if not rates_html:
            return []
        _, bylaw_url, bylaw_note = self._discover(ELECTRIC_PAGE_URL, r"Bylaw \d+ Electric Distribution Tariff",
                                                  LAST_KNOWN_BYLAW_URL, "distribution tariff bylaw")
        try:
            page = parse_rates_page(rates_html, today)
            bylaw = parse_bylaw(extract_pdf_pages(self.fetch_bytes(bylaw_url), drop_repeated_lines=False))
            table = parse_rate_table(rate_table_words(self.fetch_bytes(table_url)))
            records, rejections = parse_tariff(bylaw, table, page, bylaw_url, table_url, today,
                                               " ".join(note for note in (table_note, bylaw_note) if note))
        except Exception as exc:
            self.logger.warning("Lethbridge tariff failed closed: %s", exc)
            return []
        for code, reason in rejections.items():
            self.logger.warning("Lethbridge %s rejected: %s", code, reason)
        return self.mark_live_parsed(records)
