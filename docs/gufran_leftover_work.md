# ShiftShield: Gufran's Leftover Work & Execution Checklist

> **Role**: Cloud & Product (*"Everything that runs or is seen"*)  
> **Source Document**: [`docs/ShiftShield_Work_Split_Sameer_Gufran.pdf`](file:///d:/Hackathon/AMAZON/shiftshield/docs/ShiftShield_Work_Split_Sameer_Gufran.pdf)  
> **Partner**: Sameer (*"Engine, rulebook and evidence"*)  
> **Current Date / Status**: October 9, 2026 (Hackathon Day 2 / Friday)  

---

## 1. Role & Ownership Summary

As established in the official work split agreement:
- **Core Ownership**: AWS account & deploy, DynamoDB tables, alert logic and email, API, supervisor dashboard, public heat check, worker QR page, rest record, demo link.
- **Main Languages / Tools**: Python (Lambda functions), TypeScript/React (Web pages), AWS SAM / CloudFormation.
- **Key Outside Contacts**: Site supervisor, workers, and the field-test site.
- **Final Say**: What gets deployed to AWS and when the codebase is frozen.

---

## 2. Status Matrix: Completed vs. Leftover Work

| Area / Item | PDF Specification | Current Codebase Status | Status |
|---|---|---|:---:|
| **Repository Setup** | Public GitHub repo, README stub, MIT License, credits file | Initialized with clean history and license | ✅ **Done** |
| **SAM Infrastructure** | `template.yaml` for 9 DynamoDB tables, HTTP API, Lambdas, SNS topic, EventBridge schedule | Authored in `template.yaml` | ✅ Code Complete (Needs Live Deploy) |
| **Engine & Layer** | WBGT library packaging script for Lambda layer | `scripts/build_layer.sh` created | ✅ **Done** |
| **Alert Engine & Idempotency** | 60-min heads-up, <30-min urgent, 30-min cooldown, hysteresis, DynamoDB conditional idempotency | Implemented in `backend/app/alerts.py` with passing tests | ✅ **Done** |
| **Signed Acknowledgment** | HMAC-signed one-tap supervisor acknowledgment link (`/ack/{token}`) | Implemented in backend & `AckPage.tsx` | ✅ **Done** |
| **Supervisor Dashboard** | Real-time WBGT gauge, countdown timer, "Break Started" button, live status | Implemented in `DashboardPage.tsx` | ✅ **Done** |
| **Worker QR & Rest Record** | Anonymous break verification (`/rest/{siteCode}`), privacy masking (<3), 4-state rest record | Implemented in `rest.py` & `RestPage.tsx` | ✅ **Done** |
| **Rulebook Approval UI** | Candidate rule screen displaying exact verbatim quote and page citation; accept/edit/reject actions | Implemented in `RulebooksPage.tsx` | ✅ **Done** |
| **Public Heat Check** | No-login 10-second check (`/`) with Open-Meteo weather fetch, sliders, plain advice | Implemented in `HeatCheckPage.tsx` | ✅ **Done** |
| **Self-Playing Demo Link** | Autonomous replay flow (<3 min) demonstrating full alert → ack → QR → rest ledger loop | Implemented via `/demo` → `/replay?auto=1` | ✅ **Done** |
| **Bonus: Shade Payback** | Interactive ROI calculator on dashboard showing minutes and rupees preserved | Implemented in `DashboardPage.tsx` | ✅ **Done** |
| **Live AWS Cloud Deploy** | Live deployment to AWS account (`ap-south-1` Mumbai) via SAM + Amplify hosting | `template.yaml` prepared; live stack execution pending | ⏳ **Left Over** |
| **Live SNS Email Delivery** | Confirm supervisor email subscription and end-to-end receipt of real alert email | SNS topic in template; live subscription verification pending | ⏳ **Left Over** |
| **Physical Field Test** | On-site trial with 3+ workers scanning QR during replayed break; collect notes & feedback | Scheduled for Saturday Oct 10 midday | ⏳ **Left Over** |
| **Saturday 2 PM Checkpoint** | Live link verification of all 4 core loops with Sameer | Scheduled for Saturday Oct 10, 2:00 PM | ⏳ **Left Over** |
| **Bonus 1: Escalation Chain** | Step Functions workflow waiting for acknowledgment and timing out to Safety Officer | 20-min reminder coded; full Step Functions state machine pending | ⏳ **Left Over** |
| **Bonus 2: Amazon Polly Voice Alert** | Polly speech synthesis in Indian languages (Hindi/English) with audio link in alert | Not started | ⏳ **Left Over** |
| **Bonus 3: Heat-Day Certificate UI** | Dedicated standalone public verify route (`/verify/:certificateId`) & KMS signing integration | Backend API & card exist; standalone verify page pending | ⏳ **Left Over** |
| **CloudWatch Alarms** | CloudWatch monitoring & alarms for evaluator dead-letter queue (DLQ) and Lambda errors | DLQ defined in SAM; alarms pending | ⏳ **Left Over** |
| **Feature Freeze** | Saturday 9:00 PM strict freeze: no new features, fixes only | Scheduled for Saturday Oct 10, 9:00 PM | ⏳ **Left Over** |
| **Mobile & Secret Audit** | Test on real mobile phone over 4G/5G data; confirm zero secrets in public repo | Scheduled for Sunday Oct 11 early morning | ⏳ **Left Over** |
| **Submission & Keep-Alive** | Submit form, screenshot confirmation, keep deployment alive until judging finishes | Scheduled for Sunday Oct 11 | ⏳ **Left Over** |

---

## 3. Chronological Breakdown of Gufran's Leftover Tasks

### Phase A: Friday Evening (October 9) — Live Cloud Deployment & Integration Check

1. **Deploy SAM Stack to AWS Account (`ap-south-1`)**:
   - Run `sam build --use-container` or `sam build`.
   - Run `sam deploy --guided` to deploy the CloudFormation stack to `ap-south-1` (Mumbai).
   - Verify all 9 DynamoDB tables are active in the AWS Management Console:
     - `SitesTable`, `SiteStateTable`, `AlertKeysTable`, `IssueLogTable`, `AcksTable`, `RestConfirmsTable`, `RulebooksTable`, `ObligationLogTable`, `ReplayRunsTable`.
2. **Verify Live SNS Topic & Email Subscription**:
   - Subscribe supervisor test email address to the created SNS topic.
   - Confirm subscription via email link.
   - Trigger a test evaluation run to confirm real email delivery with the signed acknowledgement link.
3. **Deploy Frontend to AWS Amplify / CloudFront**:
   - Connect the GitHub repository or upload build artifact (`pnpm build`) to AWS Amplify Hosting.
   - Configure environment variables (`VITE_API_BASE_URL` pointing to the deployed API Gateway endpoint).
   - Confirm the public landing page (`/`) opens over HTTPS without errors.
4. **Friday Night End-of-Day Checkpoint**:
   - Verify: A scheduled run on AWS sends one correct email; one heat action plan has gone from PDF to approved rules; replay produces a full day of bands.
   - **Rule**: Sleep on Friday night (*"Tired people break working code"*).

---

### Phase B: Saturday Morning (October 10) — Pre-Test Polish & Verification

1. **Verify Worker QR Mobile Responsiveness**:
   - Open `/rest/{siteCode}` on mobile devices (Android and iOS).
   - Ensure the high-contrast break confirmation buttons (`WE GOT THE BREAK` / `NO BREAK`) and optional symptom checkboxes render clearly in bright outdoor conditions.
2. **Verify Dashboard 4-State Rest Record Display**:
   - Validate live visual state transitions on the dashboard when breaks are logged:
     - 🟢 **Confirmed by both**: Supervisor tapped "Break Started" AND worker responses are majority "YES".
     - 🟡 **Supervisor only**: Supervisor logged break, zero worker responses.
     - 🔴 **Disputed**: Supervisor logged break, workers majority "NO".
     - ⚪ **No record**: Neither supervisor nor workers logged a break.
3. **Validate Self-Playing Demo (`/demo` / `/replay?auto=1`)**:
   - Confirm that navigating to `/demo` automatically steps through the hot-day scenario (8:00 Normal → 10:00 Caution → 11:30 High → 13:00 Very High) within 2–3 minutes.
   - Ensure demo/synthetic data badges remain prominently visible.

---

### Phase C: Saturday Midday (October 10) — The Physical Field Test

1. **Conduct Field Test at Selected Site**:
   - Location: Campus construction site or agreed pilot facility.
   - Have **3 or more workers and the site supervisor** scan the QR code during a replayed/scheduled break.
2. **Observe & Note Worker Behavior**:
   - Test whether workers understand the buttons without explanation.
   - Check mobile data loading speeds on worker phones.
   - Note any confusing UI copy, button sizing issues, or language barriers.
   - Fix any UI confusion immediately upon returning.
3. **Collect Testimonial & Evidence**:
   - Record one usable quote from the supervisor or a worker.
   - Assist Sameer in capturing short video clips / photos for the demo video.

---

### Phase D: Saturday 2:00 PM Checkpoint — Core Live Go / No-Go

> [!IMPORTANT]
> **The Saturday 2 PM Rule**:  
> At 2:00 PM on Saturday, Sameer and Gufran test **four things** together on the live public URL:
> 1. **One correct alert arrives** via email/SNS.
> 2. **The rest record changes state** when supervisor taps and a worker scans.
> 3. **One heat action plan shows approved rules** in the daily compliance plan.
> 4. **The public heat check gives immediate advice** in ~10 seconds.
> 
> *If any one fails, BOTH stop all other work and fix it. Bonus features MUST NOT be started until all four pass.*

---

### Phase E: Saturday Afternoon (October 10, 2:30 PM – 9:00 PM) — Bonus Features

*Per Section 6: Take bonus features strictly in order. One finished bonus feature is worth more than four started.*

#### 1. Bonus 1: Escalation Chain (Step Functions)
- **Concept**: If an alert remains unacknowledged, automatically escalate to higher management.
- **Implementation**:
  - AWS Step Functions state machine or scheduled Lambda evaluator.
  - Timer: Wait 15–20 minutes for supervisor acknowledgment.
  - If unacknowledged: Dispatch an escalation alert to the Safety Officer / Project Manager via SNS.

#### 2. Bonus 2: Voice Alert (Amazon Polly)
- **Concept**: Spoken audio alert for noisy outdoor construction environments.
- **Implementation**:
  - Check Polly Indian language voices (e.g., Hindi `Aditi`/`Kajal`, Indian English `Raveena`/`Kajal`).
  - Synthesize short audio warning: *"Alert: Heat stress reaching High band at 1:30 PM. Mandated 30-minute break in shade."*
  - Store MP3 in S3 bucket and embed audio playback link / player in the notification.

#### 3. Bonus 3: Heat-Day Certificate Public Verification Page
- **Concept**: Cryptographically signed proof of heat compliance for ESG reporting and labor audits.
- **Implementation**:
  - Create dedicated public frontend route `/verify/:certificateId` in React (`App.tsx`).
  - Call `/api/certificates/{certificate_id}` to fetch and display certificate authenticity, issuer, hash, and metrics.
  - Wire AWS KMS CMK signing key ARN if KMS is enabled in SAM environment.

#### 4. CloudWatch Alarm & Reliability
- Create CloudWatch Metric Alarm for Evaluator Lambda error rate > 0 or Dead Letter Queue (DLQ) messages received.

---

### Phase F: Saturday 9:00 PM — Strict Feature Freeze

- **At 9:00 PM**: Code is strictly frozen.
- **No new features** may be started or merged.
- Only critical bug fixes and stability improvements allowed.
- Record product demo screens for Sameer's video walkthrough while all systems are fully functional.
- **Rule**: Sleep on Saturday night.

---

### Phase G: Sunday Morning (October 11) — Submission & Verification

1. **Pre-Submission Health Check (Early Morning)**:
   - [ ] Open every link **signed out**, on an actual mobile phone, using **cellular data (4G/5G)**.
   - [ ] Warm up the Lambda functions with a preliminary request to eliminate cold-start latency for judges.
   - [ ] **Zero Secrets Audit**: Scan repository and commit history to ensure no AWS credentials, secret access keys, HMAC tokens, or passwords are leaked.
   - [ ] Confirm repository is public on GitHub and local setup steps execute cleanly on a fresh clone.
2. **Form Submission (When Form Opens)**:
   - [ ] Fill in the official hackathon submission form with the public GitHub URL, live demo link, and video link.
   - [ ] Verify both team member names (Sameer and Gufran) and email addresses match AWS Builder Center profiles exactly.
   - [ ] Submit the form and **save a screenshot of the confirmation page**.
3. **Post-Submission Duties**:
   - [ ] Share project link in the WeMakeDevs Discord and AWS Builder Center community space.
   - [ ] **Keep Deployment Kept Alive**: Ensure the AWS SAM infrastructure and Amplify deployment remain running without disruption until hackathon judging concludes.

---

## 4. Emergency Cut-Order Protocol

If time slips or an issue arises, follow the agreed cut sequence:

1. **Cut 1**: Drop all unfinished bonus features (Step Functions escalation, Polly voice, KMS certificate) — list them as *"Next Steps / Architecture Roadmap"* in the README.
2. **Cut 2**: Symptom reporting buttons on the worker QR page — show simple break confirmation only (`WE GOT THE BREAK` / `NO BREAK`).
3. **NEVER CUT**:
   - Alert evaluation engine & delivery.
   - Supervisor tap + anonymous worker QR rest record loop.
   - Daily compliance plan table with approved rules.
   - Public zero-login heat check (`/`).
   - Replay / demo mode.
   - Demo video & submission form.

---

## 5. Gufran's Submission Checklist (Section 6 of PDF)

- [ ] **Public repository**: Commit history runs October 8 to 11; zero secrets; setup steps work on a clean machine.
- [ ] **Live link and demo link**: Accessible signed out, on mobile phone, over cellular data.
- [ ] **Form submitted**: Confirmation screenshot saved; both team members' details match Builder Center.
- [ ] **Deployment kept alive**: Cloud deployment kept running until results are announced.
