"""
agent/collectors/flows.py
Low-CPU network flow feature extractor utilizing Scapy and Npcap.
Produces 5-second window aggregation matching AdaptiveCloud's 28 canonical flow features.
Gracefully deactivates if Npcap or Scapy is absent.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("agent.collectors.flows")

_SCAPY_AVAILABLE = False
try:
    from scapy.all import IP, TCP, AsyncSniffer
    _SCAPY_AVAILABLE = True
except ImportError:
    pass


def _calc_stats(values: list[float | int]) -> tuple[float, float, float, float]:
    """Calculate (min, max, mean, std) for a list of numbers."""
    if not values:
        return 0.0, 0.0, 0.0, 0.0
    val_min = float(min(values))
    val_max = float(max(values))
    val_mean = float(sum(values) / len(values))
    if len(values) > 1:
        variance = sum((x - val_mean) ** 2 for x in values) / (len(values) - 1)
        val_std = math.sqrt(variance)
    else:
        val_std = 0.0
    return val_min, val_max, round(val_mean, 2), round(val_std, 2)


def _calc_iat(timestamps: list[float]) -> tuple[float, float, float, float]:
    """Calculate inter-arrival times stats in microseconds."""
    if len(timestamps) < 2:
        return 0.0, 0.0, 0.0, 0.0
    # timestamps are in epoch seconds; delta in microseconds
    deltas = [(timestamps[i] - timestamps[i - 1]) * 1_000_000 for i in range(1, len(timestamps))]
    return _calc_stats(deltas)


class FlowCollector:
    """
    Packet sniffer aggregating bidirectional flow volume, packet lengths,
    IAT, and TCP flags over rolling 5-second windows to match the 28 canonical features.
    """

    def __init__(self, enabled: bool = False, window_sec: int = 5, interface: str = "") -> None:
        self.enabled = enabled and _SCAPY_AVAILABLE
        self.window_sec = window_sec
        self.interface = interface or None
        self._lock = threading.Lock()
        self._sniffer = None
        self._window_start = time.time()

        self._reset_counters()

        if enabled and not _SCAPY_AVAILABLE:
            logger.info("Scapy library or Npcap packet capture driver not installed. Flow collection disabled.")
        elif self.enabled:
            self._start_sniffer()

    def _reset_counters(self) -> None:
        self._window_start = time.time()
        self.fwd_pkts = 0
        self.bwd_pkts = 0
        self.fwd_bytes = 0
        self.bwd_bytes = 0
        self.fwd_lens: list[int] = []
        self.bwd_lens: list[int] = []
        self.all_lens: list[int] = []
        self.all_times: list[float] = []
        self.fwd_times: list[float] = []
        self.bwd_times: list[float] = []
        self.fin_cnt = 0
        self.syn_cnt = 0
        self.rst_cnt = 0
        self.psh_cnt = 0
        self.ack_cnt = 0
        self.urg_cnt = 0

    def _packet_callback(self, pkt: Any) -> None:
        try:
            now = time.time()
            with self._lock:
                pkt_len = len(pkt)
                self.all_lens.append(pkt_len)
                self.all_times.append(now)

                # Heuristic direction: assume outbound/initiator is forward
                is_fwd = True
                if pkt.haslayer(IP):
                    # Check if packet is inbound or outbound relative to local
                    is_fwd = not pkt[IP].dst.startswith("10.") and not pkt[IP].dst.startswith("192.168.")

                if is_fwd:
                    self.fwd_pkts += 1
                    self.fwd_bytes += pkt_len
                    self.fwd_lens.append(pkt_len)
                    self.fwd_times.append(now)
                else:
                    self.bwd_pkts += 1
                    self.bwd_bytes += pkt_len
                    self.bwd_lens.append(pkt_len)
                    self.bwd_times.append(now)

                if pkt.haslayer(TCP):
                    flags = str(pkt[TCP].flags)
                    if "F" in flags:
                        self.fin_cnt += 1
                    if "S" in flags:
                        self.syn_cnt += 1
                    if "R" in flags:
                        self.rst_cnt += 1
                    if "P" in flags:
                        self.psh_cnt += 1
                    if "A" in flags:
                        self.ack_cnt += 1
                    if "U" in flags:
                        self.urg_cnt += 1
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
        """Extract the exact 28 canonical flow features for the elapsed time window."""
        if not self.enabled:
            return None

        now = time.time()
        with self._lock:
            duration_sec = max(0.001, now - self._window_start)
            duration_us = int(duration_sec * 1_000_000)

            tot_pkts = self.fwd_pkts + self.bwd_pkts
            tot_bytes = self.fwd_bytes + self.bwd_bytes

            f_min, f_max, f_mean, f_std = _calc_stats(self.fwd_lens)
            b_min, b_max, b_mean, b_std = _calc_stats(self.bwd_lens)
            _, _, all_mean, _ = _calc_stats(self.all_lens)

            iat_min, iat_max, iat_mean, iat_std = _calc_iat(self.all_times)
            _, _, fwd_iat_mean, _ = _calc_iat(self.fwd_times)
            _, _, bwd_iat_mean, _ = _calc_iat(self.bwd_times)

            features = {
                "flow_duration": duration_us,
                "tot_fwd_pkts": self.fwd_pkts,
                "tot_bwd_pkts": self.bwd_pkts,
                "totlen_fwd_pkts": self.fwd_bytes,
                "totlen_bwd_pkts": self.bwd_bytes,
                "fwd_pkt_len_max": f_max,
                "fwd_pkt_len_min": f_min,
                "fwd_pkt_len_mean": f_mean,
                "fwd_pkt_len_std": f_std,
                "bwd_pkt_len_max": b_max,
                "bwd_pkt_len_min": b_min,
                "bwd_pkt_len_mean": b_mean,
                "bwd_pkt_len_std": b_std,
                "flow_byts_s": round(tot_bytes / duration_sec, 2),
                "flow_pkts_s": round(tot_pkts / duration_sec, 2),
                "flow_iat_mean": iat_mean,
                "flow_iat_std": iat_std,
                "flow_iat_max": iat_max,
                "flow_iat_min": iat_min,
                "fwd_iat_mean": fwd_iat_mean,
                "bwd_iat_mean": bwd_iat_mean,
                "fin_flag_cnt": self.fin_cnt,
                "syn_flag_cnt": self.syn_cnt,
                "rst_flag_cnt": self.rst_cnt,
                "psh_flag_cnt": self.psh_cnt,
                "ack_flag_cnt": self.ack_cnt,
                "urg_flag_cnt": self.urg_cnt,
                "pkt_len_mean": all_mean,
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
