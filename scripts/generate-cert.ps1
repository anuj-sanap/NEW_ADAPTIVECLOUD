# Generate a self-signed TLS certificate for local dev (Nginx)
# Requires OpenSSL (included with Git for Windows at C:\Program Files\Git\usr\bin\openssl.exe)
# Or install mkcert for a CA-trusted cert: https://github.com/FiloSottile/mkcert

#Requires -Version 7.0
[CmdletBinding()]
param(
    [string]$CertsDir = "$PSScriptRoot\..\deploy\certs",
    [string]$CommonName = "adaptivecloud.local"
)

$CertsDir = Resolve-Path $CertsDir -ErrorAction SilentlyContinue
if (-not $CertsDir) {
    $CertsDir = "$PSScriptRoot\..\deploy\certs"
    New-Item -ItemType Directory -Force -Path $CertsDir | Out-Null
}

$keyPath  = Join-Path $CertsDir "server.key"
$crtPath  = Join-Path $CertsDir "server.crt"

# Try mkcert first (browser-trusted)
$mkcert = Get-Command mkcert -ErrorAction SilentlyContinue
if ($mkcert) {
    Write-Host "Using mkcert for CA-trusted cert..." -ForegroundColor Cyan
    & mkcert -install
    & mkcert -key-file $keyPath -cert-file $crtPath $CommonName localhost 127.0.0.1 ::1
    Write-Host "✅ mkcert cert generated at $CertsDir" -ForegroundColor Green
    exit 0
}

# Fall back to OpenSSL
$openssl = Get-Command openssl -ErrorAction SilentlyContinue
if (-not $openssl) {
    # Try Git's bundled OpenSSL
    $gitOpenssl = "C:\Program Files\Git\usr\bin\openssl.exe"
    if (Test-Path $gitOpenssl) {
        $openssl = $gitOpenssl
    } else {
        Write-Host "❌ OpenSSL not found. Install mkcert or Git for Windows." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Generating self-signed cert with OpenSSL..." -ForegroundColor Cyan

$subj = "/C=IN/ST=Dev/L=Local/O=AdaptiveCloud/CN=$CommonName"

& $openssl req -x509 -newkey rsa:4096 -keyout $keyPath -out $crtPath `
    -days 365 -nodes -subj $subj `
    -addext "subjectAltName=DNS:$CommonName,DNS:localhost,IP:127.0.0.1"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Self-signed cert generated:" -ForegroundColor Green
    Write-Host "   Key: $keyPath"
    Write-Host "   Cert: $crtPath"
    Write-Host ""
    Write-Host "⚠️  Browsers will warn about this cert — use mkcert for a trusted cert." -ForegroundColor Yellow
} else {
    Write-Host "❌ OpenSSL failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

