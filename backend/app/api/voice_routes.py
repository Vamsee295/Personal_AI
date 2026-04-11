"""
api/voice_routes.py – REST endpoints for the voice assistant.

Endpoints:
  POST /api/voice/listen    – record mic → return transcribed text
  POST /api/voice/respond   – text → AI → TTS
  POST /api/voice/pipeline  – full pipeline: listen → AI → speak
"""

from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.ai_service import ai_service
from app.agents.voice_agent import voice_agent
from app.utils.logger import get_logger

logger = get_logger("voice_routes")

router = APIRouter(prefix="/api/voice", tags=["Voice Assistant"])

_VOICE_SYSTEM = (
    "You are Ultron, a helpful local voice assistant. "
    "Respond in 1-3 short sentences, conversationally and naturally. "
    "If a command involves the computer (open VS Code, organise files, etc.) say you will do it."
)


class VoiceRespondRequest(BaseModel):
    command: str
    model: Optional[str] = "qwen2.5-coder:7b"
    speak: bool = True   # if True, TTS is triggered on backend


# ── Listen (STT) ──────────────────────────────────────────────────
@router.post("/listen")
async def listen():
    """
    Records from the default microphone for up to 5 seconds.
    Returns the transcribed text.
    """
    try:
        text = voice_agent.listen(timeout=5, phrase_limit=10)
        if not text:
            return {"text": "", "success": False, "message": "No speech detected"}
        return {"text": text, "success": True}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Voice listen error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Respond (AI + TTS) ────────────────────────────────────────────
@router.post("/respond")
async def respond(req: VoiceRespondRequest):
    """
    Takes a text command, sends it to the AI, and optionally speaks the reply.
    """
    try:
        # AI response with a short, voice-friendly system prompt
        from app.models.schemas import ChatMessage
        ai_response = await ai_service.chat(
            message=req.command,
            history=[ChatMessage(role="system", content=_VOICE_SYSTEM)],
            model=req.model,
        )

        spoken = False
        if req.speak:
            try:
                voice_agent.speak(ai_response)
                spoken = True
            except Exception as tts_exc:
                logger.warning("TTS failed: %s", tts_exc)

        return {
            "command": req.command,
            "ai_response": ai_response,
            "spoken": spoken,
            "success": True,
        }
    except Exception as exc:
        logger.error("Voice respond error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Full pipeline ─────────────────────────────────────────────────
@router.post("/pipeline")
async def voice_pipeline():
    """
    Full voice pipeline: listen → AI → speak.
    """
    try:
        # 1. Listen
        text = voice_agent.listen(timeout=6, phrase_limit=12)
        if not text:
            return {"command": "", "ai_response": "", "spoken": False, "success": False,
                    "message": "No speech detected"}

        # 2. AI
        from app.models.schemas import ChatMessage
        ai_response = await ai_service.chat(
            message=text,
            history=[ChatMessage(role="system", content=_VOICE_SYSTEM)],
        )

        # 3. TTS
        spoken = False
        try:
            voice_agent.speak(ai_response)
            spoken = True
        except Exception as tts_exc:
            logger.warning("TTS failed: %s", tts_exc)

        return {
            "command": text,
            "ai_response": ai_response,
            "spoken": spoken,
            "success": True,
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Voice pipeline error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
