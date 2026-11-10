#!/usr/bin/env bash
# scripts/simulate/run_all.sh
# Linux/WSL master runner for all 6 controlled simulations.
set -euo pipefail

TARGET_IP="${1:-127.0.0.1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "\033[1;36m========================================================================"
echo -e "   ADAPTIVECLOUD - CONTROLLED ATTACK SIMULATION ORCHESTRATOR"
echo -e "   Target: $TARGET_IP | Mode: Defensive Telemetry Generation"
echo -e "========================================================================\033[0m"

echo -e "\n\033[1;33m>>> [1/6] Running Authentication Brute-Force...\033[0m"
bash "$SCRIPT_DIR/ssh_bruteforce.sh" "$TARGET_IP" 22 5
sleep 2

echo -e "\n\033[1;33m>>> [2/6] Running Multi-Port Scan...\033[0m"
bash "$SCRIPT_DIR/port_scan.sh" "$TARGET_IP"
sleep 2

echo -e "\n\033[1;33m>>> [3/6] Running SYN Connection Burst (5s Cap)...\033[0m"
bash "$SCRIPT_DIR/syn_flood.sh" "$TARGET_IP" 80 5
sleep 2

echo -e "\n\033[1;33m>>> [4/6] Running Suspicious Process Creation...\033[0m"
bash "$SCRIPT_DIR/suspicious_process.sh" 6
sleep 2

echo -e "\n\033[1;33m>>> [5/6] Running Resource Saturation & Disk Fill...\033[0m"
bash "$SCRIPT_DIR/resource_stress.sh" 10 30
sleep 2

echo -e "\n\033[1;33m>>> [6/6] Running Service Failure & Recovery...\033[0m"
bash "$SCRIPT_DIR/service_failure.sh" "cron" 6

echo -e "\n\033[1;32m========================================================================"
echo -e " [COMPLETED] All 6 attack simulations executed successfully!"
echo -e " Review AdaptiveCloud UI: http://localhost:5173"
echo -e "========================================================================\033[0m\n"

