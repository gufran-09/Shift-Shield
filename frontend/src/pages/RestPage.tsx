import { Activity, Check, ChevronLeft, Clock3, Droplets, Shield, Sun, TriangleAlert } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { BandPill, ErrorNotice, Loading, RestPill } from '../components/Primitives';
import type { RestContext } from '../types';

const translations = {
  en: { brand: 'SHIFT SHIELD', label: 'BREAK CHECK', question: 'Did you get the scheduled break?', yes: 'WE GOT THE BREAK', no: 'NO BREAK', rest: 'SCHEDULED REST', water: 'Was water available?', shade: 'Was shade available?', symptoms: 'How is anyone feeling? (Optional)', skip: 'Choose one or skip', dizzy: 'Dizzy', headache: 'Headache', cramps: 'Cramps', ok: 'OK', submit: 'SEND ANONYMOUS CHECK', done: 'Your response was added to anonymous site totals.', private: 'No name. No phone. No worker profile. Only site-level aggregate counts.', waiting: 'The next scheduled rest period opens at', closed: 'No check is open right now. Follow your site supervisor’s plan.', demo: 'SYNTHETIC DEMO CHECK — NOT A LIVE BREAK', back: 'Back to ShiftShield' },
  hi: { brand: 'शिफ्ट शील्ड', label: 'ब्रेक जाँच', question: 'क्या आपको तय ब्रेक मिला?', yes: 'हाँ, ब्रेक मिला', no: 'नहीं, ब्रेक नहीं मिला', rest: 'तय विश्राम', water: 'क्या पानी उपलब्ध था?', shade: 'क्या छाया उपलब्ध थी?', symptoms: 'कैसा महसूस हो रहा है? (वैकल्पिक)', skip: 'चुनें या छोड़ें', dizzy: 'चक्कर', headache: 'सिरदर्द', cramps: 'ऐंठन', ok: 'ठीक', submit: 'गुमनाम उत्तर भेजें', done: 'आपका उत्तर केवल साइट के कुल गुमनाम आँकड़ों में जुड़ा।', private: 'नाम नहीं। फोन नहीं। कर्मचारी प्रोफ़ाइल नहीं। केवल साइट-स्तर के कुल आँकड़े।', waiting: 'अगला तय विश्राम शुरू होगा', closed: 'अभी कोई जाँच खुली नहीं है। साइट सुपरवाइज़र की योजना का पालन करें।', demo: 'सिंथेटिक डेमो जाँच — वास्तविक ब्रेक नहीं', back: 'ShiftShield पर लौटें' },
};

