#!/usr/bin/env bash
# scripts/simulate/port_scan.sh
# Controlled port scan simulation for Linux/WSL using nmap or /dev/tcp.
set -euo pipefail

TARGET_IP="${1:-127.0.0.1}"
PORTS=(21 22 80 443 3389 8080 8443)

echo -e "\n\033[1;33m========================================================"
echo -e " [SIMULATION] Vector 2: Multi-Port Scan (Reconnaissance)"
echo -e " Target IP:      $TARGET_IP"
echo -e " Expected Alert: port_scan (anomaly_score >= 0.65)"
echo -e " Expected Action: temporary IP blocklist entry (60 min TTL)"
echo -e "========================================================\033[0m\n"

if command -v nmap &>/dev/null; then
    echo "[INFO] Running safe nmap scan on specified ports..."
    nmap -sS -p 21,22,80,443,3389,8080,8443 --max-rate 50 -Pn "$TARGET_IP" || true
else
    for p in "${PORTS[@]}"; do
        echo -n "[SCAN] Testing TCP port $p on $TARGET_IP... "
        if timeout 0.4 bash -c "echo > /dev/tcp/$TARGET_IP/$p" 2>/dev/null; then
            echo -e "\033[0;31mOPEN\033[0m"
        else
            echo -e "\033[0;37mCLOSED / FILTERED\033[0m"
        fi
        sleep 0.15
    done
fi

echo -e "\n\033[1;32m>>> [SUCCESS] Port scan simulation finished.\033[0m\n"
