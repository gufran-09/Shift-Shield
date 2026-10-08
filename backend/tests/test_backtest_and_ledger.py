from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.backtest import summarize_comparison
from app.ledger import build_ledger
from app.models import HistoricalBacktestRequest


def _time(minute: int) -> str:
    return datetime(2026, 9, 12, 12, minute, tzinfo=timezone.utc).isoformat()


def test_backtest_counts_interval_confusion_and_lead_time() -> None:
    points = [
        {"time": _time(0), "air_c": 36.0, "band": "normal", "baseline_alert": True, "site_danger": False},
        {"time": _time(15), "air_c": 36.2, "band": "high", "baseline_alert": True, "site_danger": True},
        {"time": _time(30), "air_c": 35.0, "band": "very_high", "baseline_alert": False, "site_danger": True},
        {"time": _time(45), "air_c": 34.0, "band": "caution", "baseline_alert": False, "site_danger": False},
    ]
    result = summarize_comparison(
        points, baseline_threshold_c=36.0, baseline_source="City plan v1, p.4",
        start_date="2026-09-12", end_date="2026-09-12", archive_source="fixture",
    )
    assert result["city_baseline_alert_hours"] == 0.5
    assert result["site_high_very_high_hours"] == 0.5
    assert result["missed_danger_hours"] == 0.25
    assert result["needless_alarm_hours"] == 0.25
    assert result["lead_time_minutes"] == [15.0]
    assert result["danger_outside_13_16_hours"] is None
    assert result["worker_confirmation_rate"] is None


def test_ledger_counts_actual_quarter_hour_rest_not_hourly_limit_fraction() -> None:
    points = [
        {"activity": "work", "band": "high"},
        {"activity": "rest", "band": "high"},
        {"activity": "rest", "band": "high"},
        {"activity": "work", "band": "high", "data_status": "stale"},
    ]
    window_a = {
        "window": {"rest_window_start": "2026-09-12T12:15:00+00:00", "rest_window_end": "2026-09-12T12:30:00+00:00"},
        "aggregate": {"total_responses": 3, "split_visible": True, "break_yes_count": 3, "break_no_count": 0, "water_yes_count": 2, "water_no_count": 1, "shade_yes_count": 3, "shade_no_count": 0},
        "supervisor_acknowledged": True,
        "status": {"code": "confirmed_by_both"},
    }
    window_b = {
        "window": {"rest_window_start": "2026-09-12T12:30:00+00:00", "rest_window_end": "2026-09-12T12:45:00+00:00"},
        "aggregate": {"total_responses": 2, "split_visible": False},
        "supervisor_acknowledged": False,
        "status": {"code": "no_record"},
    }
    result = build_ledger("site-1", plan_points=points, events=[{"event_type": "heat_heads_up", "lead_minutes": 58}], rest_windows=[window_a, window_b], recorded_date="2026-09-12")
    assert result["rest_minutes_prescribed"] == 30
    assert result["rest_minutes_confirmed_by_both"] == 15
    assert result["rest_minutes_supervisor_self_reported"] == 15
    assert result["worker_response_count"] == 5
    assert result["worker_majority_yes_rate"] == 1.0
    assert result["heat_risk_hours"] == 1.0
    assert result["missed_danger_hours"] == 0.25
    assert result["alert_lead_times_minutes"] == [58.0]
    assert result["wage_savings"] is None


def test_backtest_range_must_be_completed_and_at_most_seven_days() -> None:
    yesterday = date.today().fromordinal(date.today().toordinal() - 1)
    HistoricalBacktestRequest(
        start_date=yesterday, end_date=yesterday,
        baseline_threshold_c=35, baseline_source="Official local plan, page 4",
    )
    with pytest.raises(ValidationError):
        HistoricalBacktestRequest(
            start_date=date.today(), end_date=date.today(),
            baseline_threshold_c=35, baseline_source="Official local plan, page 4",
        )
    with pytest.raises(ValidationError):
        HistoricalBacktestRequest(
            start_date=date(2026, 1, 1), end_date=date(2026, 1, 8),
            baseline_threshold_c=35, baseline_source="Official local plan, page 4",
        )
