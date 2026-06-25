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

    # --- New Browser Agent Tools ---
    elif action == "search_web":
        query = args.get("query")
        from automation.browser_agent import browser_agent
        res = await browser_agent.search_web(query)
        return res.get("message") or res.get("error")

    elif action == "open_page":
        url = args.get("url")
        from automation.browser_agent import browser_agent
        res = await browser_agent.goto_url(url)
        return res.get("message") or res.get("error")

    elif action == "click_element":
        selector = args.get("selector")
        from automation.browser_agent import browser_agent
        res = await browser_agent.click_element(selector)
        return res.get("message") or res.get("error")

    elif action == "fill_form":
        selector = args.get("selector")
        text = args.get("text")
        from automation.browser_agent import browser_agent
        res = await browser_agent.fill_input(selector, text)
        return res.get("message") or res.get("error")

    elif action == "extract_page":
        from automation.browser_agent import browser_agent
        res = await browser_agent.get_page_content()
        return res.get("content") or res.get("error")

    elif action == "take_screenshot":
        from automation.browser_agent import browser_agent
        res = await browser_agent.screenshot()
        return res.get("message") or res.get("error")

    # --- Job Agent Tools ---
    elif action == "search_jobs":
        platform = args.get("platform", "").lower()
        query = args.get("query", "")
        location = args.get("location", "")
        from app.agents.job_agent import job_agent
        
        if platform == "linkedin":
            res = await job_agent.search_linkedin_jobs(query, location)
        elif platform == "internshala":
            res = await job_agent.search_internshala_jobs(query)
        elif platform == "wellfound":
            res = await job_agent.search_wellfound_jobs(query)
        elif platform == "naukri":
            res = await job_agent.search_naukri_jobs(query)
        else:
            return f"Error: Unknown job platform '{platform}'"
            
        return res.get("message") or res.get("error")
        
    # --- Application Agent Tools ---
    elif action == "application_action":
        action_type = args.get("action_type")
        from app.agents.application_agent import application_agent
        
        if action_type == "open":
            res = await application_agent.open_application(args.get("url", ""))
        elif action_type == "upload_resume":
            res = await application_agent.upload_resume(args.get("selector", ""))
        elif action_type == "get_details":
            res = await application_agent.fill_personal_details()
            return str(res.get("details", res.get("error")))
        elif action_type == "review":
            res = await application_agent.review_application(
                company=args.get("company", ""),
                role=args.get("role", ""),
                fields_filled=args.get("fields_filled", {}),
                missing_fields=args.get("missing_fields", [])
            )
        else:
            return f"Error: Unknown application action '{action_type}'"
            
        return res.get("message") or res.get("error")

    # --- YouTube Agent Tools ---
    elif action == "youtube_action":
        action_type = args.get("action_type")
        query = args.get("query", "")
        from app.agents.youtube_agent import youtube_agent
        
        if action_type == "search":
            res = await youtube_agent.search_youtube(query)
        elif action_type == "open_video":
            res = await youtube_agent.open_video(query)
        elif action_type == "play":
            res = await youtube_agent.play_video()
        elif action_type == "open_playlist":
            res = await youtube_agent.open_playlist(query)
        else:
            return f"Error: Unknown YouTube action '{action_type}'"
            
        return res.get("message") or res.get("error")
    # -------------------------------

    elif action == "score_job":
        from app.models.schemas import JobResult
        from app.services.job_scoring import job_scorer
        from app.database.db import save_job
        
        # Create a transient JobResult from args
        job = JobResult(
            title=args.get("title", "Unknown"),
            company=args.get("company", "Unknown"),
            location=args.get("location", "Unknown"),
            salary=args.get("salary", "Unknown"),
            skills=args.get("skills", []),
            url=args.get("url", ""),
            source=args.get("source", "Unknown")
        )
        
        res = await job_scorer.score_job(job)
        if res.get("success"):
            score = res.get("score", 0.0)
            reasoning = res.get("reasoning", "")
            # Save it to database if it's a good match (e.g., > 6.0)
            if score > 6.0:
                 await save_job(job.title, job.company, job.location, job.salary, job.skills, job.url, job.source, score)
            return f"Scored job {job.title} at {score}/10.0. Reasoning: {reasoning}"
        return res.get("error")

    elif action == "log_thought":
        thought = args.get("thought", "")
        logger.info("Agent generic thought:\n%s", thought)
        
        # Log to long term task history
        from app.database.db import log_task_history
        await log_task_history(task="Agent generic thought", result=thought)
        
        return f"Logged thought: {thought}"

    else:
        logger.warning("Unknown action in plan: %s", action)
        return f"Unknown action: {action}"
