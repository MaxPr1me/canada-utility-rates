"""Ontario Price hourly archive (scripts/archive_ontario_price.py); fake fetchers and saved IESO excerpts only."""
import importlib.util
import json
import re
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "ieso_ontario_price.json"
SCRIPT = ROOT / "scripts" / "archive_ontario_price.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("archive_ontario_price", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


aop = _load_script()
DATA = json.loads(FIXTURE.read_text(encoding="utf-8"))
RUN_DATE = date(2026, 10, 15)
HOURS = list(range(1, 25))
LISTING = DATA["da_listing"]["html_excerpt"]
REPORTS = {name: entry["xml"] for name, entry in DATA["da_reports"].items()}
PREFIX = "PUB_DAHourlyOntarioZonalPrice_"
SEP15, SEP24, OCT08 = date(2026, 9, 15), date(2026, 9, 24), date(2026, 10, 8)
V1_0924, V3_0924, V1_1008 = (PREFIX + "20260924_v1.xml", PREFIX + "20260924_v3.xml", PREFIX + "20261008_v1.xml")
LFDA_LISTING = DATA["lfda"]["listing_html"]
LFDA_2025 = DATA["lfda"]["csv"]["2025"]["csv_excerpt"]
LFDA_OCT09 = DATA["lfda"]["csv"]["2026_retrieved_2026-10-09"]["csv_excerpt"]
LFDA_OCT15 = DATA["lfda"]["csv"]["2026_retrieved_2026-10-15"]["csv_excerpt"]
TABLE = DATA["market_prices"]["html_excerpt"]
API_JSON = DATA["site_api"]["json"]
CENT = Decimal("0.01")


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    def blocked(*args, **kwargs):
        raise RuntimeError("live network disabled in deterministic tests")

    monkeypatch.setattr(aop.requests, "get", blocked)
    monkeypatch.setattr(aop.gmp, "REQUEST_DELAY_SECONDS", 0)


# -- independent readers and builders (not the code under test) --------------------------------------

def _xml_prices(xml):
    pairs = re.findall(r"<PricingHour>(\d+)</PricingHour>\s*<ZonalPrice>([^<]+)</ZonalPrice>", xml)
    return {int(hour): Decimal(price) for hour, price in pairs}


def _lfda_rows(text):
    rows = {}
    for line in text.splitlines()[1:]:
        day, hour, status, rate = line.split(",")
        rows[(date.fromisoformat(day), int(hour))] = (Decimal(rate) if rate else None, status)
    return rows


BASE_XML = REPORTS[V1_1008]
BASE_PRICES = _xml_prices(BASE_XML)
LFDA_BASE = {hour: text.split(",")[3] for hour, text in enumerate(
    [line for line in LFDA_OCT15.splitlines() if line.startswith("2026-09-15,")], start=1)}


def _price(day, hour, shift="0"):
    return BASE_PRICES[hour] + Decimal(day.day) / 4 + Decimal(shift)


def _report_xml(day, prices):
    """The real 2026-10-08 report re-dated to day with the given hourly prices."""
    xml = BASE_XML.replace("<DeliveryDate>2026-10-08</DeliveryDate>", f"<DeliveryDate>{day.isoformat()}</DeliveryDate>")

    def swap(match):
        return f"<PricingHour>{match.group(1)}</PricingHour>\n<ZonalPrice>{prices[int(match.group(1))]}</ZonalPrice>"
    return re.sub(r"<PricingHour>(\d+)</PricingHour>\n<ZonalPrice>[^<]+</ZonalPrice>", swap, xml)


def _drop_hour(xml, hour):
    block = re.search(rf"<HourlyPriceComponents>\n<PricingHour>{hour}</PricingHour>.*?</HourlyPriceComponents>\n",
                      xml, flags=re.S)
    return xml.replace(block.group(0), "")


def _listing(names):
    """The real listing layout (header, one row per file, footer) for the given report files."""
    lines = LISTING.split("\n")
    template = next(line for line in lines if V1_1008 in line)
    kept = [line for line in lines if PREFIX not in line]
    footer = kept.index("<hr></pre>")
    return "\n".join(kept[:footer] + [template.replace(V1_1008, name) for name in names] + kept[footer:])


