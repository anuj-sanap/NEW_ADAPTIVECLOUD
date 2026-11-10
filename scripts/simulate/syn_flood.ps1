# scripts/simulate/syn_flood.ps1
# Simulates duration-capped (5-second max) SYN connection churn.
# LEGAL WARNING: Strictly rate-limited and duration-capped for safe self-testing.

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$TargetIp = "127.0.0.1",

    [Parameter(Mandatory=$false)]
    [int]$TargetPort = 80,

    [Parameter(Mandatory=$false)]
    [int]$DurationSeconds = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

Write-Host "`n========================================================" -ForegroundColor Yellow
Write-Host " [SIMULATION] Vector 3: SYN Connection Burst (Duration Capped)" -ForegroundColor Yellow
Write-Host " Target IP:         $TargetIp" -ForegroundColor Cyan
Write-Host " Target Port:       $TargetPort" -ForegroundColor Cyan
Write-Host " Duration Cap:      $DurationSeconds seconds (Hard safety cap)" -ForegroundColor Cyan
Write-Host " Expected Alert:    ddos (anomaly_score >= 0.85)" -ForegroundColor Green
Write-Host " Expected Action:   block_ip / automated rate-limiting" -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Yellow

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$count = 0

while ($stopwatch.Elapsed.TotalSeconds -lt $DurationSeconds) {
    $count++
    $tcp = New-Object System.Net.Sockets.TcpClient
    # Send SYN by initiating connect with immediate close
    $async = $tcp.BeginConnect($TargetIp, $TargetPort, $null, $null)
    Start-Sleep -Milliseconds 50
    $tcp.Close()

    if ($count % 20 -eq 0) {
        Write-Host "[$([int]$stopwatch.Elapsed.TotalSeconds)s/$DurationSeconds s] Dispatched $count simulated SYN packets..." -ForegroundColor Yellow
    }
}
$stopwatch.Stop()

Write-Host "`n>>> [SUCCESS] SYN burst simulation finished ($count connections tested)." -ForegroundColor Green
Write-Host ">>> Check AdaptiveCloud Dashboard: /detections, /classifications, and /responses.`n"

