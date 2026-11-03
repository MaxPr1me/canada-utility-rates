---
description: "Use when writing or changing any utility scraper, parser, seed fallback, source URL, registry entry or parser test fixture: scrapers/base.py, scrapers/registry.py, scrapers/utils/ (parsing, change_detection, validation, logging_config), scrapers/utilities/*.py, data/sources/registry.json, data/inventory/utilities.json, tests/fixtures/. Covers provenance labels (live parsed, officially verified, seed fallback), fail-closed parsing, structural drift, change detection, component dates, conditional and value-less market components, the dead-URL guard, merged/retired entries, snapshots and logging."
applyTo: "scrapers/**, data/sources/**, data/inventory/**, tests/fixtures/**"
---
# Scrapers, sources and provenance

Generic rules for every utility. Utility-specific rules live in the area files:
[Ontario electricity](ontario-electricity.instructions.md),
[Alberta electricity](alberta-electricity.instructions.md),
[other provinces and territories](regional-utilities.instructions.md) and
[gas](gas-utilities.instructions.md). Per-utility class scope, exclusions and remaining gaps are in
the [gap report](../../docs/live_parser_gap_report.md); the current queue is in the
[coverage matrix](../../docs/phase5_completion_matrix.md), whose active queue supersedes the
historical checkpoint instructions it retains. To add a utility, follow
[adding-a-utility.md](../../docs/adding-a-utility.md).

## Structure

- Every scraper in `scrapers/utilities/` inherits `scrapers/base.py:BaseScraper` and returns
  `list[TariffRecord]`. Shared fetching and verification belong in `BaseScraper` and
  `scrapers/utils/`; each utility module keeps its own tariff interpretation.
- Try the live official source first. Hardcoded `SEED_*` values are only a fallback safety net
  (AGENTS.md safeguard: never present them as live).
- Scope follows AGENTS.md's building-energy focus. Keep completed reference parsers, data and all
  snapshots for services that are now out of scope; do not delete them.

## Provenance and confidence

- **Live parsed:** the scraper read the current official page or document and rebuilt the tariff
  from it. Stamp it with `mark_live_parsed()` (`Provenance: live_parsed`).
- **Officially verified:** the tariff's structure is already known and every component, with its
  tariff, label and unit, was proved in a current official document
  (`Provenance: officially_verified`). `BaseScraper.verify_official_records()` is the shared strict
  HTML/PDF component verifier. Finding the same number somewhere is not enough.
- **Seed fallback (estimate):** when fetching fails or a schedule changes shape, call
  `mark_fallback()`. It recursively sets every tariff and component to `confidence: unverified` and
  adds `Provenance: seed_fallback` to the notes. Never raise this confidence by hand.
- `pipeline/export_json.py:derive_provenance()` exports `provenance: "live"` only for the
  `officially_verified` and `live_parsed` markers; everything else is `"seed"`, which the site hides
  by default.
- `confidence` on tariffs and components is `high`, `medium`, `low` or `unverified`.
- A class that was read completely can stay live when another class of the same utility fails, but
  never label a mixed list of live and estimated records entirely live.
- A generic verifier fixture or a fallback-only run does not prove a working live parser; inspect a
  targeted live dry run.

## Fail closed

- "Fail closed" means a doubtful source is rejected instead of guessed. A missing carbon-charge
  source cannot be hidden under a live label.
- A required cross-check source (named in the area files) that is missing, unreadable or in
  disagreement fails the affected records closed.
- "Structural drift" in the logs names components that could not be verified: open the registry
  URL, find the current approved schedule, update that utility's interpretation and test fixture,
  then run its targeted dry run.
- `scrapers/utils/change_detection.py:compare_to_seed()` pairs live-parsed records with seed data and
  grades each change: info below 5%, warning 5-30%, critical above 30%. A critical change (likely a
  parsing bug) rejects the live data and falls back to the seed.
- Missing known classes keep their labelled seed fallbacks. Record newly discovered unsupported
  classes as gaps; never invent fallback rates for them.
- A utility without seed data returns no records when its sources fail.
- `scrapers/utils/validation.py` checks data quality after every scrape (`python -m pipeline.validate`).