def _lfda_csv(days):
    lines = ["Date,Hour,Status,LFDA Rate ($/MWh)"]
    lines += [f"{day.isoformat()},{hour},Final,{LFDA_BASE[hour]}" for day in days for hour in HOURS]
    return "\n".join(lines) + "\n"


def _table(rows):
    """The fixture tables with the arithmetic-average (tab AA) row of each "Mon YYYY" label replaced."""
    html = TABLE
    for label, values in rows.items():
        pattern = re.compile(r'(data-label="Date">' + label + r'</td>\s*<td data-label="DA-OZP"[^>]*>)[^<]*'
                             r'(</td>\s*<td data-label="LFDA">)[^<]*(</td>\s*<td data-label="Ontario Price \(OEMP\)">)'
                             r'[^<]*(</td>)')
        html = pattern.sub(lambda m: m.group(1) + values[0] + m.group(2) + values[1] + m.group(3) + values[2]
                           + m.group(4), html, count=1)
    return html


def _average(values):
    return str((sum(values, Decimal(0)) / len(values)).quantize(CENT, rounding=ROUND_HALF_UP))


def _days(first, last):
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _web(listing=LISTING, reports=None, lfda_2026=LFDA_OCT09, table=TABLE):
    pages = {
        aop.DA_DIR: listing,
        aop.LFDA_DIR: LFDA_LISTING,
        aop.LFDA_DIR + "PUB_HourlyLFDA_2025_v1.csv": LFDA_2025,
        aop.LFDA_DIR + "PUB_HourlyLFDA_2026_v1.csv": lfda_2026,
        aop.PRICES_URL: table,
    }
    pages.update({aop.DA_DIR + name: xml for name, xml in (REPORTS if reports is None else reports).items()})
    return pages


def _fetch(pages, log=None):
    encoded = {url: body.encode("utf-8") for url, body in pages.items()}

    def fetch(url):
        if log is not None:
            log.append(url)
        if url not in encoded:
            raise aop.MarketDataError(f"could not download {url}: HTTP 404")
        return encoded[url]
    return fetch


def _source(pages, log=None, cache_dir=None):
    return aop.ReportSource(cache_dir, RUN_DATE, fetch=_fetch(pages, log), delay=0)


def _api_json(days, shift="0"):
    entries = [{"ReportDate": (day - timedelta(days=1)).isoformat(), "ReportForDate": day.isoformat(), "Hour": hour,
                "Price": float(_price(day, hour, shift))} for day in days for hour in HOURS]
    return json.dumps({"Predisp": [], "DayAhead": entries})


def _api(responses, log):
    def fetch(url):
        log.append(url)
        return responses.get(url, "").encode("utf-8")
    return aop.SiteApiSource(None, RUN_DATE, fetch=fetch, delay=0)


def _month_web(days, mutate=None, table_values=None, lfda_days=None):
    """Synthetic daily reports (the real 2026-10-08 hourly profile, shifted by day) and Final LFDA for them."""
    names, reports = [], {}
    for day in days:
        prices = {hour: _price(day, hour) for hour in HOURS}
        if mutate and day == mutate[0]:
            prices[mutate[1]] += Decimal(mutate[2])
        name = f"{PREFIX}{day:%Y%m%d}_v1.xml"
        names.append(name)
        reports[name] = _report_xml(day, prices)
    return _web(listing=_listing(names), reports=reports, lfda_2026=_lfda_csv(days if lfda_days is None else lfda_days),
                table=_table(table_values or {}))


AUGUST = _days(date(2026, 8, 1), date(2026, 8, 31))
AUGUST_DA = [_price(day, hour) for day in AUGUST for hour in HOURS]
AUGUST_LFDA = [Decimal(LFDA_BASE[hour]) for _ in AUGUST for hour in HOURS]
AUGUST_TABLE = {"Aug 2026": (_average(AUGUST_DA), _average(AUGUST_LFDA),
                             _average([da + lfda for da, lfda in zip(AUGUST_DA, AUGUST_LFDA)]))}


# -- official report parsing -------------------------------------------------------------------------

