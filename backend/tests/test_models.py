"""
backend/tests/test_models.py
One-row-per-table insert and retrieval test across all 20 SQLAlchemy models
to guarantee schema validity, type consistency, and foreign key integrity.
"""
from datetime import UTC, datetime
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditLog,
    Blocklist,
    Classification,
    Detection,
    DriftEvent,
    FeedbackLabel,
    FlowFeature,
    Host,
    Incident,
    IncidentItem,
    MaintenanceForecast,
    Metric,
    MLModel,
    ModelEvaluation,
    Prediction,
    RCAReport,
    ResponseAction,
    RetrainingJob,
    SecurityEvent,
    User,
)


@pytest.mark.asyncio
async def test_insert_one_row_per_table(db_session: AsyncSession):
    now = datetime.now(UTC)

    # 1. User
    user = User(
        username="db_tester",
        email="tester@test.local",
        password_hash="hashed_pw_here",
        role="admin",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    assert user.id is not None

    # 2. Host
    host = Host(
        hostname="WIN-TEST-VM01",
        os_version="Windows Server 2022",
        agent_platform="windows",
        ip_address="100.64.0.10",
        status="online",
        api_key_hash="hashed_key_here",
    )
    db_session.add(host)
    await db_session.flush()
    assert host.id is not None

    # 3. Metric
    metric = Metric(
        host_id=host.id,
        ts=now,
        cpu=45.2,
        mem=60.8,
        disk=102400.0,
        net_in=50000.0,
        net_out=25000.0,
        load=1.2,
        proc_count=85,
        conn_count=12,
        extra={"top_process": "svchost.exe"},
    )
    db_session.add(metric)
    await db_session.flush()
    assert metric.id is not None

    # 4. SecurityEvent
    event = SecurityEvent(
        host_id=host.id,
        ts=now,
        source="wazuh",
        rule_id="5710",
        level=10,
        category="authentication_failure",
        src_ip="192.168.1.100",
        user="Administrator",
        event_id=4625,
        raw={"message": "Failed logon attempt"},
    )
    db_session.add(event)
    await db_session.flush()
    assert event.id is not None

    # 5. FlowFeature
    flow = FlowFeature(
        host_id=host.id,
        ts=now,
        features={"syn_rate": 20.5, "ack_rate": 15.2, "port_entropy": 0.8},
    )
    db_session.add(flow)
    await db_session.flush()
    assert flow.id is not None

    # 6. Detection
    detection = Detection(
        host_id=host.id,
        ts=now,
        anomaly_score=0.88,
        is_attack=True,
        status="open",
    )
    db_session.add(detection)
    await db_session.flush()
    assert detection.id is not None

    # 7. Classification
    classification = Classification(
        host_id=host.id,
        ts=now,
        detection_id=detection.id,
        label="brute_force",
        confidence=0.92,
        probs={"benign": 0.05, "brute_force": 0.92, "ddos": 0.03},
    )
    db_session.add(classification)
    await db_session.flush()
    assert classification.id is not None

    # 8. Incident
    incident = Incident(
        title="Test Incident",
        severity="high",
        status="open",
        assigned_to=user.id,
        description="Correlated attack",
        summary={"detection_count": 1},
    )
    db_session.add(incident)
    await db_session.flush()
    assert incident.id is not None

    # 9. IncidentItem
    item = IncidentItem(
        incident_id=incident.id,
        item_type="detection",
        item_id=detection.id,
        details={"score": 0.88},
    )
    db_session.add(item)
    await db_session.flush()
    assert item.id is not None

    # 10. RCAReport
    rca = RCAReport(
        incident_id=incident.id,
        probable_cause="Repeated SSH/RDP dictionary attack",
        source_ips=["192.168.1.100"],
        affected_hosts=["WIN-TEST-VM01"],
        evidence={"event_id": 4625, "count": 25},
        timeline=[{"ts": now.isoformat(), "action": "First failed login"}],
    )
    db_session.add(rca)
    await db_session.flush()
    assert rca.id is not None

    # 11. Prediction
    prediction = Prediction(
        host_id=host.id,
        ts=now,
        kind="cpu",
        horizon_min=15,
        value=89.5,
        probability=0.85,
    )
    db_session.add(prediction)
    await db_session.flush()
    assert prediction.id is not None

    # 12. MaintenanceForecast
    forecast = MaintenanceForecast(
        host_id=host.id,
        component="disk",
        metric_name="C: free space",
        days_remaining=14.5,
        confidence=0.9,
        details={"growth_gb_per_day": 1.2},
    )
    db_session.add(forecast)
    await db_session.flush()
    assert forecast.id is not None

    # 13. ResponseAction
    action = ResponseAction(
        host_id=host.id,
        incident_id=incident.id,
        action="block_ip",
        status="executed",
        target="192.168.1.100",
        initiated_by="system",
        result={"firewall_rule_added": True},
    )
    db_session.add(action)
    await db_session.flush()
    assert action.id is not None

    # 14. Blocklist
    blocked = Blocklist(
        ip="192.168.1.100",
        reason="Repeated authentication failure",
        active=True,
    )
    db_session.add(blocked)
    await db_session.flush()
    assert blocked.id is not None

    # 15. MLModel
    ml_model = MLModel(
        name="xgboost_attack_classifier",
        task="attack_classification",
        version="v1.0.0",
        metrics={"accuracy": 0.94, "f1": 0.93},
        artifact_path="ml/models/model_v1.0.0.joblib",
        status="active",
    )
    db_session.add(ml_model)
    await db_session.flush()
    assert ml_model.id is not None

    # 16. ModelEvaluation
    eval_record = ModelEvaluation(
        model_id=ml_model.id,
        dataset_name="heldout_test_set_v1",
        metrics={"precision": 0.95, "recall": 0.92},
    )
    db_session.add(eval_record)
    await db_session.flush()
    assert eval_record.id is not None

    # 17. DriftEvent
    drift = DriftEvent(
        model_id=ml_model.id,
        feature_name="net_in",
        drift_score=0.18,
        p_value=0.01,
        is_drift=True,
        details={"ks_statistic": 0.18},
    )
    db_session.add(drift)
    await db_session.flush()
    assert drift.id is not None

    # 18. RetrainingJob
    job = RetrainingJob(
        model_id=ml_model.id,
        status="completed",
        dataset_size=1200,
        started_at=now,
        completed_at=now,
        metrics_summary={"new_f1": 0.96},
    )
    db_session.add(job)
    await db_session.flush()
    assert job.id is not None

    # 19. FeedbackLabel
    feedback = FeedbackLabel(
        detection_id=detection.id,
        analyst_id=user.id,
        true_label="brute_force",
        comments="Confirmed by analyst inspection of event log",
    )
    db_session.add(feedback)
    await db_session.flush()
    assert feedback.id is not None

    # 20. AuditLog
    audit = AuditLog(
        user_id=user.id,
        action="BLOCK_IP_TRIGGERED",
        resource_type="response_action",
        resource_id=str(action.id),
        details={"target": "192.168.1.100"},
        ip_address="127.0.0.1",
    )
    db_session.add(audit)
    await db_session.flush()
    assert audit.id is not None

    # Commit the transaction
    await db_session.commit()

    # Verify query retrieves the records
    user_query = await db_session.execute(select(User).where(User.id == user.id))
    retrieved_user = user_query.scalar_one()
    assert retrieved_user.username == "db_tester"

    metric_query = await db_session.execute(select(Metric).where(Metric.id == metric.id))
    retrieved_metric = metric_query.scalar_one()
    assert retrieved_metric.cpu == 45.2

    block_query = await db_session.execute(select(Blocklist).where(Blocklist.id == blocked.id))
    retrieved_block = block_query.scalar_one()
    assert retrieved_block.ip == "192.168.1.100"
