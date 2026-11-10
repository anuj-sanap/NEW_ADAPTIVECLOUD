"""
backend/tests/test_winevents.py
Unit tests for Windows Event Log XML parser in agent/collectors/winevents.py.
Validates extraction of EventID, RecordID, Timestamp, User, Source IP,
category classification, and error resilience.
"""
import sys
from pathlib import Path

# Add project root to sys.path so agent can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agent.collectors.winevents import parse_event_xml


SAMPLE_4625_XML = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Microsoft-Windows-Security-Auditing" />
    <EventID>4625</EventID>
    <Version>0</Version>
    <Level>0</Level>
    <Task>12544</Task>
    <Opcode>0</Opcode>
    <Keywords>0x8010000000000000</Keywords>
    <TimeCreated SystemTime="2026-11-10T14:15:22.123456Z" />
    <EventRecordID>98214</EventRecordID>
    <Channel>Security</Channel>
    <Computer>gcp-worker-01</Computer>
    <Security />
  </System>
  <EventData>
    <Data Name="SubjectUserSid">S-1-5-18</Data>
    <Data Name="SubjectUserName">WORKER$</Data>
    <Data Name="TargetUserName">Administrator</Data>
    <Data Name="Status">0xc000006d</Data>
    <Data Name="SubStatus">0xc000006a</Data>
    <Data Name="LogonType">3</Data>
    <Data Name="LogonProcessName">NtLmSsp</Data>
    <Data Name="AuthenticationPackageName">NTLM</Data>
    <Data Name="WorkstationName">ATTACKER-PC</Data>
    <Data Name="IpAddress">198.51.100.45</Data>
    <Data Name="IpPort">51234</Data>
  </EventData>
</Event>"""


SAMPLE_4624_XML = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <EventID>4624</EventID>
    <TimeCreated SystemTime="2026-11-10T14:16:00.000000Z" />
    <EventRecordID>98215</EventRecordID>
  </System>
  <EventData>
    <Data Name="TargetUserName">SecOpsUser</Data>
    <Data Name="IpAddress">100.64.0.10</Data>
  </EventData>
</Event>"""


SAMPLE_4672_XML = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <EventID>4672</EventID>
    <TimeCreated SystemTime="2026-11-10T14:17:00.000000Z" />
    <EventRecordID>98216</EventRecordID>
  </System>
  <EventData>
    <Data Name="SubjectUserName">SuperAdmin</Data>
    <Data Name="PrivilegeList">SeSecurityPrivilege&#x0d;&#x0a;&#x09;SeBackupPrivilege</Data>
  </EventData>
</Event>"""


SAMPLE_4688_XML = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <EventID>4688</EventID>
    <TimeCreated SystemTime="2026-11-10T14:18:00.000000Z" />
    <EventRecordID>98217</EventRecordID>
  </System>
  <EventData>
    <Data Name="NewProcessName">C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe</Data>
    <Data Name="CommandLine">powershell.exe -enc SQBFAFgA</Data>
    <Data Name="SubjectUserName">CompromisedUser</Data>
  </EventData>
</Event>"""


SAMPLE_4720_XML = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <EventID>4720</EventID>
    <TimeCreated SystemTime="2026-11-10T14:19:00.000000Z" />
    <EventRecordID>98218</EventRecordID>
  </System>
  <EventData>
    <Data Name="TargetUserName">backdoor_admin</Data>
    <Data Name="SubjectUserName">LocalAdmin</Data>
  </EventData>
</Event>"""


def test_parse_event_4625_logon_failure():
    result = parse_event_xml(SAMPLE_4625_XML)
    assert result is not None
    assert result["event_id"] == 4625
    assert result["record_id"] == 98214
    assert result["source"] == "winevent"
    assert result["category"] == "authentication_failure"
    assert result["level"] == 10
    assert result["src_ip"] == "198.51.100.45"
    assert result["user"] == "Administrator"
    assert result["raw"]["LogonType"] == "3"


def test_parse_event_4624_logon_success():
    result = parse_event_xml(SAMPLE_4624_XML)
    assert result is not None
    assert result["event_id"] == 4624
    assert result["record_id"] == 98215
    assert result["category"] == "logon_success"
    assert result["level"] == 3
    assert result["user"] == "SecOpsUser"
    assert result["src_ip"] == "100.64.0.10"


def test_parse_event_4672_privilege_escalation():
    result = parse_event_xml(SAMPLE_4672_XML)
    assert result is not None
    assert result["event_id"] == 4672
    assert result["category"] == "privilege_escalation"
    assert result["level"] == 8
    assert result["user"] == "SuperAdmin"


def test_parse_event_4688_process_creation():
    result = parse_event_xml(SAMPLE_4688_XML)
    assert result is not None
    assert result["event_id"] == 4688
    assert result["category"] == "process_creation"
    assert result["level"] == 5
    assert "CommandLine" in result["raw"]
    assert "-enc" in result["raw"]["CommandLine"]


def test_parse_event_4720_account_created():
    result = parse_event_xml(SAMPLE_4720_XML)
    assert result is not None
    assert result["event_id"] == 4720
    assert result["category"] == "account_manipulation"
    assert result["level"] == 9
    assert result["user"] == "backdoor_admin"


def test_parse_event_xml_malformed():
    assert parse_event_xml("not valid xml <<< >>>") is None
    assert parse_event_xml("<Empty></Empty>") is None
    assert parse_event_xml("") is None

