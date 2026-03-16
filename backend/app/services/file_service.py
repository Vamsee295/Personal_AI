"""
services/file_service.py – Sandboxed CRUD operations on project files.
"""

from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import List

from app.core.security import assert_path_allowed
from app.models.schemas import FileInfo
from app.utils.logger import get_logger

logger = get_logger("file_service")


class FileService:
    """All file I/O goes through this service so path sandboxing is enforced."""

    # ─────────────────────────────────────────────────────────────
    #  Read
    # ─────────────────────────────────────────────────────────────
    def read(self, path: str) -> str:
        p = assert_path_allowed(path)
        if not p.is_file():
            raise FileNotFoundError(f"'{p}' does not exist or is a directory.")
        text = p.read_text(encoding="utf-8", errors="replace")
        logger.info("Read file: %s  (%d chars)", p, len(text))
        return text

    # ─────────────────────────────────────────────────────────────
    #  Write (overwrite)
    # ─────────────────────────────────────────────────────────────
    def write(self, path: str, content: str) -> None:
        p = assert_path_allowed(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        logger.info("Wrote file: %s  (%d chars)", p, len(content))

    # ─────────────────────────────────────────────────────────────
    #  Create (fail if exists)
    # ─────────────────────────────────────────────────────────────
    def create(self, path: str, content: str = "") -> None:
        p = assert_path_allowed(path)
        if p.exists():
            raise FileExistsError(f"'{p}' already exists. Use write() to overwrite.")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        logger.info("Created file: %s", p)

    # ─────────────────────────────────────────────────────────────
    #  Delete
    # ─────────────────────────────────────────────────────────────
    def delete(self, path: str) -> None:
        p = assert_path_allowed(path)
        if not p.exists():
            raise FileNotFoundError(f"'{p}' does not exist.")
        if p.is_dir():
            shutil.rmtree(p)
            logger.info("Deleted directory: %s", p)
        else:
            p.unlink()
            logger.info("Deleted file: %s", p)

    # ─────────────────────────────────────────────────────────────
    #  Rename / move
    # ─────────────────────────────────────────────────────────────
    def rename(self, old_path: str, new_path: str) -> None:
        src = assert_path_allowed(old_path)
        dst = assert_path_allowed(new_path)
        if not src.exists():
            raise FileNotFoundError(f"'{src}' does not exist.")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        logger.info("Moved/Renamed: %s → %s", src, dst)

    # ─────────────────────────────────────────────────────────────
    #  List
    # ─────────────────────────────────────────────────────────────
    def list_dir(self, path: str, recursive: bool = False) -> List[FileInfo]:
        p = assert_path_allowed(path)
        if not p.is_dir():
            raise NotADirectoryError(f"'{p}' is not a directory.")

        items: List[FileInfo] = []

        if recursive:
            for root, dirs, files in os.walk(p):
                # prune heavy dirs
                dirs[:] = [
                    d for d in dirs
                    if d not in {"node_modules", "__pycache__", ".git", "dist", "build", ".next"}
                ]
                for fname in files:
                    fp = Path(root) / fname
                    items.append(FileInfo(
                        name=fp.name,
                        path=str(fp),
                        is_dir=False,
                        size=fp.stat().st_size,
                        extension=fp.suffix.lower(),
                    ))
                for dname in dirs:
                    dp = Path(root) / dname
                    items.append(FileInfo(name=dp.name, path=str(dp), is_dir=True))
        else:
            for entry in sorted(p.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
                items.append(FileInfo(
                    name=entry.name,
                    path=str(entry),
                    is_dir=entry.is_dir(),
                    size=entry.stat().st_size if entry.is_file() else None,
                    extension=entry.suffix.lower() if entry.is_file() else None,
                ))

        logger.debug("list_dir(%s)  recursive=%s  items=%d", p, recursive, len(items))
        return items

    # ─────────────────────────────────────────────────────────────
    #  Simple text search across files
    # ─────────────────────────────────────────────────────────────
    def search_code(self, directory: str, query: str) -> List[dict]:
        """
        Search for `query` (case-insensitive) in all text files under `directory`.
        Returns list of {file, line_number, line} dicts.
        """
        root = assert_path_allowed(directory)
        results = []

        for fpath in root.rglob("*"):
            if fpath.is_dir():
                continue
            if fpath.suffix.lower() in {".png", ".jpg", ".gif", ".ico", ".ttf", ".woff", ".exe"}:
                continue
            try:
                for i, line in enumerate(fpath.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    if query.lower() in line.lower():
                        results.append({
                            "file": str(fpath),
                            "line_number": i,
                            "line": line.strip(),
                        })
            except Exception:
                continue

        logger.info("search_code('%s') → %d matches", query, len(results))
        return results


# Module-level singleton
file_service = FileService()
