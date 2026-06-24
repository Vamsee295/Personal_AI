"""
voice/voice_output.py -- Offline Text-to-Speech engine using Piper TTS.

Piper provides high-quality, fully local neural text-to-speech without cloud dependencies.
Models are downloaded automatically or loaded from a local cache.

INSTALL:
    pip install piper-tts
"""

from __future__ import annotations

import io
import os
import wave
import logging
import re
import threading
from typing import Optional
from pathlib import Path

logger = logging.getLogger("voice_output")

# ── Lazy-init globals ─────────────────────────────────────────────────────────
_piper_voice = None          # Piper Voice singleton
_tts_lock  = threading.Lock()  # serialise speak() calls
_is_speaking = False
_play_obj = None

PIPER_MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "piper"
PIPER_MODEL_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_MODEL = "en_US-lessac-medium" # Default high quality english voice

# ── Markdown / formatting stripper ───────────────────────────────────────────
_MD_PATTERN = re.compile(
    r"```[\s\S]*?```"       # code fences
    r"|`[^`]*`"             # inline code
    r"|\*{1,3}([^*]*)\*{1,3}"  # bold/italic
    r"|#{1,6}\s"            # headings
    r"|\[([^\]]*)\]\([^)]*\)"  # markdown links → keep label
    r"|~~([^~]*)~~"         # strikethrough
)


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting so spoken text sounds natural."""
    cleaned = _MD_PATTERN.sub(lambda m: m.group(1) or m.group(2) or m.group(3) or "", text)
    cleaned = re.sub(r"[_~]", "", cleaned)          # leftover underscores / tildes
    cleaned = re.sub(r"\s{2,}", " ", cleaned)       # collapse whitespace
    return cleaned.strip()


# =============================================================================
#  ENGINE INIT
# =============================================================================

def init_tts(model_name: str = DEFAULT_MODEL):
    """
    Initialise and return the Piper Voice singleton.
    Downloads the model if it's not present locally.
    """
    global _piper_voice
    if _piper_voice is not None:
        return _piper_voice

    try:
        from piper.voice import PiperVoice
        from piper.download import ensure_voice_exists, find_voice

        logger.info(f"Initialising Piper TTS with model: {model_name}")
        model_path, config_path = ensure_voice_exists(
            model_name,
            [str(PIPER_MODEL_DIR)],
            str(PIPER_MODEL_DIR)
        )

        _piper_voice = PiperVoice(load_model=model_path, config_path=config_path)
        logger.info("Piper TTS engine initialised successfully.")
        return _piper_voice

    except ImportError:
        logger.error("piper-tts not installed. Run: pip install piper-tts")
        return None
    except Exception as exc:
        logger.error("Piper TTS init failed: %s", exc)
        return None

def _ensure_engine():
    """Return the piper voice, initialising it if needed."""
    global _piper_voice
    if _piper_voice is None:
        init_tts()
    return _piper_voice


# =============================================================================
#  SPEAK
# =============================================================================

def speak(text: str) -> bool:
    """
    Speak text aloud via the Piper TTS engine.
    """
    global _is_speaking, _play_obj

    piper = _ensure_engine()
    if piper is None:
        logger.warning("Piper TTS unavailable -- skipping speak().")
        return False

    clean = _strip_markdown(text)
    if not clean:
        return True

    try:
        import simpleaudio as sa
        with _tts_lock:
            _is_speaking = True
            logger.info("TTS speaking: %s", clean[:80])

            # Synthesize audio to memory
            wav_io = io.BytesIO()
            with wave.open(wav_io, "wb") as wav_file:
                piper.synthesize(clean, wav_file)

            # Play audio
            wav_io.seek(0)
            wave_read = wave.open(wav_io, "rb")
            audio_data = wave_read.readframes(wave_read.getnframes())

            _play_obj = sa.play_buffer(audio_data, wave_read.getnchannels(), wave_read.getsampwidth(), wave_read.getframerate())
            _play_obj.wait_done()
            _is_speaking = False
            _play_obj = None
        return True
    except ImportError:
        logger.error("simpleaudio not installed. Run: pip install simpleaudio")
        _is_speaking = False
        return False
    except Exception as exc:
        logger.error("TTS speak() error: %s", exc)
        _is_speaking = False
        return False


def speak_async(text: str) -> threading.Thread:
    """
    Speak text in a background thread so the caller isn't blocked.

    Useful when calling from async FastAPI handlers or background loops.
    The thread is daemonised so it won't prevent program exit.

    Returns:
        The Thread object (already started).
    """
    t = threading.Thread(target=speak, args=(text,), daemon=True, name="TTS-thread")
    t.start()
    return t


# =============================================================================
#  CONTROL
# =============================================================================

def set_voice_speed(rate: int) -> None:
    """
    Change the TTS speech rate dynamically.

    Args:
        rate: Words per minute.
              100 = slow and clear
              175 = normal (default)
              250 = fast
    """
    engine = _ensure_engine()
    if engine:
        engine.setProperty("rate", max(80, min(rate, 300)))
        logger.info("TTS rate set to %d", rate)


def set_voice(gender: str = "male") -> bool:
    """
    Switch between available Windows SAPI5 voices by gender keyword.

    Searches voice names/IDs for the gender string (case-insensitive).
    Common options: "male", "female", "david", "zira", "hazel".

    Returns:
        True if a matching voice was found and set.
    """
    engine = _ensure_engine()
    if not engine:
        return False

    try:
        voices = engine.getProperty("voices")
        target = gender.lower()
        for v in voices:
            name = (v.name or "").lower()
            vid  = (v.id or "").lower()
            if target in name or target in vid:
                engine.setProperty("voice", v.id)
                logger.info("TTS voice changed to: %s", v.name)
                return True
        logger.warning("No voice found matching: %s", gender)
        return False
    except Exception as exc:
        logger.error("set_voice error: %s", exc)
        return False


def stop_speaking() -> None:
    """Stop current speech immediately."""
    global _is_speaking
    engine = _ensure_engine()
    if engine:
        try:
            engine.stop()
            _is_speaking = False
            logger.info("TTS stopped.")
        except Exception as exc:
            logger.warning("TTS stop() error: %s", exc)


def get_available_voices() -> list[dict]:
    """Return a list of available TTS voices for the frontend selector."""
    engine = _ensure_engine()
    if not engine:
        return []
    try:
        voices = engine.getProperty("voices")
        return [
            {"id": v.id, "name": v.name or v.id, "languages": getattr(v, "languages", [])}
            for v in voices
        ]
    except Exception:
        return []


def is_speaking() -> bool:
    """Return True if TTS is currently active."""
    return _is_speaking
