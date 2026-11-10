"""
agent/agent.py
Main orchestrator for the AdaptiveCloud Windows Host Monitoring Agent.
Loads config.yaml, coordinates periodic system metrics, Windows event log polling,
heuristic process auditing, flow telemetry, and executes adaptive commands.
"""
from __future__ import annotations

import logging
import platform
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from agent.collectors import (
    FlowCollector,
    SuspiciousProcessCollector,
    SystemCollector,
    WinEventsCollector,
)
from agent.executor import AgentExecutor
from agent.sender import AgentSender

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("agent.core")


def load_config(config_path: str = "config.yaml") -> dict[str, Any]:
    p = Path(config_path)
    if not p.exists():
        # Look in directory containing script
        p = Path(__file__).parent / config_path
    if not p.exists():
        logger.warning("Config file not found at %s. Using default parameters.", config_path)
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class ResponseExecutor:
    """Executes countermeasures (block_ip, restrict, kill_process, restart_service) received from backend."""

    _executor = AgentExecutor(dry_run=False)

    @classmethod
    def execute(cls, command: dict[str, Any]) -> dict[str, Any]:
        action = command.get("action", "")
        target = command.get("target", "")
        cmd_id = command.get("id")
        return cls._executor.execute_action(action=action, target=target, action_id=cmd_id)


class MonitoringAgent:
    """Central agent service managing collector cycles and control plane synchronization."""

    def __init__(self, config_file: str = "config.yaml") -> None:
        self.config = load_config(config_file)
        self.running = False

        srv = self.config.get("server", {})
        agt = self.config.get("agent", {})
        cols = self.config.get("collectors", {})

        self.poll_interval = agt.get("poll_interval_sec", 10)
        self.cmd_poll_sec = agt.get("command_poll_sec", 5)
        self.hostname = agt.get("hostname") or platform.node()
        self.os_version = f"{platform.system()} {platform.release()} ({platform.version()})"

        self.sender = AgentSender(
            server_url=srv.get("url", "https://localhost"),
            api_key=srv.get("api_key", ""),
            verify_ssl=srv.get("verify_ssl", False),
            timeout_sec=srv.get("timeout_sec", 10),
            buffer_dir=srv.get("buffer_dir", "./data/spool"),
            max_buffer_mb=srv.get("max_buffer_mb", 50),
        )

        sys_cfg = cols.get("system", {})
        self.sys_collector = SystemCollector(
            monitored_services=sys_cfg.get("monitored_services", []),
            top_count=sys_cfg.get("top_processes_count", 10),
        )

        win_cfg = cols.get("winevents", {})
        self.win_collector = WinEventsCollector(
            checkpoint_file=agt.get("checkpoint_file", "./data/winevent_checkpoint.json"),
            target_event_ids=win_cfg.get("target_event_ids"),
            lookback_records=win_cfg.get("lookback_records", 100),
        )

        proc_cfg = cols.get("processes", {})
        self.proc_collector = SuspiciousProcessCollector(
            high_cpu_threshold=proc_cfg.get("high_cpu_threshold_percent", 75.0),
            flag_temp_dirs=proc_cfg.get("flag_temp_directories", True),
            flag_encoded_ps=proc_cfg.get("flag_encoded_powershell", True),
        )

        flow_cfg = cols.get("flows", {})
        self.flow_collector = FlowCollector(
            enabled=flow_cfg.get("enabled", False),
            window_sec=flow_cfg.get("window_sec", 5),
            interface=flow_cfg.get("interface", ""),
        )

        self.executor = ResponseExecutor()

    def start(self) -> None:
        self.running = True
        logger.info("AdaptiveCloud Agent started on host: %s (%s)", self.hostname, self.os_version)

        # Initial host registration check
        reg_result = self.sender.register(self.hostname, self.os_version)
        if reg_result:
            logger.info("Host registered with control plane: %s", reg_result.get("hostname"))

        last_metric_time = 0.0
        last_cmd_time = 0.0

        try:
            while self.running:
                now = time.time()

                # 1. System Metrics & Flow Collection
                if now - last_metric_time >= self.poll_interval:
                    metrics = self.sys_collector.collect()
                    self.sender.post("metrics", metrics)

                    if self.flow_collector.enabled:
                        flows = self.flow_collector.collect()
                        if flows:
                            self.sender.post("flows", flows)

                    last_metric_time = now

                # 2. Windows Security Events & Suspicious Processes
                winevents = self.win_collector.collect()
                if winevents:
                    logger.info("Collected %d Windows Security Event(s)", len(winevents))
                    self.sender.post("events", winevents)

                proc_events = self.proc_collector.collect()
                if proc_events:
                    logger.warning("Detected %d suspicious process anomaly(ies)", len(proc_events))
                    self.sender.post("events", proc_events)

                # 3. Poll Adaptive Commands
                if now - last_cmd_time >= self.cmd_poll_sec:
                    commands = self.sender.get_commands()
                    for cmd in commands:
                        self.executor.execute(cmd)
                    last_cmd_time = now

                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Agent termination requested by user.")
        finally:
            self.stop()

    def stop(self) -> None:
        self.running = False
        if hasattr(self, "flow_collector"):
            self.flow_collector.stop()
        logger.info("AdaptiveCloud Agent shutdown complete.")


if __name__ == "__main__":
    agent = MonitoringAgent()
    agent.start()
