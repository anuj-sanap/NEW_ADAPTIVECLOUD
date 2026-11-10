"""
agent/collectors package: System, Windows Event Log, Suspicious Process, and Network Flow collectors.
"""
from agent.collectors.system import SystemCollector
from agent.collectors.winevents import WinEventsCollector
from agent.collectors.processes import SuspiciousProcessCollector
from agent.collectors.flows import FlowCollector

__all__ = [
    "SystemCollector",
    "WinEventsCollector",
    "SuspiciousProcessCollector",
    "FlowCollector",
]
