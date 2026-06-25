# VOICE AGENT V2 TESTING

This document outlines the testing workflow for the offline voice command capabilities powered by Piper TTS and faster-whisper.

## 1. Wake Word Tests

**Test Action:**
Run the backend daemon or execute `voice_agent.start()` and speak: "Hey Jarvis."

**Expected Behavior:**
1. The microphone loop running in `continuous_listen` (using `faster-whisper` on `int8` CPU quantization) detects the short transcription.
2. The substring match successfully identifies "hey jarvis".
3. The system halts its silent loop, emits a quick "Yes?" using Piper TTS (or an equivalent beep), and begins listening to a 6-second audio buffer to capture the main command.

## 2. Speech Recognition Tests

**Test Action:**
Immediately after the wake word, speak: "Open Chrome and search for local jobs."

**Expected Behavior:**
1. `faster-whisper` accurately transcribes the buffer entirely locally.
2. The string "Open Chrome and search for local jobs" is sent to the LLM via `brain.py` and `planner.py`.
3. The LLM translates the NLP intent into a strict JSON tool schema: `{"action": "open_app", "args": {"app_name": "chrome"}}` (or the `search_web` action).
4. `executor.py` dispatches the command.

## 3. TTS Tests

**Test Action:**
Wait for the command to finish executing.

**Expected Behavior:**
1. The `executor` returns a string result (e.g., "Navigated to duckduckgo.com").
2. `generate_spoken_response()` creates a conversational reply: "Done, I've opened Chrome for you."
3. The text is passed to `voice_manager.speak()`.
4. `voice_output.py` uses `piper-tts` with the `en_US-lessac-medium` neural voice model to synthesize raw PCM audio in-memory via `io.BytesIO`.
5. `simpleaudio` plays the buffer loudly and clearly. No API calls are made to ElevenLabs or OpenAI.

## Failure Scenarios

- **Microphone Disconnected:** `pyaudio` throws an `IOError` during stream initialization. The voice agent gracefully disables itself without crashing the background daemon.
- **Piper Missing Model:** If the `lessac-medium` `.onnx` file isn't downloaded yet, Piper hangs on the first start to download it locally to `models/piper/`. Subsequent calls are instantaneous.
- **Noise Interference:** If faster-whisper transcribes hallucinated garbage (like "[music]" or "[blank]"), the loop discards it and continues listening silently.