"""
agents/job_agent.py -- High-level Job Application Agent using Playwright capabilities.
"""

from __future__ import annotations
import asyncio
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

from app.models.schemas import JobResult
from automation.browser_agent import browser_agent
from app.services.ai_service import ai_service
from app.database.db import log_job_search, log_job_application

logger = logging.getLogger("job_agent")

class JobAgent:
    """Agent for searching and applying to jobs via various platforms."""

    async def _extract_jobs_from_page(self, source: str) -> List[JobResult]:
        """Ask LLM to extract jobs from current page text."""
        page_state = await browser_agent.get_page_state()
        content = page_state.get("content", "")

        prompt = f"""
        Extract job listings from this page text.
        Return ONLY a JSON list of objects with these exact keys: title, company, location, salary, url, source.
        If a value is missing, use "Not specified".
        Source should be '{source}'.
        
        Page Text:
        {content[:8000]}
        """

        try:
            # Using deepseek or qwen for extraction
            result_str = await ai_service.chat(message=prompt, history=[])
            if isinstance(result_str, dict):
                result_str = result_str.get("content", "[]")

            # Basic parsing of the JSON block
            import re
            match = re.search(r"\[.*\]", result_str, re.DOTALL)
            if match:
                jobs_data = json.loads(match.group(0))
                jobs = [JobResult(**j) for j in jobs_data]
                return jobs
            return []
        except Exception as e:
            logger.error("Failed to extract jobs: %s", e)
            return []

    async def search_jobs(self, platform: str, query: str, location: str = "") -> Dict[str, Any]:
        """Generic job search router that aggregates extraction and scoring."""
        platform = platform.lower()

        from app.database.db import save_task_checkpoint
        task_id = f"{platform}_search_{query}_{location}"
        await save_task_checkpoint(task_id, "searching")

        logger.info(f"Searching {platform} for '{query}' in '{location}'")
        
        url = ""
        if platform == "linkedin":
            url_query = query.replace(" ", "%20")
            url_location = location.replace(" ", "%20")
            url = f"https://www.linkedin.com/jobs/search?keywords={url_query}&location={url_location}"
        elif platform == "internshala":
            url_query = query.replace(" ", "%20")
            url = f"https://internshala.com/internships/keywords-{url_query}"
        elif platform == "wellfound":
            url_query = query.replace(" ", "+")
            url = f"https://wellfound.com/role/l/{url_query}"
        elif platform == "naukri":
            url_query = query.replace(" ", "-")
            url = f"https://www.naukri.com/{url_query}-jobs"
        else:
            return {"success": False, "error": f"Unsupported platform: {platform}"}

        # Navigate
        await browser_agent.goto_url(url)
        await asyncio.sleep(3) # Let page load

        await save_task_checkpoint(task_id, "extracting")
        jobs = await self._extract_jobs_from_page(source=platform.title())
        
        saved_count = 0
        from app.services.job_scoring import job_scorer
        from app.database.db import save_job
        
        scored_jobs = []
        for j in jobs:
            await log_job_search(j.title, j.company, j.location, j.salary, j.skills, j.url, j.source)

            # Auto-score the job
            score_res = await job_scorer.score_job(j)
            if score_res.get("success"):
                score = score_res.get("score", 0.0)
                reasoning = score_res.get("reasoning", "")
                scored_jobs.append({"job": j, "score": score, "reasoning": reasoning})

                # Only save high value jobs automatically
                if score > 6.0:
                    await save_job(j.title, j.company, j.location, j.salary, j.skills, j.url, j.source, score)
                    saved_count += 1
        
        await save_task_checkpoint(task_id, "completed")
        
        # Sort best jobs to return to the planner context
        scored_jobs.sort(key=lambda x: x["score"], reverse=True)
        top_jobs = [{"title": sj["job"].title, "company": sj["job"].company, "url": sj["job"].url, "score": sj["score"]} for sj in scored_jobs[:3]]

        return {
            "success": True,
            "source": platform.title(),
            "jobs_found": len(jobs),
            "highly_matched_jobs_saved": saved_count,
            "top_matches": top_jobs,
            "message": f"Found {len(jobs)} jobs. Saved {saved_count} top matches to DB."
        }

    async def review_application(self, job_title: str, company: str, fields: Dict[str, str]) -> Dict[str, Any]:
        """Show required info and request user confirmation before submission."""
        
        # Load user profile
        import os
        profile_path = Path(__file__).resolve().parent.parent.parent / "memory" / "user_profile.json"
        
        resume_path = "Unknown"
        if os.path.exists(profile_path):
            try:
                with open(profile_path, "r") as f:
                    profile = json.load(f)
                    resume_path = profile.get("resume_path", "Unknown")
            except Exception:
                pass

        # Create the review summary
        review_text = (
            f"=== Application Review ===\n"
            f"Job: {job_title} at {company}\n"
            f"Resume Path: {resume_path}\n"
            f"Fields to be submitted:\n"
        )
        for k, v in fields.items():
            review_text += f"  - {k}: {v}\n"
            
        review_text += "\nWARNING: I will not submit this application automatically. Please review the browser window and confirm."

        logger.info(review_text)
        
        # For headless autonomous operation, this returns the prompt to the user interface/LLM context
        # In a real UI, this would trigger a modal or voice prompt
        return {
            "success": True,
            "action_required": "user_confirmation",
            "message": review_text
        }

job_agent = JobAgent()
