"""ShiftShield API. Safety decisions stay in deterministic, versioned Python modules."""
from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import datetime, time as wall_time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .backtest import run_historical_comparison
from .alerts import acknowledge, create_email_subscription, issue_alert, refresh_email_subscription, remove_email_subscription, verify_ack_token
from .compliance import approved_rules, apply_stricter_constraints, daily_compliance
from .config import DEMO_MODE, PUBLIC_ORIGIN, SITE_ADJUSTMENTS, THRESHOLDS
from .demo import REPLAY_FIXTURE_VERSION, REPLAY_STEPS, SITE_FIXTURES, demo_worker_context, record_demo_break_started, record_replay_step, replay_compliance, replay_dashboard, replay_state, seed_demo, start_replay, submit_demo_worker
from .ledger import build_ledger
from .models import AckRequest, HistoricalBacktestRequest, PublicCheckRequest, ReplayAction, RestSubmission, RuleDecision, SiteCreate
from .physics import METHOD, calculate_site_wbgt
from .rest import aggregate_key, combined_rest_status, public_aggregate, submit_aggregate
from .rulebook import (
    BedrockUnavailable,
    InvalidQuote,
    MAX_PDF_BYTES,
    approve_candidate,
    invoke_candidates,
    persist_candidates,
    read_pdf_pages,
    start_rulebook_workflow,
    store_pdf,
)
from .schedule_clock import attach_rest_windows, eligible_rest_window, next_rest_window
from .scheduling import BAND_ORDER, make_plan, one_band_stricter, select_band
from .security import create_site_access, verify_site_access
from .store import Store, store
from .weather import ForecastUnavailable, forecast_15m, historical_15m


