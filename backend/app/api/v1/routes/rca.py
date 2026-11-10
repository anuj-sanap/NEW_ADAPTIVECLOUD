"""
backend/app/api/v1/routes/rca.py
API endpoints for Root Cause Analysis (RCA) reporting and incident forensics.
- GET  /rca/{incident_id}: Retrieve RCA report for a security incident.
- POST /rca/{incident_id}/regenerate: Re-analyze telemetry and synthesize fresh RCA report.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_role
from app.db.session import get_db
from app.models.incident import Incident, RCAReport
from app.models.user import User
from app.schemas.rca import RCAReportResponse
from app.services.rca import generate_rca_report

router = APIRouter(prefix="/rca", tags=["rca"])

_viewer = Depends(require_role("admin", "analyst", "viewer"))
_analyst = Depends(require_role("admin", "analyst"))


def _format_rca_response(rca: RCAReport) -> RCAReportResponse:
    evidence = rca.evidence or {}
    return RCAReportResponse(
        id=rca.id,
        incident_id=rca.incident_id,
        probable_cause=rca.probable_cause,
        confidence=evidence.get("confidence", 0.85),
        source_ips=rca.source_ips,
        affected_hosts=rca.affected_hosts,
        evidence=evidence.get("correlated_patterns", {}),
        timeline=rca.timeline,
        recommended_actions=evidence.get("recommended_actions", []),
        plain_english_summary=evidence.get("plain_english_summary", ""),
        created_at=rca.created_at,
        updated_at=rca.updated_at,
    )


@router.get(
    "/{incident_id}",
    response_model=RCAReportResponse,
    summary="Retrieve forensic RCA report for an incident",
)
async def get_incident_rca(
    incident_id: uuid.UUID,
    _user: Annotated[User, _viewer],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RCAReportResponse:
    # Check if incident exists
    stmt = select(Incident).where(Incident.id == incident_id)
    incident = (await db.execute(stmt)).scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )

    # Check if RCA already exists
    rca_stmt = select(RCAReport).where(RCAReport.incident_id == incident_id)
    rca = (await db.execute(rca_stmt)).scalar_one_or_none()

    if not rca:
        # Generate on the fly
        rca = await generate_rca_report(db, incident_id)

    return _format_rca_response(rca)


@router.post(
    "/{incident_id}/regenerate",
    response_model=RCAReportResponse,
    summary="Regenerate forensic RCA report with latest telemetry",
)
async def regenerate_incident_rca(
    incident_id: uuid.UUID,
    _user: Annotated[User, _analyst],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RCAReportResponse:
    stmt = select(Incident).where(Incident.id == incident_id)
    incident = (await db.execute(stmt)).scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found",
        )

    rca = await generate_rca_report(db, incident_id)
    return _format_rca_response(rca)
