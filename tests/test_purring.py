import unittest
import wave
from unittest.mock import MagicMock, patch
from PyQt6.QtMultimedia import QSoundEffect
from desktop_pet.purring import PurrSound, PURR_PATH


class PurrTests(unittest.TestCase):
    def test_local_audio_is_short_pcm_loop(self):
        with wave.open(str(PURR_PATH), 'rb') as audio:
            self.assertEqual(audio.getnchannels(), 1)
            self.assertEqual(audio.getsampwidth(), 2)
            self.assertEqual(audio.getframerate(), 44100)
            self.assertGreater(audio.getnframes(), 44100)
            self.assertNotEqual(set(audio.readframes(44100)), {0})

    def make_sound(self):
        self.effect = MagicMock()
        self.effect.status.return_value = QSoundEffect.Status.Ready
        self.effect.isPlaying.return_value = False
        with patch('desktop_pet.purring.QSoundEffect', return_value=self.effect) as factory:
            factory.Status = QSoundEffect.Status
            self.sound = PurrSound(None)
        return self.sound

    def test_start_does_not_restart_playing_loop_and_stop_clears_intent(self):
        sound = self.make_sound()
        sound.start()
        self.effect.play.assert_called_once()
        self.effect.isPlaying.return_value = True
        sound.start()
        self.effect.play.assert_called_once()
        sound.stop()
        self.assertFalse(sound.wanted)
        self.effect.stop.assert_called_once()

    def test_delayed_load_only_plays_if_still_petting(self):
        sound = self.make_sound()
        self.effect.status.return_value = QSoundEffect.Status.Loading
        sound.start()
        self.effect.play.assert_not_called()
        sound.stop()
        self.effect.status.return_value = QSoundEffect.Status.Ready
        sound._ready()
        self.effect.play.assert_not_called()
        sound.start()
        self.effect.play.assert_called_once()

    def test_mute_and_missing_audio_are_safe(self):
        sound = self.make_sound()
        sound.set_enabled(False)
        sound.start()
        self.assertFalse(sound.wanted)
        self.effect.play.assert_not_called()
        sound.set_enabled(True)
        self.effect.status.return_value = QSoundEffect.Status.Error
        sound.start()
        self.effect.play.assert_not_called()
