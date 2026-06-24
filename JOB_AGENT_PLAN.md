# Job Agent Automation Plan

This document outlines the workflows for the JARVIS Job Application Agent.

## Overview
The goal is to allow JARVIS to autonomously search, find, and apply for jobs (e.g., React internships) on platforms like LinkedIn, Indeed, and specific company portals using the Playwright browser agent.

---

## 1. Internship & Job Search Workflow
**Trigger:** Voice command or UI prompt ("Find me React internships").

1. **Initialization:**
   - Agent accesses `backend/memory/user_profile.json` to load skills (e.g., React, TypeScript), location, and preferences.
   - Calculates target keywords based on skills.
2. **Navigation:**
   - Calls `navigate_browser` to open LinkedIn Jobs or Indeed.
3. **Execution:**
   - Uses `browser_fill` to enter the keywords ("React Intern") into the search bar.
   - Uses `browser_click` to click the 'Search' button.
   - Uses `browser_read` or generic screen OCR to parse the list of job titles and links.
4. **Processing:**
   - The LLM processes the text, identifying the top 3-5 relevant listings.
   - The loop continues for each listing, parsing descriptions to ensure a good match.
5. **Output:**
   - Agent synthesizes a summary of the listings and pauses for user feedback before proceeding to application.

---

## 2. Resume Upload Workflow
**Trigger:** Required as part of a job application form.

1. **Identify Upload Field:**
   - Through `browser_read`, the agent identifies the "Upload Resume" button or `<input type="file">`.
2. **Retrieve Path:**
   - Reads `resume_path` from `memory/user_profile.json`.
3. **Execution:**
   - The agent (pending an `upload_file` tool addition, or using generic native OS keystrokes) triggers the file upload dialogue.
   - It types the absolute file path into the native dialogue box and hits "Enter" (using OS-level tools), OR directly sets the file path on the HTML input via Playwright APIs.
4. **Verification:**
   - Agent verifies that the upload succeeded (e.g., seeing a "resume.pdf uploaded" text node).

---

## 3. Safe Application Workflow
**Trigger:** Moving from reviewing a job description to applying.

1. **Form Filling:**
   - Agent clicks the "Apply Now" button.
   - For every field on the form (Name, Email, Phone, LinkedIn, GitHub), the agent reads the label and queries `memory/user_profile.json` for the data.
   - Uses `browser_fill` to populate the form inputs.
2. **Upload:**
   - Executes the Resume Upload Workflow if required.
3. **MANDATORY SAFETY HALT (Confirmation Check):**
   - **Crucial Rule:** The agent MUST NOT click the final "Submit Application" button autonomously.
   - Upon completing the form, the agent will log its thought: "Form is complete. Waiting for user confirmation to submit."
   - The agent will use the voice or chat module to ask: *"I have filled out the application for [Company]. Please review it in the browser. Should I submit?"*
4. **Final Action:**
   - If the user says "Yes" or clicks "Approve", the agent executes `browser_click` on the Submit button.
   - If "No", the agent halts or clears the form.