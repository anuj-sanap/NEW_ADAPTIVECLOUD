# Tailscale Encrypted Mesh Network Setup

This document explains how to connect your local development workstation (running Docker Compose) and your GCP Windows Server 2022 workers into a private, encrypted WireGuard mesh network using **Tailscale** at ₹0 cost.

---

## 1. Why Tailscale?

- **Zero Public Port Exposure**: The FastAPI backend, PostgreSQL, and Wazuh manager do **not** need public IPs or port forwarding.
- **Stable Private Addressing**: Every machine receives a permanent internal IP in the `100.64.0.0/10` CGNAT range (e.g. `100.x.y.z`), eliminating external IP churn when GCP VMs stop and start.
- **End-to-End Encryption**: Automated WireGuard tunnel handling with hardware-accelerated encryption.
- **₹0 Budget**: Free tier includes 1 user and up to 100 devices.

---

## 2. Installation & Configuration on Developer Workstation (PC)

### Step 2.1: Install Tailscale
In PowerShell:
```powershell
winget install Tailscale.Tailscale
```
Or download the installer from [Tailscale Windows Download](https://tailscale.com/download/windows).

### Step 2.2: Authenticate and Connect
1. Click the Tailscale icon in the system tray and select **Log In**.
2. Complete authorization via your browser.
3. Retrieve your PC's assigned Tailscale IP address:
```powershell
tailscale ip -4
```
*Example Output*: `100.85.120.45` (referred to as `$CONTROL_PC_TAILSCALE_IP`).

### Step 2.3: Restrict Windows Defender Firewall to Tailscale Interface
To ensure backend HTTPS (443) and Wazuh ports (1514, 1515) are strictly accessible to your Tailscale mesh and blocked from local LAN or public adapters, run in elevated PowerShell:

```powershell
# 1. Identify the Tailscale Network Interface Alias
$tsInterface = Get-NetAdapter | Where-Object { $_.InterfaceDescription -like "*Tailscale*" } | Select-Object -ExpandProperty Name
Write-Host "Tailscale Interface: $tsInterface" -ForegroundColor Green

# 2. Allow HTTPS (443) strictly on Tailscale interface
New-NetFirewallRule -DisplayName "AdaptiveCloud - Tailscale Inbound HTTPS" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 443 `
    -InterfaceAlias $tsInterface `
    -Description "Allows cloud workers to communicate with FastAPI reverse proxy"

# 3. Allow Wazuh Agent Reporting (1514 UDP/TCP) strictly on Tailscale
New-NetFirewallRule -DisplayName "AdaptiveCloud - Tailscale Wazuh Events (1514)" `
    -Direction Inbound `
    -Action Allow `
    -Protocol UDP `
    -LocalPort 1514 `
    -InterfaceAlias $tsInterface

# 4. Allow Wazuh Agent Registration (1515 TCP) strictly on Tailscale
New-NetFirewallRule -DisplayName "AdaptiveCloud - Tailscale Wazuh Enrollment (1515)" `
    -Direction Inbound `
    -Action Allow `
    -Protocol TCP `
    -LocalPort 1515 `
    -InterfaceAlias $tsInterface
```

---

## 3. Installation on GCP Windows Server 2022 Worker

Connect to your worker VM via RDP, open PowerShell as **Administrator**, and run:

### Step 3.1: Download & Install Tailscale
```powershell
$installerUrl = "https://pkgs.tailscale.com/stable/tailscale-setup-latest.exe"
$destPath = "$env:TEMP\tailscale-setup.exe"
Invoke-WebRequest -Uri $installerUrl -OutFile $destPath
Start-Process -FilePath $destPath -ArgumentList "/quiet" -Wait
Remove-Item $destPath -Force
```

### Step 3.2: Log in using an Auth Key (Headless / Automated)
Generate a reusable, pre-authenticated auth key in the [Tailscale Admin Console](https://login.tailscale.com/admin/settings/keys):
```powershell
& "C:\Program Files\Tailscale\tailscale.exe" up --auth-key="tskey-auth-kXXXXX-XXXXXX" --hostname="gcp-win-worker-01"
```

Verify connectivity by pinging your developer PC's Tailscale IP:
```powershell
ping 100.85.120.45
```

---

## 4. Binding Services in Docker Compose

With Tailscale active, your developer PC can expose port 443 and 1514 directly on its Tailscale IP address.

In `deploy/docker-compose.yml`:
```yaml
nginx:
  ports:
    - "100.85.120.45:443:443"  # Binds only to Tailscale interface!
    - "127.0.0.1:443:443"      # Local browser access
```
The cloud worker agents will communicate with `https://100.85.120.45/api/v1/agents/...`.

