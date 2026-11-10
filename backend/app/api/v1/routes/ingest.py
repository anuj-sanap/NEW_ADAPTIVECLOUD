"""
backend/app/api/v1/routes/ingest.py
Telemetry ingest endpoint called by monitored Windows/Linux host agents (X-API-Key auth).
"""
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_agent_from_api_key
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.host import Host
from app.models.metric import Metric
from app.schemas.metric import MetricIngestResponse, MetricPayload
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/ingest", tags=["ingest"])
logger = get_logger("ingest")
settings = get_settings()


async def _trigger_inference(metric_id: str, payload: dict) -> None:
    """Send telemetry snapshot to internal ML service asynchronously."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.ML_SERVICE_URL}/predict",
                json={"metric_id": metric_id, "features": payload},
            )
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("ML inference trigger skipped/failed", metric_id=metric_id, error=str(exc))


@router.post(
    "",
    response_model=MetricIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a metric snapshot from an agent (X-API-Key)",
)
async def ingest_metric(
    payload: MetricPayload,
    background_tasks: BackgroundTasks,
    host: Annotated[Host, Depends(get_agent_from_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MetricIngestResponse:
    now = datetime.now(UTC)

    metric = Metric(
        host_id=host.id,
        ts=payload.collected_at,
        cpu=payload.cpu_percent,
        mem=payload.memory_percent,
        disk=payload.disk_read_bytes_sec + payload.disk_write_bytes_sec,
        net_in=payload.net_bytes_recv_sec,
        net_out=payload.net_bytes_sent_sec,
        load=round(payload.cpu_percent / 100.0, 2),
        proc_count=payload.process_count,
        conn_count=payload.active_connections,
        extra={
            "top_processes": [p.model_dump() for p in payload.top_processes],
            "event_log_errors_1m": payload.event_log_errors_1m,
            "event_log_warnings_1m": payload.event_log_warnings_1m,
            "memory_used_mb": payload.memory_used_mb,
        },
    )
    db.add(metric)

    # Update host heartbeat status
    host.last_seen = now
    host.status = "online"

    await db.flush()

    # Broadcast on WebSocket live channel
    await ws_manager.publish(
        channel="metrics",
        msg_type="event",
        data={
            "host_id": str(host.id),
            "hostname": host.hostname,
            "ts": metric.ts.isoformat(),
            "cpu": metric.cpu,
            "mem": metric.mem,
            "disk": metric.disk,
            "net_in": metric.net_in,
            "net_out": metric.net_out,
            "conn_count": metric.conn_count,
            "proc_count": metric.proc_count,
        },
    )

    # Queue ML inference in background
    background_tasks.add_task(
        _trigger_inference,
        str(metric.id),
        payload.model_dump(mode="json"),
    )

    logger.info("Metric snapshot ingested", metric_id=str(metric.id), host_id=str(host.id))

    return MetricIngestResponse(
        metric_id=metric.id,
        queued_for_inference=True,
    )
