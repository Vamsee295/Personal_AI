"""
agents/vision_module.py -- The agent's eyes.

Pipeline:
  capture_*()  ->  PIL Image
  extract_text_from_image()  ->  clean string (OCR via pytesseract)
  analyze_screen_with_llm()  ->  JSON action dict (via Ollama)
  run_vision_action_loop()   ->  autonomous see -> decide -> act loop

Tesseract must be installed on Windows:
  winget install UB-Mannheim.TesseractOCR
  (default path: C:/Program Files/Tesseract-OCR/tesseract.exe)
  (this machine's path: V:/Installations/tesseract.exe)
"""

from __future__ import annotations

import io
import json
import re
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

import mss
import mss.tools
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

from app.utils.logger import get_logger

logger = get_logger("vision_module")

# ── Tesseract path (machine-specific, with sensible fallback) ─────────────────
_TESSERACT_PATHS = [
    r"V:\Installations\tesseract.exe",                      # this machine
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",        # winget default
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",  # older installs
]

def _configure_tesseract() -> None:
    """Find and configure the Tesseract executable path."""
    # Check app settings first
    try:
        from app.config import settings
        if settings.TESSERACT_PATH:
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_PATH
            logger.info("Tesseract path from settings: %s", settings.TESSERACT_PATH)
            return
    except Exception:
        pass

    # Try known paths
    for path in _TESSERACT_PATHS:
        if Path(path).exists():
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info("Tesseract found at: %s", path)
            return

    logger.warning(
        "Tesseract not found at known paths. OCR may fail. "
        "Install with: winget install UB-Mannheim.TesseractOCR"
    )

_configure_tesseract()

# ── Screenshot output directory ────────────────────────────────────────────────
SCREENSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# ── OCR quality: characters that indicate pure garbage output ─────────────────
_GARBAGE_THRESHOLD = 0.4   # if >40% of chars are non-printable, treat as garbage


# =============================================================================
#  CAPTURE FUNCTIONS
# =============================================================================

def capture_full_screen(save: bool = True) -> Image.Image:
    """
    Capture the entire virtual desktop using mss.

    Args:
        save: If True, also saves a timestamped PNG to backend/screenshots/.

    Returns:
        PIL Image object (RGB mode).
    """
    with mss.mss() as sct:
        # monitors[0] = full virtual desktop (all monitors combined)
        monitor = sct.monitors[0]
        raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    if save:
        filename = f"vision_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
        path = SCREENSHOT_DIR / filename
        img.save(str(path))
        logger.info("Full screen saved: %s", path)

    logger.info("Captured full screen: %dx%d px", img.width, img.height)
    return img


def capture_region(x: int, y: int, width: int, height: int, save: bool = False) -> Image.Image:
    """
    Capture a rectangular region of the screen.

    Args:
        x, y      : Top-left corner coordinates (screen pixels).
        width     : Region width in pixels.
        height    : Region height in pixels.
        save      : Whether to save a timestamped PNG.

    Returns:
        PIL Image object (RGB mode).
    """
    with mss.mss() as sct:
        region = {"top": y, "left": x, "width": width, "height": height}
        raw = sct.grab(region)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    if save:
        filename = f"region_{x}_{y}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.png"
        path = SCREENSHOT_DIR / filename
        img.save(str(path))
        logger.info("Region saved: %s", path)

    logger.info("Captured region (%d,%d) %dx%d px", x, y, width, height)
    return img


def capture_active_window(save: bool = False) -> Image.Image:
    """
    Detect the currently focused window and capture only that region.

    Falls back to full-screen capture if pygetwindow cannot find the window
    or the window has zero size.

    Returns:
        PIL Image object (RGB mode).
    """
    try:
        import pygetwindow as gw

        active = gw.getActiveWindow()
        if active is None:
            raise RuntimeError("No active window detected")

        left   = active.left
        top    = active.top
        width  = active.width
        height = active.height

        # Sanity-check: sometimes minimised windows report 0-size
        if width <= 0 or height <= 0:
            raise RuntimeError(f"Active window has invalid size: {width}x{height}")

        logger.info(
            "Active window: '%s' at (%d,%d) %dx%d",
            active.title[:60], left, top, width, height,
        )
        return capture_region(left, top, width, height, save=save)

    except ImportError:
        logger.warning("pygetwindow not installed -- falling back to full screen. "
                       "Install with: pip install pygetwindow")
    except Exception as exc:
        logger.warning("Could not detect active window (%s) -- falling back to full screen", exc)

    return capture_full_screen(save=save)


# =============================================================================
#  OCR FUNCTIONS
# =============================================================================

def _preprocess_for_ocr(img: Image.Image) -> Image.Image:
    """
    Apply mild preprocessing to improve Tesseract accuracy:
    - Upscale small images (Tesseract works best >= 300 DPI equivalent)
    - Convert to grayscale
    - Light sharpening
    """
    # Upscale if image is small
    if img.width < 1920:
        scale = max(1, 1920 // img.width)
        img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)

    img = img.convert("L")  # grayscale
    img = ImageEnhance.Contrast(img).enhance(1.5)
    img = img.filter(ImageFilter.SHARPEN)
    return img


