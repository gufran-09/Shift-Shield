import { Activity, ArrowRight, CheckCircle2, CirclePause, CirclePlay, Clock3, QrCode, ShieldAlert, SkipForward, Sun } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { BandPill, ErrorNotice, Loading, SafetyNotice } from '../components/Primitives';
import type { DemoManifest, DemoRunState, DemoStep } from '../types';

const bandClass: Record<string, string> = { normal: 'replay-normal', caution: 'replay-caution', high: 'replay-high', very_high: 'replay-very-high' };

export function ReplayPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedRun = searchParams.get('run');
  const [manifest, setManifest] = useState<DemoManifest | null>(null);
  const [runId, setRunId] = useState('');
  const [runState, setRunState] = useState<DemoRunState | null>(null);
  const [active, setActive] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [complete, setComplete] = useState(false);

  useEffect(() => {
    let live = true;
    async function initialize() {
      try {
        const result = await api.getDemo();
        if (live) setManifest(result);
        if (requestedRun) {
          const state = await api.replayState(requestedRun);
          if (live) { setRunId(requestedRun); setRunState(state); setActive(state.current_step); setComplete(state.current_step >= result.steps.length - 1); }
        }
      } catch (err) { if (live) setError(err instanceof Error ? err.message : 'The replay is unavailable.'); }
      finally { if (live) setLoading(false); }
    }
    void initialize();
    return () => { live = false; };
  }, [requestedRun]);

  async function start() {
    setError(''); setComplete(false); setPlaying(false); setActive(-1); setRunState(null); setLoading(true);
    try {
      const run = await api.startReplay();
      setRunId(run.run_id); setSearchParams({ run: run.run_id });
      setManifest((old) => old ? { ...old, steps: run.steps, sites: [run.site_a, run.site_b], disclaimer: run.disclaimer } : old);
      setPlaying(true);
    }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not start the replay.'); }
    finally { setLoading(false); }
  }

  const steps = manifest?.steps ?? [];
  const advance = useCallback(async () => {
    if (!runId || !steps.length) return;
    const nextIndex = active + 1;
    if (nextIndex >= steps.length) { setPlaying(false); setComplete(true); return; }
    const step = steps[nextIndex];
    try {
      await api.replayStep(runId, step.event_id);
      setRunState(await api.replayState(runId));
      setActive(nextIndex);
      if (nextIndex === steps.length - 1) { setComplete(true); setPlaying(false); }
    }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not record the replay step.'); setPlaying(false); }
  }, [active, runId, steps]);

  useEffect(() => { if (!playing) return; const timer = window.setTimeout(() => { void advance(); }, 2600); return () => window.clearTimeout(timer); }, [playing, advance]);
  const activeStep: DemoStep | null = active >= 0 ? steps[active] ?? null : null;
  const qrUrl = runId ? `${window.location.origin}/rest/concrete-yard?demoRun=${encodeURIComponent(runId)}` : '';
  const timeToFinish = Math.max(0, steps.length - active - 1) * 2.6;
  const comparison = useMemo(() => steps.map((step) => ({ ...step, delta: Number((step.wbgt_c - step.site_b_wbgt_c).toFixed(1)) })), [steps]);

  if (loading && !manifest) return <Loading label="Loading the synthetic replay fixture…" />;
  return <div className="page-stack replay-page">
    <div className="replay-topline"><span className="eyebrow"><span className="replay-light" /> HOT-DAY REPLAY · {manifest?.fixture_version ?? '—'}</span><span className="synthetic-stamp">SYNTHETIC · NOT FIELD DATA</span></div>
    <section className="replay-hero"><div className="replay-hero__copy"><span className="eyebrow">THE FULL LOOP · UNDER 2 MINUTES</span><h1>From forecast<br />to <em>proof of rest.</em></h1><p>Watch the same city weather meet two different sites, trigger a stricter schedule, reach a supervisor, then get a worker response — all as a clearly labelled deterministic replay.</p><div className="replay-actions"><button className="button button--primary" disabled={loading} onClick={() => void start()}><CirclePlay size={17} />{runId ? 'START NEW DEMO' : 'START DEMO'}<ArrowRight size={15} /></button>{runId && <button className="button button--quiet" onClick={() => setPlaying((value) => !value)}>{playing ? <CirclePause size={17} /> : <SkipForward size={17} />}{playing ? 'PAUSE' : active >= steps.length - 1 ? 'REPLAY COMPLETE' : 'RESUME REPLAY'}</button>}</div>{playing && <div className="replay-speed"><span className="pulse-dot" /> AUTO-ADVANCE · ~{timeToFinish.toFixed(0)} SEC TO FINISH</div>}</div><div className="replay-scorecard"><div className="replay-scorecard__top"><span>SIMULATION BOARD</span><span>00 — 06</span></div><div className="replay-scorecard__sites"><div><span>01 / EXPOSED</span><strong>Reflective Concrete Yard</strong><small>Low shade · Heavy work</small></div><div><span>02 / PARTIAL SHADE</span><strong>Partly Shaded Packing</strong><small>Open wind · Moderate work</small></div></div><div className="replay-scorecard__equals"><span>SAME CITY WEATHER</span><i /><span>DIFFERENT SITE EXPOSURE</span></div><div className="replay-deltas">{comparison.length ? comparison.map((item) => <span key={item.event_id}><b>{item.time_label}</b> {item.delta > 0 ? '+' : ''}{item.delta}°</span>) : <span>6 synthetic time points</span>}</div></div></section>
    {error && <ErrorNotice message={error} onRetry={() => void start()} />}
    <SafetyNotice>{manifest?.disclaimer ?? 'Synthetic values only. Not current weather, field measurements, medical guidance or approved local policy.'}</SafetyNotice>
    <section className="replay-stage"><div className="replay-stage__left"><div className="replay-stage__title"><div><span className="eyebrow">REPLAY SEQUENCE</span><h2>Six turns in <em>the shift.</em></h2></div><span className="replay-counter">{String(active + 1).padStart(2, '0')} <i>/</i> {String(steps.length).padStart(2, '0')}</span></div><div className="replay-steps">{steps.map((step, index) => <button className={`replay-step ${index === active ? 'is-current' : ''} ${index < active ? 'is-done' : ''}`} key={step.event_id} onClick={() => { setPlaying(false); if (index <= active) setActive(index); }} disabled={!runId}><span className="replay-step__number">{index < active ? <CheckCircle2 size={17} /> : `0${index + 1}`}</span><span className="replay-step__time">{step.time_label}</span><span className="replay-step__body"><strong>{step.headline}</strong><small>{step.detail}</small></span><span className={`replay-step__band ${bandClass[step.risk_label] ?? ''}`}>{step.risk_label.replace('_', ' ')}</span></button>)}</div></div>
      <div className={`replay-event-card ${activeStep ? bandClass[activeStep.risk_label] ?? '' : ''}`}>
        {activeStep ? <><div className="replay-event-card__top"><span className="eyebrow">{activeStep.time_label} · SITE A</span><BandPill band={activeStep.risk_label} /></div><div className="replay-event-card__reading"><strong>{activeStep.wbgt_c.toFixed(1)}<small>°C</small></strong><span>WBGT<br />ESTIMATE</span></div><h3>{activeStep.headline}</h3><p>{activeStep.detail}</p>{activeStep.alert && <div className="replay-event-card__alert"><ShieldAlert size={16} /><span>{activeStep.alert}</span></div>}{active === 1 && runState?.alert_ack_path && (runState.alert_acknowledged ? <div className="replay-event-card__confirm"><CheckCircle2 size={16} /> Supervisor alert acknowledgement is stored.</div> : <Link className="inline-link" to={`${runState.alert_ack_path}?return=${encodeURIComponent(`/replay?run=${runId}`)}`}>OPEN SIGNED SUPERVISOR ACK LINK <ArrowRight size={14} /></Link>)}{active >= 2 && runState && <div className="replay-event-card__confirm"><CheckCircle2 size={16} /> {runState.worker_aggregate.total_responses} synthetic aggregate response{runState.worker_aggregate.total_responses === 1 ? '' : 's'} · individual votes hidden.</div>}{active < steps.length - 1 && <button className="button button--primary button--wide" onClick={() => void advance()}>ADVANCE REPLAY <ArrowRight size={15} /></button>}</> : <div className="replay-wait"><div className="replay-wait__icon"><Activity size={20} /></div><span className="eyebrow">AWAITING FIRST EVENT</span><h3>Start the replay<br /><em>to see the plan move.</em></h3><p>Nothing in this screen is a live site measurement.</p></div>}
        {complete && <div className="replay-complete"><CheckCircle2 size={16} /><span>Full synthetic loop complete · forecast → schedule → supervisor → worker response</span></div>}
      </div>
    </section>
    {active >= 2 && runId && <section className="replay-qr-panel"><div><span className="eyebrow">WORKER CHECK-IN · RUN-SCOPED</span><h3>Scan to test the <em>real QR flow.</em></h3><p>Responses update this synthetic run’s aggregate only. The live site ledger is not touched.</p><Link className="inline-link" to={`/rest/concrete-yard?demoRun=${encodeURIComponent(runId)}`}>OPEN SYNTHETIC CHECK <ArrowRight size={14} /></Link></div><div className="replay-qr"><QRCodeSVG value={qrUrl} size={104} level="M" bgColor="#fff" fgColor="#20332c" /><span><QrCode size={13} /> RUN-SCOPED DEMO</span></div></section>}
    {runId && <section className="replay-run-actions"><div><span className="eyebrow">PERSISTED REPLAY BOARD</span><h3>Supervisor, worker and ledger use this <em>same run.</em></h3><p>Refreshes read the local SQLite run record. Synthetic evidence never enters a live site ledger.</p></div><Link className="button button--primary" to={`/dashboard/demo?demoRun=${encodeURIComponent(runId)}`}>OPEN SUPERVISOR DASHBOARD <ArrowRight size={15} /></Link>{runState?.rest_status && <div className="replay-run-status"><span className="rest-status-label">{runState.rest_status.label}</span><span>{runState.worker_aggregate.total_responses} anonymous aggregate responses · {runState.supervisor_break_started ? 'supervisor break-start recorded' : 'supervisor break-start pending'}</span></div>}</section>}
    <section className="replay-schedule"><div className="card-heading"><div><span className="eyebrow">REPLAY HEAT CURVE</span><h2>Two sites. <em>One forecast.</em></h2></div><span className="replay-provenance"><Sun size={14} /> Deterministic fixture</span></div><div className="replay-compare-grid">{steps.map((step, index) => <div key={step.event_id} className={`replay-compare-cell${index === active ? ' is-current' : ''}`}><span>{step.time_label}</span><div className="replay-bars"><div className={`replay-bar ${bandClass[step.risk_label] ?? ''}`} style={{ height: `${Math.max(8, step.wbgt_c * 4.2)}px` }} /><div className="replay-bar replay-bar--second" style={{ height: `${Math.max(8, step.site_b_wbgt_c * 4.2)}px` }} /></div><strong>{step.wbgt_c.toFixed(1)}° <i>/</i> {step.site_b_wbgt_c.toFixed(1)}°</strong><small>SITE A / SITE B</small></div>)}</div><div className="replay-legend"><span><i className="legend-block legend-block--a" /> Site A · low shade · heavy</span><span><i className="legend-block legend-block--b" /> Site B · partial shade · moderate</span></div></section>
    <div className="replay-safety-line"><Clock3 size={16} /><span>This replay checks product flow, not medical advice or a safe-work recommendation. Threshold chart digitization awaits professional review.</span></div>
  </div>;
}
