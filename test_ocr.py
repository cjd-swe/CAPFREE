import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

from backend.app.ocr import pipeline, parser

# Test OCR with the test image
image_path = "/Users/camerondavis/Projects/Coding/CAPFREE/test_betting_slip.png"

with open(image_path, 'rb') as f:
    image_bytes = f.read()

print("Running OCR on test image...")
raw_text = pipeline.extract_text(image_bytes)
print(f"\nExtracted Text:\n{raw_text}\n")

print("Parsing picks...")
picks = parser.parse_picks(raw_text)
print(f"\nParsed Picks ({len(picks)} found):")
for i, pick in enumerate(picks, 1):
    print(f"{i}. {pick}")
