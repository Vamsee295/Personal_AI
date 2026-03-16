"""
agents/screen_agent.py – Screen capture, OCR, and screen AI analysis.
"""

from __future__ import annotations
from typing import Optional
import base64
import io

from app.utils.logger import get_logger

logger = get_logger("screen_agent")


class ScreenAgent:
    """Captures the screen and performs OCR / AI analysis."""

    def capture_screen(self) -> bytes:
        """Capture the primary screen and return raw PNG bytes."""
        try:
            import mss
            import numpy as np

            with mss.mss() as sct:
                monitor = sct.monitors[1]
                screenshot = sct.grab(monitor)
                # Convert to bytes via Pillow
                from PIL import Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf.getvalue()
        except ImportError as exc:
            logger.warning("mss or Pillow not installed: %s", exc)
            raise RuntimeError("Screen capture dependencies not installed. Run: pip install mss Pillow")

    def capture_base64(self) -> str:
        """Return screen capture as a base64-encoded PNG string."""
        raw = self.capture_screen()
        return base64.b64encode(raw).decode("utf-8")

    def extract_text(self, image_bytes: Optional[bytes] = None) -> str:
        """
        Run OCR on the given image bytes (or capture screen if not provided).
        Returns extracted text.
        """
        try:
            import pytesseract
            from PIL import Image
            from app.config import settings

            if settings.TESSERACT_PATH:
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH

            if image_bytes is None:
                image_bytes = self.capture_screen()

            img = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(img)
            logger.info("OCR extracted %d chars", len(text))
            return text
        except ImportError as exc:
            logger.warning("pytesseract not installed: %s", exc)
            raise RuntimeError("OCR dependencies not installed. Run: pip install pytesseract Pillow")

    def click(self, x: int, y: int) -> None:
        """Move mouse and click at (x, y)."""
        try:
            import pyautogui
            pyautogui.click(x, y)
            logger.info("Clicked at (%d, %d)", x, y)
        except ImportError:
            raise RuntimeError("pyautogui not installed.")

    def type_text(self, text: str, interval: float = 0.05) -> None:
        """Type text using keyboard simulation."""
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=interval)
        except ImportError:
            raise RuntimeError("pyautogui not installed.")

    def hotkey(self, *keys: str) -> None:
        """Press a keyboard shortcut. Example: hotkey('ctrl', 'c')"""
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
        except ImportError:
            raise RuntimeError("pyautogui not installed.")


# Module-level singleton
screen_agent = ScreenAgent()
