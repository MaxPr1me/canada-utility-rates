"""
validation.py — Validate scraped tariff data before storing it.

These checks catch common scraping errors:
  - Missing required fields
  - Unreasonable rate values (negative, absurdly high)
  - Inconsistent units
  - Missing components for a tariff
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from scrapers.base import TariffRecord, RateComponent

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a TariffRecord."""
    is_valid: bool
    warnings: list[str]
    errors: list[str]


# ─── Reasonable bounds for sanity checks ─────────────────────

# Electricity: most Canadian residential rates are $0.05–$0.25/kWh.
# Allow a wider range for commercial/industrial/riders.
ELECTRICITY_MIN = 0.0       # some components can be zero or negative (rebates)
ELECTRICITY_MAX = 5.0       # $/kWh — absurdly high, catches parsing errors

# Gas: most rates are $1–$15/GJ or $0.05–$1.50/m³.
GAS_MIN = 0.0
GAS_MAX_GJ = 50.0           # $/GJ
GAS_MAX_M3 = 10.0           # $/m³

# Fixed charges: $0–$200/month is a reasonable range.
FIXED_MAX = 500.0            # $/month


def validate_tariff(record: TariffRecord) -> ValidationResult:
    """
    Validate a single TariffRecord.

    Returns a ValidationResult with any warnings and errors.
    The record is considered invalid only if there are errors.
    Warnings flag things that look suspicious but might be correct.
    """
    warnings: list[str] = []
    errors: list[str] = []

    # ── Required fields ───────────────────────────────────────
    if not record.utility_name:
        errors.append("Missing utility_name")
    if not record.province:
        errors.append("Missing province")
    if not record.tariff_name:
        errors.append("Missing tariff_name")
    if record.utility_type not in ("electricity", "gas"):
        errors.append(f"Invalid utility_type: {record.utility_type!r}")
    if record.customer_class not in (
        "residential", "commercial", "industrial", "general_service", "other"
    ):
        warnings.append(f"Unusual customer_class: {record.customer_class!r}")

    # ── Must have at least one component ──────────────────────
    if not record.components:
        errors.append("Tariff has no rate components")

    # ── Validate each component ───────────────────────────────
    for i, comp in enumerate(record.components):
        prefix = f"Component[{i}] ({comp.component_name})"

        if not comp.component_type:
            errors.append(f"{prefix}: missing component_type")
        if not comp.component_name:
            errors.append(f"{prefix}: missing component_name")

        if comp.charge_value is not None:
            _validate_charge_value(comp, record.utility_type, prefix, warnings, errors)

    is_valid = len(errors) == 0

    if warnings:
        logger.warning("Validation warnings for %s / %s: %s",
                        record.utility_name, record.tariff_name, warnings)
    if errors:
        logger.error("Validation ERRORS for %s / %s: %s",
                      record.utility_name, record.tariff_name, errors)

    return ValidationResult(is_valid=is_valid, warnings=warnings, errors=errors)


def _validate_charge_value(
    comp: RateComponent,
    utility_type: str,
    prefix: str,
    warnings: list[str],
    errors: list[str],
) -> None:
    """Check that a charge value is within reasonable bounds."""
    value = comp.charge_value
    unit = (comp.charge_unit or "").lower()

    # Negative values are OK for rebates, but flag anything else
    if value < 0 and comp.component_type != "rebate":
        warnings.append(f"{prefix}: negative value {value} but type is {comp.component_type!r}")

    # Fixed charges
    if comp.component_type == "fixed":
        if value > FIXED_MAX:
            warnings.append(f"{prefix}: fixed charge ${value} seems very high")

    # Energy / volumetric charges
    elif "kwh" in unit:
        if value > ELECTRICITY_MAX:
            errors.append(f"{prefix}: ${value}/kWh is unreasonably high — possible parsing error")

    elif "gj" in unit:
        if value > GAS_MAX_GJ:
            warnings.append(f"{prefix}: ${value}/GJ seems very high")

    elif "m3" in unit or "m³" in unit:
        if value > GAS_MAX_M3:
            warnings.append(f"{prefix}: ${value}/m³ seems very high")


def validate_batch(records: list[TariffRecord]) -> tuple[list[TariffRecord], list[TariffRecord]]:
    """
    Validate a batch of records.

    Returns:
        (valid_records, invalid_records)
    """
    valid = []
    invalid = []
    for record in records:
        result = validate_tariff(record)
        if result.is_valid:
            valid.append(record)
        else:
            invalid.append(record)
    logger.info("Validation: %d valid, %d invalid out of %d total",
                len(valid), len(invalid), len(records))
    return valid, invalid
