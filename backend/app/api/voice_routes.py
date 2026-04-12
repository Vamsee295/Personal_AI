"""
api/voice_routes.py - Voice pipeline with validation + rule-based parser

LAYERS:
  1. /api/voice/stt   → Accept audio blob → Faster-Whisper transcription → validate garbage
  2. /api/voice/execute → text → rule_based_parser → LLM fallback → execute → spoken response
"""

from __future__ import annotations

import re
import tempfile
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.utils.logger import get_logger

logger = get_logger("voice_routes")

router = APIRouter(prefix="/api/voice", tags=["Voice Assistant"])


# ── GARBAGE FILTER ──────────────────────────────────────────────────────────────
# Words that Whisper commonly hallucinates on silence/background noise

_GARBAGE_WORDS = {
    "you", "uh", "um", "hmm", "hm", "ah", "oh", "okay",
    "thanks", "thank", "bye", "goodbye", ".", ",", "...", "the",
    "a", "i", "is", "it", "and", "or", "but",
}

def _is_valid_transcription(text: str) -> bool:
    """Return True only if the transcription is a meaningful command."""
    if not text or len(text.strip()) < 4:
        return False
    words = text.strip().lower().split()
    # Reject if EVERY word is in the garbage list
    if all(w.strip(".,!?") in _GARBAGE_WORDS for w in words):
        logger.warning("Rejected garbage transcription: %r", text)
        return False
    return True


# ── RULE-BASED PARSER (runs BEFORE LLM) ─────────────────────────────────────────
# Handles the most common commands instantly, no LLM hallucination possible

def rule_based_parser(cmd: str) -> dict | None:
    """
    Fast, deterministic intent parser.
    Returns action dict if matched, None to fall through to LLM.
    """
    c = cmd.lower().strip()

    # ── YouTube ──────────────────────────────────────────────────────────────────
    if "youtube" in c:
        if any(w in c for w in ("play", "search", "find", "watch")):
            query = re.sub(
                r'\b(play|search|find|watch|on|in|at|the|a|youtube|for|me)\b',
                '', c, flags=re.IGNORECASE
            ).strip(" ,.-")
            if query:
                return {"action": "search_youtube", "query": query}
        return {"action": "open_url", "target": "https://youtube.com"}

    # ── VS Code ───────────────────────────────────────────────────────────────────
    if any(p in c for p in ("vs code", "vscode", "visual studio code", "open code")):
        return {"action": "open_app", "target": "vscode"}

    # ── Screenshot ────────────────────────────────────────────────────────────────
    if any(p in c for p in ("screenshot", "capture screen", "take a screenshot")):
        return {"action": "take_screenshot", "target": "", "value": "", "x": 0, "y": 0}

    # ── Google Search ─────────────────────────────────────────────────────────────
    if "google" in c and any(w in c for w in ("search", "find", "look up")):
        query = re.sub(r'\b(google|search|find|look up|for|a|the|me)\b', '', c).strip()
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        return {"action": "open_url", "target": url}

    # ── Common apps ───────────────────────────────────────────────────────────────
    for keyword, target in [
        ("calculator", "calculator"),
        ("notepad",    "notepad"),
        ("spotify",    "spotify"),
        ("discord",    "discord"),
        ("chrome",     "chrome"),
        ("brave",      "brave"),
        ("terminal",   "terminal"),
        ("cmd",        "cmd"),
    ]:
        if keyword in c:
            return {"action": "open_app", "target": target}

    # ── Show desktop ──────────────────────────────────────────────────────────────
    if "desktop" in c or "minimise all" in c or "minimize all" in c:
        return {"action": "press_key", "target": "", "value": "win+d", "x": 0, "y": 0}

    # ── Scroll ────────────────────────────────────────────────────────────────────
    if "scroll down" in c:
        return {"action": "scroll", "target": "", "value": "down", "x": 0, "y": 0}
    if "scroll up" in c:
        return {"action": "scroll", "target": "", "value": "up", "x": 0, "y": 0}

    return None  # → fall through to LLM


# ── STT: Accept audio blob from browser ─────────────────────────────────────────

