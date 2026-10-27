import os
import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtCore import QEvent, QPointF, QSettings, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from desktop_pet.window import PetWindow


class PetSwitchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.settings = QSettings(str(Path(self.temp.name)/'prefs.ini'), QSettings.Format.IniFormat)
        for key in ('physics/enabled', 'sound/effects', 'sound/purr', 'autonomy/enabled', 'nap/enabled'):
            self.settings.setValue(key, False)
        self.guard = patch('socket.socket.connect', side_effect=AssertionError('No network'))
        self.guard.start()
        self.windows = []

    def make_window(self, **kwargs):
        w = PetWindow(settings=self.settings, **kwargs)
        self.windows.append(w)
        w.show()
        self.app.processEvents()
        return w

    def wait(self, predicate):
        deadline = time.monotonic()+5
        while not predicate() and time.monotonic()<deadline:
            QTest.qWait(10)
        self.assertTrue(predicate())

    def tearDown(self):
        for w in self.windows:
            self.wait(lambda: w.worker is None and w.voice_worker is None)
            w.close()
            w.deleteLater()
        self.app.processEvents()
        self.guard.stop()
        self.temp.cleanup()

    def test_selector_remembers_choice_and_preserves_draft_position_and_settings(self):
        w = self.make_window()
        position = w.pos()
        w.input.setText('Mi borrador')
        w.pet_actions['golden'].trigger()
        self.assertEqual(w.pet.id, 'golden')
        self.assertTrue(w.pet_actions['golden'].isChecked())
        self.assertFalse(w.pet_actions['siamese'].isChecked())
        self.assertEqual(w.input.text(), 'Mi borrador')
        self.assertEqual(w.pos(), position)
        self.assertFalse(w.physics_enabled)
        self.assertEqual(self.make_window().pet.id, 'golden')
        golden = w.sprites
        w.set_pet('siamese')
        w.set_pet('golden')
        self.assertIs(w.sprites, golden)

    def test_language_switch_updates_ui_and_persists(self):
        w = self.make_window()
        w.set_language('en')
        self.assertEqual(w.language, 'en')
        self.assertEqual(w.input.placeholderText(), 'Type here…')
        self.assertEqual(w.response_menu.title(), 'Response mode: local demo')
        self.assertEqual(w.pet_actions['rabbit'].text(), 'Rabbit · cheerful')
        self.assertEqual(w.close_action.text(), 'Close pet')
        self.assertTrue(w.english_action.isChecked())
        w.concentration._status('ready')
        self.assertIn('open Instagram or TikTok', w.concentration_status_action.toolTip())
        self.assertEqual(self.make_window().language, 'en')
        w.set_language('es')
        self.assertEqual(w.input.placeholderText(), 'Escribe aquí…')
        self.assertEqual(w.close_action.text(), 'Cerrar mascota')

    def test_request_uses_selected_pet_and_selector_is_locked_until_finished(self):
        gate = threading.Event()
        calls = []
        def respond(question, **kwargs):
            calls.append(kwargs['pet_id'])
            gate.wait(2)
            return '¡Vamos juntos!'
        w = self.make_window()
        w.set_pet('golden')
        with patch('desktop_pet.window.answer_question', side_effect=respond):
            w.input.setText('Hola')
            w.submit()
            try:
                self.assertFalse(w.pet_menu.isEnabled())
                self.assertFalse(w.set_pet('siamese'))
                self.assertEqual(w.pet.id, 'golden')
            finally:
                gate.set()
                self.wait(lambda: w.worker is None)
        self.assertEqual(calls, ['golden'])
        self.assertTrue(w.pet_menu.isEnabled())
        self.assertTrue(w.set_pet('siamese'))

    def test_switch_clears_old_dialogue_and_sleep_without_clearing_input(self):
        w = self.make_window()
        w.show_response('Frase del gato.')
        w.sleeping = True
        w.input.setText('Pregunta pendiente')
        self.assertTrue(w.set_pet('golden'))
        self.assertFalse(w.sleeping)
        self.assertFalse(w.talking_timer.isActive())
        self.assertFalse(w.dialogue_frame.isVisible())
        self.assertEqual(w.input.text(), 'Pregunta pendiente')

    def test_missing_atlas_keeps_current_pet(self):
        w = self.make_window()
        with patch('desktop_pet.window.load_pet_sprites', side_effect=ValueError('missing')):
            self.assertFalse(w.set_pet('golden'))
        self.assertEqual(w.pet.id, 'siamese')
        self.assertTrue(w.pet_actions['siamese'].isChecked())

    def test_recording_blocks_switch_without_recording_real_audio(self):
        w = self.make_window()
        w.microphone.recording = True
        try:
            w._voice_controls()
            self.assertFalse(w.pet_menu.isEnabled())
            self.assertFalse(w.set_pet('golden'))
        finally:
            w.microphone.recording = False
            w._voice_controls()
        self.assertTrue(w.pet_menu.isEnabled())

    def test_dog_head_strokes_activate_pose_and_click_still_grabs(self):
        w = self.make_window()
        w.set_pet('golden')
        with patch.object(w.purr, 'start') as purr:
            for offset in (-8, 8, -8):
                point = QPointF(w._head_rect().center()) + QPointF(offset, 0)
                self.app.sendEvent(w.character, QMouseEvent(
                    QEvent.Type.MouseMove, point, QPointF(w.character.mapToGlobal(point.toPoint())),
                    Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
            self.assertTrue(w.petting)
            self.assertEqual(w.sprite_state, 'petting')
            purr.assert_not_called()
        QTest.mousePress(w.character, Qt.MouseButton.LeftButton)
        self.assertFalse(w.petting)
        self.assertIsNotNone(w._drag_offset)
        self.assertEqual(w.sprite_state, 'falling')
        QTest.mouseRelease(w.character, Qt.MouseButton.LeftButton)
        self.assertIsNone(w._drag_offset)

    def test_transcript_automatically_uses_dog_without_confirmation(self):
        w = self.make_window()
        w.set_pet('golden')
        with patch('desktop_pet.window.answer_question', return_value='¡Cuenta conmigo!') as answer:
            w._on_transcript('¿Me ayudas?')
            w._voice_finished()
            self.wait(lambda: w.worker is None)
        self.assertEqual(answer.call_args.kwargs['pet_id'], 'golden')
        self.assertEqual(w.bubble.text(), '¡Cuenta conmigo!')

    def test_saved_golden_starts_without_feline_sounds(self):
        self.settings.setValue('pet/selected', 'golden')
        w = self.make_window()
        self.assertEqual(w.pet.id, 'golden')
        self.assertFalse(w.sounds.feline)
        self.assertFalse(w.purr.enabled)

    def test_dog_does_not_meow_or_purr_and_cat_preference_is_preserved(self):
        self.settings.setValue('sound/purr', True)
        w = self.make_window()
        w.set_pet('golden')
        self.assertFalse(w.purr.enabled)
        self.assertFalse(w.purr_action.isEnabled())
        self.assertIn('perro', w.sounds_action.text())
        self.assertIn('patita', w.cursor_push_action.text())
        self.assertTrue(self.settings.value('sound/purr', type=bool))
        w.sounds.set_enabled(True)
        with patch.object(w.sounds, '_play') as play:
            w.sounds.start_speech()
            play.assert_not_called()
            w.sounds.set_walking(True)
            play.assert_called_once_with('walk')
        w.sounds.set_enabled(False)
        w.set_pet('siamese')
        self.assertTrue(w.purr.enabled)
        self.assertTrue(w.purr_action.isChecked())
        self.assertTrue(w.purr_action.isEnabled())
        self.assertTrue(w.sounds.feline)
