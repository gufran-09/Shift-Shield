from __future__ import annotations

from fastapi.testclient import TestClient

from app import alerts, main, store as store_module
from app.store import Store


def test_run_scoped_demo_persists_ack_worker_and_dashboard_evidence(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", str(tmp_path / "replay.sqlite3"))
    db = Store()
    monkeypatch.setattr(main, "store", db)
    monkeypatch.setattr(main, "DEMO_MODE", True)
    monkeypatch.setattr(alerts, "DEMO_MODE", True)
    monkeypatch.setattr(alerts, "_secret_cache", "replay-test-secret-long-enough-for-signing")

    client = TestClient(main.app)
    manifest = client.get("/api/demo")
    assert manifest.status_code == 200
    assert [step["event_id"] for step in manifest.json()["steps"]] == ["08:00", "10:00", "11:30", "13:00", "14:00", "16:00"]

    started = client.post("/api/demo/start")
    assert started.status_code == 200
    run_id = started.json()["run_id"]
    assert started.json()["is_synthetic"] is True

    for event_id in ("08:00", "10:00", "11:30"):
        result = client.post(f"/api/demo/{run_id}/step", json={"event_id": event_id})
        assert result.status_code == 200, result.text
    # Replaying a completed event is idempotent and does not append a second event.
    assert client.post(f"/api/demo/{run_id}/step", json={"event_id": "10:00"}).status_code == 200

    state_after_refresh = client.get(f"/api/demo/{run_id}").json()
    assert state_after_refresh["current_step"] == 2
    assert state_after_refresh["worker_aggregate"]["total_responses"] == 7
    assert state_after_refresh["rest_status"]["code"] == "no_record"
    assert state_after_refresh["alert_ack_path"].startswith("/ack/")
    assert state_after_refresh["is_synthetic"] is True
    compliance_before = client.get(f"/api/demo/{run_id}/compliance")
    assert compliance_before.status_code == 200
    assert compliance_before.json()["status"] == "no_approved_plan"
    assert compliance_before.json()["obligations"][1]["status"] == "no_record"

    token = state_after_refresh["alert_ack_path"].rsplit("/", maxsplit=1)[1]
    inspected = client.get(f"/api/ack/{token}")
    assert inspected.status_code == 200 and inspected.json()["already_acknowledged"] is False
    acked = client.post("/api/ack", json={"token": token})
    assert acked.status_code == 200 and acked.json()["acknowledged"] is True
    assert client.get(f"/api/ack/{token}").json()["already_acknowledged"] is True

    dashboard = client.get(f"/api/demo/{run_id}/dashboard")
    assert dashboard.status_code == 200
    initial_board = dashboard.json()
    assert initial_board["is_synthetic"] is True
    assert initial_board["plan"]["is_demo_only"] is True
    assert initial_board["windows"][0]["aggregate"]["total_responses"] == 7
    assert initial_board["ledger"]["rest_windows_in_plan"] == 1

    break_started = client.post(f"/api/demo/{run_id}/break-started")
    assert break_started.status_code == 200
    assert break_started.json()["created"] is True
    assert break_started.json()["rest_status"]["code"] == "confirmed_by_both"
    assert client.post(f"/api/demo/{run_id}/break-started").json()["already_recorded"] is True
    compliance_after_start = client.get(f"/api/demo/{run_id}/compliance").json()
    assert compliance_after_start["status"] == "no_approved_plan"
    assert compliance_after_start["is_synthetic"] is True
    assert compliance_after_start["obligations"][1]["status"] == "confirmed_by_both"

    worker_page = client.get(f"/api/demo/{run_id}/worker")
    assert worker_page.status_code == 200
    worker_context = worker_page.json()
    assert worker_context["eligible"] is True
    assert worker_context["site"]["site_code"] == "concrete-yard"

    payload = {
        "window_id": worker_context["active_window"]["rest_window_id"],
        "break_received": True,
        "water_available": True,
        "shade_available": True,
        "symptoms": [],
    }
    rejected_identity = client.post(f"/api/demo/{run_id}/worker", json={**payload, "phone": "+910000000000"})
    assert rejected_identity.status_code == 422
    accepted = client.post(f"/api/demo/{run_id}/worker", json=payload)
    assert accepted.status_code == 200
    assert accepted.json()["aggregate"]["total_responses"] == 8
    assert accepted.json()["combined_status"]["code"] == "confirmed_by_both"

    refreshed_board = client.get(f"/api/demo/{run_id}/dashboard").json()
    assert refreshed_board["windows"][0]["aggregate"]["total_responses"] == 8
    assert refreshed_board["ledger"]["worker_response_count"] == 8
    assert refreshed_board["ledger"]["rest_minutes_confirmed_by_both"] == 30
    assert refreshed_board["supervisor_break_started"] is True
    assert client.get(f"/api/demo/{run_id}/compliance").json()["obligations"][1]["status"] == "confirmed_by_both"

    saved_aggregate = db.list("rest_confirms", {"site_id": "demo-concrete-yard"})
    assert len(saved_aggregate) == 1
    assert not {"name", "phone", "identity", "device_id", "client_token", "ip", "answers"}.intersection(saved_aggregate[0])
    replay_events = db.list("replay_runs", {"run_id": run_id})
    assert {row.get("event_id") for row in replay_events} >= {"08:00", "10:00", "11:30"}
    assert len([row for row in replay_events if row.get("event_id") == "10:00"]) == 1
