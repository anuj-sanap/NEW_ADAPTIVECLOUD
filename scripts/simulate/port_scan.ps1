# scripts/simulate/port_scan.ps1
# Simulates controlled multi-port reconnaissance scan.
# LEGAL WARNING: Run ONLY against your own authorized worker VM.

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$TargetIp = "127.0.0.1",

    [Parameter(Mandatory=$false)]
    [int[]]$Ports = @(21, 22, 80, 443, 3389, 8080, 8443)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

Write-Host "`n========================================================" -ForegroundColor Yellow
Write-Host " [SIMULATION] Vector 2: Multi-Port Scan (Reconnaissance)" -ForegroundColor Yellow
Write-Host " Target IP:      $TargetIp" -ForegroundColor Cyan
Write-Host " Ports Probed:   $($Ports -join ', ')" -ForegroundColor Cyan
Write-Host " Expected Alert: port_scan (anomaly_score >= 0.65)" -ForegroundColor Green
Write-Host " Expected Action: temporary IP blocklist entry (60 min TTL)" -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Yellow

foreach ($port in $Ports) {
    Write-Host "[SCAN] Probing TCP port $port on $TargetIp... " -NoNewline
    
    $tcp = New-Object System.Net.Sockets.TcpClient
    $async = $tcp.BeginConnect($TargetIp, $port, $null, $null)
    $ok = $async.AsyncWaitHandle.WaitOne(400, $false)
    
    if ($ok) {
        try {
            $tcp.EndConnect($async)
            Write-Host "OPEN" -ForegroundColor Red
        } catch {
            Write-Host "CLOSED / FILTERED" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "FILTERED (Timeout)" -ForegroundColor DarkGray
    }
    $tcp.Close()
    Start-Sleep -Milliseconds 150
}

Write-Host "`n>>> [SUCCESS] Port scan simulation finished." -ForegroundColor Green
Write-Host ">>> Check AdaptiveCloud Dashboard: /detections and /classifications.`n"

