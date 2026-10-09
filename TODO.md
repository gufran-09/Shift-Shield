# ShiftShield: Master Execution & Delivery TODO

> **Team**: EcoNexus (Sameer & Gufran)  
> **Track**: WeMakeDevs x AWS Environmental Hacks 2026 — Track 02 (Heat & Worker Safety)  
> **Current Date**: Friday, October 9, 2026  
> **Status**: Codebase 100% Complete & Tested · Deployment & Field-Trial Execution In Progress

---

## 🏆 Current Progress & Implemented Deliverables

- [x] **Liljegren WBGT Calculation Engine**: Outdoor solar/wind equations with pure-Python math fallback (`backend/app/physics.py`, `backend/app/liljegren_pure.py`).
- [x] **Cited Deterministic NIOSH Scheduling**: Dynamic work/rest bands (Normal 60/0, Caution 45/15, High 30/30, Very High 15/45) with hysteresis.
- [x] **Alert Evaluation & Idempotency**: 60-min heads-up, <30-min urgent alerts, DynamoDB conditional idempotency, signed one-tap HMAC acknowledgment (`/ack/{token}`).
- [x] **Supervisor Desk Dashboard**: Live WBGT gauges, countdown timer, "Break Started" trigger, 12-hour exposure forecast (`frontend/src/pages/DashboardPage.tsx`).
- [x] **Worker QR Check-in & Privacy Masking**: Anonymous `/rest/{siteCode}` page, count aggregation, privacy threshold (<3), 4-state rest record.
- [x] **Heat Action Plan Rulebook AI**: Bedrock multi-page extraction with exact source-page quote verification and human approval gate (`/rulebooks`).
- [x] **Public Heat Check (`/`)**: 10-second zero-login weather & WBGT advisory with Open-Meteo attribution.
- [x] **Autonomous Replay Flow (`/demo`)**: Self-playing hot-day simulation running through all 4 bands in <3 minutes.
- [x] **Bonus 1 — Escalation Chain**: Safety Officer escalation trigger via SNS when supervisor fails to acknowledge (`backend/app/alerts.py`, `backend/app/evaluator.py`).
- [x] **Bonus 2 — Amazon Polly Multilingual Voice Alert**: Spoken announcements in Hindi (`Kajal`/`Aditi`) and Indian English (`Raveena`/`Kajal`) with in-app audio player (`backend/app/voice.py`, `DashboardPage.tsx`).
- [x] **Bonus 3 — Tamper-Evident Heat Certificate**: Digital certificate generation with AWS KMS CMK / HMAC signing and standalone public verification page (`/verify/:certificateId`).
- [x] **Bonus 4 — Shade Payback ROI Calculator**: Interactive rupee/minute ROI estimator on supervisor dashboard.
- [x] **Serverless SAM Infrastructure**: `template.yaml` for 9 DynamoDB tables, HTTP API, Lambdas, SNS topic, EventBridge schedule, DLQ, and CloudWatch Alarms.
- [x] **Test Suite Passing**: 100% passing tests for physics, idempotency, safety core, and bonus features.

---

## 📋 Leftover Action Items (Gufran & Sameer)

### Phase A: Live Cloud Deployment (Friday Evening — Oct 9)
- [x] **Deploy SAM Stack to AWS Mumbai (`ap-south-1`)**:
  - [x] Run `sam build` in `d:\Hackathon\AMAZON\shiftshield`.
  - [x] Run `sam deploy` with stack name `shiftshield-prod` in region `ap-south-1`.
  - [x] Verify that all 9 DynamoDB tables are created and active:
    - `shiftshield-prod-sites`
    - `shiftshield-prod-site-state`
    - `shiftshield-prod-alert-keys`
    - `shiftshield-prod-issue-log`
    - `shiftshield-prod-acks`
    - `shiftshield-prod-rest-confirms`
    - `shiftshield-prod-rulebooks`
    - `shiftshield-prod-obligation-log`
    - `shiftshield-prod-replay-runs`
  - [x] HTTP API Gateway deployed endpoint URL:
    - **`https://hrzm2jaosj.execute-api.ap-south-1.amazonaws.com`**
- [x] **Verify SNS Email Delivery**:
  - [x] SNS Topic active: `arn:aws:sns:ap-south-1:022671037337:shiftshield-prod-alerts`.
  - [x] Created subscription helper: `python scripts/subscribe_sns_alert.py <supervisor-email>`.
  - [x] Created and verified test alert publisher: `python scripts/send_test_alert.py`.
