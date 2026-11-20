# RateComponent

> 27 nodes

## Key Concepts

- **RateComponent** (287 connections) — `scrapers/base.py`
- **nelson_hydro.py** (17 connections) — `scrapers/utilities/nelson_hydro.py`
- **penticton.py** (17 connections) — `scrapers/utilities/penticton.py`
- **parse_rates()** (11 connections) — `scrapers/utilities/nelson_hydro.py`
- **parse_appendix()** (10 connections) — `scrapers/utilities/penticton.py`
- **parse_rates_page()** (7 connections) — `scrapers/utilities/nelson_hydro.py`
- **._build_record()** (6 connections) — `scrapers/utilities/maritime_electric.py`
- **._parse_component_line()** (5 connections) — `scrapers/utilities/maritime_electric.py`
- **find_bylaw_url()** (5 connections) — `scrapers/utilities/penticton.py`
- **_tier_from_label()** (4 connections) — `scrapers/utilities/maritime_electric.py`
- **_schedule()** (4 connections) — `scrapers/utilities/nelson_hydro.py`
- **_pair()** (3 connections) — `scrapers/utilities/penticton.py`
- **comp()** (2 connections) — `scrapers/utilities/nelson_hydro.py`
- **comp()** (2 connections) — `scrapers/utilities/penticton.py`
- **_iso()** (2 connections) — `scrapers/utilities/nelson_hydro.py`
- **date** (1 connections)
- **date** (1 connections)
- **One individual charge line within a tariff.** (1 connections) — `scrapers/base.py`
- **Build one record; None unless the class has exactly its expected components.** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Turn one '... Charge ... $ value' schedule line into a RateComponent.** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Infer (tier_number, tier_threshold) from a 'first N unit' / 'balance' label.** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **nelson_hydro.py — Scraper for Nelson Hydro, the City of Nelson's electric…** (1 connections) — `scrapers/utilities/nelson_hydro.py`
- **(effective date, {code: (basic per period, energy $/kWh)}, bylaw CivicWeb…** (1 connections) — `scrapers/utilities/nelson_hydro.py`
- **Build A1/A3/B1/B4 from the bylaw schedules of the page's effective year; raise…** (1 connections) — `scrapers/utilities/nelson_hydro.py`
- **penticton.py — Scraper for the City of Penticton electric utility (British…** (1 connections) — `scrapers/utilities/penticton.py`
- *... and 2 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (39 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (22 shared connections)
- [re](re.md) (20 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (19 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (18 shared connections)
- [RateComponent](RateComponent.md) (17 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (14 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (13 shared connections)
- [fortisalberta.py](fortisalberta.py.md) (11 shared connections)
- [extract_effective_date](extract_effective_date.md) (9 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (8 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (8 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/maritime_electric.py`
- `scrapers/utilities/nelson_hydro.py`
- `scrapers/utilities/penticton.py`

## Audit Trail

- EXTRACTED: 308 (86%)
- INFERRED: 51 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*