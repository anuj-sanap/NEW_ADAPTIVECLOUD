"""
agent/collectors/flows.py
Low-CPU network flow feature extractor utilizing Scapy and Npcap.
Produces 5-second window aggregation features.
Gracefully deactivates if Npcap or Scapy is absent.
"""
from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("agent.collectors.flows")

_SCAPY_AVAILABLE = False
try:
    from scapy.all import IP, TCP, UDP, AsyncSniffer
    _SCAPY_AVAILABLE = True
except ImportError:
    pass


class FlowCollector:
    """
    Lightweight packet sniffer aggregating TCP/UDP flag rates, volume,
    and port entropy over rolling 5-second time windows.
    """

    def __init__(self, enabled: bool = False, window_sec: int = 5, interface: str = "") -> None:
        self.enabled = enabled and _SCAPY_AVAILABLE
        self.window_sec = window_sec
        self.interface = interface or None
        self._lock = threading.Lock()
        self._sniffer = None

        # Flow counter window state
        self._reset_counters()

        if enabled and not _SCAPY_AVAILABLE:
            logger.info("Scapy library or Npcap packet capture driver not installed. Flow collection disabled.")
        elif self.enabled:
            self._start_sniffer()

    def _reset_counters(self) -> None:
        self.pkt_count = 0
        self.byte_count = 0
        self.tcp_count = 0
        self.udp_count = 0
        self.syn_count = 0
        self.ack_count = 0
        self.rst_count = 0
        self.fin_count = 0
        self.unique_dst_ports: set[int] = set()
        self.unique_dst_ips: set[str] = set()

    def _packet_callback(self, pkt: Any) -> None:
        try:
            with self._lock:
                self.pkt_count += 1
                self.byte_count += len(pkt)

                if pkt.haslayer(IP):
                    self.unique_dst_ips.add(pkt[IP].dst)

                if pkt.haslayer(TCP):
                    self.tcp_count += 1
                    tcp = pkt[TCP]
                    self.unique_dst_ports.add(tcp.dport)
                    flags = str(tcp.flags)
                    if "S" in flags:
                        self.syn_count += 1
                    if "A" in flags:
                        self.ack_count += 1
                    if "R" in flags:
                        self.rst_count += 1
                    if "F" in flags:
                        self.fin_count += 1

                elif pkt.haslayer(UDP):
                    self.udp_count += 1
                    self.unique_dst_ports.add(pkt[UDP].dport)
        except Exception:
            pass

    def _start_sniffer(self) -> None:
        try:
            kwargs = {
                "prn": self._packet_callback,
                "store": False,
                "filter": "ip",
            }
            if self.interface:
                kwargs["iface"] = self.interface

            self._sniffer = AsyncSniffer(**kwargs)
            self._sniffer.start()
            logger.info("Scapy AsyncSniffer active on interface: %s", self.interface or "default")
        except Exception as e:
            logger.warning("Could not initiate Npcap sniffer (Npcap might be missing): %s", e)
            self.enabled = False

    def collect(self) -> dict[str, Any] | None:
        """Extract aggregated flow features for the elapsed time window and reset counters."""
        if not self.enabled:
            return None

        with self._lock:
            features = {
                "packet_rate": round(self.pkt_count / float(self.window_sec), 2),
                "byte_rate": round(self.byte_count / float(self.window_sec), 2),
                "tcp_ratio": round(self.tcp_count / max(1, self.pkt_count), 3),
                "udp_ratio": round(self.udp_count / max(1, self.pkt_count), 3),
                "syn_rate": round(self.syn_count / float(self.window_sec), 2),
                "ack_rate": round(self.ack_count / float(self.window_sec), 2),
                "rst_rate": round(self.rst_count / float(self.window_sec), 2),
                "fin_rate": round(self.fin_count / float(self.window_sec), 2),
                "dst_port_count": len(self.unique_dst_ports),
                "dst_ip_count": len(self.unique_dst_ips),
            }
            self._reset_counters()

        return {
            "ts": datetime.now(UTC).isoformat(),
            "features": features,
        }

    def stop(self) -> None:
        if self._sniffer and self._sniffer.running:
            try:
                self._sniffer.stop()
            except Exception:
                pass
