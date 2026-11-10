"""
backend/tests/test_detection_incidents_api.py
Integration tests for detection, classification, incident correlation,
and model management APIs.
"""
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_api_key
from app.models.detection import Classification, Detection
from app.models.host import Host
from app.models.incident import Incident, IncidentItem
from app.models.ml import MLModel
from ml.features.feature_map import CANONICAL_FEATURES

settings = get_settings()


@pytest.mark.asyncio
async def test_detections_and_classifications_query(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    host = Host(
        hostname="worker-detection-test",
        os_version="Windows Server 2022",
        agent_platform="windows",
        api_key_hash=hash_api_key(settings.AGENT_API_KEY),
    )
    db_session.add(host)
    await db_session.commit()
    await db_session.refresh(host)

    now = datetime.now(UTC)
    det = Detection(
        host_id=host.id,
        ts=now,
        anomaly_score=0.88,
        is_attack=True,
        status="open",
    )
    db_session.add(det)
    await db_session.commit()
    await db_session.refresh(det)

    clf = Classification(
        host_id=host.id,
        ts=now,
        detection_id=det.id,
        label="brute_force",
        confidence=0.99,
        probs={"brute_force": 0.99, "benign": 0.01},
    )
    db_session.add(clf)
    await db_session.commit()
    await db_session.refresh(clf)

    # 1. Query detections
    det_resp = await client.get(
        "/api/v1/detections?is_attack=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert det_resp.status_code == 200
    det_data = det_resp.json()
    assert det_data["total"] >= 1
    assert det_data["items"][0]["anomaly_score"] == 0.88

    # 2. Query classifications
    clf_resp = await client.get(
        f"/api/v1/classifications?detection_id={det.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert clf_resp.status_code == 200
    clf_data = clf_resp.json()
    assert clf_data["total"] == 1
    assert clf_data["items"][0]["label"] == "brute_force"


@pytest.mark.asyncio
async def test_incidents_listing_and_detail(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    incident = Incident(
        title="Security Incident: Brute Force from 198.51.100.99",
        severity="high",
        status="open",
        description="Multiple failed logons detected",
        summary={"src_ip": "198.51.100.99", "event_count": 5},
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)

    item = IncidentItem(
        incident_id=incident.id,
        item_type="security_event",
        item_id=uuid.uuid4(),
        details={"rule_id": "100001"},
    )
    db_session.add(item)
    await db_session.commit()

    # Query list
    inc_resp = await client.get(
        "/api/v1/incidents?severity=high",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert inc_resp.status_code == 200
    assert inc_resp.json()["total"] >= 1

    # Query detail
    detail_resp = await client.get(
        f"/api/v1/incidents/{incident.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert detail_data["id"] == str(incident.id)
    assert len(detail_data["items"]) == 1
    assert detail_data["items"][0]["item_type"] == "security_event"


@pytest.mark.asyncio
async def test_models_registry_and_activation(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
    viewer_token: str,
):
    m1 = MLModel(
        name="random_forest",
        task="attack_classification",
        version="1.0.0",
        metrics={"accuracy": 0.9994, "f1_macro": 0.9994},
        artifact_path="ml/models/random_forest.joblib",
        status="candidate",
    )
    m2 = MLModel(
        name="xgboost",
        task="attack_classification",
        version="1.0.0",
        metrics={"accuracy": 1.0, "f1_macro": 1.0},
        artifact_path="ml/models/xgboost.joblib",
        status="active",
    )
    db_session.add_all([m1, m2])
    await db_session.commit()
    await db_session.refresh(m1)
    await db_session.refresh(m2)

    # 1. List models
    list_resp = await client.get(
        "/api/v1/models",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert list_resp.status_code == 200
    models_list = list_resp.json()
    assert len(models_list) >= 2

    # 2. Get model metrics
    metrics_resp = await client.get(
        f"/api/v1/models/{m2.id}/metrics",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert metrics_resp.status_code == 200
    assert metrics_resp.json()["metrics"]["f1_macro"] == 1.0

    # 3. Non-admin cannot activate model
    forbidden_resp = await client.post(
        f"/api/v1/models/{m1.id}/activate",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert forbidden_resp.status_code == 403

    # 4. Admin activates m1 (promoting to active, demoting m2 to candidate)
    act_resp = await client.post(
        f"/api/v1/models/{m1.id}/activate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert act_resp.status_code == 200
    assert act_resp.json()["status"] == "activated"
    assert act_resp.json()["name"] == "random_forest"

    # Verify statuses updated in DB
    await db_session.refresh(m1)
    await db_session.refresh(m2)
    assert m1.status == "active"
    assert m2.status == "candidate"


@pytest.mark.asyncio
async def test_flow_ingest_and_realtime_detection(
    client: AsyncClient,
    db_session: AsyncSession,
):
    host = Host(
        hostname="worker-flow-stream-test",
        os_version="Windows Server 2022",
        agent_platform="windows",
        ip_address="198.51.100.5",
        status="online",
        api_key_hash=hash_api_key(settings.AGENT_API_KEY),
    )
    db_session.add(host)
    await db_session.commit()
    await db_session.refresh(host)

    # Create flow feature payload with 28 canonical features
    sample_flow = {f: 15.0 for f in CANONICAL_FEATURES}
    sample_flow["flow_pkts_s"] = 5000.0  # Volumetric anomaly

    resp = await client.post(
        "/api/v1/agents/flows",
        json={
            "ts": datetime.now(UTC).isoformat(),
            "features": sample_flow,
        },
        headers={"X-API-Key": settings.AGENT_API_KEY},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "accepted"
    assert "detections" in data
    assert len(data["detections"]) == 1

