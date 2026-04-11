"""
executor.py – Executes the functional commands determined by the planner.
"""

from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger("executor")

async def execute_plan(plan: Dict[str, Any]) -> str:
    """
    Takes a plan dictionary and executes the corresponding system action.
    """
    action = plan.get("action")
    args = plan.get("args", {})
    
    logger.info("Executing plan: %s", plan)

    if action == "none":
        return "No action needed."

    elif action == "open_app":
        app_name = args.get("app_name")
        if app_name == "code":
            from app.system.app_control import open_vscode
            result = open_vscode()
            return f"Opened VS Code: {result.get('success')}"
            
        elif app_name == "chrome":
            from app.system.app_control import open_browser
            result = open_browser("https://google.com")
            return f"Opened Chrome: {result.get('success')}"
            
        else:
            from app.system.app_control import open_app as open_generic_app
            result = open_generic_app(app_name)
            return f"Opened {app_name}: {result.get('success')}"

    elif action == "organize_files":
        target = args.get("target")
        if target == "downloads":
            # Just an example path. A real system might use pathlib Path.home() / "Downloads"
            import os
            downloads_dir = os.path.expanduser("~/Downloads")
            from app.agents.file_agent import file_agent
            actions = file_agent.organise(downloads_dir, dry_run=False)
            return f"Organized {len(actions)} files in Downloads."
        return "Target directory not recognized."

    elif action == "explain_error":
        context = args.get("context", "")
        # Here we could format and log this, or send to a UI websocket.
        # For a headless agent, logging the AI's explanation is typically what it does.
        logger.info("Agent Error Explanation:\n%s", context)
        return "Explained error in logs."

    elif action == "log_thought":
        thought = args.get("thought", "")
        logger.info("Agent generic thought:\n%s", thought)
        return "Logged thought."

    else:
        logger.warning("Unknown action in plan: %s", action)
        return "Unknown action."
