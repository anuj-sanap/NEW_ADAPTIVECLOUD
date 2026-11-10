# API Contract — Adaptive Cloud Security System
> Version: v1 | Base: `/api/v1` | WebSocket: `/ws/live`

---

## Authentication

| Method | Header / Body | Used by |
|--------|--------------|---------|
| JWT Bearer | `Authorization: Bearer <access_token>` | Human users (admin, analyst, viewer) |
| API Key | `X-API-Key: <key>` | Windows monitoring agents |

- Access token TTL: **15 minutes**
- Refresh token TTL: **7 days**
- API keys stored as **bcrypt hashes** in DB; shown **once** at creation

---

## Role Permission Matrix

| Endpoint | admin | analyst | viewer | agent |
|----------|:-----:|:-------:|:------:|:-----:|
| POST /auth/login | ✅ | ✅ | ✅ | — |
| POST /auth/refresh | ✅ | ✅ | ✅ | — |
| GET /agents | ✅ | — | — | — |
| POST /agents | ✅ | — | — | — |
| DELETE /agents/{id} | ✅ | — | — | — |
| POST /ingest | — | — | — | ✅ |
| GET /metrics | ✅ | ✅ | ✅ | — |
| GET /metrics/latest | ✅ | ✅ | ✅ | — |
| GET /predictions | ✅ | ✅ | ✅ | — |
| POST /ml/train | ✅ | — | — | — |
| GET /ml/status | ✅ | ✅ | — | — |
| GET /health | public | public | public | public |

---

## Endpoints

### POST /api/v1/auth/login
Authenticate a user and receive JWT tokens.

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response 200:**
```json
{
  "access_token": "string (JWT)",
  "refresh_token": "string (JWT)",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Errors:** `401 Unauthorized` → `{"detail": "Invalid credentials", "code": "AUTH_INVALID"}`

---

### POST /api/v1/auth/refresh
Exchange a refresh token for new access token.

**Request:**
```json
{ "refresh_token": "string" }
```

**Response 200:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 900
}
```

---

### GET /api/v1/agents
List all registered monitoring agents. **Requires: admin**

