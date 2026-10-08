"""Run the app's own WBGT + NIOSH pipeline on a real archived day and compare it with fixed rest windows.

Usage (from backend/):
    python -m evaluation.replay_real_day --date 2024-05-04
    python -m evaluation.replay_real_day --date 2024-05-04 --shade mostly --intensity heavy --acclimatization acclimatized

Weather is Open-Meteo archive/reanalysis, not an on-site measurement. Weather data by Open-Meteo.com.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from app.physics import calculate_site_wbgt
from app.scheduling import make_plan
from app.weather import historical_15m

# Fixed "peak hours" windows quoted from the heat action plans (local time, [start, end)).
FIXED_WINDOWS = {
    "Telangana HAP 2021 p.36 (12 noon to 3 PM)": (12, 15),
    "Delhi HAP 2025 p.155 (12 to 4 PM)": (12, 16),
}
RISKY = {"high", "very_high"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lat", type=float, default=17.385)
    parser.add_argument("--lon", type=float, default=78.4867)
    parser.add_argument("--date", default="2024-05-04")
    parser.add_argument("--timezone", default="Asia/Kolkata")
    parser.add_argument("--shade", default="none", choices=["none", "partial", "mostly", "indoor"])
    parser.add_argument("--surface", default="light_concrete")
    parser.add_argument("--intensity", default="heavy", choices=["light", "moderate", "heavy", "very_heavy"])
    parser.add_argument("--acclimatization", default="acclimatized", choices=["acclimatized", "unacclimatized", "unknown"])
    parser.add_argument("--out", default=None, help="optional JSON output path")
    args = parser.parse_args()

    site = {
        "site_id": "archive-replay", "latitude": args.lat, "longitude": args.lon, "timezone": args.timezone,
        "shade": args.shade, "surface": args.surface, "wind_exposure": "partial_or_unknown",
        "land_use": "unknown", "enclosure": "open", "intensity": args.intensity,
        "acclimatization": args.acclimatization, "ppe": "normal",
    }
    archive = historical_15m(args.lat, args.lon, start_date=args.date, end_date=args.date, timezone_name=args.timezone)
    rows = archive["rows"]
    wbgt = calculate_site_wbgt(
        timestamps=[r["time"] for r in rows], latitude=args.lat, longitude=args.lon,
        air_c=[r["temperature_2m"] for r in rows], dewpoint_c=[r["dew_point_2m"] for r in rows],
        pressure_hpa=[r["surface_pressure"] for r in rows], wind_10m_m_s=[r["wind_speed_10m"] for r in rows],
        direct_w_m2=[r["direct_radiation"] for r in rows], diffuse_w_m2=[r["diffuse_radiation"] for r in rows],
        shortwave_w_m2=[r["shortwave_radiation"] for r in rows], profile=site,
    )

    from zoneinfo import ZoneInfo
    zone = ZoneInfo(args.timezone)
    hourly = []
    for row, point in zip(rows, wbgt, strict=True):
        local = datetime.fromisoformat(row["time"]).astimezone(zone)
        if local.minute != 0 or not 6 <= local.hour <= 19:
            continue
        plan = make_plan(point, site)
        label = "STOP (above 15-min limit)" if plan["exceeds_final_15_min_curve"] else f'{plan["label"]} {plan["work_minutes_per_hour"]}/{plan["rest_minutes_per_hour"]}'
        hourly.append({
            "local_hour": local.hour, "air_c": round(row["temperature_2m"], 1), "rh_pct": round(row["relative_humidity_2m"]),
            "wbgt_c": point["wbgt_c"], "wbgt_for_thresholds_c": plan["wbgt_for_thresholds_c"],
            "band": plan["band"], "stop": plan["exceeds_final_15_min_curve"], "schedule": label,
        })

    print(f"\n{args.date}  lat {args.lat} lon {args.lon}  shade={args.shade} intensity={args.intensity} acclimatization={args.acclimatization}")
    print("Open-Meteo archive/reanalysis (not on-site). Weather data by Open-Meteo.com\n")
    print(f'{"Time":>5} {"Air":>5} {"RH%":>4} {"WBGT":>5} {"+margin":>7}  Schedule')
    for h in hourly:
        print(f'{h["local_hour"]:02d}:00 {h["air_c"]:5.1f} {h["rh_pct"]:4d} {h["wbgt_c"]:5.1f} {h["wbgt_for_thresholds_c"]:7.1f}  {h["schedule"]}')
    peak = max(hourly, key=lambda h: h["wbgt_c"])
    hottest_air = max(hourly, key=lambda h: h["air_c"])
    print(f'\nWBGT peak: {peak["local_hour"]:02d}:00 ({peak["wbgt_c"]} C).  Hottest air: {hottest_air["local_hour"]:02d}:00 ({hottest_air["air_c"]} C).')
    risky = [h for h in hourly if h["band"] in RISKY or h["stop"]]
    for name, (start, end) in FIXED_WINDOWS.items():
        missed = [f'{h["local_hour"]:02d}:00' for h in risky if not start <= h["local_hour"] < end]
        print(f"{name}: risky hours outside the window = {', '.join(missed) or 'none'}")

    if args.out:
        Path(args.out).write_text(json.dumps({
            "date": args.date, "site_profile": site, "data_source": archive["source"],
            "observed_on_site": False, "attribution": "Weather data by Open-Meteo.com", "hourly": hourly,
        }, indent=2))
        print(f"\nSaved {args.out}")


if __name__ == "__main__":
    main()
