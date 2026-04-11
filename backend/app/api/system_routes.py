"""
api/system_routes.py – Endpoints for system-level automation (apps, file organiser, screen).
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.system.app_control import open_app, open_vscode, open_browser
from app.utils.logger import get_logger

logger = get_logger("system_routes")

router = APIRouter(prefix="/api/system", tags=["System Control"])


class OpenAppRequest(BaseModel):
    app: str
    args: Optional[str] = None


class OrganiseRequest(BaseModel):
    directory: str
    dry_run: bool = False


class BrowserRequest(BaseModel):
    url: str = "https://google.com"


# ── Open application ───────────────────────────────────────────────
@router.post("/open-app")
async def api_open_app(req: OpenAppRequest):
    result = open_app(req.app, req.args)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result


@router.post("/open-vscode")
async def api_open_vscode(path: Optional[str] = None):
    return open_vscode(path)


@router.post("/open-browser")
async def api_open_browser(req: BrowserRequest):
    return open_browser(req.url)


# ── File organiser ─────────────────────────────────────────────────
@router.post("/organise-files")
async def api_organise_files(req: OrganiseRequest):
    try:
        from app.agents.file_agent import file_agent
        actions = file_agent.organise(req.directory, req.dry_run)
        return {"success": True, "actions": actions, "count": len(actions)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ── Screen capture ─────────────────────────────────────────────────
@router.get("/screen-capture")
async def api_screen_capture():
    """Return a base64-encoded PNG of the current screen."""
    try:
        from app.agents.screen_agent import screen_agent
        import asyncio
        b64 = await asyncio.to_thread(screen_agent.capture_base64)
        return {"success": True, "image_base64": b64}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/screen-text")
async def api_screen_text():
    """Run OCR on the current screen and return extracted text."""
    try:
        from app.agents.screen_agent import screen_agent
        import asyncio
        text = await asyncio.to_thread(screen_agent.extract_text)
        return {"success": True, "text": text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Task management (DB) ──────────────────────────────────────────

class TaskRequest(BaseModel):
    title: str
    description: str = ""
    priority: int = 3


@router.post("/tasks")
async def create_task(req: TaskRequest):
    from app.database.db import create_task as db_create_task
    task_id = await db_create_task(req.title, req.description, req.priority)
    return {"success": True, "task_id": task_id}


@router.get("/tasks")
async def list_tasks(status: Optional[str] = None):
    from app.database.db import list_tasks as db_list_tasks
    tasks = await db_list_tasks(status)
    return {"tasks": tasks}
