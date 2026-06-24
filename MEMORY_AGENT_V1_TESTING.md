# MEMORY AGENT V1 TESTING

This document outlines tests for verifying the long-term memory integrations in the JARVIS system, specifically focusing on user preferences, task history continuation, and automatic learning.

## 1. Memory Recall Tests

**Prerequisites:**
- `user_preferences` table in `ultron.db` must have data, or `memory/user_profile.json` must exist.
- E.g., `user_profile.json` has `{"skills": ["React", "Python"]}`.

**Prompt:**
> "What are my primary skills?"

**Expected Behavior:**
1. The `agent_loop.py` captures the browser/screen state and asks `brain.py` to think.
2. `brain.py` pulls `user_profile` via `memory_manager` and embeds it in the system prompt.
3. The LLM correctly identifies the skills without searching the web.
4. The agent outputs the answer using `log_thought`.

## 2. Task Continuation Tests

**Prerequisites:**
- The agent successfully executed a task previously, which was saved to `task_history` (e.g. "Logged thought: Applied to 3 Google jobs").

**Prompt:**
> "What was the last company I applied to?"

**Expected Behavior:**
1. `brain.py` pulls recent tasks (`task_history`) and applications (`job_history`) via `memory_manager`.
2. The LLM receives `[LONG TERM MEMORY]` containing `[{"company": "Google", "role": "Frontend", "status": "prepared"}]`.
3. The LLM answers "Google" using `log_thought` without needing to re-check the browser or active memory list.

## 3. Preference Learning Tests

**Trigger Context:**
- The user uses voice or prompts repeatedly indicating a preference. E.g.
  Action 1: `search_jobs(platform="linkedin", query="Remote Python")`
  Action 2: `search_web(query="Remote Python jobs")`
  Action 3: `search_jobs(platform="wellfound", query="Remote Python intern")`

**Expected Behavior:**
1. Once the `action_history` length hits intervals of 5, the `agent_loop.py` triggers `memory_manager.learn_preferences(action_history)`.
2. The `ai_service` processes the last 5 actions and identifies the keyword trend: "Remote" and "Python".
3. The LLM returns a JSON object like `{"location_preference": "Remote", "language_preference": "Python"}`.
4. `memory_manager.save_memory()` writes these keys to the SQLite `user_preferences` table.
5. In subsequent loops, `brain.py` automatically injects `{"location_preference": "Remote", "language_preference": "Python"}` into the `[LONG TERM MEMORY]` block, permanently altering the agent's contextual behavior without explicit configuration.

## Failure Scenarios
- **No Trend Detected:** If the 5 recent actions are random (e.g. checked weather, opened YouTube, checked time), the `learn_preferences` prompt outputs `{}`. The SQLite database remains unmodified, preventing hallucinated preferences.
- **Corrupted JSON Profile:** If `user_profile.json` is malformed, `memory_manager.load_user_profile()` returns `{}` and logs an error, ensuring the agent doesn't crash during the thinking phase.