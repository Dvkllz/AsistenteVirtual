"""Offline contact sheet and GIF preview of the runtime frame order (Pillow)."""

from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parent.parent
assets = root / "assets" / "siamese"
walk = ["walking.png"] + [f"animation/walking_{i}.png" for i in range(1, 4)]
jump = [f"animation/jumping_{i}.png" for i in range(3)] + ["falling.png"]
sheet = Image.new("RGB", (800, 450), "#202536")
draw = ImageDraw.Draw(sheet)
frames = []
for index in range(4):
    gif = Image.new("RGB", (220, 450), "#202536")
    for row, names in enumerate((walk, jump)):
        sprite = Image.open(assets / names[index]).convert("RGBA")
        sprite.thumbnail((190, 190), Image.Resampling.LANCZOS)
        sheet.paste(sprite, (index * 200 + 5, row * 225 + 5), sprite)
        draw.text((index * 200 + 60, row * 225 + 205),
                  ("Paso " if row == 0 else "Salto ") + str(index + 1), fill="white")
        gif.paste(sprite, (15, row * 225 + 5), sprite)
    frames.append(gif)
output = root / "artifacts"
output.mkdir(exist_ok=True)
sheet.save(output / "cat-animation-frames.png")
frames[0].save(output / "cat-animation.gif", save_all=True, append_images=frames[1:],
               duration=120, loop=0)
