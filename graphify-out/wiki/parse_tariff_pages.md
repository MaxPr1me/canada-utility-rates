# parse_tariff_pages

> 23 nodes

## Key Concepts

- **parse_tariff_pages()** (22 connections) — `scrapers/utils/oeb_tariff.py`
- **TariffSheet** (10 connections) — `scrapers/utils/oeb_tariff.py`
- **parse_tariff_zones()** (8 connections) — `scrapers/utils/oeb_tariff.py`
- **_split_page()** (8 connections) — `scrapers/utils/oeb_tariff.py`
- **_approved_copies()** (7 connections) — `scrapers/utils/oeb_tariff.py`
- **_cover_case_number()** (7 connections) — `scrapers/utils/oeb_tariff.py`
- **_dedupe_classifications()** (6 connections) — `scrapers/utils/oeb_tariff.py`
- **add_line()** (5 connections) — `scrapers/utils/oeb_tariff.py`
- **_iso()** (4 connections) — `scrapers/utils/oeb_tariff.py`
- **_today_iso()** (4 connections) — `scrapers/utils/oeb_tariff.py`
- **date** (4 connections)
- **extend_tail()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **flush_allowance()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **start_class()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **proposed()** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **single()** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **start_charges()** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Parse every rate zone in a (possibly multi-zone) tariff document.** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Strip the repeated OEB page header; return header facts and body lines.** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Drop tariff copies printed under a "Proposed/Draft Tariff of Rates and Charges"…** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Identical repeated classes collapse to the first; differing repeats are…** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Case number from the Schedule A cover immediately before the tariff, only if…** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Parse OEB tariff pages for one distributor (and, if given, one rate zone). Non-…** (1 connections) — `scrapers/utils/oeb_tariff.py`

## Relationships

- [oeb_tariff.py](oeb_tariff.py.md) (18 shared connections)
- [build_demand_records](build_demand_records.md) (7 shared connections)
- [DocumentPage](DocumentPage.md) (5 shared connections)
- [class_loss_factors](class_loss_factors.md) (2 shared connections)
- [OntarioLDCScraper](OntarioLDCScraper.md) (1 shared connections)

## Source Files

- `scrapers/utils/oeb_tariff.py`

## Audit Trail

- EXTRACTED: 63 (93%)
- INFERRED: 5 (7%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*