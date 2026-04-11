import mss
import numpy as np
import cv2
import pytesseract
from PIL import Image
import os

# Configured Tesseract Path
tess_path = r"V:\Installations\tesseract.exe"
print(f"Using Tesseract path: {tess_path}")

if not os.path.exists(tess_path):
    print(f"❌ ERROR: Tesseract not found at {tess_path}")
    exit(1)

pytesseract.pytesseract.tesseract_cmd = tess_path

print("Starting screen capture...")
try:
    with mss.mss() as sct:
        # Get primary monitor
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        print(f"✅ Screen captured: {screenshot.size}")

    # Convert to numpy array for OpenCV
    img = np.array(screenshot)

    # Save to file
    cv2.imwrite("screen_test.png", img)
    print("✅ Screenshot saved as screen_test.png")

    # Run OCR
    print("Running OCR...")
    text = pytesseract.image_to_string(Image.open("screen_test.png"))

    print("--- Extracted Text ---")
    print(text if text.strip() else "[No text detected]")
    print("----------------------")

except Exception as e:
    print(f"❌ ERROR during test: {e}")
