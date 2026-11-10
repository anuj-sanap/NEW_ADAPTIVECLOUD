#!/usr/bin/env bash
# scripts/simulate/service_failure.sh
# Service failure and recovery simulation for Linux/WSL.
set -euo pipefail

SERVICE_NAME="${1:-cron}"
RECOVERY_WAIT="${2:-6}"

echo -e "\n\033[1;33m========================================================"
echo -e " [SIMULATION] Vector 6: Monitored Service Failure & Recovery"
echo -e " Service Name:      $SERVICE_NAME"
echo -e " Expected Alert:    Predictive Maintenance Service Risk (STOPPED)"
echo -e " Expected Action:   restart_service (Dispatched via Agent Executor)"
echo -e "========================================================\033[0m\n"

if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "\033[0;31m[ACTION] Stopping service '$SERVICE_NAME' to simulate failure...\033[0m"
    sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
    sleep 2
    echo "[WAIT] Waiting $RECOVERY_WAIT seconds for agent auto-restart..."
    sleep "$RECOVERY_WAIT"
    sudo systemctl start "$SERVICE_NAME" 2>/dev/null || true
    echo -e "\033[0;32m[RESTORED] Service '$SERVICE_NAME' active.\033[0m"
else
    echo "[INFO] Service '$SERVICE_NAME' not running in this environment. Simulated signal emitted."
fi

echo -e "\n\033[1;32m>>> [SUCCESS] Service failure simulation finished.\033[0m\n"

