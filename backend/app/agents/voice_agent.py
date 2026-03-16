"""
agents/voice_agent.py – Speech-to-text (Whisper / SpeechRecognition) + TTS.
"""

from __future__ import annotations
from app.utils.logger import get_logger

logger = get_logger("voice_agent")


class VoiceAgent:
    """Handles speech recognition and text-to-speech."""

    # ─────────────────────────────────────────────────────────────
    #  Speech recognition
    # ─────────────────────────────────────────────────────────────
    def listen(self, timeout: int = 5, phrase_limit: int = 15) -> str:
        """
        Record audio from the default microphone and transcribe it.
        Returns the recognised text string.
        """
        try:
            import speech_recognition as sr

            r = sr.Recognizer()
            with sr.Microphone() as source:
                logger.info("Listening (timeout=%ds)…", timeout)
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)

            text = r.recognize_google(audio)
            logger.info("Recognised: %s", text)
            return text

        except ImportError:
            raise RuntimeError("SpeechRecognition or PyAudio not installed.")
        except Exception as exc:
            logger.warning("Voice recognition error: %s", exc)
            return ""

    # ─────────────────────────────────────────────────────────────
    #  Text-to-speech (system TTS via pyttsx3 – offline)
    # ─────────────────────────────────────────────────────────────
    def speak(self, text: str) -> None:
        """Convert text to speech and play it."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            logger.info("Spoke: %s", text[:80])
        except ImportError:
            logger.warning("pyttsx3 not installed – skipping TTS.")
        except Exception as exc:
            logger.error("TTS error: %s", exc)

    # ─────────────────────────────────────────────────────────────
    #  Full voice pipeline
    # ─────────────────────────────────────────────────────────────
    async def voice_command_loop(self, on_text_callback) -> None:
        """
        Continuously listen for voice, pass transcribed text to callback.
        callback signature: async def callback(text: str) -> str
        """
        import asyncio
        logger.info("Voice command loop started.")
        while True:
            try:
                text = self.listen()
                if text:
                    response = await on_text_callback(text)
                    if response:
                        self.speak(response)
            except Exception as exc:
                logger.error("Voice loop error: %s", exc)
            await asyncio.sleep(0.5)


# Module-level singleton
voice_agent = VoiceAgent()
