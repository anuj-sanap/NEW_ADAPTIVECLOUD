"""
backend/app/api/v1/routes/hosts.py
Host management and historical telemetry query endpoints.
- GET /hosts: List registered monitored hosts with dynamic status derived from last_seen.
- GET /hosts/{id}: Detail metadata for a specific host.
- GET /hosts/{id}/metrics: Time-series resource metrics with time-range filtering and downsampling.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_role
from app.db.session import get_db
from app.models.host import Host
from app.models.metric import Metric
from app.models.user import User
from app.schemas.host import HostMetricsResponse, HostResponse, MetricPoint

router = APIRouter(prefix="/hosts", tags=["hosts"])

_viewer = Depends(require_role("admin", "analyst", "viewer"))

ONLINE_THRESHOLD_SECONDS = 90


def compute_host_status(last_seen: datetime | None) -> str:
    """Return 'online' if heartbeated within ONLINE_THRESHOLD_SECONDS, else 'offline'."""
    if not last_seen:
        return "offline"
    now = datetime.now(UTC)
    ts = last_seen if last_seen.tzinfo is not None else last_seen.replace(tzinfo=UTC)
    delta = (now - ts).total_seconds()
    return "online" if delta <= ONLINE_THRESHOLD_SECONDS else "offline"


@router.get(
    "",
    response_model=list[HostResponse],
    summary="List all registered hosts with dynamic health status",
)
async def list_hosts(
    _user: Annotated[User, _viewer],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[HostResponse]:
    stmt = select(Host).order_by(Host.hostname.asc())
    result = await db.execute(stmt)
    hosts = result.scalars().all()

    response: list[HostResponse] = []
    for h in hosts:
        dyn_status = compute_host_status(h.last_seen)
        response.append(
            HostResponse(
                id=h.id,
                hostname=h.hostname,
                os_version=h.os_version,
                agent_platform=h.agent_platform,
                ip_address=h.ip_address,
                status=dyn_status,
                last_seen=h.last_seen,
                is_active=h.is_active,
                created_at=h.created_at,
                updated_at=h.updated_at,
            )
        )
    return response


@router.get(
    "/{host_id}",
    response_model=HostResponse,
    summary="Retrieve host detail",
)
async def get_host(
    host_id: uuid.UUID,
    _user: Annotated[User, _viewer],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HostResponse:
    stmt = select(Host).where(Host.id == host_id)
    result = await db.execute(stmt)
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host '{host_id}' not found",
        )

    return HostResponse(
        id=host.id,
        hostname=host.hostname,
        os_version=host.os_version,
        agent_platform=host.agent_platform,
        ip_address=host.ip_address,
        status=compute_host_status(host.last_seen),
        last_seen=host.last_seen,
        is_active=host.is_active,
        created_at=host.created_at,
        updated_at=host.updated_at,
    )


@router.get(
    "/{host_id}/metrics",
    response_model=HostMetricsResponse,
    summary="Query host historical telemetry with optional downsampling",
)
async def get_host_metrics(
    host_id: uuid.UUID,
    _user: Annotated[User, _viewer],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_dt: Optional[datetime] = Query(None, alias="from", description="Start timestamp (UTC)"),
    to_dt: Optional[datetime] = Query(None, alias="to", description="End timestamp (UTC)"),
    resolution: Literal["raw", "1m", "5m", "1h"] = Query("raw", description="Aggregation bucket"),
    limit: int = Query(1000, ge=1, le=5000, description="Max raw points to return"),
) -> HostMetricsResponse:
    # Verify host exists
    host_stmt = select(Host.id).where(Host.id == host_id)
    host_res = await db.execute(host_stmt)
    if not host_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host '{host_id}' not found",
        )

    stmt = select(Metric).where(Metric.host_id == host_id)
    if from_dt:
        stmt = stmt.where(Metric.ts >= from_dt)
    if to_dt:
        stmt = stmt.where(Metric.ts <= to_dt)
    stmt = stmt.order_by(Metric.ts.asc())

    if resolution == "raw":
        stmt = stmt.limit(limit)
        res = await db.execute(stmt)
        records = res.scalars().all()
        points = [
            MetricPoint(
                ts=m.ts,
                cpu=m.cpu,
                mem=m.mem,
                disk=m.disk,
                net_in=m.net_in,
                net_out=m.net_out,
                load=m.load,
                proc_count=m.proc_count,
                conn_count=m.conn_count,
                extra=m.extra,
            )
            for m in records
        ]
        return HostMetricsResponse(
            host_id=host_id,
            resolution="raw",
            total_points=len(points),
            from_dt=from_dt,
            to_dt=to_dt,
            metrics=points,
        )

    # Resolution downsampling in Python (database-agnostic)
    bucket_seconds = {"1m": 60, "5m": 300, "1h": 3600}[resolution]
    res = await db.execute(stmt)
    records = res.scalars().all()

    buckets: dict[int, list[Metric]] = defaultdict(list)
    for m in records:
        ts_aware = m.ts if m.ts.tzinfo is not None else m.ts.replace(tzinfo=UTC)
        epoch = int(ts_aware.timestamp())
        bucket_key = (epoch // bucket_seconds) * bucket_seconds
        buckets[bucket_key].append(m)

    downsampled_points: list[MetricPoint] = []
    for bucket_key in sorted(buckets.keys()):
        items = buckets[bucket_key]
        n = len(items)
        avg_cpu = sum(x.cpu for x in items) / n
        avg_mem = sum(x.mem for x in items) / n
        avg_disk = sum(x.disk for x in items) / n
        avg_net_in = sum(x.net_in for x in items) / n
        avg_net_out = sum(x.net_out for x in items) / n
        avg_load = sum(x.load for x in items) / n
        avg_proc = int(round(sum(x.proc_count for x in items) / n))
        avg_conn = int(round(sum(x.conn_count for x in items) / n))

        downsampled_points.append(
            MetricPoint(
                ts=datetime.fromtimestamp(bucket_key, tz=UTC),
                cpu=round(avg_cpu, 2),
                mem=round(avg_mem, 2),
                disk=round(avg_disk, 2),
                net_in=round(avg_net_in, 2),
                net_out=round(avg_net_out, 2),
                load=round(avg_load, 2),
                proc_count=avg_proc,
                conn_count=avg_conn,
                extra={"bucket_count": n},
            )
        )

    return HostMetricsResponse(
        host_id=host_id,
        resolution=resolution,
        total_points=len(downsampled_points),
        from_dt=from_dt,
        to_dt=to_dt,
        metrics=downsampled_points,
    )
