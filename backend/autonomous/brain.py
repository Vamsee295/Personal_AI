"""
brain.py – The core reasoning engine for the autonomous agent.
"""

from app.services.ai_service import ai_service
from app.utils.logger import get_logger

logger = get_logger("brain")

from typing import Any, List, Dict
from autonomous.planner import TOOLS_SCHEMA

from app.services.memory_manager import memory_manager
import json

async def think(context: str, action_history: List[Dict[str, str]] = None, model: str = "qwen2.5-coder:7b") -> Any:
    """
    Given environmental context and action history, ask the AI to decide
    what action it should take using native tool calling. Integrates long term memory.
    """
    logger.info("Brain is thinking about the current context...")
    
    # 1. Fetch long-term context from Memory Manager
    user_profile = memory_manager.load_user_profile()
    user_prefs = await memory_manager.search_memory()
    job_history = await memory_manager.get_recent_job_history(limit=5)
    task_history = await memory_manager.get_recent_task_history(limit=5)

    history_str = ""
    if action_history:
        history_str = "\nRecent actions (Short-term context):\n"
        for act in action_history:
            history_str += f"- Action: {act.get('action')} | Result: {act.get('result')}\n"

    prompt = f"""
    You are JARVIS, an autonomous browser and desktop assistant.

    You must accomplish tasks by calling the provided tools.
    You can navigate the browser, click elements, read the page, fill inputs, search for jobs, and prepare applications.

    [LONG TERM MEMORY]
    User Profile: {json.dumps(user_profile)}
    User Preferences: {json.dumps(user_prefs)}
    Recent Job Applications: {json.dumps(job_history)}
    Recent Past Tasks: {json.dumps(task_history)}

    {history_str}

    Current environmental context (Screen/Browser Text):
    ---
    {context[:3000]}
    ---

    Based ONLY on the text and history above, decide what tool to call next.
    If you are done, or no action is needed, call `log_thought` with "Task complete" or similar.
    """

    try:
        # Use our existing ai_service to query Ollama with tools
        response = await ai_service.chat(
            message=prompt,
            history=[],
            model=model,
            tools=TOOLS_SCHEMA
        )
        logger.debug("Brain thought: %s", response)
        return response
    except Exception as e:
        logger.error("Brain failed to think: %s", e)
        return "error"
