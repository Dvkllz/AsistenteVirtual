"""Cached directional frames and deterministic animation selection."""

from pathlib import Path

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QImage, QPainter, QPixmap, QTransform

SPRITE_DIR = Path(__file__).resolve().parent.parent / "assets" / "siamese"
SPRITE_STATES = ("idle", "talking", "falling", "walking", "petting", "sleeping")
FRAME_FILES = {
    "idle": ("idle.png",),
    "petting": ("petting.png",),
    "sleeping": ("sleeping.png",),
    "talking": ("talking.png",),
    "walking": ("walking.png", "animation/walking_1.png", "animation/walking_2.png",
                "animation/walking_3.png"),
    "falling": ("falling.png", "animation/jumping_0.png", "animation/jumping_1.png",
                "animation/jumping_2.png"),
}


def select_frame(state, elapsed=0.0, *, vy=0.0, launch_age=None, pounce=None):
    if state == "walking":
        return int(max(0.0, elapsed) / 0.12) % 4
    if state == "falling":
        if pounce is not None:
            return 1 if pounce < .12 else 2 if pounce < .45 else 3 if pounce < .72 else 0
        if launch_age is not None and launch_age < .08:
            return 1
        if vy < -200:
            return 2
        if launch_age is not None and vy < 160:
            return 3
    return 0


def select_state(*, dragging: bool, airborne: bool, speaking: bool, walking: bool) -> str:
    if dragging or airborne:
        return "falling"
    if speaking:
        return "talking"
    if walking:
        return "walking"
    return "idle"


class SpriteSet:
    def __init__(self, directory: Path = SPRITE_DIR):
        self.missing: list[str] = []
        self.frames: dict[tuple[str, int, int], QPixmap] = {}
        self.missing_animation: list[str] = []
        fallback = QPixmap(str(directory / "idle.png"))
        if fallback.isNull():
            fallback = QPixmap(str(SPRITE_DIR.parent / "placeholder.png"))
        for state in SPRITE_STATES:
            source = QPixmap(str(directory / f"{state}.png"))
            if source.isNull():
                self.missing.append(state)
                source = fallback
            for index, filename in enumerate(FRAME_FILES[state]):
                frame = source if index == 0 else QPixmap(str(directory / filename))
                if frame.isNull():
                    self.missing_animation.append(filename)
                    frame = source
                # Scale once at load, not on each physics tick. Keep alpha.
                right = frame.scaled(117, 112, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                if state == "walking" and state not in self.missing:
                    # A horizontal cat was shrunk by fitting its long tail into a square.
                    # Enlarge every walk frame uniformly; discard only transparent top padding.
                    right = QPixmap(152, 112)
                    right.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(right)
                    painter.drawPixmap(0, -38, frame.scaled(
                        152, 152, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation))
                    painter.end()
                self.frames[state, 1, index] = right
                self.frames[state, -1, index] = right.transformed(QTransform().scale(-1, 1))

    def pixmap(self, state: str, direction: int = 1, frame: int = 0) -> QPixmap:
        return self.frames[state, -1 if direction < 0 else 1, frame % len(FRAME_FILES[state])]


class AtlasSpriteSet(SpriteSet):
    """Load twelve atlas poses once; all frames share a 152x112 logical canvas."""
    CELLS = {'idle': (0,), 'talking': (1,), 'petting': (2,), 'sleeping': (3,),
             'walking': (4, 5, 6, 7), 'falling': (8, 9, 10, 11)}

    def __init__(self, directory: Path):
        atlas = QPixmap(str(directory / 'atlas.png'))
        self.frames = {}
        self.missing = []
        self.missing_animation = []
        if atlas.isNull() or atlas.width() % 4 or atlas.height() % 3:
            raise ValueError('El atlas de la mascota no está disponible o no es válido.')
        cell_w, cell_h = atlas.width() // 4, atlas.height() // 3
        cells, bounds = {}, {}
        for index in range(12):
            cells[index] = atlas.copy(index % 4 * cell_w, index // 4 * cell_h, cell_w, cell_h)
            # Alpha bounds are computed only at load, never on animation ticks.
            im = cells[index].toImage().convertToFormat(QImage.Format.Format_RGBA8888)
            # Read packed alpha bytes: avoid millions of Python -> Qt QColor calls.
            alpha = im.constBits().asstring(im.sizeInBytes())[3::4]
            points = [(offset % cell_w, offset // cell_w)
                      for offset, value in enumerate(alpha) if value > 128]
            if not points:
                raise ValueError('Falta una pose en el atlas de la mascota.')
            xs, ys = zip(*points)
            bounds[index] = QRect(min(xs), min(ys), max(xs)-min(xs)+1, max(ys)-min(ys)+1)
        # A single scale per animation prevents walking/sitting from pulsing.
        groups = ((0, 1, 2), (3,), (4, 5, 6, 7), (8, 9, 10, 11))
        targets = ((112, 100), (118, 57), (140, 82), (140, 100))
        scales = {}
        for indices, (width, height) in zip(groups, targets):
            scale = min(width / max(bounds[i].width() for i in indices),
                        height / max(bounds[i].height() for i in indices))
            scales.update({i: scale for i in indices})
        for state, indices in self.CELLS.items():
            for frame, index in enumerate(indices):
                crop = cells[index].copy(bounds[index])
                scaled = crop.scaled(round(crop.width()*scales[index]), round(crop.height()*scales[index]),
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                right = QPixmap(152, 112)
                right.fill(Qt.GlobalColor.transparent)
                painter = QPainter(right)
                painter.drawPixmap((152-scaled.width())//2, 110-scaled.height(), scaled)
                painter.end()
                self.frames[state, 1, frame] = right
                self.frames[state, -1, frame] = right.transformed(QTransform().scale(-1, 1))


def load_pet_sprites(pet_id='siamese'):
    from desktop_pet.pets import get_pet
    profile = get_pet(pet_id)
    return AtlasSpriteSet(profile.directory) if profile.id == 'golden' else SpriteSet(profile.directory)
