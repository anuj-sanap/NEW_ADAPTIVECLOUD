#!/usr/bin/env bash
# scripts/simulate/ssh_bruteforce.sh
# Controlled authentication brute-force simulation for Linux/WSL.
set -euo pipefail

TARGET_IP="${1:-127.0.0.1}"
TARGET_PORT="${2:-22}"
ATTEMPTS="${3:-5}"

echo -e "\n\033[1;33m========================================================"
echo -e " [SIMULATION] Vector 1: Authentication Brute-Force"
echo -e " Target IP:      $TARGET_IP"
echo -e " Target Port:    $TARGET_PORT"
echo -e " Expected Alert: brute_force (anomaly_score >= 0.75)"
echo -e " Expected Action: block_ip / Netsh firewall drop rule"
echo -e "========================================================\033[0m\n"

PASSWORDS=("Password123!" "Admin2026$" "SecretPass!" "Winter2026!" "Testing123!")

for i in $(seq 1 "$ATTEMPTS"); do
    PWD="${PASSWORDS[$(( (i-1) % ${#PASSWORDS[@]} ))]}"
    echo -n "[$i/$ATTEMPTS] Probing dummy account 'test_audit_account' with candidate password... "
    # Safe TCP probe with 1s timeout
    timeout 1 bash -c "echo 'SSH-2.0-AdaptiveCloud_Simulated_Prober' > /dev/tcp/$TARGET_IP/$TARGET_PORT" 2>/dev/null || true
    echo -e "\033[0;31mPROBE SENT (Simulated Fail)\033[0m"
    sleep 0.3
done

echo -e "\n\033[1;32m>>> [SUCCESS] Brute-force simulation finished.\033[0m\n"

