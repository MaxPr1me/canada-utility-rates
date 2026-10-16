"""Check that the SQLite history database only grows before CI uploads it.

The Monthly Scrape workflow is the only writer of data/db/rates.db (asset rates.db of the data-history release). It
records statistics right after restoring the database and verifies them again before uploading:

    python scripts/check_db_history.py stats --db PATH --out FILE
    python scripts/check_db_history.py verify --db PATH --before FILE

``stats`` requires PRAGMA integrity_check "ok" and writes table counts, the highest historical_snapshots id, a SHA-256
digest over every snapshot row up to that id (all columns, in id order), the file size and the file SHA-256.
``verify`` requires integrity "ok", no fewer snapshots, tariff versions or scrape runs, a highest snapshot id no lower
than before and the same digest for the rows that existed before (earlier history unchanged). Rate component counts
are only reported: re-storing a tariff replaces its components. Any failure exits with status 1. On GitHub Actions
the result is one public ``::notice`` (or ``::error``) annotation. Standard library only; the database is opened
read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOTS = "historical_snapshots"
COUNTED_TABLES = ("tariffs", "rate_components", SNAPSHOTS, "scrape_runs", "utilities")
GATED_TABLES = {SNAPSHOTS: "snapshots", "tariffs": "tariff versions", "scrape_runs": "scrape runs"}
REPORT_ORDER = (("tariffs", "tariff versions"), (SNAPSHOTS, "snapshots"), ("scrape_runs", "scrape runs"),
                ("utilities", "utilities"), ("rate_components", "rate components"))
NOTICE_TITLE = "Database history"
FORMAT_VERSION = 1


class HistoryCheckError(Exception):
    """The database, or the statistics recorded before the run, fail a check."""


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _connect_readonly(db: Path) -> sqlite3.Connection:
    if not db.is_file():
        raise HistoryCheckError(f"database file not found: {db}")
    return sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)


def _check_integrity(conn: sqlite3.Connection, db: Path) -> None:
    try:
        result = [row[0] for row in conn.execute("PRAGMA integrity_check")]
    except sqlite3.DatabaseError as exc:
        raise HistoryCheckError(f"{db} is not a readable SQLite database: {exc}") from exc
    if result != ["ok"]:
        raise HistoryCheckError(f"PRAGMA integrity_check failed for {db}: " + "; ".join(map(str, result[:5])))


def _columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info({_quote(table)})")]


def _blob(value):
    if isinstance(value, bytes):
        return {"blob": value.hex()}
    raise TypeError(f"unexpected value type {type(value).__name__}")


def _snapshot_digest(conn: sqlite3.Connection, columns: list[str], max_id: int) -> tuple[str, int]:
    """SHA-256 over the given columns of every snapshot row with id <= max_id, in id order; also the row count."""
    present = set(_columns(conn, SNAPSHOTS))
    missing = [column for column in columns if column not in present]
    if missing:
        raise HistoryCheckError(f"{SNAPSHOTS} no longer has column(s): {', '.join(missing)}")
    digest = hashlib.sha256(json.dumps(columns).encode("ascii") + b"\n")
    rows = 0
    query = (f"SELECT {', '.join(map(_quote, columns))} FROM {SNAPSHOTS} WHERE id <= ? ORDER BY id")
    for row in conn.execute(query, (max_id,)):
        digest.update(json.dumps(list(row), separators=(",", ":"), default=_blob).encode("ascii") + b"\n")
        rows += 1
    return digest.hexdigest(), rows


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_stats(db: Path, columns: list[str] | None = None, digest_max_id: int | None = None) -> dict:
    """Integrity-checked statistics; the snapshot digest covers ids <= digest_max_id (default: the highest id)."""
    db = Path(db)
    with closing(_connect_readonly(db)) as conn:
        _check_integrity(conn, db)
        missing = [table for table in COUNTED_TABLES if not _columns(conn, table)]
        if missing:
            raise HistoryCheckError(f"{db} has no table(s): {', '.join(missing)}")
        counts = {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in COUNTED_TABLES}
        max_id = conn.execute(f"SELECT COALESCE(MAX(id), 0) FROM {SNAPSHOTS}").fetchone()[0]
        columns = list(columns) if columns is not None else _columns(conn, SNAPSHOTS)
        limit = max_id if digest_max_id is None else digest_max_id
        digest, digest_rows = _snapshot_digest(conn, columns, limit)
    return {
        "format_version": FORMAT_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "db": str(db),
        "integrity_check": "ok",
        "counts": counts,
        "max_snapshot_id": max_id,
        "snapshot_columns": columns,
        "digest_max_id": limit,
        "digest_rows": digest_rows,
        "snapshot_digest": digest,
        "file_size_bytes": db.stat().st_size,
        "file_sha256": _file_sha256(db),
    }


def load_before(path: Path) -> dict:
    try:
        before = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HistoryCheckError(f"cannot read the earlier statistics {path}: {exc}") from exc
    incomplete = HistoryCheckError(f"the earlier statistics {path} are incomplete or not from the stats command")
    if not isinstance(before, dict) or not isinstance(before.get("counts"), dict):
        raise incomplete
    counts, columns = before["counts"], before.get("snapshot_columns")
    numbers = [before.get(key) for key in ("max_snapshot_id", "digest_max_id", "digest_rows")]
    numbers += [counts.get(table) for table in COUNTED_TABLES]
    if (not all(isinstance(number, int) for number in numbers)
            or before["digest_max_id"] != before["max_snapshot_id"]
            or not isinstance(columns, list) or not columns or not all(isinstance(c, str) for c in columns)
            or not isinstance(before.get("snapshot_digest"), str)):
        raise incomplete
    return before


def verify(db: Path, before: dict) -> tuple[dict, list[str]]:
    """Current statistics (digest over the earlier id range) and the list of failed checks."""
    now = read_stats(db, before["snapshot_columns"], before["max_snapshot_id"])
    problems = []
    for table, label in GATED_TABLES.items():
        if now["counts"][table] < before["counts"][table]:
            problems.append(f"{label} fell from {before['counts'][table]} to {now['counts'][table]}")
    if now["max_snapshot_id"] < before["max_snapshot_id"]:
        problems.append(f"highest snapshot id fell from {before['max_snapshot_id']} to {now['max_snapshot_id']}")
    if now["digest_rows"] != before["digest_rows"]:
        problems.append(f"earlier snapshots (id <= {before['max_snapshot_id']}): {before['digest_rows']} before, "
                        f"{now['digest_rows']} now")
    if now["snapshot_digest"] != before["snapshot_digest"]:
        problems.append(f"earlier snapshots changed: the digest of rows with id <= {before['max_snapshot_id']} differs")
    return now, problems


def _escape(message: str) -> str:
    return message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def format_verified(before: dict, now: dict) -> str:
    """One line: counts with their growth, the file size and SHA-256."""
    parts = []
    for table, label in REPORT_ORDER:
        count, growth = now["counts"][table], now["counts"][table] - before["counts"][table]
        parts.append(f"{label} {count:,} ({growth:+,})")
    return (f"History verified, {before['digest_rows']:,} earlier snapshots unchanged: " + ", ".join(parts)
            + f"; size {now['file_size_bytes']:,} bytes; sha256 {now['file_sha256']}")


def format_notice(message: str, github: bool) -> str:
    return f"::notice title={NOTICE_TITLE}::{_escape(message)}" if github else f"{NOTICE_TITLE}: {message}"


def format_error(message: str, github: bool) -> str:
    return f"::error title={NOTICE_TITLE}::{_escape(message)}" if github else f"{NOTICE_TITLE} check FAILED: {message}"


def _on_github() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    stats_parser = commands.add_parser("stats", help="record integrity-checked statistics")
    stats_parser.add_argument("--db", type=Path, required=True)
    stats_parser.add_argument("--out", type=Path, required=True)
    verify_parser = commands.add_parser("verify", help="check that history only grew since the recorded statistics")
    verify_parser.add_argument("--db", type=Path, required=True)
    verify_parser.add_argument("--before", type=Path, required=True)
    args = parser.parse_args(argv)
    github = _on_github()

    try:
        if args.command == "stats":
            stats = read_stats(args.db)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
            counts = stats["counts"]
            print(f"Database statistics for {args.db}: integrity ok; tariff versions {counts['tariffs']:,}, "
                  f"snapshots {counts[SNAPSHOTS]:,} (highest id {stats['max_snapshot_id']}), "
                  f"scrape runs {counts['scrape_runs']:,}, utilities {counts['utilities']:,}, "
                  f"rate components {counts['rate_components']:,}; size {stats['file_size_bytes']:,} bytes; "
                  f"sha256 {stats['file_sha256']}; written to {args.out}", flush=True)
            return 0
        before = load_before(args.before)
        now, problems = verify(args.db, before)
    except HistoryCheckError as exc:
        print(format_error(str(exc), github), file=sys.stderr, flush=True)
        return 1
    if problems:
        print(format_error("; ".join(problems), github), file=sys.stderr, flush=True)
        return 1
    print(format_notice(format_verified(before, now), github), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
