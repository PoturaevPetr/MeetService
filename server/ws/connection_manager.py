from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import WebSocket


class ConnectionManager:
    """Один WebSocket на пользователя (последнее подключение вытесняет предыдущее)."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._by_user: dict[uuid.UUID, WebSocket] = {}

    async def connect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        async with self._lock:
            old = self._by_user.get(user_id)
            self._by_user[user_id] = websocket
        if old is not None:
            try:
                await old.close(code=4401)
            except Exception:
                pass

    async def disconnect(self, user_id: uuid.UUID, websocket: WebSocket) -> None:
        async with self._lock:
            cur = self._by_user.get(user_id)
            if cur is websocket:
                del self._by_user[user_id]

    def is_online(self, user_id: uuid.UUID) -> bool:
        return user_id in self._by_user

    async def send_json(self, user_id: uuid.UUID, payload: dict[str, Any]) -> bool:
        async with self._lock:
            ws = self._by_user.get(user_id)
        if ws is None:
            return False
        try:
            await ws.send_json(payload)
            return True
        except Exception:
            return False


manager = ConnectionManager()
