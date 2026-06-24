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
    elif action == "navigate_browser":
        url = args.get("url")
        from automation.browser_agent import browser_agent
        res = await browser_agent.goto_url(url)
        return res.get("message") or res.get("error")

    elif action == "browser_click":
        selector = args.get("selector")
        from automation.browser_agent import browser_agent
        res = await browser_agent.click_element(selector)
        return res.get("message") or res.get("error")

    elif action == "browser_fill":
        selector = args.get("selector")
        text = args.get("text")
        from automation.browser_agent import browser_agent
        res = await browser_agent.fill_input(selector, text)
        return res.get("message") or res.get("error")

    elif action == "browser_read":
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

    elif action == "review_application":
        job_title = args.get("job_title", "")
        company = args.get("company", "")
        fields = args.get("fields", {})
        from app.agents.job_agent import job_agent

        res = await job_agent.review_application(job_title, company, fields)
        return res.get("message") or res.get("error")
    # -------------------------------

    elif action == "log_thought":
        thought = args.get("thought", "")
        logger.info("Agent generic thought:\n%s", thought)
        return f"Logged thought: {thought}"

    else:
        logger.warning("Unknown action in plan: %s", action)
        return f"Unknown action: {action}"
