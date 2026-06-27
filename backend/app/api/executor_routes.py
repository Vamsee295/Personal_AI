"""
api/executor_routes.py – POST /execute endpoint.

Flow:
  1. Receive {"command": "user natural-language instruction"}
  2. Build an engineered system prompt with few-shot examples that forces Ollama
     to always respond with a single valid JSON object.
  3. Parse the JSON from Ollama's raw text response.
  4. Pass the parsed dict to action_executor.execute_action().
  5. Return the executor result.
"""

from __future__ import annotations

import json
import re
import asyncio
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.ollama_client import ollama
from app.services.action_executor import execute_action
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("executor_routes")

router = APIRouter(prefix="/api", tags=["Action Executor"])

# ── Pydantic models ───────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    command: str
    model: Optional[str] = None   # override the default Ollama model if needed


class ExecuteResponse(BaseModel):
    command: str
    parsed_action: dict
    result: dict
    raw_llm_response: str


# ── System prompt (JSON-enforced, few-shot) ───────────────────────────────────

_EXECUTOR_SYSTEM_PROMPT = """\
You are an AI agent controller. Convert the user command into a single JSON action.

STRICT RULES:
- Respond with ONLY a valid JSON object. No prose, no markdown fences.
- NEVER guess. If the command is unclear or too short, return {"action": "none"}.
- If the command has fewer than 3 meaningful words, return {"action": "none"}.
- If user says "play" or "search" with youtube → use "search_youtube" and extract the query.

ACTIONS:
  open_app               → {"action":"open_app","target":"app_name"}
  open_url               → {"action":"open_url","target":"https://url"}
  search_youtube         → {"action":"search_youtube","query":"search term"}
  type_text              → {"action":"type_text","value":"text"}
  press_key              → {"action":"press_key","value":"ctrl+c"}
  take_screenshot        → {"action":"take_screenshot"}
  scroll                 → {"action":"scroll","value":"up|down"}
  send_whatsapp_message  → {"action":"send_whatsapp_message","target":"contact","value":"message"}
  none                   → {"action":"none"} (unclear command)

EXAMPLES:
Input: play varanasi teaser in youtube
Output: {"action":"search_youtube","query":"varanasi teaser"}

Input: open vs code
Output: {"action":"open_app","target":"vscode"}

Input: take a screenshot
Output: {"action":"take_screenshot"}

Input: open google
Output: {"action":"open_url","target":"https://www.google.com"}

Input: you
Output: {"action":"none"}

Input: hmm
Output: {"action":"none"}

{memory_context}
Command: """


def fallback_parser(command: str) -> dict | None:
    cmd = command.lower()
    if "youtube" in cmd and ("play" in cmd or "search" in cmd):
        query = cmd.replace("play", "").replace("search", "") \
                   .replace("on youtube", "").replace("in youtube", "") \
                   .replace("youtube", "").strip()
        return {"action": "search_youtube", "query": query}
    return None


def _extract_json(text: str) -> dict:
    """
    Try multiple strategies to extract a valid JSON object from raw LLM text.
    Raises ValueError if no valid JSON can be found.
    """
    text = text.strip()

    # Strategy 1: Direct parse (ideal path)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Strip markdown fences ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find first {...} block in the text
    brace_match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group())
        except json.JSONDecodeError:
            pass

    # Strategy 4: Find the largest {...} block (handles nested-ish responses)
    all_braces = re.findall(r"\{[\s\S]*?\}", text)
    for candidate in sorted(all_braces, key=len, reverse=True):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise ValueError(f"Could not extract valid JSON from LLM response:\n{text[:500]}")


# ── Route ─────────────────────────────────────────────────────────────────────

@router.post("/execute", response_model=ExecuteResponse)
async def execute_command(req: ExecuteRequest):
    """
    Accepts a natural language command, converts it to a JSON action via Ollama,
    executes it on the local machine, and saves the result to memory.
    """
    command = req.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="'command' must not be empty.")

    model = req.model or settings.DEFAULT_MODEL
    logger.info("POST /execute | model=%s | command=%r", model, command[:120])

    # ── Step 0: Build memory context to inject into system prompt ─────────────
    mem_context = ""
    try:
        from app.services.memory_manager import memory_manager as mem
        mem_context = str(await mem.search_memory())
    except Exception as mem_exc:
        logger.warning("Memory context build failed (non-fatal): %s", mem_exc)

    # ── Step 1: Call Ollama with the engineered system prompt ─────────────────
    system_prompt = _EXECUTOR_SYSTEM_PROMPT.replace("{memory_context}", mem_context)
    t_start = time.time()
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": command},
        ]
        raw_response: str = await ollama.chat(messages=messages, model=model)
        logger.info("Ollama raw response: %s", raw_response[:300])

    except Exception as exc:
        logger.error("Ollama call failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail=f"Ollama is unavailable or returned an error: {exc}",
        )

    # ── Step 2: Parse JSON from Ollama's response ─────────────────────────────
    try:
        action_dict = _extract_json(raw_response)
    except ValueError as exc:
        logger.error("JSON extraction failed: %s", exc)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "LLM did not return valid JSON.",
                "raw_response": raw_response[:1000],
                "hint": str(exc),
            },
        )

    # fallback if LLM gives wrong result
    if action_dict.get("action") == "open_url" and "youtube" in command.lower():
        fallback = fallback_parser(command)
        if fallback:
            action_dict.update(fallback)

    logger.info("Parsed action: %s", json.dumps(action_dict))

    # ── Safety: reject 'none' actions (LLM admitted it doesn't understand) ────
    if action_dict.get("action") == "none":
        logger.warning("LLM returned 'none' for command: %r — not executing", command)
        return ExecuteResponse(
            command=command,
            parsed_action=action_dict,
            result={"success": False, "action": "none", "message": "Command not understood."},
            raw_llm_response=raw_response,
        )

    # ── Step 3: Execute the action (in thread to avoid blocking event loop) ────
    result = await asyncio.to_thread(execute_action, action_dict)
    duration_ms = int((time.time() - t_start) * 1000)


    # ── Step 4: Save to memory (non-fatal) ───────────────────────────────────
    try:
        from app.services.memory_manager import memory_manager as mem
        import aiosqlite
        from app.database.db import DB_PATH
        result_str = result.get("message") or result.get("error") or str(result)

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO task_history (task, result) VALUES (?, ?)",
                (command, result_str)
            )
            await db.commit()
    except Exception as mem_exc:
        logger.warning("Memory save failed (non-fatal): %s", mem_exc)


    return ExecuteResponse(
        command=command,
        parsed_action=action_dict,
        result=result,
        raw_llm_response=raw_response,
    )


# ── Direct execute (skip LLM, for testing) ────────────────────────────────────

class DirectExecuteRequest(BaseModel):
    action: dict


@router.post("/execute/direct")
async def direct_execute(req: DirectExecuteRequest):
    """
    Bypass Ollama – pass a raw action dict directly to the executor.
    Useful for testing without needing a running LLM.

    Example body:
        {"action": {"action": "open_app", "target": "notepad", "value": "", "x": 0, "y": 0}}
    """
    result = await asyncio.to_thread(execute_action, req.action)
    return {"result": result}
