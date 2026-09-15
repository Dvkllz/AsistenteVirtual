"""Offline pixel typography and native Qt icons for the compact chat controls."""
from functools import lru_cache
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFontDatabase, QIcon, QPainter, QPixmap

FONT_PATH = Path(__file__).resolve().parent.parent / "assets/fonts/PixelifySans.ttf"


@lru_cache(maxsize=1)
def pixel_font_family():
    font_id = QFontDatabase.addApplicationFont(str(FONT_PATH))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    return families[0] if families else "Consolas"


PATTERNS = {
    "microphone": ("000111000", "001111100", "001111100", "001111100",
                   "001111100", "100111001", "100000001", "010000010",
                   "001111100", "000010000", "001111100"),
    "stop": ("000000000", "011111110", "011111110", "011111110",
             "011111110", "011111110", "011111110", "011111110", "000000000"),
    "send": ("000010000", "000011000", "000011100", "111111110",
             "111111111", "111111110", "000011100", "000011000", "000010000"),
}


@lru_cache(maxsize=3)
def pixel_icon(name):
    icon = QIcon()
    for mode, color in ((QIcon.Mode.Normal, "#eaf5dc"), (QIcon.Mode.Disabled, "#71816b")):
        for state in (QIcon.State.Off, QIcon.State.On):
            rows = PATTERNS["stop" if name == "microphone" and state == QIcon.State.On else name]
            pixmap = QPixmap(24, 24)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            left, top = (24 - len(rows[0]) * 2) // 2, (24 - len(rows) * 2) // 2
            for y, row in enumerate(rows):
                for x, value in enumerate(row):
                    if value == "1":
                        painter.fillRect(left + x * 2, top + y * 2, 2, 2, QColor(color))
            painter.end()
            icon.addPixmap(pixmap, mode, state)
    return icon
