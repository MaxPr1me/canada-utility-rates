# build_demand_records

> 18 nodes

## Key Concepts

- **build_demand_records()** (23 connections) — `scrapers/utils/oeb_tariff.py`
- **_norm_name()** (12 connections) — `scrapers/utils/oeb_tariff.py`
- **classify_classification()** (11 connections) — `scrapers/utils/oeb_tariff.py`
- **residential_demand_floor()** (7 connections) — `scrapers/utils/oeb_tariff.py`
- **_demand_bounds()** (5 connections) — `scrapers/utils/oeb_tariff.py`
- **exclusion_reason()** (5 connections) — `scrapers/utils/oeb_tariff.py`
- **_name_bounds()** (5 connections) — `scrapers/utils/oeb_tariff.py`
- **_num()** (5 connections) — `scrapers/utils/oeb_tariff.py`
- **_selected()** (5 connections) — `scrapers/utils/oeb_tariff.py`
- **_today_iso()** (4 connections) — `scrapers/utils/oeb_tariff.py`
- **date** (4 connections)
- **connection_not_printed_note()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **_tariff_code()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **kW floor of a residential class billed on a demand basis; ``None`` unless every…** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Categorise a classification for record builders; one of ``CLASS_CATEGORIES``.…** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Why an "excluded" class is never built (``None`` for other categories).** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Build demand-billed delivery records, failing closed per classification.…** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **kW bounds printed in a class name; an inclusive "... to 4,999" upper bound…** (1 connections) — `scrapers/utils/oeb_tariff.py`

## Relationships

- [oeb_tariff.py](oeb_tariff.py.md) (14 shared connections)
- [Classification](Classification.md) (9 shared connections)
- [TariffSheet](TariffSheet.md) (3 shared connections)
- [parse_tariff_pages](parse_tariff_pages.md) (3 shared connections)
- [close_class](close_class.md) (2 shared connections)
- [class_loss_factors](class_loss_factors.md) (2 shared connections)
- [._energy_entries](_energy_entries.md) (2 shared connections)
- [._tariff_demand_records](_tariff_demand_records.md) (1 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (1 shared connections)
- [OntarioLDCScraper](OntarioLDCScraper.md) (1 shared connections)
- [_dedupe_classifications](_dedupe_classifications.md) (1 shared connections)

## Source Files

- `scrapers/utils/oeb_tariff.py`

## Audit Trail

- EXTRACTED: 67 (99%)
- INFERRED: 1 (1%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*