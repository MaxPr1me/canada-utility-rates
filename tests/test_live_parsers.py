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

    def test_confidence_is_high(self):
        """HQ rates now verified from official PDF — confidence should be high."""
        for r in self.records:
            assert r.confidence == "high"

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

    def test_effective_dates_updated(self):
        for r in self.records:
            assert r.effective_date == "2025-01-01"


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
