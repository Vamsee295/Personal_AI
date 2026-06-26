"""
automation/whatsapp_automation.py -- Selenium-powered WhatsApp Web controller.

HOW THE CHROME PROFILE TRICK WORKS
------------------------------------
Normal Selenium opens a fresh, blank Chrome session every time -- no cookies,
no login state, nothing. WhatsApp Web would show the QR code on EVERY run.

By pointing ChromeOptions at a persistent --user-data-dir on disk, Chrome saves
ALL session data (cookies, localStorage, IndexedDB) between runs. The first time
you run this, scan the QR code once with your phone. After that, every subsequent
run finds WhatsApp already logged in -- no QR code, instant access.

The profile directory is: backend/chrome_profile/  (auto-created on first run)

INSTALL REQUIREMENTS
---------------------
  pip install selenium webdriver-manager

ChromeDriver is auto-managed by webdriver_manager -- no manual download needed.
It detects your installed Chrome version and downloads the matching driver.

USAGE
------
  from automation.whatsapp_automation import send_whatsapp_message
  result = send_whatsapp_message("Ravi", "Good morning!")
  print(result)  # {"status": "success", "contact": "Ravi", "message": "Good morning!"}
"""

from __future__ import annotations

import time
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("whatsapp_automation")

# ── Constants ─────────────────────────────────────────────────────────────────
WHATSAPP_URL     = "https://web.whatsapp.com"
DEFAULT_TIMEOUT  = 90    # seconds to wait for WhatsApp to load / QR scan
SEARCH_TIMEOUT   = 15    # seconds to wait for search results
MESSAGE_TIMEOUT  = 10    # seconds to wait for message box

# Absolute path to the persistent Chrome profile directory
_BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_PROFILE_DIR = str(_BACKEND_DIR / "chrome_profile")

# ── Selenium selectors (WhatsApp Web DOM) ─────────────────────────────────────
# These target stable aria-labels / data-testid attributes rather than
# fragile class names, which WhatsApp obfuscates and rotates frequently.

# Search input (click to open, then type)
SEL_SEARCH_BOX      = 'div[contenteditable="true"][data-tab="3"]'
SEL_SEARCH_BOX_ALT  = 'div[aria-label="Search input textbox"]'

# Contact result rows in the search panel
SEL_CONTACT_RESULT  = 'div[aria-label="Search results."] span[dir="auto"] span[title]'
SEL_CONTACT_ROW     = 'div[data-testid="cell-frame-container"]'

# Message input box inside an open chat
SEL_MSG_BOX         = 'div[contenteditable="true"][data-tab="10"]'
SEL_MSG_BOX_ALT     = 'div[aria-label="Type a message"]'

# Indicator that WhatsApp is fully loaded (side panel visible)
SEL_SIDE_PANEL      = 'div[id="side"]'

# QR code canvas (shown when not logged in)
SEL_QR_CODE         = 'canvas[aria-label="Scan me!"]'

# Sent message indicator (double tick or clock icon)
SEL_MSG_SENT        = 'span[data-icon="msg-time"], span[data-icon="msg-dblcheck"]'


# =============================================================================
#  DRIVER INITIALISATION
# =============================================================================

