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
from desktop_pet.autonomy import IdleMouse, QUIPS


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
        self.settings.setValue('sound/purr', False)
        self.settings.setValue('autonomy/cursor_push', False)
        self.settings.setValue('autonomy/cursor_carry', False)
        self.cursor_guard = patch('desktop_pet.autonomy.QCursor.setPos',
                                  side_effect=AssertionError('Real cursor writes forbidden in tests'))
        self.cursor_guard.start()

    def tearDown(self):
        for window in self.windows:
            self.wait_until(lambda: window.worker is None)
            window.close()
            window.deleteLater()
        self.app.processEvents()
        self.guard.stop()
        self.cursor_guard.stop()
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
            event = QMouseEvent(kind, local, global_pos, button, buttons, Qt.KeyboardModifier.ShiftModifier)
            self.app.sendEvent(window.character, event)
        self.assertEqual(window.pos(), start - QPointF(40, 30).toPoint())
        self.assertIsNone(window._drag_offset)
        self.assertEqual(self.settings.value('window/x', type=int), window.x())
        self.assertEqual(self.settings.value('window/y', type=int), window.y())

    def pet_event(self, window, kind, offset=0, *, outside=False, held=True):
        point = QPointF(window.character.rect().center()) + QPointF(offset, 0)
        if outside:
            point = QPointF(-10, -10)
        button = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else Qt.MouseButton.LeftButton
        buttons = Qt.MouseButton.LeftButton if held else Qt.MouseButton.NoButton
        event = QMouseEvent(kind, point, QPointF(window.character.mapToGlobal(point.toPoint())),
                            button, buttons, Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(window.character, event)

    def test_pet_requires_held_movement_without_dragging(self):
        window = self.make_window()
        start = window.pos()
        self.pet_event(window, QEvent.Type.MouseMove, 4, held=False)
        self.assertFalse(window.petting)
        self.pet_event(window, QEvent.Type.MouseButtonPress)
        self.assertTrue(window._pet_held)
        self.assertFalse(window.petting)
        self.assertIsNone(window._drag_offset)
        with patch.object(window.purr, 'start') as purr:
            self.pet_event(window, QEvent.Type.MouseMove, 8)
            purr.assert_called_once()
        self.assertEqual(window.sprite_state, 'petting')
        self.assertEqual(window.pos(), start)
        self.assertTrue(window.autonomy.busy())
        artifacts = Path(__file__).resolve().parent.parent / 'artifacts'
        artifacts.mkdir(exist_ok=True)
        window.grab().save(str(artifacts / 'mascota-petting-preview.png'))
        self.pet_event(window, QEvent.Type.MouseButtonRelease, 8, held=False)
        self.assertFalse(window._pet_held)
        self.assertFalse(window.petting)
        self.assertFalse(window.pet_timer.isActive())
        self.assertFalse(window.purr.wanted)
        self.assertEqual(window.sprite_state, 'idle')

    def test_pet_stops_when_still_or_outside_and_resumes_with_movement(self):
        window = self.make_window()
        self.pet_event(window, QEvent.Type.MouseButtonPress)
        self.pet_event(window, QEvent.Type.MouseMove, 8)
        window.pet_timer.start(20)
        self.wait_until(lambda: not window.petting)
        self.assertTrue(window._pet_held)
        self.pet_event(window, QEvent.Type.MouseMove, -8)
        self.assertTrue(window.petting)
        self.pet_event(window, QEvent.Type.MouseMove, outside=True)
        self.assertFalse(window.petting)
        self.assertFalse(window.purr.wanted)
        self.pet_event(window, QEvent.Type.MouseMove, 0)
        self.assertTrue(window.petting)
        self.pet_event(window, QEvent.Type.MouseMove, 8, held=False)
        self.assertFalse(window._pet_held)
        self.assertFalse(window.petting)

    def test_pet_pauses_physics_and_resumes_on_release(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        self.pet_event(window, QEvent.Type.MouseButtonPress)
        self.pet_event(window, QEvent.Type.MouseMove, 8)
        window._start_motion()
        self.assertFalse(window.motion_timer.isActive())
        self.assertEqual(window.sprite_state, 'petting')
        self.pet_event(window, QEvent.Type.MouseButtonRelease, 8, held=False)
        self.assertTrue(window.motion_timer.isActive())

    def test_pet_cancels_on_menu_deactivate_hide_ungrab_and_close(self):
        for action in ('menu', 'deactivate', 'hide', 'ungrab', 'close'):
            window = self.make_window()
            self.pet_event(window, QEvent.Type.MouseButtonPress)
            self.pet_event(window, QEvent.Type.MouseMove, 8)
            if action == 'menu':
                window._pause_motion()
            elif action == 'deactivate':
                self.app.sendEvent(window, QEvent(QEvent.Type.WindowDeactivate))
            elif action == 'hide':
                window.hide()
            elif action == 'ungrab':
                self.app.sendEvent(window.character, QEvent(QEvent.Type.UngrabMouse))
            else:
                window.close()
            self.assertFalse(window.petting, action)
            self.assertFalse(window._pet_held, action)
            self.assertFalse(window.pet_timer.isActive(), action)
            self.assertFalse(window.purr.wanted, action)

    def test_purr_toggle_persists_and_pet_pose_works_muted(self):
        window = self.make_window()
        window.purr.effect.setMuted(True)
        window.purr_action.setChecked(True)
        self.assertTrue(self.settings.value('sound/purr', type=bool))
        self.pet_event(window, QEvent.Type.MouseButtonPress)
        self.pet_event(window, QEvent.Type.MouseMove, 8)
        self.assertTrue(window.purr.wanted)
        window.purr_action.setChecked(False)
        self.assertFalse(window.purr.wanted)
        self.assertFalse(self.settings.value('sound/purr', type=bool))
        self.assertEqual(window.sprite_state, 'petting')

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

    def test_answer_uses_talking_pose_then_returns_to_idle(self):
        window = self.make_window(responder=lambda question: 'Miau. De nada.')
        self.assertEqual(window.sprite_state, 'idle')
        window.input.setText('Hola')
        window.submit()
        self.wait_until(lambda: window.worker is None)
        self.assertEqual(window.sprite_state, 'talking')
        self.assertTrue(window.talking_timer.isActive())
        window.talking_timer.start(20)
        self.wait_until(lambda: window.sprite_state == 'idle')

    def test_drag_and_jump_choose_falling_sprite(self):
        window = self.make_window()
        QTest.mousePress(window.character, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(window.sprite_state, 'falling')
        QTest.mouseRelease(window.character, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(window.sprite_state, 'idle')
        window.set_physics_enabled(True)
        window.jump()
        self.assertEqual(window.sprite_state, 'falling')

    def test_walk_reverses_at_both_edges_and_stays_in_bounds(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        left, top, right, bottom = window._bounds()
        for edge, direction in ((right, 1), (left, -1)):
            window.set_walking(False)
            window.move(edge, bottom)
            window.facing = direction
            window.set_walking(True)
            self.assertEqual(window.sprite_state, 'walking')
            window._last_tick = time.monotonic() - 1 / 60
            window._tick_motion()
            self.assertEqual(window.facing, -direction)
            for _ in range(10):
                window._last_tick = time.monotonic() - 1 / 60
                window._tick_motion()
            self.assertTrue(left <= window.x() <= right)
            self.assertGreater(abs(window.body.x - edge), 5)
            self.assertTrue(window.motion_timer.isActive())
        window.set_walking(False)
        self.assertFalse(window.walking)
        self.assertFalse(window.walk_action.isChecked())

    def test_walking_is_cancelled_for_typing_and_physics_off(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.move(window.x(), window._bounds()[3])
        window.set_walking(True)
        self.assertTrue(window.walking)
        window.input.setFocus()
        self.app.processEvents()
        self.assertFalse(window.walking)
        self.assertFalse(window.motion_timer.isActive())
        self.assertEqual(window.sprite_state, 'idle')
        window.set_walking(True)
        window.set_physics_enabled(False)
        self.assertFalse(window.walking)
        self.assertFalse(window.walk_action.isEnabled())
        window.set_walking(True)
        self.assertFalse(window.walking)

    def test_close_does_not_restart_sprite_or_movement_timers(self):
        window = self.make_window()
        window._on_answer('Miau')
        window.close()
        window._on_answer('Late answer')
        self.app.processEvents()
        self.assertFalse(window.motion_timer.isActive())
        self.assertFalse(window.talking_timer.isActive())

    def test_smaller_character_keeps_text_readable(self):
        window = self.make_window()
        self.assertEqual((window.width(), window.height()), (268, 332))
        self.assertEqual(window.character.pixmap().height(), 112)
        self.assertGreaterEqual(window.input.height(), 35)

    def test_automatic_walk_is_short_and_does_not_take_focus(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.setFocus()
        auto = window.autonomy
        auto.timer.stop()
        auto.next_walk = 0
        auto.next_quip = float('inf')
        with patch.object(window, 'setFocus', side_effect=AssertionError('Focus stolen')):
            auto.tick()
        self.assertTrue(auto.auto_walking)
        self.assertTrue(window.walking)
        self.assertTrue(5000 <= auto.walk_timer.interval() <= 10000)
        auto.end_walk()
        self.assertFalse(window.walking)

    def test_automatic_jokes_are_local_and_respect_recent_or_pending_text(self):
        window = self.make_window()
        auto = window.autonomy
        auto.timer.stop()
        auto.next_walk = float('inf')
        auto.next_quip = 0
        original = window.bubble.text()
        auto.tick()
        self.assertEqual(window.bubble.text(), original)
        window._last_response_at = time.monotonic() - 21
        with patch('desktop_pet.window.answer_question', side_effect=AssertionError('Network request')):
            auto.tick()
        self.assertIn(window.bubble.text(), QUIPS)
        self.assertTrue(window.talking_timer.isActive())
        quip = window.bubble.text()
        window.input.setText('Pregunta sin enviar')
        auto.next_quip = 0
        window._last_response_at = 0
        auto.tick()
        self.assertEqual(window.input.text(), 'Pregunta sin enviar')
        self.assertEqual(window.bubble.text(), quip)
        self.assertIsNone(window.worker)

    def test_cursor_pounce_uses_ten_second_delay_and_never_moves_cursor(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.setFocus()
        auto = window.autonomy
        auto.timer.stop()
        auto.next_walk = auto.next_quip = float('inf')
        area = window.screen().availableGeometry()
        target = area.topLeft() + QPointF(60, area.height() // 2).toPoint()
        auto.mouse = IdleMouse(100, target)
        with patch('desktop_pet.autonomy.QCursor.pos', return_value=target), \
                patch('desktop_pet.autonomy.QCursor.setPos', side_effect=AssertionError('Cursor moved')), \
                patch('desktop_pet.autonomy.time.monotonic', return_value=109.9):
            auto.tick()
            self.assertFalse(auto.pouncing)
        with patch('desktop_pet.autonomy.QCursor.pos', return_value=target), \
                patch('desktop_pet.autonomy.QCursor.setPos', side_effect=AssertionError('Cursor moved')), \
                patch('desktop_pet.autonomy.time.monotonic', return_value=110):
            auto.tick()
            self.assertTrue(auto.pouncing)
            self.assertEqual(window.sprite_state, 'falling')
            auto.animation.setCurrentTime(auto.animation.duration())
            self.assertTrue(auto.swatting)
            self.assertEqual(window.sprite_state, 'walking')
            self.assertTrue(auto.effect.windowFlags() & Qt.WindowType.WindowTransparentForInput)
            self.assertTrue(area.contains(window.geometry()))
            self.assertTrue(auto.effect.isVisible())
            artifacts = Path(__file__).resolve().parent.parent / 'artifacts'
            artifacts.mkdir(exist_ok=True)
            self.assertTrue(window.grab().save(str(artifacts / 'mascota-swat-preview.png')))
            auto.finish_pounce()
            auto.tick()
            self.assertFalse(auto.pouncing)
            self.assertFalse(auto.effect.isVisible())

    def test_mouse_movement_cancels_pounce_and_toggle_stops_all_habits(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.setFocus()
        auto = window.autonomy
        auto.timer.stop()
        target = window.screen().availableGeometry().topLeft() + QPointF(60, 300).toPoint()
        auto.mouse = IdleMouse(time.monotonic(), target)
        auto.pounce(target)
        self.assertTrue(auto.pouncing)
        with patch('desktop_pet.autonomy.QCursor.pos', return_value=target + QPointF(1, 0).toPoint()):
            auto.tick()
        self.assertFalse(auto.pouncing)
        auto.pounce(target)
        window.autonomy_action.trigger()
        self.assertFalse(auto.enabled)
        self.assertFalse(auto.timer.isActive())
        self.assertFalse(auto.pouncing)
        self.assertFalse(auto.swat_timer.isActive())
        self.assertFalse(self.settings.value('autonomy/enabled', type=bool))
        window.autonomy_action.trigger()
        self.assertTrue(auto.timer.isActive())
        window.close()
        self.assertFalse(auto.timer.isActive())
        self.assertFalse(auto.effect.isVisible())

    def test_physics_disabled_prevents_automatic_movement_but_not_jokes(self):
        window = self.make_window()
        auto = window.autonomy
        auto.timer.stop()
        auto.next_walk = 0
        target = window.screen().availableGeometry().topLeft()
        auto.mouse = IdleMouse(time.monotonic() - 11, target)
        with patch('desktop_pet.autonomy.QCursor.pos', return_value=target):
            auto.tick()
        self.assertFalse(window.walking)
        self.assertFalse(auto.pouncing)

    def test_pounce_and_swat_complete_on_event_loop(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.setFocus()
        auto = window.autonomy
        auto.timer.stop()
        target = window.screen().availableGeometry().topLeft() + QPointF(60, 300).toPoint()
        with patch('desktop_pet.autonomy.QCursor.pos', return_value=target):
            auto.pounce(target)
            self.wait_until(lambda: auto.swatting)
            self.assertTrue(auto.effect.isVisible())
            self.wait_until(lambda: not auto.swatting)
        self.assertFalse(auto.pouncing)
        self.assertFalse(auto.effect.isVisible())
        self.assertTrue(window.motion_timer.isActive())

    def test_opening_menu_cancels_pounce_immediately(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.setFocus()
        auto = window.autonomy
        auto.timer.stop()
        target = window.screen().availableGeometry().topLeft() + QPointF(60, 300).toPoint()
        auto.pounce(target)
        window.menu.popup(window.mapToGlobal(window.rect().center()))
        self.app.processEvents()
        self.assertFalse(auto.pouncing)
        self.assertFalse(auto.effect.isVisible())
        self.assertFalse(window.motion_timer.isActive())
        window.menu.hide()

    def test_walk_cycles_frames_and_stops_in_idle(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.move(window.x(), window._bounds()[3])
        window.set_walking(True)
        keys = set()
        for _ in range(5):
            keys.add(window.character.pixmap().cacheKey())
            QTest.qWait(130)
        self.assertGreaterEqual(len(keys), 3)
        window.set_walking(False)
        self.wait_until(lambda: window.sprite_state == 'idle')
        key = window.character.pixmap().cacheKey()
        QTest.qWait(150)
        self.assertEqual(window.character.pixmap().cacheKey(), key)

    def test_pounce_has_four_animation_phases(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.setFocus()
        auto = window.autonomy
        auto.timer.stop()
        target = window.screen().availableGeometry().topLeft() + QPointF(60, 300).toPoint()
        auto.pounce(target)
        for milliseconds, expected in ((0, 1), (250, 2), (500, 3), (750, 0)):
            auto.animation.setCurrentTime(milliseconds)
            self.assertEqual(window.sprite_frame, expected)
        auto.finish_pounce()

    def test_swat_pushes_cursor_once_and_does_not_rearm_itself(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.set_cursor_push_enabled(True)
        window.setFocus()
        auto = window.autonomy
        auto.timer.stop()
        auto.next_walk = auto.next_quip = float('inf')
        target = window.screen().availableGeometry().topLeft() + QPointF(60, 300).toPoint()
        with patch('desktop_pet.autonomy.QCursor.pos', return_value=target), \
                patch('desktop_pet.autonomy.QCursor.setPos') as move:
            auto.pounce(target)
            auto.animation.setCurrentTime(auto.animation.duration())
            move.assert_called_once()
            destination = move.call_args.args[0]
            self.assertEqual(destination, target + QPointF(window.facing * 24, -8).toPoint())
            self.assertTrue(window.screen().availableGeometry().contains(destination))
            auto.swat()
            move.assert_called_once()
        auto.finish_pounce()
        self.assertTrue(auto.mouse.fired)
        self.assertFalse(auto.mouse.poll(time.monotonic() + 50, destination))

    def test_moved_cursor_or_held_button_prevents_contact_push(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.set_cursor_push_enabled(True)
        window.setFocus()
        auto = window.autonomy
        auto.timer.stop()
        target = window.screen().availableGeometry().topLeft() + QPointF(60, 300).toPoint()
        for held, cursor in ((False, target + QPointF(1, 0).toPoint()), (True, target)):
            with patch('desktop_pet.autonomy.mouse_button_down', return_value=False):
                auto.pounce(target)
            with patch('desktop_pet.autonomy.QCursor.pos', return_value=cursor), \
                    patch('desktop_pet.autonomy.mouse_button_down', return_value=held):
                auto.animation.setCurrentTime(auto.animation.duration())
            self.assertFalse(auto.swatting)
            self.assertFalse(auto.pouncing)

    def test_cursor_push_switch_is_persistent_and_cancels_active_attempt(self):
        window = self.make_window()
        window.set_cursor_push_enabled(True)
        self.assertTrue(self.settings.value('autonomy/cursor_push', type=bool))
        self.assertTrue(window.autonomy.cursor_push_enabled)
        window.set_cursor_push_enabled(False)
        self.assertFalse(self.settings.value('autonomy/cursor_push', type=bool))
        self.assertFalse(window.autonomy.cursor_push_enabled)

    def carry_setup(self):
        window = self.make_window()
        window.set_physics_enabled(True)
        window.set_cursor_carry_enabled(True)
        window.place_bottom_right()
        window._stop_motion()
        window.setFocus()
        auto = window.autonomy
        auto.timer.stop()
        target = window.screen().availableGeometry().topLeft() + QPointF(80, 300).toPoint()
        return window, auto, target

    def test_carry_moves_pointer_with_cat_then_releases_at_three_seconds(self):
        window, auto, target = self.carry_setup()
        cursor = [target]
        with patch('desktop_pet.autonomy.QCursor.pos', side_effect=lambda: cursor[0]), \
                patch('desktop_pet.autonomy.QCursor.setPos', side_effect=lambda p: cursor.__setitem__(0, p)) as move:
            auto.pounce(target)
            auto.animation.setCurrentTime(auto.animation.duration())
            self.assertTrue(auto.carrying)
            self.assertFalse(auto.swatting)
            start = window.pos()
            auto.carry_animation.setCurrentTime(1500)
            self.assertNotEqual(window.pos(), start)
            self.assertEqual(cursor[0], window.pos() + auto.mouth_offset())
            self.assertTrue(window.screen().availableGeometry().contains(cursor[0]))
            self.assertTrue(window.screen().availableGeometry().contains(window.geometry()))
            self.assertEqual(window.sprite_state, 'walking')
            self.assertGreater(move.call_count, 0)
            count = move.call_count
            auto.carry_started = time.monotonic() - 3.01
            auto.move_carry(.8)
            self.assertFalse(auto.carrying)
            self.assertEqual(move.call_count, count)
            self.assertTrue(auto.mouse.fired)
            self.assertFalse(auto.mouse.poll(time.monotonic() + 30, cursor[0]))

    def test_user_mouse_movement_releases_without_overwriting_it(self):
        window, auto, target = self.carry_setup()
        cursor = [target]
        with patch('desktop_pet.autonomy.QCursor.pos', side_effect=lambda: cursor[0]), \
                patch('desktop_pet.autonomy.QCursor.setPos', side_effect=lambda p: cursor.__setitem__(0, p)) as move:
            auto.pounce(target)
            auto.animation.setCurrentTime(auto.animation.duration())
            auto.carry_animation.setCurrentTime(500)
            cursor[0] = cursor[0] + QPointF(7, 0).toPoint()
            user_position = cursor[0]
            count = move.call_count
            auto.move_carry(.3)
            self.assertFalse(auto.carrying)
            self.assertEqual(move.call_count, count)
            self.assertEqual(cursor[0], user_position)
            self.assertFalse(auto.mouse.fired)

    def test_escape_and_mouse_button_cancel_carry_before_next_pointer_write(self):
        for interrupt in ('escape_pressed', 'mouse_button_down'):
            window, auto, target = self.carry_setup()
            cursor = [target]
            with patch('desktop_pet.autonomy.QCursor.pos', side_effect=lambda: cursor[0]), \
                    patch('desktop_pet.autonomy.QCursor.setPos', side_effect=lambda p: cursor.__setitem__(0, p)) as move:
                auto.pounce(target)
                auto.animation.setCurrentTime(auto.animation.duration())
                self.assertTrue(auto.carrying)
                count = move.call_count
                with patch('desktop_pet.autonomy.' + interrupt, return_value=True):
                    auto.move_carry(.2)
                self.assertFalse(auto.carrying)
                self.assertEqual(move.call_count, count)
            window.close()

    def test_carry_option_and_close_release_immediately(self):
        for action in ('disable', 'close', 'physics', 'menu'):
            window, auto, target = self.carry_setup()
            cursor = [target]
            with patch('desktop_pet.autonomy.QCursor.pos', side_effect=lambda: cursor[0]), \
                    patch('desktop_pet.autonomy.QCursor.setPos', side_effect=lambda p: cursor.__setitem__(0, p)) as move:
                auto.pounce(target)
                auto.animation.setCurrentTime(auto.animation.duration())
                self.assertTrue(auto.carrying)
                count = move.call_count
                if action == 'disable':
                    window.set_cursor_carry_enabled(False)
                    self.assertFalse(self.settings.value('autonomy/cursor_carry', type=bool))
                elif action == 'close':
                    window.close()
                elif action == 'physics':
                    window.set_physics_enabled(False)
                else:
                    window.menu.popup(window.mapToGlobal(window.rect().center()))
                self.assertFalse(auto.carrying)
                auto.move_carry(.5)
                self.assertEqual(move.call_count, count)
            window.menu.hide()
            window.close()

    def test_carry_completes_on_real_event_loop_without_pointer_writes_after_release(self):
        window, auto, target = self.carry_setup()
        cursor = [target]
        with patch('desktop_pet.autonomy.QCursor.pos', side_effect=lambda: cursor[0]), \
                patch('desktop_pet.autonomy.QCursor.setPos', side_effect=lambda p: cursor.__setitem__(0, p)) as move:
            auto.pounce(target)
            auto.animation.setCurrentTime(auto.animation.duration())
            self.wait_until(lambda: not auto.carrying, timeout=4000)
            self.assertGreater(move.call_count, 1)
            count = move.call_count
            QTest.qWait(100)
            self.assertEqual(move.call_count, count)

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
                                                            Qt.KeyboardModifier.ShiftModifier))
        self.assertTrue(window.motion_timer.isActive())
        released_y = window.y()
        self.wait_until(lambda: window.y() > released_y + 5)
        current = QPointF(window.character.mapToGlobal(local.toPoint()))
        self.app.sendEvent(window.character, QMouseEvent(QEvent.Type.MouseButtonPress, local, current,
                           Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.ShiftModifier))
        self.assertFalse(window.motion_timer.isActive())
        self.assertEqual((window.body.vx, window.body.vy), (0, 0))
