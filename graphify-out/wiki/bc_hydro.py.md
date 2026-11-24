# bc_hydro.py

> 22 nodes

## Key Concepts

- **bc_hydro.py** (18 connections) — `scrapers/utilities/bc_hydro.py`
- **change_detection.py** (18 connections) — `scrapers/utils/change_detection.py`
- **._try_live_scrape()** (15 connections) — `scrapers/utilities/manitoba_hydro.py`
- **compare_to_seed()** (14 connections) — `scrapers/utils/change_detection.py`
- **has_critical_alerts()** (11 connections) — `scrapers/utils/change_detection.py`
- **log_change_alerts()** (11 connections) — `scrapers/utils/change_detection.py`
- **ChangeAlert** (6 connections) — `scrapers/utils/change_detection.py`
- **_compare_components()** (6 connections) — `scrapers/utils/change_detection.py`
- **_pair_records()** (5 connections) — `scrapers/utils/change_detection.py`
- **_match_key()** (4 connections) — `scrapers/utils/change_detection.py`
- **_classify_severity()** (3 connections) — `scrapers/utils/change_detection.py`
- **bc_hydro.py — Scraper for BC Hydro electricity rates (British Columbia). BC…** (1 connections) — `scrapers/utilities/bc_hydro.py`
- **Attempt to parse rates from the live Manitoba Hydro website.** (1 connections) — `scrapers/utilities/manitoba_hydro.py`
- **change_detection.py — Compare live-parsed tariff records against seed data.…** (1 connections) — `scrapers/utils/change_detection.py`
- **Compare individual rate components between a live and seed record.** (1 connections) — `scrapers/utils/change_detection.py`
- **Compare live-parsed tariff records against seed/fallback data. Returns a list…** (1 connections) — `scrapers/utils/change_detection.py`
- **Log each ChangeAlert at the appropriate severity level.** (1 connections) — `scrapers/utils/change_detection.py`
- **Check if any alerts are critical (likely parsing errors).** (1 connections) — `scrapers/utils/change_detection.py`
- **A single detected difference between live and seed data.** (1 connections) — `scrapers/utils/change_detection.py`
- **Classify the severity of a change based on % and absolute value.** (1 connections) — `scrapers/utils/change_detection.py`
- **Build a matching key for pairing live records to seed records. Uses tariff_code…** (1 connections) — `scrapers/utils/change_detection.py`
- **Pair live and seed records by matching key. Returns list of (live, seed)…** (1 connections) — `scrapers/utils/change_detection.py`

## Relationships

- [BaseScraper](BaseScraper.md) (19 shared connections)
- [TariffRecord](TariffRecord.md) (11 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (7 shared connections)
- [._parse_commercial](_parse_commercial.md) (4 shared connections)
- [RateComponent](RateComponent.md) (4 shared connections)
- [run_scrape.py](run_scrape.py.md) (2 shared connections)
- [.fetch_page](fetch_page.md) (1 shared connections)
- [ntpc.py](ntpc.py.md) (1 shared connections)
- [.mark_live_parsed](mark_live_parsed.md) (1 shared connections)
- [re](re.md) (1 shared connections)
- [NovaScotiaPowerScraper](NovaScotiaPowerScraper.md) (1 shared connections)
- [DocumentPage](DocumentPage.md) (1 shared connections)

## Source Files

- `scrapers/utilities/bc_hydro.py`
- `scrapers/utilities/manitoba_hydro.py`
- `scrapers/utils/change_detection.py`

## Audit Trail

- EXTRACTED: 84 (95%)
- INFERRED: 4 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*