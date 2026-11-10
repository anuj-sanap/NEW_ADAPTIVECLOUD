"""
backend/app/websocket/manager.py
WebSocket live event streaming hub with channel subscriptions,
heartbeat monitoring (20s interval), and broadcast publishing.
Channels: metrics, detections, incidents, predictions, responses, models.
Envelope: {type, channel, ts, data}
"""
import asyncio
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import WebSocket
from app.core.logging import get_logger

logger = get_logger("websocket.manager")

VALID_CHANNELS = {
    "metrics",
    "detections",
    "incidents",
    "predictions",
    "responses",
    "models",
    "system",
}

ChannelType = Literal[
    "metrics",
    "detections",
    "incidents",
    "predictions",
    "responses",
    "models",
    "system",
]


class ConnectionManager:
    """
    Manages client WebSocket connections, channel dispatching,
    and background heartbeat pings.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._heartbeat_task: asyncio.Task | None = None

    def start_heartbeat(self) -> None:
        """Start background 20-second heartbeat loop if not already running."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        """Send periodic ping envelope every 20 seconds to all active clients."""
        while True:
            try:
                await asyncio.sleep(20)
                await self.publish(
                    channel="system",
                    msg_type="ping",
                    data={"server_time": datetime.now(UTC).isoformat()},
                )
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Heartbeat error", error=str(e))

    async def connect(self, ws: WebSocket) -> None:
        """Accept a client websocket connection."""
        await ws.accept()
        async with self._lock:
            self._connections.add(ws)
        self.start_heartbeat()
        logger.info("Client connected to WS hub", active_clients=len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        """Unregister a client connection."""
        async with self._lock:
            self._connections.discard(ws)
        logger.info("Client disconnected from WS hub", active_clients=len(self._connections))

    def _make_envelope(self, channel: str, msg_type: str, data: Any) -> dict[str, Any]:
        """Wrap payload in standard event envelope."""
        return {
            "type": msg_type,
            "channel": channel,
            "ts": datetime.now(UTC).isoformat(),
            "data": data,
        }

    async def publish(
        self,
        channel: ChannelType | str,
        msg_type: str = "event",
        data: Any = None,
    ) -> None:
        """
        Broadcast message to all connected clients.
        Dead connections are detected and purged safely.
        """
        if data is None:
            data = {}
        envelope = self._make_envelope(channel, msg_type, data)
        dead: set[WebSocket] = set()

        async with self._lock:
            clients = set(self._connections)

        async def _send(client: WebSocket) -> None:
            try:
                await client.send_json(envelope)
            except Exception:
                dead.add(client)

        if clients:
            await asyncio.gather(*[_send(c) for c in clients], return_exceptions=True)

        if dead:
            async with self._lock:
                self._connections -= dead
            logger.debug("Purged dead connections", count=len(dead))

    # Backward-compatible alias
    async def broadcast(self, channel: str, data: Any, msg_type: str = "event") -> None:
        await self.publish(channel=channel, msg_type=msg_type, data=data)


# Global singleton instance
ws_manager = ConnectionManager()
