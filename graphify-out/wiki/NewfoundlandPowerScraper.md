# NewfoundlandPowerScraper

> 29 nodes

## Key Concepts

- **NewfoundlandPowerScraper** (24 connections) — `scrapers/utilities/newfoundland_power.py`
- **._try_live_scrape()** (14 connections) — `scrapers/utilities/newfoundland_power.py`
- **._parse_pages()** (11 connections) — `scrapers/utilities/newfoundland_power.py`
- **._find_page()** (9 connections) — `scrapers/utilities/newfoundland_power.py`
- **._page_date()** (9 connections) — `scrapers/utilities/newfoundland_power.py`
- **._net_metering_domestic()** (7 connections) — `scrapers/utilities/newfoundland_power.py`
- **._primary_voltage_discount()** (7 connections) — `scrapers/utilities/newfoundland_power.py`
- **._prompt_payment()** (7 connections) — `scrapers/utilities/newfoundland_power.py`
- **._seasonal_domestic()** (7 connections) — `scrapers/utilities/newfoundland_power.py`
- **._annotate_base()** (7 connections) — `scrapers/utilities/newfoundland_power.py`
- **._curtailable()** (7 connections) — `scrapers/utilities/newfoundland_power.py`
- **._parse_ratebook()** (7 connections) — `scrapers/utilities/newfoundland_power.py`
- **._service_fees()** (6 connections) — `scrapers/utilities/newfoundland_power.py`
- **.scrape()** (6 connections) — `scrapers/utilities/newfoundland_power.py`
- **._parse_components()** (5 connections) — `scrapers/utilities/newfoundland_power.py`
- **._seed_data()** (5 connections) — `scrapers/utilities/newfoundland_power.py`
- **._rate_section()** (3 connections) — `scrapers/utilities/newfoundland_power.py`
- **add()** (3 connections) — `scrapers/utilities/newfoundland_power.py`
- **._slice()** (3 connections) — `scrapers/utilities/newfoundland_power.py`
- **Attach page-level provenance to the already parsed core components.** (1 connections) — `scrapers/utilities/newfoundland_power.py`
- **Parse optional/seasonal, discount and fee records; each fails independently.** (1 connections) — `scrapers/utilities/newfoundland_power.py`
- **Build a TariffRecord for each core rate class found in the RateBook text.** (1 connections) — `scrapers/utilities/newfoundland_power.py`
- **Return the charge-bearing detail section for a rate code, bounded to the next…** (1 connections) — `scrapers/utilities/newfoundland_power.py`
- **Return the text between *start_label* and the earliest of *end_labels*.** (1 connections) — `scrapers/utilities/newfoundland_power.py`
- **Extract fixed, demand and energy components from one rate-detail section.** (1 connections) — `scrapers/utilities/newfoundland_power.py`
- *... and 4 more nodes in this community*

## Relationships

- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (13 shared connections)
- [DocumentPage](DocumentPage.md) (11 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (10 shared connections)
- [BaseScraper](BaseScraper.md) (6 shared connections)
- [.fetch_page](fetch_page.md) (3 shared connections)
- [.__init__](__init__.md) (1 shared connections)
- [RateComponent](RateComponent.md) (1 shared connections)

## Source Files

- `scrapers/utilities/newfoundland_power.py`

## Audit Trail

- EXTRACTED: 98 (97%)
- INFERRED: 3 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*