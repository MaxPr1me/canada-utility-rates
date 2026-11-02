"""Raw preservation is independent of validation; all HTTP comes from saved IESO excerpts."""
import gzip
import hashlib
import json
from pathlib import Path

import pytest
import requests

from tests import test_ontario_price_archive as f
from scripts import preserve_ieso_reports as raw

aop = f.aop


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("unmocked HTTP in raw-report tests")

    monkeypatch.setattr(raw.requests, "get", blocked)
    monkeypatch.setattr(aop.gmp, "REQUEST_DELAY_SECONDS", 0)


def preserve(path, pages=None, *, log=None, dry_run=False):
    args = ["--output-dir", str(path)]
    if dry_run:
        args.append("--dry-run")
    return raw.main(args, fetch=f._fetch(f._web() if pages is None else pages, log), run_date=f.RUN_DATE)


def replay(path, output, pages=None, *, log=None, extra=()):
    return aop.main(["--raw-dir", str(path), "--output", str(output), "--no-site-api", *extra],
                    fetch=f._fetch(f._web() if pages is None else pages, log), run_date=f.RUN_DATE)


def snapshot(path):
    return {item.name: (item.read_bytes(), item.stat().st_mtime_ns)
            for item in path.iterdir()} if path.exists() else {}


def objects(path):
    return json.loads((path / raw.INDEX).read_text(encoding="utf-8"))["reports"]


def new_revision(pages):
    name = f.PREFIX + "20260924_v4.xml"
    pages[aop.DA_DIR] = f._listing([f.V1_1008, name])
    pages[aop.DA_DIR + name] = f.REPORTS[f.V3_0924].replace("<ZonalPrice>", "<ZonalPrice>", 1)
    return name


def test_preserves_exact_raw_bytes_highest_versions_and_deterministic_gzip(tmp_path, capsys):
    path, log = tmp_path / "raw", []
    assert preserve(path, log=log) == 0
    index = json.loads((path / raw.INDEX).read_text())
    assert index["verification"] == "raw_unverified"
    assert len(index["reports"]) == 5
    pages = f._web()
    for filename, metadata in index["reports"].items():
        compressed = (path / filename).read_bytes()
        content = gzip.decompress(compressed)
        assert content == pages[metadata["source_url"]].encode()
        assert hashlib.sha256(content).hexdigest() == metadata["sha256"]
        assert len(content) == metadata["size"]
        assert compressed[4:8] == b"\0\0\0\0"
    assert aop.DA_DIR + f.V1_0924 not in log
    assert aop.PRICES_URL not in log
    assert "UNVERIFIED" in capsys.readouterr().out


def test_idempotent_raw_files_but_mutable_lfda_is_downloaded_every_run(tmp_path):
    path, log = tmp_path / "raw", []
    assert preserve(path) == 0
    before = snapshot(path)
    assert preserve(path, log=log) == 0
    assert snapshot(path) == before
    assert not any(url.endswith(".xml") for url in log)
    assert len([url for url in log if url.endswith(".csv")]) == 2
    assert aop.DA_DIR in log and aop.LFDA_DIR in log


@pytest.mark.parametrize("empty_listing", [False, True])
def test_replays_reports_removed_from_online_listing_without_redownloading(tmp_path, empty_listing):
    path, output, log = tmp_path / "raw", tmp_path / "archive.csv", []
    assert preserve(path) == 0
    pages = f._web(listing=f._listing([] if empty_listing else [f.V1_1008]), reports={})
    before = snapshot(path)
    assert replay(path, output, pages, log=log) == 0
    rows = aop.load_archive(output.read_bytes(), "test")
    assert len(rows) == 72
    assert rows[(f.SEP24, 1)].version == 3
    assert not any(url.endswith(".xml") for url in log)
    assert aop.PRICES_URL in log and any(url.endswith(".csv") for url in log)
    assert snapshot(path) == before


