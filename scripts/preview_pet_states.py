"""Offline visual check of actual cached sprite sizes; no asset modifications."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication
from desktop_pet.sprites import SpriteSet

app = QApplication([])
sprites = SpriteSet()
canvas = QPixmap(620, 170)
canvas.fill(QColor("#202536"))
painter = QPainter(canvas)
painter.setPen(Qt.GlobalColor.white)
for index, (state, label) in enumerate((("idle", "Quieto"), ("walking", "Caminando"),
                                       ("sleeping", "Dormido / caricias"))):
    pixmap = sprites.pixmap(state)
    painter.drawPixmap(index * 205 + (205 - pixmap.width()) // 2, 5, pixmap)
    painter.drawText(index * 205 + 30, 147, label)
painter.end()
target = Path(__file__).resolve().parent.parent / "artifacts/pet-states.png"
target.parent.mkdir(exist_ok=True)
canvas.save(str(target))
