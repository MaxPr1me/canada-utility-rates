"""Rate History reviewed series: the selection rules the website applies, shared by the tests and monitoring.

``site/data/rate_history_series.json`` (owner decisions 55 and 56, 2026-11-23) picks the regulated and default
prices the Rate History tab charts by matching stored component names with full-match regexes;
``site/js/rate-history.js`` applies the same rules in the browser. A scraper that renames or drops a matched line
would leave that series line silently empty, so ``series_problems`` checks the list against the current export and
model monitoring reports any line no current live price carries.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

SELECTOR_KEYS = {"component_type", "tou_period", "name_regex"}


def _full(pattern: str, text: Any) -> bool:
    return re.fullmatch(pattern, text if isinstance(text, str) else "") is not None


def _component_matches(component: dict, selector: dict) -> bool:
    return all(_full(value, component.get("component_name")) if key == "name_regex" else component.get(key) == value
               for key, value in selector.items())


def record_selected(record: dict, match: dict) -> bool:
    """True when a record belongs to a series. Only live records do: estimates are never charted (decision 55)."""
    if record.get("provenance") != "live":
        return False
    if any(key in match and record.get(key) != match[key] for key in ("province", "utility_type", "utility_name")):
        return False
    components = record.get("components") or []
    if not all(any(_component_matches(c, sel) for c in components) for sel in match.get("requires", [])):
        return False
    return not any(any(_component_matches(c, sel) for c in components) for sel in match.get("excludes", []))


def line_components(record: dict, line: dict) -> list[dict]:
    """The record's components that carry a series line."""
    if "tariff_code_regex" in line and not _full(line["tariff_code_regex"], record.get("tariff_code")):
        return []
    return [c for c in record.get("components") or []
            if _full(line["name_regex"], c.get("component_name"))
            and ("component_type" not in line or c.get("component_type") == line["component_type"])
            and ("tou_period" not in line or c.get("tou_period") == line["tou_period"])]


def _check_list(document: Any) -> list[dict]:
    """The list's series, refusing a document the site could not read (a broken regex is a ValueError here)."""
    if (not isinstance(document, dict) or document.get("version") != 1
            or document.get("kind") != "rate_history_series" or not isinstance(document.get("series"), list)):
        raise ValueError("unsupported Rate History series list")
    for row in document["series"]:
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str) or not isinstance(row.get("match"), dict)
                or not isinstance(row.get("lines"), list) or not row["lines"]):
            raise ValueError(f"invalid Rate History series {row.get('id') if isinstance(row, dict) else row!r}")
        selectors = row["match"].get("requires", []) + row["match"].get("excludes", [])
        patterns = [sel["name_regex"] for sel in selectors if isinstance(sel, dict) and "name_regex" in sel]
        if any(not isinstance(sel, dict) or not sel or set(sel) - SELECTOR_KEYS for sel in selectors):
            raise ValueError(f"{row['id']}: invalid component selector")
        for line in row["lines"]:
            if not isinstance(line, dict) or not isinstance(line.get("id"), str) or "name_regex" not in line:
                raise ValueError(f"{row['id']}: invalid series line")
            patterns += [line[key] for key in ("name_regex", "tariff_code_regex") if key in line]
        for pattern in patterns:
            try:
                re.compile(pattern)
            except (re.error, TypeError) as exc:
                raise ValueError(f"{row['id']}: invalid regex {pattern!r} ({exc})") from None
    return document["series"]


def series_problems(document: Any, records: Iterable[dict]) -> list[str]:
    """Series and lines that no current live price carries, for example after a scraper renamed a component.

    Each tariff (province, utility, name) counts through its newest live version (effective date, then scrape run),
    so an older version still carrying an old name cannot hide a rename. An empty list means every series line is
    carried by at least one current live price.
    """
    series = _check_list(document)
    newest: dict[tuple, tuple[tuple, dict]] = {}
    for record in records:
        if not isinstance(record, dict) or record.get("provenance") != "live":
            continue
        key = (record.get("province"), record.get("utility_name"), record.get("name"))
        rank = (record.get("effective_date") or "", record.get("scrape_run_id") or 0)
        if key not in newest or rank > newest[key][0]:
            newest[key] = (rank, record)
    current = [record for _, record in newest.values()]
    problems = []
    for row in series:
        selected = [record for record in current if record_selected(record, row["match"])]
        if not selected:
            problems.append(f"Rate History series {row['id']}: no current live tariff matches it.")
            continue
        for line in row["lines"]:
            if not any(line_components(record, line) for record in selected):
                problems.append(f"Rate History series {row['id']}, line {line['id']}: no current live price matches "
                                f"{line['name_regex']!r} (renamed or removed?); update site/data/rate_history_series.json.")
    return problems
