"""
backend/app/schemas/detection.py
Pydantic schemas for anomaly detection and multi-class classification endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel


class DetectionResponse(BaseModel):
    id: uuid.UUID
    host_id: uuid.UUID
    ts: datetime
    anomaly_score: float
    is_attack: bool
    model_id: Optional[uuid.UUID] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ClassificationResponse(BaseModel):
    id: uuid.UUID
    host_id: uuid.UUID
    ts: datetime
    detection_id: Optional[uuid.UUID] = None
    label: str
    confidence: float
    probs: dict[str, Any]
    model_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}
