from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app import alerts, rest, store as store_module
from app.config import THRESHOLDS
from app.models import RestSubmission
from app.physics import calculate_site_wbgt
from app.rulebook import InvalidQuote, approve_candidate, verify_quote
from app.scheduling import select_band
from app.store import Store


def test_liljegren_reference_and_raw_site_inputs_are_preserved() -> None:
    profile = {
        "surface": "light_concrete",
        "shade": "none",
        "wind_exposure": "open",
        "land_use": "vegetated",
        "enclosure": "open",
    }
    point = calculate_site_wbgt(
        timestamps=["2026-06-01T12:00:00Z"],
        latitude=28.6139,
        longitude=77.209,
        air_c=[35.0],
        dewpoint_c=[25.0],
        pressure_hpa=[1008.0],
        wind_10m_m_s=[1.5],
        direct_w_m2=[650.0],
        diffuse_w_m2=[100.0],
        shortwave_w_m2=[750.0],
        profile=profile,
        margin_c=1.0,
    )[0]

    assert point["method"].startswith("Liljegren et al. (2008)")
    assert point["wbgt_c"] == pytest.approx(33.46, abs=0.02)
    assert point["conservative_wbgt_c"] == pytest.approx(point["wbgt_c"] + 1.0)
    # v7 site equation: 650 W/m2 direct + 100 diffuse + 0.25 * 750 global.
    # pywbgt modifies its own solar/wind arrays, so the logged input stays 937.5/1.5.
    assert point["site_solar_w_m2"] == pytest.approx(937.5)
    assert point["site_wind_10m_m_s"] == pytest.approx(1.5)
    assert point["model_adjusted_solar_w_m2"] != pytest.approx(point["site_solar_w_m2"])
    assert point["model_wind_2m_m_s"] < point["site_wind_10m_m_s"]


def test_higher_humidity_and_less_shade_do_not_reduce_estimated_wbgt() -> None:
    common = {
        "timestamps": ["2026-06-01T12:00:00Z"],
        "latitude": 28.6139,
        "longitude": 77.209,
        "air_c": [35.0],
        "pressure_hpa": [1008.0],
        "wind_10m_m_s": [1.5],
        "direct_w_m2": [650.0],
        "diffuse_w_m2": [100.0],
        "shortwave_w_m2": [750.0],
        "margin_c": 1.0,
    }
    base_profile = {"surface": "light_concrete", "shade": "none", "wind_exposure": "open", "land_use": "vegetated", "enclosure": "open"}
    base = calculate_site_wbgt(**common, dewpoint_c=[24.0], profile=base_profile)[0]["wbgt_c"]
    more_humid = calculate_site_wbgt(**common, dewpoint_c=[27.0], profile=base_profile)[0]["wbgt_c"]
    shaded = calculate_site_wbgt(**common, dewpoint_c=[24.0], profile={**base_profile, "shade": "mostly"})[0]["wbgt_c"]

    assert more_humid >= base
    assert shaded <= base


def test_niosh_curve_boundaries_tighten_and_unknown_uses_ral() -> None:
    row = THRESHOLDS["curves_by_acclimatization"]["unacclimatized"]["class_rows"]["light"]
    limits = row["wbgt_c_at_work_minutes_per_hour"]
    assert select_band(limits["60"] - 0.01, "light", "unacclimatized")["band"] == "normal"
    assert select_band(limits["60"], "light", "unacclimatized")["band"] == "caution"
    assert select_band(limits["45"], "light", "unacclimatized")["band"] == "high"
    assert select_band(limits["30"], "light", "unacclimatized")["band"] == "very_high"
    above_final = select_band(limits["15"], "light", "unacclimatized")
    assert above_final["exceeds_final_15_min_curve"] is True
    assert above_final["safe_schedule_supported"] is False
    assert above_final["source_curve"] == "RAL"
    assert select_band(20.0, "light", "unknown")["source_curve"] == "RAL"


