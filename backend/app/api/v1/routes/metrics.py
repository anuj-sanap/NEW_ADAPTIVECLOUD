"""
backend/app/api/v1/routes/metrics.py
Metric query endpoints (analyst+).
"""
import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_role
from app.core.config import get_settings
from app.db.session import get_db
from app.models.metric import Metric
from app.models.user import User
from app.schemas.metric import MetricListResponse, MetricRecord

router = APIRouter(prefix="/metrics", tags=["metrics"])
settings = get_settings()

_analyst = Depends(require_role("admin", "analyst", "viewer"))


@router.get(
    "",
    response_model=MetricListResponse,
    summary="Query stored metrics with optional filters",
)
async def list_metrics(
    _user: Annotated[User, _analyst],
    db: Annotated[AsyncSession, Depends(get_db)],
    agent_id: Optional[uuid.UUID] = Query(None, description="Filter by agent UUID"),
    from_dt: Optional[datetime] = Query(None, alias="from", description="Start datetime (UTC ISO-8601)"),
    to_dt: Optional[datetime] = Query(None, alias="to", description="End datetime (UTC ISO-8601)"),
    limit: int = Query(settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE),
) -> MetricListResponse:
    stmt = select(Metric)

    if agent_id:
        stmt = stmt.where(Metric.agent_id == agent_id)
    if from_dt:
        stmt = stmt.where(Metric.collected_at >= from_dt)
    if to_dt:
        stmt = stmt.where(Metric.collected_at <= to_dt)

    # Total count (without limit)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    # Paginated results
    stmt = stmt.order_by(Metric.collected_at.desc()).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return MetricListResponse(total=total, items=rows)  # type: ignore[arg-type]


@router.get(
    "/latest",
    response_model=list[MetricRecord],
    summary="Get the most recent metric snapshot per agent",
)
async def latest_metrics(
    _user: Annotated[User, _analyst],
    db: Annotated[AsyncSession, Depends(get_db)],
    agent_id: Optional[uuid.UUID] = Query(None),
) -> list[MetricRecord]:
    """
    Returns the single latest MetricRecord for each agent (or just the
    specified agent). Uses a correlated subquery for correctness with partitioned table.
    """
    # Subquery: max collected_at per agent
    subq = (
        select(Metric.agent_id, func.max(Metric.collected_at).label("max_ts"))
        .group_by(Metric.agent_id)
        .subquery()
    )

    stmt = select(Metric).join(
        subq,
        (Metric.agent_id == subq.c.agent_id) & (Metric.collected_at == subq.c.max_ts),
    )
    if agent_id:
        stmt = stmt.where(Metric.agent_id == agent_id)

    result = await db.execute(stmt)
    return result.scalars().all()  # type: ignore[return-value]
