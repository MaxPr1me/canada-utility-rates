---
description: "Use when changing GitHub Actions workflows, the scrape pipeline or the database tooling: .github/workflows/ (scrape.yml, source-health.yml, deploy.yml), pipeline/run_scrape.py, pipeline/export_json.py, pipeline/validate.py, pipeline/diff_report.py, scripts/check_db_history.py, scripts/pull_history_db.py, scripts/coverage_gate.py, data/sources/coverage_ledger.json and schema/. Covers the single-writer SQLite history in the data-history release, restore and SHA-256 digest checks, history verification, upload order and backups, dispatch inputs, pipefail and runner pins, the public provenance notice, the coverage gate and its ledger, upserts and workflow_run deployment chaining."
applyTo: ".github/workflows/**, scripts/check_db_history.py, scripts/pull_history_db.py, scripts/coverage_gate.py, data/sources/coverage_ledger.json, pipeline/run_scrape.py, pipeline/export_json.py, pipeline/validate.py, pipeline/diff_report.py, schema/**"
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

- Runs at 08:00 UTC on the 1st and on manual dispatch with an optional `utility` or `province` input
  (not both; the province must match `^[A-Za-z]{2}$`). Inputs reach the shell only through `env`.
- Order: check inputs; restore and digest-check the database (initialize only a new one); run the
  deterministic tests; scrape; `pipeline.validate`; synchronize with `git pull --ff-only origin main`;
  `pipeline.export_json`; reject empty exports; report the coverage gate; verify the history; upload;
  diff report; commit `site/data/` with a plain `git push`; prune backups. A queued dispatch checks
  out its dispatch-time commit, so the sync makes the export see the previous writer's bot commit;
  generated files are never rebased onto newer inputs, like the market workflows (issue #5; owner
  decision 2026-11-04). A push rejected because `main` moved after the export fails the run after
  the database is saved; start a new dispatch rather than re-running the failed job.
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
  Actions as its source.
- The three data writers take turns through the `utility-data-updates` concurrency group (rules in
  the market-data instructions).
- Known harmless warning: "git ... exit code 128" in the checkout post-step, because
  `.claude/worktrees/agent-*` are committed gitlinks without `.gitmodules`.
- The owner dispatches workflows from the GitHub web UI; there is no local `gh` CLI.

## Pipeline scripts

- `run_scrape.py` upserts with `ON CONFLICT ... DO UPDATE SET` and NULL-safe `IS` comparisons, so
  re-runs are idempotent. `--province` filters through `get_active_utilities()`, which skips merged
  and retired entries. Locally use `--dry-run` only; `--init-db` creates an empty practice database.
- Per-run provenance summary: `tally_provenance`, `summarize_run`, `format_summary_markdown` and
  `append_step_summary` (a Markdown table in `$GITHUB_STEP_SUMMARY`; no schema change).
  `format_github_notice()`/`emit_github_notice()` print one public `::notice title=Scrape provenance::`
  annotation (live, seed and invalid totals; failed, no-valid and seed-only utilities), escaping `%`,
  CR and LF, only when `GITHUB_ACTIONS == "true"`. Tests that call `main()` set or clear that variable.
- `pipeline.validate` reconfigures stdout so Windows consoles do not crash on non-ASCII names.
- `export_json.py` writes the site JSON, then the representative models.

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
  `source_blocked` and `deferred`, a `monitor` {item, review_by} and an optional `stored_name`.
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
