"""
backend/app/services/audit.py
Helper service to log security and administrative actions to the audit_logs table.
"""
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from app.core.logging import get_logger

logger = get_logger("audit")


async def record_audit_log(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    user_id: Optional[UUID] = None,
    details: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Persist an audit log entry within the active database session.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()
    logger.info(
        "Audit log recorded",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=str(user_id) if user_id else None,
    )
    return entry

