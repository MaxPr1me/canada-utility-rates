# OntarioLDCScraper

> 21 nodes

## Key Concepts

- **OntarioLDCScraper** (30 connections) — `scrapers/utilities/ontario_ldc.py`
- **._try_live_scrape()** (16 connections) — `scrapers/utilities/ontario_ldc.py`
- **._load_sheets()** (8 connections) — `scrapers/utilities/ontario_ldc.py`
- **._xml_cross_check()** (6 connections) — `scrapers/utilities/ontario_ldc.py`
- **._fetch_oeb()** (5 connections) — `scrapers/utilities/ontario_ldc.py`
- **._fetch_tariff_pages()** (5 connections) — `scrapers/utilities/ontario_ldc.py`
- **._record_absent_classes()** (4 connections) — `scrapers/utilities/ontario_ldc.py`
- **._class_rejected()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._drop_duplicate_demand()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **.set_demand_records()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._sheet_problem()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._xml_pairs()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._drop_duplicate_labels()** (2 connections) — `scrapers/utilities/ontario_ldc.py`
- **one()** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **Data-driven scraper for any Ontario electricity LDC. All Ontario LDCs share the…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **Supply externally built GS >= 50 kW records that replace the GS-D seeds. The…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **A configured tariff rejected a class of this group (not a whole sheet).** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **Build live records from the LDC's approved tariff(s) and OEB RPP prices.…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **An accepted approved tariff that publishes no class of a group counts as that…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **Fetch and parse one tariff document; return the accepted (doc, zone sheet)…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **Compare tariff entries with the OEB bill-data feed; log differences, never…** (1 connections) — `scrapers/utilities/ontario_ldc.py`

## Relationships

- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (8 shared connections)
- [._build_rpp_records](_build_rpp_records.md) (5 shared connections)
- [parse_rpp_page](parse_rpp_page.md) (5 shared connections)
- [._tariff_demand_records](_tariff_demand_records.md) (4 shared connections)
- [._energy_entries](_energy_entries.md) (4 shared connections)
- [BaseScraper](BaseScraper.md) (3 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (2 shared connections)
- [.fetch_page](fetch_page.md) (2 shared connections)
- [oeb_distributor_for_registry](oeb_distributor_for_registry.md) (1 shared connections)
- [oeb_tariff.py](oeb_tariff.py.md) (1 shared connections)
- [TariffSheet](TariffSheet.md) (1 shared connections)
- [build_demand_records](build_demand_records.md) (1 shared connections)

## Source Files

- `scrapers/utilities/ontario_ldc.py`

## Audit Trail

- EXTRACTED: 64 (94%)
- INFERRED: 4 (6%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*