"""
backend/app/schemas/agent.py
Pydantic schemas for agent registration and listing endpoints.
"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AgentCreate(BaseModel):
    hostname: str = Field(..., min_length=1, max_length=255)
    os_version: str = Field(..., min_length=1, max_length=128)
    ip_address: Optional[str] = Field(None, description="Tailscale IP preferred")


class AgentCreatedResponse(BaseModel):
    """Returned once at creation; api_key shown only here."""
    id: uuid.UUID
    hostname: str
    api_key: str = Field(..., description="Raw API key — store securely, shown only once")


class AgentResponse(BaseModel):
    id: uuid.UUID
    hostname: str
    os_version: str
    ip_address: Optional[str]
    status: str
    last_seen: Optional[datetime]
    created_at: datetime
    revoked: bool

    model_config = {"from_attributes": True}

