// frontend/src/types/index.ts
// Shared TypeScript types — keep in sync with docs/DATA_SCHEMA.md

export type AttackLabel =
  | 'benign'
  | 'brute_force'
  | 'ddos'
  | 'port_scan'
  | 'unauthorized_access'
  | 'suspicious_process'

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical'
export type UserRole = 'admin' | 'analyst' | 'viewer'
export type AgentStatus = 'online' | 'offline'

// ── API Auth ─────────────────────────────────────────────────────────────────
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
}

// ── Agent ────────────────────────────────────────────────────────────────────
export interface Agent {
  id: string
  hostname: string
  os_version: string
  ip_address: string | null
  status: AgentStatus
  last_seen: string | null
  created_at: string
  revoked: boolean
}

// ── Metric ───────────────────────────────────────────────────────────────────
export interface ProcessInfo {
  pid: number
  name: string
  cpu_percent: number
  memory_mb: number
}

export interface MetricRecord {
  id: string
  agent_id: string
  collected_at: string
  ingested_at: string
  cpu_percent: number
  memory_percent: number
  memory_used_mb: number
  disk_read_bytes_sec: number
  disk_write_bytes_sec: number
  net_bytes_sent_sec: number
  net_bytes_recv_sec: number
  active_connections: number
  process_count: number
  top_processes: ProcessInfo[]
  event_log_errors_1m: number
  event_log_warnings_1m: number
}

// ── Prediction ───────────────────────────────────────────────────────────────
export interface PredictionRecord {
  id: string
  agent_id: string
  metric_id: string
  predicted_at: string
  label: AttackLabel
  confidence: number
  model_version: string
  features_used: string[]
}

// ── Alert ────────────────────────────────────────────────────────────────────
export interface AlertRecord {
  id: string
  agent_id: string
  prediction_id: string | null
  alert_type: string
  severity: AlertSeverity
  message: string
  acknowledged: boolean
  created_at: string
}

// ── WebSocket envelope ────────────────────────────────────────────────────────
export type WsChannel = 'metrics' | 'predictions' | 'alerts' | 'system'
export type WsType = 'event' | 'error' | 'ping' | 'pong'

export interface WsEnvelope<T = unknown> {
  type: WsType
  channel: WsChannel
  ts: string
  data: T
}

// ── ML Status ─────────────────────────────────────────────────────────────────
export interface MLStatus {
  status: 'ready' | 'not_available' | 'training' | 'failed'
  model_version?: string
  trained_at?: string
  training_samples?: number
  features?: string[]
  labels?: string[]
  job_status?: string
}
