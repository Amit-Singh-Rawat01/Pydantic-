import asyncio
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import WebSocket


class LiveHub:
    """Read the total once per tick and broadcast it to every client."""

    def __init__(self, read_total: Callable[[], Optional[int]]):
        self.read_total = read_total
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
                total = await asyncio.to_thread(self.read_total)
            except Exception as error:
                print(f"[hub] total padhne mein error: {error}")
                total = None

            await self._broadcast(
                {
                    "total_errors": total,
                    "total_source": "redis" if total is not None else "unavailable",
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            await asyncio.sleep(1)

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