def test_daily_report_parse_reads_24_hourly_prices():
    prices = aop.parse_da_report(BASE_XML.encode(), OCT08, V1_1008)

    assert sorted(prices) == HOURS
    assert prices == BASE_PRICES
    assert prices[1] == Decimal("31.39") and prices[24] == Decimal("42.10")


def test_daily_report_with_23_hours_or_a_repeated_hour_is_rejected():
    with pytest.raises(aop.MarketDataError, match=r"expected hours 1-24, found 23 \(missing \[24\]\)"):
        aop.parse_da_report(_drop_hour(BASE_XML, 24).encode(), OCT08, V1_1008)
    repeated = BASE_XML.replace("<PricingHour>24</PricingHour>", "<PricingHour>23</PricingHour>")
    with pytest.raises(aop.MarketDataError, match="duplicate hour 23"):
        aop.parse_da_report(repeated.encode(), OCT08, V1_1008)


@pytest.mark.parametrize("old, new, message", [
    ("<DocTitle>Day Ahead Hourly Ontario Zonal Energy Price Report</DocTitle>", "<DocTitle>Other</DocTitle>",
     "unexpected report title"),
    ('docID="DAHourlyOntarioZonalPrice"', 'docID="DAHourlyZonal"', "expected an IESO DAHourlyOntarioZonalPrice"),
    ("<DeliveryDate>2026-10-08</DeliveryDate>", "<DeliveryDate>2026-10-09</DeliveryDate>", "does not match"),
    ("<ZonalPrice>31.39</ZonalPrice>", "<ZonalPrice>n/a</ZonalPrice>", "expected a price"),
    ("<ZonalPrice>31.39</ZonalPrice>", "<ZonalPrice>31.391</ZonalPrice>", "at most two decimals"),
    ("<ZonalPrice>31.39</ZonalPrice>", "<ZonalPrice>2000.01</ZonalPrice>", "outside"),
    ("<ZonalPrice>31.39</ZonalPrice>", "<ZonalPrice>-2000.01</ZonalPrice>", "outside"),
])
def test_daily_report_with_unexpected_content_is_rejected(old, new, message):
    assert old in BASE_XML
    with pytest.raises(aop.MarketDataError, match=message):
        aop.parse_da_report(BASE_XML.replace(old, new, 1).encode(), OCT08, V1_1008)


def test_lfda_report_keeps_blank_values_and_rejects_partial_days():
    values = aop.parse_lfda_csv(LFDA_2025, 2025, "PUB_HourlyLFDA_2025.csv")

    assert values == _lfda_rows(LFDA_2025)
    assert {values[(date(2025, 5, 1), hour)] for hour in HOURS} == {(None, "Final")}
    assert values[(date(2025, 5, 3), 1)][0] is not None
    lines = LFDA_2025.splitlines()
    with pytest.raises(aop.MarketDataError, match=r"2025-05-03: expected hours 1-24"):
        aop.parse_lfda_csv("\n".join(lines[:-1]) + "\n", 2025, "fixture")
    with pytest.raises(aop.MarketDataError, match="unexpected header"):
        aop.parse_lfda_csv(LFDA_2025.replace("LFDA Rate ($/MWh)", "LFDA Rate"), 2025, "fixture")
    with pytest.raises(aop.MarketDataError, match="date 2025-05-01 is outside 2026"):
        aop.parse_lfda_csv(LFDA_2025, 2026, "fixture")


def test_market_table_reads_both_tabs_and_rejects_changed_layout():
    tables = aop.parse_market_table(TABLE)

    assert sorted(tables["arithmetic"]) == ["2025-05", "2026-05", "2026-07", "2026-08"]
    assert tables["arithmetic"]["2026-08"] == {"da_ozp": Decimal("63.88"), "lfda": Decimal("0.52"),
                                               "oemp": Decimal("64.40")}
    assert tables["arithmetic"]["2025-05"] == {"da_ozp": Decimal("22.13"), "lfda": Decimal("0.33"),
                                               "oemp": Decimal("22.46")}
    assert tables["weighted"]["2026-08"]["da_ozp"] == Decimal("67.66")
    with pytest.raises(aop.MarketDataError, match="unexpected columns"):
        aop.parse_market_table(TABLE.replace("<th>LFDA</th>", "<th>Adjustment</th>", 1))
    with pytest.raises(aop.MarketDataError, match="tab WA"):
        aop.parse_market_table(TABLE.replace('id="WA"', 'id="XX"'))
    with pytest.raises(aop.MarketDataError, match="unexpected month"):
        aop.parse_market_table(TABLE.replace("Aug 2026", "2026-08", 1))


