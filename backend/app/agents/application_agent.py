"""
agents/application_agent.py -- Agent responsible for preparing and safely submitting job applications.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, Any

from automation.browser_agent import browser_agent
from app.database.db import create_pending_application

logger = logging.getLogger("application_agent")

class ApplicationAgent:
    """Agent for filling out job applications securely."""

    def __init__(self):
        self.profile_path = Path(__file__).resolve().parent.parent.parent / "memory" / "user_profile.json"

    def _load_profile(self) -> Dict[str, Any]:
        if self.profile_path.exists():
            try:
                with open(self.profile_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load user profile: {e}")
        return {}

    async def open_application(self, url: str) -> Dict[str, Any]:
        """Navigate to the job application URL."""
        logger.info(f"Opening application URL: {url}")
        return await browser_agent.goto_url(url)

    async def upload_resume(self, selector: str) -> Dict[str, Any]:
        """Upload the user's resume using Playwright's set_input_files on an <input type=file>."""
        logger.info(f"Attempting to upload resume to selector: {selector}")
        profile = self._load_profile()
        resume_path = profile.get("resume_path")

        if not resume_path or not Path(resume_path).exists():
            return {"success": False, "error": "Resume path not found or invalid in user_profile."}

        try:
            await browser_agent._ensure_started()
            locator = browser_agent._page.locator(selector).first
            await locator.set_input_files(resume_path)
            return {"success": True, "message": f"Successfully uploaded resume to {selector}"}
        except Exception as e:
            logger.error("Failed to upload resume: %s", e)
            return {"success": False, "error": str(e)}

    async def fill_personal_details(self) -> Dict[str, Any]:
        """
        Attempt to auto-fill common fields (name, email, phone) on the active DOM
        using generic selectors or by prompting the LLM for the right selectors.
        Here we assume the LLM handles specific selectors via `fill_form` step by step,
        so this function returns the raw data for the LLM to use.
        """
        profile = self._load_profile()
        details = {
            "name": profile.get("name", ""),
            "email": profile.get("email", ""),
            "phone": profile.get("phone", ""),
            "linkedin_url": profile.get("linkedin_url", ""),
            "github_url": profile.get("github_url", "")
        }
        return {"success": True, "details": details}

    async def review_application(self, company: str, role: str, fields_filled: Dict[str, str], missing_fields: list[str]) -> Dict[str, Any]:
        """
        Final safety gate before submission. Outputs the prepared info and pauses.
        Records the application as 'prepared' in SQLite.
        """
        profile = self._load_profile()
        resume_path = profile.get("resume_path", "None")

        review_msg = (
            "==============================================\n"
            "        APPLICATION REVIEW (READY)            \n"
            "==============================================\n"
            f"Company: {company}\n"
            f"Role: {role}\n"
            f"Resume attached: {resume_path}\n"
            "Fields Filled:\n"
        )

        for k, v in fields_filled.items():
            review_msg += f"  - {k}: {v}\n"

        if missing_fields:
            review_msg += "\nMissing Fields (Please complete manually if required):\n"
            for f in missing_fields:
                review_msg += f"  - {f}\n"

        review_msg += "\n[SAFETY HALT] The application is prepared. Please review the browser window. I will NOT auto-submit. Respond to confirm submission."

        logger.warning(review_msg)

        # Log to DB
        await create_pending_application(company=company, role=role, status="prepared")

        return {"success": True, "message": review_msg}

application_agent = ApplicationAgent()
