# ENMAXEnergyScraper

> 16 nodes

## Key Concepts

- **.mark_live_parsed()** (49 connections) — `scrapers/base.py`
- **ENMAXEnergyScraper** (12 connections) — `scrapers/utilities/enmax_energy.py`
- **._try_live_scrape()** (11 connections) — `scrapers/utilities/enmax_energy.py`
- **.scrape()** (7 connections) — `scrapers/utilities/ntpc.py`
- **.scrape()** (6 connections) — `scrapers/utilities/epcor_gas_ontario.py`
- **.scrape()** (5 connections) — `scrapers/utilities/enmax_energy.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/ntpc.py`
- **._pdf_pages()** (4 connections) — `scrapers/utilities/enmax_energy.py`
- **._seed_data()** (4 connections) — `scrapers/utilities/enmax_energy.py`
- **._today()** (3 connections) — `scrapers/utilities/enmax_energy.py`
- **.__init__()** (2 connections) — `scrapers/utilities/enmax_energy.py`
- **Label records rebuilt directly from a live fetch this run. Use this when a…** (1 connections) — `scrapers/base.py`
- **Scrape ENMAX Energy Corporation RoLR rates for Calgary, Alberta.** (1 connections) — `scrapers/utilities/enmax_energy.py`
- **Parse the ENMAX RoLR page and rate schedule; the UCA table is a required cross-…** (1 connections) — `scrapers/utilities/enmax_energy.py`
- **Parse the current PUB-approved schedule; label any unreplaced seed as an…** (1 connections) — `scrapers/utilities/ntpc.py`
- **Return seed/fallback data based on known published rates.** (1 connections) — `scrapers/utilities/ntpc.py`

## Relationships

- [TariffRecord](TariffRecord.md) (14 shared connections)
- [extract_pdf_pages](extract_pdf_pages.md) (8 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (5 shared connections)
- [RateComponent](RateComponent.md) (4 shared connections)
- [DocumentPage](DocumentPage.md) (3 shared connections)
- [nl_hydro.py](nl_hydro.py.md) (3 shared connections)
- [EPCOROntarioGasScraper](EPCOROntarioGasScraper.md) (3 shared connections)
- [ntpc.py](ntpc.py.md) (3 shared connections)
- [BaseScraper](BaseScraper.md) (2 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (2 shared connections)
- [parse_html](parse_html.md) (2 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (2 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/enmax_energy.py`
- `scrapers/utilities/epcor_gas_ontario.py`
- `scrapers/utilities/ntpc.py`

## Audit Trail

- EXTRACTED: 91 (97%)
- INFERRED: 3 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*