# OntarioLDCScraper

> 21 nodes

## Key Concepts

- **OntarioLDCScraper** (30 connections) — `scrapers/utilities/ontario_ldc.py`
- **._try_live_scrape()** (16 connections) — `scrapers/utilities/ontario_ldc.py`
- **._build_rpp_records()** (7 connections) — `scrapers/utilities/ontario_ldc.py`
- **.scrape()** (7 connections) — `scrapers/utilities/ontario_ldc.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/ontario_ldc.py`
- **._record_absent_classes()** (4 connections) — `scrapers/utilities/ontario_ldc.py`
- **._rpp_components()** (4 connections) — `scrapers/utilities/ontario_ldc.py`
- **._class_rejected()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._copy_components()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._drop_duplicate_demand()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **._external_demand_records()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **.set_demand_records()** (3 connections) — `scrapers/utilities/ontario_ldc.py`
- **energy()** (2 connections) — `scrapers/utilities/ontario_ldc.py`
- **._drop_duplicate_labels()** (2 connections) — `scrapers/utilities/ontario_ldc.py`
- **._rpp_tariff_notes()** (2 connections) — `scrapers/utilities/ontario_ldc.py`
- **make_vol_delivery()** (2 connections) — `scrapers/utilities/ontario_ldc.py`
- **Data-driven scraper for any Ontario electricity LDC. All Ontario LDCs share the…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **Supply externally built GS >= 50 kW records that replace the GS-D seeds. The…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **A configured tariff rejected a class of this group (not a whole sheet).** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **Build live records from the LDC's approved tariff(s) and OEB RPP prices.…** (1 connections) — `scrapers/utilities/ontario_ldc.py`
- **An accepted approved tariff that publishes no class of a group counts as that…** (1 connections) — `scrapers/utilities/ontario_ldc.py`

## Relationships

- [TariffRecord](TariffRecord.md) (9 shared connections)
- [._xml_cross_check](_xml_cross_check.md) (6 shared connections)
- [._energy_entries](_energy_entries.md) (6 shared connections)
- [RateComponent](RateComponent.md) (6 shared connections)
- [parse_bill_data](parse_bill_data.md) (4 shared connections)
- [ontario_ldc.py](ontario_ldc.py.md) (2 shared connections)
- [BaseScraper](BaseScraper.md) (1 shared connections)
- [oeb_distributor_for_registry](oeb_distributor_for_registry.md) (1 shared connections)
- [validate_energy_charges](validate_energy_charges.md) (1 shared connections)
- [build_demand_records](build_demand_records.md) (1 shared connections)
- [parse_rpp_page](parse_rpp_page.md) (1 shared connections)
- [.fetch_page](fetch_page.md) (1 shared connections)

## Source Files

- `scrapers/utilities/ontario_ldc.py`

## Audit Trail

- EXTRACTED: 68 (97%)
- INFERRED: 2 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*