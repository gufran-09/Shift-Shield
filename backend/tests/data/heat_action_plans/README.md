# Heat action plan test data

| File | What it is |
|---|---|
| `delhi_hap_2025.pdf` | Delhi Heat Action Plan 2025, Delhi Disaster Management Authority (PDF created 21 April 2025, 163 pages). Public government document, included unchanged for testing. |
| `telangana_hap_2021.pdf` | Telangana State Heatwave Action Plan 2021, Government of Telangana, Revenue (Disaster Management) Department (111 pages, text layer on every page). Public government document, included unchanged for testing. SHA-256 b666cfc7…c3380. |
| `telangana_hap_2021_obligations.csv` | Answer key: 26 worker-facing obligations, same columns as Delhi. |
| `delhi_hap_2025_obligations.csv` | Answer key: 48 worker-facing obligations with page, exact sentence or anchor phrase, who must act, what, when, and type. |

## How the answer key was made

1. Drafted with AI help (Claude) from the PDF text and, for scanned pages, from the page images.
2. Every row checked against the PDF by hand by Sameer Ahmed on 8 October 2026 (`verified_by_human` column).
3. Say this in the writeup: "drafted with AI help and verified by hand".

## Things the data shows

- **Pages 155 to 158 (Labour Department circular, dated 16/04/2025) are scanned images with no text layer.** 15 rows come from there. The extractor needs OCR (Textract) or a vision model to read them, and text-based quote checks cannot verify them.
- **pypdf inserts a space before some hyphens in table cells** (page 56 reads "1pm -5pm" and "health -checkup"). A whitespace-only quote check rejects a correct human quote there. `backend/evaluation/score_rulebook.py` tolerates this; consider the same in `verify_quote`.
- **The plan gives four different peak-hour windows**: 12 to 4 PM (circular, p.155), 1 to 5 PM (pp.56, 81), working hours 7 AM to 1 PM and 4 to 6 PM (p.56), and 12 noon to 3 PM (p.76).
- This is the **2025** plan. It does not contain the "1 PM to 4 PM" rule that news reports describe for 2026.

## Telangana 2021: things the data shows

- PDF page number equals printed page number.
- **The labour rules give two different peak windows:** "12 Noon to 3 PM" (p.35) and "peak afternoon hours (11pm – 3pm) during a heat alert" (p.59), where "11pm" is apparently a typo for 11 AM. Other departments use 12 to 4 PM (TSRTC, pp.36, 59) and the public advice says 12.00 noon to 3.00 p.m. (p.99).
- Page 72 suggests an "extended afternoon break or alternate working hours", and page 100 tells employers to "increase the frequency and length of rest breaks", but no page says how long or how often. ShiftShield's NIOSH schedule fills exactly that gap.
- Quotes keep the plan's own spelling ("constriction workers", "contactors", "causalities").
- A 2025 Telangana plan was released on 2 May 2025 but we could not find it published online, so this is the latest plan we can cite.
