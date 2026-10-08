import { Activity, ArrowDown, ArrowRight, ArrowUpRight, CheckCircle2, Crosshair, Leaf, MapPin, ShieldCheck, Sun, TriangleAlert, Wind } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api } from '../api';
import { BandPill, ErrorNotice, Loading, SafetyNotice } from '../components/Primitives';
import { RouteHint } from '../components/RouteHint';
import type { PublicHeatCheckResponse } from '../types';

const initial = { latitude: 28.6139, longitude: 77.209, timezone: 'Asia/Kolkata', surface: 'light_concrete', shade: 'none', wind_exposure: 'partial_or_unknown', land_use: 'dense_built_up', enclosure: 'open', intensity: 'moderate', acclimatization: 'unknown', ppe: 'normal' };
const timeLabel = (value: string) => new Date(value).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' });

export function HeatCheckPage() {
  const [form, setForm] = useState(initial);
  const [result, setResult] = useState<PublicHeatCheckResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [geoMessage, setGeoMessage] = useState('');

  const set = (key: keyof typeof initial, value: string | number) => setForm((current) => ({ ...current, [key]: value }));
  const locate = () => {
    if (!navigator.geolocation) { setGeoMessage('Location is unavailable in this browser. Enter coordinates below.'); return; }
    setGeoMessage('Requesting location permission…');
    navigator.geolocation.getCurrentPosition(
      (position) => { set('latitude', Number(position.coords.latitude.toFixed(5))); set('longitude', Number(position.coords.longitude.toFixed(5))); setGeoMessage('Location added. The forecast uses coordinates only for this check.'); },
      () => setGeoMessage('Location permission was not granted. Enter coordinates manually.'),
      { timeout: 8000, maximumAge: 300000 },
    );
  };

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setError(''); setResult(null);
    try { setResult(await api.heatCheck(form)); } catch (err) { setError(err instanceof Error ? err.message : 'Heat estimate unavailable.'); }
    finally { setLoading(false); }
  }

  const current = result?.current;
  const chartRows = result?.timeline.slice(0, 48).map((point) => ({ ...point, timeLabel: timeLabel(point.time) })) ?? [];
  return <div className="landing-page">
    <section className="hero">
      <div className="hero__copy">
        <span className="hero-kicker"><span className="pulse-dot" />SHIFT-SCALE HEAT SAFETY <i /> BUILT FOR REAL WORKSITES</span>
        <h1>Heat plans that<br /><em>prove the rest</em><br />happened.</h1>
        <p className="hero__sub">Site-specific heat risk, actionable work-rest schedules, and worker-confirmed rest records — without installing hardware.</p>
        <div className="hero__actions"><a className="button button--primary" href="#heat-check">CHECK HEAT RISK <ArrowRight size={17} /></a><Link className="button button--quiet" to="/replay">WATCH 2-MINUTE DEMO <ArrowUpRight size={16} /></Link></div>
        <div className="hero__proof"><div className="proof-avatar"><ShieldCheck size={18} /></div><div><strong>Forecast to rest record</strong><span>One clear chain of evidence for every shift.</span></div><span className="proof-lines">01 <i /> 02 <i /> 03 <i /> 04</span></div>
      </div>
      <div className="hero__visual" aria-label="Illustration of a ShiftShield heat-risk shift dashboard">
        <div className="hero-card hero-card--main">
          <div className="hero-card__top"><span><span className="tiny-orange-dot" /> LIVE SITE ESTIMATE</span><span className="mono">DELHI · 13:15</span></div>
          <div className="hero-dial"><div className="hero-dial__arc" /><div className="hero-dial__content"><span>EST. SITE WBGT</span><strong>29.4<small>°C</small></strong><span className="hero-dial__range">+ 1.0° margin <i /> 30.4° conservative</span></div></div>
          <div className="hero-card__rule" />
          <div className="hero-plan"><div><span className="eyebrow">CURRENT WORK / REST</span><strong>30 <small>work</small> <i>/</i> 30 <small>rest</small></strong></div><div className="hero-plan__badge">HIGH</div></div>
          <div className="hero-timeline"><span>08:00</span><i className="timeline-line timeline-line--green" /><span>10:00</span><i className="timeline-line timeline-line--amber" /><span>12:00</span><i className="timeline-line timeline-line--red" /><span>14:00</span></div>
          <div className="hero-annotation"><span className="hero-annotation__signal"><CheckCircle2 size={14} /></span><span>Rest recorded from both sides</span><b>2/2</b></div>
        </div>
        <div className="hero-floating hero-floating--top"><div className="floating-icon"><Wind size={16} /></div><div><span>FORECAST → PLAN</span><strong>15 min intervals</strong></div><span className="floating-check"><CheckCircle2 size={16} /></span></div>
        <div className="hero-floating hero-floating--bottom"><div className="qr-squares" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /><i /><i /></div><div><span>WORKER CHECK-IN</span><strong>No names. No app.</strong></div><span className="floating-arrow">↗</span></div>
        <div className="hero-stamp"><span>BUILT FOR</span><strong>THE SHIFT</strong><small>NOT THE WEATHER APP</small></div>
        <div className="hero-grid-mark" aria-hidden="true">S–</div>
      </div>
    </section>

    <div className="hero-thesis"><span className="hero-thesis__mark">“</span><p>An alert tells you heat is dangerous. <strong>ShiftShield tells you what to do — and records whether it happened.</strong></p><span className="hero-thesis__source">THE SHIFT SHIELD PROMISE</span></div>
    <RouteHint />

    <section className="section-block section-block--tight"><div className="section-heading"><div><span className="eyebrow">THREE SIGNALS, ONE SHIFT</span><h2>From weather alert to<br /><em>rest on the record.</em></h2></div><span className="section-index">01 — 03</span></div>
      <div className="feature-row">
        <article className="feature-card"><span className="feature-card__no">01 / ESTIMATE</span><div className="feature-card__icon feature-card__icon--sun"><Sun size={20} /></div><h3>Heat at the site,<br />not across the city.</h3><p>Estimate outdoor WBGT using the forecast plus shade, surface, wind and enclosure inputs. Every result stays labelled as an estimate.</p><span className="feature-card__foot">SITE PROFILE <ArrowUpRight size={14} /></span></article>
        <article className="feature-card feature-card--dark"><span className="feature-card__no">02 / ACT</span><div className="feature-card__icon feature-card__icon--plan"><Activity size={20} /></div><h3>A schedule people<br />can follow.</h3><p>A deterministic 15-minute work-rest plan shows the next change, what to do and when. No opaque AI safety decisions.</p><span className="feature-card__foot">CITED RULES <ArrowUpRight size={14} /></span></article>
        <article className="feature-card"><span className="feature-card__no">03 / CONFIRM</span><div className="feature-card__icon feature-card__icon--proof"><CheckCircle2 size={20} /></div><h3>The rest is counted<br />from both sides.</h3><p>Supervisors confirm the scheduled break. Workers can respond anonymously by QR. Only aggregate counts are shown.</p><span className="feature-card__foot">NO WORKER ACCOUNTS <ArrowUpRight size={14} /></span></article>
      </div>
    </section>

    <section className="heat-check-section" id="heat-check"><div className="heat-check-intro"><span className="eyebrow">PUBLIC HEAT CHECK <i className="section-mark" /></span><h2>Know the risk<br /><em>at your coordinates.</em></h2><p>Choose the worksite conditions and run a forecast-based estimate. No sign-in. No hardware. No heat-index substitution.</p><div className="heat-check-points"><span><CheckCircle2 size={15} /> WBGT method is shown</span><span><CheckCircle2 size={15} /> 15-minute schedule intervals</span><span><CheckCircle2 size={15} /> Conservative margin made visible</span></div><div className="heat-check-aside"><TriangleAlert size={18} /><span>Prototype threshold curves and site coefficients still need occupational-safety review before field use.</span></div></div>
      <div className="check-form-wrap"><div className="check-form-header"><div><span className="eyebrow">STEP 01 / SITE CONDITIONS</span><h3>Check heat risk</h3></div><span className="form-time"><span className="online-dot" /> ~10 SEC</span></div>
        <form className="check-form" onSubmit={submit}>
          <div className="form-section-label"><MapPin size={15} /> LOCATION</div>
          <div className="form-grid form-grid--location"><label>Latitude<input type="number" step="any" min="-90" max="90" value={form.latitude} onChange={(event) => set('latitude', Number(event.target.value))} required /></label><label>Longitude<input type="number" step="any" min="-180" max="180" value={form.longitude} onChange={(event) => set('longitude', Number(event.target.value))} required /></label><button type="button" className="location-btn" onClick={locate}><Crosshair size={15} /> Use my location</button></div>
          {geoMessage && <p className="inline-hint" role="status">{geoMessage}</p>}
          <div className="form-section-label"><Sun size={15} /> WORKSITE PROFILE</div>
          <div className="form-grid">
            <label>Work intensity<select value={form.intensity} onChange={(event) => set('intensity', event.target.value)}><option value="light">Light</option><option value="moderate">Moderate</option><option value="heavy">Heavy</option></select></label>
            <label>Shade<select value={form.shade} onChange={(event) => set('shade', event.target.value)}><option value="none">None / direct sun</option><option value="partial">Partly shaded</option><option value="mostly">Mostly shaded</option><option value="indoor">Indoor / no sun</option></select></label>
            <label>Ground surface<select value={form.surface} onChange={(event) => set('surface', event.target.value)}><option value="bare_soil">Bare soil</option><option value="grass">Grass</option><option value="asphalt">Asphalt</option><option value="light_concrete">Light concrete</option><option value="dark_concrete">Dark concrete</option><option value="mixed">Mixed</option></select></label>
            <label>Acclimatisation<select value={form.acclimatization} onChange={(event) => set('acclimatization', event.target.value)}><option value="unknown">Unknown (cautious)</option><option value="unacclimatized">New / returning</option><option value="acclimatized">Acclimatised</option></select></label>
          </div>
          <button className="button button--primary button--wide" type="submit" disabled={loading}>{loading ? 'CALCULATING ESTIMATE…' : 'CHECK LOCAL HEAT RISK'}<ArrowRight size={17} /></button>
          {error && <ErrorNotice message={error} />}
        </form>
        {loading && <Loading label="Fetching forecast and calculating site WBGT — no heat-index fallback." />}
        {result && current && <div className="heat-result" aria-live="polite">
          <div className="result-top"><div><span className="eyebrow">SITE ESTIMATE · {result.forecast.source_resolution}</span><h4>{result.location.latitude.toFixed(3)}° N <i>/</i> {result.location.longitude.toFixed(3)}° E</h4></div><BandPill band={current.band} /></div>
          <div className="result-metrics"><div><span>ESTIMATED WBGT</span><strong>{current.wbgt_c.toFixed(1)}<small>°C</small></strong></div><div className="result-equation"><span>+ {current.margin_c.toFixed(1)}°C margin</span><b>=</b></div><div><span>CONSERVATIVE WBGT</span><strong>{current.conservative_wbgt_c.toFixed(1)}<small>°C</small></strong></div></div>
          <div className="result-action"><span className="result-action__tag">CURRENT WORK / REST</span><strong>{current.work_minutes_per_hour} <small>work</small><i>/</i> {current.rest_minutes_per_hour} <small>rest min / hour</small></strong><p>{current.guidance}</p></div>
          <div className="chart-heading"><span>NEXT HOURS <small>WBGT · °C</small></span><span>Source: Open-Meteo · {result.forecast.forecast_age_minutes ?? '—'}m ago</span></div>
          <div className="check-chart"><ResponsiveContainer width="100%" height={190}><AreaChart data={chartRows} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}><defs><linearGradient id="heatFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#e86340" stopOpacity={0.3} /><stop offset="100%" stopColor="#e86340" stopOpacity={0.01} /></linearGradient></defs><CartesianGrid vertical={false} stroke="#e7e4dc" strokeDasharray="3 4" /><XAxis dataKey="timeLabel" tick={{ fontSize: 10, fill: '#7c8179' }} axisLine={false} tickLine={false} interval={5} /><YAxis tick={{ fontSize: 10, fill: '#7c8179' }} axisLine={false} tickLine={false} domain={['dataMin - 1', 'dataMax + 1']} /><Tooltip formatter={(value) => [`${Number(value).toFixed(1)}°C`, 'WBGT']} labelStyle={{ color: '#182421' }} contentStyle={{ borderRadius: 12, border: '1px solid #e4e1d8', fontSize: 12 }} /><Area type="monotone" dataKey="conservative_wbgt_c" stroke="#e86340" strokeWidth={2.5} fill="url(#heatFill)" name="Conservative WBGT" /><Area type="monotone" dataKey="wbgt_c" stroke="#283a33" strokeWidth={1.5} strokeDasharray="4 4" fill="transparent" name="Estimated WBGT" /></AreaChart></ResponsiveContainer></div>
          <SafetyNotice>{result.disclaimer}</SafetyNotice><div className="result-footer"><span>{result.forecast.data_status?.toUpperCase()} FORECAST <i /> {result.threshold_status.toUpperCase()}</span><span>{result.fixed_emergency_footer}</span></div>
        </div>}
      </div>
    </section>

    <section className="closing-cta"><div><span className="eyebrow">THE NEXT STEP</span><h2>Bring the shift<br /><em>into view.</em></h2><p>Set up a site profile and give the supervisor one place to see the plan — and the rest record.</p></div><Link to="/setup" className="button button--light">SET UP A WORKSITE <ArrowRight size={17} /></Link><div className="closing-cta__watermark">S<span>–</span></div></section>
    <div className="landing-bottom"><span><Leaf size={13} /> No sensors. No worker accounts. Aggregate response only.</span><span>Source-backed decision support <ArrowDown size={13} /></span></div>
  </div>;
}
