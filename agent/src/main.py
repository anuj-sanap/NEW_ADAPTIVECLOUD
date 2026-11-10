"""
agent/src/main.py
Entry point for the Windows monitoring agent.
Reads config from .env, collects metrics on a schedule, and POSTs to backend.
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

# ── Logging setup (before any other imports that might log) ──────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("agent")

# ── Load .env from agent directory ───────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import os
from collector import collector as _collector_mod
from collector import MetricsCollector
from sender import MetricSender

# ── Configuration from environment ───────────────────────────────────────────
AGENT_ID: str = os.environ["AGENT_ID"]          # UUID assigned at registration
AGENT_API_KEY: str = os.environ["AGENT_API_KEY"] # Raw key from POST /agents
BACKEND_URL: str = os.environ["BACKEND_URL"]     # e.g. https://100.64.0.1
COLLECT_INTERVAL: int = int(os.getenv("COLLECT_INTERVAL_SEC", "30"))


def main() -> None:
    logger.info(
        "Agent starting | agent_id=%s backend=%s interval=%ds",
        AGENT_ID, BACKEND_URL, COLLECT_INTERVAL,
    )

    collector = MetricsCollector(agent_id=AGENT_ID)
    sender = MetricSender(backend_url=BACKEND_URL, api_key=AGENT_API_KEY)

    # Warm up CPU counters (psutil needs an initial interval call)
    import psutil
    psutil.cpu_percent(interval=1)

    while True:
        try:
            snapshot = collector.collect()
            ok = sender.send(snapshot)
            if ok:
                logger.info("Snapshot sent | cpu=%.1f%% mem=%.1f%%",
                            snapshot["cpu_percent"], snapshot["memory_percent"])
        except Exception as exc:
            logger.error("Failed to send metric: %s", exc, exc_info=True)

        time.sleep(COLLECT_INTERVAL)


if __name__ == "__main__":
    main()