app = FastAPI(
    title="ShiftShield API",
    version="0.1.0",
    description=(
        "Site heat-risk decision support. Thresholds and site adjustments are provisional demo assumptions, "
        "pending occupational-safety review; this is not medical advice or field-ready guidance."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
_origins = [item.strip() for item in os.getenv("WEB_ORIGINS", "").split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def privacy_and_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.on_event("startup")
def initialize_demo() -> None:
    # Fixtures contain no real worker/supervisor data; they are not inserted in field mode.
    if DEMO_MODE:
        seed_demo()
    elif THRESHOLDS.get("professional_review") != "APPROVED":
        raise RuntimeError("Field mode is blocked until an occupational-safety professional approves the versioned threshold configuration.")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _next_shift_end_utc(site: dict[str, Any]) -> str:
    try:
        zone = ZoneInfo(str(site.get("timezone") or "UTC"))
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("UTC")
    local_now = _now().astimezone(zone)
    end_clock = wall_time.fromisoformat(str(site.get("shift_end", "17:00")))
    end_date = local_now.date()
    if end_clock <= local_now.timetz().replace(tzinfo=None):
        end_date += timedelta(days=1)
    return datetime.combine(end_date, end_clock, tzinfo=zone).astimezone(timezone.utc).isoformat()


def _site_or_404(site_id: str) -> dict[str, Any]:
    site = store.get("sites", {"site_id": site_id})
    if not site:
        raise HTTPException(status_code=404, detail={"error": "site_not_found", "message": "Site not found."})
    return site


def _site_by_code_or_404(site_code: str) -> dict[str, Any]:
    matches = store.list("sites", {"site_code": site_code})
    if not matches:
        raise HTTPException(status_code=404, detail={"error": "site_not_found", "message": "This QR code is not linked to an active site."})
    return matches[0]


def _authorize(site_id: str, authorization: str | None) -> dict[str, Any]:
    site = _site_or_404(site_id)
    verify_site_access(site, authorization)
    return site


def _public_site(site: dict[str, Any]) -> dict[str, Any]:
    hidden = {
        "admin_token_salt", "admin_token_hash", "sns_topic_arn", "sns_subscription_arn",
        "email_contact_hash", "supervisor_email", "email_opt_in_at", "email_opt_out_at",
    }
    return {key: value for key, value in site.items() if key not in hidden}


def _public_event(event: dict[str, Any]) -> dict[str, Any]:
    clean = dict(event)
    clean.pop("ack_token", None)
    return clean


def _schedule_for_profile(site: dict[str, Any], forecast: dict[str, Any], *, state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    weather = forecast["rows"]
    calculated = calculate_site_wbgt(
        timestamps=[row["time"] for row in weather],
        latitude=float(site["latitude"]),
        longitude=float(site["longitude"]),
        air_c=[row["temperature_2m"] for row in weather],
        dewpoint_c=[row["dew_point_2m"] for row in weather],
        pressure_hpa=[row["surface_pressure"] for row in weather],
        wind_10m_m_s=[row["wind_speed_10m"] for row in weather],
        direct_w_m2=[row["direct_radiation"] for row in weather],
        diffuse_w_m2=[row["diffuse_radiation"] for row in weather],
        shortwave_w_m2=[row["shortwave_radiation"] for row in weather],
        profile=site,
    )
    points: list[dict[str, Any]] = []
    for source, wbgt in zip(weather, calculated, strict=True):
        point = {**wbgt, "data_status": source.get("data_status", "fresh"), "source_resolution": forecast["source_resolution"]}
        plan = make_plan(point, site)
        points.append({
            **plan,
            "time": source["time"],
            "temperature_2m_c": source["temperature_2m"],
            "dew_point_2m_c": source["dew_point_2m"],
            "relative_humidity_pct": source["relative_humidity_2m"],
            "surface_pressure_hpa": source["surface_pressure"],
            "wind_speed_10m_m_s": source["wind_speed_10m"],
            "direct_radiation_w_m2": source["direct_radiation"],
            "diffuse_radiation_w_m2": source["diffuse_radiation"],
            "shortwave_radiation_w_m2": source["shortwave_radiation"],
            "data_status": source.get("data_status", "fresh"),
        })
    timezone_name = str(forecast.get("timezone") or site.get("timezone") or "UTC")
    if points and state:
        # An anonymous symptom threshold can tighten the plan, never ease it.
        floor = state.get("symptom_band_floor")
        floor_until = state.get("symptom_floor_until")
        if floor and floor_until:
            try:
                if datetime.fromisoformat(str(floor_until).replace("Z", "+00:00")) > _now():
                    current = points[0]
                    if BAND_ORDER.get(str(floor), 0) > BAND_ORDER.get(str(current["band"]), 0):
                        _apply_band_action(current, str(floor))
                        current["symptom_tightening_applied"] = True
            except ValueError:
                pass
    return attach_rest_windows(points, site, timezone_name)


def _apply_band_action(point: dict[str, Any], band: str) -> None:
    action = THRESHOLDS["band_actions"][band]
    point.update({
        "band": band,
        "label": action["label"],
        "work_minutes_per_hour": int(action["work_minutes_per_hour"]),
        "rest_minutes_per_hour": int(action["rest_minutes_per_hour"]),
        "guidance": action["guidance"],
    })


def _safe_forecast(site: dict[str, Any], *, store_obj: Store = store) -> tuple[dict[str, Any], bool]:
    try:
        value = forecast_15m(
            float(site["latitude"]), float(site["longitude"]),
            timezone_name=str(site.get("timezone") or "auto"), horizon_hours=36,
        )
        return value, False
    except ForecastUnavailable as exc:
        prior = store_obj.get("site_state", {"site_id": site["site_id"], "state_key": "last_forecast"})
        if not prior or not prior.get("forecast"):
            raise HTTPException(status_code=503, detail={
                "error": "weather_unavailable",
                "message": "Current forecast is unavailable and there is no recent forecast to fall back to. Risk is unknown; use the approved local heat-safety plan. No normal/green status is available.",
            }) from exc
        forecast = prior["forecast"]
        try:
            age = (_now() - datetime.fromisoformat(forecast["fetched_at_utc"].replace("Z", "+00:00"))).total_seconds() / 60
        except (KeyError, ValueError, TypeError):
            age = 10_000
        if age > 360:
            raise HTTPException(status_code=503, detail={
                "error": "weather_stale",
                "message": "The last forecast is over six hours old. Risk is unknown; use the approved local heat-safety plan. No normal/green status is available.",
            }) from exc
        stale = {**forecast, "forecast_age_minutes": round(age, 1), "data_status": "stale", "warning": str(exc)}
        stale["rows"] = [{**row, "data_status": "stale"} for row in forecast.get("rows", [])]
        return stale, True


def _apply_evaluation_hysteresis(
    points: list[dict[str, Any]], site: dict[str, Any], state: dict[str, Any] | None,
) -> tuple[int, str, int]:
    """Tighten on one evaluation; require two below-buffer evaluations before easing."""
    if not points:
        return 0, "normal", 0
    current = points[0]
    candidate = str(current["band"])
    previous = str((state or {}).get("current_band") or candidate)
    below_count = int((state or {}).get("ease_count", 0))
    if BAND_ORDER.get(candidate, 0) > BAND_ORDER.get(previous, 0):
        selected, below_count = candidate, 0
    elif BAND_ORDER.get(candidate, 0) < BAND_ORDER.get(previous, 0):
        limits = current.get("thresholds_c", {})
        prior_boundary = {"caution": "60", "high": "45", "very_high": "30"}.get(previous)
        buffer = float(THRESHOLDS["hysteresis"]["buffer_c"])
        value = float(current.get("wbgt_for_thresholds_c", 99))
        if prior_boundary and value < float(limits.get(prior_boundary, 0)) - buffer:
            below_count += 1
        else:
            below_count = 0
        if below_count >= int(THRESHOLDS["hysteresis"]["below_threshold_consecutive_evaluations_to_ease"]):
            selected = ["normal", "caution", "high", "very_high"][max(0, BAND_ORDER.get(previous, 3) - 1)]
            below_count = 0
        else:
            selected = previous
    else:
        selected, below_count = candidate, 0
    if selected != candidate:
        _apply_band_action(current, selected)
        current["hysteresis_hold"] = selected == previous
    return len(points), selected, below_count


def _register_email_opt_in(site: dict[str, Any], email: str | None, enabled: bool) -> dict[str, Any]:
    if not enabled:
        return {"email_alert_opt_in": False, "email_subscription_status": "off", "email_opt_out_at": _now().isoformat()}
    if not email:
        raise HTTPException(status_code=422, detail={"error": "email_required_for_opt_in", "message": "Enter a supervisor email address to enable alerts."})
    import hashlib

    metadata: dict[str, Any] = {
        "email_alert_opt_in": True,
        "email_contact_hash": hashlib.sha256(email.strip().lower().encode()).hexdigest(),
        "email_opt_in_at": _now().isoformat(),
    }
    if DEMO_MODE:
        metadata["email_subscription_status"] = "not_sent_demo"
        return metadata
    try:
        metadata.update(create_email_subscription(site["site_id"], email, enabled=True))
    except Exception as exc:
        # Never include the raw email, request payload or AWS exception text in logs.
        metadata["email_subscription_status"] = f"setup_error:{type(exc).__name__}"
    return metadata


def _record_plan(site: dict[str, Any], forecast: dict[str, Any], points: list[dict[str, Any]], *, store_obj: Store = store) -> dict[str, Any]:
    site_id = str(site["site_id"])
    previous_state = store_obj.get("site_state", {"site_id": site_id, "state_key": "evaluation"}) or {}
    previous_evaluation_band = previous_state.get("current_band")
    if points:
        _, current_band, ease_count = _apply_evaluation_hysteresis(points, site, previous_state)
    else:
        current_band, ease_count = str(previous_state.get("current_band", "normal")), int(previous_state.get("ease_count", 0))
    created = _now().isoformat()
    plan_id = f"plan-{uuid.uuid4()}"
    plan = {
        "site_id": site_id,
        "plan_id": plan_id,
        "created_at": created,
        "forecast": forecast,
        "points": points,
        "current": points[0] if points else None,
        "current_band": current_band,
        "source_versions": {
            "thresholds": THRESHOLDS["version"],
            "site_adjustments": SITE_ADJUSTMENTS["version"],
            "wbgt_method": METHOD,
            "profile_version": site.get("profile_version", 1),
        },
        "is_demo_only": True,
        "safety_disclaimer": "Decision support only—not medical advice. Threshold transcription is pending occupational-safety review; follow official local guidance.",
    }
    # Mutable current state for the API; immutable issued-plan snapshot in the audit log.
    store_obj.put("site_state", {
        "site_id": site_id, "state_key": "last_forecast", "forecast": forecast,
        "saved_at": created,
    })
    store_obj.put("site_state", {
        "site_id": site_id, "state_key": "evaluation", "current_band": current_band,
        "ease_count": ease_count, "evaluated_at": created,
    })
    points = attach_rest_windows(points, site, str(forecast.get("timezone") or site.get("timezone") or "UTC"))
    plan["points"] = points
    plan["current"] = points[0] if points else None
    store_obj.put("site_state", {"site_id": site_id, "state_key": "latest_plan", "plan": plan, "saved_at": created})
    log_record = {
        "site_id": site_id,
        "issue_id": plan_id,
        "event_type": "issued_site_plan",
        "created_at": created,
        "current_band": current_band,
        "current_wbgt_c": (plan["current"] or {}).get("wbgt_c"),
        "current_conservative_wbgt_c": (plan["current"] or {}).get("conservative_wbgt_c"),
        "method": METHOD,
        "source_versions": plan["source_versions"],
        "forecast_fetched_at_utc": forecast.get("fetched_at_utc"),
        "forecast_age_minutes": forecast.get("forecast_age_minutes"),
        "data_status": forecast.get("data_status", "fresh"),
        "recorded_points": points,
        "decision_support_only": True,
    }
    log_record["recorded_points"] = points
    store_obj.put("issue_log", log_record, append_only=True)
    _issue_transition_alert(
        {**site, "shift_end_utc": _next_shift_end_utc(site)}, points,
        previous_evaluation_band=str(previous_evaluation_band) if previous_evaluation_band else None,
        store_obj=store_obj,
    )
    return plan


def _issue_transition_alert(site: dict[str, Any], points: list[dict[str, Any]], *, previous_evaluation_band: str | None = None, store_obj: Store = store) -> None:
    if not points:
        return
    now = _now()
    candidates: list[tuple[dict[str, Any], dict[str, Any], float]] = []
    if points and previous_evaluation_band and BAND_ORDER.get(str(points[0]["band"]), 0) > BAND_ORDER.get(previous_evaluation_band, 0):
        # The transition may have occurred between 15-minute evaluations; alert now.
        candidates.append(({"band": previous_evaluation_band}, points[0], 0.0))
    for previous, upcoming in zip(points, points[1:]):
        if candidates:
            break
        if BAND_ORDER.get(str(upcoming["band"]), 0) <= BAND_ORDER.get(str(previous["band"]), 0):
            continue
        try:
            transition = datetime.fromisoformat(str(upcoming["time"]).replace("Z", "+00:00"))
        except ValueError:
            continue
        lead = (transition - now).total_seconds() / 60
        if 0 <= lead <= 75 and (45 <= lead <= 75 or lead < 30):
            candidates.append((previous, upcoming, lead))
            break
    if not candidates:
        return
    previous, upcoming, lead = candidates[0]
    refreshed_site = refresh_email_subscription(site)
    if refreshed_site != site:
        store_obj.put("sites", refreshed_site)
        site = refreshed_site
    shift_date = str(upcoming.get("local_time", upcoming["time"]))[:10]
    transition_time = now.isoformat() if lead == 0 else str(upcoming["time"])
    alert_type = "heads_up" if lead >= 30 else "immediate_stricter_plan"
    pending = store_obj.get("site_state", {"site_id": str(site["site_id"]), "state_key": "pending_alert"})
    if pending and pending.get("status", "pending") == "pending" and pending.get("alert_id"):
        prior_ack = store_obj.get("acks", {"alert_id": str(pending["alert_id"])})
        if not prior_ack:
            pending_to = str(pending.get("to_band", "normal"))
            candidate_rank = BAND_ORDER.get(str(upcoming["band"]), 0)
            pending_rank = BAND_ORDER.get(pending_to, 0)
            if candidate_rank < pending_rank:
                resolved = {**pending, "status": "superseded_by_easing", "resolved_at": now.isoformat()}
                store_obj.put("site_state", resolved)
                store_obj.put("issue_log", {
                    "site_id": str(site["site_id"]), "issue_id": f"eased-{pending['alert_id']}",
                    "event_type": "pending_alert_eased", "alert_id": pending["alert_id"],
                    "created_at": now.isoformat(), "new_band": str(upcoming["band"]),
                }, append_only=True)
                return
            if candidate_rank == pending_rank:
                if transition_time != pending.get("window_start"):
                    digest = hashlib.sha256(transition_time.encode()).hexdigest()[:16]
                    store_obj.put("issue_log", {
                        "site_id": str(site["site_id"]), "issue_id": f"move-{pending['alert_id']}-{digest}",
                        "event_type": "pending_alert_rescheduled", "alert_id": pending["alert_id"],
                        "old_window_start": pending.get("window_start"), "new_window_start": transition_time,
                        "created_at": now.isoformat(),
                    }, append_only=True)
                    store_obj.put("site_state", {**pending, "window_start": transition_time, "rescheduled_at": now.isoformat()})
                return
            # A higher-severity target bypasses the same-type cooldown.
    # Idempotency is enforced by the conditional DynamoDB insert in issue_alert.
    alert = issue_alert(
        site,
        shift_date=shift_date,
        from_band=str(previous["band"]),
        to_band=str(upcoming["band"]),
        window_start=transition_time,
        alert_type=alert_type,
        payload={
            "reason": str(upcoming.get("guidance", "A stricter work/rest plan is forecast.")),
            "change_time": transition_time,
            "lead_minutes": round(lead),
            "work_minutes_per_hour": upcoming["work_minutes_per_hour"],
            "rest_minutes_per_hour": upcoming["rest_minutes_per_hour"],
            "margin_c": upcoming.get("margin_c"),
            "source_versions": {
                "thresholds": THRESHOLDS["version"],
                "site_adjustments": SITE_ADJUSTMENTS["version"],
                "wbgt_method": METHOD,
                "profile_version": site.get("profile_version", 1),
            },
        },
        store_obj=store_obj,
        now=now,
    )
    if alert:
        store_obj.put("site_state", {
            "site_id": site["site_id"], "state_key": "pending_alert", "alert_id": alert["alert_id"],
            "from_band": alert["from_band"], "to_band": alert["to_band"], "alert_type": alert["alert_type"],
            "window_start": transition_time, "created_at": alert["created_at"], "reminder_sent": False,
            "saved_at": now.isoformat(),
        })


def _calculate_profile(site: dict[str, Any], *, persist: bool = False, store_obj: Store = store) -> dict[str, Any]:
    site = {**site, "shift_end_utc": _next_shift_end_utc(site)}
    forecast, stale = _safe_forecast(site, store_obj=store_obj)
    if stale:
        # Unknown freshness never appears as a green/normal result.
        forecast = {**forecast, "data_status": "stale"}
    points = _schedule_for_profile(site, forecast, state=store_obj.get("site_state", {"site_id": site["site_id"], "state_key": "symptom_floor"}))
    if stale:
        for point in points:
            point["data_status"] = "stale"
            if BAND_ORDER.get(str(point["band"]), 0) < BAND_ORDER["caution"]:
                _apply_band_action(point, "caution")
                point["data_status"] = "stale_caution"
        points = attach_rest_windows(points, site, str(forecast.get("timezone") or site.get("timezone") or "UTC"))
    plan = _record_plan(site, forecast, points, store_obj=store_obj) if persist else {
        "site_id": site.get("site_id"), "created_at": _now().isoformat(),
        "forecast": forecast, "points": points, "current": points[0] if points else None,
        "is_demo_only": True, "source_versions": {
            "thresholds": THRESHOLDS["version"], "site_adjustments": SITE_ADJUSTMENTS["version"],
            "wbgt_method": METHOD, "profile_version": site.get("profile_version", 1),
        },
        "safety_disclaimer": "Decision support only—not medical advice. Threshold transcription is pending occupational-safety review; follow official local guidance.",
    }
    return plan


def _event_window(site_id: str, window_id: str) -> dict[str, Any] | None:
    state = store.get("site_state", {"site_id": site_id, "state_key": "latest_plan"})
    if not state or not state.get("plan"):
        return None
    for point in state["plan"].get("points", []):
        if point.get("rest_window_id") == window_id:
            return point
    return None


def _rest_context(site: dict[str, Any]) -> dict[str, Any]:
    saved = store.get("site_state", {"site_id": site["site_id"], "state_key": "latest_plan"})
    if not saved or not saved.get("plan"):
        raise HTTPException(status_code=409, detail={"error": "no_issued_plan", "message": "There is no issued rest schedule yet. Ask the supervisor to refresh the forecast."})
    plan = saved["plan"]
    points = plan.get("points", [])
    window = next_rest_window(points)
    if not window:
        return {"site": _public_site(site), "active_window": None, "eligible": False, "message": "No break is scheduled in this forecast window. Follow the site plan and local guidance."}
    now = _now()
    eligible = eligible_rest_window(points, str(window["rest_window_id"]), now=now) is not None
    rest_key = aggregate_key(str(site["site_id"]), str(window["rest_window_id"]))
    values = store.get("rest_confirms", {"rest_key": rest_key})
    ack = store.get("acks", {"alert_id": f"rest-{rest_key}"})
    aggregate = public_aggregate(values)
    return {
        "site": {"name": site.get("name"), "site_code": site.get("site_code"), "language": site.get("language", "en"), "timezone": site.get("timezone", "Asia/Kolkata")},
        "active_window": {key: window.get(key) for key in ("rest_window_id", "rest_window_start", "rest_window_end", "work_minutes_per_hour", "rest_minutes_per_hour", "band", "label")},
        "eligible": eligible,
        "message": "This scheduled break is open now." if eligible else "This is the next scheduled break. Responses are accepted only during the break window.",
        "aggregate": aggregate,
        "combined_status": combined_rest_status(bool(ack), aggregate),
        "disclaimer": "Anonymous aggregate only. No worker names, phone numbers, device IDs, or individual responses are stored. Counts do not prove a break occurred.",
    }


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "service": "shiftshield", "mode": "demo" if DEMO_MODE else "field", "storage_backend": store.backend, "threshold_review": THRESHOLDS["professional_review"]}


@app.get("/api/meta")
def metadata() -> dict[str, Any]:
    return {
        "name": "ShiftShield",
        "tagline": "The heat alert that proves the rest happened.",
        "thresholds": {"version": THRESHOLDS["version"], "status": THRESHOLDS["status"], "professional_review": THRESHOLDS["professional_review"]},
        "site_adjustments": {"version": SITE_ADJUSTMENTS["version"], "status": SITE_ADJUSTMENTS["status"]},
        "method": METHOD,
        "public_origin_configured": bool(PUBLIC_ORIGIN),
        "demo_mode": DEMO_MODE,
        "decision_support_only": True,
        "safety_notice": "Demo values pending occupational-safety review. Not medical advice or field-ready guidance; follow official local safety instructions.",
    }


@app.post("/api/public/heat-check")
def public_heat_check(request: PublicCheckRequest) -> dict[str, Any]:
    profile = request.model_dump()
    profile["site_id"] = "public-check"
    profile["shift_start"] = "00:00"
    profile["shift_end"] = "23:59"
    profile["profile_version"] = 1
    try:
        plan = _calculate_profile(profile, persist=False)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"error": "heat_estimate_unavailable", "message": f"WBGT estimate unavailable ({type(exc).__name__}); no heat-index fallback was used."}) from exc
    forecast = plan["forecast"]
    # The forecast starts at local midnight; the public check must describe now, not 00:00.
    now = _now()
    now_quarter = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0)
    all_points = plan.get("points", [])
    upcoming = [point for point in all_points if datetime.fromisoformat(str(point["time"]).replace("Z", "+00:00")) >= now_quarter] or all_points[-1:]
    return {
        "location": {"latitude": request.latitude, "longitude": request.longitude, "timezone": forecast.get("timezone")},
        "forecast": {key: forecast.get(key) for key in ("source", "source_resolution", "fetched_at_utc", "forecast_age_minutes", "timezone", "data_status", "warning")},
        "current": upcoming[0] if upcoming else None,
        "timeline": upcoming[:97],
        "threshold_status": THRESHOLDS["status"],
        "site_assumption_status": SITE_ADJUSTMENTS["status"],
        "is_demo_only": True,
        "disclaimer": plan["safety_disclaimer"],
        "fixed_emergency_footer": "Shade, cool the person, water if conscious; call 112 for confusion, fainting or hot dry skin.",
    }


