"""Aggregate QR rest-confirmation rules. Never persist an individual response."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from collections.abc import Sequence
from typing import Any

from .config import THRESHOLDS
from .store import Store, store


COUNTER_FIELDS = {
    "break_received": "break_yes",
    "break_missed": "break_no",
    "water_yes": "water_yes",
    "water_no": "water_no",
    "shade_yes": "shade_yes",
    "shade_no": "shade_no",
    "symptom_dizzy": "symptom_dizzy",
    "symptom_headache": "symptom_headache",
    "symptom_cramps": "symptom_cramps",
}


def aggregate_key(site_id: str, window_id: str) -> str:
    return hashlib.sha256(f"{site_id}|{window_id}".encode()).hexdigest()


def submit_aggregate(
    site_id: str,
    window_id: str,
    *,
    break_received: bool,
    water_available: bool | None,
    shade_available: bool | None,
    symptoms: Sequence[str],
    store_obj: Store = store,
) -> dict[str, Any]:
    key = aggregate_key(site_id, window_id)
    increments = {"total_responses": 1}
    increments["break_yes" if break_received else "break_no"] = 1
    if water_available is not None:
        increments["water_yes" if water_available else "water_no"] = 1
    if shade_available is not None:
        increments["shade_yes" if shade_available else "shade_no"] = 1
    symptom_values = set(symptoms) - {"ok"}
    if symptom_values.intersection({"dizzy", "headache", "cramps"}):
        increments["symptom_reports"] = 1
        for symptom in symptom_values.intersection({"dizzy", "headache", "cramps"}):
            increments[f"symptom_{symptom}"] = 1
    values = store_obj.increment(
        "rest_confirms", {"rest_key": key}, increments,
        {"site_id": site_id, "window_id": window_id, "updated_at": datetime.now(timezone.utc).isoformat()},
    )
    # No submitted answer, timestamp, client token, name, phone, IP or device fingerprint is stored.
    return public_aggregate(values)


def public_aggregate(values: dict[str, Any] | None) -> dict[str, Any]:
    if not values:
        return {
            "total_responses": 0,
            "split_visible": False,
            "majority": None,
            "symptom_tightening": False,
            "water_yes_count": None,
            "shade_yes_count": None,
        }
    total = int(values.get("total_responses", 0))
    split_visible = total >= 3
    yes = int(values.get("break_yes", 0))
    no = int(values.get("break_no", 0))
    symptoms = int(values.get("symptom_reports", 0))
    threshold = int(THRESHOLDS["symptom_tightening"]["reports_to_tighten"])
    out: dict[str, Any] = {
        "total_responses": total,
        "split_visible": split_visible,
        "majority": None,
        "symptom_tightening": symptoms >= threshold,
        "symptom_reports": symptoms if split_visible else None,
        "symptom_threshold": threshold,
        "threshold_status": THRESHOLDS["symptom_tightening"]["status"],
        "water_yes_count": int(values.get("water_yes", 0)) if split_visible else None,
        "water_no_count": int(values.get("water_no", 0)) if split_visible else None,
        "shade_yes_count": int(values.get("shade_yes", 0)) if split_visible else None,
        "shade_no_count": int(values.get("shade_no", 0)) if split_visible else None,
    }
    if split_visible:
        out.update({"break_yes_count": yes, "break_no_count": no})
        if yes > no:
            out["majority"] = "yes"
        elif no > yes:
            out["majority"] = "no"
    return out


def combined_rest_status(supervisor_acknowledged: bool, aggregate: dict[str, Any]) -> dict[str, str]:
    total = int(aggregate.get("total_responses", 0))
    majority = aggregate.get("majority") if aggregate.get("split_visible") else None
    if supervisor_acknowledged and majority == "yes":
        return {"code": "confirmed_by_both", "label": "Confirmed by both", "tone": "good", "detail": "Supervisor acknowledged; anonymous workers mostly confirmed the break."}
    if supervisor_acknowledged and majority == "no":
        return {"code": "disputed", "label": "Disputed", "tone": "danger", "detail": "Supervisor acknowledged; anonymous workers mostly reported no break."}
    if supervisor_acknowledged:
        return {"code": "supervisor_only", "label": "Supervisor only", "tone": "warning", "detail": "Supervisor acknowledged; no worker majority is visible yet."}
    if total:
        return {"code": "no_record", "label": "No record", "tone": "muted", "detail": "Worker responses exist, but supervisor acknowledgement is missing."}
    return {"code": "no_record", "label": "No record", "tone": "muted", "detail": "Neither a supervisor acknowledgement nor worker response is recorded."}
