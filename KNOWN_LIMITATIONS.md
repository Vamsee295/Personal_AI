# Known Limitations

1. **Headed Browsers in Sandbox/CI**: Playwright attempts to launch headed chromium which fails without an active X11 Server. We bypass this in tests, but production requires a real desktop.
2. **LLM Hallucinations**: Since the system enforces JSON output via prompts, edge cases with poorly tuned local models might return malformed JSON. We handle this with regex fallbacks and `none` safety checks.
3. **Database Scalability**: The current implementation of `task_history` writes simple strings to SQLite. Long-term use might require pruning older data.
4. **Dependency conflicts**: Occasional issues with `pyautogui` and `pyscreeze` expecting older `numpy<2` versions.
