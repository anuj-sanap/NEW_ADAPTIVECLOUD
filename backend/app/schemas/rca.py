"""
backend/app/schemas/rca.py
Pydantic schemas for Root Cause Analysis (RCA) reporting and incident forensics.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel


class SourceIpInfo(BaseModel):
    ip: str
    count: int = 1
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    country: Optional[str] = "Unknown"
    city: Optional[str] = "Unknown"


class TimelineEvent(BaseModel):
    ts: datetime
    type: str  # security_event | flow | metric_spike | process
    description: str
    source: str
    details: Optional[dict[str, Any]] = None


class RCAReportResponse(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    probable_cause: str
    confidence: float
    source_ips: list[SourceIpInfo]
    affected_hosts: list[str]
    evidence: dict[str, Any]
    timeline: list[TimelineEvent]
    recommended_actions: list[str]
    plain_english_summary: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

