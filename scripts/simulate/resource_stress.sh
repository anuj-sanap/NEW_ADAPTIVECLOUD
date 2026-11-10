#!/usr/bin/env bash
# scripts/simulate/resource_stress.sh
# Synthetic CPU and bounded disk fill simulation for Linux/WSL.
set -euo pipefail

DURATION_SEC="${1:-12}"
DISK_CAP_MB="${2:-30}"

echo -e "\n\033[1;33m========================================================"
echo -e " [SIMULATION] Vector 5: Resource Saturation & Disk Fill"
echo -e " Duration:          $DURATION_SEC seconds"
echo -e " Disk Fill Cap:     $DISK_CAP_MB MB (Strict safety cap)"
echo -e " Expected Alert:    Predictive Maintenance CPU > 85%, Disk ETA Warning"
echo -e " Expected Action:   Capacity Warning Broadcasted to /maintenance"
echo -e "========================================================\033[0m\n"

SANDBOX_DIR="/tmp/adaptivecloud_stress"
mkdir -p "$SANDBOX_DIR"
TEMP_FILE="$SANDBOX_DIR/synthetic_payload.tmp"

cleanup() {
    echo -e "\033[0;36m[CLEANUP] Reclaiming temporary storage...\033[0m"
    rm -rf "$SANDBOX_DIR"
    echo -e "\033[0;32m[CLEANUP] Completed.\033[0m"
}
trap cleanup EXIT

echo -e "\033[0;36m[DISK] Generating bounded $DISK_CAP_MB MB file to simulate disk fill slope...\033[0m"
dd if=/dev/zero of="$TEMP_FILE" bs=1M count="$DISK_CAP_MB" 2>/dev/null

if command -v stress-ng &>/dev/null; then
    echo "[CPU] Running safe stress-ng for $DURATION_SEC seconds..."
    stress-ng --cpu 2 --timeout "${DURATION_SEC}s" --metrics-brief 2>/dev/null || true
else
    echo "[CPU] Running synthetic compute loop for $DURATION_SEC seconds..."
    END_TIME=$((SECONDS + DURATION_SEC))
    while [ $SECONDS -lt $END_TIME ]; do
        : $(( 123456 * 789101 ))
    done
fi

echo -e "\n\033[1;32m>>> [SUCCESS] Resource stress simulation completed safely.\033[0m\n"

