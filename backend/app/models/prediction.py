"""
backend/app/models/prediction.py
SQLAlchemy ORM models for ML predictive metrics, attack forecasts, and maintenance projections.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Prediction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Predictive maintenance / forecasting model output.
    kind: threat | cpu | memory | disk | service
    """

    __tablename__ = "predictions"

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

    # Kind: threat | cpu | memory | disk | service
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    horizon_min: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    probability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    outcome_observed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index("ix_predictions_host_id_ts", "host_id", "ts"),
    )

    def __repr__(self) -> str:
        return f"<Prediction id={self.id} host_id={self.host_id} kind={self.kind} prob={self.probability:.2f}>"


class MaintenanceForecast(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Predictive maintenance forecast estimating component exhaustion or failure horizon.
    """

    __tablename__ = "maintenance_forecasts"

    host_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("hosts.id", ondelete="CASCADE"),
        nullable=False,
    )
    component: Mapped[str] = mapped_column(String(64), nullable=False)  # disk, memory, cpu, pagefile
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    days_remaining: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_maintenance_forecasts_host_id", "host_id"),
    )

    def __repr__(self) -> str:
        return f"<MaintenanceForecast id={self.id} host_id={self.host_id} component={self.component} days={self.days_remaining:.1f}>"
