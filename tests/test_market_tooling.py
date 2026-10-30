"""Market tooling guards (offline): default outputs of the market scripts and the Deploy Site triggers.

The website's Market Pricing file is built only by scripts/build_ontario_market.py, which the Ontario Price Archive
workflow runs with its default --output; the legacy Phase 6A generator, run by hand, defaults to a git-ignored
scratch file under logs/. Deploy Site also follows the archive workflow, after successful runs only. Both are user
decisions of 2026-10-30.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
DEPLOY_WORKFLOW = WORKFLOWS / "deploy.yml"
SCRAPE_WORKFLOW = WORKFLOWS / "scrape.yml"
ARCHIVE_WORKFLOW = WORKFLOWS / "ontario-price-archive.yml"
SITE_MARKET_FILE = ROOT / "site" / "data" / "market_pricing_ontario.json"
LEGACY_SCRATCH_FILE = ROOT / "logs" / "market_pricing_legacy_2020_2024.json"
SUCCESS_ONLY = "github.event_name != 'workflow_run' || github.event.workflow_run.conclusion == 'success'"
MAIN_CHECKOUT = "ref: ${{ github.event_name == 'workflow_run' && 'main' || github.ref }}"


def _script(name):
    """scripts/<name>.py, reusing a copy already loaded by another test module or script (as the scripts' own
    loaders do), so collecting this module never swaps the module object that other modules bind to."""
    path = ROOT / "scripts" / f"{name}.py"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    assert Path(module.__file__).resolve() == path.resolve()
    return module


gmp = _script("generate_market_pricing")
bom = _script("build_ontario_market")


def _workflow_name(path):
    """The top-level name: of a workflow file, which is what workflow_run triggers match."""
    match = re.search(r"(?m)^name:[ \t]*(.+?)[ \t]*$", path.read_text(encoding="utf-8"))
    assert match, f"{path.name} has no top-level name"
    return match.group(1).strip("\"'")


def _workflow_run_sources(text):
    """Workflows listed under on.workflow_run; deploy.yml writes them as one flow-style list."""
    match = re.search(r"(?m)^  workflow_run:\n(?:    #[^\n]*\n)*    workflows: \[([^\]\n]*)\]\n"
                      r"    types: \[completed\]$", text)
    assert match, "deploy.yml must list the workflow_run workflows in one [...] list followed by types: [completed]"
    return [name.strip().strip("\"'") for name in match.group(1).split(",")]


def test_legacy_generator_defaults_to_a_git_ignored_scratch_file():
    assert gmp.DEFAULT_OUTPUT == LEGACY_SCRATCH_FILE
    assert not gmp.DEFAULT_OUTPUT.is_relative_to(ROOT / "site")
    assert gmp.parse_args([]).output == LEGACY_SCRATCH_FILE
    ignored = {line.strip() for line in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
    assert "logs/" in ignored


def test_legacy_writer_creates_missing_directories_and_leaves_no_temporary_file(tmp_path):
    output = tmp_path / "fresh-clone" / "logs" / LEGACY_SCRATCH_FILE.name
    document = {"metadata": {"province": "ON"}, "hourly_surface": []}
    gmp.write_document(output, document)
    assert json.loads(output.read_text(encoding="utf-8")) == document
    assert [path.name for path in output.parent.iterdir()] == [output.name]


def test_rolling_builder_still_writes_the_site_file_that_the_archive_workflow_commits():
    assert bom.DEFAULT_OUTPUT == SITE_MARKET_FILE
    assert bom.parse_args([]).output == SITE_MARKET_FILE
    text = ARCHIVE_WORKFLOW.read_text(encoding="utf-8")
    (build,) = re.findall(r"(?m)^ +run: (python scripts/build_ontario_market\.py[^\n]*)$", text)
    assert "--output" not in build
    added = [line.split() for line in re.findall(r"(?m)^ +git add ([^\n]+)$", text)]
    assert any(SITE_MARKET_FILE.relative_to(ROOT).as_posix() in paths for paths in added)


def test_deploy_follows_the_monthly_scrape_and_the_ontario_price_archive_by_name():
    sources = _workflow_run_sources(DEPLOY_WORKFLOW.read_text(encoding="utf-8"))
    assert sorted(sources) == ["Monthly Scrape", "Ontario Price Archive"]
    # A renamed workflow would silently stop triggering deploys.
    assert {_workflow_name(SCRAPE_WORKFLOW), _workflow_name(ARCHIVE_WORKFLOW)} == set(sources)


def test_deploy_runs_only_after_successful_runs_and_checks_out_main():
    text = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    assert f"\n  deploy:\n    if: {SUCCESS_ONLY}\n" in text
    assert f"\n          {MAIN_CHECKOUT}\n" in text
