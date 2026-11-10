"""
backend/app/models/response.py
SQLAlchemy ORM models for automated/manual adaptive responses and dynamic IP blocklists.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ResponseAction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Adaptive countermeasure action executed against an attack or failure.
    action: block_ip | restrict | restart_service | kill_process
    status: pending | executed | failed | verified | rolled_back
    """

    __tablename__ = "response_actions"

    host_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    incident_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<ResponseAction id={self.id} action={self.action} target={self.target} status={self.status}>"


class Blocklist(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Active firewall blocklist entries maintained dynamically by adaptive defenses.
    """

    __tablename__ = "blocklist"

    ip: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    def __repr__(self) -> str:
        return f"<Blocklist id={self.id} ip={self.ip} active={self.active}>"
