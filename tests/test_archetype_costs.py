"""pipeline/archetype_costs.py: simulated building archetype costs (method AC-1; owner decisions 86-114 and 166-167).

Records come from tests/fixtures/archetype_records.json (frozen live records of 2026-11-26 plus a test-only RoLR-MC
copy), runs are built in memory except in the last test, and market histories are flat synthetic files, so a test's
numbers never depend on the month's scrape or market.
"""
import copy
import json
import math
from datetime import date, datetime
from pathlib import Path

import pytest

from pipeline import archetype_costs as ac
from pipeline import archetype_profiles as ap
from pipeline import representative_models as rm
from scrapers.utils.market_pricing import ALBERTA_METHOD, ROLLING_METHOD

FIXTURE = Path(__file__).parent / "fixtures" / "archetype_records.json"
AS_OF = "2026-11-26"
CONFIG = ac.load_config()
SPARK = ac.load_json(ac.SPARK_GAP_CONFIG_PATH)
SHAPE_KEYS = [(month, kind, hour) for month in range(1, 13) for kind in ("weekday", "weekend") for hour in range(24)]
TOU = "Toronto Hydro-Electric System Ltd."


def _records():
    return copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8"))["records"])


def _market(province, energy, ga=None):
    """A flat 60-month history ending October 2026: every bin and month at ``energy`` (+ ``ga`` Class B GA)."""
    months = [f"{2021 + (10 + i) // 12:04d}-{(10 + i) % 12 + 1:02d}" for i in range(60)]
    monthly = [{"month": m, "energy_arithmetic": energy, **({"ga_class_b": ga} if ga is not None else {})}
               for m in months]
    surface = [{"month": m, "day_type": kind, "hour": hour, "hours_count": 20, "avg_energy_price": energy}
               for m, kind, hour in SHAPE_KEYS]
    method = ROLLING_METHOD if province == "ON" else ALBERTA_METHOD
    return {"metadata": {"derivation_method": method, "window": {"start_month": months[0], "end_month": months[-1],
                                                                 "months": 60}},
            "monthly": monthly, "hourly_surface": surface}


MARKETS = {"ON": _market("ON", 0.05, 0.06), "AB": _market("AB", 0.08)}


def _run(city="Toronto", building="MediumOffice", fuel="Electricity", kwh_per_hour=10.0, hourly=None, peaks=None,
         gas_gj=None, area=1000.0, name=None):
    hourly = list(hourly) if hourly is not None else [kwh_per_hour] * ap.HOURS
    monthly = [0.0] * 12
    for (month, _), kwh in zip(ap.hour_calendar(), hourly):
        monthly[month - 1] += kwh
    province = "ON" if city == "Toronto" else "AB"
    flat = sum(hourly) / len(hourly)
    return ap.ArchetypeRun(
        datapoint_id=name or f"{city}-{building}-{fuel}", building_type=building, heating_fuel=fuel, province=province,
        city=city, weather_file=f"CAN_{province}_{city}.epw", climate_zone="6", floor_area_m2=area,
        unmet_heating_occupied=0.0, unmet_cooling_occupied=0.0, monthly_kwh=tuple(monthly),
        monthly_peak_kw=tuple(peaks or [kwh_per_hour * 1.2] * 12), monthly_gas_gj=tuple(gas_gj or [0.0] * 12),
        market_bin_kw={key: flat for key in SHAPE_KEYS}, market_month_kwh={m: monthly[m - 1] for m in range(1, 13)},
        hourly_kwh=tuple(hourly))


def _build(runs, records=None, as_of=AS_OF, markets=MARKETS, config=CONFIG):
    archetypes = ap.ArchetypeSet(root="memory", runs=tuple(runs), problems=(), workbook_rows=len(runs))
    return ac.build_archetype_costs(records if records is not None else _records(), rm.load_crosswalk(),
                                    rm.load_usage_levels(), rm.load_taxes(), config, SPARK, as_of=as_of,
                                    market_documents=markets, archetypes=archetypes)


def _entry(result, run_id):
    return next(run for run in result["runs"] if run["id"] == run_id)


def _charge(fuel, pattern):
    found = [c for c in fuel["charges"] if pattern in c["component"]]
    assert len(found) == 1, (pattern, [c["component"] for c in fuel["charges"]])
    return found[0]