def test_new_revisions_keep_old_bytes_and_highest_raw_revision_wins(tmp_path):
    path, output, log = tmp_path / "raw", tmp_path / "archive.csv", []
    assert preserve(path) == 0
    assert replay(path, output) == 0
    before = snapshot(path)
    pages = f._web()
    name = new_revision(pages)
    assert preserve(path, pages, log=log) == 0
    assert [url for url in log if url.endswith(".xml")] == [aop.DA_DIR + name]
    assert all(snapshot(path)[key] == value for key, value in before.items() if key != raw.INDEX)
    assert replay(path, output, f._web(listing=f._listing([f.V1_1008]), reports={})) == 0
    assert aop.load_archive(output.read_bytes(), "test")[(f.SEP24, 1)].version == 4
    assert len(objects(path)) == 6


@pytest.mark.parametrize("damage, message", [
    ("gzip", "missing or corrupt raw gzip"),
    ("hash", "SHA256 mismatch"),
    ("metadata", "metadata/hash mismatch"),
    ("missing_object", "missing or corrupt raw gzip"),
    ("index", "corrupt raw index"),
    ("missing_index", "raw index missing"),
])
def test_rejects_corruption_or_whole_file_loss_without_touching_archive(tmp_path, capsys, damage, message):
    path, output = tmp_path / "raw", tmp_path / "archive.csv"
    assert preserve(path) == 0
    output.write_bytes(b"existing archive must not change")
    filename = sorted(objects(path))[0]
    target = path / filename
    if damage == "gzip":
        target.write_bytes(b"not gzip")
    elif damage == "hash":
        target.write_bytes(gzip.compress(b"different bytes", mtime=0))
    elif damage == "metadata":
        index = json.loads((path / raw.INDEX).read_text())
        index["reports"][filename]["sha256"] = "0" * 64
        (path / raw.INDEX).write_text(json.dumps(index))
    elif damage == "missing_object":
        target.unlink()
    elif damage == "index":
        (path / raw.INDEX).write_bytes(b"{broken")
    else:
        (path / raw.INDEX).unlink()
    damaged = snapshot(path)
    log = []
    assert replay(path, output, log=log) == 1
    assert output.read_bytes() == b"existing archive must not change"
    assert snapshot(path) == damaged and not log
    assert message in capsys.readouterr().err
    assert preserve(path) == 1
    assert snapshot(path) == damaged


def test_absent_raw_directory_is_an_error_not_an_optional_hint(tmp_path, capsys):
    assert replay(tmp_path / "absent", tmp_path / "archive.csv") == 1
    assert "raw directory does not exist" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_partial_fetch_failures_preserve_other_reports_and_retry_missing_only(tmp_path, capsys):
    path, log = tmp_path / "raw", []
    pages = f._web()
    del pages[aop.DA_DIR + f.V3_0924]
    del pages[aop.LFDA_DIR + "PUB_HourlyLFDA_2025_v1.csv"]
    assert preserve(path, pages, log=log) == 1
    errors = capsys.readouterr().err
    assert f.V3_0924 in errors and "PUB_HourlyLFDA_2025_v1.csv" in errors
    assert len(objects(path)) == 3
    assert aop.DA_DIR + f.V1_1008 in log
    log.clear()
    assert preserve(path, log=log) == 0
    assert len(objects(path)) == 5
    assert [url for url in log if url.endswith(".xml")] == [aop.DA_DIR + f.V3_0924]


@pytest.mark.parametrize("failed_directory, count", [(aop.DA_DIR, 2), (aop.LFDA_DIR, 3)])
def test_independent_listing_failure_does_not_stop_other_report_family(tmp_path, failed_directory, count):
    pages = f._web()
    del pages[failed_directory]
    assert preserve(tmp_path / "raw", pages) == 1
    assert len(objects(tmp_path / "raw")) == count


