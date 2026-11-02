"""Export hourly/monthly energy + Class B GA totals in CAD cents/kWh, without filling hourly gaps.

Reads the retained source files only; never downloads, changes tariffs, or writes the database.
April 2025's official hourly HOEP is included with an explicit monthly-reconciliation warning.
"""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path


def _load_market():
    name = "build_ontario_market"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


market = _load_market()
arc, gmp = market.arc, market.gmp
MarketDataError = market.MarketDataError
DEFAULT_DIR = market.PROJECT_ROOT / "data" / "market"
SUPPLEMENT_NAME = "PUB_PriceHOEPPredispOR_2025_v119.csv"
SUPPLEMENT_URL = gmp.HOEP_DIR + SUPPLEMENT_NAME
DEFAULT_SUPPLEMENT = DEFAULT_DIR / SUPPLEMENT_NAME
HOURLY_NAME = "ontario_total_hourly.csv"
HISTORICAL_NAME = "ontario_total_hourly_2020_2025.csv"
MONTHLY_NAME = "ontario_total_monthly.csv"
METADATA_NAME = "ontario_total_metadata.json"
HOURLY_FIELDS = ["date", "hour_ending", "market", "total_cents_per_kwh", "status",
                 "monthly_average_total_cents_per_kwh"]
MONTHLY_FIELDS = ["month", "total_cents_per_kwh", "status", "available_hourly_totals", "expected_hours"]
FIRST_DAY, HISTORICAL_END = date(2020, 1, 1), date(2025, 12, 31)
APRIL = "2025-04"
STATUS = {
    "observed": "Observed hourly energy plus the month's published Class B GA.",
    "observed_monthly_mismatch": "Observed hourly HOEP plus Class B GA; April 2025's hourly mean does not "
                                 "match the published monthly energy average. Not monthly-validated.",
    "observed_preliminary_lfda": "Observed DA-OZP plus a published non-final LFDA and monthly Class B GA; "
                                  "the LFDA may be revised.",
    "missing_hourly_energy": "No hourly energy observation is archived; total left blank.",
    "pending_lfda": "DA-OZP is archived, but LFDA is absent; total left blank.",
    "pending_class_b_ga": "Hourly energy is archived, but no validated monthly Class B GA is available.",
    "pending_lfda_and_class_b_ga": "Both LFDA and validated monthly Class B GA are absent; total left blank.",
}


def cents(value: Decimal | None) -> str:
    return "" if value is None else format(value / Decimal(10), ".3f")


def load_supplement(content: bytes, hoep: dict) -> dict:
    prices = gmp.parse_hoep_csv(gmp._text(content, SUPPLEMENT_NAME), 2025, SUPPLEMENT_NAME)
    expected = set(arc._days(date(2025, 1, 1), date(2025, 4, 30)))
    if set(prices) != expected:
        raise MarketDataError(f"{SUPPLEMENT_NAME}: expected every day from January 1 to April 30, 2025")
    april = {}
    for day, hours in prices.items():
        arc._check_hours(hours, f"{SUPPLEMENT_NAME} {day}")
        for hour, value in hours.items():
            price = market._cents(value, f"{SUPPLEMENT_NAME} {day} hour {hour}")
            key = day, hour
            if key in hoep and hoep[key] != price:
                raise MarketDataError(f"{SUPPLEMENT_NAME}: {day} hour {hour} disagrees with the HOEP archive")
            if day.month == 4:
                april[key] = price
    return april