def test_site_api_excerpt_equals_the_official_report_for_the_same_day():
    served = aop.parse_site_api(API_JSON.encode(), OCT08, OCT08, "fixture")

    assert served == {OCT08: aop.parse_da_report(BASE_XML.encode(), OCT08, V1_1008)}
    assert aop.parse_site_api(b"", OCT08, OCT08, "404") == {}
    with pytest.raises(aop.MarketDataError, match="no DayAhead list"):
        aop.parse_site_api(b'{"Predisp": []}', OCT08, OCT08, "fixture")


# -- merging ------------------------------------------------------------------------------------------

def test_highest_report_version_is_used_and_lower_versions_are_not_downloaded():
    assert _xml_prices(REPORTS[V1_0924]) == _xml_prices(REPORTS[V3_0924])
    shifted_v1 = _report_xml(SEP24, {hour: price + 1 for hour, price in _xml_prices(REPORTS[V1_0924]).items()})
    log = []

    result = aop.update_archive(_source(_web(reports=dict(REPORTS, **{V1_0924: shifted_v1})), log), {})

    assert {result.rows[(SEP24, hour)].version for hour in HOURS} == {3}
    assert {hour: result.rows[(SEP24, hour)].da_ozp for hour in HOURS} == _xml_prices(REPORTS[V3_0924])
    assert result.downloaded == {SEP15: 1, SEP24: 3, OCT08: 1}
    assert aop.DA_DIR + V3_0924 in log
    assert not [url for url in log if re.search(r"_20260924(_v[12])?\.xml$|ZonalPrice\.xml$", url)]


def test_cached_higher_version_is_used_and_unversioned_only_days_are_skipped(tmp_path):
    folder = tmp_path / "reports-public.ieso.ca_public_DAHourlyOntarioZonalPrice"
    folder.mkdir()
    revised = {hour: price + Decimal("0.05") for hour, price in BASE_PRICES.items()}
    (folder / (PREFIX + "20261008_v2.xml")).write_text(_report_xml(OCT08, revised), encoding="utf-8")
    listing = LISTING.replace("<hr></pre>", f'<a href="{PREFIX}20261009.xml">{PREFIX}20261009.xml</a>\n<hr></pre>')
    log = []

    result = aop.update_archive(_source(_web(listing=listing), log, cache_dir=tmp_path), {})

    assert [result.rows[(OCT08, hour)] for hour in HOURS] == [aop.Row(revised[hour], aop.REPORT, 2) for hour in HOURS]
    assert aop.DA_DIR + V1_1008 not in log and aop.DA_DIR + PREFIX + "20261008_v2.xml" not in log
    assert result.unversioned == [date(2026, 10, 9)]
    assert (date(2026, 10, 9), 1) not in result.rows


@pytest.mark.parametrize("source, version", [(aop.SITE_API, None), (aop.REPORT, 1)])
def test_report_replaces_site_api_rows_and_lower_versions(source, version):
    existing = {(SEP24, hour): aop.Row(Decimal("99.99"), source, version, Decimal("0.01"), "Preliminary")
                for hour in HOURS}

    result = aop.update_archive(_source(_web()), existing)

    official = _xml_prices(REPORTS[V3_0924])
    lfda = _lfda_rows(LFDA_OCT09)
    assert [result.rows[(SEP24, hour)] for hour in HOURS] == [
        aop.Row(official[hour], aop.REPORT, 3, *lfda[(SEP24, hour)]) for hour in HOURS]
    assert (result.added, result.updated) == (48, 24)


