<#
.SYNOPSIS
    Automated TLS/SSL Provisioning for AdaptiveCloud.
    Supports:
    - Free DuckDNS dynamic domain + Let's Encrypt automated ACME issuance
    - Local / Tailscale intranet zero-cost self-signed certificates with SAN support
.PARAMETER DuckDnsDomain
    Optional DuckDNS subdomain (e.g. "my-adaptivecloud" -> "my-adaptivecloud.duckdns.org")
.PARAMETER DuckDnsToken
    Optional DuckDNS account token (free from duckdns.org)
.PARAMETER Email
    Email address for Let's Encrypt expiration notifications
.PARAMETER SelfSigned
    Force self-signed / mkcert generation for local dev or Tailscale mesh IP
#>
[CmdletBinding()]
param(
    [string]$DuckDnsDomain = "",
    [string]$DuckDnsToken = "",
    [string]$Email = "admin@adaptivecloud.local",
    [switch]$SelfSigned
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$CertsDir = Join-Path $ScriptDir "certs"
$KeyPath = Join-Path $CertsDir "server.key"
$CrtPath = Join-Path $CertsDir "server.crt"

if (-not (Test-Path $CertsDir)) {
    New-Item -ItemType Directory -Path $CertsDir -Force | Out-Null
}

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "   ADAPTIVECLOUD - AUTOMATED TLS/SSL PROVISIONING (STRICT ₹0 BUDGET)   " -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

# Case 1: DuckDNS + Let's Encrypt Automated Mode
if ($DuckDnsDomain -and $DuckDnsToken -and (-not $SelfSigned)) {
    $CleanDomain = $DuckDnsDomain.Replace(".duckdns.org", "")
    $FullDomain = "$CleanDomain.duckdns.org"

    Write-Host "[*] Updating DuckDNS Dynamic DNS record for $FullDomain..." -ForegroundColor Yellow
    try {
        $updateUrl = "https://www.duckdns.org/update?domains=$CleanDomain&token=$DuckDnsToken&ip="
        $resp = Invoke-RestMethod -Uri $updateUrl -Method Get
        if ($resp -match "OK") {
            Write-Host "[+] DuckDNS dynamic IP synchronization succeeded." -ForegroundColor Green
        } else {
            Write-Warning "DuckDNS returned response: $resp. Check your token/domain."
        }
    } catch {
        Write-Warning "Could not update DuckDNS directly: $_"
    }

    Write-Host "[*] Checking for certbot tool..." -ForegroundColor Yellow
    $certbot = Get-Command certbot -ErrorAction SilentlyContinue
    if ($certbot) {
        Write-Host "[*] Executing Certbot standalone challenge on port 80..." -ForegroundColor Yellow
        & certbot certonly --standalone `
            -d $FullDomain `
            --non-interactive `
            --agree-tos `
            -m $Email `
            --preferred-challenges http

        $letsEncryptDir = "/etc/letsencrypt/live/$FullDomain"
        if (Test-Path "$letsEncryptDir/fullchain.pem") {
            Copy-Item "$letsEncryptDir/fullchain.pem" $CrtPath -Force
            Copy-Item "$letsEncryptDir/privkey.pem" $KeyPath -Force
            Write-Host "[+] Let's Encrypt certificates successfully installed to $CertsDir" -ForegroundColor Green
            exit 0
        }
    } else {
        Write-Host "[!] Certbot not installed on host. Running Certbot via Docker..." -ForegroundColor Yellow
        docker run -it --rm --name certbot `
            -v "$CertsDir:/etc/letsencrypt/live/$FullDomain" `
            -p 80:80 `
            certbot/certbot certonly --standalone `
            -d $FullDomain `
            --non-interactive `
            --agree-tos `
            -m $Email

        if (Test-Path "$CertsDir/fullchain.pem") {
            Copy-Item "$CertsDir/fullchain.pem" $CrtPath -Force
            Copy-Item "$CertsDir/privkey.pem" $KeyPath -Force
            Write-Host "[+] Let's Encrypt certificates issued via Docker." -ForegroundColor Green
            exit 0
        }
    }
}

# Case 2: Self-Signed Fallback / Local / Tailscale Intranet
Write-Host "[*] Generating SAN-enabled SSL certificates for development & Tailscale..." -ForegroundColor Yellow
$genCertScript = Join-Path (Split-Path -Parent $ScriptDir) "scripts\gen_cert.ps1"
if (Test-Path $genCertScript) {
    & powershell.exe -ExecutionPolicy Bypass -File $genCertScript -CertsDir $CertsDir -Domain "localhost"
} else {
    # Inline OpenSSL generation fallback
    $openssl = Get-Command openssl -ErrorAction SilentlyContinue
    if ($openssl) {
        & openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
            -keyout $KeyPath -out $CrtPath `
            -subj "/CN=adaptivecloud.local" `
            -addext "subjectAltName=DNS:localhost,DNS:adaptivecloud.local,IP:127.0.0.1"
    } else {
        Write-Warning "Neither OpenSSL nor gen_cert.ps1 found. Ensure certs/server.crt and server.key exist."
    }
}

if ((Test-Path $KeyPath) -and (Test-Path $CrtPath)) {
    Write-Host "[+] TLS certificates verified at:" -ForegroundColor Green
    Write-Host "    Key: $KeyPath"
    Write-Host "    Crt: $CrtPath"
} else {
    Write-Error "Failed to verify generated SSL certificates in $CertsDir"
}

