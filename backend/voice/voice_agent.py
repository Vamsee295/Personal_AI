"""
voice/voice_agent.py -- The unified Voice Loop Controller for Ultron.

Ties together:
  voice_input.py  → faster-whisper STT + wake word listener
  voice_output.py → pyttsx3 TTS
  memory_manager  → inject past context into Ollama prompt
  action_executor → execute JSON actions on the laptop

Architecture:
  1. start()         → speaks greeting, starts wake word listener
  2. on_wake_detected() → says "Yes?", records 6s command audio
  3. process_voice_command() → memory → Ollama → execute → speak result
  4. stop()          → clean shutdown

Singleton enforced: only ONE VoiceAgent may be active at a time.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from typing import Optional

logger = logging.getLogger("voice_agent")

# ── Singleton guard ───────────────────────────────────────────────────────────
_instance: Optional["VoiceAgent"] = None
_instance_lock = threading.Lock()


# =============================================================================
#  RESPONSE GENERATOR
# =============================================================================

def generate_spoken_response(action: dict, result: dict) -> str:
    """
    Convert a JSON action + its execution result into a natural spoken sentence.

    The agent should sound like a helpful assistant, not a terminal log.

    Args:
        action : The action dict (e.g. {"action": "open_app", "target": "chrome"}).
        result : The executor result dict ({"success": True, "message": "..."}).

    Returns:
        A natural-language string suitable for TTS.
    """
    action_type = action.get("action", "").lower()
    target      = action.get("target", "").strip()
    value       = action.get("value", "").strip()
    success     = result.get("success", False)
    error_msg   = result.get("error", "")

    if not success:
        # Keep error messages short for TTS
        short_err = re.sub(r"['\"`*{}]", "", str(error_msg))[:80]
        return f"Sorry, I ran into a problem. {short_err}" if short_err else "Sorry, that didn't work."

    responses = {
        "open_app":              f"Done, I've opened {target or 'the application'} for you.",
        "open_url":              f"Done, I've opened {target or 'the website'} in your browser.",
        "type_text":             f"Done, I've typed that for you.",
        "press_key":             f"Done, I pressed {value or target}.",
        "mouse_click":           f"Done, I clicked at the target location.",
        "take_screenshot":       "I've taken a screenshot and saved it.",
        "move_mouse":            "Done, I moved the mouse.",
        "scroll":                f"Done, I scrolled {value or 'the page'}.",
        "send_whatsapp_message": f"Message sent to {target} successfully.",
        "read_whatsapp":         f"I've read the messages from {target}.",
    }
    return responses.get(action_type, f"Done. The action {action_type} completed successfully.")


# =============================================================================
#  VOICE AGENT CLASS
# =============================================================================

class VoiceAgent:
    """
    The full voice pipeline controller.

    Usage:
        agent = VoiceAgent.get_instance()
        agent.start()    # speaks greeting + starts wake word listener
        # ...speak "Hey Vamsee open Chrome"...
        agent.stop()
    """

    def __init__(self) -> None:
        # Lazy imports -- only fail at runtime if libraries missing
        self.is_active    = False
        self._command_lock = threading.Lock()  # prevent concurrent command processing
        logger.info("VoiceAgent initialised.")

    @classmethod
    def get_instance(cls) -> "VoiceAgent":
        """Return the singleton VoiceAgent, creating it if needed."""
        global _instance
        with _instance_lock:
            if _instance is None:
                _instance = cls()
        return _instance

    # ─────────────────────────────────────────────────────────────────────────
    #  LIFECYCLE
    # ─────────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """
        Start the voice agent:
        1. Speak welcome greeting via TTS.
        2. Start wake word listener in background thread.
        """
        if self.is_active:
            logger.warning("VoiceAgent.start() called but already active.")
            return

        self.is_active = True
        logger.info("VoiceAgent starting.")

        # Speak welcome in background (non-blocking)
        from voice.voice_output import speak_async
        speak_async("Ultron is online. Say Hello Ultron to wake me.")

        # Start wake word listener
        try:
            from voice.voice_input import start_wake_word_listener
            start_wake_word_listener(self.on_wake_detected)
        except Exception as exc:
            logger.error("Failed to start wake word listener: %s", exc)
            self.is_active = False

    def stop(self) -> None:
        """Stop all voice activity cleanly."""
        self.is_active = False
        try:
            from voice.voice_input import stop_listening
            stop_listening()
        except Exception:
            pass
        try:
            from voice.voice_output import stop_speaking
            stop_speaking()
        except Exception:
            pass
        logger.info("VoiceAgent stopped.")

    # ─────────────────────────────────────────────────────────────────────────
    #  WAKE WORD HANDLER
    # ─────────────────────────────────────────────────────────────────────────

    def on_wake_detected(self) -> None:
        """
        Called by the wake word listener when activation phrase is heard.

        Plays an acknowledgement sound, records the full command (6 seconds),
        transcribes it, then runs the full agent pipeline on it.
        Skips if another command is currently being processed.
        """
        if not self.is_active:
            return

        if not self._command_lock.acquire(blocking=False):
            logger.info("Wake word detected but command already in progress -- ignoring.")
            return

        try:
            from app.services.voice_manager import voice_manager
            from voice.voice_input import listen_and_transcribe
            import time

            # Acknowledge
            voice_manager.speak("Yes?")
            time.sleep(0.3)  # small gap before recording

            # Record command
            logger.info("Recording command after wake word...")
            print("[VoiceAgent] Listening for command (6s)...")
            command_text = listen_and_transcribe(duration=6.0, model_size="base")

            if not command_text:
                voice_manager.speak("Sorry, I didn't catch that. Please try again.")
                return

            print(f"[VoiceAgent] Command: {command_text}")
            
            import asyncio
            # To avoid crossing thread boundaries with Playwright (which lives on the main event loop),
            # we send the command to the autonomous loop via a global queue.
            from autonomous.agent_loop import get_voice_queue
            
            from autonomous.agent_loop import main_event_loop
            try:
                if main_event_loop and main_event_loop.is_running():
                    queue = get_voice_queue()
                    main_event_loop.call_soon_threadsafe(queue.put_nowait, command_text)
                else:
                    raise RuntimeError("No running main loop found")
            except RuntimeError:
                # Fallback if running entirely standalone (no main loop running yet)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.process_voice_command(command_text))
                loop.close()

        except Exception as exc:
            logger.error("on_wake_detected error: %s", exc)
            try:
                from app.services.voice_manager import voice_manager
                voice_manager.speak("Sorry, I had a problem processing that.")
            except Exception:
                pass
        finally:
            self._command_lock.release()

    # ─────────────────────────────────────────────────────────────────────────
    #  COMMAND PIPELINE
    # ─────────────────────────────────────────────────────────────────────────

    async def process_voice_command(self, command_text: str) -> dict:
        """
        Voice commands are now dispatched directly to the global orchestrator.
        The Brain orchestrator will handle state tracking, memory injection, planning, and executing.
        """
        logger.info("Dispatching voice command to Orchestrator: %s", command_text[:100])

        try:
            # Just push directly to the brain's orchestrator queue
            from autonomous.agent_loop import get_orchestrator_queue
            import uuid
            
            queue = get_orchestrator_queue()
            task_id = str(uuid.uuid4())
            await queue.put({
                "command": command_text,
                "task_id": task_id,
                "source": "voice"
            })
            
            # The agent loop emits "task_completed" or "task_failed" when done.
            # Voice module watches that stream from the frontend or an internal watcher
            # to know when to speak back, or we let the main loop speak back directly if needed.
            # For immediate confirmation:
            return {
                "success": True,
                "command": command_text,
                "task_id": task_id,
                "spoken_response": "I'm on it.",
            }
        except Exception as e:
            logger.error(f"Failed to dispatch voice command: {e}")
            from voice.voice_output import speak
            speak("Sorry, there was an issue processing your request.")
            return {"success": False, "error": str(e)}

    # ─────────────────────────────────────────────────────────────────────────
    #  OLLAMA HELPER (synchronous -- for use from threads)
    # ─────────────────────────────────────────────────────────────────────────

    _VOICE_SYSTEM_PROMPT = """\
