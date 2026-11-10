"""
backend/app/api/v1/routes/responses.py
Endpoints for automated countermeasure tracking, manual approval, rollback, and policy configuration.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.response import ResponseAction
from app.models.user import User
from app.schemas.response import (
    PolicyConfigResponse,
    PolicyConfigUpdate,
    ResponseActionResponse,
)
from app.services.response_engine import (
    approve_response_action,
    policy_manager,
    rollback_response_action,
)

router = APIRouter(prefix="/responses", tags=["responses"])

_analyst = Depends(require_role("admin", "analyst"))
_admin = Depends(require_role("admin"))


@router.get("", response_model=list[ResponseActionResponse], summary="List countermeasure response actions")
async def list_response_actions(
    host_id: Optional[uuid.UUID] = Query(None, description="Filter by host ID"),
    action: Optional[str] = Query(None, description="Filter by action: block_ip | restrict | restart_service | kill_process"),
    action_status: Optional[str] = Query(None, alias="status", description="Filter by status: pending | executed | failed | verified | rolled_back"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ResponseAction]:
    stmt = select(ResponseAction).order_by(desc(ResponseAction.created_at))

    if host_id:
        stmt = stmt.where(ResponseAction.host_id == host_id)
    if action:
        stmt = stmt.where(ResponseAction.action == action)
    if action_status:
        stmt = stmt.where(ResponseAction.status == action_status)

    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post("/{action_id}/approve", response_model=ResponseActionResponse, summary="Approve pending countermeasure action")
async def approve_action_endpoint(
    action_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = _analyst,
) -> ResponseAction:
    try:
        action = await approve_response_action(db, action_id, user_id=current_user.id)
        return action
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{action_id}/rollback", response_model=ResponseActionResponse, summary="Rollback executed countermeasure action")
async def rollback_action_endpoint(
    action_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = _analyst,
) -> ResponseAction:
    try:
        action = await rollback_response_action(db, action_id, user_id=current_user.id)
        return action
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/policy", response_model=PolicyConfigResponse, summary="Get active response policy and safety config")
async def get_response_policy(
    current_user: User = Depends(get_current_user),
) -> PolicyConfigResponse:
    return PolicyConfigResponse(
        dry_run=policy_manager.dry_run,
        max_actions_per_minute=policy_manager.max_actions_per_minute,
        never_block_ips=policy_manager.never_block_ips,
        policies=policy_manager.policies,
    )


@router.put("/policy", response_model=PolicyConfigResponse, summary="Update response policy and safety config (Admin)")
async def update_response_policy(
    update: PolicyConfigUpdate,
    current_user: User = _admin,
) -> PolicyConfigResponse:
    if update.dry_run is not None:
        policy_manager.dry_run = update.dry_run
    if update.max_actions_per_minute is not None:
        policy_manager.max_actions_per_minute = update.max_actions_per_minute
    if update.never_block_ips is not None:
        policy_manager.never_block_ips = update.never_block_ips
    if update.policies is not None:
        policy_manager.policies = [p.model_dump() for p in update.policies]

    return PolicyConfigResponse(
        dry_run=policy_manager.dry_run,
        max_actions_per_minute=policy_manager.max_actions_per_minute,
        never_block_ips=policy_manager.never_block_ips,
        policies=policy_manager.policies,
    )
