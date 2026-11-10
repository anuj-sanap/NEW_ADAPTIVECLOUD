# scripts/simulate/suspicious_process.ps1
# Simulates unauthorized reconnaissance / suspicious process creation.
# Run on the monitored worker VM or locally in a test container.

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [int]$HoldSeconds = 8
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

Write-Host "`n========================================================" -ForegroundColor Yellow
Write-Host " [SIMULATION] Vector 4: Suspicious Process Execution" -ForegroundColor Yellow
Write-Host " Hold Time:         $HoldSeconds seconds before automatic termination" -ForegroundColor Cyan
Write-Host " Expected Alert:    suspicious_process (anomaly_score >= 0.80)" -ForegroundColor Green
Write-Host " Expected Action:   kill_process / automated process termination" -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Yellow

$tempSandboxDir = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "adaptivecloud_sim")
if (-not (Test-Path $tempSandboxDir)) {
    New-Item -ItemType Directory -Path $tempSandboxDir -Force | Out-Null
}

$simScriptPath = Join-Path $tempSandboxDir "mimikatz_test_recon.ps1"
$simScriptContent = @"
# Harmless simulated reconnaissance test script
Write-Output 'AdaptiveCloud Security Test - Harmless Discovery Simulation'
Start-Sleep -Seconds $HoldSeconds
"@
Set-Content -Path $simScriptPath -Value $simScriptContent -Force

Write-Host "[EXEC] Spawning simulated reconnaissance background process (PID will be monitored)..." -ForegroundColor Yellow

# Launch background PowerShell process with recognizable argument signature for agent Event 4688 tracking
$proc = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command & '$simScriptPath'" `
    -PassThru

Write-Host "[STARTED] Spawned process '$($proc.ProcessName)' with PID $($proc.Id)" -ForegroundColor Cyan
Write-Host "[MONITOR] Agent and Windows Event Log (4688) capturing execution..." -ForegroundColor DarkGray

Start-Sleep -Seconds 3

# Check if process is still running or if automated response engine killed it
$stillRunning = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue

if ($null -ne $stillRunning) {
    Write-Host "[STATUS] Process still active. Waiting for response engine or timeout..." -ForegroundColor Yellow
    Start-Sleep -Seconds ($HoldSeconds - 3)
    # Safe cleanup if not already terminated
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    Write-Host "[CLEANUP] Test process terminated safely." -ForegroundColor Green
} else {
    Write-Host "[DETECTED] Process was successfully terminated by countermeasure engine!" -ForegroundColor Green
}

# Clean temp script
Remove-Item -Path $tempSandboxDir -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "`n>>> [SUCCESS] Suspicious process simulation finished." -ForegroundColor Green
Write-Host ">>> Check AdaptiveCloud Dashboard: /detections and /responses.`n"
