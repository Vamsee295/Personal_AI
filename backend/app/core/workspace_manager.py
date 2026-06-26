"""
core/workspace_manager.py – Tracks open projects, indexes files, and provides a tree view.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, List, Set

from app.core.security import assert_path_allowed
from app.utils.logger import get_logger

logger = get_logger("workspace_manager")

# File types to index when scanning for code (for summarisation / search)
CODE_EXTENSIONS: Set[str] = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
    ".java", ".cpp", ".c", ".h", ".rs", ".go", ".rb", ".php",
    ".json", ".yaml", ".yml", ".toml", ".md", ".txt", ".sh", ".bat",
}


class WorkspaceManager:
    """Manages the list of open project workspaces."""

    def __init__(self) -> None:
        # Map: absolute-path-string → workspace metadata dict
        self._workspaces: Dict[str, dict] = {}

    # ─────────────────────────────────────────────────────────────
    #  Open / close
    # ─────────────────────────────────────────────────────────────
    def open(self, path: str) -> dict:
        """Open a project folder as a workspace and return its metadata."""
        root = assert_path_allowed(path)  # raises if not allowed

        if not root.is_dir():
            raise FileNotFoundError(f"'{root}' is not a directory.")

        meta = self._scan(root)
        self._workspaces[str(root)] = meta
        logger.info("Opened workspace: %s  (%d files)", root, meta["file_count"])
        return meta

    def close(self, path: str) -> None:
        resolved = str(Path(path).resolve())
        self._workspaces.pop(resolved, None)

    @property
    def active_workspaces(self) -> List[dict]:
        return list(self._workspaces.values())

    # ─────────────────────────────────────────────────────────────
    #  Directory tree
    # ─────────────────────────────────────────────────────────────
    def get_tree(self, path: str, max_depth: int = 4) -> List[dict]:
        """
        Return a nested dict tree of the directory, respecting the sandbox.
        """
        root = assert_path_allowed(path)
        return self._build_tree(root, depth=0, max_depth=max_depth)

    def _build_tree(self, directory: Path, depth: int, max_depth: int) -> List[dict]:
        if depth > max_depth:
            return []
        nodes = []
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            return []

        for entry in entries:
            if entry.name.startswith(".") and entry.name not in {".env"}:
                continue  # skip hidden files (except .env)
            if entry.name in {"node_modules", "__pycache__", ".git", "dist", "build", ".next"}:
                continue  # skip heavy folders

            node: dict = {
                "name": entry.name,
                "path": str(entry),
                "is_dir": entry.is_dir(),
            }
            if entry.is_dir():
                node["children"] = self._build_tree(entry, depth + 1, max_depth)
            else:
                node["size"] = entry.stat().st_size
                node["extension"] = entry.suffix.lower()

            nodes.append(node)
        return nodes

    # ─────────────────────────────────────────────────────────────
    #  Internal helpers
    # ─────────────────────────────────────────────────────────────
    def _scan(self, root: Path) -> dict:
        """Walk the workspace root and collect basic statistics."""
        file_count = 0
        languages: Set[str] = set()

        for dirpath, dirnames, filenames in os.walk(root):
            # Prune dirs we never want to recurse into
            dirnames[:] = [
                d for d in dirnames
                if d not in {"node_modules", "__pycache__", ".git", "dist", "build", ".next"}
                and not d.startswith(".")
            ]
            for fname in filenames:
                ext = Path(fname).suffix.lower()
                if ext in CODE_EXTENSIONS:
                    languages.add(ext.lstrip("."))
                file_count += 1

        return {
            "path": str(root),
            "name": root.name,
            "file_count": file_count,
            "languages": sorted(languages),
        }


# Module-level singleton
workspace_manager = WorkspaceManager()
