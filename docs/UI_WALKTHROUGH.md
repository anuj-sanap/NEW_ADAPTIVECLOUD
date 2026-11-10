# AdaptiveCloud UI Walkthrough & Verification Guide

This guide documents the design system, architecture, and step-by-step verification checklist for the complete React 18 + TypeScript + Vite + Tailwind CSS dashboard of **AdaptiveCloud**.

---

## 1. Design System & UX Standards

The dashboard adheres to strict design system principles:
- **Typography**: Inter font with clear typographical hierarchy (`text-xs` for dense SecOps metadata, `font-mono` for IPs/timestamps/scores).
- **Theming**: Light theme by default with persistent dark mode toggle (`localStorage.adaptivecloud_theme`).
- **Color Palette**:
  - Neutrals: Slate tones (`slate-50` to `slate-950`).
  - Brand Accent: Single indigo accent (`indigo-600` / `indigo-400`).
  - Status Indicators (used *only* for status):
    - Healthy / Verified / Benign: Emerald (`bg-emerald-500`, `text-emerald-600`).
    - Warning / Investigating / Pending: Amber (`bg-amber-500`, `text-amber-600`).
    - Danger / Critical / Blocked / Offline: Rose (`bg-rose-500`, `text-rose-600`).
- **Cards & Layout**: 8px grid system, `rounded-xl` cards with thin borders (`border-slate-200` / `dark:border-slate-800`), no heavy shadows, generous whitespace.
- **Role-Awareness**:
  - `admin`: Full administrative control (trigger retraining, promote/reject models, update policy, approve countermeasures).
  - `analyst`: Can record feedback, approve/rollback actions, block IPs, run drift checks.
  - `viewer`: Read-only access across all views. Action buttons are hidden or replaced with read-only badges.
- **Zero Mock Data Principle**: Every card, table, chart, and drawer connects directly to the real FastAPI REST endpoints (`/api/v1/*`) or live WebSocket (`/ws/live`). Empty states explicitly articulate what data is missing (e.g., cold start telemetry buffering percentages) rather than showing fake mock stats.

---

## 2. Navigational Hierarchy & Page Catalog

| Index | Page Name | Route | Core Endpoints & WS Channels | Plain-English Purpose |
|:---:|:---|:---|:---|:---|
| **1** | **Executive Overview** | `/` | `GET /dashboard/summary`, `GET /hosts` | Executive posture: health score gauge, 6 core KPIs, 24h attack distribution, and prioritized risk checklist. |
| **2** | **Live Cloud Monitoring** | `/monitoring` | `GET /hosts`, `GET /hosts/{id}/metrics`, `/ws/live?channel=metrics` | Cloud worker telemetry: live CPU, RAM, disk, network I/O charts, top process tables, and listening ports. |
| **3** | **Attack Detection** | `/detections` | `GET /detections`, `GET /detections/{id}`, `/ws/live?channel=detections` | Real-time flow anomaly feed: anomaly scores, raw flow feature drawer, and filterable threshold search. |
| **4** | **Attack Classification** | `/classifications` | `GET /classifications`, `POST /learning/feedback` | Attack categorizer: vector distribution pie chart and analyst human-in-the-loop ground truth feedback buttons. |
| **5** | **Root Cause Analysis** | `/rca` | `GET /incidents`, `GET /rca/{incident_id}`, `POST /rca/{incident_id}/regenerate` | Forensic correlation: plain-English HOD summaries, probable causes, source IP geolocation, and PowerShell fixes. |
| **6** | **Threat Prediction** | `/predictions` | `GET /predictions`, `POST /predictions/evaluate/{host_id}` | Attack forecasting: forward 15m/60m probability cards, zero-fabrication cold-start progress gates, and calibration audit. |
| **7** | **Predictive Maintenance** | `/maintenance` | `GET /maintenance/hosts/{id}`, `GET /maintenance/forecasts`, `POST /maintenance/evaluate/{id}` | Capacity forecasting: Theil-Sen disk days remaining, CPU/RAM saturation forecasts, and Windows service health. |
| **8** | **Response & Recovery** | `/responses` | `GET /responses`, `POST /responses/{id}/approve`, `POST /responses/{id}/rollback`, `GET/PUT /responses/policy`, `/blocklist` | Defensive countermeasures: IP blocklist management, Netsh firewall dry-run toggle, and approvals queue. |
| **9** | **ML & Adaptive Learning** | `/learning` | `GET /models`, `GET/POST /learning/drift`, `GET/POST /learning/jobs`, `POST /learning/jobs/{id}/promote` | Continuous learning: Champion vs Challenger metrics, Kolmogorov-Smirnov feature drift audit, and replay retraining. |
| **10** | **Reports & Audit Logs** | `/reports` | `GET /reports/summary`, `GET /reports/export?format=csv`, `GET /audit` | Compliance & auditing: executive compliance SLA cards, CSV/JSON report export, and immutable audit logs. |

