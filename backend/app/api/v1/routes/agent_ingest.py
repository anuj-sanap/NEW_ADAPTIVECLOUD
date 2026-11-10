"""
backend/app/api/v1/routes/agent_ingest.py
High-throughput ingestion endpoints for monitoring agents:
- POST /agents/register: Initial agent handshake
- POST /agents/metrics: Ingest system telemetry and push metric.new
- POST /agents/events: Ingest security audit events and push event.new
- POST /agents/flows: Ingest network flow statistical summaries
- GET  /agents/commands: Command polling for countermeasure execution
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_agent_from_api_key
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import hash_api_key
from app.db.session import get_db
from app.models.flow_feature import FlowFeature
from app.models.host import Host
from app.models.metric import Metric
from app.models.response import ResponseAction
from app.models.security_event import SecurityEvent
from app.services.detection import evaluate_flow_telemetry
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/agents", tags=["agents"])
logger = get_logger("agent_ingest")
settings = get_settings()


class AgentRegisterRequest(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=255)
    os_version: str = Field(..., max_length=128)
    agent_platform: str = Field("windows", max_length=64)
    ip_address: str | None = None


class AgentRegisterResponse(BaseModel):
    host_id: uuid.UUID
    hostname: str
    status: str
    poll_interval_sec: int


class MetricIngestItem(BaseModel):
    ts: datetime
    cpu: float
    mem: float
    disk: float = 0.0
    net_in: float = 0.0
    net_out: float = 0.0
    load: float = 0.0
    proc_count: int = 0
    conn_count: int = 0
    extra: dict[str, Any] | None = None


class EventIngestItem(BaseModel):
    ts: datetime
    source: str = "agent"  # winevent | agent | wazuh
    rule_id: str | None = None
    level: int = 5
    category: str = "security_audit"
    src_ip: str | None = None
    user: str | None = None
    event_id: int | None = None
    raw: dict[str, Any] | None = None


class FlowIngestItem(BaseModel):
    ts: datetime
    features: dict[str, Any]


@router.post(
    "/register",
    response_model=AgentRegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="Agent initial registration and handshake",
)
async def register_agent(
    body: AgentRegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> AgentRegisterResponse:
    now = datetime.now(UTC)

    # Check for existing host by hostname
    stmt = select(Host).where(Host.hostname == body.hostname)
    res = await db.execute(stmt)
    host = res.scalar_one_or_none()

    if host:
        host.os_version = body.os_version
        host.agent_platform = body.agent_platform
        host.ip_address = body.ip_address or host.ip_address
        host.last_seen = now
        host.status = "online"
    else:
        # Create new host record
        host = Host(
            hostname=body.hostname,
            os_version=body.os_version,
            agent_platform=body.agent_platform,
            ip_address=body.ip_address,
            status="online",
            last_seen=now,
            api_key_hash=hash_api_key(x_api_key or settings.AGENT_API_KEY),
        )
        db.add(host)

    await db.commit()
    await db.refresh(host)
    logger.info("Host registration synchronized", host_id=str(host.id), hostname=host.hostname)

    return AgentRegisterResponse(
        host_id=host.id,
        hostname=host.hostname,
        status="online",
        poll_interval_sec=10,
    )


@router.post(
    "/metrics",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest system resource metrics from host",
)
async def ingest_agent_metrics(
    payload: MetricIngestItem | list[MetricIngestItem],
    host: Annotated[Host, Depends(get_agent_from_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    now = datetime.now(UTC)
    host.last_seen = now
    host.status = "online"

    items = [payload] if isinstance(payload, MetricIngestItem) else payload
    saved_count = 0

    for item in items:
        metric = Metric(
            host_id=host.id,
            ts=item.ts,
            cpu=item.cpu,
            mem=item.mem,
            disk=item.disk,
            net_in=item.net_in,
            net_out=item.net_out,
            load=item.load,
            proc_count=item.proc_count,
            conn_count=item.conn_count,
            extra=item.extra or {},
        )
        db.add(metric)
        saved_count += 1

        # Broadcast over WebSocket live stream
        await ws_manager.publish(
            channel="metrics",
            msg_type="metric.new",
            data={
                "host_id": str(host.id),
                "hostname": host.hostname,
                "ts": item.ts.isoformat(),
                "cpu": item.cpu,
                "mem": item.mem,
                "disk": item.disk,
                "net_in": item.net_in,
                "net_out": item.net_out,
                "proc_count": item.proc_count,
                "conn_count": item.conn_count,
            },
        )

    await db.commit()
    logger.debug("Ingested metrics batch", host=host.hostname, count=saved_count)
    return {"status": "accepted", "count": saved_count}


@router.post(
    "/events",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest security events from host",
)
async def ingest_agent_events(
    payload: EventIngestItem | list[EventIngestItem],
    host: Annotated[Host, Depends(get_agent_from_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    now = datetime.now(UTC)
    host.last_seen = now
    host.status = "online"

    items = [payload] if isinstance(payload, EventIngestItem) else payload
    saved_count = 0

    for item in items:
        event = SecurityEvent(
            host_id=host.id,
            ts=item.ts,
            source=item.source,
            rule_id=item.rule_id,
            level=item.level,
            category=item.category,
            src_ip=item.src_ip,
            user=item.user,
            event_id=item.event_id,
            raw=item.raw or {},
        )
        db.add(event)
        saved_count += 1

        # Broadcast over WebSocket live stream
        await ws_manager.publish(
            channel="detections",
            msg_type="event.new",
            data={
                "host_id": str(host.id),
                "hostname": host.hostname,
                "ts": item.ts.isoformat(),
                "source": item.source,
                "rule_id": item.rule_id,
                "level": item.level,
                "category": item.category,
                "src_ip": item.src_ip,
                "user": item.user,
            },
        )

    await db.commit()
    logger.info("Ingested security events batch", host=host.hostname, count=saved_count)
    return {"status": "accepted", "count": saved_count}


@router.post(
    "/flows",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest network flow telemetry summaries",
)
async def ingest_agent_flows(
    payload: FlowIngestItem | list[FlowIngestItem],
    host: Annotated[Host, Depends(get_agent_from_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    items = [payload] if isinstance(payload, FlowIngestItem) else payload
    eval_results = []
    for item in items:
        flow = FlowFeature(
            host_id=host.id,
            ts=item.ts,
            features=item.features,
        )
        db.add(flow)
        # Real-time inference evaluation
        eval_res = await evaluate_flow_telemetry(
            db=db,
            host_id=host.id,
            ts=item.ts,
            features=item.features,
            src_ip=host.ip_address,
        )
        eval_results.append(eval_res)

    await db.commit()
    return {"status": "accepted", "count": len(items), "detections": eval_results}


@router.get(
    "/commands",
    summary="Poll for pending countermeasures queued for this host",
)
async def poll_agent_commands(
    host: Annotated[Host, Depends(get_agent_from_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    # Query pending actions assigned to this host
    stmt = (
        select(ResponseAction)
        .where(
            (ResponseAction.host_id == host.id) | (ResponseAction.host_id.is_(None)),
            ResponseAction.status == "pending",
        )
        .order_by(ResponseAction.created_at.asc())
        .limit(10)
    )
    result = await db.execute(stmt)
    actions = result.scalars().all()

    commands = []
    for a in actions:
        commands.append({
            "id": str(a.id),
            "action": a.action,
            "target": a.target,
        })
        a.status = "executed"

    if commands:
        await db.commit()

    return {"commands": commands}
