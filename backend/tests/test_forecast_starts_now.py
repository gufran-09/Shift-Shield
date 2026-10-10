"""The forecast must start at the current quarter-hour, not at local midnight."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import weather
from app.weather import HOURLY


def _payload(start: datetime, hours: int) -> dict:
    times = [int((start + timedelta(hours=h)).timestamp()) for h in range(hours)]
    return {"timezone": "Asia/Kolkata", "hourly": {"time": times, **{name: [1.0 + h for h in range(hours)] for name in HOURLY}}}


def test_rows_start_at_current_quarter(monkeypatch):
    midnight_ist_in_utc = datetime(2026, 10, 9, 18, 30, tzinfo=timezone.utc)  # 00:00 IST, 10 Oct
    monkeypatch.setattr(weather, "_fetch", lambda *a, **k: _payload(midnight_ist_in_utc, 72))
    now = midnight_ist_in_utc + timedelta(hours=17, minutes=12)  # 17:12 IST
    result = weather.forecast_15m(17.385, 78.4867, timezone_name="Asia/Kolkata", now=now)
    first = datetime.fromisoformat(result["rows"][0]["time"])
    assert first == midnight_ist_in_utc + timedelta(hours=17)  # 17:00 IST is the current quarter
    assert len(result["rows"]) == 36 * 4 + 1


def test_late_evening_still_has_full_horizon(monkeypatch):
    midnight_ist_in_utc = datetime(2026, 10, 9, 18, 30, tzinfo=timezone.utc)
    monkeypatch.setattr(weather, "_fetch", lambda *a, **k: _payload(midnight_ist_in_utc, 72))
    now = midnight_ist_in_utc + timedelta(hours=23, minutes=50)
    result = weather.forecast_15m(17.385, 78.4867, timezone_name="Asia/Kolkata", now=now)
    assert len(result["rows"]) == 36 * 4 + 1
