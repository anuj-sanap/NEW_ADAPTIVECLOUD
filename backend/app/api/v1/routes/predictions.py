"""
backend/app/api/v1/routes/predictions.py
Endpoints for threat and resource failure predictions.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.db.session import get_db
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import PredictionResponse
from app.services.threat_prediction import generate_threat_forecasts

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("", response_model=list[PredictionResponse], summary="List predictive forecasts")
async def list_predictions(
    host_id: Optional[uuid.UUID] = Query(None, description="Filter by host ID"),
    kind: Optional[str] = Query(None, description="Filter by kind: threat | cpu | memory | disk | service"),
    min_probability: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum forecast probability"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Prediction]:
    stmt = select(Prediction).order_by(desc(Prediction.ts))

    if host_id:
        stmt = stmt.where(Prediction.host_id == host_id)
    if kind:
        stmt = stmt.where(Prediction.kind == kind)
    if min_probability is not None:
        stmt = stmt.where(Prediction.probability >= min_probability)

    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post("/evaluate/{host_id}", summary="Trigger threat forecasting evaluation for host")
async def evaluate_threat_predictions(
    host_id: uuid.UUID,
    horizon_min: int = Query(15, description="Forward forecast horizon in minutes"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await generate_threat_forecasts(db=db, host_id=host_id, horizon_min=horizon_min)
    return result
