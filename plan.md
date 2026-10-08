# ShiftShield implementation plan — Final Plan v7 aligned

## Sources and precedence

Primary source: the supplied `ShiftShield_Final_Plan_v7.pdf` (EcoNexus, Environmental Hacks 2026, Oct 5, 2026), read with the detailed requirements in `pasted_content.txt`. Where they differ, the PDF is authoritative, as the brief requested. The PDF itself says this is a planning document; its example values and the site-coefficient ranges are not measurements and must not be represented as validated.

Resolved priority discrepancy: PDF §4 / R11 makes the rulebook agent and daily compliance **P0 for the stated two-person team**, even though the pasted brief classifies it P1. The build will deliver the quote-verification / human-approval pipeline after the core alert → ack → QR rest loop is stable. Photo-to-profile and the shift re-planner are P2 in PDF R18 (deferred, despite their earlier descriptions in the pasted prompt). Escalation, voice, heat-day certificate, rupee payback and AI wording are P1. WhatsApp, sensor checks, missed-call confirmation, hash chain and integrations are P2. The PDF’s core definition of done and safety/privacy requirements remain in force.

The repository’s initial scaffold commit was verified as `2026-10-08 06:37:19 +0000`, on the hackathon’s Oct 8 kickoff date. Keep implementation commits chronologically after that; do not import pre-kickoff code or imply otherwise.

## Product goal and P0 cutline

Ship one operationally coherent product, not a weather mockup. The proof loop is:

`Open-Meteo forecast → site profile + 15-minute WBGT → cited deterministic schedule → email/in-app heads-up about an hour early → signed one-tap supervisor acknowledgement → anonymous QR responses → one of four rest-record states → physiology + approved plan compliance → append-only log and ledger`.

P0: manual site profile; public no-login heat check; site-specific WBGT series with margin and comparisons; versioned work/rest engine; 15-minute evaluator; email alert (AWS SNS email subscription when configured) and one-use acknowledgement; append-only issue log; supervisor dashboard/chart; rest QR and optional symptoms; data-derived ledger; historical/replay backtest; deterministic self-playing `/demo`; and (for the two-person plan) uploaded-plan extraction, exact quote/page verification, human approval, and a daily compliance view. A stranger should reach useful advice in about 10 seconds; demo autoplay must show the full loop in under 3 minutes. The code runs locally without an AWS account; actual AWS use is provisioned with SAM and requires credentials/account access unavailable in this session.

## P0 scientific configuration and source handling

### WBGT

Use the plan’s outdoor physical-method option (published Liljegren et al. model) as the candidate site-WBGT engine; do not substitute heat index, Stull wet-bulb alone, apparent temperature or dry-bulb thresholds. Candidate library is `pywbgt==3.0.7` (GPL-3.0; its documented Liljegren implementation needs a C compiler/OpenMP and unit-aware meteorological inputs). The source comparison by Lemke et al. 2012 recommends Liljegren for outdoor meteorological WBGT and cautions that it can underestimate indoor natural wet-bulb; evaluate the package on the Lambda build target and add pinned license notices. If the native dependency cannot be built reproducibly for Lambda, do not silently switch methods: disable live safety evaluations until a compatible, reviewed method is selected. Preserve the PDF’s WBGT definitions: direct sun `0.7*Tnwb + 0.2*Tg + 0.1*Tdb`; indoor/no sun `0.7*Tnwb + 0.3*Tg`.

Fetch the PDF’s listed Open-Meteo hourly temperature, RH, wind, shortwave, direct and diffuse radiation; interpolate forecast values to 15-minute schedule intervals and label the underlying hourly data resolution. Record raw inputs, forecast age, method/version and site profile version with every result. Apply the supplied site equations `S_site=(1-shade)*S_direct+S_diffuse+k_surface*S_total`, `T_site=T_air+dT_landuse`, same vapor pressure for `RH_site`, `u_site=f_wind*u_10m`, then WBGT model and configurable conservative margin (v7 says start near 1°C and justify by sensitivity analysis).

