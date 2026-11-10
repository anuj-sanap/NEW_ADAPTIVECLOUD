"""
backend/app/schemas/event.py
Pydantic schemas for Security Events query responses.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class SecurityEventResponse(BaseModel):
    id: uuid.UUID
    host_id: uuid.UUID
    ts: datetime
    source: str
    rule_id: Optional[str] = None
    level: int
    category: Optional[str] = None
    src_ip: Optional[str] = None
    user: Optional[str] = None
    event_id: Optional[int] = None
    raw: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}

