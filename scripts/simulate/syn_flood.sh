#!/usr/bin/env bash
# scripts/simulate/syn_flood.sh
# Controlled SYN burst simulation with 5-second hard time cap.
set -euo pipefail

TARGET_IP="${1:-127.0.0.1}"
TARGET_PORT="${2:-80}"
DURATION_SEC="${3:-5}"

echo -e "\n\033[1;33m========================================================"
echo -e " [SIMULATION] Vector 3: SYN Connection Burst (Duration Capped)"
echo -e " Target IP:         $TARGET_IP"
echo -e " Target Port:       $TARGET_PORT"
echo -e " Duration Cap:      $DURATION_SEC seconds (Hard safety cap)"
echo -e " Expected Alert:    ddos (anomaly_score >= 0.85)"
echo -e " Expected Action:   block_ip / automated rate-limiting"
echo -e "========================================================\033[0m\n"

if command -v hping3 &>/dev/null; then
    echo "[INFO] Running safe hping3 rate-limited burst for $DURATION_SEC seconds..."
    timeout "$DURATION_SEC" hping3 -S -p "$TARGET_PORT" -i u50000 -c 100 "$TARGET_IP" 2>/dev/null || true
else
    END_TIME=$((SECONDS + DURATION_SEC))
    COUNT=0
    while [ $SECONDS -lt $END_TIME ]; do
        COUNT=$((COUNT + 1))
        timeout 0.05 bash -c "echo > /dev/tcp/$TARGET_IP/$TARGET_PORT" 2>/dev/null || true
        sleep 0.05
    done
    echo "[INFO] Dispatched $COUNT safe simulated SYN probes."
fi

echo -e "\n\033[1;32m>>> [SUCCESS] SYN burst simulation finished.\033[0m\n"
