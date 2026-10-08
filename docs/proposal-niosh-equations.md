# Proposal: derive the threshold curves from NIOSH's equations

**Status:** proposal for Gufran. Nothing in `backend/app/config/thresholds.v1.json` is changed by this commit.

## The source

NIOSH 2016-106, section 8.1, printed page 93, gives the limits as equations, M = metabolic rate in watts:

- RAL (unacclimatized) = 59.9 - 14.1 log10 M
- REL (acclimatized)   = 56.7 - 11.5 log10 M

Limits are 1-hour time-weighted averages (section 1.1, printed page 2). For w minutes of work per hour, the hourly average rate is (w x M_task + (60 - w) x 117 W) / 60, with resting = 117 W from Table 5-1 (printed page 70). This averaging step is our derivation from NIOSH's rules, not a printed NIOSH table, so it needs the same review as the chart readings.

## Comparison at the chart workloads already used (200/300/400/500 kcal/h)

| Group | Class | Current file (60/45/30/15) | From equations (60/45/30/15) |
|---|---|---|---|
| RAL | light | 27.5 / 28.5 / 29.5 / 30.5 | 26.5 / 27.3 / 28.3 / 29.4 |
| RAL | moderate | 25.0 / 26.0 / 27.5 / 29.0 | 24.0 / 25.2 / 26.5 / 28.3 |
| RAL | heavy | 24.0 / 24.5 / 26.0 / 27.5 | 22.3 / 23.6 / 25.2 / 27.3 |
| RAL | very heavy | 22.0 / 23.0 / 25.0 / 26.5 | 20.9 / 22.3 / 24.0 / 26.5 |
| REL | light | 29.5 / 30.5 / 31.5 / 32.5 | 29.5 / 30.1 / 30.9 / 31.8 |
| REL | moderate | 27.5 / 28.5 / 29.5 / 30.5 | 27.5 / 28.4 / 29.5 / 30.9 |
| REL | heavy | 26.0 / 27.5 / 28.5 / 29.5 | 26.0 / 27.1 / 28.4 / 30.1 |
| REL | very heavy | 25.0 / 26.0 / 27.5 / 29.0 | 24.9 / 26.0 / 27.5 / 29.5 |

## What it shows

- **REL (acclimatized):** the chart readings match the equations within about 0.5 C at 60, 45 and 30 min/h.
- **RAL (unacclimatized), 60 min/h:** the chart readings are **1.0 to 1.7 C less strict** than NIOSH's own equation. The 60-minute value needs no averaging step, so the equation is the authoritative number there.

## Suggested change

At minimum, set the 60-minute values to the equation values (stricter for RAL, unchanged for REL). Optionally generate all four columns from the equations, keep the chart readings as a cross-check, and record both in the file's `transcription_method`.
