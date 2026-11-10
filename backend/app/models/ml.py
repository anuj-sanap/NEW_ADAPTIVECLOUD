"""
backend/app/models/ml.py
SQLAlchemy ORM models for ML lifecycle: models, evaluations, drift tracking, retraining, and human feedback.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MLModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Registered ML model metadata, versioning, performance metrics, and deployment status.
    status: candidate | active | retired
    """

    __tablename__ = "ml_models"

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    task: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # anomaly, attack_classification, forecasting
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    artifact_path: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="candidate", index=True)

    __table_args__ = (
        Index("ix_ml_models_name_version", "name", "version", unique=True),
    )

    def __repr__(self) -> str:
        return f"<MLModel id={self.id} name={self.name} v={self.version} status={self.status}>"


class ModelEvaluation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Formal offline or online model evaluation records against validation benchmarks.
    """

    __tablename__ = "model_evaluations"

    model_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ml_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dataset_name: Mapped[str] = mapped_column(String(128), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ModelEvaluation id={self.id} model_id={self.model_id}>"


class DriftEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Detected data or concept drift events in telemetry streams.
    """

    __tablename__ = "drift_events"

    model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ml_models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    feature_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    drift_score: Mapped[float] = mapped_column(Float, nullable=False)
    p_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_drift: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<DriftEvent id={self.id} feature={self.feature_name} score={self.drift_score:.3f}>"


class RetrainingJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Automated or admin-triggered model retraining pipeline executions.
    """

    __tablename__ = "retraining_jobs"

    model_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ml_models.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    dataset_size: Mapped[int] = mapped_column(Float, nullable=False, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metrics_summary: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<RetrainingJob id={self.id} status={self.status}>"


class FeedbackLabel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Human analyst ground truth feedback on detections/classifications for active learning.
    """

    __tablename__ = "feedback_labels"

    detection_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("detections.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    analyst_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    true_label: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<FeedbackLabel id={self.id} true_label={self.true_label}>"

