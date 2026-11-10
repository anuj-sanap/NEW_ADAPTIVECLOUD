"""
backend/app/api/v1/routes/detections.py
API endpoints for querying unsupervised anomaly detections.
- GET /detections: Query detection scores with filters and pagination.
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
from app.db.session import get_db
from app.models.detection import Detection
from app.models.user import User
from app.schemas.common import PaginationEnvelope
from app.schemas.detection import DetectionResponse

router = APIRouter(prefix="/detections", tags=["detections"])

_viewer = Depends(require_role("admin", "analyst", "viewer"))


@router.get(
    "",
    response_model=PaginationEnvelope[DetectionResponse],
    summary="Query anomaly detections with filters and pagination",
)
async def list_detections(
    _user: Annotated[User, _viewer],
    db: Annotated[AsyncSession, Depends(get_db)],
    host_id: Optional[uuid.UUID] = Query(None, description="Filter by Host UUID"),
    is_attack: Optional[bool] = Query(None, description="Filter by attack flag"),
    status: Optional[str] = Query(None, description="Filter by status (open, investigating, resolved)"),
    from_dt: Optional[datetime] = Query(None, alias="from", description="Start timestamp (UTC)"),
    to_dt: Optional[datetime] = Query(None, alias="to", description="End timestamp (UTC)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginationEnvelope[DetectionResponse]:
    stmt = select(Detection)

    if host_id:
        stmt = stmt.where(Detection.host_id == host_id)
    if is_attack is not None:
        stmt = stmt.where(Detection.is_attack == is_attack)
    if status:
        stmt = stmt.where(Detection.status == status)
    if from_dt:
        stmt = stmt.where(Detection.ts >= from_dt)
    if to_dt:
        stmt = stmt.where(Detection.ts <= to_dt)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * size
    stmt = stmt.order_by(Detection.ts.desc()).offset(offset).limit(size)
    records = (await db.execute(stmt)).scalars().all()

    items = [DetectionResponse.model_validate(r) for r in records]
    pages = math.ceil(total / size) if size > 0 else 0

    return PaginationEnvelope[DetectionResponse](
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )
