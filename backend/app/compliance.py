"""Deterministic compliance merger; AI candidates are never applied directly."""
from __future__ import annotations

from typing import Any

from .scheduling import BAND_ORDER, stricter_band


def approved_rules(plan_id: str, *, store_obj) -> list[dict[str, Any]]:
    return [item for item in store_obj.list("rulebooks", {"plan_id": plan_id}) if item.get("status") == "approved" and item.get("human_approved") and item.get("quote_verified")]


def apply_stricter_constraints(physiology: dict[str, Any], rules: list[dict[str, Any]]) -> dict[str, Any]:
    work = int(physiology.get("work_minutes_per_hour", 60))
    rest = int(physiology.get("rest_minutes_per_hour", 0))
    applied: list[str] = []
    manual_review: list[str] = []
    for rule in rules:
        rule_id = str(rule.get("rule_id", ""))
        max_work = rule.get("maximum_work_minutes_per_hour")
        min_rest = rule.get("minimum_rest_minutes_per_hour")
        if max_work is None and min_rest is None:
            manual_review.append(rule_id)
            continue
        if max_work is not None and int(max_work) < work:
            work = int(max_work)
            applied.append(rule_id)
        if min_rest is not None and int(min_rest) > rest:
            rest = int(min_rest)
            applied.append(rule_id)
    if work + rest > 60:
        return {
            **physiology,
            "compliance_application_supported": False,
            "compliance_conflict": "The approved policy constraints exceed 60 minutes per hour; qualified human review is required.",
            "policy_rules_applied": [],
            "manual_review_rule_ids": sorted(set(manual_review + applied)),
        }
    changed = work < int(physiology.get("work_minutes_per_hour", 60)) or rest > int(physiology.get("rest_minutes_per_hour", 0))
    return {
        **physiology,
        "work_minutes_per_hour": work,
        "rest_minutes_per_hour": rest,
        "band": stricter_band(str(physiology.get("band", "normal")), "very_high" if changed else str(physiology.get("band", "normal"))),
        "compliance_application_supported": not bool(manual_review),
        "compliance_conflict": None,
        "policy_rules_applied": sorted(set(applied)),
        "manual_review_rule_ids": sorted(set(manual_review)),
        "policy_status": "approved rules applied" if rules and not manual_review else "manual review required" if manual_review else "no approved plan loaded",
    }


def daily_compliance(site: dict[str, Any], physiological_plan: dict[str, Any], rules: list[dict[str, Any]], *, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = evidence or {}
    if not rules:
        return {
            "site_id": site["site_id"],
            "date": evidence.get("date"),
            "policy_loaded": False,
            "status": "unconfirmed",
            "message": "No action-plan document has been approved. This view does not claim legal compliance.",
            "applied_schedule": physiological_plan,
            "rows": [],
            "decision_support_only": True,
        }
    rows = []
    for rule in rules:
        rows.append({
            "obligation": rule.get("title"),
            "plan_says": rule.get("requirement_text"),
            "quote": rule.get("exact_quote"),
            "pdf_page_number": rule.get("pdf_page_number"),
            "physiology_says": f"{physiological_plan.get('work_minutes_per_hour')} work / {physiological_plan.get('rest_minutes_per_hour')} rest minutes per hour",
            "applied_today": "Human-approved rule is included in the stricter combined schedule; confirm execution in the supervisor checklist.",
            "status": "unconfirmed",
            "confirmed_by": None,
            "evidence": evidence.get(str(rule.get("rule_id"))),
            "approver": rule.get("reviewer_name"),
            "reviewed_at": rule.get("reviewed_at"),
        })
    return {
        "site_id": site["site_id"],
        "date": evidence.get("date"),
        "policy_loaded": True,
        "status": "unconfirmed" if any(row["status"] == "unconfirmed" for row in rows) else "met",
        "message": "Reading/compliance aid, not legal advice. Human review and shift evidence are required.",
        "rows": rows,
        "decision_support_only": True,
    }
