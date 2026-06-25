# AGENT CAPABILITIES V1 TESTING

This document outlines testing for the new generic browser capabilities, the newly added YouTube agent, and the continuous Observe -> Replan loop.

## 1. Observe -> Replan Loop
**Prompt:**
> "Find the company 'OpenAI' on Wikipedia, then extract the first paragraph and log it as a thought."

**Expected Behavior:**
1. The agent calls `search_web` for "OpenAI Wikipedia".
2. The loop **immediately** restarts (skipping the 5-second sleep) and extracts the DOM content from DuckDuckGo.
3. The agent calls `click_element` or `open_page` for the Wikipedia link.
4. The loop immediately restarts, reading the Wikipedia DOM.
5. The agent calls `log_thought` with the summarized paragraph.
6. The loop goes dormant (waits 5 seconds) since `log_thought` is a terminal action.

**Failure Cases:**
- The agent gets stuck in a loop navigating between two pages. (Mitigated by the 20-action history).

## 2. Generic Browser Tools
**Prompt:**
> "Search the web for the current weather in London."

**Expected Behavior:**
1. Agent calls `search_web` with query "current weather in London".
2. Browser automatically opens DuckDuckGo and fetches the DOM context.
3. Agent reads the result.

## 3. YouTube Agent
**Prompt:**
> "Play some lo-fi hip hop on YouTube."

**Expected Behavior:**
1. Agent plans `youtube_action` with `action_type: search` and `query: lo-fi hip hop`.
2. Browser navigates to the YouTube search results.
3. Observe loop catches the video titles.
4. Agent plans `youtube_action` with `action_type: open_video` for the top result.
5. Agent calls `youtube_action` with `action_type: play` to toggle playback (simulating the 'k' keystroke).

**Failure Cases:**
- YouTube popups or ad blockers interrupt the DOM state. The agent should log an error or use `extract_page` to figure out why the video isn't playing and close the popup via `click_element`.

## 4. Job Search Tool
**Prompt:**
> "Look for full-stack developer roles on Wellfound."

**Expected Behavior:**
1. The agent calls `search_jobs` directly with `platform: wellfound`, `query: full-stack developer`.
2. The specific Wellfound extraction flow executes and pushes the data to SQLite.