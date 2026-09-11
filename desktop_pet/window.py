"""Transparent, draggable desktop pet. Network work stays off the GUI thread."""

from collections.abc import Callable
import time

from PyQt6.QtCore import QEvent, QPoint, QRect, QSettings, Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QActionGroup, QCloseEvent
from PyQt6.QtWidgets import (
    QApplication, QLabel, QLineEdit, QMenu, QScrollArea, QVBoxLayout, QWidget,
)

from desktop_pet.service import MAX_QUESTION_CHARS, PetServiceError, answer_question, has_openai_key
from desktop_pet.physics import Body, DragVelocity
from desktop_pet.sprites import SPRITE_DIR, SpriteSet, select_state, select_frame
from desktop_pet.autonomy import CatAutonomy
from desktop_pet.purring import PurrSound
from desktop_pet.petting import HeadStrokes

ASSET_PATH = SPRITE_DIR / "idle.png"


class AnswerThread(QThread):
    answered = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, question: str, responder: Callable[[str], str], parent: QWidget):
        super().__init__(parent)
        self.question = question
        self.responder = responder

    def run(self) -> None:
        try:
            self.answered.emit(self.responder(self.question))
        except PetServiceError as error:
            self.failed.emit(str(error))
        except Exception:
            # Never expose raw SDK exceptions, request bodies, or secrets in the UI.
            self.failed.emit("Algo salió mal al responder. Inténtalo de nuevo.")


