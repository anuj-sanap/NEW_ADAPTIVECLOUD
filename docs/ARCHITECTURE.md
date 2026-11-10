# Architecture — Adaptive Cloud Security System

## Overview
An AI-driven security monitoring platform that collects real-time telemetry from
Windows Server VMs on GCP, streams it through a FastAPI backend, runs ML-based
attack classification, and displays live alerts on a React dashboard.

---

## Component Map

```
┌─────────────────────────────────────────────────────────────────────┐
│  Developer PC (Windows 10/11)                                       │
│  ┌─────────────────── Docker Compose ───────────────────────────┐   │
│  │  nginx (HTTPS:443)  ←──── reverse proxy ────────────────────┐│   │
│  │  fastapi (:8000)    ←──── REST + WebSocket                  ││   │
│  │  ml-service (:8001) ←──── inference + training              ││   │
│  │  postgres (:5432)   ←──── persistent storage                ││   │
│  │  wazuh-manager (:1514/:55000) ← SIEM                        ││   │
│  └──────────────────────────────────────────────────────────────┘│   │
│                                                                     │
│  React Dev Server (:5173)  ← Vite HMR (dev only)                  │
└──────────────────┬──────────────────────────────────────────────────┘
                   │ Tailscale mesh (encrypted WireGuard)
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐   ┌────────▼───────┐
│ GCP VM #1      │   │ GCP VM #2      │
│ Windows Srv    │   │ Windows Srv    │
│ 2022           │   │ 2022           │
│                │   │                │
│ agent/         │   │ agent/         │
│ (psutil +      │   │ (psutil +      │
│  pywin32)      │   │  pywin32)      │
│                │   │                │
│ Wazuh Agent    │   │ Wazuh Agent    │
│ (MSI)          │   │ (MSI)          │
└────────────────┘   └────────────────┘
```

---

## Network Topology

### Tailscale Mesh
- All nodes (dev PC + GCP VMs) join the same Tailscale tailnet
- Each node gets a stable `100.x.x.x` Tailscale IP
- WireGuard encrypts all traffic between nodes — no public IPs needed
- Dev PC acts as the control plane; VMs are workers
- Cost: **₹0** (Tailscale free tier: up to 100 devices, 3 users)

### Port Map
| Service | Listen | Exposed |
|---------|--------|---------|
| Nginx | 443, 80 | PC Tailscale IP |
| FastAPI | 8000 | Nginx only (not direct) |
| ML Service | 8001 | FastAPI only (internal) |
| PostgreSQL | 5432 | Backend only (not Nginx) |
| Wazuh Manager API | 55000 | Nginx + FastAPI |
| Wazuh Agent | 1514 | VMs → PC |
| React (dev) | 5173 | localhost only |

---

## Security Model

### Transport
- Tailscale provides WireGuard encryption for all VM ↔ PC traffic
- Nginx terminates TLS (mkcert self-signed or Let's Encrypt)
- Internal Docker services communicate over Docker bridge network

### Application Auth
1. **Human users** → JWT (HS256, 15-min access + 7-day refresh)
2. **Agent processes** → X-API-Key (bcrypt-hashed in DB, never stored plain)
3. **WebSocket** → JWT passed as query param `?token=<access_token>`

### Role-Based Access
- `admin`: full CRUD, can train models, manage agents/users
- `analyst`: read metrics, predictions, alerts; cannot manage agents
- `viewer`: read-only dashboard access

---

## Data Pipeline

```
Windows Agent (every 30s)
    │
    ▼  POST /api/v1/ingest (X-API-Key)
FastAPI Backend
    │
    ├── Save MetricRecord to PostgreSQL
    ├── Broadcast raw metric over WebSocket (channel: "metrics")
    └── POST to ML Service /predict (internal)
            │
            ▼
        ML Service
            ├── Load active model (XGBoost / scikit-learn)
            ├── Extract features from MetricPayload
            ├── Predict label + confidence
            └── POST result back to Backend
                    │
                    ├── Save PredictionRecord to PostgreSQL
                    ├── Broadcast prediction over WebSocket (channel: "predictions")
                    └── If threat detected → create AlertRecord
                                └── Broadcast alert over WebSocket (channel: "alerts")
```

---

## ML Pipeline

### Features (derived from MetricPayload)
- cpu_percent, memory_percent, memory_used_mb
- disk_read_bytes_sec, disk_write_bytes_sec
- net_bytes_sent_sec, net_bytes_recv_sec
- active_connections, process_count
- event_log_errors_1m, event_log_warnings_1m

### Algorithm
- **Primary**: XGBoostClassifier (multi-class, 6 labels)
- **Fallback**: RandomForestClassifier (scikit-learn)
- **Validation**: 5-fold stratified cross-validation
- **No hardcoded metrics**: all metrics derived from real training data only

### Training Trigger
- Manual: `POST /api/v1/ml/train` (admin only)
- Minimum: 500 labelled samples required before training is attempted
- If insufficient data: returns `{"status": "not_available"}`

### Model Versioning
- Stored in `ml/models/` as `model_v{major}.{minor}.{patch}.joblib`
- Metadata tracked in `ml_models` DB table
- Only one model marked `is_active = true` at a time

---

## Wazuh Integration

Wazuh provides host-based intrusion detection as a complementary signal:
- **Wazuh Manager**: runs in Docker on dev PC
- **Wazuh Agents**: installed via MSI on each GCP Windows VM
- **Alert forwarding**: FastAPI subscribes to Wazuh REST API (`/security/events`)
  for high-severity (level ≥ 10) alerts and stores them as `AlertRecord` rows
- Wazuh alerts appear in the same WebSocket `"alerts"` channel

---

## Deployment Notes

### Dev / Local
```
docker compose -f deploy/docker-compose.yml up -d
npm run dev  # in frontend/
```

### Production (self-hosted on dev PC)
```
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.prod.yml up -d
```

The prod override adds:
- Nginx with real TLS cert
- PostgreSQL with volume mount
- Resource limits on containers

### GCP Free Tier Usage
- **Compute Engine**: e2-micro (1 vCPU, 1 GB RAM) × 2 VMs → free tier eligible
- **Networking**: Tailscale eliminates need for public IPs
- **Storage**: 30 GB standard persistent disk per VM (free tier)
- **Cost**: ₹0 within free trial
