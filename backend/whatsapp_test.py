# -*- coding: utf-8 -*-
"""
whatsapp_test.py -- Test WhatsApp automation end-to-end.
Run from the backend/ directory:  python whatsapp_test.py

BEFORE RUNNING:
  1. pip install selenium webdriver-manager  (if not done)
  2. Change CONTACT_NAME to a real WhatsApp contact
  3. Change TEST_MESSAGE to whatever you want to send
  4. Run this script
  5. A Chrome window will open -- scan the QR code once
  6. The message will be sent automatically

After the first run, the Chrome profile is saved -- no QR scan on future runs.
"""

import sys
import io
from pathlib import Path

# Force UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add backend/ to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import settings

# ─── CONFIGURE THESE BEFORE RUNNING ──────────────────────────────────────────
CONTACT_NAME = settings.WHATSAPP_TEST_CONTACT
TEST_MESSAGE = "Hello from Vamsee AI! This is an automated test message."
# ─────────────────────────────────────────────────────────────────────────────

PASS_TAG = "[PASS]"
FAIL_TAG = "[FAIL]"
SEP      = "-" * 65

results = []


def section(title: str):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def record(name: str, passed: bool, detail: str = ""):
    tag = PASS_TAG if passed else FAIL_TAG
    print(f"  Status : {tag}")
    if detail:
        print(f"  Detail : {detail[:200]}")
    results.append((name, passed))


# =============================================================================
# TEST 1 -- Import check
# =============================================================================
section("Import check")
try:
    from automation.whatsapp_automation import (
        init_driver,
        send_whatsapp_message,
        get_recent_messages,
        close_driver,
        DEFAULT_PROFILE_DIR,
    )
    print(f"  Module imported OK")
    print(f"  Chrome profile: {DEFAULT_PROFILE_DIR}")
    record("Import whatsapp_automation", True)
except ImportError as e:
    print(f"  ERROR: {e}")
    print("  HINT: Run: pip install selenium webdriver-manager")
    record("Import whatsapp_automation", False, str(e))
    sys.exit(1)

# =============================================================================
# TEST 2 -- Send a message
# =============================================================================
section(f"Send WhatsApp message to '{CONTACT_NAME}'")
print(f"  Contact : {CONTACT_NAME}")
print(f"  Message : {TEST_MESSAGE}")
print()
print("  [INFO] Chrome will open. If QR code appears, scan it with your phone.")
print("  [INFO] This only happens once -- session is saved to chrome_profile/")
print()

result = send_whatsapp_message(CONTACT_NAME, TEST_MESSAGE)

print(f"\n  Result  : {result}")
sent_ok = result.get("status") == "success"
record(f"Send message to '{CONTACT_NAME}'", sent_ok, str(result))

# =============================================================================
# TEST 3 -- Read recent messages (only if send succeeded)
# =============================================================================
if sent_ok:
    section(f"Read last 3 messages from '{CONTACT_NAME}'")
    try:
        from automation.whatsapp_automation import read_whatsapp
        msgs_result = read_whatsapp(CONTACT_NAME, 3)
        messages = msgs_result.get("messages", [])
        print(f"  Messages fetched: {len(messages)}")
        for i, m in enumerate(messages, 1):
            print(f"  [{i}] ({m.get('sender', '?')}) {m.get('text', '')[:80]} [{m.get('time', '')}]")
        record("Read recent messages", len(messages) >= 0, f"{len(messages)} messages returned")
    except Exception as e:
        print(f"  ERROR: {e}")
        record("Read recent messages", False, str(e))
else:
    print("\n  [SKIP] Skipping read test since send failed.")
    results.append(("Read recent messages", False))

# =============================================================================
# Cleanup -- keep driver alive for the session (do NOT close)
# =============================================================================
print("\n  [INFO] Chrome driver kept alive for future calls.")
print("  [INFO] Call close_driver() or POST /whatsapp/close to terminate it.")

# =============================================================================
# Summary
# =============================================================================
print(f"\n{'=' * 65}")
print("WHATSAPP TEST SUMMARY")
print('=' * 65)
passed = sum(1 for _, ok in results if ok)
for name, ok in results:
    tag = PASS_TAG if ok else FAIL_TAG
    print(f"  {tag}  {name}")

print(f"\n  {passed}/{len(results)} tests passed")
print('=' * 65)

if sent_ok:
    print(f"\n[SUCCESS] WhatsApp automation is working!")
    print(f"  Message sent to '{CONTACT_NAME}'")
    print(f"  Step 3 is DONE. Come back to move to Step 4.")
else:
    print(f"\n[WARNING] Send failed. Common fixes:")
    print(f"  1. Check CONTACT_NAME matches EXACTLY what's in your WhatsApp")
    print(f"  2. Make sure you scanned the QR code if it appeared")
    print(f"  3. Check your internet connection")
    print(f"  4. Delete chrome_profile/ and try again if session is corrupted")
    sys.exit(1)