def test_the_reviewed_inputs_are_valid_and_problems_fail_closed():
    assert ac.config_problems(CONFIG) == [] and ac.stale_reviews(CONFIG, date(2026, 11, 26)) == []
    assert ac.stale_reviews(CONFIG, date(2028, 1, 1))
    broken = copy.deepcopy(CONFIG)
    broken["apartments"]["building_types"]["LowriseApartment"]["dwelling_units"] = 6
    broken["clock_periods"]["ON_TOU"]["seasons"]["winter"] = [12, 1, 2, 3, 4]
    broken["clock_periods"]["ON_TOU"]["weekday_hours"]["summer"]["mid-peak"] = [[10, 12]]
    broken["holidays"]["OEB_TOU"]["rules"].append({"name": "Lunar", "kind": "lunar"})
    broken["demand"]["ratchets"][0]["fraction"] = 0.8  # the reviewed stored wording still says 90%
    problems = " | ".join(ac.config_problems(broken))
    for text in ("dwelling_units must be an integer above 6", "cover each month exactly once", "periods overlap",
                 "unknown holiday rule kind", "invalid demand ratchet"):
        assert text in problems, text
    with pytest.raises(ValueError):
        _build([_run()], config=broken)


def test_an_oeb_bill_calculator_month_is_reproduced_to_the_cent():
    # Owner decision 99: the OEB calculator (Toronto Hydro GS < 50 kW, 2,500 kWh time-of-use, 64/18/18 split) gives
    # $526.47: energy, per-kWh transmission and regulatory charges on kWh x 1.0295; distribution and riders metered.
    records = _records()
    tou = next(r for r in records if r["tariff_code"] == "GS-TOU-S")
    energy = [c for c in tou["components"] if c["component_type"] == "energy" and c["tou_period"]]

    def charge(kind, name, value, unit):
        return {"component_type": kind, "component_name": name, "charge_value": value, "charge_unit": unit}

    tou["components"] = energy + [
        charge("fixed", "Service Charge", 44.11, "$/30 days"),
        charge("distribution", "Distribution Volumetric Rate", 0.04778, "$/kWh"),
        charge("rider", "Rate Rider total", 0.00168, "$/kWh"),
        charge("transmission", "Retail Transmission Rate - Network Service Rate", 0.0131, "$/kWh"),
        charge("transmission", "Retail Transmission Rate - Line and Transformation Connection Service Rate",
               0.00801, "$/kWh"),
        charge("regulatory", "Wholesale Market Service Rate", 0.0047, "$/kWh"),
        charge("regulatory", "Rural or Remote Electricity Rate Protection Charge", 0.0006, "$/kWh"),
        charge("regulatory", "Standard Supply Service - Administrative Charge", 0.25, "$/30 days")]
    labels = ac.clock_labels(CONFIG["clock_periods"]["ON_TOU"], CONFIG["holidays"]["OEB_TOU"])
    targets = {"off-peak": 1600.0, "mid-peak": 450.0, "on-peak": 450.0}
    september = [(i, label) for i, ((month, _), label) in enumerate(zip(ap.hour_calendar(), labels)) if month == 9]
    counts = {period: sum(1 for _, label in september if label == period) for period in targets}
    hourly = [1.0] * ap.HOURS
    for index, label in september:
        hourly[index] = targets[label] / counts[label]
    result = _build([_run(hourly=hourly, peaks=[30.0] * 12, name="calc")], records=records)
    electricity = _entry(result, "calc")["electricity"]
    assert electricity["class"]["code"] == "GS-TOU-S" and electricity["supply"]["kind"] == "rpp_tou"
    month = electricity["months"][8]
    assert month["days"] == 30 and month["volume"] == pytest.approx(2500.0)
    assert month["without_tax"] == pytest.approx(541.08, abs=0.005)
    assert month["with_tax"] == pytest.approx(526.47, abs=0.005)
    assert [line["name"] for line in electricity["annual"]["tax_lines"]] == ["HST", "Ontario Electricity Rebate (OER)"]


