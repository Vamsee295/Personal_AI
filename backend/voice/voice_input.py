"""
voice/voice_input.py -- Offline Speech-to-Text using faster-whisper.

Pipeline:
  pyaudio (mic) → raw PCM bytes → faster-whisper (local CPU) → text string

faster-whisper is a highly optimised reimplementation of OpenAI Whisper using
CTranslate2. On a Ryzen 7 6800H with the "base" model it transcribes a 5-second
clip in ~0.5 seconds -- entirely offline, no API key needed.

MODEL SIZES (accuracy vs speed trade-off):
    tiny   -- fastest, ~1GB RAM, good enough for simple commands
    base   -- best balance for commands, ~1.5GB RAM  ← default
    small  -- more accurate, ~2.5GB RAM
    medium -- near-perfect, ~5GB RAM (may be slow on CPU)

First run downloads the model to ~/.cache/huggingface/hub/ (~150MB for base).
Subsequent runs load from cache instantly.

INSTALL:
    pip install faster-whisper pyaudio
    # If pyaudio fails on Windows:
    pip install pipwin && pipwin install pyaudio

WAKE WORDS (no extra library -- we just transcribe short chunks and check):
    "hey vamsee", "vamsee", "hey agent", "wake up", "computer"
"""

from __future__ import annotations

import io
import logging
import struct
import threading
import time
import wave
from typing import Callable, List, Optional

logger = logging.getLogger("voice_input")

# ── Module-level state ────────────────────────────────────────────────────────
_whisper_model   = None          # faster-whisper WhisperModel singleton
_model_size      = "base"        # default Whisper model
_listening       = False         # flag for continuous_listen / wake word loops
_listener_thread: Optional[threading.Thread] = None

# ── Audio constants ───────────────────────────────────────────────────────────
_SAMPLE_RATE   = 16_000   # 16 kHz -- Whisper requirement
_CHANNELS      = 1        # mono
_SAMPLE_WIDTH  = 2        # 16-bit PCM (2 bytes per sample)
_CHUNK_SIZE    = 1024     # pyaudio chunk size

# ── Default wake words ────────────────────────────────────────────────────────
DEFAULT_WAKE_WORDS: List[str] = [
    "hey jarvis",
    "jarvis",
    "hello jarvis",
    "hey agent",
    "wake up jarvis",
    "computer",
]


# =============================================================================
#  WHISPER INIT (lazy / singleton)
# =============================================================================

def _load_whisper(model_size: str = "base"):
    """
    Load the faster-whisper model, downloading it on first run.

    Uses a module-level singleton to avoid reloading on every transcription.
    Loads on CPU (device="cpu") for compatibility -- the Ryzen 7 6800H handles
    "base" model comfortably. Set compute_type="int8" for lowest RAM usage.

    Returns:
        WhisperModel instance, or None if faster-whisper is not installed.
    """
    global _whisper_model, _model_size

    if _whisper_model is not None and _model_size == model_size:
        return _whisper_model

    try:
        from faster_whisper import WhisperModel

        logger.info("Loading faster-whisper model: %s (first run may download ~150MB)", model_size)
        print(f"[VoiceInput] Loading Whisper model '{model_size}'... (first run downloads ~150MB)")

        _whisper_model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",   # fastest on CPU, minimal RAM
        )
        _model_size = model_size
        logger.info("faster-whisper model '%s' ready.", model_size)
        print("[VoiceInput] Whisper model ready.")
        return _whisper_model

    except ImportError:
        logger.error(
            "faster-whisper not installed. Run: pip install faster-whisper"
        )
        return None
    except Exception as exc:
        logger.error("Failed to load Whisper model '%s': %s", model_size, exc)
        return None


# =============================================================================
#  RECORDING
# =============================================================================

