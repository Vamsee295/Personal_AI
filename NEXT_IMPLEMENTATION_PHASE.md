# Next Implementation Phase Recommendation

Based strictly on extending the existing codebase, without rebuilding the project or shifting to a new architecture from scratch, I recommend the following as the **highest-impact next development phase**:

## Phase: Playwright Browser Agent & Native Tool Calling

### Why this phase?
The immediate goal is to enable "Job application assistance" and general "Browser automation," which are currently impossible with the highly-specialized Selenium WhatsApp script. Additionally, the core agent planning loop relies on brittle string-matching. Upgrading to native tool calling while introducing Playwright solves both problems simultaneously, drastically increasing the agent's capability and reliability.

### Key Objectives

1. **Replace Selenium with Playwright (Async)**
   - **Action**: Add `playwright` to `backend/requirements.txt`.
   - **Implementation**: Create a new `backend/automation/browser_agent.py` utilizing `playwright.async_api`.
   - **Capabilities**: Implement generic browser functions:
     - `goto_url(url)`
     - `get_page_content()` (extracting clean text or accessibility trees, not raw HTML)
     - `click_element(selector)`
     - `fill_input(selector, text)`
   - **Benefit**: Faster, headless-capable, and doesn't require managing ChromeDriver binaries. It provides the foundation for logging into LinkedIn, Indeed, etc.

2. **Upgrade `planner.py` to use Native Ollama Tool Calling**
   - **Action**: Rewrite how the agent requests actions.
   - **Implementation**: Instead of the LLM outputting strings like "open chrome", use Ollama's `tools` API (supported in recent Ollama versions for Qwen/Llama3).
   - Define strict Pydantic JSON schemas for tools like `open_app`, `navigate_browser`, `click_web_element`.
   - Pass these schemas to the Ollama API in `ollama_client.py`.
   - **Benefit**: The LLM will output guaranteed structured JSON matching the exact arguments the `action_executor.py` needs, completely removing the need for manual regex parsing.

3. **Enhance the Multi-Step Agent State (`agent_loop.py`)**
   - **Action**: Add conversational/action context tracking.
   - **Implementation**: When the loop runs, pass the *last 5 actions and their results* back into the LLM prompt.
   - E.g., `History: [Agent navigated to indeed.com -> Success. Agent clicked 'Login' -> Success. Current Screen: Login Page]`.
   - **Benefit**: This allows the agent to execute complex, multi-step tasks like a job application, because it remembers what step of the process it is currently on.

### Summary
By integrating Playwright and wiring it into native Ollama tool-calling, the existing agent will transform from a simple reactive script into a structured, reliable autonomous web worker capable of navigating dynamic web apps.