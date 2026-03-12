import pytesseract
from PIL import Image
import cv2
import numpy as np
import io
import logging

logger = logging.getLogger(__name__)

# Tesseract config — PSM 11 finds text anywhere on page (best for complex layouts)
_TESS_CONFIG = "--psm 11 --oem 3"


def _is_dark_image(gray: np.ndarray) -> bool:
    """Return True if image has predominantly dark background (light-on-dark text)."""
    return float(np.mean(gray)) < 127


def preprocess_image(image_bytes: bytes) -> Image.Image:
    """Public alias kept for backwards compatibility with tests."""
    return _preprocess(image_bytes)


def _preprocess(image_bytes: bytes) -> Image.Image:
    """
    Preprocess image bytes for best Tesseract accuracy:
    1. Auto-detect dark background and invert (light text → dark text on white)
    2. Upscale if too small (Tesseract needs ~300 DPI equivalent)
    3. Apply Otsu thresholding to clean up text/background separation
    """
    pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

    # Auto-invert dark-background images
    if _is_dark_image(gray):
        logger.debug("Dark background detected — inverting image")
        gray = cv2.bitwise_not(gray)

    # Upscale if width is too small for reliable OCR
    h, w = gray.shape
    if w < 1400:
        scale = 1400 / w
        gray = cv2.resize(gray, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)

    # Otsu thresholding: works well for bimodal histograms (text vs background)
    _, thresh = cv2.threshold(gray, 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return Image.fromarray(thresh)


def extract_text(image_bytes: bytes) -> str:
    """
    Extract text from image bytes using Tesseract OCR.
    Runs two passes — standard preprocessing and a fallback with lighter
    thresholding — and returns whichever gives more text.
    """
    try:
        # Pass 1: full preprocessing (invert + threshold)
        img1 = _preprocess(image_bytes)
        text1 = pytesseract.image_to_string(img1, config=_TESS_CONFIG)

        # Pass 2: grayscale only (no hard threshold) — better for some noisy images
        pil_img = Image.open(io.BytesIO(image_bytes)).convert("L")
        arr = np.array(pil_img)
        if _is_dark_image(arr):
            arr = cv2.bitwise_not(arr)
        h, w = arr.shape
        if w < 1400:
            arr = cv2.resize(arr, None, fx=1400/w, fy=1400/w,
                             interpolation=cv2.INTER_CUBIC)
        img2 = Image.fromarray(arr)
        text2 = pytesseract.image_to_string(img2, config=_TESS_CONFIG)

        # Return whichever pass extracted more content
        result = text1 if len(text1) >= len(text2) else text2
        return result.strip()

    except Exception as e:
        logger.error(f"OCR error: {e}")
        return ""