@router.post("/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """
    Accepts audio (WebM) recorded by the browser.
    Returns transcribed text after garbage filtering.
    """
    try:
        from faster_whisper import WhisperModel

        audio_bytes = await audio.read()
        logger.info("Audio received: %d bytes", len(audio_bytes))

        if len(audio_bytes) < 5000:
            return {"text": "", "success": False, "message": "Audio too short — please hold the mic button while speaking."}

        suffix = ".webm" if "webm" in (audio.content_type or "") else ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            model = WhisperModel("base.en", device="cpu", compute_type="int8")
            segments, info = model.transcribe(
                tmp_path,
                beam_size=5,
                language="en",
                vad_filter=False,             # 🔥 Disabled VAD: prevent premature cutting
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
        finally:
            os.unlink(tmp_path)

        logger.info("Raw Whisper output: %r", text)

        if not text or not _is_valid_transcription(text):
            logger.warning("Rejected transcription: %r", text)
            return {
                "text": "", "success": False,
                "message": f"Didn't catch a valid command (got: '{text}'). Please speak clearly."
            }

        logger.info("Valid transcription: %r", text)
        return {"text": text, "success": True}

    except ImportError:
        raise HTTPException(status_code=503, detail="faster-whisper not installed.")
    except Exception as exc:
        logger.exception("STT error")
        raise HTTPException(status_code=500, detail=str(exc))


# ── EXECUTE: text → rule_parser → LLM fallback → action ─────────────────────────

class VoiceExecuteRequest(BaseModel):
    command: str
    model: Optional[str] = None


@router.post("/execute")
async def voice_execute(req: VoiceExecuteRequest):
    """
    Runs the command through:
      1. Rule-based parser (instant, no hallucination)
      2. LLM executor (fallback for complex commands)
    Returns result + a natural spoken_response.
    """
    command = req.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="Command cannot be empty")

    logger.info("Voice execute: %r", command)

    # ── Layer 1: Rule-based parser ─────────────────────────────────────────────
    rule_action = rule_based_parser(command)
    if rule_action:
        logger.info("Rule matched: %s", rule_action)
        import asyncio
        from app.services.action_executor import execute_action
        result = await asyncio.to_thread(execute_action, rule_action)
        spoken = _make_spoken_response(rule_action.get("action", ""), rule_action, result.get("message", "Done."))
        return {
            "command": command,
            "action": rule_action,
            "result": result,
            "spoken_response": spoken,
            "success": result.get("success", False),
            "source": "rule",
        }

    # ── Layer 2: LLM executor fallback ────────────────────────────────────────
    try:
        from app.api.executor_routes import execute_command, ExecuteRequest
        exec_req = ExecuteRequest(command=command, model=req.model)
        exec_res = await execute_command(exec_req)

        result = exec_res.result
        action = exec_res.parsed_action.get("action", "")

        # Reject "none" actions (LLM admitted it doesn't understand)
        if action == "none":
            return {
                "command": command, "action": exec_res.parsed_action,
                "result": {"success": False},
                "spoken_response": "I didn't understand that command. Please try again.",
                "success": False,
                "source": "llm_rejected",
            }

        spoken = _make_spoken_response(action, exec_res.parsed_action, result.get("message", "Done."))
        return {
            "command": command,
            "action": exec_res.parsed_action,
            "result": result,
            "spoken_response": spoken,
            "success": result.get("success", False),
            "source": "llm",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Voice execute error")
        raise HTTPException(status_code=500, detail=str(exc))


def _make_spoken_response(action: str, parsed: dict, fallback: str) -> str:
    t = parsed.get("target", "")
    q = parsed.get("query",  "")
    v = parsed.get("value",  "")
    return {
        "open_app":              f"Opening {t}.",
        "open_url":              f"Opening {t}.",
        "search_youtube":        f"Searching YouTube for {q}.",
        "type_text":             "Text typed.",
        "press_key":             f"Pressed {v}.",
        "take_screenshot":       "Screenshot saved.",
        "scroll":                f"Scrolled {v}.",
        "send_whatsapp_message": f"Sending message to {t} on WhatsApp.",
        "read_whatsapp":         f"Reading messages from {t}.",
        "none":                  "Command not understood.",
    }.get(action, fallback)
