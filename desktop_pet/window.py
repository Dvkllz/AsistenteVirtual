"""Transparent, draggable desktop pet. Network work stays off the GUI thread."""

from collections.abc import Callable
from pathlib import Path
import time

from PyQt6.QtCore import QEvent, QPoint, QSettings, Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QActionGroup, QCloseEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QLabel, QLineEdit, QMenu, QScrollArea, QVBoxLayout, QWidget,
)

from desktop_pet.service import MAX_QUESTION_CHARS, PetServiceError, answer_question, has_openai_key
from desktop_pet.physics import Body, DragVelocity

ASSET_PATH = Path(__file__).resolve().parent.parent / "assets" / "placeholder.png"


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
        self._drag_offset: QPoint | None = None
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
        self.setFixedSize(268, 360)
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
        self.character.setFixedHeight(140)
        self.character.setAccessibleName("Mascota; arrastra para mover y clic derecho para cerrar")
        self.character.setToolTip("Arrastra y suelta para lanzarme · Clic derecho para opciones")
        self.character.setCursor(Qt.CursorShape.OpenHandCursor)
        pixmap = QPixmap(str(ASSET_PATH))
        if pixmap.isNull():
            self.character.setText("No se encontró assets/placeholder.png")
            self.character.setStyleSheet("color: white; background: #202536; border-radius: 16px;")
        else:
            self.character.setPixmap(pixmap.scaled(146, 140, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation))
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
        self.menu.aboutToShow.connect(self.motion_timer.stop)
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
        QTimer.singleShot(0, self._start_motion)

    def _bounds(self) -> tuple[int, int, int, int]:
        if self._physics_screen not in QApplication.screens():
            self._physics_screen = QApplication.primaryScreen()
        area = self._physics_screen.availableGeometry()
        return (area.left(), area.top(), max(area.left(), area.right() - self.width() + 1),
                max(area.top(), area.bottom() - self.height() + 1))

    def _stop_motion(self) -> None:
        self.motion_timer.stop()
        self.body = Body(float(self.x()), float(self.y()))

    def _start_motion(self) -> None:
        if (not self.physics_enabled or self._closing or not self.isVisible()
                or self._drag_offset is not None or self.menu.isVisible() or self.input.hasFocus()):
            return
        self.body.x, self.body.y = float(self.x()), float(self.y())
        self.body.sleeping = False
        self._physics_screen = QApplication.screenAt(self.geometry().center()) or self.screen()
        self._last_tick = time.monotonic()
        self.motion_timer.start()

    @pyqtSlot()
    def _tick_motion(self) -> None:
        now = time.monotonic()
        self.body.step(now - self._last_tick, self._bounds())
        self._last_tick = now
        self.move(round(self.body.x), round(self.body.y))
        if self.body.sleeping:
            self.motion_timer.stop()
            self.save_position()

    @pyqtSlot(bool)
    def set_physics_enabled(self, enabled: bool) -> None:
        self.physics_enabled = enabled
        self.physics_action.setChecked(enabled)
        self.jump_action.setEnabled(enabled)
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
        self.setFocus()
        self._stop_motion()
        self.body.vy = -650.0
        self._start_motion()

    def _screen_added(self, screen) -> None:
        screen.availableGeometryChanged.connect(self._screen_changed)
        self._screen_changed()

    def _screen_changed(self, *_args) -> None:
        self._stop_motion()
        if not any(screen.availableGeometry().contains(self.geometry()) for screen in QApplication.screens()):
            self.place_bottom_right()
            self.save_position()
        self._start_motion()

    def set_mode(self, live: bool, *, announce: bool = True) -> None:
        if self.worker is not None:
            return
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
        self._stop_motion()
        self.place_bottom_right()
        self.save_position()
        self._start_motion()

    def eventFilter(self, watched, event) -> bool:
        if watched is getattr(self, "input", None):
            if event.type() == QEvent.Type.FocusIn:
                self._stop_motion()
            elif event.type() == QEvent.Type.FocusOut:
                QTimer.singleShot(0, self._start_motion)
        if watched is self.character:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._stop_motion()
                self.setFocus()
                self.drag_velocity = DragVelocity()
                self.drag_velocity.record(time.monotonic(), self.x(), self.y())
                self._drag_offset = event.globalPosition().toPoint() - self.pos()
                self.character.setCursor(Qt.CursorShape.ClosedHandCursor)
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
                self._drag_offset = None
                self.character.setCursor(Qt.CursorShape.OpenHandCursor)
                self.save_position()
                self.body.vx, self.body.vy = self.drag_velocity.release(time.monotonic())
                self._start_motion()
                return True
        return super().eventFilter(watched, event)

    @pyqtSlot()
    def submit(self) -> None:
        question = self.input.text().strip()
        if not question or self.worker is not None or self._closing:
            return
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
        self.bubble.setText(text)
        self.scroll.verticalScrollBar().setValue(0)

    @pyqtSlot(str)
    def _on_answer(self, text: str) -> None:
        self.input.clear()
        self.show_response(text)

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
