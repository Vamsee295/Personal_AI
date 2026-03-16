"""
core/security.py – Path sandbox and command-whitelist enforcement.
"""

from __future__ import annotations
from pathlib import Path
from typing import List

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("security")


# ══════════════════════════════════════════════════════════════════
#  File-system sandbox
# ══════════════════════════════════════════════════════════════════

def _allowed_roots() -> List[Path]:
    return [Path(r).resolve() for r in settings.ALLOWED_WORKSPACE_ROOTS]


def is_path_allowed(target: str | Path) -> bool:
    """
    Return True only when `target` is inside one of the configured workspace roots.
    Raises ValueError with a descriptive message when blocked.
    """
    try:
        target_path = Path(target).resolve()
    except Exception as exc:
        raise ValueError(f"Invalid path: {target}") from exc

    for root in _allowed_roots():
        try:
            target_path.relative_to(root)
            return True
        except ValueError:
            continue

    raise ValueError(
        f"Access denied: '{target_path}' is outside the allowed workspace roots. "
        f"Allowed roots: {[str(r) for r in _allowed_roots()]}"
    )


def assert_path_allowed(path: str | Path) -> Path:
    """
    Wrapper that raises ValueError if the path is not allowed.
    Returns the resolved Path on success.
    """
    is_path_allowed(path)           # raises on failure
    return Path(path).resolve()


# ══════════════════════════════════════════════════════════════════
#  Terminal command safety
# ══════════════════════════════════════════════════════════════════

def is_command_safe(command: str) -> bool:
    """
    Return True when the command does not start with any blocked token.
    Raises ValueError with a reason when blocked.
    """
    if not command or not command.strip():
        raise ValueError("Empty command is not allowed.")

    first_token = command.strip().split()[0].lower()

    # Strip leading path separators (e.g. ./rm or /bin/rm → rm)
    first_token = first_token.split("/")[-1].split("\\")[-1]

    if first_token in [b.lower() for b in settings.BLOCKED_COMMANDS]:
        raise ValueError(
            f"Command '{first_token}' is blocked for security reasons."
        )

    return True


def assert_command_safe(command: str) -> str:
    """Raises ValueError if the command is blocked, else returns the command."""
    is_command_safe(command)
    return command
