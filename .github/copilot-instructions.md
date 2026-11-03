# Shared development workflow

## Required reading and maintenance

Before making task decisions or changes, read this file and [AGENTS.md](../AGENTS.md).
Both apply: AGENTS.md owns the project safeguards and the plain-language maintainer guide;
this file owns the development workflow. Area rules live in [instructions/](instructions/):
VS Code loads each one automatically when you edit matching files. If your tool does not,
read the relevant files yourself (AGENTS.md lists them by area). Report missing instructions
or conflicts before proceeding with affected work; never guess missing requirements.

At completion, check README.md, AGENTS.md, this file, the affected area instructions and
the docs listed in AGENTS.md's Documentation Review Rule against the changed behaviour.
Update affected guidance in the same change. Do not duplicate a rule in several files, and
do not put activity logs or volatile figures (test totals, record counts, run IDs, commit
hashes) in instruction files: current figures belong only in README's short status. Dated
history lives in the maintainer's local, git-ignored `.local/HISTORY.md` and open work in
`.local/TASKS.md`. If instructions change during a task, re-read them before continuing
affected work. Markdown links cannot force a tool to load files; reading them is the
agent's job.

## Clarify before relying on assumptions

Use available evidence to establish facts. If requirements, scope, behaviour, data, sources,
methodology or user intent remain unclear, or more than one sensible path exists, ask a
specific question before acting on it. Present concrete options, their trade-offs and an
evidence-based recommendation, and allow an alternative answer. Never treat an unanswered
question as approval of a default. Recorded owner decisions (dated in the instructions and
docs) are binding: follow them and reopen one only with new evidence, by asking.

## Codebase exploration with graphify

`graphify-out/` holds a knowledge graph of the application code. Tests, data folders, the
database schema and workflow YAML are left out (`.graphifyignore`). Before investigating
architecture or file relationships, or making a multi-file change:

1. If `graphify-out/graph.json` exists, locate the relevant code with the graph first:
   - `graphify query "question"` for broad context
   - `graphify explain "Symbol"` for one component and its connections
   - `graphify path "A" "B"` for how two parts connect
   - `graphify affected "Symbol" --depth 3` for callers to check before changing shared code
   If `graphify` is not found, VS Code probably started before graphify was installed: use
   `%USERPROFILE%\.local\bin\graphify.exe` (or `~/.local/bin/graphify`) and suggest a restart.
2. Use `graphify-out/wiki/index.md` for broad navigation. Read `graphify-out/GRAPH_REPORT.md`
   only for architecture reviews or when targeted queries are not enough.
3. Then read the actual source files, preferring targeted reads over scanning the repository,
   and reuse what you already learned in the session.
4. Find tests, data, docs and workflows with ordinary search: they are not in the graph.
5. Never treat a graph relationship as proof of correctness; confirm it in code and tests.

If the graph is missing, stale or the CLI is unavailable, say so, explore with ordinary
targeted search, and suggest `python scripts/graphify_hook.py status`.

After a commit that changes code, the post-commit hook (`scripts/graphify_hook.py`) refreshes
`graphify-out/` and records it in a separate `chore(graphify): refresh code graph for <sha>`
commit. Expect that commit after yours. Never edit `graphify-out/` by hand or amend a
`chore(graphify)` commit; to change your own last commit after the hook ran, make a new
commit. Never run `graphify hook install` (it adds other hooks and a merge driver). If you
run `graphify vscode install`, restore this file afterwards with
`git restore .github/copilot-instructions.md`. Setup and troubleshooting: README section
"Graphify (optional developer tool)" and [graphify.instructions.md](instructions/graphify.instructions.md).

## Validate changes

- Run the smallest relevant tests first (`python -m pytest tests/test_name.py`), then the
  full suite with `pytest tests` when shared code changes (a bare `pytest` also collects old
  test copies left in the git-ignored `logs/` folder). Tests block unmocked network access
  and use source-derived fixtures.
- Check scraper and parser changes with a targeted dry run, for example
  `python -m pipeline.run_scrape --utility "BC Hydro" --dry-run`, and report its live and
  estimated record counts.
- Never store scrapes locally or upload a database: the Monthly Scrape on GitHub is the only
  writer of the history database (see AGENTS.md). Locally, scrape with `--dry-run`;
  `python -m pipeline.run_scrape --init-db` only creates an empty practice database.
- Market scripts that download official files support `--dry-run`; use it unless the owner
  asks for written output.

## Conventions

- Python 3.10+ with type hints. ISO-8601 dates, UTC timestamps. Currency is CAD unless
  stated; province codes are two-letter uppercase (BC, ON, QC).
- Keep `data/sources/registry.json` and scraper URL constants synchronized; most scrapers
  do not read the registry's URLs at run time.
- Every tariff keeps its individual rate components; never flatten a tariff to one number.
- The website is plain HTML, CSS and JavaScript with no build step.

## Explain code

For new or changed code, write docstrings and concise comments that explain why: the source
evidence, owner decisions (with their date), boundaries, units and failure behaviour. Do not
add comments that repeat the code, and do not rewrite unrelated documentation.

## Keep the README quick start working

README.md keeps a short, beginner-friendly quick start near the top (a "README within the
README"): purpose, prerequisites, the smallest working workflow, expected outputs and the
important limitations. Keep it consistent with what actually works, check any command you
change, and link to details instead of growing it. Never describe planned work as done.

## Commits, pushes and teamwork

- Significant tested milestones may be committed and pushed, as the owner explicitly requested.
  Stage only the task's files: never unrelated work, `tests/_pending/` or the `.claude/worktrees/`
  gitlinks.
- Parallel workers may each own separate utility files; database, export, registry and test
  integration and publishing are done one at a time. Preserve all earlier snapshots.
- Context checkpoint: when approaching the context limit (target about 90%), stop opening
  new work, finish and validate the current batch, record completed work, test results,
  remaining gaps and the exact next step in the coverage matrix or `.local/TASKS.md`, then
  commit and push the verified changes before stopping. If usage cannot be measured,
  checkpoint early rather than claim an exact percentage.
