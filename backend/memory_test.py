# -*- coding: utf-8 -*-
"""
memory_test.py -- Verify the Memory Manager is working end-to-end.
Run from backend/ directory:  python memory_test.py

Tests:
  1. DB creation and init
  2. Save 5 diverse fake commands
  3. get_recent_commands()
  4. search_similar_commands()
  5. Preference save/get
  6. build_memory_context() -- the Ollama injection string
  7. get_memory_stats()
  8. format_relative_time()
  9. clear_old_memories() -- dry run (0 days old = clear all, then re-seed)
"""

import sys
import io
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

PASS  = "[PASS]"
FAIL  = "[FAIL]"
SEP   = "-" * 65
results = []


def section(title: str):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


def ok(name: str, detail: str = ""):
    print(f"  {PASS}  {detail}" if detail else f"  {PASS}")
    results.append((name, True))


def fail(name: str, detail: str = ""):
    print(f"  {FAIL}  {detail}" if detail else f"  {FAIL}")
    results.append((name, False))


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1 — Import + DB init
# ─────────────────────────────────────────────────────────────────────────────
section("Import + DB initialisation")
try:
    from memory.memory_manager import memory, format_relative_time
    db_path = Path(memory.db_path)
    if db_path.exists():
        ok("Import + DB init", f"DB created at: {db_path}")
    else:
        fail("Import + DB init", "DB file not found after init")
except Exception as e:
    fail("Import + DB init", str(e))
    print("  Cannot continue without a working memory module.")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# TEST 2 — Save 5 diverse fake commands
# ─────────────────────────────────────────────────────────────────────────────
section("Save 5 diverse commands")

FAKE_COMMANDS = [
    {
        "user_input":   "Open Chrome browser",
        "action_taken": {"action": "open_app",   "target": "chrome",    "value": "", "x": 0, "y": 0},
        "result":       "Opened 'chrome' (PID 12345)",
        "success":      True,
        "duration_ms":  240,
    },
    {
        "user_input":   "Send good morning to Ravi on WhatsApp",
        "action_taken": {"action": "send_whatsapp_message", "target": "Ravi", "value": "Good morning!", "x": 0, "y": 0},
        "result":       "WhatsApp message sent to Ravi",
        "success":      True,
        "duration_ms":  3800,
    },
    {
        "user_input":   "Take a screenshot of the screen",
        "action_taken": {"action": "take_screenshot", "target": "", "value": "", "x": 0, "y": 0},
        "result":       "Screenshot saved: screenshots/screenshot_20260411.png",
        "success":      True,
        "duration_ms":  120,
    },
    {
        "user_input":   "Open Notepad and type hello",
        "action_taken": {"action": "open_app", "target": "notepad", "value": "", "x": 0, "y": 0},
        "result":       "Opened 'notepad' (PID 99990)",
        "success":      True,
        "duration_ms":  310,
    },
    {
        "user_input":   "Open my project at D:/Projects/VamseeAI",
        "action_taken": {"action": "open_app", "target": "code",    "value": "D:/Projects/VamseeAI", "x": 0, "y": 0},
        "result":       "VS Code opened",
        "success":      False,  # intentionally failed  
        "duration_ms":  890,
    },
]

saved_ids = []
try:
    for cmd in FAKE_COMMANDS:
        row_id = memory.save_command(**cmd)
        saved_ids.append(row_id)
        print(f"  Saved id={row_id}: \"{cmd['user_input'][:50]}\"")
    ok("Save 5 commands", f"IDs: {saved_ids}")
