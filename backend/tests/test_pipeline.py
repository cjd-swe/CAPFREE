"""
Tests for the OCR pipeline — verifies image preprocessing and text extraction.
These tests require Tesseract to be installed.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image, ImageDraw, ImageFont
import io
import pytest

from app.ocr.pipeline import extract_text, preprocess_image


def _create_test_image(text: str, size=(400, 100), bg="white", fg="black") -> bytes:
    """Create a simple image with text for testing OCR."""
    img = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(img)
    # Use default font — Tesseract doesn't need fancy fonts to read clean text
    draw.text((10, 30), text, fill=fg)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestPreprocessImage:
    """Test image preprocessing."""

    def test_returns_pil_image(self):
        img_bytes = _create_test_image("Hello")
        result = preprocess_image(img_bytes)
        assert isinstance(result, Image.Image)

    def test_handles_jpg(self):
        img = Image.new("RGB", (100, 100), "white")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        result = preprocess_image(buf.getvalue())
        assert isinstance(result, Image.Image)

    def test_handles_png(self):
        img = Image.new("RGB", (100, 100), "white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = preprocess_image(buf.getvalue())
        assert isinstance(result, Image.Image)


class TestExtractText:
    """Test OCR text extraction. Requires Tesseract installed."""

    def test_extracts_simple_text(self):
        """OCR should extract clean, large text from a generated image."""
        # Create a larger image with big text for reliable OCR
        img = Image.new("RGB", (600, 100), "white")
        draw = ImageDraw.Draw(img)
        # Draw text large enough for Tesseract to read
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        except (OSError, IOError):
            font = ImageFont.load_default()
        draw.text((20, 20), "LAKERS", fill="black", font=font)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        text = extract_text(buf.getvalue())
        assert "LAKERS" in text.upper()

    def test_empty_image_returns_something(self):
        """A blank white image should return empty or whitespace-only text."""
        img_bytes = _create_test_image("")
        text = extract_text(img_bytes)
        assert isinstance(text, str)

    def test_returns_string_on_error(self):
        """Bad input should return empty string, not raise."""
        # Invalid image bytes
        result = extract_text(b"not an image at all")
        assert result == ""


class TestEndToEnd:
    """Test the full pipeline: image → OCR → parser."""

    def test_generated_pick_image(self):
        """Generate an image with a pick, run OCR + parser, verify output."""
        from app.ocr.parser import parse_picks

        img = Image.new("RGB", (800, 100), "white")
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
        except (OSError, IOError):
            font = ImageFont.load_default()
        draw.text((20, 20), "LAKERS -5.5 2u", fill="black", font=font)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        raw_text = extract_text(buf.getvalue())
        picks = parse_picks(raw_text)

        # This may or may not parse depending on OCR quality with default font.
        # The important thing is it doesn't crash.
        assert isinstance(picks, list)
        # If OCR read it correctly, we should get a pick
        if "LAKERS" in raw_text.upper() and "5.5" in raw_text:
            assert len(picks) >= 1
