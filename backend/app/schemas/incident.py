"""
backend/app/schemas/incident.py
Pydantic schemas for security incident listing and detail inspection.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel


class IncidentItemResponse(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    item_type: str
    item_id: uuid.UUID
    details: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentResponse(BaseModel):
    id: uuid.UUID
    title: str
    severity: str
    status: str
    assigned_to: Optional[uuid.UUID] = None
    description: Optional[str] = None
    summary: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class IncidentDetailResponse(IncidentResponse):
    items: list[IncidentItemResponse] = []
