"""
agents/youtube_agent.py -- High-level YouTube Agent using Playwright capabilities.
"""

from __future__ import annotations
import asyncio
import logging
from typing import Dict, Any

from automation.browser_agent import browser_agent

logger = logging.getLogger("youtube_agent")

class YouTubeAgent:
    """Agent for searching and interacting with YouTube."""

    async def search_youtube(self, query: str) -> Dict[str, Any]:
        """Search YouTube for a specific query."""
        logger.info(f"Searching YouTube for {query}")

        import urllib.parse
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.youtube.com/results?search_query={encoded_query}"

        return await browser_agent.goto_url(url)

    async def open_video(self, video_id_or_url: str) -> Dict[str, Any]:
        """Open a specific YouTube video."""
        logger.info(f"Opening YouTube video {video_id_or_url}")

        if "youtube.com" in video_id_or_url or "youtu.be" in video_id_or_url:
            url = video_id_or_url
        else:
            url = f"https://www.youtube.com/watch?v={video_id_or_url}"

        return await browser_agent.goto_url(url)

    async def play_video(self) -> Dict[str, Any]:
        """Play or pause the current video by pressing 'k'."""
        logger.info("Toggling play/pause on YouTube")

        # In YouTube, pressing 'k' toggles play/pause reliably
        try:
            # We can use playwright's keyboard press through the browser_agent if we add it,
            # but since browser_agent might not expose direct keyboard yet, we can evaluate JS:
            if browser_agent._page:
                await browser_agent._page.keyboard.press("k")
                return {"success": True, "message": "Toggled play/pause."}
            return {"success": False, "error": "No active page."}
        except Exception as e:
            logger.error("Failed to play video: %s", e)
            return {"success": False, "error": str(e)}

    async def open_playlist(self, playlist_id_or_url: str) -> Dict[str, Any]:
        """Open a specific YouTube playlist."""
        logger.info(f"Opening YouTube playlist {playlist_id_or_url}")

        if "youtube.com/playlist" in playlist_id_or_url:
            url = playlist_id_or_url
        else:
            url = f"https://www.youtube.com/playlist?list={playlist_id_or_url}"

        return await browser_agent.goto_url(url)

youtube_agent = YouTubeAgent()
