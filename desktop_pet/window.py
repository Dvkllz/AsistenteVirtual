"""Transparent, draggable desktop pet. Network work stays off the GUI thread."""

from collections.abc import Callable
from pathlib import Path

from PyQt6.QtCore import QEvent, QPoint, Qt, QThread, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QCloseEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QLabel, QLineEdit, QMenu, QScrollArea, QVBoxLayout, QWidget,
)

from desktop_pet.service import MAX_QUESTION_CHARS, PetServiceError, answer_question

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
    def __init__(self, *, live: bool = False, responder: Callable[[str], str] | None = None):
        super().__init__()
        self.live = live
        self.responder = responder or (lambda question: answer_question(question, live=live))
        self.worker: AnswerThread | None = None
        self._closing = False
        self._drag_offset: QPoint | None = None

        self.setWindowTitle("Mascota virtual · " + ("OpenAI" if live else "Prueba local"))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 440)
        self.setStyleSheet("""
            QWidget { font-family: 'Segoe UI'; font-size: 13px; }
            QLabel#bubble {
                background: #202536; color: #f3f5fc; border: 1px solid #404961;
                border-radius: 16px; padding: 14px;
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
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(7)

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
        self.scroll.setFixedHeight(154)
        self.scroll.setWidget(self.bubble)
        layout.addWidget(self.scroll)

        self.character = QLabel()
        self.character.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.character.setFixedHeight(182)
        self.character.setAccessibleName("Mascota; arrastra para mover y clic derecho para cerrar")
        self.character.setToolTip("Arrástrame para moverme · Clic derecho para cerrar")
        self.character.setCursor(Qt.CursorShape.OpenHandCursor)
        pixmap = QPixmap(str(ASSET_PATH))
        if pixmap.isNull():
            self.character.setText("No se encontró assets/placeholder.png")
            self.character.setStyleSheet("color: white; background: #202536; border-radius: 16px;")
        else:
            self.character.setPixmap(pixmap.scaled(190, 182, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation))
        self.character.installEventFilter(self)
        layout.addWidget(self.character)

        self.input = QLineEdit()
        self.input.setMaxLength(MAX_QUESTION_CHARS)
        self.input.setPlaceholderText("Pregúntame algo…  ↵")
        self.input.setAccessibleName("Pregunta; Enter para enviar")
        self.input.returnPressed.connect(self.submit)
        layout.addWidget(self.input)
        self.mode = QLabel("OPENAI · consume tokens" if live else "PRUEBA LOCAL · sin consumo")
        self.mode.setObjectName("mode")
        layout.addWidget(self.mode, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.menu = QMenu(self)
        close_action = QAction("Cerrar mascota", self)
        close_action.triggered.connect(self.close)
        self.menu.addAction(close_action)
        for surface in (self, self.character, self.bubble, self.mode):
            surface.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            surface.customContextMenuRequested.connect(
                lambda point, target=surface: self.menu.popup(target.mapToGlobal(point))
            )

        self.show_response("Aquí estoy. Pregunta algo; intentaré disimular mi entusiasmo."
                           if live else "Modo de prueba local. Escribe algo y pulsa Enter: sarcasmo gratis, por ahora.")
        self.place_bottom_right()

    def place_bottom_right(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            area = screen.availableGeometry()
            self.move(max(area.left(), area.right() - self.width() - 19),
                      max(area.top(), area.bottom() - self.height() - 19))

    def eventFilter(self, watched, event) -> bool:
        if watched is self.character:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
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
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._drag_offset = None
                self.character.setCursor(Qt.CursorShape.OpenHandCursor)
                return True
        return super().eventFilter(watched, event)

    @pyqtSlot()
    def submit(self) -> None:
        question = self.input.text().strip()
        if not question or self.worker is not None or self._closing:
            return
        self.input.setEnabled(False)
        self.show_response("Pensando… sí, eso también lleva tiempo.")
        self.worker = AnswerThread(question, self.responder, self)
        self.worker.answered.connect(self._on_answer)
        self.worker.failed.connect(self.show_response)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

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
        self.input.setFocus()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.worker is not None:
            # Hide immediately; keep Qt alive until the HTTP worker finishes safely.
            # Never terminate a running thread or block the GUI with wait().
            self._closing = True
            self.hide()
            event.ignore()
        else:
            event.accept()