def _clean_ocr_text(raw: str) -> str:
    """
    Clean raw Tesseract output:
    - Remove non-printable / control characters
    - Collapse multiple blank lines
    - Strip trailing whitespace per line
    """
    # Keep printable ASCII + common punctuation; strip control chars
    cleaned = re.sub(r"[^\x20-\x7Ea-zA-Z0-9\n\r\t.,;:!?@#$%^&*()_+=\-\[\]{}'\"/<>|\\]", " ", raw)
    # Collapse runs of spaces/tabs on each line
    lines = [re.sub(r"[ \t]+", " ", line).rstrip() for line in cleaned.splitlines()]
    # Collapse >2 consecutive blank lines to a single blank
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return result.strip()


def _is_garbage(text: str) -> bool:
    """Return True if the OCR result is mostly junk (empty or non-printable)."""
    if not text or len(text.strip()) < 10:
        return True
    non_alpha = sum(1 for c in text if not (c.isalpha() or c.isspace()))
    ratio = non_alpha / max(len(text), 1)
    return ratio > _GARBAGE_THRESHOLD


def extract_text_from_image(img: Image.Image) -> str:
    """
    Run Tesseract OCR on a PIL Image and return cleaned text.

    Returns:
        Cleaned extracted text string, or "" if OCR produces garbage.
    """
    try:
        processed = _preprocess_for_ocr(img)
        raw = pytesseract.image_to_string(
            processed,
            config="--psm 6 --oem 3",   # psm 6 = uniform block of text
        )
        cleaned = _clean_ocr_text(raw)
        if _is_garbage(cleaned):
            logger.warning("OCR returned garbage/empty text (len=%d)", len(cleaned))
            return ""
        logger.info("OCR extracted %d characters", len(cleaned))
        return cleaned
    except pytesseract.TesseractNotFoundError:
        logger.error(
            "Tesseract not found! Install with: winget install UB-Mannheim.TesseractOCR"
        )
        raise
    except Exception as exc:
        logger.error("OCR error: %s", exc)
        return ""


def extract_text_from_screen() -> str:
    """
    Convenience function: capture full screen + run OCR in one call.

    Returns:
        Cleaned OCR text from the full screen.
    """
    img = capture_full_screen(save=False)
    return extract_text_from_image(img)


# =============================================================================
#  LLM ANALYSIS
# =============================================================================

_VISION_SYSTEM_PROMPT = """\
You are Vamsee AI -- an intelligent vision-based automation agent running on Windows 11.

Your job:
1. Read the text extracted from the user's screen (provided in <screen_content> tags).
2. Understand the user's goal (provided in <goal> tags).
3. Decide the single best next action to take RIGHT NOW.
4. Output ONLY a valid JSON object -- absolutely no prose, explanation, or markdown.

ACTION SCHEMA (always output exactly these keys):
{
  "action": "<one of: open_app | type_text | press_key | mouse_click | take_screenshot | move_mouse | scroll | done>",
  "target": "<app name, key name, or direction>",
  "value":  "<text to type, key combo, scroll amount, or extra detail>",
  "x": <integer x-coordinate, 0 if not applicable>,
  "y": <integer y-coordinate, 0 if not applicable>,
  "reason": "<one sentence explaining why you chose this action>"
}

Use "action": "done" ONLY when the goal has been fully achieved and no further action is needed.

If the screen content is unclear or empty, make your best decision based on the goal alone.

---
FEW-SHOT EXAMPLES:

EXAMPLE 1 -- Fix a terminal error:
<goal>Fix the ModuleNotFoundError I see in the terminal</goal>
<screen_content>
Traceback (most recent call last):
  File "main.py", line 3, in <module>
    import requests
ModuleNotFoundError: No module named 'requests'
</screen_content>
OUTPUT:
{"action": "type_text", "target": "", "value": "pip install requests", "x": 0, "y": 0, "reason": "The terminal shows requests is missing; typing the pip install command will fix it."}

EXAMPLE 2 -- Click a visible button:
<goal>Click the Submit button to send the form</goal>
<screen_content>
Name: John Doe
Email: john@example.com
[Submit]  [Cancel]
</screen_content>
OUTPUT:
{"action": "mouse_click", "target": "", "value": "left", "x": 760, "y": 540, "reason": "The Submit button is visible on screen; clicking it will submit the form."}

EXAMPLE 3 -- Type in a visible text field:
<goal>Search for 'Python tutorials' in the browser search bar</goal>
<screen_content>
Google Chrome
Address bar: https://www.google.com
Search Google or type a URL
</screen_content>
OUTPUT:
{"action": "type_text", "target": "", "value": "Python tutorials", "x": 0, "y": 0, "reason": "The browser search bar is visible and focused; typing the search term will start the search."}

Now process the user's goal and screen content below:
"""


