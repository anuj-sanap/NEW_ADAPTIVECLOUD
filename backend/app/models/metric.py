"""
backend/app/models/metric.py
SQLAlchemy ORM model for metric snapshots ingested from agents.
Partitioned in PostgreSQL by collected_at (monthly RANGE partitions).
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Metric(Base):
    """
    Telemetry snapshot from a Windows agent.
    Table is range-partitioned on collected_at (monthly) in PostgreSQL.
    The partition DDL is managed via Alembic raw SQL migration.
    """

    __tablename__ = "metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, primary_key=True
    )
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # ── CPU / Memory ──────────────────────────────────────────────────────────
    cpu_percent: Mapped[float] = mapped_column(Float, nullable=False)
    memory_percent: Mapped[float] = mapped_column(Float, nullable=False)
    memory_used_mb: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Disk I/O ─────────────────────────────────────────────────────────────
    disk_read_bytes_sec: Mapped[float] = mapped_column(Float, nullable=False)
    disk_write_bytes_sec: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Network I/O ──────────────────────────────────────────────────────────
    net_bytes_sent_sec: Mapped[float] = mapped_column(Float, nullable=False)
    net_bytes_recv_sec: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Connections / Processes ───────────────────────────────────────────────
    active_connections: Mapped[int] = mapped_column(Integer, nullable=False)
    process_count: Mapped[int] = mapped_column(Integer, nullable=False)
    top_processes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # ── Windows Event Log ────────────────────────────────────────────────────
    event_log_errors_1m: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    event_log_warnings_1m: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return (
            f"<Metric id={self.id} agent_id={self.agent_id} "
            f"collected_at={self.collected_at.isoformat()}>"
        )
