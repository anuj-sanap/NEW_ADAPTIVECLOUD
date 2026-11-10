"""
backend/app/api/v1/routes/predictions.py
ML prediction query and training trigger endpoints.
"""
import uuid as uuid_mod
from typing import Annotated, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_role
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.models.prediction import ATTACK_LABELS, Prediction
from app.models.user import User
from app.schemas.prediction import (
    MLNotAvailable,
    MLStatusResponse,
    PredictionListResponse,
    PredictionRecord,
    TrainJobResponse,
)

router = APIRouter(tags=["predictions"])
logger = get_logger(__name__)
settings = get_settings()

_analyst = Depends(require_role("admin", "analyst", "viewer"))
_admin = Depends(require_role("admin"))


@router.get(
    "/predictions",
    response_model=PredictionListResponse | MLNotAvailable,
    summary="Query ML predictions",
)
async def list_predictions(
    _user: Annotated[User, _analyst],
    db: Annotated[AsyncSession, Depends(get_db)],
    agent_id: Optional[UUID] = Query(None),
    label: Optional[str] = Query(None, description="Filter by attack label"),
    limit: int = Query(50, ge=1, le=500),
) -> PredictionListResponse | MLNotAvailable:
    # Check model availability by counting existing predictions
    count_check = await db.execute(select(func.count()).select_from(Prediction))
    if count_check.scalar_one() == 0:
        return MLNotAvailable()

    if label and label not in ATTACK_LABELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid label. Valid: {list(ATTACK_LABELS)}",
        )

    stmt = select(Prediction)
    if agent_id:
        stmt = stmt.where(Prediction.agent_id == agent_id)
    if label:
        stmt = stmt.where(Prediction.label == label)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(Prediction.predicted_at.desc()).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return PredictionListResponse(total=total, items=rows)  # type: ignore[arg-type]


@router.post(
    "/ml/train",
    response_model=TrainJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger model retraining (admin)",
)
async def trigger_training(
    _user: Annotated[User, _admin],
) -> TrainJobResponse:
    """
    Sends a training request to the ML service.
    If the ML service is unavailable, returns 503.
    """
    job_id = uuid_mod.uuid4()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.ML_SERVICE_URL}/train",
                json={"job_id": str(job_id)},
            )
            resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ML service error: {exc.response.text}",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ML service unreachable: {exc}",
        )

    return TrainJobResponse(
        job_id=job_id,
        status="queued",
        message="Training job queued. Poll GET /api/v1/ml/status for progress.",
    )


@router.get(
    "/ml/status",
    response_model=MLStatusResponse,
    summary="Get ML model status",
)
async def ml_status(
    _user: Annotated[User, Depends(require_role("admin", "analyst"))],
) -> MLStatusResponse:
    """
    Proxies the ML service's status endpoint.
    Returns not_available if service is unreachable or no model exists.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ML_SERVICE_URL}/status")
            resp.raise_for_status()
            data = resp.json()
            return MLStatusResponse(**data)
    except Exception as exc:
        logger.warning("ML status check failed", error=str(exc))
        return MLStatusResponse(status="not_available")