`site_adjustments.v1.json` will record the PDF’s stated starting assumptions verbatim and mark each `provisional_demo_only`: shade 0–about 0.8, surface factor small (grass about 0.05; light concrete about 0.20–0.25), land-use adjustment about 0 to +2°C, wind factor about 1.0 open to 0.4 sheltered. Do not label those as independently sourced or calibrated. Prioritize shade, keep surface effect small, and show sensitivity. V7 itself cites a field comparison where on-site WBGT was roughly 2.4–2.5°C above regional-station estimates and differences among tested surfaces were largely insignificant. The model’s accuracy is therefore explicitly unvalidated until field checks; profile estimate is not a site sensor reading.

### Work/rest thresholds

Source: CDC/NIOSH *Criteria for a Recommended Standard: Occupational Exposure to Heat and Hot Environments*, DHHS (NIOSH) Publication 2016-106. Official PDF: https://www.cdc.gov/niosh/docs/2016-106/pdfs/2016-106.pdf.

- Use Table 5-1 (printed p.70) for workload classes / comparison; the NIOSH column gives acclimatized continuous WBGT limits (resting 33°C; light 30°C for <200 kcal/h; moderate 28°C for 201–300 kcal/h; heavy 26°C for 301–400 kcal/h; very heavy 25°C for 401–500 kcal/h).
- For acclimatized exposure use Figure 8-2 / REL (printed p.95); for unacclimatized or unknown use the more conservative Figure 8-1 / RAL (printed p.94). Both figures plot WBGT against metabolic heat with 15/30/45/60 work-minutes per hour lines, and the axes describe a standard person; they are curves, not a machine-readable work/rest lookup. Thus the threshold JSON must identify values as **conservative digitizations of the cited curves**, cite the exact figure/page and threshold source version, state the workload mapping, and be reviewed before any field deployment. Do not cite NIOSH Table 6-2/6-3 air-temperature/EPA work/rest examples as WBGT thresholds.
- Use work/rest curve transitions to define the four product bands: below the 60-min/h line = A NORMAL / 60 work:0 rest; crossing the 60 line = B CAUTION / 45:15; crossing the 45 line = C HIGH / 30:30; crossing the 30 line = D VERY HIGH / 15:45. Above the 15-min/h curve add the source-backed reschedule/stop-nonessential-heavy-work control; do not claim that 15:45 makes conditions safe above the final curve. Tie/boundary selects the more conservative schedule. Band names are product labels around NIOSH limit curves, not official NIOSH risk-band terminology.
- The chart is graphical, so script/config comments document the plotted workloads used (upper edge of the selected NIOSH workload class), calibration, conservative half-degree rounding and remaining professional-review status; every threshold row includes source/page/version, work intensity, acclimatisation, WBGT limit/range, schedule, water guidance and additional controls. Until an occupational safety professional reviews the transcription, expose it only in the clearly marked hackathon demo, never as field-ready guidance.
- Clothing: NIOSH Table 3-2 (printed p.19) gives 2006 WBGT adjustments: baseline work clothes 0°C, cloth coveralls 0°C, double-layer cloth 3°C, SMS coveralls 0.5°C, polyolefin coveralls 1°C, limited-use vapor-barrier coveralls 11°C. NIOSH also says two-layer clothing lowers limits by 2°C and partially air/vapor-impermeable protective ensembles by 4°C, with caveats; WBGT is not appropriate for fully impermeable encapsulating ensembles. Do not pretend “heavy” or “impermeable” form options unambiguously identify these exact garments. The engine applies the more conservative documented adjustment only where mapped/confirmed and otherwise warns and uses cautious handling.
- Water guidance cites NIOSH’s one 8-oz cup every 15–20 minutes (executive summary printed page vi). This is general source guidance, not personalized medical advice. Every view displays “Decision support, not medical advice. Follow official local safety guidance.” The supplied plan’s fixed emergency footer is: “Shade, cool the person, water if conscious; call 112 for confusion, fainting or hot dry skin.” Keep it fixed/code-authored, not AI-generated.
- Keep all NIOSH-derived data in `backend/app/config/thresholds.v1.json`; record threshold/source version in every issue-log event. Unknown profile values select unacclimatized/cautious assumptions. Stale weather uses last good forecast plus cautious behavior. Tightening acts immediately; easing requires below threshold-minus-buffer for two consecutive evaluations. The buffer is configurable and disclosed as an engineering assumption, not a NIOSH medical threshold.

