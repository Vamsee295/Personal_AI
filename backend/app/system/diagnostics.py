"""
system/diagnostics.py -- Runs dependency and health verification checks on startup.
"""

from __future__ import annotations
import asyncio
import logging
from pathlib import Path
from app.services.tool_health import tool_health

logger = logging.getLogger("diagnostics")

async def run_startup_diagnostics() -> bool:
    """Verifies that all core dependencies are installed and available."""
    logger.info("Running JARVIS Startup Diagnostics...")
    all_clear = True

    # 1. Database Check
    try:
        from app.database.db import init_db
        await init_db()
        tool_health.report_success("database")
        logger.info("[OK] SQLite Database initialized.")
    except Exception as e:
        tool_health.report_error("database", str(e))
        logger.error(f"[FAIL] SQLite Database: {e}")
        all_clear = False

    # 2. Ollama Check
    try:
        import aiohttp
        from app.config import settings
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5) as resp:
                if resp.status == 200:
                    tool_health.report_success("ollama")
                    logger.info(f"[OK] Ollama reachable at {settings.OLLAMA_BASE_URL}")
                else:
                    raise Exception(f"HTTP {resp.status}")
    except Exception as e:
        tool_health.report_error("ollama", str(e))
        logger.error(f"[FAIL] Ollama: {e}")
        all_clear = False

    # 3. Playwright Check
    try:
        import playwright
        tool_health.report_success("browser")
        logger.info("[OK] Playwright module found.")
    except Exception as e:
        tool_health.report_error("browser", "Playwright not installed")
        logger.error(f"[FAIL] Playwright: {e}")
        all_clear = False

    # 4. Voice Check
    try:
        import piper
        from faster_whisper import WhisperModel
        tool_health.report_success("voice")
        logger.info("[OK] Piper TTS and Faster-Whisper modules found.")
    except Exception as e:
        tool_health.report_error("voice", str(e))
        logger.error(f"[FAIL] Voice dependencies missing: {e}")
        # Not marking all_clear=False since voice might be optional for text-only workflows

    # 5. Directory Check
    directories = ["memory", "screenshots", "chrome_profile", "logs"]
    root = Path(__file__).resolve().parent.parent.parent
    for d in directories:
        dir_path = root / d
        dir_path.mkdir(exist_ok=True)

    if all_clear:
        logger.info("Diagnostics Complete. All core systems GO.")
    else:
        logger.warning("Diagnostics Complete with WARNINGS. Some sub-systems are degraded.")

    return all_clear
