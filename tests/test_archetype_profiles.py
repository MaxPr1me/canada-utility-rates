"""pipeline/archetype_profiles.py: reading and checking the simulated BTAP runs (owner decisions 86-94, 2026-11-24).

Small BTAP folders are generated in tmp_path; the last test reads the repository's own runs once, because the
documented usage levels (data/models/usage_levels.json, methods 7S-1 and 7S-2) quote their size-band figures.
"""
import csv
import dataclasses
import re
import statistics
from datetime import datetime, timedelta

import openpyxl
import pytest

from pipeline import archetype_profiles as ap

STEP_J = 900_000.0  # 0.25 kWh in 15 minutes: a steady 1 kW


def _write_run(root, datapoint, electricity, gas=None):
    folder = root / ap.RUNS_DIR / datapoint
    folder.mkdir(parents=True)
    labels = ap._calendar()["labels"]
    with open(folder / "timestep.csv", "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(ap.CSV_HEADER)
        for name, values in ((ap.ELECTRICITY, electricity), (ap.GAS, gas)):
            for index, value in enumerate(values or []):
                writer.writerow([index, labels[index], datapoint, name, "", "J", value])


def _row(datapoint, electricity, gas=None, province="ON", fuel=None, area=100.0, **overrides):
    kwh = sum(electricity) / ap.J_PER_KWH
    peak = max(electricity) / ap.J_PER_KWH * 4
    row = {":building_type": "MediumOffice", ":template": "NECB2020", ":datapoint_id": datapoint, "status": "SUCCEEDED",
           ":epw_file": f"CAN_{province}_{'Toronto' if province == 'ON' else 'Calgary'}.Intl.AP.716240_CWEC2020.epw",
           ":primary_heating_fuel": fuel or ("NaturalGas" if gas else "Electricity"),
           "bldg_conditioned_floor_area_m_sq": area,
           "energy_eui_electricity_gj_per_m_sq": kwh * ap.J_PER_KWH / ap.J_PER_GJ / area,
           "energy_eui_natural_gas_gj_per_m_sq": sum(gas or []) / ap.J_PER_GJ / area,
           "energy_peak_electric_w_per_m_sq": peak * 1000 / area, "location_state_province_region": province,
           "unmet_hours_heating_during_occupied": 10.0, "unmet_hours_cooling_during_occupied": 5.0,
           "location_necb_climate_zone": "5"}
    row.update(overrides)
    return row


def _write_workbook(root, rows):
    path = root / ap.RESULTS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = ap.SHEET
    header = list(rows[0])
    sheet.append(header)
    for row in rows:
        sheet.append([row[column] for column in header])
    workbook.save(path)


def _step(moment):
    return int((moment - datetime(ap.YEAR, 1, 1)) / timedelta(minutes=ap.STEP_MINUTES))


def _steady(**spikes):
    values = [STEP_J] * ap.STEPS
    for moment, joules in spikes.values():
        values[_step(moment)] = joules
    return values


def test_daylight_saving_moves_only_steps_inside_its_2006_dates():
    assert ap._prevailing(datetime(2006, 3, 12, 1, 45)) == datetime(2006, 3, 12, 1, 45)
    assert ap._prevailing(datetime(2006, 3, 12, 2, 0)) == datetime(2006, 3, 12, 3, 0)
    assert ap._prevailing(datetime(2006, 11, 5, 0, 45)) == datetime(2006, 11, 5, 1, 45)
    assert ap._prevailing(datetime(2006, 11, 5, 1, 0)) == datetime(2006, 11, 5, 1, 0)


def test_the_spring_change_hour_shares_aesos_he03_bin_and_autumn_is_unchanged(tmp_path):
    # Owner decision 166 (2026-11-26): AESO labels 01:00-02:00 standard time on the spring change day HE03 (no HE02)
    # and bins it in hour 2, so the simulated hour goes there too; the true clock (_prevailing) is unchanged.
    assert ap._aeso_bin_moment(datetime(2006, 3, 12, 0, 45)) == datetime(2006, 3, 12, 0, 45)
    assert ap._aeso_bin_moment(datetime(2006, 3, 12, 1, 0)) == datetime(2006, 3, 12, 2, 0)
    assert ap._aeso_bin_moment(datetime(2006, 3, 12, 1, 45)) == datetime(2006, 3, 12, 2, 45)
    assert ap._aeso_bin_moment(datetime(2006, 3, 12, 2, 0)) == datetime(2006, 3, 12, 3, 0)
    assert ap._aeso_bin_moment(datetime(2006, 3, 5, 1, 15)) == datetime(2006, 3, 5, 1, 15)
    # Autumn: HE02 (00:00-01:00 standard) and HE02* (01:00-02:00 standard) both enter hour 1, as AESO bins them.
    autumn = [ap._aeso_bin_moment(datetime(2006, 11, 5, hour, 15)).hour for hour in (0, 1)]
    assert autumn == [1, 1]
    # A 1 kWh step at 01:15 standard time on Sunday 2006-03-12 over a steady 1 kW: eight March weekend days give hour 2
    # four steps each in Calgary, and March 12's hour 1 is empty there, as in AESO's heatmap.
    electricity = _steady(spring=(datetime(2006, 3, 12, 1, 15), 3_600_000.0))
    _write_run(tmp_path, "on-run", electricity)
    _write_run(tmp_path, "ab-run", electricity)
    _write_workbook(tmp_path, [_row("on-run", electricity), _row("ab-run", electricity, province="AB")])
    data = ap.load_archetypes(tmp_path)
    toronto, calgary = sorted(data.runs, key=lambda run: run.province, reverse=True)
    assert calgary.market_bin_kw[(3, "weekend", 2)] == pytest.approx(1 + 0.75 / 8)
    assert calgary.market_bin_kw[(3, "weekend", 1)] == pytest.approx(1.0)
    assert toronto.market_bin_kw[(3, "weekend", 1)] == pytest.approx(1 + 0.75 / 8)
    assert toronto.market_bin_kw[(3, "weekend", 2)] == pytest.approx(1.0)
    assert calgary.market_month_kwh[3] == pytest.approx(31 * 24 - 1 + 0.75)


def test_runs_are_checked_against_the_workbook_and_binned_on_each_markets_clock(tmp_path):
    # A 1 kWh step (4 kW) on Monday 2006-07-03 at 10:00 standard time: IESO bin hour 10, AESO bin hour 11 (daylight).
    spike = datetime(2006, 7, 3, 10, 0)
    electricity = _steady(peak=(spike, 3_600_000.0))
    _write_run(tmp_path, "on-run", electricity)
    _write_run(tmp_path, "ab-run", electricity, gas=[2_000_000.0] * ap.STEPS)
    _write_workbook(tmp_path, [_row("on-run", electricity),
                               _row("ab-run", electricity, gas=[2_000_000.0] * ap.STEPS, province="AB")])
    data = ap.load_archetypes(tmp_path)
    assert data.problems == () and data.workbook_rows == 2
    toronto, calgary = sorted(data.runs, key=lambda run: run.province, reverse=True)
    assert (toronto.city, calgary.city, calgary.heating_fuel) == ("Toronto", "Calgary", "NaturalGas")
    assert toronto.monthly_kwh[0] == pytest.approx(31 * 24) and toronto.monthly_kwh[6] == pytest.approx(31 * 24 + 0.75)
    assert toronto.monthly_peak_kw[6] == pytest.approx(4.0) and toronto.monthly_peak_kw[0] == pytest.approx(1.0)
    assert toronto.average_monthly_peak_kw == pytest.approx(15 / 12)
    assert toronto.kwh_per_kw == pytest.approx(toronto.annual_kwh / 12 / (15 / 12))
    assert calgary.annual_gas_gj == pytest.approx(2e-3 * ap.STEPS)
    assert len(toronto.market_bin_kw) == len(calgary.market_bin_kw) == 576
    weekdays = 21  # July 2006 has 21 weekdays, each giving four 15-minute steps to an hour bin
    assert toronto.market_bin_kw[(7, "weekday", 10)] == pytest.approx(1 + 0.75 / weekdays)
    assert toronto.market_bin_kw[(7, "weekday", 11)] == pytest.approx(1.0)
    assert calgary.market_bin_kw[(7, "weekday", 11)] == pytest.approx(1 + 0.75 / weekdays)
    assert calgary.market_bin_kw[(7, "weekday", 10)] == pytest.approx(1.0)
    # A steady load: daylight saving moves March's last hour into April and October's last hour into November.
    assert toronto.market_month_kwh[3] == pytest.approx(31 * 24)
    assert calgary.market_month_kwh[3] == pytest.approx(31 * 24 - 1)
    assert calgary.market_month_kwh[11] == pytest.approx(30 * 24 + 1)
    assert sum(calgary.market_month_kwh.values()) == pytest.approx(calgary.annual_kwh)


def test_a_run_that_disagrees_with_the_workbook_is_left_out_with_its_reason(tmp_path):
    electricity = _steady()
    for name in ("good", "off", "gas-missing", "broken"):
        if name != "broken":
            _write_run(tmp_path, name, electricity)
    rows = [_row("good", electricity), _row("off", electricity), _row("gas-missing", electricity, fuel="NaturalGas"),
            _row("broken", electricity), _row("good", electricity)]
    rows[1]["energy_eui_electricity_gj_per_m_sq"] *= 1.01
    _write_workbook(tmp_path, rows)
    data = ap.load_archetypes(tmp_path)
    assert [run.datapoint_id for run in data.runs] == ["good"]
    reasons = "\n".join(data.problems)
    assert "(off): electricity" in reasons and "differs from output.xlsx" in reasons
    assert "(gas-missing): gas meter missing for NaturalGas heating" in reasons
    assert "(broken):" in reasons and "(good): duplicate datapoint id" in reasons and len(data.problems) == 4


def test_a_broken_timestep_file_names_its_first_bad_line(tmp_path):
    values = _steady()
    _write_run(tmp_path, "gap", values)
    path = tmp_path / ap.RUNS_DIR / "gap" / "timestep.csv"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    del lines[101]
    path.write_text("".join(lines), encoding="utf-8")
    with pytest.raises(ValueError, match=r"line 102: step 101 '2006-01-02 01:15' is not the expected 15-minute step 100"):
        ap.read_timestep(path, "gap")
    _write_run(tmp_path, "text", values)
    path = tmp_path / ap.RUNS_DIR / "text" / "timestep.csv"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    lines[5] = lines[5].replace("900000.0", "n/a")
    path.write_text("".join(lines), encoding="utf-8")
    with pytest.raises(ValueError, match=r"line 6: value 'n/a' is negative or not finite"):
        ap.read_timestep(path, "text")


def test_a_missing_or_malformed_workbook_raises(tmp_path):
    with pytest.raises(ap.ArchetypeDataError, match="unreadable"):
        ap.read_workbook(tmp_path / "missing.xlsx")
    _write_workbook(tmp_path, [{":building_type": "Warehouse"}])
    with pytest.raises(ap.ArchetypeDataError, match="lacks columns"):
        ap.read_workbook(tmp_path / ap.RESULTS_FILE)


def test_size_bands_use_the_average_monthly_peak_with_the_lower_limit_included(tmp_path):
    electricity = _steady()
    _write_run(tmp_path, "one-kw", electricity)
    _write_workbook(tmp_path, [_row("one-kw", electricity)])
    data = ap.load_archetypes(tmp_path)
    assert [run.datapoint_id for run in ap.runs_in_band(data, "ON", 1.0, 2.0)] == ["one-kw"]
    assert ap.runs_in_band(data, "ON", 0.0, 1.0) == [] and ap.runs_in_band(data, "AB", 0.0, None) == []
    assert ap.runs_in_band(data, "ON", 0.5, None)


def test_the_fingerprint_follows_the_values_used_and_not_the_run_order(tmp_path):
    electricity = _steady()
    for name in ("a-run", "b-run"):
        _write_run(tmp_path, name, electricity)
    _write_workbook(tmp_path, [_row("a-run", electricity), _row("b-run", electricity)])
    data = ap.load_archetypes(tmp_path)
    fingerprint = ap.archetype_fingerprint(data)
    assert re.fullmatch(r"[0-9a-f]{64}", fingerprint)
    assert ap.archetype_fingerprint(dataclasses.replace(data, runs=tuple(reversed(data.runs)))) == fingerprint
    bins = dict(data.runs[0].market_bin_kw)
    bins[(1, "weekday", 12)] += 0.5
    changed = dataclasses.replace(data, runs=(dataclasses.replace(data.runs[0], market_bin_kw=bins), data.runs[1]))
    assert ap.archetype_fingerprint(changed) != fingerprint


def test_the_repository_runs_all_validate_and_match_the_documented_size_band_figures():
    data = ap.load_archetypes()
    assert data.problems == () and len(data.runs) == data.workbook_rows == 68
    for (low, high), count, median in (((50, 500), 41, 259.9), ((500, 5000), 10, 255.9)):
        runs = ap.runs_in_band(data, "ON", low, high) + ap.runs_in_band(data, "AB", low, high)
        assert len(runs) == count
        assert round(statistics.median(run.kwh_per_kw for run in runs), 1) == median
