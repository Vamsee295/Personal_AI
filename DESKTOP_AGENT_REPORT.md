# Desktop Agent Report

## Implemented Desktop Tools
The `Brain` orchestrator can now natively command the following desktop tools via the `Tool Registry`:
1. `open_app`: Uses subprocess/commands to open system apps (Notepad, VS Code, Chrome).
2. `type_text`: Types keystrokes via `pyautogui` directly to the active window.
3. `press_key`: Submits hotkeys (e.g., `alt+tab`, `win+d`, `enter`).
4. `mouse_click`: Clicks coordinates provided by the Vision Agent or heuristics.
5. `move_mouse`: Moves the cursor physically.
6. `scroll_desktop`: Triggers mouse wheel events to navigate local UI or web pages outside playwright.
7. `take_screenshot`: Captures the full OS screen via `mss` for the Vision Agent.

## Supported Operating System Features
- Primarily mapped for Windows 11 conventions in `app/services/action_executor.py` but handles generic fallback via python subprocesses on Linux/Mac.
- Leverages X11 displays gracefully in the Docker/headless environment using `xvfb-run`.

## Safety Limitations
- The agent does not inherently know what application is active without Vision Analysis. It can type blindly if a window focus is lost.
- Destructive hotkeys (like `alt+f4`) are supported and could be triggered if the LLM hallucinates an escape route.
- Mouse coordinate mapping requires exact resolution matching. If the monitor scales dynamically, the click targets may drift.

## Remaining Work
- Implement active window polling (e.g. via `pygetwindow`) to ensure the agent only types when the target application actually has focus.

## Manual Testing Scenarios
1. Ask the Chat Agent: "Open notepad, type 'hello world', and press enter."
2. Check the Agent Control Live Pipeline: Verify `open_app` -> `type_text` -> `press_key` events emit successfully.
3. View the `backend/screenshots` folder to verify full desktop rendering with `take_screenshot`.
