"""
backend/app/services/wazuh_ingestor.py
Asynchronous ingestion worker for Wazuh SIEM alerts.
Tails alerts.json, normalizes Wazuh alerts to SecurityEvent domain models,
maps alert signatures to attack labels (brute_force, ddos, port_scan,
unauthorized_access, suspicious_process), handles log rotation,
deduplicates alerts, and broadcasts event.new on the WebSocket live stream.
"""
from __future__ import annotations

import asyncio
import json
import os
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.host import Host
from app.models.security_event import SecurityEvent
from app.services.classification import classify_and_correlate
from app.websocket.manager import ws_manager

logger = get_logger("wazuh_ingestor")
settings = get_settings()

# Allowed attack labels defined in project specification
ATTACK_LABELS = {
    "benign",
    "brute_force",
    "ddos",
    "port_scan",
    "unauthorized_access",
    "suspicious_process",
}


def map_wazuh_to_attack_label(alert: dict[str, Any]) -> str:
    """
    Map Wazuh rule IDs, groups, and descriptions to standardized attack labels:
    - brute_force
    - ddos
    - port_scan
    - unauthorized_access
    - suspicious_process
    - benign (fallback)
    """
    rule = alert.get("rule", {})
    rule_id = str(rule.get("id", ""))
    groups = [g.lower() for g in rule.get("groups", [])]
    desc = str(rule.get("description", "")).lower()

    # Direct custom rule mappings
    if rule_id == "100001" or "brute_force" in groups or "authentication_failed" in groups or "4625" in desc:
        return "brute_force"
    if rule_id == "100005" or "port_scan" in groups or "recon" in groups or "scan" in desc:
        return "port_scan"
    if rule_id in ("100002", "100003") or "privilege_escalation" in groups or "account_change" in groups or "4672" in desc or "4720" in desc:
        return "unauthorized_access"
    if rule_id == "100004" or "suspicious_process" in groups or "execution" in groups or "4688" in desc:
        return "suspicious_process"
    if "ddos" in groups or "dos" in groups or "flood" in desc:
        return "ddos"

    # Category matching
    if any(k in desc for k in ["failed login", "bad password", "logon failure"]):
        return "brute_force"
    if any(k in desc for k in ["privilege", "new user", "administrator", "elevat"]):
        return "unauthorized_access"
    if any(k in desc for k in ["powershell", "cmd.exe", "whoami", "script", "suspicious"]):
        return "suspicious_process"

    return "benign"


def parse_wazuh_alert(raw_line: str) -> dict[str, Any] | None:
    """Parse and normalize a single JSON line from alerts.json."""
    line = raw_line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
        if not isinstance(data, dict):
            return None
    except json.JSONDecodeError:
        logger.warning("Failed to decode Wazuh alert JSON line", line=line[:100])
        return None

    rule = data.get("rule", {})
    agent = data.get("agent", {})
    win_data = data.get("data", {}).get("win", {})
    event_data = win_data.get("eventdata", {})
    system_data = win_data.get("system", {})

    rule_id = str(rule.get("id", ""))
    level = int(rule.get("level", 1))
    category = map_wazuh_to_attack_label(data)

    # Extract source IP
    src_ip = (
        event_data.get("ipAddress")
        or data.get("data", {}).get("srcip")
        or data.get("srcip")
        or None
    )
    if src_ip in ("-", "::1", "127.0.0.1", ""):
        src_ip = None

    # Extract user
    user = (
        event_data.get("targetUserName")
        or data.get("data", {}).get("dstuser")
        or data.get("data", {}).get("srcuser")
        or None
    )

    # Extract event ID
    event_id = None
    raw_eid = system_data.get("eventID") or event_data.get("eventID")
    if raw_eid:
        try:
            event_id = int(raw_eid)
        except (ValueError, TypeError):
            pass

    # Extract timestamp
    ts_str = data.get("timestamp") or data.get("@timestamp")
    ts = datetime.now(UTC)
    if ts_str:
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            pass

    alert_id = str(data.get("id") or f"{rule_id}_{ts.isoformat()}_{src_ip}")

    return {
        "alert_id": alert_id,
        "ts": ts,
        "rule_id": rule_id,
        "level": level,
        "category": category,
        "src_ip": src_ip,
        "user": user,
        "event_id": event_id,
        "agent_name": agent.get("name"),
        "agent_id": agent.get("id"),
        "raw": data,
    }


