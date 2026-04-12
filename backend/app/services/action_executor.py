"""
services/action_executor.py – Routes Ollama JSON action objects to real OS-level operations.

Supported actions:
  open_app               → Open any application by name using subprocess.Popen
  type_text              → Type text via pyautogui
  press_key              → Press key / combo via pyautogui (e.g. ctrl+c, alt+tab)
  mouse_click            → Click at (x, y) coordinates
  take_screenshot        → Capture screen with mss, save to backend/screenshots/
  move_mouse             → Move mouse smoothly to (x, y)
  scroll                 → Scroll up/down at current position
  send_whatsapp_message  → Send a WhatsApp message via Selenium
  read_whatsapp          → Read recent messages from a WhatsApp chat
  unknown_action         → Graceful fallback with detailed logging
"""

from __future__ import annotations

import os
import re
import json
import time
import subprocess
import webbrowser
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("action_executor")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(name)s: %(message)s")

# ── Screenshot output directory ───────────────────────────────────────────────
SCREENSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# ── Windows app path map ──────────────────────────────────────────────────────
# Maps friendly names → actual executable paths / commands on Windows
APP_PATH_MAP: Dict[str, str] = {
    # Editors / IDEs
    "notepad":        "notepad.exe",
    "wordpad":        "wordpad.exe",
    "code":           r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vscode":         r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "vscodium":       r"C:\Program Files\VSCodium\VSCodium.exe",

    # Browsers
    "chrome":         r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "firefox":        r"C:\Program Files\Mozilla Firefox\firefox.exe",
    "edge":           r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "brave":          r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",

    # System utilities
    "calculator":     "calc.exe",
    "explorer":       "explorer.exe",
    "taskmgr":        "taskmgr.exe",
    "taskmanager":    "taskmgr.exe",
    "cmd":            "cmd.exe",
    "powershell":     "powershell.exe",
    "terminal":       "wt.exe",   # Windows Terminal
    "paint":          "mspaint.exe",
    "snipping":       "SnippingTool.exe",

    # Office / Productivity
    "word":           r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    "excel":          r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    "powerpoint":     r"C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE",
    "onenote":        r"C:\Program Files\Microsoft Office\root\Office16\ONENOTE.EXE",

    # Communication
    "discord":        r"C:\Users\%USERNAME%\AppData\Local\Discord\Update.exe",
    "slack":          r"C:\Users\%USERNAME%\AppData\Local\slack\slack.exe",
    "teams":          r"C:\Users\%USERNAME%\AppData\Local\Microsoft\Teams\current\Teams.exe",
    "zoom":           r"C:\Users\%USERNAME%\AppData\Roaming\Zoom\bin\Zoom.exe",

    # Media
    "vlc":            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    "spotify":        r"C:\Users\%USERNAME%\AppData\Roaming\Spotify\Spotify.exe",

    # Tools
    "git":            r"C:\Program Files\Git\git-bash.exe",
    "postman":        r"C:\Users\%USERNAME%\AppData\Local\Postman\app-\Postman.exe",
    "whatsapp":       r"explorer shell:AppsFolder\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
}

# ── Website URL map ─────────────────────────────────────────────────────────
# Maps friendly names → actual URLs
SITE_MAP: Dict[str, str] = {
    "youtube":        "https://www.youtube.com",
    "google":         "https://www.google.com",
    "gmail":          "https://mail.google.com",
    "chatgpt":        "https://chat.openai.com",
    "github":         "https://github.com",
    "stackoverflow":  "https://stackoverflow.com",
    "reddit":         "https://www.reddit.com",
    "twitter":        "https://twitter.com",
    "x":              "https://x.com",
    "instagram":      "https://www.instagram.com",
    "linkedin":       "https://www.linkedin.com",
    "facebook":       "https://www.facebook.com",
    "amazon":         "https://www.amazon.com",
    "netflix":        "https://www.netflix.com",
}


def _resolve_path(raw: str) -> str:
    """Expand %USERNAME% and other env vars in an app path."""
    return os.path.expandvars(raw)


# ─────────────────────────────────────────────────────────────────────────────
#  Individual action functions
# ─────────────────────────────────────────────────────────────────────────────