def init_driver(profile_dir: str = DEFAULT_PROFILE_DIR):
    """
    Initialize Chrome via Selenium with a persistent user profile.

    The profile_dir stores all Chrome session data (cookies, cache, localStorage).
    Scanning the WhatsApp QR code once is enough -- all future runs skip it.

    Anti-detection options are applied so WhatsApp doesn't flag as a bot.

    Returns:
        selenium.webdriver.Chrome instance
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    profile_path = Path(profile_dir)
    profile_path.mkdir(parents=True, exist_ok=True)
    logger.info("Chrome profile directory: %s", profile_path)

    opts = Options()

    # ── Persistent session (the QR trick) ────────────────────────────────────
    opts.add_argument(f"--user-data-dir={profile_path}")

    # ── Anti-detection flags ──────────────────────────────────────────────────
    # Removes "Chrome is being controlled by automated software" banner
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    # Disables the navigator.webdriver flag that WhatsApp checks
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    # Realistic window size
    opts.add_argument("--window-size=1280,800")
    # Use a real user-agent string
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # ── Auto-managed ChromeDriver ─────────────────────────────────────────────
    logger.info("Downloading / verifying ChromeDriver via webdriver_manager...")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)

    # Patch navigator.webdriver to False at runtime
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )

    logger.info("Chrome driver initialised. Window: %s", driver.get_window_size())
    return driver


# =============================================================================
#  WHATSAPP LOAD + LOGIN
# =============================================================================

def wait_for_whatsapp_load(driver, timeout: int = DEFAULT_TIMEOUT) -> None:
    """
    Navigate to WhatsApp Web and wait until the user is logged in
    (side panel visible). If the QR code is showing, print a clear
    human-readable prompt and keep polling until login completes.

    Raises:
        TimeoutException if login doesn't complete within `timeout` seconds.
    """

    logger.info("Opening WhatsApp Web...")
    print("[WhatsApp] Opening https://web.whatsapp.com ...")
    driver.get(WHATSAPP_URL)

    # Give the page a moment to settle before checking state
    time.sleep(3)

    # Poll until either logged in or QR appears
    deadline = time.time() + timeout
    qr_noticed = False

    while time.time() < deadline:
        # Check if fully loaded (side panel present)
        side_panels = driver.find_elements("css selector", SEL_SIDE_PANEL)
        if side_panels and side_panels[0].is_displayed():
            logger.info("WhatsApp Web loaded and logged in.")
            print("[WhatsApp] Loaded and logged in!")
            return

        # Check for QR code
        qr_elements = driver.find_elements("css selector", SEL_QR_CODE)
        if qr_elements and not qr_noticed:
            print("\n" + "=" * 60)
            print("  WHATSAPP QR CODE DETECTED")
            print("  Please scan the QR code in the Chrome window with your phone.")
            print("  Your session will be saved -- you only need to do this ONCE.")
            print("=" * 60 + "\n")
            logger.info("QR code visible -- waiting for user to scan...")
            qr_noticed = True

        time.sleep(2)

    # Final check
    side_panels = driver.find_elements("css selector", SEL_SIDE_PANEL)
    if side_panels and side_panels[0].is_displayed():
        return

    raise TimeoutError(
        f"WhatsApp did not load within {timeout}s. "
        "Check if the Chrome window opened and if QR was scanned."
    )


# =============================================================================
#  CONTACT SEARCH
# =============================================================================

def search_contact(driver, contact_name: str) -> None:
    """
    Open the WhatsApp search box and type the contact name character-by-character.

    Uses small delays between characters to mimic human typing and avoid
    WhatsApp's debounce dropping characters.

    Raises:
        Exception if the search box cannot be found or clicked.
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys

    logger.info("Searching for contact: %r", contact_name)
    print(f"[WhatsApp] Searching for '{contact_name}'...")

    wait = WebDriverWait(driver, SEARCH_TIMEOUT)

    # Try primary selector, fall back to alt
    try:
        search_box = wait.until(
            EC.element_to_be_clickable(("css selector", SEL_SEARCH_BOX))
        )
    except Exception:
        search_box = wait.until(
            EC.element_to_be_clickable(("css selector", SEL_SEARCH_BOX_ALT))
        )

    # Click to focus, clear any existing text
    search_box.click()
    time.sleep(0.4)

    # Clear with triple-click + delete
    ActionChains(driver).triple_click(search_box).perform()
    search_box.send_keys(Keys.DELETE)
    time.sleep(0.3)

    # Type contact name slowly for reliability
    for char in contact_name:
        search_box.send_keys(char)
        time.sleep(0.08)

    logger.info("Typed contact name into search box.")
    # Wait for results to appear
    time.sleep(1.5)


