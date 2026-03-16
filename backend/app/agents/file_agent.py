"""
agents/file_agent.py – AI-driven file organisation (e.g. Downloads sorter).
"""

from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import Dict, List

from app.core.security import assert_path_allowed
from app.utils.logger import get_logger

logger = get_logger("file_agent")

# Extension → target sub-folder mapping
CATEGORY_MAP: Dict[str, str] = {
    # Images
    "jpg": "Images", "jpeg": "Images", "png": "Images",
    "gif": "Images", "bmp": "Images", "webp": "Images",
    "svg": "Images",
    # Documents
    "pdf": "Documents", "docx": "Documents", "doc": "Documents",
    "xlsx": "Documents", "xls": "Documents", "pptx": "Documents",
    "txt": "Documents",
    # Videos
    "mp4": "Videos", "mkv": "Videos", "avi": "Videos", "mov": "Videos",
    # Audio
    "mp3": "Audio", "wav": "Audio", "flac": "Audio", "aac": "Audio",
    # Archives
    "zip": "Archives", "rar": "Archives", "7z": "Archives", "tar": "Archives",
    "gz": "Archives",
    # Code
    "py": "Code", "js": "Code", "ts": "Code", "java": "Code",
    "cpp": "Code", "c": "Code", "go": "Code", "rs": "Code",
    # Installers
    "exe": "Installers", "msi": "Installers", "dmg": "Installers",
}


class FileAgent:
    """Organises a directory by sorting files into categorised sub-folders."""

    def organise(self, directory: str, dry_run: bool = False) -> List[dict]:
        """
        Sort all files in `directory` into sub-folders based on extension.
        Returns a list of {"file", "moved_to"} dicts describing actions taken.
        dry_run=True logs actions without moving anything.
        """
        root = assert_path_allowed(directory)
        if not root.is_dir():
            raise NotADirectoryError(f"'{root}' is not a directory.")

        actions: List[dict] = []

        for entry in root.iterdir():
            if entry.is_dir():
                continue
            ext = entry.suffix.lstrip(".").lower()
            category = CATEGORY_MAP.get(ext, "Other")
            dest_dir = root / category
            dest_path = dest_dir / entry.name

            if not dry_run:
                dest_dir.mkdir(exist_ok=True)
                shutil.move(str(entry), str(dest_path))
                logger.info("Moved %s → %s/%s", entry.name, category, entry.name)

            actions.append({
                "file": entry.name,
                "moved_to": str(dest_path),
                "category": category,
                "dry_run": dry_run,
            })

        return actions


# Module-level singleton
file_agent = FileAgent()
