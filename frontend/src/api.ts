import type {
  AlertEvent,
  ComplianceResponse,
  DemoManifest,
  DemoRunState,
  LedgerResponse,
  HistoricalBacktestResponse,
  PlanResponse,
  PublicHeatCheckResponse,
  ReplayDashboardResponse,
  RestContext,
  RestWindowRecord,
  RulebookRecord,
  SiteProfile,
} from './types';

const jsonHeaders = { Accept: 'application/json', 'Content-Type': 'application/json' };
const enc = (value: string) => encodeURIComponent(value);

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/+$/, '');

export function saveSupervisorSession(site: SiteProfile, token: string): void {
  sessionStorage.setItem('shiftshield.activeSiteId', site.site_id);
  sessionStorage.setItem('shiftshield.activeSite', JSON.stringify({ site_id: site.site_id, site_code: site.site_code, name: site.name }));
  sessionStorage.setItem(`shiftshield.siteToken.${site.site_id}`, token);
}

export function activeSiteId(): string | null {
  return sessionStorage.getItem('shiftshield.activeSiteId');
}

export function activeSiteName(): string | null {
  try {
    const value = sessionStorage.getItem('shiftshield.activeSite');
    return value ? (JSON.parse(value) as { name?: string }).name ?? null : null;
  } catch {
    return null;
  }
}

function auth(siteId: string): Record<string, string> {
  const token = sessionStorage.getItem(`shiftshield.siteToken.${siteId}`);
  if (!token) throw new Error('Supervisor token is missing from this browser session. Reopen setup and keep the one-time token safe.');
  return { Authorization: `Bearer ${token}` };
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Accept', 'application/json');
  const url = path.startsWith('http://') || path.startsWith('https://') ? path : `${API_BASE}${path}`;
  const response = await fetch(url, { ...init, headers, credentials: 'omit' });
  const body = (await response.json().catch(() => ({}))) as { detail?: { message?: string; error?: string } | string } & Record<string, unknown>;
  if (!response.ok) {
    const detail = body.detail;
    const message = typeof detail === 'object' && detail !== null
      ? detail.message ?? detail.error
      : typeof detail === 'string' ? detail : undefined;
    throw new Error(message ?? `Request failed (${response.status})`);
  }
  return body as T;
}

function json(method: string, value: unknown): RequestInit {
  return { method, headers: jsonHeaders, body: JSON.stringify(value) };
}

