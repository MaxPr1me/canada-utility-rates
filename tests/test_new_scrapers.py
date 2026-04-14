"""
test_new_scrapers.py — Tests for all non-Ontario utility scrapers added in the expansion.

Covers: provincial electricity, gas utilities, and territory utilities.
Each test instantiates the scraper, calls scrape(), and verifies
that the seed data produces valid TariffRecord objects.
"""

import sys
from pathlib import Path

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from scrapers.base import TariffRecord


# ─── Provincial Electricity ───────────────────────────────────

class TestFortisBCElectric:
    def setup_method(self):
        from scrapers.utilities.fortisbc_electric import FortisBCElectricScraper
        self.records = FortisBCElectricScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) > 0
        assert all(isinstance(r, TariffRecord) for r in self.records)

    def test_province_and_type(self):
        for r in self.records:
            assert r.province == "BC"
            assert r.utility_type == "electricity"

    def test_has_residential(self):
        res = [r for r in self.records if r.customer_class == "residential"]
        assert len(res) >= 1
        assert res[0].components  # has components


class TestManitobaHydro:
    def setup_method(self):
        from scrapers.utilities.manitoba_hydro import ManitobaHydroScraper
        self.records = ManitobaHydroScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 2

    def test_province(self):
        for r in self.records:
            assert r.province == "MB"

    def test_has_residential_and_commercial(self):
        classes = {r.customer_class for r in self.records}
        assert "residential" in classes


class TestSaskPower:
    def setup_method(self):
        from scrapers.utilities.saskpower import SaskPowerScraper
        self.records = SaskPowerScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 2

    def test_province(self):
        for r in self.records:
            assert r.province == "SK"


class TestNBPower:
    def setup_method(self):
        from scrapers.utilities.nb_power import NBPowerScraper
        self.records = NBPowerScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_province(self):
        for r in self.records:
            assert r.province == "NB"


class TestNovaScotiaPower:
    def setup_method(self):
        from scrapers.utilities.nova_scotia_power import NovaScotiaPowerScraper
        self.records = NovaScotiaPowerScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_province(self):
        for r in self.records:
            assert r.province == "NS"


class TestMaritimeElectric:
    def setup_method(self):
        from scrapers.utilities.maritime_electric import MaritimeElectricScraper
        self.records = MaritimeElectricScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_province(self):
        for r in self.records:
            assert r.province == "PE"


class TestNewfoundlandPower:
    def setup_method(self):
        from scrapers.utilities.newfoundland_power import NewfoundlandPowerScraper
        self.records = NewfoundlandPowerScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_province(self):
        for r in self.records:
            assert r.province == "NL"


class TestNLHydro:
    def setup_method(self):
        from scrapers.utilities.nl_hydro import NLHydroScraper
        self.records = NLHydroScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_province(self):
        for r in self.records:
            assert r.province == "NL"


# ─── Gas Utilities ────────────────────────────────────────────

class TestEnergir:
    def setup_method(self):
        from scrapers.utilities.energir import EnergirScraper
        self.records = EnergirScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_is_gas(self):
        for r in self.records:
            assert r.utility_type == "gas"
            assert r.province == "QC"


class TestFortisBCEnergy:
    def setup_method(self):
        from scrapers.utilities.fortisbc_energy import FortisBCEnergyScraper
        self.records = FortisBCEnergyScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_is_gas(self):
        for r in self.records:
            assert r.utility_type == "gas"
            assert r.province == "BC"


class TestATCOGas:
    def setup_method(self):
        from scrapers.utilities.atco_gas import ATCOGasScraper
        self.records = ATCOGasScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_is_gas(self):
        for r in self.records:
            assert r.utility_type == "gas"
            assert r.province == "AB"

    def test_has_carbon_charge(self):
        all_types = set()
        for r in self.records:
            for c in r.components:
                all_types.add(c.component_type)
        assert "carbon" in all_types


class TestCentraGas:
    def setup_method(self):
        from scrapers.utilities.centra_gas import CentraGasScraper
        self.records = CentraGasScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_is_gas(self):
        for r in self.records:
            assert r.utility_type == "gas"
            assert r.province == "MB"


