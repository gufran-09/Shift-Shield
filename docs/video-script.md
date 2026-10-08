# Demo video script (target 3:00)

Record at 1440x900, browser zoom 110 %, dark mode off. One voice (Sameer). Screen first, face optional.
Every number on screen must come from the app or `docs/replay-day.md`. Synthetic replay data is always called "demo data" out loud.

| # | Time | Screen | Say (roughly) |
|---|---|---|---|
| 1 | 0:00 to 0:15 | Black title card: "4 May 2024, Hyderabad. Air peaked at 41.4 °C at 2 PM." | "Telangana's heat plan tells employers to avoid outdoor work from 12 noon to 3 PM. On this day, that protected 3 hours." |
| 2 | 0:15 to 0:40 | `docs/replay-day.md` table, highlight 10:00 and 12:00 to 15:00 rows | "We ran the real archived weather through our estimate for a heavy-work site. Heat stress peaked at 10 to 11 in the morning, not at 2 PM, and 12 of 14 daylight hours were high-risk. A fixed afternoon window misses most of them. This is an estimate from reanalysis weather, not a sensor, but the shape is the point." |
| 3 | 0:40 to 0:55 | Title: "ShiftShield: the heat alert that proves the rest happened." | "ShiftShield turns a site's real conditions into a work-rest schedule, warns before it changes, and records whether the break actually happened." |
| 4 | 0:55 to 1:15 | Heat Check page: pick Hyderabad, heavy work, no shade, click Check | "Anyone can check a site with no login. It estimates WBGT, the heat-stress index NIOSH uses, from the forecast plus shade, surface and wind, adds a safety margin, and gives the NIOSH work-rest split for this workload." |
| 5 | 1:15 to 1:35 | Setup → Dashboard: band timeline, next rest window, alert about an hour ahead | "A supervisor sets up the site once. The dashboard shows the plan for the shift and alerts about an hour before the schedule tightens." |
| 6 | 1:35 to 2:00 | Replay page playing (label "demo data" visible): supervisor ack, worker QR page on phone, "I rested" tap, aggregate count | "This is the self-playing demo with demo data. The supervisor confirms the break. Workers confirm it too, anonymously, by scanning a QR code: no names, no phone numbers, counts hidden until three people answer. A symptom report can only make the plan stricter, never looser." |
| 7 | 2:00 to 2:30 | Rulebooks: upload Delhi HAP PDF, candidate rule with exact quote + page, Approve button | "Heat action plans are long PDFs. Our rulebook agent on Amazon Bedrock reads them and proposes rules, each with the exact quote and page. A person approves every rule. The app then applies whichever is stricter: the plan or the physiology. We scored it against a hand-built answer key of the Delhi plan: [RECALL] recall, [PRECISION] precision." |
| 8 | 2:30 to 2:45 | Architecture slide: React on CloudFront/S3 → API Gateway → Lambda (FastAPI) → DynamoDB, Bedrock, SNS, Open-Meteo | "It all runs on AWS in Mumbai. [CONFIRM SERVICES WITH GUFRAN]" |
| 9 | 2:45 to 3:00 | Closing card: cross-check table summary + disclaimer | "Our WBGT matches an independent implementation within half a degree, and every threshold traces to a NIOSH equation. It's decision support, not medical advice. We found no tool that connects the heat estimate, the schedule and proof of rest. ShiftShield does." |

## Fill before recording
- [RECALL] / [PRECISION]: from `python -m evaluation.score_rulebook` once Bedrock works. If Bedrock isn't ready, cut the score sentence; never invent it.
- Architecture: list only services actually deployed.
- If the NIOSH-equation patch is merged, re-run `replay_real_day` and update the numbers in rows 1 and 2.

## Rules
- Say "our estimate suggests", not "workers were in danger".
- Say "we found no tool that does this", not "first ever".
- Show "Weather data by Open-Meteo.com" on any screen with weather.
