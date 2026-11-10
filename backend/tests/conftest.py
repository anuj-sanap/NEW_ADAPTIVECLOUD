"""
backend/tests/conftest.py
Pytest test fixtures, async SQLite test database, and mock FastAPI client.
"""
from collections.abc import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User

# Use in-memory SQLite with StaticPool for fast, isolated testing
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create all tables in fresh SQLite in-memory instance, override get_db, yield session, drop tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        async def _override_db():
            yield session

        app.dependency_overrides[get_db] = _override_db
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def test_admin_user(db_session: AsyncSession) -> User:
    admin = User(
        username="admin_test",
        email="admin@test.local",
        password_hash=hash_password("adminpass123"),
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture(scope="function")
async def test_analyst_user(db_session: AsyncSession) -> User:
    analyst = User(
        username="analyst_test",
        email="analyst@test.local",
        password_hash=hash_password("analystpass123"),
        role="analyst",
        is_active=True,
    )
    db_session.add(analyst)
    await db_session.commit()
    await db_session.refresh(analyst)
    return analyst


@pytest_asyncio.fixture(scope="function")
async def test_viewer_user(db_session: AsyncSession) -> User:
    viewer = User(
        username="viewer_test",
        email="viewer@test.local",
        password_hash=hash_password("viewerpass123"),
        role="viewer",
        is_active=True,
    )
    db_session.add(viewer)
    await db_session.commit()
    await db_session.refresh(viewer)
    return viewer


@pytest.fixture
def admin_token(test_admin_user: User) -> str:
    return create_access_token(test_admin_user.id, test_admin_user.role)


@pytest.fixture
def analyst_token(test_analyst_user: User) -> str:
    return create_access_token(test_analyst_user.id, test_analyst_user.role)


@pytest.fixture
def viewer_token(test_viewer_user: User) -> str:
    return create_access_token(test_viewer_user.id, test_viewer_user.role)
