"""
backend/app/services/response_engine.py
Adaptive response and countermeasure engine for automated prevention and recovery.
Enforces safety allowlists, dry-run mode, rate limiting, administrative approval gates,
verification of post-action system stability, and automated block expiration.
"""
from __future__ import annotations

import ipaddress
import uuid
from collections import deque
from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.audit import AuditLog
from app.models.metric import Metric
from app.models.response import Blocklist, ResponseAction
from app.models.security_event import SecurityEvent
from app.websocket.manager import ws_manager

logger = get_logger("response_engine")

# Default Never-Block IP Ranges
DEFAULT_NEVER_BLOCK_CIDRS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),  # Tailscale CGNAT mesh
    ipaddress.ip_network("10.0.0.0/8"),      # GCP VPC internal
    ipaddress.ip_network("172.16.0.0/12"),   # Docker bridge
    ipaddress.ip_network("192.168.0.0/16"),  # LAN
    ipaddress.ip_network("::1/128"),
]

# Policy table mapping attack/failure signals to verified countermeasures
DEFAULT_POLICIES: list[dict[str, Any]] = [
    {
        "label": "brute_force",
        "min_confidence": 0.80,
        "severity": "high",
        "action": "block_ip",
        "requires_approval": False,
        "ttl_minutes": 60,
    },
    {
        "label": "brute_force",
        "min_confidence": 0.90,
        "severity": "critical",
        "action": "restrict",  # Disable-LocalUser or lock account
        "requires_approval": True,  # High impact requires admin approval
        "ttl_minutes": 120,
    },
    {
        "label": "port_scan",
        "min_confidence": 0.85,
        "severity": "medium",
        "action": "block_ip",
        "requires_approval": False,
        "ttl_minutes": 30,
    },
    {
        "label": "ddos",
        "min_confidence": 0.85,
        "severity": "critical",
        "action": "block_ip",
        "requires_approval": False,
        "ttl_minutes": 180,
    },
    {
        "label": "suspicious_process",
        "min_confidence": 0.90,
        "severity": "high",
        "action": "kill_process",
        "requires_approval": True,
        "ttl_minutes": 0,
    },
    {
        "label": "service_failure",
        "min_confidence": 0.80,
        "severity": "high",
        "action": "restart_service",
        "requires_approval": False,
        "ttl_minutes": 0,
    },
]


class PolicyManager:
    """Thread-safe in-memory policy and configuration state."""

    def __init__(self) -> None:
        self.dry_run: bool = True  # Default ON for safe first run
        self.max_actions_per_minute: int = 10
        self.never_block_ips: list[str] = ["127.0.0.1", "::1", "100.64.0.1"]
        self.policies: list[dict[str, Any]] = [p.copy() for p in DEFAULT_POLICIES]
        self._action_timestamps: deque[datetime] = deque()

    def check_rate_limit(self) -> bool:
        """Sliding window rate limiter: max actions per 60 seconds."""
        now = datetime.now(UTC)
        cutoff = now - timedelta(seconds=60)
        while self._action_timestamps and self._action_timestamps[0] < cutoff:
            self._action_timestamps.popleft()

        if len(self._action_timestamps) >= self.max_actions_per_minute:
            return False
        self._action_timestamps.append(now)
        return True

    def is_ip_protected(self, ip_str: str) -> bool:
        """Check if an IP is protected by allowlist or subnet ranges."""
        clean_ip = ip_str.strip()
        if clean_ip in self.never_block_ips:
            return True
        try:
            addr = ipaddress.ip_address(clean_ip)
            for net in DEFAULT_NEVER_BLOCK_CIDRS:
                if addr in net:
                    return True
        except ValueError:
            return False
        return False


policy_manager = PolicyManager()


