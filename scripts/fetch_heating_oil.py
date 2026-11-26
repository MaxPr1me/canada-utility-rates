"""Refresh the heating-oil prices used by the spark gap comparison (owner decisions 149-152 and 162, 2026-11-26).

Source: Statistics Canada Table 18-10-0001-01, "Monthly average retail prices for gasoline and fuel oil, by
geography", product "Household heating fuel", in cents per litre, read through Statistics Canada's official Web Data
Service (getDataFromVectorsAndLatestNPeriods). One city series per region whose homes compare with heating oil
(decision 146); Nunavut has no series (decision 148).

Output: data/fuel/heating_oil_prices.json, every month kept. A month already stored whose value changes (or
disappears) stops the refresh for review and nothing is written, as the market histories do. A month Statistics Canada
marks unavailable ("..", "x", "F") is stored without a price, never as one. The file is rewritten only when a month or
its status changes. Run by the Monthly Scrape before the export; a failed download keeps the last file and model
monitoring warns when the newest month is more than three months old.

    python scripts/fetch_heating_oil.py --dry-run     # report what would change, write nothing
    python scripts/fetch_heating_oil.py               # write data/fuel/heating_oil_prices.json
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import requests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "fuel" / "heating_oil_prices.json"
WDS_URL = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromVectorsAndLatestNPeriods"
TABLE_URL = "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000101"
PRODUCT_ID = 18100001
# Region: (vector, city as Statistics Canada publishes it). Checked against the table's CSV on 2026-11-26.
SERIES = {
    "NB": (735159, "Saint John, New Brunswick"),
    "NS": (735158, "Halifax, Nova Scotia"),
    "PE": (735157, "Charlottetown and Summerside, Prince Edward Island"),
    "NL": (735149, "St. John's, Newfoundland and Labrador"),
    "YT": (735155, "Whitehorse, Yukon"),
    "NT": (735156, "Yellowknife, Northwest Territories"),
}
# Statistics Canada status codes (WDS getCodeSets, 2026-11-26): these mean no usable value.
UNUSABLE_STATUS = {1: "..", 2: "0s", 8: "F", 9: "...", 10: "<LOD"}
QUALITY_STATUS = {3: "A", 4: "B", 5: "C", 6: "D", 7: "E"}  # E: use with caution (kept, labelled)
SYMBOLS = {1: "p", 3: "r"}
FIRST_MONTHS = 24
UPDATE_MONTHS = 6
USER_AGENT = "canada-utility-rates heating-oil refresh (https://github.com/MaxPr1me/canada-utility-rates)"

logger = logging.getLogger("fetch_heating_oil")


class RevisionError(ValueError):
    """A stored month changed value: stop for review instead of overwriting history."""


def download(latest_n: int, post: Optional[Callable[..., Any]] = None, attempts: int = 3) -> list:
    """The service's answer for every series (raises on HTTP or network errors after ``attempts`` tries)."""
    post = post or requests.post
    body = [{"vectorId": vector, "latestN": latest_n} for vector, _ in SERIES.values()]
    for attempt in range(1, attempts + 1):
        try:
            response = post(WDS_URL, json=body, headers={"User-Agent": USER_AGENT}, timeout=60)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == attempts:
                raise
            logger.warning("Statistics Canada request failed (%s); retrying", exc)
            time.sleep(5 * attempt)
    raise RuntimeError("unreachable")


def parse(answer: Any) -> dict[str, dict[str, dict]]:
    """{region: {YYYY-MM: entry}} from the service's answer; raises ValueError when it is not what was asked for."""
    if not isinstance(answer, list) or len(answer) != len(SERIES):
        raise ValueError("unexpected answer from Statistics Canada's data service")
    regions = {vector: region for region, (vector, _) in SERIES.items()}
    out: dict[str, dict[str, dict]] = {}
    for item in answer:
        data = item.get("object") if isinstance(item, dict) else None
        if not isinstance(data, dict) or item.get("status") != "SUCCESS":
            raise ValueError(f"Statistics Canada did not return a series: {item!r:.200}")
        region = regions.get(data.get("vectorId"))
        if region is None or data.get("productId") != PRODUCT_ID:
            raise ValueError(f"unexpected series v{data.get('vectorId')} of table {data.get('productId')}")
        months = {}
        for point in data.get("vectorDataPoint") or []:
            match = re.fullmatch(r"(\d{4}-\d{2})-01", str(point.get("refPer")))
            if match is None or point.get("scalarFactorCode") not in (0, None):
                raise ValueError(f"unexpected reference period or scale in v{data['vectorId']}: {point!r:.200}")
            status = point.get("statusCode") or 0
            value = point.get("value")
            usable = (status not in UNUSABLE_STATUS and (point.get("securityLevelCode") or 0) == 0
                      and isinstance(value, (int, float)) and math.isfinite(value) and value > 0)
            months[match.group(1)] = {
                "value": float(value) if usable else None,
                "status": QUALITY_STATUS.get(status) if usable else (UNUSABLE_STATUS.get(status) or "x"),
                "symbol": SYMBOLS.get(point.get("symbolCode") or 0),
                "release_time": point.get("releaseTime"),
            }
        out[region] = months
    if set(out) != set(SERIES):
        raise ValueError("Statistics Canada's answer is missing a series")
    return out


