# ShiftShield implementation audit — demo-first snapshot

Audit time: 2026-10-08. Scope: current repository state before demo-path fixes; no files were reset or rebuilt.

## DONE (source exists and checks pass)

- Frontend pages exist for public heat check, site setup, supervisor dashboard, anonymous `/rest/{siteCode}`, alert acknowledgement, compliance, ledger/backtest, rulebooks, and replay. `/demo` currently redirects to `/replay`.
- Frontend and Python API are connected by same-origin `/api` calls through Vite’s proxy. Public heat check calls Open-Meteo and the Python WBGT/scheduling path; supervisor, QR, ledger and compliance pages call backend routes.
- Deterministic WBGT, schedule-boundary, anonymized aggregate, acknowledgement, quote-verification, archive-backtest and ledger tests exist. Current baseline: **10 backend tests passed; Pyright 0 errors; TypeScript check passed; production frontend build passed.**
- Local default persistence is SQLite at `/tmp/shiftshield-local.sqlite3`; it has one generic `records` table and nine logical entities: `sites`, `site_state`, `alert_keys`, `issue_log`, `acks`, `rest_confirms`, `rulebooks`, `obligation_log`, `replay_runs`.
- The real-data path is wired to Open-Meteo + the selected physical WBGT adapter; the explicit demo fixture is synthetic and visibly labelled.

## PARTIALLY DONE (code exists; end-to-end behavior still needs runtime proof)

- Public forecast, site setup, plan, live dashboard, supervisor rest acknowledgement and worker QR responses are implemented. The preview/API servers were not running during the initial audit, so the complete live-weather path had not yet been exercised in a browser.
- Core API calls persist through the local SQLite adapter; persistence after refresh has not yet been verified through the full user flow.
- Live QR confirmation counts are aggregate-only and hide the yes/no split until three responses. Live break-window acceptance depends on the actual issued interval.

## BROKEN / DEMO-BLOCKING

- The deterministic replay starts only after the button is clicked and then requires a separate Play/Advance action; it does not immediately auto-run on **START DEMO**.
- Replay acknowledgement and worker responses currently append only `replay_runs` entries. They do **not** update the shared `acks`/`rest_confirms` evidence or drive the dashboard, four-state rest record, compliance and ledger screens. The replay’s optional QR route repeats a replay event instead of recording a site/run-scoped anonymous aggregate.
- Consequently, the supplied end-to-end demonstration cannot yet prove `supervisor acknowledgement + worker aggregate → confirmed-by-both`, or that the recorded result survives a refresh.
- No local Preview/API process was listening during this audit; no preview URL was verified yet.

## NOT STARTED / NOT VERIFIABLE

- **No AWS deployment is verified.** AWS CLI is unavailable and no `AWS_*` credential/region variables are configured in this Sandbox. No SAM/CloudFormation template or `infra/` folder was present at audit time; therefore no AWS service, deployed API URL, region, DynamoDB table, or production frontend can honestly be reported as deployed.
- DynamoDB and other AWS resources have not been created or inspected. The current verified database is local SQLite only.
- Repository work is still uncommitted local changes on `main`; an `origin` remote name exists, but no push/checkpoint or publication has been verified.

## Next action

Fix only the synthetic replay core path: one-click deterministic start; real append-only replay events; run-scoped supervisor break acknowledgement and anonymous aggregate update; dashboard/status/ledger refresh from those persisted events; and a QR page that posts the run-scoped aggregate. Then start Preview and execute the documented browser/API path. Defer nonessential new features and do not claim AWS deployment without actual read-only verification.