### Rulebook and compliance

P0 for this two-person team. PDF uploads are extracted page-by-page (use Textract for scans where configured; local text PDF parser for searchable PDF). The Strands/Bedrock agent proposes structured obligations only. Code checks the exact quote against the indicated page; reject unverifiable quotes before review. A human approves/edits/rejects every candidate; store rule version, quote, page, approver and timestamp. Daily compliance combines the approved local policy with the physiological plan and applies the stricter constraint for every interval; never schedule work during mandated rest. Status is met/not met/unconfirmed with timestamp/evidence; rest derives from two-sided record, water/shade from anonymous worker aggregate answers and checklist items from supervisor. Do not preload fictitious approved legal rules. No local Indian city action-plan source PDFs were supplied, so demo starts with “No plan approved” and the upload/verification/approval pipeline is functional; a synthetic fixture exists only in tests and is explicitly not law/policy.

## P0 workflows

1. **Public heat check:** no login, browser location or manually selected coordinates, sun/shade/profile inputs, forecast, estimated site WBGT + margin = conservative WBGT, current/upcoming band, work/rest/water/shade actions, next-hours chart/timeline, data freshness, and clear estimate/safety disclaimer.
2. **Setup:** site name/location, surface, shade, enclosure, intensity, acclimatisation, PPE, shift start/end, tasks, supervisor contact (email), language. Explicit email-alert opt-in timestamp, opt-out/deletion. Photo-assisted setup is deferred. Unknowns choose cautious values.
3. **Supervisor dashboard:** current site/time/status/band/WBGT/freshness, current schedule, transition and countdown, chart/bands/timeline, email/in-app alert state, one-tap acknowledgement, anonymous worker counts and combined rest status, compliance, QR, ledger/backtest/replay.
4. **Alert:** 15-minute evaluation during a shift; 45–75 minute lead target (about 60); send immediately below 30 minutes; pending forecast movement updates the existing pending alert without a duplicate message; genuinely stricter transitions bypass the same-type cooldown; no duplicates through DynamoDB conditional idempotency key `siteId + shiftDate + fromBand + toBand + windowStart`. Heads-up includes current/new conditions, change time, schedule, reason, signed link. Acknowledge token is alert/site-bound, single-use, expires shift end, and can only acknowledge. At 20 minutes without tap send one reminder; no nagging. Email delivery via SNS topic/subscription once configured; demo uses in-app alert and deterministic mailbox. Never claim an email was sent in local demo.
5. **Worker QR:** `/rest/{siteCode}`, no login, local-language large buttons “We got the break” / “No break”, optional water and shade yes/no, optional dizzy/cramps/headache symptoms. Only accept during an issued break window. Store counts only, hide yes/no split until 3 responses, do not expose individual response or retain identity/phone/device/network fingerprints. The PDF proposes a random browser token to limit one response per phone, but the explicit pasted privacy requirement prohibits stored device identifiers; do not store that token. Explain that anonymous aggregate counts cannot guarantee de-duplication or prove a break occurred. Supervisor states Sent/Acknowledged/Not acknowledged; workers No response/Responses received/Majority YES/Majority NO; combined: green confirmed by both, amber supervisor only, red disputed if supervisor ack plus majority NO, grey no record. The supervisor action is explicitly “BREAK STARTED” and creates an append-only self-report at the issued rest-window start; it does not wait until the window ends or prove completion. Symptom threshold and one-band tightening are configurable demo assumptions; symptoms may only tighten the plan and notify the supervisor.
6. **Ledger/backtest/replay:** daily rest minutes prescribed/confirmed, heat risk, lost/preserved work, missed-danger, needless-alarm, lead time, confirmation rate, sensitivity; only calculate if data supports it. Rupee savings are P1 and require a user-entered wage assumption. Backtest compares the site WBGT to an explicitly labelled fixed city dry-bulb baseline (not the NIOSH WBGT rule). Archive/replay source/date and values. Two-site demo shares identical city weather and contrasts reflective concrete/low shade/heavy with partial shade/moderate, with all synthetic/site-adjustment values marked as replay. Demo events include 8:00 normal, 10:00 caution, 11:30 high, 13:00 very high and full workflow in under 3 minutes.

