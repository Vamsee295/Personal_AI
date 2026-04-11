# -*- coding: utf-8 -*-
"""
vision_test.py -- Verify the Vision Module is working end-to-end.
Run from the backend/ directory:  python vision_test.py

Tests:
  1. Full screen capture (mss) -- saves PNG to screenshots/
  2. Active window capture + OCR -- prints extracted text
  3. Region capture + OCR -- top-left quadrant of screen

No Ollama required. This only tests capture + OCR.

Tesseract install (Windows):
  winget install UB-Mannheim.TesseractOCR
  (then restart terminal)
"""

import sys
import io
from pathlib import Path

# Force UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Add backend/ to path so app.* imports work
sys.path.insert(0, str(Path(__file__).resolve().parent))

PASS_TAG = "[PASS]"
FAIL_TAG = "[FAIL]"
SEP      = "-" * 65

results = []


def section(title: str):
    print(f"\n{SEP}")
    print(f"  TEST: {title}")
    print(SEP)


def record(name: str, passed: bool, detail: str = ""):
    tag = PASS_TAG if passed else FAIL_TAG
    print(f"  Status : {tag}")
    if detail:
        print(f"  Detail : {detail}")
    results.append((name, passed))


# =============================================================================
# TEST 1 -- Full screen capture
# =============================================================================
section("Full screen capture (mss)")

try:
    from app.agents.vision_module import capture_full_screen, SCREENSHOT_DIR

    img = capture_full_screen(save=True)
    saved_files = sorted(SCREENSHOT_DIR.glob("vision_*.png"))
    latest = saved_files[-1] if saved_files else None

    print(f"  Captured : {img.width} x {img.height} px")
    print(f"  Saved to : {latest}")
    record("Full screen capture", latest is not None and latest.exists(),
           f"File: {latest}")

except Exception as e:
    print(f"  ERROR: {e}")
    record("Full screen capture", False, str(e))


# =============================================================================
# TEST 2 -- Active window capture + OCR
# =============================================================================
section("Active window capture + Tesseract OCR")

try:
    from app.agents.vision_module import capture_active_window, extract_text_from_image

    print("  Capturing active window...")
    window_img = capture_active_window(save=False)
    print(f"  Window size : {window_img.width} x {window_img.height} px")

    print("  Running OCR (this may take a few seconds)...")
    text = extract_text_from_image(window_img)

    if text:
        print(f"\n  --- OCR OUTPUT ({len(text)} chars) ---")
        # Print first 800 chars with visible line numbers
        for i, line in enumerate(text.splitlines()[:30], 1):
            print(f"  {i:02d}: {line}")
        if len(text.splitlines()) > 30:
            print(f"  ... ({len(text.splitlines()) - 30} more lines)")
        print(f"  --- END OF OCR OUTPUT ---\n")
        record("Active window OCR", True, f"{len(text)} characters extracted")
    else:
        print("  WARNING: OCR returned empty text.")
        print("  This can happen if the screen is very dark or Tesseract is mis-configured.")
        record("Active window OCR", False, "Empty OCR output")

except pytesseract.TesseractNotFoundError if False else Exception as e:
    # Catch both TesseractNotFoundError and generic errors
    error_msg = str(e)
    if "TesseractNotFound" in type(e).__name__ or "tesseract" in error_msg.lower():
        print(f"\n  [!] TESSERACT NOT FOUND")
        print(f"  Install with: winget install UB-Mannheim.TesseractOCR")
        print(f"  Then restart your terminal and run this test again.")
    else:
        print(f"  ERROR: {e}")
    record("Active window OCR", False, error_msg[:120])


# =============================================================================
# TEST 3 -- Region capture + OCR (top-left 800x600 area)
# =============================================================================
section("Region capture + OCR (top-left 800x600 region)")

try:
    from app.agents.vision_module import capture_region, extract_text_from_image

    region_img = capture_region(x=0, y=0, width=800, height=600, save=False)
    print(f"  Region size : {region_img.width} x {region_img.height} px")

    text = extract_text_from_image(region_img)

    if text:
        preview = text[:300].replace("\n", " ")
        print(f"  OCR preview : {preview}")
        record("Region OCR", True, f"{len(text)} characters extracted from region")
    else:
        print("  WARNING: OCR returned empty text for this region.")
        record("Region OCR", False, "Empty OCR output for region")

except Exception as e:
    print(f"  ERROR: {e}")
    record("Region OCR", False, str(e))


# =============================================================================
# Summary
# =============================================================================
print(f"\n{'=' * 65}")
print("VISION TEST SUMMARY")
print('=' * 65)
passed = sum(1 for _, ok in results if ok)
for name, ok in results:
    tag = PASS_TAG if ok else FAIL_TAG
    print(f"  {tag}  {name}")

print(f"\n  {passed}/{len(results)} tests passed")
print('=' * 65)

if passed == len(results):
    print("\n[SUCCESS] Vision Module is working! Tesseract is reading your screen.")
    print("  Next: Try the LLM loop with:")
    print('  curl -X POST http://localhost:8000/api/vision/analyze-screen \\')
    print('       -H "Content-Type: application/json" \\')
    print('       -d \'{"goal": "What app is currently open on my screen?"}\'\n')
else:
    print("\n[WARNING] Some tests failed. Check the output above.")
    if passed == 0:
        print("  Likely cause: Tesseract not installed or not found.")
        print("  Fix: winget install UB-Mannheim.TesseractOCR")
    sys.exit(1)