def record_audio(duration: float = 5.0, sample_rate: int = _SAMPLE_RATE) -> Optional[bytes]:
    """
    Record audio with multi-layer fallback logic for Windows hardware errors.
    
    1. Tries default device at 16kHz
    2. Tries Microsoft Sound Mapper (ID 0) fallback
    3. Tries alternate sample rates (44.1kHz, 48kHz)
    """
    try:
        import pyaudio
    except ImportError:
        logger.error("pyaudio not installed.")
        return None

    pa = pyaudio.PyAudio()
    stream = None
    
    # Negotiation parameters
    rates_to_try = [sample_rate, 44100, 48000]
    # We found ID 0 is often Sound Mapper which is more resilient
    devices_to_try = [None, 0] # None = default
    
    success = False
    actual_rate = sample_rate

    for dev_idx in devices_to_try:
        if success: break
        for rate in rates_to_try:
            try:
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=_CHANNELS,
                    rate=rate,
                    input=True,
                    input_device_index=dev_idx,
                    frames_per_buffer=_CHUNK_SIZE,
                )
                actual_rate = rate
                success = True
                if dev_idx is not None or rate != sample_rate:
                    logger.info("Recording fallback success: Device=%s, Rate=%d", dev_idx, rate)
                break
            except Exception:
                # logger.debug("Failed opening mic (dev=%s, rate=%d): %s", dev_idx, rate, e)
                continue

    if not success:
        logger.error("All audio input attempts failed (including fallbacks). Check mic privacy settings.")
        pa.terminate()
        return None

    try:
        print(f"[VoiceInput] Listening ({actual_rate}Hz)...", flush=True)
        frames = []
        num_chunks = int(actual_rate / _CHUNK_SIZE * duration)
        for _ in range(num_chunks):
            data = stream.read(_CHUNK_SIZE, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        pa.terminate()

        # Pack into WAV
        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(_SAMPLE_WIDTH)
            wf.setframerate(actual_rate)
            wf.writeframes(b"".join(frames))
        return wav_buf.getvalue()

    except Exception as exc:
        logger.error("Recording runtime error: %s", exc)
        if stream: stream.close()
        pa.terminate()
        return None

    except Exception as exc:
        logger.error("record_audio error: %s", exc)
        print(f"[VoiceInput] Recording error: {exc}")
        if stream is not None:
            try:
                stream.stop_stream()
                stream.close()
            except Exception:
                pass
        if pa is not None:
            try:
                pa.terminate()
            except Exception:
                pass
        return None


def _audio_energy(raw_frames: bytes) -> float:
    """
    Compute RMS energy of raw 16-bit PCM samples.
    Used to detect whether the user is actually speaking.
    """
    if not raw_frames:
        return 0.0
    count = len(raw_frames) // 2
    if count == 0:
        return 0.0
    try:
        samples = struct.unpack(f"{count}h", raw_frames[:count * 2])
        rms = (sum(s ** 2 for s in samples) / count) ** 0.5
        return rms
    except Exception:
        return 0.0


# =============================================================================
#  TRANSCRIPTION
# =============================================================================

def transcribe_audio(audio_bytes: bytes, model_size: str = "base") -> str:
    """
    Transcribe WAV audio bytes to text using faster-whisper (100% offline).

    The Whisper model is loaded once and cached as a module-level singleton.
    Subsequent calls reuse the loaded model for speed.

    Args:
        audio_bytes : WAV-format bytes (as returned by record_audio()).
        model_size  : Whisper model size ("tiny", "base", "small", "medium").

    Returns:
        Transcribed text string. Returns "" on silence, error, or empty audio.
    """
    if not audio_bytes:
        return ""

    model = _load_whisper(model_size)
    if model is None:
        logger.warning("Whisper model unavailable -- cannot transcribe.")
        return ""

    try:
        # faster-whisper accepts a file-like object (BytesIO)
        audio_io = io.BytesIO(audio_bytes)
        segments, _info = model.transcribe(
            audio_io,
            language="en",         # English only -- faster
            vad_filter=True,       # skip silent chunks automatically
            vad_parameters={
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 300,
            },
        )

        # Collect all segment texts
        parts = [seg.text.strip() for seg in segments if seg.text.strip()]
        result = " ".join(parts).strip()

        if result:
            logger.info("Transcribed: %s", result[:100])
        else:
            logger.debug("Transcription returned empty (silence or no speech).")

        return result

    except Exception as exc:
        logger.error("transcribe_audio error: %s", exc)
        return ""


def listen_and_transcribe(duration: float = 5.0, model_size: str = "base") -> str:
    """
    Convenience: record audio then transcribe it in one call.

    Args:
        duration   : How many seconds to record.
        model_size : Whisper model to use.

    Returns:
        Transcribed text, or "" if nothing was heard / error.
    """
    audio = record_audio(duration)
    if not audio:
        return ""
    return transcribe_audio(audio, model_size)


# =============================================================================
#  WAKE WORD
# =============================================================================

def detect_wake_word(
    transcribed_chunk: str,
    wake_words: List[str] = DEFAULT_WAKE_WORDS,
) -> bool:
    """
    Check if a transcribed audio chunk contains a wake word.

    Uses simple case-insensitive substring matching -- no extra library needed.
    Transcribe a short (2-3 second) audio chunk and pass the result here.

    Args:
        transcribed_chunk : Text from a recent Whisper transcription.
        wake_words        : List of wake phrases to listen for.

    Returns:
        True if any wake word is found in the chunk.
    """
    lower = transcribed_chunk.lower().strip()
    for word in wake_words:
        if word.lower() in lower:
            logger.info("Wake word detected: '%s' in '%s'", word, lower[:60])
            return True
    return False


# =============================================================================
#  CONTINUOUS + WAKE WORD LISTENERS
# =============================================================================

def continuous_listen(
    callback: Callable[[str], None],
    silence_threshold: float = 500.0,
    chunk_duration: float = 3.0,
    model_size: str = "base",
) -> None:
    """
    Run a continuous listen loop in the current thread.

    Repeatedly records `chunk_duration`-second audio chunks, checks the energy
    level to skip silent chunks (saving CPU), transcribes active chunks with
    Whisper, and calls `callback(text)` whenever real speech is detected.

    This function BLOCKS -- call it from a background thread:
        t = threading.Thread(target=continuous_listen, args=(my_callback,), daemon=True)
        t.start()

    Stops when stop_listening() is called (sets _listening=False).

    Args:
        callback          : Called with transcribed text for each non-silent chunk.
        silence_threshold : RMS energy below this is treated as silence (skipped).
        chunk_duration    : Audio chunk length in seconds.
        model_size        : Whisper model size.
    """
    global _listening
    _listening = True
    logger.info("Continuous listen loop started (chunk=%.1fs, threshold=%.0f).", chunk_duration, silence_threshold)

    while _listening:
        try:
            import pyaudio

            pa = pyaudio.PyAudio()
            stream = None
            
            # Negotiation for continuous loop
            success = False
            actual_rate = _SAMPLE_RATE
            for dev_idx in [None, 0]:
                if success: break
                for forrate in [_SAMPLE_RATE, 44100]:
                    try:
                        stream = pa.open(
                            format=pyaudio.paInt16,
                            channels=_CHANNELS,
                            rate=forrate,
                            input=True,
                            input_device_index=dev_idx,
                            frames_per_buffer=_CHUNK_SIZE,
                        )
                        actual_rate = forrate
                        success = True
                        break
                    except: continue

            if not success:
                logger.error("Continuous listen failed to open mic. Retrying in 5s...")
                pa.terminate()
                time.sleep(5)
                continue

            frames = []
            num_chunks = int(actual_rate / _CHUNK_SIZE * chunk_duration)
            for _ in range(num_chunks):
                if not _listening:
                    break
                try:
                    data = stream.read(_CHUNK_SIZE, exception_on_overflow=False)
                    frames.append(data)
                except Exception as e:
                    logger.warning("Stream read error: %s", e)
                    break

            stream.stop_stream()
            stream.close()
            pa.terminate()

            if not _listening or len(frames) == 0:
                continue

            raw = b"".join(frames)
            energy = _audio_energy(raw)

            if energy < silence_threshold:
                continue

            # Active speech -- package into WAV and transcribe
            wav_buf = io.BytesIO()
            with wave.open(wav_buf, "wb") as wf:
                wf.setnchannels(_CHANNELS)
                wf.setsampwidth(_SAMPLE_WIDTH)
                wf.setframerate(actual_rate)
                wf.writeframes(raw)

            text = transcribe_audio(wav_buf.getvalue(), model_size)
            if text:
                callback(text)

        except ImportError:
            logger.error("pyaudio not installed -- cannot run continuous_listen.")
            _listening = False
            break
        except Exception as exc:
            logger.error("continuous_listen loop error: %s", exc)
            time.sleep(0.5)

    logger.info("Continuous listen loop stopped.")


def start_wake_word_listener(
    on_wake_callback: Callable[[], None],
    wake_words: Optional[List[str]] = None,
    check_interval: float = 2.0,
    model_size: str = "tiny",  # tiny is fast enough for keyword spotting
) -> threading.Thread:
    """
    Start a background thread that listens for a wake word.

    Records short (2-second) audio chunks, transcribes them with the tiny
    Whisper model (fast -- ~0.2s per chunk), and checks for wake words. When
    detected, calls on_wake_callback() which should start the full command
    recording session.

    Using "tiny" model for wake word detection is intentional -- it's fast
    enough to check 2-second chunks in near real-time on the Ryzen 7 6800H.
    The full "base" model is used for command transcription.

    Args:
        on_wake_callback : Called (no args) when a wake word is detected.
        wake_words       : Custom wake words list (uses DEFAULT_WAKE_WORDS if None).
        check_interval   : Seconds per audio chunk to check.
        model_size       : Whisper model for keyword spotting (tiny recommended).

    Returns:
        The background Thread (already started).
    """
    global _listening, _listener_thread
    _listening = True
    words = wake_words or DEFAULT_WAKE_WORDS

    print(f"[VoiceInput] Wake word listener active... say '{words[0]}' to start")
    logger.info("Wake word listener started. Words: %s", words)

    def _loop():
        global _listening
        while _listening:
            try:
                audio = record_audio(duration=check_interval)
                if audio is None:
                    time.sleep(1)
                    continue

                # Quick energy check first to avoid transcribing silence
                raw_frames = audio[44:]  # skip WAV header (44 bytes)
                energy = _audio_energy(raw_frames)
                if energy < 200:  # very low threshold for wake word detection
                    continue

                # Transcribe with tiny model (fast!)
                text = transcribe_audio(audio, model_size=model_size)
                if not text:
                    continue

                logger.debug("Wake word check: '%s'", text[:60])

                if detect_wake_word(text, words):
                    logger.info("Wake word confirmed!")
                    try:
                        on_wake_callback()
                    except Exception as cb_exc:
                        logger.error("Wake callback error: %s", cb_exc)

            except Exception as exc:
                logger.error("Wake word listener error: %s", exc)
                time.sleep(1)

        logger.info("Wake word listener stopped.")

    _listener_thread = threading.Thread(target=_loop, daemon=True, name="WakeWordListener")
    _listener_thread.start()
    return _listener_thread


def stop_listening() -> None:
    """
    Stop all background listen loops (continuous_listen and wake word listener).
    Sets the module-level _listening flag to False; loops exit on next iteration.
    """
    global _listening
    _listening = False
    logger.info("Voice input: stop_listening() called.")