def click_first_result(driver) -> str:
    """
    Click the first contact that appears in the search results.

    Returns:
        The title/name of the contact that was clicked.

    Raises:
        Exception if no results found within SEARCH_TIMEOUT.
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    print("[WhatsApp] Clicking first search result...")
    logger.info("Waiting for search results...")

    wait = WebDriverWait(driver, SEARCH_TIMEOUT)

    # Wait for at least one result row
    rows = wait.until(
        EC.presence_of_all_elements_located(("css selector", SEL_CONTACT_ROW))
    )

    if not rows:
        raise RuntimeError("No contact results found in WhatsApp search.")

    # Click the first row
    first = rows[0]
    contact_title = first.get_attribute("aria-label") or "Unknown"
    first.click()
    logger.info("Clicked contact: %s", contact_title)
    print(f"[WhatsApp] Opened chat with: {contact_title}")

    # Let the chat window load
    time.sleep(1.5)
    return contact_title


# =============================================================================
#  SEND MESSAGE
# =============================================================================

def send_message(driver, message: str) -> None:
    """
    Type and send a message in the currently open WhatsApp chat.

    Uses ActionChains for reliable typing on WhatsApp's contenteditable input.
    Retries once if the message box is stale or not interactable.

    Raises:
        Exception if the message box cannot be found or message fails to send.
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys

    print(f"[WhatsApp] Sending message: '{message[:60]}{'...' if len(message) > 60 else ''}'")
    logger.info("Locating message input box...")

    wait = WebDriverWait(driver, MESSAGE_TIMEOUT)

    def _get_msg_box():
        try:
            return wait.until(
                EC.element_to_be_clickable(("css selector", SEL_MSG_BOX))
            )
        except Exception:
            return wait.until(
                EC.element_to_be_clickable(("css selector", SEL_MSG_BOX_ALT))
            )

    try:
        msg_box = _get_msg_box()
        msg_box.click()
        time.sleep(0.3)
        ActionChains(driver).send_keys_to_element(msg_box, message).perform()
    except Exception as exc:
        # Retry once
        logger.warning("First attempt to type message failed (%s), retrying...", exc)
        time.sleep(1)
        msg_box = _get_msg_box()
        msg_box.click()
        time.sleep(0.3)
        ActionChains(driver).send_keys_to_element(msg_box, message).perform()

    time.sleep(0.4)

    # Press Enter to send
    msg_box.send_keys(Keys.ENTER)
    logger.info("Message sent.")

    # Brief wait to confirm the input cleared (message was accepted)
    time.sleep(1.0)
    try:
        current_text = msg_box.get_attribute("textContent") or ""
        if current_text.strip():
            logger.warning("Message box not cleared after send -- message may not have been sent.")
    except Exception:
        pass  # stale element is actually fine -- chat may have refreshed

    print("[WhatsApp] Message sent!")


# =============================================================================
#  HIGH-LEVEL SEND FUNCTION (main entry point)
# =============================================================================

# Module-level driver singleton -- keeps Chrome alive between calls
_driver = None


def send_whatsapp_message(
    contact_name: str,
    message: str,
    profile_dir: str = DEFAULT_PROFILE_DIR,
) -> Dict[str, Any]:
    """
    Full pipeline: Open Chrome -> Load WhatsApp -> Search -> Click -> Send.

    The Chrome driver is kept alive in a module-level singleton so subsequent
    calls reuse the same browser window (much faster than relaunching).

    Args:
        contact_name : Name of the WhatsApp contact (as it appears in WhatsApp).
        message      : Text to send.
        profile_dir  : Path to persistent Chrome profile directory.

    Returns:
        {"status": "success", "contact": ..., "message": ..., "chat_opened": ...}
        or {"status": "error", "error": ..., "contact": ..., "message": ...}
    """
    global _driver

    print(f"\n{'='*55}")
    print(f"  WhatsApp Automation: Sending to '{contact_name}'")
    print(f"{'='*55}\n")

    try:
        # Initialise or reuse driver
        if _driver is None:
            logger.info("Initialising new Chrome driver...")
            _driver = init_driver(profile_dir)
        else:
            logger.info("Reusing existing Chrome driver.")

        # Load WhatsApp (waits for login / QR scan if needed)
        wait_for_whatsapp_load(_driver)

        # Search and open contact
        search_contact(_driver, contact_name)
        chat_title = click_first_result(_driver)

        # Send the message
        send_message(_driver, message)

        print(f"\n[WhatsApp] Done! Message delivered to '{chat_title}'")
        return {
            "status":      "success",
            "contact":     contact_name,
            "chat_opened": chat_title,
            "message":     message,
        }

    except TimeoutError as exc:
        logger.error("Timeout during WhatsApp automation: %s", exc)
        return {"status": "error", "contact": contact_name, "message": message, "error": str(exc)}
    except RuntimeError as exc:
        logger.error("Runtime error: %s", exc)
        return {"status": "error", "contact": contact_name, "message": message, "error": str(exc)}
    except Exception as exc:
        logger.exception("Unexpected error in send_whatsapp_message")
        # Reset driver on unexpected errors so next call gets a fresh browser
        try:
            if _driver:
                _driver.quit()
        except Exception:
            pass
        _driver = None
        return {"status": "error", "contact": contact_name, "message": message, "error": str(exc)}


