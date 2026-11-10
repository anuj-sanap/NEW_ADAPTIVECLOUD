# AdaptiveCloud Architecture Documentation

## 1. System Overview
The **AI-Based Adaptive Cloud Security and Predictive Maintenance System** is an end-to-end, zero-budget cloud security and host health monitoring platform.

- **Monitored Workers**: Windows Server 2022 VMs hosted on Google Cloud Platform (utilizing free trial credits).
- **Control Plane**: Docker Compose on a developer Windows 10/11 workstation with WSL2 backend.
- **Private Networking**: Tailscale WireGuard mesh encrypts and routes all traffic between GCP VMs and the local PC without exposing public ports.

```
       +-------------------------------------------------------------+
       | GCP Free Tier VM (Windows Server 2022)                       |
       |  - Python 3.11 Ingest Agent (psutil + pywin32)              |
       |  - Wazuh Host Agent MSI                                     |
       |  - Tailscale Client (IP: 100.64.0.2)                        |
       +------------------------------+------------------------------+
                                      | WireGuard Tunnel (Tailscale)
                                      v
+-------------------------------------+-------------------------------------+
| Developer Workstation (Windows 10/11 + Docker Desktop WSL2)                |
| Tailscale Node (IP: 100.64.0.1)                                            |
|                                                                           |
|  +---------------------------------------------------------------------+  |
|  | Nginx Reverse Proxy (:80 -> :443 HTTPS, TLS, Rate Limiting, WS)     |  |
|  +-------------------+-----------------------------+-------------------+  |
|                      |                             |                      |
|                      v                             v                      |
|  +-------------------------------+     +-------------------------------+  |
|  | FastAPI Backend (:8000)       |     | React 18 SPA (Vite/Tailwind)  |  |
|  | - JWT Auth & RBAC (3 Roles)   |     +-------------------------------+  |
|  | - REST Ingest & WebSocket Hub |                                        |
|  | - Correlator & Adaptive Engine|                                        |
|  +---------------+---------------+                                        |
|                  |                                                        |
|         +--------+--------+                                               |
|         v                 v                                               |
|  +---------------+  +--------------------------------------------------+  |
|  | PostgreSQL 16 |  | ML Microservice (:8001)                          |  |
|  | (19 Tables)   |  | - Unsupervised Anomaly Detection                 |  |
|  +---------------+  | - XGBoost Multi-Class Classifier                 |  |
|                     | - Resource Forecast & Predictive Maintenance     |  |
|                     +--------------------------------------------------+  |
+---------------------------------------------------------------------------+
```

---

## 2. Component Breakdown

### 2.1 Edge Monitoring Agent (`agent/`)
- Lightweight Windows service running on GCP VMs.
- **`collector.py`**:
  - CPU, RAM, Disk I/O, Network I/O, Process lists via `psutil`.
  - Windows Security & System Event Log via `pywin32` (`win32evtlog`).
- **`sender.py`**: Transmits periodic JSON payloads to `POST /api/v1/ingest` with `X-API-Key` authentication and exponential back-off via `tenacity`.

### 2.2 Control Backend (`backend/`)
- **FastAPI Core**: Async REST API with dependency injection for JWT users (`require_role`) and host agents (`get_agent_from_api_key`).
- **Database Layer**: SQLAlchemy 2 async engine with Alembic migrations, managing 19 models with UUID PKs and index optimizations.
- **WebSocket Hub (`/ws/live`)**:
  - Broadcasts on 6 channels (`metrics`, `detections`, `incidents`, `predictions`, `responses`, `models`).
  - Active client connection tracking with 20-second heartbeat.
- **Adaptive Engine**: Automatically issues response actions (`block_ip`, `kill_process`, `restart_service`) and updates the `blocklist` upon high-confidence detections.

### 2.3 Machine Learning Microservice (`ml/`)
- **Feature Extraction**: Canonical 11-feature normalized vectors from telemetry snapshots.
- **Attack Classification**: Multi-class XGBoost model classifying `benign`, `brute_force`, `ddos`, `port_scan`, `unauthorized_access`, and `suspicious_process`.
- **Zero-Fake-Metrics Policy**: Returns `{"status": "not_available"}` whenever no trained model artifact or insufficient training data exists.
- **Continuous Learning & Drift**: Active learning via analyst feedback (`feedback_labels`) and drift metrics (`drift_events`).

### 2.4 Deployment & Ingress (`deploy/`)
- **Nginx Reverse Proxy**:
  - SSL/TLS termination with HTTP -> HTTPS redirection.
  - Proxy buffer tuning and WebSocket upgrade headers (`Upgrade`, `Connection: "upgrade"`).
  - Rate limiting on `/api/v1/auth/login` to prevent brute force.
- **Docker Compose**: Orchestrates PostgreSQL 16 (persistent named volume), backend, frontend, and Nginx with memory constraints designed for 8–16 GB Windows host PCs.

---

## 3. Data Flow Pipelines

### 3.1 Telemetry & Detection Pipeline
1. Agent samples telemetry every 30 seconds -> sends HTTP POST to `/api/v1/ingest`.
2. Backend saves row to `metrics` table -> pushes live snapshot to WebSocket `metrics` channel.
3. Backend enqueues async task to ML service `/predict`.
4. If anomalous:
   - Row added to `detections` table.
   - Attack classification saved to `classifications`.
   - Live alert pushed to WebSocket `detections` channel.
   - If confidence exceeds threshold, auto-mitigation (`response_actions`) triggers and IP is added to `blocklist`.

### 3.2 Predictive Maintenance Pipeline
1. Host resource utilization trends analyzed across rolling windows.
2. Horizon forecasts saved to `predictions` and `maintenance_forecasts`.
3. Analysts alerted before disk exhaustion or resource leaks cause host outages.
