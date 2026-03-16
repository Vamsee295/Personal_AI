"""
api/agent_routes.py – REST + WebSocket endpoints for the AI agent engine.
"""

from __future__ import annotations
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from app.models.schemas import AgentTask, WorkspaceOpenRequest
from app.services.agent_service import agent_service
from app.core.workspace_manager import workspace_manager
from app.utils.logger import get_logger

logger = get_logger("agent_routes")

router = APIRouter(prefix="/api/agent", tags=["AI Agent"])


# ── Execute a multi-step agent task ───────────────────────────────
@router.post("/execute")
async def execute_task(req: AgentTask):
    """
    Let the AI agent plan and execute a multi-step task.
    Returns a structured list of steps and a final summary.
    """
    try:
        result = await agent_service.execute(
            task=req.task,
            context=req.context,
            workspace_path=req.workspace_path,
            model=req.model,
        )
        return result
    except Exception as exc:
        logger.error("Agent execution error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── WebSocket: live agent progress ─────────────────────────────────
@router.websocket("/ws")
async def ws_agent(websocket: WebSocket):
    """
    WebSocket for the AI agent – sends progress updates as the agent works.
    Client sends:  {"task": "...", "context": "...", "workspace_path": "..."}
    Server sends:  step-by-step JSON updates, then final result.
    """
    await websocket.accept()
    logger.info("WebSocket /ws/agent connected")

    try:
        data = await websocket.receive_json()
        task = data.get("task", "")
        context = data.get("context")
        workspace_path = data.get("workspace_path")
        model = data.get("model")

        await websocket.send_json({"status": "planning", "message": "AI is planning the task…"})

        result = await agent_service.execute(
            task=task,
            context=context,
            workspace_path=workspace_path,
            model=model,
        )

        # Send each step
        for step in result.get("steps", []):
            await websocket.send_json({"status": "step", "step": step})

        await websocket.send_json({"status": "done", "result": result})

    except WebSocketDisconnect:
        logger.info("WebSocket /ws/agent disconnected")
    except Exception as exc:
        logger.error("WebSocket /ws/agent error: %s", exc)
        try:
            await websocket.send_json({"status": "error", "message": str(exc)})
        except Exception:
            pass


# ── Workspace management ──────────────────────────────────────────

@router.post("/workspace/open")
async def open_workspace(req: WorkspaceOpenRequest):
    """Open a project folder as the active workspace."""
    try:
        meta = workspace_manager.open(req.path)
        return {"success": True, "workspace": meta}
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/workspace/list")
async def list_workspaces():
    """List all currently open workspaces."""
    return {"workspaces": workspace_manager.active_workspaces}


@router.post("/workspace/close")
async def close_workspace(req: WorkspaceOpenRequest):
    """Remove a workspace from the active list."""
    workspace_manager.close(req.path)
    return {"success": True, "message": f"Closed: {req.path}"}
