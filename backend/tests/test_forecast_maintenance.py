"""
backend/tests/test_forecast_maintenance.py
Comprehensive test suite for threat forecasting, predictive maintenance,
outcome backfilling, scheduler execution, and dashboard telemetry API.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_api_key
from app.models.host import Host
from app.models.metric import Metric
from app.models.prediction import MaintenanceForecast, Prediction
from app.models.security_event import SecurityEvent
from app.services.maintenance import (
    backfill_observed_outcomes,
    evaluate_predictive_maintenance,
)
from app.services.scheduler import telemetry_scheduler
from app.services.threat_prediction import generate_threat_forecasts


@pytest.mark.asyncio
async def test_threat_forecasting_cold_start(db_session: AsyncSession):
    """Honest cold start: below threshold must return not_available."""
    host = Host(hostname="WORKER-COLD-01", ip_address="100.64.0.21", status="online", api_key_hash=hash_api_key("test_key"))
    db_session.add(host)
    await db_session.commit()
    await db_session.refresh(host)

    # Add only 2 events (less than 12 intervals)
    ev = SecurityEvent(
        host_id=host.id,
        ts=datetime.now(UTC),
        source="agent",
        category="brute_force",
        level=4,
    )
    db_session.add(ev)
    await db_session.commit()

    result = await generate_threat_forecasts(db_session, host.id, horizon_min=15)
    assert result["status"] == "not_available"
    assert "Collecting telemetry data" in result["message"]
    assert result["samples_collected"] <= 2
    assert result["samples_required"] == 12


@pytest.mark.asyncio
async def test_threat_forecasting_ready(db_session: AsyncSession):
    """When sufficient intervals exist, forecasting produces calibrated probabilities."""
    host = Host(hostname="WORKER-WARM-01", ip_address="100.64.0.22", status="online", api_key_hash=hash_api_key("test_key"))
    db_session.add(host)
    await db_session.commit()
    await db_session.refresh(host)

    now = datetime.now(UTC)
    # Add events spanning 15 distinct 5-minute intervals (1.25 hours)
    for i in range(15):
        t = now - timedelta(minutes=(15 - i) * 5)
        ev = SecurityEvent(
            host_id=host.id,
            ts=t,
            source="winevent",
            event_id=4625 if i % 2 == 0 else 4624,
            category="brute_force" if i % 2 == 0 else "logon",
            level=5 if i % 2 == 0 else 3,
            src_ip="198.51.100.10",
        )
        db_session.add(ev)
    await db_session.commit()

    result = await generate_threat_forecasts(db_session, host.id, horizon_min=15)
    assert result["status"] == "ready"
    assert result["horizon_min"] == 15
    assert len(result["predictions"]) >= 5
    # Verify predictions were persisted
    stmt = select(Prediction).where(Prediction.host_id == host.id, Prediction.kind == "threat")
    preds = (await db_session.execute(stmt)).scalars().all()
    assert len(preds) >= 5


@pytest.mark.asyncio
async def test_predictive_maintenance_evaluation(db_session: AsyncSession):
    host = Host(hostname="WORKER-MAINT-01", ip_address="100.64.0.23", status="online", api_key_hash=hash_api_key("test_key"))
    db_session.add(host)
    await db_session.commit()
    await db_session.refresh(host)

    now = datetime.now(UTC)
    # Under 5 metrics -> not_available
    m_single = Metric(host_id=host.id, ts=now, cpu=50.0, mem=60.0, disk=70.0)
    db_session.add(m_single)
    await db_session.commit()

    res_cold = await evaluate_predictive_maintenance(db_session, host.id)
    assert res_cold["status"] == "not_available"

    # Add sufficient metrics with rising CPU & disk
    for i in range(10):
        t = now - timedelta(minutes=(10 - i) * 2)
        m = Metric(
            host_id=host.id,
            ts=t,
            cpu=50.0 + (i * 4.0),   # 50% -> 86%
            mem=60.0 + (i * 2.0),   # 60% -> 78%
            disk=80.0 + (i * 0.5),  # 80% -> 84.5%
            extra={"services": {"Spooler": "running", "w32time": "running"}},
        )
        db_session.add(m)
    await db_session.commit()

    res_ready = await evaluate_predictive_maintenance(db_session, host.id)
    assert res_ready["status"] == "ready"
    assert "cpu_breach_prob_15m" in res_ready
    assert "mem_breach_prob_30m" in res_ready
    assert "days_to_disk_full" in res_ready
    assert res_ready["days_to_disk_full"] > 0

    # Verify forecasts were persisted
    fc_stmt = select(MaintenanceForecast).where(MaintenanceForecast.host_id == host.id)
    forecasts = (await db_session.execute(fc_stmt)).scalars().all()
    assert len(forecasts) >= 3


@pytest.mark.asyncio
async def test_prediction_outcome_backfilling(db_session: AsyncSession):
    """Verify empirical outcome backfilling once forecast horizon has elapsed."""
    host = Host(hostname="WORKER-BACKFILL-01", ip_address="100.64.0.24", status="online", api_key_hash=hash_api_key("test_key"))
    db_session.add(host)
    await db_session.commit()
    await db_session.refresh(host)

    now = datetime.now(UTC)
    # Forecast made 20 minutes ago for horizon 15m (target time = now - 5m)
    past_prediction = Prediction(
        host_id=host.id,
        ts=now - timedelta(minutes=20),
        kind="cpu",
        horizon_min=15,
        value=88.0,
        probability=0.85,
        outcome_observed=None,
    )
    db_session.add(past_prediction)

    # Actual metric recorded at target time (now - 5m) with CPU = 89.2 (>85% breach)
    actual_metric = Metric(
        host_id=host.id,
        ts=now - timedelta(minutes=5),
        cpu=89.2,
        mem=60.0,
        disk=70.0,
    )
    db_session.add(actual_metric)
    await db_session.commit()

    backfilled = await backfill_observed_outcomes(db_session)
    assert backfilled >= 1

    await db_session.refresh(past_prediction)
    assert past_prediction.outcome_observed == 1.0


@pytest.mark.asyncio
async def test_scheduler_run_once(db_session: AsyncSession):
    """Test telemetry scheduler run_once execution cycle."""
    stats = await telemetry_scheduler.run_once()
    assert "hosts_evaluated" in stats
    assert "backfilled_predictions" in stats
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_dashboard_and_maintenance_apis(
    client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
):
    headers = {"Authorization": f"Bearer {admin_token}"}

    host = Host(hostname="WORKER-API-01", ip_address="100.64.0.25", status="online", api_key_hash=hash_api_key("test_key"))
    db_session.add(host)
    await db_session.commit()
    await db_session.refresh(host)

    # 1. GET /api/v1/dashboard/summary
    dash_res = await client.get("/api/v1/dashboard/summary", headers=headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert "host_health_score" in dash_data
    assert "active_incidents" in dash_data
    assert "attack_counts_24h" in dash_data
    assert "top_risks" in dash_data

    # 2. GET /api/v1/maintenance/forecasts
    fc_res = await client.get("/api/v1/maintenance/forecasts", headers=headers)
    assert fc_res.status_code == 200
    assert isinstance(fc_res.json(), list)

    # 3. GET /api/v1/maintenance/hosts/{id}
    maint_host_res = await client.get(f"/api/v1/maintenance/hosts/{host.id}", headers=headers)
    assert maint_host_res.status_code == 200
    maint_host_data = maint_host_res.json()
    assert maint_host_data["host_id"] == str(host.id)
    assert maint_host_data["hostname"] == "WORKER-API-01"
    assert "component_status" in maint_host_data

    # 4. GET /api/v1/predictions
    pred_res = await client.get("/api/v1/predictions", headers=headers)
    assert pred_res.status_code == 200
    assert isinstance(pred_res.json(), list)
