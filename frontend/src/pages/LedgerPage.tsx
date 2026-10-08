import { ArrowDownToLine, BarChart3, Clock3, FileText, ShieldAlert } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api';
import { ErrorNotice, Loading, Metric, PageHeading, SafetyNotice } from '../components/Primitives';
import type { HistoricalBacktestResponse, LedgerResponse } from '../types';

function downloadCsv(data: LedgerResponse) {
  const rows: Array<[string, string]> = [['metric', 'value'], ...Object.entries(data)
    .filter(([key]) => key !== 'latest_backtest')
    .map(([key, value]) => [key, value === null ? 'not available' : String(value)] as [string, string])];
  if (data.latest_backtest) {
    for (const [key, value] of Object.entries(data.latest_backtest)) {
      if (!['timeline', 'limitations', 'sensitivity_analysis'].includes(key) && typeof value !== 'object') {
        rows.push([`backtest.${key}`, value === null ? 'not available' : String(value)]);
      }
    }
  }
  const csv = rows.map((row) => row.map((cell) => `"${cell.replaceAll('"', '""')}"`).join(',')).join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'shiftshield-evidence-ledger.csv'; link.click(); URL.revokeObjectURL(link.href);
}

function chartTime(value: string): string {
  return new Date(value).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function HistoricalComparison({ siteId, initial, onComplete }: { siteId: string; initial?: HistoricalBacktestResponse; onComplete: (value: HistoricalBacktestResponse) => void }) {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [threshold, setThreshold] = useState('');
  const [source, setSource] = useState('');
  const [result, setResult] = useState(initial ?? null);
  const [error, setError] = useState('');
  const [running, setRunning] = useState(false);

  useEffect(() => { if (initial) setResult(initial); }, [initial]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setRunning(true);
    try {
      const value = await api.backtest(siteId, {
        start_date: startDate,
        end_date: endDate,
        baseline_threshold_c: Number(threshold),
        baseline_source: source.trim(),
      });
      setResult(value); onComplete(value);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Historical comparison unavailable.');
    } finally { setRunning(false); }
  }

  return <section className="backtest-section panel-card">
    <div className="card-heading"><div><span className="eyebrow">ARCHIVE / REANALYSIS · NOT FIELD DATA</span><h2>Compare a city alert.</h2></div><FileText size={18} /></div>
    <p className="panel-intro">Enter a fixed dry-bulb alert threshold and cite its public source. ShiftShield compares it with site-profile WBGT and the same deterministic work/rest engine.</p>
    <SafetyNotice>This is a user-supplied city-style baseline, not a NIOSH WBGT limit. Archive/reanalysis is not an on-site observation; interpolated quarter-hours are estimates. If no defensible threshold is available, do not run or interpret a comparison.</SafetyNotice>
    <form className="backtest-form" onSubmit={submit}>
      <label>Start date<input type="date" value={startDate} max={endDate || undefined} required onChange={(event) => setStartDate(event.target.value)} /></label>
      <label>End date<input type="date" value={endDate} min={startDate || undefined} required onChange={(event) => setEndDate(event.target.value)} /></label>
      <label>Baseline threshold (°C)<input type="number" min="10" max="60" step="0.1" value={threshold} required onChange={(event) => setThreshold(event.target.value)} placeholder="e.g. 36.0" /></label>
      <label className="backtest-form__source">Threshold source / page<input type="text" maxLength={300} minLength={6} value={source} required onChange={(event) => setSource(event.target.value)} placeholder="Official city rule or source page" /></label>
      <div className="backtest-form__submit"><button className="button button--primary" type="submit" disabled={running}>{running ? 'FETCHING ARCHIVE…' : 'RUN HISTORICAL COMPARISON'}<ArrowDownToLine size={15} /></button></div>
    </form>
    {error && <ErrorNotice message={error} />}
    {result && <div className="backtest-results">
      <div className="backtest-result-banner"><div><span className="eyebrow">{result.date_range.start} → {result.date_range.end}</span><strong>{result.site_name} · Profile v{result.site_profile_version ?? '—'}</strong><small>{result.archive_source} · {result.interval_count.toLocaleString('en-IN')} quarter-hour intervals</small></div><span className="quote-tag quote-tag--rejected">NOT A SITE MEASUREMENT</span></div>
      <div className="metrics-grid backtest-metrics">
        <Metric label="CITY ALERT HOURS" value={result.city_baseline_alert_hours.toFixed(2)} unit="h" foot={`Raw air ≥ ${result.baseline.threshold_c.toFixed(1)}°C`} />
        <Metric label="SITE HIGH+ HOURS" value={result.site_high_very_high_hours.toFixed(2)} unit="h" foot="WBGT work/rest schedule" accent />
        <Metric label="MISSED-DANGER HOURS" value={result.missed_danger_hours.toFixed(2)} unit="h" foot="Site HIGH+ while city threshold is off" />
        <Metric label="NEEDLESS-ALARM HOURS" value={result.needless_alarm_hours.toFixed(2)} unit="h" foot="City threshold on while site is below HIGH" />
      </div>
      <div className="backtest-chart-card">
        <div className="card-heading"><div><span className="eyebrow">SAME HOURLY ARCHIVE INPUT</span><h3>Dry bulb vs conservative site WBGT</h3></div><span className="chart-key">15-minute interpolation</span></div>
        <div className="backtest-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={result.timeline} margin={{ top: 12, right: 16, left: -18, bottom: 4 }}><CartesianGrid strokeDasharray="3 4" stroke="#d9ded9" /><XAxis dataKey="local_time" tickFormatter={(value: string) => chartTime(value)} minTickGap={36} tick={{ fontSize: 10, fill: '#66706e' }} /><YAxis unit="°C" domain={['auto', 'auto']} tick={{ fontSize: 10, fill: '#66706e' }} /><Tooltip labelFormatter={(value) => chartTime(String(value))} formatter={(value, name) => [`${Number(value).toFixed(1)}°C`, name]} /><Legend /><ReferenceLine y={result.baseline.threshold_c} stroke="#cf6c35" strokeDasharray="6 4" label={{ value: 'City threshold', fill: '#a34c1d', fontSize: 10 }} /><Line type="monotone" dataKey="air_c" name="City dry bulb" stroke="#698080" dot={false} strokeWidth={1.5} isAnimationActive={false} /><Line type="monotone" dataKey="conservative_wbgt_c" name="Site WBGT + margin" stroke="#e86a3b" dot={false} strokeWidth={2.2} isAnimationActive={false} /></LineChart></ResponsiveContainer></div>
        <p className="chart-footnote">Both lines use Open-Meteo hourly archive/reanalysis interpolated to 15 minutes. Site WBGT also uses the versioned provisional site assumptions and WBGT method shown below.</p>
      </div>
      <div className="ledger-two-col backtest-detail-grid"><section className="panel-card"><span className="eyebrow">ALERT LEAD-TIME SAMPLES</span><h3>Earlier warning</h3><p className="panel-intro">Difference between a city threshold episode starting and the first site HIGH+ interval. Zero means both began together.</p>{result.lead_time_minutes.length ? <div className="lead-time-list">{result.lead_time_minutes.map((value, index) => <div key={`${index}-${value}`}><span>RISK EPISODE {String(index + 1).padStart(2, '0')}</span><strong>{Math.round(value)}<small> min</small></strong><i style={{ width: `${Math.min(100, Math.max(8, value / 75 * 100))}%` }} /></div>)}</div> : <div className="empty-inline">No earlier city-threshold episode overlaps a site HIGH+ episode.</div>}<div className="evidence-row"><span>Worker confirmation rate</span><strong>Not present in weather archive</strong></div><div className="evidence-row"><span>1–4 PM legal window</span><strong>Not computed</strong></div></section><section className="panel-card"><span className="eyebrow">UNCERTAINTY SENSITIVITY</span><h3>Shift the safety margin.</h3><p className="panel-intro">Reuses the same physical-model outputs and reclassifies the schedule at each margin; it does not retrain the model.</p><div className="sensitivity-list">{result.sensitivity_analysis.map((item) => <div key={item.uncertainty_margin_c}><span>{item.uncertainty_margin_c.toFixed(1)}°C margin</span><strong>{item.high_or_very_high_hours.toFixed(2)} h HIGH+</strong></div>)}</div><div className="evidence-row"><span>Baseline source</span><strong>{result.baseline.source}</strong></div></section></div>
      <details className="backtest-limits"><summary>Source, method and limits</summary><p>{result.definition}</p><p><strong>{result.wbgt_method ?? 'Liljegren physical WBGT'}.</strong> Threshold set {result.threshold_version ?? 'version unknown'}; default margin {result.default_uncertainty_margin_c?.toFixed(1) ?? '—'}°C. Chart status remains pending occupational review.</p><ul>{result.limitations.map((item) => <li key={item}>{item}</li>)}</ul></details>
    </div>}
  </section>;
}

export function LedgerPage() {
  const { siteId = '' } = useParams();
  const [searchParams] = useSearchParams();
  const demoRun = searchParams.get('demoRun');
  const [data, setData] = useState<LedgerResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  useEffect(() => { let live = true; const request = demoRun ? api.replayDashboard(demoRun).then((board) => board.ledger) : api.ledger(siteId); void request.then((value) => { if (live) setData(value); }).catch((err: unknown) => { if (live) setError(err instanceof Error ? err.message : 'Ledger unavailable.'); }).finally(() => { if (live) setLoading(false); }); return () => { live = false; }; }, [siteId, demoRun]);
  if (loading) return <Loading label="Building ledger from issued plan records…" />;
  if (!data) return <div className="page-stack"><ErrorNotice message={error || 'Ledger not available.'} /></div>;
  return <div className="page-stack"><PageHeading eyebrow={`${demoRun ? 'SYNTHETIC REPLAY LEDGER' : 'DAILY HEAT-HOURS LEDGER'} · ${data.recorded_date}`} title="Count what happened." note="No wages, avoided injuries or completed breaks are inferred without evidence." actions={<button className="button button--secondary" onClick={() => downloadCsv(data)}><ArrowDownToLine size={15} /> EXPORT CSV</button>} />{error && <ErrorNotice message={error} />}{demoRun && <div className="rest-record-foot"><Link to={`/dashboard/demo?demoRun=${encodeURIComponent(demoRun)}`}>RETURN TO SUPERVISOR DASHBOARD <ArrowDownToLine size={14} /></Link><Link to={`/compliance/${encodeURIComponent(siteId)}?demoRun=${encodeURIComponent(demoRun)}`}>VIEW COMPLIANCE RECORD <ArrowDownToLine size={14} /></Link></div>}<SafetyNotice>{demoRun ? 'Replay mode — ledger entries are derived from the synthetic run only; there are no live workers, actual worksite measurements, or approved local legal rules.' : '“Prescribed” is from an issued 15-minute schedule. “Confirmed by both” requires separate supervisor self-report and a worker majority in the same break interval; neither is proof. Anonymous responses are not unique-worker counts.'}</SafetyNotice>
    <div className="ledger-ribbon"><span><BarChart3 size={16} /> {data.issued_plan_intervals} IN-SHIFT 15-MINUTE INTERVALS</span><span><Clock3 size={16} /> {data.evidence_status}</span></div>
    <div className="metrics-grid"><Metric label="HIGH-RISK FORECAST" value={data.heat_risk_hours.toFixed(2)} unit="h" foot="HIGH / VERY HIGH intervals" accent /><Metric label="REST PRESCRIBED" value={data.rest_minutes_prescribed} unit="min" foot="Counted as actual quarter-hour rest intervals" /><Metric label="CONFIRMED BY BOTH" value={data.rest_minutes_confirmed_by_both} unit="min" foot="Self-report + visible worker majority" /><Metric label="STALE HIGH+ DATA" value={data.missed_danger_hours.toFixed(2)} unit="h" foot="Stale/missing during HIGH / VERY HIGH" /></div>
    <div className="ledger-two-col"><section className="panel-card"><span className="eyebrow">ALERT TIMING</span><h2>Lead time</h2><p className="panel-intro">Minutes between an issued stricter-plan heads-up and its forecasted change.</p><div className="lead-time-list">{data.alert_lead_times_minutes.length ? data.alert_lead_times_minutes.map((time, index) => <div key={index}><span>ALERT {String(index + 1).padStart(2, '0')}</span><strong>{Math.round(time)}<small> min</small></strong><i style={{ width: `${Math.min(100, Math.max(8, time / 75 * 100))}%` }} /></div>) : <div className="empty-inline">No dated heads-up transition is in today’s issue log.</div>}</div></section><section className="panel-card"><span className="eyebrow">REST EVIDENCE · ANONYMOUS AGGREGATES</span><h2>Some splits stay hidden.</h2><div className="evidence-row"><span>Anonymous responses (not unique workers)</span><strong>{data.worker_response_count}</strong></div><div className="evidence-row"><span>Windows with ≥3 responses</span><strong>{data.visible_response_windows}</strong></div><div className="evidence-row"><span>Majority YES rate</span><strong>{data.worker_majority_yes_rate === null ? 'Hidden until 3 / window' : `${Math.round(data.worker_majority_yes_rate * 100)}%`}</strong></div><div className="evidence-row"><span>Supervisor self-reported rest</span><strong>{data.rest_minutes_supervisor_self_reported} min</strong></div><div className="evidence-row"><span>Disputed rest</span><strong>{data.rest_minutes_disputed} min</strong></div><div className="evidence-row"><span>Wage savings</span><strong>Not calculated</strong></div><p className="evidence-foot">{data.confirmation_rate_note} {data.wage_savings_note}</p></section></div>
    {!demoRun && <HistoricalComparison siteId={siteId} initial={data.latest_backtest} onComplete={(value) => setData((current) => current ? { ...current, latest_backtest: value } : current)} />}
    <div className="compliance-note"><ShieldAlert size={17} /><span><strong>Forecast estimate, not proof.</strong> A scheduled break, a supervisor self-report and an anonymous worker aggregate are distinct signals. Do not use worker feedback for discipline or performance scoring.</span></div>
  </div>;
}
