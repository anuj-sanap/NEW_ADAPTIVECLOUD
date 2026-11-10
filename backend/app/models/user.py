"""
backend/app/models/user.py
SQLAlchemy ORM model for application users.
"""
import uuid
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Application user with role-based access."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("admin", "analyst", "viewer", name="user_role_enum"),
        nullable=False,
        default="viewer",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role}>"
