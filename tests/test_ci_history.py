"""CI history guards: scripts/check_db_history.py, scripts/pull_history_db.py and the data workflows (offline)."""
import hashlib
import importlib.util
import json
import re
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest

from pipeline.run_scrape import store_results
from scrapers.base import RateComponent, TariffRecord

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema" / "create_tables.sql"
SCRAPE_WORKFLOW = ROOT / ".github" / "workflows" / "scrape.yml"
ARCHIVE_WORKFLOW = ROOT / ".github" / "workflows" / "ontario-price-archive.yml"
SNAPSHOT_COLUMNS = ["id", "scrape_run_id", "tariff_id", "snapshot_date", "tariff_json", "hash", "created_at"]


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check = _load_script("check_db_history")
pull = _load_script("pull_history_db")


@pytest.fixture(autouse=True)
def _offline_and_local(monkeypatch):
    def blocked(*args, **kwargs):
        raise RuntimeError("live network disabled in deterministic tests")

    monkeypatch.setattr(pull.requests, "get", blocked)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)


# -- history databases built like pipeline.run_scrape builds them ------------------------------------

def _record(name, energy, effective="2026-10-01", components=2):
    parts = [RateComponent("energy", "Energy Charge", energy, "$/kWh"),
             RateComponent("fixed", "Monthly Service Charge", 12.5, "$/month")]
    return TariffRecord(utility_name="Test Hydro", province="ON", utility_type="electricity", tariff_name=name,
                        effective_date=effective, notes="Provenance: live_parsed.", components=parts[:components])


def _store_run(db, records):
    with closing(sqlite3.connect(db)) as conn:
        run_id = conn.execute("INSERT INTO scrape_runs (started_at, status) VALUES ('2026-10-16T08:00:00+00:00', "
                              "'completed')").lastrowid
        assert run_id is not None
        conn.commit()
        store_results(records, run_id, conn)


def _execute(db, sql, *params):
    with closing(sqlite3.connect(db)) as conn:
        conn.execute(sql, params)
        conn.commit()


@pytest.fixture
def history_db(tmp_path):
    db = tmp_path / "rates.db"
    with closing(sqlite3.connect(db)) as conn:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
    _store_run(db, [_record("Residential", 0.10), _record("General Service", 0.12)])
    _store_run(db, [_record("Residential", 0.11, effective="2026-11-01")])
    return db


@pytest.fixture
def before(history_db, tmp_path):
    out = tmp_path / "db_before.json"
    assert check.main(["stats", "--db", str(history_db), "--out", str(out)]) == 0
    return out


def _verify(db, before_file):
    return check.main(["verify", "--db", str(db), "--before", str(before_file)])


# -- check_db_history: stats ----------------------------------------------------------------------

def test_stats_records_counts_digest_and_file_hash(history_db, tmp_path, capsys):
    out = tmp_path / "stats.json"
    assert check.main(["stats", "--db", str(history_db), "--out", str(out)]) == 0
    assert "integrity ok" in capsys.readouterr().out
    stats = json.loads(out.read_text(encoding="utf-8"))
    assert stats["integrity_check"] == "ok"
    assert stats["counts"] == {"tariffs": 3, "rate_components": 6, "historical_snapshots": 3, "scrape_runs": 2,
                               "utilities": 1}
    assert stats["max_snapshot_id"] == stats["digest_max_id"] == 3
    assert stats["digest_rows"] == 3
    assert stats["snapshot_columns"] == SNAPSHOT_COLUMNS
    assert re.fullmatch(r"[0-9a-f]{64}", stats["snapshot_digest"])
    assert stats["file_size_bytes"] == history_db.stat().st_size
    assert stats["file_sha256"] == hashlib.sha256(history_db.read_bytes()).hexdigest()


def test_stats_digest_is_deterministic_and_never_writes_the_database(history_db, before):
    data = history_db.read_bytes()
    again = check.read_stats(history_db)
    assert again["snapshot_digest"] == json.loads(before.read_text(encoding="utf-8"))["snapshot_digest"]
    assert history_db.read_bytes() == data


