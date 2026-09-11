"""Local habits with optional, interruptible cursor play; never clicks or locks."""

import math
import random
import sys
import time

from PyQt6.QtCore import QPoint, QTimer, Qt, QVariantAnimation
from PyQt6.QtGui import QColor, QCursor, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget


QUIPS = (
    "Trabajo remoto: tú trabajas, yo miro.",
    "Ese ratón lleva diez segundos haciéndose el muerto.",
    "He optimizado tu escritorio: ahora tiene gato.",
    "Mi siguiente reunión es con una siesta.",
    "No es un error. Es una función felina.",
    "Tu productividad necesita más atún.",
    "Hoy tampoco voy a pagar alquiler.",
    "Estoy supervisando. Se parece mucho a no hacer nada.",
)


def mouse_button_down():
    if QApplication.mouseButtons() != Qt.MouseButton.NoButton:
        return True
    if sys.platform == "win32":
        # Qt may not have seen a button pressed in another application.
        import ctypes
        return any(ctypes.windll.user32.GetAsyncKeyState(key) & 0x8000
                   for key in (0x01, 0x02, 0x04, 0x05, 0x06))
    return False


def escape_pressed():
    if sys.platform == "win32":
        import ctypes
        return bool(ctypes.windll.user32.GetAsyncKeyState(0x1B) & 0x8000)
    return False


class IdleMouse:
    """Fire once per stationary period; activity must rearm the interaction."""

    def __init__(self, now: float, position: QPoint):
        self.position = QPoint(position)
        self.since = now
        self.fired = False

    def poll(self, now: float, position: QPoint, blocked: bool = False) -> bool:
        if position != self.position or blocked:
            self.position = QPoint(position)
            self.since = now
            self.fired = False
            return False
        if not self.fired and now - self.since >= 10:
            self.fired = True
            return True
        return False


class SwatEffect(QWidget):
    """Brief visual strike near the cursor; all mouse input passes through."""

    def __init__(self, parent):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.WindowTransparentForInput
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedSize(56, 56)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#ffcc78"), 2.5))
        for offset in (0, 9, 18):
            painter.drawLine(13 + offset, 12, 7 + offset, 37)


