# -*- coding: utf-8 -*-
"""
test_executor.py -- Smoke-tests for action_executor.py
Run from the backend/ directory:  python test_executor.py

Tests 5 real actions without needing Ollama running.
Each test prints PASS/FAIL with details.
"""

import sys
import os
import time
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Ensure backend/ is on the Python path so app.* imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.action_executor import execute_action

PASS_TAG = "[PASS]"
FAIL_TAG = "[FAIL]"
SEP      = "-" * 60

results = []


def run_test(name: str, action: dict):
    print(f"\n{SEP}")
    print(f"TEST: {name}")
    print(f"Input : {action}")
    result = execute_action(action)
    print(f"Output: {result}")
    ok = result.get("success", False)
    tag = PASS_TAG if ok else FAIL_TAG
    print(f"Status: {tag}")
    results.append((name, ok, result))
    return result


# ---------------------------------------------------------------
# Test 1 -- open_app: Notepad
# ---------------------------------------------------------------
run_test(
    "open_app -- Notepad",
    {"action": "open_app", "target": "notepad", "value": "", "x": 0, "y": 0},
)

# Give Notepad time to open before we type into it
print("\n[INFO] Waiting 2 seconds for Notepad to open...")
time.sleep(2)

# ---------------------------------------------------------------
# Test 2 -- type_text: "Hello World from Vamsee AI!"
# ---------------------------------------------------------------
run_test(
    "type_text -- Hello World",
    {"action": "type_text", "target": "", "value": "Hello World from Vamsee AI!", "x": 0, "y": 0},
)

# ---------------------------------------------------------------
# Test 3 -- press_key: Enter (new line in Notepad)
# ---------------------------------------------------------------
run_test(
    "press_key -- Enter",
    {"action": "press_key", "target": "", "value": "enter", "x": 0, "y": 0},
)

# ---------------------------------------------------------------
# Test 4 -- take_screenshot
# ---------------------------------------------------------------
result_ss = run_test(
    "take_screenshot -- full screen",
    {"action": "take_screenshot", "target": "", "value": "", "x": 0, "y": 0},
)
if result_ss.get("success"):
    fp = result_ss.get("file_path", "")
    exists = Path(fp).exists() if fp else False
    check = PASS_TAG if exists else FAIL_TAG
    print(f"File exists on disk? {check} ({fp})")

# ---------------------------------------------------------------
# Test 5 -- unknown_action: graceful fallback
# ---------------------------------------------------------------
result_unk = run_test(
    "unknown_action -- graceful fallback",
    {"action": "fly_to_mars", "target": "Mars", "value": "42", "x": 0, "y": 0},
)
# For unknown_action we EXPECT success=False -- that IS the correct behavior
ok = not result_unk.get("success", True)   # False is the right answer here
tag = PASS_TAG if ok else FAIL_TAG
print(f"Fallback returned failure as expected? {tag}")
# Fix the recorded result
results[-1] = (results[-1][0], ok, result_unk)


# ---------------------------------------------------------------
# Summary
# ---------------------------------------------------------------
print(f"\n{'=' * 60}")
print("TEST SUMMARY")
print('=' * 60)
passed = sum(1 for _, ok, _ in results if ok)
for name, ok, _ in results:
    tag = PASS_TAG if ok else FAIL_TAG
    print(f"  {tag}  {name}")

print(f"\n{'=' * 60}")
print(f"  {passed}/{len(results)} tests passed")
print('=' * 60)

if passed == len(results):
    print("\n[SUCCESS] All tests passed! Step 1 complete -- your agent has hands.\n")
else:
    print("\n[WARNING] Some tests failed -- check the output above for details.\n")
    sys.exit(1)
