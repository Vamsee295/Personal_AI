"""
automation/browser_agent.py -- General-purpose Playwright browser automation agent.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser, Playwright, BrowserContext

logger = logging.getLogger("browser_agent")

SCREENSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

class BrowserAgent:
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock: Optional[asyncio.Lock] = None

    async def _ensure_started(self):
        """Starts Playwright and the browser if not already running."""
        if self._lock is None:
            self._lock = asyncio.Lock()

        async with self._lock:
            if self._playwright is None:
                logger.info("Starting Playwright...")
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=False) # Headless=False so the user can see the agent's actions
                self._context = await self._browser.new_context(viewport={"width": 1280, "height": 720})
                self._page = await self._context.new_page()

    async def search_web(self, query: str) -> Dict[str, Any]:
        """Search the web using DuckDuckGo (or generic search engine)."""
        try:
            await self._ensure_started()
            import urllib.parse
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://duckduckgo.com/?q={encoded_query}"
            await self._page.goto(url, wait_until="networkidle")
            return {"success": True, "message": f"Searched web for '{query}'"}
        except Exception as e:
            logger.error("Failed to search web: %s", e)
            return {"success": False, "error": str(e)}

    async def goto_url(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL."""
        try:
            await self._ensure_started()
            # Playwright requires http:// or https://
            if not url.startswith("http"):
                url = f"https://{url}"
            await self._page.goto(url, wait_until="networkidle")
            return {"success": True, "message": f"Navigated to {url}"}
        except Exception as e:
            logger.error("Failed to goto URL: %s", e)
            return {"success": False, "error": str(e)}

    async def get_page_content(self) -> Dict[str, Any]:
        """Get text content of the page, stripped of raw HTML, representing what the user sees."""
        try:
            await self._ensure_started()
            text = await self._page.evaluate("document.body.innerText")
            # Truncate if insanely long to prevent blowing up the LLM context
            text = text[:10000] if text else ""
            return {"success": True, "content": text}
        except Exception as e:
            logger.error("Failed to get page content: %s", e)
            return {"success": False, "error": str(e)}

    async def get_page_state(self) -> Dict[str, Any]:
        """Get the current URL, page title, and visible content."""
        try:
            await self._ensure_started()
            url = self._page.url
            title = await self._page.title()
            text = await self._page.evaluate("document.body.innerText")
            text = text[:10000] if text else ""

            return {
                "success": True,
                "url": url,
                "title": title,
                "content": text
            }
        except Exception as e:
            logger.error("Failed to get page state: %s", e)
            return {"success": False, "error": str(e)}

    async def click_element(self, selector: str) -> Dict[str, Any]:
        """Click on a specific element by CSS or text selector."""
        try:
            await self._ensure_started()

            # Using text locators if selector seems like plain text
            if not selector.startswith(".") and not selector.startswith("#") and "[" not in selector:
                locator = self._page.get_by_text(selector, exact=False).first
            else:
                locator = self._page.locator(selector).first

            await locator.wait_for(state="visible", timeout=5000)
            await locator.click()
            return {"success": True, "message": f"Clicked on '{selector}'"}
        except Exception as e:
            logger.error("Failed to click element: %s", e)
            return {"success": False, "error": f"Could not find or click '{selector}'. Exception: {str(e)}"}

    async def fill_input(self, selector: str, text: str) -> Dict[str, Any]:
        """Fill an input field with text."""
        try:
            await self._ensure_started()

            # If it looks like placeholder text, try get_by_placeholder
            if not selector.startswith(".") and not selector.startswith("#") and "[" not in selector:
                locator = self._page.get_by_placeholder(selector).first
                # Fallback to get_by_role / label if needed, but placeholder is common
            else:
                locator = self._page.locator(selector).first

            await locator.wait_for(state="visible", timeout=5000)
            await locator.fill(text)
            return {"success": True, "message": f"Filled '{selector}' with text."}
        except Exception as e:
            logger.error("Failed to fill input: %s", e)
            return {"success": False, "error": f"Could not find or fill '{selector}'. Exception: {str(e)}"}

    async def screenshot(self, path: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot of the current page."""
        try:
            await self._ensure_started()
            import datetime
            if path is None:
                filename = f"browser_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                path = str(SCREENSHOT_DIR / filename)
            await self._page.screenshot(path=path)
            return {"success": True, "message": f"Screenshot saved to {path}"}
        except Exception as e:
            logger.error("Failed to take screenshot: %s", e)
            return {"success": False, "error": str(e)}

    async def close(self):
        """Shutdown Playwright cleanly."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None
        self._page = None
        self._context = None

# Global singleton instance
browser_agent = BrowserAgent()
