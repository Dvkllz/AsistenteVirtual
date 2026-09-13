import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtMultimedia import QMediaPlayer
from desktop_pet.purring import PurrSound, PURR_PATH


class PurrTests(unittest.TestCase):
    def make_sound(self):
        self.effect = MagicMock()
        self.effect.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
        with patch("desktop_pet.purring.QMediaPlayer", return_value=self.effect) as factory, \
                patch("desktop_pet.purring.QAudioOutput"):
            factory.Loops = QMediaPlayer.Loops
            self.sound = PurrSound(None)
        return self.sound

    def test_user_mp3_exists_and_loads_only_on_petting(self):
        sound = self.make_sound()
        self.assertEqual(PURR_PATH.name, "ronroneo.mp3")
        self.assertTrue(PURR_PATH.is_file())
        self.effect.setSource.assert_not_called()
        self.effect.setLoops.assert_called_once_with(-1)
        sound.start()
        self.effect.setSource.assert_called_once()

    def test_start_does_not_restart_loop_and_stop_clears_intent(self):
        sound = self.make_sound()
        sound.start()
        self.effect.play.assert_called_once()
        self.effect.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
        sound.start()
        self.effect.play.assert_called_once()
        sound.stop()
        self.assertFalse(sound.wanted)
        self.effect.stop.assert_called_once()

    def test_muted_does_not_load_or_play(self):
        sound = self.make_sound()
        sound.set_enabled(False)
        sound.start()
        self.assertFalse(sound.wanted)
        self.effect.setSource.assert_not_called()
        self.effect.play.assert_not_called()

    def test_missing_audio_is_safe(self):
        sound = self.make_sound()
        with patch("desktop_pet.purring.Path.is_file", return_value=False):
            sound.start()
        self.effect.play.assert_not_called()
