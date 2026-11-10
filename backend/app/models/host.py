"""
backend/app/models/host.py
SQLAlchemy ORM model for monitored hosts (Windows / Linux VMs).
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Host(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A monitored host system (e.g. Windows Server 2022 on GCP).
    Identified by host_id (UUID), authenticating via API key.
    """

    __tablename__ = "hosts"

    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    os_version: Mapped[str] = mapped_column(String(128), nullable=False, default="Windows Server 2022")
    agent_platform: Mapped[str] = mapped_column(String(64), nullable=False, default="windows")
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="offline", index=True)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    def __repr__(self) -> str:
        return f"<Host id={self.id} hostname={self.hostname!r} status={self.status}>"

