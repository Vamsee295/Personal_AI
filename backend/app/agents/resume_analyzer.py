"""
agents/resume_analyzer.py -- Reads and parses PDF resumes to extract user skills and info.
"""

from __future__ import annotations
import logging
from typing import Dict, Any

import fitz  # PyMuPDF
from app.services.ai_service import ai_service

logger = logging.getLogger("resume_analyzer")

class ResumeAnalyzer:
    """Agent for parsing and analyzing a user's resume PDF."""

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract all raw text from a given PDF."""
        logger.info(f"Extracting text from resume: {pdf_path}")
        text = ""
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text("text") + "\n"
            doc.close()
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
        return text

    async def analyze_resume(self, pdf_path: str) -> Dict[str, Any]:
        """Ask LLM to extract skills, projects, and technologies from the resume text."""
        raw_text = self.extract_text_from_pdf(pdf_path)
        
        if not raw_text.strip():
            return {"success": False, "error": "No text extracted from PDF."}

        prompt = f"""
        Analyze the following resume text and extract the applicant's key details.
        Return ONLY a JSON object with these exact keys:
        - "skills": A list of strings representing general skills.
        - "technologies": A list of strings representing specific tools, languages, or frameworks.
        - "projects": A list of strings briefly summarizing major projects.

        Resume Text:
        ---
        {raw_text[:8000]}
        ---
        """

        try:
            result_str = await ai_service.chat(message=prompt, history=[])
            if isinstance(result_str, dict):
                result_str = result_str.get("content", "{}")

            import re
            import json
            match = re.search(r"\{.*\}", result_str, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                return {
                    "success": True,
                    "skills": data.get("skills", []),
                    "technologies": data.get("technologies", []),
                    "projects": data.get("projects", [])
                }
            return {"success": False, "error": "Could not parse JSON from LLM response."}
        except Exception as e:
            logger.error("Failed to analyze resume: %s", e)
            return {"success": False, "error": str(e)}

resume_analyzer = ResumeAnalyzer()
