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

    async def search_linkedin_jobs(self, query: str, location: str = "") -> Dict[str, Any]:
        """Search LinkedIn for jobs."""
        logger.info(f"Searching LinkedIn for {query} in {location}")

        url_query = query.replace(" ", "%20")
        url_location = location.replace(" ", "%20")
        url = f"https://www.linkedin.com/jobs/search?keywords={url_query}&location={url_location}"

        await browser_agent.goto_url(url)
        # Wait a bit for dynamic content to load
        await asyncio.sleep(3)

        jobs = await self._extract_jobs_from_page(source="LinkedIn")
        for j in jobs:
            await log_job_search(j.title, j.company, j.location, j.salary, j.url, j.source)

        return {"success": True, "source": "LinkedIn", "jobs_found": len(jobs), "message": f"Found {len(jobs)} jobs on LinkedIn."}

    async def search_internshala_jobs(self, query: str) -> Dict[str, Any]:
        """Search Internshala for jobs/internships."""
        logger.info(f"Searching Internshala for {query}")

        url_query = query.replace(" ", "%20")
        url = f"https://internshala.com/internships/keywords-{url_query}"

        await browser_agent.goto_url(url)
        await asyncio.sleep(3)

        jobs = await self._extract_jobs_from_page(source="Internshala")
        for j in jobs:
            await log_job_search(j.title, j.company, j.location, j.salary, j.url, j.source)

        return {"success": True, "source": "Internshala", "jobs_found": len(jobs), "message": f"Found {len(jobs)} internships on Internshala."}

    async def search_wellfound_jobs(self, query: str) -> Dict[str, Any]:
        """Search Wellfound (formerly AngelList) for jobs."""
        logger.info(f"Searching Wellfound for {query}")

        url_query = query.replace(" ", "+")
        url = f"https://wellfound.com/role/l/{url_query}"

        await browser_agent.goto_url(url)
        await asyncio.sleep(3)

        jobs = await self._extract_jobs_from_page(source="Wellfound")
        for j in jobs:
            await log_job_search(j.title, j.company, j.location, j.salary, j.url, j.source)

        return {"success": True, "source": "Wellfound", "jobs_found": len(jobs), "message": f"Found {len(jobs)} jobs on Wellfound."}

    async def search_naukri_jobs(self, query: str) -> Dict[str, Any]:
        """Search Naukri for jobs."""
        logger.info(f"Searching Naukri for {query}")

        url_query = query.replace(" ", "-")
        url = f"https://www.naukri.com/{url_query}-jobs"

        await browser_agent.goto_url(url)
        await asyncio.sleep(3)

        jobs = await self._extract_jobs_from_page(source="Naukri")
        for j in jobs:
            await log_job_search(j.title, j.company, j.location, j.salary, j.url, j.source)

        return {"success": True, "source": "Naukri", "jobs_found": len(jobs), "message": f"Found {len(jobs)} jobs on Naukri."}

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
