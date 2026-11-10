"""
backend/app/api/v1/routes/learning.py
Endpoints for active learning human feedback, statistical drift detection,
controlled retraining triggers, and Champion/Challenger promotion gates.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.ml import DriftEvent, FeedbackLabel, RetrainingJob
from app.models.user import User
from app.schemas.learning import (
    DriftCheckResponse,
    DriftEventResponse,
    FeedbackCreate,
    FeedbackResponse,
    PromotionResponse,
    RetrainingJobResponse,
    RetrainRequest,
)
from app.services.learning import (
    execute_drift_check,
    promote_candidate_model,
    record_analyst_feedback,
    reject_candidate_model,
    trigger_retraining_pipeline,
)

router = APIRouter(prefix="/learning", tags=["learning"])

_analyst = Depends(require_role("admin", "analyst"))
_admin = Depends(require_role("admin"))


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED, summary="Submit analyst ground truth feedback")
async def submit_feedback(
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = _analyst,
) -> FeedbackLabel:
    try:
        fb = await record_analyst_feedback(db, analyst_id=current_user.id, payload=payload)
        return fb
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/drift", response_model=list[DriftEventResponse], summary="List detected feature/concept drift events")
async def list_drift_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DriftEvent]:
    stmt = select(DriftEvent).order_by(desc(DriftEvent.created_at)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post("/drift/check", response_model=DriftCheckResponse, summary="Trigger statistical drift analysis across feature streams")
async def run_drift_check_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = _analyst,
) -> DriftCheckResponse:
    result = await execute_drift_check(db)
    return DriftCheckResponse(**result)


@router.get("/jobs", response_model=list[RetrainingJobResponse], summary="List controlled model retraining jobs")
async def list_retraining_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[RetrainingJob]:
    stmt = select(RetrainingJob).order_by(desc(RetrainingJob.created_at)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post("/retrain", response_model=RetrainingJobResponse, status_code=status.HTTP_202_ACCEPTED, summary="Trigger controlled model retraining pipeline (Admin)")
async def trigger_retraining(
    request: RetrainRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = _admin,
) -> RetrainingJob:
    job = await trigger_retraining_pipeline(
        db=db,
        triggered_by=f"admin:{current_user.username}",
        force=request.force,
        replay_ratio=request.replay_ratio,
    )
    return job


@router.post("/jobs/{job_id}/promote", response_model=PromotionResponse, summary="Promote candidate model to active champion (Admin)")
async def promote_model_endpoint(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = _admin,
) -> PromotionResponse:
    try:
        res = await promote_candidate_model(db, job_id=job_id, user_id=current_user.id)
        return PromotionResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/jobs/{job_id}/reject", response_model=dict[str, Any], summary="Reject candidate model and maintain existing champion (Admin)")
async def reject_model_endpoint(
    job_id: uuid.UUID,
    reason: Optional[str] = Query("Administrative rejection", description="Rejection rationale"),
    db: AsyncSession = Depends(get_db),
    current_user: User = _admin,
) -> dict[str, Any]:
    try:
        res = await reject_candidate_model(db, job_id=job_id, user_id=current_user.id, reason=reason or "Administrative rejection")
        return res
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