@app.post("/api/sites")
def create_site(request: SiteCreate) -> dict[str, Any]:
    site_id = str(uuid.uuid4())
    site_code = secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:12].lower()
    supervisor_token, salt, digest = create_site_access()
    now = _now().isoformat()
    payload = request.model_dump(exclude={"supervisor_email", "email_alert_opt_in"})
    site: dict[str, Any] = {
        **payload,
        "site_id": site_id,
        "site_code": site_code,
        "profile_version": 1,
        "created_at": now,
        "updated_at": now,
        "admin_token_salt": salt,
        "admin_token_hash": digest,
        "active": True,
    }
    try:
        ZoneInfo(str(site["timezone"]))
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_timezone", "message": "Use an IANA time zone such as Asia/Kolkata."}) from exc
    site["shift_end_utc"] = _next_shift_end_utc(site)
    email_state = _register_email_opt_in(site, request.supervisor_email, request.email_alert_opt_in)
    site.update(email_state)
    store.put("sites", site)
    return {
        "site": _public_site(site),
        "supervisor_token": supervisor_token,
        "supervisor_token_notice": "This high-entropy supervisor token is shown once. Store it in a password manager; it is not recoverable from the server.",
        "email_status": site.get("email_subscription_status", "off"),
    }


@app.get("/api/sites/{site_id}")
def get_site(site_id: str, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    site = _authorize(site_id, authorization)
    return {"site": _public_site(site)}


@app.put("/api/sites/{site_id}")
def update_site(site_id: str, request: SiteCreate, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    site = _authorize(site_id, authorization)
    next_profile = request.model_dump(exclude={"supervisor_email", "email_alert_opt_in"})
    try:
        ZoneInfo(str(next_profile["timezone"]))
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_timezone", "message": "Use an IANA time zone such as Asia/Kolkata."}) from exc
    previous_opt_in = bool(site.get("email_alert_opt_in"))
    new_opt_in = request.email_alert_opt_in
    email_fields: dict[str, Any]
    if previous_opt_in and not new_opt_in:
        try:
            remove_email_subscription(site)
        except Exception:
            pass
        email_fields = {"email_alert_opt_in": False, "email_subscription_status": "off", "email_opt_out_at": _now().isoformat()}
    elif new_opt_in:
        if previous_opt_in:
            try:
                remove_email_subscription(site)
            except Exception:
                pass
        email_fields = _register_email_opt_in(site, request.supervisor_email, True)
    else:
        email_fields = {"email_alert_opt_in": False, "email_subscription_status": "off"}
    updated = {**site, **next_profile, **email_fields, "updated_at": _now().isoformat(), "profile_version": int(site.get("profile_version", 1)) + 1}
    updated["shift_end_utc"] = _next_shift_end_utc(updated)
    store.put("sites", updated)
    return {"site": _public_site(updated), "email_status": updated.get("email_subscription_status", "off")}


@app.post("/api/sites/{site_id}/email-opt-out")
def email_opt_out(site_id: str, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    site = _authorize(site_id, authorization)
    try:
        remove_email_subscription(site)
    except Exception as exc:
        # The opt-out state takes effect in the app even if SNS needs cleanup.
        status = f"sns_cleanup_pending:{type(exc).__name__}"
    else:
        status = "off"
    updated = {**site, "email_alert_opt_in": False, "email_subscription_status": status, "email_opt_out_at": _now().isoformat()}
    for key in ("sns_topic_arn", "sns_subscription_arn", "email_contact_hash", "email_opt_in_at"):
        updated.pop(key, None)
    store.put("sites", updated)
    return {"email_alert_opt_in": False, "status": status, "message": "The local alert preference is off. Contact-hash metadata has been deleted; no email address was stored by ShiftShield."}


@app.post("/api/sites/{site_id}/plan")
def refresh_site_plan(site_id: str, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    site = _authorize(site_id, authorization)
    return _calculate_profile(site, persist=True)


@app.get("/api/sites/{site_id}/plan")
def get_site_plan(site_id: str, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    site = _authorize(site_id, authorization)
    saved = store.get("site_state", {"site_id": site_id, "state_key": "latest_plan"})
    if saved and saved.get("plan"):
        return saved["plan"]
    return _calculate_profile(site, persist=False)


@app.get("/api/sites/{site_id}/logs")
def site_logs(site_id: str, limit: int = 100, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    _authorize(site_id, authorization)
    limit = max(1, min(250, limit))
    events = store.list("issue_log", {"site_id": site_id})
    events.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return {"site_id": site_id, "events": [_public_event(event) for event in events[:limit]], "append_only": True}


@app.get("/api/sites/{site_id}/ledger")
def site_ledger(site_id: str, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    site = _authorize(site_id, authorization)
    saved = store.get("site_state", {"site_id": site_id, "state_key": "latest_plan"})
    plan = saved.get("plan", {}) if saved else {}
    zone = ZoneInfo(str(site.get("timezone", "UTC")))
    local_date = _now().astimezone(zone).date().isoformat()
    points = [point for point in plan.get("points", []) if point.get("in_shift") and str(point.get("local_time", ""))[:10] == local_date]
    unique: dict[str, dict[str, Any]] = {}
    for point in points:
        window_id = point.get("rest_window_id")
        if point.get("activity") != "rest" or not window_id or window_id in unique:
            continue
        key = aggregate_key(site_id, str(window_id))
        aggregate = public_aggregate(store.get("rest_confirms", {"rest_key": key}))
        ack = store.get("acks", {"alert_id": f"rest-{key}"})
        unique[str(window_id)] = {
            "window": point,
            "aggregate": aggregate,
            "supervisor_acknowledged": bool(ack),
            "status": combined_rest_status(bool(ack), aggregate),
        }
    all_events = store.list("issue_log", {"site_id": site_id})
    today_events = []
    for event in all_events:
        try:
            event_date = datetime.fromisoformat(str(event.get("created_at", "")).replace("Z", "+00:00")).astimezone(zone).date().isoformat()
        except ValueError:
            continue
        if event_date == local_date:
            today_events.append(event)
    result = build_ledger(site_id, plan_points=points, events=today_events, rest_windows=list(unique.values()), recorded_date=local_date)
    archived = store.get("site_state", {"site_id": site_id, "state_key": "latest_backtest"})
    if archived and archived.get("result"):
        result["latest_backtest"] = archived["result"]
    return result


@app.get("/api/sites/{site_id}/certificate")
def site_certificate(site_id: str, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    site = _authorize(site_id, authorization)
    ledger_data = site_ledger(site_id, authorization=authorization)
    date_val = str(ledger_data.get("date", _now().date().isoformat()))
    cert_id = f"cert-{hashlib.sha256(f'{site_id}|{date_val}'.encode()).hexdigest()[:16]}"
    payload = {
        "certificate_id": cert_id,
        "site_id": site_id,
        "site_name": site.get("name", "Site"),
        "date": date_val,
        "heat_risk_hours": float(ledger_data.get("heat_risk_hours", 0) or 0),
        "rest_minutes_prescribed": int(ledger_data.get("rest_minutes_prescribed", 0) or 0),
        "rest_minutes_confirmed": int(ledger_data.get("rest_minutes_confirmed_by_both", 0) or 0),
        "issued_at": _now().isoformat(),
        "issuer": "ShiftShield Verified Rest Record",
    }
    canonical = json.dumps(payload, sort_keys=True)
    signature = hmac.new(b"shiftshield-heat-cert-v1", canonical.encode(), hashlib.sha256).hexdigest()
    cert_record = {
        **payload,
        "signature": signature,
        "verification_url": f"/verify/{cert_id}",
    }
    store.put("site_state", {
        "site_id": site_id,
        "state_key": f"certificate:{cert_id}",
        "certificate": cert_record,
    })
    return cert_record


@app.get("/api/certificates/{certificate_id}")
def verify_certificate(certificate_id: str) -> dict[str, Any]:
    records = store.list("site_state")
    found = next((item.get("certificate") for item in records if item.get("state_key") == f"certificate:{certificate_id}"), None)
    if not found:
        raise HTTPException(status_code=404, detail={"error": "certificate_not_found", "message": "Certificate not found."})
    to_verify = {k: v for k, v in found.items() if k not in {"signature", "verification_url"}}
    canonical = json.dumps(to_verify, sort_keys=True)
    expected_sig = hmac.new(b"shiftshield-heat-cert-v1", canonical.encode(), hashlib.sha256).hexdigest()
    is_valid = hmac.compare_digest(str(found.get("signature", "")), expected_sig)
    return {
        "valid": is_valid,
        "certificate": found,
        "status": "cryptographically_verified" if is_valid else "tampered_or_invalid",
    }


@app.post("/api/sites/{site_id}/backtest")
def site_backtest(site_id: str, request: HistoricalBacktestRequest, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    site = _authorize(site_id, authorization)
    try:
        archive = historical_15m(
            float(site["latitude"]), float(site["longitude"]),
            start_date=request.start_date.isoformat(), end_date=request.end_date.isoformat(),
            timezone_name=str(site.get("timezone", "UTC")),
        )
        result = run_historical_comparison(
            site, archive,
            baseline_threshold_c=request.baseline_threshold_c,
            baseline_source=request.baseline_source,
            start_date=request.start_date.isoformat(), end_date=request.end_date.isoformat(),
        )
    except ForecastUnavailable as exc:
        raise HTTPException(status_code=503, detail={"error": "archive_unavailable", "message": str(exc)}) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail={"error": "backtest_invalid", "message": str(exc)}) from exc
    now = _now().isoformat()
    summary = {key: value for key, value in result.items() if key != "timeline"}
    store.put("issue_log", {
        "site_id": site_id, "issue_id": f"backtest-{uuid.uuid4()}",
        "event_type": "historical_backtest", "created_at": now,
        "profile_version": site.get("profile_version"), "metrics": summary,
    }, append_only=True)
    store.put("site_state", {"site_id": site_id, "state_key": "latest_backtest", "result": result, "updated_at": now})
    return result


@app.get("/api/sites/{site_id}/rest-windows")
def site_rest_windows(site_id: str, limit: int = 24, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    _authorize(site_id, authorization)
    saved = store.get("site_state", {"site_id": site_id, "state_key": "latest_plan"})
    if not saved or not saved.get("plan"):
        return {"site_id": site_id, "windows": []}
    now = _now()
    points = saved["plan"].get("points", [])
    unique: dict[str, dict[str, Any]] = {}
    for point in points:
        window_id = point.get("rest_window_id")
        if not window_id or window_id in unique:
            continue
        try:
            start = datetime.fromisoformat(str(point["rest_window_start"]).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(point["rest_window_end"]).replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if end < now - timedelta(hours=2) or start > now + timedelta(hours=8):
            continue
        key = aggregate_key(site_id, str(window_id))
        aggregate = public_aggregate(store.get("rest_confirms", {"rest_key": key}))
        ack = store.get("acks", {"alert_id": f"rest-{key}"})
        unique[str(window_id)] = {
            "window": {name: point.get(name) for name in ("rest_window_id", "rest_window_start", "rest_window_end", "band", "label", "work_minutes_per_hour", "rest_minutes_per_hour")},
            "aggregate": aggregate,
            "supervisor_acknowledged": bool(ack),
            "status": combined_rest_status(bool(ack), aggregate),
        }
    rows = sorted(unique.values(), key=lambda row: str(row["window"]["rest_window_start"]))[:max(1, min(48, limit))]
    return {"site_id": site_id, "windows": rows, "disclaimer": "Supervisor acknowledgement is a self-report, and QR counts are anonymous aggregates—not proof."}


@app.post("/api/sites/{site_id}/rest-windows/{window_id}/ack")
def acknowledge_rest_window(site_id: str, window_id: str, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    _authorize(site_id, authorization)
    point = _event_window(site_id, window_id)
    if not point or point.get("activity") != "rest":
        raise HTTPException(status_code=404, detail={"error": "rest_window_not_found", "message": "This is not an issued rest window for the current plan."})
    start_text = str(point.get("rest_window_start", ""))
    end_text = str(point.get("rest_window_end", ""))
    try:
        start = datetime.fromisoformat(start_text.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"error": "rest_window_invalid", "message": "The issued break window has no valid start/end time."}) from exc
    now = _now()
    if start > now:
        raise HTTPException(status_code=409, detail={"error": "rest_window_not_started", "message": "Supervisor break-start acknowledgement is available at the scheduled rest start."})
    if now - end > timedelta(hours=12):
        raise HTTPException(status_code=410, detail={"error": "rest_window_expired", "message": "This break window is too old to acknowledge."})
    key = aggregate_key(site_id, window_id)
    ack_id = f"rest-{key}"
    record = {"alert_id": ack_id, "site_id": site_id, "window_id": window_id, "record_type": "supervisor_break_started", "acknowledged_at": now.isoformat(), "source": "supervisor_self_report"}
    created = store.put("acks", record, append_only=True)
    if created:
        store.put("issue_log", {"site_id": site_id, "issue_id": f"rest-supervisor-{key}", "event_type": "supervisor_break_started", "window_id": window_id, "created_at": now.isoformat(), "record_type": "self_report"}, append_only=True)
    aggregate = public_aggregate(store.get("rest_confirms", {"rest_key": key}))
    return {"acknowledged": created, "already_acknowledged": not created, "status": combined_rest_status(True, aggregate), "disclaimer": "Supervisor acknowledgement is a self-report; it does not independently prove a break occurred."}


@app.get("/api/sites/{site_id}/compliance")
def site_compliance(site_id: str, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    site = _authorize(site_id, authorization)
    saved = store.get("site_state", {"site_id": site_id, "state_key": "latest_plan"})
    physiological = (saved or {}).get("plan", {}).get("current") or {"band": "unknown", "work_minutes_per_hour": None, "rest_minutes_per_hour": None}
    plans = [item for item in store.list("rulebooks", {"site_id": site_id}) if item.get("record_type") == "plan"]
    active_plan = next((item for item in reversed(plans) if item.get("status") in {"uploaded", "candidates_ready", "extraction_unavailable"}), None)
    rules = approved_rules(str(active_plan["plan_id"]), store_obj=store) if active_plan else []
    combined = apply_stricter_constraints(physiological, rules)
    local_date = _now().astimezone(ZoneInfo(str(site.get("timezone", "UTC")))).date().isoformat()
    return daily_compliance(site, combined, rules, evidence={"date": local_date})


@app.get("/api/compare")
def compare_sites(site_a: str, site_b: str, authorization_a: str | None = Header(default=None, alias="X-Site-A-Authorization"), authorization_b: str | None = Header(default=None, alias="X-Site-B-Authorization")) -> dict[str, Any]:
    first = _authorize(site_a, authorization_a)
    second = _authorize(site_b, authorization_b)
    state_a = store.get("site_state", {"site_id": site_a, "state_key": "latest_plan"})
    state_b = store.get("site_state", {"site_id": site_b, "state_key": "latest_plan"})
    plan_a = (state_a or {}).get("plan")
    plan_b = (state_b or {}).get("plan")
    if not plan_a or not plan_b:
        raise HTTPException(status_code=409, detail={"error": "compare_requires_plans", "message": "Refresh both site plans before comparing them."})
    by_time_b = {point["time"]: point for point in plan_b.get("points", [])}
    rows = []
    for point in plan_a.get("points", []):
        other = by_time_b.get(point["time"])
        if other:
            rows.append({"time": point["time"], "site_a_wbgt_c": point["wbgt_c"], "site_a_band": point["band"], "site_b_wbgt_c": other["wbgt_c"], "site_b_band": other["band"]})
    return {"site_a": {"site_id": site_a, "name": first.get("name")}, "site_b": {"site_id": site_b, "name": second.get("name")}, "shared_interval_count": len(rows), "rows": rows, "synthetic": bool(first.get("demo_fixture") and second.get("demo_fixture")), "warning": "Site adjustments are provisional demo assumptions; comparison is not a field measurement."}


@app.post("/api/ack")
def acknowledge_alert(request: AckRequest) -> dict[str, Any]:
    try:
        result = acknowledge(request.token, store_obj=store)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_acknowledgement", "message": str(exc)}) from exc
    return result


@app.get("/api/ack/{token}")
def inspect_acknowledgement(token: str) -> dict[str, Any]:
    # GET is deliberately read-only so link scanners cannot consume one-use acknowledgements.
    try:
        payload = verify_ack_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"error": "invalid_acknowledgement", "message": str(exc)}) from exc
    issued = store.get("issue_log", {"site_id": payload["site_id"], "issue_id": payload["alert_id"]})
    if not issued:
        raise HTTPException(status_code=404, detail={"error": "alert_not_found", "message": "This link is not bound to a stored alert."})
    ack = store.get("acks", {"alert_id": payload["alert_id"]})
    return {"valid": True, "already_acknowledged": bool(ack), "alert": {key: issued.get(key) for key in ("alert_id", "alert_type", "from_band", "to_band", "window_start", "payload", "created_at")}}


@app.get("/api/rest/{site_code}")
def worker_rest_context(site_code: str) -> dict[str, Any]:
    site = _site_by_code_or_404(site_code)
    return _rest_context(site)


@app.post("/api/rest/{site_code}")
def worker_rest_submit(site_code: str, request: RestSubmission) -> dict[str, Any]:
    site = _site_by_code_or_404(site_code)
    point = _event_window(str(site["site_id"]), request.window_id)
    eligible = eligible_rest_window([point] if point else [], request.window_id)
    if not point or not eligible:
        raise HTTPException(status_code=409, detail={"error": "rest_window_closed", "message": "This is not an active issued break window. No response was recorded."})
    aggregate = submit_aggregate(
        str(site["site_id"]), request.window_id,
        break_received=request.break_received,
        water_available=request.water_available,
        shade_available=request.shade_available,
        symptoms=request.symptoms,
    )
    threshold = int(THRESHOLDS["symptom_tightening"]["reports_to_tighten"])
    if aggregate.get("symptom_tightening") and point.get("band"):
        from_band = str(point["band"])
        to_band = one_band_stricter(from_band)
        until = (_now() + timedelta(hours=1)).isoformat()
        store.put("site_state", {"site_id": site["site_id"], "state_key": "symptom_floor", "symptom_band_floor": to_band, "symptom_floor_until": until, "trigger_window_id": request.window_id})
        issue_alert(
            site,
            shift_date=str(point.get("local_time", _now().isoformat()))[:10],
            from_band=from_band,
            to_band=to_band,
            window_start=f"{request.window_id}:symptom-threshold-{threshold}",
            alert_type="symptom_tightening",
            payload={"reason": "The configured aggregate symptom threshold was reached. This can only tighten the schedule; a supervisor should check conditions and follow official first aid guidance.", "work_minutes_per_hour": THRESHOLDS["band_actions"][to_band]["work_minutes_per_hour"], "rest_minutes_per_hour": THRESHOLDS["band_actions"][to_band]["rest_minutes_per_hour"], "source_versions": {"thresholds": THRESHOLDS["version"]}},
        )
    ack_key = f"rest-{aggregate_key(str(site['site_id']), request.window_id)}"
    supervisor_ack = store.get("acks", {"alert_id": ack_key})
    return {
        "accepted": True,
        "aggregate": aggregate,
        "combined_status": combined_rest_status(bool(supervisor_ack), aggregate),
        "message": "Response recorded only in anonymous aggregate counts.",
        "disclaimer": "This aggregate is not identity verification or proof the break occurred.",
    }


@app.get("/api/demo")
def demo_manifest() -> dict[str, Any]:
    if not DEMO_MODE:
        raise HTTPException(status_code=404, detail={"error": "demo_disabled", "message": "The replay is available only in demo mode."})
    sites = seed_demo(store)
    return {
        "fixture_version": REPLAY_FIXTURE_VERSION,
        "sites": [_public_site(site) for site in sites],
        "steps": REPLAY_STEPS,
        "disclaimer": "Synthetic deterministic replay only; values are not current weather, field readings, approved local policy or validated medical guidance.",
        "bedrock_configured": bool(os.getenv("BEDROCK_MODEL_ID")),
    }


@app.post("/api/demo/start")
def demo_start() -> dict[str, Any]:
    if not DEMO_MODE:
        raise HTTPException(status_code=404, detail={"error": "demo_disabled", "message": "The replay is available only in demo mode."})
    return start_replay(store_obj=store)


@app.get("/api/demo/{run_id}")
def demo_state(run_id: str) -> dict[str, Any]:
    if not DEMO_MODE:
        raise HTTPException(status_code=404, detail={"error": "demo_disabled", "message": "The replay is available only in demo mode."})
    try:
        return replay_state(run_id, store)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "replay_not_found", "message": "Replay run not found."}) from exc


@app.get("/api/demo/{run_id}/dashboard")
def demo_dashboard(run_id: str) -> dict[str, Any]:
    if not DEMO_MODE:
        raise HTTPException(status_code=404, detail={"error": "demo_disabled", "message": "The replay is available only in demo mode."})
    try:
        return replay_dashboard(run_id, store)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "replay_not_found", "message": "Replay run not found."}) from exc


@app.get("/api/demo/{run_id}/compliance")
def demo_compliance(run_id: str) -> dict[str, Any]:
    if not DEMO_MODE:
        raise HTTPException(status_code=404, detail={"error": "demo_disabled", "message": "The replay is available only in demo mode."})
    try:
        return replay_compliance(run_id, store)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "replay_not_found", "message": "Replay run not found."}) from exc


@app.get("/api/demo/{run_id}/worker")
def demo_worker_page_context(run_id: str) -> dict[str, Any]:
    if not DEMO_MODE:
        raise HTTPException(status_code=404, detail={"error": "demo_disabled", "message": "The replay is available only in demo mode."})
    try:
        return demo_worker_context(run_id, store)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "replay_not_found", "message": "Replay run not found."}) from exc


@app.post("/api/demo/{run_id}/step")
def demo_step(run_id: str, request: ReplayAction) -> dict[str, Any]:
    if not DEMO_MODE:
        raise HTTPException(status_code=404, detail={"error": "demo_disabled", "message": "The replay is available only in demo mode."})
    try:
        result = record_replay_step(run_id, request.event_id, store_obj=store)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "replay_not_found", "message": "Replay run not found."}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": "invalid_replay_step", "message": str(exc)}) from exc
    return result


