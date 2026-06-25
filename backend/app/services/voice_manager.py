"""
services/voice_manager.py -- High-level interface for local Voice IO.
Orchestrates Speech-to-Text (Whisper.cpp) and Text-to-Speech (Piper).
"""

import logging
from typing import Optional, Callable
from voice.voice_input import continuous_listen
from voice.voice_output import speak_async, stop_speaking, is_speaking

logger = logging.getLogger("voice_manager")

class VoiceManager:
    """Orchestrates listening and speaking completely locally."""
    
    def listen(self, callback: Callable[[str], None], wake_words: Optional[list[str]] = None) -> None:
        """
        Start the continuous listening loop in a background thread.
        Triggers `callback` when a wake word is detected and command is transcribed.
        """
        logger.info("Starting local voice listener loop.")
        continuous_listen(on_command=callback, wake_words=wake_words)

    def transcribe(self, audio_data: bytes) -> str:
        """
        (Optional) Expose a direct manual transcribe method if needed.
        Currently continuous_listen handles recording and transcription natively.
        """
        pass

    def speak(self, text: str) -> None:
        """Speak text aloud using the local Piper TTS model."""
        logger.info(f"Speaking: {text}")
        speak_async(text)

    def stop(self) -> None:
        """Halt any current speech."""
        stop_speaking()

    def is_active(self) -> bool:
        """Return True if TTS is currently talking."""
        return is_speaking()

voice_manager = VoiceManager()
