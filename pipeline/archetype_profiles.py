"""Simulated building archetypes: read, validate and summarize the owner's BTAP runs.

The owner simulated NECB 2020 archetype buildings with NRCan's Building Technology Assessment Platform (BTAP; OpenStudio
3.11 and EnergyPlus): 17 building types, each in Toronto and Calgary (CWEC 2020 typical weather) with electric or natural
gas space heating, 68 runs (owner decisions 86, 87 and 93 of 2026-11-24 brought them into the repository unchanged).
``data/btap/NECB2020_Default/NECB2020_Default/`` holds ``results/output.xlsx`` (one row per run: building type, weather
file, heating fuel, floor area, energy use intensities, peak demand, unmet hours and the run's ``:datapoint_id``) and
``parametric/runs/<datapoint_id>/timestep.csv`` (whole-building Electricity:Facility, then NaturalGas:Facility for
gas-heated runs, in joules per 15-minute step). These are simulated buildings, never metered customers: anything priced
from them is labelled simulated or estimated and never counts as live coverage (AGENTS.md safeguard 8).

Time convention (owner decision 94): each Timestep label is the start of a 15-minute interval in local standard time on
the 2006 calendar (January 1 is a Sunday). The simulated schedules observe neither holidays nor daylight saving. Market
bins follow each market's own clock (market-data rules): the IESO heatmap is in Eastern Standard Time, so Toronto steps
are not shifted; the AESO heatmap is in Alberta's prevailing local time, so Calgary steps inside daylight saving move one
hour later (today's rule on the 2006 calendar: from the second Sunday of March at 02:00 standard time to the first Sunday
of November at 01:00 standard time). Both heatmaps count holidays as the weekday they fall on, and so do the bins here.
One known difference, one hour a year: AESO labels the hour before the spring change (01:00-02:00 standard time) HE03
and its heatmap files it in hour 2 (HE-1), while decision 94 leaves that hour unshifted in hour 1 here. The autumn
repeated hour (HE02 and HE02*) matches. The difference is open with the owner, not corrected silently.

Failure behaviour: a missing or unreadable results workbook, or one without the expected columns, raises
``ArchetypeDataError``; a run that fails any check is left out with its reason in ``ArchetypeSet.problems``.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BTAP_ROOT = PROJECT_ROOT / "data" / "btap" / "NECB2020_Default" / "NECB2020_Default"
RESULTS_FILE = Path("results") / "output.xlsx"
RUNS_DIR = Path("parametric") / "runs"
SHEET = "btap_data"
CSV_HEADER = ["Index", "Timestep", "datapoint_id", "Name", "KeyValue", "Units", "Value"]
ELECTRICITY, GAS = "Electricity:Facility", "NaturalGas:Facility"
YEAR, STEP_MINUTES, STEPS = 2006, 15, 35040
J_PER_KWH, J_PER_GJ = 3.6e6, 1e9
# The 68 runs agreed with output.xlsx to 0.0085% (electricity), 0.0028% (gas) and 0.00005% (peak) when checked on
# 2026-11-25; a larger gap means the CSV and the workbook do not describe the same simulation.
TOTAL_TOLERANCE = 0.001
# Owner decision 91 (2026-11-24): a run is flagged when its occupied unmet hours (heating plus cooling) exceed 300, the
# usual NECB and ASHRAE 90.1 simulation-quality limit.
UNMET_FLAG_HOURS = 300.0
DAY_TYPES = ("weekday", "weekend")
# Market clock per province (market-data rules): "standard" = the simulation's own local standard time (IESO bins are
# EST); "prevailing" = local time with daylight saving (AESO bins).
MARKET_CLOCKS = {"ON": "standard", "AB": "prevailing"}
HEATING_FUELS = ("Electricity", "NaturalGas")

COLUMNS = {
    "building_type": ":building_type", "template": ":template", "weather_file": ":epw_file",
    "heating_fuel": ":primary_heating_fuel", "datapoint_id": ":datapoint_id", "status": "status",
    "floor_area_m2": "bldg_conditioned_floor_area_m_sq",
    "eui_electricity_gj_m2": "energy_eui_electricity_gj_per_m_sq",
    "eui_gas_gj_m2": "energy_eui_natural_gas_gj_per_m_sq",
    "peak_electric_w_m2": "energy_peak_electric_w_per_m_sq",
    "province": "location_state_province_region",
    "unmet_heating_occupied": "unmet_hours_heating_during_occupied",
    "unmet_cooling_occupied": "unmet_hours_cooling_during_occupied",
    "climate_zone": "location_necb_climate_zone",
}


class ArchetypeDataError(ValueError):
    """The BTAP results workbook is missing, unreadable or not in the expected shape."""


@dataclass(frozen=True)
class ArchetypeRun:
    """One validated simulation run; kWh and kW are whole-building electricity, gas in GJ."""

    datapoint_id: str
    building_type: str
    heating_fuel: str
    province: str
    city: str
    weather_file: str
    climate_zone: Optional[str]
    floor_area_m2: float
    unmet_heating_occupied: float
    unmet_cooling_occupied: float
    monthly_kwh: tuple[float, ...]
    monthly_peak_kw: tuple[float, ...]
    monthly_gas_gj: tuple[float, ...]
    # On the province's market clock (empty when the province has no market clock): the average kW in each bin
    # (calendar month 1-12, "weekday"/"weekend", hour beginning 0-23) and the kWh in each calendar month.
    market_bin_kw: dict = field(default_factory=dict, compare=False, repr=False)
    market_month_kwh: dict = field(default_factory=dict, compare=False, repr=False)

    @property
    def annual_kwh(self) -> float:
        return math.fsum(self.monthly_kwh)

    @property
    def annual_gas_gj(self) -> float:
        return math.fsum(self.monthly_gas_gj)

    @property
    def average_monthly_kwh(self) -> float:
        return self.annual_kwh / 12

    @property
    def average_monthly_peak_kw(self) -> float:
        """Mean of the 12 monthly highest 15-minute demands: Toronto Hydro's "monthly average peak demand", the
        class measure of owner decision 100."""
        return math.fsum(self.monthly_peak_kw) / 12

    @property
    def max_peak_kw(self) -> float:
        return max(self.monthly_peak_kw)

    @property
    def kwh_per_kw(self) -> float:
        """Average monthly kWh per kW of average monthly peak (x 100 gives the kWh of a 100 kW customer)."""
        return self.average_monthly_kwh / self.average_monthly_peak_kw

    @property
    def unmet_occupied_hours(self) -> float:
        return self.unmet_heating_occupied + self.unmet_cooling_occupied

    @property
    def quality_flag(self) -> bool:
        return self.unmet_occupied_hours > UNMET_FLAG_HOURS


@dataclass(frozen=True)
class ArchetypeSet:
    """Validated runs plus the reasons any run was left out."""

    root: str
    runs: tuple[ArchetypeRun, ...]
    problems: tuple[str, ...]
    workbook_rows: int


def _step_starts() -> list[datetime]:
    start = datetime(YEAR, 1, 1)
    return [start + timedelta(minutes=STEP_MINUTES * index) for index in range(STEPS)]


def _nth_sunday(month: int, nth: int) -> datetime:
    day = datetime(YEAR, month, 1)
    day += timedelta(days=(6 - day.weekday()) % 7)
    return day + timedelta(days=7 * (nth - 1))


def _prevailing(moment: datetime) -> datetime:
    """Local prevailing time of a local-standard-time moment, with today's daylight saving rule on the 2006 calendar."""
    begins = _nth_sunday(3, 2) + timedelta(hours=2)    # 02:00 standard time becomes 03:00 daylight time
    ends = _nth_sunday(11, 1) + timedelta(hours=1)     # 02:00 daylight time = 01:00 standard time
    return moment + timedelta(hours=1) if begins <= moment < ends else moment


