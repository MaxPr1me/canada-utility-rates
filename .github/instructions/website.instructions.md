---
description: "Use when changing the static website under site/: index.html, css/, js/app.js (Rate Browser, Market Pricing, Compare), js/models.js (Representative Models), js/archetypes.js (Building Archetypes), js/across-canada.js, js/rate-history.js (Rate History) and the site/data/ JSON it reads. Covers the seven views, hiding seed (estimated) rates by default, filterState Sets, the province-to-utility cascade, dedupe by effective date, formatCharge, Compare never totalling, the Ontario/Alberta market dashboard, the window.CanadaUtilityModels API and shared lazy load, the Rate History periods, reviewed series and event lists and hand-built SVG charts, safe DOM building, failure notices, the estimated market energy note, the Building Archetypes tab (simulated, lazy, phone cards), the Across-Canada sub-tabs and spark gap view, and offline browser tests."
applyTo: "site/**"
---
# Static website

A plain HTML, CSS and JavaScript single-page app (Chart.js from a CDN), deployed to GitHub Pages and
reading `site/data/`. The Rate History charts are hand-built SVG instead: Chart.js cannot draw a bar as
wide as a price period, and SVG keeps working if the CDN fails. Model data rules, including
Across-Canada's: [representative-models.instructions.md](representative-models.instructions.md). Market
file rules: [market-data.instructions.md](market-data.instructions.md).

## Views

- Seven views: **Rate Browser** (filters, cards, details), **Rate History** (how stored prices changed),
  **Market Pricing**, **Representative Models**, **Building Archetypes** (simulated building costs),
  **Across-Canada** (residential comparison and, in its second sub-tab, the spark gap) and **Compare**
  (two tariffs). Across-Canada and Compare stay separate.
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
  factor and elective classes. Across-Canada's residential sub-tab keeps filtering to residential electricity.
- Estimated market energy (method 7S-2, owner decisions 119-123 of 2026-11-25): the Ontario and Alberta
  50-499 kW and 500-4,999 kW models include it in the table. The badge says "with estimated market
  energy", the caption says it is not live, and each estimated level gets an "Estimated energy" tag.
  One always-visible note under the table, "Market energy in this model" (decision 123, replacing the
  opt-in simulated block and the separate benchmark block), shows the price used, the level's energy
  amount, the same-use-every-hour benchmark (price and medians, a comparison only), the simulated
  buildings' price range, the assumptions, a collapsed list of the buildings (BTAP type names as text
  only) and the sources. It describes the estimate only when the model is `market_energy_estimated`
  with that cost basis, `energy_estimate.available` and the level's `market_energy_estimate` amount
  (fail closed); a pending model shows why (the estimate's reason when an input failed) and only a
  usable benchmark; an estimated model whose details fail the checks shows no number.
- Render `fixed_charge_variants` as always-visible reference assumptions for every supplied level,
  plus each contributor's chosen component. They describe the example customer, not the visitor's
  actual service or eligibility. Older exports may omit these fields.
- Show the historical market benchmark only as the same-use-every-hour comparison in the energy note,
  never in place of the table's numbers.
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

- Two sub-tab buttons above the view (owner decision 144, 2026-11-26), styled like Rate History's but
  with their own `across-subtab` class and `aria-pressed` (`data-across-tab`): "Residential
  electricity" (default, `#across-residential`) and "Spark gap" (`#across-spark`, below).
- A scrollable national table and grouped horizontal CSS bars by province, with a stable province hue
  and related shades per rate structure, for desktop and phone screens.
- Territories with a model show their before-subsidy totals labelled "before subsidies" (status and
  chart label, plus a note under the chart) and, in the row, the published after-subsidy median before
  tax or the reason none is shown; a territory without a model keeps "Not modelled yet".

## Spark gap (`site/js/spark-gap.js`, `site/css/spark-gap.css`; method SG-1, decisions 124-165)

- Reads `data/spark_gap.json` with its own lazy fetch the first time its sub-tab opens (never on page
  load); a missing or broken file shows a retryable notice in this sub-tab only.
- Shows the pipeline's values only (nothing recalculated): a customer selector (home by default; small
  building; mid-size building, which list the eight gas provinces), the tax toggle (with tax and
  rebates by default), CSS bars of the average spark gap on one 0-to-N scale with a dashed line at 1,
  and a table of both prices (average and marginal, cents per kWh with $/GJ), the spark gap, the
  break-even COP (businesses: furnace and boiler), and for homes the realistic COP with its city and
  the result in words with any marginal note. A row that is not available says why and never gets a
  zero bar.
- Labels: "Estimated energy", "Interim rates", "Before subsidies" (territories also state the
  after-subsidy spark gap and break-even, before tax) and the oil price's month. A "Method and
  sources" list names the comparison-fuel rule and left-out fuels, the oil price basis and energy, the
  heating values, the efficiencies, the COP source and, for businesses, input tax credits; links are
  http(s) only and all text is set with `textContent`.

## Building Archetypes (`site/js/archetypes.js`, `site/css/archetypes.css`; method AC-1, decisions 107-110)

- A tab right after Representative Models with a "Simulated" badge. The view repeats the SIMULATED badge
  and keeps an always-visible banner ("Simulated buildings, not real buildings or bills"); rows tag
  estimated market energy and quality-flagged runs. Never reuse these costs in another view
  (safeguard 8).
- Reads `data/archetype_costs.json` with its own lazy fetch the first time the tab opens (never on page
  load). A file that is missing, broken or not an AC-1 SIMULATED document shows a notice in this view
  only; opening the tab again retries.
