# JOB AGENT V2 TESTING

This document outlines the testing workflow for the Job Agent v2 capabilities: Universal Search, Job Extraction, Resume Understanding, and Job Ranking.

## 1. Resume Understanding
**Prerequisites:** 
- Have a dummy PDF resume at the path specified in `backend/memory/user_profile.json` (e.g., `/home/jules/Documents/resume.pdf`).
- Ensure `PyMuPDF` is installed (`pip install PyMuPDF`).

**Test Action:**
The background Job Scorer initializes by parsing this PDF. The LLM extracts the candidate's skills, technologies, and projects, caching them to compare against jobs.

## 2. Job Search and Extraction
**Prompt:**
> "Find React developer internships on Wellfound and extract their required skills."

**Expected Behavior:**
1. Agent plans `search_jobs(platform="wellfound", query="React developer internship")`.
2. Browser navigates to Wellfound and the page DOM is fed back into the agent context.
3. The internal `job_agent._extract_jobs_from_page` method queries Ollama to extract an array of `JobResult`s containing the required `skills`.
4. The jobs are logged into `job_search_history`.

## 3. Job Ranking and Saving
**Prompt:**
> "Score the latest job listing you found against my resume."

**Expected Behavior:**
1. The agent plans `score_job(title="...", company="..." ...)`.
2. `job_scorer.py` evaluates the job's `skills` against the candidate's `user_profile.json` and the `resume_analyzer.py` output.
3. The LLM assigns a score from 0.0 to 10.0 and provides reasoning.
4. If the score is > 6.0, the job is permanently stored in the `saved_jobs` SQLite table.

## 4. Application Preparation (Safety Restraint)
**Prompt:**
> "I like the high-scoring job. Prepare my application."

**Expected Behavior:**
1. The agent plans `review_application(job_title="...", company="...", fields={...})`.
2. The agent outputs the fields to be submitted alongside the `resume_path`.
3. **CRITICAL:** The agent logs a warning and HALTS. It strictly waits for explicit user confirmation before any final DOM submission via `click_element(selector="Submit")`.

## Failure Cases
- **Missing Resume:** If the PDF does not exist at `resume_path`, the scorer gracefully falls back to the static `skills` array defined in `user_profile.json`.
- **Garbage DOM/No Jobs:** If the search returns a 404 or captcha page, `extract_jobs_from_page` gracefully returns `[]`, preventing database contamination.