@pytest.mark.parametrize("content, message", [
    (None, "database file not found"),
    (b"This is not a database. " * 200, "not a readable SQLite database"),
    (b"", "has no table(s)"),
])
def test_stats_fails_closed_without_a_usable_database(tmp_path, capsys, content, message):
    db, out = tmp_path / "rates.db", tmp_path / "stats.json"
    if content is not None:
        db.write_bytes(content)
    assert check.main(["stats", "--db", str(db), "--out", str(out)]) == 1
    assert message in capsys.readouterr().err
    assert not out.exists()


def test_stats_fails_when_integrity_check_finds_a_damaged_page(history_db, tmp_path, capsys):
    data = bytearray(history_db.read_bytes())
    page_size = int.from_bytes(data[16:18], "big")
    page_size = 65536 if page_size == 1 else page_size
    data[-page_size:-page_size + 16] = b"\xff" * 16
    history_db.write_bytes(bytes(data))
    out = tmp_path / "stats.json"
    assert check.main(["stats", "--db", str(history_db), "--out", str(out)]) == 1
    err = capsys.readouterr().err
    assert "integrity_check failed" in err or "not a readable SQLite database" in err
    assert not out.exists()


# -- check_db_history: verify ---------------------------------------------------------------------

def test_verify_passes_when_a_run_appends_snapshots_and_replaces_components(history_db, before, capsys):
    capsys.readouterr()
    _store_run(history_db, [_record("Residential", 0.115, effective="2026-11-01", components=1),
                            _record("General Service", 0.12, components=1)])
    assert _verify(history_db, before) == 0
    out = capsys.readouterr().out.strip()
    assert out == (f"Database history: History verified, 3 earlier snapshots unchanged: tariff versions 3 (+0), "
                   f"snapshots 5 (+2), scrape runs 3 (+1), utilities 1 (+0), rate components 4 (-2); "
                   f"size {history_db.stat().st_size:,} bytes; "
                   f"sha256 {hashlib.sha256(history_db.read_bytes()).hexdigest()}")


def test_verify_passes_for_an_unchanged_database(history_db, before):
    assert _verify(history_db, before) == 0


def test_verify_notice_on_github_is_one_public_annotation(history_db, before, capsys, monkeypatch):
    capsys.readouterr()
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    _store_run(history_db, [_record("Small Business", 0.13)])
    assert _verify(history_db, before) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("::notice title=Database history::History verified, 3 earlier snapshots unchanged: "
                               "tariff versions 4 (+1), snapshots 4 (+1), scrape runs 3 (+1), ")
    assert lines[0].endswith(f"sha256 {hashlib.sha256(history_db.read_bytes()).hexdigest()}")


def test_notice_and_error_escape_workflow_command_characters():
    assert check.format_notice("50% done\r\nnext", True) == "::notice title=Database history::50%25 done%0D%0Anext"
    assert check.format_error("a\nb", True) == "::error title=Database history::a%0Ab"
    assert check.format_notice("50% done", False) == "Database history: 50% done"
    assert check.format_error("bad", False) == "Database history check FAILED: bad"


