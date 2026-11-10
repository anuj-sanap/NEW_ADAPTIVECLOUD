"""
backend/app/services/classification.py
Hybrid threat classifier and incident correlator.
Combines supervised ML predictions (brute_force, ddos, port_scan) with rule-based
Windows security telemetry heuristics (unauthorized_access, suspicious_process).
Labels provenance as ml | rule | both.
Correlates events by src_ip and time window into unified incidents.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.detection import Classification
from app.models.incident import Incident, IncidentItem
from app.websocket.manager import ws_manager
from ml.inference.predictor import flow_predictor

logger = get_logger("classification_service")

# Incident correlation window (15 minutes)
INCIDENT_CORRELATION_WINDOW_MIN = 15


def rule_based_check(event_data: dict[str, Any] | None) -> tuple[str | None, float]:
    """
    Examines Windows event / process telemetry for unauthorized_access or suspicious_process.
    Returns (label, confidence).
    """
    if not event_data:
        return None, 0.0

    eid = event_data.get("event_id") or event_data.get("eventID")
    category = event_data.get("category", "")
    cmdline = str(event_data.get("raw", {}).get("CommandLine", "")).lower()

    # Unauthorized access rules (4672 special privileges, 4720 user created)
    if eid in (4672, 4720) or category == "unauthorized_access":
        return "unauthorized_access", 0.95

    # Suspicious process rules (4688 with encoded command or temp execution)
    if eid == 4688 or category == "suspicious_process":
        if any(k in cmdline for k in ["-enc", "-encodedcommand", "\\temp\\", "\\downloads\\", "\\appdata\\"]):
            return "suspicious_process", 0.98
        return "suspicious_process", 0.85

    return None, 0.0


async def correlate_incident(
    db: AsyncSession,
    host_id: uuid.UUID,
    ts: datetime,
    label: str,
    source: str,
    confidence: float,
    src_ip: str | None = None,
    detection_id: uuid.UUID | None = None,
    classification_id: uuid.UUID | None = None,
) -> Incident:
    """
    Groups correlated detections and classifications into an Incident
    by src_ip within a 15-minute rolling window.
    """
    cutoff = ts - timedelta(minutes=INCIDENT_CORRELATION_WINDOW_MIN)

    # Search for an existing open incident with same src_ip (or host_id if no src_ip)
    stmt = (
        select(Incident)
        .where(
            Incident.status == "open",
            Incident.created_at >= cutoff,
        )
        .order_by(Incident.created_at.desc())
    )
    res = await db.execute(stmt)
    open_incidents = res.scalars().all()

    target_incident: Incident | None = None
    for inc in open_incidents:
        inc_summary = inc.summary or {}
        if src_ip and inc_summary.get("src_ip") == src_ip:
            target_incident = inc
            break
        elif not src_ip and inc_summary.get("host_id") == str(host_id):
            target_incident = inc
            break

    severity = "critical" if label in ("ddos", "unauthorized_access") else "high"

    if target_incident:
        # Merge into existing incident
        summary = target_incident.summary or {}
        summary["event_count"] = summary.get("event_count", 1) + 1
        summary["last_label"] = label
        summary["last_source"] = source
        summary["last_seen"] = ts.isoformat()
        target_incident.summary = summary

        if severity == "critical":
            target_incident.severity = "critical"

        target_incident.description = (
            f"Correlated {summary['event_count']} security events. "
            f"Latest activity: {label} via {source} engine from {src_ip or 'local host'}."
        )
    else:
        # Create fresh incident
        title = f"Security Incident: {label.replace('_', ' ').title()} from {src_ip or 'Monitored Host'}"
        target_incident = Incident(
            title=title,
            severity=severity,
            status="open",
            description=f"Initial detection of {label} attack pattern via {source} analysis.",
            summary={
                "src_ip": src_ip,
                "host_id": str(host_id),
                "initial_label": label,
                "source": source,
                "event_count": 1,
                "confidence": confidence,
            },
        )
        db.add(target_incident)
        await db.flush()

    # Link IncidentItem
    if classification_id:
        item = IncidentItem(
            incident_id=target_incident.id,
            item_type="classification",
            item_id=classification_id,
            details={"label": label, "source": source, "confidence": confidence},
        )
        db.add(item)
    elif detection_id:
        item = IncidentItem(
            incident_id=target_incident.id,
            item_type="detection",
            item_id=detection_id,
            details={"label": label, "source": source},
        )
        db.add(item)

    await db.commit()
    await db.refresh(target_incident)

    # Publish incident.updated over WebSocket
    await ws_manager.publish(
        channel="incidents",
        msg_type="incident.updated",
        data={
            "incident_id": str(target_incident.id),
            "title": target_incident.title,
            "severity": target_incident.severity,
            "status": target_incident.status,
            "src_ip": src_ip,
            "label": label,
            "source": source,
            "event_count": (target_incident.summary or {}).get("event_count", 1),
            "ts": ts.isoformat(),
        },
    )

    logger.info("Correlated incident %s: %s [%s]", target_incident.id, target_incident.title, target_incident.severity)
    return target_incident


async def classify_and_correlate(
    db: AsyncSession,
    host_id: uuid.UUID,
    ts: datetime,
    flow_features: dict[str, Any] | None = None,
    event_data: dict[str, Any] | None = None,
    src_ip: str | None = None,
    detection_id: uuid.UUID | None = None,
) -> Classification | None:
    """
    Core classification coordinator:
    1. Runs ML classifier on network flow features if present.
    2. Runs rule-based classification on security events if present.
    3. Combines findings into final label with source tag (ml | rule | both).
    4. Persists Classification and correlates with Incident.
    """
    ml_label: str | None = None
    ml_conf = 0.0
    ml_probs: dict[str, Any] = {}

    if flow_features and flow_predictor.is_classifier_ready:
        pred_res = flow_predictor.classify_attack(flow_features)
        if pred_res.get("status") == "ok":
            ml_label = pred_res["label"]
            ml_conf = pred_res["confidence"]
            ml_probs = pred_res.get("probs", {})

    rule_label, rule_conf = rule_based_check(event_data)

    # Combine ML and Rule decisions
    final_label: str | None = None
    final_conf = 0.0
    source = "ml"

    if rule_label and ml_label and ml_label != "benign":
        # Both triggered on non-benign patterns
        source = "both"
        # Prioritize higher confidence
        if rule_conf >= ml_conf:
            final_label = rule_label
            final_conf = rule_conf
        else:
            final_label = ml_label
            final_conf = ml_conf
    elif rule_label:
        source = "rule"
        final_label = rule_label
        final_conf = rule_conf
    elif ml_label:
        source = "ml"
        final_label = ml_label
        final_conf = ml_conf
    else:
        return None

    # If determined to be benign with high confidence, no threat classification record needed
    if final_label == "benign":
        return None

    probs_meta = dict(ml_probs)
    probs_meta["source"] = source
    probs_meta["rule_label"] = rule_label
    probs_meta["ml_label"] = ml_label

    classification = Classification(
        host_id=host_id,
        ts=ts,
        detection_id=detection_id,
        label=final_label,
        confidence=final_conf,
        probs=probs_meta,
    )
    db.add(classification)
    await db.commit()
    await db.refresh(classification)

    # Publish detection/classification event over WebSocket
    await ws_manager.publish(
        channel="detections",
        msg_type="classification.new",
        data={
            "classification_id": str(classification.id),
            "detection_id": str(detection_id) if detection_id else None,
            "host_id": str(host_id),
            "label": final_label,
            "confidence": final_conf,
            "source": source,
            "src_ip": src_ip,
            "ts": ts.isoformat(),
        },
    )

    # Correlate into Incident
    await correlate_incident(
        db=db,
        host_id=host_id,
        ts=ts,
        label=final_label,
        source=source,
        confidence=final_conf,
        src_ip=src_ip,
        detection_id=detection_id,
        classification_id=classification.id,
    )

    return classification
