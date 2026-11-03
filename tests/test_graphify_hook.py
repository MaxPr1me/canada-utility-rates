"""Tests for scripts/graphify_hook.py in temporary Git repositories.

A small stand-in for graphify writes deterministic outputs and logs every call,
so these tests need Git but neither graphify nor the network. They run in CI
before every Monthly Scrape, so they must stay hermetic: no global Git
configuration, no files outside pytest's temporary folders. Each test copies a
template repository built once per module, because starting git and Python is
slow on some Windows machines.
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "graphify_hook.py"
GIT = shutil.which("git")

_spec = importlib.util.spec_from_file_location("graphify_hook", HELPER)
graphify_hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(graphify_hook)

PIN = graphify_hook.read_pin(ROOT)
COMMITTED = {
    "graphify-out/graph.json",
    "graphify-out/GRAPH_REPORT.md",
    "graphify-out/graph.html",
    "graphify-out/GRAPH_TREE.html",
    "graphify-out/GRAPH_CALLFLOW.html",
    "graphify-out/wiki/index.md",
    "graphify-out/.graphify_build.json",
    "graphify-out/.graphify_labels.json",
}

pytestmark = pytest.mark.skipif(GIT is None, reason="Git is required for the hook tests")

FAKE_GRAPHIFY = r'''
"""Stand-in for graphify: small deterministic outputs, one log line per call."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

args = sys.argv[1:]
with open(os.environ["FAKE_GRAPHIFY_LOG"], "a", encoding="utf-8") as stream:
    stream.write(json.dumps({
        "args": args,
        "backend": os.environ.get("GRAPHIFY_BACKEND"),
        "hashseed": os.environ.get("PYTHONHASHSEED"),
    }) + "\n")
if args[:1] == ["--version"]:
    print("graphify " + os.environ.get("FAKE_GRAPHIFY_VERSION", "0.0.0"))
    sys.exit(0)

root = Path.cwd()
out = root / os.environ["GRAPHIFY_OUT"]


def option(name):
    return args[args.index(name) + 1]


if args[0] in ("extract", "update"):
    if args[0] == "update" and os.environ.get("FAKE_GRAPHIFY_FAIL"):
        print("controlled graphify failure", file=sys.stderr)
        sys.exit(3)
    out.mkdir(exist_ok=True)
    nodes = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(("tests/", "graphify-out/", ".git/")):
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:8]
        nodes.append({"id": f"{rel}:{digest}", "community": 0, "community_name": "app core"})
    if os.environ.get("FAKE_GRAPHIFY_LEAK"):
        nodes.append({"id": str(root), "community": 0, "community_name": "app core"})
    graph = json.dumps({"nodes": nodes, "links": []}, indent=1, sort_keys=True) + "\n"
    target = out / "graph.json"
    if not target.is_file() or target.read_text(encoding="utf-8") != graph:
        target.write_text(graph, encoding="utf-8")
        (out / "GRAPH_REPORT.md").write_text(f"# Report\n{len(nodes)} nodes\n", encoding="utf-8")
        (out / "graph.html").write_text(f"<p>{len(nodes)} nodes</p>\n", encoding="utf-8")
    # Local-only files hold absolute paths, like graphify's; they must stay ignored.
    (out / ".graphify_root").write_text(str(root), encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({"root": str(root)}), encoding="utf-8")
    (out / "cache").mkdir(exist_ok=True)
    (out / "cache" / "entry.json").write_text(json.dumps({"root": str(root)}), encoding="utf-8")
    (out / ".graphify_labels.json").write_text("{}\n", encoding="utf-8")
    if args[0] == "extract":
        (out / ".graphify_build.json").write_text('{"code_only": true}', encoding="utf-8")
    sys.exit(0)
if args[:2] == ["export", "wiki"]:
    labels = json.loads(Path(option("--labels")).read_text(encoding="utf-8"))
    (out / "wiki").mkdir(exist_ok=True)
    (out / "wiki" / "index.md").write_text(
        "# Wiki\n" + json.dumps(labels, sort_keys=True) + "\n", encoding="utf-8"
    )
    sys.exit(0)
if args[:2] == ["export", "callflow-html"]:
    # Like graphify's page, this one records when it was generated.
    Path(option("--output")).write_text(f"<p>call flow {time.time()}</p>\n", encoding="utf-8")
    sys.exit(0)
if args[0] == "tree":
    Path(option("--output")).write_text(f"<p>tree {option('--label')}</p>\n", encoding="utf-8")
    sys.exit(0)
