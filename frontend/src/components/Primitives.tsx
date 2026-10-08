import { AlertTriangle, ArrowUpRight, Check, LoaderCircle } from 'lucide-react';
import type { ReactNode } from 'react';
import type { HeatBand, RestStatus } from '../types';

export function PageHeading({ eyebrow, title, note, actions }: { eyebrow: string; title: string; note?: string; actions?: ReactNode }) {
  return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1>{note && <p className="page-heading__note">{note}</p>}</div>{actions && <div className="page-heading__actions">{actions}</div>}</div>;
}

export function SafetyNotice({ children }: { children?: ReactNode }) {
  return <div className="safety-banner"><AlertTriangle size={17} /><span>{children ?? 'Decision support only — not medical advice. Demo threshold transcription and site adjustments are not field-ready; follow official local guidance.'}</span></div>;
}

export function BandPill({ band, text }: { band: HeatBand; text?: string }) {
  const label = text ?? ({ normal: 'NORMAL', caution: 'CAUTION', high: 'HIGH', very_high: 'VERY HIGH', unknown: 'UNAVAILABLE' } as Record<HeatBand, string>)[band];
  return <span className={`band-pill band-pill--${band}`}><span className="band-pill__dot" />{label}</span>;
}

export function RestPill({ status }: { status: RestStatus }) {
  const Icon = status.code === 'confirmed_by_both' ? Check : status.code === 'disputed' ? AlertTriangle : ArrowUpRight;
  return <span className={`rest-pill rest-pill--${status.tone}`}><Icon size={14} />{status.label}</span>;
}

export function Loading({ label = 'Loading shift data…' }: { label?: string }) {
  return <div className="loading-state"><LoaderCircle className="spin" size={20} /><span>{label}</span></div>;
}

export function ErrorNotice({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="error-notice" role="alert"><AlertTriangle size={18} /><span>{message}</span>{onRetry && <button className="text-button" onClick={onRetry}>Try again</button>}</div>;
}

export function Metric({ label, value, unit, foot, accent = false }: { label: string; value: ReactNode; unit?: string; foot?: string; accent?: boolean }) {
  return <div className={`metric${accent ? ' metric--accent' : ''}`}><span className="metric__label">{label}</span><strong className="metric__value">{value}{unit && <small>{unit}</small>}</strong>{foot && <span className="metric__foot">{foot}</span>}</div>;
}