class WazuhAlertTailer:
    """
    Asynchronous file tailer for alerts.json with rotation resilience
    and duplicate suppression.
    """

    def __init__(self, alerts_path: str, dedupe_size: int = 1000):
        self.alerts_path = Path(alerts_path)
        self.dedupe_size = dedupe_size
        self._seen_ids: deque[str] = deque(maxlen=dedupe_size)
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def is_duplicate(self, alert_id: str) -> bool:
        if alert_id in self._seen_ids:
            return True
        self._seen_ids.append(alert_id)
        return False

    async def _resolve_host_id(self, agent_name: str | None, agent_ip: str | None) -> Any:
        async with AsyncSessionLocal() as db:
            if agent_name:
                stmt = select(Host).where(Host.hostname == agent_name)
                res = await db.execute(stmt)
                host = res.scalar_one_or_none()
                if host:
                    return host.id

            # Fallback to any active host or first host
            stmt = select(Host.id).limit(1)
            res = await db.execute(stmt)
            fallback_id = res.scalar_one_or_none()
            return fallback_id

    async def process_alert(self, parsed: dict[str, Any]) -> None:
        if self.is_duplicate(parsed["alert_id"]):
            return

        host_id = await self._resolve_host_id(parsed.get("agent_name"), parsed.get("src_ip"))
        if not host_id:
            logger.debug("No registered host for Wazuh alert; skipping persistence", agent=parsed.get("agent_name"))
            return

        async with AsyncSessionLocal() as db:
            event = SecurityEvent(
                host_id=host_id,
                ts=parsed["ts"],
                source="wazuh",
                rule_id=parsed["rule_id"],
                level=parsed["level"],
                category=parsed["category"],
                src_ip=parsed["src_ip"],
                user=parsed["user"],
                event_id=parsed["event_id"],
                raw=parsed["raw"],
            )
            db.add(event)
            await db.commit()

        # Broadcast via WebSocket
        await ws_manager.publish(
            channel="detections",
            msg_type="event.new",
            data={
                "host_id": str(host_id),
                "source": "wazuh",
                "rule_id": parsed["rule_id"],
                "level": parsed["level"],
                "category": parsed["category"],
                "src_ip": parsed["src_ip"],
                "user": parsed["user"],
                "ts": parsed["ts"].isoformat(),
            },
        )

        # Correlate into classification and incidents if significant security event
        if parsed["level"] >= 8 or parsed["category"] in ("brute_force", "unauthorized_access", "suspicious_process", "port_scan", "ddos"):
            try:
                async with AsyncSessionLocal() as db:
                    await classify_and_correlate(
                        db=db,
                        host_id=host_id,
                        ts=parsed["ts"],
                        event_data={
                            "event_id": parsed["event_id"],
                            "category": parsed["category"],
                            "raw": parsed["raw"],
                        },
                        src_ip=parsed["src_ip"],
                    )
            except Exception as e:
                logger.error("Failed correlating Wazuh alert into incident", error=str(e))

        logger.info(
            "Wazuh alert ingested and published",
            rule_id=parsed["rule_id"],
            category=parsed["category"],
            level=parsed["level"],
            src_ip=parsed["src_ip"],
        )

    async def run(self) -> None:
        self._running = True
        logger.info("Wazuh alert tailer worker started", path=str(self.alerts_path))

        file_obj = None
        current_inode = None

        while self._running:
            try:
                if not self.alerts_path.exists():
                    await asyncio.sleep(2)
                    continue

                stat = self.alerts_path.stat()
                # Check file rotation (inode change on Linux, or size shrink)
                if file_obj is None or getattr(stat, "st_ino", None) != current_inode or file_obj.tell() > stat.st_size:
                    if file_obj:
                        file_obj.close()
                    file_obj = open(self.alerts_path, "r", encoding="utf-8", errors="replace")
                    current_inode = getattr(stat, "st_ino", None)
                    # Seek to end on initial open if file is large to avoid replaying gigabytes
                    file_obj.seek(0, os.SEEK_END)

                line = file_obj.readline()
                if line:
                    parsed = parse_wazuh_alert(line)
                    if parsed:
                        await self.process_alert(parsed)
                else:
                    await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in Wazuh tailer loop", error=str(e))
                await asyncio.sleep(2)

        if file_obj:
            file_obj.close()
        logger.info("Wazuh alert tailer worker stopped")

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run())

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass


wazuh_tailer = WazuhAlertTailer(settings.WAZUH_ALERTS_PATH)