**Response 200:**
```json
[
  {
    "id": "uuid",
    "hostname": "string",
    "os_version": "string",
    "ip_address": "string",
    "status": "online | offline",
    "last_seen": "2024-01-01T00:00:00Z",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

---

### POST /api/v1/agents
Register a new agent. **Requires: admin**

**Request:**
```json
{
  "hostname": "string",
  "os_version": "string",
  "ip_address": "string"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "hostname": "string",
  "api_key": "string (shown ONCE, store securely)"
}
```

---

### DELETE /api/v1/agents/{id}
Revoke an agent. **Requires: admin**

**Response 204:** No content

---

### POST /api/v1/ingest
Receive a metric snapshot from a Windows agent. **Requires: X-API-Key**

**Request body** (see `docs/DATA_SCHEMA.md` for full MetricPayload spec):
```json
{
  "agent_id": "uuid",
  "collected_at": "2024-01-01T00:00:00Z",
  "cpu_percent": 42.5,
  "memory_percent": 68.1,
  "memory_used_mb": 10944.0,
  "disk_read_bytes_sec": 1048576.0,
  "disk_write_bytes_sec": 524288.0,
  "net_bytes_sent_sec": 204800.0,
  "net_bytes_recv_sec": 1048576.0,
  "active_connections": 23,
  "process_count": 142,
  "top_processes": [
    {"pid": 1234, "name": "svchost.exe", "cpu_percent": 5.1, "memory_mb": 128.4}
  ],
  "event_log_errors_1m": 0,
  "event_log_warnings_1m": 2
}
```

**Response 202:**
```json
{
  "metric_id": "uuid",
  "queued_for_inference": true
}
```

---

### GET /api/v1/metrics
Query stored metrics. **Requires: analyst+**

**Query params:** `agent_id` (uuid, optional), `from` (ISO datetime), `to` (ISO datetime), `limit` (int, default 100, max 1000)

**Response 200:**
```json
{
  "total": 500,
  "items": [ /* MetricPayload + id field */ ]
}
```

---

### GET /api/v1/metrics/latest
Get most recent metric per agent. **Requires: analyst+**

**Query params:** `agent_id` (optional — omit for all agents)

**Response 200:**
```json
[ /* array of latest MetricPayload records */ ]
```

---

### GET /api/v1/predictions
Query ML predictions. **Requires: analyst+**

**Query params:** `agent_id` (uuid, optional), `limit` (int, default 50, max 500), `label` (filter by attack label)

**Response 200:**
```json
{
  "total": 120,
  "items": [
    {
      "id": "uuid",
      "agent_id": "uuid",
      "metric_id": "uuid",
      "predicted_at": "2024-01-01T00:00:00Z",
      "label": "benign",
      "confidence": 0.97,
      "model_version": "v1.0.0",
      "features_used": ["cpu_percent", "net_bytes_recv_sec", "active_connections"]
    }
  ]
}
```

If no model is trained yet:
```json
{ "status": "not_available" }
```

---

### POST /api/v1/ml/train
Trigger model retraining on accumulated data. **Requires: admin**

**Response 202:**
```json
{
  "job_id": "uuid",
  "status": "queued",
  "message": "Training job queued. Poll GET /api/v1/ml/status for progress."
}
```

---

### GET /api/v1/ml/status
Get current model status and last training metadata. **Requires: analyst+**

**Response 200 (model available):**
```json
{
  "status": "ready",
  "model_version": "v1.0.0",
  "trained_at": "2024-01-01T00:00:00Z",
  "training_samples": 4821,
  "features": ["cpu_percent", "memory_percent", "net_bytes_recv_sec", "active_connections", "disk_read_bytes_sec"],
  "labels": ["benign", "brute_force", "ddos", "port_scan", "unauthorized_access", "suspicious_process"],
  "job_status": "idle"
}
```

**Response 200 (no model):**
```json
{ "status": "not_available" }
```

---

### GET /api/v1/health
Liveness + readiness check. **Public.**

**Response 200:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "db": "ok",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

## WebSocket — /ws/live

### Connection
```
ws://host/ws/live?token=<JWT access_token>
```

### Envelope Schema
Every message sent by the server follows this envelope:
```json
{
  "type": "string",
  "channel": "string",
  "ts": "ISO-8601 UTC string",
  "data": {}
}
```

| Field | Description |
|-------|-------------|
| `type` | Message type: `"event"`, `"error"`, `"ping"` |
| `channel` | `"metrics"`, `"predictions"`, `"alerts"` |
| `ts` | Server UTC timestamp |
| `data` | Payload — schema depends on channel |

### Channels

**metrics** — emitted on each /ingest call:
```json
{ "type": "event", "channel": "metrics", "ts": "...", "data": { /* MetricPayload */ } }
```

**predictions** — emitted after ML inference:
```json
{ "type": "event", "channel": "predictions", "ts": "...", "data": { /* PredictionRecord */ } }
```

**alerts** — emitted when label != "benign" and confidence > threshold:
```json
{ "type": "event", "channel": "alerts", "ts": "...", "data": {
  "id": "uuid",
  "agent_id": "uuid",
  "label": "brute_force",
  "confidence": 0.93,
  "severity": "high",
  "message": "Brute force attack detected on WIN-SRV-01"
}}
```

### Client → Server
Clients may send:
```json
{ "type": "ping" }
```
Server responds:
```json
{ "type": "pong", "channel": "system", "ts": "...", "data": {} }
```

---

## Standard Error Schema
```json
{
  "detail": "Human-readable error message",
  "code": "MACHINE_READABLE_CODE"
}
```

| HTTP | Code | Meaning |
|------|------|---------|
| 400 | `VALIDATION_ERROR` | Request body / params invalid |
| 401 | `AUTH_REQUIRED` | No or expired token |
| 401 | `AUTH_INVALID` | Wrong credentials |
| 403 | `FORBIDDEN` | Insufficient role |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `CONFLICT` | Duplicate resource |
| 422 | `UNPROCESSABLE` | Pydantic validation failure |
| 500 | `INTERNAL_ERROR` | Unexpected server error |
| 503 | `NOT_AVAILABLE` | Model/service not ready |
