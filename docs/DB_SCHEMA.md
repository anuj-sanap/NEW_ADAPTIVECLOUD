# AdaptiveCloud Database Schema Documentation

This document describes all relational tables, types, foreign keys, and indexes managed by SQLAlchemy 2 and Alembic migrations.

All tables share standard metadata:
- **`id`**: `UUID` v4 Primary Key
- **`created_at`**: `TIMESTAMPTZ` (UTC), defaults to `CURRENT_TIMESTAMP`
- **`updated_at`**: `TIMESTAMPTZ` (UTC), auto-updated on modification

All time-series tables (metrics, security_events, flow_features, detections, classifications, predictions) include a composite index on `(host_id, ts)` for fast lookups.

---

## 1. Core & Infrastructure Tables

### 1.1 `users`
User accounts with Role-Based Access Control (RBAC).

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | No | Primary Key |
| `username` | `VARCHAR(64)` | No | Unique login username |
| `email` | `VARCHAR(255)` | No | Unique email address |
| `password_hash` | `VARCHAR(255)` | No | Bcrypt hashed password |
| `role` | `VARCHAR(32)` | No | `admin` \| `analyst` \| `viewer` |
| `is_active` | `BOOLEAN` | No | Account status flag |
| `last_login` | `TIMESTAMPTZ` | Yes | Last authentication timestamp |
| `created_at` | `TIMESTAMPTZ` | No | Timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | Timestamp |

### 1.2 `hosts`
Monitored physical/virtual machines (Windows Server 2022 on GCP, etc.).

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | No | Primary Key (Host ID) |
| `hostname` | `VARCHAR(255)` | No | Host machine name |
| `os_version` | `VARCHAR(128)` | No | Operating system string |
| `agent_platform` | `VARCHAR(64)` | No | Agent sensor type (`windows`, `linux`) |
| `ip_address` | `VARCHAR(64)` | Yes | Tailscale or local IP address |
| `status` | `VARCHAR(32)` | No | `online` \| `offline` |
| `api_key_hash` | `VARCHAR(255)` | No | Bcrypt hash of host's secret ingest key |
| `last_seen` | `TIMESTAMPTZ` | Yes | Heartbeat timestamp |
| `is_active` | `BOOLEAN` | No | Active tracking flag |
| `created_at` | `TIMESTAMPTZ` | No | Timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | Timestamp |

---

## 2. Telemetry & Ingestion Tables

### 2.1 `metrics`
System resource utilization samples sent by agents.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | No | Primary Key |
| `host_id` | `UUID` | No | Foreign Key -> `hosts.id` (CASCADE) |
| `ts` | `TIMESTAMPTZ` | No | Observation timestamp (UTC) |
| `cpu` | `FLOAT` | No | Total CPU utilization % |
| `mem` | `FLOAT` | No | RAM memory utilization % |
| `disk` | `FLOAT` | No | Disk I/O bytes/sec |
| `net_in` | `FLOAT` | No | Network input bytes/sec |
| `net_out` | `FLOAT` | No | Network output bytes/sec |
| `load` | `FLOAT` | No | System load indicator |
| `proc_count` | `INTEGER` | No | Total active processes |
| `conn_count` | `INTEGER` | No | Active network socket connections |
| `extra` | `JSON` | Yes | Process lists, sensor details, disk free space |
| `created_at` | `TIMESTAMPTZ` | No | Timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | Timestamp |

**Indexes**: `ix_metrics_host_id_ts(host_id, ts)`

### 2.2 `security_events`
Security alerts and raw audit events from Wazuh SIEM and Windows Event Logs.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | No | Primary Key |
| `host_id` | `UUID` | No | Foreign Key -> `hosts.id` (CASCADE) |
| `ts` | `TIMESTAMPTZ` | No | Event timestamp |
| `source` | `VARCHAR(32)` | No | `wazuh` \| `agent` \| `winevent` |
| `rule_id` | `VARCHAR(64)` | Yes | Rule identifier |
| `level` | `INTEGER` | No | Severity level (1-15) |
| `category` | `VARCHAR(64)` | Yes | Threat category |
| `src_ip` | `VARCHAR(64)` | Yes | Attacker IP address |
| `user` | `VARCHAR(128)` | Yes | Target user account |
| `event_id` | `INTEGER` | Yes | Windows Event ID (e.g. 4625 for logon failure) |
| `raw` | `JSON` | Yes | Full JSON payload of alert |
| `created_at` | `TIMESTAMPTZ` | No | Timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | Timestamp |

**Indexes**: `ix_security_events_host_id_ts(host_id, ts)`

### 2.3 `flow_features`
High-frequency network flow summary statistics.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | No | Primary Key |
| `host_id` | `UUID` | No | Foreign Key -> `hosts.id` (CASCADE) |
| `ts` | `TIMESTAMPTZ` | No | Flow window timestamp |
| `features` | `JSON` | No | Dictionary of engineered flow numerical features |
| `created_at` | `TIMESTAMPTZ` | No | Timestamp |
| `updated_at` | `TIMESTAMPTZ` | No | Timestamp |

**Indexes**: `ix_flow_features_host_id_ts(host_id, ts)`

---

## 3. Detections, Incidents & Root Cause Analysis

