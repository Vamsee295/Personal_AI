import mss
import numpy as np
import pytesseract
from PIL import Image
import os

print("--- Environment Verification ---")
try:
    import mss
    print("✅ mss OK")
except ImportError:
    print("❌ mss MISSING")

try:
    import numpy
    print("✅ numpy OK")
except ImportError:
    print("❌ numpy MISSING")

try:
    import pytesseract
    print("✅ pytesseract OK")
except ImportError:
    print("❌ pytesseract MISSING")

try:
    from PIL import Image
    print("✅ Pillow (PIL) OK")
except ImportError:
    print("❌ Pillow (PIL) MISSING")

from app.config import settings

tess_path = settings.TESSERACT_PATH or r"V:\Installations\tesseract.exe"
if tess_path and os.path.exists(tess_path):
    print(f"✅ Tesseract Binary found at: {tess_path}")
    pytesseract.pytesseract.tesseract_cmd = tess_path
    try:
        ver = pytesseract.get_tesseract_version()
        print(f"✅ Tesseract Version: {ver}")
    except Exception as e:
        print(f"❌ Tesseract execution failed: {e}")
else:
    print(f"❌ Tesseract Binary NOT FOUND at: {tess_path}")
