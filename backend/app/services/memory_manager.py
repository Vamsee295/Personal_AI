"""
services/memory_manager.py -- Agent Memory Management.
Handles user preferences, long-term recall, and automatic preference learning.
"""

from __future__ import annotations
import json
import logging
from typing import Dict, Any, List
import aiosqlite
from pathlib import Path

from app.database.db import DB_PATH
from app.services.ai_service import ai_service

logger = logging.getLogger("memory_manager")

class MemoryManager:
    """Manages long-term context, preferences, and task histories for JARVIS."""
    
    def __init__(self):
        self.profile_path = Path(__file__).resolve().parent.parent.parent / "memory" / "user_profile.json"

    async def save_memory(self, key: str, value: str) -> None:
        """Save a user preference key-value pair to SQLite."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT OR REPLACE INTO user_preferences (key, value) VALUES (?, ?)",
                (key, value)
            )
            await db.commit()
            
    async def load_memory(self, key: str) -> str | None:
        """Load a specific memory key."""
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row[0] if row else None

    async def search_memory(self) -> Dict[str, str]:
        """Fetch all user preferences."""
        prefs = {}
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT key, value FROM user_preferences")
            rows = await cursor.fetchall()
            for r in rows:
                prefs[r[0]] = r[1]
        return prefs

    async def update_memory(self, key: str, value: str) -> None:
        """Alias for save_memory."""
        await self.save_memory(key, value)

    def load_user_profile(self) -> Dict[str, Any]:
        """Load static user profile JSON."""
        if self.profile_path.exists():
            try:
                with open(self.profile_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load user profile: {e}")
        return {}

    async def get_recent_job_history(self, limit: int = 5) -> List[Dict[str, str]]:
        """Fetch recent job applications/statuses."""
        history = []
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT company, role, status FROM job_history ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            for r in rows:
                history.append({"company": r[0], "role": r[1], "status": r[2]})
        return history

    async def get_recent_task_history(self, limit: int = 5) -> List[Dict[str, str]]:
        """Fetch recent autonomous tasks completed."""
        history = []
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT task, result FROM task_history ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = await cursor.fetchall()
            for r in rows:
                history.append({"task": r[0], "result": r[1]})
        return history

    async def learn_preferences(self, action_history: List[Dict[str, Any]]) -> None:
        """
        Analyze a list of recent actions to infer if the user has repeated preferences.
        E.g. repeatedly searching "Remote React Frontend".
        """
        if not action_history:
            return

        actions_str = json.dumps(action_history, indent=2)
        prompt = f"""
        Analyze the following recent actions taken by the user or the agent.
        Identify any recurring preferences, keywords, or requirements (e.g. they always search for 'Remote' or 'React', or prefer 'Frontend' roles).
        Return ONLY a JSON dictionary of key-value pairs representing these preferences. 
        If nothing obvious stands out, return an empty dictionary {{}}.
        
        Actions:
        {actions_str}
        """

        try:
            result_str = await ai_service.chat(message=prompt, history=[])
            if isinstance(result_str, dict):
                result_str = result_str.get("content", "{}")

            import re
            match = re.search(r"\{.*\}", result_str, re.DOTALL)
            if match:
                prefs = json.loads(match.group(0))
                for k, v in prefs.items():
                    # We save the learned preference
                    await self.save_memory(f"learned_pref_{k}", str(v))
                    logger.info(f"Learned new preference: {k} = {v}")
        except Exception as e:
            logger.error(f"Failed to learn preferences: {e}")

memory_manager = MemoryManager()
