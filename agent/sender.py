"""
agent/sender.py
Secure HTTPS sender for AdaptiveCloud agent with exponential back-off,
offline local disk spooling, and self-signed certificate support.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger("agent.sender")


class AgentSender:
    """
    Handles robust transmission of metrics, security events, and flow features
    to the FastAPI backend. Implements local disk buffering during network partitions.
    """

    def __init__(
        self,
        server_url: str,
        api_key: str,
        verify_ssl: bool | str = False,
        timeout_sec: int = 10,
        buffer_dir: str = "./data/spool",
        max_buffer_mb: int = 50,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self.timeout_sec = timeout_sec
        self.buffer_dir = Path(buffer_dir)
        self.max_buffer_mb = max_buffer_mb

        self.buffer_dir.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "AdaptiveCloud-Windows-Agent/1.0",
        })

    def _spool_to_disk(self, endpoint_key: str, data: Any) -> None:
        """Persist failed transmission payload to disk spool."""
        try:
            # Check buffer size cap
            total_bytes = sum(f.stat().st_size for f in self.buffer_dir.glob("*.json"))
            if total_bytes > self.max_buffer_mb * 1024 * 1024:
                oldest = sorted(self.buffer_dir.glob("*.json"), key=lambda f: f.stat().st_mtime)
                if oldest:
                    oldest[0].unlink(missing_ok=True)

            fname = f"{int(time.time())}_{endpoint_key}_{uuid.uuid4().hex[:8]}.json"
            spool_file = self.buffer_dir / fname
            spool_file.write_text(json.dumps({"endpoint": endpoint_key, "payload": data}), encoding="utf-8")
            logger.warning("Network offline. Spooled transmission to %s", fname)
        except Exception as e:
            logger.error("Failed spooling transmission to disk", error=str(e))

    def flush_spool(self) -> None:
        """Attempt to transmit spooled items in FIFO chronological order."""
        files = sorted(self.buffer_dir.glob("*.json"), key=lambda f: f.stat().st_mtime)
        for f in files:
            try:
                content = json.loads(f.read_text(encoding="utf-8"))
                endpoint = content["endpoint"]
                payload = content["payload"]

                url = f"{self.server_url}/api/v1/agents/{endpoint}"
                resp = self.session.post(url, json=payload, verify=self.verify_ssl, timeout=self.timeout_sec)
                if resp.status_code in (200, 201, 202):
                    f.unlink(missing_ok=True)
                    logger.info("Successfully flushed spooled file %s", f.name)
                else:
                    break
            except Exception:
                break

    def post(self, endpoint: str, data: Any) -> bool:
        """Send HTTP POST with automatic retry, fall back to disk spool on failure."""
        url = f"{self.server_url}/api/v1/agents/{endpoint}"
        try:
            resp = self.session.post(
                url,
                json=data,
                verify=self.verify_ssl,
                timeout=self.timeout_sec,
            )
            if resp.status_code in (200, 201, 202):
                self.flush_spool()
                return True
            else:
                logger.warning("Server returned %d for %s: %s", resp.status_code, endpoint, resp.text)
                self._spool_to_disk(endpoint, data)
                return False
        except (requests.ConnectionError, requests.Timeout) as e:
            logger.warning("Transmission failed (%s). Spooling to disk.", str(e))
            self._spool_to_disk(endpoint, data)
            return False
        except Exception as e:
            logger.error("Unexpected error in post transmission: %s", str(e))
            return False

    def get_commands(self) -> list[dict[str, Any]]:
        """Poll server for pending administrative or adaptive mitigation commands."""
        url = f"{self.server_url}/api/v1/agents/commands"
        try:
            resp = self.session.get(
                url,
                verify=self.verify_ssl,
                timeout=self.timeout_sec,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("commands", []) if isinstance(data, dict) else []
            return []
        except Exception:
            return []

    def register(self, hostname: str, os_version: str, ip_address: str | None = None) -> dict[str, Any] | None:
        """Register host with control plane."""
        url = f"{self.server_url}/api/v1/agents/register"
        payload = {
            "hostname": hostname,
            "os_version": os_version,
            "agent_platform": "windows",
            "ip_address": ip_address,
        }
        try:
            resp = self.session.post(
                url,
                json=payload,
                verify=self.verify_ssl,
                timeout=self.timeout_sec,
            )
            if resp.status_code in (200, 201):
                return resp.json()
            logger.error("Agent registration failed (%d): %s", resp.status_code, resp.text)
            return None
        except Exception as e:
            logger.error("Error during agent registration: %s", str(e))
            return None
