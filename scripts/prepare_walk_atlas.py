"""Slice a 2x2 generated atlas with ONE shared crop and scale (offline only)."""

import argparse
from pathlib import Path
from PIL import Image
from prepare_cat_sprite import remove_background


def prepare(source, target):
    atlas = Image.open(source).convert('RGBA')
    width, height = atlas.width // 2, atlas.height // 2
    frames = [remove_background(atlas.crop((col * width, row * height,
               (col + 1) * width, (row + 1) * height)))
              for row in range(2) for col in range(2)]
    boxes = [frame.getbbox() for frame in frames]
    box = (min(b[0] for b in boxes), min(b[1] for b in boxes),
           max(b[2] for b in boxes), max(b[3] for b in boxes))
    factor = 480 / max(box[2] - box[0], box[3] - box[1])
    size = (round((box[2] - box[0]) * factor), round((box[3] - box[1]) * factor))
    names = ['walking.png'] + [f'animation/walking_{i}.png' for i in range(1, 4)]
    for frame, name in zip(frames, names):
        canvas = Image.new('RGBA', (512, 512))
        canvas.alpha_composite(frame.crop(box).resize(size, Image.Resampling.LANCZOS),
                               ((512 - size[0]) // 2, 496 - size[1]))
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(path, optimize=True)
        print(f'{name}: common crop {box}, scale {factor:.3f}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('target', type=Path)
    args = parser.parse_args()
    prepare(args.source, args.target)
