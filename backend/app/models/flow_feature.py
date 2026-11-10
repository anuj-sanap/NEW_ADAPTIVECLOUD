"""
backend/app/models/flow_feature.py
SQLAlchemy ORM model for network flow features extracted from packet/socket counters.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class FlowFeature(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Extracted network flow features (rates, flags, port statistics) for anomaly detection.
    """

    __tablename__ = "flow_features"

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
    features: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        Index("ix_flow_features_host_id_ts", "host_id", "ts"),
    )

    def __repr__(self) -> str:
        return f"<FlowFeature id={self.id} host_id={self.host_id} ts={self.ts}>"

