export type HeatBand = 'normal' | 'caution' | 'high' | 'very_high' | 'unknown';
export type RestStatusCode = 'confirmed_by_both' | 'supervisor_only' | 'disputed' | 'no_record';

export interface SiteProfile {
  site_id: string;
  site_code: string;
  name: string;
  latitude: number;
  longitude: number;
  timezone: string;
  surface: string;
  shade: string;
  wind_exposure: string;
  land_use: string;
  enclosure: string;
  intensity: string;
  acclimatization: string;
  ppe: string;
  shift_start: string;
  shift_end: string;
  tasks: Array<{ name: string; intensity: string; duration_minutes: number }>;
  language: string;
  email_alert_opt_in?: boolean;
  email_subscription_status?: string;
  profile_version?: number;
  demo_fixture?: boolean;
}

export interface SchedulePoint {
  time: string;
  local_time?: string;
  wbgt_c: number;
  margin_c: number;
  conservative_wbgt_c: number;
  wbgt_for_thresholds_c: number;
  band: HeatBand;
  label?: string;
  work_minutes_per_hour: number;
  rest_minutes_per_hour: number;
  water_guidance?: string;
  guidance?: string;
  safe_schedule_supported?: boolean;
  exceeds_final_15_min_curve?: boolean;
  data_status?: string;
  source_resolution?: string;
  wind_speed_10m_m_s?: number;
  activity?: 'work' | 'rest';
  rest_window_id?: string;
  rest_window_start?: string;
  rest_window_end?: string;
  shade_guidance?: string;
}

export interface ForecastMetadata {
  source?: string;
  source_resolution?: string;
  fetched_at_utc?: string;
  forecast_age_minutes?: number;
  timezone?: string;
  data_status?: string;
  warning?: string;
}

export interface PlanResponse {
  site_id: string;
  created_at: string;
  forecast: ForecastMetadata;
  points: SchedulePoint[];
  current: SchedulePoint | null;
  is_demo_only: boolean;
  source_versions?: Record<string, string | number>;
  safety_disclaimer?: string;
}

export interface PublicHeatCheckResponse {
  location: { latitude: number; longitude: number; timezone?: string };
  forecast: ForecastMetadata;
  current: SchedulePoint | null;
  timeline: SchedulePoint[];
  threshold_status: string;
  site_assumption_status: string;
  is_demo_only: boolean;
  disclaimer: string;
  fixed_emergency_footer: string;
}

export interface AggregateResponse {
  total_responses: number;
  split_visible: boolean;
  majority: 'yes' | 'no' | null;
  symptom_tightening: boolean;
  symptom_reports: number | null;
  symptom_threshold: number;
  break_yes_count?: number;
  break_no_count?: number;
  water_yes_count: number | null;
  water_no_count?: number | null;
  shade_yes_count: number | null;
  shade_no_count?: number | null;
}

export interface RestStatus {
  code: RestStatusCode;
  label: string;
  tone: 'good' | 'warning' | 'danger' | 'muted';
  detail: string;
}

export interface RestContext {
  site: Pick<SiteProfile, 'name' | 'site_code' | 'language' | 'timezone'>;
  active_window: SchedulePoint | null;
  eligible: boolean;
  message: string;
  aggregate?: AggregateResponse;
  combined_status?: RestStatus;
  disclaimer: string;
}

export interface RestWindowRecord {
  window: SchedulePoint;
  aggregate: AggregateResponse;
  supervisor_acknowledged: boolean;
  status: RestStatus;
}

export interface AlertEvent {
  event_type: string;
  alert_id?: string;
  alert_type?: string;
  from_band?: HeatBand;
  to_band?: HeatBand;
  window_start?: string;
  created_at?: string;
  delivery_status?: string;
  payload?: { reason?: string; lead_minutes?: number; work_minutes_per_hour?: number; rest_minutes_per_hour?: number };
}