class CatAutonomy:
    """Owned by PetWindow; Qt children stop automatically with their parent."""

    def __init__(self, window):
        self.window = window
        self.enabled = window.settings.value("autonomy/enabled", True, type=bool)
        self.cursor_push_enabled = window.settings.value("autonomy/cursor_push", True, type=bool)
        self.cursor_carry_enabled = window.settings.value("autonomy/cursor_carry", True, type=bool)
        self.rng = random.Random()
        now = time.monotonic()
        self.mouse = IdleMouse(now, QCursor.pos())
        self.next_walk = now + self.rng.uniform(20, 45)
        self.next_quip = now + self.rng.uniform(45, 90)
        self.last_quip = None
        self.auto_walking = False
        self.pouncing = False
        self.pounce_progress = 0.0
        self.swatting = False
        self.carrying = False
        self.carry_expected = QPoint()
        self.carry_started = 0.0
        self.target = QPoint()
        self.effect = SwatEffect(window)
        self.timer = QTimer(window)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.tick)
        self.walk_timer = QTimer(window)
        self.walk_timer.setSingleShot(True)
        self.walk_timer.timeout.connect(self.end_walk)
        self.swat_timer = QTimer(window)
        self.swat_timer.setSingleShot(True)
        self.swat_timer.timeout.connect(self.finish_pounce)
        self.animation = QVariantAnimation(window)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setDuration(850)
        self.animation.valueChanged.connect(self.move_pounce)
        self.animation.finished.connect(self.swat)
        self.carry_animation = QVariantAnimation(window)
        self.carry_animation.setStartValue(0.0)
        self.carry_animation.setEndValue(1.0)
        self.carry_animation.setDuration(3000)
        self.carry_animation.valueChanged.connect(self.move_carry)
        self.carry_animation.finished.connect(self.finish_carry)
        if self.enabled:
            self.timer.start()

    def busy(self):
        w = self.window
        return (w._closing or not w.isVisible() or w._drag_offset is not None or w.petting
                or w.menu.isVisible() or w.input.hasFocus() or bool(w.input.text())
                or w.bubble.hasSelectedText() or w.worker is not None
                or mouse_button_down())

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.window.settings.setValue("autonomy/enabled", enabled)
        self.window.settings.sync()
        self.cancel()
        self.timer.stop()
        now = time.monotonic()
        self.mouse = IdleMouse(now, QCursor.pos())
        self.next_walk = now + self.rng.uniform(20, 45)
        self.next_quip = now + self.rng.uniform(45, 90)
        if enabled and not self.window._closing:
            self.timer.start()

    def tick(self):
        w = self.window
        now, cursor = time.monotonic(), QCursor.pos()
        if self.carrying:
            if self.carry_interrupted(cursor):
                self.finish_carry()
            return
        blocked = self.busy() or not self.enabled
        moved = cursor != self.mouse.position
        trigger = self.mouse.poll(now, cursor, blocked)
        if blocked:
            self.cancel()
            return
        if moved and (self.pouncing or self.swatting):
            self.finish_pounce()
        if self.pouncing or self.swatting:
            return
        if trigger and w.physics_enabled:
            self.pounce(cursor)
            if self.pouncing:
                return
        if now >= self.next_walk:
            self.next_walk = now + self.rng.uniform(20, 45)
            if w.physics_enabled and not w.walking and not w.talking_timer.isActive():
                w.facing = self.rng.choice((-1, 1))
                w.set_walking(True, automatic=True)
                self.auto_walking = w.walking
                if self.auto_walking:
                    self.walk_timer.start(self.rng.randint(5000, 10000))
        if now >= self.next_quip and now - w._last_response_at >= 20:
            self.next_quip = now + self.rng.uniform(45, 90)
            choices = [quip for quip in QUIPS if quip != self.last_quip]
            self.last_quip = self.rng.choice(choices)
            w._on_answer(self.last_quip)

    def end_walk(self):
        self.walk_timer.stop()
        if self.auto_walking:
            self.auto_walking = False
            self.window.set_walking(False, automatic=True)

    def forget_walk(self):
        self.auto_walking = False
        self.walk_timer.stop()

    def pounce(self, cursor):
        w = self.window
        # Do not teleport across monitors, outside the work area, or onto the UI.
        if (self.busy() or not self.enabled or not w.physics_enabled
                or QApplication.screenAt(cursor) != w.screen()
                or w.geometry().contains(cursor)):
            return
        self.end_walk()
        w._cancel_walk()
        w._stop_motion()
        self.target = QPoint(cursor)
        w.facing = 1 if cursor.x() >= w.character.mapToGlobal(w.character.rect().center()).x() else -1
        paw = w.character.pos() + QPoint(w.character.width() // 2 + w.facing * 35,
                                        w.character.height() - 18)
        if self.cursor_carry_enabled:
            paw = self.mouth_offset()
        self.start = w.pos()
        self.destination = cursor - paw
        self.bounds = w._bounds()
        self.destination = self.clamp(self.destination)
        self.pouncing = True
        self.pounce_progress = 0.0
        w._refresh_sprite()
        self.animation.start()

    def clamp(self, point):
        left, top, right, bottom = self.bounds
        return QPoint(max(left, min(right, point.x())), max(top, min(bottom, point.y())))

    def move_pounce(self, progress):
        if not self.pouncing:
            return
        # Smooth travel plus a small arc; never grabs focus or moves the pointer.
        t = float(progress)
        self.pounce_progress = t
        ease = 1 - (1 - t) ** 3
        delta = self.destination - self.start
        point = self.start + QPoint(round(delta.x() * ease),
                                    round(delta.y() * ease - math.sin(math.pi * t) * 50))
        self.window.move(self.clamp(point))
        self.window._refresh_sprite()

    def swat(self):
        if not self.pouncing:
            return
        # Recheck at the instant of contact, not just the slower idle poll.
        if (self.busy() or not self.enabled or not self.window.physics_enabled
                or QCursor.pos() != self.target or escape_pressed()):
            self.finish_pounce()
            return
        self.pouncing = False
        if self.cursor_carry_enabled:
            self.start_carry()
            return
        self.swatting = True
        self.effect.move(self.target - QPoint(28, 28))
        self.effect.show()
        self.window._refresh_sprite()
        if self.cursor_push_enabled:
            area = self.window.screen().availableGeometry()
            pushed = self.target + QPoint(self.window.facing * 24, -8)
            pushed.setX(max(area.left(), min(area.right(), pushed.x())))
            pushed.setY(max(area.top(), min(area.bottom(), pushed.y())))
            QCursor.setPos(pushed)
            # Our own single nudge must not rearm another attack in ten seconds.
            self.mouse.position = QPoint(pushed)
            self.mouse.fired = True
        self.swat_timer.start(350)

    def mouth_offset(self):
        w = self.window
        return w.character.pos() + QPoint(w.character.width() // 2 + w.facing * 43,
                                          w.character.height() // 2 + 5)

    def carry_interrupted(self, cursor=None):
        if cursor is None:
            cursor = QCursor.pos()
        return (cursor != self.carry_expected or self.busy() or escape_pressed()
                or not self.enabled or not self.cursor_carry_enabled
                or not self.window.physics_enabled
                or time.monotonic() - self.carry_started >= 3.0)

    def start_carry(self):
        w = self.window
        # Called only after contact has rechecked the stationary cursor/buttons.
        if (self.busy() or not self.enabled or not self.cursor_carry_enabled
                or not w.physics_enabled or escape_pressed() or QCursor.pos() != self.target):
            w._start_motion()
            return
        self.bounds = w._bounds()
        self.carry_start = w.pos()
        left, _, right, _ = self.bounds
        direction = 1 if right - w.x() >= w.x() - left else -1
        w.facing = direction
        self.carry_destination = self.clamp(w.pos() + QPoint(direction * 120, 0))
        self.carry_expected = QPoint(self.target)
        self.carry_started = time.monotonic()
        self.carrying = True
        self.effect.hide()
        w.character.setCursor(Qt.CursorShape.ArrowCursor)
        w._refresh_sprite()
        self.carry_animation.start()

    def move_carry(self, progress):
        if not self.carrying:
            return
        # Check before EVERY pointer write. Do not fight a user's mouse movement.
        if self.carry_interrupted():
            self.finish_carry()
            return
        t = float(progress)
        delta = self.carry_destination - self.carry_start
        point = self.carry_start + QPoint(round(delta.x() * t),
                                          round(-math.sin(math.pi * t) * 6))
        w = self.window
        w.move(self.clamp(point))
        w._refresh_sprite()
        destination = w.pos() + self.mouth_offset()
        area = w.screen().availableGeometry()
        destination.setX(max(area.left(), min(area.right(), destination.x())))
        destination.setY(max(area.top(), min(area.bottom(), destination.y())))
        if destination != self.carry_expected:
            QCursor.setPos(destination)
            self.carry_expected = QPoint(destination)
        self.mouse.position = QPoint(self.carry_expected)
        self.mouse.fired = True

    def finish_carry(self, resume=True):
        if not self.carrying:
            return
        self.carrying = False
        self.carry_animation.stop()
        self.window.character.setCursor(Qt.CursorShape.OpenHandCursor)
        # Release where it is. Never snap the pointer back after user activity.
        cursor = QCursor.pos()
        if cursor != self.carry_expected:
            self.mouse = IdleMouse(time.monotonic(), cursor)
        else:
            self.mouse.position = QPoint(cursor)
            self.mouse.fired = True
        self.window._stop_motion()
        if resume:
            self.window._start_motion()

    def finish_pounce(self, resume=True):
        self.finish_carry(resume=resume)
        active = self.pouncing or self.swatting
        self.animation.stop()
        self.swat_timer.stop()
        self.effect.hide()
        self.pouncing = self.swatting = False
        if active:
            self.window._stop_motion()
            if resume:
                self.window._start_motion()

    def cancel(self):
        self.end_walk()
        self.finish_pounce()

    def close(self):
        self.timer.stop()
        self.cancel()
