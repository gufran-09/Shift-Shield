import { Activity, ArrowRight, BellRing, CheckCircle2, Clock3, Copy, ExternalLink, RefreshCw, ShieldAlert, ShieldCheck, Sun, Wind } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api';
import { BandPill, ErrorNotice, Loading, PageHeading, RestPill, SafetyNotice } from '../components/Primitives';
import type { AlertEvent, LedgerResponse, PlanResponse, ReplayDashboardResponse, RestWindowRecord, SiteProfile } from '../types';

function localTime(value?: string, timezone = 'Asia/Kolkata') {
  if (!value) return '—';
  return new Date(value).toLocaleTimeString('en-IN', { timeZone: timezone, hour: '2-digit', minute: '2-digit' });
}

export function DashboardPage() {
  const { siteId = '' } = useParams();
  const [searchParams] = useSearchParams();
  const demoRun = searchParams.get('demoRun');
  const [site, setSite] = useState<SiteProfile | null>(null);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [windows, setWindows] = useState<RestWindowRecord[]>([]);
  const [events, setEvents] = useState<AlertEvent[]>([]);
  const [ledger, setLedger] = useState<LedgerResponse | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [lastUpdated, setLastUpdated] = useState('');
  const [demoBoard, setDemoBoard] = useState<ReplayDashboardResponse | null>(null);
  const [dailyWage, setDailyWage] = useState(500);
  const [crewSize, setCrewSize] = useState(10);
  const [shadeCost, setShadeCost] = useState(4500);
  const [certificate, setCertificate] = useState<{ certificate_id: string; signature: string; verification_url: string; date: string } | null>(null);
  const [certLoading, setCertLoading] = useState(false);

  const load = useCallback(async (refresh = false) => {
    if (!siteId) return;
    setBusy(true); setError('');
    try {
      if (demoRun) {
        const board = await api.replayDashboard(demoRun);
        setDemoBoard(board); setSite(board.site); setPlan(board.plan); setWindows(board.windows); setEvents(board.events); setLedger(board.ledger);
        setLastUpdated(new Date(board.plan.created_at).toLocaleTimeString('en-IN', { timeZone: board.site.timezone || 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' }));
        return;
      }
      const profile = await api.getSite(siteId);
      setSite(profile.site);
      const nextPlan = refresh ? await api.refreshPlan(siteId) : await api.getPlan(siteId);
      setPlan(nextPlan);
      const [restData, logData, ledgerData] = await Promise.all([api.restWindows(siteId), api.logs(siteId), api.ledger(siteId)]);
      setWindows(restData.windows); setEvents(logData.events); setLedger(ledgerData); setLastUpdated(new Date().toLocaleTimeString('en-IN', { timeZone: profile.site.timezone || 'Asia/Kolkata', hour: '2-digit', minute: '2-digit' }));
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not load this site.'); }
    finally { setBusy(false); }
  }, [siteId, demoRun]);

  useEffect(() => { void load(true); }, [load]);
  const current = plan?.current;
  const siteTimezone = site?.timezone ?? 'Asia/Kolkata';
  const nextChange = useMemo(() => {
    if (!plan?.points.length || !current) return null;
    return plan.points.find((point) => point.time > current.time && point.band !== current.band) ?? null;
  }, [current, plan]);
  const chartRows = plan?.points.slice(0, 48).map((point) => ({ ...point, clock: localTime(point.time, siteTimezone) })) ?? [];
  const qrUrl = site ? `${window.location.origin}/rest/${site.site_code}${demoRun ? `?demoRun=${encodeURIComponent(demoRun)}` : ''}` : '';
  const alertEvents = events.filter((item) => item.event_type === 'heat_alert').slice(0, 4);

  async function ackBreak(windowId: string) {
    if (!site) return;
    try { if (demoRun) await api.replayBreakStarted(demoRun); else await api.acknowledgeRest(site.site_id, windowId); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not record break acknowledgement.'); }
  }

  async function copyQr() {
    if (!qrUrl) return;
    try { await navigator.clipboard.writeText(qrUrl); setCopied(true); window.setTimeout(() => setCopied(false), 1600); }
    catch { setError('Clipboard unavailable. Open the QR link manually.'); }
  }

  async function generateCert() {
    if (!site) return;
    setCertLoading(true);
    try {
      const cert = await api.getCertificate(site.site_id);
      setCertificate(cert);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not generate certificate.');
    } finally {
      setCertLoading(false);
    }
  }

  const riskHours = ledger?.heat_risk_hours ?? 4.0;
  const preservedMinsPerWorker = Math.round(riskHours * 20);
  const totalCrewMinutes = preservedMinsPerWorker * crewSize;
  const hourlyWage = dailyWage / 8;
  const dailyRupeesSaved = Math.round((totalCrewMinutes / 60) * hourlyWage);
  const daysToPayback = Math.max(1, Math.ceil(shadeCost / Math.max(1, dailyRupeesSaved)));

  if (busy && !plan) return <Loading label="Loading site profile and issuing the current plan…" />;
  if (error && !site) return <div className="page-stack"><ErrorNotice message={error} onRetry={() => void load(true)} /><Link className="button button--secondary" to="/setup">Create a site profile</Link></div>;
  if (!site || !plan) return <Loading />;
  const freshness = plan.forecast.forecast_age_minutes;
  const forecastStatus = plan.forecast.data_status ?? 'unknown';
  const shiftEnd = site.shift_end;

  return <div className="page-stack dashboard-page">
    <PageHeading eyebrow={`${demoRun ? 'SUPERVISOR REPLAY' : 'SUPERVISOR DESK'} · ${site.timezone}`} title={site.name} note={`Shift ${site.shift_start}–${shiftEnd} · Profile v${site.profile_version ?? 1}`} actions={<button className="button button--secondary" onClick={() => void load(true)} disabled={busy}><RefreshCw size={15} className={busy ? 'spin' : ''} />{busy ? 'UPDATING…' : demoRun ? 'REFRESH REPLAY' : 'REFRESH PLAN'}</button>} />
    {error && <ErrorNotice message={error} />}
    <div className="dashboard-meta"><span className="dashboard-meta__live"><span className="pulse-dot" /> PLAN ISSUED {lastUpdated && `· ${lastUpdated}`}</span><span>{plan.forecast.source_resolution ?? '15-min intervals'}</span><span>{demoRun ? 'DETERMINISTIC SYNTHETIC REPLAY' : `Forecast age ${freshness == null ? 'unknown' : `${Math.round(freshness)}m`}`}</span></div>
    <SafetyNotice>{demoRun ? plan.safety_disclaimer ?? 'Replay mode — historical/simulated scenario. Values are synthetic fixtures.' : 'WBGT is a forecast-based site estimate, not a sensor reading. Threshold transcription and site coefficients are provisional demo assumptions, pending occupational-safety review.'}</SafetyNotice>

    <section className="dashboard-hero-card">
      <div className="dashboard-hero-card__main"><div className="dash-status-line"><span className="eyebrow">CURRENT CONDITIONS</span><BandPill band={current?.band ?? 'unknown'} /><span className={`freshness-tag freshness-tag--${forecastStatus}`}>{forecastStatus.replaceAll('_', ' ').toUpperCase()}</span></div>
        <div className="dash-reading"><div><strong>{current ? current.wbgt_c.toFixed(1) : '—'}<small>°C</small></strong><span>ESTIMATED SITE WBGT</span></div><div className="dash-reading__equation"><span>+ {current?.margin_c?.toFixed(1) ?? '—'}°C</span><b>=</b><strong>{current?.conservative_wbgt_c?.toFixed(1) ?? '—'}<small>°C</small></strong><span>CONSERVATIVE</span></div></div>
        <div className="dash-plan-line"><div><span className="eyebrow">CURRENT WORK / REST</span><strong>{current?.work_minutes_per_hour ?? '—'} <small>work</small><i> / </i>{current?.rest_minutes_per_hour ?? '—'} <small>rest per hour</small></strong></div><p>{current?.guidance ?? 'Forecast or safety plan unavailable.'}</p></div>
        <div className="dash-microfacts"><span><Wind size={14} /> {current?.wind_speed_10m_m_s?.toFixed?.(1) ?? 'Forecast wind'}</span><span><Sun size={14} /> {current?.source_resolution ?? 'Hourly forecast interpolated'}</span><span><Clock3 size={14} /> Updated {lastUpdated || '—'}</span></div>
      </div>
      <div className="dashboard-hero-card__next"><span className="eyebrow">NEXT SCHEDULE CHANGE</span>{nextChange ? <><div className="next-time">{localTime(nextChange.time, siteTimezone)}</div><BandPill band={nextChange.band} /><p>{nextChange.work_minutes_per_hour} work / {nextChange.rest_minutes_per_hour} rest minutes per hour</p><span className="next-window">Forecast · not a field alarm</span></> : <><div className="next-time">—</div><p>No stricter band change in this forecast window.</p></>}
        <Link className="inline-link" to={demoRun ? `/compliance/${site.site_id}?demoRun=${encodeURIComponent(demoRun)}` : `/compliance/${site.site_id}`}>VIEW DAILY COMPLIANCE <ArrowRight size={14} /></Link>
      </div>
    </section>

    <section className="dashboard-chart-card"><div className="card-heading"><div><span className="eyebrow">SHIFT TIMELINE · NEXT 12 HOURS</span><h2>Heat exposure, <em>by interval.</em></h2></div><div className="chart-legend"><span><i className="legend-line legend-line--solid" /> Conservative WBGT</span><span><i className="legend-line legend-line--dash" /> Estimated WBGT</span></div></div>
      <div className="dashboard-chart"><ResponsiveContainer width="100%" height={264}><AreaChart data={chartRows} margin={{ top: 12, right: 12, left: -16, bottom: 0 }}><defs><linearGradient id="dashFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#e86340" stopOpacity={0.24} /><stop offset="100%" stopColor="#e86340" stopOpacity={0.015} /></linearGradient></defs><CartesianGrid vertical={false} stroke="#e8e5de" strokeDasharray="3 5" /><XAxis dataKey="clock" tick={{ fontSize: 10, fill: '#747a73' }} axisLine={false} tickLine={false} interval={7} /><YAxis tick={{ fontSize: 10, fill: '#747a73' }} axisLine={false} tickLine={false} domain={['dataMin - 1', 'dataMax + 1']} /><Tooltip formatter={(value, name) => [`${Number(value).toFixed(1)}°C`, name === 'conservative_wbgt_c' ? 'Conservative WBGT' : 'Estimated WBGT']} contentStyle={{ borderRadius: 12, border: '1px solid #e8e5de', fontSize: 12 }} /><Area type="monotone" dataKey="conservative_wbgt_c" stroke="#e86340" strokeWidth={2.5} fill="url(#dashFill)" /><Area type="monotone" dataKey="wbgt_c" stroke="#263a33" strokeWidth={1.5} strokeDasharray="5 4" fill="transparent" /></AreaChart></ResponsiveContainer></div>
      <div className="timeline-band-row"><span>RISK BAND</span>{chartRows.filter((_, index) => index % 4 === 0).slice(0, 12).map((point, index) => <div key={`${point.time}-${index}`} className={`risk-block risk-block--${point.band}`} title={`${point.clock} ${point.band}`}><span>{index % 2 === 0 ? point.clock : ''}</span></div>)}</div>
    </section>

    <div className="dashboard-grid">
      <section className="panel-card rest-record-card"><div className="card-heading card-heading--small"><div><span className="eyebrow">REST CONFIRMATION</span><h2>Breaks, from <em>both sides.</em></h2></div><span className="card-heading__badge">ANONYMOUS</span></div>
        <p className="panel-intro">Supervisor tap is a self-report. Worker QR shows aggregate counts only; neither is proof on its own.</p>
        {windows.length === 0 ? <div className="empty-inline">No scheduled break windows in the current forecast.</div> : <div className="rest-window-list">{windows.slice(0, 4).map(({ window, aggregate, status, supervisor_acknowledged }) => {
          const started = !!window.rest_window_start && new Date(window.rest_window_start).getTime() <= Date.now();
          const expired = !!window.rest_window_end && new Date(window.rest_window_end).getTime() < Date.now() - 12 * 60 * 60 * 1000;
          const split = aggregate.split_visible;
          const water = split && aggregate.water_yes_count !== undefined && aggregate.water_yes_count !== null ? `WATER ${aggregate.water_yes_count}/${aggregate.total_responses}` : '';
          const shade = split && aggregate.shade_yes_count !== undefined && aggregate.shade_yes_count !== null ? `SHADE ${aggregate.shade_yes_count}/${aggregate.total_responses}` : '';
          const evidence = split ? [aggregate.majority ? `BREAK ${aggregate.majority.toUpperCase()}` : 'BREAK SPLIT VISIBLE', water, shade].filter(Boolean).join(' · ') : 'response split hidden until 3';
          return <div className="rest-window" key={window.rest_window_id}><div className="rest-window__time"><strong>{localTime(window.rest_window_start, siteTimezone)}</strong><span>{window.work_minutes_per_hour}/{window.rest_minutes_per_hour} min · {window.label ?? window.band}</span></div><div className="rest-window__info"><RestPill status={status} /><span>{aggregate.total_responses} anonymous response{aggregate.total_responses === 1 ? '' : 's'}</span><span className="rest-window__evidence">{evidence}</span><span className="rest-window__evidence">SUPERVISOR: {supervisor_acknowledged ? `✓ BREAK STARTED${demoRun ? ' · SYNTHETIC' : ''}` : 'WAITING'}</span></div><button className={`rest-ack-btn${supervisor_acknowledged ? ' rest-ack-btn--done' : ''}`} disabled={!started || expired || supervisor_acknowledged} onClick={() => window.rest_window_id && void ackBreak(window.rest_window_id)}>{supervisor_acknowledged ? <><CheckCircle2 size={15} /> BREAK STARTED</> : started ? 'BREAK STARTED' : 'AVAILABLE AT BREAK START'}</button></div>;
        })}</div>}
        <div className="rest-record-foot"><span>Counts hide yes/no splits until 3 responses; counts are not unique-worker counts.</span>{demoRun && demoBoard?.alert_ack_path && <Link to={`${demoBoard.alert_ack_path}?return=${encodeURIComponent(`/dashboard/demo?demoRun=${demoRun}`)}`}>Open signed alert ack <ArrowRight size={14} /></Link>}<Link to={demoRun ? `/replay?run=${encodeURIComponent(demoRun)}` : `/ledger/${site.site_id}`}>{demoRun ? 'Return to replay' : 'Open ledger'} <ArrowRight size={14} /></Link></div>
      </section>

      <section className="panel-card qr-card"><div className="card-heading card-heading--small"><div><span className="eyebrow">WORKER CHECK-IN</span><h2>One scan. <em>No names.</em></h2></div><span className="card-heading__icon"><Activity size={17} /></span></div><div className="qr-card__body"><div className="qr-frame"><QRCodeSVG value={qrUrl} size={126} level="M" includeMargin bgColor="#fbfaf6" fgColor="#1c2d27" /></div><div className="qr-card__text"><strong>Break confirmation</strong><p>Public page · no login · counts only. A check is available only inside an issued rest window.</p><a href={qrUrl} target="_blank" rel="noreferrer" className="inline-link">OPEN WORKER PAGE <ExternalLink size={14} /></a></div></div><button className="button button--secondary button--wide" onClick={() => void copyQr()}>{copied ? <CheckCircle2 size={15} /> : <Copy size={15} />}{copied ? 'LINK COPIED' : 'COPY QR LINK'}</button></section>
    </div>

    <section className="dashboard-bottom-grid"><div className="panel-card alert-card"><div className="card-heading card-heading--small"><div><span className="eyebrow">ALERT LOG</span><h2>Plan changes, <em>in context.</em></h2></div><BellRing size={17} /></div>{alertEvents.length ? <div className="alert-list">{alertEvents.map((event, index) => <div className="alert-list__item" key={event.alert_id ?? index}><div className="alert-list__icon"><ShieldAlert size={16} /></div><div><strong>{event.alert_type?.replaceAll('_', ' ') ?? 'Heat alert'} · {event.from_band} → {event.to_band}</strong><p>{event.payload?.reason ?? `Schedule change forecast for ${localTime(event.window_start)}.`}</p><small>{event.delivery_status === 'demo_in_app_only' ? 'In-app demo alert — email was not sent' : event.delivery_status ?? 'Delivery status unavailable'} · {event.created_at ? new Date(event.created_at).toLocaleString() : ''}</small></div></div>)}</div> : <div className="empty-inline">No stricter transition alert has been issued for this plan.</div>}<Link className="inline-link" to={`/ledger/${site.site_id}`}>OPEN APPEND-ONLY LOG <ArrowRight size={14} /></Link></div>
      <div className="panel-card ledger-brief"><div className="card-heading card-heading--small"><div><span className="eyebrow">TODAY’S HEAT LEDGER</span><h2>What the plan <em>accounts for.</em></h2></div><span className="metric-stamp">DATA ONLY</span></div><div className="ledger-mini"><div><strong>{ledger?.heat_risk_hours?.toFixed(1) ?? '—'}<small>h</small></strong><span>HIGH-RISK FORECAST</span></div><div><strong>{ledger?.rest_minutes_prescribed ?? '—'}<small>m</small></strong><span>REST PRESCRIBED</span></div><div><strong>{ledger?.rest_minutes_confirmed_by_both ?? '—'}<small>m</small></strong><span>CONFIRMED BY BOTH</span></div></div><p>No wage savings or completed minutes are inferred without evidence.</p><Link className="inline-link" to={`/ledger/${site.site_id}`}>VIEW FULL LEDGER <ArrowRight size={14} /></Link></div></section>

    <section className="dashboard-bottom-grid">
      <div className="panel-card shade-payback-card">
        <div className="card-heading card-heading--small">
          <div><span className="eyebrow">BONUS FEATURE · ROI ESTIMATE</span><h2>Shade Payback Calculator</h2></div>
          <span className="metric-stamp">~{daysToPayback} DAYS</span>
        </div>
        <p className="panel-intro">Installing shade tarpaulins drops site solar exposure, lowering WBGT by ~1.5–2°C and shifting bands from High/Very High down to Caution/Normal.</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, margin: '14px 0' }}>
          <div><label style={{ fontSize: 11, color: '#747a73', display: 'block' }}>Daily Wage (₹/day)</label><input type="number" value={dailyWage} onChange={(e) => setDailyWage(Math.max(100, Number(e.target.value)))} style={{ width: '100%', padding: '6px 8px', borderRadius: 8, border: '1px solid #d4d0c7' }} /></div>
          <div><label style={{ fontSize: 11, color: '#747a73', display: 'block' }}>Crew Size (workers)</label><input type="number" value={crewSize} onChange={(e) => setCrewSize(Math.max(1, Number(e.target.value)))} style={{ width: '100%', padding: '6px 8px', borderRadius: 8, border: '1px solid #d4d0c7' }} /></div>
          <div><label style={{ fontSize: 11, color: '#747a73', display: 'block' }}>Shade Cost (₹)</label><input type="number" value={shadeCost} onChange={(e) => setShadeCost(Math.max(500, Number(e.target.value)))} style={{ width: '100%', padding: '6px 8px', borderRadius: 8, border: '1px solid #d4d0c7' }} /></div>
        </div>
        <div className="ledger-mini">
          <div><strong>{preservedMinsPerWorker}<small>m</small></strong><span>SAVED / WORKER</span></div>
          <div><strong>₹{dailyRupeesSaved}<small>/d</small></strong><span>CREW SAVINGS</span></div>
          <div><strong>{daysToPayback}<small>d</small></strong><span>BREAK EVEN</span></div>
        </div>
      </div>

      <div className="panel-card certificate-card">
        <div className="card-heading card-heading--small">
          <div><span className="eyebrow">BONUS FEATURE · CRYPTOGRAPHIC AUDIT</span><h2>Heat-Day Certificate</h2></div>
          <ShieldCheck size={18} color="#e86340" />
        </div>
        <p className="panel-intro">Signs today's verified rest compliance ledger with an HMAC cryptographic signature for municipal and OHS inspectors.</p>
        {certificate ? (
          <div style={{ background: '#f5f3ee', padding: 12, borderRadius: 10, margin: '12px 0', fontSize: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <strong>CERT #{certificate.certificate_id}</strong>
              <span style={{ color: '#2d6a4f', fontWeight: 600 }}>✓ SIGNED</span>
            </div>
            <div style={{ color: '#666', marginBottom: 4 }}>Date: {certificate.date}</div>
            <div style={{ fontFamily: 'monospace', fontSize: 10, wordBreak: 'break-all', color: '#888' }}>
              SIG: {certificate.signature.slice(0, 32)}...
            </div>
          </div>
        ) : (
          <button className="button button--primary" onClick={() => void generateCert()} disabled={certLoading} style={{ marginTop: 12 }}>
            {certLoading ? 'SIGNING...' : 'GENERATE SIGNED CERTIFICATE'}
          </button>
        )}
      </div>
    </section>
  </div>;
}