@lru_cache(maxsize=1)
def _calendar() -> dict:
    """Per-step labels, calendar months and market-bin keys, shared by every run (all use the 2006 calendar)."""
    starts = _step_starts()
    labels = [moment.strftime("%Y-%m-%d %H:%M") for moment in starts]
    months = [moment.month for moment in starts]

    def key(moment: datetime) -> tuple[int, str, int]:
        return moment.month, DAY_TYPES[1] if moment.weekday() >= 5 else DAY_TYPES[0], moment.hour

    bins = {"standard": [key(moment) for moment in starts],
            "prevailing": [key(_prevailing(moment)) for moment in starts]}
    return {"labels": labels, "months": months, "bins": bins}


def _number(value) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _within(value: float, reference: float) -> bool:
    return abs(value - reference) <= TOTAL_TOLERANCE * max(abs(reference), 1e-9)


def read_workbook(path: Path) -> list[dict]:
    """The results workbook's rows as dicts of the columns this module uses (fail closed on shape)."""
    try:
        import openpyxl

        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as exc:  # missing file, not an xlsx, unreadable
        raise ArchetypeDataError(f"BTAP results workbook {path} unreadable ({type(exc).__name__}: {exc})") from exc
    try:
        if SHEET not in workbook.sheetnames:
            raise ArchetypeDataError(f"BTAP results workbook {path.name} has no {SHEET!r} sheet")
        rows = workbook[SHEET].iter_rows(values_only=True)
        header = next(rows, None) or ()
        index = {name: position for position, name in enumerate(header) if name}
        missing = [column for column in COLUMNS.values() if column not in index]
        if missing:
            raise ArchetypeDataError(f"BTAP results workbook {path.name} lacks columns {missing}")
        out = [{key: row[index[column]] for key, column in COLUMNS.items()} for row in rows if any(v is not None for v in row)]
    finally:
        workbook.close()
    if not out:
        raise ArchetypeDataError(f"BTAP results workbook {path.name} has no runs")
    return out