- Shows the pipeline's values only (nothing recalculated):
  - "With tax and rebates" first, with a switch to "Before tax and rebates";
  - filters by city, building type and heating, and a table sortable by annual cost, $/m² and effective
    ¢/kWh;
  - a detail panel per row: monthly costs (a stacked electricity and gas SVG with a table), the load,
    quality and apartment notes, each fuel's rate class and why, supply, annual cost, effective rates,
    cost by charge group with the tax lines, loss factor, estimated energy, rebates not applied and
    tariff sources, the same building with the other heating fuel, and the simulation file links.

  A fuel that is not computable shows its reasons. No load-shape heatmap (decision 108).
- Phones: below 640 px each row becomes a stacked card. The detail's label/value rows stack through
  child selectors (`.arch-kv > tr > th/td`), so the nested charge-group table keeps its two columns.
  The filters stretch below 768 px, as on Representative Models.
- There is no global `.hidden` rule: `#view-archetypes .hidden` hides the view's loading line, notice
  and panels. Build with `createElement`/`createElementNS` and `textContent`; links are http(s) only.

## Rate History (`site/js/rate-history.js`, `site/css/rate-history.css`)

Owner decisions 44-57 (2026-11-23) and 80-84 (2026-11-24).

- Inputs, loaded the first time the view opens:
  - every stored tariff version, through `window.CanadaUtilitySite.rates()` (`app.js` keeps the raw array
    before its newest-only deduplication);
  - the reviewed lists `rate_history_series.json` and `rate_history_events.json`;
  - `rate_history_revisions.json` (Monthly Scrape export), `market_quarterly_ontario.json`,
    `market_quarterly_alberta.json` and `model_cost_quarterly.json`;
  - model labels and selector order from the shared `CanadaUtilityModels.load()`.

  A missing or broken optional file shows a notice in its own part only.
- Opening the view shows "Recent price changes", with the chart of the newest item below it and the
  four sub-tab buttons above with none selected (Tariff prices, Regulated & default, Market, Model
  costs). The list holds:
  - real changes whose effective date is within the last 90 days, up to the visitor's own date (a
    future change joins only on its date), newest first;
  - tariff and regulated/default prices only, never corrections;
  - identical changes as one line, grouped by their regulated series line when they have one;
  - 20 lines, then "Show more".

  A list item opens its chart in the sub-tab it belongs to.
- Choosing a chart:
  - province, utility, tariff and price-line drop-downs, plus a utility-name search that ignores
    accents and capital letters;
  - the Rate Browser detail window's "History" button, on live tariffs only, opens that tariff.
- Price periods. A price line is component type, name, unit, tier, tier threshold, time-of-use
  period, season, sub-component and demand threshold; a change of unit, tier or period starts a new
  line and is never converted. A line's period:
  - starts at its effective date (else its tariff's);
  - ends at the earliest of its own end date, its tariff version's end date and the next period's
    start, and a line missing from the newest version ends where that version starts;
  - takes its value from the newest version carrying the same start;
  - prices equal within floating-point tolerance are the same price (as in `export_json`).

  Display rules:
  - an ended price with no newer price leaves a "No current price stored" gap and is never extended;
  - future periods are drawn after a "today" marker;
  - value-less market prices are listed as "Variable" with a link to the Market sub-tab;
  - lines repeated within one version are listed as not charted;
  - a same-date correction shows "revised on <date>" from the revisions file;
  - estimates are never charted.
- Price charts:
  - one bar per period, as wide as the period lasts; a tariff's lines side by side, never stacked or
    added, each switchable from the legend;
  - different units in separate panels;
  - up to 5 same-unit comparison lines in the province hues;
  - per-kWh electricity prices in cents/kWh (display only), other units as published;
  - a "% change since the first period shown" toggle;
  - the default range starts September 29, 2026 (collection began), with 1Y, 5Y and All buttons only
    when bars start earlier.
- Market and model charts use quarterly bars:
  - **Market:** opens on all stored history; Ontario shows energy, Class B GA and the published total
    side by side, and Alberta shows pool energy.
  - **Model costs:** the saved quarter-end medians with a "Before tax and rebates" / "With tax and
    rebates" toggle (default with tax, like Across-Canada; owner decision 85, 2026-11-24); the current
    quarter is labelled "quarter in progress".
  - `break_before` draws a "method changed" gap with its reasons, and the % change restarts after it.
  - Recording gaps are noted, and market benchmarks are their own line.
  - Since method 7S-2 (2026-11-25) the Ontario and Alberta 50-499 kW and 500-4,999 kW model costs
    include estimated market energy (the cost basis change breaks their series); the explanation says
    so, and the benchmark line prices the same use in every hour.
- Event markers come only from `rate_history_events.json` (regulator or government decisions, each with
  its official source and checked quote), shown on charts whose family, province and fuel match.
  `site/data/rate_history_series.json` selects records and price lines by stored component names with
  full-match regexes (`pipeline/rate_history.py` holds the same rules in Python). A scraper change that
  renames a matched line must update the list: `tests/test_rate_history_lists.py` checks every series
  against frozen live records, and model monitoring's `rate_history_series` check reports any series
  line that no tariff's newest live version carries after a data run. Where the records carrying a
  series line disagree, each value is drawn with its tariff count; none is picked.
- Every chart has a data table (it scrolls sideways on phones) and a CSV download (cells that could
  start a spreadsheet formula are escaped). The address (`#rate-history/...`) remembers the chart.
  Build with `createElement`/`createElementNS` and `textContent` only, and link only http(s) URLs.

## Tests

- Browser tests run offline: every request is routed to frozen or synthetic local data.
- A new view must be added to the navigation list and the views loop of `tests/test_rate_history_site.py`.
  The Building Archetypes tab has its own tests at 1280 and 390 px in `tests/test_archetypes_site.py`.
