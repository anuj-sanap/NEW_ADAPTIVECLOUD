"""
backend/app/schemas/ml.py
Pydantic schemas for ML model registry and lifecycle management.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class MLModelResponse(BaseModel):
    id: uuid.UUID
    name: str
    task: str
    version: str
    status: str
    metrics: dict[str, Any]
    artifact_path: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MLModelMetricsResponse(BaseModel):
    model_id: uuid.UUID
    name: str
    task: str
    version: str
    metrics: dict[str, Any]