def read_timestep(path: Path, datapoint_id: str) -> dict[str, list[float]]:
    """Joules per step for each meter in a run's timestep.csv; raises ValueError naming the first broken line.

    The only valid layout is electricity's 35,040 steps, then gas's for a gas-heated run. Rows are checked as they
    are read: building row lists or columns first costs more than the checks themselves.
    """
    labels = _calendar()["labels"]
    series: dict[str, list[float]] = {}
    order: list[str] = []
    line = 1
    try:
        with open(path, newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            if next(reader, None) != CSV_HEADER:
                raise ValueError("unexpected header")
            for line, row in enumerate(reader, start=2):
                if len(row) != 7:
                    raise ValueError(f"line {line}: {len(row)} fields")
                index, label, run_id, name, key_value, unit, value = row
                if name not in (ELECTRICITY, GAS) or key_value or unit != "J" or run_id != datapoint_id:
                    raise ValueError(f"line {line}: unexpected meter, key, unit or datapoint ({name}, {key_value!r}, "
                                     f"{unit}, {run_id})")
                values = series.get(name)
                if values is None:
                    if order and len(series[order[-1]]) != STEPS:
                        raise ValueError(f"line {line}: {name} starts before the previous meter has {STEPS} steps")
                    values = series[name] = []
                    order.append(name)
                elif order[-1] != name:
                    raise ValueError(f"line {line}: {name} rows are not contiguous")
                step = len(values)
                if step >= STEPS or index != str(step) or label != labels[step]:
                    raise ValueError(f"line {line}: step {index} {label!r} is not the expected 15-minute step "
                                     f"{step} ({labels[step] if step < STEPS else 'past the year end'})")
                try:
                    joules = float(value)
                except ValueError:
                    joules = math.nan
                if not math.isfinite(joules) or joules < 0:
                    raise ValueError(f"line {line}: value {value!r} is negative or not finite")
                values.append(joules)
    except csv.Error as exc:
        raise ValueError(f"line {line + 1}: unreadable CSV ({exc})") from exc
    if order[:1] != [ELECTRICITY] or any(len(values) != STEPS for values in series.values()):
        raise ValueError(f"needs {ELECTRICITY} first and {STEPS} steps per meter "
                         f"(found {', '.join(f'{name} {len(series[name])}' for name in order) or 'nothing'})")
    return series

def _run(row: dict, root: Path) -> ArchetypeRun:
    datapoint = row["datapoint_id"]
    if not isinstance(datapoint, str) or not datapoint or Path(datapoint).name != datapoint:
        raise ValueError(f"invalid datapoint id {datapoint!r}")
    if row["status"] != "SUCCEEDED":
        raise ValueError(f"status {row['status']!r}")
    if row["template"] != "NECB2020":
        raise ValueError(f"template {row['template']!r} is not NECB2020")
    if row["heating_fuel"] not in HEATING_FUELS:
        raise ValueError(f"heating fuel {row['heating_fuel']!r}")
    weather, province = row["weather_file"], row["province"]
    if not (isinstance(weather, str) and isinstance(province, str) and weather.startswith(f"CAN_{province}_")):
        raise ValueError(f"weather file {weather!r} does not name province {province!r}")
    # The city named in the weather file (owner decision 89): Toronto's station is at Pearson, in Mississauga.
    city = weather.split("_")[2].split(".")[0]
    numbers = {key: _number(row[key]) for key in ("floor_area_m2", "eui_electricity_gj_m2", "eui_gas_gj_m2",
                                                  "peak_electric_w_m2", "unmet_heating_occupied",
                                                  "unmet_cooling_occupied")}
    if any(value is None or value < 0 for value in numbers.values()) or not numbers["floor_area_m2"]:
        raise ValueError("floor area, energy use intensity, peak or unmet hours missing or negative")
    series = read_timestep(root / RUNS_DIR / datapoint / "timestep.csv", datapoint)
    if (GAS in series) != (row["heating_fuel"] == "NaturalGas"):
        raise ValueError(f"gas meter {'present' if GAS in series else 'missing'} for {row['heating_fuel']} heating")
    area = numbers["floor_area_m2"]
    electricity = series[ELECTRICITY]
    calendar = _calendar()
    monthly_kwh, monthly_peak, monthly_gas = [0.0] * 12, [0.0] * 12, [0.0] * 12
    buckets: dict[int, list[float]] = {month: [] for month in range(1, 13)}
    for month, joules in zip(calendar["months"], electricity):
        buckets[month].append(joules)
    for month, values in buckets.items():
        monthly_kwh[month - 1] = math.fsum(values) / J_PER_KWH
        monthly_peak[month - 1] = max(values) / J_PER_KWH * (60 / STEP_MINUTES)
    if GAS in series:
        gas_buckets: dict[int, list[float]] = {month: [] for month in range(1, 13)}
        for month, joules in zip(calendar["months"], series[GAS]):
            gas_buckets[month].append(joules)
        monthly_gas = [math.fsum(gas_buckets[month]) / J_PER_GJ for month in range(1, 13)]
    annual_kwh, annual_gas = math.fsum(monthly_kwh), math.fsum(monthly_gas)
    expected_kwh = numbers["eui_electricity_gj_m2"] * area * J_PER_GJ / J_PER_KWH
    expected_gas = numbers["eui_gas_gj_m2"] * area
    expected_peak = numbers["peak_electric_w_m2"] * area / 1000
    if not _within(annual_kwh, expected_kwh):
        raise ValueError(f"electricity {annual_kwh:,.1f} kWh differs from output.xlsx {expected_kwh:,.1f} kWh")
    if not _within(annual_gas, expected_gas):
        raise ValueError(f"gas {annual_gas:,.3f} GJ differs from output.xlsx {expected_gas:,.3f} GJ")
    if not _within(max(monthly_peak), expected_peak):
        raise ValueError(f"peak {max(monthly_peak):,.2f} kW differs from output.xlsx {expected_peak:,.2f} kW")
    bin_kw: dict[tuple[int, str, int], float] = {}
    month_kwh: dict[int, float] = {}
    clock = MARKET_CLOCKS.get(province)
    if clock:
        parts: dict[tuple[int, str, int], list[float]] = {}
        for key, joules in zip(calendar["bins"][clock], electricity):
            parts.setdefault(key, []).append(joules)
        if len(parts) != 12 * len(DAY_TYPES) * 24:
            raise ValueError(f"{len(parts)} market bins on the {clock} clock, expected {12 * len(DAY_TYPES) * 24}")
        step_hours = STEP_MINUTES / 60
        bin_kw = {key: math.fsum(values) / J_PER_KWH / (len(values) * step_hours) for key, values in parts.items()}
        by_month: dict[int, list[float]] = {}
        for key, values in parts.items():
            by_month.setdefault(key[0], []).append(math.fsum(values) / J_PER_KWH)
        month_kwh = {month: math.fsum(values) for month, values in sorted(by_month.items())}
    return ArchetypeRun(
        datapoint_id=datapoint, building_type=str(row["building_type"]), heating_fuel=row["heating_fuel"],
        province=province, city=city, weather_file=weather,
        climate_zone=str(row["climate_zone"]) if row["climate_zone"] is not None else None,
        floor_area_m2=area, unmet_heating_occupied=numbers["unmet_heating_occupied"],
        unmet_cooling_occupied=numbers["unmet_cooling_occupied"], monthly_kwh=tuple(monthly_kwh),
        monthly_peak_kw=tuple(monthly_peak), monthly_gas_gj=tuple(monthly_gas), market_bin_kw=bin_kw,
        market_month_kwh=month_kwh)


@lru_cache(maxsize=4)
def _load(root: str) -> ArchetypeSet:
    base = Path(root)
    rows = read_workbook(base / RESULTS_FILE)
    runs, problems, seen = [], [], set()
    for row in rows:
        datapoint = row.get("datapoint_id")
        label = f"{row.get('building_type')} / {row.get('weather_file')} / {row.get('heating_fuel')} ({datapoint})"
        if datapoint in seen:
            problems.append(f"{label}: duplicate datapoint id")
            continue
        seen.add(datapoint)
        try:
            runs.append(_run(row, base))
        except (OSError, ValueError) as exc:
            problems.append(f"{label}: {exc}")
    return ArchetypeSet(root=str(base), runs=tuple(runs), problems=tuple(problems), workbook_rows=len(rows))


def load_archetypes(root: Path | str | None = None) -> ArchetypeSet:
    """All validated runs under ``root`` (default the repository's BTAP folder); cached per folder for one process."""
    return _load(str(Path(root or BTAP_ROOT).resolve()))


def runs_in_band(archetypes: ArchetypeSet, province: str, min_kw: float, max_kw: Optional[float]) -> list[ArchetypeRun]:
    """Runs simulated in ``province`` whose average monthly peak is in [min_kw, max_kw) (no upper limit when None)."""
    return [run for run in archetypes.runs if run.province == province and run.average_monthly_peak_kw >= min_kw
            and (max_kw is None or run.average_monthly_peak_kw < max_kw)]


def archetype_fingerprint(archetypes: ArchetypeSet) -> str:
    """SHA-256 of every value the models read from the validated runs (identity, size, monthly use and peaks, market
    bins), so model monitoring sees a changed simulation as a changed input (method 7S-2). Values are rounded to six
    decimals and the runs sorted by datapoint id: the same data gives the same fingerprint on any machine."""
    def number(value: float) -> float:
        return round(float(value), 6)

    rows = [{"datapoint_id": run.datapoint_id, "building_type": run.building_type, "heating_fuel": run.heating_fuel,
             "province": run.province, "city": run.city, "floor_area_m2": number(run.floor_area_m2),
             "unmet_occupied_hours": number(run.unmet_occupied_hours),
             "monthly_kwh": [number(value) for value in run.monthly_kwh],
             "monthly_peak_kw": [number(value) for value in run.monthly_peak_kw],
             "market_bin_kw": [[month, kind, hour, number(kw)]
                               for (month, kind, hour), kw in sorted(run.market_bin_kw.items())],
             "market_month_kwh": [[month, number(kwh)] for month, kwh in sorted(run.market_month_kwh.items())]}
            for run in sorted(archetypes.runs, key=lambda run: run.datapoint_id)]
    text = json.dumps({"runs": rows, "left_out": len(archetypes.problems)}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
