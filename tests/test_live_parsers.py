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
    def scrape_document(document, landing_unavailable=False):
        from scrapers.utilities.hydro_quebec import HydroQuebecScraper
        from scrapers.utils.parsing import DocumentPage

        scraper = HydroQuebecScraper()
        pages = [DocumentPage(**page) for page in document["pages"]]
        with patch.object(scraper, "fetch_page", return_value="<h1>Residential rates</h1>", side_effect=ConnectionError("Landing page unavailable") if landing_unavailable else None), \
             patch.object(scraper, "fetch_bytes", return_value=b"pdf"), \
             patch.object(scraper, "now_iso", return_value="2026-10-02T00:00:00+00:00"), \
             patch.object(scraper, "_parse_rate_d", return_value=None), \
             patch.object(scraper, "_parse_rate_g", return_value=None), \
             patch.object(scraper, "_parse_rate_m", return_value=None), \
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
        assert set(records) == {"Res", "SC", "LC", "Res-DS", "SC-DS", "LC-DS"}
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
        assert set(self.parse(pages)) == {"SC", "SC-DS", "LC", "LC-DS"}

    def test_source_values_and_retailer_eligibility(self, pages):
        pages["residential"] = pages["residential"].replace("$26.50", "$27.50")
        records = self.parse(pages)
        assert next(component.charge_value for component in records["Res"].components if component.component_type == "fixed") == 27.5
        pages["retailers"] = ""
        assert set(self.parse(pages)) == {"Res", "SC", "LC"}

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
            assert len(records) == 6
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