export interface LedgerResponse {
  site_id: string;
  recorded_date: string;
  issued_plan_intervals: number;
  rest_windows_in_plan: number;
  heat_risk_hours: number;
  rest_minutes_prescribed: number;
  rest_minutes_confirmed_by_both: number;
  rest_minutes_supervisor_self_reported: number;
  rest_minutes_disputed: number;
  missed_danger_hours: number;
  needless_alarm_hours: number | null;
  alert_lead_times_minutes: number[];
  worker_majority_yes_rate: number | null;
  worker_response_count: number;
  water_available_yes_rate: number | null;
  shade_available_yes_rate: number | null;
  visible_response_windows: number;
  confirmation_rate_note: string;
  outside_window_danger_hours: number | null;
  outside_window_note: string;
  wage_savings: number | null;
  wage_savings_note: string;
  evidence_status: string;
  latest_backtest?: HistoricalBacktestResponse;
}

export interface HistoricalBacktestPoint {
  time: string;
  local_time: string;
  air_c: number;
  wbgt_c: number;
  conservative_wbgt_c: number;
  margin_c: number;
  band: HeatBand;
  baseline_alert: boolean;
  site_danger: boolean;
}

export interface HistoricalBacktestResponse {
  site_id: string;
  site_name: string;
  date_range: { start: string; end: string };
  archive_source: string;
  source_resolution: string;
  observed_on_site: false;
  baseline: { type: string; threshold_c: number; source: string; warning: string };
  definition: string;
  interval_count: number;
  city_baseline_alert_hours: number;
  site_high_very_high_hours: number;
  site_danger_hours: number;
  missed_danger_hours: number;
  needless_alarm_hours: number;
  lead_time_minutes: number[];
  danger_outside_13_16_hours: number | null;
  outside_window_note: string;
  worker_confirmation_rate: number | null;
  worker_confirmation_note: string;
  site_profile_version?: number;
  threshold_version?: string;
  wbgt_method?: string;
  default_uncertainty_margin_c?: number;
  sensitivity_analysis: Array<{ uncertainty_margin_c: number; high_or_very_high_hours: number }>;
  timeline: HistoricalBacktestPoint[];
  limitations: string[];
}

export interface ComplianceResponse {
  site_id?: string;
  date?: string;
  obligations?: Array<Record<string, unknown>>;
  status?: string;
  warning?: string;
  is_synthetic?: boolean;
  run_id?: string;
  rest_record_status?: RestStatus;
  [key: string]: unknown;
}

export interface RulebookRecord {
  plan_id: string;
  plan_version?: string;
  file_name?: string;
  page_count?: number;
  status?: string;
  candidate_count?: number;
  approved_obligation_count?: number;
  extraction_message?: string;
  rule_id?: string;
  title?: string;
  responsible_party?: string;
  requirement_text?: string;
  applies_when?: string;
  exact_quote?: string;
  pdf_page_number?: number;
  quote_verified?: boolean;
  human_approved?: boolean;
  created_at?: string;
}

export interface DemoStep {
  event_id: string;
  time_label: string;
  wbgt_c: number;
  site_b_wbgt_c: number;
  risk_label: HeatBand;
  work_minutes_per_hour: number;
  rest_minutes_per_hour: number;
  duration_hours: number;
  headline: string;
  detail: string;
  alert: string | null;
}

export interface DemoManifest {
  fixture_version: string;
  sites: SiteProfile[];
  steps: DemoStep[];
  disclaimer: string;
  bedrock_configured: boolean;
}

export interface DemoRunState {
  run_id: string;
  events: Array<Record<string, unknown>>;
  current: Record<string, unknown>;
  current_step: number;
  worker_window_id: string;
  fixture_version: string;
  is_synthetic: true;
  site_a: SiteProfile;
  site_b: SiteProfile;
  worker_aggregate: AggregateResponse;
  supervisor_break_started: boolean;
  rest_status: RestStatus;
  alert_acknowledged: boolean;
  alert_ack_path: string | null;
  alert_event: AlertEvent | null;
  rest_window: { rest_window_id: string; rest_window_start: string; rest_window_end: string };
}

export interface ReplayDashboardResponse {
  run_id: string;
  is_synthetic: true;
  site: SiteProfile;
  plan: PlanResponse;
  windows: RestWindowRecord[];
  events: AlertEvent[];
  ledger: LedgerResponse;
  supervisor_break_started: boolean;
  alert_acknowledged: boolean;
  alert_ack_path: string | null;
  worker_aggregate: AggregateResponse;
  rest_status: RestStatus;
  worker_window_id: string;
  current_step: number;
}
