"""List the hottest days in a past season, to choose the replay day.

    python scripts/find_hot_days.py --lat 17.385 --lon 78.4867 --year 2024
"""
import argparse
import json
import urllib.parse
import urllib.request


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--lat", type=float, required=True)
    a.add_argument("--lon", type=float, required=True)
    a.add_argument("--year", type=int, default=2024)
    a.add_argument("--top", type=int, default=8)
    args = a.parse_args()
    params = {"latitude": args.lat, "longitude": args.lon, "start_date": f"{args.year}-04-01",
              "end_date": f"{args.year}-06-30", "timezone": "Asia/Kolkata",
              "daily": "temperature_2m_max,relative_humidity_2m_mean,shortwave_radiation_sum"}
    url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        d = json.load(r)["daily"]
    rows = sorted(zip(d["time"], d["temperature_2m_max"], d["relative_humidity_2m_mean"]),
                  key=lambda x: (x[1] or -99), reverse=True)[: args.top]
    print("date        max air C  mean RH%")
    for day, tmax, rh in rows:
        print(f"{day}   {tmax:6.1f}    {rh:5.0f}")
    print("\nPick one that news reports also call a heatwave day, and one milder day as a control.")
    print("Weather data by Open-Meteo.com")


if __name__ == "__main__":
    main()
