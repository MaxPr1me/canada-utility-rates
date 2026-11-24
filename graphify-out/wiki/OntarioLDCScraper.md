# OntarioLDCScraper

> 27 nodes

## Key Concepts

- **OntarioLDCScraper** (30 connections) — `scrapers/utilities/ontario_ldc.py`
- **._try_live_scrape()** (16 connections) — `scrapers/utilities/ontario_ldc.py`
- **._build_rpp_records()** (7 connections) — `scrapers/utilities/ontario_ldc.py`
- **.scrape()** (7 connections) — `scrapers/utilities/ontario_ldc.py`
- **._xml_cross_check()** (6 connections) — `scrapers/utilities/ontario_ldc.py`
- **._fetch_oeb()** (5 connections) — `scrapers/utilities/ontario_ldc.py`
- **._fetch_tariff_pages()** (5 connections) — `scrapers/utilities/ontario_ldc.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/ontario_ldc.py`
- **._record_absent_classes()** (4 connections) — `scrapers/utilities/ontario_ldc.py`
- **._rpp_components()** (4 connections) — `scrapers/utilities/ontario_ldc.py`
- **._class_rejected()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._copy_components()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._drop_duplicate_demand()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._external_demand_records()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **.set_demand_records()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._xml_pairs()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **energy()** (2 connections) — `scrapers/utilities/ontario_ldc.py`
- **._drop_duplicate_labels()** (2 connections) — `scrapers/utilities/ontario_ldc.py`
- **._rpp_tariff_notes()** (2 connections) — `scrapers/utilities/ontario_ldc.py`
- **make_vol_delivery()** (2 connections) — `scrapers/utilities/ontario_ldc.py`
- **one()** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **Data-driven scraper for any Ontario electricity LDC. All Ontario LDCs share the…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **Supply externally built GS >= 50 kW records that replace the GS-D seeds. The…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **A configured tariff rejected a class of this group (not a whole sheet).** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **Build live records from the LDC's approved tariff(s) and OEB RPP prices.…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- *... and 2 more nodes in this community*

## Relationships

- [TariffRecord](TariffRecord.md) (8 shared connections)
- [._energy_entries](_energy_entries.md) (7 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (6 shared connections)
- [ontario_ldc.py](ontario_ldc.py.md) (4 shared connections)
- [._load_sheets](_load_sheets.md) (4 shared connections)
- [BaseScraper](BaseScraper.md) (2 shared connections)
- [oeb_distributor_for_registry](oeb_distributor_for_registry.md) (1 shared connections)
- [validate_energy_charges](validate_energy_charges.md) (1 shared connections)
- [ntpc.py](ntpc.py.md) (1 shared connections)
- [oeb_tariff.py](oeb_tariff.py.md) (1 shared connections)
- [build_demand_records](build_demand_records.md) (1 shared connections)
- [RateComponent](RateComponent.md) (1 shared connections)

## Source Files

- `scrapers/utilities/ontario_ldc.py`

## Audit Trail

- EXTRACTED: 76 (95%)
- INFERRED: 4 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*