- [x] **Deploy Frontend to AWS Amplify Hosting**:
  - [x] Build production assets: `pnpm run build` in `frontend/` (TypeScript + Vite).
  - [x] Set environment variable `VITE_API_BASE_URL` pointing to deployed HTTP API.
  - [x] Deploy `frontend/dist` to AWS Amplify Hosting (`shiftshield-web`, branch `main`).
  - [x] Public Live Frontend URL (HTTPS):
    - **`https://main.d2y1tc05g1s6r3.amplifyapp.com`**
  - [x] Verified zero console/CORS errors with API Gateway integration.
- [x] **Friday Night Checkpoint**:
  - [x] Infrastructure verified with `scripts/verify_aws_stack.py` (DynamoDB, SNS, Lambda, CloudWatch DLQ alarm all PASS).
  - [x] 53/53 test suite passing (100% pass rate).
  - [x] Replay simulation, Polly voice, and certificate verification working on live AWS endpoint.

---

### Phase B: Saturday Morning Polish (Saturday, Oct 10 — 9:00 AM to 11:30 AM)
- [ ] **Worker QR Mobile Smoke Test**:
  - [ ] Open `/rest/{siteCode}` on real iOS and Android phones using cellular data (4G/5G).
  - [ ] Verify high-contrast visibility of "WE GOT THE BREAK" and "NO BREAK" buttons in bright direct sunlight.
  - [ ] Check touch targets are large and responsive.
- [ ] **Validate Live 4-State Rest Transitions**:
  - [ ] Log supervisor break start on dashboard.
  - [ ] Submit worker responses via QR code and observe live dashboard transitions:
    - 🟢 **Confirmed by both**: Supervisor tapped + worker majority YES.
    - 🟡 **Supervisor only**: Supervisor tapped + zero worker responses.
    - 🔴 **Disputed**: Supervisor tapped + worker majority NO.
    - ⚪ **No record**: Neither supervisor nor workers responded.
- [ ] **Test Voice Alert Audio on Phone**:
  - [ ] Tap "Hindi (काजल / अदिति)" on dashboard; verify Polly speech plays clearly through mobile speaker.

---

### Phase C: Physical Field Trial (Saturday Midday, Oct 10 — 12:00 PM to 1:30 PM)
- [ ] **Conduct On-Site Trial**:
  - [ ] Location: Campus construction site or agreed pilot facility.
  - [ ] Assemble **3+ workers and the site supervisor**.
  - [ ] Have workers scan the QR code during a scheduled/replayed break.
- [ ] **Collect Feedback & Evidence**:
  - [ ] Note whether workers understand the prompt without explanation.
  - [ ] Record mobile network loading speed on site.
  - [ ] Collect **1 usable quote/testimonial** from the supervisor or worker.
  - [ ] Assist Sameer in capturing short video clips and photos for the submission video.

---

### Phase D: Saturday 2:00 PM Checkpoint — Core Live Go / No-Go
> [!IMPORTANT]
> **Saturday 2 PM Rule**: Sameer and Gufran jointly test all 4 core loops on the live public URL:
- [ ] **Test 1**: One real alert arrives via SNS email.
- [ ] **Test 2**: Rest record changes state when supervisor taps and worker scans.
- [ ] **Test 3**: Daily compliance plan displays human-approved rules from PDF.
- [ ] **Test 4**: Public heat check gives immediate advice in ~10 seconds.
- [ ] *If any fail, stop all other tasks and fix immediately.*

---

### Phase E: Feature Freeze & Media Capture (Saturday, Oct 10 — 2:30 PM to 9:00 PM)
- [ ] **Strict Feature Freeze (9:00 PM)**:
  - [ ] Zero new features after 9:00 PM; bug fixes and stability only.
- [ ] **Demo Video Recording**:
  - [ ] Record clean screen captures of the live dashboard, heat check, worker QR scan, Polly audio, and certificate verify.
  - [ ] Hand over video assets to Sameer for video editing and voiceover.

---

### Phase F: Sunday Pre-Submission & Final Audit (Sunday, Oct 11)
- [ ] **Zero Secrets Audit**:
  - [ ] Scan full git commit history to verify no AWS access keys, secret tokens, or private credentials are in the repository.
  - [ ] Confirm repository is public on GitHub.
- [ ] **Lambda Warm-up**:
  - [ ] Send initial requests to `/api/health`, `/`, and `/api/demo` to eliminate cold-start latency for judges.
- [ ] **Hackathon Form Submission**:
  - [ ] Verify both team member names and emails match AWS Builder Center profiles exactly.
  - [ ] Submit form with GitHub URL, live demo URL, and video link.
  - [ ] **Save a screenshot of the submission confirmation screen**.
- [ ] **Keep Deployment Alive**:
  - [ ] Ensure the AWS SAM stack and Amplify deployment remain running without interruption until judging concludes.