## P1/P2 after the P0 loop is proven

P1: no-ack escalation (15-minute chain, shortened timers in replay); voice alert in local language (verify Polly voice support first); heat-day signed certificate; rupee payback ledger if wage data is supplied; bilingual AI wording/explanations; advanced analyses.

P2: photo-to-profile (one/two site-only photos, Bedrock suggestions validated against allowed options, confidence, supervisor confirmation, delete image after save); deterministic shift re-planner (only reorder tasks/start up to two hours early/move long break; maximize safe work minutes; tie-break toward less C/D time; never relax work/rest rule); WhatsApp, sensor, missed-call, hash chain, OSM/land-cover integrations. Note: summary line in PDF earlier labels re-planner/photo optional, while R18 explicitly assigns both P2; R18 is the implementation cutline.

## Architecture and project structure

- Frontend: React/TypeScript/Vite. Public static site route and interactive SPA; `/manus-routes.json` accurately lists pages. Preview is a working local-service preview; not an AWS deployment.
- Backend: Python 3.12 FastAPI application exported through Mangum for AWS API Gateway HTTP API → Lambda. One API Lambda plus a scheduled evaluator Lambda with separately scoped IAM roles; P0 rulebook invoke is on the AWS stack. No always-on backend.
- Weather: Open-Meteo forecast/history API, timeouts, validation, hourly-to-15-minute interpolation and freshness metadata.
- Data: DynamoDB on-demand, logical entities/tables in the brief (sites, site_state, alert_keys with TTL, issue_log append-only, acks, rest_confirms aggregate counts only, rulebooks, obligation_log, replay_runs). Local SQLite/memory repository for development only. Signed one-use acknowledgements and conditional writes. Per-site high-entropy supervisor bearer capability is created at setup, returned once, stored only as a salted hash and required for supervisor dashboard/plan changes; worker QR and public heat check remain anonymous. Demo fixtures bypass supervisor auth only while demo mode is enabled. No PII/device fields in rest responses or logs.
- Alerts: SNS topic with email subscription/explicit opt-in and confirmation; a post-confirmation check hashes SNS endpoints transiently and persists no raw email. EventBridge Scheduler/evaluation; one reminder at 20 minutes; dead-letter queue, retries, CloudWatch alarms. Secret/signing material lives in Secrets Manager when deployed.
- AI/documents: Bedrock + Strands Agents SDK for candidate-only rule extraction; S3 and Textract only where configured/needed; code quote verification and human approval always gate publication.
- Hosting: Amplify for static build. SAM source covers API, Lambda, DynamoDB, scheduler, SNS/queues, IAM, alarms and parameters; instructions include AWS Budgets warning. Actual deploy requires the team’s AWS account, correct region/model access, email confirmation and credentials.
- Replay compliance and ledger are run-scoped pages backed by the same persisted synthetic supervisor/worker state. They display the two-sided record status while retaining “no approved local action plan”; they never claim legal compliance.

```text
/
  frontend/src/{pages,components,api,styles}  # React/TypeScript product surface
  frontend/public/manus-routes.json           # Preview page-route manifest
  backend/app/main.py                         # FastAPI JSON API + Mangum handler
  backend/app/{physics,scheduling,weather}.py # deterministic site WBGT + forecast adapters
  backend/app/{alerts,rest,rulebook,compliance,replay,ledger}.py
  backend/app/{store,models,config/}           # DynamoDB/SQLite, schema, versioned JSON rules
  backend/app/evaluator.py                     # EventBridge schedule evaluation
  backend/tests/{unit,integration,fixtures}    # deterministic safety/privacy regression suite
  template.yaml                               # AWS SAM API/Lambda/DynamoDB/SNS/scheduler
  docs/{architecture.mmd,api.md,data-model.md,safety-model.md,limitations.md,research-notes.md}
  scripts/                                    # local, fixture, SAM/deploy helpers
  README.md
  plan.md
  TODO.md
```

