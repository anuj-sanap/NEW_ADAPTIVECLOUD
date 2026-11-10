"""
backend/app/api/v1/routes/agents.py
Agent management endpoints (admin only).
"""
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_role
from app.core.security import hash_api_key
from app.db.session import get_db
from app.models.agent import Agent
from app.models.user import User
from app.schemas.agent import AgentCreate, AgentCreatedResponse, AgentResponse

router = APIRouter(prefix="/agents", tags=["agents"])

_admin = Depends(require_role("admin"))


@router.get(
    "",
    response_model=list[AgentResponse],
    summary="List all registered agents (admin)",
)
async def list_agents(
    _user: Annotated[User, _admin],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AgentResponse]:
    result = await db.execute(select(Agent).order_by(Agent.created_at.desc()))
    return result.scalars().all()  # type: ignore[return-value]


@router.post(
    "",
    response_model=AgentCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new agent (admin)",
)
async def create_agent(
    body: AgentCreate,
    _user: Annotated[User, _admin],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AgentCreatedResponse:
    """
    Register a new Windows agent. The raw API key is returned ONCE here.
    It is never stored in plain text; only the bcrypt hash is persisted.
    """
    raw_key = secrets.token_urlsafe(48)   # 64-char URL-safe random key
    agent = Agent(
        hostname=body.hostname,
        os_version=body.os_version,
        ip_address=body.ip_address,
        api_key_hash=hash_api_key(raw_key),
        status="offline",
    )
    db.add(agent)
    await db.flush()   # get the generated UUID before commit

    return AgentCreatedResponse(
        id=agent.id,
        hostname=agent.hostname,
        api_key=raw_key,
    )


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an agent (admin)",
)
async def revoke_agent(
    agent_id: uuid.UUID,
    _user: Annotated[User, _admin],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent: Agent | None = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    agent.revoked = True
    agent.status = "offline"

