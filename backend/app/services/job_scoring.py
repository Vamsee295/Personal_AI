"""
services/job_scoring.py -- Scores job listings against user profile and resume data.
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Dict, Any

from app.models.schemas import JobResult
from app.services.ai_service import ai_service
from app.agents.resume_analyzer import resume_analyzer

logger = logging.getLogger("job_scoring")

class JobScorer:
    """Service to score JobResults against the user's profile and resume."""

    def __init__(self):
        self.profile_path = Path(__file__).resolve().parent.parent.parent / "memory" / "user_profile.json"

    async def score_job(self, job: JobResult) -> Dict[str, Any]:
        """
        Evaluate the job against the user profile and resume (if available).
        Returns a dictionary with the score (0.0 to 10.0) and reasoning.
        """
        
        # 1. Load basic user profile
        user_profile = {}
        if self.profile_path.exists():
            try:
                with open(self.profile_path, "r") as f:
                    user_profile = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load user profile: {e}")

        # 2. Analyze resume if path exists
        resume_data = {}
        resume_path = user_profile.get("resume_path")
        if resume_path and Path(resume_path).exists():
            res = await resume_analyzer.analyze_resume(resume_path)
            if res.get("success"):
                resume_data = res

        # 3. Ask LLM to score the job
        prompt = f"""
        You are an expert technical recruiter matching a candidate to a job.
        
        Job Details:
        - Title: {job.title}
        - Company: {job.company}
        - Location: {job.location}
        - Required Skills: {', '.join(job.skills) if job.skills else 'Not specified'}

        Candidate Profile:
        - Stated Skills: {', '.join(user_profile.get('skills', []))}
        
        Candidate Resume Data:
        - Extracted Technologies: {', '.join(resume_data.get('technologies', []))}
        - Extracted Projects: {', '.join(resume_data.get('projects', []))}

        Based on how well the candidate's profile and resume match the job details, provide a fit score from 0.0 to 10.0.
        Return ONLY a JSON object with:
        - "score": A float between 0.0 and 10.0.
        - "reasoning": A short string explaining the score.
        """

        try:
            result_str = await ai_service.chat(message=prompt, history=[])
            if isinstance(result_str, dict):
                result_str = result_str.get("content", "{}")

            import re
            match = re.search(r"\{.*\}", result_str, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return {
                    "success": True,
                    "score": float(data.get("score", 0.0)),
                    "reasoning": data.get("reasoning", "No reasoning provided.")
                }
            return {"success": False, "error": "Could not parse scoring JSON.", "score": 0.0}
        except Exception as e:
            logger.error("Failed to score job: %s", e)
            return {"success": False, "error": str(e), "score": 0.0}

job_scorer = JobScorer()