---

## 3. Detailed Page Breakdown & Verification Checklist

### Page 1: Executive Overview (`/`)
- [ ] **System Health Gauge**: SVG radial gauge displaying score between 0 and 100 based on online hosts, incident severity, and prediction risks.
- [ ] **Key Stat Tiles**: Online hosts, active incidents, 24h attacks blocked, highest predicted threat probability, active ML champion model, and last retrain timestamp.
- [ ] **24-Hour Attack Breakdown**: Recharts horizontal bar chart visualizing attack counts across the 6 labels (`benign`, `brute_force`, `ddos`, `port_scan`, `unauthorized_access`, `suspicious_process`).
- [ ] **Prioritized Threat Vectors**: Ranked list with severity badges, probability bars, and host attribution.
- [ ] **"What Needs Attention" Panel**: High-level executive synthesis summarizing outstanding alerts.

### Page 2: Live Cloud Monitoring (`/monitoring`)
- [ ] **Host Selector Cards**: Horizontal cards showing hostname, operating system, IP address, and status dot (`online` / `offline`).
- [ ] **Real-Time Telemetry Charts**: Recharts AreaChart updating via WebSocket or 5s polling for:
  - CPU & Memory Utilization % (with warning thresholds).
  - Network Ingress/Egress (KB/s) and Disk I/O.
- [ ] **Process & Port Inspector**: Top CPU-consuming processes (name, PID, CPU %) and listening TCP/UDP ports.
- [ ] **Monitored Services**: Wazuh Agent, Windows Event Log service status.

### Page 3: Attack Detection (`/detections`)
- [ ] **Live Anomaly Feed**: Sortable, filterable DataTable querying `GET /api/v1/detections`.
- [ ] **Anomaly Scores**: Monospace anomaly score values with color thresholds (>0.7 flagged with danger badge).
- [ ] **Attack-Only Filter**: Quick toggle to filter out benign flows.
- [ ] **Forensics Drawer**: Slide-over drawer displaying raw network flow features (packet counts, byte rates, duration, inter-arrival times, TCP flags).

### Page 4: Attack Classification (`/classifications`)
- [ ] **Vector Distribution Pie Chart**: PieChart breaking down observed attack classes with custom tooltips.
- [ ] **Classifications DataTable**: Timestamp, Target Host, Predicted Class, Model ID, and Confidence %.
- [ ] **Active Learning Feedback Buttons**:
  - Green Checkmark (`Confirm`): Submits true label to `POST /api/v1/learning/feedback`.
  - Amber Edit Button (`Fix Label`): Opens modal to select the corrected label from the 6 standard classes and record comments.

### Page 5: Root Cause Analysis (`/rca`)
- [ ] **Incidents Table**: Severity badges (`critical`, `high`, `medium`, `low`), incident title, status, and creation date.
- [ ] **Forensic Investigation Drawer**:
  - **Executive Summary**: Plain-English explanation tailored for HOD/management review.
  - **Probable Cause**: Root cause hypothesis with calculated evidence confidence rating.
  - **Attributing Source IPs**: IP list with request counts, first/last seen times, and geolocation country/city tags.
  - **Remediation Commands**: Copyable PowerShell commands (e.g. `New-NetFirewallRule -RemoteAddress ... -Action Block`, `Disable-LocalUser`).
  - **Chronological Timeline**: Step-by-step event sequence correlating Windows Event IDs (4624, 4625, 4688), network flow bursts, and metric spikes.

### Page 6: Threat Prediction (`/predictions`)
- [ ] **Host & Horizon Selectors**: Allows selecting target monitored host and forecast horizon (15m vs 60m).
- [ ] **Vector Threat Probabilities**: 5 risk cards (brute-force, DDoS, port scan, unauthorized access, suspicious process) with probability percentages and severity badges.
- [ ] **Cold Start Safety Banner**: When fewer than 12 5-minute intervals exist, displays a progress bar (`Collecting telemetry data: X%`) explaining that predictions are blocked until sufficient telemetry history is recorded.
- [ ] **Audit & Calibration Table**: Historical predictions showing predicted probabilities versus actual ground-truth observed outcomes (`Pending Verification` vs `Attack Observed` vs `Benign`).

