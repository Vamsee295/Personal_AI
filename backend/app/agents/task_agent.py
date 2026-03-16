"""
agents/task_agent.py – Manages task creation, tracking, and status updates via the database.
"""

from __future__ import annotations
from typing import List, Optional

from app.database.db import create_task, list_tasks, update_task_status
from app.utils.logger import get_logger

logger = get_logger("task_agent")


class TaskAgent:
    """High-level wrapper around the task database helpers."""

    async def add(self, title: str, description: str = "", priority: int = 3) -> int:
        task_id = await create_task(title, description, priority)
        logger.info("Task created: [%d] %s", task_id, title)
        return task_id

    async def get_all(self, status: Optional[str] = None) -> List[dict]:
        return await list_tasks(status)

    async def mark_done(self, task_id: int) -> None:
        await update_task_status(task_id, "done")
        logger.info("Task %d → done", task_id)

    async def mark_in_progress(self, task_id: int) -> None:
        await update_task_status(task_id, "in_progress")

    async def mark_failed(self, task_id: int) -> None:
        await update_task_status(task_id, "failed")


# Module-level singleton
task_agent = TaskAgent()

