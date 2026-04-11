"""
planner.py – Maps the AI's natural language thought into a discrete, actionable system command.
"""

import json
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger("planner")

def plan(ai_response: str) -> Dict[str, Any]:
    """
    Parses the raw reasoning text from the Brain and maps it to specific 
    functional commands the Executor understands.
    
    Returns a dictionary like: 
    {"action": "open_vscode", "args": ...}
    """
    response_lower = ai_response.lower()
    
    # 1. Do Nothing
    if "none" in response_lower or "no action required" in response_lower:
        return {"action": "none"}
        
    # 2. Open Apps
    if "open vscode" in response_lower or "open code" in response_lower:
        return {"action": "open_app", "args": {"app_name": "code"}}
        
    if "open chrome" in response_lower or "open browser" in response_lower:
        return {"action": "open_app", "args": {"app_name": "chrome"}}

    # 3. File Tasks
    if "organize downloads" in response_lower or "organise downloads" in response_lower:
        # We can dynamically resolve the Downloads folder logic inside the executor
        return {"action": "organize_files", "args": {"target": "downloads"}}

    # 4. Error explanations
    if "explain error" in response_lower or "error" in response_lower or "exception" in response_lower:
        # Assuming the AI response itself contains the explanation or context of the error
        return {"action": "explain_error", "args": {"context": ai_response}}

    # Fallback to general chat / log thought
    return {"action": "log_thought", "args": {"thought": ai_response}}
