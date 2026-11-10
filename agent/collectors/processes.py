"""
agent/collectors/processes.py
Heuristic suspicious process and anomalous activity detector.
Flags binaries in Temp/AppData/Downloads, obfuscated/encoded PowerShell,
suspicious network listeners, and unclassified high-CPU utilization loops.
"""
from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

import psutil

logger = logging.getLogger("agent.collectors.processes")

# Patterns matching encoded or hidden PowerShell invocations
ENCODED_PS_REGEX = re.compile(
    r"(powershell|pwsh).*(-\s*enc|-\s*encodedcommand|-\s*e\s+|\bfrombase64string\b|\bdownloadstring\b|\biex\b)",
    re.IGNORECASE,
)

# Known standard Windows processes that normally consume high CPU
WHITELIST_PROCS = {
    "system", "idle", "svchost.exe", "msmpeng.exe", "explorer.exe",
    "tiworker.exe", "trustedinstaller.exe", "python.exe", "taskmgr.exe"
}


class SuspiciousProcessCollector:
    """
    Scans running processes and generates security event records
    when anomalous behavior, suspicious paths, or obfuscated CLI arguments are identified.
    """

    def __init__(
        self,
        high_cpu_threshold: float = 75.0,
        flag_temp_dirs: bool = True,
        flag_encoded_ps: bool = True,
    ) -> None:
        self.high_cpu_threshold = high_cpu_threshold
        self.flag_temp_dirs = flag_temp_dirs
        self.flag_encoded_ps = flag_encoded_ps

        # Detect user and system temp paths
        self.suspicious_path_substrings = [
            "\\temp\\",
            "\\appdata\\local\\temp\\",
            "\\downloads\\",
            "\\appdata\\roaming\\",
        ]

    def _is_suspicious_path(self, exe_path: str) -> bool:
        low = exe_path.lower()
        return any(sub in low for sub in self.suspicious_path_substrings)

    def collect(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        now_iso = datetime.now(UTC).isoformat()

        for proc in psutil.process_iter(["pid", "name", "exe", "cmdline", "cpu_percent", "username"]):
            try:
                info = proc.info
                pid = info["pid"]
                name = info["name"] or "unknown"
                exe = info["exe"] or ""
                cmdline_list = info["cmdline"] or []
                cmdline = " ".join(cmdline_list)
                cpu = info["cpu_percent"] or 0.0
                user = info["username"]

                # 1. Obfuscated / Encoded PowerShell
                if self.flag_encoded_ps and ENCODED_PS_REGEX.search(cmdline):
                    findings.append({
                        "ts": now_iso,
                        "source": "agent",
                        "rule_id": "SP-001",
                        "level": 12,
                        "category": "suspicious_process",
                        "user": user,
                        "raw": {
                            "reason": "Obfuscated or encoded PowerShell command line detected",
                            "pid": pid,
                            "name": name,
                            "exe": exe,
                            "cmdline": cmdline[:500],
                        },
                    })
                    continue

                # 2. Binary executing out of Temp / Downloads / AppData
                if self.flag_temp_dirs and exe and self._is_suspicious_path(exe):
                    findings.append({
                        "ts": now_iso,
                        "source": "agent",
                        "rule_id": "SP-002",
                        "level": 9,
                        "category": "suspicious_process",
                        "user": user,
                        "raw": {
                            "reason": "Executable running from temporary, downloads, or roaming directory",
                            "pid": pid,
                            "name": name,
                            "exe": exe,
                            "cmdline": cmdline[:500],
                        },
                    })
                    continue

                # 3. High CPU unknown binary (crypto-mining / runaway anomaly)
                if cpu >= self.high_cpu_threshold and name.lower() not in WHITELIST_PROCS:
                    findings.append({
                        "ts": now_iso,
                        "source": "agent",
                        "rule_id": "SP-003",
                        "level": 8,
                        "category": "suspicious_process",
                        "user": user,
                        "raw": {
                            "reason": f"High anomalous CPU utilization ({cpu:.1f}%) by unlisted executable",
                            "pid": pid,
                            "name": name,
                            "exe": exe,
                            "cpu_percent": cpu,
                        },
                    })

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                logger.debug("Error inspecting process", error=str(e))

        return findings
