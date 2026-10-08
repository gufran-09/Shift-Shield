"""Deterministic, versioned work/rest classifier; AI is never in this path."""
from __future__ import annotations

from typing import Any

from .config import THRESHOLDS

BAND_ORDER = {"normal": 0, "caution": 1, "high": 2, "very_high": 3}


def _acclimatization_key(value: str | None) -> str:
    return "acclimatized" if value == "acclimatized" else "unacclimatized"


def clothing_adjustment(ppe: str | None) -> tuple[float, str | None]:
    rows = THRESHOLDS["clothing_adjustments_c"]
    key = ppe if ppe in rows else "heavy"
    warning = None
    if key == "heavy":
        warning = "Generic heavy PPE is mapped to a conservative partial-impermeability adjustment; confirm the garment type."
    elif key == "impermeable":
        warning = "WBGT is not appropriate for a fully impermeable encapsulating ensemble; stop and obtain a qualified assessment."
    return float(rows[key]["degrees_c"]), warning


def select_band(wbgt_for_thresholds_c: float, intensity: str, acclimatization: str | None = None) -> dict[str, Any]:
    intensity_key = intensity if intensity in THRESHOLDS["workload_classes"] else "very_heavy"
    acclimatization_key = _acclimatization_key(acclimatization)
    group = THRESHOLDS["curves_by_acclimatization"][acclimatization_key]
    row = group["class_rows"][intensity_key]
    limits = {int(minutes): float(temp) for minutes, temp in row["wbgt_c_at_work_minutes_per_hour"].items()}
    value = float(wbgt_for_thresholds_c)

    # A tie goes to the stricter schedule. These are source-curve crossings,
    # not an official NIOSH four-band terminology.
    if value >= limits[30]:
        band = "very_high"
    elif value >= limits[45]:
        band = "high"
    elif value >= limits[60]:
        band = "caution"
    else:
        band = "normal"
    action = dict(THRESHOLDS["band_actions"][band])
    exceeds_final_curve = value >= limits[15]
    action.update({
        "band": band,
        "source_curve": group["curve"],
        "source_figure": group["source_figure"],
        "source_page": group["source_page"],
        "thresholds_c": {str(minutes): temperature for minutes, temperature in sorted(limits.items(), reverse=True)},
        "workload_kcal_per_hour": row["workload_kcal_per_hour"],
        "workload_class": intensity_key,
        "acclimatization": acclimatization_key,
        "threshold_version": THRESHOLDS["version"],
        "water_guidance": THRESHOLDS["water_guidance"],
        "exceeds_final_15_min_curve": exceeds_final_curve,
        "status_label": THRESHOLDS["status"],
        "professional_review": THRESHOLDS["professional_review"],
    })
    if exceeds_final_curve:
        action["guidance"] += " The value is at/above the final 15-minute NIOSH curve; no work/rest duration is supported above it. Reschedule and stop non-essential heavy work."
        action["safe_schedule_supported"] = False
    else:
        action["safe_schedule_supported"] = True
    return action


def make_plan(point: dict[str, Any], site: dict[str, Any]) -> dict[str, Any]:
    ppe_c, ppe_warning = clothing_adjustment(site.get("ppe", "normal"))
    wbgt_for_thresholds = float(point["conservative_wbgt_c"]) + ppe_c
    schedule = select_band(wbgt_for_thresholds, site.get("intensity", "heavy"), site.get("acclimatization", "unknown"))
    schedule["wbgt_c"] = point["wbgt_c"]
    schedule["margin_c"] = point["margin_c"]
    schedule["conservative_wbgt_c"] = point["conservative_wbgt_c"]
    schedule["clothing_adjustment_c"] = ppe_c
    schedule["wbgt_for_thresholds_c"] = round(wbgt_for_thresholds, 2)
    schedule["ppe_warning"] = ppe_warning
    schedule["data_status"] = point.get("data_status", "fresh")
    schedule["source_resolution"] = point.get("source_resolution", "hourly forecast interpolated to 15-minute intervals")
    schedule["is_demo_only"] = True
    return schedule


def stricter_band(left: str, right: str) -> str:
    return left if BAND_ORDER.get(left, 3) >= BAND_ORDER.get(right, 3) else right


def one_band_stricter(band: str) -> str:
    ordered = ["normal", "caution", "high", "very_high"]
    return ordered[min(BAND_ORDER.get(band, 3) + 1, 3)]
