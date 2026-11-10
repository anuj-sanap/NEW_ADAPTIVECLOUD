"""
backend/app/websocket/manager.py
WebSocket connection manager for live event broadcasting.
Implements the envelope: {type, channel, ts, data}.
"""
import asyncio
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """
    Manages a set of active WebSocket connections and broadcasts messages.

    Each connection is tracked as an authenticated WebSocket instance.
    Messages are sent concurrently using asyncio.gather with
    return_exceptions=True so a failed send never drops other clients.
    """

    def __init__(self) -> None:
        # Set of active websocket connections
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        """Accept and register a WebSocket connection."""
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        logger.info("WS client connected", total=len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket connection (safe to call even if not registered)."""
        async with self._lock:
            self._connections.discard(ws)
        logger.info("WS client disconnected", total=len(self._connections))

    def _make_envelope(
        self,
        channel: str,
        data: Any,
        msg_type: str = "event",
    ) -> dict[str, Any]:
        """Build the standard WebSocket message envelope."""
        return {
            "type": msg_type,
            "channel": channel,
            "ts": datetime.now(UTC).isoformat(),
            "data": data,
        }

    async def broadcast(
        self,
        channel: str,
        data: Any,
        msg_type: str = "event",
    ) -> None:
        """
        Send a message to all connected clients.
        Dead connections are silently removed.
        """
        envelope = self._make_envelope(channel, data, msg_type)
        dead: set[WebSocket] = set()

        async with self._lock:
            snapshot = set(self._connections)

        async def _send(ws: WebSocket) -> None:
            try:
                await ws.send_json(envelope)
            except Exception:
                dead.add(ws)

        await asyncio.gather(*[_send(ws) for ws in snapshot], return_exceptions=True)

        if dead:
            async with self._lock:
                self._connections -= dead
            logger.debug("Removed dead WS connections", count=len(dead))

    async def send_pong(self, ws: WebSocket) -> None:
        """Respond to a client ping with a pong envelope."""
        try:
            await ws.send_json(
                self._make_envelope("system", {}, msg_type="pong")
            )
        except Exception:
            await self.disconnect(ws)


# Singleton — imported by routes and background tasks
ws_manager = ConnectionManager()