export const api = {
  health: () => request<{ status: string; mode: string; threshold_review: string }>('/api/health'),
  heatCheck: (payload: Record<string, unknown>) => request<PublicHeatCheckResponse>('/api/public/heat-check', json('POST', payload)),
  createSite: async (payload: Record<string, unknown>) => {
    const result = await request<{ site: SiteProfile; supervisor_token: string; supervisor_token_notice: string; email_status: string }>('/api/sites', json('POST', payload));
    saveSupervisorSession(result.site, result.supervisor_token);
    return result;
  },
  getSite: (siteId: string) => request<{ site: SiteProfile }>(`/api/sites/${enc(siteId)}`, { headers: auth(siteId) }),
  refreshPlan: (siteId: string) => request<PlanResponse>(`/api/sites/${enc(siteId)}/plan`, { ...json('POST', {}), headers: { ...jsonHeaders, ...auth(siteId) } }),
  getPlan: (siteId: string) => request<PlanResponse>(`/api/sites/${enc(siteId)}/plan`, { headers: auth(siteId) }),
  logs: (siteId: string) => request<{ events: AlertEvent[] }>(`/api/sites/${enc(siteId)}/logs?limit=60`, { headers: auth(siteId) }),
  restWindows: (siteId: string) => request<{ windows: RestWindowRecord[]; disclaimer: string }>(`/api/sites/${enc(siteId)}/rest-windows?limit=24`, { headers: auth(siteId) }),
  acknowledgeRest: (siteId: string, windowId: string) => request<{ acknowledged: boolean; already_acknowledged: boolean; status: RestWindowRecord['status'] }>(`/api/sites/${enc(siteId)}/rest-windows/${enc(windowId)}/ack`, { ...json('POST', {}), headers: { ...jsonHeaders, ...auth(siteId) } }),
  ledger: (siteId: string) => request<LedgerResponse>(`/api/sites/${enc(siteId)}/ledger`, { headers: auth(siteId) }),
  getCertificate: (siteId: string) => request<{ certificate_id: string; site_name: string; date: string; heat_risk_hours: number; rest_minutes_prescribed: number; rest_minutes_confirmed: number; signature: string; verification_url: string; issuer: string; issued_at: string }>(`/api/sites/${enc(siteId)}/certificate`, { headers: auth(siteId) }),
  verifyCertificate: (certId: string) => request<{ valid: boolean; status: string; certificate: Record<string, unknown> }>(`/api/certificates/${enc(certId)}`),
  backtest: (siteId: string, payload: { start_date: string; end_date: string; baseline_threshold_c: number; baseline_source: string }) => request<HistoricalBacktestResponse>(`/api/sites/${enc(siteId)}/backtest`, { ...json('POST', payload), headers: { ...jsonHeaders, ...auth(siteId) } }),
  compliance: (siteId: string) => request<ComplianceResponse>(`/api/sites/${enc(siteId)}/compliance`, { headers: auth(siteId) }),
  compare: (siteA: string, siteB: string) => {
    const params = new URLSearchParams({ site_a: siteA, site_b: siteB });
    const headers = { 'X-Site-A-Authorization': auth(siteA).Authorization, 'X-Site-B-Authorization': auth(siteB).Authorization };
    return request<{ rows: Array<{ time: string; site_a_wbgt_c: number; site_a_band: string; site_b_wbgt_c: number; site_b_band: string }>; warning: string }>(`/api/compare?${params}`, { headers });
  },
  workerContext: (siteCode: string) => request<RestContext>(`/api/rest/${enc(siteCode)}`),
  workerSubmit: (siteCode: string, payload: { window_id: string; break_received: boolean; water_available: boolean | null; shade_available: boolean | null; symptoms: string[] }) => request<{ accepted: boolean; aggregate: RestContext['aggregate']; combined_status: RestContext['combined_status']; message: string; disclaimer: string }>(`/api/rest/${enc(siteCode)}`, json('POST', payload)),
  getDemo: () => request<DemoManifest>('/api/demo'),
  startReplay: () => request<{ run_id: string; fixture_version: string; is_synthetic: boolean; steps: DemoManifest['steps']; site_a: SiteProfile; site_b: SiteProfile; disclaimer: string }>('/api/demo/start', json('POST', {})),
  replayState: (runId: string) => request<DemoRunState>(`/api/demo/${enc(runId)}`),
  replayDashboard: (runId: string) => request<ReplayDashboardResponse>(`/api/demo/${enc(runId)}/dashboard`),
  replayCompliance: (runId: string) => request<ComplianceResponse>(`/api/demo/${enc(runId)}/compliance`),
  replayStep: (runId: string, eventId: string) => request<Record<string, unknown>>(`/api/demo/${enc(runId)}/step`, json('POST', { event_id: eventId })),
  replayBreakStarted: (runId: string) => request<DemoRunState>(`/api/demo/${enc(runId)}/break-started`, json('POST', {})),
  replayWorkerContext: (runId: string) => request<RestContext>(`/api/demo/${enc(runId)}/worker`),
  replayWorkerSubmit: (runId: string, payload: { window_id: string; break_received: boolean; water_available: boolean | null; shade_available: boolean | null; symptoms: string[] }) => request<{ accepted: boolean; aggregate: RestContext['aggregate']; combined_status: RestContext['combined_status']; message: string; disclaimer: string }>(`/api/demo/${enc(runId)}/worker`, json('POST', payload)),
  acknowledgeAlertInfo: (token: string) => request<{ valid: boolean; already_acknowledged: boolean; alert: AlertEvent }>(`/api/ack/${enc(token)}`),
  acknowledgeAlert: (token: string) => request<{ acknowledged: boolean; already_acknowledged: boolean; site_id: string; alert_id: string }>('/api/ack', json('POST', { token })),
  rulebooks: (siteId: string) => request<{ plans: RulebookRecord[]; candidates: RulebookRecord[] }>(`/api/rulebooks/${enc(siteId)}`, { headers: auth(siteId) }),
  uploadRulebook: (siteId: string, file: File, planVersion: string) => {
    const form = new FormData();
    form.append('file', file);
    form.append('plan_version', planVersion);
    return request<{ plan: RulebookRecord; candidates: RulebookRecord[]; warning?: string }>(`/api/rulebooks/${enc(siteId)}`, { method: 'POST', headers: auth(siteId), body: form });
  },
  decideRule: (siteId: string, planId: string, ruleId: string, action: 'approve' | 'reject' | 'edit', requirementText?: string, appliesWhen?: string) => request<{ candidate: RulebookRecord; human_gate: string }>(`/api/rulebooks/${enc(siteId)}/${enc(planId)}/${enc(ruleId)}/decision`, { ...json('POST', { action, requirement_text: requirementText, applies_when: appliesWhen, reviewer_role: 'site_supervisor' }), headers: { ...jsonHeaders, ...auth(siteId) } }),
  getVoiceAlertUrl: (siteId: string, lang: 'hi' | 'en' = 'hi') => `${API_BASE}/api/sites/${enc(siteId)}/voice-alert?lang=${lang}&format=audio`,
  escalateAlert: (siteId: string) => request<{ escalated: boolean; message?: string; event?: Record<string, unknown> }>(`/api/sites/${enc(siteId)}/escalate`, { ...json('POST', {}), headers: { ...jsonHeaders, ...auth(siteId) } }),
};