class PetWindow(QWidget):
    def __init__(self, *, live: bool = False, responder: Callable[[str], str] | None = None,
                 settings: QSettings | None = None):
        super().__init__()
        self.live = live
        self._custom_responder = responder
        self.settings = settings or QSettings()
        self.worker: AnswerThread | None = None
        self._closing = False
        self.autonomy = None
        self._last_response_at = time.monotonic()
        self._drag_offset: QPoint | None = None
        self.petting = False
        self.head_strokes = HeadStrokes()
        self.purr = PurrSound(self, self.settings.value("sound/purr", True, type=bool))
        self.pet_timer = QTimer(self)
        self.pet_timer.setSingleShot(True)
        self.pet_timer.setInterval(650)
        self.pet_timer.timeout.connect(self._stop_petting)
        self.walking = False
        self.facing = 1
        self.sprite_state = "idle"
        self.sprite_frame = 0
        self._sprite_state_started = time.monotonic()
        self._jump_started = None
        self._sprite_key = None
        self.sprites = SpriteSet()
        self.talking_timer = QTimer(self)
        self.talking_timer.setSingleShot(True)
        self.talking_timer.timeout.connect(self._refresh_sprite)
        self.body = Body()
        self.drag_velocity = DragVelocity()
        self.physics_enabled = self.settings.value("physics/enabled", True, type=bool)
        self.motion_timer = QTimer(self)
        self.motion_timer.setInterval(16)
        self.motion_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.motion_timer.timeout.connect(self._tick_motion)
        self._last_tick = time.monotonic()
        self._physics_screen = QApplication.primaryScreen()

        self.setWindowTitle("Mascota virtual")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(268, 332)
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI'; font-size: 13px; }
            QLabel#bubble {
                background: #202536; color: #f3f5fc; border: 1px solid #404961;
                border-radius: 14px; padding: 11px;
            }
            QLineEdit {
                background: #202536; color: #f3f5fc; border: 1px solid #46516b;
                border-radius: 13px; padding: 10px 12px; selection-background-color: #526d93;
            }
            QLineEdit:focus { border: 1px solid #8fdac5; }
            QLineEdit:disabled { color: #a5afc5; }
            QLabel#mode {
                color: #d9e3f2; background: #202536; border-radius: 8px;
                padding: 3px 9px; font-size: 11px;
            }
            QMenu { background: #202536; color: #f3f5fc; border: 1px solid #46516b; padding: 5px; }
            QMenu::item { padding: 7px 20px; }
            QMenu::item:selected { background: #394660; }
            QScrollBar:vertical { background: transparent; width: 6px; }
            QScrollBar::handle:vertical { background: #687891; border-radius: 3px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.bubble = QLabel()
        self.bubble.setObjectName("bubble")
        self.bubble.setWordWrap(True)
        self.bubble.setTextFormat(Qt.TextFormat.PlainText)
        self.bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.bubble.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.bubble.setAccessibleName("Respuesta de la mascota")
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")
        self.scroll.viewport().setAutoFillBackground(False)
        self.scroll.setFixedHeight(118)
        self.scroll.setWidget(self.bubble)
        layout.addWidget(self.scroll)

        self.character = QLabel()
        self.character.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.character.setFixedHeight(112)
        self.character.setMouseTracking(True)
        self.character.setAccessibleName("Mascota; arrastra para lanzar; pasa el ratón sobre la cabeza para acariciar")
        self.character.setToolTip("Arrastra y suelta: lanzar · Ratón de lado a lado sobre la cabeza, sin clic: caricias")
        self.character.setCursor(Qt.CursorShape.OpenHandCursor)
        self.character.setPixmap(self.sprites.pixmap("idle"))
        self.character.installEventFilter(self)
        layout.addWidget(self.character)

        self.input = QLineEdit()
        self.input.setMaxLength(MAX_QUESTION_CHARS)
        self.input.setPlaceholderText("Pregúntame algo…  ↵")
        self.input.setAccessibleName("Pregunta; Enter para enviar")
        self.input.returnPressed.connect(self.submit)
        self.input.installEventFilter(self)
        layout.addWidget(self.input)
        self.mode = QLabel()
        self.mode.setObjectName("mode")
        layout.addWidget(self.mode, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.menu = QMenu(self)
        self.menu.aboutToShow.connect(self._pause_motion)
        self.menu.aboutToHide.connect(lambda: QTimer.singleShot(0, self._start_motion))
        self.mode_group = QActionGroup(self)
        self.mode_group.setExclusive(True)
        self.demo_action = QAction("Modo de prueba · sin consumo", self, checkable=True)
        self.live_action = QAction("Usar OpenAI · consume tokens", self, checkable=True)
        self.mode_group.addAction(self.demo_action)
        self.mode_group.addAction(self.live_action)
        self.demo_action.triggered.connect(lambda checked: checked and self.set_mode(False))
        self.live_action.triggered.connect(lambda checked: checked and self.set_mode(True))
        self.menu.addActions((self.demo_action, self.live_action))
        self.menu.addSeparator()
        self.physics_action = QAction("Física activada", self, checkable=True)
        self.physics_action.setChecked(self.physics_enabled)
        self.physics_action.toggled.connect(self.set_physics_enabled)
        self.menu.addAction(self.physics_action)
        self.jump_action = QAction("Dar un salto", self)
        self.jump_action.setEnabled(self.physics_enabled)
        self.jump_action.triggered.connect(self.jump)
        self.menu.addAction(self.jump_action)
        self.walk_action = QAction("Pasear", self, checkable=True)
        self.walk_action.setEnabled(self.physics_enabled)
        self.walk_action.toggled.connect(self.set_walking)
        self.menu.addAction(self.walk_action)
        self.autonomy_action = QAction("Travesuras automáticas", self, checkable=True)
        self.autonomy_action.setChecked(self.settings.value("autonomy/enabled", True, type=bool))
        self.autonomy_action.toggled.connect(self.set_autonomy_enabled)
        self.menu.addAction(self.autonomy_action)
        self.cursor_push_action = QAction("Empujar cursor al dar zarpazo", self, checkable=True)
        self.cursor_push_action.setChecked(self.settings.value("autonomy/cursor_push", True, type=bool))
        self.cursor_push_action.toggled.connect(self.set_cursor_push_enabled)
        self.menu.addAction(self.cursor_push_action)
        self.cursor_carry_action = QAction("Llevarse el cursor (3 segundos)", self, checkable=True)
        self.cursor_carry_action.setChecked(self.settings.value("autonomy/cursor_carry", True, type=bool))
        self.cursor_carry_action.toggled.connect(self.set_cursor_carry_enabled)
        self.menu.addAction(self.cursor_carry_action)
        self.purr_action = QAction("Ronroneo al acariciar", self, checkable=True)
        self.purr_action.setChecked(self.purr.enabled)
        self.purr_action.toggled.connect(self.set_purr_enabled)
        self.menu.addAction(self.purr_action)
        self.reset_position_action = QAction("Volver a la esquina", self)
        self.reset_position_action.triggered.connect(self.reset_position)
        self.menu.addAction(self.reset_position_action)
        self.menu.addSeparator()
        self.close_action = QAction("Cerrar mascota", self)
        self.close_action.triggered.connect(self.close)
        self.menu.addAction(self.close_action)
        for surface in (self, self.character, self.bubble, self.mode):
            surface.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            surface.customContextMenuRequested.connect(
                lambda point, target=surface: self.menu.popup(target.mapToGlobal(point))
            )

        self.set_mode(live, announce=True)
        if not self.restore_position():
            self.place_bottom_right()
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setFocus()
        for screen in QApplication.screens():
            screen.availableGeometryChanged.connect(self._screen_changed)
        QApplication.instance().screenRemoved.connect(self._screen_changed)
        QApplication.instance().screenAdded.connect(self._screen_added)
        self.autonomy = CatAutonomy(self)
        QTimer.singleShot(0, self._start_motion)

    def _refresh_sprite(self) -> None:
        if not hasattr(self, "character"):
            return
        moving = self.motion_timer.isActive()
        airborne = moving and (self.y() < self._bounds()[3] - 1 or abs(self.body.vy) > 100)
        state = select_state(dragging=self._drag_offset is not None, airborne=airborne,
                             speaking=self.talking_timer.isActive(), walking=self.walking and moving)
        if self.autonomy and self.autonomy.pouncing:
            state = "falling"
        elif self.autonomy and (self.autonomy.swatting or self.autonomy.carrying):
            state = "walking"
        if self.petting:
            state = "petting"
        now = time.monotonic()
        if state != self.sprite_state:
            self._sprite_state_started = now
        self.sprite_state = state
        progress = self.autonomy.pounce_progress if self.autonomy and self.autonomy.pouncing else None
        frame = select_frame(state, now - self._sprite_state_started, vy=self.body.vy,
                             launch_age=None if self._jump_started is None else now - self._jump_started,
                             pounce=progress)
        if self._drag_offset is not None or (self.autonomy and self.autonomy.swatting):
            frame = 0
        self.sprite_frame = frame
        key = (state, self.facing, frame)
        if key != self._sprite_key:
            self.character.setPixmap(self.sprites.pixmap(state, self.facing, frame))
            self._sprite_key = key

    def _cancel_walk(self) -> None:
        if self.autonomy:
            self.autonomy.forget_walk()
        self.walking = False
        if hasattr(self, "walk_action"):
            self.walk_action.setChecked(False)

    @pyqtSlot(bool)
    def set_walking(self, enabled: bool, *, automatic: bool = False) -> None:
        if not automatic and self.autonomy:
            self.autonomy.forget_walk()
            self.autonomy.finish_pounce(resume=False)
        if enabled == self.walking:
            return
        if enabled and (not self.physics_enabled or self._closing or self._drag_offset is not None):
            self.walk_action.setChecked(False)
            return
        self.walking = enabled
        self.walk_action.setChecked(enabled)
        self._stop_motion()
        if enabled and not automatic:
            self.setFocus()
        self._start_motion()

    @pyqtSlot(bool)
    def set_autonomy_enabled(self, enabled: bool) -> None:
        self.autonomy_action.setChecked(enabled)
        if self.autonomy:
            self.autonomy.set_enabled(enabled)

    @pyqtSlot(bool)
    def set_cursor_push_enabled(self, enabled: bool) -> None:
        self.cursor_push_action.setChecked(enabled)
        if self.autonomy:
            self.autonomy.cursor_push_enabled = enabled
            if not enabled:
                self.autonomy.finish_pounce()
        self.settings.setValue("autonomy/cursor_push", enabled)
        self.settings.sync()

    @pyqtSlot(bool)
    def set_cursor_carry_enabled(self, enabled: bool) -> None:
        self.cursor_carry_action.setChecked(enabled)
        if self.autonomy:
            self.autonomy.cursor_carry_enabled = enabled
            if not enabled:
                self.autonomy.finish_pounce()
        self.settings.setValue("autonomy/cursor_carry", enabled)
        self.settings.sync()

    def _end_speaking(self) -> None:
        self.talking_timer.stop()
        self._refresh_sprite()

    def set_purr_enabled(self, enabled: bool) -> None:
        self.purr.set_enabled(enabled)
        self.settings.setValue("sound/purr", enabled)
        self.settings.sync()

    def _head_rect(self) -> QRect:
        # Normalized regions in the existing 512px sprites, mirrored with the cat.
        x, y, width, height = ((.76, .37, .23, .25) if self.sprite_state == "walking"
                               else (.38, .04, .46, .34))
        if self.facing < 0:
            x = 1 - x - width
        pixmap = self.character.pixmap()
        rect = pixmap.rect()
        rect.moveCenter(self.character.rect().center())
        return QRect(rect.x() + round(x * rect.width()), rect.y() + round(y * rect.height()),
                     round(width * rect.width()), round(height * rect.height()))

    def _stop_petting(self) -> None:
        was_petting = self.petting
        self.pet_timer.stop()
        self.purr.stop()
        self.petting = False
        self.head_strokes.reset()
        self._refresh_sprite()
        if was_petting:
            QTimer.singleShot(0, self._start_motion)

    def _hover_head(self, event) -> None:
        if (event.buttons() != Qt.MouseButton.NoButton or self._closing or self.menu.isVisible()
                or self._drag_offset is not None
                or self.sprite_state == "falling"
                or (self.autonomy and (self.autonomy.pouncing or self.autonomy.swatting
                                       or self.autonomy.carrying))
                or not self._head_rect().contains(event.position().toPoint())):
            self._stop_petting()
            return
        cursor = event.globalPosition()
        if self.head_strokes.feed(cursor.x(), cursor.y(), time.monotonic()):
            if not self.petting:
                if self.autonomy:
                    self.autonomy.cancel()
                self._cancel_walk()
                self._stop_motion()
            self.petting = True
            self.pet_timer.start()
            self.purr.start()
            self._refresh_sprite()

    def event(self, event) -> bool:
        # Clear hover gestures when switching apps or hiding.
        if (event.type() in (QEvent.Type.WindowDeactivate, QEvent.Type.Hide)
                and hasattr(self, "character")):
            self._stop_petting()
        return super().event(event)

    def _bounds(self) -> tuple[int, int, int, int]:
        if self._physics_screen not in QApplication.screens():
            self._physics_screen = QApplication.primaryScreen()
        area = self._physics_screen.availableGeometry()
        return (area.left(), area.top(), max(area.left(), area.right() - self.width() + 1),
                max(area.top(), area.bottom() - self.height() + 1))

    def _stop_motion(self) -> None:
        self.motion_timer.stop()
        self._jump_started = None
        self.body = Body(float(self.x()), float(self.y()))
        self._refresh_sprite()

    def _pause_motion(self) -> None:
        self._stop_petting()
        if self.autonomy:
            self.autonomy.cancel()
        self.motion_timer.stop()
        self._refresh_sprite()

    def _start_motion(self) -> None:
        if (not self.physics_enabled or self._closing or not self.isVisible()
                or self._drag_offset is not None or self.petting
                or self.menu.isVisible() or self.input.hasFocus()
                or (self.autonomy and (self.autonomy.pouncing or self.autonomy.swatting
                                       or self.autonomy.carrying))):
            return
        self.body.x, self.body.y = float(self.x()), float(self.y())
        self.body.sleeping = False
        self._physics_screen = QApplication.screenAt(self.geometry().center()) or self.screen()
        self._last_tick = time.monotonic()
        self.motion_timer.start()
        self._refresh_sprite()

    @pyqtSlot()
    def _tick_motion(self) -> None:
        now = time.monotonic()
        bounds = self._bounds()
        if self.walking and bounds[0] == bounds[2]:
            self._cancel_walk()
        if self.walking and self.body.y >= bounds[3] - 1 and self.body.vy >= 0:
            self.body.vx = self.facing * 72.0
        self.body.step(now - self._last_tick, bounds)
        if self.walking and self.body.vx:
            # A substep can bounce and move back inside the edge in one tick.
            self.facing = 1 if self.body.vx > 0 else -1
        self._last_tick = now
        self.move(round(self.body.x), round(self.body.y))
        if self.body.sleeping:
            self._jump_started = None
            self.motion_timer.stop()
            self.save_position()
        self._refresh_sprite()

    @pyqtSlot(bool)
    def set_physics_enabled(self, enabled: bool) -> None:
        self.physics_enabled = enabled
        self.physics_action.setChecked(enabled)
        self.jump_action.setEnabled(enabled)
        self.walk_action.setEnabled(enabled)
        if not enabled:
            if self.autonomy:
                self.autonomy.cancel()
            self._cancel_walk()
        self.settings.setValue("physics/enabled", enabled)
        self.settings.sync()
        self._stop_motion()
        if enabled:
            self._start_motion()
        else:
            self.save_position()

    @pyqtSlot()
    def jump(self) -> None:
        if not self.physics_enabled or self._closing or self._drag_offset is not None:
            return
        if self.autonomy:
            self.autonomy.cancel()
        self._cancel_walk()
        self.setFocus()
        self._stop_motion()
        self.body.vy = -650.0
        self._jump_started = time.monotonic()
        self._start_motion()

    def _screen_added(self, screen) -> None:
        screen.availableGeometryChanged.connect(self._screen_changed)
        self._screen_changed()

    def _screen_changed(self, *_args) -> None:
        if self.autonomy:
            self.autonomy.cancel()
        self._stop_motion()
        if not any(screen.availableGeometry().contains(self.geometry()) for screen in QApplication.screens()):
            self.place_bottom_right()
            self.save_position()
        self._start_motion()

    def set_mode(self, live: bool, *, announce: bool = True) -> None:
        if self.worker is not None:
            return
        self._end_speaking()
        self.live = live
        self.demo_action.setChecked(not live)
        self.live_action.setChecked(live)
        self.setWindowTitle("Mascota virtual · " + ("OpenAI" if live else "Prueba local"))
        self.mode.setText("OPENAI · consume tokens" if live else "PRUEBA LOCAL · sin consumo")
        if not announce:
            return
        if live and not has_openai_key():
            self.show_response("OpenAI está seleccionado, pero falta una clave válida. Magnífica conexión imaginaria.")
        elif live:
            self.show_response("OpenAI activado. Cada pregunta consume tokens; elige tus batallas.")
        else:
            self.show_response("Modo de prueba local. Escribe algo y pulsa Enter: sarcasmo gratis, por ahora.")

    def place_bottom_right(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(max(area.left(), area.right() - self.width() - 19),
                      max(area.top(), area.bottom() - self.height() - 19))

    def restore_position(self) -> bool:
        if not (self.settings.contains("window/x") and self.settings.contains("window/y")):
            return False
        try:
            x = self.settings.value("window/x", type=int)
            y = self.settings.value("window/y", type=int)
        except (TypeError, ValueError, OverflowError):
            return False
        position = QPoint(x, y)
        geometry = self.geometry()
        geometry.moveTopLeft(position)
        if not any(screen.availableGeometry().contains(geometry)
                   for screen in QApplication.screens()):
            return False
        self.move(position)
        return True

    def save_position(self) -> None:
        self.settings.setValue("window/x", self.x())
        self.settings.setValue("window/y", self.y())
        self.settings.sync()

    @pyqtSlot()
    def reset_position(self) -> None:
        if self.autonomy:
            self.autonomy.cancel()
        self._cancel_walk()
        self._stop_motion()
        self.place_bottom_right()
        self.save_position()
        self._start_motion()

    def eventFilter(self, watched, event) -> bool:
        if watched is getattr(self, "input", None):
            if event.type() == QEvent.Type.FocusIn:
                self._stop_petting()
                if self.autonomy:
                    self.autonomy.cancel()
                self._cancel_walk()
                self._stop_motion()
            elif event.type() == QEvent.Type.FocusOut:
                QTimer.singleShot(0, self._start_motion)
        if watched is self.character:
            if event.type() in (QEvent.Type.UngrabMouse, QEvent.Type.Leave, QEvent.Type.MouseButtonPress):
                self._stop_petting()
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                if self.autonomy:
                    self.autonomy.cancel()
                self._cancel_walk()
                self._stop_motion()
                self.setFocus()
                self.drag_velocity = DragVelocity()
                self.drag_velocity.record(time.monotonic(), self.x(), self.y())
                self._drag_offset = event.globalPosition().toPoint() - self.pos()
                self._refresh_sprite()
                self.character.setCursor(Qt.CursorShape.ClosedHandCursor)
                return True
            if event.type() == QEvent.Type.MouseMove and self._drag_offset is None:
                self._hover_head(event)
                return True
            if event.type() == QEvent.Type.MouseMove and self._drag_offset is not None:
                cursor = event.globalPosition().toPoint()
                position = cursor - self._drag_offset
                screen = QApplication.screenAt(cursor) or self.screen()
                area = screen.availableGeometry()
                position.setX(max(area.left(), min(position.x(), area.right() - self.width() + 1)))
                position.setY(max(area.top(), min(position.y(), area.bottom() - self.height() + 1)))
                self.move(position)
                self.drag_velocity.record(time.monotonic(), self.x(), self.y())
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if self._drag_offset is None:
                    return True
                self._drag_offset = None
                self.character.setCursor(Qt.CursorShape.OpenHandCursor)
                self.save_position()
                self.body.vx, self.body.vy = self.drag_velocity.release(time.monotonic())
                self._start_motion()
                self._refresh_sprite()
                return True
        return super().eventFilter(watched, event)

    @pyqtSlot()
    def submit(self) -> None:
        question = self.input.text().strip()
        if not question or self.worker is not None or self._closing:
            return
        if self.autonomy:
            self.autonomy.cancel()
        self._cancel_walk()
        self._end_speaking()
        self.input.setEnabled(False)
        self.show_response("Pensando… sí, eso también lleva tiempo.")
        responder = self._custom_responder or (lambda value: answer_question(value, live=self.live))
        self.worker = AnswerThread(question, responder, self)
        self.worker.answered.connect(self._on_answer)
        self.worker.failed.connect(self.show_response)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
        self.demo_action.setEnabled(False)
        self.live_action.setEnabled(False)

    @pyqtSlot(str)
    def show_response(self, text: str) -> None:
        self._last_response_at = time.monotonic()
        self.bubble.setText(text)
        self.scroll.verticalScrollBar().setValue(0)

    @pyqtSlot(str)
    def _on_answer(self, text: str) -> None:
        if self._closing:
            return
        self.input.clear()
        self.show_response(text)
        self.talking_timer.start(max(1800, min(6500, len(text) * 45)))
        self._refresh_sprite()

    @pyqtSlot()
    def _on_finished(self) -> None:
        if self.worker is not None:
            self.worker.deleteLater()
            self.worker = None
        if self._closing:
            self.close()
            # A previously hidden window may not emit lastWindowClosed.
            QApplication.instance().quit()
            return
        self.input.setEnabled(True)
        self.demo_action.setEnabled(True)
        self.live_action.setEnabled(True)
        self.input.setFocus()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._closing = True
        self._stop_petting()
        if self.autonomy:
            self.autonomy.close()
        self._cancel_walk()
        self.talking_timer.stop()
        self._stop_motion()
        self.save_position()
        if self.worker is not None:
            # Hide immediately; keep Qt alive until the HTTP worker finishes safely.
            # Never terminate a running thread or block the GUI with wait().
            self._closing = True
            self.hide()
            event.ignore()
        else:
            event.accept()