def test_enmax_classes_follow_the_tests_with_ratchet_rate_of_last_resort_and_on_peak_holidays():
    big = _run("Calgary", "Hospital", kwh_per_hour=40.0, peaks=[200.0, 200.0] + [100.0] * 10, name="d310")
    medium = _run("Calgary", "Warehouse", kwh_per_hour=10.0, peaks=[100.0] * 12, name="d300")
    small = _run("Calgary", "SmallOffice", kwh_per_hour=5.0, peaks=[30.0] * 12, name="d200")
    result = _build([big, medium, small])
    d310 = _entry(result, "d310")["electricity"]
    assert (d310["class"]["code"], d310["supply"]["kind"], d310["supply"]["estimated"]) == ("D310", "pool", True)
    july = d310["months"][6]
    assert (july["metered_kw"], july["billing_kw"]) == (100.0, 180.0)  # 90% of the 200 kW (222 kVA) peak
    facilities = _charge(d310, "Facilities Charge")
    non_ratcheted = _charge(d310, "Non-Ratcheted Demand Charge")
    peak_days, other_days = 31 + 28, 365 - 31 - 28  # January and February at 200 kW, the other months at 100 kW
    assert facilities["annual"] == pytest.approx(0.154031 / 0.9 * (200 * peak_days + 180 * other_days), abs=0.01)
    assert non_ratcheted["annual"] == pytest.approx(0.050674 / 0.9 * (200 * peak_days + 100 * other_days), abs=0.01)
    labels = ac.clock_labels(CONFIG["clock_periods"]["ENMAX_ON_PEAK"], CONFIG["holidays"]["AB_GENERAL"])
    on_hours = sum(1 for label in labels if label == "on-peak")
    assert _charge(d310, "On Peak")["annual"] == pytest.approx(0.012021 * 40 * on_hours, abs=0.01)
    by_clock = {clock: label for (_, clock), label in zip(ap.hour_calendar(), labels)}
    assert by_clock[datetime(2006, 4, 14, 10)] == "off-peak"  # Good Friday, an Alberta general holiday
    assert by_clock[datetime(2006, 7, 4, 9)] == "on-peak"    # 08:00 standard time is 09:00 on the summer clock
    assert by_clock[datetime(2006, 12, 26, 10)] == "on-peak"  # Boxing Day is not an Alberta general holiday
    assert d310["estimated_energy"]["price_per_kwh"] == pytest.approx(0.08)
    assert d310["annual"]["groups"]["energy"] == pytest.approx(0.08 * 40 * ap.HOURS, abs=0.01)
    d300 = _entry(result, "d300")["electricity"]
    assert (d300["class"]["code"], d300["supply"]["kind"]) == ("D300", "rate_of_last_resort")
    assert _charge(d300, "RoLR Energy Charge")["annual"] == pytest.approx(0.1206 * 10 * ap.HOURS, abs=0.01)
    d200 = _entry(result, "d200")["electricity"]
    assert (d200["class"]["code"], d200["supply"]["kind"]) == ("D200", "rate_of_last_resort")
    assert [line["name"] for line in d200["annual"]["tax_lines"]] == ["GST"]


def test_ontario_supply_rebate_and_apartment_class_follow_the_regulations():
    runs = [_run(kwh_per_hour=36.0, peaks=[120.0] * 12, name="market"),
            _run(kwh_per_hour=27.0, peaks=[120.0] * 12, name="rpp-annual"),
            _run(building="MidriseApartment", kwh_per_hour=115.0, peaks=[300.0] * 12, name="apartment"),
            _run(building="LargeHotel", kwh_per_hour=115.0, peaks=[300.0] * 12, name="hotel"),
            _run(building="LowriseApartment", kwh_per_hour=12.0, peaks=[30.0] * 12, name="lowrise")]
    result = _build(runs)
    market = _entry(result, "market")["electricity"]
    assert (market["class"]["code"], market["supply"]["kind"]) == ("GS 50-999 kW", "market")
    assert market["loss_factor"] == 1.0295
    assert market["annual"]["groups"]["energy"] == pytest.approx(0.11 * 36 * ap.HOURS * 1.0295, abs=0.01)
    assert _charge(market, "Global Adjustment Account")["annual"] > 0
    assert [t["name"] for t in market["tax_not_applied"]] == ["Ontario Electricity Rebate (OER)"]
    rpp = _entry(result, "rpp-annual")["electricity"]
    assert rpp["supply"]["kind"] == "rpp_tou" and "250,000 or less" in rpp["supply"]["reason"]
    assert {c["tou_period"] for c in rpp["charges"] if c["bucket"] == "energy"} == {"on-peak", "mid-peak", "off-peak"}
    assert not any("Global Adjustment Account" in c["component"] for c in rpp["charges"])
    assert any(line["kind"] == "rebate" for line in rpp["annual"]["tax_lines"])
    apartment = _entry(result, "apartment")["electricity"]
    assert apartment["supply"]["kind"] == "rpp_tou" and "residential complex" in apartment["supply"]["reason"]
    assert any(line["kind"] == "rebate" for line in apartment["annual"]["tax_lines"])  # decision 103
    hotel = _entry(result, "hotel")["electricity"]
    assert hotel["supply"]["kind"] == "market" and not any(l["kind"] == "rebate" for l in hotel["annual"]["tax_lines"])
    lowrise = _entry(result, "lowrise")
    assert lowrise["electricity"]["class"]["code"] == "GS 50-999 kW"
    assert "owner decision 167" in lowrise["electricity"]["class"]["reason"]
    assert lowrise["apartment"]["dwelling_units"] == 17