## Components and dates

- Each component keeps its own date; a tariff built from parts with different dates takes the
  latest required part's date.
- Conditional, optional, alternative and source-blocked prices are not charges that every customer
  pays. The model engine (`component_exclusion()` in `pipeline/representative_models.py`) recognizes
  them by `sub_component` (`conditional`, `conditional_credit`, `alternative`,
  `conditional alternative`, `optional`) or by notes that begin, after the `Provenance: ...` marker,
  with "Conditional", "Alternative" or "Optional".
- A price that follows a market is a value-less component: `charge_value=None` plus
  `market_reference` and `market_source_url`; the site shows "Variable". Never give it a made-up
  value.
- Keep different kinds of sources separate (Alberta wires, Alberta default retail, AESO, gas and
  northern utilities), with their published classes, communities, tiers and units.

## Completeness

- Source-check dates, live-record counts and catalogue completion are different facts. Multi-class
  coverage is not catalogue completeness.
- **Completing a utility** means auditing its building-relevant standard published classes, not just
  replacing existing estimates or completing every unrelated service.
- Some products are left out on purpose; record exclusions and remaining gaps in the gap report and
  the coverage matrix.

## Registry and source URLs

- `data/sources/registry.json` is the system of record: each utility's source URLs, format, scraper
  module and status. `data/inventory/utilities.json` is the reference list of all Canadian
  utilities, including unscraped ones. `data/excel/old_urls.xlsm` is audit-only: no scraper reads it.
- Choose sources in the order of AGENTS.md's "Source URL Management" section.
- When a source moves, update the registry, the scraper's URL constant and the fixtures in the same
  change. Add the old address to `DENYLIST` in `tests/test_source_urls.py` with the check date, the
  HTTP status seen and what to cite instead. The guard scans every module in `scrapers/utilities/`
  and `scrapers/utils/`, every registry string and the reference files
  `data/inventory/utilities.json` and `site/data/market_structure_notes.json`.
- A dead seed citation with no archived copy showing its values is kept with a "page removed
  (checked YYYY-MM-DD)" note and listed in `KEPT_DEAD` with the reason; it must still be cited by a
  scraper module and must not also be denied (owner decision 2026-10-30).
- `scrapers/registry.py:get_active_utilities()` runs only `active` and `partial` entries. `merged`
  entries (with a `merged_into` successor) and `retired` entries are skipped by monthly runs but keep
  their history; never delete them.

## Fetching and parsing

- JS-rendered pages: `BaseScraper.fetch_rendered_page()` uses headless Chromium
  (`python -m playwright install chromium`).
- `scrapers/utils/parsing.py` provides `DocumentPage`, page-aware fail-closed PDF extraction and
  section selection, CSV/XLSX readers, content hashing, effective-date/unit/currency normalization
  and contextual verification, plus `find_text_near_label()`, `extract_rate_from_text()`,
  `detect_js_rendered()`, query-safe and relative-aware `find_pdf_links()` and strict
  `verify_tariff_values()` (proves fallback values still appear in an official schedule).

## History

- Every successful stored scrape adds a copy of each tariff to `historical_snapshots`. Never
  overwrite or delete snapshots or old effective-date versions; the website shows the latest version
  of each tariff.
- Snapshot serialization (`pipeline/run_scrape.py:canonical_snapshot()`) is canonical JSON with
  sorted component dictionaries: the fingerprint ignores component order but changes when values,
  units, tiers, dates or structure change. `pipeline/diff_report.py:diff_runs()` compares the
  append-only per-run snapshots.

## Logging

- `setup_logging()` (`scrapers/utils/logging_config.py`) is idempotent and keeps pdfminer/pdfplumber
  at WARNING: per-token pdfminer DEBUG once grew `logs/scrape.log` to about 10 GB and stalled the
  test suite. The log rotates at 10 MB with 3 backups; it is a git-ignored debug diary that nothing
  reads, so deleting it is safe.

## Fixtures

- `tests/fixtures/` holds official HTML/PDF-text excerpts with their source URLs and page/section
  details for repeatable parser tests. A fixture covers only the classes and conditions it saves; it
  does not prove the utility's catalogue is complete.
