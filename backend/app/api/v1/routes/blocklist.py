"""
backend/app/api/v1/routes/blocklist.py
Endpoints for dynamic IP blocklist management.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user, require_role
from app.db.session import get_db
from app.models.audit import AuditLog
from app.models.response import Blocklist
from app.models.user import User
from app.schemas.response import BlocklistCreate, BlocklistResponse
from app.services.response_engine import policy_manager

router = APIRouter(prefix="/blocklist", tags=["blocklist"])

_analyst = Depends(require_role("admin", "analyst"))


@router.get("", response_model=list[BlocklistResponse], summary="List active and historical IP blocklist entries")
async def list_blocklist(
    active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Blocklist]:
    stmt = select(Blocklist).order_by(desc(Blocklist.created_at))
    if active is not None:
        stmt = stmt.where(Blocklist.active == active)
    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.post("", response_model=BlocklistResponse, status_code=status.HTTP_201_CREATED, summary="Add IP to firewall blocklist")
async def add_to_blocklist(
    payload: BlocklistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = _analyst,
) -> Blocklist:
    # 1. Safety check
    if policy_manager.is_ip_protected(payload.ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot block protected IP '{payload.ip}' (allowlist / control server safety)",
        )

    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=payload.ttl_minutes) if payload.ttl_minutes else None

    # Check if entry already exists
    stmt = select(Blocklist).where(Blocklist.ip == payload.ip)
    existing = (await db.execute(stmt)).scalar_one_or_none()

    if existing:
        existing.active = True
        existing.reason = payload.reason
        existing.expires_at = expires_at
        entry = existing
    else:
        entry = Blocklist(
            ip=payload.ip,
            reason=payload.reason,
            expires_at=expires_at,
            active=True,
        )
        db.add(entry)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="blocklist.add",
        resource_type="blocklist",
        resource_id=payload.ip,
        details={"reason": payload.reason, "ttl_minutes": payload.ttl_minutes},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{target}", response_model=dict[str, str], summary="Remove IP from active firewall blocklist")
async def remove_from_blocklist(
    target: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = _analyst,
) -> dict[str, str]:
    # Support target by IP or UUID
    try:
        target_uuid = uuid.UUID(target)
        stmt = select(Blocklist).where((Blocklist.id == target_uuid) | (Blocklist.ip == target))
    except ValueError:
        stmt = select(Blocklist).where(Blocklist.ip == target)

    entry = (await db.execute(stmt)).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Blocklist entry for '{target}' not found")

    entry.active = False

    audit = AuditLog(
        user_id=current_user.id,
        action="blocklist.remove",
        resource_type="blocklist",
        resource_id=entry.ip,
    )
    db.add(audit)
    await db.commit()
    return {"status": "success", "message": f"IP '{entry.ip}' removed from active blocklist"}