### Page 7: Predictive Maintenance (`/maintenance`)
- [ ] **Capacity Risk Tiles**:
  - **Disk Exhaustion**: Theil-Sen robust linear regression showing days remaining until 100% volume saturation.
  - **CPU Saturation**: Probability of sustained >85% compute spike within 15 minutes.
  - **Memory Leak Risk**: Continuous heap accumulation detection.
  - **Service Reliability**: Crash and restart tracking for Wazuh Agent and Windows services.
- [ ] **Saturation Threshold Trend**: Recharts AreaChart with a dashed red line at the 85% critical risk threshold.
- [ ] **Maintenance Forecast Audit**: Table of logged capacity forecasts and confidence scores.

### Page 8: Response & Recovery (`/responses`)
- [ ] **Policy & Engine Status Banner**: Shows current operating mode (`Dry-Run` vs `Live Enforcement`), max actions per minute limit, and count of protected allowlist IPs.
- [ ] **Approvals Queue**: Surfaces high-impact actions awaiting analyst authorization with `Authorize` and confirmation dialogs.
- [ ] **Active Host Blocklist**: Table of currently blocked IP addresses with TTLs and an `Unblock` button.
- [ ] **Manual IP Block Form**: Dialog allowing analysts to block an IP with reason and TTL duration.
- [ ] **Action Execution Log**: Pipeline tracking (`pending` &rarr; `executed` &rarr; `verified` / `failed`) with a one-click `Rollback` button.

### Page 9: ML & Adaptive Learning (`/learning`)
- [ ] **Champion vs Candidate Cards**:
  - **Active Champion**: Macro F1, precision, recall, latency (ms), and version in production.
  - **Challenger Candidate**: Side-by-side metric comparison for models trained on fresh replay buffers.
- [ ] **Promotion Gate**: Admin-only `Promote` and `Reject` buttons to safely promote candidate models into production without downtime.
- [ ] **Feature Drift Detection**:
  - `Run Drift Check` button triggering statistical tests.
  - Drift Events table displaying tested feature names, drift distances, p-values, and drift alerts.
- [ ] **Retraining Configuration**: Modal with replay buffer slider (5% to 50%) to prevent catastrophic forgetting.

### Page 10: Reports & Audit Logs (`/reports`)
- [ ] **Compliance Overview Tiles**: System uptime %, monitored host ratio, total detections, incidents, and attacks blocked.
- [ ] **Reporting Window Selector**: Toggle between 7, 14, and 30 day windows (`GET /api/v1/reports/summary?days=X`).
- [ ] **Forensic Report Export**: One-click download buttons for CSV and JSON reports (`GET /api/v1/reports/export?format=csv`).
- [ ] **Immutable Audit Trail**: Searchable, filterable table recording all administrative logins, model promotions, blocklist changes, and policy modifications.

---

## 4. Automated Test Results

### Frontend Unit & Component Tests (Vitest)
```powershell
Set-Location frontend; npm test
```
- `src/store/__tests__/themeStore.test.ts`: Toggles dark/light themes and tests `localStorage` persistence.
- `src/store/__tests__/authStore.test.ts`: Validates token management, user roles, permission checks, and logout.
- `src/components/__tests__/uiComponents.test.tsx`: Validates `Badge`, `SeverityBadge`, `StatusDot`, `Card`, `EmptyState`, and `DataTable` searching/sorting.
**Status**: 3 test files passed, 11 tests passed in ~3.5 seconds.

### Frontend Production Build (Vite + TypeScript)
```powershell
Set-Location frontend; npm run build
```
- `tsc --noEmit`: 0 errors.
- `vite build`: Successfully bundled production assets in `frontend/dist/`.
**Status**: Completed cleanly in ~9.9 seconds.

### Backend Test Suite (Pytest)
```powershell
& "backend/.venv/Scripts/pytest.exe" -v backend/tests
```
- 58/58 tests passing across Auth, RBAC, Detection, Classification, Incident Correlation, RCA, Threat Prediction, Predictive Maintenance, Response Engine, Blocklist, Drift Detection, Model Retraining, and Wazuh/WinEvent normalizers.
**Status**: 58 passed in ~20 seconds.

