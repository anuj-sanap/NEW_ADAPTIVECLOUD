"""
backend/app/schemas/report.py
Pydantic schemas for executive compliance and security summary reporting.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel


class ReportSummaryResponse(BaseModel):
    generated_at: datetime
    reporting_period_days: int
    total_hosts: int
    online_hosts: int
    total_detections: int
    total_incidents: int
    attacks_blocked: int
    uptime_percentage: float
    attack_breakdown: dict[str, int]
    top_threat_vectors: list[dict[str, Any]]

