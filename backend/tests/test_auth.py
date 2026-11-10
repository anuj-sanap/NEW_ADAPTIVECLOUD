"""
backend/tests/test_auth.py
Unit and integration tests for authentication and profile routes.
"""
import pytest
from httpx import AsyncClient
from app.models.user import User


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_admin_user: User):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_test", "password": "adminpass123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, test_admin_user: User):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_test", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "does_not_exist", "password": "somepassword"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_auth_me_success(client: AsyncClient, admin_token: str, test_admin_user: User):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == test_admin_user.username
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_auth_me_unauthorized(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_refresh_token_flow(client: AsyncClient, test_admin_user: User):
    # Step 1: Login to get refresh token
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin_test", "password": "adminpass123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Step 2: Use refresh token to obtain fresh access token
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

