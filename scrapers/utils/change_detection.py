"""
change_detection.py — Compare live-parsed tariff records against seed data.

When a scraper successfully parses live HTML, it should compare the
extracted values against its hardcoded seed data before returning.
This catches parsing errors (huge deviations probably mean broken CSS
selectors) and genuine rate changes (moderate deviations worth logging).

Usage in a scraper's _try_live_scrape():

    from scrapers.utils.change_detection import compare_to_seed, log_change_alerts

    live = self._parse_rates_from_html(soup)
    seed = self._seed_data()
    alerts = compare_to_seed(live, seed)
    log_change_alerts(alerts)

    # Reject if any critical deviations (likely a parsing bug)
    if any(a.severity == "critical" for a in alerts):
        return None
    return live
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from scrapers.base import TariffRecord

logger = logging.getLogger(__name__)


@dataclass
class ChangeAlert:
    """A single detected difference between live and seed data."""

    utility_name: str
    tariff_name: str
    component_name: str
    seed_value: Optional[float]
    live_value: Optional[float]
    pct_change: Optional[float]  # percentage, e.g. 12.5 means 12.5%
    severity: str                # "info", "warning", "critical"
    message: str


# ── Thresholds ─────────────────────────────────────────────────

INFO_THRESHOLD_PCT = 5.0       # < 5%  → info
WARNING_THRESHOLD_PCT = 30.0   # 5-30% → warning
# > 30% → critical

# Absolute floor: ignore tiny absolute differences even if % is large.
# e.g. seed=0.0001 live=0.0002 is 100% but only $0.0001 different.
ABS_FLOOR = 0.005  # $0.005


def _classify_severity(pct_change: float, abs_diff: float) -> str:
    """Classify the severity of a change based on % and absolute value."""
    if abs_diff < ABS_FLOOR:
        return "info"
    if abs(pct_change) < INFO_THRESHOLD_PCT:
        return "info"
    if abs(pct_change) < WARNING_THRESHOLD_PCT:
        return "warning"
    return "critical"


# ── Pairing logic ──────────────────────────────────────────────

def _match_key(record: TariffRecord) -> str:
    """
    Build a matching key for pairing live records to seed records.
    Uses tariff_code first (most specific), falls back to tariff_name.
    """
    code = record.tariff_code or ""
    name = record.tariff_name or ""
    cls = record.customer_class or ""
    return f"{code}|{name}|{cls}".lower()


def _pair_records(
    live_records: list[TariffRecord],
    seed_records: list[TariffRecord],
) -> list[tuple[Optional[TariffRecord], Optional[TariffRecord]]]:
    """
    Pair live and seed records by matching key.
    Returns list of (live, seed) tuples. Unmatched records appear
    with None on the missing side.
    """
    seed_by_key = {}
    for rec in seed_records:
        key = _match_key(rec)
        seed_by_key[key] = rec

    pairs = []
    seen_seed_keys = set()

    for live_rec in live_records:
        key = _match_key(live_rec)
        seed_rec = seed_by_key.get(key)
        if seed_rec:
            seen_seed_keys.add(key)
        pairs.append((live_rec, seed_rec))

    # Any seed records not matched to a live record
    for key, seed_rec in seed_by_key.items():
        if key not in seen_seed_keys:
            pairs.append((None, seed_rec))

    return pairs


# ── Component comparison ───────────────────────────────────────

def _compare_components(
    utility_name: str,
    tariff_name: str,
    live_record: TariffRecord,
    seed_record: TariffRecord,
) -> list[ChangeAlert]:
    """Compare individual rate components between a live and seed record."""
    alerts = []

    # Index seed components by (type, name) for matching
    seed_comps = {}
    for comp in seed_record.components:
        ckey = f"{comp.component_type or ''}|{comp.component_name or ''}".lower()
        seed_comps[ckey] = comp

    seen_seed = set()

    for live_comp in live_record.components:
        ckey = f"{live_comp.component_type or ''}|{live_comp.component_name or ''}".lower()
        seed_comp = seed_comps.get(ckey)

        if seed_comp is None:
            alerts.append(ChangeAlert(
                utility_name=utility_name,
                tariff_name=tariff_name,
                component_name=live_comp.component_name or "",
                seed_value=None,
                live_value=live_comp.charge_value,
                pct_change=None,
                severity="warning",
                message=f"New component in live data: {live_comp.component_name}",
            ))
            continue

        seen_seed.add(ckey)

        # Both have values — compare
        lv = live_comp.charge_value
        sv = seed_comp.charge_value

        if lv is None and sv is None:
            continue  # both null (e.g. market-based), no comparison possible
        if lv is None or sv is None:
            alerts.append(ChangeAlert(
                utility_name=utility_name,
                tariff_name=tariff_name,
                component_name=live_comp.component_name or "",
                seed_value=sv,
                live_value=lv,
                pct_change=None,
                severity="warning",
                message=f"Value presence mismatch: seed={sv}, live={lv}",
            ))
            continue

        abs_diff = abs(lv - sv)
        if sv != 0:
            pct = ((lv - sv) / abs(sv)) * 100.0
        elif lv != 0:
            pct = 100.0  # seed was 0, live is not
        else:
            continue  # both zero

        severity = _classify_severity(pct, abs_diff)

        if severity != "info" or abs_diff > 0:
            alerts.append(ChangeAlert(
                utility_name=utility_name,
                tariff_name=tariff_name,
                component_name=live_comp.component_name or "",
                seed_value=sv,
                live_value=lv,
                pct_change=round(pct, 2),
                severity=severity,
                message=f"{live_comp.component_name}: seed=${sv:.4f} → live=${lv:.4f} ({pct:+.1f}%)",
            ))

    # Check for missing components (in seed but not in live)
    for ckey, seed_comp in seed_comps.items():
        if ckey not in seen_seed:
            alerts.append(ChangeAlert(
                utility_name=utility_name,
                tariff_name=tariff_name,
                component_name=seed_comp.component_name or "",
                seed_value=seed_comp.charge_value,
                live_value=None,
                pct_change=None,
                severity="warning",
                message=f"Component missing from live data: {seed_comp.component_name}",
            ))

    return alerts


# ── Public API ─────────────────────────────────────────────────

def compare_to_seed(
    live_records: list[TariffRecord],
    seed_records: list[TariffRecord],
    tolerance_pct: float = 15.0,
) -> list[ChangeAlert]:
    """
    Compare live-parsed tariff records against seed/fallback data.

    Returns a list of ChangeAlert objects describing any differences.
    The tolerance_pct parameter is informational (used in log messages);
    actual severity classification uses the module-level thresholds.

    Args:
        live_records: Records extracted from live HTML parsing.
        seed_records: Hardcoded fallback records from _seed_data().
        tolerance_pct: Informational tolerance threshold (default 15%).

    Returns:
        List of ChangeAlert objects, possibly empty if data matches.
    """
    all_alerts: list[ChangeAlert] = []

    if not live_records or not seed_records:
        return all_alerts

    utility_name = live_records[0].utility_name if live_records else "Unknown"
    pairs = _pair_records(live_records, seed_records)

    for live_rec, seed_rec in pairs:
        if live_rec is None and seed_rec is not None:
            all_alerts.append(ChangeAlert(
                utility_name=utility_name,
                tariff_name=seed_rec.tariff_name,
                component_name="(tariff)",
                seed_value=None,
                live_value=None,
                pct_change=None,
                severity="warning",
                message=f"Tariff in seed but not in live data: {seed_rec.tariff_name}",
            ))
        elif live_rec is not None and seed_rec is None:
            all_alerts.append(ChangeAlert(
                utility_name=utility_name,
                tariff_name=live_rec.tariff_name,
                component_name="(tariff)",
                seed_value=None,
                live_value=None,
                pct_change=None,
                severity="info",
                message=f"New tariff in live data: {live_rec.tariff_name}",
            ))
        elif live_rec is not None and seed_rec is not None:
            alerts = _compare_components(
                utility_name=utility_name,
                tariff_name=live_rec.tariff_name,
                live_record=live_rec,
                seed_record=seed_rec,
            )
            all_alerts.extend(alerts)

    return all_alerts


def log_change_alerts(alerts: list[ChangeAlert]) -> None:
    """Log each ChangeAlert at the appropriate severity level."""
    for alert in alerts:
        prefix = f"[{alert.utility_name}] {alert.tariff_name}"
        if alert.severity == "critical":
            logger.error("CRITICAL %s: %s", prefix, alert.message)
        elif alert.severity == "warning":
            logger.warning("CHANGE %s: %s", prefix, alert.message)
        else:
            logger.info("CHANGE %s: %s", prefix, alert.message)


def has_critical_alerts(alerts: list[ChangeAlert]) -> bool:
    """Check if any alerts are critical (likely parsing errors)."""
    return any(a.severity == "critical" for a in alerts)
