# scripts/gcp_teardown.ps1
# Decommission GCP Windows Worker VM and cleanup firewall rules to prevent budget leakage.

[CmdletBinding()]
param(
    [string]$Project = $(gcloud config get-value project 2>$null),
    [string]$Zone = "us-central1-a",
    [string]$InstanceName = "win-worker-01",
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step { param([string]$msg) Write-Host "`n>>> [GCP Teardown] $msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$msg) Write-Host "  [OK] $msg" -ForegroundColor Green }

Write-Host "==========================================================" -ForegroundColor Yellow
Write-Host "  AdaptiveCloud GCP Resource Teardown                     " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Yellow

if (-not $Force) {
    $confirm = Read-Host "Are you sure you want to permanently delete instance '$InstanceName' and cleanup firewall rules in project '$Project'? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "Teardown aborted." -ForegroundColor Gray
        exit 0
    }
}

# 1. Delete Instance
Write-Step "Checking for active instance '$InstanceName'..."
$instanceExists = gcloud compute instances list --filter="name=$InstanceName" --format="value(name)" 2>$null
if ($instanceExists) {
    Write-Step "Deleting instance '$InstanceName' and boot disk..."
    gcloud compute instances delete $InstanceName --zone=$Zone --quiet
    Write-OK "Instance deleted."
} else {
    Write-OK "Instance '$InstanceName' does not exist."
}

# 2. Delete Firewall Rule
Write-Step "Checking for firewall rule 'allow-rdp-my-ip-only'..."
$fwExists = gcloud compute firewall-rules list --filter="name=allow-rdp-my-ip-only" --format="value(name)" 2>$null
if ($fwExists) {
    Write-Step "Deleting firewall rule 'allow-rdp-my-ip-only'..."
    gcloud compute firewall-rules delete allow-rdp-my-ip-only --quiet
    Write-OK "Firewall rule deleted."
} else {
    Write-OK "Firewall rule does not exist."
}

Write-Host "`nTeardown complete. All billable worker resources have been removed." -ForegroundColor Green
