# AdaptiveCloud Troubleshooting & Diagnostic Guide

This operational guide details diagnosis and remediation procedures for common failure modes encountered across the AdaptiveCloud stack on Windows and Google Cloud.

---

## 1. Diagnostic Matrix

| Issue | Root Cause | Immediate Remediation |
| :--- | :--- | :--- |
| **Backend OOM / Crash on WSL2** | WSL2 consuming default 50% RAM | Limit WSL2 RAM to 6GB via `%USERPROFILE%\.wslconfig` |
| **Alembic Migration Hangs** | Database lock on `alembic_version` | Terminate idle connections in Postgres: `pg_terminate_backend` |
| **Agent Ingestion Returns 401** | `X-API-Key` mismatch or revoked agent | Verify `AGENT_API_KEY` in `.env` matches agent `config.yaml` |
| **Npcap / Scapy Sniffer Error** | WinPcap/Npcap missing or service stopped | Reinstall Npcap with "WinPcap API-compatible mode" enabled |
| **Threat Prediction `not_available`** | Cold-start threshold (< 12 samples) | Normal behavior; inspect progress percentage in response payload |
| **Wazuh Alerts Not Ingested** | Read permissions on shared volume | Ensure `wazuh_alerts` volume mount is readable by backend container |
| **WebSocket Disconnects (`/ws/live`)** | Nginx `proxy_read_timeout` too short | Ensure Nginx config has `proxy_read_timeout 86400s;` and HTTP/1.1 |

---

## 2. Windows & WSL2 Specific Issues

### Issue 2.1: Docker Desktop / Vmmem Memory Exhaustion
**Symptoms**: Windows workstation becomes sluggish, mouse lags, or Docker containers fail with exit code 137 (OOMKilled).  
**Remedy**:
1. Create or edit `C:\Users\<YourUser>\.wslconfig`:
   ```ini
   [wsl2]
   memory=6GB
   processors=4
   swap=2GB
   localhostForwarding=true
   ```
2. Restart WSL2 from PowerShell (Admin):
   ```powershell
   wsl --shutdown
   ```
3. Relaunch Docker Desktop.

### Issue 2.2: PowerShell Execution Policy Restrictions
**Symptoms**: `File scripts/tasks.ps1 cannot be loaded because running scripts is disabled on this system.`  
**Remedy**:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### Issue 2.3: Port Conflicts on Windows (5432, 80, 443)
**Symptoms**: `Error response from daemon: Ports are not available: exposing port TCP 0.0.0.0:5432`  
**Diagnosis**:
```powershell
Get-NetTCPConnection -LocalPort 5432, 80, 443 -ErrorAction SilentlyContinue | Format-Table OwningProcess, LocalPort, State
```
**Remedy**: Stop native PostgreSQL or IIS services running locally:
```powershell
Stop-Service -Name postgresql* -ErrorAction SilentlyContinue
Stop-Service -Name W3SVC -ErrorAction SilentlyContinue
```

---

## 3. Database & Migration Troubleshooting

### Issue 3.1: Deadlocked Alembic Migrations
**Symptoms**: Running `alembic upgrade head` hangs indefinitely without printing table creations.  
**Diagnosis**:
```sql
SELECT pid, query, state, age(clock_timestamp(), query_start) 
FROM pg_stat_activity 
WHERE query ILIKE '%alembic%' OR state = 'idle in transaction';
```
**Remedy**:
Execute kill query inside PostgreSQL:
```powershell
docker exec -it adaptivecloud-postgres psql -U postgres -d adaptivecloud -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'adaptivecloud' AND pid <> pg_backend_pid();
"
```

---

## 4. Agent & Network Telemetry Issues

### Issue 4.1: Npcap Driver Binding Failure
**Symptoms**: Agent log shows `RuntimeError: Sniffing requires Npcap/WinPcap or Administrator privileges`.  
**Remedy**:
1. Check Npcap service status on the Windows worker:
   ```powershell
   Get-Service -Name npcap -ErrorAction SilentlyContinue
   ```
2. If stopped, start the driver service:
   ```powershell
   Start-Service -Name npcap
   ```
3. If packet capture is optional, verify that `agent/config.yaml` has `flows.enabled: false` to fall back purely on OS socket statistics and Windows Security Event logs.

### Issue 4.2: Tailscale Private Peering Lost
**Symptoms**: Agent cannot reach `https://100.64.0.10:443/api/v1/agents/register`.  
**Remedy**:
1. Check Tailscale ping from worker to PC:
   ```powershell
   tailscale ping 100.64.0.10
   ```
2. Verify Windows Defender Firewall on PC allows port 443 and 1514/1515 on the Tailscale interface (`Tailscale-Tunnel`):
   ```powershell
   New-NetFirewallRule -DisplayName "AdaptiveCloud Tailscale Stack" `
       -Direction Inbound -InterfaceAlias "Tailscale" `
       -Action Allow -Protocol TCP -LocalPort 443, 80, 1514, 1515, 8000
   ```

---

## 5. Machine Learning & Forecasting Diagnostics

### Issue 5.1: Cold-Start Data Notice on Threat Prediction
**Symptoms**: Dashboard shows `Prediction Unavailable: Collecting Telemetry Data: 42%`.  
**Explanation**:
The threat forecasting model uses time-series autoregression and EWMA filters. It requires a minimum of **12 time-series bins (1 hour)** of live data before computing rolling statistics.  
**Verification**:
```powershell
# Ingest synthetic training bursts to immediately populate time-series windows:
pwsh -File .\scripts\generate_training_load.ps1 -HostCount 1 -Cycles 12
```

### Issue 5.2: Feature Drift Detection Triggers Alert
**Symptoms**: Dashboard alerts `Feature Drift Detected: mean PSI > 0.25`.  
**Explanation**:
Live telemetry feature distributions have shifted significantly from the baseline dataset (CIC-IDS2017). This indicates either a novel attack pattern or network topology change.  
**Remedy**:
1. Navigate to **Models & Learning** (`/models-learning`).
2. Review drifted features (e.g. `flow_pkts_s`, `bwd_pkt_len_mean`).
3. Click **Trigger Retraining** to retrain candidate model on combined baseline + active feedback stream.
4. Review Champion vs Challenger F1-scores and promote if challenger exceeds champion.
