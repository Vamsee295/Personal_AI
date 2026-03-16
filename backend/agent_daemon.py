"""
agent_daemon.py – Background AI service that runs independently of the UI.

Responsibilities:
  • Continuous voice command listener
  • Periodic screen monitoring (detect errors)
  • Task reminder notifications

Run with:  python agent_daemon.py
"""

from __future__ import annotations
import asyncio
import sys
from pathlib import Path

# Make sure the app package is importable when running from backend/
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.database.db import init_db, log_activity
from app.services.ai_service import ai_service
from app.utils.logger import get_logger

logger = get_logger("daemon")


async def handle_voice_command(text: str) -> str:
    """Process a voice command through the AI and return a spoken reply."""
    logger.info("Voice: %s", text)
    await log_activity("voice_command", text)
    return await ai_service.chat(text, history=[])


async def voice_loop() -> None:
    """Continuously listen for voice commands and respond."""
    try:
        from app.agents.voice_agent import voice_agent
        logger.info("Voice loop started.")
        await voice_agent.voice_command_loop(handle_voice_command)
    except Exception as exc:
        logger.warning("Voice loop unavailable: %s", exc)


async def task_reminder_loop() -> None:
    """Check pending tasks every 30 minutes and log a reminder."""
    from app.database.db import list_tasks
    while True:
        try:
            tasks = await list_tasks(status="pending")
            if tasks:
                logger.info("Reminder: %d pending task(s)", len(tasks))
                await log_activity("task_reminder", f"{len(tasks)} pending tasks")
        except Exception as exc:
            logger.error("Reminder loop error: %s", exc)
        await asyncio.sleep(1800)   # 30 minutes


async def main() -> None:
    logger.info("═══ Vamsee AI Daemon starting ═══")
    await init_db()
    await log_activity("daemon_start", "Background agent started")

    # Run all background loops concurrently
    await asyncio.gather(
        task_reminder_loop(),
        # Uncomment to enable voice:
        # voice_loop(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Daemon stopped.")
