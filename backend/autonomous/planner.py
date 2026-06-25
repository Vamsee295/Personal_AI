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
            "name": "search_web",
            "description": "Search the internet for a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_page",
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
            "name": "click_element",
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
            "name": "fill_form",
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
            "name": "extract_page",
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
    },
    {
        "type": "function",
        "function": {
            "name": "search_jobs",
            "description": "Search for jobs on specific platforms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "enum": ["linkedin", "internshala", "wellfound", "naukri"], "description": "The job board to search on."},
                    "query": {"type": "string", "description": "The job title or keyword to search for."},
                    "location": {"type": "string", "description": "The location to search in (only used for linkedin currently)."}
                },
                "required": ["platform", "query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "application_action",
            "description": "Perform an action related to filling out and reviewing a job application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "enum": ["open", "upload_resume", "get_details", "review"], "description": "The application action to perform."},
                    "url": {"type": "string", "description": "The URL to open (if action_type is 'open')."},
                    "selector": {"type": "string", "description": "The file input selector (if action_type is 'upload_resume')."},
                    "company": {"type": "string", "description": "Company name (if action_type is 'review')."},
                    "role": {"type": "string", "description": "Role name (if action_type is 'review')."},
                    "fields_filled": {"type": "object", "description": "Key-value pairs of filled fields (if action_type is 'review')."},
                    "missing_fields": {"type": "array", "items": {"type": "string"}, "description": "List of missing fields (if action_type is 'review')."}
                },
                "required": ["action_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_action",
            "description": "Perform an action on YouTube.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "enum": ["search", "open_video", "play", "open_playlist"], "description": "The action to perform on YouTube."},
                    "query": {"type": "string", "description": "The search query or URL/ID to open."}
                },
                "required": ["action_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "score_job",
            "description": "Score a job based on the user's resume and profile.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Job title."},
                    "company": {"type": "string", "description": "Company name."},
                    "location": {"type": "string", "description": "Job location."},
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Required skills for the job."
                    }
                },
                "required": ["title", "company"]
            }
        }
    }
]

def get_available_tools() -> list:
    """Filter TOOLS_SCHEMA based on tool_health."""
    from app.services.tool_health import tool_health
    health = tool_health.get_health()
    available = []

    for tool in TOOLS_SCHEMA:
        name = tool["function"]["name"]

        # Check browser tools
        if name in ["search_web", "open_page", "click_element", "fill_form", "extract_page", "search_jobs", "application_action", "youtube_action"]:
            if health.get("browser", {}).get("available"):
                available.append(tool)
        # Assuming log_thought and score_job only require Ollama/Memory, which are implicitly checked if this code runs
        else:
            available.append(tool)

    return available

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
