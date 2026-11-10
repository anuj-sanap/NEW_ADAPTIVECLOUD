"""
backend/app/api/v1/routes/auth.py
Authentication endpoints: login, token refresh, and /auth/me profile inspection.
"""
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
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
from pydantic import BaseModel
from uuid import UUID

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class UserProfileResponse(BaseModel):
    id: UUID
    username: str
    email: str
    role: str
    is_active: bool
    last_login: datetime | None

    model_config = {"from_attributes": True}


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate user and issue JWT access and refresh tokens",
)
async def login(
    body: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    result = await db.execute(select(User).where(User.username == body.username))
    user: User | None = result.scalar_one_or_none()

    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None or not user.is_active:
        raise invalid_exc
    if not verify_password(body.password, user.password_hash):
        raise invalid_exc

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
    summary="Exchange valid refresh token for a new access token",
)
async def refresh_token_endpoint(
    body: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccessTokenResponse:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_refresh_token(body.refresh_token)
        user_id_str: str = payload.get("sub", "")
        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        raise exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise exc

    return AccessTokenResponse(
        access_token=create_access_token(user.id, user.role),
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Retrieve profile of currently authenticated user",
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserProfileResponse:
    return UserProfileResponse.model_validate(current_user)
