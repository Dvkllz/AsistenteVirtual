import os
import time
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication
from desktop_pet.sounds import AUDIO_DIR, FILES, MEOWS, CatSounds


class SoundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def make_sounds(self, enabled=True):
        with patch("desktop_pet.sounds.QMediaPlayer") as factory, \
                patch("desktop_pet.sounds.QAudioOutput"):
            factory.Loops = QMediaPlayer.Loops
            factory.Error = QMediaPlayer.Error
            factory.MediaStatus = QMediaPlayer.MediaStatus
            factory.side_effect = lambda *_: MagicMock()
            sounds = CatSounds(enabled=enabled)
        for player in sounds.players.values():
            player.error.return_value = QMediaPlayer.Error.NoError
        self.addCleanup(sounds.deleteLater)
        self.addCleanup(sounds.set_enabled, False)
        return sounds

    def test_correct_files_and_loop_modes_and_lazy_loading(self):
        sounds = self.make_sounds()
        self.assertEqual(FILES, {"meow_1": "meow_1.wav", "meow_2": "meow_2.wav",
                                "meow_3": "meow_3.wav", "close": "explota.mp3", "walk": "caminar1.mp3"})
        for name, player in sounds.players.items():
            self.assertTrue((AUDIO_DIR / FILES[name]).is_file())
            player.setLoops.assert_called_once_with(-1 if name == "walk" else 1)
            player.setSource.assert_not_called()
        sounds.start_speech()
        self.assertTrue(sounds.players[sounds.last_meow].setSource.call_args.args[0].isLocalFile())

    def test_one_meow_at_start_no_end_sound_and_no_immediate_repeat(self):
        sounds = self.make_sounds()
        sounds.start_speech()
        first = sounds.last_meow
        sounds.players[first].play.assert_called_once()
        sounds.stop_speech(completed=True)
        sounds.stop_speech(completed=True)
        self.assertEqual(sum(p.play.call_count for p in sounds.players.values()), 1)
        sounds.start_speech()
        self.assertNotEqual(sounds.last_meow, first)
        sounds.stop_speech()
        self.assertEqual(sum(p.play.call_count for p in sounds.players.values()), 2)
        self.assertNotIn("end", sounds.players)

    def test_all_three_meows_are_available_and_unmute_does_not_replay(self):
        sounds = self.make_sounds()
        with patch.object(sounds.rng, 'choice', side_effect=list(MEOWS)):
            for name in MEOWS:
                sounds.start_speech()
                self.assertEqual(sounds.last_meow, name)
        sounds.set_enabled(False)
        sounds.set_enabled(True)
        for name in MEOWS:
            sounds.players[name].play.assert_called_once()

    def test_walk_does_not_restart_every_tick_and_mute_is_immediate(self):
        sounds = self.make_sounds()
        for _ in range(10):
            sounds.set_walking(True)
        sounds.players["walk"].play.assert_called_once()
        sounds.set_enabled(False)
        sounds.players["walk"].stop.assert_called_once()
        sounds.set_enabled(True)
        self.assertEqual(sounds.players["walk"].play.call_count, 2)
        sounds.set_walking(False)
        self.assertFalse(sounds.walking)

    def test_close_once_waits_for_end_and_prevents_new_loops(self):
        sounds = self.make_sounds()
        sounds.start_speech()
        sounds.set_walking(True)
        finished = []
        sounds.close_finished.connect(lambda: finished.append(True))
        self.assertTrue(sounds.begin_close())
        self.assertTrue(sounds.begin_close())
        sounds.players["close"].play.assert_called_once()
        sounds.start_speech()
        sounds.set_walking(True)
        self.assertFalse(sounds.walking)
        sounds._close_status(QMediaPlayer.MediaStatus.EndOfMedia)
        sounds._close_status(QMediaPlayer.MediaStatus.EndOfMedia)
        self.assertEqual(finished, [True])
        self.assertFalse(sounds.close_pending)
        self.assertFalse(sounds.close_timeout.isActive())

    def test_disabled_missing_error_and_watchdog_do_not_hold_exit(self):
        self.assertFalse(self.make_sounds(False).begin_close())
        sounds = self.make_sounds()
        with patch("desktop_pet.sounds.Path.is_file", return_value=False):
            self.assertFalse(sounds.begin_close())
        sounds = self.make_sounds()
        sounds.players["close"].error.return_value = QMediaPlayer.Error.ResourceError
        self.assertFalse(sounds.begin_close())
        sounds = self.make_sounds()
        self.assertTrue(sounds.begin_close())
        sounds.close_timeout.start(10)
        QTest.qWait(30)
        self.assertFalse(sounds.close_pending)

    def test_supplied_mp3_files_decode_with_real_qt_backend_muted(self):
        sounds = CatSounds()
        try:
            for output in sounds.outputs.values():
                output.setMuted(True)
            for name, player in sounds.players.items():
                sounds._play(name)
                deadline = time.monotonic() + 4
                while player.duration() == 0 and time.monotonic() < deadline:
                    QTest.qWait(20)
                self.assertGreater(player.duration(), 0, name)
                self.assertEqual(player.error(), QMediaPlayer.Error.NoError, name)
                player.stop()
        finally:
            sounds.set_enabled(False)
            sounds.deleteLater()