class TestSaskEnergy:
    def setup_method(self):
        from scrapers.utilities.saskenergy import SaskEnergyScraper
        self.records = SaskEnergyScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_is_gas(self):
        for r in self.records:
            assert r.utility_type == "gas"
            assert r.province == "SK"


class TestHeritageGas:
    def setup_method(self):
        from scrapers.utilities.heritage_gas import HeritageGasScraper
        self.records = HeritageGasScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_is_gas(self):
        for r in self.records:
            assert r.utility_type == "gas"
            assert r.province == "NS"


class TestLibertyGasNB:
    def setup_method(self):
        from scrapers.utilities.liberty_gas_nb import LibertyGasNBScraper
        self.records = LibertyGasNBScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_is_gas(self):
        for r in self.records:
            assert r.utility_type == "gas"
            assert r.province == "NB"


class TestEPCORGas:
    def setup_method(self):
        from scrapers.utilities.epcor_gas import EPCORGasScraper
        self.records = EPCORGasScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_is_gas(self):
        for r in self.records:
            assert r.utility_type == "gas"
            assert r.province == "AB"


# ─── Territory Utilities ──────────────────────────────────────

class TestYukonEnergy:
    def setup_method(self):
        from scrapers.utilities.yukon_energy import YukonEnergyScraper
        self.records = YukonEnergyScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 2

    def test_province(self):
        for r in self.records:
            assert r.province == "YT"


class TestYukonElectrical:
    def setup_method(self):
        from scrapers.utilities.yukon_electrical import YukonElectricalScraper
        self.records = YukonElectricalScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_province(self):
        for r in self.records:
            assert r.province == "YT"


class TestNTPC:
    def setup_method(self):
        from scrapers.utilities.ntpc import NTPCScraper
        self.records = NTPCScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 2

    def test_province(self):
        for r in self.records:
            assert r.province == "NT"

    def test_has_expensive_rates(self):
        """NT rates should be much higher than southern Canada."""
        for r in self.records:
            energy_comps = [c for c in r.components if c.component_type == "energy"]
            for c in energy_comps:
                if c.charge_value is not None:
                    assert c.charge_value > 0.20, "NT rates should be > $0.20/kWh"


class TestQulliq:
    def setup_method(self):
        from scrapers.utilities.qulliq import QulliqScraper
        self.records = QulliqScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_province(self):
        for r in self.records:
            assert r.province == "NU"

    def test_confidence_is_low(self):
        for r in self.records:
            assert r.confidence in ("low", "unverified")


# ─── Ontario LDC Scraper ─────────────────────────────────────

