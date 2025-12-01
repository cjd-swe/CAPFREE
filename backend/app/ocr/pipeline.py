import pytesseract
from PIL import Image
import cv2
import numpy as np
import io

# Ensure tesseract is installed and in path
# pytesseract.pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract'

def preprocess_image(image_bytes: bytes) -> Image.Image:
    """
    Convert bytes to PIL Image and perform preprocessing for better OCR.
    """
    image = Image.open(io.BytesIO(image_bytes))
    
    # Convert to grayscale
    # cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    
    # Apply thresholding
    # _, cv_image = cv2.threshold(cv_image, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Convert back to PIL Image
    # image = Image.fromarray(cv_image)
    
    return image

def extract_text(image_bytes: bytes) -> str:
    """
    Extract text from image bytes using Tesseract OCR.
    """
    try:
        image = preprocess_image(image_bytes)
        text = pytesseract.image_to_string(image)
        return text
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""
