# compare_to_seed

> 12 nodes

## Key Concepts

- **compare_to_seed()** (14 connections) — `scrapers/utils/change_detection.py`
- **ChangeAlert** (6 connections) — `scrapers/utils/change_detection.py`
- **_compare_components()** (6 connections) — `scrapers/utils/change_detection.py`
- **_pair_records()** (5 connections) — `scrapers/utils/change_detection.py`
- **_match_key()** (4 connections) — `scrapers/utils/change_detection.py`
- **_classify_severity()** (3 connections) — `scrapers/utils/change_detection.py`
- **Compare individual rate components between a live and seed record.** (1 connections) — `scrapers/utils/change_detection.py`
- **Compare live-parsed tariff records against seed/fallback data. Returns a list…** (1 connections) — `scrapers/utils/change_detection.py`
- **A single detected difference between live and seed data.** (1 connections) — `scrapers/utils/change_detection.py`
- **Classify the severity of a change based on % and absolute value.** (1 connections) — `scrapers/utils/change_detection.py`
- **Build a matching key for pairing live records to seed records. Uses tariff_code…** (1 connections) — `scrapers/utils/change_detection.py`
- **Pair live and seed records by matching key. Returns list of (live, seed)…** (1 connections) — `scrapers/utils/change_detection.py`

## Relationships

- [BaseScraper](BaseScraper.md) (8 shared connections)
- [._parse_commercial](_parse_commercial.md) (4 shared connections)
- [TariffRecord](TariffRecord.md) (4 shared connections)
- [BCHydroScraper](BCHydroScraper.md) (1 shared connections)
- [._try_live_scrape](_try_live_scrape.md) (1 shared connections)
- [NBPowerScraper](NBPowerScraper.md) (1 shared connections)
- [parsing.py](parsing.py.md) (1 shared connections)

## Source Files

- `scrapers/utils/change_detection.py`

## Audit Trail

- EXTRACTED: 28 (88%)
- INFERRED: 4 (12%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*