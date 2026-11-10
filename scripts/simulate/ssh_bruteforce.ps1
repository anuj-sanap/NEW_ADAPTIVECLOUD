# scripts/simulate/ssh_bruteforce.ps1
# Simulates controlled authentication brute-force against a target test host.
# LEGAL WARNING: Use only against your own authorized test worker VMs.

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$TargetIp = "127.0.0.1",

    [Parameter(Mandatory=$false)]
    [int]$TargetPort = 22,

    [Parameter(Mandatory=$false)]
    [int]$Attempts = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

Write-Host "`n========================================================" -ForegroundColor Yellow
Write-Host " [SIMULATION] Vector 1: Authentication Brute-Force" -ForegroundColor Yellow
Write-Host " Target IP:      $TargetIp" -ForegroundColor Cyan
Write-Host " Target Port:    $TargetPort" -ForegroundColor Cyan
Write-Host " Test Attempts:  $Attempts (bounded safety ceiling)" -ForegroundColor Cyan
Write-Host " Expected Alert: brute_force (anomaly_score >= 0.75)" -ForegroundColor Green
Write-Host " Expected Action: block_ip / Netsh firewall drop rule" -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Yellow

$dummyUser = "test_audit_account"
$passwords = @("Password123!", "Admin2026$", "SecretPass!", "Winter2026!", "Testing123!")

$count = 0
foreach ($pwd in $passwords) {
    if ($count -ge $Attempts) { break }
    $count++
    
    Write-Host "[$count/$Attempts] Simulating failed credential challenge for '$dummyUser'..." -NoNewline
    
    try {
        # Attempt TCP socket connection + credential probe simulation
        $client = New-Object System.Net.Sockets.TcpClient
        $asyncResult = $client.BeginConnect($TargetIp, $TargetPort, $null, $null)
        $waitSuccess = $asyncResult.AsyncWaitHandle.WaitOne(1000, $false)
        
        if ($waitSuccess) {
            $client.EndConnect($asyncResult)
            $stream = $client.GetStream()
            $writer = New-Object System.IO.StreamWriter($stream)
            $writer.WriteLine("SSH-2.0-AdaptiveCloud_Simulated_Prober")
            $writer.Flush()
            $client.Close()
            Write-Host " PROBE SENT (Simulated Fail)" -ForegroundColor Red
        } else {
            Write-Host " TARGET UNREACHABLE (Simulated Drop)" -ForegroundColor DarkGray
        }
    } catch {
        Write-Host " REJECTED (Expected: Auth Failed)" -ForegroundColor Yellow
    }

    Start-Sleep -Milliseconds 300
}

Write-Host "`n>>> [SUCCESS] Brute-force simulation finished." -ForegroundColor Green
Write-Host ">>> Check AdaptiveCloud Dashboard: /detections and /rca for incident correlation.`n"

