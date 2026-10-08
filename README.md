# ShiftShield

**The heat alert that proves the rest happened.** Environmental Hacks 2026 (WeMakeDevs × AWS), Track 02: Heat and Water. Team EcoNexus: Sameer Ahmed, Gufran Ahmed.

**Live app:** _link added after deployment_ · **Demo video (3 min):** _link added after recording_

Outdoor workers in Indian cities get heat advice as a fixed rule: "avoid work from 12 noon to 3 PM". ShiftShield turns a worksite's real conditions into a work-rest schedule, warns about an hour before it tightens, and keeps a record of whether the break happened.

> Decision support only, not medical or legal advice. Thresholds are pending occupational-safety review. Not for field use without a qualified review.

## Why fixed windows are not enough

Real archived weather for Hyderabad, 4 May 2024 (the hottest day of April to June 2024 in Open-Meteo's archive), run through this app's own pipeline for a heavy-work site:

- Heat stress (WBGT) peaked at **10 to 11 AM**; the air peaked at 2 PM.
- **12 of 14 daylight hours** were High or above. Telangana's "12 noon to 3 PM" covers 3 of them; Delhi's "12 to 4 PM" covers 4.

Archive/reanalysis is not an on-site reading, and the site adjustments are provisional. Full table and caveats: [`docs/replay-day.md`](docs/replay-day.md). Reproduce: `cd backend && python -m evaluation.replay_real_day --date 2024-05-04`.

## What it does

- **Public heat check, no login.** Site-specific WBGT estimate (Liljegren et al. 2008, via pywbgt) from the Open-Meteo forecast plus shade, surface, land use and wind, with a 1 °C safety margin.
- **NIOSH work-rest schedule.** Bands A Normal 60/0, B Caution 45/15, C High 30/30, D Very high 15/45, and Stop above the 15-minute limit. Unknown acclimatisation uses the stricter RAL curve.
- **Alert about an hour ahead** when the schedule is about to tighten.
- **Proof of rest.** The supervisor acknowledges each break; workers confirm anonymously by QR (no names, phones or device IDs; counts hidden until three responses).
- **Symptom buttons only tighten** the plan, never ease it.
- **Rulebook agent.** Reads a heat action plan PDF and proposes rules, each with its exact quote and page. A person approves every rule. The app applies whichever is stricter, the plan or the physiology.
- **Self-playing demo** with clearly labelled synthetic data.

## Evidence

| Check | Result | How to run |
|---|---|---|
| WBGT vs an independent pure-Python Liljegren implementation (5 cases, Hyderabad) | differences +0.45, +0.23, +0.30, −0.01, +0.32 °C (tolerance 1.5) | `cd backend && python -m pytest tests/test_wbgt_crosscheck.py -v -s` |
| Physical sanity: more humidity, less shade or less wind never lowers WBGT in sun | pass | same file |
| Rulebook answer key: Delhi HAP 2025, every row checked by hand against the PDF page | 48 rows; 15 on scanned pages flagged | `tests/test_rulebook_answer_key.py` |
| Rulebook answer key: Telangana HAP 2021, every row checked by hand | 26 rows; plan gives two conflicting peak windows (p.35, p.59) | `tests/test_rulebook_answer_key_telangana.py` |
| NIOSH thresholds equal the RAL/REL equations (section 8.1), rounded down | pass for every row | `tests/test_niosh_equations.py` |
| Rulebook agent recall / precision on the Delhi plan | _pending Bedrock run_ | `python -m evaluation.score_rulebook candidates.json tests/data/heat_action_plans/delhi_hap_2025_obligations.csv` |

## Run locally

Requires Python 3.12 (numpy 2.5.3), Node and pnpm.

```
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements-dev.txt
pnpm install
pnpm dev                      # API on :8000, web on :3000
cd backend && python -m pytest -q
```

## Architecture on AWS

ShiftShield deploys serverless to **`ap-south-1` (Mumbai)** with the AWS Serverless Application Model (SAM). AI rule extraction calls Amazon Nova Pro in `us-west-2` (set by `BEDROCK_REGION`), because Bedrock quotas in ap-south-1 were zero for our account; its input is a public government PDF.

```text
┌─────────────────┐       ┌─────────────────┐       ┌──────────────────────┐
│  React 19 SPA   │ ────► │ API Gateway v2  │ ────► │ FastAPI API Lambda   │
│ (Amplify / S3)  │       │   (HTTP API)    │       │   (Python 3.12)      │
└─────────────────┘       └─────────────────┘       └──────────┬───────────┘
                                                               │
┌─────────────────┐       ┌─────────────────┐                  ▼
│  EventBridge    │ ────► │ 15-min Evaluator│ ─────► ┌───────────────────┐
│ Scheduler (15m) │       │ Lambda + DLQ    │        │ Amazon DynamoDB   │
└─────────────────┘       └────────┬────────┘        │ (9 on-demand      │
                                   │                 │  tables with TTL) │
                                   ▼                 └───────────────────┘
                          ┌─────────────────┐                  ▲
                          │ AWS SNS Topic   │                  │
                          │ (Alert Emails)  │ ─────────────────┘
                          └─────────────────┘
```

- **API & Compute**: Amazon API Gateway HTTP API v2 invoking FastAPI (Python 3.12 via Mangum) with least-privilege IAM roles.
- **Scheduled Evaluator**: Amazon EventBridge Scheduler triggers the evaluator Lambda every 15 minutes with SQS Dead Letter Queue and CloudWatch alarms.
- **Data Persistence**: 9 Amazon DynamoDB on-demand tables (`sites`, `site_state`, `alert_keys` with 48h TTL, `issue_log`, `acks`, `rest_confirms`, `rulebooks`, `obligation_log`, `replay_runs`).
- **Alert Dispatch & Proof**: Amazon SNS email delivery with single-use HMAC-SHA256 supervisor acknowledgement links (`/ack/{token}`) backed by AWS Secrets Manager.
- **Infrastructure as Code**: Single-command automated deployment via [`template.yaml`](template.yaml):
  ```bash
  sam validate --lint
  sam build --use-container
  sam deploy --guided
  ```
  See [`docs/aws-deployment-guide.md`](docs/aws-deployment-guide.md) for step-by-step instructions.

## Repository map

| Path | What is there |
|---|---|
| `backend/app/` | FastAPI app: WBGT physics, NIOSH scheduling, alerts, rest record, rulebook agent |
| `backend/app/config/` | Versioned threshold and site-adjustment files, with sources |
| `backend/tests/` | Test suite, independent WBGT reference, heat action plan PDFs and answer keys |
| `backend/evaluation/` | Real-day replay, rulebook extraction runner and scorer |
| `frontend/` | React app: heat check, setup, dashboard, worker QR page, replay, rulebooks |
| `template.yaml` | AWS SAM infrastructure |
| `docs/` | Evidence, NIOSH method note, deployment guide, video script |

## Sources

- NIOSH (2016). *Criteria for a Recommended Standard: Occupational Exposure to Heat and Hot Environments*, DHHS (NIOSH) Publication 2016-106. RAL/REL equations, section 8.1.
- Liljegren, J. C. et al. (2008). Modeling the wet bulb globe temperature using standard meteorological measurements. *J. Occup. Environ. Hyg.* 5(10).
- Delhi Disaster Management Authority, Heat Action Plan 2025. Government of Telangana, Heatwave Action Plan 2021.
- Weather data and place search by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0).

## Credits

Open-source libraries we use, each under its own licence: pywbgt (Kyle R. Wodzicki), NumPy, pandas, MetPy, FastAPI, Mangum, pypdf, boto3, Strands Agents, AWS Lambda Powertools, React, Vite, Recharts, lucide-react. The two heat action plan PDFs are public government documents, included unchanged for testing.

## AI tools used

- **Claude (Anthropic):** research, the reference WBGT engine, test and evaluation code, documentation, debugging (Sameer).
- **Google Antigravity & Gemini 3.8:** AWS SAM serverless architecture design, DynamoDB data modeling, alert deduplication & evaluator engine, proof-of-rest verification loop, UI/UX polish, and deployment pipelines (Gufran).
