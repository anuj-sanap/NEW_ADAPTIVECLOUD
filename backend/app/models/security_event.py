"""
backend/app/models/security_event.py
SQLAlchemy ORM model for security events (Wazuh, Agent, Windows Event Log).
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SecurityEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Security event ingested from Wazuh SIEM, Windows Event Log, or agent sensors.
    """

    __tablename__ = "security_events"

    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    # Source: wazuh | agent | winevent
    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rule_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    src_ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    user: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    event_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    raw: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)

    __table_args__ = (
        Index("ix_security_events_host_id_ts", "host_id", "ts"),
    )

    def __repr__(self) -> str:
        return f"<SecurityEvent id={self.id} source={self.source} level={self.level} rule={self.rule_id}>"

