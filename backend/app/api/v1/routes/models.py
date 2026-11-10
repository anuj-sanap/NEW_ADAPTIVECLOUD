"""
backend/app/api/v1/routes/models.py
API endpoints for ML model registry management, performance metrics, and model activation.
- GET  /models: List registered ML models and current statuses.
- GET  /models/{id}/metrics: Inspect formal evaluation metrics for a model.
- POST /models/{id}/activate: Promote a model to active deployment (Admin only).
"""
from __future__ import annotations

import uuid
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_role
from app.db.session import get_db
from app.models.ml import MLModel
from app.models.user import User
from app.schemas.ml import MLModelMetricsResponse, MLModelResponse
from ml.inference.predictor import flow_predictor

router = APIRouter(prefix="/models", tags=["models"])

_viewer = Depends(require_role("admin", "analyst", "viewer"))
_admin = Depends(require_role("admin"))


@router.get(
    "",
    response_model=list[MLModelResponse],
    summary="List registered ML models and deployment status",
)
async def list_models(
    _user: Annotated[User, _viewer],
    db: Annotated[AsyncSession, Depends(get_db)],
    task: Optional[str] = Query(None, description="Filter by task: anomaly | attack_classification"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: active | candidate | retired"),
) -> list[MLModelResponse]:
    stmt = select(MLModel).order_by(MLModel.name.asc(), MLModel.version.desc())
    if task:
        stmt = stmt.where(MLModel.task == task)
    if status_filter:
        stmt = stmt.where(MLModel.status == status_filter)

    records = (await db.execute(stmt)).scalars().all()
    return [MLModelResponse.model_validate(r) for r in records]


@router.get(
    "/{model_id}/metrics",
    response_model=MLModelMetricsResponse,
    summary="Retrieve evaluation metrics for an ML model",
)
async def get_model_metrics(
    model_id: uuid.UUID,
    _user: Annotated[User, _viewer],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MLModelMetricsResponse:
    stmt = select(MLModel).where(MLModel.id == model_id)
    res = await db.execute(stmt)
    model = res.scalar_one_or_none()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    return MLModelMetricsResponse(
        model_id=model.id,
        name=model.name,
        task=model.task,
        version=model.version,
        metrics=model.metrics,
    )


@router.post(
    "/{model_id}/activate",
    response_model=dict[str, Any],
    summary="Promote an ML model to active production deployment (Admin only)",
)
async def activate_model(
    model_id: uuid.UUID,
    _admin_user: Annotated[User, _admin],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    stmt = select(MLModel).where(MLModel.id == model_id)
    res = await db.execute(stmt)
    target = res.scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    # Deactivate all existing models of the same task
    deactivate_stmt = select(MLModel).where(MLModel.task == target.task, MLModel.status == "active")
    active_res = await db.execute(deactivate_stmt)
    currently_active = active_res.scalars().all()
    for m in currently_active:
        m.status = "candidate"

    # Promote target model
    target.status = "active"
    await db.commit()
    await db.refresh(target)

    # Hot-reload in memory
    if target.task == "attack_classification":
        flow_predictor.reload(classifier_name=target.name)
    elif target.task == "anomaly":
        flow_predictor.reload()

    return {
        "status": "activated",
        "model_id": str(target.id),
        "name": target.name,
        "task": target.task,
        "version": target.version,
    }

