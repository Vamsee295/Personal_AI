"""
planner.py – Maps the AI's natural language thought into a discrete, actionable system command.
"""

import json
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger("planner")

# Define tools schema for Ollama native tool calling
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open a desktop application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Name of the application to open (e.g., 'code', 'chrome', 'calculator')."}
                },
                "required": ["app_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "navigate_browser",
            "description": "Navigate to a specific URL in the browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to navigate to (e.g., 'https://linkedin.com')."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_click",
            "description": "Click an element on the current webpage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "The text or CSS selector of the element to click."}
                },
                "required": ["selector"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_fill",
            "description": "Fill a text input on the current webpage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "The text or CSS selector of the input field."},
                    "text": {"type": "string", "description": "The text to type into the field."}
                },
                "required": ["selector", "text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_read",
            "description": "Get the text content of the current webpage.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Take a screenshot of the current browser page.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "log_thought",
            "description": "Log a thought or explain an error if no active action is needed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {"type": "string", "description": "The text to log or explain."}
                },
                "required": ["thought"]
            }
        }
    }
]

def plan(ai_response: Any) -> Dict[str, Any]:
    """
    Parses the tool-call object returned from Ollama and maps it to specific
    functional commands the Executor understands.
    """
    if isinstance(ai_response, dict) and "tool_calls" in ai_response:
        tool_call = ai_response["tool_calls"][0]
        func = tool_call.get("function", {})
        
        return {
            "action": func.get("name"),
            "args": func.get("arguments", {})
        }

    # If the AI just responded with plain text instead of a tool call
    if isinstance(ai_response, str):
        response_lower = ai_response.lower()
        if "none" in response_lower or "no action required" in response_lower:
            return {"action": "none"}
        return {"action": "log_thought", "args": {"thought": ai_response}}

    return {"action": "none"}
