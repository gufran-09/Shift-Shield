"""Open-Meteo adapter; hourly inputs interpolated to quarters remain estimates."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from typing import Any, cast

import pandas as pd

BASE_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY = [
    "temperature_2m", "relative_humidity_2m", "dew_point_2m", "wind_speed_10m",
    "shortwave_radiation", "direct_radiation", "diffuse_radiation", "surface_pressure",
]


class ForecastUnavailable(RuntimeError):
    pass


def _fetch(latitude: float, longitude: float, timezone_name: str = "auto") -> dict[str, Any]:
    params = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY),
        "forecast_days": 3,
        "timezone": timezone_name,
        "timeformat": "unixtime",
        "wind_speed_unit": "ms",
    })
    request = Request(f"{BASE_URL}?{params}", headers={"User-Agent": "ShiftShield/0.1 (heat-safety decision-support demo)"})
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise ForecastUnavailable(f"Open-Meteo forecast unavailable ({type(exc).__name__}); use the labelled replay or retry later.") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("hourly"), dict) or not payload["hourly"].get("time"):
        raise ForecastUnavailable("Open-Meteo returned no hourly forecast values.")
    return payload


def forecast_15m(latitude: float, longitude: float, *, timezone_name: str = "auto", horizon_hours: int = 36, now: datetime | None = None) -> dict[str, Any]:
    payload = _fetch(latitude, longitude, timezone_name)
    hourly = payload["hourly"]
    try:
        stamps = pd.to_datetime(hourly["time"], unit="s", utc=True)
        frame = pd.DataFrame({name: hourly.get(name) for name in HOURLY}, index=stamps)
    except (TypeError, ValueError, KeyError) as exc:
        raise ForecastUnavailable("Open-Meteo returned malformed hourly forecast fields.") from exc
    if frame[HOURLY].isna().to_numpy().any():
        missing = [name for name in HOURLY if bool(frame[name].isna().to_numpy().any())]
        raise ForecastUnavailable(f"Open-Meteo forecast lacks required fields: {', '.join(missing)}")
    quarter = frame.resample("15min").interpolate(method="time")
    # Open-Meteo starts at local midnight; the plan must start at the current quarter-hour,
    # otherwise "current" conditions and alerts would describe 00:00 instead of now.
    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = pd.Timestamp(now_utc).floor("15min")
    upcoming = quarter[quarter.index >= start]
    quarter = (upcoming if len(upcoming) else quarter.iloc[-1:]).iloc[: max(1, horizon_hours * 4 + 1)]
    issued = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    for stamp, values in quarter.iterrows():
        row: dict[str, Any] = {key: float(values[key]) for key in HOURLY}
        row["time"] = pd.Timestamp(stamp).isoformat()
        row["data_status"] = "fresh"
        row["source_resolution"] = "hourly"
        rows.append(row)
    if not rows:
        raise ForecastUnavailable("No forecast intervals were produced.")
    return {
        "source": "Open-Meteo Forecast API",
        "source_url": BASE_URL,
        "source_resolution": "hourly forecast, interpolated to 15-minute intervals",
        "timezone": payload.get("timezone", timezone_name),
        "latitude": payload.get("latitude", latitude),
        "longitude": payload.get("longitude", longitude),
        "fetched_at_utc": issued,
        "forecast_age_minutes": 0.0,
        "model_run_metadata": payload.get("generationtime_ms"),
        "units": payload.get("hourly_units", {}),
        "rows": rows,
        "disclaimer": "Forecast values between hourly inputs are linear interpolations, not new measurements.",
    }


def historical_15m(latitude: float, longitude: float, *, start_date: str, end_date: str, timezone_name: str) -> dict[str, Any]:
    """Fetch archive/reanalysis weather; it is never described as an on-site observation."""
    params = urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY),
        "timezone": timezone_name,
        "timeformat": "unixtime",
        "wind_speed_unit": "ms",
    })
    request = Request(f"{ARCHIVE_URL}?{params}", headers={"User-Agent": "ShiftShield/0.1 (historical heat-safety comparison demo)"})
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise ForecastUnavailable(f"Open-Meteo archive unavailable ({type(exc).__name__}); no historical comparison was produced.") from exc
    hourly = payload.get("hourly") if isinstance(payload, dict) else None
    if not isinstance(hourly, dict) or not hourly.get("time"):
        raise ForecastUnavailable("Open-Meteo archive returned no hourly values for this location/date range.")
    try:
        stamps = pd.to_datetime(hourly["time"], unit="s", utc=True)
        if any(not isinstance(hourly.get(name), list) or len(hourly[name]) != len(stamps) for name in HOURLY):
            raise ValueError("archive variable lengths differ")
        frame = pd.DataFrame({name: hourly[name] for name in HOURLY}, index=stamps)
    except (TypeError, ValueError, KeyError) as exc:
        raise ForecastUnavailable("Open-Meteo archive returned malformed hourly weather fields.") from exc
    if frame[HOURLY].isna().to_numpy().any():
        raise ForecastUnavailable("Open-Meteo archive lacks one or more required WBGT inputs; no fallback method was used.")
    quarter = frame.resample("15min").interpolate(method="time")
    rows: list[dict[str, Any]] = []
    for stamp, values in quarter.iterrows():
        row: dict[str, Any] = {key: float(cast(Any, values[key])) for key in HOURLY}
        row["time"] = pd.Timestamp(cast(Any, stamp)).isoformat()
        row["data_status"] = "archive_reanalysis"
        row["source_resolution"] = "hourly archive/reanalysis, interpolated to 15-minute intervals"
        rows.append(row)
    if not rows:
        raise ForecastUnavailable("Open-Meteo archive produced no historical intervals.")
    return {
        "source": "Open-Meteo Historical Weather API (archive/reanalysis)",
        "source_url": ARCHIVE_URL,
        "source_resolution": "hourly archive/reanalysis, linearly interpolated to 15-minute intervals",
        "timezone": payload.get("timezone", timezone_name),
        "latitude": payload.get("latitude", latitude),
        "longitude": payload.get("longitude", longitude),
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "start_date": start_date,
        "end_date": end_date,
        "units": payload.get("hourly_units", {}),
        "rows": rows,
        "observed_on_site": False,
        "disclaimer": "Archive/reanalysis is not an on-site observation. Quarter-hour values are interpolated from hourly data.",
    }
