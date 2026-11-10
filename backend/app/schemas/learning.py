"""
backend/app/schemas/learning.py
Pydantic schemas for human analyst feedback, feature drift events, and controlled retraining jobs.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    detection_id: Optional[uuid.UUID] = None
    true_label: str = Field(..., description="Ground truth label verified by analyst: benign | brute_force | ddos | port_scan | unauthorized_access | suspicious_process")
    comments: Optional[str] = Field(None, description="Analyst justification or forensic notes")


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    detection_id: Optional[uuid.UUID] = None
    analyst_id: Optional[uuid.UUID] = None
    true_label: str
    comments: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DriftEventResponse(BaseModel):
    id: uuid.UUID
    model_id: Optional[uuid.UUID] = None
    feature_name: str
    drift_score: float
    p_value: Optional[float] = None
    is_drift: bool
    details: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class DriftCheckResponse(BaseModel):
    status: str
    overall_drift: bool
    mean_psi: float
    max_psi: float
    drifted_features: list[str]
    total_features_evaluated: int
    events_recorded: int
    evaluated_at: datetime


class RetrainRequest(BaseModel):
    force: bool = False
    replay_ratio: float = Field(0.70, ge=0.1, le=0.9, description="Ratio of historical baseline replay samples")


class RetrainingJobResponse(BaseModel):
    id: uuid.UUID
    model_id: Optional[uuid.UUID] = None
    status: str
    dataset_size: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metrics_summary: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PromotionResponse(BaseModel):
    job_id: uuid.UUID
    decision: str
    previous_champion_id: Optional[uuid.UUID] = None
    new_champion_id: Optional[uuid.UUID] = None
    message: str