def test_requests_errors_are_reported_and_do_not_stop_later_downloads(tmp_path, capsys):
    base = f._fetch(f._web())

    def fetch(url):
        if url == aop.DA_DIR + f.V3_0924:
            raise requests.Timeout("test timeout")
        return base(url)

    assert raw.main(["--output-dir", str(tmp_path / "raw")], fetch=fetch, run_date=f.RUN_DATE) == 1
    assert len(objects(tmp_path / "raw")) == 4
    assert "test timeout" in capsys.readouterr().err


def test_empty_lfda_is_captured_without_erasing_useful_bytes_and_validation_still_fails(tmp_path, capsys):
    path, output = tmp_path / "raw", tmp_path / "archive.csv"
    assert preserve(path) == 0
    assert replay(path, output) == 0
    before, previous = snapshot(path), output.read_bytes()
    pages = f._web(lfda_2026="")
    assert preserve(path, pages) == 1
    assert len(objects(path)) == 6
    assert all(snapshot(path)[key] == value for key, value in before.items() if key != raw.INDEX)
    assert any(gzip.decompress((path / key).read_bytes()) == b"" for key in objects(path))
    assert replay(path, output, pages) == 1
    assert output.read_bytes() == previous
    assert "the IESO published this file empty" in capsys.readouterr().err
    before = snapshot(path)
    assert preserve(path, pages) == 1
    assert snapshot(path) == before
    assert preserve(path) == 0
    assert snapshot(path) == before


def test_bad_da_capture_does_not_poison_immutable_cache_forever(tmp_path):
    path, output, log = tmp_path / "raw", tmp_path / "archive.csv", []
    pages = f._web()
    pages[aop.DA_DIR + f.V3_0924] = "<html>temporarily unavailable</html>"
    assert preserve(path, pages) == 1
    assert len(objects(path)) == 5
    assert replay(path, output) == 1
    assert not output.exists()
    assert preserve(path, log=log) == 0
    assert [url for url in log if url.endswith(".xml")] == [aop.DA_DIR + f.V3_0924]
    assert len(objects(path)) == 6
    assert replay(path, output, f._web(listing=f._listing([]), reports={})) == 0


def test_malformed_newer_revision_is_not_silently_replaced_by_older_valid_report(tmp_path):
    path, output = tmp_path / "raw", tmp_path / "archive.csv"
    assert preserve(path) == 0
    assert replay(path, output) == 0
    before = output.read_bytes()
    pages = f._web()
    name = new_revision(pages)
    pages[aop.DA_DIR + name] = "<bad>"
    assert preserve(path, pages) == 1
    assert replay(path, output, f._web(listing=f._listing([]), reports={})) == 1
    assert output.read_bytes() == before


def test_differing_valid_bytes_under_same_immutable_name_are_rejected(tmp_path, capsys):
    path, output = tmp_path / "raw", tmp_path / "archive.csv"
    assert preserve(path) == 0
    store = raw.RawStore(path)
    changed = f.REPORTS[f.V1_1008].replace("<ZonalPrice>31.39</ZonalPrice>", "<ZonalPrice>31.40</ZonalPrice>")
    assert store.capture(f.V1_1008, changed.encode())
    assert replay(path, output) == 1
    assert "conflicting valid bytes" in capsys.readouterr().err
    assert not output.exists()


def test_monthly_price_mismatch_never_discards_raw_reports_or_changes_validated_archive(tmp_path, capsys):
    path, output = tmp_path / "raw", tmp_path / "archive.csv"
    pages = f._month_web(f.AUGUST, mutate=(f.AUGUST[16], 18, "20.00"), table_values=f.AUGUST_TABLE)
    assert preserve(path, pages) == 0
    assert len(objects(path)) == 33
    before = snapshot(path)
    assert replay(path, output, pages) == 1
    assert not output.exists()
    assert "monthly check" in capsys.readouterr().err
    assert snapshot(path) == before