def _csv(fields: list[str], rows: list[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def build(hoep: dict, monthly: dict, archive: dict, april: dict, first: date = FIRST_DAY) -> tuple[dict, dict]:
    if not monthly:
        raise MarketDataError("monthly history is empty")
    expected_months = market._span(first.strftime("%Y-%m"), max(monthly))
    if sorted(monthly) != expected_months or max(monthly) < "2025-12":
        raise MarketDataError("monthly history must be consecutive and include the whole 2020-2025 export period")
    energy = {**hoep, **april}
    for key, row in archive.items():
        if key[0] < arc.OEMP_START:
            raise MarketDataError(f"Ontario Price archive contains a pre-market day: {key[0]}")
        if row.oemp is not None:
            energy[key] = row.oemp

    by_month: dict[str, list[Decimal]] = defaultdict(list)
    for (day, _hour), value in energy.items():
        by_month[day.strftime("%Y-%m")].append(value)
    warnings = []
    for key, values in sorted(by_month.items()):
        if key not in monthly or len(values) != len(arc._month_days(key)) * 24:
            continue
        mean = sum(values, Decimal(0)) / len(values)
        difference = mean - monthly[key].energy_arithmetic
        if abs(difference) > market.HOEP_TOLERANCE:
            if key != APRIL:
                raise MarketDataError(f"{key}: hourly energy mean {mean} disagrees with monthly "
                                      f"{monthly[key].energy_arithmetic} $/MWh")
            warnings.append({"month": key, "hourly_mean_per_mwh": str(mean),
                             "published_monthly_per_mwh": str(monthly[key].energy_arithmetic),
                             "difference_per_mwh": str(difference),
                             "status": "observed_monthly_mismatch"})
    warning_months = {item["month"] for item in warnings}
    last = max(market._month_end(max(monthly)), max((day for day, _ in archive), default=HISTORICAL_END))
    hourly = []
    counts: Counter = Counter()
    for day in arc._days(first, last):
        month = day.strftime("%Y-%m")
        known_month = monthly.get(month)
        for hour in arc.HOURS:
            key = day, hour
            value, stored = energy.get(key), archive.get(key)
            total = None
            if value is None:
                status = ("pending_lfda" if known_month else "pending_lfda_and_class_b_ga") \
                    if stored else "missing_hourly_energy"
            elif known_month is None:
                status = "pending_class_b_ga"
            else:
                total = value + known_month.ga_class_b
                status = "observed_monthly_mismatch" if month in warning_months else "observed"
                if stored and stored.lfda_status != "Final":
                    status = "observed_preliminary_lfda"
                counts[month] += 1
            hourly.append({
                "date": day.isoformat(), "hour_ending": str(hour), "market": market._era(month),
                "total_cents_per_kwh": cents(total), "status": status,
                "monthly_average_total_cents_per_kwh": cents(known_month.total_arithmetic if known_month else None),
            })
    historical = [row for row in hourly if row["date"] <= HISTORICAL_END.isoformat()]
    monthly_rows = [
        {"month": key, "total_cents_per_kwh": cents(row.total_arithmetic),
         "status": "monthly_average_hourly_mismatch" if key in warning_months else "monthly_average",
         "available_hourly_totals": counts[key], "expected_hours": len(arc._month_days(key)) * 24}
        for key, row in sorted(monthly.items())
    ]
    metadata = {
        "schema_version": 1, "unit": "CAD cents/kWh",
        "formula": "(hourly HOEP or Ontario Price in $/MWh + that month's Class B GA in $/MWh) / 10",
        "hour_convention": "IESO hour-ending 1-24, Eastern Standard Time (UTC-05:00); no daylight-saving shift.",
        "hourly_start": first.isoformat(), "hourly_end": last.isoformat(),
        "monthly_end": max(monthly), "hourly_rows": len(hourly),
        "historical_2020_2025_rows": len(historical),
        "status_counts": dict(sorted(Counter(row["status"] for row in hourly).items())),
        "historical_status_counts": dict(sorted(Counter(row["status"] for row in historical).items())),
        "status_definitions": STATUS, "monthly_reconciliation_warnings": warnings,
        "notes": [
            "The total is market energy plus Class B GA, not a complete customer bill: excludes delivery, "
            "losses, regulatory/retail charges and taxes. Class A is not covered.",
            "Monthly-average reference values are separate from hourly totals and never fill missing hours.",
            "HOEP retired April 30, 2025; Ontario Price = DA-OZP + LFDA from May 1, 2025.",
            "April-June 2020 use the project's published capped Class B GA of 115 $/MWh.",
            "2021 GA excludes the separately billed Class B non-RPP recovery charge.",
            "April 2025's original hourly file is used only by these exports, with a warning; "
            "the validated site heatmap, representative models and tariffs are unchanged.",
            "Original component archives are retained for audit and future revisions.",
        ],
        "supplement_source_url": SUPPLEMENT_URL,
    }
    return {HOURLY_NAME: _csv(HOURLY_FIELDS, hourly), HISTORICAL_NAME: _csv(HOURLY_FIELDS, historical),
            MONTHLY_NAME: _csv(MONTHLY_FIELDS, monthly_rows)}, metadata


def check_no_loss(path: Path, content: bytes) -> None:
    if not path.exists():
        return
    key_fields = ["month"] if path.name == MONTHLY_NAME else ["date", "hour_ending"]
    before = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
    after = csv.DictReader(io.StringIO(content.decode("utf-8")))
    if before.fieldnames != after.fieldnames:
        raise MarketDataError(f"{path}: existing output has an unexpected header")
    fresh = {tuple(row[field] for field in key_fields): row for row in after}
    seen = set()
    for row in before:
        if None in row or any(value is None for value in row.values()):
            raise MarketDataError(f"{path}: existing output has a malformed row")
        key = tuple(row[field] for field in key_fields)
        if key in seen or key not in fresh:
            raise MarketDataError(f"{path}: duplicate or lost historical row {key}")
        if row["total_cents_per_kwh"] and not fresh[key]["total_cents_per_kwh"]:
            raise MarketDataError(f"{path}: refusing to erase the existing total for {key}")
        seen.add(key)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--hoep-csv", type=Path, default=market.DEFAULT_HOEP)
    parser.add_argument("--monthly-csv", type=Path, default=market.DEFAULT_MONTHLY)
    parser.add_argument("--archive", type=Path, default=market.DEFAULT_ARCHIVE)
    parser.add_argument("--hoep-2025-source", type=Path, default=DEFAULT_SUPPLEMENT)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        inputs = {path: path.read_bytes() for path in
                  (args.hoep_csv, args.monthly_csv, args.archive, args.hoep_2025_source)}
        hoep = market.load_hoep_csv(inputs[args.hoep_csv], str(args.hoep_csv), "2020-01")
        monthly = market.load_monthly(inputs[args.monthly_csv], str(args.monthly_csv))
        archive = arc.load_archive(inputs[args.archive], str(args.archive))
        april = load_supplement(inputs[args.hoep_2025_source], hoep)
        files, metadata = build(hoep, monthly, archive, april)
        metadata["inputs"] = [{"file": path.name,
                               "sha256": hashlib.sha256(content if path == args.hoep_2025_source
                                                        else content.replace(b"\r\n", b"\n")).hexdigest(),
                               "hash_basis": "original_bytes" if path == args.hoep_2025_source
                                             else "lf_normalized_bytes"}
                              for path, content in inputs.items()]
        files[METADATA_NAME] = (json.dumps(metadata, indent=2, ensure_ascii=True) + "\n").encode("utf-8")
        outputs = []
        for name, content in files.items():
            path = args.output_dir / name
            if name != METADATA_NAME:
                check_no_loss(path, content)
            if not path.exists() or path.read_bytes() != content:
                outputs.append((path, content))
        for warning in metadata["monthly_reconciliation_warnings"]:
            print(f"WARNING: {warning['month']} hourly mean {warning['hourly_mean_per_mwh']} vs published "
                  f"{warning['published_monthly_per_mwh']} $/MWh; rows explicitly flagged.", file=sys.stderr)
        print(f"{metadata['hourly_rows']:,} hourly rows; {metadata['historical_2020_2025_rows']:,} in 2020-2025; "
              f"{len(monthly)} monthly totals; statuses {metadata['status_counts']}")
        if args.dry_run:
            print("Dry run: nothing written.")
        elif outputs:
            market.write_outputs(outputs)
            print(f"Saved {len(outputs)} changed files in {args.output_dir}")
        else:
            print("Combined price files are unchanged.")
    except (MarketDataError, OSError) as exc:
        print(f"Ontario total export failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
