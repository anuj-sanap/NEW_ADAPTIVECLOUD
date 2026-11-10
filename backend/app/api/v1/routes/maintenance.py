"""
backend/app/api/v1/routes/maintenance.py
Endpoints for predictive maintenance, capacity planning, and component exhaustion forecasts.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.db.session import get_db
from app.models.host import Host
from app.models.prediction import MaintenanceForecast
from app.models.user import User
from app.schemas.prediction import HostMaintenanceDetailResponse, MaintenanceForecastResponse
from app.services.maintenance import evaluate_predictive_maintenance

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.get("/forecasts", response_model=list[MaintenanceForecastResponse], summary="List latest maintenance forecasts")
async def list_maintenance_forecasts(
    host_id: Optional[uuid.UUID] = Query(None, description="Filter by host ID"),
    component: Optional[str] = Query(None, description="Filter by component: disk | cpu | memory"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MaintenanceForecast]:
    stmt = select(MaintenanceForecast).order_by(desc(MaintenanceForecast.created_at))

    if host_id:
        stmt = stmt.where(MaintenanceForecast.host_id == host_id)
    if component:
        stmt = stmt.where(MaintenanceForecast.component == component)

    stmt = stmt.offset(offset).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/hosts/{host_id}", response_model=HostMaintenanceDetailResponse, summary="Get host maintenance details")
async def get_host_maintenance(
    host_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HostMaintenanceDetailResponse:
    host_stmt = select(Host).where(Host.id == host_id)
    host_res = await db.execute(host_stmt)
    host = host_res.scalar_one_or_none()
    if not host:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host {host_id} not found",
        )

    # Fetch latest forecasts for this host
    fc_stmt = (
        select(MaintenanceForecast)
        .where(MaintenanceForecast.host_id == host_id)
        .order_by(desc(MaintenanceForecast.created_at))
        .limit(20)
    )
    fc_res = await db.execute(fc_stmt)
    forecasts = list(fc_res.scalars().all())

    # Calculate component health status from forecasts
    component_status = {
        "cpu": "healthy",
        "memory": "healthy",
        "disk": "healthy",
        "services": "healthy",
    }
    disk_eta: Optional[float] = None
    service_risks: list[dict] = []

    for fc in forecasts:
        if fc.component == "disk":
            disk_eta = fc.days_remaining
            if fc.days_remaining < 3.0:
                component_status["disk"] = "critical"
            elif fc.days_remaining < 14.0:
                component_status["disk"] = "warning"
        elif fc.component == "cpu" and fc.details.get("probability_15m", 0) > 0.75:
            component_status["cpu"] = "warning"
        elif fc.component == "memory" and fc.details.get("probability_30m", 0) > 0.75:
            component_status["memory"] = "warning"

    return HostMaintenanceDetailResponse(
        host_id=host.id,
        hostname=host.hostname,
        forecasts=[MaintenanceForecastResponse.model_validate(f) for f in forecasts],
        disk_fill_eta_days=disk_eta,
        service_risks=service_risks,
        component_status=component_status,
    )


@router.post("/evaluate/{host_id}", summary="Run on-demand maintenance evaluation for host")
async def evaluate_host_maintenance(
    host_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host_stmt = select(Host).where(Host.id == host_id)
    host_res = await db.execute(host_stmt)
    if not host_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Host {host_id} not found",
        )

    result = await evaluate_predictive_maintenance(db=db, host_id=host_id)
    return result
