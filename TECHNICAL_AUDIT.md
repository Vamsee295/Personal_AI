# Technical Audit Report: Personal AI Agent v2

## 1. Current Project Architecture
- **Frontend**: Next.js 14+ with React 18, utilizing Vite internally for some tooling config (despite Next.js scripts), TailwindCSS, and Shadcn UI components.
- **Backend**: Python 3.10+ FastAPI server running asynchronously using `uvicorn`, communicating with Ollama locally for LLM operations.
- **Communication**: Frontend communicates to Backend over standard HTTP REST (`/api/*`) and WebSockets (e.g., live screen insights, voice).
- **Core Automation**: Actions are dispatched to OS utilities (Subprocess) and PyAutoGUI / MSS. WhatsApp uses Selenium or direct Windows UI automation.
- **Overall status**: The current architecture is a classic decoupled client-server model. It does not meet the "Tauri + Rust Backend + Python Agent Layer" constraint yet. The entire frontend/backend packaging needs a structural shift to conform to the new architecture.

## 2. Frontend Modules and Completion Status
- **Workspace/Chat**: `chat/index.tsx`, `files/index.tsx`
  - **Purpose**: Interactive coding and file manipulation interface.
  - **Status**: Partially completed. UI is present, integrates with agent APIs.
  - **Tech Debt**: Heavy reliance on browser-native APIs where Tauri native APIs would provide better local system access.
  - **Recommended Improvements**: Refactor standard Next.js routing into a React SPA suitable for Tauri compilation. Replace browser `fetch` calls with Tauri IPC.
  - **Priority**: High

- **Voice Assistant Interface**: `voice/index.tsx`
  - **Purpose**: Voice command UI with waveform and Web Speech API fallback.
  - **Status**: Partially completed. Relies heavily on Web API/browser speech synthesis.
  - **Tech Debt**: Fails offline requirements gracefully if relying on browser APIs that phone home.
  - **Recommended Improvements**: Delegate entirely to backend/Tauri core for Piper TTS & Whisper.cpp to ensure local execution.
  - **Priority**: Medium

- **System Control & Tasks**: `control/index.tsx`, `tasks/index.tsx`
  - **Purpose**: Execute terminal tasks, read logs, manage OS apps.
  - **Status**: Completed but heavily tied to FastAPI backend.
  - **Tech Debt**: Relies on REST endpoints.
  - **Recommended Improvements**: Move system monitoring and control strictly into Tauri Rust core.
  - **Priority**: Low

## 3. Backend Modules and Completion Status
- **FastAPI Core**: `backend/app/main.py`
  - **Purpose**: Orchestrator, serves REST endpoints.
  - **Status**: Completed.
  - **Tech Debt**: Heavyweight. Requires managing Python environments and local networking ports, which adds friction to local-first setup.
  - **Recommended Improvements**: Transition high-level logic to Tauri (Rust) where possible. Retain Python purely as an Agent Layer daemon (e.g. `agent_daemon.py`) communicating over stdio or local IPC with Rust, not exposing generic HTTP.
  - **Priority**: Critical

- **AI Service (Ollama)**: `backend/app/core/ollama_client.py`
  - **Purpose**: Wraps local Ollama APIs.
  - **Status**: Completed.
  - **Tech Debt**: None, works well for local constraint.
  - **Recommended Improvements**: Optimize error handling if Ollama isn't running.
  - **Priority**: Low

- **Voice Module**: `backend/voice/`
  - **Purpose**: Wake-word and offline Voice.
  - **Status**: Completed (using `faster-whisper` and `pyttsx3`/`SpeechRecognition`).
  - **Tech Debt**: `pyttsx3` is notoriously clunky and `SpeechRecognition` can be slow/legacy.
  - **Recommended Improvements**: Replace with `whisper.cpp` Python bindings (or Rust bindings via Tauri) and Piper TTS for high-quality, fully local voice interaction.
  - **Priority**: High

## 4. Agent Framework Status
- **Planner & Executor**: `backend/autonomous/planner.py`, `backend/autonomous/executor.py`
  - **Purpose**: Translate NLP to JSON intent, execute on local OS.
  - **Status**: Completed and functioning natively.
  - **Tech Debt**: Uses raw Python execution (`eval`/subprocess) which is powerful but brittle.
  - **Recommended Improvements**: Define strict schemas using Pydantic, formalize tool-calling using standard local LLM features (Ollama tool-calling) instead of manual string parsing.
  - **Priority**: High

## 5. Ollama Integration Status
- **Purpose**: Providing AI capabilities (Qwen3, Llama, DeepSeek).
- **Status**: Completed via HTTP requests to `localhost:11434`.
- **Tech Debt**: HTTP overhead is minimal but manual streaming logic exists.
- **Recommended Improvements**: Integrate native Ollama tool-calling. Ensure Qwen3 and DeepSeek models are configured as defaults instead of fallback Llama models.
- **Priority**: Low

## 6. Memory Architecture
- **Implementation**: SQLite via `aiosqlite` (`backend/app/database/db.py`).
  - **Purpose**: Persist tasks, logs, and context.
  - **Status**: Partially completed. Stores basic history.
  - **Tech Debt**: Missing vector store integration for semantic memory. "Persistent memory" currently just means relational logs.
  - **Recommended Improvements**: Add local vector database (e.g., ChromaDB local, or SQLite+Vector) to enable genuine agent reflection and semantic recall.
  - **Priority**: High

## 7. Browser Automation Readiness
- **Implementation**: Selenium (`backend/automation/whatsapp_desktop_automation.py`).
  - **Purpose**: Automating web apps (specifically WhatsApp currently).
  - **Status**: Partially completed.
  - **Tech Debt**: Selenium is slow and requires managing chromedriver.
  - **Recommended Improvements**: Replace completely with **Playwright**. Playwright provides a much richer, robust browser context model and doesn't require separate driver binaries natively.
  - **Priority**: Critical

