# AGENT RELIABILITY V1

This document outlines the features and architectural additions made to improve the stability and observability of the JARVIS agent.

## 1. Tool Health Manager & Startup Diagnostics
- Added `tool_health.py` to keep track of the health and availability of all core subsystems (database, ollama, browser, voice).
- Added `diagnostics.py` to verify dependencies on application startup.
- The agent loop calls `run_startup_diagnostics()` before entering its infinite loop.

## 2. Browser Recovery
- The `browser_agent.py` was updated with a `recover()` function.
- If an operation fails, or if a manual closure of the browser is detected (`self._page.is_closed()`), the agent safely tears down the remaining Playwright structures and attempts to recreate the context organically without crashing the main application thread.

## 3. Retry Framework
- An `@async_retry` decorator was added to `utils/retry.py`.
- It supports exponential backoff (`initial_backoff`, `max_retries`) and is applied directly to network-sensitive browser operations like `goto_url`, `search_web`, `click_element`, and `fill_input`.

## 4. Persistent Task Checkpoints
- `app/database/db.py` received a new SQLite table: `task_checkpoints`.
- Both `job_agent.py` and `application_agent.py` use `save_task_checkpoint` to document exactly what stage they are at (e.g. "searching", "extracting", "opened", "uploading").
- If the daemon crashes and reboots, this table provides a verifiable trail of what task states were abandoned.

## 5. Structured Logging & Exception Handling
- `utils/logger.py` was enhanced to write out valid JSON Lines (`backend.jsonl`) via a custom `StructuredJSONFormatter`.
- This ensures all backend logs include exact timestamps, modules, log levels, and optional metadata like `task_id` or `duration_ms` for indexing.

## 6. Performance Monitoring
- `utils/performance.py` tracks the elapsed execution time for:
  - `planning_times_ms`
  - `tool_execution_times_ms`
  - `llm_response_times_ms`
- The system averages these out over a moving window of 1000 items and outputs a lightweight JSON report every 10 execution loops (`logs/performance_report.json`).

## Testing Instructions
1. Run `python run.py`. You should immediately see the startup diagnostics console logs identifying component availability.
2. Manually kill the Chromium window while a task is running.
3. Observe the `backend.jsonl` file to see structured error reports, followed by the Retry Framework catching the exception, and the Browser Agent executing its `recover()` loop to bring the window back up seamlessly.