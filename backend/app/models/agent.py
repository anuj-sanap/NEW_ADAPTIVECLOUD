"""
backend/app/models/agent.py
SQLAlchemy ORM model for registered monitoring agents (Windows VMs).
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Agent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A registered Windows Server VM running the monitoring agent.
    The api_key_hash stores the bcrypt hash of the secret key.
    The raw key is returned only once at creation time.
    """

    __tablename__ = "agents"

    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    os_version: Mapped[str] = mapped_column(String(128), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("online", "offline", name="agent_status_enum"),
        nullable=False,
        default="offline",
        index=True,
    )
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<Agent id={self.id} hostname={self.hostname!r} status={self.status}>"
