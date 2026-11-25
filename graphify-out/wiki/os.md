# os

> 27 nodes

## Key Concepts

- **hashlib** (25 connections)
- **os** (25 connections)
- **pull_history_db.py** (18 connections) — `scripts/pull_history_db.py`
- **pull()** (11 connections) — `scripts/pull_history_db.py`
- **requests** (11 connections)
- **download()** (9 connections) — `scripts/pull_history_db.py`
- **PullError** (6 connections) — `scripts/pull_history_db.py`
- **canonical_snapshot()** (6 connections) — `pipeline/run_scrape.py`
- **store_results()** (6 connections) — `pipeline/run_scrape.py`
- **resolve_asset()** (6 connections) — `scripts/pull_history_db.py`
- **file_sha256()** (4 connections) — `scripts/pull_history_db.py`
- **Path** (4 connections)
- **shutil** (4 connections)
- **tempfile** (4 connections)
- **backup_path()** (3 connections) — `scripts/pull_history_db.py`
- **content_hash()** (3 connections) — `scrapers/utils/parsing.py`
- **main()** (3 connections) — `scripts/pull_history_db.py`
- **Connection** (1 connections)
- **Exception** (1 connections)
- **Serialize a semantic tariff deterministically for historical hashing. Component…** (1 connections) — `pipeline/run_scrape.py`
- **Store scraped tariff records into the database. Returns the number of records…** (1 connections) — `pipeline/run_scrape.py`
- **Return a stable SHA-256 hash for downloaded official content.** (1 connections) — `scrapers/utils/parsing.py`
- **Download the history database written by CI into a read-only local mirror. The…** (1 connections) — `scripts/pull_history_db.py`
- **Download, verify and (unless dry_run) install the release asset at ``output``;…** (1 connections) — `scripts/pull_history_db.py`
- **The release asset could not be found, downloaded or verified.** (1 connections) — `scripts/pull_history_db.py`
- *... and 2 more nodes in this community*

## Relationships

- [json](json.md) (9 shared connections)
- [graphify_hook.py](graphify_hook.py.md) (8 shared connections)
- [BaseScraper](BaseScraper.md) (6 shared connections)
- [build_alberta_market.py](build_alberta_market.py.md) (6 shared connections)
- [run_scrape.py](run_scrape.py.md) (5 shared connections)
- [preserve_ieso_reports.py](preserve_ieso_reports.py.md) (5 shared connections)
- [check_db_history.py](check_db_history.py.md) (4 shared connections)
- [archive_ontario_price.py](archive_ontario_price.py.md) (4 shared connections)
- [TariffRecord](TariffRecord.md) (2 shared connections)
- [re](re.md) (2 shared connections)
- [archetype_profiles.py](archetype_profiles.py.md) (2 shared connections)
- [io](io.md) (2 shared connections)

## Source Files

- `pipeline/run_scrape.py`
- `scrapers/utils/parsing.py`
- `scripts/pull_history_db.py`

## Audit Trail

- EXTRACTED: 111 (98%)
- INFERRED: 2 (2%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*