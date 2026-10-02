# How to Add a New Utility Scraper

This guide walks through adding a scraper for a new Canadian utility,
step by step.

The current campaign is building-focused: include single-family/multi-unit residential,
commercial, institutional and building-related industrial service. Use official utility
eligibility, not an assumption that NECB 2025 defines tariff classes. Do not expand
farm/oil-field processes, irrigation, standalone lighting, wholesale or other non-building
services merely to complete a catalogue. Existing implementations remain reference data.

## 1. Research the utility

Before writing code, find these things:

- **Official rate page** — where rates are published on the utility's website
- **Rate schedule documents** — PDFs or pages with detailed tariff tables
- **Data format** — is it an HTML page, a PDF, a spreadsheet?
- **Rate structure** — flat? tiered? time-of-use? demand? mixed?
- **Customer classes** — residential, commercial, industrial, etc.
- **All charge components** — fixed fees, energy charges, delivery, transmission, riders, etc.
- **Relevant catalogue** — building-service class codes, zones/communities, voltage variants and optional products; document non-building exclusions and applicable special or closed-to-new-customer schedules.
- **Effective periods** — distinguish current approved schedules from archived, proposed or future schedules, including separately dated riders.

Write down the URLs you find — you'll need them.

## 2. Create the scraper file

Create a new Python file in `scrapers/utilities/`. Name it after the utility
using underscores and lowercase:

```
scrapers/utilities/my_utility.py
```

## 3. Write the scraper class

Use this template. `_try_live_scrape()` must call `mark_live_parsed()` on complete
parsed classes before combining them with any classes marked by `mark_fallback()`.

```python
"""
my_utility.py — Scraper for [Utility Name] ([Province]).

Official source:
  [URL to rate page]
"""

from __future__ import annotations

import logging
from typing import Optional

from scrapers.base import BaseScraper, TariffRecord, RateComponent

logger = logging.getLogger(__name__)


class MyUtilityScraper(BaseScraper):
    """Scrape [Utility Name] rates."""

    def __init__(self):
        super().__init__(utility_name="[Utility Name]", province="[XX]")

    def scrape(self) -> list[TariffRecord]:
        records = []

        # Try live scraping first, fall back to seed data
        live = self._try_live_scrape()
        if live:
            records.extend(live)
        else:
            self.logger.warning("Live scrape failed — using seed data")
            # Fallback: label seed values as unverified estimates (never shown as live).
            records.extend(self.mark_fallback(self._seed_data()))

        return records

    def _try_live_scrape(self) -> Optional[list[TariffRecord]]:
        try:
            html = self.fetch_page("https://example.com/rates")
            # Parse the HTML to extract rate data
            # ...
            return None  # Replace with parsed records
        except Exception as e:
            self.logger.warning("Could not fetch: %s", e)
            return None

    def _seed_data(self) -> list[TariffRecord]:
        """Known rate values as fallback."""
        return [
            TariffRecord(
                utility_name="[Utility Name]",
                province="[XX]",
                utility_type="electricity",  # or "gas"
                tariff_name="[Tariff Name]",
                tariff_code="[Code]",
                customer_class="residential",
                rate_structure="flat",
                effective_date="2024-01-01",
                source_url="https://...",
                confidence="unverified",
                components=[
                    RateComponent(
                        component_type="fixed",
                        component_name="Monthly Charge",
                        charge_value=10.00,
                        charge_unit="$/month",
                    ),
                    RateComponent(
                        component_type="energy",
                        component_name="Energy Charge",
                        charge_value=0.10,
                        charge_unit="$/kWh",
                    ),
                ],
            ),
        ]
```

## 4. Register the scraper

Add an entry to `data/sources/registry.json`:

```json
{
    "name": "[Utility Name]",
    "province": "[XX]",
    "utility_type": "electricity",
    "scraper_module": "scrapers.utilities.my_utility",
    "scraper_class": "MyUtilityScraper",
    "status": "active",
    "sources": [
        {
            "url": "https://...",
            "source_type": "html",
            "description": "Main rate page",
            "is_primary": true
        }
    ],
    "notes": ""
}
```

## 5. Test it

```bash
# Run deterministic tests; normal tests must not make live HTTP requests
python -m pytest -q

# Run in dry-run mode (no database changes)
python -m pipeline.run_scrape --utility "[Utility Name]" --dry-run
```

## 6. Verify the data

After scraping, export and check:

```bash
python -m pipeline.run_scrape --utility "[Utility Name]"
python -m pipeline.validate
python -m pipeline.export_json
```

Inspect the utility's exported classes, component counts, units, effective dates and
provenance, not merely the scrape success count. Repeat storage in a test database to
prove classes keep their own components and snapshots are appended without duplicates.
Never delete the real database to validate a parser change.

## Tips

