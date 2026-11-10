"""
backend/app/api/v1/routes/auth.py
Authentication endpoints: login, refresh.
"""
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT tokens",
)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """
    Validate username + password and issue access + refresh tokens.
    Returns HTTP 401 on any credential mismatch (intentionally vague).
    """
    result = await db.execute(select(User).where(User.username == body.username))
    user: User | None = result.scalar_one_or_none()

    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None or not user.is_active:
        raise invalid_exc
    if not verify_password(body.password, user.password_hash):
        raise invalid_exc

    # Update last_login
    user.last_login = datetime.now(UTC)
    await db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, user.role),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Exchange refresh token for new access token",
)
async def refresh(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccessTokenResponse:
    """
    Validate a refresh JWT and issue a new access token.
    Does not rotate the refresh token (stateless; revocation via short access TTL).
    """
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_refresh_token(body.refresh_token)
        user_id: str = payload.get("sub", "")
    except JWTError:
        raise exc

    from uuid import UUID
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise exc

    return AccessTokenResponse(
        access_token=create_access_token(user.id, user.role),
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
