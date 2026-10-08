# Replay day: Hyderabad, 4 May 2024

## Why this day

- Open-Meteo's archive ranks it the hottest day of April to June 2024 at Hyderabad (17.385 N, 78.4867 E), with a 41.4 C maximum (`python scripts/find_hot_days.py --lat 17.385 --lon 78.4867 --year 2024`).
- News On AIR reported severe heatwave conditions across Telangana on 3 May 2024, with an average maximum of 44 C in Hyderabad: https://newsonair.gov.in/telangana-experiences-severe-heatwave-conditions-18-districts-record-temperatures-exceeding-46-degrees-celsius
- The archive reads about 2 to 3 C below the reported station values. Reanalysis grids are coarse; say so in the writeup.

Use one milder day from the same list as the control day.

## First result (Sameer's reference engine v0.1.1, to be reproduced with the app's backtest)

Shaded site (shade 0.8), heavy work, acclimatized crew, 1 C margin. Hourly, local time.

| Time | Air C | RH % | WBGT C | Schedule |
|---|---|---|---|---|
| 07:00 | 30.0 | 67 | 27.7 | High, 30/30 |
| 08:00 | 33.2 | 53 | 28.8 | Very high, 15/45 |
| 09:00 | 35.7 | 42 | 29.6 | Stop this work |
| 10:00 | 38.0 | 31 | 29.6 | Stop this work |
| 11:00 | 39.5 | 24 | 29.6 | Stop this work |
| 12:00 | 40.5 | 19 | 29.4 | Very high, 15/45 |
| 13:00 | 41.1 | 17 | 29.1 | Very high, 15/45 |
| 14:00 | 41.4 | 16 | 28.8 | Very high, 15/45 |
| 15:00 | 41.4 | 15 | 28.0 | Very high, 15/45 |
| 16:00 | 40.7 | 14 | 26.7 | High, 30/30 |
| 17:00 | 39.1 | 14 | 25.2 | Normal |

**Finding to verify:** at this shaded site the heat-stress peak was 9 to 11 AM, when the air was more humid, not in the hottest afternoon hours. A fixed afternoon rest window (1 to 4 PM, 12 to 4 PM or 1 to 5 PM) would miss it. Confirm with the app's pywbgt pipeline before using it in the video.

Weather data by Open-Meteo.com.
