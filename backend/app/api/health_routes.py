"""
api/health_routes.py -- Health and diagnostic endpoints.

GET /api/health            -- full status check (FastAPI + Ollama + system)
GET /api/screenshot/latest -- serve the most recent PNG from screenshots/
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("health_routes")

router = APIRouter(prefix="/api", tags=["Health"])

# ── Screenshots directory (same as action_executor uses) ──────────────────────
_SCREENSHOTS_DIR = Path(__file__).resolve().parent.parent.parent / "screenshots"


@router.get("/health")
async def health_check():
    """
    Returns the overall backend health including Ollama availability.
    Used by the frontend to display the status indicator.
    """
    import requests as req

    ollama_running = False
    try:
        r = req.get(f"{settings.OLLAMA_BASE_URL}/", timeout=3)
        ollama_running = r.status_code == 200
    except Exception:
        pass

    return {
        "status":         "ok",
        "ollama_running": ollama_running,
        "ollama_url":     settings.OLLAMA_BASE_URL,
        "model":          settings.DEFAULT_MODEL,
        "version":        settings.APP_VERSION,
    }


@router.get("/screenshot/latest")
async def latest_screenshot():
    """
    Serve the most recently saved PNG file from the screenshots/ directory.

    Returns a FileResponse (image/png) that the frontend <img> tag can display
    directly via URL rather than needing base64 encoding.

    Returns 404 if no screenshots have been taken yet.
    """
    if not _SCREENSHOTS_DIR.exists():
        raise HTTPException(status_code=404, detail="No screenshots directory found.")

    # Sort by modification time, newest first
    pngs = sorted(
        _SCREENSHOTS_DIR.glob("*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not pngs:
        raise HTTPException(status_code=404, detail="No screenshots taken yet.")

    latest = pngs[0]
    logger.info("Serving latest screenshot: %s", latest.name)

    return FileResponse(
        path=str(latest),
        media_type="image/png",
        filename=latest.name,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )
