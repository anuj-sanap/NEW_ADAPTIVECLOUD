"""
backend/app/models/audit.py
SQLAlchemy ORM model for administrative and system audit logging.
"""
import uuid
from typing import Any, Optional

from sqlalchemy import ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Immutable audit log entry tracking user and agent actions across the platform.
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action} user={self.user_id}>"
