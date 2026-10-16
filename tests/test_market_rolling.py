"""Rolling Ontario market history (scripts/build_ontario_market.py) and scrapers/utils/market_pricing.py.

Synthetic months are built from saved official IESO excerpts (tests/fixtures/ieso_market_rolling.json); nothing is
downloaded. The builder's internal window_months/first_month parameters keep the worlds small (12 months from 2024).
"""
import copy
import functools
import importlib.util
import io
import json
import re
import sys
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import openpyxl
import pytest

from scrapers.utils import market_pricing

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ieso_market_rolling.json"
SCRIPT = ROOT / "scripts" / "build_ontario_market.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("build_ontario_market", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bom = _load_script()
gmp, arc = bom.gmp, bom.arc
DATA = json.loads(FIXTURE.read_text(encoding="utf-8"))
AS_OF = date(2025, 10, 16)
FIRST, SIZE = "2024-01", 12
GENERATED = datetime(2025, 10, 16, 12, 0, tzinfo=timezone.utc)
CENT = Decimal("0.01")
ARCHIVE_START, ARCHIVE_END = date(2025, 5, 2), date(2025, 9, 30)
BLANK_LFDA = {(date(2025, 6, 10), hour) for hour in (1, 2, 3)}
GA_PREFIX = "PUB_GlobalAdjustment_"
HOEP_NAMES = {2024: "PUB_PriceHOEPPredispOR_2024_v395.csv", 2025: "PUB_PriceHOEPPredispOR_2025_v119.csv"}
AVERAGE_NAMES = {2024: "PUB_PriceHOEPAverage_2024_v13.xml", 2025: "PUB_PriceHOEPAverage_2025_v4.xml"}


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise RuntimeError("live network disabled in deterministic tests")

    monkeypatch.setattr(gmp.requests, "get", blocked)
    monkeypatch.setattr(gmp, "REQUEST_DELAY_SECONDS", 0)


# -- independent builders of the synthetic world (not the code under test) ---------------------------

