"""
core/ollama_client.py – Low-level async client for the Ollama REST API.

Supports both streaming and non-streaming completions.
"""

from __future__ import annotations
import json
import asyncio
from typing import AsyncIterator, Optional, List, Dict, Any

import aiohttp
import requests

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("ollama_client")


class OllamaClient:
    """Async HTTP client that wraps the Ollama local API."""

    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")
        self.generate_url = f"{self.base_url}/api/generate"
        self.chat_url = f"{self.base_url}/api/chat"
        self.tags_url = f"{self.base_url}/api/tags"

    # ─────────────────────────────────────────────────────────────
    #  List available models
    # ─────────────────────────────────────────────────────────────
    async def list_models(self) -> List[str]:
        """Return a list of locally available Ollama model names."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.tags_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception as exc:
            logger.warning("Could not fetch Ollama models: %s", exc)
            return []

    # ─────────────────────────────────────────────────────────────
    #  Non-streaming single completion
    # ─────────────────────────────────────────────────────────────
    async def generate(
        self,
        prompt: str,
        model: str = settings.DEFAULT_MODEL,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send a prompt to Ollama and return the full response string."""
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        logger.debug("Ollama generate → model=%s, prompt_len=%d", model, len(prompt))

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.generate_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=settings.OLLAMA_TIMEOUT),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("response", "")

    # ─────────────────────────────────────────────────────────────
    #  Streaming completion (yields text chunks)
    # ─────────────────────────────────────────────────────────────
    async def generate_stream(
        self,
        prompt: str,
        model: str = settings.DEFAULT_MODEL,
        system: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """Yield text tokens as they arrive from Ollama."""
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        logger.debug("Ollama stream  → model=%s", model)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.generate_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=settings.OLLAMA_TIMEOUT),
            ) as resp:
                resp.raise_for_status()
                async for raw_line in resp.content:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("response", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    # ─────────────────────────────────────────────────────────────
    #  Chat endpoint (multi-turn)
    # ─────────────────────────────────────────────────────────────
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = settings.DEFAULT_MODEL,
        stream: bool = False,
    ) -> str:
        """Send a chat (multi-turn) request and return the assistant reply."""
        payload = {"model": model, "messages": messages, "stream": stream}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.chat_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=settings.OLLAMA_TIMEOUT),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data.get("message", {}).get("content", "")

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = settings.DEFAULT_MODEL,
    ) -> AsyncIterator[str]:
        """Yield chat reply tokens progressively."""
        payload = {"model": model, "messages": messages, "stream": True}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.chat_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=settings.OLLAMA_TIMEOUT),
            ) as resp:
                resp.raise_for_status()
                async for raw_line in resp.content:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        token = chunk.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

    # ─────────────────────────────────────────────────────────────
    #  Health check
    # ─────────────────────────────────────────────────────────────
    def is_running(self) -> bool:
        """Quick synchronous check that Ollama is reachable."""
        try:
            r = requests.get(f"{self.base_url}/", timeout=3)
            return r.status_code == 200
        except Exception:
            return False


# Module-level singleton
ollama = OllamaClient()