def test_higher_archived_version_is_kept():
    existing = {(SEP24, hour): aop.Row(Decimal("99.99"), aop.REPORT, 5) for hour in HOURS}
    log = []

    result = aop.update_archive(_source(_web(), log), existing)

    assert {result.rows[(SEP24, hour)].da_ozp for hour in HOURS} == {Decimal("99.99")}
    assert {result.rows[(SEP24, hour)].version for hour in HOURS} == {5}
    assert not [url for url in log if "20260924" in url]


def test_lfda_value_and_status_follow_the_published_report():
    first = aop.update_archive(_source(_web(lfda_2026=LFDA_OCT09)), {})
    second = aop.update_archive(_source(_web(lfda_2026=LFDA_OCT15)), first.rows)

    old, new = _lfda_rows(LFDA_OCT09), _lfda_rows(LFDA_OCT15)
    assert [hour for hour in HOURS if old[(SEP15, hour)][0] != new[(SEP15, hour)][0]] == [13, 14, 16, 17]
    assert {first.rows[(SEP15, hour)].lfda_status for hour in HOURS} == {"Preliminary"}
    for hour in HOURS:
        row = second.rows[(SEP15, hour)]
        assert (row.lfda, row.lfda_status) == new[(SEP15, hour)] == (new[(SEP15, hour)][0], "Final")
        assert row.oemp == row.da_ozp + row.lfda
    assert (second.added, second.updated, second.downloaded) == (0, 24, {})
    assert {second.rows[(OCT08, hour)].lfda_status for hour in HOURS} == {""}


def test_blank_published_lfda_stays_blank_and_is_left_out_of_the_lfda_average():
    days = [date(2025, 5, 1), date(2025, 5, 3)]
    rows = {(day, hour): aop.Row(Decimal("20.00"), aop.REPORT, 1) for day in days for hour in HOURS}
    aop.apply_lfda(rows, aop.parse_lfda_csv(LFDA_2025, 2025, "fixture"))

    lines = aop.serialize(rows).decode().splitlines()
    assert lines[1] == "2025-05-01,1,20.00,,,report,1,Final"
    status = aop.month_status("2025-05", rows, None)
    may3 = [value for (day, _), (value, _) in _lfda_rows(LFDA_2025).items() if day == days[1]]
    assert (status.blank_lfda, status.pending_lfda) == (24, 0)
    assert abs(status.averages["lfda"] - sum(may3, Decimal(0)) / 24) < Decimal("1e-20")
    assert abs(status.averages["oemp"] - Decimal("20.00") - sum(may3, Decimal(0)) / 24) < Decimal("1e-20")


# -- monthly cross-check and the command line ----------------------------------------------------------

def test_complete_month_matching_the_published_averages_passes():
    result = aop.update_archive(_source(_month_web(AUGUST, table_values=AUGUST_TABLE)), {})

    august = next(status for status in result.months if status.month == "2026-08")
    assert august.results == {"da_ozp": "pass", "lfda": "pass", "oemp": "pass"}
    assert (august.hours, august.expected, august.sources) == (744, 744, {"report": 744})
    assert [status.results["da_ozp"] for status in result.months if status.month == "2026-07"] == [
        "not checked (no hourly DA-OZP in the archive)"]


def test_incomplete_month_is_not_checked_and_pending_lfda_leaves_only_the_da_ozp_checked():
    partial = aop.update_archive(_source(_month_web(AUGUST[:-1], table_values=AUGUST_TABLE)), {})
    pending = aop.update_archive(_source(_month_web(AUGUST, table_values=AUGUST_TABLE, lfda_days=AUGUST[:-1])), {})

    august = next(status for status in partial.months if status.month == "2026-08")
    assert set(august.results.values()) == {"not checked (incomplete: 720 of 744 hours)"}
    august = next(status for status in pending.months if status.month == "2026-08")
    assert august.results == {"da_ozp": "pass", "lfda": "not checked (LFDA not yet published for 24 hours)",
                              "oemp": "not checked (LFDA not yet published for 24 hours)"}


