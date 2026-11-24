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
- Dated components (owner decision 34, 2026-11-23): a component with an `end_date` shows its period
  in the details and Compare ("Nov 1-30, 2026", "until ..."), and an "Ended" tag (`.ended-badge`) on
  the card, in the details and in Compare once the end date is before the visitor's own date (the end
  date is the last day the price applies). Ended prices are never hidden: they stay until a newer
  record is stored.

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
  with cascading selectors, before/with-tax-and-rebates columns, a table and CSS range bars (no new charts), then
  contributors and outliers, taxes, method, coverage and exclusions. Keep the contributor nouns and the
  excluded-market-charge notes.
- Both model views label tax-inclusive totals as "with tax and rebates". The shared
  `rebateExplanation()` uses applied rebate lines and published medians to explain a lower total
  beside the prices; never infer a rebate from a lower number alone or recalculate tax in the browser.
- Gas models show levels in each utility's native unit (`quantity` + `unit`: m³ or GJ, never
  converted). Every level with a `role` gets a Reference or Sensitivity tag (residential electricity
  too since 7D-2: 1,000 kWh is the reference level, decision 29); "Typical" remains only for an older
  file without roles. The reference level is highlighted. Commercial gas models (7D-2) add a "Class
  used" column to the contributors table (the tariff codes of the records used at the selected level,
  and the elective choice with both costs) and a "Class used at each level" note with the peak-month
  factor and elective classes. Across-Canada keeps filtering to residential electricity.
- The synthetic 7E block is opt-in ("Show illustrative all-in estimate (synthetic load profile)"): off
  by default and reset when the model changes, with its warning, SYNTHETIC badge and fixed caveat.
- Render `fixed_charge_variants` as always-visible reference assumptions for every supplied level,
  plus each contributor's chosen component. They describe the example customer, not the visitor's
  actual service or eligibility. Older exports may omit these fields.
- Show the historical market benchmarks apart from the delivery-only table, never in place of it.
- Territorial models (method 7T-1, owner decisions 2026-11-24): an "Interim rates: ..." badge
  (`#models-interim`) beside the state badge when `model.interim` lists utilities; under the main
  table, an "After automatic subsidies (before tax)" table read from `level.after_subsidy` (or the
  model's reason when `subsidies.after_subsidy` is false, as for Nunavut), the tax note and the
  applied and not-applied subsidies; an after-subsidy column in the contributors table; the joint
  rate book and the reviewed percentage riders in the notes. The after-subsidy figure never replaces
  the before-subsidy table and is never taxed or recalculated in the browser.
- Load `model_change_history.json` independently of the shared model-data promise. Its generation,
  as-of, method, model/level identities, usage, costs and recorded last-change dates must match;
  missing or invalid history gets a retryable notice without hiding prices or breaking Across-Canada.
- The selected model's **Last changed** is a meaningful recorded change, not a build/check date.
  A first baseline says earlier changes are unknown. Keep selected/all-model history access,
  separate base/observed-benchmark labels, material flags and recording-gap notices. Display saved
  amounts rather than recalculating bills; history policy is in the
  [model rules](representative-models.instructions.md#change-monitoring-phase-8-owner-decision-2026-11-17).
- Build the model views with `createElement`/`textContent` and allow only http(s) links. A missing or
  broken file shows a notice without breaking the other views.

## Across-Canada (`site/js/across-canada.js`, `site/css/across-canada.css`)

- A scrollable national table and grouped horizontal CSS bars by province, with a stable province hue
  and related shades per rate structure, for desktop and phone screens.
- Territories with a model show their before-subsidy totals labelled "before subsidies" (status and
  chart label, plus a note under the chart) and, in the row, the published after-subsidy median before
  tax or the reason none is shown; a territory without a model keeps "Not modelled yet".

## Tests

- Browser tests run offline: every request is routed to frozen or synthetic local data.
