import asyncio
from typing import Any, Callable, Dict, List, Optional

from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


class LiveHub:
    """Read one snapshot per tick and broadcast it to every client."""

    def __init__(self, read_snapshot: Callable[[], Dict[str, Any]], every_sec: float = 1):
        self.read_snapshot = read_snapshot
        self.every_sec = every_sec
        self.clients: List[WebSocket] = []
        self._task: Optional[asyncio.Task] = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.append(ws)
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    def disconnect(self, ws: WebSocket):
        if ws in self.clients:
            self.clients.remove(ws)

    async def _loop(self):
        while self.clients:
            try:
                snapshot = await asyncio.to_thread(self.read_snapshot)
                snapshot = jsonable_encoder(snapshot)
            except Exception as error:
                print(f"[hub] snapshot padhne mein error: {error}")
                snapshot = {"total_errors": None}

            await self._broadcast(snapshot)
            await asyncio.sleep(self.every_sec)

    async def _broadcast(self, message: Dict[str, Any]):
        dead: List[WebSocket] = []
        for ws in list(self.clients):
            try:
                await ws.send_json(message)
            except Exception as error:
                print(f"[hub] client hataya: {type(error).__name__}")
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
