"""Alert idempotency, signed acknowledge-only links and opt-in email delivery."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3

from .config import AWS_REGION, DEMO_MODE, PUBLIC_ORIGIN
from .store import Store, store

_secret_cache: str | None = None


def _secret() -> str:
    global _secret_cache
    if _secret_cache:
        return _secret_cache
    secret_arn = os.getenv("ACK_SIGNING_SECRET_ARN")
    if secret_arn:
        response = boto3.client("secretsmanager", region_name=AWS_REGION).get_secret_value(SecretId=secret_arn)
        _secret_cache = str(response["SecretString"])
    else:
        configured = os.getenv("ACK_SIGNING_SECRET")
        if not configured and not DEMO_MODE:
            raise RuntimeError("ACK_SIGNING_SECRET_ARN must be configured outside demo mode")
        _secret_cache = configured or (secrets.token_urlsafe(48) if DEMO_MODE else "")
    if len(_secret_cache) < 24:
        raise RuntimeError("Acknowledgement signing secret is too short")
    return _secret_cache


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def sign_ack_token(*, site_id: str, alert_id: str, expires_at: int) -> str:
    payload = json.dumps({"site_id": site_id, "alert_id": alert_id, "exp": expires_at}, separators=(",", ":")).encode()
    body = _b64(payload)
    signature = _b64(hmac.new(_secret().encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def verify_ack_token(token: str) -> dict[str, Any]:
    try:
        body, supplied = token.split(".", 1)
        expected = _b64(hmac.new(_secret().encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(supplied, expected):
            raise ValueError("Invalid acknowledgement signature")
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if int(payload["exp"]) < int(time.time()):
            raise ValueError("Acknowledgement link has expired")
        return payload
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid or expired acknowledgement link") from exc


def make_idempotency_key(site_id: str, shift_date: str, from_band: str, to_band: str, window_start: str) -> str:
    material = "|".join((site_id, shift_date, from_band, to_band, window_start))
    return hashlib.sha256(material.encode()).hexdigest()


def create_email_subscription(site_id: str, email: str, *, enabled: bool) -> dict[str, Any]:
    """Send the address only to SNS; persist only its hash and subscription metadata."""
    if not enabled:
        return {"email_opt_in": False, "email_subscription_status": "off"}
    if not email or "@" not in email:
        raise ValueError("An email address is required for explicit alert opt-in")
    topic_name = f"shiftshield-site-{site_id}"[:256]
    client = boto3.client("sns", region_name=AWS_REGION)
    topic_arn = client.create_topic(Name=topic_name)["TopicArn"]
    response = client.subscribe(TopicArn=topic_arn, Protocol="email", Endpoint=email, ReturnSubscriptionArn=True)
    return {
        "sns_topic_arn": topic_arn,
        "sns_subscription_arn": response.get("SubscriptionArn"),
        "email_contact_hash": hashlib.sha256(email.strip().lower().encode()).hexdigest(),
        "email_opt_in": True,
        "email_opt_in_at": datetime.now(timezone.utc).isoformat(),
        "email_subscription_status": "pending_confirmation",
    }


def remove_email_subscription(site: dict[str, Any]) -> None:
    topic_arn = site.get("sns_topic_arn")
    subscription_arn = site.get("sns_subscription_arn")
    if not topic_arn:
        return
    client = boto3.client("sns", region_name=AWS_REGION)
    if subscription_arn and subscription_arn != "pending confirmation":
        try:
            client.unsubscribe(SubscriptionArn=subscription_arn)
        except Exception:
            # Deleting the per-site topic remains the opt-out path for pending or stale ARNs.
            pass
    client.delete_topic(TopicArn=topic_arn)


def refresh_email_subscription(site: dict[str, Any]) -> dict[str, Any]:
    """Detect user-confirmed SNS email subscription without persisting its address."""
    topic_arn = site.get("sns_topic_arn")
    expected_hash = site.get("email_contact_hash")
    if not topic_arn or not expected_hash or not site.get("email_alert_opt_in"):
        return site
    if site.get("email_subscription_status") == "confirmed":
        return site
    client = boto3.client("sns", region_name=AWS_REGION)
    token: str | None = None
    while True:
        params: dict[str, Any] = {"TopicArn": topic_arn}
        if token:
            params["NextToken"] = token
        response = client.list_subscriptions_by_topic(**params)
        for subscription in response.get("Subscriptions", []):
            endpoint = str(subscription.get("Endpoint", ""))
            digest = hashlib.sha256(endpoint.strip().lower().encode()).hexdigest()
            arn = str(subscription.get("SubscriptionArn", ""))
            if hmac.compare_digest(digest, str(expected_hash)) and arn and arn != "PendingConfirmation":
                return {**site, "sns_subscription_arn": arn, "email_subscription_status": "confirmed"}
        token = response.get("NextToken")
        if not token:
            return site


def issue_alert(
    site: dict[str, Any],
    *,
    shift_date: str,
    from_band: str,
    to_band: str,
    window_start: str,
    alert_type: str,
    payload: dict[str, Any],
    store_obj: Store = store,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    now = now or datetime.now(timezone.utc)
    site_id = str(site["site_id"])
    idempotency = make_idempotency_key(site_id, shift_date, from_band, to_band, window_start)
    ttl = int(now.timestamp()) + 48 * 3600
    if not store_obj.put("alert_keys", {"idempotency_key": idempotency, "ttl": ttl, "site_id": site_id}, append_only=True):
        return None

    alert_id = str(uuid.uuid4())
    shift_end = site.get("shift_end_utc")
    if shift_end:
        expires_at = int(datetime.fromisoformat(shift_end.replace("Z", "+00:00")).timestamp())
    else:
        expires_at = int(now.timestamp()) + 12 * 3600
    token = sign_ack_token(site_id=site_id, alert_id=alert_id, expires_at=expires_at)
    alert = {
        "site_id": site_id,
        "alert_id": alert_id,
        "issue_id": alert_id,
        "event_type": "heat_alert",
        "idempotency_key": idempotency,
        "alert_type": alert_type,
        "from_band": from_band,
        "to_band": to_band,
        "window_start": window_start,
        "created_at": now.isoformat(),
        "expires_at": expires_at,
        "ack_token": token,
        "payload": payload,
        "source_versions": payload.get("source_versions", {}),
        "margin_c": payload.get("margin_c"),
        "delivery_status": "demo_in_app_only" if DEMO_MODE else "pending",
    }
    if not store_obj.put("issue_log", alert, append_only=True):
        return None

    if not DEMO_MODE and site.get("email_opt_in") and site.get("email_subscription_status") == "confirmed" and site.get("sns_topic_arn"):
        origin = PUBLIC_ORIGIN.rstrip("/")
        if not origin:
            alert["delivery_status"] = "email_not_configured_public_origin_missing"
            return alert
        subject = f"ShiftShield: {to_band.replace('_', ' ').upper()} heat plan at {site.get('name', 'your site')}"
        message = (
            f"{payload.get('reason', 'A stricter heat-safety plan is needed.')}\n\n"
            f"Current band: {from_band}; new band: {to_band}.\n"
            f"Change time: {window_start}.\n"
            f"Work/rest: {payload.get('work_minutes_per_hour', 'see dashboard')} work / "
            f"{payload.get('rest_minutes_per_hour', 'see dashboard')} rest minutes per hour.\n\n"
            f"Acknowledge (this link only records acknowledgement): {origin}/ack/{token}\n"
            "Decision support, not medical advice. Follow official local safety guidance."
        )
        try:
            response = boto3.client("sns", region_name=AWS_REGION).publish(
                TopicArn=site["sns_topic_arn"], Subject=subject[:100], Message=message
            )
            delivery = "sns_published"
            alert["sns_message_id"] = response.get("MessageId")
        except Exception as exc:
            delivery = f"sns_error:{type(exc).__name__}"
        alert["delivery_status"] = delivery
        # Append a separate delivery-result event; the plan/message event itself is immutable.
        store_obj.put("issue_log", {
            "site_id": site_id,
            "issue_id": f"delivery-{alert_id}",
            "alert_id": alert_id,
            "event_type": "delivery_result",
            "delivery_status": delivery,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, append_only=True)
    return alert


def acknowledge(token: str, *, store_obj: Store = store) -> dict[str, Any]:
    payload = verify_ack_token(token)
    site_id = str(payload["site_id"])
    alert_id = str(payload["alert_id"])
    issued = store_obj.get("issue_log", {"site_id": site_id, "issue_id": alert_id})
    if not issued or issued.get("alert_type") is None:
        raise ValueError("This acknowledgement link is not bound to an issued site alert")
    ack = {
        "alert_id": alert_id,
        "site_id": site_id,
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
        "acknowledgement_only": True,
    }
    if not store_obj.put("acks", ack, append_only=True):
        return {"acknowledged": False, "already_acknowledged": True, "site_id": site_id, "alert_id": alert_id}
    store_obj.put("issue_log", {
        "site_id": site_id,
        "issue_id": f"ack-{uuid.uuid4()}",
        "alert_id": alert_id,
        "event_type": "supervisor_acknowledgement",
        "acknowledged_at": ack["acknowledged_at"],
    }, append_only=True)
    pending = store_obj.get("site_state", {"site_id": site_id, "state_key": "pending_alert"})
    if pending and pending.get("alert_id") == alert_id:
        store_obj.put("site_state", {**pending, "status": "acknowledged", "acknowledged_at": ack["acknowledged_at"]})
    return {"acknowledged": True, "already_acknowledged": False, "site_id": site_id, "alert_id": alert_id}


def maybe_send_ack_reminder(site: dict[str, Any], *, store_obj: Store = store, now: datetime | None = None) -> dict[str, Any] | None:
    """Send at most one reminder 20 minutes after an unacknowledged heads-up."""
    now = now or datetime.now(timezone.utc)
    pending = store_obj.get("site_state", {"site_id": str(site["site_id"]), "state_key": "pending_alert"})
    if not pending or pending.get("status", "pending") != "pending" or pending.get("reminder_sent") or not pending.get("alert_id"):
        return None
    alert_id = str(pending["alert_id"])
    issued = store_obj.get("issue_log", {"site_id": str(site["site_id"]), "issue_id": alert_id})
    if not issued or issued.get("alert_type") not in {"heads_up", "immediate_stricter_plan"}:
        return None
    if store_obj.get("acks", {"alert_id": alert_id}):
        return None
    try:
        created = datetime.fromisoformat(str(issued["created_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return None
    if (now - created).total_seconds() < 20 * 60:
        return None
    idempotency = f"ack-reminder:{alert_id}"
    if not store_obj.put("alert_keys", {"idempotency_key": idempotency, "ttl": int(now.timestamp()) + 48 * 3600, "site_id": site["site_id"], "purpose": "one_acknowledgement_reminder"}, append_only=True):
        return None
    delivery = "demo_in_app_only" if DEMO_MODE else "not_sent_no_confirmed_destination"
    try:
        if not DEMO_MODE and site.get("email_alert_opt_in") and site.get("email_subscription_status") == "confirmed" and site.get("sns_topic_arn") and PUBLIC_ORIGIN:
            token = str(issued.get("ack_token", ""))
            message = (
                f"Reminder: the ShiftShield {issued.get('to_band', 'stricter')} plan for {site.get('name', 'your site')} is still unacknowledged.\n"
                f"Change time: {pending.get('window_start', issued.get('window_start', 'see dashboard'))}.\n"
                f"Acknowledge only (does not verify a break): {PUBLIC_ORIGIN.rstrip('/')}/ack/{token}\n"
                "This is the one reminder; no further nagging will be sent. Decision support, not medical advice."
            )
            boto3.client("sns", region_name=AWS_REGION).publish(
                TopicArn=site["sns_topic_arn"], Subject=f"ShiftShield reminder: {site.get('name', 'site')}"[:100], Message=message,
            )
            delivery = "sns_reminder_published"
        event = {
            "site_id": str(site["site_id"]),
            "issue_id": f"reminder-{alert_id}",
            "alert_id": alert_id,
            "event_type": "acknowledgement_reminder",
            "created_at": now.isoformat(),
            "delivery_status": delivery,
            "reminder_number": 1,
        }
        store_obj.put("issue_log", event, append_only=True)
        store_obj.put("site_state", {**pending, "site_id": str(site["site_id"]), "state_key": "pending_alert", "reminder_sent": True, "reminder_sent_at": now.isoformat(), "reminder_delivery_status": delivery})
        return event
    except Exception:
        # Release the claim on transient failure so the scheduled retry can try again.
        store_obj.delete("alert_keys", {"idempotency_key": idempotency})
        raise


def maybe_escalate_unacknowledged_alert(site: dict[str, Any], *, store_obj: Store = store, now: datetime | None = None) -> dict[str, Any] | None:
    """Escalate to Safety Officer if alert remains unacknowledged 15 minutes after reminder (or 35 min total)."""
    now = now or datetime.now(timezone.utc)
    pending = store_obj.get("site_state", {"site_id": str(site["site_id"]), "state_key": "pending_alert"})
    if not pending or pending.get("status", "pending") != "pending" or pending.get("escalated") or not pending.get("alert_id"):
        return None
    alert_id = str(pending["alert_id"])
    issued = store_obj.get("issue_log", {"site_id": str(site["site_id"]), "issue_id": alert_id})
    if not issued:
        return None
    if store_obj.get("acks", {"alert_id": alert_id}):
        return None
    try:
        if pending.get("reminder_sent_at"):
            sent_time = datetime.fromisoformat(str(pending["reminder_sent_at"]).replace("Z", "+00:00"))
            wait_seconds = 15 * 60
        else:
            sent_time = datetime.fromisoformat(str(issued["created_at"]).replace("Z", "+00:00"))
            wait_seconds = 35 * 60
    except (KeyError, ValueError):
        return None
    if (now - sent_time).total_seconds() < wait_seconds:
        return None
    idempotency = f"ack-escalation:{alert_id}"
    if not store_obj.put("alert_keys", {"idempotency_key": idempotency, "ttl": int(now.timestamp()) + 48 * 3600, "site_id": site["site_id"], "purpose": "safety_officer_escalation"}, append_only=True):
        return None
    delivery = "demo_in_app_only" if DEMO_MODE else "not_sent_no_confirmed_destination"
    try:
        topic_arn = os.getenv("SAFETY_OFFICER_SNS_TOPIC_ARN") or site.get("sns_topic_arn")
        if not DEMO_MODE and topic_arn and PUBLIC_ORIGIN:
            token = str(issued.get("ack_token", ""))
            message = (
                f"[ESCALATION: UNACKNOWLEDGED HEAT ALERT]\n\n"
                f"Site: {site.get('name', 'Site')}\n"
                f"Condition: {str(issued.get('to_band', 'stricter')).replace('_', ' ').upper()} heat band scheduled.\n"
                f"Change time: {pending.get('window_start', issued.get('window_start', 'see dashboard'))}.\n"
                f"Status: The site supervisor has NOT acknowledged this alert within the designated safety window.\n\n"
                f"Emergency Acknowledge / Inspection Link: {PUBLIC_ORIGIN.rstrip('/')}/ack/{token}\n\n"
                "Decision support, not medical advice. Safety Officer or Project Manager intervention recommended."
            )
            boto3.client("sns", region_name=AWS_REGION).publish(
                TopicArn=topic_arn,
                Subject=f"ShiftShield ESCALATION: Unacknowledged alert at {site.get('name', 'Site')}"[:100],
                Message=message,
            )
            delivery = "sns_escalation_published"
        event = {
            "site_id": str(site["site_id"]),
            "issue_id": f"escalation-{alert_id}",
            "alert_id": alert_id,
            "event_type": "safety_officer_escalation",
            "created_at": now.isoformat(),
            "delivery_status": delivery,
            "escalated_to": "safety_officer",
        }
        store_obj.put("issue_log", event, append_only=True)
        store_obj.put("site_state", {
            **pending,
            "site_id": str(site["site_id"]),
            "state_key": "pending_alert",
            "escalated": True,
            "escalated_at": now.isoformat(),
            "escalation_delivery_status": delivery,
        })
        return event
    except Exception:
        store_obj.delete("alert_keys", {"idempotency_key": idempotency})
        raise

