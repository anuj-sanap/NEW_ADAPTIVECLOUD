"""
backend/tests/test_response_engine.py
Tests for automated countermeasures, safety allowlists, dry-run mode,
admin approval gates, post-action verification, rollback, and blocklist lifecycle.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent.executor import AgentExecutor, CommandValidator
from app.models.response import Blocklist
from app.services.response_engine import (
    approve_response_action,
    cleanup_expired_blocks,
    evaluate_and_trigger_response,
    policy_manager,
    rollback_response_action,
)


def test_command_validator_allowlists():
    # 1. Protected IPs
    assert CommandValidator.is_protected_ip("127.0.0.1") is True
    assert CommandValidator.is_protected_ip("100.64.0.1") is True  # Tailscale
    assert CommandValidator.is_protected_ip("10.0.1.15") is True   # GCP VPC
    assert CommandValidator.is_protected_ip("192.168.1.50") is True
    assert CommandValidator.is_protected_ip("203.0.113.88") is False  # Public attacker

    # 2. Protected Processes
    assert CommandValidator.is_protected_process("svchost.exe") is True
    assert CommandValidator.is_protected_process("explorer.exe") is True
    assert CommandValidator.is_protected_process("system") is True
    assert CommandValidator.is_protected_process("4") is True  # System PID
    assert CommandValidator.is_protected_process("malware_miner.exe") is False

    # 3. Allowlisted Services
    assert CommandValidator.is_allowlisted_service("Spooler") is True
    assert CommandValidator.is_allowlisted_service("w32time") is True
    assert CommandValidator.is_allowlisted_service("unapproved_crypto_daemon") is False


def test_agent_executor_safety_refusal():
    executor = AgentExecutor(dry_run=False)

    # Attempt to block localhost
    res_ip = executor.execute_action("block_ip", "127.0.0.1")
    assert res_ip["success"] is False
    assert "SAFETY REFUSAL" in res_ip["output"]

    # Attempt to kill svchost.exe
    res_proc = executor.execute_action("kill_process", "svchost.exe")
    assert res_proc["success"] is False
    assert "SAFETY REFUSAL" in res_proc["output"]

    # Attempt to restart unapproved service
    res_svc = executor.execute_action("restart_service", "rogue_service")
    assert res_svc["success"] is False
    assert "SAFETY REFUSAL" in res_svc["output"]


@pytest.mark.asyncio
async def test_response_engine_safety_allowlist_raises(db_session: AsyncSession):
    # Attempting to trigger response on protected IP raises ValueError
    with pytest.raises(ValueError, match="Cannot block protected IP"):
        await evaluate_and_trigger_response(
            db=db_session,
            label="brute_force",
            confidence=0.95,
            severity="high",
            target="127.0.0.1",
        )

    with pytest.raises(ValueError, match="Cannot block protected IP"):
        await evaluate_and_trigger_response(
            db=db_session,
            label="ddos",
            confidence=0.95,
            severity="critical",
            target="100.64.0.1",  # Control server Tailscale IP
        )


@pytest.mark.asyncio
async def test_response_engine_dry_run_execution(db_session: AsyncSession):
    policy_manager.dry_run = True

    action = await evaluate_and_trigger_response(
        db=db_session,
        label="port_scan",
        confidence=0.90,
        severity="medium",
        target="198.51.100.77",
    )
    assert action is not None
    assert action.status in ("executed", "verified")
    assert action.action == "block_ip"
    assert action.result["dry_run"] is True
    assert action.result["simulated"] is True

    # Blocklist record should be created
    stmt = select(Blocklist).where(Blocklist.ip == "198.51.100.77")
    entry = (await db_session.execute(stmt)).scalar_one_or_none()
    assert entry is not None
    assert entry.active is True
    assert entry.expires_at is not None


@pytest.mark.asyncio
async def test_response_engine_admin_approval_mode(db_session: AsyncSession):
    # Suspicious process requires approval per default policy
    action = await evaluate_and_trigger_response(
        db=db_session,
        label="suspicious_process",
        confidence=0.95,
        severity="high",
        target="powershell_encoded_beacon.exe",
    )
    assert action is not None
    assert action.status == "pending"

    # Approve action
    approved = await approve_response_action(db_session, action.id)
    assert approved.status in ("executed", "verified")
    assert approved.result.get("approved_at") is not None


@pytest.mark.asyncio
async def test_response_engine_rollback(db_session: AsyncSession):
    # Execute a block
    action = await evaluate_and_trigger_response(
        db=db_session,
        label="brute_force",
        confidence=0.85,
        severity="high",
        target="198.51.100.88",
    )
    assert action is not None

    # Verify active blocklist exists
    stmt = select(Blocklist).where(Blocklist.ip == "198.51.100.88")
    entry = (await db_session.execute(stmt)).scalar_one_or_none()
    assert entry is not None and entry.active is True

    # Rollback
    rolled = await rollback_response_action(db_session, action.id)
    assert rolled.status == "rolled_back"

    # Blocklist should now be inactive
    await db_session.refresh(entry)
    assert entry.active is False


@pytest.mark.asyncio
async def test_expired_blocks_cleanup(db_session: AsyncSession):
    now = datetime.now(UTC)
    # Create an entry expired 10 minutes ago
    expired_entry = Blocklist(
        ip="198.51.100.99",
        reason="Test expired block",
        expires_at=now - timedelta(minutes=10),
        active=True,
    )
    db_session.add(expired_entry)
    await db_session.commit()

    cleaned = await cleanup_expired_blocks(db_session)
    assert cleaned >= 1

    await db_session.refresh(expired_entry)
    assert expired_entry.active is False


@pytest.mark.asyncio
async def test_responses_and_blocklist_api(
    client: AsyncClient,
    admin_token: str,
    db_session: AsyncSession,
):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. GET /api/v1/responses/policy
    pol_res = await client.get("/api/v1/responses/policy", headers=headers)
    assert pol_res.status_code == 200
    pol_data = pol_res.json()
    assert "dry_run" in pol_data
    assert "policies" in pol_data
    assert len(pol_data["policies"]) >= 4

    # 2. PUT /api/v1/responses/policy (update dry_run)
    put_res = await client.put(
        "/api/v1/responses/policy",
        json={"dry_run": True, "max_actions_per_minute": 15},
        headers=headers,
    )
    assert put_res.status_code == 200
    assert put_res.json()["max_actions_per_minute"] == 15

    # 3. POST /api/v1/blocklist (valid public IP)
    bl_add = await client.post(
        "/api/v1/blocklist",
        json={"ip": "198.51.100.111", "reason": "Test block", "ttl_minutes": 30},
        headers=headers,
    )
    assert bl_add.status_code == 201
    assert bl_add.json()["ip"] == "198.51.100.111"

    # 4. POST /api/v1/blocklist (refuse protected IP)
    bl_refuse = await client.post(
        "/api/v1/blocklist",
        json={"ip": "127.0.0.1", "reason": "Attempt to block loopback"},
        headers=headers,
    )
    assert bl_refuse.status_code == 400
    assert "protected IP" in bl_refuse.json()["error"]["message"]

    # 5. GET /api/v1/blocklist
    bl_list = await client.get("/api/v1/blocklist", headers=headers)
    assert bl_list.status_code == 200
    assert isinstance(bl_list.json(), list)

    # 6. DELETE /api/v1/blocklist/{target}
    bl_del = await client.delete("/api/v1/blocklist/198.51.100.111", headers=headers)
    assert bl_del.status_code == 200
    assert bl_del.json()["status"] == "success"

    # 7. GET /api/v1/responses
    resp_list = await client.get("/api/v1/responses", headers=headers)
    assert resp_list.status_code == 200
    assert isinstance(resp_list.json(), list)
