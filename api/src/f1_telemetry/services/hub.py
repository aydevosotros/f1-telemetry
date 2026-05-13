import asyncio
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class WebSocketHub:
    def __init__(self) -> None:
        self._live: set[WebSocket] = set()
        self._session_clients: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect_live(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._live.add(websocket)

    async def disconnect_live(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._live.discard(websocket)

    async def connect_session(self, session_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._session_clients[session_id].add(websocket)

    async def disconnect_session(self, session_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            self._session_clients[session_id].discard(websocket)

    async def broadcast_live(self, payload: dict) -> None:
        await self._broadcast(self._live, payload)

    async def broadcast_session(self, session_id: UUID, payload: dict) -> None:
        await self._broadcast(self._session_clients[session_id], payload)

    async def _broadcast(self, clients: set[WebSocket], payload: dict) -> None:
        stale: list[WebSocket] = []
        for client in list(clients):
            try:
                await client.send_json(payload)
            except RuntimeError:
                stale.append(client)
        for client in stale:
            clients.discard(client)


hub = WebSocketHub()
