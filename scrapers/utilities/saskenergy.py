"""
saskenergy.py — Scraper for SaskEnergy natural gas rates (Saskatchewan).

SaskEnergy is Saskatchewan's Crown-owned natural gas distribution
utility, serving the entire province.

Official sources (HTML pages; the old /accounts-services/rates URL is dead):
  https://www.saskenergy.com/manage-account/rates/residential-rates
  https://www.saskenergy.com/manage-account/rates/business-rates
  https://www.saskenergy.com/manage-account/rates-fees-and-charges/federal-carbon-tax
  https://www.saskenergy.com/manage-account/rates/gas-retailers

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