def test_verify_fails_when_a_prior_snapshot_is_deleted(history_db, before, capsys, monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    _execute(history_db, "DELETE FROM historical_snapshots WHERE id = 2")
    assert _verify(history_db, before) == 1
    err = capsys.readouterr().err
    assert err.startswith("::error title=Database history::")
    assert "snapshots fell from 3 to 2" in err and "earlier snapshots changed" in err


def test_verify_fails_when_growth_hides_a_deleted_snapshot(history_db, before, capsys):
    _execute(history_db, "DELETE FROM historical_snapshots WHERE id = 3")
    _store_run(history_db, [_record("Residential", 0.12, effective="2026-12-01"), _record("Small Business", 0.13)])
    assert _verify(history_db, before) == 1
    err = capsys.readouterr().err
    assert "earlier snapshots (id <= 3): 3 before, 2 now" in err
    assert "snapshots fell" not in err


def test_verify_fails_when_the_highest_snapshot_id_drops(history_db, before, capsys):
    _execute(history_db, "DELETE FROM historical_snapshots WHERE id = 3")
    assert _verify(history_db, before) == 1
    assert "highest snapshot id fell from 3 to 2" in capsys.readouterr().err


@pytest.mark.parametrize("column, value", [
    ("tariff_json", '{"edited": true}'), ("hash", "0" * 64), ("snapshot_date", "2000-01-01"),
    ("created_at", "2000-01-01 00:00:00"), ("tariff_id", 99), ("scrape_run_id", 99),
])
def test_verify_fails_when_any_column_of_a_prior_snapshot_changes(history_db, before, capsys, column, value):
    _execute(history_db, f"UPDATE historical_snapshots SET {column} = ? WHERE id = 1", value)
    assert _verify(history_db, before) == 1
    assert "earlier snapshots changed" in capsys.readouterr().err


@pytest.mark.parametrize("sql, message", [
    ("DELETE FROM tariffs WHERE name = 'General Service'", "tariff versions fell from 3 to 2"),
    ("DELETE FROM scrape_runs WHERE id = 1", "scrape runs fell from 2 to 1"),
])
def test_verify_fails_when_counts_drop(history_db, before, capsys, sql, message):
    _execute(history_db, sql)
    assert _verify(history_db, before) == 1
    assert message in capsys.readouterr().err


def test_verify_reports_but_does_not_gate_fewer_components(history_db, before, capsys):
    _execute(history_db, "DELETE FROM rate_components WHERE component_type = 'fixed'")
    assert _verify(history_db, before) == 0
    assert "rate components 3 (-3)" in capsys.readouterr().out


def test_verify_fails_when_the_database_is_no_longer_sqlite(history_db, before, capsys):
    history_db.write_bytes(b"This is not a database. " * 200)
    assert _verify(history_db, before) == 1
    assert "not a readable SQLite database" in capsys.readouterr().err


def test_verify_compares_only_the_recorded_snapshot_columns(history_db, before, capsys):
    _execute(history_db, "ALTER TABLE historical_snapshots ADD COLUMN reviewed TEXT DEFAULT 'no'")
    assert _verify(history_db, before) == 0
    _execute(history_db, "ALTER TABLE historical_snapshots RENAME COLUMN hash TO payload_hash")
    assert _verify(history_db, before) == 1
    assert "historical_snapshots no longer has column(s): hash" in capsys.readouterr().err


@pytest.mark.parametrize("content", ["not json", json.dumps([1, 2]), json.dumps({"counts": {}})])
def test_verify_rejects_unusable_earlier_statistics(history_db, tmp_path, capsys, content):
    bad = tmp_path / "bad.json"
    bad.write_text(content, encoding="utf-8")
    assert _verify(history_db, bad) == 1
    assert "earlier statistics" in capsys.readouterr().err


# -- pull_history_db (mocked GitHub) ------------------------------------------------------------------

OLD_DB = b"SQLite format 3\x00" + b"old local history " * 50
NEW_DB = b"SQLite format 3\x00" + b"new release history " * 60
DOWNLOAD_URL = pull.DOWNLOAD_PREFIX + "rates.db"


class FakeResponse:
    def __init__(self, status_code=200, payload=None, body=b""):
        self.status_code, self._payload, self._body = status_code, payload, body

    def json(self):
        return self._payload

    def iter_content(self, chunk_size):
        for start in range(0, len(self._body), 97):
            yield self._body[start:start + 97]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _release(body=NEW_DB, **asset):
    rates = {"name": "rates.db", "state": "uploaded", "size": len(body), "browser_download_url": DOWNLOAD_URL,
             "digest": "sha256:" + hashlib.sha256(body).hexdigest(), "updated_at": "2026-11-01T08:41:00Z"}
    rates.update(asset)
    backup = {"name": "rates-2026-11-01.db.gz", "state": "uploaded", "size": 10, "digest": "sha256:" + "1" * 64,
              "browser_download_url": pull.DOWNLOAD_PREFIX + "rates-2026-11-01.db.gz"}
    return {"tag_name": "data-history", "assets": [backup, rates]}


@pytest.fixture
def github(monkeypatch):
    state = {"api_status": 200, "release": _release(), "body": NEW_DB, "calls": []}

    def fake_get(url, **kwargs):
        state["calls"].append((url, kwargs))
        if url == pull.RELEASE_API:
            return FakeResponse(state["api_status"], state["release"])
        if url == DOWNLOAD_URL:
            return FakeResponse(200, body=state["body"])
        raise AssertionError(f"unexpected URL {url}")

    monkeypatch.setattr(pull.requests, "get", fake_get)
    return state


@pytest.fixture
def local_db(tmp_path):
    output = tmp_path / "db" / "rates.db"
    output.parent.mkdir()
    output.write_bytes(OLD_DB)
    return output


def _leftovers(directory):
    return sorted(path.name for path in directory.iterdir() if path.name.endswith(".part"))


def test_pull_uses_the_public_api_without_credentials(github, local_db):
    assert pull.main(["--output", str(local_db), "--dry-run"]) == 0
    api_url, api_kwargs = github["calls"][0]
    assert api_url == "https://api.github.com/repos/MaxPr1me/canada-utility-rates/releases/tags/data-history"
    assert github["calls"][1][0] == ("https://github.com/MaxPr1me/canada-utility-rates/releases/download/"
                                     "data-history/rates.db")
    assert not any("Authorization" in (kwargs.get("headers") or {}) for _, kwargs in github["calls"])


def test_pull_backs_up_the_local_copy_and_replaces_it_atomically(github, local_db, monkeypatch, capsys):
    replaced, real_replace = [], pull.os.replace

    def spy(src, dst):
        replaced.append((Path(src), Path(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(pull.os, "replace", spy)
    assert pull.main(["--output", str(local_db)]) == 0
    assert local_db.read_bytes() == NEW_DB
    backups = list((local_db.parent / "backups").iterdir())
    assert len(backups) == 1 and re.fullmatch(r"rates-\d{8}T\d{6}Z\.db", backups[0].name)
    assert backups[0].read_bytes() == OLD_DB
    assert len(replaced) == 1 and replaced[0][1] == local_db and replaced[0][0].parent == local_db.parent
    assert _leftovers(local_db.parent) == []
    assert "previous copy kept as" in capsys.readouterr().out


def test_pull_installs_without_backup_when_there_is_no_local_copy(github, tmp_path):
    output = tmp_path / "db" / "rates.db"
    assert pull.main(["--output", str(output)]) == 0
    assert output.read_bytes() == NEW_DB
    assert not (output.parent / "backups").exists()


def test_pull_leaves_a_matching_local_copy_alone(github, local_db, monkeypatch, capsys):
    local_db.write_bytes(NEW_DB)
    monkeypatch.setattr(pull.os, "replace", lambda *args: pytest.fail("nothing should be replaced"))
    assert pull.main(["--output", str(local_db)]) == 0
    assert "already matches" in capsys.readouterr().out
    assert not (local_db.parent / "backups").exists()
    assert _leftovers(local_db.parent) == []


def test_pull_dry_run_downloads_and_verifies_but_replaces_nothing(github, local_db, capsys):
    assert pull.main(["--output", str(local_db), "--dry-run"]) == 0
    assert local_db.read_bytes() == OLD_DB
    assert not (local_db.parent / "backups").exists()
    assert _leftovers(local_db.parent) == []
    assert capsys.readouterr().out.startswith("Dry run: downloaded and verified rates.db")


@pytest.mark.parametrize("asset, message", [
    ({"digest": "sha256:" + hashlib.sha256(b"something else").hexdigest()}, "SHA-256 mismatch"),
    ({"size": len(NEW_DB) + 1}, "but the release asset has"),
])
def test_pull_replaces_nothing_when_the_download_does_not_match(github, local_db, capsys, asset, message):
    github["release"] = _release(**asset)
    assert pull.main(["--output", str(local_db)]) == 1
    assert message in capsys.readouterr().err
    assert local_db.read_bytes() == OLD_DB
    assert not (local_db.parent / "backups").exists()
    assert _leftovers(local_db.parent) == []


@pytest.mark.parametrize("api_status, release, message", [
    (404, {"message": "Not Found"}, "not found"),
    (500, {"message": "Server Error"}, "HTTP 500"),
    (200, {"assets": []}, "has 0 assets named 'rates.db'"),
    (200, _release(digest=None), "no SHA-256 digest"),
    (200, _release(digest="md5:abc"), "no SHA-256 digest"),
    (200, _release(browser_download_url="https://example.com/rates.db"), "unexpected download URL"),
    (200, _release(state="starter"), "not a complete upload"),
])
def test_pull_fails_closed_on_release_problems(github, local_db, capsys, api_status, release, message):
    github["api_status"], github["release"] = api_status, release
    assert pull.main(["--output", str(local_db)]) == 1
    assert message in capsys.readouterr().err
    assert [url for url, _ in github["calls"]] == [pull.RELEASE_API]
    assert local_db.read_bytes() == OLD_DB


# -- workflows --------------------------------------------------------------------------------------

def _steps(path):
    """(name, text) per step; a step's text runs to the next step."""
    chunks = re.split(r"(?m)^      - name: ", path.read_text(encoding="utf-8"))[1:]
    return [(chunk.split("\n", 1)[0].strip(), chunk) for chunk in chunks]


def _step(steps, name):
    matches = [text for step_name, text in steps if step_name == name]
    assert len(matches) == 1, name
    return matches[0]


def _run(text):
    return text.split("\n        run:", 1)[1] if "\n        run:" in text else ""


def _index(steps, name):
    return [step_name for step_name, _ in steps].index(name)


def test_no_run_script_interpolates_expressions():
    for workflow in (SCRAPE_WORKFLOW, ARCHIVE_WORKFLOW):
        for name, text in _steps(workflow):
            assert "${{" not in _run(text), f"{workflow.name}: {name}"


def test_scrape_restore_never_silently_starts_a_new_database():
    steps = _steps(SCRAPE_WORKFLOW)
    text = SCRAPE_WORKFLOW.read_text(encoding="utf-8")
    restore = _run(_step(steps, "Restore database history"))
    assert 'gh api "repos/$GITHUB_REPOSITORY/releases/tags/data-history"' in restore
    assert "|| status=$?" in restore
    assert restore.count("history=new") == 1
    assert re.search(r'if grep -qF "\(HTTP 404\)" release_error\.txt; then\n(?:[^\n]*\n){0,3}'
                     r'\s*echo "history=new" >> "\$GITHUB_OUTPUT"\n\s*exit 0\n\s*fi\n\s*fail ', restore)
    assert "refusing to start an empty database" in restore
    assert ".digest" in restore and "sha256sum" in restore and '[ "$actual" != "$expected" ]' in restore
    assert '|| fail "The data-history release exists, but rates.db could not be downloaded."' in restore
    assert "check_db_history.py stats --db data/db/rates.db --out db_before.json" in restore
    assert restore.index("check_db_history.py stats") < restore.index('echo "history=existing"')
    assert "--init-db" not in restore
    assert "gh release view data-history >/dev/null 2>&1" not in text
    assert "[ ! -f data/db/rates.db ]" not in text
    init = _step(steps, "Initialize database (first run only)")
    assert "if: steps.restore.outputs.history == 'new'" in init
    assert [name for name, step in steps if "--init-db" in _run(step)] == ["Initialize database (first run only)"]


def test_scrape_verifies_history_before_uploading_with_a_dated_backup():
    steps = _steps(SCRAPE_WORKFLOW)
    order = ["Check manual inputs", "Checkout repository", "Set up Python", "Install dependencies",
             "Install Playwright browser", "Restore database history", "Initialize database (first run only)",
             "Run deterministic tests before scraping", "Run scrapers", "Validate data", "Export JSON for site",
             "Reject empty or corrupt exports", "Check database history before upload", "Save database history",
             "Generate diff report", "Commit updated data", "Prune old database backups",
             "Create issue on workflow errors"]
    assert [name for name, _ in steps] == order
    verify = _run(_step(steps, "Check database history before upload"))
    assert ("python scripts/check_db_history.py verify --db data/db/rates.db --before db_before.json 2>&1 "
            "| tee verify_output.txt") in verify
    assert "python scripts/check_db_history.py stats --db data/db/rates.db --out db_after.json" in verify
    assert re.search(r"\*\)\n[^\n]*\n\s*exit 1", verify)
    save = _step(steps, "Save database history")
    assert "\n        if:" not in save and "continue-on-error" not in save
    save_run = _run(save)
    assert 'backup="$RUNNER_TEMP/rates-$(date -u +%Y-%m-%d).db.gz"' in save_run
    assert 'gzip -c data/db/rates.db > "$backup"' in save_run
    assert save_run.index('gh release upload data-history "$backup" --clobber') < save_run.index(
        "gh release upload data-history data/db/rates.db --clobber")
    issue = _step(steps, "Create issue on workflow errors")
    assert "'verify_output.txt'" in issue and "## Database History" in issue
    assert "if: failure() && steps.inputs.outcome != 'failure'" in issue


def test_scrape_prunes_dated_backups_to_the_newest_twelve():
    prune = _run(_step(_steps(SCRAPE_WORKFLOW), "Prune old database backups"))
    pattern = r"^rates-[0-9]{4}-[0-9]{2}-[0-9]{2}\.db\.gz$"
    assert "gh release view data-history --json assets --jq '.assets[].name'" in prune
    assert f"grep -E '{pattern}'" in prune and "sort -r | tail -n +13" in prune
    assert 'gh release delete-asset data-history "$name" --yes' in prune
    assert re.fullmatch(pattern.strip("^$"), "rates-2026-11-01.db.gz")
    assert not re.fullmatch(pattern.strip("^$"), "rates.db")


def test_scrape_inputs_utility_or_province_pass_through_env():
    text = SCRAPE_WORKFLOW.read_text(encoding="utf-8")
    inputs = text.split("workflow_dispatch:", 1)[1].split("\nconcurrency:", 1)[0]
    assert "\n      utility:" in inputs and "\n      province:" in inputs
    steps = _steps(SCRAPE_WORKFLOW)
    for name in ("Check manual inputs", "Run scrapers"):
        step = _step(steps, name)
        assert "UTILITY: ${{ github.event.inputs.utility }}" in step
        assert "PROVINCE: ${{ github.event.inputs.province }}" in step
    check_inputs = _run(_step(steps, "Check manual inputs"))
    assert re.search(r'if \[ -n "\$UTILITY" \] && \[ -n "\$PROVINCE" \]; then\n[^\n]*\n\s*exit 1', check_inputs)
    scrape = _run(_step(steps, "Run scrapers"))
    assert 'python -m pipeline.run_scrape --utility "$UTILITY" 2>&1 | tee scrape_output.txt' in scrape
    assert 'python -m pipeline.run_scrape --province "$PROVINCE" 2>&1 | tee scrape_output.txt' in scrape


def test_archive_workflow_commits_the_archive_before_building_the_market_history():
    steps = _steps(ARCHIVE_WORKFLOW)
    order = ["Checkout repository", "Set up Python", "Install dependencies", "Update the Ontario Price archive",
             "Commit updated archive", "Build the Ontario market history", "Commit updated market history",
             "Create issue on failure"]
    assert [name for name, _ in steps] == order
    archive_commit = _run(_step(steps, "Commit updated archive"))
    assert re.findall(r"git add [^\n]+", archive_commit) == ["git add data/market/ontario_price_hourly.csv"]
    market = _step(steps, "Build the Ontario market history")
    assert "run: python scripts/build_ontario_market.py 2>&1 | tee market_output.txt" in market
    market_commit = _run(_step(steps, "Commit updated market history"))
    assert re.findall(r"git add [^\n]+", market_commit) == [
        "git add site/data/market_pricing_ontario.json data/market/ontario_market_monthly.csv"]
    assert 'git commit -m "data: Ontario market history update $(date +%Y-%m-%d)"' in market_commit
    assert market_commit.index("git diff --staged --quiet") < market_commit.index("git commit")
    assert market_commit.index("git pull --rebase origin main") < market_commit.index("git push")
    issue = _step(steps, "Create issue on failure")
    assert "'market_output.txt'" in issue and "'archive_output.txt'" in issue


def test_workflows_parse_as_yaml():
    yaml = pytest.importorskip("yaml")
    for workflow in (SCRAPE_WORKFLOW, ARCHIVE_WORKFLOW):
        data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        triggers = data.get("on", data.get(True))
        assert "workflow_dispatch" in triggers and "schedule" in triggers
        (job,) = data["jobs"].values()
        assert [step["name"] for step in job["steps"]] == [name for name, _ in _steps(workflow)]
        for step in job["steps"]:
            assert "${{" not in step.get("run", "")
    scrape = yaml.safe_load(SCRAPE_WORKFLOW.read_text(encoding="utf-8"))
    assert set(scrape.get("on", scrape.get(True))["workflow_dispatch"]["inputs"]) == {"utility", "province"}
    steps = {step["name"]: step for step in scrape["jobs"]["scrape"]["steps"]}
    assert steps["Restore database history"]["id"] == "restore"
    assert steps["Initialize database (first run only)"]["if"] == "steps.restore.outputs.history == 'new'"
    assert "if" not in steps["Save database history"]
    assert steps["Check database history before upload"]["env"]["HISTORY"] == "${{ steps.restore.outputs.history }}"
