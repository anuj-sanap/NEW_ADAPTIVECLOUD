# AdaptiveCloud - User Guide & Operational Manual
**For Department Heads (HOD), Infrastructure Managers, and Security Operations Center (SOC) Analysts**

---

## 1. Introduction & Core Mission

AdaptiveCloud is an autonomous, AI-driven cloud infrastructure protection and predictive maintenance platform. It transforms reactive IT management into proactive cyber defense by combining:
1. **Real-time Machine Learning Anomaly Detection** across live Windows Server telemetry.
2. **Automated Forensic Root Cause Analysis (RCA)** generating instant, plain-English incident timelines.
3. **Capacity Planning & Predictive Maintenance** forecasting disk fill horizons and service degradation days before outage occurs.
4. **Human-in-the-Loop Active Learning** ensuring algorithms continually adapt to enterprise workloads.

---

## 2. Navigating the Security & Operations Dashboard

The web management console is organized into 10 dedicated operational workspaces accessible via the left navigation sidebar.

### 2.1 Executive Overview (`/`)
*Designed for Head of Department (HOD) and IT Leadership*
- **Platform Health Score**: Overall operational health percentage (0-100%) computed dynamically from active incidents, offline hosts, and resource constraints.
- **Key Performance Indicators (KPIs)**:
  - *Active Correlated Incidents*: Unresolved security emergencies requiring analyst review.
  - *Attacks Neutralized Today*: Automated firewall blocks and process isolations executed.
  - *Highest Predicted Risk*: The single greatest cyber threat forecasted for the upcoming 60-minute window.
  - *Active ML Champion*: Current production model architecture and F1 accuracy score.
- **"What Needs Attention" Executive Briefing**: Natural-language summary explaining current operational risks in non-technical terms.

---

### 2.2 System & Infrastructure Monitoring (`/monitoring`)
*Real-time Telemetry & Host Health*
- **Live Fleet Table**: Shows all enrolled Windows Server worker nodes, IP addresses, OS versions, and heartbeat status.
- **Resource Gauges**: Live CPU utilization, memory pressure, disk utilization, and network throughput dials updated over WebSockets every 2 seconds.
- **Windows Service Inspector**: Live status of core Windows services (`w32time`, `dnscache`, `lanmanworkstation`).

---

### 2.3 Attack Detections & Classifications (`/detections` & `/classifications`)
*Deep Packet & Flow Intelligence*
- **Anomaly Stream**: Unsupervised Isolation Forest scores evaluating network flow statistical distributions.
- **Attack Classification**: Supervised XGBoost multi-class categorization assigning canonical labels:
  - `benign`: Normal business applications and management traffic.
  - `brute_force`: Repeated credential stuffing and RDP/SSH login failures.
  - `ddos`: High-velocity packet floods saturating host network stacks.
  - `port_scan`: Systematic port sweeps probing for open listening sockets.
  - `unauthorized_access`: Privilege escalation attempts (Windows Event 4672).
  - `suspicious_process`: Living-off-the-land binaries (LOLBins) or unrecognized script execution (Event 4688).

---

### 2.4 Forensic Root Cause Analysis (RCA) (`/rca`)
*Automated Incident Reconstruction*
- **Ordered Forensic Timeline**: Reconstructs events chronologically leading up to the breach (e.g. 5x Event 4625 failed logons -> 1x Event 4624 success -> PowerShell spawn).
- **Correlated Multi-Modal Evidence**: Joins metric spikes (CPU 99%), network flow rate anomalies, and Windows Event Logs.
- **Probable Cause Statement**: Transparent, rule-grounded forensic explanation with confidence rating.
- **PowerShell Remediation Scripts**: Generates exact, copy-pasteable PowerShell commands to isolate compromised accounts or block malicious CIDRs via `netsh advfirewall`.

---

### 2.5 Threat Forecasting & Capacity Planning (`/threat-prediction` & `/maintenance`)
*Predictive AI for Outage Prevention*
- **15-Minute & 60-Minute Threat Forecasts**: Autoregressive time-series models predicting the probability of imminent brute force or DDoS sweeps.
- **Cold-Start Indicator**: Displays an honest progress bar (`Collecting Telemetry Data: 65%`) when historical sample size is insufficient, guaranteeing zero fabricated forecasts.
- **Theil-Sen Disk Fill Horizon**: Robust linear trend estimation calculating exact days remaining before disk capacity reaches 95% critical threshold.
- **Service Failure Risk**: Identifies unstable background services displaying unexpected restarts.

---

### 2.6 Automated Countermeasures & Blocklist (`/responses`)
*Safe Automated Containment*
- **Active Quarantine Blocklist**: Live list of IP addresses blocked in host Windows Defender Firewalls with expiration TTLs.
- **Safety Rails**:
  - Whitelist of protected management IPs (Control Server, Gateway, Admin IP) that can **never** be blocked.
  - Dry-Run Toggle: Run automated actions in simulation mode before enabling live firewall actuation.
- **Rollback Action**: Instantly lift any firewall block or process restriction with a single click.

---

### 2.7 Models & Adaptive Learning (`/models-learning`)
*Continuous Model Governance*
- **Human Ground Truth Feedback**: Analysts can confirm or correct model classifications, submitting verified labels to the active training buffer.
- **Statistical Drift Detection**: Population Stability Index (PSI) tracking changes in feature distributions (`flow_pkts_s`, `bwd_iat_mean`).
- **Champion vs Challenger Retraining**: Controlled pipeline triggering retraining, evaluating candidate models, and enforcing promotion gates based on F1-score superiority.

---

### 2.8 Compliance Reports & Audit Trail (`/reports-audit`)
*Audit-Ready Governance*
- **7-Day & 30-Day Executive Reports**: System uptime %, incident resolution metrics, attack distribution charts.
- **Immutable Audit Trail**: Chronological log of every user login, countermeasure approval, and model retraining event.
- **Export Options**: One-click download of audit logs in JSON or CSV format for management review.

