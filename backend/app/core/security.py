"""
backend/app/core/security.py
JWT token creation/validation and password hashing utilities.
"""
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# ── Password hashing ─────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return bcrypt hash of plain-text password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Compare plain password against stored bcrypt hash."""
    return _pwd_context.verify(plain, hashed)


def hash_api_key(raw_key: str) -> str:
    """Hash an API key with bcrypt for storage."""
    return _pwd_context.hash(raw_key)


def verify_api_key(raw_key: str, hashed: str) -> bool:
    """Verify a raw API key against its stored bcrypt hash."""
    return _pwd_context.verify(raw_key, hashed)


# ── JWT helpers ──────────────────────────────────────────────────────────────

def _create_token(data: dict[str, Any], expire_delta: timedelta) -> str:
    """Internal: sign and return a JWT with the given payload and expiry."""
    payload = data.copy()
    payload["exp"] = datetime.now(UTC) + expire_delta
    payload["iat"] = datetime.now(UTC)
    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_access_token(user_id: UUID, role: str) -> str:
    """Create a short-lived access JWT for a user."""
    return _create_token(
        {"sub": str(user_id), "role": role, "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: UUID) -> str:
    """Create a long-lived refresh JWT for a user."""
    return _create_token(
        {"sub": str(user_id), "type": "refresh"},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate an access JWT.

    Raises:
        JWTError: if the token is expired, malformed, or wrong type.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    if payload.get("type") != "access":
        raise JWTError("Token is not an access token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a refresh JWT.

    Raises:
        JWTError: if the token is expired, malformed, or wrong type.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    if payload.get("type") != "refresh":
        raise JWTError("Token is not a refresh token")
    return payload
