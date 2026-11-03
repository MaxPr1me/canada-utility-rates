"""Keep this repository's graphify code graph current and committed.

graphify (pinned in requirements-graphify.txt) builds the code knowledge graph in
graphify-out/ that agents query before reading source files. Owner decisions,
2026-11-03:

* Application code only (.graphifyignore leaves out tests, data folders, the
  database schema and workflow YAML). That keeps graph.html below graphify's
  5,000-node limit, so it shows real files and functions instead of an
  aggregated view of unnamed communities.
* Communities keep graphify's automatic names (each community's best-connected
  node). No AI model is ever called: every graphify run gets GRAPHIFY_BACKEND=none.
* The outputs allowed by the graphify block in .gitignore are committed. After
  each code commit the post-commit hook refreshes them and records them in a
  separate follow-up commit that touches only graphify-out/. Commits that change
  only documentation or excluded folders skip graphify entirely.
* Only the pinned graphify version runs. Another release can rewrite the whole
  committed graph, so a version mismatch stops every command that would run
  graphify: nothing is refreshed or committed.

The helper owns only the post-commit hook, never pushes, and a failure never
undoes the commit that triggered it. It needs only the Python standard library,
so the hook works with whichever Python 3.10+ interpreter installed it.

Commands (run from anywhere inside the checkout):
  install    install the post-commit hook (pins this Python and graphify)
  uninstall  remove the hook installed by this helper
  status     report graphify version, hook and graph state
  build      rebuild graphify-out/ from scratch (review it, then commit it)
  refresh    incremental refresh; add --commit to record the outputs
  run        what the hook runs after each commit
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import NamedTuple

PIN_FILE = "requirements-graphify.txt"
PACKAGE = "graphifyy"
OUTPUT = "graphify-out"
GRAPH = f"{OUTPUT}/graph.json"
# graphify update maintains graph.json, GRAPH_REPORT.md and graph.html; this
# helper exports the three views below itself.
WIKI_INDEX = f"{OUTPUT}/wiki/index.md"
CALLFLOW = f"{OUTPUT}/GRAPH_CALLFLOW.html"
TREE = f"{OUTPUT}/GRAPH_TREE.html"
# Temporary, git-ignored inputs for the exports below.
EXPORT_LABELS = f"{OUTPUT}/.graphify_labels.export.json"
EXPORT_SECTIONS = f"{OUTPUT}/.graphify_callflow_sections.json"
# Call-flow sections by project area. graphify's default sections are keyword
# archetypes written for graphify's own code ("Graph Build", "Serving API") and
# mislabel this project, so each community goes to the area most of its nodes
# come from instead. The first matching prefix wins.
CALLFLOW_AREAS = (
    ("scrapers/utilities/", "utility-scrapers", "Utility scrapers"),
    ("scrapers/", "scraper-framework", "Scraper framework and parsing helpers"),
    ("pipeline/", "pipeline", "Pipeline: scrape, validate, export and models"),
    ("scripts/", "scripts", "Market data and maintenance scripts"),
    ("site/", "website", "Website"),
)
# The graph is code only, so a commit changing nothing but these files (or
# folders excluded in .graphifyignore) cannot change it; the hook then skips
# graphify entirely (owner decision 2026-11-03: saves 10-15 s per such commit).
DOC_SUFFIXES = (".md", ".txt")
# Generated state that a from-scratch build removes first. cache/ (content-hashed
# extraction results) and the label files are kept.
REBUILT_STATE = ("graph.json", "manifest.json", ".graphify_build_state.json", ".graphify_analysis.json")

HEADER = b"#!/bin/sh\n# canada-utility-costs graphify post-commit v1\n"
CHECKSUM = b"# content-sha256: "
SKIP_ENV = "GRAPHIFY_SKIP_HOOK"
# Set for the follow-up commit, so the post-commit run it triggers exits at once.
ACTIVE_ENV = "GRAPHIFY_HOOK_ACTIVE"
COMMIT_PREFIX = "chore(graphify): refresh code graph for "
HELPER = "python scripts/graphify_hook.py"
INSTALL_HELP = (
    "graphify is an optional developer tool that needs Python 3.10 or newer. "
    "Install the pinned version, then restart VS Code so new terminals find it:\n"
    f"  uv tool install {PACKAGE} -c {PIN_FILE}\n"
    "or, inside the project's virtual environment:\n"
    f"  pip install -r {PIN_FILE}"
)
# State files Git leaves while an operation replays or combines commits. A
# follow-up commit in the middle of one would surprise the operation, so the
# hook skips; the next ordinary commit refreshes the whole graph anyway.
OPERATIONS = (
    ("rebase-merge", "A rebase"),
    ("rebase-apply", "A rebase or patch application"),
    ("MERGE_HEAD", "A merge"),
    ("CHERRY_PICK_HEAD", "A cherry-pick"),
    ("REVERT_HEAD", "A revert"),
    ("sequencer", "A cherry-pick or revert sequence"),
)


class HookError(Exception):
    """An expected failure with an actionable message; the command exits 1."""


def git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    """Run git inside *root* and return its output; failures keep git's message."""
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise HookError(f"'git {' '.join(args)}' failed: {detail}")
    return result.stdout