function siteTime(value: string | undefined, timezone: string | undefined): string {
  if (!value) return '--:--';
  return new Date(value).toLocaleTimeString('en-IN', {
    timeZone: timezone || 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function BoolChoice({ label, icon, value, onChange }: { label: string; icon: 'water' | 'shade'; value: boolean | null; onChange: (value: boolean | null) => void }) {
  const Icon = icon === 'water' ? Droplets : Sun;
  return <div className="rest-question"><div className="rest-question__label"><Icon size={18} /><span>{label}</span></div><div className="choice-row"><button type="button" className={value === true ? 'choice choice--selected' : 'choice'} onClick={() => onChange(value === true ? null : true)}>YES</button><button type="button" className={value === false ? 'choice choice--selected' : 'choice'} onClick={() => onChange(value === false ? null : false)}>NO</button></div></div>;
}

export function RestPage() {
  const { siteCode = '' } = useParams();
  const [params] = useSearchParams();
  const demoRun = params.get('demoRun');
  const [context, setContext] = useState<RestContext | null>(null);
  const [answer, setAnswer] = useState<boolean | null>(null);
  const [water, setWater] = useState<boolean | null>(null);
  const [shade, setShade] = useState<boolean | null>(null);
  const [symptoms, setSymptoms] = useState<string[]>([]);
  const [submitted, setSubmitted] = useState(false);
  const [demoSubmitted, setDemoSubmitted] = useState(false);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const lang = context?.site.language === 'hi' ? translations.hi : translations.en;

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { setContext(demoRun ? await api.replayWorkerContext(demoRun) : await api.workerContext(siteCode)); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not load this break check.'); }
    finally { setLoading(false); }
  }, [siteCode, demoRun]);
  useEffect(() => { void load(); }, [load]);

  function toggleSymptom(value: string) {
    setSymptoms((current) => value === 'ok' ? (current.includes('ok') ? [] : ['ok']) : current.includes(value) ? current.filter((item) => item !== value && item !== 'ok') : [...current.filter((item) => item !== 'ok'), value]);
  }

  async function submit() {
    if (answer === null) return;
    if (demoRun) {
      if (!context?.eligible || !context.active_window?.rest_window_id) { setError('Start the replay and reach its 11:30 rest step first.'); return; }
      setSending(true); setError('');
      try {
        await api.replayWorkerSubmit(demoRun, { window_id: context.active_window.rest_window_id, break_received: answer, water_available: water, shade_available: shade, symptoms });
        setDemoSubmitted(true);
        await load();
      }
      catch (err) { setError(err instanceof Error ? err.message : 'Could not record the synthetic demo response.'); }
      finally { setSending(false); }
      return;
    }
    if (!context?.active_window?.rest_window_id) return;
    setSending(true); setError('');
    try {
      await api.workerSubmit(siteCode, { window_id: context.active_window.rest_window_id, break_received: answer, water_available: water, shade_available: shade, symptoms });
      setSubmitted(true); await load();
    } catch (err) { setError(err instanceof Error ? err.message : 'The response was not accepted.'); }
    finally { setSending(false); }
  }

  if (loading) return <main className="worker-shell"><Loading label="Opening break check…" /></main>;
  if (error && !context && !demoRun) return <main className="worker-shell"><div className="worker-brand"><span className="worker-brand__icon"><Shield size={22} /></span><strong>SHIFT SHIELD</strong></div><ErrorNotice message={error} onRetry={() => void load()} /><Link className="worker-back" to="/">{lang.back}</Link></main>;
  const window = context?.active_window;
  const demo = !!demoRun;
  return <main className={`worker-shell${demo ? ' worker-shell--demo' : ''}`}>
    <div className="worker-brand"><span className="worker-brand__icon"><Shield size={22} /></span><strong>{lang.brand}</strong><span className="worker-brand__tag">HEAT SAFETY</span></div>
    {demo ? <div className="worker-demo-banner"><Activity size={15} />{lang.demo}</div> : <div className="worker-site-line"><span className="online-dot" />{context?.site.name ?? 'Worksite'} <span><BandPill band={window?.band ?? 'unknown'} /></span></div>}
    <section className="worker-card">
      <div className="worker-card__eyebrow"><span>{lang.label}</span><span>{siteTime(window?.rest_window_start, context?.site.timezone)}</span></div>
      <div className="worker-card__graphic"><div className="rest-ring"><div className="rest-ring__center"><span><Sun size={17} /></span><strong>{window?.rest_minutes_per_hour ?? 30}<small>MIN</small></strong><i>REST</i></div><div className="rest-ring__label">YOUR TIME<br />MATTERS</div></div></div>
      <h1>{lang.question}</h1>
      {!demo && <p className="worker-window-copy">{context?.eligible ? `${lang.rest} · ${window?.rest_minutes_per_hour ?? 0} MIN` : context?.message}</p>}
      {context && window && <div className="worker-plan-note"><span><strong>{window.work_minutes_per_hour}</strong> work</span><i>/</i><span><strong>{window.rest_minutes_per_hour}</strong> rest <small>min / hour</small></span><BandPill band={window.band ?? 'unknown'} /></div>}
      {!demo && context?.active_window === null && <div className="worker-closed"><Clock3 size={17} /><span>{lang.closed}</span></div>}
      {!demo && window && !context?.eligible && <div className="worker-next"><Clock3 size={16} /><span>{lang.waiting} <strong>{siteTime(window.rest_window_start, context?.site.timezone)}</strong></span></div>}
      <div className="worker-main-choices"><button type="button" disabled={!demo && (!context?.eligible || submitted)} className={`worker-answer worker-answer--yes${answer === true ? ' is-selected' : ''}`} onClick={() => setAnswer(true)}><span className="worker-answer__symbol"><Check size={24} /></span><strong>{lang.yes}</strong><small>YES</small></button><button type="button" disabled={!demo && (!context?.eligible || submitted)} className={`worker-answer worker-answer--no${answer === false ? ' is-selected' : ''}`} onClick={() => setAnswer(false)}><span className="worker-answer__symbol"><ChevronLeft size={24} /></span><strong>{lang.no}</strong><small>NO</small></button></div>
      <div className={`worker-optional${!context?.eligible && !demo ? ' is-muted' : ''}`}>
        <span className="eyebrow">OPTIONAL CHECK-IN</span>
        <BoolChoice label={lang.water} icon="water" value={water} onChange={setWater} />
        <BoolChoice label={lang.shade} icon="shade" value={shade} onChange={setShade} />
        <div className="rest-question rest-question--symptoms"><div className="rest-question__label"><TriangleAlert size={18} /><span>{lang.symptoms}</span></div><p>{lang.skip}</p><div className="symptom-row">{(['dizzy', 'headache', 'cramps', 'ok'] as const).map((key) => <button type="button" key={key} className={symptoms.includes(key) ? 'symptom-chip symptom-chip--selected' : 'symptom-chip'} onClick={() => toggleSymptom(key)}>{symptoms.includes(key) && <Check size={13} />}{lang[key]}</button>)}</div></div>
      </div>
      {error && <ErrorNotice message={error} />}
      {(submitted || demoSubmitted) ? <div className="worker-thanks" role="status"><Check size={19} /><div><strong>{demo ? 'Synthetic replay response recorded.' : lang.done}</strong><small>{demo ? 'This response changes only the synthetic replay.' : lang.private}</small></div></div> : <button className="worker-submit" disabled={answer === null || sending || (!demo && !context?.eligible)} onClick={() => void submit()}>{sending ? 'SENDING…' : lang.submit}<ArrowRightIcon /></button>}
      {context?.combined_status && <div className="worker-combined"><RestPill status={context.combined_status} /><span>{context.aggregate?.total_responses ?? 0} {demo ? 'synthetic replay' : 'site'} responses · individual votes are never shown</span></div>}
      <p className="worker-privacy"><Shield size={14} />{demo ? 'Synthetic replay only. No response enters a live site ledger.' : lang.private}</p>
      <p className="worker-disclaimer">{context?.disclaimer ?? 'Decision support only — follow the site supervisor and official local safety guidance.'}</p>
    </section>
    <Link className="worker-back" to={demo ? `/replay?run=${encodeURIComponent(demoRun ?? '')}` : '/'}>{lang.back}</Link>
    <div className="worker-emergency">Shade, cool the person, water if conscious; call 112 for confusion, fainting or hot dry skin.</div>
  </main>;
}

function ArrowRightIcon() { return <span aria-hidden="true">→</span>; }
