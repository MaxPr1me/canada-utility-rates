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

    def test_live_pdf_parses_residential(self):
        from scrapers.utilities.saskpower import SaskPowerScraper
        html = '<body><p>Current rates</p><a href="/media/report-rates-residential.pdf">Residential rate schedule</a></body>'
        pdf_text = (
            "RESIDENTIAL RATES STANDARD RATE Effective February 1, 2026 "
            "Basic monthly charge $31.16 $31.16 "
            "Energy charge (\u00a2/kWh) 15.476\u00a2 15.476\u00a2"
        )
        scraper = SaskPowerScraper()
        with patch.object(scraper, "fetch_page", return_value=html), \
             patch.object(scraper, "fetch_bytes", return_value=b"pdf"), \
             patch("scrapers.utilities.saskpower.extract_pdf_text", return_value=pdf_text):
            records = scraper._try_live_scrape()
        assert records is not None
        live = [r for r in records if "live_parsed" in (r.notes or "")]
        assert len(live) == 1
        res = live[0]
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
        with patch.object(scraper, "fetch_page", return_value=html), \
             patch.object(scraper, "fetch_bytes", return_value=b"pdf"), \
             patch.object(scraper, "now_iso", return_value="2026-10-01T00:00:00+00:00"), \
             patch("scrapers.utilities.saskpower.extract_pdf_text", side_effect=ValueError("Broken PDF")), \
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

    def test_transformation_fixture_sources_are_registered(self, transformation_documents):
        from scrapers.registry import get_utility

        entry = get_utility("SaskPower")
        registered = {source["url"] for source in entry["sources"]}
        assert {document["source_url"] for document in transformation_documents.values()} <= registered

    @pytest.mark.parametrize("unit", ["$/kWh", "\u00a2/kW"])
    def test_residential_rejects_changed_energy_unit(self, unit):
        from scrapers.utilities.saskpower import SaskPowerScraper

        text = (
            "RESIDENTIAL RATES STANDARD RATE Effective February 1, 2026 "
            f"Basic monthly charge $31.16 $31.16 Energy charge ({unit}) 15.476\u00a2 15.476\u00a2"
        )
        assert SaskPowerScraper()._parse_residential_pdf(text, "https://example.com/rates.pdf") is None


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
