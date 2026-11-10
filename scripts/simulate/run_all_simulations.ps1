# scripts/simulate/run_all_simulations.ps1
# Master simulation runner for AdaptiveCloud
# Executes all 6 controlled attack vectors sequentially with safety prompts.

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$TargetIp = "127.0.0.1",

    [Parameter(Mandatory=$false)]
    [switch]$SkipConfirmation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

$SimDir = $PSScriptRoot

Write-Host @"
========================================================================
   ADAPTIVECLOUD - CONTROLLED ATTACK SIMULATION ORCHESTRATOR
   Target: $TargetIp | Mode: Defensive Telemetry Generation
========================================================================
 LEGAL REMINDER: Run ONLY against test hosts you own and control.
 Bounded durations and safe rate-limits are enforced on all vectors.
========================================================================
"@ -ForegroundColor Cyan

if (-not $SkipConfirmation) {
    $confirm = Read-Host "Proceed with executing simulation suite against $TargetIp? (y/N)"
    if ($confirm -notmatch "^[yY]") {
        Write-Host "Simulation aborted by user." -ForegroundColor Yellow
        exit 0
    }
}

$simulations = @(
    @{ Name = "Authentication Brute-Force"; Script = "ssh_bruteforce.ps1"; Args = @("-TargetIp", $TargetIp) },
    @{ Name = "Port Scan (Reconnaissance)"; Script = "port_scan.ps1"; Args = @("-TargetIp", $TargetIp) },
    @{ Name = "SYN Flood (5s Duration Cap)"; Script = "syn_flood.ps1"; Args = @("-TargetIp", $TargetIp, "-DurationSeconds", "5") },
    @{ Name = "Suspicious Process Execution"; Script = "suspicious_process.ps1"; Args = @("-HoldSeconds", "6") },
    @{ Name = "Resource Saturation & Disk Fill"; Script = "resource_stress.ps1"; Args = @("-DurationSeconds", "10") },
    @{ Name = "Service Failure & Auto-Restart"; Script = "service_failure.ps1"; Args = @() }
)

$index = 0
foreach ($sim in $simulations) {
    $index++
    Write-Host "`n--------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host ">>> Running Vector $index/6: $($sim.Name)..." -ForegroundColor Yellow
    Write-Host "--------------------------------------------------------" -ForegroundColor DarkGray
    
    $scriptPath = Join-Path $SimDir $sim.Script
    if (Test-Path $scriptPath) {
        & $scriptPath @($sim.Args)
    } else {
        Write-Host "[ERROR] Script not found: $scriptPath" -ForegroundColor Red
    }
    Start-Sleep -Seconds 2
}

Write-Host @"
========================================================================
 [COMPLETED] All 6 attack simulations dispatched successfully!
 Review AdaptiveCloud UI:
   - Live Feed:       http://localhost:5173/detections
   - Classification:  http://localhost:5173/classifications
   - Forensic RCA:    http://localhost:5173/rca
   - Response Engine: http://localhost:5173/responses
   - Maintenance:     http://localhost:5173/maintenance
========================================================================
"@ -ForegroundColor Green