def open_app(action: Dict[str, Any]) -> Dict[str, Any]:
    """Open an application by name. Falls back to ShellExecute if path not found."""
    target = str(action.get("target", "")).lower().strip()
    logger.info("▶ open_app: target=%r", target)

    try:
        # 1. Check if it's a known website
        if target in SITE_MAP:
            logger.info("  Target found in SITE_MAP – redirecting to open_url")
            return open_url({"action": "open_url", "target": SITE_MAP[target]})

        # 2. Check if it looks like a URL (heuristic)
        if target.startswith(("http://", "https://")) or \
           (re.search(r"\.[a-z]{2,3}(/|$)", target) and " " not in target):
            logger.info("  Target looks like a URL – redirecting to open_url")
            return open_url({"action": "open_url", "target": target})

        # 3. Lookup in app map, else try the name directly as an executable
        raw_path = APP_PATH_MAP.get(target, target + ".exe")
        exe_path = _resolve_path(raw_path)

        # Check if full path exists; if not, rely on PATH / shell
        if os.path.isabs(exe_path) and not os.path.exists(exe_path):
            logger.warning("  Path '%s' not found – falling back to shell search", exe_path)
            exe_path = target  # let Windows PATH handle it

        process = subprocess.Popen(
            exe_path,
            shell=True,      # shell=True lets Windows find PATH-based commands
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        msg = f"Opened '{target}' (PID {process.pid})"
        logger.info("  ✓ %s", msg)
        return {"success": True, "action": "open_app", "message": msg}

    except FileNotFoundError:
        err = f"Application '{target}' not found on this system"
        logger.error("  ✗ %s", err)
        return {"success": False, "action": "open_app", "error": err}
    except Exception as exc:
        logger.error("  ✗ open_app unexpected error: %s", exc)
        return {"success": False, "action": "open_app", "error": str(exc)}


def open_url(action: Dict[str, Any]) -> Dict[str, Any]:
    """Open a URL in the default web browser."""
    url = str(action.get("target", action.get("value", ""))).strip()
    logger.info("▶ open_url: target=%r", url)

    if not url:
        return {"success": False, "action": "open_url", "error": "No URL provided"}

    # Add protocol if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        webbrowser.open(url)
        msg = f"Opened URL: {url}"
        logger.info("  ✓ %s", msg)
        return {"success": True, "action": "open_url", "message": msg}
    except Exception as exc:
        logger.error("  ✗ open_url error: %s", exc)
        return {"success": False, "action": "open_url", "error": str(exc)}


def search_youtube(action: Dict[str, Any]) -> Dict[str, Any]:
    import urllib.parse
    import webbrowser
    query = action.get("query", action.get("value", action.get("target", "")))
    logger.info("▶ search_youtube: query=%r", query)
    
    if not query:
        return {"success": False, "action": "search_youtube", "error": "No search query provided"}
        
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    try:
        webbrowser.open(url)
        msg = f"Opened YouTube search for: {query}"
        logger.info("  ✓ %s", msg)
        return {"success": True, "action": "search_youtube", "message": msg}
    except Exception as exc:
        logger.error("  ✗ search_youtube error: %s", exc)
        return {"success": False, "action": "search_youtube", "error": str(exc)}


def type_text(action: Dict[str, Any]) -> Dict[str, Any]:
    """Type text using pyautogui, with interval between keystrokes."""
    import pyautogui

    text = str(action.get("value", action.get("target", "")))
    logger.info("▶ type_text: value=%r", text[:60])

    try:
        time.sleep(0.5)   # allow window focus to settle
        pyautogui.typewrite(text, interval=0.04)
        msg = f"Typed {len(text)} characters"
        logger.info("  ✓ %s", msg)
        return {"success": True, "action": "type_text", "message": msg}

    except Exception as exc:
        logger.error("  ✗ type_text error: %s", exc)
        return {"success": False, "action": "type_text", "error": str(exc)}


def press_key(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Press a key or key combination.
    Examples: 'ctrl+c', 'alt+tab', 'win+d', 'enter', 'f5'
    """
    import pyautogui

    combo = str(action.get("value", action.get("target", "enter"))).lower().strip()
    logger.info("▶ press_key: combo=%r", combo)

    try:
        time.sleep(0.5)
        keys = [k.strip() for k in combo.split("+")]
        pyautogui.hotkey(*keys)
        msg = f"Pressed key combo: {combo}"
        logger.info("  ✓ %s", msg)
        return {"success": True, "action": "press_key", "message": msg}

    except Exception as exc:
        logger.error("  ✗ press_key error: %s", exc)
        return {"success": False, "action": "press_key", "error": str(exc)}


def mouse_click(action: Dict[str, Any]) -> Dict[str, Any]:
    """Click at (x, y) screen coordinates."""
    import pyautogui

    x = int(action.get("x", 0))
    y = int(action.get("y", 0))
    button = str(action.get("value", "left")).lower()  # left / right / middle
    logger.info("▶ mouse_click: x=%d y=%d button=%s", x, y, button)

    try:
        time.sleep(0.5)
        pyautogui.click(x, y, button=button)
        msg = f"Clicked {button} at ({x}, {y})"
        logger.info("  ✓ %s", msg)
        return {"success": True, "action": "mouse_click", "message": msg}

    except Exception as exc:
        logger.error("  ✗ mouse_click error: %s", exc)
        return {"success": False, "action": "mouse_click", "error": str(exc)}


def take_screenshot(action: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ARG001
    """Capture the entire screen with mss and save as a timestamped PNG."""
    import mss
    import mss.tools

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"screenshot_{timestamp}.png"
    filepath = SCREENSHOT_DIR / filename
    logger.info("▶ take_screenshot: saving to %s", filepath)

    try:
        with mss.mss() as sct:
            monitor = sct.monitors[0]   # monitor[0] = entire virtual desktop
            raw = sct.grab(monitor)
            mss.tools.to_png(raw.rgb, raw.size, output=str(filepath))

        msg = f"Screenshot saved: {filepath}"
        logger.info("  ✓ %s", msg)
        return {
            "success": True,
            "action": "take_screenshot",
            "message": msg,
            "file_path": str(filepath),
        }

    except Exception as exc:
        logger.error("  ✗ take_screenshot error: %s", exc)
        return {"success": False, "action": "take_screenshot", "error": str(exc)}


def move_mouse(action: Dict[str, Any]) -> Dict[str, Any]:
    """Move mouse pointer smoothly to (x, y)."""
    import pyautogui

    x = int(action.get("x", 0))
    y = int(action.get("y", 0))
    duration = float(action.get("value", 0.4))   # seconds for smooth movement
    logger.info("▶ move_mouse: x=%d y=%d duration=%.2fs", x, y, duration)

    try:
        time.sleep(0.3)
        pyautogui.moveTo(x, y, duration=duration)
        msg = f"Mouse moved to ({x}, {y})"
        logger.info("  ✓ %s", msg)
        return {"success": True, "action": "move_mouse", "message": msg}

    except Exception as exc:
        logger.error("  ✗ move_mouse error: %s", exc)
        return {"success": False, "action": "move_mouse", "error": str(exc)}


def scroll(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scroll at the current mouse position.
    value > 0  → scroll UP (positive clicks)
    value < 0  → scroll DOWN (negative clicks)
    """
    import pyautogui

    # Accept 'up'/'down' strings or numeric values
    raw_val = action.get("value", action.get("target", "3"))
    if isinstance(raw_val, str):
        if raw_val.lower() == "up":
            clicks = 5
        elif raw_val.lower() == "down":
            clicks = -5
        else:
            try:
                clicks = int(raw_val)
            except ValueError:
                clicks = 3
    else:
        clicks = int(raw_val)

    logger.info("▶ scroll: clicks=%d", clicks)

    try:
        time.sleep(0.3)
        pyautogui.scroll(clicks)
        direction = "up" if clicks > 0 else "down"
        msg = f"Scrolled {direction} by {abs(clicks)} clicks"
        logger.info("  ✓ %s", msg)
        return {"success": True, "action": "scroll", "message": msg}

    except Exception as exc:
        logger.error("  ✗ scroll error: %s", exc)
        return {"success": False, "action": "scroll", "error": str(exc)}


def send_whatsapp_message(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send a WhatsApp message via Selenium.

    action fields:
      target : contact name (as it appears in WhatsApp)
      value  : message text to send
    """
    contact = str(action.get("target", "")).strip()
    message = str(action.get("value", "")).strip()
    logger.info("▶ send_whatsapp_message: contact=%r message=%r", contact, message[:60])

    if not contact:
        return {"success": False, "action": "send_whatsapp_message", "error": "'target' (contact name) is required."}
    if not message:
        return {"success": False, "action": "send_whatsapp_message", "error": "'value' (message text) is required."}

    try:
        from automation.whatsapp_desktop_automation import send_whatsapp_message as _wa_send
        result = _wa_send(contact, message)
        ok = result.get("status") == "success"
        return {
            "success": ok,
            "action": "send_whatsapp_message",
            "message": f"Sent to '{contact}': {message[:60]}" if ok else result.get("error", "Unknown error"),
            **result,
        }
    except Exception as exc:
        logger.error("  ✗ send_whatsapp_message error: %s", exc)
        return {"success": False, "action": "send_whatsapp_message", "error": str(exc)}


def read_whatsapp(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read recent messages from a WhatsApp chat.

    action fields:
      target : contact name
      value  : number of messages to read (default 5)
    """
    contact = str(action.get("target", "")).strip()
    try:
        count = int(action.get("value", 5))
    except (TypeError, ValueError):
        count = 5
    logger.info("▶ read_whatsapp: contact=%r count=%d", contact, count)

    if not contact:
        return {"success": False, "action": "read_whatsapp", "error": "'target' (contact name) is required."}

    try:
        from automation.whatsapp_desktop_automation import read_whatsapp as _wa_read
        result = _wa_read(contact, count)
        return {
            "success": result.get("status") == "success",
            "action": "read_whatsapp",
            "message": result.get("error") if result.get("status") == "error" else f"Read {result.get('count', 0)} messages from '{contact}'",
            **result,
        }
    except Exception as exc:
        logger.error("  ✗ read_whatsapp error: %s", exc)
        return {"success": False, "action": "read_whatsapp", "error": str(exc)}


def unknown_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """Graceful fallback: log everything received and return a clear error."""
    action_name = action.get("action", "<none>")
    logger.warning(
        "▶ unknown_action received: action=%r | full payload=%s",
        action_name,
        json.dumps(action, indent=2),
    )
    return {
        "success": False,
        "action": "unknown_action",
        "received": action,
        "error": (
            f"Action '{action_name}' is not implemented. "
            "Supported: open_app, type_text, press_key, mouse_click, "
            "take_screenshot, move_mouse, scroll, "
            "send_whatsapp_message, read_whatsapp."
        ),
    }


# ── Action router ─────────────────────────────────────────────────────────────
_ACTION_MAP = {
    "open_app":               open_app,
    "open_url":               open_url,
    "search_youtube":         search_youtube,
    "type_text":              type_text,
    "press_key":              press_key,
    "mouse_click":            mouse_click,
    "take_screenshot":        take_screenshot,
    "move_mouse":             move_mouse,
    "scroll":                 scroll,
    "send_whatsapp_message":  send_whatsapp_message,
    "read_whatsapp":          read_whatsapp,
}


def execute_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main entry-point. Receives a parsed action dict (from Ollama JSON output)
    and dispatches it to the appropriate handler function.

    Args:
        action: e.g. {"action": "open_app", "target": "notepad", "value": "", "x": 0, "y": 0}

    Returns:
        Result dict with at minimum {"success": bool, "action": str, "message"/"error": str}
    """
    if not isinstance(action, dict):
        logger.error("execute_action: received non-dict input: %r", action)
        return {
            "success": False,
            "action": "invalid_input",
            "error": f"Expected a dict, got {type(action).__name__}",
        }

    action_name = str(action.get("action", "")).lower().strip()
    handler = _ACTION_MAP.get(action_name, unknown_action)

    logger.info("═══ Executing action: %s ═══", action_name or "<empty>")
    result = handler(action)
    logger.info("═══ Result: %s ═══", json.dumps(result))
    return result
