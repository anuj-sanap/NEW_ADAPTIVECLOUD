"""
backend/app/services/detection.py
Anomaly detection pipeline service.
Invokes Isolation Forest scoring on incoming flow feature windows.
Persists Detection records, broadcasts detection.new on WebSocket,
and hands off anomalous flows to the classification and correlation service.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.detection import Classification, Detection
from app.services.classification import classify_and_correlate
from app.websocket.manager import ws_manager
from ml.inference.predictor import flow_predictor

logger = get_logger("detection_service")


async def evaluate_flow_telemetry(
    db: AsyncSession,
    host_id: uuid.UUID,
    ts: datetime,
    features: dict[str, Any],
    src_ip: str | None = None,
) -> dict[str, Any]:
    """
    Evaluates incoming network flow features:
    1. Runs Isolation Forest anomaly scoring.
    2. If anomalous, invokes multi-class threat classification and incident correlation.
    Returns result dictionary or {"status": "not_available"}.
    """
    score_res = flow_predictor.score_anomaly(features)
    if score_res.get("status") == "not_available":
        logger.debug("Anomaly detection model not available; skipping inference")
        return {"status": "not_available"}

    if score_res.get("status") != "ok":
        return score_res

    anomaly_score = float(score_res["anomaly_score"])
    is_attack = bool(score_res["is_attack"])

    detection = Detection(
        host_id=host_id,
        ts=ts,
        anomaly_score=anomaly_score,
        is_attack=is_attack,
        status="open",
    )
    db.add(detection)
    await db.commit()
    await db.refresh(detection)

    # Publish detection.new over WebSocket
    await ws_manager.publish(
        channel="detections",
        msg_type="detection.new",
        data={
            "detection_id": str(detection.id),
            "host_id": str(host_id),
            "anomaly_score": anomaly_score,
            "is_attack": is_attack,
            "ts": ts.isoformat(),
        },
    )

    classification_record: Classification | None = None
    if is_attack:
        logger.info(
            "Anomalous flow detected on host %s (score=%.4f); triggering classifier",
            host_id,
            anomaly_score,
        )
        classification_record = await classify_and_correlate(
            db=db,
            host_id=host_id,
            ts=ts,
            flow_features=features,
            src_ip=src_ip,
            detection_id=detection.id,
        )

    return {
        "status": "ok",
        "detection_id": str(detection.id),
        "anomaly_score": anomaly_score,
        "is_attack": is_attack,
        "classification": classification_record.label if classification_record else None,
    }
