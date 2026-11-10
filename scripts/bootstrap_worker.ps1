# scripts/bootstrap_worker.ps1
# Provisioning script for Windows Server 2022 worker node.
# Must be executed as Administrator on the GCP Windows VM.

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)]
    [string]$ControlServerTailscaleIp,

    [string]$AgentApiKey = "adm-agent-live-insecure-dev-key-change-in-production",
    [switch]$InstallNpcap = $false,
    [string]$InstallDir = "C:\AdaptiveCloud"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Verify Elevated Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Error: This script must be run as Administrator." -ForegroundColor Red
    exit 1
}

function Write-Step { param([string]$msg) Write-Host "`n>>> [Worker Bootstrap] $msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "  [WARN] $msg" -ForegroundColor Yellow }

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AdaptiveCloud Windows Server Worker Bootstrap Script     " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# ── 1. Enable Advanced Security Auditing (auditpol & registry) ────────────────
Write-Step "Configuring Windows Advanced Audit Policies..."

# Logon / Logoff -> Audit Logon (Events 4624 success, 4625 failure)
auditpol /set /subcategory:"Logon" /success:enable /failure:enable
Write-OK "Auditing enabled for Logon events (4624 / 4625)."

# Detailed Tracking -> Process Creation (Event 4688)
auditpol /set /subcategory:"Process Creation" /success:enable /failure:enable
Write-OK "Auditing enabled for Process Creation (4688)."

# Account Management -> User Account Management (Event 4720 user created)
auditpol /set /subcategory:"User Account Management" /success:enable /failure:enable
Write-OK "Auditing enabled for User Account Management (4720)."

# Privilege Use -> Sensitive Privilege Use (Event 4672 admin logon)
auditpol /set /subcategory:"Sensitive Privilege Use" /success:enable /failure:enable
Write-OK "Auditing enabled for Sensitive Privilege Use (4672)."

# Enable full command-line capture in Event 4688 via Group Policy Registry
$auditRegPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System\Audit"
if (-not (Test-Path $auditRegPath)) {
    New-Item -Path $auditRegPath -Force | Out-Null
}
Set-ItemProperty -Path $auditRegPath -Name "ProcessCreationIncludeCmdLine_Enabled" -Value 1 -Type DWord
Write-OK "Command line auditing enabled in Process Creation events."

# ── 2. Install Python 3.11 ───────────────────────────────────────────────────
Write-Step "Checking for Python 3.11+..."
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    Write-Step "Downloading Python 3.11 installer..."
    $pyUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $pyInstaller = "$env:TEMP\python-3.11.9.exe"
    Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller
    
    Write-Step "Installing Python 3.11 with PATH integration..."
    Start-Process -FilePath $pyInstaller -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0" -Wait
    Remove-Item $pyInstaller -Force
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-OK "Python 3.11 installed successfully."
} else {
    Write-OK "Python detected: $(python --version)"
}

# ── 3. (Optional) Install Npcap for Network Flow Capture ─────────────────────
if ($InstallNpcap) {
    Write-Step "Downloading and installing Npcap for raw packet capture..."
    $npcapUrl = "https://npcap.com/dist/npcap-1.79.exe"
    $npcapInstaller = "$env:TEMP\npcap-installer.exe"
    try {
        Invoke-WebRequest -Uri $npcapUrl -OutFile $npcapInstaller
        Start-Process -FilePath $npcapInstaller -ArgumentList "/S /winpcap_mode=yes" -Wait
        Remove-Item $npcapInstaller -Force
        Write-OK "Npcap installed."
    } catch {
        Write-Warn "Npcap install failed or required manual acceptance. Packet flow module will operate in socket mode."
    }
}

# ── 4. Install & Configure Wazuh Agent ────────────────────────────────────────
Write-Step "Installing Wazuh Windows Agent pointing to $ControlServerTailscaleIp..."
$wazuhMsiUrl = "https://packages.wazuh.com/4.x/windows/wazuh-agent-4.9.2-1.msi"
$wazuhMsi = "$env:TEMP\wazuh-agent.msi"
Invoke-WebRequest -Uri $wazuhMsi -OutFile $wazuhMsi

$msiArgs = "/i `"$wazuhMsi`" /q WAZUH_MANAGER=`"$ControlServerTailscaleIp`" WAZUH_REGISTRATION_SERVER=`"$ControlServerTailscaleIp`""
Start-Process "msiexec.exe" -ArgumentList $msiArgs -Wait
Remove-Item $wazuhMsi -Force

Start-Service -Name "Wazuh" -ErrorAction SilentlyContinue
Write-OK "Wazuh Agent installed and service started."

# ── 5. Set up AdaptiveCloud Agent Workspace ──────────────────────────────────
Write-Step "Setting up AdaptiveCloud Agent in $InstallDir..."
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
}

# Copy agent codebase if present locally, or create base config
$configPath = Join-Path $InstallDir "config.yaml"
$configContent = @"
agent:
  hostname: "$($env:COMPUTERNAME)"
  server_url: "https://$ControlServerTailscaleIp"
  api_key: "$AgentApiKey"
  verify_ssl: false
  poll_interval_sec: 10
  flow_capture_enabled: $InstallNpcap
"@
Set-Content -Path $configPath -Value $configContent -Encoding UTF8
Write-OK "Agent configuration saved to $configPath."

# ── 6. Register Agent Service with NSSM ───────────────────────────────────────
Write-Step "Configuring Windows Service..."
$nssmZip = "$env:TEMP\nssm.zip"
$nssmExe = "$env:TEMP\nssm-2.24\win64\nssm.exe"
if (-not (Test-Path $nssmExe)) {
    Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile $nssmZip
    Expand-Archive -Path $nssmZip -DestinationPath "$env:TEMP" -Force
    Remove-Item $nssmZip -Force
}

$serviceName = "AdaptiveCloudAgent"
$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if (-not $existingService) {
    $pythonExe = (Get-Command python).Source
    $agentScript = Join-Path $InstallDir "agent.py"
    
    & $nssmExe install $serviceName "$pythonExe" "$agentScript"
    & $nssmExe set $serviceName AppDirectory "$InstallDir"
    & $nssmExe set $serviceName AppRestartDelay 5000
    & $nssmExe set $serviceName Description "AdaptiveCloud Telemetry and Security Monitoring Agent"
    Write-OK "Registered service '$serviceName' with auto-restart."
} else {
    Write-OK "Service '$serviceName' already registered."
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  Worker Bootstrap Complete!                               " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