@app.post("/api/demo/{run_id}/break-started")
def demo_break_started(run_id: str) -> dict[str, Any]:
    if not DEMO_MODE:
        raise HTTPException(status_code=404, detail={"error": "demo_disabled", "message": "The replay is available only in demo mode."})
    try:
        return record_demo_break_started(run_id, store)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "replay_not_found", "message": "Replay run not found."}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"error": "break_not_open", "message": str(exc)}) from exc


@app.post("/api/demo/{run_id}/worker")
def demo_worker_submit(run_id: str, request: RestSubmission) -> dict[str, Any]:
    if not DEMO_MODE:
        raise HTTPException(status_code=404, detail={"error": "demo_disabled", "message": "The replay is available only in demo mode."})
    try:
        context = demo_worker_context(run_id, store)
        active = context.get("active_window")
        if not context.get("eligible") or not active:
            raise HTTPException(status_code=409, detail={"error": "demo_window_closed", "message": "Reach the synthetic 11:30 rest step first."})
        if request.window_id != active.get("rest_window_id"):
            raise HTTPException(status_code=409, detail={"error": "invalid_demo_window", "message": "This response is not bound to the active replay window."})
        result = submit_demo_worker(
            run_id,
            break_received=request.break_received,
            water_available=request.water_available,
            shade_available=request.shade_available,
            symptoms=list(request.symptoms),
            store_obj=store,
        )
        return {**result, "disclaimer": context["disclaimer"]}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "replay_not_found", "message": "Replay run not found."}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail={"error": "demo_window_closed", "message": str(exc)}) from exc


