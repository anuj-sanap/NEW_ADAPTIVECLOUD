"""
backend/app/api/v1/routes/ingest.py
Metric ingest endpoint called by Windows agents (X-API-Key auth).
"""
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_agent_from_api_key
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.agent import Agent
from app.models.metric import Metric
from app.schemas.metric import MetricIngestResponse, MetricPayload
from app.websocket.manager import ws_manager

router = APIRouter(prefix="/ingest", tags=["ingest"])
logger = get_logger(__name__)
settings = get_settings()


async def _trigger_inference(metric_id: str, payload: dict) -> None:
    """
    Background task: POST the metric snapshot to the ML service for inference.
    Failures are logged but do not affect the HTTP response to the agent.
    """
    if not settings.ML_INFERENCE_ENABLED:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.ML_SERVICE_URL}/predict",
                json={"metric_id": metric_id, "features": payload},
            )
            resp.raise_for_status()
    except Exception as exc:
        logger.warning("ML inference request failed", metric_id=metric_id, error=str(exc))


@router.post(
    "",
    response_model=MetricIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ingest a metric snapshot from a Windows agent",
)
async def ingest_metric(
    payload: MetricPayload,
    background_tasks: BackgroundTasks,
    agent: Annotated[Agent, Depends(get_agent_from_api_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MetricIngestResponse:
    """
    Accept a telemetry snapshot from a registered Windows agent.
    - Validates the payload (Pydantic).
    - Persists the metric to PostgreSQL.
    - Updates agent last_seen + status to online.
    - Broadcasts raw metric over WebSocket channel 'metrics'.
    - Enqueues ML inference as a background task.
    """
    # Guard: agent_id in payload must match the authenticated agent
    if payload.agent_id != agent.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="agent_id in payload does not match authenticated agent",
        )

    now = datetime.now(UTC)

    metric = Metric(
        agent_id=agent.id,
        collected_at=payload.collected_at,
        ingested_at=now,
        cpu_percent=payload.cpu_percent,
        memory_percent=payload.memory_percent,
        memory_used_mb=payload.memory_used_mb,
        disk_read_bytes_sec=payload.disk_read_bytes_sec,
        disk_write_bytes_sec=payload.disk_write_bytes_sec,
        net_bytes_sent_sec=payload.net_bytes_sent_sec,
        net_bytes_recv_sec=payload.net_bytes_recv_sec,
        active_connections=payload.active_connections,
        process_count=payload.process_count,
        top_processes=[p.model_dump() for p in payload.top_processes],
        event_log_errors_1m=payload.event_log_errors_1m,
        event_log_warnings_1m=payload.event_log_warnings_1m,
    )
    db.add(metric)

    # Update agent heartbeat
    agent.last_seen = now
    agent.status = "online"

    await db.flush()

    metric_id_str = str(metric.id)

    # Broadcast to WebSocket clients on "metrics" channel
    await ws_manager.broadcast(
        channel="metrics",
        data=payload.model_dump(mode="json"),
    )

    # Enqueue inference (non-blocking)
    background_tasks.add_task(
        _trigger_inference,
        metric_id_str,
        payload.model_dump(mode="json"),
    )

    logger.info(
        "Metric ingested",
        metric_id=metric_id_str,
        agent_id=str(agent.id),
        label_cpu=payload.cpu_percent,
    )

    return MetricIngestResponse(
        metric_id=metric.id,
        queued_for_inference=settings.ML_INFERENCE_ENABLED,
    )
