"""Independent cross-check of app.physics (pywbgt) and the properties the TODO requires.

The reference in tests/reference/liljegren_reference.py is a separate pure-Python implementation
of Liljegren et al. (2008), written by Sameer. Agreement within the tolerance below is evidence
that inputs, units and the WBGT combination are wired correctly; it is not a calibration.

Run from backend/:  pytest tests/test_wbgt_crosscheck.py -v -s
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

import pytest

pytest.importorskip("pywbgt")
from app.physics import calculate_site_wbgt  # noqa: E402
from tests.reference.liljegren_reference import esat_mb, wbgt_outdoor_c  # noqa: E402
from tests.reference.solar_reference import cos_zenith  # noqa: E402

LAT, LON = 17.385, 78.4867  # Hyderabad
OPEN_SITE = {"surface": "grass", "shade": "none", "wind_exposure": "open", "land_use": "vegetated", "enclosure": "open"}
TOLERANCE_C = 1.5

# (UTC time, air C, RH %, wind 10 m m/s, direct W/m2, diffuse W/m2) - illustrative inputs, not observations
CASES = [
    ("2024-05-04T03:30:00Z", 33.0, 50, 2.0, 300.0, 100.0),
    ("2024-05-04T06:30:00Z", 40.0, 20, 3.0, 750.0, 150.0),
    ("2024-05-04T09:30:00Z", 41.0, 16, 4.0, 450.0, 120.0),
    ("2024-05-04T12:30:00Z", 36.0, 25, 2.0, 0.0, 0.0),
    ("2024-06-15T07:00:00Z", 35.0, 60, 1.5, 600.0, 200.0),
]


def dewpoint_c(temp_c: float, rh_pct: float) -> float:
    a, b = 17.625, 243.04
    gamma = math.log(rh_pct / 100) + a * temp_c / (b + temp_c)
    return b * gamma / (a - gamma)


def app_point(time, temp, rh, wind, direct, diffuse, profile=OPEN_SITE):
    return calculate_site_wbgt(
        timestamps=[time], latitude=LAT, longitude=LON, air_c=[temp], dewpoint_c=[dewpoint_c(temp, rh)],
        pressure_hpa=[945.0], wind_10m_m_s=[wind], direct_w_m2=[direct], diffuse_w_m2=[diffuse],
        shortwave_w_m2=[direct + diffuse], profile=profile, margin_c=0.0)[0]


@pytest.mark.parametrize("case", CASES)
def test_app_agrees_with_independent_reference(case):
    time, temp, rh, wind, direct, diffuse = case
    app = app_point(*case)
    when = datetime.fromisoformat(time.replace("Z", "+00:00")).astimezone(timezone.utc)
    solar = app["model_adjusted_solar_w_m2"]
    fdir = direct / (direct + diffuse) if direct + diffuse > 0 else 0.0
    # same moisture as the app (it passes dew point); recompute RH at the site air temperature
    e = rh / 100 * esat_mb(temp + 273.15, 945.0)
    rh_site = 100 * e / esat_mb(app["air_site_c"] + 273.15, 945.0)
    ref, _, _ = wbgt_outdoor_c(app["air_site_c"], rh_site, 945.0, app["model_wind_2m_m_s"], solar, fdir,
                               cos_zenith(when, LAT, LON))
    print(f"{time}  app {app['wbgt_c']:5.2f}  reference {ref:5.2f}  diff {app['wbgt_c'] - ref:+.2f}")
    assert abs(app["wbgt_c"] - ref) <= TOLERANCE_C


def test_more_humidity_never_lowers_wbgt():
    dry = app_point("2024-05-04T06:30:00Z", 38.0, 20, 2.0, 700.0, 150.0)["wbgt_c"]
    humid = app_point("2024-05-04T06:30:00Z", 38.0, 60, 2.0, 700.0, 150.0)["wbgt_c"]
    assert humid >= dry


def test_more_shade_never_raises_wbgt():
    sun = app_point("2024-05-04T06:30:00Z", 38.0, 30, 2.0, 700.0, 150.0)["wbgt_c"]
    shaded = app_point("2024-05-04T06:30:00Z", 38.0, 30, 2.0, 700.0, 150.0, {**OPEN_SITE, "shade": "mostly"})["wbgt_c"]
    assert shaded <= sun


def test_more_wind_never_raises_wbgt_in_sun():
    calm = app_point("2024-05-04T06:30:00Z", 38.0, 30, 1.0, 700.0, 150.0)["wbgt_c"]
    windy = app_point("2024-05-04T06:30:00Z", 38.0, 30, 5.0, 700.0, 150.0)["wbgt_c"]
    assert windy <= calm
