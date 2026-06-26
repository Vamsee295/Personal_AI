# Known Limitations

1. **Hardware Resource Saturation**
   Running Local TTS (Piper), Local STT (Faster-Whisper), Local LLM (Ollama), and Playwright browsers simultaneously can overload systems with low RAM.

2. **Desktop OS Environment Dependency**
   `pyautogui` requires an active Display Server. Running the agent completely headless on standard Linux servers requires explicit `Xvfb` wrapping.

3. **LLM Context Window Limits**
   During extensive multi-step tasks that encounter numerous failures, the `Observe -> Replan` error trace stack can grow extremely large. Though memory summarization exists, prompt trimming might be needed for very deep retry trees.

4. **Voice Interruption**
   Voice input does not currently support full duplex "barge-in" capabilities. The user must wait until the TTS playback buffer finishes speaking before providing a new wake word.
