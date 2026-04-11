"""
api/memory_routes.py -- Memory system endpoints.

GET  /memory/recent          -- last 20 commands
GET  /memory/stats           -- total commands, success rate, db size, etc.
POST /memory/preference      -- manually save a preference
DELETE /memory/clear         -- delete commands older than N days
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.utils.logger import get_logger

logger = get_logger("memory_routes")

router = APIRouter(prefix="/memory", tags=["Memory"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class PreferenceRequest(BaseModel):
    key:   str
    value: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/recent")
async def get_recent_commands(
    limit:  int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Return the last N commands from the memory database, most recent first.
    Paginate with limit + offset for the memory viewer UI.
    """
    try:
        from memory.memory_manager import memory
        commands = memory.get_commands_page(limit=limit, offset=offset)
        total_stats = memory.get_memory_stats()
        return {
            "commands": commands,
            "count": len(commands),
            "total_commands": total_stats.get("total_commands", 0),
            "limit": limit,
            "offset": offset,
        }
    except Exception as exc:
        logger.error("GET /memory/recent error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stats")
async def get_memory_stats():
    """
    Return aggregate statistics about the memory database.

    Response shape:
        {
          "total_commands": 42,
          "success_rate": 0.95,
          "most_used_action": "open_app",
          "preferences_count": 5,
          "db_size_kb": 12.3
        }
    """
    try:
        from memory.memory_manager import memory
        return memory.get_memory_stats()
    except Exception as exc:
        logger.error("GET /memory/stats error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/preference")
async def save_preference(req: PreferenceRequest):
    """
    Manually save or update a user preference.

    Example body:
        {"key": "preferred_browser", "value": "chrome"}
    """
    if not req.key.strip() or not req.value.strip():
        raise HTTPException(status_code=400, detail="Both 'key' and 'value' are required.")
    try:
        from memory.memory_manager import memory
        memory.save_preference(req.key.strip(), req.value.strip())
        return {
            "success": True,
            "key": req.key,
            "value": req.value,
            "message": f"Preference '{req.key}' saved.",
        }
    except Exception as exc:
        logger.error("POST /memory/preference error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/preferences")
async def get_preferences():
    """Return all saved user preferences."""
    try:
        from memory.memory_manager import memory
        return {
            "preferences": memory.get_all_preferences(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/clear")
async def clear_old_memories(days: int = Query(30, ge=1, le=365)):
    """
    Delete commands older than `days` days to keep the database lean.
    Default is 30 days.
    """
    try:
        from memory.memory_manager import memory
        deleted = memory.clear_old_memories(days)
        return {
            "success": True,
            "deleted": deleted,
            "message": f"Deleted {deleted} command(s) older than {days} days.",
        }
    except Exception as exc:
        logger.error("DELETE /memory/clear error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/search")
async def search_commands(q: str = Query(..., min_length=2), limit: int = Query(5, ge=1, le=20)):
    """Search past commands by keyword."""
    try:
        from memory.memory_manager import memory
        results = memory.search_similar_commands(q, limit)
        return {"query": q, "results": results, "count": len(results)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
