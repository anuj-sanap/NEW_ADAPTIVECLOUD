"""
agent/collectors/winevents.py
Windows Security Event Log reader and parser.
Monitors critical security events (4625, 4624, 4672, 4688, 4720) using pywin32 or wevtutil.
Checkpoints highest processed EventRecordID to local disk to prevent duplicate event ingestion.
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("agent.collectors.winevents")

# XML namespace for Windows Event Log XML schema
NS = {"ns": "http://schemas.microsoft.com/win/2004/08/events/event"}


def parse_event_xml(xml_text: str) -> dict[str, Any] | None:
    """
    Parses a single Windows Event XML string into a normalized security event dict.
    Extracts EventID, RecordID, Timestamp, User, Source IP, Category, and Details.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    system = root.find("ns:System", NS)
    if system is None:
        return None

    event_id_el = system.find("ns:EventID", NS)
    if event_id_el is None or not event_id_el.text:
        return None

    try:
        event_id = int(event_id_el.text)
    except ValueError:
        return None

    record_el = system.find("ns:EventRecordID", NS)
    record_id = int(record_el.text) if (record_el is not None and record_el.text) else 0

    time_created = system.find("ns:TimeCreated", NS)
    ts = time_created.attrib.get("SystemTime") if time_created is not None else datetime.now(UTC).isoformat()

    # Extract all EventData Data items as key/value pairs
    data_dict: dict[str, str] = {}
    event_data = root.find("ns:EventData", NS)
    if event_data is not None:
        for data in event_data.findall("ns:Data", NS):
            name = data.attrib.get("Name")
            val = data.text or ""
            if name:
                data_dict[name] = val

    src_ip = data_dict.get("IpAddress") or data_dict.get("WorkstationName")
    if src_ip in ("-", "127.0.0.1", "::1"):
        src_ip = None

    target_user = (
        data_dict.get("TargetUserName")
        or data_dict.get("SubjectUserName")
        or data_dict.get("TargetUserSid")
    )
    if target_user in ("-", "SYSTEM", "LOCAL SERVICE", "NETWORK SERVICE"):
        target_user = None

    # Threat category and severity level mappings
    category = "security_audit"
    level = 5

    if event_id == 4625:
        category = "authentication_failure"
        level = 10
    elif event_id == 4624:
        category = "logon_success"
        level = 3
    elif event_id == 4672:
        category = "privilege_escalation"
        level = 8
    elif event_id == 4688:
        category = "process_creation"
        level = 5
    elif event_id == 4720:
        category = "account_manipulation"
        level = 9

    return {
        "event_id": event_id,
        "record_id": record_id,
        "ts": ts,
        "source": "winevent",
        "rule_id": str(event_id),
        "level": level,
        "category": category,
        "src_ip": src_ip,
        "user": target_user,
        "raw": data_dict,
    }


class WinEventsCollector:
    """
    Tails Windows Security Log, checks records against target Event IDs,
    and maintains an on-disk cursor checkpoint.
    """

    def __init__(
        self,
        checkpoint_file: str = "./data/winevent_checkpoint.json",
        target_event_ids: list[int] | None = None,
        lookback_records: int = 100,
    ) -> None:
        self.checkpoint_file = Path(checkpoint_file)
        self.target_event_ids = target_event_ids or [4624, 4625, 4672, 4688, 4720]
        self.lookback_records = lookback_records
        self.last_record_id = self._load_checkpoint()

    def _load_checkpoint(self) -> int:
        if self.checkpoint_file.exists():
            try:
                data = json.loads(self.checkpoint_file.read_text(encoding="utf-8"))
                return int(data.get("last_record_id", 0))
            except Exception as e:
                logger.warning("Could not read event checkpoint, resetting to 0", error=str(e))
        return 0

    def _save_checkpoint(self, record_id: int) -> None:
        try:
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            self.checkpoint_file.write_text(
                json.dumps({"last_record_id": record_id, "updated_at": datetime.now(UTC).isoformat()}),
                encoding="utf-8",
            )
            self.last_record_id = record_id
        except Exception as e:
            logger.error("Failed saving event checkpoint", error=str(e))

    def _query_wevtutil(self) -> list[dict[str, Any]]:
        """Query Security log via wevtutil XML export."""
        id_query = " or ".join([f"EventID={eid}" for eid in self.target_event_ids])
        xpath = f"*[System[({id_query}) and EventRecordID > {self.last_record_id}]]"

        cmd = [
            "wevtutil",
            "qe",
            "Security",
            f"/q:{xpath}",
            "/f:xml",
            f"/c:{self.lookback_records}",
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                logger.debug("wevtutil returned non-zero code %d: %s", res.returncode, res.stderr)
                return []
            raw_xml = res.stdout.strip()
            if not raw_xml:
                return []

            # Wrap in root element if multiple events returned
            wrapped = f"<Events>{raw_xml}</Events>"
            root = ET.fromstring(wrapped)
            events: list[dict[str, Any]] = []
            max_record = self.last_record_id

            for event_node in root.findall("ns:Event", NS):
                event_str = ET.tostring(event_node, encoding="utf-8").decode("utf-8")
                parsed = parse_event_xml(event_str)
                if parsed:
                    events.append(parsed)
                    if parsed["record_id"] > max_record:
                        max_record = parsed["record_id"]

            if max_record > self.last_record_id:
                self._save_checkpoint(max_record)

            return events
        except FileNotFoundError:
            logger.debug("wevtutil not available on this platform")
            return []
        except Exception as e:
            logger.warning("Error querying wevtutil", error=str(e))
            return []

    def collect(self) -> list[dict[str, Any]]:
        """Collect and parse new security events since last checkpoint."""
        if sys.platform != "win32":
            return []
        return self._query_wevtutil()
