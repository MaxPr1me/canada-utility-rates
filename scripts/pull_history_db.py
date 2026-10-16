"""Download the history database written by CI into a read-only local mirror.

The Monthly Scrape workflow is the only writer of the SQLite history database: it stores data/db/rates.db as asset
rates.db of the public GitHub release tagged data-history. This script finds that asset through the public GitHub
API (no sign-in), downloads it to a temporary file next to the output, checks its size and SHA-256 against the
digest GitHub publishes for the asset, copies an existing local database to backups/rates-<UTC timestamp>.db beside
it and then replaces the local file in one step (os.replace). A local file that already matches is left alone.
Nothing is ever uploaded: to store a scrape, push the code and run the Monthly Scrape workflow.

    python scripts/pull_history_db.py [--output PATH] [--dry-run]

``--dry-run`` downloads and verifies, then deletes the download and replaces nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "db" / "rates.db"
REPOSITORY = "MaxPr1me/canada-utility-rates"
RELEASE_TAG = "data-history"
ASSET_NAME = "rates.db"
RELEASE_API = f"https://api.github.com/repos/{REPOSITORY}/releases/tags/{RELEASE_TAG}"
DOWNLOAD_PREFIX = f"https://github.com/{REPOSITORY}/releases/download/{RELEASE_TAG}/"
API_HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
TIMEOUT = (15, 300)
CHUNK_SIZE = 1 << 20


class PullError(Exception):
    """The release asset could not be found, downloaded or verified."""


def resolve_asset() -> dict:
    """Download URL, expected size and SHA-256 of the rates.db release asset."""
    response = requests.get(RELEASE_API, headers=API_HEADERS, timeout=TIMEOUT)
    if response.status_code == 404:
        raise PullError(f"release {RELEASE_TAG!r} not found in {REPOSITORY} ({RELEASE_API})")
    if response.status_code != 200:
        raise PullError(f"GitHub API answered HTTP {response.status_code} for {RELEASE_API}")
    assets = [asset for asset in response.json().get("assets") or [] if asset.get("name") == ASSET_NAME]
    if len(assets) != 1:
        raise PullError(f"release {RELEASE_TAG!r} has {len(assets)} assets named {ASSET_NAME!r}, expected 1")
    asset = assets[0]
    match = re.fullmatch(r"sha256:([0-9a-fA-F]{64})", asset.get("digest") or "")
    if match is None:
        raise PullError(f"asset {ASSET_NAME!r} has no SHA-256 digest, so a download cannot be verified")
    url, size = asset.get("browser_download_url") or "", asset.get("size")
    if not url.startswith(DOWNLOAD_PREFIX):
        raise PullError(f"unexpected download URL for {ASSET_NAME!r}: {url!r}")
    if asset.get("state") != "uploaded" or not isinstance(size, int) or size <= 0:
        raise PullError(f"asset {ASSET_NAME!r} is not a complete upload (state {asset.get('state')!r}, size {size!r})")
    return {"url": url, "size": size, "sha256": match.group(1).lower(), "updated_at": asset.get("updated_at")}


def download(asset: dict, directory: Path) -> Path:
    """Stream the asset into a temporary file in ``directory``; removed again unless size and SHA-256 match."""
    handle, name = tempfile.mkstemp(prefix=".rates-", suffix=".part", dir=directory)
    temp = Path(name)
    digest, size = hashlib.sha256(), 0
    try:
        with os.fdopen(handle, "wb") as out, requests.get(asset["url"], stream=True, timeout=TIMEOUT) as response:
            if response.status_code != 200:
                raise PullError(f"download answered HTTP {response.status_code} for {asset['url']}")
            for chunk in response.iter_content(CHUNK_SIZE):
                out.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        if size != asset["size"]:
            raise PullError(f"downloaded {size:,} bytes, but the release asset has {asset['size']:,}")
        if digest.hexdigest() != asset["sha256"]:
            raise PullError(f"SHA-256 mismatch: downloaded {digest.hexdigest()}, release asset digest {asset['sha256']}")
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return temp


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def backup_path(output: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return output.parent / "backups" / f"{output.stem}-{stamp}{output.suffix}"


def pull(output: Path, dry_run: bool = False) -> str:
    """Download, verify and (unless dry_run) install the release asset at ``output``; returns a summary line."""
    asset = resolve_asset()
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = download(asset, output.parent)
    try:
        verified = f"{ASSET_NAME} ({asset['size']:,} bytes, sha256 {asset['sha256']}, uploaded {asset['updated_at']})"
        if dry_run:
            return f"Dry run: downloaded and verified {verified}; nothing replaced."
        if output.exists() and file_sha256(output) == asset["sha256"]:
            return f"{output} already matches {verified}; nothing replaced."
        backup = None
        if output.exists():
            backup = backup_path(output)
            if backup.exists():
                raise PullError(f"backup {backup} already exists; nothing replaced")
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(output, backup)
        os.replace(temp, output)
        kept = f"; previous copy kept as {backup}" if backup else ""
        return f"Installed {verified} at {output}{kept}."
    finally:
        temp.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help=f"default: {DEFAULT_OUTPUT}")
    parser.add_argument("--dry-run", action="store_true", help="download and verify only; replace nothing")
    args = parser.parse_args(argv)
    try:
        print(pull(args.output, args.dry_run), flush=True)
    except (PullError, requests.RequestException, OSError) as exc:
        print(f"Pull failed: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
