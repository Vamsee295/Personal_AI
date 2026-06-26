import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.events.stream import event_stream
import logging

logger = logging.getLogger("ws_routes")
router = APIRouter()

@router.websocket("/ws/orchestrator")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def event_listener(payload):
        try:
            await websocket.send_json(payload)
        except Exception as e:
            logger.error(f"Error sending ws payload: {e}")
            raise e

    event_stream.subscribe(event_listener)

    try:
        while True:
            # Keep connection alive, wait for client to disconnect
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("Client disconnected from orchestrator ws")
    finally:
        event_stream.unsubscribe(event_listener)
