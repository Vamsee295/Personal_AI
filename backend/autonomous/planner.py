"""
planner.py – Maps the AI's natural language thought into a discrete, actionable system command.
"""

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
            "name": "vision_capture",
            "description": "Capture the screen for the Vision Agent to analyze.",
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
            "name": "vision_ocr",
            "description": "Extract raw text from the screen using OCR.",
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
            "name": "vision_analyze",
            "description": "Analyze the screen with the Vision Agent to find UI elements, buttons, or inputs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "What you want to find or understand (e.g. 'find login button')."}
                },
                "required": ["goal"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "vision_read_error",
            "description": "Analyze the screen specifically to read and extract error dialogs or tracebacks.",
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
            "name": "vision_describe_screen",
            "description": "Get a description and summary of the current visible screen/window.",
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
            "name": "type_text",
            "description": "Type text on the keyboard (e.g., into an active desktop application window).",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The text to type."}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a specific key or key combination on the keyboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "combo": {"type": "string", "description": "The key combo to press (e.g. 'enter', 'ctrl+c', 'win+d', 'alt+tab')."}
                },
                "required": ["combo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mouse_click",
            "description": "Click the mouse at specific screen coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate."},
                    "y": {"type": "integer", "description": "Y coordinate."},
                    "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Which mouse button to click."}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_mouse",
            "description": "Move the mouse to specific screen coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate."},
                    "y": {"type": "integer", "description": "Y coordinate."}
                },
                "required": ["x", "y"]
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
            "description": "Take a screenshot of the current screen to analyze it.",
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
            "name": "scroll_desktop",
            "description": "Scroll the desktop mouse wheel up or down.",
            "parameters": {
                "type": "object",
                "properties": {
                    "clicks": {"type": "integer", "description": "Number of clicks to scroll. Positive is usually up, negative is down."}
                },
                "required": ["clicks"]
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
            "description": "Perform an action related to filling out, reviewing, and submitting a job application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "enum": ["open", "upload_resume", "get_details", "review", "submit"], "description": "The application action to perform."},
                    "url": {"type": "string", "description": "The URL to open (if action_type is 'open')."},
                    "selector": {"type": "string", "description": "The selector to use (if action_type is 'upload_resume' or 'submit')."},
                    "company": {"type": "string", "description": "Company name (if action_type is 'review')."},
                    "role": {"type": "string", "description": "Role name (if action_type is 'review')."},
                    "fields_filled": {"type": "object", "description": "Key-value pairs of filled fields (if action_type is 'review')."},
                    "missing_fields": {"type": "array", "items": {"type": "string"}, "description": "List of missing fields (if action_type is 'review')."},
                    "application_id": {"type": "integer", "description": "The application ID to submit (if action_type is 'submit')."}
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
    },
    {
        "type": "function",
        "function": {
            "name": "file_action",
            "description": "Perform intelligent file operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "enum": ["organise", "undo", "analyze"], "description": "The file action to perform."},
                    "path": {"type": "string", "description": "The directory to organise or the specific file to analyze."}
                },
                "required": ["action_type"]
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
        if name in ["search_web", "open_page", "click_element", "fill_form", "extract_page", "search_jobs", "application_action", "youtube_action", "scroll_page", "summarize_page", "download_file"]:
            if health.get("browser", {}).get("available"):
                available.append(tool)
        elif name.startswith("vision_"):
            if health.get("vision", {}).get("available", True):
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
