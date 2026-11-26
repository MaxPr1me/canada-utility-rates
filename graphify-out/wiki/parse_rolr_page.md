# parse_rolr_page

> 31 nodes

## Key Concepts

- **red_deer.py** (22 connections) — `scrapers/utilities/red_deer.py`
- **._try_live_scrape()** (12 connections) — `scrapers/utilities/red_deer.py`
- **.fetch_rendered_page()** (10 connections) — `scrapers/base.py`
- **RedDeerScraper** (8 connections) — `scrapers/utilities/red_deer.py`
- **parse_rolr_page()** (8 connections) — `scrapers/utilities/red_deer.py`
- **parse_schedule_a()** (8 connections) — `scrapers/utilities/red_deer.py`
- **parse_schedule_d()** (8 connections) — `scrapers/utilities/red_deer.py`
- **build_records()** (7 connections) — `scrapers/utilities/red_deer.py`
- **_sections()** (7 connections) — `scrapers/utilities/red_deer.py`
- **._discover_schedule_url()** (6 connections) — `scrapers/utilities/enmax_power.py`
- **_flat()** (6 connections) — `scrapers/utilities/red_deer.py`
- **parse_delivery_page()** (6 connections) — `scrapers/utilities/red_deer.py`
- **current_tariff_link()** (5 connections) — `scrapers/utilities/enmax_power.py`
- **._html()** (5 connections) — `scrapers/utilities/red_deer.py`
- **_iso()** (4 connections) — `scrapers/utilities/red_deer.py`
- **_quarter()** (3 connections) — `scrapers/utilities/red_deer.py`
- **.scrape()** (3 connections) — `scrapers/utilities/red_deer.py`
- **date** (3 connections)
- **.__init__()** (2 connections) — `scrapers/utilities/red_deer.py`
- **Return the fully-rendered HTML of a JS-heavy page via headless Chromium.…** (1 connections) — `scrapers/base.py`
- **Return the one ENMAX link labelled as the current distribution tariff, else…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **Static tariffs page first; the rendered page only if the link is absent or the…** (1 connections) — `scrapers/utilities/enmax_power.py`
- **red_deer.py — Scraper for the City of Red Deer Electric Light & Power…** (1 connections) — `scrapers/utilities/red_deer.py`
- **Effective date and the Administration Charge and application text per Regulated…** (1 connections) — `scrapers/utilities/red_deer.py`
- **The delivery page's charges by rate class, Local Access Fee, Balancing Pool and…** (1 connections) — `scrapers/utilities/red_deer.py`
- *... and 6 more nodes in this community*

## Relationships

- [BaseScraper](BaseScraper.md) (7 shared connections)
- [re](re.md) (7 shared connections)
- [TariffRecord](TariffRecord.md) (5 shared connections)
- [extract_pdf_pages](extract_pdf_pages.md) (5 shared connections)
- [parse_html](parse_html.md) (4 shared connections)
- [DocumentPage](DocumentPage.md) (4 shared connections)
- [ENMAXPowerScraper](ENMAXPowerScraper.md) (2 shared connections)
- [RateComponent](RateComponent.md) (2 shared connections)
- [CentraGasScraper](CentraGasScraper.md) (1 shared connections)
- [fortisalberta.py](fortisalberta.py.md) (1 shared connections)
- [FortisBCEnergyScraper](FortisBCEnergyScraper.md) (1 shared connections)
- [maritime_electric.py](maritime_electric.py.md) (1 shared connections)

## Source Files

- `scrapers/base.py`
- `scrapers/utilities/enmax_power.py`
- `scrapers/utilities/red_deer.py`

## Audit Trail

- EXTRACTED: 91 (96%)
- INFERRED: 4 (4%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*