"""
api/file_routes.py – REST endpoints for file system operations.
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    FileReadRequest, FileWriteRequest, FileCreateRequest,
    FileDeleteRequest, FileRenameRequest,
    DirectoryListRequest, DirectoryListResponse,
    SuccessResponse,
)
from app.services.file_service import file_service
from app.core.workspace_manager import workspace_manager
from app.utils.logger import get_logger

logger = get_logger("file_routes")

router = APIRouter(prefix="/api/files", tags=["File System"])


def _http_error(exc: Exception) -> HTTPException:
    """Convert common exceptions to HTTPException."""
    if isinstance(exc, (FileNotFoundError, NotADirectoryError)):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, FileExistsError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ValueError):          # security / path violation
        return HTTPException(status_code=403, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


# ── List directory ─────────────────────────────────────────────────
@router.post("/list", response_model=DirectoryListResponse)
async def list_directory(req: DirectoryListRequest):
    try:
        items = file_service.list_dir(req.path, req.recursive)
        return DirectoryListResponse(path=req.path, items=items)
    except Exception as exc:
        raise _http_error(exc)


# ── Read file ──────────────────────────────────────────────────────
@router.post("/read")
async def read_file(req: FileReadRequest):
    try:
        content = file_service.read(req.path)
        return {"path": req.path, "content": content}
    except Exception as exc:
        raise _http_error(exc)


# ── Write file ─────────────────────────────────────────────────────
@router.post("/write", response_model=SuccessResponse)
async def write_file(req: FileWriteRequest):
    try:
        file_service.write(req.path, req.content)
        return SuccessResponse(message=f"File written: {req.path}")
    except Exception as exc:
        raise _http_error(exc)


# ── Create file ────────────────────────────────────────────────────
@router.post("/create", response_model=SuccessResponse)
async def create_file(req: FileCreateRequest):
    try:
        file_service.create(req.path, req.content)
        return SuccessResponse(message=f"File created: {req.path}")
    except Exception as exc:
        raise _http_error(exc)


# ── Delete file ────────────────────────────────────────────────────
@router.post("/delete", response_model=SuccessResponse)
async def delete_file(req: FileDeleteRequest):
    try:
        file_service.delete(req.path)
        return SuccessResponse(message=f"Deleted: {req.path}")
    except Exception as exc:
        raise _http_error(exc)


# ── Rename / move ─────────────────────────────────────────────────
@router.post("/rename", response_model=SuccessResponse)
async def rename_file(req: FileRenameRequest):
    try:
        file_service.rename(req.old_path, req.new_path)
        return SuccessResponse(message=f"Renamed: {req.old_path} → {req.new_path}")
    except Exception as exc:
        raise _http_error(exc)


# ── Code search ────────────────────────────────────────────────────
@router.get("/search")
async def search_code(directory: str, query: str):
    try:
        results = file_service.search_code(directory, query)
        return {"query": query, "results": results, "count": len(results)}
    except Exception as exc:
        raise _http_error(exc)


# ── Workspace tree ─────────────────────────────────────────────────
@router.get("/tree")
async def get_tree(path: str, max_depth: int = 4):
    try:
        tree = workspace_manager.get_tree(path, max_depth)
        return {"path": path, "tree": tree}
    except Exception as exc:
        raise _http_error(exc)