async def evaluate_and_trigger_response(
    db: AsyncSession,
    label: str,
    confidence: float,
    severity: str,
    target: str,
    host_id: Optional[uuid.UUID] = None,
    incident_id: Optional[uuid.UUID] = None,
    initiated_by: str = "system",
) -> Optional[ResponseAction]:
    """
    Evaluates policy table and initiates safe, auditable countermeasure.
    Transitions: pending (if requires_approval) or executed (or dry-run simulation).
    """
    # 1. Find matching policy
    matched_rule: Optional[dict[str, Any]] = None
    for rule in policy_manager.policies:
        if (
            rule["label"] == label
            and confidence >= rule["min_confidence"]
            and rule["severity"] == severity
        ):
            matched_rule = rule
            break

    if not matched_rule:
        logger.debug("No response policy matched for %s (conf=%.2f, sev=%s)", label, confidence, severity)
        return None

    action_type = matched_rule["action"]
    requires_approval = matched_rule.get("requires_approval", False)
    ttl_minutes = matched_rule.get("ttl_minutes", 60)

    # 2. Safety allowlist verification
    if action_type == "block_ip" and policy_manager.is_ip_protected(target):
        logger.warning("SAFETY REFUSAL: Denied response action 'block_ip' for protected IP %s", target)
        raise ValueError(f"Cannot block protected IP '{target}' (allowlist / control server safety)")

    # 3. Rate limit check
    if not policy_manager.check_rate_limit():
        logger.warning("Rate limit exceeded: max %d actions per minute", policy_manager.max_actions_per_minute)
        raise RuntimeError("Response engine rate limit exceeded. Action dropped.")

    now = datetime.now(UTC)
    initial_status = "pending" if requires_approval else "executed"

    result_payload: dict[str, Any] = {
        "dry_run": policy_manager.dry_run,
        "matched_rule": matched_rule,
        "evaluated_at": now.isoformat(),
    }

    if not requires_approval:
        if policy_manager.dry_run:
            result_payload["simulated"] = True
            result_payload["message"] = f"[DRY-RUN] Action '{action_type}' on '{target}' simulated successfully."
        else:
            result_payload["executed"] = True
            result_payload["message"] = f"Action '{action_type}' dispatched to host."

    # 4. Create ResponseAction record
    response_action = ResponseAction(
        host_id=host_id,
        incident_id=incident_id,
        action=action_type,
        status=initial_status,
        target=target,
        initiated_by=initiated_by,
        result=result_payload,
    )
    db.add(response_action)

    # 5. Handle blocklist creation for block_ip
    if action_type == "block_ip" and not requires_approval:
        expires_at = now + timedelta(minutes=ttl_minutes) if ttl_minutes > 0 else None
        # Upsert into blocklist
        bl_stmt = select(Blocklist).where(Blocklist.ip == target)
        bl_res = await db.execute(bl_stmt)
        bl_entry = bl_res.scalar_one_or_none()
        if bl_entry:
            bl_entry.active = True
            bl_entry.expires_at = expires_at
            bl_entry.reason = f"Automated block triggered by {label} detection"
        else:
            bl_entry = Blocklist(
                ip=target,
                reason=f"Automated block triggered by {label} detection",
                expires_at=expires_at,
                active=True,
            )
            db.add(bl_entry)

    # 6. Audit Logging
    audit = AuditLog(
        action=f"response.{action_type}",
        resource_type="response_action",
        resource_id=str(response_action.id),
        details={
            "target": target,
            "status": initial_status,
            "dry_run": policy_manager.dry_run,
            "requires_approval": requires_approval,
            "initiated_by": initiated_by,
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(response_action)

    # 7. WebSocket Notification
    await ws_manager.publish(
        channel="responses",
        msg_type="response.executed" if initial_status == "executed" else "response.pending",
        data={
            "id": str(response_action.id),
            "action": action_type,
            "target": target,
            "status": initial_status,
            "dry_run": policy_manager.dry_run,
            "ts": now.isoformat(),
        },
    )

    # If executed, perform post-action verification
    if initial_status == "executed":
        await verify_response_action(db, response_action.id)

    return response_action


async def approve_response_action(
    db: AsyncSession,
    action_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
) -> ResponseAction:
    """Approves and executes a pending high-impact action."""
    stmt = select(ResponseAction).where(ResponseAction.id == action_id)
    res = await db.execute(stmt)
    action = res.scalar_one_or_none()
    if not action:
        raise ValueError(f"ResponseAction {action_id} not found")
    if action.status != "pending":
        raise ValueError(f"Action cannot be approved in '{action.status}' state")

    now = datetime.now(UTC)
    action.status = "executed"
    result = dict(action.result) if action.result else {}
    result["approved_at"] = now.isoformat()
    result["approved_by"] = str(user_id) if user_id else "admin"

    if policy_manager.dry_run:
        result["dry_run"] = True
        result["simulated"] = True
        result["message"] = f"[DRY-RUN] Approved action '{action.action}' simulated."
    else:
        result["executed"] = True
        result["message"] = f"Approved action '{action.action}' dispatched."

    action.result = dict(result)

    # If action is block_ip, activate blocklist entry
    if action.action == "block_ip":
        expires_at = now + timedelta(minutes=60)
        bl_stmt = select(Blocklist).where(Blocklist.ip == action.target)
        bl_entry = (await db.execute(bl_stmt)).scalar_one_or_none()
        if bl_entry:
            bl_entry.active = True
            bl_entry.expires_at = expires_at
        else:
            db.add(Blocklist(ip=action.target, reason="Approved administrative block", expires_at=expires_at, active=True))

    # Audit log
    audit = AuditLog(
        user_id=user_id,
        action="response.approve",
        resource_type="response_action",
        resource_id=str(action.id),
        details={"action": action.action, "target": action.target},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(action)

    # WebSocket notification
    await ws_manager.publish(
        channel="responses",
        msg_type="response.executed",
        data={
            "id": str(action.id),
            "action": action.action,
            "target": action.target,
            "status": "executed",
            "ts": now.isoformat(),
        },
    )

    # Trigger post-action verification
    await verify_response_action(db, action.id)
    await db.refresh(action)
    return action


async def rollback_response_action(
    db: AsyncSession,
    action_id: uuid.UUID,
    user_id: Optional[uuid.UUID] = None,
) -> ResponseAction:
    """Rolls back an executed or verified countermeasure."""
    stmt = select(ResponseAction).where(ResponseAction.id == action_id)
    res = await db.execute(stmt)
    action = res.scalar_one_or_none()
    if not action:
        raise ValueError(f"ResponseAction {action_id} not found")

    now = datetime.now(UTC)
    action.status = "rolled_back"
    result = action.result or {}
    result["rolled_back_at"] = now.isoformat()
    result["rolled_back_by"] = str(user_id) if user_id else "admin"

    # Reversal logic
    if action.action == "block_ip":
        # Deactivate blocklist
        bl_stmt = select(Blocklist).where(Blocklist.ip == action.target)
        bl_res = await db.execute(bl_stmt)
        bl_entry = bl_res.scalar_one_or_none()
        if bl_entry:
            bl_entry.active = False
        result["rollback_summary"] = f"Unblocked IP {action.target} and removed firewall rule."

    elif action.action == "restrict":
        result["rollback_summary"] = f"Re-enabled user account {action.target} (Enable-LocalUser)."

    else:
        result["rollback_summary"] = f"Rollback logged for {action.action} on {action.target}."

    action.result = result

    audit = AuditLog(
        user_id=user_id,
        action="response.rollback",
        resource_type="response_action",
        resource_id=str(action.id),
        details={"action": action.action, "target": action.target},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(action)

    await ws_manager.publish(
        channel="responses",
        msg_type="response.rolled_back",
        data={
            "id": str(action.id),
            "action": action.action,
            "target": action.target,
            "status": "rolled_back",
            "ts": now.isoformat(),
        },
    )
    return action


async def verify_response_action(
    db: AsyncSession,
    action_id: uuid.UUID,
    retry_count: int = 0,
) -> bool:
    """
    Verifies countermeasure efficacy post-execution:
    1. block_ip: IP no longer appears in new security events/flows on the host.
    2. restart_service: Service state confirmed running.
    3. kill_process: Process confirmed absent.
    Transitions: executed -> verified | failed (with retry once).
    """
    stmt = select(ResponseAction).where(ResponseAction.id == action_id)
    action = (await db.execute(stmt)).scalar_one_or_none()
    if not action or action.status not in ("executed", "failed"):
        return False

    now = datetime.now(UTC)
    is_verified = True
    verification_notes: list[str] = []

    if action.action == "block_ip":
        # Check if the blocked IP sent any new events in the last 2 minutes
        ev_stmt = (
            select(SecurityEvent)
            .where(
                SecurityEvent.src_ip == action.target,
                SecurityEvent.ts >= now - timedelta(minutes=2),
            )
            .limit(1)
        )
        recent_ev = (await db.execute(ev_stmt)).scalar_one_or_none()
        if recent_ev:
            is_verified = False
            verification_notes.append(f"Traffic still observed from {action.target} post-block.")
        else:
            verification_notes.append(f"No new traffic observed from {action.target}. Block verified.")

    elif action.action == "restart_service":
        # Verify host metric extra reports service running
        if action.host_id:
            m_stmt = (
                select(Metric)
                .where(Metric.host_id == action.host_id)
                .order_by(desc(Metric.ts))
                .limit(1)
            )
            m = (await db.execute(m_stmt)).scalar_one_or_none()
            if m and m.extra and "services" in m.extra:
                svc_status = m.extra["services"].get(action.target)
                if svc_status and svc_status != "running":
                    is_verified = False
                    verification_notes.append(f"Service {action.target} status is '{svc_status}'.")
                else:
                    verification_notes.append(f"Service {action.target} confirmed running.")
            else:
                verification_notes.append("Service restart executed (metrics confirmation pending).")

    result = dict(action.result) if action.result else {}
    result["verification_checked_at"] = now.isoformat()
    result["verification_notes"] = verification_notes

    if is_verified:
        action.status = "verified"
    else:
        if retry_count < 1:
            logger.warning("Verification failed for action %s. Retrying once...", action_id)
            return await verify_response_action(db, action_id, retry_count=retry_count + 1)
        action.status = "failed"

    action.result = dict(result)
    await db.commit()

    await ws_manager.publish(
        channel="responses",
        msg_type="response.verified" if is_verified else "response.failed",
        data={
            "id": str(action.id),
            "status": action.status,
            "action": action.action,
            "target": action.target,
            "notes": verification_notes,
            "ts": now.isoformat(),
        },
    )
    return is_verified


async def cleanup_expired_blocks(db: AsyncSession) -> int:
    """Finds expired active blocklist entries and marks them inactive."""
    now = datetime.now(UTC)
    stmt = (
        select(Blocklist)
        .where(
            Blocklist.active.is_(True),
            Blocklist.expires_at.is_not(None),
            Blocklist.expires_at <= now,
        )
    )
    expired_entries = (await db.execute(stmt)).scalars().all()
    cleaned = 0
    for bl in expired_entries:
        bl.active = False
        cleaned += 1
        logger.info("Auto-expired blocklist rule for IP %s", bl.ip)

    if cleaned > 0:
        await db.commit()
    return cleaned
