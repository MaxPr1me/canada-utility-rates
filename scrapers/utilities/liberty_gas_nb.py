"""
liberty_gas_nb.py — Scraper for Liberty Utilities gas rates (New Brunswick).

Liberty Utilities provides natural gas distribution in parts of
New Brunswick, serving a relatively small service area.

Official sources:
  https://naturalgasnb.com/en/for-home/accounts-billing/customer-rate-classes/      (distribution rates, all classes)
  https://naturalgasnb.com/en/for-home/accounts-billing/our-product-offering/       (Liberty Utility Gas commodity)
  https://naturalgasnb.com/en/for-business/accounts-and-billing/our-product-offering/
  https://www.canada.ca/en/revenue-agency/services/forms-publications/publications/fcrates/fuel-charge-rates.html

New Brunswick gas rates are regulated by the Energy and Utilities
Board of New Brunswick (EUB NB).  Liberty uses GJ as the primary
billing unit.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

PAGE_URLS = {
    "classes": "https://naturalgasnb.com/en/for-home/accounts-billing/customer-rate-classes/",
    "home_supply": "https://naturalgasnb.com/en/for-home/accounts-billing/our-product-offering/",
    "business_supply": "https://naturalgasnb.com/en/for-business/accounts-and-billing/our-product-offering/",
    "carbon": (
        "https://www.canada.ca/en/revenue-agency/services/forms-publications/"
        "publications/fcrates/fuel-charge-rates.html"
    ),
}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
DATE = r"([A-Z][a-z]+ \d{1,2}, \d{4})"
RATE = r"(\d[\d,]*\.\d{2,4})"

# Seed data — limited public rate information available.
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://naturalgasnb.com/en/for-home/accounts-billing/customer-rate-classes/",
    "basic_charge_monthly": 18.00,              # $/month
    "delivery_rate": 7.00,                      # $/GJ — delivery/distribution
    "commodity_rate": 6.50,                     # $/GJ — gas supply (market-linked)
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
    "rate_rider": 0.0250,                       # $/GJ — periodic adjustment
}


class LibertyGasNBScraper(BaseScraper):
    """Scrape Liberty Utilities natural gas rates for New Brunswick."""

    def __init__(self):
        super().__init__(utility_name="Liberty Utilities Gas NB", province="NB")

    def scrape(self) -> list[TariffRecord]:
        records = list(self._try_live_scrape() or [])
        if not any(record.customer_class == "residential" for record in records):
            self.logger.warning("Residential live parse unavailable — using unverified seed for Liberty Utilities Gas NB")
            records.extend(self.mark_fallback(self._seed_data()))
        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Fetch each official page independently and parse complete building classes."""
        from scrapers.utils.parsing import parse_html

        pages: dict[str, str] = {}
        for key, url in PAGE_URLS.items():
            try:
                soup = parse_html(self.fetch_page(url))
                pages[key] = (soup.find("main") or soup).get_text(" ", strip=True)
            except Exception as exc:
                self.logger.warning("Liberty NB %s page unavailable: %s", key, exc)
        records = self.parse_pages(pages)
        return self.mark_live_parsed(records) if records else None

    # ── Parsing ──────────────────────────────────────────────

    @staticmethod
    def _norm(text: str) -> str:
        return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()

    @staticmethod
    def _long_date(value: str) -> Optional[date]:
        try:
            return datetime.strptime(value, "%B %d, %Y").date()
        except ValueError:
            return None

    @staticmethod
    def _num(value: str) -> float:
        return float(value.replace(",", ""))

    def _carbon(self, text: str, today: date) -> Optional[tuple[date, str]]:
        """Explicit federal zero fuel charge, with New Brunswick's charge period ending March 31, 2025."""
        zero = re.search(
            r"Fuel charge rates \S{1,2} Beginning " + DATE + r" On [A-Z][a-z]+ \d{1,2}, \d{4}, the Government of "
            r"Canada made regulations that cease the application of the federal fuel charge, by setting all fuel "
            r"charge rates to zero", text)
        nb_ended = re.search(r"the rates applied in New Brunswick from April 1, 2019 to March 31, 2020, and from "
                             r"July 1, 2023 to March 31, 2025", text)
        effective = self._long_date(zero.group(1)) if zero else None
        if not effective or not nb_ended or effective > today:
            return None
        return effective, (f"Canada Revenue Agency fuel charge rates, beginning {zero.group(1)}: all federal fuel "
                           "charge rates set to zero; New Brunswick's charge applied until March 31, 2025. "
                           "Liberty's rate pages publish no carbon row.")

    def _commodity(self, text: str, today: date) -> Optional[tuple[date, float]]:
        """Current month's Liberty Utility Gas rate from the year-column history table."""
        if "The Liberty Utility Gas rate for the current month may change monthly" not in text:
            return None
        header = re.search(r"UTILITY GAS RATE HISTORY \(\$/GJ\) ((?:\d{4} )+)", text)
        if not header:
            return None
        years = header.group(1).split()
        month = MONTHS[today.month - 1]
        row = re.search(rf"{month} ((?:\d+\.\d{{2}} ?)+)", text[header.end():])
        if years[0] != str(today.year) or not row or len(row.group(1).split()) != len(years):
            return None
        value = float(row.group(1).split()[0])
        return (date(today.year, today.month, 1), value) if value > 0 else None

    @staticmethod
    def _detail(text: str, heading: str) -> str:
        start = text.find(f"{heading} Applicability ")
        if start < 0:
            raise ValueError(f"{heading} detail section missing")
        end = text.find(" Applicability ", start + len(heading) + 15)
        return text[start:end if end > 0 else len(text)]

    def _class_values(self, text: str, code: str) -> tuple[dict, str]:
        """Summary-table values for one class, confirmed by its own rate-schedule section."""
        patterns = {
            "SGS": (r"Small General Service - - " + RATE + r" N/A " + RATE + r" Mid-General Service", "Small General Service"),
            "MGS": (r"Mid-General Service - < 250 GJ For Customers with maximum consumption up to (\d+) GJs per month: "
                    + RATE + r" For Customers with maximum consumption greater than (\d+) GJs per month: " + RATE
                    + r" N/A For the first (\d+) GJs delivered per month: " + RATE + r" For volumes delivered in "
                    r"excess of (\d+) GJs per month: " + RATE + r" Large General Service", "Mid-General Service"),
            "LGS": (r"Large General Service 250 GJ - For Customers with maximum consumption up to (\d+) GJs per month: "
                    + RATE + r" For Customers with maximum consumption greater than (\d+) GJs per month: " + RATE
                    + r" N/A For the first (\d+) GJs delivered per month: " + RATE + r" For volumes delivered in "
                    r"excess of (\d+) GJs per month - between September 1 and April 30: " + RATE
                    + r" - between May 1 and Aug 31: " + RATE + r" Contract General Service", "Large General Service"),
        }
        pattern, heading = patterns[code]
        match = re.search(pattern, text)
        if not match:
            raise ValueError("summary-table row missing or changed")
        groups = match.groups()
        detail = self._detail(text, heading)
        rates = [value for value in groups if "." in value]
        if not all(value in detail for value in rates):
            raise ValueError("rate-schedule section does not repeat the summary-table rates")
        if min(self._num(value) for value in groups) <= 0:
            raise ValueError("non-positive charge or threshold")
        if code != "SGS" and not (groups[0] == groups[2] and groups[4] == groups[6]):
            raise ValueError("threshold boundaries are inconsistent")
        return {"groups": [self._num(value) for value in groups]}, detail

    def _ops_values(self, text: str, detail_text: str) -> tuple[list[float], str]:
        """Off-Peak summary row, confirmed by its own rate-schedule section (which may be a separate text)."""
        row = re.search(r"Off-Peak N/A N/A " + RATE + r" N/A " + RATE + r"(?: |$)", text)
        if not row:
            raise ValueError("summary-table row missing or changed")
        detail = self._detail(detail_text, "Off-Peak Service")
        fixed = re.search(r"Monthly Distribution Customer Charge \(\$ per Month\): " + RATE, detail)
        delivery = re.search(r"Monthly Distribution Delivery Charge \(\$ per GJ\): For all volumes delivered per month: "
                             + RATE, detail)
        if not fixed or not delivery or (fixed.group(1), delivery.group(1)) != row.groups():
            raise ValueError("rate-schedule section does not repeat the summary-table rates")
        values = [self._num(value) for value in row.groups()]
        if min(values) <= 0:
            raise ValueError("non-positive charge")
        return values, detail

    def parse_pages(self, pages: dict[str, str], today: Optional[date] = None) -> list[TariffRecord]:
        """Build SGS/MGS/LGS/OPS from texts keyed classes/home_supply/business_supply/carbon (optional ops).

        Missing carbon evidence rejects everything; each class is otherwise isolated.
        """
        today = today or datetime.now(timezone.utc).date()
        pages = {key: self._norm(text) for key, text in pages.items()}
        carbon = self._carbon(pages.get("carbon", ""), today)
        if carbon is None:
            self.logger.warning("Liberty NB: required current carbon applicability could not be verified")
            return []
        text = pages.get("classes", "")
        effective_match = re.search(r"rates and charges are effective as of " + DATE + r"\.", text)
        effective = self._long_date(effective_match.group(1)) if effective_match else None
        if not effective or effective > today:
            self.logger.warning("Liberty NB: distribution effective date missing or in the future")
            return []
        records: list[TariffRecord] = []
        for code, supply_key in (("SGS", "home_supply"), ("MGS", "business_supply"), ("LGS", "business_supply"),
                                 ("OPS", "business_supply")):
            try:
                if code == "OPS":
                    groups, detail = self._ops_values(text, pages.get("ops", text))
                    values = {"groups": groups}
                else:
                    values, detail = self._class_values(text, code)
                bills = re.search(r"Effective Date: To apply to all bills rendered for natural gas delivered on and "
                                  r"after " + DATE, detail)
                if not bills or self._long_date(bills.group(1)) != effective:
                    raise ValueError("rate-schedule effective date differs from the summary table")
                commodity = self._commodity(pages.get(supply_key, ""), today)
                if commodity is None:
                    raise ValueError("current Liberty Utility Gas rate missing")
                records.append(self._build(code, values["groups"], detail, effective, commodity, supply_key, carbon))
            except ValueError as exc:
                self.logger.warning("Liberty NB %s not parsed live: %s", code, exc)
        return records

    def _build(self, code: str, groups: list[float], detail: str, effective: date, commodity: tuple[date, float],
                supply_key: str, carbon: tuple[date, str]) -> TariffRecord:
        url = PAGE_URLS["classes"]
        eff = effective.isoformat()
        source = f"Current Natural Gas Distribution Rates & Charges, effective {effective.strftime('%B')} {effective.day}, {effective.year}"
        names = {"SGS": "Residential — Small General Service", "MGS": "Commercial — Mid-General Service",
                 "LGS": "Commercial — Large General Service", "OPS": "Commercial — Off-Peak Service"}

        def comp(kind: str, name: str, value: float, unit: str, **extra) -> RateComponent:
            return RateComponent(kind, name, value, unit, effective_date=eff, source_url=url, source_detail=source, **extra)

        if code == "SGS":
            comps = [comp("fixed", "Monthly Distribution Customer Charge", groups[0], "$/month"),
                     comp("delivery", "Monthly Distribution Delivery Charge", groups[1], "$/GJ")]
            eligibility = ("Dwellings, dwelling outbuildings and individually gas-metered self-contained dwelling units "
                           "within an apartment building, served through one meter.")
            if "individually gas metered, self-contained dwelling units within an apartment building" not in detail:
                raise ValueError("SGS dwelling definition missing")
        elif code == "OPS":
            comps = [comp("fixed", "Monthly Distribution Customer Charge", groups[0], "$/month"),
                     comp("delivery", "Monthly Distribution Delivery Charge", groups[1], "$/GJ")]
            sentence = re.search(r"The Off-Peak Service \(OPS\) Rates are applied to any customer requiring the use of "
                                 r"Liberty's Distribution System to have a supply of natural gas delivered to a single "
                                 r"location served through one meter for the months of April through November\.", detail)
            overrun = re.search(r"Seasonal Overrun Charge: Any volume of natural gas consumed during the months of "
                                r"December through March inclusively will be subject to a Seasonal Overrun Charge of "
                                r"\$10 per GJ in addition to the rates applicable to this service\.", detail)
            if not sentence or not overrun or "There is no minimum annual charge." not in detail:
                raise ValueError("Off-Peak eligibility or seasonal terms missing")
            eligibility = sentence.group(0)
        else:
            low, fixed_low, _, fixed_high, block, rate1, _, *rest = groups
            comps = [
                comp("fixed", "Monthly Distribution Customer Charge", fixed_low, "$/month", sub_component="conditional",
                     notes=f"Alternative: applies when maximum monthly consumption is up to {low:.0f} GJ"),
                comp("fixed", "Monthly Distribution Customer Charge (higher consumption)", fixed_high, "$/month",
                     sub_component="conditional",
                     notes=f"Alternative: applies when maximum monthly consumption is greater than {low:.0f} GJ"),
                comp("delivery", "Monthly Distribution Delivery Charge — Block 1", rate1, "$/GJ", tier_number=1,
                     tier_threshold=block, tier_unit="GJ/month", notes=f"First {block:.0f} GJ delivered per month"),
            ]
            if code == "MGS":
                comps.append(comp("delivery", "Monthly Distribution Delivery Charge — Block 2", rest[0], "$/GJ",
                                  tier_number=2, notes=f"Volumes in excess of {block:.0f} GJ per month"))
                sentence = re.search(r"Service is limited to customers with a consumption less than (\d+) GJs per month\.", detail)
            else:
                for value, season, months in ((rest[0], "winter", "Sep-Apr"), (rest[1], "summer", "May-Aug")):
                    comps.append(comp("delivery", f"Monthly Distribution Delivery Charge — Block 2 ({months})", value,
                                      "$/GJ", tier_number=2, season=season, season_months=months,
                                      notes=f"Volumes in excess of {block:.0f} GJ per month delivered {months}"))
                sentence = re.search(r"Service is limited to customers with a consumption of at least (\d+) GJs per "
                                     r"billing month\.", detail)
            if not sentence:
                raise ValueError("monthly consumption eligibility sentence missing")
            eligibility = sentence.group(0)
        supply_date, supply_value = commodity
        carbon_date, carbon_note = carbon
        comps += [
            RateComponent("commodity", "Liberty Utility Gas", supply_value, "$/GJ", effective_date=supply_date.isoformat(),
                          source_url=PAGE_URLS[supply_key], source_detail="Utility Gas Rate History ($/GJ)",
                          market_reference="Liberty Utility Gas (LUG)",
                          notes="Optional utility supply at cost, may change monthly; customers may buy from a marketer "
                                "instead, whose price is not included."),
            RateComponent("carbon", "Federal Carbon Charge", 0.0, "$/GJ", effective_date=carbon_date.isoformat(),
                          source_url=PAGE_URLS["carbon"], source_detail="CRA fuel charge rates", notes=carbon_note),
        ]
        minimum = (" Minimum annual charge applies if qualifying monthly consumption is not met (difference versus "
                   "Mid-General Service plus 5%)." if code == "LGS" else "")
        if code == "OPS":
            minimum = (" No minimum annual charge. Seasonal Overrun Charge: volume consumed December through March is "
                       "subject to $10 per GJ in addition to the rates for this service (not added to the components). "
                       "Term of service: one year with automatic annual renewal. The page does not restrict OPS to "
                       "commercial customers; it applies to any customer using gas only April through November.")
        return TariffRecord(
            utility_name="Liberty Utilities Gas NB", province="NB", utility_type="gas", tariff_name=names[code],
            tariff_code=code, customer_class="residential" if code == "SGS" else "commercial", eligibility=eligibility,
            rate_structure="flat" if code in ("SGS", "OPS") else "tiered",
            pricing_method="regulated", effective_date=max(effective, supply_date, carbon_date).isoformat(),
            source_url=url, source_page=source, confidence="high",
            notes=("Minimum monthly charge is the customer charge." + minimum + " Distribution rates are subject to "
                   "tax adjustments including HST, which are not included. Regulated by the EUB NB."),
            components=comps,
        )

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Liberty Utilities Gas NB",
            province="NB",
            utility_type="gas",
            tariff_name="Residential — Small General Service",
            tariff_code="SGS",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="low",
            notes=(
                "Liberty Utilities residential gas rate for New Brunswick. "
                "Small service area — limited public rate data available. "
                "Commodity rate is market-linked and varies. "
                "Regulated by the EUB NB."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="low",
                    notes="Fixed monthly customer charge",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Delivery Charge",
                    charge_value=SEED_RESIDENTIAL["delivery_rate"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="Liberty distribution charge for gas delivery",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Gas Supply Charge",
                    charge_value=SEED_RESIDENTIAL["commodity_rate"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="Gas commodity cost — market-linked, varies periodically",
                    market_reference="New Brunswick gas supply portfolio",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_RESIDENTIAL["carbon_charge"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Rate Rider",
                    charge_value=SEED_RESIDENTIAL["rate_rider"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="Periodic rate adjustment rider",
                ),
            ],
        ))

        return records
