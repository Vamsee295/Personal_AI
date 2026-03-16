"""
api/terminal_routes.py – REST + WebSocket endpoints for terminal execution.
"""

from __future__ import annotations
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from app.models.schemas import TerminalRequest, TerminalResponse
from app.services.terminal_service import terminal_service
from app.utils.logger import get_logger

logger = get_logger("terminal_routes")

router = APIRouter(prefix="/api/terminal", tags=["Terminal"])


# ── Single execution ───────────────────────────────────────────────
@router.post("/run", response_model=TerminalResponse)
async def run_command(req: TerminalRequest):
    """Run a shell command and return its complete output."""
    try:
        stdout, stderr, rc = await terminal_service.run(
            command=req.command,
            cwd=req.cwd,
            timeout=req.timeout,
        )
        return TerminalResponse(
            stdout=stdout,
            stderr=stderr,
            return_code=rc,
            command=req.command,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except TimeoutError as exc:
        raise HTTPException(status_code=408, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Streaming execution via WebSocket ──────────────────────────────
@router.websocket("/ws")
async def ws_terminal(websocket: WebSocket):
    """
    WebSocket terminal – streams command output line by line.

    Client sends:  {"command": "...", "cwd": "...", "timeout": 30}
    Server sends:  each output line as text, then {"done": true}
    """
    await websocket.accept()
    logger.info("WebSocket /ws/terminal connected")

    try:
        while True:
            data = await websocket.receive_json()
            command = data.get("command", "")
            cwd = data.get("cwd")
            timeout = int(data.get("timeout", 60))

            try:
                async for line in terminal_service.run_stream(command, cwd, timeout):
                    await websocket.send_text(line)
            except ValueError as exc:
                await websocket.send_json({"error": str(exc)})
            except Exception as exc:
                await websocket.send_json({"error": str(exc)})
            finally:
                await websocket.send_json({"done": True})

    except WebSocketDisconnect:
        logger.info("WebSocket /ws/terminal disconnected")
