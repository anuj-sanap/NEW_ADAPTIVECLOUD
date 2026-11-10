# scripts/simulate/resource_stress.ps1
# Generates controlled CPU compute load and bounded temporary disk fill for predictive maintenance testing.
# Strictly bounded: 12 seconds max, disk fill capped at 30 MB with immediate automatic cleanup.

[CmdletBinding()]
param(
    [Parameter(Mandatory=$false)]
    [int]$DurationSeconds = 12,

    [Parameter(Mandatory=$false)]
    [int]$DiskCapMB = 30
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Continue"

Write-Host "`n========================================================" -ForegroundColor Yellow
Write-Host " [SIMULATION] Vector 5: Resource Saturation & Disk Fill" -ForegroundColor Yellow
Write-Host " Duration:          $DurationSeconds seconds" -ForegroundColor Cyan
Write-Host " Disk Fill Cap:     $DiskCapMB MB (Strict safety cap, temporary sandbox)" -ForegroundColor Cyan
Write-Host " Expected Alert:    Predictive Maintenance CPU > 85%, Disk ETA Warning" -ForegroundColor Green
Write-Host " Expected Action:   Capacity Warning Broadcasted to /maintenance" -ForegroundColor Green
Write-Host "========================================================`n" -ForegroundColor Yellow

$sandboxDir = [System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "adaptivecloud_stress")
if (-not (Test-Path $sandboxDir)) {
    New-Item -ItemType Directory -Path $sandboxDir -Force | Out-Null
}
$tempFile = Join-Path $sandboxDir "synthetic_payload.tmp"

try {
    Write-Host "[DISK] Writing bounded $DiskCapMB MB temporary payload to simulate storage slope..." -ForegroundColor Cyan
    $stream = [System.IO.File]::Create($tempFile)
    $buffer = New-Object byte[] (1024 * 1024) # 1 MB buffer
    for ($i = 0; $i -lt $DiskCapMB; $i++) {
        $stream.Write($buffer, 0, $buffer.Length)
    }
    $stream.Close()
    Write-Host "[DISK] Completed writing sandbox file: $([math]::Round((Get-Item $tempFile).Length / 1MB, 2)) MB" -ForegroundColor Green

    Write-Host "[CPU] Applying synthetic CPU compute pressure across available threads for $DurationSeconds s..." -ForegroundColor Yellow
    $stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    $job = Start-Job -ScriptBlock {
        param($duration)
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        while ($sw.Elapsed.TotalSeconds -lt $duration) {
            $val = [math]::Sqrt(1234567.89) * [math]::Sin(45.0)
        }
    } -ArgumentList $DurationSeconds

    while ($stopwatch.Elapsed.TotalSeconds -lt $DurationSeconds) {
        $remaining = [math]::Round($DurationSeconds - $stopwatch.Elapsed.TotalSeconds, 1)
        Write-Host "[$([int]$stopwatch.Elapsed.TotalSeconds)s/$DurationSeconds s] Stress active ($remaining s remaining)..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 2
    }

    Wait-Job $job -Timeout 2 | Out-Null
    Receive-Job $job | Out-Null
    Remove-Job $job -Force | Out-Null
}
finally {
    Write-Host "[CLEANUP] Removing temporary stress payload..." -ForegroundColor Cyan
    Remove-Item -Path $sandboxDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "[CLEANUP] Sandbox storage reclaimed." -ForegroundColor Green
}

Write-Host "`n>>> [SUCCESS] Resource stress simulation completed safely." -ForegroundColor Green
Write-Host ">>> Check AdaptiveCloud Dashboard: /maintenance and /monitoring for forecast slope updates.`n"
