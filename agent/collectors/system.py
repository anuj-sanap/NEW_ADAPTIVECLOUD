"""
agent/collectors/system.py
Collects detailed host resource metrics and Windows services telemetry via psutil.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import UTC, datetime
from typing import Any

import psutil

logger = logging.getLogger("agent.collectors.system")


class SystemCollector:
    """
    Samples CPU, memory, swap, disk I/O, network I/O, sockets,
    top running processes, and status of specified Windows Services.
    """

    def __init__(self, monitored_services: list[str] | None = None, top_count: int = 10) -> None:
        self.monitored_services = monitored_services or []
        self.top_count = top_count
        self._prev_disk = psutil.disk_io_counters()
        self._prev_net = psutil.net_io_counters()
        self._prev_ts = datetime.now(UTC)

    def _compute_rates(self) -> tuple[float, float, float, float]:
        """Compute disk read/write and net rx/tx in bytes per second."""
        now = datetime.now(UTC)
        elapsed = (now - self._prev_ts).total_seconds()
        if elapsed <= 0:
            elapsed = 1.0

        cur_disk = psutil.disk_io_counters()
        cur_net = psutil.net_io_counters()

        def rate(cur: int, prev: int) -> float:
            return max(0.0, float(cur - prev) / elapsed)

        disk_read = rate(cur_disk.read_bytes, self._prev_disk.read_bytes) if (cur_disk and self._prev_disk) else 0.0
        disk_write = rate(cur_disk.write_bytes, self._prev_disk.write_bytes) if (cur_disk and self._prev_disk) else 0.0
        net_in = rate(cur_net.bytes_recv, self._prev_net.bytes_recv) if (cur_net and self._prev_net) else 0.0
        net_out = rate(cur_net.bytes_sent, self._prev_net.bytes_sent) if (cur_net and self._prev_net) else 0.0

        self._prev_disk = cur_disk
        self._prev_net = cur_net
        self._prev_ts = now

        return disk_read, disk_write, net_in, net_out

    def _get_top_processes(self) -> list[dict[str, Any]]:
        procs: list[dict[str, Any]] = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_info"]):
            try:
                info = p.info
                rss = (info["memory_info"].rss if info["memory_info"] else 0) / 1024 / 1024
                procs.append({
                    "pid": info["pid"],
                    "name": info["name"] or "unknown",
                    "cpu_percent": round(info["cpu_percent"] or 0.0, 1),
                    "memory_mb": round(rss, 1),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
        return procs[: self.top_count]

    def _get_network_connections(self) -> tuple[int, list[dict[str, Any]]]:
        established = 0
        listening: list[dict[str, Any]] = []
        try:
            conns = psutil.net_connections(kind="inet")
            for c in conns:
                if c.status == psutil.CONN_ESTABLISHED:
                    established += 1
                elif c.status == psutil.CONN_LISTEN:
                    listening.append({
                        "fd": c.fd,
                        "family": int(c.family),
                        "type": int(c.type),
                        "port": c.laddr.port if c.laddr else None,
                        "ip": c.laddr.ip if c.laddr else None,
                    })
        except (psutil.AccessDenied, PermissionError):
            logger.debug("Access denied reading net_connections")
        return established, listening

    def _get_windows_services(self) -> dict[str, str]:
        """Check status of monitored services on Windows via win_service_iter."""
        statuses: dict[str, str] = {}
        if sys.platform != "win32" or not hasattr(psutil, "win_service_iter"):
            return statuses

        try:
            target_set = {s.lower() for s in self.monitored_services}
            for svc in psutil.win_service_iter():
                try:
                    name = svc.name()
                    if name.lower() in target_set:
                        statuses[name] = svc.status()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            logger.warning("Error inspecting Windows services", error=str(e))
        return statuses

    def collect(self) -> dict[str, Any]:
        """Generate complete telemetry dictionary matching backend metrics schema."""
        now = datetime.now(UTC)
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk usage for system drive
        try:
            root_drive = os.environ.get("SystemDrive", "C:") + "\\" if sys.platform == "win32" else "/"
            disk_usage = psutil.disk_usage(root_drive)
            disk_pct = disk_usage.percent
        except Exception:
            disk_pct = 0.0

        disk_read, disk_write, net_in, net_out = self._compute_rates()
        established_conns, listening_ports = self._get_network_connections()
        top_processes = self._get_top_processes()
        service_statuses = self._get_windows_services()

        # Approximate load
        try:
            load = os.getloadavg()[0] if hasattr(os, "getloadavg") else round(cpu_pct / 100.0, 2)
        except Exception:
            load = round(cpu_pct / 100.0, 2)

        return {
            "ts": now.isoformat(),
            "cpu": round(cpu_pct, 2),
            "mem": round(mem.percent, 2),
            "disk": round(disk_read + disk_write, 2),
            "net_in": round(net_in, 2),
            "net_out": round(net_out, 2),
            "load": round(load, 2),
            "proc_count": len(psutil.pids()),
            "conn_count": established_conns,
            "extra": {
                "memory_used_mb": round(mem.used / 1024 / 1024, 1),
                "memory_total_mb": round(mem.total / 1024 / 1024, 1),
                "swap_percent": swap.percent,
                "disk_percent": disk_pct,
                "top_processes": top_processes,
                "listening_ports_count": len(listening_ports),
                "windows_services": service_statuses,
            },
        }
