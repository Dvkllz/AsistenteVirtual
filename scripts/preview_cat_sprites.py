"""Render the final sprites on contrasting backgrounds for visual QA."""
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parent.parent
sheet = Image.new("RGB", (1024, 570), "#202536")
draw = ImageDraw.Draw(sheet)
for index, state in enumerate(("idle", "talking", "falling", "walking")):
    sprite = Image.open(root / "assets" / "siamese" / f"{state}.png").convert("RGBA")
    sprite.thumbnail((240, 240), Image.Resampling.LANCZOS)
    for row, color in enumerate(("#202536", "#f3f5fc")):
        x, y = index * 256, row * 285
        draw.rectangle((x, y, x + 255, y + 284), fill=color)
        sheet.paste(sprite, (x + (256 - sprite.width) // 2, y + 10), sprite)
        draw.text((x + 85, y + 255), state, fill="#a0a6b5" if row == 0 else "#202536")
(root / "artifacts").mkdir(exist_ok=True)
sheet.save(root / "artifacts" / "siamese-states.png")
