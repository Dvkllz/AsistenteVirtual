"""Offline pixel typography and native Qt icons for the compact chat controls."""
from functools import lru_cache
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QFontDatabase, QIcon, QPainter, QPixmap, QPolygon
from PyQt6.QtWidgets import QWidget

FONT_PATH = Path(__file__).resolve().parent.parent / "assets/fonts/PixelifySans.ttf"


class DialogueFrame(QWidget):
    """Pixel-cut double frame; its tail and borders stay put while text scrolls."""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        width, bottom = self.width(), self.height() - 10
        center = width // 2

        def panel(inset, color):
            left, top = inset, inset
            right, base = width - inset, bottom - inset
            painter.setBrush(QColor(color))
            painter.drawPolygon(QPolygon([
                QPoint(left + 5, top), QPoint(right - 5, top),
                QPoint(right - 5, top + 3), QPoint(right, top + 3),
                QPoint(right, base - 3), QPoint(right - 5, base - 3),
                QPoint(right - 5, base), QPoint(left + 5, base),
                QPoint(left + 5, base - 3), QPoint(left, base - 3),
                QPoint(left, top + 3), QPoint(left + 5, top + 3),
            ]))

        # Offset layers give a dark outline, a bright rim and an inset lip.
        panel(0, "#101910")
        panel(2, "#b6c98d")
        panel(4, "#526644")
        panel(6, "#18211c")
        painter.fillRect(11, 7, width - 22, 1, QColor("#768b5f"))
        painter.fillRect(11, bottom - 7, width - 22, 1, QColor("#0d150f"))
        painter.fillRect(center - 9, bottom - 4, 18, 8, QColor("#101910"))
        painter.fillRect(center - 5, bottom + 4, 10, 4, QColor("#101910"))
        painter.fillRect(center - 7, bottom - 4, 14, 6, QColor("#b6c98d"))
        painter.fillRect(center - 3, bottom + 2, 6, 4, QColor("#b6c98d"))
        painter.fillRect(center - 5, bottom - 5, 10, 5, QColor("#18211c"))
        painter.fillRect(center - 2, bottom, 4, 3, QColor("#526644"))
        painter.end()


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
