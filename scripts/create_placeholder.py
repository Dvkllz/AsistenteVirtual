"""Generate the simple local PNG asset with alpha; no image API involved."""

from pathlib import Path

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen


def main() -> None:
    image = QImage(360, 360, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(20, 30, 45, 45))
    painter.drawEllipse(QRectF(66, 318, 232, 22))
    painter.setPen(QPen(QColor("#26364a"), 7))
    painter.setBrush(QColor("#8fdac5"))
    body = QPainterPath(QPointF(78, 159))
    body.cubicTo(68, 110, 75, 69, 94, 42)
    body.lineTo(141, 83)
    body.cubicTo(165, 76, 197, 76, 220, 83)
    body.lineTo(266, 42)
    body.cubicTo(286, 76, 292, 118, 282, 159)
    body.cubicTo(306, 218, 286, 309, 253, 320)
    body.lineTo(218, 297)
    body.lineTo(180, 320)
    body.lineTo(142, 297)
    body.lineTo(107, 320)
    body.cubicTo(72, 310, 54, 218, 78, 159)
    painter.drawPath(body)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#c6f3e2"))
    painter.drawEllipse(QRectF(103, 117, 155, 165))
    painter.setBrush(QColor("#26364a"))
    painter.drawRoundedRect(QRectF(117, 151, 26, 37), 12, 12)
    painter.drawRoundedRect(QRectF(217, 151, 26, 37), 12, 12)
    painter.setPen(QPen(QColor("#26364a"), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(113, 137), QPointF(146, 145))
    painter.drawLine(QPointF(213, 145), QPointF(246, 137))
    painter.drawArc(QRectF(160, 186, 40, 28), 185 * 16, 150 * 16)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#e9aab5"))
    painter.drawEllipse(QRectF(96, 193, 26, 13))
    painter.drawEllipse(QRectF(239, 193, 26, 13))
    painter.end()
    target = Path(__file__).resolve().parent.parent / "assets" / "placeholder.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(target)):
        raise RuntimeError("Could not save placeholder PNG")
    print(f"Created {target}")


if __name__ == "__main__":
    main()
