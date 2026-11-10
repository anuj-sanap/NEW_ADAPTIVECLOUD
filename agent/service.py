"""
agent/service.py
Windows Service wrapper for AdaptiveCloud Monitoring Agent using pywin32.
Enables background service execution, automatic startup on boot, and recovery on crash.
Usage:
    python agent/service.py install
    python agent/service.py start
    python agent/service.py stop
    python agent/service.py remove
"""
from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

# Add project root to sys.path so imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logger = logging.getLogger("agent.service")

_WIN32SERVICE_AVAILABLE = False
if sys.platform == "win32":
    try:
        import servicemanager
        import win32event
        import win32service
        import win32serviceutil
        _WIN32SERVICE_AVAILABLE = True
    except ImportError:
        pass


if _WIN32SERVICE_AVAILABLE:

    class AdaptiveCloudService(win32serviceutil.ServiceFramework):
        _svc_name_ = "AdaptiveCloudAgent"
        _svc_display_name_ = "AdaptiveCloud Security & Monitoring Agent"
        _svc_description_ = "Collects system metrics, Windows Security events, and executes automated countermeasures."

        def __init__(self, args):
            super().__init__(args)
            self.stop_event = win32event.CreateEvent(None, 0, 0, None)
            self.agent = None
            self.thread = None

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.stop_event)
            if self.agent:
                self.agent.stop()

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            from agent.agent import MonitoringAgent

            self.agent = MonitoringAgent()
            self.thread = threading.Thread(target=self.agent.start, daemon=True)
            self.thread.start()

            # Wait until service stop requested
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)

            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STOPPED,
                (self._svc_name_, ""),
            )

    def main():
        if len(sys.argv) == 1:
            servicemanager.Initialize()
            servicemanager.PrepareToHostSingle(AdaptiveCloudService)
            servicemanager.StartServiceCtrlDispatcher()
        else:
            win32serviceutil.HandleCommandLine(AdaptiveCloudService)

else:
    def main():
        print("pywin32 service components are only available on Windows platforms.")
        from agent.agent import MonitoringAgent
        agent = MonitoringAgent()
        agent.start()


if __name__ == "__main__":
    main()
