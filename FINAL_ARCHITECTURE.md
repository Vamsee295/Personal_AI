# Final Architecture V1

## Component Layout
```text
[ User Voice / Web Interface ] --> (FastAPI Router)
                                        |
                                [ Orchestrator Queue ]
                                        |
                                [ Agent Loop (Brain) ] <--> (Memory Manager / SQLite)
                                        |
                            +-----------+-----------+
                            |                       |
                    (Observe Stage)            (Plan Stage)
                Screen Agent + Browser       Ollama (qwen2.5-coder:7b)
                            |                       |
                            +-----------+-----------+
                                        |
                                (Execute Stage)
                            [ Action Executor ]
                                        |
                    +-----------+-------+-------+-----------+
                    |           |               |           |
            Playwright    PyAutoGUI      Vision/File    System
            (Web UI)      (Desktop UI)   (Analysis)     (File IO)
```

## Key Mechanisms
1. **Event Stream (`event_stream.py`)**: Asynchronously publishes execution stages (`task_started`, `tool_selected`, `tool_finished`, `task_failed`) over WebSocket (`/ws/orchestrator`) to the Next.js `ExecutionTimeline`.
2. **Observe -> Replan**: The Loop forces an observation of screen/DOM *before* making the next tool choice. If a tool fails (e.g. missing UI element), the retry loop catches it and feeds the error explicitly into the next LLM prompt context to self-correct.
3. **Structured Tools**: Tool schemas enforced through generic mappings (e.g. `open_app`, `type_text`, `open_page`) removing tight-coupling to individual platforms.