@pytest.mark.parametrize("url", [aop.PRICES_URL, aop.LFDA_DIR + "PUB_HourlyLFDA_2026_v1.csv"])
def test_raw_mode_never_uses_stale_mutable_same_day_cache(tmp_path, capsys, url):
    path, output, cache = tmp_path / "raw", tmp_path / "archive.csv", tmp_path / "cache"
    assert preserve(path) == 0
    args = ["--output", str(output), "--no-site-api", "--cache-dir", str(cache)]
    assert aop.main(args, fetch=f._fetch(f._web()), run_date=f.RUN_DATE) == 0
    before = output.read_bytes()
    pages, log = f._web(), []
    del pages[url]
    assert replay(path, output, pages, log=log, extra=("--cache-dir", str(cache))) == 1
    assert url in log and "could not download" in capsys.readouterr().err
    assert output.read_bytes() == before


@pytest.mark.parametrize("existing", [False, True])
def test_dry_run_changes_no_raw_files_or_directories(tmp_path, existing):
    path = tmp_path / "raw"
    if existing:
        assert preserve(path) == 0
    before = snapshot(path)
    pages = f._web(lfda_2026=f.LFDA_OCT15)
    new_revision(pages)
    assert preserve(path, pages, dry_run=True) == 0
    assert snapshot(path) == before
    assert path.exists() == existing


@pytest.mark.parametrize("pending", [False, True])
def test_interrupted_object_before_index_update_is_resumable_and_replay_is_read_only(tmp_path, pending):
    path, output = tmp_path / "raw", tmp_path / "archive.csv"
    assert preserve(path) == 0
    pages = f._web()
    name = new_revision(pages)
    content = pages[aop.DA_DIR + name].encode()
    filename = f"{name}.{hashlib.sha256(content).hexdigest()}.gz"
    target = path / (filename + ".pending" if pending else filename)
    target.write_bytes(gzip.compress(content, mtime=0))
    before = snapshot(path)
    assert replay(path, output) == 1
    assert snapshot(path) == before
    assert preserve(path, pages, dry_run=True) == 0
    assert snapshot(path) == before
    assert preserve(path, pages) == 0
    assert filename in objects(path) and (path / filename).exists()
    assert not (path / (filename + ".pending")).exists()
    assert replay(path, output, f._web(listing=f._listing([]), reports={})) == 0


def test_interrupted_initial_index_is_resumable(tmp_path):
    path = tmp_path / "raw"
    path.mkdir()
    (path / (raw.INDEX + ".pending")).write_text(json.dumps({
        "schema": 1, "verification": "raw_unverified", "reports": {},
    }))
    assert preserve(path) == 0
    assert len(objects(path)) == 5
    assert not (path / (raw.INDEX + ".pending")).exists()


def test_partial_index_update_does_not_lose_completed_object(tmp_path, monkeypatch):
    path = tmp_path / "raw"
    store = raw.RawStore(path, recover=True)
    original = raw._atomic_write

    def fail_index(target: Path, content: bytes):
        if target.name == raw.INDEX:
            raise OSError("simulated index write failure")
        original(target, content)

    with monkeypatch.context() as patch:
        patch.setattr(raw, "_atomic_write", fail_index)
        with pytest.raises(OSError, match="simulated"):
            store.capture(f.V1_1008, f.BASE_XML.encode())
    assert len(list(path.glob("*.gz"))) == 1
    assert objects(path) == {}
    recovered = raw.RawStore(path, recover=True)
    assert recovered.read_da(f.V1_1008) == f.BASE_XML.encode()
    assert len(objects(path)) == 1


def test_partial_gzip_write_is_explicit_corruption_not_silent_loss(tmp_path, capsys):
    path = tmp_path / "raw"
    assert preserve(path) == 0
    filename = f"{f.PREFIX}20260924_v4.xml.{'0' * 64}.gz.pending"
    (path / filename).write_bytes(b"partial")
    before = snapshot(path)
    assert preserve(path) == 1
    assert "missing or corrupt raw gzip" in capsys.readouterr().err
    assert snapshot(path) == before
