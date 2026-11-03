---
description: "Use when changing the graphify setup or when the post-commit graph refresh fails: scripts/graphify_hook.py, tests/test_graphify_hook.py, .graphifyignore, requirements-graphify.txt, the graphify-out/ allowlist in .gitignore, or files in graphify-out/."
applyTo: "scripts/graphify_hook.py, tests/test_graphify_hook.py, .graphifyignore, requirements-graphify.txt, graphify-out/**"
---
# Graphify setup

These are owner decisions (2026-11-03). Change them only after asking the owner.

- **Scope:** application code only. `.graphifyignore` leaves out `tests/`, `data/`,
  `site/data/`, `schema/`, `.github/` and `.claude/`; it records the reason for each. Keep
  the graph below graphify's 5,000-node HTML limit: above it, `graph.html` becomes an
  aggregated view of unnamed communities.
- **Names and models:** communities keep graphify's automatic names (the best-connected
  node). The helper sets `GRAPHIFY_BACKEND=none` for every graphify run, so no AI model is
  ever called. Do not add hand-written labels.
- **Version pin:** `requirements-graphify.txt` is the only place the version is set. The
  helper refuses any other version for `install`, `build`, `refresh` and `run`. To upgrade:
  change the pin, reinstall, run `python scripts/graphify_hook.py build` and
  `python -m pytest tests/test_graphify_hook.py`, then commit.
- **Committed outputs:** exactly the allowlist block in `.gitignore`: `graph.json`,
  `GRAPH_REPORT.md`, `graph.html`, `GRAPH_TREE.html`, `GRAPH_CALLFLOW.html`, `wiki/`,
  `.graphify_build.json` (keeps updates code-only) and the label files. Caches,
  `manifest.json`, build state and `.graphify_root` (which can hold an absolute path) stay
  ignored. `.gitattributes` marks `graphify-out/**` as generated with LF line endings.
- **Hook ownership:** the helper owns post-commit only, identified by a content checksum. It
  never overwrites, appends to or deletes another hook. Never use `graphify hook install`,
  which also adds checkout, merge and rewrite hooks and a merge driver.
- **Follow-up commit:** contains only `graphify-out/` and is never pushed. It is made only
  when nothing else uncommitted could be in the graph (changes under plain directory rules
  in `.graphifyignore` do not count). It is never made during a rebase, merge, cherry-pick or
  revert, in a linked worktree, or when a changed output contains this checkout's or the
  home folder's path (the repository is public). A failure never undoes the user's commit.
- **Skipped commits:** commits that change only `.md` or `.txt` files or excluded folders
  skip graphify entirely, because they cannot change a code-only graph. A merge commit shows
  no diff here, so it is refreshed.
- **Views:** the wiki and call-flow exports read a temporary merged labels file built from
  `graph.json`'s `community_name`; graphify's labels file holds only curated names. Call-flow
  sections are this project's areas (`CALLFLOW_AREAS`), not graphify's default archetypes,
  which describe graphify's own code. The call-flow page embeds a timestamp, so views are
  re-exported only when `graph.json` changed or a view is missing.
- **Full rebuild:** `build` deletes `graph.json` before `graphify update`, because update
  writes community names, the report and `graph.html` only when it has no identical graph to
  compare with. Run it after changing the pin or `.graphifyignore`, then review and commit.
- **Speed:** each git process can take about a second on Windows with real-time scanning.
  Keep the hook lean: batch git questions (one `rev-parse`, one `status`) and avoid extra
  graphify runs.
- **Tests:** `tests/test_graphify_hook.py` uses temporary repositories, a stand-in graphify,
  no network and no global Git configuration, because the Monthly Scrape runs the whole suite
  before scraping. Keep it passing on Ubuntu (Python 3.12) and Windows.
