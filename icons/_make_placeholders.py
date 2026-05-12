"""Generate placeholder PNG icons for the Unraid-Templates repo.

Run once to produce icons/<name>.png files. Replace with real icons later.
"""
from PIL import Image, ImageDraw, ImageFont
import os

ICONS = [
    ("wirespeed-computing", "WS", (24, 45, 88)),
    ("mcp-memory", "MEM", (60, 35, 95)),
    ("filesystem-mcp", "FS", (35, 95, 60)),
    ("tailscale-sidecar", "TS", (95, 60, 35)),
]

SIZE = 256
HERE = os.path.dirname(os.path.abspath(__file__))

try:
    font = ImageFont.truetype("arial.ttf", 96)
except OSError:
    font = ImageFont.load_default()

for name, label, color in ICONS:
    img = Image.new("RGB", (SIZE, SIZE), color)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), label, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (SIZE - w) // 2 - bbox[0]
    y = (SIZE - h) // 2 - bbox[1]
    draw.text((x, y), label, fill=(255, 255, 255), font=font)
    out = os.path.join(HERE, name + ".png")
    img.save(out, "PNG")
    print("wrote", out)
