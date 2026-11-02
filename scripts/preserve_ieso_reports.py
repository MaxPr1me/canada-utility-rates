"""Preserve unverified IESO DA-OZP/LFDA bytes independently of monthly price checks.

The index identifies immutable, content-addressed gzip objects by source URL and
SHA-256 of the original bytes. LFDA is fetched afresh every run; changed or empty
responses are additional objects, never replacements. Only versioned daily DA
reports are replayable. Raw capture is not evidence that a price is verified.

    python scripts/preserve_ieso_reports.py [--output-dir PATH] [--dry-run]

One writer is required. Each object and index update is atomic; preservation can
recover complete objects left before an interrupted index update. Replay is
read-only and rejects unreconciled objects, missing files and corrupt bytes.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import re
import sys
import zlib
from datetime import date, datetime, timezone
from pathlib import Path

import requests


def _load_archive():
    if "archive_ontario_price" in sys.modules:
        return sys.modules["archive_ontario_price"]
    path = Path(__file__).with_name("archive_ontario_price.py")
    spec = importlib.util.spec_from_file_location("archive_ontario_price", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


aop = _load_archive()
MarketDataError = aop.MarketDataError
DEFAULT_OUTPUT_DIR = aop.PROJECT_ROOT / "data" / "market" / "ieso_raw"
INDEX = "index.json"
OBJECT_RE = re.compile(r"(.+\.(?:xml|csv))\.([0-9a-f]{64})\.gz")


def _report_url(name: str) -> str:
    match = aop.DA_FILE_RE.fullmatch(name)
    if match and match.group(3) and int(match.group(3)) > 0:
        try:
            day = datetime.strptime(match.group(2), "%Y%m%d").date()
        except ValueError as exc:
            raise MarketDataError(f"raw report has invalid delivery date: {name}") from exc
        if day >= aop.OEMP_START:
            return aop.DA_DIR + name
    match = aop.LFDA_FILE_RE.fullmatch(name)
    if match and int(match.group(2)) >= aop.OEMP_START.year:
        return aop.LFDA_DIR + name
    raise MarketDataError(f"unsupported raw report name: {name}")


def _descriptor(filename: str, content: bytes) -> dict:
    match = OBJECT_RE.fullmatch(filename)
    if not match:
        raise MarketDataError(f"invalid raw object name: {filename}")
    digest = hashlib.sha256(content).hexdigest()
    if digest != match.group(2):
        raise MarketDataError(f"{filename}: SHA256 mismatch")
    return {"source_url": _report_url(match.group(1)), "sha256": digest, "size": len(content)}


def _read_object(path: Path, filename: str) -> tuple[bytes, dict]:
    try:
        content = gzip.decompress(path.read_bytes())
    except (OSError, EOFError, zlib.error) as exc:
        raise MarketDataError(f"{path}: missing or corrupt raw gzip: {exc}") from exc
    return content, _descriptor(filename, content)


def _atomic_write(path: Path, content: bytes) -> None:
    pending = path.with_name(path.name + ".pending")
    with pending.open("wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(pending, path)


class RawStore:
    """Integrity-checked raw bytes; no monthly-validation status is stored."""

    def __init__(self, path: Path, *, recover: bool = False, dry_run: bool = False):
        self.path = Path(path)
        self.dry_run = dry_run
        self.entries: dict[str, dict] = {}
        self.recovered: list[str] = []
        index = self.path / INDEX
        pending_index = self.path / (INDEX + ".pending")
        if not self.path.exists():
            if not recover:
                raise MarketDataError(f"raw directory does not exist: {self.path}")
        elif not self.path.is_dir():
            raise MarketDataError(f"raw directory is not a directory: {self.path}")
        elif index.is_file():
            self.entries = self._load_index(index)
        elif recover and pending_index.is_file():
            self.entries = self._load_index(pending_index)
            self.recovered.append(pending_index.name)
        elif not recover or any(self.path.iterdir()):
            raise MarketDataError(f"raw index missing: {index}")

        for filename, entry in self.entries.items():
            _, actual = _read_object(self.path / filename, filename)
            if actual != entry:
                raise MarketDataError(f"{filename}: raw index metadata/hash mismatch")

        for path in sorted(self.path.iterdir()) if self.path.exists() else []:
            if path.name == INDEX or path.name == INDEX + ".pending":
                continue
            pending = path.name.endswith(".gz.pending")
            filename = path.name.removesuffix(".pending") if pending else path.name
            if filename in self.entries and not pending:
                continue
            _, entry = _read_object(path, filename)
            if not recover:
                raise MarketDataError(f"{path}: unindexed/interrupted raw capture; run preservation to recover")
            if pending and not dry_run:
                target = self.path / filename
                if target.exists():
                    # The target was already hash-checked above; never replace it.
                    path.unlink()
                else:
                    os.replace(path, target)
            self.entries[filename] = entry
            self.recovered.append(path.name)
        if recover and not dry_run and (not index.exists() or self.recovered or pending_index.exists()):
            self._write_index()

    @staticmethod
    def _load_index(path: Path) -> dict[str, dict]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise MarketDataError(f"{path}: corrupt raw index: {exc}") from exc
        if (not isinstance(data, dict) or set(data) != {"schema", "verification", "reports"}
                or data["schema"] != 1 or data["verification"] != "raw_unverified"
                or not isinstance(data["reports"], dict)):
            raise MarketDataError(f"{path}: invalid raw index schema")
        for filename, entry in data["reports"].items():
            if not OBJECT_RE.fullmatch(filename) or "/" in filename or "\\" in filename:
                raise MarketDataError(f"{path}: invalid raw object name {filename!r}")
            if (not isinstance(entry, dict) or set(entry) != {"source_url", "sha256", "size"}
                    or not isinstance(entry["size"], int) or isinstance(entry["size"], bool)
                    or entry["size"] < 0):
                raise MarketDataError(f"{path}: invalid raw metadata for {filename}")
        return data["reports"]

    def _write_index(self) -> None:
        self.path.mkdir(parents=True, exist_ok=True)
        data = {"schema": 1, "verification": "raw_unverified", "reports": self.entries}
        _atomic_write(self.path / INDEX, (json.dumps(data, sort_keys=True, indent=2) + "\n").encode("utf-8"))

    def names(self) -> set[str]:
        return {filename.rsplit(".", 2)[0] for filename in self.entries}

    def capture(self, name: str, content: bytes) -> bool:
        """Persist bytes before parsing, including malformed responses. Return whether new."""
        _report_url(name)
        digest = hashlib.sha256(content).hexdigest()
        filename = f"{name}.{digest}.gz"
        if filename in self.entries:
            return False
        if not self.dry_run:
            self.path.mkdir(parents=True, exist_ok=True)
            _atomic_write(self.path / filename, gzip.compress(content, mtime=0))
        self.entries[filename] = _descriptor(filename, content)
        if not self.dry_run:
            self._write_index()
        return True

    def read_da(self, name: str) -> bytes:
        """Choose a parseable capture, but reject two differing valid immutable reports."""
        match = aop.DA_FILE_RE.fullmatch(name)
        if match is None:
            raise MarketDataError(f"not a daily DA report: {name}")
        day = datetime.strptime(match.group(2), "%Y%m%d").date()
        candidates, failures = [], []
        for filename in sorted(self.entries):
            if filename.rsplit(".", 2)[0] != name:
                continue
            content, _ = _read_object(self.path / filename, filename)
            try:
                aop.parse_da_report(content, day, name)
            except MarketDataError as exc:
                failures.append(str(exc))
            else:
                candidates.append(content)
        if len(candidates) > 1:
            raise MarketDataError(f"{name}: conflicting valid bytes for an immutable report")
        if not candidates:
            raise MarketDataError(f"{name}: no parseable raw capture: {'; '.join(failures)}")
        return candidates[0]


class RawReportSource(aop.ReportSource):
    """Read-only DA replay; LFDA, listings and monthly tables are always fetched live."""

    def __init__(self, raw_dir: Path, run_date: date, *, cache_dir: Path | None = None,
                 fetch=None, delay: float | None = None):
        super().__init__(cache_dir, run_date, fetch=fetch or aop.gmp.http_get, delay=delay)
        self.raw = RawStore(raw_dir)
        self.raw_names = self.raw.names()
        self.has_raw_da = any(aop.DA_FILE_RE.fullmatch(name) for name in self.raw_names)

    def _cache_path(self, url: str, immutable: bool) -> Path | None:
        # ReportSource normally reuses mutable pages for a day; a raw replay must
        # not hide a currently empty LFDA response or failed live monthly table.
        return super()._cache_path(url, immutable) if immutable else None

    def get(self, url: str, immutable: bool) -> bytes:
        if immutable and url.startswith(aop.DA_DIR):
            name = url[len(aop.DA_DIR):]
            if name in self.raw_names:
                return self.raw.read_da(name)
        return super().get(url, immutable)

    def archived(self, directory_url: str, pattern: re.Pattern) -> dict[str, tuple[int, str]]:
        found = super().archived(directory_url, pattern)
        if directory_url == aop.DA_DIR:
            for name in self.raw_names:
                match = pattern.fullmatch(name)
                if match and match.group(3):
                    found = aop.gmp._best_versions(found, {match.group(2): (int(match.group(3)), name)})
        return found


def preserve(source: aop.ReportSource, store: RawStore) -> tuple[int, list[str]]:
    """Continue independent downloads after expected fetch/parse/write failures."""
    added, failures = 0, []
    for directory, pattern in ((aop.DA_DIR, aop.DA_FILE_RE), (aop.LFDA_DIR, aop.LFDA_FILE_RE)):
        try:
            listed = aop.gmp.parse_listing(source.get(directory, immutable=False).decode("utf-8", "replace"),
                                           pattern)
            if not listed:
                raise MarketDataError(f"{directory}: no reports listed")
        except (MarketDataError, requests.RequestException, OSError) as exc:
            failures.append(f"{directory}: {exc}")
            continue
        for key, (version, name) in sorted(listed.items()):
            try:
                if directory == aop.DA_DIR:
                    if not version:
                        continue
                    day = datetime.strptime(key, "%Y%m%d").date()
                    if day < aop.OEMP_START:
                        continue
                    if name in store.names():
                        try:
                            store.read_da(name)
                        except MarketDataError:
                            # An earlier empty/malformed HTTP 200 must not poison
                            # the immutable cache forever. Keep it and retry live.
                            pass
                        else:
                            continue
                elif not aop.OEMP_START.year <= int(key) <= source.run_date.year:
                    continue
                content = source.get(directory + name, immutable=False)
                added += store.capture(name, content)
                if directory == aop.DA_DIR:
                    aop.parse_da_report(content, day, name)
                    if not store.dry_run:
                        store.read_da(name)
                else:
                    aop.parse_lfda_csv(aop.gmp._text(content, name), int(key), name)
            except (MarketDataError, requests.RequestException, OSError, ValueError) as exc:
                failures.append(f"{name}: {exc}")
    return added, failures


def main(argv: list[str] | None = None, *, fetch=None, run_date: date | None = None) -> int:
    parser = argparse.ArgumentParser(description="Preserve raw, unverified official IESO DA-OZP and LFDA reports.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="download and inspect, but change no raw files")
    args = parser.parse_args(argv)
    today = run_date or datetime.now(timezone.utc).date()
    source = aop.ReportSource(None, today, fetch=fetch or aop.gmp.http_get)
    try:
        store = RawStore(args.output_dir, recover=True, dry_run=args.dry_run)
        added, failures = preserve(source, store)
    except (MarketDataError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for name in store.recovered:
        print(f"{'Would recover' if args.dry_run else 'Recovered'} interrupted raw capture: {name}")
    print(f"{'Dry run: would preserve' if args.dry_run else 'Preserved'} {added} new raw objects; "
          f"{source.downloads} downloads; {len(failures)} failures. Raw reports are UNVERIFIED.")
    for failure in failures:
        print(f"ERROR: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
