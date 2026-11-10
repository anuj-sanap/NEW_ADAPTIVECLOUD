"""
agent/src/collector.py
Windows system telemetry collector using psutil and pywin32.
Collects CPU, memory, disk, network, processes, and Windows Event Log metrics.
"""
from __future__ import annotations

import ctypes
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import psutil

logger = logging.getLogger(__name__)

# Windows Event Log constants (pywin32)
_EVTLOG_AVAILABLE = False
try:
    import win32evtlog
    import win32evtlogutil
    import winerror
    _EVTLOG_AVAILABLE = True
except ImportError:
    logger.warning("pywin32 not available — Event Log collection disabled")

# Event IDs that indicate errors / warnings in System/Security log
_ERROR_TYPES = {win32evtlog.EVENTLOG_ERROR_TYPE} if _EVTLOG_AVAILABLE else set()
_WARNING_TYPES = {win32evtlog.EVENTLOG_WARNING_TYPE} if _EVTLOG_AVAILABLE else set()


class MetricsCollector:
    """
    Collects a point-in-time telemetry snapshot from a Windows host.

    Usage:
        collector = MetricsCollector(agent_id="<uuid>")
        snapshot = collector.collect()
    """

    # Disk/net counters need two readings to compute rates
    _prev_disk: psutil._common.sdiskio | None = None
    _prev_net: psutil._common.snetio | None = None
    _prev_ts: datetime | None = None

    def __init__(self, agent_id: str) -> None:
        self.agent_id = agent_id
        # Prime the counters on first call
        self._prev_disk = psutil.disk_io_counters()
        self._prev_net = psutil.net_io_counters()
        self._prev_ts = datetime.now(UTC)

    def _compute_io_rates(self) -> tuple[float, float, float, float]:
        """
        Compute bytes/sec for disk and network since the last call.
        Returns (disk_read, disk_write, net_sent, net_recv) all in bytes/sec.
        """
        now = datetime.now(UTC)
        cur_disk = psutil.disk_io_counters()
        cur_net = psutil.net_io_counters()

        elapsed = (now - self._prev_ts).total_seconds() if self._prev_ts else 1.0
        if elapsed <= 0:
            elapsed = 1.0

        def _rate(cur: int, prev: int) -> float:
            return max(0.0, (cur - prev) / elapsed)

        disk_read = _rate(cur_disk.read_bytes, self._prev_disk.read_bytes) if self._prev_disk else 0.0
        disk_write = _rate(cur_disk.write_bytes, self._prev_disk.write_bytes) if self._prev_disk else 0.0
        net_sent = _rate(cur_net.bytes_sent, self._prev_net.bytes_sent) if self._prev_net else 0.0
        net_recv = _rate(cur_net.bytes_recv, self._prev_net.bytes_recv) if self._prev_net else 0.0

        self._prev_disk = cur_disk
        self._prev_net = cur_net
        self._prev_ts = now

        return disk_read, disk_write, net_sent, net_recv

    @staticmethod
    def _get_top_processes(n: int = 10) -> list[dict[str, Any]]:
        """
        Return the top N processes by CPU usage.
        Uses a two-call psutil pattern for accurate CPU readings.
        """
        procs: list[dict[str, Any]] = []
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                info = proc.info
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"] or "unknown",
                    "cpu_percent": round(info["cpu_percent"] or 0.0, 2),
                    "memory_mb": round((info["memory_info"].rss if info["memory_info"] else 0) / 1024 / 1024, 2),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return sorted(procs, key=lambda p: p["cpu_percent"], reverse=True)[:n]

    @staticmethod
    def _get_event_log_counts(window_seconds: int = 60) -> tuple[int, int]:
        """
        Count Windows Event Log errors and warnings in the last `window_seconds`.
        Returns (error_count, warning_count).
        Falls back to (0, 0) if pywin32 is unavailable or access is denied.
        """
        if not _EVTLOG_AVAILABLE:
            return 0, 0

        cutoff = datetime.now(UTC) - timedelta(seconds=window_seconds)
        errors = warnings = 0

        try:
            handle = win32evtlog.OpenEventLog(None, "System")
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

            while True:
                records = win32evtlog.ReadEventLog(handle, flags, 0)
                if not records:
                    break
                for rec in records:
                    # TimeGenerated is a pywintypes.datetime — convert to UTC
                    ts = datetime.fromtimestamp(
                        int(rec.TimeGenerated), tz=UTC
                    )
                    if ts < cutoff:
                        # Records are newest-first; stop once past the window
                        win32evtlog.CloseEventLog(handle)
                        return errors, warnings

                    if rec.EventType in _ERROR_TYPES:
                        errors += 1
                    elif rec.EventType in _WARNING_TYPES:
                        warnings += 1

            win32evtlog.CloseEventLog(handle)
        except Exception as exc:
            logger.warning("Event log read failed: %s", exc)

        return errors, warnings

    def collect(self) -> dict[str, Any]:
        """
        Perform a full telemetry snapshot and return it as a dict
        matching the MetricPayload schema (docs/DATA_SCHEMA.md).
        """
        now = datetime.now(UTC)

        # CPU / Memory
        cpu_pct = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()

        # Disk / Net rates
        disk_read, disk_write, net_sent, net_recv = self._compute_io_rates()

        # Connections
        try:
            conns = psutil.net_connections(kind="tcp")
            active_conns = sum(1 for c in conns if c.status == "ESTABLISHED")
        except psutil.AccessDenied:
            active_conns = -1   # -1 signals "access denied" — backend accepts it

        proc_count = len(psutil.pids())
        top_procs = self._get_top_processes()
        err_count, warn_count = self._get_event_log_counts(60)

        return {
            "agent_id": self.agent_id,
            "collected_at": now.isoformat(),
            "cpu_percent": round(cpu_pct, 2),
            "memory_percent": round(mem.percent, 2),
            "memory_used_mb": round(mem.used / 1024 / 1024, 2),
            "disk_read_bytes_sec": round(disk_read, 2),
            "disk_write_bytes_sec": round(disk_write, 2),
            "net_bytes_sent_sec": round(net_sent, 2),
            "net_bytes_recv_sec": round(net_recv, 2),
            "active_connections": max(0, active_conns),
            "process_count": proc_count,
            "top_processes": top_procs,
            "event_log_errors_1m": err_count,
            "event_log_warnings_1m": warn_count,
        }
