"""
saskenergy.py — Scraper for SaskEnergy natural gas rates (Saskatchewan).

SaskEnergy is Saskatchewan's Crown-owned natural gas distribution
utility, serving the entire province.

Official sources (HTML pages; the old /accounts-services/rates URL is dead):
  https://www.saskenergy.com/manage-account/rates/residential-rates
  https://www.saskenergy.com/manage-account/rates/business-rates
  https://www.saskenergy.com/manage-account/rates-fees-and-charges/federal-carbon-tax
  https://www.saskenergy.com/manage-account/rates/gas-retailers
  https://www.saskenergy.com/manage-account/rates-fees-and-charges/service-fees
  https://online.flippingbook.com/view/493513/45/ and /46/ (Terms and Conditions of
  Service Schedule, Appendix C - Tariff of Fees, linked from the service fees page)

Saskatchewan gas rates are regulated by the Saskatchewan Rate Review
Panel.  SaskEnergy uses m3 as the primary billing unit.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

BASE_URL = "https://www.saskenergy.com"
PAGE_URLS = {
    "residential": BASE_URL + "/manage-account/rates/residential-rates",
    "business": BASE_URL + "/manage-account/rates/business-rates",
    "carbon": BASE_URL + "/manage-account/rates-fees-and-charges/federal-carbon-tax",
    "retailers": BASE_URL + "/manage-account/rates/gas-retailers",
}
FEE_URLS = {
    "fees": BASE_URL + "/manage-account/rates-fees-and-charges/service-fees",
    "appendix_c": "https://online.flippingbook.com/view/493513/45/",
    "appendix_c_cont": "https://online.flippingbook.com/view/493513/46/",
}
# (name, page row label, Appendix C label, unit, after-hours fee published)
FEE_ROWS = [
    ("Tenancy Change Fee", "Tenancy Change", "Tenancy Change Fee", "$/tenancy change", True),
    ("Service Activation Fee", "Service Activation", "Service Activation Fee", "$/activation", True),
    ("Disconnection Fee", "Disconnection", "Disconnection Fee", "$/disconnection", True),
    ("Missed Appointment Fee", "Missed Appointment", "Missed Appointment Fee", "$/missed appointment", True),
    ("Meter Dispute Fee", "Meter Dispute", "Meter Dispute Fee", "$/meter dispute", False),
    ("Equipment Service Fee", "Equipment", "Equipment Service Fee", "$/service call", True),
    ("Multi-Suite Verification Fee", "Multi-Suite Verification", "Multi-Suite Verification Fee", "$/verification", True),
    ("Thermocouple Fee", "Thermocouple", "Thermocouple Fee", "$/service call", True),
]

# Seed data (2024, unverified fallback only — not current truth).
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": PAGE_URLS["residential"],
    "basic_charge_monthly": 23.50,              # $/month
    "commodity_rate": 0.2093,                   # $/m³ — gas commodity
    "delivery_rate": 0.0856,                    # $/m³ — delivery/distribution
    "carbon_charge": 0.1239,                    # $/m³ — federal carbon levy
    "rate_rider": 0.0035,                       # $/m³ — rate adjustment rider
}


class SaskEnergyScraper(BaseScraper):
    """Scrape SaskEnergy natural gas rates for Saskatchewan."""

    def __init__(self):
        super().__init__(utility_name="SaskEnergy", province="SK")

    def scrape(self) -> list[TariffRecord]:
        live = self._try_live_scrape() or []
        records = list(live)

        if not any(record.tariff_code == "Res" for record in records):
            self.logger.warning("Residential live parse unavailable — using unverified seed for SaskEnergy")
            records.extend(self.mark_fallback(self._seed_data()))
        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Fetch each official page independently and parse complete classes."""
        pages: dict[str, str] = {}
        for key, url in PAGE_URLS.items():
            try:
                pages[key] = self._page_text(self.fetch_page(url))
            except Exception as exc:
                self.logger.warning("SaskEnergy %s page unavailable: %s", key, exc)
        records = self.parse_pages(pages)
        fee_pages: dict[str, str] = {}
        for key, url in FEE_URLS.items():
            try:
                fee_pages[key] = self._page_text(self.fetch_page(url))
            except Exception as exc:
                self.logger.warning("SaskEnergy %s page unavailable: %s", key, exc)
        fees = self.parse_fees(fee_pages)
        if fees:
            records.append(fees)
        if not records:
            return None
        return self.mark_live_parsed(records)

    @staticmethod
    def _page_text(html: str) -> str:
        from scrapers.utils.parsing import parse_html
        soup = parse_html(html)
        node = soup.find("main") or soup
        return node.get_text(" ", strip=True)

    # ── Parsing ──────────────────────────────────────────────

    @staticmethod
    def _norm(text: str) -> str:
        text = text.replace("\xa0", " ")
        text = re.sub(r"\bm\s?[³3]", "m3", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _num(value: str) -> float:
        return float(value.replace(",", ""))

    @staticmethod
    def _date(value: str) -> Optional[date]:
        try:
            return datetime.strptime(value, "%B %d, %Y").date()
        except ValueError:
            return None

    def _effective(self, text: str, today: date) -> Optional[date]:
        match = re.search(r"Effective as of ([A-Z][a-z]+ \d{1,2}, \d{4})", text)
        effective = self._date(match.group(1)) if match else None
        return effective if effective and effective <= today else None

    def _service_rows(self, section: str) -> Optional[dict[str, Optional[dict[str, Optional[float]]]]]:
        amount = r"\$\s*(\d[\d,]*(?:\.\d+)?)"
        full = re.search(
            rf"Full Service Basic Monthly Charge ?: ?{amount} Delivery Charge ?: ?{amount} per m3 "
            rf"Commodity Rate ?: ?{amount} per m3(?: \({amount}/GJ\))?", section)
        if not full:
            return None
        if min(self._num(value) for value in full.groups() if value is not None) <= 0:
            return None
        out = {
            "full": {
                "basic": self._num(full.group(1)),
                "delivery": self._num(full.group(2)),
                "commodity": self._num(full.group(3)),
                "commodity_gj": self._num(full.group(4)) if full.group(4) else None,
            },
            "delivery_only": None,
        }
        delivery_only = re.search(
            rf"Delivery Service Basic Monthly Charge ?: ?{amount} Delivery Charge ?: ?{amount} per m3 "
            r"Commodity Rate ?: ?Gas Retailer Contract Price", section)
        if delivery_only and min(self._num(value) for value in delivery_only.groups()) > 0:
            out["delivery_only"] = {"basic": self._num(delivery_only.group(1)), "delivery": self._num(delivery_only.group(2))}
        return out

    def _industrial_rows(self, section: str) -> dict[str, object]:
        """Parse the closed Small Industrial full-service row with its monthly delivery blocks."""
        amount = r"\$\s*(\d[\d,]*(?:\.\d+)?)"
        closed = re.search(
            r"As of ([A-Z][a-z]+ \d{1,2}, \d{4}), this class is no longer accepting new customers\. "
            r"Existing customers \(prior to \1\) are eligible to maintain this service\.", section)
        closed_on = self._date(closed.group(1)) if closed else None
        if not closed_on:
            raise ValueError("closure/eligibility statement missing")
        full = re.search(
            rf"Full Service Basic Monthly Charge ?: ?{amount} Delivery Charge ?: ?First ([\d,]+) m3 ?/month ?: ?"
            rf"{amount} per m3 Remaining volumes ?: ?{amount} per m3 "
            rf"Commodity Rate ?: ?{amount} (?:per )?m3(?: \({amount}/GJ\))?", section)
        if not full:
            raise ValueError("incomplete Full Service block row or wrong unit")
        if min(self._num(value) for value in full.groups() if value is not None) <= 0:
            raise ValueError("non-positive published value")
        if not re.search(r"Small Industrial customers are not eligible to purchase gas from a Gas Retailer", section):
            raise ValueError("retailer eligibility statement missing")
        return {
            "basic": self._num(full.group(1)),
            "block": self._num(full.group(2)),
            "delivery": self._num(full.group(3)),
            "delivery_remaining": self._num(full.group(4)),
            "commodity": self._num(full.group(5)),
            "commodity_gj": self._num(full.group(6)) if full.group(6) else None,
            "closed_on": closed_on,
        }

    def _carbon(self, text: str, today: date) -> Optional[tuple[date, str]]:
        """Return (effective date, note) only for an explicit, current, zero published charge."""
        match = re.search(
            r"As of ([A-Z][a-z]+ \d{1,2}, \d{4}), SaskEnergy.s residential and commercial customer "
            r"classes will receive a zero charge for the Federal Carbon Tax", text)
        effective = self._date(match.group(1)) if match else None
        if not effective or effective > today:
            return None
        rows = re.findall(
            r"April (\d{4}) \S+ \$\s*([\d.]+) per tonne \(\$\s*([\d.]+) per cubic metre\)", text)
        if not rows or int(rows[-1][0]) != effective.year or any(float(value) != 0 for value in rows[-1][1:]):
            return None
        return effective, f"Published April {effective.year} schedule row: ${rows[-1][1]} per tonne ($0.0000 per cubic metre)"

    def parse_pages(self, pages: dict[str, str], today: Optional[date] = None) -> list[TariffRecord]:
        """Build tariffs from page texts keyed residential/business/carbon/retailers.

        Each class and each variant is isolated: one malformed class never
        discards another. Nothing is emitted unless the effective date, units
        and every required row are present.
        """
        today = today or datetime.now(timezone.utc).date()
        pages = {key: self._norm(text) for key, text in pages.items()}
        carbon = self._carbon(pages["carbon"], today) if pages.get("carbon") else None
        if carbon is None:
            self.logger.warning("SaskEnergy: required current carbon applicability could not be verified")
            return []
        retail = re.search(
            r"buy natural gas from an authorized Gas Retailer if your annual consumption is less than "
            r"([\d,]+) m3", pages.get("retailers", ""))
        retail_limit = self._num(retail.group(1)) if retail else None

        specs = [
            ("residential", None, "Residential", "Res", "residential", None),
            ("business", "Small Commercial", "Small Commercial", "SC", "commercial", "small"),
            ("business", "Large Commercial", "Large Commercial", "LC", "commercial", "large"),
            ("business", "Small Industrial", "Small Industrial", "SI", "industrial", "small"),
        ]
        records: list[TariffRecord] = []
        for page_key, label, name, code, cclass, sub in specs:
            try:
                text = pages.get(page_key, "")
                eff = self._effective(text, today)
                if not eff:
                    raise ValueError("missing or future effective date")
                umin = umax = None
                seg = text
                if label:
                    starts = [(match.start(), match.group(1), match.group(2)) for match in re.finditer(
                        r"(Small Commercial|Large Commercial|Small Industrial) The following rates "
                        r"apply if your annual gas consumption is ([^.]*?m3)\s*\.", text)]
                    idx = next((index for index, heading in enumerate(starts) if heading[1] == label), None)
                    if idx is None:
                        raise ValueError("class heading missing")
                    end = starts[idx + 1][0] if idx + 1 < len(starts) else len(text)
                    seg = text[starts[idx][0]:end]
                    elig = starts[idx][2]
                    lt = re.fullmatch(r"less than ([\d,]+) m3", elig)
                    rng = re.fullmatch(r"([\d,]+) to ([\d,]+) m3", elig)
                    if lt:
                        umax = self._num(lt.group(1))
                    elif rng:
                        umin, umax = self._num(rng.group(1)), self._num(rng.group(2))
                    else:
                        raise ValueError("unrecognised eligibility")
                if code == "SI":
                    if not umin:
                        raise ValueError("unrecognised eligibility")
                    records.append(self._build(name, code, cclass, sub, self._industrial_rows(seg), None, eff,
                                               PAGE_URLS[page_key], umin, umax, carbon, retail_limit))
                    continue
                rows = self._service_rows(seg)
                if not rows:
                    raise ValueError("incomplete Full Service row or wrong unit")
                records.append(self._build(name, code, cclass, sub, rows["full"], None, eff,
                                           PAGE_URLS[page_key], umin, umax, carbon, retail_limit))
                ds = rows["delivery_only"]
                if ds and retail_limit and (umax or retail_limit) <= retail_limit:
                    records.append(self._build(f"{name} - Delivery Service", f"{code}-DS", cclass, sub,
                                               None, ds, eff, PAGE_URLS[page_key], umin,
                                               umax or retail_limit, carbon, retail_limit))
            except ValueError as exc:
                self.logger.warning("SaskEnergy %s not parsed live: %s", name, exc)
        return records

    def parse_fees(self, pages: dict[str, str], today: Optional[date] = None) -> Optional[TariffRecord]:
        """Build the one-time service fee record from the service fees page and dated Appendix C.

        Values come from the service fees table; each fee is kept only when Appendix C
        (which carries the effective date) prints the same values for the same fee.
        """
        today = today or datetime.now(timezone.utc).date()
        page = self._norm(pages.get("fees", ""))
        appendix = self._norm(pages.get("appendix_c", "") + " " + pages.get("appendix_c_cont", ""))
        dated = re.search(r"APPENDIX C\W{0,3}\S{0,3}\W{0,3}TARIFF OF FEES EFFECTIVE ([A-Z][a-z]+ \d{1,2}, \d{4})", appendix)
        effective = self._date(dated.group(1)) if dated else None
        if (not effective or effective > today or "Terms and Conditions of Service Schedule" not in page
                or "Fee During Business Hours Fee After Hours" not in page
                or "Terms and Conditions of Service Schedule" not in appendix):
            self.logger.warning("SaskEnergy service fees not parsed live: dated Appendix C or fee table missing")
            return None
        eff_s = effective.isoformat()
        url = FEE_URLS["appendix_c"]
        detail = (f"Terms and Conditions of Service Schedule, Appendix C - Tariff of Fees effective "
                  f"{effective.strftime('%B')} {effective.day}, {effective.year}; values match the service fees page")

        def confirmed(label: str, sequence: str) -> bool:
            return any(sequence in appendix[m.end():m.end() + 160] for m in re.finditer(re.escape(label), appendix))

        comps: list[RateComponent] = []
        classes = r"(?:All Rate Classifications|Residential & Commercial Small Commercial Large & Industrial)"
        for name, row, label, unit, after_hours in FEE_ROWS:
            after = r"\$(\d[\d,]*(?:\.\d\d)?)" if after_hours else "N/A"
            match = re.search(rf"(?<![\w-]){re.escape(row)} {classes} \$(\d[\d,]*(?:\.\d\d)?)"
                              rf"(?: \$(\d[\d,]*(?:\.\d\d)?))? {after}(?: {after})?(?= |$)", page)
            if not match:
                self.logger.warning("SaskEnergy %s not parsed live: row missing", name)
                continue
            values = [self._num(v) for v in match.groups() if v is not None]
            # Two-group rows list both business-hours cells before both after-hours cells.
            if match.group(2) is not None:
                business = values[:2]
                after_values = values[2:]
            else:
                business = values[:1]
                after_values = values[1:]
            if len(set(business)) != 1 or len(set(after_values)) > 1 or min(values) <= 0:
                self.logger.warning("SaskEnergy %s not parsed live: class-specific or non-positive fee", name)
                continue
            fee = business[0]
            late = after_values[0] if after_values else None
            sequence = f"${fee:g} ${late:g}" if late is not None else f"${fee:g} N/A"
            if not confirmed(label, sequence):
                self.logger.warning("SaskEnergy %s not parsed live: Appendix C does not confirm %s", name, sequence)
                continue
            comps.append(RateComponent(
                "other", f"{name} - Business Hours", fee, unit, sub_component="business hours",
                effective_date=eff_s, source_url=url, source_detail=detail,
                notes="One-time fee per occurrence when the service is performed during business hours."))
            if late is not None:
                comps.append(RateComponent(
                    "other", f"{name} - After Hours", late, unit, sub_component="after hours",
                    effective_date=eff_s, source_url=url, source_detail=detail,
                    notes="Conditional alternative: replaces the business-hours fee only when the service is "
                          "performed after business hours."))

        late_payment = re.search(r"Late Payment All Rate Classifications (\d+(?:\.\d+)?)% interest rate per month, "
                                 r"or (\d+(?:\.\d+)?)% per year", page)
        if late_payment and re.search(
                rf"payable to SaskEnergy on all SaskEnergy accounts is {float(late_payment.group(1)):.1f}% per Month, "
                rf"compounded monthly, or {re.escape(late_payment.group(2))}% per annum", appendix):
            comps.append(RateComponent(
                "other", "Late Payment Charge", round(float(late_payment.group(1)) / 100, 6), "fraction/month",
                effective_date=eff_s, source_url=url, source_detail=detail,
                notes=f"Interest on overdue balances only: {late_payment.group(1)}% per month compounded monthly "
                      f"({late_payment.group(2)}% per year)."))
        else:
            self.logger.warning("SaskEnergy Late Payment Charge not parsed live")
        for name, row, unit, wording in (
            ("Return Payment Fee", "Return Payment", "$/returned payment", "for each returned payment"),
            ("Dispute Resolution Fee", "Dispute Resolution", "$/application", "for each application"),
        ):
            match = re.search(rf"{row} All Rate Classifications \$(\d+(?:\.\d\d)?) {wording}", page)
            value = self._num(match.group(1)) if match else 0
            if value <= 0 or f"The {name} is ${value:.2f} {wording}" not in appendix:
                self.logger.warning("SaskEnergy %s not parsed live", name)
                continue
            comps.append(RateComponent(
                "other", name, value, unit, effective_date=eff_s, source_url=url, source_detail=detail,
                notes=f"One-time fee {wording}."))
        if not comps:
            return None
        return TariffRecord(
            utility_name="SaskEnergy", province="SK", utility_type="gas",
            tariff_name="Service Fees (Terms and Conditions Appendix C)", tariff_code="T&C-C",
            customer_class="other", sub_class="service fees", rate_structure="flat", pricing_method="regulated",
            effective_date=eff_s, source_url=url, source_page="Appendix C - Tariff of Fees", confidence="high",
            notes=("One-time service and account fees that apply across rate classes under the Terms and Conditions of "
                   "Service Schedule; not recurring gas charges and never part of a monthly bill estimate. After-hours "
                   "fees are alternatives to the business-hours fee. Safety services (no charge), emergency/facility "
                   "damage and custom services (variable charge basis) and deposits are not priced."),
            components=comps,
        )

    def _build(
        self, name: str, code: str, cclass: str, sub: Optional[str],
        full: Optional[dict], delivery_only: Optional[dict[str, Optional[float]]],
        eff: date, url: str, umin: Optional[float], umax: Optional[float],
        carbon: tuple[date, str], retail_limit: Optional[float],
    ) -> TariffRecord:
        vals = full or delivery_only
        eff_s = eff.isoformat()
        detail = f"Effective as of {eff.strftime('%B')} {eff.day}, {eff.year}"
        comps = [
            RateComponent("fixed", "Basic Monthly Charge", vals["basic"], "$/month",
                          effective_date=eff_s, source_url=url, source_detail=detail,
                          notes="Minimum bill equals the Basic Monthly Charge"),
        ]
        block = vals.get("block")
        if block:
            comps += [
                RateComponent("delivery", "Delivery Charge - First Block", vals["delivery"], "$/m³",
                              tier_number=1, tier_threshold=block, tier_unit="m³/month",
                              effective_date=eff_s, source_url=url, source_detail=detail,
                              notes=f"First {block:,.0f} m³ per month"),
                RateComponent("delivery", "Delivery Charge - Remaining Volumes", vals["delivery_remaining"], "$/m³",
                              tier_number=2, tier_threshold=block, tier_unit="m³/month",
                              effective_date=eff_s, source_url=url, source_detail=detail,
                              notes=f"Monthly volumes above {block:,.0f} m³"),
            ]
        else:
            comps.append(RateComponent("delivery", "Delivery Charge", vals["delivery"], "$/m³",
                                       effective_date=eff_s, source_url=url, source_detail=detail))
        if full:
            gj = f" Published as ${full['commodity_gj']:.2f}/GJ." if full["commodity_gj"] is not None else ""
            comps.append(RateComponent(
                "commodity", "Commodity Charge", full["commodity"], "$/m³",
                effective_date=eff_s, source_url=url, source_detail=detail,
                notes="SaskEnergy gas supply (Gas Consumption Charge)." + gj))
        notes = ("SaskEnergy full service: SaskEnergy supplies gas. " if full else
                 "Delivery service only: commodity is the Gas Retailer contract price (negotiated, not "
                 "published, not included). Retailer access requires annual consumption below "
                 f"{retail_limit:,.0f} m³. ")
        carbon_date, carbon_note = carbon
        if full and full.get("closed_on"):
            closed_on = full["closed_on"]
            notes += (f"Closed class: not accepting new customers since {closed_on.isoformat()}; customers served "
                      "before that date may keep it until their contract ends. New firm delivery above 660,000 m³/year "
                      "is TransGas service (not priced here). Not eligible for Gas Retailer supply. ")
            carbon_note += (". SaskEnergy's zero-charge statement names residential and commercial classes; this "
                            "industrial value is the page's published April schedule row for Part I natural gas")
        comps.append(RateComponent(
            "carbon", "Federal Carbon Charge", 0.0, "$/m³",
            effective_date=carbon_date.isoformat(), source_url=PAGE_URLS["carbon"],
            source_detail="Federal Carbon Charge Amendment", notes=carbon_note))
        elig = None
        if umax:
            elig = (f"Annual consumption {umin:,.0f} to {umax:,.0f} m³" if umin
                    else f"Annual consumption below {umax:,.0f} m³")
        if full and full.get("closed_on"):
            elig += f"; existing customers served before {full['closed_on'].isoformat()} only"
        return TariffRecord(
            utility_name="SaskEnergy", province="SK", utility_type="gas", tariff_name=name,
            tariff_code=code, customer_class=cclass, sub_class=sub,
            eligibility=elig,
            usage_min=umin, usage_max=umax, usage_unit="m³/year" if umax else None,
            rate_structure="tiered" if block else "flat", pricing_method="regulated", effective_date=max(eff, carbon_date).isoformat(),
            source_url=url, source_page=detail, confidence="high",
            notes=notes + "Regulated by the Saskatchewan Rate Review Panel. GST/PST and municipal payments are separate.",
            components=comps,
        )

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="SaskEnergy",
            province="SK",
            utility_type="gas",
            tariff_name="Residential",
            tariff_code="Res",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="high",
            notes=(
                "SaskEnergy residential natural gas rate. "
                "SaskEnergy is a Saskatchewan Crown corporation providing "
                "gas distribution across the entire province. "
                "Rates in $/m3. "
                "Regulated by the Saskatchewan Rate Review Panel."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Basic Monthly Charge",
                    charge_value=SEED_RESIDENTIAL["basic_charge_monthly"],
                    charge_unit="$/month",
                    confidence="high",
                    notes="Fixed monthly customer charge",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Commodity Charge",
                    charge_value=SEED_RESIDENTIAL["commodity_rate"],
                    charge_unit="$/m³",
                    confidence="high",
                    notes="Natural gas commodity cost — largest volumetric component",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Delivery Charge",
                    charge_value=SEED_RESIDENTIAL["delivery_rate"],
                    charge_unit="$/m³",
                    confidence="high",
                    notes="SaskEnergy distribution charge for gas delivery",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_RESIDENTIAL["carbon_charge"],
                    charge_unit="$/m³",
                    confidence="high",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Rate Rider",
                    charge_value=SEED_RESIDENTIAL["rate_rider"],
                    charge_unit="$/m³",
                    confidence="high",
                    notes="Rate adjustment rider — periodic true-up",
                ),
            ],
        ))

        return records