def test_rest_aggregate_masks_splits_until_three_and_stores_no_identity(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", str(tmp_path / "rest.sqlite3"))
    db = Store()
    site_id, window_id = "site-test", "site-test:2030-01-01T12:00Z"

    first = rest.submit_aggregate(site_id, window_id, break_received=True, water_available=True, shade_available=None, symptoms=[], store_obj=db)
    second = rest.submit_aggregate(site_id, window_id, break_received=False, water_available=False, shade_available=True, symptoms=["dizzy"], store_obj=db)
    assert first["split_visible"] is False
    assert second["split_visible"] is False
    assert "break_yes_count" not in second and "break_no_count" not in second
    assert second["water_yes_count"] is None and second["symptom_reports"] is None

    third = rest.submit_aggregate(site_id, window_id, break_received=True, water_available=True, shade_available=True, symptoms=[], store_obj=db)
    assert third["total_responses"] == 3
    assert third["split_visible"] is True
    assert third["majority"] == "yes"
    assert rest.combined_rest_status(True, third)["code"] == "confirmed_by_both"

    saved = db.list("rest_confirms", {"site_id": site_id})
    assert len(saved) == 1
    assert not {"name", "phone", "identity", "device_id", "client_token", "ip", "answers"}.intersection(saved[0])


def test_anonymous_submission_schema_rejects_identity_fields() -> None:
    with pytest.raises(ValidationError):
        RestSubmission.model_validate({
            "window_id": "site-test:2030-01-01T12:00Z",
            "break_received": True,
            "phone": "+910000000000",
        })


def test_alert_is_idempotent_and_acknowledgement_does_not_edit_issue(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", str(tmp_path / "alerts.sqlite3"))
    db = Store()
    monkeypatch.setattr(alerts, "_secret_cache", "test-signing-secret-that-is-long-enough")
    monkeypatch.setattr(alerts, "DEMO_MODE", True)
    now = datetime.now(timezone.utc)
    site = {"site_id": "site-test", "name": "Test Yard", "shift_end_utc": (now + timedelta(hours=3)).isoformat()}
    kwargs = {
        "shift_date": now.date().isoformat(),
        "from_band": "normal",
        "to_band": "caution",
        "window_start": (now + timedelta(minutes=60)).isoformat(),
        "alert_type": "heads_up",
        "payload": {"reason": "synthetic test event"},
        "store_obj": db,
        "now": now,
    }

    issued = alerts.issue_alert(site, **kwargs)
    assert issued is not None
    assert alerts.issue_alert(site, **kwargs) is None
    original = db.get("issue_log", {"site_id": site["site_id"], "issue_id": issued["alert_id"]})
    first_ack = alerts.acknowledge(issued["ack_token"], store_obj=db)
    second_ack = alerts.acknowledge(issued["ack_token"], store_obj=db)

    assert first_ack["acknowledged"] is True
    assert second_ack["already_acknowledged"] is True
    assert db.get("issue_log", {"site_id": site["site_id"], "issue_id": issued["alert_id"]}) == original
    assert len([row for row in db.list("issue_log", {"site_id": site["site_id"]}) if row.get("event_type") == "heat_alert"]) == 1


def test_rulebook_quote_must_match_exact_source_page_and_unverified_rule_cannot_be_approved(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", str(tmp_path / "rules.sqlite3"))
    db = Store()
    pages = {1: "The site supervisor shall provide shade during scheduled rest periods."}
    assert verify_quote(pages, 1, "The site supervisor shall provide shade during scheduled rest periods.")
    assert verify_quote(pages, 1, "The site supervisor\nshall provide shade during scheduled rest periods.")
    assert not verify_quote(pages, 2, "The site supervisor shall provide shade during scheduled rest periods.")
    assert not verify_quote(pages, 1, "The supervisor may remove scheduled rest.")

    db.put("rulebooks", {
        "plan_id": "plan-test", "rule_id": "rule-test", "quote_verified": False,
        "status": "rejected_unverifiable_quote", "requirement_text": "unverified",
    })
    with pytest.raises(InvalidQuote):
        approve_candidate("plan-test", "rule-test", action="approve", reviewer_name="site_supervisor", store_obj=db)
