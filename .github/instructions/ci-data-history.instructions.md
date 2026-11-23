---
description: "Use when changing GitHub Actions workflows, the scrape pipeline or the database tooling: .github/workflows/ (scrape.yml, source-health.yml, deploy.yml), pipeline/run_scrape.py, pipeline/export_json.py, pipeline/validate.py, pipeline/diff_report.py, scripts/check_db_history.py, scripts/pull_history_db.py, scripts/coverage_gate.py, data/sources/coverage_ledger.json and schema/. Covers the single-writer SQLite history in the data-history release, restore and SHA-256 digest checks, history verification, upload order and backups, dispatch inputs, pipefail and runner pins, the public provenance notice, the coverage gate and its ledger, upserts and workflow_run deployment chaining."
applyTo: ".github/workflows/**, scripts/check_db_history.py, scripts/pull_history_db.py, scripts/coverage_gate.py, scripts/model_monitoring_issue.js, pipeline/model_monitoring.py, tests/test_model_monitoring.py, data/sources/coverage_ledger.json, pipeline/run_scrape.py, pipeline/export_json.py, pipeline/validate.py, pipeline/diff_report.py, schema/**"
---
# CI, database history and the coverage gate

Market workflows: [market-data.instructions.md](market-data.instructions.md). Provenance export and
snapshot rules: [scrapers.instructions.md](scrapers.instructions.md). Model export:
[representative-models.instructions.md](representative-models.instructions.md).

## Single-writer database (owner decision 2026-10-16)

- The Monthly Scrape is the only writer of `data/db/rates.db` (AGENTS.md safeguard). The master copy
  is asset `rates.db` of the `data-history` GitHub release, next to dated `rates-YYYY-MM-DD.db.gz`
  backups (the newest 12 are kept). Deleting the release deletes the database and every backup.
- The schema is `schema/create_tables.sql`. Earlier snapshots, tariff versions and scrape runs must
  survive every change; the history check below rejects any loss.
- Restore: look up the release with `gh api .../releases/tags/data-history`. Only HTTP 404 (no
  release) starts a new database (`history=new`, then `run_scrape --init-db`); any other lookup
  failure stops the run. `rates.db` must be the single uploaded asset with a `sha256:` digest, and the
  download must match it.
- `scripts/check_db_history.py stats --db ... --out ...` runs after the restore and
  `verify --db ... --before ...` before the upload. Verify requires `PRAGMA integrity_check` ok; no
  fewer snapshots, tariff versions or scrape runs; a highest snapshot id that is not lower; and an
  unchanged SHA-256 digest over all earlier snapshot rows (rate components are only reported). It
  posts one public `::notice title=Database history::` (or `::error`). A failed check uploads nothing.
- Upload the dated backup first, then `rates.db` (`--clobber` deletes the existing asset before
  uploading its replacement). Prune the backups to the newest 12 after the bot commit.
- `scripts/pull_history_db.py` (`--output`, `--dry-run`) resolves the public asset through the GitHub
  API, verifies its size and digest, copies an older local file to
  `data/db/backups/rates-<UTC timestamp>.db` and then `os.replace`s it. It never uploads.
- `tests/test_ci_history.py` covers the history check and the download script.

## Monthly Scrape (`scrape.yml`)

- Runs at 08:00 UTC on the 1st (the full run), at 08:00 UTC on the 4th for the monthly-price group,
  and on manual dispatch with an optional `utility` or `province` input (not both). Inputs and
  `github.event.schedule` reach the shell only through `env`.
- **Monthly-price run (owner decisions 2026-11-20 and 2026-11-23):** the active registry entries with
  `monthly_price_refresh: true` (`run_scrape --monthly-price-refresh`), whose monthly price is usually
  posted after the 1st. "Run scrapers" selects it when `$SCHEDULE` equals the cron string, which must
  equal `MONTHLY_PRICE_CRON` in `pipeline/model_monitoring.py` (a test checks both). It uses the same
  restore, tests, history check and publication as every run.
- **Input check (owner decision 2026-11-20):** after the checkout and before anything is installed,
  `python3 -m scrapers.registry --utility="$UTILITY" --province="$PROVINCE"` (the runner's own Python;
  `scrapers/registry.py` is standard library only) rejects both inputs set, a province that is not
  two letters (naming the utility box, and the utility when the text is one), a code with no active
  utility (listing the valid codes) and a utility not found ignoring accents and case (naming the
  closest registry names), each as an `::error title=Inputs::` annotation that says what to type.
- Order: check out; check inputs; restore and digest-check the database (initialize only a new one);
  run the deterministic tests; scrape; `pipeline.validate`; synchronize with `git pull --ff-only origin
  main`; `pipeline.export_json`; reject empty exports; report the coverage gate; verify the history;
  upload; diff report; commit `site/data/` with a plain `git push`; prune backups. A queued dispatch
  checks out its dispatch-time commit, so the sync makes the export see the previous writer's bot
  commit; generated files are never rebased onto newer inputs, like the market workflows (issue #5;
  owner decision 2026-11-04). A push rejected because `main` moved after the export fails the run
  after the database is saved; start a new dispatch rather than re-running the failed job.
