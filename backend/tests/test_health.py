"""
backend/tests/test_health.py
Health check endpoint tests.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_healthy(client: AsyncClient):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert "version" in data
    assert "timestamp" in data