def test_gas_uses_enbridge_rate_6_blocks_on_m3_and_atco_classes_by_annual_gj():
    toronto = _run(fuel="NaturalGas", gas_gj=[100.0] * 12, name="egd")
    low = _run("Calgary", "SmallOffice", fuel="NaturalGas", kwh_per_hour=5.0, peaks=[30.0] * 12,
               gas_gj=[100.0] * 12, name="atco-low")
    mid = _run("Calgary", "SmallOffice", fuel="NaturalGas", kwh_per_hour=5.0, peaks=[30.0] * 12,
               gas_gj=[110.0] * 12, name="atco-mid")
    result = _build([toronto, low, mid])
    gas = _entry(result, "egd")["gas"]
    m3 = 100.0 * 1000 / 39.08
    assert (gas["class"]["code"], gas["unit"], gas["mj_per_m3"]) == ("EGD-6", "m3", 39.08)
    assert gas["months"][0]["volume"] == pytest.approx(m3, abs=0.001)
    blocks = 500 * 0.137319 + 1050 * 0.109839 + (m3 - 1550) * 0.090595
    assert gas["months"][0]["groups"]["distribution_volumetric"] == pytest.approx(blocks, abs=0.01)
    assert _entry(result, "egd")["load"]["annual_gas_m3"] == pytest.approx(12 * m3, abs=0.1)
    assert _entry(result, "atco-low")["gas"]["class"]["code"] == "S-LOW"  # exactly 1,200 GJ: "or less"
    assert _entry(result, "atco-mid")["gas"]["class"]["code"] == "S-MID"
    total = _entry(result, "egd")["total"]
    assert total["status"] == "ok" and total["with_tax"] == pytest.approx(
        _entry(result, "egd")["electricity"]["annual"]["with_tax"] + gas["annual"]["with_tax"], abs=0.02)


def test_doubtful_inputs_leave_a_fuel_not_computable_with_its_reason():
    gas_run = _run("Calgary", "SmallOffice", fuel="NaturalGas", kwh_per_hour=5.0, peaks=[30.0] * 12,
                   gas_gj=[50.0] * 12, name="ended")
    ended = _entry(_build([gas_run], as_of="2026-12-02"), "ended")
    assert ended["gas"]["status"] == "not_computable" and ended["total"]["status"] == "not_computable"
    assert "with_tax" not in ended["total"]
    records = _records()
    tou = next(r for r in records if r["tariff_code"] == "GS-TOU-S")
    next(c for c in tou["components"] if c["tou_period"] == "on-peak")["tou_hours"] = "Weekdays 4 p.m. - 9 p.m."
    changed = _entry(_build([_run(kwh_per_hour=5.0, peaks=[30.0] * 12, name="tou")], records=records), "tou")
    assert "differ from the reviewed ON_TOU periods" in " ".join(changed["electricity"]["reasons"])
    records = [r for r in _records() if r["tariff_code"] != "GS 50-999 kW"]
    missing = _entry(_build([_run(kwh_per_hour=36.0, peaks=[120.0] * 12, name="gone")], records=records), "gone")
    assert "no live record for class" in " ".join(missing["electricity"]["reasons"])
    records = _records()
    d310 = next(r for r in records if r["tariff_code"] == "D310")
    d310["eligibility"] = d310["eligibility"].replace("twice", "three times")
    reworded = _entry(_build([_run("Calgary", "Hospital", kwh_per_hour=40.0, peaks=[200.0] * 12, name="worded")],
                             records=records), "worded")
    assert "no longer contains the reviewed quote" in " ".join(reworded["electricity"]["reasons"])
    hospital = _run("Calgary", "Hospital", kwh_per_hour=40.0, peaks=[200.0] * 12, name="ratchet")
    records = _records()
    facilities = next(c for c in next(r for r in records if r["tariff_code"] == "D310")["components"]
                      if c["component_name"] == "Facilities Charge")
    facilities["notes"] = facilities["notes"].replace("90% of the highest", "80% of the highest")
    changed_ratchet = _entry(_build([hospital], records=records), "ratchet")
    assert "no longer contains the reviewed demand wording" in " ".join(changed_ratchet["electricity"]["reasons"])
    records = _records()
    large = next(r for r in records if r["tariff_code"] == "GS 50-999 kW")
    demand = next(c for c in large["components"]
                  if c["component_name"] == "Retail Transmission Rate - Network Service Rate")
    demand["notes"] = f"{demand.get('notes') or ''} Billed on a ratchet of 80% of the highest demand."
    unreviewed = _entry(_build([_run(kwh_per_hour=36.0, peaks=[120.0] * 12, name="unreviewed")], records=records),
                        "unreviewed")
    assert "mentions a demand ratchet that no reviewed rule covers" in " ".join(unreviewed["electricity"]["reasons"])
    no_market = _entry(_build([_run(kwh_per_hour=36.0, peaks=[120.0] * 12, name="nomarket")],
                              markets={"ON": None, "AB": None}), "nomarket")
    assert "market energy not estimable" in " ".join(no_market["electricity"]["reasons"])