@pytest.mark.parametrize("mutate, table_values", [
    ((date(2026, 8, 17), 18, "20.00"), AUGUST_TABLE),
    (None, {"Aug 2026": (AUGUST_TABLE["Aug 2026"][0], str(Decimal(AUGUST_TABLE["Aug 2026"][1]) + Decimal("0.02")),
                         AUGUST_TABLE["Aug 2026"][2])}),
])
def test_month_differing_from_the_published_averages_fails_and_writes_nothing(tmp_path, capsys, mutate,
                                                                               table_values):
    output = tmp_path / "data" / "archive.csv"
    fetch = _fetch(_month_web(AUGUST, mutate=mutate, table_values=table_values))

    assert aop.main(["--output", str(output), "--no-site-api"], fetch=fetch, run_date=RUN_DATE) == 1

    assert not output.exists() and not output.parent.exists()
    assert "monthly check" in capsys.readouterr().err


def test_second_run_without_new_data_leaves_the_file_byte_identical(tmp_path, capsys):
    output = tmp_path / "archive.csv"
    log = []
    arguments = ["--output", str(output), "--no-site-api"]

    assert aop.main(arguments, fetch=_fetch(_web(), log), run_date=RUN_DATE) == 0
    first, stamp = output.read_bytes(), output.stat().st_mtime_ns
    log.clear()
    assert aop.main(arguments, fetch=_fetch(_web(), log), run_date=RUN_DATE) == 0

    assert output.read_bytes() == first and output.stat().st_mtime_ns == stamp
    assert not [url for url in log if url.endswith(".xml")]
    assert "is unchanged" in capsys.readouterr().out
    lines = first.decode("utf-8").split("\n")
    assert b"\r" not in first and lines[-1] == "" and len(lines) == 2 + 3 * 24
    assert lines[0] == "date,hour_ending,da_ozp,lfda,oemp,da_ozp_source,da_ozp_version,lfda_status"
    lfda = _lfda_rows(LFDA_OCT09)[(SEP24, 1)][0]
    da = _xml_prices(REPORTS[V3_0924])[1]
    assert f"2026-09-24,1,{da:.2f},{lfda:.2f},{da + lfda:.2f},report,3,Preliminary" in lines
    assert "2026-10-08,24,42.10,,,report,1," in lines
    assert lines[1:-1] == sorted(lines[1:-1], key=lambda line: (line[:10], int(line.split(",")[1])))


def test_dry_run_checks_everything_and_writes_nothing(tmp_path, capsys):
    output = tmp_path / "archive.csv"

    assert aop.main(["--output", str(output), "--no-site-api", "--dry-run"], fetch=_fetch(_web()),
                    run_date=RUN_DATE) == 0

    assert not output.exists()
    assert "Dry run: nothing written" in capsys.readouterr().out


def test_cli_failure_exits_1_and_leaves_the_existing_archive_untouched(tmp_path, capsys):
    output = tmp_path / "archive.csv"
    arguments = ["--output", str(output), "--no-site-api"]
    assert aop.main(arguments, fetch=_fetch(_web()), run_date=RUN_DATE) == 0
    before = output.read_bytes()
    name = PREFIX + "20261009_v1.xml"
    broken = _drop_hour(_report_xml(date(2026, 10, 9), BASE_PRICES), 24)
    pages = _web(listing=_listing([*REPORTS, name]), reports=dict(REPORTS, **{name: broken}))

    assert aop.main(arguments, fetch=_fetch(pages), run_date=RUN_DATE) == 1

    assert output.read_bytes() == before
    assert "expected hours 1-24" in capsys.readouterr().err


@pytest.mark.parametrize("change, message", [
    (lambda lines: lines[:-1], "expected hours 1-24"),
    (lambda lines: [lines[0].replace("oemp", "price")] + lines[1:], "unexpected header"),
    (lambda lines: lines[:1] + [lines[1].replace(",report,", ",web,")] + lines[2:], "da_ozp_source"),
    (lambda lines: lines[:1] + [re.sub(r"^([^,]*,[^,]*,[^,]*,[^,]*,)[^,]*", r"\g<1>1.00", lines[1])] + lines[2:],
     "is not da_ozp \\+ lfda"),
])
def test_inconsistent_existing_archive_fails_closed(change, message):
    rows = {(SEP24, hour): aop.Row(price, aop.REPORT, 3, Decimal("0.10"), "Final")
            for hour, price in _xml_prices(REPORTS[V3_0924]).items()}
    lines = aop.serialize(rows).decode().splitlines()
    assert aop.load_archive(aop.serialize(rows), "archive") == rows

    with pytest.raises(aop.MarketDataError, match=message):
        aop.load_archive(("\n".join(change(lines)) + "\n").encode(), "archive")


