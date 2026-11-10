"""
backend/app/websocket/router.py
WebSocket endpoint at /ws/live.
"""
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError
from sqlalchemy import select

from app.core.logging import get_logger
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.websocket.manager import ws_manager

router = APIRouter(tags=["websocket"])
logger = get_logger(__name__)


async def _authenticate_ws(token: str) -> User | None:
    """
    Validate a JWT passed as a WebSocket query param.
    Returns the User on success, None on failure.
    """
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub", "")
    except JWTError:
        return None

    from uuid import UUID
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        return result.scalar_one_or_none()


@router.websocket("/ws/live")
async def websocket_live(
    ws: WebSocket,
    token: Annotated[str, Query(description="JWT access token")],
) -> None:
    """
    Live event stream endpoint.
    - Client connects with ?token=<access_token>
    - Server broadcasts metric, prediction, and alert events
    - Client can send {"type": "ping"} to receive pong
    """
    user = await _authenticate_ws(token)
    if user is None:
        await ws.close(code=4001, reason="Unauthorized")
        return

    await ws_manager.connect(ws)
    logger.info("WS authenticated", user_id=str(user.id), role=user.role)

    try:
        while True:
            msg = await ws.receive_json()
            if isinstance(msg, dict) and msg.get("type") == "ping":
                await ws_manager.send_pong(ws)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WS error", error=str(exc))
    finally:
        await ws_manager.disconnect(ws)
