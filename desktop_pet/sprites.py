"""Four cached, direction-aware Siamese cat sprites, with deterministic priority."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QTransform

SPRITE_DIR = Path(__file__).resolve().parent.parent / "assets" / "siamese"
SPRITE_STATES = ("idle", "talking", "falling", "walking")


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
        self.frames: dict[tuple[str, int], QPixmap] = {}
        fallback = QPixmap(str(directory / "idle.png"))
        if fallback.isNull():
            fallback = QPixmap(str(SPRITE_DIR.parent / "placeholder.png"))
        for state in SPRITE_STATES:
            source = QPixmap(str(directory / f"{state}.png"))
            if source.isNull():
                self.missing.append(state)
                source = fallback
            # Scale once at load, not on each physics tick. Keep generated alpha.
            right = source.scaled(146, 140, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            self.frames[state, 1] = right
            self.frames[state, -1] = right.transformed(QTransform().scale(-1, 1))

    def pixmap(self, state: str, direction: int = 1) -> QPixmap:
        return self.frames[state, -1 if direction < 0 else 1]