def test_monitoring_reports_a_missing_stale_or_old_archetype_file(tmp_path):
    (tmp_path / "data" / "models").mkdir(parents=True)
    (tmp_path / "site" / "data").mkdir(parents=True)
    (tmp_path / "data" / "models" / "archetypes.json").write_text(json.dumps(CONFIG), encoding="utf-8")
    today = date(2026, 11, 26)
    assert "missing or unreadable" in " ".join(ac.archetype_costs_problems(tmp_path, today))
    document = _build([_run(kwh_per_hour=5.0, peaks=[30.0] * 12)])
    (tmp_path / "site" / "data" / "archetype_costs.json").write_text(json.dumps(document), encoding="utf-8")
    models = {"generated_at": "2000-01-01T00:00:00+00:00"}
    (tmp_path / "site" / "data" / "representative_models.json").write_text(json.dumps(models), encoding="utf-8")
    assert ac.archetype_costs_problems(tmp_path, today) == []
    models["generated_at"] = "2999-01-01T00:00:00+00:00"
    (tmp_path / "site" / "data" / "representative_models.json").write_text(json.dumps(models), encoding="utf-8")
    assert "older than the representative models" in " ".join(ac.archetype_costs_problems(tmp_path, today))
    assert "days ago" in " ".join(ac.archetype_costs_problems(tmp_path, date(2028, 1, 1)))


def test_a_failed_export_keeps_the_previous_file(tmp_path, monkeypatch):
    from pipeline import export_json

    target = tmp_path / "archetype_costs.json"
    target.write_text('{"kept": true}\n', encoding="utf-8")

    def broken(*args, **kwargs):
        raise ValueError("unusable inputs")

    monkeypatch.setattr(ac, "write_archetype_costs", broken)
    assert export_json.export_archetype_costs([], target) is None
    assert target.read_text(encoding="utf-8") == '{"kept": true}\n'


def test_the_68_repository_runs_take_the_documented_classes():
    data = ap.load_archetypes()
    result = ac.build_archetype_costs(_records(), rm.load_crosswalk(), rm.load_usage_levels(), rm.load_taxes(),
                                      CONFIG, SPARK, as_of=AS_OF, market_documents=MARKETS, archetypes=data)
    assert result["summary"]["runs"] == 68 and result["summary"]["computable"] == 68
    counts = {}
    for run in result["runs"]:
        for fuel in ("electricity", "gas"):
            entry = run[fuel]
            if entry:
                counts[(run["city"], fuel, entry["class"]["code"])] = counts.get(
                    (run["city"], fuel, entry["class"]["code"]), 0) + 1
                key = (run["city"], fuel, "supply", entry["supply"]["kind"])
                counts[key] = counts.get(key, 0) + 1
    assert counts == {
        ("Toronto", "electricity", "GS-TOU-S"): 7, ("Toronto", "electricity", "GS 50-999 kW"): 23,
        ("Toronto", "electricity", "GS 1,000-4,999 kW"): 4, ("Toronto", "electricity", "supply", "rpp_tou"): 16,
        ("Toronto", "electricity", "supply", "market"): 18, ("Toronto", "gas", "EGD-6"): 17,
        ("Toronto", "gas", "supply", "utility"): 17,
        ("Calgary", "electricity", "D310"): 20, ("Calgary", "electricity", "D300"): 9,
        ("Calgary", "electricity", "D200"): 5, ("Calgary", "electricity", "supply", "rate_of_last_resort"): 12,
        ("Calgary", "electricity", "supply", "pool"): 22, ("Calgary", "gas", "S-LOW"): 9,
        ("Calgary", "gas", "S-MID"): 8, ("Calgary", "gas", "supply", "utility"): 17}
    for run in result["runs"]:
        assert math.isclose(run["total"]["with_tax"], sum(m["with_tax"] for m in run["total"]["months"]), abs_tol=0.1)
