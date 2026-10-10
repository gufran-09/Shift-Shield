# ShiftShield: the heat alert that proves the rest happened

**Track 02: Heat and Water** · Team EcoNexus (Sameer Ahmed, Gufran Ahmed) · Repo: https://github.com/gufran-09/Shift-Shield · Video: [FILL] · Live app: https://main.d2y1tc05g1s6r3.amplifyapp.com

## The problem

Indian heat action plans tell employers to keep outdoor workers out of the sun at fixed hours: "12 Noon to 3 PM" in Telangana's plan (p.35), "12 to 4 PM" in Delhi's (p.155). But heat stress depends on humidity, sun, wind and how hard someone works, not on the clock. And nobody records whether a break actually happened.

We ran real archived weather for Hyderabad on 4 May 2024 through our pipeline for a heavy-work site. Heat stress (WBGT) peaked at **10 to 11 AM**, while the air peaked at 2 PM. **12 of 14 daylight hours** were high-risk; Telangana's fixed window covers 3 of them. (Reanalysis weather and provisional site factors, so this is an estimate, not a measurement.)

## What we built

- **Public heat check, no login.** Type a place, pick sun or shade, surface and workload. ShiftShield estimates site WBGT (Liljegren et al. 2008, via pywbgt) from the Open-Meteo forecast, adds a 1 °C safety margin, and shows the next 24 hours.
- **NIOSH work-rest schedule.** Limits come straight from the NIOSH 2016-106 RAL/REL equations, averaged over each hour: 60/0, 45/15, 30/30, 15/45, or stop. Unknown acclimatisation gets the stricter limit.
- **Alert about an hour before the schedule tightens**, with one-tap supervisor acknowledgement.
- **Proof of rest.** Workers scan a QR code and answer "we got the break / no break" anonymously: no names, phones or device IDs, and counts stay hidden until three people answer. Symptom reports can only make the plan stricter.
- **Rulebook agent.** Reads a heat action plan PDF page by page and proposes rules with the exact quote and page. Code rejects any quote not found on that page; a person approves every rule; the app applies whichever is stricter, the plan or the physiology.
- **Self-playing demo** with clearly labelled synthetic data.

## Where AWS fits

Live on AWS in ap-south-1 (Mumbai), deployed with AWS SAM: the React app on Amplify Hosting, an API Gateway HTTP API, FastAPI on Lambda (Python 3.12), nine DynamoDB tables, an evaluator Lambda run every 15 minutes by EventBridge with a dead-letter queue, SNS email alerts, CloudWatch alarms on evaluator errors and the dead-letter queue, and Secrets Manager for signed acknowledgement links. The rulebook agent uses Strands Agents with Amazon Bedrock (Amazon Nova Pro, called in us-west-2 because Bedrock quotas in ap-south-1 were zero for our account).

## How we checked it

- Our WBGT matches an independent implementation we wrote from the paper within 0.5 °C on five Hyderabad cases. Physical sanity tests: more humidity, less shade or less wind never lowers WBGT in sun.
- Every threshold equals the NIOSH equation, rounded down. Switching from chart readings to the equations made one live Hyderabad reading stricter (30/30 → 15/45).
- Hand-checked answer keys for both plans: 48 Delhi rows (15 on scanned pages) and 26 Telangana rows. Telangana's plan gives two different peak windows for workers (p.35 and p.59) and never says how long a break should be, which is the gap ShiftShield fills.
- Rulebook agent score on the Delhi plan: [FILL: recall/precision, or "not measured: Bedrock quota was restricted during the event"].
- 49 automated tests.

## Limits

Decision support, not medical or legal advice. Site adjustments are provisional assumptions, not field calibration. Thresholds await occupational-safety review. Worker counts are anonymous, so they show what was reported, not proof that a break happened.

## AI tools used

Claude (Anthropic): research, reference WBGT engine, tests, evaluation tools, docs, debugging (Sameer). Google Antigravity and Gemini: infrastructure, alert engine, frontend (Gufran). [FILL: add Manus if used]

Weather data and place search by Open-Meteo.com (CC BY 4.0).
