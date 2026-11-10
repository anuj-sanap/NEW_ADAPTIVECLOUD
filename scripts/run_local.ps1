<#
.SYNOPSIS
    AdaptiveCloud Local Development Launcher.
    Runs the FastAPI backend and React frontend concurrently on Windows without Docker or external DBs.
#>
[CmdletBinding()]
param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "backend"
$FrontendDir = Join-Path $RepoRoot "frontend"
$PythonExe = Join-Path $BackendDir ".venv\Scripts\python.exe"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   ADAPTIVECLOUD - LOCAL DEVELOPMENT RUNTIME LAUNCHER                   " -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# Set environment
$env:PYTHONPATH = "$BackendDir;$RepoRoot"
if (-not (Test-Path (Join-Path $RepoRoot ".env"))) {
    Write-Host "[*] Initializing local .env with SQLite engine..." -ForegroundColor Yellow
    @"
ENVIRONMENT=development
DEBUG=true
DOMAIN=localhost
DATABASE_URL=sqlite+aiosqlite:///./adaptivecloud.db
JWT_SECRET=adaptivecloud_development_secret_key_change_in_production_min32chars
AGENT_API_KEY=adm-agent-live-insecure-dev-key-change-in-production
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:3000","http://localhost:8000","https://localhost","http://localhost"]
WAZUH_ENABLED=false
WAZUH_ALERTS_PATH=backend/wazuh_alerts.json
"@ | Out-File -FilePath (Join-Path $RepoRoot ".env") -Encoding utf8
}

if (-not $FrontendOnly) {
    Write-Host "[*] Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Green
    $backendProcess = Start-Process -FilePath $PythonExe `
        -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload" `
        -WorkingDirectory $BackendDir `
        -PassThru
    Write-Host "[+] Backend running (PID: $($backendProcess.Id))" -ForegroundColor Green
}

if (-not $BackendOnly) {
    Write-Host "[*] Starting Vite React Frontend on http://localhost:5173..." -ForegroundColor Green
    $frontendProcess = Start-Process -FilePath "npm.cmd" `
        -ArgumentList "run dev" `
        -WorkingDirectory $FrontendDir `
        -PassThru
    Write-Host "[+] Frontend running (PID: $($frontendProcess.Id))" -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  Web Dashboard:   http://localhost:5173" -ForegroundColor Green
Write-Host "  Interactive API: http://localhost:8000/api/docs" -ForegroundColor Green
Write-Host "  Live Stream:     ws://localhost:8000/ws/live" -ForegroundColor Green
Write-Host "  Default Admin:   Username: admin | Password: password123" -ForegroundColor Yellow
Write-Host "========================================================================" -ForegroundColor Cyan

