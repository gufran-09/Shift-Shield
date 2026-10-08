"""Deterministic, synthetic hot-day replay and its isolated evidence views."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, time as wall_time
from typing import Any
from zoneinfo import ZoneInfo

from .alerts import DEMO_MODE, issue_alert, sign_ack_token
from .config import THRESHOLDS
from .rest import aggregate_key, combined_rest_status, public_aggregate, submit_aggregate
from .store import Store, store

REPLAY_FIXTURE_VERSION = "hot-day-v2-synthetic"
SITE_FIXTURES: list[dict[str, Any]] = [
    {
        "site_id": "demo-concrete-yard", "site_code": "concrete-yard", "name": "Concrete Yard · Low Shade",
        "latitude": 28.6139, "longitude": 77.2090, "timezone": "Asia/Kolkata", "surface": "light_concrete",
        "shade": "none", "wind_exposure": "sheltered", "land_use": "dense_urban", "enclosure": "outdoor",
        "intensity": "heavy", "acclimatization": "unacclimatized", "ppe": "normal", "shift_start": "08:00",
        "shift_end": "18:00", "tasks": [{"name": "Yard handling", "intensity": "heavy", "duration_minutes": 480}],
        "language": "en", "profile_version": 1, "demo_fixture": True,
    },
    {
        "site_id": "demo-shaded-yard", "site_code": "shaded-yard", "name": "Shaded Yard · Moderate Work",
        "latitude": 28.6139, "longitude": 77.2090, "timezone": "Asia/Kolkata", "surface": "grass",
        "shade": "partial", "wind_exposure": "open", "land_use": "vegetated", "enclosure": "outdoor",
        "intensity": "moderate", "acclimatization": "acclimatized", "ppe": "normal", "shift_start": "08:00",
        "shift_end": "18:00", "tasks": [{"name": "Inspection", "intensity": "moderate", "duration_minutes": 480}],
        "language": "en", "profile_version": 1, "demo_fixture": True,
    },
]
REPLAY_STEPS: list[dict[str, Any]] = [
    {"event_id": "08:00", "time_label": "08:00", "wbgt_c": 22.6, "site_b_wbgt_c": 21.4, "risk_label": "normal", "work_minutes_per_hour": 60, "rest_minutes_per_hour": 0, "duration_hours": 2.0, "headline": "Shift opens", "detail": "Synthetic forecast starts the shift at 60 work / 0 scheduled rest minutes per hour.", "alert": None},
    {"event_id": "10:00", "time_label": "10:00", "wbgt_c": 23.25, "site_b_wbgt_c": 22.05, "risk_label": "caution", "work_minutes_per_hour": 45, "rest_minutes_per_hour": 15, "duration_hours": 1.5, "headline": "Heat is building", "detail": "A synthetic heads-up is issued before the stricter 11:30 work/rest schedule.", "alert": "Heads-up: the schedule is forecast to tighten at 11:30."},
    {"event_id": "11:30", "time_label": "11:30", "wbgt_c": 24.1, "site_b_wbgt_c": 22.9, "risk_label": "high", "work_minutes_per_hour": 30, "rest_minutes_per_hour": 30, "duration_hours": 1.5, "headline": "Scheduled rest begins", "detail": "The supervisor can record that the scheduled break started; the QR form records anonymous aggregate responses.", "alert": None},
    {"event_id": "13:00", "time_label": "13:00", "wbgt_c": 25.7, "site_b_wbgt_c": 24.2, "risk_label": "very_high", "work_minutes_per_hour": 15, "rest_minutes_per_hour": 45, "duration_hours": 1.0, "headline": "Peak heat window", "detail": "A stricter synthetic work/rest schedule is shown; above the final curve, stop non-essential heavy work.", "alert": "Synthetic very-high band: stop non-essential heavy work and follow the conservative rest control."},
    {"event_id": "14:00", "time_label": "14:00", "wbgt_c": 24.4, "site_b_wbgt_c": 23.0, "risk_label": "high", "work_minutes_per_hour": 30, "rest_minutes_per_hour": 30, "duration_hours": 2.0, "headline": "Conditions ease slightly", "detail": "The replay demonstrates hysteresis: conditions do not jump straight back to normal.", "alert": None},
    {"event_id": "16:00", "time_label": "16:00", "wbgt_c": 23.1, "site_b_wbgt_c": 21.9, "risk_label": "caution", "work_minutes_per_hour": 45, "rest_minutes_per_hour": 15, "duration_hours": 2.0, "headline": "Shift trends cooler", "detail": "Replay closes with remaining caution and a source-labelled evidence summary.", "alert": None},
]


def seed_demo(store_obj: Store = store) -> list[dict[str, Any]]:
    for site in SITE_FIXTURES:
        existing = store_obj.get("sites", {"site_id": site["site_id"]})
        if existing is None:
            store_obj.put("sites", {**site, "created_at": datetime.now().astimezone().isoformat()})
    return [store_obj.get("sites", {"site_id": site["site_id"]}) or site for site in SITE_FIXTURES]


def start_replay(store_obj: Store = store) -> dict[str, Any]:
    run_id = f"run-{uuid.uuid4()}"
    started = datetime.now().astimezone().isoformat()
    store_obj.put("replay_runs", {
        "run_id": run_id, "event_id": "start", "current_step": -1, "started_at": started,
        "created_at": started, "fixture_version": REPLAY_FIXTURE_VERSION, "is_synthetic": True,
        "site_id": SITE_FIXTURES[0]["site_id"],
    }, append_only=True)
    return {
        "run_id": run_id, "fixture_version": REPLAY_FIXTURE_VERSION, "is_synthetic": True,
        "steps": REPLAY_STEPS, "site_a": SITE_FIXTURES[0], "site_b": SITE_FIXTURES[1],
        "disclaimer": "Replay mode — historical/simulated scenario only. No live weather, field reading, real worker, legal plan or medical guidance is represented.",
    }


def _run_or_error(run_id: str, store_obj: Store) -> dict[str, Any]:
    run = store_obj.get("replay_runs", {"run_id": run_id, "event_id": "start"})
    if not run:
        raise KeyError("Replay run not found")
    return run


def _all_run_events(run_id: str, store_obj: Store) -> list[dict[str, Any]]:
    return sorted(
        [event for event in store_obj.list("replay_runs", {"run_id": run_id}) if event.get("event_id") != "start"],
        key=lambda event: (int(event.get("current_step", -1)), str(event.get("created_at", ""))),
    )


def _issue_replay_alert(run_id: str, step: dict[str, Any], store_obj: Store) -> dict[str, Any] | None:
    site = SITE_FIXTURES[0]
    transition_time = "2026-10-08T11:30:00+05:30"
    return issue_alert(
        site, shift_date="2026-10-08", from_band="normal", to_band="caution",
        window_start=f"{run_id}:{transition_time}", alert_type="heads_up",
        payload={
            "reason": "Deterministic synthetic replay: a stricter band is forecast before 11:30.",
            "lead_minutes": 90, "work_minutes_per_hour": 45, "rest_minutes_per_hour": 15,
            "source_versions": {"replay": REPLAY_FIXTURE_VERSION, "thresholds": THRESHOLDS["version"]},
            "is_synthetic": True,
        }, store_obj=store_obj,
    )


def record_replay_step(run_id: str, event_id: str, store_obj: Store = store) -> dict[str, Any]:
    _run_or_error(run_id, store_obj)
    index = next((i for i, step in enumerate(REPLAY_STEPS) if step["event_id"] == event_id), None)
    if index is None:
        raise ValueError("Unknown replay event; choose a published fixture event.")
    existing = store_obj.get("replay_runs", {"run_id": run_id, "event_id": event_id})
    if existing:
        return existing
    created_at = datetime.now().astimezone().isoformat()
    event: dict[str, Any] = {
        "run_id": run_id, "event_id": event_id, "current_step": index,
        "created_at": created_at, "fixture_version": REPLAY_FIXTURE_VERSION,
        "step": REPLAY_STEPS[index], "site_id": SITE_FIXTURES[0]["site_id"], "is_synthetic": True,
    }
    if REPLAY_STEPS[index].get("alert"):
        alert = _issue_replay_alert(run_id, REPLAY_STEPS[index], store_obj)
        event["alert_id"] = alert.get("alert_id") if alert else None
    created = store_obj.put("replay_runs", event, append_only=True)
    return event if created else (store_obj.get("replay_runs", {"run_id": run_id, "event_id": event_id}) or event)


def _current_run_index(run_id: str, store_obj: Store) -> int:
    events = _all_run_events(run_id, store_obj)
    return max((int(item.get("current_step", -1)) for item in events), default=-1)


def _alert_for_run(run_id: str, store_obj: Store) -> dict[str, Any] | None:
    events = _all_run_events(run_id, store_obj)
    alert_id = next((str(event["alert_id"]) for event in events if event.get("alert_id")), None)
    if not alert_id:
        return None
    matches = [item for item in store_obj.list("issue_log", {"site_id": SITE_FIXTURES[0]["site_id"], "alert_id": alert_id})]
    return next((item for item in matches if item.get("event_type") == "heat_alert"), None)


def _seed_crew_aggregate(run_id: str, store_obj: Store) -> dict[str, Any]:
    window_id = f"{run_id}:11:30:synthetic-rest-window"
    key = aggregate_key(SITE_FIXTURES[0]["site_id"], window_id)
    existing = store_obj.get("rest_confirms", {"rest_key": key})
    if existing:
        return public_aggregate(existing)
    initial = {
        "rest_key": key, "site_id": SITE_FIXTURES[0]["site_id"], "window_id": window_id,
        "total_responses": 7, "break_yes": 7, "break_no": 0,
        "water_yes": 7, "water_no": 0, "shade_yes": 7, "shade_no": 0,
        "symptom_dizzy_count": 0, "symptom_headache_count": 0, "symptom_cramps_count": 0,
        "fixture_version": REPLAY_FIXTURE_VERSION, "is_synthetic": True,
        "created_at": datetime.now().astimezone().isoformat(),
    }
    store_obj.put("rest_confirms", initial, append_only=True)
    return public_aggregate(store_obj.get("rest_confirms", {"rest_key": key}) or initial)


def _replay_window(run_id: str, store_obj: Store) -> dict[str, str]:
    now = datetime.now().astimezone()
    start = now - timedelta(minutes=1)
    end = now + timedelta(minutes=29)
    return {
        "rest_window_id": f"{run_id}:11:30:synthetic-rest-window",
        "rest_window_start": start.isoformat(), "rest_window_end": end.isoformat(),
    }


def replay_state(run_id: str, store_obj: Store = store) -> dict[str, Any]:
    start = _run_or_error(run_id, store_obj)
    events = _all_run_events(run_id, store_obj)
    current_step = max((int(event.get("current_step", -1)) for event in events), default=-1)
    window = _replay_window(run_id, store_obj)
    aggregate = _seed_crew_aggregate(run_id, store_obj) if current_step >= 2 else public_aggregate(None)
    window_key = aggregate_key(SITE_FIXTURES[0]["site_id"], window["rest_window_id"])
    supervisor_ack = store_obj.get("acks", {"alert_id": f"rest-{window_key}"})
    status = combined_rest_status(bool(supervisor_ack), aggregate)
    alert = _alert_for_run(run_id, store_obj)
    alert_acknowledged = bool(alert and store_obj.get("acks", {"alert_id": alert["alert_id"]}))
    token = None
    if alert:
        try:
            expires_at = int(datetime.now().timestamp()) + 4 * 3600
            token = sign_ack_token(site_id=str(alert["site_id"]), alert_id=str(alert["alert_id"]), expires_at=expires_at)
        except Exception:
            token = str(alert.get("ack_token", ""))
    return {
        "run_id": run_id, "events": events, "current_step": current_step,
        "current": REPLAY_STEPS[current_step] if current_step >= 0 else None,
        "fixture_version": start.get("fixture_version", REPLAY_FIXTURE_VERSION), "is_synthetic": True,
        "site_a": SITE_FIXTURES[0], "site_b": SITE_FIXTURES[1],
        "worker_aggregate": aggregate, "worker_window_id": window["rest_window_id"],
        "rest_window": window, "supervisor_break_started": bool(supervisor_ack),
        "rest_status": status, "alert_event": alert, "alert_acknowledged": alert_acknowledged,
        "alert_ack_path": f"/ack/{token}" if token else None,
    }


def record_demo_break_started(run_id: str, store_obj: Store = store) -> dict[str, Any]:
    state = replay_state(run_id, store_obj)
    if state["current_step"] < 2:
        raise ValueError("Reach the synthetic 11:30 scheduled-rest step before recording a break start.")
    window_id = state["worker_window_id"]
    key = aggregate_key(SITE_FIXTURES[0]["site_id"], window_id)
    ack_id = f"rest-{key}"
    now = datetime.now().astimezone().isoformat()
    record = {
        "alert_id": ack_id, "site_id": SITE_FIXTURES[0]["site_id"], "window_id": window_id,
        "record_type": "supervisor_break_started", "acknowledged_at": now,
        "source": "supervisor_self_report", "run_id": run_id,
        "fixture_version": REPLAY_FIXTURE_VERSION, "is_synthetic": True,
    }
    created = store_obj.put("acks", record, append_only=True)
    if created:
        store_obj.put("issue_log", {
            "site_id": SITE_FIXTURES[0]["site_id"], "issue_id": f"demo-break-start-{run_id}",
            "event_type": "supervisor_break_started", "window_id": window_id,
            "run_id": run_id, "created_at": now, "record_type": "self_report",
            "fixture_version": REPLAY_FIXTURE_VERSION, "is_synthetic": True,
        }, append_only=True)
    refreshed = replay_state(run_id, store_obj)
    return {"created": created, "already_recorded": not created, **refreshed}


def demo_worker_context(run_id: str, store_obj: Store = store) -> dict[str, Any]:
    state = replay_state(run_id, store_obj)
    ready = state["current_step"] >= 2
    return {
        "run_id": run_id, "is_synthetic": True,
        "site": {"name": SITE_FIXTURES[0]["name"], "site_code": SITE_FIXTURES[0]["site_code"], "language": "en", "timezone": "Asia/Kolkata"},
        "active_window": ({**state["rest_window"], "work_minutes_per_hour": 30, "rest_minutes_per_hour": 30, "band": "high", "activity": "rest"} if ready else None),
        "eligible": ready, "message": "Replay mode — historical/simulated scenario; never a current condition.",
        "aggregate": state["worker_aggregate"], "combined_status": state["rest_status"],
        "disclaimer": "Responses are synthetic replay aggregates; no worker is represented and no identity is collected.",
    }


def submit_demo_worker(
    run_id: str, *, break_received: bool, water_available: bool | None,
    shade_available: bool | None, symptoms: list[str], store_obj: Store = store,
) -> dict[str, Any]:
    context = demo_worker_context(run_id, store_obj)
    if not context["eligible"] or not context["active_window"]:
        raise ValueError("Reach the synthetic 11:30 rest step before submitting the replay response.")
    window_id = str(context["active_window"]["rest_window_id"])
    aggregate = submit_aggregate(
        SITE_FIXTURES[0]["site_id"], window_id, break_received=break_received,
        water_available=water_available, shade_available=shade_available,
        symptoms=symptoms, store_obj=store_obj,
    )
    # submit_aggregate deliberately retains no caller ID or individual response.
    refreshed = replay_state(run_id, store_obj)
    return {
        "accepted": True, "aggregate": aggregate, "combined_status": refreshed["rest_status"],
        "message": "Synthetic demo response added to the aggregate only.",
        "disclaimer": "No identity is collected; the replay is not a live workforce record.",
    }


def replay_dashboard(run_id: str, store_obj: Store = store) -> dict[str, Any]:
    state = replay_state(run_id, store_obj)
    zone = ZoneInfo("Asia/Kolkata")
    local_date = datetime.now(zone).date()
    points: list[dict[str, Any]] = []
    for index, step in enumerate(REPLAY_STEPS):
        hour, minute = (int(part) for part in step["event_id"].split(":"))
        local_dt = datetime.combine(local_date, wall_time(hour, minute), tzinfo=zone)
        action = THRESHOLDS["band_actions"][step["risk_label"]]
        points.append({
            "time": local_dt.isoformat(), "local_time": local_dt.isoformat(),
            "wbgt_c": float(step["wbgt_c"]), "margin_c": 1.0,
            "conservative_wbgt_c": float(step["wbgt_c"]) + 1.0,
            "wbgt_for_thresholds_c": float(step["wbgt_c"]) + 1.0,
            "band": step["risk_label"], "label": action["label"],
            "work_minutes_per_hour": int(step["work_minutes_per_hour"]),
            "rest_minutes_per_hour": int(step["rest_minutes_per_hour"]),
            "guidance": action["guidance"], "water_guidance": THRESHOLDS["water_guidance"],
            "safe_schedule_supported": step["risk_label"] != "very_high",
            "exceeds_final_15_min_curve": step["risk_label"] == "very_high",
            "data_status": "synthetic_replay", "source_resolution": "Synthetic fixture",
            "activity": "rest" if step["risk_label"] in {"high", "very_high"} else "work",
            "rest_window_id": state["worker_window_id"] if index == 2 else None,
            "rest_window_start": state["rest_window"].get("rest_window_start") if index == 2 else None,
            "rest_window_end": state["rest_window"].get("rest_window_end") if index == 2 else None,
        })
    current_index = max(0, state["current_step"])
    current_point = points[current_index]
    start = _run_or_error(run_id, store_obj)
    ledger = _replay_ledger(run_id, state, local_date.isoformat())
    alert_events = [state["alert_event"]] if state.get("alert_event") else []
    window_point = points[2] if state["current_step"] >= 2 else None
    windows: list[dict[str, Any]] = []
    if window_point:
        windows.append({"window": window_point, "aggregate": state["worker_aggregate"], "supervisor_acknowledged": state["supervisor_break_started"], "status": state["rest_status"]})
    return {
        "run_id": run_id, "is_synthetic": True,
        "site": {**SITE_FIXTURES[0], "profile_version": 1},
        "plan": {
            "site_id": SITE_FIXTURES[0]["site_id"], "created_at": start["created_at"],
            "forecast": {"source": "deterministic replay", "source_resolution": "Synthetic fixture", "fetched_at_utc": start["created_at"], "forecast_age_minutes": 0, "timezone": "Asia/Kolkata", "data_status": "synthetic_replay"},
            "points": points, "current": current_point, "is_demo_only": True,
            "safety_disclaimer": "Replay mode — historical/simulated scenario. WBGT and band values below are seeded test data, not current weather, field readings, or safe-work guidance.",
        },
        "windows": windows, "events": alert_events, "ledger": ledger,
        "supervisor_break_started": state["supervisor_break_started"],
        "alert_acknowledged": state["alert_acknowledged"], "alert_ack_path": state["alert_ack_path"],
        "worker_aggregate": state["worker_aggregate"], "rest_status": state["rest_status"],
        "worker_window_id": state["worker_window_id"], "current_step": state["current_step"],
    }


def _replay_ledger(run_id: str, state: dict[str, Any], recorded_date: str) -> dict[str, Any]:
    included_steps = REPLAY_STEPS[:max(0, int(state["current_step"]) + 1)]
    plan_rest = sum(float(step["duration_hours"]) * float(step["rest_minutes_per_hour"]) for step in included_steps)
    danger_hours = sum(float(step["duration_hours"]) for step in included_steps if step["risk_label"] in {"high", "very_high"})
    aggregate = state["worker_aggregate"]
    status_code = state["rest_status"]["code"]
    confirmed = 30 if status_code == "confirmed_by_both" else 0
    supervisor_only = 30 if status_code == "supervisor_only" else 0
    disputed = 30 if status_code == "disputed" else 0
    total = int(aggregate.get("total_responses", 0))
    yes = int(aggregate.get("break_yes_count", 0))
    return {
        "site_id": SITE_FIXTURES[0]["site_id"], "recorded_date": recorded_date,
        "issued_plan_intervals": max(0, state["current_step"] + 1),
        "rest_windows_in_plan": 1 if state["current_step"] >= 2 else 0,
        "heat_risk_hours": danger_hours if state["current_step"] >= 2 else 0.0,
        "rest_minutes_prescribed": round(plan_rest) if state["current_step"] >= 2 else 0,
        "rest_minutes_confirmed_by_both": confirmed,
        "rest_minutes_supervisor_self_reported": supervisor_only,
        "rest_minutes_disputed": disputed, "missed_danger_hours": 0.0,
        "needless_alarm_hours": None, "alert_lead_times_minutes": [90] if state.get("alert_event") else [],
        "worker_majority_yes_rate": (yes / total) if total >= 3 else None,
        "worker_response_count": total,
        "water_available_yes_rate": 1.0 if total >= 3 and aggregate.get("water_yes_count", 0) == total else None,
        "shade_available_yes_rate": 1.0 if total >= 3 and aggregate.get("shade_yes_count", 0) == total else None,
        "visible_response_windows": 1 if total >= 3 else 0,
        "confirmation_rate_note": "Synthetic replay aggregate; no live workers represented.",
        "outside_window_danger_hours": None,
        "outside_window_note": "No approved local action plan is loaded in this synthetic replay.",
        "wage_savings": None, "wage_savings_note": "No wage inputs; no savings inferred.",
        "evidence_status": "synthetic_replay_only", "run_id": run_id, "is_synthetic": True,
    }


def replay_compliance(run_id: str, store_obj: Store = store) -> dict[str, Any]:
    """Expose persisted synthetic break evidence without implying legal compliance."""
    state = replay_state(run_id, store_obj)
    step = REPLAY_STEPS[2]
    status = state["rest_status"]
    if state["current_step"] < 2:
        rest_status = "no_record"
        evidence_text = "Reach the synthetic 11:30 rest step before either side can submit the break record."
        confirmed_by = "Not available until replay rest step"
    elif status["code"] == "confirmed_by_both":
        rest_status = "confirmed_by_both"
        evidence_text = "Supervisor self-report plus an anonymous worker majority confirms this synthetic rest record."
        confirmed_by = "Supervisor self-report + worker aggregate"
    elif status["code"] == "supervisor_only":
        rest_status = "supervisor_only"
        evidence_text = "A synthetic supervisor self-report exists; worker evidence is not a majority YES."
        confirmed_by = "Supervisor self-report only"
    elif status["code"] == "disputed":
        rest_status = "disputed"
        evidence_text = "Synthetic worker feedback disputes the supervisor self-report."
        confirmed_by = "Conflicting synthetic evidence"
    else:
        rest_status = "no_record"
        evidence_text = "The synthetic scheduled-rest step has not yet been recorded by both sides."
        confirmed_by = "Awaiting two-sided evidence"
    alert_text = "Alert acknowledged" if state["alert_acknowledged"] else "Alert not yet acknowledged"
    return {
        "site_id": SITE_FIXTURES[0]["site_id"],
        "date": datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat(),
        "status": "no_approved_plan",
        "warning": "Replay mode — simulated scenario only. No local heat action plan was uploaded or approved; this is not a legal compliance result.",
        "is_synthetic": True,
        "run_id": run_id,
        "rest_record_status": status,
        "obligations": [
            {
                "obligation_id": "demo-local-plan-unconfirmed",
                "title": "Local heat action plan",
                "plan_requirement": "No real local plan uploaded or approved",
                "physiology_requirement": "The deterministic schedule is shown separately as synthetic replay data",
                "applied_requirement": "No legal/local obligation applied",
                "status": "unconfirmed",
                "confirmed_by": "No human reviewer",
            },
            {
                "obligation_id": f"{run_id}-synthetic-rest-record",
                "title": "11:30 scheduled rest record · synthetic",
                "plan_requirement": f"Replay fixture: {step['work_minutes_per_hour']} work / {step['rest_minutes_per_hour']} rest minutes per hour",
                "physiology_requirement": "Not a real site evaluation; seeded scenario only",
                "applied_requirement": f"{alert_text}. {evidence_text}",
                "status": rest_status,
                "confirmed_by": confirmed_by,
            },
        ],
    }
