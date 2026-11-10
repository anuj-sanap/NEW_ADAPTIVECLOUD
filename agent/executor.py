"""
agent/executor.py
Cross-platform command executor with safety allowlists for the AdaptiveCloud agent.
Validates countermeasures against strict internal allowlists before issuing OS-level commands.
Supports Windows Defender Firewall (netsh/PowerShell), service restarts, and process termination.
"""
from __future__ import annotations

import ipaddress
import logging
import os
import platform
import subprocess
import sys
import time
from typing import Any

import psutil

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [executor] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("agent.executor")

# Protected critical Windows & Linux system processes that CANNOT be terminated
PROTECTED_PROCESSES = {
    # Windows
    "system",
    "idle",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "explorer.exe",
    "winlogon.exe",
    "taskmgr.exe",
    "dwm.exe",
    "fontdrvhost.exe",
    "sihost.exe",
    # Linux
    "systemd",
    "init",
    "kthreadd",
    "sshd",
    "dbus-daemon",
    "systemd-journald",
}

# Allowlisted services that can be safely restarted
RESTARTABLE_SERVICES = {
    # Windows
    "spooler",
    "w32time",
    "dnscache",
    "lanmanworkstation",
    "wazuh",
    "adaptivecloud-agent",
    # Linux
    "nginx",
    "wazuh-agent",
    "cron",
    "rsyslog",
}

# Default CIDRs and networks that must never be blocked
NEVER_BLOCK_CIDRS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),  # Tailscale CGNAT mesh
    ipaddress.ip_network("10.0.0.0/8"),      # GCP VPC internal
    ipaddress.ip_network("172.16.0.0/12"),   # Docker bridge / internal
    ipaddress.ip_network("192.168.0.0/16"),  # LAN
    ipaddress.ip_network("::1/128"),
]


