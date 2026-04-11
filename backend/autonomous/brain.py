"""
brain.py – The core reasoning engine for the autonomous agent.
"""

from app.services.ai_service import ai_service
from app.utils.logger import get_logger

logger = get_logger("brain")

async def think(context: str, model: str = "qwen2.5-coder:7b") -> str:
    """
    Given environmental context (like screen OCR text), ask the AI to decide
    what action it should take.
    """
    logger.info("Brain is thinking about the current context...")
    
    prompt = f"""
    You are Ultron, an autonomous computing assistant.

    You have the ability to observe the user's screen and decide if any action is needed.
    You can:
    - analyze screen errors
    - open apps (e.g., vscode, chrome)
    - organize files or downloads
    - help with coding
    - do nothing if the screen looks normal

    Here is the current text extracted from the user's screen:
    ---
    {context[:3000]}
    ---

    Based ONLY on the text above, decide what action should be taken right now.
    Answer with a short, specific command or intent. 
    Examples: 
    - "explain error: NameError: x is not defined"
    - "open_vscode"
    - "organize_downloads"
    - "none" if everything is fine and no action is required.
    """

    try:
        # Use our existing ai_service to query Ollama
        response = await ai_service.chat(
            message=prompt,
            history=[],
            model=model
        )
        logger.debug("Brain thought: %s", response)
        return response.strip()
    except Exception as e:
        logger.error("Brain failed to think: %s", e)
        return "error"