# =============================================================================
#  READ RECENT MESSAGES
# =============================================================================

def get_recent_messages(
    driver,
    contact_name: str,
    count: int = 5,
) -> List[Dict[str, str]]:
    """
    Scrape the last `count` messages from an open WhatsApp chat.

    If the chat for `contact_name` isn't already open, it searches and opens it.

    Returns:
        List of dicts: [{"sender": "...", "text": "...", "time": "..."}]
        Returns [] on failure rather than raising.
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    try:
        wait_for_whatsapp_load(driver)
        search_contact(driver, contact_name)
        click_first_result(driver)

        wait = WebDriverWait(driver, MESSAGE_TIMEOUT)

        # WhatsApp message rows
        SEL_MSG_ROW  = 'div.message-in, div.message-out'
        SEL_MSG_TEXT = 'span.selectable-text span'
        SEL_MSG_TIME = 'div[data-testid="msg-meta"] span'

        # Wait for at least one message row
        try:
            wait.until(EC.presence_of_element_located(("css selector", SEL_MSG_ROW)))
        except Exception:
            logger.warning("No message rows found in chat.")
            return []

        rows = driver.find_elements("css selector", SEL_MSG_ROW)
        rows = rows[-count:]   # take only the last N

        messages: List[Dict[str, str]] = []
        for row in rows:
            try:
                # Determine sender (in = contact, out = you)
                classes = row.get_attribute("class") or ""
                sender = "them" if "message-in" in classes else "you"

                # Extract text
                text_els = row.find_elements("css selector", SEL_MSG_TEXT)
                text = " ".join(el.text for el in text_els).strip()

                # Extract timestamp
                time_els = row.find_elements("css selector", SEL_MSG_TIME)
                timestamp = time_els[0].text.strip() if time_els else ""

                if text:
                    messages.append({"sender": sender, "text": text, "time": timestamp})
            except Exception:
                continue

        logger.info("Scraped %d messages from chat with %s", len(messages), contact_name)
        return messages

    except Exception as exc:
        logger.error("get_recent_messages failed: %s", exc)
        return []


def read_whatsapp(contact_name: str, count: int = 5) -> Dict[str, Any]:
    """
    Convenience wrapper: open chat with contact and return recent messages.
    Uses the module-level driver singleton.
    """
    global _driver
    if _driver is None:
        _driver = init_driver()

    messages = get_recent_messages(_driver, contact_name, count)
    return {
        "status":   "success" if messages else "empty",
        "contact":  contact_name,
        "messages": messages,
        "count":    len(messages),
    }


# =============================================================================
#  DRIVER LIFECYCLE
# =============================================================================

def close_driver(driver=None) -> None:
    """
    Safely quit the Chrome driver.
    If driver is None, quits the module-level singleton.
    """
    global _driver
    target = driver or _driver
    if target:
        try:
            target.quit()
            logger.info("Chrome driver closed.")
        except Exception as exc:
            logger.warning("Error closing driver: %s", exc)
    if driver is None:
        _driver = None


def get_driver(profile_dir: str = DEFAULT_PROFILE_DIR):
    """Return the module-level driver singleton, initialising it if needed."""
    global _driver
    if _driver is None:
        _driver = init_driver(profile_dir)
    return _driver