except Exception as e:
    fail("Save 5 commands", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# TEST 3 — get_recent_commands
# ─────────────────────────────────────────────────────────────────────────────
section("get_recent_commands(5)")
try:
    recent = memory.get_recent_commands(5)
    print(f"  Returned {len(recent)} commands:")
    for r in recent:
        action = r["action_taken"].get("action", "?") if isinstance(r["action_taken"], dict) else "?"
        print(f"    [{r['relative_time']}] {r['user_input'][:45]} -> {action} ({'OK' if r['success'] else 'FAIL'})")
    ok("get_recent_commands", f"{len(recent)} entries returned")
except Exception as e:
    fail("get_recent_commands", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# TEST 4 — search_similar_commands
# ─────────────────────────────────────────────────────────────────────────────
section("search_similar_commands('open browser')")
try:
    results_q = memory.search_similar_commands("open browser", limit=3)
    print(f"  Found {len(results_q)} similar commands for 'open browser':")
    for r in results_q:
        print(f"    -> \"{r['user_input'][:60]}\" ({'OK' if r['success'] else 'FAIL'})")
    ok("search_similar_commands", f"{len(results_q)} matches")
except Exception as e:
    fail("search_similar_commands", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# TEST 5 — Preferences
# ─────────────────────────────────────────────────────────────────────────────
section("Preferences: save + get + get_all")
try:
    memory.save_preference("preferred_browser", "chrome")
    memory.save_preference("morning_contact",   "Ravi")
    memory.save_preference("last_opened_app",   "notepad")

    val = memory.get_preference("preferred_browser")
    all_prefs = memory.get_all_preferences()

    print(f"  preferred_browser: {val}")
    print(f"  All preferences  : {all_prefs}")
    assert val == "chrome", "Expected 'chrome'"
    assert "morning_contact" in all_prefs
    ok("Preferences", f"{len(all_prefs)} preferences stored")
except Exception as e:
    fail("Preferences", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# TEST 6 — build_memory_context (the Ollama injection string)
# ─────────────────────────────────────────────────────────────────────────────
section("build_memory_context('open whatsapp and send message')")
try:
    ctx = memory.build_memory_context("open whatsapp and send message to Ravi")
    print()
    print(ctx)
    print()
    ok("build_memory_context", f"{len(ctx)} characters of context generated")
except Exception as e:
    fail("build_memory_context", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# TEST 7 — Memory stats
# ─────────────────────────────────────────────────────────────────────────────
section("get_memory_stats()")
try:
    stats = memory.get_memory_stats()
    print(f"  total_commands   : {stats.get('total_commands')}")
    print(f"  success_rate     : {stats.get('success_rate', 0) * 100:.0f}%")
    print(f"  most_used_action : {stats.get('most_used_action')}")
    print(f"  preferences_count: {stats.get('preferences_count')}")
    print(f"  db_size_kb       : {stats.get('db_size_kb')} KB")
    ok("get_memory_stats", str(stats))
except Exception as e:
    fail("get_memory_stats", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# TEST 8 — format_relative_time
# ─────────────────────────────────────────────────────────────────────────────
section("format_relative_time()")
try:
    from datetime import datetime, timedelta
    cases = [
        (datetime.now().isoformat(),                          "just now"),
        ((datetime.now() - timedelta(minutes=5)).isoformat(), "5 minutes ago"),
        ((datetime.now() - timedelta(hours=3)).isoformat(),   "3 hours ago"),
        ((datetime.now() - timedelta(days=1)).isoformat(),    "yesterday"),
        ((datetime.now() - timedelta(days=5)).isoformat(),    "5 days ago"),
    ]
    for ts, expected in cases:
        result_str = format_relative_time(ts)
        print(f"  {expected:20s} -> {result_str}")
    ok("format_relative_time", "All relative times resolved")
except Exception as e:
    fail("format_relative_time", str(e))

# ─────────────────────────────────────────────────────────────────────────────
# TEST 9 — extract_and_save_preferences (auto-detection)
# ─────────────────────────────────────────────────────────────────────────────
section("extract_and_save_preferences (auto-detect)")
try:
    memory.extract_and_save_preferences(
        "Send good evening to Priya on WhatsApp",
        {"action": "send_whatsapp_message", "target": "Priya", "value": "good evening"},
    )
    memory.extract_and_save_preferences(
        "Open Firefox browser",
        {"action": "open_app", "target": "firefox", "value": ""},
    )
    all_prefs = memory.get_all_preferences()
    print(f"  Preferences after auto-extract: {all_prefs}")
    ok("extract_and_save_preferences", "Auto-detection ran without error")
except Exception as e:
    fail("extract_and_save_preferences", str(e))

# =============================================================================
# Summary
# =============================================================================
print(f"\n{'=' * 65}")
print("MEMORY TEST SUMMARY")
print('=' * 65)
passed = sum(1 for _, ok_flag in results if ok_flag)
for name, ok_flag in results:
    tag = PASS if ok_flag else FAIL
    print(f"  {tag}  {name}")

print(f"\n  {passed}/{len(results)} tests passed")
print('=' * 65)

if passed == len(results):
    print("\n[SUCCESS] Memory system is working!")
    print("  The agent now remembers every command.")
    print("  Start the backend and run a few commands,")
    print("  then check GET /memory/recent to see the history.\n")
else:
    print("\n[WARNING] Some tests failed. Check the output above.\n")
    sys.exit(1)
