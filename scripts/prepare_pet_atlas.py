"""Remove disconnected transparent-edge speckles from a generated 4x3 pet atlas."""

import argparse
from collections import deque
from pathlib import Path

from PIL import Image, ImageOps


def clean_cell(cell: Image.Image, minimum_component: int = 300) -> Image.Image:
    """Keep the animal silhouette and substantial limbs, with soft alpha intact."""
    rgba = cell.convert('RGBA')
    width, height = rgba.size
    alpha = rgba.getchannel('A').tobytes()
    mask = bytes(value > 128 for value in alpha)
    visited = bytearray(len(mask))
    components = []
    for start, active in enumerate(mask):
        if not active or visited[start]:
            continue
        queue = deque([start])
        visited[start] = 1
        component = []
        while queue:
            index = queue.popleft()
            component.append(index)
            y, x = divmod(index, width)
            for ny in range(max(0, y - 1), min(height, y + 2)):
                for nx in range(max(0, x - 1), min(width, x + 2)):
                    neighbor = ny * width + nx
                    if mask[neighbor] and not visited[neighbor]:
                        visited[neighbor] = 1
                        queue.append(neighbor)
        if len(component) >= minimum_component:
            ys, xs = zip(*(divmod(index, width) for index in component))
            components.append((component, min(xs), min(ys), max(xs), max(ys)))
    keep = bytearray(len(mask))
    if components:
        main = max(components, key=lambda item: len(item[0]))
        _, left, top, right, bottom = main
        # Keep detached paws only when they sit against the body; discard distant flecks.
        for component, x0, y0, x1, y1 in components:
            if (component is main[0] or
                    (x0 >= left - 12 and x1 <= right + 12
                     and y0 >= top - 12 and y1 <= bottom + 12)):
                for index in component:
                    keep[index] = 1
    rgba.putalpha(Image.frombytes('L', rgba.size,
                                  bytes(value if keep[i] else 0
                                        for i, value in enumerate(alpha))))
    return rgba


def prepare(source: Path, target: Path, seated_source: Path | None = None) -> None:
    atlas = Image.open(source).convert('RGBA')
    if atlas.width % 4 or atlas.height % 3:
        raise ValueError('The pet atlas must have exactly 4 columns and 3 rows.')
    cell_width, cell_height = atlas.width // 4, atlas.height // 3
    seated = None
    if seated_source is not None:
        sheet = Image.open(seated_source).convert('RGBA')
        if sheet.width % 2 or sheet.height % 2:
            raise ValueError('The seated-pose sheet must have exactly 2 columns and 2 rows.')
        source_width, source_height = sheet.width // 2, sheet.height // 2
        seated = [sheet.crop((column * source_width, row * source_height,
                              (column + 1) * source_width, (row + 1) * source_height))
                  for row in range(2) for column in range(2)]
    output = Image.new('RGBA', atlas.size)
    for row in range(3):
        for column in range(4):
            box = (column * cell_width, row * cell_height,
                   (column + 1) * cell_width, (row + 1) * cell_height)
            index = row * 4 + column
            if row == 0 and seated is not None:
                pose = ImageOps.contain(seated[index], (cell_width - 24, cell_height - 24))
                cell = Image.new('RGBA', (cell_width, cell_height))
                cell.alpha_composite(pose, ((cell_width-pose.width)//2,
                                            (cell_height-pose.height)//2))
            else:
                cell = atlas.crop(box)
            output.alpha_composite(clean_cell(cell), box[:2])
    target.parent.mkdir(parents=True, exist_ok=True)
    output.save(target, optimize=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pet', nargs='?', default='hamster',
                        help='pet asset folder name (defaults to hamster)')
    parser.add_argument('--source-name', default='atlas-generated.png',
                        help='source PNG filename inside the pet folder')
    parser.add_argument('--seated-name',
                        help='optional 2x2 sprite sheet replacing idle, talk, pet and sleep')
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent.parent / 'assets' / args.pet
    source, target = folder / args.source_name, folder / 'atlas.png'
    if not source.is_file():
        parser.error(f'No generated atlas found at {source}')
    seated = folder / args.seated_name if args.seated_name else None
    prepare(source, target, seated)
