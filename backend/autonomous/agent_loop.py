"""
agent_loop.py – The main autonomous observation-action loop.
Run directly with `python run_agent.py` or `python -m autonomous.agent_loop`
"""

import asyncio
import sys
from pathlib import Path

# Fix relative imports when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.screen_agent import screen_agent
from autonomous.brain import think
from autonomous.planner import plan
from autonomous.executor import execute_plan
from app.utils.logger import get_logger

logger = get_logger("agent_loop")

async def run_autonomous_loop():
    """
    Infinite loop:
      1. Observe screen (OCR)
      2. Think (LLM decides what's needed)
      3. Plan (Maps thought to discrete action)
      4. Execute (Runs action)
    """
    logger.info("🚀 Starting Autonomous Agent Loop...")
    
    # Keeping track of what it saw last to avoid spamming the same thought
    last_context = ""
    
    while True:
        try:
            # 1. Observe (Read screen)
            logger.debug("Observing screen...")
            # We run OCR in a thread to not block standard asyncio execution
            screen_text = await asyncio.to_thread(screen_agent.extract_text)
            
            # Simple deduplication so it doesn't think about the exact same screen endlessly
            if screen_text == last_context:
                await asyncio.sleep(5)
                continue
                
            last_context = screen_text

            if screen_text.strip():
                # 2. Think
                ai_thought = await think(screen_text)
                
                # 3. Plan
                action_plan = plan(ai_thought)
                
                # 4. Execute
                result = await execute_plan(action_plan)
                
                logger.info("Agent Step Complete | Plan: %s | Result: %s", action_plan.get('action'), result)
            else:
                logger.debug("No text detected on screen.")
                
        except Exception as e:
            logger.error("Agent Loop Error: %s", e)
            
        # Wait 5 seconds before next cycle
        await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(run_autonomous_loop())
    except KeyboardInterrupt:
        logger.info("Agent Loop stopped by user.")
