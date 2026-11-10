#!/usr/bin/env bash
# ==============================================================================
# deploy/nginx/duckdns_certbot.sh
# Automated DuckDNS IP update + Let's Encrypt Certificate Issuance / Renewal
# Designed for Linux / WSL / Google Cloud VM host deployments with ₹0 budget.
# ==============================================================================
set -euo pipefail

DUCKDNS_DOMAIN="${1:-${DUCKDNS_DOMAIN:-}}"
DUCKDNS_TOKEN="${2:-${DUCKDNS_TOKEN:-}}"
EMAIL="${3:-${ADMIN_EMAIL:-admin@adaptivecloud.local}}"
CERTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../certs" && pwd)"

mkdir -p "${CERTS_DIR}"

if [[ -z "${DUCKDNS_DOMAIN}" || -z "${DUCKDNS_TOKEN}" ]]; then
    echo "[!] DUCKDNS_DOMAIN and DUCKDNS_TOKEN must be specified as arguments or environment variables."
    echo "    Usage: ./duckdns_certbot.sh <subdomain> <token> [email]"
    echo "[*] Falling back to generating self-signed TLS certificates for development..."
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "${CERTS_DIR}/server.key" \
        -out "${CERTS_DIR}/server.crt" \
        -subj "/CN=adaptivecloud.local" \
        -addext "subjectAltName=DNS:localhost,DNS:adaptivecloud.local,IP:127.0.0.1"
    
    echo "[+] Self-signed certificates generated in ${CERTS_DIR}"
    exit 0
fi

CLEAN_DOMAIN="${DUCKDNS_DOMAIN/.duckdns.org/}"
FULL_DOMAIN="${CLEAN_DOMAIN}.duckdns.org"

echo "[*] Updating DuckDNS IP address for ${FULL_DOMAIN}..."
DUCK_RESP=$(curl -s "https://www.duckdns.org/update?domains=${CLEAN_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=")
if [[ "${DUCK_RESP}" == *"OK"* ]]; then
    echo "[+] DuckDNS dynamic DNS record updated successfully."
else
    echo "[!] DuckDNS update returned: ${DUCK_RESP}"
fi

echo "[*] Requesting Let's Encrypt certificate for ${FULL_DOMAIN}..."
if command -v certbot >/dev/null 2>&1; then
    certbot certonly --standalone \
        -d "${FULL_DOMAIN}" \
        --non-interactive \
        --agree-tos \
        -m "${EMAIL}" \
        --preferred-challenges http

    LE_PATH="/etc/letsencrypt/live/${FULL_DOMAIN}"
    cp "${LE_PATH}/fullchain.pem" "${CERTS_DIR}/server.crt"
    cp "${LE_PATH}/privkey.pem" "${CERTS_DIR}/server.key"
    echo "[+] Certificates copied to ${CERTS_DIR}"
else
    echo "[*] Certbot CLI not found locally. Running Certbot in Docker container..."
    docker run -it --rm \
        -v "/etc/letsencrypt:/etc/letsencrypt" \
        -v "/var/lib/letsencrypt:/var/lib/letsencrypt" \
        -p 80:80 \
        certbot/certbot certonly --standalone \
        -d "${FULL_DOMAIN}" \
        --non-interactive \
        --agree-tos \
        -m "${EMAIL}"

    LE_PATH="/etc/letsencrypt/live/${FULL_DOMAIN}"
    sudo cp "${LE_PATH}/fullchain.pem" "${CERTS_DIR}/server.crt"
    sudo cp "${LE_PATH}/privkey.pem" "${CERTS_DIR}/server.key"
    sudo chmod 644 "${CERTS_DIR}/server.crt"
    sudo chmod 600 "${CERTS_DIR}/server.key"
    echo "[+] Certificates acquired and copied to ${CERTS_DIR}"
fi