def empty_document() -> dict:
    return {
        "version": 1,
        "kind": "heating_oil_prices",
        "source": {
            "table": "18-10-0001-01",
            "title": "Monthly average retail prices for gasoline and fuel oil, by geography",
            "product": "Household heating fuel",
            "unit": "cents per litre",
            "url": TABLE_URL,
            "service": WDS_URL,
            "basis": "Consumer Price Index average retail prices, treated as prices paid including sales tax (owner "
                     "decision 165, 2026-11-26).",
        },
        "updated_at": None,
        "series": {region: {"vector": f"v{vector}", "geo": geo, "months": {}} for region, (vector, geo) in
                   SERIES.items()},
    }


def merge(document: dict, fresh: dict[str, dict[str, dict]]) -> tuple[dict, list[str]]:
    """(merged document, list of changes). Raises RevisionError when a stored month's value changes or disappears."""
    merged = json.loads(json.dumps(document))
    changes, revisions = [], []
    for region, months in sorted(fresh.items()):
        series = merged["series"].setdefault(region, {"vector": f"v{SERIES[region][0]}", "geo": SERIES[region][1],
                                                      "months": {}})
        stored = series["months"]
        for month, entry in sorted(months.items()):
            old = stored.get(month)
            if old is not None and old.get("value") is not None and (
                    entry["value"] is None or not math.isclose(old["value"], entry["value"], abs_tol=1e-9)):
                revisions.append(f"{region} {month}: {old['value']} -> {entry['value']} ({entry['status'] or 'normal'})")
                continue
            if old != entry:
                changes.append(f"{region} {month}: {'new' if old is None else 'status'} {entry['value']} "
                               f"{entry['status'] or ''}".rstrip())
                stored[month] = entry
        series["months"] = dict(sorted(stored.items()))
    if revisions:
        raise RevisionError("Statistics Canada changed stored heating-oil prices; review before refreshing: "
                            + "; ".join(revisions))
    return merged, changes


def write(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def refresh(path: Path, *, dry_run: bool, months: Optional[int] = None,
            post: Optional[Callable[..., Any]] = None) -> list[str]:
    """Download, merge and (unless ``dry_run``) write; returns the changes. Nothing is written on any failure."""
    document = json.loads(path.read_text(encoding="utf-8")) if path.exists() else empty_document()
    if document.get("version") != 1 or document.get("kind") != "heating_oil_prices":
        raise ValueError(f"{path} is not a version 1 heating_oil_prices file")
    fresh = parse(download(months or (UPDATE_MONTHS if path.exists() else FIRST_MONTHS), post=post))
    merged, changes = merge(document, fresh)
    if changes and not dry_run:
        merged["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        write(path, merged)
    return changes


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="report what would change and write nothing")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--months", type=int, default=None,
                        help=f"latest months to request (default {FIRST_MONTHS} for a new file, else {UPDATE_MONTHS})")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    try:
        changes = refresh(args.output, dry_run=args.dry_run, months=args.months)
    except Exception as exc:
        print(f"Heating-oil refresh FAILED ({type(exc).__name__}: {exc}); {args.output} left unchanged.",
              file=sys.stderr)
        return 1
    verb = "would change" if args.dry_run else "changed"
    print(f"Heating-oil prices: {len(changes)} month(s) {verb}." if changes else "Heating-oil prices: no change.")
    for change in changes:
        print(f"  {change}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
