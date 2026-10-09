"""
test_live_parsers.py — Tests for live HTML/text parsing logic in Tier 1 scrapers.

Tests the parsing methods directly (without network I/O) by feeding them
synthetic HTML or verifying seed data structures. This validates that:
  - Seed data matches expected values after the 2025/2026 updates
  - Parser methods exist and accept correct arguments
  - TariffRecords have correct structure, component types, and value ranges
  - Rate structures are correctly classified (flat, tiered, demand, etc.)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch

from scrapers.base import TariffRecord, RateComponent


# ─── Manitoba Hydro ─────────────────────────────────────────────

class TestManitobaHydroSeed:
    @pytest.fixture(autouse=True)
    def setup(self):
        from scrapers.utilities.manitoba_hydro import ManitobaHydroScraper
        with patch.object(ManitobaHydroScraper, "_try_live_scrape", return_value=None):
            self.scraper = ManitobaHydroScraper()
            self.records = self.scraper.scrape()

    def test_returns_three_tariffs(self):
        assert len(self.records) == 3

    def test_residential_is_flat(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        assert res.rate_structure == "flat"
        assert res.tariff_name == "Residential Service"

    def test_residential_basic_charge(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        fixed = [c for c in res.components if c.component_type == "fixed"][0]
        assert fixed.charge_value == pytest.approx(9.84)
        assert fixed.charge_unit == "$/month"

    def test_residential_energy_rate(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        energy = [c for c in res.components if c.component_type == "energy"][0]
        assert energy.charge_value == pytest.approx(0.09970)
        assert energy.charge_unit == "$/kWh"

    def test_gs_small_is_tiered(self):
        gs = [r for r in self.records if "Small" in r.tariff_name][0]
        assert gs.rate_structure == "tiered"
        assert gs.customer_class == "commercial"

    def test_gs_small_has_two_energy_tiers(self):
        gs = [r for r in self.records if "Small" in r.tariff_name][0]
        energy = [c for c in gs.components if c.component_type == "energy"]
        assert len(energy) == 2
        tier1 = [c for c in energy if c.tier_number == 1][0]
        tier2 = [c for c in energy if c.tier_number == 2][0]
        assert tier1.charge_value == pytest.approx(0.09864)
        assert tier2.charge_value == pytest.approx(0.07568)

    def test_gs_small_tier_threshold(self):
        gs = [r for r in self.records if "Small" in r.tariff_name][0]
        tier1 = [c for c in gs.components if c.tier_number == 1][0]
        assert tier1.tier_threshold == 11000

    def test_gs_medium_is_demand(self):
        gm = [r for r in self.records if "Medium" in r.tariff_name][0]
        assert gm.rate_structure == "demand"

    def test_gs_medium_has_demand_charge(self):
        gm = [r for r in self.records if "Medium" in r.tariff_name][0]
        demand = [c for c in gm.components if c.component_type == "demand"][0]
        assert demand.charge_value == pytest.approx(12.39)
        assert demand.charge_unit == "$/kVA"

    def test_gs_medium_has_two_energy_tiers(self):
        gm = [r for r in self.records if "Medium" in r.tariff_name][0]
        energy = [c for c in gm.components if c.component_type == "energy"]
        assert len(energy) == 2

    def test_effective_dates_updated(self):
        for r in self.records:
            assert r.effective_date == "2026-01-01"


# ─── Manitoba Hydro building classes ───

import html as _html
import json
from pathlib import Path

from scrapers.base import BaseScraper
from scrapers.utilities.manitoba_hydro import COMMERCIAL_URL as MBH_COMMERCIAL_URL, RESIDENTIAL_URL as MBH_RESIDENTIAL_URL, ManitobaHydroScraper

MBH_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "manitoba_hydro.json")

with open(MBH_FIXTURE, encoding="utf-8") as fh:
    MBH_PAGES = json.load(fh)["pages"]


def MBH_to_html(lines):
    return "<html><body>" + "".join(f"<p>{_html.escape(ln)}</p>" for ln in lines) + "</body></html>"


def MBH_edited(page, old, new):
    lines = list(MBH_PAGES[page]["lines"])
    assert old in lines, old
    lines[lines.index(old)] = new
    return lines


def MBH_without(page, line):
    lines = list(MBH_PAGES[page]["lines"])
    lines.remove(line)
    return lines


def MBH_parse_res(lines=None):
    return {r.tariff_name: r for r in ManitobaHydroScraper()._parse_residential(MBH_to_html(lines or MBH_PAGES["residential"]["lines"]))}


def MBH_parse_com(lines=None):
    return {r.tariff_name: r for r in ManitobaHydroScraper()._parse_commercial(MBH_to_html(lines or MBH_PAGES["commercial"]["lines"]))}


def MBH_comp(record, name):
    return [c for c in record.components if c.component_name == name][0]


class TestManitobaHydroBuildingLive:
    def test_fixture_provenance(self):
        assert MBH_PAGES["residential"]["url"] == MBH_RESIDENTIAL_URL
        assert MBH_PAGES["commercial"]["url"] == MBH_COMMERCIAL_URL
        assert all(p["section"] and p["lines"] for p in MBH_PAGES.values())

    def test_residential_variants(self):
        res = MBH_parse_res()
        assert set(res) == {"Residential Service", "Residential Seasonal Service", "Residential Diesel Service"}
        std = res["Residential Service"]
        assert MBH_comp(std, "Basic Charge").charge_value == pytest.approx(9.84)
        assert MBH_comp(std, "Basic Charge (exceeding 200 Amp)").charge_value == pytest.approx(19.68)
        assert MBH_comp(std, "Basic Charge").charge_unit == "$/month"
        assert MBH_comp(std, "Energy Charge").charge_value == pytest.approx(0.0997)
        seasonal = res["Residential Seasonal Service"]
        assert MBH_comp(seasonal, "Basic Annual Charge").charge_value == pytest.approx(118.08)
        assert MBH_comp(seasonal, "Basic Annual Charge").charge_unit == "$/year"
        assert MBH_comp(seasonal, "Energy Charge").charge_value == pytest.approx(0.0997)
        assert "7,500 kWh per season" in seasonal.eligibility
        diesel = res["Residential Diesel Service"]
        assert MBH_comp(diesel, "Basic Charge").charge_value == pytest.approx(8.08)
        assert MBH_comp(diesel, "Energy Charge").charge_value == pytest.approx(0.08196)
        assert "60 A" in diesel.eligibility

    def test_commercial_existing_classes_keep_names_and_kva(self):
        com = MBH_parse_com()
        assert {
            "General Service Small (Non-Demand)", "General Service Small (Demand)",
            "General Service Seasonal (Single Phase)", "General Service Medium",
            "General Service Large (>750 V to 30 kV)", "General Service Large (>30 kV to 100 kV)",
            "General Service Large (>100 kV)",
        } <= set(com)
        medium = com["General Service Medium"]
        demand = [c for c in medium.components if c.component_type == "demand"][0]
        assert (demand.charge_value, demand.charge_unit, demand.demand_unit) == (12.39, "$/kVA", "kVA")
        assert "25% of contract demand" in medium.notes
        assert MBH_comp(com["General Service Seasonal (Single Phase)"], "Basic Annual Charge").charge_unit == "$/year"
        assert "Minimum monthly bill is the basic charge plus demand charge" in com["General Service Small (Demand)"].notes

    def test_commercial_diesel_classes(self):
        com = MBH_parse_com()
        gs = com["Diesel General Service"]
        assert MBH_comp(gs, "Basic Charge").charge_value == pytest.approx(20.74)
        first, balance = MBH_comp(gs, "First 2,000 kWh"), MBH_comp(gs, "Balance of kWh")
        assert (first.charge_value, first.tier_number, first.tier_threshold) == (pytest.approx(0.09485), 1, 2000)
        assert (balance.charge_value, balance.tier_number) == (pytest.approx(0.42617), 2)
        gov = com["Diesel Government and First Nation Education"]
        energy = MBH_comp(gov, "Energy Charge")
        assert energy.charge_value == pytest.approx(2.59382)
        assert energy.charge_unit == "$/kWh"
        assert MBH_comp(gov, "Basic Charge").charge_value == pytest.approx(20.74)

    def test_every_component_has_source_and_date(self):
        records = list(MBH_parse_res().values()) + list(MBH_parse_com().values())
        assert len(records) == 12
        for r in records:
            assert r.effective_date == "2026-01-01"
            for c in r.components:
                assert c.effective_date == "2026-01-01"
                assert c.source_url in (MBH_RESIDENTIAL_URL, MBH_COMMERCIAL_URL)
                assert "rates effective January 1, 2026" in c.source_detail

    def test_scrape_marks_live_provenance(self):
        pages = {MBH_RESIDENTIAL_URL: MBH_to_html(MBH_PAGES["residential"]["lines"]), MBH_COMMERCIAL_URL: MBH_to_html(MBH_PAGES["commercial"]["lines"])}
        with patch.object(BaseScraper, "fetch_page", lambda self, url, delay=1.0: pages[url]):
            records = ManitobaHydroScraper().scrape()
        assert len(records) == 12
        assert all("Provenance: live_parsed" in r.notes for r in records)

    # ── Independent fail-closed mutations ─────────────────────────

    def test_missing_seasonal_condition_rejects_only_seasonal(self):
        line = next(ln for ln in MBH_PAGES["residential"]["lines"] if "per season" in ln)
        res = MBH_parse_res(MBH_edited("residential", line, "The account is billed twice a year."))
        assert "Residential Seasonal Service" not in res
        assert {"Residential Service", "Residential Diesel Service"} <= set(res)

    def test_renamed_diesel_unit_rejects_only_that_class(self):
        com = MBH_parse_com(MBH_edited("commercial", "9.485\u00a2/kWh", "9.485\u00a2/kVA"))
        assert "Diesel General Service" not in com
        assert "Diesel Government and First Nation Education" in com
        assert "General Service Medium" in com

    def test_missing_demand_row_rejects_only_medium(self):
        com = MBH_parse_com(MBH_without("commercial", "$12.39/kVA"))
        assert "General Service Medium" not in com
        assert {"General Service Small (Demand)", "Diesel General Service"} <= set(com)

    def test_unknown_residential_row_rejects_only_that_class(self):
        lines = MBH_edited("residential", "Basic annual charge not exceeding 200 Amp", "Basic annual charge not exceeding 300 Amp")
        res = MBH_parse_res(lines)
        assert "Residential Seasonal Service" not in res
        assert "Residential Service" in res

    def test_missing_effective_date_rejects_page_not_other_page(self):
        assert MBH_parse_res(MBH_without("residential", "Rates effective January 1, 2026")) == {}
        assert MBH_parse_com() != {}

    def test_future_date_rejected(self):
        assert MBH_parse_com(MBH_edited("commercial", "Rates effective January 1, 2026", "Rates effective January 1, 2099")) == {}

    def test_missing_diesel_eligibility_text_rejects_diesel_only(self):
        line = next(ln for ln in MBH_PAGES["commercial"]["lines"] if "First Nation schools" in ln)
        com = MBH_parse_com(MBH_edited("commercial", line, "Commercial customers are eligible."))
        assert "Diesel General Service" not in com and "Diesel Government and First Nation Education" not in com
        assert "General Service Medium" in com

    # ── Price follows source ──────────────────────────────────────

    def test_prices_follow_source(self):
        res = MBH_parse_res(MBH_edited("residential", "$118.08", "$120.00"))
        assert MBH_comp(res["Residential Seasonal Service"], "Basic Annual Charge").charge_value == pytest.approx(120.0)
        com = MBH_parse_com(MBH_edited("commercial", "$2.59382/kWh", "$2.61000/kWh"))
        assert MBH_comp(com["Diesel Government and First Nation Education"], "Energy Charge").charge_value == pytest.approx(2.61)
        res = MBH_parse_res(MBH_edited("residential", "8.196\u00a2/kWh", "8.300\u00a2/kWh"))
        assert MBH_comp(res["Residential Diesel Service"], "Energy Charge").charge_value == pytest.approx(0.083)


# ─── NB Power ──────────────────────────────────────────────────

class TestNBPowerSeed:
    @pytest.fixture(autouse=True)
    def setup(self):
        from scrapers.utilities.nb_power import NBPowerScraper
        with patch.object(NBPowerScraper, "_try_live_scrape", return_value=None):
            self.scraper = NBPowerScraper()
            self.records = self.scraper.scrape()

    def test_returns_at_least_two_tariffs(self):
        assert len(self.records) >= 2

    def test_residential_is_flat(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        assert res.rate_structure == "flat"

    def test_residential_service_charge(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        fixed = [c for c in res.components if c.component_type == "fixed"][0]
        assert fixed.charge_value == pytest.approx(30.87)

    def test_residential_single_energy_rate(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        energy = [c for c in res.components if c.component_type == "energy"]
        assert len(energy) == 1
        assert energy[0].charge_value == pytest.approx(0.1584)

    def test_commercial_present(self):
        comm = [r for r in self.records if r.customer_class == "commercial"]
        assert len(comm) >= 1

    def test_effective_date_updated(self):
        for r in self.records:
            assert r.effective_date >= "2026-04-14"


# ─── Nova Scotia Power ──────────────────────────────────────────

# ─── NB Power building classes ───

import json
from pathlib import Path

from scrapers.utilities.nb_power import NBPowerScraper, RESIDENTIAL_URL, BUSINESS_URL

NBP_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "nb_power.json").read_text(encoding="utf-8")
)

NBP_RURAL = "Residential Service (Rate D) - Rural/Seasonal"
NBP_WH_RES = "Water Heater Rental (Residential)"
NBP_WH_BUS = "Water Heater Rental (Business)"
NBP_SURE = "SureConnect Service (Residential)"
NBP_RL = "Recreational Lighting"
NBP_PFC = "Public Fast Charging Rate"
NBP_NEW = {NBP_RURAL, NBP_WH_RES, NBP_WH_BUS, NBP_SURE, NBP_RL, NBP_PFC}


def _NBP_scrape(res=None, biz=None):
    pages = {
        RESIDENTIAL_URL: NBP_FIXTURE["residential"]["html"] if res is None else res,
        BUSINESS_URL: NBP_FIXTURE["business"]["html"] if biz is None else biz,
    }
    with patch.object(NBPowerScraper, "fetch_page", side_effect=lambda url, *a, **k: pages[url]):
        records = NBPowerScraper().scrape()
    return {r.tariff_name: r for r in records}


def _NBP_comp(rec, name):
    return next(c for c in rec.components if c.component_name == name)


def _NBP_replace_last(text, old, new, before=None):
    end = text.index(before) if before else len(text)
    i = text.rindex(old, 0, end)
    return text[:i] + new + text[i + len(old):]


class TestNBPowerBuildingLive:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.recs = _NBP_scrape()

    def test_fixture_is_source_derived(self):
        for key in ("residential", "business"):
            assert NBP_FIXTURE[key]["url"].startswith("https://www.nbpower.com/")
            assert NBP_FIXTURE[key]["section"] and NBP_FIXTURE[key]["retrieved"]

    def test_all_new_classes_live(self):
        assert NBP_NEW <= set(self.recs)
        for name in NBP_NEW:
            assert "Provenance: live_parsed" in self.recs[name].notes
            assert "seed_fallback" not in self.recs[name].notes

    def test_existing_identities_preserved(self):
        for name in ("Residential Service (Rate D)", "General Service I", "Small Industrial Service"):
            assert name in self.recs and "live_parsed" in self.recs[name].notes

    def test_every_component_has_date_source_detail(self):
        for name in NBP_NEW:
            for c in self.recs[name].components:
                assert c.effective_date == "2026-04-14"
                assert c.source_url in (RESIDENTIAL_URL, BUSINESS_URL)
                assert c.source_detail

    def test_existing_live_components_have_date_source_detail(self):
        for name in ("Residential Service (Rate D)", "General Service I", "Small Industrial Service"):
            for c in self.recs[name].components:
                assert c.effective_date == "2026-04-14"
                assert c.source_url in (RESIDENTIAL_URL, BUSINESS_URL)
                assert c.source_detail

    def test_rural_seasonal(self):
        r = self.recs[NBP_RURAL]
        assert r.customer_class == "residential"
        fixed = _NBP_comp(r, "Basic Charge")
        assert (fixed.charge_value, fixed.charge_unit) == (33.82, "$/billing period")
        assert _NBP_comp(r, "Energy Charge").charge_value == pytest.approx(0.1584)

    def test_water_heater_residential(self):
        r = self.recs[NBP_WH_RES]
        vals = {c.component_name: (c.charge_value, c.charge_unit) for c in r.components}
        assert vals == {
            "Water Heater Rental 22 gal/100 L": (10.99, "$/month"),
            "Water Heater Rental 40 gal/180 L": (10.99, "$/month"),
            "Water Heater Rental 60 gal/270 L": (13.99, "$/month"),
        }

    def test_water_heater_business(self):
        r = self.recs[NBP_WH_BUS]
        assert r.customer_class == "commercial"
        assert len(r.components) == 6
        assert _NBP_comp(r, "Water Heater Rental 100 gal/455 L (Commercial 600V)").charge_value == 50.49
        assert _NBP_comp(r, "Water Heater Rental 100 gal/455 L").charge_value == 24.99

    def test_sureconnect(self):
        c = self.recs[NBP_SURE].components[0]
        assert (c.component_name, c.charge_value, c.charge_unit) == ("SureConnect Service 30 A", 29.99, "$/month")

    def test_recreational_lighting(self):
        r = self.recs[NBP_RL]
        assert r.rate_structure == "tiered"
        t1, t2 = _NBP_comp(r, "Tier 1 Energy Charge"), _NBP_comp(r, "Tier 2 Energy Charge")
        assert (t1.charge_value, t1.tier_threshold, t1.tier_unit) == (0.1821, 5000.0, "kWh/billing period")
        assert t2.charge_value == 0.1304
        assert _NBP_comp(r, "Basic Charge").charge_unit == "$/billing period"

    def test_fast_charging_bands_units_and_hours(self):
        r = self.recs[NBP_PFC]
        assert "above 20%" in r.eligibility and "General Service" in r.eligibility
        d = _NBP_comp(r, "Demand Charge (LF 15% < LF <= 20%)")
        assert (d.charge_value, d.charge_unit, d.demand_unit) == (11.271, "$/kW/billing period", "kW")
        on = _NBP_comp(r, "On-Peak Energy Charge (LF 0% < LF <= 5%)")
        off = _NBP_comp(r, "Off-Peak Energy Charge (LF 0% < LF <= 5%)")
        assert (on.charge_value, on.tou_hours) == (0.1223, "7:00 am-10:00 pm")
        assert (off.charge_value, off.tou_hours) == (0.0638, "10:00 pm-7:00 am")
        assert sum(c.component_type == "demand" for c in r.components) == 4
        assert _NBP_comp(r, "Off-Peak Energy Charge (LF 15% < LF <= 20%)").charge_value == 0.0449

    def test_no_street_lighting_or_one_time_fee_records(self):
        names = " ".join(self.recs).lower()
        assert "dusk" not in names and "flood" not in names

    # ── Independent failure (mutation rejections) ──────────────────

    def test_reject_rural_only(self):
        res = NBP_FIXTURE["residential"]["html"].replace("Rural/Seasonal", "Rural", 1)
        recs = _NBP_scrape(res=res)
        assert NBP_RURAL not in recs
        assert {NBP_WH_RES, NBP_SURE, NBP_WH_BUS, NBP_RL, NBP_PFC} <= set(recs)

    def test_reject_residential_water_heater_only(self):
        res = NBP_FIXTURE["residential"]["html"].replace("$13.99", "n/a", 1)
        recs = _NBP_scrape(res=res)
        assert NBP_WH_RES not in recs
        assert {NBP_RURAL, NBP_SURE, NBP_WH_BUS} <= set(recs)

    def test_reject_business_water_heater_only(self):
        biz = NBP_FIXTURE["business"]["html"].replace("(Commercial 208V)", "(", 1)
        recs = _NBP_scrape(biz=biz)
        assert NBP_WH_BUS not in recs
        assert {NBP_WH_RES, NBP_RL, NBP_PFC, "General Service I"} <= set(recs)

    def test_reject_recreational_lighting_when_total_does_not_reconcile(self):
        biz = NBP_FIXTURE["business"]["html"]
        biz = _NBP_replace_last(biz, "13.04¢ Total Charge", "13.50¢ Total Charge", before="Small Industrial Service")
        recs = _NBP_scrape(biz=biz)
        assert NBP_RL not in recs
        assert {NBP_PFC, NBP_WH_BUS, "General Service I"} <= set(recs)

    def test_reject_fast_charging_without_over_20_rule(self):
        biz = NBP_FIXTURE["business"]["html"].replace("General Service Rates apply", "See tariff", 1)
        recs = _NBP_scrape(biz=biz)
        assert NBP_PFC not in recs
        assert {NBP_RL, NBP_WH_BUS} <= set(recs)

    def test_reject_all_business_extras_without_page_date_keeps_residential(self):
        biz = NBP_FIXTURE["business"]["html"].replace("(effective April 14, 2026)", "", 1)
        recs = _NBP_scrape(biz=biz)
        assert not ({NBP_RL, NBP_PFC, NBP_WH_BUS} & set(recs))
        assert {NBP_RURAL, NBP_WH_RES, NBP_SURE} <= set(recs)

    def test_reject_sureconnect_when_unit_not_monthly(self):
        res = NBP_FIXTURE["residential"]["html"]
        i = res.index("SureConnect Service:")
        res = res[:i] + res[i:].replace("$/month", "$/year", 1)
        recs = _NBP_scrape(res=res)
        assert NBP_SURE not in recs
        assert {NBP_RURAL, NBP_WH_RES} <= set(recs)

    # ── Price follows source ───────────────────────────────────────

    def test_price_follows_source(self):
        res = NBP_FIXTURE["residential"]["html"].replace("$33.82", "$34.50", 1).replace("$29.99", "$31.25", 1)
        biz = NBP_FIXTURE["business"]["html"].replace("$4.509", "$4.600", 1).replace("$24.99", "$25.49", 1)
        recs = _NBP_scrape(res=res, biz=biz)
        assert _NBP_comp(recs[NBP_RURAL], "Basic Charge").charge_value == 34.50
        assert recs[NBP_SURE].components[0].charge_value == 31.25
        assert _NBP_comp(recs[NBP_PFC], "Demand Charge (LF 0% < LF <= 5%)").charge_value == 4.6
        assert _NBP_comp(recs[NBP_WH_BUS], "Water Heater Rental 100 gal/455 L").charge_value == 25.49

    def test_effective_date_follows_source(self):
        res = NBP_FIXTURE["residential"]["html"].replace("April 14, 2026", "May 1, 2027")
        recs = _NBP_scrape(res=res)
        assert recs[NBP_RURAL].effective_date == "2027-05-01"
        assert recs[NBP_SURE].components[0].effective_date == "2027-05-01"
        assert recs[NBP_RL].effective_date == "2026-04-14"


class TestNovaScotiaPowerSeed:
    @pytest.fixture(autouse=True)
    def setup(self):
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper
        with patch.object(NovaScotiaPowerScraper, "_try_live_scrape", return_value=None):
            self.scraper = NovaScotiaPowerScraper()
            self.records = self.scraper.scrape()

    def test_returns_four_tariffs(self):
        assert len(self.records) == 4

    def test_optional_residential_products_are_discovered(self):
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper, RESIDENTIAL_URL

        root = RESIDENTIAL_URL.rsplit("/", 1)[0]
        product_urls = {root + "/time-of-day", root + "/time-of-use", root + "/critical-peak"}
        html = '<h1>Standard Residential Service Rate</h1>' + ''.join(
            f'<a href="{url}">Learn More</a>' for url in sorted(product_urls)
        )
        scraper = NovaScotiaPowerScraper()
        with patch.object(scraper, "fetch_page", return_value=html) as fetch, \
             patch.object(scraper, "_try_live_commercial", return_value=None):
            scraper._try_live_scrape()
        fetched = {call.args[0] for call in fetch.call_args_list}
        assert product_urls <= fetched

    def test_residential_is_flat(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        assert res.rate_structure == "flat"
        assert res.tariff_name == "Domestic Service"

    def test_residential_basic_charge(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        fixed = [c for c in res.components if c.component_type == "fixed"][0]
        assert fixed.charge_value == pytest.approx(19.17)

    def test_residential_energy_rate(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        energy = [c for c in res.components if c.component_type == "energy"][0]
        assert energy.charge_value == pytest.approx(0.18187)

    def test_rate10_small_commercial_present(self):
        r10 = [r for r in self.records if r.tariff_code == "10"]
        assert len(r10) == 1
        assert r10[0].rate_structure == "tiered"

    def test_rate11_commercial_general_present(self):
        r11 = [r for r in self.records if r.tariff_code == "11"]
        assert len(r11) == 1
        demand = [c for c in r11[0].components if c.component_type == "demand"]
        assert len(demand) == 1

    def test_rate12_large_commercial_present(self):
        r12 = [r for r in self.records if r.tariff_code == "12"]
        assert len(r12) == 1
        assert r12[0].rate_structure == "demand"


class TestNovaScotiaPowerResidential:
    @pytest.fixture
    def document(self):
        import json
        from pathlib import Path

        fixture = Path(__file__).parent / "fixtures" / "nova_scotia_residential.json"
        return json.loads(fixture.read_text(encoding="utf-8"))

    @staticmethod
    def parse(document, today="2026-10-02"):
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper
        from scrapers.utils.parsing import DocumentPage

        scraper = NovaScotiaPowerScraper()
        products = {kind: product["html"] for kind, product in document["products"].items()}
        with patch.object(scraper, "now_iso", return_value=today + "T00:00:00+00:00"):
            records = scraper._parse_residential_tariffs([DocumentPage(**page) for page in document["pages"]], products, document["source_url"])
        return {record.tariff_code: record for record in records}

    def test_standard_rates_and_riders_are_separate(self, document):
        records = self.parse(document)
        assert set(records) == {"02/03/04", "05/06", "70", "80"}
        standard = records["02/03/04"]
        assert standard.tariff_name == "Domestic Service"
        assert standard.effective_date == "2026-05-01"
        assert standard.end_date == "2026-12-31"
        assert standard.components[0].charge_value == 20.08
        assert standard.components[1].charge_value == 0.18324
        riders = {component.component_name: component for component in standard.components if component.component_type == "rider"}
        assert riders["FAM Actual/Balance Adjustment (Combined)"].charge_value == 0.00156
        assert riders["DSM Cost Recovery Rider"].charge_value == 0.00648
        assert riders["Storm Cost Recovery Rider"].charge_value == 0
        assert sum(component.charge_value for component in standard.components if component.charge_unit == "$/kWh") == pytest.approx(0.19128)
        assert riders["Optional Green Power Block"].sub_component == "optional"
        assert riders["Optional Green Power Block"].charge_unit == "$/block/month"
        assert all(component.source_url == document["source_url"] and component.source_detail for component in standard.components)

    def test_tod_requires_storage_and_preserves_seasonal_windows(self, document):
        record = self.parse(document)["05/06"]
        assert record.rate_structure == "tou"
        assert "Electric Thermal Storage (ETS)" in record.eligibility
        energy = [component for component in record.components if component.component_type == "energy"]
        winter = [component for component in energy if component.season == "winter"]
        shoulder = [component for component in energy if component.season == "non-winter"]
        assert [component.charge_value for component in winter] == [0.24384, 0.19459, 0.24384, 0.11632]
        assert [component.charge_value for component in shoulder] == [0.19459, 0.11632]
        assert all(component.season_months == "12,1,2" for component in winter)
        assert "7:00 AM to 12:00 PM" in winter[0].tou_hours
        assert "4:00 PM to 11:00 PM" in winter[2].tou_hours
        assert "Saturdays, Sundays and statutory holidays" in winter[3].tou_hours

    def test_pilots_use_documented_interim_phase_in_october(self, document):
        records = self.parse(document)
        for code in ("70", "80"):
            record = records[code]
            assert record.rate_structure == "flat"
            assert record.sub_class == "pilot - interim standard pricing"
            assert record.end_date == "2026-10-31"
            energy = [component for component in record.components if component.component_type == "energy"]
            assert len(energy) == 1 and energy[0].charge_value == 0.18324
            assert "closed to new applications" in record.eligibility
            assert "interim provisions apply" in record.eligibility
            assert "Conditional Pilot" in record.tariff_name
            assert "Conditional interim variant only" in record.eligibility
            assert "not a claim that all pilot customers" in record.notes
            assert "2026-11-01" in record.notes
        assert not any(component.charge_value in {0.37321, 1.82871, 0.13213} for record in records.values() for component in record.components)

    def test_pilots_switch_only_on_published_november_date(self, document):
        records = self.parse(document, today="2026-11-01")
        october = self.parse(document)
        tou, cpp = records["80"], records["70"]
        assert all(records[code].tariff_name == october[code].tariff_name for code in ("70", "80"))
        assert tou.effective_date == cpp.effective_date == "2026-11-01"
        assert tou.rate_structure == cpp.rate_structure == "tou"
        assert [component.charge_value for component in tou.components if component.component_type == "energy"] == [0.36517, 0.18324]
        assert [component.charge_value for component in cpp.components if component.component_type == "energy"] == [1.82067, 0.15411]
        assert "No more than 18 Critical Peak Events" in cpp.notes
        assert "Nova Scotia Heritage Day" in tou.notes
        assert all(record.end_date == "2026-12-31" for record in records.values())

    @pytest.mark.parametrize(("page_number", "remaining"), [
        (5, {"05/06", "70", "80"}), (7, {"02/03/04", "70", "80"}),
        (10, {"02/03/04", "05/06", "80"}), (14, {"02/03/04", "05/06", "70"}),
        (66, set()), (75, set()), (79, set()),
    ])
    def test_incomplete_source_sections_fail_by_class(self, document, page_number, remaining):
        document["pages"] = [page for page in document["pages"] if page["page_number"] != page_number]
        assert set(self.parse(document)) == remaining

    def test_missing_equipment_eligibility_rejects_tod_only(self, document):
        page = next(page for page in document["pages"] if page["page_number"] == 7)
        page["text"] = page["text"].replace("Electric Thermal Storage (ETS)", "equipment not specified")
        assert set(self.parse(document)) == {"02/03/04", "70", "80"}

    def test_rider_and_tod_values_follow_live_source(self, document):
        page = next(page for page in document["pages"] if page["page_number"] == 6)
        page["text"] = page["text"].replace("24.384", "26.000")
        record = self.parse(document)["05/06"]
        assert record.components[1].charge_value == 0.26
        page = next(page for page in document["pages"] if page["page_number"] == 66)
        page["text"] = page["text"].replace("0.156", "0.200")
        records = self.parse(document)
        assert all(next(component for component in record.components if component.component_name.startswith("FAM")).charge_value == 0.002 for record in records.values())

    def test_unverified_year_or_missing_source_date_fails_closed(self, document):
        assert not self.parse(document, today="2027-01-01")
        for product in document["products"].values():
            product["html"] = product["html"].replace("Rates updated as of May 1, 2026.", "")
        assert not self.parse(document)

    @pytest.mark.parametrize(("page_number", "old", "new", "rejected"), [
        (6, "cents per kilowatt-hour", "dollars per kilowatt-hour", "05/06"),
        (4, "per month $20.08", "per week $20.08", "02/03/04"),
        (4, "$20.08", "-$20.08", "02/03/04"),
        (12, "cents per\nkilowatt-hour", "dollars per\nkilowatt-hour", "80"),
    ])
    def test_wrong_units_or_negative_fixed_charges_reject_only_affected_class(self, document, page_number, old, new, rejected):
        page = next(page for page in document["pages"] if page["page_number"] == page_number)
        page["text"] = page["text"].replace(old, new)
        assert set(self.parse(document)) == {"02/03/04", "05/06", "70", "80"} - {rejected}

    def test_pilot_requires_current_enrollment_evidence(self, document):
        document["products"]["cpp"]["html"] = document["products"]["cpp"]["html"].replace("are now closed", "status unavailable")
        assert set(self.parse(document)) == {"02/03/04", "05/06", "80"}

    def test_source_column_wrapping_preserves_tou_units(self, document):
        page = next(page for page in document["pages"] if page["page_number"] == 12)
        page["text"] = page["text"].replace(
            "Interim Energy Charge (Non-winter Period) cents per\nkilowatt-hour",
            "Interim Energy Charge (Non- cents per\nwinter Period) kilowatt-hour",
        )
        records = self.parse(document)
        assert records["80"].components[1].charge_value == 0.18324
        page["text"] = page["text"].replace("cents per", "dollars per")
        assert "80" not in self.parse(document)

    def test_residential_sources_are_registered(self, document):
        from scrapers.registry import get_utility

        registered = {source["url"] for source in get_utility("Nova Scotia Power")["sources"]}
        assert {product["source_url"] for product in document["products"].values()} | {document["source_url"]} <= registered

    def test_residential_failure_keeps_business_live(self):
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper

        scraper = NovaScotiaPowerScraper()
        business = scraper._seed_data_rate10()
        with patch.object(scraper, "_try_live_residential", return_value=[]), \
             patch.object(scraper, "_try_live_commercial", return_value=[business]):
            records = scraper.scrape()
        assert len(records) == 4
        assert [record.tariff_code for record in records if "live_parsed" in (record.notes or "")] == ["10"]
        assert all(component.source_url and component.source_detail for record in records if record.tariff_code == "10" for component in record.components)
        assert all(record.confidence == "unverified" for record in records if record.tariff_code != "10")

    def test_business_parse_failure_keeps_residential_live(self, document):
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper

        scraper = NovaScotiaPowerScraper()
        with patch.object(scraper, "_try_live_residential", return_value=list(self.parse(document).values())), \
             patch.object(scraper, "_try_live_commercial", side_effect=ValueError("Malformed business amount")):
            records = scraper.scrape()
        assert len([record for record in records if "live_parsed" in (record.notes or "")]) == 4
        assert {record.tariff_code for record in records if "seed_fallback" in (record.notes or "")} == {"10", "11", "12"}

    def test_residential_dates_components_and_history_survive_export(self, document, tmp_path, monkeypatch):
        import json
        import sqlite3
        from pipeline import export_json
        from pipeline.run_scrape import store_results
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper
        from tests.test_phase5_hardening import database

        records = NovaScotiaPowerScraper().mark_live_parsed(list(self.parse(document).values()))
        connection = database()
        for run_id in (1, 2):
            store_results(records, run_id, connection)
        assert connection.execute("SELECT count(*) FROM tariffs").fetchone()[0] == 4
        assert connection.execute("SELECT count(*) FROM historical_snapshots").fetchone()[0] == 8
        db_path = tmp_path / "rates.db"
        persisted = sqlite3.connect(db_path)
        connection.backup(persisted)
        persisted.close()
        connection.close()
        monkeypatch.setattr(export_json, "DB_PATH", db_path)
        monkeypatch.setattr(export_json, "SITE_DATA_DIR", tmp_path / "site")
        export_json.export_all()
        exported = json.loads((tmp_path / "site" / "rates.json").read_text(encoding="utf-8"))
        assert len(exported) == 4
        assert all(record["provenance"] == "live" for record in exported)
        assert {record["tariff_code"]: len(record["components"]) for record in exported} == {record.tariff_code: len(record.components) for record in records}
        assert {record["end_date"] for record in exported if record["tariff_code"] in {"70", "80"}} == {"2026-10-31"}
        assert all(component["source_url"] and component["source_detail"] for record in exported for component in record["components"])


# ─── BC Hydro ──────────────────────────────────────────────────

class TestBCHydroSeedUpdated:
    @pytest.fixture(autouse=True)
    def setup(self):
        from scrapers.utilities.bc_hydro import BCHydroScraper
        with patch.object(BCHydroScraper, "_try_live_scrape", return_value=None):
            self.scraper = BCHydroScraper()
            self.records = self.scraper.scrape()

    def test_returns_four_tariffs(self):
        assert len(self.records) == 4

    def test_residential_optional_products_are_fetched(self):
        from scrapers.utilities.bc_hydro import BCHydroScraper, RESIDENTIAL_URL

        root = RESIDENTIAL_URL.rsplit("/", 1)[0]
        flat_url = root + "/flat.html"
        time_url = root + "/time-of-day.html"
        html = (
            '<h1>Residential rates</h1>'
            '<p>Residential customers can choose between the flat rate and tiered rate plan, '
            'which can both also be combined with optional time-of-day pricing.</p>'
            f'<a href="{flat_url}">Flat rate</a>'
            f'<a href="{time_url}">Time-of-day pricing</a>'
        )
        scraper = BCHydroScraper()
        with patch.object(scraper, "fetch_page", return_value=html) as fetch, \
             patch.object(scraper, "_parse_business", return_value=None):
            scraper._try_live_scrape()
        fetched = {call.args[0] for call in fetch.call_args_list}
        assert {flat_url, time_url} <= fetched

    def test_residential_is_tiered(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        assert res.rate_structure == "tiered"
        assert res.tariff_code == "1101"

    def test_sgs_has_no_demand_charge(self):
        sgs = [r for r in self.records if r.tariff_code == "1300"][0]
        demand = [c for c in sgs.components if c.component_type == "demand"]
        assert len(demand) == 0, "SGS Rate 1300 should have no demand charge"

    def test_sgs_is_flat(self):
        sgs = [r for r in self.records if r.tariff_code == "1300"][0]
        assert sgs.rate_structure == "flat"

    def test_mgs_present(self):
        mgs = [r for r in self.records if r.tariff_code == "1500"]
        assert len(mgs) == 1, "MGS Rate 1500 should be present"

    def test_mgs_has_demand_charge(self):
        mgs = [r for r in self.records if r.tariff_code == "1500"][0]
        demand = [c for c in mgs.components if c.component_type == "demand"]
        assert len(demand) == 1

    def test_lgs_present(self):
        lgs = [r for r in self.records if r.tariff_code == "1600"]
        assert len(lgs) == 1, "LGS Rate 1600 should be present"

    def test_lgs_has_demand_charge(self):
        lgs = [r for r in self.records if r.tariff_code == "1600"][0]
        demand = [c for c in lgs.components if c.component_type == "demand"]
        assert len(demand) == 1
        assert demand[0].charge_value == pytest.approx(13.83)

    def test_lgs_energy_lower_than_mgs(self):
        lgs = [r for r in self.records if r.tariff_code == "1600"][0]
        mgs = [r for r in self.records if r.tariff_code == "1500"][0]
        lgs_energy = [c for c in lgs.components if c.component_type == "energy"][0]
        mgs_energy = [c for c in mgs.components if c.component_type == "energy"][0]
        assert lgs_energy.charge_value < mgs_energy.charge_value

    def test_effective_dates_updated(self):
        for r in self.records:
            assert r.effective_date == "2026-04-01"


class TestBCHydroResidentialOptions:
    @pytest.fixture
    def document(self):
        import json
        from pathlib import Path

        return json.loads((Path(__file__).parent / "fixtures" / "bc_hydro_residential.json").read_text(encoding="utf-8"))

    @staticmethod
    def parse(document):
        from scrapers.utilities.bc_hydro import BCHydroScraper
        from scrapers.utils.parsing import DocumentPage

        scraper = BCHydroScraper()
        with patch.object(scraper, "now_iso", return_value="2026-10-01T00:00:00+00:00"):
            return {record.tariff_code: record for record in scraper._parse_residential_tariff([DocumentPage(**page) for page in document["pages"]])}

    def test_all_residential_options_and_adjustment_basis(self, document):
        records = self.parse(document)
        assert set(records) == {"1101", "1151", "1105", "1101+2101", "1151+2101"}
        assert records["1101"].tariff_name == "Residential Service (Rate 1101)"
        flat = records["1151"]
        assert flat.components[0].charge_value == 0.25 and flat.components[0].charge_unit == "$/day"
        assert flat.components[1].charge_value == 0.127
        assert flat.effective_date == "2026-04-01"
        assert records["1105"].components[0].charge_value == 0.1261
        assert "2008" in records["1105"].eligibility and "Closed" in records["1105"].tariff_name
        assert records["1101+2101"].rate_structure == "mixed"
        assert records["1151+2101"].rate_structure == "tou"
        for code in ("1101+2101", "1151+2101"):
            record = records[code]
            adjustments = {component.tou_period: component for component in record.components if component.tou_period}
            assert adjustments["overnight"].charge_value == -0.05
            assert adjustments["on-peak"].charge_value == 0.05
            assert adjustments["off-peak"].charge_value == 0
            assert "23:00" in adjustments["overnight"].tou_hours and "07:00" in adjustments["overnight"].tou_hours
            assert "16:00" in adjustments["on-peak"].tou_hours and "21:00" in adjustments["on-peak"].tou_hours
            assert record.effective_date == "2026-07-01"
            percentages = [component for component in record.components if component.charge_unit == "fraction"]
            assert [component.charge_value for component in percentages] == [-0.015, 0]
            assert all("not to RS 2101" in component.notes for component in percentages)
        discount = next(component for component in flat.components if component.sub_component == "conditional")
        assert discount.charge_value == -0.25 and "more than three units" in discount.notes
        assert all(component.source_url == document["source_url"] and component.source_detail for record in records.values() for component in record.components)

    @pytest.mark.parametrize(("page_number", "remaining"), [
        (90, {"1101", "1151", "1105"}),
        (88, {"1101", "1105", "1101+2101"}),
        (233, set()),
    ])
    def test_incomplete_source_sections_fail_closed(self, document, page_number, remaining):
        document["pages"] = [page for page in document["pages"] if page["page_number"] != page_number]
        assert set(self.parse(document)) == remaining

    def test_values_follow_source_and_future_schedule_is_rejected(self, document):
        page = next(page for page in document["pages"] if page["page_number"] == 87)
        page["text"] = page["text"].replace("12.70", "13.20")
        assert self.parse(document)["1151"].components[1].charge_value == 0.132
        for page in document["pages"]:
            if page["page_number"] in {89, 90}:
                page["text"] = page["text"].replace("July 1, 2026", "July 1, 2027")
        assert set(self.parse(document)) == {"1101", "1151", "1105"}

    def test_live_wrapper_preserves_independent_fallbacks(self, document):
        from scrapers.utilities.bc_hydro import BCHydroScraper
        from scrapers.utils.parsing import DocumentPage

        scraper = BCHydroScraper()
        with patch.object(scraper, "fetch_page", return_value="<h1>Residential rates</h1>"), \
             patch.object(scraper, "fetch_bytes", return_value=b"pdf"), \
             patch.object(scraper, "_parse_business", return_value=None), \
             patch("scrapers.utilities.bc_hydro.extract_pdf_pages", return_value=[DocumentPage(**page) for page in document["pages"]]):
            records = scraper.scrape()
        assert len([record for record in records if "live_parsed" in (record.notes or "")]) == 5
        assert len([record for record in records if "seed_fallback" in (record.notes or "")]) == 3

    def test_divergent_monthly_tiers_do_not_borrow_bimonthly_values(self, document):
        page = document["pages"][0]
        page["text"] = page["text"].replace("675 kWh per month @ 11.87", "675 kWh per month @ 13.87")
        assert set(self.parse(document)) == {"1151", "1105", "1151+2101"}

    def test_residential_variants_keep_their_components_in_storage(self, document):
        from pipeline.run_scrape import store_results
        from tests.test_phase5_hardening import database

        records = list(self.parse(document).values())
        connection = database()
        store_results(records, 1, connection)
        store_results(records, 2, connection)
        assert connection.execute("SELECT count(*) FROM tariffs").fetchone()[0] == 5
        assert connection.execute("SELECT count(*) FROM historical_snapshots").fetchone()[0] == 10
        actual = dict(connection.execute(
            "SELECT tariffs.tariff_code, count(rate_components.id) FROM tariffs JOIN rate_components "
            "ON rate_components.tariff_id = tariffs.id GROUP BY tariffs.id"
        ))
        assert actual == {record.tariff_code: len(record.components) for record in records}
        connection.close()


# ─── BC Hydro business ───

from scrapers.utilities.bc_hydro import BCHydroScraper, TARIFF_URL as BCH_TARIFF_URL
from scrapers.utils.parsing import DocumentPage

BCH_FIXTURE = Path(__file__).parent / "fixtures" / "bc_hydro_business.json"
BCH_NAMES = {
    "1300": "Small General Service (Rate 1300)",
    "1500": "Medium General Service (Rate 1500)",
    "1600": "Large General Service (Rate 1600)",
}
BCH_FEES = "Standard Service Charges (Terms and Conditions Section 11)"


def BCH_parse(document):
    scraper = BCHydroScraper()
    with patch.object(scraper, "now_iso", return_value="2026-10-05T00:00:00+00:00"):
        return {r.tariff_name: r for r in scraper._parse_business_tariff([DocumentPage(**p) for p in document["pages"]])}


def BCH_page(document, number):
    return next(p for p in document["pages"] if p["page_number"] == number)


def BCH_comp(record, name):
    return next(c for c in record.components if c.component_name == name)


class TestBCHydroBusinessLive:
    @pytest.fixture
    def document(self):
        return json.loads(BCH_FIXTURE.read_text(encoding="utf-8"))

    def test_all_business_classes_and_fees_parse(self, document):
        records = BCH_parse(document)
        assert set(records) == set(BCH_NAMES.values()) | {BCH_FEES}
        sgs, mgs, lgs = (records[BCH_NAMES[c]] for c in ("1300", "1500", "1600"))
        assert [(c.component_type, c.charge_value, c.charge_unit) for c in sgs.components[:2]] == [
            ("fixed", 0.4089, "$/day"), ("energy", 0.1406, "$/kWh")]
        assert not [c for c in sgs.components if c.component_type == "demand"]
        assert (BCH_comp(mgs, "Basic Charge").charge_value, BCH_comp(mgs, "Demand Charge").charge_value,
                BCH_comp(mgs, "Energy Charge").charge_value) == (0.2999, 6.07, 0.1086)
        assert BCH_comp(mgs, "Demand Charge").charge_unit == "$/kW"
        assert (BCH_comp(lgs, "Demand Charge").charge_value, BCH_comp(lgs, "Energy Charge").charge_value) == (13.83, 0.0679)
        assert (sgs.demand_max_kw, mgs.demand_min_kw, mgs.demand_max_kw, mgs.usage_max, lgs.demand_min_kw) == (35, 35, 150, 550000, 150)
        assert all(r.effective_date == "2026-04-01" and r.tariff_code for r in (sgs, mgs, lgs))
        assert "Minimum Charge: The Basic Charge" in sgs.notes and "November 1 to March 31" in mgs.notes

    def test_discounts_are_conditional_and_riders_separate(self, document):
        records = BCH_parse(document)
        for code, unit in (("1300", "$/kW/month"), ("1500", "$/kW/billing period"), ("1600", "$/kW/billing period")):
            record = records[BCH_NAMES[code]]
            primary = BCH_comp(record, "Conditional Primary Voltage Discount")
            transformer = BCH_comp(record, "Conditional Transformer Ownership Discount")
            assert (primary.charge_value, primary.charge_unit, primary.sub_component) == (-0.015, "fraction", "conditional")
            assert (transformer.charge_value, transformer.charge_unit, transformer.sub_component) == (-0.25, unit, "conditional")
            riders = [c for c in record.components if c.charge_unit == "fraction" and c.component_type == "rider"]
            assert [c.charge_value for c in riders] == [-0.015, 0.0]
            assert "1301" in record.notes or "1501" in record.notes or "1601" in record.notes

    def test_every_component_has_source_date_and_detail(self, document):
        for record in BCH_parse(document).values():
            for c in record.components:
                assert c.effective_date and c.source_url == BCH_TARIFF_URL and c.source_detail, c.component_name

    def test_standard_charge_values_and_units(self, document):
        fees = BCH_parse(document)[BCH_FEES]
        expected = {
            "Service Connection Call-Back Charge": (351.0, "$/call-back"),
            "Metering Work - One Meter": (262.0, "$/meter"),
            "Metering Work - Concurrent with Service Connection": (64.0, "$/meter"),
            "Instrument Metering (CT and PT)": (840.0, "$/installation"),
            "Default Reconnection Charge": (29.2, "$/account"),
            "Overtime Reconnection Charge": (283.0, "$/account"),
            "Refused Access Reconnection Charge": (1070.0, "$/service connection"),
            "Account Charge": (13.5, "$/account"),
            "Late Payment Charge": (0.015, "fraction/month"),
            "Radio-off Meter Charge": (18.3, "$/month"),
            "Radio-off Meter Move Charge": (141.0, "$/move"),
        }
        assert {c.component_name: (c.charge_value, c.charge_unit) for c in fees.components} == expected
        assert fees.effective_date == "2026-04-01" and fees.customer_class == "other"

    @pytest.mark.parametrize(("page_number", "missing"), [
        (105, "1600"),   # rate-schedule variants page
        (99, "1300"),    # rider continuation page
        (101, "1500"),   # variants page
    ])
    def test_missing_page_rejects_only_that_class(self, document, page_number, missing):
        document["pages"] = [p for p in document["pages"] if p["page_number"] != page_number]
        records = BCH_parse(document)
        assert set(records) == (set(BCH_NAMES.values()) - {BCH_NAMES[missing]}) | {BCH_FEES}

    def test_changed_unit_rejects_only_that_class(self, document):
        p = BCH_page(document, 104)
        p["text"] = p["text"].replace("per kW of Billing Demand", "per kVA of Billing Demand")
        assert set(BCH_parse(document)) == {BCH_NAMES["1300"], BCH_NAMES["1500"], BCH_FEES}

    def test_future_date_rejects_only_that_class(self, document):
        for number in (100, 101, 102, 103):
            p = BCH_page(document, number)
            p["text"] = p["text"].replace("April 1, 2026", "April 1, 2027")
        assert set(BCH_parse(document)) == {BCH_NAMES["1300"], BCH_NAMES["1600"], BCH_FEES}

    def test_rider_failure_blocks_classes_but_not_fees(self, document):
        document["pages"] = [p for p in document["pages"] if p["page_number"] != 233]
        assert set(BCH_parse(document)) == {BCH_FEES}

    def test_fee_page_failure_does_not_remove_rates(self, document):
        document["pages"] = [p for p in document["pages"] if p["page_number"] != 81]
        records = BCH_parse(document)
        assert set(BCH_NAMES.values()) <= set(records)
        assert "Account Charge" not in {c.component_name for c in records[BCH_FEES].components}
        assert "Default Reconnection Charge" in {c.component_name for c in records[BCH_FEES].components}

    def test_single_missing_fee_amount_is_omitted(self, document):
        p = BCH_page(document, 79)
        p["text"] = p["text"].replace("Service Connection Call-Back Charge $ 351.00", "Service Connection Call-Back Charge")
        names = {c.component_name for c in BCH_parse(document)[BCH_FEES].components}
        assert "Service Connection Call-Back Charge" not in names and "Account Charge" in names

    def test_values_follow_source(self, document):
        p = BCH_page(document, 100)
        p["text"] = p["text"].replace("10.86", "11.26").replace("$6.07", "$6.57")
        mgs = BCH_parse(document)[BCH_NAMES["1500"]]
        assert BCH_comp(mgs, "Energy Charge").charge_value == 0.1126
        assert BCH_comp(mgs, "Demand Charge").charge_value == 6.57
        p = BCH_page(document, 81)
        p["text"] = p["text"].replace("$ 13.50", "$ 14.50")
        assert {c.component_name: c.charge_value for c in BCH_parse(document)[BCH_FEES].components}["Account Charge"] == 14.5
        p = BCH_page(document, 233)
        p["text"] = p["text"].replace("equal to 0%", "equal to 2%")
        assert [c.charge_value for c in BCH_parse(document)[BCH_NAMES["1300"]].components if c.component_type == "rider"] == [-0.015, 0.02]

    def test_wrapper_marks_business_live_and_keeps_residential_fallback(self, document):
        scraper = BCHydroScraper()
        with patch.object(scraper, "fetch_page", return_value="<h1>Residential rates</h1>"), \
             patch.object(scraper, "fetch_bytes", return_value=b"pdf"), \
             patch("scrapers.utilities.bc_hydro.extract_pdf_pages", return_value=[DocumentPage(**p) for p in document["pages"]]):
            records = scraper.scrape()
        live = {r.tariff_name for r in records if "live_parsed" in (r.notes or "")}
        assert live == set(BCH_NAMES.values()) | {BCH_FEES}
        fallback = {r.tariff_name for r in records if "seed_fallback" in (r.notes or "")}
        assert fallback == {"Residential Service (Rate 1101)"}


# ─── Hydro-Québec ──────────────────────────────────────────────

class TestHydroQuebecUpdated:
    @pytest.fixture(autouse=True)
    def setup(self):
        from scrapers.utilities.hydro_quebec import HydroQuebecScraper
        with patch.object(HydroQuebecScraper, "_try_live_scrape", return_value=None):
            self.scraper = HydroQuebecScraper()
            self.records = self.scraper.scrape()

    def test_returns_three_tariffs(self):
        assert len(self.records) == 3

    def test_effective_dates_updated(self):
        for r in self.records:
            assert r.effective_date == "2026-04-01"

    def test_fallback_confidence_is_unverified(self):
        """A mocked live failure must not present seed rates as freshly verified."""
        for r in self.records:
            assert r.confidence == "unverified"
            assert "seed_fallback" in r.notes

    def test_rate_d_values_updated(self):
        rate_d = [r for r in self.records if r.tariff_code == "D"][0]
        tier1 = [c for c in rate_d.components if c.tier_number == 1][0]
        assert tier1.charge_value == pytest.approx(0.07065)

    def test_rate_m_present(self):
        rate_m = [r for r in self.records if r.tariff_code == "M"]
        assert len(rate_m) == 1
        assert rate_m[0].customer_class == "commercial"


class TestHydroQuebecDomestic:
    @pytest.fixture
    def document(self):
        import json
        from pathlib import Path

        path = Path(__file__).parent / "fixtures" / "hydro_quebec_domestic.json"
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def scrape_document(document, landing_unavailable=False, legacy=False):
        from scrapers.utilities.hydro_quebec import HydroQuebecScraper
        from scrapers.utils.parsing import DocumentPage

        scraper = HydroQuebecScraper()
        pages = [DocumentPage(**page) for page in document["pages"]]
        with patch.object(scraper, "fetch_page", return_value="<h1>Residential rates</h1>", side_effect=ConnectionError("Landing page unavailable") if landing_unavailable else None), \
             patch.object(scraper, "fetch_bytes", return_value=b"pdf"), \
             patch.object(scraper, "now_iso", return_value="2026-10-02T00:00:00+00:00"), \
             patch.object(scraper, "_parse_rate_d", new=scraper._parse_rate_d if legacy else (lambda *_: None)), \
             patch.object(scraper, "_parse_rate_g", new=scraper._parse_rate_g if legacy else (lambda *_: None)), \
             patch.object(scraper, "_parse_rate_m", new=scraper._parse_rate_m if legacy else (lambda *_: None)), \
             patch("scrapers.utilities.hydro_quebec.extract_pdf_text", return_value="\n".join(page.text for page in pages)), \
             patch("scrapers.utilities.hydro_quebec.extract_pdf_pages", return_value=pages, create=True):
            return scraper.scrape()

    def test_dp_dm_rates_are_rebuilt_from_their_own_sections(self, document):
        records = self.scrape_document(document)
        live = {record.tariff_code: record for record in records if "live_parsed" in (record.notes or "")}
        assert set(live) == {"DP", "DM", "DN"}
        dp = live["DP"]
        assert dp.customer_class == "residential" and dp.effective_date == "2026-04-01"
        energy = [component for component in dp.components if component.component_type == "energy"]
        assert [component.charge_value for component in energy] == [0.06878, 0.10458]
        assert energy[0].tier_threshold == 1200
        demand = {component.season: component for component in dp.components if component.component_type == "demand"}
        assert demand["summer"].charge_value == 5.369
        assert demand["winter"].charge_value == 7.266
        assert demand["summer"].season_months == "4,5,6,7,8,9,10,11"
        assert demand["winter"].season_months == "12,1,2,3"
        assert all(component.demand_threshold_kw == 50 for component in demand.values())
        assert not any(component.component_type == "fixed" for component in dp.components)
        assert "13.833" in dp.notes and "20.750" in dp.notes and "65%" in dp.notes
        dm = live["DM"]
        assert "May 31, 2009" in dm.eligibility and "bulk metering" in dm.eligibility
        fixed = next(component for component in dm.components if component.component_type == "fixed")
        assert fixed.charge_value == 0.46154 and fixed.charge_unit == "$/multiplier/day"
        energy = [component for component in dm.components if component.component_type == "energy"]
        assert [component.charge_value for component in energy] == [0.07065, 0.11142]
        assert energy[0].tier_threshold == 40 and energy[0].tier_unit == "kWh/day/multiplier"
        demand = next(component for component in dm.components if component.component_type == "demand")
        assert demand.charge_value == 7.266 and demand.demand_threshold_kw is None
        assert "multiplier" in demand.notes and "50" in demand.notes
        credit = next(component for component in dm.components if component.component_type == "rebate")
        assert credit.charge_value == -0.002818 and credit.charge_unit == "$/kWh"
        assert credit.sub_component == "conditional"
        assert all(component.source_url == document["source_url"] and component.source_detail for record in live.values() for component in record.components)

    def test_dn_off_grid_keeps_territory_multiplier_and_separate_prices(self, document):
        live = {record.tariff_code: record for record in self.scrape_document(document) if "live_parsed" in (record.notes or "")}
        assert set(live) == {"DP", "DM", "DN"}
        dn = live["DN"]
        assert dn.customer_class == "residential" and dn.effective_date == "2026-04-01"
        assert "north of the 53rd parallel" in dn.eligibility
        assert "except the Schefferville system" in dn.eligibility
        assert "multiplier is 1, unless" in dn.notes and "May 31, 2009" in dn.notes
        assert "65%" in dn.notes and "Rate DT described in Chapter 2 does not apply" in dn.notes
        fixed = next(component for component in dn.components if component.component_type == "fixed")
        assert fixed.charge_value == 0.46154 and fixed.charge_unit == "$/multiplier/day"
        energy = [component for component in dn.components if component.component_type == "energy"]
        assert [component.charge_value for component in energy] == [0.07065, 0.50469]
        assert energy[0].tier_threshold == 40 and energy[0].tier_unit == "kWh/day/multiplier"
        assert "grandfathered" not in energy[0].notes
        demand = next(component for component in dn.components if component.component_type == "demand")
        assert demand.charge_value == 7.266 and demand.demand_threshold_kw is None
        assert "50 kilowatts" in demand.notes and "4 kilowatts times the multiplier" in demand.notes
        credit = next(component for component in dn.components if component.component_type == "rebate")
        assert credit.charge_value == -0.002818 and credit.sub_component == "conditional"
        assert "9.2" in credit.notes and "12.3" in credit.notes
        assert len(dn.components) == 5
        assert all(component.source_url == document["source_url"] and component.source_detail for component in dn.components)

    @pytest.mark.parametrize(("page_number", "remaining"), [
        (18, {"DM", "DN"}), (20, {"DP", "DN"}), (11, set()), (152, set()), (154, set()),
        (127, {"DP", "DM"}), (128, {"DP", "DM"}),
    ])
    def test_missing_conditions_fail_closed(self, document, page_number, remaining):
        document["pages"] = [page for page in document["pages"] if page["page_number"] != page_number]
        live = [record for record in self.scrape_document(document) if "live_parsed" in (record.notes or "")]
        assert {record.tariff_code for record in live} == remaining

    @pytest.mark.parametrize(("code", "page_number", "old", "new"), [
        ("DP", 17, "6.878\u00a2", "$6.878"),
        ("DP", 17, "$ 5.369", "$ -5.369"),
        ("DP", 17, "1,200 kilowatthours", "1,200 kilowatts"),
        ("DM", 19, "May 31, 2009", "eligibility unknown"),
        ("DM", 19, "46.154\u00a2", "$46.154"),
        ("DN", 127, "50.469\u00a2", "$50.469"),
        ("DN", 127, "50.469\u00a2", "-50.469\u00a2"),
        ("DN", 127, "46.154\u00a2", "-46.154\u00a2"),
        ("DN", 127, "$7.266", "$-7.266"),
        ("DN", 127, "north of the 53rd parallel", "south of the 53rd parallel"),
        ("DN", 127, "except the Schefferville system", "including the Schefferville system"),
        ("DN", 127, "multiplier is 1, unless", "multiplier is 2, unless"),
        ("DN", 127, "as described in Article 12.3", "as described in Article 12.2"),
        ("DN", 128, "1 for each additional room.", ""),
        ("DN", 128, "65%", "unknown percentage"),
        ("DN", 128, "4 kilowatts times the multiplier", "4 kilovoltamperes times the multiplier"),
        ("DN", 128, "Rate D T described in Chapter 2 does not apply", "Rate D T described in Chapter 2 applies"),
    ])
    def test_tariff_drift_does_not_downgrade_other_class(self, document, code, page_number, old, new):
        page = next(page for page in document["pages"] if page["page_number"] == page_number)
        page["text"] = page["text"].replace(old, new)
        live = [record for record in self.scrape_document(document) if "live_parsed" in (record.notes or "")]
        assert {record.tariff_code for record in live} == {"DP", "DM", "DN"} - {code}

    def test_rates_and_thresholds_follow_source_changes(self, document):
        page = next(page for page in document["pages"] if page["page_number"] == 17)
        page["text"] = page["text"].replace("6.878", "7.125").replace("1,200", "1,500")
        records = self.scrape_document(document)
        dp = next(record for record in records if record.tariff_code == "DP")
        energy = next(component for component in dp.components if component.component_type == "energy")
        assert energy.charge_value == 0.07125 and energy.tier_threshold == 1500

    def test_dn_values_and_rules_follow_source_changes(self, document):
        table = next(page for page in document["pages"] if page["page_number"] == 127)
        table["text"] = table["text"].replace("50.469", "51.125").replace("40 kilowatthours", "45 kilowatthours")
        continuation = next(page for page in document["pages"] if page["page_number"] == 128)
        continuation["text"] = continuation["text"].replace("65%", "70%").replace("50 kilowatts", "60 kilowatts")
        live = {record.tariff_code: record for record in self.scrape_document(document) if "live_parsed" in (record.notes or "")}
        assert set(live) == {"DP", "DM", "DN"}
        energy = [component for component in live["DN"].components if component.component_type == "energy"]
        assert [component.charge_value for component in energy] == [0.07065, 0.51125]
        assert energy[0].tier_threshold == 45
        demand = next(component for component in live["DN"].components if component.component_type == "demand")
        assert "60 kilowatts" in demand.notes and "70%" in live["DN"].notes
        dm_energy = [component.charge_value for component in live["DM"].components if component.component_type == "energy"]
        assert dm_energy == [0.07065, 0.11142]

    def test_missing_or_future_edition_date_cannot_borrow_grandfathering_date(self, document):
        document["pages"][0]["text"] = document["pages"][0]["text"].replace("2026", "2027")
        assert all(record.confidence == "unverified" for record in self.scrape_document(document))
        document["pages"] = document["pages"][1:]
        assert all(record.confidence == "unverified" for record in self.scrape_document(document))

    def test_pdf_nonbreaking_hyphen_preserves_continuation(self, document):
        page = next(page for page in document["pages"] if page["page_number"] == 18)
        page["text"] = page["text"].replace("maximum-demand", "maximum\u2011demand")
        live = [record for record in self.scrape_document(document) if "live_parsed" in (record.notes or "")]
        assert {record.tariff_code for record in live} == {"DP", "DM", "DN"}

    def test_landing_failure_does_not_block_official_pdf(self, document):
        records = self.scrape_document(document, landing_unavailable=True)
        assert {record.tariff_code for record in records if "live_parsed" in (record.notes or "")} == {"DP", "DM", "DN"}

    def test_multiplier_and_seasonal_components_survive_export(self, document, tmp_path, monkeypatch):
        import json
        import sqlite3
        from pipeline import export_json
        from pipeline.run_scrape import store_results
        from tests.test_phase5_hardening import database

        records = [record for record in self.scrape_document(document) if "live_parsed" in (record.notes or "")]
        connection = database()
        for run_id in (1, 2):
            assert store_results(records, run_id, connection) == 3
        assert connection.execute("SELECT count(*) FROM tariffs").fetchone()[0] == 3
        assert connection.execute("SELECT count(*) FROM historical_snapshots").fetchone()[0] == 6
        path = tmp_path / "rates.db"
        persisted = sqlite3.connect(path)
        connection.backup(persisted)
        persisted.close()
        connection.close()
        monkeypatch.setattr(export_json, "DB_PATH", path)
        monkeypatch.setattr(export_json, "SITE_DATA_DIR", tmp_path / "site")
        export_json.export_all()
        exported = json.loads((tmp_path / "site" / "rates.json").read_text(encoding="utf-8"))
        assert len(exported) == 3 and all(record["provenance"] == "live" for record in exported)
        assert {record["tariff_code"]: len(record["components"]) for record in exported} == {record.tariff_code: len(record.components) for record in records}
        dm = next(record for record in exported if record["tariff_code"] == "DM")
        assert any(component["charge_unit"] == "$/multiplier/day" for component in dm["components"])
        assert any(component["tier_unit"] == "kWh/day/multiplier" for component in dm["components"])
        dn = next(record for record in exported if record["tariff_code"] == "DN")
        assert "except the Schefferville system" in dn["eligibility"]
        assert "multiplier is 1, unless" in dn["notes"]
        assert any(component["charge_value"] == 0.50469 for component in dn["components"])
        assert all(component["source_detail"] for record in exported for component in record["components"])


class TestHydroQuebecOptional:
    document = TestHydroQuebecDomestic.document

    @pytest.fixture
    def optional_document(self, document):
        for key in ("dt_pages", "winter_credit_pages", "flex_d_pages"):
            document["pages"].extend(document[key])
        return document

    @staticmethod
    def options(document):
        return {record.tariff_code: record for record in TestHydroQuebecDomestic.scrape_document(document)
                if record.tariff_code in {"DT", "FLEX_D", "WINTER_CREDIT_D"}}

    def test_temperature_events_and_closed_option_remain_distinct(self, optional_document):
        records = self.options(optional_document)
        assert set(records) == {"DT", "FLEX_D", "WINTER_CREDIT_D"}
        dual = records["DT"]
        energy = [component for component in dual.components if component.component_type == "energy"]
        assert [component.charge_value for component in energy] == [0.05131, 0.30001]
        assert all("-12 C or -15 C" in component.tou_period and component.tou_hours is None for component in energy)
        assert "Certificate of Eligibility" in dual.notes and "off-grid" in dual.notes
        assert next(component for component in dual.components if component.component_type == "demand").demand_threshold_kw is None
        flex = records["FLEX_D"]
        assert len(flex.components) == 7
        peak = next(component for component in flex.components if component.tou_period == "peak demand event")
        assert peak.charge_value == 0.46463 and peak.season_months == "12,1,2,3"
        assert peak.tou_hours == "06:00-10:00,16:00-20:00"
        assert "120 h per winter" in peak.notes
        option = records["WINTER_CREDIT_D"]
        assert option.components[0].charge_value == -0.5849
        assert option.components[0].charge_unit == "$/kWh curtailed"
        assert "reference energy" in option.notes.lower()
        assert "15:00" in option.notes
        assert "2026-03-31" in option.notes and "Rate D charges remain separate" in option.notes

    @pytest.mark.parametrize(("page_number", "rejected"), [
        (21, {"DT"}), (22, {"DT"}), (23, {"DT"}), (24, {"DT"}), (128, {"DT"}),
        (29, {"WINTER_CREDIT_D"}), (30, {"WINTER_CREDIT_D"}), (31, {"WINTER_CREDIT_D"}),
        (32, {"FLEX_D"}), (33, {"FLEX_D"}), (34, {"FLEX_D"}),
        (11, {"DT", "FLEX_D", "WINTER_CREDIT_D"}),
    ])
    def test_required_pages_fail_by_optional_product(self, optional_document, page_number, rejected):
        optional_document["pages"] = [page for page in optional_document["pages"] if page["page_number"] != page_number]
        assert set(self.options(optional_document)) == {"DT", "FLEX_D", "WINTER_CREDIT_D"} - rejected

    @pytest.mark.parametrize(("page_number", "old", "new", "rejected"), [
        (22, "46.154", "-46.154", "DT"),
        (22, "5.131", "-5.131", "DT"),
        (21, "Certificate of Eligibility", "undocumented eligibility", "DT"),
        (33, "46.154", "-46.154", "FLEX_D"),
        (33, "4.886", "-4.886", "FLEX_D"),
        (29, "March 31, 2026", "March 31, 2030", "WINTER_CREDIT_D"),
        (29, "reference energy:", "reference removed:", "WINTER_CREDIT_D"),
        (30, "15:00", "unknown time", "WINTER_CREDIT_D"),
    ])
    def test_optional_source_corruption_is_rejected(self, optional_document, page_number, old, new, rejected):
        page = next(page for page in optional_document["pages"] if page["page_number"] == page_number)
        assert old in page["text"]
        page["text"] = page["text"].replace(old, new)
        assert set(self.options(optional_document)) == {"DT", "FLEX_D", "WINTER_CREDIT_D"} - {rejected}


# ─── SaskPower ──────────────────────────────────────────────────

import copy
HQX_EXTRAS = {
    "DN_INUKJUAK", "G9", "FLEX_G", "FLEX_M", "FLEX_G9", "DUAL_ENERGY_SMALL", "DUAL_ENERGY_MEDIUM",
    "DUAL_ENERGY_MEDIUM_LLF", "WINTER_CREDIT_G", "NET_METERING_I", "NET_METERING_III",
}
HQX_CREDIT_CARRIERS = {"G9", "FLEX_M", "FLEX_G9", "DUAL_ENERGY_SMALL", "DUAL_ENERGY_MEDIUM", "DUAL_ENERGY_MEDIUM_LLF", "DN_INUKJUAK"}



HQX_LEGACY_TEXT = (
    "Structure of Rate D 2.5 46.154 \u00a2 system access charge for each day 7.065 \u00a2 per kilowatthour 11.142 \u00a2 per kilowatthour "
    "Structure of Rate G $15.426 system access charge $22.071 per kilowatt of billing demand in excess of 50 kilowatts "
    "12.388 \u00a2 per kilowatthour 9.534 \u00a2 per kilowatthour "
    "Structure of Rate M $18.242 per kilowatt of billing demand 6.292 \u00a2 per kilowatthour 4.666 \u00a2 per kilowatthour"
)


def HQX_build(document, remove=(), edits=(), legacy=False):
    """Scrape the fixture with the new pages merged in; returns {tariff_code: record} for live records."""
    document = copy.deepcopy(document)
    extra = [page for page in document["building_extras_pages"] if page["page_number"] not in remove]
    for page_number, old, new in edits:
        for page in extra:
            if page["page_number"] == page_number:
                assert old in page["text"], (page_number, old)
                page["text"] = page["text"].replace(old, new)
    base = [page for page in document["pages"] if page["page_number"] not in remove]
    document["pages"] = base + extra
    if legacy:
        document["pages"].insert(0, {"page_number": 9999, "text": HQX_LEGACY_TEXT})
    records = TestHydroQuebecDomestic.scrape_document(document, legacy=legacy)
    return {record.tariff_code: record for record in records if "live_parsed" in (record.notes or "")}


def HQX_comp(record, name_part):
    return next(component for component in record.components if name_part in component.component_name)


class TestHydroQuebecBuildingExtrasLive:
    @pytest.fixture
    def document(self):
        return json.loads((Path(__file__).parent / "fixtures" / "hydro_quebec_domestic.json").read_text(encoding="utf-8"))

    def test_all_live_components_carry_source_url_detail_and_date(self, document):
        live = HQX_build(document, legacy=True)
        assert {"D", "G", "M", "DP", "DM", "DN"} <= set(live)
        for code, record in live.items():
            for component in record.components:
                assert component.source_url and component.source_detail and component.effective_date, (code, component.component_name)

    def test_eleven_records_added_beside_existing_live_classes(self, document):
        live = HQX_build(document)
        assert HQX_EXTRAS <= set(live) and {"DP", "DM", "DN"} <= set(live)
        for code in HQX_EXTRAS:
            record = live[code]
            assert record.effective_date == "2026-04-01" and record.confidence != "unverified"
            assert "Provenance: live_parsed" in record.notes
            for component in record.components:
                assert component.source_url == document["source_url"]
                assert component.source_detail and component.effective_date == "2026-04-01"
        for code in HQX_CREDIT_CARRIERS - {"DN_INUKJUAK"}:
            credits = [c for c in live[code].components if c.component_type == "rebate"]
            assert [c.charge_value for c in credits] == [-0.7131, -1.1427, -2.5512, -3.1208, -4.1239]
            assert all(c.sub_component == "conditional" and c.charge_unit == "$/kW/month" for c in credits)

    def test_inukjuak_keeps_multiplier_indexed_tier_and_conditions(self, document):
        record = HQX_build(document)["DN_INUKJUAK"]
        assert record.customer_class == "residential"
        fixed = HQX_comp(record, "System Access")
        assert fixed.charge_value == 0.46154 and fixed.charge_unit == "$/multiplier/day"
        first, second = [c for c in record.components if c.component_type == "energy"]
        assert (first.charge_value, second.charge_value) == (0.07065, 0.21064)
        assert first.tier_threshold == 40 and first.tier_unit == "kWh/day/multiplier"
        assert HQX_comp(record, "Demand").charge_value == 7.266 and HQX_comp(record, "Demand").demand_threshold_kw is None
        credit = HQX_comp(record, "Supply Voltage Credit")
        assert credit.charge_value == -0.002818 and credit.sub_component == "conditional"
        assert "Rate DM on May 31, 2009" in record.notes and "65%" in record.notes
        assert "50.469" in record.notes and "March 31, 2029" in record.notes
        assert "Inukjuak" in record.eligibility

    def test_g9_and_flex_g9_demand_energy_and_conditions(self, document):
        live = HQX_build(document)
        g9 = live["G9"]
        assert g9.customer_class == "commercial" and g9.demand_min_kw == 65
        assert HQX_comp(g9, "Demand Charge").charge_value == 5.292 and HQX_comp(g9, "Demand Charge").charge_unit == "$/kW/month"
        assert HQX_comp(g9, "Energy").charge_value == 0.12611
        excess = HQX_comp(g9, "Excess")
        assert excess.charge_value == 12.95 and excess.sub_component == "conditional"
        surcharge = HQX_comp(g9, "Short-Term")
        assert surcharge.charge_value == 7.542 and surcharge.season == "winter" and surcharge.season_months == "12,1,2,3"
        assert "46.278" in g9.notes and "75%" in g9.notes and "15.426" in g9.notes
        flex = live["FLEX_G9"]
        assert HQX_comp(flex, "Demand Charge").charge_value == 5.292
        assert HQX_comp(flex, "Outside Peak").charge_value == 0.10133 and HQX_comp(flex, "Winter Peak Demand Event").charge_value == 0.62558
        assert HQX_comp(flex, "Summer Energy").charge_value == 0.12611 and HQX_comp(flex, "Summer Energy").season_months == "4,5,6,7,8,9,10,11"
        assert HQX_comp(flex, "Winter Peak Demand Event").tou_hours == "06:00-09:00,16:00-20:00"
        assert "100 h per winter" in HQX_comp(flex, "Winter Peak Demand Event").notes and "17:00" in HQX_comp(flex, "Winter Peak Demand Event").notes

    def test_flex_g_and_flex_m_events_seasons_and_tiers(self, document):
        live = HQX_build(document)
        flex_g = live["FLEX_G"]
        assert flex_g.demand_max_kw == 50
        assert HQX_comp(flex_g, "Monthly System Access").charge_value == 15.426 and HQX_comp(flex_g, "Monthly System Access").charge_unit == "$/month"
        peak = HQX_comp(flex_g, "Winter Peak Demand Event")
        assert peak.charge_value == 0.56516 and peak.season_months == "12,1,2,3" and peak.tou_hours == "06:00-10:00,16:00-20:00"
        assert "120 h per winter" in peak.notes and "15:00" in peak.notes
        assert HQX_comp(flex_g, "Outside Peak").charge_value == 0.10173 and HQX_comp(flex_g, "Summer Energy").charge_value == 0.12388
        flex_m = live["FLEX_M"]
        assert flex_m.demand_max_kw == 5000 and "experimental" in flex_m.sub_class
        assert HQX_comp(flex_m, "Demand Charge").charge_value == 18.242
        assert HQX_comp(flex_m, "Winter Peak Demand Event").charge_value == 0.62558 and HQX_comp(flex_m, "Outside Peak").charge_value == 0.03966
        tiers = [c for c in flex_m.components if c.season == "summer"]
        assert [c.charge_value for c in tiers] == [0.06292, 0.04666] and tiers[0].tier_threshold == 210000
        assert "November 20" in flex_m.notes and "65%" in flex_m.notes

    def test_dual_energy_variants_keep_temperature_zones_and_seasons(self, document):
        live = HQX_build(document)
        for code in ("DUAL_ENERGY_SMALL", "DUAL_ENERGY_MEDIUM", "DUAL_ENERGY_MEDIUM_LLF"):
            record = live[code]
            electric, fuel = [c for c in record.components if c.season == "heating"]
            assert (electric.charge_value, fuel.charge_value) == (0.06995, 0.62558)
            assert electric.season_months == "10,11,12,1,2,3,4" and "-12 C or -15 C" in electric.tou_period and electric.tou_hours is None
            assert all(c.season_months == "5,6,7,8,9" for c in record.components if c.season == "non-heating")
            assert "Certificate of Eligibility" in record.notes and "space heating" in record.notes
        small, medium, low = live["DUAL_ENERGY_SMALL"], live["DUAL_ENERGY_MEDIUM"], live["DUAL_ENERGY_MEDIUM_LLF"]
        assert small.demand_max_kw == 100 and HQX_comp(small, "Demand").charge_value == 22.071 and HQX_comp(small, "Demand").demand_threshold_kw == 50
        assert [c.charge_value for c in small.components if c.tier_number] == [0.12388, 0.09534]
        assert medium.demand_min_kw == 50 and HQX_comp(medium, "Demand").charge_value == 18.242
        assert [c.tier_threshold for c in medium.components if c.tier_number] == [210000, 210000]
        assert low.demand_min_kw == 65 and HQX_comp(low, "Non-Heating Season Demand").charge_value == 5.292
        assert HQX_comp(low, "Excess").charge_value == 12.95 and "no billing demand applies" in low.notes

    def test_winter_credit_g_and_net_metering_prices(self, document):
        live = HQX_build(document)
        credit = live["WINTER_CREDIT_G"]
        assert credit.sub_class == "closed to new enrollment" and credit.demand_max_kw == 50
        assert credit.components[0].charge_value == -0.62558 and credit.components[0].charge_unit == "$/kWh curtailed"
        assert "2026-03-31" in credit.notes and "reference energy" in credit.notes.lower() and "Rate G charges remain separate" in credit.notes
        option_one = live["NET_METERING_I"]
        assert len(option_one.components) == 1 and option_one.components[0].charge_value == -0.0473
        assert option_one.components[0].sub_component == "conditional" and "Rate G" in option_one.notes and "cannot be negative" in option_one.notes
        option_three = live["NET_METERING_III"]
        assert [c.charge_value for c in option_three.components] == [-0.2127, -0.41287, -0.60055]
        assert all(c.charge_unit == "$/kWh injected" for c in option_three.components)
        assert "heavy diesel" in option_three.components[0].component_name

    @pytest.mark.parametrize(("page", "old", "new", "rejected"), [
        (140, "unless the contract was eligible for Rate D M", "unless removed", {"DN_INUKJUAK"}),
        (141, "65%", "165%", {"DN_INUKJUAK"}),
        (49, "$5.292 per kilowatt of billing demand", "$-5.292 per kilowatt of billing demand", {"G9"}),
        (49, "increased by $7.542", "increased by $-7.542", {"G9"}),
        (44, "56.516", "-56.516", {"FLEX_G"}),
        (58, "62.558", "-62.558", {"FLEX_M"}),
        (59, "5,000 kilowatts, the contract ceases", "x kilowatts, the contract ceases", {"FLEX_M"}),
        (61, "10.133", "-10.133", {"FLEX_G9"}),
        (125, "6.995", "-6.995", {"DUAL_ENERGY_SMALL", "DUAL_ENERGY_MEDIUM"}),
        (126, "$12.950", "$-12.950", {"DUAL_ENERGY_MEDIUM_LLF"}),
        (124, "Certificate of Eligibility", "undocumented eligibility", {"DUAL_ENERGY_SMALL", "DUAL_ENERGY_MEDIUM", "DUAL_ENERGY_MEDIUM_LLF"}),
        (42, "62.558", "-62.558", {"WINTER_CREDIT_G"}),
        (40, "March 31, 2026", "March 31, 2030", {"WINTER_CREDIT_G"}),
        (26, "4.730", "-4.730", {"NET_METERING_I"}),
        (132, "41.287", "-41.287", {"NET_METERING_III"}),
    ])
    def test_source_mutation_rejects_only_the_affected_class(self, document, page, old, new, rejected):
        live = HQX_build(document, edits=[(page, old, new)])
        assert set(live) >= {"DP", "DM", "DN"}
        assert HQX_EXTRAS - set(live) == rejected

    @pytest.mark.parametrize(("page", "rejected"), [
        (139, {"DN_INUKJUAK"}), (140, {"DN_INUKJUAK"}), (141, {"DN_INUKJUAK"}),
        (49, {"G9"}), (50, {"G9"}),
        (43, {"FLEX_G"}), (44, {"FLEX_G"}), (45, {"FLEX_G"}),
        (57, {"FLEX_M"}), (58, {"FLEX_M"}), (59, {"FLEX_M"}),
        (60, {"FLEX_G9"}), (61, {"FLEX_G9"}), (62, {"FLEX_G9"}),
        (123, {"DUAL_ENERGY_SMALL", "DUAL_ENERGY_MEDIUM", "DUAL_ENERGY_MEDIUM_LLF"}),
        (125, {"DUAL_ENERGY_SMALL", "DUAL_ENERGY_MEDIUM", "DUAL_ENERGY_MEDIUM_LLF"}), (126, {"DUAL_ENERGY_MEDIUM_LLF"}),
        (40, {"WINTER_CREDIT_G"}), (41, {"WINTER_CREDIT_G"}), (42, {"WINTER_CREDIT_G"}),
        (25, {"NET_METERING_I"}), (26, {"NET_METERING_I"}), (27, {"NET_METERING_I"}), (39, {"NET_METERING_I"}),
        (131, {"NET_METERING_III"}), (132, {"NET_METERING_III"}), (133, {"NET_METERING_III"}),
        (152, HQX_CREDIT_CARRIERS), (11, HQX_EXTRAS),
    ])
    def test_missing_pages_fail_by_class(self, document, page, rejected):
        live = HQX_build(document, remove={page})
        assert HQX_EXTRAS - set(live) == rejected

    def test_published_prices_follow_the_source(self, document):
        live = HQX_build(document, edits=[
            (49, "$5.292", "$6.111"), (58, "$18.242", "$19.500"), (139, "21.064¢", "22.222¢"), (132, "41.287¢", "40.000¢"),
        ])
        assert HQX_comp(live["G9"], "Demand Charge").charge_value == 6.111
        assert HQX_comp(live["FLEX_G9"], "Demand Charge").charge_value == 5.292
        assert HQX_comp(live["FLEX_M"], "Demand Charge").charge_value == 19.5
        assert [c.charge_value for c in live["DN_INUKJUAK"].components if c.component_type == "energy"] == [0.07065, 0.22222]
        assert live["NET_METERING_III"].components[1].charge_value == -0.4

    def test_repeat_storage_and_export_keep_new_classes(self, document, tmp_path, monkeypatch):
        import sqlite3
        from pipeline import export_json
        from pipeline.run_scrape import store_results
        from tests.test_phase5_hardening import database

        live = HQX_build(document)
        records = [live[code] for code in sorted(HQX_EXTRAS)]
        connection = database()
        for run_id in (1, 2):
            assert store_results(records, run_id, connection) == len(records)
        assert connection.execute("SELECT count(*) FROM tariffs").fetchone()[0] == len(records)
        assert connection.execute("SELECT count(*) FROM historical_snapshots").fetchone()[0] == 2 * len(records)
        path = tmp_path / "rates.db"
        with sqlite3.connect(path) as persisted:
            connection.backup(persisted)
        connection.close()
        monkeypatch.setattr(export_json, "DB_PATH", path)
        monkeypatch.setattr(export_json, "SITE_DATA_DIR", tmp_path / "site")
        export_json.export_all()
        exported = json.loads((tmp_path / "site" / "rates.json").read_text(encoding="utf-8"))
        assert {item["tariff_code"]: len(item["components"]) for item in exported} == {record.tariff_code: len(record.components) for record in records}
        assert all(item["provenance"] == "live" for item in exported)


class TestSaskPowerUpdated:
    @pytest.fixture(autouse=True)
    def setup(self):
        from scrapers.utilities.saskpower import SaskPowerScraper
        with patch.object(SaskPowerScraper, "_try_live_scrape", return_value=None):
            self.scraper = SaskPowerScraper()
            self.records = self.scraper.scrape()

    def test_returns_three_tariffs(self):
        assert len(self.records) == 3

    def test_residential_is_flat(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        assert res.rate_structure == "flat"

    def test_demand_commercial_has_demand_charge(self):
        dc = [r for r in self.records if "Demand" in r.tariff_name][0]
        demand = [c for c in dc.components if c.component_type == "demand"]
        assert len(demand) == 1

    def test_effective_dates_present(self):
        for r in self.records:
            assert r.effective_date

    def test_live_pdf_parses_residential(self, residential_document):
        records = self._scrape_transformation_document(residential_document)
        live = [r for r in records if "live_parsed" in (r.notes or "")]
        assert len(live) == 3
        res = next(record for record in live if record.tariff_name == "Residential Service")
        assert res.tariff_name == "Residential Service"
        assert res.source_url.endswith("report-rates-residential.pdf")
        energy = [c for c in res.components if c.component_type == "energy"][0]
        assert energy.charge_value == pytest.approx(0.15476)

    @pytest.fixture
    def transformation_documents(self):
        import json
        from pathlib import Path

        fixture_dir = Path(__file__).parent / "fixtures"
        return {
            name: json.loads((fixture_dir / f"saskpower_{name}_transformation.json").read_text(encoding="utf-8"))
            for name in ("supplied", "customer_owned")
        }

    @staticmethod
    def _scrape_transformation_document(document, broken_residential=False):
        from scrapers.utilities.saskpower import SaskPowerScraper
        from scrapers.utils.parsing import DocumentPage

        pages = [DocumentPage(**page) for page in document["pages"]]
        html = f'<body><a href="{document["source_url"]}">Transformation Rates</a>'
        if broken_residential:
            html += '<a href="/report-rates-residential.pdf">Residential Rates</a>'
        html += '</body>'
        scraper = SaskPowerScraper()

        def fetch_pdf(url):
            if broken_residential and "residential" in url:
                raise ValueError("Broken PDF")
            return b"pdf"

        with patch.object(scraper, "fetch_page", return_value=html), \
             patch.object(scraper, "fetch_bytes", side_effect=fetch_pdf), \
             patch.object(scraper, "now_iso", return_value="2026-10-01T00:00:00+00:00"), \
             patch("scrapers.utilities.saskpower.extract_pdf_pages", return_value=pages):
            return scraper.scrape()

    def test_live_pdf_parses_supplied_transformation_without_residential(self, transformation_documents):
        fixture = transformation_documents["supplied"]
        records = self._scrape_transformation_document(fixture)
        live = {record.tariff_code: record for record in records if "live_parsed" in (record.notes or "")}
        assert set(live) == {"E05", "E06", "E75", "E76", "E37", "E15", "E16", "E17", "E18", "E35"}
        expected = {
            "E05": (75.85, 16750, 0.11964, 21.632), "E06": (75.85, 15500, 0.11964, 21.632),
            "E75": (42.79, 14500, 0.15602, 20.788), "E76": (42.79, 13000, 0.15602, 20.788),
        }
        for code, (basic, threshold, energy_rate, demand_rate) in expected.items():
            record = live[code]
            assert record.effective_date == "2026-02-01"
            assert record.rate_structure == "mixed"
            fixed = [component for component in record.components if component.component_type == "fixed"]
            energy = [component for component in record.components if component.component_type == "energy"]
            demand = [component for component in record.components if component.component_type == "demand"]
            assert fixed[0].charge_value == pytest.approx(basic)
            assert len(energy) == len(demand) == 2
            assert energy[0].tier_threshold == threshold
            assert energy[0].charge_value == pytest.approx(energy_rate)
            assert demand[0].charge_value == 0
            assert demand[0].tier_threshold == 50
            assert demand[0].tier_unit == "kVA"
            assert demand[1].charge_value == pytest.approx(demand_rate)
            assert all(component.demand_unit == "kVA" for component in demand)
            assert all(component.source_url == fixture["source_url"] for component in record.components)
            assert all(component.source_detail for component in record.components)

    @pytest.mark.parametrize(("old", "new"), [
        ("Balance $/kVA $21.632 $21.632", "Balance $/kVA $21.632"),
        ("Balance $/kVA", "Balance $/kW"),
        ("February 1, 2026", "February 1, 2027"),
        ("Effective February 1, 2026", "Effective date unavailable"),
        ("E05 E06", "E06 E05"),
        ("\u00a2/kWh", "$/kWh"),
        ("$21.632", "-$21.632"),
        ("11.964\u00a2", "-11.964\u00a2"),
    ])
    def test_incomplete_schedule_does_not_downgrade_other_classes(self, transformation_documents, old, new):
        document = transformation_documents["supplied"]
        document["pages"][0]["text"] = document["pages"][0]["text"].replace(old, new)
        records = self._scrape_transformation_document(document)
        live = [record for record in records if "live_parsed" in (record.notes or "")]
        assert {record.tariff_code for record in live} == {"E75", "E76", "E37", "E15", "E16", "E17", "E18", "E35"}
        fallback = next(record for record in records if record.tariff_name == "Power Service (Demand)")
        assert fallback.confidence == "unverified"
        assert "seed_fallback" in fallback.notes
        assert all(component.confidence == "unverified" for component in fallback.components)

    def test_changed_values_and_cent_glyph_are_parsed(self, transformation_documents):
        document = transformation_documents["supplied"]
        for page in document["pages"]:
            page["text"] = page["text"].replace("20.788", "22.123").replace("\u00a2", "\ufffd")
        records = self._scrape_transformation_document(document)
        small = next(record for record in records if record.tariff_code == "E75")
        demand = next(component for component in small.components if component.component_type == "demand" and component.tier_number == 2)
        assert demand.charge_value == pytest.approx(22.123)

    def test_broken_residential_pdf_keeps_commercial_live(self, transformation_documents):
        records = self._scrape_transformation_document(transformation_documents["supplied"], broken_residential=True)
        assert {record.tariff_code for record in records if "live_parsed" in (record.notes or "")} == {"E05", "E06", "E75", "E76", "E37", "E15", "E16", "E17", "E18", "E35"}
        residential = next(record for record in records if record.tariff_name == "Residential Service")
        assert residential.confidence == "unverified"

    @pytest.fixture
    def residential_document(self):
        import json
        from pathlib import Path

        fixture = Path(__file__).parent / "fixtures" / "saskpower_residential.json"
        return json.loads(fixture.read_text(encoding="utf-8"))

    def test_residential_standard_bulk_metered_and_diesel(self, residential_document):
        records = self._scrape_transformation_document(residential_document)
        live = [record for record in records if "live_parsed" in (record.notes or "")]
        assert len(live) == 3
        standard = next(record for record in live if record.tariff_name == "Residential Service")
        assert standard.tariff_code == "E01/E03"
        assert standard.components[0].charge_value == 31.16
        assert standard.components[1].charge_value == 0.15476
        bulk = next(record for record in live if record.sub_class == "bulk metered")
        assert bulk.components[0].charge_value == 31.16
        assert bulk.components[0].charge_unit == "$/unit/month"
        assert "closed to new customers" in bulk.eligibility.lower()
        assert "trailer" in bulk.eligibility.lower()
        diesel = next(record for record in live if record.tariff_code == "E04")
        assert diesel.rate_structure == "tiered"
        assert [(component.charge_value, component.tier_threshold) for component in diesel.components] == [
            (31.16, None), (0.15476, 650), (0.60416, 650),
        ]
        assert all(record.customer_class == "residential" and record.effective_date == "2026-02-01" for record in live)
        assert all(component.source_url == residential_document["source_url"] and component.source_detail for record in live for component in record.components)

    @pytest.mark.parametrize(("old", "new"), [
        ("Basic monthly charge $31.16 $31.16", "Basic monthly charge $31.16"),
        ("15.476\u00a2 15.476\u00a2", "15.476\u00a2 17.000\u00a2"),
        ("(\u00a2/kWh)", "($/kWh)"),
        ("Effective February 1, 2026", "Effective February 1, 2027"),
        ("Rate Codes* E01 E03", "Rate Codes* E03 E01"),
    ])
    def test_residential_standard_fails_without_borrowing_diesel_values(self, residential_document, old, new):
        residential_document["pages"][0]["text"] = residential_document["pages"][0]["text"].replace(old, new)
        records = self._scrape_transformation_document(residential_document)
        assert [record.tariff_code for record in records if "live_parsed" in (record.notes or "")] == ["E04"]
        fallback = next(record for record in records if record.tariff_name == "Residential Service")
        assert fallback.confidence == "unverified"

    def test_residential_diesel_rejects_incomplete_tiers(self, residential_document):
        residential_document["pages"][1]["text"] = residential_document["pages"][1]["text"].replace("60.416\u00a2", "unavailable")
        records = self._scrape_transformation_document(residential_document)
        live = [record for record in records if "live_parsed" in (record.notes or "")]
        assert len(live) == 2
        assert all(record.tariff_code == "E01/E03" for record in live)

    def test_residential_bulk_metering_requires_complete_applicability(self, residential_document):
        residential_document["pages"][0]["text"] = residential_document["pages"][0]["text"].replace("closed to new customers", "availability not stated")
        records = self._scrape_transformation_document(residential_document)
        live = [record for record in records if "live_parsed" in (record.notes or "")]
        assert {record.sub_class for record in live} == {"city, town, village and rural", "diesel"}

    def test_residential_values_follow_source_changes(self, residential_document):
        for page in residential_document["pages"]:
            page["text"] = page["text"].replace("31.16", "32.25").replace("15.476", "16.125")
        records = self._scrape_transformation_document(residential_document)
        live = [record for record in records if "live_parsed" in (record.notes or "")]
        assert len(live) == 3
        assert all(record.components[0].charge_value == 32.25 and record.components[1].charge_value == 0.16125 for record in live)

    @pytest.fixture
    def renewable_access_document(self):
        import json
        from pathlib import Path

        fixture = Path(__file__).parent / "fixtures" / "saskpower_renewable_access.json"
        return json.loads(fixture.read_text(encoding="utf-8"))

    def test_renewable_access_voltage_classes(self, renewable_access_document):
        records = self._scrape_transformation_document(renewable_access_document)
        live = {record.tariff_code: record for record in records if "live_parsed" in (record.notes or "")}
        assert set(live) == {"R23", "R24"}
        expected = {"R23": (8151.50, 18.088, 0.05508), "R24": (8731.50, 17.821, 0.04695)}
        for code, values in expected.items():
            record = live[code]
            assert tuple(component.charge_value for component in record.components) == values
            assert record.components[1].demand_unit == "kVA"
            assert record.effective_date == "2026-02-01"
            assert "Renewable Access Service" in record.eligibility
            assert "75 per cent" in record.notes and "preceding 11" in record.notes
            assert all(component.source_url == renewable_access_document["source_url"] for component in record.components)
        page = renewable_access_document["pages"][0]
        page["text"] = page["text"].replace("5.508", "5.608")
        changed = self._scrape_transformation_document(renewable_access_document)
        updated = next(record for record in changed if record.tariff_code == "R23")
        assert updated.components[2].charge_value == 0.05608

    @pytest.mark.parametrize(("old", "new"), [
        ("$18.088 $17.821", "$18.088"),
        ("72kV 100kV & above", "72kV"),
        ("Effective February 1, 2026", "Effective February 1, 2027"),
        ("\u00a2/kWh", "$/kWh"),
    ])
    def test_renewable_access_rejects_invalid_table(self, renewable_access_document, old, new):
        document = renewable_access_document
        assert any("live_parsed" in (record.notes or "") for record in self._scrape_transformation_document(document))
        document["pages"][0]["text"] = document["pages"][0]["text"].replace(old, new)
        records = self._scrape_transformation_document(document)
        assert not any("live_parsed" in (record.notes or "") for record in records)

    def test_renewable_access_requires_billing_demand_continuation(self, renewable_access_document):
        renewable_access_document["pages"] = renewable_access_document["pages"][:1]
        records = self._scrape_transformation_document(renewable_access_document)
        assert not any("live_parsed" in (record.notes or "") for record in records)

    def test_irrigation_diesel_and_unmetered_units(self, transformation_documents):
        records = self._scrape_transformation_document(transformation_documents["supplied"])
        live = {record.tariff_code: record for record in records if "live_parsed" in (record.notes or "")}
        irrigation = live["E37"]
        assert [(component.charge_value, component.charge_unit) for component in irrigation.components] == [
            (283.78, "$/season"), (28.553, "$/HP/season"), (0.10764, "$/kWh"),
        ]
        assert irrigation.components[1].demand_unit == "HP"
        assert irrigation.demand_min_kw is None
        assert all(component.season_months == "2,3,4,5,6,7,8,9,10" for component in irrigation.components)
        assert "Feb" in irrigation.eligibility and "Oct. 31" in irrigation.eligibility
        diesel = live["E35"]
        assert diesel.rate_structure == "tiered"
        assert [(component.charge_value, component.tier_threshold) for component in diesel.components] == [
            (46.36, None), (0.16086, 650), (0.55413, 650),
        ]
        expected = {
            "E15": (4.697, "$/100 W/month"), "E16": (81.66, "$/power supply unit/month"),
            "E17": (1.713, "$/10 W/month"), "E18": (4.687, "$/kVA/month"),
        }
        for code, value_unit in expected.items():
            record = live[code]
            assert len(record.components) == 1
            assert (record.components[0].charge_value, record.components[0].charge_unit) == value_unit
            assert record.effective_date == "2026-02-01"
            assert record.components[0].source_detail
        assert "22.08" in live["E15"].notes and "81.66" not in live["E15"].notes
        assert "34.21" in live["E17"].notes and "X-RAY" not in live["E17"].notes
        assert "cable television" in live["E16"].eligibility

    @pytest.mark.parametrize(("code", "page_number", "old", "new"), [
        ("E16", 6, "Charge per power supply unit per month $81.66", "Charge per power supply unit per month unavailable"),
        ("E15", 6, "100 watt", "100 kW"),
        ("E37", 5, "$/HP/season", "$/kW/season"),
        ("E35", 8, "Balance (\u00a2/kWh) 55.413\u00a2", "Balance unavailable"),
        ("E18", 7, "Flat rate Effective February 1, 2026", "Flat rate Effective February 1, 2027"),
    ])
    def test_single_code_schedules_fail_independently(self, transformation_documents, code, page_number, old, new):
        document = transformation_documents["supplied"]
        page = next(page for page in document["pages"] if page["page_number"] == page_number)
        page["text"] = page["text"].replace(old, new)
        records = self._scrape_transformation_document(document)
        codes = {record.tariff_code for record in records if "live_parsed" in (record.notes or "")}
        assert codes == {"E05", "E06", "E75", "E76", "E37", "E15", "E16", "E17", "E18", "E35"} - {code}

    def test_customer_owned_voltage_tou_and_capacity_classes(self, transformation_documents):
        records = self._scrape_transformation_document(transformation_documents["customer_owned"])
        live = {record.tariff_code: record for record in records if "live_parsed" in (record.notes or "")}
        assert set(live) == {"E07", "E08", "E10", "E12", "E77", "E78", "E82", "E83", "E84", "E22", "E23", "E24", "N22", "N23", "N24"}
        assert all(record.effective_date == "2026-02-01" for record in live.values())
        assert "closed to new customers" in live["E10"].eligibility.lower()
        assert "72" in live["E10"].eligibility
        energy = next(component for component in live["E12"].components if component.component_type == "energy")
        assert energy.charge_value == pytest.approx(0.05536)
        power = live["E82"]
        fixed = next(component for component in power.components if component.component_type == "fixed")
        assert fixed.charge_value == pytest.approx(7022.82)
        energy = {component.tou_period: component for component in power.components if component.component_type == "energy"}
        assert energy["on-peak"].charge_value == 0.07070
        assert energy["off-peak"].charge_value == 0.06070
        assert "7:00" in energy["on-peak"].tou_hours
        assert "statutory holidays" in energy["on-peak"].tou_hours
        assert "preceding 11" in power.notes
        assert "preceding 23" in live["N22"].notes
        assert all(component.demand_unit == "kVA" for record in live.values() for component in record.components if component.component_type == "demand")

    def test_customer_owned_tou_requires_continuation_page(self, transformation_documents):
        document = transformation_documents["customer_owned"]
        document["pages"] = [page for page in document["pages"] if page["page_number"] != 6]
        records = self._scrape_transformation_document(document)
        codes = {record.tariff_code for record in records if "live_parsed" in (record.notes or "")}
        assert not codes.intersection({"E82", "E83", "E84"})
        assert {"E22", "E23", "E24", "N22", "N23", "N24"} <= codes

    def test_customer_owned_wrong_demand_unit_rejects_only_affected_schedule(self, transformation_documents):
        document = transformation_documents["customer_owned"]
        page = next(page for page in document["pages"] if page["page_number"] == 7)
        page["text"] = page["text"].replace("Per kVA", "Per kW")
        records = self._scrape_transformation_document(document)
        codes = {record.tariff_code for record in records if "live_parsed" in (record.notes or "")}
        assert not codes.intersection({"E22", "E23", "E24"})
        assert {"E82", "E83", "E84", "N22", "N23", "N24"} <= codes

    def test_transformation_fixture_sources_are_registered(self, transformation_documents, farm_oilfield_documents, residential_document, renewable_access_document):
        from scrapers.registry import get_utility

        entry = get_utility("SaskPower")
        registered = {source["url"] for source in entry["sources"]}
        documents = list(transformation_documents.values()) + list(farm_oilfield_documents.values()) + [residential_document, renewable_access_document]
        assert {document["source_url"] for document in documents} <= registered

    @pytest.fixture
    def farm_oilfield_documents(self):
        import json
        from pathlib import Path

        return {
            name: json.loads((Path(__file__).parent / "fixtures" / f"saskpower_{name}.json").read_text(encoding="utf-8"))
            for name in ("farm", "oilfield")
        }

    def test_farm_seasonal_and_interruptible_schedules(self, farm_oilfield_documents):
        records = self._scrape_transformation_document(farm_oilfield_documents["farm"])
        live = {record.tariff_code: record for record in records if "live_parsed" in (record.notes or "")}
        assert set(live) == {"E34", "E19", "E41"}
        standard = live["E34"]
        assert standard.customer_class == "other" and standard.sub_class == "farm"
        assert standard.rate_structure == "mixed"
        assert [(component.charge_value, component.charge_unit) for component in standard.components] == [
            (48.02, "$/month"), (0, "$/kVA"), (15.727, "$/kVA"), (0.13852, "$/kWh"), (0.0582, "$/kWh"),
        ]
        assert standard.components[3].tier_threshold == 16000
        assert live["E19"].components[0].charge_value == 659.83
        assert live["E19"].components[0].charge_unit == "$/season"
        interruptible = live["E41"]
        assert interruptible.effective_date == "2026-02-01"
        assert interruptible.components[0].charge_value == 1244.10
        assert interruptible.components[0].charge_unit == "$/meter location/month"
        assert interruptible.components[1].charge_value == 0.08331
        assert "closed to new customers" in interruptible.eligibility.lower()
        assert "1997" in interruptible.notes
        assert all(component.season_months == "2,3,4,5,6,7,8,9,10" for component in interruptible.components)
        assert all(record.demand_min_kw is None for record in live.values())

    def test_oilfield_metering_voltage_and_tou_schedules(self, farm_oilfield_documents):
        records = self._scrape_transformation_document(farm_oilfield_documents["oilfield"])
        live = {record.tariff_code: record for record in records if "live_parsed" in (record.notes or "")}
        assert set(live) == {"E43", "E44", "E86", "E87", "E88", "E46", "E47", "E48"}
        assert live["E43"].components[0].charge_unit == "$/metering point/month"
        assert live["E43"].components[1].charge_value == 18.490
        assert live["E44"].components[1].charge_value == 17.763
        assert "60 per cent" in live["E44"].notes
        assert "100kV & Above" in live["E48"].eligibility
        assert live["E48"].components[2].charge_value == 0.0626
        energy = [component for component in live["E86"].components if component.component_type == "energy"]
        assert [(component.tou_period, component.charge_value) for component in energy] == [("on-peak", 0.0707), ("off-peak", 0.0607)]
        assert "statutory holidays" in energy[0].tou_hours
        assert all(record.effective_date == "2026-02-01" for record in live.values())
        assert all(component.source_url == farm_oilfield_documents["oilfield"]["source_url"] for record in live.values() for component in record.components)

    @pytest.mark.parametrize(("family", "page_number", "old", "new", "rejected"), [
        ("farm", 1, "16,000 kWh/month", "16,000 kVA/month", {"E34"}),
        ("farm", 2, "Basic seasonal charge", "Basic monthly charge", {"E19"}),
        ("farm", 3, "$1,244.10/month", "$1,244.10/season", {"E41"}),
        ("farm", 3, "Effective February 1, 2026", "Effective February 1, 2027", {"E41"}),
        ("oilfield", 1, "per metering point", "per season", {"E43"}),
        ("oilfield", 4, "ON-PEAK ENERGY CONSUMPTION", "Missing on-peak hours", {"E86", "E87", "E88"}),
    ])
    def test_farm_oilfield_failures_are_class_specific(self, farm_oilfield_documents, family, page_number, old, new, rejected):
        document = farm_oilfield_documents[family]
        original = self._scrape_transformation_document(document)
        expected = {record.tariff_code for record in original if "live_parsed" in (record.notes or "")}
        assert expected
        page = next(page for page in document["pages"] if page["page_number"] == page_number)
        page["text"] = page["text"].replace(old, new)
        changed = self._scrape_transformation_document(document)
        assert {record.tariff_code for record in changed if "live_parsed" in (record.notes or "")} == expected - rejected

    def test_farm_and_oilfield_values_follow_source_changes(self, farm_oilfield_documents):
        farm = farm_oilfield_documents["farm"]
        farm["pages"][0]["text"] = farm["pages"][0]["text"].replace("13.852", "14.200")
        record = next(record for record in self._scrape_transformation_document(farm) if record.tariff_code == "E34")
        assert record.components[3].charge_value == 0.142
        oilfield = farm_oilfield_documents["oilfield"]
        oilfield["pages"][-1]["text"] = oilfield["pages"][-1]["text"].replace("6.260", "6.310")
        record = next(record for record in self._scrape_transformation_document(oilfield) if record.tariff_code == "E48")
        assert record.components[2].charge_value == 0.0631

    @pytest.mark.parametrize("unit", ["$/kWh", "\u00a2/kW"])
    def test_residential_rejects_changed_energy_unit(self, unit):
        from scrapers.utilities.saskpower import SaskPowerScraper

        text = (
            "RESIDENTIAL RATES STANDARD RATE Effective February 1, 2026 "
            f"Basic monthly charge $31.16 $31.16 Energy charge ({unit}) 15.476\u00a2 15.476\u00a2"
        )
        assert SaskPowerScraper()._parse_residential_pdf(text, "https://example.com/rates.pdf") is None


class TestYukonEnergyBuildingRates:
    @pytest.fixture
    def documents(self):
        import json
        from pathlib import Path

        fixture = Path(__file__).parent / "fixtures" / "yukon_energy_building_rates.json"
        return json.loads(fixture.read_text(encoding="utf-8"))["documents"]

    @staticmethod
    def scrape_documents(documents):
        from scrapers.utilities.yukon_energy import YukonEnergyScraper
        from scrapers.utils.parsing import DocumentPage

        by_url = {document["source_url"]: document for document in documents.values()}
        html = '<body>' + ''.join(f'<a href="{url}">Current rate schedule</a>' for url in by_url) + '</body>'
        scraper = YukonEnergyScraper()

        def pages(data):
            return [DocumentPage(**page) for page in by_url[data.decode("utf-8")]["pages"]]

        with patch.object(scraper, "fetch_page", return_value=html), \
             patch.object(scraper, "fetch_bytes", side_effect=lambda url: url.encode("utf-8")), \
             patch.object(scraper, "now_iso", return_value="2026-10-01T00:00:00+00:00"), \
             patch("scrapers.utilities.yukon_energy.extract_pdf_text", side_effect=lambda data: '\n'.join(page.text for page in pages(data)), create=True), \
             patch("scrapers.utilities.yukon_energy.extract_pdf_pages", side_effect=pages, create=True):
            return scraper.scrape()

    def test_residential_includes_current_riders_and_relief(self, documents):
        records = self.scrape_documents(documents)
        residential = next(record for record in records if record.tariff_code == "1160")
        riders = {component.component_name: component for component in residential.components if component.component_type == "rider"}
        true_up = next(component for name, component in riders.items() if "J1" in name)
        assert true_up.charge_value == 15.91
        assert true_up.charge_unit == "%"
        assert true_up.effective_date == "2026-04-01"
        fuel = next(component for name, component in riders.items() if "Rider F" in name)
        assert fuel.charge_value == 0.01 and fuel.charge_unit == "$/kWh"
        assert fuel.effective_date == "2026-10-01"
        relief = next(component for component in residential.components if component.component_type == "rebate")
        assert relief.charge_value == -25 and relief.charge_unit == "%"
        assert relief.tier_threshold == 1500 and relief.tier_unit == "kWh"
        assert relief.end_date == "2027-03-31"
        assert "Rider F" in relief.notes
        assert residential.effective_date == "2026-10-01"
        base = [component for component in residential.components if component.component_type in {"fixed", "energy"}]
        assert [component.charge_value for component in base] == [14.65, 0.1214, 0.1282, 0.1399]
        assert all(component.component_name.startswith("Base ") for component in base)
        assert [component.charge_value for name, component in riders.items() if "Base Rate Adjustment" in name] == [14.38, 100.23]
        assert len(residential.components) == 9
        assert all(component.source_url and component.source_detail and component.effective_date for component in residential.components)

    @pytest.mark.parametrize("missing", ["cross_reference", "j1", "fuel", "relief"])
    def test_missing_required_document_does_not_mark_live(self, documents, missing):
        del documents[missing]
        records = self.scrape_documents(documents)
        assert len(records) == 3
        assert all(record.confidence == "unverified" and "seed_fallback" in record.notes for record in records)
        assert all(component.confidence == "unverified" for record in records for component in record.components)

    @pytest.mark.parametrize(("document", "old", "new"), [
        ("cross_reference", "12.14 1.75 12.17 26.05", "-12.14 1.75 12.17 26.05"),
        ("cross_reference", "\u00a2/kWh", "$/kWh"),
        ("cross_reference", "1160 Hydro Non-Govt", "1180 Hydro Govt"),
        ("j1", "Effective: 2026/04/01", "Effective: 2027/04/01"),
        ("j1", "To all electric service retail rates", "To industrial retail rates"),
        ("fuel", "\u00a2 per kWh", "dollars per kWh"),
        ("fuel", "To all classes of service.", "To commercial service only."),
        ("relief", "March 31,\n2027", "September 30,\n2026"),
        ("relief", "Non Government", "Government"),
        ("relief", "includes base rates and Rider J, J1, R and R1", "includes fuel charges"),
    ])
    def test_invalid_component_context_fails_closed(self, documents, document, old, new):
        pages = documents[document]["pages"]
        pages[0]["text"] = pages[0]["text"].replace(old, new)
        records = self.scrape_documents(documents)
        assert not any("live_parsed" in (record.notes or "") for record in records)

    def test_current_rider_values_follow_the_source(self, documents):
        documents["j1"]["pages"][0]["text"] = documents["j1"]["pages"][0]["text"].replace("15.91%", "16.25%")
        documents["fuel"]["pages"][0]["text"] = documents["fuel"]["pages"][0]["text"].replace("1.0 \u00a2", "1.2 \u00a2")
        residential = next(record for record in self.scrape_documents(documents) if record.tariff_code == "1160")
        true_up = next(component for component in residential.components if "J1 -" in component.component_name)
        fuel = next(component for component in residential.components if "Rider F" in component.component_name)
        assert true_up.charge_value == 16.25
        assert fuel.charge_value == 0.012

    def test_yukon_sources_are_registered(self, documents):
        from scrapers.registry import get_utility

        entry = get_utility("Yukon Energy")
        assert {document["source_url"] for document in documents.values()} <= {source["url"] for source in entry["sources"]}

    def test_yukon_component_dates_and_history_survive_storage(self, documents):
        from dataclasses import replace
        from pipeline.run_scrape import store_results
        from tests.test_phase5_hardening import database

        residential = next(record for record in self.scrape_documents(documents) if record.tariff_code == "1160")
        connection = database()
        store_results([replace(residential, effective_date="2024-04-01")], 1, connection)
        store_results([residential], 2, connection)
        assert connection.execute("SELECT count(*) FROM tariffs").fetchone()[0] == 2
        assert connection.execute("SELECT count(*) FROM historical_snapshots").fetchone()[0] == 2
        rebate = connection.execute(
            "SELECT charge_value, charge_unit, tier_threshold, effective_date, end_date, source_url "
            "FROM rate_components WHERE scrape_run_id = 2 AND component_type = 'rebate'"
        ).fetchone()
        assert rebate == (-25, "%", 1500, "2026-10-01", "2027-03-31", documents["relief"]["source_url"])
        assert connection.execute("SELECT count(*) FROM rate_components WHERE scrape_run_id = 2").fetchone()[0] == 9
        connection.close()


class TestSaskEnergyLive:
    @pytest.fixture
    def pages(self):
        import json
        from pathlib import Path

        document = json.loads((Path(__file__).parent / "fixtures" / "saskenergy.json").read_text(encoding="utf-8"))
        return {key: page["text"] for key, page in document["pages"].items()}

    @staticmethod
    def parse(pages):
        from datetime import date
        from scrapers.utilities.saskenergy import SaskEnergyScraper

        return {record.tariff_code: record for record in SaskEnergyScraper().parse_pages(pages, date(2026, 10, 2))}

    def test_complete_service_variants_and_component_periods(self, pages):
        records = self.parse(pages)
        assert set(records) == {"Res", "SC", "LC", "Res-DS", "SC-DS", "LC-DS", "SI"}
        for code, fixed, delivery in (("Res", 26.5, 0.1113), ("SC", 47.5, 0.0887), ("LC", 171.5, 0.0772)):
            record = records[code]
            components = {component.component_type: component for component in record.components}
            assert components["fixed"].charge_value == fixed
            assert components["delivery"].charge_value == delivery
            assert components["commodity"].charge_value == 0.1264
            assert components["commodity"].charge_unit == "$/m³"
            assert components["carbon"].charge_value == 0
            assert components["carbon"].effective_date == "2025-04-01"
            assert components["fixed"].effective_date == "2023-10-01"
            assert record.effective_date == "2025-04-01"
            assert all(component.source_url and component.source_detail for component in record.components)
            delivery_only = records[code + "-DS"]
            assert {component.component_type for component in delivery_only.components} == {"fixed", "delivery", "carbon"}
            assert "not included" in delivery_only.notes and "Gas Retailer" in delivery_only.notes
        assert (records["LC"].usage_min, records["LC"].usage_max) == (100001, 660000)

    @pytest.mark.parametrize("carbon", ["", "unavailable", "As of April 1, 2030, residential charges are zero"])
    def test_missing_carbon_evidence_rejects_incomplete_live_output(self, pages, carbon):
        pages["carbon"] = carbon
        assert self.parse(pages) == {}

    @pytest.mark.parametrize(("old", "new"), [
        ("$0.1113 per m 3", "$0.1113 per kWh"),
        ("$0.1113", "$-0.1113"),
        ("$26.50", "$0.00"),
        ("October 1, 2023", "October 1, 2030"),
    ])
    def test_residential_drift_preserves_complete_commercial_classes(self, pages, old, new):
        assert old in pages["residential"]
        pages["residential"] = pages["residential"].replace(old, new)
        assert set(self.parse(pages)) == {"SC", "SC-DS", "LC", "LC-DS", "SI"}

    def test_source_values_and_retailer_eligibility(self, pages):
        pages["residential"] = pages["residential"].replace("$26.50", "$27.50")
        records = self.parse(pages)
        assert next(component.charge_value for component in records["Res"].components if component.component_type == "fixed") == 27.5
        pages["retailers"] = ""
        assert set(self.parse(pages)) == {"Res", "SC", "LC", "SI"}

    def test_failed_carbon_fetch_returns_only_unverified_seed(self, pages):
        from scrapers.utilities.saskenergy import SaskEnergyScraper, PAGE_URLS

        scraper = SaskEnergyScraper()
        responses = {PAGE_URLS[key]: value for key, value in pages.items()}
        responses[PAGE_URLS["carbon"]] = ""
        with patch.object(scraper, "fetch_page", side_effect=lambda url: responses[url]):
            records = scraper.scrape()
        assert len(records) == 1 and records[0].tariff_code == "Res"
        assert all(record.confidence == "unverified" and "seed_fallback" in record.notes for record in records)


# ─── NL Hydro ──────────────────────────────────────────────────

class TestNLHydroUpdated:
    @pytest.fixture(autouse=True)
    def setup(self):
        from scrapers.utilities.nl_hydro import NLHydroScraper
        with patch.object(NLHydroScraper, "_try_live_scrape", return_value=None):
            self.scraper = NLHydroScraper()
            self.records = self.scraper.scrape()

    def test_returns_three_tariffs(self):
        assert len(self.records) == 3

    def test_rural_residential_energy_updated(self):
        rural = [r for r in self.records if r.sub_class == "rural"][0]
        energy = [c for c in rural.components if c.component_type == "energy"][0]
        assert energy.charge_value == pytest.approx(0.15213)

    def test_labrador_rate_lower_than_island(self):
        rural = [r for r in self.records if r.sub_class == "rural"][0]
        labrador = [r for r in self.records if r.sub_class == "labrador interconnected"][0]
        rural_energy = [c for c in rural.components if c.component_type == "energy"][0]
        lab_energy = [c for c in labrador.components if c.component_type == "energy"][0]
        assert lab_energy.charge_value < rural_energy.charge_value

    def test_effective_dates_updated(self):
        for r in self.records:
            assert r.effective_date == "2026-01-01"

    def test_source_urls_updated(self):
        """All URLs should point to the new path, not the old 404 URL."""
        for r in self.records:
            assert "electicity-rates" in r.source_url


class TestNLHydroLive:
    @pytest.fixture
    def document(self):
        import json
        from pathlib import Path

        return json.loads((Path(__file__).parent / "fixtures" / "nl_hydro.json").read_text(encoding="utf-8"))

    @staticmethod
    def parse(document):
        from datetime import date
        from scrapers.utilities.nl_hydro import NLHydroScraper
        from scrapers.utils.parsing import DocumentPage

        return {record.tariff_code: record for record in NLHydroScraper().parse_schedule_pages(
            [DocumentPage(**page) for page in document["pages"]], document["source_url"], today=date(2026, 10, 2))}

    @staticmethod
    def page(document, code):
        import re

        return next(page for page in document["pages"] if re.search(rf"^RATE NO\. {re.escape(code)}\s*$", page["text"], re.M))

    def test_all_source_classes_keep_components_and_conditions(self, document):
        records = self.parse(document)
        expected = {"1.1": 3, "1.1S": 2, "1.3": 1, "2.1": 7, "2.3": 5, "2.4": 5,
                    "1.2D": 10, "1.2DS": 2, "2.1D": 4, "2.2D": 5,
                    "1.2G": 2, "2.1G": 2, "2.2G": 3,
                    "1.1L": 2, "2.1L": 4, "2.2L": 5, "2.3L": 2, "2.4L": 2}
        assert {code: len(record.components) for code, record in records.items()} == expected
        assert all(record.effective_date == "2026-07-01" for record in records.values())
        assert all("live_parsed" in record.notes for record in records.values())
        fixed = [component for component in records["2.1"].components if component.component_type == "fixed"]
        assert all("Mutually exclusive" in component.notes for component in fixed)
        for code in ("1.1S", "1.2DS"):
            assert "apply together with base Rate" in records[code].notes
            assert all(component.charge_unit == "$/kWh adjustment" for component in records[code].components)
        assert all(component.source_url == document["source_url"] and component.source_detail for record in records.values() for component in record.components)

    @pytest.mark.parametrize(("code", "old", "new", "rejected"), [
        ("1.1", "Effective July 1, 2026", "Effective December 1, 2026", {"1.1", "1.1S"}),
        ("1.1", "Minimum Monthly Charge", "Missing Monthly Condition", {"1.1", "1.1S"}),
        ("1.2D", "Minimum Monthly Charge", "Missing Monthly Condition", {"1.2D", "1.2DS"}),
        ("1.2D", "17.213", "(17.213)", {"1.2D", "1.2DS"}),
        ("2.1", "Minimum Monthly Charge", "Missing Monthly Condition", {"2.1"}),
        ("2.4", "Maximum Monthly Charge", "Missing Maximum Condition", {"2.4"}),
        ("2.3L", "per kVA", "per kW", {"2.3L"}),
        ("1.1S", "12 months", "6 months", {"1.1S"}),
        ("1.1S", "Effective July 1, 2026", "Effective June 1, 2026", {"1.1S"}),
        ("1.2DS", "First Block Only", "Undocumented Block", {"1.2DS"}),
    ])
    def test_incomplete_schedules_reject_only_dependent_classes(self, document, code, old, new, rejected):
        baseline = set(self.parse(document))
        page = self.page(document, code)
        assert old in page["text"]
        page["text"] = page["text"].replace(old, new)
        assert set(self.parse(document)) == baseline - rejected

    def test_energy_follows_the_source_and_missing_page_is_isolated(self, document):
        import re

        page = self.page(document, "1.1L")
        page["text"], replaced = re.subn(r"(@\s*)\d+\.\d+(\s*[¢])", r"\g<1>3.500\2", page["text"])
        assert replaced == 1
        records = self.parse(document)
        assert next(component.charge_value for component in records["1.1L"].components if component.component_type == "energy") == 0.035
        document["pages"].remove(page)
        assert set(self.parse(document)) == set(records) - {"1.1L"}


class TestFortisBCElectricLive:
    @pytest.fixture
    def document(self):
        import json
        from pathlib import Path

        return json.loads((Path(__file__).parent / "fixtures" / "fortisbc_electric.json").read_text(encoding="utf-8"))

    @staticmethod
    def parse(document):
        from datetime import date
        from scrapers.utilities.fortisbc_electric import FortisBCElectricScraper
        from scrapers.utils.parsing import DocumentPage

        with patch("scrapers.utilities.fortisbc_electric._today", return_value=date(2026, 10, 2)):
            return {record.tariff_code: record for record in FortisBCElectricScraper().parse_schedule_pages(
                [DocumentPage(**page) for page in document["pages"]])}

    def test_source_prices_dates_and_conditional_alternatives(self, document):
        records = self.parse(document)
        assert set(records) == {"01", "2A", "20", "21", "22A", "23A"}
        assert all(record.effective_date == "2026-01-01" for record in records.values())
        residential = records["01"]
        assert residential.rate_structure == "flat"
        assert [component.charge_value for component in residential.components] == [49.58, 0.15503]
        assert residential.components[0].charge_unit == "$/two months"
        credit = next(component for component in records["20"].components if component.component_type == "rebate")
        assert credit.charge_value == -1.5 and credit.charge_unit == "%"
        assert credit.sub_component == "conditional"
        demand = [component for component in records["21"].components if component.component_type == "demand"]
        assert {component.demand_unit for component in demand} == {"kW", "kVA"}
        assert "Alternate" in next(component.notes for component in demand if component.demand_unit == "kVA")
        assert all(component.source_url and component.source_detail for record in records.values() for component in record.components)

    @pytest.mark.parametrize(("page_number", "old", "new", "rejected"), [
        (55, "15.503¢", "15.503$", "01"),
        (55, "$49.58", "$0.00", "01"),
        (58, "Effective Date: January 1, 2026", "Effective Date:", "20"),
        (58, "January 1, 2026", "January 1, 2030", "20"),
        (59, "generally greater than 40 kW", "generally greater than", "21"),
        (60, "$13.53 per kVA", "$13.53", "21"),
        (61, "9:00 am - 11:00 am Monday-Friday", "9:00 am - 12:00 pm Monday-Friday", "22A"),
        (62, "28.943", "-28.943", "23A"),
    ])
    def test_corrupt_schedule_is_rejected_independently(self, document, page_number, old, new, rejected):
        page = next(page for page in document["pages"] if page["page_number"] == page_number)
        assert old in page["text"]
        page["text"] = page["text"].replace(old, new)
        assert set(self.parse(document)) == {"01", "2A", "20", "21", "22A", "23A"} - {rejected}

    def test_closed_plan_needs_source_notice_and_continuation(self, document):
        import re

        page = next(page for page in document["pages"] if page["page_number"] == 56)
        page["text"], changed = re.subn(r"closed", "unspecified", page["text"], flags=re.I)
        assert changed
        assert "2A" not in self.parse(document)
        document["pages"] = [page for page in document["pages"] if page["page_number"] != 60]
        assert "21" not in self.parse(document)

    def test_price_follows_source(self, document):
        page = next(page for page in document["pages"] if page["page_number"] == 55)
        page["text"] = page["text"].replace("15.503", "16.000")
        assert self.parse(document)["01"].components[1].charge_value == 0.16


# ─── FortisBC Electric large commercial ───

from datetime import date

FBE_ALL_CODES = {"01", "2A", "20", "21", "22A", "23A", "30", "32", "85"}
FBE_NEW_CODES = {"30", "32", "85"}


class TestFortisBCElectricLargeCommercialLive:
    @pytest.fixture
    def document(self):
        path = Path(__file__).parent / "fixtures" / "fortisbc_electric.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["pages"] = document["pages"] + document["large_commercial_pages"]
        return document

    @staticmethod
    def parse(document):
        from scrapers.utilities.fortisbc_electric import FortisBCElectricScraper
        from scrapers.utils.parsing import DocumentPage

        with patch("scrapers.utilities.fortisbc_electric._today", return_value=date(2026, 10, 5)):
            return {record.tariff_code: record for record in FortisBCElectricScraper().parse_schedule_pages(
                [DocumentPage(**page) for page in document["pages"]])}

    def test_existing_six_unchanged_without_new_pages(self, document):
        base = dict(document, pages=[p for p in document["pages"] if p["page_number"] < 63])
        assert set(self.parse(base)) == FBE_ALL_CODES - FBE_NEW_CODES

    def test_source_values_units_and_eligibility(self, document):
        records = self.parse(document)
        assert set(records) == FBE_ALL_CODES
        rs30 = records["30"]
        values = {(c.component_name, c.charge_unit): c.charge_value for c in rs30.components}
        assert values[("Customer Charge", "$/month")] == 1252.43
        assert values[("Demand Charge", "$/kVA")] == 12.18
        assert values[("Energy Charge", "$/kWh")] == 0.07384
        assert values[("Transmission Metering Voltage Discount", "%")] == -1.5
        assert values[("Customer-Supplied Transformation Discount", "$/kVA")] == -6.197
        credits = [c for c in rs30.components if c.component_type == "rebate"]
        assert credits and all(c.sub_component == "conditional" for c in credits)
        assert "500 kVA" in rs30.eligibility and rs30.demand_min_kw is None
        assert rs30.effective_date == "2026-01-01"
        demand = next(c for c in rs30.components if c.component_type == "demand")
        assert demand.demand_unit == "kVA" and "75%" in demand.notes

        rs32 = records["32"]
        energy = {c.component_name: c.charge_value for c in rs32.components if c.component_type == "energy"}
        assert energy == {
            "Winter On-Peak Energy Charge": 0.30051, "Winter Off-Peak Energy Charge": 0.06127,
            "Summer On-Peak Energy Charge": 0.28851, "Summer Off-Peak Energy Charge": 0.04768,
            "Shoulder On-Peak Energy Charge": 0.0692, "Shoulder Off-Peak Energy Charge": 0.03651,
        }
        assert next(c for c in rs32.components if c.component_type == "fixed").charge_value == 2959.53
        assert rs32.rate_structure == "tou" and "500 kVA" in rs32.eligibility

        rs85 = records["85"]
        assert [(c.charge_value, c.charge_unit, c.sub_component) for c in rs85.components] == [(0.015, "$/kWh", "optional")]
        assert "$2.50 per month" in rs85.components[0].notes
        assert rs85.effective_date == "2019-07-01"

        assert all(c.effective_date and c.source_url and c.source_detail
                   for code in FBE_NEW_CODES for c in records[code].components)

    def test_industrial_schedules_are_not_emitted(self, document):
        assert not {"31", "33", "37", "38"} & set(self.parse(document))

    @pytest.mark.parametrize(("page_number", "old", "new", "rejected"), [
        (63, "$12.18 per kVA", "$12.18", "30"),
        (63, "7.384¢", "7.384$", "30"),
        (63, "$1,252.43 per Month", "$0.00 per Month", "30"),
        (64, "discount of $6.197 per kVA", "discount of $6.197", "30"),
        (64, "A discount of 1.5%", "A discount of 150%", "30"),
        (66, "10:00 pm to 7:00 am business days", "10:00 pm to 8:00 am business days", "32"),
        (66, "Effective Date: January 1, 2026", "Effective Date: January 1, 2030", "32"),
        (92, "1.500¢ per kW.h", "1.500$ per kW.h", "85"),
        (92, "$2.50 per", "per", "85"),
    ])
    def test_corrupt_schedule_is_rejected_independently(self, document, page_number, old, new, rejected):
        page = next(p for p in document["large_commercial_pages"] if p["page_number"] == page_number)
        assert old in page["text"]
        page["text"] = page["text"].replace(old, new)
        document["pages"] = [p for p in document["pages"] if p["page_number"] < 63] + document["large_commercial_pages"]
        assert set(self.parse(document)) == FBE_ALL_CODES - {rejected}

    def test_missing_continuation_rejects_only_rs30(self, document):
        document["pages"] = [p for p in document["pages"] if p["page_number"] != 64]
        assert set(self.parse(document)) == FBE_ALL_CODES - {"30"}

    def test_price_follows_source(self, document):
        for page in document["pages"]:
            if page["page_number"] == 63:
                page["text"] = page["text"].replace("12.18", "13.00").replace("7.384", "7.500")
            if page["page_number"] == 92:
                page["text"] = page["text"].replace("1.500", "2.000")
        records = self.parse(document)
        rs30 = {c.component_name: c.charge_value for c in records["30"].components}
        assert rs30["Demand Charge"] == 13.0 and rs30["Energy Charge"] == 0.075
        assert records["85"].components[0].charge_value == 0.02


class TestCentraGasLive:
    @pytest.fixture
    def document(self):
        import json
        from pathlib import Path

        return json.loads((Path(__file__).parent / "fixtures" / "centra_gas.json").read_text(encoding="utf-8"))

    @staticmethod
    def parse(document):
        from datetime import date
        from scrapers.utilities.centra_gas import CentraGasScraper

        return {record.tariff_code: record for record in CentraGasScraper().parse_pages(
            {key: page["text"] for key, page in document["pages"].items()}, date(2026, 10, 2))}

    def test_native_units_supply_choices_and_component_dates(self, document):
        records = self.parse(document)
        assert len(records) == 12
        by_name = {record.tariff_name: record for record in records.values()}
        for name, expected in document["expected"]["classes"].items():
            record = by_name[name]
            assert record.effective_date == "2026-08-01"
            assert len(record.components) == expected["components"]
            assert next(component.charge_value for component in record.components if component.component_type == "fixed") == expected["basic"]
            carbon = next(component for component in record.components if component.component_type == "carbon")
            assert carbon.charge_value == 0 and carbon.effective_date == "2025-04-01"
        assert next(component.charge_value for component in records["SGS"].components if component.component_type == "commodity") == 0.066
        assert all(component.component_type != "commodity" for code, record in records.items() if code.endswith(("-T", "-MKT")) for component in record.components)
        assert all(component.charge_unit == "$/m³/month" for record in records.values() for component in record.components if component.component_type == "demand")
        assert all(component.source_url and component.source_detail for record in records.values() for component in record.components)

    @pytest.mark.parametrize(("key", "old", "new", "count"), [
        ("carbon", "Manitoba, ", "", 0),
        ("carbon", "Beginning April 1, 2025 On", "Beginning April 1, 2027 On", 0),
        ("supply", "$0.0660 (Aug. 1, 2026)", "$0.0700 (Aug. 1, 2026)", 3),
        ("commercial", "Demand 36.97", "Demand 37.97", 11),
        ("commercial", "Alternate supply service 1.29¢/m 3 Delivery is", "Delivery is", 11),
        ("commercial", "Delivery 11.32¢/m 3", "Delivery 11.32/m 3", 10),
        ("supply", "we will continue to provide all other components", "we may provide", 9),
        ("residential", "Rates effective August 1, 2026 Effective August 1, 2026", "Rates effective August 1, 2027 Effective August 1, 2027", 10),
        ("commercial", "Charge Cost Basic monthly charge $85.00", "Charge Cost Minimum $5.00 Basic monthly charge $85.00", 10),
    ])
    def test_required_source_failure_is_not_hidden(self, document, key, old, new, count):
        assert old in document["pages"][key]["text"]
        document["pages"][key]["text"] = document["pages"][key]["text"].replace(old, new)
        assert len(self.parse(document)) == count

    def test_basic_charge_follows_source(self, document):
        document["pages"]["commercial"]["text"] = document["pages"]["commercial"]["text"].replace("$85.00", "$86.00")
        record = self.parse(document)["COM-LGS"]
        assert next(component.charge_value for component in record.components if component.component_type == "fixed") == 86


def _gas_fixture(name):
    import json
    from pathlib import Path

    return json.loads((Path(__file__).parent / "fixtures" / f"{name}.json").read_text(encoding="utf-8"))


class TestFortisBCEnergyLive:
    @pytest.fixture
    def document(self):
        return _gas_fixture("fortisbc_energy")

    @staticmethod
    def parse(document):
        from datetime import date
        from scrapers.utilities.fortisbc_energy import FortisBCEnergyScraper

        return {record.tariff_name: record for record in FortisBCEnergyScraper().parse_pages(
            {key: page["text"] for key, page in document["pages"].items()}, date(2026, 10, 5))}

    def test_service_areas_native_units_and_dates(self, document):
        records = self.parse(document)
        assert set(records) == {
            "Residential — Rate 1", "Residential — Rate 1 (Fort Nelson)", "Commercial — Rate 2",
            "Commercial — Rate 2 (Fort Nelson)", "Commercial — Rate 3", "Commercial — Rate 3 (Fort Nelson)"}
        for record in records.values():
            assert record.effective_date == "2026-07-01"
            units = {component.component_type: component.charge_unit for component in record.components}
            assert units == {"fixed": "$/day", "delivery": "$/GJ", "transmission": "$/GJ", "commodity": "$/GJ", "carbon": "$/GJ"}
            carbon = next(component for component in record.components if component.component_type == "carbon")
            assert carbon.charge_value == 0 and carbon.effective_date == "2025-04-01"
            assert all(component.source_url and component.source_detail for component in record.components)
        assert records["Residential — Rate 1"].components[1].charge_value == 8.469
        assert records["Residential — Rate 1 (Fort Nelson)"].components[2].charge_value == 0.987
        assert records["Commercial — Rate 2"].usage_max == 2000 and records["Commercial — Rate 3"].usage_min == 2000
        assert "Revelstoke" not in " ".join(records)

    @pytest.mark.parametrize(("key", "old", "new", "count"), [
        ("carbon", "Carbon tax was eliminated effective April 1, 2025.", "Carbon tax applies.", 0),
        ("carbon", "effective April 1, 2025.", "effective April 1, 2027.", 0),
        ("residential", "Delivery charge per GJ $8.114", "Delivery charge per GJ 8.114", 5),
        ("residential", "(Effective July 1, 2026) Basic charge per day $0.4216 Delivery charge per gigajoule",
         "(Effective July 1, 2027) Basic charge per day $0.4216 Delivery charge per gigajoule", 5),
        ("business", "Rate 3 You are", "Rate 3 is for", 2),
        ("business", "use less than 2,000 gigajoules (GJ) annually", "use some gas", 4),
        ("business", "Cost of gas per GJ $1.660", "Cost of gas per GJ $0.000", 5),
    ])
    def test_required_source_failure_is_not_hidden(self, document, key, old, new, count):
        assert old in document["pages"][key]["text"]
        document["pages"][key]["text"] = document["pages"][key]["text"].replace(old, new, 1)
        assert len(self.parse(document)) == count

    def test_price_follows_source(self, document):
        document["pages"]["business"]["text"] = document["pages"]["business"]["text"].replace("$4.3526", "$4.5000", 1)
        assert self.parse(document)["Commercial — Rate 3"].components[0].charge_value == 4.5


class TestFortisBCEnergyRate5Live:
    @pytest.fixture
    def document(self):
        return _gas_fixture("fortisbc_energy")

    @staticmethod
    def parse(document):
        from datetime import date
        from scrapers.utilities.fortisbc_energy import FortisBCEnergyScraper

        pages = {key: page["text"] for key, page in document["pages"].items()}
        urls = {key: document["pages"][key]["url"] for key in ("rate4", "rate5")}
        return {record.tariff_name: record for record in FortisBCEnergyScraper().parse_pages(
            pages, date(2026, 10, 5), document_urls=urls)}

    @staticmethod
    def values(record, season=None):
        return {(c.component_type, c.component_name, c.season): (c.charge_value, c.charge_unit)
                for c in record.components if season is None or c.season in (None, season)}

    def test_old_call_without_documents_is_unchanged(self, document):
        from datetime import date
        from scrapers.utilities.fortisbc_energy import FortisBCEnergyScraper

        pages = {key: page["text"] for key, page in document["pages"].items()}
        assert len(FortisBCEnergyScraper().parse_pages(pages, date(2026, 10, 5))) == 6

    def test_rate5_components_units_and_eligibility(self, document):
        records = self.parse(document)
        assert len(records) == 8
        rate5 = records["Commercial — Rate 5"]
        assert rate5.tariff_code == "Rate 5" and rate5.customer_class == "commercial"
        assert rate5.effective_date == "2026-07-01"
        assert rate5.usage_min == 5000 and rate5.usage_unit == "GJ/year"
        assert "written contract only" in rate5.eligibility and "5,000 GJ" in rate5.eligibility
        assert "Minimum monthly charge" in rate5.notes
        assert {(c.component_name, c.charge_value, c.charge_unit) for c in rate5.components} == {
            ("Basic Charge", 469.00, "$/month"),
            ("Rider 2 (Clean Growth Innovation Fund Account)", 0.40, "$/month"),
            ("Demand Charge", 37.735, "$/GJ/month of daily demand"),
            ("Delivery Charge", 1.352, "$/GJ"),
            ("Storage and Transport Charge", 0.784, "$/GJ"),
            ("Cost of Gas", 1.660, "$/GJ"),
            ("Rider 6 (Midstream Cost Reconciliation Account)", 0.126, "$/GJ"),
            ("Rider 8 (Storage and Transport RNG)", 0.909, "$/GJ"),
            ("BC Carbon Tax", 0.0, "$/GJ"),
        }
        carbon = next(c for c in rate5.components if c.component_type == "carbon")
        assert carbon.effective_date == "2025-04-01"
        for component in rate5.components:
            assert component.source_url and component.source_detail and component.effective_date
        assert all(c.effective_date == "2026-07-01" for c in rate5.components if c is not carbon)
        assert not any("Fort Nelson" in name for name in records if "Rate 4" in name or "Rate 5" in name)

    def test_rate4_seasonal_components(self, document):
        rate4 = self.parse(document)["Commercial — Rate 4"]
        assert rate4.tariff_code == "Rate 4" and rate4.effective_date == "2026-07-01"
        assert "written consent only" in rate4.eligibility and "April 1 and November 1" in rate4.eligibility
        assert "$20.00/GJ" in rate4.notes
        got = {(c.component_name, c.season): (c.charge_value, c.charge_unit) for c in rate4.components}
        assert got[("Basic Charge", None)] == (14.4230, "$/day")
        assert got[("Rider 2 (Clean Growth Innovation Fund Account)", None)] == (0.0131, "$/day")
        assert got[("Delivery Charge", "Off-Peak Period")] == (2.204, "$/GJ")
        assert got[("Delivery Charge", "Extension Period")] == (3.268, "$/GJ")
        assert got[("Cost of Gas", "Off-Peak Period")] == got[("Cost of Gas", "Extension Period")] == (1.660, "$/GJ")
        assert got[("Storage and Transport Charge", "Off-Peak Period")] == (0.784, "$/GJ")
        assert got[("Rider 8 (Storage and Transport RNG)", None)] == (0.909, "$/GJ")
        off = next(c for c in rate4.components if c.season == "Off-Peak Period")
        assert off.season_months == "April 1 to November 1"

    @pytest.mark.parametrize(("key", "old", "new", "missing"), [
        ("rate5", "Demand Charge per Month per Gigajoule of Daily Demand1 $ 37.735",
         "Demand Charge per Month per Gigajoule of Daily Demand1 37.735", "Commercial — Rate 5"),
        ("rate5", "Subtotal of per Month Delivery Margin Related Charges $ 469.40",
         "Subtotal of per Month Delivery Margin Related Charges $ 470.40", "Commercial — Rate 5"),
        ("rate5", "Effective Date: July 1, 2026", "Effective Date: July 1, 2027", "Commercial — Rate 5"),
        ("business_rate45", "Rate 5 is authorized by written contract only", "Rate 5 is open to all",
         "Commercial — Rate 5"),
        ("rate4", "(b) Extension Period $ 3.268", "(b) Extension Period 3.268", "Commercial — Rate 4"),
        ("rate4", "Subtotal of per Day Delivery Margin Related Charges $ 14.4361",
         "Subtotal of per Day Delivery Margin Related Charges $ 14.5000", "Commercial — Rate 4"),
        ("rate4", "Effective Date: July 1, 2026", "Effective Date: July 1, 2027", "Commercial — Rate 4"),
        ("business_rate45", "Rate 4 is authorized by written consent only", "Rate 4 is open to all",
         "Commercial — Rate 4"),
    ])
    def test_each_rate_fails_closed_independently(self, document, key, old, new, missing):
        assert old in document["pages"][key]["text"]
        document["pages"][key]["text"] = document["pages"][key]["text"].replace(old, new)
        records = self.parse(document)
        assert missing not in records
        other = {"Commercial — Rate 5", "Commercial — Rate 4"} - {missing}
        assert other <= set(records) and len(records) == 7

    def test_carbon_evidence_still_required(self, document):
        document["pages"]["carbon"]["text"] = "Carbon tax applies."
        assert self.parse(document) == {}

    def test_price_follows_source(self, document):
        page = document["pages"]["rate5"]
        page["text"] = page["text"].replace("$ 37.735", "$ 40.000", 1)
        rate5 = self.parse(document)["Commercial — Rate 5"]
        assert next(c.charge_value for c in rate5.components if c.component_type == "demand") == 40.0
        page = document["pages"]["rate4"]
        page["text"] = page["text"].replace("Off-Peak Period $ 2.204", "Off-Peak Period $ 2.500", 1)
        rate4 = self.parse(document)["Commercial — Rate 4"]
        assert next(c.charge_value for c in rate4.components
                    if c.component_type == "delivery" and c.season == "Off-Peak Period") == 2.5


FBEX_NAME = "Residential — Rate 1 (Revelstoke propane)"


class TestFortisBCEnergyRevelstokeLive:
    @pytest.fixture
    def document(self):
        return _gas_fixture("fortisbc_energy")

    @staticmethod
    def parse(document, replace=None):
        from scrapers.utilities.fortisbc_energy import FortisBCEnergyScraper

        pages = {key: page["text"] for key, page in document["pages"].items()}
        pages["residential"] += " " + document["revelstoke_residential"]["text"]
        if replace:
            pages["residential"] = pages["residential"].replace(*replace)
        return {r.tariff_name: r for r in FortisBCEnergyScraper().parse_pages(pages, date(2026, 10, 5))}

    def test_revelstoke_propane_record(self, document):
        records = self.parse(document)
        assert len(records) == 7 and FBEX_NAME in records
        record = records[FBEX_NAME]
        assert record.effective_date == "2026-07-01" and record.sub_class == "Revelstoke (propane)"
        values = {c.component_type: (c.charge_value, c.charge_unit) for c in record.components}
        assert values == {"fixed": (0.4216, "$/day"), "delivery": (8.469, "$/GJ"), "transmission": (2.472, "$/GJ"),
                          "commodity": (1.66, "$/GJ"), "carbon": (0.0, "$/GJ")}
        assert all(c.effective_date and c.source_url and c.source_detail for c in record.components)
        carbon = next(c for c in record.components if c.component_type == "carbon")
        assert carbon.effective_date == "2025-04-01" and "motor fuel tax applies to propane" in carbon.notes

    def test_existing_records_unchanged_by_revelstoke(self, document):
        records = self.parse(document)
        assert len([n for n in records if "Revelstoke" not in n]) == 6

    @pytest.mark.parametrize("replace", [
        ("Revelstoke (Effective July 1, 2026)", "Revelstoke (Effective July 1, 2027)"),
        ("Revelstoke (Effective July 1, 2026) Basic charge per day $0.4216 Delivery charge per GJ $8.469 Storage and transport charge per GJ $2.472 Cost of gas per GJ $1.660",
         "Revelstoke (Effective July 1, 2026) Basic charge per day $0.4216 Delivery charge per GJ $8.469 Storage and transport charge per GJ $2.472 Cost of gas per GJ"),
        ("Revelstoke (Effective July 1, 2026) Basic charge per day $0.4216 Delivery charge per GJ $8.469",
         "Revelstoke (Effective July 1, 2026) Basic charge per day $0.4216 Delivery charge per GJ 8.469"),
    ])
    def test_failure_is_isolated(self, document, replace):
        records = self.parse(document, replace)
        assert FBEX_NAME not in records and len(records) == 6

    def test_missing_table_yields_no_record(self, document):
        from scrapers.utilities.fortisbc_energy import FortisBCEnergyScraper

        pages = {key: page["text"] for key, page in document["pages"].items()}
        assert FBEX_NAME not in {r.tariff_name for r in FortisBCEnergyScraper().parse_pages(pages, date(2026, 10, 5))}


class TestHeritageGasLive:
    @pytest.fixture
    def document(self):
        return _gas_fixture("heritage_gas")

    @staticmethod
    def parse(document):
        from datetime import date
        from scrapers.utilities.heritage_gas import HeritageGasScraper

        return {record.tariff_code: record for record in HeritageGasScraper().parse_pages(
            {key: page["text"] for key, page in document["pages"].items()}, date(2026, 10, 5),
            table_url=document["pages"]["rate_table"]["url"])}

    def test_classes_components_and_tiers(self, document):
        records = self.parse(document)
        assert set(records) == {"Residential", "GS"}
        residential, general = records["Residential"], records["GS"]
        assert residential.effective_date == general.effective_date == "2026-10-01"
        assert [c.charge_value for c in residential.components if c.component_type in ("fixed", "delivery", "commodity")] == [29.0, 12.349, 12.49]
        tiers = [(c.charge_value, c.tier_threshold) for c in general.components if c.component_type == "delivery"]
        assert tiers == [(9.142, 15.0), (5.943, 415.0), (5.693, None)]
        assert general.usage_max == 50000 and "Rate Class 3" in general.eligibility
        for record in records.values():
            carbon = next(c for c in record.components if c.component_type == "carbon")
            assert carbon.charge_value == 0 and carbon.effective_date == "2025-04-01"
            assert [c.charge_value for c in record.components if c.charge_unit == "%"] == [5.0, 0.6]
            assert all(c.source_url == document["pages"]["rate_table"]["url"] and c.source_detail for c in record.components)

    @pytest.mark.parametrize(("key", "old", "new", "count"), [
        ("rate_table", "$0.000 $0.000 $0.000", "$0.500 $0.500 $0.500", 0),
        ("rate_table", "as of April 1, 2025", "as of April 1, 2027", 0),
        ("rate_table", "RATE TABLE OCTOBER 2026", "RATE TABLE NOVEMBER 2026", 0),
        ("rate_table", "Total Variable ($/GJ) $26.55", "Total Variable ($/GJ) $27.55", 0),
        ("rate_table", "(>15 - 415 GJs/month)", "(>20 - 415 GJs/month)", 0),
        ("rate_table", "Rate Rider A: 5%", "Rate Rider A: five percent", 0),
        ("residential", "Variable Charge per GJ $12.349", "Variable Charge per GJ $12.000", 1),
        ("residential", "as of October 1, 2026", "as of September 1, 2026", 1),
        ("business", "Commodity Charge per GJ $8.10", "Commodity Charge per GJ $8.20", 1),
        ("business", "General Service: Any Customer", "General Service: Some Customers", 1),
    ])
    def test_required_source_failure_is_not_hidden(self, document, key, old, new, count):
        assert old in document["pages"][key]["text"]
        document["pages"][key]["text"] = document["pages"][key]["text"].replace(old, new, 1)
        assert len(self.parse(document)) == count


class TestHeritageGasRC3Live:
    @pytest.fixture
    def document(self):
        return _gas_fixture("heritage_gas")

    @staticmethod
    def parse(document, key=None, old=None, new=None, tariff_url="default"):
        from datetime import date
        from scrapers.utilities.heritage_gas import HeritageGasScraper

        pages = {k: v["text"] for k, v in document["pages"].items()}
        pages["tariff"] = document["rc3_pages"]["tariff"]["text"]
        if key:
            assert old in pages[key], old
            pages[key] = pages[key].replace(old, new)
        url = document["rc3_pages"]["tariff"]["url"] if tariff_url == "default" else tariff_url
        records = HeritageGasScraper().parse_pages(
            pages, date(2026, 10, 5), table_url=document["pages"]["rate_table"]["url"], tariff_url=url)
        return {record.tariff_code: record for record in records}

    def test_rc3_values_and_units(self, document):
        records = self.parse(document)
        assert set(records) == {"Residential", "GS", "RC3"}
        rc3 = records["RC3"]
        assert rc3.customer_class == "commercial" and rc3.usage_min == 50000 and rc3.usage_unit == "GJ/year"
        assert "greater than 50,000 GJ per year" in rc3.eligibility
        values = {(c.component_type, c.component_name): (c.charge_value, c.charge_unit) for c in rc3.components}
        assert values[("fixed", "Fixed Monthly Customer Charge")] == (1995.54, "$/month")
        assert values[("delivery", "Base Energy Charge")] == (0.167, "$/GJ")
        assert values[("demand", "Demand Charge")] == (30.85, "$/GJ of Billing Demand/month")
        assert values[("transmission", "Transportation Cost Recovery Rate")] == (0.71, "$/GJ")
        assert values[("commodity", "Gas Cost Recovery Rate")] == (8.10, "$/GJ")
        assert values[("rider", "RDA Recovery Rate")] == (1.0, "$/GJ")
        assert values[("carbon", "Federal Carbon Tax")] == (0.0, "$/GJ")
        assert [c.charge_value for c in rc3.components if c.charge_unit == "%"] == [5.0, 0.6]
        demand = next(c for c in rc3.components if c.component_type == "demand")
        assert "225 GJ per month" in demand.notes and "Contract Demand" in demand.notes
        assert demand.source_url == document["rc3_pages"]["tariff"]["url"]
        carbon = next(c for c in rc3.components if c.component_type == "carbon")
        assert carbon.effective_date == "2025-04-01"

    def test_absent_tariff_keeps_existing_behaviour(self, document):
        from datetime import date
        from scrapers.utilities.heritage_gas import HeritageGasScraper

        pages = {k: v["text"] for k, v in document["pages"].items()}
        records = HeritageGasScraper().parse_pages(pages, date(2026, 10, 5), table_url="https://example.test/t.pdf")
        assert {r.tariff_code for r in records} == {"Residential", "GS"}

    @pytest.mark.parametrize(("key", "old", "new"), [
        ("tariff", "Demand Charge * $ 30.850 per GJ of Billing Demand per month",
         "Demand Charge * $ 30.850 per kW of Billing Demand per month"),
        ("tariff", "Demand Charge * $ 30.850", "Demand Charge * $ 31.850"),
        ("tariff", "1. 225 GJ per month", "1. 250 GJ per month"),
        ("tariff", "Effective for consumption on and after January 1, 2024", "Effective for consumption on and after January 1, 2027"),
        ("rate_table", "RC3 Demand Charge $30.85", "RC3 Demand Charge $29.85"),
        ("rate_table", "GS Tiers: $0.167", "GS Tiers: $0.170"),
        ("business", "greater than 50,000 GJ per year", "greater than 75,000 GJ per year"),
    ])
    def test_rc3_fails_closed_independently(self, document, key, old, new):
        records = self.parse(document, key, old, new)
        assert set(records) == {"Residential", "GS"}

    def test_missing_tariff_url_rejects_only_rc3(self, document):
        assert set(self.parse(document, tariff_url=None)) == {"Residential", "GS"}

    def test_rc3_price_follows_source(self, document):
        from datetime import date
        from scrapers.utilities.heritage_gas import HeritageGasScraper

        rc3 = self.parse(document, "rate_table", "$1,995.54", "$2,000.00")
        assert "RC3" not in rc3  # tariff still says 1995.54, so the mismatch is rejected
        both = self.parse(document, "tariff", "$ 1995.54 per month", "$ 2000.00 per month")
        assert "RC3" not in both
        text = document["rc3_pages"]["tariff"]["text"]
        pages = {k: v["text"] for k, v in document["pages"].items()}
        pages["rate_table"] = pages["rate_table"].replace("$1,995.54", "$2,000.00").replace("$30.85", "$31.50")
        pages["tariff"] = text.replace("1995.54", "2000.00").replace("30.850", "31.500")
        records = {r.tariff_code: r for r in HeritageGasScraper().parse_pages(
            pages, date(2026, 10, 5), table_url="https://example.test/t.pdf", tariff_url="https://example.test/tariff.pdf")}
        values = {c.component_type: c.charge_value for c in records["RC3"].components if c.component_type in ("fixed", "demand")}
        assert values == {"fixed": 2000.0, "demand": 31.5}


class TestEnergirLive:
    @pytest.fixture
    def document(self):
        return _gas_fixture("energir")

    @staticmethod
    def parse(document, today=None):
        from datetime import date
        from scrapers.utilities.energir import EnergirScraper

        return {record.tariff_name: record for record in EnergirScraper().parse_pages(
            {"pricing": document["pricing"]["text"], "tariff": " ".join(page["text"] for page in document["tariff_pages"])},
            today or date(2026, 10, 5), tariff_url=document["tariff_url"])}

    def test_rate_d1_bands_and_components(self, document):
        records = self.parse(document)
        assert set(records) == {"Residential — Rate D1", "Business — Rate D1", "Commercial — Rate D3", "Commercial — Rate D4"}
        record = records["Residential — Rate D1"]
        assert record.effective_date == "2026-10-01" and record.rate_structure == "tiered"
        basic = [(c.charge_value, c.tier_threshold) for c in record.components if c.component_type == "fixed"]
        assert basic[0] == (0.62525, 10950.0) and basic[-1] == (6.89394, None) and len(basic) == 7
        blocks = [(c.charge_value, c.tier_threshold) for c in record.components if c.component_type == "delivery"]
        assert blocks[0] == (0.31299, 30.0) and blocks[-1] == (0.04038, None) and len(blocks) == 9
        by_name = {c.component_name: c for c in record.components}
        assert by_name["Natural Gas Supply"].charge_value == 0.15535
        assert by_name["Cap-and-Trade Emission Allowances (CTEAS)"].charge_value == 0.08727
        assert by_name["Load Balancing"].sub_component == "conditional"
        assert all(c.charge_unit == "$/m³" for c in record.components if c.component_type != "fixed")
        assert all(c.source_url == document["tariff_url"] and c.source_detail for c in record.components)
        assert [c.charge_value for c in records["Business — Rate D1"].components] == [c.charge_value for c in record.components]

    @pytest.mark.parametrize(("old", "new", "surviving"), [
        ("15.535¢/m³", "15.535$/m³", set()),
        ("is 8.727¢/m³", "is 8.727", set()),
        ("from 30 to 100 21.376", "from 40 to 100 21.376", {"D3", "D4"}),
        ("from 10,950 to 36,500 127.397", "from 10,950 to 36,500", {"D3", "D4"}),
        ("¢/Metering device/Day", "$/Metering device/Month", {"D3", "D4"}),
        ("as of October 1, 2026 is 2.165", "as of September 1, 2026 is 2.165", set()),
        ("Rate D1 applies by default", "Rate D3 applies by default", {"D3", "D4"}),
    ])
    def test_required_source_failure_is_not_hidden(self, document, old, new, surviving):
        changed = 0
        for page in document["tariff_pages"]:
            if old in page["text"] or old in " ".join(page["text"].split()):
                page["text"] = " ".join(page["text"].split()).replace(old, new, 1)
                changed += 1
        assert changed == 1
        assert {r.tariff_code for r in self.parse(document).values()} == surviving

    def test_edition_must_be_current_and_linked(self, document):
        from datetime import date

        assert self.parse(document, date(2026, 9, 30)) == {}
        document["pricing"]["text"] = document["pricing"]["text"].replace(
            "Conditions of Service and Tariff effective as of October 1, 2026", "Conditions of Service and Tariff", 1)
        assert self.parse(document) == {}

    def test_price_follows_source(self, document):
        for page in document["tariff_pages"]:
            page["text"] = page["text"].replace("31.299", "32.000")
        record = self.parse(document)["Residential — Rate D1"]
        assert next(c for c in record.components if c.component_type == "delivery").charge_value == 0.32


class TestEnergirD3D4Live:
    @pytest.fixture
    def document(self):
        return _gas_fixture("energir")

    @staticmethod
    def parse(document, today=None):
        from datetime import date
        from scrapers.utilities.energir import EnergirScraper

        return {record.tariff_name: record for record in EnergirScraper().parse_pages(
            {"pricing": document["pricing"]["text"], "tariff": " ".join(page["text"] for page in document["tariff_pages"])},
            today or date(2026, 10, 5), tariff_url=document["tariff_url"])}

    @staticmethod
    def mutate(document, old, new):
        from scrapers.utilities.energir import EnergirScraper

        changed = 0
        for page in document["tariff_pages"]:
            text = EnergirScraper._norm(page["text"])
            if old in text:
                page["text"] = text.replace(old, new, 1)
                changed += 1
        assert changed == 1, old

    def test_d3_d4_prices_units_and_eligibility(self, document):
        records = self.parse(document)
        assert set(records) == {"Residential — Rate D1", "Business — Rate D1", "Commercial — Rate D3", "Commercial — Rate D4"}
        for code in ("D3", "D4"):
            record = records[f"Commercial — Rate {code}"]
            assert record.tariff_code == code and record.customer_class == "commercial"
            assert record.effective_date == "2026-10-01" and record.rate_structure == "demand"
            assert all(c.effective_date == "2026-10-01" and c.source_url == document["tariff_url"]
                       and "article" in c.source_detail for c in record.components)
            mdo = [c for c in record.components if c.component_type == "demand"]
            assert [(c.charge_value, c.tier_threshold) for c in mdo] == [
                (0.11565, 333.0), (0.09317, 1000.0), (0.06356, 3000.0), (0.0527, 10000.0), (0.03863, 30000.0),
                (0.0302, 100000.0), (0.02156, 300000.0), (0.01741, 1000000.0), (0.01185, None)]
            assert {c.charge_unit for c in mdo} == {"$/m³/day"}
            by_name = {c.component_name: c for c in record.components}
            energy = by_name["Volume Withdrawn up to Subscribed Volume"]
            assert (energy.charge_value, energy.charge_unit) == (0.0035, "$/m³")
            excess = [c for c in record.components if c.component_name.startswith("Withdrawal Above Subscribed Volume")]
            assert [c.charge_value for c in excess] == [0.18476, 0.13996, 0.10362, 0.07283, 0.05869, 0.04872, 0.04038]
            assert all(c.sub_component == "conditional" for c in excess)
            assert by_name["Natural Gas Supply"].charge_value == 0.15535
            assert by_name["Cap-and-Trade Emission Allowances (CTEAS)"].charge_value == 0.08727
            assert by_name["Load Balancing — Average Price"].sub_component == "conditional"
        d3 = {c.component_name: c for c in records["Commercial — Rate D3"].components}
        d4 = {c.component_name: c for c in records["Commercial — Rate D4"].components}
        assert d3["Load Balancing — Average Price"].charge_value == 0.01237
        assert d4["Load Balancing — Average Price"].charge_value == 0.0123
        assert records["Commercial — Rate D3"].usage_min == 75000 and records["Commercial — Rate D3"].usage_unit == "m³/year"
        assert "333 m³/day" in records["Commercial — Rate D3"].eligibility and "60%" in records["Commercial — Rate D3"].eligibility
        assert "10,000 m³/day" in records["Commercial — Rate D4"].eligibility
        assert records["Commercial — Rate D4"].usage_min is None

    @pytest.mark.parametrize(("old", "new", "missing"), [
        ("Distribution Service D3 For all withdrawals", "Distribution Service D3 For some withdrawals", {"D3"}),
        ("Distribution Service D4 For all withdrawals", "Distribution Service D4 For some withdrawals", {"D4"}),
        ("D4 1.230", "D4 n/a", {"D4"}),
        ("D3 1.237", "D3 n/a", {"D3"}),
        ("Subscribed Volume Price m³/Day ¢/m³/Day first 333", "Subscribed Volume Price m³/Day ¢/GJ/Day first 333", {"D3", "D4"}),
        ("from 333 to 1,000 9.317", "from 400 to 1,000 9.317", {"D3", "D4"}),
        ("the unit price is 0.350¢/m³", "the unit price is 0.350$/m³", {"D3", "D4"}),
        ("15.535¢/m³", "15.535$/m³", {"D1", "D3", "D4"}),
        ("¢/Metering device/Day", "$/Metering device/Month", {"D1"}),
    ])
    def test_rates_fail_independently(self, document, old, new, missing):
        self.mutate(document, old, new)
        codes = {record.tariff_code for record in self.parse(document).values()}
        assert codes == {"D1", "D3", "D4"} - missing

    def test_edition_failure_rejects_everything(self, document):
        from datetime import date

        assert self.parse(document, date(2026, 9, 30)) == {}

    def test_price_follows_source(self, document):
        self.mutate(document, "from 333 to 1,000 9.317", "from 333 to 1,000 9.500")
        self.mutate(document, "D4 1.230", "D4 1.500")
        records = self.parse(document)
        assert [c.charge_value for c in records["Commercial — Rate D3"].components if c.component_type == "demand"][1] == 0.095
        d4 = {c.component_name: c for c in records["Commercial — Rate D4"].components}
        assert d4["Load Balancing — Average Price"].charge_value == 0.015
        assert [c.charge_value for c in records["Residential — Rate D1"].components if c.component_type == "delivery"][0] == 0.31299


class TestLibertyGasNBLive:
    @pytest.fixture
    def document(self):
        return _gas_fixture("liberty_gas_nb")

    @staticmethod
    def parse(document):
        from datetime import date
        from scrapers.utilities.liberty_gas_nb import LibertyGasNBScraper

        return {record.tariff_code: record for record in LibertyGasNBScraper().parse_pages(
            {key: page["text"] for key, page in document["pages"].items()}, date(2026, 10, 5))}

    def test_building_classes_alternatives_and_seasons(self, document):
        records = self.parse(document)
        assert set(records) == {"SGS", "MGS", "LGS"}
        for record in records.values():
            assert record.effective_date == "2026-10-01"
            commodity = next(c for c in record.components if c.component_type == "commodity")
            assert commodity.charge_value == 11.02 and commodity.effective_date == "2026-10-01"
            carbon = next(c for c in record.components if c.component_type == "carbon")
            assert carbon.charge_value == 0 and carbon.effective_date == "2025-04-01"
            assert all(c.effective_date == "2025-01-01" for c in record.components if c.component_type in ("fixed", "delivery"))
            assert all(c.source_url and c.source_detail for c in record.components)
        assert [c.charge_value for c in records["MGS"].components if c.component_type == "fixed"] == [22.5, 52.5]
        assert all(c.sub_component == "conditional" for c in records["LGS"].components if c.component_type == "fixed")
        seasonal = {c.season_months: c.charge_value for c in records["LGS"].components if c.season_months}
        assert seasonal == {"Sep-Apr": 6.565, "May-Aug": 2.4689}
        assert "Minimum annual charge" in records["LGS"].notes

    @pytest.mark.parametrize(("key", "old", "new", "count"), [
        ("carbon", "New Brunswick from April 1, 2019", "Nova Scotia from April 1, 2019", 0),
        ("classes", "effective as of January 1, 2025.", "effective as of January 1, 2027.", 0),
        ("home_supply", "October 11.02 9.91", "October 9.91", 2),
        ("business_supply", "October 11.02 9.91", "October 9.91", 1),
        ("classes", "For all volumes delivered 11.2378", "For all volumes delivered 11.3000", 2),
        ("classes", "between May 1 and Aug 31: 2.4689", "between May 1 and Aug 31: -2.4689", 2),
        ("classes", "Service is limited to customers with a consumption less than 250 GJs per month.", "", 2),
    ])
    def test_required_source_failure_is_not_hidden(self, document, key, old, new, count):
        assert old in document["pages"][key]["text"]
        document["pages"][key]["text"] = document["pages"][key]["text"].replace(old, new, 1)
        assert len(self.parse(document)) == count


class TestLibertyOffPeakLive:
    @pytest.fixture
    def document(self):
        return _gas_fixture("liberty_gas_nb")

    @staticmethod
    def parse(document, with_ops=True):
        from datetime import date
        from scrapers.utilities.liberty_gas_nb import LibertyGasNBScraper

        pages = {key: page["text"] for key, page in document["pages"].items()}
        if with_ops:
            pages["ops"] = document["ops_page"]["text"]
        return {record.tariff_code: record for record in LibertyGasNBScraper().parse_pages(pages, date(2026, 10, 5))}

    def test_ops_values_units_and_eligibility(self, document):
        records = self.parse(document)
        assert set(records) == {"SGS", "MGS", "LGS", "OPS"}
        ops = records["OPS"]
        assert ops.tariff_name == "Commercial — Off-Peak Service" and ops.customer_class == "commercial"
        assert ops.effective_date == "2026-10-01" and ops.rate_structure == "flat"
        assert ops.eligibility == (
            "The Off-Peak Service (OPS) Rates are applied to any customer requiring the use of Liberty's "
            "Distribution System to have a supply of natural gas delivered to a single location served through "
            "one meter for the months of April through November.")
        by_type = {c.component_type: c for c in ops.components}
        assert (by_type["fixed"].charge_value, by_type["fixed"].charge_unit) == (50.0, "$/month")
        assert (by_type["delivery"].charge_value, by_type["delivery"].charge_unit) == (5.6244, "$/GJ")
        assert by_type["fixed"].effective_date == by_type["delivery"].effective_date == "2025-01-01"
        assert (by_type["commodity"].charge_value, by_type["commodity"].effective_date) == (11.02, "2026-10-01")
        assert (by_type["carbon"].charge_value, by_type["carbon"].effective_date) == (0.0, "2025-04-01")
        assert len(ops.components) == 4
        assert "$10 per GJ" in ops.notes and "No minimum annual charge" in ops.notes
        assert all(c.source_url and c.source_detail for c in ops.components)

    def test_ops_absent_without_detail_section(self, document):
        assert set(self.parse(document, with_ops=False)) == {"SGS", "MGS", "LGS"}

    @pytest.mark.parametrize(("page", "old", "new"), [
        ("ops", "Delivery Charge ($ per GJ): For all volumes delivered per month: 5.6244",
         "Delivery Charge ($ per GJ): For all volumes delivered per month: 5.7000"),
        ("ops", "for the months of April through November.", "for the months of April through October."),
        ("ops", "subject to a Seasonal Overrun Charge of $10 per GJ", "subject to a Seasonal Overrun Charge of $12 per GJ"),
        ("ops", "on and after January 1, 2025.", "on and after January 1, 2026."),
        ("classes", "Off-Peak N/A N/A 50.00 N/A 5.6244", "Off-Peak N/A N/A 50.00 N/A 0.0000"),
    ])
    def test_ops_rejected_independently(self, document, page, old, new):
        if page == "ops":
            assert old in document["ops_page"]["text"]
            document["ops_page"]["text"] = document["ops_page"]["text"].replace(old, new, 1)
        else:
            assert old in document["pages"][page]["text"]
            document["pages"][page]["text"] = document["pages"][page]["text"].replace(old, new, 1)
        assert set(self.parse(document)) == {"SGS", "MGS", "LGS"}

    def test_price_follows_source(self, document):
        document["pages"]["classes"]["text"] = document["pages"]["classes"]["text"].replace(
            "Off-Peak N/A N/A 50.00", "Off-Peak N/A N/A 55.00", 1)
        document["ops_page"]["text"] = document["ops_page"]["text"].replace(
            "Customer Charge ($ per Month): 50.00", "Customer Charge ($ per Month): 55.00", 1)
        ops = self.parse(document)["OPS"]
        assert next(c for c in ops.components if c.component_type == "fixed").charge_value == 55.0


class TestNovaScotiaBuildingOptions:
    @pytest.fixture
    def document(self):
        import json
        from pathlib import Path

        return json.loads((Path(__file__).parent / "fixtures" / "nova_scotia_residential.json").read_text(encoding="utf-8"))

    @staticmethod
    def parse(document):
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper
        from scrapers.utils.parsing import DocumentPage

        pages = {page["page_number"]: page for page in document["pages"]}
        for group in document["building_pages"].values():
            pages.update({page["page_number"]: page for page in group})
        scraper = NovaScotiaPowerScraper()
        with patch.object(scraper, "now_iso", return_value="2026-10-02T00:00:00+00:00"):
            return {record.tariff_code: record for record in scraper._parse_building_option_tariffs(
                [DocumentPage(**page) for page in pages.values()],
                {kind: product["html"] for kind, product in document["products"].items()}, document["source_url"])}

    def test_murb_and_solar_adjustments_preserve_basis(self, document):
        records = self.parse(document)
        assert set(records) == {"89", "Solar Garden Rider", "Community Solar Rider"}
        murb = records["89"]
        assert len(murb.components) == 9 and "minimum of 10 units" in murb.eligibility
        assert all(component.component_type != "fixed" for component in murb.components)
        assert "minimum-bill condition" in murb.notes
        assert sum(component.component_type == "rider" for component in murb.components) == 3
        for code in ("Solar Garden Rider", "Community Solar Rider"):
            assert "otherwise applicable tariff" in records[code].notes
            assert all(component.sub_component == "optional" for component in records[code].components)
            assert all(component.charge_value < 0 for component in records[code].components if component.component_type == "rebate")
            assert records[code].effective_date == max(component.effective_date for component in records[code].components)
        assert all(component.source_url and component.source_detail for record in records.values() for component in record.components)

    def test_solar_capacity_charge_must_be_positive(self, document):
        import re

        changed = 0
        for page in document["building_pages"]["solar_garden"]:
            page["text"], count = re.subn(r"(Monthly Solar Capacity Charge\s+\$)\d+\.\d+", r"\g<1>0.00", page["text"])
            changed += count
        assert changed == 1
        assert set(self.parse(document)) == {"89", "Community Solar Rider"}

    @pytest.mark.parametrize(("number", "rejected"), [
        (35, {"89"}), (36, {"89"}), (37, {"89"}), (67, {"89"}), (76, {"89"}),
        (69, {"Solar Garden Rider"}), (71, {"Solar Garden Rider"}), (73, {"Solar Garden Rider"}),
        (80, {"Community Solar Rider"}), (83, {"Community Solar Rider"}),
    ])
    def test_building_option_missing_pages_are_independent(self, document, number, rejected):
        document["pages"] = [page for page in document["pages"] if page["page_number"] != number]
        for key in document["building_pages"]:
            document["building_pages"][key] = [page for page in document["building_pages"][key] if page["page_number"] != number]
        assert set(self.parse(document)) == {"89", "Solar Garden Rider", "Community Solar Rider"} - rejected


# ─── Nova Scotia Power business ───

import json
from pathlib import Path

NSP_FIXTURE = Path(__file__).parent / "fixtures" / "nova_scotia_residential.json"
NSP_ALL_CODES = {"10", "11", "12"}


class TestNovaScotiaBusinessLive:
    @pytest.fixture
    def document(self):
        return json.loads(NSP_FIXTURE.read_text(encoding="utf-8"))

    @staticmethod
    def pages(document):
        from scrapers.utils.parsing import DocumentPage

        merged = {page["page_number"]: page for page in document["pages"]}
        for group in document["building_pages"].values():
            merged.update({page["page_number"]: page for page in group})
        merged.update({page["page_number"]: page for page in document["business_pages"]["rates"]})
        return [DocumentPage(**page) for page in merged.values()]

    @classmethod
    def parse(cls, document, today="2026-10-02"):
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper

        scraper = NovaScotiaPowerScraper()
        products = {kind: product["html"] for kind, product in document["products"].items()}
        with patch.object(scraper, "now_iso", return_value=today + "T00:00:00+00:00"):
            records = scraper._parse_business_tariffs(cls.pages(document), products, document["source_url"])
        return {record.tariff_code: record for record in records}

    @staticmethod
    def edit(document, page_number, old, new, group=None):
        pages = document["business_pages"]["rates"] if group is None else document["building_pages"][group]
        page = next(page for page in pages if page["page_number"] == page_number)
        assert old in page["text"]
        page["text"] = page["text"].replace(old, new)

    @staticmethod
    def values(record, ctype):
        return [(c.component_name, c.charge_value, c.charge_unit) for c in record.components if c.component_type == ctype]

    @staticmethod
    def riders(record):
        return {c.component_name: c for c in record.components if c.component_type == "rider"}

    def test_small_general_values_units_and_riders(self, document):
        record = self.parse(document)["10"]
        assert record.tariff_name == "Small Commercial" and record.rate_structure == "tiered"
        assert record.effective_date == "2026-05-01" and record.end_date == "2026-12-31"
        assert self.values(record, "fixed") == [("Customer Charge", 22.0, "$/month")]
        energy = [c for c in record.components if c.component_type == "energy"]
        assert [(c.charge_value, c.tier_number, c.tier_threshold, c.tier_unit) for c in energy] == [
            (0.18919, 1, 200.0, "kWh/month"), (0.17112, 2, None, None)]
        riders = self.riders(record)
        assert riders["FAM Actual/Balance Adjustment (Combined)"].charge_value == 0.00156
        assert riders["DSM Cost Recovery Rider"].charge_value == 0.00729
        assert riders["Storm Cost Recovery Rider"].charge_value == 0
        assert all(r.charge_unit == "$/kWh" for r in riders.values())
        assert "minimum-bill condition" in record.notes and "$22.00" in record.notes
        assert "less than 32,000 kWh per year" in record.eligibility

    def test_general_demand_values_units_and_riders(self, document):
        record = self.parse(document)["11"]
        assert record.tariff_name == "Commercial General Demand" and record.rate_structure == "demand"
        assert self.values(record, "demand") == [("Demand Charge", 9.809, "$/kW/month")]
        credit = next(c for c in record.components if c.component_type == "rebate")
        assert credit.charge_value == -0.32 and credit.charge_unit == "$/kW/month" and credit.sub_component == "conditional"
        energy = [c for c in record.components if c.component_type == "energy"]
        assert [(c.charge_value, c.tier_threshold, c.tier_unit) for c in energy] == [
            (0.14782, 200.0, "kWh/kW of maximum demand/month"), (0.11718, None, None)]
        riders = self.riders(record)
        assert [riders[n].charge_value for n in ("FAM Actual/Balance Adjustment (Combined)", "DSM Cost Recovery Rider", "Storm Cost Recovery Rider")] == [0.00207, 0.00749, 0]
        assert not [c for c in record.components if c.component_type == "fixed"]
        assert "minimum monthly bill" in record.notes and "$22.00" in record.notes

    def test_large_general_values_units_and_riders(self, document):
        record = self.parse(document)["12"]
        assert record.tariff_name == "Large Commercial"
        assert self.values(record, "demand") == [("Demand Charge", 11.174, "$/kVA/month")]
        assert next(c for c in record.components if c.component_type == "demand").demand_unit == "kVA"
        credit = next(c for c in record.components if c.component_type == "rebate")
        assert credit.charge_value == -0.32 and credit.charge_unit == "$/kVA/month"
        assert self.values(record, "energy") == [("Energy Charge", 0.11164, "$/kWh")]
        riders = self.riders(record)
        assert [riders[n].charge_value for n in ("FAM Actual/Balance Adjustment (Combined)", "DSM Cost Recovery Rider", "Storm Cost Recovery Rider")] == [0.00158, 0.00458, 0]
        assert "any use except industrial" in record.eligibility
        assert "not an additional fixed charge" in record.notes

    def test_every_component_has_dates_and_sources(self, document):
        for record in self.parse(document).values():
            for component in record.components:
                assert component.effective_date and component.source_url == document["source_url"] and component.source_detail
            detail = {c.component_name: c.source_detail for c in record.components if c.component_type == "rider"}
            assert "FUEL ADJUSTMENT" in detail["FAM Actual/Balance Adjustment (Combined)"]
            assert "DEMAND SIDE MANAGEMENT" in detail["DSM Cost Recovery Rider"]
            assert detail["Storm Cost Recovery Rider"].startswith("STORM COST RECOVERY RIDER")

    @pytest.mark.parametrize(("mutate", "rejected"), [
        (lambda t, d: t.edit(d, 25, "Rate Code 11", "Rate Code 99"), "11"),
        (lambda t, d: t.edit(d, 16, "cents per kilowatt-hour", "dollars per kilowatt-hour"), "10"),
        (lambda t, d: t.edit(d, 39, "any use except industrial", "any use"), "12"),
        (lambda t, d: t.edit(d, 17, "Effective January 1, 2027 $22.73", "Effective January 1, 2027"), "10"),
        (lambda t, d: t.edit(d, 76, "0.428 0.029 0.458", "0.428 0.029 0.999", "building_riders"), "12"),
        (lambda t, d: t.edit(d, 75, "Small 0.809 (0.080) 0.729", "Small", "building_riders"), "10"),
        (lambda t, d: t.edit(d, 26, "$22.00", "-$22.00"), "11"),
    ])
    def test_one_class_fails_independently(self, document, mutate, rejected):
        mutate(self, document)
        assert set(self.parse(document)) == NSP_ALL_CODES - {rejected}

    def test_missing_continuation_page_rejects_only_that_class(self, document):
        document["business_pages"]["rates"] = [p for p in document["business_pages"]["rates"] if p["page_number"] != 39]
        assert set(self.parse(document)) == {"10", "11"}

    def test_prices_follow_source(self, document):
        self.edit(document, 16, "18.919", "20.000")
        self.edit(document, 25, "$9.809", "$10.100")
        self.edit(document, 38, "11.164", "11.264")
        self.edit(document, 38, "$11.174", "$11.500")
        records = self.parse(document)
        assert records["10"].components[1].charge_value == 0.2
        assert self.values(records["11"], "demand")[0][1] == 10.1
        assert self.values(records["12"], "energy")[0][1] == 0.11264
        assert self.values(records["12"], "demand")[0][1] == 11.5

    def test_rider_values_follow_source_per_class(self, document):
        self.edit(document, 66, "Small General Critical Peak 0.156 0.156", "Small General Critical Peak 0.200 0.200", "building_riders")
        self.edit(document, 67, "Large General 0.158 0.158", "Large General 0.300 0.300", "building_riders")
        records = self.parse(document)
        assert self.riders(records["10"])["FAM Actual/Balance Adjustment (Combined)"].charge_value == 0.002
        assert self.riders(records["12"])["FAM Actual/Balance Adjustment (Combined)"].charge_value == 0.003
        assert self.riders(records["11"])["FAM Actual/Balance Adjustment (Combined)"].charge_value == 0.00207

    def test_unsupported_year_or_missing_book_date_fails_closed(self, document):
        assert self.parse(document, today="2027-01-01") == {}
        for product in document["products"].values():
            product["html"] = product["html"].replace("Rates updated as of May 1, 2026.", "")
        assert self.parse(document) == {}

    def test_scraper_uses_cached_book_and_fails_closed_without_it(self, document):
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper

        scraper = NovaScotiaPowerScraper()
        assert scraper._try_live_commercial() is None
        scraper._book = (self.pages(document), {k: p["html"] for k, p in document["products"].items()}, document["source_url"])
        with patch.object(scraper, "now_iso", return_value="2026-10-02T00:00:00+00:00"):
            records = scraper._try_live_commercial()
        assert {record.tariff_code for record in records} == NSP_ALL_CODES

    def test_failed_business_class_keeps_seed_fallback_for_that_class_only(self, document):
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper

        self.edit(document, 25, "Rate Code 11", "Rate Code 99")
        scraper = NovaScotiaPowerScraper()
        scraper._book = (self.pages(document), {k: p["html"] for k, p in document["products"].items()}, document["source_url"])
        with patch.object(scraper, "now_iso", return_value="2026-10-02T00:00:00+00:00"), \
             patch.object(scraper, "_try_live_residential", return_value=[]):
            records = scraper._try_live_scrape()
        by_code = {record.tariff_code: record for record in records}
        assert "live_parsed" in by_code["10"].notes and "live_parsed" in by_code["12"].notes
        assert "seed_fallback" in by_code["11"].notes and by_code["11"].confidence == "unverified"


# ─── Maritime Electric building classes ───

NSPP_FIXTURE = Path(__file__).parent / "fixtures" / "nova_scotia_residential.json"
NSPP_CODES = {"72", "73", "82", "83"}
NSPP_INTERIM = "2026-10-05"
NSPP_NOVEMBER = "2026-11-02"


class TestNovaScotiaBusinessPilotsLive:
    @pytest.fixture
    def document(self):
        return json.loads(NSPP_FIXTURE.read_text(encoding="utf-8"))

    @staticmethod
    def pages(document):
        from scrapers.utils.parsing import DocumentPage

        cover = DocumentPage(**document["pages"][0])
        riders = document["building_pages"]["building_riders"]
        return [cover] + [DocumentPage(**p) for p in document["business_pilot"]["pages"] + riders]

    @classmethod
    def parse(cls, document, today=NSPP_INTERIM, business_html=None):
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper

        scraper = NovaScotiaPowerScraper()
        products = {kind: product["html"] for kind, product in document["products"].items()}
        html = business_html if business_html is not None else document["business_pilot"]["business_html"]
        with patch.object(scraper, "now_iso", return_value=today + "T00:00:00+00:00"):
            records = scraper._parse_business_pilot_tariffs(cls.pages(document), products, document["source_url"], html)
        return {record.tariff_code: record for record in records}

    @staticmethod
    def edit(document, page_number, old, new):
        page = next(p for p in document["business_pilot"]["pages"] if p["page_number"] == page_number)
        assert old in page["text"]
        page["text"] = page["text"].replace(old, new)

    @staticmethod
    def drop(document, page_number):
        document["business_pilot"]["pages"] = [p for p in document["business_pilot"]["pages"] if p["page_number"] != page_number]

    @staticmethod
    def values(record, kind):
        return {c.component_name: c.charge_value for c in record.components if c.component_type == kind}

    def test_interim_phase_records_and_values(self, document):
        records = self.parse(document)
        assert set(records) == NSPP_CODES
        small, general = records["72"], records["73"]
        assert small.effective_date == "2026-05-01" and small.end_date == "2026-10-31"
        assert "Conditional Pilot" in small.tariff_name and small.customer_class == "commercial"
        assert "interim" in small.sub_class and "restoration" in small.notes
        assert self.values(small, "fixed") == {"Customer Charge": 22.0}
        assert self.values(small, "energy") == {
            "Interim Energy Charge - First 200 kWh": 0.18919, "Interim Energy Charge - Balance": 0.17112}
        assert self.values(general, "demand") == {"Demand Charge": 9.809}
        assert self.values(general, "rebate") == {"Customer-Owned Transformer Demand Reduction": -0.32}
        assert self.values(records["83"], "energy") == {
            "Interim Energy Charge - First 200 kWh": 0.14782, "Interim Energy Charge - Balance": 0.11718}
        tier = next(c for c in general.components if c.tier_number == 1)
        assert tier.tier_unit == "kWh/kW of maximum demand/month" and tier.tier_threshold == 200.0
        assert "No Critical Peak Events" in small.notes
        assert "Rate Code 10" in records["82"].notes and "Rate Code 11" in records["83"].notes

    def test_components_have_provenance_and_riders_separate(self, document):
        for record in self.parse(document).values():
            assert len(self.values(record, "rider")) == 3
            for component in record.components:
                assert component.effective_date and component.source_url and component.source_detail
            assert not any("Interim" in c.component_name for c in record.components if c.component_type == "rider")
        assert self.values(self.parse(document)["72"], "rider") == {
            "FAM Actual/Balance Adjustment (Combined)": 0.00156,
            "DSM Cost Recovery Rider": 0.00729,
            "Storm Cost Recovery Rider": 0.0,
        }
        assert self.values(self.parse(document)["83"], "rider")["FAM Actual/Balance Adjustment (Combined)"] == 0.00207

    def test_november_phase_is_date_gated(self, document):
        records = self.parse(document, today=NSPP_NOVEMBER)
        assert set(records) == NSPP_CODES
        cpp = records["72"]
        assert cpp.effective_date == "2026-11-01" and cpp.rate_structure == "tou"
        assert self.values(cpp, "energy") == {
            "Critical Peak Event Energy": 1.51941, "Non-Critical Energy - First 200 kWh": 0.16739,
            "Non-Critical Energy - Balance": 0.15331}
        assert "18" in cpp.notes and "holidays" in cpp.notes
        assert self.values(records["73"], "energy")["Critical Peak Event Energy"] == 1.42972
        tou = records["82"]
        assert self.values(tou, "energy") == {"Winter On-Peak Energy": 0.37674, "Winter Off-Peak Energy": 0.18902}
        on_peak = next(c for c in tou.components if c.tou_period == "on-peak")
        assert "7:00 AM to 11:00 AM" in on_peak.tou_hours and "5:00 PM to 9:00 PM" in on_peak.tou_hours
        off_peak = next(c for c in records["83"].components if c.tou_period == "off-peak")
        assert "weekends" in off_peak.tou_hours and off_peak.charge_value == 0.14348
        assert "interim" not in tou.sub_class
        # Next-year columns are never used.
        for record in records.values():
            assert all(c.charge_value not in (0.39698, 0.19777, 0.12723, 0.28938, 0.167157, 0.17381) for c in record.components)

    def test_dates_beyond_book_year_fail_closed(self, document):
        assert self.parse(document, today="2027-01-02") == {}

    def test_price_follows_source(self, document):
        self.edit(document, 23, "18.919 17.112", "19.001 17.222")
        records = self.parse(document)
        assert self.values(records["82"], "energy")["Interim Energy Charge - First 200 kWh"] == 0.19001
        assert self.values(records["72"], "energy")["Interim Energy Charge - First 200 kWh"] == 0.18919

    def test_closure_notice_required_for_all(self, document):
        assert self.parse(document, business_html="<p>Apply now for the pilot.</p>") == {}

    def test_missing_continuation_rejects_only_that_pilot(self, document):
        self.drop(document, 21)
        records = self.parse(document)
        assert set(records) == NSPP_CODES - {"72"}

    def test_changed_demand_credit_rejects_only_rate_83(self, document):
        self.edit(document, 31, "32 cents per kilowatt reduction", "40 cents per kilowatt reduction")
        assert set(self.parse(document)) == NSPP_CODES - {"83"}

    def test_missing_interim_condition_rejects_only_rate_72(self, document):
        self.edit(document, 18, "If system functionality is restored after March 1, 2026", "If system is restored")
        assert set(self.parse(document)) == NSPP_CODES - {"72"}

    def test_november_incomplete_tou_row_rejects_only_rate_82(self, document):
        self.edit(document, 23, "Effective November 1, 2026 37.674 18.902 37.674 18.902", "Effective November 1, 2026 37.674 18.902")
        records = self.parse(document, today=NSPP_NOVEMBER)
        assert set(records) == NSPP_CODES - {"82"}

    def test_november_missing_event_limits_rejects_only_rate_73(self, document):
        self.edit(document, 29, "No more than 18 Critical Peak Events", "Some Critical Peak Events")
        assert set(self.parse(document, today=NSPP_NOVEMBER)) == NSPP_CODES - {"73"}

    def test_missing_rider_row_rejects_pilots_but_not_others_when_class_differs(self, document):
        for page in document["building_pages"]["building_riders"]:
            page["text"] = page["text"].replace("Small General, Small General Time of Use", "Small General, Renamed")
        records = self.parse(document)
        assert set(records) == {"73", "83"}

    def test_live_scrape_includes_pilots_without_changing_other_inputs(self, document):
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper

        scraper = NovaScotiaPowerScraper()
        products = {kind: product["html"] for kind, product in document["products"].items()}
        scraper._book = (self.pages(document), products, document["source_url"])
        html = document["business_pilot"]["business_html"]
        with patch.object(scraper, "now_iso", return_value=NSPP_INTERIM + "T00:00:00+00:00"), \
                patch.object(scraper, "fetch_page", return_value=html):
            records = scraper._try_live_commercial()
        assert {r.tariff_code for r in records} >= NSPP_CODES
        with patch.object(scraper, "now_iso", return_value=NSPP_INTERIM + "T00:00:00+00:00"), \
                patch.object(scraper, "fetch_page", side_effect=RuntimeError("down")):
            records = scraper._try_live_commercial()
        assert not records or not ({r.tariff_code for r in records} & NSPP_CODES)


import json
from pathlib import Path

import scrapers.utilities.maritime_electric as me
from scrapers.utils.parsing import DocumentPage

ME_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "maritime_electric.json").read_text(encoding="utf-8")
)
ME_URL = ME_FIXTURE["url"]
ME_PAGE1 = next(p["text"] for p in ME_FIXTURE["pages"] if p["page_number"] == 1)

ME_BUILDING = {"110", "130", "131", "133", "232", "233"}
ME_INDUSTRIAL = {"320", "310", "340", "330"}


def _ME_parse(text=ME_PAGE1, url=ME_URL):
    scraper = me.MaritimeElectricScraper()
    return {r.tariff_code: r for r in scraper._parse_pages([DocumentPage(1, text)], url)}


def _ME_comp(record, ctype, tier=None):
    return next(c for c in record.components if c.component_type == ctype and c.tier_number == tier)


class TestMaritimeElectricBuildingLive:
    def test_all_classes_parse(self):
        assert set(_ME_parse()) == ME_BUILDING | ME_INDUSTRIAL

    def test_residential_values_and_units(self):
        recs = _ME_parse()
        for code, service in (("110", 24.57), ("130", 26.92), ("131", 26.92), ("133", 37.50)):
            r = recs[code]
            fixed = _ME_comp(r, "fixed")
            assert (fixed.charge_value, fixed.charge_unit) == (service, "$/month")
            t1, t2 = _ME_comp(r, "energy", 1), _ME_comp(r, "energy", 2)
            assert (t1.charge_value, t1.charge_unit, t1.tier_threshold, t1.tier_unit) == (0.1784, "$/kWh", 2000.0, "kWh")
            assert (t2.charge_value, t2.charge_unit, t2.tier_threshold) == (0.1423, "$/kWh", None)
            assert r.customer_class == "residential"

    def test_general_service_values_and_units(self):
        recs = _ME_parse()
        for code in ("232", "233"):
            r = recs[code]
            assert _ME_comp(r, "fixed").charge_value == 24.57
            demand = _ME_comp(r, "demand", 2)
            assert (demand.charge_value, demand.charge_unit, demand.demand_unit) == (13.43, "$/kW", "kW")
            assert _ME_comp(r, "energy", 1).charge_value == 0.2188
            assert _ME_comp(r, "energy", 1).tier_threshold == 5000.0
            assert _ME_comp(r, "energy", 2).charge_value == 0.1438
            # First 20 kW is published as "$ -" and is not emitted as a charge.
            assert len([c for c in r.components if c.component_type == "demand"]) == 1
            assert r.customer_class == "commercial"

    def test_industrial_retained_with_native_threshold_unit(self):
        recs = _ME_parse()
        assert _ME_comp(recs["320"], "energy", 1).tier_unit == "kWh per kW billing demand"
        assert _ME_comp(recs["310"], "demand").charge_value == 14.50
        assert recs["310"].customer_class == "industrial"

    def test_provenance_fields_on_every_component(self):
        for r in _ME_parse().values():
            assert r.effective_date == "2026-08-01"
            assert r.source_page == "PDF page 1"
            for c in r.components:
                assert c.effective_date == "2026-08-01"
                assert c.source_url == ME_URL
                assert c.source_detail.startswith("PDF page 1, Rate " + r.tariff_code)

    def test_names_unchanged(self):
        recs = _ME_parse()
        assert recs["110"].tariff_name == "Residential Urban (Rate 110)"
        assert recs["233"].tariff_name == "General Service - Seasonal Operators Option (Rate 233)"
        assert _ME_comp(recs["110"], "energy", 1).component_name == "Energy Charge per kWh for first 2,000 kWh"

    # Mutation rejections: each class fails alone.
    def test_missing_service_charge_rejects_only_that_class(self):
        recs = _ME_parse(ME_PAGE1.replace("Service Charge $ 26.92\n", "", 1))
        assert "130" not in recs
        assert {"110", "131", "133", "232"} <= set(recs)

    def test_missing_balance_block_rejects_only_that_class(self):
        text = ME_PAGE1.replace("Energy Charge per kWh for balance of kWh $ 0.1423\nService Charge $ 37.50", "Service Charge $ 37.50", 1)
        text = text.replace("133 Residential Seasonal Option\nService Charge $ 37.50\nEnergy Charge per kWh for first 2,000 kWh $ 0.1784\nEnergy Charge per kWh for balance of kWh $ 0.1423\n",
                            "133 Residential Seasonal Option\nService Charge $ 37.50\nEnergy Charge per kWh for first 2,000 kWh $ 0.1784\n")
        recs = _ME_parse(text)
        assert "133" not in recs
        assert {"110", "131", "232"} <= set(recs)

    def test_changed_tier_threshold_rejects_only_that_class(self):
        text = ME_PAGE1.replace("first 5,000 kWh $ 0.2188", "first 6,000 kWh $ 0.2188", 1)
        recs = _ME_parse(text)
        assert "232" not in recs
        assert "233" in recs and "110" in recs

    def test_unparseable_charge_value_rejects_only_that_class(self):
        text = ME_PAGE1.replace("Demand Charge per kW $ 14.50", "Demand Charge per kW $ -", 1)
        recs = _ME_parse(text)
        assert "310" not in recs
        assert "320" in recs and "110" in recs

    def test_missing_zero_first_block_demand_rejects_general_service_only(self):
        text = ME_PAGE1.replace("Demand Charge - per kW for first 20 kW $ -\n", "", 1)
        recs = _ME_parse(text)
        assert "232" not in recs
        assert "233" in recs and "110" in recs

    def test_duplicate_class_header_rejects_that_class(self):
        recs = _ME_parse(ME_PAGE1 + "\n130 Residential Rural\n")
        # Appended after the page marker, so the body is unchanged.
        assert "130" in recs
        dup = ME_PAGE1.replace("131 Residential Seasonal\n", "130 Residential Rural\n", 1)
        assert "130" not in _ME_parse(dup)

    def test_missing_or_mismatched_date_rejects_all(self):
        assert _ME_parse(ME_PAGE1.replace("Code August 1, 2026", "Code")) == {}
        assert _ME_parse(ME_PAGE1.replace("August 1, 2026", "September 1, 2026")) == {}

    def test_missing_rate_page_rejects_all(self):
        assert _ME_parse(ME_PAGE1.replace("110 Residential Urban", "110 Residential")) == {}

    def test_price_follows_source(self):
        text = ME_PAGE1.replace("Service Charge $ 24.57", "Service Charge $ 25.01").replace("$ 0.1784", "$ 0.1900")
        recs = _ME_parse(text)
        assert _ME_comp(recs["110"], "fixed").charge_value == 25.01
        assert _ME_comp(recs["130"], "energy", 1).charge_value == 0.1900
        assert _ME_comp(recs["232"], "fixed").charge_value == 25.01

    def test_scrape_marks_live_and_failure_falls_back(self, monkeypatch):
        scraper = me.MaritimeElectricScraper()
        schedule = "\n".join(ME_FIXTURE["rates_page"]["html_lines"])
        html = f'<html><a href="{ME_URL}">Schedule of Adjusted Rates Section N-28</a>{schedule}</html>'
        monkeypatch.setattr(scraper, "fetch_page", lambda url, **k: html)
        monkeypatch.setattr(scraper, "fetch_bytes", lambda url, **k: b"%PDF")
        monkeypatch.setattr(me, "_extract_pages", lambda b: [DocumentPage(1, ME_PAGE1)])
        live = scraper.scrape()
        assert len(live) == 10
        assert all("Provenance: live_parsed" in r.notes for r in live)

        monkeypatch.setattr(me, "_extract_pages", lambda b: [DocumentPage(1, "garbage")])
        fallback = scraper.scrape()
        assert all("Provenance: seed_fallback" in r.notes for r in fallback)
        assert all(r.confidence == "unverified" for r in fallback)


class TestRegionalBatchStorage:
    @pytest.mark.parametrize("family", ["hydro_quebec", "nl_hydro", "saskenergy", "fortisbc_electric", "nova_scotia_power", "centra_gas",
                                        "fortisbc_energy", "heritage_gas", "energir", "liberty_gas_nb"])
    def test_new_classes_survive_repeat_storage_and_export(self, family, tmp_path, monkeypatch):
        import json
        import sqlite3
        from datetime import date
        from pathlib import Path
        from pipeline import export_json
        from pipeline.run_scrape import store_results
        from tests.test_phase5_hardening import database

        fixture_name = {"hydro_quebec": "hydro_quebec_domestic", "nova_scotia_power": "nova_scotia_residential"}.get(family, family)
        document = json.loads((Path(__file__).parent / "fixtures" / f"{fixture_name}.json").read_text(encoding="utf-8"))
        if family == "hydro_quebec":
            for key in ("dt_pages", "winter_credit_pages", "flex_d_pages"):
                document["pages"].extend(document[key])
            records = list(TestHydroQuebecOptional.options(document).values())
            assert len(records) == 3
        elif family == "nl_hydro":
            records = list(TestNLHydroLive.parse(document).values())
            assert len(records) == 18
        elif family == "fortisbc_electric":
            from scrapers.utilities.fortisbc_electric import FortisBCElectricScraper

            records = FortisBCElectricScraper().mark_live_parsed(list(TestFortisBCElectricLive.parse(document).values()))
            assert len(records) == 6
        elif family == "nova_scotia_power":
            from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper

            records = NovaScotiaPowerScraper().mark_live_parsed(list(TestNovaScotiaBuildingOptions.parse(document).values()))
            assert len(records) == 3
        elif family == "centra_gas":
            from scrapers.utilities.centra_gas import CentraGasScraper

            records = CentraGasScraper().mark_live_parsed(list(TestCentraGasLive.parse(document).values()))
            assert len(records) == 12
        elif family == "fortisbc_energy":
            from scrapers.utilities.fortisbc_energy import FortisBCEnergyScraper

            records = FortisBCEnergyScraper().mark_live_parsed(list(TestFortisBCEnergyLive.parse(document).values()))
            assert len(records) == 6
        elif family == "heritage_gas":
            from scrapers.utilities.heritage_gas import HeritageGasScraper

            records = HeritageGasScraper().mark_live_parsed(list(TestHeritageGasLive.parse(document).values()))
            assert len(records) == 2
        elif family == "energir":
            from scrapers.utilities.energir import EnergirScraper

            records = EnergirScraper().mark_live_parsed(list(TestEnergirLive.parse(document).values()))
            assert len(records) == 4
        elif family == "liberty_gas_nb":
            from scrapers.utilities.liberty_gas_nb import LibertyGasNBScraper

            records = LibertyGasNBScraper().mark_live_parsed(list(TestLibertyGasNBLive.parse(document).values()))
            assert len(records) == 3
        else:
            from scrapers.utilities.saskenergy import SaskEnergyScraper

            scraper = SaskEnergyScraper()
            records = scraper.mark_live_parsed(scraper.parse_pages(
                {key: page["text"] for key, page in document["pages"].items()}, date(2026, 10, 2)))
            assert len(records) == 7
        connection = database()
        for run_id in (1, 2):
            assert store_results(records, run_id, connection) == len(records)
        assert connection.execute("SELECT count(*) FROM tariffs").fetchone()[0] == len(records)
        assert connection.execute("SELECT count(*) FROM historical_snapshots").fetchone()[0] == 2 * len(records)
        path = tmp_path / "rates.db"
        with sqlite3.connect(path) as persisted:
            connection.backup(persisted)
        connection.close()
        monkeypatch.setattr(export_json, "DB_PATH", path)
        monkeypatch.setattr(export_json, "SITE_DATA_DIR", tmp_path / "site")
        export_json.export_all()
        exported = json.loads((tmp_path / "site" / "rates.json").read_text(encoding="utf-8"))
        assert {record["tariff_code"]: len(record["components"]) for record in exported} == {record.tariff_code: len(record.components) for record in records}
        assert all(record["provenance"] == "live" for record in exported)
        assert all(component["source_url"] and component["source_detail"] for record in exported for component in record["components"])


# ─── Newfoundland Power ────────────────────────────────────────

class TestNewfoundlandPowerUpdated:
    @pytest.fixture(autouse=True)
    def setup(self):
        from scrapers.utilities.newfoundland_power import NewfoundlandPowerScraper
        with patch.object(NewfoundlandPowerScraper, "_try_live_scrape", return_value=None):
            self.scraper = NewfoundlandPowerScraper()
            self.records = self.scraper.scrape()

    def test_returns_two_tariffs(self):
        assert len(self.records) == 2

    def test_effective_dates_updated(self):
        for r in self.records:
            assert r.effective_date == "2025-07-01"

    def test_source_urls_updated(self):
        """All URLs should point to the new path, not the old 404 URL."""
        for r in self.records:
            assert "My-Account" in r.source_url

    def test_residential_has_correct_rate(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        energy = [c for c in res.components if c.component_type == "energy"][0]
        assert energy.charge_value == pytest.approx(0.13263)

    def test_general_service_has_demand(self):
        gs = [r for r in self.records if r.customer_class == "commercial"][0]
        demand = [c for c in gs.components if c.component_type == "demand"]
        assert len(demand) == 1

    def test_changed_pdf_rate_is_rejected(self):
        from scrapers.utilities.newfoundland_power import NewfoundlandPowerScraper
        html = '<body><p>Current rates</p><a href="rates.pdf">Schedule of Rates</a></body>'
        scraper = NewfoundlandPowerScraper()
        with patch.object(scraper, "fetch_page", return_value=html), \
             patch.object(scraper, "fetch_bytes", return_value=b"pdf"), \
             patch("scrapers.utilities.newfoundland_power.extract_pdf_text", return_value="changed rates"):
            assert scraper._try_live_scrape() is None


# ─── Cross-utility sanity checks ───────────────────────────────

# ─── Newfoundland Power building classes ───

import json
from pathlib import Path

from scrapers.utilities.newfoundland_power import NewfoundlandPowerScraper
from scrapers.utils.parsing import DocumentPage

NFP_FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "newfoundland_power.json").read_text(encoding="utf-8")
)
NFP_URL = NFP_FIXTURE["source_url"]


def _NFP_pages(mutate=None):
    pages = {p["page_number"]: p["text"] for p in NFP_FIXTURE["pages"]}
    if mutate:
        mutate(pages)
    return [DocumentPage(n, t) for n, t in sorted(pages.items())]


def _NFP_parse(mutate=None):
    scraper = NewfoundlandPowerScraper()
    pages = _NFP_pages(mutate)
    text = "\n".join(p.text for p in pages)
    base = scraper._parse_ratebook(text, NFP_URL)
    scraper._annotate_base(base, pages, NFP_URL)
    extra = scraper._parse_pages(pages, NFP_URL, base)
    return {r.tariff_code: r for r in base + extra}


def _NFP_comp(record, name):
    return next(c for c in record.components if c.component_name == name)


class TestNewfoundlandPowerBuildingLive:
    def test_all_records_present(self):
        assert set(_NFP_parse()) == {"1.1", "2.1", "2.3", "2.4", "1.1S", "PPD", "RULE-9K", "FEES"}

    def test_seasonal_domestic(self):
        r = _NFP_parse()["1.1S"]
        assert r.tariff_name == "Domestic Seasonal - Optional (Rate 1.1S)"
        assert r.effective_date == "2026-07-01"
        win = _NFP_comp(r, "Winter Season Premium Adjustment")
        non = _NFP_comp(r, "Non-Winter Season Credit Adjustment")
        assert (win.charge_value, win.charge_unit, win.season_months) == (0.00953, "$/kWh", "December-April")
        assert (non.charge_value, non.charge_unit, non.season_months) == (-0.01297, "$/kWh", "May-November")
        assert "12-month" in r.notes

    def test_prompt_payment_percent(self):
        c = _NFP_parse()["PPD"].components[0]
        assert (c.charge_value, c.charge_unit) == (-1.5, "%")
        assert "current month's bill" in c.notes

    def test_primary_voltage_discount_kva(self):
        r = _NFP_parse()["RULE-9K"]
        vals = {c.component_name: (c.charge_value, c.charge_unit, c.demand_unit) for c in r.components}
        assert vals == {
            "Primary Voltage Demand Discount (4 kV to 25 kV)": (-0.40, "$/kVA", "kVA"),
            "Primary Voltage Demand Discount (33 kV to 138 kV)": (-0.90, "$/kVA", "kVA"),
        }

    def test_fees(self):
        r = _NFP_parse()["FEES"]
        vals = {c.component_name: (c.charge_value, c.charge_unit) for c in r.components}
        assert vals == {
            "Reconnection Fee (normal office hours)": (20.0, "$/reconnection"),
            "Reconnection Fee (other times)": (40.0, "$/reconnection"),
            "Application Fee (name change / new premises)": (8.0, "$/application"),
            "Dishonoured Payment Charge": (16.0, "$/payment"),
        }

    def test_base_identities_and_provenance(self):
        recs = _NFP_parse()
        assert recs["1.1"].tariff_name == "Domestic Service (Rate 1.1)"
        assert recs["2.3"].tariff_name == "General Service 110 kVA - 1000 kVA (Rate 2.3)"
        for r in recs.values():
            for c in r.components:
                assert c.effective_date == "2026-07-01"
                assert c.source_url == NFP_URL
                assert c.source_detail

    def test_mutated_seasonal_rejected_independently(self):
        recs = _NFP_parse(lambda p: p.__setitem__(25, p[25].replace("0.953¢", "0.953")))
        assert "1.1S" not in recs
        assert {"1.1", "PPD", "RULE-9K", "FEES"} <= set(recs)

    def test_mutated_discount_rejected_independently(self):
        recs = _NFP_parse(lambda p: p.__setitem__(27, p[27].replace("1.5%", "2%")))
        assert "PPD" not in recs
        assert {"1.1S", "RULE-9K", "FEES", "2.3"} <= set(recs)

    def test_mutated_9k_rejected_independently(self):
        recs = _NFP_parse(lambda p: p.__setitem__(12, p[12].replace("per kVA", "per kW")))
        assert "RULE-9K" not in recs
        assert {"1.1S", "PPD", "FEES"} <= set(recs)

    def test_missing_date_rejects_only_that_page(self):
        recs = _NFP_parse(lambda p: p.__setitem__(25, p[25].replace("Effective July 1, 2026", "")))
        assert "1.1S" not in recs
        assert "FEES" in recs and "RULE-9K" in recs

    def test_one_fee_failure_keeps_other_fees(self):
        recs = _NFP_parse(lambda p: p.__setitem__(13, p[13].replace("$8.00", "")))
        names = {c.component_name for c in recs["FEES"].components}
        assert "Application Fee (name change / new premises)" not in names
        assert "Dishonoured Payment Charge" in names

    def test_price_follows_source(self):
        recs = _NFP_parse(lambda p: p.__setitem__(
            25, p[25].replace("0.953¢", "1.100¢").replace("(1.297)¢", "(1.500)¢")))
        assert _NFP_comp(recs["1.1S"], "Winter Season Premium Adjustment").charge_value == 0.011
        assert _NFP_comp(recs["1.1S"], "Non-Winter Season Credit Adjustment").charge_value == -0.015

    def test_scrape_marks_live_and_keeps_extras(self):
        scraper = NewfoundlandPowerScraper()
        pages = _NFP_pages()
        text = "\n".join(p.text for p in pages)
        html = '<body><a href="RateBook.pdf">Schedule of Rates</a></body>'
        with patch.object(scraper, "fetch_page", return_value=html), \
             patch.object(scraper, "fetch_bytes", return_value=b"pdf"), \
             patch("scrapers.utilities.newfoundland_power.extract_pdf_text", return_value=text), \
             patch("scrapers.utilities.newfoundland_power.extract_pdf_pages", return_value=pages):
            records = scraper._try_live_scrape()
        assert len(records) == 8
        assert all("Provenance: live_parsed" in r.notes for r in records)

    def test_pages_failure_keeps_base_records(self):
        scraper = NewfoundlandPowerScraper()
        text = "\n".join(p.text for p in _NFP_pages())
        html = '<body><a href="RateBook.pdf">Schedule of Rates</a></body>'
        with patch.object(scraper, "fetch_page", return_value=html), \
             patch.object(scraper, "fetch_bytes", return_value=b"pdf"), \
             patch("scrapers.utilities.newfoundland_power.extract_pdf_text", return_value=text):
            records = scraper._try_live_scrape()
        assert {r.tariff_code for r in records} == {"1.1", "2.1", "2.3", "2.4"}


class TestAllTier1UtilitiesBasicSanity:
    """Verify all 8 Tier 1 utilities produce valid TariffRecords."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from scrapers.utilities.manitoba_hydro import ManitobaHydroScraper
        from scrapers.utilities.nb_power import NBPowerScraper
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper
        from scrapers.utilities.bc_hydro import BCHydroScraper
        from scrapers.utilities.hydro_quebec import HydroQuebecScraper
        from scrapers.utilities.saskpower import SaskPowerScraper
        from scrapers.utilities.nl_hydro import NLHydroScraper
        from scrapers.utilities.newfoundland_power import NewfoundlandPowerScraper

        scrapers = [
            ManitobaHydroScraper, NBPowerScraper, NovaScotiaPowerScraper,
            BCHydroScraper, HydroQuebecScraper, SaskPowerScraper,
            NLHydroScraper, NewfoundlandPowerScraper,
        ]
        self.all_records = []
        for cls in scrapers:
            with patch.object(cls, "_try_live_scrape", return_value=None):
                self.all_records.extend(cls().scrape())

    def test_all_records_are_tariff_records(self):
        for r in self.all_records:
            assert isinstance(r, TariffRecord)

    def test_all_have_components(self):
        for r in self.all_records:
            assert len(r.components) >= 1

    def test_all_have_valid_structure(self):
        valid = {"flat", "tiered", "demand", "tou", "mixed"}
        for r in self.all_records:
            assert r.rate_structure in valid

    def test_all_energy_rates_positive(self):
        for r in self.all_records:
            for c in r.components:
                if c.component_type == "energy":
                    assert c.charge_value > 0

    def test_all_have_source_url(self):
        for r in self.all_records:
            assert r.source_url is not None
            assert r.source_url.startswith("http")

    def test_total_tariff_count(self):
        """8 utilities should produce at least 19 tariff records total."""
        assert len(self.all_records) >= 19


# ======================================================================
# BC Hydro power-factor surcharge
# ======================================================================
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scrapers.utilities.bc_hydro import BCHydroScraper, TARIFF_URL
from scrapers.utils.parsing import DocumentPage


BCHPF_FIXTURE = Path(__file__).parent / "fixtures" / "bc_hydro_business.json"
BCHPF_BUSINESS = {"1300", "1500", "1600"}


@pytest.fixture
def BCHPF_document():
    return json.loads(BCHPF_FIXTURE.read_text(encoding="utf-8"))


def BCHPF_parse(BCHPF_document):
    scraper = BCHydroScraper()
    with patch.object(scraper, "now_iso", return_value="2026-10-05T00:00:00+00:00"):
        return scraper._parse_business_tariff([DocumentPage(**page) for page in BCHPF_document["pages"]])


def BCHPF_surcharge(record):
    return [component for component in record.components if component.component_name == "Conditional Power Factor Surcharge"]


def test_bchpf_power_factor_tiers_are_conditional_rate_section_fractions(BCHPF_document):
    records = BCHPF_parse(BCHPF_document)
    assert {record.tariff_code for record in records if record.tariff_code in BCHPF_BUSINESS} == BCHPF_BUSINESS
    for record in records:
        if record.tariff_code not in BCHPF_BUSINESS:
            continue
        tiers = BCHPF_surcharge(record)
        assert [component.charge_value for component in tiers] == [.02, .04, .09, .16, .24, .34, .44, .57, .72, .80]
        assert all(component.component_type == "adjustment" and component.sub_component == "conditional"
                   and component.charge_unit == "fraction of Rate section charges"
                   and component.source_url == TARIFF_URL
                   and component.source_detail == "Electric Tariff Terms and Conditions section 7.2; PDF pages 53-54"
                   and component.effective_date == "2025-04-01" for component in tiers)
        assert "less than 90% but 88% or more" in tiers[0].notes
        assert "less than 50%" in tiers[-1].notes
        assert all("Not a billing-demand adjustment" in component.notes for component in tiers)


def test_bchpf_changed_official_percentage_propagates(BCHPF_document):
    page = next(page for page in BCHPF_document["pages"] if page["page_number"] == 54)
    page["text"] = page["text"].replace("Less than 90% but 88% or more 2", "Less than 90% but 88% or more 3")
    records = BCHPF_parse(BCHPF_document)
    assert {record.tariff_code for record in records if record.tariff_code in BCHPF_BUSINESS} == BCHPF_BUSINESS
    assert all(BCHPF_surcharge(record)[0].charge_value == .03 for record in records if record.tariff_code in BCHPF_BUSINESS)


@pytest.mark.parametrize("missing_page", [53, 54])
def test_bchpf_missing_clause_rejects_business_only(BCHPF_document, missing_page):
    BCHPF_document["pages"] = [page for page in BCHPF_document["pages"] if page["page_number"] != missing_page]
    records = BCHPF_parse(BCHPF_document)
    assert {record.tariff_code for record in records if record.tariff_code in BCHPF_BUSINESS} == set()
    assert [record.tariff_name for record in records] == ["Standard Service Charges (Terms and Conditions Section 11)"]


def test_bchpf_malformed_clause_rejects_business_only(BCHPF_document):
    page = next(page for page in BCHPF_document["pages"] if page["page_number"] == 54)
    page["text"] = page["text"].replace("Less than 88% but 85% or more 4", "Less than 88% but 85% or more unknown")
    assert [record.tariff_name for record in BCHPF_parse(BCHPF_document)] == ["Standard Service Charges (Terms and Conditions Section 11)"]


# ======================================================================
# Centra Gas PUB schedule conditions
# ======================================================================
import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities.centra_gas import CentraGasScraper, PAGE_URLS


@pytest.fixture
def CGC_pages():
    fixture = json.loads((Path(__file__).resolve().parent / "fixtures" / "centra_gas.json").read_text(encoding="utf-8"))
    return {key: page["text"] for key, page in fixture["pages"].items()}


def CGC_parse(CGC_pages):
    return {record.tariff_code: record for record in CentraGasScraper().parse_pages(CGC_pages, date(2026, 10, 5))}


def test_cgc_approved_conditions_and_sources(CGC_pages):
    records = CGC_parse(CGC_pages)
    assert len(records) == 12
    assert records["SGS"].usage_max == records["COM-LGS"].usage_max == 680000
    assert records["COM-HVF-S"].usage_min == records["COM-MFS-T"].usage_min == 680000
    assert "one year" in records["COM-LGS"].eligibility
    assert "highest daily m³" in records["COM-HVF-S"].eligibility
    assert "preceding eleven months" in records["COM-MFS-S"].eligibility
    assert "200 GJ/day" in records["COM-HVF-T"].eligibility
    assert "pass-through commodity/transport" in records["COM-IS-S"].eligibility
    assert PAGE_URLS["schedule"] in records["COM-HVF-T"].notes
    assert "PDF page 34" in next(component.source_detail for component in records["COM-HVF-T"].components
                                 if component.component_type == "demand")


@pytest.mark.parametrize(("old", "new", "missing"), [
    ("PDF page 17", "PDF page 77", {"SGS", "SGS-MKT", "COM-SGS", "COM-SGS-MKT", "COM-LGS", "COM-LGS-MKT"}),
    ("PDF page 34", "PDF page 74", {"COM-HVF-S", "COM-HVF-T", "COM-MFS-S", "COM-MFS-T", "COM-IS-S", "COM-IS-T"}),
    ("equals or exceeds 200 GJ", "equals or exceeds some GJ", {"COM-HVF-T", "COM-MFS-T", "COM-IS-T"}),
    ("pass-through cost of acquiring additional gas commodity", "unspecified cost of gas", {"COM-IS-S", "COM-IS-T"}),
])
def test_cgc_required_schedule_section_rejects_affected_classes(CGC_pages, old, new, missing):
    assert old in CGC_pages["schedule"]
    original = set(CGC_parse(CGC_pages))
    CGC_pages["schedule"] = CGC_pages["schedule"].replace(old, new, 1)
    assert set(CGC_parse(CGC_pages)) == original - missing


def test_cgc_published_boundary_mutation_propagates(CGC_pages):
    CGC_pages["schedule"] = CGC_pages["schedule"].replace("equals or exceeds 680,000 m3", "equals or exceeds 690,000 m3", 1)
    records = CGC_parse(CGC_pages)
    assert records["COM-HVF-S"].usage_min == records["COM-HVF-T"].usage_min == 690000
    assert "690,000 m³" in records["COM-HVF-S"].eligibility
    assert records["COM-MFS-S"].usage_min == 680000


# ======================================================================
# Energir inventory-related adjustments (evidence only)
# ======================================================================
import json
from datetime import date
from pathlib import Path

from scrapers.utilities.energir import EnergirScraper


def ENI_fixture():
    return json.loads((Path(__file__).resolve().parent / "fixtures" / "energir.json").read_text(encoding="utf-8"))


def ENI_parse(document):
    return EnergirScraper().parse_pages(
        {"pricing": document["pricing"]["text"],
         "tariff": " ".join(page["text"] for page in document["tariff_pages"])},
        date(2026, 10, 5), tariff_url=document["tariff_url"])


def test_eni_inventory_evidence_does_not_invent_a_price():
    document = ENI_fixture()
    assert "adjustment is necessary" in document["inventory_reference"]["pages"][0]["text"]
    assert "calculated separately" in document["inventory_reference"]["pages"][1]["text"]
    assert "credit" in document["inventory_reference"]["pages"][2]["credit_text"]
    assert "15.535" in document["supply_price_history"]["text"]
    records = ENI_parse(document)
    assert {record.tariff_name for record in records} == {
        "Residential — Rate D1", "Business — Rate D1", "Commercial — Rate D3", "Commercial — Rate D4"}
    for record in records:
        components = {component.component_name: component for component in record.components}
        assert not any("inventory" in name.lower() for name in components)
        assert (components["Natural Gas Supply"].charge_value,
                components["Transportation"].charge_value) == (0.15535, 0.02165)
        assert all(component.source_url == document["tariff_url"] and component.source_detail
                   for component in record.components)


def test_eni_shared_prices_follow_published_values():
    document = ENI_fixture()
    for page in document["tariff_pages"]:
        page["text"] = page["text"].replace("15.535¢/m³", "15.700¢/m³")
        page["text"] = page["text"].replace("2.165¢/m³", "2.300¢/m³")
    for record in ENI_parse(document):
        values = {component.component_name: component.charge_value for component in record.components}
        assert values["Natural Gas Supply"] == 0.157
        assert values["Transportation"] == 0.023
        assert not any("inventory" in name.lower() for name in values)


def test_eni_missing_required_dated_supply_price_rejects_live_records():
    document = ENI_fixture()
    for page in document["tariff_pages"]:
        page["text"] = page["text"].replace("as of October 1, 2026 is\n15.535¢/m³",
                                             "as of October 1, 2026 is\nnot published")
    assert ENI_parse(document) == []


# ======================================================================
# FortisBC Energy Revelstoke business Rates 2/3
# ======================================================================
import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.utilities.fortisbc_energy import FortisBCEnergyScraper


@pytest.fixture
def FBER_document():
    path = Path(__file__).parent / "fixtures" / "fortisbc_energy.json"
    return json.loads(path.read_text(encoding="utf-8"))


def FBER_parse(FBER_document, rate2=None, rate3=None, index=None):
    pages = {key: page["text"] for key, page in FBER_document["pages"].items()}
    for rate, replacement in (("rate2", rate2), ("rate3", rate3)):
        if replacement is not None:
            excerpt = FBER_document["revelstoke_business"][rate]
            assert excerpt in pages["business"]
            pages["business"] = pages["business"].replace(excerpt, replacement, 1)
    pages["tariffs"] = index if index is not None else FBER_document["revelstoke_tariffs"]["text"]
    return {record.tariff_name: record for record in FortisBCEnergyScraper().parse_pages(pages, date(2026, 10, 5))}


FBER_RATE2 = "Commercial — Rate 2 (Revelstoke propane)"
FBER_RATE3 = "Commercial — Rate 3 (Revelstoke propane)"


def test_fber_revelstoke_business_prices_units_and_provenance(FBER_document):
    records = FBER_parse(FBER_document)
    assert len(records) == 8
    for name, basic, delivery, storage in ((FBER_RATE2, 1.4309, 5.877, 2.493),
                                           (FBER_RATE3, 4.3526, 5.377, 2.268)):
        record = records[name]
        assert record.effective_date == "2026-07-01" and record.sub_class == "Revelstoke (propane)"
        assert {component.component_type: (component.charge_value, component.charge_unit)
                for component in record.components} == {
                    "fixed": (basic, "$/day"), "delivery": (delivery, "$/GJ"),
                    "transmission": (storage, "$/GJ"), "commodity": (1.660, "$/GJ"),
                    "carbon": (0.0, "$/GJ")}
        assert next(c for c in record.components if c.component_type == "commodity").component_name == "Cost of Propane"
        assert all(c.source_url and c.source_detail and c.effective_date for c in record.components)
        assert "motor fuel tax applies to propane" in next(c for c in record.components if c.component_type == "carbon").notes
    assert records[FBER_RATE2].usage_max == 2000 and records[FBER_RATE3].usage_min == 2000


def test_fber_prices_follow_business_source(FBER_document):
    rate2 = FBER_document["revelstoke_business"]["rate2"].replace("$5.877", "$6.000")
    rate3 = FBER_document["revelstoke_business"]["rate3"].replace("$4.3526", "$4.5000")
    records = FBER_parse(FBER_document, rate2=rate2, rate3=rate3)
    assert next(c.charge_value for c in records[FBER_RATE2].components if c.component_type == "delivery") == 6.0
    assert next(c.charge_value for c in records[FBER_RATE3].components if c.component_type == "fixed") == 4.5


@pytest.mark.parametrize(("rate", "old", "new", "missing"), [
    ("rate2", "$2.493", "2.493", FBER_RATE2),
    ("rate2", "July 1, 2026", "July 1, 2027", FBER_RATE2),
    ("rate3", "$5.377", "5.377", FBER_RATE3),
    ("rate3", "Cost of gas per GJ $1.660", "Cost of gas per GJ", FBER_RATE3),
])
def test_fber_missing_or_future_table_is_isolated(FBER_document, rate, old, new, missing):
    excerpt = FBER_document["revelstoke_business"][rate]
    assert old in excerpt
    records = FBER_parse(FBER_document, **{rate: excerpt.replace(old, new)})
    assert missing not in records and ({FBER_RATE2, FBER_RATE3} - {missing}) <= set(records)
    assert len(records) == 7


@pytest.mark.parametrize(("old", "new", "missing"), [
    ("Rate 2 Small commercial rate", "Rate 2 Unspecified rate", FBER_RATE2),
    ("Rate 3 Large commercial rate", "Rate 3 Unspecified rate", FBER_RATE3),
])
def test_fber_missing_class_authorization_is_isolated(FBER_document, old, new, missing):
    index = FBER_document["revelstoke_tariffs"]["text"]
    records = FBER_parse(FBER_document, index=index.replace(old, new))
    assert missing not in records and ({FBER_RATE2, FBER_RATE3} - {missing}) <= set(records)


def test_fber_rate2_cannot_borrow_rate3_revelstoke_authorization(FBER_document):
    index = FBER_document["revelstoke_tariffs"]["text"]
    index = index.replace("the Municipality of Revelstoke, and the Fort Nelson Service Area.",
                          "the Fort Nelson Service Area.", 1)
    records = FBER_parse(FBER_document, index=index)
    assert FBER_RATE2 not in records and FBER_RATE3 in records


def test_fber_missing_propane_evidence_rejects_both_business_classes(FBER_document):
    FBER_document["pages"]["residential"]["text"] = FBER_document["pages"]["residential"]["text"].replace(
        "Revelstoke (for propane customers)", "Revelstoke")
    assert not ({FBER_RATE2, FBER_RATE3} & set(FBER_parse(FBER_document)))


# ======================================================================
# Hydro-Quebec Rate M net metering Option I
# ======================================================================
import json
from pathlib import Path

import pytest



@pytest.fixture
def HQM_document():
    return json.loads((Path(__file__).parent / "fixtures" / "hydro_quebec_domestic.json").read_text(encoding="utf-8"))


def test_hqm_rate_m_option_i_uses_shared_surplus_bank_credit(HQM_document):
    live = HQX_build(HQM_document)
    assert len(live) == 15
    rate = live["NET_METERING_I_M"]
    assert rate.tariff_name == "Net Metering Option I - Rate M Customer-Generators"
    assert rate.customer_class == "commercial" and rate.effective_date == "2026-04-01"
    assert "Rate M contract" in rate.eligibility and "1,000 kilowatts" in rate.eligibility
    assert "estimated maximum power demand" in rate.eligibility and "photovoltaic power" in rate.eligibility
    assert "Rate M charges remain separate" in rate.notes and "cannot be negative" in rate.notes
    assert len(rate.components) == 1
    credit = rate.components[0]
    assert credit.charge_value == -0.0473 and credit.charge_unit == "$/kWh of surplus-bank balance"
    assert credit.sub_component == "conditional" and "reset to zero" in credit.notes
    assert credit.source_url == HQM_document["source_url"]
    assert all(str(page) in credit.source_detail for page in (25, 26, 27, 56))
    assert credit.effective_date == "2026-04-01"


@pytest.mark.parametrize(("page", "absent"), [(56, {"NET_METERING_I_M"}), (26, {"NET_METERING_I", "NET_METERING_I_M"})])
def test_hqm_missing_section_isolated(HQM_document, page, absent):
    live = HQX_build(HQM_document, remove={page})
    assert set(HQX_build(HQM_document)) - set(live) == absent


def test_hqm_rate_m_application_mutation_isolated(HQM_document):
    live = HQX_build(HQM_document, edits=[(56, "Rate M contract", "Rate G contract")])
    assert "NET_METERING_I_M" not in live
    assert "NET_METERING_I" in live and "FLEX_M" in live


def test_hqm_common_credit_value_propagates(HQM_document):
    live = HQX_build(HQM_document, edits=[(26, "4.730", "5.125")])
    assert live["NET_METERING_I_M"].components[0].charge_value == -0.05125
    assert live["NET_METERING_I"].components[0].charge_value == -0.05125


# ======================================================================
# NL Hydro industrial firm and net metering (batch 9)
# ======================================================================
from scrapers.utilities.nl_hydro import NLHydroScraper as NLB9_NLHydroScraper
import copy
import json
from datetime import date
from pathlib import Path

from pipeline.export_json import derive_provenance
from scrapers.utils.parsing import DocumentPage


def NLB9__document():
    return json.loads((Path(__file__).resolve().parent / "fixtures" / "nl_hydro.json").read_text(encoding="utf-8"))


def NLB9__parse(document):
    scraper = NLB9_NLHydroScraper()
    pages = [DocumentPage(**page) for page in document["pages"] + document["wp1_pages"]]
    records = scraper.parse_schedule_pages(pages, document["source_url"], today=date(2026, 10, 6))
    return {record.tariff_code: record for record in records}


def test_nlb9_nl_hydro_industrial_firm_prices_and_provenance():
    document = NLB9__document()
    records = NLB9__parse(document)
    assert len(records) == 21
    island = records["IND-FIRM"]
    assert [(part.charge_value, part.charge_unit) for part in island.components[:4]] == [
        (10.73, "$/kW/month"), (0.04428, "$/kWh"), (0.01987, "$/kWh"), (0.00007, "$/kWh")]
    assert all(part.sub_component == "conditional" and part.charge_unit == "$/year"
               for part in island.components[4:])
    labrador = records["LAB-IND"]
    assert [(part.charge_value, part.charge_unit) for part in labrador.components] == [
        (1.08, "$/kW/month"), (0.41, "$/kW/month"), (29.22, "$/MWh"), (78.61, "$/MWh")]
    assert labrador.components[0].sub_component == "conditional"
    assert "forecast-weighted" in labrador.notes
    for code in ("IND-FIRM", "LAB-IND", "NM"):
        record = records[code]
        assert record.effective_date == "2026-07-01"
        assert derive_provenance(record.confidence, record.notes) == "live"
        assert all(part.source_url == document["source_url"] and part.source_detail and
                   part.effective_date == record.effective_date for part in record.components)


def test_nlb9_nl_hydro_net_metering_rule_is_conditional_not_a_flat_price():
    option = NLB9__parse(NLB9__document())["NM"]
    assert option.rate_structure == "mixed"
    assert len(option.components) == 1
    credit = option.components[0]
    assert credit.charge_value == -1.0
    assert credit.charge_unit == "fraction of applicable class energy rate per eligible kWh"
    assert credit.sub_component == "conditional"
    assert "not a replacement tariff" in option.notes
    assert "variable rates" not in credit.charge_unit


def test_nlb9_nl_hydro_industrial_and_option_pages_fail_independently():
    baseline = NLB9__parse(NLB9__document())
    for page_number, expected in ((9, "IND-FIRM"), (63, "LAB-IND"), (68, "NM")):
        document = copy.deepcopy(NLB9__document())
        document["wp1_pages"] = [page for page in document["wp1_pages"]
                                 if page["page_number"] != page_number]
        assert set(NLB9__parse(document)) == set(baseline) - {expected}


def test_nlb9_nl_hydro_industrial_source_mutations_fail_closed():
    for page_number, old, replacement, expected in (
        (9, "$10.73", "missing", "IND-FIRM"),
        (10, "Corner Brook Pulp and Paper Limited", "Unknown Company", "IND-FIRM"),
        (62, "66 kV or greater", "unknown voltage", "LAB-IND"),
        (63, "$29.22/MWh", "unknown", "LAB-IND"),
        (67, "5.0 MW", "unknown", "NM"),
        (68, "Banked Energy Credits", "unknown", "NM"),
    ):
        document = NLB9__document()
        page = next(page for page in document["wp1_pages"] if page["page_number"] == page_number)
        assert old in page["text"]
        page["text"] = page["text"].replace(old, replacement)
        assert expected not in NLB9__parse(document)


# ======================================================================
# Energir D5 interruptible and RNG supply (batch 9)
# ======================================================================
from scrapers.utilities.energir import EnergirScraper as END5_EnergirScraper
import json
from datetime import date
from pathlib import Path



def END5__document():
    path = Path(__file__).resolve().parent / "fixtures" / "energir.json"
    return json.loads(path.read_text(encoding="utf-8"))


def END5__parse(document):
    pages = document["tariff_pages"] + document["d5_pages"]
    return {record.tariff_code: record for record in END5_EnergirScraper().parse_pages(
        {"pricing": document["pricing"]["text"], "tariff": " ".join(page["text"] for page in pages)},
        today=date(2026, 10, 6), tariff_url=document["tariff_url"])}


def test_end5_energir_d5_units_eligibility_and_source():
    document = END5__document()
    records = END5__parse(document)
    assert set(records) == {"D1", "D3", "D4", "D5"}
    d5 = records["D5"]
    assert d5.tariff_name == "Commercial — Rate D5" and d5.effective_date == "2026-10-01"
    assert "3,200 m³/day" in d5.eligibility and "Category A or B, not both" in d5.eligibility
    delivery = [component for component in d5.components if component.component_type == "delivery"]
    assert [(component.charge_value, component.tier_threshold) for component in delivery] == [
        (0.15389, 3000), (0.11254, 10000), (0.09759, 30000), (0.06491, 100000),
        (0.05401, 300000), (0.04784, None)]
    assert all(component.charge_unit == "$/m³" and "14.4.2.1" in component.source_detail for component in delivery)
    balancing = [component for component in d5.components if component.component_name.startswith("Load Balancing")]
    assert [(component.charge_value, component.sub_component) for component in balancing] == [
        (-0.01665, "conditional"), (0.02477, "conditional")]
    assert all(component.source_url == document["tariff_url"] and component.source_detail
               and component.effective_date == "2026-10-01" for component in d5.components)
    assert "$5.00" not in [component.component_name for component in d5.components]
    assert "pass-through" in d5.notes and "minimum annual obligation" in d5.notes


def test_end5_energir_d5_malformed_section_fails_independently():
    document = END5__document()
    document["d5_pages"][0]["text"] = document["d5_pages"][0]["text"].replace(
        "from 3,000 to 10,000 11.254", "from 4,000 to 10,000 11.254")
    assert set(END5__parse(document)) == {"D1", "D3", "D4"}


def test_end5_energir_d5_missing_interruption_terms_fails_independently():
    document = END5__document()
    document["d5_pages"][2]["text"] = document["d5_pages"][2]["text"].replace(
        "14.4.3 MINIMUM ANNUAL OBLIGATION", "14.4.3 UNKNOWN")
    assert set(END5__parse(document)) == {"D1", "D3", "D4"}


def test_end5_energir_renewable_supply_is_optional_not_additive():
    records = END5__parse(END5__document())
    for record in records.values():
        supply = [component for component in record.components if component.component_type == "commodity"]
        assert [(component.component_name, component.charge_value, component.charge_unit) for component in supply] == [
            ("Natural Gas Supply", 0.15535, "$/m³"),
            ("Gas from Renewable Sources Supply", 0.85239, "$/m³")]
        assert supply[1].sub_component == "conditional"
        assert "replacement" in supply[1].notes


def test_end5_energir_missing_renewable_price_keeps_base_rates():
    document = END5__document()
    document["tariff_pages"][0]["text"] = document["tariff_pages"][0]["text"].replace(
        "85.239¢/m³", "price to be determined")
    records = END5__parse(document)
    assert set(records) == {"D1", "D3", "D4", "D5"}
    assert all(not any(component.component_name == "Gas from Renewable Sources Supply"
                       for component in record.components) for record in records.values())


# ======================================================================
# Manitoba Hydro per-page failure isolation (batch 9)
# ======================================================================
from scrapers.utilities.manitoba_hydro import COMMERCIAL_URL as MBB9_COMMERCIAL_URL, RESIDENTIAL_URL as MBB9_RESIDENTIAL_URL, ManitobaHydroScraper as MBB9_ManitobaHydroScraper
import html
import json
from pathlib import Path
from unittest.mock import patch

from pipeline.export_json import derive_provenance
from scrapers.base import BaseScraper


MBB9_PAGES = json.loads((Path(__file__).resolve().parent / "fixtures" / "manitoba_hydro.json").read_text(encoding="utf-8"))["pages"]


def MBB9__html(page):
    return "<html><body>" + "".join(f"<p>{html.escape(line)}</p>" for line in MBB9_PAGES[page]["lines"]) + "</body></html>"


def test_mbb9_ManitobaHydro_commercial_survives_residential_fetch_failure():
    def fetch(scraper, url, delay=1.0):
        if url == MBB9_RESIDENTIAL_URL:
            raise ConnectionError("residential unavailable")
        assert url == MBB9_COMMERCIAL_URL
        return MBB9__html("commercial")

    with patch.object(BaseScraper, "fetch_page", fetch):
        records = MBB9_ManitobaHydroScraper().scrape()

    live = [record for record in records if derive_provenance(record.confidence, record.notes) == "live"]
    assert len(live) == 9
    assert all(record.source_url == MBB9_COMMERCIAL_URL for record in live)
    assert all(component.source_url and component.source_detail and component.effective_date
               for record in live for component in record.components)
    assert any(record.tariff_name == "Residential Service" and
               derive_provenance(record.confidence, record.notes) == "seed" for record in records)


def test_mbb9_ManitobaHydro_residential_survives_commercial_fetch_failure():
    def fetch(scraper, url, delay=1.0):
        if url == MBB9_COMMERCIAL_URL:
            raise ConnectionError("commercial unavailable")
        assert url == MBB9_RESIDENTIAL_URL
        return MBB9__html("residential")

    with patch.object(BaseScraper, "fetch_page", fetch):
        records = MBB9_ManitobaHydroScraper().scrape()

    live = [record for record in records if derive_provenance(record.confidence, record.notes) == "live"]
    assert {record.tariff_name for record in live} == {
        "Residential Service", "Residential Seasonal Service", "Residential Diesel Service"
    }
    assert all(component.source_url and component.source_detail and component.effective_date
               for record in live for component in record.components)
    assert any(record.tariff_name == "General Service Medium" and
               derive_provenance(record.confidence, record.notes) == "seed" for record in records)


# ======================================================================
# Newfoundland Power curtailable and net metering (batch 9)
# ======================================================================
from scrapers.utilities.newfoundland_power import NewfoundlandPowerScraper as NPB9_NewfoundlandPowerScraper
import json
from pathlib import Path
from unittest.mock import patch

from scrapers.utils.parsing import DocumentPage


NPB9_FIXTURE = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "newfoundland_power.json").read_text(encoding="utf-8")
)
NPB9_URL = NPB9_FIXTURE["source_url"]


def NPB9__pages(mutate=None):
    pages = {page["page_number"]: page["text"] for page in NPB9_FIXTURE["pages"] + NPB9_FIXTURE["optional_pages"]}
    if mutate:
        mutate(pages)
    return [DocumentPage(number, text) for number, text in sorted(pages.items())]


def NPB9__parse(mutate=None):
    scraper = NPB9_NewfoundlandPowerScraper()
    pages = NPB9__pages(mutate)
    base = scraper._parse_ratebook("\n".join(page.text for page in pages), NPB9_URL)
    scraper._annotate_base(base, pages, NPB9_URL)
    return {rate.tariff_code: rate for rate in base + scraper._parse_pages(pages, NPB9_URL, base)}


def test_npb9_newfoundland_power_options_source_prices_and_dates():
    records = NPB9__parse()
    assert len(records) == 11
    for code in ("2.3-CURT1", "2.4-CURT1"):
        rate = records[code]
        credit = rate.components[0]
        assert (credit.charge_value, credit.charge_unit, credit.demand_unit) == (-29.0, "$/kVA", "kVA")
        assert rate.effective_date == credit.effective_date == "2026-07-01"
        assert "Option 2" in rate.notes and "May" in rate.notes
        assert "pages 30-31" in credit.source_detail
    net = records["1.1-NM"]
    assert (net.components[0].charge_value, net.components[0].charge_unit) == (-0.15587, "$/kWh")
    assert "pages 32-34" in net.components[0].source_detail
    assert "annual cash settlement is priced here" in net.notes
    assert all(component.source_url == NPB9_URL and component.source_detail
               for rate in records.values() for component in rate.components)


def test_npb9_newfoundland_power_options_fail_independently_on_missing_page():
    records = NPB9__parse(lambda pages: pages.pop(31))
    assert "2.3-CURT1" not in records and "2.4-CURT1" not in records
    assert "1.1-NM" in records and "FEES" in records


def test_npb9_newfoundland_power_net_metering_rejects_missing_date():
    records = NPB9__parse(lambda pages: pages.__setitem__(33, pages[33].replace("Effective July 1, 2026", "")))
    assert "1.1-NM" not in records
    assert "2.3-CURT1" in records


def test_npb9_newfoundland_power_curtail_credit_tracks_source():
    records = NPB9__parse(lambda pages: pages.__setitem__(30, pages[30].replace("$29 per kVA", "$31 per kVA")))
    assert records["2.3-CURT1"].components[0].charge_value == -31.0
    assert records["2.4-CURT1"].components[0].charge_value == -31.0


def test_npb9_newfoundland_power_optional_scrape_marks_live():
    scraper = NPB9_NewfoundlandPowerScraper()
    pages = NPB9__pages()
    text = "\n".join(page.text for page in pages)
    with patch.object(scraper, "fetch_page", return_value='<a href="RateBook.pdf">Schedule of Rates</a>'),\
         patch.object(scraper, "fetch_bytes", return_value=b"pdf"),\
         patch("scrapers.utilities.newfoundland_power.extract_pdf_text", return_value=text),\
         patch("scrapers.utilities.newfoundland_power.extract_pdf_pages", return_value=pages):
        records = scraper.scrape()
    assert len(records) == 11
    assert all("Provenance: live_parsed" in rate.notes for rate in records)


# ======================================================================
# NB Power small and large industrial (batch 9)
# ======================================================================
from scrapers.utilities.nb_power import BUSINESS_URL as NBB9_BUSINESS_URL, RESIDENTIAL_URL as NBB9_RESIDENTIAL_URL, NBPowerScraper as NBB9_NBPowerScraper
import json
from pathlib import Path
from unittest.mock import patch

from pipeline.export_json import derive_provenance


NBB9_FIXTURE = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "nb_power.json").read_text(encoding="utf-8")
)


def NBB9__records(business=None):
    pages = {
        NBB9_RESIDENTIAL_URL: NBB9_FIXTURE["residential"]["html"],
        NBB9_BUSINESS_URL: NBB9_FIXTURE["business"]["html"] if business is None else business,
    }
    with patch.object(NBB9_NBPowerScraper, "fetch_page", side_effect=pages.__getitem__):
        return {record.tariff_name: record for record in NBB9_NBPowerScraper().scrape()}


def test_nbb9_nb_power_industrial_live_charges_and_identity():
    records = NBB9__records()
    small = records["Small Industrial Service"]
    large = records["Large Industrial Service"]
    assert small.demand_max_kw == 750
    assert large.demand_min_kw == 750
    assert [(component.charge_value, component.charge_unit) for component in small.components] == [
        (9.39, "$/kW"), (0.1863, "$/kWh"), (0.0903, "$/kWh"),
    ]
    assert small.components[1].tier_threshold == 100
    assert small.components[1].tier_unit == "kWh per kilowatt"
    assert [(component.charge_value, component.charge_unit) for component in large.components] == [
        (19.98, "$/kW/month"), (0.0785, "$/kWh"),
    ]
    assert large.components[0].demand_unit == "kW"
    assert "90% of the maximum kVA" in large.notes
    assert "100% of the total contracted amount" in large.notes
    for record in (small, large):
        assert record.effective_date == "2026-04-14"
        assert derive_provenance(record.confidence, record.notes) == "live"
        assert all(component.source_url == NBB9_BUSINESS_URL and component.source_detail
                   and component.effective_date == record.effective_date for component in record.components)


def test_nbb9_nb_power_large_industrial_rejects_incomplete_billing_demand():
    business = NBB9_FIXTURE["business"]["html"].replace("90% of the maximum kVA demand", "N/A", 1)
    records = NBB9__records(business)
    assert "Large Industrial Service" not in records
    assert derive_provenance(records["Small Industrial Service"].confidence,
                             records["Small Industrial Service"].notes) == "live"


def test_nbb9_nb_power_large_industrial_rejects_mismatched_energy_total():
    business = NBB9_FIXTURE["business"]["html"].replace("7.85¢ Total Charge", "7.99¢ Total Charge", 1)
    records = NBB9__records(business)
    assert "Large Industrial Service" not in records
    assert "General Service I" in records


def test_nbb9_nb_power_small_industrial_rejects_missing_tier():
    business = NBB9_FIXTURE["business"]["html"].replace("9.03¢ Total Charge", "N/A", 1)
    records = NBB9__records(business)
    small = records["Small Industrial Service"]
    assert derive_provenance(small.confidence, small.notes) == "seed"
    assert derive_provenance(records["Large Industrial Service"].confidence,
                             records["Large Industrial Service"].notes) == "live"


def test_nbb9_nb_power_small_industrial_rejects_wrong_demand_unit():
    business = NBB9_FIXTURE["business"]["html"].replace("$9.39 /kW", "$9.39 /kVA", 1)
    records = NBB9__records(business)
    small = records["Small Industrial Service"]
    assert derive_provenance(small.confidence, small.notes) == "seed"
    assert derive_provenance(records["Large Industrial Service"].confidence,
                             records["Large Industrial Service"].notes) == "live"


# ======================================================================
# BC Hydro transmission and net metering (batch 9)
# ======================================================================
from scrapers.utilities.bc_hydro import BCHydroScraper as BCHB9_BCHydroScraper, TARIFF_URL as BCHB9_TARIFF_URL
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from scrapers.utils.parsing import DocumentPage
from scrapers.utils.validation import validate_batch
from pipeline.export_json import derive_provenance


BCHB9_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "bc_hydro_business.json"


def BCHB9_transmission_pages():
    document = json.loads(BCHB9_FIXTURE.read_text(encoding="utf-8"))
    return [DocumentPage(**page) for page in document["pages"]]


def test_bchb9_BCHydro_transmission_values_and_provenance():
    records = BCHB9_BCHydroScraper()._parse_transmission_tariff(BCHB9_transmission_pages())
    assert len(records) == 1
    record = records[0]
    assert (record.tariff_code, record.effective_date, record.customer_class) == ("1830", "2026-04-01", "industrial")
    assert [(part.charge_value, part.charge_unit) for part in record.components] == [
        (12.178, "$/kVA/billing period"), (0.04914, "$/kWh"), (-0.015, "fraction"), (0.0, "fraction"),
    ]
    assert all(part.effective_date and part.source_url == BCHB9_TARIFF_URL and part.source_detail for part in record.components)
    assert "minimum" in record.notes.lower() and "50% of contract demand" in record.notes


def test_bchb9_BCHydro_transmission_fails_closed_without_continuation():
    pages = [page for page in BCHB9_transmission_pages() if page.page_number != 139]
    assert BCHB9_BCHydroScraper()._parse_transmission_tariff(pages) == []


def test_bchb9_BCHydro_transmission_fails_closed_on_changed_unit():
    pages = [replace(page, text=page.text.replace("per kVA of Billing Demand", "per kW of Billing Demand"))
             if page.page_number == 138 else page for page in BCHB9_transmission_pages()]
    assert BCHB9_BCHydroScraper()._parse_transmission_tariff(pages) == []


def test_bchb9_BCHydro_transmission_fails_closed_on_future_date():
    pages = [replace(page, text=page.text.replace("April 1, 2026", "April 1, 2027"))
             if page.page_number in (138, 139, 140) else page for page in BCHB9_transmission_pages()]
    assert BCHB9_BCHydroScraper()._parse_transmission_tariff(pages) == []


def test_bchb9_BCHydro_closed_net_metering_credit_is_not_cash_price():
    records = BCHB9_BCHydroScraper()._parse_net_metering_tariff(BCHB9_transmission_pages())
    assert len(records) == 1
    record = records[0]
    assert (record.tariff_code, record.effective_date) == ("1289", "2026-07-01")
    assert [(part.charge_value, part.charge_unit, part.sub_component) for part in record.components] == [
        (-1.0, "kWh credit/kWh net generation", "conditional"),
    ]
    assert all(part.source_url == BCHB9_TARIFF_URL and part.source_detail and part.effective_date for part in record.components)
    assert "Mid-Columbia" in record.notes and "not a replacement" in record.notes.lower()


def test_bchb9_BCHydro_net_metering_missing_price_rule_fails_closed_without_affecting_transmission():
    pages = [page for page in BCHB9_transmission_pages() if page.page_number != 224]
    scraper = BCHB9_BCHydroScraper()
    assert scraper._parse_net_metering_tariff(pages) == []
    assert len(scraper._parse_transmission_tariff(pages)) == 1


def test_bchb9_BCHydro_net_metering_changed_credit_rule_fails_closed():
    pages = [replace(page, text=page.text.replace("credit the Customer’s Generation Account with the Net Generation", "record exported power"))
             if page.page_number == 227 else page for page in BCHB9_transmission_pages()]
    assert BCHB9_BCHydroScraper()._parse_net_metering_tariff(pages) == []


def test_bchb9_BCHydro_net_metering_future_date_fails_closed():
    pages = [replace(page, text=page.text.replace("July 1, 2026", "July 1, 2027"))
             if page.page_number in range(223, 232) else page for page in BCHB9_transmission_pages()]
    assert BCHB9_BCHydroScraper()._parse_net_metering_tariff(pages) == []


def test_bchb9_BCHydro_full_document_wrapper_publishes_both_new_records():
    scraper = BCHB9_BCHydroScraper()
    residential = json.loads((BCHB9_FIXTURE.parent / "bc_hydro_residential.json").read_text(encoding="utf-8"))
    business_pages = BCHB9_transmission_pages()
    business_numbers = {page.page_number for page in business_pages}
    pages = ([DocumentPage(1, "BC Hydro Electric Tariff, Title Page\nEffective: April 1, 2025")]
             + business_pages + [DocumentPage(**page) for page in residential["pages"]
                                 if page["page_number"] not in business_numbers])
    with patch.object(scraper, "fetch_page", return_value=""),\
         patch.object(scraper, "fetch_bytes", return_value=b"pdf"),\
         patch("scrapers.utilities.bc_hydro.extract_pdf_pages", return_value=pages):
        records = scraper.scrape()
    valid, invalid = validate_batch(records)
    assert len(valid) == 11 and not invalid
    assert {record.tariff_code for record in valid} >= {"1830", "1289"}
    assert all(derive_provenance(record.confidence, record.notes) == "live" for record in valid)
    assert all(part.source_url and part.source_detail and part.effective_date for record in valid for part in record.components)


# ======================================================================
# FortisBC Electric RS31/RS33 (batch 9)
# ======================================================================
from scrapers.utilities.fortisbc_electric import FortisBCElectricScraper as FBEB9_FortisBCElectricScraper, TARIFF_URL as FBEB9_TARIFF_URL
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

from scrapers.utils.parsing import DocumentPage


def FBEB9__records():
    fixture = json.loads((Path(__file__).resolve().parent / "fixtures" / "fortisbc_electric.json")
                         .read_text(encoding="utf-8"))
    pages = [DocumentPage(**page) for key in ("pages", "large_commercial_pages", "industrial_pages")
             for page in fixture[key]]
    with patch("scrapers.utilities.fortisbc_electric._today", return_value=date(2026, 10, 6)):
        return {record.tariff_code: record for record in FBEB9_FortisBCElectricScraper().parse_schedule_pages(pages)}


def test_fbeb9_FortisBCElectric_industrial_values_and_source():
    records = FBEB9__records()
    assert set(records) == {"01", "2A", "20", "21", "22A", "23A", "30", "31", "32", "33", "85"}
    rs31 = records["31"]
    assert rs31.customer_class == "industrial" and "5,000 kVA" in rs31.eligibility
    assert [(component.component_name, component.charge_value, component.charge_unit)
            for component in rs31.components] == [
                ("Customer Charge", 4077.97, "$/month"), ("Wires Charge", 6.29, "$/kVA"),
                ("Power Supply Charge", 4.39, "$/kVA"), ("Energy Charge", 0.06851, "$/kWh")]
    assert [component.demand_unit for component in rs31.components if component.component_type == "demand"] == ["kVA", "kVA"]
    assert "stand-by" in rs31.components[1].notes
    rs33 = records["33"]
    assert rs33.customer_class == "industrial" and rs33.rate_structure == "tou"
    assert [(component.charge_value, component.charge_unit) for component in rs33.components] == [
        (3785.34, "$/month"), (0.23221, "$/kWh"), (0.06576, "$/kWh"),
        (0.30968, "$/kWh"), (0.05119, "$/kWh"), (0.0743, "$/kWh"), (0.03918, "$/kWh")]
    for code, sheet in (("31", "R-31.1"), ("33", "R-33.1")):
        assert records[code].effective_date == "2026-01-01"
        assert all(component.effective_date == "2026-01-01" and component.source_url == FBEB9_TARIFF_URL
                   and sheet in component.source_detail for component in records[code].components)


def test_fbeb9_FortisBCElectric_industrial_schedules_fail_independently():
    fixture = json.loads((Path(__file__).resolve().parent / "fixtures" / "fortisbc_electric.json")
                         .read_text(encoding="utf-8"))
    pages = [DocumentPage(**page) for page in fixture["industrial_pages"]]
    scraper = FBEB9_FortisBCElectricScraper()
    assert {record.tariff_code for record in scraper.parse_schedule_pages(pages[1:])} == {"33"}
    assert {record.tariff_code for record in scraper.parse_schedule_pages(pages[:1])} == {"31"}
    broken = pages[0].text.replace("$6.29 per kVA", "$6.29 per kW")
    assert broken != pages[0].text
    assert {record.tariff_code for record in scraper.parse_schedule_pages(
        [DocumentPage(pages[0].page_number, broken), pages[1]])} == {"33"}


def test_fbeb9_FortisBCElectric_industrial_future_date_rejected():
    fixture = json.loads((Path(__file__).resolve().parent / "fixtures" / "fortisbc_electric.json")
                         .read_text(encoding="utf-8"))
    pages = [DocumentPage(**page) for page in fixture["industrial_pages"]]
    future = pages[1].text.replace("Effective Date: January 1, 2026", "Effective Date: January 1, 2030")
    with patch("scrapers.utilities.fortisbc_electric._today", return_value=date(2026, 10, 6)):
        assert {record.tariff_code for record in FBEB9_FortisBCElectricScraper().parse_schedule_pages(
            [pages[0], DocumentPage(pages[1].page_number, future)])} == {"31"}


# ======================================================================
# Hydro-Quebec L/LG/H and business DR (batch 9)
# ======================================================================
from scrapers.utilities.hydro_quebec import HydroQuebecScraper as HQB9_HydroQuebecScraper
import json
from pathlib import Path

from scrapers.utils.parsing import DocumentPage


def HQB9__large_power_records(removed=(), edits=()):
    path = Path(__file__).resolve().parent / "fixtures" / "hydro_quebec_domestic.json"
    fixture = json.loads(path.read_text(encoding="utf-8"))
    pages = fixture["pages"] + fixture["large_power_pages"]
    for page_number, old, new in edits:
        page = next(page for page in pages if page["page_number"] == page_number and old in page["text"])
        page["text"] = page["text"].replace(old, new)
    selected = [DocumentPage(**page) for page in pages if page["page_number"] not in removed]
    records = HQB9_HydroQuebecScraper()._parse_large_power_rates(selected, "2026-04-01")
    return {record.tariff_code: record for record in records}


def test_hqb9_HydroQuebec_large_power_classes_from_official_pages():
    records = HQB9__large_power_records()
    assert set(records) == {"L", "LG", "H"}
    assert all(record.effective_date == "2026-04-01" and record.demand_min_kw == 5000 for record in records.values())
    assert all(component.source_url and component.source_detail and component.effective_date == "2026-04-01"
               for record in records.values() for component in record.components)


def test_hqb9_HydroQuebec_large_power_prices_and_conditions():
    records = HQB9__large_power_records()
    demand = {code: next(component for component in record.components if component.component_name == "Billing Demand")
              for code, record in records.items()}
    assert {code: (component.charge_value, component.charge_unit) for code, component in demand.items()} == {
        "L": (15.027, "$/kW/month"), "LG": (16.571, "$/kW/month"), "H": (6.630, "$/kW/month")}
    energies = {code: [(component.charge_value, component.charge_unit) for component in record.components
                       if component.component_type == "energy"] for code, record in records.items()}
    assert energies == {"L": [(0.03821, "$/kWh")], "LG": [(0.04324, "$/kWh")],
                        "H": [(0.06695, "$/kWh"), (0.2262, "$/kWh")]}
    assert "110%" in records["L"].notes and "26.420" in records["L"].notes
    assert "75%" in records["LG"].notes and "60%" in records["LG"].components[2].notes
    assert "24 monthly periods" in records["H"].notes and "weekends" in records["H"].components[2].notes
    assert records["H"].components[2].season_months == "12,1,2,3"
    for record in records.values():
        credits = [component for component in record.components if component.component_type == "rebate"]
        assert [credit.charge_value for credit in credits] == [-0.7131, -1.1427, -2.5512, -3.1208, -4.1239]
        assert all(credit.sub_component == "conditional" and credit.source_detail == "Article 12.2; PDF page 152" for credit in credits)
        assert "Article 12.5" in record.notes and "720 hours" in record.notes


def test_hqb9_HydroQuebec_large_power_missing_pages_reject_only_affected_class():
    for page, missing in ((64, "L"), (65, "L"), (66, "L"), (68, "LG"), (71, "H")):
        assert set(HQB9__large_power_records(removed=(page,))) == {"L", "LG", "H"} - {missing}


def test_hqb9_HydroQuebec_large_power_bad_price_and_shared_context_fail_closed():
    assert set(HQB9__large_power_records(edits=((67, "4.324 cents", "price not published"),))) == {"L", "H"}
    assert not HQB9__large_power_records(removed=(152,))
    assert not HQB9__large_power_records(removed=(154,))


def HQB9__dr_record(removed=(), old=None, new=None):
    path = Path(__file__).resolve().parent / "fixtures" / "hydro_quebec_domestic.json"
    fixture = json.loads(path.read_text(encoding="utf-8"))
    pages = fixture["dr_leeway_pages"]
    if old is not None:
        page = next(page for page in pages if old in page["text"])
        page["text"] = page["text"].replace(old, new)
    selected = [DocumentPage(**page) for page in pages if page["page_number"] not in removed]
    return HQB9_HydroQuebecScraper()._parse_dr_leeway(selected, "2026-04-01")


def test_hqb9_HydroQuebec_business_dr_leeway_conditional_credits():
    records = HQB9__dr_record()
    assert len(records) == 1
    record = records[0]
    assert record.tariff_code == "DR_LEEWAY_BUSINESS" and record.effective_date == "2026-04-01"
    assert "Rate L" in record.eligibility and "no simultaneous Commitment Option" in record.eligibility
    assert "Base-rate energy and demand charges remain separate" in record.notes
    assert [component.charge_value for component in record.components] == [
        -44.638, -74.743, -85.124, -92.391, -99.658, -1.879, -2.512]
    assert all(component.charge_unit.startswith("$/kW") and component.sub_component == "conditional"
               and component.source_url == record.source_url and component.source_detail == "Article 6.44; PDF page 97"
               and component.effective_date == "2026-04-01" for component in record.components)
    assert all(component.season_months == "12,1,2,3" for component in record.components)


def test_hqb9_HydroQuebec_business_dr_leeway_missing_page_or_price_fails_closed():
    for page in (94, 95, 96, 97, 98):
        assert not HQB9__dr_record(removed=(page,))
    assert not HQB9__dr_record(old="$85.124", new="price not published")
    assert not HQB9__dr_record(old="No credit is granted if the weekday effective interruptible power is less than 10 kilowatts.",
                          new="")


# ======================================================================
# NSPower industrial 21/22/23/25 (batch 10)
# ======================================================================
from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper as NSPB10_NovaScotiaPowerScraper
"""Pending NS Power industrial tests (Rate 21/22/23 and Interruptible Rider 25)."""

import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scrapers.utils.parsing import DocumentPage

NSPB10_FIXTURES = Path(__file__).resolve().parent / "fixtures"
NSPB10_INDUSTRIAL = json.loads((NSPB10_FIXTURES / "nova_scotia_industrial.json").read_text(encoding="utf-8"))
NSPB10_RESIDENTIAL = json.loads((NSPB10_FIXTURES / "nova_scotia_residential.json").read_text(encoding="utf-8"))
NSPB10_ALL_CODES = {"21", "22", "23", "25"}
NSPB10_TODAY = "2026-10-07"


@pytest.fixture
def NSPB10_industrial():
    return copy.deepcopy(NSPB10_INDUSTRIAL)


def NSPB10__pages(NSPB10_industrial, drop=()):
    merged = {page["page_number"]: page for page in NSPB10_RESIDENTIAL["pages"]}
    for group in NSPB10_RESIDENTIAL["building_pages"].values():
        merged.update({page["page_number"]: page for page in group})
    merged.update({page["page_number"]: page for page in NSPB10_RESIDENTIAL["business_pages"]["rates"]})
    merged.update({page["page_number"]: page for page in NSPB10_industrial["pages"]})
    return [DocumentPage(**page) for number, page in sorted(merged.items()) if number not in drop]


def NSPB10__products():
    return {kind: product["html"] for kind, product in NSPB10_RESIDENTIAL["products"].items()}


def NSPB10__parse(NSPB10_industrial, today=NSPB10_TODAY, drop=()):
    scraper = NSPB10_NovaScotiaPowerScraper()
    with patch.object(scraper, "now_iso", return_value=today + "T00:00:00+00:00"):
        records = scraper._parse_industrial_tariffs(NSPB10__pages(NSPB10_industrial, drop), NSPB10__products(), NSPB10_industrial["source_url"])
    return {record.tariff_code: record for record in records}


def NSPB10__edit(NSPB10_industrial, page_number, old, new):
    page = next(page for page in NSPB10_industrial["pages"] if page["page_number"] == page_number)
    assert old in page["text"]
    page["text"] = page["text"].replace(old, new)


def NSPB10__by_name(record):
    return {c.component_name: c for c in record.components}


def NSPB10__riders(record):
    return [round(NSPB10__by_name(record)[name].charge_value, 6) for name in (
        "FAM Actual/Balance Adjustment (Combined)", "DSM Cost Recovery Rider", "Storm Cost Recovery Rider")]


def test_nspb10_all_industrial_classes_parse_from_source(NSPB10_industrial):
    records = NSPB10__parse(NSPB10_industrial)
    assert set(records) == NSPB10_ALL_CODES
    for record in records.values():
        assert record.customer_class == "industrial" and record.rate_structure == "demand"
        assert record.effective_date == "2026-05-01" and record.end_date == "2026-12-31"
        assert "no bill total is calculated" in record.notes
        for component in record.components:
            assert component.source_url == NSPB10_industrial["source_url"] and component.source_detail and component.effective_date


def test_nspb10_small_industrial_values_units_and_riders(NSPB10_industrial):
    record = NSPB10__parse(NSPB10_industrial)["21"]
    c = NSPB10__by_name(record)
    assert record.tariff_name == "Small Industrial" and record.sub_class == "small industrial"
    assert (c["Demand Charge"].charge_value, c["Demand Charge"].charge_unit, c["Demand Charge"].demand_unit) == (7.496, "$/kVA/month", "kVA")
    credit = c["Customer-Owned Transformer Demand Reduction"]
    assert (credit.charge_value, credit.charge_unit, credit.sub_component) == (-0.32, "$/kVA/month", "conditional")
    first, balance = c["Energy Charge - First 200 kWh per kVA"], c["Energy Charge - Balance"]
    assert (first.charge_value, first.tier_threshold, first.tier_unit) == (0.13832, 200.0, "kWh/kVA of maximum demand/month")
    assert (balance.charge_value, balance.tier_number) == (0.11516, 2)
    assert NSPB10__riders(record) == [0.00144, 0.00555, 0.0]
    assert not [x for x in record.components if x.component_type == "fixed"]
    assert "$22.00 minimum monthly bill" in record.notes and "less than 250 kVA or 225 kW" in record.eligibility
    assert "PDF pages 40, 41" in c["Demand Charge"].source_detail


def test_nspb10_medium_industrial_values_units_and_riders(NSPB10_industrial):
    record = NSPB10__parse(NSPB10_industrial)["22"]
    c = NSPB10__by_name(record)
    assert record.tariff_name == "Medium Industrial"
    assert c["Demand Charge"].charge_value == 10.71 and c["Demand Charge"].charge_unit == "$/kVA/month"
    assert c["Customer-Owned Transformer Demand Reduction"].sub_component == "conditional"
    assert (c["Energy Charge"].charge_value, c["Energy Charge"].charge_unit) == (0.10682, "$/kWh")
    assert NSPB10__riders(record) == [0.00206, 0.00479, 0.0]
    assert "250 kVA (225 kW) and over" in record.eligibility and "$22.00" in record.notes


def test_nspb10_large_industrial_firm_values_and_conditional_adder(NSPB10_industrial):
    record = NSPB10__parse(NSPB10_industrial)["23"]
    c = NSPB10__by_name(record)
    assert record.tariff_name == "Large Industrial - Firm"
    assert c["Demand Charge"].charge_value == 9.268
    adder = c["Distribution Cost Adder"]
    assert (adder.charge_value, adder.charge_unit, adder.sub_component) == (2.161, "$/kVA/month", "conditional")
    assert c["Energy Charge - Firm Customers"].charge_value == 0.10295
    assert "Interruptible Demand Credit" not in c
    assert NSPB10__riders(record) == [0.00247, 0.00663, 0.0]
    assert "greater of the demand charge or $22.00" in record.notes
    assert "2,000 kVA or 1,800 kW and over" in record.eligibility


def test_nspb10_interruptible_rider_record_is_conditional_and_uses_own_rows(NSPB10_industrial):
    record = NSPB10__parse(NSPB10_industrial)["25"]
    c = NSPB10__by_name(record)
    assert record.tariff_name == "Large Industrial - Interruptible Rider"
    assert c["Energy Charge - Interruptible Customers"].charge_value == 0.10334
    credit = c["Interruptible Demand Credit"]
    assert (credit.charge_value, credit.charge_unit, credit.sub_component) == (-7.638, "$/kVA/month", "conditional")
    assert "billed interruptible demand" in credit.notes
    assert NSPB10__riders(record) == [0.00224, 0.00663, 0.0]
    assert "10 minutes" in record.notes and "Penalties" in record.notes
    assert "Rate Code 25" in credit.source_detail and "PDF pages 44, 45, 46, 47, 48, 49" in credit.source_detail


def test_nspb10_2027_columns_are_never_used(NSPB10_industrial):
    values = {c.charge_value for record in NSPB10__parse(NSPB10_industrial).values() for c in record.components}
    assert not values & {8.143, 0.13795, 0.1128, 11.269, 0.09941, 10.006, 2.327, 0.09709, 0.09688, -7.667, 22.73}


def test_nspb10_prices_follow_source(NSPB10_industrial):
    NSPB10__edit(NSPB10_industrial, 40, "$7.496", "$7.600")
    NSPB10__edit(NSPB10_industrial, 42, "10.682", "10.900")
    NSPB10__edit(NSPB10_industrial, 44, "10.295 10.334", "10.300 10.400")
    NSPB10__edit(NSPB10_industrial, 47, "$7.638", "$7.700")
    records = NSPB10__parse(NSPB10_industrial)
    assert NSPB10__by_name(records["21"])["Demand Charge"].charge_value == 7.6
    assert NSPB10__by_name(records["22"])["Energy Charge"].charge_value == 0.109
    assert NSPB10__by_name(records["23"])["Energy Charge - Firm Customers"].charge_value == 0.103
    assert NSPB10__by_name(records["25"])["Energy Charge - Interruptible Customers"].charge_value == 0.104
    assert NSPB10__by_name(records["25"])["Interruptible Demand Credit"].charge_value == -7.7


@pytest.mark.parametrize(("page", "old", "new", "rejected"), [
    (40, "Rate Code 21", "Rate Code 99", {"21"}),
    (40, "32 cents per kilovolt", "40 cents per kilovolt", {"21"}),
    (41, "for industrial use", "for any use", {"21"}),
    (42, "$10.710", "-$10.710", {"22"}),
    (43, "reduced by 1.1%", "reduced by 1.5%", {"22"}),
    (44, "Firm Interruptible", "Firm", {"23", "25"}),
    (44, "For customers connected at distribution level", "For all customers", {"23", "25"}),
    (47, "within ten (10) minutes", "within thirty (30) minutes", {"25"}),
    (47, "$7.638", "", {"25"}),
    (67, "Large Industrial Interruptible 0.224 0.224", "Large Industrial Interruptible 0.224 0.300", {"25"}),
    (67, "Small Industrial 0.144 0.144", "Small Industrial 0.144 0.150", {"21"}),
    (76, "Medium Industrial 0.483 (0.004) 0.479", "Medium Industrial 0.483 (0.004) 0.999", {"22"}),
    (76, "Large Industrial including Interruptible Rider 0.612 0.051 0.663",
     "Large Industrial including Interruptible Rider 0.612 0.051 0.900", {"23", "25"}),
    (79, "Small Industrial 0.000", "Small Industrial", {"21"}),
])
def test_nspb10_one_class_fails_independently(NSPB10_industrial, page, old, new, rejected):
    NSPB10__edit(NSPB10_industrial, page, old, new)
    assert set(NSPB10__parse(NSPB10_industrial)) == NSPB10_ALL_CODES - rejected


@pytest.mark.parametrize(("drop", "rejected"), [
    ({41}, {"21"}), ({43}, {"22"}), ({48}, {"23", "25"}),
])
def test_nspb10_missing_continuation_page_rejects_only_that_class(NSPB10_industrial, drop, rejected):
    assert set(NSPB10__parse(NSPB10_industrial, drop=drop)) == NSPB10_ALL_CODES - rejected


def test_nspb10_negative_rider_value_is_read_as_credit(NSPB10_industrial):
    NSPB10__edit(NSPB10_industrial, 67, "Medium Industrial 0.206 0.206", "Medium Industrial (0.010) (0.010)")
    assert NSPB10__by_name(NSPB10__parse(NSPB10_industrial)["22"])["FAM Actual/Balance Adjustment (Combined)"].charge_value == -0.0001


def test_nspb10_unsupported_year_or_missing_book_date_fails_closed(NSPB10_industrial):
    assert NSPB10__parse(NSPB10_industrial, today="2027-01-01") == {}
    scraper = NSPB10_NovaScotiaPowerScraper()
    products = {k: v.replace("Rates updated as of May 1, 2026.", "") for k, v in NSPB10__products().items()}
    with patch.object(scraper, "now_iso", return_value=NSPB10_TODAY + "T00:00:00+00:00"):
        assert scraper._parse_industrial_tariffs(NSPB10__pages(NSPB10_industrial), products, NSPB10_industrial["source_url"]) == []


def test_nspb10_existing_business_classes_preserved_with_full_rider_pages(NSPB10_industrial):
    scraper = NSPB10_NovaScotiaPowerScraper()
    with patch.object(scraper, "now_iso", return_value=NSPB10_TODAY + "T00:00:00+00:00"):
        business = {r.tariff_code: r for r in scraper._parse_business_tariffs(NSPB10__pages(NSPB10_industrial), NSPB10__products(), NSPB10_industrial["source_url"])}
    assert set(business) == {"10", "11", "12"}
    assert NSPB10__riders(business["12"]) == [0.00158, 0.00458, 0.0]
    assert NSPB10__riders(business["11"]) == [0.00207, 0.00749, 0.0]


def test_nspb10_cached_book_adds_industrial_live_records_without_seeds(NSPB10_industrial):
    scraper = NSPB10_NovaScotiaPowerScraper()
    scraper._book = (NSPB10__pages(NSPB10_industrial), NSPB10__products(), NSPB10_industrial["source_url"])
    with patch.object(scraper, "now_iso", return_value=NSPB10_TODAY + "T00:00:00+00:00"),\
         patch.object(scraper, "_try_live_residential", return_value=[]),\
         patch.object(scraper, "fetch_page", side_effect=RuntimeError("offline")):
        records = scraper._try_live_scrape()
    by_code = {record.tariff_code: record for record in records}
    assert NSPB10_ALL_CODES | {"10", "11", "12"} <= set(by_code)
    for code in NSPB10_ALL_CODES:
        assert "live_parsed" in by_code[code].notes and "seed_fallback" not in by_code[code].notes


def test_nspb10_failed_industrial_class_has_no_seed_fallback(NSPB10_industrial):
    NSPB10__edit(NSPB10_industrial, 42, "Rate Code 22", "Rate Code 98")
    scraper = NSPB10_NovaScotiaPowerScraper()
    scraper._book = (NSPB10__pages(NSPB10_industrial), NSPB10__products(), NSPB10_industrial["source_url"])
    with patch.object(scraper, "now_iso", return_value=NSPB10_TODAY + "T00:00:00+00:00"),\
         patch.object(scraper, "_try_live_residential", return_value=[]),\
         patch.object(scraper, "fetch_page", side_effect=RuntimeError("offline")):
        records = scraper._try_live_scrape()
    codes = [record.tariff_code for record in records]
    assert "22" not in codes and {"21", "23", "25"} <= set(codes)


# ======================================================================
# FortisBC Energy Rate 7 and transportation 22/23/25/27 (batch 10)
# ======================================================================
from scrapers.utilities.fortisbc_energy import FortisBCEnergyScraper as FBEB10_FortisBCEnergyScraper
import json
from datetime import date
from pathlib import Path

import pytest


FBEB10_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "fortisbc_energy.json"
FBEB10_NEW_KEYS = ("rate7", "rate22", "rate23", "rate25", "rate27")
FBEB10_NAMES = {"rate7": "Industrial — Rate 7", "rate22": "Industrial — Rate 22 (Transportation)",
         "rate23": "Commercial — Rate 23 (Transportation)", "rate25": "Commercial — Rate 25 (Transportation)",
         "rate27": "Industrial — Rate 27 (Transportation)"}
FBEB10_EXISTING = {"Residential — Rate 1", "Residential — Rate 1 (Fort Nelson)", "Commercial — Rate 2",
            "Commercial — Rate 2 (Fort Nelson)", "Commercial — Rate 3", "Commercial — Rate 3 (Fort Nelson)",
            "Commercial — Rate 4", "Commercial — Rate 5"}


def FBEB10__document():
    return json.loads(FBEB10_FIXTURE.read_text(encoding="utf-8"))


def FBEB10__inputs(document):
    pages = {key: page["text"] for key, page in document["pages"].items()}
    pages["business_rate45"] += " " + document["business_rate7"]["text"]
    pages["tariffs"] = document["tariffs_transport"]["text"]
    urls = {key: document["pages"][key]["url"] for key in ("rate4", "rate5")}
    for key in FBEB10_NEW_KEYS:
        pages[key] = document[key]["text"]
        urls[key] = document[key]["url"]
    return pages, urls


def FBEB10__parse(pages, urls):
    return {r.tariff_name: r for r in FBEB10_FortisBCEnergyScraper().parse_pages(pages, date(2026, 10, 7), document_urls=urls)}


def FBEB10__records(document=None):
    return FBEB10__parse(*FBEB10__inputs(document or FBEB10__document()))


def FBEB10__values(record):
    return {c.component_name: (c.charge_value, c.charge_unit, c.sub_component) for c in record.components}


def test_fbeb10_all_classes_parse_with_existing_preserved():
    records = FBEB10__records()
    assert set(records) == FBEB10_EXISTING | set(FBEB10_NAMES.values())
    for record in records.values():
        for component in record.components:
            assert component.source_url and component.source_detail and component.effective_date


def test_fbeb10_existing_records_identical_with_and_without_new_documents():
    document = FBEB10__document()
    pages, urls = FBEB10__inputs(document)
    base_pages = {key: page["text"] for key, page in document["pages"].items()}
    base_urls = {key: document["pages"][key]["url"] for key in ("rate4", "rate5")}
    before = FBEB10__parse(base_pages, base_urls)
    after = FBEB10__parse(pages, urls)
    assert set(before) == FBEB10_EXISTING
    for name, record in before.items():
        assert after[name] == record


def test_fbeb10_rate7_source_values_units_and_dates():
    record = FBEB10__records()[FBEB10_NAMES["rate7"]]
    assert record.tariff_code == "Rate 7" and record.customer_class == "industrial"
    assert record.description == "General Interruptible Service" and record.effective_date == "2026-07-01"
    assert record.source_url == FBEB10__document()["rate7"]["url"]
    assert "written contract only" in record.eligibility and "alternative energy source" in record.eligibility
    assert "Unauthorized Overrun Gas" in record.notes and "Minimum monthly charge" in record.notes
    assert FBEB10__values(record) == {
        "Basic Charge": (880.00, "$/month", None),
        "Rider 2 (Clean Growth Innovation Fund Account)": (0.40, "$/month", None),
        "Delivery Charge": (2.199, "$/GJ", None),
        "Storage and Transport Charge": (0.784, "$/GJ", None),
        "Cost of Gas": (1.660, "$/GJ", None),
        "Rider 6 (Midstream Cost Reconciliation Account)": (0.126, "$/GJ", None),
        "Rider 8 (Storage and Transport RNG)": (0.909, "$/GJ", None),
        "BC Carbon Tax": (0.0, "$/GJ", None),
    }
    carbon = next(c for c in record.components if c.component_type == "carbon")
    assert carbon.effective_date == "2025-04-01"
    assert all(c.effective_date == "2026-07-01" for c in record.components if c is not carbon)
    assert "Order G-131-26" in record.source_page


def test_fbeb10_rate23_transport_values_and_rider5_page_date():
    record = FBEB10__records()[FBEB10_NAMES["rate23"]]
    assert record.customer_class == "commercial" and record.usage_min == 2000 and record.usage_unit == "GJ/year"
    assert record.effective_date == "2026-01-01"
    assert "licensed marketer" in record.eligibility and "institutional" in record.eligibility
    assert FBEB10__values(record) == {
        "Basic Charge": (132.08, "$/month", None),
        "Rider 2 (Clean Growth Innovation Fund Account)": (0.40, "$/month", None),
        "Administrative Charge": (39.00, "$/month", None),
        "Delivery Charge": (5.165, "$/GJ", None),
        "Rider 5 (Revenue Stabilization Adjustment Charge)": (0.212, "$/GJ", None),
        "BC Carbon Tax": (0.0, "$/GJ", None),
    }
    assert not any(c.component_type == "commodity" for c in record.components)
    assert "commodity price is private" in record.notes


def test_fbeb10_rate25_transport_demand_and_volume():
    record = FBEB10__records()[FBEB10_NAMES["rate25"]]
    assert record.customer_class == "commercial" and record.usage_min == 5000 and record.rate_structure == "demand"
    assert record.effective_date == "2026-01-01"
    values = FBEB10__values(record)
    assert values["Basic Charge"] == (469.00, "$/month", None)
    assert values["Demand Charge"] == (37.7352, "$/GJ/month of daily demand", None)
    assert values["Delivery Charge"] == (1.352, "$/GJ", None)
    assert values["Administrative Charge"] == (39.00, "$/month", None)
    assert len(values) == 6
    demand = next(c for c in record.components if c.component_type == "demand")
    assert demand.demand_unit == "GJ/day" and "1.10" in demand.notes


def test_fbeb10_rate27_interruptible_transport():
    record = FBEB10__records()[FBEB10_NAMES["rate27"]]
    assert record.customer_class == "industrial" and record.usage_min is None
    assert FBEB10__values(record) == {
        "Basic Charge": (880.00, "$/month", None),
        "Rider 2 (Clean Growth Innovation Fund Account)": (0.40, "$/month", None),
        "Administrative Charge": (39.00, "$/month", None),
        "Delivery Charge": (2.199, "$/GJ", None),
        "BC Carbon Tax": (0.0, "$/GJ", None),
    }


def test_fbeb10_rate22_conditional_firm_and_interruptible_parts():
    record = FBEB10__records()[FBEB10_NAMES["rate22"]]
    assert record.customer_class == "industrial" and "12,000 Gigajoules per Month" in record.eligibility
    assert "hospitals" in record.eligibility
    values = FBEB10__values(record)
    assert values["Basic Charge"] == (3664.00, "$/month", None)
    assert values["Administration Charge"] == (39.00, "$/month", None)
    assert values["Delivery Charge — Firm DTQ"] == (35.038, "$/GJ/month of Firm DTQ", "conditional")
    assert values["Delivery Charge — Firm MTQ"] == (0.203, "$/GJ", "conditional")
    assert values["Delivery Charge — Interruptible MTQ"] == (1.355, "$/GJ", "conditional")
    assert values["Demand Surcharge"] == (17.00, "$/GJ of Demand Surcharge Quantity", "conditional")
    dates = {c.component_name: c.effective_date for c in record.components}
    assert dates["Administration Charge"] == "2018-11-01" and dates["Basic Charge"] == "2026-01-01"
    assert record.effective_date == "2026-01-01"


@pytest.mark.parametrize(("key", "old", "new"), [
    ("rate7", "$ 2.199", "2.199"),
    ("rate7", "Subtotal of per Month Delivery Margin Related Charges $ 880.40",
     "Subtotal of per Month Delivery Margin Related Charges $ 881.40"),
    ("rate7", "Effective Date: July 1, 2026", "Effective Date: July 1, 2027"),
    ("rate7", "Rider 6 Midstream Cost Reconciliation Account", "Rider 6"),
    ("business_rate7", "Rate 7 is authorized by written contract only", "Rate 7 is open to all"),
    ("rate22", "Firm DTQ $ 35.038", "Firm DTQ 35.038"),
    ("rate22", "subject to a minimum of 12,000 Gigajoules per Month", "subject to no minimum"),
    ("rate22", "10. Administration Charge per Month $ 39.00", "10. Administration Charge per Month"),
    ("rate23", "9. Rider 5 per Gigajoule $ 0.212", "9. Rider 5 per Gigajoule"),
    ("rate23", "Subtotal of the Basic Charge and Rate Rider 2 per Month Related Charges $ 132.48",
     "Subtotal of the Basic Charge and Rate Rider 2 per Month Related Charges $ 133.48"),
    ("rate25", "Daily Demand is equal to 1.10", "Daily Demand is"),
    ("rate25", "Effective Date: January 1, 2026", "Effective Date: January 1, 2027"),
    ("rate27", "3. Delivery Charge per Gigajoule $ 2.199", "3. Delivery Charge per Gigajoule"),
    ("tariffs_transport", "Rate 27 Interruptible transportation", "Rate 27 Something else"),
])
def test_fbeb10_each_new_class_fails_closed_independently(key, old, new):
    document = FBEB10__document()
    target = document[key]
    assert old in target["text"]
    target["text"] = target["text"].replace(old, new)
    missing = FBEB10_NAMES["rate7" if key == "business_rate7" else
                    "rate27" if key == "tariffs_transport" else key]
    records = FBEB10__records(document)
    assert missing not in records
    assert set(records) == (FBEB10_EXISTING | set(FBEB10_NAMES.values())) - {missing}


def test_fbeb10_missing_document_rejects_only_that_class():
    document = FBEB10__document()
    pages, urls = FBEB10__inputs(document)
    del pages["rate25"]
    urls.pop("rate7")
    records = FBEB10__parse(pages, urls)
    assert set(records) == (FBEB10_EXISTING | set(FBEB10_NAMES.values())) - {FBEB10_NAMES["rate25"], FBEB10_NAMES["rate7"]}


def test_fbeb10_missing_tariff_index_rejects_transport_only():
    pages, urls = FBEB10__inputs(FBEB10__document())
    del pages["tariffs"]
    records = FBEB10__parse(pages, urls)
    assert set(records) == FBEB10_EXISTING | {FBEB10_NAMES["rate7"]}


def test_fbeb10_price_follows_source():
    document = FBEB10__document()
    document["rate7"]["text"] = document["rate7"]["text"].replace("$ 2.199", "$ 2.500", 1)
    document["rate25"]["text"] = document["rate25"]["text"].replace("$ 37.7352", "$ 40.0000", 1)
    records = FBEB10__records(document)
    assert FBEB10__values(records[FBEB10_NAMES["rate7"]])["Delivery Charge"][0] == 2.5
    assert FBEB10__values(records[FBEB10_NAMES["rate25"]])["Demand Charge"][0] == 40.0


def test_fbeb10_carbon_evidence_still_required():
    pages, urls = FBEB10__inputs(FBEB10__document())
    pages["carbon"] = "Carbon tax applies."
    assert FBEB10__parse(pages, urls) == {}


def test_fbeb10_discovery_finds_rate7_and_transport_links_only():
    business = ('<a href="https://x/gas-utility/rateschedule_7.pdf?sfvrsn=1">Rate 7</a>'
                '<a href="https://x/gas-utility/rateschedule_6.pdf">Rate 6</a>')
    index = ''.join(f'<a href="https://y/gas-utility/rateschedule_{n}.pdf">R</a>'
                    for n in ("22", "22a", "23", "25", "26", "27", "7"))
    found = FBEB10_FortisBCEnergyScraper._discover_documents(business, index)
    assert found == {"rate7": "https://x/gas-utility/rateschedule_7.pdf?sfvrsn=1",
                     "rate22": "https://y/gas-utility/rateschedule_22.pdf",
                     "rate23": "https://y/gas-utility/rateschedule_23.pdf",
                     "rate25": "https://y/gas-utility/rateschedule_25.pdf",
                     "rate27": "https://y/gas-utility/rateschedule_27.pdf"}


# ======================================================================
# SaskEnergy small industrial (batch 10)
# ======================================================================
from scrapers.utilities.saskenergy import PAGE_URLS as SEB10_PAGE_URLS, SaskEnergyScraper as SEB10_SaskEnergyScraper
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest


SEB10_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "saskenergy.json"
SEB10_TODAY = date(2026, 10, 7)


def SEB10__pages():
    document = json.loads(SEB10_FIXTURE.read_text(encoding="utf-8"))
    return {key: page["text"] for key, page in document["pages"].items()}


def SEB10__parse(pages):
    return {record.tariff_code: record for record in SEB10_SaskEnergyScraper().parse_pages(pages, SEB10_TODAY)}


def test_seb10_small_industrial_source_values():
    records = SEB10__parse(SEB10__pages())
    assert set(records) == {"Res", "SC", "LC", "SI", "Res-DS", "SC-DS", "LC-DS"}
    si = records["SI"]
    assert (si.customer_class, si.sub_class, si.tariff_name) == ("industrial", "small", "Small Industrial")
    assert (si.usage_min, si.usage_max, si.usage_unit) == (660001, 970000, "m³/year")
    assert si.rate_structure == "tiered"
    assert si.effective_date == "2025-04-01"
    assert "2022-09-08" in si.eligibility and "Closed class" in si.notes and "TransGas" in si.notes
    fixed = [c for c in si.components if c.component_type == "fixed"]
    assert [(c.charge_value, c.charge_unit) for c in fixed] == [(226.5, "$/month")]
    delivery = sorted((c for c in si.components if c.component_type == "delivery"), key=lambda c: c.tier_number)
    assert [(c.tier_number, c.charge_value, c.charge_unit, c.tier_threshold, c.tier_unit) for c in delivery] == [
        (1, 0.0507, "$/m³", 40000, "m³/month"), (2, 0.0446, "$/m³", 40000, "m³/month")]
    commodity = next(c for c in si.components if c.component_type == "commodity")
    assert (commodity.charge_value, commodity.charge_unit) == (0.1264, "$/m³")
    assert "$3.20/GJ" in commodity.notes
    carbon = next(c for c in si.components if c.component_type == "carbon")
    assert (carbon.charge_value, carbon.effective_date) == (0.0, "2025-04-01")
    assert "residential and commercial" in carbon.notes
    assert all(c.effective_date == "2023-10-01" for c in si.components if c.component_type != "carbon")
    assert all(c.source_url == SEB10_PAGE_URLS["business"] and c.source_detail for c in si.components if c.component_type != "carbon")


def test_seb10_small_industrial_has_no_delivery_only_variant():
    pages = SEB10__pages()
    records = SEB10__parse(pages)
    assert "SI-DS" not in records
    assert "Delivery Service" not in pages["business"].split("Small Industrial The following")[1]


@pytest.mark.parametrize(("old", "new"), [
    ("Remaining volumes : $0.0446 per m 3", "Remaining volumes : $0.0446 per GJ"),
    ("First 40,000 m 3 /month: $0.0507", "First 40,000 m 3 /month: $0.0000"),
    ("$226.50", "$-226.50"),
    ("As of September 8, 2022, this class is no longer accepting new customers.", ""),
    ("Small Industrial customers are not eligible to purchase gas from a Gas Retailer.", ""),
    ("660,001 to 970,000 m 3", "over 660,000 m 3"),
])
def test_seb10_small_industrial_drift_rejects_only_that_class(old, new):
    pages = SEB10__pages()
    assert old in pages["business"]
    pages["business"] = pages["business"].replace(old, new)
    records = SEB10__parse(pages)
    assert "SI" not in records
    assert {"Res", "SC", "LC", "Res-DS", "SC-DS", "LC-DS"} <= set(records)


def test_seb10_missing_small_industrial_section_preserves_existing_classes():
    pages = SEB10__pages()
    pages["business"] = pages["business"].split(" Small Industrial The following")[0]
    assert set(SEB10__parse(pages)) == {"Res", "SC", "LC", "Res-DS", "SC-DS", "LC-DS"}


def test_seb10_missing_business_page_keeps_residential_only():
    pages = SEB10__pages()
    pages.pop("business")
    assert set(SEB10__parse(pages)) == {"Res", "Res-DS"}


def test_seb10_missing_carbon_rejects_small_industrial():
    pages = SEB10__pages()
    pages["carbon"] = ""
    assert SEB10__parse(pages) == {}


def test_seb10_existing_classes_unchanged():
    records = SEB10__parse(SEB10__pages())
    for code, fixed, delivery in (("Res", 26.5, 0.1113), ("SC", 47.5, 0.0887), ("LC", 171.5, 0.0772)):
        comps = {c.component_type: c for c in records[code].components}
        assert (comps["fixed"].charge_value, comps["delivery"].charge_value, comps["commodity"].charge_value) == (fixed, delivery, 0.1264)
        assert records[code].rate_structure == "flat"
        assert "residential and commercial classes" not in comps["carbon"].notes
    assert (records["LC"].usage_min, records["LC"].usage_max) == (100001, 660000)


def test_seb10_scrape_marks_small_industrial_live():
    pages = SEB10__pages()
    scraper = SEB10_SaskEnergyScraper()
    responses = {SEB10_PAGE_URLS[key]: value for key, value in pages.items()}
    with patch.object(scraper, "fetch_page", side_effect=lambda url: responses[url]),\
            patch.object(SEB10_SaskEnergyScraper, "_page_text", staticmethod(lambda html: html)):
        records = {record.tariff_code: record for record in scraper.scrape()}
    assert "SI" in records and "live_parsed" in records["SI"].notes and "seed_fallback" not in records["SI"].notes


# ======================================================================
# Centra Gas class audit (batch 10)
# ======================================================================
from scrapers.utilities.centra_gas import CentraGasScraper as CGB10_CentraGasScraper
import json
import logging
from datetime import date
from pathlib import Path


CGB10_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "centra_gas.json"
CGB10_TODAY = date(2026, 10, 7)


def CGB10__pages():
    document = json.loads(CGB10_FIXTURE.read_text(encoding="utf-8"))
    return {key: page["text"] for key, page in document["pages"].items()}


def CGB10__parse(pages):
    scraper = CGB10_CentraGasScraper()
    records = scraper.parse_pages(pages, CGB10_TODAY)
    return scraper, {record.tariff_code: record for record in records}


def test_cgb10_official_class_list_is_fully_modelled_or_excluded():
    scraper, records = CGB10__parse(CGB10__pages())
    assert scraper.unmodelled_classes == []
    assert len(records) == 12
    assert not any("Special Contract" in r.tariff_name or "Power Station" in r.tariff_name for r in records.values())


def test_cgb10_exclusions_require_schedule_evidence(caplog):
    pages = CGB10__pages()
    pages["classes"] = pages["classes"].replace("electrical generating stations", "large customers")
    with caplog.at_level(logging.WARNING):
        scraper, records = CGB10__parse(pages)
    assert scraper.unmodelled_classes == ["Power Station Class"]
    assert "Power Station Class is not modelled" in caplog.text
    assert len(records) == 12


def test_cgb10_new_schedule_class_is_flagged_not_priced():
    pages = CGB10__pages()
    pages["classes"] = pages["classes"].replace(
        "Mainline Class, Special", "Mainline Class, Mainline Interruptible Class, Special")
    scraper, records = CGB10__parse(pages)
    assert scraper.unmodelled_classes == ["Mainline Interruptible Class"]
    assert len(records) == 12


def test_cgb10_missing_class_list_is_reported_without_dropping_classes():
    pages = CGB10__pages()
    pages.pop("classes")
    scraper, records = CGB10__parse(pages)
    assert scraper.unmodelled_classes == ["approved schedule class list"]
    assert len(records) == 12


def test_cgb10_new_commercial_option_is_flagged_not_priced():
    pages = CGB10__pages()
    pages["commercial"] = pages["commercial"].replace(
        "Small general service Small general service Small general service Charge Cost",
        "Mainline interruptible service – More than 680,000 m3 of natural gas used annually. "
        "Small general service Small general service Small general service Charge Cost", 1)
    scraper, records = CGB10__parse(pages)
    assert scraper.unmodelled_classes == ["Mainline interruptible service"]
    assert len(records) == 12


def test_cgb10_existing_classes_preserved_with_reconciled_parts():
    _, records = CGB10__parse(CGB10__pages())
    assert set(records) == {
        "SGS", "SGS-MKT", "COM-SGS", "COM-SGS-MKT", "COM-LGS", "COM-LGS-MKT",
        "COM-HVF-S", "COM-HVF-T", "COM-MFS-S", "COM-MFS-T", "COM-IS-S", "COM-IS-T"}
    interruptible = {c.component_name: c for c in records["COM-IS-S"].components}
    assert interruptible["Transportation to Centra"].charge_value == 0.0031
    assert interruptible["Distribution Charge"].charge_value == 0.0282
    assert "Delivery" not in interruptible
    assert interruptible["Alternate Supply Service"].charge_value == 0.0129
    assert all(r.effective_date == "2026-08-01" for r in records.values())


def test_cgb10_commercial_page_failure_rejects_only_commercial():
    pages = CGB10__pages()
    pages.pop("commercial")
    _, records = CGB10__parse(pages)
    assert set(records) == {"SGS", "SGS-MKT"}


# ======================================================================
# Maritime Electric 310-340 audit (batch 10)
# ======================================================================

import json
from pathlib import Path

import scrapers.utilities.maritime_electric as me
from scrapers.utils.parsing import DocumentPage

MEB10_FIXTURES = Path(__file__).resolve().parent / "fixtures"
MEB10_DOC = json.loads((MEB10_FIXTURES / "maritime_electric.json").read_text(encoding="utf-8"))
MEB10_URL = MEB10_DOC["url"]
MEB10_PAGE1 = next(p["text"] for p in MEB10_DOC["pages"] if p["page_number"] == 1)
MEB10_HTML = "\n".join(MEB10_DOC["rates_page"]["html_lines"])
MEB10_OTHERS = {"110", "130", "131", "133", "232", "233"}
MEB10_TARGET = {"310", "320", "330", "340"}


def MEB10_parse(html=MEB10_HTML, text=MEB10_PAGE1):
    scraper = me.MaritimeElectricScraper()
    records = scraper._apply_schedules(scraper._parse_pages([DocumentPage(1, text)], MEB10_URL), html)
    return {r.tariff_code: r for r in records}


def MEB10_comps(record):
    return {c.component_name: c for c in record.components}


def test_meb10_all_classes_with_schedule_html():
    assert set(MEB10_parse()) == MEB10_OTHERS | MEB10_TARGET


def test_meb10_small_industrial_320_complete():
    r = MEB10_parse()["320"]
    c = MEB10_comps(r)
    assert set(c) == {
        "Demand Charge - per kW",
        "Energy Charge per kWh for first 100 kWh per kW billing demand",
        "Energy Charge per kWh for balance of kWh",
    }
    demand = c["Demand Charge - per kW"]
    assert (demand.charge_value, demand.charge_unit, demand.demand_unit) == (7.46, "$/kW", "kW")
    assert "greatest of" in demand.notes and "90% of the monthly maximum kVA demand" in demand.notes and "5 kW" in demand.notes
    t1 = c["Energy Charge per kWh for first 100 kWh per kW billing demand"]
    assert (t1.charge_value, t1.tier_number, t1.tier_threshold, t1.tier_unit) == (0.2142, 1, 100.0, "kWh per kW billing demand")
    t2 = c["Energy Charge per kWh for balance of kWh"]
    assert (t2.charge_value, t2.tier_number, t2.tier_threshold) == (0.109, 2, None)
    assert r.customer_class == "industrial" and r.sub_class == "small industrial"
    assert r.demand_min_kw == 5.0 and r.demand_max_kw is None
    assert "750 kW and less than 3000 kW" in r.eligibility and "69 kV" in r.eligibility
    assert not any(x.component_type == "fixed" for x in r.components)


def test_meb10_large_industrial_310_complete_with_conditionals():
    r = MEB10_parse()["310"]
    c = MEB10_comps(r)
    assert set(c) == {
        "Demand Charge per kW", "Energy Charge per kWh",
        "Conditional Losses Adjustment - 69 kV to Primary Distribution Voltage",
        "Conditional Losses Adjustment - Primary to Utilization Voltage",
        "Conditional Transformation Charge (equivalent kVA rental)",
    }
    demand = c["Demand Charge per kW"]
    assert (demand.charge_value, demand.charge_unit, demand.demand_unit, demand.sub_component) == (14.5, "$/kW", "kW", None)
    for phrase in ("curtailable", "excluding April-November", "90% of maximum kVA demand", "no curtailable credit"):
        assert phrase in demand.notes
    assert c["Energy Charge per kWh"].charge_value == 0.092
    transformation = c["Conditional Transformation Charge (equivalent kVA rental)"]
    assert (transformation.charge_value, transformation.charge_unit, transformation.demand_unit) == (1.25, "$/kVA", "kVA")
    for name in ("Conditional Losses Adjustment - 69 kV to Primary Distribution Voltage",
                 "Conditional Losses Adjustment - Primary to Utilization Voltage"):
        assert (c[name].charge_value, c[name].charge_unit) == (1.5, "% added to monthly demand and energy")
    for x in (transformation, c["Conditional Losses Adjustment - Primary to Utilization Voltage"]):
        assert x.sub_component == "conditional" and x.notes.startswith("Conditional:")
        assert x.source_url == me.SOURCE_URL and "Large Industrial Rate Schedule" in x.source_detail
    assert "in addition" in c["Conditional Losses Adjustment - Primary to Utilization Voltage"].notes
    assert r.demand_min_kw == 750.0 and r.sub_class == "large industrial"
    assert "12 months' written notice" in r.eligibility and "69 kV" in r.eligibility
    assert "1 5/6% per month of installed cost" in r.notes


def test_meb10_wholesale_330_340_reference_only():
    recs = MEB10_parse()
    for code in ("330", "340"):
        r = recs[code]
        assert r.customer_class == "other" and r.sub_class == "wholesale (reference only)"
        assert "City of Summerside" in r.eligibility and "excluded from building scope" in r.notes
        assert "currently no customers" in r.notes
    assert "10 years" in recs["340"].eligibility and "1 year" in recs["330"].eligibility
    first = next(c for c in recs["330"].components if c.component_type == "energy" and c.tier_number == 1)
    assert first.charge_value == 0.1194 and first.tier_threshold is None and "1 April" in first.notes
    assert {c.charge_value for c in recs["340"].components} == {15.51, 0.1206}


def test_meb10_every_target_component_has_provenance():
    for code in MEB10_TARGET:
        for c in MEB10_parse()[code].components:
            assert c.effective_date == "2026-08-01" and c.source_url and c.source_detail
            if c.source_url == MEB10_URL:
                assert c.source_detail.startswith(f"PDF page 1, Rate {code}") and "cross-checked" in c.source_detail


def test_meb10_other_classes_unchanged_by_schedule_step():
    with_html, without = MEB10_parse(), MEB10_parse(html="")
    assert set(without) == MEB10_OTHERS
    for code in MEB10_OTHERS:
        assert [(c.component_name, c.charge_value) for c in with_html[code].components] ==\
               [(c.component_name, c.charge_value) for c in without[code].components]


def test_meb10_rates_page_date_mismatch_rejects_targets_only():
    recs = MEB10_parse(MEB10_HTML.replace("are effective August 1, 2026", "are effective May 1, 2026"))
    assert set(recs) == MEB10_OTHERS


def test_meb10_value_disagreement_rejects_only_that_class():
    assert set(MEB10_parse(MEB10_HTML.replace("$7.46 per kW", "$7.50 per kW"))) == MEB10_OTHERS | MEB10_TARGET - {"320"}
    assert set(MEB10_parse(text=MEB10_PAGE1.replace("Energy Charge per kWh $ 0.0920", "Energy Charge per kWh $ 0.0930"))) == MEB10_OTHERS | MEB10_TARGET - {"310"}
    assert set(MEB10_parse(MEB10_HTML.replace("9.94\u00a2", "9.95\u00a2"))) == MEB10_OTHERS | MEB10_TARGET - {"330"}


def test_meb10_new_published_charge_rejects_only_that_class():
    extra = MEB10_HTML.replace("<p>10.90\u00a2 per kWh for balance of kWh per month</p>",
                         "<p>10.90\u00a2 per kWh for balance of kWh per month</p><p>Service Charge: $30.00 per month</p>")
    assert set(MEB10_parse(extra)) == MEB10_OTHERS | MEB10_TARGET - {"320"}


def test_meb10_missing_billing_demand_or_condition_rejects_only_that_class():
    assert set(MEB10_parse(MEB10_HTML.replace("<li>5 kW.</li>", ""))) == MEB10_OTHERS | MEB10_TARGET - {"320"}
    assert set(MEB10_parse(MEB10_HTML.replace("100% of the total contracted amount for curtailable customers", "the contracted amount"))) == MEB10_OTHERS | MEB10_TARGET - {"310"}
    assert set(MEB10_parse(MEB10_HTML.replace("increased by 1 1/2% to compensate for transformation losses. This", "increased by 2% to compensate for transformation losses. This"))) == MEB10_OTHERS | MEB10_TARGET - {"310"}
    assert set(MEB10_parse(MEB10_HTML.replace("$1.25 per kVA", "$1.40 per kVA"))) == MEB10_OTHERS | MEB10_TARGET - {"310"}


def test_meb10_missing_or_duplicated_section_rejects_only_dependants():
    no_guide = MEB10_HTML.replace("<summary>Small Industrial Rate Application Guidelines</summary>", "<summary>Other</summary>")
    assert set(MEB10_parse(no_guide)) == MEB10_OTHERS | MEB10_TARGET - {"320"}
    dup = MEB10_HTML + "<details><summary>Large Industrial Rate Schedule</summary><p>x</p></details>"
    assert set(MEB10_parse(dup)) == MEB10_OTHERS | MEB10_TARGET - {"310"}
    no_wholesale = MEB10_HTML.replace("<summary>Wholesale Rate Schedule</summary>", "<summary>Other</summary>")
    assert set(MEB10_parse(no_wholesale)) == MEB10_OTHERS | {"310", "320"}


def test_meb10_wholesale_blocks_fail_independently():
    assert set(MEB10_parse(MEB10_HTML.replace("not less than 10 years", "not less than 5 years"))) == MEB10_OTHERS | MEB10_TARGET - {"340"}
    assert set(MEB10_parse(MEB10_HTML.replace("Set each year on 1 April", "Set by agreement"))) == MEB10_OTHERS | MEB10_TARGET - {"330"}


def test_meb10_scrape_live_path_uses_schedule_html(monkeypatch):
    scraper = me.MaritimeElectricScraper()
    landing = f'<html><a href="{MEB10_URL}">Schedule of Adjusted Rates Section N-28</a>{MEB10_HTML}</html>'
    monkeypatch.setattr(scraper, "fetch_page", lambda url, **k: landing)
    monkeypatch.setattr(scraper, "fetch_bytes", lambda url, **k: b"%PDF")
    monkeypatch.setattr(me, "_extract_pages", lambda b: [DocumentPage(1, MEB10_PAGE1)])
    live = scraper.scrape()
    assert {r.tariff_code for r in live} == MEB10_OTHERS | MEB10_TARGET
    assert all("Provenance: live_parsed" in r.notes for r in live)

    bare = f'<html><a href="{MEB10_URL}">Schedule of Adjusted Rates Section N-28</a></html>'
    monkeypatch.setattr(scraper, "fetch_page", lambda url, **k: bare)
    assert {r.tariff_code for r in scraper.scrape()} == MEB10_OTHERS


# ======================================================================
# NL Hydro industrial non-firm and wheeling audit (batch 10)
# ======================================================================
from scrapers.utilities.nl_hydro import NLHydroScraper as NLB10_NLHydroScraper
import copy
import json
from datetime import date
from pathlib import Path

from scrapers.utils.parsing import DocumentPage

NLB10_FIXTURES = Path(__file__).resolve().parent / "fixtures"
NLB10_TODAY = date(2026, 10, 7)


def NLB10__document():
    return json.loads((NLB10_FIXTURES / "nl_hydro.json").read_text(encoding="utf-8"))


def NLB10__parse(document):
    scraper = NLB10_NLHydroScraper()
    pages = [DocumentPage(**page) for page in
             document["pages"] + document["wp1_pages"] + document["b10_industrial_pages"]]
    records = scraper.parse_schedule_pages(pages, document["source_url"], today=NLB10_TODAY)
    return scraper, {record.tariff_code: record for record in records}


def NLB10__mutate(document, page_number, old, new):
    page = next(page for page in document["b10_industrial_pages"] if page["page_number"] == page_number)
    assert old in page["text"]
    page["text"] = page["text"].replace(old, new)
    return document


def test_nlb10_fixture_pages_are_official_non_firm_and_wheeling_excerpts():
    document = NLB10__document()
    assert document["source_url"].endswith("Schedule-of-Rates-Rules-and-Regulations_Jul_2026.pdf")
    pages = {page["page_number"]: page["text"] for page in document["b10_industrial_pages"]}
    assert sorted(pages) == [11, 12, 13]
    assert pages[11].rstrip().endswith("IND-3") and pages[12].rstrip().endswith("IND-4")
    assert pages[13].rstrip().endswith("IND-5")


def test_nlb10_non_firm_is_source_blocked_formula_gap_without_records():
    scraper, records = NLB10__parse(NLB10__document())
    reason = scraper.unmodelled_published["IND-NONFIRM"]
    assert reason.startswith("source-blocked")
    for term in ("Rate 2.4L", "NYISO Zone A", "ISO-NE Mass Hub", "583/475/556 kWh/bbl", "C = 3.34%"):
        assert term in reason
    assert not any("non-firm" in record.tariff_name.lower() for record in records.values())
    assert not any(code.startswith("IND-") and code != "IND-FIRM" for code in records)


def test_nlb10_wheeling_is_excluded_not_priced():
    scraper, records = NLB10__parse(NLB10__document())
    reason = scraper.excluded_published["IND-WHEELING"]
    assert "0.831 cents/kWh" in reason and "not a building energy supply tariff" in reason
    assert "IND-WHEELING" not in scraper.unmodelled_published
    assert not any("wheeling" in record.tariff_name.lower() for record in records.values())


def test_nlb10_existing_classes_are_preserved():
    document = NLB10__document()
    _, with_new = NLB10__parse(document)
    scraper = NLB10_NLHydroScraper()
    pages = [DocumentPage(**page) for page in document["pages"] + document["wp1_pages"]]
    baseline = {record.tariff_code: record for record in
                scraper.parse_schedule_pages(pages, document["source_url"], today=NLB10_TODAY)}
    assert len(with_new) == len(baseline) == 21
    assert set(with_new) == set(baseline)
    assert [(c.charge_value, c.charge_unit) for c in with_new["IND-FIRM"].components] ==\
        [(c.charge_value, c.charge_unit) for c in baseline["IND-FIRM"].components]
    assert "IND-NONFIRM" not in scraper.unmodelled_published
    assert scraper.excluded_published == {}


def test_nlb10_printed_non_firm_price_or_missing_formula_flags_review():
    for page_number, old, new in (
        (11, "Non-Thermal Generation Source (¢ per kWh)", "Non-Thermal Generation Source @ 9.999¢ per kWh"),
        (12, "conversion factor of 583 kWh/bbl", "conversion factor of unknown"),
        (11, "NYISO Zone A", "another market"),
    ):
        scraper, records = NLB10__parse(NLB10__mutate(NLB10__document(), page_number, old, new))
        assert "changed" in scraper.unmodelled_published["IND-NONFIRM"]
        assert len(records) == 21


def test_nlb10_missing_non_firm_continuation_is_isolated():
    document = NLB10__document()
    document["b10_industrial_pages"] = [p for p in document["b10_industrial_pages"] if p["page_number"] != 12]
    scraper, records = NLB10__parse(document)
    assert "incomplete" in scraper.unmodelled_published["IND-NONFIRM"]
    assert "IND-WHEELING" in scraper.excluded_published
    assert len(records) == 21 and "IND-FIRM" in records


def test_nlb10_wheeling_scope_change_flags_review_not_exclusion():
    document = NLB10__mutate(NLB10__document(), 13, "whose Industrial Service Agreement so provides", "any customer")
    scraper, records = NLB10__parse(document)
    assert "IND-WHEELING" not in scraper.excluded_published
    assert "changed" in scraper.unmodelled_published["IND-WHEELING"]
    assert len(records) == 21


def test_nlb10_future_dated_industrial_pages_are_not_audited_as_current():
    document = copy.deepcopy(NLB10__document())
    for page in document["b10_industrial_pages"]:
        page["text"] = page["text"].replace("Effective July 1, 2026", "Effective July 1, 2027")
    scraper, records = NLB10__parse(document)
    assert "incomplete" in scraper.unmodelled_published["IND-NONFIRM"]
    assert "incomplete" in scraper.unmodelled_published["IND-WHEELING"]
    assert scraper.excluded_published == {}
    assert len(records) == 21


# ======================================================================
# BC Hydro transmission pilots and generation credits (batch 10)
# ======================================================================
from scrapers.utilities.bc_hydro import BCHydroScraper as BCHB10_BCHydroScraper, TARIFF_URL as BCHB10_TARIFF_URL
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from scrapers.utils.parsing import DocumentPage
from scrapers.utils.validation import validate_batch
from pipeline.export_json import derive_provenance

BCHB10_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def BCHB10__pages():
    document = json.loads((BCHB10_FIXTURES / "bc_hydro_b10.json").read_text(encoding="utf-8"))
    return [DocumentPage(**page) for page in document["pages"]]


def BCHB10__mutate(pages, numbers, old, new):
    return [replace(page, text=page.text.replace(old, new)) if page.page_number in numbers else page for page in pages]


def BCHB10__by_code(records):
    return {record.tariff_code: record for record in records}


def BCHB10__values(record):
    return [(part.component_name, part.charge_value, part.charge_unit, part.sub_component) for part in record.components]


def test_bchb10_bch_b10_pilots_parse_all_four_with_source_values():
    records = BCHB10__by_code(BCHB10_BCHydroScraper()._parse_transmission_pilots(BCHB10__pages()))
    assert set(records) == {"2801", "2802", "2821", "2822"}
    riders = [("Rate Rider -- Deferral Account Rate Rider", -0.015, "fraction", None),
              ("Rate Rider -- Trade Income Rate Rider", 0.0, "fraction", None)]
    tou = [("Winter On-Peak Energy Charge", 0.17713, "$/kWh", None), ("Winter Off-Peak Energy Charge", 0.04096, "$/kWh", None),
           ("Spring Energy Charge", 0.04096, "$/kWh", None), ("Remaining Period Energy Charge", 0.04914, "$/kWh", None)]
    assert BCHB10__values(records["2801"]) == [("Billing Demand Charge", 11.79, "$/kVA/billing period", None)] + tou + riders
    assert BCHB10__values(records["2802"]) == [
        ("Winter On-Peak Billing Demand Charge", 10.37, "$/kVA/billing period", None),
        ("Winter Non-Peak Billing Demand Charge", 2.14, "$/kVA/billing period", None),
        ("Non-Winter Billing Demand Charge", 11.59, "$/kVA/billing period", None),
    ] + tou + riders
    assert BCHB10__values(records["2821"]) == [
        ("Billing Demand Charge", 10.164, "$/kVA/billing period", None),
        ("Critical Peak Pricing Energy Charge", 0.55354, "$/kWh", "conditional"),
        ("All Other Energy Charge", 0.04914, "$/kWh", None),
    ] + riders
    assert BCHB10__values(records["2822"]) == [
        ("Billing Demand Charge", 10.5, "$/kVA/billing period", None),
        ("Critical Peak Pricing Energy Charge", 0.55354, "$/kWh", "conditional"),
        ("Winter On-Peak Energy Charge", 0.13285, "$/kWh", None), ("Winter Off-Peak Energy Charge", 0.04448, "$/kWh", None),
        ("Spring Energy Charge", 0.04096, "$/kWh", None), ("Remaining Period Energy Charge", 0.04914, "$/kWh", None),
    ] + riders


def test_bchb10_bch_b10_pilots_are_conditional_dated_and_sourced():
    for record in BCHB10_BCHydroScraper()._parse_transmission_pilots(BCHB10__pages()):
        assert (record.customer_class, record.effective_date, record.end_date) == ("industrial", "2026-04-01", "2030-03-31")
        assert "conditional" in record.sub_class and "60 kV" in record.eligibility and "enrollment" in record.eligibility
        assert "not an adjustment" in record.notes and "bill guarantee" in record.notes
        assert all(part.source_url == BCHB10_TARIFF_URL and part.source_detail and part.effective_date for part in record.components)
    records = BCHB10__by_code(BCHB10_BCHydroScraper()._parse_transmission_pilots(BCHB10__pages()))
    assert records["2801"].source_page == "Electric Tariff RS 2801; PDF pages 187-193"
    assert records["2822"].source_page == "Electric Tariff RS 2822; PDF pages 209-216"
    assert "minimum" in records["2821"].notes.lower() and "minimum" not in records["2801"].notes.lower()
    seasons = {part.component_name: part.season for part in records["2802"].components}
    assert seasons["Non-Winter Billing Demand Charge"] == "non-winter" and seasons["Winter Non-Peak Billing Demand Charge"] == "winter"


def test_bchb10_bch_b10_missing_continuation_rejects_only_that_pilot():
    pages = [page for page in BCHB10__pages() if page.page_number != 198]
    assert set(BCHB10__by_code(BCHB10_BCHydroScraper()._parse_transmission_pilots(pages))) == {"2801", "2821", "2822"}


def test_bchb10_bch_b10_changed_unit_rejects_only_that_pilot():
    pages = BCHB10__mutate(BCHB10__pages(), {203}, "per kVA of Billing Demand per Billing Period", "per kW of Billing Demand per Billing Period")
    assert set(BCHB10__by_code(BCHB10_BCHydroScraper()._parse_transmission_pilots(pages))) == {"2801", "2802", "2822"}


def test_bchb10_bch_b10_changed_energy_period_rejects_pilot():
    pages = BCHB10__mutate(BCHB10__pages(), {210}, "3. Winter Off-Peak Period", "3. Shoulder Period")
    assert "2822" not in BCHB10__by_code(BCHB10_BCHydroScraper()._parse_transmission_pilots(pages))


def test_bchb10_bch_b10_missing_cpp_event_rule_rejects_cpp_pilots():
    pages = BCHB10__mutate(BCHB10__pages(), {206, 214}, "up to 15 Critical Peak", "up to 30 Critical Peak")
    assert set(BCHB10__by_code(BCHB10_BCHydroScraper()._parse_transmission_pilots(pages))) == {"2801", "2802"}


def test_bchb10_bch_b10_inconsistent_minimum_rejects_2821():
    pages = BCHB10__mutate(BCHB10__pages(), {203}, "Monthly Minimum Charge: $10.164", "Monthly Minimum Charge: $9.00")
    assert "2821" not in BCHB10__by_code(BCHB10_BCHydroScraper()._parse_transmission_pilots(pages))


def test_bchb10_bch_b10_future_date_or_missing_rider_fails_closed():
    future = BCHB10__mutate(BCHB10__pages(), set(range(187, 194)), "April 1, 2026", "April 1, 2027")
    assert "2801" not in BCHB10__by_code(BCHB10_BCHydroScraper()._parse_transmission_pilots(future))
    no_rider = [page for page in BCHB10__pages() if page.page_number != 232]
    assert BCHB10_BCHydroScraper()._parse_transmission_pilots(no_rider) == []


def test_bchb10_bch_b10_self_generation_credit_is_conditional_per_net_generation():
    records = BCHB10_BCHydroScraper()._parse_self_generation_tariff(BCHB10__pages())
    assert len(records) == 1
    record = records[0]
    assert (record.tariff_code, record.effective_date, record.customer_class) == ("2289", "2026-07-01", "other")
    assert BCHB10__values(record) == [("Conditional Net Generation Credit", -0.1, "$/kWh net generation", "conditional")]
    assert record.source_page == "Electric Tariff RS 2289; PDF pages 234-237"
    assert "not a replacement" in record.notes.lower() and "100 kW" in record.eligibility
    assert all(part.source_url == BCHB10_TARIFF_URL and part.effective_date for part in record.components)


def test_bchb10_bch_b10_self_generation_fails_closed():
    scraper = BCHB10_BCHydroScraper()
    assert scraper._parse_self_generation_tariff([page for page in BCHB10__pages() if page.page_number != 236]) == []
    assert scraper._parse_self_generation_tariff(BCHB10__mutate(BCHB10__pages(), {234}, "Energy Price of 10\u023c per kWh", "Energy Price of market value")) == []
    assert scraper._parse_self_generation_tariff(BCHB10__mutate(BCHB10__pages(), set(range(234, 238)), "July 1, 2026", "July 1, 2027")) == []


def test_bchb10_bch_b10_community_generation_credit_is_conditional_per_net_generation():
    records = BCHB10_BCHydroScraper()._parse_community_generation_tariff(BCHB10__pages())
    assert len(records) == 1
    record = records[0]
    assert (record.tariff_code, record.effective_date, record.customer_class) == ("2290", "2026-07-01", "other")
    assert BCHB10__values(record) == [("Conditional Community Generation Credit", -0.1, "$/kWh net generation", "conditional")]
    assert record.source_page == "Electric Tariff RS 2290; PDF pages 238-248"
    assert "not a replacement" in record.notes.lower() and "fee" in record.notes and "2 MW" in record.eligibility
    assert all(part.source_url == BCHB10_TARIFF_URL and part.effective_date for part in record.components)


def test_bchb10_bch_b10_community_generation_fails_closed():
    scraper = BCHB10_BCHydroScraper()
    assert scraper._parse_community_generation_tariff([page for page in BCHB10__pages() if page.page_number != 246]) == []
    assert scraper._parse_community_generation_tariff(BCHB10__mutate(BCHB10__pages(), {238}, "Community Energy Price of 10\u023c", "Community Energy Price of market")) == []
    assert scraper._parse_community_generation_tariff(BCHB10__mutate(BCHB10__pages(), {241}, "A 2 MW injection limit", "A 5 MW injection limit")) == []
    assert scraper._parse_community_generation_tariff(BCHB10__mutate(BCHB10__pages(), set(range(238, 249)), "July 1, 2026", "July 1, 2027")) == []
    assert len(scraper._parse_self_generation_tariff([page for page in BCHB10__pages() if page.page_number != 246])) == 1


def test_bchb10_bch_b10_full_scrape_preserves_existing_classes_and_adds_new_records():
    scraper = BCHB10_BCHydroScraper()
    business = json.loads((BCHB10_FIXTURES / "bc_hydro_business.json").read_text(encoding="utf-8"))
    residential = json.loads((BCHB10_FIXTURES / "bc_hydro_residential.json").read_text(encoding="utf-8"))
    pages = {page["page_number"]: DocumentPage(**page) for page in residential["pages"]}
    pages.update({page["page_number"]: DocumentPage(**page) for page in business["pages"]})
    pages.update({page.page_number: page for page in BCHB10__pages()})
    document = [DocumentPage(1, "BC Hydro Electric Tariff, Title Page\nEffective: April 1, 2025")] + [pages[n] for n in sorted(pages)]
    with patch.object(scraper, "fetch_page", return_value=""),\
         patch.object(scraper, "fetch_bytes", return_value=b"pdf"),\
         patch("scrapers.utilities.bc_hydro.extract_pdf_pages", return_value=document):
        records = scraper.scrape()
    valid, invalid = validate_batch(records)
    assert not invalid and len(valid) == 17
    codes = {record.tariff_code for record in valid}
    assert codes >= {"1101", "1151", "1300", "1500", "1600", "1830", "1289", "2801", "2802", "2821", "2822", "2289", "2290"}
    assert "1892" not in codes
    assert all(derive_provenance(record.confidence, record.notes) == "live" for record in valid)


def test_bchb10_bch_b10_existing_fixture_without_new_pages_is_unchanged():
    business = json.loads((BCHB10_FIXTURES / "bc_hydro_business.json").read_text(encoding="utf-8"))
    pages = [DocumentPage(**page) for page in business["pages"]]
    scraper = BCHB10_BCHydroScraper()
    assert scraper._parse_transmission_pilots(pages) == []
    assert scraper._parse_self_generation_tariff(pages) == []
    assert scraper._parse_community_generation_tariff(pages) == []
    assert len(scraper._parse_transmission_tariff(pages)) == 1


# ======================================================================
# Hydro-Quebec DR Commitment (batch 10)
# ======================================================================
from scrapers.utilities.hydro_quebec import HydroQuebecScraper as HQB10_HydroQuebecScraper
import json
from pathlib import Path

from scrapers.utils.parsing import DocumentPage

HQB10_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "hydro_quebec_domestic.json"


def HQB10__fixture():
    return json.loads(HQB10_FIXTURE.read_text(encoding="utf-8"))


def HQB10__commitment(removed=(), old=None, new=None):
    pages = HQB10__fixture()["dr_commitment_pages"]
    if old is not None:
        page = next(page for page in pages if old in page["text"])
        page["text"] = page["text"].replace(old, new)
    selected = [DocumentPage(**page) for page in pages if page["page_number"] not in removed]
    return HQB10_HydroQuebecScraper()._parse_dr_commitment(selected, "2026-04-01")


def test_hqb10_dr_commitment_source_metadata():
    source = HQB10__fixture()["dr_commitment_source"]
    assert source["url"] == "https://www.hydroquebec.com/data/documents-donnees/pdf/electricity-rates.pdf"
    assert source["physical_pdf_pages"].startswith("83-93")
    assert [page["page_number"] for page in HQB10__fixture()["dr_commitment_pages"]] == list(range(83, 94))


def test_hqb10_dr_commitment_conditional_credits():
    records = HQB10__commitment()
    assert len(records) == 1
    record = records[0]
    assert record.tariff_code == "DR_COMMITMENT_BUSINESS" and record.customer_class == "commercial"
    assert record.effective_date == "2026-04-01" and record.source_url.endswith("electricity-rates.pdf")
    assert "Rate G, M, L or LG" in record.eligibility and "load factor above 60%" in record.eligibility
    assert "no simultaneous Leeway Option" in record.eligibility
    assert "not replacement prices" in record.notes and "No bill total" in record.notes
    fixed = [c for c in record.components if c.component_name.startswith("Conditional Fixed Credit")]
    variable = [c for c in record.components if c.component_name.startswith("Conditional Variable Credit")]
    assert len(fixed) == len(variable) == 20
    assert fixed[0].component_name.endswith("(Sub-option I)") and fixed[-1].component_name.endswith("(Sub-option XX)")
    assert [c.charge_value for c in fixed][:5] == [-51.905, -53.981, -51.905, -53.981, -67.477]
    assert fixed[-1].charge_value == -75.781 and fixed[17].charge_value == -75.781
    assert {c.charge_value for c in variable} == {-0.05191, -0.36334}
    assert all(c.charge_unit == "$/kW of effective interruptible power/winter" and c.demand_unit == "kW" for c in fixed)
    assert all(c.charge_unit == "$/kWh of effective hourly interruptible power" for c in variable)
    assert all(c.source_detail == "Article 6.21; PDF page(s) 88-89" for c in fixed + variable)
    by_name = {c.component_name: c for c in record.components}
    assert by_name["Conditional Multi-Year Commitment Credit (2 consecutive winters)"].charge_value == 0.05
    assert by_name["Conditional Multi-Year Commitment Credit (3 consecutive winters)"].charge_value == 0.1
    assert by_name["Conditional Shorter-Notice Credit"].charge_value == -0.72667
    assert by_name["Conditional Shorter-Notice Credit"].source_detail == "Article 6.22 d); PDF page(s) 90"
    first = by_name["Conditional Overrun Deduction (first non-complied event)"]
    later = by_name["Conditional Overrun Deduction (subsequent non-complied events)"]
    assert (first.charge_value, later.charge_value) == (1.568, 4.474)
    assert "$6.281/kW" in first.notes and "$17.897/kW" in later.notes and "150%" in first.notes
    assert len(record.components) == 45
    assert all(c.sub_component == "conditional" and c.season_months == "12,1,2,3" and c.effective_date == "2026-04-01"
               and c.source_url == record.source_url for c in record.components)


def test_hqb10_dr_commitment_missing_page_fails_closed():
    for page in range(83, 94):
        assert not HQB10__commitment(removed=(page,)), page


def test_hqb10_dr_commitment_mutated_price_or_rule_fails_closed():
    assert not HQB10__commitment(old="Sub\u2011option X I V $73.705", new="Sub\u2011option X I V price not published")
    assert not HQB10__commitment(old="72.667\u00a2", new="price to be announced")
    assert not HQB10__commitment(old="a deduction of $4.474", new="a deduction")
    assert not HQB10__commitment(old="load factor that is higher than 60%", new="load factor to be determined")
    assert not HQB10__commitment(old="cannot exceed 150% of the total fixed credits", new="is uncapped")
    assert not HQB10__commitment(old="(hours): 100 100", new="(hours): to be set")


def test_hqb10_dr_commitment_does_not_affect_leeway_or_large_power():
    fixture = HQB10__fixture()
    scraper = HQB10_HydroQuebecScraper()
    leeway = scraper._parse_dr_leeway([DocumentPage(**page) for page in fixture["dr_leeway_pages"]], "2026-04-01")
    assert [record.tariff_code for record in leeway] == ["DR_LEEWAY_BUSINESS"]
    assert not scraper._parse_dr_commitment([DocumentPage(**page) for page in fixture["dr_leeway_pages"]], "2026-04-01")
    assert not scraper._parse_dr_leeway([DocumentPage(**page) for page in fixture["dr_commitment_pages"]], "2026-04-01")


# ======================================================================
# Manitoba Hydro LUBD (batch 10)
# ======================================================================
from scrapers.utilities.manitoba_hydro import COMMERCIAL_URL as MBB10_COMMERCIAL_URL, RESIDENTIAL_URL as MBB10_RESIDENTIAL_URL, SCHEDULE_URL as MBB10_SCHEDULE_URL, ManitobaHydroScraper as MBB10_ManitobaHydroScraper
import html
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.export_json import derive_provenance
from scrapers.base import BaseScraper
from scrapers.utils.parsing import DocumentPage

MBB10_FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures" / "manitoba_hydro.json").read_text(encoding="utf-8"))
MBB10_SCHEDULE = MBB10_FIXTURE["rate_schedule"]
MBB10_LUBD_NAMES = {
    "LUBD General Service Small (Single Phase)", "LUBD General Service Small (Three Phase)",
    "LUBD General Service Medium", "LUBD General Service Large (>750 V to 30 kV)",
    "LUBD General Service Large (>30 kV to 100 kV)", "LUBD General Service Large (>100 kV)",
}


def MBB10__pages(edit=None):
    pages = [DocumentPage(p["page_number"], p["text"]) for p in MBB10_SCHEDULE["pages"]]
    if edit:
        number, old, new = edit
        pages = [DocumentPage(p.page_number, p.text.replace(old, new) if p.page_number == number else p.text)
                 for p in pages]
        assert any(old in p["text"] for p in MBB10_SCHEDULE["pages"] if p["page_number"] == number), old
    return pages


def MBB10__parse(edit=None):
    return {r.tariff_name: r for r in MBB10_ManitobaHydroScraper()._parse_lubd(MBB10__pages(edit))}


def MBB10__comp(record, ctype):
    return [c for c in record.components if c.component_type == ctype]


def MBB10__html(page):
    return "<html><body>" + "".join(f"<p>{html.escape(ln)}</p>" for ln in MBB10_FIXTURE["pages"][page]["lines"]) + "</body></html>"


def test_mbb10_fixture_provenance():
    assert MBB10_SCHEDULE["url"] == MBB10_SCHEDULE_URL
    assert [p["page_number"] for p in MBB10_SCHEDULE["pages"]] == [1, 14, 15, 16]
    assert "APPROVED IN ORDER 1/26" in MBB10_SCHEDULE["pages"][0]["text"]


def test_mbb10_lubd_source_values():
    lubd = MBB10__parse()
    assert set(lubd) == MBB10_LUBD_NAMES
    small = lubd["LUBD General Service Small (Single Phase)"]
    assert small.tariff_code == "2026-50" and small.customer_class == "commercial"
    fixed, = MBB10__comp(small, "fixed")
    energy, = MBB10__comp(small, "energy")
    demand, = MBB10__comp(small, "demand")
    assert (fixed.charge_value, fixed.charge_unit) == (21.57, "$/month")
    assert (energy.charge_value, energy.charge_unit) == (pytest.approx(0.11831), "$/kWh")
    assert (demand.charge_value, demand.charge_unit, demand.demand_unit) == (3.06, "$/kVA", "kVA")
    assert "first 50 kVA" in demand.notes
    assert demand.demand_threshold_kw is None
    assert MBB10__comp(lubd["LUBD General Service Small (Three Phase)"], "fixed")[0].charge_value == 35.04
    medium = lubd["LUBD General Service Medium"]
    assert MBB10__comp(medium, "fixed")[0].charge_value == 35.81
    assert MBB10__comp(medium, "demand")[0].charge_value == 3.06
    assert "25% of contract demand" in medium.notes
    expected = {"53": (0.10466, 2.60), "54": (0.09083, 2.17), "55": (0.08418, 1.93)}
    for r in lubd.values():
        suffix = r.tariff_code.split("-")[1]
        if suffix in expected:
            assert r.customer_class == "industrial"
            assert not MBB10__comp(r, "fixed")
            assert MBB10__comp(r, "energy")[0].charge_value == pytest.approx(expected[suffix][0])
            assert MBB10__comp(r, "demand")[0].charge_value == pytest.approx(expected[suffix][1])


def test_mbb10_lubd_conditional_dates_and_sources():
    for r in MBB10__parse().values():
        assert r.notes.startswith("Conditional optional rate") and "replacing (not added to)" in r.notes
        assert "prior 12 months" in r.eligibility
        assert r.effective_date == "2026-01-01" and r.source_url == MBB10_SCHEDULE_URL
        for c in r.components:
            assert c.effective_date == "2026-01-01"
            assert c.source_url == MBB10_SCHEDULE_URL
            assert "Order 1/26" in c.source_detail and f"Tariff No. {r.tariff_code}" in c.source_detail
            assert "PDF page" in c.source_detail and "printed page" in c.source_detail


def test_mbb10_changed_unit_rejects_only_that_class():
    lubd = MBB10__parse((16, "@ $ 2.17 / kVA", "@ $ 2.17 / kW"))
    assert set(lubd) == MBB10_LUBD_NAMES - {"LUBD General Service Large (>30 kV to 100 kV)"}


def test_mbb10_missing_minimum_bill_rejects_only_medium():
    lubd = MBB10__parse((15, "Minimum Bill:\nDemand Charge PLUS Basic Charge", "Minimum Bill:"))
    assert set(lubd) == MBB10_LUBD_NAMES - {"LUBD General Service Medium"}


def test_mbb10_missing_eligibility_rejects_page_classes():
    lubd = MBB10__parse((14, "eligible for service on the General Service Small rate", "eligible for service"))
    assert set(lubd) == MBB10_LUBD_NAMES - {"LUBD General Service Small (Single Phase)", "LUBD General Service Small (Three Phase)"}


def test_mbb10_tariff_year_mismatch_rejected():
    lubd = MBB10__parse((16, "TARIFF NO. 2026-55", "TARIFF NO. 2025-55"))
    assert "LUBD General Service Large (>100 kV)" not in lubd
    assert len(lubd) == 5


def test_mbb10_missing_or_future_effective_date_rejects_all():
    assert MBB10__parse((1, "EFFECTIVE JANUARY 1, 2026", "EFFECTIVE")) == {}
    assert MBB10__parse((1, "APPROVED IN ORDER 1/26", "APPROVED")) == {}
    assert MBB10__parse((1, "JANUARY 1, 2026", "JANUARY 1, 2099")) == {}


def test_mbb10_scrape_adds_lubd_and_preserves_html_classes():
    pages = {MBB10_RESIDENTIAL_URL: MBB10__html("residential"), MBB10_COMMERCIAL_URL: MBB10__html("commercial")}
    with patch.object(BaseScraper, "fetch_page", lambda self, url, delay=1.0: pages[url]),\
            patch.object(BaseScraper, "fetch_bytes", lambda self, url, delay=1.0: b"%PDF"),\
            patch("scrapers.utilities.manitoba_hydro.extract_pdf_pages", lambda data: MBB10__pages()):
        records = MBB10_ManitobaHydroScraper().scrape()
    assert len(records) == 18
    assert MBB10_LUBD_NAMES <= {r.tariff_name for r in records}
    assert all(derive_provenance(r.confidence, r.notes) == "live" for r in records)


def test_mbb10_schedule_failure_keeps_twelve_html_classes():
    pages = {MBB10_RESIDENTIAL_URL: MBB10__html("residential"), MBB10_COMMERCIAL_URL: MBB10__html("commercial")}

    def fail(self, url, delay=1.0):
        raise ConnectionError("schedule unavailable")

    with patch.object(BaseScraper, "fetch_page", lambda self, url, delay=1.0: pages[url]),\
            patch.object(BaseScraper, "fetch_bytes", fail):
        records = MBB10_ManitobaHydroScraper().scrape()
    assert len(records) == 12
    assert not MBB10_LUBD_NAMES & {r.tariff_name for r in records}
    assert all(derive_provenance(r.confidence, r.notes) == "live" for r in records)


def test_mbb10_html_failure_keeps_lubd_and_labels_seeds():
    def fail(self, url, delay=1.0):
        raise ConnectionError("pages unavailable")

    with patch.object(BaseScraper, "fetch_page", fail),\
            patch.object(BaseScraper, "fetch_bytes", lambda self, url, delay=1.0: b"%PDF"),\
            patch("scrapers.utilities.manitoba_hydro.extract_pdf_pages", lambda data: MBB10__pages()):
        records = MBB10_ManitobaHydroScraper().scrape()
    live = {r.tariff_name for r in records if derive_provenance(r.confidence, r.notes) == "live"}
    seed = {r.tariff_name for r in records if derive_provenance(r.confidence, r.notes) == "seed"}
    assert live == MBB10_LUBD_NAMES
    assert "Residential Service" in seed and "General Service Medium" in seed


def test_mbb10_no_service_charge_or_net_billing_record():
    names = {r.tariff_name.lower() for r in MBB10__parse().values()}
    assert not any("fee" in n or "service charge" in n or "net billing" in n for n in names)
    assert "date_gap" in MBB10_FIXTURE["catalogue_review"]["service_charges"]
    assert "date_gap" in MBB10_FIXTURE["catalogue_review"]["net_billing"]


# ======================================================================
# NTPC live schedule (batch 10)
# ======================================================================
from scrapers.utilities.ntpc import DIESEL_RESIDENTIAL_NAME as NTPCB10_DIESEL_RESIDENTIAL_NAME, NTPCScraper as NTPCB10_NTPCScraper, build_records as NTPCB10_build_records, parse_residential_page as NTPCB10_parse_residential_page, parse_rider_page as NTPCB10_parse_rider_page, parse_schedule as NTPCB10_parse_schedule, parse_schedule_index as NTPCB10_parse_schedule_index, parse_tpsp as NTPCB10_parse_tpsp
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scrapers.utilities import ntpc
from scrapers.utils.parsing import DocumentPage

NTPCB10_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ntpc.json"
NTPCB10_TODAY = "2026-10-07"
NTPCB10_TPSP_PREFIX = "GNWT TPSP Subsidised First-Block Energy Price"
NTPCB10_PDF_URL = "https://www.ntpc.com/sites/default/files/2026-06/NTPC%20Rate%20Schedule%20-%20June%201%202026.pdf"


def NTPCB10__fx():
    return json.loads(NTPCB10_FIXTURE.read_text(encoding="utf-8"))


def NTPCB10__pages(fx, edit=None):
    pages = [DocumentPage(p["page"], p["text"]) for p in fx["schedule"]["pages"]]
    return [DocumentPage(p.page_number, edit(p.page_number, p.text)) for p in pages] if edit else pages


def NTPCB10__records(fx=None, edit=None, residential=None):
    fx = fx or NTPCB10__fx()
    schedule = NTPCB10_parse_schedule(NTPCB10__pages(fx, edit), NTPCB10_PDF_URL, NTPCB10_TODAY)
    page = NTPCB10_parse_residential_page(residential or fx["residential"]["html"], NTPCB10_TODAY)
    return {r.tariff_name: r for r in NTPCB10_build_records(schedule, page, NTPCB10_parse_tpsp(fx["tpsp"]["html"]),
                                                     NTPCB10_parse_rider_page(fx["riders"]["html"]))}


def NTPCB10__comp(record, name):
    (component,) = [c for c in record.components if c.component_name == name]
    return component


def test_ntpcb10_fixture_sources():
    fx = NTPCB10__fx()
    assert fx["retrieved"] == "2026-10-07"
    assert fx["residential"]["url"] == ntpc.RESIDENTIAL_URL and fx["schedule_index"]["url"] == ntpc.SCHEDULE_INDEX_URL
    assert fx["tpsp"]["url"] == ntpc.TPSP_URL and fx["riders"]["url"] == ntpc.RIDER_URL
    assert fx["schedule"]["url"] == NTPCB10_PDF_URL
    assert [p["page"] for p in fx["schedule"]["pages"]] == list(range(3, 14))


def test_ntpcb10_schedule_index_current_link():
    assert NTPCB10_parse_schedule_index(NTPCB10__fx()["schedule_index"]["html"], NTPCB10_TODAY) == (NTPCB10_PDF_URL, "2026-06-01")
    with pytest.raises(ntpc._Reject):
        NTPCB10_parse_schedule_index(NTPCB10__fx()["schedule_index"]["html"], "2026-05-31")


def test_ntpcb10_record_inventory():
    records = NTPCB10__records()
    assert len(records) == 62
    non_government = {
        "Residential Service — Snare Zone", NTPCB10_DIESEL_RESIDENTIAL_NAME, "Residential Service — Norman Wells Zone",
        "Residential Service — Taltson Zone (Hay River)", "Residential Service — Taltson Zone (Fort Smith/Fort Resolution)",
        "General Service — Snare Zone", "General Service — Thermal Zone", "General Service — Norman Wells Zone",
        "General Service — Taltson Zone (Hay River)", "General Service — Taltson Zone (Fort Smith/Fort Resolution)",
    }
    assert non_government <= set(records)
    assert sum("Government —" in name for name in records) == 52
    for record in records.values():
        assert record.province == "NT" and record.source_url == NTPCB10_PDF_URL
        assert all(c.source_url and c.source_detail and c.effective_date for c in record.components)
        assert not any(word in record.tariff_name.lower() for word in ("light", "wholesale", "stand", "interruptible"))
        assert not any("stand" in c.component_name.lower() for c in record.components)


def test_ntpcb10_thermal_residential_values_and_subsidies():
    record = NTPCB10__records()[NTPCB10_DIESEL_RESIDENTIAL_NAME]
    assert record.customer_class == "residential" and record.effective_date == "2026-09-01"
    assert (NTPCB10__comp(record, "Monthly Service Charge").charge_value, NTPCB10__comp(record, "Monthly Service Charge").charge_unit) == (18.0, "$/month")
    assert NTPCB10__comp(record, "Energy Charge").charge_value == 0.8896
    assert NTPCB10__comp(record, "Energy Charge").effective_date == "2026-06-01"
    assert NTPCB10__comp(record, "NWT Stabilization Fund Rate Rider").charge_value == 0.0101
    assert NTPCB10__comp(record, "GRA Shortfall Rider").charge_value == 0.0772
    assert NTPCB10__comp(record, "Sunk Cost Deferral Account Rider").charge_value == 0.0042
    col = NTPCB10__comp(record, "GNWT Cost of Living Subsidy")
    assert (col.component_type, col.charge_value, col.effective_date) == ("rebate", -0.1343, "2026-09-01")
    assert "March 2028" in col.notes and "residential and commercial" in col.notes
    winter = NTPCB10__comp(record, f"{NTPCB10_TPSP_PREFIX} (September 1 to March 31)")
    summer = NTPCB10__comp(record, f"{NTPCB10_TPSP_PREFIX} (April 1 to August 31)")
    assert (winter.charge_value, winter.tier_threshold, winter.season_months) == (0.365, 1000, "9,10,11,12,1,2,3")
    assert (summer.charge_value, summer.tier_threshold, summer.season_months) == (0.365, 600, "4,5,6,7,8")
    assert winter.component_type == "energy" and "Conditional alternative" in winter.notes
    assert "Minimum Monthly Bill: $18.00" in record.notes
    assert not any("total" in c.component_name.lower() for c in record.components)


def test_ntpcb10_snare_tpsp_saving_mismatch_is_not_stored():
    record = NTPCB10__records()["Residential Service — Snare Zone"]
    assert not [c for c in record.components if c.component_type == "rebate"]
    assert not [c for c in record.components if c.component_name.startswith(NTPCB10_TPSP_PREFIX)]
    assert "do not reconcile" in record.notes
    assert NTPCB10__comp(record, "GRA Shortfall Rider").charge_value == -0.0033


def test_ntpcb10_taltson_community_rider_rules():
    records = NTPCB10__records()
    hay = records["Residential Service — Taltson Zone (Hay River)"]
    smith = records["Residential Service — Taltson Zone (Fort Smith/Fort Resolution)"]
    names = lambda r: {c.component_name for c in r.components}
    assert "Misc. Deferral Transfers Rider" in names(hay) and "NWT Stabilization Fund Rate Rider" not in names(hay)
    assert "Misc. Deferral Transfers Rider" not in names(smith) and "NWT Stabilization Fund Rate Rider" in names(smith)
    assert NTPCB10__comp(hay, "GNWT Cost of Living Subsidy").charge_value == -0.1353
    assert NTPCB10__comp(smith, "GNWT Cost of Living Subsidy").charge_value == -0.1318
    assert NTPCB10__comp(hay, "Energy Charge").charge_value == 0.3242
    gov = records["General Service Government — Hay River (Taltson Zone)"]
    assert NTPCB10__comp(gov, "Energy Charge").charge_value == 0.3369 and "Misc. Deferral Transfers Rider" in names(gov)


def test_ntpcb10_general_service_and_government():
    records = NTPCB10__records()
    gs = records["General Service — Thermal Zone"]
    demand = NTPCB10__comp(gs, "Demand Charge")
    assert (demand.charge_value, demand.charge_unit, demand.demand_unit) == (8.0, "$/kW", "kW")
    assert "12 month period" in demand.notes and gs.rate_structure == "demand"
    assert NTPCB10__comp(gs, "Energy Charge").charge_value == 0.7631 and "Minimum Monthly Bill: $40.00" in gs.notes
    assert not [c for c in gs.components if c.component_type in ("rebate", "fixed")]
    gov = records["Residential Service Government — Colville Lake (Thermal Zone)"]
    assert NTPCB10__comp(gov, "Energy Charge").charge_value == 4.1956
    assert not [c for c in gov.components if c.component_type == "rebate"]


def test_ntpcb10_mutated_value_flows_through_and_page_mismatch_drops_subsidies():
    records = NTPCB10__records(edit=lambda n, t: t.replace("Energy Charge: 88.96", "Energy Charge: 90.00") if n == 6 else t)
    record = records[NTPCB10_DIESEL_RESIDENTIAL_NAME]
    assert NTPCB10__comp(record, "Energy Charge").charge_value == 0.9
    assert not [c for c in record.components if c.component_type == "rebate"]
    assert not [c for c in record.components if c.component_name.startswith(NTPCB10_TPSP_PREFIX)]
    assert "does not match" in record.notes


def test_ntpcb10_unrecognised_charge_rejects_only_that_block():
    records = NTPCB10__records(edit=lambda n, t: t.replace("Minimum Monthly Bill: $18.00\nNWT", "Mystery Fee: $3.00\nMinimum Monthly Bill: $18.00\nNWT") if n == 6 else t)
    assert NTPCB10_DIESEL_RESIDENTIAL_NAME not in records
    assert "General Service — Thermal Zone" in records and len(records) == 61


def test_ntpcb10_missing_rider_rejects_block():
    records = NTPCB10__records(edit=lambda n, t: t.replace("GRA Shortfall Rider: 7.72 ¢/kWh", "") if n == 8 else t)
    assert "General Service — Thermal Zone" not in records


def test_ntpcb10_missing_taltson_applicability_notes_reject_taltson():
    edit = lambda n, t: t.replace("does not apply to Hay River", "is under review")
    records = NTPCB10__records(edit=edit)
    assert not any("Taltson" in name for name in records) and len(records) == 62 - 10


def test_ntpcb10_conflicting_or_future_dates_fail_closed():
    with pytest.raises(ntpc._Reject):
        NTPCB10_parse_schedule(NTPCB10__pages(NTPCB10__fx(), lambda n, t: t.replace("June 1, 2026", "July 1, 2026") if n == 5 else t), NTPCB10_PDF_URL, NTPCB10_TODAY)
    with pytest.raises(ntpc._Reject):
        NTPCB10_parse_schedule(NTPCB10__pages(NTPCB10__fx()), NTPCB10_PDF_URL, "2026-05-31")
    with pytest.raises(ntpc._Reject):
        NTPCB10_parse_residential_page(NTPCB10__fx()["residential"]["html"], "2026-08-31")


def test_ntpcb10_scraper_live_path_is_labelled_live():
    fx = NTPCB10__fx()
    html = {ntpc.SCHEDULE_INDEX_URL: fx["schedule_index"]["html"], ntpc.RESIDENTIAL_URL: fx["residential"]["html"],
            ntpc.TPSP_URL: fx["tpsp"]["html"], ntpc.RIDER_URL: fx["riders"]["html"]}
    with patch.object(NTPCB10_NTPCScraper, "fetch_page", lambda self, url, delay=1.0: html[url]),\
            patch.object(NTPCB10_NTPCScraper, "fetch_bytes", lambda self, url, delay=1.0: b"%PDF"),\
            patch.object(NTPCB10_NTPCScraper, "now_iso", lambda self: NTPCB10_TODAY + "T00:00:00+00:00"),\
            patch.object(ntpc, "extract_pdf_pages", lambda data: NTPCB10__pages(fx)):
        records = NTPCB10_NTPCScraper().scrape()
    assert len(records) == 62
    assert all(r.notes.startswith("Provenance: live_parsed") and r.confidence == "high" for r in records)
    assert not any("Yellowknife" in r.tariff_name for r in records)


def test_ntpcb10_rider_page_failure_keeps_base_records_without_col():
    fx = NTPCB10__fx()
    html = {ntpc.SCHEDULE_INDEX_URL: fx["schedule_index"]["html"], ntpc.RESIDENTIAL_URL: fx["residential"]["html"],
            ntpc.TPSP_URL: fx["tpsp"]["html"]}

    def fetch(self, url, delay=1.0):
        if url not in html:
            raise ConnectionError("blocked")
        return html[url]

    with patch.object(NTPCB10_NTPCScraper, "fetch_page", fetch),\
            patch.object(NTPCB10_NTPCScraper, "fetch_bytes", lambda self, url, delay=1.0: b"%PDF"),\
            patch.object(NTPCB10_NTPCScraper, "now_iso", lambda self: NTPCB10_TODAY + "T00:00:00+00:00"),\
            patch.object(ntpc, "extract_pdf_pages", lambda data: NTPCB10__pages(fx)):
        records = {r.tariff_name: r for r in NTPCB10_NTPCScraper().scrape()}
    names = {c.component_name for c in records[NTPCB10_DIESEL_RESIDENTIAL_NAME].components}
    assert "GNWT Cost of Living Subsidy" not in names
    assert f"{NTPCB10_TPSP_PREFIX} (September 1 to March 31)" in names


def test_ntpcb10_thermal_failure_adds_labelled_diesel_seed_only():
    fx = NTPCB10__fx()
    html = {ntpc.SCHEDULE_INDEX_URL: fx["schedule_index"]["html"], ntpc.RESIDENTIAL_URL: fx["residential"]["html"],
            ntpc.TPSP_URL: fx["tpsp"]["html"], ntpc.RIDER_URL: fx["riders"]["html"]}
    pages = NTPCB10__pages(fx, lambda n, t: t.replace("Energy Charge: 88.96 ¢/kWh", "") if n == 6 else t)
    with patch.object(NTPCB10_NTPCScraper, "fetch_page", lambda self, url, delay=1.0: html[url]),\
            patch.object(NTPCB10_NTPCScraper, "fetch_bytes", lambda self, url, delay=1.0: b"%PDF"),\
            patch.object(NTPCB10_NTPCScraper, "now_iso", lambda self: NTPCB10_TODAY + "T00:00:00+00:00"),\
            patch.object(ntpc, "extract_pdf_pages", lambda data: pages):
        records = NTPCB10_NTPCScraper().scrape()
    seeds = [r for r in records if r.confidence == "unverified"]
    assert [r.tariff_name for r in seeds] == [NTPCB10_DIESEL_RESIDENTIAL_NAME]
    assert "Provenance: seed_fallback" in seeds[0].notes
    assert all(c.confidence == "unverified" for c in seeds[0].components)
    assert len(records) == 62


def test_ntpcb10_total_failure_falls_back_to_labelled_seeds():
    with patch.object(NTPCB10_NTPCScraper, "fetch_page", side_effect=ConnectionError("offline")):
        records = NTPCB10_NTPCScraper().scrape()
    assert len(records) == 3
    assert all(r.confidence == "unverified" and "Provenance: seed_fallback" in r.notes for r in records)


# ======================================================================
# Qulliq Energy live rates (batch 10)
# ======================================================================
from scrapers.utilities.qulliq import PAGE_URLS as QECB10_PAGE_URLS, QulliqScraper as QECB10_QulliqScraper
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest


QECB10_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "qulliq.json"
QECB10_TODAY = date(2026, 10, 7)


def QECB10__pages():
    document = json.loads(QECB10_FIXTURE.read_text(encoding="utf-8"))
    return {key: page["text"] for key, page in document["pages"].items()}


def QECB10__parse(pages, today=QECB10_TODAY):
    return {r.tariff_code: r for r in QECB10_QulliqScraper().parse_pages(pages, today)}


def QECB10__comps(record, kind):
    return [c for c in record.components if c.component_type == kind]


def test_qecb10_fixture_has_sources():
    document = json.loads(QECB10_FIXTURE.read_text(encoding="utf-8"))
    for key, page in document["pages"].items():
        assert page["url"] == QECB10_PAGE_URLS[key] and page["retrieved"] == "2026-10-07"


def test_qecb10_all_building_classes_parsed():
    records = QECB10__parse(QECB10__pages())
    assert set(records) == {"NG-RES", "G-RES", "MT-RES", "NG-COM", "G-COM", "MT-COM"}
    assert records["NG-RES"].tariff_name == "Residential Service"
    assert records["NG-COM"].tariff_name == "Commercial Service"
    for r in records.values():
        assert r.effective_date == "2025-04-01" and r.province == "NU"
        assert "interim" in r.notes and "October 1, 2023" in r.notes
        assert all(c.source_url and c.source_detail and c.effective_date == "2025-04-01" for c in r.components)
        assert not any("treet" in r.tariff_name or "tandby" in r.tariff_name for r in records.values())


def test_qecb10_energy_and_fixed_values():
    records = QECB10__parse(QECB10__pages())
    expected = {"NG-RES": 0.7494, "G-RES": 1.13, "MT-RES": 0.7494, "NG-COM": 0.6208, "G-COM": 1.0533, "MT-COM": 0.6208}
    for code, value in expected.items():
        (energy,) = QECB10__comps(records[code], "energy")
        assert (energy.charge_value, energy.charge_unit) == (value, "$/kWh")
    for code in ("NG-RES", "G-RES", "MT-RES"):
        (fixed,) = QECB10__comps(records[code], "fixed")
        assert (fixed.charge_value, fixed.charge_unit) == (36.0, "$/month")
    (demand,) = QECB10__comps(records["NG-COM"], "demand")
    assert (demand.charge_value, demand.charge_unit) == (16.0, "$/kW/month")
    assert records["NG-COM"].rate_structure == "demand"
    for code in ("G-COM", "MT-COM"):
        assert not QECB10__comps(records[code], "demand") and not QECB10__comps(records[code], "fixed")
        assert "no " in records[code].notes and "value is shown" in records[code].notes


def test_qecb10_nesp_is_conditional_allowance_without_price():
    records = QECB10__parse(QECB10__pages())
    rebates = QECB10__comps(records["NG-RES"], "rebate")
    assert [(c.season, c.tier_threshold, c.charge_value, c.sub_component) for c in rebates] == [
        ("summer", 700, None, "conditional"), ("winter", 1000, None, "conditional")]
    assert all("one residence" in c.notes for c in rebates)
    for code in ("G-RES", "MT-RES", "NG-COM", "G-COM", "MT-COM"):
        assert not QECB10__comps(records[code], "rebate")


def test_qecb10_fsr_rider_is_note_without_value():
    records = QECB10__parse(QECB10__pages())
    for r in records.values():
        assert "latest posted FSR application (March 2026) is a request" in r.notes
        assert not [c for c in r.components if c.component_type == "rider"]


def test_qecb10_public_housing_is_note_not_rate():
    g = QECB10__parse(QECB10__pages())["G-RES"]
    assert "6 cents/kWh" in g.notes
    assert all(c.charge_value != 0.06 for c in g.components)


@pytest.mark.parametrize(("key", "old", "new", "rejected"), [
    ("rates", "74.94 cents/kWh Non-Government", "79.00 cents/kWh Non-Government", {"NG-RES"}),
    ("rates", "113.00 cents/kWh", "120.00 cents/kWh", {"G-RES"}),
    ("rates", "Commercial - 62.08 cents/kWh", "Commercial - 65.00 cents/kWh", {"MT-COM"}),
    ("interim", "$1.0221 to $1.1300 per kWh", "$1.0221 to $1.2000 per kWh", {"G-RES"}),
    ("rates", "700 kWh for each 30-day period", "700 kW for each 30-day period", {"NG-RES"}),
    ("rates", "tenant is billed directly for 6 cents/kWh", "tenant is billed directly", {"G-RES"}),
])
def test_qecb10_value_drift_rejects_only_that_class(key, old, new, rejected):
    pages = QECB10__pages()
    assert old in pages[key]
    pages[key] = pages[key].replace(old, new, 1)
    records = QECB10__parse(pages)
    assert set(records) == {"NG-RES", "G-RES", "MT-RES", "NG-COM", "G-COM", "MT-COM"} - rejected


@pytest.mark.parametrize(("key", "old", "new"), [
    ("interim", "From $18 to $36 per month", "From $18 to per month"),
    ("interim", "From $8 to $16 per kW", "From $8 to $16 per kWh"),
    ("interim", "interim rates will remain in place until final rates are approved", "rates are final"),
    ("rates", "effective as of October 1, 2023", "effective as of April 1, 2026"),
    ("gra", "effective April 1, 2025", "effective April 1, 2027"),
    ("interim", "effective April 1, 2025. QEC", "effective April 1, 2027. QEC"),
])
def test_qecb10_stale_or_structural_drift_fails_closed(key, old, new):
    pages = QECB10__pages()
    assert old in pages[key]
    pages[key] = pages[key].replace(old, new, 1)
    assert QECB10__parse(pages) == {}


@pytest.mark.parametrize("missing", ["rates", "interim", "gra"])
def test_qecb10_missing_required_page_fails_closed(missing):
    pages = QECB10__pages()
    pages.pop(missing)
    assert QECB10__parse(pages) == {}


def test_qecb10_future_interim_date_rejected():
    assert QECB10__parse(QECB10__pages(), today=date(2025, 3, 31)) == {}


def test_qecb10_scrape_marks_live():
    pages = QECB10__pages()
    scraper = QECB10_QulliqScraper()
    responses = {QECB10_PAGE_URLS[k]: v for k, v in pages.items()}
    with patch.object(scraper, "fetch_page", side_effect=lambda url: responses[url]),\
            patch.object(QECB10_QulliqScraper, "_page_text", staticmethod(lambda html: html)):
        records = scraper.scrape()
    assert len(records) == 6
    assert all("live_parsed" in r.notes and "seed_fallback" not in r.notes for r in records)


def test_qecb10_partial_failure_keeps_live_and_labels_seed():
    pages = QECB10__pages()
    pages["rates"] = pages["rates"].replace("113.00 cents/kWh", "120.00 cents/kWh")
    scraper = QECB10_QulliqScraper()
    responses = {QECB10_PAGE_URLS[k]: v for k, v in pages.items()}
    with patch.object(scraper, "fetch_page", side_effect=lambda url: responses[url]),\
            patch.object(QECB10_QulliqScraper, "_page_text", staticmethod(lambda html: html)):
        records = {r.tariff_code: r for r in scraper.scrape()}
    assert "seed_fallback" in records["G-RES"].notes and records["G-RES"].confidence == "unverified"
    assert all(c.confidence == "unverified" for c in records["G-RES"].components)
    assert "live_parsed" in records["NG-RES"].notes and "seed_fallback" not in records["NG-RES"].notes


def test_qecb10_network_failure_all_seed_unverified():
    scraper = QECB10_QulliqScraper()
    with patch.object(scraper, "fetch_page", side_effect=OSError("down")):
        records = scraper.scrape()
    assert len(records) == 6
    assert all(r.confidence == "unverified" and "seed_fallback" in r.notes for r in records)
    assert all(c.charge_value is None or c.charge_value > 0 for r in records for c in r.components)


# ======================================================================
# Yukon Energy and ATCO Electric Yukon joint schedules (batch 10)
# ======================================================================
from scrapers.utilities.yukon_electrical import YukonElectricalScraper as YKB10_YukonElectricalScraper
from scrapers.utilities.yukon_energy import JOINT_SCHEDULE_URL as YKB10_JOINT_SCHEDULE_URL, YukonEnergyScraper as YKB10_YukonEnergyScraper, parse_joint_schedules as YKB10_parse_joint_schedules
import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scrapers.utils.parsing import DocumentPage

YKB10_FIXTURES = Path(__file__).resolve().parent / "fixtures"
YKB10_TODAY = "2026-10-07T00:00:00+00:00"
YKB10_RESIDENTIAL = {"1160", "1260", "1360", "1460", "1180", "1280", "1380", "1480"}
YKB10_GENERAL = {"2160", "2260", "2360", "2460", "2170", "2270", "2370", "2470", "2180", "2280", "2380", "2480"}


def YKB10__b10():
    return json.loads((YKB10_FIXTURES / "yukon_b10.json").read_text(encoding="utf-8"))


def YKB10__documents(book=True, gs_page=True):
    documents = json.loads((YKB10_FIXTURES / "yukon_energy_building_rates.json").read_text(encoding="utf-8"))["documents"]
    b10 = YKB10__b10()
    if gs_page:
        documents["cross_reference"]["pages"] += b10["cross_reference_other_pages"]["pages"]
    if book:
        documents["joint_schedule"] = b10["joint_schedule"]
    return documents


def YKB10__patched(scraper, documents):
    by_url = {document["source_url"]: document for document in documents.values()}
    html = "<body>" + "".join(f'<a href="{url}">Current rate schedule</a>' for url in by_url) + "</body>"

    def pages(data):
        return [DocumentPage(**page) for page in by_url[data.decode("utf-8")]["pages"]]

    return (patch.object(scraper, "fetch_page", return_value=html),
            patch.object(scraper, "fetch_rendered_page", return_value=None),
            patch.object(scraper, "fetch_bytes", side_effect=lambda url: url.encode("utf-8")),
            patch.object(scraper, "now_iso", return_value=YKB10_TODAY),
            patch("scrapers.utilities.yukon_energy.extract_pdf_pages", side_effect=pages))


def YKB10__scrape(documents, scraper=None):
    scraper = scraper or YKB10_YukonEnergyScraper()
    a, b, c, d, e = YKB10__patched(scraper, documents)
    with a, b, c, d, e:
        return scraper.scrape()


def YKB10__live(records):
    return {r.tariff_code: r for r in records if "live_parsed" in (r.notes or "")}


def YKB10__base(record):
    return [c.charge_value for c in record.components if c.component_type in {"fixed", "demand", "energy"}]


def YKB10__mutate_book(documents, page_number, old, new, count=1):
    page = next(p for p in documents["joint_schedule"]["pages"] if p["page_number"] == page_number)
    assert old in page["text"]
    page["text"] = page["text"].replace(old, new, count)


def test_ykb10_fixture_sources_and_pages():
    b10 = YKB10__b10()
    assert b10["retrieved_on"] == "2026-10-07"
    assert b10["joint_schedule"]["source_url"] == YKB10_JOINT_SCHEDULE_URL
    assert [p["page_number"] for p in b10["cross_reference_other_pages"]["pages"]] == [2, 3]
    numbers = [p["page_number"] for p in b10["joint_schedule"]["pages"]]
    assert numbers[0] == 1 and 50 in numbers and set(range(5, 37)) <= set(numbers)


def test_ykb10_joint_book_parses_every_building_schedule():
    pages = [DocumentPage(**p) for p in YKB10__b10()["joint_schedule"]["pages"]]
    terms = YKB10_parse_joint_schedules(pages, "2026-10-07")
    assert set(terms) == YKB10_RESIDENTIAL | YKB10_GENERAL
    assert terms["1160"]["customer"] == terms["1160"]["minimum"] == 14.65
    assert terms["1480"]["blocks"] == [16.47, 17.47, 41.45]
    assert terms["2160"]["demand"] == 7.39 and terms["2160"]["minimum"] == 36.95
    assert terms["2170"]["minimum"] == 36.95
    assert terms["2180"]["demand"] == 12.31 and terms["2180"]["blocks"] == [13.81, 15.0, 20.0, 12.86]
    assert terms["2180"]["minimum"] == 61.55
    assert all(t["effective"] == "2011-07-01" for t in terms.values())
    assert "Whitehorse" in terms["1160"]["available"] and terms["1460"]["available"] == "In Old Crow."
    assert YKB10_parse_joint_schedules(pages, "2011-06-30") == {}


def test_ykb10_without_joint_book_only_1160_is_live():
    records = YKB10__scrape(YKB10__documents(book=False))
    assert set(YKB10__live(records)) == {"1160"}
    assert len(YKB10__live(records)["1160"].components) == 9
    seeds = {r.tariff_name for r in records if "seed_fallback" in (r.notes or "")}
    assert seeds == {"General Service", "Residential Service — Diesel Communities"}


def test_ykb10_all_residential_and_general_service_live_with_book():
    records = YKB10__scrape(YKB10__documents())
    live = YKB10__live(records)
    assert set(live) == YKB10_RESIDENTIAL | YKB10_GENERAL
    assert not [r for r in records if "seed_fallback" in (r.notes or "")]
    for code in ("1160", "1260", "1360"):
        assert YKB10__base(live[code]) == [14.65, 0.1214, 0.1282, 0.1399]
    assert YKB10__base(live["1460"]) == [14.65, 0.1214, 0.1282, 0.3077]
    for code in ("1180", "1280", "1380"):
        assert YKB10__base(live[code]) == [18.47, 0.1647, 0.1747, 0.1885]
    assert YKB10__base(live["1480"]) == [18.47, 0.1647, 0.1747, 0.4145]
    for code in ("2160", "2360", "2170", "2370"):
        assert YKB10__base(live[code]) == [7.39, 0.1, 0.1288, 0.1568, 0.1286]
    assert YKB10__base(live["2260"]) == [7.39, 0.1, 0.1288, 0.1568, 0.1522]
    assert YKB10__base(live["2470"]) == [7.39, 0.1, 0.1288, 0.1568, 0.3172]
    assert YKB10__base(live["2180"]) == [12.31, 0.1381, 0.15, 0.2, 0.1286]
    assert YKB10__base(live["2480"]) == [12.31, 0.1381, 0.15, 0.2, 0.3172]


def test_ykb10_residential_conditions_and_riders():
    live = YKB10__live(YKB10__scrape(YKB10__documents()))
    for code in YKB10_RESIDENTIAL:
        record = live[code]
        government = code[2] == "8"
        assert bool([c for c in record.components if c.component_type == "rebate"]) is not government
        riders = {c.component_name: c.charge_value for c in record.components if c.component_type == "rider"}
        assert riders == {
            "Rider R - Base Rate Adjustment": 14.38, "Rider J - Base Rate Adjustment": 100.23,
            "Rider J1 - Temporary True-Up": 15.91, "Rider F - Fuel Adjustment": 0.01,
        }
        minimum = "18.47" if government else "14.65"
        assert f"Minimum monthly bill: the customer charge of ${minimum}" in record.notes
        assert "Rider A:" in record.notes and "dwelling units" in record.notes
        assert record.effective_date == "2026-10-01"
        assert all(c.source_url and c.source_detail and c.effective_date for c in record.components)
    assert "Watson Lake" in live["1360"].eligibility and "non-government use" in live["1180"].eligibility


def test_ykb10_general_service_conditions_and_riders():
    live = YKB10__live(YKB10__scrape(YKB10__documents()))
    for code in YKB10_GENERAL:
        record = live[code]
        assert record.customer_class == "commercial" and record.rate_structure == "demand"
        demand = next(c for c in record.components if c.component_type == "demand")
        assert demand.charge_unit == "$/kW" and "5 kW" in demand.notes and "April-September" in demand.notes
        assert demand.effective_date == "2011-07-01" and demand.source_url == YKB10_JOINT_SCHEDULE_URL
        energy = [c for c in record.components if c.component_type == "energy"]
        assert [c.tier_threshold for c in energy] == [2000, 15000, 20000, 20000]
        assert "cross-reference page 2" in energy[3].source_detail
        assert not [c for c in record.components if c.component_type in {"rebate", "fixed"}]
        riders = [c for c in record.components if c.component_type == "rider"]
        assert len(riders) == 4 and all("fixed" not in (c.notes or "") for c in riders)
        minimum = "61.55" if code.endswith("80") else "36.95"
        assert f"not less than ${minimum}" in record.notes
        assert record.effective_date == "2026-10-01"


def test_ykb10_general_service_needs_cross_reference_block_four():
    records = YKB10__scrape(YKB10__documents(gs_page=False))
    assert set(YKB10__live(records)) == YKB10_RESIDENTIAL
    assert any(r.tariff_name == "General Service" and "seed_fallback" in r.notes for r in records)


def test_ykb10_general_service_block_four_mismatch_drops_that_code():
    documents = YKB10__documents()
    YKB10__mutate_book(documents, 15, "For energy in excess of 20,000 kW.h 15.22", "For energy in excess of 20,000 kW.h 15.32")
    assert set(YKB10__live(YKB10__scrape(documents))) == (YKB10_RESIDENTIAL | YKB10_GENERAL) - {"2260"}


@pytest.mark.parametrize(("page", "old", "new"), [
    (14, "power factor of 90 percent", "power factor of 85 percent"),
    (13, "not less than $36.95.", "not less than the customer charge."),
    (13, "(d) 5 kilowatts", "(d) 10 kilowatts"),
    (13, "$7.39 / kW", "$7.39 / kV.A"),
])
def test_ykb10_incomplete_general_service_terms_fail_closed(page, old, new):
    documents = YKB10__documents()
    YKB10__mutate_book(documents, page, old, new)
    assert set(YKB10__live(YKB10__scrape(documents))) == (YKB10_RESIDENTIAL | YKB10_GENERAL) - {"2160"}


def test_ykb10_residential_book_mismatch_drops_only_that_code():
    documents = YKB10__documents()
    YKB10__mutate_book(documents, 9, "16.47", "16.57")
    assert set(YKB10__live(YKB10__scrape(documents))) == (YKB10_RESIDENTIAL | YKB10_GENERAL) - {"1180"}


def test_ykb10_1160_book_without_minimum_keeps_legacy_1160_only():
    documents = YKB10__documents()
    YKB10__mutate_book(documents, 5, "Customer Charge $14.65", "Customer Charge $15.65")
    live = YKB10__live(YKB10__scrape(documents))
    assert set(live) == (YKB10_RESIDENTIAL | YKB10_GENERAL)
    assert "Minimum monthly bill" not in live["1160"].notes and YKB10__base(live["1160"])[0] == 14.65


def test_ykb10_missing_minimum_bill_drops_residential_code():
    documents = YKB10__documents()
    YKB10__mutate_book(documents, 6, "The minimum monthly charge is", "The monthly charge is")
    assert set(YKB10__live(YKB10__scrape(documents))) == (YKB10_RESIDENTIAL | YKB10_GENERAL) - {"1260"}


def test_ykb10_1160_book_mismatch_rejects_all_live_output():
    documents = YKB10__documents()
    YKB10__mutate_book(documents, 5, "1,000 kW.h 12.14", "1,000 kW.h 12.24")
    records = YKB10__scrape(documents)
    assert not YKB10__live(records) and all(r.confidence == "unverified" for r in records)


def test_ykb10_unrecognised_book_falls_back_to_1160_only():
    documents = YKB10__documents()
    for page in documents["joint_schedule"]["pages"]:
        page["text"] = page["text"].replace("YECL/YEC Joint", "Draft")
    assert set(YKB10__live(YKB10__scrape(documents))) == {"1160"}


def test_ykb10_future_dated_schedule_is_not_live():
    documents = YKB10__documents()
    YKB10__mutate_book(documents, 29, "Effective: 2011 07 01", "Effective: 2027 01 01")
    assert set(YKB10__live(YKB10__scrape(documents))) == (YKB10_RESIDENTIAL | YKB10_GENERAL) - {"2180"}


def test_ykb10_bad_cross_reference_government_column_drops_only_that_section():
    documents = YKB10__documents()
    page = documents["cross_reference"]["pages"][0]
    page["text"] = page["text"].replace("16.47 2.37 16.51 35.35", "16.47 2.37 16.51 3.35", 1)
    assert set(YKB10__live(YKB10__scrape(documents))) == (YKB10_RESIDENTIAL | YKB10_GENERAL) - {"1180", "1280", "1380"}


def test_ykb10_shared_riders_are_independent_copies():
    live = YKB10__live(YKB10__scrape(YKB10__documents()))
    fuel = [next(c for c in r.components if "Rider F" in c.component_name) for r in live.values()]
    assert len({id(c) for c in fuel}) == len(fuel) == 20


def test_ykb10_cross_reference_gs_page_only_publishes_block_four():
    text = YKB10__b10()["cross_reference_other_pages"]["pages"][0]["text"]
    assert all(code in text for code in YKB10_GENERAL)
    assert text.count("Energy Block 4") == 6
    assert "Customer" not in text and "Block 1" not in text and "Demand" not in text


def test_ykb10_unmodelled_atco_riders_are_currently_zero():
    riders = YKB10__b10()["atco_unmodelled_riders"]
    texts = {name: doc["pages"][0]["text"] for name, doc in riders.items()}
    assert "adjusted by the following rate: 0.0%" in texts["aey-yec-rider-r1-schedule.pdf"]
    assert "All Energy consumed at $0.0 per kWh" in texts["aey-yec-rider-s-rate-schedule.pdf"]
    assert "A rider of 0 \u00a2 per kWh" in texts["yec-rider-e.pdf"]
    assert "RATE: -$0.0 per kWh" in texts["aey-yec-winter-electrical-affordability-rebate.pdf"]


def test_ykb10_atco_yukon_reuses_joint_schedules():
    scraper = YKB10_YukonElectricalScraper()
    records = YKB10__scrape(YKB10__documents(), scraper)
    live = YKB10__live(records)
    assert set(live) == YKB10_RESIDENTIAL | YKB10_GENERAL
    assert all(r.utility_name == "Yukon Electrical Company" for r in records)
    assert all("ATCO Electric Yukon service areas" in r.notes for r in live.values())
    assert YKB10__base(live["2160"]) == [7.39, 0.1, 0.1288, 0.1568, 0.1286]
    assert not [r for r in records if "seed_fallback" in (r.notes or "")]


def test_ykb10_atco_yukon_without_book_keeps_general_service_seed():
    records = YKB10__scrape(YKB10__documents(book=False), YKB10_YukonElectricalScraper())
    assert set(YKB10__live(records)) == {"1160"}
    gs = [r for r in records if r.tariff_name == "General Service"]
    assert len(gs) == 1 and gs[0].confidence == "unverified" and "seed_fallback" in gs[0].notes
    assert not any(r.tariff_name == "Residential Service" for r in records)


def test_ykb10_atco_yukon_js_shell_keeps_labelled_seeds():
    scraper = YKB10_YukonElectricalScraper()
    shell = "<html><body><noscript>You need to enable JavaScript to run this app.</noscript></body></html>"
    with patch.object(scraper, "fetch_page", return_value=shell),\
         patch.object(scraper, "fetch_rendered_page", return_value=shell):
        records = scraper.scrape()
    assert {r.tariff_name for r in records} == {"Residential Service", "General Service"}
    assert all(r.confidence == "unverified" and "seed_fallback" in r.notes for r in records)
    assert all(c.confidence == "unverified" for r in records for c in r.components)


# ======================================================================
# Centra Mainline Interruptible transcription (batch 11)
# ======================================================================
from scrapers.utilities.centra_gas import CentraGasScraper as CGB11_CentraGasScraper
import copy
import json
import logging
from datetime import date
from pathlib import Path

from scrapers.utilities import centra_gas

CGB11_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "centra_gas.json"
CGB11_TODAY = date(2026, 10, 7)
CGB11_EXISTING = {"SGS", "SGS-MKT", "COM-SGS", "COM-SGS-MKT", "COM-LGS", "COM-LGS-MKT",
            "COM-HVF-S", "COM-HVF-T", "COM-MFS-S", "COM-MFS-T", "COM-IS-S", "COM-IS-T"}


def CGB11__document():
    return json.loads(CGB11_FIXTURE_PATH.read_text(encoding="utf-8"))


def CGB11__appendix(transcription, hashes=None):
    parts = ["PDF page 19 " + transcription["evidence"]["19"], "PDF page 50 " + transcription["evidence"]["50"]]
    for number, page in transcription["pages"].items():
        digest = (hashes or {}).get(number, page["image_sha256"])
        parts.append("PDF page " + number + " image-sha256 " + digest + " " + page["header_text"])
    return " ".join(parts)


def CGB11__pages(with_appendix=True, hashes=None):
    document = CGB11__document()
    pages = {key: page["text"] for key, page in document["pages"].items()}
    if with_appendix:
        pages["appendix_a"] = CGB11__appendix(document["appendix_a_transcription"], hashes)
    return pages


def CGB11__parse(pages):
    scraper = CGB11_CentraGasScraper()
    records = scraper.parse_pages(pages, CGB11_TODAY)
    return scraper, {record.tariff_code: record for record in records}


def CGB11__components(record):
    return {component.component_name: component for component in record.components}


def test_cgb11_module_transcription_mirrors_fixture():
    fixture = CGB11__document()["appendix_a_transcription"]
    module = centra_gas.APPENDIX_A
    assert fixture["board_order"] == module["board_order"] and fixture["effective"] == module["effective"]
    assert fixture["transcribed"] == module["transcribed"] == "2026-10-07"
    assert {int(number) for number in fixture["pages"]} == set(module["pages"])
    for number, page in fixture["pages"].items():
        mirror = module["pages"][int(number)]
        assert page["image_sha256"] == mirror["image_sha256"]
        assert page["label"] == mirror["label"] and page["title"] == mirror["title"]
        assert page["rows"] == mirror["rows"]


def test_cgb11_hash_match_builds_mainline_interruptible():
    scraper, records = CGB11__parse(CGB11__pages())
    assert set(records) == CGB11_EXISTING | {"COM-MLI-S"}
    assert scraper.unmodelled_classes == []
    record = records["COM-MLI-S"]
    assert record.tariff_name == "Commercial — Mainline Interruptible Sales (Firm Delivery)"
    assert record.customer_class == "commercial" and record.sub_class == "mainline interruptible"
    assert record.rate_structure == "demand" and record.usage_min == 680000 and record.usage_unit == "m³/year"
    assert record.effective_date == "2026-08-01"
    assert record.source_url == centra_gas.PAGE_URLS["schedule"]
    assert "PDF page 82" in record.source_page


def test_cgb11_values_units_and_medium_confidence():
    _, records = CGB11__parse(CGB11__pages())
    record = records["COM-MLI-S"]
    parts = CGB11__components(record)
    expected = {
        "Basic Monthly Charge": (1306.98, "$/month"),
        "Gas Commodity": (0.066, "$/m³"),
        "Transportation to Centra": (0.0, "$/m³"),
        "Distribution Charge": (0.0184, "$/m³"),
        "Demand Transportation Charge": (0.1816, "$/m³/month"),
        "Demand Distribution Charge": (0.2271, "$/m³/month"),
        "Alternate Supply Service": (0.003, "$/m³"),
        "Federal Carbon Charge": (0.0, "$/m³"),
    }
    assert {name: (part.charge_value, part.charge_unit) for name, part in parts.items()} == expected
    assert record.confidence == "medium"
    assert all(part.confidence == "medium" for part in record.components)
    assert "Delivery" not in parts and not any("0.4087" in str(part.charge_value) for part in record.components)
    for name, part in parts.items():
        if name == "Federal Carbon Charge":
            assert part.effective_date == "2025-04-01" and "revenue-agency" in part.source_url
            continue
        assert part.source_url == centra_gas.PAGE_URLS["schedule"]
        assert "Appendix A page 4 of 4 (PDF page 82)" in part.source_detail
        assert "Transcribed from scanned official Appendix A page 4 of 4" in part.notes
        assert "fails closed if the page changes" in part.notes
    assert "PDF page 34" in parts["Demand Distribution Charge"].source_detail
    assert "Conditional" in parts["Alternate Supply Service"].notes
    assert "Transcribed from scanned official Appendix A" in record.notes
    assert "base-only" in record.notes


def test_cgb11_conditions_are_recorded_not_priced():
    _, records = CGB11__parse(CGB11__pages())
    eligibility = records["COM-MLI-S"].eligibility
    for phrase in ("above medium pressure", "Interruptible Sales Service in conjunction with Firm Delivery",
                   "stand-by fuel", "Monthly billing demand", "pass-through commodity/transport"):
        assert phrase in eligibility


def test_cgb11_live_marking_keeps_medium_confidence():
    scraper, records = CGB11__parse(CGB11__pages())
    marked = scraper.mark_live_parsed([records["COM-MLI-S"]])[0]
    assert marked.notes.startswith("Provenance: live_parsed.")
    assert marked.confidence == "medium"
    assert all(part.confidence == "medium" and part.notes.startswith("Provenance: live_parsed.")
               for part in marked.components)


def test_cgb11_hash_mismatch_omits_only_mainline_interruptible(caplog):
    with caplog.at_level(logging.WARNING):
        scraper, records = CGB11__parse(CGB11__pages(hashes={"82": "0" * 64}))
    assert set(records) == CGB11_EXISTING
    assert scraper.unmodelled_classes == ["Mainline Interruptible (with firm delivery)"]
    assert "image changed since the reviewed transcription" in caplog.text


def test_cgb11_base_only_page_hash_mismatch_also_fails_closed():
    _, records = CGB11__parse(CGB11__pages(hashes={"80": "f" * 64}))
    assert set(records) == CGB11_EXISTING


def test_cgb11_missing_page_omits_only_mainline_interruptible():
    pages = CGB11__pages()
    pages["appendix_a"] = pages["appendix_a"].split(" PDF page 82 ")[0]
    scraper, records = CGB11__parse(pages)
    assert set(records) == CGB11_EXISTING
    assert scraper.unmodelled_classes == ["Mainline Interruptible (with firm delivery)"]


def test_cgb11_empty_appendix_is_a_gap():
    pages = CGB11__pages()
    pages["appendix_a"] = ""
    scraper, records = CGB11__parse(pages)
    assert set(records) == CGB11_EXISTING
    assert scraper.unmodelled_classes == ["Mainline Interruptible (with firm delivery)"]


def test_cgb11_changed_edition_header_fails_closed():
    pages = CGB11__pages()
    pages["appendix_a"] = pages["appendix_a"].replace("Approved by Board Order: 111/26", "Approved by Board Order: 140/26")
    _, records = CGB11__parse(pages)
    assert set(records) == CGB11_EXISTING


def test_cgb11_missing_election_evidence_fails_closed():
    pages = CGB11__pages()
    pages["appendix_a"] = pages["appendix_a"].replace("Interruptible Sales Service (in conjunction", "Sales Service (in conjunction")
    _, records = CGB11__parse(pages)
    assert set(records) == CGB11_EXISTING


def test_cgb11_text_cross_check_mismatch_fails_closed():
    pages = CGB11__pages()
    pages["commercial"] = pages["commercial"].replace("$1,409.45", "$1,410.45")
    _, records = CGB11__parse(pages)
    assert "COM-MLI-S" not in records
    assert {"COM-IS-S", "COM-IS-T"} <= set(records)


def test_cgb11_transcription_arithmetic_inconsistency_fails_closed(monkeypatch):
    broken = copy.deepcopy(centra_gas.APPENDIX_A)
    broken["pages"][82]["rows"]["Mainline Interruptible (with firm delivery)"]["demand_delivery"] = 0.4088
    monkeypatch.setattr(centra_gas, "APPENDIX_A", broken)
    _, records = CGB11__parse(CGB11__pages())
    assert set(records) == CGB11_EXISTING


def test_cgb11_without_appendix_input_behaviour_is_unchanged():
    scraper, records = CGB11__parse(CGB11__pages(with_appendix=False))
    assert set(records) == CGB11_EXISTING
    assert scraper.unmodelled_classes == []


def test_cgb11_existing_twelve_classes_unchanged():
    _, before = CGB11__parse(CGB11__pages(with_appendix=False))
    _, after = CGB11__parse(CGB11__pages())
    assert {code: after[code] for code in CGB11_EXISTING} == before


def test_cgb11_class_audit_treats_mainline_interruptible_as_modelled_only_when_built():
    pages = CGB11__pages()
    pages["classes"] = pages["classes"].replace(
        "Mainline Class, Special", "Mainline Class, Mainline Interruptible Class, Special")
    scraper, _ = CGB11__parse(pages)
    assert scraper.unmodelled_classes == []
    pages["appendix_a"] = ""
    scraper, _ = CGB11__parse(pages)
    assert scraper.unmodelled_classes == ["Mainline Interruptible Class", "Mainline Interruptible (with firm delivery)"]


# ======================================================================
# FortisBC Energy RNG and Customer Choice variants (batch 11)
# ======================================================================
from scrapers.utilities.fortisbc_energy import FortisBCEnergyScraper as FBEB11_FortisBCEnergyScraper
"""FortisBC Energy optional variants: Customer Choice 1U/2U/3U and RNG 1RNG/2RNG/3RNG/5RNG/7RNG (batch 11)."""
import json
from datetime import date
from pathlib import Path

import pytest


FBEB11_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "fortisbc_energy.json"
FBEB11_TODAY = date(2026, 10, 7)
FBEB11_VARIANT_KEYS = ("rate1u", "rate2u", "rate3u", "rate1b", "rate2b", "rate3b", "rate5b", "rate7b")
FBEB11_NAMES = {
    "rate1u": "Residential — Rate 1U (Customer Choice)",
    "rate2u": "Commercial — Rate 2U (Customer Choice)",
    "rate3u": "Commercial — Rate 3U (Customer Choice)",
    "rate1b": "Residential — Rate 1RNG (Renewable Natural Gas)",
    "rate2b": "Commercial — Rate 2RNG (Renewable Natural Gas)",
    "rate3b": "Commercial — Rate 3RNG (Renewable Natural Gas)",
    "rate5b": "Commercial — Rate 5RNG (Renewable Natural Gas)",
    "rate7b": "Industrial — Rate 7RNG (Renewable Natural Gas)",
}
FBEB11_BATCH10_KEYS = ("rate7", "rate22", "rate23", "rate25", "rate27")
FBEB11_FN_NAMES = {
    "rate1b": "Residential — Rate 1RNG (Renewable Natural Gas, Fort Nelson)",
    "rate2b": "Commercial — Rate 2RNG (Renewable Natural Gas, Fort Nelson)",
    "rate3b": "Commercial — Rate 3RNG (Renewable Natural Gas, Fort Nelson)",
}
FBEB11_EXISTING = {
    "Residential — Rate 1", "Residential — Rate 1 (Fort Nelson)", "Commercial — Rate 2",
    "Commercial — Rate 2 (Fort Nelson)", "Commercial — Rate 3", "Commercial — Rate 3 (Fort Nelson)",
    "Commercial — Rate 4", "Commercial — Rate 5", "Industrial — Rate 7", "Industrial — Rate 22 (Transportation)",
    "Commercial — Rate 23 (Transportation)", "Commercial — Rate 25 (Transportation)",
    "Industrial — Rate 27 (Transportation)",
}


def FBEB11_load_document():
    return json.loads(FBEB11_FIXTURE.read_text(encoding="utf-8"))


def FBEB11_base_inputs(document):
    pages = {key: page["text"] for key, page in document["pages"].items()}
    pages["business_rate45"] += " " + document["business_rate7"]["text"]
    pages["tariffs"] = document["tariffs_transport"]["text"]
    urls = {key: document["pages"][key]["url"] for key in ("rate4", "rate5")}
    for key in FBEB11_BATCH10_KEYS:
        pages[key] = document[key]["text"]
        urls[key] = document[key]["url"]
    return pages, urls


def FBEB11_full_inputs(document):
    pages, urls = FBEB11_base_inputs(document)
    for key in FBEB11_VARIANT_KEYS:
        pages[key] = document[key]["text"]
        urls[key] = document[key]["url"]
    return pages, urls


def FBEB11_parse(pages, urls):
    return {r.tariff_name: r for r in FBEB11_FortisBCEnergyScraper().parse_pages(pages, FBEB11_TODAY, document_urls=urls)}


def FBEB11_records(document=None):
    return FBEB11_parse(*FBEB11_full_inputs(document or FBEB11_load_document()))


def FBEB11_values(record):
    return {c.component_name: (c.charge_value, c.charge_unit, c.sub_component) for c in record.components}


def FBEB11_all_names():
    return FBEB11_EXISTING | set(FBEB11_NAMES.values()) | set(FBEB11_FN_NAMES.values())


def FBEB11_names_for(*keys):
    return {FBEB11_NAMES[key] for key in keys} | {FBEB11_FN_NAMES[key] for key in keys if key in FBEB11_FN_NAMES}


def test_fbeb11_all_variants_parse_with_existing_preserved():
    found = FBEB11_records()
    assert set(found) == FBEB11_all_names()
    document = FBEB11_load_document()
    for key, name in FBEB11_NAMES.items():
        record = found[name]
        assert record.source_url == document[key]["url"]
        assert record.effective_date == "2026-07-01"
        assert record.sub_class == "Mainland and Vancouver Island Service Area"
        for component in record.components:
            assert component.source_url and component.source_detail and component.effective_date
        assert any(c.component_type == "carbon" and c.charge_value == 0.0 for c in record.components)


def test_fbeb11_existing_records_identical_with_and_without_variants():
    document = FBEB11_load_document()
    before = FBEB11_parse(*FBEB11_base_inputs(document))
    after = FBEB11_parse(*FBEB11_full_inputs(document))
    assert set(before) == FBEB11_EXISTING
    for name, record in before.items():
        assert after[name] == record


def test_fbeb11_customer_choice_1u_is_delivery_only():
    record = FBEB11_records()[FBEB11_NAMES["rate1u"]]
    assert (record.tariff_code, record.customer_class) == ("Rate 1U", "residential")
    assert FBEB11_values(record) == {
        "Basic Charge": (0.4085, "$/day", None),
        "Rider 2 (Clean Growth Innovation Fund Account)": (0.0131, "$/day", None),
        "Delivery Charge": (8.257, "$/GJ", None),
        "Rider 5 (Revenue Stabilization Adjustment Charge)": (0.212, "$/GJ", None),
        "Storage and Transport Charge": (1.347, "$/GJ", None),
        "Rider 6 (Midstream Cost Reconciliation Account)": (0.216, "$/GJ", None),
        "Rider 8 (Storage and Transport RNG)": (0.909, "$/GJ", None),
        "BC Carbon Tax": (0.0, "$/GJ", None),
    }
    assert not [c for c in record.components if c.component_type == "commodity"]
    assert "marketer" in record.notes and "not included" in record.notes
    assert "single-family residences" in record.eligibility
    assert "Order G-131-26" in record.source_page


def test_fbeb11_customer_choice_2u_3u_volumes_and_terms():
    found = FBEB11_records()
    two, three = found[FBEB11_NAMES["rate2u"]], found[FBEB11_NAMES["rate3u"]]
    assert (two.usage_min, two.usage_max, two.usage_unit) == (None, 2000.0, "GJ/year")
    assert (three.usage_min, three.usage_max, three.usage_unit) == (2000.0, None, "GJ/year")
    assert "minimum of one Year" in two.eligibility and "minimum period of one Year" in three.eligibility
    assert FBEB11_values(two)["Basic Charge"] == (1.4178, "$/day", None)
    assert FBEB11_values(two)["Storage and Transport Charge"] == (1.365, "$/GJ", None)
    assert FBEB11_values(three)["Basic Charge"] == (4.3395, "$/day", None)
    assert FBEB11_values(three)["Delivery Charge"] == (5.165, "$/GJ", None)
    assert FBEB11_values(three)["Rider 6 (Midstream Cost Reconciliation Account)"] == (0.188, "$/GJ", None)


def test_fbeb11_rng_1b_replaces_cost_of_gas_for_selected_share():
    record = FBEB11_records()[FBEB11_NAMES["rate1b"]]
    assert record.tariff_code == "Rate 1RNG"
    v = FBEB11_values(record)
    assert v["Basic Charge"] == (0.4085, "$/day", None)
    assert v["Delivery Charge"] == (8.257, "$/GJ", None)
    assert v["Storage and Transport Charge"] == (1.347, "$/GJ", None)
    assert v["Cost of Gas"] == (1.660, "$/GJ", "conditional")
    assert v["Cost of Renewable Natural Gas (RNG Charge)"] == (8.660, "$/GJ", "conditional")
    rng = next(c for c in record.components if c.component_name.startswith("Cost of Renewable"))
    assert "instead of the Cost of Gas" in rng.notes and "5% to 100%" in rng.notes
    assert "Rate Schedule 1U are ineligible" in record.eligibility


def test_fbeb11_rng_2b_3b_use_mainland_column_only():
    found = FBEB11_records()
    two, three = FBEB11_values(found[FBEB11_NAMES["rate2b"]]), FBEB11_values(found[FBEB11_NAMES["rate3b"]])
    assert two["Storage and Transport Charge"] == (1.365, "$/GJ", None)
    assert three["Storage and Transport Charge"] == (1.171, "$/GJ", None)
    assert three["Rider 6 (Midstream Cost Reconciliation Account)"] == (0.188, "$/GJ", None)
    assert found[FBEB11_NAMES["rate3b"]].usage_min == 2000.0 and found[FBEB11_NAMES["rate2b"]].usage_max == 2000.0


def test_fbeb11_rng_5b_monthly_demand_and_7b_interruptible():
    found = FBEB11_records()
    five, seven = found[FBEB11_NAMES["rate5b"]], found[FBEB11_NAMES["rate7b"]]
    assert FBEB11_values(five) == {
        "Basic Charge": (469.00, "$/month", None),
        "Rider 2 (Clean Growth Innovation Fund Account)": (0.40, "$/month", None),
        "Demand Charge": (37.735, "$/GJ/month of daily demand", None),
        "Delivery Charge": (1.352, "$/GJ", None),
        "Storage and Transport Charge": (0.784, "$/GJ", None),
        "Rider 6 (Midstream Cost Reconciliation Account)": (0.126, "$/GJ", None),
        "Rider 8 (Storage and Transport RNG)": (0.909, "$/GJ", None),
        "Cost of Gas": (1.660, "$/GJ", "conditional"),
        "Cost of Renewable Natural Gas (RNG Charge)": (8.660, "$/GJ", "conditional"),
        "BC Carbon Tax": (0.0, "$/GJ", None),
    }
    assert five.rate_structure == "demand" and "General Firm Service Agreement" in five.notes
    assert FBEB11_values(seven)["Basic Charge"] == (880.00, "$/month", None)
    assert FBEB11_values(seven)["Delivery Charge"] == (2.199, "$/GJ", None)
    assert seven.customer_class == "industrial" and "Unauthorized Overrun Gas" in seven.notes


@pytest.mark.parametrize("key, old, new", [
    ("rate1u", "1. Basic Charge per Day $ 0.4085", "1. Basic Charge per Day $ 0.5085"),
    ("rate2u", "Rate Schedule 36 Service Agreement", "Rate Schedule 99 Service Agreement"),
    ("rate3u", "Effective Date: July 1, 2026", "Effective Date: July 1, 2027"),
    ("rate1b", "ranges between 5% of RNG and 100% of RNG", "ranges between some RNG"),
    ("rate2b", "Cost of Renewable Natural Gas (RNG Charge) per Gigajoule2,3 $ 8.660",
     "Cost of Renewable Natural Gas (RNG Charge) per Gigajoule2,3 TBD"),
    ("rate3b", "of greater than 2,000 Gigajoules", "of less than 2,000 Gigajoules"),
    ("rate5b", "Daily Demand is equal to 1.10", "Daily Demand is"),
    ("rate7b", "RATE SCHEDULE 7RNG", "RATE SCHEDULE 7X"),
])
def test_fbeb11_each_variant_fails_closed_independently(key, old, new):
    document = FBEB11_load_document()
    assert old in document[key]["text"]
    document[key]["text"] = document[key]["text"].replace(old, new)
    found = FBEB11_records(document)
    assert set(found) == FBEB11_all_names() - FBEB11_names_for(key)


def test_fbeb11_missing_documents_reject_only_those_variants():
    document = FBEB11_load_document()
    pages, urls = FBEB11_full_inputs(document)
    del pages["rate2b"]
    urls.pop("rate3u")
    found = FBEB11_parse(pages, urls)
    assert set(found) == FBEB11_all_names() - FBEB11_names_for("rate2b", "rate3u")


def test_fbeb11_price_follows_source():
    document = FBEB11_load_document()
    document["rate5b"]["text"] = document["rate5b"]["text"].replace("per Gigajoule3,4 $ 8.660", "per Gigajoule3,4 $ 9.100")
    assert FBEB11_values(FBEB11_records(document)[FBEB11_NAMES["rate5b"]])["Cost of Renewable Natural Gas (RNG Charge)"][0] == 9.1


def test_fbeb11_carbon_evidence_still_required():
    pages, urls = FBEB11_full_inputs(FBEB11_load_document())
    pages["carbon"] = "Carbon tax applies."
    assert FBEB11_parse(pages, urls) == {}


def test_fbeb11_discovery_finds_variant_links_but_not_vehicle_rng():
    index = "".join(f'<a href="https://y/gas-utility/rateschedule_{n}.pdf?sfvrsn=1">R</a>'
                    for n in ("1", "1u", "1b", "2b", "3vrng", "5b", "5vrng", "7b", "11b", "22"))
    found = FBEB11_FortisBCEnergyScraper._discover_documents("", index)
    assert found == {"rate22": "https://y/gas-utility/rateschedule_22.pdf?sfvrsn=1",
                     "rate1u": "https://y/gas-utility/rateschedule_1u.pdf?sfvrsn=1",
                     "rate1b": "https://y/gas-utility/rateschedule_1b.pdf?sfvrsn=1",
                     "rate2b": "https://y/gas-utility/rateschedule_2b.pdf?sfvrsn=1",
                     "rate5b": "https://y/gas-utility/rateschedule_5b.pdf?sfvrsn=1",
                     "rate7b": "https://y/gas-utility/rateschedule_7b.pdf?sfvrsn=1"}


def test_fbeb11_fort_nelson_1rng_uses_fort_nelson_column_with_rider_4_credit():
    document = FBEB11_load_document()
    record = FBEB11_records(document)[FBEB11_FN_NAMES["rate1b"]]
    assert (record.tariff_code, record.customer_class, record.sub_class) == ("Rate 1RNG", "residential", "Fort Nelson")
    assert record.source_url == document["rate1b"]["url"]
    assert record.effective_date == "2026-07-01"
    assert "Fort Nelson Service Area" in record.source_page and "Order G-131-26" in record.source_page
    assert FBEB11_values(record) == {
        "Basic Charge": (0.4085, "$/day", None),
        "Rider 2 (Clean Growth Innovation Fund Account)": (0.0131, "$/day", None),
        "Delivery Charge": (8.257, "$/GJ", None),
        "Rider 4 (Fort Nelson Residential Customer Common Rate Phase-in Rider)": (-0.355, "$/GJ", None),
        "Rider 5 (Revenue Stabilization Adjustment Charge)": (0.212, "$/GJ", None),
        "Storage and Transport Charge": (0.067, "$/GJ", None),
        "Rider 6 (Midstream Cost Reconciliation Account)": (0.011, "$/GJ", None),
        "Rider 8 (Storage and Transport RNG)": (0.909, "$/GJ", None),
        "Cost of Gas": (1.660, "$/GJ", "conditional"),
        "Cost of Renewable Natural Gas (RNG Charge)": (8.660, "$/GJ", "conditional"),
        "BC Carbon Tax": (0.0, "$/GJ", None),
    }
    assert "Fort Nelson Service Area" in record.eligibility and "single-family residences" in record.eligibility
    assert "no blended price" in record.notes and "Fort Nelson" in record.notes
    for component in record.components:
        assert component.source_url and component.source_detail and component.effective_date


def test_fbeb11_fort_nelson_2rng_3rng_values_and_volumes():
    found = FBEB11_records()
    two, three = found[FBEB11_FN_NAMES["rate2b"]], found[FBEB11_FN_NAMES["rate3b"]]
    assert FBEB11_values(two)["Basic Charge"] == (1.4178, "$/day", None)
    assert FBEB11_values(two)["Storage and Transport Charge"] == (0.068, "$/GJ", None)
    assert FBEB11_values(two)["Rider 6 (Midstream Cost Reconciliation Account)"] == (0.011, "$/GJ", None)
    assert FBEB11_values(three)["Basic Charge"] == (4.3395, "$/day", None)
    assert FBEB11_values(three)["Storage and Transport Charge"] == (0.058, "$/GJ", None)
    assert FBEB11_values(three)["Rider 6 (Midstream Cost Reconciliation Account)"] == (0.009, "$/GJ", None)
    for record in (two, three):
        assert not any(c.component_name.startswith("Rider 4") for c in record.components)
        assert FBEB11_values(record)["Cost of Renewable Natural Gas (RNG Charge)"] == (8.660, "$/GJ", "conditional")
        assert record.sub_class == "Fort Nelson" and record.customer_class == "commercial"
    assert (two.usage_min, two.usage_max) == (None, 2000.0) and (three.usage_min, three.usage_max) == (2000.0, None)


def test_fbeb11_mainland_rng_values_unaffected_by_fort_nelson_column():
    found = FBEB11_records()
    for key in FBEB11_FN_NAMES:
        mainland = found[FBEB11_NAMES[key]]
        assert mainland.sub_class == "Mainland and Vancouver Island Service Area"
        assert not any(c.component_name.startswith("Rider 4") for c in mainland.components)
    assert FBEB11_values(found[FBEB11_NAMES["rate1b"]])["Storage and Transport Charge"] == (1.347, "$/GJ", None)


@pytest.mark.parametrize("key, old, new", [
    ("rate2b", "Related Charges $ 2.493 $ 0.988 A", "Related Charges $ 2.493 $ 0.999 A"),
    ("rate1b", "4. Rider 4 per Gigajoule N/A $ (0.355)", "4. Rider 4 per Gigajoule N/A $ (0.455)"),
    ("rate1b", "Rider 4 Fort Nelson Residential Customer Common Rate Phase-in Rider",
     "Rider 4 Residential Customer Rider"),
    ("rate3b", "Mainland and Vancouver Island Fort Nelson Service Area Service Area",
     "Mainland and Vancouver Island Service Area"),
    ("rate3b", "with the exception of the Municipality of Revelstoke, provided",
     "with the exception of the Municipality of Revelstoke and the Fort Nelson Service Area, provided"),
])
def test_fbeb11_fort_nelson_record_fails_closed_without_touching_mainland(key, old, new):
    document = FBEB11_load_document()
    assert old in document[key]["text"]
    document[key]["text"] = document[key]["text"].replace(old, new)
    assert set(FBEB11_records(document)) == FBEB11_all_names() - {FBEB11_FN_NAMES[key]}


def test_fbeb11_customer_choice_schedules_publish_no_fort_nelson_column():
    document = FBEB11_load_document()
    found = FBEB11_records(document)
    for key in ("rate1u", "rate2u", "rate3u"):
        assert "with the exception of the Municipality of Revelstoke and the Fort Nelson Service Area" in document[key]["text"]
        assert "Table of Charges Mainland and Vancouver Island Service Area Delivery" in document[key]["text"]
        assert found[FBEB11_NAMES[key]].sub_class == "Mainland and Vancouver Island Service Area"
    assert not [name for name in found if "Customer Choice" in name and "Fort Nelson" in name]


# ======================================================================
# NTPC Taltson interruptible heating (batch 11)
# ======================================================================

"""NTPC Taltson retail interruptible heating record (batch 11, pending integration)."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from scrapers.utilities import ntpc
from scrapers.utils.parsing import DocumentPage

NTPCB11_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ntpc.json"
NTPCB11_TODAY = "2026-10-07"


def NTPCB11__fx():
    return json.loads(NTPCB11_FIXTURE.read_text(encoding="utf-8"))


def NTPCB11__pages(block, edit=None):
    pages = [DocumentPage(p["page"], p["text"]) for p in block["pages"]]
    return [DocumentPage(p.page_number, edit(p.page_number, p.text)) for p in pages] if edit else pages


def NTPCB11__record(fx=None, rate_edit=None, terms_edit=None):
    fx = fx or NTPCB11__fx()
    rate = ntpc.parse_interruptible_retail(NTPCB11__pages(fx["interruptible_schedule"], rate_edit),
                                           fx["interruptible_schedule"]["url"], NTPCB11_TODAY)
    terms = ntpc.parse_terms_schedule_d(NTPCB11__pages(fx["terms"], terms_edit), fx["terms"]["url"], NTPCB11_TODAY)
    return ntpc.build_interruptible_record(rate, terms)


def NTPCB11__scrape(terms_pages=None, schedule_extra=True, terms_error=False):
    fx = NTPCB11__fx()
    html = {ntpc.SCHEDULE_INDEX_URL: fx["schedule_index"]["html"], ntpc.RESIDENTIAL_URL: fx["residential"]["html"],
            ntpc.TPSP_URL: fx["tpsp"]["html"], ntpc.RIDER_URL: fx["riders"]["html"]}
    schedule = NTPCB11__pages(fx["schedule"]) + (NTPCB11__pages(fx["interruptible_schedule"]) if schedule_extra else [])
    terms = terms_pages if terms_pages is not None else NTPCB11__pages(fx["terms"])

    def fetch_bytes(self, url, delay=1.0):
        if url == ntpc.TERMS_URL and terms_error:
            raise ConnectionError("blocked")
        return url.encode()

    def extract(data):
        return terms if data.decode() == ntpc.TERMS_URL else schedule

    with patch.object(ntpc.NTPCScraper, "fetch_page", lambda self, url, delay=1.0: html[url]),\
            patch.object(ntpc.NTPCScraper, "fetch_bytes", fetch_bytes),\
            patch.object(ntpc.NTPCScraper, "now_iso", lambda self: NTPCB11_TODAY + "T00:00:00+00:00"),\
            patch.object(ntpc, "extract_pdf_pages", extract):
        return ntpc.NTPCScraper().scrape()


def test_ntpcb11_fixture_sources():
    fx = NTPCB11__fx()
    assert fx["terms"]["url"] == ntpc.TERMS_URL and fx["terms"]["retrieved"] == "2026-10-07"
    assert [p["page"] for p in fx["terms"]["pages"]] == [1, 8, 59, 60, 61]
    assert [p["page"] for p in fx["interruptible_schedule"]["pages"]] == [20]
    assert fx["interruptible_schedule"]["url"] == fx["schedule"]["url"]


def test_ntpcb11_record_values_and_conditions():
    record = NTPCB11__record()
    assert record.tariff_name == ntpc.INTERRUPTIBLE_NAME
    assert (record.customer_class, record.sub_class, record.province) == ("commercial", "interruptible heating", "NT")
    assert record.effective_date == "2026-06-01" and record.source_page == "PDF page 20"
    (component,) = record.components
    assert (component.component_type, component.charge_value, component.charge_unit) == ("energy", 0.063, "$/kWh")
    assert component.effective_date == "2026-06-01" and component.confidence == "high"
    assert "PDF page 20" in component.source_detail and "PDF pages 59-60" in component.source_detail
    assert component.notes.startswith("Conditional")
    for phrase in ("Fort Smith and Fort Resolution", "new interruptible loads", "fully interruptible",
                   "primarily to provide heat", "unlimited duration", "12 months notice",
                   "not be able to switch back"):
        assert phrase in record.eligibility
    assert "Riders not stated" in record.notes and "approved by the NWT Public Utilities Board" in record.notes
    assert not any(c.component_type in ("rider", "fixed", "demand") for c in record.components)
    assert not any("total" in c.component_name.lower() for c in record.components)


def test_ntpcb11_wholesale_not_included():
    record = NTPCB11__record()
    assert record.components[0].charge_value != 0.0423
    assert "Wholesale" not in record.tariff_name
    edit = lambda n, t: t.replace("Heating - Retail", "Heating - Other")
    with pytest.raises(ntpc._Reject):
        NTPCB11__record(rate_edit=edit)


def test_ntpcb11_changed_rate_value_flows_through_and_extra_line_rejects():
    record = NTPCB11__record(rate_edit=lambda n, t: t.replace("6.30 ¢/kWh", "6.50 ¢/kWh"))
    assert record.components[0].charge_value == 0.065
    with pytest.raises(ntpc._Reject):
        NTPCB11__record(rate_edit=lambda n, t: t.replace("Demand Charge: N/A\nEnergy Charge: Interruptible Energy 6.30",
                                                 "Demand Charge: N/A\nGRA Shortfall Rider: 10.40 ¢/kWh\n"
                                                 "Energy Charge: Interruptible Energy 6.30"))


def test_ntpcb11_terms_changed_quote_or_date_rejects():
    with pytest.raises(ntpc._Reject):
        NTPCB11__record(terms_edit=lambda n, t: t.replace("unlimited duration", "limited duration"))
    with pytest.raises(ntpc._Reject):
        NTPCB11__record(terms_edit=lambda n, t: t.replace("12 months notice", "6 months notice"))
    with pytest.raises(ntpc._Reject):
        NTPCB11__record(terms_edit=lambda n, t: t.replace("February 1, 2026", "February 1, 2027") if n == 1 else t)
    with pytest.raises(ntpc._Reject):
        NTPCB11__record(terms_edit=lambda n, t: "" if n == 59 else t)


def test_ntpcb11_scraper_adds_record_and_keeps_existing_62():
    records = NTPCB11__scrape()
    assert len(records) == 63
    by_name = {r.tariff_name: r for r in records}
    assert ntpc.INTERRUPTIBLE_NAME in by_name
    assert all(r.notes.startswith("Provenance: live_parsed") and r.confidence == "high" for r in records)
    baseline = NTPCB11__scrape(schedule_extra=False)
    assert len(baseline) == 62 and ntpc.INTERRUPTIBLE_NAME not in {r.tariff_name for r in baseline}
    assert [r for r in records if r.tariff_name != ntpc.INTERRUPTIBLE_NAME] == baseline


def test_ntpcb11_missing_or_changed_terms_omit_only_this_record():
    fx = NTPCB11__fx()
    for records in (NTPCB11__scrape(terms_error=True), NTPCB11__scrape(terms_pages=[]),
                    NTPCB11__scrape(terms_pages=NTPCB11__pages(fx["terms"], lambda n, t: t.replace("primarily", "partly")))):
        assert len(records) == 62
        assert ntpc.INTERRUPTIBLE_NAME not in {r.tariff_name for r in records}
        assert all(r.confidence == "high" for r in records)


# ======================================================================
# SaskEnergy service fees (batch 11)
# ======================================================================
from scrapers.utilities.saskenergy import FEE_URLS as SEB11_FEE_URLS, PAGE_URLS as SEB11_PAGE_URLS, SaskEnergyScraper as SEB11_SaskEnergyScraper
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch


SEB11_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "saskenergy.json"
SEB11_TODAY = date(2026, 10, 7)
SEB11_GAS_CODES = {"Res", "SC", "LC", "SI", "Res-DS", "SC-DS", "LC-DS"}


def SEB11__document():
    return json.loads(SEB11_FIXTURE.read_text(encoding="utf-8"))


def SEB11__fee_pages():
    return {key: page["text"] for key, page in SEB11__document()["fee_pages"].items()}


def SEB11__gas_pages():
    return {key: page["text"] for key, page in SEB11__document()["pages"].items()}


def SEB11__components(record):
    return {c.component_name: c for c in record.components}


def test_seb11_se_fees_values_units_and_date():
    record = SEB11_SaskEnergyScraper().parse_fees(SEB11__fee_pages(), SEB11_TODAY)
    assert record.tariff_code == "T&C-C" and record.utility_type == "gas"
    assert (record.customer_class, record.sub_class) == ("other", "service fees")
    assert record.effective_date == "2018-03-01"
    comps = SEB11__components(record)
    expected = {
        "Tenancy Change Fee - Business Hours": (30.0, "$/tenancy change"),
        "Tenancy Change Fee - After Hours": (30.0, "$/tenancy change"),
        "Service Activation Fee - Business Hours": (115.0, "$/activation"),
        "Service Activation Fee - After Hours": (140.0, "$/activation"),
        "Disconnection Fee - Business Hours": (80.0, "$/disconnection"),
        "Disconnection Fee - After Hours": (95.0, "$/disconnection"),
        "Missed Appointment Fee - Business Hours": (115.0, "$/missed appointment"),
        "Missed Appointment Fee - After Hours": (125.0, "$/missed appointment"),
        "Meter Dispute Fee - Business Hours": (50.0, "$/meter dispute"),
        "Equipment Service Fee - Business Hours": (100.0, "$/service call"),
        "Equipment Service Fee - After Hours": (120.0, "$/service call"),
        "Multi-Suite Verification Fee - Business Hours": (100.0, "$/verification"),
        "Multi-Suite Verification Fee - After Hours": (120.0, "$/verification"),
        "Thermocouple Fee - Business Hours": (125.0, "$/service call"),
        "Thermocouple Fee - After Hours": (150.0, "$/service call"),
        "Late Payment Charge": (0.02, "fraction/month"),
        "Return Payment Fee": (40.0, "$/returned payment"),
        "Dispute Resolution Fee": (50.0, "$/application"),
    }
    assert {name: (c.charge_value, c.charge_unit) for name, c in comps.items()} == expected
    assert "Meter Dispute Fee - After Hours" not in comps
    assert all(c.charge_unit != "$/month" for c in record.components)
    assert all(c.effective_date == "2018-03-01" for c in record.components)
    assert all(c.source_url == SEB11_FEE_URLS["appendix_c"] and "Appendix C" in c.source_detail for c in record.components)
    after = [c for c in record.components if c.sub_component == "after hours"]
    assert len(after) == 7 and all("Conditional alternative" in c.notes for c in after)
    assert "26.82%" in comps["Late Payment Charge"].notes


def test_seb11_se_fees_require_current_appendix_date():
    pages = SEB11__fee_pages()
    pages["appendix_c"] = pages["appendix_c"].replace("EFFECTIVE March 1, 2018", "")
    assert SEB11_SaskEnergyScraper().parse_fees(pages, SEB11_TODAY) is None
    pages = SEB11__fee_pages()
    pages["appendix_c"] = pages["appendix_c"].replace("March 1, 2018", "March 1, 2030")
    assert SEB11_SaskEnergyScraper().parse_fees(pages, SEB11_TODAY) is None
    pages = SEB11__fee_pages()
    pages.pop("appendix_c")
    assert SEB11_SaskEnergyScraper().parse_fees(pages, SEB11_TODAY) is None
    pages = SEB11__fee_pages()
    pages.pop("fees")
    assert SEB11_SaskEnergyScraper().parse_fees(pages, SEB11_TODAY) is None


def test_seb11_se_fees_appendix_mismatch_drops_only_that_fee():
    pages = SEB11__fee_pages()
    assert "Disconnection Fee All Rate Classifications All Rate Classifications $80 $95" in pages["appendix_c"]
    pages["appendix_c"] = pages["appendix_c"].replace("$80 $95", "$85 $95")
    comps = SEB11__components(SEB11_SaskEnergyScraper().parse_fees(pages, SEB11_TODAY))
    assert not any(name.startswith("Disconnection Fee") for name in comps)
    assert comps["Service Activation Fee - After Hours"].charge_value == 140.0
    pages = SEB11__fee_pages()
    pages["appendix_c_cont"] = pages["appendix_c_cont"].replace("$40.00", "$45.00")
    comps = SEB11__components(SEB11_SaskEnergyScraper().parse_fees(pages, SEB11_TODAY))
    assert "Return Payment Fee" not in comps and "Dispute Resolution Fee" in comps


def test_seb11_se_fees_class_specific_values_fail_closed():
    pages = SEB11__fee_pages()
    pages["fees"] = pages["fees"].replace("$115 $115 $140 $140", "$115 $120 $140 $140")
    comps = SEB11__components(SEB11_SaskEnergyScraper().parse_fees(pages, SEB11_TODAY))
    assert not any(name.startswith("Service Activation Fee") for name in comps)
    assert "Missed Appointment Fee - Business Hours" in comps


def test_seb11_se_gas_parse_pages_unchanged():
    records = SEB11_SaskEnergyScraper().parse_pages(SEB11__gas_pages(), SEB11_TODAY)
    assert {record.tariff_code for record in records} == SEB11_GAS_CODES


def test_seb11_se_scrape_appends_live_fee_record():
    responses = {SEB11_PAGE_URLS[key]: value for key, value in SEB11__gas_pages().items()}
    responses.update({SEB11_FEE_URLS[key]: value for key, value in SEB11__fee_pages().items()})
    scraper = SEB11_SaskEnergyScraper()
    with patch.object(scraper, "fetch_page", side_effect=lambda url: responses[url]),\
            patch.object(SEB11_SaskEnergyScraper, "_page_text", staticmethod(lambda html: html)):
        records = {record.tariff_code: record for record in scraper.scrape()}
    assert set(records) == SEB11_GAS_CODES | {"T&C-C"}
    assert "live_parsed" in records["T&C-C"].notes and "seed_fallback" not in records["T&C-C"].notes


def test_seb11_se_fee_fetch_failure_keeps_gas_records():
    responses = {SEB11_PAGE_URLS[key]: value for key, value in SEB11__gas_pages().items()}
    scraper = SEB11_SaskEnergyScraper()
    with patch.object(scraper, "fetch_page", side_effect=lambda url: responses[url]),\
            patch.object(SEB11_SaskEnergyScraper, "_page_text", staticmethod(lambda html: html)):
        records = {record.tariff_code for record in scraper.scrape()}
    assert records == SEB11_GAS_CODES


# ======================================================================
# OEB Tariff of Rates and Charges parser (Ontario batch 1)
# ======================================================================

"""Pending tests for scrapers.utils.oeb_tariff (OEB Tariff of Rates and Charges parser)."""

import json
from pathlib import Path

import pytest

from scrapers.utils.oeb_tariff import (
    build_demand_records,
    class_loss_factors,
    classify_classification,
    normalize_tariff_text,
    parse_tariff_pages,
    parse_tariff_zones,
)
from scrapers.utils.parsing import DocumentPage

OEBT_FIXTURES = Path(__file__).resolve().parent / "fixtures"
OEBT_TODAY = "2026-10-07"


def OEBT_load(name):
    data = json.loads((OEBT_FIXTURES / f"oeb_tariff_{name}.json").read_text(encoding="utf-8"))
    return data, [DocumentPage(p["page"], p["text"]) for p in data["pages"]]


def OEBT_mutate(pages, old, new, count=1):
    hits = sum(p.text.count(old) for p in pages)
    assert hits >= count, old
    return [DocumentPage(p.page_number, p.text.replace(old, new)) for p in pages]


def OEBT_charge(cls, label_start, kind=None):
    found = [c for c in cls.charges if c.label.startswith(label_start) and (kind is None or c.kind == kind)]
    assert len(found) == 1, (label_start, [c.label for c in cls.charges])
    return found[0]


def OEBT_record(records, code):
    found = [r for r in records if r.tariff_code == code]
    assert len(found) == 1, (code, [r.tariff_code for r in records])
    return found[0]


def OEBT_comp(rec, name, unit=None):
    found = [c for c in rec.components if c.component_name == name and (unit is None or c.charge_unit == unit)]
    assert len(found) == 1, (name, [c.component_name for c in rec.components])
    return found[0]


def OEBT_toronto_sheet(today=OEBT_TODAY):
    data, pages = OEBT_load("toronto")
    return parse_tariff_pages(pages, data["url"], today)


def OEBT_ottawa_sheet(today=OEBT_TODAY):
    data, pages = OEBT_load("ottawa")
    return parse_tariff_pages(pages, data["url"], today)


def OEBT_alectra_zone(zone, today=OEBT_TODAY, pages=None):
    data, fixture_pages = OEBT_load("alectra")
    return parse_tariff_pages(pages or fixture_pages, data["url"], today, rate_zone=zone)


# ─── Fixture provenance ──────────────────────────────────────────

@pytest.mark.parametrize("name,case", [
    ("toronto", "EB-2025-0006"), ("ottawa", "EB-2024-0115"), ("alectra", "EB-2025-0055")])
def test_oebt_fixture_metadata(name, case):
    data, pages = OEBT_load(name)
    assert data["url"].startswith("https://www.rds.oeb.ca/CMWebDrawer/Record/")
    assert data["case_number"] == case
    assert data["retrieved"] == "2026-10-07"
    assert data["effective_date"] == "2026-01-01"
    assert pages and all(p.text for p in pages)


# ─── Toronto Hydro ───────────────────────────────────────────────

def test_oebt_toronto_header():
    sheet = OEBT_toronto_sheet()
    assert sheet.errors == []
    assert sheet.distributor == "Toronto Hydro-Electric System Limited"
    assert sheet.rate_zone is None
    assert sheet.effective_date == sheet.implementation_date == "2026-01-01"
    assert sheet.case_number == "EB-2025-0006"
    assert sheet.issued_date == "2025-12-11"


def test_oebt_toronto_classes_and_thresholds():
    sheet = OEBT_toronto_sheet()
    names = [c.name for c in sheet.classifications]
    for expected in ("GENERAL SERVICE LESS THAN 50 KW", "GENERAL SERVICE 50 TO 999 KW",
                     "GENERAL SERVICE 1,000 TO 4,999 KW", "LARGE USE"):
        assert expected in names
    gs = sheet.classification("GENERAL SERVICE 50 TO 999 KW")
    assert (gs.demand_min_kw, gs.demand_max_kw) == (50, 1000)
    assert "bulk metered residential apartment buildings" in gs.eligibility
    assert (sheet.classification("GENERAL SERVICE 1,000 TO 4,999 KW").demand_min_kw,
            sheet.classification("GENERAL SERVICE 1,000 TO 4,999 KW").demand_max_kw) == (1000, 5000)
    lu = sheet.classification("LARGE USE")
    assert (lu.demand_min_kw, lu.demand_max_kw) == (5000, None)


def test_oebt_toronto_gs_50_999_values_and_units():
    gs = OEBT_toronto_sheet().classification("GENERAL SERVICE 50 TO 999 KW")
    service = OEBT_charge(gs, "Service Charge")
    assert (service.value, service.unit, service.kind, service.period) == (64.30, "$/30 days", "service", "30 days")
    dist = OEBT_charge(gs, "Distribution Volumetric Rate")
    assert (dist.value, dist.unit, dist.kind) == (10.5170, "$/kVA", "distribution")
    net = [c for c in gs.find("transmission_network") if not c.conditional]
    assert [(c.value, c.unit) for c in net] == [(4.4306, "$/kW")]
    conn = [c for c in gs.find("transmission_connection") if not c.conditional]
    assert [(c.value, c.unit) for c in conn] == [(2.8938, "$/kW")]
    ev = [c for c in gs.charges if "EV CHARGING" in c.label]
    assert {c.value for c in ev} == {0.7532, 0.4919} and all(c.conditional for c in ev)
    excess = OEBT_charge(gs, "Rate Rider for Disposition of Excess Expansion Deposits")
    assert (excess.value, excess.unit, excess.kind, excess.end_date) == (-0.0472, "$/kVA", "rider", "2029-12-31")
    ga = OEBT_charge(gs, "Rate Rider for Disposition of Global Adjustment Account")
    assert (ga.unit, ga.conditional) == ("$/kWh", True) and "non-RPP" in ga.condition
    wms = OEBT_charge(gs, "Wholesale Market Service Rate")
    assert (wms.kind, wms.value, wms.unit, wms.section) == ("regulatory", 0.0041, "$/kWh", "regulatory")


def test_oebt_toronto_large_use_and_allowances():
    sheet = OEBT_toronto_sheet()
    lu = sheet.classification("LARGE USE")
    assert OEBT_charge(lu, "Service Charge").value == 4843.52
    assert OEBT_charge(lu, "Distribution Volumetric Rate").value == 9.4416
    assert [c.value for c in lu.find("transmission_network")] == [4.8799]
    assert [c.value for c in lu.find("transmission_connection")] == [3.2117]
    allowance = [a for a in sheet.allowances if a.label.startswith("Transformer Allowance")]
    assert [(a.value, a.unit) for a in allowance] == [(-0.62, "$/kVA")]
    assert any(a.unit == "%" and a.value == -1.0 for a in sheet.allowances)
    assert [lf.value for lf in sheet.loss_factors] == [1.0295, 1.0172, 1.0192, 1.0070]


def test_oebt_toronto_records():
    records = build_demand_records(OEBT_toronto_sheet(), "Toronto Hydro")
    assert sorted(r.tariff_code for r in records) == ["GS 1,000-4,999 kW", "GS 50-999 kW", "LU"]
    gs = OEBT_record(records, "GS 50-999 kW")
    assert (gs.customer_class, gs.rate_structure, gs.province, gs.effective_date) == (
        "commercial", "demand", "ON", "2026-01-01")
    assert (gs.demand_min_kw, gs.demand_max_kw) == (50, 1000)
    assert "Ontario Electricity Market Price" in gs.notes and "HOEP" in gs.notes and "Global Adjustment" in gs.notes
    assert gs.pricing_method == "market_based" and "250,000 kilowatt hours" in gs.notes
    fixed = OEBT_comp(gs, "Service Charge")
    assert (fixed.component_type, fixed.charge_value, fixed.charge_unit) == ("fixed", 64.30, "$/30 days")
    dist = OEBT_comp(gs, "Distribution Volumetric Rate")
    assert (dist.component_type, dist.charge_unit, dist.demand_unit) == ("demand", "$/kVA", "kVA")
    allowance = OEBT_comp(gs, "Transformer Allowance for Ownership")
    assert (allowance.component_type, allowance.charge_value) == ("rebate", -0.62)
    assert allowance.notes.startswith("Conditional")
    market = [c for c in gs.components if c.market_reference]
    assert [(c.component_type, c.charge_value, c.effective_date) for c in market] == [("energy", None, "2026-01-01")]
    for c in gs.components:
        if c.market_reference:
            continue
        assert c.source_url == gs.source_url and c.effective_date == "2026-01-01"
        assert c.source_detail.startswith("PDF page ") and "EB-2025-0006" in c.source_detail
        assert "total" not in c.component_name.casefold()
    riders = [c for c in gs.components if c.component_type == "rider"]
    assert riders and all(c.end_date for c in riders)
    assert OEBT_record(records, "LU").customer_class == "industrial"
    assert "> 5,000 kW" in OEBT_record(records, "LU").notes and "< 5,000 kW" in gs.notes


# ─── Hydro Ottawa ────────────────────────────────────────────────

def test_oebt_ottawa_header_and_classes():
    sheet = OEBT_ottawa_sheet()
    assert sheet.errors == []
    assert sheet.distributor == "Hydro Ottawa Limited"
    assert (sheet.effective_date, sheet.implementation_date) == ("2026-01-01", "2026-06-01")
    assert sheet.case_number == "EB-2024-0115"
    gs = sheet.classification("GENERAL SERVICE 50 TO 1,499 KW")
    assert (gs.demand_min_kw, gs.demand_max_kw) == (50, 1500)
    assert any("ninety percent (90%)" in n for n in gs.notes)
    assert any(n.startswith("* In accordance") for n in gs.notes)


def test_oebt_ottawa_values_split_digits_and_wrapped_riders():
    sheet = OEBT_ottawa_sheet()
    gs = sheet.classification("GENERAL SERVICE 50 TO 1,499 KW")
    service = OEBT_charge(gs, "Service Charge")
    assert (service.value, service.unit) == (200.00, "$/month")
    assert OEBT_charge(gs, "Distribution Volumetric Rate").value == 7.6543
    assert OEBT_charge(gs, "Low Voltage Service Rate").kind == "low_voltage"
    group2 = OEBT_charge(gs, "Rate Rider for disposition of Group 2")
    assert (group2.value, group2.unit, group2.end_date) == (-0.2634, "$/kW", "2026-12-31")
    assert [c.value for c in gs.find("transmission_network", conditional=False)] == [4.5787]
    assert [c.value for c in gs.find("transmission_connection", conditional=False)] == [2.5918]
    lu = sheet.classification("LARGE USE")
    assert OEBT_charge(lu, "Service Charge").value == 14946.93
    assert [c.value for c in lu.find("transmission_network")] == [5.334]
    assert OEBT_charge(sheet.classification("GENERAL SERVICE 1,500 TO 4,999 KW"), "Service Charge").value == 4126.75


def test_oebt_ottawa_records():
    records = build_demand_records(OEBT_ottawa_sheet(), "Hydro Ottawa")
    assert sorted(r.tariff_code for r in records) == ["GS 1,500-4,999 kW", "GS 50-1,499 kW", "LU"]
    gs = OEBT_record(records, "GS 50-1,499 kW")
    assert "implemented 2026-06-01" in gs.notes
    pma = OEBT_comp(gs, "Primary Metering Allowance for Transformer Losses - applied to measured demand & energy")
    assert (pma.charge_value, pma.charge_unit) == (-1.0, "%") and pma.notes.startswith("Conditional")
    foregone = [c for c in gs.components if "Foregone" in c.component_name]
    assert {c.end_date for c in foregone} == {"2027-05-31"}


def test_oebt_ottawa_future_implementation_rejected():
    sheet = OEBT_ottawa_sheet(today="2026-03-01")
    assert any("Implementation date" in e for e in sheet.errors)
    assert build_demand_records(sheet, "Hydro Ottawa") == []


# ─── Alectra ─────────────────────────────────────────────────────

def test_oebt_alectra_zones():
    data, pages = OEBT_load("alectra")
    zones = parse_tariff_zones(pages, data["url"], OEBT_TODAY)
    assert set(zones) == {"Brampton Rate Zone", "Enersource Rate Zone", "Horizon Utilities Rate Zone",
                          "Guelph Rate Zone", "PowerStream Rate Zone"}
    counts = {zone: len(build_demand_records(sheet, "Alectra Utilities")) for zone, sheet in zones.items()}
    assert counts == {"Brampton Rate Zone": 3, "Enersource Rate Zone": 3, "Horizon Utilities Rate Zone": 3,
                      "Guelph Rate Zone": 3, "PowerStream Rate Zone": 2}
    for sheet in zones.values():
        assert sheet.errors == [] and sheet.case_number == "EB-2025-0055"


def test_oebt_alectra_requires_zone_selection():
    data, pages = OEBT_load("alectra")
    sheet = parse_tariff_pages(pages, data["url"], OEBT_TODAY)
    assert any("Multiple rate zones" in e for e in sheet.errors)
    assert build_demand_records(sheet, "Alectra Utilities") == []


def test_oebt_alectra_brampton_values_and_class_specific_allowance():
    sheet = OEBT_alectra_zone("Brampton Rate Zone")
    gs = sheet.classification("GENERAL SERVICE 50 TO 699 KW")
    assert (gs.demand_min_kw, gs.demand_max_kw) == (50, 700)
    assert OEBT_charge(gs, "Service Charge").value == 157.66
    assert OEBT_charge(gs, "Distribution Volumetric Rate").value == 3.5709
    cos = [c for c in gs.charges if c.term]
    assert cos and all(c.end_date is None and c.kind == "rider" for c in cos)
    nonwmp = OEBT_charge(gs, "Rate Rider for Disposition of Deferral/Variance Accounts (2026) - effective until "
                        "December 31, 2026 Applicable only for Non-Wholesale")
    assert (nonwmp.value, nonwmp.conditional) == (-0.2641, True)
    records = build_demand_records(sheet, "Alectra Utilities")
    gs_rec = OEBT_record(records, "GS 50-699 kW")
    assert gs_rec.sub_class == "Brampton Rate Zone"
    allowances = [c for c in gs_rec.components if c.component_type == "rebate"]
    assert [(c.charge_value, c.charge_unit) for c in allowances] == [(-0.6840, "$/kW")]
    assert [c.charge_value for c in OEBT_record(records, "GS 700-4,999 kW").components
            if c.component_type == "rebate"] == [-0.8515]
    assert not [c for c in OEBT_record(records, "LU").components if c.component_type == "rebate"]


def test_oebt_alectra_powerstream_interval_alternatives():
    sheet = OEBT_alectra_zone("PowerStream Rate Zone")
    gs = sheet.classification("GENERAL SERVICE 50 TO 4,999 KW")
    standard = [c for c in gs.find("transmission_network") if not c.conditional]
    assert [c.value for c in standard] == [4.5071]
    interval = [c for c in gs.charges if "Interval Metered" in c.label]
    assert len(interval) == 4 and all(c.conditional for c in interval)
    wrapped = [c for c in gs.charges if c.label == "Rate Rider for Disposition of Deferral/Variance Accounts "
               "(2026) - effective until December 31, 2026"]
    assert [(c.value, c.unit, c.conditional) for c in wrapped] == [(0.1270, "$/kW", False)]


def test_oebt_alectra_interval_only_transmission_is_class_rate():
    sheet = OEBT_alectra_zone("Guelph Rate Zone")
    gs = sheet.classification("GENERAL SERVICE 1,000 TO 4,999 KW")
    assert [(c.value, c.conditional) for c in gs.find("transmission_network")] == [(4.5377, False), (0.7714, True)]
    assert [c.value for c in gs.find("transmission_connection", conditional=False)] == [3.1058]
    lu = OEBT_record(build_demand_records(sheet, "Alectra Utilities"), "LU")
    assert OEBT_comp(lu, "Retail Transmission Rate - Network Service Rate - Interval Metered").charge_value == 5.4797
    horizon = build_demand_records(OEBT_alectra_zone("Horizon Utilities Rate Zone"), "Alectra Utilities")
    assert OEBT_record(horizon, "LARGE-USE-WITH-DEDICATED-ASSETS").customer_class == "industrial"


# ─── Fail-closed behaviour ───────────────────────────────────────

def test_oebt_missing_distribution_line_rejects_only_that_class():
    data, pages = OEBT_load("toronto")
    pages = OEBT_mutate(pages, "Distribution Volumetric Rate $/kVA 10.5170 (per 30 days)\n", "")
    sheet = parse_tariff_pages(pages, data["url"], OEBT_TODAY)
    records = build_demand_records(sheet, "Toronto Hydro")
    assert sorted(r.tariff_code for r in records) == ["GS 1,000-4,999 kW", "LU"]
    assert "Distribution Volumetric Rate" in sheet.rejections["GENERAL SERVICE 50 TO 999 KW"]


@pytest.mark.parametrize("old,new", [
    ("Retail Transmission Rate - Network Service Rate $/kW 4.4306", "Retail Transmission Rate - Network Service Rate $/kWh 4.4306"),
    ("Distribution Volumetric Rate $/kVA 10.5170", "Distribution Volumetric Rate $/kWh 10.5170"),
    ("Service Charge $ 64.30", "Service Charge $/kW 64.30"),
    ("Retail Transmission Rate - Line and Transformation Connection Service Rate $/kW 2.8938 (per 30 days)\n", ""),
])
def test_oebt_unit_mutation_or_missing_transmission_rejected(old, new):
    data, pages = OEBT_load("toronto")
    sheet = parse_tariff_pages(OEBT_mutate(pages, old, new), data["url"], OEBT_TODAY)
    codes = [r.tariff_code for r in build_demand_records(sheet, "Toronto Hydro")]
    assert "GS 50-999 kW" not in codes and "LU" in codes
    assert "GENERAL SERVICE 50 TO 999 KW" in sheet.rejections


def test_oebt_missing_effective_date_rejects_all():
    data, pages = OEBT_load("ottawa")
    pages = OEBT_mutate(pages, "Effective Date January 1, 2026", "Date January 1, 2026", count=2)
    sheet = parse_tariff_pages(pages, data["url"], OEBT_TODAY)
    assert "Effective date not found" in sheet.errors
    assert build_demand_records(sheet, "Hydro Ottawa") == []


def test_oebt_future_effective_date_rejected():
    sheet = OEBT_toronto_sheet(today="2025-12-15")
    assert any("in the future" in e for e in sheet.errors)
    assert build_demand_records(sheet, "Toronto Hydro") == []


def test_oebt_inconsistent_effective_dates_rejected():
    data, pages = OEBT_load("toronto")
    pages = [DocumentPage(p.page_number, p.text.replace("January 1, 2026", "May 1, 2026", 1))
             if i == 0 else p for i, p in enumerate(pages)]
    sheet = parse_tariff_pages(pages, data["url"], OEBT_TODAY)
    assert any("Inconsistent effective" in e for e in sheet.errors)
    assert build_demand_records(sheet, "Toronto Hydro") == []


def test_oebt_excluded_classes_never_built():
    for sheet in (OEBT_toronto_sheet(), OEBT_ottawa_sheet(), OEBT_alectra_zone("Brampton Rate Zone")):
        excluded = [c.name for c in sheet.classifications
                    if c.name.upper().startswith(("STREET LIGHTING", "STANDBY", "UNMETERED", "MICROFIT"))]
        assert excluded
        assert build_demand_records(sheet, "X", classes=tuple(excluded)) == []
        built = {r.tariff_code for r in build_demand_records(sheet, "X")}
        assert not any("LIGHT" in code or "STANDBY" in code for code in built)


def test_oebt_expired_riders_omitted_with_note():
    sheet = OEBT_toronto_sheet(today="2027-01-15")
    gs = OEBT_record(build_demand_records(sheet, "Toronto Hydro"), "GS 50-999 kW")
    ends = {c.end_date for c in gs.components if c.end_date}
    assert ends and min(ends) >= "2027-01-15"
    assert "Expired riders omitted" in gs.notes


def test_oebt_explicit_subset_selection():
    records = build_demand_records(OEBT_toronto_sheet(), "Toronto Hydro", classes=("LARGE USE",))
    assert [r.tariff_code for r in records] == ["LU"]


def test_oebt_classify_standard_classes():
    cats = {c.name: classify_classification(c) for c in OEBT_toronto_sheet().classifications}
    assert cats["RESIDENTIAL"] == "residential"
    assert cats["GENERAL SERVICE LESS THAN 50 KW"] == "gs_energy"
    assert cats["GENERAL SERVICE 50 TO 999 KW"] == "gs_demand"
    assert cats["LARGE USE"] == "large_use"
    assert all(v == "excluded" for k, v in cats.items() if k.startswith(("STREET", "STANDBY", "UNMETERED")))


# ─── Hydro One Networks (EB-2025-0030) ───────────────────────────

OEBT_PETERBOROUGH = "Former Peterborough Distribution Inc. Service Area"
OEBT_ORILLIA = "Former Orillia Power Distribution Corporation Service Area"


def OEBT_hydro_one_pages(key="raw_pages"):
    data = json.loads((OEBT_FIXTURES / "oeb_tariff_hydro_one.json").read_text(encoding="utf-8"))
    return data, [DocumentPage(p["page_number"], p["text"]) for p in data[key]]


def OEBT_hydro_one_zones(key="raw_pages", today=OEBT_TODAY, pages=None):
    data, fixture_pages = OEBT_hydro_one_pages(key)
    return parse_tariff_zones(pages or fixture_pages, data["url"], today)


def OEBT_by_code(sheet, code):
    found = [c for c in sheet.classifications if c.code == code]
    assert len(found) == 1, (code, [c.code for c in sheet.classifications])
    return found[0]


def test_oebt_hydro_one_fixture_metadata():
    data, pages = OEBT_hydro_one_pages()
    assert data["url"].startswith("https://www.hydroone.com/") and data["url"].endswith("20251223.PDF")
    assert (data["case_number"], data["effective_date"]) == ("EB-2025-0030", "2026-01-01")
    assert len(pages) == len(data["pages"]) == 58


def test_oebt_hydro_one_zones_and_headers():
    zones = OEBT_hydro_one_zones()
    assert set(zones) == {None, OEBT_PETERBOROUGH, OEBT_ORILLIA}
    for sheet in zones.values():
        assert sheet.errors == []
        assert sheet.distributor == "Hydro One Networks Inc."
        assert (sheet.effective_date, sheet.implementation_date) == ("2026-01-01", "2026-01-01")
        assert sheet.case_number == "EB-2025-0030" and sheet.issued_date == "2025-12-23"
    assert zones[None].rate_zone is None and zones[OEBT_PETERBOROUGH].rate_zone == OEBT_PETERBOROUGH
    assert any("Multiple rate zones" in e for e in parse_tariff_pages(OEBT_hydro_one_pages()[1], "u", OEBT_TODAY).errors)


def test_oebt_hydro_one_main_codes_and_categories():
    sheet = OEBT_hydro_one_zones()[None]
    cats = {c.code: classify_classification(c) for c in sheet.classifications if c.code}
    assert cats == {
        "UR": "residential", "R1": "residential", "R2": "residential", "AUR": "residential", "AR": "residential",
        "UGe": "gs_energy", "GSe": "gs_energy", "AUGe": "gs_energy", "AGSe": "gs_energy",
        "UGd": "gs_demand", "GSd": "gs_demand", "AUGd": "gs_demand", "AGSd": "gs_demand",
        "DGen": "excluded", "ST": "sub_transmission",
    }
    assert OEBT_by_code(sheet, "R1").name == "MEDIUM DENSITY - R1"
    assert OEBT_by_code(sheet, "UR").group == "RESIDENTIAL SERVICE CLASSIFICATIONS"
    assert "year-round residential property" in OEBT_by_code(sheet, "UR").eligibility
    assert OEBT_by_code(sheet, "AUGd").group == "ACQUIRED GENERAL SERVICE CLASSIFICATIONS"
    for c in sheet.classifications:
        assert not [u for u in c.unparsed if "$" in u], (c.name, c.unparsed)
    excluded = {c.name: classify_classification(c) for c in sheet.classifications if not c.code}
    assert set(excluded.values()) == {"excluded"}


def test_oebt_hydro_one_wrapped_labels_and_see_notes():
    sheet = OEBT_hydro_one_zones()[None]
    ur = OEBT_by_code(sheet, "UR")
    assert OEBT_charge(ur, "Service Charge").value == 43.70 and not ur.find("distribution")
    ga = OEBT_charge(ur, "Rate Rider for Disposition of Global Adjustment Account")
    assert (ga.value, ga.unit, ga.end_date, ga.conditional) == (0.0121, "$/kWh", "2026-12-31", True)
    assert "see Note" not in ga.label and "non-RPP" in ga.condition
    cbr = OEBT_charge(ur, "Rate Rider for Disposition of Capacity Based Recovery Account")
    assert cbr.label.endswith("(Applicable only to Non-WMP Class B Customers)") and cbr.value == -0.0006
    assert [c.value for c in ur.find("transmission_network")] == [0.0141]
    st = OEBT_by_code(sheet, "ST")
    hvds = OEBT_charge(st, "Facility Charge for connection to high-voltage")
    assert hvds.label.endswith("delivery High Voltage Distribution Station") and hvds.value == 3.698


def test_oebt_hydro_one_two_rider_sets_and_duplicate_names():
    sheet = OEBT_hydro_one_zones()[None]
    gse = OEBT_by_code(sheet, "GSe")
    esm = [c for c in gse.charges if c.label.startswith("Rate Rider for Disposition of Earning Sharing")]
    assert [(c.value, c.unit, c.conditional) for c in esm] == [(-1.12, "$/month", False), (-0.0028, "$/kWh", False)]
    chapleau = [c for c in gse.charges if "Applicable to former Chapleau PUC customers only" in c.label]
    assert [c.value for c in chapleau] == [0.0015, -0.0010, 0.0112]
    assert all(c.conditional and "former Chapleau" in c.condition for c in chapleau)
    standard_ga = OEBT_charge(gse, "Rate Rider for Disposition of Global Adjustment Account (2026) (Not applicable")
    assert "Chapleau" not in standard_ga.condition
    riders = [c for c in gse.charges if c.kind == "rider"]
    assert len(riders) == 9 and all(c.end_date == "2026-12-31" for c in riders)


def test_oebt_hydro_one_normalized_text_tolerates_dropped_rider_tails():
    raw = OEBT_by_code(OEBT_hydro_one_zones()[None], "GSe")
    norm = OEBT_by_code(OEBT_hydro_one_zones("pages")[None], "GSe")
    assert [(c.value, c.unit, c.kind) for c in raw.charges] == [(c.value, c.unit, c.kind) for c in norm.charges]
    missing = [c for c in norm.charges if c.kind == "rider" and c.end_date is None]
    assert len(missing) == 3
    assert sum("was not found in the extracted text" in n for n in norm.notes) == 3
    assert not any("was not found" in n for n in raw.notes)
    assert normalize_tariff_text("a 1\nx\nx\nx\nb 2") == "a 1\nx\nx\nx b 2"


def test_oebt_hydro_one_residential_alternatives_and_notes():
    sheet = OEBT_hydro_one_zones()[None]
    r2 = OEBT_by_code(sheet, "R2")
    services = [(c.label, c.value, c.conditional) for c in r2.find("service")]
    assert services == [("Service Charge - applicable to year-round low-density customers", 151.14, False),
                        ("Service Charge - applicable to Seasonal customers", 92.43, True)]
    rrrp = OEBT_charge(r2, "Rural or Remote Rate Protection (RRRP) credit")
    assert (rrrp.value, rrrp.unit, rrrp.conditional) == (-60.50, "$/month", True)
    for code in ("R1", "R2"):
        notes = " ".join(OEBT_by_code(sheet, code).notes)
        assert "do not reflect the impact of the Distribution Rate Protection" in notes
        assert "$42.88" in notes and "not applied or computed" in notes
    assert not any("42.88" in n for n in OEBT_by_code(sheet, "UR").notes)
    assert not [c for c in OEBT_by_code(sheet, "UR").charges if c.value == 42.88]


def test_oebt_hydro_one_loss_factors_by_code():
    sheet = OEBT_hydro_one_zones()[None]
    assert [(lf.label, lf.value) for lf in class_loss_factors(sheet, OEBT_by_code(sheet, "UGd"))] == [
        ("General Service - UGd", 1.050)]
    assert [lf.value for lf in class_loss_factors(sheet, OEBT_by_code(sheet, "UR"))] == [1.057]
    assert [lf.value for lf in class_loss_factors(sheet, OEBT_by_code(sheet, "AUR"))] == [1.043]
    assert [lf.value for lf in class_loss_factors(sheet, OEBT_by_code(sheet, "ST"))] == [1.000, 1.028, 1.006, 1.034]
    assert len(sheet.loss_factors) == 21
    peterborough = OEBT_hydro_one_zones()[OEBT_PETERBOROUGH]
    assert [lf.value for lf in peterborough.loss_factors] == [1.0548, 1.0172, 1.0443, 1.0070]


def test_oebt_hydro_one_main_demand_records():
    sheet = OEBT_hydro_one_zones()[None]
    records = build_demand_records(sheet, "Hydro One Networks Inc.")
    assert [r.tariff_code for r in records] == ["UGd", "GSd", "ST", "AUGd", "AGSd"]
    assert sheet.rejections == {}
    ugd = OEBT_record(records, "UGd")
    assert (ugd.customer_class, ugd.demand_min_kw, ugd.demand_max_kw, ugd.sub_class) == ("commercial", 50, None, None)
    assert OEBT_comp(ugd, "Service Charge").charge_value == 96.47
    dist = OEBT_comp(ugd, "Distribution Volumetric Rate")
    assert (dist.charge_value, dist.charge_unit, dist.component_type) == (13.1059, "$/kW", "demand")
    ev = OEBT_comp(ugd, "Retail Transmission Rate - Network Service Rate - EV CHARGING")
    assert ev.charge_value == 0.6952 and ev.notes.startswith("Conditional")
    allowance = OEBT_comp(ugd, "Customer-Supplied Transformation Allowance - Demand Billed - per kW of billing demand/month")
    assert (allowance.charge_value, allowance.component_type) == (-0.60, "rebate")
    assert not [c for c in ugd.components if "Energy Billed" in c.component_name]
    assert "General Service - UGd 1.05" in ugd.notes and "Residential - UR" not in ugd.notes
    gsd = OEBT_record(records, "GSd")
    assert sum("former Chapleau" in (c.notes or "") for c in gsd.components) == 3
    for rec in records:
        assert rec.effective_date == "2026-01-01" and "EB-2025-0030" in rec.notes
        assert all(c.source_detail.startswith("PDF page ") for c in rec.components if not c.market_reference)
        assert [c.charge_value for c in rec.components if c.market_reference] == [None]


def test_oebt_hydro_one_sub_transmission_load_path_only():
    sheet = OEBT_hydro_one_zones()[None]
    st = OEBT_record(build_demand_records(sheet, "Hydro One Networks Inc."), "ST")
    assert (st.customer_class, st.demand_min_kw, st.demand_max_kw) == ("industrial", 500, None)
    assert st.eligibility.startswith("Sub Transmission (ST) load path - Load which: is three-phase")
    assert "Embedded supply to Local Distribution Companies" not in st.eligibility
    assert "embedded-LDC supply path of the same class is excluded" in st.notes
    assert "never summed" in st.notes and "1% shall be added" in st.notes
    service = OEBT_comp(st, "Service Charge")
    assert (service.charge_value, service.notes) == (824.28, None)
    for name, value, unit in (
            ("Meter Charge (for Hydro One ownership)", 417.59, "$/month"),
            ("Local Transformation Charge (per transformer)", 200.00, "$/month"),
            ("Facility Charge for connection to Common ST Lines (44 kV to 13.8 kV)", 1.8196, "$/kW"),
            ("Facility Charge for connection to Specific ST Lines (44 kV to 13.8 kV)", 711.9546, "$/km"),
            ("Facility Charge for connection to low-voltage (< 13.8 kV secondary) Low Voltage Distribution Station",
             2.2187, "$/kW"),
            ("Retail Transmission Rate - Line Connection Service Rate", 0.7054, "$/kW"),
            ("Retail Transmission Rate - Transformation Connection Service Rate", 3.5764, "$/kW")):
        c = OEBT_comp(st, name)
        assert (c.charge_value, c.charge_unit) == (value, unit) and c.notes.startswith("Conditional"), name
    assert OEBT_comp(st, "Retail Transmission Rate - Network Service Rate").notes is None
    assert OEBT_comp(st, "Meter Charge (for Hydro One ownership)").sub_component == "meter_charge"
    assert not [c for c in st.components if "Tranformer Loss Allowance" in c.component_name]
    assert not [c for c in st.components if c.component_type == "demand" and c.sub_component == "distribution_volumetric"]


def test_oebt_hydro_one_st_without_load_path_rejected():
    data, pages = OEBT_hydro_one_pages()
    pages = OEBT_mutate(pages, "• Load which:", "• Customers which:")
    sheet = parse_tariff_zones(pages, data["url"], OEBT_TODAY)[None]
    codes = [r.tariff_code for r in build_demand_records(sheet, "Hydro One Networks Inc.")]
    assert "ST" not in codes and "UGd" in codes
    assert "load-path" in sheet.rejections["SUB TRANSMISSION - ST"]


def test_oebt_hydro_one_missing_ugd_distribution_rejects_only_ugd():
    data, pages = OEBT_hydro_one_pages()
    pages = OEBT_mutate(pages, "Distribution Volumetric Rate $/kW 13.1059\n", "")
    sheet = parse_tariff_zones(pages, data["url"], OEBT_TODAY)[None]
    codes = [r.tariff_code for r in build_demand_records(sheet, "Hydro One Networks Inc.")]
    assert codes == ["GSd", "ST", "AUGd", "AGSd"]
    assert "Distribution Volumetric Rate" in sheet.rejections["URBAN GENERAL SERVICE DEMAND BILLED - UGd"]


def test_oebt_hydro_one_code_selection_and_exclusions():
    sheet = OEBT_hydro_one_zones()[None]
    assert [r.tariff_code for r in build_demand_records(sheet, "H", classes=("UGd",))] == ["UGd"]
    assert build_demand_records(sheet, "H", classes=("DGen", "UNMETERED SCATTERED LOAD", "microFIT")) == []


def test_oebt_hydro_one_peterborough_and_orillia_records():
    zones = OEBT_hydro_one_zones()
    ptbo = build_demand_records(zones[OEBT_PETERBOROUGH], "Hydro One Networks Inc.")
    assert [r.tariff_code for r in ptbo] == ["GS 50-4,999 kW", "LU"]
    gs = OEBT_record(ptbo, "GS 50-4,999 kW")
    assert (gs.source_page, gs.demand_min_kw, gs.demand_max_kw, gs.customer_class) == (
        "PDF pages 37-38", 50, 5000, "commercial")
    assert OEBT_comp(gs, "Low Voltage Service Rate").charge_value == 0.3277
    assert OEBT_comp(gs, "Retail Transmission Rate - Network Service Rate").charge_value == 4.2798
    assert gs.tariff_name.startswith(OEBT_PETERBOROUGH)
    assert OEBT_record(ptbo, "LU").customer_class == "industrial"
    orillia = build_demand_records(zones[OEBT_ORILLIA], "Hydro One Networks Inc.")
    assert [r.tariff_code for r in orillia] == ["GS 50-4,999 kW"]
    assert OEBT_record(orillia, "GS 50-4,999 kW").source_page == "PDF pages 49-50"
    res = zones[OEBT_ORILLIA].classification("RESIDENTIAL")
    assert classify_classification(res) == "residential"
    smart = OEBT_charge(res, "Rate Rider for Smart Meter Incremental Revenue Requirement")
    assert (smart.value, smart.end_date) == (2.56, None) and "next cost-of-service" in smart.term
    assert classify_classification(zones[OEBT_ORILLIA].classification("STANDBY POWER")) == "excluded"


def test_oebt_hydro_one_future_date_rejected():
    zones = OEBT_hydro_one_zones(today="2025-12-31")
    for sheet in zones.values():
        assert any("in the future" in e for e in sheet.errors)
        assert build_demand_records(sheet, "Hydro One Networks Inc.") == []


# ─── Layout variants (20 more LDC tariffs) ───────────────────────

def OEBT_variant(key, pages=None, today=OEBT_TODAY):
    data = json.loads((OEBT_FIXTURES / "oeb_tariff_variants.json").read_text(encoding="utf-8"))["documents"][key]
    fixture_pages = [DocumentPage(p["page"], p["text"]) for p in data["pages"]]
    sheet = parse_tariff_pages(pages or fixture_pages, data["url"], today, rate_zone=data["rate_zone"] or "")
    return sheet, build_demand_records(sheet, key, today=today), fixture_pages


def test_oebt_variant_fixture_metadata():
    doc = json.loads((OEBT_FIXTURES / "oeb_tariff_variants.json").read_text(encoding="utf-8"))
    assert doc["retrieved"] == "2026-10-07" and "extract_tariff_pages" in doc["extraction"]
    assert len(doc["documents"]) == 15
    for data in doc["documents"].values():
        assert data["url"] == "https://www.rds.oeb.ca/CMWebDrawer/Record/" + str(data["record"]) + "/File/document"
        assert data["case_number"].startswith("EB-2025-") and data["purpose"]
        assert data["pages"] and all(p["text"] for p in data["pages"])


def test_oebt_enova_waterloo_north_size_split_transmission_alternatives():
    sheet, records, _ = OEBT_variant("enova_waterloo_north")
    assert sheet.rejections == {} and sheet.case_number is None
    gs = OEBT_record(records, "GS 50-4,999 kW")
    network = [c for c in gs.components if c.sub_component == "network_service"]
    assert {(c.charge_value, c.notes.split(":")[0]) for c in network if "EV CHARGING" not in c.component_name} == {
        (4.7623, "Conditional"), (4.7559, "Conditional")}
    small = OEBT_comp(gs, "Retail Transmission Rate - Network Service Rate - Interval Metered (less than 1,000 kW)")
    assert "demand less than 1,000 kW" in small.notes
    large = [c for c in gs.components if c.charge_value == 1.2948]
    assert len(large) == 1 and "demand 1,000 to 4,999 kW" in large[0].notes
    assert all(c.notes and c.notes.startswith("Conditional") for c in gs.components
               if c.component_type == "transmission")
    assert "no rate is inferred for non-interval-metered customers" in gs.notes
    assert "Gross Load Billing Note: The Billing Demand for Line and Transformation Connection" in gs.notes


def test_oebt_enova_size_split_requires_distinct_ranges():
    _, _, pages = OEBT_variant("enova_waterloo_north")
    pages = OEBT_mutate(pages, "Interval Metered (1,000 to 4,999 kW) $/kW 4.7559", "Interval Metered (less than 1,000 kW) $/kW 4.7559")
    sheet, records, _ = OEBT_variant("enova_waterloo_north", pages)
    assert records == [] and "Network Service Rate" in sheet.rejections["GENERAL SERVICE 50 TO 4,999 KW"]


def test_oebt_enwin_large_use_line_and_transformation_pair():
    sheet, records, _ = OEBT_variant("enwin")
    lu = OEBT_record(records, "LARGE-USE-REGULAR")
    assert (lu.customer_class, lu.demand_min_kw, lu.demand_max_kw) == ("industrial", 5000, None)
    line = [c for c in lu.components if c.sub_component == "line_connection"]
    transformation = [c for c in lu.components if c.sub_component == "transformation_connection"]
    assert [(c.charge_value, c.notes) for c in line] == [(1.0281, None)]
    assert [(c.charge_value, c.notes) for c in transformation] == [(2.56, None)]
    gs = OEBT_record(records, "GS 50-4,999 kW")
    assert (gs.demand_min_kw, gs.demand_max_kw) == (50, 5000)


def test_oebt_enwin_connection_pair_needs_both_parts():
    _, _, pages = OEBT_variant("enwin")
    pages = OEBT_mutate(pages, "Retail Transmission Rate - Transformation Connection Service Rate (see Gross Load Billing Note) $/kW 2.5600\n", "")
    sheet, records, _ = OEBT_variant("enwin", pages)
    assert "LARGE-USE-REGULAR" not in [r.tariff_code for r in records]
    assert "found 0" in sheet.rejections["LARGE USE - REGULAR"]


def test_oebt_enwin_dedicated_transformer_station_excluded():
    sheet, records, _ = OEBT_variant("enwin")
    dts = sheet.classification("DEDICATED TRANSFORMER STATION")
    assert classify_classification(dts) == "excluded"
    assert "not general facility service" in sheet.exclusions["DEDICATED TRANSFORMER STATION"]
    assert not [r for r in records if "DEDICATED" in r.tariff_name.upper()]
    assert build_demand_records(sheet, "ENWIN", classes=("DEDICATED TRANSFORMER STATION",)) == []


def test_oebt_london_co_generation_heading_separates_classes():
    sheet, records, _ = OEBT_variant("london")
    names = [c.name for c in sheet.classifications]
    assert "GENERAL SERVICE 1,000 TO 4,999 KW (CO-GENERATION)" in names
    cogen = sheet.classification("GENERAL SERVICE 1,000 TO 4,999 KW (CO-GENERATION)")
    assert classify_classification(cogen) == "excluded" and cogen.charges
    assert "co-generation" in sheet.exclusions[cogen.name]
    gs = OEBT_record(records, "GS 50-4,999 kW")
    assert [c.charge_value for c in gs.components if c.component_name == "Service Charge"] == [177.28]
    assert sheet.issued_date == "2026-03-19"
    assert not any("March 19, 2026" in t for c in sheet.classifications for t in c.unparsed)


def test_oebt_oakville_truncated_ev_label_and_open_class():
    sheet, records, _ = OEBT_variant("oakville")
    gs = OEBT_record(records, "GS 50-999 kW")
    assert (gs.demand_min_kw, gs.demand_max_kw) == (50, 1000)
    ev = OEBT_comp(gs, "Retail Transmission Rate - Line and Transformation Connection Service Rate - Interval Metered - EV")
    assert ev.charge_value == 0.4918 and "Electric Vehicle" in ev.notes
    standard = OEBT_comp(gs, "Retail Transmission Rate - Line and Transformation Connection Service Rate - Interval Metered")
    assert (standard.charge_value, standard.notes) == (2.8927, None)
    big = OEBT_record(records, "GS 1,000+ kW")
    assert classify_classification(sheet.classification("GENERAL SERVICE 1,000 KW AND GREATER")) == "gs_demand"
    assert (big.customer_class, big.demand_min_kw, big.demand_max_kw) == ("commercial", 1000, None)
    assert "no upper demand bound" in big.notes
    assert OEBT_comp(big, "Service Charge").charge_value == 4390.37


def test_oebt_burlington_proposed_copy_ignored():
    sheet, records, _ = OEBT_variant("burlington")
    assert [r.tariff_code for r in records] == ["GS 50-4,999 kW"]
    assert OEBT_comp(records[0], "Distribution Volumetric Rate").charge_value == 4.5127
    assert any(n.startswith("Ignored the proposed/draft tariff copy on PDF pages 72-74") for n in sheet.notes)
    assert sheet.issued_date == "2025-12-11"
    cbr = OEBT_comp(records[0], "Rate Rider for Disposition of Capacity Based Recovery (CBR) Account Applicable only "
                           "for Class B Customers - effective until December 31, 2027")
    assert (cbr.charge_value, cbr.end_date) == (0.089, "2027-12-31")


def test_oebt_burlington_conflicting_copies_rejected_without_cover():
    _, _, pages = OEBT_variant("burlington")
    pages = [p for p in pages if p.page_number != 71]
    sheet, records, _ = OEBT_variant("burlington", pages)
    assert records == []
    assert "conflicting duplicate" in sheet.rejections["GENERAL SERVICE 50 TO 4,999 KW"]
    assert sheet.classification("GENERAL SERVICE 50 TO 4,999 KW") is None


def test_oebt_burlington_only_proposed_tariff_fails_closed():
    _, _, pages = OEBT_variant("burlington")
    pages = [p for p in pages if p.page_number >= 71]
    sheet, records, _ = OEBT_variant("burlington", pages)
    assert records == [] and any("Only a proposed/draft" in e for e in sheet.errors)


def test_oebt_entegrus_draft_copy_ignored_and_identical_copy_deduplicated():
    sheet, records, pages = OEBT_variant("entegrus")
    assert [r.tariff_code for r in records] == ["GS 50-4,999 kW"]
    assert any("PDF pages 145-148" in n for n in sheet.notes)
    assert sheet.issued_date == "2026-03-31"
    without_cover = [p for p in pages if p.page_number != 144]
    sheet, records, _ = OEBT_variant("entegrus", without_cover)
    assert [r.tariff_code for r in records] == ["GS 50-4,999 kW"] and sheet.rejections == {}
    assert "with identical published values; the first copy is used" in records[0].notes
    rider = OEBT_comp(records[0], "Rate Rider for Disposition of Account 1576 (2026) - effective until April 30, 2027")
    assert rider.source_detail.startswith("PDF page 19 ")
    assert not any("Final Tariff Schedule" in t for c in sheet.classifications for t in c.unparsed)


def test_oebt_entegrus_differing_copy_rejected():
    sheet, _, pages = OEBT_variant("entegrus")
    service = sheet.classification("GENERAL SERVICE 50 TO 4,999 KW").find("service")[0]
    old = "Service Charge $ " + format(service.value, ",.2f")
    copy_pages = [p for p in pages if p.page_number != 144]
    changed = [DocumentPage(p.page_number, p.text.replace(old, "Service Charge $ 1.00"))
               if p.page_number >= 145 and old in p.text else p for p in copy_pages]
    assert changed != copy_pages
    sheet, records, _ = OEBT_variant("entegrus", changed)
    assert records == [] and "conflicting duplicate" in sheet.rejections["GENERAL SERVICE 50 TO 4,999 KW"]


@pytest.mark.parametrize("key,name,category,code,bounds,customer_class", [
    ("grandbridge_brantford", "GENERAL SERVICE GREATER THAN 50 KW", "gs_demand", "GS 50+ kW", (50, None), "commercial"),
    ("synergy_north", "GENERAL SERVICE 1,000 KW OR GREATER", "gs_demand", "GS 1,000+ kW", (1000, 5000), "commercial"),
    ("north_bay", "GENERAL SERVICE GREATER THAN 3,000 KW", "large_use", "GS 3,000+ kW", (3000, None), "industrial"),
])
def test_oebt_open_ended_general_service_classes(key, name, category, code, bounds, customer_class):
    sheet, records, _ = OEBT_variant(key)
    assert classify_classification(sheet.classification(name)) == category
    rec = OEBT_record(records, code)
    assert ((rec.demand_min_kw, rec.demand_max_kw), rec.customer_class) == (bounds, customer_class)
    assert sheet.rejections == {}


def test_oebt_sudbury_negative_eligibility_uses_class_name_bounds():
    sheet, records, _ = OEBT_variant("sudbury")
    gs = sheet.classification("GENERAL SERVICE 50 TO 4,999 KW")
    assert "shall not qualify as a General Service Less Than 50 kW" in gs.eligibility
    assert (gs.demand_min_kw, gs.demand_max_kw) == (50, 5000)
    assert (OEBT_record(records, "GS 50-4,999 kW").demand_min_kw, OEBT_record(records, "GS 50-4,999 kW").demand_max_kw) == (50, 5000)


def test_oebt_oshawa_wrapped_labels_reassembled():
    sheet, records, _ = OEBT_variant("oshawa")
    assert [r.tariff_code for r in records] == ["GS 50-999 kW", "GS 1,000-4,999 kW", "LU"]
    assert (sheet.effective_date, sheet.implementation_date) == ("2026-01-01", "2026-07-01")
    gs = sheet.classification("GENERAL SERVICE 50 TO 999 KW")
    cbr = OEBT_charge(gs, "Rate Rider for Disposition of Capacity Based Recovery (CBR) Account")
    assert (cbr.value, cbr.unit, cbr.end_date, cbr.condition) == (
        0.1765, "$/kW", "2027-06-30", "Applies only to Class B customers")
    assert cbr.label.endswith("(2026) - effective until June 30, 2027")
    ga = OEBT_charge(gs, "Rate Rider for Disposition of Global Adjustment Account")
    assert (ga.value, ga.unit, ga.end_date, ga.kind) == (0.0048, "$/kWh", "2027-06-30", "rider")
    ev = OEBT_charge(gs, "Retail Transmission Rate - Line and Transformation Connection Service Rate - Interval Metered EV")
    assert (ev.value, ev.conditional) == (0.7117, True)
    assert not [c for c in gs.charges if c.kind == "other" or c.label.startswith(("effective", "("))]
    standard = [c for c in gs.find("transmission_connection") if not c.conditional]
    assert [c.value for c in standard] == [3.2959]


def test_oebt_oshawa_unattached_tail_rejected():
    _, _, pages = OEBT_variant("oshawa")
    pages = OEBT_mutate(pages, "Customers $/kW 0.1765\n(2026)", "Customers $/kW 0.1765\nSEE BELOW\n(2026)")
    sheet, records, _ = OEBT_variant("oshawa", pages)
    assert "GS 50-999 kW" not in [r.tariff_code for r in records]
    assert "unrecognised delivery charge 'SEE BELOW (2026)" in sheet.rejections["GENERAL SERVICE 50 TO 999 KW"]


def test_oebt_orphan_effective_until_label_rejected():
    _, _, pages = OEBT_variant("oshawa")
    pages = OEBT_mutate(pages, "Rate Rider for Disposition of Global Adjustment Account - Applicable to Non-RPP Customers Only "
                          "(2026) -\neffective until June 30, 2027 $/kWh 0.0048", "effective until June 30, 2027 $/kWh 0.0048")
    sheet, records, _ = OEBT_variant("oshawa", pages)
    assert "wrapped tail" in sheet.rejections["GENERAL SERVICE 1,000 TO 4,999 KW"]
    assert "GS 50-999 kW" in [r.tariff_code for r in records]


def test_oebt_newmarket_meter_type_distribution_alternatives():
    sheet, records, _ = OEBT_variant("newmarket_tay")
    assert sheet.issued_date == "2026-03-06" and sheet.rejections == {}
    gs = OEBT_record(records, "GS 50-4,999 kW")
    thermal = OEBT_comp(gs, "Distribution Volumetric Rate - Thermal Demand Meter")
    interval = OEBT_comp(gs, "Distribution Volumetric Rate - Interval Meter")
    assert (thermal.charge_value, interval.charge_value) == (5.9451, 6.1116)
    assert "thermal demand meter" in thermal.notes and "an interval meter" in interval.notes
    capital = [c for c in gs.components if c.component_name.startswith("Rate Rider for Recovery of Incremental Capital")]
    assert sorted((c.charge_value, c.charge_unit) for c in capital) == [
        (0.1571, "$/kW"), (0.1774, "$/kW"), (4.55, "$/month"), (5.14, "$/month")]
    assert all("next cost-of-service" in c.notes for c in capital)


def test_oebt_newmarket_single_meter_alternative_rejected():
    _, _, pages = OEBT_variant("newmarket_tay")
    pages = OEBT_mutate(pages, "Distribution Volumetric Rate - Interval Meter $/kW 6.1116\n", "")
    sheet, records, _ = OEBT_variant("newmarket_tay", pages)
    assert records == [] and "Distribution Volumetric Rate" in sheet.rejections["GENERAL SERVICE 50 TO 4,999 KW"]


def test_oebt_midland_garbled_text_rejected():
    sheet, records, _ = OEBT_variant("midland")
    assert records == []
    assert "garbled" in sheet.rejections["GENERAL SERVICE 50 TO 4,999 KW"]


def test_oebt_kingston_out_of_order_page_stays_rejected():
    sheet, records, _ = OEBT_variant("kingston")
    assert records == [] and "GENERAL SERVICE 50 TO 4,999 KW" in sheet.rejections


def test_oebt_bluewater_billing_demand_note_attached():
    sheet, records, _ = OEBT_variant("bluewater")
    assert sheet.footnotes["1"].startswith("The Billing Demand for Line and Transformation Connection Services")
    lu = OEBT_record(records, "LU")
    assert "Tariff note 1: The Billing Demand for Line and Transformation Connection Services" in lu.notes
    assert sheet.issued_date == "2026-03-19"


# ======================================================================
# Ontario LDC tariff-sheet scraper (Ontario batch 1)
# ======================================================================
from scrapers.utilities.ontario_ldc import OEBDataError as ONL_OEBDataError, OntarioLDCScraper as ONL_OntarioLDCScraper, clean_zone as ONL_clean_zone, oeb_distributor_for_registry as ONL_oeb_distributor_for_registry, parse_bill_data as ONL_parse_bill_data, parse_rpp_page as ONL_parse_rpp_page, select_energy_classification as ONL_select_energy_classification, split_oeb_distributor as ONL_split_oeb_distributor, validate_energy_charges as ONL_validate_energy_charges
"""Pending tests: Ontario LDC records from approved OEB tariffs + RPP prices; XML as mapping/cross-check."""

import json
from datetime import date
from pathlib import Path

import pytest

from scrapers.base import BaseScraper
from scrapers.utils import oeb_tariff
from scrapers.utils.parsing import DocumentPage
from scrapers.utilities import ontario_ldc

ONL_FIXTURES = Path(__file__).resolve().parent / "fixtures"
ONL_FIXTURE = ONL_FIXTURES / "oeb_billdata.json"
ONL_TODAY = date(2026, 10, 7)
ONL_TARIFF_FIXTURES = ("toronto", "ottawa", "alectra", "hydro_one")


def ONL_load_fixture():
    return json.loads(ONL_FIXTURE.read_text(encoding="utf-8"))


def ONL_load_tariff(name):
    data = json.loads((ONL_FIXTURES / ("oeb_tariff_" + name + ".json")).read_text(encoding="utf-8"))
    pages = [DocumentPage(p.get("page", p.get("page_number")), p["text"]) for p in data["pages"]]
    return data, pages


def ONL_tariff_pages(mutate=None):
    out = {}
    for name in ONL_TARIFF_FIXTURES:
        data, pages = ONL_load_tariff(name)
        if mutate and name in mutate:
            old, new = mutate[name]
            pages = [DocumentPage(p.page_number, p.text.replace(old, new)) for p in pages]
        out[data["url"]] = pages
    return out


def ONL_rpp():
    return ONL_parse_rpp_page(ONL_load_fixture()["rpp_html"], today=ONL_TODAY)


def ONL_patch_sources(monkeypatch, res_xml=None, gs_xml=None, rpp_html=None, xml=True,
                  rpp_ok=True, tariffs=True, mutate=None, today=ONL_TODAY):
    fx = ONL_load_fixture()
    payload = {}
    if rpp_ok:
        payload[ontario_ldc.OEB_SOURCE_URL] = (rpp_html or fx["rpp_html"]).encode("utf-8")
    if xml:
        payload[ontario_ldc.OEB_BILLDATA_RES_URL] = (res_xml or fx["residential_xml"]).encode("utf-8")
        payload[ontario_ldc.OEB_BILLDATA_GS_URL] = (gs_xml or fx["gs_xml"]).encode("utf-8")
    pages = ONL_tariff_pages(mutate) if tariffs else {}
    calls = []

    def fake_fetch_bytes(self, url, delay=1.0):
        calls.append(url)
        if url not in payload:
            raise RuntimeError("unexpected url " + url)
        return payload[url]

    def fake_pages(self, url):
        calls.append(url)
        if url not in pages:
            raise RuntimeError("tariff unavailable " + url)
        return pages[url]

    ontario_ldc.clear_oeb_cache()
    monkeypatch.setattr(BaseScraper, "fetch_bytes", fake_fetch_bytes)
    monkeypatch.setattr(ONL_OntarioLDCScraper, "_fetch_tariff_pages", fake_pages)
    monkeypatch.setattr(ontario_ldc, "_today", lambda: today)
    return calls


def ONL_run(monkeypatch, name, **kw):
    ONL_patch_sources(monkeypatch, **kw)
    scraper = ONL_OntarioLDCScraper(registry_entry={"name": name})
    try:
        return scraper, scraper.scrape()
    finally:
        ontario_ldc.clear_oeb_cache()


def ONL_scrape(monkeypatch, name, **kw):
    return ONL_run(monkeypatch, name, **kw)[1]


def ONL_live(records):
    return [r for r in records if "Provenance: live_parsed" in (r.notes or "")]


def ONL_seed(records):
    return [r for r in records if "Provenance: seed_fallback" in (r.notes or "")]


def ONL_record(records, code):
    matches = [r for r in records if r.tariff_code == code]
    assert len(matches) == 1, code
    return matches[0]


def ONL_comp(rec, name):
    matches = [c for c in rec.components if c.component_name == name]
    assert len(matches) == 1, name
    return matches[0]


def ONL_comp_like(rec, text):
    return [c for c in rec.components if text in c.component_name]


# ── RPP page ───────────────────────────────────────────────────

def test_onl_rpp_parse_prices_periods_and_thresholds():
    data = ONL_rpp()
    assert data["effective_date"] == "2025-11-01"
    assert data["tou"]["Off-Peak"]["price"] == 0.098
    assert data["tou"]["Mid-Peak"]["price"] == 0.157
    assert data["tou"]["On-Peak"]["price"] == 0.203
    assert "11 a.m. – 5 p.m." in data["tou"]["Mid-Peak"]["winter_hours"]
    assert "11 a.m. – 5 p.m." in data["tou"]["On-Peak"]["summer_hours"]
    assert data["ulo"]["Ultra-Low Overnight"]["price"] == 0.039
    assert data["ulo"]["On-Peak"]["price"] == 0.391
    assert data["tier1_price"] == 0.12 and data["tier2_price"] == 0.142
    assert data["thresholds"] == {
        "res_winter": 1000.0, "res_summer": 600.0, "gs_winter": 750.0, "gs_summer": 750.0,
    }
    assert data["winter_months"] == "November 1 - April 30"


def test_onl_rpp_future_or_stale_date_fails_closed():
    html = ONL_load_fixture()["rpp_html"]
    with pytest.raises(ONL_OEBDataError):
        ONL_parse_rpp_page(html, today=date(2025, 10, 15))
    with pytest.raises(ONL_OEBDataError):
        ONL_parse_rpp_page(html, today=date(2027, 1, 15))


def test_onl_rpp_missing_table_or_unit_change_fails_closed():
    html = ONL_load_fixture()["rpp_html"]
    with pytest.raises(ONL_OEBDataError):
        ONL_parse_rpp_page(html.replace("ULO Price Periods", "Other Periods"), today=ONL_TODAY)
    with pytest.raises(ONL_OEBDataError):
        ONL_parse_rpp_page(html.replace("TOU Prices (¢/kWh)", "TOU Prices ($/kWh)"), today=ONL_TODAY)


# ── Bill data XML ──────────────────────────────────────────────

def test_onl_split_distributor_and_zone():
    assert ONL_split_oeb_distributor("Alectra Utilities Corporation-Brampton Rate Zone") == (
        "Alectra Utilities Corporation", "Brampton")
    assert ONL_split_oeb_distributor(
        "Newmarket-Tay Power Distribution Ltd.-Midland Rate Zone") == (
        "Newmarket-Tay Power Distribution Ltd.", "Midland")
    assert ONL_split_oeb_distributor(
        "Entegrus Powerlines Inc.-For Former St. Thomas Energy Rate Zone") == (
        "Entegrus Powerlines Inc.", "Former St. Thomas Energy")
    assert ONL_split_oeb_distributor("Hydro Ottawa Limited") == ("Hydro Ottawa Limited", "")


def test_onl_parse_residential_zones_and_values():
    zones, rejected = ONL_parse_bill_data(ONL_load_fixture()["residential_xml"].encode(), "residential", ONL_rpp(), ONL_TODAY)
    hydro_one = {z["zone"]: z for z in zones["Hydro One Networks Inc."]}
    assert set(hydro_one) == {
        "AUR", "UR", "AR", "R1", "R2",
        "Former Orillia Power Distribution Corporation", "Former Peterborough Distribution Inc.",
    }
    r1 = hydro_one["R1"]["values"]
    assert r1["SC"] == 72.48 and r1["OFC"] == -2.14 and r1["OC"] == -0.0047
    assert r1["VC"] is None and r1["Net"] == 0.0131 and r1["Conn"] == 0.0094 and r1["LF"] == 1.076
    assert hydro_one["R2"]["values"]["VC"] == 0.0117
    alectra = {z["zone"] for z in zones["Alectra Utilities Corporation"]}
    assert alectra == {"Brampton", "Enersource", "Guelph", "Horizon Utilities", "PowerStream"}
    toronto = {z["zone"] for z in zones["Toronto Hydro-Electric System Limited"]}
    assert toronto == {"", "Competitive Sector Multi-Unit Residential"}
    assert {z["zone"] for z in zones["Algoma Power Inc."]} == {"R1", "Seasonal"}
    assert any("Algoma Power Inc. / RESIDENTIAL R2" in m for m in rejected)
    assert "PUC Distribution Inc." not in zones
    assert any(m.startswith("PUC Distribution Inc.") and "Conn" in m for m in rejected)


def test_onl_parse_gs_rejects_empty_duplicate_but_keeps_valid_zone():
    zones, rejected = ONL_parse_bill_data(ONL_load_fixture()["gs_xml"].encode(), "gs", ONL_rpp(), ONL_TODAY)
    hydro_one = {z["zone"]: z for z in zones["Hydro One Networks Inc."]}
    assert set(hydro_one) == {
        "UGe", "GSe", "Former Orillia Power Distribution Corporation",
        "Former Peterborough Distribution Inc.",
    }
    assert hydro_one["GSe"]["values"]["VC"] == 0.0816
    assert any("Uge" in m and "SC" in m for m in rejected)
    assert "Algoma Power Inc." not in zones


def test_onl_stale_rate_year_rejects_rows():
    zones, rejected = ONL_parse_bill_data(
        ONL_load_fixture()["residential_xml"].encode(), "residential", ONL_rpp(), date(2027, 2, 1))
    assert zones == {}
    assert rejected and all("rate year" in m for m in rejected)


def test_onl_changed_xml_structure_fails_closed():
    xml = ONL_load_fixture()["residential_xml"].replace("<WMSR>", "<WMSR_NEW>").replace("</WMSR>", "</WMSR_NEW>")
    with pytest.raises(ONL_OEBDataError):
        ONL_parse_bill_data(xml.encode(), "residential", ONL_rpp(), ONL_TODAY)


def test_onl_rpp_mismatch_rejects_rows():
    xml = ONL_load_fixture()["residential_xml"].replace("<RPPOnP>0.203</RPPOnP>", "<RPPOnP>0.21</RPPOnP>")
    zones, rejected = ONL_parse_bill_data(xml.encode(), "residential", ONL_rpp(), ONL_TODAY)
    assert zones == {}
    assert any("RPPOnP" in m for m in rejected)


# ── Name mapping ───────────────────────────────────────────────

def test_onl_name_mapping_and_merged_ldcs():
    assert ONL_oeb_distributor_for_registry("Hydro Ottawa Ltd.") == "Hydro Ottawa Limited"
    assert ONL_oeb_distributor_for_registry("Toronto Hydro-Electric System Ltd.") == (
        "Toronto Hydro-Electric System Limited")
    assert ONL_oeb_distributor_for_registry("Alectra Utilities") == "Alectra Utilities Corporation"
    assert ONL_oeb_distributor_for_registry("Enova Power Corp.") == "Enova Power Corp."
    for merged in ("Kitchener-Wilmot Hydro Inc.", "Waterloo North Hydro Inc.",
                   "Guelph Hydro Electric Systems Inc.", "Brantford Power Inc."):
        assert ONL_oeb_distributor_for_registry(merged) is None


# ── Scraper ────────────────────────────────────────────────────

def test_onl_tariff_documents_config_matches_fixtures():
    docs = ontario_ldc.OEB_TARIFF_DOCUMENTS
    for name, entries in docs.items():
        assert ONL_oeb_distributor_for_registry(name), name
        for doc in entries:
            assert set(doc) >= {"url", "case_number", "zones", "default_zone"}
    by_url = {doc["url"]: doc for entries in docs.values() for doc in entries}
    for name in ONL_TARIFF_FIXTURES:
        data, _ = ONL_load_tariff(name)
        assert by_url[data["url"]]["case_number"] == data["case_number"]


def test_onl_tariff_documents_config_integrity():
    import re
    registry = json.loads((Path(__file__).resolve().parents[1] / "data" / "sources" / "registry.json")
                          .read_text(encoding="utf-8"))
    entries = registry.get("utilities", registry) if isinstance(registry, dict) else registry
    on_names = {u["name"] for u in entries if u.get("province") == "ON"}
    successors = ontario_ldc.OEB_SUCCESSOR_REGISTRY_NAMES
    merged = ontario_ldc.OEB_MERGED_REGISTRY_NAMES
    owners = {}
    for name, docs in ontario_ldc.OEB_TARIFF_DOCUMENTS.items():
        assert name in on_names or name in successors, name
        assert name not in merged, name
        assert docs, name
        defaults = set()
        for doc in docs:
            assert set(doc) - {"extract", "connection_rate"} == {"url", "case_number", "zones", "default_zone"}, name
            if "connection_rate" in doc:
                assert doc["connection_rate"] == oeb_tariff.CONNECTION_RATE_NOT_PRINTED, name
            if "extract" in doc:
                assert doc["extract"] and set(doc["extract"]) <= {"y_tolerance"}, name
                assert all(isinstance(v, (int, float)) and v > 0 for v in doc["extract"].values()), name
            assert doc["url"].startswith("https://"), name
            assert owners.setdefault(doc["url"], name) == name, doc["url"]
            assert re.fullmatch(r"EB-\d{4}-\d{4}", doc["case_number"]), name
            zones = doc["zones"]
            assert zones is None or (zones and all(isinstance(z, str) and z == ONL_clean_zone(z) for z in zones)), name
            default = doc["default_zone"]
            assert isinstance(default, (str, dict)), name
            if isinstance(default, dict):
                assert set(default) <= {"residential", "gs", "demand"}, name
            else:
                defaults.add(default)
            if len(docs) > 1:
                assert zones is not None, name
        zone_lists = [z for doc in docs for z in (doc["zones"] or [])]
        assert len(zone_lists) == len(set(zone_lists)), name
        if zone_lists:
            assert defaults <= set(zone_lists), name
    for name in successors:
        assert name in ontario_ldc.OEB_TARIFF_DOCUMENTS and name not in ontario_ldc.ONTARIO_LDC_DATA, name


def test_onl_duplicate_demand_codes_fail_closed(monkeypatch):
    from dataclasses import replace as dc_replace
    original = oeb_tariff.build_demand_records

    def doubled(sheet, name, **kw):
        records = original(sheet, name, **kw)
        return records + [dc_replace(records[0])] if records else records

    monkeypatch.setattr(oeb_tariff, "build_demand_records", doubled)
    scraper, records = ONL_run(monkeypatch, "Toronto Hydro-Electric System Ltd.")
    codes = [r.tariff_code for r in ONL_live(records)]
    assert "GS 50-999 kW" not in codes and len(codes) == len(set(codes))
    assert {"GS 1,000-4,999 kW", "LU"} <= set(codes)
    assert scraper.tariff_rejections["demand:GS 50-999 kW"] == "conflicting duplicate classifications"


def test_onl_successor_without_tariff_emits_nothing(monkeypatch):
    for name in sorted(ontario_ldc.OEB_SUCCESSOR_REGISTRY_NAMES):
        scraper, records = ONL_run(monkeypatch, name)
        assert records == [], name


@pytest.mark.parametrize("name", sorted(ontario_ldc.OEB_MERGED_REGISTRY_NAMES))
def test_onl_merged_ldc_returns_labelled_seed_unchanged(monkeypatch, name):
    calls = ONL_patch_sources(monkeypatch)
    scraper = ONL_OntarioLDCScraper(registry_entry={"name": name})
    expected = [(r.tariff_code, [c.charge_value for c in r.components]) for r in scraper._seed_data()]
    records = scraper.scrape()
    ontario_ldc.clear_oeb_cache()
    assert calls == []
    assert [(r.tariff_code, [c.charge_value for c in r.components]) for r in records] == expected
    assert records == [] or all("Provenance: seed_fallback" in (r.notes or "") for r in records)
    assert not ONL_live(records)


def test_onl_clean_zone():
    assert ONL_clean_zone("Brampton Rate Zone") == "Brampton"
    assert ONL_clean_zone("Former Peterborough Distribution Inc. Service Area") == (
        "Former Peterborough Distribution Inc.")
    assert ONL_clean_zone(None) == ""


def test_onl_local_classification_selector(monkeypatch):
    monkeypatch.delattr(oeb_tariff, "classify_classification", raising=False)

    def sel(name):
        return ONL_select_energy_classification(oeb_tariff.Classification(name=name))

    assert sel("RESIDENTIAL") == ("residential", "")
    assert sel("GENERAL SERVICE LESS THAN 50 KW") == ("gs", "")
    assert sel("MEDIUM DENSITY - R1**") == ("residential", "R1")
    assert sel("SEASONAL RESIDENTIAL") == ("residential", "Seasonal")
    assert sel("URBAN GENERAL SERVICE ENERGY BILLED - UGe") == ("gs", "UGe")
    assert sel("ACQUIRED MIXED DENSITY GENERAL SERVICE ENERGY BILLED - AGSE") == ("gs", "AGSe")
    assert sel("COMPETITIVE SECTOR MULTI-UNIT RESIDENTIAL") == (
        "residential", "Competitive Sector Multi-Unit Residential")
    for excluded in ("GENERAL SERVICE 50 TO 999 KW", "LARGE USE", "STREET LIGHTING",
                     "UNMETERED SCATTERED LOAD", "microFIT",
                     "URBAN GENERAL SERVICE DEMAND BILLED - UGd"):
        assert sel(excluded) is None, excluded


def test_onl_seasonal_service_line_split():
    def charge(label, kind, unit, value):
        return oeb_tariff.TariffCharge(label=label, value=value, unit=unit, kind=kind,
                                       section="delivery", page_number=1)

    charges = [
        charge("Service Charge* - applicable to year-round low-density customers", "service", "$/month", 151.14),
        charge("Service Charge - applicable to Seasonal customers", "service", "$/month", 92.43),
        charge("Distribution Volumetric Rate", "distribution", "$/kWh", 0.0117),
    ]
    split = ontario_ldc._split_seasonal(charges, "R2")
    assert [(q, s) for q, _, s in split] == [("R2", False), ("Seasonal", True)]
    assert [c.value for c in split[0][1] if c.kind == "service"] == [151.14]
    assert [c.value for c in split[1][1] if c.kind == "service"] == [92.43]
    assert ONL_validate_energy_charges(charges, "residential", []).startswith("expected exactly one")


def test_onl_rider_applicability_patterns():
    subarea = ontario_ldc._SUBAREA_ONLY_RE
    assert subarea.search("Rate Rider for Disposition of Group 1 Deferral/Variance Accounts (2026) "
                          "(Applicable to former Chapleau PUC customers only) - effective until December 31, 2026")
    assert not subarea.search("Rate Rider for Disposition of Capacity Based Recovery Account (2026) (Not applicable "
                              "to former Chapleau PUC customers) - effective until December 31, 2026 "
                              "(Applicable only to Non-WMP Class B Customers)")
    assert ontario_ldc._EXCLUDING_GA_RE.search("Group 1 Deferral/Variance Accounts (excluding Global Adjustment)")
    assert ontario_ldc._EXCLUDING_GA_RE.search("Group 1 Deferral/Variance Account Balances (excluding Global Adj.)")


def test_onl_toronto_records_from_tariff(monkeypatch):
    scraper, records = ONL_run(monkeypatch, "Toronto Hydro-Electric System Ltd.")
    codes = {r.tariff_code for r in ONL_live(records)}
    assert codes == {"TOU-R", "TIER-R", "ULO-R", "GS-TOU-S", "GS-TIER-S", "GS-ULO-S",
                     "GS 50-999 kW", "GS 1,000-4,999 kW", "LU"}
    assert {r.tariff_code for r in ONL_seed(records)} == {"SL"}
    tou = ONL_record(records, "TOU-R")
    assert tou.confidence == "high" and tou.effective_date == "2026-01-01"
    assert tou.source_url == ontario_ldc.OEB_TARIFF_DOCUMENTS[
        "Toronto Hydro-Electric System Ltd."][0]["url"]
    sc = ONL_comp(tou, "Service Charge")
    assert (sc.charge_value, sc.charge_unit, sc.effective_date) == (51.18, "$/30 days", "2026-01-01")
    assert "PDF page 19" in sc.source_detail and "EB-2025-0006" in sc.source_detail
    sme = ONL_comp_like(tou, "Smart Metering Entity")[0]
    assert sme.charge_value == 0.41 and sme.end_date == "2027-12-31" and sme.component_type == "rider"
    assert not ONL_comp_like(tou, "Global Adjustment")
    assert "Global Adjustment" in tou.notes and "non-RPP" in tou.notes
    cbr_rider = ONL_comp_like(tou, "Capacity Based Recovery Account")[0]
    assert "Conditional" in cbr_rider.notes
    assert ONL_comp(tou, "Retail Transmission Rate - Network Service Rate").charge_value == 0.01346
    assert not ONL_comp_like(tou, "Distribution Volumetric Rate")
    on_peak = ONL_comp(tou, "On-Peak Energy")
    assert on_peak.charge_value == 0.203 and on_peak.effective_date == "2025-11-01"
    assert on_peak.source_url == ontario_ldc.OEB_SOURCE_URL
    assert "1.0295" in tou.notes
    gs_tier = ONL_record(records, "GS-TIER-S")
    assert [c.tier_threshold for c in gs_tier.components if c.component_type == "energy"] == [750.0, 750.0]
    assert ONL_comp(gs_tier, "Distribution Volumetric Rate").charge_value == 0.04778
    assert gs_tier.demand_max_kw == 50 and gs_tier.sub_class == "GS < 50 kW"
    tier = ONL_record(records, "TIER-R")
    thresholds = {(c.tier_number, c.season): c.tier_threshold
                  for c in tier.components if c.component_type == "energy"}
    assert thresholds == {(1, "winter"): 1000.0, (2, "winter"): 1000.0,
                          (1, "summer"): 600.0, (2, "summer"): 600.0}
    assert scraper.tariff_rejections == {}


def test_onl_hydro_ottawa_implementation_date(monkeypatch):
    records = ONL_scrape(monkeypatch, "Hydro Ottawa Ltd.")
    tou = ONL_record(records, "TOU-R")
    assert tou.effective_date == "2026-06-01"
    assert ONL_comp(tou, "Service Charge").charge_value == 39.2
    delivery = [c for c in tou.components if c.component_type != "energy"]
    assert {c.effective_date for c in delivery} == {"2026-06-01"}
    assert {c.effective_date for c in tou.components if c.component_type == "energy"} == {"2025-11-01"}
    assert "implemented 2026-06-01" in tou.notes
    demand = [r for r in ONL_live(records) if r.rate_structure == "demand"]
    assert len(demand) == 3 and {r.effective_date for r in demand} == {"2026-06-01"}
    assert not {r.tariff_code for r in records} & {"GS-D1", "GS-D2", "GS-D3"}


def test_onl_alectra_zones(monkeypatch):
    records = ONL_live(ONL_scrape(monkeypatch, "Alectra Utilities"))
    codes = [r.tariff_code for r in records]
    assert len(codes) == len(set(codes))
    rpp_records = [r for r in records if r.rate_structure != "demand"]
    assert len(rpp_records) == 5 * 3 * 2
    names = {r.tariff_name for r in rpp_records}
    assert "Residential -- Time-of-Use (TOU) [Brampton]" in names
    assert "General Service < 50 kW -- ULO [Horizon Utilities]" in names
    default = ONL_record(records, "TOU-R")
    assert "PowerStream" in default.description
    assert ONL_comp(default, "Service Charge").charge_value == 34.43
    assert ONL_comp(ONL_record(records, "TOU-R-BRAMPTON"), "Service Charge").charge_value == 29.93
    allowance = [c for c in ONL_record(records, "GS-TOU-S-BRAMPTON").components if c.component_type == "rebate"]
    assert [(a.charge_value, a.charge_unit) for a in allowance] == [(-0.0032, "$/kWh")]
    assert not [c for c in ONL_record(records, "GS-TOU-S").components if c.component_type == "rebate"]
    assert "LU" in codes and "LU-BRAMPTON" in codes and "GS 50-699 kW-BRAMPTON" in codes


def test_onl_hydro_one_acquired_zones(monkeypatch):
    records = ONL_scrape(monkeypatch, "Hydro One Networks Inc.")
    peterborough = ONL_record(records, "TOU-R-FORMER-PETERBOROUGH-DISTRIBUTION-INC")
    assert peterborough.tariff_name == "Residential -- Time-of-Use (TOU) [Former Peterborough Distribution Inc.]"
    assert ONL_comp(peterborough, "Service Charge").charge_value == 23.36
    assert "Approved on an interim basis" in ONL_comp_like(peterborough, "Account 1588")[0].notes
    orillia_gs = ONL_record(records, "GS-TOU-S-FORMER-ORILLIA-POWER-DISTRIBUTION-CORPORATION")
    assert ONL_comp(orillia_gs, "Distribution Volumetric Rate").charge_value == 0.0171
    assert "next cost-of-service" in ONL_comp_like(orillia_gs, "Smart Meter Incremental")[0].notes


def test_onl_hydro_one_main_zone_classes(monkeypatch):
    records = ONL_scrape(monkeypatch, "Hydro One Networks Inc.")
    main = ONL_record(records, "TOU-R")
    if "Provenance: live_parsed" not in main.notes:
        pytest.skip("oeb_tariff does not yet parse Hydro One main-zone (density) classifications")
    assert ONL_comp(main, "Service Charge").charge_value == 74.62
    assert not ONL_comp_like(main, "Applicable to former Chapleau PUC customers only")
    codes = {r.tariff_code for r in ONL_live(records)}
    assert {"TOU-R-UR", "TOU-R-R2", "TOU-R-SEASONAL", "TOU-R-AUR", "TOU-R-AR",
            "GS-TOU-S", "GS-TOU-S-UGE", "GS-TOU-S-AUGE", "GS-TOU-S-AGSE"} <= codes
    assert ONL_comp(ONL_record(records, "GS-TOU-S"), "Distribution Volumetric Rate").charge_value == 0.0816
    assert "1.076" in main.notes
    r2 = ONL_record(records, "TOU-R-R2")
    seasonal = ONL_record(records, "TOU-R-SEASONAL")
    assert [c.charge_value for c in r2.components if c.sub_component == "service_charge"] == [151.14]
    assert [c.charge_value for c in seasonal.components if c.sub_component == "service_charge"] == [92.43]
    credit = [c for c in r2.components if c.component_type == "rebate"]
    assert [c.charge_value for c in credit] == [-60.5] and "Conditional" in credit[0].notes
    assert not [c for c in seasonal.components if c.component_type == "rebate"]
    assert ONL_comp(seasonal, "Distribution Volumetric Rate").charge_value == 0.0117


def test_onl_missing_default_zone_keeps_labelled_seed(monkeypatch):
    records = ONL_scrape(monkeypatch, "Hydro One Networks Inc.",
                     mutate={"hydro_one": ("MEDIUM DENSITY - R1", "MEDIUM DENSITY - RX")})
    tou = ONL_record(records, "TOU-R")
    if "Provenance: live_parsed" in tou.notes:
        pytest.skip("default zone still parsed under a different heading")
    assert tou.confidence == "unverified" and "seed_fallback" in tou.notes
    assert ONL_live(records)


def test_onl_xml_is_cross_check_only(monkeypatch):
    scraper, records = ONL_run(monkeypatch, "Hydro Ottawa Ltd.")
    assert any("SC: bill data 34.68 vs tariff 39.2" in d for d in scraper.xml_discrepancies)
    assert ONL_comp(ONL_record(records, "TOU-R"), "Service Charge").charge_value == 39.2
    assert not [r for r in records if "BillData" in (r.source_url or "")]
    _, no_xml = ONL_run(monkeypatch, "Hydro Ottawa Ltd.", xml=False)
    assert [r.tariff_code for r in ONL_live(no_xml)] == [r.tariff_code for r in ONL_live(records)]


def test_onl_rpp_failure_keeps_demand_live_and_energy_seed(monkeypatch):
    records = ONL_scrape(monkeypatch, "Toronto Hydro-Electric System Ltd.", rpp_ok=False)
    assert {r.tariff_code for r in ONL_live(records)} == {"GS 50-999 kW", "GS 1,000-4,999 kW", "LU"}
    assert {r.tariff_code for r in ONL_seed(records)} == {
        "TOU-R", "TIER-R", "ULO-R", "GS-TOU-S", "GS-TIER-S", "GS-ULO-S", "SL"}


def test_onl_tariff_fetch_failure_uses_seed(monkeypatch):
    records = ONL_scrape(monkeypatch, "Hydro Ottawa Ltd.", tariffs=False)
    assert len(records) == 10 and not ONL_live(records)
    assert all(r.confidence == "unverified" for r in records)


def test_onl_case_number_mismatch_fails_closed(monkeypatch):
    doc = dict(ontario_ldc.OEB_TARIFF_DOCUMENTS["Toronto Hydro-Electric System Ltd."][0])
    doc["case_number"] = "EB-2099-0001"
    monkeypatch.setitem(ontario_ldc.OEB_TARIFF_DOCUMENTS, "Toronto Hydro-Electric System Ltd.", [doc])
    scraper, records = ONL_run(monkeypatch, "Toronto Hydro-Electric System Ltd.")
    assert not ONL_live(records)
    assert any("case number" in reason for reason in scraper.tariff_rejections.values())


def test_onl_wrong_distributor_fails_closed(monkeypatch):
    docs = ontario_ldc.OEB_TARIFF_DOCUMENTS
    monkeypatch.setitem(docs, "Hydro Ottawa Ltd.", docs["Toronto Hydro-Electric System Ltd."])
    scraper, records = ONL_run(monkeypatch, "Hydro Ottawa Ltd.")
    assert not ONL_live(records)
    assert any("distributor" in reason for reason in scraper.tariff_rejections.values())


def test_onl_future_implementation_fails_closed(monkeypatch):
    scraper, records = ONL_run(monkeypatch, "Hydro Ottawa Ltd.", today=date(2026, 3, 1))
    assert not ONL_live(records)
    assert any("future" in reason for reason in scraper.tariff_rejections.values())


def test_onl_stale_tariff_fails_closed(monkeypatch):
    scraper, records = ONL_run(monkeypatch, "Toronto Hydro-Electric System Ltd.", today=date(2027, 6, 1))
    assert not ONL_live(records)
    assert any("stale" in reason for reason in scraper.tariff_rejections.values())


def test_onl_incomplete_class_fails_closed_alone(monkeypatch):
    line = "Retail Transmission Rate - Network Service Rate $/kWh 0.01346"
    scraper, records = ONL_run(monkeypatch, "Toronto Hydro-Electric System Ltd.",
                           mutate={"toronto": (line, line + "\n" + line.replace("0.01346", "0.01400"))})
    assert "residential:standard" in scraper.tariff_rejections
    codes = {r.tariff_code for r in records}
    assert not codes & {"TOU-R", "TIER-R", "ULO-R"}
    assert "Provenance: live_parsed" in ONL_record(records, "GS-TOU-S").notes
    assert "Provenance: seed_fallback" in ONL_record(records, "SL").notes


def test_onl_expired_rider_omitted(monkeypatch):
    old = "Rate Rider for Smart Metering Entity Charge - effective until December 31, 2027"
    records = ONL_scrape(monkeypatch, "Toronto Hydro-Electric System Ltd.",
                     mutate={"toronto": (old, old.replace("December 31, 2027", "September 30, 2026"))})
    tou = ONL_record(records, "TOU-R")
    assert "Provenance: live_parsed" in tou.notes
    assert not ONL_comp_like(tou, "Smart Metering Entity")
    assert "Expired riders omitted" in tou.notes


def test_onl_unconfigured_ldc_is_seed_only_without_xml(monkeypatch):
    calls = ONL_patch_sources(monkeypatch)
    monkeypatch.delitem(ontario_ldc.OEB_TARIFF_DOCUMENTS, "PUC Distribution Inc.")
    records = ONL_OntarioLDCScraper(registry_entry={"name": "PUC Distribution Inc."}).scrape()
    ontario_ldc.clear_oeb_cache()
    assert records and not ONL_live(records)
    assert all(r.confidence == "unverified" for r in records)
    assert calls == []
    assert ONL_scrape(monkeypatch, "Enova Power Corp.") == []


def test_onl_merged_ldc_produces_no_live_records(monkeypatch):
    calls = ONL_patch_sources(monkeypatch)
    records = ONL_OntarioLDCScraper(registry_entry={"name": "Kitchener-Wilmot Hydro Inc."}).scrape()
    ontario_ldc.clear_oeb_cache()
    assert records and not ONL_live(records)
    assert calls == []


def test_onl_demand_hook_replaces_seed_demand(monkeypatch):
    from scrapers.base import RateComponent, TariffRecord
    ONL_patch_sources(monkeypatch, tariffs=False)
    scraper = ONL_OntarioLDCScraper(registry_entry={"name": "Hydro Ottawa Ltd."})
    external = TariffRecord(
        utility_name="Hydro Ottawa Ltd.", province="ON", utility_type="electricity",
        tariff_name="External GS 50-1,499 kW", tariff_code="GS-D1-EXT", rate_structure="demand",
        components=[RateComponent(component_type="demand", component_name="x", charge_value=1.0)],
    )
    scraper.set_demand_records([external])
    records = scraper.scrape()
    ontario_ldc.clear_oeb_cache()
    codes = {r.tariff_code for r in records}
    assert "GS-D1-EXT" in codes and not codes & {"GS-D1", "GS-D2", "GS-D3"}
    assert "SL" in codes


# ======================================================================
# OEB tariff parser variants (Ontario batch 2)
# ======================================================================
import json
from pathlib import Path

import pytest

from scrapers.utils import oeb_tariff
from scrapers.utils.oeb_tariff import (
    build_demand_records,
    classify_classification,
    extract_tariff_pages,
    parse_tariff_pages,
    parse_tariff_zones,
)
from scrapers.utils.parsing import DocumentPage

OEBT2_B2_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "oeb_tariff_variants_b2.json"
OEBT2_B2_TODAY = "2026-10-08"


def OEBT2_b2_case(key):
    data = json.loads(OEBT2_B2_FIXTURE.read_text(encoding="utf-8"))[key]
    return data, [DocumentPage(int(n), data["text"][str(n)]) for n in data["pages"]]


def OEBT2_b2_mutate(pages, old, new):
    assert sum(p.text.count(old) for p in pages) == 1, old
    return [DocumentPage(p.page_number, p.text.replace(old, new)) for p in pages]


def OEBT2_b2_sheet(key, pages=None):
    data, fixture_pages = OEBT2_b2_case(key)
    return parse_tariff_pages(pages or fixture_pages, data["source_url"], OEBT2_B2_TODAY)


def OEBT2_b2_class(sheet, name):
    found = [c for c in sheet.classifications if c.name == name]
    assert len(found) == 1, (name, [c.name for c in sheet.classifications])
    return found[0]


def OEBT2_b2_charge(cls, label_start, kind=None):
    found = [c for c in cls.charges if c.label.startswith(label_start) and (kind is None or c.kind == kind)]
    assert len(found) == 1, (label_start, [c.label for c in cls.charges])
    return found[0]


def OEBT2_b2_record(records, code):
    found = [r for r in records if r.tariff_code == code]
    assert len(found) == 1, (code, [r.tariff_code for r in records])
    return found[0]


OEBT2_GS50 = "GENERAL SERVICE 50 TO 4,999 KW"
OEBT2_CBR_RIDER = "Rate Rider for Disposition of Capacity Based Recovery Account (2026)"


def test_oebt2_b2_fixture_metadata():
    data = json.loads(OEBT2_B2_FIXTURE.read_text(encoding="utf-8"))
    assert set(data) == {"kingston_y6", "kingston_y3", "midland_y1", "atikokan", "northern_ontario_wires",
                         "tillsonburg", "hearst"}
    for case in data.values():
        assert case["source_url"].startswith("https://www.rds.oeb.ca/CMWebDrawer/Record/")
        assert case["case_number"].startswith("EB-2025-")
        assert case["y_tolerance"] in (1, 3, 6)
        assert [int(n) for n in case["text"]] == case["pages"]


# ─── Item 1: per-document y_tolerance ─────────────────────────────

class _FakePage:
    def __init__(self, calls):
        self.calls = calls

    def extract_text(self, **kwargs):
        self.calls.append(kwargs)
        return "Kingston Hydro Corporation TARIFF OF RATES AND CHARGES"


class _FakePdf:
    def __init__(self, calls):
        self.pages = [_FakePage(calls)]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_oebt2_b2_extract_tariff_pages_default_and_override_y_tolerance(monkeypatch):
    import pdfplumber

    calls = []
    monkeypatch.setattr(pdfplumber, "open", lambda stream: _FakePdf(calls))
    assert len(extract_tariff_pages(b"%PDF")) == 1
    assert len(extract_tariff_pages(b"%PDF", y_tolerance=6)) == 1
    assert calls == [{"x_tolerance": 2, "y_tolerance": 3}, {"x_tolerance": 2, "y_tolerance": 6}]


def test_oebt2_b2_kingston_y6_gs_50_4999_validates_with_correct_pairing():
    sheet = OEBT2_b2_sheet("kingston_y6")
    cls = OEBT2_b2_class(sheet, OEBT2_GS50)
    assert oeb_tariff._validate(cls) is None and cls.unparsed == []
    cbr = OEBT2_b2_charge(cls, OEBT2_CBR_RIDER)
    assert (cbr.value, cbr.unit, cbr.conditional) == (0.1647, "$/kW", True)
    assert "Class B" in cbr.condition
    network = [c for c in cls.find("transmission_network") if not c.conditional]
    assert [(c.label, c.value) for c in network] == [("Retail Transmission Rate - Network Service Rate", 4.5677)]
    ev = OEBT2_b2_charge(cls, "Retail Transmission Rate - Network Service Rate - EV CHARGING")
    assert (ev.value, ev.conditional) == (0.7765, True)
    wms = OEBT2_b2_charge(cls, "Wholesale Market Service Rate")
    assert (wms.value, wms.unit) == (0.0041, "$/kWh")
    records = build_demand_records(sheet, "Kingston Hydro Corporation", today=OEBT2_B2_TODAY)
    assert OEBT2_b2_record(records, "GS 50-4,999 kW").demand_max_kw == 5000


def test_oebt2_b2_kingston_y3_text_stays_rejected():
    sheet = OEBT2_b2_sheet("kingston_y3")
    reason = oeb_tariff._validate(OEBT2_b2_class(sheet, OEBT2_GS50))
    assert reason and "Applicable only for Class B Customers" in reason
    build_demand_records(sheet, "Kingston Hydro Corporation", today=OEBT2_B2_TODAY)
    assert OEBT2_GS50 in sheet.rejections


# ─── Item 2: applicability tail overprinted on the next rider ─────

OEBT2_MIDLAND_TAIL = "Applicable only for Class B Customers Rate Rider for Prospective LRAMVA"
OEBT2_MIDLAND_CBR_LINE = ("Rate Rider for Disposition of Capacity Based Recovery Account (2026) - effective until "
                    "December 31, 2026 $/kW 0.1629")


def test_oebt2_b2_midland_tail_attaches_to_preceding_rider():
    sheet = OEBT2_b2_sheet("midland_y1")
    # Newmarket-Tay prints its case number only on each zone's first tariff page (not in this excerpt).
    assert sheet.rate_zone == "Midland Rate Zone" and sheet.errors == []
    cls = OEBT2_b2_class(sheet, OEBT2_GS50)
    assert oeb_tariff._validate(cls) is None
    cbr = OEBT2_b2_charge(cls, OEBT2_CBR_RIDER)
    assert (cbr.value, cbr.conditional, cbr.end_date) == (0.1629, True, "2026-12-31")
    assert cbr.label.endswith("Applicable only for Class B Customers") and "Class B" in cbr.condition
    lramva = OEBT2_b2_charge(cls, "Rate Rider for Prospective LRAMVA")
    assert (lramva.value, lramva.unit, lramva.conditional, lramva.end_date) == (0.1935, "$/kW", False, "2026-12-31")
    assert not any(c.label.startswith("Applicable") for c in cls.charges)
    records = build_demand_records(sheet, "Newmarket-Tay Power Distribution Ltd.", today=OEBT2_B2_TODAY)
    assert OEBT2_b2_record(records, "GS 50-4,999 kW")


def test_oebt2_b2_midland_tail_after_non_rider_stays_rejected():
    _, pages = OEBT2_b2_case("midland_y1")
    pages = OEBT2_b2_mutate(pages, OEBT2_MIDLAND_CBR_LINE, "Meter Charge $/kW 0.1629")
    reason = oeb_tariff._validate(OEBT2_b2_class(OEBT2_b2_sheet("midland_y1", pages), OEBT2_GS50))
    assert reason and "unrecognised delivery charge 'Applicable only for Class B" in reason


def test_oebt2_b2_midland_unknown_applicability_phrase_stays_rejected():
    _, pages = OEBT2_b2_case("midland_y1")
    pages = OEBT2_b2_mutate(pages, OEBT2_MIDLAND_TAIL, OEBT2_MIDLAND_TAIL.replace("Class B Customers", "Seasonal Customers"))
    reason = oeb_tariff._validate(OEBT2_b2_class(OEBT2_b2_sheet("midland_y1", pages), OEBT2_GS50))
    assert reason and "unrecognised delivery charge 'Applicable only for Seasonal" in reason


def test_oebt2_b2_midland_tail_not_attached_to_rider_with_applicable_clause():
    _, pages = OEBT2_b2_case("midland_y1")
    pages = OEBT2_b2_mutate(pages, OEBT2_MIDLAND_CBR_LINE, OEBT2_MIDLAND_CBR_LINE.replace(
        " $/kW", " Applicable only for Non-RPP Customers $/kW"))
    reason = oeb_tariff._validate(OEBT2_b2_class(OEBT2_b2_sheet("midland_y1", pages), OEBT2_GS50))
    assert reason and "unrecognised delivery charge 'Applicable only for Class B" in reason


# ─── Item 3: a lone Transformation Connection line is the standard rate ───

def test_oebt2_b2_atikokan_single_transformation_connection_is_standard():
    sheet = OEBT2_b2_sheet("atikokan")
    assert sheet.case_number == "EB-2025-0053"
    for name, value in (("RESIDENTIAL", 0.0069), ("GENERAL SERVICE LESS THAN 50 KW", 0.0057)):
        conn = OEBT2_b2_charge(OEBT2_b2_class(sheet, name), "Retail Transmission Rate - Transformation Connection")
        assert (conn.value, conn.unit, conn.conditional, conn.condition) == (value, "$/kWh", False, None)
    records = build_demand_records(sheet, "Atikokan Hydro Inc.", today=OEBT2_B2_TODAY)
    assert OEBT2_b2_record(records, "GS 50-4,999 kW")


def test_oebt2_b2_line_and_transformation_pair_keeps_note7_condition_for_coded_classes():
    cls = oeb_tariff.Classification(name="SUB TRANSMISSION - ST", code="ST")
    for part in ("Line", "Transformation"):
        label = f"Retail Transmission Rate - {part} Connection Service Rate"
        cls.charges.append(oeb_tariff.TariffCharge(
            label=label, value=1.0, unit="$/kW", kind="transmission_connection", section="delivery",
            page_number=1, conditional=True, condition=oeb_tariff._condition(label, "delivery")))
    oeb_tariff._single_connection_standard(cls)
    assert [c.condition for c in cls.charges] == [oeb_tariff._NOTE7_CONDITION] * 2
    pair = list(cls.charges)
    cls.charges = pair[:1]
    oeb_tariff._single_connection_standard(cls)
    assert (cls.charges[0].conditional, cls.charges[0].condition) == (True, oeb_tariff._NOTE7_CONDITION)
    cls.charges = pair[1:]
    oeb_tariff._single_connection_standard(cls)
    assert (cls.charges[0].conditional, cls.charges[0].condition) == (False, None)


def test_oebt2_b2_hydro_one_note7_pairs_unchanged():
    data = json.loads((OEBT2_B2_FIXTURE.parent / "oeb_tariff_hydro_one.json").read_text(encoding="utf-8"))
    pages = [DocumentPage(p["page_number"], p["text"]) for p in data["raw_pages"]]
    sheets = parse_tariff_zones(pages, data["url"], OEBT2_B2_TODAY)
    note7 = [c for s in sheets.values() for cls in s.classifications for c in cls.charges
             if c.condition == oeb_tariff._NOTE7_CONDITION]
    assert note7 and all(c.conditional for c in note7)
    assert {oeb_tariff._connection_part(c.label) for c in note7} == {"Line", "Transformation"}


# ─── Item 4: case number from the Schedule A cover ────────────────

OEBT2_NOW_COVER_DATE = "TARIFF OF RATES AND CHARGES EB-2025-0017\nMarch 19, 2026"


def test_oebt2_b2_northern_ontario_wires_case_from_cover():
    sheet = OEBT2_b2_sheet("northern_ontario_wires")
    assert sheet.errors == [] and sheet.issued_date == "2026-03-19"
    assert sheet.case_number == "EB-2025-0017"
    assert any("Schedule A cover (PDF page 18)" in n for n in sheet.notes)


def test_oebt2_b2_northern_ontario_wires_cover_date_mismatch_fails_closed():
    _, pages = OEBT2_b2_case("northern_ontario_wires")
    pages = OEBT2_b2_mutate(pages, OEBT2_NOW_COVER_DATE, OEBT2_NOW_COVER_DATE.replace("March 19", "March 20"))
    assert OEBT2_b2_sheet("northern_ontario_wires", pages).case_number is None


def test_oebt2_b2_northern_ontario_wires_cover_must_immediately_precede():
    _, pages = OEBT2_b2_case("northern_ontario_wires")
    moved = [DocumentPage(17 if p.page_number == 18 else p.page_number, p.text) for p in pages]
    assert OEBT2_b2_sheet("northern_ontario_wires", moved).case_number is None
    assert OEBT2_b2_sheet("northern_ontario_wires", pages[1:]).case_number is None


def test_oebt2_b2_northern_ontario_wires_cover_with_two_cases_fails_closed():
    _, pages = OEBT2_b2_case("northern_ontario_wires")
    pages = OEBT2_b2_mutate(pages, OEBT2_NOW_COVER_DATE, "TARIFF OF RATES AND CHARGES EB-2025-0099\n" + OEBT2_NOW_COVER_DATE)
    assert OEBT2_b2_sheet("northern_ontario_wires", pages).case_number is None


def test_oebt2_b2_header_case_number_still_wins():
    sheet = OEBT2_b2_sheet("hearst")
    assert sheet.case_number == "EB-2025-0033" and not any("Schedule A cover" in n for n in sheet.notes)


# ─── Item 5: GS >= 1,500 kW / Intermediate User; no silent drops ──

OEBT2_TILL_GS = "GENERAL SERVICE EQUAL TO OR GREATER THAN 1,500 KW"


def test_oebt2_b2_tillsonburg_equal_or_greater_class_built():
    sheet = OEBT2_b2_sheet("tillsonburg")
    cls = OEBT2_b2_class(sheet, OEBT2_TILL_GS)
    assert classify_classification(cls) == "gs_demand"
    assert (cls.demand_min_kw, cls.demand_max_kw) == (1500, 4999)
    assert cls.eligibility.startswith("This classification applies to a non residential account")
    records = build_demand_records(sheet, "Tillsonburg Hydro Inc.", today=OEBT2_B2_TODAY)
    rec = OEBT2_b2_record(records, "GS 1,500+ kW")
    assert rec.customer_class == "commercial" and sheet.rejections == {}
    values = {(c.component_name, c.charge_unit): c.charge_value for c in rec.components}
    assert values[("Service Charge", "$/month")] == 2380.87
    assert values[("Distribution Volumetric Rate", "$/kW")] == 2.6682


@pytest.mark.parametrize("name, low", [
    ("GENERAL SERVICE EQUAL TO OR GREATER THAN 1,500 KW", "1,500"),
    ("GENERAL SERVICE GREATER THAN OR EQUAL TO 1,000 KW", "1,000"),
    ("GENERAL SERVICE GREATER THAN 50 KW", "50"),
])
def test_oebt2_b2_gs_open_variants(name, low):
    m = oeb_tariff._GS_OPEN_RE.match(name)
    assert m and (m.group("a") or m.group("b")) == low


def test_oebt2_b2_hearst_intermediate_user_built_as_gs_demand():
    sheet = OEBT2_b2_sheet("hearst")
    cls = OEBT2_b2_class(sheet, "INTERMEDIATE USER")
    assert classify_classification(cls) == "gs_demand"
    assert (cls.demand_min_kw, cls.demand_max_kw) == (1500, 5000)
    records = build_demand_records(sheet, "Hearst Power Distribution Co. Ltd.", today=OEBT2_B2_TODAY)
    rec = OEBT2_b2_record(records, "GS 1,500-4,999 kW")
    assert rec.customer_class == "commercial" and (rec.demand_min_kw, rec.demand_max_kw) == (1500, 5000)
    assert rec.tariff_name == "Intermediate User (delivery only)"
    values = {(c.component_name, c.charge_unit): c.charge_value for c in rec.components}
    assert values[("Service Charge", "$/month")] == 285.48
    assert values[("Retail Transmission Rate - Network Service Rate", "$/kW")] == 4.1666


def test_oebt2_b2_intermediate_user_outside_range_surfaces_rejection():
    _, pages = OEBT2_b2_case("hearst")
    pages = OEBT2_b2_mutate(pages, "1,500 kW but less than 5,000 kW", "1,500 kW but less than 15,000 kW")
    sheet = OEBT2_b2_sheet("hearst", pages)
    assert classify_classification(OEBT2_b2_class(sheet, "INTERMEDIATE USER")) == "other"
    records = build_demand_records(sheet, "Hearst Power Distribution Co. Ltd.", today=OEBT2_B2_TODAY)
    assert not [r for r in records if r.demand_min_kw == 1500]
    assert "unrecognised in-scope classification" in sheet.rejections["INTERMEDIATE USER"]


def test_oebt2_b2_unrecognised_gs_name_surfaces_rejection():
    _, pages = OEBT2_b2_case("tillsonburg")
    pages = OEBT2_b2_mutate(pages, OEBT2_TILL_GS + " SERVICE", "GENERAL SERVICE INTERVAL METERED SERVICE")
    sheet = OEBT2_b2_sheet("tillsonburg", pages)
    build_demand_records(sheet, "Tillsonburg Hydro Inc.", today=OEBT2_B2_TODAY)
    assert "unrecognised in-scope classification" in sheet.rejections["GENERAL SERVICE INTERVAL METERED"]


def test_oebt2_b2_excluded_and_out_of_scope_names_not_reported_as_rejections():
    sheet = OEBT2_b2_sheet("hearst")
    sheet.classifications.append(oeb_tariff.Classification(name="FARM SERVICE", charges=[
        oeb_tariff.TariffCharge("Service Charge", 1.0, "$/month", "service", "delivery", 1)]))
    sheet.classifications.append(oeb_tariff.Classification(name="GENERAL SERVICE OVERVIEW"))
    build_demand_records(sheet, "Hearst Power Distribution Co. Ltd.", today=OEBT2_B2_TODAY)
    assert sheet.rejections == {}


def test_oebt2_b2_deinterleave_only_repairs_overprinted_heading():
    garbled = "TChiLs AclaSssSificIFatiIoCn aApTpliIeOs tNo a non residential account"
    assert oeb_tariff._deinterleave_heading(garbled) == "This classification applies to a non residential account"
    assert oeb_tariff._deinterleave_heading("CLASSIFICATION of an account") == "CLASSIFICATION of an account"
    assert oeb_tariff._deinterleave_heading("Customers whose demand exceeds 50 kW") == (
        "Customers whose demand exceeds 50 kW")


# ======================================================================
# Ontario LDC batch 2 configuration and seed suppression
# ======================================================================
from datetime import date

from scrapers.utilities import ontario_ldc

ONL2_ONL_B2_RES = {"TOU-R", "TIER-R", "ULO-R"}
ONL2_ONL_B2_GS = {"GS-TOU-S", "GS-TIER-S", "GS-ULO-S"}
ONL2_ONL_B2_DEMAND = {"GS-D1", "GS-D2", "GS-D3"}


def test_onl2_onl_b2_extract_options_configured():
    docs = ontario_ldc.OEB_TARIFF_DOCUMENTS
    assert docs["Kingston Hydro Corporation"][0]["extract"] == {"y_tolerance": 6}
    midland = [d for d in docs["Newmarket-Tay Power Distribution Ltd."] if d["zones"] == ["Midland"]]
    assert midland[0]["extract"] == {"y_tolerance": 1}
    assert "extract" not in docs["Toronto Hydro-Electric System Ltd."][0]


def test_onl2_onl_b2_extract_options_passed_only_when_present(monkeypatch):
    ONL_patch_sources(monkeypatch)
    seen = []
    pages_for = ONL_OntarioLDCScraper._fetch_tariff_pages

    def recording(self, url, **kw):
        seen.append(kw)
        return pages_for(self, url)

    monkeypatch.setattr(ONL_OntarioLDCScraper, "_fetch_tariff_pages", recording)
    doc = dict(ontario_ldc.OEB_TARIFF_DOCUMENTS["Toronto Hydro-Electric System Ltd."][0])
    scraper = ONL_OntarioLDCScraper(registry_entry={"name": "Toronto Hydro-Electric System Ltd."})
    assert scraper._load_sheets(doc, date(2026, 10, 7))
    doc["extract"] = {"y_tolerance": 6}
    assert scraper._load_sheets(doc, date(2026, 10, 7))
    ontario_ldc.clear_oeb_cache()
    assert seen == [{}, {"y_tolerance": 6}]


def test_onl2_onl_b2_fetch_tariff_pages_forwards_keyword(monkeypatch):
    calls = []

    def fake_extract(data, **kw):
        calls.append((data, kw))
        return ["page"]

    monkeypatch.setattr(ontario_ldc.oeb_tariff, "extract_tariff_pages", fake_extract)
    monkeypatch.setattr(ONL_OntarioLDCScraper, "_fetch_oeb", lambda self, url: b"pdf")
    scraper = ONL_OntarioLDCScraper(registry_entry={"name": "Kingston Hydro Corporation"})
    assert scraper._fetch_tariff_pages("u") == ["page"]
    assert scraper._fetch_tariff_pages("u", y_tolerance=6) == ["page"]
    assert calls == [(b"pdf", {}), (b"pdf", {"y_tolerance": 6})]


def test_onl2_onl_b2_new_ldcs_configured():
    docs = ontario_ldc.OEB_TARIFF_DOCUMENTS
    expected = {
        "Canadian Niagara Power Inc.": (927499, "EB-2025-0050"),
        "Grimsby Power Inc.": (925220, "EB-2025-0035"),
        "Welland Hydro-Electric System Corp.": (936222, "EB-2025-0004"),
        "Centre Wellington Hydro Ltd.": (926741, "EB-2025-0049"),
        "Festival Hydro Inc.": (925779, "EB-2025-0039"),
        "Westario Power Inc.": (924811, "EB-2025-0002"),
        "Tillsonburg Hydro Inc.": (939423, "EB-2025-0007"),
        "Orangeville Hydro Limited": (939232, "EB-2025-0015"),
        "Wasaga Distribution Inc.": (936415, "EB-2025-0005"),
        "Innpower Corporation": (926802, "EB-2025-0027"),
        "Lakefront Utilities Inc.": (925193, "EB-2025-0025"),
        "Lakeland Power Distribution Ltd.": (954612, "EB-2025-0024"),
        "Hydro 2000 Inc.": (936563, "EB-2025-0032"),
        "Hydro Hawkesbury Inc.": (937884, "EB-2025-0031"),
        "Ottawa River Power Corporation": (936459, "EB-2025-0013"),
        "Rideau St. Lawrence Distribution Inc.": (937200, "EB-2025-0010"),
        "Hearst Power Distribution Co. Ltd.": (939278, "EB-2025-0033"),
        "Atikokan Hydro Inc.": (936437, "EB-2025-0053"),
        "Fort Frances Power Corp.": (936512, "EB-2025-0038"),
        "Sioux Lookout Hydro Inc.": (936469, "EB-2025-0009"),
        "Northern Ontario Wires Inc.": (936426, "EB-2025-0017"),
    }
    for name, (record, case) in expected.items():
        entry = {
            "url": ontario_ldc._OEB_RDS_DOC.format(record),
            "case_number": case, "zones": None, "default_zone": "",
        }
        if name == "Grimsby Power Inc.":
            entry["extract"] = {"y_tolerance": 4}
        assert docs[name] == [entry], name
    assert docs["PUC Distribution Inc."][0]["connection_rate"] == "not_printed"
    assert docs["Algoma Power Inc."][0]["default_zone"] == {"residential": "R1 (i)"}


def test_onl2_onl_b2_rejected_gs_group_emits_no_gs_seed(monkeypatch):
    line = "Retail Transmission Rate - Network Service Rate $/kWh 0.01310"
    scraper, records = ONL_run(monkeypatch, "Toronto Hydro-Electric System Ltd.",
                               mutate={"toronto": (line, line + "\n" + line.replace("0.01310", "0.01400"))})
    assert any(k.startswith("gs:") for k in scraper.tariff_rejections)
    codes = {r.tariff_code for r in records}
    assert not codes & ONL2_ONL_B2_GS
    assert "Provenance: live_parsed" in ONL_record(records, "TOU-R").notes
    assert "Provenance: seed_fallback" in ONL_record(records, "SL").notes


def test_onl2_onl_b2_rejected_demand_class_emits_no_demand_seed(monkeypatch):
    def no_demand(self, doc, sheet, today):
        self.tariff_rejections["demand:standard:GENERAL SERVICE 50 TO 4,999 KW"] = "unrecognised charge"
        return []

    monkeypatch.setattr(ONL_OntarioLDCScraper, "_tariff_demand_records", no_demand)
    scraper, records = ONL_run(monkeypatch, "Hydro Ottawa Ltd.")
    codes = {r.tariff_code for r in records}
    assert not codes & ONL2_ONL_B2_DEMAND
    assert "Provenance: live_parsed" in ONL_record(records, "TOU-R").notes
    assert {r.tariff_code for r in ONL_seed(records)} == {"SL"}


def test_onl2_onl_b2_demand_seed_kept_without_demand_rejection(monkeypatch):
    monkeypatch.setattr(ONL_OntarioLDCScraper, "_tariff_demand_records", lambda self, doc, sheet, today: [])
    _, records = ONL_run(monkeypatch, "Hydro Ottawa Ltd.")
    assert ONL2_ONL_B2_DEMAND <= {r.tariff_code for r in ONL_seed(records)}


def test_onl2_onl_b2_configured_fetch_failure_keeps_labelled_seed(monkeypatch):
    _, records = ONL_run(monkeypatch, "Hydro Ottawa Ltd.", tariffs=False)
    seed_codes = {r.tariff_code for r in ONL_seed(records)}
    assert ONL2_ONL_B2_RES | ONL2_ONL_B2_GS | ONL2_ONL_B2_DEMAND | {"SL"} <= seed_codes
    assert not ONL_live(records)
    assert all(r.confidence == "unverified" for r in records)


def test_onl2_onl_b2_sheet_rejection_keeps_labelled_seed(monkeypatch):
    scraper, records = ONL_run(monkeypatch, "Toronto Hydro-Electric System Ltd.", today=date(2027, 6, 1))
    assert any(k.startswith("sheet:") for k in scraper.tariff_rejections)
    seed_codes = {r.tariff_code for r in ONL_seed(records)}
    assert ONL2_ONL_B2_RES | ONL2_ONL_B2_GS | ONL2_ONL_B2_DEMAND <= seed_codes
    assert not ONL_live(records)


def test_onl2_onl_b2_unconfigured_ldc_keeps_seed_despite_rejection(monkeypatch):
    calls = ONL_patch_sources(monkeypatch)
    monkeypatch.delitem(ontario_ldc.OEB_TARIFF_DOCUMENTS, "PUC Distribution Inc.")
    scraper = ONL_OntarioLDCScraper(registry_entry={"name": "PUC Distribution Inc."})
    scraper.tariff_rejections["residential:standard"] = "not applicable"
    records = scraper.scrape()
    ontario_ldc.clear_oeb_cache()
    assert ONL2_ONL_B2_RES <= {r.tariff_code for r in ONL_seed(records)}
    assert calls == []


# ======================================================================
# Algoma Power R1 criteria split and R2 demand-billed residential (Ontario batch 2)
# ======================================================================
import json
from datetime import date
from pathlib import Path

from scrapers.utilities import ontario_ldc
from scrapers.utils import oeb_tariff
from scrapers.utils.parsing import DocumentPage

ALG2_ALG_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "oeb_tariff_algoma.json"
ALG2_ALG_NAME = "Algoma Power Inc."
ALG2_ALG_RES = {"TOU-R", "TIER-R", "ULO-R"}
ALG2_ALG_GS = {"GS-TOU-S", "GS-TIER-S", "GS-ULO-S"}
ALG2_ALG_R1_II = "R1-II-O-REG-445-07"
ALG2_ALG_TAG_II = "Distribution Volumetric Rate - Applicable only to customers that meet criteria (ii) above"
ALG2_ALG_DEMAND_BASIS = "and which is billed on a demand basis"


def ALG2_alg_pages(mutate=None):
    data = json.loads(ALG2_ALG_FIXTURE.read_text(encoding="utf-8"))
    pages = [DocumentPage(n, data["text"][str(n)]) for n in data["pages"]]
    if mutate:
        old, new = mutate
        assert sum(p.text.count(old) for p in pages) == 1, old
        pages = [DocumentPage(p.page_number, p.text.replace(old, new)) for p in pages]
    return data, pages


def ALG2_alg_run(monkeypatch, mutate=None, tariffs=True, today=None):
    if today is None:
        ONL_patch_sources(monkeypatch)
    else:
        ONL_patch_sources(monkeypatch, today=today)
    data, pages = ALG2_alg_pages(mutate)

    def fake_pages(self, url, **kw):
        if not tariffs or url != data["source_url"]:
            raise RuntimeError("tariff unavailable " + url)
        return pages

    monkeypatch.setattr(ONL_OntarioLDCScraper, "_fetch_tariff_pages", fake_pages)
    scraper = ONL_OntarioLDCScraper(registry_entry={"name": ALG2_ALG_NAME})
    try:
        return scraper, scraper.scrape()
    finally:
        ontario_ldc.clear_oeb_cache()


def ALG2_alg_sheet(mutate=None):
    data, pages = ALG2_alg_pages(mutate)
    return ALG2_parse_sheet(pages, data["source_url"])


def ALG2_parse_sheet(pages, url):
    return oeb_tariff.parse_tariff_pages(pages, url, "2026-10-07")


def ALG2_alg_comp(record, name):
    found = [c for c in record.components if c.component_name == name]
    assert len(found) == 1, (name, [c.component_name for c in record.components])
    return found[0]


def ALG2_alg_values(record):
    return {(c.component_name, c.charge_value, c.charge_unit) for c in record.components
            if c.component_type != "energy"}


ALG2_SHARED = {
    ("Smart Metering Entity Charge - effective until December 31, 2027", 0.42, "$/month"),
    ("Retail Transmission Rate - Network Service Rate", 0.0121, "$/kWh"),
    ("Retail Transmission Rate - Line and Transformation Connection Service Rate", 0.0088, "$/kWh"),
    ("Wholesale Market Service Rate (WMS) - not including CBR", 0.0041, "$/kWh"),
    ("Capacity Based Recovery (CBR) - Applicable for Class B Customers", 0.0006, "$/kWh"),
    ("Rural or Remote Electricity Rate Protection Charge (RRRP)", 0.0006, "$/kWh"),
    ("Standard Supply Service - Administrative Charge (if applicable)", 0.25, "$/month"),
}


def test_alg2_alg_fixture_metadata():
    data = json.loads(ALG2_ALG_FIXTURE.read_text(encoding="utf-8"))
    assert data["source_url"] == ontario_ldc._OEB_RDS_DOC.format(926153)
    assert data["case_number"] == "EB-2025-0054"
    assert data["pages"] == [2, 7, 19, 20, 21, 22, 25, 26]
    assert [int(n) for n in data["text"]] == data["pages"]


def test_alg2_alg_configured():
    assert ontario_ldc.OEB_TARIFF_DOCUMENTS[ALG2_ALG_NAME] == [{
        "url": ontario_ldc._OEB_RDS_DOC.format(926153),
        "case_number": "EB-2025-0054", "zones": None, "default_zone": {"residential": "R1 (i)"},
    }]


def test_alg2_alg_sheet_classes_and_categories():
    sheet = ALG2_alg_sheet()
    assert sheet.errors == []
    assert (sheet.effective_date, sheet.implementation_date, sheet.case_number, sheet.issued_date) == (
        "2026-01-01", "2026-01-01", "EB-2025-0054", "2025-12-18")
    cats = {c.name: oeb_tariff.classify_classification(c) for c in sheet.classifications}
    assert cats["RESIDENTIAL R1"] == "residential"
    assert cats["RESIDENTIAL R2"] == "residential_demand"
    assert cats["SEASONAL CUSTOMERS"] == "residential"
    assert not {"gs_energy", "gs_demand", "large_use"} & set(cats.values())
    r2 = sheet.classification("RESIDENTIAL R2")
    assert oeb_tariff.residential_demand_floor(r2) == 50
    assert any("RRRP adjustment to the R1 base rates" in n for n in sheet.classification("RESIDENTIAL R1").notes)
    assert not any("RRRP" in n for n in sheet.classification("SEASONAL CUSTOMERS").notes)


def test_alg2_alg_r1_criteria_i_default_fully_fixed(monkeypatch):
    scraper, records = ALG2_alg_run(monkeypatch)
    for code in ALG2_ALG_RES:
        record = ONL_record(records, code)
        assert "Provenance: live_parsed" in record.notes
        assert record.customer_class == "residential"
        assert not [c for c in record.components if c.component_type == "distribution"]
        assert ALG2_alg_values(record) == ALG2_SHARED | {("Service Charge", 69.91, "$/month")}
        assert record.eligibility.startswith("Criteria (i) only: a dwelling occupied as a residence")
        assert "RRRP adjustment to the R1 base rates" in record.notes
        assert not any("criteria" in c.component_name for c in record.components)
    tou = ONL_record(records, "TOU-R")
    assert tou.tariff_name == "Residential -- Time-of-Use (TOU)"
    assert {c.component_name for c in tou.components if c.component_type == "energy"} == {
        "Off-Peak Energy", "Mid-Peak Energy", "On-Peak Energy"}
    assert not [k for k in scraper.tariff_rejections if k.startswith("residential:")]


def test_alg2_alg_r1_criteria_ii_service_and_volumetric(monkeypatch):
    _, records = ALG2_alg_run(monkeypatch)
    for base in ("TOU-R", "TIER-R", "ULO-R"):
        record = ONL_record(records, base + "-" + ALG2_ALG_R1_II)
        assert record.tariff_name.endswith("[R1 (ii) O. Reg. 445/07]")
        assert record.customer_class == "residential"
        assert ALG2_alg_values(record) == ALG2_SHARED | {("Service Charge", 31.35, "$/month"),
                                               ("Distribution Volumetric Rate", 0.0441, "$/kWh")}
        assert "Ontario Regulation 445/07" in record.eligibility.split(". Classification text:")[0]
        assert [c for c in record.components if c.component_type == "energy"]
    ulo = ONL_record(records, "ULO-R-" + ALG2_ALG_R1_II)
    assert ALG2_alg_comp(ulo, "Ultra-Low Overnight Energy").charge_value == 0.039


def test_alg2_alg_r2_delivery_only_demand_record(monkeypatch):
    _, records = ALG2_alg_run(monkeypatch)
    r2 = ONL_record(records, "R2 50+ kW")
    assert "Provenance: live_parsed" in r2.notes
    assert r2.tariff_name == "Residential R2 (delivery only)"
    assert (r2.customer_class, r2.rate_structure, r2.demand_min_kw, r2.demand_max_kw) == (
        "residential", "demand", 50, None)
    assert not [c for c in r2.components if c.component_type == "energy"]
    assert ALG2_alg_comp(r2, "Service Charge").charge_value == 806.69
    dist = ALG2_alg_comp(r2, "Distribution Volumetric Rate")
    assert (dist.charge_value, dist.charge_unit) == (4.1798, "$/kW")
    net = ALG2_alg_comp(r2, "Retail Transmission Rate - Network Service Rate")
    assert (net.charge_value, net.charge_unit) == (4.6211, "$/kW")
    assert "Conditional" not in net.notes
    conn = ALG2_alg_comp(r2, "Retail Transmission Rate - Line and Transformation Connection Service Rate")
    assert conn.charge_value == 3.3435 and "Conditional" not in conn.notes
    for name, value in (("Retail Transmission Rate - Network Service Rate - EV CHARGING", 0.7856),
                        ("Retail Transmission Rate - Line and Transformation Connection Service Rate - EV CHARGING",
                         0.5684)):
        ev = ALG2_alg_comp(r2, name)
        assert ev.charge_value == value and "Conditional: Optional Electric Vehicle" in ev.notes
    assert ALG2_alg_comp(r2, "Standard Supply Service - Administrative Charge (if applicable)").charge_value == 0.25
    assert ALG2_alg_comp(r2, "Rural or Remote Electricity Rate Protection Charge (RRRP)").charge_value == 0.0006
    allowance = ALG2_alg_comp(r2, "Transformer Allowance for Ownership - per kW of billing demand/month")
    assert allowance.charge_value == -0.6 and "Conditional" in allowance.notes
    assert "RRRP adjustment to the R2 base rates" in r2.notes
    assert "electricity commodity is not included" in r2.notes
    assert not [c for c in r2.components if "Smart Metering" in c.component_name]


def test_alg2_alg_seasonal_unchanged(monkeypatch):
    _, records = ALG2_alg_run(monkeypatch)
    seasonal = ONL_record(records, "TOU-R-SEASONAL")
    assert seasonal.tariff_name == "Residential -- Time-of-Use (TOU) [Seasonal]"
    assert ALG2_alg_comp(seasonal, "Service Charge").charge_value == 105.13
    assert ALG2_alg_comp(seasonal, "Distribution Volumetric Rate").charge_value == 0.025
    rider = [c for c in seasonal.components if c.component_type == "rider"]
    assert [c.charge_value for c in rider] == [-1.05]
    assert "RRRP adjustment" not in seasonal.notes
    assert {"TIER-R-SEASONAL", "ULO-R-SEASONAL"} <= {r.tariff_code for r in records}


def test_alg2_alg_no_gs_seeds_sl_seed_kept(monkeypatch):
    scraper, records = ALG2_alg_run(monkeypatch)
    codes = {r.tariff_code for r in records}
    assert not codes & (ALG2_ALG_GS | {"GS-D1", "GS-D2", "GS-D3"})
    assert {r.tariff_code for r in ONL_seed(records)} == {"SL"}
    assert "gs:absent" in scraper.tariff_rejections
    assert "demand:absent" in scraper.tariff_rejections
    assert len(ONL_live(records)) == 10


def test_alg2_alg_criteria_tag_mismatch_rejects_r1(monkeypatch):
    mutate = (ALG2_ALG_TAG_II, ALG2_ALG_TAG_II.replace("(ii)", "(iii)"))
    scraper, records = ALG2_alg_run(monkeypatch, mutate=mutate)
    assert "criteria tags" in scraper.tariff_rejections["residential:Residential R1"]
    codes = {r.tariff_code for r in records}
    assert not codes & ALG2_ALG_RES
    assert not [c for c in codes if ALG2_ALG_R1_II in c]
    assert "TOU-R-SEASONAL" in codes and "R2 50+ kW" in codes


def test_alg2_alg_untagged_second_service_charge_rejects_r1(monkeypatch):
    old = "Service Charge - Applicable only to customers that meet criteria (ii) above $ 31.35"
    scraper, records = ALG2_alg_run(monkeypatch, mutate=(old, "Service Charge $ 31.35"))
    assert "untagged Service Charge" in scraper.tariff_rejections["residential:Residential R1"]
    assert not {r.tariff_code for r in records} & ALG2_ALG_RES


def test_alg2_alg_residential_kw_without_demand_basis_still_rejects(monkeypatch):
    mutate = (ALG2_ALG_DEMAND_BASIS, "and which is billed on an energy basis")
    sheet = ALG2_alg_sheet(mutate)
    assert oeb_tariff.classify_classification(sheet.classification("RESIDENTIAL R2")) == "residential"
    scraper, records = ALG2_alg_run(monkeypatch, mutate=mutate)
    assert "$/kW" in scraper.tariff_rejections["residential:Residential R2"]
    assert "R2 50+ kW" not in {r.tariff_code for r in records}
    assert "TOU-R" in {r.tariff_code for r in ONL_live(records)}


def test_alg2_alg_fetch_failure_emits_labelled_seeds(monkeypatch):
    _, records = ALG2_alg_run(monkeypatch, tariffs=False)
    assert not ONL_live(records)
    assert ALG2_ALG_RES | ALG2_ALG_GS | {"GS-D1", "SL"} <= {r.tariff_code for r in ONL_seed(records)}
    assert all(r.confidence == "unverified" for r in records)


def test_alg2_alg_sheet_rejection_emits_labelled_seeds(monkeypatch):
    scraper, records = ALG2_alg_run(monkeypatch, today=date(2027, 6, 1))
    assert any(k.startswith("sheet:") for k in scraper.tariff_rejections)
    assert not ONL_live(records)
    assert ALG2_ALG_RES | ALG2_ALG_GS | {"GS-D1"} <= {r.tariff_code for r in ONL_seed(records)}


# ======================================================================
# ENMAX Power distribution tariff (batch 12)
# ======================================================================
from scrapers.utilities import enmax_power as ENX_enmax_power
from scrapers.utilities.enmax_power import ENMAXPowerScraper as ENX_ENMAXPowerScraper, current_tariff_link as ENX_current_tariff_link, parse_schedule_pages as ENX_parse_schedule_pages, render_page_words as ENX_render_page_words
from scrapers.utils.parsing import DocumentPage
import json
import logging
from datetime import date
from pathlib import Path

import pytest
import requests


ENX_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "enmax_power.json"
ENX_TODAY = date(2026, 10, 9)
ENX_CODES = {"D100", "D200", "D300", "D310", "D410"}
ENX_BPA = ("rider", "Balancing Pool Allocation Rider", 0.00129, "$/kWh", "2026-01-01", None)
ENX_EXPECTED = {
    "D100": [
        ("fixed", "Service and Facilities Charge", 0.769463, "$/day", "2026-01-01", None),
        ("distribution", "System Usage Charge", 0.015477, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Variable Charge", 0.038996, "$/kWh", "2026-01-01", None),
        ENX_BPA,
        ("rider", "Quarterly TAC Adjustment Rider", 0.000583, "$/kWh", "2026-10-01", "2026-12-31"),
        ("rider", "TAC Deferral Account Rider Adjustment", 0.000483, "$/kWh", "2026-01-01", "2026-12-31"),
    ],
    "D200": [
        ("fixed", "Service and Facilities Charge", 1.734942, "$/day", "2026-01-01", None),
        ("distribution", "System Usage Charge", 0.013024, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Variable Charge", 0.031577, "$/kWh", "2026-01-01", None),
        ENX_BPA,
        ("rider", "Quarterly TAC Adjustment Rider", 0.000602, "$/kWh", "2026-10-01", "2026-12-31"),
        ("rider", "TAC Deferral Account Rider Adjustment", 0.002877, "$/kWh", "2026-01-01", "2026-12-31"),
    ],
    "D300": [
        ("fixed", "Service Charge", 9.644493, "$/day", "2026-01-01", None),
        ("demand", "Facilities Charge", 0.065473, "$/kVA/day", "2026-01-01", None),
        ("demand", "Non-Ratcheted Demand Charge", 0.063108, "$/kVA/day", "2026-01-01", None),
        ("transmission", "Transmission Demand Charge", 0.271085, "$/kVA/day", "2026-01-01", None),
        ("transmission", "Transmission Variable Charge", 0.009237, "$/kWh", "2026-01-01", None),
        ("rebate", "Primary Voltage Transformation Credit - Service Charge", -1.848798, "$/day", "2026-01-01", None),
        ("rebate", "Primary Voltage Transformation Credit - Facilities Charge", -0.012781, "$/kVA/day",
         "2026-01-01", None),
        ENX_BPA,
        ("rider", "Quarterly TAC Adjustment Rider", 0.00063, "$/kWh", "2026-10-01", "2026-12-31"),
        ("rider", "TAC Deferral Account Rider Adjustment", 0.001355, "$/kWh", "2026-01-01", "2026-12-31"),
    ],
    "D310": [
        ("fixed", "Service Charge", 26.041806, "$/day", "2026-01-01", None),
        ("demand", "Facilities Charge", 0.154031, "$/kVA/day", "2026-01-01", None),
        ("demand", "Non-Ratcheted Demand Charge", 0.050674, "$/kVA/day", "2026-01-01", None),
        ("transmission", "Transmission Demand Charge", 0.349342, "$/kVA/day", "2026-01-01", None),
        ("transmission", "Transmission Variable Charge - On Peak", 0.012021, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Variable Charge - Off Peak", 0.009074, "$/kWh", "2026-01-01", None),
        ENX_BPA,
        ("rider", "Quarterly TAC Adjustment Rider", 0.000682, "$/kWh", "2026-10-01", "2026-12-31"),
        ("rider", "TAC Deferral Account Rider Adjustment", 0.000165, "$/kWh", "2026-01-01", "2026-12-31"),
    ],
    "D410": [
        ("fixed", "Service Charge", 30.042872, "$/day", "2026-01-01", None),
        ("demand", "Facilities Charge", 0.02096, "$/kVA/day", "2026-01-01", None),
        ("demand", "Non-Ratcheted Demand Charge", 0.060423, "$/kVA/day", "2026-01-01", None),
        ("transmission", "Transmission Demand Charge", 0.308832, "$/kVA/day", "2026-01-01", None),
        ("transmission", "Transmission Variable Charge - On Peak", 0.010132, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Variable Charge - Off Peak", 0.007561, "$/kWh", "2026-01-01", None),
        ENX_BPA,
        ("rider", "Quarterly TAC Adjustment Rider", 0.000669, "$/kWh", "2026-10-01", "2026-12-31"),
        ("rider", "TAC Deferral Account Rider Adjustment", 0.000449, "$/kWh", "2026-01-01", "2026-12-31"),
    ],
}
ENX_RECORDS = {
    "D100": ("Residential Distribution (Rate D100)", "residential", "residential", "flat", "PDF pages 3-4, 18-20"),
    "D200": ("Small Commercial Distribution (Rate D200)", "commercial", "small commercial (< 5,000 kWh/month)", "flat",
             "PDF pages 5-6, 18-20"),
    "D300": ("Medium Commercial Distribution (Rate D300)", "commercial", "medium commercial (>= 5,000 kWh/month)",
             "demand", "PDF pages 7-8, 18-20"),
    "D310": ("Large Commercial Secondary Distribution (Rate D310)", "commercial", "large commercial secondary voltage",
             "mixed", "PDF pages 9-10, 18-20"),
    "D410": ("Large Commercial Primary Distribution (Rate D410)", "commercial", "large commercial primary voltage",
             "mixed", "PDF pages 11-12, 18-20"),
}


def ENX__fixture():
    return json.loads(ENX_FIXTURE.read_text(encoding="utf-8"))


def ENX__pages(edits=(), drop=()):
    pages = []
    for page in ENX__fixture()["pages"]:
        number, text = page["page_number"], page["text"]
        if number in drop:
            continue
        for target, old, new in edits:
            if target == number:
                assert old in text, (number, old)
                text = text.replace(old, new, 1)
        pages.append(DocumentPage(number, text))
    return pages


def ENX__parse(edits=(), drop=(), today=ENX_TODAY):
    records = ENX_parse_schedule_pages(ENX__pages(edits, drop), ENX__fixture()["source_url"], today)
    return {record.tariff_code: record for record in records}


def ENX__comp(record, name):
    (component,) = [c for c in record.components if c.component_name == name]
    return component


def test_enx_fixture_is_the_current_official_schedule():
    fixture = ENX__fixture()
    assert fixture["source_url"].startswith("https://assets.enmax.com/api/public/content/")
    assert fixture["landing_url"] == "https://www.enmax.com/tariffs"
    assert fixture["retrieved_on"] == "2026-10-09"
    numbers = [page["page_number"] for page in fixture["pages"]]
    assert {1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 18, 19, 20} <= set(numbers)
    assert "RATES IN EFFECT AS OF October 1, 2026" in fixture["pages"][0]["text"]


def test_enx_parses_the_five_building_classes_exactly():
    records = ENX__parse()
    assert set(records) == ENX_CODES
    for code, (name, customer_class, sub_class, structure, source_page) in ENX_RECORDS.items():
        record = records[code]
        assert (record.tariff_name, record.customer_class, record.sub_class, record.rate_structure,
                record.source_page) == (name, customer_class, sub_class, structure, source_page)
        assert (record.utility_name, record.province, record.utility_type) == ("ENMAX Power", "AB", "electricity")
        assert record.pricing_method == "regulated" and record.confidence == "high"
        assert record.effective_date == "2026-10-01" and record.end_date is None
        assert record.source_url == ENX__fixture()["source_url"]
        actual = [(c.component_type, c.component_name, c.charge_value, c.charge_unit, c.effective_date, c.end_date)
                  for c in record.components]
        assert actual == ENX_EXPECTED[code]


def test_enx_every_component_is_sourced_and_dated():
    source_url = ENX__fixture()["source_url"]
    for record in ENX__parse().values():
        for component in record.components:
            assert component.source_url == source_url
            assert component.source_detail.startswith("PDF page ")
            assert component.effective_date and component.confidence == "high"
            assert component.charge_value is not None and component.market_reference is None
    d300 = ENX__parse()["D300"]
    assert ENX__comp(d300, "Service Charge").source_detail == (
        "PDF page 7; Rate Code D300, Distribution Charge for Distribution Access Service")
    assert ENX__comp(d300, "Transmission Demand Charge").source_detail == (
        "PDF page 7; Rate Code D300, Transmission Charge for System Access Service")
    assert ENX__comp(d300, "Primary Voltage Transformation Credit - Service Charge").source_detail == (
        "PDF page 8; Rate Code D300, Other item 5 (primary voltage transformation credit)")
    assert ENX__comp(d300, "Quarterly TAC Adjustment Rider").source_detail == (
        "PDF page 19; Quarterly TAC Adjustment Rider, Rate Code D300, Q4 2026 column")
    assert ENX__comp(d300, "TAC Deferral Account Rider Adjustment").source_detail == (
        "PDF page 20; 2026 TAC Deferral Account Rider Adjustment, Rate Code D300")
    assert ENX__comp(d300, "Balancing Pool Allocation Rider").source_detail == (
        "PDF page 18; 2026 Balancing Pool Allocation Rider")


def test_enx_demand_units_conditions_and_tou_hours():
    records = ENX__parse()
    for code in ("D300", "D310", "D410"):
        for name in ("Facilities Charge", "Non-Ratcheted Demand Charge", "Transmission Demand Charge"):
            component = ENX__comp(records[code], name)
            assert component.demand_unit == "kVA" and component.charge_unit == "$/kVA/day"
        assert "Billing Demand" in ENX__comp(records[code], "Facilities Charge").notes
        assert "90% of the highest kVA demand in the last 365 days" in ENX__comp(records[code], "Facilities Charge").notes
        assert "Metered Demand" in ENX__comp(records[code], "Non-Ratcheted Demand Charge").notes
        assert records[code].demand_min_kw is None and records[code].demand_max_kw is None
    for name in ("Primary Voltage Transformation Credit - Service Charge",
                 "Primary Voltage Transformation Credit - Facilities Charge"):
        credit = ENX__comp(records["D300"], name)
        assert credit.sub_component == "conditional" and credit.charge_value < 0
        assert credit.notes.startswith("Conditional: only D300 sites that received primary voltage service before "
                                       "January 1, 2009")
    for code in ("D310", "D410"):
        on = ENX__comp(records[code], "Transmission Variable Charge - On Peak")
        off = ENX__comp(records[code], "Transmission Variable Charge - Off Peak")
        assert (on.tou_period, off.tou_period) == ("on-peak", "off-peak")
        assert on.tou_hours == ("8 a.m. to 9 p.m. Monday to Friday inclusive, excluding statutory holidays "
                                "(ISO Rules definition)")
    for code in ("D100", "D200", "D300"):
        assert not [c for c in records[code].components if c.tou_period]
    assert not [c for r in records.values() for c in r.components if c.sub_component and c.component_type != "rebate"]


def test_enx_eligibility_usage_and_notes():
    records = ENX__parse()
    assert (records["D200"].usage_min, records["D200"].usage_max, records["D200"].usage_unit) == (
        None, 5000.0, "kWh/month")
    assert (records["D300"].usage_min, records["D300"].usage_max, records["D300"].usage_unit) == (
        5000.0, None, "kWh/month")
    assert "150 kVA was not registered twice" in records["D300"].eligibility
    assert "greater than 150 kVA twice" in records["D310"].eligibility
    assert "served at primary voltage" in records["D410"].eligibility
    assert "domestic purposes" in records["D100"].eligibility
    assert "basement suite" in records["D100"].notes
    assert "bulk metering" in records["D300"].notes
    assert "supply all transformers" in records["D410"].notes
    for record in records.values():
        assert "AUC Decision 30299-D01-2025 effective January 1, 2026" in record.notes
        assert "in effect as of October 1, 2026" in record.notes
        assert "Conditional: the City of Calgary Local Access Fee (LAF)" in record.notes
        assert not [c for c in record.components if "Local Access" in c.component_name]
        assert "31033-D01-2026" in ENX__comp(record, "Quarterly TAC Adjustment Rider").notes


def test_enx_excluded_and_source_blocked_classes_are_not_emitted(caplog):
    caplog.set_level(logging.INFO, logger="scrapers.utilities.enmax_power")
    records = ENX__parse()
    assert not {"D500", "D600", "D700"} & set(records)
    assert "D700 (transmission connected) excluded" in caplog.text and "source-blocked" in caplog.text
    assert "D500 excluded" in caplog.text and "D600 excluded" in caplog.text


def test_enx_changed_values_propagate():
    records = ENX__parse(edits=[
        (3, "Service and Facilities Charge\tper day\t$0.769463", "Service and Facilities Charge\tper day\t$0.779463"),
        (19, "($0.001826)\t$0.000583", "($0.001826)\t($0.000583)"),
        (11, "Variable Charge Off Peak\tper kWh\t$0.007561", "Variable Charge Off Peak\tper kWh\t$0.007999"),
    ])
    assert set(records) == ENX_CODES
    assert ENX__comp(records["D100"], "Service and Facilities Charge").charge_value == 0.779463
    assert ENX__comp(records["D100"], "Quarterly TAC Adjustment Rider").charge_value == -0.000583
    assert ENX__comp(records["D410"], "Transmission Variable Charge - Off Peak").charge_value == 0.007999


@pytest.mark.parametrize(("drop", "rejected"), [
    ((3,), {"D100"}),
    ((4,), {"D100"}),
    ((8,), {"D300"}),
    ((10,), {"D310"}),
    ((12,), {"D410"}),
])
def test_enx_missing_page_rejects_only_that_class(drop, rejected):
    assert set(ENX__parse(drop=drop)) == ENX_CODES - rejected


@pytest.mark.parametrize(("edits", "rejected"), [
    ([(3, "System Usage Charge\tper kWh", "System Usage Charge\tper day")], {"D100"}),
    ([(9, "Facilities Charge\tper day per kVA of", "Facilities Charge\tper day per kW of")], {"D310"}),
    ([(8, "credit of $1.848798 per day applied", "credit of $1.848798 per month applied")], {"D300"}),
    ([(3, "System Usage Charge\tper kWh\t$0.015477",
       "System Usage Charge\tper kWh\t$0.015477\nCustomer Charge\tper day\t$1.000000")], {"D100"}),
    ([(5, "SMALL COMMERCIAL\nRATE CODE D200", "MEDIUM COMMERCIAL\nRATE CODE D200")], {"D200"}),
    ([(5, "less than 5,000 kWh per month", "less than 5,000 kWh per day")], {"D200"}),
    ([(10, "\u201cOff Peak\u201d is all Energy consumption not consumed in On Peak hours", "")], {"D310"}),
    ([(8, "(c) \u201cContract Demand\u201d is the kVA contracted for by the Customer", "")], {"D300"}),
    ([(4, "Page 4 of 20", "Page 5 of 20")], {"D100"}),
    ([(7, "$0.271085", "$0.271085 $0.100000")], {"D300"}),
    ([(19, "Small Commercial\tD200\tper kWh\t$0.001280\t($0.001419)\t($0.001776)\t$0.000602\n", "")], {"D200"}),
    ([(19, "($0.001776)\t$0.000602", "($0.001776)\t")], {"D200"}),
    ([(19, "($0.001705)\t$0.000630", "($0.001705)\t0.000630")], {"D300"}),
    ([(20, "Large Commercial - Primary\tD410\tper kWh\t$0.000449\n", "")], {"D410"}),
    ([(20, "D300\tper kWh\t$0.001355", "D300\tper kVA\t$0.001355")], {"D300"}),
    ([(7, "30299-D01-2025 effective January 1, 2026 and System", "30299-D01-2025 effective January 1, 2027 and System"),
      (8, "30299-D01-2025 effective January 1, 2026 and System", "30299-D01-2025 effective January 1, 2027 and System")],
     {"D300"}),
    ([(11, "effective January 1, 2026 and System", "effective January 1, 2025 and System")], {"D410"}),
])
def test_enx_wrong_unit_row_or_date_rejects_only_that_class(edits, rejected):
    assert set(ENX__parse(edits=edits)) == ENX_CODES - rejected


@pytest.mark.parametrize("edits", [
    [(19, "The rider is effective October 1, 2026.", "The rider is effective July 1, 2026.")],
    [(19, "Q4 Oct 1, 2026", "Q4 Nov 1, 2026")],
    [(19, "Quarterly TAC Adjustment Rider Charge / (Refund)", "Quarterly TAC Adjustment Rider")],
    [(20, "Adjustment Charge / (Refund)", "Adjustment")],
    [(18, "Balancing Pool Allocation\tper kWh", "Balancing Pool Allocation\tper kW")],
    [(18, "The rider is effective\nJanuary 1, 2026.", "The rider is effective\nJanuary 1, 2027.")],
    [(20, "effective January 1, 2026 to December", "effective January 1, 2027 to December")],
    [(20, "Rider will apply to all energy delivered", "Rider may apply to some energy delivered")],
])
def test_enx_garbled_required_rider_rejects_every_class(edits):
    assert ENX__parse(edits=edits) == {}


@pytest.mark.parametrize("drop", [(18,), (19,), (20,)])
def test_enx_missing_rider_page_rejects_every_class(drop):
    assert ENX__parse(drop=drop) == {}


def test_enx_missing_or_future_in_effect_date_rejects_the_document():
    assert ENX__parse(edits=[(1, "RATES IN EFFECT AS OF October 1, 2026", "RATES IN EFFECT")]) == {}
    assert ENX__parse(drop=(1,)) == {}
    assert ENX__parse(today=date(2026, 9, 30)) == {}
    assert set(ENX__parse(today=date(2026, 10, 1))) == ENX_CODES


def test_enx_stale_schedule_after_the_quarter_fails_closed():
    assert ENX__parse(today=date(2027, 1, 4)) == {}
    assert set(ENX__parse(today=date(2026, 12, 31))) == ENX_CODES


def test_enx_expired_deferral_rider_is_excluded_but_classes_stay_live():
    records = ENX__parse(edits=[(20, "to December\n31,2026.", "to September\n30,2026.")])
    assert set(records) == ENX_CODES
    for record in records.values():
        names = [c.component_name for c in record.components]
        assert "TAC Deferral Account Rider Adjustment" not in names
        assert "Quarterly TAC Adjustment Rider" in names and "Balancing Pool Allocation Rider" in names
        assert "to September 30, 2026) has ended and is not included" in record.notes
        assert record.source_page.endswith("18-19")


def test_enx_bpa_ineligible_class_keeps_live_record_without_that_rider():
    records = ENX__parse(edits=[(18, "2 D600 sites are ineligible", "2 D600 and D200 sites are ineligible")])
    assert set(records) == ENX_CODES
    assert "Balancing Pool Allocation Rider" not in [c.component_name for c in records["D200"].components]
    assert "Balancing Pool Allocation Rider" in [c.component_name for c in records["D100"].components]


def test_enx_quarter_column_is_chosen_by_position_with_later_quarters_blank():
    edits = [
        (1, "RATES IN EFFECT AS OF October 1, 2026", "RATES IN EFFECT AS OF July 1, 2026"),
        (19, "The rider is effective October 1, 2026.", "The rider is effective July 1, 2026."),
        (19, "31033-D01-2026\neffective October 1, 2026", "31033-D01-2026\neffective July 1, 2026"),
    ]
    for q3, q4 in (("($0.001826)", "$0.000583"), ("($0.001776)", "$0.000602"), ("($0.001705)", "$0.000630"),
                   ("($0.001608)", "$0.000682"), ("($0.001634)", "$0.000669"), ("($0.002554)", "$0.000426")):
        edits.append((19, q3 + "\t" + q4, q3 + "\t"))
    records = ENX__parse(edits=edits, today=date(2026, 7, 15))
    assert set(records) == ENX_CODES
    expected = {"D100": -0.001826, "D200": -0.001776, "D300": -0.001705, "D310": -0.001608, "D410": -0.001634}
    for code, value in expected.items():
        rider = ENX__comp(records[code], "Quarterly TAC Adjustment Rider")
        assert (rider.charge_value, rider.effective_date, rider.end_date) == (value, "2026-07-01", "2026-09-30")
        assert rider.source_detail.endswith("Q3 2026 column")
        assert records[code].effective_date == "2026-07-01"
    assert ENX__parse(edits=edits, today=date(2026, 10, 2)) == {}


def test_enx_unmodelled_current_rider_rejects_the_schedule_but_ended_riders_are_ignored():
    source_url = ENX__fixture()["source_url"]
    current = DocumentPage(21, "2026 NEW ADJUSTMENT RIDER\nRider will apply to all sites. The rider is effective "
                               "October 1, 2026.\nENMAX Power Corporation Distribution Tariff Page 21 of 21")
    assert ENX_parse_schedule_pages(ENX__pages() + [current], source_url, ENX_TODAY) == []
    ended = DocumentPage(21, "DAS ADJUSTMENT RIDER\nThe adjustment is effective January 1, 2025 to March 31, 2025.\n"
                             "ENMAX Power Corporation Distribution Tariff Page 21 of 21")
    assert {r.tariff_code for r in ENX_parse_schedule_pages(ENX__pages() + [ended], source_url, ENX_TODAY)} == ENX_CODES


def test_enx_current_link_discovery_prefers_the_current_label_and_enmax_hosts():
    fixture = ENX__fixture()
    assert ENX_current_tariff_link(fixture["landing_html"]) == fixture["source_url"]
    archive_only = fixture["landing_html"].replace("View current distribution tariff", "View distribution tariff")
    assert ENX_current_tariff_link(archive_only) is None
    foreign = '<a href="https://example.com/x.pdf">View current distribution tariff</a>'
    assert ENX_current_tariff_link(foreign) is None
    two = ('<a href="https://assets.enmax.com/a">View current distribution tariff</a>'
           '<a href="https://assets.enmax.com/b">Current distribution tariff</a>')
    assert ENX_current_tariff_link(two) is None
    relative = '<a href="/api/public/content/abc?v=1">View current distribution tariff</a>'
    assert ENX_current_tariff_link(relative) == "https://www.enmax.com/api/public/content/abc?v=1"


def ENX__word(text, x0, x1, top):
    return {"text": text, "x0": x0, "x1": x1, "top": top}


def test_enx_render_keeps_columns_for_top_aligned_and_centred_cells():
    words = [
        ENX__word("COMPONENT", 114.48, 166.81, 340.79), ENX__word("TYPE", 168.96, 188.83, 340.79),
        ENX__word("UNIT", 254.64, 275.29, 340.79), ENX__word("PRICE", 388.92, 412.39, 340.79),
        ENX__word("TRANSMISSION", 72.0, 149.87, 484.31), ENX__word("CHARGE", 152.16, 193.66, 484.31),
        ENX__word("FOR", 195.72, 216.16, 484.31), ENX__word("SYSTEM", 218.64, 258.53, 484.31),
        ENX__word("ACCESS", 260.64, 297.76, 484.31), ENX__word("SERVICE", 300.0, 340.06, 484.31),
        ENX__word("per", 254.88, 271.43, 500.0), ENX__word("day", 273.36, 290.92, 500.0),
        ENX__word("per", 292.8, 309.23, 500.0), ENX__word("kVA", 311.28, 330.47, 500.0), ENX__word("of", 332.4, 342.3, 500.0),
        ENX__word("Demand", 114.48, 155.82, 507.0), ENX__word("Charge", 158.52, 192.22, 507.0),
        ENX__word("$0.271085", 373.2, 420.44, 507.2),
        ENX__word("Billing", 254.88, 284.41, 514.0), ENX__word("Demand", 287.16, 328.02, 514.0),
        ENX__word("Variable", 114.48, 153.22, 535.22), ENX__word("Charge", 155.16, 188.38, 535.22),
        ENX__word("per", 245.88, 262.43, 535.22), ENX__word("kWh", 265.32, 287.22, 535.22),
        ENX__word("$0.012021", 373.32, 420.56, 535.22),
        ENX__word("On", 114.48, 128.7, 549.38), ENX__word("Peak", 131.52, 154.98, 549.38),
        ENX__word("Variable", 114.48, 154.06, 563.54), ENX__word("Charge", 156.12, 189.82, 563.54),
        ENX__word("Off", 191.88, 206.94, 563.54), ENX__word("per", 245.88, 262.43, 564.5), ENX__word("kWh", 265.32, 287.22, 564.5),
        ENX__word("$", 374.16, 380.0, 564.44), ENX__word("0.009074", 382.0, 420.8, 564.44),
        ENX__word("Peak", 114.48, 137.22, 576.26),
        ENX__word("Where", 72.0, 103.9, 601.87),
    ]
    assert ENX_render_page_words(words, [(590.0, ["Rate Code\tUnit", "D100\tper kWh"])]).splitlines() == [
        "COMPONENT TYPE UNIT PRICE",
        "TRANSMISSION CHARGE FOR SYSTEM ACCESS SERVICE",
        "\tper day per kVA of\t",
        "Demand Charge\t\t$0.271085",
        "\tBilling Demand\t",
        "Variable Charge\tper kWh\t$0.012021",
        "On Peak\t\t",
        "Variable Charge Off\tper kWh\t$ 0.009074",
        "Peak\t\t",
        "Rate Code\tUnit",
        "D100\tper kWh",
        "Where",
    ]


def ENX__scrape(monkeypatch, static, rendered=None, pages=None, today="2026-10-09"):
    fixture = ENX__fixture()
    scraper = ENX_ENMAXPowerScraper()
    calls = {"rendered": 0, "bytes": []}

    def fetch_page(url, delay=1.0):
        assert url == fixture["landing_url"]
        if isinstance(static, Exception):
            raise static
        return static

    def fetch_rendered_page(url, wait_selector=None, timeout_ms=30000):
        calls["rendered"] += 1
        return rendered

    def fetch_bytes(url, delay=1.0):
        calls["bytes"].append(url)
        return b"%PDF-1.7 fixture"

    monkeypatch.setattr(scraper, "fetch_page", fetch_page)
    monkeypatch.setattr(scraper, "fetch_rendered_page", fetch_rendered_page)
    monkeypatch.setattr(scraper, "fetch_bytes", fetch_bytes)
    monkeypatch.setattr(scraper, "now_iso", lambda: today + "T12:00:00+00:00")
    monkeypatch.setattr(ENX_enmax_power, "extract_schedule_pages", lambda data: ENX__pages() if pages is None else pages)
    return scraper.scrape(), calls


def ENX__assert_live(records):
    assert {record.tariff_code for record in records} <= ENX_CODES
    for record in records:
        assert record.notes.startswith("Provenance: live_parsed.") and "seed_fallback" not in record.notes
        assert record.confidence == "high"
        assert all(c.notes.startswith("Provenance: live_parsed.") for c in record.components)


def test_enx_scrape_static_discovery_marks_every_class_live(monkeypatch):
    records, calls = ENX__scrape(monkeypatch, ENX__fixture()["landing_html"])
    assert {record.tariff_code for record in records} == ENX_CODES
    ENX__assert_live(records)
    assert calls == {"rendered": 0, "bytes": [ENX__fixture()["source_url"]]}


def test_enx_scrape_uses_rendered_page_when_static_page_lacks_link_or_fails(monkeypatch):
    records, calls = ENX__scrape(monkeypatch, "<html><body>loading</body></html>", rendered=ENX__fixture()["landing_html"])
    assert {record.tariff_code for record in records} == ENX_CODES and calls["rendered"] == 1
    ENX__assert_live(records)
    records, calls = ENX__scrape(monkeypatch, requests.ConnectionError("down"), rendered=ENX__fixture()["landing_html"])
    assert {record.tariff_code for record in records} == ENX_CODES and calls["rendered"] == 1


def test_enx_scrape_partial_failure_drops_only_that_class_without_new_seed(monkeypatch):
    pages = ENX__pages(edits=[(3, "System Usage Charge\tper kWh", "System Usage Charge\tper day")])
    records, _ = ENX__scrape(monkeypatch, ENX__fixture()["landing_html"], pages=pages)
    assert {record.tariff_code for record in records} == ENX_CODES - {"D100"}
    ENX__assert_live(records)


def ENX__assert_seed(records):
    assert {record.tariff_code for record in records} == {"D110", "D210", "D310"}
    for record in records:
        assert record.confidence == "unverified" and "Provenance: seed_fallback" in record.notes
        assert all(c.confidence == "unverified" and "seed_fallback" in c.notes for c in record.components)


def test_enx_scrape_total_fetch_failure_returns_labelled_seeds(monkeypatch):
    records, calls = ENX__scrape(monkeypatch, requests.ConnectionError("down"), rendered=None)
    ENX__assert_seed(records)
    assert calls == {"rendered": 1, "bytes": []}


def test_enx_scrape_unusable_document_returns_labelled_seeds(monkeypatch):
    records, _ = ENX__scrape(monkeypatch, ENX__fixture()["landing_html"], pages=[])
    ENX__assert_seed(records)
    records, _ = ENX__scrape(monkeypatch, ENX__fixture()["landing_html"], today="2027-01-04")
    ENX__assert_seed(records)


# ======================================================================
# ATCO Electric price schedules (batch 12)
# ======================================================================
from scrapers.utilities import atco_electric as ATE_atco_electric
from scrapers.utilities.atco_electric import ATCOElectricScraper as ATE_ATCOElectricScraper, FALLBACK_RIDER_URLS as ATE_FALLBACK_RIDER_URLS, FALLBACK_SCHEDULES_URL as ATE_FALLBACK_SCHEDULES_URL, RATES_MODEL_URLS as ATE_RATES_MODEL_URLS, discover_documents as ATE_discover_documents
from scrapers.utils.parsing import DocumentPage
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest


ATE_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "atco_electric.json"
ATE_TODAY = date(2026, 10, 9)
ATE_CODES = {"D11", "D13", "D21", "D31", "T31"}


def ATE__document():
    return json.loads(ATE_FIXTURE.read_text(encoding="utf-8"))


def ATE__riders(document, drop=()):
    return [(rider["source_url"], [DocumentPage(**page) for page in rider["pages"]], rider["link_date"])
            for letter, rider in document["riders"].items() if letter not in drop]


def ATE__parse(document, today=ATE_TODAY, edition="2026-01-01", drop_riders=(), drop_pages=()):
    scraper = ATE_ATCOElectricScraper()
    pages = [DocumentPage(**page) for page in document["pages"] if page["page_number"] not in drop_pages]
    records = scraper.parse_schedule_pages(
        pages, document["source_url"], ATE__riders(document, drop_riders), today=today, edition_date=edition)
    return scraper, {record.tariff_code: record for record in records}


def ATE__edit(document, where, old, new):
    """Replace text on a price-schedules page (page number) or a separate rider PDF (rider letter)."""
    pages = document["riders"][where]["pages"] if isinstance(where, str) else [
        page for page in document["pages"] if page["page_number"] == where]
    assert old in pages[0]["text"]
    pages[0]["text"] = pages[0]["text"].replace(old, new)
    return document


def ATE__component(record, name):
    (component,) = [c for c in record.components if c.component_name == name]
    return component


def ATE__values(record):
    return [(c.component_type, c.component_name, c.charge_value, c.charge_unit, c.effective_date, c.end_date)
            for c in record.components]


def ATE__serve(document):
    served = {document["source_url"]: [DocumentPage(**page) for page in document["pages"]]}
    served.update({rider["source_url"]: [DocumentPage(**page) for page in rider["pages"]]
                   for rider in document["riders"].values()})
    return served, json.dumps(document["model_excerpt"])


def ATE__fake_fetch_page(model):
    def fetch(url, *args, **kwargs):
        if url != ATE_RATES_MODEL_URLS[0]:
            raise OSError(url)
        return model
    return fetch


def ATE__scrape(document, fetch_page=None):
    served, model = ATE__serve(document)
    scraper = ATE_ATCOElectricScraper()
    scraper.today = ATE_TODAY
    fetched = []
    with patch.object(scraper, "fetch_page", side_effect=fetch_page or ATE__fake_fetch_page(model)),\
            patch.object(scraper, "fetch_bytes", side_effect=lambda url, *a, **k: fetched.append(url) or url.encode()),\
            patch.object(ATE_atco_electric, "extract_pdf_pages", side_effect=lambda data: served[data.decode()]):
        records = scraper.scrape()
    return records, fetched, served


def test_ate_fixture_is_live_official_excerpt():
    document = ATE__document()
    assert document["source_url"] == ATE_FALLBACK_SCHEDULES_URL
    assert document["landing_url"] == "https://electric.atco.com/en-ca/understanding-rates/rates.html"
    assert document["retrieved_on"] == "2026-10-09" and document["edition_link_date"] == "2026-01-01"
    assert [page["page_number"] for page in document["pages"]] == [1, 2, 3, 4, 5, 6, 12, 13, 14, 15, 16, 53, 54, 55, 56]
    assert {letter: rider["source_url"] for letter, rider in document["riders"].items()} == ATE_FALLBACK_RIDER_URLS
    assert set(document["sha256"]) == {document["source_url"], *ATE_FALLBACK_RIDER_URLS.values()}
    assert "Approved in Disposition 31037-D01-2026" in document["riders"]["S"]["pages"][0]["text"]


def test_ate_discovery_reads_only_current_cards():
    found = ATE_discover_documents(ATE__document()["model_excerpt"])
    assert found["schedules"] == {ATE_FALLBACK_SCHEDULES_URL: "2026-01-01"}
    riders = found["riders"]
    assert set(riders) == {"A", "B", "G", "J", "Q", "S"}
    assert {letter: riders[letter] for letter in "BGSJ"} == {
        "B": {ATE_FALLBACK_RIDER_URLS["B"]: "2026-01-01"}, "G": {ATE_FALLBACK_RIDER_URLS["G"]: "2026-01-01"},
        "S": {ATE_FALLBACK_RIDER_URLS["S"]: "2026-10-01"}, "J": {ATE_FALLBACK_RIDER_URLS["J"]: "2025-09-01"}}
    assert all(not url.endswith("2026-07-01-rider-s.pdf") for links in riders.values() for url in links)


def test_ate_discovery_without_current_cards_returns_nothing():
    archived = ('<h4>Archived Rate Riders</h4><p><a href="/x/2026-07-01-rider-s.pdf">Rider S: SAS Deferral</a>'
                " - Effective July 1, 2026</p>")
    assert ATE_discover_documents({"card": {"description": archived}}) == {"schedules": {}, "riders": None}


def test_ate_building_classes_parsed_live():
    scraper, records = ATE__parse(ATE__document())
    assert set(records) == ATE_CODES and scraper.rejected == {}
    expected = {
        "D11": ("Standard Residential Service (Price Schedule D11)", "residential", "flat", None),
        "D13": ("Time of Use Residential Service (Price Schedule D13)", "residential", "tou", None),
        "D21": ("Standard Small General Service (Price Schedule D21)", "commercial", "demand", 500.0),
        "D31": ("Large General Service - Distribution Connected (Price Schedule D31)", "commercial", "demand", None),
        "T31": ("Large General Service - Transmission Connected (Price Schedule T31)", "industrial", "demand", None),
    }
    for code, (name, customer_class, structure, demand_max) in expected.items():
        record = records[code]
        assert (record.tariff_name, record.customer_class, record.rate_structure, record.demand_max_kw) == (
            name, customer_class, structure, demand_max)
        assert (record.province, record.utility_type, record.pricing_method, record.confidence) == (
            "AB", "electricity", "regulated", "high")
        assert record.effective_date == "2026-10-01" and record.source_url == ATE_FALLBACK_SCHEDULES_URL
        assert "Decision 30300-D01-2025 (dated December 12, 2025), effective 2026-01-01" in record.notes
        assert "Rate of Last Resort" in record.notes and record.notes.endswith("No bill total is calculated.")
    assert records["D11"].source_page == "PDF page 3; Price Schedule D11"
    assert records["D31"].source_page == "PDF pages 12-13; Price Schedule D31"
    assert records["T31"].source_page == "PDF pages 14-16; Price Schedule T31"


def test_ate_d11_exact_components():
    record = ATE__parse(ATE__document())[1]["D11"]
    assert ATE__values(record) == [
        ("fixed", "Distribution Customer Charge", 1.4125, "$/day", "2026-01-01", None),
        ("fixed", "Service Customer Charge", 0.2698, "$/day", "2026-01-01", None),
        ("transmission", "Transmission Energy Charge", 0.0479, "$/kWh", "2026-01-01", None),
        ("distribution", "Distribution Energy Charge", 0.0903, "$/kWh", "2026-01-01", None),
        ("rider", "Rider B - Balancing Pool Adjustment", 0.00133, "$/kWh", "2026-01-01", "2026-12-31"),
        ("rider", "Rider G - Temporary Adjustment", -0.00212, "$/kWh", "2026-01-01", "2026-12-31"),
        ("rider", "Rider S - SAS Deferral Adjustment", 0.00068, "$/kWh", "2026-10-01", None),
    ]
    assert ATE__component(record, "Distribution Customer Charge").source_detail == (
        "PDF page 3; Price Schedule D11, Distribution row, Customer Charge column")
    assert record.eligibility.endswith("Price Schedule D11 is not applicable for commercial or industrial use.")
    assert "Idle Service (Option F)" in record.notes


def test_ate_d13_time_of_use_periods():
    record = ATE__parse(ATE__document())[1]["D13"]
    energy = [(c.component_type, c.charge_value, c.tou_period, c.tou_hours) for c in record.components
              if c.charge_unit == "$/kWh" and c.component_type != "rider"]
    assert energy == [
        ("transmission", 0.0853, "on-peak", "4 p.m. to 9 p.m."),
        ("distribution", 0.161, "on-peak", "4 p.m. to 9 p.m."),
        ("transmission", 0.0341, "off-peak", "Before 4 p.m. and after 9 p.m."),
        ("distribution", 0.0644, "off-peak", "Before 4 p.m. and after 9 p.m."),
    ]
    assert [c.charge_value for c in record.components if c.charge_unit == "$/day"] == [1.4125, 0.2698]
    assert "available by request only and at the discretion of the company" in record.eligibility
    assert "Advanced Metering Infrastructure (AMI)" in record.eligibility
    assert "no weekday, weekend or holiday distinction" in record.notes


def test_ate_d21_demand_energy_blocks_and_billing_demand():
    record = ATE__parse(ATE__document())[1]["D21"]
    assert [(c.component_type, c.component_name, c.charge_value, c.charge_unit, c.tier_number, c.tier_threshold)
            for c in record.components if c.component_type != "rider"] == [
        ("fixed", "Distribution Customer Charge", 0.3806, "$/day", None, None),
        ("fixed", "Service Customer Charge", 0.3262, "$/day", None, None),
        ("transmission", "Transmission Demand Charge", 0.3158, "$/kW/day", None, None),
        ("demand", "Distribution Demand Charge", 0.3062, "$/kW/day", None, None),
        ("transmission", "Transmission Energy Charge (first 200 kWh per kW of billing demand)", 0.0058, "$/kWh", 1, 200.0),
        ("distribution", "Distribution Energy Charge (first 200 kWh per kW of billing demand)", 0.0426, "$/kWh", 1, 200.0),
        ("transmission", "Transmission Energy Charge (in excess of 200 kWh per kW of billing demand)", 0.0058, "$/kWh",
         2, 200.0),
    ]
    assert {c.tier_unit for c in record.components if c.tier_number} == {"kWh per kW of billing demand"}
    assert all(c.demand_unit == "kW" for c in record.components if c.charge_unit == "$/kW/day")
    assert "between the highest metered demand in the twelve-month period" in record.notes
    assert "(e) 5 kilowatts." in record.notes
    assert record.eligibility.endswith("Not applicable for any service in excess of 500 kW.")


def test_ate_d31_demand_blocks_and_conditional_power_factor():
    record = ATE__parse(ATE__document())[1]["D31"]
    assert [(c.component_type, c.component_name, c.charge_value, c.charge_unit, c.tier_number)
            for c in record.components if c.component_type != "rider"] == [
        ("fixed", "Distribution Customer Charge", 2.2294, "$/day", None),
        ("fixed", "Service Customer Charge", 1.7967, "$/day", None),
        ("transmission", "Transmission Demand Charge (first 500 kW of billing demand)", 0.3895, "$/kW/day", 1),
        ("demand", "Distribution Demand Charge (first 500 kW of billing demand)", 0.3441, "$/kW/day", 1),
        ("transmission", "Transmission Demand Charge (billing demand over 500 kW)", 0.4721, "$/kW/day", 2),
        ("demand", "Distribution Demand Charge (billing demand over 500 kW)", 0.2411, "$/kW/day", 2),
        ("demand", "Service Demand Charge (billing demand over 500 kW)", 0.0062, "$/kW/day", 2),
        ("transmission", "Transmission Energy Charge", 0.0058, "$/kWh", None),
        ("demand", "Charge for Deficient Power Factor", 0.3153, "$/kVA/day", None),
    ]
    power_factor = ATE__component(record, "Charge for Deficient Power Factor")
    assert power_factor.sub_component == "conditional" and power_factor.demand_unit == "kVA"
    assert power_factor.notes.startswith("Conditional: applies only when the customer's power factor is below 90%")
    assert "111% of the highest metered kW demand" in power_factor.notes
    assert power_factor.source_detail == "PDF page 13; Price Schedule D31, Charge for Deficient Power Factor"
    assert {c.tier_threshold for c in record.components if c.tier_number} == {500.0}
    assert record.demand_min_kw is None and record.demand_max_kw is None
    assert "The billing demand for the Transmission charges" in record.notes and "(f) 50 kilowatts." in record.notes


def test_ate_t31_includes_only_priced_distribution_and_service():
    record = ATE__parse(ATE__document())[1]["T31"]
    assert [(c.component_type, c.component_name, c.charge_value, c.charge_unit, c.tier_number, c.tier_threshold)
            for c in record.components if c.component_type != "rider"] == [
        ("demand", "Distribution Demand Charge (first 500 kW of billing demand)", 0.0083, "$/kW/day", 1, 500.0),
        ("demand", "Service Demand Charge (first 500 kW of billing demand)", 0.0824, "$/kW/day", 1, 500.0),
    ]
    assert not [c for c in record.components if c.component_type == "transmission" or c.charge_value is None]
    assert [(c.component_name, c.charge_value) for c in record.components if c.component_type == "rider"] == [
        ("Rider B - Balancing Pool Adjustment", 0.00126), ("Rider G - Temporary Adjustment", 0.0),
        ("Rider S - SAS Deferral Adjustment", 0.0)]
    assert "current AESO DTS Rate Schedule charges less the under frequency load shedding credit" in record.notes
    assert "printed 9.07 ¢/kW/day" in record.notes and "The billing demand for the Transmission charges" not in record.notes
    assert "directly connected to a transmission substation" in record.eligibility


def test_ate_riders_per_class_dates_and_sources():
    document = ATE__document()
    records = ATE__parse(document)[1]
    expected = {"D11": (0.00133, -0.00212, 0.00068), "D13": (0.00133, -0.00212, 0.00068),
                "D21": (0.00133, -0.00475, 0.00075), "D31": (0.00133, -0.00206, 0.00089), "T31": (0.00126, 0.0, 0.0)}
    for code, values in expected.items():
        riders = [c for c in records[code].components if c.component_type == "rider"]
        assert tuple(c.charge_value for c in riders) == values
        assert [c.source_url for c in riders] == [document["riders"][letter]["source_url"] for letter in "BGS"]
        assert [(c.effective_date, c.end_date) for c in riders] == [("2026-01-01", "2026-12-31")] * 2 + [("2026-10-01", None)]
        assert all(c.charge_unit == "$/kWh" and "same value in price-schedules PDF page" in c.source_detail for c in riders)
        assert "Q4-2026" in riders[2].notes and "Disposition 31037-D01-2026" in riders[2].notes
        assert "Rider J (PBR Re-Opener Refund) applied from 2025-09-01 to 2026-02-28 and has ended" in records[code].notes
        assert "Conditional: Rider A (Municipal Assessment" in records[code].notes
        assert not any(c.component_name.startswith(("Rider A", "Rider J")) for c in records[code].components)


def test_ate_components_sourced_dated_and_in_native_units():
    for record in ATE__parse(ATE__document())[1].values():
        assert record.effective_date == max(c.effective_date for c in record.components)
        for c in record.components:
            assert c.source_url and c.source_detail and c.effective_date and c.charge_value is not None
            assert c.charge_unit in {"$/day", "$/kWh", "$/kW/day", "$/kVA/day"}


def test_ate_published_schedules_audited():
    scraper, records = ATE__parse(ATE__document())
    assert set(scraper.excluded_published) == {
        "D22", "D23", "D24", "D25", "D26", "D32", "D33", "D34", "D41", "D44", "D51", "D52", "D56", "D61", "D63", "T33"}
    assert scraper.unmodelled_published == {} and "D22" not in records


def test_ate_value_change_propagates():
    document = ATE__edit(ATE__document(), 3, "Distribution 141.25 ¢/day 9.03 ¢/kW.h", "Distribution 141.35 ¢/day 9.03 ¢/kW.h")
    ATE__edit(document, 3, "TOTAL PRICE $1.6823 /day", "TOTAL PRICE $1.6833 /day")
    records = ATE__parse(document)[1]
    assert set(records) == ATE_CODES
    assert ATE__component(records["D11"], "Distribution Customer Charge").charge_value == 1.4135


@pytest.mark.parametrize(("page", "old", "new", "rejected"), [
    (3, "TOTAL PRICE $1.6823 /day 13.82 ¢/kW.h", "TOTAL PRICE $1.6823 /day 13.83 ¢/kW.h", "D11"),
    (3, "Transmission - 4.79 ¢/kW.h", "Transmission - 4.79 ¢/kW/day", "D11"),
    (3, "PBR Re-Opener Refund (Rider J)", "PBR Re-Opener Refund (Rider K)", "D11"),
    (4, "between the hours of 4 p.m.", "between the hours of 5 p.m.", "D13"),
    (5, "Effective: 2026 01 01", "Effective: 2027 01 01", "D21"),
    (5, "Not applicable for any service in excess of 500 kW.", "Not applicable for large services.", "D21"),
    (12, "Effective: 2026 01 01", "Effective: 2026", "D31"),
    (12, "Service 179.67 ¢/day - 0.62 ¢/kW/day -", "Service 179.67 ¢/day - 0.62 ¢/kW/day", "D31"),
    (13, "deficient power factor of 31.53", "deficient power factor of 31.35", "D31"),
    (14, "Service 8.24 ¢/kW/day - -", "Service 8.25 ¢/kW/day - -", "T31"),
    (14, "Distribution 0.83 ¢/kW/day - -", "Distribution 0.83 ¢/kW/day 0.10 ¢/kW/day -", "T31"),
    (14, "Charges per current", "Charges per", "T31"),
])
def test_ate_mutation_rejects_only_that_class(page, old, new, rejected):
    scraper, records = ATE__parse(ATE__edit(ATE__document(), page, old, new))
    assert set(records) == ATE_CODES - {rejected} and set(scraper.rejected) == {rejected}


@pytest.mark.parametrize(("dropped", "rejected"), [(3, "D11"), (4, "D13"), (13, "D31"), (15, "T31")])
def test_ate_missing_page_or_continuation_rejects_only_that_class(dropped, rejected):
    scraper, records = ATE__parse(ATE__document(), drop_pages=(dropped,))
    assert set(records) == ATE_CODES - {rejected} and set(scraper.rejected) == {rejected}


def test_ate_edition_mismatch_and_future_schedules_reject_all():
    scraper, records = ATE__parse(ATE__document(), edition="2025-01-01")
    assert records == {} and set(scraper.rejected) == ATE_CODES
    assert ATE__parse(ATE__document(), today=date(2025, 12, 31))[1] == {}


def test_ate_rider_copies_must_agree_for_the_class():
    scraper, records = ATE__parse(ATE__edit(ATE__document(), "S", "D21 Small General Service 0.075", "D21 Small General Service 0.076"))
    assert set(records) == ATE_CODES - {"D21"} and "disagree" in scraper.rejected["D21"]


def test_ate_rider_change_in_both_copies_propagates():
    document = ATE__edit(ATE__document(), "S", "D11 Residential 0.068", "D11 Residential 0.070")
    ATE__edit(document, 56, "D11 Residential 0.068", "D11 Residential 0.070")
    records = ATE__parse(document)[1]
    assert ATE__component(records["D11"], "Rider S - SAS Deferral Adjustment").charge_value == 0.0007
    assert ATE__component(records["D13"], "Rider S - SAS Deferral Adjustment").charge_value == 0.00068


def test_ate_missing_separate_rider_uses_bound_copy():
    rider = ATE__component(ATE__parse(ATE__document(), drop_riders=("S",))[1]["D11"], "Rider S - SAS Deferral Adjustment")
    assert (rider.charge_value, rider.source_url) == (0.00068, ATE_FALLBACK_SCHEDULES_URL)
    assert rider.source_detail == "PDF page 56; Rider S table, row D11"


def test_ate_rider_link_date_mismatch_ignores_that_copy():
    document = ATE__document()
    document["riders"]["S"]["link_date"] = "2026-07-01"
    rider = ATE__component(ATE__parse(document)[1]["D11"], "Rider S - SAS Deferral Adjustment")
    assert rider.source_url == ATE_FALLBACK_SCHEDULES_URL


def test_ate_rider_missing_everywhere_rejects_classes():
    scraper, records = ATE__parse(ATE__document(), drop_riders=("S",), drop_pages=(56,))
    assert records == {} and all("Rider S" in reason for reason in scraper.rejected.values())


def test_ate_rider_unit_change_in_both_copies_rejects_classes():
    document = ATE__edit(ATE__document(), "B", "Price Schedule Charge (¢/kW.h)", "Price Schedule Charge (%)")
    ATE__edit(document, 53, "Price Schedule Charge (¢/kW.h)", "Price Schedule Charge (%)")
    scraper, records = ATE__parse(document)
    assert records == {} and all("Rider B" in reason for reason in scraper.rejected.values())


def test_ate_missing_rider_row_rejects_only_that_class():
    document = ATE__edit(ATE__document(), "G", "D21 Small General Service -0.475\n", "")
    ATE__edit(document, 54, "D21 Small General Service -0.475\n", "")
    scraper, records = ATE__parse(document)
    assert set(records) == ATE_CODES - {"D21"} and "no D21 row" in scraper.rejected["D21"]


def test_ate_stale_quarterly_rider_fails_closed():
    scraper, records = ATE__parse(ATE__document(), today=date(2027, 1, 4))
    assert records == {}
    assert all("Rider S Q4-2026 ended 2026-12-31" in reason for reason in scraper.rejected.values())


def test_ate_newer_quarterly_rider_supersedes_and_ended_riders_become_notes():
    document = ATE__document()
    for old, new in (("effective October 1, 2026", "effective January 1, 2027"),
                     ("Effective: 2026 10 01", "Effective: 2027 01 01"), ("Q4-2026", "Q1-2027")):
        ATE__edit(document, "S", old, new)
    document["riders"]["S"]["link_date"] = "2027-01-01"
    record = ATE__parse(document, today=date(2027, 1, 4))[1]["D11"]
    assert [(c.component_name, c.effective_date) for c in record.components if c.component_type == "rider"] == [
        ("Rider S - SAS Deferral Adjustment", "2027-01-01")]
    assert "Rider B (Balancing Pool Adjustment) applied from 2026-01-01 to 2026-12-31 and has ended" in record.notes
    assert "Rider G (Temporary Adjustment) applied from 2026-01-01 to 2026-12-31 and has ended" in record.notes
    assert record.effective_date == "2027-01-01"


def test_ate_rider_j_included_only_while_in_effect():
    document = ATE__edit(ATE__document(), "J", "to February 28, 2026", "to February 28, 2027")
    ATE__edit(document, 55, "to February 28, 2026", "to February 28, 2027")
    rider = ATE__component(ATE__parse(document)[1]["D21"], "Rider J - PBR Re-Opener Refund")
    assert (rider.charge_value, rider.charge_unit, rider.effective_date, rider.end_date) == (
        -13.5, "%", "2025-09-01", "2027-02-28")
    assert rider.notes.startswith("Percentage of total base Distribution and Service Component charges")


def test_ate_scrape_discovers_documents_and_marks_live():
    records, fetched, served = ATE__scrape(ATE__document())
    assert {record.tariff_code for record in records} == ATE_CODES
    assert all("Provenance: live_parsed" in r.notes and "seed_fallback" not in r.notes for r in records)
    assert all("Provenance: live_parsed" in c.notes for r in records for c in r.components)
    assert sorted(fetched) == sorted(served)
    assert not any(record.tariff_name.startswith(("Residential Distribution", "Small General Service Distribution"))
                   for record in records)


def test_ate_scrape_uses_last_known_links_when_discovery_fails():
    records, fetched, _ = ATE__scrape(ATE__document(), fetch_page=OSError("rates page down"))
    assert {record.tariff_code for record in records} == ATE_CODES
    assert fetched[0] == ATE_FALLBACK_SCHEDULES_URL


def test_ate_scrape_drops_failed_class_without_seed():
    records, _, _ = ATE__scrape(ATE__edit(ATE__document(), 3, "13.82 ¢/kW.h", "13.83 ¢/kW.h"))
    assert {record.tariff_code for record in records} == ATE_CODES - {"D11"}
    assert not any("seed_fallback" in record.notes for record in records)


def test_ate_total_fetch_failure_returns_labelled_seeds():
    scraper = ATE_ATCOElectricScraper()
    with patch.object(scraper, "fetch_page", side_effect=OSError("down")),\
            patch.object(scraper, "fetch_bytes", side_effect=OSError("down")):
        records = scraper.scrape()
    assert [record.tariff_code for record in records] == ["D11", "D21", "D31"]
    assert all(r.confidence == "unverified" and "Provenance: seed_fallback" in r.notes for r in records)
    assert all(c.confidence == "unverified" for r in records for c in r.components)


def test_ate_unreadable_schedules_pdf_returns_labelled_seeds():
    scraper = ATE_ATCOElectricScraper()
    scraper.today = ATE_TODAY
    with patch.object(scraper, "fetch_page", side_effect=OSError("down")),\
            patch.object(scraper, "fetch_bytes", return_value=b"not a pdf"),\
            patch.object(ATE_atco_electric, "extract_pdf_pages", return_value=[]):
        records = scraper.scrape()
    assert len(records) == 3 and all("Provenance: seed_fallback" in record.notes for record in records)


# ======================================================================
# EPCOR Distribution DAS/SAS interim tariffs (batch 12)
# ======================================================================
from scrapers.utils.parsing import DocumentPage
from scrapers.utilities.epcor_distribution import AESO_POOL_PRICE_URL as EPD_AESO_POOL_PRICE_URL, DISCOVERY_URL as EPD_DISCOVERY_URL, EPCORDistributionScraper as EPD_EPCORDistributionScraper, discover_editions as EPD_discover_editions, parse_tariff_pages as EPD_parse_tariff_pages
import json
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest


EPD_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "epcor_distribution.json"
EPD_TODAY = date(2026, 10, 9)
EPD_CODES = ["DAS-R", "DAS-SC", "DAS-MC", "DAS-TOU", "DAS-TOUP"]
EPD_SEED_CODES = ["D100", "D200", "D300"]
EPD_RIDER_G = "Rider G - Balancing Pool Rider"
EPD_RIDER_J = "Rider J - SAS True-Up Rider"
EPD_RIDER_K = "Rider K - Transmission Charge Deferral Account True-Up Rider"
EPD_ON_PEAK_HOURS = "between 8:00 a.m. and 9:00 p.m. Monday to Friday, excluding statutory holidays"

# (component_type, component_name, value, unit, effective_date, end_date)
EPD_EXPECTED = {
    "DAS-R": [
        ("fixed", "Distribution Customer Charge", 0.72856, "$/day", "2026-01-01", None),
        ("distribution", "Distribution Energy Charge", 0.01783, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Energy Charge", 0.0405, "$/kWh", "2026-01-01", None),
        ("rider", EPD_RIDER_G, 0.0013, "$/kWh", "2026-01-01", "2026-12-31"),
        ("rider", EPD_RIDER_J, -0.00016, "$/kWh", "2026-01-01", "2026-12-31"),
        ("rider", EPD_RIDER_K, 0.00103, "$/kWh", "2026-10-01", None),
    ],
    "DAS-SC": [
        ("fixed", "Distribution Customer Charge", 0.64111, "$/day", "2026-01-01", None),
        ("distribution", "Distribution Energy Charge", 0.03351, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Energy Charge", 0.043, "$/kWh", "2026-01-01", None),
        ("rider", EPD_RIDER_G, 0.0013, "$/kWh", "2026-01-01", "2026-12-31"),
        ("rider", EPD_RIDER_J, -0.00001, "$/kWh", "2026-01-01", "2026-12-31"),
        ("rider", EPD_RIDER_K, 0.00113, "$/kWh", "2026-10-01", None),
    ],
    "DAS-MC": [
        ("fixed", "Distribution Customer Charge", 1.94742, "$/day", "2026-01-01", None),
        ("demand", "Distribution Demand Charge", 0.27106, "$/kVA/day", "2026-01-01", None),
        ("distribution", "Distribution Energy Charge", 0.0, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Capacity Charge", 0.11085, "$/kVA/day", "2026-01-01", None),
        ("transmission", "Transmission Energy Charge", 0.00668, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Demand Charge", 0.21567, "$/kVA/day", "2026-01-01", None),
        ("rider", EPD_RIDER_G, 0.0013, "$/kWh", "2026-01-01", "2026-12-31"),
        ("rider", EPD_RIDER_J, 0.00064, "$/kWh", "2026-01-01", "2026-12-31"),
        ("rider", EPD_RIDER_K, 0.00113, "$/kWh", "2026-10-01", None),
    ],
    "DAS-TOU": [
        ("fixed", "Distribution Customer Charge", 43.4621, "$/day", "2026-01-01", None),
        ("demand", "Distribution Demand Charge", 0.22878, "$/kW/day", "2026-01-01", None),
        ("distribution", "Distribution On-Peak Energy Charge", 0.0, "$/kWh", "2026-01-01", None),
        ("distribution", "Distribution Off-Peak Energy Charge", 0.0, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Energy Charge", 0.00253, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Capacity Charge", 0.12868, "$/kW/day", "2026-01-01", None),
        ("transmission", "Transmission Other System Support (OSS) Charge", 0.00107, "$/kW/day", "2026-01-01", None),
        ("transmission", "Transmission Operating Reserve Charge", None, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Demand Charge", 0.24154, "$/kW/day", "2026-01-01", None),
        ("rider", EPD_RIDER_G, 0.00129, "$/kWh", "2026-01-01", "2026-12-31"),
        ("rider", EPD_RIDER_J, -0.0012, "$/kWh", "2026-01-01", "2026-12-31"),
        ("rider", EPD_RIDER_K, 0.00255, "$/kWh", "2026-10-01", None),
    ],
    "DAS-TOUP": [
        ("fixed", "Distribution Customer Charge", 67.45678, "$/day", "2026-01-01", None),
        ("demand", "Distribution Demand Charge", 0.13822, "$/kW/day", "2026-01-01", None),
        ("distribution", "Distribution On-Peak Energy Charge", 0.0, "$/kWh", "2026-01-01", None),
        ("distribution", "Distribution Off-Peak Energy Charge", 0.0, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Energy Charge", 0.0025, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Capacity Charge", 0.13497, "$/kW/day", "2026-01-01", None),
        ("transmission", "Transmission Other System Support (OSS) Charge", 0.00112, "$/kW/day", "2026-01-01", None),
        ("transmission", "Transmission Operating Reserve Charge", None, "$/kWh", "2026-01-01", None),
        ("transmission", "Transmission Demand Charge", 0.28126, "$/kW/day", "2026-01-01", None),
        ("rider", EPD_RIDER_G, 0.00128, "$/kWh", "2026-01-01", "2026-12-31"),
        ("rider", EPD_RIDER_J, -0.00024, "$/kWh", "2026-01-01", "2026-12-31"),
        ("rider", EPD_RIDER_K, 0.00259, "$/kWh", "2026-10-01", None),
    ],
}

# code -> (tariff_name, customer_class, sub_class, rate_structure)
EPD_EXPECTED_RECORDS = {
    "DAS-R": ("Residential Distribution and Transmission (DAS-R)", "residential", "single household", "flat"),
    "DAS-SC": ("Commercial/Industrial <50 kVA Distribution and Transmission (DAS-SC)", "commercial",
               "small commercial/industrial (<50 kVA)", "flat"),
    "DAS-MC": ("Commercial/Industrial 50 kVA to <150 kVA Distribution and Transmission (DAS-MC)", "commercial",
               "medium commercial/industrial (50 to <150 kVA)", "demand"),
    "DAS-TOU": ("Commercial/Industrial 150 kVA to <5,000 kVA Secondary Distribution and Transmission (DAS-TOU)",
                "commercial", "large commercial/industrial, secondary voltage (150 to <5,000 kVA)", "demand"),
    "DAS-TOUP": ("Primary Commercial/Industrial >=150 kVA Distribution and Transmission (DAS-TOUP)", "commercial",
                 "commercial/industrial, primary voltage (>=150 kVA)", "demand"),
}


def EPD__fixture():
    return json.loads(EPD_FIXTURE.read_text(encoding="utf-8"))


def EPD__inputs(document=None):
    document = document or EPD__fixture()
    pages = {kind: [DocumentPage(page["page_number"], page["text"]) for page in doc["pages"]]
             for kind, doc in document["documents"].items()}
    labels = {kind: datetime.strptime(text, "%B %Y").date() for kind, text in document["labels"].items()}
    return pages, dict(document["source_urls"]), labels


def EPD__parse(pages=None, today=EPD_TODAY, labels=None, riders=None):
    base_pages, urls, base_labels = EPD__inputs()
    pages = pages or base_pages
    rider_pages = riders if riders is not None else {"G": pages["G"], "J": pages["J"], "K": pages["K"], "DJ": None}
    records = EPD_parse_tariff_pages(pages["DAS"], pages["SAS"], rider_pages, urls, today=today,
                                 labels=base_labels if labels is None else labels)
    return {record.tariff_code: record for record in records}


def EPD__mutate(kind, page_number, old, new, pages=None):
    pages = pages or EPD__inputs()[0]
    (target,) = [page for page in pages[kind] if page.page_number == page_number]
    assert old in target.text
    pages[kind] = [DocumentPage(page.page_number, page.text.replace(old, new, 1)) if page is target else page
                   for page in pages[kind]]
    return pages


def EPD__drop(kind, page_number):
    pages = EPD__inputs()[0]
    pages[kind] = [page for page in pages[kind] if page.page_number != page_number]
    return pages


def EPD__component(record, name):
    (component,) = [c for c in record.components if c.component_name == name]
    return component


def test_epd_fixture_matches_discovery_page():
    document = EPD__fixture()
    assert document["landing_url"] == EPD_DISCOVERY_URL and document["retrieved_on"] == "2026-10-09"
    editions = EPD_discover_editions(document["landing_html"])
    assert set(editions) == {"DAS", "SAS", "G", "J", "K", "DJ"}
    for kind, doc in document["documents"].items():
        current = [edition for edition in editions[kind] if edition.label_date <= EPD_TODAY][0]
        assert current.url == doc["source_url"] == document["source_urls"][kind]
        assert current.label == doc["label"] == document["labels"][kind]
    assert editions["DJ"][0].label == document["labels"]["DJ"] == "January 2020"


def test_epd_discovery_selects_newest_edition_in_effect():
    editions = EPD_discover_editions(EPD__fixture()["landing_html"])
    assert [edition.label for edition in editions["K"]] == ["October 2026", "July 2026", "April 2026"]
    assert [edition.label for edition in editions["K"] if edition.label_date <= date(2026, 9, 30)][0] == "July 2026"
    assert editions["DAS"][0].url.endswith("/2026-01-distribution-access-service-tariff.pdf")
    assert editions["SAS"][0].url.endswith("/2026-01-system-access-service-tariff.pdf")


def test_epd_discovery_drops_mislabelled_document():
    html = EPD__fixture()["landing_html"].replace("October 2026", "November 2026")
    assert [edition.label for edition in EPD_discover_editions(html)["K"]] == ["July 2026", "April 2026"]


def test_epd_exact_records_and_components():
    records = EPD__parse()
    assert list(records) == EPD_CODES
    for code, expected in EPD_EXPECTED.items():
        record = records[code]
        assert [(c.component_type, c.component_name, c.charge_value, c.charge_unit, c.effective_date, c.end_date)
                for c in record.components] == expected
        name, customer_class, sub_class, structure = EPD_EXPECTED_RECORDS[code]
        assert (record.tariff_name, record.customer_class, record.sub_class, record.rate_structure) == (
            name, customer_class, sub_class, structure)
        assert (record.utility_name, record.province, record.utility_type) == ("EPCOR Distribution", "AB", "electricity")
        assert record.pricing_method == "regulated" and record.effective_date == "2026-10-01"
        assert record.end_date is None and record.demand_min_kw is None and record.demand_max_kw is None
        assert record.confidence == "medium" and all(c.confidence == "medium" for c in record.components)


def test_epd_eligibility_from_schedules():
    records = EPD__parse()
    assert "single and separate household" in records["DAS-R"].eligibility
    assert "less than 50 kVA" in records["DAS-SC"].eligibility
    assert "at least 50 kVA and less than 150 kVA" in records["DAS-MC"].eligibility
    assert "at least 150 kVA and less than 5,000 kVA" in records["DAS-TOU"].eligibility
    assert "secondary voltage" in records["DAS-TOU"].eligibility
    assert "primary voltage" in records["DAS-TOUP"].eligibility
    assert "Electric Service Agreement" in records["DAS-TOUP"].eligibility


def test_epd_component_sources_and_details():
    records = EPD__parse()
    urls = EPD__fixture()["source_urls"]
    for record in records.values():
        assert record.source_url == urls["DAS"]
        for c in record.components:
            assert c.source_url and c.source_detail and c.effective_date
    residential = records["DAS-R"]
    customer = EPD__component(residential, "Distribution Customer Charge")
    assert customer.source_url == urls["DAS"]
    assert customer.source_detail == ("DAS tariff PDF page 3 (Price Schedule DAS-R, cell DAS-R1) and page 25 "
                                      "(Table 1)")
    transmission = EPD__component(residential, "Transmission Energy Charge")
    assert transmission.source_url == urls["SAS"]
    assert transmission.source_detail == ("SAS tariff PDF page 3 (Price Schedule SAS-R, cell SAS-R1) and page 25 "
                                          "(Table 3)")
    rider = EPD__component(residential, EPD_RIDER_K)
    assert rider.source_url == urls["K"]
    assert rider.source_detail == "Rider K PDF page 1 (row SAS-R, Energy Charge)"
    assert records["DAS-TOU"].source_page == "DAS tariff PDF pages 6, 7; SAS tariff PDF pages 6, 7"


def test_epd_operating_reserve_is_value_less_market_component():
    records = EPD__parse()
    for code, percent in (("DAS-TOU", "8.09"), ("DAS-TOUP", "7.99")):
        reserve = EPD__component(records[code], "Transmission Operating Reserve Charge")
        assert reserve.charge_value is None and reserve.component_type == "transmission"
        assert reserve.market_reference == "AESO pool price x " + percent + "% (operating reserve)"
        assert reserve.market_source_url == EPD_AESO_POOL_PRICE_URL
        assert "Market-indexed" in reserve.notes and "no value is shown" in reserve.notes
        assert "Variable" in records[code].notes
    for code in ("DAS-R", "DAS-SC", "DAS-MC"):
        assert not [c for c in records[code].components if c.market_reference or c.charge_value is None]


def test_epd_tou_periods_and_demand_units():
    records = EPD__parse()
    for code in ("DAS-TOU", "DAS-TOUP"):
        on_peak = EPD__component(records[code], "Distribution On-Peak Energy Charge")
        off_peak = EPD__component(records[code], "Distribution Off-Peak Energy Charge")
        assert (on_peak.tou_period, on_peak.tou_hours) == ("on-peak", EPD_ON_PEAK_HOURS)
        assert off_peak.tou_period == "off-peak" and "outside On-Peak" in off_peak.tou_hours
        for name in ("Distribution Demand Charge", "Transmission Capacity Charge", "Transmission Demand Charge",
                     "Transmission Other System Support (OSS) Charge"):
            assert EPD__component(records[code], name).demand_unit == "kW"
        assert "50 kilowatts" in EPD__component(records[code], "Distribution Demand Charge").notes
    medium = records["DAS-MC"]
    for name in ("Distribution Demand Charge", "Transmission Capacity Charge", "Transmission Demand Charge"):
        assert EPD__component(medium, name).demand_unit == "kVA"
    assert "85% of the highest metered demand" in EPD__component(medium, "Distribution Demand Charge").notes
    assert "90% of the highest metered demand" in EPD__component(medium, "Transmission Capacity Charge").notes
    assert "or 5 kVA" in EPD__component(medium, "Transmission Capacity Charge").notes
    assert "Peak Metered Demand" in EPD__component(medium, "Transmission Demand Charge").notes


def test_epd_interim_and_rider_notes():
    records = EPD__parse()
    for code, record in records.items():
        assert "Interim:" in record.notes and "(2026 INTERIM RATE)" in record.notes and "AUC" in record.notes
        assert "Local Access Fee (Rider LAF)" in record.notes and "not shown as a component" in record.notes
        assert "Rider DG (Temporary Adjustment): N/A for " + code in record.notes
        assert ("Rider DJ (DAS True-up Rider): no edition posted for the current tariff period "
                "(latest posted edition: January 2020); not applied.") in record.notes
        assert ("Rider E (Special Facilities Charge)" in record.notes) == (code in ("DAS-TOU", "DAS-TOUP"))
        assert all("2026 interim rate" in c.notes for c in record.components if c.component_type != "rider")
    assert "DAS-R: The minimum daily charge is the customer charge." in records["DAS-R"].notes
    assert "A negative value is a credit." in EPD__component(records["DAS-R"], EPD_RIDER_J).notes
    assert "Proceeding 30427" in EPD__component(records["DAS-R"], EPD_RIDER_G).notes
    assert "(no end date printed)" in EPD__component(records["DAS-R"], EPD_RIDER_K).notes


def test_epd_excluded_classes_are_not_emitted():
    records = EPD__parse()
    assert set(records) == set(EPD_CODES)
    for record in records.values():
        assert not any(word in record.tariff_name for word in ("Lighting", "Generator", "Direct", "Traffic"))


def test_epd_value_changes_propagate():
    pages = EPD__mutate("DAS", 3, "$0.72856 $0.01783", "$0.72856 $0.01790")
    pages = EPD__mutate("DAS", 25, "DAS-R2 $0.01783", "DAS-R2 $0.01790", pages)
    pages = EPD__mutate("SAS", 6, "$0.00107 8.09%", "$0.00107 8.19%", pages)
    pages = EPD__mutate("SAS", 25, "SAS-TOU4 8.09%", "SAS-TOU4 8.19%", pages)
    pages = EPD__mutate("K", 1, "SAS-R $0.00103", "SAS-R $0.00109", pages)
    records = EPD__parse(pages)
    assert list(records) == EPD_CODES
    assert EPD__component(records["DAS-R"], "Distribution Energy Charge").charge_value == 0.0179
    assert EPD__component(records["DAS-R"], EPD_RIDER_K).charge_value == 0.00109
    reserve = EPD__component(records["DAS-TOU"], "Transmission Operating Reserve Charge")
    assert reserve.market_reference == "AESO pool price x 8.19% (operating reserve)"


@pytest.mark.parametrize(("kind", "page_number", "old", "new", "rejected"), [
    ("DAS", 25, "DAS-R2 $0.01783", "DAS-R2 $0.01790", "DAS-R"),
    ("SAS", 25, "SAS-MC3 $0.21567", "SAS-MC3 $0.21000", "DAS-MC"),
    ("DAS", 25, "DAS-MC2 $0.27106 per kVA per Day", "DAS-MC2 $0.27106 per kW per Day", "DAS-MC"),
    ("SAS", 25, "SAS-TOU2 $0.12868 /kW/day of Capacity Charge", "SAS-TOU2 $0.12868 /kVA/day of Capacity Charge",
     "DAS-TOU"),
    ("DAS", 4, "Price Schedule DAS-SC Effective: January 1, 2026", "Price Schedule DAS-SC", "DAS-SC"),
    ("SAS", 5, "Price Schedule SAS-MC Effective: January 1, 2026", "Price Schedule SAS-MC Effective: January 1, 2027",
     "DAS-MC"),
    ("DAS", 4, "normal maximum demand of less than 50 kVA", "normal maximum demand of less than 75 kVA", "DAS-SC"),
    ("DAS", 8, "On-Peak is all energy consumption", "Peak is all energy consumption", "DAS-TOUP"),
    ("DAS", 6, "DAS-TOU4*", "DAS-TOU4* DAS-TOU5*", "DAS-TOU"),
    ("SAS", 3, "Short Term Adjustment (Rider K)", "Short Term Adjustment (Rider K) Other Adjustment (Rider M)", "DAS-R"),
    ("G", 1, "SAS-MC $0.00130 N/A N/A N/A", "", "DAS-MC"),
    ("G", 1, "SAS-R $0.00130 N/A N/A N/A", "SAS-R $0.00130 $0.01000 N/A N/A", "DAS-R"),
    ("J", 1, "SAS-SC $(0.00001) N/A N/A N/A", "SAS-SC - N/A N/A N/A", "DAS-SC"),
])
def test_epd_drift_rejects_only_that_class(kind, page_number, old, new, rejected):
    records = EPD__parse(EPD__mutate(kind, page_number, old, new))
    assert list(records) == [code for code in EPD_CODES if code != rejected]


@pytest.mark.parametrize(("kind", "page_number", "rejected"), [
    ("DAS", 4, "DAS-SC"),
    ("SAS", 5, "DAS-MC"),
    ("DAS", 7, "DAS-TOU"),
    ("SAS", 9, "DAS-TOUP"),
])
def test_epd_missing_schedule_or_continuation_page_rejects_only_that_class(kind, page_number, rejected):
    assert list(EPD__parse(EPD__drop(kind, page_number))) == [code for code in EPD_CODES if code != rejected]


def test_epd_rider_e_terms_required_for_large_classes():
    records = EPD__parse(EPD__mutate("DAS", 20, "negotiated between the customer and the Company", "set by the Company"))
    assert list(records) == ["DAS-R", "DAS-SC", "DAS-MC"]


def test_epd_tariff_level_failures_reject_everything():
    labels = EPD__inputs()[2]
    assert EPD__parse(today=date(2025, 12, 31)) == {}
    assert EPD__parse(labels=dict(labels, DAS=date(2026, 2, 1))) == {}
    assert EPD__parse(EPD__mutate("DAS", 1, "Effective January 1, 2026", "")) == {}
    assert EPD__parse(EPD__drop("SAS", 25)) == {}


def test_epd_rider_editions_and_periods():
    pages, _, labels = EPD__inputs()
    expired = EPD__parse(today=date(2027, 1, 5))
    assert list(expired) == EPD_CODES
    for record in expired.values():
        names = [c.component_name for c in record.components]
        assert EPD_RIDER_G not in names and EPD_RIDER_J not in names and EPD_RIDER_K in names
        assert "Rider G (Balancing Pool Rider): edition ended December 31, 2026; not applied." in record.notes
    assert EPD__parse(labels=dict(labels, K=date(2026, 7, 1))) == {}
    future = EPD__mutate("K", 1, "True-Up Rider Effective: October 1, 2026", "True-Up Rider Effective: October 15, 2026")
    assert EPD__parse(future) == {}
    assert EPD__parse(riders={"G": pages["G"], "J": pages["J"], "K": [], "DJ": None}) == {}
    assert EPD__parse(riders={"G": pages["G"], "J": pages["J"], "DJ": None}) == {}
    without_k = EPD__parse(riders={"G": pages["G"], "J": pages["J"], "K": None, "DJ": None})
    assert list(without_k) == EPD_CODES
    for record in without_k.values():
        assert EPD_RIDER_K not in [c.component_name for c in record.components]
        assert record.effective_date == "2026-01-01" and "Rider K (" in record.notes


def test_epd_rider_edition_older_than_tariff_or_self_contradictory():
    labels = EPD__inputs()[2]
    older = EPD__mutate("G", 1, "Balancing Pool Rider Effective: January 1, 2026",
                    "Balancing Pool Rider Effective: December 1, 2025")
    older = EPD__mutate("G", 1, "effective January 1, 2026 to December 31, 2026",
                    "effective December 1, 2025 to December 31, 2026", older)
    records = EPD__parse(older, labels=dict(labels, G=date(2025, 12, 1)))
    assert list(records) == EPD_CODES
    for record in records.values():
        assert EPD_RIDER_G not in [c.component_name for c in record.components]
        assert ("Rider G (Balancing Pool Rider): latest edition (December 1, 2025) predates the current tariff; "
                "not applied.") in record.notes
    contradictory = EPD__mutate("G", 1, "effective January 1, 2026 to December 31, 2026",
                            "effective February 1, 2026 to December 31, 2026")
    assert EPD__parse(contradictory) == {}


def test_epd_rider_values_in_other_columns():
    tou = EPD__parse(EPD__mutate("G", 1, "SAS-TOU $0.00129 N/A N/A N/A", "SAS-TOU $0.00129 $0.01000 N/A N/A"))["DAS-TOU"]
    demand = EPD__component(tou, EPD_RIDER_G + " (Demand Charge per kW or kVA per Day)")
    assert (demand.charge_value, demand.charge_unit, demand.demand_unit) == (0.01, "$/kW/day", "kW")
    residential = EPD__parse(EPD__mutate("DAS", 21, "DAS-R N/A N/A N/A N/A N/A", "DAS-R N/A N/A $0.00100 N/A N/A"))["DAS-R"]
    dg = EPD__component(residential, "Rider DG - Temporary Adjustment")
    assert (dg.charge_value, dg.charge_unit, dg.effective_date) == (0.001, "$/kWh", "2026-01-01")
    assert dg.source_detail == "DAS tariff PDF page 21, Rider DG table (row DAS-R, Per kWh of Total Energy)"
    assert "Rider DG (Temporary Adjustment): N/A for DAS-R" not in residential.notes


def test_epd_interim_marker_drives_confidence():
    pages = EPD__mutate("DAS", 3, "RESIDENTIAL SERVICE (2026 INTERIM RATE)", "RESIDENTIAL SERVICE")
    pages = EPD__mutate("SAS", 3, "RESIDENTIAL SERVICE (2026 INTERIM RATE)", "RESIDENTIAL SERVICE", pages)
    records = EPD__parse(pages)
    residential = records["DAS-R"]
    assert residential.confidence == "high" and "Interim:" not in residential.notes
    assert all(c.confidence == "high" for c in residential.components)
    assert records["DAS-SC"].confidence == "medium"


def test_epd_scrape_live_from_fixture():
    document = EPD__fixture()
    pages, urls, _ = EPD__inputs(document)
    by_url = {urls[kind]: pages[kind] for kind in pages}
    fetched = []
    scraper = EPD_EPCORDistributionScraper(today=EPD_TODAY)
    with patch.object(scraper, "fetch_page", return_value=document["landing_html"]),\
            patch.object(scraper, "_fetch_pdf_pages", side_effect=lambda url: fetched.append(url) or by_url[url]):
        records = scraper.scrape()
    assert [record.tariff_code for record in records] == EPD_CODES
    assert all("Provenance: live_parsed" in r.notes and "seed_fallback" not in r.notes for r in records)
    assert all("Provenance: live_parsed" in c.notes for r in records for c in r.components)
    assert sorted(fetched) == sorted(urls.values())


def test_epd_scrape_total_fetch_failure_returns_labelled_seed():
    scraper = EPD_EPCORDistributionScraper(today=EPD_TODAY)
    with patch.object(scraper, "fetch_page", side_effect=OSError("down")),\
            patch.object(scraper, "fetch_bytes", side_effect=OSError("down")):
        records = scraper.scrape()
    assert [record.tariff_code for record in records] == EPD_SEED_CODES
    assert all(r.confidence == "unverified" and "Provenance: seed_fallback" in r.notes for r in records)
    assert all(c.confidence == "unverified" for r in records for c in r.components)


def test_epd_scrape_known_editions_only_while_valid():
    pages, urls, _ = EPD__inputs()
    by_url = {urls[kind]: pages[kind] for kind in pages}
    for today, expected in ((EPD_TODAY, EPD_CODES), (date(2027, 1, 5), EPD_SEED_CODES)):
        scraper = EPD_EPCORDistributionScraper(today=today)
        with patch.object(scraper, "fetch_page", side_effect=OSError("down")),\
                patch.object(scraper, "_fetch_pdf_pages", side_effect=lambda url: by_url[url]):
            assert [record.tariff_code for record in scraper.scrape()] == expected


def test_epd_scrape_unreadable_rider_edition_returns_labelled_seed():
    document = EPD__fixture()
    pages, urls, _ = EPD__inputs(document)
    by_url = {urls[kind]: pages[kind] for kind in pages}
    scraper = EPD_EPCORDistributionScraper(today=date(2026, 9, 15))
    with patch.object(scraper, "fetch_page", return_value=document["landing_html"]),\
            patch.object(scraper, "_fetch_pdf_pages", side_effect=lambda url: by_url.get(url, [])):
        records = scraper.scrape()
    assert [record.tariff_code for record in records] == EPD_SEED_CODES
    assert all("Provenance: seed_fallback" in r.notes for r in records)


# ======================================================================
# FortisAlberta building catalogue (batch 12)
# ======================================================================
from scrapers.utilities import fortisalberta as FAB_fa
from scrapers.utils.parsing import DocumentPage
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest


FAB_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "fortisalberta.json"
FAB_TODAY = date(2026, 10, 9)
FAB_CODES = {"11", "41", "61", "63", "65"}
FAB_PDF_URL = (
    "https://www.fortisalberta.com/docs/default-source/default-document-library/"
    "rates-options-and-riders-schedules-effective-october1-2026.pdf?sfvrsn=859d971b_10"
)

FAB_FAB_RES = [
    ("transmission", "Transmission Variable Charge", 0.04256, "$/kWh", None, "2026-01-01", None),
    ("distribution", "System Usage Charge", 0.033477, "$/kWh", None, "2026-01-01", None),
    ("fixed", "Facilities and Service Charge", 1.034442, "$/day", None, "2026-01-01", None),
    ("rider", "Base Transmission Adjustment Rider", -0.59, "%", None, "2026-01-01", "2026-12-31"),
    ("rider", "Quarterly Transmission Adjustment Rider", 0.000155, "$/kWh", None, "2026-10-01", "2026-12-31"),
    ("rider", "Balancing Pool Allocation Rider", 0.001198, "$/kWh", None, "2026-01-01", None),
]

FAB_FAB_41 = [
    ("transmission", "Transmission System Usage Charge (kW)", 0.150213, "$/kW/day", None, "2026-01-01", None),
    ("transmission", "Transmission System Usage Charge (kVA)", 0.1351917, "$/kVA/day", "alternative", "2026-01-01", None),
    ("transmission", "Transmission Capacity Charge (kW)", 0.120582, "$/kW/day", None, "2026-01-01", None),
    ("transmission", "Transmission Capacity Charge (kVA)", 0.1085238, "$/kVA/day", "alternative", "2026-01-01", None),
    ("transmission", "Transmission Variable Charge", 0.006276, "$/kWh", None, "2026-01-01", None),
    ("demand", "Distribution System Usage Charge (kW)", 0.158148, "$/kW/day", None, "2026-01-01", None),
    ("demand", "Distribution System Usage Charge (kVA)", 0.1423332, "$/kVA/day", "alternative", "2026-01-01", None),
    ("demand", "Local Facilities Charge (kW)", 0.286351, "$/kW/day", None, "2026-01-01", None),
    ("demand", "Local Facilities Charge (kVA)", 0.2577159, "$/kVA/day", "alternative", "2026-01-01", None),
    ("fixed", "Service Charge", 1.11833, "$/day", None, "2026-01-01", None),
    ("rider", "Base Transmission Adjustment Rider", 3.3, "%", None, "2026-01-01", "2026-12-31"),
    ("rider", "Quarterly Transmission Adjustment Rider", 0.000212, "$/kWh", None, "2026-10-01", "2026-12-31"),
    ("rider", "Balancing Pool Allocation Rider", 0.001208, "$/kWh", None, "2026-01-01", None),
    ("fixed", "Option I Interval Metering Service Charge", 1.158823, "$/day", "conditional", "2026-01-01", None),
]

FAB_FAB_61 = [
    ("transmission", "Transmission System Usage Charge (kW)", 0.244663, "$/kW/day", None, "2026-01-01", None),
    ("transmission", "Transmission System Usage Charge (kVA)", 0.2201967, "$/kVA/day", "alternative", "2026-01-01", None),
    ("transmission", "Transmission Capacity Charge (kW)", 0.140959, "$/kW/day", None, "2026-01-01", None),
    ("transmission", "Transmission Capacity Charge (kVA)", 0.1268631, "$/kVA/day", "alternative", "2026-01-01", None),
    ("transmission", "Transmission Variable Charge", 0.006424, "$/kWh", None, "2026-01-01", None),
    ("demand", "Distribution System Usage Charge (kW)", 0.107884, "$/kW/day", None, "2026-01-01", None),
    ("demand", "Distribution System Usage Charge (kVA)", 0.0970956, "$/kVA/day", "alternative", "2026-01-01", None),
    ("demand", "Local Facilities Charge (kW)", 0.114553, "$/kW/day", None, "2026-01-01", None),
    ("demand", "Local Facilities Charge (kVA)", 0.1030977, "$/kVA/day", "alternative", "2026-01-01", None),
    ("fixed", "Service Charge", 1.385825, "$/day", None, "2026-01-01", None),
    ("rider", "Base Transmission Adjustment Rider", -1.84, "%", None, "2026-01-01", "2026-12-31"),
    ("rider", "Quarterly Transmission Adjustment Rider", 0.000223, "$/kWh", None, "2026-10-01", "2026-12-31"),
    ("rider", "Balancing Pool Allocation Rider", 0.001235, "$/kWh", None, "2026-01-01", None),
    ("rebate", "Option A Local Facilities Credit (kW)", -0.014296, "$/kW/day", "conditional", "2026-01-01", None),
    ("rebate", "Option A Local Facilities Credit (kVA)", -0.0128664, "$/kVA/day", "alternative", "2026-01-01", None),
    ("fixed", "Option I Interval Metering Service Charge", 1.158823, "$/day", "conditional", "2026-01-01", None),
]

FAB_FAB_63 = [
    ("transmission", "Transmission System Usage Charge (kW)", 0.214447, "$/kW/day", None, "2026-01-01", None),
    ("transmission", "Transmission System Usage Charge (kVA)", 0.1930023, "$/kVA/day", "alternative", "2026-01-01", None),
    ("transmission", "Transmission Capacity Charge (kW)", 0.174184, "$/kW/day", None, "2026-01-01", None),
    ("transmission", "Transmission Capacity Charge (kVA)", 0.1567656, "$/kVA/day", "alternative", "2026-01-01", None),
    ("transmission", "Transmission Variable Charge", 0.006228, "$/kWh", None, "2026-01-01", None),
    ("distribution", "Distribution System Usage Charge", 27.080602, "$/km/day", None, "2026-01-01", None),
    ("demand", "Local Facilities Charge (kW)", 0.01517, "$/kW/day", None, "2026-01-01", None),
    ("demand", "Local Facilities Charge (kVA)", 0.013653, "$/kVA/day", "alternative", "2026-01-01", None),
    ("fixed", "Service Charge", 15.998863, "$/day", None, "2026-01-01", None),
    ("rider", "Base Transmission Adjustment Rider", -2.69, "%", None, "2026-01-01", "2026-12-31"),
    ("rider", "Quarterly Transmission Adjustment Rider", 0.000251, "$/kWh", None, "2026-10-01", "2026-12-31"),
    ("rider", "Balancing Pool Allocation Rider", 0.001199, "$/kWh", None, "2026-01-01", None),
    ("rebate", "Option A Local Facilities Credit (kW)", -0.014296, "$/kW/day", "conditional", "2026-01-01", None),
    ("rebate", "Option A Local Facilities Credit (kVA)", -0.0128664, "$/kVA/day", "alternative", "2026-01-01", None),
]

FAB_FAB_65 = [
    ("transmission", "Transmission Charge (AESO ISO tariff flow-through)", None, None, None, "2026-01-01", None),
    ("fixed", "Service Charge", 50.61944, "$/day", None, "2026-01-01", None),
    ("rider", "Base Transmission Adjustment Rider", 4.851, "$/day", None, "2026-01-01", "2026-12-31"),
]


def FAB__document():
    return json.loads(FAB_FIXTURE.read_text(encoding="utf-8"))


def FAB__pages(document=None):
    return [DocumentPage(p["page_number"], p["text"]) for p in (document or FAB__document())["pages"]]


def FAB__parse(pages, today=FAB_TODAY):
    rejected = {}
    records = FAB_fa.parse_schedule_pages(pages, FAB_PDF_URL, today, rejected)
    return {r.tariff_code: r for r in records}, rejected


def FAB__mutate(pages, page_number, old, new):
    out = []
    for page in pages:
        if page.page_number == page_number:
            assert old in page.text, (page_number, old)
            page = DocumentPage(page_number, page.text.replace(old, new, 1))
        out.append(page)
    return out


def FAB__drop(pages, page_number):
    assert any(p.page_number == page_number for p in pages)
    return [p for p in pages if p.page_number != page_number]


def FAB__rows(record):
    return [(c.component_type, c.component_name, c.charge_value, c.charge_unit, c.sub_component,
             c.effective_date, c.end_date) for c in record.components]


def FAB__component(record, name):
    (match,) = [c for c in record.components if c.component_name == name]
    return match


def FAB__scraper_with(pages, landing=None, url=FAB_PDF_URL):
    scraper = FAB_fa.FortisAlbertaScraper()
    html = landing if landing is not None else FAB__document()["landing_html"]

    def fetch_page(requested, *args, **kwargs):
        assert requested == FAB_fa.SOURCE_URL
        return html

    def read_pdf(requested):
        if requested != url:
            raise RuntimeError("unexpected download " + requested)
        return pages

    return scraper, patch.object(scraper, "fetch_page", side_effect=fetch_page),\
        patch.object(scraper, "_read_pdf", side_effect=read_pdf)


def test_fab_fixture_provenance():
    document = FAB__document()
    assert document["source_url"] == FAB_PDF_URL
    assert document["landing_url"] == FAB_fa.SOURCE_URL
    assert document["retrieved_on"] == "2026-10-09"
    assert "October 1, 2026" in document["description"]
    assert [p["page_number"] for p in document["pages"]] == [
        1, 3, 4, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 41, 42, 43, 44]


def test_fab_landing_links_and_edition_dates():
    links = FAB_fa.schedule_links(FAB__document()["landing_html"])
    assert links[0] == (FAB_PDF_URL, date(2026, 10, 1))
    assert [stated for _, stated in links] == [
        date(2026, 10, 1), date(2026, 7, 1), date(2026, 5, 1), date(2026, 4, 1), date(2026, 1, 1), None, None]
    assert FAB_fa.document_edition_date(FAB__pages()) == date(2026, 10, 1)


def test_fab_all_building_classes_parsed():
    records, rejected = FAB__parse(FAB__pages())
    assert rejected == {}
    assert set(records) == FAB_CODES
    expected = {
        "11": ("Residential Distribution (Rate 11)", "residential", None, "flat", None, None, "2026-10-01"),
        "41": ("Small General Service Distribution (Rate 41)", "commercial", "small general service", "demand",
               None, 75.0, "2026-10-01"),
        "61": ("General Service Distribution (Rate 61)", "commercial", "general service", "demand",
               None, 2000.0, "2026-10-01"),
        "63": ("Large General Service Distribution (Rate 63)", "commercial", "large general service", "demand",
               2000.0, None, "2026-10-01"),
        "65": ("Transmission Connected Service Distribution (Rate 65)", "industrial",
               "transmission connected service", "mixed", None, None, "2026-01-01"),
    }
    for code, (name, cls, sub, structure, low, high, effective) in expected.items():
        r = records[code]
        assert (r.tariff_name, r.customer_class, r.sub_class, r.rate_structure) == (name, cls, sub, structure)
        assert (r.demand_min_kw, r.demand_max_kw, r.effective_date) == (low, high, effective)
        assert (r.utility_name, r.province, r.utility_type, r.pricing_method) == (
            "FortisAlberta", "AB", "electricity", "regulated")
        assert r.source_url == FAB_PDF_URL and r.confidence == "high" and r.end_date is None
        assert "AUC Decision 30274-D01-2025" in r.notes


def test_fab_exact_components():
    records, _ = FAB__parse(FAB__pages())
    assert FAB__rows(records["11"]) == FAB_FAB_RES
    assert FAB__rows(records["41"]) == FAB_FAB_41
    assert FAB__rows(records["61"]) == FAB_FAB_61
    assert FAB__rows(records["63"]) == FAB_FAB_63
    assert FAB__rows(records["65"]) == FAB_FAB_65


def test_fab_source_details_and_pages():
    records, _ = FAB__parse(FAB__pages())
    res = records["11"]
    assert FAB__component(res, "System Usage Charge").source_detail == (
        "PDF page 3 (schedule page 1); Rate 11 Distribution Charges, System Usage Charge")
    assert FAB__component(res, "Quarterly Transmission Adjustment Rider").source_detail == (
        "PDF page 42 (schedule page 41); Quarterly Transmission Adjustment Rider, Rate 11 row, Q4 column")
    assert FAB__component(records["41"], "Local Facilities Charge (kVA)").source_detail == (
        "PDF page 15 (schedule page 13); Rate 41 Distribution Charges, Local Facilities Charge, kVA Rate")
    assert FAB__component(records["61"], "Option A Local Facilities Credit (kW)").source_detail.startswith("PDF page 28")
    assert res.source_page == "PDF pages 3, 41, 42, 43"
    assert records["41"].source_page == "PDF pages 15, 16, 31, 41, 42, 43"
    for r in records.values():
        for c in r.components:
            assert c.source_url == FAB_PDF_URL and c.confidence == "high" and c.effective_date
            assert c.source_detail.startswith("PDF page ") and not c.source_detail.startswith("PDF page 1 ")


def test_fab_alternatives_and_conditionals_are_marked():
    records, _ = FAB__parse(FAB__pages())
    for r in records.values():
        for c in r.components:
            if c.charge_unit == "$/kVA/day":
                assert c.sub_component == "alternative" and c.notes.startswith("Conditional:")
                kw_name = c.component_name.replace("(kVA)", "(kW)")
                assert FAB__component(r, kw_name).charge_unit == "$/kW/day"
            if c.sub_component == "conditional":
                assert c.notes.startswith("Conditional:")
            if c.component_type == "rebate":
                assert c.charge_value < 0 and c.sub_component in ("conditional", "alternative")
    option_i = FAB__component(records["41"], "Option I Interval Metering Service Charge")
    assert "less than 333 kW" in option_i.notes
    option_a = FAB__component(records["63"], "Option A Local Facilities Credit (kW)")
    assert "not less than 1,000 kW" in option_a.notes and "lesser of" in option_a.notes


def test_fab_rate_65_flow_through_and_riders():
    records, _ = FAB__parse(FAB__pages())
    flow = FAB__component(records["65"], "Transmission Charge (AESO ISO tariff flow-through)")
    assert flow.charge_value is None and flow.charge_unit is None
    assert flow.market_source_url == FAB_fa.AESO_TARIFF_URL
    assert "Point of Delivery" in flow.market_reference
    assert "ISO tariff Rider F" in flow.notes
    names = {c.component_name for c in records["65"].components}
    assert "Quarterly Transmission Adjustment Rider" not in names
    assert "Balancing Pool Allocation Rider" not in names
    assert "Rider A-1" not in records["65"].notes and "Municipal Franchise Fee Riders" in records["65"].notes


def test_fab_notes_carry_billing_rules_and_conditions():
    records, _ = FAB__parse(FAB__pages())
    small = records["41"].notes
    assert "less 50 kW" in small and "Rate Minimum of 3 kW" in small and "less 55.5556 kVA" in small
    assert "The Transmission Minimum Charge is the Capacity Charge." in small
    assert "Option D (Flat Rate)" in small
    large = records["63"].notes
    assert "135% of the Contract Minimum Demand" in large and "Rate Minimum of 2,000 kW" in large
    assert "The Transmission System Usage Charge is the greater of" in large
    res = records["11"].notes
    assert "Distribution Minimum Charge is the Facilities and Service Charge" in res
    assert "Exclusions: Common use areas" in res
    for code in ("11", "41", "61", "63"):
        assert "Conditional (not included): Rider A-1 Municipal Assessment Rider and Municipal Franchise Fee"\
               in records[code].notes


def test_fab_changed_value_propagates():
    pages = FAB__mutate(FAB__pages(), 3, "$0.033477 /kWh", "$0.034477 /kWh")
    records, rejected = FAB__parse(pages)
    assert rejected == {} and set(records) == FAB_CODES
    assert FAB__component(records["11"], "System Usage Charge").charge_value == 0.034477
    pages = FAB__mutate(FAB__pages(), 42, "$0.000251/kWh", "($0.000251)/kWh")
    records, _ = FAB__parse(pages)
    assert FAB__component(records["63"], "Quarterly Transmission Adjustment Rider").charge_value == -0.000251


@pytest.mark.parametrize(("page", "rejected_code"), [
    (3, "11"), (15, "41"), (16, "41"), (21, "61"), (22, "61"), (24, "63"), (25, "63"), (26, "65"),
])
def test_fab_missing_page_rejects_only_that_class(page, rejected_code):
    records, rejected = FAB__parse(FAB__drop(FAB__pages(), page))
    assert set(records) == FAB_CODES - {rejected_code}
    assert set(rejected) == {rejected_code}


def test_fab_toc_occurrence_is_skipped():
    records, rejected = FAB__parse(FAB__drop(FAB__pages(), 3))
    assert "11" not in records and "schedule not found" in rejected["11"]
    assert "RATE 11: RESIDENTIAL SERVICE" in FAB__pages()[0].text


@pytest.mark.parametrize(("page", "old", "new", "rejected_code"), [
    (3, "$0.033477 /kWh", "$0.033477 /kW", "11"),
    (15, "$0.286351 /kW-day", "$0.286351 /kW-month", "41"),
    (24, "$27.080602 /km-day", "$27.080602 /km", "63"),
    (26, "$50.619440 /day", "$50.619440 /month", "65"),
    (21, "Service Charge Daily $1.385825 /day", "Service Charge Daily", "61"),
])
def test_fab_wrong_unit_or_missing_value_rejects_only_that_class(page, old, new, rejected_code):
    records, rejected = FAB__parse(FAB__mutate(FAB__pages(), page, old, new))
    assert set(records) == FAB_CODES - {rejected_code} and set(rejected) == {rejected_code}


@pytest.mark.parametrize(("page", "new", "rejected_code"), [
    (15, "Effective Date: January 1, 2027", "41"),
    (21, "", "61"),
    (26, "Effective Date: 2026", "65"),
])
def test_fab_missing_or_future_effective_date_rejects(page, new, rejected_code):
    records, rejected = FAB__parse(FAB__mutate(FAB__pages(), page, "Effective Date: January 1, 2026", new))
    assert set(records) == FAB_CODES - {rejected_code} and set(rejected) == {rejected_code}


@pytest.mark.parametrize(("page", "old", "new", "rejected_codes"), [
    (41, "Small General Service 41 3.30%", "Small General Service", {"41"}),
    (42, "Residential Service 11 $0.000566/kWh ($0.001599)/kWh ($0.002000)/kWh $0.000155/kWh",
     "Residential Service 11 $0.000566/kWh ($0.001599)/kWh ($0.002000)/kWh", {"11"}),
    (42, "$0.000223/kWh", "($0.000223/kWh", {"61"}),
    (43, "Large General Service 63 $0.001199 /kWh", "Large General Service 63", {"63"}),
    (3, "\u2022 Balancing Pool Allocation Rider", "\u2022 Balancing Pool Allocation Rider \u2022 Rider Z Example", {"11"}),
])
def test_fab_garbled_rider_rejects_only_affected_class(page, old, new, rejected_codes):
    records, rejected = FAB__parse(FAB__mutate(FAB__pages(), page, old, new))
    assert set(records) == FAB_CODES - rejected_codes and set(rejected) == rejected_codes


@pytest.mark.parametrize(("page", "rejected_codes"), [
    (41, FAB_CODES), (42, {"11", "41", "61", "63"}), (43, {"11", "41", "61", "63"}), (28, {"61", "63"}), (31, {"41", "61"}),
])
def test_fab_missing_rider_or_option_page_rejects_classes_that_list_it(page, rejected_codes):
    records, rejected = FAB__parse(FAB__drop(FAB__pages(), page))
    assert set(records) == FAB_CODES - rejected_codes and set(rejected) == rejected_codes


def test_fab_expired_riders_excluded():
    records, rejected = FAB__parse(FAB__pages(), today=date(2027, 1, 15))
    assert rejected == {} and set(records) == FAB_CODES
    for r in records.values():
        names = {c.component_name for c in r.components}
        assert "Base Transmission Adjustment Rider" not in names
        assert "Quarterly Transmission Adjustment Rider" not in names
        assert "Base Transmission Adjustment Rider period ended December 31, 2026" in r.notes
        assert r.effective_date == "2026-01-01"
    assert FAB__component(records["11"], "Balancing Pool Allocation Rider").charge_value == 0.001198
    assert "Q4 ended December 31, 2026" in records["11"].notes


def test_fab_previous_quarter_and_malformed_credit_cell():
    records, rejected = FAB__parse(FAB__pages(), today=date(2026, 9, 30))
    assert set(rejected) == {"41"} and "unbalanced credit parentheses" in rejected["41"]
    qtar = FAB__component(records["11"], "Quarterly Transmission Adjustment Rider")
    assert (qtar.charge_value, qtar.effective_date, qtar.end_date) == (-0.002, "2026-07-01", "2026-09-30")
    assert records["11"].effective_date == "2026-07-01"
    assert FAB__component(records["63"], "Quarterly Transmission Adjustment Rider").charge_value == -0.001834


def test_fab_scrape_marks_live_and_drops_seeds(monkeypatch):
    monkeypatch.setattr(FAB_fa, "_today", lambda: FAB_TODAY)
    scraper, page_patch, pdf_patch = FAB__scraper_with(FAB__pages())
    with page_patch, pdf_patch:
        records = scraper.scrape()
    assert {r.tariff_code for r in records} == FAB_CODES
    assert not {"D10", "D20", "D30"} & {r.tariff_code for r in records}
    for r in records:
        assert "live_parsed" in r.notes and "seed_fallback" not in r.notes and r.confidence == "high"
        assert all("live_parsed" in c.notes for c in r.components)


def test_fab_scrape_partial_failure_emits_only_live_classes(monkeypatch):
    monkeypatch.setattr(FAB_fa, "_today", lambda: FAB_TODAY)
    pages = FAB__mutate(FAB__pages(), 24, "$27.080602 /km-day", "$27.080602 /km")
    scraper, page_patch, pdf_patch = FAB__scraper_with(pages)
    with page_patch, pdf_patch:
        records = scraper.scrape()
    assert {r.tariff_code for r in records} == FAB_CODES - {"63"}
    assert all("seed_fallback" not in r.notes for r in records)


def test_fab_scrape_skips_future_edition_without_downloading(monkeypatch):
    monkeypatch.setattr(FAB_fa, "_today", lambda: FAB_TODAY)
    future = ('<a class="result pdf" href="https://www.fortisalberta.com/docs/default-source/default-document-library/'
              'rates-options-and-riders-schedules-effective-january1-2027.pdf">Rates, Options and Riders '
              'schedules, Effective January 1 2027 (PDF)</a>')
    landing = FAB__document()["landing_html"].replace('<div class="row results">', '<div class="row results">' + future, 1)
    assert FAB_fa.schedule_links(landing)[0][1] == date(2027, 1, 1)
    scraper, page_patch, pdf_patch = FAB__scraper_with(FAB__pages(), landing)
    with page_patch, pdf_patch:
        records = scraper.scrape()
    assert {r.tariff_code for r in records} == FAB_CODES and all("live_parsed" in r.notes for r in records)


def test_fab_scrape_edition_label_mismatch_fails_closed(monkeypatch):
    monkeypatch.setattr(FAB_fa, "_today", lambda: FAB_TODAY)
    landing = FAB__document()["landing_html"].replace("Effective October 1 2026", "Effective September 1 2026")
    scraper, page_patch, pdf_patch = FAB__scraper_with(FAB__pages(), landing)
    with page_patch, pdf_patch:
        records = scraper.scrape()
    assert {r.tariff_code for r in records} == {"D10", "D20", "D30"}
    assert all("seed_fallback" in r.notes for r in records)


def test_fab_scrape_total_fetch_failure_returns_labelled_seeds():
    scraper = FAB_fa.FortisAlbertaScraper()
    with patch.object(scraper, "fetch_page", side_effect=OSError("down")):
        records = scraper.scrape()
    assert [r.tariff_code for r in records] == ["D10", "D20", "D30"]
    for r in records:
        assert r.confidence == "unverified" and "seed_fallback" in r.notes and r.province == "AB"
        assert all(c.confidence == "unverified" and "seed_fallback" in c.notes for c in r.components)
    assert records[0].components[0].charge_value == FAB_fa.SEED_RESIDENTIAL["basic_charge_per_day"]


def test_fab_scrape_all_classes_rejected_returns_labelled_seeds(monkeypatch):
    monkeypatch.setattr(FAB_fa, "_today", lambda: FAB_TODAY)
    scraper, page_patch, pdf_patch = FAB__scraper_with(FAB__drop(FAB__pages(), 41))
    with page_patch, pdf_patch:
        records = scraper.scrape()
    assert {r.tariff_code for r in records} == {"D10", "D20", "D30"}
    assert all(r.confidence == "unverified" and "seed_fallback" in r.notes for r in records)


# ======================================================================
# Alberta Rate of Last Resort providers (batch 12)
# ======================================================================
from scrapers.utilities import direct_energy_regulated as ROLR_ders
from scrapers.utilities import enmax_energy as ROLR_enmax
from scrapers.utilities import epcor_energy_alberta as ROLR_epcor
from scrapers.utils import alberta_rolr as ROLR_rolr
from scrapers.utils.parsing import DocumentPage
import json
from contextlib import ExitStack
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest


ROLR_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "alberta_rolr.json"
ROLR_TODAY = date(2026, 10, 9)
ROLR_AFTER_TERM = date(2027, 1, 1)
ROLR_TERM_START = "2025-01-01"
ROLR_TERM_END = "2026-12-31"
ROLR_RES = "Rate of Last Resort - Residential"
ROLR_SB = "Rate of Last Resort - Small Business"
ROLR_EDTI_RES = "Rate of Last Resort - Residential (EPCOR Distribution area)"
ROLR_EDTI_SB = "Rate of Last Resort - Small Business (EPCOR Distribution area)"
ROLR_FAI_RES = "Rate of Last Resort - Residential (FortisAlberta area)"
ROLR_FAI_SB = "Rate of Last Resort - Small Business (FortisAlberta area)"
ROLR_EPCOR_NAMES = {ROLR_EDTI_RES, ROLR_EDTI_SB, ROLR_FAI_RES, ROLR_FAI_SB}


def ROLR__sources():
    return json.loads(ROLR_FIXTURE.read_text(encoding="utf-8"))["sources"]


def ROLR__html(key):
    return ROLR__sources()[key]["html"]


def ROLR__pages(key):
    return [DocumentPage(p["page_number"], p["text"]) for p in ROLR__sources()[key]["pages"]]


def ROLR__replace(text, old, new, count=1):
    assert old in text, old
    return text.replace(old, new, count)


def ROLR__replace_page(pages, page_number, old, new):
    return [DocumentPage(p.page_number, ROLR__replace(p.text, old, new)) if p.page_number == page_number else p
            for p in pages]


def ROLR__ders_inputs(**overrides):
    src = {"uca": ROLR__html("uca"), "residential": ROLR__html("ders_residential"),
           "small_business": ROLR__html("ders_small_business")}
    src.update(overrides)
    return src


def ROLR__enmax_inputs(**overrides):
    src = {"uca": ROLR__html("uca"), "page": ROLR__html("enmax_page"), "schedule_pages": ROLR__pages("enmax_schedule")}
    src.update(overrides)
    return src


def ROLR__epcor_inputs(**overrides):
    sources = ROLR__sources()
    src = {"uca": sources["uca"]["html"]}
    for key in ROLR_epcor.AREAS:
        src[key + "_home"] = sources["epcor_" + key + "_home"]["html"]
        src[key + "_business"] = sources["epcor_" + key + "_business"]["html"]
        src[key + "_schedule"] = (sources["epcor_" + key + "_schedule"]["url"], ROLR__pages("epcor_" + key + "_schedule"))
    src.update(overrides)
    return src


def ROLR__names(records):
    return {r.tariff_name for r in records}


def ROLR__by_name(records):
    return {r.tariff_name: r for r in records}


def ROLR__comp(record, kind):
    (component,) = [c for c in record.components if c.component_type == kind]
    return component


def ROLR__all_live():
    return (ROLR_ders.parse_sources(ROLR__ders_inputs(), ROLR_TODAY)[0] + ROLR_enmax.parse_sources(ROLR__enmax_inputs(), ROLR_TODAY)[0]
            + ROLR_epcor.parse_sources(ROLR__epcor_inputs(), ROLR_TODAY)[0])


# ── Fixture and UCA table ─────────────────────────────────────────

def test_rolr_fixture_sources_match_module_urls():
    sources = ROLR__sources()
    assert sources["uca"]["url"] == ROLR_rolr.UCA_DEFAULT_RATES_URL
    assert sources["ders_residential"]["url"] == ROLR_ders.RESIDENTIAL_URL
    assert sources["ders_small_business"]["url"] == ROLR_ders.COMMERCIAL_URL
    assert sources["enmax_page"]["url"] == ROLR_enmax.ROLR_URL
    assert sources["enmax_schedule"]["url"].startswith("https://assets.enmax.com/")
    for key, area in ROLR_epcor.AREAS.items():
        assert sources["epcor_" + key + "_home"]["url"] == area["home_url"]
        assert sources["epcor_" + key + "_business"]["url"] == area["business_url"]
        assert sources["epcor_" + key + "_tariffs"]["url"] == area["tariffs_url"]
        listing = sources["epcor_" + key + "_tariffs"]["html"]
        assert ROLR_epcor.schedule_candidates(listing, key, ROLR_TODAY)[0] == sources["epcor_" + key + "_schedule"]["url"]
    assert all(entry["retrieved_on"] == "2026-10-09" for entry in sources.values())


def test_rolr_uca_table_term_unit_and_prices():
    table = ROLR_rolr.parse_uca_table(ROLR__html("uca"), ROLR_TODAY)
    assert (table.period.start.isoformat(), table.period.end.isoformat()) == (ROLR_TERM_START, ROLR_TERM_END)
    assert {k: str(v) for k, v in table.prices.items()} == {
        ("EPCOR", "EPCOR Distribution"): "12.01",
        ("EPCOR", "FortisAlberta Inc."): "12.01",
        ("ENMAX", "ENMAX Power Corporation"): "12.06",
        ("Direct Energy Regulated Services", "ATCO Electric"): "12.02",
    }


def test_rolr_uca_table_failures():
    html = ROLR__html("uca")
    with pytest.raises(ROLR_rolr.RolrError):
        ROLR_rolr.parse_uca_table(html, ROLR_AFTER_TERM)
    with pytest.raises(ROLR_rolr.RolrError):
        ROLR_rolr.parse_uca_table(ROLR__replace(html, "in ¢/kWh", "in $/kWh"), ROLR_TODAY)
    with pytest.raises(ROLR_rolr.RolrError):
        ROLR_rolr.parse_uca_table(ROLR__replace(html, "January 1, 2025 – December 31, 2026 - ", ""), ROLR_TODAY)
    with pytest.raises(ROLR_rolr.RolrError):
        ROLR_rolr.parse_uca_table(ROLR__replace(html, "will be in place until December 31, 2026",
                                      "will be in place until December 31, 2027"), ROLR_TODAY)
    with pytest.raises(ROLR_rolr.RolrError):
        ROLR_rolr.parse_uca_table(html.replace("<table", "<div").replace("</table>", "</div>"), ROLR_TODAY)


def test_rolr_uca_next_term_table_selected_by_date():
    html = ROLR__html("uca")
    start = html.index("<table")
    end = html.index("</table>", start) + len("</table>")
    future = (html[start:end].replace("January 1, 2025 – December 31, 2026", "January 1, 2027 – December 31, 2028")
              .replace("Until Dec. 31", "Until Dec. 31 2028 ").replace("<p>2026</p>", "")
              .replace("12.02", "12.50"))
    combined = html[:end] + future + html[end:]
    assert ROLR_rolr.parse_uca_table(combined, ROLR_TODAY).price("Direct Energy", "ATCO") == ROLR_rolr.parse_cents("12.02", "¢/kWh")
    later = ROLR_rolr.parse_uca_table(combined, date(2027, 2, 1))
    assert later.price("Direct Energy", "ATCO") == ROLR_rolr.parse_cents("12.50", "¢/kWh")
    # A provider still publishing the old term cannot pass against the new table.
    records, rejections = ROLR_ders.parse_sources(ROLR__ders_inputs(uca=combined), date(2027, 2, 1))
    assert records == [] and len(rejections) == 2


# ── Exact records ─────────────────────────────────────────────────

def test_rolr_ders_records():
    records, rejections = ROLR_ders.parse_sources(ROLR__ders_inputs(), ROLR_TODAY)
    assert rejections == []
    by_name = ROLR__by_name(records)
    assert set(by_name) == {ROLR_RES, ROLR_SB}
    expected = {ROLR_RES: ("RoLR-Res", "residential", ROLR_ders.RESIDENTIAL_URL, "Residential Services"),
                ROLR_SB: ("RoLR-SB", "commercial", ROLR_ders.COMMERCIAL_URL, "Small General Service")}
    for name, (code, customer_class, url, label) in expected.items():
        record = by_name[name]
        assert (record.tariff_code, record.customer_class, record.rate_structure, record.pricing_method) == (
            code, customer_class, "flat", "regulated")
        assert (record.effective_date, record.end_date, record.confidence) == (ROLR_TERM_START, ROLR_TERM_END, "high")
        assert record.source_url == url and record.usage_max is None
        assert "ATCO Electric" in record.eligibility and label in record.eligibility
        assert "administration charge" in record.notes and "not included" in record.notes
        assert [c.component_type for c in record.components] == ["energy"]
        energy = ROLR__comp(record, "energy")
        assert (energy.charge_value, energy.charge_unit, energy.effective_date, energy.end_date) == (
            0.1202, "$/kWh", ROLR_TERM_START, ROLR_TERM_END)
        assert energy.source_url == url and "12.02 cents/kWh from January 1, 2025" in energy.source_detail
        assert "Direct Energy Regulated Services / ATCO Electric 12.02 cents/kWh" in energy.notes


def test_rolr_enmax_records():
    records, rejections = ROLR_enmax.parse_sources(ROLR__enmax_inputs(), ROLR_TODAY)
    assert rejections == []
    by_name = ROLR__by_name(records)
    assert set(by_name) == {ROLR_RES, ROLR_SB}
    schedule_url = ROLR__sources()["enmax_schedule"]["url"]
    expected = {ROLR_RES: ("RoLR-Res", "residential", 0.4134, "D100", None, None),
                ROLR_SB: ("RoLR-SB", "commercial", 0.3973, "D200", 250.0, "MWh/year")}
    for name, (code, customer_class, admin_value, rate_code, usage_max, usage_unit) in expected.items():
        record = by_name[name]
        assert (record.tariff_code, record.customer_class, record.rate_structure, record.pricing_method) == (
            code, customer_class, "flat", "regulated")
        assert (record.effective_date, record.end_date, record.confidence) == (ROLR_TERM_START, ROLR_TERM_END, "medium")
        assert (record.usage_max, record.usage_unit) == (usage_max, usage_unit)
        assert rate_code + " service" in record.eligibility and "City of Calgary" in record.eligibility
        assert "INTERIM 2026" in record.notes and "Red Deer, Cardston and Ponoka" in record.notes
        energy, admin = ROLR__comp(record, "energy"), ROLR__comp(record, "fixed")
        assert (energy.charge_value, energy.charge_unit, energy.effective_date, energy.end_date) == (
            0.1206, "$/kWh", ROLR_TERM_START, ROLR_TERM_END)
        assert (admin.charge_value, admin.charge_unit, admin.effective_date, admin.end_date) == (
            admin_value, "$/day", ROLR_TERM_START, None)
        assert admin.confidence == "medium" and "Decision 29608-D01-2024" in admin.source_detail
        assert energy.source_url == schedule_url == admin.source_url
    assert "less than 250 MWh" in by_name[ROLR_SB].eligibility
    assert "Medium Commercial (D300)" in by_name[ROLR_SB].notes


def test_rolr_epcor_records():
    records, rejections = ROLR_epcor.parse_sources(ROLR__epcor_inputs(), ROLR_TODAY)
    assert rejections == []
    by_name = ROLR__by_name(records)
    assert set(by_name) == ROLR_EPCOR_NAMES
    sources = ROLR__sources()
    expected = {
        ROLR_EDTI_RES: ("RoLR-Res-EDTI", "residential", 0.23, "edti", "home", None),
        ROLR_EDTI_SB: ("RoLR-SB-EDTI", "commercial", 0.354, "edti", "business", 250000.0),
        ROLR_FAI_RES: ("RoLR-Res-FAI", "residential", 0.26, "fortis", "home", None),
        ROLR_FAI_SB: ("RoLR-SB-FAI", "commercial", 0.198, "fortis", "business", 250000.0),
    }
    for name, (code, customer_class, admin_value, area_key, page_key, usage_max) in expected.items():
        area = ROLR_epcor.AREAS[area_key]
        record = by_name[name]
        assert (record.tariff_code, record.customer_class, record.rate_structure, record.pricing_method) == (
            code, customer_class, "flat", "regulated")
        assert (record.effective_date, record.end_date, record.confidence) == ("2026-07-01", ROLR_TERM_END, "high")
        assert record.usage_max == usage_max
        assert record.usage_unit == ("kWh/year" if usage_max else None)
        assert record.source_url == area[page_key + "_url"]
        assert area["service_area"] in record.eligibility
        energy, admin = ROLR__comp(record, "energy"), ROLR__comp(record, "fixed")
        assert (energy.charge_value, energy.charge_unit, energy.effective_date, energy.end_date) == (
            0.1201, "$/kWh", ROLR_TERM_START, ROLR_TERM_END)
        assert (admin.charge_value, admin.charge_unit, admin.effective_date, admin.end_date) == (
            admin_value, "$/day", "2026-07-01", None)
        assert admin.source_url == sources["epcor_" + area_key + "_schedule"]["url"]
        assert "$/Day/Site" in admin.source_detail
    assert "single-phase service" in by_name[ROLR_EDTI_RES].eligibility
    assert "less than 250 megawatt hours" in by_name[ROLR_EDTI_SB].eligibility
    assert "FortisAlberta Inc." in by_name[ROLR_FAI_SB].eligibility


def test_rolr_every_live_component_is_sourced_and_dated():
    records = ROLR__all_live()
    assert len(records) == 8
    for record in records:
        assert record.province == "AB" and record.utility_type == "electricity"
        assert not any(c.component_type in ("delivery", "transmission", "rider") for c in record.components)
        for component in record.components:
            assert component.source_url and component.source_detail and component.effective_date
            assert component.charge_value is not None and component.charge_value > 0
        assert ROLR__comp(record, "energy").end_date == ROLR_TERM_END


# ── Mutations: changes propagate, disagreements fail closed ───────

def test_rolr_ders_changed_price_propagates():
    uca = ROLR__replace(ROLR__html("uca"), "<p>12.02</p>", "<p>12.50</p>")
    res = ROLR__replace(ROLR__html("ders_residential"), "12.02 cents/kWh", "12.50 cents/kWh")
    com = ROLR__replace(ROLR__html("ders_small_business"), "12.02 cents/kWh", "12.50 cents/kWh")
    records, rejections = ROLR_ders.parse_sources(ROLR__ders_inputs(uca=uca, residential=res, small_business=com), ROLR_TODAY)
    assert rejections == [] and {ROLR__comp(r, "energy").charge_value for r in records} == {0.125}


def test_rolr_ders_provider_uca_mismatch_rejects():
    uca = ROLR__replace(ROLR__html("uca"), "<p>12.02</p>", "<p>12.03</p>")
    records, rejections = ROLR_ders.parse_sources(ROLR__ders_inputs(uca=uca), ROLR_TODAY)
    assert records == [] and len(rejections) == 2
    com = ROLR__replace(ROLR__html("ders_small_business"), "12.02 cents/kWh", "12.03 cents/kWh")
    records, _ = ROLR_ders.parse_sources(ROLR__ders_inputs(small_business=com), ROLR_TODAY)
    assert ROLR__names(records) == {ROLR_RES}


@pytest.mark.parametrize(("old", "new"), [
    ("12.02 cents/kWh", "12.02 dollars/kWh"),
    ("to December 31, 2026", "to December 31, 2027"),
    ("from January 1, 2025, to December 31, 2026", "from January 2025 to the end of 2026"),
    ("Small General Service", "General Service"),
])
def test_rolr_ders_small_business_unit_term_or_class_drift_rejects_only_that_class(old, new):
    com = ROLR__ders_inputs()["small_business"].replace(old, new)
    assert com != ROLR__html("ders_small_business")
    records, rejections = ROLR_ders.parse_sources(ROLR__ders_inputs(small_business=com), ROLR_TODAY)
    assert ROLR__names(records) == {ROLR_RES} and len(rejections) == 1


def test_rolr_enmax_changed_price_propagates():
    uca = ROLR__replace(ROLR__html("uca"), "<p>12.06</p>", "<p>12.50</p>")
    pages = ROLR__pages("enmax_schedule")
    for number in (2, 3):
        pages = ROLR__replace_page(pages, number, "Energy Charge $0.1206 per kWh", "Energy Charge $0.1250 per kWh")
    pages = ROLR__replace_page(pages, 3, "Administration Charge $0.3973 per day", "Administration Charge $0.4000 per day")
    records, rejections = ROLR_enmax.parse_sources(ROLR__enmax_inputs(uca=uca, schedule_pages=pages), ROLR_TODAY)
    assert rejections == []
    by_name = ROLR__by_name(records)
    assert {ROLR__comp(r, "energy").charge_value for r in records} == {0.125}
    assert ROLR__comp(by_name[ROLR_SB], "fixed").charge_value == 0.4


@pytest.mark.parametrize(("page", "old", "new"), [
    (2, "Energy Charge $0.1206 per kWh", "Energy Charge $0.1216 per kWh"),
    (2, "Energy Charge $0.1206 per kWh", "Energy Charge $0.1206 per kW"),
    (2, "Administration Charge $0.4134 per day", "Administration Charge $0.4134 per month"),
    (2, "Rider n/a", "Rider $0.1797 per day"),
    (2, "D100 service", "D110 service"),
    (2, "Decision 29608-D01-2024, effective January 1, 2025", "Decision 29608-D01-2024"),
])
def test_rolr_enmax_schedule_drift_rejects_only_that_class(page, old, new):
    pages = ROLR__replace_page(ROLR__pages("enmax_schedule"), page, old, new)
    records, rejections = ROLR_enmax.parse_sources(ROLR__enmax_inputs(schedule_pages=pages), ROLR_TODAY)
    assert ROLR__names(records) == {ROLR_SB} and len(rejections) == 1


def test_rolr_enmax_uca_mismatch_term_and_cover_reject_all():
    uca = ROLR__replace(ROLR__html("uca"), "<p>12.06</p>", "<p>12.16</p>")
    assert ROLR_enmax.parse_sources(ROLR__enmax_inputs(uca=uca), ROLR_TODAY)[0] == []
    page = ROLR__html("enmax_page").replace("remain unchanged until December 31, 2026", "remain unchanged until December 31, 2027")
    assert page != ROLR__html("enmax_page")
    assert ROLR_enmax.parse_sources(ROLR__enmax_inputs(page=page), ROLR_TODAY)[0] == []
    pages = ROLR__replace_page(ROLR__pages("enmax_schedule"), 1, "ENMAX Power Corporation", "Another Utility")
    assert ROLR_enmax.parse_sources(ROLR__enmax_inputs(schedule_pages=pages), ROLR_TODAY)[0] == []
    assert ROLR_enmax.parse_sources(ROLR__enmax_inputs(), ROLR_AFTER_TERM)[0] == []


def test_rolr_enmax_schedule_for_another_year_rejected():
    entry = ROLR_enmax.parse_rate_schedule(ROLR__pages("enmax_schedule"))["Residential"]
    assert str(ROLR_enmax.parse_schedule_charges(entry, ROLR_TODAY)["admin"]) == "0.4134"
    with pytest.raises(ROLR_rolr.RolrError):
        ROLR_enmax.parse_schedule_charges(entry, date(2027, 3, 1))


def test_rolr_epcor_changed_prices_propagate():
    sources = ROLR__epcor_inputs()
    url, pages = sources["edti_schedule"]
    pages = ROLR__replace_page(pages, 2, "Administration Charge $0.230", "Administration Charge $0.245")
    records, rejections = ROLR_epcor.parse_sources(ROLR__epcor_inputs(edti_schedule=(url, pages)), ROLR_TODAY)
    assert rejections == []
    assert ROLR__comp(ROLR__by_name(records)[ROLR_EDTI_RES], "fixed").charge_value == 0.245

    uca = ROLR__replace(ROLR__html("uca"), "<p>12.01</p>", "<p>12.50</p>")  # first 12.01 cell = EPCOR Distribution
    home = ROLR__replace(sources["edti_home"], "12.01", "12.50")
    business = ROLR__replace(sources["edti_business"], "12.01", "12.50")
    for number in (2, 3):
        pages = ROLR__replace_page(pages, number, "Energy Charge 12.01", "Energy Charge 12.50")
    records, rejections = ROLR_epcor.parse_sources(ROLR__epcor_inputs(
        uca=uca, edti_home=home, edti_business=business, edti_schedule=(url, pages)), ROLR_TODAY)
    assert rejections == []
    energy = {r.tariff_name: ROLR__comp(r, "energy").charge_value for r in records}
    assert energy == {ROLR_EDTI_RES: 0.125, ROLR_EDTI_SB: 0.125, ROLR_FAI_RES: 0.1201, ROLR_FAI_SB: 0.1201}


def test_rolr_epcor_uca_mismatch_rejects_only_that_area():
    html = ROLR__html("uca")
    first = html.index("<p>12.01</p>")
    second = html.index("<p>12.01</p>", first + 1)
    uca = html[:second] + "<p>12.11</p>" + html[second + len("<p>12.01</p>"):]
    records, rejections = ROLR_epcor.parse_sources(ROLR__epcor_inputs(uca=uca), ROLR_TODAY)
    assert ROLR__names(records) == {ROLR_EDTI_RES, ROLR_EDTI_SB} and len(rejections) == 2


@pytest.mark.parametrize(("kind", "old", "new", "rejected"), [
    ("home", "12.01", "12.02", {ROLR_EDTI_RES}),
    ("business", "12.01", "12.02", {ROLR_EDTI_SB}),
    ("home", "to December 31, 2026", "to December 31, 2027", {ROLR_EDTI_RES}),
    ("business", "Small Commercial", "Medium Commercial", {ROLR_EDTI_SB}),
])
def test_rolr_epcor_page_drift_rejects_only_that_class(kind, old, new, rejected):
    page = ROLR__replace(ROLR__epcor_inputs()["edti_" + kind], old, new)
    records, rejections = ROLR_epcor.parse_sources(ROLR__epcor_inputs(**{"edti_" + kind: page}), ROLR_TODAY)
    assert ROLR__names(records) == ROLR_EPCOR_NAMES - rejected and len(rejections) == len(rejected)


@pytest.mark.parametrize(("page", "old", "new", "rejected"), [
    (2, "Energy Charge 12.01 (cents/kWh)", "Energy Charge 12.01 ($/kWh)", {ROLR_EDTI_RES}),
    (3, "Energy Charge 12.01 (cents/kWh)", "Energy Charge 12.11 (cents/kWh)", {ROLR_EDTI_SB}),
    (2, "$0.230 ($/Day/Site)", "$0.230 ($/Month/Site)", {ROLR_EDTI_RES}),
    (3, "$0.354 ($/Day/Site)", "($0.354) ($/Day/Site)", {ROLR_EDTI_SB}),
    (2, "Residential Service", "Residence", {ROLR_EDTI_RES}),
    (2, "Effective Date: July 1, 2026", "Effective Date: July 1, 2025", {ROLR_EDTI_RES, ROLR_EDTI_SB}),
    (2, "Page 2 of 5", "Page 2 of 6", {ROLR_EDTI_RES, ROLR_EDTI_SB}),
])
def test_rolr_epcor_schedule_drift_fails_closed(page, old, new, rejected):
    url, pages = ROLR__epcor_inputs()["edti_schedule"]
    pages = ROLR__replace_page(pages, page, old, new)
    records, _ = ROLR_epcor.parse_sources(ROLR__epcor_inputs(edti_schedule=(url, pages)), ROLR_TODAY)
    assert ROLR__names(records) == ROLR_EPCOR_NAMES - rejected


def test_rolr_epcor_schedule_area_dates_and_completeness():
    url, pages = ROLR__epcor_inputs()["fortis_schedule"]
    with pytest.raises(ROLR_rolr.RolrError):
        ROLR_epcor.parse_price_schedule(pages, "edti", ROLR_TODAY)  # FortisAlberta schedule offered for Edmonton
    with pytest.raises(ROLR_rolr.RolrError):
        ROLR_epcor.parse_price_schedule([p for p in pages if p.page_number != 3], "fortis", ROLR_TODAY)
    with pytest.raises(ROLR_rolr.RolrError):
        ROLR_epcor.parse_price_schedule(pages, "fortis", date(2026, 6, 30))  # July 1, 2026 schedule not yet in effect
    assert ROLR_epcor.parse_price_schedule(pages, "fortis", ROLR_TODAY)["effective"] == date(2026, 7, 1)
    records, _ = ROLR_epcor.parse_sources(ROLR__epcor_inputs(), date(2026, 6, 30))
    assert records == []
    assert ROLR_epcor.parse_sources(ROLR__epcor_inputs(), ROLR_AFTER_TERM)[0] == []


def test_rolr_epcor_schedule_candidates_newest_effective_first():
    sources = ROLR__sources()
    edti = ROLR_epcor.schedule_candidates(sources["epcor_edti_tariffs"]["html"], "edti", ROLR_TODAY)
    assert edti[0].endswith("/2026-07-edmonton-regulated-rate-tariff.pdf")
    assert edti[1].endswith("/2025-11-edmonton-regulated-rate-tariff.pdf")
    earlier = ROLR_epcor.schedule_candidates(sources["epcor_edti_tariffs"]["html"], "edti", date(2026, 6, 30))
    assert earlier[0].endswith("/2025-11-edmonton-regulated-rate-tariff.pdf")
    fortis = ROLR_epcor.schedule_candidates(sources["epcor_fortis_tariffs"]["html"], "fortis", ROLR_TODAY)
    assert fortis[0].endswith("/2026-07-fortis-regulated-rate-tariff.pdf")
    assert all("edmonton" not in url for url in fortis)


# ── Scraper level: live provenance, partial failure, total failure ─

def ROLR__run(scraper, pages_by_url, pdf_by_url=None, today=ROLR_TODAY):
    pdf_by_url = pdf_by_url or {}

    def fetch_page(url, *args, **kwargs):
        if url not in pages_by_url:
            raise OSError("down: " + url)
        return pages_by_url[url]

    def pdf_pages(data):
        if data.decode() not in pdf_by_url:
            raise OSError("no pdf")
        return pdf_by_url[data.decode()]

    with ExitStack() as stack:
        stack.enter_context(patch.object(scraper, "fetch_page", side_effect=fetch_page))
        stack.enter_context(patch.object(scraper, "fetch_bytes", side_effect=lambda url, *a, **k: url.encode()))
        stack.enter_context(patch.object(scraper, "_today", return_value=today))
        if hasattr(scraper, "_pdf_pages"):
            stack.enter_context(patch.object(scraper, "_pdf_pages", side_effect=pdf_pages))
        return scraper.scrape()


def ROLR__ders_urls():
    return {ROLR_rolr.UCA_DEFAULT_RATES_URL: ROLR__html("uca"), ROLR_ders.RESIDENTIAL_URL: ROLR__html("ders_residential"),
            ROLR_ders.COMMERCIAL_URL: ROLR__html("ders_small_business")}


def ROLR__enmax_urls():
    sources = ROLR__sources()
    return ({ROLR_rolr.UCA_DEFAULT_RATES_URL: ROLR__html("uca"), ROLR_enmax.ROLR_URL: ROLR__html("enmax_page")},
            {sources["enmax_schedule"]["url"]: ROLR__pages("enmax_schedule")})


def ROLR__epcor_urls():
    sources = ROLR__sources()
    pages = {ROLR_rolr.UCA_DEFAULT_RATES_URL: ROLR__html("uca")}
    pdfs = {}
    for key, area in ROLR_epcor.AREAS.items():
        for kind in ("home", "business", "tariffs"):
            pages[area[kind + "_url"]] = sources["epcor_" + key + "_" + kind]["html"]
        pdfs[sources["epcor_" + key + "_schedule"]["url"]] = ROLR__pages("epcor_" + key + "_schedule")
    return pages, pdfs


def ROLR__assert_live(records, names):
    assert ROLR__names(records) == names
    for record in records:
        assert "Provenance: live_parsed" in record.notes and "seed_fallback" not in record.notes
        assert record.rate_structure == "flat"
        assert all("Provenance: live_parsed" in c.notes for c in record.components)


def ROLR__assert_seed(records):
    assert ROLR__names(records) == {"Residential Regulated Rate Option", "Commercial Regulated Rate Option"}
    for record in records:
        assert record.confidence == "unverified" and "Provenance: seed_fallback" in record.notes
        assert record.rate_structure == "market"
        assert all(c.confidence == "unverified" for c in record.components)


def test_rolr_ders_scrape_live_partial_and_failure():
    ROLR__assert_live(ROLR__run(ROLR_ders.DirectEnergyRegulatedScraper(), ROLR__ders_urls()), {ROLR_RES, ROLR_SB})
    partial = ROLR__ders_urls()
    partial.pop(ROLR_ders.COMMERCIAL_URL)
    ROLR__assert_live(ROLR__run(ROLR_ders.DirectEnergyRegulatedScraper(), partial), {ROLR_RES})
    ROLR__assert_seed(ROLR__run(ROLR_ders.DirectEnergyRegulatedScraper(), {}))
    ROLR__assert_seed(ROLR__run(ROLR_ders.DirectEnergyRegulatedScraper(), ROLR__ders_urls(), today=ROLR_AFTER_TERM))


def test_rolr_enmax_scrape_live_and_failure():
    pages, pdfs = ROLR__enmax_urls()
    ROLR__assert_live(ROLR__run(ROLR_enmax.ENMAXEnergyScraper(), pages, pdfs), {ROLR_RES, ROLR_SB})
    ROLR__assert_seed(ROLR__run(ROLR_enmax.ENMAXEnergyScraper(), {}, pdfs))
    ROLR__assert_seed(ROLR__run(ROLR_enmax.ENMAXEnergyScraper(), pages, {}))
    ROLR__assert_seed(ROLR__run(ROLR_enmax.ENMAXEnergyScraper(), pages, pdfs, today=ROLR_AFTER_TERM))


def test_rolr_epcor_scrape_live_partial_and_failure():
    pages, pdfs = ROLR__epcor_urls()
    ROLR__assert_live(ROLR__run(ROLR_epcor.EPCOREnergyAlbertaScraper(), pages, pdfs), ROLR_EPCOR_NAMES)
    partial = {url: html for url, html in pages.items() if "/ab/other/" not in url}
    ROLR__assert_live(ROLR__run(ROLR_epcor.EPCOREnergyAlbertaScraper(), partial, pdfs), {ROLR_EDTI_RES, ROLR_EDTI_SB})
    ROLR__assert_seed(ROLR__run(ROLR_epcor.EPCOREnergyAlbertaScraper(), {}, pdfs))


# ======================================================================
# Ontario PUC Distribution and market-energy components (batch 12)
# ======================================================================
from scrapers.base import BaseScraper
from scrapers.utilities import ontario_ldc as ONB12_ontario_ldc
from scrapers.utils import oeb_tariff as ONB12_oeb_tariff
from scrapers.utils.parsing import DocumentPage
from scrapers.utils.validation import validate_batch
import json
from dataclasses import replace
from datetime import date
from pathlib import Path


ONB12_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "oeb_tariff_puc.json"
ONB12_TORONTO_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "oeb_tariff_toronto.json"
ONB12_OTTAWA_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "oeb_tariff_ottawa.json"
ONB12_HYDRO_ONE_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "oeb_tariff_hydro_one.json"
ONB12_ALGOMA_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "oeb_tariff_algoma.json"
ONB12_BILLDATA_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "oeb_billdata.json"
ONB12_NAME = "PUC Distribution Inc."
ONB12_TODAY = date(2026, 10, 9)
ONB12_NOTE = ("PUC Distribution's approved tariff (EB-2025-0012) prints no Retail Transmission Connection Service Rate; "
        "only the Network Service Rate is published, so no connection charge is shown.")
ONB12_RPP_CODES = {"TOU-R", "TIER-R", "ULO-R", "GS-TOU-S", "GS-TIER-S", "GS-ULO-S"}
ONB12_GS50 = "GENERAL SERVICE 50 TO 4,999 KW"
ONB12_RES_NETWORK_LINE = "Retail Transmission Rate - Network Service Rate $/kWh 0.0103"
ONB12_GS50_NETWORK_LINE = "Retail Transmission Rate - Network Service Rate $/kW 3.8677"
ONB12_EMBEDDED_RIDER = ("Rate Rider for Embedded Generation Adjustment - in effect until the effective date of the next cost "
                  "of service based rate order")
ONB12_MARKET_NAME = "Market Energy (Ontario Electricity Market Price + Class B Global Adjustment)"
ONB12_MARKET_REF = "IESO Ontario Electricity Market Price (OEMP) + Global Adjustment (Class B)"
ONB12_MARKET_URL = "https://www.ieso.ca/Power-Data/Price-Overview/Ontario-Market-Prices"


def ONB12_fixture_pages(mutate=None):
    data = json.loads(ONB12_FIXTURE.read_text(encoding="utf-8"))
    pages = [DocumentPage(p["page"], p["text"]) for p in data["pages"]]
    if mutate:
        old, new = mutate
        assert sum(p.text.count(old) for p in pages) == 1, old
        pages = [DocumentPage(p.page_number, p.text.replace(old, new)) for p in pages]
    return data, pages


def ONB12_puc_sheet():
    data, pages = ONB12_fixture_pages()
    return ONB12_oeb_tariff.parse_tariff_pages(pages, data["url"], "2026-10-09")


def ONB12_plain_pages(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return data, [DocumentPage(p["page"], p["text"]) for p in data["pages"]]


def ONB12_run_scraper(monkeypatch, ldc, pages_by_url):
    billdata = json.loads(ONB12_BILLDATA_FIXTURE.read_text(encoding="utf-8"))
    payload = {
        ONB12_ontario_ldc.OEB_SOURCE_URL: billdata["rpp_html"].encode("utf-8"),
        ONB12_ontario_ldc.OEB_BILLDATA_RES_URL: billdata["residential_xml"].encode("utf-8"),
        ONB12_ontario_ldc.OEB_BILLDATA_GS_URL: billdata["gs_xml"].encode("utf-8"),
    }

    def fake_fetch_bytes(self, url, delay=1.0):
        if url not in payload:
            raise RuntimeError("unexpected url " + url)
        return payload[url]

    def fake_pages(self, url, **kw):
        if url not in pages_by_url:
            raise RuntimeError("tariff unavailable " + url)
        return pages_by_url[url]

    ONB12_ontario_ldc.clear_oeb_cache()
    monkeypatch.setattr(BaseScraper, "fetch_bytes", fake_fetch_bytes)
    monkeypatch.setattr(ONB12_ontario_ldc.OntarioLDCScraper, "_fetch_tariff_pages", fake_pages)
    monkeypatch.setattr(ONB12_ontario_ldc, "_today", lambda: ONB12_TODAY)
    scraper = ONB12_ontario_ldc.OntarioLDCScraper(registry_entry={"name": ldc})
    try:
        return scraper, scraper.scrape()
    finally:
        ONB12_ontario_ldc.clear_oeb_cache()


def ONB12_run_puc(monkeypatch, mutate=None):
    data, pages = ONB12_fixture_pages(mutate)
    return ONB12_run_scraper(monkeypatch, ONB12_NAME, {data["url"]: pages})


def ONB12_live_records(records):
    return [r for r in records if "Provenance: live_parsed" in (r.notes or "")]


def ONB12_seed_records(records):
    return [r for r in records if "Provenance: seed_fallback" in (r.notes or "")]


def ONB12_one_record(records, code):
    found = [r for r in records if r.tariff_code == code]
    assert len(found) == 1, (code, [r.tariff_code for r in records])
    return found[0]


def ONB12_one_comp(rec, label):
    found = [c for c in rec.components if c.component_name == label]
    assert len(found) == 1, (label, [c.component_name for c in rec.components])
    return found[0]


def ONB12_market_parts(rec):
    return [c for c in rec.components if c.market_reference]


# ── Task A: PUC Distribution (EB-2025-0012) ─────────────────────

def test_onb12_fixture_metadata():
    data, pages = ONB12_fixture_pages()
    assert data["url"] == ONB12_ontario_ldc._OEB_RDS_DOC.format(936444)
    assert (data["case_number"], data["effective_date"], data["issued"]) == ("EB-2025-0012", "2026-05-01", "2026-03-19")
    assert [p.page_number for p in pages] == [7, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
    assert all(p.text for p in pages)
    assert not any("Connection Service Rate" in p.text for p in pages if p.page_number >= 15)


def test_onb12_configured_with_connection_flag_only_for_puc():
    assert ONB12_ontario_ldc.OEB_TARIFF_DOCUMENTS[ONB12_NAME] == [{
        "url": ONB12_ontario_ldc._OEB_RDS_DOC.format(936444),
        "case_number": "EB-2025-0012", "zones": None, "default_zone": "",
        "connection_rate": ONB12_oeb_tariff.CONNECTION_RATE_NOT_PRINTED,
    }]
    flagged = [n for n, docs in ONB12_ontario_ldc.OEB_TARIFF_DOCUMENTS.items() for d in docs if "connection_rate" in d]
    assert flagged == [ONB12_NAME]


def test_onb12_sheet_prints_only_network_rates():
    sheet = ONB12_puc_sheet()
    assert sheet.errors == [] and sheet.case_number == "EB-2025-0012"
    assert (sheet.effective_date, sheet.implementation_date, sheet.issued_date) == (
        "2026-05-01", "2026-05-01", "2026-03-19")
    categories = {c.name: ONB12_oeb_tariff.classify_classification(c) for c in sheet.classifications}
    assert categories["RESIDENTIAL"] == "residential"
    assert categories["GENERAL SERVICE LESS THAN 50 KW"] == "gs_energy"
    assert categories[ONB12_GS50] == "gs_demand"
    assert not any(ONB12_oeb_tariff.connection_printed(c) for c in sheet.classifications)
    assert [c.value for c in sheet.classification(ONB12_GS50).find("transmission_network", conditional=False)] == [3.8677]


def test_onb12_note_text():
    assert ONB12_oeb_tariff.connection_not_printed_note(ONB12_NAME, "EB-2025-0012") == ONB12_NOTE


def test_onb12_unflagged_demand_build_rejects_missing_connection():
    sheet = ONB12_puc_sheet()
    assert ONB12_oeb_tariff.build_demand_records(sheet, ONB12_NAME, today="2026-10-09") == []
    assert "Line and Transformation Connection Service Rate' line, found 0" in sheet.rejections[ONB12_GS50]


def test_onb12_flagged_demand_build_accepts_and_notes():
    sheet = ONB12_puc_sheet()
    records = ONB12_oeb_tariff.build_demand_records(sheet, ONB12_NAME, today="2026-10-09",
                                              connection_rate=ONB12_oeb_tariff.CONNECTION_RATE_NOT_PRINTED)
    assert [r.tariff_code for r in records] == ["GS 50-4,999 kW"] and sheet.rejections == {}
    gs = records[0]
    assert ONB12_NOTE in gs.notes
    assert not [c for c in gs.components if "Connection" in c.component_name]
    assert ONB12_one_comp(gs, "Retail Transmission Rate - Network Service Rate").charge_value == 3.8677
    assert ONB12_one_comp(gs, "Service Charge").charge_value == 137.59
    dist = ONB12_one_comp(gs, "Distribution Volumetric Rate")
    assert (dist.charge_value, dist.charge_unit) == (9.3274, "$/kW")
    assert len(ONB12_market_parts(gs)) == 1


def test_onb12_energy_validation_strict_unless_flagged():
    res = ONB12_puc_sheet().classification("RESIDENTIAL")
    reason = ONB12_ontario_ldc.validate_energy_charges(res.charges, "residential", res.unparsed)
    assert reason == "expected one standard $/kWh Retail Transmission Connection rate, found 0"
    assert ONB12_ontario_ldc.validate_energy_charges(res.charges, "residential", res.unparsed,
                                               connection_optional=True) is None


def test_onb12_regulatory_section_rider_accepted_unless_non_rpp():
    res = ONB12_puc_sheet().classification("RESIDENTIAL")
    rider = next(c for c in res.charges if c.label == ONB12_EMBEDDED_RIDER)
    assert (rider.kind, rider.section, rider.value) == ("regulatory", "regulatory", -0.0004)
    non_rpp = replace(rider, label=rider.label + " - Applicable only for Non-RPP Customers")
    charges = [non_rpp if c is rider else c for c in res.charges]
    reason = ONB12_ontario_ldc.validate_energy_charges(charges, "residential", [], connection_optional=True)
    assert reason.startswith("unrecognised regulatory charge")


def test_onb12_scraper_builds_seven_live_records(monkeypatch):
    scraper, records = ONB12_run_puc(monkeypatch)
    assert scraper.tariff_rejections == {}
    assert {r.tariff_code for r in ONB12_live_records(records)} == ONB12_RPP_CODES | {"GS 50-4,999 kW"}
    assert {r.tariff_code for r in ONB12_seed_records(records)} == {"SL"}
    for rec in ONB12_live_records(records):
        assert ONB12_NOTE in rec.notes, rec.tariff_code
        assert not [c for c in rec.components if "Connection" in c.component_name], rec.tariff_code
        assert rec.effective_date == "2026-05-01" and rec.confidence == "high"
        for c in rec.components:
            assert c.source_url and c.source_detail and c.effective_date, (rec.tariff_code, c.component_name)
    tou = ONB12_one_record(records, "TOU-R")
    assert ONB12_one_comp(tou, "Service Charge").charge_value == 42.81
    assert ONB12_one_comp(tou, "Retail Transmission Rate - Network Service Rate").charge_value == 0.0103
    assert not [c for c in tou.components if c.component_type == "distribution"]
    rider = ONB12_one_comp(tou, ONB12_EMBEDDED_RIDER)
    assert (rider.component_type, rider.charge_value, rider.charge_unit) == ("regulatory", -0.0004, "$/kWh")
    assert "next cost-of-service" in rider.notes
    assert "Global Adjustment Account" in tou.notes
    assert not [c for c in tou.components if "Global Adjustment" in c.component_name]
    gs_tou = ONB12_one_record(records, "GS-TOU-S")
    assert ONB12_one_comp(gs_tou, "Service Charge").charge_value == 24.91
    assert ONB12_one_comp(gs_tou, "Distribution Volumetric Rate").charge_value == 0.0356
    assert not ONB12_market_parts(tou) and not ONB12_market_parts(gs_tou)
    gs50 = ONB12_one_record(records, "GS 50-4,999 kW")
    assert gs50.tariff_name == "General Service 50 to 4,999 kW (delivery only)"
    assert (gs50.customer_class, gs50.demand_min_kw, gs50.demand_max_kw) == ("commercial", 50, 5000)
    assert len(ONB12_market_parts(gs50)) == 1 and gs50.pricing_method == "market_based"
    valid, invalid = validate_batch(records)
    assert invalid == [] and len(valid) == len(records)


def test_onb12_flag_still_parses_a_printed_connection_rate(monkeypatch):
    added = ONB12_RES_NETWORK_LINE + "\nRetail Transmission Rate - Line and Transformation Connection Service Rate $/kWh 0.0050"
    scraper, records = ONB12_run_puc(monkeypatch, (ONB12_RES_NETWORK_LINE, added))
    tou = ONB12_one_record(records, "TOU-R")
    conn = ONB12_one_comp(tou, "Retail Transmission Rate - Line and Transformation Connection Service Rate")
    assert (conn.charge_value, conn.charge_unit) == (0.005, "$/kWh")
    assert ONB12_NOTE not in tou.notes
    assert ONB12_NOTE in ONB12_one_record(records, "GS-TOU-S").notes


def test_onb12_flag_does_not_accept_alternative_only_connection(monkeypatch):
    added = (ONB12_GS50_NETWORK_LINE + "\nRetail Transmission Rate - Line and Transformation Connection Service Rate - "
             "EV CHARGING $/kW 0.5000")
    scraper, records = ONB12_run_puc(monkeypatch, (ONB12_GS50_NETWORK_LINE, added))
    codes = {r.tariff_code for r in records}
    assert "GS 50-4,999 kW" not in codes and "GS-D1" not in codes
    assert "found 0" in scraper.tariff_rejections["demand:standard:" + ONB12_GS50]
    assert ONB12_RPP_CODES <= {r.tariff_code for r in ONB12_live_records(records)}


def test_onb12_unflagged_puc_document_rejects_every_class(monkeypatch):
    doc = dict(ONB12_ontario_ldc.OEB_TARIFF_DOCUMENTS[ONB12_NAME][0])
    del doc["connection_rate"]
    monkeypatch.setitem(ONB12_ontario_ldc.OEB_TARIFF_DOCUMENTS, ONB12_NAME, [doc])
    scraper, records = ONB12_run_puc(monkeypatch)
    assert not ONB12_live_records(records)
    for key in ("residential:standard", "gs:standard", "demand:standard:" + ONB12_GS50):
        assert "Connection" in scraper.tariff_rejections[key], key
    assert {r.tariff_code for r in ONB12_seed_records(records)} == {"SL"}


def test_onb12_unflagged_document_without_connection_rate_still_rejected(monkeypatch):
    data, pages = ONB12_plain_pages(ONB12_TORONTO_FIXTURE)
    stripped = [DocumentPage(p.page_number, "\n".join(
        line for line in p.text.splitlines() if "Connection Service Rate" not in line)) for p in pages]
    assert "connection_rate" not in ONB12_ontario_ldc.OEB_TARIFF_DOCUMENTS["Toronto Hydro-Electric System Ltd."][0]
    scraper, records = ONB12_run_scraper(monkeypatch, "Toronto Hydro-Electric System Ltd.", {data["url"]: stripped})
    assert not ONB12_live_records(records)
    assert "Connection" in scraper.tariff_rejections["residential:standard"]
    assert "Connection" in scraper.tariff_rejections["gs:standard"]
    demand = [v for k, v in scraper.tariff_rejections.items() if k.startswith("demand:")]
    assert demand and all("Connection" in v for v in demand)


# ── Task B: Phase 6B market energy on non-RPP demand classes ───

def test_onb12_market_component_fields_on_demand_records():
    data, pages = ONB12_plain_pages(ONB12_TORONTO_FIXTURE)
    sheet = ONB12_oeb_tariff.parse_tariff_pages(pages, data["url"], "2026-10-09")
    records = ONB12_oeb_tariff.build_demand_records(sheet, "Toronto Hydro-Electric System Ltd.", today="2026-10-09")
    assert sorted(r.tariff_code for r in records) == ["GS 1,000-4,999 kW", "GS 50-999 kW", "LU"]
    for rec in records:
        parts = ONB12_market_parts(rec)
        assert len(parts) == 1, rec.tariff_code
        c = parts[0]
        assert (c.component_type, c.component_name, c.charge_value, c.charge_unit) == (
            "energy", ONB12_MARKET_NAME, None, "$/kWh")
        assert (c.market_reference, c.market_source_url, c.source_url) == (ONB12_MARKET_REF, ONB12_MARKET_URL, ONB12_MARKET_URL)
        assert c.source_detail == "IESO Ontario Market Prices and Global Adjustment pages"
        assert c.effective_date == rec.effective_date == "2026-01-01"
        for text in ("Day-Ahead Ontario Zonal Price plus the Load Forecast Deviation Adjustment",
                     "replaced the HOEP on May 1, 2025",
                     "https://www.ieso.ca/power-data/price-overview/global-adjustment",
                     "Conditional: Class A (Industrial Conservation Initiative)", "peak demand factor",
                     "no value is stored", "Market Pricing view"):
            assert text in c.notes, text
        assert (rec.pricing_method, rec.market_reference) == ("market_based", ONB12_MARKET_REF)
        assert "Ontario Electricity Market Price" in rec.notes and "retired on April 30, 2025" in rec.notes
        assert "not more than 250,000 kilowatt hours" in rec.notes and "may be eligible for RPP prices" in rec.notes
        assert "https://www.ontario.ca/laws/regulation/050095" in rec.notes
    valid, invalid = validate_batch(records)
    assert invalid == [] and len(valid) == 3


def test_onb12_hydro_one_demand_and_st_classes_get_market_component():
    data = json.loads(ONB12_HYDRO_ONE_FIXTURE.read_text(encoding="utf-8"))
    pages = [DocumentPage(p["page_number"], p["text"]) for p in data["raw_pages"]]
    sheet = ONB12_oeb_tariff.parse_tariff_zones(pages, data["url"], "2026-10-09")[None]
    records = ONB12_oeb_tariff.build_demand_records(sheet, "Hydro One Networks Inc.", today="2026-10-09")
    assert [r.tariff_code for r in records] == ["UGd", "GSd", "ST", "AUGd", "AGSd"]
    for rec in records:
        assert [c.component_name for c in ONB12_market_parts(rec)] == [ONB12_MARKET_NAME], rec.tariff_code
        assert rec.pricing_method == "market_based", rec.tariff_code
    assert validate_batch(records)[1] == []


def test_onb12_rpp_records_have_no_market_component(monkeypatch):
    data, pages = ONB12_plain_pages(ONB12_TORONTO_FIXTURE)
    scraper, records = ONB12_run_scraper(monkeypatch, "Toronto Hydro-Electric System Ltd.", {data["url"]: pages})
    rpp = [r for r in ONB12_live_records(records) if r.tariff_code in ONB12_RPP_CODES]
    assert {r.tariff_code for r in rpp} == ONB12_RPP_CODES
    for rec in rpp:
        assert not ONB12_market_parts(rec) and (rec.pricing_method, rec.market_reference) == ("regulated", None)
    demand = [r for r in ONB12_live_records(records) if r.rate_structure == "demand"]
    assert {r.tariff_code for r in demand} == {"GS 50-999 kW", "GS 1,000-4,999 kW", "LU"}
    assert all(len(ONB12_market_parts(r)) == 1 for r in demand)


def test_onb12_market_component_dated_from_implementation_date(monkeypatch):
    data, pages = ONB12_plain_pages(ONB12_OTTAWA_FIXTURE)
    scraper, records = ONB12_run_scraper(monkeypatch, "Hydro Ottawa Ltd.", {data["url"]: pages})
    demand = [r for r in ONB12_live_records(records) if r.rate_structure == "demand"]
    assert len(demand) == 3
    for rec in demand:
        assert rec.effective_date == "2026-06-01"
        assert [c.effective_date for c in ONB12_market_parts(rec)] == ["2026-06-01"]


def test_onb12_algoma_r2_stays_delivery_only_without_market_component():
    data = json.loads(ONB12_ALGOMA_FIXTURE.read_text(encoding="utf-8"))
    pages = [DocumentPage(n, data["text"][str(n)]) for n in data["pages"]]
    sheet = ONB12_oeb_tariff.parse_tariff_pages(pages, data["source_url"], "2026-10-09")
    records = ONB12_oeb_tariff.build_demand_records(sheet, "Algoma Power Inc.", today="2026-10-09")
    assert [r.tariff_code for r in records] == ["R2 50+ kW"]
    r2 = records[0]
    assert not ONB12_market_parts(r2) and not [c for c in r2.components if c.component_type == "energy"]
    assert (r2.pricing_method, r2.market_reference) == ("regulated", None)
    for text in ("electricity commodity is not included", "relates to, i. a dwelling", "O. Reg. 445/07",
                 "https://www.ontario.ca/laws/regulation/050095", "RPP commodity prices are not applied"):
        assert text in r2.notes, text
    assert ONB12_oeb_tariff.RPP_ELIGIBILITY_NOTE not in r2.notes


def test_onb12_commodity_note_uses_market_price_wording():
    note = ONB12_oeb_tariff.COMMODITY_NOTE
    assert "Ontario Electricity Market Price" in note and "retired on April 30, 2025" in note
    assert ONB12_oeb_tariff.HOEP_RETIRED_URL in note and "deferred" not in note


def test_onb12_seed_demand_records_use_market_price_wording(monkeypatch):
    scraper, records = ONB12_run_scraper(monkeypatch, "Hydro Ottawa Ltd.", {})
    seeds = {r.tariff_code: r for r in ONB12_seed_records(records)}
    for code in ("GS-D1", "GS-D2", "GS-D3"):
        rec = seeds[code]
        assert rec.market_reference == ONB12_MARKET_REF and "HOEP +" not in rec.notes
        assert "Ontario Electricity Market Price" in rec.notes and "retired April 30, 2025" in rec.notes
        energy = [c for c in rec.components if c.component_type == "energy"]
        assert [(c.market_reference, c.market_source_url, c.charge_value) for c in energy] == [
            (ONB12_MARKET_REF, ONB12_MARKET_URL, None)]


# ======================================================================
# Enbridge Gas rate handbook, three rate zones (batch 12)
# ======================================================================
from scrapers.utilities import enbridge_gas as ENB_enbridge_gas
from scrapers.utilities.enbridge_gas import EnbridgeGasScraper as ENB_EnbridgeGasScraper, blank_overlap_indexes as ENB_blank_overlap_indexes
from scrapers.utils.parsing import DocumentPage
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest


ENB_ENB_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "enbridge_gas.json"
ENB_ENB_TODAY = date(2026, 10, 9)
ENB_ENB_CODES = {
    "EGD-1", "EGD-6", "EGD-100", "EGD-110", "EGD-115", "EGD-145", "EGD-170",
    "UNW-01", "UNE-01", "UNW-10", "UNE-10", "UNW-20", "UNE-20", "UN-25", "UNW-100", "UNE-100",
    "US-M1", "US-M2", "US-M4", "US-M5",
}
ENB_ENB_RIDER_I_CODES = {"EGD-1", "EGD-6", "UNW-01", "UNE-01", "UNW-10", "UNE-10", "US-M1", "US-M2"}


def ENB__enb_document():
    return json.loads(ENB_ENB_FIXTURE.read_text(encoding="utf-8"))


def ENB__enb_pages():
    return {page["page_number"]: page["text"] for page in ENB__enb_document()["pages"]}


def ENB__enb_parse(pages, cra=None, today=ENB_ENB_TODAY):
    document = ENB__enb_document()
    scraper = ENB_EnbridgeGasScraper()
    records = scraper.parse_documents([DocumentPage(number, text) for number, text in sorted(pages.items())],
                                      document["cra_text"] if cra is None else cra, today=today,
                                      source_url=document["source_url"])
    return {record.tariff_code: record for record in records}, scraper


def ENB__enb_replace(pages, number, old, new):
    assert old in pages[number], (number, old)
    pages[number] = pages[number].replace(old, new, 1)
    return pages


def ENB__enb_rows(record):
    return [(c.component_type, c.component_name, c.charge_value, c.charge_unit, c.sub_component, c.tier_number,
             c.tier_threshold) for c in record.components]


def ENB__enb_component(record, name):
    (component,) = [c for c in record.components if c.component_name == name]
    return component


def test_enb_fixture_has_official_sources():
    document = ENB__enb_document()
    assert document["source_url"] == ENB_enbridge_gas.HANDBOOK_URL
    assert document["landing_url"] in ENB_enbridge_gas.DISCOVERY_URLS
    assert document["cra_url"] == ENB_enbridge_gas.CRA_URL
    assert document["retrieved_on"] == "2026-10-09"
    numbers = [page["page_number"] for page in document["pages"]]
    assert {1, 9, 44, 57, 103, 113, 115, 116} <= set(numbers)
    assert "EB-2026-0221" in document["description"]


def test_enb_all_modelled_classes_parse_live():
    records, scraper = ENB__enb_parse(ENB__enb_pages())
    assert set(records) == ENB_ENB_CODES
    assert scraper.rejected_classes == []
    for record in records.values():
        assert (record.utility_name, record.province, record.utility_type) == ("Enbridge Gas", "ON", "gas")
        assert record.effective_date == "2026-10-01" and record.confidence == "high"
        assert record.pricing_method == "regulated" and record.source_url == ENB_enbridge_gas.HANDBOOK_URL
        assert "OEB Order EB-2026-0221" in record.notes and "Riders D and E print no current amounts" in record.notes
        for component in record.components:
            assert component.source_url == ENB_enbridge_gas.HANDBOOK_URL
            assert component.source_detail.startswith("Rate Handbook PDF page")
            assert component.effective_date == "2026-10-01"
            if component.sub_component == "conditional":
                assert component.notes.startswith("Conditional:")


def test_enb_names_classes_and_structures():
    records, _ = ENB__enb_parse(ENB__enb_pages())
    expected = {
        "EGD-1": ("Rate 1 Residential Service (EGD Rate Zone)", "residential", "tiered"),
        "EGD-6": ("Rate 6 General Service (EGD Rate Zone)", "commercial", "tiered"),
        "EGD-100": ("Rate 100 Firm Contract Service (EGD Rate Zone)", "industrial", "demand"),
        "EGD-145": ("Rate 145 Interruptible Service (EGD Rate Zone)", "industrial", "demand"),
        "UNW-01": ("Rate 01 Small Volume General Firm Service (Union North West)", "residential", "tiered"),
        "UNE-10": ("Rate 10 Large Volume General Firm Service (Union North East)", "commercial", "tiered"),
        "UNW-20": ("Rate 20 Medium Volume Firm Service (Union North West)", "industrial", "demand"),
        "UN-25": ("Rate 25 Large Volume Interruptible Service (Union North)", "industrial", "flat"),
        "UNE-100": ("Rate 100 Large Volume High Load Factor Firm Service (Union North East)", "industrial", "demand"),
        "US-M1": ("Rate M1 Small Volume General Service (Union South)", "residential", "tiered"),
        "US-M2": ("Rate M2 Large Volume General Service (Union South)", "commercial", "tiered"),
        "US-M4": ("Rate M4 Firm Industrial and Commercial Contract Service (Union South)", "industrial", "demand"),
        "US-M5": ("Rate M5 Interruptible Industrial and Commercial Contract Service (Union South)", "industrial",
                  "flat"),
    }
    for code, (name, customer_class, structure) in expected.items():
        record = records[code]
        assert (record.tariff_name, record.customer_class, record.rate_structure) == (name, customer_class, structure)
    usage = {code: (r.usage_min, r.usage_max, r.usage_unit) for code, r in records.items() if r.usage_unit}
    assert usage == {
        "EGD-145": (340000.0, None, "m³/year"), "EGD-170": (5000000.0, None, "m³/year"),
        "UNW-01": (None, 50000.0, "m³/year"), "UNE-01": (None, 50000.0, "m³/year"),
        "UNW-10": (50000.0, None, "m³/year"), "UNE-10": (50000.0, None, "m³/year"),
        "US-M1": (None, 50000.0, "m³/year"), "US-M2": (50000.0, None, "m³/year"),
    }
    assert records["EGD-1"].eligibility.startswith("EGD Rate Zone: To any Customer")
    assert "no more than six dwelling units" in records["EGD-1"].eligibility


def test_enb_egd_rate_1_exact_components():
    record = ENB__enb_parse(ENB__enb_pages())[0]["EGD-1"]
    assert ENB__enb_rows(record) == [
        ("fixed", "Monthly Customer Charge", 27.69, "$/month", None, None, None),
        ("delivery", "Delivery Charge — First 30 m³", 0.142691, "$/m³", None, 1, 30.0),
        ("delivery", "Delivery Charge — Next 55 m³", 0.134308, "$/m³", None, 2, 85.0),
        ("delivery", "Delivery Charge — Next 85 m³", 0.127744, "$/m³", None, 3, 170.0),
        ("delivery", "Delivery Charge — Over 170 m³", 0.12285, "$/m³", None, 4, None),
        ("transmission", "Gas Supply Transportation Charge", 0.054818, "$/m³", None, None, None),
        ("transmission", "Gas Supply Transportation Dawn Charge", 0.00943, "$/m³", "conditional", None, None),
        ("commodity", "Gas Supply Commodity Charge", 0.094741, "$/m³", None, None, None),
        ("rider", "Gas Cost Adjustment (Rider C)", 0.005322, "$/m³", None, None, None),
        ("rider", "System Expansion Surcharge (Rider I)", 0.23, "$/m³", "conditional", None, None),
        ("rider", "Temporary Connection Surcharge (Rider I)", 0.23, "$/m³", "conditional", None, None),
        ("carbon", "Federal Carbon Charge", 0.0, "$/m³", None, None, None),
        ("carbon", "Facility Carbon Charge", 0.000145, "$/m³", None, None, None),
    ]
    assert ENB__enb_component(record, "Monthly Customer Charge").source_detail ==\
        "Rate Handbook PDF page 9; Rate 1 Residential Service"
    assert "Rider K" in ENB__enb_component(record, "Monthly Customer Charge").notes
    rider = ENB__enb_component(record, "Gas Cost Adjustment (Rider C)")
    assert (rider.effective_date, rider.end_date) == ("2026-10-01", "2027-12-31")
    assert rider.source_detail == "Rate Handbook PDF pages 103-104; Rider C Gas Cost Adjustment"
    assert "commodity -0.3661 + transportation 0.3634 + load balancing 0.5349" in rider.notes
    assert "Western (0.8983)" in rider.notes
    federal = ENB__enb_component(record, "Federal Carbon Charge")
    assert federal.source_detail == "Rate Handbook PDF page 115; Rider J Carbon Charges"
    assert "April 1, 2025" in federal.notes and "March 31, 2025" in federal.notes
    assert "system-gas (sales service)" in ENB__enb_component(record, "Gas Supply Commodity Charge").notes
    assert "Rider L" in record.notes and "Rider M" in record.notes


def test_enb_egd_general_and_contract_values():
    records, _ = ENB__enb_parse(ENB__enb_pages())
    blocks = [c.charge_value for c in records["EGD-6"].components if c.component_name.startswith("Delivery Charge")]
    assert blocks == [0.137319, 0.109839, 0.090595, 0.078232, 0.072738, 0.071359]
    assert [c.tier_threshold for c in records["EGD-6"].components if c.tier_number] == [
        500.0, 1550.0, 6050.0, 13050.0, 28300.0, None]
    expected = {
        "EGD-100": (148.76, 0.440136, 0.020495, 0.095, 0.004909),
        "EGD-110": (712.33, 0.295865, 0.004302, 0.094321, -0.002614),
        "EGD-115": (755.02, 0.332714, 0.001492, 0.094321, -0.003992),
        "EGD-145": (150.36, 0.149737, 0.009475, 0.094363, 0.001651),
        "EGD-170": (339.26, 0.063754, 0.004167, 0.094321, -0.000198),
    }
    for code, (fixed, demand, balancing, commodity, rider) in expected.items():
        record = records[code]
        assert ENB__enb_component(record, "Monthly Customer Charge").charge_value == fixed
        contract = ENB__enb_component(record, "Delivery Charge — Contract Demand")
        assert (contract.charge_value, contract.charge_unit, contract.demand_unit) == (
            demand, "$/m³/month", "m³/day Contract Demand")
        assert ENB__enb_component(record, "Gas Supply Load Balancing Charge").charge_value == balancing
        assert ENB__enb_component(record, "Gas Supply Commodity Charge").charge_value == commodity
        assert ENB__enb_component(record, "Gas Cost Adjustment (Rider C)").charge_value == rider
        assert not [c for c in record.components if "Rider I" in c.component_name]
    assert ENB__enb_component(records["EGD-100"], "Delivery Charge — Gas delivered").charge_value == 0.009727
    assert [(c.charge_value, c.tier_threshold) for c in records["EGD-110"].components
            if c.component_name.startswith("Delivery Charge — Gas delivered")] == [(0.010134, 1000000.0),
                                                                                  (0.00818, None)]
    assert "Minimum bill: 6.7239" in records["EGD-110"].notes
    assert "Curtailment credit: $0.50" in records["EGD-145"].notes and "16 hours" in records["EGD-145"].notes
    assert "Curtailment credit: $1.10" in records["EGD-170"].notes


def test_enb_union_north_zone_columns():
    records, _ = ENB__enb_parse(ENB__enb_pages())
    expected = {
        "UNW-01": (0.023746, 0.027031, 0.095866, -0.032294), "UNE-01": (0.05835, 0.017135, 0.156674, 0.015542),
        "UNW-10": (0.022741, 0.023442, 0.095866, -0.032294), "UNE-10": (0.048124, 0.01567, 0.156674, 0.015542),
    }
    for code, (storage, transport, commodity, rider) in expected.items():
        record = records[code]
        assert ENB__enb_component(record, "Gas Supply Storage Charge").charge_value == storage
        assert ENB__enb_component(record, "Gas Supply Transportation Charge").charge_value == transport
        assert ENB__enb_component(record, "Gas Supply Commodity Charge").charge_value == commodity
        assert ENB__enb_component(record, "Gas Cost Adjustment (Rider C)").charge_value == rider
        assert ENB__enb_component(record, "Monthly Customer Charge").charge_value == (28.91 if "01" in code else 85.78)
    assert [c.charge_value for c in records["UNE-01"].components if c.tier_number] == [
        0.129082, 0.125877, 0.120796, 0.116134, 0.11228]
    unw20, une20 = records["UNW-20"], records["UNE-20"]
    assert [(c.charge_value, c.tier_threshold, c.tier_unit) for c in unw20.components
            if c.component_type == "demand"] == [(0.389359, 70000.0, "m³/day Contract Demand"), (0.22933, None, None)]
    assert ENB__enb_component(unw20, "Gas Supply Transportation Demand Charge").charge_value == 0.296506
    assert ENB__enb_component(une20, "Gas Supply Transportation Demand Charge").charge_value == 0.372347
    charge_one = ENB__enb_component(une20, "Gas Supply Transportation Charge (Charge 1)")
    assert charge_one.charge_value == 0.011505 and "× 0.4" in charge_one.notes
    assert "× 0.3;" in ENB__enb_component(records["UNW-100"], "Gas Supply Transportation Charge (Charge 1)").notes
    assert ENB__enb_component(records["UNW-100"], "Gas Cost Adjustment (Rider C)").charge_value == -0.0267
    assert ENB__enb_component(records["UNE-100"], "Gas Cost Adjustment (Rider C)").charge_value == 0.021088
    assert "maximum prices" in unw20.notes


def test_enb_union_north_rate_25_is_negotiated_conditions_only():
    record = ENB__enb_parse(ENB__enb_pages())[0]["UN-25"]
    assert ENB__enb_rows(record) == [
        ("fixed", "Monthly Customer Charge", 408.02, "$/month", None, None, None),
        ("delivery", "Delivery Charge (negotiated)", None, "$/m³", "conditional", None, None),
        ("commodity", "Gas Supply Charge (negotiated)", None, "$/m³", "conditional", None, None),
        ("carbon", "Federal Carbon Charge", 0.0, "$/m³", None, None, None),
        ("carbon", "Facility Carbon Charge", 0.000145, "$/m³", None, None, None),
    ]
    assert "8.5950" in ENB__enb_component(record, "Delivery Charge (negotiated)").notes
    assert "1.4848 and 675.9484" in ENB__enb_component(record, "Gas Supply Charge (negotiated)").notes
    assert "Rider C prints no gas cost adjustment" in record.notes and "Rider O" in record.notes


def test_enb_union_south_classes():
    records, _ = ENB__enb_parse(ENB__enb_pages())
    m1, m2, m4, m5 = (records[code] for code in ("US-M1", "US-M2", "US-M4", "US-M5"))
    assert [(c.charge_value, c.tier_threshold) for c in m1.components if c.tier_number] == [
        (0.076394, 100.0), (0.072849, 250.0), (0.063697, None)]
    assert (ENB__enb_component(m1, "Storage Charge").charge_value, ENB__enb_component(m2, "Storage Charge").charge_value) == (
        0.010628, 0.011646)
    for record in (m1, m2, m4, m5):
        assert ENB__enb_component(record, "Gas Supply Commodity Charge").charge_value == 0.153548
        assert ENB__enb_component(record, "Gas Cost Adjustment (Rider C)").charge_value == 0.023461
        assert not [c for c in record.components if c.component_name.startswith("Gas Supply Transportation")]
    assert not [c for c in m4.components if c.component_type == "fixed"]
    assert [(c.charge_value, c.tier_threshold) for c in m4.components if c.component_type == "demand"] == [
        (0.799553, 8450.0), (0.384665, 28150.0), (0.343613, None)]
    assert [c.charge_value for c in m4.components if c.component_type == "delivery"] == [0.022487, 0.022487, 0.008506]
    assert "one-time annual adjustment" in m4.notes and "2.4795" in m4.notes
    bands = [c for c in m5.components if c.component_type == "delivery"]
    assert [(c.charge_value, c.sub_component, c.tier_threshold) for c in bands] == [
        (0.054323, "conditional", 17000.0), (0.053024, "conditional", 30000.0),
        (0.052341, "conditional", 50000.0), (0.051862, "conditional", 60000.0)]
    assert all("bands are not added" in c.notes for c in bands)
    rebates = [(c.charge_value, c.sub_component) for c in m5.components if c.component_type == "rebate"]
    assert rebates == [(-0.00053, "conditional"), (-0.0000212, "conditional")]
    firm = ENB__enb_component(m5, "Firm Service Delivery Charge — Contract Demand")
    assert (firm.charge_value, firm.charge_unit, firm.sub_component) == (0.575048, "$/m³/month", "conditional")
    assert ENB__enb_component(m5, "Monthly Customer Charge").charge_value == 837.79


def test_enb_changed_value_propagates():
    pages = ENB__enb_replace(ENB__enb_pages(), 9, "14.2691 ¢/m³", "15.2691 ¢/m³")
    pages = ENB__enb_replace(pages, 48, "38.9359 ¢/m³", "39.9359 ¢/m³")
    records, _ = ENB__enb_parse(pages)
    assert ENB__enb_component(records["EGD-1"], "Delivery Charge — First 30 m³").charge_value == 0.152691
    for code in ("UNW-20", "UNE-20"):
        assert ENB__enb_component(records[code], "Delivery Charge — Contract Demand — First 70,000 m³").charge_value\
            == 0.399359


def test_enb_split_digit_blanks_are_dropped_only_inside_numbers():
    split = [{"text": "1", "x0": 460.06, "x1": 464.46, "top": 241.56},
             {"text": " ", "x0": 460.06, "x1": 462.26, "top": 241.56},
             {"text": "4", "x0": 464.50, "x1": 468.90, "top": 241.56},
             {"text": ".", "x0": 468.93, "x1": 471.13, "top": 241.56}]
    assert ENB_blank_overlap_indexes(split) == {1}
    word_space = [{"text": "e", "x0": 100.0, "x1": 104.4, "top": 50.0},
                  {"text": " ", "x0": 104.45, "x1": 106.65, "top": 50.0},
                  {"text": "C", "x0": 106.7, "x1": 112.0, "top": 50.0}]
    assert ENB_blank_overlap_indexes(word_space) == set()
    far_columns = [{"text": "1", "x0": 137.5, "x1": 141.9, "top": 80.0},
                   {"text": " ", "x0": 141.95, "x1": 144.15, "top": 80.0},
                   {"text": "1", "x0": 393.1, "x1": 397.5, "top": 80.0}]
    assert ENB_blank_overlap_indexes(far_columns) == set()
    other_line = [{"text": "1", "x0": 460.06, "x1": 464.46, "top": 241.56},
                  {"text": " ", "x0": 460.06, "x1": 462.26, "top": 252.0},
                  {"text": "4", "x0": 464.50, "x1": 468.90, "top": 241.56}]
    assert ENB_blank_overlap_indexes(other_line) == set()


def test_enb_unjoined_split_digits_reject_the_class_instead_of_misreading():
    pages = ENB__enb_replace(ENB__enb_pages(), 9, "14.2691 ¢/m³", "1 4.2691 ¢/m³")
    records, scraper = ENB__enb_parse(pages)
    assert set(records) == ENB_ENB_CODES - {"EGD-1"}
    assert any(item.startswith("EGD Rate 1:") for item in scraper.rejected_classes)


@pytest.mark.parametrize(("number", "rejected"), [
    (9, {"EGD-1"}), (49, {"UNW-20", "UNE-20"}), (60, {"US-M4"}), (63, {"US-M5"}), (52, {"UN-25"}),
])
def test_enb_missing_schedule_page_rejects_only_that_class(number, rejected):
    pages = ENB__enb_pages()
    del pages[number]
    records, scraper = ENB__enb_parse(pages)
    assert set(records) == ENB_ENB_CODES - rejected
    assert len(scraper.rejected_classes) == 1


@pytest.mark.parametrize(("number", "old", "new", "rejected"), [
    (9, "14.2691 ¢/m³", "14.2691 $/m³", {"EGD-1"}),
    (44, "9.5866 ¢/m³ 15.6674 ¢/m³", "9.5866 ¢/m³ 15.6674 $/GJ", {"UNW-01", "UNE-01"}),
    (11, "Per cubic metre of Contract Demand 44.0136 ¢/m³", "Per cubic metre of Contract Demand 44.0136 $/GJ",
     {"EGD-100"}),
    (57, "50,000 m³ per year", "50,000 GJ per year", {"US-M1"}),
    (57, "M1 SMALL VOLUME GENERAL SERVICE", "M1 SMALL VOLUME SERVICE", {"US-M1"}),
    (44, "Union Union\nNorth West North East", "Union North", {"UNW-01", "UNE-01"}),
    (48, "Charge 2 - ¢/m³ - ¢/m³", "Charge 2 0.5000 ¢/m³ 0.5000 ¢/m³", {"UNW-20", "UNE-20"}),
    (10, "Effective October 1, 2026", "Effective July 1, 2026", {"EGD-6"}),
    (103, "Rate 6 0.4909", "Rate 6 0.5909", {"EGD-6"}),
    (115, "Rate 1 0.0000 0.0145", "Rate 1 1.2345 0.0145", {"EGD-1"}),
    (62, "50,000 m³ and equal to or less than 60,000 m³", "50,000 m³ and equal to or less than 65,000 m³",
     {"US-M5"}),
])
def test_enb_structural_or_unit_drift_rejects_only_that_class(number, old, new, rejected):
    records, _ = ENB__enb_parse(ENB__enb_replace(ENB__enb_pages(), number, old, new))
    assert set(records) == ENB_ENB_CODES - rejected


@pytest.mark.parametrize(("number", "old", "new"), [
    (1, "Effective October 1, 2026", "Effective October 1, 2027"),
    (1, "OEB Order EB-2026-0221", "OEB Order"),
    (106, "Rate 1 - ¢/m³", "Rate 1 0.1234 ¢/m³"),
    (116, "¢/m³ ¢/m³", "$/GJ $/GJ"),
])
def test_enb_edition_or_required_rider_drift_rejects_everything(number, old, new):
    records, _ = ENB__enb_parse(ENB__enb_replace(ENB__enb_pages(), number, old, new))
    assert records == {}


def test_enb_future_or_missing_edition_rejects_everything():
    assert ENB__enb_parse(ENB__enb_pages(), today=date(2026, 9, 30))[0] == {}
    pages = ENB__enb_pages()
    del pages[1]
    assert ENB__enb_parse(pages)[0] == {}


def test_enb_missing_carbon_evidence_rejects_everything():
    assert ENB__enb_parse(ENB__enb_pages(), cra="")[0] == {}
    document = ENB__enb_document()
    assert ENB__enb_parse(ENB__enb_pages(), cra=document["cra_text"].replace("Ontario, and", "and"))[0] == {}
    pages = ENB__enb_pages()
    del pages[115]
    assert ENB__enb_parse(pages)[0] == {}


def test_enb_expired_rider_c_is_excluded_but_classes_stay_live():
    pages = ENB__enb_replace(ENB__enb_pages(), 103, "October 1, 2026 to December 31, 2027", "July 1, 2026 to September 30, 2026")
    records, _ = ENB__enb_parse(pages)
    assert set(records) == ENB_ENB_CODES
    for record in records.values():
        assert not [c for c in record.components if c.component_name == "Gas Cost Adjustment (Rider C)"]
    assert "Rider C applies only from July 1, 2026 to September 30, 2026" in records["EGD-1"].notes


def test_enb_missing_rider_i_rejects_only_classes_that_list_it():
    pages = ENB__enb_pages()
    del pages[113]
    records, _ = ENB__enb_parse(pages)
    assert set(records) == ENB_ENB_CODES - ENB_ENB_RIDER_I_CODES


def ENB__enb_serve(document):
    handbook_link = ('<a href="/-/media/Extranet-Pages/ontario/business-and-industrial/Commercial-and-Industrial/'
                     'Large-Volume-Rates-and-Services/EGD-Rates/rate-handbook.pdf?rev=abc&amp;hash=XYZ#page=13">'
                     'Rate Handbook</a>')
    pages = [DocumentPage(page["page_number"], page["text"]) for page in document["pages"]]
    html = {ENB_enbridge_gas.DISCOVERY_URLS[0]: "<html><body>" + handbook_link + "</body></html>",
            ENB_enbridge_gas.CRA_URL: "<html><main><p>" + document["cra_text"] + "</p></main></html>"}
    return pages, html


def test_enb_scrape_marks_live_from_discovered_handbook():
    document = ENB__enb_document()
    pages, html = ENB__enb_serve(document)
    with patch.object(ENB_EnbridgeGasScraper, "fetch_page", lambda self, url, delay=1.0: html[url]),\
            patch.object(ENB_EnbridgeGasScraper, "fetch_bytes",
                         lambda self, url, delay=1.0: b"handbook" if url == ENB_enbridge_gas.HANDBOOK_URL else b""),\
            patch.object(ENB_enbridge_gas, "extract_handbook_pages",
                         lambda data: pages if data == b"handbook" else []):
        records = ENB_EnbridgeGasScraper().scrape()
    assert {record.tariff_code for record in records} == ENB_ENB_CODES
    for record in records:
        assert record.notes.startswith("Provenance: live_parsed.") and "seed_fallback" not in record.notes
        assert record.source_url == ENB_enbridge_gas.HANDBOOK_URL
        assert all(c.notes.startswith("Provenance: live_parsed.") for c in record.components)


def test_enb_discovery_ignores_foreign_hosts():
    foreign = '<a href="https://example.com/rate-handbook.pdf">Rate Handbook</a>'
    with patch.object(ENB_EnbridgeGasScraper, "fetch_page", lambda self, url, delay=1.0: foreign):
        assert ENB_EnbridgeGasScraper()._discover_handbook() == ENB_enbridge_gas.HANDBOOK_URL


def test_enb_total_fetch_failure_returns_labelled_seed():
    def fail(*args, **kwargs):
        raise RuntimeError("offline")

    with patch.object(ENB_EnbridgeGasScraper, "fetch_page", fail), patch.object(ENB_EnbridgeGasScraper, "fetch_bytes", fail):
        records = ENB_EnbridgeGasScraper().scrape()
    assert [record.tariff_name for record in records] == ["Residential — Rate 1 (Union South)"]
    assert records[0].confidence == "unverified" and "Provenance: seed_fallback" in records[0].notes
    assert all(c.confidence == "unverified" for c in records[0].components)


def test_enb_unmodelled_schedules_have_reasons():
    assert ("EGD", "125") in ENB_enbridge_gas.EXCLUDED_SCHEDULES and ("Union South", "T1") in ENB_enbridge_gas.EXCLUDED_SCHEDULES
    modelled = {(spec.zone, spec.rate) for spec in ENB_enbridge_gas.CLASS_SPECS}
    assert not modelled & set(ENB_enbridge_gas.EXCLUDED_SCHEDULES)


# ======================================================================
# ATCO Gas North/South rate schedules and default supply (batch 12)
# ======================================================================
from scrapers.utils.parsing import DocumentPage
import json
from datetime import date
from pathlib import Path

import pytest

import scrapers.utilities.atco_gas as atg

ATG_LANDING_URL = atg.LANDING_URL
ATG_PAGE_URLS = atg.PAGE_URLS
ATG_SCHEDULE_URLS = atg.SCHEDULE_URLS
ATG_ATCOGasScraper = atg.ATCOGasScraper
ATG_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "atco_gas.json"
ATG_TODAY = date(2026, 10, 9)
ATG_CODES = {"N-LOW", "N-MID", "N-HIGH", "N-UHU", "N-ATA", "S-LOW", "S-MID", "S-HIGH", "S-UHU", "S-ATA"}
ATG_DRT_CODES = {"N-LOW", "N-MID", "N-HIGH", "S-LOW", "S-MID", "S-HIGH"}
ATG_EN_DASH = "\u2013"
ATG_LDQ = "\u201c"
ATG_RDQ = "\u201d"

ATG_FIXED = "Fixed Charge"
ATG_VARIABLE = "Variable Charge"
ATG_DEMAND = "Demand Charge"
ATG_RIDER_L = "Rider L \u2014 Load Balancing Deferral Account"
ATG_RIDER_T = "Rider T \u2014 Transmission Service Charge"
ATG_RIDER_W = "Rider W \u2014 Weather Deferral Account"
ATG_DRT = "Default Supply Gas Charge (DERS Rider F)"
ATG_CARBON = "Federal Carbon Charge"
ATG_L_PERIOD = ("2026-05-01", "2026-12-31")
ATG_GAS = ("commodity", ATG_DRT, 1.458, "$/GJ", "2026-10-01", "2026-10-31")
ATG_ZERO_CARBON = ("carbon", ATG_CARBON, 0.0, "$/GJ", "2025-04-01", None)


def ATG__base(fixed, variable, rider_l, rider_t, demand=None):
    rows = [("fixed", ATG_FIXED, fixed, "$/day", "2026-01-01", None),
            ("delivery", ATG_VARIABLE, variable, "$/GJ", "2026-01-01", None)]
    if demand is not None:
        rows.append(("demand", ATG_DEMAND, demand, "$/GJ/day", "2026-01-01", None))
    rows.append(("rider", ATG_RIDER_L, rider_l, "$/GJ") + ATG_L_PERIOD)
    rows.append(("transmission", ATG_RIDER_T, rider_t, "$/GJ/day" if demand is not None else "$/GJ", "2026-01-01", None))
    return rows


ATG_EXPECTED = {
    "N-LOW": ATG__base(0.997, 1.049, 0.091, 1.357) + [ATG_GAS, ATG_ZERO_CARBON],
    "N-MID": ATG__base(1.909, 1.045, 0.087, 1.289) + [ATG_GAS, ATG_ZERO_CARBON],
    "N-HIGH": ATG__base(7.367, 0.0, 0.083, 0.445, demand=0.207) + [ATG_GAS, ATG_ZERO_CARBON],
    "N-UHU": ATG__base(8.008, 0.0, 0.071, 0.339, demand=0.191) + [ATG_ZERO_CARBON],
    "N-ATA": ATG__base(0.475, 6.863, 0.091, 1.357) + [ATG_ZERO_CARBON],
    "S-LOW": ATG__base(0.876, 1.0, 0.091, 1.357)
    + [("rider", ATG_RIDER_W, 0.325, "$/GJ", "2026-09-01", "2026-12-31"), ATG_GAS, ATG_ZERO_CARBON],
    "S-MID": ATG__base(1.957, 0.816, 0.087, 1.289)
    + [("rider", ATG_RIDER_W, 0.268, "$/GJ", "2026-09-01", "2026-12-31"), ATG_GAS, ATG_ZERO_CARBON],
    "S-HIGH": ATG__base(5.813, 0.0, 0.083, 0.445, demand=0.188) + [ATG_GAS, ATG_ZERO_CARBON],
    "S-UHU": ATG__base(8.457, 0.0, 0.071, 0.339, demand=0.172) + [ATG_ZERO_CARBON],
    "S-ATA": ATG__base(0.418, 6.422, 0.091, 1.357) + [ATG_ZERO_CARBON],
}
ATG_RECORDS = {
    # code: (tariff name, customer class, structure, effective, usage_min, usage_max, class page)
    "N-LOW": ("Low Use Delivery Service (North)", "residential", "flat", "2026-10-01", None, 1200, 10),
    "N-MID": ("Mid Use Delivery Service (North)", "commercial", "flat", "2026-10-01", 1200, 8000, 11),
    "N-HIGH": ("High Use Delivery Service (North)", "commercial", "demand", "2026-10-01", 8000, 100000, 12),
    "N-UHU": ("Ultra High Use Delivery Service (North)", "industrial", "demand", "2026-05-01", 100000, None, 13),
    "N-ATA": ("Alternative Technology and Appliance Delivery Service (North)", "residential", "flat",
              "2026-05-01", None, 40, 14),
    "S-LOW": ("Low Use Delivery Service (South)", "residential", "flat", "2026-10-01", None, 1200, 12),
    "S-MID": ("Mid Use Delivery Service (South)", "commercial", "flat", "2026-10-01", 1200, 8000, 13),
    "S-HIGH": ("High Use Delivery Service (South)", "commercial", "demand", "2026-10-01", 8000, 100000, 14),
    "S-UHU": ("Ultra High Use Delivery Service (South)", "industrial", "demand", "2026-05-01", 100000, None, 15),
    "S-ATA": ("Alternative Technology and Appliance Delivery Service (South)", "residential", "flat",
              "2026-05-01", None, 40, 16),
}


def ATG__fixture():
    return json.loads(ATG_FIXTURE.read_text(encoding="utf-8"))


def ATG__documents():
    return {territory: [DocumentPage(page["page_number"], page["text"]) for page in document["pages"]]
            for territory, document in ATG__fixture()["documents"].items()}


def ATG__pages():
    return {key: entry.get("html") or entry.get("text") for key, entry in ATG__fixture()["pages"].items()}


def ATG__parse(documents=None, pages=None, today=ATG_TODAY):
    scraper = ATG_ATCOGasScraper()
    records = scraper.parse_sources(ATG__documents() if documents is None else documents,
                                    ATG__pages() if pages is None else pages, today)
    return {record.tariff_code: record for record in records}, scraper.rejections


def ATG__replace(documents, territory, old, new):
    hits = [index for index, page in enumerate(documents[territory]) if old in page.text]
    assert len(hits) == 1, (territory, old, hits)
    page = documents[territory][hits[0]]
    documents[territory][hits[0]] = DocumentPage(page.page_number, page.text.replace(old, new, 1))
    return documents


def ATG__drop_page(documents, territory, marker):
    kept = [page for page in documents[territory] if marker not in page.text]
    assert len(kept) == len(documents[territory]) - 1, marker
    documents[territory] = kept
    return documents


def ATG__edit_page(pages, key, old, new):
    assert old in pages[key], (key, old)
    pages[key] = pages[key].replace(old, new, 1)
    return pages


def ATG__comps(record, kind):
    return [component for component in record.components if component.component_type == kind]


def ATG__serve(monkeypatch, documents=None, pages=None, failing=()):
    documents = ATG__documents() if documents is None else documents
    pages = ATG__pages() if pages is None else pages
    pdfs = {url: documents[territory] for territory, url in ATG_SCHEDULE_URLS.items() if territory in documents}
    html = {ATG_PAGE_URLS[key]: text for key, text in pages.items()}

    def pdf_pages(self, url):
        if url in failing or url not in pdfs:
            raise OSError("schedule unavailable")
        return pdfs[url]

    def fetch_page(self, url, delay=1.0):
        if url in failing or url not in html:
            raise OSError("page unavailable")
        return html[url]

    monkeypatch.setattr(ATG_ATCOGasScraper, "_pdf_pages", pdf_pages)
    monkeypatch.setattr(ATG_ATCOGasScraper, "fetch_page", fetch_page)
    monkeypatch.setattr(ATG_ATCOGasScraper, "_today", staticmethod(lambda: ATG_TODAY))


# ── Fixture and exact records ─────────────────────────────────

def test_atg_fixture_matches_official_sources():
    fixture = ATG__fixture()
    assert fixture["retrieved_on"] == "2026-10-09" and fixture["landing_url"] == ATG_LANDING_URL
    assert fixture["source_urls"]["north"] == ATG_SCHEDULE_URLS["North"]
    assert fixture["source_urls"]["south"] == ATG_SCHEDULE_URLS["South"]
    for key, entry in fixture["pages"].items():
        assert entry["url"] == ATG_PAGE_URLS[key] == fixture["source_urls"][key]
    for territory, document in fixture["documents"].items():
        assert document["url"] == ATG_SCHEDULE_URLS[territory] and document["pages"]
    assert "RATE SCHEDULES August 1, 2026" in fixture["documents"]["North"]["pages"][0]["text"]
    assert "RATE SCHEDULES September 1, 2026" in fixture["documents"]["South"]["pages"][0]["text"]


def test_atg_all_building_classes_parsed_live():
    records, rejections = ATG__parse()
    assert set(records) == ATG_CODES and rejections == []
    for code, (name, customer_class, structure, effective, low, high, page) in ATG_RECORDS.items():
        record = records[code]
        territory = "North" if code.startswith("N") else "South"
        assert record.tariff_name == name and record.customer_class == customer_class
        assert record.rate_structure == structure and record.effective_date == effective
        assert (record.usage_min, record.usage_max, record.usage_unit) == (low, high, "GJ/year")
        assert record.utility_name == "ATCO Gas" and record.province == "AB" and record.utility_type == "gas"
        assert record.sub_class == territory and record.pricing_method == "regulated"
        assert record.confidence == "high" and record.source_url == ATG_SCHEDULE_URLS[territory]
        assert record.source_page.endswith("PDF page " + str(page))
        assert "GST is not included." in record.notes


def test_atg_exact_component_values_units_and_dates():
    records, _ = ATG__parse()
    for code, expected in ATG_EXPECTED.items():
        actual = [(c.component_type, c.component_name, c.charge_value, c.charge_unit, c.effective_date, c.end_date)
                  for c in records[code].components]
        assert actual == expected, code


def test_atg_every_component_is_sourced_and_dated():
    records, _ = ATG__parse()
    for record in records.values():
        for component in record.components:
            assert component.source_url and component.source_detail and component.effective_date
            assert component.confidence == "high"
    low = records["N-LOW"]
    assert low.components[0].source_detail == "North rate schedule PDF page 10; Low Use Delivery Service, Fixed Charge"
    assert low.components[2].source_detail == "North rate schedule PDF page 7; Rider L, Low Use Delivery Rate"
    assert low.components[3].source_detail == "North rate schedule PDF page 9; Rider T, Low Use Delivery Rate"
    assert records["S-UHU"].components[4].source_detail == (
        "South rate schedule PDF page 10; Rider T, Ultra-High Use Delivery Rate")
    assert records["S-LOW"].components[4].source_detail == (
        "South rate schedule PDF page 11; Rider W, Low Use Delivery Rate")
    assert "AUC Decision 30301-D01-2025" in low.components[0].notes
    assert "AUC Decision 30594-D01-2026" in low.components[2].notes
    assert "AUC Decision 30329-D01-2025" in low.components[3].notes
    assert "AUC Decision 30876-D01-2026" in records["S-LOW"].components[4].notes


def test_atg_demand_classes_keep_native_units_and_billing_demand():
    records, _ = ATG__parse()
    for code, minimum in (("N-HIGH", "50"), ("N-UHU", "400"), ("S-HIGH", "50"), ("S-UHU", "400")):
        (demand,) = ATG__comps(records[code], "demand")
        (transmission,) = ATG__comps(records[code], "transmission")
        assert demand.demand_unit == transmission.demand_unit == "GJ/day"
        assert "24-hour Billing Demand" in demand.notes and minimum + " GJ/day" in demand.notes
        assert "24-hour Billing Demand" in transmission.notes
    assert "summer period" in ATG__comps(records["N-HIGH"], "demand")[0].notes
    for code in ("N-LOW", "N-MID", "N-ATA", "S-LOW", "S-MID", "S-ATA"):
        assert not ATG__comps(records[code], "demand")


def test_atg_default_supply_price_only_on_drt_classes():
    records, _ = ATG__parse()
    for code, record in records.items():
        gas = ATG__comps(record, "commodity")
        if code in ATG_DRT_CODES:
            (component,) = gas
            assert component.market_reference and "changes monthly" in component.notes
            assert "retailer contract prices are excluded" in component.notes
            assert "UCA 2026 Natural Gas Regulated Rates" in component.source_detail
            assert "Billing Period 26-Oct" in component.source_detail
        else:
            assert not gas and "Gas supply is not included" in record.notes
    assert ATG__comps(records["N-LOW"], "commodity")[0].source_url == ATG_PAGE_URLS["ders_residential"]
    assert ATG__comps(records["S-HIGH"], "commodity")[0].source_url == ATG_PAGE_URLS["ders_commercial"]


def test_atg_carbon_is_zero_with_cra_evidence():
    records, _ = ATG__parse()
    for record in records.values():
        (carbon,) = ATG__comps(record, "carbon")
        assert carbon.source_url == ATG_PAGE_URLS["carbon"] and "Alberta" in carbon.notes


def test_atg_municipal_riders_and_rider_e_are_notes_without_values():
    records, _ = ATG__parse()
    for record in records.values():
        assert "Conditional: Rider A (municipal franchise fee) and Rider B" in record.notes
        assert not [c for c in record.components if "Rider A" in c.component_name or "Rider E" in c.component_name]
        assert all(c.charge_value != 3.15 for c in record.components)
    for code in ("S-LOW", "S-MID", "S-HIGH", "S-UHU", "S-ATA"):
        assert "Rider E, a deemed value of natural gas of $3.150 per GJ (effective March 1, 2025)" in records[code].notes
    assert "Rider E" not in records["N-LOW"].notes


def test_atg_class_specific_notes():
    records, _ = ATG__parse()
    assert "classed residential here" in records["N-LOW"].notes
    assert "Conditional eligibility: available by request only" in records["S-ATA"].notes
    assert records["N-ATA"].eligibility.startswith("Available by request only")
    assert "net zero/near net zero emission homes" in records["N-ATA"].eligibility
    assert "\u2022" not in records["N-ATA"].eligibility


def test_atg_excluded_classes_never_emitted():
    records, _ = ATG__parse()
    names = " ".join(record.tariff_name for record in records.values())
    assert not any(word in names for word in ("Irrigation", "Producer", "Unmetered"))
    assert all(c.charge_value != 0.044 for record in records.values() for c in record.components)


# ── Mutations: values, pages, units, dates ────────────────────

def test_atg_changed_value_propagates():
    documents = ATG__replace(ATG__documents(), "North", "Fixed Charge: $ 0.997 per Day", "Fixed Charge: $ 0.998 per Day")
    records, _ = ATG__parse(documents)
    assert ATG__comps(records["N-LOW"], "fixed")[0].charge_value == 0.998
    pages = ATG__edit_page(ATG__pages(), "ders_residential", "1.458", "1.512")
    pages = ATG__edit_page(pages, "ders_commercial", "1.458", "1.512")
    pages = ATG__edit_page(pages, "uca", "1.458", "1.512")
    records, rejections = ATG__parse(pages=pages)
    assert set(records) == ATG_CODES and rejections == []
    assert ATG__comps(records["S-MID"], "commodity")[0].charge_value == 1.512


def test_atg_missing_class_page_rejects_only_that_class():
    records, rejections = ATG__parse(ATG__drop_page(ATG__documents(), "North", "MID USE DELIVERY SERVICE"))
    assert set(records) == ATG_CODES - {"N-MID"}
    assert rejections == ["N-MID: Mid Use Delivery Service page is missing"]


def test_atg_wrong_fixed_unit_rejects_only_that_class():
    documents = ATG__replace(ATG__documents(), "South", "Fixed Charge: $ 0.876 per Day", "Fixed Charge: $ 0.876 per Month")
    records, rejections = ATG__parse(documents)
    assert set(records) == ATG_CODES - {"S-LOW"} and rejections[0].startswith("S-LOW: unexpected units")


def test_atg_wrong_rider_t_unit_rejects_only_that_class():
    documents = ATG__replace(ATG__documents(), "North", "High Use Delivery Rate $0.445 per GJ per Day of 24 Hr. Billing Demand",
                         "High Use Delivery Rate $0.445 per GJ")
    records, rejections = ATG__parse(documents)
    assert set(records) == ATG_CODES - {"N-HIGH"}
    assert rejections == ['N-HIGH: Rider "T" unit $/GJ does not fit High Use Delivery Service']


def test_atg_unreadable_rider_l_row_rejects_only_that_class():
    old = "Mid Use Delivery Rate " + ATG_EN_DASH + " May 1, 2026 to December 31, 2026 $0.087 per GJ Debit"
    documents = ATG__replace(ATG__documents(), "South", old, old.replace(" Debit", ""))
    records, rejections = ATG__parse(documents)
    assert set(records) == ATG_CODES - {"S-MID"} and "row is unreadable" in rejections[0]


def test_atg_rider_l_credit_is_negative():
    old = "Low Use Delivery Rate " + ATG_EN_DASH + " May 1, 2026 to December 31, 2026 $0.091 per GJ Debit"
    documents = ATG__replace(ATG__documents(), "North", old, old.replace("Debit", "Credit"))
    records, _ = ATG__parse(documents)
    (rider,) = ATG__comps(records["N-LOW"], "rider")
    assert rider.charge_value == -0.091 and rider.notes.startswith("Credit (a refund)")
    assert ATG__comps(records["N-ATA"], "rider")[0].charge_value == 0.091


def test_atg_future_class_effective_date_rejects_that_class():
    old = "ATCO Gas Effective January 1, 2026 by Decision 30301-D01-2025\nThis Replaces High Use"
    documents = ATG__replace(ATG__documents(), "North", old, old.replace("January 1, 2026", "November 1, 2026"))
    records, rejections = ATG__parse(documents)
    assert set(records) == ATG_CODES - {"N-HIGH"}
    assert rejections == ["N-HIGH: rates effective 2026-11-01 are not yet in force"]


def test_atg_missing_class_header_rejects_that_class():
    old = "ATCO Gas Effective January 1, 2026 by Decision 30301-D01-2025\nThis Replaces Alternative"
    documents = ATG__replace(ATG__documents(), "South", old, "This Replaces Alternative")
    records, rejections = ATG__parse(documents)
    assert set(records) == ATG_CODES - {"S-ATA"}
    assert rejections == ["S-ATA: effective-date header is missing"]


def test_atg_future_edition_rejects_the_territory():
    documents = ATG__replace(ATG__documents(), "North", "RATE SCHEDULES August 1, 2026", "RATE SCHEDULES November 1, 2026")
    documents = ATG__replace(documents, "North", "ATCO Gas Effective August 1, 2026\nATCO GAS AND PIPELINES LTD. - NORTH",
                         "ATCO Gas Effective November 1, 2026\nATCO GAS AND PIPELINES LTD. - NORTH")
    records, rejections = ATG__parse(documents)
    assert set(records) == {code for code in ATG_CODES if code.startswith("S-")}
    assert len(rejections) == 5 and all("not yet in effect" in reason for reason in rejections)


def test_atg_cover_and_index_edition_mismatch_rejects_the_territory():
    documents = ATG__replace(ATG__documents(), "South", "RATE SCHEDULES September 1, 2026", "RATE SCHEDULES October 1, 2026")
    records, rejections = ATG__parse(documents)
    assert set(records) == {code for code in ATG_CODES if code.startswith("N-")}
    assert all("edition date differs" in reason for reason in rejections)


def test_atg_missing_schedule_rejects_only_that_territory():
    documents = ATG__documents()
    documents.pop("South")
    records, rejections = ATG__parse(documents)
    assert set(records) == {code for code in ATG_CODES if code.startswith("N-")}
    assert rejections[0] == "S-LOW: South rate schedule PDF unavailable"


def test_atg_listed_rider_without_schedule_rejects_that_class():
    old = "Transmission Service Charge: Rider " + ATG_LDQ + "T" + ATG_RDQ + "\nRATE SWITCHING: A Low Use"
    new = old.replace("\nRATE", "\nWeather Deferral Account Rider: Rider " + ATG_LDQ + "W" + ATG_RDQ + "\nRATE")
    records, rejections = ATG__parse(ATG__replace(ATG__documents(), "North", old, new))
    assert set(records) == ATG_CODES - {"N-LOW"}
    assert rejections == ['N-LOW: Rider "W" schedule page is missing']


def test_atg_rider_applicability_mismatch_rejects_that_class():
    old = "Transmission Service Charge: Rider " + ATG_LDQ + "T" + ATG_RDQ + "\nRATE SWITCHING:\nCustomers switching"
    documents = ATG__replace(ATG__documents(), "North", old, "RATE SWITCHING:\nCustomers switching")
    records, rejections = ATG__parse(documents)
    assert set(records) == ATG_CODES - {"N-ATA"}
    assert "disagree on whether it applies" in rejections[0]


def test_atg_extra_unmodelled_charge_rejects_that_class():
    old = "Variable Charge: $ 1.045 per GJ"
    documents = ATG__replace(ATG__documents(), "North", old, old + "\nMinimum Charge: $ 5.000 per Month")
    records, rejections = ATG__parse(documents)
    assert set(records) == ATG_CODES - {"N-MID"}
    assert rejections == ["N-MID: unexpected additional charge in the CHARGES section"]


# ── Riders by date ────────────────────────────────────────────

def test_atg_expired_rider_w_is_excluded_with_note():
    documents = ATG__replace(ATG__documents(), "South", "effective September 1, 2026 to December 31, 2026.",
                         "effective September 1, 2026 to September 30, 2026.")
    records, rejections = ATG__parse(documents)
    assert set(records) == ATG_CODES and rejections == []
    for code in ("S-LOW", "S-MID"):
        assert not [c for c in records[code].components if c.component_name == ATG_RIDER_W]
        assert 'Rider "W" (Weather Deferral Account Rider) applied from September 1, 2026 to September 30, 2026'\
            in records[code].notes
        assert records[code].effective_date == "2026-10-01"


def test_atg_expired_rider_l_is_excluded_and_new_month_needs_supply_price():
    records, rejections = ATG__parse(today=date(2027, 1, 5))
    assert set(records) == {"N-UHU", "N-ATA", "S-UHU", "S-ATA"}
    for record in records.values():
        assert not [c for c in record.components if c.component_name == ATG_RIDER_L]
        assert 'Rider "L" (Load Balancing Deferral Account Rider) applied from May 1, 2026 to December 31, 2026'\
            in record.notes
        assert record.effective_date == "2026-01-01"
    assert any("UCA table '2027 Natural Gas Regulated Rates in $/GJ' is missing" in r or "27-Jan" in r
               for r in rejections)


def test_atg_future_rider_period_rejects_classes_that_list_it():
    old = "Low Use Delivery Rate " + ATG_EN_DASH + " May 1, 2026 to December 31, 2026 $0.091 per GJ Debit"
    documents = ATG__replace(ATG__documents(), "South", old, old.replace("May 1, 2026", "November 1, 2026"))
    records, rejections = ATG__parse(documents)
    assert set(records) == ATG_CODES - {"S-LOW"}
    assert rejections == ['S-LOW: Rider "L" has no value in force on 2026-10-09']


# ── Default supply price (DERS + UCA) ─────────────────────────

def test_atg_next_month_without_published_price_rejects_drt_classes():
    records, rejections = ATG__parse(today=date(2026, 11, 2))
    assert set(records) == ATG_CODES - ATG_DRT_CODES
    assert all("26-Nov" in reason for reason in rejections) and len(rejections) == 6


def test_atg_uca_month_missing_rejects_drt_classes():
    pages = ATG__pages()
    start = pages["uca"].index("October")
    row_start = pages["uca"].rindex("<tr", 0, start)
    row_end = pages["uca"].index("</tr>", start) + len("</tr>")
    pages["uca"] = pages["uca"][:row_start] + pages["uca"][row_end:]
    records, rejections = ATG__parse(pages=pages)
    assert set(records) == ATG_CODES - ATG_DRT_CODES
    assert all("UCA table has no October 2026 default rate yet" in reason for reason in rejections)


def test_atg_ders_and_uca_disagreement_rejects_drt_classes():
    records, rejections = ATG__parse(pages=ATG__edit_page(ATG__pages(), "uca", "1.458", "1.459"))
    assert set(records) == ATG_CODES - ATG_DRT_CODES
    assert all("differs from the UCA default-rates table" in reason for reason in rejections)


def test_atg_ders_wrong_unit_rejects_classes_using_that_page():
    pages = ATG__edit_page(ATG__pages(), "ders_residential", 'data-rate-heading-measure-label-text="/GJ"',
                       'data-rate-heading-measure-label-text="/m\u00b3"')
    records, rejections = ATG__parse(pages=pages)
    assert set(records) == ATG_CODES - {"N-LOW", "S-LOW"}
    assert all("/GJ unit is missing" in reason for reason in rejections)


def test_atg_missing_ders_page_rejects_only_drt_classes():
    pages = ATG__pages()
    pages.pop("ders_commercial")
    records, rejections = ATG__parse(pages=pages)
    assert set(records) == ATG_CODES - {"N-MID", "N-HIGH", "S-MID", "S-HIGH"}
    assert len(rejections) == 4


# ── Carbon evidence ───────────────────────────────────────────

@pytest.mark.parametrize(("old", "new"), [
    ("by setting all fuel charge rates to zero", "by setting fuel charge rates"),
    ("The rates applied in Alberta, Manitoba,", "The rates applied in Manitoba,"),
])
def test_atg_missing_carbon_evidence_rejects_everything(old, new):
    records, rejections = ATG__parse(pages=ATG__edit_page(ATG__pages(), "carbon", old, new))
    assert records == {} and rejections[0].startswith("all classes: CRA evidence")


# ── Scraper level ─────────────────────────────────────────────

def test_atg_scrape_marks_all_records_live(monkeypatch):
    ATG__serve(monkeypatch)
    records = ATG_ATCOGasScraper().scrape()
    assert {record.tariff_code for record in records} == ATG_CODES
    assert all("Provenance: live_parsed" in record.notes and "seed_fallback" not in record.notes for record in records)
    assert all(c.notes.startswith("Provenance: live_parsed") for record in records for c in record.components)


def test_atg_scrape_supply_outage_keeps_only_classes_without_supply_price(monkeypatch):
    ATG__serve(monkeypatch, failing=(ATG_PAGE_URLS["ders_residential"], ATG_PAGE_URLS["ders_commercial"]))
    records = ATG_ATCOGasScraper().scrape()
    assert {record.tariff_code for record in records} == ATG_CODES - ATG_DRT_CODES
    assert all("live_parsed" in record.notes and "seed_fallback" not in record.notes for record in records)


def test_atg_scrape_total_failure_returns_labelled_seeds():
    records = ATG_ATCOGasScraper().scrape()
    assert [record.tariff_code for record in records] == ["D-South", "D-North"]
    assert all(record.confidence == "unverified" and "seed_fallback" in record.notes for record in records)
    assert all(c.confidence == "unverified" for record in records for c in record.components)


def test_atg_scrape_without_carbon_evidence_returns_labelled_seeds(monkeypatch):
    ATG__serve(monkeypatch, failing=(ATG_PAGE_URLS["carbon"],))
    records = ATG_ATCOGasScraper().scrape()
    assert [record.tariff_code for record in records] == ["D-South", "D-North"]
    assert all("seed_fallback" in record.notes for record in records)


# ======================================================================
# EPCOR Natural Gas Ontario, Aylmer and Southern Bruce (batch 12)
# ======================================================================
from scrapers.utils.parsing import DocumentPage
from scrapers.utilities.epcor_gas_ontario import CRA_URL as EPG_CRA_URL, RDS_SEARCH_URL as EPG_RDS_SEARCH_URL, UTILITY_NAME as EPG_UTILITY_NAME, ZONES as EPG_ZONES, EPCOROntarioGasScraper as EPG_EPCOROntarioGasScraper, find_rate_order_url as EPG_find_rate_order_url, notice_case as EPG_notice_case, notice_url as EPG_notice_url, page_effective_date as EPG_page_effective_date
import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest


EPG_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "epcor_gas_ontario.json"
EPG_TODAY = date(2026, 10, 9)
EPG_EFF = "2026-10-01"
EPG_END = "2026-12-31"
EPG_AYLMER_ORDER = "https://www.rds.oeb.ca/CMWebDrawer/Record/956907/File/document"
EPG_SB_ORDER = "https://www.rds.oeb.ca/CMWebDrawer/Record/956917/File/document"
EPG_CARBON = ("carbon", "Federal Carbon Charge", 0.0, "$/m³", "2025-04-01", None, None)
EPG_TRANSPORT = ("delivery", "Transportation Charge", 0.029161, "$/m³", EPG_EFF, None, None)
EPG_AYL_SUPPLY = [
    ("commodity", "Gas Supply Charge — PGCVA Reference Price", 0.17444, "$/m³", EPG_EFF, None, None),
    ("commodity", "Gas Supply Charge — GPRA Recovery Rate", -0.001408, "$/m³", EPG_EFF, None, None),
]
EPG_SB_SUPPLY = ("commodity", "Gas Supply Charge", 0.151554, "$/m³", EPG_EFF, None, None)


def EPG__ayl_riders(wacc):
    return [
        ("rider", "Rate Rider for PGTVA Recovery", 0.003241, "$/m³", EPG_EFF, EPG_END, None),
        ("rider", "Rate Rider for UFGVA Recovery", 0.00427, "$/m³", EPG_EFF, EPG_END, None),
        ("rider", "Rate Rider for WACC Recovery", wacc, "$/m³", EPG_EFF, EPG_END, None),
        ("rider", "Rate Rider for REDA Recovery", 0.06, "$/month", EPG_EFF, EPG_END, None),
    ]


def EPG__sb_riders(delay, ecva, ciacva, mtva, orda, cvva, ufgva, stva):
    riders = [
        ("rider", "Rate Rider for Delay in Revenue Recovery", delay, "$/m³", EPG_EFF, "2028-12-31", None),
        ("rider", "Rate Rider for ECVA Recovery", ecva, "$/m³", EPG_EFF, EPG_END, None),
        ("rider", "Rate Rider for CIACVA Recovery", ciacva, "$/m³", EPG_EFF, EPG_END, None),
        ("rider", "Rate Rider for MTVA Recovery", mtva, "$/m³", EPG_EFF, EPG_END, None),
        ("rider", "Rate Rider for ORDA Recovery", orda, "$/m³", EPG_EFF, EPG_END, None),
    ]
    if cvva is not None:
        riders.append(("rider", "Rate Rider for CVVA Recovery", cvva, "$/month", EPG_EFF, EPG_END, None))
    return riders + [
        ("rider", "Rate Rider for UFGVA Recovery", ufgva, "$/m³", EPG_EFF, EPG_END, None),
        ("rider", "Rate Rider for S&TVA Recovery", stva, "$/m³", EPG_EFF, EPG_END, None),
    ]


def EPG__block(text, value, season=None):
    name = "Delivery Charge — " + text + (" (" + season + ")" if season else "")
    return ("delivery", name, value, "$/m³", EPG_EFF, None, None)


EPG_SB1 = [
    ("fixed", "Monthly Fixed Charge", 29.57, "$/month", EPG_EFF, None, None),
    EPG__block("first 100 m³ per month", 0.306018),
    EPG__block("next 400 m³ per month", 0.29999),
    EPG__block("over 500 m³ per month", 0.291129),
    ("delivery", "Upstream Recovery Charge", 0.01474, "$/m³", EPG_EFF, None, None),
    ("delivery", "Transportation and Storage Charge", 0.026982, "$/m³", EPG_EFF, None, None),
    *EPG__sb_riders(0.01633, 0.001794, 0.020743, -0.004139, -0.002478, 8.53, -0.00163, 0.011569),
    EPG_SB_SUPPLY, EPG_CARBON,
]
APR_OCT, NOV_MAR = "April 1 - October 31", "November 1 - March 31"
APR_DEC, JAN_MAR = "April 1 - December 31", "January 1 - March 31"

# name: (code, customer_class, rate_structure, usage_min, usage_max, components)
EPG_EXPECTED = {
    "Rate 1 Residential (Aylmer)": ("AYL-1-RES", "residential", "flat", None, None, [
        ("fixed", "Monthly Fixed Charge", 29.32, "$/month", EPG_EFF, None, None),
        ("delivery", "Delivery Charge", 0.087763, "$/m³", EPG_EFF, None, None),
        *EPG__ayl_riders(-0.00177), EPG_TRANSPORT, *EPG_AYL_SUPPLY, EPG_CARBON]),
    "Rate 1 General Service (Aylmer)": ("AYL-1-GS", "commercial", "tiered", None, None, [
        ("fixed", "Monthly Fixed Charge", 28.73, "$/month", EPG_EFF, None, None),
        EPG__block("first 1,000 m³ per month", 0.120116), EPG__block("over 1,000 m³ per month", 0.095904),
        *EPG__ayl_riders(-0.00068), EPG_TRANSPORT, *EPG_AYL_SUPPLY, EPG_CARBON]),
    "Rate 2 Seasonal Service (Aylmer)": ("AYL-2", "commercial", "tiered", None, None, [
        ("fixed", "Monthly Fixed Charge", 25.09, "$/month", EPG_EFF, None, None),
        EPG__block("first 1,000 m³ per month", 0.174482, APR_OCT), EPG__block("first 1,000 m³ per month", 0.22652, NOV_MAR),
        EPG__block("next 24,000 m³ per month", 0.078075, APR_OCT), EPG__block("next 24,000 m³ per month", 0.145808, NOV_MAR),
        EPG__block("over 25,000 m³ per month", 0.056454, APR_OCT), EPG__block("over 25,000 m³ per month", 0.158877, NOV_MAR),
        *EPG__ayl_riders(-0.000559), EPG_TRANSPORT, *EPG_AYL_SUPPLY, EPG_CARBON]),
    "Rate 3 Special Large Volume Contract (Aylmer)": ("AYL-3", "industrial", "demand", 113000.0, None, [
        ("fixed", "Monthly Customer Charge — firm or interruptible service", 240.79, "$/month", EPG_EFF, None,
         "conditional"),
        ("fixed", "Monthly Customer Charge — combined firm and interruptible service", 267.2, "$/month", EPG_EFF, None,
         "conditional"),
        ("demand", "Monthly Demand Charge", 0.348861, "$/m³/month", EPG_EFF, None, None),
        ("delivery", "Monthly Firm Delivery Charge", 0.017997, "$/m³", EPG_EFF, None, None),
        ("delivery", "Monthly Interruptible Delivery Charge (negotiated)", None, "$/m³", EPG_EFF, None, "conditional"),
        *EPG__ayl_riders(-0.000602), EPG_TRANSPORT, *EPG_AYL_SUPPLY, EPG_CARBON]),
    "Rate 4 General Service Peaking (Aylmer)": ("AYL-4", "commercial", "tiered", None, None, [
        ("fixed", "Monthly Fixed Charge", 25.45, "$/month", EPG_EFF, None, None),
        EPG__block("first 1,000 m³ per month", 0.197641, APR_DEC), EPG__block("first 1,000 m³ per month", 0.259215, JAN_MAR),
        EPG__block("over 1,000 m³ per month", 0.111341, APR_DEC), EPG__block("over 1,000 m³ per month", 0.194469, JAN_MAR),
        *EPG__ayl_riders(-0.001196), EPG_TRANSPORT, *EPG_AYL_SUPPLY, EPG_CARBON]),
    "Rate 5 Interruptible Peaking Contract (Aylmer)": ("AYL-5", "industrial", "flat", 50000.0, None, [
        ("fixed", "Monthly Fixed Charge", 202.35, "$/month", EPG_EFF, None, None),
        ("delivery", "Monthly Interruptible Delivery Charge (negotiated)", None, "$/m³", EPG_EFF, None, "conditional"),
        *EPG__ayl_riders(-0.000567), EPG_TRANSPORT, *EPG_AYL_SUPPLY, EPG_CARBON]),
    "Rate 1 General Firm Service — Residential (Southern Bruce)": ("SB-1", "residential", "tiered", None, 10000.0,
                                                                  EPG_SB1),
    "Rate 1 General Firm Service — Commercial (Southern Bruce)": ("SB-1", "commercial", "tiered", None, 10000.0,
                                                                 EPG_SB1),
    "Rate 6 Large Volume General Firm Service (Southern Bruce)": ("SB-6", "commercial", "tiered", 10000.0, None, [
        ("fixed", "Monthly Fixed Charge", 117.49, "$/month", EPG_EFF, None, None),
        EPG__block("first 1,000 m³ per month", 0.282309), EPG__block("next 6,000 m³ per month", 0.254079),
        EPG__block("over 7,000 m³ per month", 0.241373),
        ("delivery", "Upstream Recovery Charge", 0.0292, "$/m³", EPG_EFF, None, None),
        ("delivery", "Transportation and Storage Charge", 0.056413, "$/m³", EPG_EFF, None, None),
        *EPG__sb_riders(0.00909, 0.001949, 0.026496, -0.006861, -0.002007, 26.03, -0.001575, 0.015659),
        EPG_SB_SUPPLY, EPG_CARBON]),
    "Rate 11 Large Volume Seasonal Service (Southern Bruce)": ("SB-11", "commercial", "flat", 10000.0, None, [
        ("fixed", "Monthly Fixed Charge", 233.99, "$/month", EPG_EFF, None, None),
        ("delivery", "Delivery Charge", 0.175362, "$/m³", EPG_EFF, None, None),
        ("delivery", "Authorized Overrun Charge (December 16 - April 30)", 0.179151, "$/m³", EPG_EFF, None,
         "conditional"),
        ("delivery", "Unauthorized Overrun Charge (December 16 - April 30)", 4.290039, "$/m³", EPG_EFF, None,
         "conditional"),
        ("delivery", "Upstream Recovery Charge", 0.000352, "$/m³", EPG_EFF, None, None),
        ("delivery", "Transportation and Storage Charge", 0.018166, "$/m³", EPG_EFF, None, None),
        *EPG__sb_riders(0.005524, 0.001031, 0.004372, -0.001135, -0.000662, None, -0.001973, 0.004799),
        EPG_SB_SUPPLY, EPG_CARBON]),
}
EPG_AYLMER = {name for name in EPG_EXPECTED if name.endswith("(Aylmer)")}
EPG_SOUTHERN_BRUCE = set(EPG_EXPECTED) - EPG_AYLMER


def EPG__doc():
    return json.loads(EPG_FIXTURE.read_text(encoding="utf-8"))


def EPG__sources(doc=None):
    doc = doc or EPG__doc()
    zones = {}
    for key, zone in doc["zones"].items():
        zones[key] = {
            "page_url": zone["page"]["url"],
            "page_html": zone["page"]["html"],
            "notice_url": zone["notice"]["url"],
            "notice_pages": [DocumentPage(p["page_number"], p["text"]) for p in zone["notice"]["pages"]],
            "order_url": zone["order"]["url"],
            "order_pages": [DocumentPage(p["page_number"], p["text"]) for p in zone["order"]["pages"]],
        }
    return {"cra": doc["cra"]["text"], "zones": zones}


def EPG__parse(sources=None, today=EPG_TODAY):
    scraper = EPG_EPCOROntarioGasScraper()
    records = scraper.parse_sources(sources if sources is not None else EPG__sources(), today)
    return {record.tariff_name: record for record in records}, scraper


def EPG__edit_page(sources, zone, old, new, count=-1):
    html = sources["zones"][zone]["page_html"]
    assert old in html, old
    sources["zones"][zone]["page_html"] = html.replace(old, new, count)
    return sources


def EPG__edit_order(sources, zone, old, new):
    pages = sources["zones"][zone]["order_pages"]
    assert any(old in page.text for page in pages), old
    sources["zones"][zone]["order_pages"] = [DocumentPage(page.page_number, page.text.replace(old, new))
                                             for page in pages]
    return sources


def EPG__edit_notice(sources, zone, old, new):
    pages = sources["zones"][zone]["notice_pages"]
    assert any(old in page.text for page in pages), old
    sources["zones"][zone]["notice_pages"] = [DocumentPage(page.page_number, page.text.replace(old, new))
                                              for page in pages]
    return sources


def EPG__component(record, name):
    (match,) = [c for c in record.components if c.component_name == name]
    return match


def test_epg_fixture_sources_match_module_urls():
    doc = EPG__doc()
    assert doc["retrieved_on"] == "2026-10-09" and doc["cra"]["url"] == EPG_CRA_URL
    assert set(doc["zones"]) == set(EPG_ZONES)
    for key, zone in doc["zones"].items():
        assert zone["page"]["url"] == EPG_ZONES[key].page_url
        assert zone["notice"]["url"] == EPG_notice_url(EPG_ZONES[key], date(2026, 10, 1))
        assert zone["rds_search"]["url"].startswith(EPG_RDS_SEARCH_URL.split("{")[0])
    assert doc["zones"]["aylmer"]["order"]["url"] == EPG_AYLMER_ORDER
    assert doc["zones"]["sb"]["order"]["url"] == EPG_SB_ORDER


def test_epg_expected_records_exact():
    records, scraper = EPG__parse()
    assert set(records) == set(EPG_EXPECTED)
    assert scraper.rejections == [] and scraper.unmodelled == []
    for name, (code, customer_class, structure, usage_min, usage_max, components) in EPG_EXPECTED.items():
        record = records[name]
        assert (record.utility_name, record.province, record.utility_type) == (EPG_UTILITY_NAME, "ON", "gas")
        assert (record.tariff_code, record.customer_class, record.rate_structure) == (code, customer_class, structure)
        assert (record.usage_min, record.usage_max) == (usage_min, usage_max)
        assert record.usage_unit == ("m³/year" if usage_min or usage_max else None)
        assert record.effective_date == EPG_EFF and record.end_date is None and record.pricing_method == "regulated"
        assert record.confidence == "high" and record.eligibility and record.description
        assert [(c.component_type, c.component_name, c.charge_value, c.charge_unit, c.effective_date, c.end_date,
                 c.sub_component) for c in record.components] == components, name


def test_epg_zone_sources_and_dates_on_every_component():
    records, _ = EPG__parse()
    for name, record in records.items():
        zone = "Aylmer" if name in EPG_AYLMER else "Southern Bruce"
        assert record.sub_class == zone + " service area"
        assert record.source_url == EPG_ZONES["aylmer" if zone == "Aylmer" else "sb"].page_url
        for component in record.components:
            assert component.source_url and component.source_detail and component.effective_date
            assert component.charge_currency == "CAD"
            if component.component_type == "rider":
                assert component.end_date and "Rider period" in component.notes
        case = "EB-2026-0225" if zone == "Aylmer" else "EB-2026-0226"
        assert case in record.notes and case in record.source_page


def test_epg_reda_rider_follows_the_approved_schedule_unit():
    records, _ = EPG__parse()
    for name in EPG_AYLMER:
        reda = EPG__component(records[name], "Rate Rider for REDA Recovery")
        assert (reda.charge_value, reda.charge_unit, reda.source_url) == (0.06, "$/month", EPG_AYLMER_ORDER)
        assert "0.06¢ per month" in reda.source_detail and "$0.06 per month" in reda.notes
        assert "0.06¢ per month" in records[name].notes


def test_epg_rate4_season_split_follows_the_approved_schedule():
    records, _ = EPG__parse()
    record = records["Rate 4 General Service Peaking (Aylmer)"]
    blocks = [c for c in record.components if c.component_name.startswith("Delivery Charge")]
    assert [(c.season, c.season_months, c.tier_number, c.tier_threshold) for c in blocks] == [
        (APR_DEC, "Apr-Dec", 1, 1000.0), (JAN_MAR, "Jan-Mar", 1, 1000.0),
        (APR_DEC, "Apr-Dec", 2, None), (JAN_MAR, "Jan-Mar", 2, None)]
    assert "April 1 to October 31 and November 1 to March 31" in record.notes
    rate2 = records["Rate 2 Seasonal Service (Aylmer)"]
    assert {c.season_months for c in rate2.components if c.season} == {"Apr-Oct", "Nov-Mar"}
    assert "Season periods" not in rate2.notes


def test_epg_tiers_join_up():
    records, _ = EPG__parse()
    sb6 = records["Rate 6 Large Volume General Firm Service (Southern Bruce)"]
    blocks = [c for c in sb6.components if c.tier_number]
    assert [(c.tier_number, c.tier_threshold, c.tier_unit) for c in blocks] == [
        (1, 1000.0, "m³/month"), (2, 7000.0, "m³/month"), (3, None, None)]


def test_epg_negotiated_ranges_stay_conditions_without_value():
    records, _ = EPG__parse()
    for name, low, high in (("Rate 3 Special Large Volume Contract (Aylmer)", "6.6129", "10.0852"),
                            ("Rate 5 Interruptible Peaking Contract (Aylmer)", "4.1116", "7.5930")):
        negotiated = EPG__component(records[name], "Monthly Interruptible Delivery Charge (negotiated)")
        assert negotiated.charge_value is None and negotiated.sub_component == "conditional"
        assert negotiated.notes.startswith("Conditional:") and low in negotiated.notes and high in negotiated.notes


def test_epg_conditional_components_are_marked():
    records, _ = EPG__parse()
    conditional = [(name, c) for name, record in records.items() for c in record.components
                   if c.sub_component == "conditional"]
    assert len(conditional) == 6
    assert all(c.notes.startswith("Conditional:") for _, c in conditional)


def test_epg_carbon_is_dated_cra_zero():
    records, _ = EPG__parse()
    for record in records.values():
        (carbon,) = [c for c in record.components if c.component_type == "carbon"]
        assert (carbon.charge_value, carbon.effective_date, carbon.source_url) == (0.0, "2025-04-01", EPG_CRA_URL)
        assert "April 1, 2025" in carbon.notes and "Ontario" in carbon.notes


def test_epg_fixed_charge_bill32_note_needs_the_schedule_footnote():
    records, _ = EPG__parse()
    fixed = [c for record in records.values() for c in record.components if c.component_name == "Monthly Fixed Charge"]
    assert len(fixed) == 9 and all("Bill 32" in c.notes for c in fixed)
    sources = EPG__edit_order(EPG__sources(), "sb", "one dollar per month in accordance with Bill 32",
                          "one dollar per month")
    records, _ = EPG__parse(sources)
    assert EPG__component(records["Rate 11 Large Volume Seasonal Service (Southern Bruce)"],
                      "Monthly Fixed Charge").notes is None


def test_epg_exclusions_reported_not_built():
    records, scraper = EPG__parse()
    assert any(entry.startswith("Aylmer Rate 6:") for entry in scraper.exclusions)
    assert any(entry.startswith("Southern Bruce Rate 16:") for entry in scraper.exclusions)
    assert not any("Rate 6 " in name and "Aylmer" in name for name in records)
    assert not any("Rate 16" in name for name in records)


def test_epg_value_changed_in_both_sources_propagates():
    sources = EPG__edit_page(EPG__sources(), "aylmer", "8.7763¢ per m³", "8.9123¢ per m³")
    EPG__edit_order(sources, "aylmer", "8.7763 cents per m3", "8.9123 cents per m3")
    records, _ = EPG__parse(sources)
    assert EPG__component(records["Rate 1 Residential (Aylmer)"], "Delivery Charge").charge_value == 0.089123
    assert set(records) == set(EPG_EXPECTED)


def test_epg_page_value_not_in_approved_schedule_rejects_only_that_class():
    records, scraper = EPG__parse(EPG__edit_page(EPG__sources(), "aylmer", "12.0116¢ per m³", "12.1116¢ per m³"))
    assert set(records) == set(EPG_EXPECTED) - {"Rate 1 General Service (Aylmer)"}
    assert any("AYL-1-GS" in entry for entry in scraper.rejections)


def test_epg_missing_class_rejects_only_that_class():
    records, scraper = EPG__parse(EPG__edit_page(EPG__sources(), "sb", "Rate 6: Large Volume (Large volume general firm service)",
                                         "Rate 6: Large Volume Firm Service"))
    assert set(records) == set(EPG_EXPECTED) - {"Rate 6 Large Volume General Firm Service (Southern Bruce)"}
    assert scraper.unmodelled == ["Southern Bruce Rate 6: Large Volume Firm Service"]


def test_epg_missing_zone_rejects_only_that_zone():
    sources = EPG__sources()
    sources["zones"]["sb"] = {}
    records, scraper = EPG__parse(sources)
    assert set(records) == EPG_AYLMER
    assert scraper.rejections == ["Southern Bruce: rates page unavailable"]


def test_epg_wrong_unit_rejects_class():
    records, _ = EPG__parse(EPG__edit_page(EPG__sources(), "aylmer", "8.7763¢ per m³", "8.7763¢ per GJ"))
    assert set(records) == set(EPG_EXPECTED) - {"Rate 1 Residential (Aylmer)"}


def test_epg_unidentified_line_rejects_class():
    records, _ = EPG__parse(EPG__edit_page(EPG__sources(), "aylmer", "Transportation Charge", "Transportation Surcharge", 1))
    assert set(records) == set(EPG_EXPECTED) - {"Rate 1 Residential (Aylmer)"}


def test_epg_range_never_becomes_a_value():
    records, _ = EPG__parse(EPG__edit_page(EPG__sources(), "aylmer", "6.6129 - 10.0852¢ per m³", "6.6129¢ per m³"))
    assert set(records) == set(EPG_EXPECTED) - {"Rate 3 Special Large Volume Contract (Aylmer)"}


def test_epg_missing_effective_date_rejects_zone():
    sources = EPG__edit_page(EPG__sources(), "sb", "The rates below are effective October 1, 2026",
                         "The rates below are current")
    records, scraper = EPG__parse(sources)
    assert set(records) == EPG_AYLMER
    assert scraper.rejections == ["Southern Bruce: rates page effective date missing"]


def test_epg_future_effective_date_rejects_zones():
    records, scraper = EPG__parse(today=date(2026, 9, 30))
    assert records == {}
    assert len(scraper.rejections) == 2 and all("in the future" in entry for entry in scraper.rejections)


def test_epg_notice_effective_date_mismatch_rejects_zone():
    records, scraper = EPG__parse(EPG__edit_notice(EPG__sources(), "aylmer", "effective Oct 1, 2026.", "effective Jul 1, 2026."))
    assert set(records) == EPG_SOUTHERN_BRUCE
    assert scraper.rejections == ["Aylmer: OEB QRAM notice effective date differs from the rates page"]


@pytest.mark.parametrize(("zone", "old", "new", "kept"), [
    ("aylmer", "= 17.3032¢/m³", "= 17.4032¢/m³", EPG_SOUTHERN_BRUCE),
    ("sb", "= 15.1554¢/m³", "= 15.2554¢/m³", EPG_AYLMER),
])
def test_epg_notice_commodity_mismatch_rejects(zone, old, new, kept):
    records, _ = EPG__parse(EPG__edit_notice(EPG__sources(), zone, old, new))
    assert set(records) == kept


def test_epg_gas_supply_parts_must_reconcile():
    sources = EPG__edit_page(EPG__sources(), "aylmer", "(0.1408)¢/m³", "(0.1508)¢/m³")
    EPG__edit_order(sources, "aylmer", "-0.1408 cents per m3", "-0.1508 cents per m3")
    records, scraper = EPG__parse(sources)
    assert set(records) == EPG_SOUTHERN_BRUCE
    assert scraper.rejections == ["Aylmer: gas supply parts do not add to the printed total"]


def test_epg_missing_carbon_evidence_rejects_everything():
    sources = EPG__sources()
    sources["cra"] = sources["cra"].replace("Alberta, Manitoba, Ontario, and Saskatchewan", "Alberta and Manitoba")
    records, scraper = EPG__parse(sources)
    assert records == {} and scraper.rejections[0].startswith("all:")


def test_epg_nonzero_notice_carbon_rejects_zone():
    records, _ = EPG__parse(EPG__edit_notice(EPG__sources(), "sb", "Facilities Carbon Charge (¢/m3) 0.0000¢",
                                     "Facilities Carbon Charge (¢/m3) 1.2000¢"))
    assert set(records) == EPG_AYLMER


def test_epg_expired_rider_rejects_classes():
    records, scraper = EPG__parse(today=date(2027, 1, 5))
    assert records == {}
    assert any("period ended" in entry for entry in scraper.rejections)


def test_epg_missing_approved_schedule_rejects_only_that_class():
    sources = EPG__edit_order(EPG__sources(), "aylmer", "RATE 5 - Interruptible Peaking Contract Rate",
                          "RATE 5 - Interruptible Contract Rate")
    records, _ = EPG__parse(sources)
    assert set(records) == set(EPG_EXPECTED) - {"Rate 5 Interruptible Peaking Contract (Aylmer)"}


def test_epg_unavailable_or_wrong_order_rejects_zone():
    sources = EPG__sources()
    sources["zones"]["sb"]["order_pages"] = []
    records, _ = EPG__parse(sources)
    assert set(records) == EPG_AYLMER
    sources = EPG__sources()
    sources["zones"]["aylmer"]["order_pages"] = EPG__sources()["zones"]["sb"]["order_pages"]
    records, scraper = EPG__parse(sources)
    assert set(records) == EPG_SOUTHERN_BRUCE
    assert scraper.rejections == ["Aylmer: OEB Decision and Rate Order is not EB-2026-0225 for Aylmer"]


def test_epg_discovery_helpers():
    doc = EPG__doc()
    sources = EPG__sources(doc)
    for key, zone in doc["zones"].items():
        case = EPG_notice_case(sources["zones"][key]["notice_pages"])
        assert case == {"aylmer": "EB-2026-0225", "sb": "EB-2026-0226"}[key]
        assert EPG_find_rate_order_url(zone["rds_search"]["html"], case) == zone["order"]["url"]
        assert EPG_find_rate_order_url(zone["rds_search"]["html"], "EB-2026-9999") is None
        assert EPG_page_effective_date(zone["page"]["html"]) == date(2026, 10, 1)


def EPG__responses():
    doc = EPG__doc()
    pages = {doc["cra"]["url"]: doc["cra"]["text"]}
    pdfs = {}
    for zone in doc["zones"].values():
        pages[zone["page"]["url"]] = zone["page"]["html"]
        pages[zone["rds_search"]["url"]] = zone["rds_search"]["html"]
        for key in ("notice", "order"):
            pdfs[zone[key]["url"]] = [DocumentPage(p["page_number"], p["text"]) for p in zone[key]["pages"]]
    return pages, pdfs


def EPG__scrape(pages, pdfs):
    scraper = EPG_EPCOROntarioGasScraper()
    scraper.today = EPG_TODAY
    with patch.object(scraper, "fetch_page", side_effect=lambda url, *a, **k: pages[url]),\
            patch.object(scraper, "_fetch_pdf_pages", side_effect=lambda url: pdfs[url]):
        return scraper.scrape()


def test_epg_scrape_marks_live_with_mocked_fetch():
    records = EPG__scrape(*EPG__responses())
    assert {record.tariff_name for record in records} == set(EPG_EXPECTED)
    assert all(record.notes.startswith("Provenance: live_parsed.") for record in records)
    assert all("seed_fallback" not in record.notes and record.confidence == "high" for record in records)
    assert all(c.notes.startswith("Provenance: live_parsed.") for record in records for c in record.components)


def test_epg_partial_fetch_failure_keeps_other_zone_live():
    pages, pdfs = EPG__responses()
    del pages[EPG_ZONES["sb"].page_url]
    records = EPG__scrape(pages, pdfs)
    assert {record.tariff_name for record in records} == EPG_AYLMER


def test_epg_total_fetch_failure_returns_no_records():
    scraper = EPG_EPCOROntarioGasScraper(registry_entry={"name": EPG_UTILITY_NAME})
    assert scraper.scrape() == []
    assert scraper.rejections and scraper.rejections[0].startswith("all:")


# ======================================================================
# Per-run live/seed provenance summary in run_scrape (batch 12)
# ======================================================================
from scrapers.base import RateComponent, TariffRecord
import logging
import sys
from types import SimpleNamespace

from pipeline import run_scrape
from pipeline.run_scrape import append_step_summary, format_summary_markdown, summarize_run, tally_provenance

OPS_SUMMARY_LIVE_NOTE = "Provenance: live_parsed"
OPS_SUMMARY_VERIFIED_NOTE = "Provenance: officially_verified"
OPS_SUMMARY_SEED_NOTE = "Provenance: seed_fallback"


def OPS__summary_record(utility, notes, name="Residential", components=True):
    return TariffRecord(
        utility_name=utility, province="NS", utility_type="electricity", tariff_name=name,
        confidence="unverified" if notes == OPS_SUMMARY_SEED_NOTE else "high", notes=notes,
        components=[RateComponent("energy", "Energy Charge", 0.1, "$/kWh")] if components else [],
    )


def OPS__summary_scraper(records):
    return SimpleNamespace(scrape=lambda: records)


def OPS__summary_failing_scrape():
    raise RuntimeError("source unavailable")


def OPS__summary_run_main(monkeypatch, tmp_path, scrapers_by_name, argv):
    entries = [{"name": name, "province": "NS", "status": "partial"} for name in scrapers_by_name]
    monkeypatch.setattr(run_scrape, "setup_logging", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_scrape, "DB_PATH", tmp_path / "rates.db")
    monkeypatch.setattr(run_scrape, "load_registry", lambda *args, **kwargs: entries)
    monkeypatch.setattr(run_scrape, "get_active_utilities", lambda registry=None: list(registry))
    monkeypatch.setattr(run_scrape, "load_scraper", lambda entry: scrapers_by_name[entry["name"]])
    monkeypatch.setattr(sys, "argv", ["run_scrape"] + argv)
    run_scrape.main()


def test_ops_tally_provenance_counts_live_markers_and_everything_else_as_seed():
    records = [
        OPS__summary_record("A", OPS_SUMMARY_LIVE_NOTE),
        OPS__summary_record("A", "Rider table checked. " + OPS_SUMMARY_VERIFIED_NOTE, name="Commercial"),
        OPS__summary_record("A", OPS_SUMMARY_SEED_NOTE, name="Seed"),
        OPS__summary_record("A", None, name="Legacy"),
    ]
    assert tally_provenance(records) == {"live": 2, "seed": 2}
    assert tally_provenance([]) == {"live": 0, "seed": 0}


def test_ops_summarize_run_totals_problem_lists_and_problems_first_rows():
    summary = summarize_run({
        "Alpha Power": {"live": 3, "seed": 0, "invalid": 0, "error": None},
        "Bravo Gas": {"live": 0, "seed": 2, "invalid": 0, "error": None},
        "Charlie Hydro": {"error": "source unavailable"},
        "Delta Energy": {"live": 0, "seed": 0, "invalid": 1, "error": None},
        "Echo Electric": {"live": 1, "seed": 1, "invalid": 0, "error": None},
        "Foxtrot Utility": {"live": 0, "seed": 0, "invalid": 0, "error": None},
    })
    assert (summary["utilities"], summary["live"], summary["seed"], summary["invalid"]) == (6, 4, 3, 1)
    assert summary["failed"] == ["Charlie Hydro"]
    assert summary["no_records"] == ["Delta Energy", "Foxtrot Utility"]
    assert summary["seed_only"] == ["Bravo Gas"]
    assert [(row["utility"], row["status"]) for row in summary["rows"]] == [
        ("Charlie Hydro", "failed"),
        ("Delta Energy", "no valid records"),
        ("Foxtrot Utility", "no valid records"),
        ("Bravo Gas", "seed only"),
        ("Echo Electric", "live + seed"),
        ("Alpha Power", "live"),
    ]


def test_ops_summarize_run_puts_invalid_records_first_within_a_status_and_any_error_fails():
    summary = summarize_run({
        "Alpha Power": {"live": 2, "seed": 0, "invalid": 0},
        "Zulu Power": {"live": 2, "seed": 0, "invalid": 3},
        "beta power": {"live": 1, "seed": 0, "invalid": 0},
        "Quiet Failure": {"error": ""},
    })
    assert [row["utility"] for row in summary["rows"]] == ["Quiet Failure", "Zulu Power", "Alpha Power", "beta power"]
    assert summary["failed"] == ["Quiet Failure"]
    assert summary["no_records"] == summary["seed_only"] == []
    assert summarize_run({})["rows"] == []


def test_ops_format_summary_markdown_renders_problems_first_and_escapes_cells():
    summary = summarize_run({
        "Alpha Power": {"live": 3, "seed": 0, "invalid": 0, "error": None},
        "Bravo Gas": {"live": 0, "seed": 2, "invalid": 0, "error": None},
        "Charlie|Hydro": {"error": "HTTP 503\nService   Unavailable"},
        "Delta Energy": {"error": "timeout | " + "x" * 200},
        "Echo": {"error": ""},
    })
    markdown = format_summary_markdown(summary)
    lines = markdown.splitlines()
    assert markdown.endswith("\n")
    assert lines[0] == "## Scrape provenance summary"
    assert "Dry run" not in markdown
    assert "- Live records: 3; seed (estimated) records: 2; invalid records: 0" in lines
    assert "- Utilities: 5; failed: 3; no valid records: 0; seed only: 1" in lines
    header = lines.index("| Utility | Live | Seed | Invalid | Status |")
    assert lines[header + 1] == "| --- | ---: | ---: | ---: | --- |"
    rows = lines[header + 2:]
    assert len(rows) == 5
    assert rows[0] == "| Charlie\\|Hydro | 0 | 0 | 0 | failed: HTTP 503 Service Unavailable |"
    assert rows[1].startswith("| Delta Energy | 0 | 0 | 0 | failed: timeout \\| xxx")
    assert rows[1].endswith("x... |") and "x" * 108 not in rows[1]
    assert rows[2] == "| Echo | 0 | 0 | 0 | failed |"
    assert rows[3] == "| Bravo Gas | 0 | 2 | 0 | seed only |"
    assert rows[4] == "| Alpha Power | 3 | 0 | 0 | live |"


def test_ops_format_summary_markdown_marks_dry_runs():
    lines = format_summary_markdown(summarize_run({}), dry_run=True).splitlines()
    assert "_Dry run: nothing saved to the database._" in lines
    assert "- Utilities: 0; failed: 0; no valid records: 0; seed only: 0" in lines
    assert lines[-1] == "| --- | ---: | ---: | ---: | --- |"


def test_ops_append_step_summary_appends_utf8_to_the_github_summary_file(tmp_path, monkeypatch):
    target = tmp_path / "step_summary.md"
    target.write_text("previous step\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(target))
    append_step_summary("| Énergir | 1 |\n")
    append_step_summary("second\n")
    assert target.read_text(encoding="utf-8") == "previous step\n| Énergir | 1 |\nsecond\n"


def test_ops_append_step_summary_is_a_no_op_without_a_summary_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    append_step_summary("ignored\n")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", "")
    append_step_summary("ignored\n")
    assert list(tmp_path.iterdir()) == []


def test_ops_append_step_summary_write_failure_only_logs_a_warning(tmp_path, monkeypatch, caplog):
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "missing" / "summary.md"))
    with caplog.at_level(logging.WARNING, logger=run_scrape.logger.name):
        append_step_summary("text\n")
    assert "Could not append the run summary to GITHUB_STEP_SUMMARY" in caplog.text
    assert not (tmp_path / "missing").exists()


def test_ops_main_dry_run_reports_live_seed_counts_and_appends_the_step_summary(tmp_path, monkeypatch, capsys, caplog):
    summary_file = tmp_path / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
    caplog.set_level(logging.INFO, logger=run_scrape.logger.name)
    scrapers = {
        "Live Utility": OPS__summary_scraper([
            OPS__summary_record("Live Utility", OPS_SUMMARY_LIVE_NOTE),
            OPS__summary_record("Live Utility", OPS_SUMMARY_VERIFIED_NOTE, name="Commercial"),
            OPS__summary_record("Live Utility", OPS_SUMMARY_SEED_NOTE, name="Street Lighting"),
            OPS__summary_record("Live Utility", OPS_SUMMARY_LIVE_NOTE, name="Broken Class", components=False),
        ]),
        "Seed Utility": OPS__summary_scraper([
            OPS__summary_record("Seed Utility", OPS_SUMMARY_SEED_NOTE),
            OPS__summary_record("Seed Utility", OPS_SUMMARY_SEED_NOTE, name="Commercial"),
        ]),
        "Broken Utility": SimpleNamespace(scrape=OPS__summary_failing_scrape),
        "Unconfigured Utility": None,
    }
    OPS__summary_run_main(monkeypatch, tmp_path, scrapers, ["--dry-run"])

    lines = capsys.readouterr().out.splitlines()
    total = lines.index("  Total tariffs scraped: 5")
    assert lines[total - 1] == "  Scrape complete: 2/4 utilities succeeded"
    assert lines[total + 1:total + 4] == [
        "  Live records: 2 | Seed (estimated) records: 3",
        "  Seed-only utilities (1): Seed Utility",
        "  Errors: 3",
    ]
    assert not any("no valid records" in line for line in lines)
    assert {"    - Live Utility: 1 invalid records", "    - Broken Utility: source unavailable",
            "    - Unconfigured Utility: no scraper configured"} <= set(lines)
    assert "  (dry run — nothing saved to database)" in lines

    assert "Live Utility: 2 live, 1 seed, 1 invalid" in caplog.messages
    seed_logs = [r for r in caplog.records if r.getMessage() == "Seed Utility: 0 live, 2 seed, 0 invalid"]
    assert [r.levelno for r in seed_logs] == [logging.WARNING]

    markdown = summary_file.read_text(encoding="utf-8")
    assert "_Dry run: nothing saved to the database._" in markdown
    assert "- Live records: 2; seed (estimated) records: 3; invalid records: 1" in markdown
    assert "- Utilities: 4; failed: 2; no valid records: 0; seed only: 1" in markdown
    assert [line for line in markdown.splitlines() if line.startswith("| ") and "---" not in line] == [
        "| Utility | Live | Seed | Invalid | Status |",
        "| Broken Utility | 0 | 0 | 0 | failed: source unavailable |",
        "| Unconfigured Utility | 0 | 0 | 0 | failed: no scraper configured |",
        "| Seed Utility | 0 | 2 | 0 | seed only |",
        "| Live Utility | 2 | 1 | 1 | live + seed |",
    ]
    assert not (tmp_path / "rates.db").exists()


def test_ops_main_all_live_run_keeps_the_existing_box_and_survives_an_unwritable_summary(tmp_path, monkeypatch, capsys,
                                                                                      caplog):
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "missing" / "summary.md"))
    scrapers = {"Live Utility": OPS__summary_scraper([OPS__summary_record("Live Utility", OPS_SUMMARY_LIVE_NOTE)])}
    with caplog.at_level(logging.WARNING, logger=run_scrape.logger.name):
        OPS__summary_run_main(monkeypatch, tmp_path, scrapers, ["--dry-run", "--utility", "live utility"])

    assert capsys.readouterr().out.splitlines()[-6:] == [
        "=" * 60,
        "  Scrape complete: 1/1 utilities succeeded",
        "  Total tariffs scraped: 1",
        "  Live records: 1 | Seed (estimated) records: 0",
        "  (dry run — nothing saved to database)",
        "=" * 60,
    ]
    assert "Could not append the run summary to GITHUB_STEP_SUMMARY" in caplog.text
    assert list(tmp_path.iterdir()) == []


# ======================================================================
# Representative models 7A crosswalk and usage levels (batch 12)
# ======================================================================
from pipeline.representative_models import DEMAND_BOUNDS as RM7A_DEMAND_BOUNDS, bands_for_demand as RM7A_bands_for_demand, coverage_report as RM7A_coverage_report, latest_live_records as RM7A_latest_live_records, load_crosswalk as RM7A_load_crosswalk, load_rates as RM7A_load_rates, load_usage_levels as RM7A_load_usage_levels, main as RM7A_main, match_record as RM7A_match_record, model_keys as RM7A_model_keys, rule_matches as RM7A_rule_matches
import copy
import json
import re
from pathlib import Path


RM7A_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "rm_records_sample.json"
RM7A_B12_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "rm_records_b12.json"
RM7A_MODELS = Path(__file__).resolve().parents[1] / "data" / "models"
RM7A_CROSSWALK = RM7A_MODELS / "crosswalk.json"
RM7A_USAGE_LEVELS = RM7A_MODELS / "usage_levels.json"
RM7A_FIXTURE_FIELDS = {"utility_name", "province", "utility_type", "name", "tariff_code", "customer_class", "sub_class",
                  "demand_min_kw", "demand_max_kw", "rate_structure", "effective_date", "provenance", "eligibility"}
RM7A_RULE_KEYS = {"id", "utility", "province", "fuel", "match", "zone", "model", "exclude", "note"}
RM7A_MATCH_KEYS = {"tariff_code", "tariff_code_regex", "name_regex", "customer_class", "rate_structure"}
RM7A_GAS_BAND_RE = re.compile(r"annual_volume:\d+-\d*:(GJ|m3)")
SMALL, MEDIUM, LARGE, XLARGE = "commercial_small", "commercial_medium", "commercial_large", "commercial_xlarge"
RM7A_AB_ELECTRICITY = {"ENMAX Power", "ATCO Electric", "EPCOR Distribution", "FortisAlberta",
                  "Direct Energy Regulated Services", "ENMAX Energy Corporation", "EPCOR Energy Alberta"}
RM7A_ON_AB_GAS = {"Enbridge Gas", "EPCOR Natural Gas (Ontario)", "ATCO Gas"}


def RM7A__records():
    return RM7A_load_rates(RM7A_FIXTURE)


def RM7A__b12_records():
    return RM7A_load_rates(RM7A_B12_FIXTURE)


def RM7A__on(code, cls="residential", lo=None, hi=None, utility="PUC Distribution Inc.", name="Synthetic"):
    return {"utility_name": utility, "province": "ON", "utility_type": "electricity", "name": name,
            "tariff_code": code, "customer_class": cls, "demand_min_kw": lo, "demand_max_kw": hi,
            "provenance": "live", "effective_date": "2026-01-01"}


def RM7A__rule(rid, utility="*", code=None, regex=None, model=None, exclude=None, zone=None):
    match = {"tariff_code": code} if code is not None else {"tariff_code_regex": regex}
    return {"id": rid, "utility": utility, "province": "ON", "fuel": "electricity", "match": match, "zone": zone,
            "model": model, "exclude": exclude, "note": ""}


def test_rm7a_fixture_is_a_frozen_reduced_snapshot_of_latest_live_records():
    data = json.loads(RM7A_FIXTURE.read_text(encoding="utf-8"))
    records = data["records"]
    assert data["count"] == len(records) == 836
    assert all(set(r) == RM7A_FIXTURE_FIELDS for r in records)
    assert all(r["provenance"] == "live" for r in records)
    assert all(r["eligibility"] is None or len(r["eligibility"]) <= 200 for r in records)
    assert len(RM7A_latest_live_records(records)) == len(records)


def test_rm7a_every_sample_record_is_mapped_or_excluded():
    report = RM7A_coverage_report(RM7A__records(), RM7A_load_crosswalk(RM7A_CROSSWALK))
    assert report["unmapped"] == []
    totals = report["totals"]
    assert totals["mapped"] + totals["excluded"] == totals["records"] == 836
    assert all(u["unmapped"] == 0 for u in report["by_utility"].values())


def test_rm7a_report_surfaces_every_conflicting_multi_rule_match_and_first_rule_wins():
    crosswalk = RM7A_load_crosswalk(RM7A_CROSSWALK)
    rules = crosswalk["rules"]
    expected = {}
    for record in RM7A__records():
        hits = [r for r in rules if RM7A_rule_matches(r, record)]
        outcomes = {json.dumps([r["model"], r["exclude"], r["zone"] or ("default" if r["model"] else None)],
                               sort_keys=True) for r in hits}
        if len(outcomes) > 1:
            expected[(record["utility_name"], record["tariff_code"], record["name"])] = hits[0]["id"]
    report = RM7A_coverage_report(RM7A__records(), crosswalk)
    surfaced = {(c["utility_name"], c["tariff_code"], c["name"]): c["winning_rule"] for c in report["conflicts"]}
    assert surfaced == expected
    specific = {r["id"] for r in rules if r["utility"] != "*"}
    assert set(surfaced.values()) <= specific | {"on-res-seasonal"}


def test_rm7a_all_46_ontario_default_rpp_records_map_to_residential_structures():
    crosswalk = RM7A_load_crosswalk(RM7A_CROSSWALK)
    records = [r for r in RM7A__records() if r["province"] == "ON"]
    assert len({r["utility_name"] for r in records}) == 46
    for code, structure in (("TOU-R", "tou"), ("TIER-R", "tiered"), ("ULO-R", "ulo")):
        hits = [r for r in records if r["tariff_code"] == code]
        assert len({r["utility_name"] for r in hits}) == len(hits) == 46
        for record in hits:
            outcome = RM7A_match_record(record, crosswalk)
            assert outcome["model"] == {"province": "ON", "fuel": "electricity", "sector": "residential",
                                        "structure": structure, "size_band": None}, record["utility_name"]
            assert outcome["zone"] == "default"


def test_rm7a_territorial_records_are_excluded_for_later_models():
    crosswalk = RM7A_load_crosswalk(RM7A_CROSSWALK)
    territorial = [r for r in RM7A__records() if r["province"] in ("YT", "NT", "NU")]
    assert len(territorial) == 109
    for record in territorial:
        outcome = RM7A_match_record(record, crosswalk)
        assert outcome["model"] is None and outcome["exclude"] == "territory_planned_later"


def test_rm7a_first_matching_rule_wins():
    specific = RM7A__rule("specific", utility="Algoma Power Inc.", code="TOU-R", exclude="pilot")
    generic = RM7A__rule("generic", code="TOU-R", model={"sector": "residential", "structure": "tou", "size_band": None})
    crosswalk = {"rules": [specific, generic]}
    assert RM7A_match_record(RM7A__on("TOU-R", utility="Algoma Power Inc."), crosswalk)["rule_id"] == "specific"
    assert RM7A_match_record(RM7A__on("TOU-R"), crosswalk)["rule_id"] == "generic"
    assert RM7A_match_record(RM7A__on("TOU-R", utility="Algoma Power Inc."), {"rules": [generic, specific]})["rule_id"] == "generic"


def test_rm7a_regexes_match_the_whole_string_only():
    loose = RM7A__rule("loose", regex="TOU-R", model={"sector": "residential", "structure": "tou", "size_band": None})
    crosswalk = {"rules": [loose]}
    assert RM7A_match_record(RM7A__on("TOU-R"), crosswalk)["rule_id"] == "loose"
    for code in ("XTOU-R", "TOU-R-BRAMPTON", "TOU-RX", None):
        assert RM7A_match_record(RM7A__on(code), crosswalk)["rule_id"] is None
    real = RM7A_load_crosswalk(RM7A_CROSSWALK)
    for code in ("XTOU-R", "TOU-R-", "tou-r", "GS 50-4,999 kWh", "LU "):
        assert RM7A_match_record(RM7A__on(code, cls="residential" if "R" in (code or "") else "commercial"), real)["rule_id"] is None
    for rule in real["rules"]:
        for key in ("tariff_code_regex", "name_regex"):
            if key in rule["match"]:
                assert rule["match"][key].startswith("^") and rule["match"][key].endswith("$"), rule["id"]


def test_rm7a_ontario_zone_tagging_and_new_distributors_need_no_new_rules():
    crosswalk = RM7A_load_crosswalk(RM7A_CROSSWALK)
    cases = [
        (RM7A__on("TOU-R"), "default", ("residential", "tou", None)),
        (RM7A__on("ULO-R-SAULT-STE-MARIE"), "other", ("residential", "ulo", None)),
        (RM7A__on("GS-TIER-S", cls="commercial", hi=50), "default", ("commercial", "tiered", [SMALL])),
        (RM7A__on("GS-TOU-S-ZONE", cls="commercial", hi=50), "other", ("commercial", "tou", [SMALL])),
        (RM7A__on("GS 50-4,999 kW", cls="commercial", lo=50, hi=5000), "default", ("commercial", "demand", [MEDIUM, LARGE])),
        (RM7A__on("GS 50-4,999 kW-ZONE", cls="commercial", lo=50, hi=5000), "other", ("commercial", "demand", [MEDIUM, LARGE])),
        (RM7A__on("LU", cls="industrial", lo=5000), "default", ("commercial", "demand", [XLARGE])),
        (RM7A__on("LU-ZONE", cls="industrial", lo=5000), "other", ("commercial", "demand", [XLARGE])),
        (RM7A__on("GSd", cls="commercial", lo=50, utility="Hydro One Networks Inc."), "default",
         ("commercial", "demand", [MEDIUM, LARGE, XLARGE])),
        (RM7A__on("UGd", cls="commercial", lo=50, utility="Hydro One Networks Inc."), "other",
         ("commercial", "demand", [MEDIUM, LARGE, XLARGE])),
        (RM7A__on("TOU-R-R2", utility="Hydro One Networks Inc."), "other", ("residential", "tou", None)),
    ]
    for record, zone, (sector, structure, bands) in cases:
        outcome = RM7A_match_record(record, crosswalk)
        assert outcome["zone"] == zone, record["tariff_code"]
        model = outcome["model"]
        assert (model["sector"], model["structure"], model["size_band"]) == (sector, structure, bands)
    assert RM7A_match_record(RM7A__on("TOU-R-SEASONAL"), crosswalk)["exclude"] == "seasonal_property"
    assert RM7A_match_record(RM7A__on("TIER-R-VERIDIAN-SEASONAL"), crosswalk)["exclude"] == "seasonal_property"


def test_rm7a_reviewed_ontario_judgement_mappings():
    crosswalk = RM7A_load_crosswalk(RM7A_CROSSWALK)
    by_code = {(r["utility_name"], r["tariff_code"]): RM7A_match_record(r, crosswalk) for r in RM7A__records()}
    assert by_code[("Hydro One Networks Inc.", "TOU-R")]["rule_id"] == "on-hydroone-tou-r-r1-default"
    assert by_code[("Hydro One Networks Inc.", "ST")]["exclude"] == "supply_voltage_alternative"
    assert by_code[("Algoma Power Inc.", "R2 50+ kW")]["exclude"] == "residential_large_demand"
    assert by_code[("Algoma Power Inc.", "TOU-R-R1-II-O-REG-445-07")]["exclude"] == "duplicate_variant"
    assert by_code[("Toronto Hydro-Electric System Ltd.", "TOU-R-COMPETITIVE-SECTOR-MULTI-UNIT-RESIDENTIAL")][
        "exclude"] == "duplicate_variant"
    assert by_code[("Bluewater Power Distribution", "GS 50-999 kW")]["model"]["size_band"] == [MEDIUM]
    assert by_code[("Bluewater Power Distribution", "GS 1,000-4,999 kW")]["model"]["size_band"] == [LARGE]
    assert by_code[("Enwin Utilities Ltd.", "LARGE-USE-REGULAR")]["model"]["size_band"] == [XLARGE]


def test_rm7a_demand_bounds_resolve_to_size_bands():
    crosswalk = RM7A_load_crosswalk(RM7A_CROSSWALK)
    cases = [((None, 50), [SMALL]), ((50, 5000), [MEDIUM, LARGE]), ((50, 1000), [MEDIUM]), ((50, 500), [MEDIUM]),
             ((1000, 5000), [LARGE]), ((500, 1500), [LARGE]), ((3000, 5000), [LARGE]), ((1500, 4999), [LARGE]),
             ((5000, None), [XLARGE]), ((3000, None), [XLARGE]), ((50, None), [MEDIUM, LARGE, XLARGE]),
             ((1000, None), [LARGE, XLARGE])]
    for (lo, hi), bands in cases:
        assert RM7A_bands_for_demand(lo, hi, crosswalk) == bands, (lo, hi)
    record = RM7A__on("GS 50-999 kW", cls="commercial", lo=50, hi=1000)
    rule = RM7A__rule("r", regex=r"^GS .+$", model={"sector": "commercial", "structure": "demand", "size_band": RM7A_DEMAND_BOUNDS})
    assert RM7A_match_record(record, {**crosswalk, "rules": [rule]})["model"]["size_band"] == [MEDIUM]


def test_rm7a_usage_levels_hold_the_approved_values():
    levels = RM7A_load_usage_levels(RM7A_USAGE_LEVELS)
    assert levels["version"] == 1
    assert levels["days_per_month"] == 30.4375
    assert levels["power_factor_for_kva"] == 0.9
    assert levels["electricity"] == {
        "residential": [{"id": "low", "kwh": 500}, {"id": "typical", "kwh": 1000}, {"id": "high", "kwh": 2000}],
        "commercial_small": [{"id": "s1", "kwh": 2000, "kw": 10}, {"id": "s2", "kwh": 8000, "kw": 25}],
        "commercial_medium": [{"id": "m1", "kwh": 40000, "kw": 100}],
        "commercial_large": [{"id": "l1", "kwh": 500000, "kw": 1000}],
        "commercial_xlarge": [],
    }
    assert "Phase 7D" in levels["gas"]["note"]
    shares = levels["tou_shares"]
    assert shares["ON_RPP_TOU"]["shares"] == {"off-peak": 0.64, "mid-peak": 0.18, "on-peak": 0.18}
    assert shares["ON_RPP_ULO"]["shares"] == {"ultra-low-overnight": 0.40, "off-peak": 0.20, "mid-peak": 0.27,
                                              "on-peak": 0.13}
    for key, entry in shares.items():
        if isinstance(entry, dict) and entry["shares"] is not None:
            assert abs(sum(entry["shares"].values()) - 1.0) < 1e-9, key
            assert entry["source"]["url"].startswith("https://www.oeb.ca/")
    season = levels["seasons"]["ON_RPP"]
    assert (season["winter"]["residential_tier_threshold_kwh"], season["summer"]["residential_tier_threshold_kwh"]) == (
        1000, 600)
    assert season["winter"]["non_residential_tier_threshold_kwh"] == season["summer"][
        "non_residential_tier_threshold_kwh"] == 750
    assert sorted(season["winter"]["months"] + season["summer"]["months"]) == list(range(1, 13))
    assert levels["basis"]


def test_rm7a_size_band_reference_loads_match_usage_levels():
    bands = RM7A_load_crosswalk(RM7A_CROSSWALK)["vocabulary"]["size_bands"]
    electricity = RM7A_load_usage_levels(RM7A_USAGE_LEVELS)["electricity"]
    assert list(bands) == [SMALL, MEDIUM, LARGE, XLARGE]
    for band in (SMALL, MEDIUM, LARGE):
        assert sorted(bands[band]["reference_kw"]) == sorted(level["kw"] for level in electricity[band])
        assert all(bands[band]["min_kw"] <= kw < bands[band]["max_kw"] for kw in bands[band]["reference_kw"])
    assert electricity[XLARGE] == [] and bands[XLARGE]["max_kw"] is None


def test_rm7a_crosswalk_rules_follow_the_schema():
    crosswalk = RM7A_load_crosswalk(RM7A_CROSSWALK)
    vocab = crosswalk["vocabulary"]
    rules = crosswalk["rules"]
    ids = [r["id"] for r in rules]
    assert len(ids) == len(set(ids))
    for rule in rules:
        assert set(rule) == RM7A_RULE_KEYS, rule["id"]
        assert (rule["model"] is None) != (rule["exclude"] is None), rule["id"]
        assert set(rule["match"]) <= RM7A_MATCH_KEYS and rule["fuel"] in ("electricity", "gas", None)
        assert rule["zone"] in ("default", "other", None) and rule["note"] is not None
        for key in ("tariff_code_regex", "name_regex"):
            if key in rule["match"]:
                re.compile(rule["match"][key])
        if rule["exclude"]:
            assert rule["exclude"] in vocab["exclusions"], rule["id"]
            continue
        model = rule["model"]
        assert model["sector"] in vocab["sectors"] and model["structure"] in vocab["structures"], rule["id"]
        band = model["size_band"]
        if model["sector"] == "residential":
            assert band is None, rule["id"]
        elif band != RM7A_DEMAND_BOUNDS and band is not None:
            assert all(b in vocab["size_bands"] or RM7A_GAS_BAND_RE.fullmatch(b) for b in band), rule["id"]
    for province in {r["province"] for r in rules}:
        order = [i for i, r in enumerate(rules) if r["province"] == province]
        specific = [i for i in order if rules[i]["utility"] != "*"]
        generic = [i for i in order if rules[i]["utility"] == "*"]
        assert not specific or not generic or max(specific) < min(generic), province


def test_rm7a_latest_live_records_follow_the_site_dedupe():
    base = {"utility_name": "U", "name": "N", "customer_class": "residential"}
    old_live = {**base, "effective_date": "2025-01-01", "provenance": "live", "tag": "old"}
    new_live = {**base, "effective_date": "2026-01-01", "provenance": "live", "tag": "new"}
    new_seed = {**base, "effective_date": "2027-01-01", "provenance": "seed"}
    other_class = {**base, "customer_class": "commercial", "effective_date": "2020-01-01", "provenance": "live"}
    assert [r["tag"] for r in RM7A_latest_live_records([old_live, new_live])] == ["new"]
    assert RM7A_latest_live_records([old_live, new_live, new_seed]) == []
    assert len(RM7A_latest_live_records([new_live, other_class])) == 2
    tie = {**new_live, "tag": "tie"}
    assert [r["tag"] for r in RM7A_latest_live_records([new_live, tie])] == ["new"]


def test_rm7a_match_record_never_raises():
    crosswalk = RM7A_load_crosswalk(RM7A_CROSSWALK)
    unmapped = {"rule_id": None, "model": None, "exclude": None, "zone": None}
    assert RM7A_match_record({}, crosswalk) == unmapped
    assert RM7A_match_record({"tariff_code": None, "name": None, "province": None}, crosswalk) == unmapped
    assert RM7A_match_record(None, crosswalk) == unmapped
    assert RM7A_match_record(RM7A__on("TOU-R"), {}) == unmapped
    bad = {"rules": [RM7A__rule("bad-regex", regex="(", exclude="pilot"),
                     {"id": "bad-key", "utility": "*", "match": {"tarif_code": "TOU-R"}, "exclude": "pilot"},
                     {"id": "bad-match", "utility": "*", "match": ["TOU-R"], "exclude": "pilot"}]}
    assert RM7A_match_record(RM7A__on("TOU-R"), bad) == unmapped


def test_rm7a_model_keys_expand_size_band_lists():
    crosswalk = RM7A_load_crosswalk(RM7A_CROSSWALK)
    rate_m = next(r for r in RM7A__records() if r["utility_name"] == "Hydro-Québec" and r["tariff_code"] == "M")
    assert RM7A_model_keys(RM7A_match_record(rate_m, crosswalk)) == [
        ("QC", "electricity", "commercial", "demand", MEDIUM), ("QC", "electricity", "commercial", "demand", LARGE)]
    assert RM7A_model_keys(RM7A_match_record(RM7A__on("TOU-R"), crosswalk)) == [("ON", "electricity", "residential", "tou", None)]
    assert RM7A_model_keys(RM7A_match_record(RM7A__on("TOU-R-SEASONAL"), crosswalk)) == []


def test_rm7a_new_utilities_are_unmapped_until_a_rule_is_appended():
    crosswalk = copy.deepcopy(RM7A_load_crosswalk(RM7A_CROSSWALK))
    record = {"utility_name": "Apex Utilities", "province": "AB", "utility_type": "gas", "name": "Rate 1",
              "tariff_code": "1", "customer_class": "residential", "provenance": "live", "effective_date": "2026-10-01"}
    assert RM7A_coverage_report([record], crosswalk)["unmapped"] == [
        {"utility_name": "Apex Utilities", "province": "AB", "tariff_code": "1", "name": "Rate 1",
         "customer_class": "residential"}]
    first_territory = next(i for i, r in enumerate(crosswalk["rules"]) if r["id"].startswith("territory-"))
    crosswalk["rules"].insert(first_territory, {
        "id": "ab-apex-utilities", "utility": "Apex Utilities", "province": "AB", "fuel": "gas", "match": {},
        "zone": None, "model": None, "exclude": "gas_models_phase_7d", "note": ""})
    assert RM7A_match_record(record, crosswalk)["rule_id"] == "ab-apex-utilities"


def test_rm7a_batch12_fixture_is_a_frozen_reduced_snapshot():
    data = json.loads(RM7A_B12_FIXTURE.read_text(encoding="utf-8"))
    records = data["records"]
    assert data["count"] == len(records) == 75 and set(data["fields"]) == RM7A_FIXTURE_FIELDS
    assert all(set(r) == RM7A_FIXTURE_FIELDS and r["provenance"] == "live" for r in records)
    assert len(RM7A_latest_live_records(records)) == len(records)
    utilities = {r["utility_name"] for r in records}
    assert utilities == RM7A_AB_ELECTRICITY | RM7A_ON_AB_GAS | {"PUC Distribution Inc."}


def test_rm7a_batch12_alberta_and_gas_records_are_excluded_with_reasons():
    crosswalk = RM7A_load_crosswalk(RM7A_CROSSWALK)
    seen = set()
    for record in RM7A__b12_records():
        outcome = RM7A_match_record(record, crosswalk)
        name = record["utility_name"]
        if name in RM7A_AB_ELECTRICITY:
            assert record["province"] == "AB" and record["utility_type"] == "electricity"
            assert (outcome["model"], outcome["exclude"]) == (None, "province_not_modelled_yet_7c"), record["name"]
        elif name in RM7A_ON_AB_GAS:
            assert record["utility_type"] == "gas"
            assert (outcome["model"], outcome["exclude"]) == (None, "gas_models_phase_7d"), record["name"]
        else:
            continue
        assert outcome["rule_id"].startswith(("ab-", "on-")) and outcome["zone"] is None
        seen.add(name)
    assert seen == RM7A_AB_ELECTRICITY | RM7A_ON_AB_GAS
    vocabulary = crosswalk["vocabulary"]["exclusions"]
    assert "Phase 7C" in vocabulary["province_not_modelled_yet_7c"]
    assert "Phase 7D" in vocabulary["gas_models_phase_7d"]


def test_rm7a_puc_distribution_maps_through_the_generic_ontario_rules():
    crosswalk = RM7A_load_crosswalk(RM7A_CROSSWALK)
    puc = {r["tariff_code"]: RM7A_match_record(r, crosswalk) for r in RM7A__b12_records()
           if r["utility_name"] == "PUC Distribution Inc."}
    expected = {"TOU-R": ("residential", "tou", None), "TIER-R": ("residential", "tiered", None),
                "ULO-R": ("residential", "ulo", None), "GS-TOU-S": ("commercial", "tou", [SMALL]),
                "GS-TIER-S": ("commercial", "tiered", [SMALL]), "GS-ULO-S": ("commercial", "ulo", [SMALL]),
                "GS 50-4,999 kW": ("commercial", "demand", [MEDIUM, LARGE])}
    assert set(puc) == set(expected)
    for code, (sector, structure, bands) in expected.items():
        outcome = puc[code]
        model = outcome["model"]
        assert (model["sector"], model["structure"], model["size_band"]) == (sector, structure, bands), code
        assert outcome["zone"] == "default" and outcome["rule_id"].startswith("on-") and "puc" not in outcome["rule_id"]


def test_rm7a_frozen_samples_together_leave_nothing_unmapped():
    crosswalk = RM7A_load_crosswalk(RM7A_CROSSWALK)
    report = RM7A_coverage_report(RM7A__records() + RM7A__b12_records(), crosswalk)
    assert report["unmapped"] == [] and report["unused_rules"] == []
    assert report["totals"]["records"] == 910 and report["totals"]["utilities"] == 77
    assert report["by_province"]["AB"] == {"excluded": 38}
    assert report["exclusions"]["province_not_modelled_yet_7c"] == 28
    assert report["exclusions"]["gas_models_phase_7d"] == 40
    assert all(key.split("|")[0] != "AB" for key in report["model_keys"])


def test_rm7a_cli_prints_coverage_for_the_fixture(capsys):
    assert RM7A_main(["--coverage", "--rates", str(RM7A_FIXTURE), "--crosswalk", str(RM7A_CROSSWALK)]) == 0
    out = capsys.readouterr().out
    assert "unmapped 0" in out and "ON|electricity|residential|tou|-" in out


# ======================================================================
# Representative models 7B engine, reference customer and export hook (batch 12)
# ======================================================================
from pipeline.representative_models import _note_body as RM7B__note_body, apply_tax_lines as RM7B_apply_tax_lines, build_models as RM7B_build_models, closest_to_median as RM7B_closest_to_median, component_exclusion as RM7B_component_exclusion, find_outliers as RM7B_find_outliers, load_crosswalk as RM7B_load_crosswalk, load_taxes as RM7B_load_taxes, load_usage_levels as RM7B_load_usage_levels, main as RM7B_main, months_from_text as RM7B_months_from_text, record_covers_level as RM7B_record_covers_level, record_monthly_cost as RM7B_record_monthly_cost, reference_customer_entries as RM7B_reference_customer_entries, reference_customer_match as RM7B_reference_customer_match, summary_stats as RM7B_summary_stats, tax_lines as RM7B_tax_lines
import copy
import json
import logging
import re
from pathlib import Path

import pytest


RM7B_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "rm_engine_sample.json"
RM7B_ROOT = Path(__file__).resolve().parents[1]
RM7B_AS_OF = "2026-10-09"
RM7B_DPM = 365.25 / 12
RM7B_RES_TOU = "ON|electricity|residential|tou|-"
RM7B_RES_TIER = "ON|electricity|residential|tiered|-"
RM7B_RES_ULO = "ON|electricity|residential|ulo|-"
RM7B_SMALL_TOU = "ON|electricity|commercial|tou|commercial_small"
RM7B_MEDIUM = "ON|electricity|commercial|demand|commercial_medium"
RM7B_LARGE = "ON|electricity|commercial|demand|commercial_large"
RM7B_XLARGE = "ON|electricity|commercial|demand|commercial_xlarge"
RM7B_STATES = {"modeled", "single_source", "market_energy_pending", "not_computable"}
RM7B_MARKET_NOTE = ("Provenance: live_parsed. The hourly Ontario Electricity Market Price replaced the HOEP on May 1, 2025. "
               "Conditional: Class A customers instead pay Global Adjustment by their peak demand factor.")
RM7B_SECTORS = ("residential", "commercial_small", "commercial_medium", "commercial_large", "commercial_xlarge")
RM7B_DEMAND_SECTORS = ("commercial_medium", "commercial_large", "commercial_xlarge")
CBR, GA, NON_WMP, SSS = "on-class-b-cbr", "on-non-rpp-class-b-ga", "on-non-wmp-riders", "on-sss-admin"


def RM7B__fx():
    return json.loads(RM7B_FIXTURE.read_text(encoding="utf-8"))


def RM7B__ul():
    return RM7B__fx()["usage_levels"]


def RM7B__strict_ul():
    return {k: v for k, v in RM7B__ul().items() if k != "reference_customer"}


def RM7B__c(ctype, value, unit, name=None, **extra):
    comp = {"component_type": ctype, "component_name": name or f"{ctype} {unit}", "charge_value": value,
            "charge_unit": unit, "notes": "Provenance: live_parsed. "}
    comp.update(extra)
    return comp


def RM7B__tou(off=0.098, mid=0.157, on=0.203):
    return [RM7B__c("energy", off, "$/kWh", "Off-Peak Energy", tou_period="off-peak"),
            RM7B__c("energy", mid, "$/kWh", "Mid-Peak Energy", tou_period="mid-peak"),
            RM7B__c("energy", on, "$/kWh", "On-Peak Energy", tou_period="on-peak")]


def RM7B__rec(components, utility="Synthetic Hydro", code="TOU-R", cls="residential", structure="tou", lo=None, hi=None,
         rid=1, province="ON"):
    return {"id": rid, "utility_name": utility, "province": province, "utility_type": "electricity",
            "name": f"{utility} {code}", "tariff_code": code, "customer_class": cls, "rate_structure": structure,
            "demand_min_kw": lo, "demand_max_kw": hi, "effective_date": "2026-01-01", "provenance": "live",
            "source_url": "https://example.org/tariff.pdf", "components": components}


def RM7B__cost(record, kwh, kw=None, sector="residential", structure="tou"):
    return RM7B_record_monthly_cost(record, kwh, kw, sector=sector, structure=structure, usage_levels=RM7B__ul(), as_of=RM7B_AS_OF)


def RM7B__build(records, zone_policy="median_of_zones", fixture=None):
    fx = fixture or RM7B__fx()
    return RM7B_build_models(records, fx["crosswalk"], fx["usage_levels"], fx["taxes"], as_of=RM7B_AS_OF, zone_policy=zone_policy)


def RM7B__model(result, model_id):
    return next(m for m in result["models"] if m["id"] == model_id)


def RM7B__level(model, level_id):
    return next(lv for lv in model["levels"] if lv["id"] == level_id)


def RM7B__seasonal_tiers(threshold_winter=1000.0, threshold_summer=600.0):
    comps = []
    for season, text, threshold in (("winter", "November 1 - April 30", threshold_winter),
                                    ("summer", "May 1 - October 31", threshold_summer)):
        for tier, price in ((1, 0.12), (2, 0.142)):
            comps.append(RM7B__c("energy", price, "$/kWh", f"Tier {tier} Energy ({season})", tier_number=tier,
                            tier_threshold=threshold, tier_unit="kWh/month", season=season, season_months=text))
    return comps


def test_rm7b_fixed_charges_convert_daily_30_day_and_yearly_units_to_months():
    rec = RM7B__rec([RM7B__c("fixed", 10.0, "$/month"), RM7B__c("fixed", 1.0, "$/day"), RM7B__c("fixed", 30.0, "$/30 days"),
                RM7B__c("rider", 120.0, "$/year")], structure="flat")
    res = RM7B__cost(rec, 0, structure="flat")
    assert res["status"] == "ok" and res["energy_status"] == "absent"
    assert res["cost"] == pytest.approx(10 + RM7B_DPM + 30 * RM7B_DPM / 30 + 10)


def test_rm7b_demand_units_kw_kva_per_day_and_per_30_days():
    comps = [RM7B__c("demand", 2.0, "$/kW"), RM7B__c("demand", 0.9, "$/kVA"), RM7B__c("demand", 0.1, "$/kW/day"),
             RM7B__c("transmission", 3.0, "$/kW", notes="Provenance: live_parsed. Published per 30 days"),
             RM7B__c("rider", 1.0, "$/kVA/month")]
    rec = RM7B__rec(comps, code="GS 50-999 kW", cls="commercial", structure="demand", lo=50, hi=1000)
    res = RM7B__cost(rec, 40000, 100, sector="commercial_medium", structure="demand")
    assert res["status"] == "ok"
    assert res["cost"] == pytest.approx(200 + 0.9 * 100 / 0.9 + 0.1 * RM7B_DPM * 100 + 3 * 100 * RM7B_DPM / 30 + 100 / 0.9)
    conversions = {text for item in res["items"] for text in item.get("conversions") or []}
    assert "kVA = kW / 0.9" in conversions and "demand charge published per 30 days x 30.4375/30" in conversions


def test_rm7b_energy_per_mwh_and_per_kwh_scale_with_usage():
    rec = RM7B__rec([RM7B__c("energy", 50.0, "$/MWh"), RM7B__c("distribution", 0.01, "$/kWh")], structure="flat")
    assert RM7B__cost(rec, 2000, structure="flat")["cost"] == pytest.approx(100 + 20)


def test_rm7b_seasonal_tiers_use_each_seasons_threshold_and_month_weighting():
    rec = RM7B__rec(RM7B__seasonal_tiers(), code="TIER-R", structure="tiered")
    assert RM7B__cost(rec, 500, structure="tiered")["cost"] == pytest.approx(60.0)
    assert RM7B__cost(rec, 1000, structure="tiered")["cost"] == pytest.approx((6 * 120 + 6 * (72 + 56.8)) / 12)
    assert RM7B__cost(rec, 2000, structure="tiered")["cost"] == pytest.approx((6 * 262 + 6 * 270.8) / 12)


def test_rm7b_all_year_tier_threshold():
    comps = [RM7B__c("energy", 0.12, "$/kWh", "Tier 1", tier_number=1, tier_threshold=750.0, tier_unit="kWh/month"),
             RM7B__c("energy", 0.142, "$/kWh", "Tier 2", tier_number=2, tier_threshold=750.0, tier_unit="kWh/month")]
    rec = RM7B__rec(comps, code="GS-TIER-S", cls="commercial", structure="tiered", hi=50)
    assert RM7B__cost(rec, 2000, 10, sector="commercial_small", structure="tiered")["cost"] == pytest.approx(267.5)


def test_rm7b_ambiguous_tiers_and_partial_seasons_are_not_computable():
    bad_unit = RM7B__rec([RM7B__c("energy", 0.1, "$/kWh", "T1", tier_number=1, tier_threshold=100.0, tier_unit="kWh per kW"),
                     RM7B__c("energy", 0.2, "$/kWh", "T2", tier_number=2)], code="TIER-R", structure="tiered")
    assert "not supported" in " ".join(RM7B__cost(bad_unit, 1000, structure="tiered")["reasons"])
    winter_only = RM7B__rec(RM7B__seasonal_tiers()[:2], code="TIER-R", structure="tiered")
    assert "each month exactly once" in " ".join(RM7B__cost(winter_only, 1000, structure="tiered")["reasons"])


def test_rm7b_tou_and_ulo_energy_use_the_official_shares():
    assert RM7B__cost(RM7B__rec(RM7B__tou()), 1000)["cost"] == pytest.approx(1000 * (0.64 * 0.098 + 0.18 * 0.157 + 0.18 * 0.203))
    ulo = RM7B__tou(mid=0.157, on=0.391) + [RM7B__c("energy", 0.039, "$/kWh", "ULO", tou_period="ultra-low-overnight")]
    expected = 1000 * (0.4 * 0.039 + 0.2 * 0.098 + 0.27 * 0.157 + 0.13 * 0.391)
    assert RM7B__cost(RM7B__rec(ulo, code="ULO-R"), 1000, structure="ulo")["cost"] == pytest.approx(expected)


def test_rm7b_tou_without_an_official_share_set_or_with_missing_periods_is_not_computable():
    bc = RM7B__cost(RM7B__rec(RM7B__tou(), province="BC"), 1000)
    assert bc["status"] == "not_computable" and "no official kWh share" in " ".join(bc["reasons"])
    partial = RM7B__cost(RM7B__rec(RM7B__tou()[:2]), 1000)
    assert "do not match the official share set" in " ".join(partial["reasons"])


def test_rm7b_conditional_alternative_optional_expired_future_and_percentage_components_are_excluded():
    comps = [
        RM7B__c("fixed", 10.0, "$/month", "Service Charge"),
        RM7B__c("regulatory", 0.0004, "$/kWh", "CBR", notes="Provenance: live_parsed. Conditional: Applies only to Class B customers"),
        RM7B__c("rebate", -60.5, "$/month", "RRRP credit", sub_component="conditional_credit",
           notes="Provenance: live_parsed. Conditional credit: qualifying year-round customers"),
        RM7B__c("transmission", 0.01, "$/kWh", "Network Service Rate"),
        RM7B__c("transmission", 0.002, "$/kWh", "Network Service Rate - EV CHARGING",
           notes="Provenance: live_parsed. Conditional: Optional Electric Vehicle Charging (EVC) Rate alternative"),
        RM7B__c("fixed", 5.0, "$/month", "Three Phase", notes="Provenance: live_parsed. Alternative: applies only to 'Three Phase' service."),
        RM7B__c("rider", 1.0, "$/month", "Optional rider", sub_component="optional"),
        RM7B__c("rider", 2.0, "$/month", "Expired rider", end_date="2026-06-30"),
        RM7B__c("rider", 3.0, "$/month", "Future rider", effective_date="2027-01-01"),
        RM7B__c("other", -1.0, "%", "Percentage adjustment"),
    ]
    res = RM7B__cost(RM7B__rec(comps, structure="flat"), 1000, structure="flat")
    assert res["status"] == "ok"
    # The Class B CBR charge is conditional but paid by the reference customer (reviewed list), so it is included.
    assert res["cost"] == pytest.approx(10 + 0.01 * 1000 + 0.0004 * 1000)
    reasons = {item["component"]: item.get("reason") for item in res["items"]}
    assert reasons == {"Service Charge": None, "CBR": "reference_customer:on-class-b-cbr", "RRRP credit": "conditional",
                       "Network Service Rate": None, "Network Service Rate - EV CHARGING": "alternative",
                       "Three Phase": "alternative", "Optional rider": "optional", "Expired rider": "expired",
                       "Future rider": "not_yet_effective", "Percentage adjustment": "percentage_base_not_computable"}
    strict = RM7B_record_monthly_cost(RM7B__rec(comps, structure="flat"), 1000, sector="residential", structure="flat",
                                 usage_levels=RM7B__strict_ul(), as_of=RM7B_AS_OF)
    assert strict["cost"] == pytest.approx(10 + 0.01 * 1000)
    assert {item["component"]: item.get("reason") for item in strict["items"]}["CBR"] == "conditional"


def test_rm7b_market_note_with_a_later_conditional_sentence_is_not_conditional():
    comp = RM7B__c("energy", None, "$/kWh", "Market Energy", market_reference="IESO OEMP + GA", notes=RM7B_MARKET_NOTE)
    assert RM7B_component_exclusion(comp, RM7B_AS_OF) == "market_pending"


def test_rm7b_charge_published_only_as_alternatives_makes_the_record_not_computable():
    alt = "Provenance: live_parsed. Conditional: Alternative distribution rate by meter type: applies only to {}"
    comps = [RM7B__c("fixed", 100.0, "$/month"),
             RM7B__c("demand", 5.9, "$/kW", "Thermal", sub_component="distribution_volumetric", notes=alt.format("thermal")),
             RM7B__c("demand", 6.1, "$/kW", "Interval", sub_component="distribution_volumetric", notes=alt.format("interval"))]
    rec = RM7B__rec(comps, code="GS 50-4,999 kW", cls="commercial", structure="demand", lo=50, hi=5000)
    res = RM7B__cost(rec, 40000, 100, sector="commercial_medium", structure="demand")
    assert res["status"] == "not_computable" and res["cost"] is None
    assert "only as conditional alternatives: Thermal; Interval" in " ".join(res["reasons"])


def test_rm7b_valueless_market_energy_prices_delivery_only_and_marks_the_model_pending():
    def demand(utility, rid, fixed):
        comps = [RM7B__c("fixed", fixed, "$/month"), RM7B__c("demand", 5.0, "$/kW", sub_component="distribution_volumetric"),
                 RM7B__c("energy", None, "$/kWh", "Market Energy", market_reference="IESO OEMP + GA", notes=RM7B_MARKET_NOTE)]
        return RM7B__rec(comps, utility=utility, code="GS 50-4,999 kW", cls="commercial", structure="demand", lo=50,
                    hi=5000, rid=rid)

    res = RM7B__cost(demand("A Hydro", 1, 100.0), 40000, 100, sector="commercial_medium", structure="demand")
    assert res["status"] == "ok" and res["energy_status"] == "market_pending"
    assert res["cost"] == pytest.approx(600.0) and res["market_pending"] == ["Market Energy"]
    model = RM7B__model(RM7B__build([demand("A Hydro", 1, 100.0), demand("B Hydro", 2, 300.0)]), RM7B_MEDIUM)
    assert model["state"] == "market_energy_pending"
    assert model["cost_basis"] == "delivery_only_market_energy_pending"
    assert RM7B__level(model, "m1")["without_tax"]["median"] == 700.0
    assert "market-priced energy is pending" in model["method"]


def test_rm7b_valueless_non_market_components_and_unsupported_units_are_not_computable():
    no_value = RM7B__cost(RM7B__rec([RM7B__c("fixed", 10.0, "$/month"), RM7B__c("rider", None, "$/month", "Unpriced")], structure="flat"),
                     1000, structure="flat")
    assert no_value["status"] == "not_computable" and "no published value: Unpriced" in " ".join(no_value["reasons"])
    odd = RM7B__cost(RM7B__rec([RM7B__c("fixed", 10.0, "$/two months", "Bimonthly")], structure="flat"), 1000, structure="flat")
    assert "unit not supported by the engine: Bimonthly" in " ".join(odd["reasons"])


def test_rm7b_demand_charges_need_a_level_with_kw():
    res = RM7B__cost(RM7B__rec([RM7B__c("demand", 5.0, "$/kW")], structure="flat"), 1000, None, structure="flat")
    assert res["status"] == "not_computable" and "no kW" in " ".join(res["reasons"])


def test_rm7b_months_from_season_texts():
    assert RM7B_months_from_text("12,1,2,3") == [12, 1, 2, 3]
    assert RM7B_months_from_text("Sep-Apr") == [9, 10, 11, 12, 1, 2, 3, 4]
    assert RM7B_months_from_text("November 1 - April 30") == [11, 12, 1, 2, 3, 4]
    assert RM7B_months_from_text("April 1 to November 1") == [4, 5, 6, 7, 8, 9, 10]
    assert RM7B_months_from_text("Four billing periods from the one commencing nearest November 1") is None
    assert RM7B_months_from_text(None) is None


def test_rm7b_record_covers_level_uses_half_open_demand_bounds_and_usage_bounds():
    gs = RM7B__rec([], code="GS 50-999 kW", cls="commercial", structure="demand", lo=50, hi=1000)
    assert RM7B_record_covers_level(gs, 40000, 100) and not RM7B_record_covers_level(gs, 500000, 1000)
    assert RM7B_record_covers_level(RM7B__rec([]), 1000, None)
    annual = dict(RM7B__rec([], structure="flat"), usage_max=32000, usage_unit="kWh/12 months")
    assert RM7B_record_covers_level(annual, 2000, None) and not RM7B_record_covers_level(annual, 3000, None)


def test_rm7b_ontario_rebate_applies_when_either_threshold_is_met():
    taxes = RM7B__fx()["taxes"]

    def names(kwh, kw, sector="commercial_small"):
        return [line["name"] for line in RM7B_tax_lines(taxes, "ON", "electricity", sector, kwh, kw, RM7B_AS_OF)[0]]

    oer = "Ontario Electricity Rebate (OER)"
    assert names(8000, 25) == ["HST", oer]
    assert names(20000, 100, "commercial_medium") == ["HST", oer]
    assert names(30000, 40, "commercial_medium") == ["HST", oer]
    assert names(1000, None, "residential") == ["HST", oer]
    applied, skipped = RM7B_tax_lines(taxes, "ON", "electricity", "commercial_medium", 40000, 100, RM7B_AS_OF)
    assert [line["name"] for line in applied] == ["HST"]
    assert skipped[0]["name"] == oer and "either test suffices" in skipped[0]["reason"]


def test_rm7b_hst_is_charged_on_the_pre_rebate_amount_and_lines_never_compound():
    applied, _ = RM7B_tax_lines(RM7B__fx()["taxes"], "ON", "electricity", "residential", 1000, None, RM7B_AS_OF)
    total, amounts = RM7B_apply_tax_lines(100.0, 60.0, applied)
    assert amounts == pytest.approx([13.0, 23.5]) and total == pytest.approx(89.5)
    lines = [{"name": "HST", "kind": "sales_tax", "rate": 0.15, "base": "pre_tax_subtotal"},
             {"name": "Energy rebate", "kind": "rebate", "rate": 0.10, "base": "energy_charge_subtotal"}]
    total, amounts = RM7B_apply_tax_lines(100.0, 60.0, lines)
    assert amounts == pytest.approx([15.0, 6.0]) and total == pytest.approx(109.0)


def test_rm7b_tax_lines_respect_dates_sectors_and_unknown_bases():
    line = {"name": "L", "kind": "sales_tax", "rate": 0.05, "base": "pre_tax_subtotal",
            "eligibility": {"sectors": ["residential"]}, "effective_date": "2008-01-01", "end_date": None}
    taxes = {"jurisdictions": {"XX": {"electricity": {"residential": [
        line, dict(line, name="Future", effective_date="2027-01-01"), dict(line, name="Ended", end_date="2026-06-30"),
        dict(line, name="Odd", base="gross_up")], "commercial": [line]}}}}
    applied, skipped = RM7B_tax_lines(taxes, "XX", "electricity", "residential", 1000, None, RM7B_AS_OF)
    assert [a["name"] for a in applied] == ["L"]
    assert {s["name"]: s["reason"].split()[0] for s in skipped} == {"Future": "not", "Ended": "ended", "Odd": "unsupported"}
    applied, skipped = RM7B_tax_lines(taxes, "XX", "electricity", "commercial_small", 1000, 10, RM7B_AS_OF)
    assert applied == [] and "not eligible" in skipped[0]["reason"]


def test_rm7b_summary_statistics_use_inclusive_quantiles():
    assert RM7B_summary_stats([4, 1, 3, 2]) == {"median": 2.5, "n": 4, "min": 1.0, "p25": 1.75, "p75": 3.25, "max": 4.0}
    assert RM7B_summary_stats([7]) == {"median": 7.0, "n": 1, "min": 7.0, "p25": 7.0, "p75": 7.0, "max": 7.0}
    assert RM7B_summary_stats([])["n"] == 0 and RM7B_summary_stats([])["median"] is None


def test_rm7b_outliers_by_percentage_or_iqr_with_signed_deviation():
    found = RM7B_find_outliers({"A": 100.0, "B": 102.0, "C": 104.0, "D": 106.0, "E": 140.0})
    assert [(o["utility"], o["deviation_pct"], o["rules"]) for o in found] == [
        ("E", 34.6, ["more_than_30pct_from_median", "outside_1.5_iqr"])]
    found = RM7B_find_outliers({"A": 100.0, "B": 101.0, "C": 102.0, "D": 103.0, "E": 120.0, "F": 60.0})
    assert [(o["utility"], o["deviation_pct"], o["rules"]) for o in found] == [
        ("F", -40.9, ["more_than_30pct_from_median", "outside_1.5_iqr"]), ("E", 18.2, ["outside_1.5_iqr"])]
    assert RM7B_find_outliers({"A": 1.0, "B": 100.0}) == []


def test_rm7b_closest_utility_ties_resolve_alphabetically():
    assert RM7B_closest_to_median({"Beta": 90.0, "Alpha": 110.0}, 100.0) == "Alpha"
    assert RM7B_closest_to_median({"Zed": 100.0, "Ann": 103.0, "Bob": 97.0}, 100.0) == "Zed"
    assert RM7B_closest_to_median({}, None) is None


def test_rm7b_zone_policies_on_a_synthetic_multi_zone_utility():
    def res(utility, code, fixed, rid):
        return RM7B__rec(RM7B__tou(0.1, 0.1, 0.1) + [RM7B__c("fixed", fixed, "$/month")], utility=utility, code=code, rid=rid)

    records = [res("X Hydro", "TOU-R", 100.0, 1), res("X Hydro", "TOU-R-NORTH", 200.0, 2),
               res("X Hydro", "TOU-R-SOUTH", 300.0, 3), res("Y Hydro", "TOU-R", 150.0, 4)]
    zones = RM7B__level(RM7B__model(RM7B__build(records), RM7B_RES_TOU), "typical")
    assert zones["without_tax"]["median"] == 275.0 and zones["closest_utility"]["utility"] == "X Hydro"
    assert next(r for r in zones["utilities"] if r["utility"] == "X Hydro")["records"] == [1, 2, 3]
    default = RM7B__model(RM7B__build(records, "default_only"), RM7B_RES_TOU)
    assert RM7B__level(default, "typical")["without_tax"]["median"] == 225.0
    skipped = [e["record_id"] for e in default["exclusions"] if e["scope"] == "record"]
    assert skipped == [2, 3]
    with pytest.raises(ValueError):
        RM7B__build(records, "every_zone")


def test_rm7b_single_source_state_and_method_text():
    model = RM7B__model(RM7B__build([RM7B__rec(RM7B__tou() + [RM7B__c("fixed", 30.0, "$/month")], utility="Only Hydro")]), RM7B_RES_TOU)
    assert model["state"] == "single_source" and model["provenance"] == "modeled"
    assert model["method"].startswith("Modeled comparison indicator, not a tariff anyone is billed. Single source: "
                                      "Only Hydro")
    assert RM7B__level(model, "typical")["outliers"] == []


def test_rm7b_fixture_is_a_frozen_ontario_sample_with_full_components():
    fx = RM7B__fx()
    records = fx["records"]
    assert fx["count"] == len(records) == 36 and fx["as_of"] == RM7B_AS_OF
    assert all(r["province"] == "ON" and r["provenance"] == "live" and r["components"] for r in records)
    assert len({r["id"] for r in records}) == len(records)
    assert {"crosswalk", "usage_levels", "taxes"} <= set(fx)


def test_rm7b_fixture_burlington_tou_typical_matches_a_hand_calculation():
    rec = next(r for r in RM7B__fx()["records"] if r["id"] == 2414)
    fixed = 36.74 + 0.42 + 0.05 + 0.5
    per_kwh = (0.0041 + 0.0015 + 0.0001 + 0.0124 + 0.0092) * 1000
    reference = 0.25 + (0.0004 + 0.0003) * 1000  # SSS administration; Class B CBR charge and CBR rider
    energy = 1000 * (0.64 * 0.098 + 0.18 * 0.157 + 0.18 * 0.203)
    res = RM7B__cost(rec, 1000)
    assert res["cost"] == pytest.approx(fixed + per_kwh + reference + energy) and round(res["cost"], 2) == 193.48
    strict = RM7B_record_monthly_cost(rec, 1000, sector="residential", structure="tou", usage_levels=RM7B__strict_ul(), as_of=RM7B_AS_OF)
    assert round(strict["cost"], 2) == 192.53
    model = RM7B__model(RM7B__build(RM7B__fx()), RM7B_RES_TOU)
    burlington = next(r for r in RM7B__level(model, "typical")["utilities"] if r["utility"] == "Burlington Hydro Inc.")
    assert burlington["cost_with_tax"] == round((fixed + per_kwh + reference + energy) * (1 + 0.13 - 0.235), 2)


def test_rm7b_fixture_exact_medians_median_of_zones():
    # Reference-customer charges (CBR, SSS, non-WMP; GA riders at m1/l1) raise every median; the 7B-1 values
    # were res TOU typical 196.84, GS<50 s2 1474.2, m1 1658.64 and l1 16368.3.
    result = RM7B__build(RM7B__fx())
    expected = {
        (RM7B_RES_TOU, "low"): (7, 118.28, 105.86, "Newmarket-Tay Power Distribution Ltd."),
        (RM7B_RES_TOU, "typical"): (7, 198.09, 177.29, "Newmarket-Tay Power Distribution Ltd."),
        (RM7B_RES_TOU, "high"): (7, 357.71, 320.15, "Newmarket-Tay Power Distribution Ltd."),
        (RM7B_RES_TIER, "typical"): (4, 196.95, 176.27, "Burlington Hydro Inc."),
        (RM7B_RES_ULO, "typical"): (4, 200.97, 179.87, "Burlington Hydro Inc."),
        (RM7B_SMALL_TOU, "s1"): (6, 396.94, 355.26, "Burlington Hydro Inc."),
        (RM7B_SMALL_TOU, "s2"): (6, 1481.26, 1325.72, "Burlington Hydro Inc."),
        (RM7B_MEDIUM, "m1"): (6, 1908.07, 2156.12, "Enova Power Corp."),
        (RM7B_LARGE, "l1"): (6, 18897.15, 21353.78, "Burlington Hydro Inc."),
    }
    for (model_id, level_id), (n, median, taxed, closest) in expected.items():
        level = RM7B__level(RM7B__model(result, model_id), level_id)
        got = (level["without_tax"]["n"], level["without_tax"]["median"], level["with_tax"]["median"],
               level["closest_utility"]["utility"])
        assert got == (n, median, taxed, closest), (model_id, level_id)
    hydro_one = next(r for r in RM7B__level(RM7B__model(result, RM7B_RES_TOU), "typical")["utilities"]
                     if r["utility"] == "Hydro One Networks Inc.")
    assert hydro_one["cost_without_tax"] == 222.55
    assert [z["cost_without_tax"] for z in hydro_one["zone_costs"]] == [222.55, 306.55, 194.29]


def test_rm7b_fixture_exact_medians_default_only():
    result = RM7B__build(RM7B__fx(), "default_only")
    typical = RM7B__level(RM7B__model(result, RM7B_RES_TOU), "typical")
    assert (typical["without_tax"]["n"], typical["without_tax"]["median"], typical["with_tax"]["median"]) == (7, 197.25, 176.54)
    medium = RM7B__level(RM7B__model(result, RM7B_MEDIUM), "m1")
    assert (medium["without_tax"]["n"], medium["without_tax"]["median"], medium["with_tax"]["median"]) == (5, 1862.23, 2104.32)
    large = RM7B__level(RM7B__model(result, RM7B_LARGE), "l1")
    assert (large["without_tax"]["n"], large["without_tax"]["median"]) == (5, 17982.86)
    assert "Newmarket-Tay Power Distribution Ltd." not in RM7B__model(result, RM7B_MEDIUM)["coverage"]["contributing_utilities"]


def test_rm7b_fixture_states_energy_basis_and_outliers():
    result = RM7B__build(RM7B__fx())
    assert result["version"] == 1 and result["method_version"] == "7B-2" and result["as_of"] == RM7B_AS_OF
    assert result["input"]["records_considered"] == 36 and result["input"]["rates_generated_at"] == "2026-10-08T15:23:54Z"
    for model in result["models"]:
        assert model["state"] in RM7B_STATES and model["provenance"] == "modeled"
    assert RM7B__model(result, RM7B_RES_TOU)["cost_basis"] == "delivery_and_energy"
    assert RM7B__model(result, RM7B_MEDIUM)["cost_basis"] == "delivery_only_no_energy_component"
    xlarge = RM7B__model(result, RM7B_XLARGE)
    assert xlarge["state"] == "single_source" and xlarge["levels"] == []
    outliers = RM7B__level(RM7B__model(result, RM7B_MEDIUM), "m1")["outliers"]
    assert [(o["utility"], o["deviation_pct"]) for o in outliers] == [
        ("Hydro One Networks Inc.", 76.0), ("Ottawa River Power Corporation", -46.2)]


def test_rm7b_fixture_alternative_only_record_is_listed_and_other_zone_is_used():
    model = RM7B__model(RM7B__build(RM7B__fx()), RM7B_MEDIUM)
    blocked = {e["record_id"]: e["reason"] for e in model["exclusions"] if e["scope"] == "record"}
    assert set(blocked) == {2454, 2469}
    assert "Thermal Demand Meter" in blocked[2454] and "Interval Metered (less than" in blocked[2469]
    row = next(r for r in RM7B__level(model, "m1")["utilities"] if r["utility"] == "Newmarket-Tay Power Distribution Ltd.")
    assert row["records"] == [2797]


def test_rm7b_fixture_toronto_kva_and_30_day_conversions():
    rec = next(r for r in RM7B__fx()["records"] if r["id"] == 2153)
    res = RM7B__cost(rec, 40000, 100, sector="commercial_medium", structure="demand")
    items = {i["component"]: i for i in res["items"]}
    volumetric = items["Distribution Volumetric Rate"]
    assert volumetric["amount"] == pytest.approx(10.517 * 100 / 0.9 * RM7B_DPM / 30)
    cbr_rider = next(i for name, i in items.items() if name.startswith("Rate Rider for Disposition of Capacity Based"))
    assert cbr_rider["reason"] == "reference_customer:on-class-b-cbr"
    assert cbr_rider["amount"] == pytest.approx(0.1892 * 100 / 0.9 * RM7B_DPM / 30)
    ga_rider = next(i for name, i in items.items() if name.startswith("Rate Rider for Disposition of Global Adjustment"))
    assert ga_rider["reason"] == "reference_customer:on-non-rpp-class-b-ga" and ga_rider["amount"] == pytest.approx(203.2)
    # 7B-1 (strict exclusion) was 2157.00; CBR, CBR rider, SSS, non-WMP and GA riders add 259.39.
    assert round(res["cost"], 2) == 2416.39


def test_rm7b_fixture_hydro_one_rrrp_credit_is_conditional_and_excluded():
    rec = next(r for r in RM7B__fx()["records"] if r["id"] == 2226)
    res = RM7B__cost(rec, 1000)
    credit = next(i for i in res["items"] if i["component"].startswith("Rural or Remote Rate Protection (RRRP) credit"))
    assert credit["status"] == "excluded" and credit["reason"] == "conditional"
    # 7B-1 was 309.50; CBR +0.60, CBR rider -0.60, 1588 non-WMP rider -3.20 and SSS +0.25 now apply.
    assert round(res["cost"], 2) == 306.55


def test_rm7b_fixture_crosswalk_excluded_variants_are_never_used():
    result = RM7B__build(RM7B__fx())
    used = {rid for m in result["models"] for lv in m["levels"] for row in lv["utilities"] for rid in row["records"]}
    listed = {r["record_id"] for m in result["models"] for u in m["utilities"] for r in u["records"]}
    assert not ({2146, 3006} & (used | listed))


def test_rm7b_fixture_market_pending_after_injecting_value_less_market_energy():
    fx = RM7B__fx()
    injected = copy.deepcopy(fx)
    for rec in injected["records"]:
        if rec["rate_structure"] == "demand":
            rec["components"].append(RM7B__c("energy", None, "$/kWh", "Market Energy (OEMP + Class B GA)",
                                        market_reference="IESO OEMP + GA (Class B)", notes=RM7B_MARKET_NOTE))
    result = RM7B__build(injected, fixture=fx)
    for model_id in (RM7B_MEDIUM, RM7B_LARGE, RM7B_XLARGE):
        model = RM7B__model(result, model_id)
        assert model["state"] == "market_energy_pending"
        assert model["cost_basis"] == "delivery_only_market_energy_pending" and model["energy"]["market_pending"]
    assert RM7B__level(RM7B__model(result, RM7B_MEDIUM), "m1")["without_tax"]["median"] == 1908.07
    assert RM7B__model(result, RM7B_RES_TOU)["state"] == "modeled"


def test_rm7b_output_shape_and_method_text_disclosures():
    result = RM7B__build(RM7B__fx())
    assert {"version", "method_version", "generated_at", "as_of", "input", "assumptions", "models",
            "coverage_report"} <= set(result)
    assert result["assumptions"]["days_per_month"] == 30.4375 and result["assumptions"]["power_factor_for_kva"] == 0.9
    assert result["coverage_report"]["totals"]["records"] == 36
    model = RM7B__model(result, RM7B_RES_TOU)
    assert {"key", "label", "state", "provenance", "coverage", "buckets", "levels", "tou", "method",
            "exclusions"} <= set(model)
    level = RM7B__level(model, "typical")
    assert {"id", "kwh", "kw", "without_tax", "with_tax", "closest_utility", "outliers"} <= set(level)
    assert [line["name"] for line in level["with_tax"]["lines"]] == ["HST", "Ontario Electricity Rebate (OER)"]
    assert model["tou"]["identical_in_all_records"] and model["tou"]["shares_id"] == "ON_RPP_TOU"
    for text in ("Median of 7 Ontario distributors' residential time-of-use (TOU) tariffs",
                 "zone policy 'median_of_zones'", "64% off-peak / 18% mid-peak / 18% on-peak",
                 "HST 13% of the pre rebate subtotal", "Ontario Electricity Rebate (OER) 23.5%", "loss factors",
                 "Conditional charges included because the reference customer pays them"):
        assert text in model["method"]
    assert [entry["id"] for entry in model["reference_customer"]] == [CBR, NON_WMP, SSS]
    assert [entry["id"] for entry in result["assumptions"]["reference_customer"]] == [CBR, GA, NON_WMP, SSS]
    assert "Not applied: Ontario Electricity Rebate (OER) at m1" in RM7B__model(result, RM7B_MEDIUM)["method"]
    assert GA in [entry["id"] for entry in RM7B__model(result, RM7B_MEDIUM)["reference_customer"]]
    energy = {b["period"]: b["median"] for b in model["buckets"] if b["bucket"] == "energy"}
    assert energy == {"mid-peak": 0.157, "off-peak": 0.098, "on-peak": 0.203}


def test_rm7b_cli_build_writes_the_models_json(tmp_path, capsys):
    fx = RM7B__fx()
    paths = {}
    for name in ("crosswalk", "usage_levels", "taxes"):
        paths[name] = tmp_path / (name + ".json")
        paths[name].write_text(json.dumps(fx[name]), encoding="utf-8")
    output = tmp_path / "models.json"
    argv = ["--build", "--rates", str(RM7B_FIXTURE), "--crosswalk", str(paths["crosswalk"]), "--usage-levels",
            str(paths["usage_levels"]), "--taxes", str(paths["taxes"]), "--output", str(output), "--as-of", RM7B_AS_OF,
            "--zone-policy", "default_only"]
    assert RM7B_main(argv) == 0
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written["assumptions"]["zone_policy"] == "default_only" and len(written["models"]) == 7
    assert RM7B_RES_TOU in capsys.readouterr().out


def test_rm7b_current_model_files_build_on_the_fixture():
    result = RM7B_build_models(RM7B__fx()["records"], RM7B_load_crosswalk(), RM7B_load_usage_levels(), RM7B_load_taxes(), as_of=RM7B_AS_OF)
    assert result["models"] and all(m["state"] in RM7B_STATES for m in result["models"])
    assert all(lv["without_tax"]["n"] >= 1 for m in result["models"] for lv in m["levels"])
    assert RM7B_ROOT.joinpath("data", "models", "taxes.json").exists()


def RM7B__live_entries(sector, province="ON", fuel="electricity"):
    return RM7B_reference_customer_entries(RM7B_load_usage_levels(), province, fuel, sector)


def RM7B__expected_reference(component, sector):
    """Independent oracle: the reviewed condition families by note prefix (Chapleau sets start differently)."""
    body = RM7B__note_body(component)
    if body.startswith("Conditional: Applies only to Class B customers"):
        return CBR
    if body.startswith("Conditional: Applies only where the service is taken"):
        return SSS
    if body.startswith("Conditional: Applies only to customers that are not wholesale market participants"):
        return NON_WMP
    if body.startswith("Conditional: Applies only to non-RPP Class B customers"):
        return GA if sector in RM7B_DEMAND_SECTORS else None
    return None


def test_rm7b_reference_customer_entries_are_well_formed_and_frozen_in_the_fixture():
    levels = RM7B_load_usage_levels()
    entries = levels["reference_customer"]
    assert [e["id"] for e in entries] == [CBR, GA, NON_WMP, SSS] and levels["reference_customer_basis"]
    for entry in entries:
        assert {"id", "province", "fuel", "sectors", "match", "reason", "source"} <= set(entry), entry["id"]
        assert entry["province"] == "ON" and entry["fuel"] == "electricity" and set(entry["sectors"]) <= set(RM7B_SECTORS)
        assert entry["reason"] and entry["source"]["title"] and (entry["source"]["url"] or entry["source"]["note"])
        assert set(entry["match"]) == {"notes_regex", "name_regex"}
        for regex in entry["match"].values():
            assert regex.startswith("^") and regex.endswith("$") and re.compile(regex)
    assert {e["id"]: e["sectors"] for e in entries}[GA] == list(RM7B_DEMAND_SECTORS)
    assert all(e["sectors"] == list(RM7B_SECTORS) for e in entries if e["id"] != GA)
    assert RM7B__ul()["reference_customer"] == entries, "refresh the frozen fixture copy and its expected values"


def test_rm7b_reference_patterns_match_the_intended_ontario_fixture_components():
    hits = {sector: {CBR: 0, GA: 0, NON_WMP: 0, SSS: 0} for sector in RM7B_SECTORS}
    conditional = 0
    for record in RM7B__fx()["records"]:
        for comp in record["components"]:
            if RM7B_component_exclusion(comp, RM7B_AS_OF) != "conditional":
                continue
            conditional += 1
            for sector in RM7B_SECTORS:
                expected = RM7B__expected_reference(comp, sector)
                assert RM7B_reference_customer_match(comp, RM7B__live_entries(sector)) == expected, (
                    record["id"], comp["component_name"], sector)
                if expected:
                    hits[sector][expected] += 1
    assert conditional == 146
    assert hits["residential"] == {CBR: 65, GA: 0, NON_WMP: 13, SSS: 36}
    assert hits["commercial_medium"] == {CBR: 65, GA: 8, NON_WMP: 13, SSS: 36}


def test_rm7b_reference_patterns_reject_excluded_and_near_miss_conditions():
    records = {r["id"]: r for r in RM7B__fx()["records"]}

    def component(record_id, prefix):
        return next(c for c in records[record_id]["components"] if c["component_name"].startswith(prefix))

    excluded = [component(2226, "Rural or Remote Rate Protection (RRRP) credit"),
                component(2421, "Transformer Allowance for Ownership"),
                component(2421, "Primary Metering Allowance for Transformer Losses"),
                component(2255, "Tranformer Loss Allowance"),
                component(2255, "Customer-Supplied Transformation Allowance"),
                component(2421, "Retail Transmission Rate - Network Service Rate - EV CHARGING")]
    excluded += [c for c in records[2255]["components"] if "Applicable to former Chapleau" in c["component_name"]]
    excluded += [c for r in records.values() for c in r["components"]
                 if RM7B_component_exclusion(c, RM7B_AS_OF) in ("alternative", "market_pending")]
    assert len([c for c in records[2255]["components"] if "Applicable to former Chapleau" in c["component_name"]]) == 3
    base = component(2414, "Capacity Based Recovery (CBR)")
    near_misses = [
        dict(base, notes="Provenance: live_parsed. Conditional: Applies only to Class B customers with interval meters"),
        dict(base, component_name="Rate Rider for Disposition of Global Adjustment Account Applicable only for Class B"),
        dict(component(2414, "Standard Supply Service"), component_name="Smart Metering Entity Charge (if applicable)"),
        dict(component(2153, "Rate Rider for Disposition of Global Adjustment"), component_name="Distribution Volumetric Rate"),
        RM7B__c("energy", None, "$/kWh", "Market Energy", market_reference="IESO OEMP + GA", notes=RM7B_MARKET_NOTE),
    ]
    for comp in excluded + near_misses:
        for sector in RM7B_SECTORS:
            assert RM7B_reference_customer_match(comp, RM7B__live_entries(sector)) is None, (comp["component_name"], sector)
    assert RM7B_reference_customer_match(base, RM7B__live_entries("residential")) == CBR
    assert RM7B__live_entries("residential", province="QC") == [] and RM7B__live_entries("residential", fuel="gas") == []
    assert RM7B_reference_customer_match(base, [{"id": "no-criteria", "match": {}}]) is None
    assert RM7B_reference_customer_match(base, [{"id": "unknown-field", "match": {"tariff_regex": "^.*$"}}]) is None
    assert RM7B_reference_customer_match(base, [{"id": "bad-regex", "match": {"name_regex": "("}}]) is None


def test_rm7b_reference_charges_are_itemized_per_sector_and_strict_without_a_sector():
    rec = next(r for r in RM7B__fx()["records"] if r["id"] == 2467)  # Enova GS 50-4,999 kW
    medium = RM7B__cost(rec, 40000, 100, sector="commercial_medium", structure="demand")
    reasons = {i["component"]: i.get("reason") for i in medium["items"]}
    ga = next(name for name in reasons if name.startswith("Rate Rider for Disposition of Global Adjustment"))
    assert reasons[ga] == "reference_customer:" + GA
    assert reasons["Standard Supply Service - Administrative Charge (if applicable)"] == "reference_customer:" + SSS
    assert sorted(r for r in reasons.values() if r and r.startswith("reference_customer:")) == [
        "reference_customer:" + rid for rid in (CBR, CBR, GA, NON_WMP, SSS)]
    small = RM7B__cost(rec, 40000, 100, sector="commercial_small", structure="demand")
    assert {i["component"]: i.get("reason") for i in small["items"]}[ga] == "conditional"
    strict = RM7B_record_monthly_cost(rec, 40000, 100, structure="demand", usage_levels=RM7B__ul(), as_of=RM7B_AS_OF)
    assert not any((i.get("reason") or "").startswith("reference_customer:") for i in strict["items"])
    assert medium["cost"] - strict["cost"] == pytest.approx(0.0051 * 40000 + 0.0115 * 100 + 0.1832 * 100
                                                            + 0.0006 * 40000 + 0.25)


def test_rm7b_export_hook_writes_compact_models_and_keeps_the_previous_file_on_failure(tmp_path, monkeypatch, caplog):
    from pipeline import export_json, representative_models

    tariffs = [RM7B__rec(RM7B__tou() + [RM7B__c("fixed", fixed, "$/month")], utility=utility, rid=rid)
               for rid, (utility, fixed) in enumerate((("A Hydro", 30.0), ("B Hydro", 40.0), ("C Hydro", 50.0)), 1)]
    tariffs.append(dict(RM7B__rec([RM7B__c("fixed", 1.0, "$/month")], utility="Seed Hydro", rid=9), provenance="seed"))
    out = tmp_path / "site" / "representative_models.json"
    result = export_json.export_representative_models(tariffs, out)
    text = out.read_text(encoding="utf-8")
    written = json.loads(text)
    assert text == json.dumps(written, separators=(",", ":"), ensure_ascii=False) + "\n"
    assert written["models"] == json.loads(json.dumps(result["models"]))
    assert written["assumptions"]["zone_policy"] == "median_of_zones" and written["input"]["provinces"] == ["ON"]
    assert written["input"]["source"] == "site/data/rates.json" and written["input"]["records_considered"] == 3
    typical = RM7B__level(RM7B__model(written, RM7B_RES_TOU), "typical")
    assert typical["without_tax"]["n"] == 3 and typical["closest_utility"]["utility"] == "B Hydro"
    previous = out.read_bytes()

    def broken(*args, **kwargs):
        raise RuntimeError("model build failed")

    monkeypatch.setattr(representative_models, "build_models", broken)
    with caplog.at_level(logging.ERROR, logger="pipeline.export_json"):
        assert export_json.export_representative_models(tariffs, out) is None
    assert out.read_bytes() == previous and "Representative models export failed" in caplog.text
    monkeypatch.setattr(representative_models, "build_models", lambda *args, **kwargs: {"models": [], "x": float("nan")})
    assert export_json.export_representative_models(tariffs, out) is None
    assert out.read_bytes() == previous and not list(out.parent.glob("*.tmp"))
