# BaseScraper

> God node · 84 connections · `scrapers/base.py`

**Community:** [BaseScraper](BaseScraper.md)

## Connections by Relation

### contains
- base.py `EXTRACTED`

### imports
- [enmax_power.py](enmax_power.py.md) `EXTRACTED`
- [epcor_distribution.py](epcor_distribution.py.md) `EXTRACTED`
- fortisbc_electric.py `EXTRACTED`
- [ntpc.py](ntpc.py.md) `EXTRACTED`
- [ontario_ldc.py](ontario_ldc.py.md) `EXTRACTED`
- [fortisalberta.py](fortisalberta.py.md) `EXTRACTED`
- [nl_hydro.py](nl_hydro.py.md) `EXTRACTED`
- epcor_gas_ontario.py `EXTRACTED`
- atco_electric.py `EXTRACTED`
- enbridge_gas.py `EXTRACTED`
- [run_scrape.py](run_scrape.py.md) `EXTRACTED`
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) `EXTRACTED`
- atco_gas.py `EXTRACTED`
- enmax_energy.py `EXTRACTED`
- manitoba_hydro.py `EXTRACTED`
- nb_power.py `EXTRACTED`
- yukon_energy.py `EXTRACTED`
- aeso.py `EXTRACTED`
- [maritime_electric.py](maritime_electric.py.md) `EXTRACTED`
- direct_energy_regulated.py `EXTRACTED`
- *…and 15 more `imports` connection(s) not listed (lowest-degree first to go)*

### inherits
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) `EXTRACTED`
- [EnbridgeGasScraper](EnbridgeGasScraper.md) `EXTRACTED`
- [CentraGasScraper](CentraGasScraper.md) `EXTRACTED`
- [OntarioLDCScraper](OntarioLDCScraper.md) `EXTRACTED`
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) `EXTRACTED`
- [BCHydroScraper](BCHydroScraper.md) `EXTRACTED`
- [EPCOROntarioGasScraper](EPCOROntarioGasScraper.md) `EXTRACTED`
- [NBPowerScraper](NBPowerScraper.md) `EXTRACTED`
- NewfoundlandPowerScraper `EXTRACTED`
- [ATCOGasScraper](ATCOGasScraper.md) `EXTRACTED`
- [EnergirScraper](EnergirScraper.md) `EXTRACTED`
- HydroQuebecScraper `EXTRACTED`
- NLHydroScraper `EXTRACTED`
- [MaritimeElectricScraper](MaritimeElectricScraper.md) `EXTRACTED`
- [SaskEnergyScraper](SaskEnergyScraper.md) `EXTRACTED`
- YukonEnergyScraper `EXTRACTED`
- [HeritageGasScraper](HeritageGasScraper.md) `EXTRACTED`
- [LibertyGasNBScraper](LibertyGasNBScraper.md) `EXTRACTED`
- SaskPowerScraper `EXTRACTED`
- [ManitobaHydroScraper](ManitobaHydroScraper.md) `EXTRACTED`
- *…and 15 more `inherits` connection(s) not listed (lowest-degree first to go)*

### method
- .mark_fallback() `EXTRACTED`
- .fetch_page() `EXTRACTED`
- .mark_live_parsed() `EXTRACTED`
- .__init__() `EXTRACTED`
- .fetch_bytes() `EXTRACTED`
- .now_iso() `EXTRACTED`
- .verify_official_records() `EXTRACTED`
- .fetch_rendered_page() `EXTRACTED`
- ._build_session() `EXTRACTED`
- .scrape() `EXTRACTED`
- .content_hash() `EXTRACTED`

### rationale_for
- Abstract base for every utility scraper. Subclasses MUST implement: scrape() ->… `EXTRACTED`

### uses
- load_scraper() `INFERRED`

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*