You are an AI agent that converts voice commands into structured JSON for a Windows automation system.

RULES:
1. Respond with ONLY a single valid JSON object.
2. JSON must have exactly: action, target, value, x (int), y (int).
3. Actions: open_app, open_url, type_text, press_key, mouse_click, take_screenshot, move_mouse, scroll, send_whatsapp_message, read_whatsapp

{memory_context}
Now respond to the voice command with ONLY the JSON:"""

    def _call_ollama(self, command: str, mem_context: str) -> tuple[dict, str]:
        """
        Call Ollama synchronously (blocking) -- safe to run in a thread.

        Returns:
            (action_dict, raw_text)
        """
        import requests as req

        system = self._VOICE_SYSTEM_PROMPT.replace("{memory_context}", mem_context)

        payload = {
            "model": "qwen2.5-coder:7b",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": command},
            ],
            "stream": False,
        }

        resp = req.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["message"]["content"].strip()

        # Parse JSON
        action = self._extract_json(raw)
        return action, raw

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extract the first valid JSON object from LLM response text."""
        text = text.strip()
        # Direct parse
        try:
            return json.loads(text)
        except Exception:
            pass
        # Markdown fence
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except Exception:
                pass
        # First {...} block
        m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
        raise ValueError(f"No valid JSON in: {text[:200]}")

    # ─────────────────────────────────────────────────────────────────────────
    #  MANUAL LISTEN (from WebSocket / API -- no wake word needed)
    # ─────────────────────────────────────────────────────────────────────────

    def listen_once(self, duration: float = 6.0) -> dict:
        """
        Record one audio clip, transcribe it, run the full agent pipeline.
        Called by the WebSocket handler when the mic button is clicked.

        Returns:
            Dict with transcribed text + execution result.
        """
        from voice.voice_input import listen_and_transcribe

        print(f"[VoiceAgent] listen_once: recording {duration}s...")
        text = listen_and_transcribe(duration=duration, model_size="base")

        if not text:
            return {
                "success": False,
                "transcribed": "",
                "message": "No speech detected",
            }

        result = self.process_voice_command(text)
        result["transcribed"] = text
        return result

    async def on_task_completed(self, success: bool, message: str):
        """Hook called when the orchestration loop finishes a task."""
        prefix = "Task completed successfully." if success else "Task failed."
        await self.speak(f"{prefix} {message}")
