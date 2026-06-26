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
from autonomous.brain import think, brain_manager
from autonomous.planner import plan
from autonomous.executor import execute_plan
from app.utils.logger import get_logger
from app.events.stream import event_stream
import uuid

logger = get_logger("agent_loop")

orchestrator_queue = None
main_event_loop = None

def get_orchestrator_queue():
    global orchestrator_queue
    if orchestrator_queue is None:
        orchestrator_queue = asyncio.Queue()
    return orchestrator_queue

# Alias for backward compatibility if any modules rely on voice_command_queue name temporarily
def get_voice_queue():
    return get_orchestrator_queue()

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

    
    from app.utils.performance import performance_monitor
    import time
    
    # Optional fallback/default task if none is active
    current_task_id = None
    error_feedback = None

    while True:
        try:

            queue = get_orchestrator_queue()

            # Check for new commands from the API or Voice
            if not queue.empty():
                item = await queue.get()
                
                if isinstance(item, dict) and "command" in item:
                    command = item["command"]
                    task_id = item.get("task_id", str(uuid.uuid4()))
                    source = item.get("source", "unknown")
                    logger.info(f"Received new command from {source}: {command}")

                    # Create new context in Brain
                    brain_manager.create_context(task_id, command)
                    current_task_id = task_id
                    error_feedback = None
                    queue.task_done()

                    # Immediately loop to start executing this new task
                    continue
                else:
                    # Backward compatibility for direct string commands from voice
                    voice_command = item
                    task_id = str(uuid.uuid4())
                    logger.info(f"Received legacy voice command: {voice_command}")
                    brain_manager.create_context(task_id, voice_command)
                    current_task_id = task_id
                    error_feedback = None
                    queue.task_done()
                    continue

            # If there's no active task, just wait
            if not current_task_id:
                await asyncio.sleep(2)
                continue
                
            ctx = brain_manager.get_context(current_task_id)
            if not ctx or ctx.is_completed:
                logger.info(f"Task {current_task_id} completed or not found. Waiting for new tasks.")
                current_task_id = None
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
            
            if combined_context.strip():
                # Emit observation event
                await event_stream.emit("observation_received", {"task_id": current_task_id, "url": browser_url})

                # 2. Think (passing history via context inside brain)
                ai_thought = await think(current_task_id, combined_context, error_feedback=error_feedback)
                
                # 3. Plan
                plan_start = time.time()
                action_plan = plan(ai_thought)
                performance_monitor.log_metric("planning_times_ms", (time.time() - plan_start) * 1000)
                
                action = action_plan.get("action")

                # Stop condition: The LLM returned 'task_completed' or 'task_failed'
                if action in ["task_completed", "task_failed"]:
                    ctx.is_completed = True
                    msg = action_plan.get("args", {}).get("summary", "Task ended.")
                    logger.info(f"Task {current_task_id} ended: {msg}")
                    await event_stream.emit(action, {"task_id": current_task_id, "message": msg})

                    # Notify voice agent if this was a voice command
                    try:
                        from voice.voice_agent import VoiceAgent
                        agent = VoiceAgent.get_instance()
                        if agent and hasattr(agent, 'on_task_completed'):
                            agent.on_task_completed(current_task_id, success=(action == "task_completed"), message=msg)
                    except Exception:
                        pass

                    current_task_id = None
                    continue

                if action != "none":
                    await event_stream.emit("tool_selected", {"task_id": current_task_id, "tool": action, "args": action_plan.get("args")})

                # 4. Execute
                exec_start = time.time()

                try:
                    await event_stream.emit("tool_started", {"task_id": current_task_id, "tool": action})
                    result = await execute_plan(action_plan)
                    success = True
                    if isinstance(result, dict) and result.get("error"):
                        success = False
                    elif "error" in str(result).lower() or "failed" in str(result).lower():
                        success = False
                except Exception as e:
                    result = str(e)
                    success = False

                performance_monitor.log_metric("tool_execution_times_ms", (time.time() - exec_start) * 1000)
                
                logger.info("Agent Step Complete | Plan: %s | Result: %s", action, result)
                await event_stream.emit("tool_finished", {"task_id": current_task_id, "tool": action, "result": str(result), "success": success})
                
                # Update History
                ctx.log_action(action, result, success)

                # Feedback loop logic
                if not success:
                    error_feedback = str(result)
                    ctx.retry_count += 1

                    if ctx.retry_count > ctx.max_retries:
                        logger.error(f"Task {current_task_id} failed after {ctx.max_retries} retries.")
                        await event_stream.emit("task_failed", {"task_id": current_task_id, "error": "Max retries exceeded."})
                        ctx.is_completed = True

                        try:
                            from voice.voice_agent import VoiceAgent
                            agent = VoiceAgent.get_instance()
                            if agent and hasattr(agent, 'on_task_completed'):
                                agent.on_task_completed(current_task_id, success=False, message="Max retries exceeded.")
                        except Exception:
                            pass

                        current_task_id = None
                        error_feedback = None
                    else:
                        logger.warning(f"Task {current_task_id} action failed. Re-planning (retry {ctx.retry_count}/{ctx.max_retries})")
                        await event_stream.emit("replanning_started", {"task_id": current_task_id, "reason": error_feedback})
                else:
                    # Reset retries and error feedback on success
                    error_feedback = None
                    ctx.retry_count = 0

                # Trigger report generation occasionally
                if len(ctx.action_history) > 0 and len(ctx.action_history) % 10 == 0:
                    performance_monitor.generate_report()

                # Immediately replan if the agent performed an actionable task
                if action not in ["none", "log_thought"]:
                    logger.debug("Action performed. Looping immediately for next observation.")
                    continue

            else:
                logger.debug("No text detected on screen or browser.")
                await asyncio.sleep(2)
                
        except Exception as e:
            logger.error("Agent Loop Error: %s", e)
            await asyncio.sleep(5)
            
        # Periodically trigger preference learning (if history is populated)
        try:
            if current_task_id:
                ctx = brain_manager.get_context(current_task_id)
                if ctx and len(ctx.action_history) > 5 and len(ctx.action_history) % 5 == 0:
                    from app.services.memory_manager import memory_manager
                    await memory_manager.learn_preferences(ctx.action_history)
        except Exception as e:
            logger.error("Preference Learning Error: %s", e)

if __name__ == "__main__":
    try:
        asyncio.run(run_autonomous_loop())
    except KeyboardInterrupt:
        logger.info("Agent Loop stopped by user.")
