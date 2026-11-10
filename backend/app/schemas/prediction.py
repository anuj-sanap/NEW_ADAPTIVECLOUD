"""
backend/app/schemas/prediction.py
Pydantic schemas for predictive maintenance, threat forecasts, and dashboard summary telemetry.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    id: uuid.UUID
    host_id: uuid.UUID
    ts: datetime
    kind: str  # threat | cpu | memory | disk | service
    horizon_min: int
    value: float
    probability: float
    model_id: Optional[uuid.UUID] = None
    outcome_observed: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MaintenanceForecastResponse(BaseModel):
    id: uuid.UUID
    host_id: uuid.UUID
    component: str  # disk | memory | cpu | pagefile
    metric_name: str
    days_remaining: float
    confidence: float
    details: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}


class HostMaintenanceDetailResponse(BaseModel):
    host_id: uuid.UUID
    hostname: str
    forecasts: list[MaintenanceForecastResponse]
    disk_fill_eta_days: Optional[float] = None
    service_risks: list[dict[str, Any]] = []
    component_status: dict[str, str] = {}


class TopRiskItem(BaseModel):
    category: str  # threat | maintenance
    title: str
    host_id: Optional[uuid.UUID] = None
    hostname: Optional[str] = None
    probability: float
    eta_minutes: Optional[int] = None
    severity: str


class DashboardSummaryResponse(BaseModel):
    host_health_score: float = Field(..., ge=0.0, le=100.0)
    total_hosts: int
    online_hosts: int
    active_incidents: int
    attack_counts_24h: dict[str, int]
    top_risks: list[TopRiskItem]
