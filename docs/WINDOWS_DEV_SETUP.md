# Windows Development Environment Setup Guide

This guide covers setting up a local Windows 10/11 environment to run and develop the **AI-Based Adaptive Cloud Security and Predictive Maintenance System** with a strict ₹0 budget.

---

## 1. BIOS Virtualization & Windows Subsystem for Linux (WSL2)

### Step 1.1: Enable Hardware Virtualization in BIOS/UEFI
1. Reboot your PC and enter BIOS (typically by pressing `F2`, `F12`, `Del`, or `Esc` during startup).
2. Look for **Intel Virtualization Technology (VT-x)** or **AMD SVM (Secure Virtual Machine)**.
3. Set the state to **Enabled**, save changes, and boot back into Windows.

### Step 1.2: Enable Windows Features
Open an elevated PowerShell (Run as Administrator) and execute:
```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```
Restart your system if prompted.

### Step 1.3: Install or Update WSL2
In PowerShell:
```powershell
wsl --update
wsl --set-default-version 2
```

---

## 2. Restrict WSL2 Memory Consumption (`.wslconfig`)

By default, WSL2 can consume up to 50% or more of total system RAM, starving Windows host processes. On systems with 8 GB to 16 GB of physical RAM, you should cap WSL2 at **4 GB – 6 GB**.

Create or edit `C:\Users\<YourUsername>\.wslconfig`:
```ini
[wsl2]
# Memory cap for WSL2 VM
memory=6GB

# Limit virtual CPUs to preserve host responsiveness
processors=4

# Disable swap file growth
swap=2GB
swapfile=C:\\temp\\wsl-swap.vhdx

# Reclaim cached memory periodically
localhostForwarding=true
```

Apply changes by restarting WSL:
```powershell
wsl --shutdown
```

---

## 3. Install Docker Desktop with WSL2 Backend

1. Download [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/).
2. During installation:
   - Select **Use WSL 2 instead of Hyper-V (recommended)**.
3. Open Docker Desktop Settings:
   - **General**: Ensure "Use the WSL 2 based engine" is enabled.
   - **Resources > WSL Integration**: Enable integration with your default distribution.
   - **Docker Engine**: Leave default or ensure DNS servers are reachable (e.g. `8.8.8.8`, `1.1.1.1`).

---

## 4. Install Tooling (Python 3.11, Node.js 20, Git)

### Step 4.1: Python 3.11+
Install Python 3.11 (or 3.12/3.13) via [Python.org](https://www.python.org/downloads/) or winget:
```powershell
winget install Python.Python.3.11
```
*Crucial*: Check **"Add python.exe to PATH"** in the installer.

### Step 4.2: Node.js 20 LTS
```powershell
winget install OpenJS.NodeJS.LTS
```

### Step 4.3: Git for Windows
```powershell
winget install Git.Git
```
*Crucial*: Choose `Checkout as-is, commit Unix-style line endings` during Git setup, or rely on our project `.gitattributes`.

---

## 5. PowerShell Execution Policy & Environment

To allow execution of project PowerShell scripts (`.ps1`):
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

To verify your environment:
```powershell
python --version
node --version
docker version
git --version
```

---

## 6. Common Windows Development Pitfalls & Solutions

### Pitfall 1: Line Endings (CRLF vs LF in Container Mounts)
- **Problem**: Windows text editors automatically save files with `\r\n` (CRLF). Shell scripts, Nginx configurations, and configuration files mounted into Linux containers will crash with errors like `\r: command not found` or syntax errors.
- **Solution**: The repository has a strictly configured `.gitattributes` file that enforces `eol=lf` for `*.sh`, `*.conf`, `*.yml`, and `Dockerfile`. In VS Code, verify the status bar shows **LF** when saving container-related files.

### Pitfall 2: MAX_PATH (260 Character Path Limit)
- **Problem**: Deep nested folder hierarchies in Python venvs or `node_modules` can exceed Windows' default 260-character path limit, causing `FileNotFoundError` or git checkout errors.
- **Solution**: Enable Long Paths in Windows (Run as Admin):
```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
    -Name "LongPathsEnabled" -Value 1 -PropertyType DWORD -Force
git config --system core.longpaths true
```

### Pitfall 3: Port Conflicts (5432, 80, 443, 8000)
- **Problem**: Local services like local PostgreSQL, IIS, or Skype might hold port `5432`, `80`, or `443`.
- **Diagnosis**:
```powershell
Get-NetTCPConnection -LocalPort 5432, 80, 443, 8000 -ErrorAction SilentlyContinue | Format-Table -AutoSize
```
- **Solution**: If IIS or World Wide Web Publishing Service is holding port 80/443:
```powershell
Stop-Service W3SVC -ErrorAction SilentlyContinue
Set-Service W3SVC -StartupType Manual -ErrorAction SilentlyContinue
```

### Pitfall 4: Windows Defender Firewall Prompts
- When Docker containers or Python services bind to network ports, Windows Firewall may pop up a dialog. **Allow access for Private Networks**.
- Never allow public network access unless intentionally configuring public ingress.

---

## 7. Starting the Stack with the PowerShell Task Runner

```powershell
# 1. Generate TLS Certificates
.\scripts\tasks.ps1 certs

# 2. Boot Docker containers
.\scripts\tasks.ps1 up

# 3. Apply database migrations
.\scripts\tasks.ps1 migrate

# 4. Seed initial admin user
.\scripts\tasks.ps1 seed

# 5. Execute test suite
.\scripts\tasks.ps1 test
```

