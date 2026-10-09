"""Tests for Bonus Features: Escalation Chain, Amazon Polly Voice Alert, and Heat Certificate Verification."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.alerts import maybe_escalate_unacknowledged_alert
from app.main import app, verify_certificate
from app.store import Store
from app.voice import build_alert_speech_text, synthesize_speech


@pytest.fixture
def isolated_store(tmp_path, monkeypatch) -> Store:
    db_file = tmp_path / "test_bonus.sqlite3"
    monkeypatch.setenv("SHIFTSHIELD_DB", str(db_file))
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    s = Store()
    s.db_path = db_file
    with s._connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS records (entity TEXT NOT NULL, record_key TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(entity, record_key))")
    return s


def test_speech_text_generation_hindi_and_english() -> None:
    hi_text = build_alert_speech_text(
        site_name="Mumbai Metro Pier 4",
        band="high",
        work_minutes=30,
        rest_minutes=30,
        language="hi",
    )
    assert "Mumbai Metro Pier 4" in hi_text
    assert "30 मिनट काम" in hi_text
    assert "30 मिनट का अनिवार्य विश्राम" in hi_text

    en_text = build_alert_speech_text(
        site_name="Hyderabad Logistics Hub",
        band="extreme_caution",
        work_minutes=45,
        rest_minutes=15,
        language="en",
    )
    assert "Hyderabad Logistics Hub" in en_text
    assert "Extreme Caution" in en_text
    assert "45 minutes of work" in en_text
    assert "15 minutes of mandatory rest" in en_text


def test_voice_synthesis_produces_audio_stream() -> None:
    audio_bytes, media_type = synthesize_speech("Test audio alert", language="hi")
    assert media_type == "audio/mpeg"
    assert len(audio_bytes) > 0


def test_alert_escalation_chain_timing(isolated_store: Store) -> None:
    site = {
        "site_id": "site-test-1",
        "name": "Test Site",
        "email_alert_opt_in": True,
        "email_subscription_status": "confirmed",
        "sns_topic_arn": "arn:aws:sns:ap-south-1:123456789012:test-topic",
    }
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Store pending alert that was created 10 minutes ago - should NOT escalate yet
    isolated_store.put("site_state", {
        "site_id": "site-test-1",
        "state_key": "pending_alert",
        "alert_id": "alert-101",
        "status": "pending",
        "reminder_sent": True,
        "reminder_sent_at": (now - timedelta(minutes=5)).isoformat(),
    })
    isolated_store.put("issue_log", {
        "site_id": "site-test-1",
        "issue_id": "alert-101",
        "event_type": "heat_alert",
        "to_band": "high",
        "created_at": (now - timedelta(minutes=25)).isoformat(),
        "ack_token": "token123",
    })

    # Under 15 min since reminder: should not escalate
    result = maybe_escalate_unacknowledged_alert(site, store_obj=isolated_store, now=now)
    assert result is None

    # Over 15 min since reminder (e.g. 16 minutes): should escalate!
    later = now + timedelta(minutes=12)
    escalated = maybe_escalate_unacknowledged_alert(site, store_obj=isolated_store, now=later)
    assert escalated is not None
    assert escalated["event_type"] == "safety_officer_escalation"
    assert escalated["escalated_to"] == "safety_officer"

    # Second call should be idempotent (not escalate again)
    again = maybe_escalate_unacknowledged_alert(site, store_obj=isolated_store, now=later + timedelta(minutes=5))
    assert again is None


def test_certificate_cryptographic_verification(isolated_store: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    import json
    import hmac
    import hashlib

    # Create a test certificate
    payload = {
        "certificate_id": "cert-test-abc",
        "site_id": "site-1",
        "site_name": "Delhi Central Station",
        "date": "2026-06-01",
        "heat_risk_hours": 4.5,
        "rest_minutes_prescribed": 90,
        "rest_minutes_confirmed": 90,
        "issued_at": "2026-06-01T18:00:00Z",
        "issuer": "ShiftShield Verified Rest Record",
    }
    canonical = json.dumps(payload, sort_keys=True)
    valid_sig = hmac.new(b"shiftshield-heat-cert-v1", canonical.encode(), hashlib.sha256).hexdigest()

    isolated_store.put("site_state", {
        "site_id": "site-1",
        "state_key": "certificate:cert-test-abc",
        "certificate": {
            **payload,
            "signature": valid_sig,
            "verification_url": "/verify/cert-test-abc",
        },
    })

    # Monkeypatch the global store used by main.py
    from app import main
    monkeypatch.setattr(main, "store", isolated_store)

    verification = main.verify_certificate("cert-test-abc")
    assert verification["valid"] is True
    assert verification["status"] == "cryptographically_verified"

    # Now tamper with certificate data
    isolated_store.put("site_state", {
        "site_id": "site-1",
        "state_key": "certificate:cert-test-abc",
        "certificate": {
            **payload,
            "rest_minutes_confirmed": 120,  # Tampered
            "signature": valid_sig,
            "verification_url": "/verify/cert-test-abc",
        },
    })

    tampered_verification = main.verify_certificate("cert-test-abc")
    assert tampered_verification["valid"] is False
    assert tampered_verification["status"] == "tampered_or_invalid"