class CommandValidator:
    """Enforces safety guardrails on all response commands."""

    @staticmethod
    def is_protected_ip(ip_str: str) -> bool:
        """Check if an IP belongs to loopback, private RFC1918, or Tailscale CGNAT."""
        try:
            addr = ipaddress.ip_address(ip_str.strip())
            for net in NEVER_BLOCK_CIDRS:
                if addr in net:
                    return True
        except ValueError:
            return False
        return False

    @staticmethod
    def is_protected_process(target: str) -> bool:
        """Check if target process name or PID belongs to critical OS infrastructure."""
        clean = target.strip().lower()
        if clean in PROTECTED_PROCESSES:
            return True
        # Check by PID if target is integer
        try:
            pid = int(clean)
            if pid <= 4:  # System and Idle
                return True
            proc = psutil.Process(pid)
            if proc.name().lower() in PROTECTED_PROCESSES:
                return True
            # Never kill current agent process or its parent
            if pid == os.getpid() or pid == os.getppid():
                return True
        except (ValueError, psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return False

    @staticmethod
    def is_allowlisted_service(service_name: str) -> bool:
        """Verify service name is within permitted restartable services."""
        return service_name.strip().lower() in RESTARTABLE_SERVICES


class AgentExecutor:
    """Executes validated countermeasure actions and reports forensic results."""

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.is_windows = platform.system().lower() == "windows"

    def execute_action(self, action: str, target: str, action_id: str | None = None) -> dict[str, Any]:
        """Validates and executes an adaptive response action."""
        t0 = time.perf_counter()
        result: dict[str, Any] = {
            "action_id": action_id,
            "action": action,
            "target": target,
            "success": False,
            "dry_run": self.dry_run,
            "output": "",
            "returncode": 0,
            "execution_time_ms": 0.0,
        }

        logger.info("Received countermeasure request: %s on target '%s' (dry_run=%s)", action, target, self.dry_run)

        # 1. Validation phase
        if action == "block_ip":
            if CommandValidator.is_protected_ip(target):
                result["output"] = f"SAFETY REFUSAL: Target IP {target} belongs to protected allowlist."
                result["returncode"] = 1
                logger.warning("Blocked attempt to firewall protected IP: %s", target)
                result["execution_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                return result

        elif action == "kill_process":
            if CommandValidator.is_protected_process(target):
                result["output"] = f"SAFETY REFUSAL: Process '{target}' is protected critical infrastructure."
                result["returncode"] = 1
                logger.warning("Blocked attempt to kill protected process: %s", target)
                result["execution_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                return result

        elif action == "restart_service":
            if not CommandValidator.is_allowlisted_service(target):
                result["output"] = f"SAFETY REFUSAL: Service '{target}' is not in allowlisted restartable services."
                result["returncode"] = 1
                logger.warning("Blocked attempt to restart unapproved service: %s", target)
                result["execution_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                return result

        # 2. Dry-run early return
        if self.dry_run:
            result["success"] = True
            result["output"] = f"[DRY-RUN SIMULATION] Action '{action}' on '{target}' would have been executed."
            result["execution_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            return result

        # 3. OS Execution Phase
        try:
            if action == "block_ip":
                result = self._execute_block_ip(target, result)
            elif action == "unblock_ip":
                result = self._execute_unblock_ip(target, result)
            elif action == "restrict":
                result = self._execute_restrict_user(target, result)
            elif action == "unrestrict":
                result = self._execute_unrestrict_user(target, result)
            elif action == "kill_process":
                result = self._execute_kill_process(target, result)
            elif action == "restart_service":
                result = self._execute_restart_service(target, result)
            else:
                result["output"] = f"Unsupported action type: {action}"
                result["returncode"] = 1

        except Exception as e:
            result["output"] = f"Execution exception: {e}"
            result["returncode"] = -1
            logger.error("Failed executing %s: %s", action, e)

        result["execution_time_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        return result

    def _execute_block_ip(self, ip: str, res: dict[str, Any]) -> dict[str, Any]:
        rule_name = f"AdaptiveBlock_{ip.replace(':', '_')}"
        if self.is_windows:
            cmd = [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={rule_name}", "dir=in", "action=block", f"remoteip={ip}",
            ]
        else:
            cmd = ["iptables", "-I", "INPUT", "-s", ip, "-j", "DROP"]

        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        res["success"] = (p.returncode == 0)
        res["returncode"] = p.returncode
        res["output"] = (p.stdout + p.stderr).strip() or "Rule added successfully."
        return res

    def _execute_unblock_ip(self, ip: str, res: dict[str, Any]) -> dict[str, Any]:
        rule_name = f"AdaptiveBlock_{ip.replace(':', '_')}"
        if self.is_windows:
            cmd = ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={rule_name}"]
        else:
            cmd = ["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"]

        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        res["success"] = (p.returncode == 0)
        res["returncode"] = p.returncode
        res["output"] = (p.stdout + p.stderr).strip() or "Rule deleted successfully."
        return res

    def _execute_restrict_user(self, username: str, res: dict[str, Any]) -> dict[str, Any]:
        """Locks a user account after brute-force authentication threshold breach."""
        if self.is_windows:
            cmd = ["net", "user", username, "/active:no"]
        else:
            cmd = ["passwd", "-l", username]

        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        res["success"] = (p.returncode == 0)
        res["returncode"] = p.returncode
        res["output"] = (p.stdout + p.stderr).strip() or f"User {username} account disabled."
        return res

    def _execute_unrestrict_user(self, username: str, res: dict[str, Any]) -> dict[str, Any]:
        """Unlocks a restricted user account during rollback."""
        if self.is_windows:
            cmd = ["net", "user", username, "/active:yes"]
        else:
            cmd = ["passwd", "-u", username]

        p = subprocess.run(cmd, capture_output=True, text=True, check=False)
        res["success"] = (p.returncode == 0)
        res["returncode"] = p.returncode
        res["output"] = (p.stdout + p.stderr).strip() or f"User {username} account re-enabled."
        return res

    def _execute_kill_process(self, target: str, res: dict[str, Any]) -> dict[str, Any]:
        killed = 0
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if str(proc.info["pid"]) == target or proc.info["name"].lower() == target.lower():
                    proc.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        res["success"] = (killed > 0)
        res["returncode"] = 0 if killed > 0 else 1
        res["output"] = f"Terminated {killed} process(es) matching '{target}'"
        return res

    def _execute_restart_service(self, service_name: str, res: dict[str, Any]) -> dict[str, Any]:
        if self.is_windows:
            cmd = f'net stop "{service_name}" && net start "{service_name}"'
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        else:
            cmd = ["systemctl", "restart", service_name]
            p = subprocess.run(cmd, capture_output=True, text=True, check=False)

        res["success"] = (p.returncode == 0)
        res["returncode"] = p.returncode
        res["output"] = (p.stdout + p.stderr).strip() or f"Service {service_name} restarted successfully."
        return res
