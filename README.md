# AI-Based Adaptive Cloud Security & Predictive Maintenance System

> **Budget: ₹0 | Cloud: GCP Free Trial | Dev: Windows 10/11 + Docker Desktop (WSL2 backend)**

A production-style, full-stack AI security monitoring platform that:
- Collects real-time telemetry from **Windows Server 2022 GCP VMs** using `psutil` + `pywin32`
- Streams data to a **FastAPI** backend via REST (X-API-Key) and broadcasts live events over **WebSocket**
- Runs **XGBoost** classification to detect: `brute_force`, `ddos`, `port_scan`, `unauthorized_access`, `suspicious_process`
- Visualises everything in a **React 18 + TypeScript + Tailwind** dashboard

---

## Architecture

```
Windows Agent (GCP VM)                  Developer PC (Windows 10/11)
┌────────────────────┐                  ┌─────────────────────────────────┐
│ psutil + pywin32   │──X-API-Key POST──▶│ Nginx :443 (TLS)                │
│ 30s snapshot loop  │  Tailscale VPN    │  → FastAPI :8000                │
│ Wazuh Agent MSI    │──────────────────▶│  → ML Service :8001             │
└────────────────────┘                  │  → PostgreSQL 16                │
                                        │  → React SPA (dist/)            │
                                        └─────────────────────────────────┘
                                                     │ WebSocket
                                              Browser dashboard
```

---

## Stack

| Layer | Technology |
|-------|-----------|
| Agent (Windows) | Python 3.11, psutil, pywin32, tenacity |
| Backend | FastAPI, SQLAlchemy 2 async, Alembic, asyncpg |
| Database | PostgreSQL 16 (partitioned `metrics` table) |
| ML | XGBoost, scikit-learn, pandas, numpy, joblib |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts, Zustand |
| Auth | JWT (users) + X-API-Key bcrypt (agents) |
| Proxy | Nginx 1.27 (TLS termination, WebSocket upgrade) |
| Network | Tailscale (WireGuard mesh, free tier) |
| Containers | Docker Compose (Linux containers on WSL2 backend) |

---

## Prerequisites

- Windows 10/11 with PowerShell 7+
- Docker Desktop (WSL2 backend) — [install](https://docs.docker.com/desktop/install/windows-install/)
- Python 3.11+ — [install](https://www.python.org/downloads/)
- Node 20+ — [install](https://nodejs.org/)
- Git — [install](https://git-scm.com/)
- Tailscale (free) — [install](https://tailscale.com/download/windows)

---

## Quick Start

### 1. Bootstrap
```powershell
cd d:\NEW_ADAPTIVECLOUD
.\scripts\bootstrap.ps1
```

### 2. Configure secrets
```powershell
# Edit the copied .env files
code backend\.env     # Set JWT_SECRET_KEY (32-char hex)
code agent\.env       # Set AGENT_ID, AGENT_API_KEY, BACKEND_URL
```

### 3. Generate TLS certificate
```powershell
.\scripts\generate-cert.ps1
```

### 4. Start the Docker stack
```powershell
cd deploy
docker compose up -d
docker compose logs -f backend   # Watch startup
```

### 5. Run database migrations
```powershell
cd ..\backend
.\.venv\Scripts\alembic upgrade head
```

### 6. Create the first admin user
```powershell
.\.venv\Scripts\python scripts\create_admin.py
```

### 7. Register a monitoring agent (admin API)
```powershell
# Replace <token> with your login token from POST /api/v1/auth/login
Invoke-RestMethod -Method POST -Uri "https://localhost/api/v1/agents" `
  -Headers @{ Authorization = "Bearer <token>" } `
  -ContentType "application/json" `
  -Body '{"hostname":"WIN-SRV-01","os_version":"Windows Server 2022","ip_address":"100.64.x.x"}'
# Save the returned api_key — it is shown ONCE
```

### 8. Start the frontend dev server
```powershell
cd ..\frontend
npm run dev
# Open https://localhost:5173
```

### 9. Install agent on a GCP Windows VM
```powershell
# On the GCP VM (after Tailscale + Python installed):
cd C:\adaptive-agent
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
# Edit .env with your AGENT_ID, AGENT_API_KEY, BACKEND_URL
.\.venv\Scripts\python src\main.py
```

---

## Directory Structure

```
NEW_ADAPTIVECLOUD/
├── agent/                  # Windows monitoring agent
│   ├── src/
│   │   ├── collector.py    # psutil + pywin32 telemetry
│   │   ├── sender.py       # HTTP POST with retry
│   │   └── main.py         # Entry point
│   └── requirements.txt
├── backend/                # FastAPI application
│   ├── app/
│   │   ├── api/v1/routes/  # auth, agents, ingest, metrics, predictions
│   │   ├── core/           # config, security, logging
│   │   ├── db/             # SQLAlchemy engine + base
│   │   ├── models/         # ORM models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── websocket/      # WS manager + router
│   ├── alembic/            # DB migrations
│   └── scripts/            # create_admin.py
├── ml/                     # ML microservice
│   └── src/
│       ├── features.py     # Feature extraction
│       ├── trainer.py      # XGBoost training pipeline
│       ├── predictor.py    # Inference
│       └── app.py          # FastAPI ML service
├── frontend/               # React 18 dashboard
│   └── src/
│       ├── pages/          # LoginPage, DashboardPage
│       ├── components/     # MetricCard, LiveAlertBanner, MetricChart
│       ├── hooks/          # useWebSocket
│       ├── store/          # authStore (Zustand)
│       ├── api/            # axios client with auto-refresh
│       └── types/          # TypeScript type definitions
├── deploy/                 # Docker Compose + Nginx + certs
│   ├── docker-compose.yml
│   └── nginx/
├── docs/                   # API_CONTRACT.md, DATA_SCHEMA.md, ARCHITECTURE.md
└── scripts/                # bootstrap.ps1, generate-cert.ps1
```

---

## API Quick Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/v1/auth/login | — | Get JWT tokens |
| POST | /api/v1/auth/refresh | — | Refresh access token |
| GET | /api/v1/agents | admin | List agents |
| POST | /api/v1/agents | admin | Register agent (returns api_key once) |
| POST | /api/v1/ingest | X-API-Key | Ingest metric snapshot |
| GET | /api/v1/metrics | analyst+ | Query metrics |
| GET | /api/v1/predictions | analyst+ | Query predictions |
| GET | /api/v1/ml/status | analyst+ | Model status |
| POST | /api/v1/ml/train | admin | Trigger retraining |
| GET | /api/v1/health | public | Healthcheck |
| WS | /ws/live?token=... | JWT | Live event stream |

See [docs/API_CONTRACT.md](docs/API_CONTRACT.md) for full schemas.

---

## Contributing

1. Keep all scripts as PowerShell (`.ps1`) or cross-platform Python
2. Never commit `.env` files or certificates
3. No hardcoded metrics — if no model: `{"status":"not_available"}`
4. UTC timestamps everywhere, UUID v4 IDs
5. Update `docs/DATA_SCHEMA.md` before changing any shared data contract

---

## Licence

MIT
