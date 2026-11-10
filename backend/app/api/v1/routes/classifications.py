"""
backend/app/api/v1/routes/classifications.py
API endpoints for querying multi-class threat classifications.
- GET /classifications: Query threat classifications with filters and pagination.
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
from app.models.detection import Classification
from app.models.user import User
from app.schemas.common import PaginationEnvelope
from app.schemas.detection import ClassificationResponse

router = APIRouter(prefix="/classifications", tags=["classifications"])

_viewer = Depends(require_role("admin", "analyst", "viewer"))


@router.get(
    "",
    response_model=PaginationEnvelope[ClassificationResponse],
    summary="Query threat classifications with filters and pagination",
)
async def list_classifications(
    _user: Annotated[User, _viewer],
    db: Annotated[AsyncSession, Depends(get_db)],
    host_id: Optional[uuid.UUID] = Query(None, description="Filter by Host UUID"),
    label: Optional[str] = Query(None, description="Filter by attack label"),
    detection_id: Optional[uuid.UUID] = Query(None, description="Filter by parent Detection UUID"),
    from_dt: Optional[datetime] = Query(None, alias="from", description="Start timestamp (UTC)"),
    to_dt: Optional[datetime] = Query(None, alias="to", description="End timestamp (UTC)"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginationEnvelope[ClassificationResponse]:
    stmt = select(Classification)

    if host_id:
        stmt = stmt.where(Classification.host_id == host_id)
    if label:
        stmt = stmt.where(Classification.label == label)
    if detection_id:
        stmt = stmt.where(Classification.detection_id == detection_id)
    if from_dt:
        stmt = stmt.where(Classification.ts >= from_dt)
    if to_dt:
        stmt = stmt.where(Classification.ts <= to_dt)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * size
    stmt = stmt.order_by(Classification.ts.desc()).offset(offset).limit(size)
    records = (await db.execute(stmt)).scalars().all()

    items = [ClassificationResponse.model_validate(r) for r in records]
    pages = math.ceil(total / size) if size > 0 else 0

    return PaginationEnvelope[ClassificationResponse](
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )

