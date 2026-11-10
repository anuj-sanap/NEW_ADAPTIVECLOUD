"""
backend/tests/test_hosts_events_api.py
Tests for host management, telemetry downsampling, security events querying,
and agent ingestion endpoints.
"""
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_api_key
from app.models.host import Host

settings = get_settings()


@pytest.mark.asyncio
async def test_agent_registration_and_metrics_ingest(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    # 1. Register agent
    reg_resp = await client.post(
        "/api/v1/agents/register",
        json={
            "hostname": "gcp-worker-test",
            "os_version": "Windows Server 2022 Datacenter",
            "agent_platform": "windows",
            "ip_address": "100.64.0.50",
        },
        headers={"X-API-Key": settings.AGENT_API_KEY},
    )
    assert reg_resp.status_code == 200
    host_info = reg_resp.json()
    host_id = host_info["host_id"]
    assert host_info["hostname"] == "gcp-worker-test"
    assert host_info["status"] == "online"

    # 2. Ingest metric batch
    now = datetime.now(UTC)
    metric_resp = await client.post(
        "/api/v1/agents/metrics",
        json=[
            {
                "ts": now.isoformat(),
                "cpu": 25.5,
                "mem": 60.0,
                "disk": 45.0,
                "net_in": 1024.0,
                "net_out": 2048.0,
                "proc_count": 120,
                "conn_count": 15,
            },
            {
                "ts": (now + timedelta(seconds=10)).isoformat(),
                "cpu": 35.5,
                "mem": 62.0,
                "disk": 45.0,
                "net_in": 2048.0,
                "net_out": 4096.0,
                "proc_count": 122,
                "conn_count": 18,
            },
        ],
        headers={"X-API-Key": settings.AGENT_API_KEY},
    )
    assert metric_resp.status_code == 202
    assert metric_resp.json()["count"] == 2

    # 3. Query host list
    hosts_resp = await client.get(
        "/api/v1/hosts",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert hosts_resp.status_code == 200
    hosts_data = hosts_resp.json()
    assert len(hosts_data) >= 1
    target = next((h for h in hosts_data if h["hostname"] == "gcp-worker-test"), None)
    assert target is not None
    assert target["status"] == "online"

    # 4. Query host detail
    host_detail_resp = await client.get(
        f"/api/v1/hosts/{host_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert host_detail_resp.status_code == 200
    assert host_detail_resp.json()["id"] == host_id

    # 5. Query host raw metrics
    metrics_query_resp = await client.get(
        f"/api/v1/hosts/{host_id}/metrics?resolution=raw",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert metrics_query_resp.status_code == 200
    mq_data = metrics_query_resp.json()
    assert mq_data["resolution"] == "raw"
    assert mq_data["total_points"] == 2

    # 6. Query host downsampled metrics (1m)
    metrics_downsample_resp = await client.get(
        f"/api/v1/hosts/{host_id}/metrics?resolution=1m",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert metrics_downsample_resp.status_code == 200
    ds_data = metrics_downsample_resp.json()
    assert ds_data["resolution"] == "1m"
    assert ds_data["total_points"] == 1
    # Average of 25.5 and 35.5 is 30.5
    assert ds_data["metrics"][0]["cpu"] == 30.5


@pytest.mark.asyncio
async def test_security_events_query_and_filtering(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    # Create host
    host = Host(
        hostname="worker-event-test",
        os_version="Windows Server 2022",
        agent_platform="windows",
        status="online",
        api_key_hash=hash_api_key(settings.AGENT_API_KEY),
    )
    db_session.add(host)
    await db_session.commit()
    await db_session.refresh(host)

    # Ingest event via agent API
    now = datetime.now(UTC)
    evt_resp = await client.post(
        "/api/v1/agents/events",
        json=[
            {
                "ts": now.isoformat(),
                "source": "winevent",
                "rule_id": "4625",
                "level": 10,
                "category": "brute_force",
                "src_ip": "198.51.100.22",
                "user": "Administrator",
                "event_id": 4625,
            },
            {
                "ts": (now + timedelta(seconds=1)).isoformat(),
                "source": "wazuh",
                "rule_id": "100004",
                "level": 10,
                "category": "suspicious_process",
                "user": "test_user",
                "event_id": 4688,
            },
        ],
        headers={"X-API-Key": settings.AGENT_API_KEY},
    )
    assert evt_resp.status_code == 202

    # Query all events
    events_resp = await client.get(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert events_resp.status_code == 200
    ev_data = events_resp.json()
    assert ev_data["total"] >= 2
    assert "items" in ev_data

    # Query with category filter
    filtered_resp = await client.get(
        "/api/v1/events?category=brute_force",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert filtered_resp.status_code == 200
    filtered_data = filtered_resp.json()
    assert filtered_data["total"] == 1
    assert filtered_data["items"][0]["category"] == "brute_force"
    assert filtered_data["items"][0]["src_ip"] == "198.51.100.22"


@pytest.mark.asyncio
async def test_host_status_offline_calculation(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    # Host last seen 5 minutes ago (> 90 seconds threshold)
    stale_time = datetime.now(UTC) - timedelta(minutes=5)
    host = Host(
        hostname="stale-worker",
        os_version="Windows Server 2022",
        agent_platform="windows",
        status="online",  # DB might say online, but dynamic calculation should return offline
        last_seen=stale_time,
        api_key_hash=hash_api_key(settings.AGENT_API_KEY),
    )
    db_session.add(host)
    await db_session.commit()
    await db_session.refresh(host)

    resp = await client.get(
        f"/api/v1/hosts/{host.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "offline"
