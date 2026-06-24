# APPLICATION AGENT V1 TESTING

This document outlines the testing workflow for the Application Agent v1 capabilities.

## Overview
The Application Agent acts as the final step in the job-seeking process. It automates filling forms, uploading resumes, and reviewing applications while strictly avoiding autonomous submission.

## 1. LinkedIn Easy Apply Test
**Prompt:**
> "Open the LinkedIn Easy Apply application at [URL], fill out my personal details, upload my resume, and prepare it for review."

**Expected Behavior:**
1. Agent plans `application_action(action_type="open", url="[URL]")`.
2. Browser opens the target LinkedIn URL.
3. Agent evaluates the DOM and pulls user info via `application_action(action_type="get_details")`.
4. Agent uses `fill_form` and `click_element` to progress through the Easy Apply modals.
5. Agent detects the resume upload field and uses `application_action(action_type="upload_resume", selector="input[type='file']")` to inject the PDF.
6. Agent concludes by calling `application_action(action_type="review")`, passing the company, role, filled fields, and missing fields.
7. A warning is logged, the `pending_applications` table updates status to `prepared`, and the agent explicitly waits for user input.

## 2. Internshala Application Test
**Prompt:**
> "I want to apply for the Frontend role at Acme Corp on Internshala. Prepare the application."

**Expected Behavior:**
1. Similar to the LinkedIn flow, the agent navigates the DOM.
2. It fetches personal details and populates text areas.
3. It identifies any mandatory fields missing from `user_profile.json` (e.g., "Why should you be hired for this role?").
4. It calls `review` highlighting the missing fields in the `missing_fields` parameter.
5. Execution halts pending user manual intervention to answer the custom questions before final submission.

## Failure Scenarios

- **Missing Resume File:** If `upload_resume` is called but the file at `resume_path` in `user_profile.json` does not exist on disk, the agent safely traps the exception and returns the error back to the LLM context.
- **Invalid Profile JSON:** If `user_profile.json` is missing or malformed, `get_details` returns empty strings, forcing the agent to rely entirely on missing fields reporting.
- **Changed DOM / Modal Flow:** If a platform updates its UI flow unexpectedly, `fill_form` or `click_element` timeout gracefully after 5000ms. The loop observes the failure and can attempt an alternative generic CSS selector heuristically.