### 3.1 `detections`
Unsupervised and statistical anomaly detection results.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | No | Primary Key |
| `host_id` | `UUID` | No | Foreign Key -> `hosts.id` (CASCADE) |
| `ts` | `TIMESTAMPTZ` | No | Anomaly timestamp |
| `anomaly_score` | `FLOAT` | No | Normalized score `[0.0, 1.0]` |
| `is_attack` | `BOOLEAN` | No | Flag indicating suspicious breach |
| `model_id` | `UUID` | Yes | Model reference |
| `status` | `VARCHAR(32)` | No | `open` \| `investigating` \| `closed` |

**Indexes**: `ix_detections_host_id_ts(host_id, ts)`

### 3.2 `classifications`
Multi-class attack classification inferences.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | No | Primary Key |
| `host_id` | `UUID` | No | Foreign Key -> `hosts.id` |
| `ts` | `TIMESTAMPTZ` | No | Classification timestamp |
| `detection_id` | `UUID` | Yes | Foreign Key -> `detections.id` |
| `label` | `VARCHAR(64)` | No | `benign`, `brute_force`, `ddos`, `port_scan`, `unauthorized_access`, `suspicious_process` |
| `confidence` | `FLOAT` | No | Predicted probability `[0.0, 1.0]` |
| `probs` | `JSON` | No | Multi-class probability distribution |
| `model_id` | `UUID` | Yes | Model reference |

**Indexes**: `ix_classifications_host_id_ts(host_id, ts)`

### 3.3 `incidents` & `incident_items`
Correlated clusters of alerts and detections.

- **`incidents`**: `title`, `severity` (`low`, `medium`, `high`, `critical`), `status` (`open`, `resolved`), `assigned_to`, `description`, `summary` (JSON).
- **`incident_items`**: Associates `incident_id` with `item_type` (`detection`, `security_event`, `prediction`) and `item_id`.

### 3.4 `rca_reports`
Automated Root Cause Analysis for resolved or escalated incidents.

- Columns: `incident_id`, `probable_cause`, `source_ips` (JSON array), `affected_hosts` (JSON array), `evidence` (JSON dict), `timeline` (JSON array).

---

## 4. Predictions & Predictive Maintenance

### 4.1 `predictions`
Short-term system trend and threat forecasting.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | No | Primary Key |
| `host_id` | `UUID` | No | Foreign Key -> `hosts.id` |
| `ts` | `TIMESTAMPTZ` | No | Generation timestamp |
| `kind` | `VARCHAR(32)` | No | `threat` \| `cpu` \| `memory` \| `disk` \| `service` |
| `horizon_min` | `INTEGER` | No | Forecast window (e.g. 15, 60 minutes) |
| `value` | `FLOAT` | No | Predicted target value |
| `probability` | `FLOAT` | No | Confidence or probability score |
| `model_id` | `UUID` | Yes | Model reference |
| `outcome_observed` | `FLOAT` | Yes | Ground truth metric when horizon elapses |

**Indexes**: `ix_predictions_host_id_ts(host_id, ts)`

### 4.2 `maintenance_forecasts`
Longer-term predictive maintenance projections for physical/virtual storage, RAM leaks, and degradation.

- Columns: `host_id`, `component` (`disk`, `memory`, `cpu`, `pagefile`), `metric_name`, `days_remaining`, `confidence`, `details` (JSON).

---

## 5. Adaptive Responses & Blocklist

### 5.1 `response_actions`
Automated or analyst-approved mitigation actions.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `UUID` | No | Primary Key |
| `host_id` | `UUID` | Yes | Target host |
| `incident_id` | `UUID` | Yes | Associated incident |
| `action` | `VARCHAR(64)` | No | `block_ip` \| `restrict` \| `restart_service` \| `kill_process` |
| `status` | `VARCHAR(32)` | No | `pending` \| `executed` \| `failed` \| `verified` \| `rolled_back` |
| `target` | `VARCHAR(255)` | No | Target IP, process name, or service name |
| `initiated_by` | `VARCHAR(64)` | No | `system` or username |
| `result` | `JSON` | Yes | Execution result & command output |

### 5.2 `blocklist`
Real-time IP ban registry synced with firewalls/proxies.

- Columns: `ip` (Unique), `reason`, `expires_at`, `active` (Boolean).

---

## 6. MLOps Lifecycle & Drift Detection

### 6.1 `ml_models`
Metadata, performance benchmarks, and deployment lifecycle status.
- Columns: `name`, `task`, `version`, `metrics` (JSON), `artifact_path`, `status` (`candidate` \| `active` \| `retired`).

### 6.2 `model_evaluations`
Benchmark evaluations on held-out test sets.
- Columns: `model_id`, `dataset_name`, `metrics` (JSON), `notes`.

### 6.3 `drift_events`
Statistical drift monitoring (e.g. Kolmogorov-Smirnov test, PSI) across features.
- Columns: `model_id`, `feature_name`, `drift_score`, `p_value`, `is_drift`, `details` (JSON).

### 6.4 `retraining_jobs`
Automated retraining pipeline runs.
- Columns: `model_id`, `status` (`pending`, `running`, `completed`, `failed`), `dataset_size`, `started_at`, `completed_at`, `error_message`, `metrics_summary`.

### 6.5 `feedback_labels`
Active learning annotations provided by security analysts.
- Columns: `detection_id`, `analyst_id`, `true_label`, `comments`.

---

## 7. Audit Logging

### 7.1 `audit_logs`
Immutable compliance and security audit log.
- Columns: `user_id`, `action`, `resource_type`, `resource_id`, `details` (JSON), `ip_address`.

