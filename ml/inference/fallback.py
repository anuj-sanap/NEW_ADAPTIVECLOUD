"""
ml/inference/fallback.py
Heuristic Rule-Based Fallback for Host Events and Cold-Start Triage.
Operates when models are not yet trained or to handle Windows host telemetry (Event IDs, process spawns).
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from ml.taxonomy.labels import AttackFamily


class RuleBasedFallback:
    """
    Transparent rule-based fallback analyzer.
    Evaluates host events (failed logins, suspicious CLI tokens, port scan signatures).
    """

    @staticmethod
    def evaluate_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluates a security event dictionary.
        Returns a detection dict if a rule triggers, or None.
        """
        event_type = str(event.get("event_type", "")).lower()
        details = event.get("details", {})
        if isinstance(details, str):
            details = {"raw": details}

        # 1. Windows Event 4625: Failed logon burst
        event_id = str(details.get("event_id", event.get("event_id", "")))
        if event_id == "4625" or "failed logon" in event_type:
            failure_count = int(details.get("count", event.get("count", 1)))
            if failure_count >= 5:
                return {
                    "family": AttackFamily.BRUTE_FORCE.value,
                    "subtype": "windows_logon_brute_force",
                    "confidence": min(0.99, 0.70 + (failure_count * 0.02)),
                    "rule": "RULE_WIN_4625_BURST",
                    "reason": f"Detected {failure_count} consecutive failed logon attempts (Event 4625).",
                }

        # 2. Suspicious process executions
        proc_name = str(details.get("process_name", "")).lower()
        cmd_line = str(details.get("command_line", "")).lower()

        suspicious_keywords = [
            "mimikatz", "meterpreter", "invoke-expression", "iex(", "downloadstring",
            "powershell -enc", "certutil -urlcache", "vssadmin delete shadows"
        ]
        for kw in suspicious_keywords:
            if kw in cmd_line or kw in proc_name:
                return {
                    "family": AttackFamily.INFILTRATION.value,
                    "subtype": "suspicious_process_injection",
                    "confidence": 0.95,
                    "rule": "RULE_SUSPICIOUS_CMDLINE",
                    "reason": f"Process execution matched high-risk signature: {kw}",
                }

        # 3. Port scan signature: high distinct ports or zero-payload SYN burst
        syn_cnt = float(event.get("syn_flag_cnt", details.get("syn_flag_cnt", 0)))
        ack_cnt = float(event.get("ack_flag_cnt", details.get("ack_flag_cnt", 0)))
        flow_duration = float(event.get("flow_duration", details.get("flow_duration", 999999)))

        if syn_cnt >= 5 and ack_cnt == 0 and flow_duration < 100_000:
            return {
                "family": AttackFamily.PORT_SCAN_RECON.value,
                "subtype": "syn_stealth_scan",
                "confidence": 0.88,
                "rule": "RULE_SYN_STEALTH_SCAN",
                "reason": "Flow exhibit high SYN count without ACK completions over short duration.",
            }

        return None
