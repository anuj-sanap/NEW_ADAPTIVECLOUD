"""
backend/app/schemas/prediction.py
Pydantic schemas for ML prediction query endpoints.
"""
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

AttackLabel = Literal[
    "benign",
    "brute_force",
    "ddos",
    "port_scan",
    "unauthorized_access",
    "suspicious_process",
]


class PredictionRecord(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    metric_id: uuid.UUID
    predicted_at: datetime
    label: AttackLabel
    confidence: float = Field(..., ge=0.0, le=1.0)
    model_version: str
    features_used: list[str]

    model_config = {"from_attributes": True}


class PredictionListResponse(BaseModel):
    total: int
    items: list[PredictionRecord]


class MLNotAvailable(BaseModel):
    """Returned when no trained model exists."""
    status: Literal["not_available"] = "not_available"


class MLStatusResponse(BaseModel):
    status: Literal["ready", "not_available", "training", "failed"]
    model_version: Optional[str] = None
    trained_at: Optional[datetime] = None
    training_samples: Optional[int] = None
    features: Optional[list[str]] = None
    labels: Optional[list[str]] = None
    job_status: Optional[str] = None


class TrainJobResponse(BaseModel):
    job_id: uuid.UUID
    status: Literal["queued"]
    message: str
