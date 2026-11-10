"""
backend/app/models/prediction.py
SQLAlchemy ORM model for ML inference results.
"""
import uuid

from datetime import datetime
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Valid attack classification labels — keep in sync with docs/DATA_SCHEMA.md
ATTACK_LABELS = (
    "benign",
    "brute_force",
    "ddos",
    "port_scan",
    "unauthorized_access",
    "suspicious_process",
)


class Prediction(Base):
    """ML inference result linked to a specific metric snapshot."""

    __tablename__ = "predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,  # FK to metrics (composite PK — handled via raw FK in migration)
        index=True,
    )
    predicted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(
        Enum(*ATTACK_LABELS, name="attack_label_enum"),
        nullable=False,
        index=True,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    features_used: Mapped[list] = mapped_column(
        # PostgreSQL text array for feature name list
        ARRAY(String),
        nullable=False,
        default=list,
    )

    def __repr__(self) -> str:
        return (
            f"<Prediction id={self.id} label={self.label!r} "
            f"confidence={self.confidence:.2f}>"
        )
