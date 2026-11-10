"""
backend/app/api/v1/routes/dashboard.py
Unified dashboard telemetry endpoint aggregating host health score, active incidents,
24-hour attack counts by category, and prioritized top risks.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.db.session import get_db
from app.models.detection import Classification
from app.models.host import Host
from app.models.incident import Incident
from app.models.prediction import MaintenanceForecast, Prediction
from app.models.security_event import SecurityEvent
from app.models.user import User
from app.schemas.prediction import DashboardSummaryResponse, TopRiskItem

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse, summary="Get unified dashboard summary")
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardSummaryResponse:
    now = datetime.now(UTC)
    last_24h = now - timedelta(hours=24)

    # 1. Hosts count
    host_stmt = select(Host)
    host_res = await db.execute(host_stmt)
    hosts = list(host_res.scalars().all())
    total_hosts = len(hosts)
    online_hosts = sum(1 for h in hosts if h.status == "online")

    # 2. Active Incidents (open, investigating)
    inc_stmt = select(func.count(Incident.id)).where(Incident.status.in_(["open", "investigating"]))
    inc_res = await db.execute(inc_stmt)
    active_incidents = inc_res.scalar_one() or 0

    # 3. 24h Attack counts
    attack_counts: dict[str, int] = defaultdict(int)
    cl_stmt = (
        select(Classification.label, func.count(Classification.id))
        .where(Classification.ts >= last_24h, Classification.label != "benign")
        .group_by(Classification.label)
    )
    cl_res = await db.execute(cl_stmt)
    for label, count in cl_res.all():
        attack_counts[label] += count

    ev_stmt = (
        select(SecurityEvent.category, func.count(SecurityEvent.id))
        .where(SecurityEvent.ts >= last_24h, SecurityEvent.category.is_not(None))
        .group_by(SecurityEvent.category)
    )
    ev_res = await db.execute(ev_stmt)
    for category, count in ev_res.all():
        if category and category != "benign":
            attack_counts[category] += count

    # Ensure all standard labels are represented
    for standard_label in ["brute_force", "ddos", "port_scan", "unauthorized_access", "suspicious_process"]:
        if standard_label not in attack_counts:
            attack_counts[standard_label] = 0

    # 4. Top Risks
    top_risks: list[TopRiskItem] = []
    host_map = {h.id: h.hostname for h in hosts}

    # Query latest high-probability threat predictions
    pred_stmt = (
        select(Prediction)
        .where(Prediction.ts >= now - timedelta(hours=2), Prediction.probability >= 0.5)
        .order_by(desc(Prediction.probability))
        .limit(5)
    )
    pred_res = await db.execute(pred_stmt)
    for p in pred_res.scalars().all():
        sev = "critical" if p.probability >= 0.8 else "high"
        top_risks.append(
            TopRiskItem(
                category="threat" if p.kind == "threat" else "maintenance",
                title=f"Predicted {p.kind.upper()} breach/attack within {p.horizon_min}m",
                host_id=p.host_id,
                hostname=host_map.get(p.host_id, "unknown"),
                probability=p.probability,
                eta_minutes=p.horizon_min,
                severity=sev,
            )
        )

    # Query urgent disk exhaustion forecasts (< 7 days)
    fc_stmt = (
        select(MaintenanceForecast)
        .where(MaintenanceForecast.component == "disk", MaintenanceForecast.days_remaining <= 7.0)
        .order_by(MaintenanceForecast.days_remaining.asc())
        .limit(5)
    )
    fc_res = await db.execute(fc_stmt)
    for fc in fc_res.scalars().all():
        top_risks.append(
            TopRiskItem(
                category="maintenance",
                title=f"Disk capacity exhaustion in {fc.days_remaining:.1f} days",
                host_id=fc.host_id,
                hostname=host_map.get(fc.host_id, "unknown"),
                probability=fc.confidence,
                eta_minutes=int(fc.days_remaining * 1440),
                severity="critical" if fc.days_remaining < 3.0 else "high",
            )
        )

    # 5. Composite Health Score Calculation (0 - 100)
    # Starts at 100. Deductions:
    # - 15 points per active incident
    # - 5 points per offline host
    # - 10 points per critical risk item
    base_score = 100.0
    incident_deduction = min(50.0, active_incidents * 15.0)
    offline_deduction = (total_hosts - online_hosts) * 5.0 if total_hosts > 0 else 0.0
    risk_deduction = sum(10.0 if r.severity == "critical" else 5.0 for r in top_risks[:5])

    health_score = max(0.0, round(base_score - incident_deduction - offline_deduction - risk_deduction, 1))

    return DashboardSummaryResponse(
        host_health_score=health_score,
        total_hosts=total_hosts,
        online_hosts=online_hosts,
        active_incidents=active_incidents,
        attack_counts_24h=dict(attack_counts),
        top_risks=top_risks[:10],
    )
