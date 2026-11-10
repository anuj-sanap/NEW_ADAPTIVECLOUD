"""
backend/tests/test_rca.py
Comprehensive test suite for Root Cause Analysis (RCA) reporting and incident forensics.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_api_key
from app.models.host import Host
from app.models.incident import Incident, IncidentItem
from app.models.metric import Metric
from app.models.security_event import SecurityEvent
from app.services.rca import generate_rca_report


@pytest.mark.asyncio
async def test_rca_report_generation_brute_force(db_session: AsyncSession):
    # 1. Create Host
    host = Host(
        hostname="WORKER-WIN-01",
        ip_address="100.64.0.15",
        os_version="Windows Server 2022 Datacenter",
        agent_platform="windows",
        status="online",
        api_key_hash=hash_api_key("test_key"),
    )
    db_session.add(host)
    await db_session.commit()
    await db_session.refresh(host)

    now = datetime.now(UTC)

    # 2. Add Security Events: Multiple 4625 (failed logons) followed by 4624 (success)
    ev1 = SecurityEvent(
        host_id=host.id,
        ts=now - timedelta(minutes=10),
        source="winevent",
        event_id=4625,
        category="brute_force",
        level=6,
        src_ip="203.0.113.55",
        user="Administrator",
        raw={"target_user": "Administrator", "failure_reason": "BadPassword"},
    )
    ev2 = SecurityEvent(
        host_id=host.id,
        ts=now - timedelta(minutes=8),
        source="winevent",
        event_id=4625,
        category="brute_force",
        level=6,
        src_ip="203.0.113.55",
        user="Administrator",
        raw={"target_user": "Administrator"},
    )
    ev3 = SecurityEvent(
        host_id=host.id,
        ts=now - timedelta(minutes=5),
        source="winevent",
        event_id=4624,
        category="logon",
        level=3,
        src_ip="203.0.113.55",
        user="Administrator",
        raw={"target_user": "Administrator", "logon_type": 3},
    )
    db_session.add_all([ev1, ev2, ev3])
    await db_session.commit()
    await db_session.refresh(ev1)
    await db_session.refresh(ev2)
    await db_session.refresh(ev3)

    # 3. Add Metric spike
    m1 = Metric(
        host_id=host.id,
        ts=now - timedelta(minutes=9),
        cpu=92.5,
        mem=68.0,
        disk=45.0,
        net_in=1000,
        net_out=2000,
        load=4.0,
        proc_count=120,
        conn_count=85,
    )
    db_session.add(m1)

    # 4. Create Incident & link items
    incident = Incident(
        title="Repeated RDP/SMB logon failures followed by successful session",
        severity="critical",
        status="open",
        description="Potential brute-force attack detected on worker",
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)

    item1 = IncidentItem(
        incident_id=incident.id,
        item_type="security_event",
        item_id=ev1.id,
    )
    item2 = IncidentItem(
        incident_id=incident.id,
        item_type="security_event",
        item_id=ev2.id,
    )
    item3 = IncidentItem(
        incident_id=incident.id,
        item_type="security_event",
        item_id=ev3.id,
    )
    db_session.add_all([item1, item2, item3])
    await db_session.commit()

    # 5. Generate RCA Report
    rca = await generate_rca_report(db_session, incident.id)

    assert rca is not None
    assert rca.incident_id == incident.id
    assert "Brute-Force" in rca.probable_cause
    assert rca.evidence is not None
    assert rca.evidence.get("confidence", 0) >= 0.85
    assert len(rca.source_ips) >= 1
    assert rca.source_ips[0]["ip"] == "203.0.113.55"
    assert "WORKER-WIN-01" in rca.affected_hosts

    # Verify plain-English summary and Windows remediation
    evidence = rca.evidence
    actions = evidence.get("recommended_actions", [])
    assert any("Firewall" in a or "account" in a.lower() for a in actions)
    assert len(evidence.get("plain_english_summary", "")) > 20


@pytest.mark.asyncio
async def test_rca_api_routes(client: AsyncClient, admin_token: str, db_session: AsyncSession):
    # Setup test incident
    incident = Incident(
        title="Unauthorized Port Sweep Detected",
        severity="high",
        status="investigating",
        description="Suspicious port scanning behavior detected",
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)

    headers = {"Authorization": f"Bearer {admin_token}"}

    # GET /api/v1/rca/{incident_id}
    res = await client.get(f"/api/v1/rca/{incident.id}", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["incident_id"] == str(incident.id)
    assert "probable_cause" in data
    assert "recommended_actions" in data
    assert "plain_english_summary" in data

    # POST /api/v1/rca/{incident_id}/regenerate
    res_regen = await client.post(f"/api/v1/rca/{incident.id}/regenerate", headers=headers)
    assert res_regen.status_code == 200
    data_regen = res_regen.json()
    assert data_regen["incident_id"] == str(incident.id)

    # 404 for non-existent incident
    fake_id = uuid.uuid4()
    res_404 = await client.get(f"/api/v1/rca/{fake_id}", headers=headers)
    assert res_404.status_code == 404
