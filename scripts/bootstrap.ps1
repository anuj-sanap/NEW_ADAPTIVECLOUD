# Adaptive Cloud Security — Project Bootstrap Script
# Run from monorepo root: .\scripts\bootstrap.ps1

#Requires -Version 7.0
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-OK   { param($msg) Write-Host "  ✅ $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Write-Fail { param($msg) Write-Host "  ❌ $msg" -ForegroundColor Red }
function Write-Step { param($msg) Write-Host "`n▶ $msg" -ForegroundColor Cyan }

$ROOT = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "=====================================================" -ForegroundColor Cyan
Write-Host "  AdaptiveCloud Security — Bootstrap" -ForegroundColor Cyan
Write-Host "=====================================================" -ForegroundColor Cyan

# ── Step 1: Check Python 3.11+ ───────────────────────────────────────────────
Write-Step "Checking Python"
try {
    $pyVer = & python --version 2>&1
    if ($pyVer -match "Python (\d+)\.(\d+)") {
        $major = [int]$Matches[1]; $minor = [int]$Matches[2]
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
            Write-Fail "Python 3.11+ required (found $pyVer)"
            exit 1
        }
        Write-OK "Python $major.$minor detected"
    }
} catch {
    Write-Fail "Python not found. Install from https://python.org"
    exit 1
}

# ── Step 2: Check Node 20+ ───────────────────────────────────────────────────
Write-Step "Checking Node.js"
try {
    $nodeVer = & node --version 2>&1
    if ($nodeVer -match "v(\d+)") {
        $nodeMajor = [int]$Matches[1]
        if ($nodeMajor -lt 20) {
            Write-Fail "Node 20+ required (found $nodeVer)"
            exit 1
        }
        Write-OK "Node $nodeVer detected"
    }
} catch {
    Write-Fail "Node.js not found. Install from https://nodejs.org"
    exit 1
}

# ── Step 3: Check Git ────────────────────────────────────────────────────────
Write-Step "Checking Git"
try {
    $gitVer = & git --version 2>&1
    Write-OK $gitVer
} catch {
    Write-Fail "Git not found. Install from https://git-scm.com"
    exit 1
}

# ── Step 4: Ensure directories exist ────────────────────────────────────────
Write-Step "Creating directory structure"
$dirs = @("agent","backend","ml","frontend","deploy","docs","scripts")
foreach ($d in $dirs) {
    $path = Join-Path $ROOT $d
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
        Write-OK "Created $d/"
    } else {
        Write-OK "$d/ exists"
    }
}

# ── Step 5: Backend venv ─────────────────────────────────────────────────────
Write-Step "Setting up backend Python venv"
$backendVenv = Join-Path $ROOT "backend\.venv"
if (-not (Test-Path $backendVenv)) {
    & python -m venv $backendVenv
    Write-OK "Created backend/.venv"
} else {
    Write-OK "backend/.venv already exists"
}

$backendReqs = Join-Path $ROOT "backend\requirements.txt"
if (Test-Path $backendReqs) {
    $pip = Join-Path $backendVenv "Scripts\pip.exe"
    & $pip install --quiet --upgrade pip
    & $pip install --quiet -r $backendReqs
    Write-OK "Backend dependencies installed"
} else {
    Write-Warn "backend/requirements.txt not found — skipping pip install"
}

# ── Step 6: ML venv ──────────────────────────────────────────────────────────
Write-Step "Setting up ML Python venv"
$mlVenv = Join-Path $ROOT "ml\.venv"
if (-not (Test-Path $mlVenv)) {
    & python -m venv $mlVenv
    Write-OK "Created ml/.venv"
} else {
    Write-OK "ml/.venv already exists"
}

$mlReqs = Join-Path $ROOT "ml\requirements.txt"
if (Test-Path $mlReqs) {
    $mlPip = Join-Path $mlVenv "Scripts\pip.exe"
    & $mlPip install --quiet --upgrade pip
    & $mlPip install --quiet -r $mlReqs
    Write-OK "ML dependencies installed"
} else {
    Write-Warn "ml/requirements.txt not found — skipping pip install"
}

# ── Step 7: Agent venv ───────────────────────────────────────────────────────
Write-Step "Setting up agent Python venv (Windows-only: psutil + pywin32)"
$agentVenv = Join-Path $ROOT "agent\.venv"
if (-not (Test-Path $agentVenv)) {
    & python -m venv $agentVenv
    Write-OK "Created agent/.venv"
} else {
    Write-OK "agent/.venv already exists"
}

$agentReqs = Join-Path $ROOT "agent\requirements.txt"
if (Test-Path $agentReqs) {
    $agentPip = Join-Path $agentVenv "Scripts\pip.exe"
    & $agentPip install --quiet --upgrade pip
    & $agentPip install --quiet -r $agentReqs
    Write-OK "Agent dependencies installed"
} else {
    Write-Warn "agent/requirements.txt not found — skipping pip install"
}

# ── Step 8: Frontend npm install ─────────────────────────────────────────────
Write-Step "Installing frontend npm packages"
$frontendPkg = Join-Path $ROOT "frontend\package.json"
if (Test-Path $frontendPkg) {
    Push-Location (Join-Path $ROOT "frontend")
    try {
        & npm install --silent
        Write-OK "Frontend packages installed"
    } finally {
        Pop-Location
    }
} else {
    Write-Warn "frontend/package.json not found — skipping npm install"
}

# ── Step 9: Copy .env examples ───────────────────────────────────────────────
Write-Step "Copying .env.example files (if .env doesn't exist)"
$envPairs = @(
    @{ src = "backend\.env.example"; dst = "backend\.env" },
    @{ src = "ml\.env.example";      dst = "ml\.env" },
    @{ src = "deploy\.env.example";  dst = "deploy\.env" },
    @{ src = "agent\.env.example";   dst = "agent\.env" }
)
foreach ($pair in $envPairs) {
    $src = Join-Path $ROOT $pair.src
    $dst = Join-Path $ROOT $pair.dst
    if ((Test-Path $src) -and (-not (Test-Path $dst))) {
        Copy-Item $src $dst
        Write-Warn "Created $($pair.dst) from example — EDIT before running"
    } elseif (Test-Path $dst) {
        Write-OK "$($pair.dst) already exists"
    }
}

# ── Summary ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=====================================================" -ForegroundColor Green
Write-Host "  Bootstrap complete!" -ForegroundColor Green
Write-Host "=====================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Edit backend/.env  (set JWT_SECRET_KEY, passwords)"
Write-Host "  2. Edit agent/.env    (set AGENT_ID, AGENT_API_KEY, BACKEND_URL)"
Write-Host "  3. Generate self-signed TLS cert:"
Write-Host "       .\scripts\generate-cert.ps1"
Write-Host "  4. Start the stack:"
Write-Host "       cd deploy; docker compose up -d"
Write-Host "  5. Run DB migrations:"
Write-Host "       cd backend; .\.venv\Scripts\alembic upgrade head"
Write-Host "  6. Create the first admin user:"
Write-Host "       cd backend; .\.venv\Scripts\python scripts\create_admin.py"
Write-Host "  7. Start the frontend dev server:"
Write-Host "       cd frontend; npm run dev"
Write-Host ""

