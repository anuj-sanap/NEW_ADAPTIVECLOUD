"""
backend/app/schemas/host.py
Pydantic schemas for Host inventory and telemetry metrics querying.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class HostResponse(BaseModel):
    id: uuid.UUID
    hostname: str
    os_version: str
    agent_platform: str
    ip_address: Optional[str] = None
    status: str
    last_seen: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MetricPoint(BaseModel):
    ts: datetime
    cpu: float
    mem: float
    disk: float = 0.0
    net_in: float = 0.0
    net_out: float = 0.0
    load: float = 0.0
    proc_count: int = 0
    conn_count: int = 0
    extra: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class HostMetricsResponse(BaseModel):
    host_id: uuid.UUID
    resolution: str
    total_points: int
    from_dt: Optional[datetime] = None
    to_dt: Optional[datetime] = None
    metrics: list[MetricPoint]
