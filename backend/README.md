# 🧠 Ultron – Backend

A high-performance, modular Intelligence Engine built with **Python** and **FastAPI**. It serves as the core "brain" for the Ultron IDE, orchestrating LLM communication and system automation.

## 🚀 Tech Stack
- **Framework:** FastAPI (Asynchronous Python)
- **AI Integration:** Ollama (Local LLM Execution)
- **Automation:** Custom Agent Engine for file, terminal, and system tasks.
- **Database:** SQLite (via `aiosqlite`) for task persistence.
- **Networking:** WebSockets for real-time streaming and Pydantic for validation.

## 🛠️ How It Works
The backend operates as a central bridge between the **Frontend UI** and **Local Intelligence**:
1. **Chat & Planning:** Processes natural language via Ollama and uses a `Planner` to map intent to actionable system commands.
2. **Autonomous Agent:** Executes multi-step workflows (e.g., "organize my downloads" or "fix this error") by piping AI thoughts into localized system tools.
3. **System Access:** Safely manages file CRUD, terminal execution, and screen monitoring within an isolated workspace.

---

## 🏗️ Installation

### 1. Prerequisites
- **Python 3.10+**
- **Ollama** (Running locally with `qwen2.5-coder` or similar)

### 2. Setup Commands
Run these in the `backend` directory:

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```
> [!NOTE]
> Edit `.env` to set your `ALLOWED_WORKSPACE_ROOTS`.

---

## ⚡ Running the Backend

### Start API Server
The main server handles all UI requests and AI orchestration.
```bash
python run.py
```
*API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)*

### Start Agent Daemon (Optional)
Runs background services like voice listening and periodic system tasks.
```bash
python agent_daemon.py
```
