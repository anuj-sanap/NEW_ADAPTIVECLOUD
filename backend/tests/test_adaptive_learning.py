"""
backend/tests/test_adaptive_learning.py
Comprehensive test suite for statistical drift detection (PSI, KS),
analyst active learning feedback, experience replay retraining, and Champion/Challenger promotion gates.
"""
from __future__ import annotations

import uuid
import numpy as np
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ml import FeedbackLabel, MLModel, RetrainingJob
from ml.learning.drift import calculate_ks, calculate_psi
from ml.learning.retrain import evaluate_promotion_gate


def test_psi_calculation_known_distributions():
    np.random.seed(42)
    # Identical distributions -> PSI near 0
    ref = np.random.normal(100, 15, size=2000)
    curr_identical = np.random.normal(100, 15, size=2000)
    psi_stable = calculate_psi(ref, curr_identical)
    assert psi_stable < 0.05, f"Expected stable PSI < 0.05, got {psi_stable}"

    # Significant concept/feature drift (mean shifted by 25 units) -> PSI >= 0.25
    curr_shifted = np.random.normal(130, 15, size=2000)
    psi_drifted = calculate_psi(ref, curr_shifted)
    assert psi_drifted >= 0.25, f"Expected drifted PSI >= 0.25, got {psi_drifted}"


def test_ks_statistic_known_distributions():
    np.random.seed(42)
    # Identical distributions -> high p-value, low statistic
    ref = np.random.normal(50, 10, size=1000)
    curr_identical = np.random.normal(50, 10, size=1000)
    stat, p_val = calculate_ks(ref, curr_identical)
    assert p_val > 0.05
    assert stat < 0.10

    # Shifted distribution -> low p-value, high statistic
    curr_shifted = np.random.normal(70, 10, size=1000)
    stat_drift, p_val_drift = calculate_ks(ref, curr_shifted)
    assert p_val_drift < 0.001
    assert stat_drift > 0.40


def test_champion_challenger_promotion_gate():
    champ_metrics = {
        "macro_f1": 0.850,
        "per_class_recall": {
            "benign": 0.980,
            "brute_force": 0.820,
            "ddos": 0.880,
            "port_scan": 0.800,
        },
    }

    # Case A: Valid Challenger with +0.020 F1 and maintained recalls -> PROMOTE
    challenger_valid = {
        "macro_f1": 0.870,
        "per_class_recall": {
            "benign": 0.980,
            "brute_force": 0.840,
            "ddos": 0.890,
            "port_scan": 0.810,
        },
    }
    can_promote, reasons = evaluate_promotion_gate(champ_metrics, challenger_valid, min_f1_margin=0.005)
    assert can_promote is True
    assert any("improved" in r for r in reasons)

    # Case B: Insufficient Macro-F1 improvement (+0.002 < 0.005) -> REJECT
    challenger_low_f1 = {
        "macro_f1": 0.852,
        "per_class_recall": {
            "benign": 0.980,
            "brute_force": 0.830,
            "ddos": 0.880,
            "port_scan": 0.810,
        },
    }
    can_promote, reasons = evaluate_promotion_gate(champ_metrics, challenger_low_f1, min_f1_margin=0.005)
    assert can_promote is False
    assert any("did not achieve required margin" in r for r in reasons)

    # Case C: Macro-F1 improved but brute_force recall dropped from 0.820 to 0.720 (-0.100) -> REJECT
    challenger_degraded_recall = {
        "macro_f1": 0.890,
        "per_class_recall": {
            "benign": 0.980,
            "brute_force": 0.720,
            "ddos": 0.920,
            "port_scan": 0.850,
        },
    }
    can_promote, reasons = evaluate_promotion_gate(champ_metrics, challenger_degraded_recall, recall_tolerance=0.05)
    assert can_promote is False
    assert any("degraded beyond tolerance" in r for r in reasons)

    # Case D: Benign recall degraded (false alarm spike from 0.980 to 0.950) -> REJECT
    challenger_bad_benign = {
        "macro_f1": 0.880,
        "per_class_recall": {
            "benign": 0.950,
            "brute_force": 0.840,
            "ddos": 0.890,
            "port_scan": 0.820,
        },
    }
    can_promote, reasons = evaluate_promotion_gate(champ_metrics, challenger_bad_benign)
    assert can_promote is False
    assert any("Benign recall degraded" in r for r in reasons)


@pytest.mark.asyncio
async def test_feedback_submission_and_retraining_apis(
    client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. POST /api/v1/learning/feedback
    fb_res = await client.post(
        "/api/v1/learning/feedback",
        json={
            "true_label": "brute_force",
            "comments": "Confirmed persistent RDP password spray by analyst",
        },
        headers=headers,
    )
    assert fb_res.status_code == 201
    fb_data = fb_res.json()
    assert fb_data["true_label"] == "brute_force"

    # Verify persisted in DB
    stmt = select(FeedbackLabel).where(FeedbackLabel.id == uuid.UUID(fb_data["id"]))
    fb_row = (await db_session.execute(stmt)).scalar_one_or_none()
    assert fb_row is not None

    # 2. POST /api/v1/learning/feedback with invalid label -> 400
    bad_res = await client.post(
        "/api/v1/learning/feedback",
        json={"true_label": "invalid_fake_label"},
        headers=headers,
    )
    assert bad_res.status_code == 400

    # 3. POST /api/v1/learning/drift/check
    drift_check_res = await client.post("/api/v1/learning/drift/check", headers=headers)
    assert drift_check_res.status_code == 200
    drift_check_data = drift_check_res.json()
    assert "overall_drift" in drift_check_data
    assert "mean_psi" in drift_check_data

    # 4. GET /api/v1/learning/drift
    drift_list_res = await client.get("/api/v1/learning/drift", headers=headers)
    assert drift_list_res.status_code == 200
    assert isinstance(drift_list_res.json(), list)

    # 5. POST /api/v1/learning/retrain (Admin)
    retrain_res = await client.post(
        "/api/v1/learning/retrain",
        json={"force": True, "replay_ratio": 0.70},
        headers=headers,
    )
    assert retrain_res.status_code == 202
    job_data = retrain_res.json()
    job_id = job_data["id"]
    assert job_data["status"] in ("candidate_ready", "rejected", "running")

    # 6. GET /api/v1/learning/jobs
    jobs_res = await client.get("/api/v1/learning/jobs", headers=headers)
    assert jobs_res.status_code == 200
    assert any(j["id"] == job_id for j in jobs_res.json())

    # 7. POST /api/v1/learning/jobs/{id}/reject
    reject_res = await client.post(
        f"/api/v1/learning/jobs/{job_id}/reject?reason=Manual+validation+hold",
        headers=headers,
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["decision"] == "rejected"

    # 8. POST /api/v1/learning/jobs/{id}/promote
    # If job has model_id, test promotion
    stmt_job = select(RetrainingJob).where(RetrainingJob.id == uuid.UUID(job_id))
    job_row = (await db_session.execute(stmt_job)).scalar_one_or_none()
    if job_row and job_row.model_id:
        promote_res = await client.post(f"/api/v1/learning/jobs/{job_id}/promote", headers=headers)
        assert promote_res.status_code == 200
        assert promote_res.json()["decision"] == "promoted"
        # Verify candidate is now ACTIVE
        cand_stmt = select(MLModel).where(MLModel.id == job_row.model_id)
        cand_row = (await db_session.execute(cand_stmt)).scalar_one_or_none()
        assert cand_row.status == "active"

