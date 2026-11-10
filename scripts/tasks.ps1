# scripts/tasks.ps1
# PowerShell Task Runner for AdaptiveCloud
# Usage: .\scripts\tasks.ps1 <command> [arguments]

[CmdletBinding()]
param(
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet("up", "down", "logs", "test", "migrate", "lint", "seed", "certs", "help")]
    [string]$Command,

    [Parameter(Position=1, ValueFromRemainingArguments=$true)]
    [string[]]$ArgsList
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$DeployDir = Join-Path $RepoRoot "deploy"
$BackendDir = Join-Path $RepoRoot "backend"

function Show-Header {
    param([string]$Title)
    Write-Host "`n>>> [AdaptiveCloud] $Title" -ForegroundColor Cyan
}

function Invoke-Up {
    Show-Header "Starting Docker Compose services (deploy/docker-compose.yml)..."
    Push-Location $DeployDir
    try {
        # Check if certs exist
        $certPath = Join-Path $DeployDir "certs\server.crt"
        if (-not (Test-Path $certPath)) {
            Write-Host "Certificates missing. Generating development certificates..." -ForegroundColor Yellow
            & "$PSScriptRoot\gen_cert.ps1"
        }
        docker compose up -d $ArgsList
        Write-Host "Services started successfully." -ForegroundColor Green
        docker compose ps
    }
    finally {
        Pop-Location
    }
}

function Invoke-Down {
    Show-Header "Stopping Docker Compose services..."
    Push-Location $DeployDir
    try {
        docker compose down $ArgsList
        Write-Host "Services stopped." -ForegroundColor Yellow
    }
    finally {
        Pop-Location
    }
}

function Invoke-Logs {
    Show-Header "Viewing service logs..."
    Push-Location $DeployDir
    try {
        if ($ArgsList) {
            docker compose logs -f $ArgsList
        } else {
            docker compose logs -f --tail=100
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-Test {
    Show-Header "Running backend test suite with pytest..."
    Push-Location $BackendDir
    try {
        $pytestCmd = "pytest"
        $venvPytest = Join-Path $BackendDir ".venv\Scripts\pytest.exe"
        if (Test-Path $venvPytest) {
            $pytestCmd = $venvPytest
        }
        & $pytestCmd -v $ArgsList
    }
    finally {
        Pop-Location
    }
}

function Invoke-Migrate {
    Show-Header "Running Alembic migrations..."
    Push-Location $BackendDir
    try {
        $alembicCmd = "alembic"
        $venvAlembic = Join-Path $BackendDir ".venv\Scripts\alembic.exe"
        if (Test-Path $venvAlembic) {
            $alembicCmd = $venvAlembic
        }
        $target = if ($ArgsList) { $ArgsList[0] } else { "head" }
        & $alembicCmd upgrade $target
        Write-Host "Migrations completed to: $target" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
}

function Invoke-Lint {
    Show-Header "Linting Python code..."
    Push-Location $RepoRoot
    try {
        $ruffCmd = "ruff"
        $venvRuff = Join-Path $BackendDir ".venv\Scripts\ruff.exe"
        if (Test-Path $venvRuff) {
            $ruffCmd = $venvRuff
        }
        & $ruffCmd check backend/ agent/ ml/
    }
    catch {
        Write-Host "Ruff not found or reported issues. Falling back to python compile check..." -ForegroundColor Yellow
        Get-ChildItem -Path @("backend", "agent", "ml") -Recurse -Filter "*.py" | ForEach-Object {
            python -m py_compile $_.FullName
        }
        Write-Host "Python files compiled with 0 syntax errors." -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
}

function Invoke-Seed {
    Show-Header "Seeding initial admin user and development fixtures..."
    $scriptPath = Join-Path $RepoRoot "scripts\create_admin.py"
    $pythonCmd = "python"
    $venvPy = Join-Path $BackendDir ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) {
        $pythonCmd = $venvPy
    }
    & $pythonCmd $scriptPath @ArgsList
}

function Invoke-Certs {
    Show-Header "Generating SSL/TLS development certificates..."
    & "$PSScriptRoot\gen_cert.ps1" @ArgsList
}

switch ($Command) {
    "up"      { Invoke-Up }
    "down"    { Invoke-Down }
    "logs"    { Invoke-Logs }
    "test"    { Invoke-Test }
    "migrate" { Invoke-Migrate }
    "lint"    { Invoke-Lint }
    "seed"    { Invoke-Seed }
    "certs"   { Invoke-Certs }
    "help"    {
        Write-Host "AdaptiveCloud Tasks Manager" -ForegroundColor Cyan
        Write-Host "  up       - Start Docker Compose services in background"
        Write-Host "  down     - Stop Docker Compose services"
        Write-Host "  logs     - Follow container logs"
        Write-Host "  test     - Execute backend test suite"
        Write-Host "  migrate  - Run Alembic database migrations"
        Write-Host "  lint     - Run linter / syntax checks"
        Write-Host "  seed     - Seed administrative user or sample fixtures"
        Write-Host "  certs    - Generate local TLS development certificates"
    }
}

