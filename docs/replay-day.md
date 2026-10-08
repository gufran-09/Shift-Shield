# Replay day: Hyderabad, 4 May 2024

## Why this day

- Open-Meteo's archive ranks it the hottest day of April to June 2024 at Hyderabad (17.385 N, 78.4867 E), with a 41.4 C maximum (`python scripts/find_hot_days.py --lat 17.385 --lon 78.4867 --year 2024`).
- News On AIR reported severe heatwave conditions across Telangana on 3 May 2024, with an average maximum of 44 C in Hyderabad: https://newsonair.gov.in/telangana-experiences-severe-heatwave-conditions-18-districts-record-temperatures-exceeding-46-degrees-celsius
- The archive reads about 2 to 3 C below the reported station values. Reanalysis grids are coarse; say so in the writeup.

Use one milder day from the same list as the control day.

## Result from the app's own pipeline (pywbgt + config thresholds)

`cd backend && python -m evaluation.replay_real_day --date 2024-05-04 [--shade mostly]`

Heavy work, acclimatized crew, light concrete, unknown land use (+2 C), partial/unknown wind, 1 C margin. Thresholds: NIOSH-equation version v2 (`NIOSH-2016-106-equations-v2-demo-2026-10-08`). Hourly, local time.

| Time | Air C | RH % | WBGT full sun | Schedule | WBGT mostly shaded | Schedule |
|---|---|---|---|---|---|---|
| 06:00 | 27.1 | 79 | 27.1 | High 30/30 | 26.6 | High 30/30 |
| 07:00 | 30.0 | 67 | 30.0 | Stop | 28.8 | Very high 15/45 |
| 08:00 | 33.2 | 53 | 32.7 | Stop | 30.9 | Stop |
| 09:00 | 35.7 | 42 | 34.5 | Stop | 32.5 | Stop |
| 10:00 | 38.0 | 31 | **35.0** | Stop | 33.2 | Stop |
| 11:00 | 39.5 | 24 | 35.0 | Stop | **33.4** | Stop |
| 12:00 | 40.5 | 19 | 34.7 | Stop | 33.2 | Stop |
| 13:00 | 41.1 | 17 | 34.7 | Stop | 33.2 | Stop |
| 14:00 | **41.4** | 16 | 34.5 | Stop | 32.7 | Stop |
| 15:00 | 41.4 | 15 | 33.8 | Stop | 31.8 | Stop |
| 16:00 | 40.7 | 14 | 31.7 | Stop | 29.9 | Stop |
| 17:00 | 39.1 | 14 | 29.1 | Very high 15/45 | 27.6 | Very high 15/45 |
| 18:00 | 36.3 | 14 | 25.2 | Caution 45/15 | 24.5 | Normal |
| 19:00 | 32.1 | 23 | 22.4 | Normal | 22.4 | Normal |

## What it shows

- **The heat-stress peak came before the hottest air.** WBGT peaked at 10:00 to 11:00 (35.0 C in sun, 33.4 C shaded), while air temperature peaked at 14:00. Morning humidity (31 to 42 %) offsets the lower air temperature.
- **Fixed rest windows cover a small part of the risky day.** For heavy work, 12 of 14 daylight hours were High or worse. Telangana's "avoid 12 noon to 3 PM" (HAP 2021, p.35) covers 3 of them; Delhi's "12 to 4 PM" (HAP 2025, p.155) covers 4. Both miss 06:00 to 11:00.
- **Honest limits:** archive/reanalysis is not an on-site reading and runs 2 to 3 C below reported station maxima; the site factors (+2 C land use, reflected-sun factor, wind factor) are provisional demo assumptions; heavy work is the strictest common case. Say "this estimate suggests", not "workers were in danger".
- Sameer's stdlib reference engine (no land-use delta) found the same shape: peak 09:00 to 11:00 at a shaded site.

Weather data by Open-Meteo.com.