class Repo(NamedTuple):
    """Where Git keeps this checkout's files, as reported by one git call."""

    root: Path
    git_dir: Path
    common_dir: Path
    hooks_dir: Path
    head: str | None = None

    @property
    def linked_worktree(self) -> bool:
        return not same_path(self.git_dir, self.common_dir)


def repo_state(path: Path, *, with_head: bool = False) -> Repo:
    """Describe the checkout containing *path* with a single git call.

    Starting git can take most of a second on Windows machines with real-time
    scanning, and the hook runs inside every commit, so the questions are batched.
    """
    args = [
        "rev-parse", "--path-format=absolute", "--show-toplevel", "--git-dir",
        "--git-common-dir", "--git-path", "hooks",
    ]
    if with_head:
        args.append("HEAD")
    try:
        lines = git(path, *args).splitlines()
    except HookError as error:
        raise HookError(f"{path} is not inside a Git working tree with a commit. {error}") from None
    root, git_dir, common, hooks = (Path(line).resolve() for line in lines[:4])
    return Repo(root, git_dir, common, hooks, lines[4].strip() if with_head else None)


def same_path(first: Path, second: Path) -> bool:
    return os.path.normcase(str(first.resolve())) == os.path.normcase(str(second.resolve()))


def is_within(path: Path, root: Path) -> bool:
    inner, outer = os.path.normcase(str(path.resolve())), os.path.normcase(str(root.resolve()))
    return inner == outer or inner.startswith(outer.rstrip("\\/") + os.sep)


def hook_path(repo: Repo) -> Path:
    """Locate post-commit in Git's active hooks directory.

    Linked worktrees share the common directory's hooks, which is allowed. A
    hooks directory outside that location and outside this checkout belongs to
    someone else (a shared or global core.hooksPath); changing it needs a human
    decision, so the helper refuses rather than edit it.
    """
    hooks = repo.hooks_dir
    if not same_path(hooks, repo.common_dir / "hooks") and not is_within(hooks, repo.root):
        raise HookError(
            f"Git's hooks directory is outside this repository ({hooks}). Changing a "
            "shared hooks directory needs a manual decision; nothing was changed."
        )
    return hooks / "post-commit"


def read_pin(root: Path) -> str:
    """Return the graphify version pinned in requirements-graphify.txt."""
    try:
        text = (root / PIN_FILE).read_text(encoding="utf-8")
    except OSError:
        raise HookError(
            f"{PIN_FILE} is missing; it pins the only graphify version this helper runs."
        ) from None
    match = re.search(rf"^\s*{PACKAGE}\s*==\s*([0-9][^\s;#]*)", text, re.IGNORECASE | re.MULTILINE)
    if not match:
        raise HookError(f"{PIN_FILE} has no exact '{PACKAGE}==<version>' line.")
    return match.group(1)


def resolve_graphify(explicit: str | None) -> Path:
    """Find an installed graphify; never install one.

    Order: --graphify, PATH, next to this Python (a virtual-environment install),
    then uv's default tool folder (~/.local/bin). A VS Code window started before
    graphify was installed does not have that folder on its PATH yet.
    """
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            located = shutil.which(explicit)
            path = Path(located) if located else path
        if not path.is_file():
            raise HookError(
                f"graphify not found at {explicit}. If it moved, reinstall it and then "
                f"run '{HELPER} uninstall' and '{HELPER} install'.\n{INSTALL_HELP}"
            )
        return path.absolute()
    names = ("graphify.exe", "graphify") if os.name == "nt" else ("graphify",)
    located = shutil.which("graphify")
    candidates = [Path(located)] if located else []
    for folder in (Path(sys.executable).parent, Path.home() / ".local" / "bin"):
        candidates.extend(folder / name for name in names)
    for candidate in candidates:
        if candidate.is_file():
            return candidate.absolute()
    raise HookError(f"graphify was not found.\n{INSTALL_HELP}")


