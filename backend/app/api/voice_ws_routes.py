"""
api/voice_ws_routes.py -- WebSocket + REST endpoints for the voice system.

WebSocket  ws://localhost:8000/voice/ws
  → {"action": "start_listening"}  → listen, transcribe, execute, respond
  → {"action": "start_wake_mode"}  → enable background wake word listener
  → {"action": "stop"}             → stop everything

POST /voice/speak          body: {"text": "..."} → speak aloud via TTS
POST /voice/transcribe     file upload           → WAV/MP3 → text
GET  /voice/status         → is_active, model loaded, TTS ready
GET  /voice/voices         → list available TTS voices
POST /voice/settings       → update rate, volume, voice
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

logger = logging.getLogger("voice_ws_routes")

router = APIRouter(prefix="/voice", tags=["Voice (Whisper+TTS)"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class SpeakRequest(BaseModel):
    text: str
    async_mode: bool = True   # if True, don't block the HTTP response


class VoiceSettingsRequest(BaseModel):
    rate:   Optional[int]   = None   # 100 = slow, 175 = normal, 250 = fast
    volume: Optional[float] = None   # 0.0 – 1.0
    gender: Optional[str]   = None   # "male" / "female" / voice ID


# =============================================================================
#  WEBSOCKET  ws://localhost:8000/voice/ws
# =============================================================================

@router.websocket("/ws")
async def voice_websocket(ws: WebSocket):
    """
    WebSocket handler for the frontend mic button.

    Protocol:
        Client → {"action": "start_listening", "duration": 6}
        Server → {"status": "listening"}
        Server → {"status": "transcribed", "text": "open chrome"}
        Server → {"status": "executing", "action": {...}}
        Server → {"status": "done", "result": {...}, "spoken": "Done, I opened..."}

        Client → {"action": "start_wake_mode"}
        Server → {"status": "wake_mode_on"}

        Client → {"action": "stop"}
        Server → {"status": "stopped"}
    """
    await ws.accept()
    logger.info("Voice WebSocket connected.")
    await ws.send_json({"status": "ready", "message": "Voice agent connected."})

    agent = None

    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action", "")

            # ── SINGLE LISTEN SESSION ─────────────────────────────────────────
            if action == "start_listening":
                duration = float(data.get("duration", 6.0))
                await ws.send_json({"status": "listening", "duration": duration})

                # Run blocking listen+execute in thread pool
                try:
                    from voice.voice_agent import VoiceAgent
                    agent = VoiceAgent.get_instance()

                    result = await asyncio.to_thread(agent.listen_once, duration)

                    await ws.send_json({
                        "status":      "done",
                        "success":     result.get("success", False),
                        "transcribed": result.get("transcribed", ""),
                        "action_taken": result.get("action", {}),
                        "result":      result.get("result", {}),
                        "spoken":      result.get("spoken_response", ""),
                    })
                except Exception as exc:
                    logger.error("WebSocket listen error: %s", exc)
                    await ws.send_json({"status": "error", "message": str(exc)})

            # ── WAKE WORD MODE ────────────────────────────────────────────────
            elif action == "start_wake_mode":
                try:
                    from voice.voice_agent import VoiceAgent
                    agent = VoiceAgent.get_instance()
                    await asyncio.to_thread(agent.start)
                    await ws.send_json({"status": "wake_mode_on",
                                        "message": "Say 'Hey Vamsee' to activate."})
                except Exception as exc:
                    await ws.send_json({"status": "error", "message": str(exc)})

            # ── STOP ──────────────────────────────────────────────────────────
            elif action == "stop":
                if agent:
                    await asyncio.to_thread(agent.stop)
                await ws.send_json({"status": "stopped"})
                break

            else:
                await ws.send_json({"status": "error", "message": f"Unknown action: {action}"})

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected.")
    except Exception as exc:
        logger.error("Voice WebSocket error: %s", exc)
    finally:
        if agent:
            try:
                await asyncio.to_thread(agent.stop)
            except Exception:
                pass


# =============================================================================
#  REST ENDPOINTS
# =============================================================================

@router.post("/speak")
async def speak_text(req: SpeakRequest):
    """
    Speak any text aloud via the pyttsx3 engine.
    Useful for testing TTS or reading log entries aloud from the UI.
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="'text' must not be empty.")
    try:
        from voice.voice_output import speak_async, speak
        if req.async_mode:
            t = speak_async(req.text)
            return {"success": True, "spoken": True, "async": True,
                    "thread": t.name}
        else:
            ok = await asyncio.to_thread(speak, req.text)
            return {"success": True, "spoken": ok, "async": False}
    except Exception as exc:
        logger.error("POST /voice/speak error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/transcribe")
async def transcribe_upload(file: UploadFile = File(...)):
    """
    Accept a WAV or MP3 audio file upload and transcribe it with faster-whisper.

    Returns:
        {"text": "transcribed words", "success": true}
    """
    try:
        audio_bytes = await file.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file.")

        from voice.voice_input import transcribe_audio
        text = await asyncio.to_thread(transcribe_audio, audio_bytes)

        return {
            "success": True,
            "text": text,
            "filename": file.filename,
            "bytes": len(audio_bytes),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("POST /voice/transcribe error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/status")
async def voice_status():
    """Return current voice system status."""
    try:
        from voice.voice_input import _whisper_model, _listening, _model_size
        from voice.voice_output import _engine, is_speaking

        return {
            "whisper_loaded":    _whisper_model is not None,
            "whisper_model":     _model_size,
            "wake_word_active":  _listening,
            "tts_ready":         _engine is not None,
            "tts_speaking":      is_speaking(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/voices")
async def list_voices():
    """Return all available TTS voices from Windows SAPI5."""
    try:
        from voice.voice_output import get_available_voices
        voices = await asyncio.to_thread(get_available_voices)
        return {"voices": voices, "count": len(voices)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/settings")
async def update_voice_settings(req: VoiceSettingsRequest):
    """Dynamically update TTS speed, volume, or voice selection."""
    try:
        from voice.voice_output import set_voice_speed, set_voice, _ensure_engine
        engine = _ensure_engine()
        changed = {}

        if req.rate is not None:
            set_voice_speed(req.rate)
            changed["rate"] = req.rate

        if req.volume is not None and engine:
            vol = max(0.0, min(float(req.volume), 1.0))
            engine.setProperty("volume", vol)
            changed["volume"] = vol

        if req.gender is not None:
            ok = await asyncio.to_thread(set_voice, req.gender)
            changed["voice_set"] = ok

        return {"success": True, "changed": changed}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