def _q(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _days(first, last):
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _month_days(key):
    year, month = int(key[:4]), int(key[5:])
    return _days(date(year, month, 1), date(year, month, monthrange(year, month)[1]))


def _weekend(day):
    return day.weekday() >= 5


HOEP_BASE = {int(line.split(",")[1]): Decimal(line.split(",")[2])
             for line in DATA["hoep_hourly"]["csv_excerpt"].splitlines()[4:]}
ARCHIVE_LINES = DATA["archive"]["csv_excerpt"].splitlines()
DA_BASE = {int(line.split(",")[1]): Decimal(line.split(",")[2]) for line in ARCHIVE_LINES[1:]}
LFDA_BASE = {int(line.split(",")[1]): Decimal(line.split(",")[3]) for line in ARCHIVE_LINES[1:]}


def _hoep(day, hour):
    """The real 2025-01-15 profile, shifted by month, day type and year so that months and bins differ."""
    return HOEP_BASE[hour] + day.month + (3 if _weekend(day) else 0) + Decimal("0.5") * (day.year - 2024)


def _hoep_mean(key):
    values = [_hoep(day, hour) for day in _month_days(key) for hour in range(1, 25)]
    return sum(values) / len(values)


def _hoep_csv(year):
    lines = DATA["hoep_hourly"]["csv_excerpt"].splitlines()[:4]
    lines[2] = lines[2].replace("2025", str(year))
    last = date(2025, 4, 30) if year == 2025 else date(year, 12, 31)
    for day in _days(date(year, 1, 1), last):
        lines += [",".join([day.isoformat(), str(hour), f"{_hoep(day, hour):.2f}"] + ["0.00"] * 6)
                  for hour in range(1, 25)]
    return ("\n".join(lines) + "\n").encode("utf-8")


def _averages_xml(year, months, override=None):
    xml = DATA["hoep_averages"]["xml"]
    block = re.search(r"<HOEP>.*?</HOEP>\n", xml, flags=re.S).group(0)
    body = ""
    for month in months:
        key = f"{year}-{month:02d}"
        arithmetic = (override or {}).get(key, str(_q(_hoep_mean(key))))
        text = block.replace("<Month>January</Month>", f"<Month>{gmp.MONTH_NAMES[month - 1]}</Month>")
        text = re.sub(r"<ArithmeticAve>[^<]*<", f"<ArithmeticAve>{arithmetic}<", text)
        body += re.sub(r"<WeightedAve>[^<]*<", f"<WeightedAve>{_q(_hoep_mean(key) + 1)}<", text)
    start, end = xml.index("<HOEP>"), xml.rindex("</HOEP>\n") + len("</HOEP>\n")
    xml = (xml[:start] + body + xml[end:]).replace("<ReportYear>2025</ReportYear>", f"<ReportYear>{year}</ReportYear>")
    return xml.encode("utf-8")


def _listing(names):
    lines = ['<img src="/icons/text.gif" alt="[TXT]"> <a href="' + name + '">' + name + "</a>" for name in names]
    return ("<html><body><pre>\n" + "\n".join(lines) + "\n</pre></body></html>").encode("utf-8")


def _da(day, hour):
    return DA_BASE[hour] + day.month - 8 + (2 if _weekend(day) else 0)


def _archive_rows():
    rows = {}
    for day in _days(ARCHIVE_START, ARCHIVE_END):
        for hour in range(1, 25):
            rows[(day, hour)] = (_da(day, hour), None if (day, hour) in BLANK_LFDA else LFDA_BASE[hour])
    return rows


ARCHIVE = _archive_rows()


def _archive_csv(rows=None):
    lines = [ARCHIVE_LINES[0]]
    for (day, hour), (da, lfda) in sorted((rows or ARCHIVE).items()):
        oemp = "" if lfda is None else arc._money(da + lfda)
        lines.append(f"{day.isoformat()},{hour},{arc._money(da)},{arc._money(lfda)},{oemp},report,1,Final")
    return ("\n".join(lines) + "\n").encode("utf-8")


ARCHIVE_CSV = _archive_csv()


def _archive_means(key):
    rows = [value for (day, _hour), value in ARCHIVE.items() if f"{day:%Y-%m}" == key]
    da = _q(sum(row[0] for row in rows) / len(rows))
    lfdas = [row[1] for row in rows if row[1] is not None]
    lfda = _q(sum(lfdas) / len(lfdas))
    return da, lfda, da + lfda


def _table_rows():
    """{label: (aa, wa)}: May 2025 as published (partly archived); later months from the archive, OEMP = DA + LFDA."""
    rows = {"May 2025": (("22.13", "0.33", "22.46"), ("24.31", "0.36", "24.67"))}
    for key, label in (("2025-06", "Jun 2025"), ("2025-07", "Jul 2025"), ("2025-08", "Aug 2025"),
                       ("2025-09", "Sep 2025")):
        da, lfda, oemp = _archive_means(key)
        rows[label] = ((str(da), str(lfda), str(oemp)), (str(da + 2), str(lfda), str(oemp + 2)))
    return rows


def _table(rows=None):
    html = DATA["market_prices"]["html_excerpt"]
    template = re.search(r'<tr>\s*<td data-label="Date">Aug 2026</td>.*?</tr>', html, flags=re.S).group(0)
    rows = rows or _table_rows()
    for index, pane in enumerate(("AA", "WA")):
        body = "\n".join(
            re.sub(r'(data-label="Date">)[^<]*(<.*?data-label="DA-OZP"[^>]*>)[^<]*(<.*?data-label="LFDA">)[^<]*'
                   r'(<.*?data-label="Ontario Price \(OEMP\)">)[^<]*(<)',
                   lambda m, v=values[index], label=label: (m.group(1) + label + m.group(2) + v[0] + m.group(3) + v[1]
                                                            + m.group(4) + v[2] + m.group(5)),
                   template, flags=re.S)
            for label, values in reversed(list(rows.items())))
        start = html.index('id="' + pane + '"')
        open_at = html.index("<tbody>", start) + len("<tbody>")
        html = html[:open_at] + "\n" + body + "\n" + html[html.index("</tbody>", open_at):]
    return html.encode("utf-8")


def _xlsx(sheets):
    workbook = openpyxl.Workbook()
    default = workbook.worksheets[0]
    for title, rows in sheets.items():
        sheet = workbook.create_sheet(title)
        for row in rows:
            sheet.append(row)
    workbook.remove(default)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _workbook_sheets(kind, last="2025-06", changes=None):
    """The real 2024-2025 rows with actual rates after `last` blanked (the workbook had not listed them yet)."""
    sheets = copy.deepcopy(DATA[kind]["sheets"])
    rows = next(iter(sheets.values()))
    year = None
    for row in rows:
        if row and isinstance(row[0], int):
            year = row[0]
        if len(row) > 1 and str(row[1]).replace("\u200b", "").startswith("Actual"):
            for month in range(1, 13):
                key = f"{year}-{month:02d}"
                if key > last:
                    row[month + 1] = None
                elif key in (changes or {}):
                    row[month + 1] = changes[key]
    return sheets


def _ga_actual(key):
    rows = DATA["ga_mwh_workbook"]["sheets"]["Global Adjustment $MWh"]
    block = next(index for index, row in enumerate(rows) if row and row[0] == int(key[:4]))
    return Decimal(str(rows[block + 2][int(key[5:]) + 1])).quantize(CENT)


def _ga_xml(key, actual=None, first="3.00"):
    if actual is None:
        xml = DATA["ga_reports"]["xml"]["PUB_GlobalAdjustment_202610_v1.xml"]
        xml = xml.replace("<TradeMonth>2026-10</TradeMonth>", f"<TradeMonth>{key}</TradeMonth>")
        return re.sub(r"<FirstEstimateRate>[^<]*<", f"<FirstEstimateRate>{first}<", xml).encode("utf-8")
    xml = DATA["ga_reports"]["xml"]["PUB_GlobalAdjustment_202609_v3.xml"]
    xml = xml.replace("<TradeMonth>2026-09</TradeMonth>", f"<TradeMonth>{key}</TradeMonth>")
    return re.sub(r"<ActualRate>[^<]*<", f"<ActualRate>{actual}<", xml).encode("utf-8")


def _ga_listing(names):
    html = DATA["ga_reports"]["listing_html"]
    template = next(line for line in html.splitlines() if "PUB_GlobalAdjustment_202609_v3.xml" in line)
    lines = [line for line in html.splitlines() if GA_PREFIX not in line]
    footer = lines.index("<hr></pre>")
    rows = [template.replace("PUB_GlobalAdjustment_202609_v3.xml", name) for name in names]
    return ("\n".join(lines[:footer] + rows + lines[footer:]) + "\n").encode("utf-8")


def _ga_reports(sep_actual=None, changes=None):
    actual = {"2025-05": _ga_actual("2025-05"), "2025-06": _ga_actual("2025-06"), "2025-07": "14.38",
              "2025-08": "30.10", "2025-09": sep_actual}
    actual.update(changes or {})
    pages = {}
    for key, value in actual.items():
        name = f"{GA_PREFIX}{key.replace('-', '')}_v{3 if value is not None else 1}.xml"
        pages[bom.GA_DIR + name] = _ga_xml(key, value)
    pages[bom.GA_DIR] = _ga_listing([url[len(bom.GA_DIR):] for url in pages])
    return pages


@functools.lru_cache(maxsize=1)
def _base_world():
    world = {
        gmp.HOEP_DIR: _listing([name for year, name in HOEP_NAMES.items()] + ["PUB_PriceHOEPPredispOR_2025.csv"]),
        gmp.HOEP_AVERAGE_DIR: _listing(list(AVERAGE_NAMES.values())),
        gmp.HOEP_AVERAGE_DIR + AVERAGE_NAMES[2024]: _averages_xml(2024, range(1, 13)),
        gmp.HOEP_AVERAGE_DIR + AVERAGE_NAMES[2025]: _averages_xml(2025, range(1, 5)),
        gmp.ONTARIO_PRICE_URL: _table(),
        gmp.GA_MWH_URL: _xlsx(_workbook_sheets("ga_mwh_workbook")),
        gmp.GA_KWH_URL: _xlsx(_workbook_sheets("ga_kwh_workbook")),
    }
    world.update({gmp.HOEP_DIR + name: _hoep_csv(year) for year, name in HOEP_NAMES.items()})
    world.update(_ga_reports())
    return world


def _world(**changes):
    world = dict(_base_world())
    world.update(changes)
    return world


def _fetcher(world, log=None):
    def fetch(url):
        if log is not None:
            log.append(url)
        if url not in world:
            raise gmp.MarketDataError(f"could not download {url}: HTTP 404")
        return world[url]
    return fetch


def _build(world=None, *, refresh=True, stored=None, hoep=None, archive=ARCHIVE_CSV, as_of=AS_OF, log=None, size=SIZE):
    source = gmp.ReportSource(None, AS_OF, fetch=_fetcher(world or _base_world(), log), delay=0)
    return bom.build(source, hoep_content=hoep, monthly_content=stored, archive_content=archive, as_of=as_of,
                     refresh_hoep=refresh, generated_at=GENERATED, window_months=size, first_month=FIRST)


@functools.lru_cache(maxsize=1)
def _base():
    return _build()


def _monthly(result):
    return {entry["month"]: entry for entry in result.document["monthly"]}


def _bin(document, month, day_type, hour):
    return next(b for b in document["hourly_surface"] if (b["month"], b["day_type"], b["hour"]) == (month, day_type, hour))


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _edit_csv(content, month, **values):
    """A monthly history with one row changed (total recomputed), as a person or an old run might have left it."""
    lines = content.decode("utf-8").splitlines()
    header = lines[0].split(",")
    for index, line in enumerate(lines):
        cells = line.split(",")
        if cells[0] == month:
            for name, value in values.items():
                cells[header.index(name)] = value
            total = Decimal(cells[header.index("energy_arithmetic")]) + Decimal(cells[header.index("ga_class_b")])
            cells[header.index("total_arithmetic")] = f"{total:.2f}"
            lines[index] = ",".join(cells)
    return ("\n".join(lines) + "\n").encode("utf-8")


# -- window, eras and completeness -------------------------------------------------------------------

def test_window_is_the_latest_consecutive_complete_months_and_an_incomplete_month_ends_it():
    result = _base()
    metadata = result.document["metadata"]
    assert result.window == [f"2024-{m:02d}" for m in range(9, 13)] + [f"2025-{m:02d}" for m in range(1, 9)]
    assert metadata["window"] == {"start_month": "2024-09", "end_month": "2025-08", "months": SIZE,
                                  "complete_rule": bom.COMPLETE_RULE}
    assert (metadata["window_start"], metadata["window_end"], metadata["years"]) == ("2024-09-01", "2025-08-31",
                                                                                     [2024, 2025])
    assert metadata["incomplete_months"] == [{"month": "2025-09",
                                              "reason": "no Class B GA actual rate published (latest: FirstEstimateRate)"}]
    assert [month.month for month in result.months] == [f"2024-{m:02d}" for m in range(1, 13)] + [
        f"2025-{m:02d}" for m in range(1, 9)]
    later = _build(_world(**_ga_reports(sep_actual="61.85")))
    assert (later.window[0], later.window[-1]) == ("2024-10", "2025-09")
    assert later.document["metadata"]["incomplete_months"] == []
    earlier = _build(as_of=date(2025, 8, 15))
    assert (earlier.window[0], earlier.window[-1]) == ("2024-08", "2025-07")
    with pytest.raises(gmp.MarketDataError, match="no 12 consecutive complete months"):
        _build(as_of=date(2024, 12, 15))


def test_eras_split_at_may_2025_with_the_validated_monthly_sources():
    result = _base()
    monthly = _monthly(result)
    metadata = result.document["metadata"]
    assert [monthly[key]["era"] for key in result.window] == ["hoep"] * 8 + ["oemp"] * 4
    assert metadata["change_date"] == "2025-05-01"
    assert [(e["id"], e["from"], e["to"]) for e in metadata["eras"]] == [("hoep", "2024-09", "2025-04"),
                                                                          ("oemp", "2025-05", "2025-08")]
    assert metadata["eras"][0]["name"] == "Hourly Ontario Energy Price (HOEP, legacy)"
    assert metadata["eras"][1]["name"] == "Ontario Electricity Market Price (Ontario Price, OEMP)"
    january = monthly["2025-01"]
    assert january["energy_arithmetic"] == pytest.approx(float(_q(_hoep_mean("2025-01"))) / 1000, abs=1e-9)
    assert january["energy_weighted"] == pytest.approx(float(_q(_hoep_mean("2025-01") + 1)) / 1000, abs=1e-9)
    assert (january["energy_source"], january["ga_source"], january["observed_hours"]) == ("hoep_hourly", "ga_workbook",
                                                                                           744)
    assert january["ga_class_b"] == 0.04109 and january["total_arithmetic"] == pytest.approx(
        january["energy_arithmetic"] + 0.04109, abs=1e-9)
    may, july = monthly["2025-05"], monthly["2025-07"]
    assert (may["energy_arithmetic"], may["energy_weighted"], may["ga_class_b"]) == (0.02246, 0.02467, 0.13493)
    assert (may["energy_source"], may["ga_source"], may["observed_hours"]) == ("oemp_monthly_table", "ga_workbook",
                                                                               30 * 24)
    assert (july["ga_class_b"], july["ga_source"]) == (0.01438, "ga_monthly_report")
    assert july["energy_arithmetic"] == pytest.approx(float(_archive_means("2025-07")[2]) / 1000, abs=1e-9)
    assert monthly["2025-06"]["observed_hours"] == 30 * 24 - len(BLANK_LFDA)
    assert bom.serialize_monthly(result.months).decode("utf-8").splitlines()[0] == ",".join(bom.MONTHLY_FIELDS)


def test_ontario_price_months_must_match_the_archive_when_it_covers_the_whole_month():
    checks = _base().document["metadata"]["cross_check"]["oemp_archive_vs_table"]
    assert [entry["month"] for entry in checks["months"]] == ["2025-07", "2025-08", "2025-09"]
    rows = _table_rows()
    aa, wa = rows["Jul 2025"]
    rows["Jul 2025"] = ((str(Decimal(aa[0]) + Decimal("0.05")), aa[1], str(Decimal(aa[2]) + Decimal("0.05"))), wa)
    with pytest.raises(gmp.MarketDataError, match="2025-07 archive OEMP"):
        _build(_world(**{gmp.ONTARIO_PRICE_URL: _table(rows)}))
    rows = _table_rows()
    aa, wa = rows["Aug 2025"]
    rows["Aug 2025"] = ((aa[0], aa[1], str(Decimal(aa[2]) + Decimal("0.02"))), wa)
    with pytest.raises(gmp.MarketDataError, match="DA-OZP .* != OEMP"):
        _build(_world(**{gmp.ONTARIO_PRICE_URL: _table(rows)}))


def test_ga_workbook_and_monthly_report_must_agree():
    overlap = _base().document["metadata"]["cross_check"]["ga_workbook_vs_monthly_reports"]
    assert [entry["month"] for entry in overlap["months"]] == ["2025-05", "2025-06"]
    assert overlap["max_abs_difference"] == 0.0
    with pytest.raises(gmp.MarketDataError, match=r"GA 2025-06: workbook 59.72 vs monthly report 59.73"):
        _build(_world(**_ga_reports(changes={"2025-06": "59.73"})))
    with pytest.raises(gmp.MarketDataError, match="TradeMonth"):
        _build(_world(**{bom.GA_DIR + f"{GA_PREFIX}202507_v3.xml": _ga_xml("2025-08", "14.38")}))


def test_hoep_import_checks_every_hourly_mean_against_the_monthly_averages_report():
    checks = _base().document["metadata"]["cross_check"]["hoep_monthly_arithmetic"]
    assert checks["months_checked"] == 16 and checks["max_abs_difference"] <= 0.005
    wrong = _averages_xml(2024, range(1, 13), override={"2024-05": str(_q(_hoep_mean("2024-05")) + Decimal("0.02"))})
    with pytest.raises(gmp.MarketDataError, match="2024-05 hourly mean"):
        _build(_world(**{gmp.HOEP_AVERAGE_DIR + AVERAGE_NAMES[2024]: wrong}))


def test_partial_final_year_month_that_does_not_match_is_left_unobserved():
    source = gmp.ReportSource(None, AS_OF, fetch=_fetcher(_base_world()), delay=0)
    rows, averages, _files = bom.import_hoep(source, FIRST)
    assert max(day for day, _ in rows) == date(2025, 4, 30) and len(rows) == (366 + 120) * 24
    averages = copy.deepcopy(averages)
    averages["2025-03"]["arithmetic"] = round(averages["2025-03"]["arithmetic"] + 0.04, 2)
    energies, check, failures, dropped = bom.hoep_energy(rows, FIRST, averages, {})
    assert failures == [] and dropped == ["2025-03", "2025-04"]
    assert energies["2025-03"] == (_q(Decimal(str(averages["2025-03"]["arithmetic"]))), _q(_hoep_mean("2025-03") + 1),
                                   bom.HOEP_REPORT)
    assert energies["2025-02"][2] == bom.HOEP_HOURLY and check["months_checked"] == 14
    averages["2024-12"]["arithmetic"] = round(averages["2024-12"]["arithmetic"] + 0.04, 2)
    assert bom.hoep_energy(rows, FIRST, averages, {})[2] == [f"2024-12 hourly mean {_hoep_mean('2024-12'):.4f} vs "
                                                              f"published {averages['2024-12']['arithmetic']:.2f}"]


def test_unobserved_final_year_month_keeps_the_report_values_and_no_hours():
    wrong = _averages_xml(2025, range(1, 5), override={"2025-04": str(_q(_hoep_mean("2025-04")) + Decimal("0.04"))})
    result = _build(_world(**{gmp.HOEP_AVERAGE_DIR + AVERAGE_NAMES[2025]: wrong}), size=17)
    april = _monthly(result)["2025-04"]
    assert (april["energy_source"], april["observed_hours"]) == ("hoep_monthly_report", 0)
    assert april["energy_arithmetic"] == pytest.approx(float(_q(_hoep_mean("2025-04")) + Decimal("0.04")) / 1000)
    metadata = result.document["metadata"]
    assert [entry["month"] for entry in metadata["unobserved_hoep_months"]] == ["2025-04"]
    assert "legacy HOEP hours of 2025-04 are left out" in metadata["heatmap_basis"]
    assert max(day for day, _ in result.hoep) == date(2025, 3, 31)
    assert _bin(result.document, 4, "weekday", 0)["hours_hoep"] == 22  # April 2024 only


# -- monthly history -------------------------------------------------------------------------------

def test_monthly_history_revision_rule():
    base = _base()
    stored = bom.serialize_monthly(base.months)
    hoep = bom.serialize_hoep(base.hoep)
    again = _build(refresh=False, stored=stored, hoep=hoep)
    assert again.revisions == [] and bom.serialize_monthly(again.months) == stored
    recent = _build(refresh=False, stored=_edit_csv(stored, "2025-08", ga_class_b="30.00"), hoep=hoep)
    revision = {"month": "2025-08", "field": "ga_class_b", "previous_per_mwh": 30.0, "new_per_mwh": 30.1}
    assert recent.revisions == [revision] and recent.document["metadata"]["revisions"] == [revision]
    assert bom.serialize_monthly(recent.months) == stored
    with pytest.raises(gmp.MarketDataError, match="2024-10 ga_class_b changed from 74.00 to 74.84"):
        _build(refresh=False, stored=_edit_csv(stored, "2024-10", ga_class_b="74.00"), hoep=hoep)
    with pytest.raises(gmp.MarketDataError, match="total_arithmetic"):
        _build(refresh=False, stored=stored.replace(b"2025-08,oemp,", b"2025-08,oemp,1", 1), hoep=hoep)


def test_months_are_kept_when_their_sources_disappear_and_ci_needs_no_legacy_downloads():
    base = _base()
    stored = bom.serialize_monthly(base.months)
    world = {url: content for url, content in _base_world().items()
             if not url.startswith((gmp.HOEP_DIR, gmp.HOEP_AVERAGE_DIR))}
    world.update(_ga_reports(changes={"2025-07": None}))
    log = []
    result = _build(world, refresh=False, stored=stored, hoep=bom.serialize_hoep(base.hoep), log=log)
    assert bom.serialize_monthly(result.months) == stored
    assert not [url for url in log if "HOEP" in url]
    with pytest.raises(gmp.MarketDataError, match="run once with --refresh-hoep"):
        _build(world, refresh=False, stored=None, hoep=bom.serialize_hoep(base.hoep))


# -- heatmap bins and metadata ---------------------------------------------------------------------

def _expected_bin(month, day_type, hour, window):
    hoep_hours, oemp_hours, energy, rate = 0, 0, Decimal(0), Decimal(0)
    for key in window:
        if int(key[5:]) != month:
            continue
        for day in _month_days(key):
            if ("weekend" if _weekend(day) else "weekday") != day_type:
                continue
            if key <= "2025-04":
                hoep_hours += 1
                energy += _hoep(day, hour + 1)
            elif (day, hour + 1) in ARCHIVE and ARCHIVE[(day, hour + 1)][1] is not None:
                oemp_hours += 1
                energy += ARCHIVE[(day, hour + 1)][0] + ARCHIVE[(day, hour + 1)][1]
            else:
                continue
            rate += _ga_actual(key) if key <= "2025-06" else Decimal({"2025-07": "14.38", "2025-08": "30.10"}[key])
    count = hoep_hours + oemp_hours
    return hoep_hours, oemp_hours, float(energy / count / 1000), float(rate / count / 1000)


@pytest.mark.parametrize("month,day_type,hour", [(1, "weekday", 0), (7, "weekday", 16), (6, "weekday", 0),
                                                 (5, "weekend", 23), (9, "weekend", 12)])
def test_bins_use_observed_hours_only(month, day_type, hour):
    result = _base()
    entry = _bin(result.document, month, day_type, hour)
    hours_hoep, hours_oemp, energy, rate = _expected_bin(month, day_type, hour, result.window)
    assert (entry["hours_hoep"], entry["hours_oemp"], entry["hours_count"]) == (hours_hoep, hours_oemp,
                                                                                hours_hoep + hours_oemp)
    assert entry["avg_energy_price"] == pytest.approx(energy, abs=1e-6)
    assert entry["avg_ga_class_b"] == pytest.approx(rate, abs=1e-6)
    assert entry["combined"] == pytest.approx(energy + rate, abs=1e-6)


def test_bin_counts_follow_the_archive_and_blank_lfda_hours():
    document = _base().document
    surface = document["hourly_surface"]
    assert len(surface) == 576 and all(set(b) == set(bom.BIN_FIELDS) for b in surface)
    assert _bin(document, 6, "weekday", 0)["hours_oemp"] == 21 - 1  # June 10, 2025 (a Tuesday) hour 0 is blank
    assert _bin(document, 6, "weekday", 3)["hours_oemp"] == 21
    assert _bin(document, 5, "weekday", 0)["hours_oemp"] == 21  # May 1, 2025 is before the archive starts
    assert {b["hours_hoep"] for b in surface if b["month"] in (5, 6, 7, 8)} == {0}
    assert {b["hours_oemp"] for b in surface if b["month"] not in (5, 6, 7, 8)} == {0}
    covered = document["metadata"]["coverage"]
    assert covered["hours"] == sum(b["hours_count"] for b in surface) == covered["hours_hoep"] + covered["hours_oemp"]
    assert covered["hours_oemp"] == (30 + 30 + 31 + 31) * 24 - len(BLANK_LFDA)
    assert covered["unobserved_hours"] == 24 + len(BLANK_LFDA)
    assert document["metadata"]["gap"]["from"] == "2025-05-01" and document["metadata"]["gap"]["to"] == "2025-05-01"
    short = {key: value for key, value in ARCHIVE.items() if key[0].month != 7}
    with pytest.raises(gmp.MarketDataError, match="no observed hours for month 7"):
        _build(archive=_archive_csv(short))


def test_metadata_keeps_the_legacy_keys_and_describes_the_rolling_history():
    metadata = _base().document["metadata"]
    assert set(gmp.REQUIRED_METADATA) <= set(metadata)
    assert all(metadata[key] for key in gmp.REQUIRED_METADATA)
    assert metadata["schema_version"] == 2 and metadata["derivation_method"] == "observed_rolling_12m_hoep_oemp_ga"
    assert bom.DERIVATION_METHOD == market_pricing.ROLLING_METHOD == "observed_rolling_60m_hoep_oemp_ga"
    assert (metadata["province"], metadata["market_operator"], metadata["unit"]) == ("ON", "IESO", "$/kWh (CAD)")
    assert metadata["generated_at"] == "2025-10-16T12:00:00Z" and metadata["revisions"] == []
    assert metadata["hoep_retirement"]["retired_on"] == "2025-04-30"
    assert set(metadata["gap"]) == {"from", "to", "reason"} and "90 days" in metadata["gap"]["reason"]
    assert "observed hourly" in metadata["heatmap_basis"] and "never modelled" in metadata["heatmap_basis"]
    assert all(set(source) == {"name", "url", "type"} for source in metadata["sources"])
    for phrase in ("not a tariff, a bill or a forecast", "Class A", "peak demand factor", "Delivery, regulatory, loss",
                   "never modelled"):
        assert phrase in metadata["notes"]
    texts = list(_strings(metadata))
    for text in texts:
        if text.startswith("http"):
            continue
        for sentence in re.split(r"(?<=[.;])\s+", text):
            if "HOEP" in sentence or "Hourly Ontario Energy Price" in sentence:
                assert "retire" in sentence.lower() or "legacy" in sentence.lower(), sentence
    joined = " ".join(texts).lower()
    for phrase in ("current hoep", "hoep is ", "trailing 12", "representative"):
        assert phrase not in joined


# -- command line ------------------------------------------------------------------------------------

def _paths(tmp_path):
    paths = {name: tmp_path / name for name in ("market.json", "monthly.csv", "hoep.csv", "archive.csv")}
    paths["archive.csv"].write_bytes(ARCHIVE_CSV)
    return paths


def _args(paths, *extra):
    return ["--output", str(paths["market.json"]), "--monthly-csv", str(paths["monthly.csv"]), "--hoep-csv",
            str(paths["hoep.csv"]), "--archive", str(paths["archive.csv"]), "--as-of", "2025-10-16", *extra]


def test_main_writes_nothing_on_failure_and_everything_after_all_checks(tmp_path, capsys):
    paths = _paths(tmp_path)
    paths["market.json"].write_text("previous", encoding="utf-8")
    broken = _world(**_ga_reports(changes={"2025-06": "59.73"}))
    options = {"generated_at": GENERATED, "window_months": SIZE, "first_month": FIRST}
    assert bom.main(_args(paths, "--refresh-hoep"), fetch=_fetcher(broken), **options) == 1
    assert "ERROR" in capsys.readouterr().err
    assert paths["market.json"].read_text(encoding="utf-8") == "previous"
    assert not paths["monthly.csv"].exists() and not paths["hoep.csv"].exists()
    assert bom.main(_args(paths, "--refresh-hoep", "--dry-run"), fetch=_fetcher(_world()), **options) == 0
    assert paths["market.json"].read_text(encoding="utf-8") == "previous" and not paths["monthly.csv"].exists()
    assert bom.main(_args(paths, "--refresh-hoep"), fetch=_fetcher(_world()), **options) == 0
    written = {name: path.read_bytes() for name, path in paths.items()}
    assert json.loads(written["market.json"])["metadata"]["window"]["end_month"] == "2025-08"
    assert written["hoep.csv"].startswith(b"date,hour_ending,hoep\n2024-01-01,1,")
    assert written["monthly.csv"].startswith(b"month,era,energy_arithmetic,energy_weighted,ga_class_b,")
    assert not list(tmp_path.glob("*.tmp"))
    log = []
    assert bom.main(_args(paths), fetch=_fetcher(_world(), log), **options) == 0
    assert not [url for url in log if "HOEP" in url]
    written = {name: path.read_bytes() for name, path in paths.items()}
    capsys.readouterr()
    options["generated_at"] = GENERATED + timedelta(days=1)
    assert bom.main(_args(paths), fetch=_fetcher(_world()), **options) == 0
    assert "All outputs are unchanged." in capsys.readouterr().out
    assert {name: path.read_bytes() for name, path in paths.items()} == written
    paths["hoep.csv"].unlink()
    assert bom.main(_args(paths), fetch=_fetcher(_world()), **options) == 1


# -- market_pricing consumers ------------------------------------------------------------------------

def _write(tmp_path, document, method):
    path = tmp_path / "market.json"
    document = copy.deepcopy(document)
    document["metadata"]["derivation_method"] = method
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_market_pricing_reads_both_observed_methods(tmp_path):
    document = _base().document
    path = _write(tmp_path, document, market_pricing.ROLLING_METHOD)
    assert market_pricing.get_observed_bin(7, "weekday", 16, path) == _bin(document, 7, "weekday", 16)
    july = market_pricing.get_monthly_average(7, path)
    bins = [b for b in document["hourly_surface"] if b["month"] == 7]
    assert july["hours"] == sum(b["hours_count"] for b in bins)
    assert market_pricing.get_monthly_series(path) == document["monthly"]
    legacy = _write(tmp_path, {"metadata": {}, "hourly_surface": document["hourly_surface"]},
                    "observed_legacy_hoep_2020_2024_average")
    assert market_pricing.load_ontario_market_pricing(legacy)["hourly_surface"]
    with pytest.raises(ValueError, match="no monthly series"):
        market_pricing.get_monthly_series(legacy)


@pytest.mark.parametrize("method", ["observed_trailing_12_month_average", "observed_rolling_12m_hoep_oemp_ga",
                                    "observed_rolling_60m_hoep_oemp_ga_v2", "representative_historical_model", None])
def test_market_pricing_rejects_other_methods(tmp_path, method):
    path = tmp_path / "market.json"
    path.write_text(json.dumps({"metadata": {"derivation_method": method}, "hourly_surface": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="not an observed IESO market surface"):
        market_pricing.load_ontario_market_pricing(path)


# -- synthetic load profile (Phase 7E, illustrative) -------------------------------------------------

BUSINESS = 12 * 365.25 * 5 / 7 / 12
OTHER = 730.5 - BUSINESS


def _month_keys(end, count=60):
    index = int(end[:4]) * 12 + int(end[5:]) - 1
    return [f"{i // 12:04d}-{i % 12 + 1:02d}" for i in range(index - count + 1, index + 1)]


def _synthetic_document(end="2026-08"):
    """Hand-computable: weekday hours 7-18 at 0.10 $/kWh (July 0.20), other hours 0.05; 10 or 4 hours per bin."""
    surface = []
    for month in range(1, 13):
        for kind in ("weekday", "weekend"):
            for hour in range(24):
                business = kind == "weekday" and 7 <= hour <= 18
                price = (0.20 if month == 7 else 0.10) if business else 0.05
                surface.append({"month": month, "day_type": kind, "hour": hour, "hours_count": 10 if kind == "weekday"
                                else 4, "avg_energy_price": price, "avg_ga_class_b": 0.04, "combined": price + 0.04,
                                "hours_hoep": 0, "hours_oemp": 10 if kind == "weekday" else 4})
    keys = _month_keys(end)
    monthly = [{"month": key, "era": "oemp", "energy_arithmetic": round(0.05 + 0.001 * index, 6),
                "energy_weighted": 0.06, "ga_class_b": 0.04, "total_arithmetic": round(0.09 + 0.001 * index, 6),
                "energy_source": "oemp_monthly_table", "ga_source": "ga_workbook", "observed_hours": 0}
               for index, key in enumerate(keys)]
    metadata = {"derivation_method": market_pricing.ROLLING_METHOD,
                "window": {"start_month": keys[0], "end_month": keys[-1], "months": 60}}
    return {"metadata": metadata, "monthly": monthly, "hourly_surface": surface}


def _expected_price(document, kwh, kw):
    base = (kwh - kw * BUSINESS) / OTHER
    factors = {}
    for month in range(1, 13):
        high = 0.20 if month == 7 else 0.10
        time_weighted = (120 * high + 120 * 0.05 + 96 * 0.05) / 336
        profile = (kw * 120 * high + base * 120 * 0.05 + base * 96 * 0.05) / (kw * 120 + base * 120 + base * 96)
        factors[month] = profile / time_weighted
    totals = [entry["energy_arithmetic"] * factors[int(entry["month"][5:])] + entry["ga_class_b"]
              for entry in document["monthly"]]
    return base, factors, sum(totals) / len(totals)


@pytest.mark.parametrize("kwh,kw", [(40000, 100), (500000, 1000)])
def test_synthetic_profile_price_on_a_hand_computable_surface(kwh, kw):
    document = _synthetic_document()
    result = market_pricing.synthetic_profile_price(document, kwh=kwh, kw=kw, as_of=date(2026, 10, 16))
    base, factors, price = _expected_price(document, kwh, kw)
    assert result["ok"] is True and result["reason"] is None
    assert result["price_per_kwh"] == pytest.approx(price, abs=1e-6)
    assert result["label"] == "SYNTHETIC LOAD PROFILE - ILLUSTRATIVE ONLY"
    profile = result["profile"]
    assert profile["base_kw"] == pytest.approx(base, abs=1e-6) and profile["peak_kw"] == kw
    assert profile["business_hours_beginning"] == list(range(7, 19)) and profile["days"] == "Monday-Friday"
    assert profile["business_hours_per_month"] == pytest.approx(260.892857, abs=1e-6)
    assert profile["other_hours_per_month"] == pytest.approx(469.607143, abs=1e-6)
    assert result["window"] == {"start_month": "2021-09", "end_month": "2026-08", "months": 60}
    assert result["shape_factors"] == {str(m): pytest.approx(factors[m], abs=1e-6) for m in range(1, 13)}
    assert len(result["months"]) == 60 and result["months"][0]["month"] == "2021-09"
    july = next(entry for entry in result["months"] if entry["month"] == "2026-07")
    assert july["shaped_energy"] == pytest.approx(july["energy_level"] * factors[7], abs=1e-6)
    assert july["total"] == pytest.approx(july["shaped_energy"] + 0.04, abs=1e-6)
    assert result["profile"]["base_kw"] == pytest.approx(29.622024 if kw == 100 else 509.164195, abs=1e-6)


def _not_ok(document, reason, **options):
    arguments = {"kwh": 40000, "kw": 100, "as_of": date(2026, 10, 16), **options}
    result = market_pricing.synthetic_profile_price(document, **arguments)
    assert result["ok"] is False and result["price_per_kwh"] is None, result
    assert reason in result["reason"], result["reason"]
    assert result["label"] == "SYNTHETIC LOAD PROFILE - ILLUSTRATIVE ONLY"


def test_synthetic_profile_price_refuses_doubtful_inputs():
    document = _synthetic_document()
    legacy = copy.deepcopy(document)
    legacy["metadata"]["derivation_method"] = "observed_legacy_hoep_2020_2024_average"
    _not_ok(legacy, "not the rolling observed history")
    _not_ok(document, "stale market history", as_of=date(2027, 1, 1))
    assert market_pricing.synthetic_profile_price(document, kwh=40000, kw=100, as_of=date(2026, 12, 31))["ok"]
    _not_ok(document, "base load would be negative", kwh=1000)
    _not_ok(document, "would exceed the business-hours load", kwh=100000, kw=10)
    _not_ok(document, "kwh and kw must be positive", kwh=0)
    cheap = copy.deepcopy(document)
    for entry in cheap["hourly_surface"]:
        if entry["month"] == 3:
            entry["avg_energy_price"] = 0.0005
    _not_ok(cheap, "calendar month 3: time-weighted mean energy")
    missing_bin = copy.deepcopy(document)
    missing_bin["hourly_surface"].pop(100)
    _not_ok(missing_bin, "bins or monthly records missing/invalid")
    missing_month = copy.deepcopy(document)
    missing_month["monthly"].pop(10)
    _not_ok(missing_month, "bins or monthly records missing/invalid")
    bad_value = copy.deepcopy(document)
    bad_value["monthly"][5]["ga_class_b"] = None
    _not_ok(bad_value, "bins or monthly records missing/invalid")
