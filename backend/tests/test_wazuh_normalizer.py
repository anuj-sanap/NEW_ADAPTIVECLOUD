"""
backend/tests/test_wazuh_normalizer.py
Unit tests for Wazuh alert parsing, attack label mapping, and deduplication
in backend/app/services/wazuh_ingestor.py.
"""

from app.services.wazuh_ingestor import (
    ATTACK_LABELS,
    WazuhAlertTailer,
    map_wazuh_to_attack_label,
    parse_wazuh_alert,
)


SAMPLE_BRUTE_FORCE_ALERT = {
    "timestamp": "2026-11-10T14:20:00.000+0000",
    "rule": {
        "level": 10,
        "description": "AdaptiveCloud: Multiple Windows logon failures (Event 4625) from same IP within 60s - Possible RDP brute force",
        "id": "100001",
        "groups": ["windows", "adaptivecloud", "brute_force"],
    },
    "agent": {
        "id": "001",
        "name": "gcp-worker-01",
        "ip": "100.64.0.5",
    },
    "data": {
        "win": {
            "eventdata": {
                "ipAddress": "198.51.100.77",
                "targetUserName": "Administrator",
            },
            "system": {
                "eventID": "4625",
            },
        },
    },
    "id": "alert-brute-001",
}


SAMPLE_PRIV_ESCALATION_ALERT = {
    "timestamp": "2026-11-10T14:21:00.000+0000",
    "rule": {
        "level": 8,
        "description": "AdaptiveCloud: Special privileges assigned to new logon session (Event 4672)",
        "id": "100002",
        "groups": ["windows", "unauthorized_access", "privilege_escalation"],
    },
    "agent": {
        "id": "001",
        "name": "gcp-worker-01",
    },
    "data": {
        "win": {
            "eventdata": {
                "targetUserName": "EvilUser",
            },
            "system": {
                "eventID": "4672",
            },
        },
    },
    "id": "alert-priv-002",
}


SAMPLE_PROCESS_ALERT = {
    "timestamp": "2026-11-10T14:22:00.000+0000",
    "rule": {
        "level": 10,
        "description": "AdaptiveCloud: Suspicious process spawned from Temp/Downloads or with encoded command (Event 4688)",
        "id": "100004",
        "groups": ["windows", "suspicious_process", "execution"],
    },
    "agent": {
        "id": "001",
        "name": "gcp-worker-01",
    },
    "data": {
        "win": {
            "eventdata": {
                "targetUserName": "victim_user",
            },
            "system": {
                "eventID": "4688",
            },
        },
    },
    "id": "alert-proc-003",
}


SAMPLE_PORT_SCAN_ALERT = {
    "timestamp": "2026-11-10T14:23:00.000+0000",
    "rule": {
        "level": 8,
        "description": "AdaptiveCloud: Rapid inbound connection attempts - Port scan indicator",
        "id": "100005",
        "groups": ["windows", "port_scan", "recon"],
    },
    "agent": {"id": "001", "name": "gcp-worker-01"},
    "data": {"srcip": "203.0.113.88"},
    "id": "alert-scan-004",
}


SAMPLE_BENIGN_ALERT = {
    "timestamp": "2026-11-10T14:24:00.000+0000",
    "rule": {
        "level": 3,
        "description": "Windows logon success",
        "id": "60106",
        "groups": ["windows"],
    },
    "agent": {"id": "001", "name": "gcp-worker-01"},
    "id": "alert-benign-005",
}


def test_map_wazuh_attack_labels():
    assert map_wazuh_to_attack_label(SAMPLE_BRUTE_FORCE_ALERT) == "brute_force"
    assert map_wazuh_to_attack_label(SAMPLE_PRIV_ESCALATION_ALERT) == "unauthorized_access"
    assert map_wazuh_to_attack_label(SAMPLE_PROCESS_ALERT) == "suspicious_process"
    assert map_wazuh_to_attack_label(SAMPLE_PORT_SCAN_ALERT) == "port_scan"
    assert map_wazuh_to_attack_label(SAMPLE_BENIGN_ALERT) == "benign"

    # Ensure all mapped labels belong to standardized set
    for alert in [
        SAMPLE_BRUTE_FORCE_ALERT,
        SAMPLE_PRIV_ESCALATION_ALERT,
        SAMPLE_PROCESS_ALERT,
        SAMPLE_PORT_SCAN_ALERT,
        SAMPLE_BENIGN_ALERT,
    ]:
        label = map_wazuh_to_attack_label(alert)
        assert label in ATTACK_LABELS


def test_parse_wazuh_alert_line():
    import json

    line = json.dumps(SAMPLE_BRUTE_FORCE_ALERT)
    parsed = parse_wazuh_alert(line)

    assert parsed is not None
    assert parsed["alert_id"] == "alert-brute-001"
    assert parsed["rule_id"] == "100001"
    assert parsed["level"] == 10
    assert parsed["category"] == "brute_force"
    assert parsed["src_ip"] == "198.51.100.77"
    assert parsed["user"] == "Administrator"
    assert parsed["event_id"] == 4625
    assert parsed["agent_name"] == "gcp-worker-01"


def test_wazuh_tailer_deduplication():
    tailer = WazuhAlertTailer("/tmp/fake_alerts.json", dedupe_size=5)

    assert tailer.is_duplicate("alert-1") is False
    assert tailer.is_duplicate("alert-1") is True  # Duplicate suppressed
    assert tailer.is_duplicate("alert-2") is False
    assert tailer.is_duplicate("alert-2") is True


def test_parse_wazuh_alert_empty_or_invalid():
    assert parse_wazuh_alert("") is None
    assert parse_wazuh_alert("    \n") is None
    assert parse_wazuh_alert("not json") is None
    assert parse_wazuh_alert("[]") is None