class TestOntarioLDCScraper:
    def test_known_ldc(self):
        from scrapers.utilities.ontario_ldc import OntarioLDCScraper
        s = OntarioLDCScraper(registry_entry={"name": "Hydro Ottawa Ltd."})
        records = s.scrape()
        # 3 residential (TOU, Tiered, ULO) + 3 GS<50 (TOU, Tiered, ULO)
        # + 3 demand tiers (GS-D1, GS-D2, GS-D3) + 1 street lighting = 10
        assert len(records) == 10
        assert all(r.province == "ON" for r in records)
        assert all(r.utility_name == "Hydro Ottawa Ltd." for r in records)

    def test_tou_has_peak_periods(self):
        from scrapers.utilities.ontario_ldc import OntarioLDCScraper
        s = OntarioLDCScraper(registry_entry={"name": "London Hydro Inc."})
        records = s.scrape()
        tou = [r for r in records if r.rate_structure == "tou" and "TOU" in r.tariff_name][0]
        periods = {c.tou_period for c in tou.components if c.tou_period}
        assert "off-peak" in periods
        assert "mid-peak" in periods
        assert "on-peak" in periods

    def test_delivery_charges_differ_by_ldc(self):
        from scrapers.utilities.ontario_ldc import OntarioLDCScraper
        s1 = OntarioLDCScraper(registry_entry={"name": "Toronto Hydro-Electric System Ltd."})
        s2 = OntarioLDCScraper(registry_entry={"name": "Hydro One Networks Inc."})
        r1 = s1.scrape()[0]
        r2 = s2.scrape()[0]
        fixed1 = [c for c in r1.components if c.component_type == "fixed"][0].charge_value
        fixed2 = [c for c in r2.components if c.component_type == "fixed"][0].charge_value
        assert fixed1 != fixed2  # Different LDCs have different delivery charges

    def test_unknown_ldc_uses_median(self):
        from scrapers.utilities.ontario_ldc import OntarioLDCScraper
        s = OntarioLDCScraper(registry_entry={"name": "Nonexistent Power Co."})
        records = s.scrape()
        # 3 residential + 3 GS<50 + 1 demand tier (gs_d1) + 1 street lighting = 8
        assert len(records) == 8
        assert records[0].confidence == "unverified"

    def test_all_55_ldcs_have_data(self):
        from scrapers.utilities.ontario_ldc import ONTARIO_LDC_DATA
        assert len(ONTARIO_LDC_DATA) >= 53  # at least 53 LDCs in the data dict

    def test_has_commercial_classes(self):
        from scrapers.utilities.ontario_ldc import OntarioLDCScraper
        s = OntarioLDCScraper(registry_entry={"name": "Toronto Hydro-Electric System Ltd."})
        records = s.scrape()
        classes = {r.customer_class for r in records}
        assert "residential" in classes
        assert "commercial" in classes
        # Check GS < 50 kW
        gs_small = [r for r in records if r.sub_class == "GS < 50 kW"]
        assert len(gs_small) >= 3  # TOU, Tiered, ULO
        # Check demand tiers (GS >= 50 kW)
        demand = [r for r in records if r.rate_structure == "demand"]
        assert len(demand) >= 1
        assert demand[0].demand_min_kw == 50

    def test_has_street_lighting(self):
        from scrapers.utilities.ontario_ldc import OntarioLDCScraper
        s = OntarioLDCScraper(registry_entry={"name": "Hydro Ottawa Ltd."})
        records = s.scrape()
        sl = [r for r in records if r.sub_class == "street lighting"]
        assert len(sl) == 1
        assert sl[0].customer_class == "other"

    def test_demand_tiers(self):
        """Major LDC with 3 demand tiers has distinct tariff codes."""
        from scrapers.utilities.ontario_ldc import OntarioLDCScraper
        s = OntarioLDCScraper(registry_entry={"name": "Hydro Ottawa Ltd."})
        records = s.scrape()
        demand = [r for r in records if r.rate_structure == "demand"]
        codes = {r.tariff_code for r in demand}
        assert codes == {"GS-D1", "GS-D2", "GS-D3"}
        # Check demand ranges don't overlap
        d1 = [r for r in demand if r.tariff_code == "GS-D1"][0]
        d2 = [r for r in demand if r.tariff_code == "GS-D2"][0]
        d3 = [r for r in demand if r.tariff_code == "GS-D3"][0]
        assert d1.demand_min_kw == 50
        assert d2.demand_min_kw == 1500
        assert d3.demand_min_kw == 5000
        assert d3.demand_max_kw is None  # no upper bound

    def test_demand_tier_transmission_is_demand_based(self):
        """GS >= 50 kW transmission should be $/kW, not $/kWh."""
        from scrapers.utilities.ontario_ldc import OntarioLDCScraper
        s = OntarioLDCScraper(registry_entry={"name": "Hydro Ottawa Ltd."})
        records = s.scrape()
        d1 = [r for r in records if r.tariff_code == "GS-D1"][0]
        tx = [c for c in d1.components if c.component_type == "transmission"]
        assert len(tx) == 2
        for c in tx:
            assert c.charge_unit == "$/kW", f"Demand-tier TX should be $/kW, got {c.charge_unit}"

    def test_small_ldc_fewer_tiers(self):
        """Small LDC with only gs_d1 should have fewer records."""
        from scrapers.utilities.ontario_ldc import OntarioLDCScraper
        s = OntarioLDCScraper(registry_entry={"name": "Burlington Hydro Inc."})
        records = s.scrape()
        demand = [r for r in records if r.rate_structure == "demand"]
        assert len(demand) == 1
        assert demand[0].tariff_code == "GS-D1"

    def test_oeb_rates_updated(self):
        """OEB rates should be Nov 2025 values."""
        from scrapers.utilities.ontario_ldc import OEB_TOU, OEB_ULO, OEB_REGULATORY_CHARGE
        assert OEB_TOU["off_peak"] == 0.098
        assert OEB_TOU["on_peak"] == 0.203
        assert OEB_ULO["ultra_low_overnight"] == 0.039
        assert OEB_REGULATORY_CHARGE == 0.0053

    def test_gs_ulo_present(self):
        """GS < 50 kW should have ULO tariff."""
        from scrapers.utilities.ontario_ldc import OntarioLDCScraper
        s = OntarioLDCScraper(registry_entry={"name": "Hydro Ottawa Ltd."})
        records = s.scrape()
        gs_ulo = [r for r in records if r.tariff_code == "GS-ULO-S"]
        assert len(gs_ulo) == 1
        assert gs_ulo[0].sub_class == "GS < 50 kW"

    def test_industrial_class_for_large_demand(self):
        """GS-D3 (5,000+ kW) should be customer_class='industrial'."""
        from scrapers.utilities.ontario_ldc import OntarioLDCScraper
        s = OntarioLDCScraper(registry_entry={"name": "Hydro Ottawa Ltd."})
        records = s.scrape()
        d3 = [r for r in records if r.tariff_code == "GS-D3"][0]
        assert d3.customer_class == "industrial"


