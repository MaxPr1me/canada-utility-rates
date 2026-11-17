# parse_tariff_pages

> 12 nodes

## Key Concepts

- **parse_tariff_pages()** (22 connections) — `scrapers/utils/oeb_tariff.py`
- **add_line()** (5 connections) — `scrapers/utils/oeb_tariff.py`
- **extend_tail()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **flush_allowance()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **start_class()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **_split_footnotes()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **_tail_split()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **single()** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **start_charges()** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Split "<previous label tail>) <new label>" glued together by row joining.** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Split a numbered NOTES section ("1. ... 2. ..." or "1) ... 2) ...") into {"1":…** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Parse OEB tariff pages for one distributor (and, if given, one rate zone). Non-…** (1 connections) — `scrapers/utils/oeb_tariff.py`

## Relationships

- [TariffSheet](TariffSheet.md) (5 shared connections)
- [oeb_tariff.py](oeb_tariff.py.md) (5 shared connections)
- [build_demand_records](build_demand_records.md) (3 shared connections)
- [close_class](close_class.md) (2 shared connections)
- [Classification](Classification.md) (1 shared connections)
- [_dedupe_classifications](_dedupe_classifications.md) (1 shared connections)
- [class_loss_factors](class_loss_factors.md) (1 shared connections)
- [DocumentPage](DocumentPage.md) (1 shared connections)

## Source Files

- `scrapers/utils/oeb_tariff.py`

## Audit Trail

- EXTRACTED: 32 (97%)
- INFERRED: 1 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*