"""
backend/app/api/v1/dependencies.py
Authentication and authorization dependencies for FastAPI endpoints:
- get_current_user (JWT Bearer)
- require_role (RBAC: admin, analyst, viewer)
- get_agent_from_api_key (X-API-Key header)
"""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_access_token, verify_api_key
from app.db.session import get_db
from app.models.host import Host
from app.models.user import User

settings = get_settings()
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Validate Bearer JWT and return the active User object.
    Raises 401 if missing, expired, or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_exception

    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str: str = payload.get("sub", "")
        if not user_id_str:
            raise credentials_exception
        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(*roles: str):
    """
    Factory creating a role-enforcement dependency.
    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """
    async def _role_checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: requires role in {roles}",
            )
        return user
    return _role_checker


async def get_agent_from_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
    db: AsyncSession = Depends(get_db),
) -> Host:
    """
    Verify X-API-Key header.
    Validates either against configured master AGENT_API_KEY or stored Host bcrypt hashes.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header required for agent ingestion",
        )

    # Master development key check
    if settings.AGENT_API_KEY and x_api_key == settings.AGENT_API_KEY:
        result = await db.execute(select(Host).where(Host.is_active.is_(True)).limit(1))
        host = result.scalar_one_or_none()
        if host:
            return host
        # If no host exists yet, create a default dev host
        dev_host = Host(
            hostname="DEFAULT-DEV-HOST",
            os_version="Windows Server 2022",
            agent_platform="windows",
            status="online",
            api_key_hash="dev-master-key",
        )
        db.add(dev_host)
        await db.flush()
        return dev_host

    # Query active hosts and check stored bcrypt hash
    result = await db.execute(select(Host).where(Host.is_active.is_(True)))
    hosts = result.scalars().all()

    for host in hosts:
        if verify_api_key(x_api_key, host.api_key_hash):
            return host

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or revoked agent API key",
    )
