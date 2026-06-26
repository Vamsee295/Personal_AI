"""
config.py – Central configuration for Vamsee AI Backend.
All settings are read from environment variables (or .env file via pydantic-settings).
"""

from __future__ import annotations
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────
    APP_NAME: str = "Ultron Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ── Server ─────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── CORS – allow frontend dev server ─────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",   # Next.js dev
        "http://localhost:5173",   # Vite dev
        "http://localhost:8080",
    ]

    # ── Ollama ────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_MODEL: str = "qwen2.5-coder:7b"
    OLLAMA_TIMEOUT: int = 120          # seconds per request

    # ── Workspace / file-system sandbox ─────────────────────────
    # Only paths UNDER these roots are accessible to the AI.
    ALLOWED_WORKSPACE_ROOTS: List[str] = [
        "C:/Users/Vamsee/Projects",
        "X:/Project-Buildings",
    ]

    # ── Terminal security ─────────────────────────────────────────
    # Commands whose FIRST token is in this list are always rejected.
    BLOCKED_COMMANDS: List[str] = [
        "rm", "del", "rmdir", "rd", "format",
        "shutdown", "reboot", "restart",
        "reg", "regedit", "net", "netsh",
        "taskkill", "cipher", "diskpart",
    ]

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./ultron.db"

    # ── Logging ──────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"

    # ── Tesseract OCR ─────────────────────────────────────────────
    # Manual path to tesseract.exe (e.g., "C:/Program Files/Tesseract-OCR/tesseract.exe")
    TESSERACT_PATH: Optional[str] = None

    # ── External APIs (Secrets) ──────────────────────────────────
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # ── Voice ────────────────────────────────────────────────────
    PICOVOICE_ACCESS_KEY: Optional[str] = None
    WAKE_WORD_PPN: Optional[str] = None

    # ── Testing ──────────────────────────────────────────────────
    WHATSAPP_TEST_CONTACT: str = "Test"


# Singleton instance - import this everywhere.
Settings.model_rebuild()
settings = Settings()
