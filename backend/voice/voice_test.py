"""
voice/voice_test.py -- Voice system end-to-end test.
Run from backend/ directory: python voice/voice_test.py

Tests:
  1. TTS -- speak a sentence and verify audio output
  2. STT -- record 5 seconds and print transcription
  3. Round trip -- record → transcribe → Ollama → print JSON action
  4. Wake word -- listen 30s and print detections (says "Hey Vamsee" to test)
"""

from __future__ import annotations

import sys
import io
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure backend/ root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEP  = "─" * 65
PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"


def section(title: str):
    print(f"\n{SEP}")
    print(f"  TEST: {title}")
    print(SEP)


# =============================================================================
#  TEST 1: Text-to-Speech
# =============================================================================
section("TTS — speak a greeting")
print("  Attempting to speak: 'Hello, I am Vamsee AI, your personal assistant'")
try:
    from voice.voice_output import init_tts, speak

    engine = init_tts()
    if engine is None:
        print(f"  {FAIL} TTS engine failed to initialise. Is pyttsx3 installed?")
    else:
        ok = speak("Hello, I am Vamsee AI, your personal assistant.")
        if ok:
            print(f"  {PASS} TTS spoke successfully. Did you hear it?")
        else:
            print(f"  {FAIL} speak() returned False.")
except ImportError as e:
    print(f"  {SKIP} pyttsx3 not installed: {e}")
    print("  Install: pip install pyttsx3")
except Exception as e:
    print(f"  {FAIL} TTS error: {e}")

time.sleep(1)

# =============================================================================
#  TEST 2: Speech-to-Text (live microphone)
# =============================================================================
section("STT — record 5 seconds from microphone")
print("  >>> SPEAK NOW (you have 5 seconds) <<<")
try:
    from voice.voice_input import listen_and_transcribe

    text = listen_and_transcribe(duration=5.0, model_size="base")
    if text:
        print(f"  {PASS} Transcribed: '{text}'")
    else:
        print(f"  {FAIL} No speech detected or Whisper returned empty.")
        print("  Make sure your microphone is connected and working.")
except ImportError as e:
    print(f"  {SKIP} faster-whisper or pyaudio not installed: {e}")
    print("  Install: pip install faster-whisper pyaudio")
    print("  Windows PyAudio: pip install pipwin && pipwin install pyaudio")
except Exception as e:
    print(f"  {FAIL} STT error: {e}")

time.sleep(1)

# =============================================================================
#  TEST 3: Full Round Trip — voice → Ollama → JSON action
# =============================================================================
section("Round trip — record → transcribe → Ollama → JSON")
print("  >>> SAY A COMMAND (e.g. 'Open Notepad') (5 seconds) <<<")
try:
    import requests
    from voice.voice_input import listen_and_transcribe

    text = listen_and_transcribe(duration=5.0, model_size="base")

    if not text:
        print(f"  {SKIP} No speech detected — skipping Ollama step.")
    else:
        print(f"  Transcribed: '{text}'")
        print("  Sending to Ollama...")

        SYSTEM = (
            "Convert this voice command to a single JSON action. "
            "Keys: action, target, value, x, y. "
            "Return ONLY JSON, no extra text."
        )
        resp = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "qwen2.5-coder:7b",
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user",   "content": text},
                ],
                "stream": False,
            },
            timeout=30,
        )

        if resp.ok:
            raw = resp.json()["message"]["content"]
            print(f"  {PASS} Ollama response: {raw[:200]}")
        else:
            print(f"  {FAIL} Ollama returned {resp.status_code}")

except ImportError as e:
    print(f"  {SKIP} Dependency missing: {e}")
except requests.exceptions.ConnectionError:
    print(f"  {SKIP} Ollama not running at localhost:11434")
except Exception as e:
    print(f"  {FAIL} Round trip error: {e}")

time.sleep(1)

# =============================================================================
#  TEST 4: Wake Word Detection
# =============================================================================
section("Wake word detection — listen 15 seconds")
print("  >>> SAY 'Hey Vamsee' within the next 15 seconds <<<")
print("  (The listener uses the 'tiny' Whisper model for speed)")

try:
    detected_count = [0]
    stop_event = __import__("threading").Event()

    def on_wake():
        detected_count[0] += 1
        print(f"\n  *** WAKE WORD DETECTED! (count={detected_count[0]}) ***")
        try:
            from voice.voice_output import speak_async
            speak_async("Wake word confirmed!")
        except Exception:
            pass

    from voice.voice_input import start_wake_word_listener, stop_listening

    thread = start_wake_word_listener(on_wake, check_interval=2.0, model_size="tiny")

    # Let it run for 15 seconds
    for i in range(15, 0, -1):
        print(f"  Listening... {i}s remaining", end="\r", flush=True)
        time.sleep(1)

    stop_listening()
    print()  # newline after countdown

    if detected_count[0] > 0:
        print(f"  {PASS} Wake word detected {detected_count[0]} time(s)!")
    else:
        print(f"  {FAIL} Wake word not detected. Try speaking louder or closer to the mic.")

except ImportError as e:
    print(f"  {SKIP} Missing dependency: {e}")
except Exception as e:
    print(f"  {FAIL} Wake word test error: {e}")

# =============================================================================
#  SUMMARY
# =============================================================================
print(f"\n{SEP}")
print("  VOICE TEST COMPLETE")
print(SEP)
print("  If Tests 1 + 2 passed: full voice pipeline is working!")
print("  Next: restart the backend, open localhost:3000/control,")
print("  and click the mic button to say a voice command.")
print(f"{SEP}\n")
