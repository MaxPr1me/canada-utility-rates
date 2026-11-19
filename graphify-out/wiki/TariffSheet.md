# TariffSheet

> 12 nodes

## Key Concepts

- **TariffSheet** (10 connections) — `scrapers/utils/oeb_tariff.py`
- **parse_tariff_zones()** (8 connections) — `scrapers/utils/oeb_tariff.py`
- **_split_page()** (8 connections) — `scrapers/utils/oeb_tariff.py`
- **_approved_copies()** (7 connections) — `scrapers/utils/oeb_tariff.py`
- **_cover_case_number()** (7 connections) — `scrapers/utils/oeb_tariff.py`
- **_iso()** (4 connections) — `scrapers/utils/oeb_tariff.py`
- **.classification()** (3 connections) — `scrapers/utils/oeb_tariff.py`
- **proposed()** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Parse every rate zone in a (possibly multi-zone) tariff document.** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Strip the repeated OEB page header; return header facts and body lines.** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Drop tariff copies printed under a "Proposed/Draft Tariff of Rates and Charges"…** (1 connections) — `scrapers/utils/oeb_tariff.py`
- **Case number from the Schedule A cover immediately before the tariff, only if…** (1 connections) — `scrapers/utils/oeb_tariff.py`

## Relationships

- [oeb_tariff.py](oeb_tariff.py.md) (7 shared connections)
- [parse_tariff_pages](parse_tariff_pages.md) (5 shared connections)
- [DocumentPage](DocumentPage.md) (4 shared connections)
- [build_demand_records](build_demand_records.md) (3 shared connections)
- [class_loss_factors](class_loss_factors.md) (1 shared connections)
- [close_class](close_class.md) (1 shared connections)
- [_dedupe_classifications](_dedupe_classifications.md) (1 shared connections)
- [Classification](Classification.md) (1 shared connections)
- [parse_bill_data](parse_bill_data.md) (1 shared connections)

## Source Files

- `scrapers/utils/oeb_tariff.py`

## Audit Trail

- EXTRACTED: 34 (89%)
- INFERRED: 4 (11%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*