## 8. Desktop Automation Readiness
- **Implementation**: PyAutoGUI, MSS, OpenCV (`backend/app/services/action_executor.py`, `backend/app/agents/vision_module.py`).
  - **Purpose**: Screenshots, coordinate clicking, keyboard typing.
  - **Status**: Completed.
  - **Tech Debt**: Screen coordinates are highly resolution dependent. Tesseract OCR is finicky and requires system installation.
  - **Recommended Improvements**: Investigate multi-modal local LLMs (e.g. LLaVA or Qwen-VL) to bypass Tesseract OCR entirely, reading UI natively. Use Rust for lower-level native OS hooks where PyAutoGUI falls short.
  - **Priority**: Medium

## 9. Security Considerations
- **Status**: Local-only, so external threats are minimal.
- **Tech Debt**: Python `subprocess` and `os.system` are run without sandboxing. The Agent can theoretically execute destructive commands (e.g., `rm -rf`).
- **Recommended Improvements**: Implement a "dry-run" mode or prompt confirmation for irreversible file system/shell actions.
- **Priority**: High

## 10. Missing Dependencies
- Playwright (Python bindings)
- Whisper.cpp (Python/Rust bindings)
- Piper TTS (Binaries/Bindings)
- Tauri CLI and Rust environment for build pipeline.

## 11. Scalability Concerns
- **Model Ram Usage**: Running Local LLM + Whisper + TTS simultaneously will consume significant RAM/VRAM. Memory management between models needs orchestration.
- **Python Threading**: Heavy reliance on `asyncio.to_thread` for blocking UI tasks (like screen capture or browser automation).

## 12. Recommended Production Architecture

To meet all constraints (Tauri, Rust, Python Agent Layer, Playwright, Whisper.cpp, Piper TTS, Local-first), the architecture should shift to:

```text
[ React (TypeScript) + Tauri UI ]
          | (Tauri IPC / Events)
          v
[ Tauri Core (Rust) ] 
   - Manages Window State
   - OS-level system calls (System Tray, Global Hotkeys)
   - Spawns & monitors the Python Agent Layer process
          | (gRPC, standard I/O, or local socket)
          v
[ Python Agent Layer ]
   - Automation: Playwright, PyAutoGUI, MSS
   - AI Comm: Ollama Client (Qwen3, DeepSeek)
   - Voice Pipeline: Whisper.cpp STT <-> Piper TTS
   - Memory: SQLite + Local Vector Search
```

---

## A. Completed Features
- Ollama local inference connectivity.
- Desktop UI interactions (PyAutoGUI, App launching).
- SQLite relational database scaffolding.
- Basic screenshot & OCR pipeline.

## B. Partially Completed Features
- Agent planning loop (needs upgrade to native tool-calling).
- Voice commands (needs migration to Piper/Whisper.cpp).
- Browser automation (needs migration to Playwright).

## C. Missing Features
- Job application assistance module.
- Tauri + Rust application shell.
- Semantic persistent memory (Vector store).
- Multi-modal vision analysis (instead of Tesseract).

## D. Critical Refactors
1. **Frontend**: Port Next.js components to standard Vite/React strictly static output for Tauri embedding. Remove Next.js Server Components / API routes.
2. **Backend**: Discard FastAPI overhead. Convert Python backend into a dedicated daemon (`agent_daemon.py`) that communicates via JSON RPC or WebSockets over a loopback socket to the Tauri Rust core.
3. **Browser Automation**: Rip out Selenium, install and wrap Playwright async Python API.
4. **Voice**: Replace `faster-whisper` with `whisper.cpp`, replace `pyttsx3` with Piper.

## E. Recommended Folder Structure
```
ultron-agent/
├── src-tauri/                 # Rust Backend (Tauri Core)
│   ├── src/
│   │   ├── main.rs            # Entry point, spawns Python daemon
│   │   ├── commands.rs        # IPC handlers
│   │   └── system.rs          # Native OS hooks
│   ├── Cargo.toml
│   └── tauri.conf.json
├── src/                       # Frontend (React + TypeScript)
│   ├── components/            # UI Components (Shadcn)
│   ├── pages/                 # React Router Views
│   ├── lib/                   # Tauri IPC Wrappers
│   └── main.tsx               # React Entry point
├── agent-layer/               # Python AI Backend
│   ├── core/
│   │   ├── llm.py             # Ollama client
│   │   └── memory.py          # SQLite + Vector logic
│   ├── automation/
│   │   ├── browser.py         # Playwright scripts (Job App Assistant)
│   │   └── desktop.py         # PyAutoGUI / MSS
│   ├── voice/
│   │   ├── stt.py             # Whisper.cpp
│   │   └── tts.py             # Piper TTS
│   ├── daemon.py              # Main entry loop for Python process
│   ├── pyproject.toml
│   └── requirements.txt
├── package.json
└── vite.config.ts
```

## F. Development Roadmap
1. **Phase 1**: Initialize Tauri + Vite React project. Port existing frontend assets into the new structure. Ensure it builds as a native desktop app.
2. **Phase 2**: Restructure Python backend into `agent-layer`. Remove FastAPI. Set up secure IPC/Local socket communication between Rust and Python.
3. **Phase 3**: Migrate browser automation to Playwright. Build the foundation for Job Application assistance workflows.
4. **Phase 4**: Overhaul Voice module with Whisper.cpp and Piper TTS for ultra-fast, local speech.
5. **Phase 5**: Enhance Memory system with local embeddings. Refine Tool-Calling utilizing Ollama's native tool protocols.
