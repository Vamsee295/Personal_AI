# Vamsee AI – Local AI Agent & IDE

Vamsee AI is a powerful, locally-hosted AI coding assistant and system agent similar to Cursor and Antigravity IDE. It combines a sleek React/Next.js frontend with a modular FastAPI backend to provide an integrated development experience powered by local LLMs (Ollama).

## Project Structure
- **[frontend/](./frontend)**: Next.js application containing the IDE workspace, chat panel, and system control UI.
- **[backend/](./backend)**: FastAPI server managing AI communication, file system access, terminal execution, and system automation.

## Core Features
1. **AI Chat & Code Generation**: Real-time communication with local LLMs (Qwen2.5, DeepSeek, etc.) via Ollama.
2. **Sanboxed File System**: Secure read/write access to project folders with path enforcement.
3. **Integrated Terminal**: Run shell commands directly from the IDE with output streaming and security filtering.
4. **Autonomous AI Agent**: Execute multi-step tasks like debugging, refactoring, or project analysis using the Agent Engine.
5. **System Automation**:
   - **Screen AI**: Capture screen, run OCR, and analyze errors with AI.
   - **Voice Assistant**: Control your IDE and system using voice commands.
   - **File Organiser**: Automatically categorise and sort files in any directory.
   - **App Control**: Launch VS Code, browsers, and other applications seamlessly.

## Quick Start (Running the Project)

### 1. Prerequisites
- **Ollama**: [Download and Install](https://ollama.com/)
- **Python 3.10+**
- **Node.js 18+**

### 2. Start the Backend
```powershell
cd backend
# Setup environment
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env

# Run server
python run.py
```
*Backend runs at http://localhost:8000*

### 3. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```
*Frontend runs at http://localhost:3000*

## Documentation
- [Backend Documentation](./backend/README.md)
- [Frontend Documentation](./frontend/README.md)
- [Implementation Walkthrough](./.gemini/antigravity/brain/88676c32-873c-457b-968f-bef75d33418d/walkthrough.md) (Detailed Architecture)

Built with ❤️ by Vamsee.
