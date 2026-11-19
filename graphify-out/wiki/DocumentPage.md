# DocumentPage

> 22 nodes

## Key Concepts

- **DocumentPage** (222 connections) — `scrapers/utils/parsing.py`
- **parse_manual()** (11 connections) — `scrapers/utilities/summerside_electric.py`
- **FortisBCElectricScraper** (10 connections) — `scrapers/utilities/fortisbc_electric.py`
- **.scrape()** (8 connections) — `scrapers/utilities/fortisbc_electric.py`
- **extract_schedule_pages()** (6 connections) — `scrapers/utilities/fortisbc_electric.py`
- **manual_effective()** (6 connections) — `scrapers/utilities/summerside_electric.py`
- **._fetch_schedule_pages()** (5 connections) — `scrapers/utilities/fortisbc_electric.py`
- **.parse_schedule_pages()** (5 connections) — `scrapers/utilities/fortisbc_electric.py`
- **find_pdf_section()** (4 connections) — `scrapers/utils/parsing.py`
- **_iso()** (2 connections) — `scrapers/utilities/summerside_electric.py`
- **record()** (2 connections) — `scrapers/utilities/summerside_electric.py`
- **.source_detail()** (1 connections) — `scrapers/utils/parsing.py`
- **where()** (1 connections) — `scrapers/utilities/summerside_electric.py`
- **date** (1 connections)
- **Extract only the supported schedule sheets from the full Electric Tariff PDF.…** (1 connections) — `scrapers/utilities/fortisbc_electric.py`
- **Scrape FortisBC Electric building rate schedules from the official Electric…** (1 connections) — `scrapers/utilities/fortisbc_electric.py`
- **Parse each schedule independently; label seed fallbacks for failed seeded…** (1 connections) — `scrapers/utilities/fortisbc_electric.py`
- **Return the schedules that parse completely; a failing schedule is skipped and…** (1 connections) — `scrapers/utilities/fortisbc_electric.py`
- **Most recent date of the page-2 revision table (rate adjustments only).** (1 connections) — `scrapers/utilities/summerside_electric.py`
- **Build the in-scope Section N schedules; raise ValueError (fail closed) on a…** (1 connections) — `scrapers/utilities/summerside_electric.py`
- **Return pages belonging to a labelled tariff section. Merely finding a number is…** (1 connections) — `scrapers/utils/parsing.py`
- **Text extracted from one source page, retaining its human page number.** (1 connections) — `scrapers/utils/parsing.py`

## Relationships

- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (25 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (24 shared connections)
- [BaseScraper](BaseScraper.md) (23 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (17 shared connections)
- [epcor_distribution.py](epcor_distribution.py.md) (15 shared connections)
- [TariffRecord](TariffRecord.md) (14 shared connections)
- [enmax_power.py](enmax_power.py.md) (14 shared connections)
- [re](re.md) (13 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (13 shared connections)
- [NewfoundlandPowerScraper](NewfoundlandPowerScraper.md) (11 shared connections)
- [EnbridgeGasScraper](EnbridgeGasScraper.md) (10 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (8 shared connections)

## Source Files

- `scrapers/utilities/fortisbc_electric.py`
- `scrapers/utilities/summerside_electric.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 168 (63%)
- INFERRED: 97 (37%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*