"""
backend/app/api/v1/dependencies.py
FastAPI dependency functions for authentication and authorisation.
"""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, verify_api_key
from app.db.session import get_db
from app.models.agent import Agent
from app.models.user import User

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Validate a Bearer JWT and return the authenticated User.
    Raises HTTP 401 if the token is invalid or the user is inactive.
    """
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id: str = payload.get("sub", "")
    except JWTError:
        raise exc

    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise exc
    return user


def require_role(*roles: str):
    """
    Factory: returns a dependency that enforces one of the given roles.

    Usage:
        @router.post("/...", dependencies=[Depends(require_role("admin"))])
    """
    async def _check(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {' or '.join(roles)}",
            )
        return user
    return _check


async def get_agent_from_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """
    Validate an X-API-Key header and return the authenticated Agent.
    Iterates active agents and bcrypt-checks the hash (not a lookup by raw key).
    Raises HTTP 401 if the key is missing, invalid, or the agent is revoked.

    Performance note: for large agent counts, consider storing a prefix index.
    With typical deployments (< 100 agents) bcrypt iteration is acceptable.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header required",
        )

    result = await db.execute(
        select(Agent).where(Agent.revoked.is_(False))
    )
    agents = result.scalars().all()

    for agent in agents:
        if verify_api_key(x_api_key, agent.api_key_hash):
            return agent

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or revoked API key",
    )
