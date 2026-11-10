"""
backend/tests/test_rbac.py
Tests verifying Role-Based Access Control (RBAC) across admin, analyst, and viewer roles.
"""
import pytest
from fastapi import APIRouter, Depends
from httpx import AsyncClient

from app.api.v1.dependencies import require_role
from app.main import app

# Create dynamic test routes to isolate RBAC dependency logic
rbac_router = APIRouter(prefix="/test-rbac")

@rbac_router.get("/admin", dependencies=[Depends(require_role("admin"))])
async def admin_only():
    return {"message": "admin granted"}

@rbac_router.get("/analyst", dependencies=[Depends(require_role("admin", "analyst"))])
async def analyst_or_admin():
    return {"message": "analyst granted"}

@rbac_router.get("/viewer", dependencies=[Depends(require_role("admin", "analyst", "viewer"))])
async def any_authenticated():
    return {"message": "viewer granted"}

app.include_router(rbac_router)


@pytest.mark.asyncio
async def test_admin_access_to_all(client: AsyncClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    r1 = await client.get("/test-rbac/admin", headers=headers)
    assert r1.status_code == 200

    r2 = await client.get("/test-rbac/analyst", headers=headers)
    assert r2.status_code == 200

    r3 = await client.get("/test-rbac/viewer", headers=headers)
    assert r3.status_code == 200


@pytest.mark.asyncio
async def test_analyst_access_restrictions(client: AsyncClient, analyst_token: str):
    headers = {"Authorization": f"Bearer {analyst_token}"}
    # Analyst cannot access admin-only
    r1 = await client.get("/test-rbac/admin", headers=headers)
    assert r1.status_code == 403
    assert r1.json()["error"]["code"] == "FORBIDDEN"

    # Analyst can access analyst route
    r2 = await client.get("/test-rbac/analyst", headers=headers)
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_viewer_access_restrictions(client: AsyncClient, viewer_token: str):
    headers = {"Authorization": f"Bearer {viewer_token}"}
    # Viewer cannot access admin or analyst
    r1 = await client.get("/test-rbac/admin", headers=headers)
    assert r1.status_code == 403

    r2 = await client.get("/test-rbac/analyst", headers=headers)
    assert r2.status_code == 403

    # Viewer can access viewer route
    r3 = await client.get("/test-rbac/viewer", headers=headers)
    assert r3.status_code == 200

