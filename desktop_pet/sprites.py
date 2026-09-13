"""Cached directional frames and deterministic animation selection."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QPixmap, QTransform

SPRITE_DIR = Path(__file__).resolve().parent.parent / "assets" / "siamese"
SPRITE_STATES = ("idle", "talking", "falling", "walking", "petting")
FRAME_FILES = {
    "idle": ("idle.png",),
    "petting": ("petting.png",),
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
        if state == "sleeping":
            state = "petting"
        return self.frames[state, -1 if direction < 0 else 1, frame % len(FRAME_FILES[state])]
