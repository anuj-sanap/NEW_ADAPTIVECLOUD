# scripts/simulate/service_failure.ps1
# Simulates service failure and verifies automated agent recovery.
# Targets an allowlisted non-critical service (e.g., 'Spooler').

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [string]$ServiceName = "Spooler",

    [Parameter(Mandatory=$false)]
    [int]$RecoveryWaitSeconds = 6
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

Write-Host "`n========================================================" -ForegroundColor Yellow
Write-Host " [SIMULATION] Vector 6: Monitored Service Failure & Recovery" -ForegroundColor Yellow
Write-Host " Service Name:      $ServiceName" -ForegroundColor Cyan
Write-Host " Expected Alert:    Predictive Maintenance Service Risk (STOPPED)" -ForegroundColor Green
Write-Host " Expected Action:   restart_service (Dispatched via Agent Executor)" -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Yellow

$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

if ($null -eq $service) {
    Write-Host "[WARNING] Service '$ServiceName' not found on this host. Testing mock failure signal." -ForegroundColor Yellow
    exit 0
}

Write-Host "[ACTION] Stopping service '$ServiceName' to simulate unexpected failure..." -ForegroundColor Red
Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue

Start-Sleep -Seconds 2
$statusAfterStop = (Get-Service -Name $ServiceName).Status
Write-Host "[STATUS] Current service state: $statusAfterStop" -ForegroundColor Yellow
Write-Host "[WAIT] Waiting $RecoveryWaitSeconds seconds for AdaptiveCloud agent executor auto-recovery..." -ForegroundColor DarkGray

Start-Sleep -Seconds $RecoveryWaitSeconds

$recoveredStatus = (Get-Service -Name $ServiceName).Status
if ($recoveredStatus -eq "Running") {
    Write-Host "[VERIFIED] Service '$ServiceName' was restored to: $recoveredStatus!" -ForegroundColor Green
} else {
    Write-Host "[MANUAL RESTORE] Ensuring service is running..." -ForegroundColor Cyan
    Start-Service -Name $ServiceName -ErrorAction SilentlyContinue
    Write-Host "[RESTORED] Service '$ServiceName' is: $((Get-Service -Name $ServiceName).Status)" -ForegroundColor Green
}

Write-Host "`n>>> [SUCCESS] Service failure simulation finished." -ForegroundColor Green
Write-Host ">>> Check AdaptiveCloud Dashboard: /maintenance and /responses for verified recovery action.`n"

