# scripts/gcp_create_worker.ps1
# Automates provisioning of a Windows Server 2022 Worker VM on Google Cloud Platform
# Enforces IP-restricted RDP firewall rules and configures administrator credentials.

[CmdletBinding()]
param(
    [string]$Project = $(gcloud config get-value project 2>$null),
    [string]$Zone = "us-central1-a",
    [string]$InstanceName = "win-worker-01",
    [string]$MachineType = "e2-medium",
    [int]$DiskSizeGb = 50,
    [string]$AdminUser = "admin_analyst"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step { param([string]$msg) Write-Host "`n>>> [GCP Worker Setup] $msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "  [WARN] $msg" -ForegroundColor Yellow }

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AdaptiveCloud GCP Windows Server 2022 Provisioner       " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Preflight checks
Write-Step "Checking gcloud SDK installation and active configuration..."
$gcloud = Get-Command gcloud -ErrorAction SilentlyContinue
if (-not $gcloud) {
    Write-Host "Error: gcloud CLI not found. Install from https://cloud.google.com/sdk/docs/install" -ForegroundColor Red
    exit 1
}

if (-not $Project -or $Project -eq "(unset)") {
    Write-Host "Error: No active GCP project set. Run 'gcloud config set project <PROJECT_ID>'." -ForegroundColor Red
    exit 1
}
Write-OK "Using Project: $Project in Zone: $Zone"

# 2. Restrictive Firewall Rule based on Developer Public IP
Write-Step "Detecting developer public IP address..."
try {
    $myIp = (Invoke-RestMethod -Uri "https://api.ipify.org" -TimeoutSec 10).Trim()
    Write-OK "Detected public IP: $myIp"
} catch {
    Write-Host "Failed to query public IP from ipify. Fallback to ifconfig.me..." -ForegroundColor Yellow
    $myIp = (Invoke-RestMethod -Uri "https://ifconfig.me" -TimeoutSec 10).Trim()
    Write-OK "Detected public IP: $myIp"
}

Write-Step "Configuring VPC firewall rule for RDP (port 3389)..."
$existingFw = gcloud compute firewall-rules list --filter="name=allow-rdp-my-ip-only" --format="value(name)" 2>$null
if ($existingFw) {
    Write-OK "Updating existing firewall rule 'allow-rdp-my-ip-only' with current IP..."
    gcloud compute firewall-rules update allow-rdp-my-ip-only `
        --project=$Project `
        --source-ranges="$myIp/32" `
        --rules=tcp:3389
} else {
    Write-OK "Creating firewall rule 'allow-rdp-my-ip-only' allowing $myIp/32..."
    gcloud compute firewall-rules create allow-rdp-my-ip-only `
        --project=$Project `
        --direction=INGRESS `
        --priority=1000 `
        --network=default `
        --action=ALLOW `
        --rules=tcp:3389 `
        --source-ranges="$myIp/32" `
        --target-tags=windows-worker `
        --description="RDP access restricted exclusively to developer workstation"
}

# 3. Create Windows Server 2022 VM
Write-Step "Checking if instance '$InstanceName' already exists..."
$instanceExists = gcloud compute instances list --filter="name=$InstanceName" --format="value(name)" 2>$null

if ($instanceExists) {
    Write-Warn "Instance '$InstanceName' already exists."
    $status = gcloud compute instances describe $InstanceName --zone=$Zone --format="value(status)"
    Write-OK "Current status: $status"
    if ($status -eq "TERMINATED") {
        Write-Step "Starting existing stopped VM..."
        gcloud compute instances start $InstanceName --zone=$Zone
    }
} else {
    Write-Step "Deploying Windows Server 2022 Datacenter ($MachineType, $DiskSizeGb GB)..."
    Write-Warn "NOTE: Windows Server carries licensing fees deducted from your trial credit."
    
    gcloud compute instances create $InstanceName `
        --project=$Project `
        --zone=$Zone `
        --machine-type=$MachineType `
        --image-family=windows-2022 `
        --image-project=windows-cloud `
        --boot-disk-size="$($DiskSizeGb)GB" `
        --boot-disk-type=pd-standard `
        --tags=windows-worker `
        --metadata=enable-oslogin=FALSE
}

# 4. Fetch Public IP
Write-Step "Retrieving VM external IP address..."
$workerIp = gcloud compute instances describe $InstanceName --zone=$Zone --format="value(networkInterfaces[0].accessConfigs[0].natIP)"
Write-OK "Instance External IP: $workerIp"

# 5. Reset / Generate Windows credentials
Write-Step "Provisioning administrator credentials via Windows Guest Agent..."
Write-Host "Waiting 30 seconds for guest OS services to stabilize..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-OK "Generating password for user '$AdminUser'..."
$credOutput = gcloud compute reset-windows-password $InstanceName --zone=$Zone --user=$AdminUser --quiet

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  Worker VM Provisioned Successfully!                      " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host $credOutput -ForegroundColor Yellow
Write-Host "`nConnect via Microsoft Remote Desktop:" -ForegroundColor Cyan
Write-Host "  mstsc /v:$workerIp`n" -ForegroundColor White
Write-Host "To stop instance and halt trial credit deductions:" -ForegroundColor Yellow
Write-Host "  gcloud compute instances stop $InstanceName --zone=$Zone`n" -ForegroundColor Gray
