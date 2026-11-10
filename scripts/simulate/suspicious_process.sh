#!/usr/bin/env bash
# scripts/simulate/suspicious_process.sh
# Harmless simulated reconnaissance process execution for Linux/WSL.
set -euo pipefail

HOLD_SECONDS="${1:-8}"

echo -e "\n\033[1;33m========================================================"
echo -e " [SIMULATION] Vector 4: Suspicious Process Execution"
echo -e " Hold Time:         $HOLD_SECONDS seconds before termination"
echo -e " Expected Alert:    suspicious_process (anomaly_score >= 0.80)"
echo -e " Expected Action:   kill_process / automated process termination"
echo -e "========================================================\033[0m\n"

SANDBOX_DIR="/tmp/adaptivecloud_sim"
mkdir -p "$SANDBOX_DIR"
TEST_SCRIPT="$SANDBOX_DIR/recon_test.sh"

cat << 'EOF' > "$TEST_SCRIPT"
#!/usr/bin/env bash
# Harmless discovery listener simulator
echo "[SANDBOX] Simulated discovery probe running..."
sleep 8
EOF
chmod +x "$TEST_SCRIPT"

echo "[EXEC] Spawning background test process..."
"$TEST_SCRIPT" &
TEST_PID=$!

echo -e "[STARTED] Spawned process with PID \033[1;36m$TEST_PID\033[0m"
sleep 3

if kill -0 "$TEST_PID" 2>/dev/null; then
    echo "[STATUS] Process active. Waiting for response engine or timeout..."
    sleep $((HOLD_SECONDS - 3))
    kill -9 "$TEST_PID" 2>/dev/null || true
    echo -e "\033[0;32m[CLEANUP] Test process terminated safely.\033[0m"
else
    echo -e "\033[0;32m[DETECTED] Process terminated by response engine!\033[0m"
fi

rm -rf "$SANDBOX_DIR"
echo -e "\n\033[1;32m>>> [SUCCESS] Suspicious process simulation finished.\033[0m\n"