def graphify_env(*, hook: bool = False) -> dict[str, str]:
    """Return the environment for every graphify run.

    PYTHONHASHSEED=0 keeps clustering stable between runs (smaller graph diffs).
    PYTHONUTF8=1 lets graphify print non-ASCII text on Windows consoles.
    GRAPHIFY_BACKEND=none guarantees that no AI model is called. GRAPHIFY_OUT
    keeps output in this checkout, and GRAPHIFY_FORCE=0 keeps graphify's
    shrink guard on for refreshes (build passes --force explicitly). A personal
    GRAPHIFY_VIZ_NODE_LIMIT is dropped so committed views use graphify's default.
    """
    env = os.environ.copy()
    env.pop("GRAPHIFY_VIZ_NODE_LIMIT", None)
    env.update(
        PYTHONHASHSEED="0", PYTHONUTF8="1", GRAPHIFY_BACKEND="none",
        GRAPHIFY_NO_TIPS="1", GRAPHIFY_OUT=OUTPUT, GRAPHIFY_FORCE="0",
    )
    if hook and os.name == "nt":
        # Git for Windows hooks inherit fragile console handles; graphify's own
        # hook also extracts sequentially there.
        env.setdefault("GRAPHIFY_MAX_WORKERS", "1")
    return env


def installed_version(exe: Path) -> str:
    try:
        result = subprocess.run(
            [str(exe), "--version"], capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=graphify_env(), timeout=300,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise HookError(f"Could not run '{exe} --version': {error}") from None
    output = (result.stdout + result.stderr).strip()
    match = re.search(r"graphify\s+v?(\S+)", output)
    if result.returncode or not match:
        raise HookError(f"'{exe} --version' did not report a graphify version: {output[:300]}")
    return match.group(1)


def require_pinned(root: Path, exe: Path) -> str:
    """Stop unless *exe* is exactly the pinned graphify version."""
    pinned, found = read_pin(root), installed_version(exe)
    if found != pinned:
        raise HookError(
            f"graphify {found} ({exe}) is not the pinned {pinned} ({PIN_FILE}), so "
            "nothing was run, refreshed or committed.\n"
            f"Fix: uv tool install --reinstall {PACKAGE} -c {PIN_FILE}\n"
            f"  (or, in the project's virtual environment: pip install -r {PIN_FILE}).\n"
            f"To upgrade on purpose instead: change the pin, run '{HELPER} build' and "
            "'python -m pytest tests/test_graphify_hook.py', then commit."
        )
    return pinned


def run_graphify(root: Path, exe: Path, *args: str, hook: bool = False) -> None:
    """Run graphify in the checkout, streaming its output to the terminal."""
    print(f"[graphify] graphify {' '.join(args)}", flush=True)
    try:
        result = subprocess.run([str(exe), *args], cwd=root, env=graphify_env(hook=hook))
    except OSError as error:
        raise HookError(f"Could not start {exe}: {error}") from None
    if result.returncode:
        raise HookError(
            f"'graphify {' '.join(args)}' failed (exit {result.returncode}); see its output above."
        )


def digest(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def graph_summary(root: Path) -> str:
    data = json.loads((root / GRAPH).read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    communities = {node.get("community") for node in nodes if node.get("community") is not None}
    return f"{len(nodes)} nodes, {len(data.get('links', []))} edges, {len(communities)} communities"


def community_labels(root: Path) -> dict[str, str]:
    """Return {community id: name} as recorded on graph.json's nodes.

    graphify keeps curated names in .graphify_labels.json and its automatic
    names in .graphify_labels.pending.json, but writes both onto every node as
    community_name. The wiki and call-flow exports read a single labels file, so
    they get this merged view; with the curated file alone they would print
    "Community N".
    """
    data = json.loads((root / GRAPH).read_text(encoding="utf-8"))
    labels: dict[str, str] = {}
    for node in data.get("nodes", []):
        cid, name = node.get("community"), node.get("community_name")
        if isinstance(cid, (int, str)) and str(cid).isdigit() and isinstance(name, str) and name:
            labels.setdefault(str(cid), name)
    return labels


def callflow_sections(root: Path) -> list[dict]:
    """Group communities into CALLFLOW_AREAS by where most of their nodes live.

    Computed from graph.json on every export, so new communities never need a
    hand-maintained list. Communities made only of external symbols, or of
    files outside the listed areas, go to "Other".
    """
    data = json.loads((root / GRAPH).read_text(encoding="utf-8"))
    votes: dict[str, dict[int, int]] = {}
    for node in data.get("nodes", []):
        cid = node.get("community")
        if cid is None:
            continue
        source = str(node.get("source_file") or "").replace("\\", "/")
        counts = votes.setdefault(str(cid), {})
        for area, (prefix, _, _) in enumerate(CALLFLOW_AREAS):
            if source.startswith(prefix):
                counts[area] = counts.get(area, 0) + 1
                break
    sections = [{"id": sid, "name": name, "communities": []} for _, sid, name in CALLFLOW_AREAS]
    other = {"id": "other", "name": "Other", "communities": []}
    for cid in sorted(votes, key=lambda value: (len(value), value)):
        counts = votes[cid]
        if counts:
            best = min(counts, key=lambda area: (-counts[area], area))
            sections[best]["communities"].append(cid)
        else:
            other["communities"].append(cid)
    return [section for section in (*sections, other) if section["communities"]]


def export_views(root: Path, exe: Path, *, hook: bool = False) -> None:
    """Regenerate the wiki, call-flow and tree views from graph.json."""
    labels, sections = root / EXPORT_LABELS, root / EXPORT_SECTIONS
    labels.write_text(json.dumps(community_labels(root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    sections.write_text(json.dumps(callflow_sections(root), indent=2) + "\n", encoding="utf-8")
    try:
        run_graphify(root, exe, "export", "wiki", "--labels", EXPORT_LABELS, hook=hook)
        run_graphify(
            root, exe, "export", "callflow-html", "--labels", EXPORT_LABELS,
            "--sections", EXPORT_SECTIONS, "--output", CALLFLOW, hook=hook,
        )
        run_graphify(root, exe, "tree", "--output", TREE, "--label", root.name, hook=hook)
    finally:
        labels.unlink(missing_ok=True)
        sections.unlink(missing_ok=True)


def local_path_needles(root: Path) -> list[str]:
    """Spellings of this checkout's and the home folder's paths, as outputs may hold them."""
    needles: set[str] = set()
    for base in (root, Path.home()):
        text = str(base.resolve())
        for variant in (text, text.replace("\\", "/"), text.replace("\\", "\\\\")):
            # Very short paths such as /root would match unrelated text. Windows
            # paths are compared case-insensitively (lower(), not normcase(),
            # which would turn the forward-slash spelling back into backslashes).
            if len(variant) >= 8:
                needles.add(variant.lower() if os.name == "nt" else variant)
    return sorted(needles)


def check_no_local_paths(root: Path, changed_outputs: list[str]) -> None:
    """Refuse changed outputs that embed this machine's paths: the repository is public.

    Only changed or new outputs are read; unchanged ones were checked when they
    were committed. Git-ignored files (caches, manifests) never reach a commit.
    """
    needles = local_path_needles(root)
    offenders = []
    for name in changed_outputs:
        path = root / name
        if not path.is_file():
            continue  # a deleted output
        text = path.read_text(encoding="utf-8", errors="replace")
        if os.name == "nt":
            text = text.lower()
        if any(needle in text for needle in needles):
            offenders.append(name)
    if offenders:
        raise HookError(
            "These graph outputs contain a local path (this checkout or your home folder): "
            + ", ".join(offenders)
            + ". Nothing was committed. Find what put the path there before committing graphify-out/."
        )


def directory_rules(root: Path) -> tuple[str, ...]:
    """graphify-out/ plus the plain directory rules in .graphifyignore (such as tests/).

    Changes under these paths cannot alter the code graph, so they do not block
    the follow-up commit. Rules with wildcards or negation are not interpreted:
    changes they cover still block the commit, which is the safe direction.
    """
    prefixes = [f"{OUTPUT}/"]
    try:
        lines = (root / ".graphifyignore").read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    for line in lines:
        rule = line.strip()
        if rule.endswith("/") and not rule.startswith(("#", "!")) and not any(c in rule for c in "*?[\\"):
            prefixes.append(rule.lstrip("/"))
    return tuple(prefixes)


def working_changes(root: Path) -> tuple[list[str], list[str]]:
    """Return (changed graph outputs, other uncommitted paths graphify may have read).

    One git status call answers both questions. Git-ignored files are not
    listed, and gitlinks (the agent worktrees under .claude/) are skipped.
    """
    status = git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=all")
    entries = status.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if len(entry) < 4:
            continue
        paths.append(entry[3:])
        if "R" in entry[:2] or "C" in entry[:2]:
            # Renames and copies are followed by their source path.
            if index < len(entries) and entries[index]:
                paths.append(entries[index])
            index += 1
    outputs = [path for path in paths if path.startswith(f"{OUTPUT}/")]
    excluded = directory_rules(root)
    return outputs, [path for path in paths if not path.startswith(excluded)]


def commit_outputs(root: Path, head: str) -> None:
    """Record graphify-out/ in its own commit; never touches other paths or remotes."""
    message = f"{COMMIT_PREFIX}{head[:12]}"
    git(root, "add", "-A", "--", OUTPUT)
    env = os.environ.copy()
    env[ACTIVE_ENV] = "1"
    git(root, "commit", "--no-verify", "--quiet", "-m", message, "--", OUTPUT, env=env)
    print(f"[graphify] Committed the refreshed graph separately: '{message}'. Nothing was pushed.")


def refresh(root: Path, exe: Path, *, commit: bool, hook: bool = False, head: str | None = None) -> None:
    """Update the graph incrementally, re-export the views and optionally commit.

    The follow-up commit is made only when nothing else is uncommitted that
    graphify could have read; otherwise a committed graph could describe code
    that was never committed.
    """
    require_pinned(root, exe)
    output, graph = root / OUTPUT, root / GRAPH
    if output.is_symlink() or not graph.is_file():
        raise HookError(
            f"No {GRAPH} in this checkout (or {OUTPUT} is a link). Build it once with "
            f"'{HELPER} build', review it, then commit {OUTPUT}/."
        )
    before = digest(graph)
    run_graphify(root, exe, "update", ".", hook=hook)
    views_missing = any(not (root / view).is_file() for view in (WIKI_INDEX, CALLFLOW, TREE))
    if digest(graph) != before or views_missing:
        export_views(root, exe, hook=hook)
    else:
        print("[graphify] graph.json unchanged; views left as they are.")
    outputs, blocking = working_changes(root)
    check_no_local_paths(root, outputs)
    print(f"[graphify] Graph: {graph_summary(root)}.")
    if not commit:
        return
    if not outputs:
        print("[graphify] Graph outputs already match this commit; nothing to commit.")
        return
    if blocking:
        shown = ", ".join(blocking[:5]) + (f" and {len(blocking) - 5} more" if len(blocking) > 5 else "")
        print(
            f"[graphify] Refreshed {OUTPUT}/ but did not commit it: uncommitted changes "
            f"({shown}) may be in the graph. Commit or stash them; the next commit "
            f"refreshes and commits the graph (or run '{HELPER} refresh --commit')."
        )
        return
    commit_outputs(root, head or git(root, "rev-parse", "HEAD").strip())


def build(root: Path, explicit: str | None) -> None:
    """Rebuild the graph from scratch, then export every view. Does not commit."""
    exe = resolve_graphify(explicit)
    require_pinned(root, exe)
    output = root / OUTPUT
    if output.is_symlink():
        raise HookError(f"{OUTPUT} is a link; build into a real folder in this checkout.")
    for name in REBUILT_STATE:
        (output / name).unlink(missing_ok=True)
    # extract records the code-only scope in .graphify_build.json (which keeps
    # later updates from also scanning Markdown) and fills the extraction cache,
    # but writes no community names, report or graph.html. update writes those
    # only when it has no identical graph to compare with, so extract's graph
    # (and its analysis sidecar, which update would leave stale) goes first.
    run_graphify(root, exe, "extract", ".", "--code-only", "--force")
    for name in ("graph.json", ".graphify_analysis.json"):
        (output / name).unlink(missing_ok=True)
    run_graphify(root, exe, "update", ".", "--force")
    export_views(root, exe)
    outputs, _ = working_changes(root)
    check_no_local_paths(root, outputs)
    print(
        f"[graphify] Built {graph_summary(root)}. Review {OUTPUT}/, then commit it: "
        f"git add {OUTPUT} && git commit -m \"chore(graphify): rebuild code graph\""
    )


def operation_in_progress(git_dir: Path) -> str | None:
    for name, label in OPERATIONS:
        if (git_dir / name).exists():
            return label
    return None


def changed_in_head(root: Path) -> list[str]:
    """Paths the last commit changed (none for a merge commit, which shows no diff here)."""
    listing = git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "-z", "HEAD")
    return [name for name in listing.split("\0") if name]


def run_hook(path: Path, explicit: str | None) -> None:
    """Post-commit entry point: decide whether this commit needs a refresh."""
    if os.environ.get(SKIP_ENV, "").strip() == "1":
        print(f"[graphify] {SKIP_ENV}=1: graph not refreshed for this commit.")
        return
    repo = repo_state(path, with_head=True)
    if repo.linked_worktree:
        print("[graphify] Linked worktree: graph not refreshed here (refresh it in the main checkout).")
        return
    operation = operation_in_progress(repo.git_dir)
    if operation:
        print(
            f"[graphify] {operation} is in progress: graph not refreshed. When it is "
            f"finished, run '{HELPER} refresh --commit'."
        )
        return
    names = changed_in_head(repo.root)
    if names and all(name.startswith(f"{OUTPUT}/") for name in names):
        return  # a commit of graph outputs only
    excluded = directory_rules(repo.root)
    if names and all(name.startswith(excluded) or name.lower().endswith(DOC_SUFFIXES) for name in names):
        print("[graphify] Only documentation or folders outside the graph changed; graph not refreshed.")
        return
    refresh(repo.root, resolve_graphify(explicit), commit=True, hook=True, head=repo.head)


def hook_bytes(graphify: Path, python: Path | None = None, helper: Path | None = None) -> bytes:
    """Return the post-commit hook, pinning this interpreter, this helper and graphify.

    Git for Windows also runs hooks with sh. Forward slashes and shlex quoting
    keep paths with spaces or apostrophes intact. The checkout is resolved when
    the hook runs, so one hook serves every worktree that shares it.
    """
    command = [
        (python or Path(sys.executable)).absolute().as_posix(),
        (helper or Path(__file__)).resolve().as_posix(),
        "run", "--graphify", graphify.absolute().as_posix(),
    ]
    body = HEADER + (
        "# Installed by scripts/graphify_hook.py: refreshes graphify-out/ after each commit\n"
        "# and records it in a separate follow-up commit. Never pushes; a failure never\n"
        f"# undoes the commit. Skip it once with {SKIP_ENV}=1.\n"
        "exec " + shlex.join(command) + "\n"
    ).encode("utf-8")
    return body + CHECKSUM + hashlib.sha256(body).hexdigest().encode("ascii") + b"\n"


def is_owned(content: bytes) -> bool:
    """Recognize an unedited hook from this helper (not a security signature).

    The checksum protects hand-edited hooks from being replaced or deleted.
    """
    body, separator, checksum = content.rpartition(CHECKSUM)
    return (
        body.startswith(HEADER)
        and bool(separator)
        and checksum == hashlib.sha256(body).hexdigest().encode("ascii") + b"\n"
    )


def hook_command(content: bytes) -> list[str]:
    for line in content.decode("utf-8", "replace").splitlines():
        if line.startswith("exec "):
            return shlex.split(line[len("exec "):])
    return []


def existing_hook(path: Path) -> bytes | None:
    if path.is_symlink():
        raise HookError(f"{path} is a link; it was left untouched (preserved).")
    return path.read_bytes() if path.exists() else None


def require_owned(path: Path, content: bytes) -> None:
    if not is_owned(content):
        raise HookError(
            f"{path} belongs to another tool or was edited, so it was preserved. "
            "Merge it with the graphify hook by hand, or move it aside after review."
        )


def make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | 0o111)


def install(repo: Repo, explicit: str | None) -> None:
    """Install post-commit only; installing the identical hook again changes nothing."""
    exe = resolve_graphify(explicit)
    require_pinned(repo.root, exe)
    path = hook_path(repo)
    content = existing_hook(path)
    desired = hook_bytes(exe)
    if content is not None:
        require_owned(path, content)
        if content != desired:
            raise HookError(
                f"{path} already pins other paths. Run '{HELPER} uninstall', then "
                f"'{HELPER} install' to pin the current ones."
            )
        make_executable(path)
        print(f"Already installed: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:  # never overwrite a hook created meanwhile
        stream.write(desired)
    make_executable(path)
    print(f"Installed the post-commit hook: {path}\n  graphify: {exe}\n  Python: {sys.executable}")


def uninstall(repo: Repo) -> None:
    """Remove only this helper's unedited hook."""
    path = hook_path(repo)
    content = existing_hook(path)
    if content is None:
        print(f"Not installed: {path}")
        return
    require_owned(path, content)
    path.unlink()
    print(f"Removed: {path}")


def status(repo: Repo, explicit: str | None) -> bool:
    """Print graphify, hook and graph state; return True when all is ready."""
    ready = True
    root = repo.root
    pinned = read_pin(root)
    print(f"Pinned graphify: {pinned} ({PIN_FILE})")
    path = hook_path(repo)
    content = existing_hook(path)
    hook_exe: str | None = None
    if content is None:
        ready = False
        print(f"Hook: not installed ({path}). Install it with '{HELPER} install'.")
    elif not is_owned(content):
        ready = False
        print(f"Hook: {path} belongs to another tool or was edited, so it was preserved.")
    else:
        command = hook_command(content)
        python_path = command[0] if command else ""
        hook_exe = command[command.index("--graphify") + 1] if "--graphify" in command else None
        print(f"Hook: installed (post-commit only): {path}")
        if not Path(python_path).is_file():
            ready = False
            print(f"  Its Python is missing ({python_path}); run '{HELPER} uninstall', then 'install'.")
        if os.name != "nt" and not os.access(path, os.X_OK):
            ready = False
            print(f"  It is not executable; run '{HELPER} install' again.")
    try:
        exe = resolve_graphify(explicit or hook_exe)
        found = installed_version(exe)
        if found == pinned:
            print(f"graphify: {found} at {exe}")
        else:
            ready = False
            print(
                f"graphify: {found} at {exe} does NOT match the pin. Fix: uv tool install "
                f"--reinstall {PACKAGE} -c {PIN_FILE}"
            )
    except HookError as error:
        ready = False
        print(f"graphify: {error}")
    if (root / GRAPH).is_file():
        print(f"Graph: {graph_summary(root)} ({GRAPH})")
    else:
        ready = False
        print(f"Graph: missing. Build it with '{HELPER} build', review it, then commit {OUTPUT}/.")
    if repo.linked_worktree:
        print("Note: this is a linked worktree; the shared hook skips commits made here.")
    return ready


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog="Commands" + __doc__.split("Commands", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo", type=Path, default=Path.cwd(),
        help="any folder inside the checkout (default: the current folder)",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name, text in (
        ("install", "install the post-commit hook"),
        ("uninstall", "remove the hook installed by this helper"),
        ("status", "report graphify, hook and graph state"),
        ("build", "rebuild graphify-out/ from scratch (does not commit)"),
        ("refresh", "refresh graphify-out/ incrementally"),
        ("run", "post-commit entry point"),
    ):
        command = commands.add_parser(name, help=text)
        if name != "uninstall":
            command.add_argument(
                "--graphify",
                help="graphify executable (default: PATH, this Python's folder, then ~/.local/bin)",
            )
        if name == "refresh":
            command.add_argument(
                "--commit", action="store_true",
                help="record changed outputs in a separate commit when nothing else is uncommitted",
            )
    args = parser.parse_args(argv)
    if args.command == "run" and os.environ.get(ACTIVE_ENV):
        return 0  # the hook run triggered by our own follow-up commit
    try:
        if args.command == "run":
            run_hook(args.repo, args.graphify)
            return 0
        repo = repo_state(args.repo)
        if args.command == "install":
            install(repo, args.graphify)
        elif args.command == "uninstall":
            uninstall(repo)
        elif args.command == "status":
            return 0 if status(repo, args.graphify) else 1
        elif args.command == "build":
            build(repo.root, args.graphify)
        else:
            refresh(repo.root, resolve_graphify(args.graphify), commit=args.commit)
    except HookError as error:
        print(f"[graphify] {error}", file=sys.stderr)
        if args.command == "run":
            print("[graphify] Your commit is kept; only the graph refresh was skipped.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