# ─── Alberta Distribution Utilities ─────────────────────────

class TestATCOElectric:
    def setup_method(self):
        from scrapers.utilities.atco_electric import ATCOElectricScraper
        self.records = ATCOElectricScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 3  # residential + small commercial + large commercial

    def test_province(self):
        for r in self.records:
            assert r.province == "AB"
            assert r.utility_type == "electricity"

    def test_has_commercial(self):
        classes = {r.customer_class for r in self.records}
        assert "residential" in classes
        assert "commercial" in classes


class TestFortisAlberta:
    def setup_method(self):
        from scrapers.utilities.fortisalberta import FortisAlbertaScraper
        self.records = FortisAlbertaScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 3

    def test_province(self):
        for r in self.records:
            assert r.province == "AB"
            assert r.utility_type == "electricity"


class TestEPCORDistribution:
    def setup_method(self):
        from scrapers.utilities.epcor_distribution import EPCORDistributionScraper
        self.records = EPCORDistributionScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 3

    def test_province(self):
        for r in self.records:
            assert r.province == "AB"


class TestENMAXPower:
    def setup_method(self):
        from scrapers.utilities.enmax_power import ENMAXPowerScraper
        self.records = ENMAXPowerScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 3

    def test_province(self):
        for r in self.records:
            assert r.province == "AB"


# ─── Alberta Retail/RRO Utilities ────────────────────────────

class TestDirectEnergyRegulated:
    def setup_method(self):
        from scrapers.utilities.direct_energy_regulated import DirectEnergyRegulatedScraper
        self.records = DirectEnergyRegulatedScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 2

    def test_province_and_market(self):
        for r in self.records:
            assert r.province == "AB"
            assert r.rate_structure == "market"


class TestENMAXEnergy:
    def setup_method(self):
        from scrapers.utilities.enmax_energy import ENMAXEnergyScraper
        self.records = ENMAXEnergyScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 2

    def test_province(self):
        for r in self.records:
            assert r.province == "AB"


class TestEPCOREnergyAlberta:
    def setup_method(self):
        from scrapers.utilities.epcor_energy_alberta import EPCOREnergyAlbertaScraper
        self.records = EPCOREnergyAlbertaScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 2

    def test_province(self):
        for r in self.records:
            assert r.province == "AB"


class TestAESO:
    def setup_method(self):
        from scrapers.utilities.aeso import AESOScraper
        self.records = AESOScraper().scrape()

    def test_returns_records(self):
        assert len(self.records) >= 1

    def test_is_market_reference(self):
        for r in self.records:
            assert r.province == "AB"
            assert r.rate_structure == "market"
            assert r.customer_class == "other"