print(f"fake graphify: unexpected arguments {args}", file=sys.stderr)
sys.exit(2)
'''


def clean_env() -> dict[str, str]:
    """Process environment without Git, graphify or stand-in overrides."""
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("GIT_", "GRAPHIFY_", "FAKE_GRAPHIFY_"))
    }
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    return env


class Checkout:
    """A temporary repository using this project's graphify configuration."""

    def __init__(self, root: Path, graphify: Path, log: Path):
        self.root, self.graphify, self.log = root, graphify, log
        self.env = clean_env()
        self.env.update(FAKE_GRAPHIFY_VERSION=PIN, FAKE_GRAPHIFY_LOG=str(log))

    @property
    def hook(self) -> Path:
        return self.root / ".git" / "hooks" / "post-commit"

    def git(self, *args: str, cwd: Path | None = None, check: bool = True, **extra_env: str):
        result = subprocess.run(
            [GIT, "-C", str(cwd or self.root), *args],
            capture_output=True, text=True, env={**self.env, **extra_env},
        )
        if check and result.returncode:
            raise AssertionError(f"git {args} failed:\n{result.stdout}\n{result.stderr}")
        return result

    def helper(self, *args: str, check: bool = True, graphify: bool = True, **extra_env: str):
        command = [sys.executable, str(HELPER), "--repo", str(self.root), *args]
        if graphify and args[0] != "uninstall" and "--graphify" not in args:
            command += ["--graphify", str(self.graphify)]
        result = subprocess.run(command, capture_output=True, text=True, env={**self.env, **extra_env})
        if check and result.returncode:
            raise AssertionError(f"helper {args} failed:\n{result.stdout}\n{result.stderr}")
        return result

    def commit(self, name: str, text: str, message: str, **extra_env: str) -> str:
        """Commit one file as a person would (the hook runs); return Git's output."""
        (self.root / name).write_text(text, encoding="utf-8")
        self.git("add", "--", name)
        result = self.git("commit", "-m", message, **extra_env)
        return result.stdout + result.stderr

    def subjects(self, count: int) -> list[str]:
        return self.git("log", f"-{count}", "--format=%s").stdout.splitlines()

    def calls(self) -> list[dict]:
        if not self.log.is_file():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def commands(self) -> list[str]:
        """The graphify commands run so far, without version checks."""
        return [call["args"][0] for call in self.calls() if call["args"][0] != "--version"]

    def tracked_outputs(self) -> set[str]:
        return set(self.git("ls-files", "graphify-out").stdout.split())


@pytest.fixture(scope="module")
def template(tmp_path_factory) -> Checkout:
    """A committed project with a built graph, created once and copied per test."""
    base = tmp_path_factory.mktemp("graphify hook template")
    tool = base / "tool bin"
    tool.mkdir()
    script = tool / "fake_graphify.py"
    script.write_text(FAKE_GRAPHIFY, encoding="utf-8")
    if os.name == "nt":
        graphify = tool / "graphify.cmd"
        graphify.write_text(f'@"{sys.executable}" "{script}" %*\n', encoding="utf-8")
    else:
        graphify = tool / "graphify"
        graphify.write_text(
            "#!/bin/sh\nexec " + shlex.join([sys.executable, str(script)]) + ' "$@"\n',
            encoding="utf-8",
        )
        graphify.chmod(0o755)
    root = base / "repo's source"
    root.mkdir()
    repo = Checkout(root, graphify, base / "template-calls.jsonl")
    repo.git("init", "--initial-branch=main")
    for key, value in (
        ("user.name", "Hook Test"), ("user.email", "hook-test@example.invalid"),
        ("commit.gpgsign", "false"), ("core.autocrlf", "false"),
    ):
        repo.git("config", key, value)
    for name in (".gitignore", ".gitattributes", ".graphifyignore", graphify_hook.PIN_FILE):
        shutil.copyfile(ROOT / name, root / name)
    (root / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_app.py").write_text("def test_app():\n    pass\n", encoding="utf-8")
    repo.git("add", "-A")
    repo.git("commit", "-m", "initial")
    repo.helper("build")
    repo.git("add", "-A", "--", "graphify-out")
    repo.git("commit", "-m", "build graph")
    return repo


@pytest.fixture
def repo(template: Checkout, tmp_path: Path) -> Checkout:
    copy = tmp_path / "repo's source"
    shutil.copytree(template.root, copy)
    return Checkout(copy, template.graphify, tmp_path / "calls.jsonl")


def test_pin_and_ignore_rules_are_consistent():
    assert re.fullmatch(r"\d+\.\d+\.\d+", PIN)
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "graphify-out/*" in gitignore
    for path in COMMITTED:
        entry = "!graphify-out/wiki/" if path.startswith("graphify-out/wiki/") else f"!{path}"
        assert entry in gitignore
    assert "tests/" in graphify_hook.directory_rules(ROOT)


def test_build_commits_only_the_allowlisted_outputs(template: Checkout):
    assert template.tracked_outputs() == COMMITTED
    graph = json.loads((template.root / "graphify-out" / "graph.json").read_text(encoding="utf-8"))
    assert [node["id"].split(":")[0] for node in graph["nodes"]] == ["app.py"]
    assert "app core" in (template.root / "graphify-out" / "wiki" / "index.md").read_text(encoding="utf-8")
    assert not (template.root / graphify_hook.EXPORT_LABELS).exists()
    assert not (template.root / graphify_hook.EXPORT_SECTIONS).exists()
    assert template.commands() == ["extract", "update", "export", "export", "tree"]
    assert all(call["backend"] == "none" and call["hashseed"] == "0" for call in template.calls())


def test_callflow_sections_follow_project_areas(tmp_path: Path):
    nodes = [
        {"community": 0, "source_file": "scrapers/utilities/bc_hydro.py"},
        {"community": 0, "source_file": "scrapers/utilities/nb_power.py"},
        {"community": 0, "source_file": "scrapers/base.py"},
        {"community": 1, "source_file": "scrapers/utils/parsing.py"},
        {"community": 2, "source_file": "site/js/app.js"},
        {"community": 3, "source_file": ""},
    ]
    (tmp_path / "graphify-out").mkdir()
    (tmp_path / "graphify-out" / "graph.json").write_text(json.dumps({"nodes": nodes}), encoding="utf-8")
    sections = {s["id"]: s["communities"] for s in graphify_hook.callflow_sections(tmp_path)}
    assert sections == {
        "utility-scrapers": ["0"], "scraper-framework": ["1"], "website": ["2"], "other": ["3"],
    }


def test_install_lifecycle_manages_only_its_own_post_commit(repo: Checkout):
    status = repo.helper("status", check=False)
    assert status.returncode == 1 and "not installed" in status.stdout
    mismatch = repo.helper("install", check=False, FAKE_GRAPHIFY_VERSION="0.0.1")
    assert mismatch.returncode == 1 and f"is not the pinned {PIN}" in mismatch.stderr
    assert not repo.hook.exists()

    repo.helper("install")
    content = repo.hook.read_bytes()
    assert graphify_hook.is_owned(content) and b"\r\n" not in content
    assert "Already installed" in repo.helper("install").stdout
    assert repo.hook.read_bytes() == content
    status = repo.helper("status", graphify=False)  # checks the graphify the hook pins
    assert "installed (post-commit only)" in status.stdout and PIN in status.stdout
    hooks = [path.name for path in repo.hook.parent.iterdir() if not path.name.endswith(".sample")]
    assert hooks == ["post-commit"]
    assert repo.git("config", "--get-regexp", r"^merge\.", check=False).returncode == 1
    repo.helper("uninstall")
    assert not repo.hook.exists()
    assert "Not installed" in repo.helper("uninstall").stdout

    for foreign in (b"#!/bin/sh\nexit 0\n", graphify_hook.hook_bytes(repo.graphify) + b"# local edit\n"):
        repo.hook.write_bytes(foreign)
        for command in ("install", "uninstall"):
            result = repo.helper(command, check=False)
            assert result.returncode == 1 and "preserved" in result.stderr
        status = repo.helper("status", check=False)
        assert status.returncode == 1 and "preserved" in status.stdout
        assert repo.hook.read_bytes() == foreign


def test_commits_refresh_and_record_the_graph(repo: Checkout):
    repo.helper("install")
    repo.commit("app.py", "def main():\n    return 2\n", "change app")
    code_commit = repo.git("rev-parse", "--short=12", "HEAD~1").stdout.strip()
    assert repo.subjects(3) == [
        f"chore(graphify): refresh code graph for {code_commit}", "change app", "build graph",
    ]
    changed = repo.git("show", "--name-only", "--format=", "HEAD").stdout.split()
    assert "graphify-out/graph.json" in changed
    assert all(name.startswith("graphify-out/") for name in changed)
    assert repo.tracked_outputs() == COMMITTED
    assert repo.git("status", "--porcelain").stdout == ""
    assert repo.commands() == ["update", "export", "export", "tree"]
    assert all(call["backend"] == "none" for call in repo.calls())

    # A documentation-only commit cannot change a code-only graph: graphify is skipped.
    output = repo.commit("README.md", "# Changed\n", "docs only")
    assert repo.subjects(1) == ["docs only"]
    assert "Only documentation" in output
    assert len(repo.commands()) == 4

    # Other commits that leave the graph unchanged get a refresh but no graph commit.
    repo.commit("settings.cfg", "[demo]\n", "settings only")
    assert repo.subjects(1) == ["settings only"]
    assert repo.commands()[4:] == ["update"]
    assert repo.git("status", "--porcelain").stdout == ""

    # A hand-made commit of graph outputs only does not trigger a refresh.
    (repo.root / "graphify-out" / "GRAPH_REPORT.md").write_text("# Edited\n", encoding="utf-8")
    repo.git("add", "graphify-out")
    repo.git("commit", "-m", "graph only")
    assert repo.subjects(1) == ["graph only"]
    assert len(repo.commands()) == 5


def test_uncommitted_code_blocks_the_graph_commit(repo: Checkout):
    repo.helper("install")
    (repo.root / "tests" / "test_extra.py").write_text("x = 1\n", encoding="utf-8")
    (repo.root / "draft.py").write_text("def draft():\n    pass\n", encoding="utf-8")
    output = repo.commit("app.py", "def main():\n    return 3\n", "change app")
    assert repo.subjects(1) == ["change app"]
    assert "did not commit" in output and "draft.py" in output
    assert "test_extra.py" not in output  # tests/ is outside the graph
    assert repo.git("status", "--porcelain", "--", "graphify-out").stdout.strip()
    (repo.root / "draft.py").unlink()
    repo.commit("app.py", "def main():\n    return 4\n", "change app again")
    assert repo.subjects(1)[0].startswith(graphify_hook.COMMIT_PREFIX)


def test_skips_leave_the_graph_alone(repo: Checkout, tmp_path: Path):
    repo.helper("install")
    output = repo.commit("app.py", "def main():\n    return 5\n", "skipped", GRAPHIFY_SKIP_HOOK="1")
    assert "GRAPHIFY_SKIP_HOOK=1" in output
    linked = tmp_path / "linked tree"
    repo.git("worktree", "add", "-b", "side", str(linked))
    (linked / "app.py").write_text("def main():\n    return 6\n", encoding="utf-8")
    repo.git("add", "app.py", cwd=linked)
    result = repo.git("commit", "-m", "side change", cwd=linked)
    assert "Linked worktree" in result.stdout + result.stderr
    assert repo.subjects(1) == ["skipped"]
    assert repo.commands() == []


def test_problems_keep_the_commit_and_commit_no_graph(repo: Checkout):
    repo.helper("install")
    output = repo.commit("app.py", "def main():\n    return 7\n", "after failure", FAKE_GRAPHIFY_FAIL="1")
    assert repo.subjects(1) == ["after failure"]
    assert "controlled graphify failure" in output and "Your commit is kept" in output

    output = repo.commit("app.py", "def main():\n    return 8\n", "after mismatch", FAKE_GRAPHIFY_VERSION="0.0.1")
    assert repo.subjects(1) == ["after mismatch"]
    assert f"is not the pinned {PIN}" in output
    assert repo.commands() == ["update"]  # the version mismatch ran nothing

    output = repo.commit("app.py", "def main():\n    return 9\n", "leaky", FAKE_GRAPHIFY_LEAK="1")
    assert repo.subjects(1) == ["leaky"]
    assert "contain a local path" in output and "graphify-out/graph.json" in output


def test_missing_graph_or_graphify_is_actionable(repo: Checkout):
    (repo.root / "graphify-out" / "graph.json").unlink()
    result = repo.helper("refresh", check=False)
    assert result.returncode == 1 and "scripts/graphify_hook.py build" in result.stderr
    missing = repo.root.parent / "no such folder" / "graphify"
    result = repo.helper("install", "--graphify", str(missing), check=False)
    assert result.returncode == 1
    assert "uv tool install graphifyy -c requirements-graphify.txt" in result.stderr
    assert not repo.hook.exists()
