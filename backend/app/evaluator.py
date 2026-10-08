"""EventBridge scheduled evaluator. It calls the same deterministic plan path as the dashboard."""
from __future__ import annotations

from typing import Any

from aws_lambda_powertools import Logger

from .alerts import maybe_send_ack_reminder
from .config import DEMO_MODE
from .main import _calculate_profile
from .store import store

logger = Logger(service="shiftshield-evaluator")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    if DEMO_MODE:
        logger.info("scheduled_evaluation_skipped_in_demo_mode")
        return {"status": "skipped_demo_mode", "evaluated": 0}
    sites = store.list("sites", {"active": True})
    results: list[dict[str, str]] = []
    for site in sites:
        try:
            plan = _calculate_profile(site, persist=True)
            try:
                maybe_send_ack_reminder(site)
            except Exception as reminder_error:
                logger.exception("ack_reminder_failed", site_id=str(site["site_id"]), error_type=type(reminder_error).__name__)
            results.append({"site_id": str(site["site_id"]), "status": "evaluated", "current_band": str((plan.get("current") or {}).get("band", "unknown"))})
        except Exception as exc:
            # Do not log contact addresses, tokens, uploaded PDF text or request bodies.
            logger.exception("site_evaluation_failed", site_id=str(site.get("site_id", "unknown")), error_type=type(exc).__name__)
            results.append({"site_id": str(site.get("site_id", "unknown")), "status": "failed", "error_type": type(exc).__name__})
    logger.info("scheduled_evaluation_finished", evaluated=len(sites), failed=sum(item["status"] == "failed" for item in results))
    return {"status": "complete", "evaluated": len(sites), "results": results}
