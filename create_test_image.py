from PIL import Image, ImageDraw, ImageFont
import os

# Create a simple betting slip image
width, height = 400, 300
image = Image.new('RGB', (width, height), color='white')
draw = ImageDraw.Draw(image)

# Add text (using default font since we may not have custom fonts)
text_lines = [
    "TODAY'S PICKS",
    "",
    "Lakers -5.5    2u",
    "Chiefs ML      1.5u",
    "Over 225.5     3u",
]

y_position = 30
for line in text_lines:
    draw.text((30, y_position), line, fill='black')
    y_position += 40

# Save the image
output_path = os.path.join(os.getcwd(), 'test_betting_slip.png')
image.save(output_path)
print(f"Test image created at: {output_path}")
