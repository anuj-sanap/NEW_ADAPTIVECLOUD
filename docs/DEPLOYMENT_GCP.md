# Google Cloud Platform (GCP) Production Deployment Guide

## 1. Executive Summary & Topology

AdaptiveCloud is architected as a hybrid, zero-cost cloud security system combining:
1. **Control Plane (On-Premises / Windows Dev PC)**: Runs PostgreSQL 16, FastAPI Backend, React SPA, and Wazuh Manager inside hardened Docker Linux containers on WSL2.
2. **Data Plane (Google Cloud Platform)**: Monitored cloud worker nodes running **Windows Server 2022 Datacenter** on Compute Engine.
3. **Private Encrypted Mesh (Tailscale)**: Private WireGuard overlay network bridging PC and GCP worker VMs without exposing internal API, database, or Wazuh ports to the public internet.

```
+-----------------------------------------------------------------------------------------+
|                                    TAILSCALE MESH                                       |
|                                                                                         |
|   +------------------------------------+       +------------------------------------+   |
|   |   DEVELOPER PC (Control Stack)     |       |     GCP WORKER VM (Data Plane)     |   |
|   |   IP: 100.64.0.10                  |       |     IP: 100.64.0.50                |   |
|   |                                    |       |                                    |   |
|   |   - Nginx Reverse Proxy (:443)     |<======|==== - AdaptiveCloud Windows Agent  |   |
|   |   - FastAPI Backend API (:8000)    |   TLS |       (Metrics, Events, Flows)     |   |
|   |   - PostgreSQL 16 (:5432)          |       |     - Wazuh Agent MSI              |   |
|   |   - Wazuh Manager (:1514, :1515)   |<======|==== - Windows Defender Firewall    |   |
|   |   - React 18 SPA Frontend (:80)    | Wazuh |       (Automated Netsh Rules)      |   |
|   +------------------------------------+       +------------------------------------+   |
|                                           ▲                                             |
|                                           | Private Overlay Tunnel                      |
+-------------------------------------------|---------------------------------------------+
                                            |
                              Public Internet (BLOCKED)
                     GCP Firewall: 3389 RDP allowed ONLY
                      from Developer's Static Public IP
```

---

## 2. Strict ₹0 Budget & Credit Safety Controls

> [!WARNING]
> Google Cloud Free Trial provides $300 in credit. Compute Engine's "Always Free" tier (`e2-micro`) applies **only to Linux OS images**, NOT Windows Server. Windows Server Datacenter carries an hourly OS licensing fee charged against your trial credit.

### Mandatory Cost-Saving Rules:
1. **Always STOP the VM after testing**:
   ```powershell
   .\scripts\gcp_teardown.ps1
   ```
2. **Never leave the VM running overnight or unmonitored**. A stopped VM incurs only fractional persistent disk charges (~₹15/month for 50 GB standard PD).
3. **Set Up an Immediate GCP Budget Alert**:
   - Go to **GCP Console** -> **Billing** -> **Budgets & alerts**.
   - Create budget named `AdaptiveCloud-Zero-Budget`.
   - Target amount: **₹100** (or **$1.00**).
   - Set alert thresholds at **50%**, **90%**, and **100%** with email notifications.

---

## 3. Step 0: Prerequisites on Windows PC

Ensure the following tools are installed on your Windows workstation:
1. **Google Cloud SDK (`gcloud`)**:
   ```powershell
   winget install Google.CloudSDK
   gcloud init
   gcloud auth login
   ```
2. **Tailscale**:
   ```powershell
   winget install Tailscale.Tailscale
   tailscale up
   ```
3. **Docker Desktop** (with WSL2 engine enabled).
4. **PowerShell 7 (`pwsh`)** with unrestricted script execution for the project:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
   ```

---

## 4. Step 1: Deploying the GCP Windows Server 2022 Worker VM

Run the automated provisioning script from the repository root:

```powershell
pwsh -File .\scripts\gcp_create_worker.ps1 `
    -ProjectId "your-gcp-project-id" `
    -Zone "us-central1-a" `
    -MachineType "e2-medium" `
    -DiskSizeGb 50
