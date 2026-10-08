import { ArrowLeft, ArrowRight, Check, Copy, Mail, MapPin, ShieldCheck, TriangleAlert } from 'lucide-react';
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { ErrorNotice, SafetyNotice } from '../components/Primitives';
import { PlaceSearch } from '../components/PlaceSearch';
import type { SiteProfile } from '../types';

type Created = { site: SiteProfile; supervisor_token: string; supervisor_token_notice: string; email_status: string };
const defaultForm = { name: '', latitude: 28.6139, longitude: 77.209, timezone: 'Asia/Kolkata', surface: 'light_concrete', shade: 'none', wind_exposure: 'partial_or_unknown', land_use: 'dense_built_up', enclosure: 'open', intensity: 'heavy', acclimatization: 'unknown', ppe: 'normal', shift_start: '08:00', shift_end: '17:00', language: 'en', supervisor_email: '', email_alert_opt_in: false };

export function SetupPage() {
  const [form, setForm] = useState(defaultForm);
  const [taskNames, setTaskNames] = useState(['', '', '']);
  const [created, setCreated] = useState<Created | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const set = (key: keyof typeof defaultForm, value: string | number | boolean) => setForm((old) => ({ ...old, [key]: value }));

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('');
    const namedTasks = taskNames.map((name) => name.trim()).filter(Boolean);
    if (namedTasks.length > 0 && namedTasks.length < 3) { setError('Add three tasks, or clear the task list. This keeps the profile complete.'); return; }
    setLoading(true);
    const tasks = namedTasks.slice(0, 6).map((name) => ({ name, intensity: form.intensity, duration_minutes: 120 }));
    try {
      const result = await api.createSite({ ...form, tasks });
      setCreated(result);
    } catch (err) { setError(err instanceof Error ? err.message : 'Could not create the site.'); }
    finally { setLoading(false); }
  }

  async function copyToken() {
    if (!created) return;
    try { await navigator.clipboard.writeText(created.supervisor_token); setCopied(true); window.setTimeout(() => setCopied(false), 1800); }
    catch { setError('Clipboard access is unavailable. Select and copy the token manually.'); }
  }

  if (created) return <div className="setup-success page-stack">
    <div className="success-symbol"><ShieldCheck size={28} /></div><span className="eyebrow">SITE CREATED · {created.email_status.replaceAll('_', ' ').toUpperCase()}</span><h1>Your worksite is<br /><em>on the watch.</em></h1>
    <p className="setup-success__lead">{created.site.name} is ready for its first forecast. The supervisor token below is shown once.</p>
    <div className="token-panel"><div><span className="eyebrow">SUPERVISOR ACCESS TOKEN</span><p>{created.supervisor_token_notice}</p></div><code>{created.supervisor_token}</code><button className="button button--secondary" onClick={copyToken}>{copied ? <Check size={16} /> : <Copy size={16} />}{copied ? 'COPIED' : 'COPY TOKEN'}</button></div>
    <div className="token-warning"><TriangleAlert size={18} /><span>Save this token securely. ShiftShield stores only its salted hash and cannot recover it later. It remains in this browser tab for the current session.</span></div>
    <div className="setup-success__actions"><button className="button button--primary" onClick={() => navigate(`/dashboard/${created.site.site_id}`)}>OPEN SHIFT OVERVIEW <ArrowRight size={17} /></button><Link className="button button--quiet" to="/">RUN PUBLIC HEAT CHECK <ArrowRight size={16} /></Link></div>
  </div>;

  return <div className="setup-page page-stack">
    <Link to="/" className="back-link"><ArrowLeft size={15} /> Back to public heat check</Link>
    <div className="setup-heading"><div><span className="eyebrow">SITE ONBOARDING · 03 MIN</span><h1>Put your shift<br /><em>on the map.</em></h1><p>Tell ShiftShield what the crew is working in. Unknown values stay cautious; site coefficients are prototype assumptions.</p></div><div className="setup-counter"><span>PROFILE</span><strong>01 <i>/</i> 01</strong><small>ONE WORKSITE</small></div></div>
    <SafetyNotice>Site adjustments and threshold charts are demo-only, not calibrated site measurements. Professional review is required before field use.</SafetyNotice>
    <form className="setup-form" onSubmit={submit}>
      <div className="setup-form__section"><div className="setup-form__section-head"><span>01</span><div><h2>Where is the work?</h2><p>Site name, coordinates and local timezone.</p></div></div>
        <PlaceSearch onPick={(place) => { set('latitude', place.latitude); set('longitude', place.longitude); if (place.timezone) set('timezone', place.timezone); }} />
        <div className="form-grid form-grid--three"><label>Worksite name<input required minLength={2} maxLength={100} value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="e.g. South Yard — Packing" /></label><label>Latitude<input type="number" step="any" min="-90" max="90" value={form.latitude} onChange={(e) => set('latitude', Number(e.target.value))} required /></label><label>Longitude<input type="number" step="any" min="-180" max="180" value={form.longitude} onChange={(e) => set('longitude', Number(e.target.value))} required /></label><label>Time zone<input value={form.timezone} onChange={(e) => set('timezone', e.target.value)} required placeholder="Asia/Kolkata" /></label></div>
      </div>
      <div className="setup-form__section"><div className="setup-form__section-head"><span>02</span><div><h2>What is the crew working in?</h2><p>Choose the nearest match. Don’t guess about protective clothing.</p></div></div>
        <div className="form-grid form-grid--three">
          <label>Ground surface<select value={form.surface} onChange={(e) => set('surface', e.target.value)}><option value="bare_soil">Bare soil</option><option value="grass">Grass</option><option value="asphalt">Asphalt</option><option value="light_concrete">Light concrete</option><option value="dark_concrete">Dark concrete</option><option value="mixed">Mixed</option></select></label>
          <label>Shade<select value={form.shade} onChange={(e) => set('shade', e.target.value)}><option value="none">None / direct sun</option><option value="partial">Partial</option><option value="mostly">Mostly shaded</option><option value="indoor">Indoor / no sun</option></select></label>
          <label>Enclosure / roof<select value={form.enclosure} onChange={(e) => set('enclosure', e.target.value)}><option value="open">Open / no roof</option><option value="metal_roof">Metal roof</option><option value="concrete_roof">Concrete roof</option><option value="ventilated">Ventilated</option><option value="closed">Closed</option></select></label>
          <label>Wind exposure<select value={form.wind_exposure} onChange={(e) => set('wind_exposure', e.target.value)}><option value="open">Open to wind</option><option value="sheltered">Sheltered</option><option value="partial_or_unknown">Partial / unknown (cautious)</option></select></label>
          <label>Work intensity<select value={form.intensity} onChange={(e) => set('intensity', e.target.value)}><option value="light">Light</option><option value="moderate">Moderate</option><option value="heavy">Heavy</option></select></label>
          <label>Acclimatisation<select value={form.acclimatization} onChange={(e) => set('acclimatization', e.target.value)}><option value="unknown">Unknown (cautious)</option><option value="unacclimatized">New / returning workers</option><option value="acclimatized">Acclimatised workers</option></select></label>
          <label>PPE<select value={form.ppe} onChange={(e) => set('ppe', e.target.value)}><option value="normal">Normal work clothing</option><option value="heavy">Heavy clothing (confirm adjustment)</option><option value="impermeable">Impermeable (needs qualified assessment)</option></select></label>
          <label>Land use<select value={form.land_use} onChange={(e) => set('land_use', e.target.value)}><option value="unknown">Unknown (cautious)</option><option value="vegetated">Vegetated</option><option value="dense_built_up">Dense built-up</option></select></label>
        </div>
      </div>
      <div className="setup-form__section"><div className="setup-form__section-head"><span>03</span><div><h2>Who is on shift?</h2><p>Shift timing, work sequence and the alert contact.</p></div></div>
        <div className="form-grid form-grid--three"><label>Shift start<input type="time" value={form.shift_start} onChange={(e) => set('shift_start', e.target.value)} required /></label><label>Shift end<input type="time" value={form.shift_end} onChange={(e) => set('shift_end', e.target.value)} required /></label><label>Worker language<select value={form.language} onChange={(e) => set('language', e.target.value)}><option value="en">English</option><option value="hi">हिन्दी</option></select></label></div>
        <div className="task-list"><div className="task-list__top"><span className="eyebrow">TASK LIST <small>OPTIONAL — ADD 3 TO 6, OR LEAVE EMPTY</small></span><MapPin size={15} /></div><div className="form-grid form-grid--three">{taskNames.map((name, index) => <label key={index}>Task {index + 1}<input value={name} onChange={(event) => setTaskNames((old) => old.map((item, idx) => idx === index ? event.target.value : item))} placeholder={['Loading / unloading', 'Outdoor packing', 'Material movement'][index] ?? 'Task name'} /></label>)}</div></div>
        <div className="contact-optin"><div className="contact-optin__icon"><Mail size={18} /></div><div className="contact-optin__body"><strong>Supervisor alert contact</strong><p>Contact is sent to AWS SNS only when opting in. ShiftShield stores a hash and consent timestamp — not the email address.</p><label className="field-label">Email address<input type="email" maxLength={254} value={form.supervisor_email} onChange={(e) => set('supervisor_email', e.target.value)} placeholder="supervisor@example.org" disabled={!form.email_alert_opt_in} /></label></div><label className="toggle-row"><input type="checkbox" checked={form.email_alert_opt_in} onChange={(e) => set('email_alert_opt_in', e.target.checked)} /><span>Opt in to heat alerts</span></label></div>
      </div>
      {error && <ErrorNotice message={error} />}
      <div className="setup-submit"><div><ShieldCheck size={18} /><span>Supervisor token shown once · Worker QR remains anonymous</span></div><button className="button button--primary" type="submit" disabled={loading}>{loading ? 'CREATING SITE…' : 'CREATE WORKSITE'}<ArrowRight size={17} /></button></div>
    </form>
  </div>;
}