@app.get("/api/rulebooks/{site_id}")
def list_rulebooks(site_id: str, authorization: str | None = Header(default=None, alias="Authorization")) -> dict[str, Any]:
    _authorize(site_id, authorization)
    records = store.list("rulebooks", {"site_id": site_id})
    records.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return {"site_id": site_id, "plans": [item for item in records if item.get("record_type") == "plan"], "candidates": [item for item in records if item.get("record_type") != "plan"], "legal_advice": False}


@app.post("/api/rulebooks/{site_id}")
async def upload_rulebook(
    site_id: str,
    file: UploadFile = File(...),
    plan_version: str = Form(..., min_length=1, max_length=160),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    site = _authorize(site_id, authorization)
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail={"error": "pdf_required", "message": "Upload a PDF action plan."})
    content = await file.read(MAX_PDF_BYTES + 1)
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail={"error": "pdf_too_large", "message": "PDF must be no larger than 10 MiB."})
    try:
        pages = read_pdf_pages(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": "pdf_read_failed", "message": str(exc)}) from exc
    plan_id = str(uuid.uuid4())
    try:
        stored_file = store_pdf(plan_id, site_id, content)
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"error": "private_storage_unavailable", "message": f"Could not store the private PDF ({type(exc).__name__}). No obligations were approved."}) from exc
    created = _now().isoformat()
    plan_record: dict[str, Any] = {
        "site_id": site_id, "plan_id": plan_id, "rule_id": "__plan__", "record_type": "plan",
        "plan_version": plan_version.strip(), "file_name": (file.filename or "action-plan.pdf")[:120],
        "page_count": len(pages), "searchable_page_count": sum(bool(text.strip()) for text in pages.values()),
        "object_key": stored_file["object_key"], "storage": stored_file["storage"],
        "created_at": created, "status": "uploaded", "approved_obligation_count": 0,
    }
    store.put("rulebooks", plan_record)
    if os.getenv("RULEBOOK_STATE_MACHINE_ARN") and os.getenv("BEDROCK_MODEL_ID"):
        try:
            execution_arn = start_rulebook_workflow(
                site_id, plan_id, stored_file["object_key"], plan_version.strip()
            )
        except Exception as exc:
            plan_record["status"] = "extraction_failed"
            plan_record["extraction_message"] = f"Workflow could not be started ({type(exc).__name__}); no obligations were approved."
            store.put("rulebooks", plan_record)
            return {"plan": plan_record, "candidates": [], "warning": plan_record["extraction_message"]}
        plan_record.update({"status": "queued", "workflow_execution_arn": execution_arn})
        store.put("rulebooks", plan_record)
        return {"plan": plan_record, "candidates": [], "warning": "Extraction is queued. Candidates remain unapproved until each exact source-page quote is reviewed."}
    if os.getenv("BEDROCK_MODEL_ID") and len(pages) > 1:
        plan_record["status"] = "extraction_unavailable"
        plan_record["extraction_message"] = "Configure the asynchronous Step Functions workflow for multi-page extraction. No rules were approved."
        store.put("rulebooks", plan_record)
        return {"plan": plan_record, "candidates": [], "warning": plan_record["extraction_message"]}
    try:
        candidates = invoke_candidates(pages, plan_version=plan_version.strip())
    except BedrockUnavailable as exc:
        plan_record["status"] = "extraction_unavailable"
        plan_record["extraction_message"] = str(exc)
        store.put("rulebooks", plan_record)
        return {"plan": plan_record, "candidates": [], "warning": str(exc), "core_decision_engine_available": True}
    for candidate in candidates:
        candidate.update({"site_id": site_id, "record_type": "candidate"})
    persist_candidates(plan_id, candidates)
    plan_record["status"] = "candidates_ready" if candidates else "no_candidates_found"
    plan_record["candidate_count"] = sum(bool(item.get("quote_verified")) for item in candidates)
    store.put("rulebooks", plan_record)
    return {"plan": plan_record, "candidates": candidates, "warning": "AI output is only a candidate. Every quote is independently checked and every obligation requires human approval."}


