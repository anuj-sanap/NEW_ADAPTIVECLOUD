<#
.SYNOPSIS
    Generates controlled benign and test load on local or worker Windows machines.
.DESCRIPTION
    Creates genuine, observable telemetry for testing the AdaptiveCloud monitoring agent,
    threat forecasting, and predictive maintenance engines.
    SAFETY: Strictly targets local host or specified worker VM. Never touches unauthorized systems.
.PARAMETER Mode
    Workload profile to simulate: 'all', 'cpu', 'memory', 'disk', 'network', 'auth'
.PARAMETER DurationSeconds
    Duration of the workload in seconds (default: 30)
.PARAMETER TargetHost
    Target address for benign network pings (default: 127.0.0.1)
.EXAMPLE
    .\scripts\generate_training_load.ps1 -Mode cpu -DurationSeconds 15
    .\scripts\generate_training_load.ps1 -Mode all -DurationSeconds 20
#>

[CmdletBinding()]
param(
    [ValidateSet("all", "cpu", "memory", "disk", "network", "auth")]
    [string]$Mode = "all",

    [int]$DurationSeconds = 30,

    [string]$TargetHost = "127.0.0.1"
)

$ErrorActionPreference = "Continue"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   AdaptiveCloud Telemetry & Training Load Generator        " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Target: $TargetHost | Mode: $Mode | Duration: ${DurationSeconds}s" -ForegroundColor Yellow
Write-Host "[SAFETY GUARANTEE] This script operates strictly on local test resources." -ForegroundColor Green
Write-Host ""

function Start-CpuStress([int]$Seconds) {
    Write-Host "[+] Generating controlled CPU load for $Seconds seconds..." -ForegroundColor DarkYellow
    $endTime = (Get-Date).AddSeconds($Seconds)
    $cores = [System.Environment]::ProcessorCount
    $jobs = @()
    
    # Run small mathematical loops in background jobs to create observable CPU spike
    1..[Math]::Min($cores, 2) | ForEach-Object {
        $jobs += Start-Job -ScriptBlock {
            param($deadline)
            while ((Get-Date) -lt $deadline) {
                $null = [Math]::Sqrt([Math]::Sin(42.5) * [Math]::Cos(84.2))
            }
        } -ArgumentList $endTime
    }
    
    $jobs | Wait-Job -Timeout ($Seconds + 5) | Out-Null
    $jobs | Remove-Job -Force | Out-Null
    Write-Host "  [OK] CPU stress cycle complete." -ForegroundColor Green
}

function Start-MemoryStress([int]$Seconds) {
    Write-Host "[+] Allocating controlled memory buffer (approx 200MB) for $Seconds seconds..." -ForegroundColor DarkYellow
    try {
        # Allocate 200MB byte array
        $buffer = New-Object byte[] (200 * 1024 * 1024)
        for ($i = 0; $i -lt $buffer.Length; $i += 4096) {
            $buffer[$i] = 1
        }
        Start-Sleep -Seconds $Seconds
        $buffer = $null
        [System.GC]::Collect()
        Write-Host "  [OK] Memory stress released and GC completed." -ForegroundColor Green
    }
    catch {
        Write-Warning "Memory stress error: $_"
    }
}

function Start-DiskStress() {
    Write-Host "[+] Writing controlled temporary disk load..." -ForegroundColor DarkYellow
    $tempDir = Join-Path $env:TEMP "adaptivecloud_load_test"
    if (-not (Test-Path $tempDir)) {
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    }
    
    $filePath = Join-Path $tempDir "temp_io_benchmark.bin"
    try {
        $bytes = New-Object byte[] (25 * 1024 * 1024) # 25MB
        [System.IO.File]::WriteAllBytes($filePath, $bytes)
        Start-Sleep -Seconds 2
        Remove-Item $filePath -Force -ErrorAction SilentlyContinue
        Write-Host "  [OK] Disk write/delete cycle complete (25MB generated and pruned)." -ForegroundColor Green
    }
    finally {
        Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Start-NetworkLoad([string]$HostTarget) {
    Write-Host "[+] Executing benign network probing against $HostTarget..." -ForegroundColor DarkYellow
    1..5 | ForEach-Object {
        try {
            Test-Connection -ComputerName $HostTarget -Count 1 -Quiet | Out-Null
        }
        catch {
            # Gracefully handle ping restrictions
        }
        Start-Sleep -Milliseconds 200
    }
    Write-Host "  [OK] Benign ICMP / connectivity telemetry generated." -ForegroundColor Green
}

function Start-AuthAuditEvents() {
    Write-Host "[+] Generating observable Security Audit events (Event 4688 & local audit probes)..." -ForegroundColor DarkYellow
    # Spawn a clean, known PowerShell process that triggers Event 4688 with command line
    Start-Process powershell.exe -ArgumentList "-NoProfile -Command Write-Output 'AdaptiveCloud-Telemetry-Verification'" -Wait -NoNewWindow
    Write-Host "  [OK] Process creation telemetry registered." -ForegroundColor Green
}

# Execution router
$startTime = Get-Date

if ($Mode -eq "all" -or $Mode -eq "cpu") {
    Start-CpuStress -Seconds ([Math]::Min($DurationSeconds, 15))
}

if ($Mode -eq "all" -or $Mode -eq "memory") {
    Start-MemoryStress -Seconds ([Math]::Min($DurationSeconds, 10))
}

if ($Mode -eq "all" -or $Mode -eq "disk") {
    Start-DiskStress
}

if ($Mode -eq "all" -or $Mode -eq "network") {
    Start-NetworkLoad -HostTarget $TargetHost
}

if ($Mode -eq "all" -or $Mode -eq "auth") {
    Start-AuthAuditEvents
}

$elapsed = ((Get-Date) - $startTime).TotalSeconds
Write-Host ""
Write-Host "[SUCCESS] Telemetry load generator finished in $([Math]::Round($elapsed, 2))s." -ForegroundColor Green
Write-Host "Check agent metrics or backend API (/api/v1/metrics) to observe the recorded spikes." -ForegroundColor Cyan
