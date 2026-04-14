"""
test_scrapers.py — Tests for the utility scrapers (seed data path).

Each scraper tries to fetch live pages and falls back to seed data.
These tests mock _try_live_scrape to return None so the scrapers
use their built-in seed data, then verify the returned TariffRecords.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch

from scrapers.base import TariffRecord, RateComponent
from scrapers.utilities.bc_hydro import BCHydroScraper
from scrapers.utilities.hydro_quebec import HydroQuebecScraper
from scrapers.utilities.toronto_hydro import TorontoHydroScraper
from scrapers.utilities.enbridge_gas import EnbridgeGasScraper


# ─── BC Hydro ────────────────────────────────────────────────────

class TestBCHydroSeed:
    @pytest.fixture(autouse=True)
    def scraper(self):
        with patch.object(BCHydroScraper, "_try_live_scrape", return_value=None):
            self.scraper = BCHydroScraper()
            self.records = self.scraper.scrape()

    def test_returns_non_empty_list(self):
        assert len(self.records) > 0

    def test_returns_tariff_records(self):
        for rec in self.records:
            assert isinstance(rec, TariffRecord)

    def test_residential_tariff_present(self):
        residential = [r for r in self.records if r.customer_class == "residential"]
        assert len(residential) >= 1

    def test_residential_fields(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        assert res.utility_name == "BC Hydro"
        assert res.province == "BC"
        assert res.utility_type == "electricity"
        assert res.rate_structure == "tiered"
        assert res.tariff_code == "1101"

    def test_residential_has_components(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        assert len(res.components) >= 3  # basic charge + step 1 + step 2

    def test_step_rates(self):
        res = [r for r in self.records if r.customer_class == "residential"][0]
        energy = [c for c in res.components if c.component_type == "energy"]
        assert len(energy) >= 2
        step1 = [c for c in energy if c.tier_number == 1][0]
        step2 = [c for c in energy if c.tier_number == 2][0]
        assert step1.charge_value == pytest.approx(0.0950)
        assert step2.charge_value == pytest.approx(0.1408)
        assert step1.charge_unit == "$/kWh"

    def test_commercial_tariff_present(self):
        commercial = [r for r in self.records if r.customer_class == "commercial"]
        assert len(commercial) >= 1


# ─── Hydro-Québec ────────────────────────────────────────────────

class TestHydroQuebecSeed:
    @pytest.fixture(autouse=True)
    def scraper(self):
        with patch.object(HydroQuebecScraper, "_try_live_scrape", return_value=None):
            self.scraper = HydroQuebecScraper()
            self.records = self.scraper.scrape()

    def test_returns_non_empty_list(self):
        assert len(self.records) > 0

    def test_returns_tariff_records(self):
        for rec in self.records:
            assert isinstance(rec, TariffRecord)

    def test_rate_d_present(self):
        rate_d = [r for r in self.records if r.tariff_code == "D"]
        assert len(rate_d) == 1

    def test_rate_d_fields(self):
        rate_d = [r for r in self.records if r.tariff_code == "D"][0]
        assert rate_d.utility_name == "Hydro-Québec"
        assert rate_d.province == "QC"
        assert rate_d.utility_type == "electricity"
        assert rate_d.customer_class == "residential"
        assert rate_d.rate_structure == "tiered"

    def test_rate_d_has_tiered_energy(self):
        rate_d = [r for r in self.records if r.tariff_code == "D"][0]
        energy = [c for c in rate_d.components if c.component_type == "energy"]
        assert len(energy) >= 2
        tier1 = [c for c in energy if c.tier_number == 1][0]
        assert tier1.charge_value == pytest.approx(0.06509)

    def test_rate_g_present(self):
        rate_g = [r for r in self.records if r.tariff_code == "G"]
        assert len(rate_g) == 1
        assert rate_g[0].customer_class == "commercial"


# ─── Toronto Hydro ───────────────────────────────────────────────

class TestTorontoHydroSeed:
    @pytest.fixture(autouse=True)
    def scraper(self):
        with patch.object(TorontoHydroScraper, "_try_live_scrape", return_value=None):
            self.scraper = TorontoHydroScraper()
            self.records = self.scraper.scrape()

    def test_returns_non_empty_list(self):
        assert len(self.records) > 0

    def test_tou_tariff_present(self):
        tou = [r for r in self.records if r.tariff_code == "TOU-R"]
        assert len(tou) == 1
        assert tou[0].rate_structure == "tou"

    def test_tiered_tariff_present(self):
        tiered = [r for r in self.records if r.tariff_code == "TIER-R"]
        assert len(tiered) == 1
        assert tiered[0].rate_structure == "tiered"

    def test_ulo_tariff_present(self):
        ulo = [r for r in self.records if r.tariff_code == "ULO-R"]
        assert len(ulo) == 1
        assert ulo[0].rate_structure == "tou"

    def test_tou_has_peak_periods(self):
        tou = [r for r in self.records if r.tariff_code == "TOU-R"][0]
        periods = {c.tou_period for c in tou.components if c.tou_period}
        assert "on-peak" in periods
        assert "mid-peak" in periods
        assert "off-peak" in periods

    def test_ulo_has_ultra_low_overnight(self):
        ulo = [r for r in self.records if r.tariff_code == "ULO-R"][0]
        ulo_comps = [c for c in ulo.components if c.tou_period == "ultra-low-overnight"]
        assert len(ulo_comps) == 1
        assert ulo_comps[0].charge_value == pytest.approx(0.028)

    def test_delivery_components_present(self):
        tou = [r for r in self.records if r.tariff_code == "TOU-R"][0]
        comp_types = {c.component_type for c in tou.components}
        assert "distribution" in comp_types
        assert "transmission" in comp_types
        assert "fixed" in comp_types

    def test_all_tariffs_are_ontario(self):
        for rec in self.records:
            assert rec.province == "ON"
            assert rec.utility_name == "Toronto Hydro"


# ─── Enbridge Gas ────────────────────────────────────────────────

class TestEnbridgeGasSeed:
    @pytest.fixture(autouse=True)
    def scraper(self):
        with patch.object(EnbridgeGasScraper, "_try_live_scrape", return_value=None):
            self.scraper = EnbridgeGasScraper()
            self.records = self.scraper.scrape()

    def test_returns_non_empty_list(self):
        assert len(self.records) > 0

    def test_utility_type_is_gas(self):
        for rec in self.records:
            assert rec.utility_type == "gas"

    def test_gas_components_present(self):
        rec = self.records[0]
        comp_types = {c.component_type for c in rec.components}
        assert "commodity" in comp_types
        assert "delivery" in comp_types
        assert "carbon" in comp_types

    def test_fixed_charge(self):
        rec = self.records[0]
        fixed = [c for c in rec.components if c.component_type == "fixed"]
        assert len(fixed) == 1
        assert fixed[0].charge_value == pytest.approx(28.44)
        assert fixed[0].charge_unit == "$/month"

    def test_volumetric_units_are_m3(self):
        rec = self.records[0]
        volumetric = [c for c in rec.components if c.charge_unit == "$/m³"]
        # commodity, delivery, transportation, carbon, rider
        assert len(volumetric) >= 4

    def test_rider_can_be_negative(self):
        rec = self.records[0]
        riders = [c for c in rec.components if c.component_type == "rider"]
        assert len(riders) >= 1
        # The cost adjustment rider is negative in seed data
        assert riders[0].charge_value < 0

    def test_province_and_name(self):
        rec = self.records[0]
        assert rec.province == "ON"
        assert rec.utility_name == "Enbridge Gas"
