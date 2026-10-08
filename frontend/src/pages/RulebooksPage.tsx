import { ArrowRight, Check, FileUp, FileWarning, RefreshCw, ShieldCheck, X } from 'lucide-react';
import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { activeSiteId, api } from '../api';
import { ErrorNotice, Loading, PageHeading, SafetyNotice } from '../components/Primitives';
import type { RulebookRecord } from '../types';

export function RulebooksPage() {
  const siteId = activeSiteId();
  const [version, setVersion] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [plans, setPlans] = useState<RulebookRecord[]>([]);
  const [candidates, setCandidates] = useState<RulebookRecord[]>([]);
  const [warning, setWarning] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deciding, setDeciding] = useState('');
  const [edits, setEdits] = useState<Record<string, string>>({});

  async function refresh() {
    if (!siteId) { setLoading(false); return; }
    setError('');
    try { const result = await api.rulebooks(siteId); setPlans(result.plans); setCandidates(result.candidates); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not load the rulebook desk.'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, [siteId]);
  const extractionPending = plans.some((plan) => plan.status === 'queued' || plan.status === 'processing');
  useEffect(() => {
    if (!siteId || !extractionPending) return;
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => window.clearInterval(timer);
  }, [siteId, extractionPending]);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!siteId || !file || !version.trim()) return;
    setUploading(true); setError(''); setWarning('');
    try { const result = await api.uploadRulebook(siteId, file, version.trim()); setWarning(result.warning ?? 'Candidate extraction completed.'); setFile(null); await refresh(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not process this PDF.'); }
    finally { setUploading(false); }
  }

  async function decide(candidate: RulebookRecord, action: 'approve' | 'reject' | 'edit', requirementText?: string) {
    if (!siteId || !candidate.plan_id || !candidate.rule_id) return;
    setDeciding(candidate.rule_id); setError('');
    try { await api.decideRule(siteId, candidate.plan_id, candidate.rule_id, action, requirementText); await refresh(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Could not save the decision.'); }
    finally { setDeciding(''); }
  }

  if (loading) return <Loading label="Loading private plan records…" />;
  if (!siteId) return <div className="page-stack"><PageHeading eyebrow="RULEBOOK DESK" title="Connect a site first." note="Plan reviews are stored against a specific worksite." /><Link className="button button--primary" to="/setup">CREATE SITE <ArrowRight size={16} /></Link></div>;
  return <div className="page-stack"><PageHeading eyebrow="POLICY READING AID · HUMAN GATE" title="Quotes before conclusions." note="AI may suggest obligations from the PDF. Code checks the exact source quote; a human must approve each one." actions={<button className="button button--secondary" onClick={() => { setLoading(true); void refresh(); }}><RefreshCw size={15} /> REFRESH</button>} />{error && <ErrorNotice message={error} onRetry={() => void refresh()} />}
    <SafetyNotice>Not legal advice. Do not use a candidate as an approved rule until the original source page is reviewed. No real Delhi or other-city action-plan PDF was supplied with this prototype.</SafetyNotice>
    <section className="rulebook-upload"><div className="rulebook-upload__symbol"><FileUp size={22} /></div><div className="rulebook-upload__copy"><span className="eyebrow">UPLOAD AN OFFICIAL HEAT ACTION PLAN</span><h2>Start with the source file.</h2><p>Searchable PDF · max 10 MiB · 250 pages. Scanned PDFs need Textract in AWS. Uploaded files are private and never public.</p></div><form className="rulebook-upload__form" onSubmit={upload}><label>Plan version<input required maxLength={160} value={version} onChange={(event) => setVersion(event.target.value)} placeholder="City / agency · year" /></label><label className="file-drop"><FileUp size={17} /><span>{file ? file.name : 'Choose PDF'}</span><input type="file" accept="application/pdf,.pdf" onChange={(event) => setFile(event.target.files?.[0] ?? null)} required /></label><button className="button button--primary" type="submit" disabled={uploading || !file}>{uploading ? 'READING…' : 'UPLOAD & EXTRACT'}<ArrowRight size={16} /></button></form></section>
    {warning && <div className="upload-warning"><FileWarning size={17} />{warning}</div>}
    <div className="rulebook-grid"><section className="panel-card"><div className="card-heading card-heading--small"><div><span className="eyebrow">DOCUMENT REGISTER</span><h2>Uploaded plans</h2></div><span className="metric-stamp">{plans.length} FILE{plans.length === 1 ? '' : 'S'}</span></div>{plans.length ? <div className="rulebook-plan-list">{plans.map((plan) => <div className="rulebook-plan" key={plan.plan_id}><div className="rulebook-plan__icon"><FileWarning size={17} /></div><div><strong>{plan.file_name ?? plan.plan_version ?? 'Action plan'}</strong><span>{plan.plan_version} · {plan.page_count ?? '—'} pages · {String(plan.status ?? 'uploaded').replaceAll('_', ' ')}</span><small>{plan.approved_obligation_count ?? 0} approved obligations</small></div></div>)}</div> : <div className="empty-inline">No plan file has been uploaded for this site.</div>}</section>
      <section className="panel-card rulebook-principles"><span className="eyebrow">NON-NEGOTIABLE GATES</span><h2>Four checks. <em>Always.</em></h2><div><span>01</span><p>Each candidate quote must match the cited PDF page.</p><Check size={16} /></div><div><span>02</span><p>Unverified quotes are rejected before review.</p><Check size={16} /></div><div><span>03</span><p>A named policy role must approve or reject; no auto-approval.</p><Check size={16} /></div><div><span>04</span><p>Approved policy and physiology combine using the stricter rule.</p><Check size={16} /></div></section></div>
    <section className="candidate-section"><div className="card-heading"><div><span className="eyebrow">SOURCE-PAGE REVIEW</span><h2>Obligation candidates</h2></div><span className="candidate-count">{candidates.length} CANDIDATE{candidates.length === 1 ? '' : 'S'}</span></div>{candidates.length ? candidates.map((candidate) => {
      const draft = edits[candidate.rule_id ?? ''] ?? candidate.requirement_text ?? '';
      return <article className="candidate-card" key={`${candidate.plan_id}-${candidate.rule_id}`}><div className="candidate-card__top"><span className={candidate.quote_verified ? 'quote-tag quote-tag--verified' : 'quote-tag quote-tag--rejected'}>{candidate.quote_verified ? 'QUOTE MATCHED' : 'UNVERIFIABLE — REJECTED'}</span><span className="candidate-page">PDF PAGE {candidate.pdf_page_number ?? '—'} · {candidate.plan_version}</span></div><h3>{candidate.title ?? 'Candidate obligation'}</h3><p className="candidate-req">{candidate.requirement_text ?? 'No proposed requirement text.'}</p><blockquote className="candidate-quote">“{candidate.exact_quote ?? 'No source quote returned.'}”</blockquote><div className="candidate-byline"><span>Responsible party: <strong>{candidate.responsible_party ?? 'Not specified'}</strong></span><span>When: <strong>{candidate.applies_when ?? 'Not specified'}</strong></span></div>{!candidate.human_approved && candidate.quote_verified && <label className="candidate-edit">Human-edited wording (save edit, then approve separately)<textarea rows={3} value={draft} onChange={(event) => setEdits((current) => ({ ...current, [candidate.rule_id ?? '']: event.target.value }))} /></label>}<div className="candidate-review"><span>{candidate.human_approved ? 'APPROVED BY HUMAN REVIEW' : String(candidate.status ?? 'awaiting_review').replaceAll('_', ' ').toUpperCase()}</span>{!candidate.human_approved && candidate.quote_verified && <div><button className="candidate-edit-button" disabled={!!deciding || !draft.trim()} onClick={() => void decide(candidate, 'edit', draft)}><FileWarning size={14} />EDIT TEXT</button><button className="candidate-approve" disabled={!!deciding} onClick={() => void decide(candidate, 'approve')}><Check size={14} />{deciding === candidate.rule_id ? 'SAVING…' : 'APPROVE'}</button><button className="candidate-reject" disabled={!!deciding} onClick={() => void decide(candidate, 'reject')}><X size={14} />REJECT</button></div>}</div></article>;
    }) : <div className="empty-policy empty-policy--small"><div className="empty-policy__icon"><FileWarning size={20} /></div><span className="eyebrow">{extractionPending ? 'EXTRACTION IN PROGRESS' : 'NO EXTRACTED CANDIDATES'}</span><h3>{extractionPending ? <>Source review<br /><em>is being prepared.</em></> : <>Nothing is approved<br /><em>by default.</em></>}</h3><p>{extractionPending ? 'This private PDF is queued for candidate-only analysis. This page refreshes automatically; no schedule changes until a human reviews a verified source quote.' : 'In the local demo, Bedrock is not configured. The core heat and work/rest path remains usable. After deploying with a supported Bedrock model, candidates will appear here for source-page review.'}</p><Link className="inline-link" to={`/compliance/${siteId}`}>VIEW COMPLIANCE STATUS <ArrowRight size={14} /></Link></div>}</section>
    <div className="compliance-note"><ShieldCheck size={18} /><span>AI is a document-reading aid only. It cannot alter deterministic WBGT calculations, select a less restrictive schedule or approve obligations.</span></div>
  </div>;
}
