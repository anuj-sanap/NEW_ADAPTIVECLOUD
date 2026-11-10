"""
backend/app/schemas/metric.py
Pydantic schemas for metric ingest and query endpoints.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ProcessInfo(BaseModel):
    pid: int
    name: str = Field(..., max_length=255)
    cpu_percent: float = Field(..., ge=0.0)
    memory_mb: float = Field(..., ge=0.0)


class MetricPayload(BaseModel):
    """
    Payload sent by the Windows agent to POST /api/v1/ingest.
    All fields required; validation enforces non-negative ranges.
    """
    agent_id: uuid.UUID
    collected_at: datetime  # Must be UTC

    cpu_percent: float = Field(..., ge=0.0, le=100.0)
    memory_percent: float = Field(..., ge=0.0, le=100.0)
    memory_used_mb: float = Field(..., ge=0.0)

    disk_read_bytes_sec: float = Field(..., ge=0.0)
    disk_write_bytes_sec: float = Field(..., ge=0.0)

    net_bytes_sent_sec: float = Field(..., ge=0.0)
    net_bytes_recv_sec: float = Field(..., ge=0.0)

    active_connections: int = Field(..., ge=0)
    process_count: int = Field(..., ge=0)
    top_processes: list[ProcessInfo] = Field(default_factory=list, max_length=20)

    event_log_errors_1m: int = Field(..., ge=0)
    event_log_warnings_1m: int = Field(..., ge=0)

    @field_validator("collected_at", mode="before")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        """Accept timezone-aware datetimes only."""
        if hasattr(v, "tzinfo") and v.tzinfo is None:
            raise ValueError("collected_at must be timezone-aware (UTC)")
        return v


class MetricIngestResponse(BaseModel):
    metric_id: uuid.UUID
    queued_for_inference: bool


class MetricRecord(MetricPayload):
    """MetricPayload plus server-generated fields (returned from GET /metrics)."""
    id: uuid.UUID
    ingested_at: datetime

    model_config = {"from_attributes": True}


class MetricListResponse(BaseModel):
    total: int
    items: list[MetricRecord]
