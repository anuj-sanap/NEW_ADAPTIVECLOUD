# AdaptiveCloud API Contract (v1)

- **Base URL**: `/api/v1`
- **WebSocket URL**: `/ws/live?token=<jwt>`
- **Authentication**:
  - **User JWT**: `Authorization: Bearer <access_token>`
  - **Agent Key**: `X-API-Key: <secret_key>`
- **Global Error Envelope**:
  ```json
  {
    "error": {
      "code": "UNAUTHORIZED | FORBIDDEN | NOT_FOUND | VALIDATION_ERROR | NOT_IMPLEMENTED | INTERNAL_SERVER_ERROR",
      "message": "Descriptive human-readable explanation"
    }
  }
  ```
- **Standard Pagination Envelope**:
  ```json
  {
    "items": [ ... ],
    "total": 120,
    "page": 1,
    "size": 50,
    "pages": 3
  }
  ```

---

## Complete Route Directory by Functional Group

| Route Group | Method | Path | Auth | Purpose |
|---|---|---|---|---|
| **Health** | `GET` | `/api/v1/health` | Public | Liveness and DB connectivity healthcheck |
| **Auth** | `POST` | `/api/v1/auth/login` | Public | Authenticate user and issue JWT access & refresh tokens |
| | `POST` | `/api/v1/auth/refresh` | Public | Issue fresh access token using valid refresh token |
| | `GET` | `/api/v1/auth/me` | Bearer | Retrieve profile & role of authenticated user |
| **Ingest** | `POST` | `/api/v1/ingest` | X-API-Key | Ingest real-time telemetry snapshot from host agent |
| **Hosts** | `GET` | `/api/v1/hosts` | Bearer (Analyst+) | List all registered monitoring hosts and statuses |
| | `POST` | `/api/v1/hosts` | Bearer (Admin) | Enroll a new host and generate an ingestion API key |
| | `GET` | `/api/v1/hosts/{id}` | Bearer (Analyst+) | Retrieve host hardware metadata, OS, and heartbeat |
| | `DELETE` | `/api/v1/hosts/{id}` | Bearer (Admin) | Decommission and revoke access for a host |
| **Metrics** | `GET` | `/api/v1/metrics` | Bearer (Analyst+) | Query time-series telemetry (CPU, RAM, Disk, Net, Load) |
| | `GET` | `/api/v1/metrics/latest` | Bearer (Viewer+) | Retrieve latest metric snapshot for all hosts |
| **Events** | `GET` | `/api/v1/events` | Bearer (Analyst+) | Query security events from Wazuh and Windows Event Log |
| | `POST` | `/api/v1/events` | X-API-Key / Admin | Ingest out-of-band security event alerts |
| **Detections** | `GET` | `/api/v1/detections` | Bearer (Analyst+) | Query anomaly detection scores and attack flags |
| | `GET` | `/api/v1/detections/{id}`| Bearer (Analyst+) | Inspect feature anomaly contributions for a detection |
| **Classifications** | `GET` | `/api/v1/classifications`| Bearer (Analyst+) | Query multi-class attack labels (`brute_force`, `ddos`, etc.) |
| | `GET` | `/api/v1/classifications/{id}`| Bearer (Analyst+) | Inspect classification probabilities & model version |
| **Incidents** | `GET` | `/api/v1/incidents` | Bearer (Analyst+) | List correlated security incidents with severity filters |
| | `POST` | `/api/v1/incidents` | Bearer (Analyst+) | Create or escalate a manual incident |
| | `GET` | `/api/v1/incidents/{id}` | Bearer (Analyst+) | Retrieve incident details, correlated events & timeline |
| | `PATCH` | `/api/v1/incidents/{id}` | Bearer (Analyst+) | Update status (`investigating`, `resolved`) or assignment |
| **RCA** | `GET` | `/api/v1/rca/{incident_id}` | Bearer (Analyst+) | Fetch Root Cause Analysis report, probable cause & evidence |
| | `POST` | `/api/v1/rca/{incident_id}` | Bearer (Analyst+) | Trigger automated RCA synthesis for an incident |
| **Predictions** | `GET` | `/api/v1/predictions` | Bearer (Viewer+) | Retrieve short-term trend forecasts & threat projections |
| | `POST` | `/api/v1/predictions/query`| Bearer (Analyst+) | Generate ad-hoc forecast for a specific host & horizon |
| **Maintenance** | `GET` | `/api/v1/maintenance` | Bearer (Viewer+) | Fetch predictive maintenance component exhaustion projections |
| | `GET` | `/api/v1/maintenance/{host_id}`| Bearer (Viewer+) | Component failure horizon & disk exhaustion forecast |
| **Responses** | `GET` | `/api/v1/responses` | Bearer (Analyst+) | List automated and analyst-initiated adaptive actions |
| | `POST` | `/api/v1/responses` | Bearer (Admin) | Execute countermeasure (`block_ip`, `kill_process`, `restart_service`) |
| | `POST` | `/api/v1/responses/{id}/rollback` | Bearer (Admin) | Revert previously executed countermeasure |
| **Blocklist** | `GET` | `/api/v1/blocklist` | Bearer (Analyst+) | List active dynamically blocked IP addresses |
| | `POST` | `/api/v1/blocklist` | Bearer (Admin) | Manually add IP to firewall blocklist with expiration |
| | `DELETE`| `/api/v1/blocklist/{ip}` | Bearer (Admin) | Remove IP from blocklist |
| **Models** | `GET` | `/api/v1/models` | Bearer (Analyst+) | List registered ML models, performance metrics & status |
| | `POST` | `/api/v1/models/promote`| Bearer (Admin) | Promote candidate model to active deployment |
| | `GET` | `/api/v1/models/{id}/drift`| Bearer (Analyst+) | Check feature drift statistics (KS-test / PSI) |
| **Learning** | `GET` | `/api/v1/learning/jobs` | Bearer (Admin) | List model retraining jobs and datasets |
| | `POST` | `/api/v1/learning/train`| Bearer (Admin) | Trigger model retraining on newly accumulated data |
| | `POST` | `/api/v1/learning/feedback`| Bearer (Analyst) | Submit analyst ground-truth label for active learning |
| **Reports** | `GET` | `/api/v1/reports/summary`| Bearer (Viewer+) | Generate compliance summary report (PDF / JSON) |
| | `GET` | `/api/v1/reports/audit` | Bearer (Admin) | Export compliance audit trail for external auditors |
| **Audit** | `GET` | `/api/v1/audit` | Bearer (Admin) | Query administrative access and configuration audit logs |
| **Dashboard** | `GET` | `/api/v1/dashboard/summary` | Bearer (Viewer+) | High-level KPI summary: online hosts, active alerts, incidents |
| **WebSocket** | `WS` | `/ws/live` | Bearer in query | Bi-directional streaming: metrics, detections, incidents, responses |
