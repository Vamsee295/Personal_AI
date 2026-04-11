"""
voice/voice_output.py -- Offline Text-to-Speech engine using pyttsx3.

pyttsx3 uses Windows' built-in SAPI5 speech engine -- zero internet required,
zero latency from network calls. The engine is initialised ONCE at module level
as a singleton to avoid the overhead of re-initialising on every speak() call.

THREAD SAFETY NOTE: pyttsx3 is NOT thread-safe -- runAndWait() must always be
called from the SAME thread that called engine.say(). Use speak_async() to fire
TTS from background contexts without blocking the caller.

INSTALL:
    pip install pyttsx3
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Optional

logger = logging.getLogger("voice_output")

# ── Lazy-init globals ─────────────────────────────────────────────────────────
_engine    = None          # pyttsx3 engine singleton
_tts_lock  = threading.Lock()  # serialise speak() calls
_is_speaking = False

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

def init_tts():
    """
    Initialise and return the pyttsx3 TTS engine singleton.

    Sets up the first available English voice, a comfortable speech rate (175
    words per minute), and full volume. Called automatically on first use --
    do not call it manually unless you need to force a reset.

    Returns:
        pyttsx3.Engine, or None if pyttsx3 is not installed / SAPI5 error.
    """
    global _engine
    if _engine is not None:
        return _engine

    try:
        import pyttsx3

        engine = pyttsx3.init()

        # ── Voice selection -- prefer the first English voice ─────────────────
        voices = engine.getProperty("voices")
        english_voice = None
        for v in voices:
            # On Windows, English voices have "English" or "en" in their ID/name
            vid = (v.id or "").lower()
            if "english" in vid or "en_" in vid or "en-" in vid or "zira" in vid or "david" in vid:
                english_voice = v.id
                break

        if english_voice:
            engine.setProperty("voice", english_voice)
            logger.info("TTS voice selected: %s", english_voice)
        elif voices:
            # Fall back to first available voice
            engine.setProperty("voice", voices[0].id)
            logger.info("TTS voice (fallback): %s", voices[0].id)

        # ── Rate: 175 WPM -- slightly slower than default for clarity ──────────
        engine.setProperty("rate", 175)
        # ── Volume: full ───────────────────────────────────────────────────────
        engine.setProperty("volume", 1.0)

        _engine = engine
        logger.info("pyttsx3 TTS engine initialised.")
        return engine

    except ImportError:
        logger.error("pyttsx3 not installed. Run: pip install pyttsx3")
        return None
    except Exception as exc:
        logger.error("TTS init failed: %s", exc)
        return None


def _ensure_engine():
    """Return the engine, initialising it if needed."""
    global _engine
    if _engine is None:
        init_tts()
    return _engine


# =============================================================================
#  SPEAK
# =============================================================================

def speak(text: str) -> bool:
    """
    Speak text aloud via the pyttsx3 SAPI5 engine.

    Strips markdown formatting before speaking so code fences, asterisks, and
    heading symbols don't get read out. Serialised with a threading.Lock so
    only one speak() runs at a time (calling speak() while already speaking
    will wait for the current speech to finish).

    Args:
        text: The text to speak. May contain markdown -- it will be cleaned.

    Returns:
        True if speech completed, False on error or if engine unavailable.
    """
    global _is_speaking

    engine = _ensure_engine()
    if engine is None:
        logger.warning("TTS unavailable -- skipping speak().")
        return False

    clean = _strip_markdown(text)
    if not clean:
        return True

    try:
        with _tts_lock:
            _is_speaking = True
            logger.info("TTS speaking: %s", clean[:80])
            engine.say(clean)
            engine.runAndWait()
            _is_speaking = False
        return True
    except RuntimeError as exc:
        # pyttsx3 sometimes throws if the engine loop is already running
        logger.warning("TTS runtime error (engine busy?): %s", exc)
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
