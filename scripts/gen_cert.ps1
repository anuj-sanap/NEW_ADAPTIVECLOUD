# scripts/gen_cert.ps1
# Generate SSL/TLS certificate for local HTTPS with Nginx
# Prioritizes mkcert (browser-trusted), falls back to OpenSSL or PowerShell New-SelfSignedCertificate

[CmdletBinding()]
param(
    [string]$CertsDir = "$PSScriptRoot\..\deploy\certs",
    [string]$Domain = "localhost"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $CertsDir)) {
    New-Item -ItemType Directory -Force -Path $CertsDir | Out-Null
}

$ResolvedDir = (Resolve-Path $CertsDir).Path
$KeyPath = Join-Path $ResolvedDir "server.key"
$CrtPath = Join-Path $ResolvedDir "server.crt"

Write-Host ">>> Target directory: $ResolvedDir" -ForegroundColor Cyan

# 1. Try mkcert (preferred for local zero-warning development)
$mkcert = Get-Command mkcert -ErrorAction SilentlyContinue
if ($mkcert) {
    Write-Host "Using mkcert to generate browser-trusted local certificates..." -ForegroundColor Green
    & mkcert -install
    & mkcert -key-file $KeyPath -cert-file $CrtPath $Domain "127.0.0.1" "::1" "adaptivecloud.local"
    Write-Host "Certificate generation complete with mkcert." -ForegroundColor Green
    exit 0
}

# 2. Try OpenSSL (system path or Git for Windows)
$openssl = Get-Command openssl -ErrorAction SilentlyContinue
if (-not $openssl) {
    $gitOpenssl = "C:\Program Files\Git\usr\bin\openssl.exe"
    if (Test-Path $gitOpenssl) {
        $openssl = $gitOpenssl
    }
}

if ($openssl) {
    Write-Host "Using OpenSSL to generate self-signed certificate..." -ForegroundColor Yellow
    $subj = "/C=US/ST=Dev/L=Local/O=AdaptiveCloud/CN=$Domain"
    & $openssl req -x509 -newkey rsa:2048 -keyout $KeyPath -out $CrtPath `
        -days 365 -nodes -subj $subj `
        -addext "subjectAltName=DNS:$Domain,DNS:adaptivecloud.local,IP:127.0.0.1"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Self-signed certificate generated with OpenSSL." -ForegroundColor Green
        exit 0
    }
}

# 3. Fallback: Native PowerShell certificate export
Write-Host "OpenSSL and mkcert not detected. Using PowerShell PKI cmdlets..." -ForegroundColor Yellow
$cert = New-SelfSignedCertificate -DnsName $Domain, "127.0.0.1", "adaptivecloud.local" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter (Get-Date).AddYears(1) `
    -KeyExportPolicy Exportable `
    -KeySpec Signature `
    -KeyLength 2048 `
    -KeyAlgorithm RSA `
    -HashAlgorithm SHA256

$certBytes = $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
[System.IO.File]::WriteAllBytes($CrtPath, $certBytes)

# Export key as PEM if possible
Write-Host "Certificate written to $CrtPath. Key should be generated via openssl/mkcert when available." -ForegroundColor Yellow
Write-Host "Done." -ForegroundColor Green

