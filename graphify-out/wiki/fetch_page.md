# .fetch_page

> 43 nodes

## Key Concepts

- **.fetch_page()** (50 connections) — `scrapers/base.py`
- **.mark_live_parsed()** (49 connections) — `scrapers/base.py`
- **.fetch_bytes()** (44 connections) — `scrapers/base.py`
- **._try_live_scrape()** (17 connections) — `scrapers/utilities/saskpower.py`
- **._try_live_scrape()** (14 connections) — `scrapers/utilities/newfoundland_power.py`
- **._try_live_scrape()** (13 connections) — `scrapers/utilities/fortisbc_energy.py`
- **._try_live_scrape()** (11 connections) — `scrapers/utilities/enbridge_gas.py`
- **._try_live_scrape()** (11 connections) — `scrapers/utilities/enmax_energy.py`
- **._try_live_scrape()** (11 connections) — `scrapers/utilities/nl_hydro.py`
- **.fetch_rendered_page()** (10 connections) — `scrapers/base.py`
- **.verify_official_records()** (10 connections) — `scrapers/base.py`
- **._try_live_scrape()** (10 connections) — `scrapers/utilities/enmax_power.py`
- **._try_live_scrape()** (10 connections) — `scrapers/utilities/heritage_gas.py`
- **._try_live_scrape()** (8 connections) — `scrapers/utilities/direct_energy_regulated.py`
- **._try_live_residential()** (8 connections) — `scrapers/utilities/nova_scotia_power.py`
- **._log_response()** (6 connections) — `scrapers/base.py`
- **._discover_schedule_url()** (6 connections) — `scrapers/utilities/enmax_power.py`
- **._try_last_known_schedule()** (6 connections) — `scrapers/utilities/nl_hydro.py`
- **._discover_handbook()** (5 connections) — `scrapers/utilities/enbridge_gas.py`
- **verify_tariff_values()** (5 connections) — `scrapers/utils/parsing.py`
- **describe_response()** (4 connections) — `scrapers/base.py`
- **._pdf_pages()** (4 connections) — `scrapers/utilities/enmax_energy.py`
- **rate_value_appears()** (4 connections) — `scrapers/utils/parsing.py`
- **Response** (2 connections)
- **GET a URL and return the response text. Includes a polite delay between…** (1 connections) — `scrapers/base.py`
- *... and 18 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (33 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (20 shared connections)
- [parse_html](parse_html.md) (12 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (10 shared connections)
- [.mark_fallback](mark_fallback.md) (10 shared connections)
- [fortisbc_electric.py](fortisbc_electric.py.md) (7 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (7 shared connections)
- [extract_effective_date](extract_effective_date.md) (7 shared connections)
- [re](re.md) (6 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (6 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (5 shared connections)
- [EPCOROntarioGasScraper](EPCOROntarioGasScraper.md) (4 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/direct_energy_regulated.py`
- `scrapers/utilities/enbridge_gas.py`
- `scrapers/utilities/enmax_energy.py`
- `scrapers/utilities/enmax_power.py`
- `scrapers/utilities/fortisbc_energy.py`
- `scrapers/utilities/heritage_gas.py`
- `scrapers/utilities/newfoundland_power.py`
- `scrapers/utilities/nl_hydro.py`
- `scrapers/utilities/nova_scotia_power.py`
- `scrapers/utilities/saskpower.py`
- `scrapers/utils/parsing.py`

## Audit Trail

- EXTRACTED: 273 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*