- The diff report (`pipeline.diff_report`) compares the newest run with the one before it, but only for
  utilities with records in the newest run (owner decision 2026-11-20). The previous run's other
  utilities are counted under "Not compared" instead of being listed as removed; a utility that
  returned nothing is named by the run's provenance notice.
- A failure after the input check opens an issue that includes a Database History section.
  Deployment is separate.

## All workflows

- Runners are pinned to `ubuntu-24.04` (owner decision 2026-10-15) and use Python 3.12.
- `defaults.run.shell: bash` adds pipefail, so `cmd | tee` fails its step.
- **Source Health** (`source-health.yml`): 10:00 UTC on the 15th and on dispatch; a non-blocking dry
  run of every source that uploads its log and publishes nothing.
- **Deploy Site** (`deploy.yml`): pushes to `main`, manual dispatch, and `workflow_run` after each
  successful Monthly Scrape, Ontario Price Archive and Market Benchmarks run (the names must equal each
  workflow's `name:`; owner decision 2026-10-30 for the archive). Bot pushes with `GITHUB_TOKEN`
  trigger no workflows, hence `workflow_run`. A `workflow_run` deploy checks out `main`; a failed or
  cancelled run deploys nothing even if it committed data, so dispatch Deploy Site by hand to publish
  such a commit. `workflow_run` fires only from the default branch, and GitHub Pages must use GitHub
  Actions as its source. A `build` job uploads the site artifact and a separate `deploy` job
  (`needs: build`, environment `github-pages`) publishes it, as in GitHub's Pages starter workflows:
  deploying in the upload's own job intermittently found no artifact ("No artifacts named
  github-pages", actions/deploy-pages#451; three failures on AWS-hosted runners from 2026-11-20). A
  failed `deploy` job can be re-run on its own within a day, reusing the build job's artifact
  (`upload-pages-artifact` keeps it one day); later, dispatch Deploy Site.
- The three data writers take turns through the `utility-data-updates` concurrency group (rules in
  the market-data instructions).
- Known harmless warning: "git ... exit code 128" in the checkout post-step, because
  `.claude/worktrees/agent-*` are committed gitlinks without `.gitmodules`.
- The owner dispatches workflows from the GitHub web UI; there is no local `gh` CLI.

## Pipeline scripts

- `run_scrape.py` upserts with `ON CONFLICT ... DO UPDATE SET` and NULL-safe `IS` comparisons, so
  re-runs are idempotent. `--province` filters through `get_active_utilities()`, which skips merged
  and retired entries. `--utility` finds any registry entry ignoring accents, case and repeated spaces
  (`scrapers.registry.find_utility`); an unknown name exits 1 naming the closest registry names.
  `--monthly-price-refresh` (not with `--utility` or `--province`) runs `monthly_price_utilities()`
  and exits 1 when no active entry is flagged. Locally use `--dry-run` only; `--init-db` creates an
  empty practice database.
- Per-run provenance summary: `tally_provenance`, `summarize_run`, `format_summary_markdown` and
  `append_step_summary` (a Markdown table in `$GITHUB_STEP_SUMMARY`; no schema change).
  `format_github_notice()`/`emit_github_notice()` print one public `::notice title=Scrape provenance::`
  annotation (live, seed and invalid totals; failed, no-valid and seed-only utilities), escaping `%`,
  CR and LF, only when `GITHUB_ACTIONS == "true"`. Tests that call `main()` set or clear that variable.
- `pipeline.validate` reconfigures stdout so Windows consoles do not crash on non-ASCII names.
- `export_json.py` writes the site JSON, then the representative models.
- `run_scrape --summary-json PATH` optionally writes the existing per-utility provenance summary
  with expected utility names, full/targeted scope (`scope.group` is `monthly_price_refresh` for the
  run on the 4th, otherwise null), dry-run status and run/attempt identity.
  Receipt failure is logged without changing the scrape or database behavior. Each row's
  `excluded_seed` counts the part of `seed` labelled by `mark_fallback` with
  `scrapers.base.EXCLUDED_CLASS_FALLBACK_REASON` (Ontario street lighting); public totals still
  count those records as seed.

## Model monitoring

Comparison/history policy is in the
[model rules](representative-models.instructions.md#change-monitoring-phase-8-owner-decision-2026-11-17).
The following workflow decisions were approved on 2026-11-17.

- Reuse the existing model build in each data writer. Record history after generation and stage it
  with the models in the same publication step. Never add a build or database writer for monitoring.
- `scripts/model_monitoring_issue.js` captures actual step outcomes and collects run/attempt-bound
  generation, source and publication receipts. A green workflow or an unchanged file proves
  neither source health nor a successful model generation. A partial scrape cannot satisfy a
  full-registry cadence check; per-utility recovery stays scoped to its checked sources.
- A source check passes only with live records, no invalid records, no error and no estimates
  other than labelled excluded-class estimates (`excluded_seed`, owner decision 2026-11-18). Any
  other estimate is a source problem; receipts without the field count every estimate.
- **Manual-update utilities (owner decision 2026-11-19, issue #6):** a well-formed ledger
  `manual_update` lets that utility's estimates-only check (no live, no invalid, no error) pass
  while the receipt's `checked_at` date is on or before `review_by`; after it the check fails and
  asks for the yearly manual procedure. A malformed or unreadable ledger grants no exemption. Any
  live, invalid or error result is checked normally.
- The three data writers and Source Health call `model-monitoring.yml`, a reusable read-only
  reporting job with **no schedule**. Its `model-monitoring-issues` job concurrency serializes issue
  updates without putting Source Health in the data-writer concurrency group.
- Check on existing/manual runs only. Read scheduled due times from the workflow YAML; Market
  Benchmarks is due after qualifying completed parent workflows, not on an invented calendar.
  A missing refresh becomes overdue **strictly more than 24 hours after its due time**, detected
  at the next check. Known failures are reported immediately. This grace never extends tariff
  expiry, audit/review deadlines or observed-market validity rules. Complete workflow silence
  cannot be detected until another check runs.
- **Monthly-price schedule (owner decisions 2026-11-20 and 2026-11-23):** the full refresh's due
  time comes from `scrape.yml`'s crons other than `MONTHLY_PRICE_CRON`, which has its own check,
  `workflow:scrape.yml:monthly-price`: a successful full or monthly-price run after its due time
  meets it, and it is overdue strictly more than 24 hours later. A failing source check of a
  monthly-price utility (the registry flag, read by `main()`; an unreadable registry holds nothing)
  seen between the full run's due time and the next monthly-price due time is held (`ok: null`, no
  issue). A newer check replaces it, and if none arrives within 24 hours of that due time it is
  reported. Other utilities and other days are reported at once.
- A run stopped by its input check (outcome receipt `inputs: "failure"`; owner decision 2026-11-23)
  is neither a failure nor a refresh: it scraped and saved nothing, and its own error says what to
  type. Older receipts without the field are read as before.
- Reuse the coverage gate, crosswalk coverage, reviewed block-period checks and observed-market
  reader. Missing/invalid configuration and unmapped live tariffs remain problems; a documented
  `not_computable` model is not inherently corrupt. Do not hide known coverage gaps.
- Keep one bot-owned, marked monitoring issue for input/refresh problems, never ordinary price
  changes. Preserve unchecked problems and maintainer text, reject older recovery evidence and
  avoid duplicating a failure already reported by its workflow. Only monitoring-owned issues are
  auto-closed, with recovery evidence; publication problems require verified publication.
- Recording, evidence upload and the reusable reporting job are non-blocking. Failures stay
  visible in Actions logs/annotations and diagnostic artifacts; missing receipts stay unverified.
  These failures must not bypass database safety gates or turn a valid publication into a failed
  workflow that prevents deployment. The reporter uses standard-library Python and Node built-ins;
  both sides of its JSON subprocess pipe use UTF-8, including on Windows.

## Coverage gate (`scripts/coverage_gate.py`, owner decisions 2026-10-30)

- Decides whether "nationwide live-rate coverage is complete" may be claimed. Scope: the active
  registered utilities and their main building classes with documented exclusions; representative
  models do not gate.
- Options `--as-of`, `--json`, `--report-only`, `--verbose`, `--max-age-days` (120) and `--warn-days`
  (30); standard library only. It checks every active registry entry (`active`/`partial`) against
  `site/data/rates.json` and `data/sources/coverage_ledger.json`.
- Errors: `no_live_output` (no live record whose effective date has been reached and whose end date
  has not passed), `no_audit`, `stale_audit`, `deferred_open`, `monitor_overdue`, `ledger_orphan`,
  `ledger_invalid`. Warnings: `monitor_due_soon`, `live_expiring`.
- Ledger schema 1: per registry name an `audit` {date, basis, source}, the string lists `excluded`,
  `source_blocked` and `deferred`, a `monitor` {item, review_by}, an optional `stored_name` and an
  optional entry-only `manual_update` {reason, decided, review_by} (exactly these keys; review_by on
  or after decided) for a source refreshed by hand. Its review date counts like a monitor item
  (`monitor_due_soon`, then `monitor_overdue`); it never stands in for live output.
  `groups` let entries inherit an audit and standard exclusions (`"group": "ontario_electricity"`); an
  entry's own audit wins and the lists are concatenated. The ledger records decisions and never
  changes a rate. Undecided items go under `deferred`, which keeps the gate failing until resolved.
- `stored_name` exists because the export keys records by the scraper's utility name: "Energir"
  (registry "Énergir") and "Liberty Utilities Gas NB" (registry "Liberty Utilities NB").
- `scrape.yml` runs it after the export as a `continue-on-error`, `--report-only` step that posts one
  `::notice`/`::warning` "Coverage gate" annotation; it never blocks the database save.
- The README may say coverage is complete only when the gate passes, and a passing gate never
  dismisses a known source contradiction.
- `tests/test_coverage_gate.py` uses synthetic inputs only, never the live export.
