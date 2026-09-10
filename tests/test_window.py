import os
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtCore import QEvent, QPointF, QSettings, Qt, QTimer
from PyQt6.QtGui import QImage, QMouseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from desktop_pet.service import PetServiceError
from desktop_pet.window import ASSET_PATH, PetWindow


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.guard = patch('socket.socket.connect', side_effect=AssertionError('Network forbidden in tests'))
        self.guard.start()
        self.windows = []
        self.temp_settings = TemporaryDirectory()
        self.settings = QSettings(str(Path(self.temp_settings.name) / 'settings.ini'), QSettings.Format.IniFormat)
        self.settings.setValue('physics/enabled', False)

    def tearDown(self):
        for window in self.windows:
            self.wait_until(lambda: window.worker is None)
            window.close()
            window.deleteLater()
        self.app.processEvents()
        self.guard.stop()
        self.temp_settings.cleanup()

    def make_window(self, **kwargs):
        kwargs.setdefault('settings', self.settings)
        window = PetWindow(**kwargs)
        self.windows.append(window)
        window.show()
        self.app.processEvents()
        return window

    def wait_until(self, predicate, timeout=3000):
        deadline = time.monotonic() + timeout / 1000
        while not predicate() and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertTrue(predicate(), 'Timed out waiting for UI state')

    def test_transparency_placement_and_asset(self):
        window = self.make_window()
        self.assertTrue(window.windowFlags() & Qt.WindowType.FramelessWindowHint)
        self.assertTrue(window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.assertTrue(window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground))
        self.assertTrue(self.app.primaryScreen().availableGeometry().contains(window.geometry()))
        image = QImage(str(ASSET_PATH))
        self.assertFalse(image.isNull())
        self.assertTrue(image.hasAlphaChannel())
        self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
        self.assertFalse(window.character.pixmap().isNull())
        artifacts = Path(__file__).resolve().parent.parent / 'artifacts'
        artifacts.mkdir(exist_ok=True)
        self.assertTrue(window.grab().save(str(artifacts / 'mascota-preview.png')))

    def test_enter_keeps_event_loop_alive_and_blocks_duplicates(self):
        gate = threading.Event()
        calls = []

        def respond(question):
            calls.append((question, threading.get_ident()))
            gate.wait(2)
            return 'Respuesta lista.'

        window = self.make_window(responder=respond)
        window.input.setText('Hola')
        QTest.keyClick(window.input, Qt.Key.Key_Return)
        try:
            self.assertFalse(window.input.isEnabled())
            ticks = []
            QTimer.singleShot(10, lambda: ticks.append(True))
            self.wait_until(lambda: bool(ticks) and bool(calls))
            window.submit()
            self.assertEqual(len(calls), 1)
            self.assertNotEqual(calls[0][1], threading.get_ident())
        finally:
            gate.set()
        self.wait_until(lambda: window.worker is None)
        self.assertEqual(window.bubble.text(), 'Respuesta lista.')
        self.assertTrue(window.input.isEnabled())
        self.assertEqual(window.input.text(), '')

    def test_error_preserves_question_for_retry(self):
        def fail(question):
            raise PetServiceError('Sin conexión.')
        window = self.make_window(responder=fail)
        window.input.setText('Pregunta pendiente')
        window.submit()
        self.wait_until(lambda: window.worker is None)
        self.assertEqual(window.bubble.text(), 'Sin conexión.')
        self.assertEqual(window.input.text(), 'Pregunta pendiente')
        self.assertTrue(window.input.isEnabled())

    def test_long_plain_text_scrolls(self):
        window = self.make_window()
        text = '<b>No es HTML</b> ' + ('Una respuesta larga. ' * 150)
        window.show_response(text)
        QTest.qWait(40)
        self.assertEqual(window.bubble.textFormat(), Qt.TextFormat.PlainText)
        self.assertGreater(window.scroll.verticalScrollBar().maximum(), 0)

    def test_drag_character(self):
        window = self.make_window()
        start = window.pos()
        local = QPointF(window.character.rect().center())
        global_start = QPointF(window.character.mapToGlobal(local.toPoint()))
        for kind, global_pos, button, buttons in [
            (QEvent.Type.MouseButtonPress, global_start, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton),
            (QEvent.Type.MouseMove, global_start - QPointF(40, 30), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton),
            (QEvent.Type.MouseButtonRelease, global_start - QPointF(40, 30), Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton),
        ]:
            event = QMouseEvent(kind, local, global_pos, button, buttons, Qt.KeyboardModifier.NoModifier)
            self.app.sendEvent(window.character, event)
        self.assertEqual(window.pos(), start - QPointF(40, 30).toPoint())
        self.assertIsNone(window._drag_offset)
        self.assertEqual(self.settings.value('window/x', type=int), window.x())
        self.assertEqual(self.settings.value('window/y', type=int), window.y())

    def test_saved_position_is_restored(self):
        self.settings.setValue('window/x', 40)
        self.settings.setValue('window/y', 50)
        window = self.make_window()
        self.assertEqual(window.pos(), QPointF(40, 50).toPoint())
        window.reset_position()
        self.assertTrue(self.app.primaryScreen().availableGeometry().contains(window.geometry()))

    def test_mode_switch_changes_responder_without_duplicate_request(self):
        with patch('desktop_pet.window.has_openai_key', return_value=True), \
                patch('desktop_pet.window.answer_question', return_value='Respuesta OpenAI') as answer:
            window = self.make_window()
            window.live_action.trigger()
            self.assertTrue(window.live)
            self.assertIn('consume tokens', window.mode.text())
            window.input.setText('Hola')
            window.submit()
            self.assertFalse(window.demo_action.isEnabled())
            self.wait_until(lambda: window.worker is None)
            answer.assert_called_once_with('Hola', live=True)
            self.assertTrue(window.demo_action.isEnabled())
            window.demo_action.trigger()
            self.assertFalse(window.live)

    def test_context_menu_close_during_request(self):
        gate = threading.Event()
        window = self.make_window(responder=lambda question: (gate.wait(2), 'Terminado')[1])
        window.input.setText('Hola')
        window.submit()
        try:
            window.character.customContextMenuRequested.emit(window.character.rect().center())
            self.app.processEvents()
            self.assertTrue(window.menu.isVisible())
            window.menu.hide()
            window.close_action.trigger()
            self.assertTrue(window._closing)
            self.assertFalse(window.isVisible())
        finally:
            gate.set()
        self.wait_until(lambda: window.worker is None)
        self.assertFalse(window.isVisible())

    def test_empty_enter_does_not_start_worker(self):
        window = self.make_window(responder=lambda question: self.fail('Unexpected request'))
        window.input.setText('   ')
        QTest.keyClick(window.input, Qt.Key.Key_Return)
        self.assertIsNone(window.worker)

    def test_smaller_character_keeps_text_readable(self):
        window = self.make_window()
        self.assertEqual((window.width(), window.height()), (268, 360))
        self.assertLessEqual(window.character.pixmap().height(), 140)
        self.assertGreaterEqual(window.input.height(), 35)

    def test_physics_timer_settles_and_saves_only_at_rest(self):
        window = self.make_window()
        window.physics_action.trigger()
        window.setFocus()
        window.move(window.x(), window.y() - 100)
        window._start_motion()
        self.assertTrue(window.motion_timer.isActive())
        window.motion_timer.stop()
        with patch.object(window, 'save_position') as save:
            for _ in range(1000):
                window._last_tick = time.monotonic() - 1 / 60
                window._tick_motion()
                if window.body.sleeping:
                    break
            self.assertTrue(window.body.sleeping)
            save.assert_called_once()
        self.assertFalse(window.motion_timer.isActive())
        self.assertEqual(window.y(), window._bounds()[3])

    def test_typing_pauses_motion_and_toggle_is_persistent(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.setFocus()
        window.jump()
        self.assertTrue(window.motion_timer.isActive())
        window.input.setFocus()
        self.app.processEvents()
        self.assertFalse(window.motion_timer.isActive())
        window.set_physics_enabled(False)
        self.assertFalse(window.jump_action.isEnabled())
        self.assertFalse(self.settings.value('physics/enabled', type=bool))
        window.jump()
        self.assertFalse(window.motion_timer.isActive())

    def test_menu_pauses_motion_and_close_stops_timer(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.setFocus()
        window.jump()
        window.menu.popup(window.mapToGlobal(window.rect().center()))
        self.app.processEvents()
        self.assertFalse(window.motion_timer.isActive())
        window.menu.hide()
        window.close()
        self.app.processEvents()
        self.assertFalse(window.motion_timer.isActive())

    def test_invalid_and_partially_offscreen_position_falls_back(self):
        for x, y in [('broken', 10), (-267, 10), (999999, 999999)]:
            self.settings.setValue('window/x', x)
            self.settings.setValue('window/y', y)
            window = self.make_window()
            self.assertTrue(self.app.primaryScreen().availableGeometry().contains(window.geometry()))

    def test_releasing_character_starts_gravity_and_regrabbing_stops_it(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.move(window.x(), window.y() - 140)
        local = QPointF(window.character.rect().center())
        origin = QPointF(window.character.mapToGlobal(local.toPoint()))
        for kind, point, button, buttons in [
            (QEvent.Type.MouseButtonPress, origin, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton),
            (QEvent.Type.MouseMove, origin - QPointF(20, 20), Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton),
            (QEvent.Type.MouseButtonRelease, origin - QPointF(20, 20), Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton),
        ]:
            self.app.sendEvent(window.character, QMouseEvent(kind, local, point, button, buttons,
                                                            Qt.KeyboardModifier.NoModifier))
        self.assertTrue(window.motion_timer.isActive())
        released_y = window.y()
        self.wait_until(lambda: window.y() > released_y + 5)
        current = QPointF(window.character.mapToGlobal(local.toPoint()))
        self.app.sendEvent(window.character, QMouseEvent(QEvent.Type.MouseButtonPress, local, current,
                           Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
        self.assertFalse(window.motion_timer.isActive())
        self.assertEqual((window.body.vx, window.body.vy), (0, 0))
