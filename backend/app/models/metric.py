"""
backend/app/models/metric.py
SQLAlchemy ORM model for host resource telemetry metrics.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Metric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Periodic resource metrics collected from a monitored host.
    Includes CPU, memory, disk, network I/O, load, process count, connection count.
    """

    __tablename__ = "metrics"

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

    cpu: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    mem: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    disk: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    net_in: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    net_out: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    load: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    proc_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conn_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=dict)

    __table_args__ = (
        Index("ix_metrics_host_id_ts", "host_id", "ts"),
    )

    def __repr__(self) -> str:
        return f"<Metric id={self.id} host_id={self.host_id} ts={self.ts} cpu={self.cpu}>"
