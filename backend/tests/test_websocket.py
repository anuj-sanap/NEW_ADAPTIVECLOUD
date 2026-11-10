"""
backend/tests/test_websocket.py
WebSocket live stream hub connection, authentication, and publishing tests.
"""
import pytest
from starlette.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.websocket.manager import ws_manager


def test_websocket_missing_token():
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/live"):
            pass


def test_websocket_invalid_token():
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/live?token=invalid_jwt_token_string"):
            pass


def test_websocket_connect_and_ping(db_session: AsyncSession, admin_token: str):
    client = TestClient(app)
    with client.websocket_connect(f"/ws/live?token={admin_token}") as ws:
        # Send ping to server
        ws.send_json({"type": "ping", "ts": "2026-11-10T19:00:00Z"})
        response = ws.receive_json()
        assert response["type"] == "pong"
        assert response["channel"] == "system"


@pytest.mark.asyncio
async def test_websocket_publish_method():
    # Verify the ws_manager.publish method executes cleanly without active clients
    await ws_manager.publish(
        channel="metrics",
        msg_type="event",
        data={"cpu": 55.5, "mem": 60.0},
    )

    await ws_manager.publish(
        channel="detections",
        msg_type="event",
        data={"is_attack": True, "label": "ddos"},
    )
