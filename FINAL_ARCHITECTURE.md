# Final Architecture

## The Stack
- **Frontend**: Next.js 14, React, Tailwind CSS, Shadcn UI
- **Backend**: FastAPI, Python 3.10+, SQLite
- **AI Core**: Ollama (local) using `qwen2.5-coder:7b`
- **Automation**: Playwright, PyAutoGUI

## Execution Flow
1. **User Request**: Incoming via `/api/brain/execute` or WebSocket.
2. **Action Router**: Determines if a strict rule applies (e.g. simple apps) or if it requires the LLM.
3. **LLM Planner**: If required, Ollama is invoked with a strict JSON format prompt.
4. **Executor**: Translates JSON into Python OS/Browser function calls.
5. **Memory Manager**: Persists the result into `ultron.db` for future context building.
6. **Safety Interception**: If the agent proposes a destructive command (Job Submissions), a `SAFETY HALT` is triggered before the executor can fire.