@app.post("/api/rulebooks/{site_id}/{plan_id}/{rule_id}/decision")
def decide_rule(
    site_id: str,
    plan_id: str,
    rule_id: str,
    decision: RuleDecision,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    _authorize(site_id, authorization)
    try:
        candidate = approve_candidate(
            plan_id, rule_id,
            action=decision.action,
            reviewer_name=f"{decision.reviewer_role} (role label; no reviewer name stored)",
            requirement_text=decision.requirement_text,
            applies_when=decision.applies_when,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail={"error": "candidate_not_found", "message": str(exc)}) from exc
    except (InvalidQuote, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"error": "candidate_rejected", "message": str(exc)}) from exc
    if not candidate.get("quote_verified"):
        raise HTTPException(status_code=422, detail={"error": "quote_not_verified", "message": "A source-page quote must verify before approval."})
    candidate["site_id"] = site_id
    candidate["record_type"] = "candidate"
    approved_count = len(approved_rules(plan_id, store_obj=store))
    plan = store.get("rulebooks", {"plan_id": plan_id, "rule_id": "__plan__"})
    if plan:
        plan.update({
            "status": "approved_rules_present" if approved_count else "candidates_ready",
            "approved_obligation_count": approved_count,
        })
        store.put("rulebooks", plan)
    obligation_key = f"{plan_id}:{rule_id}:{candidate.get('reviewed_at', _now().isoformat())}"
    store.put("obligation_log", {
        "site_id": site_id,
        "obligation_key": obligation_key,
        "event_type": f"rule_candidate_{decision.action}",
        "plan_id": plan_id,
        "rule_id": rule_id,
        "source_page": candidate.get("pdf_page_number"),
        "source_quote_sha256": hashlib.sha256(str(candidate.get("exact_quote", "")).encode("utf-8")).hexdigest(),
        "plan_version": candidate.get("plan_version"),
        "reviewer_role": decision.reviewer_role,
        "human_approved": bool(candidate.get("human_approved")),
        "reviewed_at": candidate.get("reviewed_at"),
    }, append_only=True)
    return {"candidate": candidate, "human_gate": "recorded", "ai_controls_schedule": False}


@app.exception_handler(Exception)
async def unexpected_error(request, exc: Exception):
    # Never return tracebacks, database internals, AWS errors or submitted request bodies.
    return JSONResponse(status_code=500, content={"detail": {"error": "internal_error", "message": f"The request could not be completed ({type(exc).__name__})."}})
