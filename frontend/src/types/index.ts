// frontend/src/types/index.ts

export type Role = 'admin' | 'analyst' | 'viewer';

export interface User {
  id: string;
  username: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface Host {
  id: string;
  hostname: string;
  os_version: string;
  agent_platform: string;
  ip_address?: string;
  status: 'online' | 'offline';
  last_seen?: string;
  is_active: boolean;
  created_at: string;
}

export interface Metric {
  id: string;
  host_id: string;
  ts: string;
  cpu: number;
  mem: number;
  disk: number;
  net_in: number;
  net_out: number;
  load: number;
  proc_count: number;
  conn_count: number;
  extra?: {
    top_cpu_processes?: Array<{ name: string; pid: number; cpu_percent: number }>;
    top_memory_processes?: Array<{ name: string; pid: number; memory_percent: number }>;
    listening_ports?: Array<{ port: number; proto: string }>;
    services?: Record<string, string>;
  };
}

export interface SecurityEvent {
  id: string;
  host_id: string;
  ts: string;
  source: 'wazuh' | 'agent' | 'winevent';
  rule_id?: string;
  level: number;
  category?: string;
  src_ip?: string;
  user?: string;
  event_id?: number;
  raw?: Record<string, any>;
}

export interface Detection {
  id: string;
  host_id: string;
  ts: string;
  anomaly_score: number;
  is_attack: boolean;
  model_id?: string;
  status: string;
  details?: Record<string, any>;
}

export interface Classification {
  id: string;
  host_id: string;
  ts: string;
  label: 'benign' | 'brute_force' | 'ddos' | 'port_scan' | 'unauthorized_access' | 'suspicious_process';
  confidence: number;
  probs?: Record<string, number>;
  model_id?: string;
}

export interface Incident {
  id: string;
  title: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'investigating' | 'mitigated' | 'resolved' | 'closed';
  description?: string;
  summary?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface SourceIpInfo {
  ip: string;
  count: number;
  first_seen?: string;
  last_seen?: string;
  country?: string;
  city?: string;
}

export interface TimelineEvent {
  ts: string;
  type: string;
  description: string;
  source: string;
  details?: Record<string, any>;
}

export interface RCAReport {
  id: string;
  incident_id: string;
  probable_cause: string;
  confidence: number;
  source_ips: SourceIpInfo[];
  affected_hosts: string[];
  evidence: Record<string, any>;
  timeline: TimelineEvent[];
  recommended_actions: string[];
  plain_english_summary: string;
  created_at: string;
  updated_at: string;
}

export interface Prediction {
  id: string;
  host_id: string;
  ts: string;
  kind: 'threat' | 'cpu' | 'memory' | 'disk' | 'service';
  horizon_min: number;
  value: number;
  probability: number;
  model_id?: string;
  outcome_observed?: number | null;
  created_at: string;
}

export interface MaintenanceForecast {
  id: string;
  host_id: string;
  component: 'disk' | 'memory' | 'cpu' | 'services';
  metric_name: string;
  days_remaining: number;
  confidence: number;
  details: Record<string, any>;
  created_at: string;
}

export interface HostMaintenanceDetail {
  host_id: string;
  hostname: string;
  forecasts: MaintenanceForecast[];
  disk_fill_eta_days?: number | null;
  service_risks: Array<{ service: string; status: string; risk: string }>;
  component_status: Record<string, string>;
}

export interface ResponseAction {
  id: string;
  host_id?: string;
  incident_id?: string;
  action: 'block_ip' | 'restrict' | 'restart_service' | 'kill_process';
  status: 'pending' | 'executed' | 'failed' | 'verified' | 'rolled_back';
  target: string;
  initiated_by: string;
  result?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface BlocklistEntry {
  id: string;
  ip: string;
  reason?: string;
  expires_at?: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PolicyRule {
  label: string;
  min_confidence: number;
  severity: string;
  action: string;
  requires_approval: boolean;
  ttl_minutes: number;
}

export interface PolicyConfig {
  dry_run: boolean;
  max_actions_per_minute: int;
  never_block_ips: string[];
  policies: PolicyRule[];
}

export interface MLModel {
  id: string;
  name: string;
  task: string;
  version: string;
  status: 'candidate' | 'active' | 'retired' | 'rejected';
  metrics: {
    macro_f1?: number;
    precision?: number;
    recall?: number;
    accuracy?: number;
    per_class_recall?: Record<string, number>;
    inference_latency_ms?: number;
  };
  artifact_path: string;
  created_at: string;
  updated_at: string;
}

export interface DriftEvent {
  id: string;
  model_id?: string;
  feature_name: string;
  drift_score: number;
  p_value?: number;
  is_drift: boolean;
  details: Record<string, any>;
  created_at: string;
}

export interface RetrainingJob {
  id: string;
  model_id?: string;
  status: 'pending' | 'running' | 'candidate_ready' | 'promoted' | 'rejected' | 'failed';
  dataset_size: number;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  metrics_summary?: Record<string, any>;
  created_at: string;
}

export interface FeedbackLabel {
  id: string;
  detection_id?: string;
  analyst_id?: string;
  true_label: string;
  comments?: string;
  created_at: string;
}

export interface AuditLog {
  id: string;
  user_id?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
  created_at: string;
}

export interface TopRiskItem {
  category: string;
  title: string;
  host_id?: string;
  hostname?: string;
  probability: number;
  eta_minutes?: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export interface DashboardSummary {
  host_health_score: number;
  total_hosts: number;
  online_hosts: number;
  active_incidents: number;
  attack_counts_24h: Record<string, number>;
  top_risks: TopRiskItem[];
}

export interface ReportSummary {
  generated_at: string;
  reporting_period_days: number;
  total_hosts: number;
  online_hosts: number;
  total_detections: number;
  total_incidents: number;
  attacks_blocked: number;
  uptime_percentage: number;
  attack_breakdown: Record<string, number>;
  top_threat_vectors: Array<{ vector: string; count: number; risk: string }>;
}

export interface LiveStreamEnvelope<T = any> {
  type: string;
  channel: string;
  ts: string;
  data: T;
}
