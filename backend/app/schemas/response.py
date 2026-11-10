"""
backend/app/schemas/response.py
Pydantic schemas for automated response actions, dynamic blocklists, and policy configurations.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class ResponseActionResponse(BaseModel):
    id: uuid.UUID
    host_id: Optional[uuid.UUID] = None
    incident_id: Optional[uuid.UUID] = None
    action: str  # block_ip | restrict | restart_service | kill_process
    status: str  # pending | executed | failed | verified | rolled_back
    target: str
    initiated_by: str
    result: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResponseActionCreate(BaseModel):
    host_id: Optional[uuid.UUID] = None
    incident_id: Optional[uuid.UUID] = None
    action: str = Field(..., description="block_ip | restrict | restart_service | kill_process")
    target: str = Field(..., description="Target IP, username, process, or service")


class PolicyRule(BaseModel):
    label: str = Field(..., description="Attack or anomaly label")
    min_confidence: float = Field(..., ge=0.0, le=1.0)
    severity: str = Field(..., description="low | medium | high | critical")
    action: str = Field(..., description="block_ip | restrict | restart_service | kill_process")
    requires_approval: bool = False
    ttl_minutes: int = Field(60, ge=0, description="Auto-expiration minutes (0 = permanent/manual)")


class PolicyConfigResponse(BaseModel):
    dry_run: bool
    max_actions_per_minute: int
    never_block_ips: list[str]
    policies: list[PolicyRule]


class PolicyConfigUpdate(BaseModel):
    dry_run: Optional[bool] = None
    max_actions_per_minute: Optional[int] = None
    never_block_ips: Optional[list[str]] = None
    policies: Optional[list[PolicyRule]] = None


class BlocklistResponse(BaseModel):
    id: uuid.UUID
    ip: str
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BlocklistCreate(BaseModel):
    ip: str = Field(..., description="IPv4 or IPv6 address to block")
    reason: Optional[str] = Field("Manual administrative block", description="Forensic rationale")
    ttl_minutes: Optional[int] = Field(60, ge=1, le=43200, description="Time to live in minutes (default: 60)")

