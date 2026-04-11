"""
services/ai_service.py – High-level AI capabilities built on top of OllamaClient.
"""

from __future__ import annotations
from typing import AsyncIterator, List, Optional

from app.core.ollama_client import ollama
from app.config import settings
from app.models.schemas import ChatMessage
from app.utils.logger import get_logger

logger = get_logger("ai_service")

# ── System prompts ────────────────────────────────────────────────
_CHAT_SYSTEM = (
    "You are Ultron, a professional AI coding assistant integrated into a high-performance IDE. "
    "Your goal is to provide accurate, concise, and perfectly formatted code solutions.\n\n"
    "### Formatting Rules (STRICT):\n"
    "1. Always format responses using Markdown.\n"
    "2. All code must be inside triple backticks with the programming language specified (e.g., ```java).\n"
    "3. ALWAYS put a blank line BEFORE and AFTER every code block.\n"
    "4. Code blocks must start on a new line. Never merge code with normal text.\n"
    "5. Use headings (##, ###) for structure.\n"
    "6. Use numbered or bulleted lists for steps; avoid long wall-of-text paragraphs.\n"
    "7. If explaining code, keep it brief and impactful."
)

_CODE_GEN_SYSTEM = (
    "You are an expert software engineer. When asked to generate code, respond with "
    "ONLY the code block (no extra explanation unless asked). Make sure the code is "
    "correct, well-commented, and production-quality."
)

_AGENT_SYSTEM = (
    "You are an autonomous coding agent. You receive a task description and must "
    "reason step-by-step to produce a structured JSON plan of actions. Output ONLY "
    "valid JSON with a list of steps. Each step has: action (string), description (string)."
)


class AIService:
    """Provides chat, code generation, and agent-planning capabilities."""

    # ─────────────────────────────────────────────────────────────
    #  Chat
    # ─────────────────────────────────────────────────────────────
    async def chat(
        self,
        message: str,
        history: List[ChatMessage],
        model: Optional[str] = None,
    ) -> str:
        """Single-turn chat with conversation history."""
        model = model or settings.DEFAULT_MODEL

        messages = [{"role": "system", "content": _CHAT_SYSTEM}]
        for h in history:
            messages.append({"role": h.role, "content": h.content})
        messages.append({"role": "user", "content": message})

        response = await ollama.chat(messages=messages, model=model)
        logger.debug("Chat response len=%d", len(response))
        return response

    async def chat_stream(
        self,
        message: str,
        history: List[ChatMessage],
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Streaming chat – yields tokens as they arrive."""
        model = model or settings.DEFAULT_MODEL

        messages = [{"role": "system", "content": _CHAT_SYSTEM}]
        for h in history:
            messages.append({"role": h.role, "content": h.content})
        messages.append({"role": "user", "content": message})

        async for token in ollama.chat_stream(messages=messages, model=model):
            yield token

    # ─────────────────────────────────────────────────────────────
    #  Code generation
    # ─────────────────────────────────────────────────────────────
    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        context: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Generate code for the given prompt and optional context."""
        model = model or settings.DEFAULT_MODEL

        full_prompt = f"Language: {language}\n"
        if context:
            full_prompt += f"Existing code context:\n```{language}\n{context}\n```\n\n"
        full_prompt += f"Task: {prompt}"

        return await ollama.generate(
            prompt=full_prompt,
            model=model,
            system=_CODE_GEN_SYSTEM,
        )

    async def generate_code_stream(
        self,
        prompt: str,
        language: str = "python",
        context: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Streaming code generation."""
        model = model or settings.DEFAULT_MODEL

        full_prompt = f"Language: {language}\n"
        if context:
            full_prompt += f"Existing code context:\n```{language}\n{context}\n```\n\n"
        full_prompt += f"Task: {prompt}"

        async for token in ollama.generate_stream(
            prompt=full_prompt,
            model=model,
            system=_CODE_GEN_SYSTEM,
        ):
            yield token

    # ─────────────────────────────────────────────────────────────
    #  Agent planning
    # ─────────────────────────────────────────────────────────────
    async def plan_task(
        self,
        task: str,
        context: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Ask the AI to produce a step-by-step execution plan (JSON)."""
        model = model or settings.DEFAULT_MODEL

        prompt = f"Task: {task}"
        if context:
            prompt += f"\n\nAdditional context:\n{context}"

        return await ollama.generate(
            prompt=prompt,
            model=model,
            system=_AGENT_SYSTEM,
        )

    # ─────────────────────────────────────────────────────────────
    #  Utilities
    # ─────────────────────────────────────────────────────────────
    async def available_models(self) -> list[str]:
        return await ollama.list_models()

    def ollama_running(self) -> bool:
        return ollama.is_running()


# Module-level singleton
ai_service = AIService()
