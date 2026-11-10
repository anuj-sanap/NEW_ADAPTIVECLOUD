"""
backend/app/models/incident.py
SQLAlchemy ORM models for security incidents, aggregated incident items, and RCA reports.
"""
import uuid
from typing import Any, Optional

from sqlalchemy import ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Incident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Correlated security incident aggregating multiple events, detections, or anomalies.
    """

    __tablename__ = "incidents"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<Incident id={self.id} title={self.title!r} severity={self.severity} status={self.status}>"


class IncidentItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Links a specific detection, event, or metric anomaly to an overarching incident.
    """

    __tablename__ = "incident_items"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_type: Mapped[str] = mapped_column(String(64), nullable=False)  # detection, security_event, prediction
    item_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<IncidentItem id={self.id} incident={self.incident_id} type={self.item_type}>"


class RCAReport(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Root Cause Analysis (RCA) report generated for an incident.
    """

    __tablename__ = "rca_reports"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    probable_cause: Mapped[str] = mapped_column(Text, nullable=False)
    source_ips: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    affected_hosts: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    def __repr__(self) -> str:
        return f"<RCAReport id={self.id} incident_id={self.incident_id}>"
