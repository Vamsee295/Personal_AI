"""
system/app_control.py – Open, close, and manage system applications.
"""

from __future__ import annotations
import subprocess
import sys
from typing import Optional

from app.utils.logger import get_logger

logger = get_logger("app_control")

_IS_WINDOWS = sys.platform == "win32"

# Well-known app shortcuts (cross-platform where possible)
KNOWN_APPS = {
    "vscode": "code",
    "code": "code",
    "chrome": "chrome" if not _IS_WINDOWS else "start chrome",
    "notepad": "notepad",
    "explorer": "explorer",
    "terminal": "wt" if _IS_WINDOWS else "gnome-terminal",
    "calculator": "calc" if _IS_WINDOWS else "gnome-calculator",
    "browser": "start microsoft-edge:" if _IS_WINDOWS else "xdg-open https://google.com",
}


def open_app(app_name: str, args: Optional[str] = None) -> dict:
    """
    Launch an application by name or executable path.
    Returns {"success": bool, "command": str, "pid": int|None}
    """
    command = KNOWN_APPS.get(app_name.lower(), app_name)
    if args:
        command = f"{command} {args}"

    try:
        if _IS_WINDOWS:
            proc = subprocess.Popen(command, shell=True)
        else:
            proc = subprocess.Popen(command.split())

        logger.info("Opened app: %s  (pid=%s)", command, proc.pid)
        return {"success": True, "command": command, "pid": proc.pid}

    except Exception as exc:
        logger.error("Failed to open %s: %s", app_name, exc)
        return {"success": False, "command": command, "error": str(exc)}


def open_vscode(path: Optional[str] = None) -> dict:
    """Open VS Code, optionally at a specific path."""
    return open_app("code", args=path or ".")


def open_browser(url: str = "https://google.com") -> dict:
    """Open the default browser at a given URL."""
    if _IS_WINDOWS:
        command = f"start {url}"
    else:
        command = f"xdg-open {url}"

    try:
        subprocess.Popen(command, shell=True)
        return {"success": True, "url": url}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
