"""
backend/app/api/v1/routes/events.py
Security events query endpoint with filtering and pagination.
- GET /events: Search security events from Wazuh SIEM, agent sensors, and Windows Event Logs.
"""
from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_role
from app.core.config import get_settings
from app.db.session import get_db
from app.models.security_event import SecurityEvent
from app.models.user import User
from app.schemas.common import PaginationEnvelope
from app.schemas.event import SecurityEventResponse

router = APIRouter(prefix="/events", tags=["events"])
settings = get_settings()

_viewer = Depends(require_role("admin", "analyst", "viewer"))


@router.get(
    "",
    response_model=PaginationEnvelope[SecurityEventResponse],
    summary="Query security audit and SIEM events with filters and pagination",
)
async def list_security_events(
    _user: Annotated[User, _viewer],
    db: Annotated[AsyncSession, Depends(get_db)],
    host_id: Optional[uuid.UUID] = Query(None, description="Filter by Host UUID"),
    source: Optional[str] = Query(None, description="Filter by source: wazuh | agent | winevent"),
    level: Optional[int] = Query(None, ge=1, le=15, description="Filter by minimum alert severity level"),
    category: Optional[str] = Query(None, description="Filter by event category"),
    src_ip: Optional[str] = Query(None, description="Filter by source IP address"),
    from_dt: Optional[datetime] = Query(None, alias="from", description="Start timestamp (UTC)"),
    to_dt: Optional[datetime] = Query(None, alias="to", description="End timestamp (UTC)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginationEnvelope[SecurityEventResponse]:
    stmt = select(SecurityEvent)

    if host_id:
        stmt = stmt.where(SecurityEvent.host_id == host_id)
    if source:
        stmt = stmt.where(SecurityEvent.source == source)
    if level is not None:
        stmt = stmt.where(SecurityEvent.level >= level)
    if category:
        stmt = stmt.where(SecurityEvent.category == category)
    if src_ip:
        stmt = stmt.where(SecurityEvent.src_ip == src_ip)
    if from_dt:
        stmt = stmt.where(SecurityEvent.ts >= from_dt)
    if to_dt:
        stmt = stmt.where(SecurityEvent.ts <= to_dt)

    # Count total matching rows
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    # Apply pagination and sorting (most recent first)
    offset = (page - 1) * size
    stmt = stmt.order_by(SecurityEvent.ts.desc()).offset(offset).limit(size)
    records = (await db.execute(stmt)).scalars().all()

    items = [
        SecurityEventResponse(
            id=r.id,
            host_id=r.host_id,
            ts=r.ts,
            source=r.source,
            rule_id=r.rule_id,
            level=r.level,
            category=r.category,
            src_ip=r.src_ip,
            user=r.user,
            event_id=r.event_id,
            raw=r.raw,
            created_at=r.created_at,
        )
        for r in records
    ]

    pages = math.ceil(total / size) if size > 0 else 0

    return PaginationEnvelope[SecurityEventResponse](
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )

