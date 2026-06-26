import asyncio
import time
from typing import Dict, Any, Callable

class EventStream:
    def __init__(self):
        self._listeners = []

    def subscribe(self, callback: Callable):
        self._listeners.append(callback)

    def unsubscribe(self, callback: Callable):
        if callback in self._listeners:
            self._listeners.remove(callback)

    async def emit(self, event_type: str, data: Dict[str, Any] = None):
        if data is None:
            data = {}
        payload = {
            "type": event_type,
            "data": data,
            "timestamp": time.time()
        }
        for listener in self._listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(payload)
                else:
                    listener(payload)
            except Exception as e:
                import logging
                logging.getLogger("event_stream").error(f"Error in listener: {e}")

event_stream = EventStream()
