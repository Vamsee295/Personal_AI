"""
services/terminal_service.py – Safe subprocess-based command execution.
"""

from __future__ import annotations
import asyncio
import subprocess
import sys
from typing import AsyncIterator, Optional, Tuple

from app.core.security import assert_command_safe
from app.utils.logger import get_logger

logger = get_logger("terminal_service")

_IS_WINDOWS = sys.platform == "win32"


class TerminalService:
    """Executes shell commands with security checks and output streaming."""

    # ─────────────────────────────────────────────────────────────
    #  Non-streaming run
    # ─────────────────────────────────────────────────────────────
    async def run(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 30,
    ) -> Tuple[str, str, int]:
        """
        Execute `command` and return (stdout, stderr, return_code).
        Raises ValueError if command is blocked.
        """
        assert_command_safe(command)

        logger.info("Running command: %s  (cwd=%s)", command, cwd)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                shell=True,
            )

            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            rc = proc.returncode or 0

            logger.info("Command finished rc=%d  stdout_len=%d", rc, len(stdout))
            return stdout, stderr, rc

        except asyncio.TimeoutError:
            logger.warning("Command timed out: %s", command)
            raise TimeoutError(f"Command timed out after {timeout}s: {command}")
        except Exception as exc:
            logger.error("Command error: %s", exc)
            raise

    # ─────────────────────────────────────────────────────────────
    #  Streaming run (yields lines)
    # ─────────────────────────────────────────────────────────────
    async def run_stream(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 60,
    ) -> AsyncIterator[str]:
        """
        Execute `command` and yield stdout / stderr lines as they arrive.
        """
        assert_command_safe(command)
        logger.info("Streaming command: %s", command)

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,   # merge stderr into stdout
            cwd=cwd,
            shell=True,
        )

        start = asyncio.get_event_loop().time()

        assert proc.stdout is not None

        while True:
            try:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=1.0)
            except asyncio.TimeoutError:
                if asyncio.get_event_loop().time() - start > timeout:
                    proc.kill()
                    yield "[TIMEOUT] Command exceeded time limit.\n"
                    break
                # process still running, just no output yet
                if proc.returncode is not None:
                    break
                continue

            if not line:
                break

            decoded = line.decode("utf-8", errors="replace")
            yield decoded

        await proc.wait()
        yield f"\n[Process exited with code {proc.returncode}]\n"


# Module-level singleton
terminal_service = TerminalService()
