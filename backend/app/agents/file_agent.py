"""
agents/file_agent.py – AI-driven file organisation (e.g. Downloads sorter).
"""

from __future__ import annotations
import os
import shutil
from typing import Dict, List, Any

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

    def __init__(self):
        self._undo_stack: List[List[dict]] = []

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
        reverse_actions: List[dict] = []

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

                # Record undo info
                reverse_actions.append({
                    "src": str(dest_path),
                    "dest": str(entry)
                })

            actions.append({
                "file": entry.name,
                "moved_to": str(dest_path),
                "category": category,
                "dry_run": dry_run,
            })

        if not dry_run and reverse_actions:
            self._undo_stack.append(reverse_actions)

        return actions

    def undo_last_organisation(self) -> Dict[str, Any]:
        """Revert the most recent file organisation."""
        if not self._undo_stack:
            return {"success": False, "error": "No actions to undo."}

        actions_to_undo = self._undo_stack.pop()
        success_count = 0

        for action in actions_to_undo:
            try:
                src = action["src"]
                dest = action["dest"]
                if os.path.exists(src):
                    shutil.move(src, dest)
                    success_count += 1

                    # Clean up empty directory
                    src_dir = os.path.dirname(src)
                    if not os.listdir(src_dir):
                        os.rmdir(src_dir)
            except Exception as e:
                logger.error(f"Undo failed for {src}: {e}")

        return {"success": True, "message": f"Successfully reversed {success_count} file moves."}

    async def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Use the Vision Agent or LLM to read and summarize a file (text/PDF).
        """
        try:
            path = assert_path_allowed(file_path)
            if not path.is_file():
                return {"success": False, "error": f"{path} is not a file."}

            ext = path.suffix.lower()
            content = ""

            if ext in [".txt", ".md", ".csv", ".json", ".py", ".js"]:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read(4000) # Read up to 4000 chars for context
            elif ext == ".pdf":
                try:
                    import fitz # PyMuPDF
                    doc = fitz.open(path)
                    for i in range(min(3, len(doc))): # Read up to 3 pages
                        content += doc.load_page(i).get_text()
                    content = content[:4000]
                except ImportError:
                    return {"success": False, "error": "PyMuPDF not installed, cannot read PDF"}
            else:
                return {"success": False, "error": f"Unsupported file type for analysis: {ext}"}

            from app.services.ai_service import ai_service
            from app.config import settings
            prompt = f"Analyze the following file content and provide a short 2-3 sentence summary of what this file is about:\n\n{content}"
            summary = await ai_service.chat(message=prompt, history=[], model=settings.DEFAULT_MODEL)

            return {"success": True, "summary": summary, "file": path.name}

        except Exception as e:
            logger.error(f"File analysis failed: {e}")
            return {"success": False, "error": str(e)}


# Module-level singleton
file_agent = FileAgent()
