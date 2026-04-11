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
You are an AI agent that converts natural language instructions into structured JSON commands for a Windows automation system. 

CRITICAL RULES:
1. You MUST respond with ONLY a single valid JSON object — no prose, no markdown, no ```json fences.
2. The JSON must have exactly these keys:
   - "action"  : one of [open_app, type_text, press_key, mouse_click, take_screenshot, move_mouse, scroll, send_whatsapp_message, read_whatsapp]
   - "target"  : the app name, text to type, key name, contact name, or direction (string)
   - "value"   : extra detail such as button type, key combo, scroll amount, message text, or count (string)
   - "x"       : screen x-coordinate as integer (0 if not applicable)
   - "y"       : screen y-coordinate as integer (0 if not applicable)
3. Do NOT add any extra keys or explanatory text outside the JSON.

ACTION REFERENCE:
  open_app               → opens an application; target = app name (e.g. "notepad", "chrome", "calculator")
  type_text              → types text on keyboard; value = text to type
  press_key              → presses key/combo; value = "ctrl+c", "alt+tab", "win+d", "enter", "f5"
  mouse_click            → clicks at coordinates; x,y = pixel coords; value = "left"/"right"/"middle"
  take_screenshot        → captures the screen; no additional fields needed
  move_mouse             → moves mouse to x,y; value = duration in seconds (e.g. "0.4")
  scroll                 → scrolls; value = "up", "down", or integer (positive=up, negative=down)
  send_whatsapp_message  → sends a WhatsApp message; target = contact name, value = message text
  read_whatsapp          → reads recent messages; target = contact name, value = count (e.g. "5")

FEW-SHOT EXAMPLES (input → JSON output):

User: "Open Notepad"
{"action": "open_app", "target": "notepad", "value": "", "x": 0, "y": 0}

User: "Type Hello World"
{"action": "type_text", "target": "", "value": "Hello World", "x": 0, "y": 0}

User: "Press Ctrl+C"
{"action": "press_key", "target": "", "value": "ctrl+c", "x": 0, "y": 0}

User: "Click at the top-left corner"
{"action": "mouse_click", "target": "", "value": "left", "x": 10, "y": 10}

User: "Take a screenshot"
{"action": "take_screenshot", "target": "", "value": "", "x": 0, "y": 0}

User: "Move the mouse to the center of the screen"
{"action": "move_mouse", "target": "", "value": "0.5", "x": 960, "y": 540}

User: "Scroll down on the page"
{"action": "scroll", "target": "", "value": "down", "x": 0, "y": 0}

User: "Open Google Chrome"
{"action": "open_app", "target": "chrome", "value": "", "x": 0, "y": 0}

User: "Open calculator"
{"action": "open_app", "target": "calculator", "value": "", "x": 0, "y": 0}

User: "Show the desktop"
{"action": "press_key", "target": "", "value": "win+d", "x": 0, "y": 0}

User: "Send good morning to Ravi on WhatsApp"
{"action": "send_whatsapp_message", "target": "Ravi", "value": "Good morning!", "x": 0, "y": 0}

{memory_context}
Now respond to the user's instruction below with ONLY the JSON object:
"""


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
        from memory.memory_manager import memory as mem
        mem_context = mem.build_memory_context(command)
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

    logger.info("Parsed action: %s", json.dumps(action_dict))

    # ── Step 3: Execute the action (in thread to avoid blocking event loop) ────
    result = await asyncio.to_thread(execute_action, action_dict)
    duration_ms = int((time.time() - t_start) * 1000)

    # ── Step 4: Save to memory (non-fatal) ───────────────────────────────────
    try:
        from memory.memory_manager import memory as mem
        result_str = result.get("message") or result.get("error") or str(result)
        mem.save_command(
            user_input=command,
            action_taken=action_dict,
            result=result_str,
            success=bool(result.get("success", False)),
            duration_ms=duration_ms,
        )
        mem.extract_and_save_preferences(command, action_dict)
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
