"""Offline preparation for the approved Siamese cutouts (Pillow + NumPy).

This color mask is specific to the warm seal-point fur against the generated
neutral checkerboard. It is not a general-purpose background remover.
Run only during asset preparation; the desktop application does not import it.
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def prepare(source: Path, target: Path) -> None:
    original = Image.open(source).convert("RGBA")
    rgb = np.asarray(original.convert("RGB")).astype(np.int16)
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    # The backdrop is neutral and light. Fur is warm; eyes are blue; points dark.
    foreground = ((red - blue > 16) | (blue - red > 22)
                  | (np.minimum(np.minimum(red, green), blue) < 135))
    mask = Image.fromarray((foreground * 255).astype(np.uint8))
    mask = mask.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    # Fill light highlights enclosed by the silhouette, never the outer backdrop.
    outside = mask.copy()
    ImageDraw.floodfill(outside, (0, 0), 128)
    filled = np.where(np.asarray(outside) == 128, 0, 255).astype(np.uint8)
    mask = Image.fromarray(filled).filter(ImageFilter.MinFilter(3))
    mask = mask.filter(ImageFilter.GaussianBlur(0.6))
    original.putalpha(mask)
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("No cat silhouette detected")
    original = original.crop(bbox)
    original.thumbnail((480, 480), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (512, 512))
    canvas.alpha_composite(original, ((512 - original.width) // 2,
                                      496 - original.height))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, optimize=True)
    print(f"{target.name}: RGBA {canvas.size}, transparent background")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    prepare(args.source, args.target)
