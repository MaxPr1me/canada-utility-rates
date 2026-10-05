"""
heritage_gas.py — Scraper for Heritage Gas rates (Nova Scotia).

Heritage Gas Limited provides natural gas distribution to parts of
Nova Scotia, including the Halifax Regional Municipality, Amherst,
and other communities.

Official sources:
  https://eastwardenergy.com/for-home/rates/       (residential summary)
  https://eastwardenergy.com/for-business/rates/   (class definitions and link to the monthly rate table PDF)

Nova Scotia gas rates are regulated by the Nova Scotia Energy Board (formerly
NSUARB).  Eastward Energy (formerly Heritage Gas) uses GJ as the billing unit.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

PAGE_URLS = {
    "residential": "https://eastwardenergy.com/for-home/rates/",
    "business": "https://eastwardenergy.com/for-business/rates/",
}

REGULATORY_URL = "https://eastwardenergy.com/regulatory/"

MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER",
          "OCTOBER", "NOVEMBER", "DECEMBER"]
MONEY = r"\$(\d[\d,]*\.\d+)"
DATE = r"([A-Z][a-z]+ \d{1,2}, \d{4})"

# Seed data — limited public rate information available.
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://eastwardenergy.com/for-home/rates/",
    "basic_charge_monthly": 20.00,              # $/month
    "delivery_rate": 10.50,                     # $/GJ — delivery/distribution
    "commodity_rate": 8.00,                     # $/GJ — gas supply (varies with market)
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
}


class HeritageGasScraper(BaseScraper):
    """Scrape Heritage Gas natural gas rates for Nova Scotia."""

    def __init__(self):
        super().__init__(utility_name="Heritage Gas", province="NS")

    def scrape(self) -> list[TariffRecord]:
        records = list(self._try_live_scrape() or [])
        if not any(record.customer_class == "residential" for record in records):
            self.logger.warning("Residential live parse unavailable — using unverified seed for Heritage Gas")
            records.extend(self.mark_fallback(self._seed_data()))
        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Fetch both rate pages and the monthly rate table they link to, then parse complete classes."""
        from scrapers.utils.parsing import extract_pdf_pages, parse_html

        pages: dict[str, str] = {}
        table_url = None
        for key, url in PAGE_URLS.items():
            try:
                soup = parse_html(self.fetch_page(url))
                pages[key] = (soup.find("main") or soup).get_text(" ", strip=True)
                for link in soup.find_all("a", href=True):
                    if link.get_text(" ", strip=True) == "View Rates" and link["href"].lower().endswith(".pdf"):
                        table_url = table_url or link["href"]
            except Exception as exc:
                self.logger.warning("Eastward Energy %s page unavailable: %s", key, exc)
        if table_url:
            try:
                pdf_pages = extract_pdf_pages(self.fetch_bytes(table_url))
                pages["rate_table"] = " ".join(page.text for page in pdf_pages)
            except Exception as exc:
                self.logger.warning("Eastward Energy rate table unavailable: %s", exc)
        tariff_url = None
        try:
            soup = parse_html(self.fetch_page(REGULATORY_URL))
            for link in soup.find_all("a", href=True):
                if link.get_text(" ", strip=True) == "Tariffs" and link["href"].lower().endswith(".pdf"):
                    tariff_url = link["href"]
                    break
            if tariff_url:
                pages["tariff"] = " ".join(p.text for p in extract_pdf_pages(self.fetch_bytes(tariff_url)))
        except Exception as exc:
            self.logger.warning("Eastward Energy tariff unavailable: %s", exc)
        records = self.parse_pages(pages, table_url=table_url, tariff_url=tariff_url)
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
    def _money(value: str) -> float:
        return float(value.replace(",", ""))

    def _row(self, table: str, label: str, columns: int = 3) -> list[float]:
        match = re.search(label + " " + " ".join([MONEY] * columns), table)
        if not match:
            raise ValueError(f"rate-table row missing or changed: {label}")
        return [self._money(value) for value in match.groups()]

    def _table(self, table: str, today: date) -> dict:
        """Strictly parse the monthly rate table; raises ValueError on any drift."""
        title = re.search(r"RATE TABLE (" + "|".join(MONTHS) + r") (\d{4})", table)
        if not title:
            raise ValueError("rate-table month missing")
        effective = date(int(title.group(2)), MONTHS.index(title.group(1)) + 1, 1)
        if effective > today:
            raise ValueError("future rate table")
        values = {"effective": effective}
        values["fixed"] = self._row(table, r"Fixed Monthly Customer Charge")
        base = re.search(r"Base Energy Charge \(\$/GJ\) " + MONEY + r" GS Tiers: " + MONEY, table)
        tiers = re.search(
            r"GS Tier 1 \(\S ?(\d+) GJs/month\) " + MONEY + r" GS Tier 2 \(> ?(\d+) - (\d+) GJs/month\) " + MONEY
            + r" GS Tier 3 \(> ?(\d+) GJs/month\) " + MONEY, table)
        if not base or not tiers:
            raise ValueError("base energy charge rows missing or changed")
        first, rate1, low2, high2, rate2, low3, rate3 = tiers.groups()
        if not (first == low2 and high2 == low3):
            raise ValueError("General Service tier boundaries are inconsistent")
        values["base_res"] = self._money(base.group(1))
        values["gs_tiers"] = [(self._money(rate1), float(first)), (self._money(rate2), float(high2)),
                              (self._money(rate3), None)]
        values["tcrr"] = self._row(table, r"Transportation Cost Recovery Rate\d? \(\$/GJ\)")
        values["gcrr"] = self._row(table, r"Gas Cost Recovery Rate\d? \(\$/GJ\)")
        values["carbon"] = self._row(table, r"Federal Carbon Tax\d? \(\$/GJ\)")
        values["rda"] = self._row(table, r"RDA Recovery Rate\d? \(\$/GJ\)")
        values["total"] = self._row(table, r"Total Variable \(\$/GJ\)")
        carbon_date = re.search(r"has been reduced to \$0/GJ by the Federal Government as of " + DATE, table)
        carbon_effective = self._long_date(carbon_date.group(1)) if carbon_date else None
        if any(values["carbon"]) or not carbon_effective or carbon_effective > today:
            raise ValueError("zero federal carbon charge and its effective date are not both published")
        values["carbon_date"] = carbon_effective
        riders = re.search(r"Municipal Taxes \(Rate Rider A: (\d+(?:\.\d+)?)% & Rate Rider B: (\d+(?:\.\d+)?)%\) "
                           r"are assessed on fixed monthly, base energy and demand charges", table)
        if not riders:
            raise ValueError("municipal tax riders A/B missing or changed")
        values["riders"] = (float(riders.group(1)), float(riders.group(2)))
        approval = re.search(r"Delivery Rates approved: " + DATE + r" - NSUARB Matter No\. (M\d+)", table)
        values["approval"] = f"{approval.group(1)}, NSUARB Matter No. {approval.group(2)}" if approval else None
        if min(values["fixed"][:2] + [values["base_res"], values["tcrr"][0], values["gcrr"][0], values["gcrr"][1]]) <= 0:
            raise ValueError("non-positive charge")
        for column, base_rate in ((0, values["base_res"]), (1, values["gs_tiers"][0][0])):
            parts = base_rate + values["tcrr"][column] + values["gcrr"][column] + values["rda"][column]
            if abs(parts - values["total"][column]) > 0.006:
                raise ValueError("published total variable rate does not reconcile with its components")
        return values

    def _summary(self, text: str, heading: str, fixed_label: str) -> tuple[date, float, float, float]:
        match = re.search(
            heading + r" as of " + DATE + r"\..{0,300}?" + fixed_label + r" " + MONEY + r" .{0,40}?Variable Charge per GJ "
            + MONEY + r" .{0,40}?Commodity Charge per GJ " + MONEY, text)
        effective = self._long_date(match.group(1)) if match else None
        if not effective:
            raise ValueError(f"'{heading}' summary missing or changed")
        return effective, self._money(match.group(2)), self._money(match.group(3)), self._money(match.group(4))

    def parse_pages(self, pages: dict[str, str], today: Optional[date] = None,
                    table_url: Optional[str] = None, tariff_url: Optional[str] = None) -> list[TariffRecord]:
        """Build tariffs from texts keyed residential/business/rate_table.

        The rate table is authoritative; each class must also agree with its page summary
        for the same effective date. Classes are parsed independently.
        """
        today = today or datetime.now(timezone.utc).date()
        pages = {key: self._norm(text) for key, text in pages.items()}
        try:
            values = self._table(pages.get("rate_table", ""), today)
        except ValueError as exc:
            self.logger.warning("Eastward Energy rate table not parsed live: %s", exc)
            return []
        if not table_url:
            self.logger.warning("Eastward Energy rate table URL missing")
            return []
        records: list[TariffRecord] = []
        try:
            summary = self._summary(pages.get("residential", ""), "Average Residential Rates",
                                    r"Fixed Delivery Charge per month")
            if summary != (values["effective"], values["fixed"][0], values["base_res"], values["gcrr"][0]):
                raise ValueError("residential page summary does not match the rate table")
            records.append(self._build(values, 0, table_url))
        except ValueError as exc:
            self.logger.warning("Eastward Energy residential not parsed live: %s", exc)
        try:
            business = pages.get("business", "")
            summary = self._summary(business, "Rates for General Service Class", r"Fixed Delivery Charge")
            if summary != (values["effective"], values["fixed"][1], values["gs_tiers"][0][0], values["gcrr"][1]):
                raise ValueError("General Service page summary does not match the rate table")
            definition = re.search(r"General Service: (Any Customer who is an end-user and whose rate class is not "
                                   r"either Residential, Rate Class 3, or Rate Class 4\.)", business)
            limit = re.search(r"Rate Class 3: Any Customer who is an end-user and whose total gas requirements at "
                              r"that location are greater than ([\d,]+) GJ per year", business)
            if not definition or not limit:
                raise ValueError("General Service class definition missing")
            records.append(self._build(values, 1, table_url, definition.group(1),
                                       float(limit.group(1).replace(",", ""))))
        except ValueError as exc:
            self.logger.warning("Eastward Energy General Service not parsed live: %s", exc)
        if pages.get("tariff"):
            try:
                if not tariff_url:
                    raise ValueError("tariff URL missing")
                rc3 = self._rc3(pages["rate_table"], pages["tariff"], pages.get("business", ""), values)
                records.append(self._build_rc3(values, rc3, table_url, tariff_url))
            except ValueError as exc:
                self.logger.warning("Eastward Energy Rate Class 3 not parsed live: %s", exc)
        return records

    def _rc3(self, table: str, tariff: str, business: str, values: dict) -> dict:
        """Cross-check the Rate Class 3 column against the approved tariff schedule; raises ValueError on drift."""
        base = re.search(r"Base Energy Charge \(\$/GJ\) " + MONEY + r" GS Tiers: " + MONEY, table)
        demand = re.search(r"RC3 Demand Charge " + MONEY, table)
        if not base or not demand:
            raise ValueError("Rate Class 3 base energy or demand row missing or changed")
        base_rate, demand_rate = self._money(base.group(2)), self._money(demand.group(1))
        schedule = re.search(
            r"Schedule 3 .{0,40}?Large General Service Rate Class 3 ELIGIBILITY Any Customer who is an end-user and "
            r"whose total gas requirements at that location are greater than ([\d,]+) GJ per year\..{0,1500}?"
            r"Effective for consumption on and after (January 1, 2024):\s*Fixed Monthly Customer Charge: \$ ?([\d.]+) per month "
            r"Base Energy Charge: \$ ?([\d.]+) per GJ Demand Charge \* \$ ?([\d.]+) per GJ of Billing Demand per month "
            r"\* The Billing Demand will be the greater of: 1\. 225 GJ per month 2\. The Contract Demand 3\. The greatest "
            r"amount of gas in GJ in any consecutive 24-hour period during the current and preceding eleven billing periods\. "
            r"MONTHLY BILL.{0,400}?MINIMUM MONTHLY BILL The Minimum Monthly Bill shall be the sum of the Fixed Monthly "
            r"Customer Charge plus the Demand Charge\.", tariff)
        if not schedule:
            raise ValueError("Rate Class 3 tariff schedule missing or changed")
        limit = float(schedule.group(1).replace(",", ""))
        if (self._money(schedule.group(3)), self._money(schedule.group(4)), self._money(schedule.group(5))) != (
                values["fixed"][2], base_rate, demand_rate):
            raise ValueError("rate table does not match the approved Rate Class 3 tariff")
        if not self._long_date(schedule.group(2)) <= values["effective"]:
            raise ValueError("tariff rates are not yet in effect")
        eligibility = re.search(r"Rate Class 3: (Any Customer who is an end-user and whose total gas requirements at that "
                                r"location are greater than ([\d,]+) GJ per year)", business)
        if not eligibility or float(eligibility.group(2).replace(",", "")) != limit:
            raise ValueError("Rate Class 3 eligibility missing or inconsistent with the tariff")
        parts = base_rate + values["tcrr"][2] + values["gcrr"][2] + values["rda"][2]
        if abs(parts - values["total"][2]) > 0.006:
            raise ValueError("published Rate Class 3 total variable does not reconcile with its components")
        return {"base": base_rate, "demand": demand_rate, "limit": limit, "eligibility": eligibility.group(1) + "."}

    def _build_rc3(self, values: dict, rc3: dict, url: str, tariff_url: str) -> TariffRecord:
        effective = values["effective"]
        eff = effective.isoformat()
        detail = f"Eastward Energy Rate Table {MONTHS[effective.month - 1].title()} {effective.year}"
        tariff_detail = "Eastward Energy Tariffs, Schedule 3 Large General Service Rate Class 3 (pages 9-10)"
        approval = f"; delivery rates approved {values['approval']}" if values["approval"] else ""

        def comp(kind, name, value, unit, source, source_detail, **kw):
            return RateComponent(kind, name, value, unit, effective_date=eff, source_url=source,
                                 source_detail=source_detail, **kw)

        comps = [
            comp("fixed", "Fixed Monthly Customer Charge", values["fixed"][2], "$/month", url, detail,
                 notes="Delivery charge regulated by the Nova Scotia Energy Board" + approval),
            comp("delivery", "Base Energy Charge", rc3["base"], "$/GJ", url, detail),
            comp("demand", "Demand Charge", rc3["demand"], "$/GJ of Billing Demand/month", tariff_url, tariff_detail,
                 notes="Billing Demand is the greater of 225 GJ per month, the Contract Demand, and the greatest amount "
                       "of gas in GJ in any consecutive 24-hour period during the current and preceding eleven billing "
                       "periods. Minimum monthly bill is the Fixed Monthly Customer Charge plus the Demand Charge."),
            comp("transmission", "Transportation Cost Recovery Rate", values["tcrr"][2], "$/GJ", url, detail),
            comp("commodity", "Gas Cost Recovery Rate", values["gcrr"][2], "$/GJ", url, detail,
                 market_reference="Eastward Energy gas cost recovery",
                 notes="Reviewed monthly and adjusted to current market pricing; passed through without mark-up."),
            comp("rider", "RDA Recovery Rate", values["rda"][2], "$/GJ", url, detail,
                 notes="Recovery of deferred Revenue Deficiency Account costs"),
            RateComponent("carbon", "Federal Carbon Tax", 0.0, "$/GJ", effective_date=values["carbon_date"].isoformat(),
                          source_url=url, source_detail=detail + ", note 4",
                          notes="Federal fuel charge reduced to $0/GJ as of "
                                f"{values['carbon_date'].strftime('%B')} {values['carbon_date'].day}, {values['carbon_date'].year}"),
        ]
        for letter, percent in zip("AB", values["riders"]):
            comps.append(comp("rider", f"Municipal Tax — Rate Rider {letter}", percent, "%", url, detail + ", note 6",
                              notes="Percentage assessed on fixed monthly, base energy and demand charges only, not on "
                                    "commodity, transportation or RDA rates"))
        return TariffRecord(
            utility_name="Heritage Gas", province="NS", utility_type="gas", tariff_name="Rate Class 3",
            tariff_code="RC3", customer_class="commercial", eligibility=rc3["eligibility"],
            usage_min=rc3["limit"], usage_unit="GJ/year", rate_structure="flat", pricing_method="regulated",
            effective_date=max(effective, values["carbon_date"]).isoformat(), source_url=url, source_page=detail,
            confidence="high",
            notes=("Eastward Energy (formerly Heritage Gas) Large General Service Rate Class 3; demand unit and billing "
                   "demand from the approved tariff. Published Total Variable excludes the demand charge. Rate Class 4 "
                   "rates are negotiated per site and not published. HST is not included."),
            components=comps,
        )

    def _build(self, values: dict, column: int, url: str, eligibility: Optional[str] = None,
               usage_max: Optional[float] = None) -> TariffRecord:
        effective = values["effective"]
        eff = effective.isoformat()
        detail = f"Eastward Energy Rate Table {MONTHS[effective.month - 1].title()} {effective.year}"
        residential = column == 0
        comps = [RateComponent(
            "fixed", "Fixed Monthly Customer Charge", values["fixed"][column], "$/month", effective_date=eff,
            source_url=url, source_detail=detail,
            notes="Delivery charge regulated by the Nova Scotia Energy Board"
                  + (f"; delivery rates approved {values['approval']}" if values["approval"] else ""))]
        if residential:
            comps.append(RateComponent("delivery", "Base Energy Charge", values["base_res"], "$/GJ",
                                       effective_date=eff, source_url=url, source_detail=detail))
        else:
            for number, (rate, threshold) in enumerate(values["gs_tiers"], start=1):
                comps.append(RateComponent(
                    "delivery", f"Base Energy Charge — GS Tier {number}", rate, "$/GJ", tier_number=number,
                    tier_threshold=threshold, tier_unit="GJ/month" if threshold else None, effective_date=eff,
                    source_url=url, source_detail=detail,
                    notes="Monthly volume block; threshold is the block's upper bound" if threshold else
                          "Monthly volume above the Tier 2 upper bound"))
        comps += [
            RateComponent("transmission", "Transportation Cost Recovery Rate", values["tcrr"][column], "$/GJ",
                          effective_date=eff, source_url=url, source_detail=detail),
            RateComponent("commodity", "Gas Cost Recovery Rate", values["gcrr"][column], "$/GJ", effective_date=eff,
                          source_url=url, source_detail=detail, market_reference="Eastward Energy gas cost recovery",
                          notes=("Biannual residential GCRR: a six-month forecast set August 1 and February 1, subject "
                                 "to interim adjustment" if residential else
                                 "Reviewed monthly and adjusted to current market pricing")
                          + "; passed through without mark-up."),
            RateComponent("rider", "RDA Recovery Rate", values["rda"][column], "$/GJ", effective_date=eff,
                          source_url=url, source_detail=detail,
                          notes="Recovery of deferred Revenue Deficiency Account costs"),
            RateComponent("carbon", "Federal Carbon Tax", 0.0, "$/GJ", effective_date=values["carbon_date"].isoformat(),
                          source_url=url, source_detail=detail + ", note 4",
                          notes="Federal fuel charge reduced to $0/GJ as of "
                                f"{values['carbon_date'].strftime('%B')} {values['carbon_date'].day}, {values['carbon_date'].year}"),
        ]
        for letter, percent in zip("AB", values["riders"]):
            comps.append(RateComponent(
                "rider", f"Municipal Tax — Rate Rider {letter}", percent, "%", effective_date=eff, source_url=url,
                source_detail=detail + ", note 6",
                notes="Percentage assessed on fixed monthly, base energy and demand charges only, not on commodity, "
                      "transportation or RDA rates"))
        return TariffRecord(
            utility_name="Heritage Gas", province="NS", utility_type="gas",
            tariff_name="Residential" if residential else "General Service",
            tariff_code="Residential" if residential else "GS",
            customer_class="residential" if residential else "commercial", eligibility=eligibility,
            usage_max=usage_max, usage_unit="GJ/year" if usage_max else None,
            rate_structure="flat" if residential else "tiered", pricing_method="regulated",
            effective_date=max(effective, values["carbon_date"]).isoformat(), source_url=url, source_page=detail,
            confidence="high",
            notes=("Eastward Energy (formerly Heritage Gas). Published in $/GJ. Rate Class 3 and Rate Class 4 are "
                   "separate classes for customers above the General Service limit. HST is not included."),
            components=comps,
        )

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Heritage Gas",
            province="NS",
            utility_type="gas",
            tariff_name="Residential — Small General Service",
            tariff_code="SGS",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="low",
            notes=(
                "Heritage Gas residential rate for Nova Scotia. "
                "Limited public rate data — values are approximate. "
                "Heritage Gas serves a small service area including Halifax "
                "and Amherst. Commodity rate varies with market conditions. "
                "Regulated by the NSUARB."
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
                    notes="Heritage Gas distribution charge for gas delivery",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Gas Supply Charge",
                    charge_value=SEED_RESIDENTIAL["commodity_rate"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="Gas commodity cost — varies with market conditions",
                    market_reference="Nova Scotia gas supply portfolio",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_RESIDENTIAL["carbon_charge"],
                    charge_unit="$/GJ",
                    confidence="low",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
            ],
        ))

        return records
