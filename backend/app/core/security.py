"""
backend/app/core/security.py
JWT token management, password hashing, and agent API key verification.
Uses bcrypt directly for robust, cross-platform password hashing.
"""
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


def hash_password(plain: str) -> str:
    """Hash password using bcrypt (max 72 bytes)."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8")[:72], salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password against stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def hash_api_key(raw_key: str) -> str:
    """Hash raw agent API key with bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(raw_key.encode("utf-8")[:72], salt).decode("utf-8")


def verify_api_key(raw_key: str, hashed: str) -> bool:
    """Verify raw API key against stored bcrypt hash."""
    try:
        return bcrypt.checkpw(raw_key.encode("utf-8")[:72], hashed.encode("utf-8"))
    except Exception:
        return False


def _create_token(data: dict[str, Any], expire_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(UTC) + expire_delta
    payload["iat"] = datetime.now(UTC)
    return jwt.encode(
        payload,
        settings.secret_key,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(user_id: UUID, role: str) -> str:
    """Create short-lived JWT access token."""
    return _create_token(
        {"sub": str(user_id), "role": role, "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: UUID) -> str:
    """Create longer-lived JWT refresh token."""
    return _create_token(
        {"sub": str(user_id), "type": "refresh"},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate an access token."""
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.JWT_ALGORITHM],
    )
    if payload.get("type") != "access":
        raise JWTError("Token type is not access")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate a refresh token."""
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.JWT_ALGORITHM],
    )
    if payload.get("type") != "refresh":
        raise JWTError("Token type is not refresh")
    return payload
