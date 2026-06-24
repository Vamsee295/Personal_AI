"""
database/db.py – SQLite database with aiosqlite for async access.

Tables:
  - tasks:       user tasks tracked by the AI agent
  - ai_logs:     AI request/response audit log
  - activity:    user activity timeline
  - files_history: file modifications made by the AI
"""

from __future__ import annotations
import aiosqlite
from pathlib import Path
from app.utils.logger import get_logger

logger = get_logger("db")

DB_PATH = Path("ultron.db")


# ══════════════════════════════════════════════════════════════════
#  Schema creation
# ══════════════════════════════════════════════════════════════════

CREATE_TASKS = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT DEFAULT 'pending',   -- pending | in_progress | done | failed
    priority    INTEGER DEFAULT 3,         -- 1=high, 3=low
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_AI_LOGS = """
CREATE TABLE IF NOT EXISTS ai_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    model       TEXT,
    prompt      TEXT,
    response    TEXT,
    tokens      INTEGER,
    duration_ms INTEGER,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_ACTIVITY = """
CREATE TABLE IF NOT EXISTS activity (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action      TEXT NOT NULL,
    details     TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_FILES_HISTORY = """
CREATE TABLE IF NOT EXISTS files_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path   TEXT NOT NULL,
    action      TEXT NOT NULL,   -- read | write | create | delete
    old_content TEXT,
    new_content TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_JOB_SEARCH_HISTORY = """
CREATE TABLE IF NOT EXISTS job_search_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    company     TEXT,
    location    TEXT,
    salary      TEXT,
    skills      TEXT,
    url         TEXT,
    source      TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_SAVED_JOBS = """
CREATE TABLE IF NOT EXISTS saved_jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    company     TEXT,
    location    TEXT,
    salary      TEXT,
    skills      TEXT,
    url         TEXT,
    source      TEXT,
    score       REAL DEFAULT 0.0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_JOB_APPLICATION_HISTORY = """
CREATE TABLE IF NOT EXISTS job_application_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      INTEGER,
    title       TEXT NOT NULL,
    company     TEXT,
    url         TEXT,
    status      TEXT DEFAULT 'pending',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_PENDING_APPLICATIONS = """
CREATE TABLE IF NOT EXISTS pending_applications (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company     TEXT NOT NULL,
    role        TEXT NOT NULL,
    status      TEXT DEFAULT 'prepared', -- prepared | approved | submitted | failed
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_USER_PREFERENCES = """
CREATE TABLE IF NOT EXISTS user_preferences (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT UNIQUE NOT NULL,
    value       TEXT NOT NULL
);
"""

CREATE_JOB_HISTORY = """
CREATE TABLE IF NOT EXISTS job_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company     TEXT NOT NULL,
    role        TEXT NOT NULL,
    status      TEXT NOT NULL,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_TASK_HISTORY = """
CREATE TABLE IF NOT EXISTS task_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task        TEXT NOT NULL,
    result      TEXT NOT NULL,
    timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""

async def init_db() -> None:
    """Create all tables if they do not exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TASKS)
        await db.execute(CREATE_AI_LOGS)
        await db.execute(CREATE_ACTIVITY)
        await db.execute(CREATE_FILES_HISTORY)
        await db.execute(CREATE_JOB_SEARCH_HISTORY)
        await db.execute(CREATE_SAVED_JOBS)
        await db.execute(CREATE_JOB_APPLICATION_HISTORY)
        await db.execute(CREATE_PENDING_APPLICATIONS)
        await db.execute(CREATE_USER_PREFERENCES)
        await db.execute(CREATE_JOB_HISTORY)
        await db.execute(CREATE_TASK_HISTORY)
        await db.commit()
    logger.info("Database initialised at %s", DB_PATH.resolve())


# ══════════════════════════════════════════════════════════════════
#  Task helpers
# ══════════════════════════════════════════════════════════════════

async def create_task(title: str, description: str = "", priority: int = 3) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tasks (title, description, priority) VALUES (?, ?, ?)",
            (title, description, priority),
        )
        await db.commit()
        return cursor.lastrowid

async def create_pending_application(company: str, role: str, status: str = 'prepared') -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO pending_applications (company, role, status) VALUES (?, ?, ?)",
            (company, role, status),
        )
        await db.commit()
        return cursor.lastrowid

async def update_pending_application_status(app_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE pending_applications SET status = ?, timestamp = CURRENT_TIMESTAMP WHERE id = ?",
            (status, app_id),
        )
        await db.commit()

async def log_job_history(company: str, role: str, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO job_history (company, role, status) VALUES (?, ?, ?)",
            (company, role, status),
        )
        await db.commit()

async def log_task_history(task: str, result: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO task_history (task, result) VALUES (?, ?)",
            (task, result),
        )
        await db.commit()


async def list_tasks(status: str | None = None) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if status:
            cursor = await db.execute("SELECT * FROM tasks WHERE status=? ORDER BY priority, created_at", (status,))
        else:
            cursor = await db.execute("SELECT * FROM tasks ORDER BY priority, created_at")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def update_task_status(task_id: int, status: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE tasks SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, task_id),
        )
        await db.commit()


# ══════════════════════════════════════════════════════════════════
#  AI log helpers
# ══════════════════════════════════════════════════════════════════

async def log_ai_interaction(
    model: str,
    prompt: str,
    response: str,
    tokens: int = 0,
    duration_ms: int = 0,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO ai_logs (model, prompt, response, tokens, duration_ms) VALUES (?,?,?,?,?)",
            (model, prompt, response, tokens, duration_ms),
        )
        await db.commit()


# ══════════════════════════════════════════════════════════════════
#  Activity helpers
# ══════════════════════════════════════════════════════════════════

async def log_activity(action: str, details: str = "") -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO activity (action, details) VALUES (?, ?)",
            (action, details),
        )
        await db.commit()

# ══════════════════════════════════════════════════════════════════
#  Job Agent helpers
# ══════════════════════════════════════════════════════════════════

import json

async def log_job_search(title: str, company: str, location: str, salary: str, skills: list[str], url: str, source: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        skills_str = json.dumps(skills)
        cursor = await db.execute(
            "INSERT INTO job_search_history (title, company, location, salary, skills, url, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (title, company, location, salary, skills_str, url, source),
        )
        await db.commit()
        return cursor.lastrowid

async def save_job(title: str, company: str, location: str, salary: str, skills: list[str], url: str, source: str, score: float = 0.0) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        skills_str = json.dumps(skills)
        cursor = await db.execute(
            "INSERT INTO saved_jobs (title, company, location, salary, skills, url, source, score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (title, company, location, salary, skills_str, url, source, score),
        )
        await db.commit()
        return cursor.lastrowid

async def log_job_application(job_id: int, title: str, company: str, url: str, status: str = 'pending') -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO job_application_history (job_id, title, company, url, status) VALUES (?, ?, ?, ?, ?)",
            (job_id, title, company, url, status),
        )
        await db.commit()
        return cursor.lastrowid
