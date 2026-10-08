"""Meteorology-to-WBGT adapter using the pinned pywbgt Liljegren implementation."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from metpy.units import units
from pywbgt import wbgt as pywbgt_estimate

from .config import SITE_ADJUSTMENTS

METHOD = "Liljegren et al. (2008), via pywbgt 3.0.7; temperature components combined per ShiftShield Plan v7"


def surface_factor(surface: str) -> float:
    return float(SITE_ADJUSTMENTS["surface_factor"].get(surface, SITE_ADJUSTMENTS["surface_factor"]["unknown_default"]))


def site_factors(profile: dict[str, Any]) -> dict[str, float]:
    shade_choice = profile.get("shade", "none")
    shade = SITE_ADJUSTMENTS["shade_fraction"].get(shade_choice, SITE_ADJUSTMENTS["shade_fraction"]["unknown_default"])
    is_indoor = shade_choice == "indoor" or profile.get("enclosure") == "closed"
    land_use = profile.get("land_use", "unknown")
    land_delta = SITE_ADJUSTMENTS["land_use_delta_c"].get(land_use, SITE_ADJUSTMENTS["land_use_delta_c"]["unknown_default"])
    wind_choice = profile.get("wind_exposure", "partial_or_unknown")
    wind_factor = SITE_ADJUSTMENTS["wind_factor"].get(wind_choice, SITE_ADJUSTMENTS["wind_factor"]["partial_or_unknown"])
    if is_indoor:
        shade = SITE_ADJUSTMENTS["shade_fraction"]["indoor_no_sun"]
    return {
        "shade_fraction": float(shade),
        "surface_factor": surface_factor(profile.get("surface", "mixed")),
        "land_use_delta_c": float(land_delta),
        "wind_factor": float(wind_factor),
        "indoor_no_sun": float(is_indoor),
    }


def _per_row(values: Any, count: int) -> np.ndarray:
    """Return one float per input row; a scalar library output is repeated, a wrong length is an error."""
    array = np.asarray(values, dtype=float)
    if array.ndim == 0:
        return np.full(count, float(array))
    array = array.reshape(-1)
    if array.size != count:
        raise ValueError(f"WBGT library returned {array.size} values for {count} input rows")
    return array


def calculate_site_wbgt(
    *,
    timestamps: list[str] | list[datetime],
    latitude: float,
    longitude: float,
    air_c: list[float],
    dewpoint_c: list[float],
    pressure_hpa: list[float],
    wind_10m_m_s: list[float],
    direct_w_m2: list[float],
    diffuse_w_m2: list[float],
    shortwave_w_m2: list[float],
    profile: dict[str, Any],
    margin_c: float | None = None,
) -> list[dict[str, Any]]:
    count = len(air_c)
    arrays = [dewpoint_c, pressure_hpa, wind_10m_m_s, direct_w_m2, diffuse_w_m2, shortwave_w_m2, timestamps]
    if count == 0 or any(len(values) != count for values in arrays):
        raise ValueError("Meteorological inputs must be non-empty arrays of equal length")
    numeric = [air_c, dewpoint_c, pressure_hpa, wind_10m_m_s, direct_w_m2, diffuse_w_m2, shortwave_w_m2]
    if any(not np.isfinite(np.asarray(values, dtype=float)).all() for values in numeric):
        raise ValueError("Meteorological inputs contain a missing or non-finite value")
    if any(value < 0 for value in wind_10m_m_s) or any(value < 0 for value in [*direct_w_m2, *diffuse_w_m2, *shortwave_w_m2]):
        raise ValueError("Wind and radiation values cannot be negative")

    factors = site_factors(profile)
    indoor = bool(factors["indoor_no_sun"])
    direct = np.asarray(direct_w_m2, dtype=float)
    diffuse = np.asarray(diffuse_w_m2, dtype=float)
    global_shortwave = np.asarray(shortwave_w_m2, dtype=float)
    if indoor:
        solar_site = np.zeros(count, dtype=float)
    else:
        solar_site = (
            (1 - factors["shade_fraction"]) * direct
            + diffuse
            + factors["surface_factor"] * global_shortwave
        )
    site_air = np.asarray(air_c, dtype=float) + factors["land_use_delta_c"]
    site_dew = np.asarray(dewpoint_c, dtype=float)  # same vapour pressure as the source forecast
    site_wind = np.asarray(wind_10m_m_s, dtype=float) * factors["wind_factor"]
    dates = pd.DatetimeIndex(pd.to_datetime(timestamps, utc=True))
    iso_times = [str(value) for value in dates]

    try:
        components = pywbgt_estimate(
            datetime=dates,
            lat=np.full(count, float(latitude)),
            lon=np.full(count, float(longitude)),
            # pywbgt/Liljegren mutates several input arrays during unit conversion
            # and wind/solar adjustments; pass isolated copies so audit inputs stay raw.
            solar=units.Quantity(solar_site.copy(), "W/m^2"),
            pres=units.Quantity(np.asarray(pressure_hpa, dtype=float).copy(), "hPa"),
            temp_air=units.Quantity(site_air.copy(), "degC"),
            temp_dew=units.Quantity(site_dew.copy(), "degC"),
            speed=units.Quantity(site_wind.copy(), "m/s"),
            method="liljegren",
        )
    except Exception as exc:
        raise ValueError(f"WBGT model could not evaluate the supplied meteorology: {type(exc).__name__}") from exc

    globe_component = components[0]
    wet_bulb_component = components[2]
    model_solar_component, wind_2m_component, min_wind_component = components[4], components[5], components[6]
    if (
        globe_component is None
        or wet_bulb_component is None
        or model_solar_component is None
        or wind_2m_component is None
        or min_wind_component is None
    ):
        raise ValueError("WBGT library did not return all required thermal and model-input components")
    globe_c = _per_row(globe_component.to("degC").magnitude, count)
    natural_wet_c = _per_row(wet_bulb_component.to("degC").magnitude, count)
    model_solar_w_m2 = _per_row(model_solar_component.to("W/m^2").magnitude, count)
    wind_2m_m_s = _per_row(wind_2m_component.to("m/s").magnitude, count)
    # pywbgt returns the minimum-wind floor as a single scalar, not one value per row.
    min_wind_m_s = _per_row(min_wind_component.to("m/s").magnitude, count)
    margin = float(margin_c if margin_c is not None else SITE_ADJUSTMENTS["uncertainty_margin_c"]["default"])
    if not 0 <= margin <= 5:
        raise ValueError("Uncertainty margin must be between 0°C and 5°C")

    rows: list[dict[str, Any]] = []
    for index in range(count):
        dry = float(site_air[index])
        natural_wet = float(natural_wet_c[index])
        globe = float(globe_c[index])
        # These are the two definitions requested in Plan v7; do not use the library's
        # blended value to hide whether the no-sun or outdoor formula was selected.
        wbgt_c = 0.7 * natural_wet + 0.3 * globe if indoor else 0.7 * natural_wet + 0.2 * globe + 0.1 * dry
        conservative = wbgt_c + margin
        rows.append({
            "time": iso_times[index],
            "wbgt_c": round(wbgt_c, 2),
            "margin_c": margin,
            "conservative_wbgt_c": round(conservative, 2),
            "wbgt_for_thresholds_c": round(conservative, 2),
            "air_site_c": round(dry, 2),
            "natural_wet_bulb_c": round(natural_wet, 2),
            "globe_c": round(globe, 2),
            "site_solar_w_m2": round(float(solar_site[index]), 1),
            "site_wind_10m_m_s": round(float(site_wind[index]), 2),
            "model_adjusted_solar_w_m2": round(float(model_solar_w_m2[index]), 1),
            "model_wind_2m_m_s": round(float(wind_2m_m_s[index]), 3),
            "model_min_wind_m_s": round(float(min_wind_m_s[index]), 3),
            "method": METHOD,
            "site_factors": factors,
        })
    return rows
