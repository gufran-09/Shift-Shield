"""Turn per-hour limits into deterministic quarter-hour work/rest windows."""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


QUARTER = timedelta(minutes=15)


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _parse(value: str) -> datetime:
    stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def _inside_shift(local: datetime, shift_start: str, shift_end: str) -> bool:
    start = time.fromisoformat(shift_start)
    end = time.fromisoformat(shift_end)
    now = local.timetz().replace(tzinfo=None)
    if start < end:
        return start <= now < end
    if start > end:
        return now >= start or now < end
    return False


def attach_rest_windows(points: list[dict[str, Any]], site: dict[str, Any], timezone_name: str) -> list[dict[str, Any]]:
    """Anchor each repeating hourly work/rest block at the site's wall-clock hour."""
    zone = _zone(timezone_name)
    site_id = str(site["site_id"])
    out: list[dict[str, Any]] = []
    for point in points:
        item = dict(point)
        stamp = _parse(str(point["time"]))
        local = stamp.astimezone(zone)
        in_shift = _inside_shift(local, str(site.get("shift_start", "08:00")), str(site.get("shift_end", "17:00")))
        work = int(point.get("work_minutes_per_hour", 60))
        minute = local.minute
        on_break = in_shift and work < 60 and minute >= work
        item["local_time"] = local.isoformat()
        item["in_shift"] = in_shift
        item["activity"] = "rest" if on_break else "work" if in_shift else "off_shift"
        item["rest_window_id"] = f"{site_id}:{int(stamp.timestamp())}" if on_break else None
        item["rest_window_start"] = stamp.isoformat() if on_break else None
        item["rest_window_end"] = (stamp + QUARTER).isoformat() if on_break else None
        out.append(item)
    return out


def eligible_rest_window(points: list[dict[str, Any]], window_id: str, *, now: datetime | None = None) -> dict[str, Any] | None:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    for point in points:
        if point.get("activity") != "rest" or point.get("rest_window_id") != window_id:
            continue
        start = _parse(str(point["rest_window_start"]))
        end = _parse(str(point["rest_window_end"]))
        if start <= now < end:
            return point
    return None


def next_rest_window(points: list[dict[str, Any]], *, now: datetime | None = None) -> dict[str, Any] | None:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    for point in points:
        if point.get("activity") == "rest" and point.get("rest_window_start"):
            if _parse(str(point["rest_window_end"])) > now:
                return point
    return None
