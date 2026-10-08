"""Async Step Functions task for private, candidate-only rulebook extraction."""
from __future__ import annotations

import os
from typing import Any

import boto3
from aws_lambda_powertools import Logger

from .config import AWS_REGION
from .rulebook import BedrockUnavailable, invoke_candidates, persist_candidates, read_pdf_pages
from .store import store

logger = Logger(service="shiftshield-rulebook-worker")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    site_id = str(event.get("site_id", ""))
    plan_id = str(event.get("plan_id", ""))
    object_key = str(event.get("object_key", ""))
    plan_version = str(event.get("plan_version", ""))
    if not site_id or not plan_id or not object_key or not plan_version:
        raise ValueError("Step Functions rulebook input is incomplete")

    plan_key = {"plan_id": plan_id, "rule_id": "__plan__"}
    plan = store.get("rulebooks", plan_key)
    if not plan:
        raise ValueError("Rulebook plan record does not exist")
    if plan.get("status") in {"candidates_ready", "no_candidates_found", "approved_rules_present"}:
        return {"status": str(plan["status"]), "plan_id": plan_id, "already_complete": True}

    store.put("rulebooks", {**plan, "status": "processing", "processing_started_at": _utc_now()})
    try:
        bucket = os.getenv("RULEBOOK_BUCKET")
        if not bucket:
            raise RuntimeError("Private rulebook storage is not configured")
        response = boto3.client("s3", region_name=AWS_REGION).get_object(Bucket=bucket, Key=object_key)
        content = response["Body"].read(10 * 1024 * 1024 + 1)
        pages = read_pdf_pages(content)
        candidates = invoke_candidates(pages, plan_version=plan_version)
        for candidate in candidates:
            candidate.update({"site_id": site_id, "record_type": "candidate"})
        persist_candidates(plan_id, candidates, store_obj=store)
        verified_count = sum(bool(item.get("quote_verified")) for item in candidates)
        updated = {
            **plan,
            "status": "candidates_ready" if verified_count else "no_candidates_found",
            "candidate_count": verified_count,
            "page_count": len(pages),
            "searchable_page_count": sum(bool(text.strip()) for text in pages.values()),
            "extraction_completed_at": _utc_now(),
            "approved_obligation_count": int(plan.get("approved_obligation_count", 0)),
        }
        store.put("rulebooks", updated)
        logger.info("rulebook_extraction_completed", site_id=site_id, plan_id=plan_id, verified_candidate_count=verified_count)
        return {"status": updated["status"], "plan_id": plan_id, "verified_candidate_count": verified_count}
    except (BedrockUnavailable, ValueError, RuntimeError) as exc:
        failed = {
            **plan,
            "status": "extraction_failed",
            "extraction_message": f"Extraction stopped ({type(exc).__name__}); no obligation was approved.",
            "extraction_completed_at": _utc_now(),
        }
        store.put("rulebooks", failed)
        logger.warning("rulebook_extraction_stopped", site_id=site_id, plan_id=plan_id, error_type=type(exc).__name__)
        return {"status": "extraction_failed", "plan_id": plan_id, "error_type": type(exc).__name__}


def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
