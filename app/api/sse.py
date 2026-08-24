import asyncio
import json
from typing import AsyncGenerator, Dict, List
from app.models.run_state import AgentRun


class SSEManager:
    """Manages Server-Sent Events (SSE) queues for active agent runs."""

    def __init__(self):
        self._queues: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        if run_id not in self._queues:
            self._queues[run_id] = []
        q = asyncio.Queue()
        self._queues[run_id].append(q)
        return q

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        if run_id in self._queues:
            try:
                self._queues[run_id].remove(queue)
            except ValueError:
                pass
            if not self._queues[run_id]:
                del self._queues[run_id]

    async def broadcast(self, event_type: str, run: AgentRun) -> None:
        run_id = run.run_id
        if run_id in self._queues:
            payload = {
                "event": event_type,
                "data": run.model_dump(),
            }
            for q in list(self._queues[run_id]):
                await q.put(payload)


sse_manager = SSEManager()
