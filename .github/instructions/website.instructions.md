---
description: "Use when changing the static website under site/: index.html, css/, js/app.js (Rate Browser, Market Pricing, Compare), js/models.js (Representative Models), js/across-canada.js and the site/data/ JSON it reads. Covers the five views, hiding seed (estimated) rates by default, filterState Sets, the province-to-utility cascade, dedupe by effective date, formatCharge, Compare never totalling, the Ontario/Alberta market dashboard, the window.CanadaUtilityModels API and shared lazy load, safe DOM building, failure notices, the opt-in synthetic block and offline browser tests."
applyTo: "site/**"
---
# Static website

A plain HTML, CSS and JavaScript single-page app (Chart.js from a CDN), deployed to GitHub Pages and
reading `site/data/`. Model data rules, including Across-Canada's:
[representative-models.instructions.md](representative-models.instructions.md). Market file rules:
[market-data.instructions.md](market-data.instructions.md).

## Views

- Five views: **Rate Browser** (filters, cards, details), **Market Pricing**, **Representative
  Models**, **Across-Canada** (residential comparison) and **Compare** (two tariffs). Across-Canada and
  Compare stay separate.
- Test over HTTP (`python -m http.server --directory site 8000`); opening the HTML file directly does
  not reliably load the JSON.

## Provenance display

- Records with `provenance: "seed"` are hidden by default behind the labelled "Show estimated (not
  live-verified) rates" toggle and are labelled "Estimated" when shown (AGENTS.md safeguard).
- Cards show confidence indicators; details show source attribution. `.estimated-banner.hidden` hides
  empty notices.

## Rate Browser

- `filterState` uses JavaScript `Set`s: an empty set shows all; non-empty sets intersect.
- The province filter cascades into the utility filter: selecting a province hides other provinces'
  utilities.
- Deduplicate at load time: show only the most recent `effective_date` per utility + tariff.
- `formatCharge()` prefixes "$" only for units starting with "$" (negatives as "-$1.85/day"); %,
  fraction and other units stay plain. Value-less market components show "Variable". Values are
  HTML-escaped, and the details modal has one "Charge" column.

## Compare

- The no-build comparison state is an in-memory two-item array in `site/js/app.js`. It aligns exact
  type/name/unit keys and never totals them or calculates a bill.
- Manual check: serve the site, add two cards, open Compare, remove or replace either one, and check
  the sideways-scrolling table on a phone-sized screen.

## Market Pricing

- Accept only observed market files. `OBSERVED_MARKET_METHOD` gates the legacy and rolling Ontario
  methods; Ontario and Alberta have separate validators and methods, and Ontario's GA, era and gap
  assumptions never leak into Alberta. If a file was not built from real observed prices, hide the
  dashboard and show a "not available" notice.
- Ontario shows the rolling observed energy, GA and total, a source-attributed monthly table, a
  monthly chart with May 2025 marked and the observed-hours heatmap, where each bin shows its hour
  count. Explain the unrecoverable OEMP gap on the page.
- Keep the always-visible note that market-billed customers now pay the OEMP plus GA.
- If the Chart.js CDN fails, the tables, heatmaps and region switching keep working.

## Representative Models (`site/js/models.js`)

- `window.CanadaUtilityModels` is a frozen API: a cached, retryable `load`, money/date/source-link
  helpers and labels. Representative Models and Across-Canada share one lazy fetch of
  `representative_models.json`; neither rewrites the export.
- Default view (owner decision 2026-10-15): Ontario residential TOU at the typical level (1,000 kWh),
  with cascading selectors, without/with-tax columns, a table and CSS range bars (no new charts), then
  contributors and outliers, taxes, method, coverage and exclusions. Keep the contributor nouns and the
  excluded-market-charge notes.
- The synthetic 7E block is opt-in ("Show illustrative all-in estimate (synthetic load profile)"): off
  by default and reset when the model changes, with its warning, SYNTHETIC badge and fixed caveat.
- Render `fixed_charge_variants` as always-visible reference assumptions for every supplied level,
  plus each contributor's chosen component. They describe the example customer, not the visitor's
  actual service or eligibility. Older exports may omit these fields.
- Show the historical market benchmarks apart from the delivery-only table, never in place of it.
- Build the model views with `createElement`/`textContent` and allow only http(s) links. A missing or
  broken file shows a notice without breaking the other views.

## Across-Canada (`site/js/across-canada.js`, `site/css/across-canada.css`)

- A scrollable national table and grouped horizontal CSS bars by province, with a stable province hue
  and related shades per rate structure, for desktop and phone screens.

## Tests

- Browser tests run offline: every request is routed to frozen or synthetic local data.
