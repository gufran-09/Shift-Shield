"""Evidence-derived shift-day totals; never infer wages or completed breaks without evidence."""
from __future__ import annotations

from datetime import datetime
from typing import Any

RISK_BANDS = {"normal": 0, "caution": 1, "high": 2, "very_high": 3}


def _window_minutes(record: dict[str, Any]) -> int:
    window = record.get("window", {})
    try:
        start = datetime.fromisoformat(str(window["rest_window_start"]).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(window["rest_window_end"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return 15
    return max(0, min(180, round((end - start).total_seconds() / 60)))


def build_ledger(
    site_id: str,
    *,
    plan_points: list[dict[str, Any]],
    events: list[dict[str, Any]],
    rest_windows: list[dict[str, Any]],
    recorded_date: str,
) -> dict[str, Any]:
    prescribed_rest = sum(15 for point in plan_points if point.get("activity") == "rest")
    risk_minutes = sum(15 for point in plan_points if RISK_BANDS.get(str(point.get("band")), 0) >= RISK_BANDS["high"])
    stale_minutes = sum(
        15 for point in plan_points
        if point.get("data_status") in {"stale", "missing"}
        and RISK_BANDS.get(str(point.get("band")), 0) >= RISK_BANDS["high"]
    )
    confirmed_minutes = 0
    supervisor_reported_minutes = 0
    disputed_minutes = 0
    responses = 0
    visible_yes = 0
    visible_total = 0
    water_yes = water_total = shade_yes = shade_total = 0
    for record in rest_windows:
        duration = _window_minutes(record)
        status = record.get("status", {}).get("code")
        if status == "confirmed_by_both":
            confirmed_minutes += duration
        if record.get("supervisor_acknowledged"):
            supervisor_reported_minutes += duration
        if status == "disputed":
            disputed_minutes += duration
        aggregate = record.get("aggregate", {})
        responses += int(aggregate.get("total_responses", 0))
        # Combine yes/no only from windows individually at/above the 3-response mask threshold.
        if aggregate.get("split_visible"):
            visible_yes += int(aggregate.get("break_yes_count", 0))
            visible_total += int(aggregate.get("break_yes_count", 0)) + int(aggregate.get("break_no_count", 0))
            if aggregate.get("water_yes_count") is not None:
                water_yes += int(aggregate.get("water_yes_count", 0))
                water_total += int(aggregate.get("water_yes_count", 0)) + int(aggregate.get("water_no_count", 0))
            if aggregate.get("shade_yes_count") is not None:
                shade_yes += int(aggregate.get("shade_yes_count", 0))
                shade_total += int(aggregate.get("shade_yes_count", 0)) + int(aggregate.get("shade_no_count", 0))
    confirmation_rate = round(visible_yes / visible_total, 3) if visible_total else None
    water_rate = round(water_yes / water_total, 3) if water_total else None
    shade_rate = round(shade_yes / shade_total, 3) if shade_total else None
    lead_times = [
        round(float(event["lead_minutes"]), 1)
        for event in events
        if event.get("lead_minutes") is not None and event.get("event_type") in {"heat_heads_up", "heat_transition_alert"}
    ]
    return {
        "site_id": site_id,
        "recorded_date": recorded_date,
        "issued_plan_intervals": len(plan_points),
        "rest_windows_in_plan": len(rest_windows),
        "heat_risk_hours": round(risk_minutes / 60, 2),
        "rest_minutes_prescribed": prescribed_rest,
        "rest_minutes_confirmed_by_both": confirmed_minutes,
        "rest_minutes_supervisor_self_reported": supervisor_reported_minutes,
        "rest_minutes_disputed": disputed_minutes,
        "missed_danger_hours": round(stale_minutes / 60, 2),
        "needless_alarm_hours": None,
        "alert_lead_times_minutes": lead_times,
        "worker_response_count": responses,
        "worker_majority_yes_rate": confirmation_rate,
        "water_available_yes_rate": water_rate,
        "shade_available_yes_rate": shade_rate,
        "visible_response_windows": sum(1 for item in rest_windows if item.get("aggregate", {}).get("split_visible")),
        "confirmation_rate_note": "Yes/no rate combines only individual rest windows with at least 3 responses; this is not a unique-worker rate.",
        "outside_window_danger_hours": None,
        "outside_window_note": "Not computed; no approved local 1–4 PM danger rule was supplied.",
        "wage_savings": None,
        "wage_savings_note": "Not calculated; no wage rate or validated counterfactual was supplied.",
        "evidence_status": "forecast-derived and aggregate-only; supervisor acknowledgement is self-report, not proof",
    }
