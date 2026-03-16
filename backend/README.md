# Vamsee AI – Backend

The backend of Vamsee AI is a high-performance, modular API built with **Python** and **FastAPI**. It acts as the "brain" of the AI IDE, handling AI communication, file system operations, terminal execution, and system-level automation.

## Core Roles
- **AI Engine Integration**: Communicates with local LLMs via **Ollama** (streaming supported).
- **Security Sandboxing**: Restricts file access to allowed workspace directories and blocks dangerous shell commands.
- **System Automation**: Provides services for screen capture, OCR, voice commands, and application control (e.g., opening VS Code).
- **Workspace Management**: Tracks project folders, builds file trees, and indexes code.
- **Persistent Storage**: Uses **SQLite** via `aiosqlite` for task tracking, activity logging, and AI audit history.

## Technology Stack
- **FastAPI**: Main web framework.
- **Uvicorn**: ASGI server.
- **Ollama Client**: Custom async client for local AI models (Qwen, DeepSeek, etc.).
- **Pydantic**: Data validation and settings management.
- **WebSockets**: Real-time streaming for AI chat and terminal output.
- **SQLite**: lightweight database for agents and logs.

## Getting Started

### Prerequisites
1. **Python 3.10+** installed on your system.
2. **Ollama** installed and running locally.
3. (Optional) **Tesseract OCR** installed for screen-reading features.

### Installation & Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   ```powershell
   cp .env.example .env
   # Edit .env and update ALLOWED_WORKSPACE_ROOTS
   ```

### Running the Backend
1. **Start the FastAPI Server**:
   ```bash
   python run.py
   ```
   The server will start at `http://localhost:8000`.
   Interactive API documentation is available at `http://localhost:8000/docs`.

2. **Start the Background Agent (Optional)**:
   ```bash
   python agent_daemon.py
   ```
   This runs the voice listener and periodic task reminders.

## API Modules
- `/api/chat`: AI chat and code generation.
- `/api/files`: File system CRUD and search.
- `/api/terminal`: Command execution and output streaming.
- `/api/agent`: Autonomous multi-step agent tasks.
- `/api/system`: System control (apps, screen, voice).