# -- site API gap fill ----------------------------------------------------------------------------------

REPORT_DAYS = _days(date(2026, 8, 25), date(2026, 10, 8))
MAY, JULY = _days(date(2026, 5, 1), date(2026, 5, 31)), _days(date(2026, 7, 1), date(2026, 7, 31))


def _gap_fill_web():
    names = [f"{PREFIX}{day:%Y%m%d}_v1.xml" for day in REPORT_DAYS]
    reports = {name: _report_xml(day, {hour: _price(day, hour) for hour in HOURS})
               for name, day in zip(names, REPORT_DAYS)}
    may_da = [_price(day, hour, "3") for day in MAY for hour in HOURS]
    may_lfda = [Decimal(LFDA_BASE[hour]) for _ in MAY for hour in HOURS]
    table = _table({"May 2026": (_average(may_da), _average(may_lfda),
                                 _average([da + lfda for da, lfda in zip(may_da, may_lfda)]))})
    return _web(listing=_listing(names), reports=reports, lfda_2026=_lfda_csv(MAY + JULY), table=table)


def _overlap_responses(shift_one_hour=False):
    responses = {}
    for first, last in ((date(2026, 8, 25), date(2026, 8, 31)), (date(2026, 9, 1), date(2026, 9, 30)),
                        (date(2026, 10, 1), date(2026, 10, 8))):
        responses[aop.site_api_url(first, last)] = _api_json(_days(first, last))
    if shift_one_hour:
        url = aop.site_api_url(date(2026, 9, 1), date(2026, 9, 30))
        data = json.loads(responses[url])
        assert (data["DayAhead"][6]["ReportForDate"], data["DayAhead"][6]["Hour"]) == ("2026-09-01", 7)
        data["DayAhead"][6]["Price"] = float(_price(date(2026, 9, 1), 7) + CENT)
        responses[url] = json.dumps(data)
    return responses


def test_site_api_fills_only_gap_months_matching_the_published_table():
    responses = _overlap_responses()
    responses[aop.site_api_url(MAY[0], MAY[-1])] = _api_json(MAY, shift="3")
    responses[aop.site_api_url(JULY[0], JULY[-1])] = _api_json(JULY, shift="3")
    log = []

    result = aop.update_archive(_source(_gap_fill_web()), {}, _api(responses, log))

    assert result.api.qualified and len(result.api.overlap_days) == len(REPORT_DAYS)
    assert result.api.filled == ["2026-05"]
    assert result.api.dropped["2026-07"].startswith("DA-OZP fail")
    assert {result.rows[(day, hour)].source for day in MAY for hour in HOURS} == {aop.SITE_API}
    assert {result.rows[(day, hour)].version for day in MAY for hour in HOURS} == {None}
    assert result.rows[(MAY[0], 1)].da_ozp == _price(MAY[0], 1, "3")
    assert not [key for key in result.rows if key[0].month == 7 and key[0].year == 2026]
    may = next(status for status in result.months if status.month == "2026-05")
    assert may.results == {"da_ozp": "pass", "lfda": "pass", "oemp": "pass"}
    assert len(log) == 3 + 16
    lines = aop.serialize(result.rows).decode().splitlines()
    assert lines[1].startswith("2026-05-01,1,") and lines[1].endswith(",site_api,,Final")


def test_site_api_differing_by_one_cent_on_an_overlap_day_is_not_used():
    responses = _overlap_responses(shift_one_hour=True)
    responses[aop.site_api_url(MAY[0], MAY[-1])] = _api_json(MAY, shift="3")
    log = []

    result = aop.update_archive(_source(_gap_fill_web()), {}, _api(responses, log))

    assert not result.api.qualified and len(result.api.mismatches) == 1
    assert result.api.mismatches[0].startswith("2026-09-01 hour 7: site API ")
    assert result.api.filled == [] and len(log) == 3
    assert {row.source for row in result.rows.values()} == {aop.REPORT}
