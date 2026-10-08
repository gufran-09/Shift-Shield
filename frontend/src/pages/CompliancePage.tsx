import { ArrowRight, ClipboardCheck, FileText, ShieldAlert } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api';
import { ErrorNotice, Loading, PageHeading, SafetyNotice } from '../components/Primitives';
import type { ComplianceResponse } from '../types';

export function CompliancePage() {
  const { siteId = '' } = useParams();
  const [searchParams] = useSearchParams();
  const demoRun = searchParams.get('demoRun');
  const [data, setData] = useState<ComplianceResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let live = true;
    const request = demoRun ? api.replayCompliance(demoRun) : api.compliance(siteId);
    void request.then((value) => { if (live) setData(value); })
      .catch((err: unknown) => { if (live) setError(err instanceof Error ? err.message : 'Compliance view unavailable.'); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [siteId, demoRun]);

  if (loading) return <Loading label={demoRun ? 'Loading synthetic replay evidence…' : 'Loading approved policy and issued plan…'} />;
  const dashboardPath = demoRun ? `/dashboard/demo?demoRun=${encodeURIComponent(demoRun)}` : `/dashboard/${encodeURIComponent(siteId)}`;
  const ledgerPath = demoRun ? `/ledger/${encodeURIComponent(siteId)}?demoRun=${encodeURIComponent(demoRun)}` : `/ledger/${encodeURIComponent(siteId)}`;
  return <div className="page-stack">
    <PageHeading eyebrow={demoRun ? 'SYNTHETIC REPLAY · EVIDENCE VIEW' : 'SITE RULEBOOK · DAILY VIEW'} title="A rule is only live" note="after someone checks the source."
      actions={demoRun ? <Link className="button button--secondary" to={dashboardPath}>SUPERVISOR DASHBOARD <ArrowRight size={15} /></Link> : <Link className="button button--secondary" to="/rulebooks">OPEN RULEBOOK DESK <ArrowRight size={15} /></Link>} />
    {error && <ErrorNotice message={error} />}
    <SafetyNotice>{demoRun ? 'Replay mode — synthetic only. No real local action plan was uploaded or approved, so this page is not a legal compliance result.' : 'Reading and compliance aid only — not legal advice. No obligation is treated as approved until a human reviews its source quote and page.'}</SafetyNotice>
    <section className="compliance-hero">
      <div className="compliance-hero__mark"><ClipboardCheck size={23} /></div>
      <div><span className="eyebrow">{demoRun ? 'REPLAY DATE' : 'TODAY'} · {data?.date ?? new Date().toLocaleDateString()}</span>
        <h2>{data?.status === 'no_approved_plan' ? 'No approved action plan' : 'Daily heat obligations'}</h2>
        <p>{typeof data?.warning === 'string' ? data.warning : 'Physiology-based work/rest remains deterministic. Upload a local heat action plan to add human-verified obligations.'}</p>
        {demoRun && data?.rest_record_status && <p><strong>Replay rest-record status: {data.rest_record_status.label ?? data.rest_record_status.code.replaceAll('_', ' ')}.</strong> Counts are synthetic, not live-worker evidence.</p>}
      </div>
      <span className="compliance-status">{String(data?.status ?? 'UNCONFIRMED').replaceAll('_', ' ').toUpperCase()}</span>
    </section>
    {Array.isArray(data?.obligations) && data.obligations.length > 0 ? <div className="compliance-table-wrap"><table className="compliance-table"><thead><tr><th>Obligation / record</th><th>Plan says</th><th>Physiology says</th><th>Applied today</th><th>Status</th><th>Confirmed by</th></tr></thead><tbody>{data.obligations.map((item, index) => <tr key={String(item.obligation_id ?? index)}><td>{String(item.title ?? 'Obligation')}</td><td>{String(item.plan_requirement ?? 'Source text')}</td><td>{String(item.physiology_requirement ?? 'See deterministic plan')}</td><td>{String(item.applied_requirement ?? 'Unconfirmed')}</td><td><span className="compliance-chip">{String(item.status ?? 'unconfirmed').replaceAll('_', ' ')}</span></td><td>{String(item.confirmed_by ?? '—')}</td></tr>)}</tbody></table></div> : <section className="empty-policy"><div className="empty-policy__icon"><FileText size={22} /></div><span className="eyebrow">NO LEGAL OR CITY POLICY LOADED</span><h3>Nothing invented.<br /><em>Nothing silently approved.</em></h3><p>No real local heat action plan was provided with this prototype. Upload the official PDF, inspect each extracted quote and approve the obligations before they appear here.</p><Link className="button button--primary" to="/rulebooks">UPLOAD A PLAN <ArrowRight size={16} /></Link></section>}
    {demoRun && <div className="rest-record-foot"><Link to={ledgerPath}>OPEN THIS RUN’S LEDGER <ArrowRight size={14} /></Link><Link to={`/replay?run=${encodeURIComponent(demoRun)}`}>RETURN TO REPLAY <ArrowRight size={14} /></Link></div>}
    <div className="compliance-note"><ShieldAlert size={18} /><span><strong>Stricter rule wins.</strong> In a real field deployment, approved policy and physiology are combined using the stricter requirement. This replay has no approved local rule. AI cannot lower the work/rest limit or approve a rule.</span></div>
  </div>;
}
