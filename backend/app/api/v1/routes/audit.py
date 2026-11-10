"""
backend/app/api/v1/routes/audit.py
Endpoints for querying administrative and system audit logs.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditLogResponse], summary="List system and administrative audit logs")
async def list_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action substring"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by initiating user UUID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(desc(AuditLog.created_at))

    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)

    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())

