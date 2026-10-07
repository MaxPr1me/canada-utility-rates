"""
qulliq.py — Scraper for Qulliq Energy Corporation electricity rates (Nunavut).

QEC serves 25 diesel communities under a territory-wide rate structure
(Ministerial Instruction of October 21, 2022): every customer of the same
type pays the same rate regardless of community. Separate energy rates exist
for non-government, government and municipal tax-based customers.

Official sources (text HTML):
  - Customer Rates page — per-class energy rates and the Nunavut Electricity
    Subsidy Program (NESP) kWh allowances.
  - Interim Electricity Rates notice — URRC-authorized interim rates effective
    April 1, 2025, including the monthly service and demand service charges.
  - General Rate Application page — used only to detect a newer application.
  - Fuel Stabilization Rate page — rider context (no current rider value is
    published as approved text, so no rider price is emitted).

The Customer Rates page labels its values "effective as of October 1, 2023",
but they equal the April 1, 2025 interim values; the parser requires that
agreement and uses the interim notice date. Any disagreement, a later page
label or a newer GRA effective date fails closed for the affected scope.

Regulated by the Minister responsible for QEC on advice of the Utility Rates
Review Council (URRC). Streetlight and standby service are out of scope.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

UTILITY = "Qulliq Energy Corporation"

PAGE_URLS = {
    "rates": "https://www.qec.nu.ca/customer-care/accounts-and-billing/customer-rates",
    "interim": "https://www.qec.nu.ca/interim-electricity-rates-effective-april-1-2025-general-rate-application",
    "gra": "https://www.qec.nu.ca/customer-care/rate-application",
    "fsr": "https://www.qec.nu.ca/customer-care/general-information/what-fuel-stabilization-rate",
}

# ── Seed / fallback rate data ─────────────────────────────────────
# Last values confirmed from the official pages (interim rates effective
# April 1, 2025). Used only as labelled, unverified fallback.
SEED = {
    "effective_date": "2025-04-01",
    "residential_service_charge": 36.00,     # $/month
    "commercial_demand_charge": 16.00,       # $/kW/month (non-government)
    "energy": {
        "NG-RES": 0.7494,
        "G-RES": 1.1300,
        "MT-RES": 0.7494,
        "NG-COM": 0.6208,
        "G-COM": 1.0533,
        "MT-COM": 0.6208,
    },
    "nesp_summer_kwh": 700,
    "nesp_winter_kwh": 1000,
}

CLASS_INFO = {
    # code: (tariff_name, customer_class, sub_class, page label, interim notice label)
    "NG-RES": ("Residential Service", "residential", "non_government",
               "Non-Government Residential (Domestic) Customers",
               "Residential non-Government/Municipal Tax Base"),
    "G-RES": ("Government Residential Service", "residential", "government",
              "Government Residential (Domestic) Customers", "Residential Government"),
    "MT-RES": ("Municipal Tax-Based Residential Service", "residential", "municipal_tax_based",
               None, "Residential non-Government/Municipal Tax Base"),
    "NG-COM": ("Commercial Service", "commercial", "non_government",
               "Non-Government Commercial Customers",
               "Commercial Non-Government/Municipal Tax Base"),
    "G-COM": ("Government Commercial Service", "commercial", "government",
              "Government Commercial Customers", "Commercial Government"),
    "MT-COM": ("Municipal Tax-Based Commercial Service", "commercial", "municipal_tax_based",
               None, "Commercial Non-Government/Municipal Tax Base"),
}

_MONEY = r"\$\s?(\d+(?:\.\d+)?)"
_DATE = r"([A-Z][a-z]+ \d{1,2}, \d{4})"


def _iso(text: str) -> Optional[str]:
    try:
        return datetime.strptime(text, "%B %d, %Y").date().isoformat()
    except ValueError:
        return None


class QulliqScraper(BaseScraper):
    """Parse Qulliq Energy Corporation territory-wide building rates."""

    def __init__(self) -> None:
        super().__init__(utility_name=UTILITY, province="NU")

    def scrape(self) -> list[TariffRecord]:
        records = self._try_live_scrape() or []
        parsed = {r.tariff_code for r in records}
        missing = [r for r in self._seed_data() if r.tariff_code not in parsed]
        if missing:
            self.logger.warning("Qulliq live parse incomplete — %d classes use unverified seed", len(missing))
            records.extend(self.mark_fallback(missing))
        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        pages: dict[str, str] = {}
        for key, url in PAGE_URLS.items():
            try:
                pages[key] = self._page_text(self.fetch_page(url))
            except Exception as exc:
                self.logger.warning("Qulliq %s page unavailable: %s", key, exc)
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

    @staticmethod
    def _norm(text: str) -> str:
        text = text.replace("\xa0", " ").replace("\u2013", "-").replace("\u2014", "-").replace("\u2019", "'")
        return re.sub(r"\s+", " ", text).strip()

    # ── Parsing ──────────────────────────────────────────────

    def parse_pages(self, pages: dict[str, str], today: Optional[date] = None) -> list[TariffRecord]:
        today = today or date.today()
        rates = self._norm(pages.get("rates", ""))
        interim = self._norm(pages.get("interim", ""))
        gra = self._norm(pages.get("gra", ""))
        fsr = self._norm(pages.get("fsr", ""))
        if not rates or not interim or not gra:
            self.logger.warning("Qulliq required page missing; failing closed")
            return []

        m = re.search(r"authorized Qulliq Energy Corporation \(QEC\) to implement interim electricity rates, effective " + _DATE, interim)
        effective = _iso(m.group(1)) if m else None
        if not effective or effective > today.isoformat():
            self.logger.warning("Qulliq interim notice effective date missing or in the future")
            return []

        # A GRA requesting a later effective date may change rates; require review.
        later = [d for d in (_iso(x) for x in re.findall(r"effective " + _DATE, gra)) if d and d > effective]
        if later or f"effective {m.group(1)}" not in gra:
            self.logger.warning("Qulliq rate-application page references a newer or different GRA date: %s", later)
            return []

        label = re.search(r"The rates below are effective as of " + _DATE, rates)
        label_iso = _iso(label.group(1)) if label else None
        if not label_iso or label_iso > effective:
            self.logger.warning("Qulliq customer-rates date label missing or newer than interim notice")
            return []

        notice = self._parse_interim(interim)
        page = self._parse_rates_page(rates)
        if notice is None or page is None:
            return []

        records: list[TariffRecord] = []
        for code, (name, cls, sub, page_label, _) in CLASS_INFO.items():
            notice_rate = notice["energy"].get(code)
            page_rate = page["energy"].get(code)
            if notice_rate is None or page_rate is None or round(page_rate, 4) != round(notice_rate, 4):
                self.logger.warning("Qulliq %s: page %s vs interim notice %s — class rejected", code, page_rate, notice_rate)
                continue
            if code == "NG-RES" and page.get("nesp") is None:
                self.logger.warning("Qulliq NESP allowance terms missing — non-government residential rejected")
                continue
            if code == "G-RES" and not page.get("public_housing"):
                self.logger.warning("Qulliq public-housing billing terms missing — government residential rejected")
                continue
            records.append(self._build(code, effective, page_rate, notice, page, label.group(1), fsr))
        return records

    def _parse_interim(self, text: str) -> Optional[dict]:
        def change(label: str, unit: str) -> Optional[float]:
            hit = re.search(re.escape(label) + r":? From ?" + _MONEY + r" to " + _MONEY + r" per " + unit + r"\b", text)
            return float(hit.group(2)) if hit else None

        service = change("Residential Monthly Service Charge", "month")
        demand = change("Commercial Demand Service Charge (Non-Government)", "kW")
        energy = {}
        for code, info in CLASS_INFO.items():
            value = change(f"Energy Rate (for {info[4]})", "kWh")
            if value is not None and 0 < value < 5:
                energy[code] = value
        if service is None or not 0 < service < 500 or demand is None or not 0 < demand < 200:
            self.logger.warning("Qulliq interim service/demand charges not found or out of range")
            return None
        if "interim rates will remain in place until final rates are approved" not in text:
            self.logger.warning("Qulliq interim-status wording missing; cannot classify rates")
            return None
        return {"service": service, "demand": demand, "energy": energy}

    def _parse_rates_page(self, text: str) -> Optional[dict]:
        energy: dict[str, float] = {}
        for code, info in CLASS_INFO.items():
            if info[3]:
                hit = re.search(r"(?<!Non-)" + re.escape(info[3]) + r" - (\d+(?:\.\d+)?) cents/kWh", text)
                if hit:
                    energy[code] = float(hit.group(1)) / 100
        muni = re.search(r"Municipal Tax-Based Customer \(Residential/Domestic - (\d+(?:\.\d+)?) cents/kWh & Commercial - (\d+(?:\.\d+)?) cents/kWh\)", text)
        if muni:
            energy["MT-RES"] = float(muni.group(1)) / 100
            energy["MT-COM"] = float(muni.group(2)) / 100
        nesp = re.search(
            r"subsidy of ([\d,]+) kWh for each 30-day period from April 1 to September 30 and "
            r"([\d,]+) kWh for each 30-day period from October 1 to March 31", text)
        nesp_terms = None
        if nesp and "only eligible for this subsidy for one residence" in text and "not living in a public housing unit" in text:
            nesp_terms = (int(nesp.group(1).replace(",", "")), int(nesp.group(2).replace(",", "")))
        public_housing = "tenant is billed directly for 6 cents/kWh" in text
        if not energy:
            return None
        return {"energy": energy, "nesp": nesp_terms, "public_housing": public_housing}

    # ── Record assembly ──────────────────────────────────────

    def _build(self, code: str, effective: str, energy_rate: float, notice: dict, page: dict,
               page_label: str, fsr: str) -> TariffRecord:
        name, cls, sub, _, _ = CLASS_INFO[code]
        rates_url, notice_url = PAGE_URLS["rates"], PAGE_URLS["interim"]
        conf = "medium"
        status = (
            "QEC interim rates authorized by the URRC effective April 1, 2025; per QEC they remain until final "
            "rates are approved and are refunded if final rates are lower. No published final 2025/26 rate "
            "schedule was found. The Customer Rates page labels these values 'effective as of "
            f"{page_label}', but they equal the April 1, 2025 interim notice values."
        )
        rider = ""
        if fsr:
            rider = (" Fuel Stabilization Rate rider: a separate cents/kWh charge or credit when approved; no current "
                     "approved rider value is published as text, so none is shown.")
            latest = re.search(r"FSR Application Letter ([A-Z][a-z]+ \d{4})", fsr)
            if latest:
                rider += (f" QEC's latest posted FSR application ({latest.group(1)}) is a request; its approval "
                          "is not published.")
        comps: list[RateComponent] = []
        if cls == "residential":
            fixed_note = "Interim Residential Monthly Service Charge."
            if code == "NG-RES":
                fixed_note += (" QEC states this increase is fully covered by the Nunavut Electricity Subsidy "
                               "Program (NESP) and customers will not be billed for this charge.")
            comps.append(RateComponent(
                component_type="fixed", component_name="Monthly Service Charge",
                charge_value=notice["service"], charge_unit="$/month", effective_date=effective,
                source_url=notice_url, source_detail="Interim rates notice — For Residential Customers",
                confidence=conf, notes=fixed_note))
        if code == "NG-COM":
            comps.append(RateComponent(
                component_type="demand", component_name="Demand Service Charge",
                charge_value=notice["demand"], charge_unit="$/kW/month", demand_unit="kW",
                effective_date=effective, source_url=notice_url,
                source_detail="Interim rates notice — For Commercial Customers (Non-Government)",
                confidence=conf,
                notes="Monthly demand service charge per kW; QEC may install a demand meter on any commercial service."))
        comps.append(RateComponent(
            component_type="energy", component_name="Energy Charge",
            charge_value=energy_rate, charge_unit="$/kWh", effective_date=effective,
            source_url=rates_url, source_detail="Customer Rates page (cents/kWh), cross-checked to interim notice",
            confidence=conf,
            notes=("Consumption above the NESP allowance, or without NESP eligibility, is billed at this full rate."
                   if code == "NG-RES" else None)))

        eligibility = None
        notes = status + rider
        if code == "NG-RES":
            summer, winter = page["nesp"]
            eligibility = "Residential customers not living in a public housing unit."
            for season, months, kwh in (("summer", "Apr-Sep", summer), ("winter", "Oct-Mar", winter)):
                comps.append(RateComponent(
                    component_type="rebate",
                    component_name=f"Nunavut Electricity Subsidy Program Allowance ({'April-September' if season == 'summer' else 'October-March'})",
                    charge_value=None, charge_unit="$/kWh", tier_number=1, tier_threshold=kwh,
                    tier_unit="kWh per 30-day period", season=season, season_months=months,
                    sub_component="conditional", effective_date=effective, source_url=rates_url,
                    source_detail="Customer Rates page — Non-Government Residential subsidy terms",
                    confidence=conf,
                    notes=(f"Conditional territorial subsidy on the first {kwh:,} kWh per 30-day period for an "
                           "eligible non-government residential customer, one residence only (one subsidized "
                           "account). The subsidized price per kWh is not published on the rate page, so no "
                           "value is shown; it is not an averaged discount. The FSR rider is not subsidized.")))
        elif code == "G-RES":
            eligibility = "Residential customers living in a government-owned public housing unit."
            notes += (" Public housing tenants under the User Pay Power Program are billed directly 6 cents/kWh; "
                      "the government is billed the remainder (base charge and metered usage at this rate), and "
                      "the full rate when the unit is unoccupied. The tenant arrangement is a billing condition, "
                      "not a separate tariff.")
        elif code in ("MT-RES", "MT-COM"):
            eligibility = ("Municipalities obtaining most operating costs through community tax revenue; "
                           "reclassification requires a regulatory application to the Minister responsible for QEC.")
            if code == "MT-COM":
                notes += " A base charge applies, but its municipal value is not published as text; no value is shown."
        elif code == "NG-COM":
            eligibility = ("Non-governmental commercial customers or business accounts, including mechanical rooms "
                           "for multiple units or dwellings and temporary construction service connections.")
        elif code == "G-COM":
            eligibility = "Commercial government accounts or government offices."
            notes += (" A base/demand charge applies, but the interim notice publishes only the non-government "
                      "demand service charge; no government value is shown.")

        return TariffRecord(
            utility_name=UTILITY, province="NU", utility_type="electricity",
            tariff_name=name, tariff_code=code, customer_class=cls, sub_class=sub,
            eligibility=eligibility,
            rate_structure="demand" if code == "NG-COM" else "flat",
            pricing_method="regulated", effective_date=effective,
            source_url=rates_url, source_page="Customer Rates page; Interim Electricity Rates notice",
            confidence=conf, notes=notes, components=comps,
        )

    def _seed_data(self) -> list[TariffRecord]:
        notice = {"service": SEED["residential_service_charge"], "demand": SEED["commercial_demand_charge"]}
        page = {"nesp": (SEED["nesp_summer_kwh"], SEED["nesp_winter_kwh"])}
        records = []
        for code in CLASS_INFO:
            record = self._build(code, SEED["effective_date"], SEED["energy"][code], notice, page,
                                 "October 1, 2023", "")
            record.confidence = "low"
            for comp in record.components:
                comp.confidence = "low"
            records.append(record)
        return records
