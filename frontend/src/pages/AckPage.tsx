import { ArrowLeft, Check, ShieldAlert } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { BandPill, ErrorNotice, Loading } from '../components/Primitives';
import type { AlertEvent } from '../types';

export function AckPage() {
  const { token = '' } = useParams();
  const [searchParams] = useSearchParams();
  const requestedReturn = searchParams.get('return') ?? '/';
  const returnTo = requestedReturn.startsWith('/') && !requestedReturn.startsWith('//') ? requestedReturn : '/';
  const [alert, setAlert] = useState<AlertEvent | null>(null);
  const [already, setAlready] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => { let live = true; void api.acknowledgeAlertInfo(token).then((data) => { if (live) { setAlert(data.alert); setAlready(data.already_acknowledged); } }).catch((err: unknown) => { if (live) setError(err instanceof Error ? err.message : 'This acknowledgement link is invalid or expired.'); }).finally(() => { if (live) setLoading(false); }); return () => { live = false; }; }, [token]);
  async function confirm() {
    setError(''); setLoading(true);
    try { const data = await api.acknowledgeAlert(token); setAlready(data.already_acknowledged); setConfirmed(data.acknowledged || data.already_acknowledged); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not record acknowledgement.'); }
    finally { setLoading(false); }
  }
  return <main className="ack-shell"><Link className="ack-brand" to="/"><span className="worker-brand__icon"><ShieldAlert size={20} /></span><strong>SHIFT SHIELD</strong></Link><section className="ack-card">
    {loading && <Loading label="Checking signed alert link…" />}{error && <ErrorNotice message={error} />}
    {!loading && alert && <><span className="eyebrow">SUPERVISOR ACKNOWLEDGEMENT · ACK ONLY</span><h1>Confirm you’ve<br /><em>seen the plan.</em></h1><div className="ack-transition"><div><span className="eyebrow">SCHEDULE CHANGE</span><p>{alert.window_start ? (Number.isNaN(new Date(alert.window_start).getTime()) ? alert.window_start : new Date(alert.window_start).toLocaleString()) : 'See site dashboard'}</p></div><div className="ack-transition__bands"><BandPill band={alert.from_band ?? 'unknown'} /><span>→</span><BandPill band={alert.to_band ?? 'unknown'} /></div></div><p className="ack-reason">{alert.payload?.reason ?? 'A stricter work/rest plan has been issued.'}</p><div className="ack-warning"><ShieldAlert size={17} /><span>This link records that the supervisor saw the alert. It does not change site settings or verify that a break happened.</span></div>{already || confirmed ? <><div className="worker-thanks"><Check size={19} /><div><strong>Alert acknowledged.</strong><small>No worksite configuration was changed.</small></div></div><Link className="inline-link" to={returnTo}>RETURN TO DEMO <ArrowLeft size={14} /></Link></> : <button className="button button--primary button--wide" onClick={() => void confirm()} disabled={loading}>ACKNOWLEDGE ALERT <Check size={17} /></button>}</>}
  </section><Link to="/" className="worker-back"><ArrowLeft size={14} /> Open ShiftShield</Link></main>;
}
