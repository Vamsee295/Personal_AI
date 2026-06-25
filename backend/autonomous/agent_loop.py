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

voice_command_queue = None
main_event_loop = None

def get_voice_queue():
    global voice_command_queue
    if voice_command_queue is None:
        voice_command_queue = asyncio.Queue()
    return voice_command_queue

async def run_autonomous_loop():
    """
    Infinite loop:
      1. Observe screen (OCR / Browser Page Content)
      2. Think (LLM decides what's needed, passing history)
      3. Plan (Maps tool call to discrete action)
      4. Execute (Runs action)
    """
    global main_event_loop
    main_event_loop = asyncio.get_running_loop()
    
    from app.system.diagnostics import run_startup_diagnostics
    await run_startup_diagnostics()
    
    logger.info("🚀 Starting Autonomous Agent Loop...")
    
    # Keeping track of what it saw last to avoid spamming the same thought
    last_context = ""
    
    # Memory for multi-step execution (last 20 actions)
    action_history = []
    
    from app.utils.performance import performance_monitor
    import time
    from app.database.db import load_task_checkpoint
    
    # Recovery Task Evaluation
    # Note: Normally you'd want the UI or prompt to determine which task to resume. 
    # For now, we seed history if there's a hardcoded recent task, but realistically
    # JARVIS will rely on `task_history` DB fed into `brain.py` context to naturally pick up.
    
    while True:
        try:
            loop_start = time.time()
            queue = get_voice_queue()
            # Check for direct voice commands injected from the VoiceAgent thread
            if not queue.empty():
                voice_command = await queue.get()
                logger.info(f"Received voice command from queue: {voice_command}")
                
                from voice.voice_agent import VoiceAgent
                agent = VoiceAgent.get_instance()
                # Process the command entirely on the main event loop
                await agent.process_voice_command(voice_command)
                queue.task_done()
                continue
                
            # 1. Observe (Read screen / Browser)
            logger.debug("Observing screen and browser...")
            
            # Combine generic screen text with browser DOM text
            screen_text = await asyncio.to_thread(screen_agent.extract_text)
            
            from automation.browser_agent import browser_agent
            browser_res = await browser_agent.get_page_state()
            
            browser_url = browser_res.get("url", "None")
            browser_title = browser_res.get("title", "None")
            browser_text = browser_res.get("content", "")
            
            combined_context = (
                f"SCREEN OCR:\n{screen_text}\n\n"
                f"BROWSER STATE:\n"
                f"URL: {browser_url}\n"
                f"Title: {browser_title}\n"
                f"Content:\n{browser_text}"
            )
            
            # Simple deduplication so it doesn't think about the exact same screen endlessly
            if combined_context == last_context:
                await asyncio.sleep(5)
                continue
                
            last_context = combined_context

            if combined_context.strip():
                # 2. Think (passing history)
                ai_thought = await think(combined_context, action_history=action_history)
                
                # 3. Plan
                plan_start = time.time()
                action_plan = plan(ai_thought)
                performance_monitor.log_metric("planning_times_ms", (time.time() - plan_start) * 1000)
                
                # 4. Execute
                exec_start = time.time()
                result = await execute_plan(action_plan)
                performance_monitor.log_metric("tool_execution_times_ms", (time.time() - exec_start) * 1000)
                
                logger.info("Agent Step Complete | Plan: %s | Result: %s", action_plan.get('action'), result)
                
                # Trigger report generation occasionally
                if len(action_history) > 0 and len(action_history) % 10 == 0:
                    performance_monitor.generate_report()
                
                # Update History
                action_history.append({
                    "action": action_plan.get("action"),
                    "result": str(result)
                })
                # Keep only the last 20
                if len(action_history) > 20:
                    action_history.pop(0)

                # Immediately replan if the agent performed an actionable task
                if action_plan.get("action") not in ["none", "log_thought"]:
                    logger.debug("Action performed. Looping immediately for next observation.")
                    continue

            else:
                logger.debug("No text detected on screen or browser.")
                
        except Exception as e:
            logger.error("Agent Loop Error: %s", e)
            
        # Wait 5 seconds before next cycle (if nothing actionable happened)
        await asyncio.sleep(5)
        
        # Periodically trigger preference learning (if history is populated)
        try:
            if len(action_history) > 5 and len(action_history) % 5 == 0:
                from app.services.memory_manager import memory_manager
                await memory_manager.learn_preferences(action_history)
        except Exception as e:
            logger.error("Preference Learning Error: %s", e)

if __name__ == "__main__":
    try:
        asyncio.run(run_autonomous_loop())
    except KeyboardInterrupt:
        logger.info("Agent Loop stopped by user.")
