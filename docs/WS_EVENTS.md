# AdaptiveCloud WebSocket Live Streaming Specification

## Overview
- **Endpoint**: `/ws/live`
- **Protocol**: `ws://` (in dev) / `wss://` (in production behind HTTPS Nginx)
- **Authentication**: JWT access token provided as a query parameter:
  ```
  wss://localhost/ws/live?token=<jwt_access_token>
  ```
- **Heartbeat**: Automatic server `ping` dispatched every 20 seconds. Clients may also send `{"type": "ping"}` to receive an immediate `{"type": "pong"}`.

---

## Message Envelope
All events emitted by the server adhere to the standard envelope format:

```json
{
  "type": "event",
  "channel": "metrics | detections | incidents | predictions | responses | models | system",
  "ts": "2026-11-10T19:00:00.000000Z",
  "data": { ... }
}
```

---

## Channels & Event Payloads

### 1. `metrics` Channel
Emitted when an agent posts telemetry snapshots.
```json
{
  "type": "event",
  "channel": "metrics",
  "ts": "2026-11-10T19:00:00.000000Z",
  "data": {
    "host_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "hostname": "WIN-SRV-01",
    "ts": "2026-11-10T19:00:00.000000Z",
    "cpu": 72.4,
    "mem": 64.1,
    "disk": 2048576.0,
    "net_in": 1048576.0,
    "net_out": 524288.0,
    "load": 2.5,
    "proc_count": 142,
    "conn_count": 38
  }
}
```

### 2. `detections` Channel
Emitted when an anomaly or multi-class attack is detected.
```json
{
  "type": "event",
  "channel": "detections",
  "ts": "2026-11-10T19:00:01.000000Z",
  "data": {
    "detection_id": "c1f10bc5-62bb-4d56-b09b-06488d5e825a",
    "host_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "anomaly_score": 0.94,
    "is_attack": true,
    "label": "brute_force",
    "confidence": 0.91,
    "status": "open"
  }
}
```

### 3. `incidents` Channel
Emitted when an incident is opened, updated, or escalated.
```json
{
  "type": "event",
  "channel": "incidents",
  "ts": "2026-11-10T19:00:02.000000Z",
  "data": {
    "incident_id": "e9b251a2-c7bb-4e6f-a0e2-66388901bbdc",
    "title": "Correlated Brute Force Campaign against WIN-SRV-01",
    "severity": "high",
    "status": "open",
    "affected_hosts": ["WIN-SRV-01"]
  }
}
```

### 4. `predictions` Channel
Emitted when predictive maintenance or resource horizon forecasts are computed.
```json
{
  "type": "event",
  "channel": "predictions",
  "ts": "2026-11-10T19:00:03.000000Z",
  "data": {
    "host_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "kind": "memory",
    "horizon_min": 60,
    "value": 92.5,
    "probability": 0.88
  }
}
```

### 5. `responses` Channel
Emitted when an automated mitigation or countermeasure is queued or executed.
```json
{
  "type": "event",
  "channel": "responses",
  "ts": "2026-11-10T19:00:04.000000Z",
  "data": {
    "action_id": "5fa23d61-b751-419b-a0d3-356cfc431477",
    "action": "block_ip",
    "target": "203.0.113.42",
    "status": "executed",
    "initiated_by": "system"
  }
}
```

### 6. `models` Channel
Emitted on model lifecycle transitions (retraining finished, candidate deployed).
```json
{
  "type": "event",
  "channel": "models",
  "ts": "2026-11-10T19:00:05.000000Z",
  "data": {
    "model_id": "22a83e02-b2df-4796-93d3-1a2f647971eb",
    "name": "attack_classifier_xgboost",
    "version": "v1.1.0",
    "status": "active"
  }
}
```

### 7. `system` Channel (Heartbeat & Diagnostics)
Emitted periodically every 20 seconds.
```json
{
  "type": "ping",
  "channel": "system",
  "ts": "2026-11-10T19:00:20.000000Z",
  "data": {
    "server_time": "2026-11-10T19:00:20.000000Z"
  }
}
```
Client response:
```json
{
  "type": "pong"
}
```

