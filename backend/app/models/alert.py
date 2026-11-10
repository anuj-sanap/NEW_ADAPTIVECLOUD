"""
backend/app/models/alert.py
SQLAlchemy ORM model for security alerts.
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Alert(Base):
    """
    Security alert raised when an ML prediction exceeds the confidence
    threshold for a non-benign attack label.
    Also accepts Wazuh-originated alerts.
    """

    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prediction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,  # Null for Wazuh-originated alerts
        index=True,
    )
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(
        Enum("low", "medium", "high", "critical", name="alert_severity_enum"),
        nullable=False,
        index=True,
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    acknowledged_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return (
            f"<Alert id={self.id} type={self.alert_type!r} "
            f"severity={self.severity} ack={self.acknowledged}>"
        )
