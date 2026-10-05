"""
energir.py — Scraper for Energir natural gas rates (Quebec).

Energir (formerly Gaz Metro) is the primary natural gas distributor
in Quebec, serving residential and commercial customers.

Official sources:
  https://energir.com/en/residential/customer-centre/billing-and-pricing/pricing
      (links the current Conditions of Service and Tariff PDF)
  Conditions of Service and Tariff PDF: supply (11), transportation (12), load
  balancing (13), Rate D1 distribution (14.2) and cap-and-trade (15) prices.

Quebec gas rates are regulated by the Regie de l'energie. Prices are published
in cents per m3 and stored as $/m3 (a plain /100 conversion; no heat-content
conversion is performed).
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)

PAGE_URLS = {
    "pricing": "https://energir.com/en/residential/customer-centre/billing-and-pricing/pricing",
}
DATE = r"([A-Z][a-z]+ \d{1,2}, \d{4})"
CENTS = r"(\d+\.\d{3})¢/m³"
VOLUME = r"(\d[\d,]*)"

# Seed data based on Regie-approved rates.
SEED_RESIDENTIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.energir.com/en/residential/billing-and-rates/rates/",
    "customer_charge_monthly": 15.29,           # $/month
    "distribution_rate": 0.5085,                # $/GJ
    "supply_rate": 4.3500,                      # $/GJ — varies with market
    "transportation_rate": 0.2150,              # $/GJ
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
    "load_balancing_rider": 0.0340,             # $/GJ
}

SEED_COMMERCIAL = {
    "effective_date": "2024-10-01",
    "source_url": "https://www.energir.com/en/residential/billing-and-rates/rates/",
    "customer_charge_monthly": 30.00,           # $/month
    "distribution_rate": 0.3714,                # $/GJ
    "supply_rate": 4.3500,                      # $/GJ — varies with market
    "transportation_rate": 0.2150,              # $/GJ
    "carbon_charge": 3.3220,                    # $/GJ — federal carbon levy
    "demand_charge": 3.75,                      # $/GJ of peak demand
}


class EnergirScraper(BaseScraper):
    """Scrape Energir natural gas rates for Quebec."""

    def __init__(self):
        super().__init__(utility_name="Energir", province="QC")

    def scrape(self) -> list[TariffRecord]:
        records = list(self._try_live_scrape() or [])
        if not records:
            self.logger.warning("Rate D1 live parse unavailable — using unverified seed for Energir")
            records.extend(self.mark_fallback(self._seed_data()))
        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        """Fetch the pricing page, follow its current tariff PDF link and parse Rate D1."""
        from scrapers.utils.parsing import extract_pdf_pages, parse_html

        try:
            soup = parse_html(self.fetch_page(PAGE_URLS["pricing"]))
        except Exception as exc:
            self.logger.warning("Energir pricing page unavailable: %s", exc)
            return None
        tariff_url = next((link["href"] for link in soup.find_all("a", href=True)
                           if link.get_text(" ", strip=True).startswith("Conditions of Service and Tariff effective")
                           and link["href"].lower().endswith(".pdf")), None)
        if not tariff_url:
            self.logger.warning("Energir current tariff PDF link not found")
            return None
        try:
            tariff = " ".join(page.text for page in extract_pdf_pages(self.fetch_bytes(tariff_url)))
        except Exception as exc:
            self.logger.warning("Energir tariff PDF unavailable: %s", exc)
            return None
        pricing = (soup.find("main") or soup).get_text(" ", strip=True)
        records = self.parse_pages({"pricing": pricing, "tariff": tariff}, tariff_url=tariff_url)
        return self.mark_live_parsed(records) if records else None

    # ── Parsing ──────────────────────────────────────────────

    @staticmethod
    def _norm(text: str) -> str:
        text = text.replace("\xa0", " ")
        text = re.sub(r"\bm\s?³", "m³", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _long_date(value: str) -> Optional[date]:
        try:
            return datetime.strptime(value.title(), "%B %d, %Y").date()
        except ValueError:
            return None

    @staticmethod
    def _dollars(cents: str) -> float:
        return round(float(cents) / 100, 6)

    @staticmethod
    def _volume(text: str) -> float:
        return float(text.replace(",", ""))

    def _dated_price(self, text: str, pattern: str, label: str, edition: date) -> tuple[date, float]:
        match = re.search(pattern, text)
        effective = self._long_date(match.group(1)) if match else None
        if not effective or effective != edition:
            raise ValueError(f"{label} price or its edition date missing or changed")
        value = self._dollars(match.group(2))
        if value <= 0:
            raise ValueError(f"non-positive {label} price")
        return effective, value

    def _blocks(self, section: str, unit: str) -> list[tuple[float, Optional[float]]]:
        """Contiguous (price, upper bound) bands from 0 to an open-ended last band."""
        rows = re.findall(rf"from {VOLUME} to {VOLUME} (\d+\.\d{{3}})", section)
        last = re.search(rf"{VOLUME} and over (\d+\.\d{{3}})", section)
        if len(rows) < 2 or not last:
            raise ValueError(f"{unit} price bands missing")
        bands: list[tuple[float, Optional[float]]] = []
        lower = 0.0
        for start, end, price in rows:
            if self._volume(start) != lower or self._volume(end) <= lower:
                raise ValueError(f"{unit} price bands are not contiguous")
            lower = self._volume(end)
            bands.append((self._dollars(price), lower))
        if self._volume(last.group(1)) != lower:
            raise ValueError(f"{unit} open-ended band does not follow the last band")
        bands.append((self._dollars(last.group(2)), None))
        if min(price for price, _ in bands) <= 0:
            raise ValueError("non-positive band price")
        return bands

    def parse_pages(self, pages: dict[str, str], today: Optional[date] = None,
                    tariff_url: Optional[str] = None) -> list[TariffRecord]:
        """Build Rate D1 records from texts keyed pricing/tariff; any missing required price rejects D1."""
        today = today or datetime.now(timezone.utc).date()
        pages = {key: self._norm(text) for key, text in pages.items()}
        tariff = pages.get("tariff", "")
        try:
            if not tariff_url:
                raise ValueError("tariff URL missing")
            editions = {self._long_date(value) for value in
                        re.findall(r"CONDITIONS OF SERVICE AND TARIFF AS OF ([A-Z]+ \d{1,2}, \d{4})", tariff)}
            if len(editions) != 1 or None in editions:
                raise ValueError("tariff pages do not share one edition date")
            edition = editions.pop()
            linked = re.search(r"Conditions of Service and Tariff effective as of " + DATE, pages.get("pricing", ""))
            if not linked or self._long_date(linked.group(1)) != edition or edition > today:
                raise ValueError("tariff edition is not the current edition linked from the pricing page")

            default = re.search(r"14\.1\.2 DEFAULT DISTRIBUTION RATE Rate D1 applies by default", tariff)
            fee_start = tariff.find("14.2.2.1 Basic Fee")
            unit_start = tariff.find("14.2.2.2 Unit Prices for the Volume Withdrawn")
            unit_end = tariff.find("14.2.3 RATE REBATES")
            if not default or not 0 <= fee_start < unit_start < unit_end:
                raise ValueError("Rate D1 sections missing")
            fee_section = tariff[fee_start:unit_start]
            if "¢/Metering device/Day" not in fee_section or "multiplied by the number of days" not in fee_section:
                raise ValueError("basic fee unit or billing-day rule changed")
            unit_section = tariff[unit_start:unit_end]
            if "m³/Day ¢/m³" not in unit_section:
                raise ValueError("distribution unit changed")
            values = {
                "basic": self._blocks(fee_section, "basic fee"),
                "distribution": self._blocks(unit_section, "distribution"),
                "supply": self._dated_price(
                    tariff, r"the traditional natural gas supply price, as of " + DATE + r" is " + CENTS
                    + r"\. The price may be adjusted monthly", "supply", edition),
                "transport": self._dated_price(
                    tariff, r"12\.1\.2\.1\.1 Transportation Basis Price For each m³ of volume withdrawn, the "
                    r"transportation basis price as of " + DATE + r" is " + CENTS, "transportation", edition),
                "cteas": self._dated_price(
                    tariff, r"the CTEAS price as of " + DATE + r" is " + CENTS + r"\. The price may be adjusted "
                    r"quarterly", "cap-and-trade", edition),
            }
            balancing = re.search(r"13\.1\.2\.1 Price for Customers whose Annual Volume is Less than " + VOLUME
                                  + r" m³ For each m³ of volume withdrawn, the unit price is " + CENTS, tariff)
            social = re.search(r"11\.4\.2\.1 Socialization cost A price of " + CENTS + r" applies to each m³ of "
                               r"traditional natural gas withdrawn by a customer whose purchase of gas from renewable "
                               r"source is less than the percentage prescribed .{0,120}?this percentage is set at "
                               r"(\d+)%", tariff)
            rider = re.search(r"11\.4\.2\.2 Rider A price of " + CENTS + r" applies to each m³ of traditional "
                              r"natural gas withdrawn by a customer whose purchase of gas from renewable gas is less "
                              r"than (\d+)% for the year ending " + DATE, tariff)
            if not balancing or not social or not rider:
                raise ValueError("load-balancing or renewable-gas socialization price missing")
            values["balancing"] = (self._volume(balancing.group(1)), self._dollars(balancing.group(2)))
            values["social"] = (self._dollars(social.group(1)), social.group(2))
            values["rider"] = (self._dollars(rider.group(1)), rider.group(2), rider.group(3))
            if min(values["balancing"][1], values["social"][0], values["rider"][0]) <= 0:
                raise ValueError("non-positive adjustment price")
        except ValueError as exc:
            self.logger.warning("Energir Rate D1 not parsed live: %s", exc)
            return []
        return [self._build(values, edition, tariff_url, customer_class)
                for customer_class in ("residential", "commercial")]

    def _build(self, values: dict, edition: date, url: str, customer_class: str) -> TariffRecord:
        eff = edition.isoformat()
        detail = f"Conditions of Service and Tariff as of {edition.strftime('%B')} {edition.day}, {edition.year}"

        def component(kind: str, name: str, value: float, unit: str, article: str, **extra) -> RateComponent:
            return RateComponent(kind, name, value, unit, effective_date=eff, source_url=url,
                                 source_detail=f"{detail}, article {article}", **extra)

        comps = []
        for number, (price, upper) in enumerate(values["basic"], start=1):
            comps.append(component(
                "fixed", f"Basic Fee — Band {number}", price, "$/metering device/day", "14.2.2.1",
                tier_number=number, tier_threshold=upper, tier_unit="m³/year" if upper else None,
                notes="One band applies, selected by annual volume withdrawn (upper bound shown); multiplied by the "
                      "days in the billing period. Additional meters at an address pay the minimum band."))
        for number, (price, upper) in enumerate(values["distribution"], start=1):
            comps.append(component(
                "delivery", f"Distribution — Block {number}", price, "$/m³", "14.2.2.2", tier_number=number,
                tier_threshold=upper, tier_unit="m³/day" if upper else None,
                notes="Daily volume block (upper bound shown) multiplied by the days in the billing period"))
        threshold, balancing = values["balancing"]
        social, social_percent = values["social"]
        rider, rider_percent, rider_year = values["rider"]
        comps += [
            component("commodity", "Natural Gas Supply", values["supply"][1], "$/m³", "11.1.2.1",
                      market_reference="Energir traditional natural gas supply",
                      notes="Distributor's traditional supply price, adjustable monthly. Customers may supply their own "
                            "gas; fixed-price agreements and renewable-source gas are priced separately."),
            component("transmission", "Transportation", values["transport"][1], "$/m³", "12.1.2.1.1",
                      notes="Distributor's transportation basis price; customer-provided transportation is priced "
                            "separately."),
            component("other", "Load Balancing", balancing, "$/m³", "13.1.2.1", sub_component="conditional",
                      notes=f"Applies to customers whose annual volume is less than {threshold:,.0f} m³; other "
                            "customers pay a load-factor formula price."),
            component("rider", "Renewable Gas Socialization Cost", social, "$/m³", "11.4.2.1",
                      sub_component="conditional",
                      notes=f"Applies to traditional gas when renewable-gas purchases are below the prescribed "
                            f"{social_percent}%."),
            component("rider", "Renewable Gas Socialization Rider", rider, "$/m³", "11.4.2.2",
                      sub_component="conditional",
                      notes=f"Applies to traditional gas when renewable-gas purchases were below {rider_percent}% "
                            f"for the year ending {rider_year}."),
            component("carbon", "Cap-and-Trade Emission Allowances (CTEAS)", values["cteas"][1], "$/m³", "15.1.2.1",
                      notes="Quebec cap-and-trade allowance cost per m³ of traditional gas, adjustable quarterly; "
                            "registered emitters are not billed this service."),
        ]
        residential = customer_class == "residential"
        return TariffRecord(
            utility_name="Energir", province="QC", utility_type="gas",
            tariff_name="Residential — Rate D1" if residential else "Business — Rate D1", tariff_code="D1",
            customer_class=customer_class, sub_class="general distribution service",
            eligibility="Rate D1 applies by default to any customer withdrawing firm-service natural gas at a single "
                        "metering point, regardless of volume.",
            rate_structure="tiered", pricing_method="regulated", effective_date=eff, source_url=url,
            source_page=detail, confidence="high",
            notes=("The same default Rate D1 schedule applies to residential and business customers. Prices are "
                   "published in cents per m³ and stored as $/m³. Inventory-related adjustments, rate rebates, "
                   "minimum annual obligations and taxes are not included. Regulated by the Régie de l'énergie."),
            components=comps,
        )

    def _seed_data(self) -> list[TariffRecord]:
        records = []

        # ── Residential ──────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Energir",
            province="QC",
            utility_type="gas",
            tariff_name="Residential — Rate D1",
            tariff_code="D1",
            customer_class="residential",
            rate_structure="flat",
            effective_date=SEED_RESIDENTIAL["effective_date"],
            source_url=SEED_RESIDENTIAL["source_url"],
            confidence="medium",
            notes=(
                "Energir residential rate for Quebec. "
                "Gas supply portion varies with market conditions. "
                "Regulated by the Regie de l'energie."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_RESIDENTIAL["customer_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly charge regardless of gas usage",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Distribution Charge",
                    charge_value=SEED_RESIDENTIAL["distribution_rate"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Energir distribution charge for delivering gas",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Gas Supply Charge",
                    charge_value=SEED_RESIDENTIAL["supply_rate"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Cost of natural gas commodity — varies with market",
                    market_reference="Quebec gas supply portfolio",
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Transportation Charge",
                    charge_value=SEED_RESIDENTIAL["transportation_rate"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Pipeline transportation to Energir system",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_RESIDENTIAL["carbon_charge"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="rider",
                    component_name="Load Balancing Rider",
                    charge_value=SEED_RESIDENTIAL["load_balancing_rider"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Load balancing and inventory management adjustment",
                ),
            ],
        ))

        # ── Commercial ───────────────────────────────────────────
        records.append(TariffRecord(
            utility_name="Energir",
            province="QC",
            utility_type="gas",
            tariff_name="Commercial — Rate D3",
            tariff_code="D3",
            customer_class="commercial",
            rate_structure="flat",
            effective_date=SEED_COMMERCIAL["effective_date"],
            source_url=SEED_COMMERCIAL["source_url"],
            confidence="medium",
            notes=(
                "Energir small commercial rate for Quebec. "
                "Includes demand charges based on peak consumption. "
                "Regulated by the Regie de l'energie."
            ),
            components=[
                RateComponent(
                    component_type="fixed",
                    component_name="Monthly Customer Charge",
                    charge_value=SEED_COMMERCIAL["customer_charge_monthly"],
                    charge_unit="$/month",
                    confidence="medium",
                    notes="Fixed monthly charge for commercial accounts",
                ),
                RateComponent(
                    component_type="delivery",
                    component_name="Distribution Charge",
                    charge_value=SEED_COMMERCIAL["distribution_rate"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Volume-based distribution charge — lower rate for commercial",
                ),
                RateComponent(
                    component_type="commodity",
                    component_name="Gas Supply Charge",
                    charge_value=SEED_COMMERCIAL["supply_rate"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Cost of natural gas commodity — varies with market",
                    market_reference="Quebec gas supply portfolio",
                ),
                RateComponent(
                    component_type="transmission",
                    component_name="Transportation Charge",
                    charge_value=SEED_COMMERCIAL["transportation_rate"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Pipeline transportation to Energir system",
                ),
                RateComponent(
                    component_type="carbon",
                    component_name="Federal Carbon Charge",
                    charge_value=SEED_COMMERCIAL["carbon_charge"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Federal carbon levy — increases annually per federal schedule",
                ),
                RateComponent(
                    component_type="demand",
                    component_name="Demand Charge",
                    charge_value=SEED_COMMERCIAL["demand_charge"],
                    charge_unit="$/GJ",
                    confidence="medium",
                    notes="Demand-based charge on peak gas consumption",
                ),
            ],
        ))

        return records
