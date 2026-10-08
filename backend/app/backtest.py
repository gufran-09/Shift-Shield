"""Historical archive comparison using the identical deterministic WBGT/schedule path."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .config import SITE_ADJUSTMENTS
from .physics import calculate_site_wbgt
from .scheduling import BAND_ORDER, make_plan

INTERVAL_HOURS = 0.25
SENSITIVITY_OFFSETS_C = (-0.5, 0.0, 0.5)


def _stamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed


def _risk_hours(points: list[dict[str, Any]]) -> float:
    return round(sum(INTERVAL_HOURS for point in points if BAND_ORDER.get(str(point.get("band")), 0) >= BAND_ORDER["high"]), 2)


def summarize_comparison(
    points: list[dict[str, Any]],
    *,
    baseline_threshold_c: float,
    baseline_source: str,
    start_date: str,
    end_date: str,
    archive_source: str,
) -> dict[str, Any]:
    """Compute evidence-labelled interval and transition metrics from already-classified points."""
    intervals = points[:-1] if len(points) > 1 else points
    baseline_hours = sum(INTERVAL_HOURS for point in intervals if point["baseline_alert"])
    danger_hours = sum(INTERVAL_HOURS for point in intervals if point["site_danger"])
    missed = sum(INTERVAL_HOURS for point in intervals if point["site_danger"] and not point["baseline_alert"])
    needless = sum(INTERVAL_HOURS for point in intervals if point["baseline_alert"] and not point["site_danger"])
    episode_starts: list[int] = []
    was_danger = False
    for index, point in enumerate(intervals):
        active = bool(point["site_danger"])
        if active and not was_danger:
            episode_starts.append(index)
        was_danger = active
    baseline_starts: list[int] = []
    was_baseline_alert = False
    for index, point in enumerate(intervals):
        active = bool(point["baseline_alert"])
        if active and not was_baseline_alert:
            baseline_starts.append(index)
        was_baseline_alert = active
    lead_times: list[float] = []
    for index in episode_starts:
        start = _stamp(str(intervals[index]["time"]))
        prior_starts = [baseline_index for baseline_index in baseline_starts if baseline_index <= index]
        if prior_starts:
            baseline_at = _stamp(str(intervals[prior_starts[-1]]["time"]))
            lead = max(0.0, (start - baseline_at).total_seconds() / 60.0)
            lead_times.append(round(lead, 1))
    return {
        "date_range": {"start": start_date, "end": end_date},
        "archive_source": archive_source,
        "source_resolution": "Hourly archive/reanalysis, linearly interpolated to 15-minute intervals",
        "observed_on_site": False,
        "baseline": {
            "type": "user-specified fixed city-style dry-bulb threshold",
            "threshold_c": round(float(baseline_threshold_c), 2),
            "source": baseline_source,
            "warning": "This comparison threshold is supplied by the user; it is not a NIOSH WBGT limit or a ShiftShield clinical recommendation.",
        },
        "definition": "Site danger is a deterministic HIGH/VERY HIGH WBGT work/rest-plan interval. City alert is raw archive air temperature at or above the supplied threshold.",
        "interval_count": len(intervals),
        "city_baseline_alert_hours": round(baseline_hours, 2),
        "site_high_very_high_hours": _risk_hours(intervals),
        "site_danger_hours": round(danger_hours, 2),
        "missed_danger_hours": round(missed, 2),
        "needless_alarm_hours": round(needless, 2),
        "lead_time_minutes": lead_times,
        "danger_outside_13_16_hours": None,
        "outside_window_note": "Not computed; no approved local rule defining a 1–4 PM danger window was supplied.",
        "worker_confirmation_rate": None,
        "worker_confirmation_note": "Historical archive data contains no worker confirmations.",
    }


def run_historical_comparison(
    site: dict[str, Any],
    archive: dict[str, Any],
    *,
    baseline_threshold_c: float,
    baseline_source: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Use raw city air for the baseline and the configured site profile for physical WBGT."""
    rows = list(archive.get("rows", []))
    if not rows:
        raise ValueError("Historical archive contains no quarter-hour intervals")
    base_margin = float(SITE_ADJUSTMENTS["uncertainty_margin_c"]["default"])
    met = calculate_site_wbgt(
        timestamps=[str(row["time"]) for row in rows],
        latitude=float(site["latitude"]),
        longitude=float(site["longitude"]),
        air_c=[float(row["temperature_2m"]) for row in rows],
        dewpoint_c=[float(row["dew_point_2m"]) for row in rows],
        pressure_hpa=[float(row["surface_pressure"]) for row in rows],
        wind_10m_m_s=[float(row["wind_speed_10m"]) for row in rows],
        direct_w_m2=[float(row["direct_radiation"]) for row in rows],
        diffuse_w_m2=[float(row["diffuse_radiation"]) for row in rows],
        shortwave_w_m2=[float(row["shortwave_radiation"]) for row in rows],
        profile=site,
        margin_c=base_margin,
    )
    classified: list[dict[str, Any]] = []
    for raw, thermal in zip(rows, met, strict=True):
        point = {**raw, **thermal}
        schedule = make_plan(point, site)
        classified.append({
            "time": thermal["time"],
            "air_c": round(float(raw["temperature_2m"]), 2),
            "wbgt_c": thermal["wbgt_c"],
            "conservative_wbgt_c": thermal["conservative_wbgt_c"],
            "wbgt_for_thresholds_c": schedule["wbgt_for_thresholds_c"],
            "margin_c": base_margin,
            "band": schedule["band"],
            "work_minutes_per_hour": schedule["work_minutes_per_hour"],
            "rest_minutes_per_hour": schedule["rest_minutes_per_hour"],
            "exceeds_final_15_min_curve": schedule["exceeds_final_15_min_curve"],
            "threshold_version": schedule["threshold_version"],
            "baseline_alert": float(raw["temperature_2m"]) >= float(baseline_threshold_c),
            "site_danger": BAND_ORDER.get(str(schedule["band"]), 0) >= BAND_ORDER["high"] or bool(schedule["exceeds_final_15_min_curve"]),
            "local_time": _stamp(str(raw["time"])).astimezone(ZoneInfo(str(site.get("timezone", "UTC")))).isoformat(),
        })
    summary = summarize_comparison(
        classified,
        baseline_threshold_c=baseline_threshold_c,
        baseline_source=baseline_source,
        start_date=start_date,
        end_date=end_date,
        archive_source=str(archive.get("source", "Open-Meteo archive/reanalysis")),
    )
    sensitivity: list[dict[str, Any]] = []
    for offset in SENSITIVITY_OFFSETS_C:
        margin = min(5.0, max(0.0, round(base_margin + offset, 2)))
        adjusted: list[dict[str, Any]] = []
        for raw, thermal in zip(rows, met, strict=True):
            alternative = {**thermal, "margin_c": margin, "conservative_wbgt_c": round(float(thermal["wbgt_c"]) + margin, 2)}
            schedule = make_plan(alternative, site)
            adjusted.append({"band": schedule["band"]})
        sensitivity.append({"uncertainty_margin_c": margin, "high_or_very_high_hours": _risk_hours(adjusted[:-1] if len(adjusted) > 1 else adjusted)})
    summary.update({
        "site_id": site["site_id"],
        "site_name": site["name"],
        "site_profile_version": site.get("profile_version"),
        "threshold_version": classified[0].get("threshold_version"),
        "wbgt_method": met[0]["method"],
        "default_uncertainty_margin_c": base_margin,
        "sensitivity_analysis": sensitivity,
        "timeline": classified,
        "limitations": [
            "Hourly archive/reanalysis interpolated to quarter hours; not on-site measurements.",
            "Site-adjustment coefficients and NIOSH curve transcription are provisional demo assumptions pending professional review.",
            "No worker confirmation, legal rule, wage or injury outcome is inferred from weather data.",
        ],
    })
    return summary
