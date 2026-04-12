"""
agents/voice_agent.py – Speech-to-text (Whisper / SpeechRecognition) + TTS.
"""

from __future__ import annotations
import os
import time
import asyncio
import threading
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger("voice_agent")


class VoiceAgent:
    """Handles speech recognition and text-to-speech."""
    
    def __init__(self):
        self.is_active = False
        self.last_active_time = time.time()
        self.stop_speaking = False
        self.whisper_model = None

    def interrupt_tts(self):
        """Signal TTS to stop. (Windows pyttsx3 threaded interruption is best done via ignoring)."""
        self.stop_speaking = True

    # ─────────────────────────────────────────────────────────────
    #  Speech recognition (Faster-Whisper)
    # ─────────────────────────────────────────────────────────────
    def listen(self, timeout: int = 3, phrase_limit: int = 15) -> str:
        """
        Record audio from the microphone, save temp, transcribe with Whisper.
        """
        try:
            import speech_recognition as sr
            import tempfile
            
            # Lazy load whisper to save memory if not used
            if not self.whisper_model:
                logger.info("Loading Faster-Whisper model (base.en)...")
                from faster_whisper import WhisperModel
                self.whisper_model = WhisperModel("base.en", compute_type="int8")

            r = sr.Recognizer()
            with sr.Microphone() as source:
                logger.info("Listening...")
                r.adjust_for_ambient_noise(source, duration=0.2)
                audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)

            # Write to temp file for Whisper
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(audio.get_wav_data())
                temp_path = f.name
            
            segments, _ = self.whisper_model.transcribe(temp_path)
            text = " ".join([seg.text for seg in segments]).strip()
            
            os.remove(temp_path)
            
            final_text = text.lower()
            if final_text:
                logger.info("Recognised: %s", final_text)
            return final_text

        except sr.WaitTimeoutError:
            return ""
        except Exception as exc:
            logger.debug("Voice recognition error: %s", exc)
            return ""

    # ─────────────────────────────────────────────────────────────
    #  Text-to-speech (system TTS via pyttsx3 – offline)
    # ─────────────────────────────────────────────────────────────
    def speak(self, text: str) -> None:
        """Convert text to speech and play it in a non-blocking thread."""
        self.stop_speaking = False
        logger.info("Speaking: %s", text[:80])
        
        def run_tts():
            try:
                import pyttsx3
                # Attempt to initialize COM interface for thread (windows specifically)
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                except ImportError:
                    pass
                
                engine = pyttsx3.init()
                
                # Check interruption before saying
                if not self.stop_speaking:
                    engine.say(text)
                    engine.runAndWait()
            except Exception as e:
                logger.warning("TTS Thread error: %s", e)
            
        t = threading.Thread(target=run_tts, daemon=True)
        t.start()

    # ─────────────────────────────────────────────────────────────
    #  Wake word detection
    # ─────────────────────────────────────────────────────────────
    def wait_for_wakeword(self) -> bool:
        """Wait for the wake word using Porcupine."""
        try:
            import pvporcupine
            import pyaudio
            import struct
        except ImportError:
            logger.error("pvporcupine or pyaudio not installed.")
            return False

        access_key = settings.PICOVOICE_ACCESS_KEY or os.environ.get("PICOVOICE_ACCESS_KEY")
        if not access_key:
            logger.error("PICOVOICE_ACCESS_KEY not found in environment.")
            return False
            
        try:
            ppn_path = settings.WAKE_WORD_PPN or os.environ.get("WAKE_WORD_PPN", "ultron.ppn")
            if ppn_path and os.path.exists(ppn_path):
                porcupine = pvporcupine.create(access_key=access_key, keyword_paths=[ppn_path])
            else:
                porcupine = pvporcupine.create(access_key=access_key, keywords=["jarvis"])
            
            pa = pyaudio.PyAudio()
            stream = pa.open(
                rate=porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=porcupine.frame_length
            )
            
            logger.info("Listening for wake word (Idle)...")
            try:
                while True:
                    pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                    pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
                    result = porcupine.process(pcm)
                    if result >= 0:
                        logger.info("Wake word detected!")
                        return True
            finally:
                stream.close()
                pa.terminate()
                porcupine.delete()
        except Exception as e:
            logger.error("Porcupine error: %s", e)
            return False

    # ─────────────────────────────────────────────────────────────
    #  Full voice pipeline
    # ─────────────────────────────────────────────────────────────
    async def voice_command_loop(self, on_text_callback) -> None:
        """
        State machine for Gemini-style voice mode.
        """
        logger.info("Voice command loop started.")
        while True:
            try:
                if not self.is_active:
                    # 💤 IDLE MODE
                    detected = await asyncio.to_thread(self.wait_for_wakeword)
                    if detected:
                        self.is_active = True
                        self.last_active_time = time.time()
                        self.speak("Yes Sir")
                    else:
                        await asyncio.sleep(5)
                else:
                    # 🟢 ACTIVE MODE
                    if time.time() - self.last_active_time > 15:
                        self.speak("Going to sleep")
                        self.is_active = False
                        continue
                        
                    # Listen with shorter timeout so we can check idle limit
                    command = await asyncio.to_thread(self.listen, 3, 10)
                    
                    if "stop" in command or "exit" in command:
                        self.interrupt_tts()
                        self.speak("Going idle")
                        self.is_active = False
                    elif command:
                        self.last_active_time = time.time()
                        self.interrupt_tts() # Stop whatever it was saying before
                        
                        response = await on_text_callback(command)
                        if response:
                            self.speak(response)
                            self.last_active_time = time.time()
            except Exception as exc:
                logger.error("Voice loop error: %s", exc)
                await asyncio.sleep(2)


# Module-level singleton
voice_agent = VoiceAgent()
