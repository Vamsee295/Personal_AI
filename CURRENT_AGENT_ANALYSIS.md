# Current Agent Analysis

## 1. Current Agent Execution Flow
The existing agent uses a continuous observation-action loop (defined in `backend/autonomous/agent_loop.py`):
1. **Observe**: Captures the screen and uses PyTesseract to extract OCR text (`screen_agent.extract_text`).
2. **Think**: Passes the OCR context to the LLM (Ollama) to decide if an action is needed (`autonomous/brain.py`).
3. **Plan**: Parses the AI's natural language response into a specific JSON command (`autonomous/planner.py`).
4. **Execute**: Runs the selected action against the OS or browser via `autonomous/executor.py` or `action_executor.py`.

## 2. Current Planner Behavior
The planner (`autonomous/planner.py`) relies on simplistic string matching rather than structured JSON outputs or native LLM tool-calling. It lowercases the AI's response and looks for explicit keywords (e.g., `if "open vscode" in response_lower:` -> returns `{"action": "open_app", "args": {"app_name": "code"}}`). This makes the planner rigid, difficult to scale, and completely reliant on the LLM generating exact phrasing.

Alternatively, `services/agent_service.py` has a multi-step agent execution flow that tries to extract raw JSON out of markdown blocks (`_parse_plan`), which is better but still brittle compared to modern native tool-calling APIs.

## 3. Current Executor Behavior
The `executor.py` and `services/action_executor.py` files take the parsed dictionary and route it to standard Python functions.
- OS apps are opened via `subprocess.Popen` mapping known app names to system paths.
- UI manipulation is handled by `PyAutoGUI` (typing text, moving mouse, clicking, pressing keys).
- File operations are handled by standard Python OS/pathlib methods.

## 4. Current Memory Behavior
Memory is handled by an SQLite database (`backend/app/database/db.py`) tracking `tasks`, `ai_logs`, `activity`, and `files_history`.
- Currently, this acts only as an audit trail (logging what the AI *did*).
- **Critical flaw**: The agent does not read its own past activity to build context for current decisions. There is no vector database or semantic search to retrieve long-term context or "remember" past user preferences.

## 5. Existing Tool Architecture
Tools are hardcoded functions scattered across `action_executor.py` and `executor.py`. They lack formalized JSON schemas (like JSON Schema definitions used by OpenAI/Ollama tool calling). Because they lack schemas, the LLM cannot natively introspect what tools are available or what arguments they require; instead, the `ai_service.py` prompt manually explains what to do, and the backend heavily sanitizes the output.

## 6. Existing Browser Automation Capabilities
Browser automation is currently heavily localized to one specific task: WhatsApp automation.
- `automation/whatsapp_automation.py` uses **Selenium** with a persistent Chrome profile to navigate to WhatsApp Web, search for contacts, and send messages.
- There is no general-purpose browser agent capable of navigating arbitrary DOMs, clicking links, reading page text, or filling out generic forms.

## 7. Existing Desktop Automation Capabilities
Desktop automation is moderately mature:
- Screenshots and OCR via `mss` and `pytesseract`.
- Mouse and keyboard injection via `pyautogui`.
- Native window management via `subprocess` commands and `pygetwindow`.
However, relying on coordinate-based clicks and OCR text matching is notoriously brittle for cross-platform autonomous agents.

## 8. Existing Voice Capabilities
The Voice pipeline (`voice_agent.py`) uses:
- Wake word and listening via standard microphones.
- **faster-whisper** for Speech-to-Text.
- **pyttsx3** / SAPI5 for offline Text-to-Speech.
- While entirely offline, the current TTS implementation is somewhat robotic and dependent on the host OS's native voices.

---

## Missing Capabilities Preventing Real Agent & Job Application Automation
To enable Jarvis to act as a real AI agent that can reliably apply for jobs and perform arbitrary browser tasks:

1. **Native Tool Calling**: The agent needs to utilize Ollama's native tool-calling JSON schema support. This ensures the LLM reliably populates correct arguments instead of relying on regex scraping and string parsing.
2. **General-Purpose Browser Control**: Selenium is too slow and specific. The agent needs **Playwright** wrapped into a generic set of tools (`navigate`, `click_element`, `fill_input`, `read_dom`), allowing the agent to "see" the accessibility tree of the page and interact with job boards dynamically.
3. **Multi-Step Memory Context**: The agent's loop needs to carry over its previous actions (e.g., "I clicked the login button, now I see the password field") rather than evaluating every loop tick as a brand-new stateless event.
4. **Robust Plan Execution State**: Job applications require sequences (Log in -> Search -> Click Apply -> Upload Resume -> Submit). The current loop is too reactive. It needs a state machine that tracks progress through a complex goal over minutes or hours.