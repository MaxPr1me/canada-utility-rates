"""
manitoba_hydro.py — Scraper for Manitoba Hydro electricity rates (Manitoba).

Manitoba Hydro is the sole electricity and natural gas utility in Manitoba.
Manitoba benefits from abundant hydroelectric generation, resulting in some
of the lowest electricity rates in Canada.

Official sources:
  Residential: https://www.hydro.mb.ca/accounts_and_services/rates/residential_rates/
  Commercial:  https://www.hydro.mb.ca/accounts_and_services/rates/commercial_rates/

Regulated by: Public Utilities Board of Manitoba (PUB Manitoba)
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent
from scrapers.utils.parsing import detect_js_rendered, parse_html
from scrapers.utils.change_detection import compare_to_seed, log_change_alerts, has_critical_alerts

logger = logging.getLogger(__name__)

# ── URLs ──────────────────────────────────────────────────────────
RESIDENTIAL_URL = "https://www.hydro.mb.ca/accounts_and_services/rates/residential_rates/"
COMMERCIAL_URL = "https://www.hydro.mb.ca/accounts_and_services/rates/commercial_rates/"

# ── Seed / fallback data (updated to January 1, 2026 published rates) ──

SEED_RESIDENTIAL = {
    "effective_date": "2026-01-01",
    "source_url": RESIDENTIAL_URL,
    "energy_rate": 0.09970,          # $/kWh — flat rate (9.970¢/kWh)
    "basic_charge_per_month": 9.84,  # $/month (≤200 Amp service)
}

SEED_GENERAL_SERVICE_SMALL = {
    "effective_date": "2026-01-01",
    "source_url": COMMERCIAL_URL,
    "energy_rate_tier1": 0.09864,      # $/kWh — first 11,000 kWh (9.864¢/kWh)
    "energy_rate_tier2": 0.07568,      # $/kWh — balance (7.568¢/kWh)
    "tier1_threshold_kwh": 11000,      # kWh
    "basic_charge_per_month": 21.57,   # $/month (single-phase)
}

SEED_GENERAL_SERVICE_MEDIUM = {
    "effective_date": "2026-01-01",
    "source_url": COMMERCIAL_URL,
    "energy_rate_tier1": 0.09120,      # $/kWh — first 19,500 kWh (9.120¢/kWh)
    "energy_rate_tier2": 0.04728,      # $/kWh — balance (4.728¢/kWh)
    "tier1_threshold_kwh": 19500,      # kWh
    "demand_charge": 12.39,            # $/kVA (first 50 kVA no charge, balance)
    "demand_free_kva": 50,             # first 50 kVA at no charge
    "basic_charge_per_month": 35.81,   # $/month
}

# Commercial general-service classes published on the commercial rates page,
# in page order. (tariff_name, customer_class, rate_structure, eligibility)
_MB_COMMERCIAL: list[tuple[str, str, str, str]] = [
    ("General Service Small (Non-Demand)", "commercial", "tiered",
     "General service small; billing demand not exceeding 50 kVA (non-demand metered)."),
    ("General Service Small (Demand)", "commercial", "demand",
     "General service small; billing demand between 51 kVA and 200 kVA."),
    ("General Service Seasonal (Single Phase)", "commercial", "tiered",
     "General service seasonal; consumption primarily in summer; demand not exceeding 50 kVA."),
    ("General Service Medium", "commercial", "demand",
     "General service medium; billing demand exceeding 200 kVA."),
    ("General Service Large (>750 V to 30 kV)", "industrial", "demand",
     "General service large; supply voltage exceeding 750 V but not exceeding 30 kV."),
    ("General Service Large (>30 kV to 100 kV)", "industrial", "demand",
     "General service large; supply voltage exceeding 30 kV but not exceeding 100 kV."),
    ("General Service Large (>100 kV)", "industrial", "demand",
     "General service large; supply voltage exceeding 100 kV."),
]


def _mb_section(low: str) -> Optional[int]:
    """Map a header line to a commercial section index (see _MB_COMMERCIAL), else None."""
    if "general service" not in low:
        return None
    if "small" in low and "non-demand" in low:
        return 0
    if "small" in low and "demand" in low:
        return 1
    if "seasonal" in low:
        return 2
    if "medium" in low:
        return 3
    if "large" in low and "750" in low:
        return 4
    if "large" in low and "exceeding 30" in low:
        return 5
    if "large" in low and "exceeding 100" in low:
        return 6
    return None


def _mb_number(line: str) -> Optional[tuple[str, float, str]]:
    """Parse a Manitoba Hydro value line into (kind, value, unit); glyph-agnostic for cents."""
    line = line.strip()
    m = re.match(r"^\$\s*([\d.]+)\s*/\s*kWh$", line, re.I)
    if m:
        return ("energy", float(m.group(1)), "$/kWh")
    m = re.match(r"^([\d.]+)\s*[^\d\s/]{0,2}\s*/\s*kWh$", line, re.I)
    if m:
        return ("energy", round(float(m.group(1)) / 100.0, 6), "$/kWh")
    m = re.match(r"^\$\s*([\d.]+)\s*/\s*kVA$", line, re.I)
    if m:
        return ("demand", float(m.group(1)), "$/kVA")
    m = re.match(r"^\$\s*([\d,]+\.?\d*)$", line)
    if m:
        return ("fixed", float(m.group(1).replace(",", "")), "$")
    return None


def _mb_component(label: str, value: str) -> Optional[RateComponent]:
    """Build a RateComponent from a label line and the value line that follows it."""
    parsed = _mb_number(value)
    if parsed is None:
        return None
    _, number, _ = parsed
    low = label.lower()

    if low.startswith("basic"):
        variant = (
            " (single phase)" if "single phase" in low
            else " (three phase)" if "three phase" in low
            else ""
        )
        if "annual" in low:
            return RateComponent(
                component_type="fixed", component_name="Basic Annual Charge" + variant,
                charge_value=number, charge_unit="$/year",
            )
        return RateComponent(
            component_type="fixed", component_name="Basic Charge" + variant,
            charge_value=number, charge_unit="$/month",
        )

    if "kwh" in low and low.startswith(("first", "next", "balance")):
        tier = 1 if low.startswith("first") else 2 if low.startswith("next") else 3
        m = re.search(r"(?:first|next)\s+([\d,]+)\s*kwh", low)
        threshold = float(m.group(1).replace(",", "")) if m else None
        return RateComponent(
            component_type="energy", component_name=label,
            charge_value=number, charge_unit="$/kWh",
            tier_number=tier, tier_threshold=threshold,
            tier_unit="kWh" if threshold else None,
        )

    if low.startswith("energy charge"):
        return RateComponent(
            component_type="energy", component_name="Energy Charge",
            charge_value=number, charge_unit="$/kWh",
        )

    if low.startswith("demand charge") or ("balance of" in low and "demand" in low):
        return RateComponent(
            component_type="demand",
            component_name="Demand Charge" if low.startswith("demand") else label,
            charge_value=number, charge_unit="$/kVA", demand_unit="kVA",
            notes=None if low.startswith("demand") else "Applied to billing demand above the first 50 kVA",
        )

    return None


def _mb_lines(html: str) -> list[str]:
    return [re.sub(r"\s+", " ", ln).strip() for ln in parse_html(html).get_text("\n", strip=True).splitlines() if ln.strip()]


def _mb_effective(lines: list[str], before: int) -> Optional[tuple[str, str]]:
    """First 'Rates effective <date>' line ahead of the electricity tables -> (iso, printed); rejects future dates."""
    for ln in lines[:before]:
        m = re.fullmatch(r"Rates effective (\w+ \d{1,2}, \d{4})", ln)
        if m:
            try:
                parsed = datetime.strptime(m.group(1), "%B %d, %Y").date()
            except ValueError:
                return None
            return (parsed.isoformat(), m.group(1)) if parsed <= date.today() else None
    return None


def _mb_pairs(section: list[str], spec: dict[str, tuple]) -> Optional[tuple[list[RateComponent], list[str]]]:
    """Pair label/value lines against an exact spec; any unknown, missing or repeated row rejects the class."""
    components: dict[str, RateComponent] = {}
    texts: list[str] = []
    i = 0
    while i < len(section):
        label = section[i]
        if label.lower() in ("charge", "cost"):
            i += 1
            continue
        parsed = _mb_number(section[i + 1]) if i + 1 < len(section) else None
        if parsed is None:
            texts.append(label)
            i += 1
            continue
        key = label.lower()
        if key not in spec or key in components:
            return None
        kind, number, unit = parsed
        want_kind, name, want_unit = spec[key]
        if kind != want_kind or (kind != "fixed" and unit != want_unit):
            return None
        components[key] = RateComponent(
            component_type=kind, component_name=name, charge_value=number, charge_unit=want_unit,
        )
        i += 2
    if set(components) != set(spec):
        return None
    return [components[k] for k in spec], texts


def _mb_stamp(record: TariffRecord, iso: str, url: str, detail: str) -> TariffRecord:
    record.effective_date = iso
    record.source_url = url
    record.source_page = detail
    for component in record.components:
        component.effective_date = iso
        component.source_url = url
        component.source_detail = detail
    return record


# (tariff_name, section header prefix, structure, sub_class, spec, required source phrases, eligibility)
_MB_RESIDENTIAL = [
    ("Residential Service", "residential standard rates", "flat", None,
     {"basic monthly charge not exceeding 200 amp": ("fixed", "Basic Charge", "$/month"),
      "basic monthly charge exceeding 200 amp": ("fixed", "Basic Charge (exceeding 200 Amp)", "$/month"),
      "energy charge": ("energy", "Energy Charge", "$/kWh")},
     ("minimum monthly bill is the basic charge",), None),
    ("Residential Seasonal Service", "residential seasonal rates", "flat", "residential seasonal",
     {"basic annual charge not exceeding 200 amp": ("fixed", "Basic Annual Charge", "$/year"),
      "energy charge": ("energy", "Energy Charge", "$/kWh")},
     ("minimum annual bill is the basic charge", "billed twice a year", "less than 7,500 kwh per season"),
     "Seasonal residential account using less than 7,500 kWh per season; billed April and October for six-month periods."),
    ("Residential Diesel Service", "residential diesel rates", "flat", "residential diesel",
     {"basic monthly charge not exceeding 60 amp": ("fixed", "Basic Charge", "$/month"),
      "energy charge": ("energy", "Energy Charge", "$/kWh")},
     ("minimum monthly bill is the monthly basic charge", "does not exceed 60 a, 120/240 v, single phase"),
     "Residential services in the diesel communities with capacity not exceeding 60 A, 120/240 V, single phase."),
]

# (tariff_name, header, sub_class, spec, required phrases)
_MB_DIESEL_COMMERCIAL = [
    ("Diesel General Service", "diesel - general service", "diesel general service",
     {"basic monthly charge": ("fixed", "Basic Charge", "$/month"),
      "first 2,000 kwh": ("energy", "First 2,000 kWh", "$/kWh"),
      "balance of kwh": ("energy", "Balance of kWh", "$/kWh")}),
    ("Diesel Government and First Nation Education", "diesel - government and first nation education",
     "diesel government and first nation education",
     {"basic monthly charge": ("fixed", "Basic Charge", "$/month"),
      "energy charge": ("energy", "Energy Charge", "$/kWh")}),
]

# Per-class component counts (type -> count) that must all be present for a general-service class to be accepted.
_MB_COMMERCIAL_SHAPE = {
    0: {"fixed": 2, "energy": 2},
    1: {"fixed": 2, "energy": 3, "demand": 1},
    2: {"fixed": 1, "energy": 2},
    3: {"fixed": 1, "energy": 2, "demand": 1},
    4: {"energy": 1, "demand": 1},
    5: {"energy": 1, "demand": 1},
    6: {"energy": 1, "demand": 1},
}


class ManitobaHydroScraper(BaseScraper):
    """Scrape Manitoba Hydro electricity rates."""

    def __init__(self):
        super().__init__(utility_name="Manitoba Hydro", province="MB")

    def scrape(self) -> list[TariffRecord]:
        """
        Attempt to scrape live Manitoba Hydro rates.
        Falls back to seed data if the live page is unreachable or unparseable.
        """
        records = []

        live_records = self._try_live_scrape()
        if live_records:
            records.extend(live_records)
            self.logger.info(
                "Successfully scraped %d Manitoba Hydro tariffs from live site",
                len(records),
            )
        else:
            self.logger.warning("Live scrape failed — using seed data for Manitoba Hydro")
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    # ── Live scraping ────────────────────────────────────────────

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Attempt to parse rates from the live Manitoba Hydro website."""
        try:
            # Fetch both rate pages
            residential_html = self.fetch_page(RESIDENTIAL_URL)
            commercial_html = self.fetch_page(COMMERCIAL_URL)

            # Check if pages are JS-rendered (would need a headless browser)
            if detect_js_rendered(residential_html):
                self.logger.warning("Residential page appears JS-rendered — cannot parse")
                return None
            if detect_js_rendered(commercial_html):
                self.logger.warning("Commercial page appears JS-rendered — cannot parse")
                return None

            # Parse each page
            residential_records = self._parse_residential(residential_html)
            commercial_records = self._parse_commercial(commercial_html)

            live_records = residential_records + commercial_records
            if not live_records:
                self.logger.warning("Could not parse any tariffs from live pages")
                return None

            # Compare to seed data for sanity checking
            seed_records = self._seed_data()
            alerts = compare_to_seed(live_records, seed_records)
            log_change_alerts(alerts)

            if has_critical_alerts(alerts):
                self.logger.error(
                    "Critical deviations from seed data — likely a parsing error. "
                    "Falling back to seed data."
                )
                return None

            live_records = self.mark_live_parsed(live_records)

            # Preserve any classes we couldn't parse live as labelled seed estimates
            live_names = {r.tariff_name for r in live_records}
            seed_only = [r for r in seed_records if r.tariff_name not in live_names]
            if seed_only:
                live_records = live_records + self.mark_fallback(seed_only)

            return live_records

        except Exception as e:
            self.logger.warning("Live scrape failed for Manitoba Hydro: %s", e)
            return None

    def _parse_residential(self, html: str) -> list[TariffRecord]:
        """Parse residential rates from the Manitoba Hydro residential page text."""
        lines = _mb_lines(html)
        starts = [i for i, ln in enumerate(lines) if ln.lower().startswith("residential standard rates")]
        if not starts:
            self.logger.warning("Residential standard section not found")
            return []
        eff = _mb_effective(lines, starts[0])
        if eff is None:
            self.logger.warning("Residential electricity effective date missing or in the future")
            return []
        iso, printed = eff

        def section(prefix: str) -> Optional[list[str]]:
            idx = [i for i, ln in enumerate(lines) if ln.lower().startswith(prefix)]
            if not idx:
                return None
            out: list[str] = []
            for ln in lines[idx[0] + 1:]:
                low = ln.lower()
                if low.startswith(("residential ", "natural gas", "back to top")):
                    break
                out.append(ln)
            return out

        records: list[TariffRecord] = []
        for name, prefix, structure, sub_class, spec, phrases, eligibility in _MB_RESIDENTIAL:
            rows = section(prefix)
            parsed = _mb_pairs(rows, spec) if rows is not None else None
            body = " ".join(rows or []).lower()
            if parsed is None or not all(p in body for p in phrases):
                self.logger.warning("Manitoba Hydro %s rejected: section missing, drifted or incomplete", name)
                continue
            components, texts = parsed
            if name == "Residential Service":
                components[0].notes = "Monthly basic charge regardless of consumption (≤200 Amp service)"
                components[1].notes = "Monthly basic charge for service exceeding 200 Amp"
                components[2].notes = "Flat rate applied to all kWh consumed"
                notes = (
                    "Manitoba Hydro flat residential rate. Among the lowest electricity rates in Canada "
                    "due to abundant hydroelectric generation. Minimum monthly bill is the basic charge."
                )
            else:
                notes = " ".join(t for t in texts if t.lower().startswith(("minimum", "the account", "the residential")))
                if name == "Residential Diesel Service":
                    notes += " Page states diesel-zone rates were maintained at existing levels; date is the page's rates-effective date."
            records.append(_mb_stamp(TariffRecord(
                utility_name="Manitoba Hydro", province="MB", utility_type="electricity",
                tariff_name=name, customer_class="residential", sub_class=sub_class,
                rate_structure=structure, eligibility=eligibility, confidence="high",
                notes=notes, components=components,
            ), iso, RESIDENTIAL_URL, f"Residential rates page, '{name}' table; rates effective {printed}"))
        return records

    def _parse_commercial(self, html: str) -> list[TariffRecord]:
        """Parse every general-service class from the Manitoba Hydro commercial rates page.

        Labels and values sit on separate lines; each class section header repeats
        before its data. Capture (label, next-line value) pairs per section.
        """
        raw = _mb_lines(html)
        anchors = [i for i, ln in enumerate(raw) if ln.lower().startswith("commercial general service rate options")]
        eff = _mb_effective(raw, anchors[0]) if anchors else None
        if eff is None:
            self.logger.warning("Commercial electricity effective date missing or in the future")
            return []
        iso, printed = eff
        lines = [ln for ln in raw if not re.fullmatch(r"\d{1,2}", ln)]  # drop footnote markers
        sections: dict[int, list[RateComponent]] = {}
        section_notes: dict[int, list[str]] = {}
        current: Optional[int] = None
        i = 0
        while i < len(lines):
            low = lines[i].lower()
            if "diesel" in low or low.startswith("contact"):
                current = None
                i += 1
                continue
            sec = _mb_section(low)
            if sec is not None:
                current = sec
                sections.setdefault(current, [])
                i += 1
                continue
            if current is not None and i + 1 < len(lines):
                component = _mb_component(lines[i], lines[i + 1])
                if component is not None:
                    sections[current].append(component)
                    i += 2
                    continue
            if current is not None and low.startswith(("minimum", "monthly bill demand", "for accounts where")):
                section_notes.setdefault(current, []).append(lines[i])
            i += 1

        records: list[TariffRecord] = []
        for idx, (name, cclass, structure, eligibility) in enumerate(_MB_COMMERCIAL):
            components = sections.get(idx)
            if not components:
                continue
            counts: dict[str, int] = {}
            for c in components:
                counts[c.component_type] = counts.get(c.component_type, 0) + 1
            if counts != _MB_COMMERCIAL_SHAPE[idx]:
                self.logger.warning("Manitoba Hydro %s rejected: unexpected components %s", name, counts)
                continue
            extra = " ".join(dict.fromkeys(section_notes.get(idx, [])))
            records.append(_mb_stamp(TariffRecord(
                utility_name="Manitoba Hydro", province="MB", utility_type="electricity",
                tariff_name=name, customer_class=cclass, sub_class=name.lower(),
                rate_structure=structure, confidence="high", eligibility=eligibility,
                notes=("Parsed from the Manitoba Hydro commercial general service rate page. " + extra).strip(),
                components=components,
            ), iso, COMMERCIAL_URL, f"Commercial rates page, '{name}' table; rates effective {printed}"))
        records.extend(self._parse_diesel_commercial(lines, iso, printed))
        return records

    def _parse_diesel_commercial(self, lines: list[str], iso: str, printed: str) -> list[TariffRecord]:
        """Parse the diesel-zone general service and government/First Nation education tables."""
        norm = [ln.lower().replace("\u2013", "-").replace("\u2014", "-") for ln in lines]
        if not any("first nation schools and educational facilities" in n for n in norm):
            return []
        records: list[TariffRecord] = []
        for name, header, sub_class, spec in _MB_DIESEL_COMMERCIAL:
            starts = [i for i, n in enumerate(norm) if n == header]
            if not starts:
                continue
            rows: list[str] = []
            for j in range(starts[0], len(lines)):
                if norm[j] != header and (norm[j].startswith(("diesel -", "contact", "back to top", "limited use"))):
                    break
                if norm[j] != header:
                    rows.append(lines[j])
            parsed = _mb_pairs(rows, spec)
            if parsed is None:
                self.logger.warning("Manitoba Hydro %s rejected: section missing or drifted", name)
                continue
            components, texts = parsed
            for tier, c in enumerate([c for c in components if c.component_type == "energy"], 1):
                if len(spec) > 2:
                    c.tier_number = tier
                    m = re.search(r"first ([\d,]+) kwh", c.component_name.lower())
                    if m:
                        c.tier_threshold, c.tier_unit = float(m.group(1).replace(",", "")), "kWh"
            notes = " ".join(t for t in texts if t.lower().startswith("minimum"))
            records.append(_mb_stamp(TariffRecord(
                utility_name="Manitoba Hydro", province="MB", utility_type="electricity",
                tariff_name=name, customer_class="commercial", sub_class=sub_class,
                rate_structure="tiered" if len(spec) > 2 else "flat", confidence="high",
                eligibility=(
                    "Diesel-zone commercial customers are eligible for the general service rate; the government "
                    "and education rate applies to First Nation schools and educational facilities."
                ),
                notes=(notes + " Page states diesel-zone rates were maintained at existing levels; "
                       "date is the page's rates-effective date.").strip(),
                components=components,
            ), iso, COMMERCIAL_URL, f"Commercial rates page, '{name}' table; rates effective {printed}"))
        return records

    # ── Seed / fallback data ─────────────────────────────────────

    def _seed_data(self) -> list[TariffRecord]:
        """Return seed/fallback data based on known published rates."""
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Manitoba Hydro",
            province="MB",
            utility_type="electricity",
            tariff_name="Residential Service",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes=(
                "Manitoba Hydro flat residential rate. "
                "Among the lowest electricity rates in Canada due to abundant hydroelectric generation."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_per_month"],
                    charge_unit="$/month",
                    notes="Monthly basic charge regardless of consumption (≤200 Amp service)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge",
                    charge_value=SEED_RESIDENTIAL["energy_rate"],
                    charge_unit="$/kWh",
                    notes="Flat rate applied to all kWh consumed",
                ),
            ],
        ))

        # ── General Service Small (Non-Demand) ───────────────────
        records.append(TariffRecord(
            utility_name="Manitoba Hydro",
            province="MB",
            utility_type="electricity",
            tariff_name="General Service Small (Non-Demand)",
            customer_class="commercial",
            sub_class="general service small",
            rate_structure="tiered",
            effective_date=SEED_GENERAL_SERVICE_SMALL["effective_date"],
            source_url=SEED_GENERAL_SERVICE_SMALL["source_url"],
            confidence="high",
            eligibility="Non-demand metered commercial customers (≤50 kVA)",
            notes="Small commercial accounts without demand metering",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_GENERAL_SERVICE_SMALL["basic_charge_per_month"],
                    charge_unit="$/month",
                    notes="Monthly basic charge (single-phase service)",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — First Block",
                    charge_value=SEED_GENERAL_SERVICE_SMALL["energy_rate_tier1"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_GENERAL_SERVICE_SMALL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="First 11,000 kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — Balance",
                    charge_value=SEED_GENERAL_SERVICE_SMALL["energy_rate_tier2"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_GENERAL_SERVICE_SMALL["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="All additional kWh beyond the first block",
                ),
            ],
        ))

        # ── General Service Medium ───────────────────────────────
        records.append(TariffRecord(
            utility_name="Manitoba Hydro",
            province="MB",
            utility_type="electricity",
            tariff_name="General Service Medium",
            customer_class="commercial",
            sub_class="general service medium",
            rate_structure="demand",
            effective_date=SEED_GENERAL_SERVICE_MEDIUM["effective_date"],
            source_url=SEED_GENERAL_SERVICE_MEDIUM["source_url"],
            confidence="high",
            eligibility="Demand-metered commercial customers (>200 kVA)",
            notes="Medium commercial accounts with demand metering",
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Charge",
                    charge_value=SEED_GENERAL_SERVICE_MEDIUM["basic_charge_per_month"],
                    charge_unit="$/month",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_GENERAL_SERVICE_MEDIUM["demand_charge"],
                    charge_unit="$/kVA",
                    demand_unit="kVA",
                    notes="First 50 kVA at no charge; applied to billing demand above 50 kVA",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — First Block",
                    charge_value=SEED_GENERAL_SERVICE_MEDIUM["energy_rate_tier1"],
                    charge_unit="$/kWh",
                    tier_number=1,
                    tier_threshold=SEED_GENERAL_SERVICE_MEDIUM["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="First 19,500 kWh per month",
                ),
                RateComponent(
                    component_type="energy",
                    component_name="Energy Charge — Balance",
                    charge_value=SEED_GENERAL_SERVICE_MEDIUM["energy_rate_tier2"],
                    charge_unit="$/kWh",
                    tier_number=2,
                    tier_threshold=SEED_GENERAL_SERVICE_MEDIUM["tier1_threshold_kwh"],
                    tier_unit="kWh",
                    notes="All additional kWh beyond the first block",
                ),
            ],
        ))

        return records
