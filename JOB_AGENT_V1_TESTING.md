# JOB AGENT V1 TESTING

This document outlines how to test the newly implemented `JobAgent` capabilities, which leverage the `BrowserAgent` to autonomously search and review job applications.

## Supported Job Boards
The agent natively supports structured querying and initial listing extraction for:
1. **LinkedIn** (`platform: "linkedin"`)
2. **Internshala** (`platform: "internshala"`)
3. **Wellfound** (formerly AngelList) (`platform: "wellfound"`)
4. **Naukri** (`platform: "naukri"`)

## Testing the Search Workflow

**Prompt:**
> "Search LinkedIn for remote React Developer jobs in London."

**Expected Behavior:**
1. The agent calls the `search_jobs` tool with `platform: "linkedin"`, `query: "React Developer remote"`, and `location: "London"`.
2. The browser automatically navigates to `https://www.linkedin.com/jobs/search?keywords=React%20Developer%20remote&location=London`.
3. The agent reads the page content and passes it to the extraction LLM prompt.
4. The backend writes the structured results (title, company, location, URL) to the `job_search_history` SQLite table.
5. The agent responds indicating the number of jobs found.

**Prompt:**
> "Find me Python internships on Internshala."

**Expected Behavior:**
1. The agent calls the `search_jobs` tool with `platform: "internshala"`, `query: "Python"`.
2. The browser automatically navigates to `https://internshala.com/internships/keywords-Python`.
3. The agent reads the page content and stores the listings in the SQLite `job_search_history` table.

## Testing the Application Workflow & Safety Constraints

**Prompt:**
> "I have reviewed the job description for the Frontend role at Google. Please prepare my application using my user profile, but don't submit it yet."

**Expected Behavior:**
1. The agent synthesizes the form fields.
2. It calls the `review_application` tool with the job title, company, and a dictionary of populated fields (e.g., pulling "Jane Doe" from `backend/memory/user_profile.json`).
3. **MANDATORY SAFETY CONSTRAINT:** The system will log a critical warning: `WARNING: I will not submit this application automatically. Please review the browser window and confirm.`
4. The execution loop halts, returning control to the user. Final submission (`browser_click` on the submit button) will ONLY occur if the user subsequently provides a direct prompt like "Looks good, go ahead and submit."