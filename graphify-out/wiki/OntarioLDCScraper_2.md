# OntarioLDCScraper

> 12 nodes

## Key Concepts

- **._try_live_scrape()** (16 connections) — `scrapers/utilities/ontario_ldc.py`
- **._xml_cross_check()** (6 connections) — `scrapers/utilities/ontario_ldc.py`
- **._fetch_oeb()** (5 connections) — `scrapers/utilities/ontario_ldc.py`
- **._fetch_tariff_pages()** (5 connections) — `scrapers/utilities/ontario_ldc.py`
- **._record_absent_classes()** (4 connections) — `scrapers/utilities/ontario_ldc.py`
- **._drop_duplicate_demand()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._xml_pairs()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._drop_duplicate_labels()** (2 connections) — `scrapers/utilities/ontario_ldc.py`
- **one()** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **Build live records from the LDC's approved tariff(s) and OEB RPP prices.…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **An accepted approved tariff that publishes no class of a group counts as that…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **Compare tariff entries with the OEB bill-data feed; log differences, never…** (1 connections) — `scrapers/utilities/ontario_ldc.py`

## Relationships

- [OntarioLDCScraper](OntarioLDCScraper.md) (10 shared connections)
- [ontario_ldc.py](ontario_ldc.py.md) (3 shared connections)
- [TariffRecord](TariffRecord.md) (2 shared connections)
- [.fetch_page](fetch_page.md) (2 shared connections)
- [._load_sheets](_load_sheets.md) (2 shared connections)
- [._energy_entries](_energy_entries.md) (2 shared connections)
- [BaseScraper](BaseScraper.md) (1 shared connections)
- [oeb_tariff.py](oeb_tariff.py.md) (1 shared connections)
- [build_demand_records](build_demand_records.md) (1 shared connections)

## Source Files

- `scrapers/utilities/ontario_ldc.py`

## Audit Trail

- EXTRACTED: 34 (94%)
- INFERRED: 2 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*