API route groups preserve the P0 brief: site create/update/forecast/plan/log/compare; signed ack; anonymous rest GET/POST; plans/candidates/rule approval; compliance; ledger; demo/replay; health. P1 certificate and P2 re-planner routes remain explicitly deferred unless implemented end-to-end. Every delivered endpoint validates inputs and emits structured JSON errors; do not expose fake success for unfinished APIs.

## Design direction

- **Design movement:** industrial editorial with field-operations console discipline: high-contrast data hierarchy, clear provenance, no weather-app ornament.
- **Core principles:** (1) safety status is impossible to miss; (2) every recommendation exposes its source and freshness; (3) worker interaction is anonymous, immediate and thumb-first; (4) state changes are calm and reversible, while severe risk is explicit.
- **Color philosophy:** deep navy/charcoal communicates operational trust; ownable ShiftShield orange `#F36B3F` identifies heat/action; amber means caution, red means restrictive risk, and green means confirmed rest. Text labels and icons accompany every color so color is never the sole status channel.
- **Layout paradigm:** asymmetric control-room composition, not a centred card grid: a dominant current-status/action rail, a horizontal time-and-risk spine, then separate evidence/rest and compliance ledgers. Public check and QR use single-column mobile layouts.
- **Signature elements:** (1) a segmented vertical “heat-shield” band next to the current plan; (2) a timeline with a clearly marked alert lead window and work/rest blocks; (3) paired evidence chips for “Supervisor” and “Workers”.
- **Interaction philosophy:** critical actions require one deliberate tap and immediately show their recorded result; forecast projections are distinguished from issued plans; anonymous worker confirmation asks one plain-language question before optional checks.
- **Animation:** 160–220 ms opacity/position transitions for state changes, no looping heat animation, no motion on critical status, replay timeline transitions paced to its controls, and `prefers-reduced-motion` disables nonessential movement.
- **Typography system:** IBM Plex Sans for interface/headline/body; IBM Plex Mono for WBGT, times, thresholds and ledger values. Use tabular numerals, 12–14 px dense evidence text, 16 px body, 28–40 px desktop headings; never set worker actions below 18 px.
- **Brand essence:** “Site-specific heat plans with proof of rest, for shift supervisors and workers—unlike city alerts, ShiftShield records whether the break happened.” Personality: **direct, protective, accountable**.
- **Brand voice:** short, humane and operational—no blame, alarmist filler or legal certainty. Example lines: “HIGH HEAT RISK — rest starts at 12:30.” “Your answer is anonymous. No names or phone numbers.”
- **Wordmark & logo:** a custom split-shield mark, with one vertical half formed from an orange heat bar and the other from two navy rest bars; set beside the SHIFT SHIELD wordmark, never a default-font solo title.
- **Signature brand color:** ShiftShield signal orange `#F36B3F`.

## Validation implications / unresolved external resources

- Threshold data is a manual transcription of NIOSH Figures 8-1/8-2, not an explicit numeric lookup table; report exact graph/page, points/workload, conservative rounding and professional review status. No unreviewed profile is field-ready.
- Site coefficients in v7 are expressly called assumptions; they stay marked provisional and must be sensitivity-tested. The site comparison is illustrative until archived weather/field validation exists.
- Actual Delhi/other-city Heat Action Plan PDF(s), occupational-health professional review, real worker/supervisor field feedback, AWS account/permissions, Bedrock model access, and SNS email confirmation are not supplied. Build general pipeline/UI and tests; do not fabricate their outcomes or claim AWS deployment.
- Repository history must begin on Oct 8; keep the existing dated scaffold as genesis and make normal incremental commits. Do not push a public repository or deploy infrastructure absent explicit account access and permission.
