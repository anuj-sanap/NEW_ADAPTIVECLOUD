"""
backend/app/websocket/router.py
WebSocket live stream endpoint (/ws/live) with JWT authentication.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.websocket.manager import ws_manager

router = APIRouter(tags=["websocket"])
logger = get_logger("websocket.router")


async def _authenticate_ws(token: str, db: AsyncSession) -> User | None:
    """Validate Bearer token provided in websocket query parameter."""
    try:
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub", "")
        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user and user.is_active:
        return user
    return None


@router.websocket("/ws/live")
async def websocket_live_endpoint(
    ws: WebSocket,
    token: Annotated[str | None, Query(description="JWT Access Token")] = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Live streaming telemetry and alerts endpoint.
    - Connect: ws://localhost:8000/ws/live?token=<jwt>
    - Server pushes events on channels: metrics, detections, incidents, predictions, responses, models
    - 20-second heartbeat ping / pong supported
    """
    if not token:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return

    user = await _authenticate_ws(token, db)
    if not user:
        await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")
        return

    await ws_manager.connect(ws)
    logger.info("WS client authenticated and registered", user=user.username, role=user.role)

    try:
        while True:
            data = await ws.receive_json()
            if isinstance(data, dict):
                msg_type = data.get("type")
                if msg_type == "ping":
                    await ws.send_json({
                        "type": "pong",
                        "channel": "system",
                        "ts": data.get("ts"),
                        "data": {},
                    })
    except WebSocketDisconnect:
        logger.info("WS client disconnected normally", user=user.username)
    except Exception as e:
        logger.warning("WS communication closed with error", user=user.username, error=str(e))
    finally:
        await ws_manager.disconnect(ws)
