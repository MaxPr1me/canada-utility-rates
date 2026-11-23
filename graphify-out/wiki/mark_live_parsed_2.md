# .mark_live_parsed

> 20 nodes

## Key Concepts

- **.mark_live_parsed()** (49 connections) — `scrapers/base.py`
- **.fetch_bytes()** (44 connections) — `scrapers/base.py`
- **._try_live_scrape()** (14 connections) — `scrapers/utilities/maritime_electric.py`
- **._try_live_scrape()** (10 connections) — `scrapers/utilities/medicine_hat.py`
- **._try_live_scrape()** (9 connections) — `scrapers/utilities/atco_electric.py`
- **._parse_pages()** (8 connections) — `scrapers/utilities/maritime_electric.py`
- **._try_last_known_schedule()** (8 connections) — `scrapers/utilities/maritime_electric.py`
- **MedicineHatScraper** (7 connections) — `scrapers/utilities/medicine_hat.py`
- **_extract_pages()** (6 connections) — `scrapers/utilities/maritime_electric.py`
- **._apply_schedules()** (6 connections) — `scrapers/utilities/maritime_electric.py`
- **.scrape()** (3 connections) — `scrapers/utilities/medicine_hat.py`
- **.__init__()** (2 connections) — `scrapers/utilities/medicine_hat.py`
- **GET a URL and return raw bytes (for PDFs, spreadsheets).** (1 connections) — `scrapers/base.py`
- **Label records rebuilt directly from a live fetch this run. Use this when a…** (1 connections) — `scrapers/base.py`
- **Return live-parsed classes only; classes that fail are dropped, never replaced…** (1 connections) — `scrapers/utilities/atco_electric.py`
- **Raw per-page text; the shared normalizer drops repeated rows, which this…** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Parse every non-lighting service class from the official Schedule of Adjusted…** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Parse non-lighting service classes from the rate page; each class fails alone.** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Cross-check industrial/wholesale classes against their Section N schedules;…** (1 connections) — `scrapers/utilities/maritime_electric.py`
- **Parse the City of Medicine Hat's bundled electricity rates.** (1 connections) — `scrapers/utilities/medicine_hat.py`

## Relationships

- [BCHydroScraper](BCHydroScraper.md) (11 shared connections)
- [BaseScraper](BaseScraper.md) (10 shared connections)
- [.fetch_page](fetch_page.md) (7 shared connections)
- [._try_live_scrape](_try_live_scrape.md) (7 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (6 shared connections)
- [parse_html](parse_html.md) (5 shared connections)
- [epcor_energy_alberta.py](epcor_energy_alberta.py.md) (5 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (5 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (4 shared connections)
- [ntpc.py](ntpc.py.md) (3 shared connections)
- [.mark_fallback](mark_fallback.md) (3 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (3 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/atco_electric.py`
- `scrapers/utilities/maritime_electric.py`
- `scrapers/utilities/medicine_hat.py`

## Audit Trail

- EXTRACTED: 146 (99%)
- INFERRED: 1 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*