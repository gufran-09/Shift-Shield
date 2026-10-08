from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from app import alerts, rest, store as store_module
from app.store import Store


@pytest.fixture
def isolated_store(tmp_path, monkeypatch) -> Store:
    db_file = tmp_path / "test_alerts.sqlite3"
    monkeypatch.setenv("SHIFTSHIELD_DB", str(db_file))
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    s = Store()
    s.db_path = db_file
    with s._connect() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS records (entity TEXT NOT NULL, record_key TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(entity, record_key))")
    return s


def test_alert_idempotency_prevents_duplicate_issues(isolated_store: Store) -> None:
    site = {
        "site_id": "site-test-101",
        "name": "Delhi Test Yard",
        "shift_end_utc": "2026-10-08T18:00:00Z",
    }
    payload = {
        "reason": "Temperature rising rapidly",
        "work_minutes_per_hour": 30,
        "rest_minutes_per_hour": 30,
    }
    now = datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc)

    # First issuance succeeds
    first_alert = alerts.issue_alert(
        site,
        shift_date="2026-10-08",
        from_band="caution",
        to_band="high",
        window_start="2026-10-08T11:00:00Z",
        alert_type="heads_up",
        payload=payload,
        store_obj=isolated_store,
        now=now,
    )
    assert first_alert is not None
    assert first_alert["site_id"] == "site-test-101"
    assert first_alert["from_band"] == "caution"
    assert first_alert["to_band"] == "high"

    # Second issuance with identical window and bands is blocked by idempotency key
    duplicate = alerts.issue_alert(
        site,
        shift_date="2026-10-08",
        from_band="caution",
        to_band="high",
        window_start="2026-10-08T11:00:00Z",
        alert_type="heads_up",
        payload=payload,
        store_obj=isolated_store,
        now=now,
    )
    assert duplicate is None


def test_ack_token_signature_and_expiration() -> None:
    now_ts = int(time.time())
    valid_token = alerts.sign_ack_token(site_id="site-xyz", alert_id="alert-123", expires_at=now_ts + 3600)
    verified = alerts.verify_ack_token(valid_token)
    assert verified["site_id"] == "site-xyz"
    assert verified["alert_id"] == "alert-123"

    # Tampered token fails
    parts = valid_token.split(".")
    tampered = f"{parts[0]}.corrupted_signature"
    with pytest.raises(ValueError, match="Invalid or expired acknowledgement link"):
        alerts.verify_ack_token(tampered)

    # Expired token fails
    expired_token = alerts.sign_ack_token(site_id="site-xyz", alert_id="alert-123", expires_at=now_ts - 60)
    with pytest.raises(ValueError, match="Invalid or expired acknowledgement link"):
        alerts.verify_ack_token(expired_token)


def test_acknowledgement_records_only_once(isolated_store: Store) -> None:
    site = {"site_id": "site-test-202", "name": "Hyderabad Site"}
    alert = alerts.issue_alert(
        site,
        shift_date="2026-10-08",
        from_band="normal",
        to_band="caution",
        window_start="2026-10-08T10:00:00Z",
        alert_type="heads_up",
        payload={"reason": "Test alert"},
        store_obj=isolated_store,
    )
    assert alert is not None
    token = alert["ack_token"]

    # First ack succeeds
    res1 = alerts.acknowledge(token, store_obj=isolated_store)
    assert res1["acknowledged"] is True
    assert res1["already_acknowledged"] is False

    # Second ack is idempotent (already acknowledged)
    res2 = alerts.acknowledge(token, store_obj=isolated_store)
    assert res2["acknowledged"] is False
    assert res2["already_acknowledged"] is True


def test_maybe_send_ack_reminder_timing_and_single_dispatch(isolated_store: Store) -> None:
    site = {"site_id": "site-test-303", "name": "Solar Yard"}
    now = datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc)
    alert = alerts.issue_alert(
        site,
        shift_date="2026-10-08",
        from_band="caution",
        to_band="high",
        window_start="2026-10-08T11:00:00Z",
        alert_type="heads_up",
        payload={"reason": "High heat expected"},
        store_obj=isolated_store,
        now=now,
    )
    assert alert is not None

    isolated_store.put("site_state", {
        "site_id": "site-test-303",
        "state_key": "pending_alert",
        "alert_id": alert["alert_id"],
        "status": "pending",
        "window_start": "2026-10-08T11:00:00Z",
    })

    # 10 minutes later: too early, no reminder
    too_early = alerts.maybe_send_ack_reminder(site, store_obj=isolated_store, now=now + timedelta(minutes=10))
    assert too_early is None

    # 21 minutes later: sends 1 reminder
    reminder = alerts.maybe_send_ack_reminder(site, store_obj=isolated_store, now=now + timedelta(minutes=21))
    assert reminder is not None
    assert reminder["reminder_number"] == 1

    # Calling again after 25 minutes: reminder already sent, so no duplicates
    again = alerts.maybe_send_ack_reminder(site, store_obj=isolated_store, now=now + timedelta(minutes=25))
    assert again is None


def test_four_rest_record_states_and_privacy_masking(isolated_store: Store) -> None:
    site_id = "site-privacy-404"
    window_id = "win-001"

    # 1. Neither supervisor nor workers -> No record
    empty_agg = rest.public_aggregate(None)
    status0 = rest.combined_rest_status(supervisor_acknowledged=False, aggregate=empty_agg)
    assert status0["code"] == "no_record"

    # 2. Supervisor acknowledged, no worker response -> Supervisor only
    status1 = rest.combined_rest_status(supervisor_acknowledged=True, aggregate=empty_agg)
    assert status1["code"] == "supervisor_only"

    # Worker response count under 3: counts are masked from public view
    agg1 = rest.submit_aggregate(
        site_id, window_id, break_received=True, water_available=True, shade_available=True, symptoms=[], store_obj=isolated_store,
    )
    assert agg1["split_visible"] is False
    assert agg1["total_responses"] == 1

    # Add 2 more responses (total 3, majority YES)
    rest.submit_aggregate(site_id, window_id, break_received=True, water_available=True, shade_available=True, symptoms=[], store_obj=isolated_store)
    agg3 = rest.submit_aggregate(site_id, window_id, break_received=True, water_available=True, shade_available=True, symptoms=[], store_obj=isolated_store)
    assert agg3["split_visible"] is True
    assert agg3["total_responses"] == 3
    assert agg3["majority"] == "yes"

    # 3. Supervisor + majority YES -> Confirmed by both
    status2 = rest.combined_rest_status(supervisor_acknowledged=True, aggregate=agg3)
    assert status2["code"] == "confirmed_by_both"

    # 4. Supervisor + majority NO -> Disputed
    window_id_no = "win-002"
    rest.submit_aggregate(site_id, window_id_no, break_received=False, water_available=None, shade_available=None, symptoms=[], store_obj=isolated_store)
    rest.submit_aggregate(site_id, window_id_no, break_received=False, water_available=None, shade_available=None, symptoms=[], store_obj=isolated_store)
    agg_no = rest.submit_aggregate(site_id, window_id_no, break_received=False, water_available=None, shade_available=None, symptoms=[], store_obj=isolated_store)
    assert agg_no["majority"] == "no"
    status3 = rest.combined_rest_status(supervisor_acknowledged=True, aggregate=agg_no)
    assert status3["code"] == "disputed"