- **Start with a source-derived fixture** — capture a small relevant HTML/PDF-text excerpt with the direct source URL, retrieval date and page/section. Seed data is optional fallback, not completion.
- **Be specific about components** — don't flatten into one "total" number
- **Include source URLs** — link to the exact page or PDF for each value
- **Set confidence** — high confidence alone is not live provenance. Fallback output must be unverified even if someone once checked its values manually.
- **Mark provenance** — wrap live-rebuilt records in `self.mark_live_parsed(...)` (or verify seed values against the official source with `self.verify_official_records(...)`), and always pass seed fallbacks through `self.mark_fallback(...)`. The site hides anything not marked live. Never present a seed default as a live rate.
- **Add notes** — explain anything unusual about the rate structure
- **Preserve class boundaries** — a broken PDF or missing row must not mark an incomplete class live or downgrade an independent complete class. Never blanket-stamp returned mixed live/seed records.
- **Preserve units** — kVA is not kW, and daily, monthly, seasonal and volume-tier charges must not be silently converted. Keep eligibility text when the schema has no matching unit-specific threshold field.
- **Preserve billing multipliers** — for bulk-metered buildings, a daily charge or tier allowance can apply per approved dwelling/room multiplier, not per account. Retain units such as `$/multiplier/day` and `kWh/day/multiplier`, occupancy conditions and billing-period proration. Distinguish a default multiplier of one from a grandfathered exception; an exception does not close the whole tariff to new customers. Do not turn a variable demand allowance into a fixed threshold or add minimum bills as extra charges. Conditional voltage bands are alternatives, not cumulative rebates.
- **Keep source configuration aligned** — update registry links and any URL constants the scraper actually fetches.
- **Keep component periods and alternatives explicit** — a combined tariff starts when all required components apply; retain each component's own date. Phase/amperage alternatives must not look cumulative. A separately published optional adjustment needs its base-plan applicability and must not look like a complete energy price. Missing required evidence (including current carbon applicability) rejects live output, rather than silently omitting the charge.
- **Validate authoritative exceptions** — do not substitute familiar TOU weekend rules for the printed schedule. Visually inspect unusual PDF wording or ambiguous columns, retain any explicit conditional/alternative basis, and test it. If full-document extraction stalls, select the needed sheets from reliable printed headings/footers before detailed extraction; do not replace source values with constants.

## Using parsing helpers for live scraping

The project provides helpers in `scrapers/utils/parsing.py` for implementing live HTML parsers:

- **`find_text_near_label(soup, label_text, search_radius=3)`** — finds numeric text near a labeled element (useful for label/value pairs in divs)
- **`extract_rate_from_text(text)`** — regex extraction of rate values from free-form text (`$X.XXXX/kWh`, `X.XX cents/kWh`, `$XX.XX/month`, `$X.XXXX/GJ`)
- **`detect_js_rendered(html)`** — detects JS-rendered pages where BeautifulSoup can't extract content
- **`find_pdf_links(soup, keywords=None, base_url=None)`** — extracts PDF `<a>` hrefs (including links with query strings), optionally filters by keywords, and resolves relative links when `base_url` is supplied
- **`verify_tariff_values(text, records, require_context=True)`** — checks known components in tariff/label/unit context; this verifies existing values rather than extracting replacements
- **`extract_pdf_pages()` / `DocumentPage`** — retain page numbers and join only the continuation pages belonging to a class; do not mistake a table-of-contents entry for a charge table

For PDF schedules, resolve links against `base_url`, download with `fetch_bytes()`,
and use page-aware extraction when layout/context matters. Rebuild records from
complete charge tables and mark those classes live. If verifying a stable known
structure instead, require contextual verification of every component. Missing or
ambiguous rows, unsupported units and unproven dates must fail closed, not inherit
seed values under a live marker.

## Change detection

When implementing a live parser, use `scrapers/utils/change_detection.py` to validate live-parsed data against seed values before accepting it:

Compare like-for-like, source-reviewed tariff structures. Old generic seed classes
are not a valid numeric baseline for newly discovered voltage, tier or demand classes.
Review structural changes against the official document and add fixtures; do not
disable safeguards merely to increase live counts.

```python
from scrapers.utils.change_detection import compare_to_seed, has_critical_alerts, log_change_alerts

alerts = compare_to_seed(live_records, self._seed_data())
log_change_alerts(alerts)

if has_critical_alerts(alerts):
    self.logger.warning("Critical drift detected — rejecting live data, falling back to seed")
    return None

return live_records
```

This prevents broken parsers from silently corrupting data. Changes are classified by severity:
- **info** (<5%): normal rate adjustments
- **warning** (5-30%): notable changes worth reviewing
- **critical** (>30%): likely a parsing error — live data is rejected

## Phase 5 provenance and fixture checklist

1. Save a small representative HTML, CSV, or extracted-text fixture; normal tests must not use the network.
2. Preserve page/section in `source_detail`, direct URLs on components, effective dates, signs, and published units (especially kW versus kVA).
3. A parser must return the complete expected structure or fail closed. For a stable known structure, `verify_official_records()` may prove all components contextually.
4. Send failed live output through `mark_fallback()`; fallback confidence is always `unverified` and its notes identify `seed_fallback`.
5. Add change/drift, partial-rejection, negative-credit, and date tests as applicable. Never verify a component merely because its number appears elsewhere in a PDF.
6. Mutate a fixture value and prove output follows the source; test missing columns, wrong units, future/missing dates, failed fetches and multi-class persistence/export.
7. Compare the returned code/class set with the building-relevant published catalogue. Document unsupported building classes and non-building exclusions separately; never invent rates to call a utility complete.
8. Update the README, maintainer guides and coverage/gap reports with actual test and source-check results. Fixture-tested but inaccessible sources remain blocked, not live-verified.
9. Preserve stable tariff names when adding coverage. Shared published codes can have distinct billing variants (for example, per-account and bulk per-unit service); keep those variants separate. A combined code record is valid only while every published column represented by it agrees.
10. Resolve dated interim/future tariff phases before using advertised prices. A product page may show a later pricing structure while the tariff has conditional interim rules. Preserve the condition and enrollment status explicitly; do not claim a participant's operational status is known. Keep plan identity stable across transitions so older phases remain history rather than duplicate current products.
