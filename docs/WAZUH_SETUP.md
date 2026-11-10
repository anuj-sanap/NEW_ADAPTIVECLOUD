# Wazuh 4.x SIEM Setup & Tailscale Worker Enrollment

This guide details how to run the single-node Wazuh Manager in Docker on your Windows development PC, enroll Windows Server 2022 cloud workers securely over Tailscale, and stream normalized alerts into AdaptiveCloud.

---

## 1. Architecture & Memory Optimization

To honor the **strict ₹0 budget** and keep Docker Desktop RAM usage low on an 8–16 GB PC:
- **No Heavy Indexer/Dashboard**: Standard Wazuh deployments require OpenSearch/Indexer (4+ GB RAM). AdaptiveCloud runs **only** the `wazuh-manager` daemon (`~1.5 GB RAM`), relying on `alerts.json` for event streaming.
- **Shared Alerts Volume**: The manager writes alerts to `/var/ossec/logs/alerts/alerts.json`. This directory is mounted into the `backend` container as a shared volume (`wazuh_alerts`).
- **Private Mesh Connectivity**: The manager exposes agent ports `1514` (event reporting) and `1515` (agent enrollment) on your PC's private Tailscale IP. No ports are opened to the public Internet.

---

## 2. Prerequisites

1. **Tailscale Connected**: Both your Windows PC and the GCP Windows Server 2022 worker must be connected to your Tailscale tailnet.
   - Run on your PC:
     ```powershell
     tailscale ip -4
     ```
     Note your PC's 100.x.y.z IP address (referred to below as `$PC_TAILSCALE_IP`).
2. **Windows Defender Firewall on PC**:
   Allow inbound traffic on ports 1514 and 1515 exclusively on the Tailscale network interface:
   ```powershell
   New-NetFirewallRule -DisplayName "Wazuh Agent Ports (Tailscale Only)" `
     -Direction Inbound -InterfaceAlias "Tailscale" -Action Allow `
     -Protocol TCP -LocalPort 1514,1515
   New-NetFirewallRule -DisplayName "Wazuh Agent UDP (Tailscale Only)" `
     -Direction Inbound -InterfaceAlias "Tailscale" -Action Allow `
     -Protocol UDP -LocalPort 1514
   ```

---

## 3. Starting Wazuh Manager in Docker

From your PC repository root:

```powershell
# Start all core services including Wazuh manager
.\scripts\tasks.ps1 up
```

Verify that the `adaptivecloud-wazuh` container is running healthy:
```powershell
docker ps --filter "name=adaptivecloud-wazuh"
```

Verify that `local_rules.xml` is mounted:
```powershell
docker exec adaptivecloud-wazuh /var/ossec/bin/wazuh-control status
```

---

## 4. Enrolling the Windows Cloud Worker

### Automated Enrollment (Recommended)
When running `scripts/bootstrap_worker.ps1` as Administrator on the worker, provide your PC's Tailscale IP:
```powershell
.\scripts\bootstrap_worker.ps1 -ControlServerIp "100.x.y.z" -ManagerIp "100.x.y.z" -Hostname "gcp-worker-01"
```

### Manual Enrollment Steps (Step-by-Step)
Log in to the Windows Server 2022 worker via RDP:

1. **Download the Official Wazuh Agent MSI (v4.9.2)**:
   ```powershell
   $msiUrl = "https://packages.wazuh.com/4.x/windows/wazuh-agent-4.9.2-1.msi"
   Invoke-WebRequest -Uri $msiUrl -OutFile "$env:TEMP\wazuh-agent.msi"
   ```

2. **Install and Register with Manager**:
   Replace `100.x.y.z` with your PC's Tailscale IP:
   ```powershell
   $ManagerIp = "100.x.y.z"
   $AgentName = $env:COMPUTERNAME

   Start-Process msiexec.exe -ArgumentList `
     "/i `"$env:TEMP\wazuh-agent.msi`" WAZUH_MANAGER=`"$ManagerIp`" WAZUH_REGISTRATION_SERVER=`"$ManagerIp`" WAZUH_AGENT_NAME=`"$AgentName`" /q" `
     -Wait
   ```

3. **Configure Windows Event Auditing (`auditpol`)**:
   Ensure Windows records logon attempts and process executions:
   ```powershell
   # Logon and Logoff audit
   auditpol /set /subcategory:"Logon" /success:enable /failure:enable
   auditpol /set /subcategory:"Special Logon" /success:enable /failure:enable
   auditpol /set /subcategory:"User Account Management" /success:enable /failure:enable

   # Detailed process creation with full command line
   auditpol /set /subcategory:"Process Creation" /success:enable /failure:enable
   reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\Audit" `
     /v ProcessCreationIncludeCmdLine_Enabled /t REG_DWORD /d 1 /f
   ```

4. **Start the Wazuh Agent Service**:
   ```powershell
   Start-Service -Name "WazuhSvc"
   Get-Service -Name "WazuhSvc"
   ```

---

## 5. Local Security Rules (`deploy/wazuh/local_rules.xml`)

AdaptiveCloud supplies custom rules for monitored Windows endpoints:

| Rule ID | Level | Event ID | Attack Label | Description |
|---|---|---|---|---|
| **100001** | 10 | 4625 | `brute_force` | Multiple failed logons (>=5 in 60s) from same source IP |
| **100002** | 8 | 4672 | `unauthorized_access` | Sensitive privilege assigned to new logon session |
| **100003** | 9 | 4720 | `unauthorized_access` | New local user account created |
| **100004** | 10 | 4688 | `suspicious_process` | Process launched from `%TEMP%`, `Downloads`, or encoded PowerShell |
| **100005** | 8 | 5156/5157 | `port_scan` | Inbound connection attempt burst (Windows Filtering Platform) |

---

## 6. Real-Time Ingestion & WebSocket Verification

1. When an alert fires on the worker, the Wazuh agent transmits the encrypted payload over port 1514 to the manager on your PC.
2. The manager writes the normalized alert to `/var/ossec/logs/alerts/alerts.json`.
3. `backend/app/services/wazuh_ingestor.py` tails `alerts.json`, normalizes the alert to a `SecurityEvent` record in PostgreSQL, and broadcasts:
   ```json
   {
     "type": "event.new",
     "channel": "detections",
     "ts": "2026-11-10T14:00:00Z",
     "data": {
       "host_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
       "source": "wazuh",
       "rule_id": "100001",
       "level": 10,
       "category": "brute_force",
       "src_ip": "100.64.0.2",
       "user": "Administrator"
     }
   }
   ```
4. Querying the live API:
   ```powershell
   $token = (Invoke-RestMethod -Method Post "https://localhost/api/v1/auth/login" `
     -Body (@{username="admin"; password="password"} | ConvertTo-Json) `
     -ContentType "application/json" -SkipCertificateCheck).access_token

   Invoke-RestMethod -Method Get "https://localhost/api/v1/events?category=brute_force" `
     -Headers @{Authorization="Bearer $token"} -SkipCertificateCheck
   ```