```

### What this script automates:
1. **Detects your public IP**: Queries `https://api.ipify.org` and configures a GCP VPC Firewall Rule (`allow-rdp-my-ip`) permitting inbound TCP port 3389 **only** from your exact IP address. All other internet traffic is dropped.
2. **Provisions the VM**:
   - Image: `windows-cloud/windows-server-2022-dc-v20240410`
   - Boot Disk: 50 GB Standard Persistent Disk (`pd-standard`)
   - Tags: `adaptivecloud-worker`
3. **Resets Administrative Password**: Securely generates Windows credentials using `gcloud compute reset-windows-password`.

---

## 5. Step 2: Worker Node Bootstrap & Agent Registration

1. **RDP into the worker VM**:
   ```powershell
   mstsc.exe /v:<Worker-External-IP>
   ```
2. Open PowerShell as Administrator on the worker and run the bootstrap script:
   ```powershell
   # Copy scripts/bootstrap_worker.ps1 to the worker or run:
   powershell.exe -ExecutionPolicy Bypass -File .\bootstrap_worker.ps1 `
       -ControlServerHost "100.64.0.10" `
       -WazuhManagerHost "100.64.0.10" `
       -AgentApiKey "your-production-agent-key"
   ```

### What the bootstrap script executes:
- **Enables Enhanced Windows Security Auditing**:
  ```powershell
  auditpol /set /subcategory:"Logon" /success:enable /failure:enable
  auditpol /set /subcategory:"Process Creation" /success:enable /failure:enable
  reg add "HKLM\Software\Microsoft\Windows\CurrentVersion\Policies\System\Audit" /v ProcessCreationIncludeCmdLine_Enabled /t REG_DWORD /d 1 /f
  ```
- **Installs Python 3.11** silently via `winget` or direct MSI.
- **Installs Wazuh Agent MSI**: Points registration to the PC's Tailscale IP (`100.64.0.10:1515`).
- **Installs AdaptiveCloud Windows Monitoring Agent as a Windows Service**: Monitors CPU, memory, disk, network flows (WinPcap/Npcap), and Security Events (4624/4625/4688).

---

## 6. Step 3: Launching the Production Control Stack on PC

1. **Configure Environment Secrets**:
   Ensure `.env` contains strong production secrets:
   ```env
   ENVIRONMENT=production
   DEBUG=false
   DOMAIN=100.64.0.10
   POSTGRES_PASSWORD=your_strong_postgres_password_here
   JWT_SECRET=your_minimum_32_character_jwt_secret_token_here
   AGENT_API_KEY=your_production_agent_api_key_here
   ```
2. **Provision TLS Certificates**:
   ```powershell
   pwsh -File .\deploy\setup_ssl.ps1 -SelfSigned
   ```
3. **Launch Docker Stack**:
   ```powershell
   docker compose -f .\deploy\docker-compose.prod.yml up -d --build
   ```
4. **Run Database Migrations & Seed Admin**:
   ```powershell
   docker exec -i adaptivecloud-backend-prod alembic upgrade head
   docker exec -i adaptivecloud-backend-prod python scripts/create_admin.py --username admin --password "StrongAdminPass123!"
   ```

---

## 7. Step 4: Verification & Smoke Test

1. Access Dashboard: Open `https://100.64.0.10` in your browser.
2. Login with `admin` and `StrongAdminPass123!`.
3. Verify worker is listed under **System Monitoring** (`/monitoring`) with status `ONLINE`.
4. Run the end-to-end integration verification suite:
   ```powershell
   pwsh -File .\scripts\tasks.ps1 -Task e2e
   ```

---

## 8. Step 5: Tearing Down to Protect Free Credits

When testing is concluded:

```powershell
# Stop the GCP VM (halts Compute Engine and Windows licensing billing)
pwsh -File .\scripts\gcp_teardown.ps1 -ProjectId "your-gcp-project-id" -InstanceName "adaptivecloud-worker-01"

# Stop the local Docker Compose stack
docker compose -f .\deploy\docker-compose.prod.yml down
```