def _build_vision_prompt(user_goal: str, screen_text: str) -> str:
    """Build the structured prompt to send to Ollama."""
    if not screen_text or _is_garbage(screen_text):
        screen_context = "(Screen text could not be read clearly. Make your best decision based on the goal alone.)"
    else:
        # Limit to 3000 chars to stay within model context
        screen_context = screen_text[:3000]

    return (
        f"<goal>{user_goal}</goal>\n\n"
        f"<screen_content>\n{screen_context}\n</screen_content>"
    )


def _extract_json_from_response(text: str) -> Dict[str, Any]:
    """Extract and parse JSON from raw LLM output. Tries multiple strategies."""
    text = text.strip()

    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strategy 2: strip markdown fences
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Strategy 3: first {...} block
    brace = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group())
        except json.JSONDecodeError:
            pass

    # Strategy 4: largest brace block
    all_candidates = re.findall(r"\{[\s\S]*?\}", text)
    for candidate in sorted(all_candidates, key=len, reverse=True):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    raise ValueError(f"No valid JSON found in LLM response:\n{text[:400]}")


def analyze_screen_with_llm(
    user_goal: str,
    screen_text: str,
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder:7b",
) -> Dict[str, Any]:
    """
    Synchronous function: sends goal + screen text to Ollama, returns parsed JSON action.

    Args:
        user_goal   : What the user wants to achieve.
        screen_text : OCR text from the screen.
        ollama_url  : Base URL for Ollama (default: localhost:11434).
        model       : Ollama model to use.

    Returns:
        Parsed action dict ready for action_executor.execute_action().
    """
    import requests as req

    prompt = _build_vision_prompt(user_goal, screen_text)
    logger.info("Sending vision prompt to Ollama (model=%s, prompt_len=%d)", model, len(prompt))

    try:
        payload = {
            "model": model,
            "system": _VISION_SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False,
        }
        resp = req.post(
            f"{ollama_url}/api/generate",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        raw_text = resp.json().get("response", "")
        logger.info("Ollama raw response: %s", raw_text[:300])

        action = _extract_json_from_response(raw_text)
        logger.info("Parsed action: %s", json.dumps(action))
        return action

    except req.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama at %s. Is it running?", ollama_url)
        raise RuntimeError(f"Ollama not reachable at {ollama_url}")
    except ValueError as exc:
        logger.error("JSON parse failure: %s", exc)
        raise
    except Exception as exc:
        logger.error("LLM analysis error: %s", exc)
        raise


# =============================================================================
#  AUTONOMOUS VISION-ACTION LOOP
# =============================================================================

def run_vision_action_loop(
    user_goal: str,
    max_steps: int = 5,
    ollama_url: str = "http://localhost:11434",
    model: str = "qwen2.5-coder:7b",
    step_delay: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Full autonomous loop: capture -> OCR -> LLM -> execute -> repeat.

    Args:
        user_goal  : Natural language goal (e.g. "fix the error in the terminal").
        max_steps  : Maximum number of action steps before stopping.
        ollama_url : Ollama base URL.
        model      : Ollama model name.
        step_delay : Seconds to wait between steps (let actions settle).

    Returns:
        List of step logs, each containing:
            {step, screen_text, action, result, stopped_early}
    """
    from app.services.action_executor import execute_action

    step_log: List[Dict[str, Any]] = []
    logger.info("=== Vision-Action Loop START | goal='%s' | max_steps=%d ===", user_goal, max_steps)

    for step in range(1, max_steps + 1):
        logger.info("--- Step %d/%d ---", step, max_steps)

        # 1. Capture screen
        try:
            img = capture_full_screen(save=True)
        except Exception as exc:
            logger.error("Screen capture failed: %s", exc)
            step_log.append({"step": step, "error": f"Capture failed: {exc}", "stopped_early": True})
            break

        # 2. OCR
        screen_text = extract_text_from_image(img)
        logger.info("Screen text len=%d", len(screen_text))

        # 3. LLM decision
        try:
            action = analyze_screen_with_llm(user_goal, screen_text, ollama_url, model)
        except Exception as exc:
            logger.error("LLM step %d failed: %s", step, exc)
            step_log.append({
                "step": step,
                "screen_text": screen_text[:500],
                "error": str(exc),
                "stopped_early": True,
            })
            break

        # 4. Check for "done" sentinel
        if action.get("action", "").lower() == "done":
            logger.info("LLM signalled 'done' -- stopping loop early at step %d", step)
            step_log.append({
                "step": step,
                "screen_text": screen_text[:500],
                "action": action,
                "result": {"success": True, "message": "Goal achieved"},
                "stopped_early": True,
            })
            break

        # 5. Execute action
        try:
            result = execute_action(action)
        except Exception as exc:
            logger.error("Action execution at step %d failed: %s", step, exc)
            result = {"success": False, "error": str(exc)}

        step_log.append({
            "step": step,
            "screen_text": screen_text[:500],
            "action": action,
            "result": result,
            "stopped_early": False,
        })

        logger.info("Step %d complete | success=%s", step, result.get("success"))

        # 6. Pause before next step
        if step < max_steps:
            time.sleep(step_delay)

    logger.info("=== Vision-Action Loop END | %d steps taken ===", len(step_log))
    return step_log
