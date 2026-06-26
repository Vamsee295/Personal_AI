# Performance & Bottlenecks

- **LLM Inference / Planner**: `app.utils.performance.PerformanceMonitor` has been hooked into the loop. Initial observations from earlier sprints show planning taking ~1.2 - 2.5s locally depending on Ollama chunk loading.
- **Desktop Actions**: Extremely fast (~150ms).
- **Browser Automation**: Heavily network IO bound. Page load + wait constraints set it to ~3-4s per `open_page` request.
- **WebSocket Throughput**: <20ms over local loopback. Events are flushed instantly to Next.js.
